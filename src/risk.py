"""
风险控制模块：仓位大小计算、组合风险敞口上限、相关性去重、当日熔断。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import RiskConfig
from .models import Position

# 简单的相关性分组：同组内标的走势高度相关，避免"看似分散、实则同一个方向的仓位"堆叠风险。
CORRELATION_GROUPS: Dict[str, str] = {
    "BTC": "crypto_major", "ETH": "crypto_major", "SOL": "crypto_major",
    "BNB": "crypto_major", "XRP": "crypto_major", "ADA": "crypto_major",
    "AVAX": "crypto_major", "DOGE": "crypto_major", "LTC": "crypto_major",
    "LINK": "crypto_major", "DOT": "crypto_major", "TRX": "crypto_major",
    "XAU": "metal", "XAG": "metal",
}


def correlation_group(symbol: str) -> str:
    base = symbol.split("_")[0].upper()
    return CORRELATION_GROUPS.get(base, base)


def position_size(
    equity: float,
    risk_per_trade_pct: float,
    entry_price: float,
    stop_price: float,
    mark_price: float,
    quanto_multiplier: float,
    max_leverage: float,
    order_size_min: int = 1,
    order_size_max: int = 10_000_000,
) -> int:
    """
    以"止损被打到时最大亏损=账户权益的risk_per_trade_pct%"为原则计算合约张数。
    同时受最大杠杆限制约束（不允许因为止损很近而开出远超杠杆上限的仓位）。
    返回值为正整数张数（方向由调用方决定 size 正负）。
    """
    if entry_price <= 0 or mark_price <= 0 or quanto_multiplier <= 0:
        return 0
    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0:
        return 0

    risk_amount = equity * (risk_per_trade_pct / 100.0)
    raw_size = risk_amount / (stop_distance * quanto_multiplier)

    max_size_by_leverage = (equity * max_leverage) / (mark_price * quanto_multiplier)

    size = min(raw_size, max_size_by_leverage, order_size_max)
    # 按最小下单单位取整（向下取整，宁可少开也不超风险）
    steps = math.floor(size / order_size_min)
    size = steps * order_size_min
    if size < order_size_min:
        return 0
    return int(size)


@dataclass
class RiskDecision:
    allowed: bool
    reason: str


class RiskManager:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg

    def portfolio_heat_pct(self, positions: List[Position], equity: float) -> float:
        """所有持仓若同时止损，占权益的百分比总和。"""
        if equity <= 0:
            return 0.0
        total_risk = 0.0
        for p in positions:
            stop_distance = abs(p.entry_price - p.stop_price)
            total_risk += stop_distance * abs(p.size) * p.quanto_multiplier
        return (total_risk / equity) * 100.0

    def can_open_new(
        self,
        symbol: str,
        positions: List[Position],
        equity: float,
        day_start_equity: float,
        pending_risk_pct: float,
    ) -> RiskDecision:
        if any(p.symbol == symbol for p in positions):
            return RiskDecision(False, "该标的已有持仓")

        if len(positions) >= self.cfg.max_concurrent_positions:
            return RiskDecision(False, "已达最大同时持仓数")

        group = correlation_group(symbol)
        same_group = [p for p in positions if correlation_group(p.symbol) == group]
        if len(same_group) >= self.cfg.max_correlated_positions:
            return RiskDecision(False, f"相关性分组[{group}]持仓已达上限")

        current_heat = self.portfolio_heat_pct(positions, equity)
        if current_heat + pending_risk_pct > self.cfg.max_portfolio_heat_pct:
            return RiskDecision(False, "组合风险敞口(portfolio heat)将超上限")

        if day_start_equity > 0:
            day_pnl_pct = (equity - day_start_equity) / day_start_equity * 100.0
            if day_pnl_pct <= -abs(self.cfg.daily_loss_limit_pct):
                return RiskDecision(False, "当日亏损触发熔断，停止开新仓")

        return RiskDecision(True, "OK")

    def daily_circuit_breaker_hit(self, equity: float, day_start_equity: float) -> bool:
        if day_start_equity <= 0:
            return False
        day_pnl_pct = (equity - day_start_equity) / day_start_equity * 100.0
        return day_pnl_pct <= -abs(self.cfg.daily_loss_limit_pct)
