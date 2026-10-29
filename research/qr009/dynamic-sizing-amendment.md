# QR009: native dynamic risk budget ×10 amendment

2026-10-28. Task `QF-QR-009-DYNAMIC-MICRO-DESIGN`; dispatch
`QF-DISPATCH-20261028-QR009-DYNAMIC-MICRO-DESIGN-1`, continued under
`QF-RESUME-20261028-QR009-DYNAMIC-MICRO-1` after a service failure.
**DESIGN_PROPOSAL / QD_REVIEW_REQUIRED / NOT_EXECUTED.**
Local fidelity clarification: `QF-CONTROL-20261028-QR009-DYNAMIC-FIDELITY-1`.

## 1. Authority, scope and evidence

The coordinator relayed the human's selections: U1 execution assumptions and U3
observation/acceptance arrangements in revision `5dc72325580259ee8d578625f0ee33d0d13eec73`
are approved; U2 selects **native dynamic risk budget ×10** in place of the pending
fixed 5% margin ticket. Do not ask the human to select the multiplier again.
Other U2 choices are not approved by implication. This document proposes their
concrete compatibility mapping for review, without editing that frozen proposal.

Only BTC_USDT and ETH_USDT, independent simulated asset paths, PAPER research.
Cross margin stays the intended account mode; exchange leverage and production
defaults are unchanged. No fit, model activation, market replay, collector, engine,
private endpoint, account access, deployment or integration is authorized here.

Source inspection is pinned to QR base
`689414ca9714e020a48161bcec8fee402dfd365b`. The 14 native hashes in the frozen spec
were verified unchanged, together with the additional sources in section 9.
The allowed historical `agent.md` sizing excerpts corroborate the tracked report;
they are not executable evidence. No configuration, credentials or account files
were read. The historical results below are **reported, not independently rerun
or verified against raw artifacts**:

| Reported ETH scheme | Return % | Maximum DD % | First entries | Adds |
|---|---:|---:|---:|---:|
| Native | 2.78 | 2.13 | 32 | 48 |
| ×5 | 13.81 | 10.86 | 32 | 49 |
| ×10, human-selected candidate | 23.95 | 20.43 | 32 | 50 |
| ×20 | 30.38 | 38.56 | 32 | 54 |
| ×40 | 37.36 | 66.53 | 32 | 58 |
| Fixed 5% | -7.12 | 85.52 | 32 | 0 |

`docs/sizing-comparison.md` reports native first-entry margin median 0.0423%
and maximum seven consecutive losing episodes for every scheme. Its corrected
period is 2026-07-29 10:00 through 2026-10-27 08:00 UTC; the earlier table had
193 missing hourly candles and is superseded. Fees/slippage in that historical
study differ from current primary assumptions; its period extends beyond the
current 2026-10-01 cutoff. Neither unchanged entry count nor more adds supplies
more independent signals. This is no ranking of future profitability or evidence
that ×10 is optimal. No multiplier search or new baseline trajectory is proposed.

## 2. Exact scope of the multiplier

`src/portfolio.py:81–165` computes, in the native signal ordering, with annualized
volatility in fractions and covariance in annualized squared returns:

```text
v_i = max(signal.vol_annual_i, 1e-6)
tau = target_annual_vol_pct / 100
w_i = tau * (combined_forecast_i / 10) / v_i
sigma = sqrt(max(w' Cov w, 0))
c = sqrt(mean(min(abs(combined_forecast_i)/10, 1)^2))
k = tau*c/sigma if sigma > 1e-8 else 0
w_i <- k*w_i
w_i <- w_i * clip(signal.risk_multiplier_i, 0, 1)
w_i <- clip(w_i, -instrument_cap, instrument_cap)
scale each correlated group's gross down to group_cap if exceeded
scale total gross down to allocation_gross_cap if exceeded
target_notional_i = capital_at_decision * w_i
```

Adaptive risk is applied after volatility scaling; it must not be canceled by
another normalization. Native covariance reindexing fills missing cells with zero;
the proposed research adapter must instead reject missing required causal input
before calling native code. This wrapper precondition does not change native math.

The historical report explicitly scales target volatility, instrument exposure
and correlated-group exposure. The following model-only gross-cap mapping is
proposed to retain the frozen baseline's 4× risk-cap convention:

| Research field | Frozen reference | ×10 candidate | Status |
|---|---:|---:|---|
| `position_sizing_mode` | `fixed_margin` | `volatility` | Implements human dynamic choice |
| `target_annual_vol_pct` | 10 | 100 | Selected ×10 mapping |
| `max_instrument_exposure_pct` | 55 | 550 | Selected ×10 mapping |
| `max_correlated_group_exposure_pct` | 60 | 600 | Selected ×10 mapping |
| Pure allocation gross cap | 4 | 40 | QD-reviewed binding proposal |
| Exchange margin mode / leverage | Existing | Unchanged | No production mutation |
| Simulation margin divisor `L_sim` | Proposed 200 | Still proposed 200 | Remaining U2 choice |

Do not inherit the current dataclass default target of 15%: that would produce
150%, not the frozen 10% ×10 = 100%. Do not multiply final quantities, forecasts,
adaptive multipliers, execution leverage or a completed allocation again.
BTC and ETH share native `crypto_major`, but current independent paths do not
exercise a joint two-asset covariance, combined margin or shared-capacity account.

`max_leverage` is overloaded in the existing live engine: allocation uses it as
a gross cap and `ensure_cross_margin` uses it as exchange leverage for dynamic
orders. A pure research adapter may pass 40 to allocation; it must never call the
live engine or exchange setup with that value. A future shared production binding
requires QD to separate these meanings explicitly. The historical single-ETH
report used 200 in this overloaded field; its 5.5× instrument cap is tighter than
both 40 and 200. That explains a possible allocation equivalence for that scope,
not a general account-level equivalence or a verification of the old results.

`should_rebalance` uses the same scaled tau: base buffer is
`0.25 * capital * tau / max(vol_annual,1e-6)`. Ordinary same-side reductions
multiply it by 3; adaptive reductions with risk multiplier <=0.45 use the base
buffer. Trade only on a strict `abs(target-current) > buffer`. Preserve native
forced-exit handling and ETH-only timing, trend agreement and trail ATR 3;
timing partial rebalance may further change the executable target. BTC timing
remains disabled. Model target caps are not a guarantee that an existing position
cannot drift above a cap between decisions.

## 3. Equity clock, exact finance and quantity conversion

**Primary engineering-review candidate, still a remaining U2 proposal:** use
qualified as-known net equity `E` as the capital argument for both allocation and
buffer. Native backtest allocation uses mark-to-market equity and live code reads
account equity; E preserves that equity-based intent. The frozen r3 accounting
identity is `E=C+A-L+U`: booked cash, plus known unposted receivables, minus known
unpaid liabilities, plus qualified unrealized PnL. Retain exact values and the
reviewed binary64 projection boundary; do not substitute free margin or budget
for equity. `C` is a distinct alternative only if explicitly chosen later, not
the default for native ×10 and never a fallback when E is UNKNOWN.

Use latest closed, available 1h trade close for native current notional and
decision prices. Use qualified MARK for U/E, held exit reserves and funding. E
must come from the same admitted prefix/phase, with complete required obligations
and reviewed R05 qualification. Allocation may reflect known A/positive U as
economic equity, but the independent cash budget below still excludes them from
spending. Reserves reduce available budget, not E a second time.

This is not proof of identical native/real-account equity: the legacy backtest
marks at its loop prices and carries its own unsettled entry-fee/funding terms;
this candidate uses qualified MARK and explicit as-known obligation/posting
clocks. The real exchange account's collateral/equity-field reconciliation has
not been validated here. No actual available exchange margin is modeled. QD/QR
must reconcile these distinctions rather than claim the old table is reproduced.
Proposed initial C=E remains10000 USDT per flat independent path, not a confirmed
two-asset shared10000-USDT account. Freeze the concrete reviewed U2 choice before
implementation; this clarification changes no source, production risk or U1/U3.

`src/strategy_execution.py` dynamic mode passes actual current notional directly;
it does not use fixed `EntrySizingBook` ratios. Native target quantity is:

```text
q_nearest = int(round(abs(native_target_notional)/(price*multiplier)))
q_target = (q_nearest // native_min_lot) * native_min_lot
native_min_lot = max(1, int(order_size_min or 1))
```

This is binary64 nearest/ties-to-even followed by integer lot truncation, not
flooring the original ratio. The source comment claiming it always stays below
target does not hold at half-lot boundaries. Frozen research uses min lot 1,
integer orders, multipliers BTC 0.0001 and ETH 0.01; fractional observed ETH
volume remains exact and is never truncated before capacity calculation.
Fractional venue order minimums or future contract conversions need a separate
binding; no silent `int()` coercion is acceptable for those metadata.

Proposed independent quantity audit retains the exact decimal input and the native
binary64 target/price/multiplier bits. Reproduce each specified binary64 multiply,
divide and ties-to-even round, compare to the rational-input result, and apply
the frozen numeric boundary. If the rational and native computations select a
different integer quantity or cross a strict cap/limit, reject the candidate
before publication; do not round money to hide the difference or replace the
native result silently. Existing R04 state/numeric validation remains mandatory.

## 4. Minimal dynamic execution and reserve mapping

**Proposed adapter work, not implemented native protection.** Current dynamic
`build_order_plan` bypasses fixed ticket funds/tier validation, and live-engine
pre-entry refresh is tied to `needs_entry_ticket`. QD must add the reviewed
research validator before every increase, including a same-direction add.
Native plan and quantity are frozen once at submission. No second sizing call
at fill and no affordability-driven resizing.

Let `s` be adverse slippage fraction, `g=max(s,0.0008)`, `r` the per-side fee,
`p_d` decision close, `q` requested increase, `h` signed current contracts and
`a` its +1/-1 opening direction. Every value below is exact decimal/rational
finance after the native numeric boundary; `L_sim=200` remains an explicit U2
scenario assumption, not inferred real leverage.

```text
N0 = q*m*p_d                     Ng = N0*(1+g)
M_pending = Ng/L_sim             F_pending = 2*r*Ng
S_pending = N0*g
M_held = sum(remaining_lot_q*m*actual_entry_fill_price)/L_sim
F_held = abs(h)*m*qualified_current_MARK*(1+s)*r
S_held = 0
budget = C-L+min(U,0)-M_held-M_pending-F_held-F_pending-S_pending
```

Here `L` is known unpaid liability, not leverage; `A` and positive U are not
spendable. Unpaid executed fees belong to L; booking changes C and removes that
liability, without reserving that paid fee again. Pending reductions require no
extra M/F, because held reserves already cover them. Slippage already in executed
price is never expensed a second time. S is a disclosed cash buffer, not exchange
margin. Preserve the existing two-reserve presentation mapping.

Proposed full-request validation, in order:

1. Require known qualified finance and unexpired reserve state, exact metadata,
   valid native numeric/clock evidence, and original frozen positive integer q.
   At submission `T_sub=max(abs(executable_native_target), abs(h+a*q)*m*p_d)*(1+g)`.
   This replaces fixed `D_sub=C*0.05*200`. Validate aggregate post-increase position
   against the selected synthetic tier, not merely this order's incremental q.
2. Check projected rounded position against scaled instrument/group/gross caps
   using current qualified E. A rounding overshoot rejects the increase; no extra
   floor/re-sizing. Existing excess exposure cannot authorize a further increase.
3. At fill, q stays fixed. With execution-only open `p_f` before adverse slippage,
   use `T_fill=max(T_sub,abs(h+a*q)*m*p_f*(1+g))` for tier checks and the conservative
   `abs(h+a*q)*m*p_f*(1+s)` for current qualified E-based exposure caps. Validate q's
   min/max and metadata independently again. Full marginal funds requirement is
   `q*m*p_f*(1+g)/L_sim + 2*r*q*m*p_f*(1+g) + q*m*p_f*g`.
   The private comparison releases only this order's own reservation; held lots
   and all other commitments remain. Reject the full request if unaffordable.
4. Only then apply the approved closed-hour liquidity capacity and adverse fill
   price. Cancel residual at that opportunity, atomically record actual fill,
   fee claim/posting, native feedback and actual held reserves. There is no
   automatic retry/top-up of the residual.

These are conservative scenario predicates, not claims of exchange tier history.
For an increase, remaining U2 metadata proposal is min1, max1e9, synthetic 1000000-USDT
tier supporting L_sim200. Unknown metadata, finance or breached limits blocks
increases. A known legal reduction/close continues under its own validation; no
forced liquidation is manufactured. C<=0 or known E<=0 stops with the frozen
insolvency/incomplete status, without claiming a liquidation/ADL simulation.

Dynamic same-side adds are new native decisions from **actual held quantity**.
For example, held3, request3, fill1 leaves held4; a later frozen target8 proposes
4, not the previous unfilled2. A later add needs new facts, funds, capacity and
all validation. Keep max one pending order per asset path. A native opposite-side
plan can emit close and open together (especially timing-disabled BTC); retain
the approved scenario rule: close first, then a later decision after the finality
gate. Do not claim the raw native planner already enforces that rule for BTC.

## 5. Partial fills, episodes, feedback and UNKNOWN

Fixed-ticket terms to retire for this candidate: `entry_ticket`, fixed 5% desired
notional, its floor/min-ceil ticket algorithm, `EntrySizingBook.bind` ratios,
`model_entry_notional`, fixed held-target ceiling, partial-entry no-pyramid sizing,
and public ratio clearing on physical flat. New research identity starts flat;
the fixed sizing state is explicitly absent/empty in this dynamic binding.
Do not migrate a running account or mutate old snapshots into dynamic state.

Keep actual fill identity, original plan, causal latest-closed fill feedback
feature, timing scope, actual price, exact fees and FIFO lots. Frozen r3 ledger
`0ea2d51901689a351068bb9d33906c3240832afa:research/qd007/event_ledger.py:509–558`
assigns same-direction added lots to the active episode; FIFO closes partial lots;
only natural zero closes the episode. An add is not a new independent outcome.
Every add fee and every held unit at the funding snapshot remains attributed to
that episode. Pending unfilled contracts receive neither fee nor funding.

Native timing initializes its entry/best-price anchor only when the existing
anchor is zero; same-side adds retain that original anchor. Do not replace it
with ledger weighted entry price. Partial reductions are `closed=False`, with
entry_price0. Preserve actual native state, callback order and original fill-time
feature; no direct state edits. At physical flat, the proposed U2 finality/reentry
wait still applies, including BTC, though BTC has no timing callback.

R01 feedback guard remains unchanged: N is exact settled episode net, D exact
amount already delivered through actual enabled callbacks, S actual accumulated
native float bits. Delta=N-D, f=float64(Delta), R=fl64(S+f); enforce the pinned
numeric bound **and sign3(R)=sign3(N)** before the single completion callback.
No epsilon, fake Fill/Posting, overwritten S or cash inferred from binary64.
R04 preserves full timing/adapter state, source/config identity, monotone cursors,
snapshot/resume equivalence and the saved natural-close feature/plan. Completion
must not use a later finality-hour feature. Add/partial/close coverage must extend
the acceptance fixtures, not relax those guards.

R05 is QD-owned and currently under amendment. This proposal neither changes nor
accepts its moving draft. Required UNKNOWN must invalidate authoritative U/E and
budget according to the reviewed R05 result, retaining reason/provenance. Do not
spend old values, map unknown to0, write a query-time null financial origin that
shadows a later valid source, or turn a receipt into financial truth. Recovery is
from a later qualified as-known selection, not restoration of cached budget.
Recompute E and current held/pending reserves before any new increase. If E is
UNKNOWN, do not call capital-dependent allocation/buffering with C, zero or stale
E. Already validated reducing intents may execute under their own causal safety
checks; fresh capital-independent native exit decisions require an explicit
reviewed adapter path and valid trade features. Set `allow_increase=False`; do
not invent liquidation or rewrite a dynamic target to simulate an exit. QD must
test this distinction so missing equity neither enables risk nor silently blocks
valid natural exits. No model run or market acceptance starts on this paragraph.

## 6. Frozen protocol change table and execution limits

| Old provision | Proposed candidate mapping | Approval/evidence boundary |
|---|---|---|
| Fixed sizing mode / 5% ticket | Dynamic native ×10, section 2 | Human selected candidate; QD reviews mapping |
| Fixed `D_sub`, floor/min-ceil | Rounded native target + exact guard/tier predicates | New dynamic validator required |
| `partial_entry=NO_PYRAMID_NO_TOPUP` | No residual retry retained; fresh dynamic adds allowed | Explicit sizing-clause replacement, not silent U1 edit |
| Partial bind / held ratio / flat clear | Actual quantities + FIFO episode; no fixed book state | New binding/version and acceptance required |
| Equity/buffer capital | Qualified as-known E primary; explicit C alternative | Remaining U2 decision; no unknown-E fallback |
| Fees, liabilities, reservations | Same amounts/clocks, applied also to adds | Reserve formula remains U2 proposal |
| Natural-close wait and R01/R04 | Retained, adds included in episode net/state | Reentry adaptation remains U2 proposal |
| U1 order opportunity / capacity / cancel | Retained without additional attempts | Already approved |
| U3 data range / observation / budgets | Retained | Already approved |
| UNKNOWN / recovery | Consume independently reviewed R05 | QD completion then QR review |

Retain hourly decisions 2024-01-01 inclusive to 2026-10-01 exclusive, 24096 per
asset path; 2023 context only; no cash/position resets at observation boundaries;
2-hour evidence-only tail. Keep execution latency1s/stress3601s; adverse 5bps/
stress10bps; capacity floor(0.001 × previous closed-hour exact contract volume),
stress0.0001; reductions first, one shared capacity per asset boundary; no fill-hour
H/L/C/V in decisions. Primary fees0.00075, stress0.0015, reference0.0005 remain.
MARK lag60s/source-age120s/available-age60s, stress120/180/60; funding source-seconds,
strict next-hour rate availability, +60s posting and settled scoped finality +1h
stay unchanged. Source manifests and revisions must remain frozen.

Keep 8 scenarios / 18 planned trajectories / 24 total attempts including at most
6 failure diagnostics. No extra 1× comparison, multiplier sweep or microstructure
arm is added. Initial ledger benchmark: 4 sizes (512,2048,8192,32768) ×2 suites,
8 runs at60s +120s producer +120s QR =720s, 256MiB RSS, 8MiB cache, 2304MiB disk.
Later query register: at most4 attempts, each600s,512MiB RSS,256MiB disk. Replay
register: each900s wall/600s CPU/1GiB RSS/512MiB disk/500k journal/256 checkpoints;
global4h wall and CPU,14GiB disk; first limit stops. Native S13 subregister remains
unassigned pending a bounded engineering plan. These figures are retained limits,
not permission to execute any run in this documentation task.

## 7. Finite proposed acceptance cases

DS01–DS12 are proposed fixtures for QD review, not new market runs. Map them into
the existing bounded register or obtain a revised reviewed register; do not
silently append runs or claim they have executed. Each includes a negative case.

| ID | Positive acceptance | Rejection / failure oracle |
|---|---|---|
| DS01 | Frozen 10/55/60/4 becomes 100/550/600/40 for pure allocation | 15%-default inheritance, final-q ×10 or exchange leverage mutation |
| DS02 | Scalar F6, vol0.5, risk0.7, E10000 yields ideal N840 then8400; buffer500 then5000 | Adaptive risk renormalized away; strict-buffer equality trades |
| DS03 | Ties-to-even 1.5→2,2.5→2 then min-lot truncation | Blind floor; exact/native threshold disagreement; rounded cap overshoot |
| DS04 | E=C+A-L+U at decision; qualified MARK for finance, trade close for native notional; cash budget separate | Future fill close, A/positive U spent as cash, UNKNOWN E falls back to C |
| DS05 | Full request passes current funds/tier/caps before liquidity | Partial capacity rescues failed full request; tier checks delta only |
| DS06 | One partial fill, cancel residual; later add sized from actual held4 | Unfilled q funded/charged, automatic top-up, same decision resubmitted |
| DS07 | Added lot shares episode; partial FIFO close; scoped all-lot costs | Treat adds as new outcomes, close callback while inventory remains |
| DS08 | Native original timing anchor survives adds; actual callbacks preserved | Weighted-entry overwrite, skipped callback counted as delivered |
| DS09 | Full flat waits; R01 sign and numeric guard pass; single completion | Tiny nonzero N becomes zero, duplicate callback, future feature substitute |
| DS10 | Close first for reversal, then new later authorized decision | BTC raw opposite opening leg slips through before finality |
| DS11 | Required UNKNOWN blocks E-based sizing/increase; valid independent exits; recovery recomputes E/budget | Old U/E/budget used, E replaced by C, or query-null shadows recovered source |
| DS12 | Identical event stream and checkpoint restart yield identical decisions/state | Future perturbation changes past, mutable schema/config or changed U1/U3 |

## 8. Ownership and outstanding decisions

QR suggests future QD-exclusive work on a new research-only dynamic adapter/
validator, its infrastructure fixtures and the shared contract change request.
These are suggestions, not QD approval; the coordinator must assign exact new
paths before edits, including an explicit exception to general research ownership
where necessary. Per AGENT_COLLABORATION, QR exclusively edits `src/portfolio.py`,
allocation/factor implementation and `src/execution_timing.py`; QD exclusively
edits `src/strategy_execution.py`, `src/systematic_engine.py`, config, execution/
risk adapters and existing shared tests. QR owns these proposal/review documents.
Read-only inspection grants no editing handoff. Changes to a counterpart's files
require handoff; shared interfaces require counterpart review and integration
approval, including when a change is in the editor's own allocation source.
Prefer an additive research adapter over editing the live engine. QD integrates
shared PROGRESS/DECISIONS after review; QR does not edit them here.

Remaining substantive human decision packet, after QD review: (a) initial10000 per
independent path with qualified-E allocation as the main candidate (C is an
explicitly different alternative); (b) synthetic margin
divisor200, synthetic tiers and exact reserve/cap predicates; (c) settled-finality
wait before reentry and fill-feedback clock mapping. Present one concrete reviewed
packet, not repeated questions about ×10, U1, U3 or cross margin. Training approval
is a separate later decision after readiness evidence; it is not requested now.

Missing evidence: QD R05 final revision and QR acceptance, implemented dynamic
adapter/contract tests, S01–S13 and finite performance/query acceptance, approved
remaining U2 binding, reproducible native replay/chronological label readiness.
No training readiness or profitability claim follows from this design. Future
microstructure research is independent and not an added mandatory gate here.

## 9. Reproducible pins

All paths below are repository-relative at base `689414ca9714e020a48161bcec8fee402dfd365b`;
both frozen proposal files also equal revision `5dc72325580259ee8d578625f0ee33d0d13eec73`.

| Source | SHA256 |
|---|---|
| `research/qr009/replay-protocol-proposal.md` | `f7f42d0efe27427318dbe67d1feb4a246652a92db5eb1328936d0bae65a46ae2` |
| `research/qr009/replay-spec-proposal.json` | `77662b551963b7d09b429acdc17881bef854ea34df46e0dde05a5727f28d422e` |
| `src/strategy_signals.py` | `aa3b9e71512008ff43f49639d8d2cf113e81def7ab031e41676453def86e78dc` |
| `src/strategy_execution.py` | `e1eaa17ea1292c7e906d4634b274fe72f2a415dfa409054674a33c22b9b1f5bb` |
| `src/position_sizing.py` | `e80773ec1bf0ec88fdf8128f368649cf123d3ad92b615b46d3ce3e754c20efad` |
| `src/execution_timing.py` | `41d4593eaf345cdc8d26759605651e3e7bcfcb679604416b29fef80b821d9344` |
| `src/portfolio.py` | `1837e2601c2255515644394b6934f45a933d11c758f93aafae926d9bb120397d` |
| `src/backtest.py` | `9183091e85c4354720118c53f0d97b72022f018afa03d9e9479f4929f5a8540c` |
| `src/costs.py` | `356d3f5a29df9a64caeb40948fe4408dad81982fa5255cba051deb578b70621e` |
| `src/carry.py` | `81b370e9b84384be578db2163f7f4397b3edf41ebf78ffc56567522ead5e016f` |
| `src/trend.py` | `5234e1d35b7da34b8dd3429a6811b5ea5036d1e20a3af51fe70e34e56063a361` |
| `src/vol.py` | `8ed00ac4df7b86ffd2abcf80bcf55c201a631f7ac31d1e786f8e7cf95713ed3a` |
| `src/indicators.py` | `232a22a778a94eb0a101991474788a637078bea3f9832d8383683056878ef828` |
| `src/config.py` | `29eed6a35c7ecb8b079b21616754c49774fa0bb9034dbba3fc2112734c968709` |
| `src/models.py` | `01c28b7c42e00fcd6b5fcc6415246a5c73af5348fd5301d11b116f1064a8c20e` |
| `src/risk.py` | `95410f4adf88f25e1030d108c43f3a4069c162523ba91bdff91e7462966826ad` |
| `src/systematic_engine.py` | `ac583f50daa3bf0f2c4f77a0efcb54ece3cbfa5acb68a7bd013e840887282b7f` |
| `tests/test_execution_parity.py` | `f0c01f6a28d188c24fff29bc7053c20c7cea2d22595d4e256e1814f72b503a8d` |
| `docs/sizing-comparison.md` | `674f472b5bb5f9924827a153615561bd23a644a128f2b4fb3341590e0fbca230` |

Frozen r3 ledger at `0ea2d51901689a351068bb9d33906c3240832afa` has SHA256
`7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`.
It was read as text, not imported or executed. Current R05 files were not read.
