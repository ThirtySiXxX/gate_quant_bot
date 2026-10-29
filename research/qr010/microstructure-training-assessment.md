# QR010: historical microstructure evidence and training assessment

2026-10-28 · BTC/ETH only · `QF-QR-010-HISTORICAL-MICRO` · QR research finding.

**Historical Gate microstructure data was actually obtained and parsed. Qualified
fragments support feature and trading-rule research. They do not yet support a
point-in-time training dataset or a claim of out-of-sample improvement.** No model,
scaler or calibrator was fitted; no strategy replay or account application ran.
Training still needs a separate human confirmation after readiness is reported.

The reproducible inventory is [historical-micro-data.json](historical-micro-data.json).
Raw bytes, HTTP receipts and derived examples remain in the ignored local
`research/.data/qr010/historical-micro/`; the manifest identifies every file by
size and SHA256. `derived/v3` is canonical. Earlier failed/intermediate analyses
are retained, not overwritten or counted as additional independent samples.

## Actual acquisition and sample limits

Before requesting data, the probe fixed three calendar anchors: 2023-01-01,
2024-07-01 and 2026-09-01, each 00:00–01:00 UTC, for BTC_USDT and ETH_USDT.
Selection used early/middle/recent dates, not returns. Target history remains
`[2023-01-01, 2026-10-01)` UTC; six sampled instrument-hours do not prove that
target's coverage, nor represent all times of day or market regimes.

| Object category | Actual outcome |
|---|---|
| Gate hourly depth deltas | Six complete HTTP 206 objects; complete gzip with CRC validation |
| Gate hourly depth snapshots | Six complete HTTP 206 objects; complete gzip; ten levels per side |
| Gate monthly trades | Six 2 MiB HTTP 206 prefixes; each gzip is truncated, none is a complete month |
| Hyperliquid L2 objects | Six anonymous requests returned HTTP 403; no L2 bytes obtained |
| Hyperliquid trade archive listings | Two anonymous requests returned HTTP 403; no trade data obtained |
| Gate public contract metadata | Two complete HTTP 200 responses; current metadata only |

The 40 data requests include 12 HEAD requests and every failure, with no retries
or redirects. Application body plus serialized header bytes total 80,684,514;
recorded acquisition/parse time is 102.353 seconds and peak recorded RSS is
179,896,320 bytes. Raw and derived evidence occupy approximately 103 MB. These
are bounded engineering measurements, not scientific sufficiency thresholds;
HTTP accounting excludes TLS/transport framing. Eight request slots remain
unused. Documentation browsing is recorded separately in the manifest.

Gate documents the archive entry points and UTC naming. Its generic start-date
claims are not evidence that a particular BTC/ETH file exists. The observed
files confirm six-column depth records and four-column trades; the historical
format includes initial `set` levels and aggregated `make`/`take` changes.
[Gate download documentation](https://www.gate.com/zh/developer/historical_quotes),
[Gate archive format](https://www.gate.com/announcements/article/21688).

Hyperliquid documents requester-paid transfer and potentially incomplete,
periodically uploaded archives. The 403 responses do not distinguish missing
objects from inaccessible objects. No billing, AWS credentials or requester-pays
access was enabled. A legitimately supplied immutable extract is another route;
no purchase is necessary for the Gate research already completed.
[Hyperliquid historical data](https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data).

## Units, clocks and reconstruction: measured results

All prices remain USDT per base unit and quantities remain exact decimal
**contracts**, including fractional contracts. Signed depth size identifies the
side; `make` adds and `take` removes absolute quantity. A decrease does not prove
whether a particular order was canceled or executed. Signed trade size supplies
a reported buy/sell direction proxy. One unique trade ID is counted once; these
files cannot identify every internal/ADL event or prove an aggressor classifier
against a second independent feed. We do not add buyer and seller copies.

The observed archive timestamps are fractional Unix **seconds**. Snapshot
`current` describes response generation and `update` the last book change; neither
is our historical receipt time. This field interpretation matches the official
[FuturesOrderBook schema](https://github.com/gateio/gateapi-python/blob/master/docs/FuturesOrderBook.md).
Current WebSocket millisecond fields and U/u update rules must not be substituted
for this archive schema. Historical publication time, receiver latency and
revision history are absent. Today's HTTP date/ETag/Last-Modified and retrieval
timestamp are retained as provenance, never backdated into `available_at`.

The decoder starts with the full hourly depth state and consumes consecutive
source ID spans. A row beginning at ID b with merged count n ends at b+n−1.
An interior snapshot ID has no exactly reconstructible state in this aggregate
record. We compare only exact boundaries against all ten recorded levels on
both sides, using decimal quantities; no nearest-ID join, rounding or forward
repair makes an inconsistent state pass.

| UTC anchor / asset | Depth rows | Snapshot records | Exact matches / tested boundaries | Other result |
|---|---:|---:|---:|---|
| 2023-01-01 BTC | 945,022 | 3,339 | 3,091 / 3,091 | 248 interior IDs; one exact repeated delta |
| 2023-01-01 ETH | 1,129,126 | 3,339 | 3,280 / 3,280 | 59 interior IDs |
| 2024-07-01 BTC | 1,505,853 | 3,322 | 3,291 / 3,292 | 30 interior IDs; one quantity mismatch |
| 2024-07-01 ETH | 943,531 | 3,322 | 3,292 / 3,292 | 30 interior IDs |
| 2026-09-01 BTC | 2,705,755 | 3,384 | 0 / 3,275 | 109 interior IDs; price/depth mismatch persists |
| 2026-09-01 ETH | 2,613,213 | 3,384 | 0 / 1 | Reconstruction fails at row 38,349; 3,383 snapshots remain unbridged |

The total is 9,842,500 depth rows and 20,090 snapshots. Snapshot parsing found no
negative price/size, crossed snapshot or nonmonotonic ID/current sequence in
these samples; raw signed negative ask/trade sizes are valid directions. No
crossed/empty book was observed at the checked timestamp-group ends before a
reconstruction failure. This is not a proof about every intra-group state.
The 2023 snapshots have four gaps exceeding two seconds for each asset; no OFI
is computed across those gaps. The delta files contain 232 rows exactly at the
next-hour boundary: a future half-open join must exclude them from the previous
hour and deduplicate against the next file. Other out-of-hour rows were absent.

Specific failures are retained, with no epsilon clipping or silent repair:

- **2023 BTC:** raw row 470,612 repeats row 467,815 verbatim, ID 25644226342.
  A bounded identity cache now treats only a proved identical row as a no-op.
  Conflicting repeats fail. The raw reversal is explained by this duplicate;
  the normalized stream is ordered. The original strict failure remains in v1.
- **2024 BTC:** snapshot line 481 / ID 62687597133 differs at ask 62699.3:
  archived quantity 21797 versus reconstructed 24986. That snapshot emits no
  feature and resets adjacent-snapshot OFI. Later independently matched states
  may yield retrospective features; this is not continuous exact L2 replay proof.
- **2026 BTC:** 0 of 3275 boundary comparisons match, including price ladders.
  No qualified book feature is emitted. Sequence continuity alone does not make
  the initial-state/schema/archive pairing correct; the root cause is unresolved.
- **2026 ETH:** 2,025,628 fractional depth rows and 1099 zero-quantity snapshot
  levels occur. At row 38,349, removal of 21.3 from 21.2999999999999 creates a
  negative reconstructed level. There are also much larger earlier level
  discrepancies, so float-like precision alone does not explain the failure.
  No qualified book feature is emitted. Snapshot zeros are not filled liquidity.

The current public metadata responses say multiplier 0.0001 for BTC and 0.01 for
ETH, with ETH decimal size enabled. These observations concern retrieval time;
they do not establish historical multiplier/minimum size/price tick schedules.
No historical conversion to base or USDT depth is made from them. The separately
approved synthetic account/order assumptions remain explicitly simulated.

All six trade prefixes extend beyond their selected first hour; they contain
1,299,844 complete physical trade rows, with no observed ID gaps, backwards IDs,
conflicting duplicates, time reversals or invalid price/zero size. They do not
prove full monthly coverage, CRC integrity of the complete monthly object, or
absence of revisions. ETH September 2026 has 138,119 fractional-quantity rows.
Trailing incomplete lines are discarded as incomplete evidence, not parsed.

| Prefix | Observed first event UTC | Observed last event UTC |
|---|---|---|
| BTC Jan 2023 | Jan 1 00:00:09.280137 | Jan 4 15:05:01.068918 |
| ETH Jan 2023 | Jan 1 00:00:00.647701 | Jan 3 14:23:24.148956 |
| BTC Jul 2024 | Jul 1 00:00:00.736115 | Jul 1 19:02:42.812720 |
| ETH Jul 2024 | Jul 1 00:00:00.758587 | Jul 2 13:56:51.710550 |
| BTC Sep 2026 | Sep 1 00:00:01.740144 | Sep 1 10:32:53.917911 |
| ETH Sep 2026 | Sep 1 00:00:00.389037 | Sep 1 09:21:21.258743 |

These are observed extrema, not a promise that every possible market event was
captured. Comparisons use only each matching selected hour, not arbitrary overlaps
between the longer prefixes and other book files.

## Traceable examples already produced

`derived/v3` contains **12,954** matched snapshot feature rows and **360** trade
minute examples. Every row points to raw hashes and source lines/IDs. These
artifacts have null historical availability and an explicit retrospective quality
label; they are not deployable signals or a newly approved shared feature schema.

- Snapshot fields: spread in bps, bid/ask top-five depth in contracts,
  dimensionless depth imbalance, and adjacent matched snapshot OFI in contracts.
  OFI is a sampled level-change proxy, not a complete message/order flow.
- Trade fields: observed signed-side contract totals and a price-weighted
  pressure ratio `(sum_buy(p*q)-sum_sell(p*q))/sum_all(p*abs(q))`.
  A common within-contract multiplier cancels in that ratio; no cross-contract
  notional aggregation or claim of a proved historical multiplier is made.
- R12 snapshot 62687349489: spread 0.01593083468811806660204058062 bps,
  top-five bid/ask depth 15679/420 contracts, imbalance
  0.9478228461395117709174482887. The first OFI is null.
- R15 first minute: 203 prints, buy 17267 / sell 31044 contracts; price-weighted
  pressure −0.2852232904408647648837272154. It is a structural example, not a
  successful trade prediction. Ratios use Decimal's 28-digit calculation context;
  original numeric lexemes and quantities remain retained in raw evidence.

Retrospective quality selection uses later file checks. Training must not import
that hindsight acceptance mask as if it had been known at the decision. A causal
decoder will invalidate/recover from evidence available at that time, with its
own tests; this probe is an offline diagnostic, not that production decoder.

## Scientific inclusion decisions

| Data / intended use | Decision | Reason and remaining evidence |
|---|---|---|
| Matched Gate L2 fragments: spread/depth/flow and rule prototyping | INCLUDE | Real prices/quantities and snapshot bridges exist; preserve retrospective status |
| Gate L2 as an approved historical ML feature set | DEFER_PENDING_EVIDENCE | Need regime coverage, metadata/clock policy, consistent recovery and costed OOS evidence |
| Current September 2026 delta+snapshot pairing for exact L2 replay | NOT_SUITABLE in present form | Both assets fail independent state checks; supplier/schema reconciliation needed |
| Gate trade prefixes for direction/pressure prototypes | INCLUDE | Exact IDs and decimals are readable; selected-hour aggregates are traceable |
| Trade prefixes as complete training months | NOT_SUITABLE | Deliberately truncated gzip; full object integrity and monthly coverage unproved |
| Full Gate trades for ML/entry/exit candidates | DEFER_PENDING_EVIDENCE | Resolve full coverage, timing and label/cost validity; economic value is untested |
| Hyperliquid cross-market features | DEFER_PENDING_EVIDENCE | No archive sample obtained; access/format/clock/contract comparability remain open |
| L2 used as individual order cancellations, queue rank or exact fills | NOT_SUITABLE | Aggregate levels and merged changes lack order identities and queue events |
| Current metadata used as historical exchange rules | NOT_SUITABLE | Retrieval-time fields do not establish an earlier effective schedule |

These decisions follow measurement and the economic question. Storage size and
convenience do not decide whether microstructure contains alpha. User direction
to include microstructure in future trading-rule research is retained; admission
to ML remains a testable hypothesis rather than an assumption that more inputs
help. Gate is the primary execution-market source. HL, if obtained, is a separate
venue with different collateral, units, basis, funding and transport delays;
BTC/ETH ticker matching alone cannot make records interchangeable.

## Frozen small candidate family; execution waits for data and approval

This is a finite research specification, not permission to run experiments now.
All account comparisons use [the shared-account binding](shared-account-binding.md):
one initial 10000-USDT BTC/ETH account, one joint covariance allocation, the same
approved ×10 native risk budget, costs, reservations and finality. Do not compare
independent-account baseline returns against a shared-account treatment.

Three different questions need different targets:

1. **Short horizon mechanism:** does a trailing 60-second pressure/depth signal
   predict the next 30-second Gate mid-price change after qualified availability?
   Use signed markout in bps, with spread/fees/latency as a separate economic
   hurdle. A positive gross correlation is not a profitable execution policy.
2. **Hourly holding model:** do past closed-hour liquidity summaries and the last
   60 seconds improve the existing four-hour target beyond hourly-only inputs?
   Retain the current next-eligible-entry/label isolation conventions. Feed finite
   aggregates, not millions of raw ticks merely because they are available.
3. **Execution and exits:** does a causal filter improve net entry/exit prices,
   tail costs or account drawdown? Compare identical native intents and realistic
   delay/capacity assumptions. Quote markouts and book-depth crossing costs are
   proxies; they do not establish queue fills or historical real execution.

Freeze one research grid of 1 second, one lookback of 60 seconds, top-five depth,
and maximum accepted snapshot age/gap of 2 seconds. As-of join only records with
qualified `available_at <= decision_at`; no interpolation across invalid periods.
Proposed fields: spread, top-five imbalance, 60-second signed trade pressure,
60-second sampled OFI divided by mean top-five total depth, and total top-five
depth (contracts, asset-specific scaling fitted on training data only if approved).
Hourly features use time-weighted summaries over the preceding closed hour plus
the last 60-second vector. Full required window validity is mandatory; record
ineligibility/exposure loss rather than filling an unavailable interval with zero.

One predeclared entry-rule candidate requires spread <=5 bps (the primary
one-side slippage budget), with depth imbalance and trade pressure agreeing with
the native entry direction. One exit-overlay candidate requests a reduce-only
close when both signs oppose the held direction for two consecutive eligible
one-second decisions. Both use strict directional signs; zero offers no
confirmation. Native exits remain available. The constants are mechanism-based
research hypotheses, not fitted optima or approved production settings; no grid
search over thresholds or losing-streak filters is authorized.

| Future arm | Treatment | Primary comparison |
|---|---|---|
| A0 | Native hourly/timing strategy, unchanged | Baseline |
| A1 | A0 plus Gate entry filter | A1−A0 |
| A2 | A0 plus Gate exit overlay | A2−A0 |
| A3 | Same hourly-only ML family and frozen fit budget | ML control |
| A4 | A3 plus the fixed Gate aggregates | A4−A3 |
| A5, conditional on HL data | A3 plus fixed comparable HL aggregates | A5−A3 |
| A6, conditional on HL data | A4 plus those same HL aggregates | A6−A4 |

At most seven arms, each under primary costs and one joint stress of fee 0.0015
per side/slippage10bps: at most 14 future evaluation paths. This does not enlarge
the currently approved nine ledger scenarios/24-attempt ceiling, and none runs
in QR010. No model-family sweep: A3–A6 must use one fixed family, estimator budget,
seeds and selection rule, frozen when training is separately requested. The
30-second target is an auxiliary mechanism study, not another silently optimized
trading arm. No automatic activation follows a favorable study.

Freeze a calendar candidate split independent of outcomes: train 2024, validate
2025-H1, sealed test 2025-H2 through 2026-09; 2023 supplies causal warmup. Actual common
coverage must first support this split. If unavailable, publish a coverage-driven
revision before outcomes or fitting; never shift the holdout toward good returns.
Purge any training observation whose label overlaps the next partition and retain
the existing 24-hour embargo for this candidate, exceeding the longest 4-hour
label. Feature warmup uses only prior inputs; scaler, thresholds and calibration
never see holdout labels. Once validation fixes the model, evaluate the sealed
test once; repeated monthly diagnostics do not authorize test-driven retuning.

The primary economic metric is paired shared-account net return difference;
report drawdown, turnover, fees/funding, cash competition, eligible exposure and
joint losing episodes alongside it. A filter may simply remove trades: report
missed gains, removed losses, time in market and a separate exposure-normalized
diagnostic. Neither a shorter losing streak nor gross Sharpe alone proves value.
Keep the three Gate portfolio contrasts as one family; use a predeclared Holm
correction at 5% familywise level. If HL is added, freeze all five contrasts as
one family before opening holdout outcomes. Report all failed arms.

Estimate uncertainty with paired time-block/episode-aware resampling that keeps
both assets and overlapping labels together. Freeze block length from training
dependence diagnostics, then hold it fixed for validation/test. Power and minimum
detectable effect curves must use training variance/autocorrelation, with useful
effect sizes tied to costs and account objectives. Tick count is not independent
sample count. Prior 28-day/100-episode/30-block planning numbers are not universal
proofs of adequacy; wide intervals mean inconclusive, not accepted alpha.

## Storage estimate and precise next evidence

For 32856 calendar hours and 45 months, applying the three measured paired-asset
sizes gives the following **scenario extrapolation in decimal GB**, not a
statistical confidence interval or a download plan:

| Both assets combined | Low observed rate | Mean observed rate | High observed rate |
|---|---:|---:|---:|
| Compressed hourly delta books | 415.280 | 733.407 | 1223.699 |
| Compressed hourly snapshots | 10.298 | 12.174 | 14.029 |
| Compressed monthly trades, HEAD-advertised size | 5.787 | 11.997 | 22.074 |
| Expanded delta CSV, if retained | 2939.883 | 4891.213 | 8189.828 |

Trade full-object sizes are advertised headers, not fully downloaded measured
payloads. Midnight-only samples, secular activity growth, compression and missing
archives make extrapolation uncertain. Streaming avoids retaining expanded CSV;
raw immutable retention, indexes, derived features and backup copies still need
a separately bounded acquisition plan. Current 2026 monthly trade objects
advertise 195488136/295034158 bytes, above this task's 128MiB per-object limit;
this task does not silently download them in chunks to evade the cap.

The next work is specific and does not require another complete R05/doc review:

1. Resolve the Gate 2026 initial-state/delta/snapshot inconsistency and fractional
   quantity mapping with narrowly selected adjacent-hour/source-format evidence.
   Isolate 2024's mismatched snapshot. Keep the failed data excluded meanwhile.
2. Obtain complete trade objects and contiguous paired BTC/ETH book coverage
   across the frozen train/validation/test calendars under a newly sized bounded
   acquisition task, plus historical effective metadata. Verify hours and days
   across regimes, not just month-start snapshots; do not label this pilot full
   coverage. Full tick history is optional for hourly sufficient statistics, but
   raw source integrity and reproducible aggregation are still required.
3. Define an explicit historical availability/latency scenario where true receiver
   clocks cannot be recovered, and distinguish its simulated conclusions from
   deployment evidence. Future paired capture can calibrate delays, but cannot
   retroactively create historical receipt times. No collector starts here.
4. Finish QD's shared-account ledger/execution implementation and targeted tests;
   produce mature cost labels and verify causal feature-core parity. Training,
   paper inference and future live inference should share feature/signal/risk
   semantics, while fill feedback remains environment-specific. Full cross-margin
   liquidation/ADL is still not simulated.
5. Report the dataset, label, causal-alignment and uncertainty-readiness evidence
   to the user, then obtain fresh confirmation **before any fitting**. If HL is
   required, separately choose authorized requester-paid access or a legitimate
   immutable archive; current 403 results neither prove usefulness nor disprove it.

Current readiness: **NOT_READY_FOR_TRAINING**. The completed deliverable is real
bounded sample acquisition, parsed evidence and scientific candidate selection.
No historical or future profitability claim follows from it.
