# QF-QR-009 R3 design revision r2

2026-10-28 Australia/Melbourne. **DESIGN_ONLY_PENDING_QD_REVIEW_AND_USER_CHOICES.**
Task QF-QR-009-R3-DESIGN-REVISION; dispatch
`QF-DISPATCH-20261028-QR009-DESIGN-REVISION-1`, continuing exact handoff
`QF-CONTROL-20261028-QR009-EXACT-QD-R01-R06-1`.
QR worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`,
branch `codex/qr-validation-baseline`, clean base
`4d4e5304be7646e0a4520f4ec8512a7890f847a4`.
Result is the commit containing this report; resolve using
`git log -1 --format=%H -- docs/agent-reports/qr/QF-QR-009-replay-design-r2.md`.

## Completed changes and exact scope

Only the two assigned proposals were edited and this role report added:

| File | Final SHA256 / scope |
| --- | --- |
| `research/qr009/replay-protocol-proposal.md` | `f7f42d0efe27427318dbe67d1feb4a246652a92db5eb1328936d0bae65a46ae2`; r2 numerical feedback, delayed callbacks, sizing/context, cutoff, reservation and source-consumer bindings |
| `research/qr009/replay-spec-proposal.json` | `77662b551963b7d09b429acdc17881bef854ea34df46e0dde05a5727f28d422e`; matching machine proposal, issue map, closed binding inventories and prospective acceptance vectors |
| This report | Independent revision evidence; exact bytes identified by its Git object. |

Read exact coordinator counterexample
`qr009-coordinator-feedback-literal-counterexample.json`, SHA
`4d42124402c0af2515458b4f3021453d4c57564590e96f3b0b5612505dfd002b`.
Read the entire440-line QD engineering report at
`89cf347482c8121a4e3da559c6fb639a30788d6f`,
`docs/agent-reports/qd/QF-QD-009-replay-engineering-review.md`, SHA
`8ca4301e21aa599f97fde432695a5b40bfbcb8a58e03751f089430e2d3325e3e`.
Its Git object/workfile matched at handoff, and commit adds only that report.
No moving QD amendment was read or inferred from chat summaries.

Native wrapper/accumulator source and their fourteen frozen pins were checked.
In particular execution_timing SHA41d4593e… and strategy_execution SHAe1eaa17e…
remain unchanged. Prior QR006/007/008, initial QR009 report and streaming review
are frozen. No implementation/test/runner, native module, shared journal or QD
file was edited. No source/main integration or push.

## Finite issue → revision → required acceptance

All rows are **proposed responses for QD review**, not self-approved fixes or
implementation PASS. The old exact-native-net assertion is explicitly withdrawn.

| Issue | r2 revision | Evidence still required |
| --- | --- | --- |
| R01 exact versus float feedback | Keep exact delivered D and settled N separate from actual native S bits. Delta=N-D projects normally; before closed=True require finite bounded approximation and exact negative/zero/positive agreement of fl64(S+float(Delta)) with N. Mismatch stops before publication; no epsilon, residual cancellation, fake cash/Fill or direct state repair. Use scoped wrapper, disabled BTC distinction and unchanged rearm-flag behavior. | FB01–FB12 on actual unchanged native-wrapper path; full pre/post native state, exact-once, unknown/finality, branch mismatch atomic stop and restart. Literal examples alone are insufficient. |
| R02 delayed features/sizing/numeric context | Intent uses d-H feature; fill callback uses latest closed f-H feature and original intent plan. Completion preserves the final-close fill feature. Bind actual executed opening notional through public sizing method; persist ratio, clear publicly at physical flat. Explicit local Decimal50 context; unrounded submission desired tier; separate exact frozen-quantity fill validator, never another ticket calculation. | Actual native delayed trailing/adverse/weak semantics, partial entry/reduction, ratio lifecycle, adjacent quantity/tier/budget thresholds and context isolation. Fill-time feedback choice remains material U2 proposal. |
| R03 warmup/genesis/cutoff | 2023 is original-clock context and no-account/zero-inventory evidence, not financial snapshots. Financial expected calendar begins2024. Predeclare reserve expiry by cutoff; cutoff cancellation is lifecycle state, no new/backdated Reserves/Valuation. Tail does not treat old MARK as fresh; expired reserve budget is null. | QD RV02/context/lifecycle transport and genesis/expiry equality, open/flat tail, no post-cutoff market queries or financial-origin expansion. |
| R04 atomic execution/priority | Own reserve is released only privately for whole-request validation, then K determines liquidity partial. Fill/fee/Posting/cancel/feedback/ratio/reserves form one published transition. Phase5 cannot retrospectively cancel a phase4 fill. | Actual no-fill/partial/reversal/own-reserve/fee/slippage trace, interrupted atomic transition and unchanged native outputs. |
| R05 fact/consumer identity | Closed open-only projection, unchanged full OHLCV availability; source MARK availability a distinct from selection q. Stable funding business tuple excludes file hashes/row number. Reuse qualified valuation or current-q delivery with original source time. Query-scoped UNKNOWN transport/recovery is an explicit QD dependency; never silently use a stale supported view. Schema/plan/roles/cursors/subset checks defined. | Exact amended contract review, independent complete-prefix/latest-eligible query proof, future-hash perturbation, unknown recovery and realized-query subset. Current contract is not assumed to support new bindings. |
| R06 finite resources/feasibility | Initial eight-attempt720s ledger register unchanged; later S13 finite register and aggregate headroom remain unassigned. Define500000 logical-record metric and separate physical/index/checkpoint counts. No assumption all18 paths will finish; require native scaling/parity before markets. | Separately bounded synthetic implementation and native evidence. No benchmark run, additional scenario, extra search or relaxed cap here. |

R02 fill tier predicate is `max(original_unrounded_desired, frozen_quantity*m*open)
*(1+g)`; whole-order budget uses the frozen quantity at actual open. This is an
explicit pending U2 binding, not a historical tier claim or permission to resize.
The completion numeric gate cannot promise all paths complete: incompatibility
is a preserved failed trajectory, not a reason to alter the threshold after results.

## Persistent state and failure boundary

The proposal now inventories ordered delivered amounts/IDs and their float bits,
all TimingState fields/presence, sizing ratios, distinct intent/fill/close features
and clocks, orders/plans, reconstructible financial/lot/claim/reserve state,
feature/query/calendar cursors, finality revisions/postings, completion latch,
prefix identity, stop latch and resource accounting. Actual closed transport schema
and registration remain QD/QR engineering gates, not invented fields accepted by
the frozen kernel. Native public dump/restore must preserve bits and completeness.

Pre-call checking is read-only. Actual native calls later run only on detached,
unpublished candidates; full post-state is validated before atomic publication.
A failure preserves earlier committed cash/postings and publishes none of the
failed tick's candidate state. Post-publication I/O uncertainty uses the reviewed
commit-resolution protocol, not a false rollback. Unknown N continues waiting;
disabled timing is explicitly not applicable rather than silently counted as
delivered. A later refund cannot replay or rewrite prior completion/rearm.

## Checks actually performed

No native/app imports, market observations, MARK queries, replays, benchmarks,
labels, model/scaler/calibrator fits, dependency changes or service operations.

**22 final stdlib literal checks passed**, including:

- Coordinator p=(-0.1,-0.2), N0 -> binary64 residual -2^-54; proposed sign gate
  rejects. QD p=(-0.1,+0.3,-0.2), N0 -> -2^-55; rejects too.
- Representable zero cancellation and ±0.125 targets pass the literal numerical
  gate with disclosed errors. ±2^-60 targets erased to zero reject both signs.
- Unknown N has no projection/completion; altered same-sign state bits fail
  identity; nonfinite state and a deliberately out-of-schema underflow example
  demonstrate rejection predicates, not valid source-data execution.
- Delayed feature clock comparison, partial notional ratio4 versus1, own-reserve
  budget, unrounded/gap tier arithmetic, local Decimal50 context, account-genesis
  and reserve-expiry boundaries, source availability versus consumer q.

Reproducible command (socket connections blocked before other imports):

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python /Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qr009-r2-design-audit-1/literal_checks-2.py
```

Result `literal-result-2.json` in that audit folder,7468bytes, SHA
`b6334a6fdf5c87e5e0662733272272077d1a32511dcb5d9edbc76a4c13bad888`.
The earlier small pass (`literal_checks.py`/`literal-result.json`) is retained;
its trivial self-equality illustration was removed from the final22-count check.
Neither is an actual native state-transition/checkpoint test. FB10–FB12 remain
NOT_EXECUTED, as do every S01–S13 and A23/A26/A34 end-to-end requirement.

**18 final structural/identity checks passed**, using `final_checks.py` and `final-check.json` in
the same audit folder: strict JSON, MD/JSON revision/binding agreement, unchanged
approved-input object/native strategy/scenario matrix/permissions and numerical
resource ceilings against base4d4e530; exact evidence pins, frozen old report/review,
only three assigned paths and source Git preservation. `git diff --check` and
staged scope are checked before the independent commit. These do not establish
engineering acceptance or training readiness.

Source main HEAD/staged/unstaged/index/status fingerprints remain the protected
baseline (cae0d2395adf2cd3905e41cb1c16748c8247c32c; exact SHA witnesses in final audit).
No claim of a new full78-file source/raw-data scan is made.

## User choices, dependencies and next step

At most the original three draft groups remain, for the coordinator to ask after
QD rereview: U1 execution; U2 independent capital/reserves/delayed finality feedback
and fill-feature timing; U3 observation/carry/tail/finite validation. Numerical
transport mechanics are engineering review, not a fourth user question. New
assumptions remain PROPOSED. Approved source/fees/MARK/funding clocks/multipliers
and eight scenarios/eighteen paths are unchanged; all execution/fit permissions
remain false.

QD should rereview this exact r2 and supply its separately authored RV01–RV04 /
R03–R05 transport amendment as an exact commit/hash. No moving contract is accepted
here. Then coordinator consolidates user choices and separately bounded
implementation, native/query/replay, label and information-sufficiency gates.

**Training remains NOT_READY.** Notify the user once R3/R4/R5 gates pass and obtain
fresh human confirmation before any fit. Stop after this design checkpoint;
no automatic implementation, market run, integration, cross-chat reply or model
activation is authorized by it.
