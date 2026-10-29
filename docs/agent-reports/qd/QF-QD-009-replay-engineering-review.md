# QF-QD-009: frozen R3 proposal engineering review

2026-10-28, Australia/Melbourne. **REVISE; DESIGN REVIEW ONLY.**
This is not scenario approval, implementation acceptance or permission to run.
R3 remains NOT_READY; R4/R5 and all fitting remain blocked by their separate gates.

## Allocation and exact review target

- Task: `QF-QD-009-R3-ENGINEERING-REVIEW`, dispatch
  `QF-DISPATCH-20261028-QD009-R3-ENGINEERING-REVIEW-1`.
- QD worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
  branch `codex/qd-cache-safety`; clean starting HEAD
  `19cd4c7e461799b9b9a13fef2028902e8dfcd48c`.
- Exclusive edit: this report only. Native sources, the QD009 interface request,
  QR proposals, shared journals and main are unchanged. The resulting commit is
  the commit adding this report; resolve with
  `git log -1 --format='%H' -- docs/agent-reports/qd/QF-QD-009-replay-engineering-review.md`.
- A–C target: QR commit `946e9fcbe2e10c1de3f51efea5f17d7395cd2067`, parent
  `0a90b2555db8e16934053abff31db29bac4296a2`. Both files were read from Git
  objects, not a moving QR worktree. Subsequent QR review does not replace A–C.

| Frozen object | Bytes / SHA256 |
| --- | --- |
| `research/qr009/replay-protocol-proposal.md` at946e9fc | 31192 / `e5e9bf76364fa6807e9de3f78ba14de2f80a928522a3a121d9d6e428f289245f` |
| `research/qr009/replay-spec-proposal.json` at946e9fc | 32549 / `da7517514a2973c2abb3ac2ff557b77c898c6d0098bcac629443e97d3d225b52` |
| `docs/interface-requests/qd-qf009-streaming-ledger.md` at19cd4c7 | SHA `36a7b157cdba45692b6737ba465d7b2bf4e29b9d2a012a52b67d454fb1c02ac7`; remains frozen |
| QR `research/qr009/streaming-ledger-review.md` at4d4e530 | 15031 / `a141bbf5ed69663b2db29ba0c7acffd41712c730eb0c0ce08ad166e6efa8578e` |
| QR `docs/agent-reports/qr/QF-QR-009-replay-design.md` at4d4e530 | 10133 / `54755a1496f9e17b72c5eb8539a69728906b6a29b28476f9c778264f09d69a67` |

The latter dependency commit is `4d4e5304be7646e0a4520f4ec8512a7890f847a4`,
parent946e9fc, supplied by control
`QF-CONTROL-20261028-QD009-QR-EXACT-RV-DEPENDENCIES-1`. Its RV01–RV04 are
contract-author work, not questions for the user. No interface was amended here.
The fourteen `strategy_binding.native_source_sha256` entries all match current
source bytes. Source citations below refer to those pins, not another checkout.

## Disposition and coverage

The proposal makes the previously implicit simulation choices reviewable and
preserves important unknown-data and causal-state constraints. It can proceed to
bounded revisions. It cannot be frozen as an executable manifest: R01 contains a
demonstrable numeric assertion failure; R02–R05 require explicit state/transport
bindings. R06 lists finite future acceptance work, not a measured failure.

| Requested review area | Disposition / location below |
| --- | --- |
| Approved inputs versus new research assumptions | Accepted separation; U1–U3 below remain pending |
| Complete native bridge, pending orders, books and fold/restart continuity | R02, R03 and QR RV01/RV02 dependencies |
| Exact/float64 boundary, session sign/reset/rearm | R01; remaining numeric acceptance in R02/R06 |
| Open-only fills, previous-hour capacity, cancellation and reservations | Accepted directions with R02/R04 binding requirements |
| Finite MARK query closure and independent latest-eligible evidence | Conditional acceptance; R05; actual supports NOT_EVALUATED |
| QD009 calendars/facts/cutoffs/atomicity/revisions/S13 compatibility | R03–R05 and exact QR RV01–RV04 dependencies |
| Initial synthetic versus later native/query/market resources | R06; no test/benchmark/replay execution |

## Directly acceptable design directions

These are design judgments, conditional on implementation and the three human
choices; they are not test PASS or evidence of realizable trading performance.

1. Keep the approved fee fractions0.00075/0.0015/0.0005 per fill, BTC/ETH
   multipliers0.0001/0.01, integer quantities and the economic data window
   `[2023-01-01,2026-10-01)`. Keep approved MARK clocks: primary delay60s,
   source age120s; stress120s/180s; available age60s. Preserve source seconds.
   Funding rate availability is strictly next UTC hour R, not flooring to8h;
   amount-known=max(R,qualified snapshot MARK availability), booking known+60s,
   and finality=max(complete scoped evidence,cash settlement)+1h. Historical
   receipt times, exchange tiers or booking times are not established by this.
2. Preserve current native configuration and mathematical modules. In particular
   use the existing closed-bar EWMAC/Carry/allocation/timing/sizing functions,
   ETH-only timing scope, disabled daily-loss gate and empty ML path. New research
   simulation rules must be disclosed separately from native-policy parity.
3. Strategy gets completed OHLCV; the proposed fill-only open view gets only
   instrument/time/open from the new hour. Capacity uses exact contract volume
   of the previous complete hour, with integer floor and shared reduction-first
   capacity. Adverse price embeds slippage once; no second slippage cash posting.
4. Preserve unknown T/U/reserves/coverage and block new risk rather than replacing
   them with zero. Keep natural reductions when their required closed inputs are
   supported. Unknown funding may permanently block reentry under this proposed
   scenario; retain those paths. Flat U=0 does not prove a supported new-entry MARK.
5. Distinguish booked C from E and spendable budget; do not finance risk with
   unknown amounts or unbooked receivables. Executed fee liabilities and future
   fee reservations are distinct. No monthly/year/fold account reset, partial
   entry top-up, forced terminal exit, or deletion of unsupported/negative paths.
6. The carry binding is explicit and causal: `prepare_features` supplies main-bar
   open timestamps to carry; `signal_at` waits for main-bar close. Source08:00:03
   -> R09:00 -> main open12:00 -> signal16:00 is consistent. The28800s unit and
   factor1095 are proposed annualization choices, not inferred settlement cadence
   or cash proration. Missing carry must be gated before native zero fallback.
7. Proposed eight scenarios/eighteen full-state paths and chronological skip of
   the first admissible entry are finite controls. Skip at decision admission,
   never remove a subsequently observed trade. This is no alpha/selection proof.

## R01 — blocking: completion delta cannot establish exact native session net

**Evidence:** protocol§5 sentence “session_pnl equals settled net immediately
before native reset”; JSON `native_feedback.completion_call` and
`numeric_projection.exact_postchecks`. Native
`src/execution_timing.py:182–196` adds Python float PnL, tests `<0`, then resets
the accumulator. `src/strategy_execution.py:91–96` is the scoped wrapper.

**Minimal literal counterexample, actually calculated with stdlib:** delivered
exact cash feedback is `[-0.1,+0.3,-0.2]`; its exact sum and settled episode net
are0, so the proposed exact completion delta is0. Sequential float64 addition
gives `-2.7755575615628914e-17`; adding float0 leaves it negative. Every individual
conversion meets the proposed1e-12 bound. The native close therefore takes its
loss branch if supplied a feature, although the authoritative net is exactly0.
After the call, session_pnl is0, concealing the pre-reset mismatch. This is a
literal arithmetic/source counterexample, not a replay or executed native test.

**Required QR revision:** remove the equality guarantee. Specify exact delivered
amounts separately from actual native float state, and an atomic pre-close branch
check on a staged native state before the irreversible feedback transition is
published. The computational accumulator may be approximate only under the
reviewed projection; zero/sign compatibility must be checked at the actual branch.
If it cannot satisfy the stated rule, preserve the prefix and report a distinct
numeric incompatibility, rather than promise all paths complete. Specify this
outcome in both files. No epsilon, skipped fill feedback, invented cash delta,
manual TimingState repair or retroactive rearm is an acceptable silent fix.

Bind calls to the scoped `strategy_execution.record_fill` wrapper. Direct calls
to `ExecutionTiming.record_fill` would create timing state even for disabled BTC
timing. Separate financial feedback bookkeeping from whether that native wrapper
actually runs. Also, native `record_fill` writes blocked_side/rearm_price on a
negative close even when `rearm_after_loss=False`; that flag is consumed by
`decide`, not the close method. Do not “fix” this native behavior in the adapter.

**Future acceptance:** zero and either-sign cancellation residuals, multi-part
fills, opening fee, delayed funding, permanently unknown net, both rearm flags,
both symbol scopes and later refunds. Check all native fields before/after reset,
including last_fill_bar/extrema and an existing block. Restarts before completion
must reproduce the same permitted branch or explicit stop, with one completion.
No claim to solve every float input is needed at this design checkpoint.

## R02 — blocking binding gaps: delayed callbacks, partial tickets and numeric context

**Evidence:** protocol§§3,5,8; JSON `execution`, `native_feedback.saved_state`,
`numeric_projection`; native `strategy_execution.py:28–96`,
`execution_timing.py:137–154,182–196`, `position_sizing.py:49–91,94–122`.

**Counterexample A (source reasoning):** an08:00 intent uses the07:00 hourly
feature; its delayed fill occurs09:00. Reusing that intent feature in the fill
callback sets last_fill_bar=07:00. The09:00 decision uses the now-closed08:00
feature and passes `bar>last_fill_bar`, potentially updating best_close/trailing
from a bar completed before entry. The draft permits reading prior closed bars
but does not choose the callback feature/bar binding. The old immediate-fill
loop cannot decide this delayed execution case implicitly.

**Counterexample B (literal):** model target100, requested ticket notional100,
actual partial-entry notional25. `EntrySizingBook.bind(100,100)` gives ratio1;
a later model target50 clamps to held25 and makes no reduction. Binding the
public method with actual filled notional gives ratio4 and target12.5. Therefore
copying old `backtest.py:465`'s full-ticket binding into a partial-fill replay
would change exit sizing. The current proposal does not specify this binding.

**Required QR revision:** distinguish intent feature, fill-feedback feature and
saved natural-close completion feature, with their clocks, plan scope and use
sites. Freeze which available feature each uses and explain any delayed-state
effect; do not rerun the signal to choose quantity or write last_fill_bar by hand.
Specify `bind` using actual initial executed notional, ratio persistence and
clearing only at the declared flat lifecycle point. No rebind to a hypothetical
full ticket or top-up after cancellation. Save the actual selected plan, feature,
native books, exact/float feedback state and pending/finality state in a closed,
versioned native-state contract; bit-preserving float serialization is required.

Submission may call unchanged `entry_ticket`, but freeze Python/numpy/pandas and
Decimal context too: quantity uses `Decimal(str(float))` under ambient context.
Independently check exact floor/tier/min/max/budget boundaries, including adjacent
integer quantities and >2^53/overflow/underflow. A conversion-error bound alone
does not prove branch parity. Native submission tier coverage is based on the
unrounded desired notional; do not silently replace it with rounded ticket N.

At fill, frozen-quantity validation is a distinct reviewed execution validator,
not a second `entry_ticket` call that recalculates quantity from changed C/price.
Specify its exact price, adverse reserve factor, tier coverage basis and metadata
checks. Test differences from native submission explicitly. This requires typed
adapter bindings, not changes to the fourteen frozen native modules.

## R03 — blocking cross-contract binding: warmup, account genesis and cutoff

**Evidence:** protocol§§2,5; JSON `account`, `evidence_tail`; QD009§§2–5,
especially lines198–205 and FinancialBody types; independent QR RV02.

The proposal has no financial account/claims in2023, but asks for explicit zero
funding eligibility/calendar evidence during warmup. A literal financial
FundingSnapshot at2023 with Config.initial_at_us=2024 is outside the kernel's
economic origin range. Retimestamping it to2024 would be wrong. Separately,
pre-genesis raw context admission is ambiguous in the existing QD proposal.

**Required revision/binding:** distinguish warmup facts and zero-inventory proof
from financial snapshots/obligations. Prefer an explicit immutable original-clock
context prefix and account genesis2024 with the account's due financial calendar
starting there; preserve the full2023 source calendar as warmup evidence. QR must
state the mapping in both proposal files; QD supplies the reviewed RV02 context
admission amendment. If another mapping is chosen, demonstrate no2023 account
activity or2024 reset. Do not silently enlarge the financial economic range.

At cutoff the order book must cancel pending orders while no new financial
origins are permitted at/after economic end. A newly emitted Reserves record with
effective_at=cutoff violates the frozen origin rule; a backdated cutoff-1us
release violates availability/frontier semantics. This is a binding problem,
not proof that every cancellation needs a kernel change. Predeclared reservation
expiry at cutoff plus a typed lifecycle/noop state transition may suffice.

Specify that solution, including financial view semantics for open holdings in
the2h tail. If tail recomputation genuinely needs new Reserves/Valuation origins,
QD must propose an explicit versioned profile/type delta with narrow scope and
QR review; it cannot be silently admitted to r3 or the frozen streaming profile.
Never claim a carried MARK remains fresh beyond its age limit. Tail assertions
may use stored qualified snapshot evidence without a new current-MARK query.

**Future acceptance:** before/equal genesis, no warmup cash/positions, initial
native prefix parity, restart after context admission, pending cancellation exactly
at cutoff, reservation expiry at equality, open versus flat-but-immature tail,
no post-cutoff market/query/order/decision, and late scoped evidence without a
history rewrite. Ledger state, timing/sizing state and source cursors survive
fold/month/year/checkpoint boundaries; annotations never reset them.

## R04 — required execution/atomicity clarification, not a new trading rule

**Evidence:** protocol§§3–4; JSON `execution`, `reservations`, `scheduler`.
The whole-ticket-before-capacity rule and own-reserve release are sound proposed
directions, but must be explicit in the future typed execution transition.

Example: C=100 with this pending order reserving80 leaves spendable20. For a
full requirement80, comparison must release only its own80, obtaining100. Using20
would incorrectly cancel; releasing another held/pending reservation would allow
overspending. A failed check terminally cancels/releases once; it must not first
publish an unreserved opening or leave a half-updated book. Then capacity may
reduce a passing request, never make a failing full request affordable.

Required atomic state/output binds frozen order quantity, own reservation identity,
exact pre-fill funds, full-check outcome, K consumption, actual fill/fee/Postings,
partial residual cancellation, native feedback and sizing-state update. K=0,
missing open/capacity and rejection produce no zero Fill/fee; cancel exactly once.
Executed fee remains a liability until its Posting and must not also remain a
future-entry/exit fee reservation. Held margin uses remaining lots/entry prices;
held future exit fee uses a qualified current MARK under the stated formula.
Guard both double fee and double slippage in the implemented A34 end-to-end trace.

Clarify same-time priority without changing it: primary phase4 executes an already
eligible old order before phase5's new opposing decision. Phase5 can cancel an
order still pending, e.g. a stress-latency order before its later eligibility; it
cannot retroactively cancel a phase4 fill using a newly computed signal. A new
order cannot fill in its submission phase. Reductions consume capacity first;
partial exit can receive a later fresh natural exit; reversal opening waits for
the required later decision and episode feedback gate. Test these phase ties,
no-fill/cancel/replacement and interrupted/resumed partial entry/exit/reversal.

This supplies acceptance requirements to an adapter task. It does not assert
that an unimplemented scheduler has already violated them. Transport and
atomic ledger publication also depend on QR RV01/RV03 below.

## R05 — conditional query acceptance; versioned fact/identity bindings needed

**Evidence:** protocol§§4,7–8; JSON `query_plan`, `numeric_projection`,
`postings_and_finality`; QD009 FactSchema/FactProjection, generated IDs and§5 seals.

The stated closure is acceptable for the proposed schedule: H_grid, H_grid+60s
and exact funding source S cover decisions/eligible opens, booking, finality and
snapshot roles. Same-us phase cancellation and exclusive scope endpoints add no
query times. Both latencies land on H. Tail adds no current-MARK query. Literal
upper bounds are `2*32856+4107=69819` per asset/clock and279276 overall, with
at most seven roles per lookup; deduplication can lower actual counts. This is a
schedule proof, not an observed query list, hit rate or support validation.

The independent checker must stream the complete required raw intervals and prove
the latest eligible source, including absence of a later eligible point. Eligibility
requires source+delay<=q, source age<=limit and available age<=60s, with equality
allowed. A supplied selected point passing those inequalities is insufficient.
Missing required adjacent-month coverage is unknown. QR008 raw PASS_WITH_GAPS and
its point-selection helper do not provide this query proof. Keep unsupported
queries/counts even for flat accounts; proved zero quantity can yield zero funding
without pretending the diagnostic MARK is supported. No actual support was checked.

**Required typed bindings before freeze/run:**

1. Register a distinct execution-only open Fact schema/view and original-clock
   qualification rule, rather than expose a retimestamped finalized OHLCV row.
   Mutating fill-hour H/L/C/V must leave earlier fills/decisions unchanged;
   mutating previous-hour V may change capacity only when that bar is available.
2. Separate raw point availability a=source+delay from its later selection at q.
   Example: after the sealed q1 prefix, q2 selects the same still-eligible point.
   Emitting a new financial body with available_at=a behind the frontier is
   PAST_AVAILABILITY. Define reuse of an existing financial record or a new
   consumer selection known/available at q, retaining raw fact availability a and
   valuation source time separately. Funding calculation must retain its actual
   approved snapshot MARK clock. No historical availability rewrite is needed.
3. Resolve `accepted_source_row_identity` in funding obligation identity. It must
   be a stable causal semantic identity, not implicitly a whole-file/catalogue
   digest. Rehashing a later raw row may change audit references but cannot change
   an earlier obligation ID, native state or economic sequence. Pin the exact
   logical key, duplicate/alias policy, and audit join in the typed binding.
4. Freeze query schema/plan hash, role schedule, source cursor, unknown reasons and
   actual-query-subset assertion. Boundary probes such as cutoff-1us/cutoff belong
   to synthetic lookup tests unless they are explicitly in the runtime universe;
   they must not silently expand it. Unexpected runtime queries hard-stop.

These can use separately reviewed closed Fact/input/intent/state schemas under a
new binding version. Where the frozen kernel cannot transport them, QD authors
an interface-request revision, QR reviews, and integration approval follows.
They are not silently added fields or authority to edit the current contract.
Late old-origin revisions are admitted only with new current availability and
valid references; past as-known views remain unchanged. Late unobserved new
origins are not repaired by these bindings. Later refunds update current ledger
and readiness, never replay an earlier native completion.

## R06 — finite resource acceptance dependencies; no feasibility result

The JSON and protocol now agree with the frozen initial ledger register:
N512/2048/8192/32768, two producer repetitions each =8 measured attempts;
60s each/480s aggregate; one producer and one QR functional suite120s each;
720s total, RSS256MiB/cache8MiB, aggregate new output2304MiB. The4x growth
limits remain T(4N)<=6T(N)+0.25s, bytes(4N)<=4.5bytes(N)+64KiB and
RSS32768<=RSS512+32MiB. This supersedes the draft's older uncommitted ladder.
It is a separate initial engineering register, not enlarged by later R3 ceilings.

Adopt QR RV04: make the initial functional inventory explicitly finite S01–S12,
with fixtures/negative reasons/ownership, and record S13 BLOCKED_NATIVE_PORT /
NOT_EXECUTED. QR checks saved artifacts; there are no hidden eight independent
benchmark repetitions. The later actual-native S13 gate needs its own finite
attempt/case/fixture/time/CPU/RSS/disk register before authorization. Neither the
initial suite nor a toy adapter can establish it. All34 QF006 criteria remain;
this report does not waive any to fit a cap.

Proposed query register: at most2 producer+2 independent attempts,600s each,
RSS512MiB and new disk256MiB each ->4 attempts, at most2400s/1024MiB of component
ceilings. Replay:18 planned+6 failure-diagnostic=24 started attempts,900s wall /
600s CPU /1024MiB RSS /512MiB disk /500000 journal records /256 checkpoints per
attempt, one active path; every168 active hours plus fold/end checkpoints.
Whole later R3 ceiling is14400s wall/CPU and14336MiB new disk including query,
tests and failures. Successful paths cannot be rerun for selection.

Sum of maximum per-attempt ceilings can exceed the global ceiling; that is not
a contradiction when first limit stops the stage. It also does not promise all18
paths finish. Freeze the later-native/test inclusion and sub-register, aggregate
accounting, failed/partial-output retention and remaining headroom before dispatch.
Define the500000 record metric separately from FinancialBodies, generated/noop
registry entries, receipts, index pages and checkpoints; report each actual count.
Do not redefine “record” after a run or suppress required traces to fit.

Native throughput is unmeasured. A naive `prepare_features` on every hourly
prefix from length8760 through32855 touches501377520 hourly observations per
path, about9.0 billion across18, before4h/daily/covariance work. This is a literal
operation-volume illustration, not a timing estimate. A bounded native synthetic
scaling/parity gate must precede market execution. Past-only reusable preparation
or an incremental equivalent needs evidence against the pinned functions; cached
future features cannot become trusted raw facts. No strategy rewrite or cap
increase follows from this observation. Initial ledger scaling is insufficient
to establish full native feasibility.

## Separate QD contract dependencies from QR proposal revisions

QR's exact4d4e530 review is REVISE. Its four items are accepted as required
contract-author follow-up, not blamed on A–C or delegated to the user:

| QR dependency | QD amendment / A–C connection |
| --- | --- |
| RV01 complete bounded economic input | Expose authoritative available intent/order status and actual FIFO lot ranges across policy/execution/environment ports, or an explicit equivalent composite port. Roots alone are insufficient. Include controller ledger-read inventory, selectors, clocks, bounds, hashes and restart state. This is necessary for R02/R04 funding/partial fills. |
| RV02 pre-initial context | Original-clock closed warmup facts and first-admission/dedup/cursor semantics without financial warmup replay. Connect to R03 and native prefix parity; no hidden precomputed future capsule. |
| RV03 durable resolution/stop recovery | After HEAD replacement uncertainty, re-establish required durability barriers under lease, validate reachable request/hash, distinguish orphan tails and REQUEST_CONFLICT, and restore persistent integrity/resource stops. Readable cached HEAD alone is not durable acknowledgment. No unlimited retries or restored ACTIVE over a stop. |
| RV04 finite initial manifest/S13 split | Initial S01–S12 cases and eight saved benchmark artifacts; S13 explicitly later blocked gate with separate finite register. Connect to R06 without increasing the initial caps. |

Revise the QD009 request in a separately allocated author-only commit, identifying
the changed contract/profile or closed-schema versions and migration/rejection
tests. QR must review that exact target. Current19cd4c7 is unchanged and remains
unimplemented. Accepted design directions in QR's review do not make its four
revisions optional or grant this task permission to implement.

## Three remaining human choice groups

Preserve these groups; coordinator asks after bounded engineering revisions.
No question was sent by this review and no choice was made for the user.

- **U1 execution:** retrospective open-only proxy, hourly decisions,1s primary /
  3601s stress latency,5/10bps adverse fills, previous-hour participation0.001 /
  0.0001, one eligible open/cancel and the proposed8bps reserve floor binding.
- **U2 account/feedback:** independent10000USDT accounts; C-based native equity;
  synthetic tiers/limits; pending/held reserves and unknown gating; delayed flat
  episode completion/reentry. R01/R02 must first make that recommendation precise;
  internal float/transport mechanisms are engineering work, not a fourth question.
- **U3 observation/validation:**2023 warmup/2024 account start, conservative native
  carry sampling with28800s equivalent unit,2h evidence-only tail, eight scenarios /
  eighteen paths and bounded attempts/resources. These do not authorize execution.

Already approved fees, MARK/funding clocks, multipliers, source segmentation and
economic window are not reopened. Null implementation/checker/schema/runtime/
resolved-config identities in `implementation_freeze_gate` correctly block runs.

## Minimal subsequent tasks and acceptance order

These are proposed dependencies, not new active allocations or permission to edit.
One role has one active task; every new dispatch must provide exact base/allowlist.

| Stage / exclusive editor | Finite scope and acceptance |
| --- | --- |
| A / QR | Revise only its two A–C proposal files for R01–R05, preserve U1–U3 and approved inputs; exact MD/JSON consistency and minimal examples. No runtime implementation. |
| B / QD, parallel to A | Amend only `docs/interface-requests/qd-qf009-streaming-ledger.md` for RV01–RV04 and identified transport/lifecycle bindings. Return exact target for independent QR review. No simultaneous edits to either author's files. |
| L / QD producer, separate QR oracle | Later `research/qd009/streaming_ledger.py` + `tests/test_qd_streaming_ledger.py`; QR `research/qr009/validate_streaming_ledger.py` + `tests/qr_research/test_qr009_streaming_ledger.py`. Only after reviewed contract/frozen S01–S12 manifest; execute the existing finite720s register, report all failures/ratios. QD007 r3 remains unchanged. |
| N / QD native bridge, QR independent cases | Later `research/qd008/native_adapter.py` + `tests/test_qd_event_replay.py`, with separately allocated QR oracle fixtures. Register complete typed projection/intent/feature/execution/state schemas; test actual pinned functions, R01/R02/R04, future perturbation, A23/A26/A34 and interrupted continuation. Freeze finite S13 budget first. No market data required. |
| Q / separately allocated query producer and independent checker | After approved query/scenario freeze and an explicit dispatch, stream the existing accepted inputs under the4-attempt register; independently prove coverage/latest eligibility and role closure. Exact disjoint paths must be assigned then; no new intake is implied. |
| R3 / future bounded dispatch | Only after L/N/Q acceptance, U1–U3 choices and complete code/data/config/schema/runtime bindings. Run prescribed full-state paths within global ceilings; preserve incomplete/unsupported/failed outcomes. No reset/forced exit/selection rerun. |
| R4 then R5 / separately allocated | Natural-episode export, maturity/finality, censoring/invalidity, strict24h boundaries and cross-asset purging; dependence/precision-based sufficiency. Then freeze features/model/search budget/metrics and truly prospective evaluation. Examined2023–2026 data are retrospective. Tell the user when gates pass and obtain fresh confirmation before any fit. |

Do not replace these gates with isolated arithmetic assertions, producer-generated
expected totals, an infrastructure-only PASS, QR008 raw intake acceptance or a
more profitable historical path. No current R4 label dataset, statistical
sufficiency result, prospective R5 plan, model training or activation is established.

## Work performed, verification and preservation

- Completed: exact-object/hash review, fourteen native source hash comparisons,
  static native dataflow/branch/state review, cross-contract comparison and small
  stdlib literal arithmetic checks. Both A–C object hashes/bytes and both QR
  dependency object hashes/bytes matched. Source pins matched14/14. The feedback residual, partial-sizing ratios,
  query upper bounds and720s/2304MiB initial totals above were reproduced.
- Commands used: `git show <exact-commit>:<path>`, SHA256 over those bytes;
  JSON parsing of the frozen spec; `Fraction`/float literal arithmetic; targeted
  source reads and Git status/diff checks. These are review checks, not strategy
  tests. No S01–S13 test, benchmark, native bridge, raw market-row scan, actual
  MARK query, replay, export, fit, network or application/engine launch was run.
- Modified files: this report only. No code/default/trading-rule/contract edits,
  credential access, dependency installation, merge, push, NAS or live operation.
  Shared PROGRESS/DECISIONS remain with integration editor after review.
- Original main HEAD: `cae0d2395adf2cd3905e41cb1c16748c8247c32c`.
  Before/after SHA256 preservation witnesses: staged binary diff
  `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`;
  unstaged binary diff
  `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d`;
  full porcelain/untracked status
  `2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649`.
  Final checks matched these witnesses before committing only this report.
- Limitation: R01's arithmetic mismatch is demonstrated; callback/transport/
  resource findings otherwise distinguish missing specification from prospective
  acceptance. No actual implementation behavior or market feasibility is claimed.
- Dependencies: QR revises its proposal, QD separately authors contract revisions,
  QR independently reviews them; coordinator allocates finite implementation work
  and later user choices. No automatic integration is approved.
- Next action: review this exact report commit, allocate A/B revisions, then stop
  this task. The coordinator reads the committed report directly; no cross-chat
  response or additional activity is required here.
