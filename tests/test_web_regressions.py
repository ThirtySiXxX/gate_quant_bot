import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from src.backtest import PortfolioBacktestResult
from src.backtest_runner import BacktestController, BacktestJob
from src.dashboard_web import create_app
from src.json_utils import json_safe
from src.walkforward import diagnose_trend_capture


def strict_loads(text):
    def reject(value):
        raise ValueError('Invalid JSON numeric token: ' + value)
    return json.loads(text, parse_constant=reject)


class WebRegressionTests(unittest.TestCase):
    def test_single_symbol_backtest_accepts_search_codes_outside_trading_pool(self):
        started = []
        def start(symbols, days, capital, **kwargs):
            started.append(symbols)
            return SimpleNamespace(id='single', symbols=symbols, days_back=days, walkforward=False)
        controller = SimpleNamespace(start_job=start)
        state = SimpleNamespace(add_log=Mock())
        cfg = SimpleNamespace(snapshot=lambda: {'symbols': ['ETH_USDT']})
        client = create_app(state, cfg, None, None, controller).test_client()
        for raw, canonical in [('btc', 'BTC_USDT'), (' SOL/USDT ', 'SOL_USDT'),
                               ('DOGE-USDT', 'DOGE_USDT'), ('zecusdt', 'ZEC_USDT'),
                               ('NEWTOKEN42', 'NEWTOKEN42_USDT'), ('1000PEPE_USDT', '1000PEPE_USDT')]:
            with self.subTest(raw=raw):
                response = client.post('/api/backtest/start', json={'symbols': [raw], 'days_back': 30})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json['ok'])
                self.assertEqual(started[-1], [canonical])
        self.assertTrue(client.post('/api/backtest/start', json={'symbol': 'btc'}).json['ok'])
        self.assertEqual(started[-1], ['BTC_USDT'])

    def test_web_backtest_rejects_empty_multiple_and_invalid_symbols_before_job_creation(self):
        start = Mock(side_effect=AssertionError('invalid selection must not create a job'))
        client = create_app(None, None, None, None, SimpleNamespace(start_job=start)).test_client()
        for payload in [None, [], {}, {'symbols': []}, {'symbols': ['BTC_USDT', 'ETH_USDT']},
                        {'symbols': ['BTC_USDT', 'BTC_USDT']}, {'symbols': 'BTC_USDT'},
                        {'symbols': [None]}, {'symbols': [123]}, {'symbol': ''},
                        {'symbol': 'BTC,ETH'}, {'symbol': '../ETH'}, {'symbol': 'BTC ETH'},
                        {'symbol': '币种'}, {'symbol': 'A' * 61}]:
            with self.subTest(payload=payload):
                response = client.post('/api/backtest/start', json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json['ok'])
        start.assert_not_called()

    def test_nonfinite_old_result_does_not_break_list_detail_or_chart(self):
        raw = dict(schema_version=3, short_interval='1h', trades=[], executions=[],
                   chart_candles={'ETH_USDT': [dict(t=3600, o=1., h=2., l=1., c=2.)]},
                   trend_diagnosis=dict(median_capture_pct=float('nan'),
                                        episodes=[dict(entry_lag_pct=float('nan'))]),
                   sharpe=float('inf'), sortino=-float('inf'))
        job = BacktestJob('legacy-nan', ['ETH_USDT'], 30, 1000, status='done', result=raw)
        controller = SimpleNamespace(get_job=lambda _: job, list_jobs=lambda: [job.to_summary()])
        client = create_app(None, None, None, None, controller).test_client()
        for path in ['/api/backtest/list', '/api/backtest/job/legacy-nan',
                     '/api/backtest/job/legacy-nan/chart?symbol=ETH_USDT&interval=1h']:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            strict_loads(response.get_data(as_text=True))
        full = strict_loads(client.get('/api/backtest/job/legacy-nan').text)
        self.assertIsNone(full['trend_diagnosis']['episodes'][0]['entry_lag_pct'])
        self.assertIsNone(full['summary']['sharpe'])
        self.assertTrue(math.isnan(raw['trend_diagnosis']['median_capture_pct']))

    def test_diagnosis_missing_participation_uses_null(self):
        prices = pd.DataFrame({'timestamp': [0, 3600, 7200, 10800], 'close': [100., 120., 100., 125.]})
        result = PortfolioBacktestResult(equity_curve=[dict(t=0, e=100.), dict(t=10800, e=100.)])
        diagnosis = diagnose_trend_capture(result, {'ETH_USDT': prices}, min_move_pct=8)
        self.assertGreater(diagnosis['episode_count'], 0)
        self.assertEqual(diagnosis['participated_count'], 0)
        self.assertIsNone(diagnosis['median_entry_lag_pct'])
        self.assertTrue(all(row['entry_lag_pct'] is None for row in diagnosis['episodes']))
        json.dumps(diagnosis, allow_nan=False)

    def test_persistence_is_strict_and_old_record_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = BacktestController(None, None, tmp, tmp)
            job = BacktestJob('a', ['ETH_USDT'], 30, 1000, status='done',
                              result={'trades': [], 'value': float('nan')})
            controller._persist(job)
            self.assertIsNone(strict_loads((Path(tmp)/'a.json').read_text())['result']['value'])
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])
            data = json.loads((Path(tmp)/'a.json').read_text())
            data['result']['value'] = float('inf')
            (Path(tmp)/'a.json').write_text(json.dumps(data))
            loaded = BacktestController(None, None, tmp, tmp)
            self.assertIsNone(loaded.list_jobs()[0]['summary']['value'])

    def test_invalid_numbers_rejected_before_credentials_or_thread(self):
        cfg = SimpleNamespace(snapshot=lambda: {'symbols': ['ETH_USDT']})
        class NoCredentials:
            def load(self):
                raise AssertionError('invalid inputs must not reach credentials')
        with tempfile.TemporaryDirectory() as tmp:
            controller = BacktestController(cfg, NoCredentials(), tmp, tmp)
            for days, capital in [(float('nan'), 1000), (float('inf'), 1000), (-1, 1000),
                                  (30, float('inf')), (30, -1), (30, 'bad')]:
                with self.assertRaises(ValueError):
                    controller.start_job(['ETH_USDT'], days, capital)
            self.assertEqual(controller.list_jobs(), [])

    def test_all_json_routes_encode_unavailable_metric_as_null(self):
        app = create_app(None, None, None, None, None)
        with app.app_context():
            response = app.json.response({'profit_factor': float('inf'), 'nested': [float('nan')]})
            self.assertEqual(strict_loads(response.get_data(as_text=True)), {'profit_factor': None, 'nested': [None]})
        self.assertEqual(json_safe({'x': (1, True, 2.5)}), {'x': [1, True, 2.5]})
