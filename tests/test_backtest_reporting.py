import unittest
from src.backtest_reporting import position_summary, legacy_events, chart_payload
from src.backtest_runner import BacktestJob
from src.backtest import _performance_stats
from src.dashboard_web import create_app

class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.trades=[dict(symbol='ETH_USDT',side='long',open_time=3600.,close_time=7200.,pnl=-2.,reason='组合再平衡(减仓)',exit_price=102.),dict(symbol='ETH_USDT',side='long',open_time=3600.,close_time=10800.,pnl=5.,reason='平仓',exit_price=104.)]
    def test_reduction_does_not_create_second_position_or_loss(self):
        s=position_summary(self.trades)
        self.assertEqual(s['position_count'],1);self.assertEqual(s['closed_leg_count'],2)
        self.assertEqual(s['win_rate_pct'],100);self.assertEqual(s['max_loss_streak'],0)
    def test_legacy_first_price_and_adds_not_invented(self):
        events=legacy_events(self.trades)
        self.assertEqual([e['action'] for e in events],['open','reduce','close'])
        self.assertIsNone(events[0]['price']);self.assertTrue(all(e['estimated'] for e in events))
    def test_resample_and_exact_bar_assignment(self):
        result=dict(schema_version=2,short_interval='1h',trades=self.trades,chart_candles={'ETH_USDT':[dict(t=i*3600,o=100+i,h=102+i,l=99+i,c=101+i) for i in range(8)]},executions=[dict(id=0,symbol='ETH_USDT',action='open',time=3600,bar_time=3600),dict(id=1,symbol='ETH_USDT',action='close',time=28800,bar_time=25200)])
        view=chart_payload(result,'ETH_USDT','4h')
        self.assertEqual(len(view['candles']),2);self.assertEqual(view['candles'][0],dict(t=0,o=100,h=105,l=99,c=104))
        self.assertEqual([e['chart_time'] for e in view['events']],[0,14400])
    def test_missing_candle_never_maps_to_distant_bar(self):
        result=dict(trades=self.trades)
        view=chart_payload(result,'ETH_USDT','1h',[dict(t=0,o=100,h=100,l=100,c=100)])
        self.assertEqual(view['unmapped_events'],3)
    def test_listing_omits_heavy_arrays_but_detail_keeps_fills(self):
        job=BacktestJob('x',['ETH_USDT'],5,10000,result=dict(trades=self.trades,equity_curve=[],schema_version=2,executions=[{'action':'open'}],chart_candles={'ETH_USDT':[]}))
        summary=job.to_summary()['summary']
        self.assertNotIn('chart_candles',summary);self.assertNotIn('executions',summary)
        self.assertEqual(job.to_full()['executions'],[{'action':'open'}])
    def test_legacy_wrong_average_is_not_displayed(self):
        job=BacktestJob('x',['ETH_USDT'],5,10000,result=dict(trades=self.trades,avg_trade_notional=999.))
        self.assertIsNone(job.to_summary()['summary']['avg_trade_notional'])
    def test_initial_loss_included_in_drawdown_and_cagr(self):
        stats=_performance_stats([dict(t=0,e=90),dict(t=365*86400,e=90)],100.)
        self.assertAlmostEqual(stats['max_drawdown_pct'],10.)
        self.assertAlmostEqual(stats['annualized_return_pct'],-10.)
    def test_loss_streak_is_per_symbol_not_interleaved(self):
        rows=[dict(symbol=s,side='long',open_time=t,close_time=t+1,pnl=p) for s,t,p in [('A',1,-1),('B',2,1),('A',3,-1),('A',4,-1)]]
        self.assertEqual(position_summary(rows)['max_loss_streak'],3)
    def test_chart_endpoint_uses_snapshot_without_credentials_or_network(self):
        job=BacktestJob('x',['ETH_USDT'],5,10000,result=dict(schema_version=2,trades=self.trades,executions=[],short_interval='1h',chart_candles={'ETH_USDT':[dict(t=0,o=1,h=2,l=1,c=2)]}))
        class Controller:
            def get_job(self,key):return job if key=='x' else None
        client=create_app(None,None,None,None,Controller()).test_client()
        r=client.get('/api/backtest/job/x/chart?symbol=ETH_USDT&interval=1h')
        self.assertEqual(r.status_code,200);self.assertTrue(r.json['ok'])
        self.assertEqual(client.get('/api/backtest/job/x/chart?symbol=BTC_USDT').status_code,400)
        self.assertEqual(client.get('/api/backtest/job/missing/chart?symbol=ETH_USDT').status_code,404)
        self.assertEqual(client.get('/api/backtest/job/x/chart?symbol=ETH_USDT&interval=15m').status_code,400)
