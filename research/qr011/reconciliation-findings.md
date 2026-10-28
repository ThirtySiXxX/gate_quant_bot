# QR011: September 2026 microstructure reconciliation

2026-10-28 · BTC_USDT / ETH_USDT · base `88168f34c8c2855e9e65510bcde749cc459ff12a`.

**The current delta archive and snapshot archive cannot be treated as one exact
public order book. This is now established by initial-state-independent event
counterexamples, rather than just failed whole-book comparisons.** BTC's delta
stream is internally coherent across the next hourly boundary. ETH has a separate
source-encoded numerical precision problem. Neither result resolves the larger
cross-feed state differences. The supplier's exact upstream cause remains unknown.

No QR010 evidence is changed or promoted. This task does not fit models, replay
trading strategies/accounts, activate signals or change shared runtime contracts.
The machine-readable evidence index is [reconciliation-result.json](reconciliation-result.json).
New raw/diagnostic artifacts are ignored under
`research/.data/qr011/reconciliation/`; source hashes and line/ID references are
preserved. Arithmetic shadow states may be negative and are never valid books.

## 1. Fixed diagnostics and controls

We held the documented `set` initial state plus signed `make`/`take` additive
mapping fixed. No collection of alternative parsers was optimized against
snapshots. For each snapshot at an exact merged-ID boundary, compare quantities
at the same side/price against the previous eligible snapshot and intervening net
delta. Initial quantities cancel from this comparison. Absent prior levels are
known zero only inside that snapshot's visible price corridor; deeper prices are
unknown. Interior merged IDs are excluded, not interpolated.

| Pair | Comparable level transitions | Exact | Compatible with integer-floor censoring difference <1 | Larger discrepancy |
|---|---:|---:|---:|---:|
| BTC 2023-01-01 control | 58,827 | 58,827 | 58,827 | 0 |
| ETH 2024-07-01 control | 57,541 | 57,541 | 57,541 | 0 |
| BTC 2026-09-01 | 56,195 | 47,710 | 47,710 | 8,485 |
| ETH 2026-09-01 | 55,324 | 38,093 | 47,320 | 8,004 |

These are engineering comparisons, not independent statistical observations or
alpha tests. The controls test this new diagnostic on already-pinned files; the
old research suite, OHLCV acceptance and QR010 results were not rerun or changed.
The source IDs remain contiguous after the already-proved exact duplicate in
2023 BTC. Source ID continuity does not prove identical liquidity coverage.

## 2. Earliest proved discrepancies and rejected explanations

At BTC's first recorded snapshot (ID123743116006, current1788220801.274), bid
78544.5 has snapshot quantity14, while initial CSV line24591 has12877.0 at ID
123743115561. **No intervening delta touches this side/price.** Another untouched
bid,78540.9, is5815.0 in the initial state and2177 in the snapshot. The ratios
differ, rejecting a common multiplier conversion. Changing `make`/`take` semantics
cannot fix untouched levels. The actual upstream divergence may precede the file;
this is the earliest observable contradiction in the available comparison.

ETH's first snapshot (ID107314025459, current1788220801.355) reports bid2466.46
quantity43, versus untouched initial quantity410.8 at CSV line20522. An integer
floor cannot account for a367.8 difference. Some other small differences are
consistent with flooring, but that cannot explain the whole book.

The decisive BTC transition uses snapshots at lines3 and4 (IDs123743118849 and
123743119963). Bid78538.9 is2258 in both snapshots. Every intervening raw change
at that level is below, and each has merged-count1:

| CSV line | Event second | Action | Quantity | Source ID |
|---:|---|---|---:|---:|
| 47538 | 1788220803.8 | make | 16.0 | 123743119402 |
| 47559 | 1788220803.8 | take | 16.0 | 123743119424 |
| 47668 | 1788220804.0 | make | 128.0 | 123743119543 |

Net raw change is+128; snapshot change is0. This contradicts the intended mapping
even after reseeding from the earlier snapshot. It does not depend on a merged
interior ID, source initial quantity, float arithmetic, common quantity scaling,
or reversal of the sign. Treating the final `make` as an absolute size gives128,
also not2258. The pinned public-trade prefix contains no trade at78538.9 in the
first ten seconds, so simply subtracting those public trades cannot fix it.
This does not exclude unrecorded/internal event classes.

ETH has independent large transition failures too: bid2466.25 changes from9 to7
between its first two snapshots, while the seven intervening raw events net
**+46053.8** contracts. The raw error is46055.8, far beyond integer censoring or
the tiny numerical tails. Full event references are in the diagnostic transition
file and the compact `large_transition_mismatch` evidence.

| Hypothesis | Evidence-based disposition |
|---|---|
| Wrong initial seed only | Rejected as a complete explanation: many adjacent-snapshot differences fail independently of that seed |
| Uniform contracts/base/notional scaling | Rejected: untouched levels require incompatible ratios; matched transitions elsewhere use the same units |
| Side reversal or simple absolute-size replacement | Rejected as a universal mapping by the single-ID counterexample and the exact controls |
| Merged-count/off-by-one interpretation alone | Rejected as a complete explanation: the decisive three events have count1 and lie well inside the two snapshot IDs |
| Corrupt/truncated transport | Complete raw gzip CRC and hashes pass; corruption is not evidenced by these downloads |
| Wrong symbol/month/hour URL | Pinned symbol/date paths and overlapping clocks/IDs match; adjacent-hour seed comparison independently corroborates the archive chain |
| Legacy integer quantity display | Supported for subunit discrepancies by documented behavior and integer snapshots; cannot explain large BTC/ETH errors |
| Source numerical tails | Directly proved in ETH raw lexemes; explain the first negative residual but not large state differences |
| Different liquidity scope/event filtering or source snapshot defect | Consistent with observations; exact supplier mechanism remains unproved |
| Arbitrary time-shift repair | Not justified. ID-bracketed, timestamp-compatible discrepancies cannot be silently replaced with a hindsight best match |

Gate currently documents separate ordinary and RPI depth channels, and its API
changelog dates the futures RPI REST endpoint addition to2026-10-13. This shows
why liquidity scope must be identified, but **does not prove that these September
archives contain RPI orders**, or identify which feed is wrong. The archived CSV
has no RPI/event-class flag and the snapshots retain no request parameters.
[Futures depth channels](https://www.gate.com/docs/developers/futures/ws/en/),
[API changelog](https://www.gate.com/docs/developers/apiv4/en/).

## 3. Two new requests resolve the hourly-boundary question

Existing files could not establish continuity against a second full initial
state. An immutable plan therefore requested exactly two new objects: BTC and
ETH `2026090101.csv.gz`, one hour after the original anchor. No old object was
downloaded again; no earlier/other hours, currencies or current books were used.

| New object | Compressed bytes | SHA256 | Result |
|---|---:|---|---|
| BTC 01 UTC, N01 | 24,926,143 | `ab215a229488b634f7b6353abf541b9ef26f3d1e17852aa94a1e8099feaf40b5` | HTTP206 complete; gzip CRC pass |
| ETH 01 UTC, N02 | 23,704,818 | `e8f58db184028c3c913bc983ebcd3605d07a18d9d7ced2fd7ed63752d3c1f24a` | HTTP206 complete; gzip CRC pass |

BTC's final original delta reaches ID123746036996 at line2705755, exactly the
next initial ID. All **44,067 nonzero-union price levels match exactly**. Thus the
frozen additive interpretation reproduces the archive's next full state without
using any of its quantities during reconstruction. The raw archive is internally
consistent across this boundary; the public-snapshot mismatch is independent.
This is archive self-consistency, not independent venue/execution validation.

ETH reaches the next initial ID107316992580 at line2613213. Of39,951 union levels,
35,064 match exactly; the largest discrepancy is **2.908e−11 contracts**. All4,887
differences are below0.1, including tiny residual levels that the next file omits.
No value is clipped for this comparison. This supports an internally consistent
economic-scale archive with small numeric tails, while still failing strict
exact decimal equality. It does not explain snapshot differences of hundreds or
tens of thousands. The following hour was gzip-validated for this boundary test,
not certified as a complete reconciled second-hour market dataset.

## 4. ETH precision: proved source issue; no arbitrary epsilon fix

The first negative quantity has this entire raw chain:

```text
line20523 set  1238.3999999999999   ID107314023639
line36813 take 1217.1             ID107314023769
line38349 take   21.3             ID107314025564
exact remainder = -0.0000000000001
```

The decimal tails are present in source text before our parser performs any
arithmetic. Decimal50 preserves them. The source values resemble accumulated
binary floating-point output; the supplier's implementation language/algorithm
is not known. Switching our parser from float to Decimal cannot restore decimal
information already lost by the producer.

Across2,613,213 original ETH rows,41,745 lie off a tenth-contract grid, at maximum
distance1e−10; the smallest positive raw size is0.1. A **diagnostic-only** nearest
tenth falsification experiment removes all negative arithmetic-shadow events
(versus44,806 without rounding). It does not repair the independently proved
large snapshot discrepancies. No normalized dataset or production rule is emitted.
The observed maximum is not a guaranteed producer error bound, and the sample's
observed grid is not a historical venue lot schedule. No epsilon or inferred lot
size is approved. A future versioned normalizer needs effective historical quantum
and a justified producer encoding/error bound, and must reject deviations beyond
that bound; this task does not invent those inputs.

Gate's2025-12 announcement and WebSocket documentation describe a separate legacy
integer response path that rounds fractional quantities down unless decimal
support is requested. The snapshots are integer-valued, consistent with that
path, but the archive request header is unavailable. A raw observed new ask239.3
appearing as239 and a new bid0.4 appearing as0 provide direct corroboration of
lost precision. This is distinct from the CSV's tiny source tails.
[Official quantity migration notice](https://www.gate.com/zh/help/annlist/others/48788/gate-announcement-on-usdt-perpetual-contract-order-quantity-field-type-changes-and-feature-rollout-plan),
[Decimal response behavior](https://www.gate.com/docs/developers/futures/ws/zh_CN/).

For explicitly conditional legacy-floor research, `QR011-floor-bounds-v1`
represents reported nonnegative n as `[n,n+1)`, without guessing its fractional
part. Top-five bid depth is `[B,B+5)` and ask depth `[A,A+5)`; imbalance lies between
`(B−A−5)/(B+A+5)` and `(B+5−A)/(B+A+5)`. These are conservative bounds; no value
at the midpoint is fabricated. Both zero totals produce an uninformative[-1,1]
range, never neutral imbalance0. The helper requires explicit encoding evidence;
the actual archive examples remain labeled **conditional**, not exact recovery.

The maximum conditional imbalance interval width over the3384 snapshots is
0.0009761812 for BTC and0.0019964065 for ETH. ETH has1099 zero depth entries and
**three snapshots with a zero reported best-quote quantity**. Such a quote has no
proved executable capacity; never treat zero as empty and silently choose the next
price, nor assume positive size. Price-only exploration may retain the quoted
price as an indicative observation with that flag. No new exact OFI is admitted.

## 5. Initialization, invalidation and recovery decision

**Current status: no recovered, qualified public L2 stream.** A later archive seed
or a top-ten public snapshot cannot self-certify a compatible source scope.
Independent snapshot reseeding already fails the transition counterexample;
it cannot repair deeper unseen state either. Do not cherry-pick future matching
snapshots and label the past interval valid.

For a future compatible source, initialize only from a complete snapshot with
verified venue/instrument/liquidity scope, precision, source ID and available time.
Apply contiguous declared deltas after that ID; preserve unknown depth beyond a
limited snapshot. Gap, conflicting duplicate, unqualified clock/scope, impossible
quantity or unexplained independent-state mismatch invalidates affected features.
Under these archives a tiny negative quantity is still invalid without an approved
encoding bound. Stale caches and old good values cannot stand in for recovery.

Recovery requires a new compatible source snapshot received/available by that
decision, known precision, and a contiguous sequence from its ID. It is effective
from that point forward; it does not retrospectively repair an earlier interval.
Top-ten quantity bounds cannot authorize deeper-book slippage or queue inference.
Absent historical receipt/publication clocks still require a clearly labeled
latency/availability scenario; the current task provides none as a real clock.

These are research acceptance semantics for a future decoder, not a modification
to QD's current ledger/R05 contract or a newly scheduled implementation task.

## 6. Retained research uses and minimum next acquisition

| Source/use | Conclusion now |
|---|---|
| Delta + public snapshot as one exact executable L2 book | NOT_SUITABLE_IN_CURRENT_FORM; internally consistent archive does not prove compatible public liquidity |
| Standalone snapshots: indicative price/spread | INCLUDE for retrospective source-specific research with clock/zero-best-quantity flags; not fill prices |
| Standalone snapshot quantities | Conditional interval/sensitivity research only; need confirmed response encoding and source scope before ML admission |
| Exact sampled OFI from censored/mixed feeds | DEFER; quantity changes combine encoding uncertainty and unverified scope |
| Standalone exact-string public trades | Retain as a separate pressure/flow candidate; full objects/CRC/coverage and timing still needed; no new trade audit or full-month promotion here |
| Archive's own depth state | Retain for source investigation; no API-executable-capacity or venue-liquidity assertion |

The microstructure research direction remains active. One scientifically
identifiable route is a **snapshot/transactions-only** feature set, treating
quantity censoring explicitly and comparing it with a same-account baseline.
Another is a supplier-documented historical L2 feed with matched full snapshots,
deltas, liquidity flags and exact decimal quantities. Future ordinary/RPI/decimal
capture could establish channel semantics and latency from capture time onward;
it cannot manufacture historical receipt clocks. No vendor message, paid access
or collector was initiated here.

Before expanding acquisition, obtain the archive's versioned event/liquidity-scope
definition and exact quantity encoding, or select a documented alternative.
The smallest structural pilot for that source is one contiguous BTC+ETH interval
including a full seed, at least two independently sourced comparison snapshots,
the intervening complete trades/deltas and an hourly-boundary transition. Reuse
the fixed2026-09-01 anchor when available; widen dates only under a separate
bounded acquisition task. This pilot tests compatibility, not statistical power.

After that gate, continuous paired coverage must support the already frozen
calendar design (2023 warmup,2024 train,2025-H1 validation,2025-H2 through2026-09
sealed evaluation), or a documented coverage-driven revision before outcomes.
Measure dependence/effect size and mature costs under the approved shared
10000-USDT account. Neither this diagnostic's millions of rows nor a fixed count
of days establishes effective sample adequacy. Training remains **NOT_READY** and
requires fresh human confirmation before any model/scaler/calibrator fitting.
