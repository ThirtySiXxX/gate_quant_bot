"""Causal hourly ML features and JSON-only inference, shared by live and replay.

Training dependencies are deliberately absent here. An unavailable/expired model
blocks new entries through the shared policy; it never disables existing exits.
"""
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

FEATURE_VERSION = 1
FEATURE_NAMES = tuple(
    [f"return_{h}h" for h in (1, 4, 12, 24, 72, 168)]
    + [f"volatility_{h}h" for h in (6, 24, 72)]
    + [f"volume_relative_{h}h" for h in (6, 24, 168)]
    + ["range_pct", "body_pct", "upper_wick_pct", "lower_wick_pct", "efficiency_24h",
       "hour_sin", "hour_cos", "weekday_sin", "weekday_cos"])


def causal_features(candles):
    """A row becomes available at timestamp+3600; gaps restart all lookbacks."""
    frame = candles.reset_index(drop=True).copy()
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("ML行情必须按时间严格升序且无重复")
    values = frame[["open", "high", "low", "close", "volume"]].astype(float)
    valid = np.isfinite(values).all(axis=1) & (values.iloc[:, :4] > 0).all(axis=1)
    valid &= (values.volume >= 0) & (values.high >= values[["open", "close", "low"]].max(axis=1))
    valid &= values.low <= values[["open", "close"]].min(axis=1)
    segment = (frame.timestamp.diff().ne(3600) | ~valid | ~valid.shift(fill_value=False)).cumsum()
    out = pd.DataFrame(np.nan, index=frame.index, columns=FEATURE_NAMES)
    for _, group in frame.groupby(segment, sort=False):
        if len(group) < 169 or not valid.loc[group.index].all():
            continue
        x = pd.DataFrame(index=group.index)
        close = group.close.astype(float)
        returns = np.log(close).diff()
        for h in (1, 4, 12, 24, 72, 168):
            x[f"return_{h}h"] = np.log(close / close.shift(h))
        for h in (6, 24, 72):
            x[f"volatility_{h}h"] = returns.rolling(h, min_periods=h).std()
        for h in (6, 24, 168):
            average = group.volume.rolling(h, min_periods=h).mean()
            x[f"volume_relative_{h}h"] = np.log((group.volume + 1) / (average + 1))
        x["range_pct"] = (group.high - group.low) / close
        x["body_pct"] = (close - group.open) / close
        x["upper_wick_pct"] = (group.high - group[["open", "close"]].max(axis=1)) / close
        x["lower_wick_pct"] = (group[["open", "close"]].min(axis=1) - group.low) / close
        travel = close.diff().abs().rolling(24, min_periods=24).sum()
        x["efficiency_24h"] = (close - close.shift(24)).abs() / travel.replace(0, np.nan)
        dates = pd.to_datetime(group.timestamp, unit="s", utc=True)
        for name, cycle, period in (("hour", dates.dt.hour, 24), ("weekday", dates.dt.dayofweek, 7)):
            x[name + "_sin"] = np.sin(2 * np.pi * cycle / period)
            x[name + "_cos"] = np.cos(2 * np.pi * cycle / period)
        out.loc[group.index] = x.loc[:, list(FEATURE_NAMES)].values
    return out.replace([np.inf, -np.inf], np.nan)


def supervised_samples(candles, symbol, horizon=4, round_trip_cost=.0014, edge=.001):
    """Three classes: down/neutral/up; entry at next open, exit h hours later.

    Unknown future outcomes stay missing. Any gap in the feature or label window
    invalidates that row; missing hours are never interpolated into samples.
    """
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon 必须为正整数")
    frame = candles.reset_index(drop=True)
    features = causal_features(frame)
    entry, exit_price = frame.open.shift(-1), frame.open.shift(-horizon-1)
    end = frame.timestamp.shift(-horizon-1)
    forward = exit_price / entry - 1
    complete = end.sub(frame.timestamp).eq((horizon+1)*3600) & features.notna().all(axis=1)
    complete &= np.isfinite(forward) & entry.gt(0) & exit_price.gt(0)
    target = np.where(forward > round_trip_cost+edge, 1, np.where(forward < -round_trip_cost-edge, -1, 0))
    data = features.copy()
    data["symbol"] = symbol
    data["feature_time"] = frame.timestamp + 3600
    data["label_end"] = end
    data["target"] = target
    data["forward_return"] = forward
    return data.loc[complete].reset_index(drop=True)


def load_bundle(path):
    source = Path(path)
    if source.stat().st_size > 20_000_000:
        raise ValueError("ML模型文件过大")
    bundle = json.loads(source.read_text())
    if not isinstance(bundle, dict):
        raise ValueError("ML模型必须是JSON对象")
    if bundle.get("feature_version") != FEATURE_VERSION or tuple(bundle.get("feature_names", [])) != FEATURE_NAMES:
        raise ValueError("ML特征版本不匹配")
    if (bundle.get("classes") != [-1, 0, 1]
            or not isinstance(bundle.get("models"), list) or not bundle["models"]):
        raise ValueError("ML类别或模型缺失")
    previous = -math.inf
    for model in bundle["models"]:
        if not isinstance(model, dict):
            raise ValueError("ML模型条目必须是JSON对象")
        start, end, trained = (float(model[k]) for k in ("valid_from", "valid_until", "trained_until"))
        if not all(math.isfinite(x) for x in (start, end, trained)) or not trained < start < end or start < previous:
            raise ValueError("ML训练与使用窗口重叠或包含未来标签")
        if model.get("kind") not in ("logistic", "gradient_boosting"):
            raise ValueError("未知ML模型类型")
        previous = end
    return bundle


def _tree_value(tree, row):
    node = 0
    for _ in range(len(tree["left"])):
        left = tree["left"][node]
        if left == -1:
            return tree["value"][node]
        node = left if row[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
    raise ValueError("ML树结构无效")


def predict_probabilities(model, rows):
    rows = np.asarray(rows, dtype=float)
    if rows.ndim != 2 or rows.shape[1] != len(FEATURE_NAMES) or not np.isfinite(rows).all():
        raise ValueError("ML特征缺失或无效")
    if model["kind"] == "logistic":
        scale = np.asarray(model["scale"])
        if not (scale > 0).all():
            raise ValueError("ML缩放参数无效")
        raw = ((rows - model["mean"]) / scale) @ np.asarray(model["coef"]).T + model["intercept"]
    else:
        # sklearn's decision trees evaluate float32 inputs at their split thresholds.
        rows = rows.astype(np.float32)
        raw = np.tile(np.asarray(model["initial_raw"], dtype=float), (len(rows), 1))
        for stage in model["trees"]:
            for label, tree in enumerate(stage):
                raw[:, label] += model["learning_rate"] * np.array([_tree_value(tree, row) for row in rows])
    if raw.shape != (len(rows), 3) or not np.isfinite(raw).all():
        raise ValueError("ML预测无效")
    exp = np.exp(raw - raw.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def prepare_predictions(candles, path):
    """Load once per market snapshot; compute only each model's allowed window."""
    output = [{"status": "模型未覆盖该时段"} for _ in range(len(candles))]
    try:
        bundle = load_bundle(path)
        features = causal_features(candles)
        available = candles.timestamp.to_numpy() + 3600
        for model in bundle["models"]:
            chosen = np.flatnonzero((available >= model["valid_from"]) & (available < model["valid_until"])
                                    & features.notna().all(axis=1).to_numpy())
            if len(chosen):
                probabilities = predict_probabilities(model, features.iloc[chosen].to_numpy())
                for i, p in zip(chosen, probabilities):
                    output[i] = {"status": "ok", "short": float(p[0]), "neutral": float(p[1]), "long": float(p[2]),
                                 "valid_until": model["valid_until"], "feature_time": float(available[i])}
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        output = [{"status": "模型不可用：" + str(exc)[:160]} for _ in output]
    return output
