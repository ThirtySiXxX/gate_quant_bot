"""
真实交易所接口封装（基于官方 gate-api SDK: https://github.com/gateio/gateapi-python）。

本程序始终使用 Gate.io 的"双向持仓模式(dual mode)"：同一个合约可以同时
持有多头(dual_long)和空头(dual_short)两条独立的腿，用于实现策略主仓+对冲仓
并存的场景。切换双向模式的前提是账户该结算币种下没有任何持仓/挂单，
ensure_dual_mode() 会在启动时尝试自动切换，如果已有持仓会切换失败并
在日志/网页界面里提示，需要用户先在 Gate 官网手动平掉旧仓位。
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger("bot.exchange")

try:
    import gate_api
    from gate_api.exceptions import ApiException, GateApiException
except ImportError:  # 允许在未安装 gate-api 时仍能 import 本模块做静态检查
    gate_api = None
    ApiException = Exception
    GateApiException = Exception


INTERVAL_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "8h": 28800, "1d": 86400,
}

SIDE_TO_DUAL = {"long": "dual_long", "short": "dual_short"}
MODE_TO_SIDE = {"dual_long": "long", "dual_short": "short"}

# ⚠️ 注意区分两组取值，之前这里混用过导致平仓请求被交易所拒绝：
#   - 持仓的 mode 字段用 dual_long / dual_short
#   - 下单的 auto_size 字段用 close_long / close_short
# Gate 官方 SDK 原文：「`close_long` closes the long side; while `close_short` the
# short one. Note `size` also needs to be set to 0」。
SIDE_TO_CLOSE = {"long": "close_long", "short": "close_short"}


def estimate_book_fill(asks, bids, qty: float, is_buy: bool) -> dict:
    """按盘口绝对挂单量估算一笔市价单的覆盖率、VWAP、点差和冲击成本。"""
    qty = max(float(qty), 0.0)
    ask_levels = [(float(p), abs(float(s))) for p, s in asks if float(p) > 0 and float(s) > 0]
    bid_levels = [(float(p), abs(float(s))) for p, s in bids if float(p) > 0 and float(s) > 0]
    if qty <= 0 or not ask_levels or not bid_levels:
        return {"fill_ratio": 0.0, "vwap": 0.0, "spread_bps": float("inf"),
                "slippage_bps": float("inf"), "available_qty": 0.0}

    best_ask, best_bid = ask_levels[0][0], bid_levels[0][0]
    mid = (best_ask + best_bid) / 2.0
    levels = ask_levels if is_buy else bid_levels
    remaining, value, filled = qty, 0.0, 0.0
    for price, size in levels:
        take = min(size, remaining)
        value += take * price
        filled += take
        remaining -= take
        if remaining <= 1e-12:
            break

    vwap = value / filled if filled > 0 else 0.0
    return {
        "fill_ratio": min(filled / qty, 1.0),
        "vwap": vwap,
        "spread_bps": ((best_ask - best_bid) / mid * 10000.0) if mid > 0 else float("inf"),
        "slippage_bps": (abs(vwap - mid) / mid * 10000.0) if mid > 0 and vwap > 0 else float("inf"),
        "available_qty": filled,
    }


def _err_text(e) -> str:
    """把 Gate 的异常整理成一句人能看懂的话（带上label方便对照官方错误码表）。"""
    label = getattr(e, "label", "") or ""
    msg = getattr(e, "message", "") or getattr(e, "body", "") or str(e)
    return f"[{label}] {msg}" if label else str(msg)


def _safe_int(value, default: int, min_value: int = None) -> int:
    """稳妥地把 Gate 返回的字段转成 int。
    有些合约的部分字段会以小数字符串返回（比如"0.1"），直接 int()会报错，
    这里先尝试整数解析，失败则按浮点数解析后取整，再兜底默认值。"""
    try:
        result = int(value)
    except (TypeError, ValueError):
        try:
            result = int(float(value))
        except (TypeError, ValueError):
            result = default
    if min_value is not None and result < min_value:
        result = min_value
    return result


class GateExchange:
    def __init__(self, api_key: str, api_secret: str, settle: str = "usdt",
                 host: str = "https://api.gateio.ws/api/v4"):
        if gate_api is None:
            raise RuntimeError("请先安装依赖: pip install gate-api")
        configuration = gate_api.Configuration(host=host, key=api_key, secret=api_secret)
        self.client = gate_api.ApiClient(configuration)
        self.api = gate_api.FuturesApi(self.client)
        self.settle = settle
        self._contract_cache: Dict[str, dict] = {}
        self._contract_cache_ts: Dict[str, float] = {}
        self._fee_cache: Dict[str, float] = {}
        self._fee_cache_ts: Dict[str, float] = {}

    # ---------------------------------------------------------- 双向持仓模式
    def ensure_dual_mode(self) -> tuple[bool, str]:
        """尝试将账户切换为双向持仓模式。返回 (是否已确认处于双向模式, 说明信息)。

        Gate 的接口有个特点：如果账户已经处于双向持仓模式，再次调用 set_dual_mode(True)
        不会原样成功，而是返回 400 + label=NO_CHANGE（意思是"已经是这个状态了，不用改"）。
        这其实是好消息（说明已经在双向模式），要识别出来当作成功处理，
        不能和"账户有旧仓位导致真正切换失败"混为一谈。
        """
        try:
            acc = self.api.set_dual_mode(self.settle, True)
            in_dual = bool(getattr(acc, "in_dual_mode", True))
            return True, "已切换为双向持仓模式" if in_dual else "切换请求已发送"
        except GateApiException as e:
            label = (getattr(e, "label", "") or "").upper()
            message = getattr(e, "message", "") or str(e)
            if label == "NO_CHANGE" or "already" in message.lower():
                return True, "账户已经处于双向持仓模式，无需切换"
            return False, (
                f"切换双向持仓模式失败：[{label or '未知错误'}] {message}。"
                "最常见原因是该结算币种下还有旧仓位/挂单，请先在 Gate 官网手动平仓/撤单后重启程序。"
            )
        except ApiException as e:
            body = getattr(e, "body", "") or str(e)
            if "NO_CHANGE" in str(body):
                return True, "账户已经处于双向持仓模式，无需切换"
            return False, f"切换双向持仓模式失败：{e}"

    # ---------------------------------------------------------- 行情
    def get_candles(self, contract: str, interval: str, limit: int = 300) -> pd.DataFrame:
        raw = self.api.list_futures_candlesticks(
            self.settle, contract, interval=interval, limit=limit
        )
        rows = [{
            "timestamp": float(c.t),
            "open": float(c.o), "high": float(c.h),
            "low": float(c.l), "close": float(c.c),
            "volume": float(c.v) if c.v is not None else float(c.sum or 0),
        } for c in raw]
        df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
        return df

    def get_ticker(self, contract: str) -> dict:
        raw = self.api.list_futures_tickers(self.settle, contract=contract)
        if not raw:
            raise RuntimeError(f"未获取到 {contract} 行情")
        t = raw[0]
        return {
            "last": float(t.last), "mark_price": float(t.mark_price),
            "funding_rate": float(t.funding_rate) if t.funding_rate else 0.0,
        }

    def get_funding_rate_history(self, contract: str, from_ts: Optional[int] = None,
                                  to_ts: Optional[int] = None, limit: int = 1000) -> pd.DataFrame:
        """历史资金费率(每次结算一条记录)。

        Gate 是提供这个接口的(list_futures_funding_rate_history，支持 from/to 翻页)，
        所以回测里的 carry 信号可以用真实的逐期历史费率，而不是只能拿"下载那一刻的
        实时费率"当常数贴一整段历史——后者会让回测里 carry 的贡献严重失真
        (资金费率在牛熊转换时经常反号，用常数近似等于假装它一直没变过)。

        返回 DataFrame(columns=[timestamp, funding_rate])，按时间升序。
        """
        kwargs = {"limit": min(int(limit), 1000)}
        if from_ts is not None:
            kwargs["_from"] = int(from_ts)
        if to_ts is not None:
            kwargs["to"] = int(to_ts)
        raw = self.api.list_futures_funding_rate_history(self.settle, contract, **kwargs)
        rows = [{"timestamp": float(r.t), "funding_rate": float(r.r)} for r in raw]
        if not rows:
            return pd.DataFrame(columns=["timestamp", "funding_rate"])
        return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

    def get_account_taker_fee_rate(self, contract: str, ttl: float = 300.0) -> Optional[float]:
        """读取当前账户/VIP等级对指定合约实际生效的吃单费率。失败时由调用方回退配置值。"""
        now = time.time()
        if contract in self._fee_cache and now - self._fee_cache_ts.get(contract, 0) < ttl:
            return self._fee_cache[contract]
        raw = self.api.get_futures_fee(self.settle, contract=contract)
        fee = raw.get(contract) if isinstance(raw, dict) else None
        if fee is None or getattr(fee, "taker_fee", None) is None:
            return None
        rate = float(fee.taker_fee)
        self._fee_cache[contract] = rate
        self._fee_cache_ts[contract] = now
        return rate

    def estimate_market_order(self, contract: str, side: str, qty: float,
                              is_entry: bool, levels: int = 20) -> dict:
        """下单前读取最新REST盘口，估算市价单是否有足够深度。

        这是执行保护，不参与趋势或Carry方向判断。开多/平空需要吃 asks，开空/平多吃 bids。
        """
        book = self.api.list_futures_order_book(
            self.settle, contract, interval="0", limit=max(1, min(int(levels), 50)), with_id=True)
        asks = [(x.p, x.s) for x in (book.asks or [])]
        bids = [(x.p, x.s) for x in (book.bids or [])]
        is_buy = (side == "long") if is_entry else (side == "short")
        estimate = estimate_book_fill(asks, bids, qty, is_buy)
        estimate.update({
            "book_id": getattr(book, "id", None),
            "book_ts": float(getattr(book, "current", 0.0) or 0.0),
        })
        return estimate

    def get_contract(self, contract: str, ttl: float = 300.0) -> dict:
        now = time.time()
        if contract in self._contract_cache and now - self._contract_cache_ts.get(contract, 0) < ttl:
            return self._contract_cache[contract]
        c = self.api.get_futures_contract(self.settle, contract)
        info = {
            "quanto_multiplier": float(c.quanto_multiplier or 1),
            "leverage_min": float(c.leverage_min or 1),
            "leverage_max": float(c.leverage_max or 20),
            "taker_fee_rate": float(c.taker_fee_rate or 0.0005),
            "maker_fee_rate": float(c.maker_fee_rate or 0.00015),
            "order_size_min": _safe_int(c.order_size_min, default=1, min_value=1),
            "order_size_max": _safe_int(c.order_size_max, default=1_000_000, min_value=1),
            "funding_rate": float(c.funding_rate or 0.0),
            "funding_interval": _safe_int(c.funding_interval, default=28800, min_value=60),
            "funding_next_apply": float(c.funding_next_apply or 0),
            "mark_price": float(c.mark_price or 0),
            "order_price_round": c.order_price_round,
        }
        self._contract_cache[contract] = info
        self._contract_cache_ts[contract] = now
        return info

    # ---------------------------------------------------------- 账户/持仓
    def get_account_equity(self) -> float:
        acc = self.api.list_futures_accounts(self.settle)
        total = float(acc.total or 0)
        upnl = float(acc.unrealised_pnl or 0)
        return total + upnl

    def get_dual_positions(self) -> List[dict]:
        """返回账户下所有非零仓位（双向模式下每个合约最多两条腿）。"""
        raw = self.api.list_positions(self.settle, holding=True)
        out = []
        for p in raw:
            size = float(p.size or 0)
            if size == 0:
                continue
            side = MODE_TO_SIDE.get(p.mode, "long" if size > 0 else "short")
            lev = float(p.leverage or 0)
            out.append({
                "contract": p.contract, "side": side, "size": abs(size),
                "entry_price": float(p.entry_price or 0),
                "mark_price": float(p.mark_price or 0),
                "leverage": lev,
                "unrealised_pnl": float(p.unrealised_pnl or 0),
                "mode": p.mode,
                # Gate 用 leverage 字段本身区分保证金模式：0 = 全仓，非0 = 逐仓(数值即杠杆倍数)
                "margin_mode": "cross" if lev == 0 else "isolated",
                "cross_leverage_limit": float(getattr(p, "cross_leverage_limit", 0) or 0),
            })
        return out

    # ---------------------------------------------------------- 保证金模式（全仓）
    def set_cross_margin(self, contract: str, leverage_limit: float) -> dict:
        """把该合约切到**全仓(cross margin)**。

        Gate 的约定容易踩坑：保证金模式不是一个独立开关，而是用 leverage 字段编码的——
            leverage = "0"     -> 全仓，此时用 cross_leverage_limit 指定杠杆上限
            leverage = "N"(N>0) -> 逐仓，N 就是该仓位的杠杆倍数
        所以之前传 str(int(leverage)) 实际上是把仓位设成了逐仓，这就是你看到"开进去是逐仓"的原因。
        """
        info = self.get_contract(contract)
        lim = max(float(info["leverage_min"]), min(float(leverage_limit), float(info["leverage_max"])))
        try:
            self.api.update_dual_mode_position_leverage(
                self.settle, contract, "0", cross_leverage_limit=str(int(lim)))
            return {"ok": True, "leverage_limit": lim,
                    "message": f"已设为全仓，杠杆上限 {int(lim)}x"
                                + ("（已按合约允许范围调整）" if abs(lim - float(leverage_limit)) > 1e-9 else "")}
        except (ApiException, GateApiException) as e:
            return {"ok": False, "leverage_limit": lim,
                    "message": f"切换全仓失败: {_err_text(e)}"}

    def get_margin_mode(self, contract: str) -> dict:
        """查询该合约当前的保证金模式。没有持仓时交易所不一定返回记录，
        这种情况返回 unknown —— 调用方应把它当作"还没确认"，而不是当成全仓。"""
        try:
            raw = self.api.list_positions(self.settle, holding=False)
        except (ApiException, GateApiException) as e:
            return {"ok": False, "margin_mode": "unknown", "message": f"查询保证金模式失败: {_err_text(e)}"}
        for p in raw:
            if p.contract != contract:
                continue
            lev = float(p.leverage or 0)
            mode = "cross" if lev == 0 else "isolated"
            return {"ok": True, "margin_mode": mode, "leverage": lev,
                    "cross_leverage_limit": float(getattr(p, "cross_leverage_limit", 0) or 0),
                    "message": f"当前为{'全仓' if mode == 'cross' else '逐仓'}"}
        return {"ok": True, "margin_mode": "unknown",
                "message": "交易所没有返回该合约的仓位记录（通常是从未交易过）"}

    def ensure_cross_margin(self, contract: str, leverage_limit: float) -> dict:
        """设置全仓并**回读校验**。开仓前每次都应该调一次——只发设置请求不校验的话，
        请求被静默忽略(比如已有逐仓持仓时Gate可能拒绝切换)就会在不知情的情况下按逐仓下单。"""
        setr = self.set_cross_margin(contract, leverage_limit)
        chk = self.get_margin_mode(contract)
        if chk.get("margin_mode") == "cross":
            return {"ok": True, "verified": True, "margin_mode": "cross",
                    "message": f"已确认全仓（杠杆上限 {int(chk.get('cross_leverage_limit') or leverage_limit)}x）"}
        if chk.get("margin_mode") == "isolated":
            return {"ok": False, "verified": True, "margin_mode": "isolated",
                    "message": ("仍然是逐仓！" + setr["message"]
                                 + "。最常见原因是该合约已有逐仓持仓——Gate 不允许有仓位时切换保证金模式，"
                                   "请先在 Gate 官网手动平掉该合约的仓位再重试")}
        # 拿不到确认（从未交易过该合约等），只能如实说明，不能假装成功
        return {"ok": setr["ok"], "verified": False,
                "margin_mode": chk.get("margin_mode", "unknown"),
                "message": setr["message"] + f"；但未能回读确认（{chk.get('message','')}）"}

    def set_leverage(self, contract: str, leverage: float) -> None:
        """[保留兼容旧版对冲策略] 现在统一走全仓，这里直接转发到 ensure_cross_margin。"""
        r = self.set_cross_margin(contract, leverage)
        if not r["ok"]:
            logger.warning("设置全仓失败 %s: %s", contract, r["message"])

    def open_dual(self, contract: str, side: str, size: int, text: str = "t-quantbot") -> dict:
        """开/加仓一条腿。side='long' 用正数张数下单，'short' 用负数张数下单。"""
        signed = int(size) if side == "long" else -int(size)
        order = gate_api.FuturesOrder(
            contract=contract, size=signed, price="0", tif="ioc",
            reduce_only=False, text=text,
        )
        return self._submit(order)

    def reduce_dual(self, contract: str, side: str, qty: int, text: str = "t-quantbot-reduce") -> dict:
        """部分减仓某一条腿。减多头用负数张数，减空头用正数张数（配合reduce_only）。"""
        signed = -int(qty) if side == "long" else int(qty)
        order = gate_api.FuturesOrder(
            contract=contract, size=signed, price="0", tif="ioc",
            reduce_only=True, text=text,
        )
        return self._submit(order)

    def close_dual(self, contract: str, side: str, text: str = "t-quantbot-close") -> dict:
        """完全平掉某一条腿。size 必须为0，并用 auto_size 指定平哪一边。"""
        order = gate_api.FuturesOrder(
            contract=contract, size=0, price="0", tif="ioc",
            reduce_only=True, auto_size=SIDE_TO_CLOSE[side], text=text,
        )
        return self._submit(order)

    # ------------------------------------------------- 手动测试下单（供"手动开单"页面用）
    def set_leverage_checked(self, contract: str, leverage: float) -> dict:
        """设为全仓 + 指定杠杆上限，并回读校验。结果如实返回（不吞异常），
        方便手动测试页逐步显示每一步到底成功没有。"""
        return self.ensure_cross_margin(contract, leverage)

    def open_market(self, contract: str, side: str, size: int,
                     text: str = "t-manual") -> dict:
        """市价开仓（IOC）。返回统一结构，失败不抛异常而是返回 ok=False，便于页面展示。"""
        signed = int(size) if side == "long" else -int(size)
        order = gate_api.FuturesOrder(contract=contract, size=signed, price="0",
                                       tif="ioc", reduce_only=False, text=text)
        try:
            r = self._submit(order)
            left = abs(float(r.get("left") or 0))
            filled = abs(int(size)) - int(round(left))
            return {"ok": filled > 0, "raw": r, "filled": filled, "requested": int(size),
                    "fill_price": r.get("fill_price"),
                    "message": (f"已成交 {filled}/{int(size)} 张"
                                + (f"，均价≈{r.get('fill_price')}" if r.get("fill_price") else "")
                                if filled > 0 else f"未成交(left={left:.0f})，IOC单已撤销")}
        except (ApiException, GateApiException) as e:
            return {"ok": False, "message": f"下单失败: {_err_text(e)}"}

    def create_tp_sl(self, contract: str, side: str, trigger_price: float,
                      kind: str, text: str = "t-manual-tpsl") -> dict:
        """挂一张"价格触发的全平单"作为止盈或止损。

        触发规则(rule)：1 = 价格>=触发价，2 = 价格<=触发价。
        多头止盈在上方(rule=1)、止损在下方(rule=2)；空头反过来。
        price_type=1 表示用标记价触发（比最新价更抗插针）。
        """
        if side == "long":
            rule = 1 if kind == "tp" else 2
        else:
            rule = 2 if kind == "tp" else 1
        initial = gate_api.FuturesInitialOrder(
            contract=contract, size=0, price="0", tif="ioc",
            reduce_only=True, auto_size=SIDE_TO_CLOSE[side], text=text,
        )
        trigger = gate_api.FuturesPriceTrigger(
            strategy_type=0, price_type=1, price=str(trigger_price), rule=rule, expiration=0,
        )
        try:
            resp = self.api.create_price_triggered_order(
                self.settle, gate_api.FuturesPriceTriggeredOrder(initial=initial, trigger=trigger))
            oid = getattr(resp, "id", None) or getattr(resp, "id_string", None)
            return {"ok": True, "order_id": oid,
                    "message": f"{'止盈' if kind=='tp' else '止损'}单已挂 @ {trigger_price}（触发单号 {oid}）"}
        except (ApiException, GateApiException) as e:
            return {"ok": False,
                    "message": f"{'止盈' if kind=='tp' else '止损'}单挂单失败: {_err_text(e)}"}

    def _submit(self, order) -> dict:
        try:
            resp = self.api.create_futures_order(self.settle, order)
            fill_price = float(resp.fill_price) if resp.fill_price else None
            return {
                "id": resp.id, "status": resp.status, "fill_price": fill_price,
                "size": float(resp.size or 0), "left": float(resp.left or 0),
                "tkfr": float(resp.tkfr) if resp.tkfr else None,
            }
        except (ApiException, GateApiException) as e:
            logger.error("下单失败 contract=%s: %s", getattr(order, "contract", "?"), e)
            raise
