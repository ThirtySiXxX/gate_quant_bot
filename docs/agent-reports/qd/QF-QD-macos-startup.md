# QF-QD-MACOS-STARTUP: use the project's interpreter directly

Date: 2026-10-28 (Australia/Melbourne).
Dispatch: `QF-DISPATCH-20261027-QD-STARTUP-1`.
Status: implemented, tested and committed locally; awaiting coordinator review
and application of the exact single-commit patch. Stop after this bounded task.

## Claim and baseline

- Role: QD. Branch: `codex/qd-cache-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Parent: `f0f9eb072f331b5a2c029825c5fc7de9e33da4b8`.
- Exclusive files: `启动.command`, `tests/test_qd_macos_launcher.py`, this report.
- The coordinator assigned these infrastructure paths. No shared contract or
  QR-owned file requires modification, and shared journals remain untouched.
- Implementation commit: the single commit containing this report, obtainable
  with `git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-macos-startup.md`.
  Review that commit against its parent; do not integrate this whole branch,
  which also contains earlier isolated QD milestones and a user-source snapshot.

## Findings and changes completed

The old launcher sourced `venv/bin/activate` and then invoked bare `python` for
pip and `main.py`. Activation can contain an absolute path from before the
project moved. It can therefore prepend the wrong environment path and leave
`python` unavailable or select another interpreter. Separately, the launcher
required a global Python candidate even when a functional project venv existed.
The coordinator reported the concrete startup error `python: command not found`;
this task reproduced the failure classes using disposable fixtures.

- Resolve the interpreter as `"$PWD/venv/bin/python"` after entering the project
  directory and quote its invocations. Never source activation or run bare
  `python`/`pip` for dependencies or application startup.
- Search for a global creation interpreter only when `venv` does not exist.
  Existing directory entries, including broken symlinks, are retained and checked
  rather than silently recreated or replaced.
- Verify the project interpreter is executable and can execute a Python 3.10+
  version check regardless of `.deps_ok`. Unusable environments produce an
  explicit error naming the interpreter path and exit 1 without global fallback.
- Preserve the original first-run Python/Homebrew guidance, dependency marker,
  requirements installation and application arguments. The existing pip upgrade
  step on the missing-marker path is retained, not expanded. The displayed manual
  retry command also uses project-local Python so it avoids the activation defect.

No application, strategy, risk, model, account, cache or runtime dependency files
were changed. No installs/upgrades or environment repair/recreation were performed
on the user's actual environment.

## Tests and results

Before the fix, all **7 new test methods failed** (10 failure records including
subcases). After the fix, **7 methods passed** in 1.390 seconds. The suite copies
only the launcher into a disposable project whose path contains spaces, substitutes
fake shell-script interpreters and pip/main operations, and restricts PATH to
fixture commands. The real `main.py`, package manager and exchange are never run.

Coverage:

1. Ready moved environment, stale activation path, and no global Python commands.
2. Existing environment with `.deps_ok` absent: local pip install and local main.
3. Existing ready environment is preferred even when global candidates exist.
4. Runtime check failures with `.deps_ok` present/absent: no fallback, installation,
   deletion or recreation; original interpreter bytes and marker state preserved.
5. Missing interpreter in an existing environment: actionable failure, no bootstrap.
6. First-run creation through a fake global candidate, then local interpreter only.
7. Requirements-install failure: no ready marker and no application invocation.

Exact verification commands from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p test_qd_macos_launcher.py -v
/bin/bash -n 启动.command
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -c '
import socket, unittest
offline = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("offline test: network blocked"))
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover("tests"))
raise SystemExit(not result.wasSuccessful())
'
node tests/web_regressions.cjs
git diff --check
git diff --cached --check
```

- **185 full offline Python tests passed** in 9.172 seconds (prior 178 + 7 new).
  The ownership fixture's injected disk-failure log is expected.
- **8 frontend regression groups passed**.
- Syntax check passed under macOS `/bin/bash` 3.2.57. Whitespace checks passed;
  the launcher's executable file mode remains 100755. ShellCheck is unavailable
  and was not installed.
- Real source checkout remains on `main` at
  `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; index-entry SHA-256 remains
  `77931f7f4b2fc2bf8f354bb924b8f799d3d2ec76968d6141e754fabfdb6eedba`.
  Its launcher still hashes to `4aaec88a76bc932d444effb7bf01662e7913cdb2`,
  matching the initial index/source file. No source-checkout edits were made.

## Limits, dependencies and next step

This verifies shell dispatch and failure handling through fixtures, not actual
GUI/browser or trading-engine startup. Existing `.deps_ok` package-trust behavior
is retained: it does not detect later package removal. Real Python/Homebrew/pip
installation and Windows/NAS behavior were not exercised. No real configuration,
credentials, account data or ignored operational logs were read.

There is no QR semantic dependency. The coordinator should review/apply only this
exact commit's three-file patch before the user retries the macOS launcher.
The original checkout is intentionally still unmodified, so this report does not
claim its double-click launch is already repaired. No merge, cherry-pick, push,
engine start/stop, model activation or deployment occurred. Further backlog work
and recurring automation remain stopped.
