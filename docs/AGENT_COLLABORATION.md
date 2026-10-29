# QD / QR collaboration protocol

## Ownership and editing rights

QD owns architecture, data/backtest infrastructure, execution, risk, database,
APIs, deployment, performance and production monitoring. QR owns research,
statistics, alpha/factors, ML/deep learning, model validation, optimization and
experiments. No new model or production deployment is implied by these roles.

The following assigns one editor to each existing area. A reviewer may inspect
but must not edit the owner's file without an explicit recorded handoff.

| Exclusive editing owner | Files / areas | Required counterpart review |
|---|---|---|
| QD | `main.py`, launch scripts, `engine.py`, `systematic_engine.py`, exchange adapters, `data_fetcher.py`, `state.py`, `ownership.py`, credentials plumbing, dashboard/static assets, updater, storage/deployment/monitoring | QR for changed signal consumption, timestamps, costs or research assumptions |
| QD | `config.py`, `config.example.yaml`, `models.py`, `risk.py`, `position_sizing.py`, `costs.py`, `strategy_execution.py` | QR for config/defaults, shared structures, units, risk/strategy semantics |
| QD | `backtest.py`, `backtest_runner.py`, `backtest_reporting.py`, `walkforward.py`, `json_utils.py`, runtime dependencies | QR for input/results, fold semantics, accounting and validation methodology |
| QR | `trend.py`, `carry.py`, `vol.py`, `indicators.py`, `strategy_signals.py`, `execution_timing.py`, `portfolio.py`, `performance.py`, `crypto_ml.py`, `ml_training.py`, `universe.py`, optional research dependencies | QD for public functions/dataclasses, serialization, runtime costs/performance, persistence and integration |
| QD | `src/contracts.py`, `tests/test_interface_contracts.py`, `tests/test_shared_contracts.py`; existing tests except QR-owned tests below; future infrastructure tests | QR for contract-test or financial-semantic changes |
| QR | `tests/test_crypto_ml.py`, `tests/test_execution_timing.py`, `tests/test_universe.py`; new `tests/qr_*` and `research/` | QD for runtime contract or resource changes |
| QD integration editor | AGENTS and the seven workflow/audit docs; existing execution-parity/position-sizing docs | QR review of research/contract/decision entries |
| QR | Existing `crypto-ml.md`, `universe-model.md`, `sizing-comparison.md`; future research notes | QD review when claims concern runtime or risk |

Paths in the table are under `src/` unless otherwise specified. QR owns research
methodology for walk-forward; QD alone edits its current mixed infrastructure file.
QR owns candidate model semantics; requests for infrastructure changes inside
`universe.py` are assigned to QR or temporarily handed to QD. Splitting a mixed
file is a separate reviewed task. Shared semantic responsibility never grants
simultaneous editing permission. Any new unlisted shared file must be assigned
before edits; QD proposes the assignment and QR reviews it.

## Work claims and handoffs

1. Read the persistent context and inspect Git status. State role, branch,
   worktree, task ID, base commit, exact file allowlist, planned tests and dependency.
2. The user/integrator allocates disjoint claims before development begins. Record
   QD claims in `docs/agent-reports/qd/` and QR claims in `docs/agent-reports/qr/`,
   using unique task IDs. Worktree-local files are not visible to the other agent:
   publish the claim to the shared chat/review channel and get allocation confirmed.
   Do not assume a local lock file or Git worktree prevents concurrent edits.
3. Each role edits only its claimed files. If the task crosses ownership, ask the
   owner for a handoff or interface change, with a separate commit/review scope.
   Wait on dependent changes; continue work on disjoint files where possible.
4. At meaningful milestones, commit only your task's paths in your own worktree.
   Include a role-specific report with completed changes, files, exact tests and
   results, limitations, counterpart dependencies and recommended next steps.
5. QD is the default integration editor, not an automatic merger. QR reviews QD's
   shared changes; QD reviews QR's. User/integrator explicitly approves integration.
   No agent approves its own shared-contract change on behalf of the other role.
6. After approval, integrate exact commits in an integration worktree, run the
   relevant tests/full offline suite, and update shared PROGRESS/DECISIONS there.
   Never merge directly into the dirty source checkout. Push/release/deploy only
   when separately authorized. Keep worktrees/branches until retention is agreed.

Reports go to `docs/agent-reports/<role>/<task-id>.md`; interface requests go to
`docs/interface-requests/<role>-<task-id>.md`. Only the author edits their proposal;
review decisions belong in separate reviewer reports. QD consolidates journals
after integration, avoiding concurrent edits to central files.

## Interface change request template

```text
ID / author / contract owner / counterpart reviewer:
Base commit and current contract/native payload versions:
Problem and reason:
Requested fields/signatures/units/availability semantics:
Compatibility, schema version and migration/rollback:
Producer and consumer files (exclusive editors):
Acceptance criteria and positive/negative contract tests:
Independent work possible while blocked:
Review evidence and user integration approval:
State: proposed -> counterpart-reviewed -> user-approved -> implemented -> validated
```

No response is not approval. CR-001 (model/data provenance) and CR-002 (requested
versus effective backtest universe) are proposed roadmap items, not approved
runtime schema changes. Preserve existing feature version 1 and result schema 3.

## Starting from this dirty repository

**Do not simply branch from current HEAD:** it omits existing uncommitted modules.
The commands below are instructions for the user/integrator, not actions already
performed by this workflow task. They create a local snapshot commit using a
temporary Git index, preserving the source branch and its real index. They do
not push or merge. Pause all writers during the snapshot. Review all filenames
and diffs before committing; never include secrets, real config or account data.

Run these blocks in the **same zsh session** from the source checkout. The first
block prepares an isolated candidate index, not the repository's normal index.

```sh
cd /Users/lzh/Development/Project/gate_quant_bot
git status --short --branch
git worktree list
task_source_head=$(git rev-parse HEAD)
task_index_before=$(git diff --cached --binary | shasum -a 256)
task_snapshot_dir=$(mktemp -d /tmp/gate-agent-base.XXXXXX)
task_index="$task_snapshot_dir/index"
GIT_INDEX_FILE="$task_index" git read-tree "$task_source_head"
GIT_INDEX_FILE="$task_index" git add -A -- .
GIT_INDEX_FILE="$task_index" git diff --cached --name-status
GIT_INDEX_FILE="$task_index" git diff --cached --stat
GIT_INDEX_FILE="$task_index" git diff --cached --check
```

Inspect the complete candidate diff with
`GIT_INDEX_FILE="$task_index" git diff --cached` before the next block. This
captures the **visible working tree**, including existing unstaged/untracked
non-ignored source and deletions; it does not preserve the staging split inside
the new snapshot. The original staging split remains untouched. Ignored `agent.md`,
real config/data, venv, archives and excluded release scripts are not copied.
Review the local handoff at source when needed; do not copy its private paths
or ignored artifacts into tracked files indiscriminately.

After the user/integrator has reviewed and accepted the exact baseline, create
the local baseline and worktrees. Existing branch names/paths must be inspected
and reused appropriately or replaced with new names; never force/reset them.

```sh
task_tree=$(GIT_INDEX_FILE="$task_index" git write-tree)
task_base=$(printf '%s\n' 'Snapshot reviewed current source for QD/QR workflow' | git commit-tree "$task_tree" -p "$task_source_head")
git branch codex/workflow-baseline "$task_base"
test "$task_index_before" = "$(git diff --cached --binary | shasum -a 256)"
test "$task_source_head" = "$(git rev-parse HEAD)"
git worktree add -b codex/qd-data-safety ../gate_quant_bot-qd "$task_base"
git worktree add -b codex/qr-reproducible-research ../gate_quant_bot-qr "$task_base"
git worktree list
git status --short --branch
```

Stop on any command failure; do not continue with an unset/incorrect base. The
temporary candidate index may be retained for inspection. Git commit-tree needs
an existing configured author identity; do not change global identity to bypass
an error. Baseline review is essential because this snapshot incorporates the
user's prior work, not only workflow documentation. It is not a merge approval.

Each worktree must have independent ignored config, cache, database, result,
model and log paths. Never symlink/copy the original `data/`, real config, credentials
or venv into them. Environment setup is a separate explicit operation: QD installs
runtime requirements in its own venv; QR uses its own research venv. For immediate
offline checks, the existing interpreter can be reused read-only as below; imports
resolve from the current worktree. No app/engine launch is needed.

QD starting prompt (open a Codex chat with cwd `gate_quant_bot-qd`):

```text
Act as QD. Read AGENTS and all workflow docs. Confirm branch/base and obtain a
disjoint file claim for QD-001: cache atomicity/concurrency and job admission.
Audit those paths before edits. Preserve existing behavior and shared contracts;
propose any contract changes separately. Add focused offline race/recovery tests.
Commit only assigned changes on this branch. Report all seven required items.
Do not merge, use credentials, start trading, or change NAS services.
```

QR starting prompt (cwd `gate_quant_bot-qr`):

```text
Act as QR. Read AGENTS and all workflow docs. Confirm branch/base and obtain a
disjoint file claim for QR-001: reproducible offline experiments under research/
and tests/qr_*. Document dataset/feature/label/cost/split/seed provenance, enforce
the stated embargo in the experiment runner, and report negative results.
Propose CR-001 without changing runtime interfaces or activating models. Use
synthetic or explicitly approved public immutable data only. Commit only assigned
changes. Report all seven required items; no merge, trading or service operations.
```

## Offline verification and integration

From either worktree, this command uses the existing interpreter without installing
packages, blocks socket connections, and writes test artifacts only in fixtures'
temporary directories. The optional training dependency is not needed by the suite.

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*args, **kwargs):
    raise AssertionError('Network disabled during offline verification')
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
node tests/web_regressions.cjs
git diff --check
```

Socket patching guards accidental Python connections; it is not an OS network
sandbox for arbitrary subprocesses. Inspect new tests before running them. Do not
substitute launch scripts, `main.py`, update endpoints or release scripts for tests.

For approved integration, create a third worktree from the reviewed baseline:

```sh
cd /Users/lzh/Development/Project/gate_quant_bot
git worktree add -b codex/qd-qr-integration ../gate_quant_bot-integration codex/workflow-baseline
```

Review each role's `git log`/`git diff` against the baseline and integrate only
the exact approved commits there, in dependency order. Do not automatically merge
entire branches. Run contract/semantic tests and review the combined diff before
any separate decision about updating main. This source checkout remains dirty and
must not be switched/reset to make integration convenient.
