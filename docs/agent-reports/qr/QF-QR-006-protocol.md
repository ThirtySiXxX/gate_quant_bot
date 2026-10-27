# QF-QR-006 protocol review

Date 2026-10-28 Australia/Melbourne. Role QR. Status READY_FOR_QD_RECHECK.
Task QF-QR-006-PROTOCOL; dispatch QF-DISPATCH-20261028-QR006-PROTOCOL-1.
Worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`,
branch `codex/qr-validation-baseline`, base
`96be10c19a7cece6f4e8ba3fb91a8b65d2a90608` initially clean.

Exclusive files: research/qr006/ (Markdown/JSON only),
docs/interface-requests/qr-qf006-execution-cost-label.md and this report.
Parent research protocol hash independently verified:
`f399514d8724d61b4b091b95ea495dbf20f223ec93877457bc78392817d0c276`.

## Initial draft (qf006-proposal-r1)

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
Initial draft commit: `2c3846c53443307b410a647ba0efbed078884d8b`.
It received the exact QD review recorded below; no original acceptance result
is being relabeled as approval of the corrected draft.

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
`tests/test_qd_event_replay.py`, then QD target export with QR semantics and
independent validation under the confirmed future allocation below. Each has its own
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

## Revision 1 response (qf006-proposal-r2)

Dispatch `QF-DISPATCH-20261028-QR006-REVISION-1`, with narrow consistency note
`QF-CONTROL-20261028-QR006-R2-CONSISTENCY-1`. Started from clean QR commit
`2c3846c53443307b410a647ba0efbed078884d8b`. Read and independently verified exact
QD review commit `611cb7419e676bde8cb0b2e64968f3a81bd42164`, parent
`01bc6e798edd200e9553c17702739279f34f0384`:

| QD read-only file | Verified SHA256 |
| --- | --- |
| research/qd006/implementation-plan.md | ed84ef1276b78a0aebe2fb465942fba46cf77676dae9c55d7745f5f9f6111337 |
| research/qd006/review.json | 9a0a29dc95b1706c0ea037f16c9903bc1ee4c7081467360674be79ca52cf8695 |
| docs/agent-reports/qd/QF-QD-006-protocol-review.md | 76b12ab102638cce9fc9a8b75dc0201f7105d84a8a906085ef96906745cfd370 |

That review accepted 30 initial criteria and requested revision of A02/A13/A14/A21.
The following are **QR dispositions implemented in documentation, pending QD
exact recheck**, not claims that QD has accepted the revised protocol.

| Request | Disposition in corrected draft |
| --- | --- |
| QD006-R1 | Stable parent obligation with cumulative T revisions, independent posting IDs and B totals; pending P=T-B, revision cash_delta=0. Supports partial postings and separate signed late fee/funding refunds after close. Immutable posting revision 1 is explicitly bounded; imported-posting restatements >1 fail closed, while actual later cash transfers use new IDs. A13/A14 now specify duplicates/conflicts, successive revisions, split payments, sign change and late fees. |
| QD006-R2 | A02 wire role_basis is scenario. Added explicit immature label enum and allowed state/null combinations. Pending supported outcomes differ from invalid evidence and censored observations, consistently in protocol/interface/A21. |
| QD006-R3 | Typed assertion covers economic-origin interval plus linked cash obligations/postings, with authority/rule, revision refs and separate issue/receipt/consumer availability. A21 covers the natural exit and delayed posting positively; negative scopes omit exit or nonfunding events. Later available assertions set later label-known times; supersession creates a new label revision without rewriting old causal views. A22 strict microseconds and A29 unknown-finality negative are unchanged. |

Confirmed ownership proposal: **QD alone** produces/exports labels at
`research/qd009/episode_export.py`, with `tests/test_qd_episode_export.py` and
QD009 report. QR alone owns `research/qr009/label-policy.md`,
`research/qr009/validate_episode_labels.py`,
`tests/qr_research/test_qr009_labels.py` and QR009 report. No current file claim
is created. The future sequence is synthetic ledger -> evidence coverage ->
full-state replay -> producer and independent label validation, with the QD
plan's separate authorizations. No implementation or actual run is authorized.

The original five-file allowlist is unchanged; evidence.json only advances its
protocol revision link and records no new sources. Only four acceptance case
bodies change; all 34 stable IDs remain. Other runtime, schema, source/main,
previous research and shared journal files remain untouched.

## Corrected-draft verification and stop

Passed document-only checks with the existing interpreter and standard library:
68 independent Decimal assertions for cumulative pending/cash, partial postings,
refund/sign-change and late-fee examples; 26 clock/coverage/state assertions,
including distinct assertion receipt/availability, insufficient exit coverage,
strict 24h microseconds and the unchanged unknown-finality negative case.
Both JSON files parse; all 34 IDs remain unique; exactly A02/A13/A14/A21 changed.
The other 30 accepted case bodies and all nine source summaries equal the initial
committed draft. Git whitespace check passes; modifications are exactly the five
allowed Markdown/JSON files and no untracked implementation files exist.

Original source main HEAD, staged-diff SHA256 and index-byte SHA256 match the
preservation values recorded by QD. No source staging or worktree changes,
new browsing, market-data request, implementation/test code, market replay,
market-label generation, model/scaler fit, runtime edit, merge or push occurred.
These assertions are literal document checks, not implemented acceptance tests.

Corrected non-report content identities (the report itself is identified by the
commit and separately returned SHA256):

| QR file | SHA256 |
| --- | --- |
| research/qr006/protocol.md | 4957875f25168ea33d630fb63be00a712d86ac049b932bdc11f731e8b980e270 |
| research/qr006/evidence.json | c4fc6fb1cd24ce90f347dff23b8f6c4a86f9a037e9c9e0108a24cea9047c434b |
| research/qr006/acceptance.json | d75fb7d7274ab2da41c71cd097f27982a3d2a7d103b5c1146d84da2429f9058c |
| docs/interface-requests/qr-qf006-execution-cost-label.md | d62c42ddc5cbac286e3b4ebf821fd977a693d7c3986ab019942560fa1348a6d8 |

Status READY_FOR_QD_RECHECK. QD must re-review these exact corrected bytes;
no protocol-freeze acceptance is inferred. Stop here. Future implementation,
coverage/run decisions and direct human confirmation before training remain
separate gates; this revision grants none of them.
