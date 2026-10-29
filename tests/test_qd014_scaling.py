"""New plan/range/receipt engineering checks; no old test invocation or raw data."""
from dataclasses import asdict
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import socket
import time
import unittest
from unittest.mock import patch
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import HOUR, US, INSTRUMENTS
from research.qd010.joint_native_bridge import research_config
from research.qd011.codec import KINDS, pack
from research.qd011.driver import scan
from research.qd012.sources import Hour, FundingRow, Ref, MarkPoint
from research.qd013.market import cache_identity
from research.qd013.inputs import build_cache
from research.qd013.runner import create as legacy_create
from research.qd013.exports import export_all, write_bundle
from research.qd014.runner import create, Replay
from research.qd014.structure import Plan, wire, reference, validate_window, compact_receipts
from research.qd014.entry import run

ROOT = Path(__file__).resolve().parents[1]/'research/.data/qd014'
ROLES = ['valuation','reservation','decision','permitted_fill','funding_snapshot']


def configuration(times, funding, end):
    schedule, requirements = wire(times, KINDS, INSTRUMENTS, ROLES, end)
    ref = reference(schedule, requirements, funding)
    return dict(schedule=schedule, mark_requirements=requirements, expected_snapshots=funding,
        initial_at_us=times[0], end_exclusive_us=end, knowledge_end_exclusive_us=times[-1]+HOUR,
        instruments=list(INSTRUMENTS), mark_clocks=[dict(instrument_id=i,clock_id='mark-clock') for i in INSTRUMENTS],
        mark_view_bindings=[dict(instrument_id=i,clock_id='mark-clock') for i in INSTRUMENTS],
        adapters=[dict(adapter_id=k,causal_config=dict(static_plan_ref=ref)) for k in KINDS])


class Scaling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def deny(*a, **kw): raise AssertionError('QD014_OFFLINE_ONLY')
        cls.patches=[patch.object(socket,'create_connection',deny),patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny)]
        for p in cls.patches: p.start()
        ROOT.mkdir(parents=True,exist_ok=True)
        cls.root=ROOT/('engineering-'+str(time.monotonic_ns()));cls.root.mkdir()
        cls.budget=sl.configure_resource_budget(ROOT,63*1024**2)
        cls.observations={}

    @classmethod
    def tearDownClass(cls):
        raw=json.dumps(cls.observations,sort_keys=True,indent=2).encode()+b'\n'
        path=cls.root/'observations.json';cls.budget.issue(path,len(raw),len(raw));path.write_bytes(raw)
        for p in reversed(cls.patches):p.stop()

    def test_01_indexed_windows_and_version_rejection(self):
        a=1704067200000000;times=[a,a+7*US,a+HOUR,a+HOUR+60*US,a+2*HOUR,a+3*HOUR]
        cfg=configuration(times,[],a+2*HOUR);plan=Plan(cfg)
        old_schedule=[dict(at_us=t,slots=[dict(slot_id=k+':'+str(t),adapter_id=k,phase=n) for n,k in enumerate(KINDS)]) for t in times]
        old_requirements=[dict(key=dict(instrument_id=i,clock_id='mark-clock',query_at_us=t,purpose=p),before_slots=[k+':'+str(t) for k in KINDS],for_view=p in ('valuation','reservation')) for t in times if t<a+2*HOUR for i in INSTRUMENTS for p in ROLES]
        self.assertEqual(list(plan),old_schedule)
        self.assertEqual(list(plan.due(a-1,a+3*HOUR)),old_requirements)
        for t in times:
            self.assertEqual(list(plan.between(t-1,t)),[t])
            for i in INSTRUMENTS:
                for k in KINDS:self.assertEqual(plan.for_slot(k+':'+str(t),i,t),[r['key'] for r in old_requirements if r['key']['instrument_id']==i and k+':'+str(t) in r['before_slots']])
        self.assertEqual(plan.cursor_count(INSTRUMENTS[0],'mark-clock',times[-1]),20)
        for mutate in ('version','reference','times','mixed','binding'):
            bad=deepcopy(cfg)
            if mutate=='version':bad['schedule']['schema']='unknown'
            elif mutate=='reference':bad['adapters'][0]['causal_config']['static_plan_ref']['sha256']='0'*64
            elif mutate=='times':bad['schedule']['times_us'][1]=a
            elif mutate=='mixed':bad['mark_requirements']=[]
            else:bad['mark_view_bindings']=[]
            with self.assertRaises(sl.LedgerError):Plan(bad)
        window=plan.window(cfg['adapters'][0],dict(value=dict(data={})),a)
        packet=dict(causal_config=window,prior_state=dict(adapter_id='environment',value=dict(data={})),previous_invocation=dict(at_us=a-1,slot=1),slot=dict(at_us=a))
        with self.assertRaisesRegex(sl.LedgerError,'UNSUPPORTED_VERSION'):validate_window(packet)
        unknown=dict(ranges=[{'episode_id':'unsettled'}],posted=False,mark=None,amount=None,known=None)
        active=dict(ranges=[{'episode_id':'active'}],posted=False,mark='243',amount='-1',known=a)
        data=dict(funding=dict(unknown=deepcopy(unknown),active=deepcopy(active),empty=dict(ranges=[],posted=False),posted=dict(ranges=[{}],posted=True)))
        compact_receipts(data,plan.ref)
        self.assertEqual(data['funding'],dict(unknown=unknown,active=active))

    def test_02_full_target_structure_streaming_size(self):
        a=1704067200000000;end=1790812800000000;tail=end+2*HOUR
        funding=[];times=set(range(a,tail,HOUR))
        for t in range(a,end,8*HOUR):
            for i in INSTRUMENTS:funding.append(dict(instrument_id=i,event_id='fund:'+i+':'+str(t),snapshot_at_us=t,mapping_rule_id='funding:'+i))
            times.update(v for v in (t,t+HOUR,t+HOUR+60*US,t+2*HOUR+60*US) if v<tail)
        times=sorted(times);cfg=configuration(times,funding,end);plan=Plan(cfg)
        old_bytes=0;old_hash=hashlib.sha256();new_hash=hashlib.sha256();count=0
        # Full length, but stream rows; never retain the expanded requirement set.
        for t in times:
            if t>=end:continue
            for i in INSTRUMENTS:
                for p in ROLES:
                    r=dict(key=dict(instrument_id=i,clock_id='mark-clock',query_at_us=t,purpose=p),before_slots=[k+':'+str(t) for k in KINDS],for_view=p in ('valuation','reservation'))
                    raw=sl.canonical_bytes(r);old_bytes+=len(raw)+1;old_hash.update(raw+b'\n');count+=1
        for r in plan.due(a-1,tail):new_hash.update(sl.canonical_bytes(r)+b'\n')
        self.assertEqual(new_hash.hexdigest(),old_hash.hexdigest())
        old_schedule_bytes=sum(len(sl.canonical_bytes(t))+1 for t in plan)
        old_causal_bytes=5*len(sl.canonical_bytes(dict(ticks=times,funding_schedule=funding)))
        new_wire_bytes=len(sl.canonical_bytes(dict(schedule=cfg['schedule'],mark_requirements=cfg['mark_requirements'],expected_snapshots=funding)))
        new_causal_bytes=5*len(sl.canonical_bytes(dict(static_plan_ref=plan.ref)))
        before=plan.work['requirements_returned'];rows=list(plan.due(times[100]-1,times[100]));self.assertEqual(len(rows),10)
        self.assertEqual(plan.work['requirements_returned']-before,10)
        self.assertLess(new_wire_bytes,old_bytes+old_schedule_bytes)
        self.observations['full_structure']=dict(ticks=len(times),slots=len(times)*5,requirements=count,funding=len(funding),expanded_requirement_bytes=old_bytes,expanded_schedule_bytes=old_schedule_bytes,old_repeated_causal_bytes=old_causal_bytes,new_wire_bytes=new_wire_bytes,new_repeated_causal_bytes=new_causal_bytes,requirements_stream_sha256=old_hash.hexdigest(),single_tick_requirements=10,work=plan.work)

    def test_03_short_financial_equivalence_and_same_code_reopen(self):
        start=1672531200000000;at=start+1440*HOUR;end=at+8*HOUR;tail=end+2*HOUR
        hours={};funding={};marks={}
        # Reuse the known admissible synthetic price shape as input only; this
        # new check compares two plan representations, not prior research/tests.
        for coin,i in enumerate(INSTRUMENTS):
            rows=[];base=409.6
            for n in range(1456):
                price=(150+25*math.sin(n/5)+10*math.sin(n/2.7)+.005*n) if coin==0 else (250+35*math.sin(n/5+1.2)+15*math.sin(n/2.7)+.01*n)
                if n>=1416:price=300+.2*(n-1416) if coin==0 else 400+.4*(n-1416)
                o=c=price
                if coin and n>=1440:o,c={0:(base,base),1:(base,base+60),2:(base+60,base+60),3:(base+60,base+10)}.get(n-1440,(base+10,base+10+.01*(n-1444)))
                values=[format(x,'.8f') for x in (o,max(o,c)+.5,min(o,c)-.5,c)];v='1000000' if n>=1444 else '100000'
                rows.append(Hour(i,start+n*HOUR,start+(n+1)*HOUR,start+(n+1)*HOUR,*values,v,hashlib.sha256((i+str(n)+''.join(values)).encode()).hexdigest(),'SYNTHETIC',(Ref('1'*64,n+1,'qd014-synthetic','2'*64),)))
            hours[i]=tuple(rows)
            fs=[FundingRow(i,start+n*HOUR+3*US,str((start+n*HOUR)//US+3),'-0.0001',Ref('3'*64,n+1,'qd014-funding','4'*64)) for n in range(0,1456,8)]
            fs.append(FundingRow(i,at+2*HOUR+3*US,str((at+2*HOUR)//US+3),'-0.0001',Ref('3'*64,1500,'qd014-funding','4'*64)))
            funding[i]=tuple(sorted(fs,key=lambda f:f.source_us))
            marks[i]=iter(tuple(MarkPoint(i,t,'128' if coin==0 else '243',(str(t//US),'999','128' if coin==0 else '243','999'),(Ref('5'*64,1,'qd014-mark','6'*64),)) for t in range(at-180*US,end+US,30*US)))
        identity=cache_identity(sources=['QD014_SYNTHETIC'],code={'fixture':'QD014_PLAN_EQUIVALENCE'},config=pack(asdict(research_config())),scope=dict(warmup_start_us=start,initial_us=at,economic_end_us=end,tail_end_us=tail))
        cache=build_cache(self.root/'market.sqlite3',identity,hours=hours,funding=funding,mark_streams=marks,initial_us=at,economic_end_us=end)
        old=new=None
        try:
            old=legacy_create(self.root/'legacy',cache,initial_us=at,economic_end_us=end,tail_end_us=tail,write_budget=self.budget.issue)
            new=create(self.root/'compact',cache,initial_us=at,economic_end_us=end,tail_end_us=tail,write_budget=self.budget.issue)
            old.advance_chunk(at+3*HOUR);new.advance_chunk(at+3*HOUR)
            saved=new.states(at+3*HOUR);head=deepcopy(new.ledger.head);new.ledger.close()
            new=Replay.reopen(self.root/'compact/store')
            self.assertEqual(new.states(at+3*HOUR),saved);self.assertEqual(new.ledger.head,head)
            last=new.ledger.config['_plan_index'].times[-1];old.advance_chunk(last);new.advance_chunk(last)
            oldview,newview=old.view(last),new.view(last)
            self.assertEqual(oldview['balance'],newview['balance'])
            for component in ('lots','closed_slices','obligations','entries','links','orders'):
                self.assertEqual(list(scan(old.ledger,oldview,component)),list(scan(new.ledger,newview,component)),component)
            oe=[r['body'] for r in scan(old.ledger,oldview,'events')];ne=[r['body'] for r in scan(new.ledger,newview,'events')]
            self.assertEqual(oe,ne)
            self.assertGreater(sum(r['record_type']=='Fill' for r in ne),2)
            self.assertTrue(any(r['record_type']=='Posting' for r in ne))
            orows,nrows=export_all(old,last),export_all(new,last)
            keys=('label_status','net_cash_exact','gross_entry_notional_exact','label_end_us','label_known_at_us','natural_exit','cash_settled','completeness_verified')
            self.assertEqual([{k:r['qr014_episode_fields'][k] for k in keys} for r in orows],[{k:r['qr014_episode_fields'][k] for k in keys} for r in nrows])
            self.assertEqual([r['cost_breakdown_exact'] for r in orows],[r['cost_breakdown_exact'] for r in nrows])
            self.assertTrue(any(r['qr014_episode_fields']['label_status']=='valid' for r in nrows))
            self.assertTrue(any(r['censoring']=='ECONOMIC_CUTOFF_OPEN' for r in nrows))
            write_bundle(self.root/'export',nrows,dict(cache_key=cache.key,head=new.ledger.head),write_budget=self.budget.issue)
            self.assertFalse(new.states(last)['environment']['funding'])
            self.assertTrue(old.states(last)['environment']['funding'])
            with self.assertRaisesRegex(sl.LedgerError,'UNSUPPORTED_VERSION'):Replay.reopen(self.root/'legacy/store')
            self.observations['financial']=dict(events=len(ne),fills=sum(r['record_type']=='Fill' for r in ne),exports=len(nrows),legacy_funding_receipts=len(old.states(last)['environment']['funding']),compact_funding_receipts=0,compact_plan_work=new.ledger.config['_plan_index'].work)
        finally:
            if old:old.ledger.close()
            if new:new.ledger.close()
            cache.close()

    def test_04_entry_off_and_old_approval_rejected(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF_READ')):
            self.assertEqual(run()['status'],'OFF')
            with self.assertRaisesRegex(ValueError,'NAMED_QD014'):
                run(authorize_actual_replay=True,human_authorization_ref='QF-APPROVAL-QD013-PILOT-1')


if __name__=='__main__':unittest.main()
