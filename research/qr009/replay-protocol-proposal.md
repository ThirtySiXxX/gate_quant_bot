# QF-QR-009: bounded BTC/ETH R3 replay proposal

Revision `qr009-r3-proposal-1`, 2026-10-28. **DESIGN_ONLY; NOT_APPROVED_FOR_RUN.**
Dispatch `QF-DISPATCH-20261028-QR009-R3-DESIGN-1`; base
`0a90b2555db8e16934053abff31db29bac4296a2`. QR owns this proposal and its JSON
companion. QD reviews feasibility and implements only under a later allocation.
The JSON is a machine-readable proposal, not an executable run authorization.
An inconsistency between it and this document blocks freezing either artifact.

## 1. Evidence and approval boundary

QR008 accepted exact OHLCV under the approved retrospective segmented source
scenario; MARK raw is PASS_WITH_GAPS. Neither means actual MARK queries pass.
QR007 `e2211a20` accepts the QD007 r3 **synthetic reference only**. Its 34 reviewed
QF006 requirements remain intact. QD's entire `d90e368` preflight was read,
including its funding-clock correction, 4096-record cap, full-history projection
cost, missing generated-source/checkpoint API and unresolved native feedback.
Exact hashes are in the companion spec. The coordinator's requirement audit is
a scheduling index whose R2 statuses predate the final QR008 review.

| Classification | Meaning in this proposal |
| --- | --- |
| APPROVED_INPUT | Existing authority; do not ask the user again or alter values. |
| PROPOSED_USER_ASSUMPTION | Concrete recommendation below; not approved by writing it. |
| ENGINEERING_REVIEW_REQUIRED | Binding/port/test/resource proposal; QD must review, then coordinator allocates implementation. |
| FUTURE_R4_R5 | Labels, statistical sufficiency, model plan and fit authorization remain separate. |

Approved inputs: BTC_USDT and ETH_USDT only; UTC economic window
`[2023-01-01, 2026-10-01)`; accepted whole-row archive/REST segmentation;
per-fill fee fractions primary `0.00075`, stress `0.0015`, reference `0.0005`;
MARK delay/source-age `(60s,120s)` or `(120s,180s)`, available-age at most60s;
funding source seconds mapped unchanged to simulated snapshots, rate availability
at the strictly next UTC hour, known amount+60s booking and complete settled
evidence+1h finality; integer tickets, BTC multiplier0.0001 and ETH0.01.
These establish a SCENARIO, not historical exchange arrival, tiers or bookings.

The old fixture's 10000USDT, 2bps fills and 8bps reserve reference do not grant
new approval. Recommended numbers below are newly proposed explicitly. No native
source/config/default, optional21-feature schema, old CSV or result schema changes.
No private config, current account fees, historical account or real-money access.

## 2. Recommended account and information policy

**New assumptions U2/U3.** One independent USDT account for each
`(scenario_id, instrument_id, trajectory_id)`, starting with C=10000, A=L=0,
no position/order/claim and empty timing/sizing books at2024-01-01T00:00:00Z.
2023 is indicator/covariance/carry warmup only: no simulated account trades,
orders, fees or funding claims. The funding source calendar still covers2023;
flat warmup eligibility is explicitly zero, not omitted calendar evidence.
No transfer, pooled BTC/ETH capital, deposits or monthly/year/fold resets.
BTC retains the frozen public policy's timing scope (ETH only); equal data rules
do not silently enable ETH-specific timing rules for BTC.

Use **booked cash C**, as-known and positive, for native allocation `capital`,
`decide_execution` equity/no-trade buffer and `entry_ticket` equity. Report E
separately; never pass restated E or spendable budget as native equity. The native
5%/200x ticket formula remains unchanged. Current position notional for policy is
signed contracts × multiplier × latest closed1h trade close, available at decision;
MARK exclusively values U/financial reserves/funding. QD must test this distinction.
Native allocation caps describe its model target, not a proof that fixed tickets
obey those same realized notional caps. The projection must disclose both.

Research metadata supplied to native sizing: USDT linear crypto contract, min
integer quantity1, maximum order/market quantity1000000000, leverage min1/max200,
one scenario tier risk_limit1000000USDT/leverage200. These are synthetic bounds,
not backdated exchange tiers. Over-limit tickets are rejected without resizing.
No liquidation/maintenance/ADL model exists; C<=0 or known E<=0 stops that trajectory
with INSOLVENT_SCENARIO, preserving the prefix and censoring unresolved exposure.
This stop is not an estimate of when an exchange would liquidate.

Unknown funding T, required held-position MARK/U, coverage or reserve amount makes
the spendable budget null and blocks opening/increasing exposure. Known receivables
do not finance risk. Record all unavailable checks, including when flat. Known
flat U=0 is an inventory identity; it is not a fabricated MARK observation. A
fresh opening still requires supported MARK and funding-calendar coverage.
Exit/reduction decisions continue using supported closed trade features and C,
with allow_increase=False; no forced close substitutes for a natural exit. Missing
execution-only open/capacity yields no fill. A later fresh valuation can restore U;
a missing snapshot MARK permanently leaves that particular funding amount unknown
under this scenario (never replace it with a later point). That account then
retains its trace and remains blocked for new risk, even after natural flat.
No bad-period removal, reset, shortened universe or return-based retry.

## 3. Decisions, simulated fills and capacity

**New assumption U1.** Evaluate policy at every UTC whole hour in
`[2024-01-01,2026-10-01)`:24096 opportunities per asset/path. Use only closed,
available inputs. Primary latency is1000000us (1s); stress3601000000us (1h+1s).
An order can execute only at the first hourly boundary f>=decision+latency,
f<cutoff. Thus primary first opportunity is next hour; stress is two hours later.
No intra-hour stop, touch, fill price interpolation or current-open execution.

The opening field of the exact hourly row is an **execution-only retrospective
open proxy**, available to the fill simulator at that row's open boundary. This
is a new simulation assumption: the raw finalized row does not prove the first
trade's historical receipt time or that size could trade there. It must have a
separate view; the full OHLCV row remains unavailable to strategy until close.
The fill callback sees only instrument/open_us/open_price from the new hour,
never its high/low/close/volume. Prior closed bars may be read normally. This
assumption requires user approval and independent future-field perturbation tests.

Per-side adverse price: buy P=open×(1+s); sell P=open×(1-s), s=5/10000 primary,
10/10000 slippage stress. No extra slippage expense posting. Exact decimal price
arithmetic, no invented tick-size rounding. Per-fill fees use approved scenario
rate on exact executed notional; no maker advantage. Native depth/spread checks
cannot be evidenced from OHLCV and are not represented as passed.

Named capacity proxy `PREVIOUS_CLOSED_HOUR_CONTRACTS`: at f, K=floor(p×V[f-1h,f)),
p=0.001 primary,0.0001 capacity stress. V is exact contracts, including fractional
ETH values, from the prior hourly row closed and available at f. No base/quote
volume substitution or volume from the new fill hour. K is an assumed per-asset
shared capacity budget at that boundary, not executable order-book depth.
Process reductions before increases; sum absolute filled contracts<=K.
If K=0, no fill/no fee. q_fill=min(q_order,K) only after the full requested
ticket passes exact affordability/metadata checks; this partial is liquidity
simulation, never clipping quantity to fit budget. No-fill and residual orders
cancel immediately after their one eligible fill opportunity in the same
timestamp, later phase. No retries within the hour, no fractional order contracts.
At most one pending order per asset/path; cancel an old pending order on a fresh
opposing/exit decision before submitting its replacement. Same-direction entry
repeats while pending are logged without resubmission. Expire all pending at cutoff.
Partial initial entries do not pyramid on subsequent bars; remaining entry is
canceled, not repeatedly topped up. Partial exits may receive a fresh natural
exit order at a later decision. A reversal is close first; its opening leg needs
a later eligible decision and the closed-episode feedback gate below.

Submission freezes native integer quantity using last closed1h close, fee rate,
and reserve slippage g=max(s,0.0008). The0.0008 reserve floor is a **new proposed
research binding** that matches the frozen public policy's8bps reference; it is
not inferred approval or a claim of depth protection. Fill uses5/10bps, not g.
At fill, recheck the whole requested quantity with actual exact open and current
funds; release its own pending reservation for this comparison only. If unsupported,
cancel rather than silently recalculate a smaller ticket. Do not rerun the signal
to select a favorable quantity at fill. A partial fill is atomic with its postings,
reserve release and timing feedback before any next decision.

## 4. Exact reservations, cash and same-time ordering

**New U2 binding; QD review required.** Let N0=q_order×m×submission_reference,
Ng=N0×(1+g), r=fee fraction, leverage=200. Pending opening reservation is
M_pending=Ng/200, F_pending=2×r×Ng, S_pending=N0×g. It matches the native ticket
requirement exactly before float projection. Once filled/canceled, remove it
proportionally/fully; with one-shot residual cancellation no remainder survives
that timestamp. Held M=sum(remaining integer lot quantity×m×entry_fill_price)/200.
Held F=abs(held contracts)×m×current qualified MARK×(1+s)×r for prospective exit.
Held S=0: adverse entry cost is already in price/U, never reserved or expensed twice.
Pending reductions reserve no additional margin/fee: held M/F already cover them.
Unpaid known executed fees belong to L, not future fee reserves; posting removes
that liability as it changes C. No fee/funding amount is paid twice.

`budget = C - L + min(U,0) - M_held - M_pending - F_held - F_pending - S_pending`.
For QF006's two-reserve presentation, reserved_margin=M_held+M_pending+S_pending
and reserved_fees=F_held+F_pending; S is separately disclosed as a cash buffer,
not exchange margin. A/positive U are excluded. Reserve values use only present
information and are recomputed at every scheduler boundary that changes funds,
position, pending order or MARK query. No stand-alone trigger on each raw MARK tick.
At fill, the exact full-ticket check uses N=q_order×m×actual_open and same g/r;
post-state reserves use actual filled lots. This can reject a gap-up order whose
earlier reservation was sufficient. Affordability, integer-floor and tier results
must agree with the independently computed exact predicates; no float epsilon
can rescue a failed exact boundary or silently shrink the native ticket.

Deterministic primary phases within one UTC microsecond:
1. Admit closed trade bars and newly available source information. MARK is selected
   from the qualified causal prefix for this timestamp; source hashes stay audit-only.
2. Capture all scheduled funding eligibility from pre-fill lots, including empty
   sets. Record immutable snapshot quantities and selected MARK/unknown reason.
3. Recognize now-known funding totals; apply due independent funding Postings.
4. Execute previously submitted eligible orders (reduce first), post realized price
   cash and each fill's fee, cancel residuals; release/recompute reservations.
5. Issue now-eligible scoped finality and perform delayed episode feedback; refresh
   valuation/budget, then hourly policy decisions and new-order reservations.
6. Append complete state/receipt and any checkpoint. No new order fills this time.

Tie-order sensitivity moves old-order fill/fee phase4 before snapshot phase2.
It uses already-known information/current budget before the new snapshot claim,
then performs funding/bookings/feedback/decision phases. It is a named scenario,
not filename sorting. All other phases are unchanged. A same-time pre-existing
close is eligible in primary and not in this sensitivity; a new open is opposite.

Fee obligation ID=(account,fill_id,fee), revision1, total=-q×m×fill_price×r.
Its distinct Posting ID=(obligation_id,posting,1) books at the same fill_us in
the subsequent posting phase; amount known at fill. Realized price cash and fee
are separately reconciled. Replay duplicates are no-ops; a conflict hard-stops.
Funding ID binds instrument, exact source timestamp and accepted row identity;
snapshot_us=source_seconds×1000000, R=(snapshot_us//H+1)×H, H=3600000000us.
With qualified MARK already available at snapshot, amount_known=R and booking=R+60s.
Missing MARK leaves amount/known/booking null; no schedule rounding. Zero eligible
quantity has a proved zero obligation under complete calendar, even if a diagnostic
MARK query is unsupported. Its final rate is still withheld from carry until R.

Finality authority is the frozen scenario, not purported exchange evidence.
Each assertion explicitly enumerates fills, fee/funding revisions, postings and
zero-eligibility coverage; economic-origin scope covers entry through natural
last close inclusive (exclusive endpoint=last_close_us+1us). Earliest assertion
availability=max(scope_evidence_complete_us,scope_cash_settled_us)+H. Unknowns,
unsettled P or missing coverage prevent it. Assertion scope, phase and receipt
are distinct; funding-only finality cannot finalize an episode. Future revisions
invalidate the latest assertion/label view, never mutate previous as-known views.

## 5. Natural-close feedback and end of observation

**Material new U2 adaptation, not unchanged replay.** Call unchanged native
record_fill for each actual fill with closed=False; deliver only that fill's known
realized price PnL plus signed executed fee cash (opening fee included). Persist
the cumulative amount delivered, episode identity and closing decision's feature,
side and bar timestamp. Funding is not fed through a fake fill.

At physical natural flat, enter WAIT_EPISODE_FINALITY. No new entries or timing.decide
calls while flat in this state; retain native state intact. When complete cash-settled
episode finality arrives, a separately typed **feedback-completion event**, not a
Fill, invokes unchanged record_fill with closed=True and delta=
settled_episode_net minus previously delivered fill feedback. It uses the saved
natural-close feature/side/bar, so session_pnl equals settled net immediately before
native reset and loss rearm uses the actual closing decision's extrema. Resume
decisions at the next eligible hourly phase (same timestamp only if finality phase
precedes it). This delays reentry at least through finality and is intentionally
disclosed. It does not pretend unknown net=0, know future funding early, call closed
twice, or revise prior rearm after a later refund. Later revisions change current
ledger/budget and invalidate current completeness; they do not replay past feedback.
Synthetic tests must cover both rearm enabled/disabled and permanently unknown net.
No raw writes to TimingState internals or new strategy logic are authorized here.

**New U3 assumption:** after market cutoff admit only already-scoped evidence in
`[2026-10-01T00:00Z,2026-10-01T02:00Z)`. No new trade/MARK observations, features,
orders or decisions; only derived availability/bookings/assertions of economic
origins strictly before cutoff using frozen inputs. Close-fill fees are immediate;
the latest possible pre-cutoff snapshot becomes rate-known at cutoff, booked+60s,
final+1h, inside this2h window. Unknown snapshot evidence stays unknown. At cutoff,
cancel pending orders, never force-close open positions. Open exposure is censored
for later label export; naturally flat but unsettled is immature unless unsupported
evidence makes it invalid. Keep all states and all negative outcomes. R3 writes no
EpisodeLabel dataset; these are required exporter inputs for R4.

## 6. Finite run and attempt matrix (proposal, not permission)

One-factor sensitivities, never a Cartesian search or best-return selection:

| ID | Change from P0 | Asset paths |
| --- | --- | --- |
| P0 | fee0.00075, slip5bps, latency1s, participation0.001, MARK60/120s, snapshot first | BTC/ETH allow-all AND skip-first-admissible-entry:4 |
| F_HIGH | fee0.0015 | BTC/ETH allow-all:2 |
| F_REFERENCE | fee0.0005 | 2 |
| S_HIGH | slip10bps, reserve g follows max(s,8bps) | 2 |
| L_EXTRA | latency3601s | 2 |
| Q_LOW | participation0.0001 | 2 |
| M_SLOW | MARK120/180s, available age60s | 2 |
| T_FILL_FIRST | pre-existing fills before snapshot | 2 |

18 prescribed paths total, eight scenarios. The first admissible-entry skip is
selected chronologically before submission/return, once independently per asset;
if none exists report NO_INTERVENTION. Replay its whole state, not delete a row
from allow-all. It is a causal engineering control, not a fitted strategy or alpha
claim. Sensitivities isolate assumptions; no scenario wins promotion by returns.

Proposed future budgets: query construction/checking each max2 attempts,600s/attempt,
512MiB RSS and256MiB new disk,4 attempts total; no whole56M-point materialization.
The **separate initial streaming-ledger engineering register** is QD009 section8
at commit19cd4c7: N512/2048/8192/32768, two producer repetitions each (eight measured
attempts),60s/attempt,480s aggregate; producer and QR functional suites120s each;
720s total,256MiB RSS,8MiB resident cache,2304MiB aggregate output. Growth limits
are T(4N)<=6T(N)+0.25s, bytes(4N)<=4.5bytes(N)+64KiB and RSS32768<=RSS512+32MiB.
Exact case inventory/S13 staging still requires contract review; no benchmark ran.
This supersedes this draft's earlier uncommitted16K/32K/64K doubling proposal.
It is not the later native/query/market budget. The limits below are prospective
R3 ceilings and cannot enlarge or grant retries to that initial ledger register.

Replay:18 planned paths plus at most6 failure-diagnostic reruns=24 total started
attempts;600s CPU and900s wall/path,1024MiB RSS,512MiB output/path,500000 journal
records/path,256 checkpoints/path. Checkpoint every168 active hours, each fold
boundary and final state; full prefix history retained on disk, no state resets.
Whole R3 stage (including query/tests/failed attempts) max4h wall/CPU budget and
14GiB new disk, excluding read-only frozen inputs; first reached limit wins.
Run sequentially, at most one active path. Every attempt, partial output and failure
counts. Successful paths are not rerun for prettier results. Benchmark failure
blocks market authorization; these caps are proposed ceilings, not measured promises.

Hash/schema/order/conflict/numeric/parity/causality/checkpoint/unexpected-query
failure hard-stops the run, preserving error and prefix. Ordinary unsupported
MARK uses retain-and-block-risk policy above, never a dropped timestamp. A completed
trace may be COMPLETE_WITH_UNSUPPORTED, not fully supported/accepted for labels.
Insolvency/resource failure is incomplete, never a successful full-period path.

## 7. MARK query universe and independent evidence

Define H_grid={start+kH | 0<=k<32856}, H60={h+60000000 | h in H_grid}, and S_i
as all4107 frozen funding source timestamps for asset i. Proposed lookup universe
Q_i=(H_grid union H60 union S_i) intersect [start,cutoff), for **each** of the two
approved MARK clocks. Do not compute actual supports or hit rates in this task.
Bound:<=69819 distinct times/asset/clock, <=279276 lookups across both assets/clocks;
at most seven role tags per lookup. Multiplicity is deduplicated, not silently
dropping role obligations. Account state/returns never select this universe.

Roles: decision, funding_snapshot, permitted_fill, valuation, reservation, booking,
finality_check. All hourly decisions/fills/fee postings/cancels occur in H_grid;
funding amount-known is strictly next H, funding booking at H+60s; finality is a
maximum of such evidence clocks plus H, hence H or H+60s. Snapshot is in S_i.
These sets are closed under every proposed event that asks for current MARK before
cutoff, including both latencies, capacity outcomes, no fills, feedback delays,
full-state interventions and fold/checkpoint annotations. No event schedules a
new MARK query at selected-point time, later mark receipt or arbitrary duration.
After cutoff no current-valuation query is permitted; finality uses previously
bound evidence only. Cancellation is same-us phase, not a new us timestamp.
Interval-exclusive scope endpoints are not query times. These restrictions form
the closure proof; changing them requires a new reviewed plan before execution.

Future checker must bind the approved plan/hash and independently stream every
relevant raw month, validate CRC/schema/order/alias and complete-prefix coverage,
and choose the **latest eligible source point** with source+delay<=q,
q-source<=source_age_limit and q-(source+delay)<=60s. Equality passes. It must
prove no omitted later eligible point exists, not trust a producer's point list.
QR008 select_mark only checks supplied points and cannot supply that proof.
Adjacent-month reads are necessary when the eligibility interval crosses a boundary;
missing any required source interval gives UNKNOWN_MISSING_MONTH, not zero coverage.
Never request pre2023 data to repair the approved start boundary. Raw alias grouping
requires the exact four parsed lexemes and numeric timestamp; retain every physical
row reference. Same numeric values/different lexeme is not an accepted alias.

Required tests: q=available-1us/equal/+1us; age limits±1us; q at midnight/month/year,
start and cutoff-1us/cutoff; nearest future vs latest eligible point; omission of a
later eligible point; missing prior/current required month; split alias across I/O
chunks; lexical conflict/descending timestamps; wrong price column; both clock IDs;
generated future-row/catalogue perturbation; actual trace query set subset of Q,
every permitted role checked. Unknown reason/count per asset/clock/period is reported
even if no trajectory holds a position there. Unexpected query is a hard stop, not
on-demand plan expansion. Raw gaps do not establish the query-gap hit rate, which
remains **NOT_EVALUATED**. Query plans are frozen only after user choices/QD review.

## 8. Exact-to-native numeric boundary

Projection proposal `qr009-native-f64-1`. Authoritative arithmetic is exact
decimal/rational and integer UTC us. Native float64 is only the computational
input to unchanged pure policy functions. Allow fields: closed timestamp/open/
high/low/close/contract volume; availability-filtered funding timestamp/rate;
native signal/target/timing fields; causal C/budget; scenario contract/tier fields.
Audit IDs, catalogue/full-file hashes, future rows, retrieval dates, provenance,
future fill inventory and global trace hashes never enter feature arrays,
random seeds, strategy branches or economic state. Keep a separate audit envelope.
Generated decision/order/fill IDs use account scope plus causal local sequence,
not a full-file digest; phase order never depends on lexical hashes. Raw source
identity and checkpoint artifact hashes remain verifiable audit bindings. A future
raw-file rehash may change those audit references, but must not change the past
economic projection, state-machine transitions or generated local event sequence.

At decision d, bar_open+interval<=d and research_available<=d<cutoff, with the
accepted segmented-source qualification. 4h/day are exact hourly-parent aggregates
at UTC boundaries. Their availability is parent-complete close, not hour-open.
Volume stays fractional contracts. Reject unsupported/missing/nonfinite inputs;
do not invoke native zero/fallback to hide missing sources. Canonical microseconds
convert to native seconds only after exact divisibility and safe integer range
(abs(seconds)<=2^53); do not send subsecond MARK/order clocks through float bisect.
All price/money/rate conversions measure exact Fraction(float)-Fraction(source):
finite and <=1e-12 absolute for |x|<=1, <=1e-12 relative otherwise, nonzero never
underflows to zero. No economic branch tolerance is granted by this error bound.
Record max errors per field; exact postchecks guard floor/round/min/max/tier/budget
and net-sign/rearm. Unsupported native output is a stop or explicit rejected
proposal before side effects, never an allegedly exact float-to-price roundtrip.

Funding projection timestamp is R/1000000, **not legacy available_at/source time**.
Recommend constant28800s as a named **8h-equivalent carry annualization unit**:
year factor365×86400/28800=1095. It is not a discovered actual funding cadence;
cash uses each exact source event without elapsed-time proration. Preserve native
prepare_features/carry alignment to main-bar **open** timestamp; this deliberately
samples only rates available at that4h bar's start, then signal_at waits for close.
Example source08:00:03 -> rate09:00 -> first main bar open12:00 -> signal16:00.
Do not quietly shift bars or replace carry arrays to make it trade sooner. This
extra lag is disclosed and causal, shared by BTC/ETH. Before a supported native
carry value exists, no new risk; warmup may remain unavailable without orders.
Projected old rates must never be retimestamped to earlier availability to restore
parity. The21-feature ML path stays empty; no model/scaler/calibrator imports/fit.

QD adapter must expose controlled deterministic ports with frozen code/input
identities and complete serializable state, not arbitrary callbacks with hidden
future data. The exact streaming contract is reviewed separately once supplied;
this proposal does not choose an unreviewed QD API. Full catalogue identity belongs to audit; causal
prefix and numeric state remain separable for independent future perturbations.
Before run freeze, record the exact QD/QR implementation and checker commits,
projection/checkpoint/query schemas, Python/numpy/pandas versions and complete
resolved configuration. Those engineering identities are currently unassigned;
null bindings in this proposal prohibit treating it as a runnable manifest.

## 9. Minimum implementation acceptance, then training gates

Keep all34 QF006 criteria/stage mapping. New adapter/streaming implementation must
pass (QD producer tests plus independent QR oracles):
- Small <=4096 tapes match the unchanged accepted r3 reference on cash, claims,
  FIFO/partial/reversal allocations, B1 unknown fees, revisions/refunds/assertions,
  idempotency/conflict atomicity and historical as-known snapshots.
- Incremental/batched/restart traces agree through fold/month/year, live lots,
  pending orders, delayed feedback, reservations and unknown claims. Checkpoints
  bind full state and source cursors; corrupt/partial writes cannot be published.
- Native parity on exactly identical projected inputs/config/state; separately
  enumerate expected old-replay differences (clocks/fills/reserves/feedback), never
  require incompatible old final returns or implement a new strategy to match them.
- Future OHLCV including unclosed fill-hour H/L/C/V, rates, MARK and regenerated
  audit hashes change no earlier features/decisions/orders/finances/native state.
  Projection thresholds, unavailable carry, >2^53, overflow/underflow, quantity
  floor/round, fee-sign and 1us boundaries use independent literal oracles.
- Budget C1000/L30/reserves105 gives865; posting-30 moves C970/L0 and still865;
  U=-40 ->825; U=+50 ->865; unknown U/T -> null/no new risk. Test pending own-reserve
  release, partialfill+cancel, fee double-count, gap repricing and unsupported exit.
- **A23 end-to-end:** an actual scheduler episode/pending claim crosses a fold;
  checkpoint restart preserves every state, no prior-fold eligible label. A forced
  terminal-close negative fixture is censored/null; main market run never forces it.
- **A26 end-to-end:** synthetic cash100/ticket80/first loss50 versus skip-first
  produces cash50 blocked vs cash100 eligible at the next actual decision. Run
  controlled scheduler/ticket ports, not handcrafted final states/row deletion;
  separately exercise real native5%/200x sizing where budgets can change eligibility.
- **A34 end-to-end:** buy reference100 -> fill101 -> exit110, base quantity1,
  zero fee/funding yields gross/net9 and no slippage posting; trace fee/reserve/
  cash/feedback too, not just an isolated arithmetic helper. Primary 5/10bps both
  directions and partial/reversal cases must use the same implemented price port.

This task performs only document/hash and small literal checks; the above tests
are **prospective**, not passed by writing specifications. R3 still needs reviewed
streaming contract, implementation acceptance, independent finite-query coverage,
frozen scenarios and explicit bounded run dispatch. R4 then exports/validates
natural episodes, maturity/selection/invalidity and both strict24h boundaries plus
cross-asset purging. R4 sufficiency must assess independent time/dependence,
training-only dispersion and a declared useful effect/precision; raw row count is
not a universal training threshold. R5 freezes features, model/candidate/search
budgets, metrics and an actually prospective evaluation window. Examined2023–2026
data are retrospective. **Tell the user when these gates pass; obtain fresh user
confirmation before any fit.** No model training or activation follows automatically.

## 10. Draft user questions (coordinator asks after QD review; do not send now)

1. **成交模拟：是否采用“每小时决策、延迟后下一个小时开盘成交”，单边滑点5bps，
   每次最多成交上一完整小时成交量的0.1%，剩余立即取消？推荐采用。** 这是用历史
   K线做的模拟，不能还原盘口；另固定比较10bps、再延迟1小时及0.01%容量三个单项压力。
   不采用则先调整这组规则，暂不运行；不从结果挑选最好的一组。
2. **账户与再入场：是否每币独立10000USDT，用已入账现金决定原有5%/200x票据，
   按上述公式预留保证金/费用；平仓后等资金费和费用完整结清并满足确认时间再开新仓？
   推荐采用。** 估值或资金费未知时保留记录和正常退出、暂停新增风险；可能长时间停仓。
   采用的是明示模拟档位和预算，不代表真实200倍账户能存活；这会改变再入场节奏。
3. **观察范围与有界验证：是否2023只预热，2024起计账户，保留原策略保守的4小时carry
   对齐并用8小时等效年化；截止后仅留2小时处理既有账款，按表中8情景/18路径验收？
   推荐采用。** 各项压力单独比较，未知数据不删样本；最多24次含失败尝试，受资源上限
   约束。这只冻结研究假设；实现/市场回放另行分段授权，训练前仍再次确认。

These three packages contain the material choices; the user is not asked to design
IDs/checkpoint internals. Any changed answer requires corresponding spec/query-plan
review. Already approved fees/MARK/funding clocks/multipliers are not reopened.
