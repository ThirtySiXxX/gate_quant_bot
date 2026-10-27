# QR004 BTC/ETH historical data protocol r1

State: **READY_FOR_QD** (specification ready; data not yet accepted).
Dispatch: QF-DISPATCH-20261028-QR004-DATA-SPEC-1. Date: 2026-10-28.
Machine-readable acceptance rules: `data-acceptance.json` in this directory.
This is a research-local handoff, not a change to runtime contracts.

## Scope and ownership

The human authorized BTC/ETH historical expansion and readiness assessment, and
requires another confirmation before training. No model fitting, further assets,
paid sources, runtime changes, integration, deployment or live credentials.

QR explicitly accepts QD as sole editor/collector of
`research/qd004/history_intake.py`, `research/qd004/results/`,
`tests/test_qd_history_intake.py`,
`docs/agent-reports/qd/QF-QD-004-history.md`, and ignored
`research/.data/qd004/` (raw/normalized/quarantine). QR owns this protocol,
acceptance JSON, `validate_history.py`, `research/qr004/results/`,
`tests/qr_research/test_qr004_history.py` and its QR004 report. QR independently
reads QD evidence; it does not duplicate downloads or modify QD files. Publish the
exact spec SHA256 in the intake manifest. Amendments require a versioned handoff.

## Frozen calendar and inputs

Only Gate USDT-settled BTC_USDT/ETH_USDT perpetuals; native trade-price 1h, 4h and
1d candles, actual settled funding, and public contract/risk metadata. Timestamp
units are UTC Unix seconds. Price is USDT/base; candle volume is contracts, not
base-coin or quote turnover. Spot, mark/index candles and predicted funding must
never be silently substituted.

| Purpose | UTC interval (end exclusive) |
|---|---|
| Raw history | 2023-01-01 00:00 to 2026-10-27 09:00 |
| Warmup | 2023-01-01 to 2024-01-01 |
| Unchanged baseline / potential seed labels | 2024-01-01 to 2025-01-01 |
| Proposed chronological development validation | 2025-01-01 to 2025-07-01; 2025-07-01 to 2026-01-01 |
| Retrospective audit | 2026-01-01 to 2026-10-27 09:00 |

The year of warmup is chosen from the existing EMA256 + 1500-observation raw
scaler, 500-observation FDM, 1000-observation Carry scaler and 205-day regime
requirements, not from returns. Native minimum periods producing finite output
are not full windows. Verify actual native pipelines and input continuity. EMA
initialization remains approximate even after warmup. ML features require 169
contiguous closed hourly bars. No date shrink or silent reduced warmup is allowed.

All these data are development/retrospective evidence. QR001/QR003 already viewed
recent periods. There is currently **no reserved untouched final holdout**. At a
future training decision, freeze a genuinely future observation window and the
evaluation/stopping rules before fitting; collecting beyond this cutoff is not
part of this task. Labels must end plus 24h strictly before each next stage.

## Official sources and bounded acquisition

Gate documents monthly historical downloads, including native candle intervals
and executed funding (`funding_applies`). Archive existence, coverage and schema
must still be verified for each requested file. Candidate template:
`https://download.gatedata.org/futures_usdt/{type}/{YYYYMM}/{symbol}-{YYYYMM}.csv.gz`.
See [official archive guide](https://www.gate.com/developer/historical_quotes).

The [official format announcement](https://www.gate.com/announcements/article/21688)
describes futures candle columns `timestamp,size,close,high,low,open` and settled
funding `timestamp,funding_rate`. `funding_updates` represents next-period
predictions and is excluded. Inspect the actual header rather than assuming it.

The [public futures API](https://www.gate.com/docs/developers/apiv4/en/futures/)
provides recent candles, funding and current metadata. Its candle request limit
is 2000 observations. Earlier live probes encountered old-hourly/funding retention
limits: API documentation alone does not establish multi-year availability.

Use archives through September 2026 and API for the October tail. Native API
multi-year 4h/daily history may be used when verified available. Choose the source
route before inspecting returns; record it per file. At route/month joins, compare
bounded overlapping native records. Identical parsed values may be deduplicated
with every original reference retained. Conflicting values all go to quarantine
pending documented resolution; neither “last write wins” nor averaging is valid.

Budget is **450 total network attempts**, including prior probes, retries,
redirects, failures and final overlap checks, max concurrency 2 and max 2 retries
per request. Limits: 10 MiB compressed per file, 250 MiB total compressed, 100 MiB
expanded per file. Stop/report resource or source restrictions; no bypass. A 206
response is not proof of completeness: verify requested range, Content-Range,
actual bytes, gzip EOF/CRC and expected parsed period. Retain failed attempts.

## Immutable handoff and acceptance

QD supplies a dataset root plus manifest conforming to `manifest_contract` in the
JSON. Paths are relative to that root, with separate immutable raw, normalized and
quarantine partitions; reject traversal and symlink escapes. Keep downloaded
payload bytes, URL/parameters, retrieval time, HTTP outcome, lengths and hashes.
Record failed retrievals in the attempt ledger even when there is no payload.

Concrete serialization agreed in the coordinator handoff: `data_range` has `start`
and `end_exclusive`; candle `units` is `{timestamp: UTC_unix_seconds,
price: USDT_per_base, volume: contracts}`, funding `units` is
`{timestamp: UTC_unix_seconds, funding_rate: fraction_per_settlement}`.
`availability_basis` equals the corresponding `normalization` value in the JSON.
Raw `response_headers` retain Content-Range for 206. A deliberately partial probe
is `complete_object: false` and cannot be a normalized row's source.

Canonical CSV columns and availability rules are in the JSON. Row provenance is
`source_id` plus one-based parsed data-row `source_row` (header excluded); duplicate
lineage retains all sources separately. Include source format/header interpretation
in `quality_summary`. Funding timestamps stay exactly as returned, including
seconds offsets; do not round, shift, interpolate or fill missing values with zero.
Bar availability = open + interval and funding availability = source timestamp
are idealized proxies, not observed network arrival times.

Acceptance checks cover hashes, gzip integrity, row provenance, finite numeric
values, positive prices, nonnegative volume, valid OHLC bounds, uniqueness,
chronological order, expected candle grids and closed-bar cutoff. Report every
missing interval, mismatch and source conflict. Compare hourly aggregation with
independent 4h/daily OHLCV only for QC, never replacement. Suspected outliers must
be source-verified; never clip authentic crashes to improve results.

For funding, show actual inter-settlement durations and evidence for historical
schedule segments. A changed funding interval is not automatically a missing row,
and observed gaps alone do not prove a new schedule. Unresolved changes or missing
settlements block the unchanged native constant-interval replay. Current
`funding_interval`, multipliers and tiers are snapshots at retrieval, not a
historical schedule. Store actual `observed_at`; `historical_effective_at` is null
without documentary evidence. Do not backdate current metadata. The existing
frozen-metadata policy is only a hypothetical simulation; historical multiplier
or schedule uncertainty must be disclosed and may block required semantics.

After data passes, the maximum label exercise is one uninterrupted unchanged
QR003 baseline per coin from 2024 to cutoff (two total), no skip/parameter/model
variants, no fold resets. Preserve bankruptcy and terminal censoring. Reuse QR003
actual exit-ledger reconciliation and label maturity. Record whether each asset
has nonconstant targets/features in separated market periods; report time/asset
dependence and uncertainty. Candle counts and repeated paths are not independent
trade labels. If prerequisites fail, do not run incomplete “clean” backtests.

## Training decision and additional-data recommendation

Readiness means G1 raw provenance, G2 normalized semantics/coverage and G3 usable
baseline events pass, with the G4 experimental proposal ready for review. It does
not prove a trading edge. At that point ask the human to accept the prospective
holdout, minimum useful economic effect, uncertainty/precision target and G5
permission. No automatic training. The proposal permits only one fixed ridge
model, six named causal features, train-only scaling and training-mean/ML-off
comparators; details are in the JSON. No hyperparameter or threshold search.

The five market features reuse existing feature-version-1 definitions on the
last exactly closed hour: `return_4h`/`return_24h` are log close ratios;
`volatility_24h` is the sample standard deviation of 24 hourly log returns;
`efficiency_24h` is absolute 24-hour close change divided by the sum of absolute
hourly changes; `volume_relative_24h` is log((current contracts + 1)/(24-hour mean
contracts + 1)). `proposed_side_sign` is +1 long/-1 short from the pre-ML proposal.
All are dimensionless. Preserve the existing 169-contiguous-bar feature guard.

This proposed regression is research-only: the existing runtime bundle expects
21 features and three-class logistic/boosting models and cannot consume this
six-feature ridge output. Future artifact/prediction integration needs a separate
reviewed contract; none is changed here. Natural exit labels measure outcomes
under continuation of the existing policy, not causal advantage over skipping;
later policy comparisons need complete account trajectories and cost sensitivity.

| Additional history | Recommendation / contamination risk |
|---|---|
| Actual settled funding and historical interval meaning | Essential within current scope; mixing predicted rates is unacceptable. |
| Historical contract multipliers/tier changes | High value for correctness; current snapshots alone cannot prove past execution constraints. Record availability gaps. |
| Gate mark/index history | Useful future basis/liquidation research; separately keyed. Never replace trade prices. New acquisition requires authorization. |
| Order-book/spread/liquidity history | Only for a specific execution hypothesis; expensive/incomplete coverage, cannot reconstruct from OHLC. Not acquired now. |
| Additional coins | Defer until BTC/ETH pipeline passes; use point-in-time listings and delistings to address survivorship. No new symbols now. |
| Other venues or spot | Separate cross-venue features only after a hypothesis; never splice into Gate perpetual history. Timestamp, volume and instrument mismatch risks. |
| News, on-chain, macro | Lower current priority; publication delays, revisions and vintage availability create leakage risks. No acquisition now. |

More same-market history is the first choice. More data families are not inherently
dirty; undocumented origins, mixed meanings, silent repairs and future availability
are what make them unreliable. Historical profitability never proves future returns.

## Independent validator

Run `python -m research.qr004.validate_history --root DATASET_ROOT --manifest
MANIFEST_PATH --output NEW_REPORT_PATH` from the QR worktree, using the existing
read-only interpreter and no network. Output must be new; source files are never
modified. The validator verifies native raw row values using Decimal, normalized
row provenance, OHLCV, closed-time boundaries, full candle grids, raw conflicts,
gzip/206 integrity, hashes and cross-interval consistency. It always reports
`training_status: NOT_READY`: historical schedule, duplicate lineage, attempt
ledger, metadata, native warmup, label/evaluation gates and permission require
separate reviewed evidence. A structural PASS alone never certifies training.

The inverse lineage check also detects raw records silently omitted during
normalization, including funding. The reviewed QD quarantine adapter is checked
against raw values/references and actual normalized destinations; identical
duplicates are legitimate only with complete lineage. Other quarantined records
remain unresolved input limitations, not a way to waive missing-data acceptance.

Funding seconds offsets remain exact. Cross-interval comparisons require exact
Decimal OHLCV equality; discrepancies are retained for source review, never
automatically tolerated or repaired. Absolute close moves over 30% per candle and
funding over 1% per settlement are flags for source review, not deletion rules or
proof of bad data. This diagnostic threshold is fixed before reading the dataset.
