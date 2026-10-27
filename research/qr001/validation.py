"""Manifest-bound data, chronological stages and paired research evaluation."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from src.crypto_ml import FEATURE_NAMES, supervised_samples


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def validate_frame(frame, record):
    required = ['timestamp', 'funding_rate'] if record['role'] == 'funding' else [
        'timestamp', 'open', 'high', 'low', 'close', 'volume']
    if any(c not in frame for c in required) or frame.empty:
        raise ValueError('missing market columns/rows')
    if not np.isfinite(frame[required].to_numpy(dtype=float)).all():
        raise ValueError('nonfinite market data')
    t = frame.timestamp
    if t.duplicated().any() or not t.is_monotonic_increasing:
        raise ValueError('timestamps must be unique and increasing')
    if len(frame) != record['rows'] or t.iloc[0] != record['start_ts'] or t.iloc[-1] != record['end_ts']:
        raise ValueError('manifest coverage mismatch')
    if record['role'] != 'funding':
        seconds = record['interval_seconds']
        if (t % seconds != 0).any() or (t.diff().dropna() != seconds).any():
            raise ValueError('off-grid timestamp or internal gap')
        if (frame[['open', 'high', 'low', 'close']] <= 0).any().any() or (frame.volume < 0).any():
            raise ValueError('invalid price/volume')
        if ((frame.high < frame[['open', 'close', 'low']].max(axis=1)).any()
                or (frame.low > frame[['open', 'close']].min(axis=1)).any()):
            raise ValueError('invalid OHLC bounds')


def load_manifest_data(data_root, manifest, symbols):
    """No globbing: extra files cannot become assets. Never change input bytes."""
    root = Path(data_root).resolve()
    selected = [r for r in manifest['files'] if r['role'] == 'classification']
    if sorted(r['symbol'] for r in selected) != sorted(symbols):
        raise ValueError('classification symbol manifest mismatch')
    if len({r['file'] for r in manifest['files']}) != len(manifest['files']):
        raise ValueError('duplicate manifest path')
    frames = {}
    for record in manifest['files']:
        path = (root / record['file']).resolve()
        if not path.is_relative_to(root) or sha256(path) != record['sha256']:
            raise ValueError('input path/hash mismatch: ' + record['file'])
        frame = pd.read_csv(path)
        validate_frame(frame, record)
        frames[record['file']] = frame
    return frames


def make_samples(frames, manifest, protocol):
    samples = []
    for record in manifest['files']:
        if record['role'] == 'classification':
            samples.append(supervised_samples(frames[record['file']], record['symbol'],
                horizon=protocol['label_horizon_hours'],
                round_trip_cost=protocol['round_trip_cost_fraction'],
                edge=protocol['label_edge_fraction']))
    result = pd.concat(samples, ignore_index=True).sort_values(['feature_time', 'symbol']).reset_index(drop=True)
    if result.duplicated(['symbol', 'feature_time']).any():
        raise ValueError('duplicate instrument-time sample')
    return result


def split_stages(samples, start, end, embargo_hours=24, calibration_days=30):
    """Purge by label end, using identical UTC boundaries for every asset."""
    if not start < end or embargo_hours < 0 or calibration_days <= 0:
        raise ValueError('invalid stage windows')
    embargo = embargo_hours * 3600
    cal_start = start - calibration_days * 86400
    groups = {
        'fit': samples[samples.label_end < cal_start - embargo],
        'calibration': samples[(samples.feature_time >= cal_start) & (samples.label_end < start - embargo)],
        'legacy_fit': samples[samples.label_end < start - embargo],
        'evaluation': samples[(samples.feature_time >= start) & (samples.feature_time < end)
                              & (samples.label_end < end)],
    }
    if any(frame.empty for frame in groups.values()):
        raise ValueError('empty stage')
    expected = set(samples.symbol)
    for name, frame in groups.items():
        if set(frame.symbol) != expected:
            raise ValueError('missing asset in stage ' + name)
        if not (frame.label_end > frame.feature_time).all():
            raise ValueError('invalid label timing')
    if groups['fit'].label_end.max() >= groups['calibration'].feature_time.min() - embargo:
        raise ValueError('fit/calibration leakage')
    if groups['calibration'].label_end.max() >= groups['evaluation'].feature_time.min() - embargo:
        raise ValueError('calibration/evaluation leakage')
    return {k: v.copy() for k, v in groups.items()}


def losses(y, probabilities):
    p = np.asarray(probabilities, dtype=float)
    if p.shape != (len(y), 3) or not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(1), 1):
        raise ValueError('invalid probabilities')
    index = np.asarray(y, dtype=int) + 1
    return -np.log(np.clip(p[np.arange(len(y)), index], 1e-15, 1))


def metrics(y, p):
    y = np.asarray(y)
    p = np.asarray(p)
    labels = np.array([-1, 0, 1])
    pred = labels[p.argmax(1)]
    onehot = y[:, None] == labels
    direction = y != 0
    recalls = [np.mean(pred[y == k] == k) for k in labels if np.any(y == k)]
    auc = float(roc_auc_score(y, p, labels=labels, multi_class='ovr')) if len(set(y)) == 3 else None
    direction_auc = float(roc_auc_score(y[direction] == 1,
        p[direction, 2] / np.maximum(p[direction, 0] + p[direction, 2], 1e-15))) if len(set(y[direction])) == 2 else None
    confidence, correct = p.max(1), pred == y
    bins = []
    for i in range(10):
        selected = (confidence >= i / 10) & (confidence < (i + 1) / 10 if i < 9 else confidence <= 1)
        if selected.any():
            bins.append(dict(count=int(selected.sum()), confidence=float(confidence[selected].mean()),
                             accuracy=float(correct[selected].mean())))
    return dict(rows=len(y), log_loss=float(log_loss(y, p, labels=labels)),
                brier=float(np.mean(np.sum((p - onehot) ** 2, axis=1))),
                accuracy=float(correct.mean()), balanced_accuracy=float(np.mean(recalls)),
                macro_auc=auc, direction_only_auc=direction_auc,
                top_label_ece=float(sum(b['count'] * abs(b['confidence'] - b['accuracy']) for b in bins) / len(y)),
                calibration_bins=bins)


def paired_daily_losses(predictions):
    rows = predictions.copy()
    rows['day'] = rows.feature_time // 86400
    rows['difference'] = rows.calibrated_log_loss - rows.matched_raw_log_loss
    # Preserve all cross-asset dependence: one equal-asset aggregate per UTC day.
    per_asset = rows.groupby(['fold', 'day', 'symbol']).difference.mean()
    return per_asset.groupby(['fold', 'day']).mean().reset_index()


def block_interval(daily, block_days=7, repetitions=1000, seed=17):
    if block_days < 1 or repetitions < 1 or daily.empty:
        raise ValueError('invalid bootstrap input')
    rng = np.random.default_rng(seed)
    folds = [g.sort_values('day').difference.to_numpy() for _, g in daily.groupby('fold')]
    draws = []
    for _ in range(repetitions):
        selected = []
        for values in folds:
            n = len(values)
            starts = rng.integers(0, n, size=int(np.ceil(n / block_days)))
            index = ((starts[:, None] + np.arange(block_days)) % n).ravel()[:n]
            selected.append(values[index])
        draws.append(float(np.concatenate(selected).mean()))
    return dict(mean_difference=float(daily.difference.mean()),
                lower_95=float(np.quantile(draws, .025)), upper_95=float(np.quantile(draws, .975)),
                day_clusters=len(daily), block_days=block_days, repetitions=repetitions,
                method='paired equal-asset UTC-day circular blocks, resampled within each fold')
