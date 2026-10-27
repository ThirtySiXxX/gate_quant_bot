# QR-001 result: retain tooling, do not promote the model

Experiment `qr001-temperature-calibration-v1`, completed 2026-10-27.
The preregistered probability-quality criterion passed on this retrospective
sample. The trading criterion failed: the primary .45 gate made no entries.
There is no validated trading candidate for paper activation from this study.

Protocol was committed in `36ce77a`, implementation in `0ab04c2`, and the UTC-day
measurement correction in `854e1b6`. No model specification or threshold was
chosen after looking at outcomes. The correction is disclosed below. All source
runtime, risk settings and shared interfaces remain unchanged.

## Baselines and evaluation

The allowlist selected 46,891 public hourly bars across BTC, ETH, SOL, DOGE and
ZEC; unchanged feature/target logic produced 46,026 samples. Evaluation contains
10,735 asset-hours across three chronological folds and 91 distinct UTC days.
These are correlated observations, not 10,735 independent trials. All historical
periods were previously inspected in the project; no untouched final test exists.

| Fold | Evaluation start UTC | Evaluation end UTC, exclusive | Legacy / matched fit rows | Evaluation rows | Temperature |
|---|---|---|---:|---:|---:|
| 1 | 2026-07-29 10:00 | 2026-08-28 10:00 | 35,111 / 31,511 | 3,580 | 0.980770 |
| 2 | 2026-08-28 10:00 | 2026-09-27 10:00 | 38,711 / 35,111 | 3,580 | 0.896117 |
| 3 | 2026-09-27 10:00 | 2026-10-27 09:00 | 42,311 / 38,711 | 3,575 | 0.854641 |

Each fold fits a new model on earlier data. The candidate reserves 30 preceding
days for scalar calibration, with 24-hour label-end embargoes between fitting,
calibration and evaluation. The matched raw GBT uses exactly the candidate's fit
rows. Legacy controls use all earlier data available under the same evaluation
embargo. Scaling is fit on training data only. Native/export parity passed on
held-out rows. Volatility-regime cutoffs use training medians, not future data.

Log loss (lower is better):

| Model | Fold 1 | Fold 2 | Fold 3 |
|---|---:|---:|---:|
| Training-frequency prior | 1.117519 | 1.087821 | 1.082737 |
| Existing logistic specification | 1.061780 | 1.045559 | 1.052682 |
| Existing GBT specification, full causal fit window | **1.052874** | **1.042852** | 1.044446 |
| Matched raw GBT | 1.054760 | 1.043831 | 1.044826 |
| Calibrated matched GBT | 1.054656 | 1.042947 | **1.042926** |

The candidate improves over its matched control in 3/3 folds. The equal-asset,
equal-UTC-day mean log-loss difference is **-0.00105801**; the prespecified
seven-day circular block-bootstrap 95% interval is **[-0.00182329, -0.00038692]**
(1,000 draws, seed 17). The one-day sensitivity interval is
[-0.00191380, -0.00022071]. This small improvement does not establish broad
superiority: the practical full-data GBT beats the candidate in two folds.

Brier scores also improve slightly over the matched control in all three folds.
Conditional up-versus-down AUC is approximately .5093, .5178 and .5386, essentially
unchanged by temperature scaling. Positive scalar scaling preserves directional
ranking within a fold; minute tie/rounding differences do not represent new alpha.
Top-label calibration error improves in folds 1/3 but worsens in fold 2
(.012280 to .017344). Proper-score improvement is not universal calibration gain.

Asset/regime robustness is mixed. Log loss worsens for SOL in folds 1/2 and DOGE
in fold 1; high-volatility observations worsen in folds 1/2. Fold 3 improves for
all five assets and both volatility groups. Thus the aggregate result is not
uniform across market conditions. All 120 model/fold/group metric rows, including
calibration bins in JSON, are retained in the evidence files.

## Existing-engine ETH replay

Before comparison, the unchanged strategy reproduced the saved research baseline
exactly: final equity 9,287.991489687984 from 10,000, return -7.1200851031201635%,
64 executions and a matching full execution JSON SHA256. This verifies local
replay compatibility with that saved experiment, not live execution fidelity.

Every row below uses the same strategy, risk settings, bars, funding and public
contract/tier snapshot. Doubling costs doubles fees and slippage; funding remains
the same historical series. No trading parameters were changed in the application.

| Variant | Gate | Entries, each cost setting | Return, normal / double costs | Max drawdown, normal / double costs |
|---|---:|---:|---:|---:|
| Existing strategy, ML disabled | — | 32 | -7.12% / -42.06% | 85.52% / 88.97% |
| Logistic control | .45 | 2 | -42.65% / -44.75% | 52.98% / 54.44% |
| Full-data GBT control | .45 | 0 | 0% / 0% | 0% / 0% |
| Matched raw GBT | .45 | 0 | 0% / 0% | 0% / 0% |
| Calibrated GBT, primary | .45 | 0 | 0% / 0% | 0% / 0% |
| Calibrated GBT, sensitivity | .40 | 2 | +207.29% / +200.93% | 21.05% / 22.38% |
| Calibrated GBT, sensitivity | .50 | 0 | 0% / 0% | 0% / 0% |

Zero entries mean the primary candidate failed the trading-participation
criterion. Staying in cash is not evidence of a predictive trading advantage.
The .40 sensitivity's attractive return comes entirely from two long positions
in fold 1: August 10 (11h, net -1,479.23) and August 18–22 (89h, net +22,208.44),
in the replay's quote-currency units. One winning trade drives the total. There
are no additional entries in folds 2/3. The preserved sizing uses 5% equity margin
at requested 200x leverage, approximately 10x account notional at entry. This
amplifies outcomes; complete intrabar liquidation/ADL is not modeled.

The .40 threshold was a prespecified sensitivity, not a selected replacement for
the .45 primary. No matched-raw .40 ablation was preregistered, so its return also
cannot isolate the contribution of calibration. It is recorded without promotion
or a post-hoc threshold search. Sharpe/Sortino, turnover, costs and leverage for
all 14 cases are in `replay-summary.json`; two trades cannot establish stability.

## Measurement amendment and limits

Initial aggregation grouped by fold/day before averaging. Two 10:00 UTC fold
boundaries split days and produced 93 fold-day clusters for 91 actual UTC days.
The corrected method aggregates each asset's entire UTC day, then averages assets
and resamples consecutive day blocks across the whole evaluation sequence.
`initial-summary.json` preserves the superseded interval and `summary.json`
records the reason, source hashes, unchanged predictions and corrected interval.
The correction was made after observing results; it is not represented as an
untouched preregistered implementation. A regression test covers this boundary.

The intervals are conditional descriptive uncertainty for one short, selected,
previously inspected sample. They do not adjust for earlier project research,
asset survivorship, unknown data revisions or all model-selection uncertainty.
Block length seven is a prespecified sensitivity assumption, not a proven
dependence horizon. The first/last UTC days are partial. There is no measured
exchange-arrival latency, historical order book, full liquidation model or
point-in-time historical tier universe. Funding coverage is incomplete before
2026-02-13 during warmup; the replay itself starts in July. Historical tier and
volume-unit assumptions remain unchanged from the saved baseline.

## Decision and next work

- Accept the manifest/embargo/parity/uncertainty tooling for QD review.
- Retain the calibrated model as a versioned **research-only rejected-for-promotion**
  artifact. Do not activate it in PAPER or LIVE.
- Prioritize target/holding-period alignment: current four-hour labels do not
  directly describe the 11h/89h position paths above. Preregister one objective
  comparison against the same simple controls before running another experiment.
- Ask QD to review provenance enforcement and walk-forward naming through
  `docs/interface-requests/qr-001.md`; no shared-contract edits are made here.
- Reserve genuinely new data for prospective evaluation. More model complexity
  or deep learning is not justified by these results.

## Evidence inventory

`evidence-sha256.json` checks the nine numeric/model evidence files. `summary.json`
contains full fold/asset/regime metrics and the correction; `paired_losses.csv`
permits independent uncertainty reproduction; `daily_paired_losses.csv` contains
the corrected 91-day series. `run_manifest.json` records code/data/environment.
`execution-ledgers.json` retains every simulated fill/trade for all replay cases.
`calibrated_gbt.json` is the unchanged existing-format model artifact, SHA256
`3d00fce3aceff2ee2986f4d522094500726298b8669489226b2a957643392f28`.
Control bundles and full replay equity/chart series remain in ignored local
`research/runs/`; their model hashes are recorded and they can be rebuilt using
the research README. Raw public datasets remain ignored and hash-bound.
