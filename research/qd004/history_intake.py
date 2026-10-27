"""Explicit, bounded public Gate history intake. No trading/replay/model imports.

The only network entry point is the --fetch CLI mode. Normalization and verification
are offline. Source routes/specification are frozen before fetching; raw objects
are immutable and every attempt (including failures) consumes the shared budget.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib


SPEC_SHA256 = "6e3d4fb99c62d0658fcb3bb779a35b072d65b29df399e9b287fa315943687862"
PRIOR_PROBE_SHA256 = "33e234f0fa851993c3de62e795174b75af91e4dd69d037e5f017f302a6157c78"
ROUTE = "hybrid_native_v1"
SYMBOLS = ("BTC_USDT", "ETH_USDT")
API = "https://api.gateio.ws/api/v4/futures/usdt/"
ARCHIVE = "https://download.gatedata.org/futures_usdt/"
HEADERS = {"Accept": "application/octet-stream", "Accept-Encoding": "identity",
           "User-Agent": "GateQuantResearch-frozen-intake/1.0"}
CANDLE_UNITS = {"timestamp": "UTC_unix_seconds", "price": "USDT_per_base", "volume": "contracts"}
FUNDING_UNITS = {"timestamp": "UTC_unix_seconds", "funding_rate": "fraction_per_settlement"}


class IntakeError(ValueError):
    pass


def digest(body):
    return hashlib.sha256(body).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def strict_json(body):
    def pairs(items):
        result = dict(items)
        if len(result) != len(items):
            raise IntakeError("duplicate JSON object key")
        return result

    def invalid(value):
        raise IntakeError("nonfinite JSON constant")
    return json.loads(body, parse_float=Decimal, parse_constant=invalid, object_pairs_hook=pairs)


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_path(root, relative):
    root = Path(root).absolute()
    if root.is_symlink():
        raise IntakeError("symlink dataset root is not allowed")
    root = root.resolve()  # e.g. macOS /var -> /private/var outside the selected root.
    rel = PurePosixPath(relative)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or "\\" in relative:
        raise IntakeError("unsafe dataset-relative path")
    path = root.joinpath(*rel.parts)
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise IntakeError("symlink path is not allowed")
    return path


def write_once(root, relative, body):
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != body:
            raise IntakeError("immutable output already exists: " + relative)
    else:
        with path.open("xb") as handle:
            handle.write(body)
    return path


def load_spec(path):
    body = Path(path).read_bytes()
    if digest(body) != SPEC_SHA256:
        raise IntakeError("unapproved specification hash")
    return json.loads(body)


@contextmanager
def acquisition_lease(root):
    """One CLI writer; OS releases on process death. The sidecar is never unlinked."""
    import fcntl
    path = safe_path(root, ".acquisition.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise IntakeError("another collector owns this dataset") from exc
        yield


def epoch(year, month):
    return int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())


def plan_requests(spec):
    """210 native-source requests, chosen without inspecting any market outcome."""
    start, end = spec["calendar"]["raw_start"], spec["calendar"]["raw_end_exclusive"]
    tail = spec["sources"]["recent_api_start"]
    tasks = []

    def add(symbol, kind, seconds, url, params, fmt, **extra):
        tasks.append(dict(task_id=f"task-{len(tasks)+1:04d}", symbol=symbol, kind=kind,
            interval_seconds=seconds, url=url, params=params, format=fmt, route_id=ROUTE, **extra))

    for symbol in SYMBOLS:
        add(symbol, "contract_metadata", None, API + "contracts/" + symbol, {}, "contract_json")
        params = {"contract": symbol}
        add(symbol, "risk_tiers", None, API + "risk_limit_tiers?" + urllib.parse.urlencode(params), params, "tiers_json")
    for symbol in SYMBOLS:
        for interval, seconds in (("4h", 14400), ("1d", 86400)):
            stop = start + ((end - start) // seconds) * seconds
            cursor = start
            while cursor < stop:
                page_end = min(cursor + 1000 * seconds, stop)
                params = {"contract": symbol, "interval": interval, "from": cursor, "to": page_end - 1}
                add(symbol, "candles", seconds, API + "candlesticks?" + urllib.parse.urlencode(params),
                    params, "candles_json", expected_start=cursor, expected_end=page_end)
                if page_end == stop:
                    break
                cursor = page_end - seconds  # Real one-bar source overlap, not a synthetic row.
    year, month = 2023, 1
    while f"{year:04d}{month:02d}" <= spec["sources"]["archive_last_full_month"]:
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        label = f"{year:04d}{month:02d}"
        for symbol in SYMBOLS:
            for family, kind, seconds in (("candlesticks_1h", "candles", 3600), ("funding_applies", "funding", None)):
                params = dict(biz="futures_usdt", type=family, month=label, market=symbol)
                add(symbol, kind, seconds, ARCHIVE + f"{family}/{label}/{symbol}-{label}.csv.gz",
                    params, "candles_csv_gzip" if kind == "candles" else "funding_csv_gzip",
                    expected_start=epoch(year, month), expected_end=epoch(next_year, next_month))
        year, month = next_year, next_month
    for symbol in SYMBOLS:
        params = {"contract": symbol, "interval": "1h", "from": tail - 7200, "to": end - 1}
        add(symbol, "candles", 3600, API + "candlesticks?" + urllib.parse.urlencode(params),
            params, "candles_json", expected_start=tail - 7200, expected_end=end)
        params = {"contract": symbol, "from": tail - 86400, "to": end - 1, "limit": 1000}
        add(symbol, "funding", None, API + "funding_rate?" + urllib.parse.urlencode(params),
            params, "funding_json", expected_start=tail - 86400, expected_end=end)
    return tasks


def validate_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        raise IntakeError("only declared public HTTPS sources are allowed")
    query = urllib.parse.parse_qs(parsed.query)
    if parsed.hostname == "download.gatedata.org":
        pattern = r"/futures_usdt/(candlesticks_1h|funding_applies)/(202[3-6]\d{2})/(BTC_USDT|ETH_USDT)-\2\.csv\.gz"
        match = re.fullmatch(pattern, parsed.path)
        if not match or not "202301" <= match[2] <= "202609" or parsed.query:
            raise IntakeError("archive route outside frozen plan")
    elif parsed.hostname == "api.gateio.ws":
        prefix = "/api/v4/futures/usdt/"
        if parsed.path in (prefix + "contracts/" + s for s in SYMBOLS):
            if query:
                raise IntakeError("unexpected contract query")
        elif parsed.path in (prefix + "candlesticks", prefix + "funding_rate", prefix + "risk_limit_tiers"):
            if query.get("contract") not in ([s] for s in SYMBOLS):
                raise IntakeError("unexpected market")
            if set(query) - {"contract", "interval", "from", "to", "limit"}:
                raise IntakeError("unexpected query key")
        else:
            raise IntakeError("private/unapproved endpoint")
    else:
        raise IntakeError("unapproved source host")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def network_opener():
    import certifi  # Existing runtime dependency; nothing is installed here.
    return urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where())))


def read_attempts(root):
    path = safe_path(root, "attempts.jsonl")
    records = {}
    if path.exists():
        for line in path.read_text().splitlines():
            item = json.loads(line)
            key = item["attempt_id"]
            if item["event"] == "begin":
                if key in records:
                    raise IntakeError("duplicate attempt reservation")
                records[key] = item
            else:
                if key not in records or records[key].get("event") == "end":
                    raise IntakeError("invalid attempt completion")
                records[key] = item
    return list(records.values())


class Collector:
    def __init__(self, root, spec, prior_ledger, opener=None, pause=1.0):
        self.root, self.spec = Path(root).absolute(), spec
        safe_path(self.root, "raw/check")
        self.root.mkdir(parents=True, exist_ok=True)
        self.prior = json.loads(Path(prior_ledger).read_text())
        if len(self.prior) != 12 or [r["id"] for r in self.prior] != list(range(1, 13)):
            raise IntakeError("expected the twelve original source probes")
        self.prior_bytes = sum(r["saved_bytes"] for r in self.prior)
        self.prior_sha = digest(Path(prior_ledger).read_bytes())
        if self.prior_sha != PRIOR_PROBE_SHA256:
            raise IntakeError("original source-probe ledger hash changed")
        self.opener, self.pause = opener, pause
        self.records = read_attempts(self.root)
        # An interrupted request consumes budget and cannot be promoted on resume.
        for i, record in enumerate(self.records):
            if record["event"] == "begin":
                path = safe_path(self.root, record["path"])
                body = path.read_bytes() if path.exists() else b""
                if not path.exists():
                    write_once(self.root, record["path"], body)
                record = dict(record, event="end", http_status=None, error="interrupted",
                    bytes=len(body), sha256=digest(body), complete_object=False, accepted=False,
                    response_headers={}, hash_scope="interrupted_response")
                self._append(record)
                self.records[i] = record

    def _append(self, record):
        with safe_path(self.root, "attempts.jsonl").open("ab") as handle:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False).encode() + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

    def fetch(self, task):
        budget = self.spec["intake_budget"]
        attempts_used = 12 + len(self.records)
        used_bytes = self.prior_bytes + sum(r["bytes"] for r in self.records)
        if attempts_used >= budget["max_requests"] or used_bytes >= budget["max_total_compressed_bytes"]:
            raise IntakeError("shared acquisition budget exhausted")
        validate_url(task["url"])
        number = attempts_used + 1
        record = dict(task, event="begin", attempt_id=number, source_id=f"request-{number:05d}",
            path=f"raw/request-{number:05d}.bin", retrieved_at=now(), method="GET", request_headers=HEADERS,
            http_status=None, response_headers={}, bytes=0, complete_object=False, accepted=False)
        self._append(record)  # Reserve before network: a crash cannot reset the request budget.
        cap = min(budget["max_compressed_bytes_per_file"], budget["max_total_compressed_bytes"] - used_bytes)
        body_path = safe_path(self.root, record["path"])
        body_path.parent.mkdir(exist_ok=True)
        error, body, eof, declared_length = None, bytearray(), False, None
        try:
            with body_path.open("xb") as output:
                opener = self.opener or network_opener()
                request = urllib.request.Request(task["url"], headers=HEADERS, method="GET")
                try:
                    response = opener.open(request, timeout=15)
                except urllib.error.HTTPError as exc:
                    response = exc
                with response:
                    record["http_status"] = response.status
                    record["response_headers"] = {k.lower(): v for k, v in response.headers.items()
                        if k.lower() in {"date", "content-type", "content-length", "content-range", "etag", "last-modified", "content-encoding"}}
                    length = record["response_headers"].get("content-length")
                    if length is not None:
                        declared_length = int(length)
                    if declared_length is not None and declared_length > cap:
                        error = "declared_response_exceeds_byte_cap"
                    else:
                        while len(body) < cap:
                            block = response.read(min(65536, cap - len(body)))
                            if not block:
                                eof = True
                                break
                            body.extend(block)
                            output.write(block)
                        if not eof:
                            error = "response_byte_cap_without_EOF"
                output.flush()
                os.fsync(output.fileno())
        except Exception as exc:
            error = type(exc).__name__  # Do not expose environment/proxy credentials in exceptions.
        raw = bytes(body)
        headers = record["response_headers"]
        complete = eof and error is None
        if declared_length is not None and declared_length != len(raw):
            complete = False
            error = error or "content_length_mismatch"
        if record["http_status"] == 206:
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", headers.get("content-range", ""))
            complete = bool(complete and match and int(match[1]) == 0 and int(match[2]) + 1 == int(match[3]) == len(raw))
            if not complete:
                error = error or "partial_object"
        elif record["http_status"] != 200:
            complete = False
            error = error or "http_error"
        if headers.get("content-encoding", "identity") != "identity":
            complete = False
            error = error or "unexpected_transport_encoding"
        record.update(event="end", bytes=len(raw), sha256=digest(raw), complete_object=complete,
            accepted=complete, error=error, hash_scope="complete_object" if complete else "saved_response_only")
        self._append(record)
        self.records.append(record)
        if self.pause:
            time.sleep(self.pause)
        return record

    def acquire(self, tasks):
        write_once(self.root, "plan.json", json_bytes(dict(route_id=ROUTE, spec_sha256=SPEC_SHA256, requests=tasks)))
        successes = {r["task_id"]: r for r in self.records if r.get("accepted")}
        for record in successes.values():
            parse_source(self.root, record, self.spec)
        failures = Counter()
        for task in tasks:
            if task["task_id"] in successes:
                continue
            spent = sum(r["task_id"] == task["task_id"] for r in self.records)
            allowance = self.spec["intake_budget"]["max_retries_per_request"] + 1 - spent
            for retry in range(max(0, allowance)):
                record = self.fetch(task)
                if record["accepted"]:
                    try:
                        parse_source(self.root, record, self.spec)
                    except (IntakeError, ValueError, zlib.error, csv.Error) as exc:
                        raise IntakeError("source integrity/format failure; raw retained: " + record["source_id"]) from exc
                    successes[task["task_id"]] = record
                    break
                status = record["http_status"]
                if status in (401, 403, 451):
                    raise IntakeError("public source access restriction; no bypass")
                transient = status is None or status == 429 or status >= 500
                if not transient or retry == allowance - 1:
                    key = (task["kind"], task["interval_seconds"], urllib.parse.urlparse(task["url"]).hostname)
                    failures[key] += 1
                    if failures[key] >= 3:
                        raise IntakeError("systematic source failure; no brute-force continuation")
                    break
            print(json.dumps({"completed_tasks": len(successes), "planned_tasks": len(tasks),
                "attempts_including_probes": 12 + len(self.records), "last_task": task["task_id"],
                "status": self.records[-1]["http_status"] if self.records else None}), flush=True)
        return self.records


def number(value):
    if isinstance(value, bool):
        raise IntakeError("boolean numeric value")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise IntakeError("invalid numeric value") from exc
    if not result.is_finite():
        raise IntakeError("nonfinite numeric value")
    return result


def text(value):
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def numeric(value):
    return int(value) if value == int(value) else float(value)


def unpack_body(root, record, limit):
    body = safe_path(root, record["path"]).read_bytes()
    if digest(body) != record["sha256"] or len(body) != record["bytes"]:
        raise IntakeError("raw bytes/hash mismatch")
    if not record.get("accepted") or not record.get("complete_object"):
        raise IntakeError("partial/failed raw object cannot be parsed as data")
    if record["format"].endswith("gzip"):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        output = decoder.decompress(body, limit)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise IntakeError("gzip CRC/EOF, extra member, or expanded-size failure")
        return output
    if len(body) > limit:
        raise IntakeError("expanded size limit")
    return body


def parse_source(root, record, spec):
    """Return canonical Decimals plus one-based original data-row provenance."""
    body = unpack_body(root, record, spec["intake_budget"]["max_uncompressed_bytes_per_file"])
    kind, seconds = record["kind"], record["interval_seconds"]
    start, end = spec["calendar"]["raw_start"], spec["calendar"]["raw_end_exclusive"]
    mapping = {"source_id": record["source_id"], "format": record["format"], "header_present": False,
               "source_row_basis": "one_based_parsed_data_row_excluding_header"}
    if kind in ("contract_metadata", "risk_tiers"):
        parsed = strict_json(body)
        if not isinstance(parsed, dict if kind == "contract_metadata" else list) or not parsed:
            raise IntakeError("unexpected public metadata response")
        return [], [], mapping
    if record["format"].endswith("json"):
        parsed = strict_json(body)
        if not isinstance(parsed, list):
            raise IntakeError("market response is not a list")
        fields = ["t", "o", "h", "l", "c", "v"] if kind == "candles" else ["t", "r"]
        mapping["field_mapping"] = fields
        if not all(isinstance(row, dict) for row in parsed):
            raise IntakeError("non-object JSON data row")
        raw_rows = [(i, [row.get(k) for k in fields]) for i, row in enumerate(parsed, 1)]
    else:
        parsed = list(csv.reader(io.StringIO(body.decode("utf-8-sig")), strict=True))
        fields = ["timestamp", "size", "close", "high", "low", "open"] if kind == "candles" else ["timestamp", "funding_rate"]
        if parsed and [x.strip().lower() for x in parsed[0]] == fields:
            mapping["header_present"] = True
            parsed = parsed[1:]
        mapping["field_mapping"] = fields
        raw_rows = list(enumerate(parsed, 1))
    rows, issues = [], []
    for row_number, raw in raw_rows:
        ref = {"source_id": record["source_id"], "source_row": row_number}
        try:
            if len(raw) != len(fields):
                raise IntakeError("column_count")
            values = tuple(number(v) for v in raw)
            if kind == "candles" and not record["format"].endswith("json"):
                t, v, c, h, l, o = values
                values = (t, o, h, l, c, v)
            t = values[0]
            if t < 0 or t > 100_000_000_000:
                raise IntakeError("timestamp_unit_or_sign")
            if kind == "candles":
                t, o, h, l, c, v = values
                if t != int(t) or int(t) % seconds:
                    raise IntakeError("off_grid_timestamp")
                if min(o, h, l, c) <= 0 or v < 0 or h < max(o, c, l) or l > min(o, c, h):
                    raise IntakeError("invalid_OHLC_or_volume")
            reason = None
            if t < start or t >= end or (seconds and t + seconds > end):
                reason = "outside_global_closed_range"
            elif not record.get("expected_start", start) <= t < record.get("expected_end", end):
                reason = "outside_declared_source_partition"
            if reason:
                issues.append(dict(ref, reason=reason, values=[text(v) for v in values],
                    resolution="retained_exclusion", destination="quarantine/exclusions.json"))
            else:
                rows.append(dict(ref, symbol=record["symbol"], kind=kind,
                    interval_seconds=seconds, values=values))
        except (IntakeError, TypeError, ValueError) as exc:
            issues.append(dict(ref, reason=str(exc), raw_fields=[str(v) for v in raw],
                resolution="quarantined_invalid_row", destination="quarantine/exclusions.json"))
    mapping["parsed_data_rows"] = len(raw_rows)
    return rows, issues, mapping


def missing_ranges(timestamps, start, end, seconds):
    expected = range(start, start + ((end - start) // seconds) * seconds, seconds)
    present = set(timestamps)
    result = []
    for t in expected:
        if t in present:
            continue
        if result and result[-1]["end_exclusive"] == t:
            result[-1]["end_exclusive"] += seconds
            result[-1]["count"] += 1
        else:
            result.append(dict(start=t, end_exclusive=t + seconds, count=1))
    return result


def csv_bytes(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue().encode()


def normalize(root, spec, records, tasks, *, acquisition_error=None, prior_sha=None, prior_bytes=0):
    """Immutable candidate build. Conflicting versions all stay out of normalized data."""
    root = Path(root)
    groups = defaultdict(list)
    exclusions, file_issues, mappings, raw_entries, metadata = [], [], [], [], []
    for record in records:
        raw_entries.append(record)
        if not record.get("accepted"):
            file_issues.append(dict(source_id=record["source_id"], reason=record.get("error"),
                                    path=record["path"], resolution="retained_failed_attempt"))
            continue
        try:
            rows, issues, mapping = parse_source(root, record, spec)
        except (ValueError, UnicodeError, csv.Error, zlib.error) as exc:
            file_issues.append(dict(source_id=record["source_id"], reason=type(exc).__name__ + ":" + str(exc),
                                    path=record["path"], resolution="quarantined_file"))
            continue
        mappings.append(mapping)
        exclusions.extend(issues)
        if record["kind"] in ("contract_metadata", "risk_tiers"):
            metadata.append(record)
        for row in rows:
            groups[(row["symbol"], row["kind"], row["interval_seconds"], row["values"][0])].append(row)
    accepted = defaultdict(list)
    duplicates, conflicts = [], []
    for key, origins in sorted(groups.items(), key=lambda pair: str(pair[0])):
        variants = defaultdict(list)
        for row in origins:
            variants[row["values"]].append({"source_id": row["source_id"], "source_row": row["source_row"]})
        symbol, kind, seconds, timestamp = key
        detail = dict(symbol=symbol, kind=kind, interval_seconds=seconds, timestamp=numeric(timestamp))
        if len(variants) != 1:
            conflicts.append(dict(detail, reason="conflicting_numeric_records", resolution="quarantined_all_versions",
                variants=[dict(values=[text(v) for v in values], references=refs) for values, refs in variants.items()],
                destination="quarantine/conflicts.json"))
            continue
        primary = origins[0]
        accepted[(symbol, kind, seconds)].append(primary)
        if len(origins) > 1:
            duplicates.append(dict(detail, reason="exact_numeric_duplicate", resolution="deduplicated_identical",
                values=[text(v) for v in primary["values"]],
                references=next(iter(variants.values())),
                destination=dict(path=f"normalized/{symbol}-" + (f"{seconds}s" if seconds else "funding") + ".csv",
                    source_id=primary["source_id"], source_row=primary["source_row"])))
    normalized, gaps, schedules, extremes = [], [], {}, []
    calendar = spec["calendar"]
    for symbol in SYMBOLS:
        for kind, seconds in (("candles", 3600), ("candles", 14400), ("candles", 86400), ("funding", None)):
            rows = sorted(accepted[(symbol, kind, seconds)], key=lambda row: row["values"][0])
            columns = spec["normalization"]["candle_columns" if seconds else "funding_columns"]
            path = f"normalized/{symbol}-" + (f"{seconds}s" if seconds else "funding") + ".csv"
            content = csv_bytes(columns, [[*[text(v) for v in row["values"]],
                text(row["values"][0] + (seconds or 0)), row["source_id"], row["source_row"]] for row in rows])
            write_once(root, path, content)
            times = [row["values"][0] for row in rows]
            normalized.append(dict(symbol=symbol, kind=kind, interval_seconds=seconds, path=path,
                sha256=digest(content), rows=len(rows), start_ts=numeric(times[0]) if times else None,
                end_ts=numeric(times[-1]) if times else None, columns=columns,
                source_ids=sorted({row["source_id"] for row in rows}),
                units=CANDLE_UNITS if seconds else FUNDING_UNITS,
                availability_basis=spec["normalization"]["candle_available_at" if seconds else "funding_available_at"]))
            if seconds:
                missing = missing_ranges(times, calendar["raw_start"], calendar["raw_end_exclusive"], seconds)
                if missing:
                    gaps.append(dict(symbol=symbol, kind=kind, interval_seconds=seconds, missing_ranges=missing))
                for previous, row in zip(rows, rows[1:]):
                    if abs(row["values"][4] / previous["values"][4] - 1) > Decimal("0.2"):
                        extremes.append(dict(symbol=symbol, interval_seconds=seconds, timestamp=numeric(row["values"][0]),
                            source_id=row["source_id"], source_row=row["source_row"], resolution="retained_authenticity_unconfirmed_not_clipped"))
            else:
                durations = [b - a for a, b in zip(times, times[1:])]
                deviations = [dict(previous_ts=numeric(a), timestamp=numeric(b), duration=text(b-a),
                    reason="missing_event_or_schedule_change_unresolved") for a, b in zip(times, times[1:]) if b-a != 28800]
                schedules[symbol] = dict(observed_duration_counts=dict(Counter(text(v) for v in durations)),
                    compatibility_reference_seconds=28800, reference_basis="unchanged_native_research_interval_not_historical_metadata",
                    deviations=deviations, first_ts=numeric(times[0]) if times else None,
                    last_ts=numeric(times[-1]) if times else None,
                    boundary_coverage_unresolved=not times or times[0] >= calendar["raw_start"] + 28800 or times[-1] < calendar["raw_end_exclusive"] - 28800,
                    interpretation="Observed differences are evidence, not proof of intended historical schedule; never fill or round.")
    for record in metadata:
        payload = json.loads(safe_path(root, record["path"]).read_bytes())
        path = f"normalized/{record['symbol']}-{record['kind']}.json"
        observed = datetime.fromisoformat(record["retrieved_at"]).timestamp()
        content = json_bytes(dict(observed_at=record["retrieved_at"], historical_effective_at=None,
            source_id=record["source_id"], data=payload))
        write_once(root, path, content)
        normalized.append(dict(symbol=record["symbol"], kind=record["kind"], interval_seconds=None,
            path=path, sha256=digest(content), rows=1, start_ts=observed, end_ts=observed,
            columns=[], source_ids=[record["source_id"]], units={},
            availability_basis="current_snapshot_not_historical", observed_at=record["retrieved_at"], historical_effective_at=None))

    cross_qc = []
    for symbol in SYMBOLS:
        hourly = {row["values"][0]: row["values"] for row in accepted[(symbol, "candles", 3600)]}
        for seconds in (14400, 86400):
            mismatch, incomplete, checked = [], [], 0
            for row in accepted[(symbol, "candles", seconds)]:
                t, o, h, l, c, v = row["values"]
                pieces = [hourly.get(t + offset) for offset in range(0, seconds, 3600)]
                if any(p is None for p in pieces):
                    incomplete.append(numeric(t))
                    continue
                aggregate = (t, pieces[0][1], max(p[2] for p in pieces), min(p[3] for p in pieces),
                             pieces[-1][4], sum(p[5] for p in pieces))
                checked += 1
                if aggregate != row["values"]:
                    mismatch.append(dict(timestamp=numeric(t), native=[text(x) for x in row["values"]],
                        hourly_aggregate=[text(x) for x in aggregate], source_id=row["source_id"], source_row=row["source_row"]))
            cross_qc.append(dict(symbol=symbol, interval_seconds=seconds, checked=checked,
                mismatches=mismatch, incomplete_hourly_bins=incomplete, policy="QC_only_never_replace_native_inputs"))
    quarantine = []
    for name, reason, values in (("duplicate-lineage", "identical_duplicate_provenance", duplicates),
            ("conflicts", "all_conflicting_versions", conflicts), ("exclusions", "invalid_or_excluded_rows", exclusions),
            ("file-issues", "failed_or_invalid_raw_files", file_issues)):
        path = "quarantine/" + name + ".json"
        content = json_bytes(values)
        write_once(root, path, content)
        quarantine.append(dict(path=path, sha256=digest(content), reason=reason, rows=len(values),
            source_ids=sorted({record["source_id"] for record in records})))
    completed_tasks = {r["task_id"] for r in records if r.get("accepted")}
    quality = dict(state="NOT_READY", training="NOT_AUTHORIZED", acquisition_error=acquisition_error,
        planned_tasks=len(tasks), completed_tasks=len(completed_tasks),
        unfinished_tasks=[t["task_id"] for t in tasks if t["task_id"] not in completed_tasks],
        gaps=gaps, conflict_count=len(conflicts), exclusion_count=len(exclusions),
        duplicate_groups=len(duplicates), file_issues=file_issues, format_mappings=mappings,
        funding_schedule=schedules, cross_interval_qc=cross_qc, extreme_moves=extremes,
        duplicate_lineage="quarantine/duplicate-lineage.json",
        seam_policy="Native duplicate overlap at API pages/recent route joins; old disjoint archive months get continuity and independent coarser QC, not invented same-row funding overlap.",
        historical_metadata="current_only; historical_effective_at=null; QR must assess unchanged replay compatibility")
    manifest = dict(schema_version=1, dataset_id="gate-btc-eth-history-qd004-v1", created_at=now(),
        spec_sha256=SPEC_SHA256, data_range=dict(start=calendar["raw_start"], end_exclusive=calendar["raw_end_exclusive"]),
        symbols=list(SYMBOLS), raw_files=raw_entries, normalized_files=normalized, quarantine_files=quarantine,
        quality_summary=quality, route_id=ROUTE, prior_probe_count=12, prior_probe_ledger_sha256=prior_sha,
        attempts_including_probes=12 + len(records), bytes_including_probes=prior_bytes + sum(r["bytes"] for r in records),
        collector_sha256=digest(Path(__file__).read_bytes()),
        limitations=["Candidate only: QR independently validates G1/G2 and full warmup/events; no replay/training performed.",
            "Proxy availability is not observed historical arrival; current metadata is not backdated.",
            "Funding duration changes may be missing records or schedule changes; unresolved deviations block native constant-interval replay."])
    write_once(root, "manifest.json", json_bytes(manifest))
    return manifest


def verify_dataset(root, spec):
    """Second disk-reading pass: every source origin is retained/accounted for.

    This does not replace QR's independently implemented semantic validator.
    Gaps/quarantines may be reported candidates; missing provenance is an error.
    """
    root = Path(root)
    manifest = json.loads(safe_path(root, "manifest.json").read_bytes())
    if manifest["spec_sha256"] != SPEC_SHA256 or manifest["symbols"] != list(SYMBOLS):
        raise IntakeError("manifest scope/spec changed")
    if manifest["data_range"] != dict(start=spec["calendar"]["raw_start"], end_exclusive=spec["calendar"]["raw_end_exclusive"]):
        raise IntakeError("manifest silently changed date range")
    if manifest["attempts_including_probes"] > spec["intake_budget"]["max_requests"]:
        raise IntakeError("attempt budget violated")
    if manifest["bytes_including_probes"] > spec["intake_budget"]["max_total_compressed_bytes"]:
        raise IntakeError("byte budget violated")
    raw_by_ref, expected_exclusions, failed_sources = {}, {}, set()
    raw_sources = {}
    for record in manifest["raw_files"]:
        validate_url(record["url"])
        body = safe_path(root, record["path"]).read_bytes()
        if digest(body) != record["sha256"] or len(body) != record["bytes"]:
            raise IntakeError("raw file changed")
        if record["source_id"] in raw_sources:
            raise IntakeError("duplicate source ID")
        raw_sources[record["source_id"]] = record
        if not record.get("accepted"):
            failed_sources.add(record["source_id"])
            continue
        try:
            rows, exclusions, _ = parse_source(root, record, spec)
        except (ValueError, csv.Error, zlib.error, UnicodeError):
            failed_sources.add(record["source_id"])
            continue
        for row in rows:
            ref = row["source_id"], row["source_row"]
            raw_by_ref[ref] = (row["symbol"], row["kind"], row["interval_seconds"], row["values"])
        for row in exclusions:
            expected_exclusions[row["source_id"], row["source_row"]] = row
    retained = {}
    for entry in manifest["quarantine_files"]:
        path = safe_path(root, entry["path"])
        content = path.read_bytes()
        if digest(content) != entry["sha256"] or not set(entry["source_ids"]).issubset(raw_sources):
            raise IntakeError("quarantine content/lineage changed")
        retained[path.name] = json.loads(content)
    excluded = {(row["source_id"], row["source_row"]): row for row in retained["exclusions.json"]}
    if excluded != expected_exclusions:
        raise IntakeError("raw exclusions not fully accounted for")
    if not failed_sources.issubset({row["source_id"] for row in retained["file-issues.json"]}):
        raise IntakeError("failed raw source not retained in quarantine evidence")
    memberships, primary_refs = {}, set()
    normalized_rows = 0
    for entry in manifest["normalized_files"]:
        path = safe_path(root, entry["path"])
        content = path.read_bytes()
        if digest(content) != entry["sha256"] or not set(entry["source_ids"]).issubset(raw_sources):
            raise IntakeError("normalized bytes/source mismatch")
        if entry["kind"] not in ("candles", "funding"):
            data = json.loads(content)
            if data["historical_effective_at"] is not None or data["observed_at"] != entry["observed_at"]:
                raise IntakeError("current metadata backdated")
            continue
        candle = entry["kind"] == "candles"
        prefix = "candle" if candle else "funding"
        columns = spec["normalization"][prefix + "_columns"]
        if entry["columns"] != columns or entry["units"] != (CANDLE_UNITS if candle else FUNDING_UNITS):
            raise IntakeError("normalized units/schema drift")
        if entry["availability_basis"] != spec["normalization"][prefix + "_available_at"]:
            raise IntakeError("availability interpretation drift")
        reader = csv.DictReader(io.StringIO(content.decode()))
        if reader.fieldnames != columns:
            raise IntakeError("CSV columns changed")
        rows = list(reader)
        if len(rows) != entry["rows"]:
            raise IntakeError("CSV count mismatch")
        times = []
        fields = ["timestamp", "open", "high", "low", "close", "volume"] if candle else ["timestamp", "funding_rate"]
        for row in rows:
            ref = row["source_id"], int(row["source_row"])
            values = tuple(number(row[k]) for k in fields)
            identity = entry["symbol"], entry["kind"], entry["interval_seconds"], values
            if raw_by_ref.get(ref) != identity or ref[0] not in entry["source_ids"]:
                raise IntakeError("normalized row has altered/unresolved raw origin")
            if number(row["available_at"]) != values[0] + (entry["interval_seconds"] or 0):
                raise IntakeError("availability changed")
            key = identity[:3] + (values[0],)
            if key in memberships:
                raise IntakeError("duplicate normalized timestamp")
            memberships[key] = identity
            primary_refs.add(ref)
            times.append(values[0])
        if times != sorted(times) or (times and (numeric(times[0]) != entry["start_ts"] or numeric(times[-1]) != entry["end_ts"])):
            raise IntakeError("normalized timestamp bounds/order changed")
        normalized_rows += len(rows)
    accountable = set(primary_refs)
    for duplicate in retained["duplicate-lineage.json"]:
        values = tuple(number(v) for v in duplicate["values"])
        identity = duplicate["symbol"], duplicate["kind"], duplicate["interval_seconds"], values
        if memberships.get(identity[:3] + (values[0],)) != identity:
            raise IntakeError("duplicate has no identical normalized destination")
        for ref in duplicate["references"]:
            key = ref["source_id"], ref["source_row"]
            if raw_by_ref.get(key) != identity:
                raise IntakeError("duplicate lineage changed numeric values")
            accountable.add(key)
    for conflict in retained["conflicts.json"]:
        if (conflict["symbol"], conflict["kind"], conflict["interval_seconds"], number(conflict["timestamp"])) in memberships:
            raise IntakeError("conflicting timestamp was silently promoted")
        for variant in conflict["variants"]:
            values = tuple(number(v) for v in variant["values"])
            identity = conflict["symbol"], conflict["kind"], conflict["interval_seconds"], values
            for ref in variant["references"]:
                key = ref["source_id"], ref["source_row"]
                if raw_by_ref.get(key) != identity:
                    raise IntakeError("conflict lineage changed numeric values")
                accountable.add(key)
    if accountable != set(raw_by_ref):
        raise IntakeError("eligible raw record silently dropped from normalization/quarantine")
    return dict(status="PASS_LOCAL_FILE_AND_LINEAGE_RECHECK", training="NOT_READY",
        manifest_sha256=digest(safe_path(root, "manifest.json").read_bytes()),
        raw_files=len(raw_sources), normalized_rows=normalized_rows,
        accountable_raw_origins=len(accountable), excluded_origins=len(excluded),
        failed_sources_retained=len(failed_sources), independent_QR_review="PENDING")


def execute(args, spec):
    if args.verify_only or (args.root / "manifest.json").exists():
        print(json.dumps(verify_dataset(args.root, spec), sort_keys=True))
        return
    if args.prior_probe_ledger is None:
        raise IntakeError("--prior-probe-ledger is required for acquisition/normalization")
    collector = Collector(args.root, spec, args.prior_probe_ledger)
    tasks = plan_requests(spec)
    acquisition_error = None
    if args.fetch:
        try:
            collector.acquire(tasks)
        except (IntakeError, OSError, ValueError) as exc:
            acquisition_error = type(exc).__name__ + ": " + str(exc)
            print(json.dumps({"acquisition_stopped": acquisition_error}), flush=True)
    manifest = normalize(args.root, spec, collector.records, tasks, acquisition_error=acquisition_error,
                         prior_sha=collector.prior_sha, prior_bytes=collector.prior_bytes)
    verification = verify_dataset(args.root, spec)
    write_once(args.root, "verification.json", json_bytes(verification))
    print(json.dumps(dict(manifest_sha256=verification["manifest_sha256"],
        attempts=manifest["attempts_including_probes"], bytes=manifest["bytes_including_probes"],
        completed=manifest["quality_summary"]["completed_tasks"], planned=len(tasks),
        status="CANDIDATE_NOT_READY_FOR_TRAINING", local_verification=verification["status"])), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prior-probe-ledger", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fetch", action="store_true")
    mode.add_argument("--normalize-only", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    spec = load_spec(args.spec)
    if args.verify_only:
        execute(args, spec)
    else:
        with acquisition_lease(args.root):
            execute(args, spec)


if __name__ == "__main__":
    main()
