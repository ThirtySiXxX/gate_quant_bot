"""Causal model, restart and actual order-boundary regression tests (offline)."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from src.execution_timing import ExecutionTiming, TimingConfig, timing_features
from src.state import StateStore
from src.config import CostConfig, SystematicConfig
from src.portfolio import InstrumentSignal, InstrumentTarget
from src.systematic_engine import SystematicEngine
from src.models import Position

def feature(t=3600):
    return dict(bar_ts=t,bar_seconds=3600,close=100.,atr=1.,quality=.8,extension=0.,long_run=3,short_run=3,breakout_long=True,breakout_short=True,recent_high=101.,recent_low=99.)

class TimingTests(unittest.TestCase):
    def test_prefix_causality(self):
        c=100+np.cumsum(np.random.default_rng(19).normal(0,.3,400))
        df=pd.DataFrame(dict(timestamp=np.arange(400)*3600,close=c,high=c+.5,low=c-.5))
        pd.testing.assert_frame_equal(timing_features(df.iloc[:280]),timing_features(df).iloc[:280])

    def test_weak_exit_counts_bars_not_ticks_and_resets_on_gap(self):
        p=ExecutionTiming();cfg=TimingConfig();f=feature();f['quality']=.1
        def decide():return p.decide('ETH',100,100,1,1,1,f,cfg)
        for _ in range(5):self.assertFalse(decide().force_rebalance)
        f['bar_ts']=7200;self.assertFalse(decide().force_rebalance)
        f['bar_ts']=18000;self.assertFalse(decide().force_rebalance)
        f['bar_ts']=21600;self.assertFalse(decide().force_rebalance)
        f['bar_ts']=25200;self.assertTrue(decide().force_rebalance)

    def test_reverse_flattens_then_waits_for_next_bar(self):
        p=ExecutionTiming();cfg=TimingConfig();f=feature()
        d=p.decide('ETH',-100,100,-10,-10,-10,f,cfg)
        self.assertEqual(d.target_notional,0);self.assertTrue(d.force_rebalance)
        p.record_fill('ETH',3600,-2,True,1,f)
        self.assertEqual(p.decide('ETH',-100,0,-10,-10,-10,f,cfg).target_notional,0)
        f['bar_ts']=7200
        self.assertEqual(p.decide('ETH',-100,0,-10,-10,-10,f,cfg).target_notional,-100)

    def test_missing_features_allow_only_reduction(self):
        p=ExecutionTiming();cfg=TimingConfig()
        for current,target,want in [(0,100,0),(100,200,100),(100,-100,0),(100,50,50)]:
            self.assertEqual(p.decide('ETH',target,current,10,10,10,None,cfg).target_notional,want)

    def test_rearm_uses_whole_position_pnl(self):
        p=ExecutionTiming();f=feature();cfg=TimingConfig(rearm_after_loss=True)
        p.record_fill('ETH',0,5);p.record_fill('ETH',0,-3,True,1,f)
        self.assertEqual(p.states['ETH'].blocked_side,0)
        p.record_fill('ETH',0,-5);p.record_fill('ETH',0,3,True,1,f)
        self.assertEqual(p.decide('ETH',100,0,10,10,10,f,cfg).target_notional,0)
        f['close']=102.;f['bar_ts']=7200
        self.assertEqual(p.decide('ETH',100,0,10,10,10,f,cfg).target_notional,100)

    def test_long_and_short_trails_force_full_exit(self):
        for side in [1,-1]:
            p=ExecutionTiming();cfg=TimingConfig(trail_atr=3.);f=feature()
            p.record_fill('ETH',0,entry_price=100)
            f['close']=100+10*side;p.decide('ETH',100*side,100*side,10*side,10*side,10*side,f,cfg)
            f['close']=100+6*side;f['bar_ts']=7200
            d=p.decide('ETH',100*side,100*side,10*side,10*side,10*side,f,cfg)
            self.assertTrue(d.force_rebalance);self.assertEqual(p.execution_target(d,100*side,cfg),0)

    def test_restart_and_mode_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'state.sqlite3');state=StateStore(path)
            p=ExecutionTiming();f=feature();f['quality']=.1
            for t in [3600,7200]:
                f['bar_ts']=t;p.decide('ETH',100,100,1,1,1,f,TimingConfig())
            state.save_strategy_state('timing',p.dump())
            state=StateStore(path);q=ExecutionTiming();q.restore(state.load_strategy_state('timing'))
            f['bar_ts']=10800
            self.assertTrue(q.decide('ETH',100,100,1,1,1,f,TimingConfig()).force_rebalance)
            state.switch_mode('live');self.assertEqual(state.load_strategy_state('timing'),{})

    def test_bad_config_and_state_rejected(self):
        for raw in [dict(partial_rebalance=2),dict(enabled='false'),dict(entry_confirm_bars=-1),dict(trail_atr=float('nan'))]:
            with self.assertRaises(ValueError):TimingConfig(**raw)
        with self.assertRaises(ValueError):ExecutionTiming().restore({'ETH':{'last_bar':float('nan')}})

class CrossMarginTests(unittest.TestCase):
    def run_engine(self, margin, current=False, target=1000, allow=True, force_risk_reduction=False):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        state=StateStore(str(Path(tmp.name)/'state.sqlite3'))
        class Exchange:
            def ensure_cross_margin(self,*args):return margin
            def open_dual(self,symbol,side,qty):
                self.orders.append(('open',qty));return dict(left=0,fill_price=100.,fee=0.)
            def reduce_dual(self,symbol,side,qty):
                self.orders.append(('reduce',qty));return dict(left=0,fill_price=100.,fee=0.)
        ex=Exchange();ex.orders=[]
        engine=SystematicEngine(None,ex,state,cache_dir=str(Path(tmp.name)/'klines'))
        if current:state.upsert_position(Position(id='x',symbol='ETH',side='long',size=10,entry_price=100.,stop_price=0.,initial_stop_price=0.,take_profit_1=0.,leverage=0.,quanto_multiplier=1.))
        f=feature();sig=InstrumentSignal('ETH',10,0,10,.2,short_forecast=10,main_forecast=10,timing_feature=f)
        cfg=SystematicConfig(position_sizing_mode="volatility",depth_guard_enabled=False,no_trade_buffer_pct=0,execution_timing={})
        engine._execute_target('ETH',InstrumentTarget('ETH',10,target,.1,.1),sig,100.,{'quanto_multiplier':1.},10000.,cfg,CostConfig(),allow_increase=allow,
                               force_risk_reduction=force_risk_reduction)
        return ex,state,engine,sig,cfg

    def test_only_verified_cross_can_open(self):
        for mode,verified in [('isolated',True),('cross',False),('unknown',True),(None,False)]:
            ex,*_=self.run_engine(dict(margin_mode=mode,verified=verified));self.assertEqual(ex.orders,[])
        ex,*_=self.run_engine(dict(margin_mode='cross',verified=True));self.assertEqual(ex.orders,[('open',10)])

    def test_close_unblocked_by_unknown_margin(self):
        ex,*_=self.run_engine({},current=True,target=0);self.assertEqual(ex.orders,[('reduce',10)])

    def test_explicit_data_risk_reduction_not_halved(self):
        ex,*_=self.run_engine({},current=True,target=200,allow=False,force_risk_reduction=True)
        self.assertEqual(ex.orders,[('reduce',8)])

    def test_entry_gate_keeps_normal_exit_smoothing(self):
        ex,*_=self.run_engine({},current=True,target=200,allow=False)
        self.assertEqual(ex.orders,[('reduce',4)])

    def test_same_bar_does_not_add_again(self):
        ex,state,engine,sig,cfg=self.run_engine(dict(margin_mode='cross',verified=True))
        engine._execute_target('ETH',InstrumentTarget('ETH',10,2000,.2,.2),sig,100.,{'quanto_multiplier':1.},10000.,cfg,CostConfig())
        self.assertEqual(ex.orders,[('open',10)])

class SignalParityTests(unittest.TestCase):
    def test_live_carry_and_covariance_match_historical_inputs(self):
        from unittest.mock import patch
        from src import carry as carry_mod
        n=500
        def frame(seconds):
            c=100+np.arange(n)*.02+np.sin(np.arange(n)/7)
            return pd.DataFrame(dict(timestamp=1_600_000_000+np.arange(n)*seconds,close=c,open=c,high=c+.5,low=c-.5))
        frames={'1h':frame(3600),'4h':frame(14400),'1d':frame(86400)}
        h=pd.DataFrame({'timestamp':frames['4h'].timestamp[::2], 'funding_rate':np.sin(np.arange(250)/3)*.0001})
        with tempfile.TemporaryDirectory() as tmp:
            state=StateStore(str(Path(tmp)/'state.sqlite3'))
            class Exchange:
                def get_contract(self,s):return {'funding_rate':.123,'funding_interval':28800,'quanto_multiplier':1.}
                def get_account_taker_fee_rate(self,s):return .0005
                def get_ticker(self,s):return {'mark_price':100.}
            engine=SystematicEngine(None,Exchange(),state,cache_dir=str(Path(tmp)/'klines'))
            cfg=SystematicConfig()
            with patch('src.data_fetcher.fetch_candles',side_effect=lambda ex,s,interval,*a,**kw:frames[interval]), patch('src.data_fetcher.drop_unclosed_last_bar',side_effect=lambda df,*a:df), patch('src.data_fetcher.fetch_funding_history',return_value=h) as fetch:
                sig,cov,*_=engine._gather_signal('ETH_USDT',cfg,CostConfig())
                engine._gather_signal('ETH_USDT',cfg,CostConfig())
            expected=carry_mod.carry_forecast_series_from_history(frames['4h'].close,'4h',h,28800,cfg,bar_timestamps=frames['4h'].timestamp.values,fallback_funding_rate=0.)
            self.assertAlmostEqual(sig.carry_forecast,float(expected.iloc[-1]))
            self.assertEqual(cov.index.tolist(),frames['4h'].timestamp.tolist())
            self.assertEqual(fetch.call_count,1)

    def test_default_scope_only_eth(self):
        cfg=TimingConfig(**SystematicConfig().execution_timing)
        self.assertTrue(cfg.for_symbol('ETH_USDT').enabled)
        self.assertFalse(cfg.for_symbol('BTC_USDT').enabled)

class InvertedSignalTests(unittest.TestCase):
    run_engine = CrossMarginTests.run_engine
    def test_inverted_direction_transforms_trend_agreement(self):
        ex,state,engine,sig,cfg=self.run_engine(dict(margin_mode='cross',verified=True),target=0)
        cfg.invert_direction=True
        cfg.execution_timing={'require_trend_agreement':True}
        engine._execute_target('ETH',InstrumentTarget('ETH',10,1000,.1,.1),sig,100.,{'quanto_multiplier':1.},10000.,cfg,CostConfig())
        self.assertEqual(ex.orders,[('open',10)])
        self.assertIsNotNone(state.get_position('ETH','short'))
