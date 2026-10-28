# QF-QD-009-S0702-SAMPLED-RUN

Date: 2026-10-28 Australia/Melbourne; runtime timestamps below are UTC.
Dispatch: QF-DISPATCH-20261028-QD009-S0702-SAMPLED-RUN-1.

**Result: FAIL — execution supervision failed. The single authorized attempt
started a child and is consumed. S07.02 assertion outcome is UNKNOWN, not PASS
or a demonstrated financial assertion failure. No retry or repair was made.**

The parent reached its wall-deadline branch, but `os.killpg(..., SIGKILL)` raised
`PermissionError: [Errno 1] Operation not permitted`. Error handling and cleanup
called the same operation and raised again. Launcher exited 1 without producing
`result.json`. Its requested termination is not evidence of successful termination
or successful cap enforcement. The precise cause of the OS refusal was not probed.

## Authorization, identity and preservation

The coordinator relayed the direct human answer “接受监测方式，执行一次（推荐）”.
It explicitly accepted 10 ms target RSS sampling, termination above 256 MiB and
post-exit peak disclosure, possible between-sample overshoot, the 10-second parent
deadline including scheduling delay, 32 MiB output, and one attempt with no retry.

- Role/branch: QD / `codex/qd-cache-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Exact delivery HEAD before execution:
  `c7390d9f21fabacf17987de06f8c5e6aef9082e5`; initial worktree clean.
- Financial candidate: `0cdbfbdaf047727d0ff4d20d5ee670891e49b070`.
- Both the fixed run directory and this report were absent before the attempt.
- Only this new report is committed. Launcher, ledger, fixture, oracle, old
  evidence, ignore rules, shared journals, main and trading rules are unchanged.
- No other test, default-entry probe, tool self-test, source repair, benchmark,
  replay, fit, dependency installation, integration/push, engine, account,
  Windows or NAS action. No QR recheck or cross-chat reply.

Static SHA256 checks before and after the attempt matched exactly:

| File | SHA256 |
| --- | --- |
| `research/qd009/s0702_launcher.py` | `ea508282c10cf788357940a2f7039e81a2f10becb2ad1ee915c377bca0fe58ed` |
| `research/qd009/streaming_ledger.py` | `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb` |
| `tests/test_qd_streaming_ledger.py` | `3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969` |
| `research/qd007/event_ledger.py` | `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636` |
| `tests/test_qd_event_ledger.py` | `aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8` |

## Exact command and execution record

Executed once, from the worktree above:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -I -B research/qd009/s0702_launcher.py --run-once-with-sampled-rss
```

The tool initially returned running session `13571`. One `write_stdin` poll read
completion of that same process; this was not a second invocation or retry.

| Item | Actual evidence |
| --- | --- |
| Launcher invocations / test-child attempts / retries | 1 / 1 / 0 |
| Other tests, tool probes, benchmarks, fits | 0 |
| Interpreter | Existing project venv Python 3.13.7, Clang 16.0.0 |
| Persisted prelaunch timestamp | `2026-10-28T12:32:57.735099+00:00` in `started.json` |
| Exact child start / child PID | Unknown; not persisted |
| Exact parent/child end timestamp | Unknown; no final receipt |
| Launcher exit code / signal | 1 / no signal exit reported by tool |
| Child exit code / terminating signal | Unknown; parent did not collect/persist them |
| Wall duration | Unknown numerically; traceback proves the `now >= deadline` branch was reached, whose deadline was 10 s after pre-Popen timing start |
| CPU user/system | Unknown; no persisted `wait4` result |
| Sampled RSS peak / sample count / maximum gap | Unknown; parent-local measurements were lost |
| Post-exit peak RSS | Unknown; no persisted `wait4` result |
| Merged child stdout/stderr | `child-output.log`: 0 bytes |
| Final structured fixture result | Missing; `result.json` does not exist |
| Retained evidence bytes at inspection | 21,933,080 bytes across 14 files |
| Parent terminal stderr | Traceback below; no separate stderr file/byte counter was produced |
| Original S07.02 checks | UNKNOWN; no completed child result or assertion list |

Do not add tool wait durations to infer total test lifetime. Do not replace
unknown RSS/CPU/end values with zero. Retained output is below 33,554,432 bytes
at inspection, but this is not proof of a peak, cumulative-I/O or hard-cap result.

At `2026-10-28T12:33:32Z`, the post-failure read-only command
`ps -axo pid=,ppid=,pgid=,etime=,comm= | rg 'Python|python|s0702'` returned no
matching processes. This is a process-name snapshot, not PID-specific exit/signal
evidence: the child PID was not saved. No further termination command was issued.

## Preserved failure evidence

Evidence remains, unmodified and ignored, exclusively under:
`research/.data/qd009/stream-repair-r1/tmp/approved-s07-02-once/`.
No files were cleaned, moved, overwritten or reopened through the ledger.
The inventory below is a read-only stat snapshot, not a checkpoint/result audit.

| Relative path under run root | Bytes |
| --- | ---: |
| `started.json` | 1,131 |
| `child-output.log` | 0 |
| `artifacts/aggregate-resource.jsonl` | 653,760 |
| `artifacts/case/fixture0/source/facts.jsonl` | 2,717,547 |
| `artifacts/case/fixture0/source/raw.jsonl` | 2,595,045 |
| `artifacts/case/fixture0/store/CONTROL` | 102 |
| `artifacts/case/fixture0/store/GENESIS` | 18,951 |
| `artifacts/case/fixture0/store/HEAD` | 262 |
| `artifacts/case/fixture0/store/LEASE` | 0 |
| `artifacts/case/fixture0/store/RESOURCE_LOG` | 118,878 |
| `artifacts/case/fixture0/store/cache.sqlite3` | 13,201,408 |
| `artifacts/case/fixture0/store/cache.sqlite3-journal` | 13,824 |
| `artifacts/case/fixture0/store/control-00000001.json` | 760 |
| `artifacts/case/fixture0/store/guard-input-00000001.json` | 2,611,412 |

Latest observed artifact mtime was `2026-10-28T12:33:07.736248+00:00`
on `cache.sqlite3`. File mtimes do not establish child completion or assertion
progress. The original pinned 512-body fixture was invoked; its generated files
prove execution began, not that checkpoint/restore or L1.38 checks completed.

Exact launcher terminal output returned by the execution tool:

```text
Traceback (most recent call last):
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 201, in main
    stop("WALL_DEADLINE")
    ~~~~^^^^^^^^^^^^^^^^^
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 154, in stop
    os.killpg(state["pid"], signal.SIGKILL)
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 228, in main
    stop("SUPERVISOR_ERROR")
    ~~~~^^^^^^^^^^^^^^^^^^^^
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 154, in stop
    os.killpg(state["pid"], signal.SIGKILL)
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 282, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 231, in main
    stop("SUPERVISOR_CLEANUP")
    ~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qd009/s0702_launcher.py", line 154, in stop
    os.killpg(state["pid"], signal.SIGKILL)
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted
```

## Outcome and handoff

- Completed: the exact one authorized execution, preserved failed evidence and
  honest failure report. This attempt cannot be represented as BLOCKED/unused.
- Modified file: this report only. Runtime files remain ignored; no source edit.
- Checks: static Git/identity/path checks, the single runtime command above,
  and bounded read-only receipt/log/inventory/process inspection. Git whitespace
  and report-only staged scope are checked before committing; no extra tests.
- Limitation: process-group termination failed and final measurement persistence
  failed. S07.02 remains unvalidated. No whole-ledger, native-readiness, larger
  validation, research-profitability or training-readiness claim follows.
- Other-agent dependency: none; QR014 is independent and was not inspected.
- Recommended next step: coordinator reviews this failed attempt and decides any
  separate follow-up. The existing once-only directory remains claimed; there is
  no permission here to repair the launcher, bypass that directory or rerun.
  Stop after this report commit; no main integration or push.
