# QF-QR-005: canonical hourly research data v2

Status: READY_FOR_QD_DATA_ONLY_BUILD; rules frozen after QD counterpart review. QR owns semantics and independent acceptance; QD owns
the builder and dataset. No runtime/shared interface migration or training.
Human authorization: BTC/ETH data rules and reacceptance, 2026-10-28. File claims:
QF-DISPATCH-20261028-QR005-SPEC-1. Preserve every QR004/QD004 artifact unchanged.

## Decision and compatibility

Native v1 faithfully retained independent Gate timeframes but failed its exact
cross-timeframe equality rule in 2,068 coarse windows. Source checks reproduced
differences, including REST versus REST; they did not prove which source is true.
v2 deliberately changes the research input definition: use the previously frozen
hourly trade-price stream for all price timeframes, before observing new returns.
Hourly values are neither edited nor selected using profitability. Native 4h/1d
remain immutable diagnostic evidence, never fallback or training inputs in v2.
This is a versioned derivation, not correction of exchange history or a relaxation
of v1's failed tests. Internally consistent data can still be historically biased.

Only Gate USDT linear perpetual BTC_USDT and ETH_USDT. Price is USDT/base, volume
is contracts (not quote turnover, base-asset volume or comparable cross-coin units).
No spot, mark, index, other coins, new downloads or extension of the frozen range.
UTC half-open range [1672531200, 1793091600), 2023-01-01 to 2026-10-27 09:00.
2023 remains warmup; any subsequent scored baseline starts 2024-01-01 UTC.

## Deterministic bar definition

Bind the v1 manifest, normalized input files and diagnostic evidence by SHA256 in
data-acceptance.json. Copy 1h and funding CSVs byte for byte, including provenance.
Keep the original archive-through-September/REST-tail source choice, overlaps and
duplicate lineage. Resolve raw provenance through the immutable base manifest;
do not download, reselect, average, fill, clip, or silently omit any eligible row.

For interval D in {14400,86400}, a bucket starts at an integer multiple of D
seconds since Unix epoch and contains hourly opens [t,t+D). Require exactly D/3600
unique consecutive grid-aligned hours. Compute with Decimal, never float:

- open = first child open; high = maximum child high; low = minimum child low;
  close = last child close; volume = sum of child contract volumes.
- timestamp = bucket open; available_at = maximum child available_at = t+D.
  All children have available_at = open+3600. A consumer may use the bucket only
  when available_at <= decision_at. The interval is not available at its open.
- No tolerance, partial interior bucket, duplicate child, nonfinite value,
  negative volume, nonpositive price, invalid OHLC or nonintegral contract count.
- The fixed cutoff falls inside the final 4h and daily buckets. Do not emit those
  unclosed buckets. Explicitly record their complete available child hours and
  remaining hours beyond cutoff. Retain all 1h rows. This is not a data gap or
  shortening of the experiment; the cutoff remains 09:00 UTC for both coins.
- Required complete counts per coin: 33,489 1h; 8,372 derived 4h; 1,395 derived 1d.
  Final withheld bucket: 4h has 1/4 children; daily has 9/24 children.

Example four children (O,H,L,C,V): (10,13,9,12,1), (12,14,11,13,2),
(13,15,10,11,3), (11,12,8,9,4) produce (10,15,8,9,10), not the mean price.
With opens 00:00..03:00 the result is usable at 04:00, not 03:59:59.
Changing a child whose availability is later than T must not change any bucket
available at or before T. Aggregating six derived 4h bars must equal the derived
daily bar, as well as direct aggregation of 24 hours, exactly.

## Funding and replay boundary

Preserve each actual settled funding timestamp, rate, source and availability
byte for byte. Units are fraction per settlement; available_at is its exact source
timestamp. No rounding seconds to an 8h grid, merging, filling zeros or use of
predicted funding_updates. The 8h reference is diagnostic only. Report observed
inter-event durations and offsets; do not infer an authoritative historical
schedule from those counts or a current funding_interval field.

Availability for both bars and funding remains an idealized proxy, not observed
publication/arrival. Later archive retrieval is provenance, not an assertion that
revised values were available contemporaneously. Current contract multipliers,
tiers and funding interval remain current-only snapshots in v1, not historical
metadata copied into v2 or backdated facts.

Existing src/carry.py performs a backward as-of at supplied bar timestamps and
multiplies rates by a caller's constant annualization interval. It preserves
second offsets; a rate at 08:00:01 cannot be read at 08:00:00. However,
src/backtest.py prorates costs as elapsed/interval times the rate known at the next
hourly step. It does not debit each settled event at its exact timestamp. Example:
a position held 01:00..02:00, with no event in that window, can still incur one
eighth of the latest 8h fee. A position around an 08:00:01 event can instead have
its fee spread over adjacent hourly steps. Data normalization cannot fix this.

Consequently v2 can pass DATA_CONSISTENCY without becoming approved economic
labels. No new baseline may be used to claim actual settlement accounting. The
existing prorated hypothetical policy would need an explicit reviewable assumption
decision, or a separately reviewed event-accounting adapter with position
eligibility, mark/notional price availability, fees at simultaneous exit/entry,
partial closes, no double counting, and immutable cash-flow tests. This phase
does not implement that adapter. At most two unchanged baselines are permissible
only if the coordinator/counterpart review establishes compatibility without a
hidden assumption change. Otherwise G3 remains blocked and no replay is run.

## Dataset handoff contract (research only, schema 2)

QD produces a NEW root; fail if it exists. No mutation of v1 or QR files.
The manifest uses the exact root/file fields in data-acceptance.json. Base paths
are relative to the separately supplied base root; output paths are relative to
the candidate root. Reject absolute paths, traversal, symlink escapes and duplicate
file identities. The validator resolves the base explicitly, not from untrusted
manifest filesystem paths. No raw files are duplicated into v2.

Eight normalized files: two copied 1h, two copied funding, four derived candles.
Copied fields/columns/bytes match v1. Derived CSV columns are timestamp,open,high,
low,close,volume,available_at. Numeric serialization uses fixed-point Decimal
(no scientific notation), strips insignificant decimal zeros and has LF endings;
timestamps and volume are integer strings. The CSV header and row order are fixed.

For each derived file, provide a JSONL lineage file in lineage/. Its descriptor
binds parent_path and parent_sha256 to the copied hourly file. One JSON object per
derived row, keys normalized_row (one based), timestamp, parent_rows (ordered,
one-based hourly data-row indices, header excluded). No missing/repeated/reordered
parent. Parent source_id/source_row then resolves to all base raw origins and its
duplicate ledger. Do not invent a raw source_id for an aggregated bar.

Manifest identity: schema_version=2, protocol_id=canonical_hourly_v2-r1,
dataset_id, created_at (timezone-aware), spec_sha256, base_manifest_sha256,
symbols, data_range, files, withheld_buckets, network_attempts=0,
model_fits=0, limitations. Each file: symbol, kind, interval_seconds, path,
sha256, rows, columns, units, availability_basis, derivation. Copy derivation is
{method:copy_frozen_bytes,parent_path,parent_sha256}. Aggregate derivation is
{method:utc_ohlcv_from_frozen_hourly,parent_path,parent_sha256,lineage_path,
lineage_sha256,lineage_rows}. Funding interval_seconds=0, kind=funding; all
prices kind=candles. Units and availability strings match r1 exactly.
Each withheld bucket: symbol, interval_seconds, timestamp, end_exclusive,
available_parent_rows, unavailable_hours, reason=cutoff_before_bucket_close.
No output descriptor for native coarse candles or metadata. Native diagnostics
are linked by frozen spec evidence hashes, not fed into the usable frame list.

Creation timestamp may differ between reproducibility runs; normalized and lineage
bytes must be identical. Record builder source/commit hash in the QD report or as
additive manifest provenance. Unmentioned fields cannot override these semantics.

## Acceptance and training gate

QD tests producer failures; QR independently parses/recomputes from original
hourly parents, without importing the QD aggregation implementation. Check base
and candidate hashes; v1 raw lineage and all 2,068 preserved disagreements;
8-file inventory; complete grids; exact values and units; availability; every
lineage reference; final boundaries; 1h -> 4h -> daily identity; funding identity;
future perturbation; output determinism; and full native warmup as a conditional
diagnostic. Negative tests must reject rehashed corruption as well as bad hashes.

G1 provenance and G2 v2 consistency can PASS_WITH_LIMITATIONS while G3 economic
label compatibility is BLOCKED. Report these separately. G4 still needs a
prospective unseen holdout, chronological label maturity/24h embargo and accepted
economic effect/precision. No number of candles establishes independent trade
samples or forecast skill. G5 is a fresh direct human confirmation immediately
before ANY scaler/model fit. No fit, threshold search, activation or live order
is authorized. If all prerequisites eventually pass, notify the user and present
the exact bounded training plan for confirmation; never start automatically.

Official source formats and source-review evidence remain linked from
research/qr004/data-protocol.md and its immutable results. No new source lookup
or network budget is used in this phase.

## Freeze decision

QD accepted the data-only contract in commit a7cdd17d748e9d576ef335c587a90ed3ab5f5c17
against draft b545c8a9609c53c6ed3bb0735253a43a600eee05. No aggregation,
funding or source semantics changed during freeze. G3 remains BLOCKED and this
phase is limited to zero baseline replays. The event descriptor interval 0 is
not a native annualization/cost parameter. Future replay policy/adapter needs a
separate reviewable decision. This freeze records approval to build data only.
