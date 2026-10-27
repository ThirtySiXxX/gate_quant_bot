# QF-QD-005-HISTORY: canonical hourly v2 counterpart review

Date: 2026-10-28 Australia/Melbourne. Original review below was review-only;
the subsequent authorized build phase is recorded at the end of this report.
Dispatches: `QF-DISPATCH-20261028-QD005-SPEC-REVIEW-1` and
`QF-CONTROL-20261028-QD005-EXACT-DRAFT-1`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
Branch: `codex/qd-cache-safety`; parent:
`fabe12f883a803e1e98fb7d59621b561d1a92816`.
Exclusive change in this review: this QD report. QR owns the specification and
independent acceptance. Shared journals remain reserved for reviewed integration.

## Decision and exact identity

**ACCEPT the research-only data-production contract. G3 economic-label
compatibility is BLOCKED; zero baseline replays are approved by this review.**
There is no concrete blocker to building the specified data-only candidate after
QR freezes the specification and a separate build dispatch arrives. This review
does not accept an as-yet-unbuilt dataset, change runtime interfaces, approve a
funding adapter, or authorize fitting, deployment, trading or main integration.

Reviewed QR commit: `b545c8a9609c53c6ed3bb0735253a43a600eee05`.
Committed specification identities:

| File | SHA256 |
| --- | --- |
| `research/qr005/data-acceptance.json` | `4ba409d6270c0c0d6597389fc1b970ddc3657df74d392a444e260c6976cdc4ed` |
| `research/qr005/data-protocol.md` | `214e6c1fcca30abd1f9e5fc6f787294e8bb91e428001e9245b4d23b3529b6f07` |

Frozen v1 base manifest SHA256:
`5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd`.
Reviewed candidate SHA256:
`16035c8f9065ea79e4c572ce444b7af6a6b038f2526e5bda9273bf6580274dac`.
The base is the existing ignored `research/.data/qd004/history-v1/` in this
worktree. A future frozen spec must have its new commit and exact SHA recorded
before use; a semantic revision requires renewed counterpart review.

## Fields, boundaries, lineage and compatibility

- Schema 2 / `canonical_hourly_v2-r1` is a separate research manifest, not a
  migration of the shared runtime schema. Exactly eight usable files: two
  unchanged 1h, two unchanged funding and four derived 4h/1d. Native coarse bars
  and current-only metadata remain diagnostic evidence outside this inventory.
- Scope remains Gate USDT linear perpetual BTC_USDT/ETH_USDT and
  `[1672531200,1793091600)`. Price is USDT/base; volume is integer contracts;
  funding is a signed fraction per settlement; timestamps are UTC Unix seconds.
  Cross-coin contract volume is not a common base-volume or turnover measure.
- UTC epoch-aligned buckets require exactly 4/24 unique consecutive hourly
  children. Decimal first/max/min/last/sum defines OHLCV. Exact fixed-point
  serialization, sorted rows and LF endings are feasible without runtime edits.
  Decimal arithmetic must preserve exact sums rather than depend on ambient
  precision that could round a valid input.
- Each derived row has one ordered parent-row list and a bound parent file hash;
  parent rows resolve through unchanged source_id/source_row and the base duplicate
  ledger to raw origins. Aggregated rows must not claim a fabricated raw source.
  Relative paths, explicit base resolution, traversal/symlink rejection and a new
  output root prevent overwriting the frozen input or interpreting arbitrary paths.
- `available_at=max(child available_at)=bucket end` is an idealized proxy, not
  observed publication or arrival. Each coin retains all 33,489 hourly rows and
  emits 8,372 complete 4h / 1,395 complete daily rows. Tail evidence records the
  1-of-4 / 9-of-24 available children and remaining hours beyond the cutoff. An
  interior gap fails; an explicitly withheld final unclosed bucket is not a gap.
- Derived seven-column candle frames contain the native OHLCV/timestamp fields.
  Existing `strategy_signals.signal_at` selects bars by open plus configured
  interval, consistent with these complete fixed-grid bars. It does not generally
  enforce arbitrary arrival times. No direct dataset loader or integration is
  approved here; any future projection must retain the separate provenance.
- Funding is copied byte-for-byte, including second offsets and availability.
  The schema-2 descriptor's `interval_seconds=0` means no fixed event cadence;
  it must never be passed as native `funding_interval_sec`: native carry scaling
  and cost accrual would then be suppressed. A native interval assumption would
  need its own explicit review; current snapshots are not historical schedules.

## Funding compatibility finding and G3

`src/carry.py:60` aligns historical funding by backward as-of, including an exact
timestamp match. A record at 08:00:01 is unavailable at 08:00:00. The frozen input
preserves that distinction. Carry annualization additionally uses the caller's
constant interval; source identity does not establish that historical assumption.

`src/backtest.py:384-389` charges held positions using elapsed time divided by a
caller interval, endpoint notional and the rate available at the endpoint. This
is an unchanged hypothetical proration policy, not exact event settlement.
`_funding_rate_at` also falls back to a supplied constant before the first record;
these frozen streams begin at the raw start, but missing coverage must not be
silently repaired through that fallback in a future consumer.

Thus data-only acceptance is compatible with preserving the present code. It
cannot establish exact economic labels under G3: positions with no settlement in
their holding window can incur prorated funding, and second-offset events are
not debited at their source timestamps. Actual event accounting also requires
reviewed position eligibility and contemporaneous notional/price assumptions.
Current metadata, inferred schedules and arrival proxies cannot supply these as
historical facts. There is no review approval here to treat approximate cashflows
as exact labels or silently relax G3. A separate explicit hypothetical-label
policy decision or separately reviewed event-accounting work is required before
any baseline permission is reconsidered. No replay or adapter was implemented.

## Required producer and independent acceptance evidence

These are build acceptance criteria, not tests implemented or executed here:

| Positive evidence | Negative evidence that must fail |
| --- | --- |
| Four synthetic children `(10,13,9,12,1)`, `(12,14,11,13,2)`, `(13,15,10,11,3)`, `(11,12,8,9,4)` yield `(10,15,8,9,10)`; direct 24h equals six 4h aggregates exactly. | Rehashed wrong close/extremum/volume; nonfinite or invalid OHLC; negative/fractional contract volume; precision-induced rounding. |
| A 00:00 four-hour bucket becomes available at 04:00; perturbing a future child leaves every previously available bucket unchanged. | Availability at bucket open or 03:59:59; shifted grid, duplicate/missing interior hour, reordered or incorrect parent references even after rehashing. |
| Both coins retain exact 1h/funding bytes, complete counts, fixed cutoff, and explicit final withheld-parent evidence. | Rounded/filled funding, silently truncated hourly tail, emitted partial coarse bar, missing tail evidence, wrong symbol/unit or an added usable native-coarse/metadata file. |
| Parent hashes and every lineage row resolve to frozen source evidence; v1 and all 2,068 original disagreement records remain unchanged. | Valid-looking replacement parents, missing duplicate origins, hash mismatch, absolute/traversal/symlink escape, duplicate output identity, existing output root. |
| Two builds have identical normalized and lineage bytes; only declared creation provenance may vary. | Ambient numeric precision or source selection changes output; normalization substitutes native coarse values or changes the experiment range. |
| Causal funding lookup distinguishes 08:00:00 from 08:00:01 without rounding. | Schema descriptor interval 0 being treated as native cost/annualization configuration or copied source timestamps being claimed as observed arrival. |

## Verification, limitations and handoff

Read-only local checks passed: exact committed draft SHA; both frozen manifest
hashes; all 12 pinned normalized input hashes; all four committed evidence hashes;
each coin's 33,489-hour uninterrupted grid and hourly close-proxy availability;
the 1/4 and 9/24 cutoff remainders. Inspected native feature, signal, carry and
cost consumers. No generator, model, replay, network request or regression suite
was run for this report-only change. These checks do not certify v2 output.

Main remains at `cae0d2395adf2cd3905e41cb1c16748c8247c32c` with existing user work
preserved. Source staged-diff SHA256 remains
`c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`;
index-byte SHA256 remains
`7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.

Dependency: QR freezes the reviewed semantics and independently validates a future
candidate; coordinator issues a distinct bounded build dispatch. QD future claims
remain `research/qd005/`, `tests/test_qd_canonical_history.py`, this report and
ignored `research/.data/qd005/`. Do not edit QR paths, QD004 artifacts or shared
runtime/journals. Next step is freeze/build authorization, not automatic building,
baseline execution, fitting or merging. G1/G2 can later pass with declared
limitations; G3 remains blocked here, and prospective holdout/training permission
remain separate unresolved gates.

## Authorized producer build: code and tests

Dispatch `QF-DISPATCH-20261028-QD005-BUILD-1` authorizes the data-only builder,
one candidate and one separate reproducibility output, followed by QR review.
Frozen QR spec commit: `e1b459434e32e585e8a57d46b4bfedb0e79d7f67`;
`research/qr005/data-acceptance.json` SHA256:
`a516075cd2baced65dd659b520c6495d2cdf9d539ff8a1bfa2570c93ccfb63a4`.
Freeze changes are review metadata/state and zero replay budget; derivation
semantics are unchanged. G3 remains BLOCKED.

Implemented `research/qd005/canonical_history.py`: pinned-spec loading, complete
v1 file-hash preservation checks, strict hourly/funding input validation, exact
price selection and integer contract-volume summation, ordered JSONL lineage,
explicit unclosed cutoff tails, eight-file descriptors, fresh-root-only writing,
and local disk reread/recomputation with exact output inventory. Derived bytes
are independent of ambient Decimal precision/traps. The CLI refuses a build
whose source differs from the supplied committed source. No shared runtime
consumer, native cost configuration or QD004 artifact is changed.

Added 15 producer tests in `tests/test_qd_canonical_history.py`. Independent
literal OHLCV/volume and boundary expectations cover complete/partial windows,
daily equality, future perturbation, extreme Decimal precision, wrong schema,
missing/duplicate/shifted/reordered hours, invalid values/provenance, second-offset
funding, path traversal/symlinks, frozen hashes, duplicate base identities,
rehashed corruption, exact copies, reproducibility and existing-root rejection.
Fixtures use synthetic data only; they do not build the actual candidate.

Focused tests: **15 passed**. Full Python offline regression: **230 passed** in
10.795 seconds using the existing read-only interpreter and
`research/qd005/run_offline_tests.py`. Python socket connections are blocked in
the parent and macOS spawned workers. The initial full-suite stdin invocation
failed four existing multiprocessing checks because spawn could not reload
`<stdin>`; the real guarded entry script resolved the runner problem, without
changing the application or existing tests. No frontend change; JS was not rerun.

Reproduce regressions from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python research/qd005/run_offline_tests.py
```

Code and tests are committed before actual data generation. Candidate generation
and its exact code/manifest identities will be appended after the disk checks;
the implementation alone is not dataset acceptance.
