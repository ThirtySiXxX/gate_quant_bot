# QF-QR-005 BTC/ETH canonical-data reacceptance

Date: 2026-10-28. Role QR. Status: RULES_FROZEN_FOR_DATA_ONLY_BUILD; G3 BLOCKED; no training.
Worktree / branch: /Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot,
codex/qr-validation-baseline. Base: 78d90df97c11880246e8f7323e216c24b6eeae87.
Dispatch: QF-DISPATCH-20261028-QR005-SPEC-1. User asked to resolve BTC/ETH data
definitions and timeframe differences, reaccept, add no coins, and obtain a new
confirmation before training.

## Claim and current changes

Exclusive QR: research/qr005/, tests/qr_research/test_qr005_history.py,
this report. QD exclusively builds data in its independent worktree. Shared
journals/runtime/source checkout and all v1 evidence are read-only.

Draft canonical_hourly_v2-r1 defines a fixed hourly stream, exact Decimal derived
4h/1d, closed-time availability, complete child lineage, immutable old evidence
and exact funding preservation. It explicitly changes the failed native-v1
multi-stream rule rather than describing discrepant values as repaired truth.

## Tests / evidence

Draft stage: inspected existing native consumers and frozen reports; no new
dataset, baseline, fit or runtime test run yet. Validation code/tests follow
counterpart review of the data contract.

## Limitations / dependency

QD must review the draft, then build only after rule freeze. QR must independently
validate that exact candidate. Current native funding cost accounting prorates
elapsed time rather than charging exact settlement events; this is a separate
economic-label compatibility issue. Historical schedule/metadata and real arrival
remain unproven. G3 cannot be called ready by deriving consistent candles alone.

## Next steps

QD counterpart review -> freeze rules -> QD isolated build/tests -> independent
QR checks and report. No merge or training. Proposed funding-accounting adapter
may be specified for later review; no runtime implementation in this task.

## Reviewed freeze

QD commit a7cdd17d748e9d576ef335c587a90ed3ab5f5c17 accepts data production
and blocks economic-label replay. Spec status/review metadata and the phase budget
were updated accordingly; price/funding/lineage semantics are unchanged. No new
baseline will run. QR independent validator is in development; 15 focused offline
adversarial tests passed with Python socket connections blocked. No raw data or
runtime file was changed. Next dependency is coordinator dispatch of the isolated
QD builder, then its exact manifest and producer tests.
