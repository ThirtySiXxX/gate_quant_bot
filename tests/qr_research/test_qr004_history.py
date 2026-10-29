"""Offline adversarial tests for history acceptance, not profitability tests."""
import copy
import csv
from datetime import datetime
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.qr004.validate_history import (candle_quality, funding_quality, inside,
    native_warmup, number, raw_rows, sealed_diagnostics, sha256, source_identity, validate_dataset)


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

    def quarantine(self, name, reason, records):
        path = self.root/"quarantine"/(name+".json")
        path.write_text(json.dumps(records))
        entry = dict(path=str(path.relative_to(self.root)), sha256=sha256(path), reason=reason,
            rows=len(records), source_ids=[r["source_id"] for r in self.manifest["raw_files"]])
        self.manifest["quarantine_files"] = [r for r in self.manifest["quarantine_files"] if r["path"] != entry["path"]]+[entry]

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

    def test_dropped_raw_funding_record_cannot_silently_disappear(self):
        item = self.manifest["normalized_files"][3]
        rows = self.rows(item)
        missing = int(rows.pop(2)["timestamp"])
        self.write_normalized(item, rows)
        result = self.audit()
        self.assertEqual(result["structural_status"], "FAIL")
        absent = result["raw_coverage"]["omitted_origins"]
        self.assertEqual(len(absent), 1)
        self.assertEqual(absent[0]["timestamp"], missing)
        self.assertEqual(absent[0]["kind"], "funding")
        self.assertEqual(absent[0]["raw_references"], [{"source_id": "BTC_USDT-funding", "source_row": 3}])

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

    def test_duplicate_lineage_must_cover_all_references_and_destination(self):
        original = self.manifest["raw_files"][0]
        extra = dict(original, source_id="duplicate", path="raw/duplicate.json")
        path = self.root/extra["path"]
        path.write_text(json.dumps(json.loads((self.root/original["path"]).read_text())[:1]))
        extra.update(sha256=sha256(path), bytes=path.stat().st_size)
        self.manifest["raw_files"].append(extra)
        self.assert_issue("missing complete duplicate lineage")
        record = dict(symbol="BTC_USDT", kind="candles", interval_seconds=3600,
            timestamp=self.start, values=[str(self.start), "100", "102", "99", "101", "1"],
            references=[dict(source_id=original["source_id"], source_row=1), dict(source_id="duplicate", source_row=1)],
            resolution="deduplicated_identical", destination=dict(path=self.manifest["normalized_files"][0]["path"],
                source_id=original["source_id"], source_row=1))
        self.quarantine("duplicates", "identical_duplicate_provenance", [record])
        result = self.audit()
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["quarantine_accountability"]["verified_duplicate_origins"], 1)
        record["references"].pop()
        self.quarantine("duplicates", "identical_duplicate_provenance", [record])
        self.assert_issue("duplicate lineage does not account")

    def test_quarantine_cannot_disguise_in_range_funding_omission(self):
        item = self.manifest["normalized_files"][3]
        rows = self.rows(item)
        omitted = rows.pop(2)
        self.write_normalized(item, rows)
        self.quarantine("exclusions", "invalid_or_excluded_rows", [dict(
            source_id=omitted["source_id"], source_row=int(omitted["source_row"]),
            values=[omitted["timestamp"], omitted["funding_rate"]], reason="outside_global_closed_range")])
        self.assert_issue("not a validated boundary exclusion")

    def test_current_metadata_cannot_be_backdated(self):
        source = dict(source_id="metadata", path="raw/metadata.json", url="https://api.gateio.ws/api/v4/futures/usdt/contracts/BTC_USDT",
            retrieved_at="2026-10-28T00:00:00Z", http_status=200, format="contract_json")
        path = self.root/source["path"]
        payload = dict(name="BTC_USDT", quanto_multiplier="0.0001")
        path.write_text(json.dumps(payload))
        source.update(sha256=sha256(path), bytes=path.stat().st_size)
        self.manifest["raw_files"].append(source)
        observed = datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00")).timestamp()
        normalized = dict(symbol="BTC_USDT", kind="contract_metadata", interval_seconds=None,
            path="normalized/metadata.json", rows=1, start_ts=observed, end_ts=observed,
            columns=[], source_ids=["metadata"], units={}, availability_basis="current_snapshot_not_historical",
            observed_at=source["retrieved_at"], historical_effective_at=None)
        envelope = dict(source_id="metadata", observed_at=source["retrieved_at"], historical_effective_at=None, data=payload)
        target = self.root/normalized["path"]
        target.write_text(json.dumps(envelope))
        normalized["sha256"] = sha256(target)
        self.manifest["normalized_files"].append(normalized)
        self.assertEqual(self.audit()["issues"], [])
        envelope["historical_effective_at"] = self.start
        target.write_text(json.dumps(envelope))
        normalized["sha256"] = sha256(target)
        self.assert_issue("metadata snapshot lineage/backdating")

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
        source["complete_object"] = True
        self.assertTrue(raw_rows(path, source, identity, self.spec)[1])

    def test_failed_complete_json_never_becomes_normalized_source(self):
        source = self.manifest["raw_files"][0]
        source["complete_object"] = False
        self.assert_issue("normalized source missing/incomplete")
        source["complete_object"] = True
        source["response_headers"] = {"Content-Length": str(source["bytes"]+1)}
        self.assert_issue("Content-Length differs")

    def test_manifest_universe_and_spec_drift_fail_closed(self):
        self.manifest["symbols"].append("SOL_USDT")
        with self.assertRaisesRegex(ValueError, "universe"):
            self.audit()
        self.manifest["symbols"].pop()
        self.manifest["spec_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "spec hash"):
            self.audit()

    def test_sealed_attempt_audit_rejects_lost_reservation_or_changed_request(self):
        probes = self.root/"probes"
        probes.mkdir()
        prior = []
        for i in range(1, 13):
            body = probes/str(i)
            body.write_text("[]")
            prior.append(dict(id=i, body_file=str(i), sha256=sha256(body), saved_bytes=2,
                byte_cap=2, method="GET", url=self.manifest["raw_files"][0]["url"]))
        (probes/"probe-ledger.json").write_text(json.dumps(prior))
        self.manifest["prior_probe_ledger_sha256"] = sha256(probes/"probe-ledger.json")
        events, tasks = [], []
        for i, raw in enumerate(self.manifest["raw_files"], 13):
            raw.update(attempt_id=i, task_id=str(i), method="GET", params={}, request_headers={}, event="end", accepted=True)
            begin = dict(raw, event="begin", accepted=False)
            events.extend((begin, raw))
            tasks.append(dict(task_id=str(i), url=raw["url"], params={}))
        self.manifest.update(attempts_including_probes=20,
            bytes_including_probes=24+sum(r["bytes"] for r in self.manifest["raw_files"]))
        (self.root/"manifest.json").write_text(json.dumps(self.manifest))
        (self.root/"plan.json").write_text(json.dumps(dict(requests=tasks, spec_sha256=sha256(self.spec_path))))
        ledger = self.root/"attempts.jsonl"
        def save(records):
            ledger.write_text("\n".join(json.dumps(r) for r in records)+"\n")
        fixture = Path(__file__).resolve().parents[2]/"research/qr003/results/phase-a-input-spec.json"
        save(events)
        with patch('research.qr004.validate_history.native_warmup', return_value={"fixture_only": True}):
            result = sealed_diagnostics(self.root, self.spec_path, fixture, probes)
        self.assertEqual(result["attempt_audit"]["total_attempts"], 20)
        self.assertEqual(result["network_calls_by_QR"], 0)
        save(events[1:])
        with self.assertRaisesRegex(ValueError, "attempt event"):
            sealed_diagnostics(self.root, self.spec_path, fixture, probes)
        events[1] = dict(events[1], url=events[1]["url"]+"&changed=1")
        save(events)
        with self.assertRaisesRegex(ValueError, "identity changed"):
            sealed_diagnostics(self.root, self.spec_path, fixture, probes)


class NativeWarmupTests(unittest.TestCase):
    def test_full_native_windows_and_future_funding_causality(self):
        import numpy as np
        import pandas as pd
        from src.config import SystematicConfig
        # Original long-window policy; a full synthetic year, no order engine.
        fixture = Path(__file__).resolve().parents[2]/"research/qr003/results/phase-a-input-spec.json"
        cfg = SystematicConfig.build(json.loads(fixture.read_text())["instruments"]["BTC_USDT"]["fixture"]["strategy_config"])
        start, decision = 1672531200, 1704067200
        frames = {}
        for key, step in (("1h", 3600), ("4h", 14400), ("1d", 86400)):
            times = np.arange(start, decision, step)
            close = 100 + np.arange(len(times))*0.005 + np.sin(np.arange(len(times))*0.13)
            frames[key] = pd.DataFrame(dict(timestamp=times, open=close-.2,
                high=close+1, low=close-1, close=close, volume=100+np.arange(len(times))%7))
        frames["funding"] = pd.DataFrame(dict(timestamp=np.arange(start, decision+28800, 28800)+1,
            funding_rate=0.0001))
        baseline = native_warmup(frames, cfg, decision, 28800)
        self.assertTrue(baseline["full_windows_at_start"])
        self.assertFalse(baseline["training_permission"])
        frames["funding"].loc[frames["funding"].timestamp > decision, "funding_rate"] = 0.2
        self.assertEqual(baseline, native_warmup(frames, cfg, decision, 28800))
        # Finite native minimum is insufficient for the full 1000-observation scaler.
        frames["funding"] = frames["funding"][frames["funding"].timestamp >= decision-500*14400]
        short = native_warmup(frames, cfg, decision, 28800)
        self.assertTrue(short["findings"]["carry"]["native_finite"])
        self.assertFalse(short["full_windows_at_start"])
        self.assertLess(short["findings"]["carry"]["finite_prior_raw"], 1000)


if __name__ == "__main__":
    unittest.main()
