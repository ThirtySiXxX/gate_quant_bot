"""
[LEGACY / 默认不再使用] 旧版15分钟多因子 + 双向持仓自动对冲策略的交易主循环。

自从项目切换到新的"多资产 Trend + Carry + 波动率目标"系统性策略(见
systematic_engine.py)之后，这个引擎不再被 EngineController 默认调用，
但代码原样保留在这里，方便你需要参考/对比/切回旧策略时使用。

如果确实需要切回这套逻辑，把 src/engine.py 里 EngineController.start()
中构造的 SystematicEngine 换成这里的 Engine 即可，其余生命周期管理
（启停、模式切换、凭证读取）都不需要改。
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
from typing import Dict, Optional, Tuple

import pandas as pd

from . import costs, hedge as hedge_logic, indicators as ind, risk, strategy
from .config import ConfigStore, CostConfig, HedgeConfig, RiskConfig, StrategyConfig
from .credentials import CredentialStore
from .exchange_gate import GateExchange
from .exchange_paper import PaperExchange
from .models import Position, Trade, new_id, now_ts
from .state import StateStore

logger = logging.getLogger("bot.engine")

TF_REFRESH_SEC = {"15m": 60, "1h": 300, "4h": 900}


class Engine:
    def __init__(self, config_store: ConfigStore, exchange, state: StateStore):
        self.cfg_store = config_store
        self.exchange = exchange
        self.state = state
        self._candle_cache: Dict[tuple, tuple] = {}   # (symbol, tf) -> (fetched_ts, df)
        self._regime_cache: Dict[str, tuple] = {}      # symbol -> (ts, regime)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    # ---------------------------------------------------------- 行情缓存
    def _get_candles_cached(self, symbol: str, tf: str, limit: int) -> Optional[pd.DataFrame]:
        key = (symbol, tf)
        cached = self._candle_cache.get(key)
        now = time.time()
        ttl = TF_REFRESH_SEC.get(tf, 300)
        if cached and now - cached[0] < ttl:
            return cached[1]
        try:
            df = self.exchange.get_candles(symbol, tf, limit)
        except Exception as e:
            self.state.add_log(f"{symbol} 获取{tf}K线失败: {e}", "ERROR")
            return cached[1] if cached else None
        self._candle_cache[key] = (now, df)
        return df

    def _fetch_multi_tf(self, symbol: str, strat_cfg: StrategyConfig, tf_map: dict, lookback: int):
        df15 = self._get_candles_cached(symbol, tf_map["entry"], lookback)
        df1h = self._get_candles_cached(symbol, tf_map["trend_mid"], lookback)
        df4h = self._get_candles_cached(symbol, tf_map["trend_high"], lookback)
        if df15 is None or df1h is None or df4h is None:
            return None, None, None
        if len(df15) < 10 or len(df1h) < 10 or len(df4h) < 10:
            return None, None, None
        return ind.enrich(df15, strat_cfg), ind.enrich(df1h, strat_cfg), ind.enrich(df4h, strat_cfg)

    def _get_regime(self, symbol: str, strat_cfg: StrategyConfig, tf_map: dict) -> str:
        cached = self._regime_cache.get(symbol)
        now = time.time()
        if cached and now - cached[0] < 300:
            return cached[1]
        df4h = self._get_candles_cached(symbol, tf_map["trend_high"], tf_map.get("candles_lookback", 300))
        if df4h is None or len(df4h) < strat_cfg.ema_regime + 5:
            return "range"
        regime = strategy.compute_regime(ind.enrich(df4h, strat_cfg), strat_cfg)
        self._regime_cache[symbol] = (now, regime)
        return regime

    # ---------------------------------------------------------- 主循环
    def run(self):
        self.state.add_log(f"引擎启动，模式={self.state.mode}")
        try:
            while not self._stop_event.is_set():
                try:
                    self._tick()
                except Exception as e:
                    logger.exception("tick异常")
                    self.state.add_log(f"主循环异常: {e}\n{traceback.format_exc()[-500:]}", "ERROR")
                cfg = self.cfg_store.snapshot()
                poll = cfg.get("poll_interval_sec", 15)
                self._stop_event.wait(poll)
        finally:
            self.state.engine_running = False
            self.state.add_log("引擎已停止")

    def _tick(self):
        self.cfg_store.maybe_reload()
        cfg = self.cfg_store.snapshot()
        risk_cfg = RiskConfig.build(cfg.get("risk", {}))
        strat_cfg = StrategyConfig.build(cfg.get("strategy", {}))
        cost_cfg = CostConfig.build(cfg.get("costs", {}))
        hedge_cfg = HedgeConfig.build(cfg.get("hedge", {}))
        tf_map = cfg.get("timeframes", {"entry": "15m", "trend_mid": "1h", "trend_high": "4h", "candles_lookback": 300})
        symbols = cfg.get("symbols", [])

        try:
            equity = self.exchange.get_account_equity()
        except Exception as e:
            self.state.add_log(f"获取账户权益失败: {e}", "ERROR")
            return
        self.state.update_equity(equity)
        if self.state.day_start_equity <= 0:
            self.state.day_start_equity = equity

        risk_manager = risk.RiskManager(risk_cfg)

        # 1) 管理主仓（可能触发新对冲）
        for pos in self.state.list_primaries():
            try:
                self._manage_primary(pos, risk_cfg, cost_cfg, strat_cfg, hedge_cfg, tf_map)
            except Exception as e:
                self.state.add_log(f"{pos.symbol} 主仓管理异常: {e}", "ERROR")

        # 2) 管理对冲仓
        for pos in self.state.list_hedges():
            try:
                self._manage_hedge(pos, hedge_cfg)
            except Exception as e:
                self.state.add_log(f"{pos.symbol} 对冲管理异常: {e}", "ERROR")

        # 3) 熔断检查（只影响新开主仓，风险管理动作照常执行）
        equity = self.state.equity
        cb_hit = risk_manager.daily_circuit_breaker_hit(equity, self.state.day_start_equity)
        self.state.circuit_breaker_active = cb_hit
        if cb_hit:
            return

        # 4) 扫描新信号（没有主仓的标的）
        for symbol in symbols:
            if self.state.get_primary(symbol):
                continue
            try:
                self._evaluate_entry(symbol, strat_cfg, risk_cfg, cost_cfg, tf_map, risk_manager)
            except Exception as e:
                self.state.add_log(f"{symbol} 信号评估异常: {e}", "ERROR")

    # ---------------------------------------------------------- 主仓管理
    def _manage_primary(self, pos: Position, risk_cfg: RiskConfig, cost_cfg: CostConfig,
                         strat_cfg: StrategyConfig, hedge_cfg: HedgeConfig, tf_map: dict):
        try:
            ticker = self.exchange.get_ticker(pos.symbol)
            info = self.exchange.get_contract(pos.symbol)
        except Exception as e:
            self.state.add_log(f"{pos.symbol} 获取行情失败: {e}", "ERROR")
            return

        mark = ticker["mark_price"]
        qm = info["quanto_multiplier"]
        direction = 1 if pos.side == "long" else -1
        pos.mark_price = mark
        pos.unrealized_pnl = (mark - pos.entry_price) * pos.size * qm * direction
        pos.bars_held = int(pos.holding_seconds // (15 * 60))

        self._settle_funding_if_due(pos, ticker, info)

        # 如果该主仓已经在对冲中，止损/TP1/移动止盈暂停，只保留时间止损和对冲自身的处理逻辑
        if pos.linked_id:
            self.state.upsert_position(pos)
            return

        atr_val = abs(pos.entry_price - pos.initial_stop_price)
        df15 = self._get_candles_cached(pos.symbol, tf_map["entry"], tf_map.get("candles_lookback", 300))
        if df15 is not None and len(df15) > strat_cfg.atr_period + 2:
            last_atr = float(ind.enrich(df15, strat_cfg).iloc[-1]["atr"])
            if last_atr > 0:
                atr_val = last_atr

        r_multiple = hedge_logic.compute_r_multiple(pos, mark)
        exit_reason = None

        if pos.side == "long" and mark <= pos.stop_price:
            exit_reason = "止损"
        elif pos.side == "short" and mark >= pos.stop_price:
            exit_reason = "止损"

        if not exit_reason and not pos.tp1_done:
            hit_tp1 = (pos.side == "long" and mark >= pos.take_profit_1) or \
                      (pos.side == "short" and mark <= pos.take_profit_1)
            if hit_tp1:
                self._partial_take_profit(pos, risk_cfg, info, mark)
                pos.stop_price = pos.entry_price  # 移动止损到保本位
                pos.tp1_done = True

        if not exit_reason and pos.tp1_done and atr_val:
            trail_dist = atr_val * risk_cfg.atr_trail_multiplier
            if pos.side == "long":
                new_trail = mark - trail_dist
                if new_trail > pos.stop_price:
                    pos.stop_price = new_trail
            else:
                new_trail = mark + trail_dist
                if new_trail < pos.stop_price:
                    pos.stop_price = new_trail

        if not exit_reason and pos.bars_held >= risk_cfg.time_stop_bars and r_multiple < 0.5:
            exit_reason = "时间止损"

        if exit_reason:
            self._close_leg(pos, exit_reason)
            return

        # 检查是否需要开启对冲
        regime = self._get_regime(pos.symbol, strat_cfg, tf_map)
        active_hedges = len(self.state.list_hedges())
        trigger, reason = hedge_logic.should_trigger_hedge(pos, mark, regime, hedge_cfg, active_hedges)
        if trigger:
            self._open_hedge(pos, reason, risk_cfg, hedge_cfg, info, mark, regime)
        else:
            self.state.upsert_position(pos)

    def _partial_take_profit(self, pos: Position, risk_cfg: RiskConfig, info: dict, mark: float):
        reduce_qty = int(pos.size * risk_cfg.tp1_close_ratio)
        if reduce_qty <= 0:
            return
        try:
            result = self.exchange.reduce_dual(pos.symbol, pos.side, reduce_qty)
        except Exception as e:
            self.state.add_log(f"{pos.symbol} TP1减仓失败: {e}", "ERROR")
            return

        fill_price = result.get("fill_price") or mark
        fee = result.get("fee")
        if fee is None:
            notional = reduce_qty * fill_price * info["quanto_multiplier"]
            fee = costs.taker_fee(notional, info.get("taker_fee_rate", 0.0005))

        direction = 1 if pos.side == "long" else -1
        partial_gross = (fill_price - pos.entry_price) * reduce_qty * info["quanto_multiplier"] * direction
        pos.realized_partial_pnl += partial_gross
        pos.fees_paid += fee
        pos.size -= reduce_qty
        self.state.add_log(f"{pos.symbol}[{pos.side}] TP1止盈减仓{reduce_qty}张 @≈{fill_price:.4f} 分批盈亏={partial_gross:.2f}")

    def _open_hedge(self, primary: Position, reason: str, risk_cfg: RiskConfig, hedge_cfg: HedgeConfig,
                     info: dict, mark: float, regime: str):
        qty = hedge_logic.hedge_size(primary, hedge_cfg.hedge_ratio)
        if qty <= 0:
            return
        opp_side = "short" if primary.side == "long" else "long"
        try:
            self.exchange.set_leverage(primary.symbol, risk_cfg.max_leverage)
            result = self.exchange.open_dual(primary.symbol, opp_side, qty)
        except Exception as e:
            self.state.add_log(f"{primary.symbol} 对冲开仓失败: {e}", "ERROR")
            return

        fill_price = result.get("fill_price") or mark
        qm = info["quanto_multiplier"]
        notional = qty * fill_price * qm
        entry_fee = result.get("fee")
        if entry_fee is None:
            entry_fee = costs.taker_fee(notional, info.get("taker_fee_rate", 0.0005))

        hedge_pos = Position(
            id=new_id(), symbol=primary.symbol, side=opp_side, size=qty,
            entry_price=fill_price, stop_price=0.0, initial_stop_price=0.0, take_profit_1=0.0,
            leverage=risk_cfg.max_leverage, quanto_multiplier=qm, mark_price=fill_price,
            fees_paid=entry_fee, regime=regime, reason=reason, role="hedge",
            linked_id=primary.id, hedge_open_time=now_ts(),
        )
        self.state.upsert_position(hedge_pos)
        primary.linked_id = hedge_pos.id
        self.state.upsert_position(primary)
        self.state.add_log(
            f"{primary.symbol} 触发对冲: {reason} -> 开{('多' if opp_side=='long' else '空')}对冲腿 "
            f"{qty}张 @{fill_price:.4f}"
        )

    # ---------------------------------------------------------- 对冲仓管理
    def _manage_hedge(self, hedge_pos: Position, hedge_cfg: HedgeConfig):
        primary = self.state.get_by_id(hedge_pos.linked_id) if hedge_pos.linked_id else None
        try:
            ticker = self.exchange.get_ticker(hedge_pos.symbol)
            info = self.exchange.get_contract(hedge_pos.symbol)
        except Exception as e:
            self.state.add_log(f"{hedge_pos.symbol} 对冲行情获取失败: {e}", "ERROR")
            return

        mark = ticker["mark_price"]
        qm = info["quanto_multiplier"]
        direction = 1 if hedge_pos.side == "long" else -1
        hedge_pos.mark_price = mark
        hedge_pos.unrealized_pnl = (mark - hedge_pos.entry_price) * hedge_pos.size * qm * direction
        hedge_pos.bars_held = int(hedge_pos.holding_seconds // (15 * 60))
        self._settle_funding_if_due(hedge_pos, ticker, info)

        if not primary:
            # 找不到对应主仓（可能已被外部/异常流程平掉），直接把对冲腿也平掉，避免裸露风险敞口
            self._close_leg(hedge_pos, "对应主仓已不存在，平掉孤立对冲腿")
            return

        unwind, action, reason = hedge_logic.should_unwind_hedge(primary, hedge_pos, mark, hedge_cfg)
        if not unwind:
            self.state.upsert_position(hedge_pos)
            return

        if action == "resume":
            self._close_leg(hedge_pos, reason)
            primary.linked_id = None
            self.state.upsert_position(primary)
        else:  # close_both
            self._close_leg(hedge_pos, reason)
            self._close_leg(primary, reason)

    # ---------------------------------------------------------- 通用平仓
    def _settle_funding_if_due(self, pos: Position, ticker: dict, info: dict):
        funding_next_apply = info.get("funding_next_apply", 0)
        if funding_next_apply and now_ts() >= funding_next_apply > pos.last_funding_settle_ts:
            if hasattr(self.exchange, "settle_funding"):
                delta = self.exchange.settle_funding(pos.symbol, pos.side)  # 正=盈利，负=成本
                pos.funding_paid += -delta
            else:
                funding_rate = ticker.get("funding_rate", 0.0)
                notional = pos.size * ticker["mark_price"] * info["quanto_multiplier"]
                pos.funding_paid += costs.funding_fee(notional, funding_rate, pos.side)
            pos.last_funding_settle_ts = now_ts()

    def _close_leg(self, pos: Position, exit_reason: str) -> bool:
        try:
            info = self.exchange.get_contract(pos.symbol)
            result = self.exchange.close_dual(pos.symbol, pos.side)
        except Exception as e:
            self.state.add_log(f"{pos.symbol}[{pos.side}] 平仓失败: {e}", "ERROR")
            return False

        fill_price = result.get("fill_price") or pos.mark_price
        qm = pos.quanto_multiplier
        direction = 1 if pos.side == "long" else -1
        remaining_gross = (fill_price - pos.entry_price) * pos.size * qm * direction
        gross_total = pos.realized_partial_pnl + remaining_gross

        exit_fee = result.get("fee")
        if exit_fee is None:
            notional = pos.size * fill_price * qm
            exit_fee = costs.taker_fee(notional, info.get("taker_fee_rate", 0.0005))

        total_fees = pos.fees_paid + exit_fee
        net_pnl = gross_total - total_fees - pos.funding_paid

        trade = Trade(
            id=new_id(), symbol=pos.symbol, side=pos.side, size=pos.size,
            entry_price=pos.entry_price, exit_price=fill_price,
            open_time=pos.open_time, close_time=now_ts(),
            pnl=net_pnl, gross_pnl=gross_total, fees_paid=total_fees,
            funding_paid=pos.funding_paid, exit_reason=exit_reason, role=pos.role,
        )
        self.state.record_trade(trade)
        self.state.remove_position(pos.symbol, pos.side)

        side_cn = "多" if pos.side == "long" else "空"
        role_cn = "主仓" if pos.role == "primary" else "对冲仓"
        self.state.add_log(
            f"{pos.symbol}[{side_cn}/{role_cn}] 平仓[{exit_reason}] @{fill_price:.4f} "
            f"净盈亏={net_pnl:.2f} (毛={gross_total:.2f} 手续费={total_fees:.2f} 资金费={pos.funding_paid:.2f})"
        )
        return True

    # ---------------------------------------------------------- 新开主仓评估
    def _evaluate_entry(self, symbol: str, strat_cfg: StrategyConfig, risk_cfg: RiskConfig,
                         cost_cfg: CostConfig, tf_map: dict, risk_manager: risk.RiskManager):
        lookback = tf_map.get("candles_lookback", 300)
        df15, df1h, df4h = self._fetch_multi_tf(symbol, strat_cfg, tf_map, lookback)
        if df15 is None:
            return

        try:
            info = self.exchange.get_contract(symbol)
            ticker = self.exchange.get_ticker(symbol)
        except Exception as e:
            self.state.add_log(f"{symbol} 获取合约/行情信息失败: {e}", "ERROR")
            return

        funding_rate = ticker.get("funding_rate", 0.0)
        funding_interval = info.get("funding_interval", 28800)
        taker_fee_rate = info.get("taker_fee_rate") or cost_cfg.taker_fee_rate

        sig = strategy.compute_signal(
            symbol, df15, df1h, df4h, strat_cfg,
            taker_fee_rate=taker_fee_rate, slippage_bps=cost_cfg.slippage_bps,
            funding_rate=funding_rate, funding_interval_sec=funding_interval,
            time_stop_bars=risk_cfg.time_stop_bars, atr_stop_multiplier=risk_cfg.atr_stop_multiplier,
            tp1_r_multiple=risk_cfg.tp1_r_multiple, min_net_edge_r=strat_cfg.min_net_edge_r,
        )
        self.state.set_signal(symbol, {
            "action": sig.action, "score": sig.score, "regime": sig.regime,
            "reason": sig.reason, "entry_price": sig.entry_price,
            "stop_price": sig.stop_price, "net_edge_r": sig.net_edge_r,
            "ts": now_ts(),
        })

        if sig.action == "none" or sig.score < strat_cfg.min_score_to_enter:
            return

        equity = self.state.equity
        decision = risk_manager.can_open_new(
            symbol, self.state.list_primaries(), equity,
            self.state.day_start_equity, risk_cfg.risk_per_trade_pct,
        )
        if not decision.allowed:
            self.state.add_log(f"{symbol} 信号评分={sig.score:.0f} 但风控拒绝: {decision.reason}")
            return

        mark = ticker["mark_price"]
        size = risk.position_size(
            equity, risk_cfg.risk_per_trade_pct, sig.entry_price, sig.stop_price, mark,
            info["quanto_multiplier"], risk_cfg.max_leverage,
            info["order_size_min"], info["order_size_max"],
        )
        if size <= 0:
            self.state.add_log(f"{symbol} 计算仓位为0（风险金额过小或杠杆不足），跳过")
            return

        try:
            self.exchange.set_leverage(symbol, risk_cfg.max_leverage)
            result = self.exchange.open_dual(symbol, sig.action, size)
        except Exception as e:
            self.state.add_log(f"{symbol} 下单失败: {e}", "ERROR")
            return

        fill_price = result.get("fill_price") or sig.entry_price
        qm = info["quanto_multiplier"]
        notional = size * fill_price * qm
        entry_fee = result.get("fee")
        if entry_fee is None:
            entry_fee = costs.taker_fee(notional, taker_fee_rate)

        stop_distance = abs(sig.entry_price - sig.stop_price)
        direction = 1 if sig.action == "long" else -1
        tp1_price = fill_price + stop_distance * risk_cfg.tp1_r_multiple * direction

        pos = Position(
            id=new_id(), symbol=symbol, side=sig.action, size=size,
            entry_price=fill_price, stop_price=sig.stop_price, initial_stop_price=sig.stop_price,
            take_profit_1=tp1_price, leverage=risk_cfg.max_leverage, quanto_multiplier=qm,
            mark_price=fill_price, fees_paid=entry_fee, regime=sig.regime, reason=sig.reason,
            role="primary",
        )
        self.state.upsert_position(pos)
        self.state.add_log(
            f"开仓 {symbol} {'多' if sig.action=='long' else '空'} 张数={size} @{fill_price:.4f} "
            f"评分={sig.score:.0f} 止损={sig.stop_price:.4f} TP1={tp1_price:.4f} 原因={sig.reason}"
        )

