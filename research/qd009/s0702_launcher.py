"""One S07.02 launcher, not a validation suite.

Default: BLOCKED without starting a child or creating evidence. macOS provides
no established hard RSS mechanism here. The explicit sampled-RSS mode requires
separate human acceptance of that weaker control; it is not the old approval.
No retries, arbitrary commands, alternate cases or adjustable resource limits.
"""
from pathlib import Path
import argparse
import ctypes
import datetime
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research/.data/qd009/stream-repair-r1/tmp/approved-s07-02-once"
CANDIDATE = "0cdbfbdaf047727d0ff4d20d5ee670891e49b070"
PINS = {
    "research/qd009/streaming_ledger.py": "251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb",
    "tests/test_qd_streaming_ledger.py": "3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969",
    "research/qd007/event_ledger.py": "7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636",
    "tests/test_qd_event_ledger.py": "aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8",
}
MIB = 1024 ** 2
WALL = 10.0
RSS = 256 * MIB
POLL = 0.010
ARTIFACT_BYTES = 31 * MIB
LOG_BYTES = MIB // 2
RECEIPT_BYTES = MIB // 2

# Run unchanged fixture code once. -I -B prevents environment path injection and
# bytecode files; the candidate's existing VFS/application budget guards artifacts.
CHILD = r'''
from pathlib import Path
import hashlib, importlib.util, json, os, resource, sys, traceback
root, out = Path(sys.argv[1]), Path(sys.argv[2])
pins = json.loads(sys.argv[3])
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
for name, expected in pins.items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
        print(json.dumps(dict(status='FAIL', reason='IDENTITY_MISMATCH', file=name)))
        raise SystemExit(1)
def no_processes(event, args):
    if event in ('subprocess.Popen', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec'):
        raise RuntimeError('S07.02 launcher forbids descendants')
sys.addaudithook(no_processes)
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('_approved_s0702', root / 'tests/test_qd_streaming_ledger.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
t.sl.configure_resource_budget(out, 31 * 1024 ** 2)
try:
    result = t.run_case('S07.02', out / 'case', 0)
    print(json.dumps(result, sort_keys=True), flush=True)
    code = 0 if result.get('status') == 'PASS' else 1
except BaseException as error:
    code = 3 if getattr(error, 'code', '') in ('RESOURCE_EXHAUSTED', 'RESOURCE_EXHAUSTED_READ') else 1
    print(json.dumps(dict(status='CAP' if code == 3 else 'FAIL',
                         exception=type(error).__name__, reason=str(error)[:2048],
                         traceback=traceback.format_exc()[-8192:])), flush=True)
raise SystemExit(code)
'''


class TaskInfo(ctypes.Structure):
    # SDK sys/proc_info.h: six uint64_t followed by twelve int32_t fields.
    _fields_ = [(name, ctypes.c_uint64) for name in
                ("virtual", "resident", "user", "system", "threads_user", "threads_system")]
    _fields_ += [("counter_" + str(i), ctypes.c_int32) for i in range(12)]


def rss_reader():
    lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    call = lib.proc_pidinfo
    call.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    call.restype = ctypes.c_int

    def read(pid):
        info = TaskInfo()
        if call(pid, 4, 0, ctypes.byref(info), ctypes.sizeof(info)) != ctypes.sizeof(info):
            raise OSError(ctypes.get_errno(), "proc_pidinfo failed")
        return info.resident
    return read


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def encode(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def receipt(name, value, remaining):
    raw = encode(value)
    if len(raw) > remaining:
        raise RuntimeError("parent receipt reservation exhausted before write")
    with (OUT / name).open("xb") as dest:
        dest.write(raw)
        dest.flush()
        os.fsync(dest.fileno())
    return remaining - len(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-once-with-sampled-rss", action="store_true",
                        help="requires NEW human acceptance: 10ms RSS sampling is not a hard cap")
    args = parser.parse_args()
    if not args.run_once_with_sampled_rss:
        print(encode(dict(status="BLOCKED", test_processes_started=0,
                          reason="HARD_RSS_UNAVAILABLE; sampled mode needs explicit human acceptance")).decode(), end="")
        return 2
    if sys.platform != "darwin":
        raise RuntimeError("this fixed launcher supports macOS only")
    identities = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PINS}
    if identities != PINS:
        raise RuntimeError("pinned candidate/fixture/oracle mismatch; no child started")
    read_rss = rss_reader()  # Load ABI before claiming evidence or starting a child.
    # A persistent exclusive directory is the once-only claim, including failures.
    # Refuse symlinks/aliases in the pre-existing evidence parent.
    if OUT.parent.resolve() != OUT.parent or OUT.is_symlink():
        raise RuntimeError("evidence path alias refused")
    OUT.mkdir(exist_ok=False)
    artifacts = OUT / "artifacts"
    artifacts.mkdir()
    base = dict(case="S07.02", variant=0, candidate_commit=CANDIDATE,
                identities=identities,
                launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                python=sys.executable, python_version=sys.version,
                control_mode="SAMPLED_RSS_NOT_HARD", rss_limit_bytes=RSS,
                rss_poll_target_seconds=POLL, wall_limit_seconds=WALL,
                output_limit_bytes=32 * MIB, artifact_limit_bytes=ARTIFACT_BYTES,
                log_limit_bytes=LOG_BYTES, receipt_reservation_bytes=RECEIPT_BYTES)
    remaining = receipt("started.json", dict(base, started_at=utc(), status="PRELAUNCH"), RECEIPT_BYTES)
    state = dict(pid=None, reason=None)
    lock = threading.Lock()

    def stop(reason):
        with lock:
            if state["reason"] is None:
                state["reason"] = reason
            if state["pid"] is not None:
                try:
                    os.killpg(state["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass

    child = None
    usage = None
    code = None
    peak = samples = written = 0
    max_gap = 0.0
    last_sample = None
    error = None
    selector = selectors.DefaultSelector()
    # Start before Popen: interpreter startup, imports and fixture setup count.
    started_at = utc()
    start = time.monotonic()
    deadline = start + WALL
    watchdog = threading.Timer(max(0, deadline - time.monotonic()), stop, ("WALL_DEADLINE",))
    watchdog.daemon = True
    watchdog.start()
    try:
        with (OUT / "child-output.log").open("xb") as log:
            child = subprocess.Popen(
                [sys.executable, "-I", "-B", "-u", "-c", CHILD, str(ROOT), str(artifacts), json.dumps(PINS)],
                cwd=ROOT, env={"PATH": os.defpath, "TMPDIR": str(artifacts),
                               "QD009_CODE_COMMIT": CANDIDATE},
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                start_new_session=True)
            with lock:
                state["pid"] = child.pid
            if state["reason"] is not None:
                stop(state["reason"])
            os.set_blocking(child.stdout.fileno(), False)
            selector.register(child.stdout, selectors.EVENT_READ)
            while code is None or selector.get_map():
                if code is None:
                    with lock:
                        pid, status, observed_usage = os.wait4(child.pid, os.WNOHANG)
                        if pid:
                            state["pid"] = None
                    if pid:
                        code = os.waitstatus_to_exitcode(status)
                        child.returncode = code
                        usage = observed_usage
                        watchdog.cancel()
                    else:
                        now = time.monotonic()
                        if now >= deadline:
                            stop("WALL_DEADLINE")
                        try:
                            value = read_rss(child.pid)
                            peak = max(peak, value)
                            samples += 1
                            if last_sample is not None:
                                max_gap = max(max_gap, now - last_sample)
                            last_sample = now
                            if value > RSS:
                                stop("SAMPLED_RSS_EXCEEDED")
                        except OSError:
                            # Includes the exit/sample race: conservative stop,
                            # never reinterpret unavailable telemetry as zero RSS.
                            stop("RSS_SAMPLE_UNAVAILABLE")
                for key, _ in selector.select(max(0, min(POLL, deadline - time.monotonic())) if code is None else 0):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    allowed = min(len(data), LOG_BYTES - written)
                    if allowed:
                        log.write(data[:allowed])  # Pre-write accounting, not size polling.
                        written += allowed
                    if allowed != len(data):
                        stop("LOG_OUTPUT_EXCEEDED")
    except BaseException as exc:
        error = type(exc).__name__ + ": " + str(exc)[:1024]
        stop("SUPERVISOR_ERROR")
    finally:
        if child is not None and code is None:
            stop("SUPERVISOR_CLEANUP")
            with lock:
                _, status, usage = os.wait4(child.pid, 0)
                state["pid"] = None
            code = os.waitstatus_to_exitcode(status)
            child.returncode = code
        watchdog.cancel()
        selector.close()
        if child is not None and child.stdout is not None:
            child.stdout.close()
    elapsed = time.monotonic() - start
    if elapsed > WALL and state["reason"] is None:
        state["reason"] = "WALL_EXCEEDED"
    if usage is not None and usage.ru_maxrss > RSS and state["reason"] is None:
        state["reason"] = "POST_EXIT_RSS_EXCEEDED"
    result = None
    try:
        last_line = (OUT / "child-output.log").read_bytes().splitlines()[-1]
        if len(last_line) <= 32768:
            result = json.loads(last_line)
    except (OSError, ValueError, IndexError):
        pass
    status = "CAP" if state["reason"] or code == 3 else "FAIL"
    if (code == 0 and not state["reason"] and isinstance(result, dict)
            and result.get("status") == "PASS" and result.get("fixtures") == 1
            and result.get("metrics", {}).get("bodies") == 512):
        status = "PASS"
    evidence_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    final = dict(base, status=status, test_processes_started=int(child is not None),
                 started_at=started_at, ended_at=utc(), wall_seconds=elapsed,
                 exit_code=code, signal=-code if code is not None and code < 0 else None,
                 stop_reason=state["reason"], supervisor_error=error,
                 sampled_peak_rss_bytes=peak, rss_samples=samples, max_sample_gap_seconds=max_gap,
                 post_exit_peak_rss_bytes=usage.ru_maxrss if usage else None,
                 cpu_user_seconds=usage.ru_utime if usage else None,
                 cpu_system_seconds=usage.ru_stime if usage else None,
                 log_bytes=written, evidence_bytes_before_final=evidence_bytes,
                 child_result=result, retries=0)
    raw = encode(final)
    if evidence_bytes + len(raw) > 32 * MIB:
        # No overwrite/delete to disguise an overrun; retain explicit failure.
        final.update(status="CAP", stop_reason="ARTIFACT_ACCOUNTING_OVERRUN")
    summary = encode(dict(status=final["status"], receipt=str(OUT / "result.json")))
    if len(summary) > remaining:
        raise RuntimeError("console reservation exhausted before write")
    receipt("result.json", final, remaining - len(summary))
    sys.stdout.write(summary.decode())
    return 0 if final["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
