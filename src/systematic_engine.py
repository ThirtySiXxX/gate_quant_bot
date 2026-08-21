"""
新版交易主循环——多资产 Time-Series Momentum(趋势) + Carry(资金费率) +
波动率目标(volatility targeting) + 相关性感知组合风险分配。

执行节奏（对应你确认的多周期方案）：
  - 主循环每 tick_interval_sec（默认15分钟）复核一次，是否需要调仓；
  - 短趋势用 1H EWMAC，主趋势用 4H EWMAC，大周期regime过滤用 1D；
  - 资金费Carry按合约当前实际funding_rate/funding_interval计算；
  - 组合协方差按 covariance_interval（默认4H）计算，不需要每15分钟都重算成本高的协方差矩阵
    ——本实现为了代码简单起见每个tick都会重新算一遍，但因为使用的都是已经按周期聚合好的K线，
    实际数值在同一根4H/1D K线内基本不会变化，不会出现"15分钟乱跳"的问题。

每个tick做的事：
  1) 从交易所同步真实持仓(source of truth)到本地状态，纳入统一管理(含程序重启后的持仓恢复)。
  2) 更新账户权益。
  3) 对配置的每个标的：拉取1H/4H/1D历史K线(经本地缓存的分页下载器)，计算趋势/Carry/波动率信号。
  4) 用EWMA协方差矩阵做组合层风险分配(vol targeting + 相关性感知 + 硬约束)。
  5) 对比目标仓位与当前仓位，no-trade buffer过滤掉太小的调整，其余按需下单调整到目标仓位。
  6) 平仓/减仓时结算已实现盈亏、估算手续费/资金费，写入交易记录。

EngineController 负责创建/销毁真正的 SystematicEngine 实例和后台线程，本文件不做任何终端交互。
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import carry as carry_mod
from . import costs
from . import data_fetcher
from . import portfolio as pf
from . import trend as trend_mod
from . import vol as vol_mod
from .config import ConfigStore, CostConfig, RiskConfig, SystematicConfig
from .models import Position, Trade, new_id, now_ts
from .risk import RiskManager

logger = logging.getLogger("bot.systematic_engine")


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


@dataclass
class _LocalPositionBook:
    """引擎内存里对"当前正在管理的仓位"的轻量补充记账(手续费/资金费累计)，
    独立于交易所返回的真实持仓(size/entry_price/mark_price以交易所为准，
    这里只补充交易所接口不直接提供的"这个仓位生命周期内累计手续费/资金费"这类信息)。
    仓位完全平掉后对应条目会被清除；程序重启后会重新从0开始累计(已知限制，
    不影响仓位本身的安全性，只影响"手续费/资金费"统计的精确度)。"""
    fees_paid: Dict[str, float] = None
    funding_paid: Dict[str, float] = None
    last_funding_ts: Dict[str, float] = None

    def __post_init__(self):
        self.fees_paid = self.fees_paid or {}
        self.funding_paid = self.funding_paid or {}
        self.last_funding_ts = self.last_funding_ts or {}

    def add_fee(self, symbol: str, fee: float):
        self.fees_paid[symbol] = self.fees_paid.get(symbol, 0.0) + fee

    def accrue_funding(self, symbol: str, notional: float, funding_rate: float,
                        funding_interval_sec: float):
        now = now_ts()
        last = self.last_funding_ts.get(symbol, now)
        elapsed = max(now - last, 0.0)
        if funding_interval_sec <= 0:
            self.last_funding_ts[symbol] = now
            return
        events = elapsed / funding_interval_sec
        cost = costs.funding_fee(notional, funding_rate, "long") * events if notional >= 0 else \
            costs.funding_fee(abs(notional), funding_rate, "short") * events
        self.funding_paid[symbol] = self.funding_paid.get(symbol, 0.0) + cost
        self.last_funding_ts[symbol] = now

    def pop(self, symbol: str) -> Tuple[float, float]:
        fee = self.fees_paid.pop(symbol, 0.0)
        funding = self.funding_paid.pop(symbol, 0.0)
        self.last_funding_ts.pop(symbol, None)
        return fee, funding


class SystematicEngine:
    def __init__(self, config_store: ConfigStore, exchange, state, cache_dir: str = "./data/klines"):
        self.config_store = config_store
        self.exchange = exchange
        self.state = state
        self.cache_dir = cache_dir
        self._stop_event = threading.Event()
        self._book = _LocalPositionBook()

    def stop(self):
        self._stop_event.set()

    # ---------------------------------------------------------- 主循环
    def run(self):
        self.state.add_log(f"系统性引擎启动，模式={self.state.mode}")
        try:
            while not self._stop_event.is_set():
                try:
                    self._tick()
                except Exception as e:
                    logger.exception("tick异常")
                    self.state.add_log(f"主循环异常: {e}\n{traceback.format_exc()[-500:]}", "ERROR")
                cfg = self.config_store.snapshot()
                sys_cfg = SystematicConfig.build(cfg.get("systematic", {}))
                self._stop_event.wait(max(5, sys_cfg.tick_interval_sec))
        finally:
            self.state.engine_running = False
            self.state.add_log("系统性引擎已停止")

    def _tick(self):
        self.config_store.maybe_reload()
        cfg = self.config_store.snapshot()
        symbols: List[str] = cfg.get("symbols", [])
        sys_cfg = SystematicConfig.build(cfg.get("systematic", {}))
        cost_cfg = CostConfig.build(cfg.get("costs", {}))
        risk_cfg = RiskConfig.build(cfg.get("risk", {}))

        if not symbols:
            self.state.add_log("尚未配置任何交易标的，本轮跳过", "WARN")
            return

        try:
            equity = self.exchange.get_account_equity()
        except Exception as e:
            self.state.add_log(f"获取账户权益失败: {e}", "ERROR")
            return
        self.state.update_equity(equity)
        if self.state.day_start_equity <= 0:
            self.state.day_start_equity = equity

        # 只启用账户级日亏损熔断，不重新引入ATR止损/固定止盈/时间止损。
        # 熔断一旦触发，当天保持锁定：允许减仓和平仓，但禁止开仓和加仓。
        was_circuit = self.state.circuit_breaker_active
        loss_hit = RiskManager(risk_cfg).daily_circuit_breaker_hit(equity, self.state.day_start_equity)
        self.state.circuit_breaker_active = bool(was_circuit or loss_hit)
        if self.state.circuit_breaker_active and not was_circuit:
            self.state.add_log(
                f"当日权益亏损达到 {risk_cfg.daily_loss_limit_pct:.2f}%，账户级熔断已触发："
                "今天禁止开仓/加仓，但仍允许减仓和平仓", "ERROR")

        if not self._reconcile_positions():
            self.state.add_log("持仓同步失败，本轮跳过信号计算和下单——本地持仓状态此刻不可信，"
                                "继续交易可能把真实持仓误判成空仓再次开仓，等下一轮同步成功后再继续", "ERROR")
            return

        self._handle_orphaned_positions(symbols, sys_cfg, cost_cfg)

        signals: Dict[str, pf.InstrumentSignal] = {}
        returns_by_symbol: Dict[str, pd.Series] = {}
        price_now: Dict[str, float] = {}
        contract_by_symbol: Dict[str, dict] = {}
        failed_symbols: List[str] = []

        for symbol in symbols:
            try:
                bundle = self._gather_signal(symbol, sys_cfg, cost_cfg)
            except Exception as e:
                self.state.add_log(f"{symbol} 计算信号失败: {e}", "ERROR")
                failed_symbols.append(symbol)
                continue
            if bundle is None:
                failed_symbols.append(symbol)
                continue
            sig, close_cov, contract_info, live_price = bundle
            signals[symbol] = sig
            returns_by_symbol[symbol] = vol_mod.log_returns(close_cov).dropna()
            price_now[symbol] = live_price
            contract_by_symbol[symbol] = contract_info
            self.state.set_signal(symbol, {
                "action": "long" if sig.combined_forecast > 0 else ("short" if sig.combined_forecast < 0 else "none"),
                "score": abs(sig.combined_forecast) * 5,   # 换算到0-100量级，方便和旧界面的评分列对齐
                "regime": "", "reason": (
                    f"趋势={sig.trend_forecast:.1f} Carry={sig.carry_forecast:.1f} "
                    f"合成={sig.combined_forecast:.1f} 年化波动={sig.vol_annual*100:.1f}% "
                    f"自适应风险={sig.risk_multiplier*100:.0f}% "
                    f"ER={sig.efficiency_ratio:.2f} 影线波动比={sig.range_vol_ratio:.2f}"
                ),
                "entry_price": price_now[symbol], "stop_price": 0.0,
                "net_edge_r": sig.combined_forecast / 10.0, "ts": now_ts(),
            })

        if not signals:
            self.state.add_log("本轮没有任何标的成功算出信号，跳过组合分配", "WARN")
            return

        allow_increase = not self.state.circuit_breaker_active and not failed_symbols
        if failed_symbols:
            self.state.add_log(
                "本轮部分标的信号不可用(" + ",".join(failed_symbols) + ")，"
                "为避免组合忽略已有敞口，本轮所有标的只允许减仓/平仓，禁止新增风险", "WARN")

        cov = pf.build_covariance(returns_by_symbol, sys_cfg.covariance_interval, sys_cfg)
        alloc = pf.allocate_portfolio(signals, equity, cov, sys_cfg)
        self.state.set_portfolio_snapshot({
            "target_vol_pct": sys_cfg.target_annual_vol_pct,
            "portfolio_vol_before_scale_pct": alloc.portfolio_vol_before_scale * 100,
            "scale_factor": alloc.scale_factor,
            "portfolio_conviction": alloc.portfolio_conviction,
            "average_risk_multiplier": alloc.average_risk_multiplier,
            "gross_leverage": alloc.gross_leverage,
            "diversification_benefit_pct": alloc.diversification_benefit * 100,
            "ts": now_ts(),
        })

        for symbol, target in alloc.targets.items():
            try:
                self._execute_target(symbol, target, signals[symbol], price_now[symbol],
                                      contract_by_symbol[symbol], equity, sys_cfg, cost_cfg,
                                      allow_increase=allow_increase)
            except Exception as e:
                self.state.add_log(f"{symbol} 调仓执行异常: {e}", "ERROR")

    # ---------------------------------------------------------- 信号计算
    def _gather_signal(self, symbol: str, sys_cfg: SystematicConfig, cost_cfg: CostConfig):
        short_days = sys_cfg.forecast_scale_lookback / 24.0 * 1.15 + 5
        main_days = sys_cfg.forecast_scale_lookback * 4 / 24.0 * 1.15 + 10
        regime_days = sys_cfg.min_bars_regime + sys_cfg.regime_ema_long + 30
        cov_days = short_days if sys_cfg.covariance_interval == sys_cfg.short_trend_interval else main_days

        df_short = data_fetcher.fetch_candles(self.exchange, symbol, sys_cfg.short_trend_interval,
                                               short_days, cache_dir=self.cache_dir)
        df_main = data_fetcher.fetch_candles(self.exchange, symbol, sys_cfg.main_trend_interval,
                                              main_days, cache_dir=self.cache_dir)
        df_regime = data_fetcher.fetch_candles(self.exchange, symbol, sys_cfg.regime_interval,
                                                regime_days, cache_dir=self.cache_dir)

        # 只用"已经走完"的K线算信号：K线接口通常会把当前还没收盘的那一根也一起返回，
        # 直接拿它算EWMAC/波动率/carry会导致同一根K线内信号反复抖动(价格还在变)，
        # 也和回测(只处理历史已收盘K线)的口径不一致。执行下单用的价格另外通过实时行情获取，
        # 不受这里的裁剪影响。
        df_short = data_fetcher.drop_unclosed_last_bar(df_short, sys_cfg.short_trend_interval)
        df_main = data_fetcher.drop_unclosed_last_bar(df_main, sys_cfg.main_trend_interval)
        df_regime = data_fetcher.drop_unclosed_last_bar(df_regime, sys_cfg.regime_interval)

        if len(df_short) < sys_cfg.min_bars_short or len(df_main) < sys_cfg.min_bars_main:
            self.state.add_log(f"{symbol} 历史数据不足(短趋势{len(df_short)}根/主趋势{len(df_main)}根)，跳过本轮", "WARN")
            return None

        try:
            contract_info = self.exchange.get_contract(symbol)
        except Exception as e:
            self.state.add_log(f"{symbol} 获取合约信息失败: {e}", "ERROR")
            return None

        try:
            contract_info = dict(contract_info)
            contract_info["account_taker_fee_rate"] = self.exchange.get_account_taker_fee_rate(symbol)
        except Exception:
            # 账户费率接口失败不应阻断行情信号；执行和记账会回退到配置费率。
            contract_info = dict(contract_info)
            contract_info["account_taker_fee_rate"] = None

        short_f = trend_mod.group_trend_forecast(df_short["close"], sys_cfg.short_trend_interval, sys_cfg)
        main_f = trend_mod.group_trend_forecast(df_main["close"], sys_cfg.main_trend_interval, sys_cfg)
        combined_trend = trend_mod.combine_trend(float(short_f.iloc[-1]), float(main_f.iloc[-1]), sys_cfg)

        if len(df_regime) >= sys_cfg.regime_ema_long + 5:
            regime_series = trend_mod.daily_regime_series(df_regime, sys_cfg)
            regime = str(regime_series.iloc[-1])
        else:
            regime = "range"
        gated_trend = trend_mod.apply_regime_gate(combined_trend, regime, sys_cfg)

        funding_rate = float(contract_info.get("funding_rate") or 0.0)
        funding_interval = float(contract_info.get("funding_interval") or 28800)
        carry_series = carry_mod.carry_forecast_series(df_main["close"], sys_cfg.main_trend_interval,
                                                         funding_rate, funding_interval, sys_cfg)
        carry_val = float(carry_series.iloc[-1])

        combined = pf.combine_forecast(gated_trend, carry_val, sys_cfg)
        vol_ann = float(vol_mod.price_vol_annualized(df_main["close"], sys_cfg.main_trend_interval,
                                                       lam=sys_cfg.ewma_lambda).iloc[-1])
        if vol_ann <= 0 or pd.isna(vol_ann):
            self.state.add_log(f"{symbol} 波动率估计无效，跳过本轮", "WARN")
            return None

        adaptive = vol_mod.adaptive_chop_risk_from_config(df_short, sys_cfg).iloc[-1]
        risk_multiplier = float(adaptive.get("risk_multiplier", 1.0))
        efficiency_ratio = float(adaptive.get("efficiency_ratio", 1.0))
        range_vol_ratio = float(adaptive.get("vol_ratio", 1.0))
        if not np.isfinite(risk_multiplier):
            risk_multiplier = 1.0
        if not np.isfinite(efficiency_ratio):
            efficiency_ratio = 1.0
        if not np.isfinite(range_vol_ratio):
            range_vol_ratio = 1.0

        sig = pf.InstrumentSignal(
            symbol=symbol, trend_forecast=gated_trend, carry_forecast=carry_val,
            combined_forecast=combined, vol_annual=vol_ann,
            risk_multiplier=risk_multiplier, efficiency_ratio=efficiency_ratio,
            range_vol_ratio=range_vol_ratio,
        )

        if sys_cfg.covariance_interval == sys_cfg.short_trend_interval:
            close_cov = df_short["close"]
        elif sys_cfg.covariance_interval == sys_cfg.main_trend_interval:
            close_cov = df_main["close"]
        else:
            df_cov = data_fetcher.fetch_candles(self.exchange, symbol, sys_cfg.covariance_interval,
                                                 cov_days, cache_dir=self.cache_dir)
            df_cov = data_fetcher.drop_unclosed_last_bar(df_cov, sys_cfg.covariance_interval)
            close_cov = df_cov["close"] if len(df_cov) > 5 else df_main["close"]

        # 下单执行用的价格用实时行情(mark price)，不用上面裁掉了最新未收盘K线之后的收盘价——
        # 那样会比真实市场价滞后最多一整根K线的时间，对执行价格来说没必要也不应该这么滞后。
        try:
            live_price = float(self.exchange.get_ticker(symbol)["mark_price"])
        except Exception:
            live_price = float(close_cov.iloc[-1])

        return sig, close_cov, contract_info, live_price

    # ---------------------------------------------------------- 持仓同步
    def _reconcile_positions(self) -> bool:
        """用交易所返回的真实持仓覆盖本地内存状态(source of truth)，
        既能处理程序重启后的持仓恢复，也能避免本地状态和真实账户不一致。

        返回是否同步成功；调用方(_tick)在同步失败时必须整轮跳过后续的信号计算/下单，
        不能在"本地持仓状态此刻到底对不对都不知道"的情况下继续交易——否则如果账户其实
        已经有实仓，但因为这次同步失败、本地还是启动时的空状态，就可能把已有实仓当成
        空仓重复开仓。
        """
        try:
            real_positions = self.exchange.get_dual_positions()
        except Exception as e:
            self.state.add_log(f"同步持仓失败: {e}", "ERROR")
            return False

        real_keys = set()
        for p in real_positions:
            symbol, side, size = p["contract"], p["side"], p["size"]
            if size <= 0:
                continue
            key = f"{symbol}|{side}"
            real_keys.add(key)
            existing = self.state.get_position(symbol, side)
            if existing:
                # 同一进程内停止/重开引擎时，StateStore 仍保留持仓成本，
                # 新引擎的内存账本应从它恢复，避免平仓时少算已发生费用。
                self._book.fees_paid.setdefault(symbol, existing.fees_paid)
                self._book.funding_paid.setdefault(symbol, existing.funding_paid)
                existing.size = size
                existing.mark_price = p["mark_price"]
                existing.entry_price = p["entry_price"]
                existing.leverage = p.get("leverage", existing.leverage)
                direction = 1 if side == "long" else -1
                existing.unrealized_pnl = (p["mark_price"] - p["entry_price"]) * size * existing.quanto_multiplier * direction
                self.state.upsert_position(existing)
            else:
                try:
                    qm = self.exchange.get_contract(symbol)["quanto_multiplier"]
                except Exception:
                    qm = 1.0
                direction = 1 if side == "long" else -1
                new_pos = Position(
                    id=new_id(), symbol=symbol, side=side, size=size,
                    entry_price=p["entry_price"], stop_price=0.0, initial_stop_price=0.0,
                    take_profit_1=0.0, leverage=p.get("leverage", 1.0), quanto_multiplier=qm,
                    mark_price=p["mark_price"], role="primary",
                )
                new_pos.unrealized_pnl = (p["mark_price"] - p["entry_price"]) * size * qm * direction
                self.state.upsert_position(new_pos)
                self.state.add_log(f"{symbol}[{side}] 检测到交易所已有持仓(程序重启恢复)，纳入管理")

        # 本地记录了、但交易所已经没有的仓位 -> 说明已经在别处被平掉了，清理掉本地记录
        with self.state.with_lock():
            local_keys = [k for k, p in self.state.positions.items() if p.role == "primary"]
        for key in local_keys:
            if key not in real_keys:
                symbol, side = key.split("|", 1)
                self.state.remove_position(symbol, side)
                self._book.pop(symbol)
        return True

    # ---------------------------------------------------------- 孤儿持仓处理
    def _handle_orphaned_positions(self, symbols: List[str], sys_cfg: SystematicConfig,
                                    cost_cfg: CostConfig):
        """网页"设置"页移除某个交易标的后，主循环只会遍历当前配置的标的池，
        该标的原有的持仓不会再获得任何目标仓位/退出指令，会无人管理地一直留在交易所上。
        这里在每轮开始时检测"本地持有仓位、但已经不在当前标的池里"的情况，直接市价平掉，
        避免仓位失控。这是明确的自动清仓行为，会在日志里清楚标注原因。"""
        symbol_set = set(symbols)
        orphans = [p for p in self.state.list_primaries() if p.symbol not in symbol_set]
        for pos in orphans:
            symbol, side = pos.symbol, pos.side
            try:
                contract_info = self.exchange.get_contract(symbol)
                qm = contract_info["quanto_multiplier"]
                try:
                    account_rate = self.exchange.get_account_taker_fee_rate(symbol)
                except Exception:
                    account_rate = None
                taker_fee_rate = cost_cfg.effective_taker_rate(
                    contract_info.get("taker_fee_rate"), account_rate)
                # 用明确张数的 reduce-only 市价单，而不是 size=0/auto_size；
                # 这样 Gate 返回的 left 才能与请求张数直接对应，可靠识别部分成交。
                result = self.exchange.reduce_dual(symbol, side, int(pos.size))
            except Exception as e:
                self.state.add_log(f"{symbol}[{side}] 已从标的池移除但仍有持仓，自动清仓失败: {e}，"
                                    f"请尽快去 Gate 官网手动处理，避免仓位无人管理", "ERROR")
                continue

            left = abs(float(result.get("left", 0.0) or 0.0))
            filled_qty = max(0, pos.size - int(round(left)))
            if filled_qty <= 0:
                self.state.add_log(f"{symbol}[{side}] 已从标的池移除，尝试自动清仓但未成交(left={left})，"
                                    f"下一轮会重试", "WARN")
                continue

            fill_price = result.get("fill_price") or pos.mark_price
            pos_direction = 1 if side == "long" else -1
            gross = (fill_price - pos.entry_price) * filled_qty * qm * pos_direction
            fee = result.get("fee")
            if fee is None:
                fee = costs.taker_fee(filled_qty * fill_price * qm, taker_fee_rate)
            fee_so_far = self._book.fees_paid.get(symbol, 0.0)
            funding_so_far = self._book.funding_paid.get(symbol, 0.0)
            is_full_close = filled_qty >= pos.size
            proportion = 1.0 if is_full_close else min(filled_qty / max(pos.size, 1), 1.0)
            entry_fee_share = fee_so_far * proportion
            funding_share = funding_so_far * proportion
            fee_share = entry_fee_share + fee
            net = gross - fee_share - funding_share

            trade = Trade(
                id=new_id(), symbol=symbol, side=side, size=filled_qty,
                entry_price=pos.entry_price, exit_price=fill_price,
                open_time=pos.open_time, close_time=now_ts(),
                pnl=net, gross_pnl=gross, fees_paid=fee_share, funding_paid=funding_share,
                exit_reason="标的已从配置移除，自动清仓", role="primary",
            )
            self.state.record_trade(trade)
            self.state.add_log(
                f"{symbol}[{side}] 已从标的池移除，自动清仓{filled_qty}张 @≈{fill_price:.4f} 净盈亏={net:.2f}"
                + ("（部分成交，剩余下一轮继续处理）" if filled_qty < pos.size else "")
            )
            if is_full_close:
                self.state.remove_position(symbol, side)
                self._book.pop(symbol)
            else:
                self._book.fees_paid[symbol] = max(fee_so_far - entry_fee_share, 0.0)
                self._book.funding_paid[symbol] = funding_so_far - funding_share
                pos.size -= filled_qty
                pos.fees_paid = self._book.fees_paid[symbol]
                pos.funding_paid = self._book.funding_paid[symbol]
                self.state.upsert_position(pos)

    # ---------------------------------------------------------- 调仓执行
    def _execute_target(self, symbol: str, target: pf.InstrumentTarget, sig: pf.InstrumentSignal,
                         price: float, contract_info: dict, equity: float,
                         sys_cfg: SystematicConfig, cost_cfg: CostConfig,
                         allow_increase: bool = True):
        existing_long = self.state.get_position(symbol, "long")
        existing_short = self.state.get_position(symbol, "short")
        if existing_long and existing_short:
            self.state.add_log(
                f"{symbol} 同时检测到多空两条主仓，无法安全推导净目标；本轮禁止自动下单，"
                "请先检查交易所仓位或等待人工处理", "ERROR")
            return
        current = existing_long or existing_short
        current_side = current.side if current else None
        current_size = int(current.size) if current else 0
        qm = contract_info["quanto_multiplier"]
        direction = 1 if current_side == "long" else (-1 if current_side == "short" else 0)
        current_notional = current_size * price * qm * direction

        # 资金费按估算比例持续累计到本地账本，供平仓/减仓时结算展示（近似值，见 carry.py 说明）
        if current:
            funding_rate = float(contract_info.get("funding_rate") or 0.0)
            funding_interval = float(contract_info.get("funding_interval") or 28800)
            self._book.accrue_funding(symbol, current_notional, funding_rate, funding_interval)
            current.fees_paid = self._book.fees_paid.get(symbol, current.fees_paid)
            current.funding_paid = self._book.funding_paid.get(symbol, current.funding_paid)
            self.state.upsert_position(current)

        # ⚠️ 反向执行模式：预测/波动率目标/组合风险分配/约束/调仓缓冲全部照常按 target 计算，
        # 只在这里把最终要执行的名义仓位方向对调，下面的 no-trade buffer/plan_orders
        # 全部在"实际执行方向"这个统一坐标系里工作(current_notional 本来就是真实持仓、
        # 天然就是"执行方向"，所以只需要把 target 也换算到同一坐标系即可)。
        exec_target_notional = -target.target_notional if sys_cfg.invert_direction else target.target_notional
        if sys_cfg.invert_direction and abs(target.target_notional) > 1e-9:
            self.state.add_log(
                f"{symbol} 反向执行模式已启用：计算方向为{'多' if target.target_notional>0 else '空'}，"
                f"实际将执行{'空' if target.target_notional>0 else '多'}", "WARN"
            )

        if not pf.should_rebalance(
            current_notional, exec_target_notional, equity, sig.vol_annual, sys_cfg,
            risk_multiplier=target.risk_multiplier,
        ):
            return

        actions = plan_orders(current_side, current_size, exec_target_notional, price, qm,
                               contract_info.get("order_size_min", 1))
        if not actions:
            return

        taker_fee_rate = cost_cfg.effective_taker_rate(
            contract_info.get("taker_fee_rate"), contract_info.get("account_taker_fee_rate"))

        for action, side, qty in actions:
            if qty <= 0:
                continue
            if action == "open" and not allow_increase:
                self.state.add_log(
                    f"{symbol} 本轮处于风险降级/熔断状态，跳过{'开仓' if not current else '加仓'} "
                    f"{side} {qty}张；减仓和平仓仍可正常执行", "WARN")
                continue

            # 盘口只作为新风险的执行保护，不改变趋势/Carry方向；任何减仓/平仓都不能被盘口过滤阻塞。
            if action == "open" and sys_cfg.depth_guard_enabled:
                try:
                    depth = self.exchange.estimate_market_order(
                        symbol, side, qty, is_entry=True, levels=sys_cfg.depth_levels)
                except Exception as e:
                    self.state.add_log(f"{symbol} 盘口深度读取失败，跳过本次开/加仓: {e}", "WARN")
                    continue
                depth_ok = (
                    depth.get("fill_ratio", 0.0) >= sys_cfg.min_depth_fill_ratio
                    and depth.get("spread_bps", float("inf")) <= sys_cfg.max_entry_spread_bps
                    and depth.get("slippage_bps", float("inf")) <= sys_cfg.max_entry_slippage_bps
                )
                if not depth_ok:
                    self.state.add_log(
                        f"{symbol} 盘口保护拒绝开/加仓：覆盖率={depth.get('fill_ratio',0)*100:.1f}% "
                        f"点差={depth.get('spread_bps',0):.2f}bps "
                        f"预计冲击={depth.get('slippage_bps',0):.2f}bps", "WARN")
                    continue
            try:
                if action == "open":
                    # 每次开/加仓前都强制设为全仓并**回读校验**。
                    # 只发设置请求是不够的：如果该合约已经有逐仓持仓，Gate 会拒绝切换，
                    # 请求"成功返回"但模式没变，我们就会在毫不知情的情况下按逐仓下单——
                    # 逐仓和全仓的爆仓逻辑完全不同，这是必须挡住的风险差异。
                    margin = self.exchange.ensure_cross_margin(symbol, sys_cfg.max_leverage)
                    if margin.get("margin_mode") == "isolated":
                        self.state.add_log(
                            f"{symbol} 保证金模式校验未通过，拒绝开/加仓：{margin['message']}", "ERROR")
                        continue          # 只挡开仓，不影响后面的减仓/平仓动作
                    if not margin.get("verified"):
                        self.state.add_log(
                            f"{symbol} 保证金模式未能确认：{margin['message']}", "WARN")
                    result = self.exchange.open_dual(symbol, side, qty)
                elif action == "reduce":
                    result = self.exchange.reduce_dual(symbol, side, qty)
                else:  # close
                    # 和 reduce 使用同一种明确张数的 reduce-only 单，确保 left 可校验。
                    result = self.exchange.reduce_dual(symbol, side, qty)
            except Exception as e:
                # 提交失败，不知道交易所那边实际发生了什么(可能完全没成交，也可能网络问题导致
                # 响应丢失但订单其实成交了)——保守起见直接中止这个标的本轮剩余的所有动作，
                # 不能在"平仓失败"之后还继续执行"开仓"，否则一旦平仓其实部分成交了，
                # 就会同时留下两个方向的仓位。等下一轮 _reconcile_positions() 拉真实持仓再重新决策。
                self.state.add_log(f"{symbol} {action}({side} {qty}张) 下单失败: {e}，"
                                    f"本轮该标的剩余动作全部中止，等下一轮同步真实持仓后重新评估", "ERROR")
                break

            # Gate 返回的 left 是这笔订单实际未成交的数量(IOC下单没成交的部分会被立即撤销)，
            # 不能假设 qty 都成交了——之前这里直接用请求的 qty 记账，如果只成交了一部分，
            # 本地仓位/成交记录就会和交易所真实状态错开。
            left = abs(float(result.get("left", 0.0) or 0.0))
            filled_qty = max(0, qty - int(round(left)))
            if filled_qty <= 0:
                self.state.add_log(f"{symbol} {action}({side} {qty}张) 未成交(left={left:.0f})，"
                                    f"本地不记账，下一轮重新评估", "WARN")
                continue
            partial = filled_qty < qty

            fill_price = result.get("fill_price") or price
            notional = filled_qty * fill_price * qm
            fee = result.get("fee")
            if fee is None:
                fee = costs.taker_fee(notional, taker_fee_rate)

            if action == "open":
                self._book.add_fee(symbol, fee)
                existing = self.state.get_position(symbol, side)
                if existing:
                    # 加仓：本地按成交均价近似更新持仓均价，交易所的精确均价会在下个tick的
                    # _reconcile_positions() 里覆盖修正，这里只是避免"这个tick内仪表盘暂时看不到变化"
                    new_size = existing.size + filled_qty
                    existing.entry_price = (existing.entry_price * existing.size + fill_price * filled_qty) / max(new_size, 1)
                    existing.size = new_size
                    existing.mark_price = fill_price
                    existing.fees_paid = self._book.fees_paid.get(symbol, 0.0)
                    existing.funding_paid = self._book.funding_paid.get(symbol, 0.0)
                    self.state.upsert_position(existing)
                else:
                    new_pos = Position(
                        id=new_id(), symbol=symbol, side=side, size=filled_qty,
                        entry_price=fill_price, stop_price=0.0, initial_stop_price=0.0,
                        take_profit_1=0.0, leverage=sys_cfg.max_leverage, quanto_multiplier=qm,
                        mark_price=fill_price, fees_paid=self._book.fees_paid.get(symbol, 0.0),
                        funding_paid=self._book.funding_paid.get(symbol, 0.0), role="primary",
                    )
                    self.state.upsert_position(new_pos)
                self.state.add_log(
                    f"{symbol} 开/加仓 {'多' if side=='long' else '空'} {filled_qty}张 @≈{fill_price:.4f} "
                    f"(forecast={target.forecast:.1f} 自适应风险={target.risk_multiplier*100:.0f}% "
                    f"目标权重={target.target_weight*100:.1f}%)"
                    + (f" [部分成交，目标{qty}张]" if partial else "")
                )
            else:
                pos = self.state.get_position(symbol, side)
                entry_price = pos.entry_price if pos else fill_price
                pos_direction = 1 if side == "long" else -1
                gross = (fill_price - entry_price) * filled_qty * qm * pos_direction
                total_fee_so_far = self._book.fees_paid.get(symbol, 0.0)
                total_funding_so_far = self._book.funding_paid.get(symbol, 0.0)
                # close 动作如果只是部分成交，交易所上这条腿并没有真正清空，不能当"完全平仓"来
                # 结清全部历史手续费/资金费——只有确认成交量达到了当前仓位全部张数才算真正平完。
                is_full_close = action == "close" and (not pos or filled_qty >= pos.size)
                if is_full_close:
                    entry_fee_share = total_fee_so_far
                    funding_share = total_funding_so_far
                else:
                    # 减仓/部分平仓要按成交仓位比例分摊历史开仓费和资金费，
                    # 否则前面每笔减仓的净盈亏都会被高估，所有旧成本又会堆到最后一笔。
                    proportion = min(filled_qty / max(pos.size if pos else filled_qty, 1), 1.0)
                    entry_fee_share = total_fee_so_far * proportion
                    funding_share = total_funding_so_far * proportion
                    self._book.fees_paid[symbol] = max(total_fee_so_far - entry_fee_share, 0.0)
                    self._book.funding_paid[symbol] = total_funding_so_far - funding_share
                fee_share = entry_fee_share + fee
                net = gross - fee_share - funding_share

                trade = Trade(
                    id=new_id(), symbol=symbol, side=side, size=filled_qty,
                    entry_price=entry_price, exit_price=fill_price,
                    open_time=pos.open_time if pos else now_ts(), close_time=now_ts(),
                    pnl=net, gross_pnl=gross, fees_paid=fee_share, funding_paid=funding_share,
                    exit_reason=("组合再平衡" if action == "reduce" else "调仓平仓/反向"), role="primary",
                )
                self.state.record_trade(trade)
                self.state.add_log(
                    f"{symbol} {'减仓' if action=='reduce' else '平仓'} {'多' if side=='long' else '空'} "
                    f"{filled_qty}张 @≈{fill_price:.4f} 净盈亏={net:.2f} (手续费={fee_share:.2f} 资金费={funding_share:.2f})"
                    + (f" [部分成交，目标{qty}张，剩余留待下一轮]" if partial else "")
                )
                if is_full_close:
                    self.state.remove_position(symbol, side)
                    self._book.pop(symbol)
                elif pos:
                    pos.size -= filled_qty
                    pos.fees_paid = self._book.fees_paid.get(symbol, 0.0)
                    pos.funding_paid = self._book.funding_paid.get(symbol, 0.0)
                    self.state.upsert_position(pos)

                # 反手的第一步若只平掉一部分，绝不能继续执行下一步开反向仓；
                # 下一轮先同步交易所真实仓位，再重新规划剩余动作。
                if partial:
                    break
