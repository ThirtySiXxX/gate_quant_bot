# QF-QR-004 BTC/ETH data readiness

Date: 2026-10-28. Role: QR. State: **READY_FOR_QD specification; DATA PENDING**.
Training: **NOT AUTHORIZED; fresh human confirmation required before fitting**.
Branch: `codex/qr-validation-baseline`.
Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
Base: `9a598866b642fd121c3d09196bc2befd367b4a4a`.
Dispatch: QF-DISPATCH-20261028-QR004-DATA-SPEC-1.

## Completed changes

Published research-local BTC/ETH history calendar, source/units/availability rules,
immutable provenance manifest, duplicate/conflict/quarantine policy, bounded
acquisition budget, full native warmup checks and training-readiness gates.
The calendar is independent of returns. QR explicitly accepts QD sole collector
ownership as listed in `research/qr004/data-protocol.md`; no shared/runtime schema
change. The protocol ranks additional data without authorizing its acquisition.

## Files modified

Specification checkpoint `b573d5278b2bf74770b996bc03ba11fe2cb19a08`:
`research/qr004/data-protocol.md`, `research/qr004/data-acceptance.json`, and this
report. Validator checkpoint additionally changes `research/qr004/validate_history.py`
and `tests/qr_research/test_qr004_history.py`. `research/qr004/results/` is reserved
for independent acceptance evidence. Shared progress/decisions remain under
their integration editor; this report is the handoff evidence.

## Tests and results

Spec JSON parse and date/budget checks pass; `git diff --check` passes.
**22 focused offline tests pass**, with socket connections blocked: valid fixture
cannot grant training permission; raw hash/normalization tampering; advanced
availability; deleted/duplicate bars; conflicting raw overlap; mark/trade confusion;
unit/row lineage drift; traversal/symlink escape; cross-interval discrepancy;
invalid OHLCV/grid/NaN; funding offsets/interval ambiguity; truncated gzip;
206 completeness; manifest universe/spec drift. The native warmup fixture exercises
the original long-window EMA/scaler/FDM/Carry functions and causal feature code:
a year passes full windows; changing future funding leaves the result unchanged;
500 past Carry observations produce a finite native signal but correctly fail the
full 1000-observation requirement. This is a synthetic test, not actual data acceptance.

Coordinator review identified that row-to-raw equality alone did not detect an
omitted raw funding record. The validator now checks raw-to-normalized coverage
as well. Added negative fixtures for omitted funding, incomplete duplicate lineage,
mislabelled quarantine exclusions and metadata backdating. Duplicate destination,
every retained reference, conflict variants and boundary exclusions are compared
to independent raw parsing, not accepted based on file hashes alone. Non-boundary
exclusions remain blocked for separate reason review. Historical funding schedule
is still not inferred from inter-event durations.
The final transport fixture also rejects a valid-looking JSON body marked
incomplete/failed and independently checks saved bytes against HTTP Content-Length.

Command: load `tests.qr_research.test_qr004_history` through `unittest`, using
`PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python`
and patched `socket.create_connection`, `socket.socket.connect`, `connect_ex`
raising on use. Independent validator never downloads, repairs, fits or reads
operational config. No actual downloaded dataset is accepted yet; QD intake and
semantic evidence are pending. No model has been fitted.

## Known limitations

Gate documents appropriate archives; this is not proof each monthly file is
available or complete. QD is probing official sources. Phase A previously had
63 natural baseline labels, overlapping asset/time dependence and incomplete
funding warmup. Expanded data may still fail source coverage, schedule semantics
or useful event-count/precision checks. Current metadata is not historical truth.
No period already inspected will be described as an untouched test set.

## Dependencies and next steps

QD: acquire only the approved universe/calendar within the total-attempt budget;
retain payloads/failures, supply manifest and source/schedule evidence. QR: build
offline independent validation and inspect that exact handoff. Only if data gates
pass, generate at most two unchanged baseline trajectories to assess labels.
Then report READY_FOR_USER_TRAINING_CONFIRMATION or concrete NOT_READY blockers.
At the future training decision, the human must confirm the holdout and economic
precision goal as well as permission to fit. No automatic merge or integration.

Early QD adapter `research/qd004/results/intake-contract.json` reviewed and accepted:
hybrid_native_v1 uses monthly 1h/settled funding plus native REST 4h/daily and
October tail, with declared overlap checks. Exact JSON conventions agree; funding
`interval_seconds: null` records that schedule is not assumed. Identical duplicate
lineage in the quarantine partition is provenance, not automatically invalid data.
No downloaded dataset or final collector candidate is accepted by this early review.

## Collector checkpoint review

QR independently reviewed QD commit `5209a13847615214f5c8ca86cdbcc38bed627c1e`
(parent `e68813c273c66e29eb9950b6d52d144b1e89ab2d`) and the committed
`research/qd004/results/lineage-examples.json`. Examples match the QR adapter.
Collector SHA256 `2adfed92c3204244a9ed5e66732d8ce2cee89af624eb1b18feb57bdf7ee0299a`;
test SHA256 `d1931696ad7fc199767ef2cd7967b260816c5d8ad1f95c2e62d2fce80c5e280e`.
Both local files matched the exact committed bytes before execution.

**17 QD focused tests independently rerun and passed**, with sockets blocked:
fixed scope/spec/routes, total attempt and byte limits, retry/resume accounting,
access restrictions, incomplete transport, gzip integrity, original column units,
duplicates/conflicts/exclusions and dropped funding, funding-second preservation,
immutable paths, interrupted reservations, authentic extremes, exclusive collector
lease and current-only metadata. Tests used only temporary synthetic fixtures.
QD reported 214 broader Python tests and 8 frontend groups; QR did not rerun
those broad suites because this review does not change runtime or frontend code.

This technical review supports bounded intake and preserves all unresolved
semantic gates. Actual collection was still running without a final immutable
manifest at this checkpoint. No actual dataset acceptance, baseline replay,
training-readiness approval, merge or runtime integration is implied. QR validator
code checkpoint is `56e80c975cac260a8ffc8a0af793999e0109bf98`; specification hash
remains `6e3d4fb99c62d0658fcb3bb779a35b072d65b29df399e9b287fa315943687862`.
