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
    if item["http_status"] not in (200, 206):
        return [], False  # Retained failed attempt; never eligible lineage.
    payload = path.read_bytes()
    if len(payload) != item["bytes"]:
        raise ValueError("raw byte length mismatch")
    if len(payload) > spec["intake_budget"]["max_compressed_bytes_per_file"]:
        raise ValueError("raw file exceeds byte limit")
    if item["http_status"] == 206:
        headers = {k.lower(): str(v) for k, v in item.get("response_headers", {}).items()}
        match = re.fullmatch(r"bytes 0-(\d+)/(\d+)", headers.get("content-range", ""))
        if not match or int(match[1])+1 != len(payload) or int(match[2]) != len(payload):
            # Intentionally partial source probes may be retained, never consumed.
            if item.get("complete_object") is False:
                return [], False
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
    payload = json.loads(payload)
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
    quarantine = []
    for item in manifest["quarantine_files"]:
        try:
            required(item, contract["quarantine_required_fields"])
            path = inside(root, item["path"], "quarantine")
            if sha256(path) != item["sha256"] or not set(item["source_ids"]).issubset(all_sources):
                raise ValueError("quarantine hash/source mismatch")
            quarantine.append(item)
        except (ValueError, TypeError, KeyError, OSError) as error:
            issues.append(f"quarantine {item.get('path')}: {error}")
    # Raw overlapping records are checked independently of collector assertions.
    seen = defaultdict(set)
    for identity, rows in raw.values():
        if identity[1] in ("candles", "funding"):
            for row in rows:
                if start <= row[0] < end:
                    seen[identity[:3]+(row[0],)].add(row[1:])
    conflicts = [{"symbol": k[0], "kind": k[1], "interval_seconds": k[2], "timestamp": k[3],
                  "versions": len(v)} for k, v in sorted(seen.items()) if len(v) > 1]
    if conflicts:
        issues.append(f"{len(conflicts)} raw source conflicts require explicit resolution; no automatic preference")
    return {"schema_version": 1, "dataset_id": manifest["dataset_id"],
            "manifest_sha256": sha256(manifest_path), "spec_sha256": sha256(spec_path),
            "structural_status": "FAIL" if issues else "PASS",
            "training_status": "NOT_READY", "issues": issues,
            "remaining_gates": ["attempt budget and retained failure ledger review",
                "historical funding schedule, metadata and duplicate lineage review",
                "native full warmup; permitted baseline labels, maturity and dependence",
                "human training protocol/precision/holdout acceptance and fresh confirmation"],
            "raw_files": len(all_sources), "complete_sources": len(raw), "raw_bytes": total_bytes,
            "normalized": normalized, "cross_interval": qc, "source_conflicts": conflicts,
            "quarantine": quarantine, "limitations": manifest["limitations"]}


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
