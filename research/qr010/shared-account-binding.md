# QR010: BTC/ETH shared cross-margin research account

2026-10-28; `QF-CONTROL-20261028-QR010-SHARED-ACCOUNT-1`, within
`QF-QR-010-HISTORICAL-MICRO`. **Human-approved account direction and simulation
assumptions; engineering binding below; implementation/replay NOT_EXECUTED.**

This supersedes the independent-asset account target in QR009 for future work,
without editing its immutable evidence. The coordinator relayed the human's
explicit choice of one BTC/ETH cross-margin account, total initial 10000 USDT,
native dynamic risk budget ×10, margin divisor 200, synthetic 1000000-USDT tier,
pending margin/fee/slippage reserves, UNKNOWN blocks increased risk and settled
episode finality before that asset reenters. U1/U3 other assumptions stay approved.
These choices are not reopened. No exchange/account configuration was accessed or
changed; no actual available-margin or liquidation/ADL equivalence is asserted.

## One account and one native allocation

Create one new account identity and one continuous state from 2024-01-01 through
2026-10-01 exclusive, with 2023 causal warmup and the already approved evidence-only
tail. Initially C=E=10000, both inventories zero, A=L=U=0. Never assign 10000 to each
coin or add independent returns. Cash and funding/fee postings are shared:

```text
E = C + A - L + U_BTC + U_ETH
M_held = sum_asset(sum_live_lot(q_remaining*m*entry_fill_price)/200)
F_held = sum_asset(abs(q_held)*m*qualified_MARK*(1+s)*fee_fraction)
M_pending = sum_pending(N0*(1+g)/200)
F_pending = sum_pending(2*fee_fraction*N0*(1+g))
S_pending = sum_pending(N0*g),  g=max(s,0.0008)
shared_budget = C-L+min(U_BTC+U_ETH,0)-M_held-F_held-M_pending-F_pending-S_pending
```

Net unrealized PnL is aggregated once under cross margin: e.g. U_BTC=+100 and
U_ETH=-60 yields U=+40 and no positive-U spending credit; do not also subtract 60
by independently clipping each asset. A is included in economic E but excluded
from spendable cash budget. Reserved margin is not an extra E expense. Known
unpaid liabilities are reserved once; posting transfers them into C without
double charge. Held funding/fee attribution, FIFO lots and natural inventory
episodes remain keyed by asset, account and stable economic identities.

At each shared hourly decision use one admitted prefix and common UTC cutoff
for both assets, and exactly one `allocate_portfolio` call with both forecasts,
annual volatilities and the full 2×2 causal covariance. Keep native symbol order
BTC_USDT, ETH_USDT for reproducible floating computation, not for cash priority.
Use qualified E for allocation and rebalance buffers. Risk parameters are
target annual vol 100%, instrument cap 550%, `crypto_major` group cap 600%, pure
allocation gross cap 40. Both assets share crypto_major; its6×E cap is tighter
than gross 40×E. Native conviction and adaptive reduction are applied once to the
joint allocation; no duplicated per-coin full risk budget or post-allocation ×10.
The exact native source pins/formulas remain QR009 section9; no native edit here.

Require both instruments' closed, available feature inputs and complete finite
positive-risk covariance with consistent interval/units. Reject missing cells
before native `.fillna(0)` could manufacture independence. Do not silently drop a
coin, use separate 1×1 allocations, fill a return gap, or redistribute an ineligible
coin's target to the other. A singular but valid covariance uses the pinned
native formula; no new covariance estimator or regularization is fitted here.

Missing required MARK for either held asset, unknown required obligation or
unqualified account financial state makes E/shared_budget UNKNOWN and blocks
**all account increases**, including an otherwise healthy other coin. No fallback
to C, old E or zero U. Known flat inventory has proved U=0 without requiring its
mark merely to value no position. Missing one coin's strategy/covariance input
blocks a fresh joint allocation even if account finance is known. Existing valid
reductions/close intents and reviewed capital-independent native exits remain
possible; they cannot be blocked simply because another coin cannot add risk.

## Simultaneous orders: atomic budget admission, no coin priority

Chosen engineering rule: **admit the eligible increase basket atomically or reject
all its increases**. It is reproducible and avoids giving cash to whichever asset
is iterated first. This conservative choice can leave cash unused and suppress a
profitable smaller leg; it is not economically neutral or claimed optimal. Freeze
it before outcomes; no ranking by realized returns, lexicographic coin preference,
recomputed weights or budget-driven quantity scaling.

1. Process due public information, cash claims/postings and old-order outcomes
   under the approved scheduler. Actual completed reductions release only their
   actual lots/reserves. A new reduction intent does not pre-release future cash.
2. Compute the joint native targets once. Preserve ETH-only timing and actual
   quantities; flat assets awaiting their episode finality cannot submit fresh
   increases. Mask those legs without reallocating risk to the other asset.
3. Validate the remaining basket's full frozen requested quantities, exact
   metadata, per-asset tier and joint projected caps together against the same
   current E/budget. Sum marginal reserve requirements once. Equality to available
   budget passes if all exact predicates pass; otherwise reject the basket with
   `BASKET_BUDGET_INSUFFICIENT` or a specific non-budget reason. Commit all proposed
   reservations in one account transition. An invalid leg does not become an
   implicitly resized or independently favored basket.
4. Permit at most one pending increase basket/account and one pending order/asset;
   no same-side resubmission while pending. An opposing decision cancels the
   still-pending basket atomically before any replacement decision, releasing
   only that basket's actual reservation. This intentionally cancels an unchanged
   other-coin leg too; record the opportunity cost. A fill already committed in
   the earlier scheduler phase cannot be canceled retroactively.
5. At the eligible execution boundary recheck the **entire frozen basket** using
   current qualified account state and each full requested quantity before
   applying liquidity caps. Privately exclude only the basket's own pending
   reservation from the comparison, preserving all held/unrelated commitments.
   If any leg fails risk/funds/required input validation, cancel all increases.
6. Once admitted, U1 capacity remains per asset: reductions first, then increases;
   BTC liquidity cannot fill ETH. Each leg can fill partially or zero according
   to its own capacity. This is atomic risk admission, not fictitious all-or-none
   exchange execution. Cancel every residual at that one opportunity. Commit all
   actual fills, claims/postings, inventory, callbacks and reserve recomputation
   as one ordered account transaction. Never rescue an unaffordable full basket
   with a lucky partial fill.

With known budget 100 and full requirements 60+60, reject both; do not choose BTC.
With budget 120, reserve 120 once. If each admitted leg fills half, release the
unused reservations after actual fills/fees, and reconstruct held reserves from
the two actual half positions. Exact money is independent of serialized order;
native callback/state order is explicitly timestamp, phase, then BTC/ETH stable
identity. This serialization must not change admission, capacity or funding
eligibility. Same-time funding primary snapshot sees both pre-fill inventories;
the approved fill-first sensitivity sees both post-fill inventories, never a
mixture determined by asset-loop order.

## Tier, limits, finality and UNKNOWN are separate concepts

The approved synthetic 1000000-USDT tier applies **per contract to total projected
held plus requested exposure**, including existing lots and all admitted increases.
It supports divisor 200 in this scenario; it is not a historical exchange schedule.
There is no additional invented 1000000 account tier. Joint group/gross caps and
one shared cash budget constrain the combined account. At submission and fill
retain QR009's conservative rounded-quantity, g-buffered tier and current E-based
cap checks; do not check only each incremental order. A notional target/equity cap
does not imply intrabar margin sufficiency or guaranteed survival at 200 leverage.

Close-then-later-decision reversal stays per asset. Native same-side additions
share that asset's active FIFO episode. An asset's physical natural zero enters
WAIT_EPISODE_FINALITY until scoped fee/funding totals are known, settled and the
approved assertion clock is reached. R01/R04 exact-net/native-sign/full-state
guards and saved actual-close feature apply to that asset's callback only.
BTC remains timing-disabled; its episode/reentry gate still exists.

The other asset may hold/reduce/add while an episode awaits **proof-only finality**,
provided global financial values are qualified and the shared budget supports the
whole eligible basket. Known unpaid closing costs occupy L until actually posted;
known unsettled positive amounts occupy A but are not spendable. Unknown cost
totals make global A/L/E/budget unknown, blocking all increases. Thus an episode
waiting for a finality certificate is not automatically an account-wide UNKNOWN,
and a global UNKNOWN is not resolved merely because one coin became flat.
Never require both assets to be flat to attribute/close one natural episode.

R05's qualified UNKNOWN/recovery path must recompute account U/E and reserves on
recovery, without stale-value reuse or query-time dummy Valuation origins. This
binding consumes the implemented reviewed semantics; it does not initiate another
full R05 document review. Targeted implementation tests should cover the new
shared-account cases, once QD's code is ready.

## Exact replacement of the independent-path register

Replace 18 independent asset trajectories with **9 joint account trajectories**;
each carries BTC+ETH together throughout. One account per trajectory, identical
initial 10000, no resets across observation windows. No fitted models.

| Scenario | Joint trajectories | Change from primary |
|---|---|---|
| P0 | `ALLOW_ALL`, `SKIP_FIRST_ADMISSIBLE_BASKET` | Primary fee 0.00075, slip 5bps, latency 1s, capacity 0.001, primary MARK, snapshot-before-fill |
| F_HIGH | `ALLOW_ALL` | Per-side fee 0.0015 |
| F_REFERENCE | `ALLOW_ALL` | Per-side fee 0.0005 |
| S_HIGH | `ALLOW_ALL` | Per-side slip 10bps |
| L_EXTRA | `ALLOW_ALL` | Latency 3601s |
| Q_LOW | `ALLOW_ALL` | Participation 0.0001 |
| M_SLOW | `ALLOW_ALL` | Existing slow MARK clock |
| T_FILL_FIRST | `ALLOW_ALL` | All pre-existing fills before funding snapshot |

The sole path-dependence intervention skips the first chronologically admissible
new-entry basket from a fully flat account before order submission; if both coins
are in that basket, skip both. It does not select an asset by return or by name.
If none exists, record NO_INTERVENTION. Purpose: quantify downstream state/cost/
feedback dependence, not select a trading policy or turn sensitivity into alpha.

Keep at most 6 failed-run diagnostic restarts: 9 planned +6 diagnostics=15 starts,
below the absolute24-attempt ceiling. The unused 9 slots are unassigned, not extra
search permission. Keep per-attempt 900s wall/600s CPU/1GiB RSS/512MiB disk/500k
logical journal records/256 checkpoints, concurrency1; global 4h wall and CPU,
14GiB disk, first limit stops. Shared-account size may increase processing costs;
report inability to finish instead of splitting into misleading independent runs.
Existing separate query/synthetic caps stay unchanged; no execution in this task.

## Outcomes, implementation ownership and targeted acceptance

Primary results are account net return, equity/drawdown, shared budget/margin
utilization, turnover/costs, joint tail loss, correlated losing exposure and
drawdown recovery. Preserve per-asset mature episode net labels and overlapping
time-block dependence; summing episode counts does not create independent samples.
Future micro baseline, rule filter and ML increment must all use this same joint
account, costs and execution conditions. No independent-account control versus
shared-account treatment. A rule can reduce trades mechanically; report forgone
returns/exposure and cash competition, not only longest streak.

QD implements shared account scheduler, atomic basket/reserves, exact ledger,
adapter and infrastructure tests. QR retains allocation/factor and scientific
ownership of `src/portfolio.py`; no role edits another's file by inference. Existing
native math may be reused unchanged; additive adapter code is preferable. Shared
contract changes must record this user-approved scope and exact new schema/version.

Finite targeted cases for implementation: one 10000 genesis; joint covariance and
6×E group cap; missing off-diagonal rejection; +100/-60 cross-U example;60+60 vs
100/120 basket tests with reversed input iteration; one partial/one zero fill and
exact release; per-asset 1m tier plus joint caps; held ETH MARK UNKNOWN blocks BTC
increase but not a valid close; known-but-unfinalized ETH costs vs unknown costs;
per-asset close/reentry while BTC remains open; duplicate fee/funding/close proof;
same-time whole-basket funding ordering and restart/future-perturbation equivalence.
Run these once against concrete code; repeat only for a specific defect/change.
This document adds no new performance experiment and authorizes no model fit.
