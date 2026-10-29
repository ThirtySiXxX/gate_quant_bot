import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.config import ConfigStore, CostConfig, SystematicConfig
from src.performance import compounded_performance
from src.universe import (UniverseService, observation, rank_candidates, closed_prices,
                          tradable_contract, is_crypto)

ASOF = 1793001600.

def contract(symbol='BTC_USDT', **kw):
    return dict(name=symbol, status='trading', type='direct', contract_type='',
                in_delisting=False, is_pre_market=False, funding_interval=28800,
                taker_fee_rate=.0005, **kw)

def ticker(symbol='BTC_USDT'):
    return dict(contract=symbol, highest_bid=100, lowest_ask=100.01,
                volume_24h_quote=2e7, funding_rate=.0001)

def candles(seconds, seed=1, n=600):
    end=int(ASOF//seconds)*seconds
    rng=np.random.default_rng(seed)
    return pd.DataFrame({'timestamp':np.arange(end-n*seconds,end,seconds),
                         'close':100*np.exp(np.cumsum(.001+rng.normal(0,.002,n)))})

class Market:
    def __init__(self):
        self.items=[contract()];self.calls=0
    def contracts(self):self.calls+=1;return self.items
    def tickers(self):return [ticker(x['name']) for x in self.items]
    def candles(self,symbol,interval,limit):return candles(3600 if interval=='1h' else 14400)

class UniverseTests(unittest.TestCase):
    def test_catalogue_has_no_named_crypto_allowlist(self):
        c=contract('NEWTOKEN42_USDT');self.assertTrue(tradable_contract(c));self.assertTrue(is_crypto(c))
        for key,value in [('status','prelaunch'),('in_delisting',True),('is_pre_market',True),('type','inverse'),('name','../BTC_USDT')]:
            self.assertFalse(tradable_contract(dict(c,**{key:value})))
        self.assertFalse(is_crypto(dict(c,contract_type='stocks')))
        del c['contract_type'];self.assertFalse(is_crypto(c))

    def test_closed_bars_are_causal_and_fail_on_gaps_or_staleness(self):
        f=candles(3600);expected=closed_prices(f,3600,ASOF,300)
        future=pd.DataFrame({'timestamp':[ASOF,ASOF+3600],'close':[1e9,np.nan]})
        pd.testing.assert_series_equal(expected,closed_prices(pd.concat([f,future]),3600,ASOF,300))
        for broken in [f.iloc[:-1],f.drop(index=200),pd.concat([f,f.iloc[-1:]])]:
            with self.assertRaises(ValueError):closed_prices(broken,3600,ASOF,300)

    def test_factors_ignore_unclosed_prices(self):
        frames=[candles(3600),candles(14400)];args=(contract(),ticker(),ASOF,SystematicConfig(),CostConfig())
        a=observation('BTC_USDT',frames,*args)
        future=[pd.concat([f,pd.DataFrame({'timestamp':[ASOF],'close':[1e12]})]) for f in frames]
        b=observation('BTC_USDT',future,*args)
        for k in ['trend','quality','cost','side']:self.assertEqual(a[k],b[k])
        self.assertGreater(a['round_trip_cost_bps'],10)

    def test_double_cost_worsens_cost_factor_not_trend(self):
        frames=[candles(3600),candles(14400)];a=observation('BTC_USDT',frames,contract(),ticker(),ASOF,SystematicConfig(),CostConfig())
        cc=CostConfig();cc.taker_fee_rate*=2;cc.slippage_bps*=2
        b=observation('BTC_USDT',frames,contract(),ticker(),ASOF,SystematicConfig(),cc)
        self.assertLess(b['cost'],a['cost']);self.assertEqual(b['trend'],a['trend'])

    def test_ranking_ties_are_deterministic_and_duplicates_diversified(self):
        rng=np.random.default_rng(42);base=pd.Series(rng.normal(size=168),index=range(168))
        rows=[dict(symbol=s,trend=1.,quality=.5,cost=-.1,returns=base.copy()) for s in ['B_USDT','A_USDT']]
        selected,rejected=rank_candidates(rows)
        self.assertEqual([x['symbol'] for x in selected],['A_USDT']);self.assertEqual(selected[0]['score'],0.)
        self.assertEqual(len(rejected),1)
        rows=[dict(symbol=f'C{i}_USDT',trend=i,quality=i,cost=i,returns=pd.Series(rng.normal(size=168))) for i in range(8)]
        selected,_=rank_candidates(rows);self.assertEqual(len(selected),5)
        self.assertEqual(selected[0]['symbol'],'C7_USDT');self.assertTrue(all('returns' not in x for x in selected))

    def test_scan_filters_asset_class_and_missing_liquidity_and_saves_evidence(self):
        market=Market();market.items+=[dict(contract('AAPL_USDT'),contract_type='stocks'),contract('ZZZ_USDT')]
        original=market.tickers;market.tickers=lambda:[dict(t,volume_24h_quote='bad') if t['contract']=='ZZZ_USDT' else t for t in original()]
        with tempfile.TemporaryDirectory() as d:
            service=UniverseService(market,lambda:ASOF,d);r=service.scan()
            self.assertEqual(r['crypto_count'],2);self.assertEqual(r['liquidity_count'],1)
            self.assertEqual([x['symbol'] for x in r['candidates']],['BTC_USDT'])
            saved=json.loads(next(Path(d).glob('*.json')).read_text());self.assertEqual(len(saved['catalogue']),3)
            self.assertFalse(r['method']['return_fit'])

    def test_stale_or_wrong_scan_cannot_be_applied_and_live_catalogue_revalidated(self):
        now=[ASOF];m=Market();u=UniverseService(m,lambda:now[0]);u._result=u.scan()
        scan=u._result['scan_id'];self.assertEqual(u.selection(scan),['BTC_USDT'])
        with self.assertRaises(ValueError):u.selection('wrong')
        with self.assertRaises(ValueError):u.selection(scan,SystematicConfig.build({'trend_weight':.6}),CostConfig())
        now[0]+=901
        with self.assertRaises(ValueError):u.selection(scan)
        now[0]=ASOF+301;m.items[0]['in_delisting']=True
        with self.assertRaises(ValueError):u.selection(scan)

    def test_concurrent_refresh_uses_single_flight_and_error_clears_candidates(self):
        u=UniverseService(Market(),lambda:ASOF);started=threading.Event();release=threading.Event();calls=[]
        def fail(*args):calls.append(1);started.set();release.wait(2);raise ValueError('offline')
        u.scan=fail;u.start();self.assertTrue(started.wait(1));u.start(force=True)
        self.assertEqual(len(calls),1);release.set()
        for _ in range(100):
            if u.status()['status']=='error':break
            time.sleep(.005)
        self.assertEqual(u.status()['candidates'],[]);self.assertTrue(u.status()['stale'])

    def test_incompatible_or_invalid_config_fails_closed(self):
        u=UniverseService(Market(),lambda:ASOF)
        for patch_cfg in [{'short_trend_interval':'15m'},{'invert_direction':True},{'max_entry_spread_bps':float('nan')}]:
            with self.assertRaises(ValueError):u.scan(SystematicConfig.build(patch_cfg))
        with self.assertRaises(ValueError):u.scan(costs=CostConfig.build({'slippage_bps':-1}))

    def test_web_read_only_scan_and_explicit_append_without_credentials_or_engine_start(self):
        from src.dashboard_web import create_app
        u=UniverseService(Market(),lambda:ASOF);u._result=u.scan()
        creds=SimpleNamespace(load=lambda: (_ for _ in ()).throw(AssertionError('credentials accessed')))
        controller=SimpleNamespace(is_running=lambda:False)
        state=SimpleNamespace(add_log=lambda *a:None)
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'config.yaml';f.write_text('symbols: [ETH_USDT]\nmode: paper\n')
            config=ConfigStore(str(f));app=create_app(state,config,creds,controller,SimpleNamespace(),u);client=app.test_client()
            self.assertEqual(client.get('/api/universe').status_code,200)
            self.assertEqual(client.get('/api/universe/catalogue').status_code,200)
            self.assertEqual(config.snapshot()['symbols'],['ETH_USDT'])
            self.assertEqual(client.post('/api/universe/apply',json={'scan_id':'wrong'}).status_code,400)
            self.assertEqual(client.post('/api/universe/apply',json={'scan_id':u._result['scan_id']}).status_code,200)
            self.assertEqual(config.snapshot()['symbols'],['ETH_USDT','BTC_USDT'])
            controller.is_running=lambda:True
            self.assertEqual(client.post('/api/universe/apply',json={'scan_id':u._result['scan_id']}).status_code,409)
            self.assertEqual(client.post('/api/symbols',json={'symbol':'NOTREAL_USDT'}).status_code,400)
            html=client.get('/').get_data(as_text=True)
            self.assertIn('UniverseUI.init(',html);self.assertNotIn('onclick="saveInvertDirection()',html)
            self.assertNotIn('id="sys-regime-fields"',html)

class CompoundTests(unittest.TestCase):
    def test_up_ten_then_down_ten_is_minus_one(self):
        p=compounded_performance(100,[{'t':1706659200,'e':110},{'t':1709251200,'e':99}])
        self.assertAlmostEqual(p['compounded_return_pct'],-1)
        self.assertAlmostEqual(np.prod([1+x['return_pct']/100 for x in p['calendar_months']])-.99,0.)
        self.assertAlmostEqual(p['equivalent_30d_return_pct'],-1)
    def test_months_link_from_initial_equity_and_loss_is_not_hidden(self):
        p=compounded_performance(100,[{'t':1704067200,'e':90},{'t':1706745600,'e':99}])
        self.assertAlmostEqual(p['calendar_months'][0]['return_pct'],-10)
        self.assertAlmostEqual(p['calendar_months'][1]['return_pct'],10)
        self.assertAlmostEqual(p['compounded_return_pct'],-1)
    def test_legacy_report_derives_compound_from_equity_without_rewriting_result(self):
        from src.backtest_runner import BacktestJob
        r={'initial_capital':100,'trades':[], 'equity_curve':[{'t':0,'e':110},{'t':30*86400,'e':99}]}
        original=copy.deepcopy(r)
        summary=BacktestJob('x',['BTC_USDT'],30,100,result=r).to_summary()
        self.assertAlmostEqual(summary['summary']['performance']['compounded_return_pct'],-1)
        self.assertAlmostEqual(summary['summary']['return_pct'],-1)
        self.assertEqual(summary['summary']['annualized_return_pct'],summary['summary']['performance']['cagr_pct'])
        self.assertEqual(r,original)

    def test_invalid_or_insolvent_equity_is_not_annualized(self):
        for start in [0,float('nan')]:
            with self.assertRaises(ValueError):compounded_performance(start,[])
        p=compounded_performance(100,[{'t':0,'e':100},{'t':86400,'e':-10}])
        self.assertAlmostEqual(p['compounded_return_pct'],-110);self.assertIsNone(p['cagr_pct'])
        self.assertFalse(p['geometric_valid'])
        self.assertIsNone(compounded_performance(100,[])['cagr_pct'])

if __name__=='__main__':unittest.main()
