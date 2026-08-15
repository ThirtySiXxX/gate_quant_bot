"""
纯 pandas/numpy 实现的技术指标库，不依赖 ta-lib（避免安装麻烦）。
输入统一为包含 open/high/low/close/volume 列的 DataFrame（按时间升序）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(df: pd.DataFrame, period: int = 14):
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(df)
    atr_ = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    plus_dm_s = pd.Series(plus_dm, index=df.index).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    plus_di = 100 * (plus_dm_s / atr_.replace(0, np.nan))
    minus_di = 100 * (minus_dm_s / atr_.replace(0, np.nan))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_ = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx_.fillna(0.0), plus_di.fillna(0.0), minus_di.fillna(0.0)


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def keltner_channel(df: pd.DataFrame, period: int = 20, atr_mult: float = 1.5):
    mid = ema(df["close"], period)
    rng = atr(df, period)
    upper = mid + atr_mult * rng
    lower = mid - atr_mult * rng
    return upper, mid, lower


def donchian_channel(df: pd.DataFrame, period: int = 20):
    upper = df["high"].rolling(period, min_periods=period).max()
    lower = df["low"].rolling(period, min_periods=period).min()
    mid = (upper + lower) / 2
    return upper, mid, lower


def volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    return sma(df["volume"], period)


# ---------------------- 蜡烛图形态 ----------------------

def is_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_o, prev_c = df["open"].shift(1), df["close"].shift(1)
    o, c = df["open"], df["close"]
    return (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)


def is_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_o, prev_c = df["open"].shift(1), df["close"].shift(1)
    o, c = df["open"], df["close"]
    return (prev_c > prev_o) & (c < o) & (c <= prev_o) & (o >= prev_c)


def is_hammer(df: pd.DataFrame) -> pd.Series:
    body = (df["close"] - df["open"]).abs()
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return (lower_wick > 2 * body) & (upper_wick < body) & (body / rng > 0.05)


def is_shooting_star(df: pd.DataFrame) -> pd.Series:
    body = (df["close"] - df["open"]).abs()
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    return (upper_wick > 2 * body) & (lower_wick < body) & (body / rng > 0.05)


def enrich(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """给15m/1h/4h任意周期的K线批量附加所有需要的指标列。cfg为 StrategyConfig。"""
    out = df.copy()
    out["ema_fast"] = ema(out["close"], cfg.ema_fast)
    out["ema_slow"] = ema(out["close"], cfg.ema_slow)
    out["ema_regime"] = ema(out["close"], cfg.ema_regime)
    out["rsi"] = rsi(out["close"], cfg.rsi_period)
    macd_line, macd_signal, macd_hist = macd(out["close"])
    out["macd"] = macd_line
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist
    out["atr"] = atr(out, cfg.atr_period)
    adx_, plus_di, minus_di = adx(out, cfg.adx_period)
    out["adx"] = adx_
    out["plus_di"] = plus_di
    out["minus_di"] = minus_di
    bb_u, bb_m, bb_l = bollinger_bands(out["close"], cfg.bb_period, cfg.bb_std)
    out["bb_upper"], out["bb_mid"], out["bb_lower"] = bb_u, bb_m, bb_l
    out["bb_width"] = (bb_u - bb_l) / bb_m.replace(0, np.nan)
    kc_u, kc_m, kc_l = keltner_channel(out, cfg.keltner_period, cfg.keltner_atr_mult)
    out["kc_upper"], out["kc_mid"], out["kc_lower"] = kc_u, kc_m, kc_l
    out["vol_ma"] = volume_ma(out, cfg.volume_ma_period)
    out["bull_engulf"] = is_bullish_engulfing(out)
    out["bear_engulf"] = is_bearish_engulfing(out)
    out["hammer"] = is_hammer(out)
    out["shooting_star"] = is_shooting_star(out)
    return out
