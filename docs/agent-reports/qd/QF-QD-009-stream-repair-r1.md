# QF-QD-009-STREAM-REPAIR-1

2026-10-28 Australia/Melbourne. **REPAIR_CANDIDATE / WAIT_USER_VALIDATION**.
Not READY_FOR_QR_IMPLEMENTATION_ACCEPTANCE; no claim of generic-contract completion.
Base b0c19da5f9fda7d2c0dc8a9ae61bd6dd346c038a; branch codex/qd-cache-safety;
worktree /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot.
Exclusive edits: research/qd009/streaming_ledger.py,
tests/test_qd_streaming_ledger.py, this report. Old implementation evidence,
contract/reference/QR files and main are preserved.

## Registered development diagnostics (before execution)

Maximum six distinct profiling tasks, each<=60s, aggregate<=360s, RSS256MiB,
aggregate diagnostic output<=256MiB. Do not repeat unchanged tasks. Each task has
an exclusive artifact directory and source identity; unused tasks stay unused.

| ID | Fixed workload / hypothesis / decision |
| --- | --- |
| P01 | Original candidate256 bodies, one256-body commit, cProfile+node counters. H1: repeated canonical serialization, deep resident-size accounting and persistent intermediate path writes dominate. Establish actual cumulative/self-time attribution before optimizing. Max32MiB output. |
| P02 | Isolated original canonical treap1024 deterministic key updates,256 live keys, four version roots. H2: per-update path reserialization/write amplification, rather than financial arithmetic, explains scaling. Compare measured index-only profile to P01, no same workload retry. Max16MiB. |
| P03 | Changed candidate256-body commit under the same semantics, profile+counters after a concrete optimization chosen from P01/P02. Test whether measured hotspot/write amplification actually falls. Max32MiB. |
| P04 | Changed candidate8192 bodies,256-body transactions; fixed original tape, actual old view/correction. H3: batching verified nodes meets bounded-history cost without retaining lifetime records. Max96MiB. |
| P05 | Cold journal/checkpoint restore of2048 bodies, source/index verification and forged projection negative. H4: one cold reconstruction is bounded and exact; identify repeated startup/checkpoint work. Max48MiB. |
| P06 | Changed controller16 fixed ticks plus checkpoint, query UNKNOWN/recovery and bounded failure-audit paging. H5: typed cursor/inventory/controller work is bounded independently of reference-mode speed. Max32MiB. |

Ordinary small repair tests: cumulative active CPU<=300s, each wall<=60s,
output<=128MiB. Record each actual change, command, failure and resource use.
All new development/formal output<=3GiB, all measured runtime<=1800s.
The initial repair dispatch proposed one120s functional suite/eight60s benchmarks
after complete fixtures and guards. **That automatic permission was superseded**
by QF-CONTROL-20261028-QD009-USER-VALIDATION-GATE-1. No such run was started.
Any complete validation or research-conclusion revalidation now needs direct human
approval. The repair CLI blocks --freeze/--formal/--benchmark and requires an
explicitly selected development test. S13 remains unallocated.

## Progress

State verified clean at the exact base. Existing ignore rule covers the new tmp
artifact root. No new formal attempt has started. Profiling and implementation
results will be appended here with exact identities, resources and limitations.


## Human validation gate and preservation

The coordinator relayed the latest direct human instruction:
“不要一直做我么已经有的结论的验证，如果要验证我们研究得到的结论的话要经过我的验证，不然这样太浪费时间成本和金钱成本了”.
This overrides the earlier automatic acceptance allocation. P05/P06, all new formal
90/118 runs, all eight new expansion benchmarks, complete regressions, research
rechecks and market replay were not started. A small512-body development fixture
already running at the restriction finished with a fixture error; it was corrected
without rerunning that512-body case. Only directly changed code's small regression
checks followed. No message was sent to QR and no automatic QR acceptance was requested.

Old code/reference/contract/QR files, the original implementation report and its
run-1/run-2 evidence were not edited. No main integration/push, dependency install,
model/scaler fitting, app/engine, account/credentials, market acquisition or
NAS/Windows work. Only the assigned two source/test files and this report change.
QR010's one10000-USDT account and aggregate min(sum(U),0) rule are retained;
no native allocation/basket or trading-rule change was introduced.

## Concrete changes

1. **Admission ordering:** perform the frozen-calendar late-fill preflight before
   applying any same-delivery snapshot. The two previously failing S01.06 orderings
   now reject LATE_ORIGIN_UNSUPPORTED and leave the committed prefix unchanged.
2. **Index work amplification:** unique copy-on-write nodes coalesce repeated
   updates inside the transaction. Public/slot snapshots freeze their exact
   canonical Merkle roots; committed versions are immutable. Empty roots are
   memoized, priorities recomputed from the same domain/key, and private SQLite
   hashes stored as32-byte values with bounded zlib payload decoding. Raw-value
   and canonical-node hash verification remain. FIFO iteration freezes its active
   index root before mutating that tree. This does not retain lifetime records in RAM.
3. **Pre-write storage guard:** quota reservations precede canonical output writes,
   SQLite xWrite/xTruncate and SIZE_HINT extension. Optional chunk preallocation
   cannot bypass the guard. The VFS delegates locking/sync/other I/O; the cache uses
   rollback-journal DELETE with synchronous=EXTRA. A reserved emergency allowance
   supports guard/failure/stop receipts within the same quota. The append-only
   resource book preserves conservative byte grants on reopen. VFS exceptions are
   transported back to guarded Python code rather than ignored at the C boundary.
4. **Typed checkpoint exports:** immutable component/version segments include
   config/catalogue/facts, context, journal/envelopes, registry, public projection,
   ownership, dedup, revisions, calendar, adapter/order/decision/query/reserve state
   and cursors. Previously acknowledged segments are reused without rewriting
   whole snapshots. Restore first verifies declared files, recomputes committed
   journals/projections, compares exact inventory and cursor membership and keeps
   independent CONTROL latches. Rehashed removed ownership rows and stale adapter
   cursors are rejected by the executed narrow tests.
5. **Failure and uncertainty handling:** durable bounded audit pagination includes
   failure AuditRows; input-witness field/membership mismatches are distinguished
   from different adapter results. Saved guarded inputs are hash/identity checked
   and unvalidated admissions rechecked before resolution. Semantic-stop publication
   failure stays blocked across reopen and resolves to the original integrity stop.
   Existing immutable control/journal/manifest/audit files are never overwritten
   to hide tails. A verified validated companion with a failed CONTROL pointer is
   retained and adopted as control proof; an orphan financial journal is not imported.
6. **Dedup provenance:** corroborating sources update a retained Merkle reference
   root while preserving the first commit, one financial event and old views.
7. **Test infrastructure:** additional concrete financial/context/negative fixture
   constructors and named repair tests were added. This is incomplete fixture
   construction, not a claim that the original90/118 register is ready or passed.
   Ordinary test output now stays in the allocated repair tree and failures remain.

## Measured diagnostics, before the scope restriction

| Task | Wall s | CPU s | Peak RSS bytes | Outcome |
| --- | --- | --- | --- | --- |
| P01 | 4.066959 | 3.982005 | 55918592 | diagnostic completed |
| P02 | 0.613567 | 0.585789 | 43270144 | diagnostic completed |
| P03 | 1.146783 | 1.132581 | 55099392 | diagnostic completed |
| P04 | 3.362380 | 3.307661 | 57540608 | FAIL: progress logger used float in strict canonical JSON; stopped after256 |

P01 attributes3.315s cumulative to set,2.906s to put and0.963s to recursive
resident-size measurement on256 bodies;35572 persisted node writes. P02 reproduces
serialization/path-write amplification in an independent index-only workload.
P03's changed256-body workload measured1.146783s versus4.066959s, with4821 writes;
its economic root matched P01. It is an intermediate implementation measurement,
not a performance claim about the final code after checkpoint/quota additions.
P03's original node-visit counter excluded mutable-node visits; that instrumentation
was corrected afterward and must not be compared directly with P01's visit count.

P04 did NOT complete8192 and is not a successful large-run proof. It stopped at256
on a diagnostic progress-logging bug (floating seconds passed to the money/strict
JSON serializer), recorded NONCANONICAL_INPUT, and was not retried. Its exact trace
is retained. P05/P06 remain unused under the human gate. No extra performance search.

## Necessary development checks and failures

All commands ran with PYTHONDONTWRITEBYTECODE=1 using the existing read-only
`/Users/lzh/Development/Project/gate_quant_bot/venv/bin/python` interpreter.
The narrow runner is `research/.data/qd009/stream-repair-r1/tmp/unit-runner.py`;
its per-command timing/CPU/RSS/results are in `unit-runs.jsonl`.

| Changed behavior / selected check | Observed development result |
| --- | --- |
| Ancient fee unknown/restored/refund after index/checkpoint changes | passed selected16-body checks |
| Independent entry/exit/both-unknown fee sides | S01.12 narrow58-body construction passed before the human gate |
| Reversal fee split and readiness invalidation/successor | selected S01.05/S01.09 checks passed before the gate |
| Original-clock context initialization | selected S03.03 check passed before the gate |
| Rehashed removed ownership row / stale adapter cursor / failure page | targeted checkpoint tests passed |
| SQLite quota and durable stop reopen | initially failed because cold source/audit cache validation rewrote data; changed to verified read-only reuse, selected quota test then passed |
| 128 lots/128 claims setup | initially failed: fixture incorrectly gave each same-side lot a separate episode; source constructor corrected to one episode,512-body test NOT rerun |
| Two same-side lots, exact snapshot and full FIFO close | new5-body targeted test passed after the correction |
| Late origin vs snapshot eligibility | two previously failing orderings passed in RepairAdmissionTests |
| SQLite SIZE_HINT before physical allocation | target larger than quota returned SQLITE_FULL before file length changed |
| Unpublished integrity stop after reopening | RepairGuardTests passed: original input is revalidated, no commit, INTEGRITY_STOPPED retained |
| Omitted live-range witness | rejected INPUT_BINDING_MISMATCH without changing prefix |
| Native VFS callback I/O failure | propagated COMMIT_OUTCOME_UNKNOWN with the durable guard retained |
| New corroborating source | audit root changed; no repeated fill; old view and first commit retained through checkpoint |
| Validated control row with failed pointer | preserved exact companion bytes, returned not_committed, retained orphan financial data |

An early audit-directory/pointer name collision on case-insensitive macOS caused
one small test failure; it was fixed by using audit-rows/ versus AUDIT. These early
inherited TemporaryDirectory tests used automatic cleanup before the runner was
changed: that failure's directory was not retained (trace remains in the tool
transcript). This is a recorded evidence-retention deviation, not a reconstructed
PASS. Subsequent failure directories and logs are retained under this task's tmp.
Seven early small commands lack process CPU/RSS instrumentation; conservatively
bill an additional7 CPU-seconds rather than report invented exact measurements.

The checks above occurred at successive development revisions. They are not one
all-pass suite against the final code, independent QR acceptance or financial
research validation. No already accepted research result was rerun after the gate.

## Actual resource use

- Four diagnostic tasks: wall9.189690s, CPU9.008036s.
- 14 instrumented narrow commands: 12 command PASS /2 command FAIL, wall3.327663s, CPU3.082397s; failures are retained. These are command counts, not90-case results.
- Including7s for early commands and14s of startup allowance (1s per instrumented command), ordinary test CPU<=24.082397s (<300s). Measured narrow-command max RSS82690048 bytes; early uninstrumented peaks are unknown.
- Retained new task files at accounting time: 58743763 bytes, excluding subsequently written report/summary metadata and early automatically cleaned temp files; no whole old-evidence hash sweep was performed.
- New formal suites: **0**. New expansion benchmark attempts: **0**. Existing
  original failed1+8 evidence is unchanged. No new formal90/118 outcomes exist.
- The resource book counts application/VFS write requests and allocation debits,
  including DB/rollback-journal overwrites and orphan/temp output. Reopened grants
  are conservative upper debits, not measurements of storage-device amplification.
  No claim of exact hardware/block-device write totals is made.

## Remaining implementation and proof gaps

The candidate is not a complete generic-ledger implementation or an accepted
repair milestone. The90 named cases/118 positions remain **NOT_EXECUTED for this
new candidate**, with development subchecks listed separately. Several full source/
expected-table constructions are still missing; the historical constructor-template
freeze is not sufficient. Do not run the old full harness to manufacture coverage.

Pre-write file/SQLite guarding is concretely improved, but large packet allocation,
complete external RSS/monotonic-wall supervision and a reliable final receipt under
process termination are not yet proved/finished. Cumulative byte grants survive
reopen; a full conservative interrupted-active-wall debit remains incomplete.
Control-tail variants, count/cache corruption, all Fact/QueryCursor permutations,
single-tick resource extremes and complete failure/restore cases still need their
allocated implementations and targeted evidence. No32768 completion or>4096
continued-history proof exists. The new ctypes VFS/SQLite ABI path was exercised
only on this macOS host; other target environments are untested. No hardware/NFS/
SMB/power-loss guarantee follows from these tests.

S13/native/query bridge, QR010 joint allocation/atomic baskets and real data replay
remain separate future work. This candidate does not set training permission or
establish profitability/survivability. Source metadata and actual trading/risk
rules/defaults remain unchanged.

## Specific next validation question (requires human approval)

Do **not** restart all validation. The smallest useful next question is whether the
corrected one-episode128-lot fixture survives its existing512-record checkpoint
continuation and yields128 retained lots, one old partial slice and L1.38 exactly.
The executed5-body test cannot prove128-claim allocation/residual and cache behavior.

Proposed scope: exactly one corrected S07.02 run, no retries, no new data, with its
small pinned r3 oracle; expected a few seconds, hard wall10s /RSS256MiB /output32MiB,
within the remaining development allowance. Stop at first discrepancy or cap,
retain failure evidence and report; do not expand to8192/32768 or another research
conclusion automatically. Full90/118, expansion ladder and QR independent acceptance
stay pending separate human approval and completion of the missing code/fixtures.

## Delivery identities

- `research/qd009/streaming_ledger.py` SHA256 `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb`.
- `tests/test_qd_streaming_ledger.py` SHA256 `3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969`.
- Base: b0c19da5f9fda7d2c0dc8a9ae61bd6dd346c038a. Result: the commit containing
  this report (resolve `git log -1 --format=%H -- docs/agent-reports/qd/QF-QD-009-stream-repair-r1.md`).
- Working/staged whitespace checks and Python AST parsing are static checks only.
  No main merge, push, full regression or automatic acceptance is implied.


Accounting clarification: per-script timers start after Python imports. In addition
to measured body CPU, the ledger conservatively reserves1s startup per instrumented
unit command and1s per diagnostic (14+4 seconds). These are explicit upper debits,
not fabricated exact import measurements. With the7s early-command allowance,
ordinary CPU debit<=24.082397s, diagnostic CPU debit<=13.008036s; all remain well
inside the dispatched limits. No further tests were run for this clarification.
