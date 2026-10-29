# QF-QR-009: bounded BTC/ETH R3 replay proposal

Revision `qr009-r3-proposal-2`, 2026-10-28. **DESIGN_ONLY; NOT_APPROVED_FOR_RUN.**
R2 bounded revision dispatch `QF-DISPATCH-20261028-QR009-DESIGN-REVISION-1`,
base `4d4e5304be7646e0a4520f4ec8512a7890f847a4`. The initial dispatch/base below
remain provenance. This r2 incorporates the exact coordinator counterexample and
all440 lines of QD engineering report89cf347482c8121a4e3da559c6fb639a30788d6f, SHA256
`8ca4301e21aa599f97fde432695a5b40bfbcb8a58e03751f089430e2d3325e3e`.
R01–R05 are addressed as proposed bindings; R06 remains finite future acceptance.
QD contract amendments RV01–RV04 are not yet handed off/accepted by this revision.
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
orders, fees or funding claims. The full funding source calendar still covers2023 as original-clock context.
Warmup zero-inventory evidence is a configuration/context assertion of no active
account, not2023 FinancialBody snapshots or obligations. The financial account
and its expected-snapshot calendar start at2024-01-01 inclusive, end at cutoff,
and never replay/reset2023 cash. Pre-genesis context admission depends on QD RV02;
no timestamps are shifted forward or old origins inserted behind a sealed frontier.
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

R02 binding: store the original intent decision time d and its native timing
feature (hour open d-H, closed/available at d). At actual eligible fill time f,
select a distinct **fill-feedback feature** from the latest full closed1h bar
(open f-H, closed/available at f), with native timing_features on that causal
prefix. This does not rerun signal/ticket selection or change frozen quantity.
The callback uses the original intent plan's timing scope/config, but the fill
feature's bar_ts/extrema and projected actual opening price; reductions pass
entry_price=0. On natural final close persist this fill-feedback feature and its
original plan for delayed completion. Completion reuses them; it does not use a
new finality-hour feature or the earlier intent feature.

Thus an08:00 intent (07:00 feature) filled09:00 calls feedback with08:00 feature:
last_fill_bar=08:00. At09:00 the same feature cannot satisfy the native trailing
condition bar>last_fill_bar. At10:00 the09:00 feature is from an hour after entry.
Other native adverse/weak exits precede the last_fill_bar suppression and remain
unchanged; do not claim all same-tick exit logic is blocked. This delayed-callback
binding is a material U2 research choice, not a native function modification.

After the actual first partial/full opening fill, call public EntrySizingBook.bind
with the original native model_target and **actual executed entry notional**
abs(q_fill)*m*exact_fill_price projected under the numeric guard. Never bind the
requested/full-ticket notional. Freeze/persist the resulting native ratio through
partial exits; no rebind/top-up. At physical natural flat, clear it through public
model_current(symbol,0,0) in the same atomic lifecycle transition, then retain that
cleared book during finality wait. Do not directly write its ratios dictionary.
Example model100/actual25 -> ratio4; a later model50 maps to12.5, not held25.

Submission exact tier predicate uses unrounded desired D_sub=C_submission*0.05*200
and D_sub*(1+g), not rounded N0. Persist D_sub, original C, chosen tier, price/g/r,
quantity and public native results. At fill, an independent exact frozen-quantity
validator uses N_f=q_order*m*actual_open, tier basis max(D_sub,N_f)*(1+g), min/max
integer order limits and leverage200, plus N_f*(1+g)/200+2*r*N_f*(1+g)+N_f*g for
whole-order cash requirement. Its fresh funds exclude only this order's own
reservation. No second entry_ticket call/recomputed quantity from current C/price.
These distinct submission/fill predicates are explicit proposed U2 bindings;
QD verifies them and adjacent threshold cases before adapter implementation.

## 4. Exact reservations, cash and same-time ordering

**New U2 binding; QD review required.** Let N0=q_order×m×submission_reference,
Ng=N0×(1+g), r=fee fraction, leverage=200. Pending opening reservation is
M_pending=Ng/200, F_pending=2×r×Ng, S_pending=N0×g. It is the exact scenario counterpart of the native ticket
formula; native numerical results must pass the independent boundary checks. Once filled/canceled, remove it
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
earlier reservation was sufficient.
Own-release is a private comparison, not a published reserve removal. C100 with
this order's80 reserved leaves20; compare full requirement80 against100 after
releasing exactly that80. Never release another holding/order's reserve. Only
then apply K; capacity cannot make an unaffordable full order pass. Atomically
bind quantity/own-reserve ID/pre-funds/full-check/K/fill/fee claim/Posting/residual
cancel/native feedback/sizing ratio and new reserves. K=0 or missing/rejected open
produces no Fill/fee, and releases/cancels exactly once. A prepublication failure
publishes none of this candidate; prior committed events remain untouched.
 Affordability, integer-floor and tier results
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
not filename sorting.
Primary phase4 executes eligible old orders before phase5 calculates new signals.
A phase5 opposing signal may cancel only an order still pending (for example a
stress-latency order); it cannot retrospectively cancel that phase4 fill. Any
resulting fresh exit/reversal order observes its own later eligible open.
 All other phases are unchanged. A same-time pre-existing
close is eligible in primary and not in this sensitivity; a new open is opposite.

Fee obligation ID=(account,fill_id,fee), revision1, total=-q×m×fill_price×r.
Its distinct Posting ID=(obligation_id,posting,1) books at the same fill_us in
the subsequent posting phase; amount known at fill. Realized price cash and fee
are separately reconciled. Replay duplicates are no-ops; a conflict hard-stops.
Funding business ID uses a stable semantic key
(account_id, instrument_id, "funding_applies", exact source_seconds, mapping_rule_id),
encoded with the frozen ID helper; no raw-file/catalogue digest or physical row
number enters that key. Same key and identical semantic payload/rate lexeme is a
no-op with corroborating audit refs; any conflicting payload/lexeme hard-stops.
Physical row/hash identities remain separate audit joins, never economic IDs;
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

**Material U2 adaptation remains PROPOSED_USER_ASSUMPTION:** natural flat waits
for complete settled finality before session feedback/reentry. Native source and
strategy defaults stay unchanged. Feedback projection is now
`qr009-feedback-f64-guard-2` within numeric boundary `qr009-native-f64-2`.
The old assertion that native accumulated session_pnl equals exact settled net is
withdrawn. Binary64 is an approximate native computational state, never exact cash.

### 5.1 Exact amounts, actual native state and a pre-call gate

For each timing-enabled actual fill j, let p_j be its **exact** known realized
price cash plus signed executed fee cash, including the opening fee. Project once
to binary64 f_j using the fixed numeric bound in section8; call the unchanged
`strategy_execution.record_fill` wrapper -> `ExecutionTiming.record_fill` with
closed=False, the saved plan/feature and f_j. Do not write TimingState fields or
create fake fills. Track D=sum(p_j actually delivered through an enabled wrapper)
exactly and S as the actual native session_pnl **bits**, not float(D). Independently
verify S's sequential binary64 recurrence and actual candidate state after every
call. Require finite Python binary64 and round-to-nearest ties-to-even; no fsum/Kahan/
reordered sums can substitute for native += semantics.

At physical natural flat enter WAIT_EPISODE_FINALITY; no new entries or timing.decide
while waiting. Retain all state. Let N be the exact cash-settled episode net under
current complete revision/posting/assertion evidence. Null N or incomplete finality
means WAIT with no completion call; null never projects to0. For known N define
Delta=N-D exactly, f=float64(Delta), and predicted pre-reset state R=fl64(S+f),
using the pinned native += operation/order. **Do not choose f from S to cancel a
residual**; it must be the declared projection of the actual exact Delta.

Before invoking closed=True, all of the following must hold:
1. Account/episode/decision/feature/source clocks and current financial finality
   bind the same immutable prefix; completion has not occurred. Saved S bits match
   actual candidate native state and prior recurrence. No omitted/duplicate fill.
2. Delta projection and R are finite; nonzero Delta never underflows to zero.
   Exact D/N are retained independently. R may approximate N only within section8's
   fixed absolute/relative numerical bound, measured using Fraction(R)-N.
3. **sign3(R)=sign3(N)**, where sign3 is exactly negative/zero/positive, with either
   floating zero counted as zero. This has no epsilon. In particular the actual
   native predicate R<0 must equal exact N<0; a positive tiny N rounded to zero is
   also rejected. This stricter zero/sign guard prevents incidental sign changes
   being accepted because a numeric error tolerance happened to cover them.

If valid, a typed feedback-completion event (not Fill/Posting) calls the same
unchanged wrapper/native path with closed=True, f and the saved natural-close
plan/feature/direction/bar. Native session_pnl before reset is R, **not claimed
identical to N**. Verify the full returned state on a detached candidate before
publication, including last_fill_bar, loss branch's blocked_side/rearm_price,
session_pnl reset and entry_price/best_close reset; preserve all unrelated fields.
For zero/positive N, native leaves any existing blocked_side/rearm_price unchanged;
do not invent a clearing action. The completion call passes entry_price=0.
Store predicted R and its exact error in the receipt because closed=True resets S.
Resume at the next permitted hourly phase, including same-time phase only after
successful finality/completion. No later refund replays that completion or rewrites
past rearm; it changes the current ledger/budget/completeness view as before.

The wrapper skips feedback when timing is disabled or feature is absent. Freeze
this distinction: timing-disabled BTC records NATIVE_FEEDBACK_NOT_APPLICABLE,
never creates fictitious TimingState or counts p_j as delivered; the U2 finality/
reentry gate still applies to the account. Timing-enabled missing required feature
is a binding error, not permission to count a skipped call as successful. The sign
check applies when timing is enabled even if rearm_after_loss is false: record_fill
still changes blocked_side on a loss, so that flag cannot bypass validation.

### 5.2 Failure atomicity and complete persisted feedback state

Any numeric error, sign mismatch, stale/altered state, skipped required wrapper,
wrong prefix, or post-call state divergence causes a typed stop before publication:
NUMERIC_FEEDBACK_PROJECTION, NUMERIC_FEEDBACK_SIGN_MISMATCH,
FEEDBACK_STATE_MISMATCH, FEEDBACK_BINDING_MISSING or NATIVE_FEEDBACK_DIVERGENCE.
These are **proposed adapter errors**, not silent additions to QD's frozen kernel
registry; QD must bind their rejection/audit transport during engineering review.

Preflight reads immutable state only. Future implementation must reconstruct the
unchanged native object in an isolated candidate using its public restore operation,
then invoke actual native code only after the pre-call guard. State mutation inside
that unpublished candidate is reversible. Verify before committing candidate ledger,
orders, native/sizing state, feedback receipt and cursor together. A failed call/
check publishes none of that tick's candidate changes and stops further decisions;
previous valid cash/fees/postings remain, never rolled back to hide the failure.
Persist an audit/control failure receipt with exact N/D/Delta, S/f/R bit strings,
error/sign predicates, code/prefix IDs and no committed native call for the failing
completion. Post-publication I/O uncertainty follows the separately reviewed
COMMIT_UNKNOWN protocol; do not falsely claim rollback. Never switch policy or
restart a failed trajectory to suppress this failure. No epsilon, residual injection,
compensating cash, pseudo-fill, raw TimingState write or new native strategy.

Persist a closed feedback capsule per account/instrument/trajectory/episode:
- status (ACTIVE/WAIT_EPISODE_FINALITY/COMPLETED/STOPPED), ordered delivered fill IDs
  and exact p_j values, exact D, delivery applicability, f_j bits and actual S bits;
  recurrence/prefix receipt binds the complete sequence, not just its sum.
- All native TimingState fields/presence: last_bar, weak_count, last_fill_bar,
  blocked_side, rearm_price, session_pnl, entry_price, best_close. Preserve finite
  float bits and typed integers exactly; native sizing ratios likewise. A public
  dump/restore roundtrip must preserve bits; missing field/state is not defaulted.
- Pending order/decision/plan and saved close feature values (including recent
  extrema), direction, bar/source/available clocks, native config/code/projection
  versions; exact source fields separate from their native projections.
- Current exact ledger/lot/claim/posting/reservation state via verified checkpoint
  references, scenario/asset/calendar/query/feature cursors and full other adapter
  states. These references must reconstruct authoritative values, not hash-only
  inputs. Audit/catalogue hashes cannot become numeric policy inputs or seeds.
- Finality scope/revision/Posting identities and their availability, exact N/Delta,
  f/R bits and errors when attempted, completion event ID and exactly-once latch,
  last committed clock, durable failure latch and resource/attempt accounting.

Restore checks this capsule against ledger prefix and delivered-call recurrence
before accepting another native call. Do not reconstruct S from exact D or infer
missing transient state from eventual returns. Preserve incomplete/unknown and
stopped capsules across I/O/month/fold boundaries. Later review defines the exact
closed transport schema and size budget; this list is a required state inventory,
not permission to add fields ad hoc or claim R3 restart acceptance now.

### 5.3 Finite regression vectors and honest evidence boundary

Exact coordinator counterexample SHA256
`4d42124402c0af2515458b4f3021453d4c57564590e96f3b0b5612505dfd002b`:
p=(-0.1,-0.2), D=-0.3, N=0, Delta=0.3, yet native-style S+float(Delta)=
-2^-54=-5.551115123125783e-17. R2 must reject before the completion call; it must
not trigger loss rearm and describe that as zero-net behavior. This is stdlib
literal evidence, not a fault observed in an implemented native/market adapter.
QD R01 also supplies p=(-0.1,+0.3,-0.2), D=N=Delta=0; sequential binary64
leaves -2^-55. The same pre-call gate must reject that second zero-net example.

Future bounded native acceptance vectors (all PROSPECTIVE):
- FB01 above: SIGN_MISMATCH with no committed completion or rearm change.
- FB02 p=(-0.125,-0.25), N=0: exact representable cancellation passes; native
  require actual native closed-reset verification. FB03/04 p=(-0.1,-0.2), N=+0.125/-0.125: allow bounded
  floating approximation only with the correct exact sign and native branch.
- FB05/06 p=(-0.25,-0.25), N=+2^-60/-2^-60: projected correction cancels to0;
  reject both rather than erase a tiny gain/loss. FB07 N=null: WAIT, no projection.
- FB08 altered S/checkpoint bits: STATE_MISMATCH even if loss predicate coincides.
  FB09 nonfinite/overflow/nonzero-underflow projection or state: reject before call.
- FB10 duplicate completion, same event altered payload, late revision/refund:
  exactly-once/noop or conflict as appropriate, no old rearm rewrite. FB11 disabled
  timing versus enabled+missing feature; enabled/rearm_after_loss true and false;
  complete expected TimingState, not only a boolean branch.
- FB12 partial fills, natural close, delayed funding/fee completion across fold/
  checkpoint, interrupted/uninterrupted actual native-wrapper path. All calls,
  exact ledger, numeric receipts and decisions must match; no synthetic final state
  substitution. Perturb only future inputs/audit hashes and compare past states.

Small stdlib arithmetic/bit checks are allowed in this design task; none establishes
FB10–12 or complete native acceptance. Keep A23/A26/A34 and all34 QF006 criteria.

**New U3 assumption:** after market cutoff admit only already-scoped evidence in
`[2026-10-01T00:00Z,2026-10-01T02:00Z)`. No new trade/MARK observations, features,
orders or decisions; only derived availability/bookings/assertions of economic
origins strictly before cutoff using frozen inputs. Close-fill fees are immediate;
the latest possible pre-cutoff snapshot becomes rate-known at cutoff, booked+60s,
final+1h, inside this2h window. Unknown snapshot evidence stays unknown. At cutoff,
cancel pending orders via a typed account lifecycle/state transition, never
force-close open positions. Predeclare every pending/held Reserves expiry at or
before cutoff (each pre-cutoff record expires at min(next scheduled recompute,
cutoff)); equality is expired. At cutoff emit no new Reserves/Valuation origin,
no backdated release and no changed financial range. Cancellation changes declared
order/adapter state; zero post-cutoff reserve amounts are not fabricated. The
financial view reports expired/unknown reserves and budget=null; no tail new risk.
Open holdings retain lots and old marks only as timestamped evidence: current U/E
are unknown when mark age expires. Flat U=0 remains an inventory identity; E may
be known when claims are known, but expired reserves still forbid a budget. Tail
as_known checks re-evaluate age/expiry using stored evidence; they are not new
MARK lookups. Known late Postings/assertions reference pre-cutoff obligations and
may finish flat episode readiness without a fresh current mark. QD must bind this
lifecycle/context transport in its reviewed amendment; this proposal adds no
financial types to the frozen contract. Open exposure is censored
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

R06 accounting: the500000 journal-record cap counts each admitted FinancialBody,
Generated entry (including noop), DecisionRecord, typed lifecycle/trace transition
and commit/failure receipt as a record, even when nested in a serialized parent.
Count each logical identity once in this metric; copies in checkpoint files are
not new logical records but still consume byte/disk budgets. Also report each kind,
physical JSONL rows, index pages/visits, checkpoints and bytes separately; never
redefine the metric after a run. The native S13 case/fixture/attempt/time/CPU/RSS/
disk register and aggregate headroom allocation are still unassigned run blockers.
Initial ledger throughput cannot establish native throughput. Require bounded
synthetic native prefix/scaling parity before market execution; cached past-only
preparation needs independent parity, not future feature Facts or a strategy rewrite.
The global first-reached ceiling may stop before all18 paths complete; no resource
increase or extra benchmark is authorized by this revision.

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

### 7.1 R05 closed source/consumer bindings (proposed, not registered)

Execution-only schema `qr009.exec-open-fact-v1` has the existing closed Fact
transport header, instrument, stable semantic fact key, economic_at_us=open_us,
scenario_available_at_us=open_us, and only cell open_price:D+ USDT_per_base.
The consumer projection is exactly instrument/open_us/open_price; no H/L/C/V.
Qualification binds the accepted full source row and its unchanged close-time
availability separately in audit, plus U1's explicit open-only simulation rule.
This is not retimestamping the full OHLCV Fact. Native strategy never sees this
execution schema. Future fill-hour H/L/C/V changes cannot affect that fill; previous
hour V may affect K only when available. Extra fields/wrong schema fail registration.

MARK observation semantic key=(instrument,"archive-mark",source_us); accepted
exact-lexeme aliases retain all raw refs separately. The original QR008 audit point
IDs stay unchanged and are not reused as causal business IDs. Raw availability
is a=source_us+scenario_delay. A consumer selects at q and records selection_known=
selection_available=q, retaining a and source_us separately. Reusing a source at
q2 never emits a financial body newly available at old a behind sealed q1.

When a qualified financial Valuation for that source/rule already exists, reuse it
with a new consumer receipt. Otherwise propose a current-q delivery with
valuation_at_us=source_us and known_at_us=available_at_us=q (only for an origin in
the financial window), not valuation_at_us=q pretending the point is newer. An
initial flat account may use a pre-genesis context point for the explicit entry
qualification gate without fabricating an out-of-range financial Valuation. For
funding calculation retain source valuation time and actual a<=snapshot, even if
the final total is first known at strictly-next-hour R.

Current UNKNOWN query status must also reach the authoritative financial/adapter
view: never use a still-cached supported balance after a failed required query,
or create a null Valuation at q that shadows a later legitimately selected older
source. QD must supply reviewed query-scoped qualification/status transport that
propagates unknown U/reserves/budget and permits later qualified recovery without
backdating. This is an explicit interface dependency; current19cd4c7 is not assumed
to support it. If unavailable, registration/run stays BLOCKED, not a private API
or unreviewed field extension. Frozen r3 remains untouched.

Proposed closed consumer query payload `qr009.mark-selection-v1` contains exactly:
instrument_id, query_us, mark_clock_id, roles (set of the seven declared roles),
status (SUPPORTED/UNKNOWN), source_us, source_available_us, source_semantic_key,
mark_price, selected_at_us and consumer_available_us (both q), unknown_reason.
SUPPORTED requires all source/value fields and unknown_reason=null. UNKNOWN
requires those fields null and one reason MISSING_REQUIRED_MONTH,
NO_ELIGIBLE_POINT, SOURCE_TOO_OLD, AVAILABLE_TOO_OLD or UNRESOLVED_SOURCE_OR_RULE.
Invalid/conflicting raw input is a hard integrity failure, not benign UNKNOWN.
An audit envelope separately binds plan/version/hash, qualifier/code identities,
raw refs and selection proof; no such hashes enter numeric policy fields.

Freeze canonical schema/plan hashes after user choices; null/unregistered bindings
block execution. For each Q_i key the finite superset permits the seven known
role tags; actual event-role timing is additionally checked against its scheduler
rule. Unexpected time/asset/clock/role hard-stops; boundary probes at cutoff-1us/
cutoff remain synthetic-only unless explicitly in the frozen runtime set. Persist
sorted-query cursor, raw month/physical-row cursor, alias carry/lookahead, current
selection/unknown receipt and actual-used query-role set with checkpoints; restore
cannot omit gaps or repeat a lookup as new information. Completeness/latest-point
proof and actual-query subset checking remain separate independent gates.

## 8. Exact-to-native numeric boundary

Projection proposal `qr009-native-f64-2`; feedback binding is section5.1–5.3. Authoritative arithmetic is exact
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
and pre-call feedback zero/sign/rearm classification; the numeric tolerance never
permits a branch disagreement. Technical indicator branches remain the pinned
native float policy, not a newly invented exact indicator implementation.
Unsupported native output is a stop or explicit rejected
proposal before side effects, never an allegedly exact float-to-price roundtrip.

Native Decimal context is an explicit local binding, never ambient: precision50,
ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals1, clamp0; traps InvalidOperation,
DivisionByZero and Overflow enabled, other traps disabled, flags cleared per native
invocation. Restore the caller context afterwards. This does not make
Decimal(str(float)) exact source arithmetic; submission floor/tier predicates still
need independent exact checks. Native binary64 platform and Python/numpy/pandas
versions must be pinned before S13/run; unresolved implementation_freeze_gate
identities remain blockers. No dependency installation/change is authorized here.

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
   每次完成反馈前还要核对浮点状态与精确净额的零/正/负分类；不一致就停止验收并报告，
   不用容差掩盖或自动修正金额。延迟成交后的状态更新用成交时最新已收盘小时，
   完成反馈复用该次平仓成交的特征；这会影响再入场/移动退出时序，也仍待你确认。
   数值与接口细节先由QD复审，不增加研究情景或第四个问题。
3. **观察范围与有界验证：是否2023只预热，2024起计账户，保留原策略保守的4小时carry
   对齐并用8小时等效年化；截止后仅留2小时处理既有账款，按表中8情景/18路径验收？
   推荐采用。** 各项压力单独比较，未知数据不删样本；最多24次含失败尝试，受资源上限
   约束。这只冻结研究假设；实现/市场回放另行分段授权，训练前仍再次确认。

These three packages contain the material choices; the user is not asked to design
IDs/checkpoint internals. Any changed answer requires corresponding spec/query-plan
review. Already approved fees/MARK/funding clocks/multipliers are not reopened.
