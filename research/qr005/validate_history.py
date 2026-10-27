"""Independent offline v2 acceptance. Never imports QD's builder or trains.

The caller supplies two explicit roots. V1 remains an immutable source/evidence
tree, and V2 is a new derived dataset. A data PASS is not label/training approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal
import json
from pathlib import Path

from research.qr004.validate_history import (
    canonical, candle_quality, inside, integer, number, required, sha256,
    utc_time, validate_dataset as validate_v1,
)


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def decimal_text(value):
    value = number(value)
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def read_csv(path, columns):
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        demand(reader.fieldnames == columns, "CSV columns/order differ")
        rows = list(reader)
    demand(all(set(r) == set(columns) and None not in r.values() for r in rows),
           "malformed CSV width")
    return rows


def verify_hours(rows, start, end):
    tuples = [canonical(row, "candles") for row in rows]
    problems = candle_quality(tuples, 3600, start, end)["problems"]
    demand(not problems, "hourly coverage/OHLCV: " + "; ".join(problems))
    for row in rows:
        t = integer(row["timestamp"])
        demand(integer(row["available_at"]) == t+3600, "hourly availability differs")
        demand(number(row["volume"]) == integer(row["volume"]), "fractional contract volume")
    return tuples


def reference_buckets(rows, seconds, start, end):
    """QR reference: time-addressed children from the ORIGINAL frozen hourly file.

    This function does not normalize a candidate or repair inputs. Its outputs are
    transient expectations for comparisons; tests may use short synthetic rows.
    """
    demand(seconds in (14400, 86400), "unsupported derived interval")
    demand(start % seconds == 0 and end % 3600 == 0, "unaligned dataset range")
    values = verify_hours(rows, start, end)
    by_time = {row[0]: (i, row) for i, row in enumerate(values, 1)}
    expected = []
    for t in range(start, end-seconds+1, seconds):
        children = [by_time[x] for x in range(t, t+seconds, 3600)]
        points = [x[1] for x in children]
        expected.append({"timestamp": t, "open": points[0][1],
            "high": max(x[2] for x in points), "low": min(x[3] for x in points),
            "close": points[-1][4], "volume": Decimal(sum(int(x[5]) for x in points)),
            "available_at": t+seconds, "parent_rows": [x[0] for x in children]})
    tail = None
    if end % seconds:
        t = end//seconds*seconds
        tail = {"interval_seconds": seconds, "timestamp": t,
            "end_exclusive": t+seconds,
            "available_parent_rows": [by_time[x][0] for x in range(t, end, 3600)],
            "unavailable_hours": (t+seconds-end)//3600,
            "reason": "cutoff_before_bucket_close"}
    return expected, tail


def check_derived(rows, lineage, expected):
    demand(len(rows) == len(lineage) == len(expected), "derived/lineage row count differs")
    for i, (row, origin, reference) in enumerate(zip(rows, lineage, expected), 1):
        for key in ("timestamp", "open", "high", "low", "close", "volume", "available_at"):
            demand(number(row[key]) == reference[key], f"derived {key} mismatch at row {i}")
            demand(row[key] == decimal_text(reference[key]), f"noncanonical {key} encoding")
        demand(set(origin) == {"normalized_row", "timestamp", "parent_rows"}, "lineage fields differ")
        demand(type(origin["normalized_row"]) is int and type(origin["timestamp"]) is int
               and isinstance(origin["parent_rows"], list)
               and all(type(x) is int for x in origin["parent_rows"]), "lineage indices must be integers")
        demand(origin == {"normalized_row": i, "timestamp": reference["timestamp"],
                          "parent_rows": reference["parent_rows"]}, "lineage child identity/order differs")


def funding_diagnostics(rows, start, end):
    timestamps = [integer(row["timestamp"]) for row in rows]
    demand(timestamps == sorted(set(timestamps)), "funding order/duplicates")
    demand(all(start <= t < end for t in timestamps), "funding outside frozen range")
    for row in rows:
        number(row["funding_rate"])
        demand(integer(row["available_at"]) == integer(row["timestamp"]), "funding timestamp shifted")
    slots = Counter(t//28800*28800 for t in timestamps)
    return {"rows": len(rows), "nominal_reference_seconds": 28800,
        "offset_seconds_counts": dict(sorted(Counter(t % 28800 for t in timestamps).items())),
        "inter_event_seconds_counts": dict(sorted(Counter(b-a for a, b in zip(timestamps, timestamps[1:])).items())),
        "missing_reference_slots": sorted(set(range(start, end, 28800))-set(slots)),
        "duplicate_reference_slots": [t for t, count in slots.items() if count > 1],
        "authoritative_historical_schedule_proven": False}


def verify_base(base_root, spec, qr_root):
    demand(sha256(base_root/"manifest.json") == spec["base"]["manifest_sha256"], "base manifest hash mismatch")
    demand(sha256(base_root/"candidate-reviewed.json") == spec["base"]["candidate_reviewed_sha256"],
           "base supplement hash mismatch")
    for name, digest in spec["evidence_sha256"].items():
        demand(sha256(inside(qr_root, name)) == digest, "frozen QR evidence hash mismatch: "+name)
    base = json.loads((base_root/"manifest.json").read_text())
    demand(base["dataset_id"] == spec["base"]["dataset_id"], "wrong base dataset")
    for name, digest in spec["base"]["input_sha256"].items():
        demand(sha256(inside(base_root, name, "normalized")) == digest, "base input hash mismatch: "+name)
    for group in ("raw_files", "normalized_files", "quarantine_files"):
        for item in base[group]:
            demand(sha256(inside(base_root, item["path"])) == item["sha256"], "base artifact changed")
    supplement = json.loads((base_root/"candidate-reviewed.json").read_text())
    for item in supplement.get("quarantine_files", []):
        demand(sha256(inside(base_root, item["path"])) == item["sha256"], "base diagnostic changed")
    old = validate_v1(base_root, base_root/"manifest.json", qr_root/"research/qr004/data-acceptance.json")
    # Explicitly retain v1's failed result. Only its previously reviewed four
    # cross-stream disagreements are expected; any new issue fails this phase.
    demand(old["issues"] == spec["base"]["expected_v1_issues"], "v1 evidence/issue set changed")
    return base, {"v1_structural_status": old["structural_status"],
        "preserved_native_issues": old["issues"], "raw_files_verified": old["raw_files"],
        "raw_coverage": old["raw_coverage"], "new_raw_integrity_issues": []}


def inspect_candidate(root, base_root, spec, spec_hash, base):
    manifest = json.loads((root/"manifest.json").read_text())
    required(manifest, spec["manifest_required"])
    demand(type(manifest["schema_version"]) is int and manifest["schema_version"] == 2, "wrong schema version")
    demand(manifest["protocol_id"] == spec["protocol_id"] and manifest["spec_sha256"] == spec_hash,
           "protocol/spec hash differs")
    demand(isinstance(manifest["dataset_id"], str) and manifest["dataset_id"]
           and manifest["dataset_id"] != base["dataset_id"], "candidate needs new dataset identity")
    utc_time(manifest["created_at"])
    demand(manifest["base_manifest_sha256"] == spec["base"]["manifest_sha256"], "candidate base identity differs")
    demand(manifest["symbols"] == spec["scope"]["symbols"], "candidate universe differs")
    start, end = (spec["calendar"][k] for k in ("raw_start", "raw_end_exclusive"))
    demand(manifest["data_range"] == {"start": start, "end_exclusive": end}, "candidate range differs")
    for field in ("network_attempts", "model_fits"):
        demand(type(manifest[field]) is int and manifest[field] == 0, "nonzero/invalid "+field)
    demand(isinstance(manifest["limitations"], list) and manifest["limitations"], "missing limitations")
    expected_keys = {(s, kind, seconds) for s in spec["scope"]["symbols"]
        for kind, seconds in (("candles", 3600), ("candles", 14400), ("candles", 86400), ("funding", 0))}
    files, paths = {}, set()
    for entry in manifest["files"]:
        required(entry, spec["file_required"])
        demand(type(entry["interval_seconds"]) is int, "interval must be integer")
        key = (entry["symbol"], entry["kind"], entry["interval_seconds"])
        demand(key in expected_keys and key not in files, "duplicate/unexpected file identity")
        path = inside(root, entry["path"], "normalized")
        demand(path not in paths, "aliased output file")
        paths.add(path)
        demand(sha256(path) == entry["sha256"], "candidate file hash mismatch")
        prefix = "funding" if key[1] == "funding" else "candle"
        columns = (spec["derived_columns"] if key[2] in (14400, 86400)
                   else spec["normalization"][prefix+"_columns"])
        demand(entry["columns"] == columns, "descriptor columns differ")
        units = ({"timestamp": "UTC_unix_seconds", "funding_rate": "fraction_per_settlement"}
                 if prefix == "funding" else {"timestamp": "UTC_unix_seconds", "price": "USDT_per_base", "volume": "contracts"})
        demand(entry["units"] == units, "units differ")
        demand(entry["availability_basis"] == spec["normalization"][prefix+"_available_at"], "availability basis differs")
        rows = read_csv(path, columns)
        if key[2] in (14400, 86400):
            payload = path.read_bytes()
            demand(b"\r" not in payload and payload.endswith(b"\n"), "derived CSV requires LF endings")
        demand(type(entry["rows"]) is int and entry["rows"] == len(rows), "descriptor row count differs")
        files[key] = (entry, rows)
    demand(set(files) == expected_keys, "missing required file identity")
    base_files = {(x["symbol"], x["kind"], x["interval_seconds"]): x
                  for x in base["normalized_files"]}
    tails, counts, funding, native_counts = [], {}, {}, {}
    for symbol in spec["scope"]["symbols"]:
        original_hours = None
        for kind, interval in (("candles", 3600), ("funding", 0)):
            key = (symbol, kind, interval)
            entry, rows = files[key]
            parent = base_files[key]
            demand(entry["path"] == parent["path"], "copy destination path differs from frozen identity")
            demand(entry["derivation"] == {"method": "copy_frozen_bytes", "parent_path": parent["path"],
                "parent_sha256": parent["sha256"]}, "copy lineage differs")
            demand((root/entry["path"]).read_bytes() == (base_root/parent["path"]).read_bytes(), "copied input differs")
            if kind == "candles":
                original_hours = read_csv(base_root/parent["path"], parent["columns"])
                verify_hours(original_hours, start, end)
            else:
                funding[symbol] = funding_diagnostics(rows, start, end)
        coarse = {}
        for seconds in (14400, 86400):
            entry, rows = files[(symbol, "candles", seconds)]
            parent = base_files[(symbol, "candles", 3600)]
            derivation = entry["derivation"]
            demand(set(derivation) == {"method", "parent_path", "parent_sha256", "lineage_path", "lineage_sha256", "lineage_rows"}, "derived lineage descriptor differs")
            demand(derivation["method"] == "utc_ohlcv_from_frozen_hourly" and
                derivation["parent_path"] == parent["path"] and derivation["parent_sha256"] == parent["sha256"], "wrong derivation parent")
            path = inside(root, derivation["lineage_path"], "lineage")
            demand(path not in paths, "aliased lineage file")
            paths.add(path)
            demand(sha256(path) == derivation["lineage_sha256"], "lineage hash mismatch")
            lineage = [json.loads(line) for line in path.read_text().splitlines()]
            demand(type(derivation["lineage_rows"]) is int and derivation["lineage_rows"] == len(lineage), "lineage count differs")
            expected, tail = reference_buckets(original_hours, seconds, start, end)
            check_derived(rows, lineage, expected)
            if tail:
                tails.append(dict(symbol=symbol, **tail))
            coarse[seconds] = rows
            counts[f"{symbol}:{seconds}"] = len(rows)
            native = base_files[(symbol, "candles", seconds)]
            originals = read_csv(base_root/native["path"], native["columns"])
            demand(len(originals) == len(rows), "native diagnostic membership changed")
            native_counts[f"{symbol}:{seconds}"] = sum(canonical(a, "candles") != canonical(b, "candles")
                                                       for a, b in zip(rows, originals))
        four = {integer(r["timestamp"]): canonical(r, "candles") for r in coarse[14400]}
        for day in coarse[86400]:
            t = integer(day["timestamp"])
            children = [four[x] for x in range(t, t+86400, 14400)]
            expected_day = (t, children[0][1], max(x[2] for x in children), min(x[3] for x in children),
                            children[-1][4], Decimal(sum(int(x[5]) for x in children)))
            demand(canonical(day, "candles") == expected_day, "4h to daily identity fails")
    tail_key = lambda row: (row["symbol"], row["interval_seconds"])
    demand(sorted(manifest["withheld_buckets"], key=tail_key) == sorted(tails, key=tail_key), "withheld tail accounting differs")
    return {"derived_rows": counts, "exact_child_lineage_rows": sum(counts.values()),
        "withheld_buckets": tails, "preserved_native_disagreement_counts": native_counts,
        "funding": funding, "candidate_files": len(files), "network_attempts": 0, "model_fits": 0}


def validate_dataset(root, base_root, spec_path):
    root, base_root = Path(root).resolve(strict=True), Path(base_root).resolve(strict=True)
    demand(root != base_root and not root.is_relative_to(base_root), "candidate must be separate from base")
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text())
    qr_root = Path(__file__).resolve().parents[2]
    base, provenance = verify_base(base_root, spec, qr_root)
    checks = inspect_candidate(root, base_root, spec, sha256(spec_path), base)
    return {"schema_version": 2, "protocol_id": spec["protocol_id"],
        "spec_sha256": sha256(spec_path), "manifest_sha256": sha256(root/"manifest.json"),
        "data_status": "PASS_WITH_LIMITATIONS", "training_status": "NOT_READY",
        "baseline_replays": 0, "model_fits": 0, "issues": [],
        "provenance": provenance, "checks": checks, "limitations": spec["limitations"],
        "remaining_gates": ["explicit replay funding/cost compatibility and label assessment",
            "prospective holdout, economic effect and precision plan", "fresh human permission before training"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--base-root", required=True)
    parser.add_argument("--spec", default="research/qr005/data-acceptance.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    demand(not output.exists(), "output exists; evidence is immutable")
    report = validate_dataset(args.root, args.base_root, args.spec)
    with output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
