"""Replay/live decision parity with synthetic market data and a local paper account."""
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch
import tempfile
import unittest

import numpy as np
import pandas as pd

from src import ownership, strategy_signals, vol
from src.backtest import SymbolBacktestInputs, run_portfolio_backtest
from src.config import CostConfig, RiskConfig, SystematicConfig
from src.dashboard_web import create_app
from src.exchange_paper import PaperExchange
from src.models import Position
from src.portfolio import InstrumentSignal, InstrumentTarget, PortfolioAllocationResult, allocate_portfolio, should_rebalance
from src.risk import RiskManager, daily_risk_state
from src.state import StateStore
from src.systematic_engine import SystematicEngine
from src.strategy_execution import decide_execution, build_order_plan
from src.execution_timing import ExecutionTiming, TimingState
from src.position_sizing import EntrySizingBook


def contract(maximum):
    return dict(quanto_multiplier=1., leverage_min=1, leverage_max=maximum,
                order_size_min=1, order_size_max=1_000_000, taker_fee_rate=.0005)


def config(**overrides):
    return SystematicConfig(**dict(dict(
        short_trend_interval="1h", main_trend_interval="1h", regime_interval="1h",
        covariance_interval="1h", min_bars_short=1, min_bars_main=1, min_bars_regime=1,
        regime_ema_long=1, depth_guard_enabled=False, no_trade_buffer_pct=0,
        execution_timing={"enabled": False}), **overrides))


class CausalSignalTests(unittest.TestCase):
    def test_dynamic_risk_budget_scaling_preserves_signal_and_rebalance_units(self):
        cfg = config(target_annual_vol_pct=10, max_leverage=4,
                     max_instrument_exposure_pct=55, max_correlated_group_exposure_pct=60,
                     no_trade_buffer_pct=25, position_sizing_mode="volatility")
        signals = {"ETH_USDT": InstrumentSignal("ETH_USDT", 6, 0, 6, .5, risk_multiplier=.7)}
        covariance = pd.DataFrame([[.25]], index=signals, columns=signals)
        original = allocate_portfolio(signals, 10000, covariance, cfg).targets["ETH_USDT"]
        for factor in (1, 5, 10, 20, 40):
            scaled_cfg = replace(cfg, target_annual_vol_pct=10*factor,
                                 max_instrument_exposure_pct=55*factor,
                                 max_correlated_group_exposure_pct=60*factor, max_leverage=200)
            scaled = allocate_portfolio(signals, 10000, covariance, scaled_cfg).targets["ETH_USDT"]
            self.assertAlmostEqual(scaled.target_notional, original.target_notional*factor)
            self.assertEqual(scaled.forecast, original.forecast)
            for held in (0, 500, 1000, 3000):
                self.assertEqual(should_rebalance(held, original.target_notional, 10000, .5, cfg),
                                 should_rebalance(held*factor, scaled.target_notional, 10000, .5, scaled_cfg))

    def test_covariance_every_prefix_matches_live_without_future_warmup(self):
        rng = np.random.default_rng(7)
        returns = pd.DataFrame(rng.normal(0, .01, (80, 2)), columns=["BTC", "ETH"])
        _, replay, _ = vol.ewma_covariance_series(returns)
        for end in (1, 2, 5, 19, 20, 21, 50, 80):
            with self.subTest(end=end):
                np.testing.assert_allclose(replay[end-1], vol.ewma_covariance_matrix(returns.iloc[:end]))
        changed = returns.copy()
        changed.iloc[5:] = 999
        _, changed_replay, _ = vol.ewma_covariance_series(changed)
        np.testing.assert_array_equal(replay[:5], changed_replay[:5])

    def test_signal_full_history_matches_closed_prefix_and_missing_carry_is_zero(self):
        n, end = 600, 320
        prices = 100 * np.exp(np.cumsum(np.random.default_rng(19).normal(.0002, .003, n)))
        frame = pd.DataFrame(dict(timestamp=np.arange(n)*3600+1_700_000_000,
                                  open=prices, high=prices*1.003, low=prices*.997,
                                  close=prices, volume=1000.))
        cfg = config()
        full = strategy_signals.prepare_features(frame, frame, frame, None, 28800, cfg)
        closed = frame.iloc[:end]
        prefix = strategy_signals.prepare_features(closed, closed, closed, None, 28800, cfg)
        timestamp = frame.timestamp.iloc[end]
        a = strategy_signals.signal_at("ETH_USDT", full, timestamp, cfg)
        b = strategy_signals.signal_at("ETH_USDT", prefix, timestamp, cfg)
        self.assertIsNotNone(a)
        self.assertEqual(a, b)
        self.assertEqual(a.carry_forecast, 0)
        self.assertEqual(a.timing_feature["bar_ts"], frame.timestamp.iloc[end-1])


class RiskExitPriorityTests(unittest.TestCase):
    def plan(self, cause, side, force_risk_reduction):
        cfg = config(execution_timing={"enabled": True, "trail_atr": 3.})
        timing = ExecutionTiming()
        timing.states["ETH_USDT"] = TimingState(last_bar=3600, last_fill_bar=0,
            entry_price=100., best_close=110. if side == 1 else 90.,
            weak_count=3 if cause == "weak" else 0)
        # The model asks for a smaller holding. The timing rule asks to exit it.
        feature = dict(bar_ts=7200, bar_seconds=3600, quality=0. if cause == "weak" else .9,
            extension=0., close=101. if side == 1 else 99., atr=2., recent_high=112., recent_low=88.,
            long_run=5, short_run=5, breakout_long=True, breakout_short=True)
        if cause == "weak":
            timing.states["ETH_USDT"].best_close = 100.
        signal = InstrumentSignal("ETH_USDT", 0, 0, 0 if cause == "weak" else side*10, .2,
                                  short_forecast=side*10, main_forecast=side*10, timing_feature=feature)
        sizing = EntrySizingBook()
        sizing.bind("ETH_USDT", side*1000, 100000)
        return decide_execution("ETH_USDT", InstrumentTarget("ETH_USDT", side*10, side*600, .1, .1),
                                signal, side*100000, 10000, cfg, timing, sizing, allow_increase=False,
                                force_risk_reduction=force_risk_reduction)

    def test_circuit_never_replaces_atr_or_weak_signal_exit_with_partial_reduction(self):
        for cause in ("atr", "weak"):
            for direction, side in ((1, "long"), (-1, "short")):
                with self.subTest(cause=cause, side=side):
                    for force_risk_reduction in (False, True):
                        plan = self.plan(cause, direction, force_risk_reduction)
                        self.assertEqual(plan.target_notional, 0)
                        self.assertTrue(plan.decision.force_rebalance)
                        self.assertIn("ATR" if cause == "atr" else "弱信号", plan.decision.reason)
                        actions, ticket = build_order_plan("ETH_USDT", plan, side, 1000, 100,
                                                          contract(200), .0005, 2)
                        self.assertEqual(actions, [("close", side, 1000)])
                        self.assertIsNone(ticket)


class AdapterParityTests(unittest.TestCase):
    def replay(self, symbol, maximum, enabled=False, inverted=False, crash=False, atr_exit=False,
               daily_circuit=False, sizing_mode="fixed_margin", allocation_scale=1, growing=False, ml_gate=False):
        n = 48
        timestamps = np.arange(n)*3600+1_700_000_000
        prices = np.full(n, 100.)
        prices[6:9], prices[9:16], prices[16:] = 100.5, 101., 100.2
        if crash:
            prices[6:] = 98.
        if atr_exit:
            prices[3:6], prices[6:] = 104., 98.
        frame = pd.DataFrame(dict(timestamp=timestamps, open=prices, high=prices+1,
                                  low=prices-1, close=prices, volume=1000.))
        limits = [dict(risk_limit=1_000_000, leverage_max=maximum)]
        sb = SymbolBacktestInputs(symbol, frame, frame, frame, frame, 0., 28800, 1., .0005,
                                 funding_history=pd.DataFrame(dict(timestamp=timestamps, funding_rate=0.)),
                                 leverage_min=1, leverage_max=maximum, order_size_max=1_000_000,
                                 risk_limit_tiers=limits)
        cfg = config(execution_timing={"enabled": enabled, "symbols": [symbol],
                                       "trail_atr": 3. if atr_exit else 0.}, invert_direction=inverted,
                     position_sizing_mode=sizing_mode, max_leverage=maximum,
                     ml_model_path="fixture-model" if ml_gate else "")
        cost = CostConfig(slippage_bps=2)
        risk = RiskConfig(daily_loss_limit_enabled=daily_circuit, daily_loss_limit_pct=8)

        def signal_at(sym, data, timestamp, _cfg):
            timestamp = float(timestamp)
            i = int((timestamp-timestamps[0])/3600)
            f = 10 if 2 <= i < 6 or 16 <= i < 21 else (5 if 6 <= i < 9 else (-10 if 9 <= i < 16 else 0))
            if growing and (4 <= i < 6 or 12 <= i < 14):
                f *= 1.4
            feature = dict(bar_ts=timestamp-3600, bar_seconds=3600, quality=.9,
                           extension=0., close=prices[max(0, i-1)], atr=.5 if atr_exit else 2., recent_high=110., recent_low=90.,
                           long_run=5, short_run=5, breakout_long=True, breakout_short=True)
            prediction = {"status": "ok", "long": .1 if i < 6 else .8, "short": .8} if ml_gate else None
            return InstrumentSignal(sym, f, 0, f, .2, short_forecast=f, main_forecast=f,
                                    timing_feature=feature, ml_entry=prediction)

        def allocate(signals, *args):
            return PortfolioAllocationResult(targets={s: InstrumentTarget(s, sig.combined_forecast,
                sig.combined_forecast*100*allocation_scale, .1, .1) for s, sig in signals.items()})

        with patch("src.strategy_signals.signal_at", side_effect=signal_at), \
             patch("src.portfolio.allocate_portfolio", side_effect=allocate):
            result = run_portfolio_backtest([sb], cfg, cost, 10000, risk_cfg=risk)

        with tempfile.TemporaryDirectory() as temp:
            clock = [float(timestamps[0])]
            mark = [prices[0]]
            md = Mock()
            md.get_contract.side_effect = lambda s: contract(maximum)
            md.get_entry_contract.side_effect = lambda s: contract(maximum)
            md.get_risk_limit_tiers.return_value = limits
            md.get_account_taker_fee_rate.return_value = .0005
            md.get_ticker.side_effect = lambda s: {"mark_price": mark[0]}
            ex = PaperExchange(md, 10000, slippage_bps=2)
            state = StateStore(str(Path(temp)/"state.sqlite3"))
            engine = SystematicEngine(None, ex, state, str(Path(temp)/"klines"))
            actual = []
            open_order, reduce_order = ex.open_dual, ex.reduce_dual

            def open_record(s, side, qty):
                action = "add" if state.get_position(s, side) else "open"
                margin = ex.get_margin_mode(s)
                self.assertEqual(margin["margin_mode"], "cross")
                self.assertEqual(margin["cross_leverage_limit"], maximum)
                fill = open_order(s, side, qty)
                actual.append((clock[0], action, side, qty, fill["fill_price"], fill["fee"]))
                return fill

            def reduce_record(s, side, qty):
                action = "close" if qty == state.get_position(s, side).size else "reduce"
                fill = reduce_order(s, side, qty)
                actual.append((clock[0], action, side, qty, fill["fill_price"], fill["fee"]))
                return fill

            ex.open_dual, ex.reduce_dual = open_record, reduce_record
            with patch("src.systematic_engine.now_ts", side_effect=lambda: clock[0]), \
                 patch("src.state.now_ts", side_effect=lambda: clock[0]):
                state.update_equity(10000, risk_cfg=risk)
                for i, timestamp in enumerate(timestamps):
                    clock[0], mark[0] = float(timestamp), prices[i]
                    equity = ex.get_account_equity()
                    state.update_equity(equity, risk_cfg=risk)
                    if i < 2:  # covariance requires the first completed return
                        continue
                    sig = signal_at(symbol, None, timestamp, cfg)
                    target = allocate({symbol: sig}).targets[symbol]
                    engine._execute_target(symbol, target, sig, mark[0], contract(maximum), equity,
                                           cfg, cost, allow_increase=not state.circuit_breaker_active)
            expected = [(e["time"], e["action"], e["side"], e["quantity"], e["price"], e["fee"])
                        for e in result.executions]
            self.assertEqual(actual, expected)
            self.assertFalse(state.positions)
            self.assertAlmostEqual(ex.get_account_equity(), result.final_equity, places=7)
            self.assertGreaterEqual(len(actual), 2)
            return result

    def test_btc_eth_sol_and_alt_equivalent_margin_use_identical_orders(self):
        for symbol, maximum in [("BTC_USDT", 200), ("ETH_USDT", 200), ("SOL_USDT", 100),
                                ("DOGE_USDT", 20), ("XPL_USDT", 10)]:
            with self.subTest(symbol=symbol):
                result = self.replay(symbol, maximum)
                ticket = result.executions[0]["entry_ticket"]
                self.assertEqual(ticket["leverage"], maximum)
                self.assertEqual(ticket["desired_notional"], 100000 if symbol[:3] in ("BTC", "ETH", "SOL") else 10000)

    def test_timing_and_inversion_preserve_adapter_parity(self):
        for enabled, inverted in [(True, False), (True, True), (False, True)]:
            with self.subTest(enabled=enabled, inverted=inverted):
                self.replay("ETH_USDT", 200, enabled, inverted)

    def test_daily_circuit_blocks_new_entries_but_permits_exit_in_both_adapters(self):
        result = self.replay("BTC_USDT", 200, crash=True, daily_circuit=True)
        self.assertEqual(sum(e["action"] == "open" for e in result.executions), 1)
        self.assertTrue(any("熔断" in reason for reason in result.execution_diagnostics["BTC_USDT"]["entry_blocks"]))

    def test_atr_closes_remaining_position_during_circuit_in_both_adapters(self):
        result = self.replay("ETH_USDT", 200, enabled=True, atr_exit=True, daily_circuit=True)
        event = next(e for e in result.executions if e["time"] == 1_700_000_000+7*3600)
        self.assertEqual(event["action"], "close")
        self.assertEqual(event["position_after"], 0)
        self.assertIn("ATR", event["reason"])

    def test_daily_loss_gate_stays_latched_until_next_window(self):
        cfg = RiskConfig(daily_loss_limit_enabled=True, daily_loss_limit_pct=8)
        day = daily_risk_state(10000, 0, 0, False, 1000, cfg)
        day = daily_risk_state(9100, *day, 1100, cfg)
        self.assertTrue(day[2])
        day = daily_risk_state(11000, *day, 1200, cfg)
        self.assertTrue(day[2])
        day = daily_risk_state(11000, *day, 87400, cfg)
        self.assertEqual(day, (11000, 87400, False))

    def test_disabled_circuit_permits_later_entries_after_loss_in_both_adapters(self):
        result = self.replay("BTC_USDT", 200, crash=True)
        self.assertGreater(sum(e["action"] == "open" for e in result.executions), 1)
        self.assertFalse(any("熔断" in reason for reason in result.execution_diagnostics["BTC_USDT"]["entry_blocks"]))

    def test_dynamic_and_amplified_dynamic_use_identical_cross_margin_orders(self):
        for scale in (1, 5, 10, 20, 40):
            for enabled, inverted in ((True, False), (True, True), (False, False)):
                with self.subTest(scale=scale, timing=enabled, inverted=inverted):
                    result = self.replay("ETH_USDT", 200, enabled=enabled, inverted=inverted,
                                         sizing_mode="volatility", allocation_scale=scale, growing=True)
                    self.assertTrue(any(e["action"] == "add" for e in result.executions))

    def test_ml_entry_gate_preserves_adapter_parity_for_fixed_and_dynamic_sizing(self):
        for mode in ("fixed_margin", "volatility"):
            with self.subTest(mode=mode):
                result = self.replay("ETH_USDT", 200, enabled=True, sizing_mode=mode, ml_gate=True)
                self.assertTrue(any("ML入场过滤" in reason for reason in result.execution_diagnostics["ETH_USDT"]["entry_blocks"]))


class DisabledDailyRiskTests(unittest.TestCase):
    def test_old_config_defaults_to_disabled_and_clears_latch_without_resetting_pnl(self):
        cfg = RiskConfig.build({"daily_loss_limit_pct": 8})
        self.assertFalse(cfg.daily_loss_limit_enabled)
        self.assertEqual(daily_risk_state(8000, 10000, 1000, True, 1100, cfg),
                         (10000, 1000, False))
        self.assertEqual(daily_risk_state(8000, 10000, 1000, True, 1100),
                         (10000, 1000, False))
        self.assertEqual(daily_risk_state(8000, 10000, 1000, True, 87400, cfg),
                         (8000, 87400, False))

    def test_risk_manager_obeys_same_flag_and_keeps_other_guards(self):
        cfg = RiskConfig()
        risk = RiskManager(cfg)
        self.assertFalse(risk.daily_circuit_breaker_hit(8000, 10000))
        self.assertTrue(risk.can_open_new("ETH_USDT", [], 8000, 10000, 1).allowed)
        self.assertFalse(risk.can_open_new("ETH_USDT", [], 8000, 10000, 21).allowed)
        cfg.daily_loss_limit_enabled = True
        self.assertTrue(risk.daily_circuit_breaker_hit(8000, 10000))
        self.assertFalse(risk.can_open_new("ETH_USDT", [], 8000, 10000, 1).allowed)

    def test_state_and_api_report_disabled_after_previously_active_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            state = StateStore(str(Path(temp)/"state.sqlite3"))
            cfg = RiskConfig(daily_loss_limit_enabled=True)
            with patch("src.state.now_ts", return_value=1000):
                state.update_equity(10000, risk_cfg=cfg)
            with patch("src.state.now_ts", return_value=1100):
                state.update_equity(8000, risk_cfg=cfg)
                self.assertTrue(state.circuit_breaker_active)
                config_store = SimpleNamespace(snapshot=lambda: {"risk": {"daily_loss_limit_pct": 8}})
                client = create_app(state, config_store, None, None, None).test_client()
                body = client.get("/api/state").json
                self.assertFalse(body["daily_loss_limit_enabled"])
                self.assertFalse(body["circuit_breaker"])
                state.update_equity(8000, risk_cfg=RiskConfig())
                self.assertFalse(state.circuit_breaker_active)
                self.assertEqual(state.day_start_equity, 10000)


class AdoptionSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = StateStore(str(Path(self.temp.name)/"state.sqlite3"))
        self.exchange = Mock()
        self.engine = SystematicEngine(None, self.exchange, self.state, str(Path(self.temp.name)/"klines"))
        self.position = Position(id="fixture", symbol="ETH_USDT", side="long", size=10, entry_price=100,
                                 stop_price=0, initial_stop_price=0, take_profit_1=0, leverage=200,
                                 quanto_multiplier=1, mark_price=100, role="external")
        self.state.upsert_position(self.position)
        self.state.external_positions = ["ETH_USDT|long"]
        self.engine._external_keys = {"ETH_USDT|long"}
        config_store = SimpleNamespace(snapshot=lambda: {"mode": "paper", "systematic": {}})
        controller = SimpleNamespace(engine=self.engine, is_running=lambda: True)
        self.client = create_app(self.state, config_store, None, controller, None,
                                 universe_service=Mock()).test_client()

    def test_api_immediately_publishes_role_and_reconcile_preserves_it(self):
        response = self.client.post("/api/positions/adopt", json={"symbol": "ETH_USDT", "side": "long"})
        self.assertTrue(response.json["ok"])
        body = self.client.get("/api/state").json
        self.assertEqual(body["positions"][0]["role"], "primary")
        self.assertEqual(body["summary"]["external_position_count"], 0)
        self.assertEqual(body["summary"]["open_position_count"], 1)
        self.assertEqual(self.state.external_positions, [])
        self.assertEqual(self.engine._external_keys, set())
        self.assertTrue(ownership.is_owned(self.temp.name, "paper", "ETH_USDT", "long"))
        self.assertFalse(ownership.is_owned(self.temp.name, "live", "ETH_USDT", "long"))
        self.exchange.get_dual_positions.return_value = [dict(contract="ETH_USDT", side="long", size=10,
            mark_price=100, entry_price=100, cross_leverage_limit=200)]
        self.assertTrue(self.engine._reconcile_positions(SystematicConfig()))
        self.assertEqual(self.position.role, "primary")
        self.exchange.open_dual.assert_not_called()
        self.exchange.reduce_dual.assert_not_called()

    def test_persistence_failure_does_not_publish_false_adoption(self):
        with patch("src.ownership.os.replace", side_effect=OSError("fixture disk failure")):
            response = self.client.post("/api/positions/adopt", json={"symbol": "ETH_USDT", "side": "long"})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.json["ok"])
        self.assertEqual(self.client.get("/api/state").json["positions"][0]["role"], "external")
        self.assertEqual(self.engine._external_keys, {"ETH_USDT|long"})
        self.assertFalse(ownership.is_owned(self.temp.name, "paper", "ETH_USDT", "long"))
        self.assertFalse(list(Path(self.temp.name).glob(".ownership-*.tmp")))

    def test_disappeared_position_cannot_be_registered(self):
        self.state.remove_position("ETH_USDT", "long")
        with self.assertRaises(ValueError):
            self.engine.adopt_external("ETH_USDT", "long")
        self.assertFalse(ownership.is_owned(self.temp.name, "paper", "ETH_USDT", "long"))
