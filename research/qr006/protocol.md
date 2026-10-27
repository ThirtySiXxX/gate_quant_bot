# QF006 Gate execution, cost and label protocol

Revision qf006-proposal-r1; 2026-10-28 Australia/Melbourne.
State: READY_FOR_QD_REVIEW. Document review only: no implementation, data intake,
replay, label generation, fitting, integration or automatic next stage.
Scope: Gate USDT linear perpetual BTC_USDT and ETH_USDT, existing frozen v2 data
and original strategy/risk configuration. All times below are UTC.

## 1. Estimand and falsifiable question

Recommend **SCENARIO** as the primary future research estimand: performance of a
specified execution/accounting policy on a frozen market path under explicitly
named cost, availability, multiplier and margin assumptions. This can test an
economic hypothesis without pretending to reconstruct a user's private account.
It is not a claim of historical actual fills, fees, spendable margin or liquidation
survival. **HISTORICAL_EXACT** is a separate reconstruction mode requiring complete
effective historical rules, snapshots, mark valuations, fill roles and bookings;
missing critical evidence rejects that mode, not silently downgrades it.

The proposed primary fee scenario is the publicly documented VIP0 taker fraction
0.0005 in S03, no discount or referral income. It is a named announcement scenario,
not a verified current personal fee or a 2023 historical fee. All assumed fills
are taker; maker queue advantages/rebates are excluded from the primary scenario.
Historical funding rates may be environmental cash-flow inputs only after an
explicit event/snapshot mapping is established. Today's schedule cannot generate
past missing events. Scenario constants must have an explicit ID and applicability
window; a constant multiplier means synthetic contract sizing throughout that
scenario, never a statement about actual historical contract specifications.

Candidate research question: among flat-state entry proposals of the frozen
original policy, can preregistered past-only features improve prediction of the
natural-exit episode net-return target relative to a training-only constant?
A predictive improvement does not establish the value of skipping a trade.
Economic comparison requires full state replay of the resulting policy against
ML-off, with identical environment, starting capital and declared constraints.
Reject/retain-inconclusive when paired uncertainty cannot establish the predefined
useful effect, results depend on unresolved execution assumptions, or eligibility
and coverage differ. Do not search indicators until returns improve.

## 2. Verified facts, vintages and gaps

Exact URLs, page dates, access date, claim scope and missing evidence are in
`evidence.json`; IDs below are stable. Summaries are paraphrases, not page copies.

- **S01** currently describes nominal-hour position snapshots followed by
  asynchronous funding settlement; late booking after close may appear only in
  cash history. USDT funding valuation uses mark, contracts and multiplier, with
  positive rates transferring value from long to short. It does not establish
  matching-engine order at an exactly simultaneous fill. The displayed original
  publication date does not date every later paragraph. [S01](https://www.gate.com/zh/help/futures/futures-logic/27569/funding-rate-and-funding-fee)
- **S02/S04** distinguish execution fees and maker/taker roles. An immediately
  marketable limit can take liquidity. No fill means no execution fee. Tier,
  discounts and settlement asset require separate evidence; no personal fees
  were read. [S02](https://www.gate.com/zh/help/futures/futures_logic/22079?category=futures), [S04](https://www.gate.com/zh/fee)
- **S03** is published 2026-03-25 and states a change date of 2026-04-09. Its VIP0
  taker row is 0.0500%; exact effective intraday time is not specified. It is not
  a universal account fee or evidence for earlier years. [S03](https://www.gate.com/zh/announcements/article/50390)
- **S06** states automatic 1h transitions at limits from 2025-08-29 10:00 UTC;
  its displayed publication is 11:30 UTC. **S07** adds conditional 1h-to-4h
  reversion from 2026-04-13 01:00 UTC. Its March example is not an earlier effective
  date. Neither announcement proves BTC/ETH actually triggered a transition.
  [S06](https://www.gate.com/announcements/article/46849), [S07](https://www.gate.com/announcements/article/50645)
- **S05** exposes historical rate timestamp/rate and separate mark candles;
  it does not identify that timestamp as a position snapshot, cash booking or
  observed delivery time. Private fills/books are separately authenticated and
  were not requested. Endpoint documentation is not a historical coverage proof.
  [S05](https://www.gate.com/docs/developers/apiv4/en/futures/)

Historical applicability: before S06, general mechanism history is incomplete;
between S06/S07 the documented rule generations differ; after S07 market-specific
states, limits and exceptions still need evidence. Current help thresholds and
illustrative multipliers cannot be backdated. A rule with known effective time but
later publication may explain a retrospective ledger, but cannot be assumed known
by an earlier trading decision. Record both clocks and revisions separately.

## 3. Clock, identity and information rules

Proposed standalone payload namespace `qf006`, schema 1; it is unrelated to
native/schema-v1 payloads, feature version 1 and result schema 3. See interface
request for exact mandatory fields. Decimal strings for prices, rates and money;
integer contracts and integer UTC microseconds for new event ordering; an adapter
converts old Unix seconds by exact multiplication, preserving original precision.
Micros do not invent subsecond ordering. Unknown values are null plus reason.
The conversion is `event_us = source_seconds * 1_000_000`; the 24h buffer is
`embargo_us = 86_400 * 1_000_000 = 86_400_000_000`. Compare clocks only after
both event timestamps and durations have been explicitly converted to microseconds.

| Time | Meaning | Must not substitute |
| --- | --- | --- |
| nominal_settlement_at | Scheduled settlement boundary under identified rule/scenario | raw record timestamp |
| snapshot_at + sequence | Position eligibility observation/order | later cash booking |
| source_record_at | Original source t, preserved losslessly | snapshot or first public availability |
| published_at / received_at | Source publication / observed arrival, if evidenced | file retrieval as historical arrival |
| feature_available_at | Proven or explicitly assumed consumer availability | retrospectively known final rate |
| booking_at | Actual cash posting, or explicitly synthetic scenario posting | snapshot time merely to simplify code |
| retrieved_at / revision_seen_at | Research acquisition / discovery of revision | historical knowledge |

Join an event to a snapshot by source event identity or a documented, independently
verified schedule mapping. No `floor(t/28800)` inference from seconds offsets.
Ambiguous mapping is `UNRESOLVED_SNAPSHOT_MAPPING`. Preserve 4,187 raw rows per
coin; their earlier proxy availability remains original data, not new proof.

Keep separate accounting-final-rate and decision-feature views. Final rates may
reconcile obligations retrospectively, but may enter features, sizing or cash
decisions only after feature_available_at. Historical actual arrival is unknown
in v2: HISTORICAL_EXACT features requiring it are unavailable. A prospective
SCENARIO must freeze a delivery assumption before outcomes, for example next
hourly boundary strictly after max(snapshot_at, source_record_at), and compare
one additional hourly delay as a declared stress. That is a simulation assumption,
not evidence of arrival. No delivery-lag selection using returns. The example is
a proposal requiring configuration, not a default silently applied to v2.

## 4. Fills and same-time ordering

Execution fees attach to each actual/synthetic **fill**, not order submission.
Store signed contract change, price, multiplier/rule identity, liquidity role,
decision/order/fill IDs, event sequence and fee currency. Failed/cancelled
unfilled orders have zero fill quantity and no fill fee. A partial fill charges
only its filled quantity; an unfilled remainder stays pending/cancelled explicitly.
Reversals split into a closing leg and a new opposite episode. Split a single
fill fee pro rata by absolute executed base quantity; leg sums equal the original.

HISTORICAL_EXACT orders fills and snapshot by exchange sequence evidence; tied
timestamps with unknown order reject eligibility (`AMBIGUOUS_SNAPSHOT_SEQUENCE`).
SCENARIO proposes snapshot-before-same-time-fills, a transparent tie policy:
an already-held position closed/reduced at S remains eligible at S; an opening
fill at S is not; a reversal charges the old side at S and starts the new side
afterwards. Opposite tie order is a preregistered stress, never chosen for profit.
For a fill before S, include only its filled quantity; a fill after S is excluded.
The partial opening example starts flat: 4 contracts fill before S and 6 at S,
so eligible Q is 4. Conversely, starting long 10 and reducing 4 before S and 6
at S leaves eligible Q of 6. These are independent trajectories, not one order.

At each timestamp: ingest information whose declared availability has arrived;
honor proven event sequences where available; otherwise apply the scenario's
fixed snapshot-before-fills ordering; capture eligibility; process available
bookings; perform deterministic order/fill processing (close before new reversal
leg); record balances and decisions from the permitted information view. Unknown
snapshot order cannot be resolved by filename, stable sorting or later PnL.

Default future execution template is a **declared next-available-open taker
simulation**, not an exact exchange fill. Decision inputs must be closed and
available; orders cannot fill before decision+latency. With hourly bars, latency
beyond a bar-open forces the next observed executable event, not an invented
intrabar quote. No limit-touch fill or intrabar stop sequence is inferred from
OHLC. Price slippage is applied in the adverse direction once in fill price;
do not subtract it again from PnL. Proposed stress suite uses base and doubled
fee/slippage, one extra execution bar, partial/no fills and both boundary orders.
Freeze numeric base slippage, fill capacity, latency and cancellation settings
before any performance comparison; these are unresolved input parameters, not
quiet changes to current sizing/risk defaults.

## 5. Exact accounting definitions

Let fill quantity q be positive contracts, m base units/contract, P fill
USDT/base, r the applicable signed fee fraction (rebate negative). Then
`notional = q*m*P`, `fee_cost = notional*r`, `fee_cash = -fee_cost`.
Leverage does not multiply that notional a second time. Rate applicability is
per fill time, instrument, liquidity role, account tier and effective rule. Unknown
role/tier/discount blocks HISTORICAL_EXACT. SCENARIO uses its named fee rule.
Foreign fee/point assets need an evidenced conversion or separate asset ledger;
do not relabel points as USDT. Referral payouts are external transfers excluded
from alpha labels, not negative execution fees. Round only by a declared venue
rule when known; scenario uses exact decimals and a stated reporting quantum,
not an invented venue rounding precision.

For funding event k, signed eligible contracts Q_k (long positive), effective
multiplier m_k, settlement mark M_k and final rate f_k:
`funding_cash_k = -Q_k*m_k*M_k*f_k` (USDT); expense is its negative.
No event while eligible means exactly zero funding, not elapsed-time proration.
No leverage factor, no multiplication by hours/interval, no charging all positions
present at booking. Funding remains assigned to its snapshot episode/lots even
after close; it must not migrate to a newly opened opposite episode.

Settlement mark evidence is a separate input. Trade close is not exact mark;
hourly mark OHLC is not an exact instantaneous mark either. HISTORICAL_EXACT
rejects missing valuation/time-matched multiplier. SCENARIO may declare a causal
last-available mark proxy, maximum age and sensitivity, but cannot call it exact.
Without any mark series, trade-price substitution is a separately labelled proxy
diagnostic, excluded from the proposed primary mark-based result. Historical
contract conversions must split at a documented conversion rule; unknown changes
block exact mode. A declared constant scenario multiplier must be identified as
counterfactual and may not reinterpret old raw contract-volume units silently.

Use separate signed balances: C = booked USDT cash; A = unbooked receivables
(>=0); L = unbooked liabilities (>=0); U = mark unrealized PnL. Economic equity
`E = C + A - L + U`. At known funding claim creation, add credit to A or debit
to L; do not change C. At booking, move the exact amount between C and A/L,
without changing E absent market movement. Realized price PnL and executed fees
book once; closing a position does not delete its unpaid claims. Missing amount
or timing is an unresolved obligation, not zero or silently immediate settlement.

Economic equity is not available exchange margin. Report actual available margin
as null without account/risk-rule evidence. The proposed synthetic decision budget
is `C - L + min(U, 0) - reserved_margin - reserved_fees`: it recognizes known
unrealized losses and excludes A and unrealized gains. It is not a proven lower
bound on Gate margin or a complete risk model. U must be available causally from
the declared valuation policy; unknown/stale U, liability amounts or booking/
valuation rules block new risk until resolved, while reductions remain permitted.
Reserved margin excludes losses and funding liabilities already counted above;
reserved fees exclude posted fees, so none are subtracted twice. This changes
the simulated state policy and must be versioned, not called unchanged replay.
Retrospectively computed E must never leak final future funding into a decision's
budget. Known and posthoc ledgers stay separate. No survival claim without full
margin/liquidation/ADL evidence.

Idempotency: key `(instrument,event_id,revision,entry_kind,allocation_id)`; exact
duplicate delivery has zero new posting. Same revision/different bytes quarantines.
A later authoritative correction appends a reversing/delta entry linked to its
original; do not rewrite earlier cash or feature history. Store restated economic
outcome and as-known revision history; affected old labels get a new revision and
new label_known_at. Unknown completeness watermark prevents finalization.

## 6. Episode labels and maturity

One same-side episode starts at flat-to-filled exposure and ends at natural flat
or the closing leg of a reversal. Decision origin is the original flat-state entry
proposal, with trajectory and full pre-decision state hash. Rejected/unfilled
proposals have no realized episode target, not a zero return. Keep their status
for selection diagnostics. Adds/reductions are the continuation policy, not
additional independent labels.

Track FIFO lots in the new standalone ledger (research allocation convention, not
a claim about Gate's display). Opening/add fill fee belongs to that lot; partial
reductions allocate the lot's remaining entry fee in proportion to quantity closed,
exit fees to filled close quantities, and funding by each lot's snapshot quantity.
Rounding residual stays with the final slice. The union of slices reconciles once
to episode cashflows; slices are not independent training rows. Current baseline
disallows pyramiding, but the contract must reject or correctly account for adds,
not ignore them. Multiplier changes need an explicit conversion before lot math.

`episode_net = realized_price_pnl + signed_execution_fee_cash + signed_funding_cash`.
Costs already embedded in fill prices are not charged twice. Primary denominator
is `gross_entry_notional_sum`: sum of notional of every exposure-increasing fill
in the episode, including entry partials and adds; no exit notional. Target is
`episode_net / gross_entry_notional_sum`, null for invalid/zero denominator.
It measures return on gross deployed entry notional, not account ROE or return on
margin. Record initial_entry_notional separately. With no adds/single entry it
agrees with the old denominator; otherwise this is a new label definition and
must not masquerade as QR003's native label schema.
Keep exact numerator `episode_net` and denominator `gross_entry_notional_sum`.
Serialize the target fraction to 12 decimal places with ROUND_HALF_EVEN; this is
a reporting convention, not venue cash rounding or a change to exact ledger sums.

The primary target is **cash-settled**; an earlier economic-accrual target is a
different proposal requiring review, not an implicit fallback for missing bookings.
`label_end` = last natural risk-closing fill time, independent of late funding
booking. `label_known_at` = earliest evidenced/as-assumed time the episode's
complete price/fee/funding result and revisions can be known, including late
bookings and a completeness watermark. It is >= label_end and must identify
SCENARIO versus observed clock. It is null when finality is unknown. Do not set
it to exit merely because the dashboard omits a later fee. Retrospective retrieval
does not supply historical first knowledge; actual historical maturity may remain
unproved, whereas a preregistered scenario can evaluate its declared information
clock. Training-dataset receipt is also bound before the real fitting operation.

Terminal forced closes, incomplete history, unresolved snapshots/marks/rules,
liquidation without supported modeling, missing fees/bookings or conflicting
revisions yield a separate invalid/censored status and null target. Observed
natural loss is valid; never censor because it is bad. Open episodes carry across
folds with no forced split exit or reset; pending late charges are retained after
the market cutoff as unresolved unless covered by a separately approved evidence
window. A label is train-eligible at boundary B only if valid, all inputs arrived,
`label_known_at_us + 86_400_000_000 < B_us` and
`label_end_us + 86_400_000_000 < B_us`, and its
information interval does not overlap the held-out label interval. Equality fails.

## 7. Validation plan and stop conditions

Before any model comparison freeze a registry entry: hypothesis/estimand,
dataset/code/config hashes, label and feature order, information clocks, costs,
all candidate/tuning budgets, primary metric, useful economic effect delta,
acceptable confidence-interval half-width w, risk constraints and stop rule.
Delta and w are unresolved research decisions, not universal profit thresholds.
No fit is authorized by choosing placeholders.

Chronological development template: 2023 warmup, train seed 2024, validation
2025 H1 then H2, retrospective audit 2026 to fixed cutoff; expanding fits may
use only earlier matured labels. Both symbols share the same calendar partitions.
All these years have already been examined and cannot become an untouched final
test by renaming. Reserve a genuinely prospective period beginning after protocol,
implementation and model-selection freeze; exact dates and one-shot stopping
rule must be registered before its data is viewed. No new acquisition now.

Purge training labels whose decision-to-known intervals overlap validation/test
information intervals (across both coins), in addition to the strict 24h maturity
buffer. Later observations never train an earlier fold. The 24h buffer is a
predeclared safeguard, not proof of independence; extend only by pre-outcome
dependence reasoning, record the change and do not reuse exposed tests. Fit
scaling, imputation, feature selection and hyperparameters only inside the proper
training subfold. Model/scaler artifacts need data/code/training-cutoff hashes.

Prediction reporting: paired MAE/MSE versus training mean, calibration if a
probability target is later selected, target/feature variation, counts by asset,
period and regime, invalidity and censoring. Economic reporting: full-state paired
net account returns, drawdown, exposure, turnover, fees/funding, insolvency and
execution failures on common calendar periods; never erase rejected trades from
the old ledger to invent a policy result. Hold constant intended resource/risk
constraints, not realized positions (which legitimately diverge).

Uncertainty: pair BTC/ETH in the same calendar blocks, retaining cross-asset
dependence; choose block length from training dependence/holding spans, freeze it
before validation outcomes, report sensitivity to a small declared adjacent set.
Report raw episodes, overlap clusters, independent-time coverage and uncertainty;
clusters are not automatically effective N. Effective-N estimates are diagnostic
and assumption-dependent, not a gate with a universal minimum. If blocks/regimes
cannot support stable intervals, report insufficient evidence. Plan sample size
using training-only dispersion/dependence and whether delta is detectable within
w; if not, stop or separately propose future observation, not more model searches.

The constant predictor and ML-off policy are mandatory distinct comparators;
fixed Ridge is a possible predictive control, not the chosen permanent model or
cap on research. Deep learning requires a specific hypothesis, evidence of added
value relative to simpler models, sufficient independent information, and a
separately approved resource/candidate budget. No model is fitted here.

Record every attempt, failure, parameter choice and test exposure. Control the
declared comparison family; use a preselected multiplicity adjustment if formal
tests are reported, or label exploratory comparisons honestly. DSR needs trial
history and dependence/non-normality inputs; PBO/CSCV needs an appropriate aligned
candidate-return matrix and is an auxiliary selection diagnostic, not a substitute
for forward validation or permission to train on future data. Neither is computed
here or used as a single approval statistic. [DSR](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf), [PBO](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)

Stop on integrity/causality/accounting failure, insufficient precision, depleted
preregistered search budget, exposed final test, or a material conclusion that
reverses under plausible declared execution/cost stresses. Report failure or
inconclusive evidence; never move the threshold after seeing PnL.

## 8. Minimum next implementation proposal and missing data

After separate authorization, build a small offline event ledger and contract
checker first, test synthetic acceptance cases, then add a read-only projection
from frozen market data, then an episode-label exporter and full-state replay
hook reviewed by both roles. Exact future paths belong to QD's design review.
Do not change existing runtime/carry/backtest/schema/defaults as part of this
proposal. Publish isolated artifacts and review before integration.

Additional evidence proposal (no collection): public effective rule/calendar
segments, exact mark-at-snapshot or a declared mark proxy series with freshness,
multiplier/conversion history or explicit scenario constants, and rate-publication
availability. Account cash bookings/actual fills cannot be recovered from public
OHLC; do not request credentials. If later voluntarily supplied sanitized exports
are authorized, they need a separate intake and privacy scope. Otherwise the
historical-exact claim stays unavailable and the scenario remains clearly named.
First future feasibility intake should be bounded to BTC/ETH and a few fixed
boundary examples, retain failures and hashes, and stop before bulk collection
until coverage and semantics are reviewed. It must not select examples by returns.

Approval states are separate: PROTOCOL_REVIEWED -> IMPLEMENTATION_VERIFIED ->
DATA_AND_LABELS_ADEQUATE -> TRAINING_PLAN_APPROVED. None implies the next. Current
task stops after QD review and a protocol report. User confirms before fitting.
