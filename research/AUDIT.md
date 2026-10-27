# QR research audit — 2026-10-27

Role: QR. Research worktree: `codex/qr-validation-baseline`, based on QD's
source snapshot `475aaea`. Runtime source matches the original dirty checkout;
three later shared-document updates are read from source but not overwritten here.
Claims: `research/**`, `tests/qr_research/**`, `docs/agent-reports/qr/**`,
`docs/interface-requests/qr-001.md`. QD owns infrastructure/shared journals.

## Existing research and evidence

- Multi-horizon EWMAC uses price-volatility normalization, lagged scaling and
  lagged correlation diversification. Carry uses backward-aligned settled funding.
  Signals use completed bars; execution timing/position sizing is shared with
  replay. Unit tests already exercise prefix invariance and adapter parity.
- Hourly ML has 21 price/volume/time features, 168h contiguous warmup and a
  four-hour next-open three-class target. Logistic regression and shallow gradient
  boosting export JSON; runtime transformations are shared. No deep learning,
  historical order flow, order book/OI/liquidation feature set was found.
- Previous reports document corrected missing-hour data and rejected/no-trade ML
  candidates. Historical profitability is not assumed. Four-hour classification
  may not match multi-day trend-position exits; macro AUC can reflect neutral vs
  volatile states without strong conditional direction discrimination.

## Data inventory, verified this run

Five explicitly named public Gate hourly CSVs under the earlier `work/crypto-ml/data`
match the saved public-data-manifest SHA256 values: BTC/ETH/SOL/DOGE each 9,600
bars (2025-09-22 09:00 to 2026-10-27 08:00 UTC); ZEC 8,491 bars (2025-11-07
14:00 to the same end). Total 46,891. No duplicate timestamps, internal gaps or
nonfinite OHLCV were observed. ZEC's missing prefix is not proof of listing date.
Further checks of OHLC bounds, grid/coverage and feature/label continuity are
required by the new manifest loader before fitting.

Available separate research replay files include repaired ETH 1h/4h/1d candles,
settled funding CSV, public contract/tier snapshots and a saved simulated baseline
result/configuration. These are historical research artifacts, not real account
data. The original app `data/`, real config and credentials are not opened.
No usable point-in-time historical listed/delisted universe or order-book data was
identified. No new download is needed for QR-001.

## Prioritized weaknesses

| Priority | Evidence | Consequence / action |
|---|---|---|
| 1 | External `train.py` selects `data.glob('*_1h.csv')`; repaired `clean_ETH_USDT_1h.csv` now also matches | Rerunning can add a sixth, duplicated ETH series under a false symbol. Use a strict symbol/file/hash manifest; test that extra files cannot enter training. Earlier five-asset results are not retroactively declared contaminated. |
| 1 | `ml_training.fit_export` checks only label_end before valid_from | Put both fit/calibration/evaluation label-boundary embargo checks in a reproducible runner, with common timestamps across all assets. |
| 1 | Samples overlap for four hours; assets share market risk | Per-row metrics overstate independent sample count. Pair model losses by UTC day, aggregate assets together, report block-bootstrap uncertainty and fold/asset dispersion. |
| 1 | Prior data/time periods have already been inspected | This is retrospective out-of-training evaluation, not a virgin final test. Freeze protocol before new results and require prospective evidence for promotion. |
| 2 | `walkforward.py` never retrains and mode does not change slicing | Keep production runner untouched; implement a research split/fit/calibrate/evaluate protocol with tests, and request QD semantics clarification separately. |
| 2 | Probabilities drive a fixed .45 fresh-entry threshold, but past report emphasizes AUC | Evaluate proper scores/calibration and actual gate behavior. Test one predeclared temperature calibration candidate, not more indicators. |
| 2 | Export parity helper checks first training rows | New research trainer checks JSON/native inference on calibration and evaluation data too; no serialized sklearn/pickle dependency in runtime artifacts. |
| 2 | Features and model bundle lack mandatory artifact/data provenance | Add research-side manifests/code/dependency hashes and validity windows. Runtime schema changes remain a QD coordination request. |
| 2 | Volume uses `(volume+1)/(mean+1)` and generic downloader can mix raw fields | Pin exact source representation; dimensionless outputs are not invariant to unit conversion. Current selected public downloader reads `v` only. |
| 2 | Risk sizing/high leverage and incomplete liquidation can dominate returns | Same-input replay is a compatibility/cost diagnostic, not survival validation. Keep leverage/risk/defaults unchanged. |
| 3 | Five chosen survivors, 400d, incomplete historical tiers/funding and external dependencies | Expand point-in-time data/prospective evidence before broader model complexity; document present limitations. |

## QR-001 hypothesis and falsification

Existing shallow boosting probabilities may be systematically too sharp or too
flat relative to subsequent three-class frequencies. A scalar temperature fitted
only to a preceding calibration period may improve out-of-training log loss.
This is a probability-quality hypothesis, not a claim of new directional alpha.
It can fail when regime shifts change probability scale, when the base model has
no usable signal, or when calibration reduces already sparse trading participation.

Required data: the five frozen hourly datasets, unchanged 21 features/4h labels,
24h embargo on last label before every next stage, and 30 days of calibration
before each evaluation fold. One common split applies to all assets. Prior,
existing logistic/GBT specifications and matched uncalibrated GBT are controls.
The matched control uses exactly the candidate's training data; the legacy GBT
uses all causally available prior training data, preserving the practical baseline.

Temperature is bounded [.25,4] and fitted by calibration log loss only. Scaling
GBT raw scores can be folded into its existing JSON initial scores and learning
rate, so no runtime schema or feature-order change is required. Metadata must
record the latest calibration label as trained_until; calibration is training too.

Primary falsification and secondary trading conditions are frozen in
`qr001/protocol.json`. Report all three folds/assets, 1-day/7-day bootstrap blocks,
normal/double transaction costs, and .40/.45/.50 gate sensitivities without picking
the best afterwards. Reuse QD's actual replay for ETH; do not write a second fill
simulator. No positive prediction metric alone qualifies a trading candidate.

## Research roadmap

1. QR-001: strict manifest, embargoed chronological baseline, one calibration
   experiment, uncertainty, same-runtime replay and complete reproducibility.
2. Align future labels with intended holding/exit paths; compare one prespecified
   horizon/objective at a time against current four-hour labels, without borrowing
   future extrema or selecting using test outcomes.
3. Acquire prospective and point-in-time asset/funding/liquidity provenance with
   QD. Only then research cross-asset/funding/liquidity hypotheses.
4. Test regularized return/volatility baselines and regime stability before deeper
   trees, MLP/TCN or attention. Deep learning requires enough independent regimes,
   a measurable incremental benefit, latency/memory budgets and simple controls.
5. Preserve every negative experiment and reserve genuinely new periods for final
   evaluation. RL is deferred until environment/fill/cost fidelity is established.

## Method references

Chronological train-before-test and an explicit gap are consistent with
[scikit-learn TimeSeriesSplit](https://scikit-learn.org/1.5/modules/generated/sklearn.model_selection.TimeSeriesSplit.html);
the runner adds label-end purging and pooled-asset timestamp grouping that a raw
row-index split cannot guarantee. Proper probability scores measure more than
calibration alone ([scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html)).
Temperature scaling is a one-parameter calibration method described by
[Guo et al. (2017)](https://arxiv.org/abs/1706.04599); their image/document results
are not evidence that it works on these crypto data. This experiment tests that.
