"""Offline native-contract guards for docs/INTERFACES.md registry 1.0.0.

No application launch, credentials, exchange I/O, or runtime schema migration.
Counterpart review is required before changing these expectations.
"""
from dataclasses import asdict, fields
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import numpy as np
import pandas as pd
import yaml

from src.backtest import PortfolioBacktestResult, SymbolBacktestInputs
from src.backtest_runner import BacktestJob
from src.config import RiskConfig, SystematicConfig
from src.crypto_ml import (FEATURE_NAMES, FEATURE_VERSION, causal_features,
                           load_bundle, prepare_predictions, supervised_samples)
from src.data_fetcher import _fetch_page, drop_unclosed_last_bar
from src.json_utils import json_safe
from src.portfolio import InstrumentSignal, InstrumentTarget
from src.risk import daily_risk_state
from src.strategy_execution import plan_orders


def hourly_bars():
    times = np.arange(220, dtype=float) * 3600
    close = 100 + np.arange(220) * .1 + np.sin(np.arange(220))
    return pd.DataFrame(dict(timestamp=times, open=close, high=close + 1,
                             low=close - 1, close=close, volume=np.arange(220) + 10.))


def model_bundle():
    return dict(feature_version=1, feature_names=list(FEATURE_NAMES), classes=[-1, 0, 1],
                models=[dict(kind='logistic', trained_until=170 * 3600,
                             valid_from=180 * 3600, valid_until=200 * 3600,
                             mean=[0.] * 21, scale=[1.] * 21,
                             coef=np.zeros((3, 21)).tolist(),
                             intercept=np.log([.2, .3, .5]).tolist())])


class InterfaceContractTests(unittest.TestCase):
    def test_market_data_open_time_and_closed_bar_boundary(self):
        candle = SimpleNamespace(t='3600', o='100', h='102', l='99', c='101', v='10', sum=None)
        exchange = SimpleNamespace(settle='usdt', api=SimpleNamespace(
            list_futures_candlesticks=lambda *args, **kwargs: [candle]))
        frame = _fetch_page(exchange, 'ETH_USDT', '1h', 1)
        self.assertEqual(frame.columns.tolist(), ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.assertEqual(frame.timestamp.iloc[0], 3600.)
        self.assertTrue(drop_unclosed_last_bar(frame, '1h', now=7199).empty)
        self.assertEqual(len(drop_unclosed_last_bar(frame, '1h', now=7200)), 1)

    def test_feature_order_version_and_availability(self):
        expected = ([f'return_{h}h' for h in (1, 4, 12, 24, 72, 168)]
                    + [f'volatility_{h}h' for h in (6, 24, 72)]
                    + [f'volume_relative_{h}h' for h in (6, 24, 168)]
                    + ['range_pct', 'body_pct', 'upper_wick_pct', 'lower_wick_pct',
                       'efficiency_24h', 'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos'])
        self.assertEqual(FEATURE_VERSION, 1)
        self.assertEqual(list(FEATURE_NAMES), expected)
        bars = hourly_bars()
        features = causal_features(bars)
        self.assertEqual(features.columns.tolist(), expected)
        self.assertTrue(features.iloc[:168].isna().any(axis=1).all())
        samples = supervised_samples(bars, 'ETH_USDT')
        self.assertFalse(samples.empty)
        self.assertEqual(samples.iloc[0].feature_time, bars.timestamp.iloc[168] + 3600)
        self.assertTrue((samples.label_end - samples.feature_time == 4 * 3600).all())
        self.assertEqual(set(samples.symbol), {'ETH_USDT'})

    def test_prediction_probabilities_and_half_open_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'model.json'
            path.write_text(json.dumps(model_bundle()))
            predictions = prepare_predictions(hourly_bars(), path)
        # Bar i is available at (i+1)*3600, not its opening timestamp.
        self.assertNotEqual(predictions[178]['status'], 'ok')
        first = predictions[179]
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['feature_time'], 180 * 3600)
        np.testing.assert_allclose([first[k] for k in ('short', 'neutral', 'long')], [.2, .3, .5])
        self.assertEqual(first['valid_until'], 200 * 3600)
        self.assertEqual(predictions[198]['status'], 'ok')
        self.assertNotEqual(predictions[199]['status'], 'ok')

    def test_signal_and_target_signed_units(self):
        signal = InstrumentSignal('ETH_USDT', -10, 0, -10, .6)
        self.assertTrue({'symbol', 'combined_forecast', 'vol_annual', 'ml_entry',
                         'timing_feature'} <= asdict(signal).keys())
        target = InstrumentTarget(signal.symbol, -10, -1000, -.1, -.1)
        self.assertEqual(target.target_notional / 10000, target.target_weight)
        # 1000 USDT / (100 USDT/base * .1 base/contract) = 100 contracts.
        self.assertEqual(plan_orders(None, 0, target.target_notional, 100, .1, 1),
                         [('open', 'short', 100)])

    def test_model_metadata_rejects_future_training_and_wrong_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'model.json'
            good = model_bundle()
            path.write_text(json.dumps(good))
            self.assertEqual(load_bundle(path)['classes'], [-1, 0, 1])
            for bad in (dict(good, feature_version=2),
                        dict(good, feature_names=list(reversed(FEATURE_NAMES))),
                        dict(good, models=[dict(good['models'][0], trained_until=180 * 3600)])):
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    load_bundle(path)

    def test_configuration_defaults_and_ml_interval_guard(self):
        template = Path(__file__).resolve().parents[1] / 'config.example.yaml'
        config = yaml.safe_load(template.read_text())
        self.assertEqual(config['mode'], 'paper')
        cfg = SystematicConfig.build({})
        self.assertEqual(cfg.position_sizing_mode, 'fixed_margin')
        self.assertEqual(cfg.ml_model_path, '')
        self.assertEqual(cfg.ml_min_entry_probability, .45)
        with self.assertRaises(ValueError):
            SystematicConfig.build({'ml_model_path': 'fixture.json', 'short_trend_interval': '15m'})

    def test_backtest_schema_request_and_strict_json_result(self):
        required = {f.name for f in fields(SymbolBacktestInputs) if f.init}
        self.assertTrue({'symbol', 'df_short', 'df_main', 'df_regime', 'df_cov',
                         'funding_rate', 'funding_interval_sec', 'quanto_multiplier',
                         'test_start_ts'} <= required)
        result = PortfolioBacktestResult(symbols=['ETH_USDT'], initial_capital=10000,
                                        final_equity=11000, return_pct=10,
                                        equity_curve=[dict(t=3600., e=11000.)]).to_dict()
        self.assertEqual(result['schema_version'], 3)
        self.assertEqual(result['return_pct'], 10)
        self.assertEqual(result['equity_curve'][0], dict(t=3600., e=11000.))
        job = BacktestJob('fixture', ['ETH_USDT'], 30, 10000, status='done', result=result)
        self.assertNotIn('equity_curve', job.to_summary()['summary'])
        self.assertEqual(job.to_full()['equity_curve'], result['equity_curve'])
        self.assertIsNone(json.loads(json.dumps(json_safe({'unavailable': float('nan')}),
                                               allow_nan=False))['unavailable'])

    def test_risk_limit_units_defaults_and_window(self):
        cfg = RiskConfig.build({})
        self.assertFalse(cfg.daily_loss_limit_enabled)
        self.assertFalse(daily_risk_state(9000, 10000, 0, True, 100, cfg)[2])
        cfg.daily_loss_limit_enabled = True
        cfg.daily_loss_limit_pct = 5  # Percentage points, not a .05 fraction.
        self.assertFalse(daily_risk_state(9600, 10000, 0, False, 100, cfg)[2])
        self.assertTrue(daily_risk_state(9400, 10000, 0, False, 100, cfg)[2])
        self.assertTrue(daily_risk_state(9900, 10000, 0, True, 86399, cfg)[2])
        self.assertEqual(daily_risk_state(9900, 10000, 0, True, 86400, cfg),
                         (9900, 86400, False))
