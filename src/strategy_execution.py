"""Shared signal-to-order policy for live, paper and historical execution.

No exchange I/O or fills here. Adapters supply observed prices, account budgets
and contract metadata; all strategy decisions and sizing use these functions.
"""
from dataclasses import dataclass
import math
from typing import Optional, List, Tuple

from . import portfolio as pf
from .execution_timing import TimingConfig, TimingDecision
from .position_sizing import entry_ticket


@dataclass
class ExecutionPlan:
    decision: TimingDecision
    timing_config: TimingConfig
    model_target: float
    target_notional: float
    rebalance: bool
    fixed_margin: bool
    needs_entry_ticket: bool
    allow_increase: bool
    block_reason: str = ""


def decide_execution(symbol, target, signal, current_notional, equity, cfg,
                     timing, sizing, allow_increase=True, force_risk_reduction=False):
    """One path for direction, timing, buffers, fixed-ticket exits and risk gates."""
    timing_cfg = TimingConfig(**cfg.execution_timing).for_symbol(symbol)
    fixed = cfg.position_sizing_mode == "fixed_margin"
    raw = -target.target_notional if cfg.invert_direction else target.target_notional
    model_current = sizing.model_current(symbol, current_notional, raw) if fixed else current_notional
    direction = -1 if cfg.invert_direction else 1
    decision = timing.decide(symbol, raw, model_current, signal.combined_forecast,
                             signal.short_forecast * direction, signal.main_forecast * direction,
                             signal.timing_feature, timing_cfg)
    # An entry gate (daily circuit) must not rewrite the strategy's exit policy.
    # Explicit data-degradation reduction can bypass smoothing/buffers, but must
    # never weaken an existing full exit (ATR, weak-signal or reversal).
    if (force_risk_reduction and decision.target_notional != 0
            and (raw == 0 or model_current * raw > 0 and abs(raw) < abs(model_current))
            and abs(raw) <= abs(decision.target_notional)):
        decision = TimingDecision(raw, True, "风险降级，优先执行减仓")
    rebalance = decision.force_rebalance or pf.should_rebalance(
        model_current, decision.target_notional, equity, signal.vol_annual, cfg,
        risk_multiplier=target.risk_multiplier)
    model_target = timing.execution_target(decision, model_current, timing_cfg)
    actual_target = sizing.held_target(symbol, model_target, current_notional) if fixed and current_notional else model_target
    reason = decision.reason if not model_target else ""
    if not rebalance:
        reason = reason or "目标为零或未通过仓位缓冲"
    elif not allow_increase and not current_notional and model_target:
        reason = "风险降级/熔断，禁止开仓"
    # ML gates only fresh entries; its failure or disagreement must not replace exits.
    if cfg.ml_model_path and not current_notional and model_target:
        prediction = signal.ml_entry or {}
        side = "long" if model_target > 0 else "short"
        probability = prediction.get(side, -1)
        if not isinstance(probability, (int, float)) or not math.isfinite(probability):
            probability = -1
        if prediction.get("status") != "ok" or probability < cfg.ml_min_entry_probability:
            reason = "ML入场过滤：" + (prediction.get("status", "缺少预测") if prediction.get("status") != "ok"
                                    else f"方向概率{probability:.3f}低于{cfg.ml_min_entry_probability:.3f}")
            model_target = actual_target = 0.0
            rebalance = False
    return ExecutionPlan(decision, timing_cfg, model_target, actual_target, rebalance, fixed,
                         bool(fixed and not current_notional and model_target and rebalance and allow_increase),
                         allow_increase, reason)


def build_order_plan(symbol, plan, current_side, current_size, price, contract,
                     fee_rate, slippage_bps, *, budget=None, tiers=None):
    """Convert the shared decision into quantities; entry budgets are fresh per ticket."""
    if not plan.rebalance:
        return [], None
    if plan.needs_entry_ticket:
        if budget is None:
            raise ValueError("缺少开仓时的账户权益/可用额度")
        ticket = entry_ticket(symbol, budget["equity"], price, contract, tiers,
                              budget["available"], fee_rate, slippage_bps)
        return [("open", "long" if plan.model_target > 0 else "short", ticket.quantity)], ticket
    actions = plan_orders(current_side, current_size, plan.target_notional, price,
                          contract["quanto_multiplier"], contract.get("order_size_min", 1))
    if not plan.allow_increase:
        actions = [a for a in actions if a[0] != "open"]
    return actions, None


def record_fill(timing, symbol, plan, feature, *, entry_price=0.0, pnl=0.0,
                closed=False, direction=0):
    """Apply identical timing feedback after a confirmed fill in either adapter."""
    if plan.timing_config.enabled and feature:
        timing.record_fill(symbol, feature["bar_ts"], pnl, closed, direction, feature,
                           entry_price=entry_price)


def notional_to_contracts(notional: float, price: float, quanto_multiplier: float) -> int:
    if price <= 0 or quanto_multiplier <= 0:
        return 0
    return int(round(abs(notional) / (price * quanto_multiplier)))


def plan_orders(current_side: Optional[str], current_size: int, target_notional: float,
                 price: float, quanto_multiplier: float, order_size_min: int) -> List[Tuple[str, str, int]]:
    """把"当前持仓状态"和"目标名义敞口"翻译成需要执行的动作列表：
        [(action, side, qty), ...]，action in {'open','reduce','close'}。
    纯函数，不碰任何网络/交易所接口，方便单测。
    """
    order_size_min = max(1, int(order_size_min or 1))
    target_side = None
    if target_notional > 0:
        target_side = "long"
    elif target_notional < 0:
        target_side = "short"
    target_qty = notional_to_contracts(target_notional, price, quanto_multiplier)
    # 按最小下单单位向下取整(和 risk.py 的仓位计算口径一致)，宁可少开也不超出目标风险
    target_qty = (target_qty // order_size_min) * order_size_min
    if target_qty < order_size_min:
        target_qty = 0
        target_side = None

    actions: List[Tuple[str, str, int]] = []

    if current_side and target_side and current_side != target_side:
        # 方向反转：先把现有反方向仓位平掉，再在新方向重新开仓
        if current_size > 0:
            actions.append(("close", current_side, current_size))
        current_side, current_size = None, 0

    if target_side is None:
        if current_side and current_size > 0:
            actions.append(("close", current_side, current_size))
        return actions

    if current_side is None:
        if target_qty >= order_size_min:
            actions.append(("open", target_side, target_qty))
        return actions

    # 同方向，调整数量
    diff = target_qty - current_size
    if diff >= order_size_min:
        actions.append(("open", target_side, diff))
    elif -diff >= order_size_min:
        actions.append(("reduce", target_side, -diff))
    return actions


