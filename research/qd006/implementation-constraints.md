# QD006: execution, fees and label implementation constraints

Status: **PREFLIGHT_COMPLETE_AWAITING_EXACT_QR_SPEC**. Design only, 2026-10-28
Australia/Melbourne. These QD constraint IDs support later review of the exact QR
proposal; they do not approve an unseen protocol or authorize implementation.

## Estimand and evidence boundary

Choose and version either historical reconstruction with dated evidence, or a
declared counterfactual mechanism/cost scenario applied to historical trade bars.
Missing historical evidence must not silently select the second while reporting
the first. The approved BTC/ETH data range stays `[1672531200,1793091600)`, 2023
warmup. Current contract snapshots and the single frozen trade-price stream do
not establish historical mark values, fee tiers, funding eligibility or arrivals.

Current Gate documentation distinguishes funding snapshot from asynchronous
posting and notes that a posting after close can appear only in account flows.
It values USDT funding using mark price, contracts and multiplier. This describes
the current page, not proven applicability across 2023-2026. The preserved funding
source timestamp cannot stand for every clock. [Official funding rules](https://www.gate.com/zh/help/futures/futures-logic/27569/funding-rate-and-funding-fee).

Fees attach to executed quantity with the applicable liquidity role; a limit
order alone does not establish Maker status. [Official fee explanation](https://www.gate.com/zh/help/futures/futures_logic/22079?category=futures).
The April 9, 2026 announcement's public VIP0 USDT-perpetual Taker 0.0500% is a
documented scenario, not a personal or full-history rate. [Official announcement](https://www.gate.com/zh/announcements/article/50390).
The API documents separate mark candles and per-fill role/fee fields; their
existence proves neither complete historical coverage nor settlement-instant mark
reconstruction. No account endpoints or market data were queried. [Official API](https://www.gate.com/docs/developers/apiv4/en/futures/).

## Required contract decisions for QR review

**QD6-C01 — Versioned scenario and rule validity.** Bind dataset, rule evidence,
fee policy, execution policy, valuation policy, attribution policy and proposed
label definition by IDs/hashes. Record evidence observed time, supported effective
range or unknown, historical/counterfactual basis and limitations. Do not reuse
native result schema 3 or market envelope v1 for materially different semantics.

**QD6-C02 — Distinct funding clocks.** Proposed funding record needs stable
`funding_event_id`, instrument, nominal schedule time, eligibility snapshot time,
unrounded source-record time, actual posting time, and per-input information
availability/basis. Unknown clocks remain null with a reason. Preserve UTC seconds
and any evidenced subsecond sequence; do not round raw seconds or derive a
historical schedule from inter-record durations alone. Source record identity is
not actual account-posting identity. Schedule/rule evidence must map them before
an event can qualify a historical position.

**QD6-C03 — Eligibility and tied events.** Fix eligible quantity from the
snapshot, not the position still open at posting. Independent position-cycle and
lot IDs survive close/reversal. Same-second fills versus snapshot need documented
sequencing or an explicit bounded scenario; lexical ID sorting is deterministic
serialization, not evidence of exchange priority. Without either, return
`eligibility_ambiguous`; do not generate an exact target. Snapshot-before-fill
and fill-before-snapshot synthetic fixtures must both be representable.

**QD6-C04 — Distinct prices and units.** Signed quantity is contracts; multiplier
is base/contract; mark/fill/trade prices are USDT/base; cash and PnL are USDT;
rates are signed fractions, slippage is bps. Funding cost (positive expense)
`C = signed_snapshot_contracts * multiplier * settlement_mark * final_rate`.
Trade close/open is never silently relabeled exact mark. Unknown mark,
multiplier effectiveness or valuation time blocks historical amount certainty;
any proxy must be separately named, causal when used by decisions and subjected
to predeclared sensitivity rather than chosen by profitability.

**QD6-C05 — Fees and fill identity.** Record order ID, unique fill ID, position
cycle/lot attribution, event time, availability, filled quantity, execution price,
liquidity role, effective fee-policy ID, signed fee and rounding/currency rule.
Canceled/unfilled orders have zero executed fees; partial fills charge their own
notional once. Replayed identical IDs are idempotent, conflicting duplicates fail.
Unknown role cannot receive an unproven Maker discount. Credits/rebates require
an explicit signed convention and evidence; no absolute-value clipping.

**QD6-C06 — Pending obligations survive flattening.** Independent funding
entitlements and postings link by event/obligation IDs, outside the active-position
dictionary. Define signed pending asset `P` (positive receivable, negative payable),
posted cash `W`, marked unrealized `U`; economic equity is `W+U+P`. When final
amount is recognized, funding expense C changes P by -C. Posting changes W by
-C and P by +C, leaving economic equity unchanged if other state is unchanged.
Duplicate posting is a no-op only with matching identity/content. Corrections
append reversal/replacement entries; they must not overwrite earlier evidence.

**QD6-C07 — Causal policy state versus retrospective attribution.** Attribution
may attach a final fee to its earlier eligible snapshot for audit; decisions must
not see its final rate, mark or cash effect before information is available.
Represent effective time, recognized/available time and posting-observed time
separately. Pending eligibility may be known while amount is unknown: preserve
`amount=null`, not zero. Unknown actual arrival cannot become proven availability.
Any scenario resolving this must be explicit; otherwise report the research
decision state unsupported. No hindsight recomputation may alter past budgets.

**QD6-C08 — Budget and economic reconciliation.** QR must specify which causal
cash/equity view drives order budgets and timing feedback. Pending receipts are
not automatically spendable. Payable reserve/debit must be counted once, not
subtracted both as pending and posted. A proposed conservative scenario excludes
unposted receivables and reserves known payables, with separate margin reserve;
it is a research proposal, not a change to native risk defaults or a claim about
Gate liquidation rules. Numerical examples below assume all amounts already known.

**QD6-C09 — Exit, attribution and label maturity.** Keep position-flat time,
economic attribution interval, last required outcome observation and label-mature
time distinct. Allocate snapshot cost to the eligible lot/cycle, including any
already closed part, never to a new opposite position. A cash-settled target
includes late postings and is immature while required amounts/postings remain
unresolved. An economic-accrual target may mature earlier only under an explicitly
reviewed final-obligation policy; retain pending balances and identify that mode.
Label end/availability used for purge/embargo must include required delayed outcome
information, not just the exit fill. A cutoff cannot fabricate zero funding,
posting completion or a natural exit. Terminal liquidation is separately censored
unless the target explicitly specifies that executable horizon policy.

**QD6-C10 — No-event and partial/reversal accounting.** A holding interval with
no qualifying snapshot has zero event funding, regardless of elapsed hours.
Partial closes allocate the fixed snapshot entitlement without recomputing it
from the residual quantity. A reversal has separate close/open lots; earlier
entitlement cannot transfer to the new leg or net away. Funding sign must work
for long/short and positive/negative/zero rates; fee and funding credits remain
visible. Summed lot costs equal the event cost, without rounding drift.

**QD6-C11 — Stateful replay boundary.** Ledger-only postprocessing can audit a
fixed supplied fill tape but cannot claim the same strategy under changed costs.
Costs affect equity, available budget, order sizing and timing feedback. A later
new research replay must feed the reviewed causal ledger into those consumers,
reuse unchanged signal/execution decision functions once per decision, and rerun
the full path for entry-filter counterfactuals. Do not modify frozen probe
`research/qr003/replay_probe.py`, monkey-patch runtime globals, or subtract selected
trades from the old ledger. The old elapsed-time replay remains a named approximate
control, not the event-accounting authority.

**QD6-C12 — Reproducibility and fail states.** Outputs bind all input/code/spec
hashes and deterministic event order, with stable IDs, finite Decimal values,
declared precision/rounding and immutable fresh roots. Explicit statuses separate
unknown eligibility, missing valuation, unknown posting, immature/censored label
and valid zero. Independent QR tests must recompute literal accounting examples,
not import the QD reducer or merely accept recalculated hashes. No fit, collection
or replay is part of this design phase.

## Analytic fixture proposed for acceptance, not a generated market label

All times below and all values are **synthetic**, with known snapshot ordering,
mark and final rate available at snapshot, fee precision exact for these inputs.
Opening long 10 contracts, multiplier 0.001 BTC/contract, fill 49,900; closing
fill 50,100. Each fill Taker rate 0.0005. Snapshot at 08:00:00 uses mark 50,000
and rate 0.0001. Close is 08:00:01; posting is 08:00:03. Initial W=10,000.

| Checkpoint | Posted cash W | Pending P | U | Economic equity |
| --- | ---: | ---: | ---: | ---: |
| After opening fee, valued at entry | 9999.7505 | 0 | 0 | 9999.7505 |
| Snapshot, mark 50,000 | 9999.7505 | -0.05 | 1 | 10000.7005 |
| Closed before posting | 10001.5 | -0.05 | 0 | 10001.45 |
| Posting completes | 10001.45 | 0 | 0 | 10001.45 |

Opening/closing fees are 0.2495 / 0.2505, gross PnL 2, full-cycle net 1.45.
Funding amount belongs to the closed long despite the delayed cash entry. At a
cutoff of 08:00:02 the cash-settled target is immature; the payable is retained.
If six contracts close after snapshot, their funding share is 0.03 and the
remaining four carry 0.02. With no eligible snapshot, funding is exactly zero.
These calculations validate a proposed accounting identity, not exchange data.

## Bounded implementation decomposition and ownership proposal

All paths below are **future allowlist proposals**, not current file claims or
permission to write Python/tests. New dispatches must allocate exact paths and
freeze the reviewed QR specification first.

| Step | Proposed exclusive paths / owner | Completion boundary |
| --- | --- | --- |
| A: synthetic event ledger only | QD `research/qd007/event_ledger.py`, `tests/test_qd_event_ledger.py`, QD007 role report, ignored synthetic results | Versioned records, fees, snapshot entitlement, pending/posting, reconciliation; literal synthetic matrix passes; no market replay or labels |
| A independent review | QR `research/qr007/validate_event_ledger.py`, `tests/qr_research/test_qr007_ledger.py`, QR role report | Independently reproduce amounts/order/causality and reject rehashed corruptions |
| B: evidence coverage | QR semantic evidence table; QD separately assigned coverage reader/report | Explicitly resolve historical versus scenario basis, missing mark/schedule/arrival/fee inputs; acquisition requires a separate bounded authorization |
| C: research-only strategy adapter | QD `research/qd008/native_adapter.py`, `tests/test_qd_event_replay.py`, QD008 report; exact scope separately reviewed | Reuse current policy functions with ledger-backed causal budgets, no shared runtime edits; authorize any actual replay separately |
| D: target construction | QR separately claimed label module/tests/report; QD reviews ledger consumption | Reviewed target/maturity/censoring and causal splits; authorize label generation separately; no training |

Do not add a framework, database service, dependency or generic exchange adapter.
The pure ledger is the first implementable unit even while historical economics
remain unresolved; fixture success alone does not clear historical label gates.

QD is proposed editor/owner of research event/fill/accounting schema and reducer;
QR owns eligibility, valuation/fee scenarios, attribution/label semantics and
independent acceptance; counterpart review is mandatory. Existing shared-schema
editor remains QD under INTERFACES, with QR semantic review. This research proposal
does not modify it. Any future runtime exposure needs a separate versioned change
request, compatibility tests and user integration approval.

Compatibility/rollback: keep `src/`, native result schema 3, feature version 1,
old immutable datasets and research probe unchanged. New artifacts use distinct
policy/schema identities and output roots. Selecting the old research entry point
retains its old approximation and warnings; selecting no new entry point leaves
the app unchanged. No in-place result conversion, branch merge or deployment is
needed for the proposed synthetic unit. Protocol revisions invalidate dependent
candidate identities and require re-review, never silent relabeling.
