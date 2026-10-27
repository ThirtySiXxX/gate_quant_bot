# QF-QD-006-REVIEW: execution, fees and labels preflight

Date: 2026-10-28 Australia/Melbourne.
Status: **PREFLIGHT_COMPLETE_AWAITING_EXACT_QR_SPEC**.
Dispatch: `QF-DISPATCH-20261028-QD006-PREFLIGHT-1`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`; base:
`ba1a507d8b265f29f355a015d5f189178361e611` (clean before work).

## Scope and deliverable

Current exclusive claims: Markdown/JSON design in `research/qd006/` and this
report. Added `research/qd006/implementation-constraints.md`, covering twelve
numbered constraints, accounting examples, ownership, future path allowlists,
bounded implementation stages and compatibility/rollback. No QR specification
has been approved: its exact committed draft is still pending.
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
