"""Causal indicator preparation and signal assembly shared by replay and live."""
import bisect
import math

import pandas as pd

from . import carry as carry_mod
from . import trend as trend_mod
from . import vol as vol_mod
from . import portfolio as pf
from .data_fetcher import INTERVAL_SECONDS
from .execution_timing import timing_features


def prepare_features(short, main, regime, funding_history, funding_interval, cfg):
    short_f = trend_mod.group_trend_forecast(short["close"], cfg.short_trend_interval, cfg)
    main_f = trend_mod.group_trend_forecast(main["close"], cfg.main_trend_interval, cfg)
    regime_s = (trend_mod.daily_regime_series(regime, cfg) if len(regime) >= cfg.regime_ema_long + 5
                else pd.Series(["range"] * len(regime), index=regime.index))
    carry_f = carry_mod.carry_forecast_series_from_history(
        main["close"], cfg.main_trend_interval, funding_history, funding_interval, cfg,
        bar_timestamps=main["timestamp"].values, fallback_funding_rate=0.0)
    vol_ann = vol_mod.price_vol_annualized(main["close"], cfg.main_trend_interval, lam=cfg.ewma_lambda)
    adaptive = vol_mod.adaptive_chop_risk_from_config(short, cfg)
    result = {
        "short_ts": short["timestamp"].tolist(), "main_ts": main["timestamp"].tolist(),
        "regime_ts": regime["timestamp"].tolist(), "short_f": short_f.values, "main_f": main_f.values,
        "regime": regime_s.values, "carry_f": carry_f.values, "vol_ann": vol_ann.values,
        "adaptive_risk_multiplier": adaptive["risk_multiplier"].values,
        "adaptive_efficiency_ratio": adaptive["efficiency_ratio"].values,
        "adaptive_vol_ratio": adaptive["vol_ratio"].values,
        "timing_features": timing_features(short).to_dict("records"),
    }
    if cfg.ml_model_path:
        from .crypto_ml import prepare_predictions
        result["ml_predictions"] = prepare_predictions(short, cfg.ml_model_path)
    return result


def signal_at(symbol, data, timestamp, cfg):
    def index(name, interval):
        return bisect.bisect_right(data[name+"_ts"], timestamp - INTERVAL_SECONDS[interval]) - 1
    si, mi, ri = (index("short", cfg.short_trend_interval), index("main", cfg.main_trend_interval),
                  index("regime", cfg.regime_interval))
    if si + 1 < cfg.min_bars_short or mi + 1 < cfg.min_bars_main or si < 0 or mi < 0:
        return None
    short, main, vol = float(data["short_f"][si]), float(data["main_f"][mi]), float(data["vol_ann"][mi])
    if not all(math.isfinite(v) for v in (short, main, vol)) or vol <= 0:
        return None
    regime = data["regime"][ri] if ri + 1 >= cfg.regime_ema_long + 5 else "range"
    trend = trend_mod.apply_regime_gate(trend_mod.combine_trend(short, main, cfg), regime, cfg)
    carry = float(data["carry_f"][mi])
    if not math.isfinite(carry):
        carry = 0.0
    adaptive = [float(data[k][si]) for k in ("adaptive_risk_multiplier", "adaptive_efficiency_ratio", "adaptive_vol_ratio")]
    adaptive = [v if math.isfinite(v) else 1.0 for v in adaptive]
    ml_entry = None
    if cfg.ml_model_path:
        ml_entry = dict(data["ml_predictions"][si])
        # Never reuse a prediction across missing candles or after artifact expiry.
        age = timestamp - data["short_ts"][si] - INTERVAL_SECONDS[cfg.short_trend_interval]
        if (not 0 <= age < INTERVAL_SECONDS[cfg.short_trend_interval]
                or timestamp >= ml_entry.get("valid_until", timestamp)):
            ml_entry = {"status": "预测过期或当前K线缺失"}
    return pf.InstrumentSignal(
        symbol, trend, carry, pf.combine_forecast(trend, carry, cfg), vol,
        risk_multiplier=adaptive[0], efficiency_ratio=adaptive[1], range_vol_ratio=adaptive[2],
        short_forecast=short, main_forecast=main, timing_feature=data["timing_features"][si], ml_entry=ml_entry)
