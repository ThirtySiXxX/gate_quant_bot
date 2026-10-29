# QF-QD-006-REVIEW: execution, fees and labels preflight

Date: 2026-10-28 Australia/Melbourne.
Status: **PROTOCOL_DESIGN_ACCEPTED_STOP** (final bounded recheck below).
Protocol/design review accepted; not implementation-tested or data/training-ready.
Dispatch: `QF-DISPATCH-20261028-QD006-PREFLIGHT-1`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`; base:
`ba1a507d8b265f29f355a015d5f189178361e611` (clean before work).

## Scope and original preflight deliverable

Current exclusive claims: Markdown/JSON design in `research/qd006/` and this
report. Added `research/qd006/implementation-constraints.md`, covering twelve
numbered constraints, accounting examples, ownership, future path allowlists,
bounded implementation stages and compatibility/rollback. No QR specification
was approved at preflight; the subsequent exact-draft disposition is recorded below.
Design SHA256:
`306c1f81d77dd25dcd8a210ab99c3fbc929f12ea85ad8a3ccf578fac361bd505`.

Verified the supplied formal protocol file at
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/outputs/QuantFlow-正式研究协议与费用核验.md`
against SHA256 `f399514d8724d61b4b091b95ea495dbf20f223ec93877457bc78392817d0c276`.
Read AGENTS and required architecture/collaboration/interfaces/roadmap/progress/
decisions context. Current review authorization supersedes the supplied document's
older PAUSED description only for this bounded protocol/planning phase.

## Existing consumers and implementation gaps

| Current source anchor | Already supported | Gap / proposed boundary |
| --- | --- | --- |
| `src/strategy_execution.py:28,73,105` | Shared signal-to-plan, fixed-ticket budget checks, close/reduce/reversal order planning; no fill I/O | Preserve policy. A later research execution adapter must supply causal ledger budgets and confirmed fill events; proposals are not fills. |
| `src/costs.py:13,17,21,34,47` | Fee multiplication, signed funding cost, adverse bps fill-price scenario, approximate round-trip filter | Pure arithmetic does not establish effective tier, fill role, precision, snapshot eligibility or posting identity. Keep approximation named. |
| `src/config.py:192-216`; `src/backtest_runner.py:290-307` | Config/account/current-contract Taker selection and current interval/multiplier passed into native replay | Not point-in-time history; the existing online controller is not the entry point for offline protocol implementation. No account lookup authorized. |
| `src/backtest.py:361-389` | Decision/open trade price, bar-close trade-price MTM, causal as-of rate and elapsed-time funding accrual | `mark_price_now` is a variable name for trade close, not funding mark data. Native proration is not settlement-event accounting. |
| `src/backtest.py:195-208,456-506` | Simulated fill fees, averaged entry, partial/full realized PnL, proportional accumulated costs | Costs reside in current position; no independent payable/receivable survives deletion. New accounting must retain event obligations after flattening. |
| `src/backtest.py:536-564` | Terminal simulated close and recorded fees | Terminal execution time and trade close_time use different boundaries; terminal action is not a natural exit or automatically mature label. |
| `src/systematic_engine.py:50-88`; `src/exchange_paper.py:234-249` | Local proportional funding statistics; paper method can debit current marked position | Neither establishes historical eligibility/posting events. Do not start the engine or use the paper adapter as an economic oracle. |
| `src/exchange_gate.py:188-199,233-241` | Runtime account-fee capability and current contract/mark snapshots | Capability is not authorization or historical evidence. No credential/account calls were made. |
| `src/crypto_ml.py:59-82`; `src/ml_training.py:6-42` | Gap-aware fixed-horizon price classes, constant round-trip threshold, chronological label-end check; fitting code exists | No strategy-cycle event cashflows, late funding maturity or complete overlap/embargo protocol. Keep legacy feature/model path opt-in and unchanged; do not call training. |
| `research/qr003/replay_probe.py:105-188` | Frozen native-loop observer, plan/budget snapshots and stateful skip support | Its returned original result remains approximate accounting. Cannot reinterpret it as the new event ledger or repair strategy paths by deleting old trades. |

Source fingerprints at this preflight:

| File | SHA256 |
| --- | --- |
| `src/backtest.py` | `9183091e85c4354720118c53f0d97b72022f018afa03d9e9479f4929f5a8540c` |
| `src/costs.py` | `356d3f5a29df9a64caeb40948fe4408dad81982fa5255cba051deb578b70621e` |
| `src/strategy_execution.py` | `e1eaa17ea1292c7e906d4634b274fe72f2a415dfa409054674a33c22b9b1f5bb` |
| `src/crypto_ml.py` | `63d0d9569cb261c83867b18cde03f9f74c7b54626172eeb5bb36eac09c19a7f6` |
| `research/qr003/replay_probe.py` | `4a0e520fa7b0a98565435aec07936bd4425592850a6e2e64b2116acd7d1d45aa` |

## Mechanism findings and acceptance direction

Verified public official documentation only: snapshot versus asynchronous funding
posting, mark-based USDT valuation, fill-role-dependent fees and a dated public
Taker scenario. Links and uncertainty qualifications are in the design note.
Current documentation alone does not prove historical application. No bulk market
data, mark data, private endpoints or personal rates were accessed.

Review the exact QR draft against QD6-C01..C12. The acceptance matrix must include:
known/unknown same-time ordering; close before late posting; partial close and
reversal attribution; no-snapshot interval; all funding signs; per-fill fees and
duplicate/conflicting IDs; cash/pending/equity conservation; information arriving
after a decision; missing mark/rule/schedule; immutable corrections; and censored
or not-yet-mature outcomes. Hand-derived fixture in the design gives full-cycle
net 1.45 USDT, including a 0.05 payable posted after flattening. It is synthetic,
not a market label or proof of Gate historical PnL.

The main implementation constraint is two views of time: ex-post economic
attribution may attach a final amount to an earlier snapshot, while strategy
decisions can use only information available by that decision. Unknown amount
is not zero. Costs must eventually feed stateful replay, rather than changing
only its final report. Proposed first implementation is a pure synthetic event
ledger; actual-data coverage, replay and labels remain separately bounded stages.

## Verification and preservation

Protocol hash verified; targeted source inspected read-only; analytic fixture
arithmetic and design structure checked without importing application modules.
Checks passed: twelve unique ordered QD6-C IDs, design-only file inventory,
pending-review status, exact Decimal fee/pending/equity/partial-allocation
assertions, and `git diff --check`.
No runtime/tests/config/shared journals/QR files or prior evidence were edited.
No full regression suite is needed or run for this documentation-only stage.
No collection, replay, label generation, scaler/model fit, scheduling, app/engine
operation, Windows/NAS action, integration, cherry-pick, push or merge occurred.

Original main remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; source staged-diff
SHA256 `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce` and index-byte
SHA256 `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80` match prior
preservation checks. Existing staged deletions and other user work remain intact.

## Dependency and stop boundary

Await the coordinator's exact QR006 draft commit and hashes, then map every
protocol ID to ACCEPT / REVISE / BLOCKED with a concrete acceptance case and
bounded implementation consequence. This preflight makes no overall protocol
acceptance finding. Historical economic-label readiness remains unresolved.
The final protocol/plan review ends with a report; implementation, data acquisition,
actual replay/labels and training require their respective later authorizations.

## Initial exact QR draft review: REVISE (history; superseded below)

Continuation dispatch: `QF-DISPATCH-20261028-QD006-EXACT-REVIEW-1`, with schema
clarifications requested by `QF-CONTROL-20261028-QD006-SCHEMA-POINTS-1`.
QD review parent: `01bc6e798edd200e9553c17702739279f34f0384`.
Reviewed QR commit: `2c3846c53443307b410a647ba0efbed078884d8b` relative to
`96be10c19a7cece6f4e8ba3fb91a8b65d2a90608`. All five committed bytes matched
the read-only QR working files and the coordinator's exact hashes:

| QR file | SHA256 |
| --- | --- |
| `research/qr006/protocol.md` | `f4434a259ce9974e36fedc32e34aaa910b84553e496c7840b112276baf76cbe8` |
| `research/qr006/acceptance.json` | `8c3038dbd613d1d84c9e6c01873fbfee5a125ce2c5a044d4d188ab59897ad510` |
| `research/qr006/evidence.json` | `afd3468133ab45eb83fc727d959054389e1d31bdbeb49d2fa27f040f594aa00a` |
| `docs/interface-requests/qr-qf006-execution-cost-label.md` | `231f97a5a796eceaa6ddcf18d4f770d0f5ebbf842ff5ece1ad384e9b30282bbc` |
| `docs/agent-reports/qr/QF-QR-006-protocol.md` | `68b6ec921c3d6a69f80db72bf4ae207a3525096944ba9674ce10c93de9776d00` |

Added `research/qd006/implementation-plan.md` and `research/qd006/review.json`.
Exact SHA256 identities:

- Implementation plan: `ed84ef1276b78a0aebe2fb465942fba46cf77676dae9c55d7745f5f9f6111337`.
- Review JSON: `9a0a29dc95b1706c0ea037f16c9903bc1ee4c7081467360674be79ca52cf8695`.

The JSON gives every QD6-C01..C12 and QF006-A01..A34 an explicit ACCEPT/REVISE
disposition: **30 acceptance criteria ACCEPT, 4 REVISE** (A02, A13, A14, A21).
An ACCEPT means the specified future criterion is suitable; none of the 34
contract tests has been implemented or executed in this review. Overall protocol
freeze remains **REVISE**, not approved implementation.

| Required correction | Concrete reason / smallest next change |
| --- | --- |
| QD006-R1 | Separate cumulative obligation revisions from independently identified postings. A14's -0.05 correction cannot debit cash merely when a rate revision is learned. Extend A13/A14 with two revisions before posting, posting redelivery/conflict, credit and fee-correction variants. |
| QD006-R2 | Strict interface enums conflict with A02 `role_basis=synthetic` and A21 `immature`. Use the permitted role basis and an explicitly represented maturity state, keeping both stable IDs. |
| QD006-R3 | Completeness coverage time and its availability are not explicitly distinct. Add a typed scope/rule/revision/known-time assertion so a later watermark cannot mature an earlier label; extend A21, keep A22's strict microsecond inequalities. |

Counterexample for R1: booked -0.05 leaves C=999.95. Learning total=-0.10 makes
L=0.05 without changing C; learning total=-0.08 before another posting leaves
L=0.03, C unchanged. Posting -0.03 then leaves C=999.92, L=0. Revision discovery
must not masquerade as a booking or repeatedly charge the whole revised total.
The plan contains explicit counterexamples and acceptance consequences for all
three requests; no wider research or additional data is needed to resolve them.

Accepted design directions: snapshot-based eligibility, mark/units separation,
late obligations surviving close, FIFO lots, gross-entry denominator including
adds, causal fresh-loss-aware synthetic budget, strict 24h maturity in microseconds,
cross-asset purge, stateful counterfactual replay and native version isolation.
As-known cash/budget must remain separate from restated economic attribution.
The budget is a new synthetic scenario state policy, not unchanged native replay
or actual available exchange margin. Deferred data/run parameters remain explicit.

Ownership proposal resolves the QR wording ambiguity: QD alone implements the
future EpisodeLabel producer/exporter (`research/qd009/episode_export.py`);
QR alone owns label-policy specification and independent validator under
`research/qr009/`. QR's "target construction" describes semantic responsibility,
not a concurrent edit to QD's exporter. QR must confirm the proposed allocation.
The plan lists exact future editor/reviewer/test/report paths and the bounded
order: synthetic ledger -> evidence coverage -> separately approved full-state
replay -> separately approved target construction. These are proposals, not
current file claims or permission to start those stages.

Verified the two additional official funding-rule announcements: S06 states
2025-08-29 10:00 UTC effectiveness but displays later 11:30 publication; S07
states 2026-04-13 01:00 UTC effectiveness despite an earlier illustrative date.
These support QR's distinction between effective rules and public knowledge;
neither establishes actual BTC/ETH transitions or a complete historical calendar.
[S06](https://www.gate.com/announcements/article/46849),
[S07](https://www.gate.com/announcements/article/50645).
Earlier preflight checks cover the fee/funding/API sources. Statistical-method
references remain QR's methodology responsibility; QD has not computed DSR/PBO
or independently revalidated those papers in this continuation.

Verification in this continuation is document-only: exact committed/file hashes,
JSON ID/reference/ownership consistency, **58 independent literal Decimal
assertions**, strict microsecond boundary/finality-clock examples, enum
counterexamples, and Git whitespace/preservation checks. All passed, using only
the existing interpreter and standard library, without importing application
modules. The original preflight design hash remains unchanged. Source main HEAD,
staged-diff SHA and index-byte SHA again match the preservation values above.
No new implementation/tests, model/scaler fitting, market labels, replay, data
download, runtime/shared-schema edit or source-main operation occurred.
Next action: QR corrects the three specific issues and returns exact new draft
identities for re-review. Stop here; no automatic freeze, implementation or run.

## Final exact revision recheck: ACCEPT and stop

Dispatch: `QF-DISPATCH-20261028-QD006-FINAL-RECHECK-1`.
QD parent: `611cb7419e676bde8cb0b2e64968f3a81bd42164`.
Reviewed QR revision: `c7e9a2492247fa31e216035f87e8bb20cca6e6ad`, parent
`2c3846c53443307b410a647ba0efbed078884d8b`, protocol `qf006-proposal-r2`.

**ACCEPT — protocol/design review accepted; not implementation-tested or
data/training-ready.** R1/R2/R3 are resolved, with no material correction left
outstanding in this bounded review. All **34 acceptance IDs and 12 QD constraint
IDs ACCEPT as design**. The initial REVISE review, its exact hashes and its
counterexamples above remain historical evidence; the current JSON also retains
the prior review identity and the corrected IDs' earlier dispositions.

All five exact committed/file identities passed:

| QR file | SHA256 |
| --- | --- |
| `research/qr006/protocol.md` | `4957875f25168ea33d630fb63be00a712d86ac049b932bdc11f731e8b980e270` |
| `research/qr006/acceptance.json` | `d75fb7d7274ab2da41c71cd097f27982a3d2a7d103b5c1146d84da2429f9058c` |
| `research/qr006/evidence.json` | `c4fc6fb1cd24ce90f347dff23b8f6c4a86f9a037e9c9e0108a24cea9047c434b` |
| `docs/interface-requests/qr-qf006-execution-cost-label.md` | `d62c42ddc5cbac286e3b4ebf821fd977a693d7c3986ab019942560fa1348a6d8` |
| `docs/agent-reports/qr/QF-QR-006-protocol.md` | `3f5c63ba2b08717a6d44d2dcc5740fc9881e3d6017c1a0a947e15b77162554cc` |

| Closed request | Final finding |
| --- | --- |
| R1 | Cumulative authoritative T and independent posting sum B determine P=T-B; revisions have zero cash delta, available postings move cash and pending once. A13/A14 reconcile two revisions, partial payments, funding sign-change refund and a late fee refund/surcharge after close. Independent source identities and conflict rejection are explicit. Imported posting_revision>1 rejects as UNSUPPORTED_POSTING_RESTATEMENT; genuine later transfers use new evidenced posting IDs. |
| R2 | A02 uses role_basis=scenario. Wire label_status includes immature, with deterministic precedence and null target/known-time rules, distinct from open, invalid and censored. A21 conforms. |
| R3 | Typed completeness assertion separates economic scope, exact obligation/posting revisions, authority/rule, issuance, observer knowledge and consumer availability. The full episode and linked late cash must be covered. Label-known time includes the assertion's availability; only available supersession changes the latest label revision. Prior as-known labels remain immutable. |

Bounded checks passed with the existing interpreter and standard library: **64
independent literal Decimal assertions**, **30 clock/state/contract assertions**,
all five committed/file SHA checks, all stable IDs/references, and Git whitespace
checks. Only A02/A13/A14/A21 bodies changed; the other 30 accepted case bodies and
all nine source summaries match r1 exactly. The new literal checks are an
independent arithmetic/contract review, not execution of an event reducer or
34 implemented acceptance tests. No regression rerun was needed for these
Markdown/JSON changes. No new browsing or market-data requests occurred.

Current QD artifacts:

| File | SHA256 |
| --- | --- |
| `research/qd006/implementation-plan.md` | `199833b1d6d187efe12b153ea10772c123558844b9a9e7b4e9231fb0fb3d5838` |
| `research/qd006/review.json` | `3bedf35faa9195d3dbe523d374358ae53ab546eaed7ae7ec83b0b043111dfc82` |

Only those two files and this report change in this recheck. The original QD
preflight remains byte-identical. QR confirmed the sole-editor path proposal:
QD produces/exports EpisodeLabel, QR defines label semantics and independently
validates it. Exact future paths and stage ordering remain in the updated plan.

Remaining gates are explicit and do not reopen these closed protocol issues:

1. Separate human authorization/coordinator allocation for the minimal synthetic
   event ledger; freeze exact typed serialization, nested record/manifest schemas,
   identity details and deterministic fixtures for counterpart review before code.
2. Implement QD producer tests and independently run QR literal/causal/corruption
   checks. No such implementation or test run exists in this stage.
3. Resolve historical-versus-scenario evidence coverage, mark/rule/snapshot mapping,
   availability and booking/finality assumptions; preregister the complete bounded
   execution/cost/valuation manifest before any actual-data run. Public rate rows
   alone do not establish the needed calendar, valuation or private cash bookings.
4. Obtain separate authorization for full-state replay and market-label generation,
   then independent acceptance. Native runtime/defaults/probes/data remain unchanged.
5. Freeze prospective holdout/effect/precision/model/search decisions and the exact
   training plan; obtain fresh direct human confirmation before any scaler/model fit.

Final source-main HEAD, staged-diff SHA256 and actual index-byte SHA256 again match
the preservation values above. No source staging/edit, runtime/shared-schema
change, implementation/test code, collection, replay, market label, fit, engine/app
operation, integration, cherry-pick, push, merge or scheduling occurred.
**Stop:** protocol review is complete; coordinator finalizes the stage report.
Do not start the proposed implementation or any next task automatically.
