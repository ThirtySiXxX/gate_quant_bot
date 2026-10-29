# Gate Quant Bot: agent instructions

Read `docs/ARCHITECTURE.md`, `docs/AGENT_COLLABORATION.md`,
`docs/INTERFACES.md`, `docs/ROADMAP.md`, `docs/PROGRESS.md`, and
`docs/DECISIONS.md` before work. Read any more-specific AGENTS.md too.
The ignored local `agent.md`, when present, contains useful historical evidence;
it is not a replacement for this tracked policy. Current user instructions prevail.

## Preserve the existing system

- Audit the actual checkout, branch, worktrees, staged/unstaged diff and untracked
  files before editing. Do not rebuild the application or revive deleted modules.
- Preserve user changes and the original staging boundary. Never reset, clean,
  stash, stage unrelated work, or remove archives without explicit authorization.
- This repository's working tree is substantially newer than its committed HEAD.
  Follow the reviewed snapshot procedure in AGENT_COLLABORATION before starting
  new development worktrees. A plain worktree from HEAD omits existing features.
- Do not copy, read, print or commit real credentials, `.env`, `config.yaml`,
  `data/credentials.json`, account data, or ignored local operational files.

## Roles and exclusive ownership

- **QD (Quantitative Developer)** owns architecture, data infrastructure,
  backtesting infrastructure, execution, risk controls, database, APIs, deployment,
  performance engineering and production monitoring.
- **QR (Quantitative Researcher)** owns quantitative research, financial statistics,
  alpha discovery, factor engineering, ML, deep learning, model validation,
  strategy optimization and experiments. Ownership does not imply deep learning
  is already implemented or that a model is approved for use.
- Use the file ownership table in AGENT_COLLABORATION. Mixed-purpose files have
  one designated editor. Do not edit another agent's files or the same file
  concurrently, even in different worktrees. Request and obtain a handoff first.
- Each developing agent uses its own feature branch and Git worktree. Read-only
  audit agents may inspect the source checkout without modifying it.
- Commit independently in the assigned worktree. No automatic merge, push,
  release, deployment or production change. Integration requires explicit review.

## Shared contracts

INTERFACES is authoritative for the eight shared boundaries and their versions.
Each contract has one owner, a reviewer and contract tests. Do not silently change
field names, units, availability times, defaults, feature order or result schemas.
Write a change request with rationale, compatibility, acceptance criteria and tests;
wait for owner/counterpart review and user integration approval. Continue unrelated
work while waiting. Test changes must not merely bless a breaking implementation.

## Safety and research validity

- PAPER is the default. Do not enable LIVE, submit real orders, use real-money
  credentials, or change deployed NAS services without explicit user authorization.
  This workflow request grants none of those permissions. Do not start/restart the
  existing trading application or engine as part of tests.
- Paper mode currently still asks for exchange credentials. Use mock exchanges
  and synthetic/approved immutable public data for automated offline work.
- Keep current risk/sizing defaults unchanged: daily-loss gating is intentionally
  disabled; fixed-margin sizing and optional ML behavior have explicit history.
  Changing any risk setting requires a reviewed change, not an incidental cleanup.
- Historical profitability does not establish future profitability. No full
  cross-margin liquidation/ADL simulation exists. Do not claim live/replay fills
  are identical or that a high-leverage account can survive based on these tests.
- Use closed, available-at-decision data, chronological validation, explicit
  warmup/label boundaries, costs, missing-data checks and point-in-time universes.
  Report failed experiments and selection bias. Do not activate candidate models.

## Checks and persistent reports

Run offline tests as documented in AGENT_COLLABORATION. Do not install/upgrade
dependencies or run launch/release/update scripts merely to audit the repository.
After meaningful changes report: completed changes, modified files, tests and
results, known limitations, dependencies on the other agent, and next steps.
Use role-specific reports; QD integrates PROGRESS and DECISIONS after review so
two agents do not edit shared journals simultaneously. Preserve existing docs.
