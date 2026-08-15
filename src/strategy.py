"""
多因子、多周期confluence策略。

设计思路（严格按需求：15m判定开仓，更大周期看趋势）：
  1) 4h：市场状态过滤（regime）——趋势 or 震荡。用 EMA排列 + ADX 判定。
  2) 1h：中周期趋势确认——价格与均线关系、MACD柱方向是否与4h一致。
  3) 15m：入场触发——
        趋势模式：均线/肯特纳通道回踩 + RSI从超卖/超买区域回摆 + 量能确认 + K线形态确认。
        震荡模式：布林带外轨反转 + RSI极值 + K线反转形态，逆势均值回归，止损更紧。
  4) 成本感知过滤：结合手续费、滑点、预估资金费，计算"净预期R"，
     低于阈值直接放弃这笔交易——防止磨损把利润吃掉。

综合打分 0-100，达到 min_score_to_enter 才会开仓；返回 Signal 供 engine 使用。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .models import Signal
from . import indicators as ind


def compute_regime(df4h: pd.DataFrame, cfg: StrategyConfig) -> str:
    if len(df4h) < cfg.ema_regime + 5:
        return "range"
    last = df4h.iloc[-1]
    ema_fast, ema_slow, ema_reg = last["ema_fast"], last["ema_slow"], last["ema_regime"]
    adx_v = last["adx"]

    trending = adx_v >= cfg.adx_trend_threshold
    if trending and ema_fast > ema_slow > ema_reg:
        return "trend_up"
    if trending and ema_fast < ema_slow < ema_reg:
        return "trend_down"
    return "range"


def _trend_signal(symbol: str, df15: pd.DataFrame, df1h: pd.DataFrame, regime: str, cfg: StrategyConfig) -> tuple[str, float, str]:
    """趋势跟随子策略：返回 (action, score, reason)"""
    last15 = df15.iloc[-1]
    prev15 = df15.iloc[-2]
    last1h = df1h.iloc[-1]

    bias_long = regime == "trend_up"
    bias_short = regime == "trend_down"
    if not (bias_long or bias_short):
        return "none", 0.0, "非趋势市场"

    score = 0.0
    reasons = []

    # 4h regime 已经决定方向，占25分基础分
    score += 25
    reasons.append(f"4h regime={regime}")

    # 1h 中周期确认 20分
    if bias_long and last1h["close"] > last1h["ema_fast"] and last1h["macd_hist"] > 0:
        score += 20
        reasons.append("1h多头共振")
    elif bias_short and last1h["close"] < last1h["ema_fast"] and last1h["macd_hist"] < 0:
        score += 20
        reasons.append("1h空头共振")
    else:
        reasons.append("1h未共振(减分)")

    # 15m 回踩入场触发 25分
    pullback_long = (
        last15["low"] <= last15["ema_fast"] * 1.002
        and last15["close"] > last15["ema_fast"] * 0.998
        and prev15["rsi"] < cfg.rsi_oversold + 10
        and last15["rsi"] > prev15["rsi"]
    )
    pullback_short = (
        last15["high"] >= last15["ema_fast"] * 0.998
        and last15["close"] < last15["ema_fast"] * 1.002
        and prev15["rsi"] > cfg.rsi_overbought - 10
        and last15["rsi"] < prev15["rsi"]
    )
    if bias_long and pullback_long:
        score += 25
        reasons.append("15m回踩EMA快线+RSI回摆")
    elif bias_short and pullback_short:
        score += 25
        reasons.append("15m回踩EMA快线+RSI回摆(空)")

    # K线形态 15分
    if bias_long and (last15["bull_engulf"] or last15["hammer"]):
        score += 15
        reasons.append("看涨反转形态")
    elif bias_short and (last15["bear_engulf"] or last15["shooting_star"]):
        score += 15
        reasons.append("看跌反转形态")

    # 量能确认 15分
    if last15["volume"] > last15["vol_ma"] * cfg.volume_spike_mult:
        score += 15
        reasons.append("放量确认")

    action = "long" if bias_long else "short"
    return action, score, "; ".join(reasons)


def _range_signal(symbol: str, df15: pd.DataFrame, cfg: StrategyConfig) -> tuple[str, float, str]:
    """震荡市均值回归子策略"""
    last15 = df15.iloc[-1]
    prev15 = df15.iloc[-2]
    reasons = []
    score = 0.0

    touch_upper = last15["high"] >= last15["bb_upper"]
    touch_lower = last15["low"] <= last15["bb_lower"]

    action = "none"
    if touch_lower and last15["rsi"] < cfg.rsi_oversold:
        action = "long"
        score += 30
        reasons.append("触布林下轨+RSI超卖")
        if last15["bull_engulf"] or last15["hammer"]:
            score += 30
            reasons.append("反转K线")
        if last15["adx"] < cfg.adx_trend_threshold:
            score += 20
            reasons.append("ADX确认震荡")
        if last15["volume"] < last15["vol_ma"] * cfg.volume_spike_mult:
            score += 20
            reasons.append("非放量突破(排除趋势突破假象)")
    elif touch_upper and last15["rsi"] > cfg.rsi_overbought:
        action = "short"
        score += 30
        reasons.append("触布林上轨+RSI超买")
        if last15["bear_engulf"] or last15["shooting_star"]:
            score += 30
            reasons.append("反转K线")
        if last15["adx"] < cfg.adx_trend_threshold:
            score += 20
            reasons.append("ADX确认震荡")
        if last15["volume"] < last15["vol_ma"] * cfg.volume_spike_mult:
            score += 20
            reasons.append("非放量突破(排除趋势突破假象)")

    return action, score, "; ".join(reasons)


def estimate_cost_in_price(
    entry_price: float,
    taker_fee_rate: float,
    slippage_bps: float,
    funding_rate: float,
    expected_holding_sec: float,
    funding_interval_sec: float,
) -> float:
    """估算一笔交易的往返成本（换算成价格单位），用于净收益过滤。"""
    round_trip_fee = 2 * taker_fee_rate * entry_price
    round_trip_slippage = 2 * (slippage_bps / 10000.0) * entry_price
    expected_funding_events = max(expected_holding_sec / max(funding_interval_sec, 1.0), 0.0)
    expected_funding_cost = abs(funding_rate) * entry_price * expected_funding_events
    return round_trip_fee + round_trip_slippage + expected_funding_cost


def compute_signal(
    symbol: str,
    df15: pd.DataFrame,
    df1h: pd.DataFrame,
    df4h: pd.DataFrame,
    cfg: StrategyConfig,
    taker_fee_rate: float,
    slippage_bps: float,
    funding_rate: float,
    funding_interval_sec: float,
    time_stop_bars: int,
    atr_stop_multiplier: float,
    tp1_r_multiple: float,
    min_net_edge_r: float,
) -> Signal:
    min_len = max(cfg.ema_regime, cfg.bb_period, cfg.atr_period) + 5
    if len(df15) < min_len or len(df1h) < min_len or len(df4h) < cfg.ema_regime + 5:
        return Signal(symbol, "none", 0, "range", "数据不足", 0, 0, 0)

    regime = compute_regime(df4h, cfg)
    last15 = df15.iloc[-1]
    entry_price = float(last15["close"])
    atr_val = float(last15["atr"]) if not np.isnan(last15["atr"]) else 0.0
    if atr_val <= 0:
        return Signal(symbol, "none", 0, regime, "ATR无效", entry_price, entry_price, 0)

    if regime in ("trend_up", "trend_down"):
        action, score, reason = _trend_signal(symbol, df15, df1h, regime, cfg)
    else:
        action, score, reason = _range_signal(symbol, df15, cfg)

    if action == "none":
        return Signal(symbol, "none", score, regime, reason or "无信号", entry_price, entry_price, atr_val)

    stop_mult = atr_stop_multiplier if regime != "range" else atr_stop_multiplier * 0.75
    if action == "long":
        stop_price = entry_price - atr_val * stop_mult
    else:
        stop_price = entry_price + atr_val * stop_mult
    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0:
        return Signal(symbol, "none", score, regime, "止损距离无效", entry_price, entry_price, atr_val)

    expected_holding_sec = time_stop_bars * 15 * 60
    cost_price = estimate_cost_in_price(
        entry_price, taker_fee_rate, slippage_bps, funding_rate,
        expected_holding_sec, funding_interval_sec,
    )
    cost_r = cost_price / stop_distance
    net_edge_r = tp1_r_multiple - cost_r

    if score < 0:
        score = 0.0

    sig = Signal(
        symbol=symbol, action=action, score=score, regime=regime,
        reason=f"{reason} | 预估成本={cost_r:.2f}R 净预期={net_edge_r:.2f}R",
        entry_price=entry_price, stop_price=stop_price, atr=atr_val,
        net_edge_r=net_edge_r,
    )

    if net_edge_r < min_net_edge_r:
        sig.action = "none"
        sig.reason += " | 净收益不足成本，放弃"

    return sig
