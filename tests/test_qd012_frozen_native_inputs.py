"""Only new QD012 connection checks; literal/synthetic sources, no lifecycle."""
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import gzip
import hashlib
import math
import socket
import time
import unittest
from unittest.mock import patch
import numpy as np
from src.execution_timing import ExecutionTiming
from src.carry import align_funding_to_bars
import pandas as pd
from research.qd008.repair_history import hourly_row, canonical
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS, SYMBOLS, HOUR, US
from research.qd011 import driver
from research.qd011.codec import validate_context, pack, projection
from research.qd011.ports import native_inputs, prepared_v2
from research.qd012.sources import (ObjectSpec, ReadPermit, ActualHistoryOff, SourceError,
    OHLCV_MANIFEST_SHA, MARK_HANDOFF_SHA, FUNDING_HANDOFF_SHA, iter_marks, iter_funding, seconds_us)
from research.qd012.native import prepare_native, funding_points
from research.qd012.queries import Query, MarkSelector, query_plan
from research.qd012.prepare import read_hour_prefix, read_funding_prefix, mark_selectors, assemble

ROOT=Path(__file__).resolve().parents[1]/'research/.data/qd012/tmp'
START=1672531200000000  # synthetic clock anchored to UTC day, no actual prices
COUNT=1600
DECISION=START+1440*HOUR


def offline(*args,**kwargs):raise AssertionError('QD012_OFFLINE_NO_NETWORK')


class FrozenNativeInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net=[patch.object(socket,'create_connection',offline),patch.object(socket.socket,'connect',offline),
                 patch.object(socket.socket,'connect_ex',offline)]
        for p in cls.net:p.start()
        cls.root=ROOT/('synthetic-'+str(time.monotonic_ns()));cls.root.mkdir(parents=True,exist_ok=False)
        cls.budget=sl.configure_resource_budget(ROOT,63*1024**2)
        cls.specs=[];cls.permits={};cls.fspecs=[];cls.fpermits={}
        for coin,i in enumerate(INSTRUMENTS):
            lines=[]
            for k in range(COUNT):
                price=100+coin*50+.007*k+2*math.sin(k/19+coin)+.3*math.sin(k/3.7+coin)
                close=format(price,'.8f');high=format(price+1,'.8f');low=format(price-1,'.8f')
                row=hourly_row(dict(timestamp=(START+k*HOUR)//US,
                    values=dict(open=close,high=high,low=low,close=close,volume='17.9' if coin else '25'),
                    source_ref=dict(raw_sha256=str(coin+1)*64,source_row=k+1)),i,'a'*64,1790812800000000)
                lines.append(canonical(row)+b'\n')
            spec,permit=cls.write_source('hour-'+str(coin)+'.jsonl',b''.join(lines),i,'exact_ohlcv_v3_jsonl',OHLCV_MANIFEST_SHA)
            cls.specs.append(spec);cls.permits[spec.path]=permit
            raw='timestamp,funding_rate\n'+''.join(str((START+k*HOUR)//US+3)+','+('0.0001' if k%16==0 else '-0.00008')+'\n' for k in range(0,COUNT,8))
            spec,permit=cls.write_source('fund-'+str(coin)+'.bin',gzip.compress(raw.encode(),mtime=0),i,'funding_csv_gzip',FUNDING_HANDOFF_SHA)
            cls.fspecs.append(spec);cls.fpermits[spec.path]=permit
        cls.hours=read_hour_prefix(cls.specs,cls.permits,max_hours_per_instrument=COUNT)
        cls.funding=read_funding_prefix(cls.fspecs,cls.fpermits,max_records=500)
        cls.bundle=prepare_native(cls.hours,cls.funding,DECISION)

    @classmethod
    def tearDownClass(cls):
        for p in reversed(cls.net):p.stop()

    @classmethod
    def write_source(cls,name,raw,i,fmt,manifest):
        path=cls.root/name
        cls.budget.issue(path,len(raw),len(raw));path.write_bytes(raw)
        spec=ObjectSpec(str(path),hashlib.sha256(raw).hexdigest(),i,fmt,len(raw),name,manifest)
        permit=ReadPermit('QD012_SYNTHETIC_ONLY',(str(path),),manifest,START,START+(COUNT+1)*HOUR,2048,8*1024**2)
        return spec,permit

    def test_raw_decimal_actual_native_covariance_and_context(self):
        b=self.bundle
        self.assertEqual(b.status,'AVAILABLE',b.reasons)
        self.assertEqual(self.hours[INSTRUMENTS[1]][-1].volume_contracts,'17.9')
        self.assertEqual(self.hours[INSTRUMENTS[1]][4].refs[0].source_row,5)
        context=validate_context(b.warmup_context,DECISION)
        self.assertEqual(b.warmup_context['initial_timing_state'],ExecutionTiming().dump())
        for i,s in zip(INSTRUMENTS,SYMBOLS):
            self.assertEqual(len(context[s]['short_ts']),1440)
            self.assertEqual(len(context[s]['main_ts']),360)
            self.assertEqual(len(context[s]['regime_ts']),60)
            self.assertTrue(math.isnan(context[s]['main_f'][0]))
            self.assertEqual(context[s]['timing_features'][-1],b.signals[s].timing_feature)
            self.assertEqual(projection(next(o for o in b.observations if o.instrument_id==i).vol).hex(),b.signals[s].vol_annual.hex())
        a=b.covariance.to_numpy()
        self.assertGreater(np.min(np.linalg.eigvalsh(a)),0)
        self.assertNotEqual(float(a[0,0]).hex(),(b.signals[SYMBOLS[0]].vol_annual**2).hex())
        o=b.observations[0]
        self.assertEqual(projection(o.cov_btc_btc).hex(),float(a[0,0]).hex())
        self.assertEqual(o.regime,context[SYMBOLS[0]]['regime'][-1])

    def test_future_perturbation_and_explicit_missing_data(self):
        changed={i:tuple(replace(r,close='10000',high='10001',open='10000',low='9999',volume_contracts='99999')
            if r.open_us>=DECISION else r for r in rows) for i,rows in self.hours.items()}
        funding={i:tuple(replace(f,rate='0.9') if f.rate_available_us>DECISION else f for f in rows) for i,rows in self.funding.items()}
        after=prepare_native(changed,funding,DECISION)
        self.assertEqual(after.status,'AVAILABLE',after.reasons)
        self.assertEqual(after.warmup_context,self.bundle.warmup_context)
        self.assertEqual(after.observations,self.bundle.observations)
        self.assertTrue(after.covariance.equals(self.bundle.covariance))
        gap=dict(self.hours);gap[INSTRUMENTS[0]]=self.hours[INSTRUMENTS[0]][:700]+self.hours[INSTRUMENTS[0]][701:]
        b=prepare_native(gap,self.funding,DECISION)
        self.assertEqual(b.status,'UNAVAILABLE');self.assertIn('HOURLY_GAP',b.reasons[0])
        f=dict(self.funding);f[INSTRUMENTS[1]]=()
        self.assertIn('MISSING_FUNDING',prepare_native(self.hours,f,DECISION).reasons[0])

    def test_raw_mark_aliases_and_clock_boundaries(self):
        t=DECISION
        rows=[(t-120*US,'100'),(t-120*US,'100'),(t-60*US,'101'),(t+US,'102')]
        body=''.join(str(at//US)+',900,'+price+',901\n' for at,price in rows).encode()
        spec,permit=self.write_source('boundary-mark.csv.gz',gzip.compress(body,mtime=0),INSTRUMENTS[0],'mark_csv_gzip',MARK_HANDOFF_SHA)
        points=tuple(iter_marks(spec,permit));self.assertEqual(len(points),3)
        self.assertEqual([r.source_row for r in points[0].refs],[1,2]);self.assertEqual(points[0].price,'100')
        selector=MarkSelector(INSTRUMENTS[0],iter(points))
        select=lambda at:selector.select(Query(INSTRUMENTS[0],at))
        self.assertEqual(select(t-61*US).reason,'NO_ELIGIBLE_POINT')
        self.assertEqual(select(t-60*US).point.price,'100')
        self.assertEqual(select(t).point.price,'101')
        self.assertEqual(select(t+60*US).point.price,'101')
        self.assertEqual(select(t+121*US).point.price,'102')
        self.assertEqual(select(t+121*US+1).reason,'SOURCE_TOO_OLD')
        self.assertEqual(selector.select(Query(INSTRUMENTS[0],t+122*US),missing_required_month=True).reason,'MISSING_REQUIRED_MONTH')
        self.assertEqual(seconds_us('1700000000.000001'),1700000000000001)
        bad=b'1672531200,1,2,3\n1672531200,1.0,2,3\n'
        spec,permit=self.write_source('conflict.csv.gz',gzip.compress(bad,mtime=0),INSTRUMENTS[0],'mark_csv_gzip',MARK_HANDOFF_SHA)
        with self.assertRaisesRegex(SourceError,'CONFLICTING'):tuple(iter_marks(spec,permit))

    def test_funding_source_semantics_and_execution_off_gate(self):
        raw=b'timestamp,funding_rate\n1672560003,0.0002\n1672560003.000001,0.0003\n'
        spec,permit=self.write_source('fractional-funding.bin',gzip.compress(raw,mtime=0),INSTRUMENTS[0],'funding_csv_gzip',FUNDING_HANDOFF_SHA)
        rows=tuple(iter_funding(spec,permit))
        self.assertEqual(rows[0].source_us,START+8*HOUR+3*US)
        self.assertEqual(rows[0].rate_available_us,START+9*HOUR)
        self.assertEqual(rows[0].ref.source_row,1)
        self.assertEqual(funding_points(rows[:1])[0].source_us,rows[0].source_us)
        with self.assertRaisesRegex(SourceError,'NO_ROUNDING'):funding_points(rows)
        rate=align_funding_to_bars(pd.DataFrame(dict(timestamp=[START//US,rows[0].rate_available_us//US],funding_rate=[.0001,.0002])),
                                   [(START+8*HOUR)//US,(START+12*HOUR)//US])
        self.assertEqual(rate.tolist(),[.0001,.0002])
        fake=replace(self.specs[0],path='/actual-history-must-never-open.jsonl')
        with patch.object(Path,'open',side_effect=AssertionError('RAW_OPEN_FORBIDDEN')):
            with self.assertRaises(ActualHistoryOff):read_hour_prefix([fake])
            with self.assertRaises(ActualHistoryOff):read_funding_prefix(self.fspecs)
            with self.assertRaises(ActualHistoryOff):mark_selectors([])
        bad=replace(self.bundle.observations[0],cov_btc_btc=None)
        target=self.root/'rejected-no-files'
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_NATIVE_V2'):
            driver.create(target,initial_us=DECISION,end_us=DECISION+HOUR,native=[bad],opens=[],marks=[],
                          native_input_version=2,native_context=self.bundle.warmup_context)
        self.assertFalse(target.exists())

    def test_v2_actual_registered_policy_single_tick(self):
        end=DECISION+2*HOUR
        account_sources=sorted({f.source_us for rows in self.funding.values() for f in rows if DECISION<=f.source_us<end})
        qs=list(query_plan(DECISION,end,funding_source_times=account_sources))
        self.assertTrue(all(q.query_us<end for q in qs))
        specs=[];permits={}
        for coin,i in enumerate(INSTRUMENTS):
            times=sorted({q.query_us-60*US for q in qs if q.instrument_id==i})
            raw=''.join(str(at//US)+',900,100,901\n' for at in times).encode()
            spec,permit=self.write_source('account-mark-'+str(coin)+'.csv.gz',gzip.compress(raw,mtime=0),i,'mark_csv_gzip',MARK_HANDOFF_SHA)
            specs.append(spec);permits[spec.path]=permit
        result=assemble(self.hours,self.funding,mark_selectors(specs,permits),decision_times=[DECISION,DECISION+HOUR],
                        economic_end_us=end,settlement_end_us=end+2*HOUR)
        kwargs=result.driver_kwargs
        # Direct packet projection tests actual cache fields before account creation.
        packet=dict(slot=dict(at_us=DECISION+HOUR),causal_config=dict(initial_us=DECISION,native_input_version=2,
            native_schema_id='native-v2',native_context=kwargs['native_context']),permitted_facts=[])
        for n in kwargs['native']:
            vals={f['name']:getattr(n,f['name']) for f in driver.SCHEMAS['native-v2']['fields']}
            packet['permitted_facts'].append(driver.fact('native-v2',n.instrument_id,n.available_us-HOUR,n.available_us,vals,n.instrument_id+str(n.available_us)))
        cache,latest=prepared_v2(packet);signals,_=native_inputs(packet)
        actual=prepare_native(self.hours,self.funding,DECISION+HOUR)
        self.assertEqual(len(cache[SYMBOLS[0]]['short_ts']),1441)
        for i,s in zip(INSTRUMENTS,SYMBOLS):
            self.assertEqual(pack(signals[s].timing_feature),pack(actual.signals[s].timing_feature))
            self.assertEqual(signals[s].combined_forecast,actual.signals[s].combined_forecast)
            self.assertEqual(cache[s]['adaptive_efficiency_ratio'][-1],actual.signals[s].efficiency_ratio)
        continuous=driver.create(self.root/'one-tick',**kwargs)
        try:
            self.assertEqual(continuous.ledger.config['adapters'][3]['causal_config']['native_input_version'],2)
            continuous.advance(DECISION)  # exactly one new input-connection tick, no fills/lifecycle/restore
            states=continuous.states(DECISION);receipt=states['policy']['native_receipt']
            self.assertEqual(pack(receipt['covariance']),pack(self.bundle.covariance.to_numpy().tolist()))
            self.assertEqual(receipt['sizing_vol'],[self.bundle.signals[s].vol_annual for s in SYMBOLS])
            self.assertEqual(receipt['warmup_context_sha256'],self.bundle.warmup_context['context_sha256'])
            self.assertEqual(receipt['regime'],{s:self.bundle.prepared[s]['regime'][-1] for s in SYMBOLS})
            self.assertEqual(receipt['efficiency'],{s:self.bundle.signals[s].efficiency_ratio for s in SYMBOLS})
            self.assertEqual(states['execution']['fills'],[])
        finally:continuous.ledger.close()


if __name__=='__main__':unittest.main()
