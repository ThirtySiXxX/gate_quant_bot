# QF-QD-009-STREAM-IMPLEMENT — candidate implementation and bounded evidence

Dispatch: QF-DISPATCH-20261028-QD009-STREAM-IMPLEMENT-1; steering
QF-CONTROL-20261028-QD009-SHARED-ACCOUNT-1. Date: 2026-10-28 Australia/Melbourne.

**Status: implementation candidate; formal acceptance pending. Do not integrate or
use as native replay infrastructure.** This report will be completed with the
single functional attempt and eight fixed benchmark results, including failures.
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

## Formal evidence

Pending: code/fixture/environment freeze, one producer functional attempt<=120s,
then N512/2048/8192/32768 twice each<=60s (eight total, no successful reruns).
Every failed/unexecuted case and actual resource limit will be retained. No formal
result currently exists. QR's independent120s suite is not executed here.

## Dependencies and next step

QR can inspect the exact implementation and saved evidence once published. A
single actual implementation acceptance must distinguish this generic candidate
from S13/native bridge and external raw/latest-eligible qualification. Missing
fixtures and contract gaps require implementation repair; they cannot be converted
into self-approved PASS or a claim of deployment/profitability. Keep this branch
isolated and do not merge into main.
