# QF-QR-009 independent streaming-contract review

2026-10-28. **REVISE — four bounded contract clarifications before implementation.**
This is not an implementation verdict, benchmark PASS, user scenario approval or
R3 readiness. S01–S13 remain NOT_EXECUTED. No QD file was edited.

Task QF-QR-009-R3-DESIGN; handoff
`QF-CONTROL-20261028-QR009-QD-EXACT-CONTRACT-1` continues Part D of the same task.
Exact target `19cd4c7e461799b9b9a13fef2028902e8dfcd48c`, base
`d90e3684dbfcb54ead9bbfd933b209e71fb42ce5`:
`docs/interface-requests/qd-qf009-streaming-ledger.md`,998 lines,
SHA256 `36a7b157cdba45692b6737ba465d7b2bf4e29b9d2a012a52b67d454fb1c02ac7`.
The entire target was read. Git-object/workfile hashes match; commit scope is one
new file and QD worktree was clean. No dynamic target was read before handoff.
Line references below refer only to these frozen bytes.

## Accepted design directions

| ID / decision | Reason / implementation evidence still required |
| --- | --- |
| AC01 ACCEPT | Sections1–3 separate unchanged r3, new transport and differential-only ReferenceFact import. Frozen raw/fact catalogue plus causal generated registry avoids predeclared future fills. S01/S02 must compare expanded financial/null/clock semantics, not producer totals alone. |
| AC02 ACCEPT | Sections2/6 retain exact rational arithmetic, FIFO, signed costs, per-obligation T/B/P/A/L, B1 local nullable fee attribution and late corrections/refunds. Closed lots stay addressable and prior as-known views immutable. These still need actual long-trace tests. |
| AC03 ACCEPT | Section4's controlled typed deterministic port is appropriate, with explicit trusted-code rather than hostile-sandbox claims. Hashes alone do not prove causality; admission, validators, complete state and independent future perturbation are necessary. No general Python proof/new DSL is needed. Practical transport gaps remain RV01/RV02. |
| AC04 ACCEPT | Section6 removes nested view IDs from ViewCore and economic_state_sha from its own preimage. Handles follow hashing; ReceiptCore/HeadCore avoid current-prefix cycles. S10 must actually construct hashes/receipts/pages and reject mixed-cutoff tokens; this is currently a paper design. |
| AC05 ACCEPT | Sections2/5/6 keep actual non-tick query time, recompute MARK age/reserve expiry/due-calendar coverage and seal the real no-tick advance time. Test source10/max_age1 -> fresh11/stale12, reserve expiry equality11 and snapshot due11, including ±1us. No stale tick-cache substitution. |
| AC06 ACCEPT | Section5 distinguishes late current knowledge of old obligations/bookings from forbidden backdated new origins. Duplicates cannot pay twice; stale legal finality remains immature rather than a fake zero or indiscriminate integrity stop. Preserve r3's common-domain semantics. |
| AC07 ACCEPT | COMMIT_OUTCOME_UNKNOWN/resolve_commit is the right distinction after publication; no false rollback or blind retry. Durable resolution/latch recovery needs RV03 below. No crash test has run. |
| AC08 ACCEPT | Persistent roots/reverse indexes/paging and declared adapter-state checkpoints address lifetime history without resets. Cold recovery may rebuild once; ordinary advances cannot rescan all history. A state hash alone does not establish completeness. |
| AC09 ACCEPT | S13 explicitly requires actual pinned native policy with reviewed numeric/intent/execution/state schemas on synthetic inputs. Infrastructure-only acceptance may precede it only while reporting R3_NOT_READY. Market scenarios, labels and fit remain separate gates. |

## RV01 — REVISE: provide complete economic inputs across controlled ports

Target section4, lines293–295,371–375,399–403. AdapterInput supplies facts,
Balance/economic component roots and only that adapter's prior_state. It supplies
neither actual live lot ranges nor earlier DecisionRecord/intent content. The
execution result must reference stored earlier intent, but the closed input type
gives that execution port no way to obtain it. Public scan needs an audit view
handle expressly excluded from the adapter; facts may not smuggle order intent.
A root proves identity, not the numerical inputs needed by native execution.

Minimal counterexample: P at t10 emits D/O for long3 and saves its plan/feature
in P's state. At t20 separate execution port X has empty state, price100 and C1000
plus roots. It cannot recover O's side/quantity/cancel status or closing feature
without a forbidden global/scan, decoding a hash or hidden state duplication.
Similarly, an environment funding port cannot enumerate current FIFO eligibility
from a lot root alone. Validating a Fill reference afterwards does not supply its
producer's inputs. A single toy port owning its own events does not test this.

Required QD edit: a bounded controller-built economic-input projection carrying
needed current inventory/lot ranges and available decision/order intent and
confirmation state, or an explicit single composite-port design with a complete
authoritative input/state binding providing the same information. If separate
roles remain supported, their communication must be explicit. Freeze selectors,
per-role allowlists, clocks, source of truth and oversize behavior in registered
closed schemas. Bind values/membership to before-view roots and input hash; include
ledger reads as well as Fact reads in the controller inventory. Do not expose
raw/audit handles, arbitrary callbacks or future decision arrays.

Acceptance: distinct P/X ports submit then partially fill/cancel; environment port
captures exact live ranges. X uses the stored intent, not a favorable reconstruction.
Altered/omitted/stale/future intent or lot input rejects before commit. Restart
between submission/fill reproduces all P/X/ledger states. Later S13 demonstrates
actual native signals/allocation/timing/sizing/feedback using this same transport.
QD authors the type amendment; QR reviews it and owns independent checks.

## RV02 — REVISE: clarify pre-account warmup admission

Target sections3/5, lines196–205 and499–502. Initial state is predeclared; first
advance covers [initial_at,through], with batch source/import availability in that
interval. Whether pre-initial_at context Facts can enter the first controlled
packet is ambiguous. The proposed R3 account starts2024 but needs2023 indicators.
This is a specification ambiguity, not an executed failure.

Minimal counterexample: a closed2023-12-31 Fact is available before initial_at=
2024-01-01. Rejecting it loses warmup; retimestamping it changes availability;
accepting an unexplained precomputed feature capsule hides its input dependencies.

Required QD edit: distinguish immutable pre-initial context facts from financial
transitions and new post-genesis deliveries. Permit the approved closed prefix
at the first controlled slot with original clocks/qualification and no financial
replay, or define evidenced deterministic initial-state construction with exact
prefix binding and budget. Specify first admission/dedup cursor semantics.
Reference-import origin rules and post-seal backdating rejection must not weaken.

Acceptance: warmup with no position/fee/funding cash; first actual native decision
matches independent preparation from that prefix. Test before/equal initial time,
unavailable future warmup, restart after first slot and later backdating. Future
raw/catalogue perturbation cannot alter initial economic/native state. No market
intake or private data is needed. QD authors the clarification; QR reviews/tests.

## RV03 — REVISE: finish durable commit resolution and stop recovery

Target sections5/7, lines560–584 and807–815. Pre-/post-HEAD failure separation is
accepted. “Validate actual durable HEAD” needs a concrete barrier rule after the
required directory fsync fails. Persistent integrity/resource stops also need
explicit open/restore semantics so a checkpoint cannot clear them.

Minimal counterexample A: HEAD replace succeeds, directory fsync fails, then a
reopen reads the new pointer from cache. Returning committed solely from readable
bytes/hash/request index does not re-establish required directory durability.
The contract must not equate readable with durably acknowledged.
Counterexample B: H0 checkpoint is ACTIVE; a conflicting write durably latches
INTEGRITY_STOPPED without changing its economic prefix. Restoring only H0's journal
must not return ACTIVE and admit another order. An orphan tail containing a request
must not count as a committed request either.

Required QD edit: under the single-writer lease resolve against validated committed
HEAD/request reachability, re-establish required durability barriers/readback or
remain unknown, and define exact transitions out of COMMIT_UNKNOWN. Specify outcomes
for continued barrier failure, orphan-tail request and same request_id/different
request_sha256 (REQUEST_CONFLICT). Bind stop-control evidence to ledger/prefix and
reapply it on open/restore; I/O resolution cannot clear an independent semantic/
resource stop. Existing failure receipts can carry this control state with explicit
validation rules; no new financial schema or general storage framework is demanded.

Acceptance: failures around replace/fsync/readback; cached-readable but failing
barrier -> unknown; successful barrier -> one committed receipt; durable old HEAD
with no reachable request -> proven noncommit; orphan/wrong request hash rejection;
semantic/resource stop then crash/restore remains stopped. Resolution is idempotent
and recovery/resubmission work counts within frozen limits. No unlimited retry loop.
QD owns implementation/storage tests; QR independently checks states/cash/receipts.

## RV04 — REVISE: finite functional inventory and S13 stage boundary

Target section8, lines876–906. Eight measured producer attempts and absolute/growth
caps are concrete. But one functional suite is said to contain finite S01–S13
variants while S13's real native port is separately allocated later. Counts/fixtures
and independent artifact checking versus benchmark repetition must be frozen.
A wall cap is not a finite case inventory.

Required QD edit: initial infrastructure acceptance covers S01–S12 via an explicit
bounded positive/negative case manifest, fixture sizes/clocks/expected reasons,
seed=NONE and suite ownership. Retain R01–R06/B1 and RV01–RV03 coverage; do not omit
hard cases to fit. Record S13 NOT_EXECUTED/BLOCKED_NATIVE_PORT in the initial result,
not all13 PASS or an unexplained skipped test. Its later native gate needs a separate
finite register. QR checks the eight saved producer artifacts/ratios independently;
no hidden eight QR benchmark repetitions. A failure needs review/new bounded
continuation, not automatic reruns or larger limits.

Budget opinion: **ACCEPT proposed initial-infrastructure ceilings**, subject to
that manifest revision: N512/2048/8192/32768, twice each,8 measured attempts,
60s each/480s total; producer and QR suites120s each;720s combined,2304MiB new output,
256MiB RSS,8MiB cache and the stated page/transaction/read/state/exact-integer caps.
Both relative and absolute limits must pass, including validation/fsync/checkpoint/
late correction and recovery. No feasibility claim before measurement; cap failure
is a candidate failure. No increased resource or extra experiment is requested.

QR A–C checkpoint946e9fc explicitly adopts this separate **initial ledger** register
and supersedes its earlier uncommitted16K/32K/64K suggestion. QR's later query/
18-path native-market ceilings are a different proposed R3 stage, not permission
to enlarge/retry this ledger register. Neither budget is execution authorization.

## Future gates BLOCKED, not reasons to postpone all infrastructure work

| ID / status | Required future evidence |
| --- | --- |
| BG01 BLOCKED_NATIVE_PORT | S13 actual pinned native functions and closed numeric/feature/intent/execution/full-state schemas on synthetic inputs. Include1h/4h/day closure, fractional volume, new funding availability, timing/sizing books, pending orders/reserves and interrupted continuation. No hidden state/future arrays. |
| BG02 BLOCKED_SCENARIO_CHOICES | QR's new slippage/latency/capital/capacity/reserves/feedback/tail remain proposed pending QD engineering review and human choice. Approved fees/MARK/funding clocks/multipliers are not reopened by ledger review. |
| BG03 BLOCKED_QUERY_REPLAY | Independent complete-prefix/latest-eligible MARK query proof, finite actual-query subset, full-state A23/A26/A34, unknown budgets, native feedback and fold/restart continuity before market acceptance. Raw intake or small ledger arithmetic is insufficient. |
| BG04 BLOCKED_LABELS_TRAINING | R4 labels/finality/selection/sufficiency and R5 frozen model/evaluation plan still absent. No fit/activation/integration follows from infrastructure PASS. Fresh human confirmation before fitting remains required. |

## File allocation review

ACCEPT proposed exclusive separation, **not new editing permission**:

- QD alone revises its interface request. Later allocated implementation:
  `research/qd009/streaming_ledger.py`, `tests/test_qd_streaming_ledger.py`, unique
  QD report and ignored synthetic stores. Old QD007/r3 files stay frozen.
- QR independent `research/qr009/validate_streaming_ledger.py`,
  `tests/qr_research/test_qr009_streaming_ledger.py` and oracle evidence;
  never use producer arithmetic as expected values.
- Later QD `research/qd008/native_adapter.py`, `tests/test_qd_event_replay.py`;
  QR semantic/E2E review. MARK/query work needs separate allocation, not expansion
  of this ledger module. S13 is an explicit native gate, not an optional shortcut.
- Existing separate QD `research/qd009/episode_export.py` and future QR label-policy/
  independent-validator allocations are preserved. Shared journals remain with
  the integration editor; no automatic branch merge or concurrent file edits.

No generic causal language, extra model family, historical-exact reconstruction,
new exchange intake or broad rewrite is requested. RV01–RV04 address the promised
real replay ports and explicit persistence/resource guarantees.

## Review evidence and next checkpoint

Performed full static contract/native-source comparison, exact workfile/Git-object
hashing, commit scope/status and type/dataflow review, plus counterexample reasoning.
No S01–S13 test, benchmark, native bridge, synthetic stream, market query/replay or
fit was executed. ACCEPT entries are bounded design judgments, not implementation
behavior evidence. No numerical research choice was approved on the user's behalf.

Next: QD authors one bounded amendment for RV01–RV04 and returns exact commit/hash;
QR rechecks that frozen target. Coordinator may arrange parallel engineering review
of already committed QR A–C. Do not implement a shared contract before review or
ask the user to settle internal mechanics. Stop after this independent checkpoint;
coordinator reads it directly, with no cross-chat reply required.
