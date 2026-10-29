# QF-QR-005 BTC/ETH canonical-data reacceptance

## Final independent acceptance — phase complete

2026-10-28. **DATA: PASS_WITH_LIMITATIONS. TRAINING: NOT_READY.**
Zero new baseline replays, position labels, model/scaler fits, network attempts,
additional coins, runtime changes or main integration. This bounded phase is
complete; no automatic next task. Fresh human confirmation is required before
training. Earlier milestone descriptions below are preserved as historical notes.

### Rules and result

V2 deliberately uses one frozen Gate hourly trade-price stream to derive UTC
4h/day bars. This gives internally consistent inputs, not proof that hourly data
is historical truth. V1's failed native-stream equality result is not overturned:
all 2,068 original discrepancies remain unchanged and diagnostic only.

Only BTC_USDT / ETH_USDT USDT linear perpetuals. Prices are USDT/base; volume is
integer contracts, not quote/base volume. Fixed UTC range is [2023-01-01 00:00,
2026-10-27 09:00); 2023 is warmup. Derived OHLCV uses first/max/min/last/sum over
4/24 complete hourly children. Availability is bucket end, an idealized proxy.
Hourly and settled-funding bytes/source references remain exactly unchanged.
Funding seconds are never rounded, filled, or inferred from an 8h reference.

| Per asset | Records | Independent finding |
| --- | ---: | --- |
| Copied 1h | 33,489 | Exact original bytes and complete valid hourly grid |
| Derived 4h | 8,372 | Exact independent recomputation and every child reference |
| Derived 1d | 1,395 | Exact direct hourly and six-four-hour recomputation |
| Settled funding | 4,187 | Exact original timestamp/rate/availability/provenance |

Both coins total **94,886 data rows**, **19,534 derived-lineage rows**, and zero
validation issues. Each coin explicitly withholds the final unclosed 4h (1/4
children present) and daily (9/24 present) buckets without dropping any hourly
rows or shortening the cutoff. Native disagreements remain BTC 4h 188, BTC daily
148, ETH 4h 1,393, ETH daily 339: total 2,068.

### Exact candidate and review identities

Frozen rules: `e1b459434e32e585e8a57d46b4bfedb0e79d7f67`, specification SHA256
`a516075cd2baced65dd659b520c6495d2cdf9d539ff8a1bfa2570c93ccfb63a4`.
QD reviewed draft `b545c8a9609c53c6ed3bb0735253a43a600eee05` in
`a7cdd17d748e9d576ef335c587a90ed3ab5f5c17`; the freeze changed status/review
metadata and narrowed the phase replay budget to zero, not data semantics.
Actual candidate dispatch: QF-DISPATCH-20261028-QR005-CANDIDATE-REVIEW-1.

QD builder commit `710fbca77f677cfcdcd4fbe10d319f63483f48b9`, source SHA256
`7f2e0a11b96c97d833437b2c4dcdf20337a56e2199b05f4e153ac5ec92263de5`;
sealed handoff `ba1a507d8b265f29f355a015d5f189178361e611`.
QR compared exact committed source bytes, inspected the producer separately and
reran its tests. The acceptance oracle is QR's own parser/recomputation, which
does not import QD's aggregation implementation.

Candidate root:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd005/canonical-hourly-v2`.
Manifest SHA256:
`cbe95174e6eca704353a06f89e68294ec58a81cc6a59f370bb424c51d1177808`.
Reproduction sibling `reproducibility-v2`, manifest SHA256:
`7a415b384cbfb3ea865ff189c4e735cfb4bdea417ed4ad79f5eaf5a6abb58772`.
All **12 normalized/lineage files** match byte for byte; only created_at differs
between manifests. The sealed manifest's pending-review note is its creation-time
state; this report records acceptance without rewriting immutable evidence.

### Verification and conditional diagnostics

- Reverified original 210 raw files, 94,886 unique normalized market origins,
  28 duplicate groups and zero omitted origins. Original four v1 cross-stream
  failure messages remain, with no new integrity issue.
- QR's entire pre-build fingerprint of **234 v1 files** remains identical. This
  includes local evidence beyond QD's 229 selected preservation files.
- V1 null funding interval explicitly maps to v2's event marker 0 only in the
  validator; neither is supplied as native cost/annualization configuration.
- At hypothetical first decision 2024-01-01, both coins have 8,760 hourly,
  2,190 four-hour and 365 daily closed warmup observations. Four trend scale
  windows (1,500), FDM (500), Carry (1,000) and daily regime requirements pass.
  Carry computation conditionally assumes 28,800s; no historical schedule proven.
- Each coin has **24,729** eligible closed-hour decision points with all **21**
  existing causal features finite and nonconstant. These are feature rows,
  not independent labels or evidence of prediction skill. No fitting occurred.

**Tests:** QR independently executed 40 QR focused tests (23 QR004 + 17 QR005)
and 15 QD focused producer tests: **55 passed**, with Python socket connections
blocked. Adversarial cases include rehashed corruption, wrong units/universe,
missing/partial rows, premature availability, future perturbation, lineage reorder,
Decimal precision, funding seconds, legacy null mapping and path escapes.
QD reports **230 full Python tests passed**, via its guarded file runner; QR did
not repeat that broad suite. The initial stdin full-suite invocation failed four
macOS spawn tests; the proper file entry resolved them without runtime changes.
No frontend changes; no new JS test run. `git diff --check` passed.

Exact executed test scopes, interpreter, hashes and results are in
`research/qr005/results/verification-runs.json`. Independent acceptance and native
diagnostics are in `candidate-independent-validation.json` and
`candidate-native-diagnostics.json`; byte preservation/reproduction is in
`reproducibility-and-preservation.json`. Evidence index binds reports/code/tests.
To reproduce acceptance from this QR worktree, use a new output path:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python \
  -m research.qr005.validate_history \
  --root /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd005/canonical-hourly-v2 \
  --base-root /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/history-v1 \
  --output /tmp/qr005-independent-new.json
```

Actual runs also patched Python socket connections to fail. The checker is read
only except for its fresh report output and has no download/model-fitting path.
`research.qr005.assess_inputs` uses the same roots plus the frozen public QR003
fixture for conditional warmup/feature diagnostics; no real configuration is read.

### Remaining gates and next decision

| Gate | Final state |
| --- | --- |
| G1 source provenance | PASS |
| G2 canonical internal consistency | PASS_WITH_LIMITATIONS |
| G3 economic labels | BLOCKED: funding/cost and historical metadata assumptions need a separate policy decision or reviewed adapter; zero new replay/labels |
| G4 experimental protocol | NOT_FINAL: mature labels/dependence, untouched prospective holdout, useful economic effect and precision decisions pending |
| G5 training | NOT_AUTHORIZED: fresh direct human confirmation required |

Native funding as-of preserves exact seconds causally, but cost accounting uses
`elapsed / interval * endpoint notional * latest known rate`, not an event ledger.
For a hypothetical 1,000 USDT long at rate 0.0001, one hour can accrue 0.0125 USDT
despite no event in that holding window. This is an existing simulation assumption,
not evidence of corrupted funding data. Normalization cannot make it exact.
`research/qr005/replay-compatibility.md` documents the next bounded decision and
adapter acceptance criteria; no adapter or new runtime task is implemented here.

Remaining limitations: frozen official values may include revisions; availability
is idealized; historical funding schedules, settlement mark/notional, multipliers
and tiers are unproven by current snapshots. All expanded history is development/
retrospective. No untouched test, forecast edge, future profit, liquidation
survival or live-fill equivalence is established.

Next: review the funding/label policy, then assess baseline labels/maturity and
freeze the evaluation plan. Only when prerequisites are satisfied should the
exact bounded training plan be submitted to the human for confirmation. Do not
start fitting or acquire other coins automatically.

### Changed files, preservation and integration

QR only changed `research/qr005/`, `tests/qr_research/test_qr005_history.py` and
this report in its assigned worktree/branch. Old QR004/QD004 evidence is unchanged.
Main HEAD remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; staged binary diff
SHA256 remains `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`.
No reset/stash/cleanup, shared-contract migration, merge, push, service/engine
start, credentials, NAS/Windows change or automation. QD remains sole integration
editor of shared PROGRESS/DECISIONS; this role report records current decisions
and progress pending explicitly reviewed integration.

## Historical draft and freeze milestones (superseded status)

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
