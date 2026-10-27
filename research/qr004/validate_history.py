"""Independent, offline QR004 history audit. Reads immutable QD files; never fits.

Successful structural validation is not training permission. Funding schedule,
native full warmup and usable labels still need separate evidence. No repairs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
import zlib


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inside(root, name, partition=None):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("unsafe relative path")
    if partition and relative.parts[0] != partition:
        raise ValueError(f"file outside {partition} partition")
    resolved = (root / relative).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("path escapes root or is not a file")
    return resolved


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("invalid numeric value") from error
    if not result.is_finite():
        raise ValueError("nonfinite numeric value")
    return result


def integer(value):
    result = number(value)
    if result != result.to_integral_value():
        raise ValueError("nonintegral timestamp/index")
    return int(result)


def required(item, fields):
    missing = set(fields) - item.keys()
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")


def utc_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("retrieval timestamp lacks timezone")
    return parsed.timestamp()


def source_identity(url, spec):
    """Infer product/type from exact official source route, not local filenames."""
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in spec["sources"]["allowed_hosts"]
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("unapproved source origin")
    if parsed.hostname == "download.gatedata.org":
        match = re.fullmatch(r"/futures_usdt/(candlesticks_(1h|4h|1d)|funding_applies)/(\d{6})/(BTC_USDT|ETH_USDT)-\3.csv.gz", parsed.path)
        if not match or parsed.query:
            raise ValueError("unapproved archive product/type/symbol")
        if not "202301" <= match[3] <= spec["sources"]["archive_last_full_month"] or not 1 <= int(match[3][-2:]) <= 12:
            raise ValueError("archive month outside authorized range")
        kind = "funding" if match[1] == "funding_applies" else "candles"
        seconds = spec["scope"]["intervals_seconds"].get(match[2], 0)
        return match[4], kind, seconds, "archive"
    query = parse_qs(parsed.query)
    if parsed.path not in spec["sources"]["api_public_routes"]:
        raise ValueError("unapproved API route")
    if "/contracts/" in parsed.path:
        symbol, kind, seconds = parsed.path.rsplit("/", 1)[-1], "contract_metadata", 0
    else:
        symbols = query.get("contract", [])
        if len(symbols) != 1 or symbols[0] not in spec["scope"]["symbols"]:
            raise ValueError("unapproved API instrument")
        symbol = symbols[0]
        kind = {"candlesticks": "candles", "funding_rate": "funding",
                "risk_limit_tiers": "risk_tiers"}[parsed.path.rsplit("/", 1)[-1]]
        intervals = query.get("interval", [])
        seconds = spec["scope"]["intervals_seconds"].get(intervals[0], 0) if len(intervals) == 1 else 0
        if kind == "candles" and not seconds:
            raise ValueError("unapproved candle interval")
    return symbol, kind, seconds, "api"


def canonical(row, kind):
    fields = ("open", "high", "low", "close", "volume") if kind == "candles" else ("funding_rate",)
    return (integer(row["timestamp"]),) + tuple(number(row[field]) for field in fields)


def raw_rows(path, item, identity, spec):
    """Verify complete objects and independently parse official native schemas."""
    symbol, kind, seconds, route = identity
    if item["http_status"] not in (200, 206) or item.get("accepted") is False or item.get("complete_object") is False:
        return [], False  # Retained failed attempt; never eligible lineage.
    payload = path.read_bytes()
    if len(payload) != item["bytes"]:
        raise ValueError("raw byte length mismatch")
    if len(payload) > spec["intake_budget"]["max_compressed_bytes_per_file"]:
        raise ValueError("raw file exceeds byte limit")
    headers = {k.lower(): str(v) for k, v in item.get("response_headers", {}).items()}
    if "content-length" in headers and integer(headers["content-length"]) != len(payload):
        raise ValueError("HTTP Content-Length differs from saved bytes")
    if item["http_status"] == 206:
        match = re.fullmatch(r"bytes 0-(\d+)/(\d+)", headers.get("content-range", ""))
        if not match or int(match[1])+1 != len(payload) or int(match[2]) != len(payload):
            raise ValueError("partial/unknown 206 object completeness")
    if route == "archive":
        cap = spec["intake_budget"]["max_uncompressed_bytes_per_file"]
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
            expanded = stream.read(cap+1)  # EOF forces CRC verification.
        if len(expanded) > cap:
            raise ValueError("archive expansion limit exceeded")
        cells = list(csv.reader(io.StringIO(expanded.decode("utf-8-sig"))))
        if not cells:
            raise ValueError("empty archive")
        headers = (["timestamp", "size", "close", "high", "low", "open"]
                   if kind == "candles" else ["timestamp", "funding_rate"])
        if cells[0] == headers:
            cells = cells[1:]
        rows = []
        for cell in cells:
            if len(cell) != len(headers):
                raise ValueError("archive row width mismatch")
            row = dict(zip(headers, cell))
            if kind == "candles":
                row["volume"] = row.pop("size")
            rows.append(canonical(row, kind))
        return rows, True
    payload = json.loads(payload, parse_float=Decimal)
    if kind not in ("candles", "funding"):
        return payload, True
    if not isinstance(payload, list):
        raise ValueError("expected public API row list")
    rows = []
    for item in payload:
        row = ({"timestamp": item["t"], "open": item["o"], "high": item["h"],
                "low": item["l"], "close": item["c"], "volume": item["v"]}
               if kind == "candles" else {"timestamp": item["t"], "funding_rate": item["r"]})
        rows.append(canonical(row, kind))
    return rows, True


def candle_quality(rows, seconds, start, end):
    expected = set(range(start, end-seconds+1, seconds))
    observed = [row[0] for row in rows]
    problems = []
    if observed != sorted(set(observed)):
        problems.append("timestamps not unique and strictly increasing")
    for t, op, hi, lo, cl, vol in rows:
        if t % seconds or t < start or t+seconds > end:
            problems.append(f"off-grid/out-of-range/unclosed candle: {t}")
        if min(op, hi, lo, cl) <= 0 or vol < 0 or not lo <= min(op, cl) <= max(op, cl) <= hi:
            problems.append(f"invalid OHLCV: {t}")
    missing = sorted(expected - set(observed))
    if missing:
        problems.append(f"missing {len(missing)} expected candle slots")
    outliers = []
    for previous, current in zip(rows, rows[1:]):
        if previous[4] > 0 and abs(current[4]/previous[4]-1) > Decimal("0.30"):
            outliers.append(current[0])
    return {"rows": len(rows), "expected_rows": len(expected), "missing": missing,
            "problems": problems, "large_close_changes_to_verify": outliers}


def funding_quality(rows, start, end):
    times = [row[0] for row in rows]
    problems = []
    if times != sorted(set(times)):
        problems.append("funding timestamps not unique/increasing")
    if any(t < start or t >= end for t in times):
        problems.append("funding timestamp outside frozen range")
    durations = Counter(b-a for a, b in zip(times, times[1:]))
    return {"rows": len(rows), "first": min(times) if times else None,
            "last": max(times) if times else None,
            "inter_settlement_seconds": dict(sorted(durations.items())),
            "problems": problems,
            "schedule_status": "UNPROVEN: durations alone do not establish historical schedule",
            "rates_abs_over_one_percent": [r[0] for r in rows if abs(r[1]) > Decimal("0.01")]}


def cross_interval(hourly, native, seconds):
    by_time = {r[0]: r for r in hourly}
    mismatches, incomplete = [], []
    for actual in native:
        t = actual[0]
        small = [by_time.get(s) for s in range(t, t+seconds, 3600)]
        if any(row is None for row in small):
            incomplete.append(t)
            continue
        aggregate = (t, small[0][1], max(r[2] for r in small), min(r[3] for r in small),
                     small[-1][4], sum(r[5] for r in small))
        # Decimal exact equality preserves raw prices/counts without float drift.
        if aggregate != actual:
            mismatches.append({"timestamp": t, "fields": [field for field, a, b in zip(
                ("timestamp", "open", "high", "low", "close", "volume"), aggregate, actual) if a != b]})
    return {"compared": len(native)-len(incomplete), "incomplete": incomplete, "mismatches": mismatches}


def native_warmup(frames, cfg, decision_at, funding_interval):
    """Inspect the original indicators at the first scored decision, without replay.

    A nominal funding interval is an explicit caller assumption, never inferred
    from today's contract. This diagnostic cannot prove historical completeness.
    """
    import numpy as np
    from src import carry, trend, vol
    from src.crypto_ml import causal_features

    if cfg.ml_model_path:
        raise ValueError("warmup must have ML disabled")
    if funding_interval <= 0:
        raise ValueError("funding interval must be explicitly positive")
    periods = {"1h": 3600, "4h": 14400, "1d": 86400}
    clipped = {interval: frames[interval][frames[interval].timestamp+seconds <= decision_at].reset_index(drop=True)
               for interval, seconds in periods.items()}
    findings, checks = {}, []
    for interval in ("1h", "4h"):
        frame = clipped[interval]
        if frame.empty:
            raise ValueError("empty warmup frame")
        i = len(frame)-1
        raw_counts = []
        for fast, slow in cfg.ewmac_horizons:
            raw = trend.ewmac_raw(frame.close, fast, slow, interval, cfg.ewma_lambda)
            count = int(np.isfinite(raw.iloc[max(0, i-cfg.forecast_scale_lookback):i]).sum())
            raw_counts.append({"fast": fast, "slow": slow, "finite_prior_raw": count})
            checks.append(count == cfg.forecast_scale_lookback and np.isfinite(raw.iloc[i]))
        sub = trend.compute_ewmac_group(frame.close, interval, cfg)
        previous_sub = sub.shift(1).iloc[max(0, i-cfg.fdm_lookback+1):i+1]
        fdm_count = int(np.isfinite(previous_sub).all(axis=1).sum())
        native_last = float(trend.group_trend_forecast(frame.close, interval, cfg).iloc[-1])
        contiguous = bool((frame.timestamp.diff().dropna() == periods[interval]).all())
        exactly_closed = int(frame.timestamp.iloc[-1])+periods[interval] == decision_at
        checks.extend((fdm_count == cfg.fdm_lookback, np.isfinite(native_last), contiguous, exactly_closed))
        findings[interval] = {"closed_bars": len(frame), "last_open": int(frame.timestamp.iloc[-1]),
            "trend_raw_counts": raw_counts, "required_raw": cfg.forecast_scale_lookback,
            "fdm_prior_complete_rows": fdm_count, "required_fdm": cfg.fdm_lookback,
            "native_trend_finite": bool(np.isfinite(native_last)), "contiguous": contiguous,
            "exactly_closed_at_start": exactly_closed}
    main = clipped["4h"]
    rates = carry.align_funding_to_bars(frames["funding"], main.timestamp)
    ann_vol = vol.price_vol_annualized(main.close, "4h", cfg.ewma_lambda)
    raw_carry = -rates * (365*86400/funding_interval) / ann_vol.replace(0, np.nan)
    i = len(main)-1
    count = int(np.isfinite(raw_carry.iloc[max(0, i-cfg.carry_scale_lookback):i]).sum())
    native_carry = carry.carry_forecast_series_from_history(main.close, "4h", frames["funding"],
        funding_interval, cfg, bar_timestamps=main.timestamp)
    carry_finite = bool(np.isfinite(native_carry.iloc[-1]))
    checks.extend((count == cfg.carry_scale_lookback, carry_finite))
    findings["carry"] = {"finite_prior_raw": count, "required": cfg.carry_scale_lookback,
        "native_finite": carry_finite, "interval_assumption_seconds": funding_interval,
        "schedule_proven": False}
    day = clipped["1d"]
    day_count = len(day)
    day_contiguous = bool((day.timestamp.diff().dropna() == 86400).all())
    checks.extend((day_count >= cfg.regime_ema_long+5, day_contiguous))
    findings["daily"] = {"closed_bars": day_count, "required": cfg.regime_ema_long+5,
                          "contiguous": day_contiguous}
    features = causal_features(clipped["1h"])
    feature_finite = bool(np.isfinite(features.iloc[-1]).all())
    checks.append(feature_finite)
    findings["ml_features"] = {"native_last_vector_finite": feature_finite, "fits": 0}
    return {"decision_at": decision_at, "full_windows_at_start": bool(all(checks)),
            "findings": findings, "training_permission": False,
            "limitations": ["EMA initialization approximate", "funding schedule requires independent evidence",
                            "first decision only; all scored inputs checked separately"]}


def validate_dataset(root, manifest_path, spec_path):
    root = Path(root).resolve(strict=True)
    spec_path, manifest_path = Path(spec_path), Path(manifest_path)
    spec, manifest = json.loads(spec_path.read_text()), json.loads(manifest_path.read_text())
    contract = spec["manifest_contract"]
    required(manifest, contract["required_root_fields"])
    if manifest["schema_version"] != 1 or manifest["spec_sha256"] != sha256(spec_path):
        raise ValueError("manifest version/spec hash mismatch")
    if manifest["symbols"] != spec["scope"]["symbols"]:
        raise ValueError("manifest universe mismatch")
    start, end = (spec["calendar"][k] for k in ("raw_start", "raw_end_exclusive"))
    if manifest["data_range"] != {"start": start, "end_exclusive": end}:
        raise ValueError("manifest calendar mismatch")
    issues, raw, all_sources, data, normalized = [], {}, {}, {}, []
    normalized_origins = {}
    total_bytes = 0
    for item in manifest["raw_files"]:
        try:
            required(item, contract["raw_required_fields"])
            utc_time(item["retrieved_at"])
            sid = item["source_id"]
            if sid in all_sources:
                raise ValueError("duplicate source_id")
            all_sources[sid] = item
            path = inside(root, item["path"], "raw")
            if sha256(path) != item["sha256"]:
                raise ValueError("raw hash mismatch")
            if path.stat().st_size != item["bytes"]:
                raise ValueError("raw byte count mismatch")
            total_bytes += path.stat().st_size
            identity = source_identity(item["url"], spec)
            rows, complete = raw_rows(path, item, identity, spec)
            if complete:
                raw[sid] = (identity, rows)
        except (ValueError, KeyError, TypeError, OSError, EOFError, zlib.error) as error:
            issues.append(f"raw {item.get('path')}: {error}")
    if total_bytes > spec["intake_budget"]["max_total_compressed_bytes"]:
        issues.append("total byte budget exceeded")
    for item in manifest["normalized_files"]:
        try:
            required(item, contract["normalized_required_fields"])
            symbol, kind, seconds = item["symbol"], item["kind"], item["interval_seconds"]
            if symbol not in spec["scope"]["symbols"] or kind not in contract["kind_values"]:
                raise ValueError("normalized universe/type mismatch")
            path = inside(root, item["path"], "normalized")
            if sha256(path) != item["sha256"]:
                raise ValueError("normalized hash mismatch")
            if not item["source_ids"] or not set(item["source_ids"]).issubset(raw):
                raise ValueError("normalized source missing/incomplete")
            if kind not in ("candles", "funding"):
                if len(item["source_ids"]) != 1:
                    raise ValueError("metadata needs one exact source snapshot")
                sid = item["source_ids"][0]
                identity, payload = raw[sid]
                envelope = json.loads(path.read_text(), parse_float=Decimal)
                observed = utc_time(all_sources[sid]["retrieved_at"])
                if (identity[:2] != (symbol, kind) or envelope["source_id"] != sid
                        or envelope["data"] != payload or envelope["historical_effective_at"] is not None
                        or utc_time(envelope["observed_at"]) != observed
                        or item["availability_basis"] != "current_snapshot_not_historical"
                        or item["historical_effective_at"] is not None
                        or utc_time(item["observed_at"]) != observed
                        or item["start_ts"] != observed or item["end_ts"] != observed
                        or item["rows"] != 1 or item["columns"] != [] or item["units"] != {}):
                    raise ValueError("metadata snapshot lineage/backdating mismatch")
                normalized.append({"symbol": symbol, "kind": kind,
                    "status": "CURRENT_METADATA_ONLY; historical effective time independently unproven"})
                continue
            if seconds not in (3600, 14400, 86400) and kind == "candles":
                raise ValueError("normalized candle interval mismatch")
            units = ({"timestamp": "UTC_unix_seconds", "price": "USDT_per_base", "volume": "contracts"}
                     if kind == "candles" else {"timestamp": "UTC_unix_seconds", "funding_rate": "fraction_per_settlement"})
            prefix = "candle" if kind == "candles" else "funding"
            if item["units"] != units or item["availability_basis"] != spec["normalization"][prefix+"_available_at"]:
                raise ValueError("units/availability semantics mismatch")
            with path.open(newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != spec["normalization"][prefix+"_columns"] or item["columns"] != reader.fieldnames:
                    raise ValueError("normalized column order/schema mismatch")
                values = list(reader)
            rows = [canonical(row, kind) for row in values]
            if len(rows) != item["rows"] or not rows:
                raise ValueError("normalized count mismatch/empty file")
            if item["start_ts"] != rows[0][0] or item["end_ts"] != rows[-1][0]:
                raise ValueError("normalized observed bounds mismatch")
            for row, parsed in zip(values, rows):
                sid, index = row["source_id"], integer(row["source_row"])-1
                if sid not in item["source_ids"] or sid not in raw:
                    raise ValueError("unresolved row source")
                identity, source_rows = raw[sid]
                if identity[:3] != (symbol, kind, seconds if kind == "candles" else 0):
                    raise ValueError("row provenance has wrong instrument/type/interval")
                if index < 0 or index >= len(source_rows) or parsed != source_rows[index]:
                    raise ValueError("row does not equal referenced raw values")
                if integer(row["available_at"]) != parsed[0]+(seconds if kind == "candles" else 0):
                    raise ValueError("availability advanced or altered")
                normalized_origins[(symbol, kind, seconds if kind == "candles" else 0, parsed[0])] = {
                    "source_id": sid, "source_row": index+1, "path": item["path"]}
            key = symbol, kind, seconds if kind == "candles" else 0
            if key in data:
                raise ValueError("multiple normalized files for same logical stream")
            data[key] = rows
            quality = candle_quality(rows, seconds, start, end) if kind == "candles" else funding_quality(rows, start, end)
            normalized.append({"symbol": symbol, "kind": kind, "interval_seconds": seconds, **quality})
            issues.extend(f"{key}: {p}" for p in quality["problems"])
        except (ValueError, KeyError, TypeError, OSError) as error:
            issues.append(f"normalized {item.get('path')}: {error}")
    qc = []
    for symbol in spec["scope"]["symbols"]:
        for kind, seconds in (("candles", 3600), ("candles", 14400), ("candles", 86400), ("funding", 0)):
            if (symbol, kind, seconds) not in data:
                issues.append(f"missing normalized stream {symbol} {kind} {seconds}")
        for seconds in (14400, 86400):
            if (symbol, "candles", 3600) in data and (symbol, "candles", seconds) in data:
                result = cross_interval(data[symbol, "candles", 3600], data[symbol, "candles", seconds], seconds)
                qc.append({"symbol": symbol, "interval_seconds": seconds, **result})
                if result["mismatches"]:
                    issues.append(f"{symbol} {seconds}: {len(result['mismatches'])} cross-interval mismatches require source review")
    quarantine, quarantine_payloads = [], {}
    for item in manifest["quarantine_files"]:
        try:
            required(item, contract["quarantine_required_fields"])
            path = inside(root, item["path"], "quarantine")
            if sha256(path) != item["sha256"] or not set(item["source_ids"]).issubset(all_sources):
                raise ValueError("quarantine hash/source mismatch")
            payload = json.loads(path.read_text(), parse_float=Decimal)
            if not isinstance(payload, list) or len(payload) != item["rows"]:
                raise ValueError("quarantine count/type mismatch")
            quarantine_payloads[item["reason"]] = payload
            quarantine.append(item)
        except (ValueError, TypeError, KeyError, OSError) as error:
            issues.append(f"quarantine {item.get('path')}: {error}")
    # Raw overlapping records are checked independently of collector assertions.
    seen = defaultdict(set)
    references = defaultdict(list)
    boundary_excluded = Counter()
    for sid, (identity, rows) in raw.items():
        if identity[1] in ("candles", "funding"):
            for index, row in enumerate(rows, 1):
                if start <= row[0] < end and (identity[1] != "candles" or row[0]+identity[2] <= end):
                    key = identity[:3]+(row[0],)
                    seen[key].add(row[1:])
                    references[key].append({"source_id": sid, "source_row": index})
                else:
                    boundary_excluded[sid] += 1
    normalized_keys = {key+(row[0],) for key, rows in data.items() for row in rows}
    missing_raw = [{"symbol": k[0], "kind": k[1], "interval_seconds": k[2], "timestamp": k[3],
                    "raw_references": references[k]} for k in sorted(seen) if k not in normalized_keys]
    if missing_raw:
        issues.append(f"{len(missing_raw)} eligible raw record origins absent from normalization; explicit quarantine accountability required")
    conflicts = [{"symbol": k[0], "kind": k[1], "interval_seconds": k[2], "timestamp": k[3],
                  "versions": len(v)} for k, v in sorted(seen.items()) if len(v) > 1]
    if conflicts:
        issues.append(f"{len(conflicts)} raw source conflicts require explicit resolution; no automatic preference")
    accountability = quarantine_accountability(quarantine_payloads, raw, references,
        seen, normalized_origins, start, end)
    issues.extend(accountability["issues"])
    return {"schema_version": 1, "dataset_id": manifest["dataset_id"],
            "manifest_sha256": sha256(manifest_path), "spec_sha256": sha256(spec_path),
            "structural_status": "FAIL" if issues else "PASS",
            "training_status": "NOT_READY", "issues": issues,
            "remaining_gates": ["attempt budget and retained failure ledger review",
                "historical funding schedule, metadata and duplicate lineage review",
                "native full warmup; permitted baseline labels, maturity and dependence",
                "human training protocol/precision/holdout acceptance and fresh confirmation"],
            "raw_files": len(all_sources), "complete_sources": len(raw), "raw_bytes": total_bytes,
            "raw_coverage": {"eligible_unique_origins": len(seen),
                "normalized_unique_origins": len(normalized_keys), "omitted_origins": missing_raw,
                "duplicate_origins": sum(len(refs) > 1 for refs in references.values()),
                "boundary_excluded_raw_rows": dict(boundary_excluded)},
            "normalized": normalized, "cross_interval": qc, "source_conflicts": conflicts,
            "quarantine": quarantine, "quarantine_accountability": accountability,
            "limitations": manifest["limitations"]}


def quarantine_accountability(payloads, raw, references, seen, normalized, start, end):
    """Verify the reviewed QD lineage adapter against independently parsed values."""
    problems, duplicate_keys, conflict_keys, excluded_refs = [], set(), set(), set()

    def key_of(record):
        return (record["symbol"], record["kind"], record["interval_seconds"] or 0, integer(record["timestamp"]))

    def refs_of(refs):
        result = {(r["source_id"], integer(r["source_row"])) for r in refs}
        if len(result) != len(refs):
            raise ValueError("duplicate provenance reference")
        return result

    def referenced_value(ref):
        sid, index = ref[0], ref[1]-1
        identity, rows = raw[sid]
        if identity[1] not in ("candles", "funding") or index < 0 or index >= len(rows):
            raise ValueError("quarantine reference outside parsed rows")
        return identity, rows[index]

    for record in payloads.get("identical_duplicate_provenance", []):
        try:
            key, values = key_of(record), tuple(number(v) for v in record["values"])
            refs = refs_of(record["references"])
            if (key in duplicate_keys or len(refs) < 2 or len(seen[key]) != 1
                    or refs != refs_of(references[key]) or values[0] != key[3]
                    or values[1:] not in seen[key] or record["destination"] != normalized.get(key)
                    or record["resolution"] != "deduplicated_identical"):
                raise ValueError("duplicate lineage does not account for exact raw origins/destination")
            duplicate_keys.add(key)
        except (ValueError, TypeError, KeyError) as error:
            problems.append(f"duplicate lineage: {error}")
    for key in references:
        if len(references[key]) > 1 and len(seen[key]) == 1 and key not in duplicate_keys:
            problems.append(f"missing complete duplicate lineage: {key}")
    for record in payloads.get("all_conflicting_versions", []):
        try:
            key = key_of(record)
            all_refs, variants = set(), set()
            for variant in record["variants"]:
                values = tuple(number(v) for v in variant["values"])
                refs = refs_of(variant["references"])
                if values in variants or all_refs & refs or values[0] != key[3]:
                    raise ValueError("repeated/misaligned conflict variant")
                for ref in refs:
                    identity, actual = referenced_value(ref)
                    if identity[:3]+(actual[0],) != key or actual != values:
                        raise ValueError("conflict variant differs from raw source")
                variants.add(values)
                all_refs |= refs
            if (key in conflict_keys or len(variants) < 2 or all_refs != refs_of(references[key])
                    or {v[1:] for v in variants} != seen[key] or key in normalized
                    or record["resolution"] != "quarantined_all_versions"):
                raise ValueError("conflicting origins not all retained/excluded")
            conflict_keys.add(key)
        except (ValueError, TypeError, KeyError) as error:
            problems.append(f"conflict quarantine: {error}")
    for key, variants in seen.items():
        if len(variants) > 1 and key not in conflict_keys:
            problems.append(f"missing complete conflict quarantine: {key}")
    for record in payloads.get("invalid_or_excluded_rows", []):
        try:
            ref = record["source_id"], integer(record["source_row"])
            identity, actual = referenced_value(ref)
            outside = actual[0] < start or actual[0] >= end or (identity[1] == "candles" and actual[0]+identity[2] > end)
            if (ref in excluded_refs or tuple(number(v) for v in record["values"]) != actual
                    or record["reason"] != "outside_global_closed_range" or not outside):
                raise ValueError("exclusion needs independent reason review; not a validated boundary exclusion")
            excluded_refs.add(ref)
        except (ValueError, TypeError, KeyError) as error:
            problems.append(f"row exclusion: {error}")
    expected_excluded = {(sid, i) for sid, (identity, rows) in raw.items() if identity[1] in ("candles", "funding")
        for i, row in enumerate(rows, 1) if row[0] < start or row[0] >= end or (identity[1] == "candles" and row[0]+identity[2] > end)}
    if excluded_refs != expected_excluded:
        problems.append("raw boundary exclusions not fully accounted for")
    return {"issues": problems, "verified_duplicate_origins": len(duplicate_keys),
            "verified_conflict_origins": len(conflict_keys), "verified_boundary_exclusions": len(excluded_refs),
            "other_exclusions": "block until independent reason review; never silently accepted"}


def sealed_diagnostics(root, spec_path, phase_a_fixture, probe_root):
    """Reproduce QR004 offline transport, discrepancy and warmup diagnostics.

    No strategy replay, training, repairs, tolerance acceptance or network use.
    Funding offsets below describe a fixed reference grid, not a proven schedule.
    """
    import pandas as pd
    from src.config import SystematicConfig
    from datetime import timezone

    root, probe_root = Path(root), Path(probe_root)
    spec = json.loads(Path(spec_path).read_text())
    manifest = json.loads((root/"manifest.json").read_text())
    plan = json.loads((root/"plan.json").read_text())
    events = [json.loads(line) for line in (root/"attempts.jsonl").read_text().splitlines()]
    prior = json.loads((probe_root/"probe-ledger.json").read_text())
    if sha256(probe_root/"probe-ledger.json") != manifest["prior_probe_ledger_sha256"]:
        raise ValueError("prior probe ledger drift")
    if [r["id"] for r in prior] != list(range(1, 13)):
        raise ValueError("prior probe IDs changed")
    for probe in prior:
        path = inside(probe_root, probe["body_file"])
        if sha256(path) != probe["sha256"] or path.stat().st_size != probe["saved_bytes"]:
            raise ValueError("prior probe body drift")
        source_identity(probe["url"], spec)
        if probe["saved_bytes"] > probe["byte_cap"] or probe["method"] != "GET":
            raise ValueError("prior probe scope/cap mismatch")
    begins = [r for r in events if r["event"] == "begin"]
    ends = [r for r in events if r["event"] == "end"]
    if len(events) != 2*len(begins) or len(begins) != len(ends):
        raise ValueError("missing/unknown attempt event")
    if [r["attempt_id"] for r in begins] != list(range(13, 13+len(begins))):
        raise ValueError("attempt sequence lost/reset")
    tasks = {r["task_id"]: r for r in plan["requests"]}
    if len(tasks) != len(plan["requests"]) or plan["spec_sha256"] != sha256(spec_path):
        raise ValueError("request plan drift")
    for i, (begin, finish) in enumerate(zip(begins, ends)):
        if events[2*i] != begin or events[2*i+1] != finish:
            raise ValueError("unexpected concurrent or reordered attempt ledger")
        immutable = ("attempt_id", "source_id", "path", "task_id", "url", "params", "method", "retrieved_at", "request_headers")
        if any(begin[k] != finish[k] for k in immutable):
            raise ValueError("attempt identity changed")
        if begin["method"] != "GET" or any(k.lower() in ("authorization", "key", "sign") for k in begin["request_headers"]):
            raise ValueError("non-public request evidence")
        task = tasks[finish["task_id"]]
        if any(finish[k] != v for k, v in task.items()):
            raise ValueError("network request differs from frozen task")
        source_identity(finish["url"], spec)
    if ends != manifest["raw_files"]:
        raise ValueError("manifest omits/alters attempt ledger records")
    attempts = len(prior)+len(begins)
    byte_count = sum(r["saved_bytes"] for r in prior)+sum(r["bytes"] for r in ends)
    counts = Counter(r["task_id"] for r in ends)
    budget = spec["intake_budget"]
    if (attempts != manifest["attempts_including_probes"] or attempts > budget["max_requests"]
            or byte_count != manifest["bytes_including_probes"] or byte_count > budget["max_total_compressed_bytes"]
            or any(c > budget["max_retries_per_request"]+1 for c in counts.values())):
        raise ValueError("attempt/byte/retry accounting mismatch")
    fixture = json.loads(Path(phase_a_fixture).read_text())
    repository = Path(__file__).resolve().parents[2]
    for path, expected in fixture["source_sha256"].items():
        if sha256(repository/path) != expected:
            raise ValueError("frozen native source changed: "+path)
    output = {"schema_version": 1, "manifest_sha256": sha256(root/"manifest.json"),
        "spec_sha256": sha256(spec_path), "validator_sha256": sha256(Path(__file__)),
        "phase_a_fixture_sha256": sha256(phase_a_fixture), "network_calls_by_QR": 0,
        "attempt_audit": {"status": "PASS", "prior_probes": len(prior), "new_attempts": len(ends),
            "total_attempts": attempts, "remaining": budget["max_requests"]-attempts,
            "planned_tasks": len(tasks), "successful_tasks": len({r["task_id"] for r in ends if r["accepted"]}),
            "failed_attempts": sum(not r["accepted"] for r in ends), "bytes_including_probes": byte_count,
            "status_counts": dict(Counter(r["http_status"] for r in ends)),
            "attempt_ledger_sha256": sha256(root/"attempts.jsonl"), "plan_sha256": sha256(root/"plan.json"),
            "prior_probe_ledger_sha256": sha256(probe_root/"probe-ledger.json")},
        "cross_interval": [], "funding": {}, "native_warmup": {},
        "decision": "NOT_READY: unresolved required cross-interval inputs; zero baseline replays/model fits"}
    def utc(t):
        return datetime.fromtimestamp(t, timezone.utc).isoformat()
    for symbol in spec["scope"]["symbols"]:
        frames, raw_tables = {}, {}
        for item in manifest["normalized_files"]:
            if item["symbol"] != symbol or item["kind"] not in ("candles", "funding"):
                continue
            key = {3600: "1h", 14400: "4h", 86400: "1d"}.get(item["interval_seconds"], "funding")
            path = inside(root, item["path"], "normalized")
            if sha256(path) != item["sha256"]:
                raise ValueError("normalized source changed")
            with path.open() as stream:
                raw_tables[key] = list(csv.DictReader(stream))
            frames[key] = pd.read_csv(path)
        hourly = {integer(row["timestamp"]): row for row in raw_tables["1h"]}
        for interval, seconds in (("4h", 14400), ("1d", 86400)):
            mismatches = []
            for row in raw_tables[interval]:
                actual = canonical(row, "candles")
                t = actual[0]
                pieces = [hourly[s] for s in range(t, t+seconds, 3600)]
                parsed = [canonical(piece, "candles") for piece in pieces]
                aggregate = (t, parsed[0][1], max(r[2] for r in parsed), min(r[3] for r in parsed),
                    parsed[-1][4], sum(r[5] for r in parsed))
                if actual != aggregate:
                    fields = [field for field, a, b in zip(("timestamp", "open", "high", "low", "close", "volume"), actual, aggregate) if a != b]
                    mismatches.append({"timestamp": t, "utc": utc(t), "fields": fields,
                        "native": [str(v) for v in actual], "hourly_aggregate": [str(v) for v in aggregate],
                        "native_source": {"source_id": row["source_id"], "source_row": integer(row["source_row"])},
                        "hourly_sources": [{"source_id": p["source_id"], "source_row": integer(p["source_row"])} for p in pieces]})
            volume_delta = [number(r["native"][-1])-number(r["hourly_aggregate"][-1]) for r in mismatches if "volume" in r["fields"]]
            relative = [abs(number(r["native"][-1])-number(r["hourly_aggregate"][-1]))/number(r["hourly_aggregate"][-1])
                        for r in mismatches if "volume" in r["fields"] and number(r["hourly_aggregate"][-1]) > 0]
            output["cross_interval"].append({"symbol": symbol, "interval": interval, "compared": len(raw_tables[interval]),
                "mismatches": len(mismatches), "field_counts": dict(Counter(f for r in mismatches for f in r["fields"])),
                "first_utc": mismatches[0]["utc"] if mismatches else None, "last_utc": mismatches[-1]["utc"] if mismatches else None,
                "by_month": dict(sorted(Counter(r["utc"][:7] for r in mismatches).items())),
                "volume_native_minus_hourly": {"min_contracts": str(min(volume_delta, default=0)),
                    "max_contracts": str(max(volume_delta, default=0)),
                    "max_absolute_fraction": str(max(relative, default=0)),
                    "positive": sum(v > 0 for v in volume_delta), "negative": sum(v < 0 for v in volume_delta)},
                "records": mismatches})
        funding = raw_tables["funding"]
        times = [integer(r["timestamp"]) for r in funding]
        offsets = [t-(spec["calendar"]["raw_start"]+i*28800) for i, t in enumerate(times)]
        output["funding"][symbol] = {"records": len(times), "first": utc(times[0]), "last": utc(times[-1]),
            "reference_seconds": 28800, "reference_rule_proven": False,
            "offset_seconds_counts": dict(sorted(Counter(offsets).items())),
            "inter_event_seconds_counts": dict(sorted(Counter(b-a for a, b in zip(times, times[1:])).items())),
            "reference_slots_expected": len(range(spec["calendar"]["raw_start"], spec["calendar"]["raw_end_exclusive"], 28800)),
            "reference_slot_indices_complete_and_unique":
                [(t-spec["calendar"]["raw_start"])//28800 for t in times] == list(range(len(times))),
            "min_offset_seconds": min(offsets), "max_offset_seconds": max(offsets),
            "first_offset_utc": next((utc(t) for t, o in zip(times, offsets) if o), None),
            "last_offset_utc": next((utc(t) for t, o in reversed(list(zip(times, offsets))) if o), None),
            "timestamp_mutations": 0, "meaning": "Diagnostic fixed-grid comparison only; no rounding or schedule inference"}
        cfg = SystematicConfig.build(fixture["instruments"][symbol]["fixture"]["strategy_config"])
        output["native_warmup"][symbol] = native_warmup(frames, cfg, spec["calendar"]["baseline_start"], 28800)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--spec", type=Path, default=Path(__file__).with_name("data-acceptance.json"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = validate_dataset(args.root, args.manifest, args.spec)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"structural_status": result["structural_status"],
                      "training_status": result["training_status"], "issues": len(result["issues"])}))
    return 0 if result["structural_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
