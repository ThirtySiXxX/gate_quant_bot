# QF-QD-009: exact QR r2 engineering rereview

2026-10-28 Australia/Melbourne. **REVISE — limited cross-contract alignment.**
R01–R04's requested research-design clarifications are accepted, conditional on
human choices and the already-required implementation gates. R05's research rules
are also reasonable, but two concrete transport/view bindings remain open against
the current QD contract. This is not rejection for merely lacking code. R06 remains
a future finite acceptance gate, with no measured feasibility claim.

## Allocation and frozen evidence

Task `QF-QD-009-R3-ENGINEERING-REVIEW-R2`; dispatch
`QF-DISPATCH-20261028-QD009-R2-REVIEW-1`.
QD branch `codex/qd-cache-safety`, worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, clean base
`9c6d18559e35377d45f0bfc951ab4cbce20cc202`.
Only this new report is editable/committed. Result is its containing commit;
resolve using `git log -1 --format='%H' -- docs/agent-reports/qd/QF-QD-009-replay-engineering-review-r2.md`.

QR target is exactly `5dc72325580259ee8d578625f0ee33d0d13eec73`, parent
`4d4e5304be7646e0a4520f4ec8512a7890f847a4`. Git scope is exactly its two
proposals plus its new r2 report. All were read from Git objects, not moving files.

| Exact object | Bytes / SHA256 |
| --- | --- |
| QR `research/qr009/replay-protocol-proposal.md` at5dc7232 | 52191 / `f7f42d0efe27427318dbe67d1feb4a246652a92db5eb1328936d0bae65a46ae2` |
| QR `research/qr009/replay-spec-proposal.json` at5dc7232 | 52065 / `77662b551963b7d09b429acdc17881bef854ea34df46e0dde05a5727f28d422e` |
| QR `docs/agent-reports/qr/QF-QR-009-replay-design-r2.md` at5dc7232 | 11139 / `a095b9d541630625d16b1a618b42de7ef7908d51e16f67e4bf54605f3453dfff` |
| Original440-line QD report at89cf347482c8121a4e3da559c6fb639a30788d6f | `8ca4301e21aa599f97fde432695a5b40bfbcb8a58e03751f089430e2d3325e3e` |
| QD `docs/interface-requests/qd-qf009-streaming-ledger.md` at9c6d185 | `d3adb32230ceb698d7a9d5372b412471586ec9341a93176a720110811fec927a` |

The old report and new schema2/profile-r2 proposal remain unchanged. Reading the
latter for compatibility does not independently accept QD's own contract or
infer QR acceptance of it. No part of QR's later moving review was consulted.
All14 native source hashes in the frozen JSON match current source bytes.

## R01–R06 dispositions

| Item | Design disposition | Exact evidence / remaining boundary |
| --- | --- | --- |
| R01 | ACCEPT_DESIGN_WITH_PENDING_EXECUTION_GATES | Protocol§5.1–5.3,§8; JSON native_feedback/numeric_projection/FB01–12. The false exact-native-net claim is withdrawn. Actual wrapper/state/atomicity tests remain unexecuted. |
| R02 | ACCEPT_DESIGN_WITH_PENDING_EXECUTION_GATES | Protocol§3 lines145–183,§8; JSON execution.feature_clock_binding/partial_entry_sizing/submission_validation/fill_validation. Exact delayed/partial/Decimal bindings are now stated; native parity remains a gate. |
| R03 | ACCEPT_DESIGN_WITH_PENDING_EXECUTION_GATES | Protocol§2,§5 tail; JSON account/evidence_tail. Original-clock context and active financial calendar are separated; cutoff expiry/lifecycle is compatible with QD§3.1–3.2 in design. |
| R04 | ACCEPT_DESIGN_WITH_PENDING_EXECUTION_GATES | Protocol§4; JSON reservations/scheduler. Private own-release, whole-order-before-K, atomic state and old-fill/new-signal priority are explicit. Actual transition acceptance remains pending. |
| R05 | OPEN / REVISE_INTERFACE_ALIGNMENT | Protocol§7–7.1; JSON source_consumer_bindings/query_plan. Query clock/unknown/identity intent is acceptable, but N1/N2 below prevent claiming complete carriage by QD9c6d185. |
| R06 | ACCEPT_DESIGN_WITH_PENDING_EXECUTION_GATES | Protocol§6, JSON resource_proposal. Original ceilings preserved; record metric stated; later S13/scaling/headroom remain explicitly unassigned. No new scenario/cap/attempt required by this review. |

### R01: exact D/N and actual S are correctly separated

The new rule delivers exact p_j projected once, retains exact D=sum delivered
p_j, and separately records actual native session_pnl bits S and the ordered
binary64 recurrence. For complete settled N, Delta=N-D projects normally;
predicted R=fl64(S+float(Delta)) must be finite, within the fixed conversion/error
bound and have exact sign3(R)=sign3(N), including zero. It is not a correction
chosen to cancel S. A failing guard stops before completion/publication and retains
the failed path. That resolves the original zero-net counterexample at design level.

Native `src/execution_timing.py:182–196` confirms why pre-call evidence is needed:
it adds PnL, branches on negative session_pnl, then resets session/entry/best_close.
The r2 full post-state check preserves unrelated last_bar/weak_count and existing
blocked_side/rearm_price for zero/positive net; no invented positive-net clear.
The saved close feature/plan/direction remains bound to the same episode/prefix.
Later revisions update current financial evidence without replaying old feedback.

`src/strategy_execution.py:91–96` skips calls when timing is disabled or feature
missing. r2 distinguishes disabled BTC (no fictitious state/delivery) from enabled
missing feature (binding error), while retaining the account's finality gate.
It correctly does not bypass sign checking when rearm_after_loss=False: native
record_fill still writes loss-block fields; decide consumes that flag later.

Future evidence is actual pinned-wrapper FB01–12, bit-preserving public dump/
restore, recurrence/full-state/exact-once checks and candidate publication/recovery.
The proposed adapter error reasons still need an explicit mapping to allowed
kernel errors and a closed failure-capsule/audit binding; none is silently added
to QD's closed ErrorCode registry here. This is an acknowledged native registration
dependency, not a newly discovered numeric contradiction. QR's22 literal and18
structural checks are reported design evidence, not native integration PASS and
were not rerun by this review.

### R02: explicit delayed feature, ratio lifecycle and exact ticket predicates

Intent at d uses d-H's closed feature; a fill at f uses f-H's closed timing feature
with the original intent plan/scope, not a rerun signal or resized quantity. Final
natural close saves that fill feature/plan for delayed completion. The08:00 intent
filled09:00 now sets last_fill_bar=08:00. Native trailing needs bar>last_fill_bar
(`execution_timing.py:137–143`), so the09:00 decision cannot use the pre-entry bar
to update trailing. r2 correctly preserves adverse/weak exits, which precede the
same-bar suppression (`:144–155`); it does not promise all same-tick exits vanish.

`position_sizing.py:94–122` supports the chosen public calls: bind the original
model target to actual executed entry notional, retain ratio through partial exits,
and clear with model_current(symbol,0,0) at physical flat. It avoids the original
full-ticket-versus-partial notional error without writing ratios by hand.

The local Decimal50 context now freezes rounding, exponent range, traps and flag
reset, restoring the caller afterwards. This controls the ambient context used by
`entry_ticket`'s Decimal(str(float)) division (`position_sizing.py:78`); it does
not make source arithmetic exact. Separate exact floor/min/max/tier/budget checks
remain mandatory. Submission uses unrounded D_sub*(1+g), matching native tier
intent (`:58–70`). Fill validation freezes q and uses
max(D_sub,q*m*open)*(1+g), with the explicit whole-q cash formula. This is a stated
conservative U2 simulation predicate, not a second native ticket call or historical
tier fact. Slippage is embedded once in the actual fill price and actual-notional
binding. No numerical boundary or quantity is silently relaxed.

Current QD typed intent/payload/state, order-status, live-lot, financial-change
and owner/peer transport can carry these causal values and immutable references.
The actual native field schemas, owner feedback slot arrangement, runtime/codec
identities and independent threshold/parity tests remain unregistered. They must
meet the frozen packet/state limits, rather than assume a state hash proves
completeness. No actual native callback or sizing transition was executed here.

### R03: original-clock context and no new cutoff financial origin

Protocol§2/JSON account now use2023 only as context/no-active-account evidence;
the financial expected calendar begins2024. QD§3.1 admits the declared complete
pre-initial prefix once, with original clocks/receipt/cursors, equality as a normal
first release and no FinancialBody replay. This resolves the former literal
out-of-range2023 snapshot requirement without increasing the financial window.

At cutoff, predeclared Reserves expire by equality; lifecycle updates order/adapter
state with no new decision/order/Fill/Reserves/Valuation origin or backdated release.
QD§3.2 supports this and disables new market selectors in the tail. Tail views use
true age/expiry, can have unknown U/E/budget, preserve open lots, and may settle
old scoped evidence without a current MARK query. Flat U0 is an inventory identity;
expired reserves still make budget null. Complete flat episode readiness need not
wait for a new mark when all its own scoped claims/cash/assertions are complete.

The2h length and dates remain U3 choices. Actual first-slot native preparation,
expiry equality, tail views/finality, complete calendars and interrupted/fold
continuation still need their declared finite gates. This report does not mark
them passed or extend permissible tail economics.

### R04: private comparison and atomic transition, with explicit phase priority

r2 now binds the own reservation ID, frozen quantity, pre-funds, whole-ticket
check, K, fill/fee/Posting/cancel, native feedback/ratio and post-state reserves
together. C100/pending-own80 means compare against100, not20; it does not publish
an intermediate unreserved account or release another reservation. Only a passing
full request may be partially filled by capacity. K0/missing/rejected sources
produce no zero Fill/fee and one terminal cancellation/release. Executed fee L is
distinct from future fee reserves; no second slippage expense is introduced.

Phase4 old eligible fills precede phase5 new signals. An opposing phase5 signal
can cancel a still-pending stress-latency order but cannot erase that phase4 fill.
Reversal remains close-first/later decision/feedback gate. QD staged complete-tick
publication and order/decision/state projections support this requirement in
principle. Current before-view funds/reserves, private revalidation, multi-slot
feedback ownership and final post-state values must be bound and checked by the
future registered execution contract; the result is not validated merely because
the document lists its atomic group. A23/A26/A34 and partial/reversal/failure tests
remain the existing implementation gates, not new market experiments.

## R05: two finite cross-contract revisions remain

The r2 research direction is accepted: independent complete-prefix/latest-eligible
query proof, fixed H/H60/S closure, retained UNKNOWN diagnostics, original a versus
consumer q, stable funding semantic tuple without file hashes/row numbers and
actual-query-role subset checks. QR008 raw acceptance is still insufficient.
There are69819 maximum times per asset/clock and279276 overall; no supports/hit
rates were evaluated. No new query or role is requested by this review.

### N1 — wire normalization is not yet the same closed Fact schema

**Exact locations:** QR protocol§7.1 lines548–555, JSON
source_consumer_bindings.exec_open.cells; QD9c6d185§3.2 lines368–369.
QR's `qr009.exec-open-fact-v1` calls itself a Fact and has only an open_price Cell,
placing open_us in economic_at/header. QD's execution_open requires exactly both
open_us:T and open_price:D+ Cells, with the former equal to economic_at. Direct
registration of that QR one-cell Fact therefore cannot satisfy the QD shape.
For an arbitrary f, header economic_at=f plus {open_price:100} is a minimal example;
the missing required Cell is open_us. No market data or runtime test is needed.

**Finite fix:** freeze a versioned deterministic source-DTO-to-QD-Fact binding that
copies the original header time into the required time Cell and checks equality,
or explicitly align the two authors' closed shape proposals. Name/hash the two
schemas and converter; do not silently add a field to an object still advertised
as the same closed schema. This adds no new information, scenario or human choice.
Full OHLCV close availability and no fill-hour H/L/C/V access stay unchanged.

The same binding must explicitly map QR's consumer names/status/reasons/role set
to QD's six mark_selection Cells/header and separate scheduler/audit metadata.
For example query_us/source_us/mark_price are not literally QD's
query_at_us/source_at_us/selected_price. Deterministic renaming is feasible, but
UNKNOWN reason preservation and SUPPORTED/UNKNOWN conversion must be specified,
not accepted by dictionary similarity or arbitrary extra Cells. This is a finite
registration/author alignment task, not a request to redesign the research model.

### N2 — UNKNOWN Fact transport alone does not specify authoritative view override

**Exact locations:** QR protocol§7.1 lines574–583 and JSON
source_consumer_bindings.mark.unknown_status_transport; QD9c6d185§3.2
mark_selection and§6 Balance/age rules; retained r3
`research/qd007/event_ledger.py:490–493,724–756`.

QD's amendment can transport unknown mark_selection Cells to an adapter. It does
not yet give a closed normative binding from a required query's UNKNOWN status to
authoritative as_known U/E/reserves/budget, or define how later qualified status
supersedes it. Its FinancialBody/Balance/component definitions and age rules keep
the r3 financial mechanism: choose retained Valuation by source valuation_at,
evaluate age, and derive financial balances. A Fact or arbitrary AdapterState is
not specified as a new financial-view authority. Blocking only allow_increase in
the adapter is necessary but does not fulfill the stronger r2 authoritative-view
requirement. This is a gap in the QD contract, correctly left explicit by QR r2;
QR is not asked to invent a private kernel field.

**Minimal relative-clock example, no data scan:** let M be a month-start hour in
the active account window. At q1=M, a qualified source S=M-60s is available at M
under primary delay60s; the needed source interval is entirely in the prior month.
At q2=M+60s (an allowed H60 query), independently proving latest eligibility needs
the interval through source M. If that new month's required raw interval is absent,
the query is UNKNOWN_MISSING_MONTH even though the old point still satisfies
source age120s and available age60s at equality. A held position's old known
Valuation therefore remains fresh under the existing financial selection/age
rules. Merely adding an unknown Fact does not explicitly make held U null. Other
unknown claims/reserves may independently null E/budget, but do not fix that U
representation or the query qualification/valuation reference binding. This
counterexample does not assume an actually positive budget during a funding wait.

The prohibited null-Valuation shortcut is also genuinely unsafe. In a separate
primary-gap fixture, query q=H has no eligible point; recording null Valuation at
source-time H as a query sentinel then conflicts with a real point of source H
that becomes eligible at H+60s: same source valuation time/different price violates
AMBIGUOUS_VALUATION. Under other timing the newer sentinel can shadow a legitimate
older source. QR correctly forbids that shortcut. Neither a fake source time nor
backdating is an acceptable substitute for query-scoped status.

**Finite fix / owner:** QD must explicitly define the query-status-to-authoritative-
view binding in a separately allocated versioned contract amendment, reviewed by
QR, or demonstrate an already-closed typed mapping that provides identical
semantics. Specify required clock/role, query/knowledge cutoff and historical
as-known behavior; UNKNOWN must mask the appropriate required components and
later SUPPORTED must restore them without changing earlier views. Preserve flat
U0 identity and tail no-query semantics. No change to old r3, research numbers or
user questions follows. The existing deferred query/native acceptance must check
the unknown/fresh-old-view case and recovery; this does not enlarge the frozen
initial90 cases/118 fixtures or budgets in this report.

Until N1/N2 are resolved, complete R3 registration remains BLOCKED. Initial ledger
work may still be separately considered under its own independently reviewed
contract scope; this report does not self-approve that contract or block unrelated
infrastructure merely because native/query implementation is absent.

## R06 and remaining execution gates

All36 prior numeric leaves of resource_proposal match base4d4e530. Initial ledger
remains8 measured attempts at N512/2048/8192/32768, twice each;60s each/480s total,
two functional suites120s each ->720s; RSS256MiB/cache8MiB/new output2304MiB.
QD9c6d185 proposes the finite90-case/118-fixture initial manifest, with S13
NOT_EXECUTED/BLOCKED_NATIVE_PORT and QR checking eight saved producer artifacts,
not secretly rerunning eight benchmarks. It still requires independent review.

Later proposed query register is2+2 attempts,600s/RSS512MiB/disk256MiB each.
R3 retains18 planned paths+6 diagnostics=24 started attempts;900s wall/600s CPU,
RSS1024MiB/disk512MiB/500000 logical records/256 checkpoints per path. Whole later
stage remains14400s wall/CPU,14336MiB disk, first limit wins. The new explicit
logical-record metric counts admitted bodies/Generated/noops/decisions/typed
lifecycle/trace/receipts, with physical/index/checkpoint/byte counters separate.
Exact mapping to the eventual registered transport/artifacts must be frozen before
execution, rather than redefined after a result. No additional count or cap is
set here. Aggregate ceilings may stop before all18 paths finish; this is disclosed.

The finite actual-native S13 register, scaling/parity evidence and aggregate
headroom remain explicitly unassigned. Those are existing run gates, not a reason
to call design evidence a benchmark PASS or demand a new market search. No new
precondition, model family, scenario, successful-path rerun or resource increase
is introduced. Actual schema/code/checker/config/runtime bindings, independent
complete-prefix query qualification, full native restart/causality and A23/A26/A34
remain due. R4 labels/finality/purge/dependence/sufficiency and R5 fixed prospective
features/models/evaluation plan remain missing. Training is NOT_READY; fresh user
confirmation is still required before any model/scaler/calibrator fit.

## Human choices remain exactly three, not approved here

- **U1:** hourly retrospective open-only execution,1s/3601s latency,5/10bps adverse
  price, prior-hour capacity0.001/0.0001, one opportunity/cancel and reserve floor.
- **U2:** independent10000USDT accounts, C-based equity, synthetic tiers, stated
  reserves/unknown gates and delayed settled-finality feedback/reentry; now also
  explicitly disclosed fill-time feature binding and numeric incompatibility stop.
- **U3:**2023 warmup/2024 account start, conservative native carry sampling with
  28800s equivalent unit,2h evidence-only tail, eight scenarios/eighteen paths and
  bounded attempts/validation. These do not grant execution permission.

All remain PROPOSED. No question was sent and no answer inferred. Already approved
source segmentation, fees, MARK/funding clocks, instrument multipliers and economic
data window are unchanged. N1/N2 and numeric/type details are engineering work,
not a fourth human choice. Coordinator can present the three concrete research
packages after this technical disposition; unresolved internal bindings cannot
be represented as implementation-ready or approved by the user's scenario choice.

## Checks performed, limits and handoff

- Verified exact commit parent/three-path scope and three QR object hashes/bytes;
  reread original R01–R06 evidence and current frozen contract, checked their
  hashes, and compared all14 native source pins. No moving QR file was read.
- Parsed frozen JSON and compared approved_inputs, strategy_binding, scenarios
  and authorization objects exactly with4d4e530: unchanged. Compared all36 prior
  numeric resource leaves: unchanged. Reviewed MD/JSON bindings against the pinned
  wrapper/TimingState/sizing and retained r3 valuation selection source.
- Small stdlib checks were limited to structural comparisons and N2's relative
  clock inequalities: q2-S=120s, q2-a=60s, eligible-source upper bound moves from
  M-60s to M. This is a source/literal counterexample, not observed market coverage
  or an executed native integration test. QR's22/18 checks were not repeated.
- Modified only this report. No implementation/tests/benchmark/native replay,
  market-row scan/MARK query, experiment, label export, fit, application/engine,
  credentials, dependency change, merge/cherry-pick/push or service operation.
- Main preservation witnesses before/after: HEAD
  cae0d2395adf2cd3905e41cb1c16748c8247c32c; staged diff SHA
  c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce;
  unstaged diff SHA35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d;
  full porcelain/untracked status SHA
  2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649.
  Report scope/whitespace and those witnesses are checked before committing.
- Limit: proposed controlled native/query schemas, error/failure-capsule mapping,
  runtime validators, immutable fixture bytes and execution evidence do not exist
  merely because their inventories are specified. This report offers design
  acceptance only where stated, and does not certify either author's code.
- Next: coordinator allocates the finite N1 author alignment and N2 QD contract
  binding, then obtains exact independent review. Keep R01–R04 closed at design
  level unless that work reveals a specific contradiction. Stop after this report's
  one-file commit; no automatic next task or cross-chat reply is authorized.
