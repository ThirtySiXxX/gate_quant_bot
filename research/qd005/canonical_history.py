"""Frozen-spec, offline-only canonical hourly v2 builder and disk verifier.

No runtime, exchange, replay or model imports. A failed build leaves its fresh
root for inspection; it never resumes, replaces or removes existing outputs.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

SPEC_SHA256 = "a516075cd2baced65dd659b520c6495d2cdf9d539ff8a1bfa2570c93ccfb63a4"
SPEC_COMMIT = "e1b459434e32e585e8a57d46b4bfedb0e79d7f67"
SYMBOLS = ["BTC_USDT", "ETH_USDT"]
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "available_at"]
CANDLE_COLUMNS = COLUMNS + ["source_id", "source_row"]
FUNDING_COLUMNS = ["timestamp", "funding_rate", "available_at", "source_id", "source_row"]
CANDLE_UNITS = {"timestamp": "UTC_unix_seconds", "price": "USDT_per_base", "volume": "contracts"}
FUNDING_UNITS = {"timestamp": "UTC_unix_seconds", "funding_rate": "fraction_per_settlement"}
CANDLE_AVAILABILITY = "open_plus_interval_proxy_not_observed_arrival"
FUNDING_AVAILABILITY = "source_settlement_proxy_not_observed_arrival"


class HistoryError(ValueError):
    pass


def digest(body):
    return hashlib.sha256(body).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read_json(body):
    def pairs(items):
        result = dict(items)
        if len(result) != len(items):
            raise HistoryError("duplicate JSON key")
        return result
    def invalid(value):
        raise HistoryError("nonfinite JSON constant: " + value)
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def root_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise HistoryError("symlink in root path")
    return path.resolve()


def safe_path(root, relative):
    root = root_path(root)
    rel = PurePosixPath(relative)
    if (not relative or rel.is_absolute() or ".." in rel.parts
            or "\\" in relative or str(rel) != relative or relative == "."):
        raise HistoryError("unsafe relative path: " + relative)
    path = root.joinpath(*rel.parts)
    if any(p.is_symlink() for p in (path, *path.parents) if p != root):
        raise HistoryError("symlink in dataset path")
    return path


def load_spec(path):
    body = Path(path).read_bytes()
    if digest(body) != SPEC_SHA256:
        raise HistoryError("unapproved specification hash")
    spec = read_json(body)
    if (spec["schema_version"] != 2 or spec["protocol_id"] != "canonical_hourly_v2-r1"
            or spec["scope"]["symbols"] != SYMBOLS
            or spec["budget"]["max_baseline_replays_per_coin"] != 0):
        raise HistoryError("unsupported scope or replay permission")
    return spec


def checked_body(root, entry):
    body = safe_path(root, entry["path"]).read_bytes()
    if digest(body) != entry["sha256"]:
        raise HistoryError("file hash mismatch: " + entry["path"])
    return body


def load_base(root, spec):
    """Recheck all frozen raw/normalized/quarantine bytes, without modifying v1."""
    base = spec["base"]
    original = read_json(checked_body(root, dict(path="manifest.json", sha256=base["manifest_sha256"])))
    reviewed = read_json(checked_body(root, dict(path="candidate-reviewed.json", sha256=base["candidate_reviewed_sha256"])))
    if (original["dataset_id"] != base["dataset_id"] or original["symbols"] != SYMBOLS
            or original["data_range"] != data_range(spec)):
        raise HistoryError("base identity/scope mismatch")
    seen = {}
    for entry in reviewed["raw_files"] + reviewed["normalized_files"] + reviewed["quarantine_files"]:
        if entry["path"] in seen:
            raise HistoryError("duplicate base file identity")
        seen[entry["path"]] = entry["sha256"]
        checked_body(root, entry)
    for rel, sha in base["input_sha256"].items():
        if seen.get(rel) != sha:
            raise HistoryError("base descriptor differs from frozen input: " + rel)
    disagreements = read_json(safe_path(root, "quarantine/cross-interval-disagreements.json").read_bytes())
    if len(disagreements) != 2068:
        raise HistoryError("original disagreement evidence missing")
    return reviewed


def data_range(spec):
    return dict(start=spec["calendar"]["raw_start"], end_exclusive=spec["calendar"]["raw_end_exclusive"])


def integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise HistoryError("expected nonnegative integer string")
    return int(value)


def number(value):
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HistoryError("invalid decimal") from exc
    if not result.is_finite():
        raise HistoryError("nonfinite decimal")
    return result


def fixed(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def csv_rows(body, columns):
    reader = csv.DictReader(io.StringIO(body.decode("utf-8"), newline=""), strict=True)
    if reader.fieldnames != columns:
        raise HistoryError("CSV columns mismatch")
    rows = list(reader)
    if any(set(row) != set(columns) or any(v is None for v in row.values()) for row in rows):
        raise HistoryError("CSV row width mismatch")
    return rows


def hourly_rows(body, start, end):
    rows = csv_rows(body, CANDLE_COLUMNS)
    if start % 86400 or end % 3600 or end <= start or len(rows) != (end - start) // 3600:
        raise HistoryError("incomplete hourly range or invalid boundaries")
    result = []
    for i, row in enumerate(rows):
        t = integer(row["timestamp"])
        if t != start + i * 3600 or integer(row["available_at"]) != t + 3600:
            raise HistoryError("missing/duplicate/shifted hour or availability")
        values = [number(row[k]) for k in COLUMNS[1:6]]
        o, h, low, c, v = values
        if min(o, h, low, c) <= 0 or low > min(o, c) or h < max(o, c) or low > h:
            raise HistoryError("invalid OHLC")
        if v < 0 or v != int(v):
            raise HistoryError("volume must be integral nonnegative contracts")
        if not row["source_id"] or integer(row["source_row"]) < 1:
            raise HistoryError("missing raw provenance")
        result.append(dict(timestamp=t, values=values, available_at=t + 3600))
    return result


def funding_rows(body, start, end):
    rows = csv_rows(body, FUNDING_COLUMNS)
    previous = start - 1
    for row in rows:
        t = integer(row["timestamp"])
        number(row["funding_rate"])
        if not start <= t < end or t <= previous or integer(row["available_at"]) != t:
            raise HistoryError("funding time/availability/order mismatch")
        if not row["source_id"] or integer(row["source_row"]) < 1:
            raise HistoryError("missing funding provenance")
        previous = t
    if not rows or integer(rows[0]["timestamp"]) != start:
        raise HistoryError("funding start coverage missing")
    return rows


def aggregate(hours, seconds, start, end):
    """Pure deterministic derivation; callers supply a validated contiguous grid."""
    if seconds not in (14400, 86400):
        raise HistoryError("unsupported derived interval")
    if len(hours) != (end - start) // 3600 or any(
            r["timestamp"] != start + i * 3600 or r["available_at"] != start + (i + 1) * 3600
            for i, r in enumerate(hours)):
        raise HistoryError("invalid ordered children")
    width = seconds // 3600
    complete = len(hours) // width
    rows, lineage = [], []
    for i in range(complete):
        children = hours[i * width:(i + 1) * width]
        t = start + i * seconds
        # Price selection is exact Decimal comparison; integral volumes use Python
        # integer summation, independent of ambient Decimal precision/traps.
        values = [children[0]["values"][0], max(c["values"][1] for c in children),
                  min(c["values"][2] for c in children), children[-1]["values"][3]]
        volume = sum(int(c["values"][4]) for c in children)
        rows.append([str(t), *map(fixed, values), str(volume), str(max(c["available_at"] for c in children))])
        lineage.append(dict(normalized_row=i + 1, timestamp=t,
                            parent_rows=list(range(i * width + 1, (i + 1) * width + 1))))
    tail = None
    if len(hours) % width:
        t = start + complete * seconds
        tail = dict(interval_seconds=seconds, timestamp=t, end_exclusive=t + seconds,
                    available_parent_rows=list(range(complete * width + 1, len(hours) + 1)),
                    unavailable_hours=(t + seconds - end) // 3600,
                    reason="cutoff_before_bucket_close")
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    refs = b"".join((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode() for r in lineage)
    return out.getvalue().encode(), refs, complete, tail


def plan(base_root, spec, base):
    """Return the eight normalized and four lineage payloads, with descriptors."""
    start, end = spec["calendar"]["raw_start"], spec["calendar"]["raw_end_exclusive"]
    by_path = {e["path"]: e for e in base["normalized_files"]}
    payloads, files, tails = {}, [], []
    for symbol in SYMBOLS:
        parent = f"normalized/{symbol}-3600s.csv"
        hourly = checked_body(base_root, by_path[parent])
        hours = hourly_rows(hourly, start, end)
        for suffix, seconds, kind, columns, units, availability in (
                ("3600s", 3600, "candles", CANDLE_COLUMNS, CANDLE_UNITS, CANDLE_AVAILABILITY),
                ("funding", 0, "funding", FUNDING_COLUMNS, FUNDING_UNITS, FUNDING_AVAILABILITY)):
            path = f"normalized/{symbol}-{suffix}.csv"
            entry = by_path[path]
            body = checked_body(base_root, entry)
            count = len(hours) if kind == "candles" else len(funding_rows(body, start, end))
            if entry["columns"] != columns or entry["units"] != units or entry["rows"] != count or entry["availability_basis"] != availability:
                raise HistoryError("frozen copy descriptor mismatch")
            payloads[path] = body
            files.append(dict(symbol=symbol, kind=kind, interval_seconds=seconds,
                path=path, sha256=digest(body), rows=count, columns=columns, units=units,
                availability_basis=availability, derivation=dict(method="copy_frozen_bytes",
                    parent_path=path, parent_sha256=digest(body))))
        for seconds in (14400, 86400):
            body, lineage, count, tail = aggregate(hours, seconds, start, end)
            path = f"normalized/{symbol}-{seconds}s.csv"
            lp = f"lineage/{symbol}-{seconds}s.jsonl"
            payloads[path], payloads[lp] = body, lineage
            files.append(dict(symbol=symbol, kind="candles", interval_seconds=seconds,
                path=path, sha256=digest(body), rows=count, columns=COLUMNS, units=CANDLE_UNITS,
                availability_basis=CANDLE_AVAILABILITY,
                derivation=dict(method="utc_ohlcv_from_frozen_hourly", parent_path=parent,
                    parent_sha256=digest(hourly), lineage_path=lp,
                    lineage_sha256=digest(lineage), lineage_rows=count)))
            if tail:
                tails.append(dict(symbol=symbol, **tail))
    return payloads, files, tails


def build(spec_path, base_root, output_root, builder_commit):
    spec = load_spec(spec_path)
    base_root, output_root = root_path(base_root), root_path(output_root)
    if base_root == output_root or base_root in output_root.parents or output_root in base_root.parents:
        raise HistoryError("output must be separate from frozen base")
    if output_root.exists():
        raise HistoryError("output root already exists")
    if not re.fullmatch(r"[0-9a-f]{40}", builder_commit):
        raise HistoryError("builder commit must be an exact Git SHA")
    base = load_base(base_root, spec)
    payloads, files, tails = plan(base_root, spec, base)
    manifest = dict(schema_version=2, protocol_id=spec["protocol_id"],
        dataset_id="gate-btc-eth-canonical-hourly-qd005-v2", created_at=datetime.now(timezone.utc).isoformat(),
        spec_sha256=SPEC_SHA256, spec_commit=SPEC_COMMIT,
        base_manifest_sha256=spec["base"]["manifest_sha256"],
        candidate_reviewed_sha256=spec["base"]["candidate_reviewed_sha256"],
        symbols=SYMBOLS, data_range=data_range(spec), files=files, withheld_buckets=tails,
        network_attempts=0, model_fits=0, baseline_replays=0,
        builder_sha256=digest(Path(__file__).read_bytes()), builder_commit=builder_commit,
        limitations=spec["limitations"] + ["Unaccepted candidate pending independent QR validation; G3 BLOCKED; zero baseline replays."])
    output_root.mkdir()  # Exclusive creation; a competing builder cannot overwrite.
    for relative, body in {**payloads, "manifest.json": json_bytes(manifest)}.items():
        path = safe_path(output_root, relative)
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as handle:
            handle.write(body)
    return manifest


def verify(spec_path, base_root, output_root, manifest_sha256):
    """Disk reread/recomputation, not a substitute for QR's independent validator."""
    spec = load_spec(spec_path)
    base = load_base(base_root, spec)
    body = safe_path(output_root, "manifest.json").read_bytes()
    if digest(body) != manifest_sha256:
        raise HistoryError("candidate manifest hash mismatch")
    manifest = read_json(body)
    payloads, files, tails = plan(base_root, spec, base)
    expected = dict(schema_version=2, protocol_id=spec["protocol_id"],
        dataset_id="gate-btc-eth-canonical-hourly-qd005-v2", spec_sha256=SPEC_SHA256,
        spec_commit=SPEC_COMMIT, base_manifest_sha256=spec["base"]["manifest_sha256"],
        candidate_reviewed_sha256=spec["base"]["candidate_reviewed_sha256"],
        symbols=SYMBOLS, data_range=data_range(spec), files=files, withheld_buckets=tails,
        network_attempts=0, model_fits=0, baseline_replays=0,
        builder_sha256=digest(Path(__file__).read_bytes()),
        limitations=spec["limitations"] + ["Unaccepted candidate pending independent QR validation; G3 BLOCKED; zero baseline replays."])
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise HistoryError("candidate manifest semantics mismatch")
    if datetime.fromisoformat(manifest["created_at"]).utcoffset() is None or not re.fullmatch(r"[0-9a-f]{40}", manifest["builder_commit"]):
        raise HistoryError("invalid creation provenance")
    for rel, expected_body in payloads.items():
        if safe_path(output_root, rel).read_bytes() != expected_body:
            raise HistoryError("candidate bytes differ from frozen derivation: " + rel)
    actual = set()
    for path in root_path(output_root).rglob("*"):
        if path.is_symlink():
            raise HistoryError("unexpected symlink in candidate")
        if path.is_file():
            actual.add(path.relative_to(root_path(output_root)).as_posix())
    if actual != set(payloads) | {"manifest.json"}:
        raise HistoryError("unexpected candidate file inventory")
    return dict(status="PASS_LOCAL_DISK_RECOMPUTATION", manifest_sha256=manifest_sha256,
                normalized_files=len(files), lineage_files=4,
                normalized_rows=sum(f["rows"] for f in files),
                lineage_rows=sum(f["derivation"].get("lineage_rows", 0) for f in files),
                independent_qr_acceptance="PENDING", G3="BLOCKED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--builder-commit")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args()
    if args.mode == "build":
        repo = Path(__file__).resolve().parents[2]
        if not args.builder_commit:
            parser.error("build requires --builder-commit")
        committed = subprocess.check_output(["git", "show", args.builder_commit + ":research/qd005/canonical_history.py"], cwd=repo)
        if committed != Path(__file__).read_bytes():
            raise HistoryError("builder differs from committed code")
        manifest = build(args.spec, args.base, args.output, args.builder_commit)
        print(digest(json_bytes(manifest)))
    else:
        if not args.manifest_sha256:
            parser.error("verify requires --manifest-sha256")
        print(json.dumps(verify(args.spec, args.base, args.output, args.manifest_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
