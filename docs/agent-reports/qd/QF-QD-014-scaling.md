# QF-QD-014 — compact full-history preparation candidate

2026-10-29 Australia/Melbourne. **New synthetic engineering checks passed;
full-history P0 entry prepared, not executed or resource-certified. No fitting.**

## Scope and preservation

Dispatch `QF-DISPATCH-20261029-QD014-SCALE-1`, refinement
`QF-AMEND-20261029-QD014-LOWCOST-1`, final resource-basis refinement
`QF-AMEND-20261029-QD014-RESOURCE-BASIS-1`. The last amendment added explanation
only; no additional engineering execution or implementation followed. QD's existing worktree:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, exact parent `9c8c19348a507aca1f0b9d0625480a26051532a4`.
Initial tracked tree/index were clean; only prior runtime evidence was untracked.
No other agent, worktree, timer or coordination/research review loop was created.

QD0139adcbb implementation and9c8c193actual zero-trade pilot, earlier4/4checks,
and the single paired native-preparation measurement are adopted without rerun.
No actual source payload, accepted historical snapshot or old suite/benchmark was
read or executed by QD014. QR015's accepted consumer conclusion is reused; QR
source, research decisions and old reports/evidence remain unchanged.

Changed existing files only:

- `research/qd009/streaming_ledger.py`: private compiled-plan access, indexed
  ranges/cohorts, active-funding selection and tracked quota observation; checkpoint
  schedule iteration/cursors adapt to the new local wire format. No economic
  reducer, allocation/attribution, price, amount, hash algorithm, VFS or LIMITS edit.
- `research/qd011/driver.py`: new source pins, explicit pending-funding selector
  in new plans, indexed declared-tick access; old interface output remains.
- `research/qd011/ports.py`: opt-in window/version validation and retirement of
  terminal private funding receipts; existing financial formulas are unchanged.
- `research/qd013/runner.py`: opt-in static plan and explicit new-store limits;
  existing defaults remain unchanged.

New: `research/qd014/{structure,runner,entry}.py`, `manifest.json`,
`tests/test_qd014_scaling.py`, this report. No edits to `src/`, QR files, codec,
QD013 exporter/manifest/entry, old tests, central journals or production config.
Only these10assigned files are committed; no runtime data is staged. The result
commit is the commit containing this report, resolvable via
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-014-scaling.md`.
Main remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; no merge/push.

## Concrete bottlenecks and implementation

QD013 copied all ticks/funding into five causal definitions. Every packet was
canonicalized/deep-copied/hashed with those constants. Ledger `_stage`, `_queries`,
`mark_context`, driver advance and cutoff scanned the full schedule/requirements
for individual ticks; `_queries` also scanned all requirements per purpose to
rediscover a cohort. Environment iterated the entire funding calendar and all
historical rates each call; empty/already-posted private receipts stayed in state.
`_bound` repeatedly enumerated growing store directories.

`structure.Plan` now compiles one immutable wire plan into rebuildable local
indexes. New wire versions are explicit:

- `qd014.schedule-grid.v1`: ordered integer UTC-us times and one slot-order vector;
- `qd014.mark-grid.v1`: instruments/clock/purposes and economic cutoff, generating
  the same per-tick requirements lazily, including all UNKNOWN outcomes;
- `qd014.static-plan-ref.v1`: exact digest of schedule, requirements and funding
  calendar, bound into every causal definition and thus genesis/audit identity;
- `qd014.plan-window.v1`: only next tick and due/active funding rows in a packet;
- `qd014.pending-funding.v1`: explicit local fact-selection mode, available-at
  predicate plus exact active source times using the existing facts_slot index;
- `qd014.active-funding-receipts.v1`: environment heads marker binds the plan and
  declares receipt retention semantics.

The compact plan validates versions, sorted unique times, adapter/clock bindings,
purpose identities, unique funding IDs and exact references. Mixed formats,
changed references, invalid bindings and unknown versions reject. No old-state
migration: QD014 Replay.reopen rejects an old schedule; a noninitial environment
state without the exact storage marker rejects. Exact code/source pin admission
and existing genesis/audit checks remain. Existing profile3financial event and
QR episode/cache output formats are unchanged; the new *internal* schedule is
explicitly versioned rather than passed off as an old materialized list.

Runtime tick/range lookups use binary search, cohort/purpose lookup uses indexed
keys, and compact requirements generate only the requested range. Each static
plan is serialized once in genesis instead of expanded requirement/slot records;
each causal packet binds its constant-size reference and current funding window.
The ledger still writes all generated financial events, state changes and audit
frames. Checkpoints stream the same expanded schedule rows when requested; they
do not hash runtime Python objects. Full checkpoint/restore acceptance was not
performed here—only same-code close/reopen of a known committed prefix.

Environment retains every unresolved nonempty funding receipt, including unknown
mark/amount/time. A receipt with no eligible ranges has no possible later revision
in the existing algorithm; a posted receipt has no remaining computation. Only
those private memo entries are removed after existing evaluation. Original
FundingSnapshot/ObligationRevision/Posting records and ledger obligations persist;
no settlement amount, duplicate financial event, late rate, missing value or
historical audit record is removed or filled with zero. Source/chronological
admission remains authoritative. Other episode/feedback histories are preserved.

New plans use the existing persistent quota's tracked allocation plus resource
book size for `_bound`, including conservative SQLite rounding and nested files;
they avoid scanning all root files every tick. Legacy plans retain their previous
store observation. This is quota observation, not deleting charges or increasing
old limits. No supervisor or hard OS-cap claim.

Complexity: old repeated static serialization O(T*(T+F)) and full requirement
scans (including per-purpose rediscovery) are replaced by O(T+F) wire/index
construction and O(logT + due requirements + active funding) range work. Financial
history/state processing and immutable journal volume are not thereby O(1).

## New checks, exact evidence and resources

Four new named methods; initial4/4passed. A subsequent validation hardening added
mixed-format/binding rejection, then only01/03ran (2/2passed). One additional
direct01check confirmed unknown/active funding receipts survive while empty/posted
memos retire. No old test/benchmark or actual replay ran. **7method invocations,
4unique methods**, no failed artifacts or retries hidden/deleted.

From the QD worktree, all calls used PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=tests,
and OPENBLAS_NUM_THREADS/OMP_NUM_THREADS/MKL_NUM_THREADS/NUMEXPR_NUM_THREADS=1:

```sh
/usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd014_scaling -v
/usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd014_scaling.Scaling.test_01_indexed_windows_and_version_rejection test_qd014_scaling.Scaling.test_03_short_financial_equivalence_and_same_code_reopen -v
/usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd014_scaling.Scaling.test_01_indexed_windows_and_version_rejection -v
```

| Method | Actual evidence |
| --- | --- |
|01 indexed_windows_and_version_rejection|Exact small materialized/compact schedule and query outputs for hourly/irregular/tail boundaries; invalid version/ref/time/mixed/binding rejection; missing prior marker rejection; unknown and active receipts preserved|
|02 full_target_structure_streaming_size|Full original target length, streaming expanded old/new requirement hash equality; size and work counts below, no economic replay|
|03 short_financial_equivalence_and_same_code_reopen|One newly prepared synthetic fixture,8economic hours+2h tail, two real registered accounts (materialized versus compact), original native policy/ledger. Exact equality of57financial event bodies,10fills, lots/slices/obligations/entries/links/orders, final balances, exact mature/censored label fields and cost breakdown. New account saved after hour3, closed/reopened with exact state/head equality, then continued.2exports: mature ETH and open-cutoff BTC. Old funding memos4versus compact0after settlement. Reject old-format reopen|
|04 entry_off_and_old_approval_rejected|Default OFF reads no files; consumed QD013approval pattern rejected before file reads|

Synthetic preparation is1456closed hourly source bars/coin, first decision after
1440actual hours; it reuses the known admissible *input shape*, not old test code,
stores, results or research acceptance. Test03compares current guarded legacy path
to opt-in compiled path; it is not a fresh pre-change standalone benchmark. Audit
hashes/state addresses differ by plan/provenance/version; financial body equality
is asserted rather than falsely requiring identical audit addresses.

| Retained log | PASS | Wall s | CPU(user+system)s | Peak RSS B |
| --- | ---: | ---: | ---: | ---: |
|initial-four-1.log|4/4|14.32|12.86|134610944|
|affected-two-1.log|2/2|11.64|10.13|140509184|
|receipt-guard-one-1.log|1/1|0.81|0.52|see resource-summary.json|
|Aggregate / peak|7/7|26.77|23.51|140509184(134MiB)|

Budget:120wall/90CPU seconds,512MiB peak observation,64MiB new retained evidence.
Observed inclusive fresh-process resources are below these limits. Socket guards
block Python connections; no OS sandbox/hard resource guarantee. Final retained
evidence is502files/56680246bytes, including all local account runs and quota logs;
`research/.data/qd014/resource-summary.json` binds logs,40source hashes and final
manifest. Runtime evidence is not committed. No more checks are proposed here.

## Actual structural improvement, not invented runtime/RSS ratios

Full fixed-length engineering plan:2024-01-01→exclusive2026-10-01 +2h tail,
30122ticks/150610slots,6024regular synthetic funding entries,301200MARK
requirements. The irregular real funding grid is not assumed identical: runtime
calendar derives actual integer source times and rejects unsupported fractions;
this static check is not new historical data acceptance.

Expanded old/new requirement streams match SHA256
`0b0130ed51daccea85cb3128b9d831fddfbe9a54bc096440e32da288f7103cb0`.

| Measured static content | Bytes |
| --- | ---: |
| Old expanded requirements, including newline per row |90721440|
| Old expanded schedule, including newline per row |12319898|
| Old five repeated causal ticks+funding payloads |7801410|
| New whole schedule/requirements/funding wire |1560653|
| New five causal references |665|

The repeated causal static payload reduction is **99.9915%**. This percentage is
for those serialized fields, not whole-process memory or total journal disk.
One-tick requirement range returns10rows independently of older plan length,
instead of scanning301200requirements each time. Financial-run work counters
after reopen cover only the suffix (105range lookups/720requirements/2funding
window rows in the first run); they are not whole-run totals.

No fair paired QD014process-speed/RSS benchmark was authorized or run; these
workers hold both account paths and perform structure checks. Therefore no new
speedup or memory-reduction percentage is claimed. Existing QD0135.637x process
preparation speed and4.220%RSS reduction remain their prior single-pair result,
not evidence for this change. Current peak134MiB is this new engineering workload.
SPENT times also include asymmetric close/reopen activity and are not a ratio.

## Full P0 execution proposal and remaining technical limits

Callable: `research.qd014.runner.create(...)` with same scope/inputs as QD013,
optional explicit new-store ledger_limits; returns Replay with indexed advance,
view and same-code reopen. Future actual entry is `research.qd014.entry`, OFF
unless the exact reviewed manifest and new named reference match. CLI rejects
resume; existing failed/unknown directories are never retried or migrated.

Manifest SHA256:
`2c75e6eeac69d9ad12f339041c7135126975235127284ac07b0f40422b49959b`.
It pins40code files and reuses the four accepted metadata identities. Proposal:
complete2023warmup, BTCETH shared10000, continuous P0/ALLOW_ALL account
2024-01-01→exclusive2026-10-01, settlement-only+2h, no reset/forced close or
reduced economic frequency.160frozen objects,32856hour cap/coin. Exact source
scope/permits remain in the manifest; none were opened by this task.

Proposed invocation, **not executed and not authority to launch**:

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd014.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD014-FULL-P0-1 --manifest-sha256 2c75e6eeac69d9ad12f339041c7135126975235127284ac07b0f40422b49959b --scope full_p0
```

Fresh fixed destination `research/.data/qd014/full-p0-actual-1/`, one invocation,
stop on failure/unknown/resource observation, preserve all evidence, no retry.
Cache identity includes code/data/config/scope and is built once for later reuse.
Requested **new-run** profile `qd014.full-p0-resources.v1`:

- outer observations:wall14400s(4h),CPU10800s(3h),RSS1GiB;
- input physical1GiB, expanded2356028624B,53820701rows;
- total retained output32GiB, fresh ledger store30GiB and cumulative wall4h;
- new adapter state8MiB/page16MiB; original8MiBtransaction,32MiBinput packet,
  8MiBresident index, read/event/exact-integer/per-adapter-wall bounds unchanged.

These are a concrete once-only stopping allocation proposal, not measured usage,
a user verbatim numeric selection or permission. Original LIMITS and all QD013
experiment counters/stores keep60s/512MiB/2MiBlimits; no old limit was silently
raised. New limits apply only if explicitly supplied to a new versioned-plan
store. They are not a guarantee a full run finishes.

Basis and limitations: the final short compact account retains12182373Bfor16ticks
(including source, registry, journals and SQLite). Pure constant-per-tick scaling
to30122ticks is already about21.36GiB, **not a forecast**; increasing trade/episode
history may require substantially more.32GiBoutput/30GiBstore therefore provides
bounded headroom over that simple planning quantity, but cannot certify storage
adequacy. The4h/3hstop allocation allows a sustained local run rather than falsely
claiming the old60saccount limit suffices; no full-history runtime was measured.

Remaining concrete risks: funding/history markers, completed episode feedback,
seen fills and receipt histories still accumulate; repeated episode selections
and full state/read/result persistence can grow faster than linearly with activity.
The8MiBtransaction limit checks the advance request, not the aggregate journal
payload; repeated state/read frames can therefore be much larger. The16MiBpage
limit may stop a registry entry containing multiple large states even before
an individual state reaches8MiB. Export retains
O(events)maps, full native arrays remain O(N), exact arithmetic may grow, fsync and
retained audit/index history remain costly. Full-length actual-source clocks,
trade-density state sizes, full checkpoint/restore and complete resource fit are
unmeasured. A CLI that accepts full dates is not full-history success. Preserve
and report the first actual stopping cause; do not trim history, hide UNKNOWN,
relax financial rules or switch to yearly accounts to pass.

P0may run first; simultaneous completion of nine accounts is not required. Fixed
subsequent order is P0/SKIP_FIRST_ADMISSIBLE_BASKET, F_HIGH, F_REFERENCE, S_HIGH,
L_EXTRA, Q_LOW, M_SLOW, T_FILL_FIRST. Every later account uses the full registered
scope and10000joint capital from its own start, shares immutable inputs where
identities match, and receives separate execution scope/resource allocation. No
return-based dropping/reordering. The current CLI scope authorizes only a future
P0proposal, not those eight additional runs or any fit.

## Resource-basis clarification and cheapest current full-scope path

The coordinator has **not approved or accepted4h/32GiBas necessary**. These are
proposal stop ceilings. This clarification uses existing file sizes/counters and
static code only; no new check, real read, pilot, benchmark or consumer experiment.

For the fixed target, H=24096economic hours, W=32856source hours/coin. Let Ebe
the actual economic funding entries across both coins; the existing full input
record cap is8214**total**, including2023warmup. No assumed daily funding grid
is substituted for the source. The regular synthetic full-size structure used
E=6024, T=30122ticks, Q=30120economic query times. In general every funding
entry adds at most3nonhour times (snapshot, posting, finality; its rate-availability
hour already exists), so T≤H+2+3E≤48740is a conservative structural bound.
Actual E/Tare unknown until the one approved source preparation, not reasons to
read the history again just for an estimate.

| Quantity/copy | Regular engineering-plan count | What is a bound/unknown |
| --- | ---: | --- |
| Existing immutable raw objects |160:2OHLCV+90funding+68MARK | descriptors total753030778physical B; no new raw copy/download |
| Expanded source-reader envelope |2356028624B/53820701rows | allocated transport limits, not newly observed input work |
| One market cache |290790cells =65712hour+8214funding+48192native+48192open+120480two-clock MARK | actual rates/query grid may differ; byte size depends on record mix, output cap is the only enforced byte bound |
| One P0derived supplied source |162648rows =48192native+48192open+6024economic rates+60240primary MARK | general rows4H+E+2Q; no full raw OHLCV copy in this per-account spool |
| Normalized fact file |same162648rows | one final file; preparation temporarily also has one pending facts file, not nine ledgers |
| Registry |150610entries=5T | conservative≤243700at the source cap |
| Query-status records |301200=10Q | five purposes×two coins; conservative≤487400 |
| Reserves / funding snapshots |60240 /6024 |2Q /E, including zero-exposure snapshots |
| Cash events/fills/episodes |not estimated from profitability | trade/activity dependent; emitted-event contract ceiling≤64×5T, not a realistic expected count |
| State invocations / frame boundaries |150610 /up to180732 | each tick has5slots plus slot0; versions/index paths and generated frames add write amplification |

Raw descriptors identify existing accepted files: OHLCV75211578B, funding43555B,
MARK677775645B. No new copy is needed. One source/feature cache can later be shared
across registered trajectories; one full P0ledger/source pair is created now,
with no speculative copies for the other eight. Pending/final fact streams overlap
only during preparation. Reusable cache/export artifacts prevent rereading/replaying
the account for each model experiment. These are record/copy counts, not exact
future disk/RSS measurements.

In the final short synthetic compact store, retained journals alone are8568465B
and SQLite2973696B; controls37313B, manifests14164B, guard inputs3072B, audit rows
18952B, other root files413838B. Journals dominate even after static compaction.
The12182373Baccount size also includes its derived source outside the store.
Multiplying this16tick small account by30122/16gives about21.36GiB, but its fixed
startup/source overhead, reopen activity and artificial trade density make that
**a planning illustration, not an estimate of real full-run need or a lower bound**.
The prior17.29sactual day was zero-trade and cannot predict a trade-active full run.
Neither observation justifies calling4hnecessary.

Yes, an O(N²)risk remains: completed episode/fill receipts and tracked episode IDs
can grow with activity; prior/peer states are serialized into registry reads, and
whole next-state values/results reappear in frames and durable journal payloads.
NodeIndex deduplicates content internally, but journal snapshots still repeat it.
Removal of terminal funding memos solves a specific accumulation, not all lifetime
state growth. Exact event/index retention also costs O(logN)paths per update and
fsync per tick. Broad time/disk ceilings do not cure these costs.

**Cheapest path executable with this candidate:** prepare the accepted full-scope
market cache once, then run only the fixed full P0/ALLOW_ALL account in one process
and one continuous store using the indexed plan. Reuse its once-produced export
and final-view component indexes for QR015; no repeated verification, nine-way
parallel preparation, extra audit platform, yearly reset, shorter/selective window
or forced completion. Stop on the first declared resource/unknown error and keep
the exact committed state. This is the minimum current execution path, not proof
it can finish cheaply. No automatic retry or fresh account substitutes a stopped
continuous trajectory.

If the coordinator requires a predictable substantially smaller disk budget, the
remaining technical work is specifically versioned reference/delta persistence
for accumulated completed feedback/fill receipts and repeated registry/frame state,
while preserving duplicate/completion guards and recoverable original evidence.
That is not a need for another research review. It is **not implemented in this
commit**, and pretending the current CLI guarantees low-cost full completion would
be incorrect. The coordinator can choose a single bounded execution allocation or
allocate that precise persistence improvement first; this task launches neither.

## What training preparation actually needs / QR015 dependency

QR015's public producer contract is unchanged: versioned market-cache cells,
episode JSONL/manifest, filled-episode nested proposal, as-known view/source
references, exact gross-entry denominator, costs and known-at/maturity clocks.
The new finite comparison exported the same mature/censored amounts and flags.
No QR files or feature order were changed, and no new proposal exporter was added.

Actual model preparation needs point-in-time features and proposal identity,
complete/mature cash targets (with exact costs), censoring/selection evidence,
and chronological validation boundaries. Schedule/registry/risk/audit records
are supporting provenance—not extra numerical model features. Not every check
must rerun for every model experiment; accepted immutable identities and once-made
exports should be reused. Nine sensitivity trajectories belong to final robustness
acceptance; they need not all run simultaneously before baseline preparation.

The existing final-view component counts and immutable ledger indexes expose
generated orders, decisions, fills/lots and registry entries; there is no dedicated
new count export. These count generated/accepted records, **not every considered
or rejected flat-entry candidate**. The producer currently emits proposals only
nested in filled episodes. A never-filled/rejected proposal inventory is still
missing, and a zero generated-order count cannot stand in for a complete proposal
denominator or an unbiased training population. The coordinator can separately
allocate that minimal missing evidence if QR's sampling design requires it; it is
not quietly fabricated from future fills or bolted into this performance task.

Next: coordinator may allocate the exact first full P0scope/resources under the
existing user direction, then inspect its reused export/counts before selecting
any further engineering fix. This report asks for no additional routine design
approval or research audit loop. No actual replay or training is launched here.
Model/scaler/calibrator fitting still waits for explicit user confirmation. No
activation, main merge, push, deployment, app/engine, real-money credential/order,
NAS/Windows, network download or cloud computation occurred. Stop after commit.
