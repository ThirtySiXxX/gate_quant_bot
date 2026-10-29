# QF006-CR execution, funding and label sidecar proposal

State READY_FOR_QD_RECHECK; proposal qf006-proposal-r2; author QR;
proposed shared-schema/producer owner QD;
QR owns financial/label semantics and independent acceptance. Date 2026-10-28.
Base QR 96be10c19a7cece6f4e8ba3fb91a8b65d2a90608; reviewed QD preflight
01bc6e798edd200e9553c17702739279f34f0384; exact review
611cb7419e676bde8cb0b2e64968f3a81bd42164 requested R1-R3. Recheck pending.

Problem: the old funding frame conflates source t with idealized availability,
native costs prorate elapsed time, and the old episode label knows no asynchronous
posting/finality. None can represent nominal snapshot versus booking exactly.
Reasons and formulas: `research/qr006/protocol.md`; stable acceptance IDs:
`research/qr006/acceptance.json`. Official evidence: `research/qr006/evidence.json`.

## Compatibility and ownership

New **standalone research sidecars only**, namespace qf006/schema_version=1.
Do not add fields to `src/contracts.py`, native registry 1.0.0, envelope v1,
feature version 1, ML JSON bundles, result schema 3, or old QR003/004/005 files.
No implicit native consumer fallback; it must reject this namespace until a
separately reviewed adapter exists. Rollback is simply not selecting the sidecar;
original immutable inputs and policy remain readable unchanged.

QR confirms QD's exact future allocation: QD alone owns
`research/qd009/episode_export.py` and `tests/test_qd_episode_export.py`;
QR owns `research/qr009/label-policy.md`,
`research/qr009/validate_episode_labels.py` and
`tests/qr_research/test_qr009_labels.py`, plus respective role reports.
The earlier synthetic-ledger/coverage/replay stages retain the QD plan's proposed
exclusive paths. These are agreed ownership proposals only. No implementation
file claim is granted now. Shared docs and runtime stay with their current owner.
Counterpart review is not human implementation/integration/training approval.

## Minimum shared boundary: five records

These are proposed required keys; every nullable value needs a reason code.
Reject unknown namespace/version, unexpected keys, conflicting duplicate identity, nonfinite
Decimal strings, booleans as numbers, incompatible units or missing provenance.
No silent milliseconds/seconds conversion. UTC event times use integer
microseconds and `source_time_precision` states actual resolution; old source
seconds are also retained. Monetary scalar fields carry USDT; contracts are signed
integers, price USDT/base, multiplier base/contract, rates decimal fractions.
Identical identity/revision and payload is an idempotent no-op with no extra
posting; different payload under that identity/revision is quarantined. Transport
whitespace is not payload content. Convert preserved source seconds by exactly
1_000_000; a 24h duration is 86_400_000_000 microseconds, never 86_400 microseconds.

Common fields: namespace, schema_version, record_type, record_id,
instrument_id (`gate:usdt:BTC_USDT` or ETH_USDT), scenario_id, evidence_mode
(HISTORICAL_EXACT/SCENARIO), source_refs (manifest SHA + source ID/row),
source_time_precision, created_at, revision, supersedes_id, status, reason_codes.
`created_at` is export time, never knowledge time. Currency/unit declarations
are explicit in the schema/record. Unknown-key policy must be revisited only in
a versioned revision, not relaxed to absorb incompatible sources.

| Record | Additional required fields and types | Owner -> consumer |
| --- | --- | --- |
| RuleSegment | rule_id:string, rule_kind:fee/funding/multiplier/valuation/sequence/booking; valid_from:int or null; valid_to_exclusive:int or null; published_at:int or null; observed_at:int; scope:object; parameters:typed map; applicability:observed/scenario/unresolved; source_url:string; uncertainty:string/null | QD writer, QR semantics -> ledger and information filter |
| Fill | trajectory_id/order_id/fill_id/decision_id:string; episode_id:string; decision_at/filled_at:int; sequence:int/null; signed_contracts:int; fill_price/multiplier/fee_fraction/fee_cost_usdt/fee_cash_usdt:decimal; multiplier_rule_id/fee_rule_id:string; liquidity_role:maker/taker/unknown; role_basis:observed/scenario; fee_currency:string; allocation_legs:array; available_at:int/null; fee_obligation_id:string; obligation_revisions:ObligationRevision[]; cash_postings:CashPosting[] | QD -> ledger and QR label audit |
| FundingEvent | event_id:string; nominal_settlement_at/snapshot_at/source_record_at:int/null; snapshot_sequence:int/null; mapping_rule_id:string/null; source_t_seconds:integer; final_rate:decimal; final_rate_available_at:int/null; feature_available_at:int/null; availability_basis:observed/scenario/unknown; eligible_lots:array; mark_price/multiplier:decimal/null; valuation_at/valuation_available_at:int/null; valuation_rule_id/multiplier_rule_id:string/null; obligation_id:string; obligation_revisions:ObligationRevision[]; cash_postings:CashPosting[] | QD -> isolated final accounting and past-only feature views |
| LedgerEntry | trajectory_id/episode_id:string; entry_id/event_ref/allocation_id:string; kind:fee/realized_pnl/funding_claim/funding_booking/correction/transfer; transition:obligation_recognition/cash_posting/realized_pnl/transfer; obligation_id:string/null; obligation_revision:int/null; posting_id:string/null; posting_revision:int/null; economic_at/known_at/available_at/booking_at:int/null; cash_delta/receivable_delta/liability_delta/realized_pnl_usdt:decimal; posting_currency:string; position_snapshot_ref:string/null; state_before_sha256/state_after_sha256:string; revision_ref:string/null | QD -> reconciliation and QR audit |
| EpisodeLabel | trajectory_id/episode_id/decision_id/state_sha256:string; entry_at/label_end/label_known_at:int/null; direction:long/short; gross_entry_notional_sum/initial_entry_notional/realized_pnl/fee_cash/funding_cash/net_pnl/target:decimal/null; funding_event_ids/fill_ids/ledger_ids:array; label_status:valid/open/immature/censored/invalid; completeness_assertions:CompletenessAssertion[]; policy_sha256/label_version:string; information_start/information_end:int/null; feature_snapshot_ref:string; invalid_reasons:array | QR semantics, QD sole exporter -> QR validation/future trainer |

### Nested revision, posting and completeness types

All nested records inherit the containing instrument/trajectory/episode, currency
and source provenance unless explicitly narrowed by an allocation. All named time
fields below are UTC integer microseconds or null with a reason; null knowledge
prevents causal use. Container `revision` does not substitute for any nested
identity/revision or cause another posting. Arrays preserve immutable revisions.

| Type | Required keys and semantics |
| --- | --- |
| ObligationRevision | obligation_id:string; obligation_kind:fee/funding; obligation_revision:positive integer; supersedes_obligation_revision:integer/null for initial; origin_ref:string (fill/event); authority_id/rule_id:string; cumulative_signed_total_usdt:decimal/null; economic_at/known_at/available_at:int/null; allocated_totals:array of episode/lot IDs and signed totals; basis:observed/scenario; reason_codes:array |
| CashPosting | obligation_id/posting_id:string; posting_revision:integer exactly 1; signed_amount_usdt:decimal; booking_at/booking_known_at/available_at:int/null; booking_basis:observed/scenario; booking_rule_or_source_ref:string; corrects_posting_id:string/null; allocations:array of episode/lot IDs and signed amounts; reason_codes:array |
| CompletenessAssertion | assertion_id:string; assertion_revision:positive integer; supersedes_assertion_revision:integer/null for initial; authority_id/finality_rule_id:string; basis:observed/scenario; scope:typed object (instrument_id, trajectory_id, episode_id, event_kinds subset of fills/fees/funding/postings, economic_from:int, economic_to_exclusive:int); obligation_revision_refs:array of obligation_id/revision; posting_refs:array of posting_id/revision; asserted_at/known_at/available_at:int/null; reason_codes:array |

For each obligation, current authoritative T is its cumulative signed total;
B is sum of accepted independent postings; pending P=T-B, A=max(P,0), L=max(-P,0).
An obligation revision produces cash_delta=0 and changes pending by T_new-T_old;
a cash posting b produces cash_delta=b and pending_delta=-b. Allocation totals
must sum to their parent; after close they retain the original episode/lot IDs.
Fill fee_cash_usdt describes its original calculated fee obligation, not a second
cash entry; later authoritative fee totals live in its obligation revision chain.
Each funding rate/valuation revision must bind the corresponding obligation
revision and source references, not overwrite a formerly consumed observation.

Deduplication keys include instrument plus (obligation_id, obligation_revision)
or, independently, (posting_id, posting_revision). Same key/canonical content is
a no-op; different content quarantines with CONFLICTING_OBLIGATION_REVISION or
CONFLICTING_POSTING_REVISION. Reject missing supersession links. Partial postings
use different IDs and are supported. Posting revisions >1 are explicitly rejected
as UNSUPPORTED_POSTING_RESTATEMENT in this first proposed schema; actual later
refund/reversal transfers have new posting IDs and independently evidenced clocks.
Derived entry identity additionally binds transition, source key and allocation;
entry_id alone cannot defeat source deduplication. No delta under a generic
"correction" kind can move cash without a CashPosting reference.

booking_known_at >= booking_at and available_at >= booking_known_at;
obligation available_at >= known_at. Clock contradictions are invalid, not fixed
by sorting. Causal transitions use available_at; retrospective cash-event reports
may use booking_at with their separate knowledge version. The former decision
view must never be silently restated with later observations.

Completeness covers economic origins in its half-open interval, plus all postings
and corrections for its enumerated obligation revisions even outside that interval.
For a complete episode, the union of applicable scopes must cover both fills,
fees, eligible funding events and all their postings; all pending amounts must be
zero. Refs must equal the current accepted revision set at that consumer cutoff.
asserted_at <= known_at <= available_at. Unknown authority/coverage/availability
cannot mature a label. A supersession becomes effective for the consumer only at
available_at and requires a new label revision; its label_known_at cannot precede
the successor assertion's available_at. Include all required outcome/revision/
posting/assertion available times in the maximum defining label_known_at.
No scalar completeness_watermark is accepted in the new transport. A29's existing
null-watermark fixture is a shorthand for absent assertions, not a wire field.

`valid` alone permits nonnull target/label_known_at and requires natural flat plus
settled complete evidence. `open` requires continuing exposure and null natural
label_end/target/label_known_at. `immature` requires natural flat with label_end
nonnull and pending legitimate outcome/finality information; target/known remain
null. `censored` or `invalid` require target/known null and retain label_end only
if an actual natural exit exists. Precedence and hard-error distinctions follow
protocol section 6.2. `role_basis=synthetic` is rejected; the A02 wire value is
`scenario`, including for an entirely synthetic example.

`RuleSegment.parameters` uses a per-rule allowlist: fee(role, signed_fraction,
tier, discount, fee_currency, rounding); funding(interval_seconds, snapshot_rule,
rate_source_kind); multiplier(base_per_contract, conversion_rule); valuation
(price_kind, asof_rule, max_age_us); sequence(tie_order); booking(lag_us or
observed_source, pending_budget_policy). Inapplicable parameters are absent,
not an unconstrained arbitrary dictionary. A rule observed today with unknown
historical start has null valid_from; no backdating to source raw_start.

Fill allocation legs minimally identify close/open action, episode, signed
contracts and fee_cash; their quantities and fees sum exactly to parent fill.
Funding eligible_lots minimally identify snapshot lot/episode, signed contracts,
effective multiplier rule and allocated signed_cash. Sum equals event cash;
post-close booking cannot attach to a new current position. Store eligibility
even when final valuation is unresolved; do not fabricate a final cash value.

Unresolved LedgerEntry amount must not be represented as a zero-valued posted
entry: keep the unresolved FundingEvent, block affected label finality and risk
budget, and create entries only once amounts are established. Correction links
preserve all previous entries. Duplicate complete input is idempotent; conflict
within a revision quarantines instead of last-write-wins.

Amounts use positive receivables/liabilities, signed cash (positive credit) and
positive gross notional. Unit/rounding checks are independent of float-tolerance
tests. Ledger/balance adapters must separately output booked cash, receivables,
liabilities, unrealized PnL, economic equity, simulated budget, and actual available
margin status. Unknown actual margin is null, not economic equity. The exact
BalanceSnapshot transport can be nested in the ledger result manifest; its
minimum fields and invariant are the protocol's C/A/L/U/E definitions.
The synthetic decision budget includes min(U,0); unavailable/stale U blocks new
risk. Reserves must not double count losses, liabilities or posted fees. Preserve
exact label net numerator/entry-notional denominator; target serialization uses
12 decimal places, ROUND_HALF_EVEN, independently of fee/cash rounding.

## Requested implementation acceptance and handoff

Acceptance matrix QF006-A01 onward contains hand-computable synthetic inputs,
expected outputs/rejections and checker owners. Required integration sequence:
QD confirms minimal file scope -> human authorizes isolated implementation ->
QD deterministic producer/ledger tests -> QR independent arithmetic and causal
review -> separate data coverage/label assessment -> human training confirmation.

Independent work while waiting: QR can review document references and algebra;
QD can map current code and provide scope/test feasibility, without implementation.
No branch is merged or cherry-picked automatically. No changes to risk defaults,
real configuration, data sources or platform services are requested.
