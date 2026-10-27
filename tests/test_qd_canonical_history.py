"""Offline producer acceptance: explicit numerical oracles and adversarial inputs."""
from copy import deepcopy
import csv
from decimal import Inexact, ROUND_DOWN, localcontext
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.qd005 import canonical_history as ch


def csv_body(rows, columns=ch.CANDLE_COLUMNS):
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return out.getvalue().encode()


def candles(count=33):
    values = [(10, 13, 9, 12, 1), (12, 14, 11, 13, 2),
              (13, 15, 10, 11, 3), (11, 12, 8, 9, 4)]
    return [[i * 3600, *values[i % 4], (i + 1) * 3600, "raw-1", i + 1] for i in range(count)]


class CanonicalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def hours(self, count=33):
        return ch.hourly_rows(csv_body(candles(count)), 0, count * 3600)

    def fixture(self):
        """Tiny frozen base exercises real hashing/build IO; no production input read."""
        base = self.root / "base"
        base.mkdir()
        normalized = []
        payloads = {}
        for symbol in ch.SYMBOLS:
            for suffix, kind, seconds, columns, units, availability, body in (
                ("3600s", "candles", 3600, ch.CANDLE_COLUMNS, ch.CANDLE_UNITS,
                 ch.CANDLE_AVAILABILITY, csv_body(candles())),
                ("funding", "funding", None, ch.FUNDING_COLUMNS, ch.FUNDING_UNITS,
                 ch.FUNDING_AVAILABILITY, csv_body([
                     [t, "0.00010", t, "raw-1", i + 1]
                     for i, t in enumerate([0, 28801, 57600, 86400])], ch.FUNDING_COLUMNS))):
                path = f"normalized/{symbol}-{suffix}.csv"
                payloads[path] = body
                normalized.append(dict(path=path, sha256=ch.digest(body), symbol=symbol,
                    kind=kind, interval_seconds=seconds, rows=33 if kind == "candles" else 4,
                    columns=columns, units=units, availability_basis=availability))
        payloads["raw/input.bin"] = b"immutable synthetic raw provenance"
        payloads["quarantine/cross-interval-disagreements.json"] = ch.json_bytes([{}] * 2068)
        manifest = dict(dataset_id="fixture", symbols=ch.SYMBOLS,
            data_range=dict(start=0, end_exclusive=118800), normalized_files=normalized,
            raw_files=[dict(path="raw/input.bin", sha256=ch.digest(payloads["raw/input.bin"]))],
            quarantine_files=[dict(path="quarantine/cross-interval-disagreements.json",
                sha256=ch.digest(payloads["quarantine/cross-interval-disagreements.json"]))])
        payloads["manifest.json"] = ch.json_bytes(manifest)
        payloads["candidate-reviewed.json"] = ch.json_bytes(manifest)
        for rel, body in payloads.items():
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        spec = dict(schema_version=2, protocol_id="canonical_hourly_v2-r1",
            scope=dict(symbols=ch.SYMBOLS), budget=dict(max_baseline_replays_per_coin=0),
            calendar=dict(raw_start=0, raw_end_exclusive=118800), limitations=["synthetic"],
            base=dict(dataset_id="fixture", manifest_sha256=ch.digest(payloads["manifest.json"]),
                candidate_reviewed_sha256=ch.digest(payloads["candidate-reviewed.json"]),
                input_sha256={e["path"]: e["sha256"] for e in normalized}))
        spec_path = self.root / "spec.json"
        spec_path.write_bytes(ch.json_bytes(spec))
        patcher = patch.object(ch, "SPEC_SHA256", ch.digest(spec_path.read_bytes()))
        patcher.start()
        self.addCleanup(patcher.stop)
        return spec_path, base, spec, manifest

    def test_four_child_oracle_and_lineage(self):
        body, refs, count, tail = ch.aggregate(self.hours(4), 14400, 0, 14400)
        self.assertEqual(body, b"timestamp,open,high,low,close,volume,available_at\n0,10,15,8,9,10,14400\n")
        self.assertEqual(json.loads(refs), dict(normalized_row=1, timestamp=0, parent_rows=[1, 2, 3, 4]))
        self.assertEqual(count, 1)
        self.assertIsNone(tail)

    def test_daily_direct_equals_six_coarse_buckets(self):
        hours = self.hours(24)
        four, _, _, _ = ch.aggregate(hours, 14400, 0, 86400)
        day, refs, count, tail = ch.aggregate(hours, 86400, 0, 86400)
        coarse = list(csv.DictReader(io.StringIO(four.decode())))
        self.assertEqual(len(coarse), 6)
        self.assertTrue(all([r[k] for k in ["open", "high", "low", "close", "volume"]]
                            == ["10", "15", "8", "9", "10"] for r in coarse))
        self.assertEqual(day.splitlines()[1], b"0,10,15,8,9,60,86400")
        self.assertEqual(json.loads(refs)["parent_rows"], list(range(1, 25)))
        self.assertEqual(count, 1)
        self.assertIsNone(tail)

    def test_partial_cutoff_tail_records_every_available_parent(self):
        hours = self.hours()
        for seconds, count, parent_rows, missing in [(14400, 8, [33], 3), (86400, 1, list(range(25, 34)), 15)]:
            with self.subTest(seconds=seconds):
                _, _, actual, tail = ch.aggregate(hours, seconds, 0, 118800)
                self.assertEqual(actual, count)
                self.assertEqual(tail, dict(interval_seconds=seconds, timestamp=count * seconds,
                    end_exclusive=(count + 1) * seconds, available_parent_rows=parent_rows,
                    unavailable_hours=missing, reason="cutoff_before_bucket_close"))

    def test_missing_duplicate_shifted_reordered_or_unavailable_hour_rejected(self):
        for change in ("missing", "duplicate", "shift", "reorder", "availability"):
            rows = candles(8)
            if change == "missing": rows.pop(3)
            if change == "duplicate": rows[3] = rows[2][:]
            if change == "shift": rows[3][0] += 1
            if change == "reorder": rows[2], rows[3] = rows[3], rows[2]
            if change == "availability": rows[3][6] -= 1
            with self.subTest(change=change), self.assertRaises(ch.HistoryError):
                ch.hourly_rows(csv_body(rows), 0, 28800)

    def test_ohlcv_and_source_invalid_values_rejected(self):
        for column, value in [(1, "NaN"), (2, "Infinity"), (1, "0"), (3, "-1"),
                              (2, "11"), (3, "13"), (5, "-1"), (5, "0.1"),
                              (4, "garbage"), (7, ""), (8, "0")]:
            rows = candles(4)
            rows[0][column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ch.HistoryError):
                ch.hourly_rows(csv_body(rows), 0, 14400)

    def test_wrong_schema_width_and_range_rejected(self):
        for body, start, end in [(csv_body(candles(4), ch.CANDLE_COLUMNS[::-1]), 0, 14400),
                                 (csv_body([row + ["extra"] for row in candles(4)]), 0, 14400),
                                 (csv_body(candles(4)), 1, 14400),
                                 (csv_body(candles(4)), 0, 14401)]:
            with self.subTest(start=start, end=end), self.assertRaises(ch.HistoryError):
                ch.hourly_rows(body, start, end)

    def test_partial_interior_cannot_be_reclassified_as_cutoff(self):
        hours = self.hours()
        hours.pop(5)
        with self.assertRaises(ch.HistoryError):
            ch.aggregate(hours, 14400, 0, 118800)
        # Same count after replacing the interior missing hour with the next one.
        hours.insert(5, deepcopy(hours[5]))
        with self.assertRaises(ch.HistoryError):
            ch.aggregate(hours, 86400, 0, 118800)

    def test_decimal_precision_and_traps_do_not_round_prices_or_volume(self):
        rows = candles(4)
        price = "12345678901234567890.1234567890123456789"
        volume = "99999999999999999999999999999999999"
        for row in rows:
            row[1:6] = [price, price, price, price, volume]
        with localcontext() as context:
            context.prec = 2
            context.rounding = ROUND_DOWN
            context.traps[Inexact] = True
            parsed = ch.hourly_rows(csv_body(rows), 0, 14400)
            body, _, _, _ = ch.aggregate(parsed, 14400, 0, 14400)
        expected = ",".join(["0", price, price, price, price,
                             "399999999999999999999999999999999996", "14400"])
        self.assertEqual(body.decode().splitlines()[1], expected)

    def test_future_child_perturbation_does_not_change_closed_prefix(self):
        before = self.hours(8)
        after = deepcopy(before)
        after[4]["values"][1] = ch.number("9999")
        a = ch.aggregate(before, 14400, 0, 28800)[0].splitlines()
        b = ch.aggregate(after, 14400, 0, 28800)[0].splitlines()
        self.assertEqual(a[:2], b[:2])  # header and bar available at 04:00
        self.assertNotEqual(a[2], b[2])

    def test_funding_offsets_preserved_and_bad_time_or_rate_rejected(self):
        rows = [[0, "0.00010", 0, "raw", 1], [28801, "-0.002", 28801, "raw", 2]]
        parsed = ch.funding_rows(csv_body(rows, ch.FUNDING_COLUMNS), 0, 32400)
        self.assertEqual(parsed[1]["timestamp"], "28801")
        self.assertEqual(parsed[1]["funding_rate"], "-0.002")
        for column, value in [(0, 32400), (0, 0), (2, 28800), (1, "NaN"), (3, ""), (4, 0)]:
            bad = deepcopy(rows)
            bad[1][column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ch.HistoryError):
                ch.funding_rows(csv_body(bad, ch.FUNDING_COLUMNS), 0, 32400)
        with self.assertRaises(ch.HistoryError):
            ch.funding_rows(csv_body(rows[1:], ch.FUNDING_COLUMNS), 0, 32400)

    def test_path_traversal_noncanonical_and_symlink_rejected(self):
        for rel in ("../outside", "/absolute", "a/../../b", "a\\b", "a//b", "a/./b", "", "."):
            with self.subTest(rel=rel), self.assertRaises(ch.HistoryError):
                ch.safe_path(self.root, rel)
        (self.root / "link").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ch.HistoryError): ch.safe_path(self.root, "link/file")
        with self.assertRaises(ch.HistoryError): ch.root_path(self.root / "link")

    def test_spec_hash_must_match_exact_frozen_bytes(self):
        path, _, _, _ = self.fixture()
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ch.HistoryError, "specification hash"):
            ch.load_spec(path)

    def test_base_hash_tamper_and_duplicate_identity_rejected(self):
        _, base, spec, manifest = self.fixture()
        (base / "raw/input.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(ch.HistoryError, "hash mismatch"):
            ch.load_base(base, spec)
        (base / "raw/input.bin").write_bytes(b"immutable synthetic raw provenance")
        manifest["raw_files"].append(manifest["raw_files"][0])
        body = ch.json_bytes(manifest)
        (base / "candidate-reviewed.json").write_bytes(body)
        spec["base"]["candidate_reviewed_sha256"] = ch.digest(body)
        with self.assertRaisesRegex(ch.HistoryError, "duplicate base file"):
            ch.load_base(base, spec)

    def test_build_fresh_roots_reproducible_copies_inventory_and_verification(self):
        path, base, _, _ = self.fixture()
        first, second = self.root / "first", self.root / "second"
        a = ch.build(path, base, first, "0" * 40)
        b = ch.build(path, base, second, "0" * 40)
        self.assertEqual(a["files"], b["files"])
        self.assertEqual(len(a["files"]), 8)
        for file in first.rglob("*"):
            if file.is_file() and file.name != "manifest.json":
                self.assertEqual(file.read_bytes(), (second / file.relative_to(first)).read_bytes())
        for symbol in ch.SYMBOLS:
            for suffix in ("3600s", "funding"):
                rel = f"normalized/{symbol}-{suffix}.csv"
                self.assertEqual((base / rel).read_bytes(), (first / rel).read_bytes())
        result = ch.verify(path, base, first, ch.digest((first / "manifest.json").read_bytes()))
        self.assertEqual(result["normalized_rows"], 92)
        self.assertEqual(result["lineage_rows"], 18)
        self.assertEqual(result["G3"], "BLOCKED")
        with self.assertRaisesRegex(ch.HistoryError, "already exists"):
            ch.build(path, base, first, "0" * 40)
        with self.assertRaisesRegex(ch.HistoryError, "separate"):
            ch.build(path, base, base / "nested", "0" * 40)

    def test_rehashed_derived_corruption_and_extra_output_rejected(self):
        path, base, _, _ = self.fixture()
        out = self.root / "candidate"
        manifest = ch.build(path, base, out, "0" * 40)
        rel = "normalized/BTC_USDT-14400s.csv"
        original = (out / rel).read_bytes()
        corrupt = original.replace(b",15,8,9,10,", b",16,8,9,10,", 1)
        (out / rel).write_bytes(corrupt)
        entry = next(e for e in manifest["files"] if e["path"] == rel)
        entry["sha256"] = ch.digest(corrupt)
        (out / "manifest.json").write_bytes(ch.json_bytes(manifest))
        with self.assertRaisesRegex(ch.HistoryError, "semantics mismatch"):
            ch.verify(path, base, out, ch.digest((out / "manifest.json").read_bytes()))
        entry["sha256"] = ch.digest(original)
        (out / rel).write_bytes(original)
        (out / "manifest.json").write_bytes(ch.json_bytes(manifest))
        (out / "extra").write_bytes(b"not in inventory")
        with self.assertRaisesRegex(ch.HistoryError, "inventory"):
            ch.verify(path, base, out, ch.digest((out / "manifest.json").read_bytes()))


if __name__ == "__main__":
    unittest.main()
