# QR009: BTC/ETH public microstructure research preregistration

2026-10-28. Task `QF-QR-009-DYNAMIC-MICRO-DESIGN`; dispatch
`QF-DISPATCH-20261028-QR009-DYNAMIC-MICRO-DESIGN-1`, resumed under
`QF-RESUME-20261028-QR009-DYNAMIC-MICRO-1`.
**PROPOSAL / QD_REVIEW_REQUIRED / COLLECTION_NOT_STARTED / FIT_NOT_STARTED.**

## 1. Purpose and separation from the current gate

The human selected a future direction: public Gate and Hyperliquid BTC/ETH books
and trades, financially motivated order flow/pressure/liquidity features, then
tests of entry, exit and losing streaks before choosing weights. Cross margin
stays unchanged. The common causal core should serve replay and future execution
adapters. This document makes that direction reviewable; it authorizes no feed
process, live order, account/wallet subscription, credential use or fit.

This is **not an additional mandatory gate for current historical training
readiness**. Hourly candles cannot reconstruct earlier order books or tick flow;
new observations cannot fill old microstructure history. Keep the historical
8-scenario/18-trajectory register and its budgets unchanged. Future collection,
microstructure experiments and model/scaler/weight fitting need separate bounded
dispatches; actual training still requires fresh human confirmation.

## 2. Official source facts and selected feed scope

Sources checked 2026-10-28; they are mutable documentation, not frozen data.
QD must pin documentation/adapter versions and actual public instrument metadata
in any future run manifest. Examples in documentation are not current metadata.

**Hyperliquid:** select mainnet BTC and ETH perpetual `l2Book` and `trades`.
The documented slow book feed is a periodic snapshot, up to20 levels/side;
`fast=true` offers5. Use `fast=false` without price aggregation. Book pushes depend
on blocks and an elapsed0.5s condition, not a guaranteed sampling clock. Trades
arrive as arrays. A trade key combines block time, coin and tid; tid alone is not
globally unique. Level `n` counts orders, without individual order identities.
[Official subscriptions](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions).

HL `sz` is underlying-coin quantity; trade side B/A means aggressing buy/sell.
The buyer/seller address pair is not maker/taker labeling.
[Official notation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/notation).
BTC/ETH linear perpetuals are USDT-denominated but USDC-collateralized, without
applying a USDC/USDT conversion to that contract payoff. Preserve both labels;
do not identify their cash account with Gate's USDT account.
[Official contract specifications](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/contract-specifications).
The public socket is `wss://api.hyperliquid.xyz/ws`; reconnects are expected.
[Official connection documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket).

**Gate:** select `wss://fx-ws.gateio.ws/v4/ws/usdt`, BTC_USDT and ETH_USDT;
`futures.trades` plus `futures.order_book_update`, 100ms,20 levels. Request
`X-Gate-Size-Decimal: 1`; otherwise quantities can be truncated. Positive trade
size denotes taker buy, negative taker sell. `is_internal=true` denotes special
insurance/ADL trades, not ordinary depth matching. Use the U/u snapshot/update
protocol specified below; the distinct `futures.obu` channel is excluded.
[Official Gate futures WS documentation](https://www.gate.com/docs/developers/futures/ws/en/).

Gate book/trade size is contracts; `quanto_multiplier` converts contracts to base
units. Public contract metadata includes direct/inverse type and decimal-size
capability. Fetch BTC_USDT/ETH_USDT metadata and matching order-book snapshots
only under the future public collection plan. Do not reuse old multiplier values
as proof of present metadata.
[Official Gate futures API](https://www.gate.com/docs/developers/apiv4/en/futures/).

Everything below is a **proposed local research/engineering rule**, not an exchange
guarantee. Outstanding wire details (timestamp precision, heartbeat fields,
bootstrap duplicates and any schema drift) must be checked by QD fixtures before
qualification. HL book examples use epoch-millisecond-sized timestamps; retain
the raw integer and declared unit, then require adapter fixture confirmation.
Do not infer timestamp units by silently multiplying an unexpected magnitude.
[Official HL book example](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint).

## 3. Proposed capture and normalization boundary

Proposed namespace `qr009-micro-pilot`, schema1; this is not a silently added field
to an existing shared contract. QD owns the raw/normalized transport and tests;
QR reviews scientific units/availability and owns feature definitions. Contract
change request, owner/counterpart review and integration approval precede code.

Each raw envelope records run/boot/connection IDs, connection frame sequence,
venue, endpoint/channel, instrument, subscription and metadata hash; original
payload bytes encoded losslessly as base64, receipt UTC nanoseconds, receipt monotonic nanoseconds, decode-end
and validation-ready clocks, payload SHA256 and previous-envelope hash. Preserve
all physical duplicates, control/error packets and REST request/response clocks.
Never rewrite an old file to fix an interpretation. Persist closed chunks with
atomic manifest publication; incomplete crash tails are quarantined explicitly.

Normalized rows add immutable raw references, semantic event ID, source event
time/unit, source server time separately, decoded prices/quantities as decimal
strings, aggressor side, contracts/base/quote-notional units, metadata revision,
book snapshot/update IDs and `available_at`. Do not put addresses into feature
keys or infer participant identity. IDs are exact integer strings, never float
identifiers. Original public packet bytes stay in the
local raw archive; normalized research exports need no address columns.

Instrument identity distinguishes venue, BTC/ETH underlying, perpetual/direct
contract, quote denomination, settlement/collateral and exchange symbol. Gate
signed base amount is signed contracts × pinned multiplier; HL signed base amount
is signed sz. For within-venue pressure, absolute quote notional is abs(base)×price.
Keep quote denomination and settlement labels; no unobserved FX parity, cross-venue
cash summation, consolidated book, shared order queue or single global trade ID.

Availability is when a record is received, decoded and valid for the consumer,
including completed book reconstruction; never earlier than receipt. Keep source
time for economic windows but replay in recorded receipt/availability order.
Late trades cannot change already-published features or past decisions. Historical
reprocessing creates a separately identified restated view, not an as-known fix.
Bootstrap history is flagged; it does not acquire its old source time as a new
availability time or prove that a disconnected interval was fully recovered.

Proposed clock mapping to fixture-check: Gate trade `create_time_ms` and book `t`
are epoch milliseconds; retain `create_time` seconds and envelope time separately.
HL book/trade `time` is mapped as epoch milliseconds only after schema confirmation.
Parse decimal timestamp lexemes exactly, record original precision and reject
unrepresentable sub-nanosecond values; never round a clock to fit an event order.

Monotonic time controls deadlines; boot ID separates incomparable epochs. Record
paired UTC/monotonic samples each10s and read-only local clock-sync uncertainty.
No system-clock adjustment. Proposed combined-venue use requires clock uncertainty
<=50ms; a wall/monotonic discrepancy >100ms starts a new invalid clock segment.
Unknown synchronization masks cross-venue comparisons; it is not guessed from
apparent exchange lead/lag. Preserve raw timestamps across a clock step.

## 4. Deduplication, order, gaps and quality

Trade dedup keys: Gate=(venue,contract,trade ID), HL=(venue,coin,source block time,
tid). Identical semantic duplicates retain multiple raw provenance references;
conflicting payload for one identity invalidates the stream segment. Do not assume
trade IDs are consecutive or use equal timestamps as uniqueness. Explicit internal
Gate trades are retained but excluded from the primary matched-flow features,
with separate count/notional. Unknown flag/type semantics are quarantined.

For Gate, buffer arrivals during same-depth REST `with_id=true` bootstrap. From
base b discard u<=b, bridge U<=b+1<=u; subsequently require coverage of last+1.
U>last+1 gaps. Sizes replace, zero deletes, empty updates advance the cursor;
`full=true` replaces the book. Proposed research handling starts a new epoch on
replacement and suppresses cross-epoch OFI. Preserve the20-level boundary: leaving
visible depth is not proof of cancellation. No mixing with obu rules.

HL snapshots replace the visible book. The first snapshot after connect/reconnect
establishes state; no flow is calculated against a disconnected predecessor.
There is no claimed contiguous exchange sequence or recovery of every intervening
order event. Opposite-side changes between sampled snapshots are an observable
proxy, not true cancel/add counts. Neither venue supplies full queue position.

Proposed bounded reorder/buffering policy: at most32 pending book packets and
250ms waiting for a missing prerequisite, within a global64MiB queue. If a bridge
cannot be established, emit a gap and resnapshot/reconnect within the finite retry
budget. Do not sort an entire future stream to conceal gaps. Late trade rows remain
late and enter only features that can be calculated causally at their receipt.
Empty valid trade windows mean zero only with continuously healthy subscribed
transport; absence of packets by itself is not evidence of zero activity.
Even a qualified zero describes the observed feed, not proof of no trading
elsewhere or no unobservable server omission. Heartbeats cannot prove a complete
exchange trade history when the channel provides no contiguous trade sequence.

Quality is per venue × instrument × channel × time segment. Masks include schema/
unit unknown, invalid/nonfinite value, crossed/empty/insufficient book, stale,
sequence gap, reconnect/bootstrap, duplicate conflict, local drop/backpressure,
clock uncertainty, late event and cross-venue skew. Unsupported field or corrupt
input is never coerced into price0, flow0, a complete book or a valid label.

Proposed common causal sampling grid is1s; use only last qualified available book
with receipt age<=2s. Flow uses a trailing60s window; full-window valid continuity
is required after any gap. Combined venue features additionally require selected
book availability skew<=500ms, valid source-age checks under measured clock error,
and both channels healthy. No linear interpolation across missing intervals.
Gate-only/HL-only metrics retain their own masks. Report the common eligible
intersection alongside the full operational clock, so selective uptime cannot
manufacture an apparent advantage. No silent fallback inside a combined score.

## 5. One finite engineering pilot, not a performance study

All limits below are proposed for a future separately authorized pilot. No process
was started in this task. QD must provide an offline collector design/review first.

| Resource | Proposed hard bound / stop behavior |
|---|---|
| Run | One run;3600s wall including shutdown; stop acquisition at3550s, flush by3600s |
| CPU / RSS | Total1800 CPU seconds,512MiB RSS; first breach stops |
| Connections | Two simultaneously, one public socket/venue; initial+4 reconnects each,10 attempts total |
| Subscriptions | HL four (2 coins×book/trade); Gate three (2 books+one two-contract trades); no account channels |
| Reconnect | Backoff1,2,4,8s per venue; no reset of retry allowance after a success |
| HTTP | Max32 public requests total, at most1/s,5s timeout; attempts count even if failed |
| Snapshots | Gate at most10 per contract,20 total, within HTTP cap; matching level depth |
| Metadata | Two Gate contract records and one HL public perpetual metadata response; remaining requests are failures/recovery only |
| Frames / queue | Max4MiB/frame;64MiB aggregate queue; no silent drop, invalidate and stop on overflow |
| Disk | At least8GiB initially free; hard4GiB all run artifacts, stop data at3840MiB leaving256MiB for closure evidence |
| Chunks | Close at64MiB or5min, whichever first; hashes/counts/ranges in manifest |
| Fault | Schema conflict, quota exhausted, unbounded clock error or disk/queue cap: stop affected run and record incomplete status |

Normal pings/acks are counted in traffic and stored; QD freezes their bounded
heartbeat policy before running. No credentials or authenticated HTTP fallback;
no public historical bulk download to conceal live gaps. Every shutdown returns
stop reason, first/last successful clocks, missing ranges, counts, checksum status
and resource maxima. A partial hour can yield useful engineering evidence but
cannot be labeled a complete pilot or silently extended for better observations.

Export: immutable `raw/*.jsonl.gz`, `metadata/*.json`, `manifest.json`, normalized
`books.jsonl.gz`, `trades.jsonl.gz`, `quality-intervals.jsonl`, `clocks.jsonl`, and
`feature-events.jsonl.gz` when separately implemented. Decimal strings survive
round-trip; the manifest hashes exact on-disk bytes, records schema/code/config
SHA, public metadata hashes and raw-envelope links. No extra dependency or format
conversion is needed for this design; a later Parquet export must prove type and
decimal/clock preservation before use.

Pilot engineering acceptance requires both assets/venues, complete manifest/hash
verification, deterministic export/replay, zero unexplained local drops/conflicts,
and explicit qualified/unqualified time accounting. Continuity is measured, not
asserted: propose >=95% eligible1s samples per book for operational pilot PASS,
with every excluded sample explained. This is a local engineering target, not a
market guarantee or evidence of research sample sufficiency. Failed coverage is
reported as failed/incomplete, never repaired by forward filling.

## 6. Small feature families and falsifiable mechanisms

All features use a single preregistered1s evaluation grid, trailing60s primary flow
window, top5 common depth and20-level diagnostic depth. No window/depth search.
Symbols are separate series; ratios are dimensionless, spread/impact in bps,
depth in base and venue quote units. Missing qualification produces null+reason.
The hypotheses are proposals; no coefficient, scaler or weight has been fitted.

| Family | Definition and financial hypothesis | Confounds / limits / failure criterion |
|---|---|---|
| F1 Aggressor trade imbalance | `(buy_quote-sell_quote)/(buy_quote+sell_quote)` over60s; persistent aggressive pressure may forecast short-horizon direction and adverse entry | Denominator0 is undefined; liquidation/internal transfers and fragmented activity can dominate; fail if after-cost effect disappears or only unavailable windows work |
| F2 Visible depth imbalance | `(bid_depth5-ask_depth5)/(bid_depth5+ask_depth5)` in base units; asymmetric displayed liquidity may predict pressure or adverse fill | Hidden/cancelable liquidity, spoof-like quoting and changing level spacing; does not reveal intent/queue; fail if effect reverses across assets/regimes or requires depth beyond capture |
| F3 Observed OFI proxy | Best-quote price/size changes summed over60s and divided by mean observed total best depth; changes may capture short-lived liquidity pressure | Sampled/coalesced updates omit intervening events; trade double counting and boundary changes; fail on gaps/resets or if only cadence differences explain effect |
| F4 Liquidity/impact/recovery | Spread=`1e4*(ask-bid)/mid`; displayed depth; two-sided sweep cost for fixed1000 quote notional; recovery after visible depth depletion | Visible book is not guaranteed executable; selection by volatility and latency; no beyond-depth extrapolation, no future recovery value at event start; fail if improvement is only fewer trades or underpriced costs |

For F3, one observed transition contributes:

```text
bid_component = I[b_t>=b_prev]*q_bid_t - I[b_t<=b_prev]*q_bid_prev
ask_component = I[a_t<=a_prev]*q_ask_t - I[a_t>=a_prev]*q_ask_prev
observed_OFI = bid_component - ask_component
```

This formula describes the proposed proxy, not a claim of exchange order-level
flow. Skip the first book, resets, invalid sides and any window spanning a gap.
Report Gate and HL separately before standardizing/combining them. F1 and F3
overlap economically; do not count both as independent discoveries.

For F4,1000 is a diagnostic notional, not a position budget. If visible depth
cannot cover it, output `INSUFFICIENT_DEPTH`, not a guessed tail price. Recovery
event: top5 total depth falls by at least50% relative to its preceding60s median;
observe the fraction regained30s later. Its availability is after that30s window
and all required observations arrive. The event-start row must not include future
recovery. Overlapping events merge into one episode until that follow-up ends;
thresholds are frozen proposals, not optimized. Record both bid/ask asymmetry and
whether spread/volatility changed; restoration can reflect repricing rather than
new liquidity provision.

## 7. Preregistered experiment sequence and finite comparisons

M0 is engineering only: approved one-hour pilot plus offline fault fixtures.
No one-hour performance, winning streak or model-readiness claim is allowed.
M1 is a future proposed fixed28-calendar-day forward observation, with a separate
storage/collection budget and explicit authorization; not an automatic extension
of M0. First14days train/development, next7 validation, last7 untouched test.
This duration may be statistically insufficient; report that outcome rather than
extend until profitable. No historical ticks are synthesized from candles.

Before a strategy test, freeze dataset manifest, first eligible UTC boundary,
prediction/holding horizons, episode/label rule, feature transform, decision rule,
weights and thresholds using only the training window. Permission to collect or
inspect data is not permission to fit any model/scaler/calibrator/weights. The
human must confirm that later training step. Validation may accept/reject the
single frozen candidate; tuning after seeing it consumes a declared new study,
not an unseen test. Test remains sealed until the final candidate is frozen.

Before M1, obtain review/approval of the dynamic ×10 binding in
`dynamic-sizing-amendment.md`; then use that frozen candidate with the same
capital, funding/fee accounting, clocks, latency, capacity and execution adapter
for every arm. The six proposed arms per asset are:

| Arm | Data / intervention |
|---|---|
| M1.0 | Existing causal baseline; no microstructure overlay |
| M1.1 | Gate-only overlay at entry and exit |
| M1.2 | HL-only overlay at entry and exit |
| M1.3 | Combined overlay at entry and exit |
| M1.4 | Combined entry-only, native exits |
| M1.5 | Native entry, combined exit-only |

One frozen policy form must be declared before any run. Entry overlay may veto
new increases; exit overlay may request reductions. Neither can increase the
native risk cap, reverse sign, force an increase, alter native adaptive parameters
or bypass UNKNOWN. Exit policy must respect the same causal state/finality/risk
rules. UNASSIGNED: actual score, weights, thresholds, feature aggregation and
execution-label horizon. Those require later train-window design and approval;
this document is not an executable strategy configuration.

Limit the future study to6arms×2assets=12 primary paths and the same12 with a
predeclared doubled fee/slippage sensitivity,24 maximum, no retries selected by
returns. This is a **separate proposed micro study**, not permission to consume or
expand the historical24-attempt register. A future resource register must be
approved before execution; no study run is authorized here. No alternative
multipliers, dozens of windows, thresholds or hindsight best weights.

Compare on identical time intervals, including flat/no-trade periods, and publish
both common-quality opportunity-matched diagnostics and complete operational
paths. On missing overlay data, block new increases and keep independently valid
native reductions; do not turn missing into neutral pressure or silently change
the combined arm into Gate-only. Apply the same availability restrictions to the
paired diagnostic baseline. Full-clock baseline remains visible to measure missed
opportunities. Every veto and its subsequent baseline outcome is recorded.

## 8. Statistical acceptance, selection risk and shared logic

Ticks are not independent samples. Count continuous inventory episodes, decision
opportunities and independent calendar blocks separately; adds and partial closes
stay in one episode. Report BTC and ETH separately, their dependence, volatility/
trend/spread regimes defined from past data, and clustering of losses/outages.
Use chronological purging: every training label must mature before the split,
with any episode crossing a boundary excluded from that split's fit. Embargo is
at least the maximum feature lookback and declared outcome/availability horizon;
never arbitrarily truncate a natural holding period to fit a short split.

Predeclare paired calendar-block resampling for uncertainty, retaining both coins
and all arms jointly. Determine block length from train-only dependence and
episode duration, at least24h; freeze it before test. A seven-day test can have
very few independent blocks. Proposed minimum for a confirmatory claim is30
independent blocks and100 mature episodes per asset per compared arm; if unmet,
label **INSUFFICIENT_EFFECTIVE_SAMPLE**, publish descriptive results and do not
claim a statistically established improvement. The proposed short study therefore
cannot by itself meet that confirmatory block threshold; a later preregistered
longer study would need new approval, not quiet post-result extension.

Primary estimand: paired change in net PnL per fixed calendar period after all
fees, funding and the same executable cost assumptions. Report net equity return,
maximum drawdown, turnover, exposure/time-in-market, capacity, tail loss and
adverse excursion. Secondary losing-run endpoints: episode loss probability,
distribution of streak lengths, longest streak, total losing episodes, recovery
duration and uncertainty, accounting for dependence. Fewer/zero trades can reduce
observed streaks mechanically: publish missed baseline gains/losses and opportunity
cost; zero trades has undefined win rate and no demonstrated trading improvement.

Freeze one family of five baseline comparisons (M1.1–M1.5); use Holm correction
for any confirmatory tests and report all effects/intervals, not the best arm.
Cost stress and subgroups are labeled sensitivity/descriptive; no repeated peeking
or claiming numerous tick-level p-values. Include failed, sign-reversed and
inconclusive hypotheses, selection history and rejected specifications. A smaller
loss streak without acceptable net economics and uncertainty is not success.
Insufficient independent data must be reported even if a chart looks attractive.

The future shared core contains feature availability/masks, signals, dynamic sizing,
risk predicates and explicit state transitions. It accepts normalized immutable
events; data-clock and execution adapters provide historical simulation or future
paper/live transport. For a fixed recorded event/availability stream, compare
decisions, quantities, state hashes, reasons and restart checkpoints exactly under
the declared numeric boundary. Inject future perturbations; earlier output must
stay identical. Replay fills and eventual live fills may differ; identical core
logic is not identical fills or a guarantee of profitability.

Cross margin is retained as intent. Present independent BTC/ETH paths do not model
shared equity, simultaneous competing reservations, portfolio covariance/netting,
maintenance-margin changes, intrabar liquidation, insurance or ADL. Later QD
account acceptance needs simultaneous-two-asset ordering, shared funding/fee cash,
reserve contention, equity ownership and insolvency stress, with QR review. Do
not combine independent path returns or change deployed risk defaults to pretend
that account model already exists.

## 9. Finite offline acceptance and handoff

These proposed fixtures are not executed collector/feature tests in this task.
QD should assign an exclusive new research collector/normalizer module and test
file; QR owns this preregistration and scientific review. New shared schema and
quality-mask contracts need their own request and owner/counterpart approval.
Do not edit an existing QD file without coordinator handoff.

| ID | Positive fixture | Required negative result |
|---|---|---|
| MP01 | Gate -108.5 contracts×0.01=-1.085 base; HL size in base | Integer truncation or merged settlement labels rejected |
| MP02 | Stable venue-scoped trade keys; duplicate provenance retained | Conflicting same-key payload fails; HL same tid/different time is distinct |
| MP03 | Gate base100 bridges U99/u102; covered update ignored | Next U104 after102 gaps; full packet never delta-applied |
| MP04 | Reconnect snapshot establishes state then warms60s | No OFI across reset or claim of recovered missing trades |
| MP05 | Empty update advances cursor; zero size deletes | Queue overflow/drop/unknown sequence cannot yield healthy book |
| MP06 | Receipt/decode-ready governs availability, late rows marked | Source-time sorting or future recovery leaks into earlier output |
| MP07 | Clock segments and venue masks preserved | Clock uncertainty/skew/stale input blocks combined score |
| MP08 | Internal trade retained and excluded primary flow | Internal/unknown side cannot be silently counted as ordinary taker pressure |
| MP09 | Raw chunk/hash/manifest round-trip and crash quarantine | Corruption/unfinished tail cannot be relabeled complete |
| MP10 | RSS/disk/time/retry cap produces finite stop receipt | Automatic extension, unbounded reconnect or silent data drop fails |
| MP11 | Replay and restart reproduce state; future changes leave prefix intact | Adapter/core divergence or future data changes earlier decisions fails |
| MP12 | Full-clock/matched-period reports include zero trades and all arms | Tick count treated as sample size or best-arm-only report fails |

Current status: official text and source code inspected; no market endpoint called,
collector run, raw dataset produced, strategy test or fit performed. Next is QD
review of a finite implementation plan, then coordinator-controlled approval and
dispatch. This document does not consume the current R05 work or training gate.
