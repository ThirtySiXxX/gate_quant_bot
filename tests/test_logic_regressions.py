from __future__ import annotations

import math
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src import data_fetcher, updater
from src.backtest import SymbolBacktestInputs, run_portfolio_backtest
from src.config import CostConfig, SystematicConfig
from src.exchange_gate import estimate_book_fill
from src.models import Position
from src.portfolio import (
    InstrumentSignal,
    InstrumentTarget,
    allocate_portfolio,
    should_rebalance,
)
from src.systematic_engine import SystematicEngine
from src.vol import adaptive_chop_risk_series
from src.walkforward import run_walk_forward


class UpdaterVersionTests(unittest.TestCase):
    def test_parse_version_requires_an_exact_semver(self):
        self.assertEqual(updater.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(updater.parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(updater.parse_version("release-1.2.3"), (0, 0, 0))
        self.assertEqual(updater.parse_version("1.2.3-beta"), (0, 0, 0))

    def test_changelog_matching_does_not_use_version_substrings(self):
        text = "## 11.0.0 — later\nwrong\n\n## 1.0.0 — wanted\nright\n"
        section = updater.extract_changelog_section(text, "1.0.0")
        self.assertIn("right", section)
        self.assertNotIn("wrong", section)


class PortfolioConvictionTests(unittest.TestCase):
    def test_weak_forecast_keeps_one_tenth_of_strong_forecast_risk(self):
        cfg = SystematicConfig(
            target_annual_vol_pct=10,
            max_instrument_exposure_pct=1000,
            max_correlated_group_exposure_pct=1000,
            max_leverage=1000,
        )
        cov = pd.DataFrame([[0.25]], index=["BTC_USDT"], columns=["BTC_USDT"])

        def alloc(forecast: float):
            signal = InstrumentSignal("BTC_USDT", forecast, 0.0, forecast, 0.5)
            return allocate_portfolio({"BTC_USDT": signal}, 10_000, cov, cfg)

        weak = alloc(1.0)
        strong = alloc(10.0)
        self.assertAlmostEqual(weak.portfolio_conviction, 0.1)
        self.assertAlmostEqual(strong.portfolio_conviction, 1.0)
        self.assertAlmostEqual(
            strong.targets["BTC_USDT"].target_notional
            / weak.targets["BTC_USDT"].target_notional,
            10.0,
        )

    def test_adaptive_risk_overlay_is_not_scaled_back_up(self):
        cfg = SystematicConfig(
            target_annual_vol_pct=10,
            max_instrument_exposure_pct=1000,
            max_correlated_group_exposure_pct=1000,
            max_leverage=1000,
        )
        cov = pd.DataFrame([[0.25]], index=["BTC_USDT"], columns=["BTC_USDT"])
        full = InstrumentSignal("BTC_USDT", 10, 0, 10, 0.5, risk_multiplier=1.0)
        reduced = InstrumentSignal("BTC_USDT", 10, 0, 10, 0.5, risk_multiplier=0.4)
        full_alloc = allocate_portfolio({"BTC_USDT": full}, 10_000, cov, cfg)
        reduced_alloc = allocate_portfolio({"BTC_USDT": reduced}, 10_000, cov, cfg)
        self.assertAlmostEqual(
            reduced_alloc.targets["BTC_USDT"].target_notional
            / full_alloc.targets["BTC_USDT"].target_notional,
            0.4,
        )
        self.assertAlmostEqual(reduced_alloc.average_risk_multiplier, 0.4)

    def test_only_extreme_adaptive_reduction_bypasses_exit_buffer(self):
        cfg = SystematicConfig(
            target_annual_vol_pct=10,
            no_trade_buffer_pct=25,
            exit_buffer_multiplier=3,
        )
        # reference_scale = 10_000 * 10% / 20% = 5_000。从5,000降到2,500的差额
        # 小于3倍退出缓冲(3,750)，但大于正常缓冲(1,250)。
        self.assertFalse(should_rebalance(5000, 2500, 10_000, 0.20, cfg))
        self.assertTrue(should_rebalance(
            5000, 2500, 10_000, 0.20, cfg, risk_multiplier=0.4
        ))
        self.assertFalse(should_rebalance(
            5000, 2500, 10_000, 0.20, cfg, risk_multiplier=0.5
        ))


class AdaptiveChopRiskTests(unittest.TestCase):
    @staticmethod
    def _ohlc(close: np.ndarray, range_pct: np.ndarray) -> pd.DataFrame:
        open_ = np.r_[close[0], close[:-1]]
        high = np.maximum(open_, close) * (1.0 + range_pct)
        low = np.minimum(open_, close) * (1.0 - range_pct)
        return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    def test_high_volatility_chop_reduces_risk(self):
        quiet = 100.0 + np.arange(120) * 0.01
        chop = 101.2 + np.tile([3.0, -3.0], 30)
        close = np.r_[quiet, chop]
        ranges = np.r_[np.full(len(quiet), 0.001), np.full(len(chop), 0.025)]
        out = adaptive_chop_risk_series(self._ohlc(close, ranges))
        self.assertLess(float(out["efficiency_ratio"].iloc[-1]), 0.10)
        self.assertGreater(float(out["vol_ratio"].iloc[-1]), 1.20)
        self.assertLess(float(out["risk_multiplier"].iloc[-1]), 0.60)
        self.assertGreaterEqual(float(out["risk_multiplier"].min()), 0.35)

    def test_high_volatility_directional_trend_keeps_risk(self):
        quiet = 100.0 + np.arange(120) * 0.01
        trend = quiet[-1] + np.arange(1, 61) * 2.0
        close = np.r_[quiet, trend]
        ranges = np.r_[np.full(len(quiet), 0.001), np.full(len(trend), 0.02)]
        out = adaptive_chop_risk_series(self._ohlc(close, ranges))
        self.assertGreater(float(out["efficiency_ratio"].iloc[-1]), 0.90)
        self.assertGreater(float(out["vol_ratio"].iloc[-1]), 1.20)
        self.assertGreater(float(out["risk_multiplier"].iloc[-1]), 0.95)

    def test_disabled_overlay_is_neutral(self):
        cfg = SystematicConfig(adaptive_risk_enabled=False)
        close = 100.0 + np.sin(np.arange(100)) * 5.0
        frame = self._ohlc(close, np.full(100, 0.03))
        from src.vol import adaptive_chop_risk_from_config
        out = adaptive_chop_risk_from_config(frame, cfg)
        self.assertTrue(np.allclose(out["risk_multiplier"].values, 1.0))


class OrderBookGuardTests(unittest.TestCase):
    def test_market_buy_vwap_spread_and_coverage(self):
        result = estimate_book_fill(
            asks=[(101, 2), (102, 3)],
            bids=[(99, 4), (98, 4)],
            qty=4,
            is_buy=True,
        )
        self.assertAlmostEqual(result["fill_ratio"], 1.0)
        self.assertAlmostEqual(result["vwap"], 101.5)
        self.assertAlmostEqual(result["spread_bps"], 200.0)
        self.assertAlmostEqual(result["slippage_bps"], 150.0)

    def test_insufficient_depth_is_reported(self):
        result = estimate_book_fill(
            asks=[(101, 1)], bids=[(99, 1)], qty=4, is_buy=False
        )
        self.assertAlmostEqual(result["fill_ratio"], 0.25)
        self.assertAlmostEqual(result["available_qty"], 1.0)


class FundingHistoryLimitTests(unittest.TestCase):
    def test_request_is_clamped_to_gate_history_window(self):
        fixed_now = 2_000_000_000

        class Exchange:
            def __init__(self):
                self.calls = []

            def get_funding_rate_history(self, contract, from_ts, to_ts, limit):
                self.calls.append((from_ts, to_ts, limit))
                return pd.DataFrame(
                    {"timestamp": [float(from_ts)], "funding_rate": [0.0001]}
                )

        exchange = Exchange()
        with tempfile.TemporaryDirectory() as tmp, patch(
            "src.data_fetcher.time.time", return_value=fixed_now
        ):
            result = data_fetcher.fetch_funding_history(
                exchange, "BTC_USDT", 365, cache_dir=tmp, use_cache=False
            )

        self.assertEqual(len(exchange.calls), 1)
        earliest_allowed = fixed_now - data_fetcher.FUNDING_HISTORY_MAX_DAYS * 86400
        self.assertGreaterEqual(exchange.calls[0][0], earliest_allowed)
        self.assertEqual(len(result), 1)


class _FakeState:
    def __init__(self, position: Position):
        self.position = position
        self.trades = []
        self.logs = []

    def get_position(self, symbol, side):
        if self.position and self.position.symbol == symbol and self.position.side == side:
            return self.position
        return None

    def upsert_position(self, position):
        self.position = position

    def remove_position(self, symbol, side):
        old, self.position = self.position, None
        return old

    def record_trade(self, trade):
        self.trades.append(trade)

    def add_log(self, message, level="INFO"):
        self.logs.append((level, message))


class _PartialCloseExchange:
    def __init__(self):
        self.reduce_calls = 0
        self.open_calls = 0

    def reduce_dual(self, symbol, side, qty):
        self.reduce_calls += 1
        return {"left": 5, "fill_price": 100.0, "fee": 0.5}

    def open_dual(self, symbol, side, qty):
        self.open_calls += 1
        return {"left": 0, "fill_price": 100.0, "fee": 0.0}

    def set_leverage(self, symbol, leverage):
        return None


class LiveReversalSafetyTests(unittest.TestCase):
    def test_partial_reversal_close_never_opens_opposite_leg(self):
        position = Position(
            id="p1",
            symbol="BTC_USDT",
            side="long",
            size=10,
            entry_price=100,
            stop_price=0,
            initial_stop_price=0,
            take_profit_1=0,
            leverage=1,
            quanto_multiplier=1,
            mark_price=100,
        )
        state = _FakeState(position)
        exchange = _PartialCloseExchange()
        engine = SystematicEngine(None, exchange, state)
        engine._book.fees_paid["BTC_USDT"] = 1.0
        engine._book.funding_paid["BTC_USDT"] = 2.0

        cfg = SystematicConfig(
            target_annual_vol_pct=10,
            no_trade_buffer_pct=0,
            depth_guard_enabled=False,
        )
        target = InstrumentTarget("BTC_USDT", -10, -1000, -0.1, -0.1)
        signal = InstrumentSignal("BTC_USDT", -10, 0, -10, 0.2)
        engine._execute_target(
            "BTC_USDT",
            target,
            signal,
            price=100,
            contract_info={"quanto_multiplier": 1, "order_size_min": 1},
            equity=10_000,
            sys_cfg=cfg,
            cost_cfg=CostConfig(),
        )

        self.assertEqual(exchange.reduce_calls, 1)
        self.assertEqual(exchange.open_calls, 0)
        self.assertEqual(state.position.size, 5)
        self.assertEqual(len(state.trades), 1)
        self.assertAlmostEqual(state.trades[0].fees_paid, 1.0)
        self.assertAlmostEqual(state.trades[0].funding_paid, 1.0)
        self.assertAlmostEqual(engine._book.fees_paid["BTC_USDT"], 0.5)
        self.assertAlmostEqual(engine._book.funding_paid["BTC_USDT"], 1.0)
        self.assertAlmostEqual(state.position.fees_paid, 0.5)
        self.assertAlmostEqual(state.position.funding_paid, 1.0)


class WalkForwardBoundaryTests(unittest.TestCase):
    def test_explicit_test_start_excludes_indicator_warmup_from_folds(self):
        ts = np.arange(100, dtype=float) * 3600
        frame = pd.DataFrame(
            {"timestamp": ts, "open": 100, "high": 101, "low": 99,
             "close": 100, "volume": 1}
        )
        inp = SymbolBacktestInputs(
            "BTC_USDT", frame, frame, frame, frame,
            funding_rate=0, funding_interval_sec=28800,
            quanto_multiplier=1, taker_fee_rate=0.001,
            test_start_ts=float(ts[60]),
        )
        fake_result = SimpleNamespace(
            return_pct=0.0, annualized_return_pct=0.0, sharpe=0.0,
            max_drawdown_pct=0.0, trade_count=0,
        )
        with patch("src.walkforward.run_portfolio_backtest", return_value=fake_result):
            result = run_walk_forward(
                [inp], SystematicConfig(), CostConfig(), 10_000, n_folds=2
            )
        self.assertEqual(len(result.folds), 2)
        self.assertAlmostEqual(result.folds[0].start_ts, float(ts[60]))
        self.assertGreaterEqual(min(f.start_ts for f in result.folds), float(ts[60]))


class BacktestAccountingTests(unittest.TestCase):
    def test_reversal_keeps_position_ledger_and_all_costs(self):
        n = 30
        timestamps = np.arange(n, dtype=float) * 3600 + 1_700_000_000
        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": np.full(n, 100.0),
                "high": np.full(n, 100.0),
                "low": np.full(n, 100.0),
                "close": np.full(n, 100.0),
                "volume": np.full(n, 1000.0),
            }
        )
        funding = pd.DataFrame(
            {"timestamp": [timestamps[0], timestamps[-1]], "funding_rate": [0.0, 0.0]}
        )
        inp = SymbolBacktestInputs(
            symbol="BTC_USDT",
            df_short=frame,
            df_main=frame,
            df_regime=frame,
            df_cov=frame,
            funding_rate=0,
            funding_interval_sec=28800,
            quanto_multiplier=1,
            taker_fee_rate=0.001,
            funding_history=funding,
            test_start_ts=timestamps[0],
        )
        cfg = SystematicConfig(
            short_trend_interval="1h",
            main_trend_interval="1h",
            regime_interval="1h",
            covariance_interval="1h",
            min_bars_short=1,
            min_bars_main=1,
            min_bars_regime=1,
            regime_ema_long=1,
            regime_range_dampen=1,
            target_annual_vol_pct=10,
            no_trade_buffer_pct=0,
            exit_buffer_multiplier=1,
            max_instrument_exposure_pct=1000,
            max_correlated_group_exposure_pct=1000,
            max_leverage=1000,
        )
        forecasts = pd.Series(np.r_[np.full(15, 10.0), np.full(15, -10.0)])

        def cov_series(returns, lam, min_periods):
            idx = list(returns.index)
            # ewma_covariance_series 返回的是每根K线方差，回测内部会再年化。
            per_bar_variance = 0.04 / (365 * 24)
            return idx, [np.array([[per_bar_variance]]) for _ in idx], list(returns.columns)

        with (
            patch("src.backtest.trend_mod.group_trend_forecast", return_value=forecasts),
            patch("src.backtest.trend_mod.daily_regime_series", return_value=pd.Series(["range"] * n)),
            patch("src.backtest.carry_mod.carry_forecast_series_from_history", return_value=pd.Series(np.zeros(n))),
            patch("src.backtest.vol_mod.price_vol_annualized", return_value=pd.Series(np.full(n, 0.2))),
            patch("src.backtest.vol_mod.log_returns", return_value=pd.Series(np.zeros(n))),
            patch("src.backtest.vol_mod.ewma_covariance_series", side_effect=cov_series),
        ):
            result = run_portfolio_backtest([inp], cfg, CostConfig(slippage_bps=2), 10_000)

        self.assertTrue(any(t["side"] == "long" for t in result.trades))
        self.assertTrue(any(t["side"] == "short" for t in result.trades))
        self.assertAlmostEqual(
            result.total_fees,
            result.total_traded_notional * inp.taker_fee_rate,
            places=8,
        )
        self.assertAlmostEqual(
            result.final_equity,
            result.initial_capital + sum(t["pnl"] for t in result.trades),
            places=8,
        )
        self.assertTrue(math.isclose(result.gross_pnl_before_costs, 0.0, abs_tol=1e-8))


if __name__ == "__main__":
    unittest.main()
