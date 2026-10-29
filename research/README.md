# Offline QR research

Current study: [audit and roadmap](AUDIT.md), [fixed protocol](qr001/protocol.json),
[input manifest](qr001/data_manifest.json). Runtime code and shared contracts are
not edited. Every run requires a fresh output directory and verified input bytes.

Completed: [QR-001 results and decision](results/qr001/README.md),
[model card](qr001/MODEL_CARD.md). The primary trading gate failed; no candidate
is approved for activation. Exact model and compact numerical evidence are tracked
under `results/qr001/`; raw data and full run directories remain ignored.

## Reproduce QR-001

Use Python 3.13 with the project runtime requirements and optional research
requirements in a separate research environment. The recorded run uses numpy
2.5.4, pandas 3.0.5, scipy 1.18.1 and scikit-learn 1.9.1; runtime inference still
does not require sklearn. No dependency was installed into the trading environment.
For this machine, existing research dependencies are available read-only:

```sh
cd /Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/Users/lzh/Documents/Codex/2026-09-06/ni/work/crypto-ml/train-deps
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
QR_PY=/Users/lzh/Development/Project/gate_quant_bot/venv/bin/python
"$QR_PY" -m unittest discover -s tests -v
"$QR_PY" -m research.qr001.run --data-root research/.data/qr001 --output research/runs/qr001-reproduction
"$QR_PY" -m research.qr001.replay --data-root research/.data/qr001 --model-root research/runs/qr001-reproduction --output research/runs/qr001-reproduction-replay
```

The input directory contains only explicitly copied public research CSVs, not
the app's data directory. Raw data/runs are ignored by Git. The manifest specifies
relative filenames, coverage and SHA256; place the original matching files under
that layout to reproduce elsewhere. Hash mismatch is an error, not a download or
automatic refresh. Current local sources: the five named `work/crypto-ml/data`
CSV files, repaired `clean_ETH_USDT_{1h,4h,1d}.csv`, and
`work/return-regression/frozen/funding.csv` in the earlier research task directory.
All source hashes and the extracted public contract/replay configuration are
recorded. Do not execute the older external diagnosis scripts: they read the
application's account/configuration directories and are unnecessary here.

`run.py` trains prior/logistic/GBT controls and the one temperature-calibrated
candidate. `replay.py` calls the existing portfolio engine, verifies the original
baseline's exact execution hash first, and compares all prespecified cases.
Seven-day paired daily block intervals are primary; one-day intervals are a
sensitivity check. Blocks keep cross-asset dependence together. Uncertainty is
descriptive for this small previously inspected sample, not a guarantee of
future edge or adjustment for the project's entire research search history.

The existing model JSON format is preserved. Calibration scales raw scores and
sets trained_until to the last calibration label. Artifact windows are historical
and outputs are research-only. Native-reference probability parity is tested on
held-out data. Reports keep log loss, Brier, direction-only AUC, calibration,
volatility-regime/asset/fold breakdowns and costs separate from promotion decisions.

## Reproduce the uncertainty correction without fitting

The initial run at `0ab04c2` split two UTC days by fold. The corrected code at
`854e1b6` uses unique UTC days. Models and predictions are unchanged. Using the
environment above, recompute from the preserved original run into a fresh path:

```sh
"$QR_PY" -m research.qr001.summarize --run-root research/runs/qr001-main --output research/runs/qr001-utc-reproduction
```

For a checkout without ignored run files, use tracked `results/qr001/paired_losses.csv`
with `paired_daily_losses` and `block_interval` directly; all source predictions
needed for these intervals are committed. The full initial and corrected
summaries are both retained. New full runs already use the corrected aggregation.
Choose unused output names on subsequent reruns; the tools refuse to overwrite
earlier experiments. Fit wall-clock times and recorded Git revision may differ;
compare numerical results and artifact hashes, not elapsed-time fields.
