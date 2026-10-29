# QR-001 calibrated GBT model card

Status: research-only, rejected for paper promotion in this experiment.
Version: `qr001-temperature-calibration-v1`, feature version 1, classes [-1,0,1].
Implementation: `models.py`; saved model: `../results/qr001/calibrated_gbt.json`.
The result report contains the exact hash, windows, limitations and decision.

## Hypothesis and data

A single scalar temperature fit on a separate preceding period might correct
the scale of shallow-GBT three-class probabilities. It does not create new
directional rankings. Assets: BTC_USDT, ETH_USDT, SOL_USDT, DOGE_USDT, ZEC_USDT,
Gate perpetual research candles. Full file hashes/coverage are in data_manifest.
Volume is the original public downloader's `v` representation; this study does
not relabel it as USD notional or prove invariance to a volume-unit conversion.

## Features, units and timing

No new features or feature ordering are introduced. `src.crypto_ml.causal_features`
is shared by training and inference. In the following table t is a completed
hourly candle's open timestamp, C is its close, O/H/L are OHLC, V is raw volume.
All outputs are dimensionless. Names ending in `_pct` are fractions, not 0–100.

| Ordered fields | Definition |
|---|---|
| return_{1,4,12,24,72,168}h | ln(C_t / C_(t-h)) |
| volatility_{6,24,72}h | sample standard deviation (ddof=1) of hourly log returns over h observations; not annualized |
| volume_relative_{6,24,168}h | ln((V_t+1)/(rolling mean V over h +1)); includes current completed candle |
| range_pct, body_pct | (H-L)/C, (C-O)/C |
| upper_wick_pct, lower_wick_pct | (H-max(O,C))/C, (min(O,C)-L)/C |
| efficiency_24h | abs(C_t-C_(t-24)) / sum of absolute hourly price changes over 24h |
| hour_sin, hour_cos | sin/cos of 2π times UTC candle-open hour /24 |
| weekday_sin, weekday_cos | sin/cos of 2π times UTC candle-open weekday /7; Monday=0 |

Feature availability/decision time is t+3600 seconds UTC. Minimum history is 169
contiguous hourly candles for 168h lookbacks. Gaps reset lookbacks; invalid OHLCV,
undefined zero-travel efficiency or missing features exclude samples. No future
normalization is applied. The study assumes completed data arrive at the boundary;
it has no measured arrival/revision timestamps or feed latency simulation.

Target: simple return from open at t+3600 to open at t+18000 (four-hour holding
horizon). Class +1 if return > .0014+.001, -1 if return < -.0014-.001, otherwise 0.
Label_end is the exit timestamp, not the feature timestamp. The .0014 round-trip
cost and .001 edge are dimensionless fixed label assumptions, not fitted trading
PnL. Label-end embargo is 24h for fit-to-calibration and calibration-to-evaluation;
evaluation labels crossing a fold's end are excluded.

## Fitting and artifact

GBT specification is unchanged: 60 stages, learning_rate .04, depth 2,
min_samples_leaf 200, subsample .8, max_features .8, random_state 17.
Logistic control: StandardScaler fit on training only, C=.2, max_iter=500,
random_state 17. The training-frequency prior is another control.

For each fold, temperature T minimizes calibration log loss within [.25,4], using
bounded scalar minimization on log(T). Probabilities are softmax(raw/T). Export
divides initial_raw and learning_rate by T, retaining the existing GBT tree JSON
shape. Calibrated trained_until is the latest calibration label, because
calibration is part of fitting. `train_rows` retains the base estimator's row
count; calibration provenance is in the sidecar, not a silently redefined field.

Three validity windows, end exclusive: 2026-07-29 10:00–2026-08-28 10:00 UTC;
2026-08-28 10:00–2026-09-27 10:00 UTC;
2026-09-27 10:00–2026-10-27 09:00 UTC. They are historical evaluation windows,
not authorization for current use or an automatically refreshing model.

Training uses Python 3.13.7, numpy 2.5.4, pandas 3.0.5, scipy 1.18.1, sklearn
1.9.1 on local CPU with numerical thread limits of one. No new installation or
cloud resources were used. The candidate bundle is 557,580 bytes; no pickle.
Inference uses existing numpy/pandas/JSON code and does not import sklearn/scipy.
Runtime latency is not benchmarked or approved for a production budget here.

## Stable consumption boundary

`load_bundle(path)` validates the existing bundle and feature order;
`predict_probabilities(model, rows)` returns N×3 probabilities in short/neutral/
long order; `prepare_predictions(candles, path)` adds status, feature_time and
valid_until using the existing native interface. A scalar calibration requires
no new runtime adapter. All native/export comparisons passed on held-out data.
The research-side hashes/manifest do not imply the runtime loader enforces them.
QD integration review is required before any future adoption of such checks.

Failure scenarios include regime shifts in probability scale, too little
calibration history, near-random directional predictions, threshold-induced
nonparticipation, feature gaps, changed volume representation, expired models,
selection bias and leveraged replay outcomes dominated by one trade. Four-hour
labels do not directly optimize multi-day exits. Current evidence fails trading
suitability despite a small proper-score improvement; see the result report.
