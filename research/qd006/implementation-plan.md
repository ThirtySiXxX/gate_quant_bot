# QD006 exact-draft feasibility review and bounded implementation plan

2026-10-28 Australia/Melbourne. Decision: **ACCEPT** for QR revision
`c7e9a2492247fa31e216035f87e8bb20cca6e6ad` (`qf006-proposal-r2`).
**Protocol/design review accepted; not implementation-tested or data/training-ready.**
No implementation or research run is authorized. The initial QR draft
`2c3846c53443307b410a647ba0efbed078884d8b` was reviewed at QD commit
`611cb7419e676bde8cb0b2e64968f3a81bd42164`, following preflight
`01bc6e798edd200e9553c17702739279f34f0384`. Its three requests are now resolved.
Machine-readable per-ID dispositions: `research/qd006/review.json`.

## Final bounded recheck

All **34 QF006 acceptance criteria and 12 QD constraints ACCEPT** as design.
All five exact QR committed/file hashes matched; only A02/A13/A14/A21 changed,
with the other 30 cases and all nine source summaries unchanged. QD independently
checked 64 literal Decimal assertions and 30 clock/state/contract assertions.
These are document checks, not implemented producer/validator contract tests.

| Resolved request | Revised contract accepted |
| --- | --- |
| QD006-R1 | Independent cumulative obligation T revisions and immutable posting IDs; B sums accepted postings, P=T-B, A/L summed separately by obligation. Revisions change pending only; available postings move cash. Partial payments, separate refunds and late fees are covered. Imported posting revisions >1 explicitly reject; actual later transfers have new evidenced IDs. |
| QD006-R2 | A02 role_basis is scenario; valid/open/immature/censored/invalid and their nullability/precedence are explicit. Natural flat with pending legitimate outcomes is immature, not zero or prematurely valid. |
| QD006-R3 | Typed assertion covers origins plus linked postings/corrections, authority/rule and current revision references. Issuance/receipt/consumer availability are separate. Label-known time includes all required availability; supersession changes the latest revision only when available and preserves prior as-known labels. |

No material correction remains outstanding in this bounded review. The exact
proposed implementation paths below are confirmed by QR as ownership proposals;
they still require coordinator allocation and separate human implementation/run
authorization. Stop after this design review.

## Accepted design and deferred evidence

The SCENARIO / HISTORICAL_EXACT separation is implementable. Scenario fees,
synthetic tie order, valuation/availability assumptions and multiplier constants
are versioned research inputs, not inferred historical facts or new app defaults.
Funding is per eligible snapshot, independent of the active position at booking;
exact historical mode rejects missing mapping, mark, multiplier or actual booking.
No elapsed-time proration, inferred eight-hour calendar or trade-as-exact-mark
substitution is accepted as a primary event-accounting result.

Accept the synthetic budget `C-L+min(U,0)-reserved_margin-reserved_fees`, with
causal fresh U and known liabilities, no spendable A/unrealized gains, and no
double subtraction. This changes the research state policy: it is neither
unchanged native replay nor a statement about actual Gate margin. Unknown/stale
inputs block new risk while reductions remain permitted. Native defaults stay put.

Accept exact integer microseconds, retained source precision and lossless source
seconds conversion. A 24h duration is **86_400_000_000 us**. Both
`label_known_at+embargo < fold_boundary` and `label_end+embargo < fold_boundary`
are strict; equality fails. Cross-asset decision-to-known overlap is additionally
purged. Natural exit may remain label_end because knowledge/interval checks are
separate; the old exit-only eligibility check must not be reused.

Accept FIFO research lot attribution, gross entry-notional denominator including
adds, exact ledger sums and 12dp HALF_EVEN target reporting. Rejected/unfilled
proposals remain selection records with null targets, not zero outcomes. Natural
losses remain valid. Forced terminal exits and unsupported economics are separately
identified. State carries across folds. Predictive comparisons and policy-value
comparisons are distinct; changing costs/entry filters requires full state replay.

This accepts the specified design directions, not historical input adequacy,
implemented tests, profitability, a complete executable schema or a future run.

## Resolved initial review requests (historical rationale)

The following counterexamples and original requests explain the initial REVISE
decision. They are retained as acceptance rationale, not outstanding instructions;
the final bounded recheck above records their resolution in the exact r2 bytes.

### QD006-R1: independent obligation revisions and cash-posting identities

Affected criteria: A13/A14; QD6-C05/C06/C07/C12. The stated idempotency key
`(instrument,event_id,revision,entry_kind,allocation_id)` does not specify whether
revision is a rate/entitlement revision or an independent cash-posting revision.
`entry_id` exists but is not in that key; FundingEvent has only scalar booking
time/amount context. A14's appended -0.05 does not say whether it changes C or L.

Counterexample, all synthetic: initial C=1000; entitlement total=-0.05 is booked,
so C=999.95 and A=L=0. At 10:00 a new authoritative total=-0.10 is learned, but
the extra posting has not happened: C must remain 999.95, L=0.05, E=999.90.
At 10:01 total is revised to -0.08 before any extra posting: C=999.95, L=0.03,
E=999.92, not another 0.08 debit or a 0.02 cash credit. At 10:05 the outstanding
0.03 posts: C=999.92, L=0, E unchanged. Repeated delivery changes nothing.

Original correction request (now resolved): define a parent obligation identity, authoritative cumulative
amount revisions with supersession, independent stable posting IDs/revisions and
booking/booking-known clocks; specify net-unposted reconciliation against already
booked amounts. State whether multiple partial postings are supported or explicitly
rejected by the first schema. If supported, postings -0.02 and -0.01 for the same
0.03 remainder must have distinct accepted IDs; identical redelivery is a no-op,
conflicting bytes under the same posting revision quarantine. Do not make a new
rate revision imply an extra cash booking. Apply the same rule to a fee correction
learned after a closed fill/episode, including refunds and delayed payment.

Resolved acceptance: revised **A13/A14** retain their IDs and contain literal two-successive-
revision and separate-booking cases, a credit/sign-change variant and a late fee
variant. Preserve as-known history; produce a new restated label revision only
when its new required information/finality is available. This is a schema/state
transition correction, not a request for market/account data or a generic ledger.

### QD006-R2: representable fixture values and maturity state

Affected criteria: A02/A21; QD6-C05/C09/C12. Interface Fill.role_basis permits
`observed/scenario`, but A02 supplies `synthetic`. EpisodeLabel.label_status
permits `valid/open/censored/invalid`, while A21 expects `immature` at cutoff.
A strict exporter/consumer must have one deterministic interpretation.

Original correction request (now resolved): make A02's wire role_basis `scenario` (or explicitly define
its fixture-to-wire projection). Specify the maturity representation and map A21
to it. Minimal recommendation: add `immature` for an already-flat episode awaiting
legitimate outcome/finality information, with target and label_known_at null;
keep open, censored and invalid meanings distinct. An explicitly typed separate
maturity_status is also feasible if its allowed combinations and A21 mapping
are stated. Do not silently accept an unexpected enum string or label pending
cash as a realized zero. Keep A02/A21 IDs unchanged.

### QD006-R3: finality coverage is not finality knowledge time

Affected criteria: A21/A22/A29; QD6-C07/C09/C12. The integer
`completeness_watermark` has no explicit distinction between covered event time
and when that assertion becomes available, or its rule/revision scope. A21 makes
those times equal, so its present example cannot expose a hindsight mistake.

Counterexample: a funding watermark covers funding obligations through 08:00 but is first known at
10:00. A position exited at 08:00:01 with booking known at 08:00:04 must not
mature at 08:00:04 using that later assertion. If a new revision at 11:00 supersedes
the earlier completeness assertion, the revised label cannot inherit 10:00 as its
knowledge time or rewrite the earlier causal view.

Original correction request (now resolved): define the watermark's coverage meaning and separate
availability/known time, scope/revision and finality-rule reference. These may be
a small typed nested assertion or explicit fields; unknown authority/coverage or
knowledge leaves label_known_at null. In a scenario use a preregistered explicit
finality policy, never a retrospective retrieval timestamp disguised as first
knowledge. Include the assertion's available time in label_known_at; the strict
microsecond checks in A22 remain unchanged. Extend A21 with unequal clocks and
later revision; retain A29's null/unknown negative case and stable IDs.

## File ownership, ordering and compatibility proposal

These are exact **proposed future allowlists**, confirmed by QR in the reviewed
r2 draft, still requiring coordinator allocation and separate user implementation
authorization. Current changes remain
Markdown/JSON only. One path has one editor; no parallel edits to shared files.

| Stage | Sole editor paths | Reviewer / release boundary |
| --- | --- | --- |
| 1: synthetic ledger and strict research records | QD `research/qd007/event_ledger.py`, `tests/test_qd_event_ledger.py`, `docs/agent-reports/qd/QF-QD-007-ledger.md`, ignored `research/.data/qd007/` | QR owns `research/qr007/validate_event_ledger.py`, `tests/qr_research/test_qr007_ledger.py`, QR007 report; independent literal oracles and corruption checks, no import of QD arithmetic |
| 2: existing-evidence coverage design/report | QR `research/qr008/coverage-protocol.md`; QD `research/qd008/coverage.json` and QD coverage report | QR reviews claimed coverage; no downloader or new evidence window unless separately authorized; pin revised spec before actual intake |
| 3: full-state research replay adapter | QD `research/qd008/native_adapter.py`, `tests/test_qd_event_replay.py`, QD replay report and separately assigned ignored results | QR reviews unchanged policy consumption, ledger-to-budget/timing feedback and complete paired trajectories; actual-data replay needs a separate bounded run authorization |
| 4: episode target serialization | QD `research/qd009/episode_export.py`, `tests/test_qd_episode_export.py`, QD009 report | QR writes `research/qr009/label-policy.md`, `research/qr009/validate_episode_labels.py`, `tests/qr_research/test_qr009_labels.py`, QR009 report; actual label generation separately authorized |

This resolves the proposal's ownership wording: **QR owns target mathematics,
maturity/censoring/selection semantics and its independent validator; QD alone
writes the EpisodeLabel producer/exporter**. QR's phrase "target construction"
must refer to semantic specification/independent checking under this proposed
allocation, not simultaneous edits to the QD exporter. QR confirmed that allocation
in the exact r2 interface/report. No new schema file outside these paths is implicitly owned.

Stage 1 supports fees/claims/bookings/corrections, as-known versus restated views,
FIFO quantities and reconciliation on synthetic tapes. It does not implement a
market replay, full label exporter, trainer, database or exchange client. A01-A20
are primarily ledger/schema fixtures; A24's inventory/cash arithmetic can be
checked there, with target reporting in stage 4. A15/A16/A30-A33 have both
synthetic rejection tests and separate actual-evidence gates in stage 2.
State-path A23/A26/A34 reach full acceptance only with stage 3 evidence; maturity,
selection, target and overlap A21-A25/A29 reach it with stage 4. A27/A28 remain
compatibility/authorization boundaries throughout. No stage is approved here.

Before stage 1 freeze exact typed common/record enums, lot and posting IDs,
correction links, revision semantics, nullable-field reasons, per-rule parameter
allowlists and canonical serialization. The nested balance transport must explicitly
name C/A/L/U/E, budget/reserve amounts, valuation and knowledge clocks, statuses
and hashes; an unknown amount cannot be replaced with a zero LedgerEntry.
QD writes the research schema, QR reviews financial meaning. Keep qf006 namespace
and native version rejection explicit. No third-party validation dependency is needed.

Existing `src/`, old probes/data/results, model bundle format, feature version 1,
native result schema 3 and runtime configuration are read-only. The later adapter
calls unchanged shared policy functions, uses a separate event-accounting loop,
and supplies reviewed causal budget/feedback; it cannot merely relabel the old
native loop's cashflows. No runtime migration, integration or production adapter
is proposed in this phase. Rollback is not selecting the new research entry point;
old artifacts remain readable with their original approximation warnings.

## Deferred run parameters and stop conditions

Before any actual comparison, freeze slippage, latency/executable-open rule,
partial-fill capacity/cancellation, tie-order stresses, mark/proxy freshness,
multiplier/rule mapping, rate availability, booking lag/finality, starting capital,
synthetic budget reserves and cost-stress budget in one hashed scenario manifest.
Unknown mark coverage or source-to-snapshot mapping blocks the primary mark-based
run even if a synthetic ledger is correct. Historical-exact claims remain blocked
without historical mechanism/arrival/booking evidence; no credentials are requested.

QR retains hypothesis/features/model/search-budget/effect/precision choices;
prospective holdout dates and stop rule must be registered before viewing that
period. Training has no authorization here, including fitting preprocessing.
Stop after this accepted protocol/design review. Next dependency is a separate
human decision about the bounded synthetic implementation, followed by typed
manifest/schema detail review, implementation tests and independent validation.
There is no automatic implementation, intake, replay, label generation or scheduling.
