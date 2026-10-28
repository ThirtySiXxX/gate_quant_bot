# QF-QD-008-REPLAY-PREFLIGHT: R3 engineering gaps

2026-10-28 Australia/Melbourne. **READ_ONLY_DESIGN; R3_NOT_IMPLEMENTED_OR_RUN.**
Dispatch `QF-DISPATCH-20261028-QD008-REPLAY-PREFLIGHT-1`.
QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, clean base `887d19629726c384a7cb88e9c9de1ff66534ee92`.
Only this report is editable. Result commit is the commit containing this file;
resolve with `git log -1 --format='%H' -- docs/agent-reports/qd/QF-QD-008-replay-preflight.md`.

Conclusion: a separate research event loop is feasible, but the current literal
synthetic ledger cannot be used unchanged as the full-period state engine. Data
independent acceptance, a reviewed scalable ledger/source-binding contract,
causal numeric adapter, MARK query coverage and a complete scenario/run freeze
are prerequisites. Raising4096 or partitioning/resetting accounts is insufficient.
This preflight does not accept candidate data or extend the ledger's scoped
independent acceptance to market replay.

## Frozen evidence actually inspected

| Evidence | Exact identity |
| --- | --- |
| QR006 protocol / acceptance | commit `c7e9a2492247fa31e216035f87e8bb20cca6e6ad`; SHA256 `4957875f25168ea33d630fb63be00a712d86ac049b932bdc11f731e8b980e270` / `d75fb7d7274ab2da41c71cd097f27982a3d2a7d103b5c1146d84da2429f9058c` |
| QD006 accepted implementation plan | commit `9bb3c0ec2b57e7154a51e56d795645c273c1308d`; SHA `199833b1d6d187efe12b153ea10772c123558844b9a9e7b4e9231fb0fb3d5838` |
| QD007 code / schema r3 | commit `0ea2d51901689a351068bb9d33906c3240832afa`; SHA `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636` / `7fd7df5f84a8822f5fdd37243d24e0eb293d9eeacda17514c8b1f1ad04ac475a`; current bytes match |
| Old public PhaseA fixture | QR worktree `research/qr001/replay_fixture.json`, SHA `e7ab2cfabfe09ec233ed64a809b1584255265254b572dce0427a74fac751879b`; public/simulated ETH snapshot, not private config |
| New MARK metadata only | coordination `mark-r2-raw-handoff.json`, SHA `30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce`; verified exact handoff bytes, no raw-object scan |

Native source remains byte-identical to this base and the old observer's pins:
strategy_signals SHA `aa3b9e71512008ff43f49639d8d2cf113e81def7ab031e41676453def86e78dc`;
strategy_execution `e1eaa17ea1292c7e906d4634b274fe72f2a415dfa409054674a33c22b9b1f5bb`;
position_sizing `e80773ec1bf0ec88fdf8128f368649cf123d3ad92b615b46d3ce3e754c20efad`;
execution_timing `41d4593eaf345cdc8d26759605651e3e7bcfcb679604416b29fef80b821d9344`;
portfolio `1837e2601c2255515644394b6934f45a933d11c758f93aafae926d9bb120397d`;
backtest `9183091e85c4354720118c53f0d97b72022f018afa03d9e9479f4929f5a8540c`;
costs `356d3f5a29df9a64caeb40948fe4408dad81982fa5255cba051deb578b70621e`.
Paths are under `src/`. Old `research/qr003/replay_probe.py` SHA
`4a0e520fa7b0a98565435aec07936bd4425592850a6e2e64b2116acd7d1d45aa`.
No in-progress QR007 report/validator was read. The exact final review subsequently
handed off is recorded below. QD008 OHLCV is still PENDING_INDEPENDENT_REVIEW in
this dispatch; no in-progress QR008 validator was read or awaited.

Control `QF-CONTROL-20261028-QD008-PREFLIGHT-LEDGER-ACCEPTED-1` supplied formal
QR007 commit `e2211a20bb0919b77506328e68867ff9357ec6c3`. Only the final
IMPLEMENTATION-REVIEW sections of its two exact Git objects were inspected after
hash checks: QR readiness report SHA
`7744cb841d2c839e60a16668a683d0a920891927a9a939012f49d42d4dd88474` and ledger-review
SHA `c4621c6d2718c7d48d269a78487509f0eb54e28a1bc65fb13846d1d2ae114ff8`.
Formal result: **PASS_SYNTHETIC_ONLY**, bound to QD007 code0ea2d519 and schema r3.
QR reports32 checker selftests,26 independent public-API cases and11 saved
artifacts, plus R01 causal comparison. These are separate QR results, not tests
rerun by this preflight or34 research criteria PASS. Coordinator reports exact
reproduction. Capacity, dynamic sources/checkpoints and R3/R4 remain unimplemented.

## Capacity and state continuity

`event_ledger.py:350-424,464-507,509-778,784-887` implements a complete immutable
in-memory fixture journal, not an incremental historical runner. The4096 gate is
unique normalized input identities per instance, across all record kinds and
instruments; splitting apply_batch calls does not reset it. Source catalogue rows
and expected-calendar entries are separate configuration, not a4096-hour allowance.

Each apply copies all previous records, scans/guards the full candidate, projects
inventory/finance/attribution, sorts/hashes the journal and copies its receipt.
Each snapshot/readiness query starts projection again. `_guard` scans the entire
funding calendar for each Fill and reconstructs prior-fill identity sets inside
the new-fill loop. `_inventory` repeatedly scans historical lots; `_attribution`
matches allocation/range histories to slices; Posting correction-cycle checks
walk chains. Consequently a projection is not generally O(N log N): lot/allocation/
slice/calendar combinations and correction chains can be quadratic. Even ignoring
these, one append and snapshot per event give at least quadratic total copying/
scanning/hashing; quadratic projection components can produce cubic cumulative
work. Returned snapshots also contain accumulated closed slices/obligations.
This is source analysis, not a measured full-period timing or memory benchmark.

Calendar-only sizing calculations (no market computation):

| Assumption / input | Scale / consequence |
| --- | --- |
| [2023-01-01,2026-10-01) | 32856 hours/asset;2023 warmup8760,2024 onward24096. Two independent hourly account clocks have48192 active decision opportunities, not necessarily trades. |
| One recorded valuation per full-period hourly account query | 32856 records/asset before fills/reserves/funding;4096 records cover only170 days16h. With valuation+reserves each hour, half that duration. Query selection/holding rules determine the actual count. |
| Illustrative8h calendar, **not an inferred actual schedule** | 4107 snapshots/asset alone exceed4096. If every event needs snapshot, known-total revision and posting:12321 records/asset before trades. Flat qualified no-obligation events may need only the snapshot. Actual count requires the frozen source-time calendar. |
| Fill/order sensitivity | For F fills add F Fill + at least F explicit fee Postings when booked, plus revisions/refunds/assertions and allocation rows. A no-fill order is selection/order state, not a fabricated zero Fill. No trade count can be inferred from bar count. |
| Prefix scans, one valuation/query per full-period hour | Even the simple sum1..32856 is539774796 record visits/asset,1079549592 for two, before sort/attribution/deep-copy costs. This is an arithmetic illustration, not a runtime estimate. |
| MARK handoff metadata | 90 objects,718396794 compressed bytes,56585147 physical rows, six BTC aliases. Never feed every physical point into the4096-record ledger or assume all point objects fit RAM. |

Even a sparse actual strategy cannot be certified to fit: no actual record count
has been computed, and neither the model nor budget loop exists yet. Warmup can
initialize indicators without orders under a frozen startup rule; initialize the
account once at its declared start. Never reset cash, FIFO inventory, reservations,
pending obligations, revisions, IDs, timing state or information history monthly,
at2024 start after an already active account, or at a fold boundary. Chunking disk
I/O is permitted only when the same economic state and historical queries survive.

Additional interface blockers: the config requires a complete literal source
catalogue with hashes of each input payload. A simulated Fill depends on prior
budget/decisions and is not a pre-existing frozen raw observation. Supplying a
precomputed answer catalogue or mutating `_sources` is not an online integration.
The current API has no public checkpoint/restore or dynamic source-registration
contract. `audit()` is a complete copy, not a resumable validated constructor.
Expected snapshots must be declared, matched and covered even when eligibility
is empty; omitting due events must not manufacture known zero. Late origin repair
is explicitly unsupported. These semantics need review, not private-field access.

Propose a separately versioned streaming implementation, retaining QD007 unchanged
as a bounded reference. QD owns its code; QR reviews the contract before changes:

- An atomic advance-to-availability API and explicit immutable raw catalogue plus
  append-only generated-event provenance chain. Bind generated events at emission
  to decision/order IDs, causal input projection, scenario/code and prefix state;
  global catalogue/trace hashes remain audit-only. Do not predeclare future fills
  as known information. Preserve all-record ID conflict/idempotency semantics.
- Incremental exact cash/claims, FIFO deques, per-obligation posting/revision maps,
  event-time indexes and lot-to-obligation/slice reverse indexes. Coverage checks
  advance a complete calendar cursor. Process only affected allocations/closures
  while retaining equivalent residual rounding and B1 unknown propagation.
- Persist the complete append-only journal and versioned state/checkpoint indexes;
  keep unresolved old lots/obligations and lookup paths for later corrections,
  even after natural close. A checkpoint restores economic state, dedup/revision
  identities, expected-calendar cursor, source prefix, reservations, pending orders,
  feature-prefix state, timing/sizing books and as-known clock. Past snapshots can
  replay a bounded journal suffix from an earlier checkpoint; restated remains
  separately named and cannot finance a decision. No history deletion disguised
  as compaction; settled finality is relative to referenced revisions.
- Before implementation freeze checkpoint/version/null/order/hash compatibility
  and crash protocol. Compare every causal snapshot/receipt/readiness against
  QD007 on small tapes <=4096; larger synthetic doubling tapes demonstrate bounded
  memory/index behavior and avoid repeated full-history work. Measure time/RSS/
  bytes and set growth limits before results. Reject partial commits, corrupted
  checkpoints, scope conflicts and unavailable dependencies; reproduce uninterrupted
  versus restart, arbitrary I/O chunk boundaries, fold crossing and late refunds.
  Future catalogue rehash changes audit identity only; past economic projection and
  available state must match. No larger cap is approved by this proposal.

## Exact data to unchanged numeric policy

QD008 exact JSONL and microsecond clocks remain the authority for source/ledger
values. Propose a separately versioned, independently tested numeric projection
inside the new research adapter, with strict input allowlist and source IDs held
outside its numeric arrays. Finite float64 is a computational approximation for
unchanged policy only; preserve exact strings for fills, cash, units and auditing.
Do not round-trip a native float fill into an allegedly exact market price.

| Native reader | Actual consumed inputs / boundary |
| --- | --- |
| `strategy_signals.py:15-35` | Short/main close for trend and volatility; regime OHLC for EMA/ADX gate; funding rate history plus explicitly reviewed interval/availability for carry; short OHLC/timestamps for adaptive risk and timing. ML path must be empty. |
| `strategy_signals.py:38-56` | Chooses bar opens <=decision_seconds-interval, minimum-history counts, short/main forecasts, regime, volatility, carry, adaptive multipliers and timing features. This does not enforce arbitrary observed arrival; adapter must restrict every input by explicit availability first. Existing nonfinite fallbacks cannot stand in for unsupported source coverage. |
| `execution_timing.py:65-89,115-195` | OHLC-derived ATR, efficiency/quality, extension, recovery runs, breakout/recent extrema; timestamps and bar interval. Stateful confirmation, last fill, entry/best price, session PnL and rearm status affect exits/entries. Volume is not used in this ML-off timing path. |
| `portfolio.allocate/should_rebalance` | Forecast/volatility/covariance, adaptive multiplier, capital, existing notional and unchanged exposure/leverage/buffer configuration. Covariance observations must be closed/available too; pure bar-count correctness is insufficient. |
| `strategy_execution.py:28-88` | Targets, current notional, equity, timing/sizing state and allow_increase/force-reduction flags; plan_order conversion uses current side/size, price, multiplier/minimum. Reversal closes first. |
| `position_sizing.py:40-88,94-122` | Equity, price, multiplier, min/max size, leverage and supplied tier caps, fee/slippage and available budget. BTC/ETH ticket policy requests200x with5% initial-equity sizing; whole contracts; current fixed-ticket holdings do not pyramid. Equity/available quantities have distinct meanings. |

Volume must retain fractional contracts in exact data and any numeric projection;
no integer cast or quote-volume substitution. The optional21-feature ML schema
is unchanged and not executed. Original CSV/seconds/native result versions stay
unchanged. For hourly policy timestamps, validate exact divisibility of relevant
bar/decision microseconds before conversion to native integer seconds; preserve
subsecond funding/MARK/order clocks in the exact event loop, not native bisects.

Freeze a float projection version, dtype/error measurement and boundary policy.
Test >2^53, long decimal prices/volumes, overflow/underflow/nonfinite, mixed scales,
quantity floor/round thresholds, fee-reserve/tier limits and comparisons at one
microsecond. Record exact-versus-projected errors; thresholds/tolerance cannot be
selected by returns. Exact post-checks must reject a numerically unsupported ticket
rather than silently changing native integer sizing or clipping it to fit. Define
which exact equity measure projects into allocation/ticket `equity`: C, E and the
spendable budget are not interchangeable. Unknown inputs block increases, not zero
capital substitution. This binding still needs QR semantic review.

Only closed-available prefixes may enter any feature computation. At time t use
bar_close<=t and research_available<=t plus source-policy qualification; t<economic
cutoff. A terminal bar closing exactly at cutoff cannot be consumed before cutoff.
Bind funding feature lookup to accepted availability, not source-record time or
the old fixed-interval fallback. Test prefix versus full-input computation with
legal future OHLCV/rate/mark perturbations; all past features, targets, decisions
and causal state must agree. Catalogue hashes, row IDs, retrieval times, future
inventory and audit hashes never enter numeric features, strategy branches,
economic state or random seeds. Retain provenance separately rather than removing
it to fake identical full rows after rehashing.

## Separate event loop and feedback requirements

The scheduler needs one reviewed deterministic merge of available-information,
snapshot, booking, decision, order/fill and finality events. It cannot call the old
native replay and repair totals afterward. Proposed sequence must be specified
for same-time pre-existing fills versus newly submitted orders, not filename order:

1. Admit information/revisions now available and select qualified MARK observations
   with their source and delayed consumer clocks. No final rate enters an earlier
   decision. Capture scheduled funding eligibility using the approved same-time
   sequence; snapshot-before-same-time-fills is the reviewed primary template,
   with opposite order only if preregistered as a stress. Keep exact eligible
   quantities/FIFO ranges, including zero eligibility and post-close ownership.
2. Apply available known-total revisions and independent Postings in their reviewed
   dependency order. Recognition changes T/P/A/L, not cash; only Posting changes
   C/B. Missing mapping/mark/amount/coverage is unknown. At each actionable boundary
   compute C/A/L/U/E and `C-L+min(U,0)-reserved_margin-reserved_fees` as-known;
   A/positive U are not spendable. Never use restated/audit balances for financing.
3. With causal signals, evaluate existing natural exits/reductions before new risk.
   Unknown/stale U, reservations, pending T or required MARK support disables
   opens/adds and reversal's new leg while retaining eligible reductions. Native
   `build_order_plan(...allow_increase=False)` removes open actions, not closes.
   A logical reductions_supported flag does not promise an executable fill where
   trade-price/capacity evidence is missing: retain pending/cancelled exit status.
4. Schedule only permitted fills at/after decision+latency and a real executable
   event. On each actual partial fill, charge its exact fee once, split closing/
   opening reversal legs, update FIFO/entry notional and release/recompute reserved
   amounts. Recompute the budget before another opening leg or another order;
   no stale pre-close ticket or double-reserved posted fee. Pending unfilled
   remainder retains its cancellation policy. Slippage is adverse once in fill
   price, never another expense deducted from net.
5. Feed confirmed quantity/price and permitted as-known PnL to unchanged timing and
   sizing books. `TimingState.session_pnl` determines rearm after loss: the choice
   of feedback PnL when natural close precedes funding booking is an unresolved
   adapter contract. Never supply eventual net via hindsight or silently rewrite
   old rearm state after a later refund. Define and review delayed feedback/unknown
   treatment explicitly; ledger correctness alone does not settle this choice.
6. Carry all state across fold/calendar/I/O boundaries. A fold is an evaluation
   annotation, not liquidation/reset. Preserve naturally closed but immature
   obligations/assertions and revised as-known histories. At cutoff keep open
   exposure censored under the eventual exporter rule; forced diagnostic close
   cannot become a natural-exit target. Unsupported conditions retain invalid/
   unknown reasons; legitimate unsettled outcomes remain immature. No bad-return
   filtering. Any post-cutoff booking/finality evidence window must be separately
   bounded; do not add market observations or mark origins outside approved bounds.

Illustrative budget/feedback acceptance, hand-derived only: QF006-A20 starts
C1000/L30/reserves105/U0, so budget865; posting-30 gives C970/L0 and still865.
U=-40 gives825; U=+50 still865. Unknown U gives no budget/new risk. QF006-A26's
first loss50 leaves cash50 unable to finance ticket80; skipping that first entry
leaves cash100, so the next eligibility changes. Full state must diverge; deleting
the first trade from a fixed old ledger is not this experiment. No scenario was
run and these literals are not new capital/reserve defaults.

Why the old PhaseA probe is insufficient: it invokes the unchanged native loop
and observes/skips an entry, retains float averages and elapsed-time funding
(`backtest.py:384-389`), supplies old equity-minus-margin budgets, and force-closes
remaining holdings at the last price (`:537+`). Fees/funding are accumulated with
positions until reductions/close rather than independent available Postings;
there is no current T/B/P/assertion/fresh-MARK financing loop. It prices current
bar opens without an explicit event-latency/capacity queue, and its snapshots are
observation fingerprints, not restart checkpoints. These were appropriate old
observer semantics, not a defect fix or permission to change native rules. It
cannot satisfy the new protocol by changing report labels or postprocessing PnL.

## Numerical inputs: approved versus still to freeze

Do not re-ask the already approved choices supplied by this dispatch: per-fill
fee fractions0.00075 primary/0.0015 stress/0.0005 reference; MARK source+60s with
age120s and stress+120s/age180s; funding source-time mapping, next-whole-hour+60s
availability and+1h finality; integer tickets with scenario multipliers BTC0.0001/
ETH0.01; end-exclusive2026-10-01; approved whole-record OHLCV segmentation. Bind
their exact rule IDs/formulas/authority/clock definitions into the frozen run spec;
the terse handoff is not a replacement for typed event inputs or booking linkage.

Still needed from QR/owner, and user only for materially new scenario choices:

| Unresolved input | Required freeze; old evidence is reference only |
| --- | --- |
| Base slippage / fills | Adverse bps or exact price rule, partial-fill capacity, no-fill/cancel deadline and reservation release. Old public fixture cost_config.slippage_bps=2; strategy max_entry_slippage_bps=8. Native uses max(cost,entry limit) for ticket reserve but cost slippage for actual fill. Neither2 nor8 is approved as the new base fill cost by inheriting that fixture. |
| Decision/latency/executable open | Exact decision schedule, delay, equality and next-observed-open rule; no same-open execution after positive latency or inferred intrabar stop/queue. Accepted MARK delay is not order latency. |
| Capital / reserves / account scope | Initial C, ledger start/warmup exposure, independent account identity per asset/trajectory, allocation/ticket equity binding, reserved margin/fees for pending and held positions, expiries and double-count exclusions. Old fixture10000USDT is historical reference, not new approval. No zero-reserve assumption. |
| Ticket/risk scenario metadata | Explicit supplied historical-scenario tiers, leverage/min/max limits and price rounding if used, distinct from current exchange snapshots. Keep existing5%/200x native logic and disabled daily-loss gate; accepted constant multipliers do not prove real historical tiers or liquidation survival. |
| Posting/feedback/finality details | Exact synthetic booking IDs/clocks relative to accepted funding availability, fee posting assumptions, assertion scope including late corrections, timing feedback PnL when net is not yet known, and whether evidence observation continues after market cutoff. Do not reopen accepted lag values; resolve their typed bindings. |
| Stress/run budget | Freeze finite scenario matrix and paired trajectories/counts: selected cost levels, slippage/latency/capacity/tie-order combinations, which are primary versus sensitivity, and total attempts including failures. No automatic full Cartesian search or old PhaseA allow-all+three-skips budget reuse. |

Hourly contract volume is not contemporaneous executable book depth. Any proposed
volume participation/capacity rule remains a disclosed simulation assumption;
data precision acceptance does not calibrate that fill rule or prove actual fills.

The old fixture SHA above explicitly records10000 capital,2bps, ML off, ETH0.01,
an illustrative28800-second funding interval, a2026-10-27 contract/tier snapshot,
and a later-than-current-cutoff sample. Its cost flags can reference account/contract
fees. None grants private access, current fee selection, historical tiers/schedule,
new cutoff expansion or R3 run permission. QF006's original0.0005 proposal is now
the user-approved reference fee, not the new primary. Preserve the old fixture.

## Minimum ownership, dependency sequence and prospective run contract

These are proposals requiring allocation/review, not files created by this task:

| Order / owner | Smallest isolated deliverable / gate |
| --- | --- |
| 1 QR / coordinator | QD007 synthetic-only acceptance is now supplied as above. QD008 OHLCV acceptance, MARK content/query semantics and explicit scenario/run inputs still require handoff. Current metadata intake completion is not coverage PASS. |
| 2 QD implementation, QR contract review | New versioned streaming ledger, e.g. `research/qd007/streaming_ledger.py` and `tests/test_qd_streaming_ledger.py`; source registration/checkpoint contract first. Leave QD007 code/tests/schema immutable. No existing private API bypass. |
| 3 QD lookup, QR independent coverage | Separately allocate a bounded MARK query selector/index and synthetic tests, e.g. `research/qd008/mark_queries.py`; QR owns its independent query checker. Reuse approved raw; no new collector or generalized database. Freeze resources for56M points before constructing an index or point table. |
| 4 QD, QR semantic review | Earlier QD006 proposed `research/qd008/native_adapter.py`, `tests/test_qd_event_replay.py` plus role report. One small module may contain explicit numeric projection, unchanged native policy calls and separate event scheduler. Separate namespace/state/trace; no edits to native policy or21-feature format. QR owns independent trace/budget/path tests. |
| 5 Coordinator / QR | Only after synthetic equivalence/causality/restart and accepted inputs, authorize a finite R3 market run with preregistered hashes/budgets. No actual-run approval comes from this preflight. |
| 6 Later QD exporter / QR semantics | Preserve QD006 stage4 allocation: `research/qd009/episode_export.py`, producer tests; QR label policy and independent validator. R3 trace is not already an approved EpisodeLabel dataset. No fitting. |

MARK handoff reports RAW_INTAKE_COMPLETE_PENDING_INDEPENDENT_CONTENT_AND_QUERY_REVIEW,
canonical_point_table=NOT_WRITTEN and required_query_coverage=NOT_EVALUATED. Its
metadata maximum gap is2547.948272s (about42m28s), not bounded by120/180s freshness.
This does not prove a required query actually falls in the gap. No raw points or
new query support rates were computed here. Alias handling cannot repair gaps;
no interpolation, dropping unsupported decisions or trade-price substitution.

Before a market run the bounded manifest must freeze:

- Exact accepted dataset/catalogue/approval, raw MARK/funding hashes, canonical
  point/query schema, native and new code commits, projection/checkpoint contracts,
  Python/numpy/pandas versions and complete scenario/config including ML-off.
  Audit IDs identify artifacts but never become economic inputs or seeds.
- Explicit economic window, warmup and any later evidence-only window; initial
  account state and per-asset/trajectory scopes; fold calendar and no-reset rule.
  Freeze a finite MARK query universe for decisions, funding snapshots, permitted
  fill times and valuation/reserve checkpoints, under both accepted clocks. Use
  a preregistered path-independent superset or a deterministic generator whose
  finite schedule/rules are frozen before outcomes; record closure proof and all
  realized subsets. Unexpected queries stop for review, not on-demand silent
  universe expansion. Never define required queries after dropping bad paths.
- Resource ceilings for full run count, wall/CPU time, peak RAM, disk, event/trace/
  checkpoint counts and maximum branches, including failed attempts. R2's two
  builds/300s/512MiB do not authorize or size R3. Bounded synthetic scaling must
  precede numeric R3 limits. MARK streaming/index creation needs its own budget.
- Append-only whole-state trace: every proposal/no-proposal/block/order/cancel/fill,
  economic/known/available clocks and event priority, qualified query/raw references,
  before/after causal balances, lot/pending/reserve transitions, native timing/sizing
  state, lifecycle/censor reasons, assertions and checkpoint/journal prefix hashes.
  Every branch starts identically and then follows its own complete state path;
  artifact IDs never replace the underlying numeric state in independent checks.
- Stop on hash/scope/ordering mismatch, missing required dependency, unknown or
  unsupported coverage according to the frozen rule, accounting/causality failure,
  unreconciled checkpoint, resource exhaustion or exhausted attempt budget. Declare
  fail-whole-run versus retain unsupported-state/no-new-risk policy before outcomes;
  no universe shortening, profitable-path selection or retry-budget reset. Retain
  partial trace/error receipt and never publish ACCEPTED from an incomplete run.

Minimum QR handoff: exact run manifest and immutable inputs; complete event/order/
selection/financial trace; restart checkpoints/prefix identities; per-query MARK
qualification and unsupported reasons under both clocks; exact reconciliation of
cash/obligations/FIFO/reserves and fees/slippage; rejected/censored/immature counts;
source/version manifest and resource/attempt/error ledger. Provide small literal
synthetic tapes alongside full-path artifacts. Independent checks use their own
accounting/parser and trace rules, not producer totals as expected values.

## Acceptance ledger — obligations only, no new PASS

| IDs | R3 acceptance to implement; later-stage distinction |
| --- | --- |
| A23 | Identical uninterrupted versus checkpoint/chunk/fold traversal with open exposure and late claims across boundaries; terminal forced close is censored/null target and cannot train earlier fold. R3 proves continuity/trace; exporter status serialization is later. |
| A26 | Full two-trajectory loss50/skip example changes next ticket80 eligibility; extend to delayed booking/refund, unsupported MARK and reservation changes. Validate timing and all later proposals, not just adjusted totals or deletion of old rows. |
| A34 | Reference100/fill101/exit110 gives exact gross9, no second slippage expense; check all four entry/exit long/short directions, fee-on-filled-only, partial/reversal sequencing. Actual execution path is required; ledger arithmetic alone was partial stage1 evidence. |
| A04/A07/A09-A14/A19/A20 | Atomic partial/reversal, snapshot-versus-booking ownership, late cumulative revision versus separate cash Posting, unknown/new-risk gating and conserved budget after booking. Both boundary sequences only as frozen scenarios. |
| A21/A24/A25/A29 | Complete scope/knowledge trace, gross-entry denominator with adds, unfilled selection retained and late finality unknown. Episode targets/validity are stage4; QD007 readiness alone is not target export. |
| A22/A28 | Retain information intervals for later strict end+24h<B and known+24h<B, including cross-asset overlap purge; equality fails. No preprocessing fit, exposed2026 period renamed unseen, or training approval inferred from trace completeness. |
| A27/A30-A33 | Native compatibility, declared MARK query freshness including exact-age boundary/+1us failure, fixed source mapping and multiplier/rule assumptions; missing historical-exact evidence remains unsupported, not fabricated by SCENARIO. |

## Verification, preservation and next action

Actual work: Git/status/ownership checks; frozen `git show` and current-code hash
comparisons; static function reads; old public fixture and the new MARK handoff
metadata hash check; calendar/cardinality and literal budget/slippage **manual
derivations** checked with stdlib integer/Fraction arithmetic. These are design
checks, not implemented replay tests, QR independent candidate PASS or a strategy
backtest. No application imports, new candidate row/point reads, raw MARK scan,
feature/signal/return/label computation, market query coverage, fitting or network
requests occurred.
No new tests/full regression are needed for this report-only change.

Only this new report is staged/committed after Markdown/diff checks. No QD008
frozen delivery, QD007 code/schema/test/candidate, QR file, native policy, shared
journal or main user/index work is edited. Final preservation fingerprint checks
are recorded before commit. Dependencies are the exact independent results and
typed scalable/state/projection/query/run contracts above. Stop after this report;
await allocation and bounded implementation/run dispatch. No automatic merger,
push, live engine, credentials/account access, Windows/NAS or scheduling action.

Final checks executed successfully: exact one-new-report scope, balanced Markdown,
whitespace, all five tracked QD008 deliverables identical to887d196 and both
published candidate manifest metadata hashes unchanged. No canonical candidate
payload rows were re-read or independently recertified. Main's seven fingerprints
match its frozen baseline: HEAD `cae0d2395adf2cd3905e41cb1c16748c8247c32c`, branch
main, staged diff SHA `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`,
index SHA `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`,
unstaged diff SHA `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d`,
full porcelain/untracked-files=all SHA
`2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649`,72 entries.
Report checks use stdlib/Git and are not application regression or market evidence.
