"""Order-boundary tests with fake accounts; no credentials/network/live orders."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import tempfile
import unittest
from src.config import SystematicConfig, CostConfig
from src.position_sizing import entry_ticket
from src.systematic_engine import SystematicEngine
from src.portfolio import InstrumentSignal, InstrumentTarget
from src.state import StateStore
from src.exchange_gate import GateExchange
from src.exchange_paper import PaperExchange
from unittest.mock import patch
import numpy as np
import pandas as pd


def contract(maximum=200):
    return dict(quanto_multiplier=1., leverage_min=1, leverage_max=maximum,
                order_size_min=1, order_size_max=1_000_000, taker_fee_rate=.0005)


def tiers(maximum=200):
    return [dict(risk_limit=1_000_000, leverage_max=maximum)]


class TicketTests(unittest.TestCase):
    def ticket(self, symbol="DOGE_USDT", maximum=20, **kw):
        args = dict(symbol=symbol, equity=10000, price=100, contract=contract(maximum),
                    tiers=tiers(maximum), available=10000, fee_rate=.0005)
        args.update(kw)
        return entry_ticket(**args)

    def test_exact_requested_nominal_and_fallback(self):
        for symbol, maximum, leverage, margin, nominal in [
            ("BTC_USDT",200,200,500,100000), ("ETH_USDT",200,200,500,100000),
            ("SOL_USDT",100,100,1000,100000), ("SOL_USDT",200,200,500,100000),
            ("DOGE_USDT",100,20,500,10000), ("XPL_USDT",10,10,1000,10000),
            ("ZEC_USDT",5,5,2000,10000)]:
            with self.subTest(symbol=symbol, maximum=maximum):
                t = self.ticket(symbol, maximum)
                self.assertEqual((t.leverage,t.initial_margin,t.notional), (leverage,margin,nominal))

    def test_size_tier_reduces_leverage_without_reducing_alt_notional(self):
        t=self.ticket(tiers=[dict(risk_limit=5000,leverage_max=20),dict(risk_limit=20000,leverage_max=10)])
        self.assertEqual((t.notional,t.leverage,t.margin_pct),(10000,10,10))

    def test_btc_eth_do_not_silently_replace_200x(self):
        for symbol in ("BTC_USDT","ETH_USDT"):
            with self.assertRaisesRegex(ValueError,"未满足 200x"): self.ticket(symbol,100)

    def test_min_size_is_not_a_step_and_rounds_down(self):
        c=contract(20);c["order_size_min"]=5
        t=self.ticket(price=137,contract=c)
        self.assertEqual(t.quantity,72)
        self.assertLessEqual(t.notional,t.desired_notional)
        self.assertLess(t.desired_notional-t.notional,137)

    def test_no_hidden_clipping_or_guessing(self):
        for override in [dict(available=500),dict(tiers=[]),dict(tiers=[dict(risk_limit=100,leverage_max=20)]),
                         dict(contract={}),dict(contract={**contract(),"order_size_max":3}),
                         dict(contract={**contract(),"contract_type":"stocks"}),
                         dict(equity=0),dict(equity=float("nan")),dict(price=-1),
                         dict(available=float("nan")),dict(fee_rate=float("nan"))]:
            with self.subTest(override=override),self.assertRaises(ValueError):self.ticket(**override)

    def test_initial_margin_and_cost_reserve_are_separate(self):
        t=self.ticket(slippage_bps=8)
        self.assertEqual(t.initial_margin,500)
        self.assertGreater(t.required_available,510)

    def test_compounding_uses_new_equity_once(self):
        t=self.ticket(equity=12000)
        self.assertEqual((t.initial_margin,t.notional),(600,12000))


class FakeExchange:
    def __init__(self,maximum=200):
        self.maximum=maximum;self.orders=[];self.equity=10000;self.available=10000
        self.mode="cross";self.verified=True;self.readback=None;self.left=0
    def get_entry_budget(self):return dict(equity=self.equity,available=self.available)
    def get_entry_contract(self,symbol):return contract(self.maximum)
    def get_risk_limit_tiers(self,symbol):return tiers(self.maximum)
    def get_account_taker_fee_rate(self,symbol):return .0005
    def ensure_cross_margin(self,symbol,leverage):
        self.requested=leverage
        return dict(ok=self.verified,message="fixture",margin_mode=self.mode,verified=self.verified,
                    cross_leverage_limit=leverage if self.readback is None else self.readback)
    def open_dual(self,symbol,side,qty):
        self.orders.append(("open",symbol,side,qty));return dict(left=self.left,fill_price=100.,fee=0)
    def reduce_dual(self,symbol,side,qty):
        self.orders.append(("reduce",symbol,side,qty));return dict(left=0,fill_price=100.,fee=0)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.state=StateStore(str(Path(self.tmp.name)/"state.sqlite3"))
        self.ex=FakeExchange();self.engine=self.new_engine()
        self.cfg=SystematicConfig(depth_guard_enabled=False,no_trade_buffer_pct=0,execution_timing={"enabled":False})
    def new_engine(self):
        return SystematicEngine(None,self.ex,self.state,str(Path(self.tmp.name)/"klines"))
    def execute(self,symbol="BTC_USDT",target=1000,allow=True):
        sig=InstrumentSignal(symbol,10,0,10,.2)
        self.engine._execute_target(symbol,InstrumentTarget(symbol,10,target,.1,.1),sig,
                                    100.,contract(self.ex.maximum),10000,self.cfg,CostConfig(),allow)

    def test_full_ticket_overrides_old_exposure_cap(self):
        self.execute()
        self.assertEqual(self.ex.orders,[("open","BTC_USDT","long",1000)])
        self.assertEqual(self.ex.requested,200)
        self.assertEqual(self.state.get_position("BTC_USDT","long").leverage,200)

    def test_sol_and_alt_leverage_readback(self):
        self.ex.maximum=100;self.execute("SOL_USDT");self.assertEqual(self.ex.requested,100)
        self.ex.maximum=10;self.execute("DOGE_USDT")
        self.assertEqual(self.ex.orders[-1],("open","DOGE_USDT","long",100))
        self.assertEqual(self.ex.requested,10)

    def test_partial_fill_and_restart_never_top_up(self):
        self.ex.left=500;self.execute();self.engine=self.new_engine()
        self.execute(target=2000);self.execute(target=3000)
        self.assertEqual(len(self.ex.orders),1)
        self.assertEqual(self.state.get_position("BTC_USDT","long").size,500)

    def test_reduce_close_unblocked_by_funds_or_mode(self):
        self.execute();self.ex.available=0;self.ex.verified=False
        self.execute(target=500,allow=False)
        self.assertEqual(self.ex.orders[-1],("reduce","BTC_USDT","long",500))
        self.execute(target=0,allow=False)
        self.assertEqual(self.ex.orders[-1],("reduce","BTC_USDT","long",500))

    def test_reversal_closes_first_then_uses_new_equity(self):
        self.execute();self.execute(target=-1000)
        self.assertEqual(len(self.ex.orders),2);self.assertEqual(self.ex.orders[-1][0],"reduce")
        self.ex.equity=12000;self.execute(target=-1000)
        self.assertEqual(self.ex.orders[-1],("open","BTC_USDT","short",1200))

    def test_mismatched_leverage_unknown_mode_or_funds_block_entry(self):
        for key,value in (("readback",20),("mode","unknown"),("verified",False),("available",500)):
            old=getattr(self.ex,key);setattr(self.ex,key,value)
            self.execute();self.assertEqual(self.ex.orders,[]);setattr(self.ex,key,old)
        self.execute(allow=False);self.assertEqual(self.ex.orders,[])

    def test_exit_ratio_survives_restart_and_mode_isolation(self):
        self.execute();self.engine=self.new_engine();self.execute(target=500)
        self.assertEqual(self.ex.orders[-1][-1],500)
        self.state.switch_mode("live")
        self.assertEqual(self.state.load_strategy_state("entry_sizing_v1"),{})


class ExchangeBoundaryTests(unittest.TestCase):
    def exchange(self):
        ex=GateExchange.__new__(GateExchange);ex.settle="usdt";ex.api=Mock();return ex
    def test_zero_is_cross_and_both_legs_must_match(self):
        ex=self.exchange();ex.get_contract=lambda s:contract()
        ex.api.list_positions.return_value=[SimpleNamespace(contract="BTC_USDT",leverage="0",cross_leverage_limit="200"),
                                            SimpleNamespace(contract="BTC_USDT",leverage="0",cross_leverage_limit="200")]
        self.assertTrue(ex.ensure_cross_margin("BTC_USDT",200)["verified"])
        ex.api.update_dual_mode_position_leverage.assert_called_once_with("usdt","BTC_USDT","0",cross_leverage_limit="200")
        ex.api.list_positions.return_value[1].cross_leverage_limit="20"
        self.assertFalse(ex.ensure_cross_margin("BTC_USDT",200)["verified"])
        ex.api.list_positions.return_value[1].leverage="10"
        self.assertFalse(ex.ensure_cross_margin("BTC_USDT",200)["verified"])
    def test_zero_cross_available_not_replaced_by_equity(self):
        ex=self.exchange();acc=SimpleNamespace(total="10000",unrealised_pnl="200",available="10000",cross_available="0",margin_mode=0)
        ex.api.list_futures_accounts.return_value=acc
        self.assertEqual(ex.get_entry_budget(),dict(equity=10200,available=0))
        acc.cross_available=None;self.assertEqual(ex.get_entry_budget()["available"],10000)
        acc.margin_mode=2
        with self.assertRaises(ValueError):ex.get_entry_budget()
    def test_paper_accounts_for_margin_and_fees(self):
        md=Mock();md.get_ticker.return_value={"mark_price":100.};md.get_contract.return_value=contract()
        ex=PaperExchange(md,10000,slippage_bps=0)
        self.assertEqual(ex.ensure_cross_margin("BTC_USDT",200)["cross_leverage_limit"],200)
        ex.open_dual("BTC_USDT","long",1000)
        self.assertEqual(ex.get_entry_budget(),dict(equity=9950,available=9450))


class BacktestSizingTests(unittest.TestCase):
    def simulate(self, maximum=200, symbol="BTC_USDT", missing=False):
        from src.backtest import SymbolBacktestInputs, run_portfolio_backtest
        n=30; ts=np.arange(n)*3600+1_700_000_000
        frame=pd.DataFrame(dict(timestamp=ts,open=100.,high=100.,low=100.,close=100.,volume=1000.))
        inp=SymbolBacktestInputs(symbol,frame,frame,frame,frame,0,28800,1,.0005,
                                leverage_min=1,leverage_max=maximum,order_size_max=1000000,
                                risk_limit_tiers=None if missing else tiers(maximum),
                                funding_history=pd.DataFrame(dict(timestamp=[ts[0],ts[-1]],funding_rate=[0.,0.])))
        cfg=SystematicConfig(execution_timing={"enabled":False},short_trend_interval="1h",main_trend_interval="1h",
                             regime_interval="1h",covariance_interval="1h",min_bars_short=1,min_bars_main=1,
                             min_bars_regime=1,regime_ema_long=1,regime_range_dampen=1,no_trade_buffer_pct=0)
        forecast=pd.Series(np.r_[np.full(15,10.),np.full(15,-10.)])
        def covariance(returns,**kw):
            return list(returns.index),[np.array([[.04/(365*24)]]) for _ in returns.index],list(returns.columns)
        with patch("src.backtest.trend_mod.group_trend_forecast",return_value=forecast), \
             patch("src.backtest.trend_mod.daily_regime_series",return_value=pd.Series(["range"]*n)), \
             patch("src.backtest.carry_mod.carry_forecast_series_from_history",return_value=pd.Series(np.zeros(n))), \
             patch("src.backtest.vol_mod.price_vol_annualized",return_value=pd.Series(np.full(n,.2))), \
             patch("src.backtest.vol_mod.log_returns",return_value=pd.Series(np.zeros(n))), \
             patch("src.backtest.vol_mod.ewma_covariance_series",side_effect=covariance):
            return run_portfolio_backtest([inp],cfg,CostConfig(slippage_bps=0),10000)

    def test_backtest_uses_tickets_compounds_and_conserves_quantities_costs(self):
        result=self.simulate()
        opens=[e for e in result.executions if e["action"]=="open"]
        self.assertEqual(len(opens),2)
        self.assertEqual(opens[0]["quantity"],1000)
        self.assertLess(opens[1]["quantity"],1000)  # Fees reduce equity for the next entry.
        self.assertFalse(any(e["action"]=="add" for e in result.executions))
        for e in opens:
            t=e["entry_ticket"]
            self.assertEqual(t["desired_notional"],t["equity"]*10)
            self.assertLessEqual(t["initial_margin"],t["equity"]*.05)
        balance=0
        for e in result.executions:
            balance+=e["quantity"]*(1 if e["action"]=="open" else -1)
            self.assertGreaterEqual(balance,0)
        self.assertEqual(balance,0)
        self.assertAlmostEqual(sum(e["fee"] for e in result.executions),result.total_fees)
        self.assertAlmostEqual(result.final_equity,10000+sum(t["pnl"] for t in result.trades))
        self.assertTrue(any("尚未模拟完整全仓" in w for w in result.warnings))

    def test_sol_fallback_and_missing_tiers(self):
        result=self.simulate(maximum=100,symbol="SOL_USDT")
        t=next(e["entry_ticket"] for e in result.executions if e["action"]=="open")
        self.assertEqual((t["leverage"],t["initial_margin"]),(100,1000))
        missing=self.simulate(missing=True)
        self.assertEqual(missing.executions,[])
        self.assertTrue(any("缺少风险限额" in r for r in missing.execution_diagnostics["BTC_USDT"]["entry_blocks"]))


class ManualSizingTests(unittest.TestCase):
    def test_manual_preview_uses_equity_and_unknown_cross_blocks_order(self):
        from src.dashboard_web import create_app
        ex=FakeExchange();ex.get_dual_positions=lambda:[];ex.get_ticker=lambda s:dict(mark_price=100.)
        ex.set_leverage_checked=ex.ensure_cross_margin;ex.open_market=Mock()
        cfg=SimpleNamespace(snapshot=lambda:dict(mode="live",settle="usdt",systematic={}))
        creds=SimpleNamespace(load=lambda:SimpleNamespace(is_set=True,api_key="fixture",api_secret="fixture",api_host="unused"))
        state=SimpleNamespace(add_log=lambda *a:None)
        client=create_app(state,cfg,creds,None,None).test_client()
        with patch("src.exchange_gate.GateExchange",return_value=ex):
            body=dict(symbol="BTC_USDT",side="long",notional=1,leverage=1)
            result=client.post("/api/manual/preview",json=body).json
            self.assertTrue(result["ok"])
            self.assertEqual((result["contracts"],result["margin"],result["leverage"]),(1000,500,200))
            ex.mode="unknown"
            self.assertFalse(client.post("/api/manual/order",json=body).json["ok"])
            ex.open_market.assert_not_called()
