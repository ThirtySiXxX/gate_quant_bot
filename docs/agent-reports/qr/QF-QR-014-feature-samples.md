# QF-QR-014: research-local hourly features and episode samples

Status: IMPLEMENTATION_WITH_SYNTHETIC_TESTS_COMPLETE; REAL_INPUT_NOT_CONNECTED;
TRAINING_NOT_AUTHORIZED. Date: 2026-10-28 UTC. Owner/editor: QR; integration and
producer compatibility require QD review and explicit integration approval.

## Allocation and approval

- Task: `QF-QR-014-FEATURE-SAMPLE-ADAPTER`.
- Dispatch: `QF-DISPATCH-20261028-QR014-FEATURE-SAMPLES-1`.
- Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
- Branch: `codex/qr-validation-baseline`.
- Base: `8da56ce57f6100391379a053d55418ab02f2072c` (QR013 proposal).
- Exact four-file change scope: this report,
  `research/qr014/approved-training-plan.json`,
  `research/qr014/feature_samples.py`, and
  `tests/qr_research/test_qr014_feature_samples.py`.

The approved plan is a separate copy, preserving QR013. It binds the three
approved choices: continuous episode net-return regression with fixed Ridge,
hourly baseline before microstructure increments, and the approved economic
evaluation criteria. The human decision record is
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qr013-user-modeling-decisions-approved.json`,
SHA-256 `e27e05aa281d1d69508be80f2b6ddb4a908441013936bcb50ce04bef95503b9e`.
Its recorded time is `2026-10-28T12:28:00.781681+00:00`. Design approval does not
authorize estimation, actual replay, historical research revalidation, or
prospective collection. The plan retains `training_authorized=false` and
`research_validation_authorized=false`.

## Completed implementation and local interfaces

The module uses only the Python standard library and in-memory inputs. Its
`qr014.feature-samples.v1` schema is research-local. It does not replace an
INTERFACES contract or the existing native 21-feature/three-class model schema.
The explicit input types are `Candle`, `EntryProposal`, `FeatureRow`, `Episode`,
`InformationInterval`, and `PurgeContext`. No actual QD export compatibility is
asserted: an accepted-export mapping remains necessary.

`features_for_proposal` implements the approved ordered 12 columns: four signed
log returns over 1/4/24/168 hours; sample standard deviations of hourly log returns
over 24/72 hours; log relative contract volume over 24/168 hours; high-low range
divided by close; 24-hour efficiency; proposal direction; and ETH indicator.
Volatility is not annualized; range is a fraction, not percentage points. Volume
uses the approved one-contract offset and retains fractional ETH quantities.
The original literal feature-set identifier ending in `v1-proposed` is preserved
to avoid silently changing its identity when recording approval.

Only `gate:usdt:BTC_USDT` and `gate:usdt:ETH_USDT` hourly flat-entry proposals from
`P0 / ALLOW_ALL / QR010_SHARED_NATIVE_X10` are accepted. All times are UTC integer
microseconds. OHLCV inputs are exact ordinary decimal strings, domain-checked
with Decimal before explicit finite binary64 feature projection. The approved
research availability proxy is bar close; it is not a measured exchange-arrival
timestamp. Features require 169 consecutive valid, available candles ending at
the latest closed hour. Gaps and invalid/unavailable candles reset that window;
there is no imputation or stale-vector fallback. Duplicate or decreasing past
timestamps fail. Future candle values are not inspected; callers must supply an
ordered single-instrument prefix.

`assemble_samples` joins feature records with one accepted as-known episode
revision. Duplicate feature identities, repeated episode identities/revisions,
multiple episodes for one proposal, and conflicting proposal context fail rather
than overwrite. Unfilled proposals remain feature records without realized
labels. Open, immature, censored, and invalid episodes retain states and reasons
and have no model target. Orphan labels retain a missing-feature exclusion.

A valid label requires an actual entry, natural close, settled cash and scoped
completeness attestations, evidence references, and a known-at clock equal to the
maximum of natural close and all required input/posting/assertion availability
times. These are attestations from an accepted upstream checker: references and
booleans cannot prove ledger finality here. The adapter does not reconstruct
funding, fees, fills, revisions, cashflows or completeness.

The target is exact net cash divided by gross increasing-entry notional, using
rational division and 12-decimal HALF_EVEN rounding. It is not margin ROE. Fees
and slippage are not deducted again. Exact supplied totals and source references
remain in the output for audit. Excluded valid labels can retain a raw target;
their model-target field is null. Outputs contain proposal/episode identities,
revision, feature and label clocks, lineage, accepted-export/as-known/scoped
references, actual receipt/assembly times and `training_authorized=false`.

## Chronological selection

- Decision origins: 2024 train, 2025 validation, and January–September 2026
  exposed audit. Other origins are excluded; warmup does not become samples.
- Train requires both `label_end + 24h < 2025-01-01 UTC` and
  `label_known_at + 24h < 2025-01-01 UTC`, strictly. Equality fails.
- Train also requires an externally complete heldout information-interval
  inventory for both coins. Any overlap across either coin is purged; touching
  endpoints count as overlap and an unknown interval end is open-ended.
- Validation labels must close before and be known by 2026-01-01 UTC. Audit
  economic exits must precede 2026-10-01 UTC and be known before the end of the
  approved two-hour evidence tail. The tail cannot admit October economic exits.
- Actual research input receipt must precede assembly. This is separate from
  historical simulated eligibility; a future runner must also check receipt
  against actual fit time. Validation/audit records are never training rows.

## Tests and measured resources

Exactly one group of the 17 new QR014 synthetic tests ran; all 17 passed, with
zero failures/errors and no retry. Largest individual candle fixture: 340 rows.
Test execution plus module loading took 0.052803 seconds wall and 0.049709 seconds
CPU. Observed process peak RSS was 28,459,008 bytes (about 27.14 MiB), below the
256 MiB observed budget. RSS was measured, not hard-enforced on macOS. The
60-second wall alarm did not fire. Captured test output was 2,903 bytes, below
the 8 MiB total output budget.

Execution used the existing
`/Users/lzh/Development/Project/gate_quant_bot/venv/bin/python` with
`PYTHONDONTWRITEBYTECODE=1`. Socket connection methods and imports of sklearn,
numpy, pandas, torch, tensorflow and src were blocked in the test process. The
suite loaded only the new test file, new module, new plan, and synthetic inputs.
No fitting occurred; no market/MARK/trade archive was opened or feature matrix
generated. No existing research conclusion, ledger test suite, or QD candidate
was rerun or reviewed.

Coverage includes literal feature formulas/order/units; fractional quantities;
future-value perturbation; unavailable latest candles; gap/invalid-row recovery;
nonfinite and domain rejection; exact label rounding; nonvalid states; finality
clock consistency; duplicate identity rejection; strict embargo equality;
cross-asset overlap; split/receipt clocks; and absence of model/network/file-I/O
entrypoints in the module.

Ignored evidence is retained at `research/.data/qr014/tmp/new-tests-attempt-1.json`
and `research/.data/qr014/tmp/new-tests-attempt-1.log`. The JSON pins hashes of
the three implemented/tested files and actual resource measurements. These
synthetic evidence files are not part of the commit. No dependencies changed.

## Remaining conditions before training

1. QD supplies an accepted scoped episode export from the required shared-account
   label-producing path, with mature labels, exclusions, finality and revision
   evidence. Relevant path correctness is necessary; unrelated production or
   benchmark suites are not blanket first-fit requirements.
2. An explicitly allocated follow-up maps that export to this local interface
   and implements the bounded real-input preparation/training runner. This task
   supplies no data loader, full-matrix driver or automatic fit entrypoint.
3. With the purpose and resource cost approved, generate the actual training-only
   sample/dependence/precision summary and pinned artifacts. Establish both-asset
   support, nonzero target variance and sufficient independent information for
   the approved precision question. Hourly rows or raw trade counts alone are
   not independent episode counts. Actual artifact paths/sample counts remain
   null; no adequacy or profitability result is claimed.
4. Report those results and obtain fresh explicit human confirmation before
   mean/scaler/model estimation. The future budget remains at most three counted
   estimation calls and one fixed Ridge candidate, without automatic retries.

The deferred microstructure increment is not a first hourly-fit gate. The
approved prospective evaluation window and performance criteria are research
design commitments, not completed results and not permission to collect data.
No wall-time estimate for readiness is supported until actual labels and sample
counts are available. The adapter is a reference in-memory implementation;
full-history throughput and resource use have not been measured.

QD should integrate relevant progress/decision entries only after review. QR
did not modify shared journals, source checkout, runtime interfaces, deployment,
risk settings or other agents' files. This change is an independent local commit;
there is no automatic merge, push or training permission.
