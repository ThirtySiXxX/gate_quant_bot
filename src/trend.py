"""
多周期 EWMAC(指数加权移动平均交叉) 趋势信号。

对应你确认的多周期方案：
  - 短趋势：1H 收盘价上算 EWMAC(8,32)/(16,64)/(32,128)/(64,256)
  - 主趋势：4H 收盘价上同样算这四组
  - 大周期 Regime：1D EMA(21/55/200)+ADX(14) 判定趋势/震荡，对最终趋势预测做门控/衰减

处理流程（每一组 EWMAC）：
  1. raw = EMA_fast(P) - EMA_slow(P)
  2. vol-normalize：raw / sigma_P （sigma_P = 价格单位的EWMA波动率，两边量纲匹配）
  3. forecast scaling：让历史平均绝对值趋近10（纯因果，只用截至上一根K线的历史）
  4. cap 到 [-20, 20]

多组子预测先等权合并成"短趋势"/"主趋势"两个分组预测(合并时用一个简化版 Forecast
Diversification Multiplier 补偿子信号之间的相关性)，短趋势和主趋势再按权重合并成
"原始趋势预测"，最后用日线 regime 做门控。

本模块只做纯计算(pandas/numpy)，不碰任何网络/交易所接口，可以脱离交易所独立单测。
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

from . import indicators as ind
from . import vol as vol_mod
from .config import SystematicConfig

FORECAST_CAP = 20.0
FORECAST_TARGET_ABS_MEAN = 10.0


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def cap_forecast(f, cap: float = FORECAST_CAP):
    if isinstance(f, pd.Series):
        return f.clip(lower=-cap, upper=cap)
    return max(-cap, min(cap, f))


def ewmac_raw(close: pd.Series, fast: int, slow: int, interval: str, lam: float) -> pd.Series:
    """单组 EWMAC 的波动率归一化原始信号(未做 forecast scaling/cap)。"""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    sigma_p = vol_mod.price_vol_in_price_units(close, interval, lam=lam)
    sigma_p = sigma_p.replace(0, np.nan)
    return (ema_fast - ema_slow) / sigma_p


def forecast_scale_causal(raw: pd.Series, target_abs_mean: float = FORECAST_TARGET_ABS_MEAN,
                           lookback: int = 2500, min_periods: int = 100) -> pd.Series:
    """让原始信号的历史平均绝对值趋近 target_abs_mean，纯因果(t时刻的缩放系数只用t-1及更早数据)，
    避免用到未来数据导致回测结果过于乐观。用滚动窗口而不是无限expanding，让缩放系数能
    适应波动率结构性变化（比如某标的从"死气沉沉"变成"剧烈波动"，缩放系数也该跟着变）。"""
    abs_raw = raw.abs()
    rolling_mean_abs = abs_raw.rolling(lookback, min_periods=min_periods).mean().shift(1)
    # 用极小值兜底而不是把0替换成NaN：如果原始信号长期恒为0(比如资金费率恰好是0)，
    # 缩放后的结果也应该保持0，而不是被NaN污染整个序列。
    denom = rolling_mean_abs.clip(lower=1e-12)
    scalar = (target_abs_mean / denom).clip(lower=0.1, upper=100.0)
    return raw * scalar


def compute_ewmac_group(close: pd.Series, interval: str, cfg: SystematicConfig) -> pd.DataFrame:
    """返回该周期(如1H)所有 EWMAC 子预测(已缩放+cap)，列名如 'ewmac_8_32'。"""
    out = {}
    for fast, slow in cfg.ewmac_horizons:
        raw = ewmac_raw(close, fast, slow, interval, lam=cfg.ewma_lambda)
        scaled = forecast_scale_causal(raw, lookback=cfg.forecast_scale_lookback,
                                        min_periods=cfg.forecast_scale_min_periods)
        out[f"ewmac_{fast}_{slow}"] = cap_forecast(scaled)
    return pd.DataFrame(out, index=close.index)


def fdm_series(sub_df: pd.DataFrame, cfg: SystematicConfig) -> pd.Series:
    """简化版 Forecast Diversification Multiplier：
        FDM_t = clip(1 / sqrt(w' Corr_t w), 1.0, fdm_max)，w 为等权重。
    Corr_t 用截至 t-1（纯因果）的滚动窗口相关系数矩阵估计。这个值变化很慢，
    工程上每根K线都重算一次矩阵开销可以接受(子信号数通常<=8)。
    """
    n = sub_df.shape[1]
    if n <= 1:
        return pd.Series(1.0, index=sub_df.index)
    w = np.full(n, 1.0 / n)
    shifted = sub_df.shift(1)
    vals = np.ones(len(sub_df))
    for i in range(len(sub_df)):
        if i < cfg.fdm_min_periods:
            continue
        window = shifted.iloc[max(0, i - cfg.fdm_lookback + 1): i + 1].dropna()
        if len(window) < cfg.fdm_min_periods:
            continue
        corr = np.nan_to_num(window.corr().values, nan=0.0)
        denom = float(w @ corr @ w)
        if denom > 1e-8:
            vals[i] = min(cfg.fdm_max, max(1.0, 1.0 / np.sqrt(denom)))
    return pd.Series(vals, index=sub_df.index)


def group_trend_forecast(close: pd.Series, interval: str, cfg: SystematicConfig) -> pd.Series:
    """某一周期(1H或4H)的组合趋势预测：多组EWMAC等权合并 * FDM，再cap一次。"""
    sub = compute_ewmac_group(close, interval, cfg)
    combined = sub.mean(axis=1)
    fdm = fdm_series(sub, cfg)
    return cap_forecast(combined * fdm)


def daily_regime_series(df1d: pd.DataFrame, cfg: SystematicConfig) -> pd.Series:
    """日线 EMA(21/55/200) + ADX(14) 市场状态：'trend_up' | 'trend_down' | 'range'。"""
    out = df1d.copy()
    out["_ema_fast"] = _ema(out["close"], cfg.regime_ema_fast)
    out["_ema_slow"] = _ema(out["close"], cfg.regime_ema_slow)
    out["_ema_long"] = _ema(out["close"], cfg.regime_ema_long)
    adx_val, _, _ = ind.adx(out, cfg.regime_adx_period)
    out["_adx"] = adx_val

    ef, es, el, adx_v = out["_ema_fast"].values, out["_ema_slow"].values, out["_ema_long"].values, out["_adx"].values
    n = len(out)
    regimes: List[str] = ["range"] * n
    for i in range(n):
        if np.isnan(el[i]) or np.isnan(adx_v[i]):
            regimes[i] = "range"
            continue
        trending = adx_v[i] >= cfg.regime_adx_trend_threshold
        if trending and ef[i] > es[i] > el[i]:
            regimes[i] = "trend_up"
        elif trending and ef[i] < es[i] < el[i]:
            regimes[i] = "trend_down"
        else:
            regimes[i] = "range"
    return pd.Series(regimes, index=df1d.index)


def apply_regime_gate(forecast: float, regime: str, cfg: SystematicConfig) -> float:
    if regime == "range":
        return forecast * cfg.regime_range_dampen
    if regime == "trend_up" and forecast < 0:
        return forecast * cfg.regime_oppose_dampen
    if regime == "trend_down" and forecast > 0:
        return forecast * cfg.regime_oppose_dampen
    return forecast


def combine_trend(short_val: float, main_val: float, cfg: SystematicConfig) -> float:
    raw = cfg.short_trend_weight * short_val + cfg.main_trend_weight * main_val
    return cap_forecast(raw)
