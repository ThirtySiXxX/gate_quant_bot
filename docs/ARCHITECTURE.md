# Architecture and initial repository audit

Audit date: 2026-10-27 (Australia/Melbourne). Source: current local working tree,
not just HEAD. Inspection and offline tests do not establish deployed service state.

## Git and documentation baseline

- Checkout: `/Users/lzh/Development/Project/gate_quant_bot`; branch `main` at
  `cae0d23`, matching locally recorded `origin/main`. No remote fetch was performed.
- Other local branch: `release/v1.0.0` at `27e0b7c`. Initially one worktree.
- The index already contained cleanup/config edits and deletions of the old hedge
  engine, flow/strategy modules and terminal dashboard. Many further core edits
  and new research, UI and test files were unstaged or untracked. Preserve both.
- No project/ancestor AGENTS.md was found in the inspected checkout ancestry.
  Ignored `agent.md` is a substantial local handoff; its latest corrections matter.
- Existing docs cover sizing, sizing comparisons, execution parity, universe
  selection and crypto ML. They remain intact. New workflow docs supplement them.
- `scripts/release.sh` exists locally but is excluded by `.git/info/exclude`;
  it is not a portable tracked deployment definition.

## Current module boundaries

```text
main.py -> ConfigStore / CredentialStore / StateStore
        -> Flask dashboard -> EngineController -> SystematicEngine
                                              -> GateExchange | PaperExchange
        -> BacktestController -> historical downloader -> portfolio backtest

data_fetcher -> OHLCV/funding CSV -> strategy_signals -> InstrumentSignal
trend/carry/vol/indicators ------->      | optional crypto_ml JSON inference
                                      v
portfolio allocation -> InstrumentTarget -> strategy_execution
execution_timing / position_sizing / risk -----------^
                                      -> adapter fills -> state/reporting

offline ml_training -> JSON bundle -> crypto_ml
walkforward -> frozen-parameter chronological folds / retrospective diagnostics
universe -> public contract discovery / candidate scoring -> explicit user apply
```

| Area | Existing implementation |
|---|---|
| Entry/UI/API | `main.py`, platform launch scripts, Flask `dashboard_web.py`, local JS/CSS. App startup creates local stores and starts an update-check thread; do not start it for an offline audit. |
| Configuration | YAML `ConfigStore`, dataclass defaults/builders, separate systematic/risk/cost settings. `config.example.yaml` defaults to PAPER. |
| Data | Gate SDK candles and settled funding, paging, history limits, incremental CSV cache, completed-bar filtering, internal-gap repair with failure if repair is incomplete. |
| Strategy | Multi-horizon 1h/4h EWMAC, daily regime, funding Carry, causal scaling, EWMA volatility/covariance, portfolio allocation, adaptive chop reduction and scoped execution timing. |
| Execution/risk | Shared decisions and order planning; Gate/paper adapters; fixed-margin tickets, cross-mode/leverage checks, costs/depth protection, partial fills and position ownership. |
| Backtest | Portfolio loop with prepared signal/covariance series, warmup boundary, recorded actions/costs/equity, schema-3 results, strict JSON and atomic result replacement; threaded controller. Web requests currently select one instrument; Python portfolio runner remains multi-instrument. |
| ML/research | 21 hourly features, gap-aware three-class labels; optional logistic/gradient-boosting training; JSON-only inference and entry gating. No deep-learning implementation found. ML path defaults empty. |
| Validation | Chronological fixed-parameter folds, parameter sweeps and retrospective trend diagnostics. Model retraining and purged fold training are not implemented by `run_walk_forward`. |
| Persistence | Mode-separated SQLite trade/equity/strategy state, ownership JSON, OHLCV/funding CSV, backtest JSON. Real credentials are local plaintext per README; never inspect/copy them for this workflow. |
| Operations | Logging, dashboard state and local updater. No tracked CI, dependency lock, container or NAS service definition found. Production monitoring is QD responsibility, not an already-complete monitoring platform. |

Runtime dependencies: gate-api, certifi, pandas, numpy, PyYAML, Flask,
python-dotenv and urllib3. Optional `requirements-research.txt` adds scikit-learn.
Ranges are broadly bounded rather than reproducibly locked. No dependency changes
or installations were made for this audit.

## Findings and integration risks

These are source observations, not newly reproduced production failures.

| Priority | Finding and evidence | Owner / acceptance direction |
|---|---|---|
| P1 | Cache CSV writes are direct/unlocked (`data_fetcher.py:104-109`), while multiple jobs can share a cache. | QD: atomic replacement plus per-key concurrency policy; race/recovery tests. |
| P1 | Core backtest skips preparation failures/insufficient assets (`backtest.py:273-284`). Controller rejects download failures, but direct calls can still change the effective universe. | QD, QR review: explicit requested/effective universe and fail policy; never silently compare different pools. |
| P1 | `EngineController.stop` reports stopped after timed join without confirming termination (`engine.py:89-97`). | QD: represent stopping/timeout accurately; blocked-thread regression. |
| P1 | Complete intrabar cross-margin liquidation, ADL, historical risk tiers and order-book fills are absent (`backtest.py:264-271`). | QD with QR assumptions: report limitations; risk simulation before survivability claims. |
| P2 | Job admission and insertion use separate lock sections (`backtest_runner.py:191-203`). | QD: atomic admission and concurrent-request test. |
| P2 | New PaperExchange resets cash/positions, while ledgers persist (`exchange_paper.py:23-35`, `engine.py:70-77`). | QD: define restart semantics before claiming durable paper-account continuity. |
| P2 | Walk-forward mode names do not select distinct training/window behavior (`walkforward.py:279-328`). No retraining occurs. | QD owns runner; QR defines validation semantics and acceptance tests. |
| P2 | Full experiment scripts/evidence live outside this repository (`crypto-ml.md:64-73`). Training helper enforces label-before-validity, not the stronger reported 24h embargo (`ml_training.py:11-14`). | QR: reproducible offline runner, manifest and embargo tests. |
| P2 | ML bundle lacks required dataset/code hashes, instrument scope and label/cost-policy identity (`crypto_ml.py:85-107`). | QR owns metadata; QD reviews artifact consumption; additive proposal required. |
| P2 | Arbitrary config patches are accepted by local API (`dashboard_web.py:2066-2071`); no route authentication observed. Default host is loopback. | QD: assess before any network exposure. No exposure/compromise was established here. |
| P2 | Current-universe snapshots are not a historical listed/delisted universe; volume field has source-dependent fallback units. | QD data provenance + QR point-in-time methodology. |
| P3 | Monolithic embedded UI, legacy config/model structures, unpinned environment, full-history memory loading, and missing CI/monitoring definitions. | QD incremental debt work; preserve current behavior. |

The latest local handoff and `crypto-ml.md` supersede earlier optimistic ETH
results after a 193-hour data gap was identified. This audit did not rerun the
historical experiments or endorse any profitability figure. Existing ML candidates
remain opt-in and have no demonstrated approval for activation.

## Verification boundary

The initial offline baseline passed 131 Python tests. Tests exercise synthetic,
mocked and temporary-file paths for accounting, ownership, sizing, closed-bar
causality, missing history, ML validity, execution parity and web JSON behavior.
See PROGRESS for final counts and new contract tests. No exchange API, credential,
live order, service restart, NAS deployment or real historical research rerun was
part of the audit. Documentation establishes ownership; it does not fix the debts
listed above or add production safety enforcement.

Concurrent setup output was retained during final coordination: a separate
`REPOSITORY_AUDIT.md` and standalone `src/contracts.py` with rejection tests.
INTERFACES marks its additive envelopes as a proposal without runtime adapters.
The native compatibility tests separately guard present producers/consumers.
