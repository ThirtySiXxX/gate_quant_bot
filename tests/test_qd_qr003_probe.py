"""Synthetic-only tests of the original replay with isolated observation."""
from contextlib import ExitStack
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from research.qr003 import replay_probe as probe
from src import backtest
from src.config import CostConfig, RiskConfig, SystematicConfig
from src.execution_timing import ExecutionTiming
from src.portfolio import InstrumentSignal, InstrumentTarget, PortfolioAllocationResult


START = 1_700_000_000


def fixture(symbol="ETH_USDT"):
    times = START + np.arange(60) * 3600
    prices = 100 + np.sin(np.arange(60) / 3) * .02 + np.arange(60) * .005
    frame = pd.DataFrame(dict(timestamp=times, open=prices, high=prices + 1,
                              low=prices - 1, close=prices + .001, volume=1000.0))
    funding = pd.DataFrame(dict(timestamp=times[::8],
        funding_rate=[.0001 if i % 2 else -.00005 for i in range(len(times[::8]))]))
    sb = backtest.SymbolBacktestInputs(symbol, frame, frame, frame, frame, 0., 28800,
        .01, .0005, funding_history=funding, leverage_min=1, leverage_max=200,
        order_size_max=1_000_000_000, risk_limit_tiers=[dict(risk_limit=1e9, leverage_max=200)])
    cfg = SystematicConfig(position_sizing_mode="fixed_margin", ml_model_path="",
        short_trend_interval="1h", main_trend_interval="1h", regime_interval="1h",
        covariance_interval="1h", min_bars_short=1, min_bars_main=1, min_bars_regime=1,
        no_trade_buffer_pct=0, depth_guard_enabled=False,
        execution_timing={"enabled": True, "symbols": ["BTC_USDT", "ETH_USDT"],
                          "require_trend_agreement": True, "trail_atr": 3.})
    return sb, cfg


def signal_at(symbol, data, t, cfg):
    i = int((t - START) / 3600)
    if i == 0:
        return None
    f = 10 if 20 <= i < 25 or i >= 45 else (5 if 25 <= i < 28 else (-10 if 30 <= i < 34 else 0))
    feature = dict(bar_ts=t - 3600, bar_seconds=3600, quality=.9, extension=0.,
        close=float(data["short_close"][i - 1]), atr=2., recent_high=102., recent_low=98.,
        long_run=5, short_run=5, breakout_long=True, breakout_short=True)
    return InstrumentSignal(symbol, f, 0., f, .2, short_forecast=f, main_forecast=f, timing_feature=feature)


def allocate(signals, *args):
    return PortfolioAllocationResult(targets={s: InstrumentTarget(s, sig.combined_forecast,
        sig.combined_forecast * 100, .1, .1) for s, sig in signals.items()})


class ReplayProbeTests(unittest.TestCase):
    def run_case(self, *, observed=True, sb=None, cfg=None, skip=None, trajectory="synthetic", build_error=None):
        default_sb, default_cfg = fixture()
        sb, cfg = sb or default_sb, cfg or default_cfg
        original_decide = backtest.execution.decide_execution
        original_build = backtest.execution.build_order_plan
        original_fill = backtest.execution.record_fill
        original_timing = ExecutionTiming.decide
        with ExitStack() as stack:
            spies = {
                "signal_at": stack.enter_context(patch.object(backtest.signal_policy, "signal_at", side_effect=signal_at)),
                "decide_execution": stack.enter_context(patch.object(backtest.execution, "decide_execution", wraps=original_decide)),
                "build_order_plan": stack.enter_context(patch.object(backtest.execution, "build_order_plan",
                    side_effect=build_error, wraps=None if build_error else original_build)),
                "record_fill": stack.enter_context(patch.object(backtest.execution, "record_fill", wraps=original_fill)),
                "timing_decide": stack.enter_context(patch.object(ExecutionTiming, "decide", autospec=True, side_effect=original_timing)),
            }
            stack.enter_context(patch.object(backtest.pf, "allocate_portfolio", side_effect=allocate))
            args = ([sb], cfg, CostConfig(slippage_bps=2), 10000)
            if observed:
                run = probe.probe_replay(*args, trajectory_id=trajectory, skip_entry_at=skip,
                    risk_cfg=RiskConfig(daily_loss_limit_enabled=False))
            else:
                run = backtest.run_portfolio_backtest(*args, risk_cfg=RiskConfig(daily_loss_limit_enabled=False))
            return run, {name: spy.call_count for name, spy in spies.items()}

    def test_allow_all_with_real_signal_pipeline_and_synthetic_market_inputs(self):
        sb, cfg = fixture()
        n = 700
        times = START + np.arange(n) * 3600
        prices = 100 * np.exp(np.cumsum(np.random.default_rng(13).normal(.0001, .002, n)))
        frame = pd.DataFrame(dict(timestamp=times, open=prices, high=prices * 1.002,
                                  low=prices * .998, close=prices, volume=1000.0))
        sb = replace(sb, df_short=frame, df_main=frame, df_cov=frame, df_regime=frame,
            funding_history=pd.DataFrame(dict(timestamp=times[::8], funding_rate=.00005)))
        args = ([sb], cfg, CostConfig(slippage_bps=2), 10000)
        original_signal, original_timing = backtest.signal_policy.signal_at, ExecutionTiming.decide
        with patch.object(backtest.signal_policy, "signal_at", wraps=original_signal) as signal_spy, \
             patch.object(ExecutionTiming, "decide", autospec=True, side_effect=original_timing) as timing_spy:
            original = backtest.run_portfolio_backtest(*args)
            counts = signal_spy.call_count, timing_spy.call_count
            signal_spy.reset_mock()
            timing_spy.reset_mock()
            run = probe.probe_replay(*args, trajectory_id="actual-pipeline-synthetic-data")
            self.assertEqual(counts, (signal_spy.call_count, timing_spy.call_count))
            self.assertGreater(timing_spy.call_count, 0)
        self.assertEqual(json.dumps(original.to_dict(), sort_keys=True),
                         json.dumps(run.result.to_dict(), sort_keys=True))
        self.assertTrue(any(event["signal_available"] for event in run.events))
        json.dumps(run.events, allow_nan=False)

    def test_allow_all_preserves_exact_result_and_all_original_call_counts(self):
        for symbol in ("BTC_USDT", "ETH_USDT"):
            with self.subTest(symbol=symbol):
                sb, cfg = fixture(symbol)
                original, before = self.run_case(observed=False, sb=sb, cfg=cfg)
                run, after = self.run_case(sb=sb, cfg=cfg)
                # Native NaNs in summary diagnostics retain their exact JSON representation.
                self.assertEqual(json.dumps(original.to_dict(), sort_keys=True),
                                 json.dumps(run.result.to_dict(), sort_keys=True))
                self.assertEqual(before, after)
                self.assertGreater(after["timing_decide"], 0)
                self.assertEqual(after["timing_decide"], after["decide_execution"])
                self.assertEqual(run.call_counts, {name: after[name] for name in run.call_counts})
                self.assertEqual(len(run.events), after["signal_at"])
                self.assertFalse(run.skip_applied)
                json.dumps(run.events, allow_nan=False)

    def test_skip_is_applied_once_after_real_budget_and_next_bar_can_enter(self):
        baseline, _ = self.run_case()
        first_open = next(row for row in baseline.result.executions if row["action"] == "open")
        run, counts = self.run_case(skip=first_open["time"])
        skipped = [event for event in run.events if event["skip_applied"]]
        self.assertTrue(run.skip_applied)
        self.assertEqual(len(skipped), 1)
        event = skipped[0]
        self.assertEqual(event["post_budget_eligibility"]["status"], "eligible")
        self.assertTrue(event["order_check"]["budget_checked"])
        self.assertGreater(event["order_check"]["ticket"]["quantity"], 0)
        self.assertEqual(event["emitted_actions"], [])
        self.assertFalse(any(row["time"] == event["decision_at"] for row in run.result.executions))
        later_open = next(row for row in run.result.executions if row["action"] == "open")
        self.assertEqual(later_open["time"], first_open["time"] + 3600)
        self.assertEqual(counts["timing_decide"], counts["decide_execution"])
        self.assertEqual(baseline.events[:20], run.events[:20])

    def test_existing_full_and_partial_exits_cannot_be_filtered(self):
        baseline, _ = self.run_case()
        for action in ("close", "reduce"):
            row = next(row for row in baseline.result.executions if row["action"] == action)
            with self.subTest(action=action):
                run, _ = self.run_case(skip=row["time"])
                self.assertFalse(run.skip_applied)
                self.assertEqual(json.dumps(baseline.result.to_dict(), sort_keys=True),
                                 json.dumps(run.result.to_dict(), sort_keys=True))
                event = next(e for e in run.events if e["decision_at"] == row["time"])
                self.assertGreater(event["position_before"]["size"], 0)
                self.assertEqual(event["position_before"]["position_id"], row["position_id"])
                self.assertEqual(event["post_budget_eligibility"]["status"], "not_applicable")

    def test_rejected_available_budget_is_not_a_skipped_or_zero_pnl_label(self):
        baseline, _ = self.run_case()
        first_time = next(row["time"] for row in baseline.result.executions if row["action"] == "open")
        sb, _ = fixture()
        sb = replace(sb, taker_fee_rate=.1)  # Genuine fee reserve exceeds the actual account budget.
        run, _ = self.run_case(sb=sb, skip=first_time)
        event = next(e for e in run.events if e["decision_at"] == first_time)
        self.assertTrue(event["pre_ml_entry_proposal"])
        self.assertEqual(event["post_budget_eligibility"]["status"], "rejected")
        self.assertIn("可用保证金不足", event["order_check"]["error"]["message"])
        self.assertFalse(run.skip_applied)
        self.assertEqual(run.result.executions, [])
        self.assertNotIn("pnl", event)
        self.assertNotIn("label", event)

    def test_no_order_observation_is_distinct_from_order_rejection(self):
        run, _ = self.run_case(skip=START)
        missing_signal = run.events[0]
        self.assertFalse(missing_signal["signal_available"])
        self.assertIsNone(missing_signal["pre_ml_entry_proposal"])
        self.assertIsNone(missing_signal["order_check"])
        self.assertEqual(missing_signal["post_budget_eligibility"]["status"], "not_evaluated")
        no_order = next(e for e in run.events if e["plan"] and not e["plan"]["rebalance"])
        self.assertIsNone(no_order["order_check"])
        self.assertFalse(no_order["pre_ml_entry_proposal"])
        self.assertEqual(no_order["post_budget_eligibility"]["status"], "not_evaluated")
        self.assertFalse(run.skip_applied)

    def test_current_close_future_prices_and_funding_do_not_enter_earlier_events(self):
        sb, cfg = fixture()
        baseline, _ = self.run_case(sb=sb, cfg=cfg)
        frame, funding = sb.df_short.copy(), sb.funding_history.copy()
        cutoff = START + 32 * 3600
        frame.loc[frame.timestamp >= cutoff, ["close", "high", "low"]] *= 2
        frame.loc[frame.timestamp > cutoff, "open"] *= 2
        funding.loc[funding.timestamp > cutoff, "funding_rate"] = .5
        changed = replace(sb, df_short=frame, df_main=frame, df_cov=frame,
                          df_regime=frame, funding_history=funding)
        run, _ = self.run_case(sb=changed, cfg=cfg)
        prefix = lambda events: [e for e in events if e["decision_at"] <= cutoff]
        self.assertEqual(prefix(baseline.events), prefix(run.events))
        event = next(e for e in run.events if e["decision_at"] == cutoff)
        self.assertEqual(event["signal"]["timing_feature"]["bar_ts"] + 3600, cutoff)
        self.assertEqual(event["decision_price"], sb.df_short.loc[sb.df_short.timestamp == cutoff, "open"].iloc[0])
        self.assertNotIn("final_equity", event)

    def test_state_identity_links_same_origin_across_different_trajectories(self):
        a, _ = self.run_case(trajectory="allow")
        b, _ = self.run_case(trajectory="another-name")
        self.assertEqual([e["state_id"] for e in a.events], [e["state_id"] for e in b.events])
        self.assertNotEqual(a.events[0]["event_id"], b.events[0]["event_id"])

    def test_exception_is_not_retried_or_wrapped_and_globals_are_unchanged(self):
        original_globals = dict(backtest.run_portfolio_backtest.__globals__)
        error = RuntimeError("synthetic order failure")
        with patch.object(backtest.execution, "build_order_plan", side_effect=error) as failing:
            with self.assertRaises(RuntimeError) as raised:
                self.run_case()
            self.assertEqual(failing.call_count, 1)
        self.assertIs(raised.exception, error)
        self.assertEqual(backtest.run_portfolio_backtest.__globals__, original_globals)
        # A normal subsequent invocation is unaffected by the failed probe.
        run, _ = self.run_case()
        self.assertTrue(run.result.executions)

    def test_nested_probe_uses_independent_observers_without_global_restoration(self):
        sb, cfg = fixture()
        args = ([sb], cfg, CostConfig(slippage_bps=2), 10000)
        nested = []

        def progress(*args):
            if not nested:
                nested.append(probe.probe_replay([sb], cfg, CostConfig(slippage_bps=2),
                    10000, trajectory_id="nested"))

        with patch.object(backtest.signal_policy, "signal_at", side_effect=signal_at), \
             patch.object(backtest.pf, "allocate_portfolio", side_effect=allocate):
            original_globals = dict(backtest.run_portfolio_backtest.__globals__)
            outer = probe.probe_replay(*args, trajectory_id="outer", progress_cb=progress)
            self.assertEqual(original_globals, backtest.run_portfolio_backtest.__globals__)
            raw = backtest.run_portfolio_backtest(*args)
        for run in (outer, nested[0]):
            self.assertEqual(json.dumps(raw.to_dict(), sort_keys=True),
                             json.dumps(run.result.to_dict(), sort_keys=True))
        self.assertTrue(all(e["trajectory_id"] == "outer" for e in outer.events))
        self.assertTrue(all(e["trajectory_id"] == "nested" for e in nested[0].events))

    def test_original_entry_gate_flags_do_not_turn_into_a_research_skip(self):
        with patch.object(backtest, "daily_risk_state", return_value=(10000, START, True)):
            run, _ = self.run_case(skip=START + 20 * 3600)
        event = next(e for e in run.events if e["decision_at"] == START + 20 * 3600)
        self.assertFalse(event["decision_inputs"]["allow_increase"])
        self.assertFalse(event["plan"]["allow_increase"])
        self.assertFalse(event["pre_ml_entry_proposal"])
        self.assertEqual(event["post_budget_eligibility"]["status"], "rejected")
        self.assertFalse(run.skip_applied)
        self.assertEqual(run.result.executions, [])

    def test_scope_and_source_drift_fail_closed_before_replay(self):
        sb, cfg = fixture()
        for inputs, settings, skip in (([sb, sb], cfg, None), ([replace(sb, symbol="SOL_USDT")], cfg, None),
                ([sb], replace(cfg, ml_model_path="unapproved"), None),
                ([sb], replace(cfg, position_sizing_mode="volatility"), None), ([sb], cfg, True)):
            with self.subTest(skip=skip), self.assertRaises(probe.ProbeBoundaryError):
                probe.probe_replay(inputs, settings, CostConfig(), 10000, trajectory_id="scope", skip_entry_at=skip)
        with patch.dict(probe.EXPECTED_SOURCE_SHA256, {"src/backtest.py": "0" * 64}), \
             self.assertRaisesRegex(probe.ProbeBoundaryError, "source drift"):
            probe.probe_replay([sb], cfg, CostConfig(), 10000, trajectory_id="drift")


if __name__ == "__main__":
    unittest.main()
