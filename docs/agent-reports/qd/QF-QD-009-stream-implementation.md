# QF-QD-009-STREAM-IMPLEMENT — candidate implementation and bounded evidence

Dispatch: QF-DISPATCH-20261028-QD009-STREAM-IMPLEMENT-1; steering
QF-CONTROL-20261028-QD009-SHARED-ACCOUNT-1. Date: 2026-10-28 Australia/Melbourne.

**Status: CANDIDATE_FAIL / NOT_READY_FOR_INTEGRATION. Implementation and the
bounded producer attempts are delivered; the requested contract milestone is NOT
complete. Do not integrate or use as native replay infrastructure.** One functional
attempt and exactly eight benchmark attempts were performed; there were no retries.
R05 does not have independent QR runtime acceptance. S13 remains
NOT_EXECUTED/BLOCKED_NATIVE_PORT/R3_NOT_READY.

## Scope and preservation

- QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
  `codex/qd-cache-safety`, base `6c606b60c33b191ef3dec8193bd6ad67acee96b9`.
- Only this report, `research/qd009/streaming_ledger.py` and
  `tests/test_qd_streaming_ledger.py` are edited. Frozen synthetic inputs and local
  attempt evidence go under ignored `research/.data/qd009/stream-implementation/tmp/`.
- Contract SHA256 `0db8014d162ec56f85eddafe289c869c8326f0ea5cbd226aef693050f259a745`;
  pinned r3 public arithmetic/parser source SHA256
  `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`.
  The old Ledger is never used by the runtime. Small test oracles alone use it.
- No main merge, push, dependency installation, app/engine, credentials/account
  data, model fit, new market acquisition, NAS or Windows operation.
- A context-selection mistake briefly returned to the already completed cache
  milestone. The old `481f87f` commit was independently reverified, its temporary
  worktree removed, and no cache source edited. Those results do not count toward
  this ledger's tests/budget. The unfinished ledger file was preserved and resumed.

## Implemented candidate

The module adds strict JSON and exact Fraction financial processing, single-writer
OS lease, SQLite-backed immutable Merkle treap nodes and bounded resident node
cache, incremental owner/dedup/FIFO/obligation/aggregate and reverse-link indexes,
immutable commit payload/manifest plus fsynced HEAD, persistent independent control
chain, saved request receipt replay, true-time historical views, disk-backed
restatement, bounded view-bound pages, checkpoints and journal recomputation on
restore. Transient nodes born in a transaction are pruned only when unreachable;
committed versions and ancient correction targets are retained.

Controlled synthetic ports have pinned source inventories and typed validators;
the controller constructs facts, live/order/financial/episode/peer selections,
executes all due slots, maintains order status from accepted fills, and journals
results with adapter state. File/network and entropy/wall-clock guards supplement
the trusted-code review boundary; they are not a hostile-code sandbox. The module
contains no native strategy adapter, allocation policy, actual order arbitration,
real execution model or model training.

R05 maps the QR execution-open and fifteen-Cell mark-selection DTOs, derives query
status before slots including non-tick queries, distinguishes consumer/source
clocks, preserves exact UNKNOWN reasons, selects the latest authoritative query
cohort, ages stored evidence at read time and selectively masks mark-dependent
reserves. New query recovery does not fabricate a newer source timestamp.

The account is one C/A/L/U/equity/budget across BTC and ETH. A development test uses
**one total initial 10000 USDT**, two assets' combined unrealized loss and reserves;
another controlled same-tick test reserves8000 for BTC, then ETH's8000 request sees
only2000 and remains unreserved. Checkpoint/restart retains shared state. This is a
synthetic port assertion, not implementation of the later native portfolio rule.
x10 risk budget and200 margin divisor are not applied as extra notional multipliers
by the generic ledger. Production strategy/risk/sizing defaults are untouched.

## Current development checks (not formal acceptance)

Eight focused synthetic development tests passed, covering literal r3 cash/FIFO,
shared account, request replay, partial-fill/cancelled remainder, controller state
restart, UNKNOWN and QG recovery. A subsequent separate16-body regression passed
for an ancient fee -> unknown -> restored -> refund with immutable historical view.
These are focused development checks, not the90/118 register, native acceptance,
full repository regression or benchmark attempts.

## Known gaps before formal execution

The fixed register in the test file retains all90 IDs and118 planned replicas.
Unconstructed full fixtures remain explicitly NOT_EXECUTED, including several
context/forged packet/peer-state, readiness/B1, many-live-lot, forged checkpoint and
interrupted resource-debit cases. No simple smoke test is substituted for them.
Frozen plans include constructor code/source templates; missing full fixture bytes
and expected tables are explicitly identified, so that freeze is not full fixture
registration acceptance.

Checkpoint currently inventories authoritative genesis/journal/control files and
recomputes finance from committed requests. It does not yet export every exact
separate typed projection/ownership/dedup/context/cursor file required by section7;
FactCursors/QueryCursor last times and exact old adapter-cursor checks are incomplete.
This prevents a claim of complete contract conformance even where small restart
checks pass. Public audit pages currently enumerate commits; failure evidence is
in the control chain but is not yet exposed as the required paged failure AuditRows.

Persistent resource accounting records active wall and logical file sizes, but is
not a complete conservative interrupted-work/cumulative physical-write debit. Not
all admission/large packet/exact-size paths have independent tests. Trusted ports
can retain prebound host aliases or globals beyond the instrumented guards; their
review and the missing negative fixtures remain necessary. Exact same-time forward
posting dependencies and some snapshot coverage restoration paths need full
registered fixtures. Any such gaps remain candidate failures, not waived limits.

## Frozen identity and actual evidence

Implementation commits: `d2cb09a9ecd1bbaad24caff67d31563d858e9b07`, followed
by fixture-construction fix `d8d4e1779a158a3b9cb92119c13a67fb157043ea`.
The latter is the **frozen code revision** for every measured attempt. This report's
later commit changes evidence only, not the frozen module/test bytes.

| Identity | SHA256 |
| --- | --- |
| streaming_ledger.py | `84902778a2e54873059a5f4974ae53f41f76c6fd0709fde2ad24c0f9593f4379` |
| test_qd_streaming_ledger.py | `7dddc7991c593c9df725b22e1b78086a83e20f3b7068024383dfa97e2708af9a` |
| freeze.json | `6fd6107e578bb2f74e19628206c7319ddb7e53b505981518840e232d1bf32042` |
| external eight-attempt supervisor.py | `0343668303fc632e99092570df24932166abaef984aee0b65fcf04c7376efbff` |

Actual evidence directory, relative to this worktree:
`research/.data/qd009/stream-implementation/tmp/run-2/` (ignored, intentionally
not committed). `freeze.json` pins Python/executable/platform/SQLite, source files,
synthetic schemas, fixed case plans and complete benchmark raw/fact bytes.
`functional/replicas.jsonl` is the durable record of completed checks;
`functional/terminated-result.json` summarizes it **without rerunning** anything.
`benchmark-summary.json` and eight `*.supervisor.json` records retain actual timing,
output, source identities, partial progress and final/orphan files.

The first source-freeze construction aborted before any ledger acceptance run
because a deliberately invalid Posting revision was accidentally fed into the
old helper while generating rule defaults. Its55 partial plan files remain in
`tmp/run-1/`. Fix d8d4e17 separates source/rule construction from negative request
admission. This was a pre-freeze construction failure, not a benchmark warmup or
an extra functional attempt. No formal source/test edits followed the successful
run-2 freeze.

### Single functional attempt: FAIL

- Candidate checks: **53 PASS /3 FAIL /34 NOT_EXECUTED** across90 case IDs.
- Replica outcomes:70 PASS /4 FAIL /44 NOT_EXECUTED across118 planned positions.
  Only **78 fresh fixture directories** were actually created; unconstructed
  positions are not counted as executed fixtures.115 replica records completed;
  the remaining positions are reconstructed as interrupted/not-started, not PASS.
- This is not a conforming full frozen90/118 acceptance suite: several plans freeze
  only constructor/source templates rather than complete requested fixture bytes
  and independent expected tables. PASS means the candidate's listed assertions
  executed, not independent QR acceptance or full-contract compliance.
- S01.06 replicas0/1 returned ELIGIBILITY_MISMATCH instead of the required
  LATE_ORIGIN_UNSUPPORTED. A group-wide late-fill/calendar preflight must precede
  snapshot eligibility application; no expected error was changed to bless it.
- S07.01 stopped RESOURCE_EXHAUSTED at /wall after3840 committed bodies, before
  checkpoint4096. Therefore **no >4096 completed-history proof exists**.
- S12.06 replica0 was interrupted; replica1 and S12.07 were not started.
- The harness checked aggregate output only between cases. At external termination
  actual output was **170461553 bytes**, exceeding the134217728-byte suite cap.
  This is an **enforcement failure**, not a successful bounded run. The original
  external-stop action name described intended pre-cap termination; the separate
  `external-stop-correction.json` records the observed violation. Failed evidence
  was retained. No additional functional run was started.
- Worker termination prevented a final monotonic suite/RSS summary. Completed
  replica timers sum65.021242s; filesystem birth-to-stop is approximately84.318s
  and is explicitly not a monotonic suite measurement. A sampled live RSS cannot
  substitute for exact peak RSS; that gate is unproved.

Executed targeted candidate checks include controlled partial/cancel state and
checkpoint continuation (S02.01-.03), resolution barrier failures and repeated
committed resolution (S08.02-.06), old checkpoint preserving independent semantic/
resource stops (S08.09), and R05 UNKNOWN/selective reserves/recovery/historical
immutability/backdated-delivery rejection (S10.08/.09). Missing full membership,
cursor, corruption and interrupted-debit tests remain unresolved.

| Group | Candidate PASS IDs (suffixes) | FAIL | NOT_EXECUTED |
| --- | --- | --- | --- |
| S01 | 01, 02, 04, 07, 08, 10, 11 | 06 | 03, 05, 09, 12 |
| S02 | 01, 02, 03 | — | 04, 05 |
| S03 | — | — | 01, 02, 03, 04, 05, 06, 07 |
| S04 | 06, 07 | — | 01, 02, 03, 04, 05, 08 |
| S05 | 01, 03, 05 | — | 02, 04 |
| S06 | 01, 02, 03, 04, 05, 06, 07 | — | — |
| S07 | — | 01 | 02, 03 |
| S08 | 01, 02, 03, 04, 05, 06, 07, 09 | — | 08, 10, 11 |
| S09 | 01, 02, 03, 04, 05 | — | 06, 07 |
| S10 | 01, 02, 04, 05, 07, 08, 09 | — | 03, 06 |
| S11 | 01, 02, 03, 04, 05, 06, 08 | — | 07, 09 |
| S12 | 01, 03, 04, 05 | 06 | 02, 07 |

S13 remains **NOT_EXECUTED/BLOCKED_NATIVE_PORT/R3_NOT_READY**, outside the90.

### Eight fixed benchmark attempts: overall FAIL

The four complete small runs passed their own literal financial/history checks.
The four large runs were externally terminated before60s, without a final child
receipt/result. Their “committed” counts come from reachable HEAD journals, never
from a partial request or orphan tail. No successful or failed run was repeated.

| N | Rep | Committed bodies | External wall s | Output bytes | Result |
| --- | --- | --- | --- | --- | --- |
| 512 | 1 | 512 | 4.653770 | 25340693 | complete, individual checks PASS |
| 512 | 2 | 512 | 4.507856 | 25340693 | complete, individual checks PASS |
| 2048 | 1 | 2048 | 26.954896 | 54771458 | complete, individual checks PASS |
| 2048 | 2 | 2048 | 27.354365 | 54771458 | complete, individual checks PASS |
| 8192 | 1 | 3584 | 59.823411 | 138841587 | FAIL: time guard, incomplete |
| 8192 | 2 | 3584 | 59.945121 | 161884747 | FAIL: time guard, incomplete |
| 32768 | 1 | 3328 | 59.977350 | 174905749 | FAIL: time guard, incomplete |
| 32768 | 2 | 3328 | 59.984690 | 183895589 | FAIL: time guard, incomplete |

Total benchmark external wall303.201459s (<480s), measured per-attempt output below
512MiB, total819751974 bytes (<2GiB). The external supervisor reduced its aggregate
allowance to account for the functional output overrun while preserving failure
artifacts. Producer formal plus benchmark wall stayed within600s on available
measurements, but this does not repair the functional output violation.

Do not select a favorable clock for growth: the frozen child `wall_us` measurements
are4.417032/4.318700s at512 and26.781471/27.117932s at2048. Both fail
T4N<=6*Tn+0.25: bounds26.752192/26.162200s, excess0.029279/0.955732s.
The separate external end-to-end timings remain in the table; they are not used
to hide this failure. Canonical journal bytes450021 ->1808485 satisfy the small
byte-growth bound2090630.5. Larger growth ratios and the completed32768-versus512
RSS gate remain NOT_PROVEN because those runs did not finish.

Complete runs' exact child peak RSS:56164352,56410112,57294848,52936704 bytes;
last node-cache charges about1.15MiB under the8MiB configured budget. Interrupted
runs have only externally sampled peak RSS (55.4–61.4MB), not exact child maxima.
Do not turn low RSS of incomplete histories into a completed large-run PASS.

At2048 bodies the candidate reports1675228 node visits/406003 node writes versus
320389/81980 at512. Persistent-node verification/serialization/write amplification
and repeated projection/checkpoint work are concrete optimization candidates;
these counters do not establish a profiler-attributed root cause. Do not remove
hash checks or retain lifetime records in RAM merely to pass the time gate.

| Frozen N | ReferenceFact file SHA256 |
| --- | --- |
| 512 | `f4dfaf0d665f7df308b625e1159018de1662b3300f0e558837da77446109acb5` |
| 2048 | `e36ec31e23381fca1cf52872b6f477387ae6817fbae9c36ec0cbff9fede46d41` |
| 8192 | `b40b9722ee553aa8fcd49c59d62e2087a2c742863e6532dc9e88173198ac1401` |
| 32768 | `3c1b3c36706f954442d544b0477eb3109b58c83d224cc7f950d2fba52c8a23d8` |

### Commands (historical, do not repeat against occupied evidence directories)

From this worktree, existing interpreter reused without installing dependencies:

```sh
QD009_CODE_COMMIT=d8d4e1779a158a3b9cb92119c13a67fb157043ea PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m tests.test_qd_streaming_ledger --freeze research/.data/qd009/stream-implementation/tmp/run-2
QD009_CODE_COMMIT=d8d4e1779a158a3b9cb92119c13a67fb157043ea PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m tests.test_qd_streaming_ledger --formal research/.data/qd009/stream-implementation/tmp/run-2
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python research/.data/qd009/stream-implementation/tmp/run-2/supervisor.py
```

The supervisor launches exactly four N values times two repetitions of
`--benchmark DIR N REP`, with no warmup/retry. Socket connections are blocked by
the test module. Formal command ended by SIGTERM, exit143; four benchmark children
returned0 and four returned-15. Whitespace/staging checks pass. No full repository
regression is substituted for the failed ledger register.

## QR010 binding and preservation verification

Read frozen QR010 commit `88168f34c8c2855e9e65510bcde749cc459ff12a`,
`research/qr010/shared-account-binding.md`, verified SHA256
`ed9971f0e47811acdbf54442be51828d26e1684a22c7681237d8cfd0d55aed95`.
The current generic formula first sums both assets' U, then applies min(sum(U),0);
it does not separately clip each asset's loss. A is excluded from spending, and
required UNKNOWN blocks account increases while consistent reductions remain
supported. No code/fixture/acceptance restart was made for this clarification.

The development fixture that serially reserves BTC before ETH only proves that
a shared balance cannot be spent twice. It is **not** the QR010 native allocation
rule and must not be promoted as a coin-priority implementation. QR010's single
joint2x2 allocation,6E group cap, atomic increase-basket admission, per-asset1m tier,
partial-capacity execution and asset episode finality/reentry are for the later
native binder. Generic ledger gaps above are distinct from that future work.

Main preservation rechecked after attempts: HEAD `cae0d2395adf2cd3905e41cb1c16748c8247c32c`,
staged-diff SHA256 `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`,
unstaged `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d`,
status `2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649`,
index bytes `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.
All match the pre-work fingerprints. Shared journals and other worktrees were not edited.

## Dependencies and next step

QR can inspect the exact committed implementation and saved evidence. Do not spend
its independent120s suite as if this were a ready candidate. A later actual
implementation acceptance must distinguish this generic candidate
from S13/native bridge and external raw/latest-eligible qualification. Missing
fixtures and contract gaps require implementation repair; they cannot be converted
into self-approved PASS or a claim of deployment/profitability. Keep this branch
isolated and do not merge into main.


Prioritized continuation, without silently consuming more formal attempts:
1. Fix late-origin preflight/error precedence and aggregate output enforcement.
2. Complete exact typed checkpoint/cursor/failure-audit and conservative resource
   accounting, plus the currently unconstructed registered fixture assertions.
3. Profile bounded-node storage/checkpoint overhead, then implement a measured
   optimization preserving canonical roots/financial semantics.
4. Obtain a newly frozen bounded continuation register before any replacement
   formal run. The initial one functional/eight benchmark allocation is consumed.
   This is an evidence/budget boundary, not a claim the engineering goal is done.
5. Only after generic gates pass, accept separately dispatched native/query bridge
   work against QR010. No market replay, fit, main merge or deployment is implied.

Evidence inventory: `tmp/run-2/evidence-files.json`, SHA256
`af16d35e15f2bc9c59a6f8eeb845c6027893fc764e211a12f4364836ca3f6380`,
records1939 files/1053335477 logical bytes including frozen synthetic inputs,
completed/failed stores and traces (before adding the inventory itself). It verifies
that all five frozen source/reference/contract files remain byte-identical. This
aggregate inventory is not a claim that the functional128MiB cap passed.
