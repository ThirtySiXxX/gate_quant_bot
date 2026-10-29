"""Eight finite new engineering cases, synthetic only; no old suite invocation."""
from dataclasses import asdict,replace
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import sqlite3
import socket
import time
import unittest
from unittest.mock import patch
import numpy as np
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS,SYMBOLS,HOUR,US,InputGap,exact
from research.qd010.joint_native_bridge import research_config
from research.qd011.codec import pack
from research.qd011.driver import scan
from research.qd012.sources import Hour,Ref,FundingRow,MarkPoint
from research.qd012.native import prepare_native
from research.qd013.market import NativeSeries,MarketCache,cache_identity
from research.qd013.inputs import build_cache,MarkWindow
from research.qd013.compact import signal
from research.qd013.runner import create,Replay
from research.qd013.scenarios import REGISTER,scenario
from research.qd013.exports import export_all,write_bundle,qr014_fields,qr014_candles
from research.qd013.entry import run,AUTH_PATTERN

START=1672531200000000;AT=START+1440*HOUR;END=AT+8*HOUR;TAIL=END+2*HOUR
BASE=Path(__file__).resolve().parents[1]/'research/.data/qd013'


def deny(*a,**kw):raise AssertionError('QD013_OFFLINE_NETWORK_FORBIDDEN')


class ContinuousReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patches=[patch.object(socket,'create_connection',deny),patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny)]
        for p in cls.patches:p.start()
        BASE.mkdir(parents=True,exist_ok=True);cls.budget=sl.configure_resource_budget(BASE,63*1024**2)
        cls.root=BASE/('engineering-'+str(time.monotonic_ns()));cls.root.mkdir()
        cls.hours={};cls.funding={};cls.points={};cls.observations={}
        for coin,i in enumerate(INSTRUMENTS):
            rows=[];base=400+.4*24
            for k in range(1600):
                price=(150+25*math.sin(k/5)+10*math.sin(k/2.7)+.005*k) if coin==0 else (250+35*math.sin(k/5+1.2)+15*math.sin(k/2.7)+.01*k)
                if k>=1416:price=(300+.2*(k-1416)) if coin==0 else (400+.4*(k-1416))
                opened=price;close=price
                if coin and k>=1440:
                    values={0:(base,base),1:(base,base+60),2:(base+60,base+60),3:(base+60,base+10)}
                    opened,close=values.get(k-1440,(base+10,base+10+.01*(k-1444)))
                o,c=format(opened,'.8f'),format(close,'.8f');h=format(max(opened,close)+.5,'.8f');l=format(min(opened,close)-.5,'.8f')
                v='1000000' if k>=1444 else '100000'
                rowid=hashlib.sha256((i+str(k)+o+c+v).encode()).hexdigest()
                rows.append(Hour(i,START+k*HOUR,START+(k+1)*HOUR,START+(k+1)*HOUR,o,h,l,c,v,rowid,'SYNTHETIC',
                    (Ref('1'*64,k+1,'qd013-synthetic','2'*64),)))
            cls.hours[i]=tuple(rows)
            fs=[FundingRow(i,START+k*HOUR+3*US,str((START+k*HOUR)//US+3),'-0.0001',Ref('3'*64,k+1,'synthetic-funding','4'*64)) for k in range(0,1600,8)]
            fs.append(FundingRow(i,AT+2*HOUR+3*US,str((AT+2*HOUR)//US+3),'-0.0001',Ref('3'*64,1601,'synthetic-funding','4'*64)))
            cls.funding[i]=tuple(sorted(fs,key=lambda f:f.source_us))
            cls.points[i]=tuple(MarkPoint(i,t,'128' if coin==0 else '243',(str(t//US),'999','128' if coin==0 else '243','999'),
                (Ref('5'*64,n+1,'synthetic-mark','6'*64),)) for n,t in enumerate(range(AT-180*US,END+US,30*US)))
        cls.identity=cache_identity(sources=['SYNTHETIC_QD013_ONLY'],code={'candidate':'development-new-code'},config=pack(asdict(research_config())),
            scope=dict(warmup_start_us=START,initial_us=AT,economic_end_us=END,tail_end_us=TAIL))
        cls.work={};begin=time.perf_counter()
        cls.cache=build_cache(cls.root/'market.sqlite3',cls.identity,hours=cls.hours,funding=cls.funding,
            mark_streams={i:iter(p) for i,p in cls.points.items()},initial_us=AT,economic_end_us=END,work=cls.work)
        cls.observations['build_seconds']=time.perf_counter()-begin;cls.replay=None

    @classmethod
    def tearDownClass(cls):
        if cls.replay is not None:cls.replay.ledger.close()
        cls.cache.close()
        p=cls.root/'operation-observations.json';raw=json.dumps(dict(work=cls.work,observations=cls.observations),sort_keys=True,indent=2).encode()
        cls.budget.issue(p,len(raw),len(raw));p.write_bytes(raw)
        for x in reversed(cls.patches):x.stop()

    def test_01_native_series_matches_closed_prefix_bits(self):
        start=time.perf_counter()
        for at in (AT,AT+HOUR,AT+4*HOUR):
            original=prepare_native(self.hours,self.funding,at)
            self.assertEqual(original.status,'AVAILABLE',original.reasons)
            for i,s in zip(INSTRUMENTS,SYMBOLS):
                cell=self.cache.get('native',i,at);f=dict(cell,available=at,at=at-HOUR)
                native=signal(s,f)
                self.assertEqual(pack(asdict(native)),pack(asdict(original.signals[s])))
                self.assertEqual(float(cell['cov_btc_btc']).hex(),float(original.covariance.iloc[0,0]).hex())
                self.assertEqual(float(cell['cov_cross']).hex(),float(original.covariance.iloc[0,1]).hex())
                self.assertEqual(float(cell['cov_eth_eth']).hex(),float(original.covariance.iloc[1,1]).hex())
        self.observations['prefix_comparison_seconds']=time.perf_counter()-start
        self.observations['operation_comparison']=dict(original_prepare_calls=6,new_prepare_calls=self.work['native_prepare_calls'],original_covariance_calls=3,new_covariance_series_calls=self.work['covariance_series_calls'],original_full_cache_encodes=6,new_full_cache_encodes=self.work['cache_serializations'])
        self.assertEqual(self.work['native_prepare_calls'],2);self.assertEqual(self.work['covariance_series_calls'],1)

    def test_02_future_rows_do_not_change_cached_past(self):
        changed={i:tuple(replace(r,open='9000',high='9001',low='8999',close='9000',volume_contracts='17.9') if r.open_us>=AT+HOUR else r for r in rows) for i,rows in self.hours.items()}
        fs={i:tuple(replace(f,rate='0.9') if f.rate_available_us>AT else f for f in rows) for i,rows in self.funding.items()}
        series=NativeSeries(changed,fs)
        for row in series.snapshot(AT):self.assertEqual(row,self.cache.get('native',row['instrument_id'],AT))
        gap=dict(self.hours);gap[INSTRUMENTS[0]]=self.hours[INSTRUMENTS[0]][:800]+self.hours[INSTRUMENTS[0]][801:]
        with self.assertRaisesRegex(InputGap,'GAP'):NativeSeries(gap,self.funding)
        w=MarkWindow(INSTRUMENTS[0],iter(self.points[INSTRUMENTS[0]]))
        primary=w.select(AT);slow=w.select(AT,slow=True)
        self.assertEqual(primary['dto']['source_available_us']-primary['dto']['source_us'],60*US)
        self.assertEqual(slow['dto']['source_available_us']-slow['dto']['source_us'],120*US)
        self.assertEqual(w.select(END+5*HOUR)['dto']['status'],'UNKNOWN')

    def test_03_local_cache_and_indexed_fact_selection(self):
        def forbidden():raise AssertionError('CACHE_HIT_REOPENED_RAW')
        work={};hit=build_cache(self.cache.path,self.identity,hours=None,funding=None,mark_streams=None,initial_us=AT,economic_end_us=END,work=work)
        self.assertEqual(hit.key,self.cache.key);hit.close();self.assertTrue(work['cache_hit']);self.assertEqual(work['native_prepare_calls'],0)
        bad=deepcopy(self.identity);bad['schema']='new-incompatible-schema'
        with self.assertRaisesRegex(InputGap,'VERSION_MISMATCH'):MarketCache(self.cache.path,bad)
        led=object.__new__(sl.Ledger);db=sqlite3.connect(':memory:')
        led.index=SimpleNamespace(db=db);led.config=dict(initial_at_us=AT,end_exclusive_us=END,initial_context=dict(schemas=['n']))
        db.execute('CREATE TABLE facts(schema_id TEXT,inst TEXT,available INTEGER,at INTEGER,k TEXT,b BLOB)')
        db.execute('CREATE INDEX facts_selection ON facts(schema_id,inst,available,k)')
        for i in INSTRUMENTS:
            for n in range(128):
                at=AT-(128-n)*HOUR;v=dict(instrument_id=i,scenario_available_at_us=at+HOUR,economic_at_us=at,fact_key=i+':'+str(n),known=n!=127)
                db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',('n',i,at+HOUR,at,v['fact_key'],sl.canonical_bytes(v)))
            for suffix in ('a','z'):
                v=dict(instrument_id=i,scenario_available_at_us=AT,economic_at_us=AT-HOUR,fact_key=i+':tie-'+suffix,known=False)
                db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',('n',i,AT,AT-HOUR,v['fact_key'],sl.canonical_bytes(v)))
            v=dict(instrument_id=i,scenario_available_at_us=AT+HOUR,economic_at_us=AT,fact_key=i+':future',known=True)
            db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',('n',i,AT+HOUR,AT,v['fact_key'],sl.canonical_bytes(v)))
        schema=dict(view_kind='closed_bar',interval_us=HOUR)
        for allowed in (True,False):
            led.config['initial_context']['schemas']=['n'] if allowed else []
            for mode in ('latest_available','available_prefix'):
                selector=dict(schema_id='n',instruments=list(INSTRUMENTS),mode=mode)
                old=[sl.load_json(v[0]) for v in db.execute('SELECT b FROM facts WHERE schema_id=? AND available<=? ORDER BY available,k',('n',AT))]
                old=[v for v in old if allowed or v['scenario_available_at_us']>=AT]
                if mode=='latest_available':
                    latest={}
                    for v in old:latest[v['instrument_id']]=v
                    old=sorted(latest.values(),key=lambda v:(v['scenario_available_at_us'],v['fact_key']))
                before=getattr(led,'_fact_selection_work',{}).get('rows',0)
                new=[sl.load_json(v[0]) for v in led._fact_candidates(selector,schema,AT)]
                self.assertEqual(new,old)
                if mode=='latest_available':self.assertEqual(led._fact_selection_work['rows']-before,2)
        for i in INSTRUMENTS:
            for t in (AT,AT+HOUR):
                v=dict(fact_key=i+':q:'+str(t),instrument_id=i,economic_at_us=t,scenario_available_at_us=t)
                db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',('m',i,t,t,v['fact_key'],sl.canonical_bytes(v)))
        q=list(led._fact_candidates(dict(schema_id='m',instruments=list(INSTRUMENTS),mode='qualified_at_slot'),dict(view_kind='mark_selection',interval_us=0),AT))
        self.assertEqual(len(q),2);self.assertTrue(all(sl.load_json(v[0])['economic_at_us']==AT for v in q))
        self.assertEqual(list(led._fact_candidates(dict(schema_id='n',instruments=list(INSTRUMENTS),mode='latest_available'),schema,END)),[])
        self.observations['selection_work']=dict(led._fact_selection_work)
        bad=object.__new__(sl.Ledger);bad.index=led.index;bad.config=dict(led.config,initial_context=dict(schemas=['n']))
        db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',('n',INSTRUMENTS[0],AT-4*HOUR,AT-4*HOUR,'bad-older',b'{}'))
        with self.assertRaisesRegex(sl.LedgerError,'FUTURE_DEPENDENCY'):
            list(bad._fact_candidates(dict(schema_id='n',instruments=list(INSTRUMENTS),mode='latest_available'),schema,AT))
        db.close()

    def test_04_registered_continuation_preserves_state_between_chunks(self):
        # Final admissible-volatility fixture retains the exact native parity
        # assertion; only raw synthetic prices changed, never risk/strategy.
        original=prepare_native(self.hours,self.funding,AT)
        self.assertEqual(original.status,'AVAILABLE',original.reasons)
        for i,s in zip(INSTRUMENTS,SYMBOLS):
            cell=self.cache.get('native',i,AT)
            self.assertEqual(pack(asdict(signal(s,dict(cell,available=AT,at=AT-HOUR)))),pack(asdict(original.signals[s])))
        p=self.root/'P0';replay=create(p,self.cache,initial_us=AT,economic_end_us=END,tail_end_us=TAIL,write_budget=self.budget.issue)
        replay.advance_chunk(AT+3*HOUR);prior=replay.states(AT+3*HOUR);head=deepcopy(replay.ledger.head)
        replay.ledger.close();replay=Replay.reopen(p/'store')
        self.assertEqual(replay.states(AT+3*HOUR),prior);self.assertEqual(replay.ledger.head,head)
        self.assertEqual(replay.ledger.config['initial_cash_usdt'],'10000')
        last=replay.ledger.config['schedule'][-1]['at_us'];replay.advance_chunk(last)
        self.__class__.replay=replay;self.__class__.last=last
        view=replay.view(last);events=list(scan(replay.ledger,view,'events'))
        fills=[e['body'] for e in events if e['body']['record_type']=='Fill']
        self.assertGreater(len(fills),2);self.assertTrue(all(e['origin']['kind']=='generated' for e in events))
        self.assertTrue(all(f['filled_at_us']<END for f in fills))
        self.assertTrue(any(e['body']['record_type']=='FundingSnapshot' and e['body']['eligible_ranges'] for e in events))
        self.assertTrue(any(e['body']['record_type']=='Posting' and e['body']['booking_at_us']%HOUR==60*US for e in events))
        self.observations['continuous']=dict(ticks=len(replay.ledger.config['schedule']),fills=len(fills),events=len(events),fact_selection=getattr(replay.ledger,'_fact_selection_work',{}))

    def test_05_tail_natural_maturity_and_open_censoring(self):
        self.assertIsNotNone(self.replay,'registered fixture must finish before export checks')
        rows=export_all(self.replay,self.last);self.__class__.exported=rows
        mature=[r for r in rows if r['qr014_episode_fields']['label_status']=='valid']
        censored=[r for r in rows if r['censoring']=='ECONOMIC_CUTOFF_OPEN']
        self.assertTrue(mature,'actual native exit/finality must produce a mature episode')
        self.assertTrue(censored,'open inventory must be censored without forced flattening')
        for r in mature:
            f=r['qr014_episode_fields'];self.assertTrue(f['natural_exit']);self.assertTrue(f['cash_settled']);self.assertTrue(f['completeness_verified'])
            self.assertGreaterEqual(f['label_known_at_us'],f['label_end_us']+HOUR)
        for r in censored:self.assertIsNone(r['qr014_episode_fields']['net_cash_exact'])
        self.observations['exports']=dict(mature=len(mature),censored=len(censored),total=len(rows))

    def test_06_scenario_identity_and_shared_market_isolation(self):
        self.assertEqual(len(REGISTER),9);self.assertEqual(len({s for s,p in REGISTER}),8)
        accounts=[]
        for name,policy in (('F_HIGH','ALLOW_ALL'),('P0','SKIP_FIRST_ADMISSIBLE_BASKET')):
            replay=create(self.root/(name+'-'+policy),self.cache,initial_us=AT,economic_end_us=END,tail_end_us=TAIL,scenario_id=name,policy_id=policy,write_budget=self.budget.issue)
            try:
                replay.advance_chunk(AT)
                if policy!='ALLOW_ALL':
                    initial=replay.states(AT)['policy'];self.assertTrue(initial['native_receipt']['skip_used']);self.assertEqual(initial['basket_status'],'SKIPPED_FIRST_ADMISSIBLE_BASKET')
                replay.advance_chunk(AT+HOUR)
                records=export_all(replay,AT+HOUR)
                for r in records:
                    proposal=r['qr014_episode_fields']['proposal'];self.assertEqual(proposal['scenario_id'],name);self.assertEqual(proposal['policy_id'],policy)
                    self.assertFalse(r['qr014_compatible'])
                    with self.assertRaisesRegex(InputGap,'BASELINE_ONLY'):qr014_fields(r)
                if name=='F_HIGH':
                    fills=[r['body'] for r in scan(replay.ledger,replay.view(AT+HOUR),'events') if r['body']['record_type']=='Fill']
                    self.assertTrue(fills);self.assertTrue(all(f['fee_fraction']=='0.0015' for f in fills))
                accounts.append(replay.ledger.config['ledger_id'])
                self.assertEqual(replay.ledger.config['initial_cash_usdt'],'10000')
            finally:replay.ledger.close()
        self.assertEqual(len(set(accounts)),2)
        self.assertEqual(scenario('M_SLOW')['mark_delay_us'],120*US)
        self.assertTrue(scenario('T_FILL_FIRST')['fill_first'])
        self.assertEqual(scenario('L_EXTRA')['latency_us'],3601*US)

    def test_07_qr014_lineage_cost_breakdown_and_reusable_export(self):
        self.assertTrue(self.exported)
        manifest=write_bundle(self.root/'export',self.exported,dict(cache_key=self.cache.key,head=self.replay.ledger.head))
        saved=[sl.load_json(b) for b in (self.root/'export/episodes.jsonl').read_bytes().splitlines()]
        self.assertEqual(manifest['rows'],len(saved))
        for row in saved:
            fields=qr014_fields(row);self.assertIsInstance(fields['source_refs'],tuple);self.assertIsInstance(fields['proposal']['source_refs'],tuple)
            candles=list(qr014_candles(self.cache,fields['proposal']['instrument_id'],fields['proposal']['decision_us']))
            self.assertEqual(len(candles),169);self.assertEqual(candles[-1]['bar_close_us'],fields['proposal']['decision_us'])
            self.assertIsInstance(candles[-1]['volume_contracts'],str)
            self.assertTrue(fields['proposal']['pre_decision_state_ref']);self.assertTrue(row['registry_refs']);self.assertFalse(row['training_authorized'])
            if fields['label_status']=='valid':
                self.assertEqual(exact(fields['net_cash_exact']),sum((exact(v) for v in row['cost_breakdown_exact'].values()),Fraction(0)))
                self.assertGreater(exact(fields['gross_entry_notional_exact']),0)
                self.assertEqual(fields['label_known_at_us'],max((fields['label_end_us'],)+fields['input_available_us']+fields['posting_available_us']+fields['assertion_available_us']))

    def test_08_real_entry_off_and_fixed_scope(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF_READ_FILES')):
            self.assertEqual(run()['status'],'OFF')
        import re
        self.assertIsNotNone(re.fullmatch(AUTH_PATTERN,'QF-APPROVAL-QD013-PILOT-1'))
        self.assertIsNone(re.fullmatch(AUTH_PATTERN,'QF-APPROVAL-QD012-ACTUAL-SNAPSHOT-2'))
        m=json.loads((Path(__file__).resolve().parents[1]/'research/qd013/manifest.json').read_text())
        self.assertEqual(m['target']['initial_us'],1704067200000000);self.assertEqual(m['target']['economic_end_us'],1790812800000000)
        self.assertEqual(m['target']['tail_end_us'],1790820000000000);self.assertFalse(m['training_authorized'])


if __name__=='__main__':unittest.main()
