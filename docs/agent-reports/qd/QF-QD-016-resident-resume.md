# QF-QD-016 — resident quota adjustment and exact-account continuation

2026-10-29 Australia/Melbourne. Implementation and targeted check complete;
actual continuation pending at this implementation commit. No training.

User authorization requests releasing the resident-index quota and continuing
the original complete BTC/ETH P0account; direct current-chat confirmation:
“继续吧”. Original outer cumulative wall4h/CPU3h/RSS1GiB/output12GiB,
ledger10GiB and all financial/integrity/causality/decoder limits remain.

Existing QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`,
branch `codex/qd-cache-safety`, parent
`d6c7d5ab66a9f97a7f2a2270bf1a3c3820c76b64`. Tracked tree/index were clean;
prior runtime evidence remains. New files only: `research/qd016/{resident,entry}.py`,
`manifest.json`, `tests/test_qd016_resident_resume.py`, this report. No original
financial/module code, QR file, shared journal, main, old report/evidence or source
is edited. The original45code pins still match, including the ledger. A new
operational subclass is separately pinned; it does not pretend to be old code.

The operational index inherits original hash/tree/arithmetic/persistence methods.
Two copies of the original working-node allocation/update methods replace only
the hard `/resident_index` rejection with the process budget check. Deep-copy,
charge/finalizer bookkeeping, tree mutations/order and cache eviction remain.
The SQL/LRUcache sizes stay unchanged. GENESIS/old8MiBconfiguration are preserved
as historical identity; the authorized live working policy is explicit in a new
durable continuation record, not silently rewritten into an old experiment.

The exact old resource stop is resolved only if bound HEAD/CONTROL/guard hashes
match, its disposition is `stop_resource` at `/resident_index`, the next journal/
manifest and committed request are absent, and the actual committed payload's
roots/economic hash match the loaded state. This proves the failed request was
not committed without rerunning321accepted financial ticks. The original control
protocol appends a `not_committed` resolution; an exclusive hash-bound operational
record supersedes this one old resource-stop status. New resource/integrity stops
are not waived. No ambiguous-commit handling, guard or integrity check is removed.

The original account/store, full declared calendar, source spools and completed
input cache are reused. No new account or raw history-reader path exists in the
continuation entry. Attempt count increments; SPENT/write quota history remains
monotonic. Outer remaining time/CPU subtract the original failure's observed
1033.799001416wall/1002.052071CPU s; input totals carry forward unchanged. New
invocation and cumulative observations are recorded separately. Idle time between
user turns is not charged as execution time. Process RSS stays1GiB.

## Directly necessary check

Only one new named synthetic case was run. It reproduces a small resident-index
stop, checks wrong request binding cannot activate, preserves the committed head
and original failure, appends known-not-committed resolution, continues, closes/
reopens, and reaches the already accepted exact financial hash
`cdc0fefc3582f3e3381c1781017dac965155a5cdd9933c081489e1de0fd0d301`.
It proves a subsequent different resource stop stays stopped and OFF reads no
files. No old suite/research/benchmark was rerun; the existing64projection
synthetic fixture is reused instead of recomputing features.

Initial run found a second resident guard on in-place node value updates; that
specific remaining quota check was adjusted and only the same case reran.
Both logs/evidence are retained under `research/.data/qd016/`:

- `targeted-one-1.log`: failed,1.63wall/1.09CPU s,131563520Bpeak RSS;
- `targeted-one-2.log`: PASS,4.61wall/4.27CPU s,139657216Bpeak RSS.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd016_resident_resume -v
```

## Exact actual continuation binding

Manifest SHA256
`890552ba31a21029b73c19342d8243509b89f87e1a2207ae1a0bbee1525803bb`,47code pins.
Same cache key
`eac8926c3a4a568335c229836295bbd6d5bf0d56a4d56543c99ca65b28e7065d`,
content digest
`499fc9cdabbed68cbbaf2c3cc57e5c99f06e0e416404d05a8d5582d13ac0b966`.
Same store `research/.data/qd015/full-p0-actual-1/P0-ALLOW_ALL/store`.
Start at committed321,2024-01-11T16:00Z, resolve/retry only the explicitly known
uncommitted2024-01-11T17:00Zrequest. Original calendar remains2024-01-01→exclusive
2026-10-01+2h,2023warmup retained. No capital reset or forced exit.

New invocation evidence: `research/.data/qd015/full-p0-resume-1/`; original
`full-p0-actual-1/{launch,failure,readonly-summary,financial-summary,artifact-inventory}.json`
and immutable journals/control/audit records remain. HEAD/CONTROL/SPENT are
necessarily advanced in place only after preserving their baseline in the new
launch/operational records. No old failure file is overwritten.

Authorized next command, one new continuation, not a new initial replay:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd016.entry --continue-approved --human-authorization-ref QF-APPROVAL-QD016-RESUME-1 --manifest-sha256 890552ba31a21029b73c19342d8243509b89f87e1a2207ae1a0bbee1525803bb
```

New error or exhausted outer budget stops without automatic retry. No claim of
full completion, training readiness, profit, or hard OS memory enforcement yet.
Actual invocation result will be appended after execution, not inferred from this
targeted check. No model/scaler/Ridge/calibration fitting, policy/12feature/label/
public export change, new agent/chat/timer, main integration/push, engine, NAS or
Windows change is authorized or performed.
