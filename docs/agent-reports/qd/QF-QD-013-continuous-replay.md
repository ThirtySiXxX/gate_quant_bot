# QF-QD-013 — local continuous replay and reusable preparation candidate

2026-10-29 Australia/Melbourne. **BOUNDED SYNTHETIC CANDIDATE VERIFIED;
actual-history execution OFF; training not authorized.**

Implemented callable local preparation/cache, indexed input selection, compact
native inputs and continuous registered account. A new synthetic run committed
16ticks/57financial records/10generated fills, reopened without resetting state
and completed one actual ETH native finality callback. After the original16-call
quota, separately authorized checks04–07 all passed once: one mature ETH episode,
one censored BTC episode, scenario isolation and reusable QR014 field export.
A separate single cold synthetic performance pair had identical product hashes:
6.37→1.13s process wall (5.637x), peak RSS144048128→137969664bytes (4.220% lower).
This is preparation-only engineering evidence, not a real training dataset,
full-history performance proof or whole-production-suite PASS.

## Authority, preservation and changed files

Dispatch `QF-DISPATCH-20261029-QD013-CONTINUOUS-REPLAY-1` plus amendments
`QF-AMEND-20261029-QD013-LOCAL-PERFORMANCE-1` and
`QF-AMEND-20261029-QD013-INDEXED-FACT-SELECTION-1`, plus separate bounded
`QF-AMEND-20261029-QD013-MEASURED-PERFORMANCE-1` and
`QF-AMEND-20261029-QD013-TARGETED-REPAIR-CHECK-1`. The latter explicitly granted
one04–07group, not a reset of the old16-call budget. The original persisted dispatch
was read completely. The index-selection amendment explicitly granted the minimal
QD009 `_invoke`/helper/index scope before that file was edited. No other ledger,
codec, VFS, financial reducer or resource-cap changes.

QD branch `codex/qd-cache-safety`, existing worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, exact parent
`c761d90d65bb33ef4256d26cba1a48163606e41f`. The only initial untracked files were
QD012's authorized launch-receipt/result; both remain untouched/uncommitted.
No new worktree/agent, main integration, push or shared-document edits. Current
main remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`.

Changed existing files:

- `research/qd009/streaming_ledger.py`: fact-candidate selection helper and one
  rebuildable index only, within the granted extension.
- `research/qd011/driver.py`: explicit native-v3 schema, latest selector, source
  pins and optional public-scan page size.
- `research/qd011/ports.py`: compact native projection, approved scenario costs/
  clocks, intent identity, skip-basket state and parameterized existing predicates.
- `research/qd011/export.py`: v3 routes to the new scenario-aware exporter.
- `research/qd012/prepare.py`: additive explicit reusable-cache entry; existing
  snapshot/native implementation and old manifest are not overwritten.

New: `research/qd013/{market,inputs,compact,scenarios,runner,exports,entry,benchmark}.py`,
`research/qd013/manifest.json`, `research/qd013/DEPENDENCIES.md`,
`tests/test_qd013_continuous_replay.py` and this report. No edits to `src/`, QR,
old tests/reports, QD011 codec, QD012 sources/queries/manifest or old evidence.
Commit identity is the commit containing this report; resolve with
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-013-continuous-replay.md`.

Adopted without rerun/re-review: QD012's7f481da actual snapshot and c761d90report;
QD011's61536c8 old synthetic lifecycle; QR01088168f3 binding; QR014f2c931b plan/
feature-sample contract and its17-test conclusion. QR files were read with `git
show`, not copied/edited/imported or executed. Earlier PASS results do not certify
this changed candidate or its full replay.

## Local read/cache/replay/export path

Everything is local Mac Python/local files. No cloud computation, upload, service,
download or dependency installation. Intended path:

```text
frozen metadata + explicitly permitted raw iterators
    -> original native batch functions + one covariance series
    -> immutable market SQLite (exact sources / computed observations / queries)
    -> per-trajectory streamed source/fact JSONL + original ledger admission
    -> registered environment/execution/feedback/policy/reserve, one account
    -> as-known mature/censored episode JSONL + reusable export manifest
    -> QR014 field mapping /169 closed candles (no matrix or fit)
```

Callable interfaces:

- `market.NativeSeries(hours, funding).snapshot(at_us)` computes the original
  native causal arrays once and projects available observations on demand.
- `inputs.build_cache(path, identity, hours=..., funding=..., mark_streams=...,
  initial_us=..., economic_end_us=...)` builds or reuses the local immutable cache.
  `prepare.reusable_native_cache` is an additive forwarding API.
- `MarketCache.get(kind,instrument,at)` / `records(kind)` use time/instrument keys;
  missing/corrupt/version-mismatched data raises, never falls back to app/cache/API.
- `runner.create(path, cache, initial_us=..., economic_end_us=..., tail_end_us=...,
  scenario_id=..., policy_id=...)` creates one registered shared account and
  source admission; `Replay.advance_chunk(tick)` actually advances its native
  policy/execution/financial state. It does not import prepared fills or PnL.
- `Replay.reopen(store)` registers the saved exact definitions and uses the
  existing ledger recovery/head validation. Tested only for a committed small
  v3 prefix at identical code/source identity, not stress/checkpoint/unknown-commit
  recovery. No code migration, reset or resume-after-quarantine is implied.
- `exports.export_all(replay, at)` / `write_bundle(path, records, identity)` are
  the candidate once-generated reusable export. `qr014_fields` converts tuple
  fields and refuses nonbaseline trajectories; `qr014_candles` maps169closed
  cached source rows without recomputing account history or building features.

## Bottleneck → implementation → evidence → remaining limits

| Previous bottleneck | Actual change | Semantic / operation evidence | Remaining boundary |
| --- | --- | --- | --- |
| Every hourly prefix calls prepare_native, reconstructs frames/covariance and serializes complete warmup | Original prepare_features once per coin over the supplied dense data; original EWMA covariance-series once; integer grid/asof projection at1h/4h/1d | Cases01/02 compared native fields/covariance f64 to closed-prefix originals and future perturbations; final fixture initial-prefix parity also passed in04 | Original FDM/correlation implementation remains; whole native arrays/source prefix O(N) memory. No exact incremental pandas-EWM replacement or full-history timing proof |
| Full warmup repeatedly copied into registered policy packets | Local native-v3 carries true first-open/counts, last available cells/full covariance and compact provenance | ClockGrid/Last call unchanged signal_at; unprovided historical cell access raises. No fabricated300bar arrays/constant ER/VR/regime or covariance sigma² substitution | Compact v3 is a new local input/intent version; old checkpoint hashes are not interchangeable |
| latest_available scanned/decoded/counted all history then discarded it | Existing facts_selection index, instrument/availability/context predicates before limit; exact per-instrument descending(available,key) latest; qualified_at_slot pushes exact economic time; sorted cursors preserve prefix modes | Case03 latest results equal old legal selection on multi-instrument ties/context/boundaries/unknown/future records; each latest read returns2 vs260old eligible candidates in the test | No real-history query-plan/timing benchmark. Resource charging now counts actually returned/decoded candidates, not discarded history; output/read limits unchanged |
| Skipping older rows could hide invalid closed-bar facts | New closure check over newly eligible ranges before limiting, memoized only for immutable source/schema/instrument/lower-bound | Case03 rejects invalid older closure even when latest itself is valid. Outer/source cell validation retained | Memo is derived local state and rebuilds on reopen; source/ledger proof is not replaced by an index |
| Repeated MARK prefix loading / separate clocks | One monotonic source cursor/instrument, bounded candidate deque + lookahead, primary and slow clock reuse | All three cache builds recorded846source points/coin,28queries/coin across two clocks, max7points in the window; unknown/stale result checked in02 | Fixtures supply literal parsed points, so no measured real gzip speedup. Original parser/grouping has its own bounded lookahead; max7is not a whole-process memory bound |
| All facts/raw records joined into one RAM list/string | Stream supplied rows and provisional facts, one final sequential hash-binding pass; ledger's original source admission/index handles actual facts | Registered creation/continuation04 passed with actual source/registry witnesses | Derived facts are still generated/admitted separately per trajectory; two sequential derived passes remain. No full-history mutable-index sharing/bypass |
| Repeated model experiments reread raw/account history | Immutable market cache plus once-written episode/proposal records; source identity and lifecycle manifest travel with them | Cache miss/hit/version rejection03 passed; no raw/native work on hit. Field/export code is callable | Original05–07failed; separately authorized repair group now all passed. Export builds O(events/episodes) maps once; not yet bounded external-memory export |

Cache identity includes frozen source descriptors/identities, code, research
configuration, schema, scope and availability/unit semantics. Metadata state must
be COMPLETE with matching schema/key/identity. Cells retain exact source strings,
integerUTC-us and digests; computed decimals roundtrip original f64. SQLite builds
into a unique `.building` file; transaction completion/fsync precedes exclusive
same-directory hard-link publication and directory barrier. Failure temporaries
are retained; incomplete files never become hits. This is incremental row writing
and atomic immutable publication, **not** a demonstrated online incremental-EWM
state engine. New source/version/scope requires a new key/build; no silent stale
reuse. Code identity is conservative and can invalidate more than native math
alone. Concurrent builders/crash/power-loss behavior was not tested here.

Market cache is shared read-only across trajectories; account/cash/orders/timing,
fees and generated ledger state are separate. Configuration/availability/source
metadata hashes are provenance, not numerical/model features; a changed frozen
source identity changes audit addresses. Future perturbation evidence concerns
past native values, not equality of hashes that intentionally bind different data.

## Registered continuous account: actual evidence

The final synthetic fixture is1600hours/coin, first decision after1440actual
closed hours; eight economic hours plus+2h settlement-only tail. It is an engineering
fixture, **not** the full2023warmup or2024–2026 economic sample. No actual raw
history payload was opened by this task.

Pre-repair run artifacts (retained):
`research/.data/qd013/engineering-1562158588960708/`.
Separately authorized successful repair group:
`research/.data/qd013/engineering-1565250031851000/`. The earlier audit address
below binds its earlier code; new source hashes intentionally create a different
registry address while the same financial fixture remains.

- One P0/ALLOW_ALL account initialized at10000USDT, both assets included in the
  original joint allocate_portfolio call, native volatility/risk x10 configuration
  unchanged; no duplicated per-coin capital.
- Committed16declared ticks,57financial records and10actual generated fills.
  Case04 asserted generated origins, all fills before the economic cutoff,
  nonempty held funding snapshots and asynchronous funding postings atR+60s.
- Advanced through hour3, captured all adapter states/head, closed/reopened the
  same ledger and asserted exact state/head equality before continuing. No capital,
  indicators, timing or risk reset at the segment boundary.
- Final head cutoff `1677747600000000`, slot5, committed_seq16; audit prefix
  `02aa5ee9ff0b1bb932eb0c87178ad0d6423049f5156c619656e2529c7096f254`.
- Existing environment/feedback output records one still-open BTC episode and
  one naturally closed ETH episode. ETH entry `1677718800000000`, natural exit
  `1677733200000000`, actual native completion `1677736800000000` (one hour later).
  Actual shared-account net feedback is `-28.834720125`, prior delivered cash
  `-28.859020125`, completion delta`0.0243`. The original full-state/sign/error
  guard passed; recorded native exact error is approximately-4.79e-16. Timing
  reset/rearm/blocked-side fields are stored in the generated callback result.
  These are synthetic cash examples, not profitability evidence.
- That earlier callback/proof preceded a failed export05. The new authorized
  group now successfully writes2episode records: one naturally mature ETH label
  and one BTC economic-cutoff censor with no target; all required finality,
  posting, completeness, exact denominator/cost and169closed-candle assertions pass.
- F_HIGH/ALLOW_ALL separately created and filled100contracts/coin at its first
  opportunity with actual `fee_fraction='0.0015'`. This was inspected in its
  existing generated journal after the test failed in export; it is a phase
  observation from the failed group. In the authorized repair group06, both
  F_HIGH/ALLOW_ALL and P0/SKIP_FIRST_ADMISSIBLE_BASKET were reached and passed
  identity/isolation checks, high-fee fill checks, skip-state retention and
  nonbaseline QR014 rejection. Other scenario accounts were not executed.

Eight scenarios/nine trajectories are explicitly registered: P0/ALLOW_ALL,
P0/SKIP_FIRST_ADMISSIBLE_BASKET, then F_HIGH, F_REFERENCE, S_HIGH, L_EXTRA, Q_LOW,
M_SLOW and T_FILL_FIRST with ALLOW_ALL. Fee/slip/latency/participation/mark clocks
and fill-before-snapshot ordering use the adopted QR010/QR009 values. Pending
whole-basket admission, divisor200, per-asset1m tier,6Egroup cap, unknown gating
and per-asset settled reentry remain. No default risk change or extra alpha fit.
The primary exact risk predicates were parameterized locally; broad legacy or
all-scenario equivalence was not rerun/proved.

The new runner sets ledger economic end separately from knowledge end. Tail
ticks permit only old obligations/postings/completeness/feedback; no new policy,
fill or forced flattening. Open inventory is intended to export censored with no
target. Assertions/revisions/late amounts retain real clocks and source lineage.
Integer funding source compatibility remains known only for the previously
approved2023snapshot prefix; new full account raw history was not examined and
the new calendar explicitly rejects fractional source seconds without rounding.

## Tests, failures, repairs and resource accounting

Exactly8unique new named methods, **16original plus4separately authorized method
invocations,20total**. The original failures remain below. No original
17/5/lifecycle/S07/full-suite/research tests or real snapshot entry were called.
At the original16-call boundary no further check ran until the targeted-repair
amendment arrived. That amendment authorized exactly04–07once, without retries.
Failed stores/logs remain; no cap/financial assertion
was lowered. Python socket connections were blocked in fixtures, not an OS sandbox.

Base command, QD worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd013_continuous_replay -v
```

Subsequent calls used **only** the four full names below under
`test_qd013_continuous_replay.ContinuousReplay`, in order04,05,06,07. The exact
separately authorized fourth invocation was:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd013_continuous_replay.ContinuousReplay.test_04_registered_continuation_preserves_state_between_chunks test_qd013_continuous_replay.ContinuousReplay.test_05_tail_natural_maturity_and_open_censoring test_qd013_continuous_replay.ContinuousReplay.test_06_scenario_identity_and_shared_market_isolation test_qd013_continuous_replay.ContinuousReplay.test_07_qr014_lineage_cost_breakdown_and_reusable_export -v
```

| New method | Original16-call allocation / reached result (new4-call PASS below) |
| --- | --- |
| test_01_native_series_matches_closed_prefix_bits | 1, passed:3closed prefixes' signal fields/full covariance bit equality to original prepare_native |
| test_02_future_rows_do_not_change_cached_past | 1, passed: future OHLCV/funding perturbations, explicit hourly gap rejection, two MARK clock boundaries and stale unknown |
| test_03_local_cache_and_indexed_fact_selection | 1, passed: build/hit/no native calls on hit, incompatible identity rejection, old indexed-selection equality and older-invalid closure rejection |
| test_04_registered_continuation_preserves_state_between_chunks | 3, final passed: actual native input parity on the final fixture, source admission, advancement, reopen/state continuity, generated fills/funding/tail |
| test_05_tail_natural_maturity_and_open_censoring | 3, final ERROR:2MiB registry page limit; no export PASS |
| test_06_scenario_identity_and_shared_market_isolation | 3, final ERROR:tuple in canonical proof; nonbaseline output and skip path not fully verified |
| test_07_qr014_lineage_cost_breakdown_and_reusable_export | 3, final ERROR from missing export after05; no reusable-label PASS |
| test_08_real_entry_off_and_fixed_scope | 1, passed: OFF reads no files, proposed ref format excludes old snapshot approval, full target remains2024–2026 |

| Retained log | Result | Wall s | CPU user+system s | Peak RSS bytes |
| --- | --- | ---: | ---: | ---: |
| initial-eight-1.log | 4pass,1fail,3error; v3 dispatch branch was placed at wrong function end and fell into legacy seed | 4.56 | 4.16 | 146456576 |
| affected-four-1.log | 4fail; after branch repair, low-vol synthetic fixture produced no entries through original no-trade buffer | 4.31 | 3.95 | 153960448 |
| final-affected-four-1.log | 04pass,05–07error; final admissible-volatility fixture and original strategy run, export issues found | 6.63 | 6.24 | 171163648 |
| **Cumulative / peak** | **16invocations, five distinct methods passed / three not passed** | **15.50** | **14.35** | **171163648 =163.234375MiB** |

Fixture adjustment changed only synthetic raw prices to exercise admissible entry
and ATR exit; risk/sizing/fees/clock assumptions and assertions were unchanged.
The final04included a fresh original-native parity assertion on that fixture.
Cases01/02were not rerun on the changed price fixture; their earlier comparison/
future evidence remains limited to its recorded scope. The initial failure's
unclosed-lease ResourceWarning is preserved in the log; that failed process ended.

Repairs made after invocation16;04–07were subsequently verified by their
separate explicit amendment:

- QD013 registry export requests1record/page through a new optional driver.scan
  size, instead of default64exceeding2MiB. No ledger page cap raised.
- Proof hashes pass tuple-valued proposal evidence through the existing canonical
  codec before digesting, fixing NONCANONICAL_INPUT.
- Added stricter cache schema/full-declared-warmup guards, budget callbacks for
  cache/export/source writing and O(1) tracked-allocation observation instead of
  a per-tick filesystem scan; new entry directory fsync barrier. These paths were
  statically parsed/reviewed. The new synthetic checks exercise cache/export,
  but the future actual-history entry paths remain unexecuted.

Separately authorized `targeted-repair-four-1.log`:04–07 **4/4PASS**,
7.59s external wall,6.39+0.73=7.12CPU s,152420352bytes peak RSS
(145.359375MiB), observed under30s/25CPU s/256MiB. The exact command is the
base command with the module replaced by these four full manifest-listed method
names in04,05,06,07order; thread variables OPENBLAS_NUM_THREADS, OMP_NUM_THREADS,
MKL_NUM_THREADS and NUMEXPR_NUM_THREADS were all1. No retries followed.
Total20engineering invocations across four groups:23.09wall/21.47CPU s,
peak171163648bytes. Eight distinct methods have each passed in their documented
scope;01–03/08were not rerun on final code/fixture, and this is not a green full
production suite. No hidden exporter/replay call evaded the original quota.

Original evidence before its summary:343files/34120216bytes. With the4762-byte
`resource-summary.json`: **344files/34124978bytes**, below64MiB. It records log
hashes, final source identities and resource observations. This includes every
failed artifact, not a fresh budget root. Existing ResourceBudget covered ledger/
source writes; other fixture outputs were observed, not claimed hard-limited.
No supervisor or OS-hard-limit claim.

Operation observations are recorded in each run's `operation-observations.json`.
Initial cache construction0.742191375s covered all8native snapshots and local
storage/queries; original3-prefix comparison2.055696375s also included reference
cache encodes/comparisons. They have different scopes/I/O, so **no speedup ratio**
is claimed. Counted work: original3prefix requests =6native prepares/3covariance
builds/6full-cache encodes; new whole-cache build =2native prepares/1original
covariance series/0full-cache encodes. Final cache build0.764060958s. Case03's
whole helper diagnostic recorded10SQL queries/272returned records across prefix,
latest and qualified cases; latest itself returned2vs260eligible old candidates.
The final continuation's64queries/80returned facts/12closure queries are only
the **post-reopen suffix** instrumentation, not all16ticks' cumulative reads.

## Separately authorized measured performance — single cold pair

Exactly2fresh Python workers, serial baseline then candidate; no retries, no warm
pair (original has no comparable persisted reuse path), identical interpreter and
thread environment (four numerical thread variables1), both import the same
modules. Original function remains byte-identical to base c761d90, SHA
`02337f8929fe2c0468ef065572f140b794e278062d86b3a22e876c37a3ec9f10`.
The shared strategy/portfolio/vol/trend/carry/execution_timing/config/codec files
also have no diff from that base. Current driver/ledger plumbing imports differ;
no account or ledger computation occurs in this benchmark. Candidate identities
are in both worker outputs and the final manifest.

Fixed input was selected before launching: exact raw synthetic hour/funding cells
from engineering-1562158588960708 (1600hours+201funding rows/coin,3602total),
not its computed native/mark cells. Fixture bytes1963212, SHA
`bd1b50895a24ec7e731fbf9aaa6c8ce2d3ed470c587656e3d83b9c62e8683d13`. Both variants produce eight identical hourly joint
products: all signal fields, full2x2covariance f64 bits, common NativeObservation
fields, exact selected source row IDs. Version-specific source_ref formats are
excluded explicitly; common fixture identity binds the complete input. Initial
account/timing semantics are unchanged, but no account runs here. Candidate
computes its whole supplied causal series once; old prepares each closed prefix
with its intrinsic full-context encoding, without retaining old contexts across
requests. No old full-replay versus new snapshot or cache-hit versus cold comparison.

**Exact common product equality PASS**,30293canonical bytes, SHA
`4593f80ef75998b8de6bc105c016fcf6867da618c60640f000985a0ce7dba0ab`. Only after equality was verified were ratios calculated.

| Observation | Original | Candidate | Improvement |
| --- | ---: | ---: | ---: |
| Whole fresh process wall, including imports/input/output | 6.37s | 1.13s | 5.637x,82.261%less time |
| Whole process CPU(user+system) | 6.11s | 1.12s | 5.455x |
| Native preparation phase wall | 5.706583125s | 0.711081541s | 8.025x,87.539%less time |
| Native preparation phase CPU | 5.665429000s | 0.703640000s | single observation |
| Whole process peak RSS, external time | 144048128B(137.375MiB) | 137969664B(131.578125MiB) | 6078464B(5.796875MiB),4.220%less |
| prepare_features calls | 16 | 2 | 8x fewer |
| Covariance work | 8build_covariance | 1ewma_covariance_series | original recursion retained |
| Full warmup cache encodes | 16 | 0 | eliminated from new projection |

Both read the same fixture once,3602records; raw history reads0, gzip
decompressions0, ledger scans0, persistent cache builds/hits0. This measures
native preparation, **not** SQLite-cache construction or full replay/export.
Identical common output is30293bytes; worker result files also contain metrics
and all compared products (sizes recorded in final resource inventory). Each
worker logs input hydration separately. Original fullcontext serialization work
is an intrinsic cost and is not counted as equivalent reusable cache output.
The separately authorized functional group observed a real market-cache build
0.800268125s, but it has no equivalent measured old persisted-cache baseline.

Performance budget was120wall/90CPU s,256MiB per worker and16MiBnew retained
evidence; observed aggregate7.50wall/7.23CPU s,peak144048128B, evidence about2MiB
(exact retained counts in final-resource-summary.json). This was one serial pair,
no statistical repetition; filesystem/OS caches are uncontrolled and baseline ran
first. No full-history throughput or future profitability inference. Candidate's
internal RSS137920512B stopped before result serialization; the larger external
137969664B is authoritative for improvement. Old and new engineering budgets
were not charged to or rerun through this performance authorization.

Reproducible invocation shape (already run once each; **not an instruction to rerun
without new scope**), from this worktree with the same four thread variables1:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd013.benchmark baseline --fixture research/.data/qd013/performance-1/fixture.json --output research/.data/qd013/performance-1/baseline.json
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd013.benchmark candidate --fixture research/.data/qd013/performance-1/fixture.json --output research/.data/qd013/performance-1/candidate.json --expected research/.data/qd013/performance-1/baseline.json
```

Evidence:
`research/.data/qd013/performance-1/{selection,fixture,baseline,candidate,comparison}.json`
and two external-time logs; failed engineering stores/logs were preserved.

## QR014 contract and reusable export boundary

The new candidate binds actual scenario/policy/account/trajectory IDs through
registry intents and proposals, exact pre-decision view/positions/equity, actual
generated opening/closing fills and scoped ledger readiness. It maps label
revision/status, natural end/known clocks, exact cash breakdown/net/gross-entry
notional denominator, input/posting/assertion times and provenance. No pre-supplied
PnL, forced exit, equity-based substitute denominator or double cost deduction.
Nonvalid open/immature output has no known target; cost attribution is explicitly
closed-slices-only until a whole mature episode exists. Checks05–07passed under
the separately authorized repair group, limited to this synthetic fixture.

QR014's current EntryProposal contract explicitly accepts only
`('P0','ALLOW_ALL','QR010_SHARED_NATIVE_X10')`. Other trajectories retain their
actual names and carry `qr014_compatible=false` / `QR014_BASELINE_ONLY`; they are
not relabeled as P0 to pass its validator. No QR edit or new research decision is
needed for baseline mapping. Any future training across sensitivities needs a
separate QR contract decision. No12-feature matrix, target fitting/scaler/model/
calibrator or QR17-test invocation occurred here.

## Concrete next proposals, remaining caps and stop

The exact04–07repair-check proposal received explicit authority and was executed
once successfully. Original16-call and new4-call budgets/failed evidence remain
separate. Next is review of the finite **actual-input pilot proposal**, not another
implicit test rerun or actual execution. The pilot and eventual full run require
new named approval; training/model/scaler/calibrator fitting requires user
confirmation before it starts.

Future real entry stays default OFF. Static format was checked for the new named
refs `QF-APPROVAL-QD013-PILOT-1` / `QF-APPROVAL-QD013-FULL-1`; no absolute path
argument or consumed QD012 approval/directory is reused. Exact proposed pilot
command **after export verification and a new human approval**, not run:

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd013.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD013-PILOT-1 --manifest-sha256 d6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a --scope pilot
```

Manifest at that SHA binds37code files (including the benchmark) and four accepted
metadata identities. Synthetic export checks now pass; actual-input proposals
still need separate scope review/approval and have unproven resource sufficiency.

| Proposal | Exact finite scope / required remaining goal | Proposed observations, not approved |
| --- | --- | --- |
| pilot | Full2023warmup, one P0/ALLOW_ALL continuous2024-01-01→2024-01-02 economic day +2h tail;32objects;8784hours/coin raw cap | wall300s/CPU200s/RSS512MiB;physical128MiB;expanded113724359bytes/928426rows;output128MiB |
| full | Full2023warmup;2024-01-01→exclusive2026-10-01 account and +2h tail;8scenarios/9trajectories;160objects;32856hours/coin | wall900s/CPU600s/RSS1GiB;physical1GiB;expanded2356028624bytes/53820701rows;output512MiB |

The pilot is a separate diagnostic, **not** a shortened final model/account result
or a segment to stitch into a full account. Full scope remains unchanged in target.
Within any declared trajectory there is one initial account and no annual/block
reset. Each full trajectory would require its entire frozen fact/schedule scope
from the start; immutable ledger inputs are not silently appended/rebound.

Critical remaining limits: whole arrays O(N); FDM unchanged; O(ticks) fixed
schedule/mark requirements still copied in causal definitions; environment funding
calendar/rate-prefix and tracked episode/state growth remain; per-account derived
spools are repeated; whole-export maps O(events). Original ledger per-store512MiB,
cumulative60s and2MiBadapter-state/read-page limits are **unchanged** and may stop
long before the larger proposal's outer observations. No full9-trajectory resource
sufficiency, minutes-to-finish promise, cache crash/concurrency acceptance, large
v3 restore or actual full-year batch equivalence is claimed. Do not approve full
execution merely because a callable accepts the full dates.

Entry uses a fresh fixed pilot/full artifact directory, exclusive receipt and
exact code/manifest/source identities; immutable local market cache can be reused.
Existing persistent resource accounting is retained, not reset. Cooperative input/
native/row/advance checks can overshoot observations; stop on first known failure,
preserve partial `.building`/ledger/output, no automatic retry or resume. The CLI
rejects resume; direct Replay.reopen is for a known committed same-code/source
state under separately reviewed operation, never a COMMIT_OUTCOME_UNKNOWN escape.
All cache/ledger/export outputs and old development files count conservatively
against the outer root-size allocation; no old evidence cleanup is authorized.

Known native/covariance/closed-tick and small registered-continuation engineering
evidence is available now; mature reusable label delivery and real replay are the
remaining real-input dependencies. The synthetic mature reusable export is now
verified. No new agents/chat messages or QR review loop was started.
No actual payload scan, snapshot rerun, old research revalidation, source checkout,
credentials/accounts/engine, trading, NAS/Windows, download, fit, main merge/push/
release or cloud computation occurred. Commit assigned candidate/report paths,
preserve all old/new evidence and stop.

## Final retained resources and handoff

`research/.data/qd013/final-resource-summary.json` records original16and new4
checks separately from the two benchmark workers, all six log hashes and37final
code identities. Final retained QD013 evidence: **541files / 56240391bytes**, including all failures and performance evidence, below64MiB.
Performance-only evidence: **7files / 2075591bytes**, below its separate16MiB limit.
These are observed file sizes; no new supervisor or hard OS resource guarantee.
No additional engineering tests or benchmark workers were launched.

Completed candidate is ready for review on its own QD branch. Actual frozen-input
pilot approval is the next dependency; full replay/sample acceptance and any
training authorization remain separate. No QR changes are required for existing
P0/ALLOW_ALL field mapping; QR must review any future cross-scenario training
contract. Shared PROGRESS/DECISIONS are left to the integration editor under the
current exclusive file allocation. No branch merge or push is authorized.
