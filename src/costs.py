"""
交易成本模型：手续费、资金费（含黄金等大宗商品永续合约的"过夜"性质费用）、滑点。

说明：Gate.io 的 XAU_USDT / XAG_USDT 等贵金属合约本质上也是"永续合约"，
没有传统外汇/CFD那种按自然日收取的隔夜利息(overnight swap)，
而是和加密货币永续合约一样，通过"资金费率(funding rate)"机制、
按固定间隔（通常8小时）在多空双方之间转移资金，效果上等价于"持仓过夜的资金成本"。
本模块统一按资金费率机制处理，engine 里会按 funding_interval 定时结算。
"""
from __future__ import annotations


def taker_fee(notional: float, taker_fee_rate: float) -> float:
    return abs(notional) * taker_fee_rate


def maker_fee(notional: float, maker_fee_rate: float) -> float:
    return abs(notional) * maker_fee_rate


def slippage_adjusted_price(price: float, side: str, slippage_bps: float, is_entry: bool) -> float:
    """
    模拟滑点：买入/开多在成交价上方多付一点，卖出/开空在下方少收一点，
    平仓方向相反，永远对交易者不利，贴近真实成交体验。
    side: 'long' | 'short'
    """
    factor = slippage_bps / 10000.0
    worse_up = side == "long" if is_entry else side == "short"
    if worse_up:
        return price * (1 + factor)
    return price * (1 - factor)


def funding_fee(notional: float, funding_rate: float, side: str) -> float:
    """
    资金费结算：多头在正资金费率时付钱给空头（成本为正，即亏钱），
    空头则收钱（成本为负，即赚钱）；费率为负时相反。
    返回值为"该仓位这次结算产生的盈亏"（正=亏损，负=盈利，与fees_paid累加口径一致，
    这里返回的是"成本"，调用方在计算净盈亏时应做 pnl -= cost）。
    """
    signed = notional * funding_rate
    if side == "long":
        return signed
    return -signed


def round_trip_cost_estimate(
    entry_price: float,
    taker_fee_rate: float,
    slippage_bps: float,
    funding_rate: float,
    expected_holding_sec: float,
    funding_interval_sec: float,
) -> float:
    """粗略估算一笔交易的总磨损（以价格单位表示），供策略层做净收益过滤使用。"""
    fee_cost = 2 * taker_fee_rate * entry_price
    slip_cost = 2 * (slippage_bps / 10000.0) * entry_price
    funding_events = max(expected_holding_sec / max(funding_interval_sec, 1.0), 0.0)
    funding_cost = abs(funding_rate) * entry_price * funding_events
    return fee_cost + slip_cost + funding_cost
