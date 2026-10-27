# Initial repository audit

Date: 2026-10-27, Australia/Melbourne. Inspection of current files, not only HEAD.
No private configuration, credentials, account records or historical data were
opened. No service, engine, training, network download or order was started.

## Git and repository state

- Root: `/Users/lzh/Development/Project/gate_quant_bot`.
- `main` and locally recorded `origin/main`: `cae0d23`. No fetch was performed;
  this says nothing about a newer remote state. Other local branch:
  `release/v1.0.0` at `27e0b7c`. One worktree at audit start.
- 11 staged paths, 18 unstaged paths (some overlap), plus untracked research,
  execution, UI, tests and five existing docs. Five legacy modules are staged
  for deletion: dashboard_terminal, engine_legacy_hedge, flow, hedge, strategy.
  Preserve those deletions and local archives rather than restoring old modules.
- No standard AGENTS.md found at root, within nonignored source, or checked
  ancestor directories. Ignored lowercase `agent.md` contains substantial useful
  historical decisions; it remains untouched. New AGENTS.md is shared policy.
- A worktree created from HEAD today would omit most recent local functionality.
  Curate and review the existing changes into a common baseline before parallel
  writes. Setup does not silently commit or stage them.

## Existing functionality and verification

See [architecture](ARCHITECTURE.md) for the module map. The project already has
multi-asset systematic strategies, history download/cache/gap repair, manual
universe scans, paper and real execution adapters, margin/fee/budget checks,
ownership reconciliation, persistent state, portfolio replay and a Flask UI.
Shared signal/order policy and parity tests are useful existing integration
boundaries; preserve them.

Current baseline checks performed in this audit:

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests -q
node tests/web_regressions.cjs
```

131 Python tests passed; 8 frontend regression groups passed. The intentional
ownership disk-failure fixture emits a log while passing. Tests cover order
invariants, entry tickets, exits, execution parity, ML inference/causality,
history gaps, report accounting, ownership and Flask/JS interactions. They are
offline functional checks, not a live fill, liquidation or strategy-profit test.
The installed runtime imports numpy, pandas, Flask, YAML and Gate SDK.

## Findings and integration risks

| Priority | Evidence | Finding / required follow-up | Owner |
| --- | --- | --- | --- |
| P0 before parallel writes | Git status/index | Extensive user WIP is absent from HEAD; curated baseline and separate worktrees required | QD + user review |
| P1 before broader execution | `strategy_execution.build_order_plan`, `position_sizing.entry_ticket`, sizing-comparison.md | Volatility-sizing open/add path does not use fixed-ticket-equivalent fresh margin/tier checks; audit before promotion | QD |
| P1 before live claims | `backtest.py` module/initial warnings, position-sizing.md | No full intrabar cross-margin liquidation, historical tier/ADL, book queues or partial-fill simulation | QD; QR evaluates impact |
| P1 before remote exposure | `dashboard_web.create_app`, engine/manual/config/update routes | No application authentication/CSRF mechanism found; localhost default is significant. Authorization is not enforced by this new documentation at runtime | QD |
| P1 before reproducible promotion | `crypto_ml.load_bundle`, `prepare_predictions`; `ml_training.fit_export` | Legacy model/prediction formats lack artifact identity, full provenance, instrument scope and transport schema; v1 contract is additive, not yet adopted | QR + QD |
| P1 for validation claims | `walkforward.run_walk_forward`, `_slice_inputs` | `mode` is reported but does not branch into different rolling/expanding warmup behavior; fixed-parameter folds are not an ML refit protocol | QD infrastructure + QR protocol |
| P1 for ML validation | `ml_training.fit_export`, crypto-ml.md | Exporter only enforces label end before valid_from; common asset folds/24h embargo and experiments reside in external scripts. No fit_export test in repo | QR |
| P1 for input integrity | `data_fetcher._repair_candle_gaps`, `backtest.run_portfolio_backtest` | Downloader repairs/fails internal gaps; direct replay may warn and skip insufficient symbols. Need strict requested/accepted coverage policy at adapter boundary | QD |
| P2 | `ConfigStore._write_to_disk`, `data_fetcher._save_cache` | Direct YAML/CSV writes and process-local locks; multiple writers can race. Isolate paths now, assess atomicity/locking separately | QD |
| P2 | `EngineController.stop` | 15s join timeout still sets stopped flag without checking worker termination; lifecycle follow-up needs a blocking-worker test | QD |
| P2 | requirements files, repository file inventory | Broad dependency ranges, no lockfile/CI; export parity currently checks training rows rather than independent holdout | QD runtime; QR exporter |
| P2 | `models.Signal`, `portfolio.InstrumentSignal/InstrumentTarget` | Legacy types lack availability/version context and contain historical conventions; adapt explicitly, do not rename in place | QD contract transport; QR semantics |

Historical research reports document a 193-hour ETH gap and corrected return
conclusions, plus first-round ML candidates without demonstrated trading benefit.
Those numerical experiments were not rerun here; see [crypto-ml.md](crypto-ml.md)
and [sizing-comparison.md](sizing-comparison.md). No historical return is used as
an activation criterion by itself. No blanket code rewrite is warranted.

## Scope of this setup

Added shared instructions, persistent collaboration documents, standalone v1
contract validation and offline contract tests. Existing source, tests, docs,
index, defaults and local handoff were preserved. No runtime adapter migration,
Git commit, branch/worktree creation, integration merge, live activation, or NAS
change was performed. See PROGRESS.md for final checks and ROADMAP.md for work.
