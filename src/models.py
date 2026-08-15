"""公用数据结构。"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


def now_ts() -> float:
    return time.time()


@dataclass
class Signal:
    symbol: str
    action: str              # 'long' | 'short' | 'none'
    score: float
    regime: str               # 'trend_up' | 'trend_down' | 'range'
    reason: str
    entry_price: float
    stop_price: float
    atr: float
    net_edge_r: float = 0.0


@dataclass
class Position:
    id: str
    symbol: str
    side: str                 # 'long' | 'short'
    size: float                # 合约张数，有符号：多头为正，空头为负，与交易所下单方向约定一致
    entry_price: float
    stop_price: float
    initial_stop_price: float
    take_profit_1: float
    leverage: float
    quanto_multiplier: float
    open_time: float = field(default_factory=now_ts)
    bars_held: int = 0
    tp1_done: bool = False
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    fees_paid: float = 0.0
    funding_paid: float = 0.0
    realized_partial_pnl: float = 0.0   # TP1等部分减仓已实现的毛盈亏，平仓时并入总盈亏
    last_funding_settle_ts: float = field(default_factory=now_ts)
    regime: str = ""
    reason: str = ""
    role: str = "primary"       # 'primary'=正常策略仓位 | 'hedge'=对冲仓位
    linked_id: Optional[str] = None   # primary持仓存对应hedge的id；hedge持仓存对应primary的id
    hedge_open_time: Optional[float] = None  # 对冲开启时间（仅role='hedge'时使用）

    @property
    def holding_seconds(self) -> float:
        return now_ts() - self.open_time

    @property
    def notional(self) -> float:
        return abs(self.size) * self.mark_price * self.quanto_multiplier

    @property
    def position_key(self) -> str:
        return f"{self.symbol}|{self.side}"


@dataclass
class Trade:
    id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float
    open_time: float
    close_time: float
    pnl: float                 # 净盈亏（已扣除手续费与资金费）
    gross_pnl: float
    fees_paid: float
    funding_paid: float
    exit_reason: str
    role: str = "primary"

    @property
    def holding_seconds(self) -> float:
        return self.close_time - self.open_time


def new_id() -> str:
    return uuid.uuid4().hex[:12]
