"""
模拟盘(paper trading)交易所 —— 双向持仓版本。

行情(K线/最新价/合约参数/资金费率)全部读取 Gate.io 真实公开接口，
只有"账户余额、持仓、成交"是在本地内存里模拟撮合的——
用真实市场数据 + 真实费率/资金费 检验策略是否有效，同时支持
同一合约同时持有 long/short 两条独立腿（对应实盘的双向持仓模式）。

与 GateExchange 暴露完全一致的方法签名，engine.py 无需区分 paper/live。
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from . import costs
from .exchange_gate import GateExchange

logger = logging.getLogger("bot.exchange_paper")


class PaperExchange:
    def __init__(self, market_data_source: GateExchange, initial_capital: float,
                 slippage_bps: float = 5.0, taker_fee_rate: float = 0.0005):
        self.md = market_data_source
        self.slippage_bps = slippage_bps
        self.taker_fee_rate = float(taker_fee_rate)
        self.cash = initial_capital
        self.realized_pnl_total = 0.0
        # (contract, side) -> {size(abs), entry_price, leverage}
        self._positions: Dict[Tuple[str, str], dict] = {}
        # (contract, side) -> [{kind, price}]，模拟盘只记录手动挂的止盈止损，不做撮合
        self._tpsl: Dict[Tuple[str, str], list] = {}
        # contract -> 全仓杠杆上限；模拟盘统一按全仓运行，和实盘口径保持一致
        self._cross: Dict[str, float] = {}

    # ---------------------------------------------------------- 行情：直接转发底层真实行情源
    # data_fetcher.fetch_candles() 需要直接访问 exchange.api / exchange.settle 做分页K线下载
    # (systematic_engine.py 的信号计算就是通过 self.exchange 也就是这个 PaperExchange 调用的)，
    # 之前这里没有转发这两个属性，导致模拟盘下 _gather_signal() 每次都会因为
    # "'PaperExchange' object has no attribute 'api'" 直接失败、永远算不出任何信号/开不出任何仓位——
    # 这是模拟盘模式本身的bug，和"反向执行"开关无关，但会让反向执行(以及其它任何策略行为)
    # 在模拟盘下看起来"完全不生效"，因为压根没有走到下单那一步。
    @property
    def api(self):
        return self.md.api

    @property
    def settle(self):
        return self.md.settle

    # ---------------------------------------------------------- 双向持仓模式
    def ensure_dual_mode(self):
        return True, "PAPER 模拟盘天然支持双向持仓，无需切换"

    # ---------------------------------------------------------- 行情：直接转发
    def get_candles(self, contract: str, interval: str, limit: int = 300):
        return self.md.get_candles(contract, interval, limit)

    def get_ticker(self, contract: str) -> dict:
        return self.md.get_ticker(contract)

    def get_contract(self, contract: str) -> dict:
        return self.md.get_contract(contract)

    def get_account_taker_fee_rate(self, contract: str):
        try:
            return self.md.get_account_taker_fee_rate(contract)
        except Exception:
            return None

    def estimate_market_order(self, contract: str, side: str, qty: float,
                              is_entry: bool, levels: int = 20) -> dict:
        return self.md.estimate_market_order(contract, side, qty, is_entry, levels)

    # ---------------------------------------------------------- 账户/持仓：本地模拟
    def get_account_equity(self) -> float:
        equity = self.cash
        for (contract, side), pos in self._positions.items():
            try:
                mark = self.md.get_ticker(contract)["mark_price"]
                qm = self.md.get_contract(contract)["quanto_multiplier"]
            except Exception:
                continue
            direction = 1 if side == "long" else -1
            upnl = (mark - pos["entry_price"]) * pos["size"] * qm * direction
            equity += upnl
        return equity

    def get_dual_positions(self) -> List[dict]:
        out = []
        for (contract, side), pos in self._positions.items():
            try:
                mark = self.md.get_ticker(contract)["mark_price"]
            except Exception:
                mark = pos["entry_price"]
            direction = 1 if side == "long" else -1
            upnl = (mark - pos["entry_price"]) * pos["size"] * self.md.get_contract(contract)["quanto_multiplier"] * direction
            out.append({
                "contract": contract, "side": side, "size": pos["size"],
                "entry_price": pos["entry_price"], "mark_price": mark,
                "leverage": pos.get("leverage", 0), "unrealised_pnl": upnl,
                "mode": "dual_long" if side == "long" else "dual_short",
                "margin_mode": "cross" if contract in self._cross else "isolated",
                "cross_leverage_limit": self._cross.get(contract, 0.0),
            })
        return out

    # ---------------------------------------------------------- 保证金模式（模拟盘）
    def set_cross_margin(self, contract: str, leverage_limit: float) -> dict:
        info = self.md.get_contract(contract)
        lim = max(float(info["leverage_min"]), min(float(leverage_limit), float(info["leverage_max"])))
        for key, pos in self._positions.items():
            if key[0] == contract:
                pos["leverage"] = 0          # 0 = 全仓，和实盘口径一致
                pos["cross_leverage_limit"] = lim
        self._cross[contract] = lim
        return {"ok": True, "leverage_limit": lim, "message": f"[模拟盘] 已设为全仓，杠杆上限 {int(lim)}x"}

    def get_margin_mode(self, contract: str) -> dict:
        if contract in self._cross:
            return {"ok": True, "margin_mode": "cross", "leverage": 0.0,
                    "cross_leverage_limit": self._cross[contract], "message": "[模拟盘] 全仓"}
        return {"ok": True, "margin_mode": "unknown", "message": "[模拟盘] 尚未设置过该合约"}

    def ensure_cross_margin(self, contract: str, leverage_limit: float) -> dict:
        r = self.set_cross_margin(contract, leverage_limit)
        return {"ok": True, "verified": True, "margin_mode": "cross",
                "message": f"[模拟盘] 已确认全仓（杠杆上限 {int(r['leverage_limit'])}x）"}

    def set_leverage(self, contract: str, leverage: float) -> None:
        for key, pos in self._positions.items():
            if key[0] == contract:
                pos["leverage"] = leverage

    # ---------------------------------------------------------- 撮合模拟（双向）
    def open_dual(self, contract: str, side: str, size: int, text: str = "") -> dict:
        ticker = self.md.get_ticker(contract)
        info = self.md.get_contract(contract)
        qm = info["quanto_multiplier"]
        mark = ticker["mark_price"]

        fill_price = costs.slippage_adjusted_price(mark, side, self.slippage_bps, is_entry=True)
        notional = size * fill_price * qm
        fee = costs.taker_fee(notional, self.taker_fee_rate)
        self.cash -= fee

        key = (contract, side)
        existing = self._positions.get(key)
        if existing:
            total_size = existing["size"] + size
            existing["entry_price"] = (existing["entry_price"] * existing["size"] + fill_price * size) / total_size
            existing["size"] = total_size
        else:
            self._positions[key] = {"size": size, "entry_price": fill_price, "leverage": 0}

        logger.info("[PAPER] 开仓/加仓 %s side=%s size=%s fill=%.4f fee=%.4f", contract, side, size, fill_price, fee)
        return {"id": "paper-open", "status": "finished", "fill_price": fill_price, "fee": fee}

    def reduce_dual(self, contract: str, side: str, qty: int, text: str = "") -> dict:
        key = (contract, side)
        pos = self._positions.get(key)
        if not pos:
            return {"id": "paper-noop", "fill_price": 0, "fee": 0, "net_pnl": 0}
        ticker = self.md.get_ticker(contract)
        info = self.md.get_contract(contract)
        qm = info["quanto_multiplier"]
        mark = ticker["mark_price"]
        fill_price = costs.slippage_adjusted_price(mark, side, self.slippage_bps, is_entry=False)

        qty = min(qty, pos["size"])
        direction = 1 if side == "long" else -1
        gross = (fill_price - pos["entry_price"]) * qty * qm * direction
        notional = qty * fill_price * qm
        fee = costs.taker_fee(notional, self.taker_fee_rate)
        net = gross - fee
        self.cash += net
        self.realized_pnl_total += net

        pos["size"] -= qty
        if pos["size"] <= 1e-9:
            self._positions.pop(key, None)

        logger.info("[PAPER] 减仓 %s side=%s qty=%s fill=%.4f net=%.4f", contract, side, qty, fill_price, net)
        return {"fill_price": fill_price, "fee": fee, "net_pnl": net, "gross_pnl": gross}

    def close_dual(self, contract: str, side: str, text: str = "") -> dict:
        key = (contract, side)
        pos = self._positions.get(key)
        if not pos:
            return {"id": "paper-noop", "fill_price": 0, "fee": 0, "net_pnl": 0, "gross_pnl": 0}
        return self.reduce_dual(contract, side, pos["size"], text=text)

    # ------------------------------------------------- 手动测试下单（模拟盘版本）
    def set_leverage_checked(self, contract: str, leverage: float) -> dict:
        return self.ensure_cross_margin(contract, leverage)

    def open_market(self, contract: str, side: str, size: int, text: str = "t-manual") -> dict:
        r = self.open_dual(contract, side, int(size), text=text)
        return {"ok": True, "raw": r, "filled": int(size), "requested": int(size),
                "fill_price": r.get("fill_price"),
                "message": f"[模拟盘] 已成交 {int(size)} 张 @≈{r.get('fill_price'):.4f}"}

    def create_tp_sl(self, contract: str, side: str, trigger_price: float,
                      kind: str, text: str = "t-manual-tpsl") -> dict:
        """模拟盘不做真正的触发单撮合，只记录下来并如实告知用户，
        避免让人误以为模拟盘里的止盈止损会自动生效。"""
        self._tpsl.setdefault((contract, side), []).append({"kind": kind, "price": float(trigger_price)})
        return {"ok": True, "order_id": None,
                "message": (f"[模拟盘] 已记录{'止盈' if kind=='tp' else '止损'} @ {trigger_price}"
                             "（注意：模拟盘不会真的自动触发，仅用于验证参数换算是否正确）")}

    def settle_funding(self, contract: str, side: str) -> float:
        """按当前资金费率对该腿结算一次资金费，返回净现金变动（正=盈利，负=成本）。"""
        key = (contract, side)
        pos = self._positions.get(key)
        if not pos:
            return 0.0
        ticker = self.md.get_ticker(contract)
        info = self.md.get_contract(contract)
        qm = info["quanto_multiplier"]
        mark = ticker["mark_price"]
        funding_rate = ticker.get("funding_rate", 0.0)
        notional = pos["size"] * mark * qm
        cost = costs.funding_fee(notional, funding_rate, side)  # 正=亏损
        self.cash -= cost
        self.realized_pnl_total -= cost
        return -cost
