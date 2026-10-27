"""Offline adversarial tests for history acceptance, not profitability tests."""
import copy
import csv
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from research.qr004.validate_history import (candle_quality, funding_quality, inside,
    number, raw_rows, sha256, source_identity, validate_dataset)


class HistoryAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for directory in ("raw", "normalized", "quarantine"):
            (self.root / directory).mkdir()
        original = Path(__file__).resolve().parents[2] / "research/qr004/data-acceptance.json"
        self.spec = json.loads(original.read_text())
        self.start = self.spec["calendar"]["raw_start"]
        self.end = self.start + 2*86400
        self.spec["calendar"]["raw_end_exclusive"] = self.end
        self.spec_path = self.root / "spec.json"
        self.spec_path.write_text(json.dumps(self.spec))
        self.manifest = dict(schema_version=1, dataset_id="synthetic-only",
            created_at="2026-10-28T00:00:00Z", spec_sha256=sha256(self.spec_path),
            data_range={"start": self.start, "end_exclusive": self.end},
            symbols=["BTC_USDT", "ETH_USDT"], raw_files=[], normalized_files=[],
            quarantine_files=[], quality_summary={}, limitations=["synthetic short fixture"])
        for symbol in self.manifest["symbols"]:
            for interval, seconds in (("1h", 3600), ("4h", 14400), ("1d", 86400), (None, 0)):
                kind = "candles" if seconds else "funding"
                key = f"{symbol}-{interval or kind}"
                raw = ([dict(t=t, o="100", h="102", l="99", c="101", v=seconds//3600)
                        for t in range(self.start, self.end, seconds)] if seconds else
                       [dict(t=t+1, r="0.0001") for t in range(self.start, self.end, 28800)])
                path = self.root / "raw" / (key+".json")
                path.write_text(json.dumps(raw))
                url = (f"https://api.gateio.ws/api/v4/futures/usdt/"
                       f"{'candlesticks' if seconds else 'funding_rate'}?contract={symbol}")
                if seconds:
                    url += "&interval="+interval
                self.manifest["raw_files"].append(dict(source_id=key, path=str(path.relative_to(self.root)),
                    sha256=sha256(path), bytes=path.stat().st_size, url=url,
                    retrieved_at="2026-10-28T00:00:00Z", http_status=200, format="json"))
                prefix = "candle" if seconds else "funding"
                columns = self.spec["normalization"][prefix+"_columns"]
                rows = []
                for index, raw_row in enumerate(raw, 1):
                    row = dict(timestamp=raw_row["t"], available_at=raw_row["t"]+seconds,
                               source_id=key, source_row=index)
                    row.update(dict(open=100, high=102, low=99, close=101, volume=seconds//3600)
                               if seconds else dict(funding_rate="0.0001"))
                    rows.append(row)
                normalized_path = self.root / "normalized" / (key+".csv")
                item = dict(symbol=symbol, kind=kind, interval_seconds=seconds,
                    path=str(normalized_path.relative_to(self.root)), columns=columns,
                    source_ids=[key], availability_basis=self.spec["normalization"][prefix+"_available_at"],
                    units=dict(timestamp="UTC_unix_seconds", price="USDT_per_base", volume="contracts")
                    if seconds else dict(timestamp="UTC_unix_seconds", funding_rate="fraction_per_settlement"))
                self.write_normalized(item, rows)
                self.manifest["normalized_files"].append(item)

    def write_normalized(self, item, rows):
        path = self.root / item["path"]
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=item["columns"])
            writer.writeheader()
            writer.writerows(rows)
        item.update(sha256=sha256(path), rows=len(rows), start_ts=int(rows[0]["timestamp"]),
                    end_ts=int(rows[-1]["timestamp"]))

    def rows(self, item):
        with (self.root/item["path"]).open(newline="") as stream:
            return list(csv.DictReader(stream))

    def audit(self):
        path = self.root / "manifest.json"
        path.write_text(json.dumps(self.manifest))
        return validate_dataset(self.root, path, self.spec_path)

    def assert_issue(self, fragment):
        result = self.audit()
        self.assertEqual(result["structural_status"], "FAIL")
        self.assertTrue(any(fragment in issue for issue in result["issues"]), result["issues"])
        self.assertEqual(result["training_status"], "NOT_READY")

    def test_clean_fixture_is_structural_only_not_training_permission(self):
        result = self.audit()
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["structural_status"], "PASS")
        self.assertEqual(result["training_status"], "NOT_READY")
        self.assertEqual(result["complete_sources"], 8)
        self.assertEqual(result["normalized"][3]["first"], self.start+1)

    def test_modified_raw_hash_rejected(self):
        item = self.manifest["raw_files"][0]
        (self.root/item["path"]).write_text("[]")
        self.assert_issue("raw hash mismatch")

    def test_rehashed_forged_normalization_fails_lineage(self):
        item = self.manifest["normalized_files"][0]
        rows = self.rows(item)
        rows[0]["close"] = "101.5"
        self.write_normalized(item, rows)
        self.assert_issue("does not equal referenced raw")

    def test_advanced_availability_rejected(self):
        item = self.manifest["normalized_files"][0]
        rows = self.rows(item)
        rows[0]["available_at"] = rows[0]["timestamp"]
        self.write_normalized(item, rows)
        self.assert_issue("availability advanced")

    def test_deleted_candle_reports_exact_missing_slot(self):
        item = self.manifest["normalized_files"][0]
        rows = self.rows(item)
        missing = int(rows.pop(5)["timestamp"])
        self.write_normalized(item, rows)
        result = self.audit()
        self.assertEqual(result["normalized"][0]["missing"], [missing])
        self.assertEqual(result["structural_status"], "FAIL")

    def test_normalized_duplicates_rejected_even_if_identical(self):
        item = self.manifest["normalized_files"][0]
        rows = self.rows(item)
        rows.insert(1, rows[0].copy())
        self.write_normalized(item, rows)
        self.assert_issue("not unique")

    def test_conflicting_raw_overlap_detected_independently(self):
        original = self.manifest["raw_files"][0]
        extra = copy.deepcopy(original)
        extra.update(source_id="conflicting-source", path="raw/conflict.json")
        payload = json.loads((self.root/original["path"]).read_text())
        payload[0]["c"] = "101.5"
        path = self.root/extra["path"]
        path.write_text(json.dumps(payload))
        extra.update(sha256=sha256(path), bytes=path.stat().st_size)
        self.manifest["raw_files"].append(extra)
        self.assert_issue("raw source conflicts")

    def test_mark_price_cannot_masquerade_as_trade_candles(self):
        self.manifest["raw_files"][0]["url"] = self.manifest["raw_files"][0]["url"].replace("BTC_USDT", "mark_BTC_USDT")
        self.assert_issue("unapproved API instrument")

    def test_volume_unit_and_source_row_cannot_drift(self):
        item = self.manifest["normalized_files"][0]
        item["units"]["volume"] = "base_coin"
        self.assert_issue("units/availability")
        item["units"]["volume"] = "contracts"
        rows = self.rows(item)
        rows[0]["source_row"] = "0"
        self.write_normalized(item, rows)
        self.assert_issue("does not equal referenced raw")

    def test_traversal_and_symlink_escape_rejected(self):
        with self.assertRaises(ValueError):
            inside(self.root, "../outside")
        (self.root/"raw/escape").symlink_to(self.root.parent)
        with self.assertRaises(ValueError):
            inside(self.root, "raw/escape", "raw")

    def test_cross_interval_difference_is_not_repaired(self):
        item, source = self.manifest["normalized_files"][1], self.manifest["raw_files"][1]
        rows = self.rows(item)
        rows[0]["volume"] = "5"
        self.write_normalized(item, rows)
        path = self.root/source["path"]
        payload = json.loads(path.read_text())
        payload[0]["v"] = 5
        path.write_text(json.dumps(payload))
        source.update(sha256=sha256(path), bytes=path.stat().st_size)
        self.assert_issue("cross-interval mismatches")
        self.assertEqual(self.rows(item)[0]["volume"], "5")

    def test_invalid_ohlcv_offgrid_and_nan(self):
        result = candle_quality([(self.start+1, 100, 90, 99, 101, -1)], 3600, self.start, self.end)
        self.assertTrue(any("invalid OHLCV" in p for p in result["problems"]))
        self.assertTrue(any("off-grid" in p for p in result["problems"]))
        with self.assertRaises(ValueError):
            number("NaN")

    def test_funding_offsets_and_variable_intervals_are_not_rounded(self):
        rows = [(self.start+1, number("0.01")), (self.start+28802, number("-0.0003")),
                (self.start+43201, number("0"))]
        result = funding_quality(rows, self.start, self.end)
        self.assertEqual(result["inter_settlement_seconds"], {14399: 1, 28801: 1})
        self.assertTrue(result["schedule_status"].startswith("UNPROVEN"))

    def test_archive_full_and_truncated_gzip(self):
        url = "https://download.gatedata.org/futures_usdt/funding_applies/202301/BTC_USDT-202301.csv.gz"
        identity = source_identity(url, self.spec)
        path = self.root / "raw/archive.gz"
        full = gzip.compress(f"{self.start+1},-0.00010\n".encode())
        path.write_bytes(full)
        item = dict(http_status=200, bytes=len(full))
        rows, complete = raw_rows(path, item, identity, self.spec)
        self.assertTrue(complete)
        self.assertEqual(rows, [(self.start+1, number("-0.00010"))])
        path.write_bytes(full[:-6])
        item["bytes"] -= 6
        with self.assertRaises((EOFError, OSError)):
            raw_rows(path, item, identity, self.spec)

    def test_206_requires_complete_object_or_is_ineligible_probe(self):
        source = self.manifest["raw_files"][0]
        path = self.root/source["path"]
        identity = source_identity(source["url"], self.spec)
        source["http_status"] = 206
        with self.assertRaises(ValueError):
            raw_rows(path, source, identity, self.spec)
        source["complete_object"] = False
        self.assertEqual(raw_rows(path, source, identity, self.spec), ([], False))
        source["response_headers"] = {"Content-Range": f"bytes 0-{source['bytes']-1}/{source['bytes']}"}
        self.assertTrue(raw_rows(path, source, identity, self.spec)[1])

    def test_manifest_universe_and_spec_drift_fail_closed(self):
        self.manifest["symbols"].append("SOL_USDT")
        with self.assertRaisesRegex(ValueError, "universe"):
            self.audit()
        self.manifest["symbols"].pop()
        self.manifest["spec_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "spec hash"):
            self.audit()


if __name__ == "__main__":
    unittest.main()
