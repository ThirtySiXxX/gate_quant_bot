# QF-QD-009-S0702-RECEIPT-REPAIR

Date: 2026-10-28 Australia/Melbourne.
Dispatch: QF-DISPATCH-20261028-QD009-S0702-RECEIPT-REPAIR-1.

**Delivery: source repair of launcher recording/error handling, static check
only. No launcher entry, help/default invocation, child process, process probe,
test or new execution attempt. Runtime behavior is NOT VERIFIED.**

The accepted prior result remains: S07.02 started once, its approval is consumed,
and assertions are UNKNOWN. This task neither re-audits that evidence nor claims
to recover its missing measurements. It does not authorize another S07.02 run.

## Claim and preservation

- Role: QD; branch `codex/qd-cache-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Clean starting HEAD: `60549aa9ae7045d11214378f35b2f0e8cabe77c6`.
- Only changed source: `research/qd009/s0702_launcher.py`.
- Only new file: this report. Existing reports, generated evidence, journals,
  ignore rules, ledger, fixture, oracle, original main and trading rules untouched.
- No dependency/environment changes, privilege escalation, channel change,
  OS-refusal probe, QR/chat/subagent work, model fit, replay, integration or push.

## Concrete repair

1. Immediately after `Popen` returns, append and fsync `CHILD_LAUNCHED` to the
   run-local `lifecycle.jsonl`, with PID, parent launch-start timestamp and
   Popen-return observation timestamp. PID persists independently of the final
   result. Exact OS process-birth time is explicitly null, not invented from
   the parent clock. The child wrapper additionally emits a flushed
   `CHILD_CODE_ENTERED` JSON line with its own PID/UTC timestamp before fixture
   import; parent log chunks now flush/fsync. This denotes wrapper-code entry
   after stdlib imports, not kernel process birth or a completed fixture.
2. Append/fsync measurement snapshots at a 100 ms target interval, plus launch,
   reap, termination and supervision-end phases. These retain parent elapsed
   time, sampled peak/count/maximum observed inter-sample gap and output debits.
   This is independent of the unchanged 10 ms target RSS sampling interval.
   Actual gaps can be longer due to scheduling/I/O. A partial last append is
   possible on interruption; prior complete durable records remain useful.
3. Make `stop` idempotent under a reentrant lock. Mark the signal attempt before
   its syscall and record requested/returned timestamps, target PID/group,
   signal, reason, submission outcome and any error/errno. `PermissionError`
   and other termination exceptions are retained rather than rethrown through
   repeated cleanup attempts. At most one `killpg` submission per attempt;
   no direct-PID fallback, alternate channel, escalation or permission bypass.
4. Distinguish accepted signal submission, no-such-process response, submission
   failure and confirmed child exit. Only successful PID-specific `wait4`
   reaping sets `child_exit_confirmed` and supplies exit/signal/CPU/post-exit RSS.
   No `ps` inference or signal-success assumption is added. Reaping itself is
   phase-recorded so those measurements need not wait for the final receipt.
5. Cleanup uses nonblocking `wait4(WNOHANG)` and catches close/reap errors.
   A denied kill does not lead to an unbounded blocking wait before recording.
   After the one stop request, supervision stops; a still-unreaped child is
   explicitly potentially running. This does not make an unkillable child safe
   or establish that it obeyed the deadline.
6. Preserve a final-receipt allocation and attempt `result.json` after cleanup,
   including PID, termination request/result, errors, recovered observations,
   exit confirmation and explicit UNKNOWN/null reasons. Supervision-end time is
   labeled separately from child-end time. No samples means peak is null; no
   successful reap means exit/CPU/post-exit peak remain null. A permission error
   or unresolved child exit cannot produce PASS. Failed final writes retain any
   partial file and emit a bounded console failure; no overwrite/write retry.

## Fixed budgets and once-only gate

The hardcoded evidence directory is unchanged:
`research/.data/qd009/stream-repair-r1/tmp/approved-s07-02-once/`.
Its existing-directory refusal remains `mkdir(exist_ok=False)`, before any new
run-local file creation. No alternate path, directory cleanup or retry option.
This task did not open, enumerate or modify the old run directory.

Resource numbers remain: pre-Popen parent deadline 10 seconds, sampled RSS
threshold 268435456 bytes with 10 ms target sampling, output total 33554432 bytes.
Within the existing 512 KiB receipt reservation, lifecycle writes leave 128 KiB
for finalization, including prepaid console space. Artifact (31 MiB) and merged
child-log (512 KiB) allocations remain unchanged; lifecycle bytes are not extra.
Lifecycle/log write debits are conservative even if a write/fsync fails. Final
`log_bytes_issued_upper` names the upper-bound debit; it is not a claim about
successfully persisted bytes or physical device traffic.

The unchanged financial modules and pins are:

| File | SHA256 |
| --- | --- |
| `research/qd009/streaming_ledger.py` | `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb` |
| `tests/test_qd_streaming_ledger.py` | `3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969` |
| `research/qd007/event_ledger.py` | `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636` |
| `tests/test_qd_event_ledger.py` | `aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8` |

The wrapper still calls unchanged `run_case('S07.02', out / 'case', 0)` once.
No financial assertions, oracle outputs, fixture size or acceptance criteria are
changed. The wrapper's own entry marker is additional operational output only.

## Static verification

One syntax/static command is allowed: parse/compile the outer launcher and its
literal child without executing either, plus literal PINS/hash comparison.
No launcher import is needed. Results and new launcher hash are recorded after
that one command; no runtime result will be inferred from syntax success.

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -I -B - <<'PY'
import ast
import hashlib
from pathlib import Path
path = Path('research/qd009/s0702_launcher.py')
tree = ast.parse(path.read_text(), filename=str(path))
compile(tree, str(path), 'exec')
values = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}
child = ast.literal_eval(values['CHILD'])
compile(ast.parse(child, filename='<S07.02 child literal>'), '<S07.02 child literal>', 'exec')
for name, expected in ast.literal_eval(values['PINS']).items():
    if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
        raise SystemExit('PIN MISMATCH: ' + name)
print('PASS: outer/child AST and compile; four pins unchanged; no launcher code executed')
print('launcher_sha256=' + hashlib.sha256(path.read_bytes()).hexdigest())
PY
```

- Syntax/static result: **PASS**, one command, exit 0. Outer and literal-child
  AST/compile succeeded; all four source hashes matched. No compiled object or
  launcher code was executed.
- New launcher SHA256:
  `0c0bf0b6e964b911f9a23cd75586264ce4318a34f81b6aebcebd1ffa59530480`.
- Git whitespace/scope: `git diff --check` passed; status contained only the
  claimed launcher modification and this new report. Staged check before commit.
- Runtime processes/attempts/tests/probes this task: 0.

## Limits and smallest future verification choice

Unverified: lifecycle/PID durability, the permission-denied path, final receipt
after cleanup errors, signal/reap races, output partition behavior, and timing
overhead under real execution. `fsync` is requested; host/storage failure or a
parent killed before recording can still lose records. Finalization cannot be
guaranteed under host death or failed storage. The underlying OS refusal is
neither diagnosed nor fixed. A denied signal can leave a child running; an
accepted signal is still not an exit receipt. No extra termination request or
background supervision is added after the platform refuses the action.

The 10-second deadline is unchanged and is not claimed sufficient for S07.02.
Lifecycle/log fsync adds overhead inside it. Scheduling and signal delivery can
overshoot; sampling is not a hard RSS limit. The fixed output budget still relies
on the pinned application's existing budget-aware writes, not a kernel sandbox.

One concrete optional follow-up, **proposal only, requires separate approval**:
run a single synthetic supervisor check in a disposable test directory. A small
helper writes one startup line, then exits by itself within 1 second. An external
test harness substitutes that helper for `Popen`'s S07.02 command, forces one RSS
reading above the threshold and injects `PermissionError(EPERM)` for `killpg`.
Assert the durable PID/start and phase records, exactly one rejected signal
submission, a final FAIL record with UNKNOWN exit/CPU when unreaped, and unchanged
budget/once-directory refusal. The helper's natural short lifetime avoids a
deliberately persistent orphan; it must never import or execute the ledger or
fixture. Dependency injection belongs to that separately reviewed test harness,
not a new launcher CLI mode. This proposal was not written or run this task.

The original 512-body test cannot be rerun on this approval. Its existing run
directory must not be bypassed, renamed or removed to enable another attempt.
Any future S07.02 execution needs a new explicit human decision, with the prior
failure and unchanged resource budget visible.

## Handoff

Completed: scoped receipt/error-handling repair and this report. Files modified
are exactly the two claimed paths. QR dependency: none; no shared financial
contract changes. Next step: coordinator reviews the exact commit and selects
whether to request the synthetic verification; this task stops after its own
commit. No further test, process probe, integration, push or trading action.
