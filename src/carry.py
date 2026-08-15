"""
Carry 信号——对永续合约而言，Carry 就是资金费率(funding rate)。

传统期货的 Carry 来自近月/远月合约价差(Koijen/Moskowitz/Pedersen/Vrugt 的跨资产研究)，
但 Gate 上交易的都是永续合约，没有到期日、没有近月/远月价差，
其"持有成本/收益"完全体现在资金费率机制里：
    多头在资金费率为正时付钱给空头（相当于持有成本，carry为负）；
    资金费率为负时空头付钱给多头（相当于持有收益，carry为正）。
所以"如果做多，不考虑价格变化，纯粹靠资金费率能赚多少"这件事，
就是永续合约版本的 Carry，方向定义为：
    annualized_carry_if_long = -funding_rate * 每年资金费结算次数

关于历史数据：Gate 是提供历史资金费率接口的
(list_futures_funding_rate_history，见 exchange_gate.get_funding_rate_history)，
所以回测应该用 carry_forecast_series_from_history() 传入真实的逐期历史费率。
资金费率在行情转换时经常反号甚至差一个数量级，用"下载那一刻的实时费率"当常数
贴一整段历史会让 carry 的历史贡献严重失真。
carry_forecast_series() 保留了常数费率的版本，供实盘每个tick用当时最新费率计算，
以及历史费率拿不到时的降级回退。
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from . import vol as vol_mod
from .config import SystematicConfig
from .trend import cap_forecast, forecast_scale_causal

SECONDS_PER_YEAR = 365.0 * 86400.0


def annualized_funding_rate(funding_rate: float, funding_interval_sec: float) -> float:
    """把单次资金费率年化(资金费率本身就是"每次结算"的比例，乘以一年结算次数)。"""
    if funding_interval_sec <= 0:
        return 0.0
    events_per_year = SECONDS_PER_YEAR / funding_interval_sec
    return funding_rate * events_per_year


def _finalize(raw: pd.Series, cfg: SystematicConfig) -> pd.Series:
    scaled = forecast_scale_causal(raw, lookback=cfg.carry_scale_lookback,
                                    min_periods=min(cfg.forecast_scale_min_periods, cfg.carry_scale_lookback))
    return cap_forecast(scaled)


def carry_forecast_series(close: pd.Series, interval: str, funding_rate: float,
                           funding_interval_sec: float, cfg: SystematicConfig) -> pd.Series:
    """常数资金费率版本：实盘/模拟盘每个tick调用时传入当时最新的费率，
    序列末端的值就是"以当前费率计算的carry"。回测请优先用下面的
    carry_forecast_series_from_history()。"""
    annual_carry_if_long = -annualized_funding_rate(funding_rate, funding_interval_sec)
    ann_vol = vol_mod.price_vol_annualized(close, interval, lam=cfg.ewma_lambda)
    raw = annual_carry_if_long / ann_vol.replace(0, float("nan"))
    return _finalize(raw, cfg)


def align_funding_to_bars(funding_df: pd.DataFrame, bar_timestamps) -> pd.Series:
    """把"每次资金费结算一条"的稀疏历史费率，按因果方式对齐到K线时间轴上：
    每根K线取"该K线时间点之前(含)最近一次已经结算过的费率"，
    没有更早记录的早期K线用 NaN(后续会被 forecast scaling 的 min_periods 自然过滤掉)。

    严格因果：只用当前时刻已经发生过的费率，不会用到未来的费率。
    """
    ts = np.asarray(bar_timestamps, dtype=float)
    if funding_df is None or len(funding_df) == 0:
        return pd.Series(np.full(len(ts), np.nan), index=range(len(ts)))
    f = funding_df.sort_values("timestamp")
    f_ts = f["timestamp"].values.astype(float)
    f_rate = f["funding_rate"].values.astype(float)
    idx = np.searchsorted(f_ts, ts, side="right") - 1
    out = np.where(idx >= 0, f_rate[np.clip(idx, 0, len(f_rate) - 1)], np.nan)
    return pd.Series(out, index=range(len(ts)))


def carry_forecast_series_from_history(close: pd.Series, interval: str, funding_df: pd.DataFrame,
                                        funding_interval_sec: float, cfg: SystematicConfig,
                                        bar_timestamps=None,
                                        fallback_funding_rate: Optional[float] = None) -> pd.Series:
    """时变资金费率版本(回测用)：用真实的逐期历史费率算 carry。

    funding_df: DataFrame(columns=[timestamp, funding_rate])，来自
                data_fetcher.fetch_funding_history()。
    bar_timestamps: close 对应的K线时间戳序列(秒)。
    fallback_funding_rate: 历史费率为空时回退用的常数费率(通常传合约当前费率)。
    """
    if funding_df is None or len(funding_df) == 0 or bar_timestamps is None:
        return carry_forecast_series(close, interval, float(fallback_funding_rate or 0.0),
                                      funding_interval_sec, cfg)

    rate_per_bar = align_funding_to_bars(funding_df, bar_timestamps)
    rate_per_bar.index = close.index
    events_per_year = SECONDS_PER_YEAR / funding_interval_sec if funding_interval_sec > 0 else 0.0
    annual_carry_if_long = -rate_per_bar * events_per_year

    ann_vol = vol_mod.price_vol_annualized(close, interval, lam=cfg.ewma_lambda)
    raw = annual_carry_if_long / ann_vol.replace(0, float("nan"))
    return _finalize(raw, cfg)
