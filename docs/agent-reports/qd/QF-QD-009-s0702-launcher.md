# QF-QD-009-S0702-LAUNCHER

Date: 2026-10-28 Australia/Melbourne.
Dispatch: QF-DISPATCH-20261028-QD009-S0702-LAUNCHER-1.

**Delivery: a concrete, syntax-checked launcher candidate. Test remains BLOCKED
under the original hard-RSS condition. S07.02 processes started: 0. The original
single-test approval is not consumed.** No launcher entry point or child was run.

## Claim and preservation

- Role: QD; branch `codex/qd-cache-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Clean starting HEAD: `0f5f66ed55e67ce025e6943c67571c748155187e`.
- Exclusive new files: `research/qd009/s0702_launcher.py` and this report.
- No ledger, fixture, oracle, old runner/evidence, ignore rule, trading rule,
  main, shared journal, dependency or environment changes. No push/integration.
- Previous BLOCKED report remains intact. This report supersedes only its
  prohibition on preparing a new launcher, as authorized by this dispatch.

## Fixed identity and single-call behavior

The launcher checks the four pins below before launch and again inside the child
before importing the fixture. It does not require HEAD to equal the old candidate:
the launcher/report commits extend it without changing the pinned modules.

| Target | SHA256 |
| --- | --- |
| Candidate `research/qd009/streaming_ledger.py` | `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb` |
| Fixture `tests/test_qd_streaming_ledger.py` | `3c27be22b360f9813c7ff8cf5cdc4278db658f20d8aab669b872c04b4513c969` |
| r3 oracle `research/qd007/event_ledger.py` | `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636` |
| Oracle helpers `tests/test_qd_event_ledger.py` | `aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8` |

Financial candidate commit: `0cdbfbdaf047727d0ff4d20d5ee670891e49b070`.
The only child action is unchanged `run_case('S07.02', artifacts / 'case', 0)`:
the approved 128-lot, one-episode, 512-body checkpoint/restore/continue fixture,
including its existing L1.38, partial-slice and pinned-r3 assertions. No new
financial oracle, altered expectations, alternate cases or retry loop.

An exclusive `mkdir(exist_ok=False)` claims this fixed evidence root once:
`research/.data/qd009/stream-repair-r1/tmp/approved-s07-02-once/`.
The existing `.gitignore:77` `tmp/` rule covers it. It was not created this task.
No old unit output is read or appended. An existing run root is refused, including
one left by a launch failure; no automatic cleanup or second attempt is provided.

## Controls and exact limitations

**Default entry refuses before filesystem changes or child startup.** There is
no claimed hard-RSS implementation. The optional flag explicitly names the weaker
sampled control and requires a human decision before use.

1. **Time:** a parent monotonic deadline and independent watchdog begin before
   `Popen`, covering interpreter startup, imports and fixture work. At 10 seconds
   the parent sends SIGKILL to the child's new process group. Record actual wall
   time and overshoot; OS scheduling, process creation and signal delivery are
   not instantaneous. This is a supervisor deadline, not a real-time kernel
   guarantee that observed lifetime cannot exceed exactly 10.000 seconds.
2. **RSS candidate:** direct `proc_pidinfo(PROC_PIDTASKINFO)` readings target a
   10 ms interval, without launching repeated `ps` processes. Kill on a sampled
   value above 268435456 bytes or unavailable telemetry. Record sample count,
   maximum observed gap, sampled peak, and independent post-exit `wait4` peak/CPU.
   On Darwin `ru_maxrss` is bytes. A post-exit peak above the threshold produces
   CAP even if polling missed it. **Sampling cannot prevent an overshoot between
   samples, has no finite overshoot bound under scheduling delay, and does not
   certify a hard 256 MiB cap.** Parent memory is not part of child RSS; descendants
   are forbidden by a child audit hook (not an OS security sandbox).
3. **Output:** fixed disjoint reservations total 32 MiB: 31 MiB for fixture/ledger
   artifacts via the unchanged existing aggregate application/SQLite VFS pre-write
   budget; 512 KiB for merged stdout/stderr, capped by the parent before log writes;
   512 KiB for started/final receipts and the compact parent console summary,
   checked before writes. Budget exhaustion terminates/classifies the attempt;
   data is not deleted to disguise an overrun. This measures retained file bytes,
   not cumulative device traffic, directory metadata or allocated disk blocks.
   It relies on the pinned fixture's budget-aware paths; no kernel filesystem
   quota or general-purpose sandbox is claimed. Bytecode/core output is disabled;
   TMPDIR points inside the artifact allocation and child environment is minimal.
4. **Evidence:** parent `started.json`, `child-output.log`, and final `result.json`
   are separate from the artifact budget. Final receipt includes identities,
   launcher hash, interpreter, control mode, exit/signal, timings, measured RSS,
   CPU, output, original child result and PASS/FAIL/CAP. Missing/truncated child
   results cannot count as PASS. Parent attempts the final receipt after a child
   failure/kill; parent SIGKILL, host failure or failed storage cannot guarantee
   receipt persistence. Nothing in this task exercised those runtime paths.

Local SDK inspection found `RLIMIT_RSS` aliases `RLIMIT_AS` in
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sys/resource.h`.
The archived [Apple setrlimit manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setrlimit.2.html)
describes RSS handling as memory-pressure preference. Neither observation proves
an enforceable resident-memory ceiling for this interpreter. The launcher does
not call RSS/AS rlimits or describe virtual address space as physical RSS. No
container, dependency or privileged mechanism was installed.

## One precise decision for the user

Accept or reject **only the replacement of a hard RSS cap with 10 ms target
sampling, SIGKILL on sampled RSS >256 MiB, and post-exit peak disclosure/CAP** for
this single S07.02 attempt. This explicitly accepts possible transient RSS
overshoot; it does not increase the numeric threshold, extend the deadline,
increase output, authorize retries or add research tests. The supervisor timing
limitations above also remain disclosed. If strict never-exceed limits remain
required, do not execute this local candidate; a separately authorized enforceable
environment would be necessary. No such environment is proposed/installed here.

## Exact future commands (not executed)

Use the existing read-only interpreter, in this worktree. Default refusal:

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -I -B research/qd009/s0702_launcher.py
```

Expected from static inspection: compact BLOCKED message, exit 2, zero test
processes, no evidence directory. This behavior was not self-tested.

Only after explicit human acceptance of the sampled alternative, run once:

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -I -B research/qd009/s0702_launcher.py --run-once-with-sampled-rss
```

The flag is an explicit operator acknowledgement, not a technical proof of
authorization. The previous single-test approval alone does not permit its use.
No command for another case, benchmark, full suite or retry is supplied.

## Checks and handoff

Only one Python syntax/static check is authorized/performed: parse and compile
the new outer script AST and its literal CHILD string without executing either.
No imports of the launcher/fixture/candidate, help/default invocation, runtime
probe, self-test, S07.02, other test, benchmark, replay or fit. Static Git checks
verify the two-file scope and unchanged pins. Check results are recorded below.

- Static AST/compile: **PASS**, once, exit 0. The single check used the existing
  interpreter with `-I -B`, `ast.parse`/`compile` on the outer script and literal
  child, and `ast.literal_eval` on PINS to compare the four source hashes. Neither
  compiled code object was executed. Launcher SHA256:
  `ea508282c10cf788357940a2f7039e81a2f10becb2ad1ee915c377bca0fe58ed`.
- Git whitespace/scope: `git diff --check` passed; status contained only these
  two new files. Staged whitespace/scope is checked again before committing.
- Runtime results/resources: N/A; test processes 0, retries 0, runtime output 0.
- Working functionality and trading rules: unchanged; no runtime claim added.
- QR dependency: none; no financial-contract edits or new review requested.
- Next step belongs to coordinator/user: review these exact two files and decide
  the sampled-RSS alternative. This delivery is not execution/integration approval.
  Stop after committing this tool and report; leave shared journals untouched.

Exact syntax/static command executed once (not a launcher/test invocation):

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -I -B - <<'PY'
import ast
import hashlib
from pathlib import Path
source_path = Path('research/qd009/s0702_launcher.py')
source = source_path.read_text()
tree = ast.parse(source, filename=str(source_path))
compile(tree, str(source_path), 'exec')
child = next(node.value.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'CHILD' for target in node.targets))
compile(ast.parse(child, filename='<S07.02 child literal>'), '<S07.02 child literal>', 'exec')
pins_node = next(node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'PINS' for target in node.targets))
pins = ast.literal_eval(pins_node)
for name, expected in pins.items():
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('PIN MISMATCH: ' + name)
print('PASS: outer and child AST/compile; no code executed; all four pins unchanged')
print('launcher_sha256=' + hashlib.sha256(source_path.read_bytes()).hexdigest())
PY
```
