"""Run the fixed QR-001 experiment with hash-verified local public data only."""
import argparse
from pathlib import Path
import json
import platform
import subprocess
import time

import numpy as np
import pandas as pd
import scipy
import sklearn

from src.crypto_ml import FEATURE_NAMES, FEATURE_VERSION, load_bundle, predict_probabilities
from .models import calibrate, fit_reference, temperature_probabilities
from .validation import (block_interval, load_manifest_data, losses, make_samples,
                         metrics, paired_daily_losses, sha256, split_stages, write_json)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(data_root, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('use a new output directory; previous experiments are immutable')
    protocol = json.loads((HERE / 'protocol.json').read_text())
    manifest = json.loads((HERE / 'data_manifest.json').read_text())
    if protocol['seed'] != 17 or protocol['feature_version'] != FEATURE_VERSION:
        raise ValueError('this fixed baseline supports seed 17 and the current feature version only')
    if sha256(HERE / 'replay_fixture.json') != manifest['replay_fixture_sha256']:
        raise ValueError('replay fixture hash mismatch')
    frames = load_manifest_data(data_root, manifest, protocol['symbols'])
    samples = make_samples(frames, manifest, protocol)
    output.mkdir(parents=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    write_json(output / 'run_manifest.json', dict(experiment_id=protocol['experiment_id'],
        revision=revision, protocol_sha256=sha256(HERE / 'protocol.json'),
        data_manifest_sha256=sha256(HERE / 'data_manifest.json'),
        packages=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                      scipy=scipy.__version__, sklearn=sklearn.__version__),
        source_sha256={str(p.relative_to(ROOT)): sha256(p) for p in list(HERE.glob('*.py')) +
                       [ROOT / 'src/crypto_ml.py', ROOT / 'src/ml_training.py', ROOT / 'src/backtest.py']},
        input_rows=sum(r['rows'] for r in manifest['files'] if r['role'] == 'classification'),
        samples=len(samples), symbols=protocol['symbols'], label='retrospective, previously inspected history'))
    names = protocol['models']
    bundles = {name: dict(feature_version=FEATURE_VERSION, feature_names=list(FEATURE_NAMES),
                         classes=[-1, 0, 1], models=[]) for name in names if name != 'prior'}
    reports, paired = [], []
    cuts = protocol['evaluation_cutoffs']
    for fold, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
        stages = split_stages(samples, start, end, protocol['embargo_hours'], protocol['calibration_days'])
        test, cal = stages['evaluation'], stages['calibration']
        x = test[list(FEATURE_NAMES)].to_numpy()
        x_cal = cal[list(FEATURE_NAMES)].to_numpy()
        fold_models, probabilities, parity = {}, {}, {}
        for name, kind, fit in [('legacy_logistic', 'logistic', stages['legacy_fit']),
                                ('legacy_gbt', 'gradient_boosting', stages['legacy_fit']),
                                ('matched_raw_gbt', 'gradient_boosting', stages['fit'])]:
            began = time.monotonic()
            model, native = fit_reference(kind, fit, start, end)
            fold_models[name] = model
            probabilities[name] = predict_probabilities(model, x)
            error = float(np.max(np.abs(probabilities[name] - native(x))))
            np.testing.assert_allclose(probabilities[name], native(x), atol=1e-10, rtol=1e-9)
            parity[name] = dict(evaluation_max_abs_error=error, fit_seconds=time.monotonic() - began)
            if name == 'matched_raw_gbt':
                np.testing.assert_allclose(predict_probabilities(model, x_cal), native(x_cal), atol=1e-10, rtol=1e-9)
            print(json.dumps(dict(fold=fold, fitted=name, rows=len(fit))), flush=True)
        candidate, temperature = calibrate(fold_models['matched_raw_gbt'], cal, start,
                                           protocol['embargo_hours'], protocol['temperature_bounds'])
        fold_models['calibrated_gbt'] = candidate
        probabilities['calibrated_gbt'] = predict_probabilities(candidate, x)
        np.testing.assert_allclose(probabilities['calibrated_gbt'],
            temperature_probabilities(probabilities['matched_raw_gbt'], temperature), atol=1e-10, rtol=1e-9)
        prior = stages['legacy_fit'].target.value_counts(normalize=True).reindex([-1, 0, 1]).to_numpy()
        probabilities['prior'] = np.tile(prior, (len(test), 1))
        for name, model in fold_models.items():
            bundles[name]['models'].append(model)
        regime_threshold = float(stages['fit'].volatility_24h.median())
        row = dict(fold=fold, start=start, end=end, temperature=temperature,
                   stages={k: dict(rows=len(v), first_feature=float(v.feature_time.min()),
                                   last_label=float(v.label_end.max())) for k, v in stages.items()},
                   parity=parity, regime_volatility_threshold=regime_threshold, models={})
        for name in names:
            p = probabilities[name]
            row['models'][name] = dict(overall=metrics(test.target.to_numpy(), p),
                by_symbol={s: metrics(test.loc[test.symbol == s, 'target'].to_numpy(), p[test.symbol.eq(s).to_numpy()])
                           for s in protocol['symbols']},
                by_volatility_regime={r: metrics(test.loc[mask, 'target'].to_numpy(), p[mask.to_numpy()])
                    for r, mask in [('high', test.volatility_24h > regime_threshold),
                                    ('low', test.volatility_24h <= regime_threshold)] if mask.any()})
        pair = test[['symbol', 'feature_time', 'target']].copy()
        pair['fold'] = fold
        pair['matched_raw_log_loss'] = losses(test.target.to_numpy(), probabilities['matched_raw_gbt'])
        pair['calibrated_log_loss'] = losses(test.target.to_numpy(), probabilities['calibrated_gbt'])
        paired.append(pair)
        reports.append(row)
        write_json(output / f'fold-{fold}.json', row)
        print(json.dumps(dict(fold=fold, temperature=temperature, evaluation_rows=len(test),
            raw_log_loss=row['models']['matched_raw_gbt']['overall']['log_loss'],
            calibrated_log_loss=row['models']['calibrated_gbt']['overall']['log_loss'])), flush=True)
    artifacts = {}
    for name, bundle in bundles.items():
        path = output / (name + '.json')
        write_json(path, bundle)
        load_bundle(path)
        artifacts[name] = dict(file=path.name, sha256=sha256(path), status='research_only_historical_windows')
    pairs = pd.concat(paired, ignore_index=True)
    pairs.to_csv(output / 'paired_losses.csv', index=False)
    daily = paired_daily_losses(pairs)
    daily.to_csv(output / 'daily_paired_losses.csv', index=False)
    intervals = [block_interval(daily, b, protocol['bootstrap_repetitions'], protocol['seed'])
                 for b in protocol['bootstrap_block_days']]
    improved_folds = sum(r['models']['calibrated_gbt']['overall']['log_loss'] <
                         r['models']['matched_raw_gbt']['overall']['log_loss'] for r in reports)
    summary = dict(experiment_id=protocol['experiment_id'], folds=reports, intervals=intervals,
                   improved_folds=improved_folds, predictive_gate_passed=bool(
                       intervals[0]['upper_95'] < 0 and improved_folds >= 2), artifacts=artifacts,
                   recommendation='No model promotion; await trading diagnostics and genuinely new data')
    write_json(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.data_root, args.output)
