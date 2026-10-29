# QR005: data acceptance does not settle the cash-flow target

Status: dependency proposal only; no adapter or replay implemented. QD owns
backtest execution and any future adapter. QR owns the label/cost semantics.
Reviewed native source is bound by QR003's phase-a-input-spec source hashes.

## Confirmed existing behavior

- `src/carry.py:60` and `src/backtest.py:183` use past-or-equal funding records.
  A record timestamped 08:00:01 is unavailable at 08:00:00. Preserving this is
  compatible with v2; it is covered by the QR005 tests.
- Carry annualization uses a caller constant, currently 28,800 seconds in the
  frozen research fixture. Exact event rows do not prove that historical interval.
  V2's event descriptor interval_seconds=0 is not a parameter for this calculation.
- `src/backtest.py:384` accrues funding each step as
  `notional_at_step * signed_rate_at_step * elapsed / declared_interval`.
  It does not apply one debit/credit per actual settlement event.

A synthetic long position with fixed 1,000 USDT notional, last known rate 0.0001,
and a declared 8-hour interval accrues 0.0125 USDT over an hour even if its entire
holding period contains zero settlement events. With the same constant notional,
actual event accounting would charge zero in that example. This is a mathematical
counterexample to equivalence, not a new strategy backtest or measured bias on
BTC/ETH. Endpoint notional/price changes can create further differences.

## Required separate decision

One route is to explicitly retain a hypothetical prorated-cost target and name
its assumptions in every label and model evaluation. That requires a separate
label-policy review; it must never be described as exact historical settlement.
The other route is a new event-based research adapter. The following acceptance
criteria make that proposal reviewable, but are not implementation authorization:

1. Specify the position eligible at an event, including entry/exit at the exact
   same timestamp, partial reductions, reversals and events between hourly steps.
   Preserve actual source seconds; do not round events onto the decision grid.
2. Define event notional/valuation price and its availability. Hourly trade OHLC
   does not supply exact settlement mark prices. A declared causal proxy remains
   a simulation assumption; no future close or backdated current metadata.
3. Debit/credit each eligible event exactly once. A holding window with no event
   has no event funding. Reconcile fee, funding, reduction, final cash and equity
   ledgers; retain terminal censoring and bankruptcy without resetting accounts.
4. Separate funding-rate feature annualization from cost-event accounting. Keep
   as-of causality, no current-rate fallback for missing required history, and an
   explicit schedule/multiplier policy with source/vintage limitations.
5. Freeze code, config, dataset and cost policy; run at most one uninterrupted
   ML-off baseline per coin only after the relevant approval. Use actual exit
   cashflows, one label per position, chronological label-end + 24h maturity and
   dependence diagnostics. No parameter, threshold or model search.

QD must propose the exact changed file allowlist and tests before any such task.
It must not edit QR-owned contracts or migrate shared runtime interfaces silently.
This task leaves G3 BLOCKED and runs zero baselines.

## When a model can be proposed

Before asking to fit, require usable economic labels under the reviewed policy,
adequate mature/nonconstant observations across separated periods, disclosed
time/asset dependence, and a reviewable chronological evaluation plan. Freeze a
prospective untouched holdout, useful economic effect and uncertainty/precision
target. All history in this phase is development/retrospective, not a fresh test.
The earlier one-model/six-feature ridge proposal remains only a proposal. No
scaler fitting, coefficient fitting or threshold selection occurred here.

When those conditions are met, present the exact data version, target, fixed
model, split/embargo, costs, resource budget and stopping rule to the human.
Obtain fresh confirmation before the first fit. Data-consistency PASS alone does
not meet this gate, and historical profitability would not establish future edge.
