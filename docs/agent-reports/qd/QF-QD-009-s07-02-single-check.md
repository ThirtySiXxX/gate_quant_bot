# QF-QD-009-S07-02-SINGLE-CHECK

Date: 2026-10-28 Australia/Melbourne.
Dispatch: QF-DISPATCH-20261028-QD009-S0702-APPROVED-1.

**Result: BLOCKED — test not started.** The human-approved single attempt has not
been consumed. There was no probe, retry, source repair or additional test.
The dispatch explicitly requires stopping before execution if the existing
mechanism cannot ensure all three hard limits.

## Verified target and scope

- Clean worktree at inspection: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Branch: `codex/qd-cache-safety`.
- Exact candidate HEAD: `0cdbfbdaf047727d0ff4d20d5ee670891e49b070`.
- Only this new report is written/committed. No production/research/test/oracle,
  old evidence, ignore rule, main or shared-log file is changed.
- The requested evidence directory
  `research/.data/qd009/stream-repair-r1/approved-s07-02-once/` did not exist and
  was not created, because execution was blocked. No runtime evidence is invented.

## Code and oracle identity (static reads only)

| File | SHA256 |
| --- | --- |
| research/qd009/streaming_ledger.py | `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb` |
| tests/test_qd_streaming_ledger.py | `3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969` |
| research/qd007/event_ledger.py (pinned r3 oracle) | `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636` |
| tests/test_qd_event_ledger.py (oracle fixture helpers) | `aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8` |
| existing tmp/unit-runner.py | `1684175d8cfe9650959015692e4957bdf731b9e581d86160e808adcf05ccb116` |

`repair_many_live()` constructs128 opening Fills,128 funding snapshots,128
funding revisions,126 valuations, one oldest-lot reduction and one old fee
revision:512 synthetic records. All same-side lots use episode:live:0; declared
allocation quantum is0.000001. No fixture generation/import was executed here.

The existing S07.02 handler advances384 bodies through137, checkpoints/restores,
then advances128 bodies through264. Its intended assertions are:

-128 retained lots, oldest remaining quantity1;
-exact aggregate L1.38 and old partial slice entry fee cash-0.05;
-full small pinned-r3 comparison of balances, lots, slices, obligations/links and
 entries (the exact slice comparison also guards the single-slice requirement).

Every assertion above is **NOT_EXECUTED in this task**, not PASS. No conclusions
are inferred from the earlier5-body test or the earlier failed512-body attempt.

## Why the existing mechanism cannot satisfy this dispatch

The existing `tmp/unit-runner.py`, inspected as text without importing/running it:

1. Imports the test/module before calling `signal.alarm(55)`. This is55s and does
   not cover the entire process, while this task requires a whole-process10s cap.
2. Records `resource.getrusage(...).ru_maxrss` only after the test returns. It has
   no preemptive RSS enforcement for256MiB.
3. Configures its quota as128MiB minus old unit output, rather than this task's
   independent32MiB scope. It writes fixtures to old tmp/unit-dev and appends to
   old tmp/unit-runs.jsonl, violating this dispatch's exclusive new evidence path.
4. Has no independent parent final-receipt path if the process is killed by the
   signal or an RSS/output limit.

The old run-2 supervisor is not a suitable existing single-check launcher either:
it hardcodes eight benchmark attempts, a different code revision and old output
paths, with a59.8s timer and512MiB per-attempt output settings. It was only read;
it was not executed, copied, changed or used to start any child.

Additional static path check: `git check-ignore` does not ignore the requested
approved-s07-02-once path; `.gitignore:77:tmp/` covers the sibling tmp subtree only.
No ignore file was silently changed and no evidence was redirected into the old
folder. This is secondary to the missing enforceable limits.

Creating a new launcher, silently relaxing caps, changing the existing runner or
starting an exploratory run would exceed the instruction to reuse an existing
bounded mechanism and stop if it cannot ensure the limits. None was done.

## Execution and resource record

| Requested evidence | Actual result |
| --- | --- |
| Test processes started |0 |
| Test execution command |None; no executable test command was issued |
| Start/end timestamps |Not applicable: not started |
| Exit status/signal |Not applicable: no test process |
| Test wall/CPU/RSS measurements |Not applicable; no runtime result |
| New test output bytes |0; no runtime directory created |
| Retries/other tests/benchmarks |0 |
| Assertions |NOT_EXECUTED |

Static work was limited to Git status/HEAD, the directly relevant runner/fixture/
oracle code, five file identities and the requested path's ignore status. No
whole-repository/evidence hash scan, dependency install, engine/account access,
research revalidation, network, fit, integration/push or NAS/Windows action.

## Concrete prerequisite, not another research review

Provide or separately authorize the missing operational launcher: one S07.02 call
only, the specified new evidence root, a deadline measured before process launch,
enforceable256MiB RSS and pre-write32MiB accounting covering all child output plus
receipts, and a parent-owned final record on success/failure/cap termination.
The evidence directory's ignore treatment must also be resolved without changing
candidate/test/oracle bytes or using old output paths.

The existing approval for this one test remains recorded; no new financial
assumption or repeated research-conclusion review is requested. This report does
not authorize building that launcher or running the test as a follow-on action.
The coordinator can address the prerequisite within a separate explicit scope.
This task stops after committing this report. It establishes no90/118 acceptance,
32768 proof, native readiness or training permission.
