# QR017: QD015 producer binding and next actual-input handoff

2026-10-29 Australia/Melbourne. User instruction: QD has completed its work;
continue the next step. QR's isolated worktree started clean on
`codex/qr-validation-baseline`, exact parent
`f0d79c28be703d591a655db757e2d7761c2bdd94`. Only the QR-owned consumer pin,
its README, one new QR test and this role report are changed. Shared journals,
QD files and the source checkout remain outside this change.

## Completed

Read QD015's exact committed manifest/report at
`577aeed903b9eefdb2c176dac7e3e67f999731ea`. Its engineering conclusions are
adopted; no old research/test or QD algorithm review was repeated. The report
explicitly says actual full P0 remains OFF: the completed work is journal
storage implementation/verification, not delivery of a full historical dataset.

Updated `research/qr015/dataset.py` and its README to the exact producer commit
above and manifest SHA-256
`a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2`.
The three direct public exporter/market/inputs code hashes are unchanged in the
new manifest, so they were not changed. The public QD013 episode/cache versions,
four accepted source metadata hashes, QR014 hash/features/target and all selection
rules remain their approved versions. The new complete market-producer identity
must arrive in a reviewed actual handoff; an old key is never silently relabeled.

## Focused verification

Added `tests/qr_research/test_qr017_producer_binding.py`, containing one named
metadata-only case. It accepts the literal QD015 commit/manifest/direct-code
identity and rejects the old pair, mixed pairs, and a changed direct-code hash.
It does not read a dataset or invoke assembly/replay. The case passed once with
zero failures/errors; old QR015 six and QR014 seventeen tests were not rerun.

Existing interpreter, bytecode disabled, connection guards and imports of
numpy/pandas/sklearn/torch/tensorflow/src blocked. Observed wall 0.015361 seconds,
CPU 0.011808 seconds, peak RSS 28,131,328 bytes; log 283 bytes. These are measured
process observations, not hard OS limits. Evidence is retained in ignored
`research/.data/qr017/identity-check-1.{json,log}` with exact new code/test hashes.
No dependency install, market payload read, actual sample assembly or fit occurred.

## Concrete next run requiring allocation

QD015 supplies a default-OFF callable and a complete resource proposal, not an
actual completed label artifact. The next data-producing step is **one** continuous
BTC/ETH P0/ALLOW_ALL baseline: complete 2023 warmup; economic decisions from
2024-01-01 through exclusive 2026-10-01 UTC; settlement-only two-hour tail; one
shared 10,000 USDT research account, no annual reset or forced close.

The QD report proposes observed stopping ceilings: wall 4h, CPU 3h, RSS 1 GiB,
total output 12 GiB including a 10 GiB ledger. These are not measured full-run
requirements, a completion forecast, or already-approved resource use. First
failure/cap stops, evidence remains, and no automatic retry/resume is allowed.
The fresh destination is QD's `research/.data/qd015/full-p0-actual-1/`.

After explicit allocation to QD, the exact already-prepared invocation is:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd015.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD015-FULL-P0-1 --manifest-sha256 a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2 --scope full_p0
```

Working directory: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
This report does not execute that command or create its approval receipt.
The allocation also needs explicit authority to instruct QD; this chat has sent
no task messages. Model/mean/scaler/calibration fitting remains unapproved.

## Dependencies and next consumer step

After a successful complete run, QD/coordinator supplies exact episode manifest,
JSONL paths/hashes/counts, immutable cache identity/key, account/trajectory/scope,
as-known/source binding and heldout-completeness evidence. QR can then assemble
the pinned real dataset under its separately specified resource scope and report
actual counts/exclusions/readiness. No counts or completion are inferred here.
The missing never-filled/rejected proposal inventory remains a selection/strategy
evaluation gap per QR016, not a new independent blocker for the approved
conditional regression. Training still requires a ready report and fresh user
confirmation. No integration, push, app/engine or service action is performed.
