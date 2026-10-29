# QR018 — Hyperliquid book data for Gate BTC/ETH research

2026-10-29. QR, branch `codex/qr-validation-baseline`, base
`6e3e4890441b83dc375fb9f27ce8744f3b366ba9`.
Exclusive new files: this report and `research/qr018/source-probe.json`.
No shared contract, QD file, runtime, prior research artifact or journal changed.

## Decision and scope

The user confirms Gate execution and Hyperliquid book signals, BTC/ETH only,
no second-level trading and a maximum 15-minute decision timeframe. Use 15-minute
decisions as the first research design, retaining finer observations to construct
features. This is a new candidate experiment, not a silent change to QR013/014's
frozen hourly 12-feature baseline. Decision frequency and holding period are
different; the user has not supplied a new holding-period/exit rule.

Historical Hyperliquid L2 exists. A potentially useful long history is advertised,
but no acquired continuous dataset is qualified for training in this task.
Status: SOURCE_CANDIDATE_FOUND / TRAINING_NOT_READY. No fitting was performed.
Keep the user's fresh-confirmation requirement before training.

Books differ across exchanges in depth, participant composition, cancellations,
spread and imbalance as well as price. Hyperliquid features may predict Gate
returns, but that remains a hypothesis. Gate labels, funding, fees and execution
assumptions remain authoritative; Hyperliquid depth cannot represent Gate fills.

## Sources inspected

1. [Hyperliquid official archive](https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data):
   L2 snapshots in `hyperliquid-archive/market_data/date/hour/l2Book/coin.lz4`.
   Approximately monthly uploads, explicitly no completeness/timeliness guarantee;
   requester pays transfer costs. One anonymous HEAD for BTC 2025-09-01 hour 0
   returned HTTP 403. This demonstrates access failure, not object absence or
   a date boundary. No AWS profile, credential, listing or paid transfer used.
   Exact BTC/ETH date coverage, object sizes and total cost remain unknown.
2. [Tardis Hyperliquid](https://docs.tardis.dev/historical-data-details/hyperliquid):
   public exchange metadata confirms BTC/ETH perpetual availability from
   2024-10-29. Free CSVs cover the first day of each month, not continuous months.
   Full historical access is a commercial route; no subscription was purchased.
   Raw recordings include collector-local timestamps, which still differ from
   our own historical receipt times. Public metadata currently distinguishes
   regular 20-level `l2Book` (~5.4s inferred cadence) from five-level `fastBook`
   (~500ms), introduced 2026-06-17 and then used for normalized book changes.
   Do not silently join these as identical depth/resolution. Prefer a consistent
   raw channel or an explicitly normalized common-depth feature definition.
3. [orderflow-depth](https://github.com/odgersjewellr-maker/orderflow-depth):
   directory at inspected commit `7d0b160cd4fb74746d1de670d698b0d97127be52`
   has 104 dated files per coin, 2026-07-18 to 2026-10-29 (last day partial);
   only 75 dates per coin precede the current 2026-10-01 economic cutoff.
   These are filename bounds, not verified continuous coverage. GitHub metadata
   reports no detected license. Collector defaults to 15s sampling for 53 minutes
   per invocation, stores book time with a request-start fallback, not receipt
   time, converts decimal strings to JS numbers, and deduplicates trades only
   within each run. It cannot supply the existing 2024/2025 research windows.
4. [Official historical_data repository](https://github.com/hyperliquid-dex/historical_data):
   README describes selected trades, liquidations and ledger updates, not a
   complete historical order-book archive. Do not mistake it for L2 coverage.

## New bounded source probe, not repeated baseline validation

Fetched exactly two pinned public gzip objects from source 3, BTC/ETH 2026-09-01;
803,559 compressed bytes total. Git blob hashes matched the directory metadata.
No SOL data acquired. Each object contains 1,272 distinct timestamped snapshots,
occupying only 28 of 96 possible fifteen-minute bins. Each has five gaps longer
than 15 minutes; maximum gaps are 19,819.208 seconds (BTC) and 19,819.258 (ETH).
This is unsuitable as a complete day; occupied bins themselves are not certified
complete. No claim about every other day is inferred from this sample.

Receipt, object URLs/hashes and counts are in `research/qr018/source-probe.json`.
Raw gzip files and captured Tardis metadata remain under ignored
`research/.data/qr018/`. The initial system Python HTTPS request failed certificate
verification; acquisition used curl with normal certificate verification, without
disabling TLS checks or installing packages.

702 calendar days from 2024-10-29 through 2026-09-30 would produce at most
67,392 fifteen-minute rows per coin, 134,784 combined, before gaps/warmup/labels.
This is a planning upper bound, not measured accepted sample size. BTC/ETH rows
are correlated; overlapping labels further reduce effective information. A
small tabular-model study is plausible at this scale; adequacy or profitability
is not established by the row count. This source cannot fill all of 2024 under
the existing frozen split; any new temporal split must be declared separately,
and previously exposed periods must remain marked as exposed.

## Open-source framework review

- [HftBacktest](https://github.com/nkaz001/hftbacktest): L2/L3 reconstruction,
  latency/queue models and multiple exchanges. Useful for future execution
  research; requires suitable underlying data and cannot fill historical gaps.
- [NautilusTrader](https://github.com/nautechsystems/nautilus_trader): multi-venue
  event-driven backtests supporting bars, trades, quotes and books. A credible
  separate research engine, but adopting it now would duplicate current work.
- [Crypto Lake client](https://github.com/crypto-lake/lake-api): open client with
  anonymous sample access; full data is a separate paid service. Open-source
  access code is not evidence of free continuous BTC/ETH Hyperliquid history.

Recommendation: retain the existing account/backtest infrastructure. No framework
installed, vendored or executed; no claim of compatibility validation is made.

## Minimal new experiment and counterpart dependency

After obtaining continuous source data, propose a separate versioned Gate/HL
15-minute research dataset. Start with relative spread, fixed-depth imbalance
and microprice displacement; aggregate observations within closed windows.
Use time weighting and explicit staleness/coverage, not event-count weighting
that changes when feed cadence changes. Missing depth is unknown, not zero.
Snapshot differences do not identify every cancellation or true event-level OFI.

Required input binding: source venue/instrument/product/quote and size units;
schema/channel/depth versions; event time; collector receipt time when observed;
availability method and any simulated latency; immutable source hash; missingness.
Use UTC half-open windows, with every input available by decision time. Gate and
Hyperliquid quote units must not be assumed identical. Normalize within market;
any cross-market price basis needs explicit quote conversion and aligned times.

QR owns feature/label experiment design; QD owns acquisition/storage integration
and Gate 15-minute replay support. Existing hourly feature/order contracts remain
unchanged. Before integration QD/QR must review the new source and decision-grid
boundary, including future-record exclusion, gap/stale rejection, instrument/unit
mismatch and channel-depth-change cases. These are affected new checks only.
Compare Gate baseline against Gate baseline plus HL features on the same eligible
times, with chronological isolation and Gate costs. Avoid search over many
features/horizons. No new arbitrary sample quota or profitability-before-fit gate.

Next concrete dependency is access to a continuous archive and its actual size/
price: obtain a bounded BTC/ETH object inventory/quote before paid acquisition.
Do not read stored credentials or incur charges under this task. Free sources
inspected do not satisfy the current training windows; integration conditional
on sufficient qualified data has therefore not been triggered. Preserve ongoing
QD ledger work; no duplicate dispatch, replay, training or older tests were run.

## Verification and review status

Only new-source metadata inspection, two-object decompression/hash/count/gap
diagnostics, calendar arithmetic and document diff checks. No runtime code changed,
so no old unit/integration suite rerun. Report and receipt are reviewable locally;
no merge, push, shared journal edit, live trading or deployment.
