# QD engineering audit and lifecycle milestone

Date: 2026-10-27, Australia/Melbourne. New Senior QD instructions authorize local
engineering changes/tests and feature-branch commits. Prior shared-document
integration remains paused; the other QR chat owns that in-progress cleanup.

## Claim and baseline

- Role: QD. Branch: `codex/qd-lifecycle-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-lifecycle-safety/gate_quant_bot`.
- Source HEAD: `cae0d2395adf2cd3905e41cb1c16748c8247c32c`.
- Isolated source snapshot: `475aaeaa5b9365b360563294e183d912c382b570`.
  This records existing local source/WIP, including staged deletions, to make the
  QD delta reviewable. It is not an approved common baseline, integration or
  authorship claim for that earlier work. The primary HEAD/index were untouched.
- Exclusive changes: `src/engine.py`, `src/backtest_runner.py`,
  `tests/test_qd_lifecycle.py`, this role-local report. No QR mathematical files
  or shared contract/schema files are in this milestone's write scope.
- Baseline: 153 Python tests pass in the isolated checkout with socket connects
  blocked. Original interpreter reused read-only; no dependencies installed.
- Snapshot whitespace check reports three inherited EOF blank lines in
  strategy_execution.py, test_crypto_ml.py and test_history_gaps.py; preserved.
  This milestone's delta must pass `git diff --check` independently.

## Architecture assessment

The modular Python monolith fits the present workload. Flask/lifecycle and
backtest controllers orchestrate data/execution adapters; shared signal and
order-policy modules reduce research/runtime divergence. CSV/SQLite/JSON storage
is adequate for local use but has process-local synchronization boundaries.
No rewrite, microservices or C++ acceleration is justified by current evidence.

The important dependency direction is market data -> causal features/signals ->
allocation/policy -> risk and execution adapters -> recorded fills/state/reports.
QR owns mathematical/ML definitions; QD owns admission, lifecycle, persistence,
execution and infrastructure. Runtime paths currently use the native interface
registry; the standalone envelope proposal is not an adopted replacement.

## Prioritized engineering backlog

| Category / priority | Finding | Practical next step |
| --- | --- | --- |
| Correctness / P1 | Stop joins 15 seconds then reports success even if worker remains alive | This milestone: truthfully report timeout, retain running state and duplicate-start protection |
| Reliability / P1 | Admission count and insertion are separate; deleting active jobs frees the count while workers run | This milestone: atomic reservation and active-job retention |
| Reliability / P1 | Thread creation failure leaks pending job/running flag; terminal deletion can race persistence | This milestone: rollback and serialize deletion/final persistence |
| Execution risk / P1 | An in-flight order timeout is uncertain; complete durable order intent/idempotency reconciliation is not established by this audit | Separate synthetic timeout/fill/restart audit before retry-policy changes |
| Data reliability / P1 | CSV cache writes are direct and unlocked | Separate atomic per-key cache-write/merge task with failure and concurrent-writer tests |
| Execution risk / P1 | Volatility sizing lacks fixed-ticket-equivalent margin/tier checks; full liquidation/ADL/book simulation absent | Dedicated preflight/reconciliation and simulation tasks; preserve current defaults here |
| Security / P1 before network exposure | Local Flask mutation routes have no observed auth boundary; credential store is plaintext | Threat model and local container/auth/secret design before NAS exposure |
| Reliability / P2 | Paper account adapter restarts cash/positions while state ledgers persist | Agree account-restart policy and recovery tests before implementation |
| Architecture / P2 | Mixed embedded UI and legacy types; unversioned native context | Extract only when needed; proposed adapters require QR review |
| Validation / P2 | Rolling/expanding argument does not select distinct behavior; no model refit in fixed-parameter folds | QR specifies protocol; QD changes the runner in a separate claim |
| Production / P2 | No tracked container, health/readiness checks, lockfile or CI | Isolated deployment artifacts after lifecycle/recovery foundations; NAS actions separately authorized |
| Optional | Microservices, async rewrite, C++ | Defer until profiling shows a material bottleneck |

## Performance optimization plan

1. Establish a versioned synthetic/immutable workload and record input size,
   Python/package versions, wall time, CPU time, peak memory and numerical output
   hashes. Measure multiple repeats; distinguish cold and warm caches.
2. Profile repeated per-tick feature preparation and inference, CSV parse/sort and
   whole-history SQLite hydration. Inspect scaling over bars/assets, not just one
   timing. Existing prepared covariance series already avoids naive repeated work.
3. Prioritize algorithmic changes: incremental/reused closed-bar computations,
   bounded history queries and batched writes where measurements justify them.
   Test causality, alignment, deterministic ordering and accounting before speed.
4. Compare single-job and two-job workloads before adding concurrency. Cache and
   admission correctness must precede further workers. Consider vectorization or
   serialization tuning next; C++ only for a measured persistent CPU hotspot.

This milestone fixes synchronization/lifecycle correctness, not a throughput
optimization. It adds no worker capacity and makes no speedup claim; a performance
benchmark is therefore not a release criterion for this patch.

## Test coverage assessment

Existing tests cover causal features/ML windows, gap repair, fixed/dynamic parity,
position sizing, ownership, accounting, reporting and web behavior. The 153-test
baseline lacks deterministic controller admission/termination regression tests.
New tests use real controlled threads, events/barriers, fake credentials and
temporary directories. No engine trading loop, exchange connection or account
data is used. Remaining gaps include durable uncertain-order recovery, cache
multi-process races, paper restart, exporter holdout parity and liquidation.

## Proposed QR integration boundary

Preserve native feature version 1/result schema 3 and existing method signatures.
Use the current INTERFACES proposal as review input, not automatic runtime
migration. QR should deliver immutable JSON model bytes plus feature order/version,
instrument/timeframe scope, training-label cutoff, validity/embargo, data/code/
dependency hashes and label/cost semantics. QD validates shape, actual artifact
hash, availability/expiry, inference resources and risk compatibility against a
frozen fixture before paper integration. Missing/expired predictions block fresh
entries while exits remain independent. Model rollback and promotion require
explicit recorded version/review; no model is activated by this milestone.

The lifecycle patch preserves public signatures and existing payload shapes;
timeout/active-deletion booleans become truthful. A request for any new shared
fields or mathematical behavior goes to the designated owner before coding.

## Implementation and verification

Completed:

- Engine stop returns failure with an explicit timeout message while the worker
  is still alive. Its existing registration prevents a second start. Normal
  completion still returns success after termination.
- Engine thread allocation/start failures return an error and retain the prior
  successful-start timestamp rather than leaving a false running/start record.
- Backtest capacity check and pending-job insertion share one critical section.
  Thread allocation/start failure removes the reservation.
- Pending/fetching/running tasks cannot be deleted (deletion is not cancellation).
  Terminal deletion and final persistence are serialized; the worker checks
  registration before writing so a deleted result cannot reappear.
- Changed files are exactly the four paths in the claim above. Public method
  signatures and JSON shapes are unchanged. No shared envelope was adopted.

Regression evidence: the original source accepted **8 of 8** synchronized
requests despite a limit of 2. The original 8-test suite produced 7 failing
assertions (including subcases) and 1 error: timeout false success, start failure,
reservation leak, active deletion and resurrection. The two normal-operation
tests passed. After repair, all regressions pass; a ninth test also checks thread
constructor failure and retained start time.

Commands from this worktree (the existing interpreter is reused read-only):

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p 'test_qd_lifecycle.py' -v
node tests/web_regressions.cjs
git diff --check
git diff --cached --check
```

The final full suite was run with connections explicitly blocked:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
from unittest.mock import patch
with patch.object(socket.socket, 'connect', side_effect=AssertionError('offline test: network blocked')):
    result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover('tests'))
    raise SystemExit(not result.wasSuccessful())
PY
```

Result: **162 Python tests passed** (153 baseline + 9 new tests), **8 frontend
regression groups passed**. Expected failure-fixture logging is not a test
failure. No runtime dependency changes, actual exchange calls, model training,
engine trading loop, credentials reads, live orders or NAS actions occurred.

Preservation check: primary HEAD and staged-content hash match the captured
baseline. All captured primary source/test files are unchanged; the concurrent
QR task updated INTERFACES.md, PROGRESS.md and REPOSITORY_AUDIT.md after capture.
Those files were not overwritten or recopied into this worktree.

## Local decisions, limits and handoff

- Keep the existing 15-second stop timeout; report truthfully rather than kill a
  Python thread. This does not cancel an in-flight network request/order or claim
  an emergency cancellation guarantee. Durable uncertain-order reconciliation
  remains a separate high-priority task.
- Retain active tasks until their actual worker reaches terminal state. No new
  cancellation API or persistent queue is introduced. Admission protection is
  within one controller/process, not a distributed worker quota.
- Hold the controller lock during terminal persistence/deletion to establish a
  clear ordering. Large JSON writes can briefly delay list/admission operations;
  a measured per-job locking redesign is a follow-up, not a claimed speedup here.
- Existing paper-restart semantics and CSV cache races remain open. This closes
  the lifecycle subset of QD-002 and admission subset of QD-001, not either entire
  backlog item. Shared journals remain with the paused integration work.
- This local fix changes no shared quantitative schema. QR dependency:
  review the interface proposal separately; no mathematical/label/default/model
  change is included. User/integrator review is required before integration.

Review only the QD delta against snapshot `475aaeaa5b9365b360563294e183d912c382b570`:

```sh
git diff 475aaeaa5b9365b360563294e183d912c382b570..codex/qd-lifecycle-safety --stat
git log --oneline 475aaeaa5b9365b360563294e183d912c382b570..codex/qd-lifecycle-safety
```

The preceding snapshot commit includes earlier user work and is not an approved
merge into main. Integrate the focused fix only onto a reviewed baseline that
contains the existing implementation; reconcile later shared-document updates
with their owner. Recommended next milestone: cache atomicity/concurrency, then
synthetic uncertain-order reconciliation and paper restart policy.
