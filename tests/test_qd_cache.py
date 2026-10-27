"""Offline cache publication and concurrent fetch regressions (synthetic data)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import multiprocessing
import os
import socket
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import pandas as pd

from src import data_fetcher as df


def candles(times, close=100.0):
    return pd.DataFrame(dict(timestamp=times, open=100.0, high=110.0,
                             low=90.0, close=close, volume=10.0))


def funding(times, rate=0.001):
    return pd.DataFrame(dict(timestamp=times, funding_rate=rate))


def _process_fetch(directory, kind, deep, requested, entered, release, output):
    """Spawn-safe real fetch transaction; no exchange, credentials or sockets."""
    socket.socket.connect = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("offline"))
    original_load = df._load_cache

    def load(*args):
        if not deep:
            entered.set()
        return original_load(*args)

    def page(*args, **kwargs):
        if deep:
            entered.set()
            if not release.wait(10):
                raise AssertionError("process fetch was not released")
            times = [0, 3600, 7200, 10800]
        else:
            times = [7200, 10800]
        if kind == "funding":
            return funding(times, 0.001 if deep else -0.002)
        return candles(times, 100.0 if deep else 105.0)

    class Exchange:
        get_funding_rate_history = staticmethod(page)

    try:
        with patch.object(df.time, "time", return_value=14400), \
             patch.object(df, "_load_cache", side_effect=load), \
             patch.object(df, "_fetch_page", side_effect=page):
            requested.set()
            if kind == "funding":
                result = df.fetch_funding_history(Exchange(), "ETH_USDT", 1 / 6 if deep else 1 / 12, directory)
            else:
                result = df.fetch_candles(None, "ETH_USDT", "1h", 1 / 6 if deep else 1 / 12, directory)
            output.put((deep, result.timestamp.tolist()))
    except BaseException as exc:
        output.put((deep, repr(exc)))
        raise


def _process_hold_lock(path, requested, entered, release):
    requested.set()
    with df._cache_lock(path):
        entered.set()
        if release is None:
            # Do not kill a process inside a shared Event/Condition: doing so
            # can strand that test primitive independently of the file lock.
            time.sleep(30)
        elif not release.wait(10):
            raise AssertionError("lock holder was not released")


def _process_crash_during_write(directory):
    def crash(frame, handle, **kwargs):
        handle.write("timestamp,open\n0,")
        handle.flush()
        os._exit(17)

    path = df._cache_path(directory, "ETH_USDT", "1h")
    with df._cache_lock(path), patch.object(pd.DataFrame, "to_csv", crash):
        df._save_cache(directory, "ETH_USDT", "1h", candles([0, 3600]))


class CachePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ETH_USDT_1h.csv"
        self.old = candles([0, 3600])
        self.old.to_csv(self.path, index=False)
        self.old_bytes = self.path.read_bytes()

    def assert_old_cache(self):
        self.assertEqual(self.path.read_bytes(), self.old_bytes)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_serialization_failure_preserves_previous_snapshot(self):
        def fail(frame, destination, **kwargs):
            if hasattr(destination, "write"):
                destination.write("timestamp,open\n0,")
            else:
                Path(destination).write_text("timestamp,open\n0,")
            raise OSError("injected partial serialization")

        with patch.object(pd.DataFrame, "to_csv", fail), self.assertLogs(df.logger, "WARNING"):
            df._save_cache(self.temp.name, "ETH_USDT", "1h", candles([0, 3600, 7200]))
        self.assert_old_cache()

    def test_reader_sees_old_snapshot_until_new_csv_is_complete(self):
        started, release = threading.Event(), threading.Event()
        original = pd.DataFrame.to_csv

        def pause(frame, destination, **kwargs):
            if hasattr(destination, "write"):
                destination.write("timestamp,open\n0,")
                destination.flush()
            else:
                Path(destination).write_text("timestamp,open\n0,")
            started.set()
            if not release.wait(5):
                raise AssertionError("writer was not released")
            if hasattr(destination, "seek"):
                destination.seek(0)
                destination.truncate()
            return original(frame, destination, **kwargs)

        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch.object(pd.DataFrame, "to_csv", pause):
                future = pool.submit(df._save_cache, self.temp.name, "ETH_USDT", "1h", candles([0, 3600, 7200]))
                try:
                    self.assertTrue(started.wait(5))
                    pd.testing.assert_frame_equal(df.read_cached_candles(self.temp.name, "ETH_USDT", "1h"), self.old)
                finally:
                    release.set()
                future.result(timeout=5)
        self.assertEqual(pd.read_csv(self.path).timestamp.tolist(), [0, 3600, 7200])

    def test_fsync_and_replace_failures_preserve_old_snapshot_and_remove_temp(self):
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation), \
                 patch.object(df.os, operation, side_effect=OSError("injected disk error")), \
                 self.assertLogs(df.logger, "WARNING"):
                df._save_cache(self.temp.name, "ETH_USDT", "1h", candles([0, 3600, 7200]))
            self.assert_old_cache()

    def test_failed_first_write_does_not_publish_empty_or_partial_csv(self):
        self.path.unlink()
        with patch.object(pd.DataFrame, "to_csv", side_effect=OSError("disk full")), \
             self.assertLogs(df.logger, "WARNING"):
            df._save_cache(self.temp.name, "ETH_USDT", "1h", self.old)
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_replacement_preserves_existing_cache_permissions(self):
        self.path.chmod(0o640)
        df._save_cache(self.temp.name, "ETH_USDT", "1h", candles([0, 3600, 7200]))
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(pd.read_csv(self.path).timestamp.tolist(), [0, 3600, 7200])


class CacheTransactionTests(unittest.TestCase):
    def test_same_key_fetch_waits_and_merges_preceding_history(self):
        entered, release, second_requested, second_read = (threading.Event() for _ in range(4))
        original_load = df._load_cache

        def load(*args):
            if threading.current_thread().name.endswith("_1"):
                second_read.set()
            return original_load(*args)

        def page(exchange, contract, interval, limit, to_ts=None):
            if exchange == "deep":
                entered.set()
                if not release.wait(5):
                    raise AssertionError("first fetch was not released")
                return candles([0, 3600, 7200, 10800])
            return candles([7200, 10800], close=105.0)

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=14400), \
             patch.object(df, "_fetch_page", side_effect=page), \
             patch.object(df, "_load_cache", side_effect=load):
            def second():
                second_requested.set()
                return df.fetch_candles("recent", "ETH_USDT", "1h", 1 / 12, temp)

            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache") as pool:
                first = pool.submit(df.fetch_candles, "deep", "ETH_USDT", "1h", 1 / 6, temp)
                try:
                    self.assertTrue(entered.wait(5))
                    later = pool.submit(second)
                    self.assertTrue(second_requested.wait(5))
                    self.assertFalse(second_read.wait(0.2), "second fetch read a stale cache before the first published")
                finally:
                    release.set()
                first.result(timeout=5)
                result = later.result(timeout=5)
            cached = pd.read_csv(Path(temp) / "ETH_USDT_1h.csv")
            self.assertEqual(cached.timestamp.tolist(), [0, 3600, 7200, 10800])
            self.assertEqual(cached.close.tolist(), [100.0, 100.0, 105.0, 105.0])
            self.assertEqual(result.timestamp.tolist(), [7200, 10800])

    def test_different_contracts_intervals_and_funding_do_not_share_a_lock(self):
        barrier = threading.Barrier(4, timeout=5)

        def page(*args, **kwargs):
            barrier.wait()
            return candles([0])

        class Exchange:
            def get_funding_rate_history(self, *args, **kwargs):
                barrier.wait()
                return funding([0])

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=3600), \
             patch.object(df, "_fetch_page", side_effect=page), \
             ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(df.fetch_candles, None, symbol, interval, 1 / 24, temp)
                       for symbol, interval in (("ETH_USDT", "1h"), ("BTC_USDT", "1h"), ("ETH_USDT", "4h"))]
            futures.append(pool.submit(df.fetch_funding_history, Exchange(), "ETH_USDT", 1 / 24, temp))
            for future in futures:
                self.assertEqual(future.result(timeout=10).timestamp.tolist(), [0])
            self.assertEqual(len(list(Path(temp).glob("*.csv"))), 4)

    def test_cache_disabled_has_no_filesystem_side_effects(self):
        class Exchange:
            def get_funding_rate_history(self, *args, **kwargs):
                return funding([0])

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=3600), \
             patch.object(df, "_fetch_page", return_value=candles([0])), \
             patch.object(df, "_cache_path", side_effect=AssertionError("cache disabled")):
            directory = str(Path(temp) / "unused")
            self.assertEqual(len(df.fetch_candles(None, "ETH_USDT", "1h", 1 / 24, directory, use_cache=False)), 1)
            self.assertEqual(len(df.fetch_funding_history(Exchange(), "ETH_USDT", 1 / 24, directory, use_cache=False)), 1)
            self.assertFalse(Path(directory).exists())

    def test_lock_failure_falls_back_to_uncached_fetch_without_reading_or_writing(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=3600), \
             patch.object(df, "_lock_cache_file", side_effect=OSError("locking unavailable")), \
             patch.object(df, "_load_cache", side_effect=AssertionError("unsafe read")), \
             patch.object(df, "_save_cache", side_effect=AssertionError("unsafe write")), \
             patch.object(df, "_fetch_page", return_value=candles([0])), \
             self.assertLogs(df.logger, "WARNING"):
            self.assertEqual(len(df.fetch_candles(None, "ETH_USDT", "1h", 1 / 24, temp)), 1)
            class Exchange:
                def get_funding_rate_history(self, *args, **kwargs):
                    return funding([0])
            self.assertEqual(len(df.fetch_funding_history(Exchange(), "ETH_USDT", 1 / 24, temp)), 1)
            self.assertEqual(list(Path(temp).glob("*.csv")), [])

    def test_fetch_failure_propagates_once_and_releases_lock_for_another_thread(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=3600), \
             patch.object(df, "_fetch_page", side_effect=OSError("exchange unavailable")) as page:
            with self.assertRaisesRegex(OSError, "exchange unavailable"):
                df.fetch_candles(None, "ETH_USDT", "1h", 1 / 24, temp)
            self.assertEqual(page.call_count, 1)
            page.side_effect = None
            page.return_value = candles([0])
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(df.fetch_candles, None, "ETH_USDT", "1h", 1 / 24, temp).result(timeout=5)
            self.assertEqual(result.timestamp.tolist(), [0])

    def test_cache_failure_still_returns_downloaded_data(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=3600), \
             patch.object(df, "_fetch_page", return_value=candles([0])), \
             patch.object(df.os, "replace", side_effect=OSError("injected replace failure")), \
             self.assertLogs(df.logger, "WARNING"):
            pd.testing.assert_frame_equal(df.fetch_candles(None, "ETH_USDT", "1h", 1 / 24, temp), candles([0]))

    def test_cached_and_uncached_results_preserve_values_columns_and_filtering(self):
        class Exchange:
            def get_funding_rate_history(self, *args, **kwargs):
                return funding([0, 3600, 7200], -0.0003)

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(df.time, "time", return_value=10800), \
             patch.object(df, "_fetch_page", return_value=candles([0, 3600, 7200])):
            for use_cache in (False, True, True):
                result = df.fetch_candles(None, "ETH_USDT", "1h", 1 / 12, temp, use_cache)
                pd.testing.assert_frame_equal(result, candles([3600, 7200]))
                result = df.fetch_funding_history(Exchange(), "ETH_USDT", 1 / 12, temp, use_cache)
                pd.testing.assert_frame_equal(result, funding([3600, 7200], -0.0003))
            pd.testing.assert_frame_equal(df.read_cached_candles(temp, "ETH_USDT", "1h", 3600, 3600), candles([3600]))

    def test_directory_alias_and_reentry_use_one_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "cache"
            directory.mkdir()
            alias = Path(temp) / "alias"
            try:
                alias.symlink_to(directory, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            path = str(directory / "ETH_USDT_1h.csv")
            requested, entered = threading.Event(), threading.Event()

            def contender():
                requested.set()
                with df._cache_lock(str(alias / "ETH_USDT_1h.csv")):
                    entered.set()

            with ThreadPoolExecutor(max_workers=1) as pool:
                with df._cache_lock(path), df._cache_lock(str(alias / "ETH_USDT_1h.csv")):
                    future = pool.submit(contender)
                    self.assertTrue(requested.wait(5))
                    self.assertFalse(entered.wait(0.2))
                future.result(timeout=5)
                self.assertTrue(entered.is_set())
            self.assertTrue(Path(path + ".lock").exists(), "lock inode must remain for waiters")
            self.assertEqual(len(df._cache_locks), 0, "unused in-process lock entries should be reclaimed")


class CacheProcessTests(unittest.TestCase):
    def test_process_exit_mid_write_preserves_old_csv_and_next_writer_recovers(self):
        ctx = multiprocessing.get_context("spawn")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ETH_USDT_1h.csv"
            candles([0]).to_csv(path, index=False)
            old_bytes = path.read_bytes()
            process = ctx.Process(target=_process_crash_during_write, args=(temp,))
            process.start()
            try:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 17)
                self.assertEqual(path.read_bytes(), old_bytes)
                # Abrupt exit cannot run finally; orphan temps are never loaded.
                self.assertEqual(len(list(Path(temp).glob("*.tmp"))), 1)
                with patch.object(df.time, "time", return_value=7200), \
                     patch.object(df, "_fetch_page", return_value=candles([0, 3600])):
                    result = df.fetch_candles(None, "ETH_USDT", "1h", 1 / 12, temp)
                self.assertEqual(result.timestamp.tolist(), [0, 3600])
                self.assertEqual(pd.read_csv(path).timestamp.tolist(), [0, 3600])
            finally:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=5)
                process.close()

    def test_process_fetch_transactions_preserve_history_and_newest_values(self):
        ctx = multiprocessing.get_context("spawn")
        for kind in ("candles", "funding"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                requested1, entered1, requested2, entered2, release = (ctx.Event() for _ in range(5))
                output = ctx.Queue()
                first = ctx.Process(target=_process_fetch, args=(temp, kind, True, requested1, entered1, release, output))
                second = ctx.Process(target=_process_fetch, args=(temp, kind, False, requested2, entered2, release, output))
                processes = []
                try:
                    first.start()
                    processes.append(first)
                    self.assertTrue(entered1.wait(10))
                    second.start()
                    processes.append(second)
                    self.assertTrue(requested2.wait(10))
                    self.assertFalse(entered2.wait(0.2), "process read cache without waiting for publisher")
                    release.set()
                    for process in processes:
                        process.join(timeout=10)
                        self.assertEqual(process.exitcode, 0)
                    self.assertEqual(dict(output.get(timeout=5) for _ in range(2)),
                                     {True: [0, 3600, 7200, 10800], False: [7200, 10800]})
                    key = "funding" if kind == "funding" else "1h"
                    cached = pd.read_csv(Path(temp) / f"ETH_USDT_{key}.csv")
                    self.assertEqual(cached.timestamp.tolist(), [0, 3600, 7200, 10800])
                    if kind == "funding":
                        self.assertEqual(cached.funding_rate.tolist(), [0.001, 0.001, -0.002, -0.002])
                    else:
                        self.assertEqual(cached.close.tolist(), [100.0, 100.0, 105.0, 105.0])
                finally:
                    release.set()
                    for process in processes:
                        if process.is_alive():
                            process.terminate()
                        process.join(timeout=5)
                        process.close()
                    output.close()
                    output.join_thread()

    def test_terminated_process_releases_lock_without_deleting_sidecar(self):
        ctx = multiprocessing.get_context("spawn")
        with tempfile.TemporaryDirectory() as temp:
            requested1, entered1, requested2, entered2, release = (ctx.Event() for _ in range(5))
            path = str(Path(temp) / "ETH_USDT_1h.csv")
            first = ctx.Process(target=_process_hold_lock, args=(path, requested1, entered1, None))
            second = ctx.Process(target=_process_hold_lock, args=(path, requested2, entered2, release))
            processes = []
            try:
                first.start()
                processes.append(first)
                self.assertTrue(entered1.wait(10))
                second.start()
                processes.append(second)
                self.assertTrue(requested2.wait(10))
                self.assertFalse(entered2.wait(0.2))
                first.terminate()
                first.join(timeout=5)
                self.assertIsNotNone(first.exitcode)
                self.assertTrue(entered2.wait(10), "OS lock should be released on process death")
                release.set()
                second.join(timeout=10)
                self.assertEqual(second.exitcode, 0)
                self.assertTrue(Path(path + ".lock").exists())
            finally:
                release.set()
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=5)
                    process.close()


if __name__ == "__main__":
    unittest.main()
