"""Fixed initial-margin entry tickets, separate from model exit sizing.

No exchange I/O. Quantity is rounded down to whole contracts (the current engine
uses integer contracts even on markets that also permit fractional contracts).
"""
from dataclasses import asdict, dataclass
from decimal import Decimal
import math


MAJORS = frozenset(("BTC_USDT", "ETH_USDT", "SOL_USDT"))


def positive(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} 缺失或无效") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} 必须为有限正数")
    return value


@dataclass(frozen=True)
class EntryTicket:
    equity: float
    requested_leverage: float
    leverage: float
    desired_notional: float
    quantity: int
    notional: float
    initial_margin: float
    margin_pct: float
    required_available: float

    def to_dict(self):
        return asdict(self)


def entry_ticket(symbol, equity, price, contract, tiers, available, fee_rate,
                 slippage_bps=0.0):
    """Maintain requested notional when SOL/alts have a lower leverage limit.

    Tiers and account funds must be explicitly supplied; no optimistic defaults.
    BTC/ETH must support 200x. SOL equivalent fallback is user-authorized.
    """
    if not symbol.endswith("_USDT") or contract.get("contract_type", "") not in ("", "crypto"):
        raise ValueError("固定保证金规则仅支持 USDT 线性合约")
    equity = positive(equity, "账户权益")
    price = positive(price, "价格")
    qm = positive(contract.get("quanto_multiplier"), "合约乘数")
    maximum = positive(contract.get("leverage_max"), "合约最大杠杆")
    minimum = positive(contract.get("leverage_min"), "合约最小杠杆")
    requested = 200.0 if symbol in MAJORS else 20.0
    desired = equity * 0.05 * requested
    # Tier covers the unrounded target, including an adverse price move at entry.
    fee_rate, slippage_bps = float(fee_rate), float(slippage_bps)
    if not all(math.isfinite(v) and v >= 0 for v in (fee_rate, slippage_bps)):
        raise ValueError("费用/滑点参数无效")
    worst = 1 + slippage_bps / 10000
    if not tiers:
        raise ValueError("缺少风险限额档位，拒绝猜测可用杠杆")
    rows = sorted(tiers, key=lambda r: positive(r.get("risk_limit"), "档位限额"))
    tier = next((r for r in rows if positive(r.get("risk_limit"), "档位限额") >= desired * worst), None)
    if tier is None:
        raise ValueError("目标名义仓位超过交易所最高风险限额")
    leverage = math.floor(min(requested, maximum, positive(tier.get("leverage_max"), "档位杠杆")))
    if leverage < minimum or leverage < 1:
        raise ValueError("没有满足合约限制的杠杆")
    if symbol in ("BTC_USDT", "ETH_USDT") and leverage < requested:
        raise ValueError(f"{symbol} 当前合约/档位仅支持 {leverage}x，未满足 200x")
    # min size is a minimum, NOT a quantity step. We deliberately use whole units.
    minimum_qty = max(1, math.ceil(float(contract.get("order_size_min", 1))))
    maximum_qty = positive(contract.get("order_size_max"), "最大下单张数")
    market_max = contract.get("market_order_size_max")
    if market_max:
        maximum_qty = min(maximum_qty, positive(market_max, "市价单最大张数"))
    quantity = int(Decimal(str(desired)) / (Decimal(str(price)) * Decimal(str(qm))))
    if quantity < minimum_qty:
        raise ValueError("目标不足最小下单张数")
    if quantity > maximum_qty:
        raise ValueError("目标超过单笔最大下单张数，未拆单或偷偷缩小仓位")
    notional = quantity * price * qm
    margin = notional / leverage
    # Reserve initial margin, both taker fees and adverse entry slippage.
    required = notional * worst / leverage + 2 * notional * worst * fee_rate + notional * (worst - 1)
    available = float(available)
    if not math.isfinite(available) or available < required:
        raise ValueError(f"可用保证金不足：需 {required:.4f} USDT，可用 {available:.4f} USDT")
    return EntryTicket(equity, requested, leverage, desired, quantity, notional,
                       margin, margin / equity * 100, required)


class EntrySizingBook:
    """Translate existing model reduction decisions into each fixed entry ticket.

    The model keeps its original unit scale for timing/buffer/exit decisions.
    Fixed tickets never pyramid, even after partial fills or a process restart.
    A reversal closes first; its next entry uses fresh account equity.
    """
    def __init__(self, state=None):
        self.ratios = dict(state or {})
        for value in self.ratios.values():
            positive(value, "持仓模型换算比例")

    def model_current(self, symbol, current, model_target):
        if not current:
            self.ratios.pop(symbol, None)
            return 0.0
        if symbol not in self.ratios:
            # Existing holdings are not enlarged on migration or restart.
            self.ratios[symbol] = abs(model_target / current) if model_target * current > 0 else 1.0
        return current * self.ratios[symbol]

    def bind(self, symbol, model_target, actual_notional):
        self.ratios[symbol] = positive(abs(model_target) / actual_notional, "持仓模型换算比例")

    def held_target(self, symbol, model_target, current):
        if model_target * current <= 0:
            return 0.0
        target = model_target / self.ratios[symbol]
        return math.copysign(min(abs(target), abs(current)), current)
