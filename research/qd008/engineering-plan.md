# QD008 data-repair engineering preflight

2026-10-28 Australia/Melbourne. **PLAN_ONLY; SOURCE_POLICY_NOT_FROZEN.**
Dispatch `QF-DISPATCH-20261028-QD008-ENGINEERING-PREFLIGHT-1`; base
`45bf3e036516b97570b3630cc19684af26713132`, branch `codex/qd-cache-safety`.
This proposes a small offline candidate builder, not a choice of historical truth
or permission to implement/build. QR owns source-policy acceptance.

## Existing paths and boundaries

| Location at this base | Observed behavior / engineering consequence |
| --- | --- |
| `research/qd004/history_intake.py:51,364,401,482,490` | REST JSON uses `parse_float=Decimal`; archive CSV numeric text becomes Decimal. `text()`/CSV normalization preserves decimal values and source ID/one-based row. Fractional nonnegative volume is allowed here. This cannot restore precision already omitted by a provider. `number()` accepts a Python float via `str()`, so it is not a sufficient strict new-input boundary. |
| Same file `:380,556,587` | `numeric()` converts nonintegral values to float for diagnostics; QC arithmetic uses ambient Decimal division/sum. These are not the normalized CSV volume writer, but must not become the new exact builder or difference oracle. |
| Same file `:67,84,104,223,628` | Confined relative paths, write-once files, collector lease/journal, raw hashes and final manifest already exist. `write_once` writes directly to fresh files; no whole-dataset atomic publication contract exists. Preserve these old paths, budgets, raw objects and quarantine evidence. |
| `research/qd005/canonical_history.py:148-167,185-218` | v2 rejects `v != int(v)`; aggregation sums `int(child_volume)`. Removing only the gate would truncate fractions. OHLC Decimal selection is exact; integral sums avoid ambient Decimal rounding. Keep the frozen v2 builder unchanged. |
| Same file `:71,90,222,261,290` | Frozen v2 spec/base identities; hourly/funding copies, derived 4h/day lineage, fresh-root-only writer and disk recomputation. It cannot accept a new source/range by editing its old constants. Files are written into the final root before completion, rather than staged for atomic publication. |
| `src/data_fetcher.py:175,312-317`; `src/exchange_gate.py:151` | pandas dtype inference and SDK float conversion, with `sum` fallback for absent `v`. Suitable neither as exact-volume ingestion nor as an approved replacement loader. Leave native behavior unchanged; new candidate requires explicit volume unit and rejects absent `v`. |
| `src/crypto_ml.py:13-56` | Feature version1/order of 21 names stays frozen. Validation casts a local OHLCV frame to float, but rolling volume/log operations use the original grouped frame. Decimal/string columns are not a supported direct exact-data input; fractional volume is numerically representable only approximately in native floats. |
| `src/backtest.py:138-174,384-389`; `src/strategy_signals.py:15-56` | Native preparation sorts/deduplicates, consumes pandas numeric arrays and assumes fixed bar clocks; its funding remains endpoint/elapsed-time proration. Data validation must precede any future adapter. Exact repair does not approve economic labels or fix native accounting. |
| `research/qr003/replay_probe.py:48-60,90-108`; `research/qd007/event_ledger.py` | Old observer accepts native inputs and snapshots Integral/Real, not a general Decimal transport. QD007 is frozen synthetic integer-ticket accounting, not an hourly-data loader. Fractional market volume does not authorize fractional orders or a ledger schema edit. |

Retain native signatures, cache names/CSV units, model feature order/version,
strategy/risk/defaults and shared contracts. Do not retrofit this candidate into
runtime caches, original v1/v2 outputs, old spec/constants or QD007.

## Minimum proposed implementation after a separate handoff

Proposed exclusive QD files: `research/qd008/repair_history.py`,
`tests/test_qd_data_repair.py`, one sanitized
`research/qd008/results/candidate-summary.json`, this plan and the QD report.
Ignored immutable outputs: `research/.data/qd008/<candidate-id>/`; separate fresh
reproduction root. Names/schema version remain proposals until QR freezes spec.
One standard-library offline module with build/verify entry points is enough;
no downloader, service, database or generalized ingestion framework is needed.

1. Require the explicit approved source manifest/spec SHA and review commit.
   Validate every selected object hash/length/completeness, exact source identity,
   field mapping/units and per-instrument half-open partition. Freeze inputs before
   construction and recheck before publication; bind both raw hashes and policy
   hash in output. The reviewed evidence handoff is not that approval.
2. Select complete hourly OHLCV tuples according to the frozen source partitions,
   never REST `v` plus old OHLC. Keep all disagreeing old/new tuples and source
   references in a field-level delta/conflict file, including unchanged fields.
   Undecided overlaps stop publication. An explicit approved whole-row selection
   may document a conflict, but cannot silently make it disappear. Quote turnover
   remains separately named raw evidence, never a contract-volume replacement.
3. Parse source decimal tokens exactly, without a float intermediary. Enforce the
   frozen lexical/domain/size limits; reject bool, missing, nonfinite and negative
   volume. Preserve original lexemes in raw lineage; canonical CSV uses finite
   plain decimal text with a documented zero/trailing-zero rule. Use integer
   coefficient/scale arithmetic for volume sums/deltas, or an explicitly derived
   sufficient local Decimal context; never ambient Decimal addition, `int(v)`,
   tolerance, rounding or zero-fill. JSON monetary/volume values stay strings.
4. Require ordered unique complete UTC hours and explicit availability semantics.
   For each complete aligned 4h/day bucket use first open, maximum high, minimum
   low, last close and exact sum of child volumes. Availability is no earlier
   than bucket close and every child's declared availability; mark proxy clocks
   as assumptions, not observed historical arrival. Missing/interior/partial
   buckets cannot become usable bars; record withheld rows/ranges. Apply the
   approved economic end-exclusive **2026-10-01 00:00 UTC**, with start/warmup
   supplied by QR; document excluded old October tails without modifying them.
5. Each hourly row resolves to object SHA, original row/field mapping, request
   identity/retrieval time and policy partition; retain all approved duplicate
   aliases. Each derived row references the ordered exact children and parent
   file hashes. Manifest binds instrument IDs, seconds/UTC, contracts volume,
   USDT/base prices, schema/policy/code versions, input/output/lineage/delta
   hashes, counts, bounds, exclusions, unknown arrival and unresolved limitations.
   Keep the manifest's own external hash outside its preimage.
6. Build into an exclusive sibling staging directory. Reject symlinks/traversal
   and any existing candidate ID. Close/fsync outputs, write the manifest last,
   independently reread the staged inventory, then use a short permanent parent
   publication lock to check destination absence and rename on the same local
   filesystem. All publishers must honor that lock; never replace an existing
   candidate. Readers only accept a published root with an explicitly pinned
   manifest. If power-loss durability is required, implement/test directory fsync
   on the target filesystem; atomic visibility alone is not that guarantee.
7. Failure leaves a clearly unpublished staging root for inspection and no valid
   final root. Reuse already accepted immutable raw objects by hash, with no new
   GETs. Do not resume or mutate a partly written dataset: restart a whole build
   under a fresh attempt identity. Conflicting same-row identities, missing hours,
   altered frozen inputs or unknown source policy fail closed. Identical duplicate
   handling needs a frozen rule retaining every raw reference; no silent sort/
   deduplication to hide descending input or conflicts. A MARK alias policy, if
   needed, must arrive separately frozen; this plan does not invent one.

Funding and MARK are outside the minimum volume transform. Preserve their old
files/references; any requested candidate inclusion, cutoff projection or MARK
aliasing needs explicit QR semantics/lineage. Never infer historical schedules,
multiplier changes, fractional order capability or true arrival from this repair.

## Independent inputs and acceptance for the implementation stage

Producer fixtures must use literal expectations, not the builder as oracle:

| Fixture | Required evidence |
| --- | --- |
| Four hourly OHLC rows `(10,13,9,12)`, `(12,14,11,13)`, `(13,15,10,11)`, `(11,12,8,9)` and volumes `0.1,0.2,1.25,2.005` | 4h `(10,15,8,9,3.555)` exactly; six repetitions yield daily volume `21.33`. Direct daily equals six complete 4h groups field by field. |
| `9007199254740993.1`, `5623243.7`, zeros and long mixed scales | Raw-to-normalized equality, exact sums/deltas under hostile ambient Decimal precision; no 2^53 float loss or fractional truncation. Invalid grammar/nonfinite/negative/null/bool fail. |
| Two sources with same timestamp, different close and volume | No Frankenstein tuple; unresolved policy fails. Approved whole-row policy gives one traceable tuple and preserves both alternatives and every per-field delta. |
| Missing/duplicate/reversed/shifted hour; future child perturbation; cutoff inside bucket | Reject structural errors; approved identical aliases retain all refs; no partial bucket emitted; previous available bucket bytes unchanged. Test open/close and one-second-before availability. |
| Rehashed wrong OHLC/volume/parent-row order or source-row reference | Independent recomputation catches semantic corruption despite internally consistent file hashes. All raw and derived lineage resolves exactly. |
| Two writers, crash before/after manifest, disk failure, existing destination, changed input, path/symlink escape | At most one immutable published candidate; no partial final visible; restart does not overwrite evidence. Full reread and exact inventory/hash checks pass on success. |
| Second build; old v1/v2/QD007 fingerprints | Same data/lineage/delta bytes and semantic manifest (declared creation provenance excepted); prior evidence unchanged. No model or runtime activation. |

QR's independent validator must use its own parser/aggregation expectations and
the same pinned raw inputs, not producer-derived totals or producer helper imports.
Before a full build, receive: exact frozen spec/commit/SHA; complete source object
inventory/hash/row basis and whole-row partition/overlap policy; explicit disputed
BTC close disposition and prefix-era evidence/assumptions; symbols/start/warmup/
cutoff; decimal grammar/units/canonical schema; duplicate/MARK rules if in scope;
availability/exclusions; output identities/resource limits/reproduction budget;
independent acceptance cases and any necessary user source-policy decision.

No repaired candidate may feed replay, labels, features/research or fitting until
QR accepts it and any required user source decision is recorded. A later separately
reviewed offline adapter may project exact strings into finite float64 numeric
DataFrames, retaining the exact dataset/hash separately and documenting conversion
error; no exact accounting or source validation can use that float projection.
Its compatibility tests must cover fractional volume and unchanged feature order.
Fitting still requires fresh user confirmation. No adapter or experiment runs now.
