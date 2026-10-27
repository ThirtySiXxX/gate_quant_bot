"""No-network fixtures for bounded intake, dirty-data retention and lineage."""
from copy import deepcopy
from decimal import Decimal
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

from research.qd004 import history_intake as hi


def spec():
    return dict(calendar=dict(raw_start=1672531200, raw_end_exclusive=1672545600),
        sources=dict(recent_api_start=1790812800, archive_last_full_month="202609"),
        intake_budget=dict(max_requests=450, max_retries_per_request=2,
            max_compressed_bytes_per_file=10485760, max_total_compressed_bytes=262144000,
            max_uncompressed_bytes_per_file=104857600),
        normalization=dict(candle_columns=["timestamp", "open", "high", "low", "close", "volume", "available_at", "source_id", "source_row"],
            funding_columns=["timestamp", "funding_rate", "available_at", "source_id", "source_row"],
            candle_available_at="open_plus_interval_proxy_not_observed_arrival",
            funding_available_at="source_settlement_proxy_not_observed_arrival"))


def task(kind="candles", seconds=3600):
    return dict(task_id="fixture-task", symbol="BTC_USDT", kind=kind, interval_seconds=seconds,
        url=hi.ARCHIVE + ("candlesticks_1h" if kind == "candles" else "funding_applies") + "/202301/BTC_USDT-202301.csv.gz",
        params={}, format="candles_csv_gzip" if kind == "candles" else "funding_csv_gzip", route_id=hi.ROUTE)


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = headers if headers is not None else {"content-length": str(len(body))}


class Opener:
    def __init__(self, responses):
        self.responses, self.calls = iter(responses), 0

    def open(self, request, timeout):
        self.calls += 1
        return next(self.responses)


class HistoryIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "dataset"
        self.root.mkdir()
        self.rules = spec()
        self.prior = Path(self.temp.name) / "prior.json"
        self.prior.write_bytes(hi.json_bytes([dict(id=i, saved_bytes=1) for i in range(1, 13)]))
        self.prior_patch = patch.object(hi, "PRIOR_PROBE_SHA256", hi.digest(self.prior.read_bytes()))
        self.prior_patch.start()
        self.addCleanup(self.prior_patch.stop)

    def record(self, body, identity="a", kind="candles", seconds=3600, fmt=None):
        item = task(kind, seconds)
        if fmt:
            item["format"] = fmt
        path = "raw/" + identity + ".bin"
        hi.write_once(self.root, path, body)
        return dict(item, source_id=identity, path=path, retrieved_at="2026-10-28T00:00:00+00:00",
            http_status=200, complete_object=True, accepted=True, sha256=hi.digest(body),
            bytes=len(body), response_headers={}, hash_scope="complete_object")

    def candles(self, timestamp=1672531200, close="100"):
        return gzip.compress(f"{timestamp},10,{close},200,1,100\n".encode(), mtime=0)

    def test_hash_and_routes_are_pinned_before_any_fetch(self):
        path = Path(self.temp.name) / "wrong-spec.json"
        path.write_text("{}")
        with self.assertRaisesRegex(hi.IntakeError, "specification hash"):
            hi.load_spec(path)
        rules = spec()
        rules["calendar"]["raw_end_exclusive"] = 1793091600
        tasks = hi.plan_requests(rules)
        self.assertEqual(len(tasks), 210)
        for entry in tasks:
            hi.validate_url(entry["url"])
        for url in ("http://api.gateio.ws/api/v4/futures/usdt/accounts",
                    "https://api.gateio.ws/api/v4/futures/usdt/accounts",
                    hi.API + "candlesticks?contract=SOL_USDT&interval=1h",
                    "https://example.com/funding.csv", hi.ARCHIVE + "funding_updates/202301/BTC_USDT-202301.csv.gz"):
            with self.subTest(url=url), self.assertRaises(hi.IntakeError):
                hi.validate_url(url)

    def test_attempt_reservations_retries_and_resume_consume_shared_budget(self):
        opener = Opener([Response(b"error", 500), Response(self.candles())])
        collector = hi.Collector(self.root, self.rules, self.prior, opener, pause=0)
        collector.acquire([task()])
        self.assertEqual(opener.calls, 2)
        self.assertEqual([r["attempt_id"] for r in collector.records], [13, 14])
        self.assertFalse(collector.records[0]["accepted"])
        self.assertTrue(collector.records[1]["accepted"])
        resumed = hi.Collector(self.root, self.rules, self.prior, Opener([]), pause=0)
        resumed.acquire([task()])
        self.assertEqual(resumed.opener.calls, 0)
        resumed.spec = deepcopy(self.rules)
        resumed.spec["intake_budget"]["max_requests"] = 14
        with self.assertRaisesRegex(hi.IntakeError, "budget"):
            resumed.fetch(task())

    def test_public_access_barrier_is_not_retried(self):
        opener = Opener([Response(b"denied", 403)])
        collector = hi.Collector(self.root, self.rules, self.prior, opener, pause=0)
        with self.assertRaisesRegex(hi.IntakeError, "access restriction"):
            collector.acquire([task()])
        self.assertEqual(opener.calls, 1)
        self.assertEqual((self.root / collector.records[0]["path"]).read_bytes(), b"denied")

    def test_retry_limit_survives_process_resume(self):
        opener = Opener([Response(b"bad", 500) for _ in range(3)])
        collector = hi.Collector(self.root, self.rules, self.prior, opener, pause=0)
        collector.acquire([task()])
        self.assertEqual(opener.calls, 3)
        resumed = hi.Collector(self.root, self.rules, self.prior, Opener([]), pause=0)
        resumed.acquire([task()])
        self.assertEqual(resumed.opener.calls, 0)

    def test_partial_206_length_mismatch_and_byte_caps_never_promote(self):
        data = self.candles()
        responses = [Response(data, 206, {"content-range": f"bytes 0-{len(data)-1}/{len(data)+1}", "content-length": str(len(data))}),
                     Response(data, 200, {"content-length": str(len(data)+1)})]
        collector = hi.Collector(self.root, self.rules, self.prior, Opener(responses), pause=0)
        self.assertFalse(collector.fetch(task())["accepted"])
        self.assertFalse(collector.fetch(task())["accepted"])
        collector.spec = deepcopy(self.rules)
        collector.spec["intake_budget"]["max_compressed_bytes_per_file"] = 2
        collector.opener = Opener([Response(b"oversize")])
        record = collector.fetch(task())
        self.assertEqual(record["bytes"], 0)
        self.assertFalse(record["accepted"])

    def test_gzip_crc_truncation_and_expansion_are_verified(self):
        data = self.candles()
        for label, body in (("truncated", data[:-4]), ("bad-crc", data[:-8] + b"\0" * 8)):
            record = self.record(body, label)
            with self.subTest(label=label), self.assertRaises((hi.IntakeError, zlib.error)):
                hi.parse_source(self.root, record, self.rules)
        record = self.record(data, "cap")
        tiny = deepcopy(self.rules)
        tiny["intake_budget"]["max_uncompressed_bytes_per_file"] = 3
        with self.assertRaises(hi.IntakeError):
            hi.parse_source(self.root, record, tiny)

    def test_recognized_header_maps_one_based_rows_and_preserves_contract_volume(self):
        body = gzip.compress(b"timestamp,size,close,high,low,open\n1672531200,10,100,101,99,100\n", mtime=0)
        rows, errors, mapping = hi.parse_source(self.root, self.record(body), self.rules)
        self.assertEqual(errors, [])
        self.assertTrue(mapping["header_present"])
        self.assertEqual(rows[0]["source_row"], 1)
        self.assertEqual(rows[0]["values"], tuple(map(Decimal, ["1672531200", "100", "101", "99", "100", "10"])))
        api = hi.json_bytes([dict(t=1672531200, o="100", h="101", l="99", c="100", sum="999")])
        _, errors, _ = hi.parse_source(self.root, self.record(api, "missing-v", fmt="candles_json"), self.rules)
        self.assertEqual(len(errors), 1)  # sum must not replace missing v.

    def test_duplicates_keep_all_origins_and_conflicts_quarantine_every_version(self):
        records = [self.record(self.candles(close=value), name) for name, value in (("a", "100"), ("b", "100.0"), ("c", "101"))]
        manifest = hi.normalize(self.root, self.rules, records, [task()])
        conflicts = json.loads((self.root / "quarantine/conflicts.json").read_text())
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(sum(len(v["references"]) for v in conflicts[0]["variants"]), 3)
        stream = next(x for x in manifest["normalized_files"] if x["kind"] == "candles" and x["interval_seconds"] == 3600 and x["symbol"] == "BTC_USDT")
        self.assertEqual(stream["rows"], 0)
        hi.verify_dataset(self.root, self.rules)

    def test_identical_duplicate_lineage_and_silent_raw_drop_detection(self):
        records = [self.record(self.candles(), name) for name in ("a", "b")]
        hi.normalize(self.root, self.rules, records, [task()])
        hi.verify_dataset(self.root, self.rules)
        lineage = self.root / "quarantine/duplicate-lineage.json"
        values = json.loads(lineage.read_text())
        self.assertEqual(len(values[0]["references"]), 2)
        # Even with recomputed manifest hashes, dropping a duplicate origin is detected.
        values[0]["references"].pop()
        lineage.write_bytes(hi.json_bytes(values))
        manifest_path = self.root / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        next(x for x in manifest["quarantine_files"] if x["path"].endswith("duplicate-lineage.json"))["sha256"] = hi.digest(lineage.read_bytes())
        manifest_path.write_bytes(hi.json_bytes(manifest))
        with self.assertRaisesRegex(hi.IntakeError, "silently dropped"):
            hi.verify_dataset(self.root, self.rules)

    def test_invalid_and_cutoff_rows_are_explicit_not_silently_cleaned(self):
        body = gzip.compress(b"1672531200,10,100,101,99,100\n1672534800,10,100,1,99,100\n1672542000,10,100,101,99,100\n", mtime=0)
        rules = deepcopy(self.rules)
        rules["calendar"]["raw_end_exclusive"] = 1672543000
        record = self.record(body)
        manifest = hi.normalize(self.root, rules, [record], [task()])
        errors = json.loads((self.root / "quarantine/exclusions.json").read_text())
        self.assertEqual([r["source_row"] for r in errors], [2, 3])
        self.assertTrue(manifest["quality_summary"]["gaps"])
        hi.verify_dataset(self.root, rules)

    def test_funding_seconds_offsets_preserved_schedule_deviations_not_filled(self):
        rules = deepcopy(self.rules)
        rules["calendar"]["raw_end_exclusive"] = 1672621200
        body = gzip.compress(b"1672531209,0.00010\n1672560009,-0.00020\n1672617609,0.00030\n", mtime=0)
        record = self.record(body, kind="funding", seconds=None)
        manifest = hi.normalize(self.root, rules, [record], [task("funding", None)])
        schedule = manifest["quality_summary"]["funding_schedule"]["BTC_USDT"]
        self.assertEqual(schedule["observed_duration_counts"], {"28800": 1, "57600": 1})
        self.assertEqual(len(schedule["deviations"]), 1)
        content = (self.root / "normalized/BTC_USDT-funding.csv").read_text()
        self.assertIn("1672531209,0.00010,1672531209", content)
        self.assertIn("-0.00020", content)
        hi.verify_dataset(self.root, rules)

    def test_path_escape_symlink_and_immutable_overwrite_rejected(self):
        for path in ("../private", "/tmp/private", "raw\\escape"):
            with self.subTest(path=path), self.assertRaises(hi.IntakeError):
                hi.safe_path(self.root, path)
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(hi.IntakeError):
            hi.safe_path(self.root, "alias/file")
        hi.write_once(self.root, "raw/immutable", b"original")
        with self.assertRaises(hi.IntakeError):
            hi.write_once(self.root, "raw/immutable", b"changed")

    def test_interrupted_attempt_is_retained_and_cannot_reset_budget(self):
        record = dict(task(), event="begin", attempt_id=13, source_id="request-00013", path="raw/interrupted",
                      bytes=0, retrieved_at="2026-10-28T00:00:00+00:00", method="GET")
        hi.write_once(self.root, record["path"], b"partial")
        (self.root / "attempts.jsonl").write_bytes(json.dumps(record).encode() + b"\n")
        collector = hi.Collector(self.root, self.rules, self.prior, Opener([]), pause=0)
        self.assertEqual(len(collector.records), 1)
        self.assertEqual(collector.records[0]["error"], "interrupted")
        self.assertEqual(collector.records[0]["bytes"], 7)
        self.assertFalse(collector.records[0]["accepted"])

    def test_dropped_nonduplicate_funding_cannot_hide_behind_updated_hashes(self):
        rules = deepcopy(self.rules)
        rules["calendar"]["raw_end_exclusive"] = 1672621200
        record = self.record(gzip.compress(b"1672531200,.0001\n1672560000,.0002\n1672588800,.0003\n", mtime=0),
                             kind="funding", seconds=None)
        hi.normalize(self.root, rules, [record], [task("funding", None)])
        path = self.root / "normalized/BTC_USDT-funding.csv"
        lines = path.read_text().splitlines(True)
        path.write_text("".join([lines[0], lines[1], lines[3]]))
        manifest_path = self.root / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        entry = next(x for x in manifest["normalized_files"] if x["path"] == "normalized/BTC_USDT-funding.csv")
        entry.update(rows=2, sha256=hi.digest(path.read_bytes()))
        manifest_path.write_bytes(hi.json_bytes(manifest))
        with self.assertRaisesRegex(hi.IntakeError, "silently dropped"):
            hi.verify_dataset(self.root, rules)

    def test_authentic_extreme_is_flagged_and_retained_without_clipping(self):
        body = gzip.compress(b"1672531200,10,100,200,1,100\n1672534800,10,150,200,1,100\n", mtime=0)
        manifest = hi.normalize(self.root, self.rules, [self.record(body)], [task()])
        self.assertTrue(manifest["quality_summary"]["extreme_moves"])
        self.assertIn(",150,10,", (self.root / "normalized/BTC_USDT-3600s.csv").read_text())
        hi.verify_dataset(self.root, self.rules)

    def test_exclusive_collector_lease_releases_on_error(self):
        with self.assertRaises(RuntimeError):
            with hi.acquisition_lease(self.root):
                with self.assertRaisesRegex(hi.IntakeError, "another collector"):
                    with hi.acquisition_lease(self.root):
                        self.fail("concurrent acquisition was admitted")
                raise RuntimeError("fixture")
        with hi.acquisition_lease(self.root):
            self.assertTrue((self.root / ".acquisition.lock").exists())

    def test_current_metadata_keeps_actual_observation_time(self):
        record = self.record(b'{"name":"BTC_USDT","funding_interval":28800}', "meta", "contract_metadata", None, "contract_json")
        record["url"] = hi.API + "contracts/BTC_USDT"
        manifest = hi.normalize(self.root, self.rules, [record], [record])
        entry = next(x for x in manifest["normalized_files"] if x["kind"] == "contract_metadata")
        observed = json.loads((self.root / entry["path"]).read_text())
        self.assertEqual(observed["observed_at"], record["retrieved_at"])
        self.assertIsNone(observed["historical_effective_at"])
        hi.verify_dataset(self.root, self.rules)

    def test_cross_interval_evidence_is_quarantined_without_rewriting_candidates(self):
        hourly = gzip.compress(b"".join(f"{1672531200+i*3600},10,100,200,1,100\n".encode() for i in range(4)), mtime=0)
        a = self.record(hourly, "hourly")
        b = self.record(hi.json_bytes([dict(t=1672531200, o="100", h="200", l="1", c="100", v="41")]),
                        "native", seconds=14400, fmt="candles_json")
        b["url"] = hi.API + "candlesticks?contract=BTC_USDT&interval=4h&from=1672531200&to=1672545599"
        hi.normalize(self.root, self.rules, [a, b], [task()])
        original = (self.root / "manifest.json").read_bytes()
        normalized = {p.name: p.read_bytes() for p in (self.root / "normalized").iterdir()}
        checked = hi.quarantine_qc(self.root, self.rules)
        self.assertEqual(checked["status"], "PASS_LOCAL_FILE_AND_LINEAGE_RECHECK")
        self.assertEqual(original, (self.root / "manifest.json").read_bytes())
        self.assertEqual(normalized, {p.name: p.read_bytes() for p in (self.root / "normalized").iterdir()})
        evidence = json.loads((self.root / "quarantine/cross-interval-disagreements.json").read_text())
        self.assertEqual(evidence[0]["differing_fields"], ["volume"])
        self.assertEqual(len(evidence[0]["hourly_components"]), 4)
        self.assertEqual(evidence[0]["native"]["source_row"], 1)
        hi.verify_dataset(self.root, self.rules, "candidate-reviewed.json")


if __name__ == "__main__":
    unittest.main()
