"""
组合层风险分配——把每个标的的"预测(forecast)"变成实际应该持有多少名义仓位。

对应你给的规格里第七、八、九节：
  1) 每个标的先按"如果只有它一个仓位，用它自己的波动率把仓位撑到组合目标波动率，
     再乘以conviction(F/10)"算出一个"原始权重"(raw weight)。
  2) 用 EWMA 协方差矩阵算这一组原始权重实际会产生多大的组合波动率
     sigma_p = sqrt(w' Sigma w) —— 这一步会把"看似分散、实则高度相关"的仓位暴露出来
     （比如同时重仓 BTC/ETH/SOL，可能只是一笔放大的 crypto beta 敞口）。
  3) 用 k = (target_vol * 组合信号置信度) / sigma_p 统一缩放：
     强信号才使用完整风险预算，弱信号保留较小仓位。
  4) 再叠加硬约束：单标的敞口上限、同相关分组敞口上限、总杠杆上限。
  5) 最后用 no-trade buffer 过滤掉"目标仓位相对当前仓位变化很小"的调仓，降低换手成本。

本模块只做纯计算，不碰任何网络/交易所接口。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import vol as vol_mod
from .config import SystematicConfig
from .risk import correlation_group
from .trend import cap_forecast


@dataclass
class InstrumentSignal:
    symbol: str
    trend_forecast: float
    carry_forecast: float
    combined_forecast: float
    vol_annual: float          # 年化波动率(比例，如0.6=60%)
    risk_multiplier: float = 1.0       # 高波动震荡覆盖层：只能在0~1内缩风险
    efficiency_ratio: float = 1.0      # 近期方向效率 ER，诊断用
    range_vol_ratio: float = 1.0       # 1H影线快/慢波动率比，诊断用


@dataclass
class InstrumentTarget:
    symbol: str
    forecast: float
    target_notional: float     # 目标名义敞口(正=多，负=空)，单位:计价货币(如USDT)
    target_weight: float       # target_notional / capital
    raw_weight: float          # 组合缩放/约束前的原始权重(诊断用)
    risk_multiplier: float = 1.0


@dataclass
class PortfolioAllocationResult:
    targets: Dict[str, InstrumentTarget] = field(default_factory=dict)
    portfolio_vol_before_scale: float = 0.0
    scale_factor: float = 1.0
    portfolio_conviction: float = 0.0
    average_risk_multiplier: float = 1.0
    gross_leverage: float = 0.0
    diversification_benefit: float = 0.0   # 1 - (缩放后组合波动/朴素加总波动)，越大说明分散化效果越明显


def combine_forecast(trend_val: float, carry_val: float, cfg: SystematicConfig) -> float:
    raw = cfg.trend_weight * trend_val + cfg.carry_weight * carry_val
    return cap_forecast(raw)


def build_covariance(returns_by_symbol: Dict[str, pd.Series], interval: str,
                      cfg: SystematicConfig) -> pd.DataFrame:
    """从各标的收益率序列(index=时间戳，可以长度/起点不同)构建对齐后的 EWMA 协方差矩阵(年化)。"""
    df = pd.DataFrame(returns_by_symbol)
    cov_per_bar = vol_mod.ewma_covariance_matrix(df, lam=cfg.ewma_lambda)
    return vol_mod.annualize_covariance(cov_per_bar, interval)


def allocate_portfolio(signals: Dict[str, InstrumentSignal], capital: float,
                        cov_annual: pd.DataFrame, cfg: SystematicConfig) -> PortfolioAllocationResult:
    symbols = list(signals.keys())
    if not symbols or capital <= 0:
        return PortfolioAllocationResult()

    target_vol = cfg.target_annual_vol_pct / 100.0

    raw_weight = {}
    for sym in symbols:
        sig = signals[sym]
        v = max(sig.vol_annual, 1e-6)
        raw_weight[sym] = target_vol * (sig.combined_forecast / 10.0) / v

    w = np.array([raw_weight[s] for s in symbols])
    cov = cov_annual.reindex(index=symbols, columns=symbols).fillna(0.0).values
    inst_vols = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    # "完全不分散"的极端对照组：假设所有标的完全同向波动(相关系数=1)，
    # 此时组合波动率就是各标的波动的线性加总；实际组合波动率(考虑真实相关性)
    # 通常会明显低于这个值，两者之比就是"分散化收益"。
    naive_vol = float(np.sum(np.abs(w) * inst_vols))
    port_vol = float(np.sqrt(max(w @ cov @ w, 0.0)))

    # 组合目标波动率必须随整体信号置信度一起变化。旧实现无论 forecast 是1还是10，
    # 都会把组合重新放大到完整 target_vol，导致"弱信号少下注"在组合层被完全抵消。
    # 这里用各标的 |forecast|/10 的 RMS 表示组合置信度：F=10 对应完整风险预算，
    # F=1 只使用约10%的预算；同时仍允许相关性分散带来的合理统一缩放。
    conviction_values = np.array([
        min(abs(signals[s].combined_forecast) / 10.0, 1.0) for s in symbols
    ], dtype=float)
    portfolio_conviction = float(np.sqrt(np.mean(conviction_values ** 2))) if len(conviction_values) else 0.0
    desired_portfolio_vol = target_vol * portfolio_conviction
    scale = (desired_portfolio_vol / port_vol) if port_vol > 1e-8 else 0.0
    w_scaled = w * scale

    # 自适应风险覆盖层必须在组合波动率统一缩放之后再乘。
    # 如果在 raw_weight 阶段就乘，上面 desired_vol/port_vol 会把全部标的
    # 共同的风险折扣再放大回去，等于保护失效。放在这里只会缩仓，不再重新加杠杆。
    risk_multipliers = np.array([
        min(max(float(signals[s].risk_multiplier), 0.0), 1.0) for s in symbols
    ], dtype=float)
    w_scaled = w_scaled * risk_multipliers
    average_risk_multiplier = float(np.mean(risk_multipliers)) if len(risk_multipliers) else 1.0

    # ---- 约束1：单标的敞口上限 ----
    inst_cap = cfg.max_instrument_exposure_pct / 100.0
    w_scaled = np.clip(w_scaled, -inst_cap, inst_cap)

    # ---- 约束2：同相关分组敞口上限 ----
    groups = {s: correlation_group(s) for s in symbols}
    group_sum: Dict[str, float] = {}
    for s, wv in zip(symbols, w_scaled):
        g = groups[s]
        group_sum[g] = group_sum.get(g, 0.0) + abs(wv)
    group_cap = cfg.max_correlated_group_exposure_pct / 100.0
    for i, s in enumerate(symbols):
        g = groups[s]
        gs = group_sum[g]
        if gs > group_cap > 0:
            w_scaled[i] *= group_cap / gs

    # ---- 约束3：组合总杠杆上限 ----
    gross = float(np.sum(np.abs(w_scaled)))
    if gross > cfg.max_leverage and gross > 0:
        w_scaled = w_scaled * (cfg.max_leverage / gross)
        gross = cfg.max_leverage

    targets: Dict[str, InstrumentTarget] = {}
    for i, s in enumerate(symbols):
        notional = float(w_scaled[i]) * capital
        targets[s] = InstrumentTarget(
            symbol=s, forecast=signals[s].combined_forecast, target_notional=notional,
            target_weight=float(w_scaled[i]), raw_weight=raw_weight[s],
            risk_multiplier=float(risk_multipliers[i]),
        )

    div_benefit = 0.0
    if naive_vol > 1e-12:
        div_benefit = 1.0 - min(max(port_vol / naive_vol, 0.0), 1.0)

    return PortfolioAllocationResult(
        targets=targets, portfolio_vol_before_scale=port_vol, scale_factor=scale,
        portfolio_conviction=portfolio_conviction,
        average_risk_multiplier=average_risk_multiplier,
        gross_leverage=float(np.sum(np.abs(w_scaled))), diversification_benefit=div_benefit,
    )


def should_rebalance(current_notional: float, target_notional: float, capital: float,
                      vol_annual: float, cfg: SystematicConfig,
                      risk_multiplier: float = 1.0) -> bool:
    """no-trade buffer：目标仓位相对当前仓位的变化幅度，要超过一定比例才值得调仓，
    否则跳过（降低换手/手续费/滑点损耗）。

    加仓和减仓用的缓冲区宽度不对称：
      - 加仓/开仓(|target| > |current|，同方向或从空仓开仓)：用 no_trade_buffer_pct，
        保持对"趋势变强"的正常灵敏度。
      - 减仓/平到0(|target| < |current|，同方向或平到空仓)：用
        no_trade_buffer_pct * exit_buffer_multiplier（默认宽3倍），让仓位对forecast
        的短暂走弱更"迟钝"一些，不要趋势还没走完就被削减掉——这是专门用来解决
        "平仓太敏感、抓不满一段趋势"的问题。
      - 方向反转(多变空/空变多)：不做特殊处理。曾经为此加过"最短持仓"和"反转状态机"
        两条手工规则，但消融实验证明都是负贡献，已删除。
      - 自适应风险乘数低于 fast-reduce 阈值时，这是风控覆盖层要求显著降暴露，
        不能被为“让趋势走满”设置的3倍退出缓冲拦住；仅此时使用正常 buffer。
        轻微风险折扣仍保留退出缓冲，避免频繁小额调仓放大手续费。
    """
    target_vol = cfg.target_annual_vol_pct / 100.0
    v = max(vol_annual, 1e-6)
    reference_scale = capital * target_vol / v

    same_direction_or_flat = (
        target_notional == 0 or current_notional == 0
        or (current_notional > 0) == (target_notional > 0)
    )
    is_reduction = same_direction_or_flat and abs(target_notional) < abs(current_notional)
    fast_reduce_threshold = float(getattr(cfg, "adaptive_fast_reduce_threshold", 0.45))
    adaptive_reduction = is_reduction and float(risk_multiplier) <= fast_reduce_threshold
    exit_mult = 1.0 if adaptive_reduction else cfg.exit_buffer_multiplier
    buffer_pct = cfg.no_trade_buffer_pct * (exit_mult if is_reduction else 1.0)

    buffer = (buffer_pct / 100.0) * max(reference_scale, 1e-9)
    return abs(target_notional - current_notional) > buffer


"""
    [已移除] 曾经这里有两个手工加的规则：
      - guard_direction_flip()      : 方向反转前要求最短持仓时间
      - apply_reversal_state_machine(): 多→平→确认→空 的反转状态机

    两者都在消融实验里被证明不值得保留（同一批合成行情，多场景平均）：
        最短持仓8小时   : -0.42 个百分点
        反转状态机      : -5.15 个百分点
    它们都不属于任何成熟的系统化交易框架，而是为了"打补丁"手工发明的规则，
    每一条都会引入新的可调参数、扩大过拟合面，实测又拿不出正贡献，所以直接删掉。

    保留下来的规则只有两类：一是有理论依据的(forecast scaling / FDM / 波动率目标 /
    相关性感知分配，都来自 Carver 的框架)，二是经消融实测确有正贡献的
    (should_rebalance 的非对称缓冲区 +5.46pp、regime衰减 +1.81pp)。
"""
