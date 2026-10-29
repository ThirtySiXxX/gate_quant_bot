"""QR008 independent read-only exact-data acceptance. Standard library only.

Expected values come from raw records and Fraction, never QD implementation or
producer PASS flags. No datasets, features, labels or fitted objects are written.
"""
from __future__ import annotations

import argparse
import copy
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import time

SPEC_COMMIT = "8b9e85e5c041fcf9167940520035693562f761ba"
SPEC_SHA = "cd0e123d019b428e7bd12754e553c0322d4aac5593537b07752bab777280bdc0"
APPROVAL_SHA = "d3eeb12d0d5348f769a9493a215eb32e2f3be40c13ed4a0eb5607e7cef9effa0"
BUILDER_COMMIT = "383c5acccbaee652c5d9f5c84e936b7cedfa7070"
BUILDER_SHA = "9e0d36333fc0951f5b7cc51eb10b2873a115f91239fba550bdfd8a178b244448"
MANIFEST_SHAS = ("c1e6056058fd312d472e96fddfea15e78c778847de9942e5757cb39ad2ac9b91",
                 "c93557759de54a879aab582b196c8de36c99919712c439f810ab7f1d56e6e8a8")
NS = "qr008.exact-ohlcv"
DATASET = "gate-btc-eth-exact-ohlcv-v3-candidate"
POLICY = "ARCHIVE_PREFIX_REST_COMPLETE_ROWS_FROM_20251201_R1"
AGGREGATION = "UTC_EXACT_HOURLY_PARENTS_R1"
START, CUTOVER, END = 1672531200000000, 1764547200000000, 1790812800000000
U = 1000000
SYMBOLS = ("BTC_USDT", "ETH_USDT")
PERIODS = (3600, 14400, 86400)
NUMERIC = ("open", "high", "low", "close", "volume_contracts")
RAW_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z", re.ASCII)
INT_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
HEX_RE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
ROW_FIELDS = set("namespace schema_version dataset_id input_catalog_sha256 source_policy_id aggregation_version row_id content_sha256 instrument_id market price_kind interval_seconds bar_open_us bar_close_us open high low close volume_contracts research_available_at_us observed_first_available_at_us availability_basis null_reasons source_refs parent_rows source_segment".split())
PROJECTION_FIELDS = tuple("instrument_id market price_kind interval_seconds bar_open_us bar_close_us open high low close volume_contracts research_available_at_us observed_first_available_at_us availability_basis null_reasons".split())


class ReviewError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def digest(value):
    return sha(canonical(value))


def loads(body):
    def pairs(items):
        result = dict(items)
        require(len(result) == len(items), "duplicate JSON key")
        return result
    def invalid(value):
        raise ReviewError("nonfinite JSON: " + value)
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def raw_decimal(text, positive=False):
    require(type(text) is str and len(text) <= 128 and RAW_RE.fullmatch(text), "raw unsigned decimal string")
    require(len(text.split(".")[1] if "." in text else "") <= 64, "raw decimal precision")
    value = Fraction(text)
    require(not positive or value > 0, "nonpositive price")
    return value


def decimal_text(value):
    """Exact finite rational serialization, independent of Decimal context."""
    value = Fraction(value)
    n, d = abs(value.numerator), value.denominator
    twos = fives = 0
    while d % 2 == 0:
        twos += 1
        d //= 2
    while d % 5 == 0:
        fives += 1
        d //= 5
    require(d == 1, "nonterminating exact amount")
    scale = max(twos, fives)
    text = str(n * 2 ** (scale - twos) * 5 ** (scale - fives)).zfill(scale + 1)
    if scale:
        text = (text[:-scale] + "." + text[-scale:]).rstrip("0").rstrip(".")
    return ("-" if value < 0 else "") + text


def output_decimal(text, positive=False):
    require(type(text) is str and len(text) <= 160 and RAW_RE.fullmatch(text), "output decimal type/domain")
    require(len(text.split(".")[1] if "." in text else "") <= 64, "output decimal precision")
    value = Fraction(text)
    require(decimal_text(value) == text and (not positive or value > 0), "noncanonical/nonpositive output decimal")
    return value


def uint(value, message="integer", positive=False):
    require(type(value) is int and (1 if positive else 0) <= value <= 2**63 - 1, message)
    return value


def regular(path, maximum):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink input: " + str(path))
    require(path.is_file() and path.stat().st_size <= maximum, "missing/oversized input: " + str(path))
    return path


def pinned(path, expected_sha, maximum=64 * 1024 * 1024):
    body = regular(path, maximum).read_bytes()
    require(sha(body) == expected_sha, "input hash: " + str(path))
    return body


@contextmanager
def offline():
    def forbidden(*args, **kwargs):
        raise ReviewError("Network disabled")
    previous = socket.create_connection, socket.socket.connect, socket.socket.connect_ex
    socket.create_connection = socket.socket.connect = socket.socket.connect_ex = forbidden
    try:
        yield
    finally:
        socket.create_connection, socket.socket.connect, socket.socket.connect_ex = previous


@contextmanager
def bounded(seconds=900):
    require(0 < seconds <= 900, "verification time budget")
    def expired(*args):
        raise ReviewError("verification exceeded declared time budget")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def ohlcv(values):
    require(len(values) == 5, "five OHLCV values required")
    numbers = tuple(raw_decimal(v, i < 4) for i, v in enumerate(values))
    o, h, l, c, _ = numbers
    require(l <= min(o, c) <= max(o, c) <= h, "OHLC domain")
    return numbers


def parse_archive(body, descriptor):
    """Bounded small hourly objects, CRC checked through complete gzip EOF."""
    expanded = gzip.decompress(body)
    require(len(expanded) <= 1024 * 1024, "hourly expansion bound")
    require(len(expanded) == descriptor["expanded_bytes"] and sha(expanded) == descriptor["expanded_sha256"], "archive expanded identity")
    rows = []
    for line_no, physical in enumerate(expanded.splitlines(), 1):
        require(physical and len(physical) <= 1024, "hourly physical line")
        values = next(csv.reader([physical.decode("utf-8")], strict=True))
        require(len(values) == 6 and INT_RE.fullmatch(values[0]), "archive six fields/time")
        t = int(values[0]);uint(t)
        require(t == descriptor["start"] + (line_no - 1) * 3600, "archive missing/duplicate/order/grid")
        rows.append((t, ohlcv([values[i] for i in (5, 3, 4, 2, 1)]), line_no))
    require(len(rows) == descriptor["rows"] == (descriptor["end_exclusive"] - descriptor["start"]) // 3600, "archive complete grid")
    require(bool(rows), "empty archive")
    return rows


def parse_rest(body, descriptor):
    source = loads(body)
    require(type(source) is list and source, "REST nonempty array")
    rows = []
    for i, row in enumerate(source, 1):
        require(type(row) is dict and set(row) == set("t o h l c v sum".split()), "REST closed fields")
        t = uint(row["t"])
        require(t == descriptor["start"] + (i - 1) * 3600, "REST missing/duplicate/order/grid")
        raw_decimal(row["sum"])
        rows.append((t, ohlcv([row[k] for k in ("o", "h", "l", "c", "v")]), i))
    require(len(rows) == descriptor["rows"] == (descriptor["end_exclusive"] - descriptor["start"]) // 3600, "REST complete grid")
    return rows, source


def parse_v2(body, expected_count=32856):
    reader = csv.reader(io.StringIO(body.decode("utf-8"), newline=""), strict=True)
    require(next(reader) == "timestamp,open,high,low,close,volume,available_at,source_id,source_row".split(","), "v2 fields")
    result = []
    for i, values in enumerate(reader, 1):
        require(len(values) == 9 and INT_RE.fullmatch(values[0]) and INT_RE.fullmatch(values[6]) and INT_RE.fullmatch(values[8]), "v2 scalar types")
        t = int(values[0])
        require(t * U == START + (i - 1) * 3600 * U and int(values[6]) == t + 3600, "v2 clocks/grid")
        result.append((t, ohlcv(values[1:6]), values[7], int(values[8])))
    require(len(result) == expected_count, "v2 hourly coverage")
    return result


def aggregate(parents):
    require(bool(parents), "empty aggregate")
    return (parents[0][0], max(p[1] for p in parents), min(p[2] for p in parents),
            parents[-1][3], sum((p[4] for p in parents), Fraction()))


def v2_overlap(rows, start=START, end=END):
    """Old v2 retains its later tail; compare the entire declared new interval."""
    selected = [r for r in rows if start <= r[0]*U < end]
    require([r[0]*U for r in selected] == list(range(start,end,3600*U)), "v2 overlap missing/duplicate/grid")
    return selected


def expected_row(symbol, period, opened, values, refs, parents, catalog_sha):
    instrument = "gate:usdt:" + symbol
    row = dict(namespace=NS, schema_version=1, dataset_id=DATASET, input_catalog_sha256=catalog_sha,
               source_policy_id=POLICY, aggregation_version=AGGREGATION, instrument_id=instrument,
               market="USDT_linear_perpetual", price_kind="TRADE", interval_seconds=period,
               bar_open_us=opened, bar_close_us=opened + period * U,
               research_available_at_us=opened + period * U, observed_first_available_at_us=None,
               availability_basis="BAR_CLOSE_PROXY_NOT_OBSERVED",
               null_reasons={"observed_first_available_at_us": "HISTORICAL_FIRST_AVAILABILITY_UNKNOWN"},
               source_refs=refs, parent_rows=parents,
               source_segment="ARCHIVE_PREFIX" if opened < CUTOVER else "DECIMAL_REST_SUFFIX")
    row.update(zip(NUMERIC, map(decimal_text, values)))
    row["row_id"] = digest([NS, 1, DATASET, catalog_sha, POLICY, AGGREGATION, instrument, period, opened])
    row["content_sha256"] = digest(row)
    return row


def check_row(row, expected):
    require(type(row) is dict and set(row) == ROW_FIELDS, "row closed fields")
    for key in ("schema_version", "interval_seconds", "bar_open_us", "bar_close_us", "research_available_at_us"):
        uint(row[key], "row integer: " + key)
    for key in NUMERIC:
        output_decimal(row[key], key != "volume_contracts")
    require(type(row["source_refs"]) is list and type(row["parent_rows"]) is list, "row refs lists")
    for ref in row["source_refs"]:
        require(type(ref) is dict and set(ref) == {"raw_sha256", "source_row"}, "source ref fields")
        uint(ref["source_row"], "physical source row", positive=True)
        require(type(ref["raw_sha256"]) is str and HEX_RE.fullmatch(ref["raw_sha256"]), "source hash")
    for ref in row["parent_rows"]:
        require(type(ref) is dict and set(ref) == {"row_id", "content_sha256"}, "parent ref fields")
        require(all(type(v) is str and HEX_RE.fullmatch(v) for v in ref.values()), "parent hash")
    require(row == expected, "independent expected row differs at " + str(expected["bar_open_us"]))
    return row


def economic_projection(row):
    """Only declared economic/clocks fields; audit identities never decision inputs."""
    return {k: row[k] for k in PROJECTION_FIELDS}


def read_expected_row(handle, expected):
    raw = handle.readline(32769)
    require(0 < len(raw) <= 32768, "missing/oversized candidate line")
    check_row(loads(raw), expected)
    require(raw == canonical(expected)+b"\n", "canonical row bytes")
    return raw


def require_eof(handle):
    require(handle.read(1) == b"", "extra/duplicate candidate row")


def usable(row, decision_us, cutoff=END):
    uint(decision_us)
    return decision_us < cutoff and row["research_available_at_us"] <= decision_us


def verify_sources(spec, catalog):
    audit = spec["independent_audit"]
    cache = {}; fingerprints = []
    for item in audit["files"]:
        body = pinned(item["path"], item["sha256"])
        require(len(body) == item["bytes"], "frozen source size")
        fingerprints.append(dict(path=item["path"], bytes=len(body), sha256=sha(body)))
        if not item["kind"].startswith("mark_"):
            cache[item["path"]] = body
    require(len(cache) == 129 and len(fingerprints) == 148, "fixed source inventory")
    metadata = {path: loads(body) for path, body in cache.items() if path.endswith(".json") and any(x["path"] == path and x["kind"] == "evidence" for x in audit["files"])}
    v1 = next(v for p, v in metadata.items() if p.endswith("qd004/history-v1/manifest.json"))
    v2_manifest = next(v for p, v in metadata.items() if p.endswith("qd005/canonical-hourly-v2/manifest.json"))
    receipts = {r["sha256"]: r for r in v1["raw_files"]}
    for p, value in metadata.items():
        if p.endswith("/result.json") and "volume-" in p:
            receipts.update({r["sha256"]: r for r in value["attempts"]})
    expected_sources = []
    archive = {s: [] for s in SYMBOLS};rest = {s: [] for s in SYMBOLS};confirmations = []
    all_rest_records = {}
    for desc in audit["archive_objects"] + audit["rest_objects"]:
        symbol = desc["instrument"];require(symbol in SYMBOLS, "source instrument")
        is_archive = "source_id" in desc
        role = ("SELECTED_ARCHIVE_PREFIX" if desc["start"] * U < CUTOVER else "SHADOW_ARCHIVE_SUFFIX") if is_archive else ("SELECTED_DECIMAL_REST_SUFFIX" if desc["kind"] == "bulk" else "CORROBORATION_ONLY")
        expected_sources.append(dict(format="gzip_utf8_csv_six_physical_fields" if is_archive else "utf8_json_array",
            instrument_id="gate:usdt:" + symbol, original_time_unit="UTC_unix_seconds", raw_descriptor=desc,
            receipt=receipts[desc["raw_sha256"]], role=role,
            source_row_basis="one_based_physical_line" if is_archive else "one_based_JSON_array_element"))
        body = cache[desc["path"]];require(sha(body) == desc["raw_sha256"], "raw descriptor identity")
        if is_archive:
            parsed = parse_archive(body, desc)
        else:
            parsed, raw_records = parse_rest(body, desc)
            require(desc["request_headers"]["X-Gate-Size-Decimal"] == "1", "decimal response request")
            if desc["kind"] == "bulk":
                all_rest_records.update({(symbol, r["t"]): r for r in raw_records})
            else:
                confirmations.append((desc, raw_records))
        require(sum(v[1][-1].denominator != 1 for v in parsed) == desc["fractional_volume_rows"], "raw fractional rows")
        if role == "CORROBORATION_ONLY":
            continue
        destination = archive if is_archive else rest
        for t, numbers, line_no in parsed:
            destination[symbol].append(dict(t=t, values=numbers, ref={"raw_sha256": desc["raw_sha256"], "source_row": line_no}, descriptor=desc))
    require(catalog["sources"] == expected_sources, "catalog source declarations/receipt/order differ")
    for desc, rows in confirmations:
        require(len(rows) == 1 and rows[0] == all_rest_records[(desc["instrument"], rows[0]["t"])], "confirmation all-field mismatch")
    require(len(confirmations) == 4, "confirmation inventory")
    selected = {}; differences = []
    for symbol in SYMBOLS:
        old, new = archive[symbol], rest[symbol]
        require([r["t"] for r in old] == list(range(START // U, END // U, 3600)), "archive full symbol grid")
        require([r["t"] for r in new] == list(range(CUTOVER // U, END // U, 3600)), "REST full symbol grid")
        v2_file = next(x for x in audit["files"] if x["kind"] == "v2_normalized" and x["path"].endswith("/" + symbol + "-3600s.csv"))
        v2_desc = next(r for r in v2_manifest["files"] if r["symbol"] == symbol and r["kind"] == "candles" and r["interval_seconds"] == 3600)
        require(v2_desc["sha256"] == v2_file["sha256"] and v2_manifest["data_range"]["start"] * U == START
                and v2_desc["rows"] * 3600 == v2_manifest["data_range"]["end_exclusive"]-v2_manifest["data_range"]["start"], "old v2 original range binding")
        v2 = v2_overlap(parse_v2(cache[v2_file["path"]], v2_desc["rows"]))
        for index, old_row in enumerate(old):
            require(v2[index] == (old_row["t"], old_row["values"], old_row["descriptor"]["source_id"], old_row["ref"]["source_row"]), "old v2/archive full-row/lineage mismatch")
        selected[symbol] = old[:25560] + new
        for n, current in enumerate(new):
            previous = old[25560 + n]
            fields = {}
            for key, a, b in zip(("open", "high", "low", "close", "volume"), previous["values"], current["values"]):
                if a != b:
                    fields[key] = dict(archive=decimal_text(a), rest=decimal_text(b), rest_minus_archive=decimal_text(b - a))
            if fields:
                tuple_keys = ("open", "high", "low", "close", "volume")
                differences.append(dict(instrument=symbol, timestamp=current["t"],
                    utc=datetime.fromtimestamp(current["t"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    archive_ref=[previous["descriptor"]["source_id"], previous["ref"]["source_row"], previous["ref"]["raw_sha256"]],
                    rest_ref=[current["descriptor"]["path"], current["ref"]["source_row"], current["ref"]["raw_sha256"]],
                    v2_ref=[v2_file["path"], 25560 + n + 1, v2_file["sha256"]], fields=fields,
                    archive_ohlcv=dict(zip(tuple_keys, map(decimal_text, previous["values"]))),
                    rest_ohlcv=dict(zip(tuple_keys, map(decimal_text, current["values"]))),
                    v2_ohlcv=dict(zip(tuple_keys, map(decimal_text, v2[25560+n][1])))))
    require([{k: v for k, v in row.items() if not k.endswith("_ohlcv")} for row in differences] == audit["differences"], "independent discrepancy inventory differs from frozen review")
    require(len(differences) == 4221 and sum(len(r["fields"]) for r in differences) == 4222, "discrepancy coverage")
    return selected, differences, fingerprints


def verify_pair(spec_path, approval_path, roots, checkpoint=None):
    started = time.monotonic()
    checkpoint = {} if checkpoint is None else checkpoint
    spec = loads(pinned(spec_path, SPEC_SHA));approval = loads(pinned(approval_path, APPROVAL_SHA))
    require(approval["status"] == "APPROVED" and approval["policy_id"] == POLICY and approval["spec_sha256"] == SPEC_SHA
            and approval["scope"] == spec["scope"] and approval["approved_source_segments"] == spec["source_policy"]["selection"], "frozen approval binding")
    require(approval["disclosed_price_change"] == dict(instrument="BTC_USDT", bar_open_utc="2026-08-28T14:00:00Z", old_close="79513.6", selected_close="79509.9"), "approval whole-row conflict")
    roots = [Path(r).absolute() for r in roots]
    require(len(roots) == 2 and roots[0] != roots[1], "two distinct handed-off roots required")
    manifests = [loads(pinned(root/"manifest.json", h, 1024*1024)) for root, h in zip(roots, MANIFEST_SHAS)]
    require({k:v for k,v in manifests[0].items() if k != "created_at_utc"} == {k:v for k,v in manifests[1].items() if k != "created_at_utc"}, "two manifests differ beyond created_at")
    manifest = manifests[0]
    require(set(manifest) == set("aggregation_version approval_decision_id approval_sha256 builder_commit builder_sha256 candles created_at_utc dataset_id dataset_revision files independent_candidate_checker input_catalog_sha256 labels limitations market_replays model_fits namespace native_activation network_requests normative_review schema_version scope source_discrepancies_sha256 source_policy_id specification_commit specification_sha256 status".split()), "manifest closed fields")
    for k in ("schema_version", "dataset_revision", "labels", "market_replays", "model_fits", "network_requests"):
        uint(manifest[k], "manifest integer: " + k)
    require(manifest["namespace"] == NS and manifest["schema_version"] == 1 and manifest["approval_decision_id"] == "QR008-DATA-SOURCE-1"
            and manifest["native_activation"] is False and all(manifest[k] == 0 for k in ("labels", "market_replays", "model_fits", "network_requests")), "manifest scope flags")
    require(manifest["builder_commit"] == BUILDER_COMMIT and manifest["builder_sha256"] == BUILDER_SHA
            and manifest["specification_commit"] == SPEC_COMMIT and manifest["specification_sha256"] == SPEC_SHA
            and manifest["approval_sha256"] == APPROVAL_SHA and manifest["scope"] == spec["scope"]
            and manifest["source_policy_id"] == POLICY and manifest["aggregation_version"] == AGGREGATION
            and manifest["dataset_id"] == DATASET and manifest["dataset_revision"] == 3, "candidate policy/identity")
    require(manifest["status"] == "PENDING_INDEPENDENT_REVIEW" and manifest["independent_candidate_checker"] == dict(commit=None, sha256=None, status="NOT_EXECUTED"), "producer must not self-attest QR acceptance")
    files = {r["path"]: r for r in manifest["files"]}
    for item in files.values():
        require(set(item) == {"path","bytes","sha256"}, "file inventory closed fields")
        uint(item["bytes"], "file bytes", positive=True)
        require(type(item["sha256"]) is str and HEX_RE.fullmatch(item["sha256"]), "file hash type")
    require(len(manifest["candles"]) == 6 and len({r["path"] for r in manifest["candles"]}) == 6, "six candle descriptions")
    expected_names = {"input-catalog.json", "source-discrepancies.jsonl", "candidate-checks.json"} | {f"candles/{s}-{p}s.jsonl" for s in SYMBOLS for p in PERIODS}
    require(len(files) == len(manifest["files"]) == 9 and set(files) == expected_names, "complete candidate inventory")
    for root in roots:
        require(not any(p.is_symlink() for p in (root, *root.parents)), "candidate symlink root")
        inventory = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() or p.is_symlink()}
        require(inventory == expected_names | {"manifest.json"}, "unexpected/missing candidate file")
        require(sum(regular(root/n, 512*1024*1024).stat().st_size for n in inventory) == 134212899, "candidate total bytes")
    catalogs = [pinned(root/"input-catalog.json", files["input-catalog.json"]["sha256"]) for root in roots]
    require(catalogs[0] == catalogs[1], "catalog reproducibility")
    catalog = loads(catalogs[0]);catalog_hash = digest(catalog)
    require(catalogs[0] == canonical(catalog)+b"\n" and catalog_hash == manifest["input_catalog_sha256"], "catalog canonical preimage")
    require(set(catalog) == set("approval_sha256 evidence_files historical_first_availability historical_revision_history namespace schema_version scope source_policy_id sources specification".split()), "catalog closed fields")
    require(catalog["namespace"] == "qd008.exact-ohlcv-input-catalog" and type(catalog["schema_version"]) is int and catalog["schema_version"] == 1, "catalog schema")
    require(catalog["approval_sha256"] == APPROVAL_SHA and catalog["source_policy_id"] == POLICY and catalog["scope"] == spec["scope"]
            and catalog["specification"] == dict(commit=SPEC_COMMIT, sha256=SPEC_SHA)
            and catalog["evidence_files"] == spec["independent_audit"]["files"]
            and catalog["historical_first_availability"] == catalog["historical_revision_history"] == "UNKNOWN", "catalog provenance/unknown claims")
    checkpoint["phase"] = "raw source reconciliation"
    selected, differences, fingerprints = verify_sources(spec, catalog)
    print("QR008 exact: frozen sources parsed and discrepancies independently reconstructed", flush=True)
    verified_files = {}; stats = {}
    for symbol in SYMBOLS:
        hourly = selected[symbol];hourly_refs = [];higher = {}
        sums = {}
        for period in PERIODS:
            relative = f"candles/{symbol}-{period}s.jsonl";checkpoint.update(phase="candidate row verification", file=relative)
            handles = [(root/relative).open("rb") for root in roots];hashes = [hashlib.sha256(), hashlib.sha256()];sizes = [0,0]
            total = Fraction();factor = period//3600;count = 0;values4 = []
            try:
                for offset in range(0, len(hourly), factor):
                    group = hourly[offset:offset+factor]
                    require(len(group) == factor, "incomplete aggregate")
                    values = aggregate([r["values"] for r in group]);opened = group[0]["t"] * U
                    parent_refs = [] if period == 3600 else hourly_refs[offset:offset+factor]
                    expected = expected_row(symbol, period, opened, values, [r["ref"] for r in group], parent_refs, catalog_hash)
                    checkpoint["bar_open_us"] = opened
                    for i, handle in enumerate(handles):
                        raw = read_expected_row(handle, expected)
                        hashes[i].update(raw);sizes[i] += len(raw)
                    total += values[-1];count += 1
                    if period == 3600:
                        hourly_refs.append({k:expected[k] for k in ("row_id", "content_sha256")})
                    if period == 14400:
                        values4.append(values)
                    if period == 86400:
                        require(values == aggregate(higher[14400][offset//4:offset//4+6]), "nested 1h/4h/day arithmetic differs")
                    if offset == len(hourly)-factor:
                        require(expected["bar_close_us"] == END and not usable(expected, END-1) and not usable(expected, END), "exclusive cutoff")
                for handle in handles:require_eof(handle)
            finally:
                for handle in handles:handle.close()
            expected_file = files[relative]
            require(all(h.hexdigest() == expected_file["sha256"] for h in hashes) and sizes == [expected_file["bytes"]]*2, "candidate full bytes/hash")
            require(count == {3600:32856,14400:8214,86400:1369}[period], "six full grids")
            entry = next(r for r in manifest["candles"] if r["path"] == relative)
            require(entry == dict(expected_file, instrument_id="gate:usdt:"+symbol, interval_seconds=period, rows=count,
                first_bar_open_us=START, last_bar_open_us=END-period*U, last_bar_close_us=END, last_bar_usable_before_cutoff=False), "manifest candle claims")
            verified_files[relative] = dict(expected_file, rows=count, exact_volume_sum=decimal_text(total))
            sums[period] = total
            if period == 14400:higher[period] = values4
        require(len(set(sums.values())) == 1, "cross-period total volume")
        expected_total = "487594990078" if symbol == "BTC_USDT" else "147845325893.4"
        require(decimal_text(sums[3600]) == expected_total, "independent selected total")
        fractional = sum(r["values"][-1].denominator != 1 for r in hourly)
        require(fractional == (0 if symbol == "BTC_USDT" else 4106), "selected fractional-hour count")
        stats[symbol] = dict(hourly_rows=len(hourly), fractional_volume_hours=fractional, exact_volume_sum=expected_total,
                             source_prefix_rows=25560, decimal_suffix_rows=7296)
        print("QR008 exact: " + symbol + " all three grids verified in both roots", flush=True)
    discrepancy_bytes = b"".join(canonical(r)+b"\n" for r in differences)
    for root in roots:
        actual = pinned(root/"source-discrepancies.jsonl", files["source-discrepancies.jsonl"]["sha256"])
        require(actual == discrepancy_bytes and len(actual) == files["source-discrepancies.jsonl"]["bytes"], "complete discrepancy tuples/refs/bytes")
        # Producer checks are hashed for inventory only, never acceptance inputs.
        checks = pinned(root/"candidate-checks.json", files["candidate-checks.json"]["sha256"])
        require(len(checks) == files["candidate-checks.json"]["bytes"], "producer checks size")
    require(sha(discrepancy_bytes) == manifest["source_discrepancies_sha256"], "discrepancy manifest identity")
    checkpoint["phase"] = "complete"
    return dict(status="PASS_WITH_DISCLOSED_RETROSPECTIVE_SOURCE_LIMITATIONS", checker_sha256=sha(Path(__file__).read_bytes()),
                specification_sha256=SPEC_SHA, approval_sha256=APPROVAL_SHA, builder_commit=BUILDER_COMMIT,
                manifest_sha256=list(MANIFEST_SHAS), roots=list(map(str,roots)), input_catalog_sha256=catalog_hash,
                raw_files_verified=fingerprints, raw_archives=90, raw_rest_bulk=8, raw_confirmations=4,
                candidates_verified=2, rows_per_candidate=84878, candles=verified_files, symbols=stats,
                discrepancies=dict(hours=len(differences), fields=sum(len(r["fields"]) for r in differences),
                                   sha256=sha(discrepancy_bytes), full_tuple_file=str(roots[0]/"source-discrepancies.jsonl")),
                payloads_identical=9, historical_first_availability="UNKNOWN", historical_revisions="UNKNOWN",
                market_required_queries="NOT_EVALUATED", training_ready=False, market_requests=0, model_fits=0,
                elapsed_seconds=round(time.monotonic()-started,3))


def publish_new(directory, filename, value):
    directory = Path(directory).absolute()
    require(not any(p.is_symlink() for p in (directory, *directory.parents)), "output symlink")
    require(directory.is_dir(), "output directory missing")
    body = canonical(value)+b"\n"
    existing = sum(p.stat().st_size for p in directory.parent.glob("verification-*/*") if p.is_file())
    require(existing + len(body) <= 16*1024*1024, "combined QR008 audit output budget")
    with (directory/filename).open("xb") as stream:
        stream.write(body)
    return sha(body)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec",required=True,type=Path);parser.add_argument("--approval",required=True,type=Path)
    parser.add_argument("--candidate",required=True,type=Path);parser.add_argument("--reproduction",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    require(args.output.name in {"verification-exact-1","verification-exact-2"},"at most two explicit real-check destinations")
    require(args.output.parent.absolute()==Path(__file__).absolute().parents[1]/".data"/"qr008","audit output scope")
    args.output.mkdir(parents=True,exist_ok=False)
    checkpoint={};started=time.monotonic()
    try:
        with offline(),bounded():result=verify_pair(args.spec,args.approval,[args.candidate,args.reproduction],checkpoint)
    except Exception as exc:
        result=dict(status="REVISE",error_type=type(exc).__name__,detail=str(exc),checkpoint=checkpoint,
                    elapsed_seconds=round(time.monotonic()-started,3),training_ready=False,market_requests=0,model_fits=0)
    identity=publish_new(args.output,"result.json",result)
    print(json.dumps(dict(status=result["status"],sha256=identity,path=str(args.output/"result.json"),detail=result.get("detail"))))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
