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
**16 focused offline tests pass**, with socket connections blocked: valid fixture
cannot grant training permission; raw hash/normalization tampering; advanced
availability; deleted/duplicate bars; conflicting raw overlap; mark/trade confusion;
unit/row lineage drift; traversal/symlink escape; cross-interval discrepancy;
invalid OHLCV/grid/NaN; funding offsets/interval ambiguity; truncated gzip;
206 completeness; manifest universe/spec drift.

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
