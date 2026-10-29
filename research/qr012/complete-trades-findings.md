# QR012 — complete September BTC/ETH public-trades pilot

2026-10-28 · `QF-QR-012-COMPLETE-TRADES` · fixed interval
`[2026-09-01T00:00:00Z, 2026-10-01T00:00:00Z)`.

**Complete-object and neutral-aggregate checks pass for both instruments. Training
remains NOT_READY.** This is one month of structural evidence, selected before
measuring outcomes. It does not establish multi-year coverage, usable historical
arrival clocks, executable liquidity, predictive value or profitability.

## Actual measurements

| Measurement | BTC_USDT | ETH_USDT |
|---|---:|---:|
| Complete compressed bytes | 195,488,136 | 295,034,158 |
| Decompressed bytes, streamed without retaining CSV | 809,365,829 | 1,243,902,808 |
| Source/valid rows | 20,458,327 | 30,927,796 |
| Fractional contract-quantity rows | 0 | 17,457,765 |
| Minute buckets with records | 43,200 / 43,200 | 43,200 / 43,200 |
| Hour buckets with records | 720 / 720 | 720 / 720 |
| Invalid rows / duplicate IDs / time reversals | 0 / 0 / 0 | 0 / 0 / 0 |
| Adjacent ID steps greater than one | 0 | 0 |
| Largest gap between consecutive observed events, seconds | 48.674222 | 49.570751 |
| First event after month start, seconds | 1.740144 | 0.389037 |
| Last event before exclusive month end, seconds | 1.052902 | 0.904629 |
| Observed total absolute contracts | 18,287,292,734 | 6,246,062,318.6 |
| Smallest / largest minute trade count | 2 / 24,891 | 7 / 37,389 |
| Retrospective structural-pass minutes | 43,200 | 43,200 |
| Historically decision-eligible minutes established here | 0 | 0 |

Both gzip streams reached a valid terminal CRC/length check. IDs increase exactly
by one within each file. Every minute's count, exact contract sum and source-line
partition reconciles with its hour and full file. These are observations about
the supplied objects. Continuous IDs and populated minutes do not independently
prove that the exchange archive contains every relevant economic event.

Full compressed SHA256:

- BTC: `21bc62a4ced59aee8cb5f593a8bc783e3b8c67ed1076a54ca8891aa25e9959cc`
- ETH: `4cb318a4fee52f68089046d05937bd9406bbf7e548521c20d65b7bd78099981b`

## Acquisition and version proof

The immutable plan precedes all four serial data requests. Each symbol used a
64-KiB overlap probe and a tail GET beginning at byte 2,097,152. All responses were
206 with exact Content-Range, Content-Length, strong ETag and S3 version identity.
Probe bytes match the preserved QR010 prefix. The old prefix's complete 2-MiB
SHA256 is rechecked before copying it into a new object; only the validated tail
is appended. QR010 evidence is not modified. No full fallback, retry, HEAD,
redirect, credential, signed URL or private API was used.

| Symbol | Strong ETag | S3 version |
|---|---|---|
| BTC_USDT | `169b6e8bbb9185e51ce6ca6d61e45a64` | `4RAfw7Jv5MV39wzwEJjL5S7FrmgiQHhy` |
| ETH_USDT | `fbd00e1492cdf36d4ac6d610615285fa` | `MSLmiQbjmYZ7oMpWzPZaB.wjYQIyVRAl` |

ETags are treated as version identifiers, not assumed to be MD5 hashes.
Acquisition consumed 486,461,306 bytes of application bodies and serialized
headers; TLS framing is outside this accounting. The longest request was 8.795
seconds. Peak recorded RSS was 62,849,024 bytes. Actual receipts, operation timers,
caps and the hashed evidence inventory are in `complete-trades-result.json`.
The 12-request, 640-MiB network, 384-MiB object, 2-GiB retained/decompressed,
512-MiB RSS and 1,800-second active-work limits were respected. No earlier task's
budget was reset or enlarged.

## Field and aggregation rules

The archive publication describes four columns: timestamp, trade ID, price and
signed contract quantity. Quantity is measured in contracts; timestamp is UTC
Unix seconds. Prices are USDT per base unit for these USDT linear perpetuals.
The actual column counts and numeric strings were checked on the full files.
[Gate archive format](https://www.gate.com/announcements/article/21688).

The parser uses exact decimal strings for timestamps, price and quantity, rejects
nonfinite/nonpositive price and zero size, and retains raw source evidence.
It does not round ETH quantity to integers, clip residuals, infer a historical
lot size, or convert contracts using present-day metadata. Contract totals across
BTC and ETH are not comparable notionals without their historical multipliers.

Each research-local schema-1 minute record binds `gate:usdt:<SYMBOL>`, half-open
UTC minute boundaries, observed and deduplicated count/absolute-contract totals,
source object SHA256 and first/last source line. Hours sum exactly 60 such minutes.
These experiment records do not migrate any shared runtime contract.

The parser checks invalid rows, month boundaries, chronological order, ID order,
duplicates/conflicts and long interevent gaps. A bounded second pass resolves
nonincreasing IDs: exact duplicates retain one copy; conflicting IDs exclude all
versions from deduplicated totals and invalidate affected minutes. Empty minutes
would retain zero *observed* count with an explicit unknown-coverage flag, rather
than claim no trading. Fixtures exercise those failure paths; none occurred in
the two real files.

`retrospective_structural_mask` describes a completed full-file audit only. It is
not an online causal filter, evidence of event completeness or a usable trading
clock. Historical receive/available times are null and `decision_eligible=false`
for every record. Download time and monthly file publication time are evidence
acquisition/publication clocks, not reconstructed historical observation times.
No latency scenario, including a MARK delay, has been silently applied.

## Aggressor direction remains unresolved

The public perpetual WebSocket documentation explicitly maps positive/negative
size to taker buyer/seller, warns about fractional-quantity truncation without
decimal support, and distinguishes internal ADL/insurance transfers from normal
depth-matched trades using `is_internal`.
[Gate perpetual WebSocket](https://www.gate.com/docs/developers/futures/ws/en/).
The older public documentation also records the taker-sign convention.
[Gate legacy futures WebSocket](https://www.gate.com/docs/futures/ws/en/index.html).

The archive-specific publication describes position-side signs but does not
explicitly bind its historic producer to that public-feed aggressor convention,
numeric encoding or internal-event scope. The four-column archive carries no
`is_internal` flag. The conservative research status therefore remains
`UNKNOWN_ARCHIVE_TO_PUBLIC_FEED_BINDING`. Raw positive/negative row counts are
quality diagnostics only. `buy_contracts`, `sell_contracts`,
`signed_flow_contracts` and `trade_pressure` are null; price changes are not used
as a proxy to fill them. This is an unresolved binding, not evidence that the
signs are reversed.

Recovery requires versioned archive-specific documentation/evidence identifying
the producer mapping, numeric encoding and event inclusion, followed by a reviewed
adapter and tests for both signs, fractional size and excluded/internal events.
Current public-feed semantics alone do not provide that historical binding.

## Retained research path and training gates

The verified month supports neutral activity/count research, with explicit
historical-availability uncertainty. A later join to indicative quote/spread
observations must use separately reviewed availability and censoring rules.
This task does not repair QR011's exact public-L2 mismatch and provides no exact
OFI, queue position, fill, liquidity-capacity or shared-account return claim.

Before reporting readiness for a first model fit, the project still needs:

1. A reviewed feature/data scope: neutral activity is available structurally;
   aggressor pressure requires the additional archive binding above. Historical
   availability must be established or an explicit simulation scenario approved.
2. Sufficient contiguous BTC/ETH training and validation coverage, with a fixed
   unseen evaluation policy, leakage checks, warmup, label boundaries and embargo.
   A single 30-day pilot does not establish this coverage or statistical adequacy.
3. Accepted cost/label and shared-account semantics using the QD-owned streaming
   ledger. Source quality alone is not an economic acceptance result.
4. A human decision on the final calendar and explicit confirmation before any
   model, scaler or calibrator fitting.

Calendar correction: QR010/QR011's 2024 train / 2025-H1 validation / 2025-H2 test
suggestion remains a QR candidate. It did not replace the user's earlier 2024
train / 2025 validation direction. No split has been applied here; September
2026 is a fixed structural pilot, not a return-selected training/test sample.

QD continues its existing streaming repair assignment. Any runtime data adapter
requires QD ownership and coordinated review. QR012 does not reassign QD, reopen
accepted R05/QR010/QR011 reviews, start a collector or authorize another download.
Further coverage expansion requires its own prospective scope and resource plan.
