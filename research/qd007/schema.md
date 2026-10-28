# QD007 synthetic event ledger: typed API checkpoint

Status: **READY_FOR_QR_SCHEMA_REVIEW**. Proposal `qd007-synthetic-r1`,
2026-10-28 Australia/Melbourne. No implementation exists at this checkpoint.
QD sole implementation editor; QR financial reviewer and independent validator.
Parent QD: `9bb3c0ec2b57e7154a51e56d795645c273c1308d`.
Semantic authority: QR `c7e9a2492247fa31e216035f87e8bb20cca6e6ad`,
`qf006-proposal-r2`; exact source identities are in the QD007 role report.

## 1. Boundary and transport

Implement a small in-memory, offline synthetic ledger in the future assigned
`research/qd007/event_ledger.py`; no database, exchange client, dependency, file
discovery, automatic output writing or `src` import. Only BTC_USDT/ETH_USDT USDT
linear scenario fixtures; integer contracts. Fractional quantity, conversions,
hedged simultaneous long/short positions and historical-exact execution reject.
This is not evidence that actual BTC/ETH historical quantity precision is integer.
The universe assessment at `52ce1ebeb054abd49c41fc4acbb4c7b7eb41c762` leaves that
to coverage; no symbol expansion is implied.

The exact **local API transport** namespace is `qd007.synthetic-ledger`, version 1.
It refines the accepted qf006 semantics; it is deliberately not a qf006 wire
payload, native registry 1.0.0, envelope v1, model bundle or result schema 3.
There is no implicit native adapter. Local `_us` names always mean microseconds.
Funding eligibility is one record; later final-value revisions and cash postings
are separate records, so no consumer must inspect a future-valued field to find
its own availability. Joining them can later supply a qf006 FundingEvent sidecar;
that exporter is not part of stage 1.

Unknown keys, absent required keys and unsupported tags/versions reject at every
object depth. All table fields are required, including explicit nullable fields.
API accepts built-in Python dict/list/str/int/bool/null corresponding exactly to
strict JSON; no custom number objects, float, Decimal instance, tuple or datetime.
Public finance functions also use these scalar types, returning decimal strings.

## 2. Scalar, null, canonical and identity rules

| Type | Exact definition |
| --- | --- |
| ID | ASCII regex `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}` |
| H | lowercase SHA256, exactly 64 hex characters |
| I / I+ | JSON integer excluding bool, signed 64-bit / strictly positive signed 64-bit |
| Q | integer in [-(2^63-1),2^63-1], excluding bool and zero; positive buy, negative sell |
| T | integer UTC microseconds, excluding bool, range 0..2^63-1 |
| D | decimal **string** matching `[+-]?(0\|[1-9][0-9]*)(\.[0-9]+)?` (the `\|` here denotes regex alternation); max 128 digits, max 64 fractional digits on input; no exponent, whitespace, commas, percent, NaN or Infinity |
| D+ / D0 | D strictly positive / nonnegative |
| Inst | exactly `gate:usdt:BTC_USDT` or `gate:usdt:ETH_USDT` |
| Mode | exactly `SCENARIO` in this profile; reject HISTORICAL_EXACT with OUT_OF_SCOPE_MODE |
| Precision | `seconds`, `milliseconds`, `microseconds`; documents actual synthetic source precision, never invented exchange ordering |

The executable D regex is `^[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?$`.
Normalize D to fixed point, remove leading +, trailing fractional zeros and an
empty decimal point; every representation of negative zero becomes `0`. Reject
leading integer zeros except zero itself. Thus `+0.0700` becomes `0.07`, `1.00`
becomes `1`, `1e-4`, `.1`, `01`, a float and True all reject. No cash quantization
or lossy context rounding occurs in fee, funding, realized PnL, C/T/B/P or E sums.
Use exact integer/rational intermediates or sufficient local Decimal precision
with inexact traps; ambient Decimal settings cannot alter output. Internal/output
derived amounts may exceed input digit bounds and are still exact canonical D.
There are at most 4096 accepted input records per ledger instance; exceeding the
bound rejects, not truncates. This is a fixture limit, not a market capacity claim.

Every nullable record field must be null **iff** `null_reasons` has its exact
top-level field name. Every nonnull field has no entry; no extra reason entries.
Allowed codes: `NOT_APPLICABLE`, `UNKNOWN_RATE`, `UNKNOWN_SOURCE_TIME`,
`UNKNOWN_MAPPING`, `UNKNOWN_MARK`, `UNKNOWN_AMOUNT`, `UNKNOWN_BOOKING`,
`UNKNOWN_FINALITY`, `UNKNOWN_SEQUENCE`, `OPEN_ENDED_SCENARIO`.
The field tables restrict relevant reasons below; outputs additionally use
`STALE_VALUATION`, `UNKNOWN_RESERVES`, `RESTATED_VIEW`, `NOT_MODELED` and
`UNRESOLVED_DEPENDENCY`. Unknown is never represented by numeric zero.

Canonicalization first validates and normalizes scalars. Encode UTF-8 JSON with
sorted object keys, separators `(',', ':')`, ensure_ascii=False, no NaN and **no
terminal newline**. Ordered event/allocation arrays retain their order. Declared
set arrays (instruments, source_refs, assertion kind/ref sets) sort by their full
canonical element bytes and reject duplicates. Hash is SHA256 of these bytes.
No Python repr, pickle, filesystem path or floating tolerance participates.

`content_sha256(record)` hashes the canonical record excluding **only**
`created_at_us` and `source_refs`. This avoids circular source-manifest binding
and makes re-export time irrelevant. Availability/identity, economic fields and
null reasons remain included. A separate full-record hash includes every field
for audit. Different provenance may corroborate the same immutable content;
record it in audit provenance without repeating its economic transition. Never
let a new record_id escape the business-source deduplication key.

Business keys are `(ledger_id, instrument_id, record_type, record_id, revision)`.
For ObligationRevision record_id is obligation_id; for Posting it is posting_id;
for CompletenessAssertion it is assertion_id. For Fill, record_id is fill_id;
FundingSnapshot record_id is funding event ID. Revision chains are independent:
an obligation revision is never a posting revision. Same business key/content is
an idempotent no-op. Different content under the same key quarantines; source
row, record export ID or entry ID cannot make a duplicate cash transition.

## 3. Immutable ledger configuration

`LedgerConfig` has exactly:

| Field | Type / constraint |
| --- | --- |
| namespace, schema_version | `qd007.synthetic-ledger`, integer 1 |
| ledger_id, trajectory_id, scenario_id | ID; one account/trajectory per instance |
| instruments | sorted nonempty unique list[Inst], subset of the two allowed IDs |
| initial_at_us, end_exclusive_us | T; initial < end; all synthetic economic origins lie in this range |
| initial_cash_usdt | D0; no assumed leverage or automatic starting capital |
| allocation_quantum_usdt | D+ equal to a power of 10, input scale <=64; explicit fixture attribution/reporting precision, not venue cash rounding |
| rules | list[Rule], defined below, IDs unique |
| expected_funding_snapshots | list[{instrument_id:Inst,event_id:ID,snapshot_at_us:T,mapping_rule_id:ID}], sorted by instrument/time/event; explicit complete synthetic event list, may be empty |
| source_manifest | SourceManifest below, complete immutable literal-fixture catalogue |

Rule keys: `rule_id:ID`, `kind:fee/funding/multiplier/valuation/sequence/booking/finality`,
`instrument_id:Inst`, `valid_from_us:T`, `valid_to_exclusive_us:T|null`,
`available_at_us:T`, `authority_id:ID`, `parameters:object`, `null_reasons:object`.
Only valid_to may be null, with OPEN_ENDED_SCENARIO. Rules must be available by
initial_at and cover the referenced economic time; overlapping same-kind rules
for an instrument reject. This first profile has immutable scenario rules; dynamic
historical rule discovery/conversions reject rather than being backdated.

Exact `parameters` per kind (all keys required, no others):

- fee: `{role: maker|taker, signed_fraction:D, fee_currency:"USDT"}`. A separate
  rule may serve each role; fee overlaps are keyed additionally by role.
- funding: `{calendar:"explicit_snapshot_list"}`; never infer an 8h grid.
- multiplier: `{base_per_contract:D+, quantity_unit:"contracts"}`.
- valuation: `{price_kind:"MARK", max_age_us:I+}`; no trade-price primary proxy.
- sequence: `{same_time_order:snapshot_before_fills|fills_before_snapshot}`.
- booking: `{policy:"explicit_posting_records"}`; no automatic cash movement.
- finality: `{policy:"explicit_scoped_assertions", authority_id:ID}`; a registered
  fixture authority may issue assertions, not claim real exchange finality.

SourceManifest keys: `namespace:"qd007.synthetic-sources"`, `schema_version:1`,
`fixture_id:ID`, `rows:list[SourceRow]`. SourceRow is exactly
`{source_id:ID,source_row:I+,payload_sha256:H}`; keys source_id/row are unique.
Rows sort by source_id/row. Its canonical hash is the fixture manifest identity.
Record source_refs is nonempty list of exactly
`{manifest_sha256:H,source_id:ID,source_row:I+}`. Every reference must resolve in
this manifest, and its payload_sha256 must equal content_sha256(record).
The catalogue is literal fixture provenance, not an exchange raw-data parser or
proof of historical truth. Its hash excludes no fields; record content hash
excludes source_refs, avoiding recursion. Semantic negative tests must rehash the
literal catalogue too, so a hash check cannot substitute for financial validation.

## 4. Common input envelope

Each record is a **flat object**, common fields plus exactly one type's additional
fields below. Common fields:
`namespace:"qd007.synthetic-ledger"`, `schema_version:1`,
`record_type:Fill|FundingSnapshot|ObligationRevision|Posting|CompletenessAssertion|Valuation|Reserves`,
`record_id:ID`, `revision:I+`, `instrument_id:Inst`, `trajectory_id:ID`,
`scenario_id:ID`, `evidence_mode:"SCENARIO"`, `created_at_us:T`,
`available_at_us:T`, `source_time_precision:Precision`, `source_refs:list[SourceRef]`,
`null_reasons:object` as above. Config IDs must match; created_at is export
metadata, not information time. Unless explicitly a revision type below,
revision must be 1. Record economic time <= available time; no time-unit guesses.

### 4.1 Fill and its derived lots/legs

Additional Fill fields:
`order_id:ID`, `decision_id:ID`, `decision_at_us:T`, `filled_at_us:T`,
`sequence:I+|null`, `signed_contracts:Q`, `fill_price:D+`, `multiplier:D+`,
`multiplier_rule_id:ID`, `fee_fraction:D`, `fee_rule_id:ID`,
`liquidity_role:maker|taker|unknown`, `role_basis:"scenario"`,
`fee_currency:"USDT"`, `fee_obligation_id:ID`.
Null sequence requires UNKNOWN_SEQUENCE; tied fills on one instrument/time require
distinct sequences, otherwise AMBIGUOUS_FILL_SEQUENCE. decision<=filled<=available.
Role unknown rejects UNKNOWN_LIQUIDITY_ROLE; fraction/multiplier must match the
applicable rules. A zero fill is not an event: `fee_cash(0,...)` returns zero,
but a submitted Fill with quantity 0 rejects ZERO_FILL; canceled/rejected orders
belong to later adapter selection records, not fabricated episodes.

Process fills in economic time/sequence. FIFO closes existing opposite lots first;
excess quantity opens the opposite episode; same-side adds open additional lots
in the same episode. New episode_id is `episode:<opening_fill_id>`; new lot_id is
`lot:<opening_fill_id>`. One fill has at most one opening leg, including reversal.
Fill record_id is limited to 96 ASCII characters so derived episode/lot/leg IDs
remain within the common 128-character bound. A same-instrument historical fill inserted before an
already captured eligibility snapshot or earlier processed fill rejects
LATE_ORIGIN_UNSUPPORTED; this profile does not repair uncertain late fill tapes.
Late **fee/funding revisions or cash** after close are fully supported.

The Fill atomically creates its original fee obligation revision 1, total
`T=-abs(q)*multiplier*fill_price*fee_fraction`, allocated by filled quantities
between closing/opening legs. It does **not** post that fee to C. An explicit
Posting in the same or a later batch performs the cash debit once. Immediate-fee
fixtures therefore submit Fill+Posting at the same available time. Fee obligation
ID must be unique and cannot collide with funding IDs. A later ObligationRevision
of this ID must start at revision 2 and link revision 1; the original calculated
fee remains in audit, never a second cash event.

Lot unit ranges are integer `[unit_start,unit_end)` within the opening fill's
absolute quantity, initially `[0,abs(opening_quantity))`; FIFO closes the lowest
remaining units first. This identifies parts that closed before versus after a
snapshot. Output Leg is exactly `{leg_id:ID,action:close|open,episode_id:ID,
signed_contracts:Q,unit_allocations:list[UnitRange],fee_cash_usdt:D}`.
UnitRange is `{lot_id:ID,episode_id:ID,unit_start:I,unit_end:I+}` with
0<=start<end<=initial lot quantity. Closing leg signed quantity is opposite the
old lot direction; opening leg has the new direction. Leg quantities sum to the
fill, leg fees sum to its original fee cash. Leg IDs are `leg:<fill_id>:close`
and/or `leg:<fill_id>:open`; IDs never establish fill or snapshot priority.

### 4.2 FundingSnapshot (eligibility only)

Additional fields: `nominal_settlement_at_us:T|null`, `snapshot_at_us:T`,
`snapshot_sequence:I+|null`, `source_t_seconds:I|null`,
`source_record_at_us:T|null`, `mapping_rule_id:ID|null`,
`obligation_id:ID`, `eligible_ranges:list[UnitRange]`.
Null reasons are UNKNOWN_MAPPING for nominal/mapping, UNKNOWN_SEQUENCE for
sequence and UNKNOWN_SOURCE_TIME for source fields. A null mapping is retained
as unresolved, not matched by flooring source seconds. If source times are known,
both are nonnull and source_record_at_us=source_t_seconds*1_000_000<=available_at.
Later raw source/valuation facts belong to the corresponding revision evidence;
they do not mutate the original snapshot record.

Snapshot ID/time must match the explicit synthetic calendar and rule. Eligibility
must equal the still-held unit ranges at the snapshot using declared tie order;
do not inspect current position at booking. Numeric sequence only resolves known
fill ties; same-time snapshot/fill policy is fixed in the sequence rule. Mapping
unresolved keeps the expected event unqualified and blocks affected new risk;
it cannot produce a zero cash amount or a finality assertion.

For qualified nonempty eligibility, register the obligation with T/P unknown and
latest_revision=null until revision 1 establishes it. There is no zero-valued
claim LedgerEntry. Qualified empty eligibility yields a known zero obligation
with a derived revision 1, no cash Posting required. The zero depends on proven
toy eligibility, not an unavailable rate. A missing expected snapshot at/before a
consumer cutoff makes coverage unresolved; an explicitly empty event list is a
valid no-event fixture. Unrelated closed lots cannot be attached to this snapshot.

### 4.3 ObligationRevision and T/B/P

Additional fields: `obligation_kind:fee|funding`, `origin_id:ID`,
`supersedes_revision:I+|null`, `authority_id:ID`, `rule_id:ID`,
`economic_at_us:T`, `known_at_us:T`, `cumulative_signed_total_usdt:D|null`,
`allocations:list[Allocation]`, `calculation:Calculation|null`.
record_id is obligation_id; revision is its authoritative cumulative revision.
Initial funding revision 1 has null supersedes with NOT_APPLICABLE. Successors
must reference the immediately preceding accepted revision, never skip/reset;
known/available clocks cannot precede the prior revision's respective clocks.
economic<=known<=available. Authority/rule must be registered synthetic context.
Unknown total has UNKNOWN_AMOUNT, allocations=[], calculation=null with
UNKNOWN_AMOUNT; it remains unresolved rather than changing a pending balance to zero.

Allocation is exactly `{allocation_id:ID,episode_id:ID,lot_id:ID,
unit_start:I,unit_end:I+,signed_cash_usdt:D}`. It references the original fill
leg or snapshot range, including closed units. Per parent, ranges cannot overlap,
all eligible units are covered, and signed amounts sum exactly to T. allocation_id
is SHA256 of `[obligation_id,lot_id,unit_start,unit_end]`, unchanged across amount
revisions. A zero parent may have empty allocations only if eligibility is empty.
Allocation ordering is FIFO economic opening order, then unit_start; closing
leg precedes a reversal's opening leg. There is no netting unrelated obligations.

Calculation is either `{kind:"authoritative_total"}` (a literal synthetic billed
total/correction, not proof of rate-to-amount valuation) or exactly
`{kind:"funding_formula",signed_contracts:Q,multiplier:D+,mark_price:D+,
final_rate:D,valuation_at_us:T,valuation_available_at_us:T,
rate_available_at_us:T,valuation_rule_id:ID,multiplier_rule_id:ID}`.
For formula proof, quantity equals signed eligible units, rules/multiplier match,
valuation is not later than snapshot and is fresh under the valuation rule, both
input availability times are <=revision.available_at, and T equals funding_cash
exactly. Known T requires a nonnull Calculation; authoritative_total is a tagged
nonnull object. Only unknown T allows null calculation/UNKNOWN_AMOUNT. Missing/stale mark
cannot be silently replaced with trade price. Later coverage work must separately
establish actual marks/mappings; formula literals prove only arithmetic here.

At a consumer cutoff, T is the latest **available** accepted revision; B sums
available postings. P=T-B, A=max(P,0), L=max(-P,0) per obligation, then sum A/L
separately. Revision changes pending only, cash_delta=0. Missing T leaves P/A/L
unknown for that obligation even if some B is known. Rate revisions cannot imply
cash movement. Earlier as-known state is not rewritten by later revisions.

### 4.4 Posting

Additional fields: `obligation_id:ID`, `signed_amount_usdt:D`,
`booking_at_us:T`, `booking_known_at_us:T`, `booking_basis:"scenario"`,
`booking_rule_id:ID`, `corrects_posting_id:ID|null`, `allocations:list[Allocation]`.
record_id is posting_id, revision must be exactly 1; >1 quarantines as
UNSUPPORTED_POSTING_RESTATEMENT. This bounded API requires established booking
times: null booking rejects UNRESOLVED_POSTING_NOT_APPLIED. Unknown booking is
represented by the retained obligation **without a Posting**, so C/B cannot move
and completeness remains unresolved. This is an explicit local-profile restriction
of the wider qf006 nullable transport, not a guess at an actual cash event.
Null corrects uses NOT_APPLICABLE. Known booking<=booking_known<=available.
Zero transfers reject ZERO_POSTING; zero obligations need no fictitious posting.

Origin/obligation must exist; its T may still be unknown. Every allocation must
match eligible origin ranges, sum to signed amount, and retain old lot/episode
identity after close. A separately evidenced refund/surcharge is a new Posting
with its own clocks, optional corrects link and exact signed amount. Missing
corrects target rejects. Posting does not change T. An available established b
changes C and B by b, pending by -b, so E is unchanged absent another event.
Identical redelivery has no extra entry; changing amount under the same posting
identity conflicts even if an outer export ID/source row is new.

### 4.5 CompletenessAssertion

Additional fields: `supersedes_revision:I+|null`, `authority_id:ID|null`,
`finality_rule_id:ID`, `scope:Scope`, `obligation_revision_refs:list[ObligationRef]`,
`posting_refs:list[PostingRef]`, `asserted_at_us:T`, `known_at_us:T`.
Scope is exactly `{instrument_id:Inst,trajectory_id:ID,episode_id:ID,
event_kinds:list[fill|fee|funding|posting],economic_from_us:T,
economic_to_exclusive_us:T}`. start<end; IDs match the ledger/episode.
Refs are exactly `{obligation_id:ID,revision:I+}` and `{posting_id:ID,revision:1}`.
Null authority uses UNKNOWN_FINALITY and makes the record unusable; an unregistered
nonnull authority rejects UNPROVEN_FINALITY_AUTHORITY. Initial supersedes is
null/NOT_APPLICABLE. Chains and duplicates follow the independent assertion key;
asserted<=known<=available, predecessor knowledge/use clocks cannot move backward.

The half-open origin scope must cover entry and **natural exit**, including exit
fees, and all applicable kinds collectively. It also covers every referenced
obligation's linked postings/corrections outside the origin interval. Refs must
equal the current accepted obligation/posting revision set at the queried
consumer cutoff, with P=0 and no unresolved expected events. Missing coverage,
pending amount or later available revision invalidates latest completeness;
old as-known assertions remain preserved. A later successor is effective only at
its available_at, never at its coverage end, issuance, receipt or export time.
Stage 1 returns coverage/readiness diagnostics, not an EpisodeLabel or target.

### 4.6 Valuation and Reserves

Valuation additional fields: `valuation_at_us:T`, `known_at_us:T`,
`price_kind:"MARK"`, `mark_price:D+|null`, `valuation_rule_id:ID`,
`multiplier_rule_id:ID`. Null mark requires UNKNOWN_MARK; valuation<=known<=available.
For consumer cutoff t, choose latest available mark whose valuation_at<=t;
ties at the same valuation time with different prices require a new explicit
record/revision policy and reject AMBIGUOUS_VALUATION in this bounded profile.
No future mark, trade-price replacement or automatic staleness relaxation.

Reserves additional fields: `effective_at_us:T`, `expires_at_us:T`,
`known_at_us:T`, `reserved_margin_usdt:D0|null`, `reserved_fees_usdt:D0|null`,
`excludes_counted_losses_liabilities_and_posted_fees:bool`.
Null reserve uses UNKNOWN_AMOUNT; effective<=known<=available<expires, flag
must be true or DOUBLE_COUNTED_RESERVES rejects. Select latest available reserves
per instrument valid at t; unknown/expired reserve blocks increased risk.
These are explicit synthetic reserved amounts, not recomputed Gate margin.

## 5. Arithmetic, FIFO attribution and balances

Public pure functions (no mutable ledger or application dependencies):

```text
canonical_bytes(value) -> bytes
content_sha256(record) -> str
seconds_to_us(value: int|str) -> int
fee_cash(quantity: int, multiplier: str, fill_price: str, fee_fraction: str) -> str
funding_cash(signed_contracts: int, multiplier: str, mark_price: str, final_rate: str) -> str
realized_pnl(signed_closed_contracts: int, multiplier: str, entry_price: str, exit_price: str) -> str
allocate_pro_rata(total: str, weights: list[int], quantum: str) -> list[str]
```

seconds_to_us rejects bool/float and any fractional microsecond; exact multiply
by 1_000_000, no flooring/rounding. 24h=86_400_000_000us. Functions validate all
scalar domains even if quantity is zero. fee_cash=-abs(q)*m*price*r;
funding_cash=-Q*m*mark*r; realized_pnl=Q_closed*m*(exit-entry), Q_closed signed
in the **old lot direction**. No leverage factor or extra slippage deduction.
All nonzero multipliers/prices are positive; fee/rate signs remain signed.

Explicit precision detail for QR review: allocate_pro_rata uses exact rational
shares, HALF_EVEN to the configured allocation quantum for all but the final
nonzero-weight slice, and exact remaining residual for the final slice. Weights
are positive integer unit counts; empty weights permit only total=0. Cash/parent
T is never rounded. Example total=0.01, weights=[1,1,1], quantum=0.0001 yields
[0.0033,0.0033,0.0034]. A zero-weight/negative-weight variant rejects, not silently
drops a party. If rounding makes any slice, including the residual, opposite in
sign to its nonzero parent or larger in magnitude than that parent, reject
ALLOCATION_QUANTUM_TOO_COARSE before mutation; never invent a fee credit.
This formalizes the accepted reporting-quantum/final-residual rule;
it is not venue settlement rounding. QR must review this precision choice before
implementation. Partial FIFO closes split the **remaining attributed amount**
by closed/remaining units, preserving its final residual. Snapshot-range overlap
determines which closed slices receive funding; units closed before snapshot
receive none. Late corrections create new attribution versions, not edits to
previously observed slice snapshots. No account cash is debited a second time.

LotState exactly: `{lot_id,episode_id,instrument_id,opening_fill_id,opened_at_us,
direction:long|short,initial_contracts:I+,remaining_contracts:I,
entry_price:D+,multiplier:D+,live_ranges:list[UnitRange],closed_slice_ids:list[ID]}`.
ClosedSlice exactly: `{slice_id,lot_id,episode_id,closing_fill_id,closed_at_us,
unit_start:I,unit_end:I+,realized_price_pnl_usdt:D,entry_fee_cash_usdt:D,
exit_fee_cash_usdt:D,funding_cash_usdt:D|null,attribution_revision:I+}`;
unknown funding carries reason in the containing snapshot's null_reasons map,
keyed by `closed_slices/<slice_id>/funding_cash_usdt`.
Closed lots/slices remain addressable. No averaged-entry division is necessary.

BalanceSnapshot exactly: `{as_of_us:T,view:as_known|restated,
knowledge_cutoff_us:T,cash_usdt:D,receivables_usdt:D0|null,
liabilities_usdt:D0|null,unrealized_usdt:D|null,economic_equity_usdt:D|null,
reserved_margin_usdt:D0|null,reserved_fees_usdt:D0|null,
simulated_budget_usdt:D|null,actual_available_margin_usdt:null,
new_risk_supported:bool,reductions_supported:bool,valuation_refs:list[ID],
reserve_refs:list[ID],null_reasons:object}`.
E=C+A-L+U, budget=C-L+min(U,0)-reserves, never add A/unrealized gains. Flat
instruments have U=0 without a mark; held lots need a fresh causal mark and
unchanged scenario multiplier. Missing/stale U, unresolved scheduled funding,
unknown liabilities/reserves/rules yield null budget and new_risk_supported=false.
Known budget<=0 also means false; positive budget alone is not an order approval.
Actual margin is always null/NOT_MODELED. Reductions are supported when the
position inventory is internally valid; unknown costs do not erase exits.

## 6. Transactions, information views and public inspection API

```text
validate_record(record: dict) -> dict                 # normalized deep copy, pure
Ledger(config: dict)
Ledger.apply_batch(records: list[dict]) -> Receipt
Ledger.snapshot(as_of_us: int) -> Snapshot
Ledger.restated(economic_at_us: int, knowledge_cutoff_us: int) -> Snapshot
Ledger.readiness(episode_id: str, as_of_us: int) -> Readiness
Ledger.audit() -> Audit
```

No hidden wall clock, filesystem, global patch, API key or environment variable.
Construction validates immutable config and catalogue; snapshots never change
records. Batch input order is not an exchange sequence. Normalize/check complete
batch, resolve existing/in-batch origins and revision dependencies, then evaluate
on a private candidate state before one commit. Semantic event order is declared
economic time/sequence for fill/snapshot inventory, and consumer available time
for obligations/postings. Equal-time inventory uses the fixed scenario tie rule;
dependencies precede dependents at equal available time, with stable record keys
only as serialization tiebreakers for independent events. Cycles, dangling origins,
backward revision clocks and late origins affecting captured eligibility reject.

No batch prefix may mutate cash, lots, accepted IDs, revisions, committed journal
or their hash on failure. Exact duplicate transactions succeed as no-ops; new
corroborating provenance is audit-only. Conflicting identities or other invalid
records cause an atomic rejection with `LedgerError(code, json_pointer,
recoverable_identity, input_sha256|null, incumbent_sha256|null,
committed_sha256, disposition:reject|quarantine)`.
The engine retains a separate **run-integrity failure receipt**, with no financial
transition. It then refuses further apply/snapshot/readiness with INTEGRITY_STOPPED;
audit remains available. There is no reset or last-write-wins recovery API: use
a new instance with separately corrected/approved inputs. Thus conflict blocks
finality, while committed financial state remains byte-identical; compare
audit.committed_state, not the out-of-band failure receipts, for rollback tests.
Pure validate_record failure has no ledger to latch. Legitimate unknown amounts
are valid unresolved states, not integrity failures.

Receipt exactly: `{status:applied|duplicate,applied_keys:list[Key],
duplicate_keys:list[Key],corroborated_keys:list[Key],entries:list[LedgerEntry],
committed_before_sha256:H,committed_after_sha256:H}`. Key is
`{instrument_id,record_type,record_id,revision}` within this ledger config.
LedgerEntry exactly: `{entry_id:H,source_key:Key,transition:fee_claim|funding_claim|
cash_posting|realized_pnl,allocation_id:H|null,episode_id:ID|null,
economic_at_us:T,available_at_us:T,cash_delta_usdt:D,
receivable_delta_usdt:D,liability_delta_usdt:D,realized_pnl_usdt:D}`.
Null allocation/episode is allowed only for an empty-eligibility zero claim,
with null reasons supplied by the receipt's normalized source record context.
Unknown obligation totals produce no numeric entry. Delta splits of A/L handle
sign changes without netting independent obligations. Entry ID hashes source key,
transition and allocation; an arbitrary entry_id cannot bypass input deduplication.

snapshot(t) includes only record/revision inputs available<=t and economic
origins<=t; no future fields or final totals leak into C, P, inventory or U.
State hash excludes future journal contents and export timestamps. It includes
the fixed scenario/config identity (provenance, not a model feature). Changing a
future revision cannot change any past decision snapshot. Unsupported late origin
reconstruction rejects; the later replay adapter must separately address fills
and pending orders under its approved execution policy.

restated(e,k), with k>=e, projects the inventory and economic origins at e using
revisions known/available by k; cash is explicitly the retrospective booking-at<=e
view, allowing late-discovered postings. It never overwrites snapshot(e).
Restated budget is null/RESTATED_VIEW and new_risk_supported=false: this API is
for audit only and cannot feed order budgets or historical decision features.

Snapshot exactly: `{namespace,schema_version,profile:"qd007-synthetic-r1",
ledger_id,trajectory_id,scenario_id,view,as_of_us,knowledge_cutoff_us,
balances:BalanceSnapshot,lots:list[LotState],closed_slices:list[ClosedSlice],
obligations:list[ObligationState],state_sha256:H}`. ObligationState exactly:
`{instrument_id,obligation_id,kind:fee|funding,origin_id,latest_revision:I+|null,
T_usdt:D|null,B_usdt:D,P_usdt:D|null,A_usdt:D0|null,L_usdt:D0|null,
allocation_refs:list[H],posting_refs:list[Key],null_reasons:object}`.
Snapshot also requires null_reasons:object for nested output null paths.
state_sha hashes the snapshot without state_sha256. Lists sort by business keys,
except FIFO lots/slices which sort by opening/closing economic key then unit_start.

Readiness exactly: `{episode_id,as_of_us,natural_exit_at_us:T|null,
status:open|immature|complete|invalid,complete_at_us:T|null,
assertion_refs:list[Key],blocking_reasons:list[str]}`. complete is **synthetic
cash/coverage readiness**, not an emitted valid training label. It requires
natural flat, latest available revision refs, all relevant kinds/exit covered,
P=0 and no unresolved expected events. complete_at is max of exit and required
input/posting/assertion consumer availability. Null assertion authority yields
invalid readiness and is unusable;
unregistered asserted authority is an integrity rejection. Supersession never
rewrites earlier readiness. Censoring/targets/fold train eligibility remain stage 4.

Audit exactly: `{namespace,schema_version,profile,ledger_id,config_sha256:H,
source_manifest_sha256:H,committed_sha256:H,committed_state:object,
integrity:clean|stopped,failure_receipts:list[object]}`. committed_state exactly
`{config:LedgerConfig,records:list[normalized records],derived_entries:list[LedgerEntry],
corroborating_source_refs:list[object]}`; records sort by business key. Its hash
covers this full committed representation. Source provenance additions may change
committed_sha while leaving every financial snapshot state_sha unchanged.
All returned structures are deep copies; mutation by a checker cannot mutate
the ledger. Full audit reveals future fixture inputs; it is never a feature API.
Each corroborating_source_refs object is exactly `{key:Key,source_ref:SourceRef}`;
each failure_receipt has exactly the LedgerError fields specified above.

## 7. Stage-1 acceptance and explicit deferrals

No QF006 criterion is implemented or PASS at this checkpoint. Proposed accounting
test obligations after QR review, retaining all A IDs:

| IDs | Stage-1 proof / boundary |
| --- | --- |
| A01,A02,A04,A05,A07,A09-A14,A17,A18-A20 | Synthetic fee/funding/FIFO/clock/budget/revision/idempotency/atomicity proofs through this public API, literal independent oracles; no market truth claim |
| A03,A06 | Zero-fee math for zero fill and rejection of fabricated zero Fill; explicit no-event calendar. Full order cancellation/selection integration is deferred |
| A08,A15,A16,A31-A33 | Mode/type/dependency rejection only; exact historical sequence/mark/rule/conversion/calendar evidence remains stage 2 and is not proven by rejecting out-of-profile inputs |
| A21,A29 | Synthetic coverage/readiness and latest assertion/unknown-finality behavior only; actual EpisodeLabel export and market maturity remain stage 4 |
| A22 | Exact seconds/us conversion and 24h constant only; fold purge/cross-asset train eligibility deferred to stage 4 |
| A23,A25,A26,A28 | Deferred: fold/selection/stateful policy replay, exposed-test/preprocessing/permission workflow; no fake implementation PASS |
| A24 | FIFO adds, gross price PnL and inventory/entry notional arithmetic; denominator/target serialization and training-row count verified later by the exporter |
| A27 | Namespace/version rejection and native files unchanged; no production adapter coverage |
| A30 | Synthetic MARK freshness checks; obtaining/qualifying actual mark data is deferred |
| A34 | Realized PnL uses actual synthetic fill price once; full execution/slippage path remains later replay work |

Producer tests additionally require: bool/float/percent/exponent/wrong unit
rejection; ambient Decimal-context independence; fractional microsecond rejection;
future perturbation/past hash invariance; eligible **unit-range** attribution after
partial pre-snapshot close; unsupported posting restatement; revision gaps/cycles;
rehash-semantic corruption; batch [good,bad] rollback and integrity stop; deep-copy
inspection; reordering independent batches with identical economic results.
QR supplies literals and uses the public API; expected values must not call QD
finance/allocation helpers. Missing source files or unknown actual market evidence
are dependencies, not reasons to create a downloader or expand the namespace.

Checkpoint stops at schema review. Code/tests require the coordinator's exact QR
review handoff. No real-data intake/replay/labels, model/scaler fitting, runtime
migration, risk-default change, merge, deployment or scheduler is authorized here.
