"""
对冲触发/解除的纯决策逻辑（不做任何下单/网络IO，engine.py 负责执行）。

设计思路：
  1) 主仓(primary)出现明显浮亏（达到止损距离的 trigger_loss_r 倍）时，
     如果高周期市场状态已经走弱/反转（不再支持原方向），
     不直接止损离场，而是在同一合约开一条反方向的对冲腿(hedge)，
     把当前浮亏"锁住"，避免further恶化，同时保留后续反抽修复的可能性。
  2) 对冲不是无限期的：
       - 主仓浮亏收窄回 unwind_recovery_r 以内 -> 说明行情在修复，撤销对冲；
       - 达到 max_hedge_bars 仍未修复 -> 强制了结，避免占用保证金和持续付手续费/资金费；
       - 行情继续恶化超过"灾难阈值"(2.5倍原止损距离) -> 直接双腿平仓止损，避免对冲失效仍扩大亏损。
"""
from __future__ import annotations

from typing import Optional, Tuple

from .config import HedgeConfig
from .models import Position


def compute_r_multiple(pos: Position, mark_price: float) -> float:
    """当前浮动盈亏相对初始止损距离的R倍数，负数=亏损，正数=盈利。"""
    stop_distance = abs(pos.entry_price - pos.initial_stop_price)
    if stop_distance <= 0:
        return 0.0
    direction = 1 if pos.side == "long" else -1
    return (mark_price - pos.entry_price) * direction / stop_distance


def should_trigger_hedge(primary: Position, mark_price: float, current_regime: str,
                          cfg: HedgeConfig, active_hedge_count: int) -> Tuple[bool, str]:
    if not cfg.enabled:
        return False, "对冲功能已关闭"
    if primary.linked_id:
        return False, "该主仓已有对冲"
    if active_hedge_count >= cfg.max_active_hedges:
        return False, "同时对冲组数已达上限"

    r = compute_r_multiple(primary, mark_price)
    if r > -abs(cfg.trigger_loss_r):
        return False, f"浮亏未达触发阈值(当前{r:.2f}R)"

    if cfg.require_regime_flip:
        aligned = (primary.side == "long" and current_regime == "trend_up") or \
                  (primary.side == "short" and current_regime == "trend_down")
        if aligned:
            return False, "高周期趋势仍支持主仓方向，暂不对冲"

    return True, f"浮亏{r:.2f}R且趋势走弱，触发对冲"


def should_unwind_hedge(primary: Position, hedge: Position, mark_price: float,
                         cfg: HedgeConfig) -> Tuple[bool, str, str]:
    """返回 (是否需要处理, 处理方式, 原因)。
    处理方式: 'resume'=只平掉对冲腿、主仓恢复正常管理 | 'close_both'=主仓+对冲腿一起平仓了结。
    """
    r = compute_r_multiple(primary, mark_price)
    bars_held = int(hedge.holding_seconds // (15 * 60))

    if r >= -abs(cfg.unwind_recovery_r):
        return True, "resume", f"主仓浮亏已收窄至{r:.2f}R，撤销对冲恢复正常管理"

    if bars_held >= cfg.max_hedge_bars:
        return True, "close_both", "对冲持续时间达到上限，强制了结两条腿"

    stop_distance = abs(primary.entry_price - primary.initial_stop_price)
    direction = 1 if primary.side == "long" else -1
    disaster_price = primary.entry_price - direction * stop_distance * 2.5
    disaster_hit = (primary.side == "long" and mark_price <= disaster_price) or \
                   (primary.side == "short" and mark_price >= disaster_price)
    if disaster_hit:
        return True, "close_both", "行情持续大幅恶化(超2.5倍原止损距离)，触发灾难保护，双腿平仓"

    return False, "", ""


def hedge_size(primary: Position, hedge_ratio: float) -> int:
    return max(int(abs(primary.size) * hedge_ratio), 0)
