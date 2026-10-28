# QF009: versioned offline streaming ledger contract proposal

2026-10-28 Australia/Melbourne. Revision `qd009-contract-amendment-r1`.
Task `QF-QD-009-CONTRACT-AMENDMENT-R1`;
dispatch `QF-DISPATCH-20261028-QD009-CONTRACT-AMENDMENT-R1`.
**READY_FOR_QR_CONTRACT_REVIEW — proposed, not accepted or implemented.**
Author/implementation owner QD; financial/provenance reviewer and independent
oracle owner QR; integration requires separate coordinator/user approval.
Worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, clean base `89cf347482c8121a4e3da559c6fb639a30788d6f`.
Only this file is allocated now. No implicit implementation/test/output claim.

This supersedes the *proposal* at19cd4c7 (SHA256
`36a7b157cdba45692b6737ba465d7b2bf4e29b9d2a012a52b67d454fb1c02ac7`),
which remains intact in Git. Review inputs: QR4d4e530
`research/qr009/streaming-ledger-review.md`, SHA256
`a141bbf5ed69663b2db29ba0c7acffd41712c730eb0c0ce08ad166e6efa8578e`;
QD89cf347 engineering report, SHA256
`8ca4301e21aa599f97fde432695a5b40bfbcb8a58e03751f089430e2d3325e3e`.
No moving QR r2 draft was read. This amendment addresses only RV01–RV04 and
transport/lifecycle links R03/R05; QR owns native callback/partial-sizing and
research scenario choices. No reviewed proposal is an implementation permission.

## 1. Authority, boundary and compatibility

Reference QD007 code `0ea2d51901689a351068bb9d33906c3240832afa`, SHA256
`7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`;
r3 schema SHA `7fd7df5f84a8822f5fdd37243d24e0eb293d9eeacda17514c8b1f1ad04ac475a`.
QR007 `e2211a20bb0919b77506328e68867ff9357ec6c3` accepted that exact implementation
as PASS_SYNTHETIC_ONLY; it did not accept this proposal. Preflight d90e368 report
SHA `b156f6fc7bcdda0a93af3e2ad0d9476815b4186ffdcf29b8ec1fd484e8b395a5` identifies
the capacity/source-binding issues. Coordinator funding-lineage evidence SHA
`176d0c987d23d4b29b7f901b7dfaa6eeffe56ad84bc57ee07f89a261dab65be5` supports raw
lineage only; it neither supplies a converted event table nor proves arrival.

Propose namespace `qf009.streaming-ledger`, schema_version2, profile
`qf009-offline-stream-r2`. Separate from qd007.synthetic-ledger/r3, qf006/native
interfaces, result schema3 and feature version1. Scope: one scenario/account/
trajectory, BTC/ETH USDT linear, integer contracts, exact arithmetic and a controlled deterministic adapter port.
Initial implementation acceptance uses synthetic contract tests; the port contract
also explicitly targets the separately reviewed native replay bridge. No market runner, signals, order/capacity simulator,
MARK scanner, feature adapter, label exporter, fitting or deployed storage.
The streaming mechanism can later support R3 after separately reviewed adapters;
this profile is not HISTORICAL_EXACT or a claim of real available margin.

| r3 surface | Proposed difference / compatibility rule |
| --- | --- |
| Complete literal payload source_manifest | Frozen raw/fact catalogue plus verified append-only generated registry; no precomputed future Fill catalogue or private `_sources` mutation. |
| Flat record namespace/version/created_at/source_refs | FinancialBody below omits exactly these four transport fields; a new Envelope supplies version/provenance/created time. Other financial fields and nullable meanings remain. Explicit import conversion only; native/r3 objects are rejected as new envelopes. |
| apply_batch, implicit full candidate reconstruction | Atomic advance with a frozen complete tick/slot plan, compare-and-swap prefix and transaction identity. Reference-import mode preserves r3 event admission; generated mode adds checked causal witnesses. |
| Snapshot contains entire historical lists | Summary plus pinned paged components. No historical item discarded. Full materialization is a bounded explicit page traversal; r3 comparison reconstructs lists for small fixtures. |
| One microsecond cutoff | Public final-at-time view plus optional completed-slot cutoff for generated witnesses; r3 differential comparison uses final-at-time only. No invented exchange subsecond sequence. |
| No sealed availability frontier | New advance seals through_us even when no tick occurs; reject backdated new deliveries behind it. Differential reference tapes are availability-ordered, not arbitrary late insertion into a previously queried r3 subset. Financial rules remain equal within that common domain. |
| Whole Snapshot SHA | New domain-separated summary/component-root hash; not advertised equal to r3 state_sha256. Differential tests compare expanded financial fields and r3's reconstructed preimage separately. Audit roots are excluded. |
|4096 accepted-input ceiling | r3 stays unchanged. New implementation must maintain indexed persistent history, bounded workset/output and explicit byte/time limits; no all-history record-count reset or silent truncation. |
| No checkpoint/restore | New validated immutable checkpoint and commit protocol. Restoring does not create fresh cash, drop old claims or revise prior knowledge. |

Rollback is leaving this separate entry point unused; no migration of old data.
No live/native consumer may auto-select it. Unapproved market slippage, capital,
reserves, feedback and capacity are not selected here. Approved fee/funding/MARK/
multiplier choices need no new user question; their later typed scenario binding
is outside this synthetic infrastructure proposal.

### Amendment/version rejection table

| Review item | Old proposal -> this proposal | Compatibility / acceptance link |
| --- | --- | --- |
| RV01 | Roots plus own state -> typed economic selections, durable order status and explicit per-role selectors/read bindings (§4.1) | Changed AdapterDefinition/Input/Result/State/Generated and economic components; schema2/profile-r2 only. Independent P/X/environment fixtures S02/S04. |
| RV02 | Ambiguous pre-genesis facts -> InitialContext plus one-time original-clock prefix receipt/cursors (§3.1) | Config/Checkpoint change; financial origin range unchanged. S03/S09. |
| RV03 | Readable HEAD resolution -> lease/barrier/readback/reachable-request proof and persistent control guard/stops (§5.1,§7) | New control rows/files and checkpoint binding; no old-store open/import. S08/S09. |
| RV04 | Open-ended S01–S13 variants -> finite named S01–S12 manifest; S13 explicitly later (§8.1) | Initial limits unchanged; neither missing S13 nor unexecuted cases count as PASS. |
| R03/R05 link | Unspecified end/fact consumption -> expiry/noop tail and qualified fact/consumer-clock rules (§3.2,§4.2) | No added r3 FinancialBody fields or post-cutoff origin exception; external native/query schemas still required. |

Every streaming Envelope/CreateRequest/Checkpoint must use schema_version2 and
profile-r2. Profile-r1 objects reject UNSUPPORTED_VERSION; r3/qf006/native objects
reject UNSUPPORTED_NAMESPACE, with no field inference or automatic upgrade. Mixed
schema/profile/files reject CHECKPOINT_MISMATCH on restore. Internal format_version2
files have a new run/store identity; never rewrite an existing profile-r1 store.
RawCatalogue's inventory namespace/schema1 and the financial r3 meaning remain
unchanged. New hash-domain versions below prevent cross-profile witness reuse.
No producer/consumer has migrated: this is a one-file unimplemented proposal.

## 2. Types and exact financial payloads

All objects below are **closed**; all fields required. Arrays retain order unless
explicitly called sets. Reject extra/missing keys, wrong types, unsupported tags,
floats, bool-as-number, exponent/percent strings and implicit time conversion.

| Alias | Definition |
| --- | --- |
| ID | ASCII `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}`; Fill IDs <=96 chars |
| H | Lowercase64-hex SHA256 |
| I / I+ | JSON integer excluding bool,0..2^63-1 /1..2^63-1 |
| SI / Q | Integer -(2^63-1)..2^63-1; Q additionally nonzero; signed buy/sell contracts |
| T | I measured in UTC Unix microseconds; duration fields ending_us also microseconds |
| D / D0 / D+ | Signed exact decimal string, regex `[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?`; max128 input digits/64 fractional digits; nonnegative/positive restrictions for D0/D+. Canonical output removes plus/trailing fractional zeros and negative zero; never rounds cash. Derived values may exceed input digit bounds, subject to exact-integer resource limits. |
| Inst | `gate:usdt:BTC_USDT` or `gate:usdt:ETH_USDT` |
| Precision | seconds / milliseconds / microseconds, preserving actual input precision |
| ReasonMap | Object from exactly the directly null field names to allowed reason strings. Nonnull fields have no entry; no nested/root duplication. |
| Key | `{instrument_id:Inst,record_type:Kind,record_id:ID,revision:I+}` within account/trajectory |
| Cutoff | `{at_us:T,slot:I}` always retains the actual requested time. In controlled-adapter mode at a scheduled tick, slot0 is after fact release/before its adapter slots; slots1..N are completed slots and final-at-time is slotN. At a non-tick time only slot0 is valid and means final-at-that-actual-time. Reference-import mode uses only slot0, including all accepted records available by that actual time. No snapping to an earlier tick or invented exchange sequence. |
| UnitRange | `{lot_id:ID,episode_id:ID,unit_start:I,unit_end:I+}`, start<end |
| Allocation | `{allocation_id:H,episode_id:ID,lot_id:ID,unit_start:I,unit_end:I+,signed_cash_usdt:D}` |

Canonical bytes: normalized UTF-8 JSON, sorted keys, separators comma/colon,
ensure_ascii=False, allow_nan=False, no terminal LF for hash preimages. JSONL adds
one LF to each canonical object; file hashes include LF. Declared set arrays sort
by full canonical element bytes and reject duplicates. No pickle/repr/tolerance.
Exact Fraction numerator/denominator arithmetic; a wire D must terminate. Allocation
uses exact rational share, HALF_EVEN at configured power-of-ten quantum for all
but final slice, then exact residual; reject opposite-sign/excess residual.
Recompute corrections along the original remaining-FIFO closing path. No ambient
Decimal28 rounding, changed quantum, float sums or new cash rounding rule.

FinancialBody common fields exactly:

```text
record_type:Kind, record_id:ID, revision:I+, instrument_id:Inst,
trajectory_id:ID, scenario_id:ID, evidence_mode:"SCENARIO",
available_at_us:T, source_time_precision:Precision, null_reasons:ReasonMap
```

Kind and its exact additional fields:

| Kind | Additional fields |
| --- | --- |
| Fill | order_id:ID, decision_id:ID, decision_at_us:T, filled_at_us:T, sequence:I+ or null, signed_contracts:Q, fill_price:D+, multiplier:D+, multiplier_rule_id:ID, fee_fraction:D, fee_rule_id:ID, liquidity_role:maker or taker, role_basis:"scenario", fee_currency:"USDT", fee_obligation_id:ID |
| FundingSnapshot | nominal_settlement_at_us:T or null, snapshot_at_us:T, snapshot_sequence:I+ or null, source_t_seconds:I or null, source_record_at_us:T or null, mapping_rule_id:ID or null, obligation_id:ID, eligible_ranges:list[UnitRange] |
| ObligationRevision | obligation_kind:fee or funding, origin_id:ID, supersedes_revision:I+ or null, authority_id:ID, rule_id:ID, economic_at_us:T, known_at_us:T, cumulative_signed_total_usdt:D or null, allocations:list[Allocation], calculation:Calculation or null |
| Posting | obligation_id:ID, signed_amount_usdt:D, booking_at_us:T, booking_known_at_us:T, booking_basis:"scenario", booking_rule_id:ID, corrects_posting_id:ID or null, allocations:list[Allocation] |
| CompletenessAssertion | supersedes_revision:I+ or null, authority_id:ID or null, finality_rule_id:ID, scope:Scope, obligation_revision_refs:set[ObligationRef], posting_refs:set[PostingRef], asserted_at_us:T, known_at_us:T |
| Valuation | valuation_at_us:T, known_at_us:T, price_kind:"MARK", mark_price:D+ or null, valuation_rule_id:ID, multiplier_rule_id:ID |
| Reserves | effective_at_us:T, expires_at_us:T, known_at_us:T, reserved_margin_usdt:D0 or null, reserved_fees_usdt:D0 or null, excludes_counted_losses_liabilities_and_posted_fees:bool=true |

```text
Calculation = {kind:"authoritative_total"}
  | {kind:"funding_formula",signed_contracts:Q,multiplier:D+,mark_price:D+,
     final_rate:D,valuation_at_us:T,valuation_available_at_us:T,
     rate_available_at_us:T,valuation_rule_id:ID,multiplier_rule_id:ID}
Scope = {instrument_id:Inst,trajectory_id:ID,episode_id:ID,
         event_kinds:set[fill|fee|funding|posting],economic_from_us:T,
         economic_to_exclusive_us:T}
ObligationRef = {obligation_id:ID,revision:I+}
PostingRef = {posting_id:ID,revision:1}
```

Input null reasons: Fill.sequence and snapshot_sequence UNKNOWN_SEQUENCE;
nominal_settlement/mapping_rule UNKNOWN_MAPPING; source_t/source_record together
UNKNOWN_SOURCE_TIME, otherwise source_record=seconds*1000000. Initial supersedes
and corrects_posting use NOT_APPLICABLE. Unknown cumulative total/calculation use
UNKNOWN_AMOUNT together, allocations=[]; known total requires Calculation. Null
assertion authority uses UNKNOWN_FINALITY; mark_price UNKNOWN_MARK; reserve fields
UNKNOWN_AMOUNT. Posting clocks/amount are never null; no zero Posting or zero Fill.
Unknown booking means retained obligation without Posting, not a null cash event.

Financial invariants are normative, not merely comments for the later adapter:

- Economic/decision/known/available inequalities and rule coverage equal r3;
  revision/authority chains cannot skip, rewind or silently repair an old origin.
  All kinds except ObligationRevision/CompletenessAssertion have revision1.
  Posting restatement>1 quarantines; actual refund/surcharge is a new signed Posting.
- Fill creates fee T=-abs(q)*m*price*fee_fraction but no automatic C debit. Funding
  is -eligible_signed_q*m*qualified_MARK*rate, no leverage/time proration. Snapshot
  captures exact FIFO unit ranges at its economic/tie position. Qualified empty
  eligibility is known zero; absent/mapping-null snapshot or unknown nonempty T
  stays unresolved. Mapping-null snapshot remains unqualified, as r3.
- T is latest available cumulative total; B sums independent available postings;
  P=T-B, A=max(P,0), L=max(-P,0) **per obligation**, aggregate A/L separately.
  Posting changes C/B even if T unknown; conditional pending deltas stay null when
  before/after is unknown. Revisions alone never move C. Unknown is never zero.
- FIFO realization/fee splits, partials/reversal, late allocations to closed lots,
  B1 local nullable entry/exit fees, exact remaining-residual paths and immutable
  old attribution versions equal r3. Formula mark_available<=snapshot and maximum
  age, rate/mark known-time constraints are unchanged; no posthoc trade-price proxy.
- C/A/L/U/E are exact; E=C+A-L+U, budget=C-L+min(U,0)-margin_reserve-fee_reserve.
  No spendable A/positive U; no duplicated posted costs. Unknown/stale required
  inputs give null budget and new_risk_supported=false. Reductions remain supported
  for consistent inventory; this is not a fill guarantee or real margin model.
- Assertions are admitted independently of current sufficiency. At query select
  available heads, complete half-open natural-exit scope/all current references,
  P=0 and qualified calendar coverage. Stale legal assertions cause immature
  readiness, not integrity stop. Successor replaces a null-authority head; it
  cannot inherit earlier finality. No EpisodeLabel or training target is emitted.
- Global owner(kind,ID)=(instrument,trajectory,scenario), including derived
  fee/episode/lot/leg IDs, survives all checkpoints. Different source/outer IDs
  cannot evade business dedup or transfer a cash/lot/reference to another coin.

## 3. Configuration and two independent provenance layers

CreateRequest exactly `{namespace, schema_version, profile, request_id:ID, config:Config,
raw_catalogue:RawCatalogue, fact_store:SourceFileRef,
source_roots:list[{root_id:ID,path:str}],store_root:str}`. Envelope header
values are the literals above. A new exclusive local directory, symlink/path
confinement and dedicated single-writer OS lease are required; no network store.

```text
Config = {
 ledger_id:ID,trajectory_id:ID,scenario_id:ID,instruments:set[Inst],
 initial_at_us:T,end_exclusive_us:T,knowledge_end_exclusive_us:T,initial_cash_usdt:D0,
 allocation_quantum_usdt:D+,rules:list[Rule],
 expected_snapshots:list[ExpectedSnapshot],ingestion_mode:reference_import|controlled_adapters,
 adapters:list[AdapterDefinition],initial_adapter_states:list[AdapterState],
 schedule:list[Tick],fact_schemas:list[FactSchema],initial_context:InitialContext,
 limits:Limits,random_source:"NONE"
}
ExpectedSnapshot = {instrument_id:Inst,event_id:ID,snapshot_at_us:T,mapping_rule_id:ID}
Rule = {rule_id:ID,kind:fee|funding|multiplier|valuation|sequence|booking|finality,
 instrument_id:Inst,valid_from_us:T,valid_to_exclusive_us:T or null,
 available_at_us:T,authority_id:ID,parameters:RuleParameters,null_reasons:ReasonMap}
```

Rules available by initial_at; valid_to null=OPEN_ENDED_SCENARIO. Nonoverlapping
kind/instrument windows (fee additionally role); immutable scenario parameters:
fee `{role:maker|taker,signed_fraction:D,fee_currency:"USDT"}`;
funding `{calendar:"explicit_snapshot_list"}`;
multiplier `{base_per_contract:D+,quantity_unit:"contracts"}`;
valuation `{price_kind:"MARK",max_age_us:I+}`;
sequence `{same_time_order:snapshot_before_fills|fills_before_snapshot}`;
booking `{policy:"explicit_posting_records"}`;
finality `{policy:"explicit_scoped_assertions",authority_id:ID}`.
No contract conversions, fractional tickets, hedged legs, automatic funding clock
transforms or default numerical rule values. Caller must explicitly supply the
synthetic fixture's parameters. Expected snapshots are complete, unique and paged
on disk if necessary; only due entries influence current coverage.
Adapter IDs/slot IDs are unique; one initial typed AdapterState per adapter is
required (an explicitly validated empty object for a stateless port). Reference-
import mode requires adapters/initial_adapter_states empty. Initial state is a
predeclared causal input, not a later reconstruction from future outcomes.
Require initial_at<end_exclusive<=knowledge_end_exclusive. Economic origins of
Fill/FundingSnapshot/Valuation/Reserves and revision economic times obey the r3
economic range. Later knowledge/Postings/assertions may lie before the separately
declared knowledge end; this does not license later market origins. Tick times
strictly increase within the knowledge window, phase values are nondecreasing
within each tick and slot IDs are unique globally. through_us must remain before
knowledge_end_exclusive. All scheduled work and known fact availability are within
that bound. A real post-cutoff evidence window still needs its own R3 approval;
this required synthetic configuration field does not choose or extend one.

```text
FileRef = {relative_path:str,sha256:H,bytes:I,rows:I}
SourceFileRef = {root_id:ID,relative_path:str,sha256:H,bytes:I,rows:I}
RawCatalogue = {namespace:"qf009.raw-catalogue",schema_version:1,catalogue_id:ID,
 objects:list[RawObject],fact_store:SourceFileRef,qualification_ref:H}
RawObject = {object_id:ID,root_id:ID,instrument_id:Inst,sha256:H,bytes:I+,relative_path:str,
 format:synthetic_jsonl|qualified_external,source_row_basis:physical_line|json_element,
 original_time_unit:seconds|milliseconds|microseconds,
 retrieved_at_us:T or null,null_reasons:ReasonMap}
RawRef = {object_id:ID,raw_sha256:H,source_row:I+}
FactSchema = {schema_id:ID,kind:price|mark|rate|billed_total,
 view_kind:closed_bar|execution_open|mark_point|mark_selection|funding_rate|billed_total|synthetic_price,
 interval_us:I,
 fields:list[{name:ID,type:D|D0|D+|I|SI|T|bool|ID,unit:USDT|contracts|
             USDT_per_base|fraction|UTC_microseconds|none}]}
Cell = {tag:"known",type:ScalarTag,value:Scalar}
     | {tag:"unknown",type:ScalarTag,reason:Reason}
Fact = {fact_key:ID,instrument_id:Inst,schema_id:ID,economic_at_us:T,
 scenario_available_at_us:T or null,observed_first_available_at_us:T or null,
 cells:list[{name:ID,cell:Cell}],raw_refs:set[RawRef],null_reasons:ReasonMap}
```

RawObject.retrieved_at null reason UNKNOWN_RETRIEVAL; Fact scenario-available null
UNRESOLVED_AVAILABILITY, observed-first null HISTORICAL_FIRST_AVAILABILITY_UNKNOWN.
Cell reasons are UNKNOWN_RATE/MARK/AMOUNT/SOURCE_TIME/MAPPING/FINALITY as appropriate
to its typed field. Known value must obey its scalar type/unit; there are no
null Cells and no empty/zero replacement for unknown. Fields/values match exactly
the frozen schema. available facts need economic<=scenario_available. Future/
unresolved facts remain in the immutable store but cannot enter an adapter input packet.

Fact_key is a stable scoped semantic key from the qualified source mapping, not
full-catalogue/raw-file hash, directory position or retrieval timestamp. A valid
future-only raw mutation may change earlier raw_refs/audit identities but preserves
the unchanged earlier keys, cells and clocks. Raw refs must resolve/hash-check;
fact store bytes and qualification identity are frozen before create. This kernel
does not decode MARK/market archives: external qualification is a **separate
required QR gate**, not something proved by catalogue shape. Initial implementation
fixtures use synthetic JSONL. Fact schemas cannot smuggle strategy intent/order
quantity/seed/decisions in as trusted market facts. No unregistered callback or automatic raw loader.

Source roots have unique IDs and are read-only; object/fact paths are normalized
relative paths under their exact declared root, with no symlink/traversal/absolute
escape or unlisted file discovery. CreateRequest.fact_store must exactly equal
RawCatalogue.fact_store. Source roots need not be copied into store_root, and
their filesystem names are audit-only. Only qualified immutable public/synthetic
inputs are eligible; never credentials, real configs or account files.

Reference-import mode substitutes the following closed row type for Fact:
`ReferenceFact={fact_key:ID,instrument_id:Inst,body:FinancialBody,
scenario_available_at_us:T,raw_refs:set[RawRef]}`. It binds the complete normalized
FinancialBody to a synthetic literal source row before create; availability must
equal body.available_at_us and instrument must match. The entire fact store is
ReferenceFact rows in this mode, not an undocumented Cell type or mixed schema.
It has no adapters and cannot be used as a market-fill causality bypass. This is
an explicit differential-test-only import profile.

Full catalogue hash=H(canonical RawCatalogue). Full config hash includes that
catalogue and store/resource metadata and is audit-only. Causal policy hash covers
only initial account/scenario/rules/calendar/adapter/schedule/fact-schema semantics,
excluding limits, paths, raw/fact hashes, qualification/retrieval metadata. Facts
and adapter approval_ref are excluded from this policy preimage. The adapter part
contains adapter_id/role, fixed code/source/contract identities, causal_config and
initial causal state including tracked episode IDs, context plan and declared
selectors; it omits external approval/data-catalogue bindings and future
qualified selection-index results.
Thus a new whole-catalogue approval identity cannot change past economic policy.
Facts enter economic state only when available. No full catalogue/index/registry hash,
file name, export time, global row count or future inventory is readable by an
adapter policy payload, an economic arithmetic path or a random source. random_source is NONE;
any seed/PRNG/entropy request rejects UNSUPPORTED_RANDOMNESS in this profile.

### 3.1 RV02: immutable pre-initial context, not financial replay

```text
InitialContext = {mode:none|closed_fact_prefix,from_us:T,schemas:set[ID]}
ContextReceipt = {from_us:T,before_us:T,fact_count:I,
 economic_prefix_sha256:H,audit_binding_sha256:H}
FactCursor = {schema_id:ID,last_available_us:T or null,last_fact_key:ID or null}
```

For mode=none require schemas=[] and from_us=initial_at; the receipt binds an
empty prefix. Otherwise from_us<initial_at. At create the controller validates
exactly all qualified facts in these schemas whose economic_at>=from_us and
scenario_available<initial_at. Original availability must be known, economic<=
available; closed_bar additionally economic_at+interval_us<=available. An
unresolved required context fact rejects FUTURE_DEPENDENCY, not omission or zero.
Only closed_bar/funding_rate/synthetic_price may be context; no execution_open,
future observation, intent, Fill, fee, financial snapshot/claim or native feature
capsule. The receipt's before_us is exactly initial_at, exclusive. Facts available
exactly at initial_at are first normal releases, not duplicate context.

Receipt economic_prefix hashes the ordered semantic FactProjection rows excluding
raw/audit identity; audit_binding hashes the exact resolved source/ref evidence.
The economic receipt binds the initial state construction, while raw qualification
and whole-store hashes stay audit-only. Future-only rehash may change the latter,
never this unchanged prefix/native preparation. At create the context is admitted
once and its semantic keys/clocks/index plus ContextReceipt and FactCursors persist
in genesis. Each cursor is per schema, sorted by (available_us,fact_key), including
context entries; both cursor fields are null only before the first release.
No normal first delivery may skip an equal-time key. Dedup uses
stable fact_key plus semantic row equality; conflicting semantic values reject
INPUT_BINDING_MISMATCH. Exact repetitions do not initialize state twice.

First controlled slot receives the whole applicable original-clock prefix via its
approved available_prefix selectors, including normal facts available at genesis.
It runs its ordinary typed initialization from that prefix, recording next_state
atomically. Before that slot, initial AdapterState must be the schema's explicit
uninitialized/empty value, not unexplained precomputed indicators. An adapter that
needs a different evidenced initial-state constructor requires a new reviewed
binding; this proposal does not permit hidden initialization. Restart before/after
the first slot reproduces admission/preparation once, with context and slot cursors
validated. Prefix retention/reconstruction, not fresh account creation, applies
at later folds. All validation/preparation/recovery counts against existing caps.

The account financial calendar contains expected snapshots only at
initial_at<=snapshot<end_exclusive. Pre-initial source calendar entries may be
qualified context evidence of flat/no-account eligibility; they are not emitted
as FundingSnapshot or zero ObligationRevision. Thus a proposed2023 context/2024
account uses this separation without financial activity in2023 or resetting an
already active account in2024. This is transport expressibility, not approval of
those dates. Reference-import has mode=none and retains its original origin rules.
Only this explicit genesis context admission bypasses the normal first interval;
after genesis no backdated new fact/delivery may invoke the exception.

### 3.2 R03/R05 transport boundary

FactSchema.kind/view_kind mapping is closed: closed_bar/execution_open/
synthetic_price use kind=price; mark_point/mark_selection use mark; funding_rate uses rate;
billed_total uses billed_total. interval_us>0 only for closed_bar and0 otherwise.
An execution_open schema contains exactly open_us:T and open_price:D+ cells;
economic_at=the open_us cell. It is a separately qualified retrospective view,
not the finalized row with its clock changed. Source refs may join the same raw
row in audit; H/L/C/V cannot enter that projection. Its qualification and any
assumed availability need separate QR/user scenario approval. Policy selectors
cannot select execution_open. A closed_bar retains its interval/closed clock.

Raw fact availability a and consumer slot q remain separate. A Fact may be
released once at a and selected again at q>=a without a new delivery. A financial
Valuation generated from it at q retains source valuation_at, but has
known_at=available_at=q. Calculation.valuation_available_at continues to denote
the approved raw selected-point availability, not that later consumer clock.
The external output validator must bind both explicitly. This does not allow a
new Body backdated to a behind the seal. Known still-valid financial records may
instead be reused; there is no need to re-emit each raw point. Actual MARK query
qualification/age/latest-eligible proof remains an external registered gate.

`mark_selection` is a distinct qualified consumer-fact view: economic_at=
scenario_available=query_at=q, with cells query_at_us:T, source_at_us:T,
source_available_at_us:T, selected_price:D+, source_fact_key:ID and clock_id:ID.
On unsupported lookup the three selected-source cells and selected_price are
typed unknown with the external query schema's exact reasons; query_at/clock
remain known. It is a report of the query at q, not a raw point retimestamped to q.
The qualified fact-store/index binds these cells to original raw evidence and
independent complete-prefix query acceptance. Core transport does not establish
that qualification or implement its scanner. A registered schema must distinguish
these clock meanings and reject a false source clock or inferred zero. The selector
can supply this bounded per-q result without delivering every raw MARK point.
One result per instrument/clock/query is required by the approved query schema,
including unsupported results; absence is a binding failure, not a silent noop.

Tail selector rule is fixed at create, not a caller override: for slots at/after
end_exclusive, closed_bar/execution_open/mark_point/mark_selection/synthetic_price
selectors are inactive and supply a complete empty selection, bound with count0.
No new market row, current MARK lookup or prefix feature refresh reaches a tail
port, including a finalized last bar whose availability equals cutoff. This
specified inactive selection is distinct from a missing required pre-cutoff
qualified_at_slot result. Funding_rate/billed_total selectors may supply only
already-scoped economic_at<end facts with newly arrived evidence before knowledge
end. Stored qualified snapshot facts, order/episode evidence and owned state remain
available through the ledger/state transport. Tail lifecycle/feedback uses those
saved inputs; registration rejects a tail port that needs fresh market features.

If selected source time precedes account genesis, it can remain qualified fact
evidence; it cannot be emitted as an out-of-range financial Valuation origin or
shifted to genesis. With no initial inventory, flat U=0 is an identity and a
query-result fact can independently gate the first order. Any native binding
requiring an unsupported pre-genesis financial origin must return for review.

At economic end, pending reserve records must already expire no later than
end_exclusive. Expiry is invalid at equality, so it does not mean proved zero
reserves or supported risk. A scheduled typed cutoff lifecycle slot may cancel/
expire order status and update AdapterState with events=[]; no Fill, snapshot,
Valuation, new Reserves origin, decision or new order is permitted there. It is
an audited noop/transport transition within the knowledge window. Subsequent
tail slots permit only already-originated obligation/posting/assertion evidence
and necessary declared bookkeeping; no new current-market facts/query. Financial
views still evaluate true MARK age/expired reserves and can report null U/budget;
open exposure is retained, never liquidated by the kernel. Finality may use stored
qualified evidence. This expresses the proposed evidence-only tail without an
economic-origin exception or cutoff-1us backdating. Tail length and native state
semantics remain external QR/user choices. Unsupported tail economics require a
separate version amendment, not a silent extension here.

## 4. Controlled deterministic adapter port and generated-event witnesses

Control QF-CONTROL-20261028-QD009-FULL-REPLAY-FIDELITY-1 clarifies the target:
this contract must accept later **fixed native strategy/execution adapter** outputs,
not only hand-written synthetic events. Required assurance is pinned inputs and
available prefixes, typed rule/event binding, a controlled deterministic execution
path and independent future-perturbation/end-to-end checks. It is not a universal
proof that arbitrary Python has no outside dependency. No DSL/compiler is proposed.

```text
AdapterDefinition = {adapter_id:ID,role:environment|policy|execution,
 code_commit:Git40,source_files:list[{relative_path:str,sha256:H}],
 entrypoint:str,input_contract_sha256:H,output_contract_sha256:H,
 state_contract_sha256:H,causal_config:JsonValue,approval_ref:H,
 fact_selectors:list[FactSelector],ledger_selectors:list[LedgerSelector],
 peer_state_selectors:list[PeerSelector]}
Git40 = lowercase40-hex commit
JsonValue = null|bool|I|SI|str|list[JsonValue]|object[str,JsonValue]
Tick = {at_us:T,slots:list[{slot_id:ID,adapter_id:ID,phase:I}]}
AdapterState = {adapter_id:ID,contract_sha256:H,tracked_episode_ids:set[ID],
 value:JsonValue,state_sha256:H}
AdapterInput = {slot:Cutoff,slot_id:ID,causal_policy_sha256:H,
 permitted_facts:list[FactProjection],before:EconomicView,
 economic_inputs:list[EconomicSelection],peer_states:list[AdapterState],
 previous_invocation:Cutoff or null,prior_state:AdapterState,causal_config:JsonValue}
FactProjection = {fact_key:ID,instrument_id:Inst,schema_id:ID,economic_at_us:T,
 scenario_available_at_us:T,cells:list[{name:ID,cell:Cell}]}
AdapterResult = {outcome:emit|noop,events:list[FinancialBody],
 decisions:list[DecisionRecord],orders:list[OrderIntent],
 order_transitions:list[OrderTransition],next_state:AdapterState}
DecisionRecord = {decision_id:ID,at_us:T,instrument_id:Inst,order_ids:set[ID],
 input_projection_sha256:H,prior_adapter_state_sha256:H,
 intent_contract_sha256:H,intent:JsonValue}
FactSelector = {selection_id:ID,schema_id:ID,instruments:set[Inst],
 mode:available_prefix|latest_available|qualified_at_slot}
LedgerSelector = {selection_id:ID,instruments:set[Inst],
 kind:live_lots|orders_active_and_changed|decisions_for_selected_orders|
      financial_changes|episode_lots|episode_slices|episode_obligations}
PeerSelector = {selection_id:ID,adapter_id:ID}
EconomicSelection = {selection_id:ID,items:list[EconomicItem]}
EconomicItem = {kind:live_lot,value:LiveLot}|{kind:order,value:OrderRecord}|
 {kind:decision,value:DecisionRecord}|{kind:financial,value:FinancialBody}|
 {kind:lot,value:Lot}|{kind:slice,value:Closed}|{kind:obligation,value:Obligation}
LiveLot = {lot_id:ID,episode_id:ID,instrument_id:Inst,opening_fill_id:ID,
 opened_at_us:T,direction:long|short,entry_price:D+,multiplier:D+,
 live_ranges:list[UnitRange]}
OrderIntent = {order_id:ID,decision_id:ID,instrument_id:Inst,
 action:open|reduce|close,direction:long|short,requested_contracts:I+,
 submitted_at_us:T,eligible_at_us:T,expires_at_us:T,
 payload_contract_sha256:H,payload:JsonValue}
OrderTransition = {order_id:ID,at:Cutoff,
 status:partially_filled|filled|cancelled|expired,fill_keys:set[Key],reason:ID}
OrderRecord = {intent:OrderIntent,status:pending|partially_filled|filled|cancelled|expired,
 filled_contracts:I,remaining_contracts:I,last_changed:Cutoff,fill_keys:set[Key],
 terminal_reason:ID or null}
```

JsonValue forbids JSON float/nonfinite values; the adapter's separately versioned
numeric/state contract may encode native float64 exactly as16-hex bit strings,
never as ledger D or approximate source truth. Each registered input/output/state/
intent schema is a **closed external schema** pinned by those hashes; unknown
schema, missing validator or unapproved port rejects UNSUPPORTED_GENERATOR.
The kernel validates that registered schema, not arbitrary free-form dictionaries.
Initial infrastructure fixtures use a small typed state/intent schema; the R3
native port must register its actual typed schemas before it can be executed.
entrypoint/code/source identity alone does not authorize that registration.
The registered entrypoint must expose deterministic validate_input/validate_output/
validate_state operations for these pinned closed schemas plus evaluate; their
code is inside the approved source_files inventory. No runtime validator discovery
or hash-only untyped payload acceptance. Schema contents/units and completeness
are reviewed alongside the actual adapter, not guessed by the ledger kernel.

The port interface is exactly `evaluate(AdapterInput) -> AdapterResult`; it is a
stateless controller invocation with all persistent state passed/returned, not a
free callback retaining an invisible account between calls. The **execution
controller constructs** the available-prefix packet and invokes only the frozen,
reviewed adapter entrypoint; a caller cannot choose per-call code/config/clock or
pass an arbitrary Python function. Future native ports can call unchanged pinned
prepare_features/signal_at/allocation/decide_execution/build_order_plan/record_fill
inside that adapter with an independently reviewed exact-to-native numeric
projection. No native functions or market fill assumptions are implemented here.

The context supplies only whitelisted economic projections, ordered available
fact prefixes and the predecessor adapter state. It does not supply raw-store
handles, filesystem paths, source/catalogue/audit hashes, retrieval metadata,
full future arrays, qualification manifests or PRNG seeds. Source lookup happens
in the controller. At a minimum all packet facts satisfy scenario_available<=slot
and the active input schema's economic-close constraint; a packet containing a
future fact fails before the adapter runs. Past raw refs are joined into audit
by the controller after evaluation, never exposed as economic inputs. Caller
cannot nominate a smaller/different prefix based on future information: selectors
and the finite query schedule are part of the approved input contract.

Adapters are trusted reviewed project code, **not hostile-code sandboxes**. Review
must forbid direct outside data/files/network, global mutable state, wall-clock/
entropy and unregistered source lookups. Offline guards/instrumented negative
ports must reject attempted bypasses; restart/repetition and independent future
perturbations test the entire packet-controller-adapter-ledger path. These checks
are the enforceable acceptance boundary, not a claim to inspect every possible
Python branch. If an adapter cannot meet it, registration is refused; a code hash
and declared read list cannot upgrade it to causal. This explicit trust/validation
model provides the defined native-bridge port/state binding; it does not postpone
that known requirement under an unspecified optional extension.

Each generated registry entry is exactly:

```text
Generated = {registry_seq:I+,slot:Cutoff,slot_id:ID,adapter_id:ID,
 parent_audit_prefix:H,parent_registry_sha256:H,before_economic_state:H,
 adapter_definition_sha256:H,input_projection_sha256:H,
 prior_adapter_state_sha256:H,reads:list[Read],selection_bindings:list[SelectionBinding],
 result:AdapterResult,result_sha256:H,entry_sha256:H}
Read = {kind:fact,fact_key:ID,field:ID,cell:Cell,raw_refs:set[RawRef]}
 | {kind:ledger,selection_id:ID,item_kind:live_lot|order|decision|financial|lot|slice|obligation,business_key:list[str|I],
    source_cutoff:Cutoff,value:EconomicItem}
 | {kind:state,adapter_id:ID,source_cutoff:Cutoff,state:AdapterState}
SelectionBinding = {selection_id:ID,source_cutoff:Cutoff,
 source_roots:list[{component:lots|closed_slices|obligations|entries|links|orders|decisions|adapter_states|facts|fact_selections,root_sha256:H}],item_count:I,
 selected_keys_sha256:H,selected_values_sha256:H}
Envelope = {namespace:"qf009.streaming-ledger",schema_version:2,
 profile:"qf009-offline-stream-r2",body:FinancialBody,
 origin:{kind:generated,registry_seq:I+,output_index:I}
      | {kind:reference_import,fact_key:ID},created_at_us:T}
```

input_projection_sha hashes AdapterInput; it includes causal policy/financial
view/declared adapter state, never a full audit identity. AdapterInput.before
uses an EconomicView projection of View with **view_sha256/component audit handles
removed**, retaining Balance, cutoff and economic component roots only; the
precise EconomicView closed schema is `{view,economic_at_us,knowledge_cutoff,
causal_policy_sha256,balance,economic_component_roots,coverage,economic_state_sha256}`,
economic_component_roots is list[{component:lots|closed_slices|obligations|entries|
links|adapter_states|orders|decisions,root_sha256:H,count:I}]. It contains no events/registry/source audit component.
State hashes are continuity witnesses, not adapter decision inputs: the controller
strips hash-valued continuity fields before handing numeric policy payloads to
native functions. They cannot choose branches or seeds. Fixed policy identity is
part of the contract, not a numeric feature.

reads is the complete controller-supplied packet field inventory, not a caller's
claim of every internal Python access. Its field values must equal frozen available
facts or ledger/state projections; raw_refs resolve to facts only. Packet membership/exclusion is verified
independently of adapter output. Record all supplied fields even if unused, so
future noninterference is tested against actual input packets. State and decision
bindings identify predecessor declared state and exact permitted numeric inputs.
parent_registry_sha256 is the preceding Generated entry hash, or the frozen
registry genesis for the first; parent_audit_prefix is the transaction's prior
committed audit prefix, never its not-yet-created next prefix. Result hash is
canonical AdapterResult; entry hash excludes only entry_sha256,
including parent audit prefix and all provenance. State hash is canonical
AdapterState excluding state_sha256 and forbids audit data in its typed value.

The kernel/controller obtains the actual AdapterResult itself. A proposed external
Generated entry is accepted only if it equals the re-executed frozen port result
and all checked input/state bindings; an arbitrary caller-created result cannot
be made valid by rehashing its metadata. Deterministic business IDs derive from
frozen account/trajectory/slot/ordinal or explicitly registered stable semantic
IDs, never global catalogues/registry hashes. A Fill's decision_id/order_id must
resolve to an available DecisionRecord in this prefix (possibly earlier output
in the same slot), matching instrument and order_ids; decision_at must equal its
at_us and not exceed filled_at. Later executions reference the stored earlier
intent, not a new decision with the same ID. Intent/output quantities and execution
price/timing/capacity conditions are checked by the registered execution-output
contract, whose actual numerical assumptions must be frozen by QR separately.
Decision/intent content is stored, not just its hash, for independent replay.
For generated new entities the controller's required ID helper is
prefix+H(["qf009.id-v2",ledger_id,trajectory_id,scenario_id,instrument_id,
logical_kind,tick_at_us,slot_id,ordinal]); prefixes f:/p:/d:/o: identify new fill,
posting, decision/order IDs and fit the96-character Fill bound. Derived lot/
episode/leg IDs retain r3 rules; fee obligation can use fee:<fill_id>. Snapshot IDs
come from the predeclared calendar. Revisions/successor assertions reuse the
referenced existing entity ID, not a new current-slot hash. Reference-import IDs
are preserved literally. Reject an adapter's differing ID mapping before commit.

All due slots execute in the frozen schedule, including noops; caller cannot
omit an unfavourable slot or switch adapter based on future data. outcome=noop
requires events=[]; a noop may update declared causal adapter state. Unknown
financial inputs cannot silently become known cells or zero; a port either emits
valid unknown-bearing records or a typed no-new-risk/noop decision under its
reviewed output contract. The kernel still enforces all financial guards. A due
expected snapshot cannot disappear through a noop. Full registry/result/order/decision/adapter
state and emitted FinancialBodies commit atomically, closing the source-manifest
cycle without preconstructing future fills.

Multi-step positive fixture, **all numbers synthetic, times in microseconds**:
predeclare C1000, one BTC integer lot, m1, fee0, empty funding calendar, reserve0
valid throughout, a fresh MARK rule and pinned deterministic fixture port. Its
closed intent schema defines integer requested_quantity and reason; state defines
last_decision and pending_order IDs. At t10 available price100 produces decision
D10/orderO10 and Fill+1@100; fee T0 needs no zero Posting. At t20 available MARK99
gives U=-1/budget999; its fixed budget>=1000 gate records noop with reason and
updated last_decision. At t30 available exit price101 produces D30 and Fill-1@101,
gross1/C1001. At t40 available billed fee revision2 T=-0.2 on the entry gives
L0.2/budget1000.8, C unchanged. Separate Posting-0.2 at t50 gives C1000.8/L0,
same budget. Inputs/state/result/provenance are saved at every step; no native
policy choice is inferred from this tiny fixture.

Change only t30 price101->500 and rehash whole raw catalogue/fact store: t10/t20
packets' economic fields, adapter declared states, business IDs/choices/budgets
must match while full audit refs/prefixes may differ. Negative cases: controller
packet at20 includes fact available30 -> FUTURE_DEPENDENCY; external q2 result
while re-executed port emits q1 -> ADAPTER_RESULT_MISMATCH; altered packet/declared
state/read inventory -> INPUT_BINDING_MISMATCH; omitted noop/adapter switch ->
SCHEDULE_MISMATCH; direct future file/global-seed access -> FORBIDDEN_INPUT
or independent end-to-end future-perturbation rejection. The last category is
explicitly tested/reviewed, not falsely claimed to follow from code hashing alone.

Mandatory native-bridge gate before declaring R3 implementable: a reviewed port
with exact numeric-prefix and intent/execution/state schemas must drive the real
pinned native policy on bounded **synthetic** OHLC/funding/mark inputs; demonstrate
prefix/full-input equivalence, deterministic fills and feedback, known/unknown
budget gating, complete restored timing/sizing/pending-order state and future
perturbation independence. Full market data/parameters/run remain separate. Initial
ledger code can be accepted for infrastructure while this gate is NOT_EXECUTED;
that state must be reported as R3_NOT_READY, not hidden by a synthetic-only PASS.
Same port/envelope/state transport is intended for that bridge; if its typed
requirements cannot fit, QD/QR must review a versioned amendment **before** native
implementation rather than quietly adding fields or unsupported callback paths.

### 4.1 RV01: complete bounded cross-port inputs and authoritative order state

Selectors are closed enums above, not caller expressions, callbacks or unrestricted
scan requests. mark_selection must use qualified_at_slot, and that mode
is forbidden for all other view kinds. The per-q index is derived only from the
qualified fact_store already declared in CreateRequest; there is no implicit
external selection file or loader. IDs are unique per definition, instruments are a nonempty subset of
Config scope, peer IDs name another declared adapter, and fact schema IDs must
exist. Definitions and per-role field validators are frozen under their contract
hashes before create; no per-call selector/filter/limit override. Packet order is
selection_id then typed business-key order, with complete sets, not favorable
subsets. `previous_invocation=null` means never invoked, otherwise the controller's
last completed slot of this adapter, including staged earlier slots in this tick.

| Selector | Exact membership and authoritative truth |
| --- | --- |
| fact available_prefix | All facts in schema/instruments released by slot, including declared context, sorted (available_us,fact_key). |
| fact latest_available | Latest such fact per instrument by (available_us,economic_at_us,fact_key); only schemas whose qualification defines this choice. It is not generic latest-eligible MARK selection. |
| fact qualified_at_slot | Only for mark_selection: all rows of that schema/instruments with query_at=economic_at=scenario_available=slot.at_us, for the approved finite query schedule. The per-q index is a deterministic index of this declared immutable fact_store, not a second unlisted source. Missing row/schema/qualification blocks invocation; original source clocks remain separate cells. No arbitrary loader or on-demand query. |
| live_lots | Every lot with remaining units in instruments at the before-view, with actual disjoint current FIFO live_ranges, prices/multipliers/direction. No financial history is inferred from a root. |
| orders_active_and_changed | All nonterminal OrderRecords plus every terminal order changed after previous_invocation and before the current slot. Initial lower bound is genesis slot0. |
| decisions_for_selected_orders | Full earlier DecisionRecords for exactly those selected orders, including native plan/feature payload if its registered schema requires it. No future decision list. |
| financial_changes | All normalized FinancialBodies made available/accepted after previous_invocation through the before-view, sorted by actual slot then economic/tie/key order. It includes fill, fee/funding revisions, postings, valuations/reserves and assertions; not audit events. |
| episode_lots / episode_slices / episode_obligations | All corresponding current Lot/Closed/Obligation rows for prior_state.tracked_episode_ids, within instruments, including closed original lots/old obligations. Obligation membership follows retained episode allocations even if closed. Full calculation/allocation evidence is supplied via financial_changes or already-retained owned state, not inferred from reference roots. |
| peer state | Exact before-slot AdapterState of each explicit peer ID; read-only, schema checked. No other adapter's globals or state are available. |

The episode selectors' output is **only** those typed current rows; the final
sentence about additional old-body needs is a registration restriction, not an
extensible query hook. This profile supplies no arbitrary old-body lookup. A
native binding needing it must either retain that already-read evidence in owned
state or return for an explicit typed amendment. No hidden scan is permissible.

| Role | Fact view allowlist | Ledger selector allowlist | State rights |
| --- | --- | --- | --- |
| policy | closed_bar, funding_rate, synthetic_price | All seven listed ledger kinds | Own state write; explicitly declared peer states read only |
| execution | closed_bar, execution_open, mark_point, mark_selection, synthetic_price | All seven listed ledger kinds | Own state write; explicitly declared peer states read only |
| environment | mark_point, mark_selection, funding_rate, billed_total, synthetic_price | live_lots, orders_active_and_changed, financial_changes, episode_lots, episode_slices, episode_obligations | Own state write; peer_state_selectors=[] |

The registered per-role input contract must enumerate exact selected cell names
and economic payload fields; the controller rejects fields outside it before
invocation. It cannot select a partial live range/order record while asserting
complete membership. Root/hash fields remain continuity evidence, stripped before
native numerical calls. Role allowlists are upper bounds, not permission to feed
all delivered financial values into native features or to replace a MARK with
trade close. Output validators enforce the approved purpose/clock/formula.

OrderIntent is created only by a policy role, with submitted_at=its current slot,
eligible>=submitted, expires>submitted and within the declared scenario lifecycle.
An eligible time at/after expiry means no executable opportunity, not a forced
fill or rejected submission; no Fill is allowed at/after expiry.
Its decision/order scope and quantities must match the full stored DecisionRecord
and registered intent/payload schemas; order_ids exactly enumerate its created
orders. No insertion of a reconstructed past intent. Controller creates pending
OrderRecord with filled0/remaining=requested, then maintains it from validated
OrderTransitions and actual Fill references, not an adapter's asserted totals.
filled=sum absolute contracts of that order's distinct accepted fills;
remaining=requested-filled, including unfilled quantity after cancellation.
No duplicate fill counting, excess fill, terminal-to-pending transition or changing
an immutable intent. partially_filled requires0<filled<requested; filled requires
remaining0; terminal_reason is null only for nonterminal status. Existing fills,
cross-order conflicts and one order's direction/action are checked before commit.

Execution may emit fill-confirmation/partial/filled/cancel transitions. Policy may
cancel/expire existing intent under its approved lifecycle; environment cannot
modify orders. Cutoff expiry/cancellation may be a policy lifecycle invocation
with no new decision. Every OrderTransition.at equals its current slot; fill_keys
refer only to already available or same-result matching Fills. Ordered partial
then cancellation in one result is supported. Empty fill_keys on a pure cancel
does not create a Fill or cash. The registered output validator, not this kernel,
defines which market no-fill/partial/reversal choices are admissible.

State has one writer: next_state must match the invoked adapter_id/schema.
tracked_episode_ids are causal existing scoped episode IDs (empty before any
episode); selecting an absent/future/cross-account ID rejects INPUT_BINDING_MISMATCH.
Peer state cannot be patched via next_state. A binding sharing native books must
assign one owner and schedule that owner's feedback slot before the next dependent
decision, or use a reviewed composite owner. This is a transport restriction;
QR's future native schema chooses the actual callback/feature/partial-sizing rules.
All changes of a tick, including fill/fee/order status and each owner's feedback
state, stage together and publish atomically. Failure in the later feedback slot
rolls back the whole tick's proposed changes, not an already acknowledged fill.

SelectionBinding is controller evidence outside AdapterInput: source roots bind
the before-view economic components or immutable qualified fact index, plus count,
complete selected keys and semantic values. Hash preimages use domain
`qf009.selection-v2`, selection definition, cutoff and ordered contents; selected
values exclude audit refs. Fact membership evidence separately resolves raw refs.
For peer selectors it binds the prior adapter_states root/value. All membership,
omission, stale value and future inclusion checks occur before evaluation and again
before publication against the same staged predecessor; hashing a forged subset
does not validate it. A Generated entry records every supplied Fact field, every
ledger EconomicItem and every own/peer State in reads, even if unused. Reconstruct
input_projection_sha from this complete packet plus fixed config/before-view;
Read is not a self-reported list of accesses. Native output never sees audit paths.

Controller selectors use indexed bounded reads, no uncontrolled public scan handle.
No root decoding, hidden state duplication or external fetch is accepted. Enforce
max_adapter_input_bytes, state bytes, wall and reads **before** invoking a port.
Freeze read accounting here: one read for each supplied Fact cell and each of its
two economic/availability clocks; one for each economic scalar leaf in ledger
items, intent/owned/peer-state payloads and live ranges. Pure transport wrappers,
stable membership keys and hash continuity fields are verified in the complete
inventory/selection binding and charged in input bytes, not counted again as
extra economic reads. Fact clock reads use reserved field IDs
clock:economic_at_us and clock:scenario_available_at_us with typed T Cells.
FactSchema field names starting clock: are reserved and reject SCHEMA_VIOLATION;
ledger item_kind must equal its EconomicItem tag, never an arbitrary string.
No whole OrderRecord/state is counted as just one read. The262144 ceiling is
unchanged; counts/definitions are reported before execution, never redefined to
rescue a failing candidate. Excess complete selection is
RESOURCE_EXHAUSTED; there is no truncation, partial inventory or new smaller page
chosen by strategy. Controller may page internally under existing cache bounds,
but the delivered packet must be complete within the unchanged caps.

Orders/decisions become retained economic components with canonical business keys
(instrument,order_id)/(instrument,decision_id); their prior versions remain on
disk, including terminal status. Generated audit remains separate. Checkpoint
persists those rows, every owned state, per-adapter last invocation and fact/context
cursors atomically. Restart between submission/fill/feedback never rebuilds intent
from current prices or clears sizing/timing state. Actual native completeness is
still proved by later S13, not self-certified by a declared state hash.

### 4.2 R05 stable semantic identities and external-schema dependencies

Raw refs/full-file hashes are audit joins only. Qualified source keys use the
declared instrument, original source timestamp, source role and a deterministic
duplicate ordinal only if the qualified source policy requires it; the actual
key mapping/alias rule is pinned externally. A funding obligation uses the same
stable source identity, never the full file/catalogue digest. Future-only rehash
can change refs/qualification evidence, not existing semantic keys, financial IDs,
selector membership, generated order/fill sequence or prior native state.

FactSchema/qualified_at_slot can express distinct open facts and repeated selection
of an old available MARK; neither establishes raw support or a query proof. Exact
native numeric/feature/intent/payload/state and external query/qualification/index
schemas are **UNASSIGNED_BLOCKS_NATIVE_REGISTRATION** until separately reviewed.
No new callback, forecast, float tolerance, partial-ticket sizing policy or query
universe is selected by this transport amendment. Existing QF00634 criteria and
full real native replay target remain intact; S13 cannot be replaced by this port
table or a hand-authored financial tape.

## 5. Advance, queries and atomic failure

Public methods accept/return only strict JSON-compatible objects (no caller-held
mutable state). All responses are detached copies/pages. Exact signatures:

```text
create(CreateRequest) -> Head
advance(AdvanceRequest) -> Receipt
as_known({cutoff:Cutoff}) -> View
restated({economic_at_us:T,knowledge_cutoff:Cutoff}) -> View
scan({view_sha256:H,component:Component,filter:ScanFilter,
      after:PageToken or null,limit:I+,null_reasons:ReasonMap}) -> Page
readiness({episode_id:ID,cutoff:Cutoff}) -> Readiness
checkpoint({expected_head:H}) -> Checkpoint
restore({checkpoint:Checkpoint,expected_committed_head:H,store_root:str}) -> Head
resolve_commit({request_id:ID,request_sha256:H}) -> CommitResolution
audit({after_audit_seq:I,limit:I+}) -> AuditPage
```

Head exactly `{ledger_id:ID,committed_seq:I,cutoff:Cutoff,audit_prefix:H,
economic_state_sha256:H,status:ACTIVE|INTEGRITY_STOPPED|RESOURCE_STOPPED|COMMIT_UNKNOWN}`.
Genesis committed_seq0 uses cutoff(initial_at,0). Head audit prefix binds immutable
config/catalogue identities, journal and registry prefixes. Economic root hashes
only causal policy, cutoff and the economic component roots/Balance below, never
audit source refs/created times/registry/catalogue hashes. Source IDs used as keys
must have stable semantic meanings; audit objects cannot be consulted to decide.

```text
AdvanceRequest = {request_id:ID,expected_audit_prefix:H,through_us:T,
                  imported:list[Envelope],generated:list[Generated]}
Receipt = {request_id:ID,request_sha256:H,status:committed|replayed,
           before:Head,after:Head,applied_keys:list[Key],duplicate_keys:list[Key],
           entries:ComponentHandle,registry_from:I,registry_to:I,
           no_op_slots:list[Cutoff]}
ComponentSummary = {component:Component,count:I,root_sha256:H}
ComponentHandle = {view_sha256:H,component:Component,count:I,root_sha256:H}
```

First advance covers [initial_at,through]; later covers (last committed through_us,
through]. through_us>=previous time; complete every due schedule tick/slot and
calendar coverage assessment up to through. No commit midway through a tick.
Batch source/import availability must lie in this interval, except exact accepted
duplicates and the one-time pre-initial context admitted at create (§3.1), which
is not a financial import or later delivery. Caller supplies the required generated witnesses/results or requests
controller-driven adapter generation by passing generated=[]; in either case kernel
invokes every required approved adapter slot, and supplied nonempty witnesses must match exactly.
An empty array is not permission to skip slots. Imported events are only frozen
reference fixtures in reference_import mode; controlled_adapters accepts none.
Head.cutoff.at_us always equals through_us. At a scheduled controlled tick its
slot is N; otherwise it is0. A through_us with no tick still seals availability
through that exact time and computes time-dependent balances/coverage there;
the next scheduled tick is tracked separately and not substituted as Head time.
Checkpoint stores next_tick_index:I (the first schedule tick not yet processed),
in addition to calendar_cursor. Genesis Head is an unsealed sentinel; before the
first advance financial as_known queries reject SCHEMA_VIOLATION rather than
pretending the initial instant's not-yet-imported facts have been processed.

At each tick facts whose scenario availability has arrived are released first
(internal slot0). Frozen slots run in stated order; equal phase follows slot order.
The external scheduler must predeclare phase/slot semantics, decision/fill timing
and required snapshot ordering; no market latency/fee choice is made here. Reject
plans/outputs inconsistent with r3 snapshot/fill tie rules. Within one emitted
financial group, inventory/snapshots follow economic sequence and the fixed tie
rule; origins precede dependent revisions, revisions precede Postings, assertions
are checked after references exist. Valuation/reserve slots must precede adapters
that consume them. Future slots at the same microsecond are not visible to earlier
adapter invocations. Final-at-time queries include all completed slots, matching r3's time
cutoff for equivalence fixtures. Same-time ambiguous fill sequences still reject.

New delivered financial content with declared availability already behind the
committed cutoff rejects PAST_AVAILABILITY; do not relabel its time as now. Exact
duplicates may redeliver at any time and cannot repeat a transition. A late
ObligationRevision can retain an old economic origin with a **new current** known/
available time; same for a newly learned established booking. These do not rewrite
earlier as-known views. New Fill admission preserves r3's prior-fill ordering and
whole expected-calendar guards against crossing an earlier eligibility snapshot.
No backdated fill/origin reconstruction, revision gaps, posting-revision repair or
in-place replacement. Missing qualified snapshot is a visible coverage issue,
not fabricated financial zero; hard scope/identity errors stop atomically.

Same request_id/canonical request returns its saved Receipt with status=replayed,
without a second transaction, even if expected prefix is now old. Same request_id
different request conflicts. New request_id must match current expected prefix;
PREFIX_MISMATCH is a non-latching precondition rejection. Business duplicates use
Key+normalized Body hash, independent of request/registry/export/source IDs; same
key/different body quarantines. Preserve corroborating refs only in audit.

Error exactly `{code:ErrorCode,path:str,request_id:ID or null,before:Head or null,
input_sha256:H or null,disposition:reject|quarantine|stop_resource|inspect_committed_head,
null_reasons:ReasonMap}`; null request=UNKNOWN_INPUT_IDENTITY, input hash null=
NONCANONICAL_INPUT; a read-only call with no request ID uses NOT_APPLICABLE;
before null=NO_COMMITTED_LEDGER only for a failed create/invalid store open.
ErrorCode is the closed union of r3 schema/rule/financial
failure codes plus PREFIX_MISMATCH, REQUEST_CONFLICT, PAST_AVAILABILITY,
FUTURE_DEPENDENCY, FORBIDDEN_INPUT, UNSUPPORTED_GENERATOR, UNSUPPORTED_RANDOMNESS,
INPUT_BINDING_MISMATCH, ADAPTER_RESULT_MISMATCH, SCHEDULE_MISMATCH, CHECKPOINT_MISMATCH,
STORE_INTEGRITY_FAILURE, RESOURCE_EXHAUSTED, RESOURCE_EXHAUSTED_READ and
COMMIT_OUTCOME_UNKNOWN. The r3 codes are enumerated in
section9 to make this transport reviewable without an implementation fallback.
No silent arbitrary ValueError strings become a new wire code.

Pre-linearization atomic failure leaves all committed financial state, IDs, source registry and
cursor unchanged; an independently durable failure receipt is audit-only. Hard
schema/causality/reference/conflict errors in a submitted write latch INTEGRITY_STOPPED (quarantine for
conflict/restatement), admitting audit reads only. Resource exhaustion latches
RESOURCE_STOPPED with unchanged prefix, not partial success or automatic smaller
economics. Queries cannot advance state or expose future knowledge. No retries or
limit increases are automatic. A separately dispatched continuation/repaired new
run retains old failure evidence and the same economic history, not edited inputs
under the old identity. Actual crash recovery of an already committed prefix is
different from clearing a semantic stop.
Read request validation errors do not latch or alter the live economic ledger.
If publication was attempted and I/O fails around/after HEAD linearization, do
**not** claim rollback. Return COMMIT_OUTCOME_UNKNOWN/inspect_committed_head with
the last prior Head in Error.before and block new writes/financial use until
resolution. A committed complete new prefix may exist; no half cash/registry is
admitted. CommitResolution exactly `{request_id:ID,outcome:committed|not_committed|unknown,
head:Head or null,receipt:Receipt or null,null_reasons:ReasonMap}`; unknown head/
receipt reason COMMIT_OUTCOME_UNKNOWN, known-not-committed receipt null=
NOT_COMMITTED. Resolver must use the barrier/reachability proof below, rather than
treat readable HEAD/request-index bytes as durable. Ambiguous/corrupt store remains
unknown. No blind retry, new request ID or balance subtraction is an outcome
resolution. Any controlled resubmission after proven noncommit retains exact
request identity and counts against the frozen attempt/resource budget.

### 5.1 RV03: bounded durable resolution and independent persistent stops

`resolve_commit` acquires the same exclusive writer lease and performs one bounded
resolution pass; no automatic loop/retry/backoff or extra attempt. New writes and
financial use remain blocked while its write guard is unresolved.

1. Open the exact run/profile/config and independently recover CONTROL (§7),
   preserving semantic/resource latches. Read HEAD and validate the reachable
   manifest chain/request cores and hashes, using validated checkpoint plus suffix
   where available. Validate relevant blobs/dependencies against declared files;
   an orphan segment/request index entry is not reachable because its bytes exist.
   Budget includes this work and conservative crash debit.
2. Under the lease, re-establish required barriers for the chosen reachable HEAD:
   fsync referenced newly published blobs/manifests and their containing directory
   entries, fsync the HEAD file and its parent directory, then close/reopen/read
   back HEAD and required control pointer. Exact hashes, sequence, prefix and
   pointer identity must remain consistent. Previously acknowledged dependencies
   may use validated durable checkpoint evidence, never unacknowledged cache
   state. Filesystems lacking these local atomic/fsync guarantees fail precondition;
   this is no guarantee for arbitrary mounts or devices.
3. Any continued barrier/readback failure or ambiguous/corrupt candidate returns
   outcome=unknown with null head/receipt and leaves the guard. It does not
   acknowledge a readable new prefix or claim the old prefix survived. A control
   latch/uncertainty record cannot be silently cleared because this call failed.
4. If the now-durable reachable chain contains request_id with exactly the saved
   canonical request_sha256, reconstruct its single original committed Receipt
   from manifest/ReceiptCore, persist guarded resolution and return committed.
   No financial transition is re-executed or added. Repeating this call returns
   the same committed content; replayed is only the existing API receipt status.
5. If that ID is reachable with a different hash, return Error REQUEST_CONFLICT /
   quarantine and persist the integrity latch; never “not committed for this hash”
   or a new receipt. A corrupt index disagreeing with the chain gives
   STORE_INTEGRITY_FAILURE/unknown, not an alternative transaction history.
6. not_committed requires a durable validated HEAD at the guarded predecessor
   (or another already acknowledged reachable chain), no reachable matching ID,
   and no unresolved competing pointer/control publication. An orphan tail alone
   is retained/quarantined audit evidence, never imported as commit or payment.
   Persist not_committed resolution before returning it. Only a separately allowed
   same-ID/hash resubmission may follow, within remaining caps.

The returned resolution.head is current Head with the independent control overlay;
saved Receipt.after remains its historical committed head. Resolving I/O may
remove only that guard's COMMIT_UNKNOWN condition. Any integrity/resource latch
still yields a stopped current Head; financial success does not clear it. No
restart/new request/older checkpoint clears a stop. All error/receipt persistence,
readback, suffix work and resolver invocations count within the declared suite/
attempt/wall/disk budget. Limits cannot be raised to force a proof.

## 6. Financial views and bounded paging

ViewCore exactly `{view:as_known|restated,economic_at_us:T,knowledge_cutoff:Cutoff,
causal_policy_sha256:H,balance:Balance,components:list[ComponentSummary],
coverage:list[CoverageIssue],economic_state_sha256:H}`. View is exactly ViewCore
plus top-level `view_sha256:H`. **No ViewCore component contains a view ID.**
Compute economic_state_sha256 first as
H(["qf009.economic-state-v2",EconomicViewCore]), where EconomicViewCore is exactly
the closed EconomicView defined in section4 with economic_state_sha256 omitted;
its component list contains only economic ComponentSummary values, excluding
events/registry. This preimage includes actual query clocks and coverage, no
audit/view/handle identity. Then compute
view_sha256=H(["qf009.view-v2",ViewCore]). No recursive nested exclusions apply.
Only after these hashes exist may public handles be assembled by copying one
ComponentSummary and adding this view_sha256. View itself uses summaries, not
those handles. Receipt.entries is a handle to the **whole after-view entries**
component; applied_keys identifies new transitions, not a second cash effect.
Its hash/count/root must equal the chosen after-view summary. Receipt/Head/
registry are not in the ViewCore hash preimage.

Scan/Page/PageToken bind to this already computed view_sha256 and exact component/
filter. The store retains ViewCore or reconstructs it and verifies the hash before
paging; it cannot substitute another cutoff's root. EconomicView for adapter
input is derived directly from EconomicViewCore plus its economic_state_sha256,
never by handing adapters public handles or View's audit identity. Financial/root
preimages have fixed domain/version and typed business-key order, independent of
storage page layout. Thus no handle/receipt/checkpoint construction is circular.

as_known accepts any actual time initial_at<=at_us<=Head.at_us after the first
advance, with slots as defined in section2, not only schedule ticks. At non-tick
t use the last committed financial transitions available<=t but **re-evaluate**
MARK age at t, reserve expiry at t and every expected snapshot due<=t. Preserve t
in Balance.as_of_us/knowledge_cutoff_us, ViewCore and hashes; never return the
previous tick's freshness/expiry flags. Financial histories may use indexed
versions, but derived clock-dependent facts are not copied from a stale cache.
Incomplete/uncommitted slots and times beyond Head reject. restated knowledge
must be >=economic time and <=Head; its own actual economic clock determines
age/coverage while later knowledge may supply permitted revisions/bookings.
Cash uses booked-by-economic-time with later-known evidence; it cannot replace
the as-known view or finance new risk.

Pure literal boundary example (no execution): last tick10, MARK source time10 and
max_age1. A query11/slot0 has age1 and is fresh; query12/slot0 has age2 and is stale.
If reserves expire11, the query11 reserve is already invalid (expiry<=query),
even while MARK is fresh. Independently, expected snapshot11 absent at query11
is unresolved coverage. advance through11 with no tick must produce Head time11
and exactly those query11 outcomes; it cannot reuse tick10's positive budget.
r3 differential fixtures query these same true times (and final-at-time slots),
including boundaries one microsecond apart. No scheduling/numerical policy is
chosen by this example.

```text
Balance = {as_of_us:T,view:as_known|restated,knowledge_cutoff_us:T,
 cash_usdt:D,receivables_usdt:D0 or null,liabilities_usdt:D0 or null,
 unrealized_usdt:D or null,economic_equity_usdt:D or null,
 reserved_margin_usdt:D0 or null,reserved_fees_usdt:D0 or null,
 simulated_budget_usdt:D or null,actual_available_margin_usdt:null,
 new_risk_supported:bool,reductions_supported:bool,
 valuation_refs:list[ID],reserve_refs:list[ID],null_reasons:ReasonMap}
CoverageIssue = {instrument_id:Inst,event_id:ID,
 reason_code:MISSING_EXPECTED_SNAPSHOT|UNRESOLVED_SNAPSHOT_MAPPING}
Readiness = {episode_id:ID,as_of_us:T,natural_exit_at_us:T or null,
 status:open|immature|complete|invalid,complete_at_us:T or null,
 assertion_refs:set[Key],blocking_reasons:list[ID],null_reasons:ReasonMap}
```

Unknown coverage outranks unknown T for A/L/E/budget; otherwise null aggregate
reason UNKNOWN_OBLIGATION_TOTAL. Held U null UNKNOWN_MARK/STALE_VALUATION; reserves
null UNKNOWN_RESERVES; restated budget null RESTATED_VIEW; actual margin always
null NOT_MODELED. E inherits unknown coverage/T/U; budget additionally reserves.
Positive known budget alone is not order approval. Flat U0 does not make unknown
T/A/L known. Readiness follows r3 precedence: hard stop; null-authority head invalid;
open; unresolved coverage; unknown total; unsettled P; insufficient/stale assertions;
complete. Null natural exit OPEN_EPISODE; complete_at reasons match the failing
condition, never a guessed time. It is cash/coverage readiness, not a target.
The exact readiness reason codes are OPEN_EPISODE,UNRESOLVED_SNAPSHOT_COVERAGE,
UNKNOWN_OBLIGATION_TOTAL,UNSETTLED_OBLIGATION,UNRESOLVED_FINALITY and
INVALID_ASSERTION_AUTHORITY, with the precedence stated above.

Component enum: lots|closed_slices|obligations|entries|links|events|registry|adapter_states|orders|decisions.
ScanFilter exactly `{kind:"all"}` or
`{kind:"owner",owner_kind:lot|obligation|adapter|order|decision,owner_id:ID}` or
`{kind:"record",key:Key}`. Owner kind and ID are both checked, never bare ID across
different logical kinds. lots/closed_slices accept lot owner; obligations/entries
accept obligation owner; links accept lot/obligation; registry/adapter_states
accept adapter; orders/decisions accept matching order/decision owner; events accept record filter. All components accept all; other
combinations reject SCHEMA_VIOLATION. Aggregate/non-obligation entries remain
available through all, not falsely attributed to an obligation filter.
PageToken exactly `{view_sha256:H,component:Component,filter:ScanFilter,
last_business_key:list[str|I]}`.
Page exactly `{view_sha256:H,component:Component,items:list[ComponentItem],
next:PageToken or null,null_reasons:ReasonMap}`; next null=END_OF_COMPONENT.
Scan null after uses START_OF_COMPONENT; limit
1..256. Tokens pin historical view and sort key; reject mixed views/component/
scope, stale nonexistent keys, symlinks and oversized output. A resource-limited
read returns no partial page and cannot mutate live finances; its audit records
RESOURCE_EXHAUSTED_READ, a read-only code distinct from write RESOURCE_EXHAUSTED.

```text
Lot = {lot_id:ID,episode_id:ID,instrument_id:Inst,opening_fill_id:ID,
 opened_at_us:T,direction:long|short,initial_contracts:I+,remaining_contracts:I,
 entry_price:D+,multiplier:D+,live_ranges:list[UnitRange],
 closed_slice_count:I,closed_slices_root:H}
Closed = {slice_id:ID,lot_id:ID,episode_id:ID,closing_fill_id:ID,closed_at_us:T,
 unit_start:I,unit_end:I+,realized_price_pnl_usdt:D,
 entry_fee_cash_usdt:D or null,exit_fee_cash_usdt:D or null,
 funding_cash_usdt:D or null,attribution_revision:I+,null_reasons:ReasonMap}
Obligation = {instrument_id:Inst,obligation_id:ID,kind:fee|funding,origin_id:ID,
 latest_revision:I+ or null,T_usdt:D or null,B_usdt:D,P_usdt:D or null,
 A_usdt:D0 or null,L_usdt:D0 or null,
 allocation_ref_count:I,allocation_refs_root:H,posting_ref_count:I,
 posting_refs_root:H,null_reasons:ReasonMap}
Entry = {entry_id:H,source_key:Key,transition:fee_claim|funding_claim|cash_posting|realized_pnl,
 obligation_id:ID or null,allocation_id:H or null,episode_id:ID or null,
 economic_at_us:T,available_at_us:T,cash_delta_usdt:D,pending_delta_usdt:D or null,
 receivable_delta_usdt:D or null,liability_delta_usdt:D or null,
 realized_pnl_usdt:D,null_reasons:ReasonMap}
Link = {owner_kind:lot|obligation,owner_id:ID,ordinal:I,
 value:{kind:slice,id:ID}|{kind:allocation,id:H}|{kind:posting,key:Key}}
```

Items are respectively Lot/Closed/Obligation/Entry/Link/Envelope/Generated/AdapterState/OrderRecord/DecisionRecord. A Lot's
live_ranges is [] or its one remaining FIFO contiguous range. Paged links replace
unbounded closed_slice_ids/allocation_refs/posting_refs lists, not their content;
ordinals/root hashes preserve r3 FIFO/set ordering as applicable. Reconstruct these
lists for small r3 comparisons. Entry local null reasons are NOT_APPLICABLE for
non-obligation realization, AGGREGATE_OBLIGATION for aggregate allocation/episode,
UNKNOWN_PRIOR_BALANCE/CURRENT_BALANCE/OBLIGATION_TOTAL for unknown deltas. Closed
nullable fee sides independently use UNKNOWN_OBLIGATION_TOTAL; funding additionally
UNRESOLVED_SNAPSHOT_COVERAGE. Other known fee/gross/quantity fields remain known.
Obligation latest_revision null UNKNOWN_AMOUNT; T/P/A/L null UNKNOWN_OBLIGATION_TOTAL;
B remains numeric. Exact newer attribution replaces current version only, not
historical slices. No empty-page skipping of unknown financial records.
attribution_revision is the same r3 deterministic positive counter,
1+sum(relevant available obligation revision ordinals), not max unrelated ordinal.

## 7. Journal, indexes, checkpoint and restart contract

Use append-only event/registry/commit segments with versioned indexed projections,
not full-journal replay on every append/query. Map business/global-owner/revision
IDs and origin/lot/posting links by key; maintain availability index, FIFO live
queues, calendar cursor/coverage, exact per-obligation levels and aggregate unknown
counters. Reverse indexes find only affected slices for a late correction. Keep
historical versions and all correction/ID targets addressable on disk; completed
episodes are not deletable merely because P0/finality was once observed.

Internal persisted rational is exactly `{numerator:str,denominator:str}`: signed
canonical integer numerator, positive canonical integer denominator, gcd1 and
zero denominator representation forbidden; zero is0/1. No float/cache rounding.
Persistent economic roots use a canonical ordered Merkle treap over typed business
keys: priority=H(["qf009.index-priority-v2",component,key]); compare priority then
key to break ties; BST order is the declared business-key tuple order. A node
hash is H(["qf009.economic-node-v2",component,key,canonical economic item,left,right]);
empty=H([component,"empty"]). This defines one root independent of insertion,
chunk/page layout or checkpoint timing without a count-dependent tree rebalance
that would rehash the full history each append. Index priority is a deterministic
storage rule from stable business keys, never a strategy random source or audit
catalogue seed. Store/version nodes and use reverse links for affected updates;
report actual visits/bytes, including pathological depth under the resource cap.
AdapterState is an economic component only for its approved causal typed value;
registry/raw audit metadata is always in separate roots. Other valid indexes may
cache work but must preserve these canonical roots and the frozen growth bounds.

```text
Checkpoint = {namespace:"qf009.streaming-checkpoint",schema_version:2,
 profile:"qf009-offline-stream-r2",ledger_id:ID,trajectory_id:ID,scenario_id:ID,
 committed_seq:I,cutoff:Cutoff,audit_prefix:H,economic_state_sha256:H,
 config_sha256:H,causal_policy_sha256:H,raw_catalogue_sha256:H,
 fact_store_sha256:H,adapters_sha256:H,schedule_sha256:H,
 journal_prefix_sha256:H,registry_prefix_sha256:H,
 calendar_cursor:I,next_tick_index:I,registry_next_seq:I+,files:list[CheckpointFile],
 context_receipt:ContextReceipt,fact_cursors:list[FactCursor],
 adapter_cursors:list[AdapterCursor],control_seq:I,control_sha256:H,
 resource_spent:{active_wall_us:I,total_written_bytes:I,attempts_started:I+},
 runner_state_coverage:"CAPTURED_DECLARED_ADAPTER_STATE_NOT_R3_ACCEPTANCE",checkpoint_sha256:H}
CheckpointFile = {component:config|raw_catalogue|facts|adapters|schedule|adapter_states|journal|
 registry|projection|ownership|dedup|revisions|calendar|context|cursors|orders|decisions|control,
 relative_path:str,format_version:2,bytes:I,rows:I,sha256:H}
AdapterCursor = {adapter_id:ID,last_invocation:Cutoff or null}
```

checkpoint hash excludes only checkpoint_sha256. File inventory is exact and
confined; no opaque pickle/importable code or ignored trailing bytes. Config/raw/
facts/adapter/schedule use the schemas above. Journal stores committed Envelopes
with commit sequence and slot; registry stores Generated. Projection stores the
typed View/financial component rows and their historical version cutoffs. Ownership
rows `{kind:ID,entity_id:ID,instrument_id:Inst,trajectory_id:ID,scenario_id:ID}`;
dedup rows `{key:Key,body_sha256:H,first_commit:I+,audit_refs_root:H}`; revision
rows `{kind:obligation|assertion,entity_id:ID,revision:I+,key:Key,cutoff:Cutoff}`;
calendar rows `{entry:ExpectedSnapshot,seen_key:Key or null,null_reasons:ReasonMap}`,
null seen_key=MISSING_EXPECTED_SNAPSHOT. Files are canonical JSON/JSONL with
context file containing ContextReceipt and ordered admitted semantic FactProjection
rows, cursor files containing tagged FactCursor/AdapterCursor, order/decision files
containing OrderRecord/DecisionRecord versions, control files as below, and
declared row types; projection rows are tagged `{cutoff:Cutoff,component:Component,
item:ComponentItem}`. No undocumented mutable index is authoritative on restore.
Private caches may be discarded and rebuilt **without changing economic state**.
resource_spent is audit/control state, excluded from economic roots. Active wall
time and written bytes include validation/checkpoints/recovery in this declared
attempt. Restore cannot reset them; the external bounded harness persists attempt
counts and conservatively debits interrupted work when exact crash duration is
unknown. No automatic new attempt is created to clear a cap. These counters never
become financial/adapter policy inputs.

Each committed segment has a closed CommitManifest `{seq:I+,previous_prefix:H,
request_id:ID,request_sha256:H,before:Head,after:HeadCore,files:list[FileRef]}`;
HeadCore is exactly Head with audit_prefix omitted. Its canonical hash is the next
audit prefix. Journal stores the exact request and ReceiptCore alongside envelopes;
ReceiptCore is Receipt with status fixed to committed and after replaced by
HeadCore. Files containing ReceiptCore never include the not-yet-computed next
audit prefix. Materialize the public Receipt by adding that manifest hash to
after.audit_prefix, so file/manifest/receipt identities are not circular. Saved
request/core and manifest reconstruct the same idempotent receipt after a crash.
All
canonical rows, business-owner/dedup and historical-version indices must agree;
restore validates/rebuilds them from the committed journal prefix, not solely a
self-consistent forged projection hash. Cold restore may scan that prefix once
within its declared budget; normal advances must not repeat it. Stored checkpoint
state is restored/validated, never a fresh account beginning at a later month.

AuditRow is `{audit_seq:I+,kind:"commit",manifest:CommitManifest,prefix:H}` or
`{audit_seq:I+,kind:"failure",at_committed_seq:I,error:Error,failure_sha256:H}`.
AuditPage is `{rows:list[AuditRow],next_after_audit_seq:I or null,null_reasons:ReasonMap}`;
null next=END_OF_AUDIT; limit1..256/2MiB, ascending audit_seq and pinned committed
evidence. failure_sha excludes itself. Failure rows are outside economic commit
prefixes and cannot move the financial cursor; pagination includes failures even
when multiple precondition rejections share the same committed sequence.

RV03 control persistence is a small append-only companion to those failure rows,
not another financial ledger or a restartable task framework:

```text
ControlRecord = {ledger_id:ID,profile:"qf009-offline-stream-r2",control_seq:I+,
 previous_control_sha256:H,at_committed_seq:I,audit_prefix:H,
 kind:write_guard|validated|integrity_stop|resource_stop|resolution,guard_id:ID,
 guard_input:FileRef,
 request_id:ID or null,request_sha256:H or null,error:Error or null,
 outcome:committed|not_committed|unknown or null,
 null_reasons:ReasonMap,control_sha256:H}
ControlPointer = {control_seq:I,control_sha256:H}
```

All guard inputs/control rows and CONTROL pointer publication use the same file,
containing-directory fsync and close/reopen readback barriers as financial blobs/HEAD.
Hash excludes only control_sha256, domain `qf009.control-v2`. Genesis control_seq0
hash is H([domain,ledger_id,profile,"genesis"]), with no control row. Other rows
strictly chain from the previous control hash, bind a reachable committed prefix
and run identity; guard_id identifies the original write_guard, not a financial
entity. Nullable request/hash use UNKNOWN_INPUT_IDENTITY/NONCANONICAL_INPUT if
transport is invalid; error null=NOT_APPLICABLE for guard/validated/resolution; outcome
null=NOT_APPLICABLE except resolution. Stop rows require their exact Error;
resolution requires the canonical request identity and outcome. All rows of a
guard bind its same guard_input bytes; unknown resolution does not clear a guard.
No control field may enter native/economic policy hashes.

Under the writer lease, durably append/fsync a write_guard and atomically publish/
fsync/readback the dedicated CONTROL pointer **before validating/admitting the
submitted canonical JSON write or attempting financial HEAD publication**. Save
the exact submitted JSON as an exclusive fsynced one-row guard_input first, so an
interrupted admission is reproducible; this is audit evidence, not committed input.
Before HEAD publication append/durably acknowledge a validated row for this guard
after all admission/semantic/resource checks succeed. Known non-latching
PREFIX_MISMATCH preconditions and read calls do not require a guard. A canonical
but malformed submitted write can have null identity and still leave a guarded
integrity stop. Invalid JSON/nonfinite wire syntax rejected before admission is
a non-latching transport rejection; it cannot reach financial code.
If initial guard durability fails, no financial publication or validation success
is allowed; the instance remains unusable until store/control preconditions are
re-established. Never claim a stop was durably recorded when its barrier failed.

There is at most one active write guard. On pre-publication semantic/resource
failure, append the corresponding stop row and durably update CONTROL before
acknowledging the error. On fully durable financial success, append its committed
resolution and durably update CONTROL before acknowledging success. On proven
noncommit append not_committed resolution. If any control append/pointer barrier
fails after the guard, retain the unresolved durable guard, report unknown and
refuse new writes. There is no gap where an acknowledged failure can disappear
after crash merely because the economic prefix stayed unchanged. Unacknowledged
control tails remain evidence; they cannot clear a durable guard or prior latch.

An interrupted write_guard with no durable validated/stop row is unclassified,
not proof that validation passed. Even proven financial noncommit alone cannot
clear it. One bounded recovery validation of its saved exact input against the
guarded predecessor and persisted/conservative resource debit may classify it:
append validated if all checks pass, otherwise persist the proper stop. If that
classification/barrier cannot finish, remain COMMIT_UNKNOWN. This prevents a
failed stop write followed by crash from forgetting a reproducible semantic error
or evading a resource cap. Recovery never executes new financial transitions.

`open`/`restore` always discover and validate the current CONTROL tip/chain under
lease independently of checkpoint, verify reachability of its committed anchors,
and reapply all durable integrity/resource stops and unresolved guards. The
checkpoint control_seq/hash is a lower-bound witness, never authority to rewind
the current tip. Missing/corrupt/truncated control evidence or an unresolved pointer
publication yields COMMIT_UNKNOWN / STORE_INTEGRITY_FAILURE, not ACTIVE. A stopped
run is not repaired by a consistent old economic journal. Current Head.status is
derived with precedence INTEGRITY_STOPPED, RESOURCE_STOPPED, COMMIT_UNKNOWN, ACTIVE;
economic roots/cash remain unchanged by this overlay. Receipt historical heads
remain literal saved values. Cold recovery validates the control chain once;
ordinary writes use its verified tip. Stop rows are monotone within this identity;
resolver can discharge one I/O guard, never clear an independent semantic/resource
stop. Resume after such a stop needs separately reviewed continuation/new identity,
with retained evidence, never automatic restored ACTIVE or larger resource limits.

Control writes/guard/readback/storage count inside the existing caps. If a cap or
I/O failure prevents durable stop publication, the already persisted guard keeps
the run blocked across restart. No automatic scavenging/truncation of tails or
unbounded resolver polling is part of this contract. A successful readback without
the required file/directory barriers never upgrades it to durable acknowledgement.

Write transaction blobs/indices to exclusive unpublished files; flush/fsync them
and their manifest, then under the existing single-writer lease atomically replace
the dedicated local store's small HEAD pointer. This HEAD change is the only commit
linearization point. Acknowledgement follows the required directory fsync/readback
and durable guard resolution described above.
Crash before HEAD preserves the old committed prefix; unreferenced tails remain
quarantined evidence. Crash after HEAD restores that exact committed transaction,
including request-id dedup, not half its registry/cash changes. Never truncate or
overwrite old segments to hide a failure. Single writer only; no multi-host/NFS
durability claim. Unsupported fsync/atomic semantics fail the storage precondition.

restore verifies exact profile/format/config/catalogue/adapter/schedule identities,
all file bytes/hashes/row counts, prefix sequence, source dependencies, scopes,
global ownership/revision chains and recomputed economic roots at checkpoint cutoff.
expected_committed_head prevents rollback to an older checkpoint while ignoring a
known committed suffix; replay the suffix or reject CHECKPOINT_MISMATCH. No implicit
version upgrade/import, future source registration or changed caps/seed. Past
as-known queries use version indexes or an earlier checkpoint plus bounded suffix;
restated recomputes from retained evidence in an isolated read view. Changed late
total/refund across any I/O chunk/checkpoint has the same available-time effect.
Unsupported repair uses a new explicitly reviewed run identity, retaining the old
one; it cannot retroactively overwrite old decisions or convert a stopped run to PASS.

Checkpoint covers ledger state, adapter progress, provenance **and every declared
AdapterState**, atomically under the same HEAD. adapter_states files contain the
closed AdapterState rows; restore must match each registered state schema/hash
and its predecessor links before invoking the next slot. An adapter is not allowed
to keep persistent hidden state outside this capsule. runner_state_coverage remains
CAPTURED_DECLARED_ADAPTER_STATE_NOT_R3_ACCEPTANCE until QR has independently checked
the actual R3 native state inventory and interrupted/uninterrupted end-to-end path.
That later inventory must include indicator-prefix reconstruction rules, pending
orders/cancellations/reservations, timing/sizing books and current decision state.
The kernel stores/validates the declared typed capsule and atomic binding; it does
not invent those native semantics. A missing schema/component prevents native
port registration/resume, rather than silently reinitializing it. The schema and
port are explicit future R3 deliverables using this defined interface; any field
incompatibility requires QD/QR version review before implementing the bridge.

## 8. Limits, differential acceptance and finite synthetic performance proposal

Limits exactly `{max_transaction_records:I+,max_transaction_bytes:I+,
max_page_items:I+,max_page_bytes:I+,max_resident_cache_bytes:I+,
max_exact_integer_bits:I+,max_adapter_reads:I+,max_adapter_emitted_events:I+,
max_adapter_input_bytes:I+,max_adapter_state_bytes:I+,max_adapter_wall_us:I+,max_store_bytes:I+,max_wall_us:I+,
whole_history_record_ceiling:null,null_reasons:ReasonMap}`.
The null ceiling reason is STORAGE_BOUNDED_NOT_RECORD_TRUNCATED. No4096 **history**
limit; transaction bound may be4096. Resident caches evict/reload verified pages,
not drop pending history. Exact-integer overflow, disk, wall or transaction limit
stops before commit without rounding, shortened universe or discarded old records.
If one complete tick cannot fit, stop; do not split it into a different economic
sequence. Read pages are bounded and resumable by pinned token, not truncated.
These storage/runtime limits are audit controls, not spending/strategy parameters.

Propose the following fixed first implementation acceptance register; QR may revise
it **before execution**. No benchmark or fixture stream is generated in this task.

| ID | Concrete fixture/request and required rejection or differential outcome |
| --- | --- |
| S01 | Reference-import tapes<=512 records per case: fee/funding signs, partials/reversal, signed quantum residues, R01-R06/B1. Expand pages and compare normalized financial balances, lots, slices, obligations, entries, readiness and every selected historical cutoff to exact r3. Alias only transport fields; never mask monetary/null/clock/ownership differences. |
| S02 | The t10/20/30/40/50 controlled-adapter fixture above: saved requests/witnesses/read sets/receipts; literal C1001,L0.2,budget1000.8 before posting, C1000.8/L0 after; noop at20. Compare generated FinancialBodies to a separately source-bound r3 tape, plus intermediate new slot views not expressible in r3. |
| S03 | Future-only raw change/rebuilt whole catalogue/provenance; all past economic projection, business IDs, adapter results and budget identical; complete audit roots/refs allowed to differ. Equal fixed catalogue repeats require byte-identical canonical economic/registry content except declared creation metadata. |
| S04 | Deliberate future fact read, forged q2, altered input/slot, different adapter/clock, audit-hash input/seed, unknown used as zero: precise causality/type errors, no committed prefix/ID/cash mutation; stop receipt retained. |
| S05 | One step versus arbitrary complete-tick partitions, including same-time revision/posting/assertion and both declared snapshot tie rules. Final-at-time expanded states match r3 and each other; intermediate slot state sees no later slot. Ambiguous fill tie/late crossing still rejects. |
| S06 | Duplicate request/body/Posting across checkpoint and new outer IDs; exactly one cash effect. Request conflict, same ID across BTC/ETH, allocation transfer, revision gap/cycle and posting restatement reject atomically. |
| S07 | Long trace>4096 with an old closed lot, outstanding funding and later fee unknown/restoration/refund across checkpoint/fold-labelled tick; no reset/drop. Reconstructed old as-known remains byte-identical; latest attribution follows same FIFO closing path. |
| S08 | Crash before blob fsync, before HEAD, after HEAD before receipt, and restart during suffix replay; recover exactly old or new full commit, replay request idempotently. Inject fsync/readback errors after HEAD: COMMIT_UNKNOWN cannot claim rollback or retry until resolve_commit proves committed/noncommitted; repeated receipt never adds cash. Corrupt/rehashed projected C or omitted global-owner entry must fail journal recomputation despite self-consistent file hashes. |
| S09 | Restore old profile/changed catalogue/unknown version/missing dependency/symlink/traversal/known newer HEAD: reject. Partial uncommitted tail never imports as a committed repair; old run evidence retained. |
| S10 | Historical as-known versus later restated booking, stale assertion then successor, missing expected snapshot and unknown fee sides. Non-tick query11 after tick10 uses true age/expiry/coverage; through11 with no tick seals Head11. Check fresh at max_age and stale+1us, expiry equality, due-snapshot equality; compare r3 at the same actual times. ViewCore hash has no nested viewid; build handle/receipt/page only after hash and reject a mixed-cutoff token. restated budget null; late finality cannot rewrite earlier readiness or become a label. |
| S11 | Exact >2^53/>28-digit amounts, mixed scales, hostile Decimal context, invalid float/bool/percent/exponent/nonterminating output and excessive integer size. No tolerance; resource failures are distinguished from financial impossibility. |
| S12 | Maximum transaction/page/output/cache/disk/wall bounds, including single oversized same-time tick. No truncated arrays or implicit cap increase. Paging/restart with tiny caches reconstructs exactly the unlimited-cache synthetic reference. |
| S13 | Native-bridge gate: the actual separately reviewed fixed-native port on synthetic prefixes, with registered numeric/intent/execution/state schemas and no market data. Full versus prefix inputs, future perturbation, interrupted/resumed timing/sizing/pending orders and exact resulting fills/budget traces agree. Until port/schema and this test exist, record R3_NOT_READY; infrastructure-only PASS is not native replay acceptance. |

All S01-S13 are **NOT_EXECUTED**. Differential reference excludes new storage/
registry/slot/paging hashes by construction but compares their reconstructed
financial content; new long traces and witness/storage failures require QR's own
literal oracle, not an r3 cap exception. Mapping new statuses back to r3 must not
turn missing provenance/unknowns into pass. Restore-from-committed-prefix is the
only automatic crash recovery; data repairs/semantic-stop continuations are not.

### 8.1 RV04: closed initial functional manifest

Initial acceptance is exactly the following **90 named cases**, S01–S12 only.
Each runs once in the QD producer functional suite and once in the QR independent
functional suite: two suite attempts,90 outcomes each, seed=NONE, no hidden random
or parameter sweep. QD owns producer fixture/store calls, QR owns independent
expected values, rejection reasons, state/receipt/artifact checks. For every case
both record PASS/FAIL/NOT_EXECUTED plus actual bodies/slots/reads/bytes/checkpoints;
one missing/failed case fails that suite. “PASS” below is the required future
outcome, not an execution result. S13 is explicitly
**NOT_EXECUTED/BLOCKED_NATIVE_PORT/R3_NOT_READY**, outside the90, not a skipped PASS.

Replica inventory is also closed: all cases use one fresh fixture except
S01.06=3,S01.10=2; S03.01/.02/.06/.07=2 each; S04.07=3;
S05.01/.02/.04=2 each; S08.08/.09/.11=2 each; S09.01/.02/.03=2 each;
S11.02/.04/.05/.08=2 each,S11.09=3; S12.02/.03/.04/.06=2 each.
This is exactly118 fixture instantiations per suite, with90 named outcomes;
within-fixture request/query/restart steps are not extra benchmark attempts.
No unused replica allowance can be reassigned to a new probe or failed-case retry.

Fixture conventions are finite: unless overridden, one independent fresh store,
C1000, one BTC instrument, m1, fee0, empty funding calendar, integer q1, economic
range[0,1000)us, knowledge end1200us, literal facts at10/20/30/40/50us, at most64
FinancialBodies/16 market Cell facts/8 ticks/4 slots per tick/2 checkpoints/16 query calls.
Reference-import uses one ReferenceFact per FinancialBody, not the16 market-fact bound.
No current time or random seed. A specified negative mutates only the named field
from that group's valid tape. Each case has at most four explicitly named wire
variants, counted inside that case and reported individually; no unspecified
“all permutations” loop. Ranges/limits below override only that convention, never
the global register. Small reference cases stay<=512 accepted bodies per tape.

| Case | Concrete fixture / clocks / size override | Required outcome / reason |
| --- | --- | --- |
| S01.01 | t10 buy10,m.001,price49900,fee.0005; close50100 at20 | gross2, fees.5; entry claim-.2495; exact r3 fields |
| S01.02 | same notional499,maker rate-.0001 at10 | signed fee cash+.0499, no taker substitution |
| S01.03 | long10 at5, short10 after25; m.001,MARK50000; snapshots10/20/30/40, rates +.0001/-.0001/+.0001/-.0001 | four funding cash totals -.05,+.05,+.05,-.05; no elapsed proration |
| S01.04 | A11/A12:10 units entry49900/exit50100,m.001,fee.0005,funding-.05; exit6 then4 | net .87/.58,total1.45; exact residual/FIFO |
| S01.05 | old long10 reverses short6 at100,m1,fee.00025 | reversal fee.4 splits old.25/new.15; old funding stays old |
| S01.06 | R02 F filled7/available9 crosses expectedS8; three fresh replicas: [F,S],[S,F],[F] | all LATE_ORIGIN_UNSUPPORTED, old prefix unchanged |
| S01.07 | R03 snapshot80,MARK79 available90,rate95,revision100 | FUTURE_PROXY_MARK; no trade-close substitution |
| S01.08 | MARK79 available79,S80,rate95,revision available100 | unknown at99, known at100; both r3 views agree |
| S01.09 | R04 assertion10,T revision20,settling Posting21,successor22 | complete10 -> immature20/21 -> complete22; old query immutable |
| S01.10 | R05 same f1 ID BTC/ETH at10, then separately valid unique scoped IDs | ID_SCOPE_CONFLICT for shared ID; unique case PASS |
| S01.11 | R06 unknown T,Posting-.02 at10,T=-.05 at20 | C999.98/B-.02; T/P/A/L/E null then L.03; unknown-prior deltas null |
| S01.12 | B1 three sequential episodes: unknown entry / exit / both fee sides, each4 units partial exits1+3; restore T-.25->-.20->-.30 and refund+.05/top-up-.10;<=128 bodies,24 ticks | only affected fee sides null; gross/other side known; exact old-slice restoration/residuals |
| S02.01 | separate P/X/environment: P submits long3 at10; X fills1@100/cancels2 at20; environment after X snapshots actual live range; P close1 at30,X fills40 | full intent/status/range transported, no private scan; ledger/native-placeholder state atomically matches literals |
| S02.02 | same tape, checkpoint after submission10, restore then20/30/40 | identical order identity/payload, all P/X/env states and finance |
| S02.03 | same tape, checkpoint after partial/cancel20 | no top-up/replayed fill; actual one-unit range persists |
| S02.04 | P owns typed state at10, X reads declared peer at20; P updates own state in later20 slot | X sees predecessor only; single writer; later slot sees new state |
| S02.05 | end50,knowledge end60; pending order submitted40/eligible49/expires50,reserve expires50; lifecycle50,old-origin Posting51/assertion55 | cutoff cancel/no new Fill/decision; expired reserve null; tail view retains open/immature exposure |
| S03.01 | t30 future price101->500, rehash whole raw catalogue/store | unchanged t10/20 numeric packets/state/IDs/roots; audit may differ (R01) |
| S03.02 | repeat same fixed source/config twice in two stores | canonical economic/registry content equal except declared creation metadata |
| S03.03 | initial10,context from0; closed facts economic1/7,available2/8; fact available10 | two context rows once; equality10 normal first release; cash unchanged |
| S03.04 | same context, required row's availability unresolved | FUTURE_DEPENDENCY before native initialization |
| S03.05 | qualified context available2 altered to10 in proposed packet | INPUT_BINDING_MISMATCH; original-clock evidence wins |
| S03.06 | S03.03 checkpoint before first slot, then after first slot; two explicit restart positions | same prefix/init once/cursors; no warmup finance |
| S03.07 | S03.03 change only future row20 and whole-file hash | identical economic ContextReceipt/first-slot state, changed audit binding allowed |
| S04.01 | packet at20 includes fact available30 | FUTURE_DEPENDENCY, no prefix change |
| S04.02 | external generated result q2, frozen port emits q1 | ADAPTER_RESULT_MISMATCH |
| S04.03 | omit one live unit range from S02 before-view selection | INPUT_BINDING_MISMATCH even after rehashing subset |
| S04.04 | substitute older pending intent/status at20 in S02 | INPUT_BINDING_MISMATCH |
| S04.05 | change peer state's value/hash or omit required own-state read | INPUT_BINDING_MISMATCH |
| S04.06 | policy selector requests execution_open or undeclared field | FORBIDDEN_INPUT before invocation |
| S04.07 | three fixed negative-port probes: direct future file read; entropy request; unregistered global/audit input lookup | file/global:FORBIDDEN_INPUT; entropy:UNSUPPORTED_RANDOMNESS; no effects |
| S04.08 | output replaces unknown funding/reserve with zero without source | INPUT_BINDING_MISMATCH; unknown retained |
| S05.01 | ticks10/20/30: one advance30 versus three complete-tick advances10,20,30 | same final financial/native-placeholder content and selected old views |
| S05.02 | same-time old10 close/new4 open atS20; two named snapshot-before/fill-before rules | eligibility10 versus4 per declared rule; intermediate views exclude later slots |
| S05.03 | remove required same-time Fill sequence in that tape | AMBIGUOUS_FILL_SEQUENCE |
| S05.04 | two fresh replicas after sealing20: new availability19; exact accepted duplicate | new PAST_AVAILABILITY; accepted duplicate no effect without first latching that replica |
| S05.05 | old origin10 revised/known/available30 after seal20 | legal current revision; as_known20 unchanged |
| S06.01 | duplicate request/Body/Posting before+after checkpoint20; three exact redeliveries | one cash/ID effect; saved receipt replay |
| S06.02 | same request_id different canonical request hash | REQUEST_CONFLICT/quarantine |
| S06.03 | BTC lot reference linked into ETH fee/posting | REFERENCE_SCOPE_MISMATCH; owner unchanged |
| S06.04 | allocation deliberately links another episode's unit range | ALLOCATION_MISMATCH |
| S06.05 | revision1->3 missing2 | REVISION_GAP |
| S06.06 | Posting correction points to itself | DEPENDENCY_CYCLE |
| S06.07 | Posting revision2 instead of new refund ID | UNSUPPORTED_POSTING_RESTATEMENT |
| S07.01 | fixed8192-body/8192-ReferenceFact history,1024 ticks,128-body advances,checkpoint4096,earliest closed lot corrected at end; economic end20000us | all retained versions/old query match literal oracle; no4096 history reset |
| S07.02 | 512 bodies:128 live lots of2 units,128 unpaid funding claims, then oldest partial exit/revision;checkpoint384;<=256 ticks/256 facts | complete paged live/episode selections or explicit resource failure; acceptance requires exact continuation within caps |
| S07.03 |128-body/128-ReferenceFact B1 closed-episode tape,<=24 ticks across named fold at20/checkpoint,unknown fee then restore/refund at30/40 | old as-known unchanged; latest attribution exact, no fold reset |
| S08.01 | fail initial guard durability before admission at10 | no financial publish/ack; unusable pending storage proof |
| S08.02 | durable guard/validated, fail before blob fsync at10 | old financial prefix; barrier-proven not_committed, no blind retry |
| S08.03 | fail after blobs before HEAD; orphan tail contains exact request | durable old HEAD -> not_committed; orphan never imported |
| S08.04 | fail after HEAD before receipt at10 | bounded resolver reconstructs one committed receipt/cash effect |
| S08.05 | readable new HEAD but directory fsync fails on two explicit resolver calls | both unknown, durable guard retained, no extra retry |
| S08.06 | same uncertainty then successful full barrier/readback; resolve twice | committed twice with one financial effect/same saved receipt |
| S08.07 | reachable request_id/hashA, resolve with hashB | REQUEST_CONFLICT/quarantine, never not_committed |
| S08.08 | rehash forged checkpoint C or omit global-owner row; two replicas | STORE_INTEGRITY_FAILURE from journal recomputation |
| S08.09 | old ACTIVE checkpoint, durably latched integrity / resource stop at same economic prefix; two replicas | restore respectively INTEGRITY_STOPPED / RESOURCE_STOPPED |
| S08.10 | stop/CONTROL publication fails after durable guard, crash and reopen | unclassified guard stays blocked; bounded saved-input validation persists original stop, never silently ACTIVE |
| S08.11 | interrupt suffix recovery at one fixed boundary, reopen; then corrupt CONTROL hash in separate replica | valid suffix recovers within budget; corrupt control STORE_INTEGRITY_FAILURE, not ACTIVE |
| S09.01 | restore profile-r1 or unknown schema3 checkpoint; two replicas | UNSUPPORTED_VERSION for both; no upgrade |
| S09.02 | change catalogue or adapter identity; two replicas | CHECKPOINT_MISMATCH |
| S09.03 | remove declared dependency or symlink outside root; two replicas | STORE_INTEGRITY_FAILURE / SCHEMA_VIOLATION |
| S09.04 | path ../escape in source ref | SCHEMA_VIOLATION, no read/write outside root |
| S09.05 | restore checkpoint10 with expected HEAD20 and intact declared committed suffix20 | validate/replay suffix to Head20, never rollback or ignore expected HEAD |
| S09.06 | restore older context/adapter cursors than committed first slot | CHECKPOINT_MISMATCH; no duplicate initialization |
| S09.07 | prior available2 row offered as new context after seal20 | PAST_AVAILABILITY; genesis exception unavailable |
| S10.01 | economic Posting10 learned20; query as_known10 then restated10/knowledge20 | historical cash preserved; restated separate, budget null |
| S10.02 | missing due snapshot11 at query11 then late legal evidence | coverage unresolved until supported; no zero replacement (R06) |
| S10.03 | legal stale assertion then successor | immature not integrity stop; original complete time not inherited (R04) |
| S10.04 | MARK source10/max_age1; queries10/11/12 | fresh10/11,stale12; equality exact |
| S10.05 | reserve expiry11; query10/11/12 | valid10,unknown11/12, no stale cached budget |
| S10.06 | through11 with no tick after10; query11,then attempt new availability11 | Head11,proper coverage/age; new sealed-time delivery PAST_AVAILABILITY |
| S10.07 | construct ViewCore/handle/ReceiptCore/manifest and page token; mix token from20 with view10 | no hash cycle; SCHEMA_VIOLATION for mixed token |
| S10.08 | current MARK raw available10 selected at20 and30, emitted consumer valuations known20/30; max_age100 | repeat fact selection no duplicate delivery; correct distinct source/consumer clocks |
| S10.09 | after seal20 new valuation body available10 from old selected point | PAST_AVAILABILITY; no source clock rewrite |
| S11.01 | exact amount9007199254740993 and a31-digit integer; rational allocation | exact r3 fields, no float/Decimal28 rounding |
| S11.02 | mixed scales .1/.03,quantity split1/3,residual; Decimal precision6 then50 | exact same output both contexts |
| S11.03 | float money in candidate body | INVALID_DECIMAL |
| S11.04 | bool contract count or fractional integer count; two replicas | INTEGER_CONTRACT_VIOLATION for both |
| S11.05 | percent string or exponent string; two replicas | INVALID_DECIMAL |
| S11.06 | exact rational1/3 requested as unrounded wire D | NONTERMINATING_AMOUNT |
| S11.07 | exact integer8193bits versus cap8192 | RESOURCE_EXHAUSTED, no rounding |
| S11.08 | negative price / wrong-price-kind trade-as-MARK; two replicas | DECIMAL_DOMAIN / WRONG_PRICE_KIND respectively |
| S11.09 | source_record differs from source_seconds*1000000 by1us; then wrong mapping_rule_id; then unknown mapping in three replicas | CLOCK_CONTRADICTION; SNAPSHOT_MAPPING_MISMATCH; unresolved coverage respectively (A33) |
| S12.01 | one complete tick4097 bodies with transaction cap4096 | RESOURCE_EXHAUSTED, no split/partial commit |
| S12.02 | per-slot selected input exceeds32MiB or262144 scalar reads; two replicas | RESOURCE_EXHAUSTED before evaluation, no truncated selection |
| S12.03 | state exceeds2MiB or output65 events; two replicas | RESOURCE_EXHAUSTED, no checkpoint of incomplete state |
| S12.04 | injected disk ceiling / wall ceiling; two fixed boundary failures | RESOURCE_STOPPED persists; no automatic larger cap |
| S12.05 | page257 items or page bytes>2MiB; two read calls | RESOURCE_EXHAUSTED_READ, no partial page/no financial mutation |
| S12.06 |S07.01 history/clock bounds at fixed cache budgets64KiB and8MiB, page64,checkpoint4096 | exact reconstructed results equal within hard limits; no history dropped |
| S12.07 | serialize restore+resolve spend at limit and interrupted-work debit | no counter reset/new free attempt; RESOURCE_STOPPED if exhausted |

S07.01's8192-body tape is fixed:1023 eight-body cycles plus eight suffix bodies.
Each cycle opens/closes1 unit100/101, revises opening fee to-.1 and posts-.1,
then emits MARK100,zero reserves,a flat funding snapshot and known-zero funding
revision. Each fits a complete tick with declared fill-before-snapshot rule.
Suffix revises the earliest fee unknown then-.05, posts refund+.05, emits
MARK/reserves/flat snapshot/zero funding revision and a scoped first assertion.
Ticks are10+cycle_index, suffix at1100, end20000; checkpoint after body4096.
S07.02 is a distinct fixed512-body tape:128 opening Fills(q2@100),128 snapshots
and128 known authoritative funding revisions(T=-.01 each,unposted),126 MARK100
valuations,one oldest-lot reduction(q1@100) and one old opening-fee revision(T=-.1).
Use ticks10..137 for the openings/snapshots/claims, MARKs after them at138..263,
and suffix at264; checkpoint after384 bodies. All128 lots/claims remain present
until the single partial exit; complete allocation/residual evidence is retained.
S12.06 reuses S07.01, not a new random tape. Overlarge inputs in S12.01–03 are
negative fixtures; expected controlled rejection is acceptance, not a cap waiver.

This manifest freezes case identities, finite variant counts, data/clock bounds
and required reasons. Implementation handoff must pin exact fixture bytes and
independent expected-state tables (including any precise r3 parser error within
the named transport alternatives) **before** execution. Conflicting literal/error
expectations require QR review, never update expected values from producer output.
The published manifest may clarify construction without changing these90 IDs,
adding retries, shrinking hard cases or increasing limits; otherwise return for
a new reviewed register. No case is deleted because the120s suite might fail.

S13 later requires a separate frozen finite native fixture/case/attempt/CPU/wall/
RSS/disk register and actual pinned policy, numeric/feature/intent/execution/state
schemas. It must cover complete native timing/sizing/feedback and full-state
A23/A26/A34; the current90 cases do not claim those criteria passed. Original
QF00634-stage mapping remains unchanged: financial isolation is S1 only; raw
support S2, actual full-state native replay S3, labels/purge/sufficiency S4/R4 and
future model/evaluation/fresh fit permission R5 remain separate.

Finite performance ladder: N=512,2048,8192,32768 FinancialBodies on one fixed
deterministic repeating synthetic tape, one account, fixed active-state pattern
(one current lot and bounded unresolved set), with old closed references retained
and a late correction to the earliest lot at the end. Record body/event counts
separately from registry/no-op slots. Complete ticks/transactions<=256 bodies,
checkpoint every1024 bodies, final historical/late-revision query included.
Two repetitions each, **8 measured producer attempts total**, no warmup/retry
builds. Small reference comparisons S01/S02 are functional tests, not these timing
runs. One90-case S01–S12 producer suite and one90-case QR independent suite are
the two functional attempts; S13 is outside this initial register. QR additionally
checks the **eight saved producer benchmark artifacts and their ratios inside its
same120s suite**; it does not run another eight benchmarks or regenerate timings.
Any independent reference/long-tape computations count inside that suite's cap.

Proposed hard producer benchmark budget:60s each/480s aggregate measured wall,
RSS<=256MiB, resident cache<=8MiB, page<=256 items/2MiB, transaction<=4096 bodies/
8MiB, exact integers<=8192bits, adapter<=262144 supplied field reads/64 emitted events, input<=32MiB, declared
state<=2MiB and per invocation<=10s, all included in the60s attempt budget.
Each attempt new output<=512MiB; all8 outputs together<=2GiB including failures,
journals/checkpoints/traces; input raw not copied. Functional producer/QR suites
each<=120s/256MiB RSS/128MiB output, one execution each before any failure review.
Total proposed wall budget720s, new output<=2304MiB across both suites and ladder.
These are proposed synthetic engineering limits, not R3 market-run authorization.

Before measurement record fixed host/Python/implementation IDs, cache budget and
schema. For each adjacent4x N use median of its two timings: T(4N)<=6*T(N)+0.25s;
canonical economic/journal output bytes(4N)<=4.5*bytes(N)+64KiB; peak process RSS
at32768 <= RSS at512 +32MiB and absolute256MiB. The fixed active pattern separates
history/index retention from genuine growth in open economic state. Test S07/S12
also exercises a growing pending set via bounded paging; do not suppress it to
claim bounded live state. Report commit/query/checkpoint/restore times separately,
raw values, allocation visits and exact persisted counts. A failed ratio/resource
ceiling is a failed candidate; no outlier deletion, new repetition, larger cap,
amortized-away late correction or excluding fsync/validation until it passes.
QR reviews any proposed new resource register before a fresh attempt. Performance
is not allowed to alter economic results or reduce the test universe.

## 9. Error registry, proposed ownership and handoff

In addition to the new codes in sections5/6, retain the financial reference codes
as the exact frozen r3 code registry below (static extraction, not a runtime test):

```text
ALLOCATION_ID_MISMATCH,ALLOCATION_MISMATCH,ALLOCATION_QUANTUM_TOO_COARSE
AMBIGUOUS_FILL_SEQUENCE,AMBIGUOUS_RESERVES,AMBIGUOUS_VALUATION,CALCULATION_CONTRACT
CLOCK_CONTRADICTION,CONFLICTING_EVENT_REVISION,CONFLICTING_OBLIGATION_REVISION
CONFLICTING_POSTING_REVISION,DANGLING_ORIGIN,DANGLING_REFERENCE,DECIMAL_BOUNDS,DECIMAL_DOMAIN
DEPENDENCY_CYCLE,DOUBLE_COUNTED_RESERVES,DUPLICATE_RULE,DUPLICATE_SET_MEMBER,DUPLICATE_SOURCE
ELIGIBILITY_MISMATCH,EMPTY_ALLOCATION,FEE_RULE_MISMATCH,FORMULA_MISMATCH
FRACTIONAL_MICROSECOND,FUTURE_CALCULATION_INPUT,FUTURE_PROXY_MARK,FUTURE_RULE
ID_SCOPE_CONFLICT,INTEGER_CONTRACT_VIOLATION,INTEGRITY_STOPPED,INVALID_DECIMAL,INVALID_HASH
INVALID_ID,INVALID_PRECISION,INVALID_QUANTUM,INVALID_SCOPE,INVALID_UNIT_RANGE,JSON_KEY_TYPE
LATE_ORIGIN_UNSUPPORTED,MISSING_CONTRACT_CONVERSION,MISSING_PROVENANCE,MULTIPLIER_MISMATCH
MULTIPLIER_OR_QUANTITY_MISMATCH,NONCANONICAL_INPUT,NONTERMINATING_AMOUNT,NULL_REASON_CONTRACT
OBLIGATION_ORIGIN_CONFLICT,ORIGIN_OUT_OF_RANGE,OUT_OF_SCOPE_INSTRUMENT,OUT_OF_SCOPE_MODE
OVERLAPPING_RULES,OVERLONG_ORIGIN_ID,REFERENCE_SCOPE_MISMATCH,REVISION_GAP,RULE_MISMATCH
SCHEMA_VIOLATION,SNAPSHOT_MAPPING_MISMATCH,SOURCE_HASH_MISMATCH,STALE_VALUATION
UNDECLARED_SNAPSHOT,UNIT_OR_ROLE_VIOLATION,UNKNOWN_EPISODE,UNKNOWN_LIQUIDITY_ROLE
UNPROVEN_AUTHORITY,UNPROVEN_FINALITY_AUTHORITY,UNRESOLVED_POSTING_NOT_APPLIED
UNSUPPORTED_NAMESPACE,UNSUPPORTED_POSTING_RESTATEMENT,UNSUPPORTED_RECORD_TYPE
UNSUPPORTED_REVISION,UNSUPPORTED_RULE_KIND,UNSUPPORTED_VERSION,WRONG_PRICE_KIND,ZERO_FILL
ZERO_POSTING
```

FIXTURE_CAPACITY_EXCEEDED belongs to the unchanged reference only; new profile
uses RESOURCE_EXHAUSTED. Resource/code-registry comparison is a static review
obligation, not permission to accept arbitrary exception text. Reject JSON paths
identify the offending object; cross-record failure binds the complete candidate.

Proposed future exclusive files (unallocated until QR review + new dispatch):

| Owner | Proposed paths / scope |
| --- | --- |
| QD | `research/qd009/streaming_ledger.py`, `tests/test_qd_streaming_ledger.py`, unique QD009 report and ignored `research/.data/qd009/` synthetic stores; one small stdlib ledger/controller-binding/storage module, no new framework or dependencies |
| QR | `research/qr009/validate_streaming_ledger.py`, `tests/qr_research/test_qr009_streaming_ledger.py`, its independent contract-review report and ignored synthetic oracle evidence; never import producer arithmetic as expected values |
| QD proposal author | This interface request only; QR review belongs in its own file. Do not edit old QD007/008 or shared journals while waiting. |

The prior stage4 episode-export allocation is not consumed by these distinct
file names. MARK streaming/query, numeric/native adapter, real execution scenario,
R3 scheduler/runner state schemas and labels need their own contracts/owners;
they are not implementation creep into this module. Independent data/ledger
acceptance and resource-bounded implementation approval remain prerequisites.
The concrete native bridge remains proposed QD `research/qd008/native_adapter.py`
and `tests/test_qd_event_replay.py`; QR reviews its numeric/intent/execution/state
schemas and supplies independent future-perturbation/end-to-end checks. This port
can be registered through the initial adapter/state transport once those exact
contracts/code pass; the reviewed typed transport is intended to cover the known
purpose. If S13 exposes a representational gap, QD authors a typed delta and QR
reviews it before that bridge is claimed ready. The ledger's atomic commit can
include its declared state, but completeness is not self-certified by the adapter.

Requested QR decisions: accept/revise the controlled deterministic adapter port,
registered typed input/output/state contracts and explicit native-bridge gate; reference-import versus generated visibility
and same-time slot semantics; new paged/root/checkpoint transport preserving full
r3 financial semantics; finite resource/growth register. These are infrastructure
reviews, not another request for approved fees/clocks/multipliers. Slippage,
capacity, capital, reserve policy and native timing feedback remain outside this
contract and require QR scenario proposal/any necessary user decision later.

Current delivery is this proposal only. No code/tests/benchmark/stream generation,
new raw reads, features/labels/fit, network, app/engine, real config/credentials,
main integration/push or Windows/NAS work. Static structure/reference/identity/
scope/diff checks are documentation checks, not implementation PASS. After the
one-file commit, stop at READY_FOR_QR_CONTRACT_REVIEW; no response is approval and
no new file allocation or market run is inferred.

Amendment delivery checks: exact QR4d4e530/QD89cf347 review-object SHA256 and
base/status; one-file diff and unchanged financial payload/error registry; closed
new type references,90 unique case IDs/118 fixture counts, balanced fences, schema/profile/hash
domain consistency, fixed budget arithmetic and source-checkout preservation.
These are documentation/stdlib checks only. All S01–S13, producer/QR functional
suites, eight measured benchmarks, persistence fault injections, native bridge,
MARK/query validation, market replay and fit remain NOT_EXECUTED by this task.
The exact byte-identical r3 FinancialBody definition and retained76-code registry
are compared with19cd4c7; no historical research claim or user choice is added.

RV closure offered for independent QR review: RV01§4.1/types/components/checkpoint;
RV02§3.1/initial context/cursors; RV03§5.1/CONTROL/restore; RV04§8.1/90-case manifest
and unchanged initial caps. R03/R05 mechanical links are§3.2/4.2. They are proposal
changes, not self-approved implementation acceptance. The result commit is the
one changing this file; resolve with:

```sh
git log -1 --format='%H' -- docs/interface-requests/qd-qf009-streaming-ledger.md
```
 Stop after that one-file
commit and wait for QR's exact-object review. Main, existing staged/unstaged user
work, prior reports, QR files, native code, old r3 and shared journals stay intact.
