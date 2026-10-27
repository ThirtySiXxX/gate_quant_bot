# QF006-CR execution, funding and label sidecar proposal

State READY_FOR_QD_REVIEW; author QR; proposed shared-schema/producer owner QD;
QR owns financial/label semantics and independent acceptance. Date 2026-10-28.
Base QR 96be10c19a7cece6f4e8ba3fb91a8b65d2a90608; reviewed QD preflight
01bc6e798edd200e9553c17702739279f34f0384 (not yet counterpart approval).

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

QD proposes exact future paths for pure ledger, adapters and producer tests;
QR proposes independent contract/label checks after allocation. No implementation
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
| Fill | trajectory_id/order_id/fill_id/decision_id:string; episode_id:string; decision_at/filled_at:int; sequence:int/null; signed_contracts:int; fill_price/multiplier/fee_fraction/fee_cost_usdt/fee_cash_usdt:decimal; multiplier_rule_id/fee_rule_id:string; liquidity_role:maker/taker/unknown; role_basis:observed/scenario; fee_currency:string; allocation_legs:array; available_at:int/null | QD -> ledger and QR label audit |
| FundingEvent | event_id:string; nominal_settlement_at/snapshot_at/source_record_at:int/null; snapshot_sequence:int/null; mapping_rule_id:string/null; source_t_seconds:integer; final_rate:decimal; final_rate_available_at:int/null; feature_available_at:int/null; availability_basis:observed/scenario/unknown; eligible_lots:array; mark_price/multiplier:decimal/null; valuation_at/valuation_available_at:int/null; valuation_rule_id/multiplier_rule_id:string/null; signed_cash_usdt:decimal/null; booking_at/booking_known_at:int/null; booking_basis:observed/scenario/unknown; completeness_watermark:int/null | QD -> isolated final accounting and past-only feature views |
| LedgerEntry | trajectory_id/episode_id:string; entry_id/event_ref/allocation_id:string; kind:fee/realized_pnl/funding_claim/funding_booking/correction/transfer; economic_at/known_at/booking_at:int/null; cash_delta/receivable_delta/liability_delta/realized_pnl_usdt:decimal; posting_currency:string; position_snapshot_ref:string/null; state_before_sha256/state_after_sha256:string; revision_ref:string/null | QD -> reconciliation and QR audit |
| EpisodeLabel | trajectory_id/episode_id/decision_id/state_sha256:string; entry_at/label_end/label_known_at:int/null; direction:long/short; gross_entry_notional_sum/initial_entry_notional/realized_pnl/fee_cash/funding_cash/net_pnl/target:decimal/null; funding_event_ids/fill_ids/ledger_ids:array; label_status:valid/open/censored/invalid; completeness_watermark:int/null; policy_sha256/label_version:string; information_start/information_end:int/null; feature_snapshot_ref:string; invalid_reasons:array | QR semantics, QD exporter -> QR validation/future trainer |

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
