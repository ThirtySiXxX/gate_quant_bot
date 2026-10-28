"""Only new tiny synthetic connection tests; no old suite/replay/fit discovery."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import json
import importlib.util
import math
import socket
import time
import unittest

import pandas as pd
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import *
from research.qd010.joint_native_bridge import JointNativeBridge, NativeInputs, Order, FillIntent, rows
from research.qd010.episode_export import export_episode
_spec=importlib.util.spec_from_file_location('_qd010_synthetic_builders',Path(__file__).with_name('test_qd_event_ledger.py'))
builders=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builders)  # Constructors only, no old tests/oracle Ledger.

D = 1_704_067_200 * US
BTC, ETH = INSTRUMENTS
ROOT = Path('research/.data/qd010/tmp') / ('synthetic-' + str(time.monotonic_ns()))


def fill(ident, at, q, price, inst=BTC, order=None):
    r = builders.fill(ident, at, q, price, '0.00075', inst)
    r['multiplier'] = MULTIPLIERS[inst]
    if order:
        r.update(order_id=order.order_id, decision_id=order.decision_id, decision_at_us=order.decision_us)
    return r


def market(at=D, *, btc='100', eth='100', volume='100000000', fill_open='100'):
    marks = [Mark(i, t-60*US, p, f'mark:{i}:{t}') for t in (at, at+HOUR)
             for i, p in ((BTC, btc), (ETH, eth))]
    candles = [Candle(i, t, fill_open if t == at+HOUR else p,
                      '100000', '0.1', p, volume, f'bar:{i}:{t}', t+HOUR)
               for i, p in ((BTC, btc), (ETH, eth)) for t in (at-HOUR, at, at+HOUR)]
    return FrozenInputs(marks=marks, candles=candles)


def native_inputs(at=D, forecast=10):
    prepared = {}
    for symbol in SYMBOLS:
        short_ts = [at/US-(300-j)*3600 for j in range(300)]
        feature = dict(bar_ts=short_ts[-1], quality=1., extension=0., close=100.,
                       recent_high=101., recent_low=99., atr=1., long_run=3, short_run=3)
        prepared[symbol] = dict(short_ts=short_ts,
            main_ts=[at/US-(300-j)*14400 for j in range(300)], regime_ts=[at/US-86400],
            short_f=[forecast]*300, main_f=[forecast]*300, vol_ann=[.5]*300,
            regime=['range'], carry_f=[0.]*300, adaptive_risk_multiplier=[1.]*300,
            adaptive_efficiency_ratio=[1.]*300, adaptive_vol_ratio=[1.]*300,
            timing_features=[feature]*300)
    return NativeInputs(prepared, at, ('synthetic-native-prefix',),
                        pd.DataFrame([[.25, .1], [.1, .25]], index=SYMBOLS, columns=SYMBOLS), at)


class Store:
    ordinal = 0

    def __init__(self, name, records=(), through=D+HOUR):
        self.path = ROOT/name
        self.path.mkdir(parents=True)
        base_reserves = []
        for i in INSTRUMENTS:
            r = builders.reserves(i)
            r.update(record_id='reserve:'+i, expires_at_us=D+10*HOUR)
            base_reserves.append(r)
        c, bound = builders.bind(base_reserves+list(records), fee='0.00075', instruments=INSTRUMENTS)
        c = {k:v for k,v in c.items() if k not in ('namespace','schema_version','source_manifest','expected_funding_snapshots')}
        c.update(scenario_id='P0', end_exclusive_us=D+9*HOUR, knowledge_end_exclusive_us=D+10*HOUR,
                 ingestion_mode='reference_import', adapters=[], initial_adapter_states=[], schedule=[],
                 fact_schemas=[], initial_context=dict(mode='none', from_us=0, schemas=[]),
                 mark_clocks=[], mark_view_bindings=[], mark_requirements=[],
                 expected_snapshots=[dict(instrument_id=r['instrument_id'],event_id=r['record_id'],
                    snapshot_at_us=r['snapshot_at_us'],mapping_rule_id=builders.rid('funding',r['instrument_id']))
                    for r in bound if r['record_type']=='FundingSnapshot'], limits=deepcopy(sl.LIMITS), random_source='NONE')
        for rule in c['rules']:
            if rule['kind'] == 'multiplier':
                rule['parameters']['base_per_contract'] = MULTIPLIERS[rule['instrument_id']]
            if rule['kind'] == 'valuation':
                rule['parameters']['max_age_us'] = 120*US
        self.bodies = []
        for r in bound:
            body = {k:deepcopy(v) for k,v in r.items() if k not in sl.TRANSPORT}
            body['scenario_id'] = 'P0'
            if body['record_type'] in ('Posting','ObligationRevision'):
                oid=body['obligation_id'] if body['record_type']=='Posting' else body['record_id']
                for allocation in body['allocations']:
                    allocation['allocation_id']=sl.digest(['ledger','trajectory','P0',body['instrument_id'],oid,
                        allocation['lot_id'],allocation['unit_start'],allocation['unit_end']])
            self.bodies.append(body)
        source = self.path/'source'
        source.mkdir()
        raw = b'\n'.join(sl.canonical_bytes(r) for r in self.bodies)+b'\n'
        (source/'raw.jsonl').write_bytes(raw)
        sha = sl.hashlib.sha256(raw).hexdigest()
        fact_rows = [dict(fact_key=f'row:{n}', instrument_id=r['instrument_id'], body=r,
                          scenario_available_at_us=r['available_at_us'],
                          raw_refs=[dict(object_id='synthetic',raw_sha256=sha,source_row=n+1)])
                     for n,r in enumerate(self.bodies)]
        fact_bytes = b'\n'.join(sl.canonical_bytes(r) for r in fact_rows)+b'\n'
        (source/'facts.jsonl').write_bytes(fact_bytes)
        fact = dict(root_id='source',relative_path='facts.jsonl',sha256=sl.hashlib.sha256(fact_bytes).hexdigest(),
                    bytes=len(fact_bytes),rows=len(fact_rows))
        obj = dict(object_id='synthetic',root_id='source',instrument_id=BTC,sha256=sha,bytes=len(raw),
                   relative_path='raw.jsonl',format='synthetic_jsonl',source_row_basis='physical_line',
                   original_time_unit='microseconds',retrieved_at_us=None,null_reasons={'retrieved_at_us':'UNKNOWN_RETRIEVAL'})
        request = dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,request_id='create',config=c,
                       raw_catalogue=dict(namespace='qf009.raw-catalogue',schema_version=1,catalogue_id=name,
                                          objects=[obj],fact_store=fact,qualification_ref='0'*64),
                       fact_store=fact,source_roots=[dict(root_id='source',path=str(source.resolve()))],store_root=str(self.path/'store'))
        sl.create(request)
        self.ledger = sl.Ledger(self.path/'store')
        self.sent = set()
        self.advance(through)

    def request(self, through):
        Store.ordinal += 1
        ids = [n for n,b in enumerate(self.bodies) if n not in self.sent and b['available_at_us'] <= through]
        return dict(request_id=f'connection:{Store.ordinal}',expected_audit_prefix=self.ledger.head['audit_prefix'],
                    through_us=through,generated=[], imported=[dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,
                        body=self.bodies[n],origin=dict(kind='reference_import',fact_key=f'row:{n}'),created_at_us=0) for n in ids])

    def advance(self, through):
        req = self.request(through)
        result = self.ledger.advance(req)
        self.sent.update(n for n,b in enumerate(self.bodies) if b['available_at_us'] <= through)
        return result


class ConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ROOT.mkdir(parents=True)
        def offline(*args, **kwargs):
            raise AssertionError('offline connection test: network forbidden')
        cls.old_connect = socket.socket.connect
        socket.socket.connect = offline
        cls.flat = Store('flat')
        cross = [fill('btc',D-HOUR,10000,'100'), fill('eth',D-HOUR,100,'100',ETH)]
        for i,p in ((BTC,'200'),(ETH,'40')):
            m = builders.mark('valuation:'+i,D-60*US,p,i)
            m.update(known_at_us=D, available_at_us=D)
            cross.append(m)
        cls.cross = Store('cross',cross,through=D)

    @classmethod
    def tearDownClass(cls):
        cls.flat.ledger.close()
        cls.cross.ledger.close()
        socket.socket.connect = cls.old_connect

    def bridge(self, store=None):
        return JointNativeBridge((store or self.flat).ledger, mode='synthetic_reference_demo')

    def test_joint_native_signals_allocation_and_timing(self):
        b = self.bridge()
        result = b.decide(D, market(), native_inputs())
        self.assertEqual(tuple(result['allocation'].targets), SYMBOLS)
        self.assertEqual((b.cfg.target_annual_vol_pct,b.cfg.max_instrument_exposure_pct,b.cfg.max_correlated_group_exposure_pct,b.cfg.max_leverage),(100,550,600,40))
        self.assertEqual(result['increase_status'],'ADMITTED')
        self.assertEqual(len(b.pending),2)
        self.assertFalse(b.pending[0].plan.timing_config.enabled)
        self.assertTrue(b.pending[1].plan.timing_config.enabled)
        self.assertLessEqual(result['allocation'].gross_leverage,6)
        self.assertAlmostEqual(result['allocation'].targets['BTC_USDT'].target_notional,10000*.64/math.sqrt(.7),places=8)

    def test_native_joint_crypto_major_cap(self):
        inp=native_inputs()
        for prepared in inp.prepared.values():
            prepared['vol_ann']=[.05]*300
        inp.covariance.iloc[:,:]=[[.0025,.001],[.001,.0025]]
        result=self.bridge().decide(D,market(),inp)
        self.assertAlmostEqual(result['allocation'].gross_leverage,6.)
        self.assertAlmostEqual(result['allocation'].targets['BTC_USDT'].target_notional,30000.)

    def test_covariance_rejected_before_native_fillna(self):
        b, inputs = self.bridge(), native_inputs()
        inputs.covariance.iloc[0,1] = float('nan')
        result=b.decide(D,market(),inputs)
        self.assertIsNone(result['allocation'])
        self.assertEqual(result['joint_input_block_reason'],'INVALID_JOINT_COVARIANCE')
        self.assertEqual(b.pending,())

    def test_missing_covariance_and_other_asset_open_preserve_native_exit(self):
        from src.execution_timing import TimingState
        b=self.bridge(self.cross)
        b.timing.states['ETH_USDT']=TimingState(entry_price=100,best_close=120,last_fill_bar=D/US-7200)
        inp=native_inputs()
        inp.covariance.iloc[0,1]=float('nan')
        inp.prepared['ETH_USDT']['timing_features'][-1]['close']=40.
        m=market(btc='200',eth='40',fill_open='40')
        m=FrozenInputs(marks=m.marks,candles=[r for r in m.candles if not (r.instrument_id==BTC and r.open_us==D+HOUR)])
        result=b.decide(D,m,inp)
        self.assertIsNone(result['allocation'])
        self.assertEqual([(o.instrument_id,o.action) for o in b.reductions],[(ETH,'close')])
        self.cross.advance(D+HOUR)  # New empty prefix only, not a fabricated financial event.
        stage=b.opportunity(D+HOUR,m)
        self.assertEqual([(f.order.instrument_id,f.signed_contracts,f.price) for f in stage['fills']],[(ETH,-100,Fraction('39.98'))])

    def test_shared_cross_unrealized_literal_budget(self):
        f = self.bridge(self.cross).finance(D,market(btc='200',eth='40'))
        self.assertEqual(f['view']['balance']['unrealized_usdt'],'40')
        self.assertEqual(f['equity'],Fraction('10039.85'))
        self.assertEqual(f['held_margin'],1)
        self.assertEqual(f['held_exit_fees'],Fraction('0.18009'))
        self.assertEqual(f['budget'],Fraction('9998.66991'))

    def test_unknown_held_eth_blocks_all_additions(self):
        b = self.bridge(self.cross)
        m = market(btc='200',eth='40')
        m = FrozenInputs(marks=[r for r in m.marks if r.instrument_id == BTC],candles=m.candles)
        f = b.finance(D,m)
        self.assertIsNone(f['equity'])
        self.assertIsNone(f['budget'])
        self.assertEqual(f['positions'][ETH],100)
        self.assertTrue(f['view']['balance']['reductions_supported'])

    def test_unknown_finance_preserves_actual_native_forced_exit(self):
        from src.execution_timing import TimingState
        b = self.bridge(self.cross)
        b.timing.states['ETH_USDT'] = TimingState(entry_price=100,best_close=120,last_fill_bar=D/US-7200)
        m = market(btc='200',eth='40')
        m = FrozenInputs(marks=[r for r in m.marks if r.instrument_id == BTC],candles=m.candles)
        inp = native_inputs()
        inp.prepared['ETH_USDT']['timing_features'][-1]['close'] = 40.
        result = b.decide(D,m,inp)
        self.assertIsNone(result['allocation'])
        self.assertEqual([(o.instrument_id,o.action,o.quantity) for o in b.reductions],[(ETH,'close',100)])
        self.assertEqual(b.pending,())

    def test_unknown_required_funding_claim_is_not_zero(self):
        snapshot=builders.snapshot('unresolved-funding',D-1,[builders.unit('btc',0,10000,'btc')])
        records=[fill('btc',D-HOUR,10000,'100'),snapshot]
        v=builders.mark('mark-btc',D-60*US,'100')
        v.update(available_at_us=D,known_at_us=D)
        records.append(v)
        store=Store('unknown-claim',records,through=D)
        try:
            f=self.bridge(store).finance(D,market())
            self.assertIsNone(f['view']['balance']['liabilities_usdt'])
            self.assertIsNone(f['budget'])
        finally:
            store.ledger.close()

    def test_atomic_basket_budget_equality_and_iteration(self):
        for reverse in (False,True):
            b = self.bridge()
            f = b.finance(D,market())
            # Pick exact notional so each reservation is exactly 60 USDT.
            n = Fraction(60) / (Fraction('1.0008')/200+2*FEE*Fraction('1.0008')+G)
            prices = {i:n/exact(MULTIPLIERS[i]) for i in INSTRUMENTS}
            orders = [Order(str(j),str(j),i,'open',1,1,D,prices[i],n) for j,i in enumerate(INSTRUMENTS)]
            if reverse:
                orders.reverse()
            f['budget'] = Fraction(100)  # Synthetic known risk-input injection, actual ledger E retained.
            self.assertEqual(b.admit(orders,f,prices),'BASKET_BUDGET_INSUFFICIENT')
            self.assertEqual(b.pending,())
            f['budget'] = Fraction(120)
            self.assertEqual(b.admit(orders,f,prices),'ADMITTED')
            self.assertEqual(sum(pending_reserve(o.quantity,o.instrument_id,o.price) for o in b.pending),120)

    def test_partial_zero_fill_and_residual_cancellation(self):
        b = self.bridge()
        m = market(volume='2500.9')
        f = b.finance(D,m)
        orders = tuple(Order(i,i,i,'open',1,4,D,Fraction(100),Fraction(4)*exact(MULTIPLIERS[i])*100) for i in INSTRUMENTS)
        self.assertEqual(b.admit(orders,f,{i:Fraction(100) for i in INSTRUMENTS}),'ADMITTED')
        staged = b.opportunity(D+HOUR,m)
        self.assertEqual([f.quantity for f in staged['fills']],[2,2])
        self.assertEqual([q for _,q in staged['cancelled_residuals']],[2,2])
        self.assertEqual(staged['fills'][0].price,Fraction('100.05'))
        self.assertEqual(staged['status'],'REQUIRES_BOUND_LEDGER_TRANSACTION')
        with self.assertRaisesRegex(InputGap,'OPPORTUNITY_ALREADY_CONSUMED'):
            b.opportunity(D+HOUR,m)

    def test_zero_eth_capacity_does_not_use_btc_capacity(self):
        b = self.bridge()
        m = market(volume='2500.9')
        m = FrozenInputs(marks=m.marks,candles=[replace(r,volume_contracts='0.9') if r.instrument_id == ETH else r for r in m.candles])
        orders = tuple(Order(i,i,i,'open',1,4,D,Fraction(100),Fraction(4)*exact(MULTIPLIERS[i])*100) for i in INSTRUMENTS)
        self.assertEqual(b.admit(orders,b.finance(D,m),{i:Fraction(100) for i in INSTRUMENTS}),'ADMITTED')
        staged=b.opportunity(D+HOUR,m)
        self.assertEqual([(f.order.instrument_id,f.quantity) for f in staged['fills']],[(BTC,2)])
        self.assertEqual(staged['cancelled_residuals'],((BTC,2),(ETH,4)))

    def test_full_basket_recheck_not_rescued_by_partial_capacity(self):
        b = self.bridge()
        m = market(volume='1000',fill_open='100000')
        orders = tuple(Order(i,i,i,'open',1,10000,D,Fraction(1),Fraction(10000)*exact(MULTIPLIERS[i])) for i in INSTRUMENTS)
        self.assertEqual(b.admit(orders,b.finance(D,m),{i:Fraction(1) for i in INSTRUMENTS}),'ADMITTED')
        stage=b.opportunity(D+HOUR,m)
        self.assertNotEqual(stage['basket_status'],'ADMITTED')
        self.assertEqual(stage['fills'],())
        self.assertEqual([q for _,q in stage['cancelled_residuals']],[10000,10000])

    def test_mark_and_funding_clock_edges(self):
        inputs = FrozenInputs(marks=(Mark(BTC,D-60*US,'50000','raw-mark'),),
                              funding=(Funding(BTC,D,'0.0001','raw-rate','fund'),))
        self.assertIsNone(inputs.mark(BTC,D-1).value)
        self.assertEqual(inputs.mark(BTC,D+60*US).value,50000)
        self.assertIsNone(inputs.mark(BTC,D+60*US+1).value)
        self.assertIsNone(inputs.funding_terms('fund',10,D+HOUR-1)['signed_amount_usdt'])
        terms=inputs.funding_terms('fund',10,D+HOUR)
        self.assertEqual(terms['signed_amount_usdt'],Fraction('-0.005'))
        self.assertEqual(terms['posting_us'],D+HOUR+60*US)
        self.assertEqual(execution_boundary(D),D+HOUR)
        self.assertEqual(set(market().execution_open(BTC,D)),{'instrument_id','open_us','open_price','source_ref','basis'})

    def test_real_ledger_commit_and_mature_episode_export(self):
        op = Order('entry-order','entry-decision',BTC,'open',1,10000,D,Fraction(100),Fraction(100))
        cl = Order(f'order:{D+HOUR}:BTC_USDT:close',f'decision:{D+HOUR}:BTC_USDT',BTC,'close',1,10000,D+HOUR,Fraction(100),Fraction(0))
        entry,close = fill('entry',D+HOUR,10000,'100',order=op),fill('exit',D+2*HOUR,-10000,'110',order=cl)
        p1 = builders.posting('paid-entry','fee:entry','-0.075',D+HOUR,builders.unit('entry',0,10000,'entry'))
        p2 = builders.posting('paid-exit','fee:exit','-0.0825',D+2*HOUR,builders.unit('entry',0,10000,'entry'))
        a = builders.assertion(D+3*HOUR, payments=(),ident='final')
        a['scope'].update(episode_id='episode:entry',economic_from_us=D+HOUR,economic_to_exclusive_us=D+2*HOUR+1,event_kinds=['fill','fee','posting'])
        a['obligation_revision_refs']=[dict(obligation_id='fee:entry',revision=1),dict(obligation_id='fee:exit',revision=1)]
        a['posting_refs']=[dict(posting_id=i,revision=1) for i in ('paid-entry','paid-exit')]
        v=builders.mark('entry-mark',D+HOUR-60*US,'100')
        v.update(available_at_us=D+HOUR,known_at_us=D+HOUR)
        revision=builders.revision('fee:entry','entry','-0.08',D+3*HOUR+1,D+HOUR,2,'fee',builders.unit('entry',0,10000,'entry'))
        extra=builders.posting('paid-extra','fee:entry','-0.005',D+3*HOUR+2,builders.unit('entry',0,10000,'entry'))
        a2=deepcopy(a)
        a2.update(revision=2,supersedes_revision=1,available_at_us=D+4*HOUR+2,known_at_us=D+4*HOUR+2,asserted_at_us=D+4*HOUR+2,null_reasons={})
        a2['obligation_revision_refs'][0]['revision']=2
        a2['posting_refs'].append(dict(posting_id='paid-extra',revision=1))
        store = Store('episode',[entry,p1,v,close,p2,a,revision,extra,a2],through=D)
        try:
            b = self.bridge(store)
            for order,at,price,signed,fee in ((op,D+HOUR,100,10000,'-0.075'),(cl,D+2*HOUR,110,-10000,'-0.0825')):
                if order.action=='close':
                    decision=b.decide(D+HOUR,market(at=D+HOUR),native_inputs(D+HOUR,forecast=-10))
                    order=next(o for o in decision['orders'] if o.instrument_id==BTC and o.action=='close')
                staged=dict(at_us=at,fills=(FillIntent(order,10000,signed,Fraction(price),at,Fraction(fee)),))
                result=b.commit_bound_transaction(staged,store.request(at))
                store.sent.update(n for n,body in enumerate(store.bodies) if body['available_at_us']<=at)
                self.assertEqual(result['status'],'FINANCIAL_BATCH_COMMITTED')
            proposal=dict(account_id='ledger',trajectory_id='trajectory',instrument_id=BTC,proposal_id='proposal',
                          pre_decision_state_ref=store.ledger.as_known(dict(cutoff=dict(at_us=D,slot=0)))['view_sha256'],
                          scenario_id='P0',policy_id='ALLOW_ALL',account_binding_id='QR010_SHARED_NATIVE_X10',
                          decision_us=D,side=1,flat_before=True,action='flat_entry',source_refs=('native-known-proposal',))
            immature=export_episode(store.ledger,cutoff=dict(at_us=D+2*HOUR,slot=0),episode_id='episode:entry',proposal=proposal,close_receipts=b.close_receipts)
            self.assertEqual(immature['qr014_episode_fields']['label_status'],'immature')
            self.assertIsNone(immature['qr014_episode_fields']['net_cash_exact'])
            store.advance(D+3*HOUR)
            exported=export_episode(store.ledger,cutoff=dict(at_us=D+3*HOUR,slot=0),episode_id='episode:entry',proposal=proposal,close_receipts=b.close_receipts)
            e=exported['qr014_episode_fields']
            self.assertEqual((e['label_status'],e['net_cash_exact'],e['gross_entry_notional_exact']),('valid','9.8425','100'))
            self.assertEqual(e['label_known_at_us'],D+3*HOUR)
            self.assertIsNone(exported['accepted_export_ref'])
            self.assertEqual(store.ledger.as_known(dict(cutoff=dict(at_us=D+3*HOUR,slot=0)))['balance']['cash_usdt'],'10009.8425')
            rejected=export_episode(store.ledger,cutoff=dict(at_us=D+3*HOUR,slot=0),episode_id='episode:entry',proposal=proposal,close_receipts={})
            self.assertEqual(rejected['qr014_episode_fields']['label_status'],'invalid')
            store.advance(D+3*HOUR+2)
            revised=export_episode(store.ledger,cutoff=dict(at_us=D+3*HOUR+2,slot=0),episode_id='episode:entry',proposal=proposal,close_receipts=b.close_receipts)
            self.assertEqual(revised['qr014_episode_fields']['label_status'],'immature')
            self.assertIsNone(revised['qr014_episode_fields']['net_cash_exact'])
            store.advance(D+4*HOUR+2)
            settled=export_episode(store.ledger,cutoff=dict(at_us=D+4*HOUR+2,slot=0),episode_id='episode:entry',proposal=proposal,close_receipts=b.close_receipts)
            self.assertEqual(settled['qr014_episode_fields']['net_cash_exact'],'9.8375')
            self.assertGreater(settled['qr014_episode_fields']['label_revision'],e['label_revision'])
        finally:
            store.ledger.close()


if __name__ == '__main__':
    unittest.main()
