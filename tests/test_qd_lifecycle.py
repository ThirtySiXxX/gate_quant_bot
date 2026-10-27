"""Offline regressions for engine termination and backtest worker ownership."""
import concurrent.futures
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.backtest_runner import BacktestController, BacktestJob
from src.config import SystematicConfig
from src.engine import EngineController


def credentials():
    return SimpleNamespace(load=lambda: SimpleNamespace(
        is_set=True, api_key="synthetic-key", api_secret="synthetic-secret", api_host="unused"))


class EngineLifecycleTests(unittest.TestCase):
    def controller(self):
        state = SimpleNamespace(engine_running=True, engine_started_at=123.,
                                switch_mode=Mock(), add_log=Mock())
        return EngineController(SimpleNamespace(snapshot=lambda: {"mode": "paper"}),
                                credentials(), state)

    def test_stop_timeout_remains_running_and_cannot_start_second_engine(self):
        controller = self.controller()
        release = threading.Event()
        stop_requested = threading.Event()
        controller.engine = SimpleNamespace(stop=stop_requested.set)
        controller.thread = threading.Thread(target=release.wait)
        controller.thread.start()
        original_join = controller.thread.join
        try:
            with patch.object(controller.thread, "join", side_effect=lambda timeout: original_join(0)):
                ok, message = controller.stop()
            self.assertFalse(ok)
            self.assertIn("超时", message)
            self.assertTrue(stop_requested.is_set())
            self.assertTrue(controller.state.engine_running)
            self.assertTrue(controller.status()["running"])
            with patch.object(controller.cred_store, "load", side_effect=AssertionError("must not restart")):
                self.assertFalse(controller.start()[0])
        finally:
            release.set()
            original_join(2)
        self.assertFalse(controller.stop()[0])
        self.assertFalse(controller.state.engine_running)

    def test_successful_stop_waits_for_worker_exit(self):
        controller = self.controller()
        release = threading.Event()
        controller.engine = SimpleNamespace(stop=release.set)
        controller.thread = threading.Thread(target=release.wait)
        controller.thread.start()
        self.addCleanup(controller.thread.join, 2)
        self.addCleanup(release.set)
        self.assertTrue(controller.stop()[0])
        self.assertFalse(controller.thread.is_alive())
        self.assertFalse(controller.state.engine_running)

    def test_start_failure_does_not_leave_running_flag(self):
        controller = self.controller()
        controller.state.engine_running = False
        with patch("src.engine.GateExchange"), patch("src.engine.PaperExchange"), \
                patch("src.engine.SystematicEngine"), \
                patch("src.engine.threading.Thread.start", side_effect=RuntimeError("worker unavailable")):
            ok, message = controller.start()
        self.assertFalse(ok)
        self.assertIn("worker unavailable", message)
        self.assertFalse(controller.state.engine_running)
        self.assertFalse(controller.is_running())
        self.assertEqual(controller.state.engine_started_at, 123.)

    def test_thread_construction_failure_returns_error_without_false_start(self):
        controller = self.controller()
        controller.state.engine_running = False
        with patch("src.engine.GateExchange"), patch("src.engine.PaperExchange"), \
                patch("src.engine.SystematicEngine"), \
                patch("src.engine.threading.Thread", side_effect=RuntimeError("cannot allocate worker")):
            ok, message = controller.start()
        self.assertFalse(ok)
        self.assertIn("cannot allocate worker", message)
        self.assertFalse(controller.state.engine_running)
        self.assertEqual(controller.state.engine_started_at, 123.)


class BacktestAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.controller = BacktestController(SimpleNamespace(snapshot=lambda: {}), credentials(),
                                             temporary.name, temporary.name)

    def test_simultaneous_requests_cannot_exceed_worker_limit(self):
        contenders = 8
        prepared = threading.Barrier(contenders, timeout=5)
        release = threading.Event()
        workers = []
        workers_lock = threading.Lock()
        build = SystematicConfig.build

        def prepare(config):
            prepared.wait()  # Synchronize at the old check/insert race window.
            return build(config)

        def worker(job, *args):
            with workers_lock:
                workers.append(threading.current_thread())
            release.wait(5)
            job.status = "done"

        def request():
            try:
                return self.controller.start_job(["ETH_USDT"], 1)
            except RuntimeError as exc:
                return exc

        try:
            with patch("src.backtest_runner.SystematicConfig.build", side_effect=prepare), \
                    patch.object(self.controller, "_run_job", side_effect=worker), \
                    concurrent.futures.ThreadPoolExecutor(max_workers=contenders) as pool:
                results = list(pool.map(lambda _: request(), range(contenders)))
            accepted = [r for r in results if isinstance(r, BacktestJob)]
            self.assertEqual(len(accepted), self.controller.MAX_CONCURRENT)
            self.assertEqual(self.controller._active_count(), self.controller.MAX_CONCURRENT)
        finally:
            release.set()
            for worker_thread in workers:
                worker_thread.join(2)

    def test_thread_start_failure_releases_reservation(self):
        with patch("src.backtest_runner.threading.Thread.start", side_effect=RuntimeError("no worker")):
            with self.assertRaisesRegex(RuntimeError, "no worker"):
                self.controller.start_job(["ETH_USDT"], 1)
        self.assertEqual(self.controller._active_count(), 0)
        self.assertEqual(self.controller.list_jobs(), [])

    def test_active_job_cannot_be_deleted_to_bypass_admission(self):
        for status in ("pending", "fetching", "running"):
            with self.subTest(status=status):
                job = BacktestJob("active", ["ETH_USDT"], 1, 1000, status=status)
                self.controller._jobs[job.id] = job
                self.assertFalse(self.controller.delete_job(job.id))
                self.assertIs(self.controller.get_job(job.id), job)

    def test_finished_job_can_be_deleted(self):
        job = BacktestJob("finished", ["ETH_USDT"], 1, 1000, status="done")
        self.controller._jobs[job.id] = job
        self.controller._persist(job)
        path = Path(self.controller.result_dir) / "finished.json"
        self.assertTrue(path.exists())
        self.assertTrue(self.controller.delete_job(job.id))
        self.assertFalse(path.exists())
        self.assertIsNone(self.controller.get_job(job.id))

    def test_delete_during_completion_does_not_resurrect_result_file(self):
        controller = self.controller
        job = BacktestJob("finishing", ["ETH_USDT"], 1, 1000)
        controller._jobs[job.id] = job
        persist_started, release, deleted = (threading.Event() for _ in range(3))
        persist = controller._persist
        delete_results = []

        def delayed_persist(record):
            persist_started.set()
            if not release.wait(5):
                raise AssertionError("test did not release persistence")
            persist(record)

        def delete():
            delete_results.append(controller.delete_job(job.id))
            deleted.set()

        worker = threading.Thread(target=controller._run_job,
            args=(job, "usdt", credentials().load(), {}, SystematicConfig(), 1000))
        deleter = threading.Thread(target=delete)
        try:
            with self.assertLogs("bot.backtest_runner", level="ERROR"), \
                    patch("src.exchange_gate.GateExchange", side_effect=RuntimeError("synthetic failure")), \
                    patch.object(controller, "_persist", side_effect=delayed_persist):
                worker.start()
                self.assertTrue(persist_started.wait(2))
                deleter.start()
                deleted.wait(.05)  # Old code deletes before the pending write.
                release.set()
                worker.join(2)
                deleter.join(2)
        finally:
            release.set()
            if worker.ident is not None:
                worker.join(2)
            if deleter.ident is not None:
                deleter.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(deleter.is_alive())
        self.assertEqual(delete_results, [True])
        self.assertIsNone(controller.get_job(job.id))
        self.assertFalse((Path(controller.result_dir) / "finishing.json").exists())


if __name__ == "__main__":
    unittest.main()
