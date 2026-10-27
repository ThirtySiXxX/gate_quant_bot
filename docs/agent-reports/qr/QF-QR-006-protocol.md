# QF-QR-006 protocol review

Date 2026-10-28 Australia/Melbourne. Role QR. Status READY_FOR_QD_REVIEW.
Task QF-QR-006-PROTOCOL; dispatch QF-DISPATCH-20261028-QR006-PROTOCOL-1.
Worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`,
branch `codex/qr-validation-baseline`, base
`96be10c19a7cece6f4e8ba3fb91a8b65d2a90608` initially clean.

Exclusive files: research/qr006/ (Markdown/JSON only),
docs/interface-requests/qr-qf006-execution-cost-label.md and this report.
Parent research protocol hash independently verified:
`f399514d8724d61b4b091b95ea495dbf20f223ec93877457bc78392817d0c276`.

## Completed draft

Verified public official fee/funding/API pages and two dated funding-rule
announcements. Distinguished source record time, nominal snapshot, information
availability and booking. Proposed a named cost-scenario estimand with historical
exact reconstruction separately gated, event cash/claim accounting, late-posting
episode attribution, explicit denominator/known-time maturity, and chronological
evaluation with dependency and precision requirements. Wrote a standalone
interface proposal and stable acceptance matrix; native contracts remain intact.

The 2025 announcement's displayed publication follows its stated effective time;
the 2026 announcement has a pre-effective illustrative date. Both are preserved
as evidence caveats, not silently made into historical knowledge timestamps.
No full 2023-2026 historical rule, exact mark, or user fee claim is established.

## Checks and dependency

Read repository instructions/ownership/current consumers and the original label
auditor. Original source main HEAD/staged-diff fingerprint matches QR005's saved
baseline. Public documentation browsing only; no account/credential access or
market-data download. JSON/reference/arithmetic review is recorded below.
No full regression suite is needed for pure
Markdown/JSON changes, and none is run.

Dependency: QD reviews the exact committed draft, feasibility and future file
scope. QR will resolve concrete review issues and finalize the protocol; that
does not authorize implementation, baseline/label generation or fitting.
This phase stops after protocol review. Training needs fresh human confirmation.

Draft checks completed with the existing read-only project interpreter and Python
standard library: both JSON files parse; 9 unique source IDs, 34 unique sequential
acceptance IDs and their case references/owner/status fields are consistent.
43 independent literal Decimal/arithmetic assertions passed for A01/A02/A04,
A10-A12/A20/A22/A24, including the 1.45 reconciliation, 0.87+0.58 allocation,
floating-loss budget and strict microsecond maturity boundary. These are document
example checks, **not 34 implemented contract tests** or generated market labels.
QD preflight hash and source main HEAD/staged-diff SHA match the frozen baselines.
Implementation tests, market replays, generated market labels and model fits: 0.

Modified files (five, all in the exclusive claim):
`research/qr006/protocol.md`, `research/qr006/evidence.json`,
`research/qr006/acceptance.json`,
`docs/interface-requests/qr-qf006-execution-cost-label.md`, and this role report.
Next step is QD review of this committed draft; stop and await that review.

## QD preflight response and bounded implementation proposal

Read QD preflight at commit `01bc6e798edd200e9553c17702739279f34f0384`;
`research/qd006/implementation-constraints.md` SHA256
`306c1f81d77dd25dcd8a210ab99c3fbc929f12ea85ad8a3ccf578fac361bd505`.
These are QR responses for counterpart review, not a declaration of QD approval.

| QD constraint | Draft response / acceptance |
| --- | --- |
| QD6-C01 | Standalone qf006 namespace and versioned named scenario; dated rules, no native schema edits; A16/A27/A32 |
| QD6-C02 | Distinct clocks, original source seconds plus lossless integer-microsecond transport; explicit 24h conversion; A18/A22/A33 |
| QD6-C03 | Snapshot lot eligibility survives close; exact ties fail closed, both scenario tie policies declared; A07-A10 |
| QD6-C04 | Contracts/base/USDT/fraction units, mark provenance and historical multiplier evidence; A05/A15-A17/A30-A31 |
| QD6-C05 | Per-fill signed fee, partial/no fill and reversal allocation; identical duplicate no-op, conflicting payload quarantined; A01-A04/A10/A13 |
| QD6-C06 | QD pending P = QR A-L; booked W = QR C, same equity identity; append corrections, no deletion on close; A11-A14 |
| QD6-C07 | Final accounting separated from causal knowledge; unknown amount stays null; A18-A19/A32 |
| QD6-C08 | Synthetic budget C-L+min(U,0)-reserves; unknown/stale U blocks new risk; no Gate-margin/default-change claim; A20 |
| QD6-C09 | Primary cash-settled target; natural exit differs from known-time/finality; strict purge/24h maturity; A21-A23/A29 |
| QD6-C10 | Event eligibility, fixed snapshot allocation, both signs and zero-event result; A05-A07/A10/A12 |
| QD6-C11 | Future full-state replay required for sizing/timing/counterfactuals; frozen probe and runtime remain unchanged; A26/A34 |
| QD6-C12 | Exact Decimal ledger sums, rational numerator/denominator and explicit target rounding; fresh artifacts/hashes/statuses; independent literals, not production-derived oracle |

Recommend QD's bounded sequence: first, QD `research/qd007/event_ledger.py`
and `tests/test_qd_event_ledger.py`; QR independent checker
`research/qr007/validate_event_ledger.py` and
`tests/qr_research/test_qr007_ledger.py`. Then separately allocate evidence
coverage, QD `research/qd008/native_adapter.py` with
`tests/test_qd_event_replay.py`, and QR target construction. Each has its own
role report and fresh ignored results. These are proposed future paths only.
Start with synthetic ledger acceptance, then resolve data coverage, then approve
full-state replay and label generation separately. No Python file is created now.

Coordinator's four draft-close observations are incorporated: unrealized losses
and unknown U in the budget; identical versus conflicting duplicates; explicit
seconds-to-microseconds embargo conversion; distinct partial-opening and
partial-reduction snapshot trajectories. A09/A20/A22 preserve their stable IDs.

## Limitations

Current public documents cannot prove historical arrival, exact simultaneous
snapshot sequence, complete funding calendars, settlement mark or private cash
booking. These remain explicit data/assumption gates in the proposal. Candidate
constants, latency, budget and prospective final-test dates must be frozen before
any future experiment; no statistical performance or trading edge is reported.
