"""Offline QD009 repair candidate and selected development tests.

Historical harness functions are retained for evidence compatibility. The repair
CLI disables freeze/formal/benchmark operations under the human validation gate.
Use an explicitly selected, directly relevant unittest; no app or market data.
"""
from copy import deepcopy
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import resource
import socket
import sys
import tempfile
import time
import traceback
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from research.qd009 import streaming_ledger as sl
_spec=importlib.util.spec_from_file_location('_r3_fixture_builders',Path(__file__).with_name('test_qd_event_ledger.py'))
b=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)
BTC,ETH=sl.INSTRUMENTS
INPUT_SCHEMA={'name':'qd009-synthetic-input-v1','fields':'slot slot_id causal_policy_sha256 permitted_facts before economic_inputs peer_states previous_invocation prior_state causal_config'.split()}
OUTPUT_SCHEMA={'name':'qd009-synthetic-output-v1','fields':'outcome events decisions orders order_transitions reserve_dependencies next_state'.split()}
STATE_SCHEMA={'name':'qd009-synthetic-state-v1','fields':'adapter_id contract_sha256 tracked_episode_ids value state_sha256'.split(),'value_fields':['invocations','spent','decision','order','ranges','initializations','facts','peer_seen','facts_count']}
INTENT_SCHEMA={'name':'qd009-synthetic-intent-v1','action':['open','reduce','close']}
COUNTS=(12,5,7,8,5,7,3,11,7,9,9,7)
REPLICAS={'S01.06':3,'S01.10':2,'S03.01':2,'S03.02':2,'S03.06':2,'S03.07':2,'S04.07':3,'S05.01':2,'S05.02':2,'S05.04':2,'S08.08':2,'S08.09':2,'S08.11':2,'S09.01':2,'S09.02':2,'S09.03':2,'S11.02':2,'S11.04':2,'S11.05':2,'S11.08':2,'S11.09':3,'S12.02':2,'S12.03':2,'S12.04':2,'S12.06':2}
CASE_IDS=[f'S{g:02}.{i:02}' for g,count in enumerate(COUNTS,1) for i in range(1,count+1)]
assert len(CASE_IDS)==90 and sum(REPLICAS.get(k,1) for k in CASE_IDS)==118


def offline(*a,**kw):raise AssertionError('offline: network forbidden')
socket.create_connection=offline
socket.socket.connect=offline
socket.socket.connect_ex=offline


def body(record):return {k:deepcopy(v) for k,v in record.items() if k not in sl.TRANSPORT}
def dump(path,obj):sl._atomic(Path(path),obj)
def jsonl(path,rows):
    h=hashlib.sha256();size=count=0
    with Path(path).open('xb') as f:
        for row in rows:
            raw=sl.canonical_bytes(row)+b'\n'
            budget=sl._budget_for(path)
            if budget:budget.issue(path,size+len(raw),len(raw))
            f.write(raw);h.update(raw);size+=len(raw);count+=1
    return dict(relative_path=Path(path).name,sha256=h.hexdigest(),bytes=size,rows=count)


def config(records=(),instruments=(BTC,),fee='0.0005',cash='10000',multiplier='0.001',calendar=None,tie='snapshot_before_fills'):
    if calendar is None:calendar=[dict(instrument_id=r['instrument_id'],event_id=r['record_id'],snapshot_at_us=r['snapshot_at_us'],mapping_rule_id=b.rid('funding',r['instrument_id'])) for r in records if r['record_type']=='FundingSnapshot']
    # Rule construction must not prematurely admit deliberately invalid bodies.
    legacy,_=b.bind([],instruments=instruments,fee=fee,calendar=calendar,tie=tie)
    c={k:deepcopy(v) for k,v in legacy.items() if k not in ('namespace','schema_version','source_manifest','expected_funding_snapshots')}
    c.update(initial_cash_usdt=cash,knowledge_end_exclusive_us=12000,expected_snapshots=deepcopy(legacy['expected_funding_snapshots']),
             ingestion_mode='reference_import',adapters=[],initial_adapter_states=[],schedule=[],fact_schemas=[],
             initial_context=dict(mode='none',from_us=0,schemas=[]),mark_clocks=[],mark_view_bindings=[],mark_requirements=[],limits=deepcopy(sl.LIMITS),random_source='NONE')
    for r in c['rules']:
        if r['kind']=='multiplier':r['parameters']['base_per_contract']=multiplier
    return c


class Fixture:
    def __init__(self,parent,records=(),c=None,facts=None):
        self.path=Path(parent).resolve();self.path.mkdir(parents=True,exist_ok=False);self.records=[body(r) for r in records]
        self.config=deepcopy(c or config(records));source=self.path/'source';source.mkdir()
        raw=jsonl(source/'raw.jsonl',self.records if facts is None and self.records else facts if facts else [dict(empty_synthetic_source=True)])
        obj=dict(object_id='synthetic',root_id='source',instrument_id=self.config['instruments'][0],sha256=raw['sha256'],bytes=raw['bytes'],relative_path=raw['relative_path'],format='synthetic_jsonl',source_row_basis='physical_line',original_time_unit='microseconds',retrieved_at_us=None,null_reasons={'retrieved_at_us':'UNKNOWN_RETRIEVAL'})
        if facts is None:
            rows=[dict(fact_key=f'fact:{i:08}',instrument_id=r['instrument_id'],body=r,scenario_available_at_us=r['available_at_us'],raw_refs=[dict(object_id='synthetic',raw_sha256=raw['sha256'],source_row=i+1)]) for i,r in enumerate(self.records)]
        else:
            rows=deepcopy(facts)
            for i,row in enumerate(rows):row['raw_refs']=[dict(object_id='synthetic',raw_sha256=raw['sha256'],source_row=i+1)]
        ref=dict(root_id='source',**jsonl(source/'facts.jsonl',rows));self.rows=rows
        cat=dict(namespace='qf009.raw-catalogue',schema_version=1,catalogue_id='fixture',objects=[obj],fact_store=ref,qualification_ref='0'*64)
        self.request=dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,request_id='create',config=self.config,raw_catalogue=cat,fact_store=ref,source_roots=[dict(root_id='source',path=str(source))],store_root=str(self.path/'store'))
        self.head=sl.create(self.request);self.ledger=sl.Ledger(self.path/'store');self.ordinal=0

    def envelopes(self,indices=None):
        return [dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,body=self.records[i],origin=dict(kind='reference_import',fact_key=f'fact:{i:08}'),created_at_us=0) for i in (range(len(self.records)) if indices is None else indices)]
    def request_at(self,t,indices=None):
        self.ordinal+=1
        return dict(request_id=f'request:{self.ordinal}',expected_audit_prefix=self.ledger.head['audit_prefix'],through_us=t,imported=self.envelopes(indices),generated=[])
    def advance(self,t,indices=None):return self.ledger.advance(self.request_at(t,indices))
    def view(self,t,slot=0):return self.ledger.as_known(dict(cutoff=dict(at_us=t,slot=slot)))
    def balance(self,t,slot=0):return self.view(t,slot)['balance']
    def page(self,t,c,slot=0,limit=64):
        view=self.view(t,slot);token=None;result=[]
        while True:
            page=self.ledger.scan(dict(view_sha256=view['view_sha256'],component=c,filter=dict(kind='all'),after=token,limit=limit,null_reasons={} if token else {'after':'START_OF_COMPONENT'}));result+=page['items'];token=page['next']
            if token is None:return result
    def reopen(self):
        self.ledger.close();self.ledger=sl.Ledger(self.path/'store')
    def checkpoint(self):return self.ledger.checkpoint(dict(expected_head=self.ledger.head['audit_prefix']))
    def restore(self,cp):
        head=self.ledger.head['audit_prefix'];self.ledger.close()
        try:return sl.restore(dict(checkpoint=cp,expected_committed_head=head,store_root=str(self.path/'store')))
        finally:self.ledger=sl.Ledger(self.path/'store')
    def close(self):self.ledger.close()


def expect(code,call):
    try:call()
    except sl.LedgerError as e:
        assert e.code==code,(code,e.code,str(e));return e
    raise AssertionError('missing '+code)


def basic_tape():return b.economic_tape()

def one_fill(id='open',t=10,q=1,price='100',inst=BTC):
    r=b.fill(id,t,q,price,'0',inst);r['multiplier']='1';return r

def zero_reserve(inst=BTC,t=0,margin='0',fees='0',expires=10000):
    r=b.reserves(inst);r.update(available_at_us=t,effective_at_us=t,known_at_us=t,expires_at_us=expires,reserved_margin_usdt=margin,reserved_fees_usdt=fees);return r


def primitive_config(records=(),instruments=(BTC,),**kw):return config(records,instruments,fee='0',cash='1000',multiplier='1',**kw)


def benchmark_tape(n):
    """Fixed eight-body cycles, then the contract's earliest-lot suffix."""
    records=[];cycles=n//8-1
    for i in range(cycles):
        t=10+i;op=f'open:{i}';cl=f'close:{i}';f=one_fill(op,t);f['sequence']=1;f['null_reasons']={};x=one_fill(cl,t,-1,'101');x['sequence']=2;x['null_reasons']={}
        rev=b.revision('fee:'+op,op,'-0.1',t,t,2,'fee',b.unit(op,0,1,op))
        pay=b.posting('payment:'+str(i),'fee:'+op,'-0.1',t,b.unit(op,0,1,op))
        mark=b.mark('mark:'+str(i),t,'100');reserve=zero_reserve(t=t);reserve['record_id']='reserve:'+str(i)
        snap=b.snapshot('snapshot:'+str(i),t,[])
        rev0=b.revision('ob:snapshot:'+str(i),'snapshot:'+str(i),'0',t,t,2);rev0['allocations']=[]
        records.extend((f,x,rev,pay,mark,reserve,snap,rev0))
    t=10+cycles+10;unknown=b.revision('fee:open:0','open:0',None,t,10,3,'fee',b.unit('open:0',0,1,'open:0'))
    known=b.revision('fee:open:0','open:0','-0.05',t,10,4,'fee',b.unit('open:0',0,1,'open:0'))
    refund=b.posting('refund','fee:open:0','0.05',t,b.unit('open:0',0,1,'open:0'));refund['corrects_posting_id']='payment:0';refund['null_reasons']={}
    mark=b.mark('last-mark',t,'100');reserve=zero_reserve(t=t);reserve['record_id']='last-reserve';snap=b.snapshot('last-snapshot',t,[])
    rev0=b.revision('ob:last-snapshot','last-snapshot','0',t,t,2);rev0['allocations']=[]
    assertion=b.assertion(t,ident='first-finality',payments=('payment:0','refund'))
    assertion['scope'].update(episode_id='episode:open:0',economic_from_us=10,economic_to_exclusive_us=11,event_kinds=['fill','fee','posting'])
    assertion['obligation_revision_refs']=[dict(obligation_id='fee:open:0',revision=4),dict(obligation_id='fee:close:0',revision=1)]
    records.extend((unknown,known,refund,mark,reserve,snap,rev0,assertion));assert len(records)==n
    return records


class StreamingLedgerDevelopment(unittest.TestCase):
    def setUp(self):
        unit_root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');unit_root.mkdir(parents=True,exist_ok=True);self.tmp=SimpleNamespace(name=tempfile.mkdtemp(dir=unit_root));self.root=Path(self.tmp.name).resolve()
    def fixture(self,*args,**kw):
        f=Fixture(self.root/('fixture'+str(len(list(self.root.iterdir())))),*args,**kw);self.addCleanup(f.close);return f

    def test_economic_cash_fifo_old_views_checkpoint(self):
        f=self.fixture(basic_tape());f.advance(10)
        self.assertEqual(f.balance(10)['cash_usdt'],'10001.45')
        self.assertEqual(f.balance(10)['liabilities_usdt'],'0')
        closed=f.page(10,'closed_slices');self.assertEqual([(x['realized_price_pnl_usdt'],x['entry_fee_cash_usdt'],x['exit_fee_cash_usdt'],x['funding_cash_usdt']) for x in closed],[('2','-0.2495','-0.2505','-0.05')])
        before=f.view(1);cp=f.checkpoint();f.restore(cp);self.assertEqual(before,f.view(1))

    def test_shared_account_cash_reserves_and_unknown(self):
        rs=[zero_reserve(BTC,0,'800'),zero_reserve(ETH),one_fill('btc',10,1,inst=BTC),one_fill('eth',10,1,inst=ETH),b.mark('btc-mark',10,'99'),b.mark('eth-mark',10,'98',ETH)]
        c=primitive_config(rs,(BTC,ETH));c['initial_cash_usdt']='10000';f=self.fixture(rs,c=c);f.advance(10)
        x=f.balance(10);self.assertEqual(x['cash_usdt'],'10000');self.assertEqual(x['unrealized_usdt'],'-3');self.assertEqual(x['simulated_budget_usdt'],'9197')
        cp=f.checkpoint();f.restore(cp);self.assertEqual(f.balance(10),x)

    def test_request_replay_and_sealed_availability(self):
        rs=[zero_reserve(),one_fill()];f=self.fixture(rs,c=primitive_config(rs));r=f.request_at(10);a=f.ledger.advance(r)
        self.assertEqual(f.ledger.advance(r)['status'],'replayed');self.assertEqual(f.ledger.head,a['after'])
        cp=f.checkpoint();f.restore(cp);self.assertEqual(f.ledger.advance(r)['status'],'replayed')

    def test_current_query_status_checkpoint(self):
        c,facts=query_config();f=self.fixture(c=c,facts=facts);f.advance(65,[])
        self.assertEqual(f.balance(65)['mark_query_qualification'],'UNKNOWN');self.assertEqual(f.balance(65)['simulated_budget_usdt'],None)
        old=f.view(50);cp=f.checkpoint();f.restore(cp);self.assertEqual(f.view(50),old);self.assertEqual(f.balance(65)['mark_query_qualification'],'UNKNOWN')

    def test_ancient_fee_unknown_restore_refund(self):
        records=benchmark_tape(16);f=self.fixture(records,c=primitive_config(records,tie='fills_before_snapshot'))
        f.advance(10,range(8));old=f.view(10);cp=f.checkpoint();f.restore(cp);f.advance(21,range(8,16))
        self.assertEqual(f.balance(21)['cash_usdt'],'1000.95');self.assertEqual(f.view(10),old)
        self.assertEqual(f.page(21,'closed_slices')[0]['entry_fee_cash_usdt'],'-0.05')


def query_fact(inst,q,status='SUPPORTED',reason=None,source=0,available=0,price='100',clock='mark-clock',roles=('valuation','reservation')):
    dto=dict(instrument_id=inst,query_us=q,mark_clock_id=clock,roles=list(roles),status=status,source_us=source if status=='SUPPORTED' else None,
             source_available_us=available if status=='SUPPORTED' else None,source_semantic_key=[inst,'archive-mark',source] if status=='SUPPORTED' else None,
             mark_price=price if status=='SUPPORTED' else None,selected_at_us=q,consumer_available_us=q,unknown_reason=reason)
    return sl.normalize_mark_selection(dto,'mark-selection',roles)


def query_config():
    facts=[query_fact(BTC,50,source=0,available=50),query_fact(BTC,51,source=0,available=50),query_fact(BTC,65,'UNKNOWN','MISSING_REQUIRED_MONTH')]
    c=primitive_config();c['ingestion_mode']='controlled_adapters';c['fact_schemas']=[dict(schema_id='mark-selection',kind='mark',view_kind='mark_selection',interval_us=0,fields=[dict(name=x['name'],type=x['cell']['type'],unit='UTC_microseconds' if x['cell']['type']=='T' else 'USDT_per_base' if x['name']=='selected_price' else 'none') for x in facts[0]['cells']])]
    c['mark_clocks']=[dict(instrument_id=BTC,clock_id='mark-clock',valuation_rule_id=b.rid('valuation'),multiplier_rule_id=b.rid('multiplier'),source_delay_us=50,max_source_age_us=100,max_available_age_us=100)]
    c['mark_view_bindings']=[dict(instrument_id=BTC,clock_id='mark-clock')]
    c['mark_requirements']=[dict(key=dict(instrument_id=BTC,clock_id='mark-clock',query_at_us=q,purpose=p),before_slots=[],for_view=True) for q in (50,51,65) for p in ('valuation','reservation')]
    return c,facts





def adapter_state(id,value=None,tracked=()):
    state=dict(adapter_id=id,contract_sha256=sl.digest(STATE_SCHEMA),tracked_episode_ids=list(tracked),value={} if value is None else value)
    state['state_sha256']=sl.digest(state);return state


def port_definition(id,role,cfg=None,selectors=None,peers=None):
    definition=dict(adapter_id=id,role=role,code_commit=os.environ.get('QD009_CODE_COMMIT','6c606b60c33b191ef3dec8193bd6ad67acee96b9'),
       source_files=[dict(relative_path=p,sha256=hashlib.sha256((Path(__file__).resolve().parents[1]/p).read_bytes()).hexdigest()) for p in ('tests/test_qd_streaming_ledger.py','tests/test_qd_event_ledger.py','research/qd009/streaming_ledger.py')],entrypoint='tests.test_qd_streaming_ledger.SyntheticPort',
       input_contract_sha256=sl.digest(INPUT_SCHEMA),output_contract_sha256=sl.digest(OUTPUT_SCHEMA),state_contract_sha256=sl.digest(STATE_SCHEMA),causal_config=cfg or {},approval_ref=sl.digest(['synthetic-only-candidate',INPUT_SCHEMA,OUTPUT_SCHEMA,STATE_SCHEMA]),
       fact_selectors=[],ledger_selectors=selectors or [],peer_state_selectors=peers or [])
    return definition


class SyntheticPort:
    """Frozen synthetic typed script only. This is NOT the native S13 bridge."""
    def validate_input(self,p):
        sl.shape(p,'slot slot_id causal_policy_sha256 permitted_facts before economic_inputs peer_states previous_invocation prior_state causal_config')
        sl.need(all(x['scenario_available_at_us']<=p['slot']['at_us'] for x in p['permitted_facts']),'FUTURE_DEPENDENCY')
        self.validate_state(p['prior_state'])
    def validate_output(self,r):
        sl.shape(r,'outcome events decisions orders order_transitions reserve_dependencies next_state');self.validate_state(r['next_state'])
    def validate_state(self,s):
        sl.shape(s,'adapter_id contract_sha256 tracked_episode_ids value state_sha256');sl.need(type(s['value']) is dict and set(s['value'])<=set(('invocations','spent','decision','order','ranges','initializations','facts','peer_seen','facts_count')),'INPUT_BINDING_MISMATCH')
        sl.need(s['state_sha256']==sl.digest({k:v for k,v in s.items() if k!='state_sha256'}),'INPUT_BINDING_MISMATCH')
    def evaluate(self,p):
        at=p['slot']['at_us'];cfg=p['causal_config'];mode=cfg['mode'];state=deepcopy(p['prior_state']);value=state['value'];value['invocations']=value.get('invocations',0)+1
        result=dict(outcome='noop',events=[],decisions=[],orders=[],order_transitions=[],reserve_dependencies=[],next_state=state)
        inst=cfg.get('instrument',BTC);scope=cfg.get('scope',dict(ledger_id='ledger',trajectory_id='trajectory',scenario_id='scenario'))
        if mode=='forbidden_file':Path('/unlisted/future').read_bytes()
        elif mode=='forbidden_entropy':os.urandom(8)
        elif mode=='forbidden_global':raise sl.LedgerError('FORBIDDEN_INPUT')
        elif mode=='oversized_output':result['events']=[body(zero_reserve())]*65;result['outcome']='emit'
        elif mode=='oversized_state':value['spent']='x'*(2*1024**2+1)
        elif mode=='reserve':
            margin=cfg.get('margin','0');fees=cfg.get('fees','0')
            r=body(zero_reserve(inst,at,margin,fees));r['record_id']=cfg['id']
            result.update(outcome='emit',events=[r]);dep=dict(reserve_key=sl.key_of(r),margin=dict(kind='independent'),fees=dict(kind='independent'))
            if cfg.get('mark_fees'):dep['fees']=dict(kind='current_mark',query_key=dict(instrument_id=inst,clock_id='mark-clock',query_at_us=at,purpose='reservation'))
            result['reserve_dependencies']=[dep]
        elif mode=='policy':
            action='close' if at==cfg.get('close_at') else cfg.get('action','open');id=sl.business_id(scope,inst,'decision',at,p['slot_id'],0);order=sl.business_id(scope,inst,'order',at,p['slot_id'],0)
            result['decisions']=[dict(decision_id=id,at_us=at,instrument_id=inst,order_ids=[order],input_projection_sha256=sl.digest(p),prior_adapter_state_sha256=p['prior_state']['state_sha256'],intent_contract_sha256=sl.digest(INTENT_SCHEMA),intent=dict(action=action))]
            result['orders']=[dict(order_id=order,decision_id=id,instrument_id=inst,action=action,direction='long',requested_contracts=1 if action=='close' else cfg.get('quantity',1),submitted_at_us=at,eligible_at_us=at+1,expires_at_us=cfg.get('expires',1000),payload_contract_sha256=sl.digest(INTENT_SCHEMA),payload=dict(action=action))]
            value.update(decision=id,order=order)
        elif mode=='execution':
            orders=[x['value'] for selection in p['economic_inputs'] for x in selection['items'] if x['kind']=='order' and x['value']['status'] in ('pending','partially_filled')]
            for i,o in enumerate(orders):
                intent=o['intent'];id=sl.business_id(scope,inst,'fill',at,p['slot_id'],i);q=min(o['remaining_contracts'],cfg.get('fill_quantity',1));q=-q if intent['action'] in ('close','reduce') else q
                f=body(one_fill(id,at,q,cfg.get('price_by_time',{}).get(str(at),cfg.get('price','100')),inst));f.update(order_id=intent['order_id'],decision_id=intent['decision_id'],decision_at_us=intent['submitted_at_us'])
                result['events'].append(f);result['order_transitions'].append(dict(order_id=intent['order_id'],at=p['slot'],status='filled' if abs(q)==o['remaining_contracts'] else 'partially_filled',fill_keys=[sl.key_of(f)],reason='synthetic'))
                if cfg.get('cancel_remainder') and abs(q)<o['remaining_contracts']:result['order_transitions'].append(dict(order_id=intent['order_id'],at=p['slot'],status='cancelled',fill_keys=[],reason='synthetic-cancel'))
            result['outcome']='emit' if result['events'] else 'noop'
        elif mode=='context':
            value['initializations']=value.get('initializations',0)+(p['previous_invocation'] is None)
            value['facts']=deepcopy(p['permitted_facts'])
        elif mode=='copy_peer':
            value['peer_seen']=p['peer_states'][0]['value']['invocations']
        elif mode=='mark_from_context':
            values=[x['value'] for sel in p['economic_inputs'] for x in sel['items'] if x['kind']=='query_status' and x['value']['key']['purpose']=='valuation']
            if values and values[0]['status']=='SUPPORTED':
                selected=values[0];r=body(b.mark('corroborating:'+str(at),selected['source_at_us'],selected['mark_price'],inst));r.update(known_at_us=at,available_at_us=at);result.update(outcome='emit',events=[r])
        elif mode=='backdated_valuation':
            r=body(b.mark('backdated',1120,'99',inst));result.update(outcome='emit',events=[r])
        elif mode=='environment_fixture':
            if at==0:
                result.update(outcome='emit',events=[body(zero_reserve())])
            elif at==20:
                ranges=[u for sel in p['economic_inputs'] for x in sel['items'] if x['kind']=='live_lot' for u in x['value']['live_ranges']]
                value['ranges']=ranges;snap=body(b.snapshot('snapshot',20,ranges,inst));rev=body(b.revision('ob:snapshot','snapshot','-0.2',20,20,1,units=ranges[0],inst=inst))
                result.update(outcome='emit',events=[snap,rev])
            elif at==50:
                id=sl.business_id(scope,inst,'posting',at,p['slot_id'],0);post=body(b.posting(id,'ob:snapshot','-0.2',50,value['ranges'][0],inst))
                result.update(outcome='emit',events=[post])
        elif mode=='shared_budget':
            # A synthetic allocation port consumes one global remaining budget.
            # It deliberately has no separate per-asset cash initializer.
            budget=p['before']['balance']['simulated_budget_usdt'];want=Fraction(cfg['want']);allowed=budget is not None and Fraction(budget)>=want
            value['spent']=sl.fmt(want if allowed else 0)
            if allowed:
                r=body(zero_reserve(inst,at,cfg['want']));r['record_id']=cfg['id'];result.update(outcome='emit',events=[r],reserve_dependencies=[dict(reserve_key=sl.key_of(r),margin=dict(kind='independent'),fees=dict(kind='independent'))])
        state['state_sha256']=sl.digest({k:v for k,v in state.items() if k!='state_sha256'});return result


def install_ports(c,definitions,schedule):
    c['ingestion_mode']='controlled_adapters';c['adapters']=definitions;c['schedule']=schedule;c['initial_adapter_states']=[adapter_state(a['adapter_id']) for a in definitions]
    for a in definitions:sl.register_port(a,SyntheticPort())
    return c


def tick(t,*ids):return dict(at_us=t,slots=[dict(slot_id=f'{id}:{t}',adapter_id=id,phase=i) for i,id in enumerate(ids)])


def controlled_config():
    c=primitive_config(tie='fills_before_snapshot');selector=dict(selection_id='orders',instruments=[BTC],kind='orders_active_and_changed')
    defs=[port_definition('P','policy',dict(mode='policy',quantity=3,close_at=30)),port_definition('X','execution',dict(mode='execution',fill_quantity=1,cancel_remainder=True,price_by_time={'20':'100','40':'101'}),[selector]),port_definition('E','environment',dict(mode='environment_fixture'),[dict(selection_id='live',instruments=[BTC],kind='live_lots')])]
    c['expected_snapshots']=[dict(instrument_id=BTC,event_id='snapshot',snapshot_at_us=20,mapping_rule_id=b.rid('funding'))]
    return install_ports(c,defs,[tick(0,'E'),tick(10,'P'),tick(20,'X','E'),tick(30,'P'),tick(40,'X'),tick(50,'E')])


def qg_config(which):
    B=1000;inst=BTC if which==1 else ETH
    qs=(50,51,65) if which==1 else (60,61,120,121,125)
    facts=[]
    for q in qs:
        if (which==1 and q==65) or (which==2 and q==121):facts.append(query_fact(inst,B+q,'UNKNOWN','MISSING_REQUIRED_MONTH' if which==1 else 'NO_ELIGIBLE_POINT'))
        else:
            source=B-10 if which==1 else B+(62 if q==125 else 0);available=source+60
            facts.append(query_fact(inst,B+q,source=source,available=available,price='99' if which==2 and q==125 else '100'))
    c=primitive_config(instruments=(inst,));c.update(initial_at_us=B-20,end_exclusive_us=B+200,knowledge_end_exclusive_us=B+250,initial_context=dict(mode='none',from_us=B-20,schemas=[]))
    c['fact_schemas']=[dict(schema_id='mark-selection',kind='mark',view_kind='mark_selection',interval_us=0,fields=[dict(name=x['name'],type=x['cell']['type'],unit='UTC_microseconds' if x['cell']['type']=='T' else 'USDT_per_base' if x['name']=='selected_price' else 'none') for x in facts[0]['cells']])]
    for rule in c['rules']:
        if rule['kind']=='valuation':rule['parameters']['max_age_us']=120
    c['mark_clocks']=[dict(instrument_id=inst,clock_id='mark-clock',valuation_rule_id=b.rid('valuation',inst),multiplier_rule_id=b.rid('multiplier',inst),source_delay_us=60,max_source_age_us=120,max_available_age_us=60)]
    c['mark_view_bindings']=[dict(instrument_id=inst,clock_id='mark-clock')]
    c['mark_requirements']=[dict(key=dict(instrument_id=inst,clock_id='mark-clock',query_at_us=B+q,purpose=p),before_slots=[],for_view=True) for q in qs for p in ('valuation','reservation')]
    entry=50 if which==1 else 60
    defs=[port_definition('R0','environment',dict(mode='reserve',instrument=inst,id='initial-reserve')),port_definition('P','policy',dict(mode='policy',instrument=inst,expires=B+200)),port_definition('X','execution',dict(mode='execution',instrument=inst)),port_definition('R','environment',dict(mode='reserve',instrument=inst,id='held-reserve',margin='7' if which==1 else '0',fees='0.1' if which==1 else '0',mark_fees=which==1))]
    defs[2]['ledger_selectors']=[dict(selection_id='orders',instruments=[inst],kind='orders_active_and_changed')]
    defs[2]['ledger_selectors'].append(dict(selection_id='marks',instruments=[inst],kind='mark_context'))
    defs.append(port_definition('V','environment',dict(mode='mark_from_context',instrument=inst),[dict(selection_id='marks',instruments=[inst],kind='mark_context')]))
    schedule=[tick(B-20,'R0'),tick(B+entry,'V','P'),tick(B+entry+1,'X','V','R')]
    if which==2:
        defs.append(port_definition('BAD','environment',dict(mode='backdated_valuation',instrument=inst)));schedule.append(tick(1126,'BAD'))
    return install_ports(c,defs,schedule),facts


class ControllerDevelopment(unittest.TestCase):
    def setUp(self):unit_root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');unit_root.mkdir(parents=True,exist_ok=True);self.tmp=SimpleNamespace(name=tempfile.mkdtemp(dir=unit_root));self.root=Path(self.tmp.name).resolve()
    def make(self,c,facts=()):
        f=Fixture(self.root/'fixture',c=c,facts=facts);self.addCleanup(f.close);return f
    def test_partial_cancel_peer_state_restart(self):
        f=self.make(controlled_config());f.advance(10,[]);cp=f.checkpoint();f.restore(cp);f.advance(20,[])
        orders=f.page(20,'orders',2);self.assertEqual((orders[0]['filled_contracts'],orders[0]['remaining_contracts'],orders[0]['status']),(1,2,'cancelled'))
        self.assertEqual(len(f.page(20,'lots',2)),1)
    def test_qg01_selective_reserve_mask(self):
        c,facts=qg_config(1);f=self.make(c,facts);f.advance(1051,[]);x=f.balance(1051,3)
        self.assertEqual((x['cash_usdt'],x['unrealized_usdt'],x['reserved_margin_usdt'],x['reserved_fees_usdt'],x['simulated_budget_usdt']),('1000','0','7','0.1','992.9'))
        old=f.view(1051,3);f.advance(1065,[]);x=f.balance(1065)
        self.assertEqual((x['reserved_margin_usdt'],x['reserved_fees_usdt'],x['unrealized_usdt'],x['economic_equity_usdt'],x['simulated_budget_usdt']),('7',None,None,None,None))
        cp=f.checkpoint();f.restore(cp);self.assertEqual(f.view(1051,3),old);self.assertEqual(f.balance(1065),x)
    def test_qg02_recovery_uses_new_query_not_largest_old_source(self):
        c,facts=qg_config(2);f=self.make(c,facts);f.advance(1121,[]);old=f.view(1121);self.assertFalse(old['balance']['new_risk_supported']);cp=f.checkpoint();f.restore(cp);f.advance(1125,[])
        x=f.balance(1125);self.assertEqual((x['unrealized_usdt'],x['economic_equity_usdt'],x['simulated_budget_usdt']),('-1','999','999'));self.assertEqual(f.view(1121),old)
    def test_second_asset_sees_global_remaining_budget(self):
        c=primitive_config(instruments=(BTC,ETH));c['initial_cash_usdt']='10000';defs=[port_definition('B0','environment',dict(mode='reserve',instrument=BTC,id='B0')),port_definition('E0','environment',dict(mode='reserve',instrument=ETH,id='E0')),port_definition('B','policy',dict(mode='shared_budget',instrument=BTC,id='B',want='8000')),port_definition('E','policy',dict(mode='shared_budget',instrument=ETH,id='E',want='8000'))]
        install_ports(c,defs,[tick(0,'B0','E0'),tick(10,'B','E')]);f=self.make(c);f.advance(10,[])
        states={s['adapter_id']:s for s in f.page(10,'adapter_states',2)};self.assertEqual(states['B']['value']['spent'],'8000');self.assertEqual(states['E']['value']['spent'],'0');self.assertEqual(f.balance(10,2)['simulated_budget_usdt'],'2000')


def compare_reference(f,records,t,fee='0.0005',instruments=(BTC,),calendar=None,tie='snapshot_before_fills'):
    c,rs=b.bind(records,fee=fee,instruments=instruments,calendar=calendar,tie=tie)
    c['initial_cash_usdt']=f.config['initial_cash_usdt'];c['allocation_quantum_usdt']=f.config['allocation_quantum_usdt'];c['rules']=deepcopy(f.config['rules'])
    for rule in c['rules']:
        if rule['kind']=='multiplier':rule['parameters']['base_per_contract']=next(x['parameters']['base_per_contract'] for x in f.config['rules'] if x['rule_id']==rule['rule_id'])
    ref=b.el.Ledger(c);ref.apply_batch(rs);expected=ref.snapshot(t);actual=f.balance(t)
    assert {k:v for k,v in actual.items() if k not in ('mark_query_refs','mark_query_qualification')}==expected['balances'],(actual,expected['balances'])
    assert sorted(f.page(t,'closed_slices'),key=lambda v:v['slice_id'])==sorted(expected['closed_slices'],key=lambda v:v['slice_id'])
    lots=f.page(t,'lots');links=f.page(t,'links')
    for lot in lots:
        lot['closed_slice_ids']=[x['value']['id'] for x in links if x['owner_kind']=='lot' and x['owner_id']==lot['lot_id'] and x['value']['kind']=='slice'];lot.pop('closed_slice_count');lot.pop('closed_slices_root')
    assert sorted(lots,key=lambda x:x['lot_id'])==sorted(expected['lots'],key=lambda x:x['lot_id'])
    obligations=f.page(t,'obligations')
    for o in obligations:
        own=[x for x in links if x['owner_kind']=='obligation' and x['owner_id']==o['obligation_id']]
        o['allocation_refs']=sorted(x['value']['id'] for x in own if x['value']['kind']=='allocation');o['posting_refs']=sorted([x['value']['key'] for x in own if x['value']['kind']=='posting'],key=sl.canonical_bytes)
        for key in ('allocation_ref_count','allocation_refs_root','posting_ref_count','posting_refs_root'):o.pop(key)
    assert sorted(obligations,key=lambda x:x['obligation_id'])==sorted(expected['obligations'],key=lambda x:x['obligation_id'])
    assert sorted(f.page(t,'entries'),key=lambda x:x['entry_id'])==sorted(ref.audit()['committed_state']['derived_entries'],key=lambda x:x['entry_id']) if t==max(r['available_at_us'] for r in records) else True


def case_tape(id,variant=0):
    if id=='S01.01':return [b.reserves(),b.fill(at=10),b.fill('close',20,-10,'50100')],{}
    if id=='S01.02':
        r=b.fill(at=10,fee='-0.0001');r['liquidity_role']='maker';c=config([r],fee='-0.0001',cash='1000')
        for rule in c['rules']:
            if rule['kind']=='fee':rule['parameters']['role']='maker'
        return [r],dict(c=c)
    if id=='S01.04':return [b.reserves(),b.fill(at=10),b.snapshot(at=11),b.revision(at=11,economic=11),b.fill('c1',20,-6,'50100'),b.fill('c2',21,-4,'50100')],{}
    if id=='S01.06':
        r=b.fill(at=7,available=9);s=b.snapshot(at=8);rs=([r,s] if variant==0 else [s,r] if variant==1 else [r]);cal=[dict(instrument_id=BTC,event_id='fund',snapshot_at_us=8,mapping_rule_id=b.rid('funding'))]
        return rs,dict(c=config(rs,calendar=cal))
    if id in ('S01.07','S01.08'):
        r=b.revision(at=100,economic=80);r['calculation']=dict(kind='funding_formula',signed_contracts=10,multiplier='0.001',mark_price='50000',final_rate='0.0001',valuation_at_us=79,valuation_available_at_us=90 if id=='S01.07' else 79,rate_available_at_us=95,valuation_rule_id=b.rid('valuation'),multiplier_rule_id=b.rid('multiplier'))
        return [b.fill(at=10),b.snapshot(at=80),r],{}
    if id=='S01.10':
        rs=[one_fill('f1',10,inst=BTC),one_fill('f1' if variant==0 else 'f2',10,inst=ETH),zero_reserve(BTC,0,'800'),zero_reserve(ETH)]
        return rs,dict(c=primitive_config(rs,(BTC,ETH)))
    if id=='S01.11':return [b.fill(),b.snapshot(at=8),b.posting(amount='-0.02',at=10),b.revision(at=20,economic=8)],{}
    if id=='S05.03':
        rs=[one_fill('f1',20),one_fill('f2',20)];return rs,dict(c=primitive_config(rs))
    if id=='S06.03':
        rs=[one_fill('open',10),b.posting('wrong','fee:open','-0.1',20,b.unit('open',0,1),ETH)];return rs,dict(c=primitive_config(rs,(BTC,ETH)))
    if id in ('S06.04','S06.05','S06.06','S06.07'):
        f=b.fill();r=b.revision('fee:open','open','-0.1',20,1,2,'fee')
        if id=='S06.04':r['allocations'][0]['episode_id']='episode:other'
        if id=='S06.05':r.update(revision=3,supersedes_revision=2)
        if id in ('S06.06','S06.07'):
            r=b.posting('bad','fee:open','-0.1',20)
            if id=='S06.06':r['corrects_posting_id']='bad';r['null_reasons']={}
            else:r['revision']=1
        return [f,r],{}
    if id=='S10.01':
        rs=[b.fill(),b.posting('late','fee:open','-0.1',10)];rs[1]['available_at_us']=20;rs[1]['booking_known_at_us']=20;return rs,{}
    if id=='S10.02':
        rs=[one_fill(),b.snapshot('due',11,[b.unit('open',0,1)])];rs[1]['available_at_us']=20
        return rs,dict(c=primitive_config(rs))
    if id in ('S10.04','S10.05','S10.06','S10.07'):
        rs=[zero_reserve(expires=11 if id=='S10.05' else 10000),one_fill(),b.mark('mark',10,'100')];c=primitive_config(rs)
        for rule in c['rules']:
            if rule['kind']=='valuation':rule['parameters']['max_age_us']=1
        return rs,dict(c=c)
    return basic_tape(),{}


# A case is left NOT_EXECUTED when its complete frozen tape/assertion set has
# not been implemented. It is never replaced with a different easy test.
UNIMPLEMENTED={
 'S01.03':'four-snapshot long/short formula tape not yet constructed',
 'S01.05':'reversal split and retained old funding oracle not yet constructed',
 'S01.09':'complete/stale/successor readiness tape not yet constructed',
 'S01.12':'three-episode B1 partial restoration tape not yet constructed',
 'S02.04':'explicit staged peer-state predecessor tape not yet constructed',
 'S02.05':'cutoff lifecycle/tail order fixture not yet constructed',
 'S03.01':'full controller future-only mutation oracle not yet constructed',
 'S03.02':'equal-source two-store registry byte oracle not yet constructed',
 'S03.03':'context original-clock fixture not yet constructed',
 'S03.04':'unresolved context required-row fixture not yet constructed',
 'S03.05':'altered original-clock context packet fixture not yet constructed',
 'S03.06':'two explicit context restart positions not yet constructed',
 'S03.07':'context future-only rehash fixture not yet constructed',
 'S04.01':'future forged packet injection fixture not yet constructed',
 'S04.02':'external q2 versus independently emitted q1 witness not yet constructed',
 'S04.03':'rehash omitted live-range input injection not yet constructed',
 'S04.04':'substituted older order-status input injection not yet constructed',
 'S04.05':'peer-state/own-read omission injection not yet constructed',
 'S04.08':'unsupported unknown-to-zero output binding fixture not yet constructed',
 'S05.02':'both same-time snapshot-before/fill-before full tapes not yet constructed',
 'S07.02':'512-body many-live-lot/unpaid-claim tape not yet constructed',
 'S07.03':'128-body B1 fold-labelled closed-episode tape not yet constructed',
 'S08.08':'forged projected cash/omitted owner checkpoint export not implemented',
 'S08.10':'failed stop publication and saved-input revalidation not implemented',
 'S08.11':'fixed interrupted suffix plus corrupt CONTROL replicas not implemented',
 'S09.06':'checkpoint context/adapter cursor exact validation incomplete',
 'S09.07':'backdated context re-admission transport not yet constructed',
 'S10.03':'stale assertion successor complete-time fixture not yet constructed',
 'S11.07':'8193-bit derived integer reachable fixture not constructed; no false direct-internal substitute',
 'S12.07':'interrupted conservative work-debit harness not implemented',
}


def run_case(id,parent,variant=0):
    if id in UNIMPLEMENTED:return dict(status='NOT_EXECUTED',reason=UNIMPLEMENTED[id],fixtures=0)
    parent=Path(parent);f=None;calls=0;checks=[]
    def make(records=None,c=None,facts=None):
        nonlocal f,calls
        records=basic_tape() if records is None and c is None and facts is None else records or ()
        if c is None:c=config(records,cash='1000')
        f=Fixture(parent/('fixture'+str(calls)),records,c,facts);calls+=1;return f
    def must(value,label):assert value,label;checks.append(label)
    try:
        if id in ('S02.01','S02.02','S02.03'):
            f=make(c=controlled_config(),facts=[])
            if id!='S02.01':
                t=10 if id=='S02.02' else 20;f.advance(t,[]);cp=f.checkpoint();f.restore(cp)
            f.advance(40,[]);x=f.balance(40,1);must((x['cash_usdt'],x['liabilities_usdt'],x['simulated_budget_usdt'])==('1001','0.2','1000.8'),'single account C/L/budget before posting')
            f.advance(50,[]);x=f.balance(50,1);must((x['cash_usdt'],x['liabilities_usdt'])==('1000.8','0'),'explicit posting once')
            must(len(f.page(20,'lots',2))==1,'actual partial unit range persisted')
        elif id in ('S04.06','S04.07'):
            c=primitive_config();mode=('forbidden_file','forbidden_entropy','forbidden_global')[variant] if id=='S04.07' else 'noop'
            d=port_definition('P','policy',dict(mode=mode))
            if id=='S04.06':
                c['fact_schemas']=[dict(schema_id='open',kind='price',view_kind='execution_open',interval_us=1,fields=[])]
                d['fact_selectors']=[dict(selection_id='bad',schema_id='open',instruments=[BTC],mode='available_prefix')]
            install_ports(c,[d],[tick(10,'P')]);f=make(c=c,facts=[]);before=f.ledger.head.copy();expect('UNSUPPORTED_RANDOMNESS' if mode=='forbidden_entropy' else 'FORBIDDEN_INPUT',lambda:f.advance(10,[]));must(f.ledger.head==before,'no prefix mutation')
        elif id=='S05.01':
            c=controlled_config();f=make(c=c,facts=[])
            for t in ((50,) if variant==0 else (10,20,30,40,50)):f.advance(t,[])
            must((f.balance(50,1)['cash_usdt'],f.balance(50,1)['liabilities_usdt'])==('1000.8','0'),'complete-tick partitions literal finance')
            must(len(f.page(50,'registry',1))==7,'all due slots invoked including noops')
        elif id in ('S05.04','S05.05'):
            rs=[b.fill(),b.revision('fee:open','open','-0.1',30,1,2,'fee')];f=make(rs)
            f.advance(20,[0]);old=f.view(20)
            if id=='S05.04' and variant==0:
                request=f.request_at(30,[1]);request['imported'][0]['body']['available_at_us']=19;request['imported'][0]['body']['known_at_us']=19
                # Pin the alternative valid source before create instead of
                # forging source truth solely to exercise the sealed interval.
                f.close();raise unittest.SkipTest('source-bound backdated variant not yet constructed')
            else:
                f.advance(30,[0] if id=='S05.04' else [1]);must(f.view(20)==old,'old as-known unchanged')
        elif id in ('S06.01','S06.02'):
            f=make();request=f.request_at(10);first=f.ledger.advance(request)
            if id=='S06.02':
                bad=deepcopy(request);bad['through_us']=11;expect('REQUEST_CONFLICT',lambda:f.ledger.advance(bad));must(f.ledger.head==first['after'],'conflict atomic')
            else:
                must(f.ledger.advance(request)['status']=='replayed','saved receipt redelivery1');cp=f.checkpoint();f.restore(cp);must(f.ledger.advance(request)['status']=='replayed','saved receipt redelivery2');f.advance(11);must(f.balance(11)['cash_usdt']=='1001.45','outer request/business dedup redelivery3')
        elif id=='S07.01' or id=='S12.06':
            rs=benchmark_tape(8192);c=primitive_config(rs,tie='fills_before_snapshot');c['end_exclusive_us']=20000;c['knowledge_end_exclusive_us']=21000
            if id=='S12.06':c['limits']['max_resident_cache_bytes']=65536 if variant==0 else 8*1024**2
            f=make(rs,c=c);old=None
            for start in range(0,len(rs),128):
                end=min(start+128,len(rs));f.advance(max(r['available_at_us'] for r in rs[start:end]),range(start,end))
                if end==4096:
                    old=f.view(10);cp=f.checkpoint();f.restore(cp)
            x=f.balance(rs[-1]['available_at_us']);must(x['cash_usdt']=='1920.75','8192 bodies exact literal final C')
            must(f.view(10)==old,'ancient version immutable after correction/checkpoint')
            must(f.page(rs[-1]['available_at_us'],'closed_slices')[0] is not None,'paged retained slices')
        elif id.startswith('S08.'):
            rs=[one_fill()];f=make(rs,c=primitive_config(rs));request=f.request_at(10);before=f.ledger.head.copy();original=sl._atomic
            stage={'S08.01':'guard-input','S08.02':'journal-','S08.03':'HEAD','S08.04':'after-head','S08.05':'after-head','S08.06':'after-head','S08.07':'after-head'}.get(id)
            if id=='S08.09':
                cp=f.checkpoint();bad=f.request_at(10);bad['imported']*=4097
                if variant==0:bad['imported'][0]['body']['fill_price']='bad';bad['imported']=bad['imported'][:1]
                expect('INVALID_DECIMAL' if variant==0 else 'RESOURCE_EXHAUSTED',lambda:f.ledger.advance(bad));status=f.ledger.current_head()['status'];f.restore(cp);must(f.ledger.current_head()['status']==status,'old checkpoint cannot clear durable stop')
            else:
                def injected(path,value):
                    name=Path(path).name
                    if stage=='after-head' and name=='HEAD':original(path,value);raise OSError('injected after HEAD')
                    if stage!='after-head' and name.startswith(stage):raise OSError('injected before publication')
                    return original(path,value)
                with patch.object(sl,'_atomic',injected):expect('COMMIT_OUTCOME_UNKNOWN',lambda:f.ledger.advance(request))
                if id=='S08.01':must(f.ledger.head==before and f.ledger.current_head()['status']=='COMMIT_UNKNOWN','guard durability failure unusable')
                else:
                    resolution=dict(request_id=request['request_id'],request_sha256=sl.digest(request))
                    if id=='S08.07':resolution['request_sha256']='f'*64;expect('REQUEST_CONFLICT',lambda:f.ledger.resolve_commit(resolution))
                    elif id=='S08.05':
                        for _ in range(2):
                            with patch.object(sl,'_fsync_directory',side_effect=OSError('barrier failed')):must(f.ledger.resolve_commit(resolution)['outcome']=='unknown','readable HEAD still unknown')
                    else:
                        outcome='committed' if stage=='after-head' else 'not_committed';must(f.ledger.resolve_commit(resolution)['outcome']==outcome,'barrier/reachable outcome')
                        if id=='S08.06':must(f.ledger.resolve_commit(resolution)['outcome']=='committed','same one commit twice')
        elif id.startswith('S09.'):
            f=make();f.advance(10);cp=f.checkpoint()
            if id=='S09.01':
                cp['profile']='qf009-offline-stream-r1' if variant==0 else sl.PROFILE;cp['schema_version']=3 if variant==0 else 4;expect('UNSUPPORTED_VERSION',lambda:f.restore(cp))
            elif id=='S09.02':
                cp['raw_catalogue_sha256' if variant==0 else 'adapters_sha256']='f'*64;cp['checkpoint_sha256']=sl.digest({k:v for k,v in cp.items() if k!='checkpoint_sha256'});expect('CHECKPOINT_MISMATCH',lambda:f.restore(cp))
            elif id=='S09.03':
                target=f.path/'store'/cp['files'][0]['relative_path']
                if variant==0:target.rename(target.with_suffix('.saved'))
                else:
                    external=f.path/'external';external.write_bytes(target.read_bytes());target.rename(target.with_suffix('.saved'));target.symlink_to(external)
                # Keep the object missing without destroying evidence. Constructor
                # or restore must reject; close safely without reopening for fixture.
                head=f.ledger.head['audit_prefix'];f.close();expect('STORE_INTEGRITY_FAILURE' if variant==0 else 'SCHEMA_VIOLATION',lambda:sl.restore(dict(checkpoint=cp,expected_committed_head=head,store_root=str(f.path/'store'))))
            elif id=='S09.04':
                bad=deepcopy(cp);bad['files'][0]['relative_path']='../escape';bad['checkpoint_sha256']=sl.digest({k:v for k,v in bad.items() if k!='checkpoint_sha256'});expect('SCHEMA_VIOLATION',lambda:f.restore(bad))
            elif id=='S09.05':f.advance(20,[]);head=f.ledger.head.copy();must(f.restore(cp)==head,'known suffix retained, no rollback')
        elif id in ('S10.08','S10.09'):
            which=1 if id=='S10.08' else 2;c,facts=qg_config(which);f=make(c=c,facts=facts);entry=1051 if which==1 else 1061;bad=1065 if which==1 else 1121
            f.advance(entry,[]);old=f.view(entry,3);f.advance(bad,[]);x=f.balance(bad);must(x['unrealized_usdt'] is None and x['simulated_budget_usdt'] is None,'UNKNOWN held U/E/budget')
            if which==1:must((x['reserved_margin_usdt'],x['reserved_fees_usdt'])==('7',None),'selective reserve mask')
            cp=f.checkpoint();f.restore(cp);must(f.view(entry,3)==old,'original q immutable across restart')
            if which==2:
                f.advance(1125,[]);x=f.balance(1125);must((x['unrealized_usdt'],x['economic_equity_usdt'],x['simulated_budget_usdt'])==('-1','999','999'),'new query recovery')
                before=f.ledger.head.copy();expect('PAST_AVAILABILITY',lambda:f.advance(1126,[]));must(f.ledger.head==before,'backdated controlled Valuation leaves committed prefix unchanged')
        elif id.startswith('S11.'):
            if id in ('S11.01','S11.02','S11.06'):
                f=make([],c=primitive_config())
                if id=='S11.01':must(sl.fmt(Fraction('9007199254740993'))=='9007199254740993' and sl.fmt(Fraction('1234567890123456789012345678901'))=='1234567890123456789012345678901','exact >53bit and31digits');must(sl.allocate(Fraction('0.01'),[1,1,1],Fraction('0.0001'))==['0.0033','0.0033','0.0034'],'exact rational residual')
                elif id=='S11.02':
                    from decimal import localcontext
                    with localcontext() as ctx:
                        ctx.prec=6 if variant==0 else 50;must(sl.allocate(Fraction('-0.1'),[1,2],Fraction('0.01'))==['-0.03','-0.07'],'ambient Decimal independent')
                else:expect('NONTERMINATING_AMOUNT',lambda:sl.fmt(Fraction(1,3)))
            elif id=='S11.09':
                rs=[b.fill(),b.snapshot()];f=make(rs);r=f.request_at(10)
                if variant==0:r['imported'][1]['body'].update(source_t_seconds=1,source_record_at_us=1000001);r['imported'][1]['body']['null_reasons']={'snapshot_sequence':'UNKNOWN_SEQUENCE'};expect('CLOCK_CONTRADICTION',lambda:f.ledger.advance(r))
                elif variant==1:
                    # Named mapping mismatch must be source-bound to reach the
                    # semantic guard; do not count a source-forgery rejection.
                    raise unittest.SkipTest('source-bound wrong mapping fixture not constructed')
                else:
                    raise unittest.SkipTest('source-bound unknown mapping fixture not constructed')
            else:
                f=make([one_fill()],c=primitive_config([one_fill()]));r=f.request_at(10);v=r['imported'][0]['body']
                if id=='S11.03':v['fill_price']=100.0;code='INVALID_DECIMAL'
                elif id=='S11.04':v['signed_contracts']=True if variant==0 else '0.5';code='INTEGER_CONTRACT_VIOLATION'
                elif id=='S11.05':v['fill_price']='1%' if variant==0 else '1e2';code='INVALID_DECIMAL'
                else:
                    if variant==0:v['fill_price']='-1';code='DECIMAL_DOMAIN'
                    else:
                        v=r['imported'][0]['body']=body(b.mark());v['price_kind']='TRADE';code='WRONG_PRICE_KIND'
                expect(code,lambda:f.ledger.advance(r));checks.append('exact named scalar rejection')
        elif id.startswith('S12.'):
            if id=='S12.01':
                f=make([one_fill()],c=primitive_config([one_fill()]));r=f.request_at(10);r['imported']*=4097;expect('RESOURCE_EXHAUSTED',lambda:f.ledger.advance(r))
            elif id=='S12.02':raise unittest.SkipTest('full 32MiB/262144-read source fixture not yet constructed')
            elif id=='S12.03':
                c=primitive_config();d=port_definition('E','environment',dict(mode='oversized_state' if variant==0 else 'oversized_output'));install_ports(c,[d],[tick(10,'E')]);f=make(c=c,facts=[]);expect('RESOURCE_EXHAUSTED',lambda:f.advance(10,[]))
            elif id=='S12.04':
                c=primitive_config();c['limits']['max_store_bytes' if variant==0 else 'max_wall_us']=1;f=make([one_fill()],c=c);expect('RESOURCE_EXHAUSTED',lambda:f.advance(10));f.reopen();must(f.ledger.current_head()['status']=='RESOURCE_STOPPED','resource stop survives restart')
            elif id=='S12.05':
                f=make();f.advance(10);view=f.view(10);r=dict(view_sha256=view['view_sha256'],component='events',filter=dict(kind='all'),after=None,limit=257,null_reasons={'after':'START_OF_COMPONENT'});expect('RESOURCE_EXHAUSTED_READ',lambda:f.ledger.scan(r));f.ledger.config['limits']['max_page_bytes']=1;r['limit']=1;expect('RESOURCE_EXHAUSTED_READ',lambda:f.ledger.scan(r));must(f.ledger.current_head()['status']=='ACTIVE','read limits never latch finance')
        else:
            records,kw=case_tape(id,variant);f=make(records,**kw);end=max(r['available_at_us'] for r in records)
            rejects={'S01.06':'LATE_ORIGIN_UNSUPPORTED','S01.07':'FUTURE_PROXY_MARK','S05.03':'AMBIGUOUS_FILL_SEQUENCE','S06.03':'REFERENCE_SCOPE_MISMATCH','S06.04':'ALLOCATION_MISMATCH','S06.05':'REVISION_GAP','S06.06':'DEPENDENCY_CYCLE','S06.07':'UNSUPPORTED_POSTING_RESTATEMENT'}
            if id=='S01.10' and variant==0:rejects[id]='ID_SCOPE_CONFLICT'
            if id in rejects:
                before=f.ledger.head.copy();request=f.request_at(end)
                if id=='S06.07':request['imported'][-1]['body']['revision']=2
                expect(rejects[id],lambda:f.ledger.advance(request));must(f.ledger.head==before,'semantic failure atomic')
            else:
                f.advance(max(20,end));x=f.balance(max(20,end))
                if id in ('S01.01','S01.04','S01.08','S01.11'):compare_reference(f,records,max(20,end));checks.append('exact r3 expanded financial values')
                if id=='S01.01':must(x['cash_usdt']=='1002' and x['liabilities_usdt']=='0.5','literal gross/fee claims')
                elif id=='S01.02':must(x['receivables_usdt']=='0.0499','signed maker rebate')
                elif id=='S01.04':
                    slices=sorted(f.page(21,'closed_slices'),key=lambda s:s['closed_at_us']);must([sl.fmt(sum(Fraction(s[k]) for k in ('realized_price_pnl_usdt','entry_fee_cash_usdt','exit_fee_cash_usdt','funding_cash_usdt'))) for s in slices]==['0.87','0.58'],'exact partial .87/.58')
                elif id=='S01.10':
                    must(x['cash_usdt']=='1000' and x['simulated_budget_usdt'] is None,'single cash, held no mark unknown budget')
                elif id=='S01.11':must((x['cash_usdt'],x['liabilities_usdt'])==('999.98','0.2795'),'posting unknown T preserves cash; aggregate fee plusfunding L')
                elif id=='S10.01':
                    old=f.balance(10);rest=f.ledger.restated(dict(economic_at_us=10,knowledge_cutoff=dict(at_us=20,slot=0)));must(old['cash_usdt']=='1000' and rest['balance']['cash_usdt']=='999.9' and rest['balance']['simulated_budget_usdt'] is None,'as-known versus restated booking')
                elif id=='S10.02':must(f.balance(11)['receivables_usdt'] is None and f.balance(20)['receivables_usdt'] is None,'coverage/unknown total not zero')
                elif id=='S10.04':must(f.balance(11)['unrealized_usdt']=='0' and f.balance(12)['unrealized_usdt'] is None,'MARK equality then +1 stale')
                elif id=='S10.05':must(f.balance(10)['reserved_margin_usdt']=='0' and f.balance(11)['reserved_margin_usdt'] is None,'reserve expiry equality')
                elif id=='S10.06':
                    # Current commit already sealed20: this checks actual
                    # non-tick view clock, not the complete requested11 tape.
                    raise unittest.SkipTest('non-tick view executed; exact through11/backdated11 tape incomplete')
                elif id=='S10.07':
                    v10=f.view(10);v20=f.view(20);p=f.ledger.scan(dict(view_sha256=v20['view_sha256'],component='events',filter=dict(kind='all'),after=None,limit=1,null_reasons={'after':'START_OF_COMPONENT'}));expect('SCHEMA_VIOLATION',lambda:f.ledger.scan(dict(view_sha256=v10['view_sha256'],component='events',filter=dict(kind='all'),after=p['next'],limit=1,null_reasons={})));checks.append('hash/handle/token view binding')
        metrics=dict(bodies=len(f.records),stored_events=f.ledger.index.count('events',f.ledger.state.root('events')),slots=f.ledger.index.count('registry',f.ledger.state.root('registry')),node_visits=f.ledger.index.visits,cache_bytes=f.ledger.index.size) if f and not f.ledger._closed else {}
        return dict(status='PASS',fixtures=calls,checks=checks,metrics=metrics)
    except unittest.SkipTest as e:return dict(status='NOT_EXECUTED',fixtures=calls,partial_checks=checks,reason=str(e))
    finally:
        if f:f.close()


def source_plan(id,variant):
    if id in UNIMPLEMENTED:return dict(case_id=id,variant=variant,status='NOT_IMPLEMENTED',reason=UNIMPLEMENTED[id])
    if id in ('S02.01','S02.02','S02.03','S05.01'):return dict(case_id=id,variant=variant,config=controlled_config(),records=[],facts=[])
    if id in ('S10.08','S10.09'):
        c,facts=qg_config(1 if id=='S10.08' else 2);return dict(case_id=id,variant=variant,config=c,records=[],facts=facts)
    records,kw=case_tape(id,variant)
    return dict(case_id=id,variant=variant,records=[body(r) for r in records],config=kw['c'] if 'c' in kw else config(records,cash='1000'),construction='run_case closed source above; request mutations/checks frozen by test sha256')


def identities():
    root=Path(__file__).resolve().parents[1]
    files=('research/qd009/streaming_ledger.py','tests/test_qd_streaming_ledger.py','tests/test_qd_event_ledger.py','research/qd007/event_ledger.py','docs/interface-requests/qd-qf009-streaming-ledger.md')
    return dict(files=[dict(path=p,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in files],
                environment=dict(python=sys.version,executable=sys.executable,executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),platform=platform.platform(),sqlite=sl.sqlite3.sqlite_version,code_commit=os.environ.get('QD009_CODE_COMMIT','6c606b60c33b191ef3dec8193bd6ad67acee96b9')),
                schema_hashes=dict(input=sl.digest(INPUT_SCHEMA),output=sl.digest(OUTPUT_SCHEMA),state=sl.digest(STATE_SCHEMA),intent=sl.digest(INTENT_SCHEMA)))


def freeze(directory):
    """Freeze immutable synthetic source bytes, code and environment, no ledger run."""
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False);inventory=[]
    for id in CASE_IDS:
        for variant in range(REPLICAS.get(id,1)):
            p=directory/f'{id}-{variant}.plan.json';dump(p,source_plan(id,variant));inventory.append(dict(relative_path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
    bench={}
    for n in (512,2048,8192,32768):
        source=directory/f'input-{n}';source.mkdir();records=benchmark_tape(n);raw=jsonl(source/'raw.jsonl',(body(r) for r in records))
        rows=(dict(fact_key=f'fact:{i:08}',instrument_id=r['instrument_id'],body=body(r),scenario_available_at_us=r['available_at_us'],raw_refs=[dict(object_id='synthetic',raw_sha256=raw['sha256'],source_row=i+1)]) for i,r in enumerate(records))
        ref=dict(root_id='source',**jsonl(source/'facts.jsonl',rows));c=primitive_config(records,tie='fills_before_snapshot');c['end_exclusive_us']=20000;c['knowledge_end_exclusive_us']=21000
        obj=dict(object_id='synthetic',root_id='source',instrument_id=BTC,sha256=raw['sha256'],bytes=raw['bytes'],relative_path=raw['relative_path'],format='synthetic_jsonl',source_row_basis='physical_line',original_time_unit='microseconds',retrieved_at_us=None,null_reasons={'retrieved_at_us':'UNKNOWN_RETRIEVAL'})
        request=dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,request_id='create',config=c,raw_catalogue=dict(namespace='qf009.raw-catalogue',schema_version=1,catalogue_id='fixture',objects=[obj],fact_store=ref,qualification_ref='0'*64),fact_store=ref,source_roots=[dict(root_id='source',path=str(source))],store_root='REPLACED_PER_ATTEMPT')
        dump(source/'create.json',request);bench[str(n)]=dict(create_sha256=hashlib.sha256((source/'create.json').read_bytes()).hexdigest(),facts=ref,raw=raw,
             expected_cash={512:'1056.75',2048:'1229.55',8192:'1920.75',32768:'4685.55'}[n],body_count=n,cycles=n//8-1)
        del records
    manifest=dict(identities=identities(),case_ids=CASE_IDS,replicas=REPLICAS,expected_cases=90,expected_fixtures=118,plans=inventory,benchmarks=bench,
                  functional_attempts=1,functional_seconds=120,benchmark_attempts=8,benchmark_seconds_each=60,
                  caveat='Candidate construction is incomplete for NOT_IMPLEMENTED cases. Plans freeze source templates and constructor code, not a claim that all118 exact fixture bytes/expected tables exist.')
    dump(directory/'freeze.json',manifest);return manifest


def verify_freeze(directory):
    manifest=sl.load_json((Path(directory)/'freeze.json').read_bytes());assert manifest['identities']==identities(),'code/environment changed after freeze'
    for p in manifest['plans']:assert hashlib.sha256((Path(directory)/p['relative_path']).read_bytes()).hexdigest()==p['sha256'],'frozen plan changed'
    return manifest


def rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform=='darwin' else value*1024


def bytes_under(path):return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file())


def functional(directory):
    import signal
    directory=Path(directory).resolve();manifest=verify_freeze(directory);out=directory/'functional';out.mkdir(exist_ok=False);start=time.monotonic()
    results=[];executed_fixtures=0;timed_out=False
    def timeout(*_):raise TimeoutError('functional120s budget exhausted')
    old=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
    try:
        for id in CASE_IDS:
            variants=[]
            for v in range(REPLICAS.get(id,1)):
                casepath=out/f'{id}-{v}';case_start=time.monotonic()
                if timed_out:
                    row=dict(status='NOT_EXECUTED',reason='one functional budget exhausted',fixtures=0)
                else:
                    try:
                        row=run_case(id,casepath,v)
                    except TimeoutError:
                        timed_out=True;row=dict(status='FAIL',reason='TIME_BUDGET',fixtures=len(list(casepath.glob('fixture*'))))
                    except Exception as e:
                        row=dict(status='FAIL',reason=str(e),exception=type(e).__name__,traceback=traceback.format_exc()[-4000:],fixtures=len(list(casepath.glob('fixture*'))))
                row.update(case_id=id,variant=v,wall_us=int((time.monotonic()-case_start)*1e6));executed_fixtures+=row['fixtures'];variants.append(row)
                with (out/'replicas.jsonl').open('ab') as log:log.write(sl.canonical_bytes(row)+b'\n');log.flush();os.fsync(log.fileno())
                if not timed_out and (rss_bytes()>256*1024**2 or bytes_under(out)>128*1024**2):timed_out=True
            status='FAIL' if any(x['status']=='FAIL' for x in variants) else 'NOT_EXECUTED' if any(x['status']=='NOT_EXECUTED' for x in variants) else 'PASS'
            results.append(dict(case_id=id,status=status,variants=variants))
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
    totals={status:sum(r['status']==status for r in results) for status in ('PASS','FAIL','NOT_EXECUTED')}
    result=dict(kind='producer-functional',status='PASS' if totals=={'PASS':90,'FAIL':0,'NOT_EXECUTED':0} and executed_fixtures==118 else 'FAIL',
       totals=totals,expected_cases=90,expected_fixtures=118,actual_created_fixtures=executed_fixtures,wall_us=int((time.monotonic()-start)*1e6),peak_rss_bytes=rss_bytes(),output_bytes=bytes_under(out),
       results=results,S13='NOT_EXECUTED/BLOCKED_NATIVE_PORT/R3_NOT_READY',identities=manifest['identities'])
    dump(out/'result.json',result);return result


def benchmark(directory,n,rep):
    import signal
    directory=Path(directory).resolve();manifest=verify_freeze(directory);assert n in (512,2048,8192,32768) and rep in (1,2)
    out=directory/f'benchmark-{n}-{rep}';out.mkdir(exist_ok=False);dump(out/'started.json',dict(n=n,rep=rep,identity=sl.digest(manifest['identities'])))
    start=time.monotonic();ledger=None;summary=dict(n=n,rep=rep,status='FAIL',accepted_bodies=0,attempt=rep,complete=False,checkpoints=0)
    def timeout(*_):raise TimeoutError('benchmark60s budget exhausted')
    old=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,60)
    try:
        request=sl.load_json((directory/f'input-{n}/create.json').read_bytes());request['store_root']=str(out/'store')
        assert hashlib.sha256((directory/f'input-{n}/create.json').read_bytes()).hexdigest()==manifest['benchmarks'][str(n)]['create_sha256']
        sl.create(request);ledger=sl.Ledger(out/'store');last=0;historical=None
        source=directory/f'input-{n}/facts.jsonl';batch=[]
        with source.open('rb') as rows:
            for raw in rows:
                fact=sl.load_json(raw);batch.append(dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,body=fact['body'],origin=dict(kind='reference_import',fact_key=fact['fact_key']),created_at_us=0))
                if len(batch)==256:
                    end=max(e['body']['available_at_us'] for e in batch);last+=len(batch)
                    ledger.advance(dict(request_id=f'batch:{last}',expected_audit_prefix=ledger.head['audit_prefix'],through_us=end,imported=batch,generated=[]));batch=[];summary['accepted_bodies']=last
                    if last==256:historical=ledger.as_known(dict(cutoff=dict(at_us=10,slot=0)))
                    if last%1024==0:
                        cp=ledger.checkpoint(dict(expected_head=ledger.head['audit_prefix']));dump(out/f'checkpoint-{last}.json',cp);summary['checkpoints']+=1
                    if rss_bytes()>256*1024**2:raise MemoryError('RSS256MiB exceeded')
                    if bytes_under(out)>512*1024**2:raise OSError('OUTPUT512MiB exceeded')
                    with (out/'progress.jsonl').open('ab') as trace:trace.write(sl.canonical_bytes(dict(accepted=last,node_visits=ledger.index.visits,node_writes=ledger.index.writes,resident_node_cache_bytes=ledger.index.size,wall_us=int((time.monotonic()-start)*1e6)))+b'\n')
            assert not batch,'fixed ladder divides256'
        view=ledger.as_known(dict(cutoff=ledger.head['cutoff']));assert view['balance']['cash_usdt']==manifest['benchmarks'][str(n)]['expected_cash'],view['balance']
        assert ledger.as_known(dict(cutoff=dict(at_us=10,slot=0)))==historical,'old as-known changed'
        oldlot=ledger.state.location('lots','lot:open:0');slices=list(ledger.state.rows('_slice_lot',prefix=['lot:open:0']));assert len(slices)==1
        slc=ledger.state.location('closed_slices',slices[0][1]);assert slc['entry_fee_cash_usdt']=='-0.05'
        summary.update(status='PASS',complete=True,cash_usdt=view['balance']['cash_usdt'],economic_state_sha256=view['economic_state_sha256'],event_count=ledger.index.count('events',ledger.state.root('events')),
                       closed_slice_count=ledger.index.count('closed_slices',ledger.state.root('closed_slices')),node_visits=ledger.index.visits,node_writes=ledger.index.writes,resident_node_cache_bytes=ledger.index.size)
    except (Exception,TimeoutError) as e:summary.update(error=type(e).__name__,reason=str(e),traceback=traceback.format_exc()[-3000:])
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        if ledger:
            try:ledger.close()
            except Exception as e:summary.update(status='FAIL',close_error=str(e))
    summary.update(wall_us=int((time.monotonic()-start)*1e6),peak_rss_bytes=rss_bytes(),output_bytes=bytes_under(out),canonical_journal_bytes=sum(p.stat().st_size for p in (out/'store').glob('journal-*.json')),
                   declared_n=n,fixture_sha256=manifest['benchmarks'][str(n)]['facts']['sha256'])
    if summary['wall_us']>60000000 or summary['peak_rss_bytes']>256*1024**2 or summary['output_bytes']>512*1024**2:summary['status']='FAIL'
    dump(out/'result.json',summary);return summary


def main():
    parser=argparse.ArgumentParser();sub=parser.add_mutually_exclusive_group();sub.add_argument('--freeze',metavar='DIR');sub.add_argument('--formal',metavar='DIR');sub.add_argument('--benchmark',nargs=3,metavar=('DIR','N','REP'))
    args,remaining=parser.parse_known_args()
    if args.freeze:
        m=freeze(args.freeze);print(json.dumps(dict(frozen=args.freeze,sha256=hashlib.sha256((Path(args.freeze)/'freeze.json').read_bytes()).hexdigest(),cases=len(m['case_ids']),replicas=sum(m['replicas'].get(k,1) for k in m['case_ids']))));return
    if args.formal:
        r=functional(args.formal);print(json.dumps({k:v for k,v in r.items() if k not in ('results','identities')}));raise SystemExit(r['status']!='PASS')
    if args.benchmark:
        directory,n,rep=args.benchmark;r=benchmark(directory,int(n),int(rep));print(json.dumps({k:v for k,v in r.items() if k!='traceback'}));raise SystemExit(r['status']!='PASS')
    unittest.main(argv=[sys.argv[0]]+remaining)




# Repair-r1 concrete fixtures. These are defined before CLI entry (moved below)
# and will be serialized in full before any new formal attempt.
def repair_b1(long_form=False):
    records=[zero_reserve()];affected=[]
    for j,start in enumerate((1,8,15)):
        op=f'b1-open:{j}';c1=f'b1-close:{j}:1';c2=f'b1-close:{j}:3'
        records.extend((one_fill(op,start,4),one_fill(c1,start+1,-1),one_fill(c2,start+2,-3)))
        targets=([('fee:'+op,op,start,b.unit(op,0,4,op))] if j==0 else [('fee:'+c1,c1,start+1,b.unit(op,0,1,op)),('fee:'+c2,c2,start+2,b.unit(op,1,4,op))])
        if j==2:targets.append(('fee:'+op,op,start,b.unit(op,0,4,op)))
        affected+=targets
    for oid,origin,econ,u in affected:
        records.extend((b.revision(oid,origin,'-0.25',18,econ,2,'fee',u),b.posting('initial:'+origin,oid,'-0.25',19,u),b.revision(oid,origin,None,20,econ,3,'fee',u)))
        if long_form:
            records.extend((b.revision(oid,origin,'-0.2',30,econ,4,'fee',u),b.posting('refund:'+origin,oid,'0.05',40,u)))
        else:
            records.extend((b.revision(oid,origin,'-0.25',21,econ,4,'fee',u),b.revision(oid,origin,'-0.2',22,econ,5,'fee',u),b.posting('refund:'+origin,oid,'0.05',23,u),b.revision(oid,origin,'-0.3',24,econ,6,'fee',u),b.posting('surcharge:'+origin,oid,'-0.1',25,u)))
    if long_form:
        for i in range(128-len(records)):records.append(b.mark(f'b1-corroborating:{i}',17,'100'))
    return records,primitive_config(records)


def repair_readiness():
    records=[zero_reserve(),one_fill('open',1,10),one_fill('close',9,-10)]
    a=b.assertion(10,payments=());a['scope']['event_kinds']=['fill','fee'];a['obligation_revision_refs']=[dict(obligation_id='fee:open',revision=1),dict(obligation_id='fee:close',revision=1)]
    rev=b.revision('fee:open','open','-0.1',20,1,2,'fee',b.unit('open',0,10));pay=b.posting('settle','fee:open','-0.1',21,b.unit('open',0,10))
    a2=deepcopy(a);a2.update(available_at_us=22,asserted_at_us=22,known_at_us=22,revision=2,supersedes_revision=1,null_reasons={});a2['scope']['event_kinds']=['fill','fee','posting'];a2['obligation_revision_refs'][0]['revision']=2;a2['posting_refs']=[dict(posting_id='settle',revision=1)]
    records.extend((a,rev,pay,a2));return records,primitive_config(records)


def repair_many_live():
    records=[one_fill(f'live:{i}',10+i,2) for i in range(128)]
    for i in range(128):records.append(b.snapshot(f'fund:{i}',10+i,[b.unit(f'live:{j}',0,2,'live:0') for j in range(i+1)]))
    for i in range(128):
        snap=records[128+i];rev=b.revision('ob:fund:'+str(i),'fund:'+str(i),'-0.01',10+i,10+i)
        # Independent pinned reference public allocation arithmetic, not the
        # candidate's allocation wrapper, constructs the literal source rows.
        amounts=b.el.allocate_pro_rata('-0.01',[2]*(i+1),'0.000001')
        rev['allocations']=[b.allocation(rev['record_id'],amount,u) for amount,u in zip(amounts,snap['eligible_ranges'])];records.append(rev)
    records.extend(b.mark(f'live-mark:{i}',138+i,'100') for i in range(126))
    records.extend((one_fill('oldest-reduce',264,-1),b.revision('fee:live:0','live:0','-0.1',264,10,2,'fee',b.unit('live:0',0,2,'live:0'))))
    c=primitive_config(records,tie='fills_before_snapshot');c['allocation_quantum_usdt']='0.000001';assert len(records)==512
    return records,c


def context_fixture(variant=0,unresolved=False):
    facts=[]
    for id,econ,available,price in [('a',1,2,'100'),('b',7,None if unresolved else 8,'101'),('equal',9,10,'102'),('future',19,20,'500' if variant else '103')]:
        facts.append(dict(fact_key=id,instrument_id=BTC,schema_id='closed',economic_at_us=econ,scenario_available_at_us=available,observed_first_available_at_us=None,
            cells=[dict(name='price',cell=dict(tag='known',type='D+',value=price))],raw_refs=[],null_reasons={'observed_first_available_at_us':'HISTORICAL_FIRST_AVAILABILITY_UNKNOWN',**({'scenario_available_at_us':'UNRESOLVED_AVAILABILITY'} if available is None else {})}))
    c=primitive_config();c['initial_at_us']=10;c['initial_context']=dict(mode='closed_fact_prefix',from_us=0,schemas=['closed'])
    c['fact_schemas']=[dict(schema_id='closed',kind='price',view_kind='closed_bar',interval_us=1,fields=[dict(name='price',type='D+',unit='USDT_per_base')])]
    d=port_definition('P','policy',dict(mode='context'));d['fact_selectors']=[dict(selection_id='prefix',schema_id='closed',instruments=[BTC],mode='available_prefix')]
    return install_ports(c,[d],[tick(10,'P'),tick(20,'P')]),facts


REPAIR_CASE_IDS=set(UNIMPLEMENTED)|{'S05.04','S10.06','S11.09'}
_OLD_RUN_CASE=run_case

def _repair_run_case(id,parent,variant=0):
    parent=Path(parent);fixture=None;created=0;checks=[]
    def make(records=(),c=None,facts=None):
        nonlocal fixture,created
        created+=1;fixture=Fixture(parent/'fixture0',records,c or primitive_config(records),facts);return fixture
    def check(ok,label):assert ok,label;checks.append(label)
    def step(t):return fixture.advance(t,[i for i,r in enumerate(fixture.records) if r['available_at_us']<=t and fixture.ledger.state.get('events',list(sl.wire_key(r))) is None])
    try:
        if id=='S01.03':
            records=[zero_reserve(),b.fill('long',5,10,'50000','0'),b.fill('short',25,-20,'50000','0')]
            for i,t in enumerate((10,20,30,40)):
                u=b.unit('long' if i<2 else 'short',0,10,'long' if i<2 else 'short');snap=b.snapshot('settlement:'+str(t),t,[u]);total=('-0.05','0.05','0.05','-0.05')[i]
                rev=b.revision('ob:settlement:'+str(t),snap['record_id'],total,t+1,t,1,units=u)
                rev['calculation']=dict(kind='funding_formula',signed_contracts=10 if i<2 else -10,multiplier='0.001',mark_price='50000',final_rate='0.0001' if i%2==0 else '-0.0001',valuation_at_us=t-1,valuation_available_at_us=t-1,rate_available_at_us=t+1,valuation_rule_id=b.rid('valuation'),multiplier_rule_id=b.rid('multiplier'))
                records.extend((b.mark('funding-mark:'+str(t),t-1,'50000'),snap,rev))
            f=make(records,config(records,fee='0',cash='1000'));step(41)
            obs={o['obligation_id']:o['T_usdt'] for o in f.page(41,'obligations')};check([obs['ob:settlement:'+str(t)] for t in (10,20,30,40)]==['-0.05','0.05','0.05','-0.05'],'four funding signs/no proration');compare_reference(f,records,41,fee='0')
        elif id=='S01.05':
            op=one_fill('old',5,10);rev=one_fill('reverse',20,-16);op['fee_fraction']=rev['fee_fraction']='0.00025'
            snap=b.snapshot('old-fund',10,[b.unit('old',0,10,'old')]);claim=b.revision('ob:old-fund','old-fund','-0.05',11,10,1,units=b.unit('old',0,10,'old'))
            records=[zero_reserve(),op,snap,claim,rev];c=config(records,fee='0.00025',cash='1000',multiplier='1');f=make(records,c);step(11);past=f.view(11);step(20)
            closed=f.page(20,'closed_slices')[0];check((closed['entry_fee_cash_usdt'],closed['exit_fee_cash_usdt'],closed['funding_cash_usdt'])==('-0.25','-0.25','-0.05'),'reversal old10/new6 fee .25/.15, funding stays old');check(f.view(11)==past,'old view immutable');check([l['remaining_contracts'] for l in f.page(20,'lots')]==[0,6],'new short6');compare_reference(f,records,20,fee='0.00025')
        elif id in ('S01.09','S10.03'):
            records,c=repair_readiness();f=make(records,c)
            for t,status in ((10,'complete'),(20,'immature'),(21,'immature'),(22,'complete')):
                step(t);r=f.ledger.readiness(dict(episode_id='episode:open',cutoff=dict(at_us=t,slot=0)));check(r['status']==status,'readiness '+str(t))
                if t==10:old=f.view(10);check(r['complete_at_us']==10,'original complete10')
                if t==22:check(r['complete_at_us']==22,'no inherited complete time')
            check(f.view(10)==old,'earlier completeness immutable')
        elif id in ('S01.12','S07.03'):
            records,c=repair_b1(id=='S07.03');f=make(records,c);step(20);old=f.view(20);cp=f.checkpoint();f.restore(cp)
            unknown=f.page(20,'closed_slices');byep={j:[x for x in unknown if x['episode_id']==f'episode:b1-open:{j}'] for j in range(3)}
            check(all(x['entry_fee_cash_usdt'] is None and x['exit_fee_cash_usdt']=='0' for x in byep[0]),'entry unknown local')
            check(all(x['entry_fee_cash_usdt']=='0' and x['exit_fee_cash_usdt'] is None for x in byep[1]),'exit unknown local')
            check(all(x['entry_fee_cash_usdt'] is None and x['exit_fee_cash_usdt'] is None for x in byep[2]),'both unknown local')
            end=40 if id=='S07.03' else 25;step(end);check(f.view(20)==old,'fold/checkpoint immutable old unknown');check(f.balance(end)['cash_usdt']==('998.8' if id=='S07.03' else '998.2'),'refund/top-up exact cash');compare_reference(f,records,end,fee='0')
            if id=='S07.03':check(len(records)==128,'exact128 bodies across fold20/30/40')
        elif id=='S07.02':
            records,c=repair_many_live();f=make(records,c);f.advance(137,range(384));cp=f.checkpoint();f.restore(cp);f.advance(264,range(384,512))
            check(len(f.page(264,'lots',limit=64))==128,'all128 live/original lots paged');check(f.ledger.state.location('lots','lot:live:0')['remaining_contracts']==1,'oldest partial exit');check(f.balance(264)['liabilities_usdt']=='1.38','128 unpaid claims plus late fee');check(f.page(264,'closed_slices')[0]['entry_fee_cash_usdt']=='-0.05','old lot exact split')
            compare_reference(f,records,264,fee='0')
        elif id.startswith('S03.'):
            c,facts=context_fixture(variant if id in ('S03.01','S03.07') else 0,id=='S03.04')
            if id=='S03.04':expect('FUTURE_DEPENDENCY',lambda:make(c=c,facts=facts));check(True,'unresolved required context rejected before initialization')
            else:
                f=make(c=c,facts=facts);context=f.ledger.state.meta('context_receipt');check(context['fact_count']==2,'original availability2/8 admitted exactly once')
                if id=='S03.06' and variant==0:cp=f.checkpoint();f.restore(cp)
                f.advance(10,[]);states=f.page(10,'adapter_states',1);check(states[0]['value']['initializations']==1 and len(states[0]['value']['facts'])==3,'equality10 is first ordinary release; initialize once');check(f.balance(10,1)['cash_usdt']=='1000','context never finance')
                if id=='S03.06' and variant==1:cp=f.checkpoint();f.restore(cp)
                if id=='S03.05':
                    witness=preview_witness(f,20);w=deepcopy(witness);w[0]['reads'].append(dict(kind='fact',fact_key='a',field='scenario_available_at_us',cell=dict(tag='known',type='T',value=10),raw_refs=f.rows[0]['raw_refs']));request=f.request_at(20,[]);request['generated']=w;expect('INPUT_BINDING_MISMATCH',lambda:f.ledger.advance(request));check(True,'altered original-clock packet rejected')
                else:
                    before=f.view(10,1);f.advance(20,[]);check(f.view(10,1)==before,'past packet/state remains fixed');check(f.page(20,'adapter_states',1)[0]['value']['initializations']==1,'no fold reinitialization')
                    # Per-replica fingerprints are compared by the finite driver.
                    dump(parent/'comparison.json',dict(past=before,context=context,registry=f.page(10,'registry',1)))
        elif id in ('S04.01','S04.02','S04.03','S04.04','S04.05'):
            c=controlled_config();f=make(c=c,facts=[]);f.advance(10,[]);g=preview_witness(f,20);proposed=deepcopy(g)
            if id=='S04.01':
                # Add a genuinely frozen future fact, not a fabricated hash.
                raise AssertionError('future-fact fixture needs construction before formal')
            elif id=='S04.02':proposed[0]['result']['events'][0]['signed_contracts']=2;proposed[0]['result_sha256']=sl.digest(proposed[0]['result'])
            elif id=='S04.03':
                read=next(x for x in proposed[1]['reads'] if x['kind']=='ledger' and x['item_kind']=='live_lot');read['value']['value']['live_ranges']=[]
            elif id=='S04.04':
                read=next(x for x in proposed[0]['reads'] if x['kind']=='ledger' and x['item_kind']=='order');read['value']['value']['remaining_contracts']=2
            else:proposed[0]['reads']=[x for x in proposed[0]['reads'] if x['kind']!='state']
            for entry in proposed:
                entry.pop('entry_sha256');entry['entry_sha256']=sl.digest(entry)
            request=f.request_at(20,[]);request['generated']=proposed;before=f.ledger.head.copy();expect('ADAPTER_RESULT_MISMATCH' if id=='S04.02' else 'INPUT_BINDING_MISMATCH',lambda:f.ledger.advance(request));check(f.ledger.head==before,'forged witness cannot change prefix')
        elif id=='S05.04':
            records=[one_fill('accepted',10),one_fill('backdated',19)];f=make(records);f.advance(20,[0]);old=f.ledger.head.copy()
            if variant==0:expect('PAST_AVAILABILITY',lambda:f.advance(30,[1]));check(f.ledger.head==old,'new19 behind seal20 rejected')
            else:f.advance(30,[0]);check(len(f.page(30,'events'))==1,'exact duplicate under new outer identity has no effect')
        elif id=='S10.06':
            records=[zero_reserve(expires=11),one_fill('open',10),b.mark('m',10,'100'),one_fill('backdated',11)];c=primitive_config(records)
            for r in c['rules']:
                if r['kind']=='valuation':r['parameters']['max_age_us']=1
            c['expected_snapshots']=[dict(instrument_id=BTC,event_id='due',snapshot_at_us=11,mapping_rule_id=b.rid('funding'))]
            f=make(records,c);f.advance(10,[0,1,2]);f.advance(11,[]);check(f.ledger.head['cutoff']==dict(at_us=11,slot=0),'actual non-tick11 seals')
            b11=f.balance(11);check(b11['unrealized_usdt']=='0' and b11['reserved_margin_usdt'] is None and b11['receivables_usdt'] is None,'true freshness/expiry/due coverage equality');expect('PAST_AVAILABILITY',lambda:f.advance(12,[3]))
        elif id=='S11.09':
            snap=b.snapshot();snap.update(source_t_seconds=0,source_record_at_us=0);snap['null_reasons']={'snapshot_sequence':'UNKNOWN_SEQUENCE'}
            if variant==1:snap['mapping_rule_id']='wrong-mapping'
            if variant==2:snap['mapping_rule_id']=None;snap['null_reasons']['mapping_rule_id']='UNKNOWN_MAPPING'
            records=[b.fill(),snap];c=config(records,cash='1000');c['expected_snapshots'][0]['mapping_rule_id']=b.rid('funding');f=make(records,c)
            if variant==0:
                request=f.request_at(10);request['imported'][1]['body']['source_record_at_us']=1;expect('CLOCK_CONTRADICTION',lambda:f.ledger.advance(request))
            elif variant==1:expect('SNAPSHOT_MAPPING_MISMATCH',lambda:f.advance(10))
            else:f.advance(10);check(f.balance(10)['receivables_usdt'] is None,'unqualified mapping remains unresolved coverage')
        else:raise AssertionError('repair fixture not implemented: '+id)
        return dict(status='PASS',fixtures=created,checks=checks,metrics=dict(bodies=len(fixture.records) if fixture else 0))
    finally:
        if fixture:fixture.close()


def preview_witness(f,t):
    ledger=f.ledger;ledger.index.db.commit();ledger.index.db.execute('SAVEPOINT witness_preview');state=sl.State(ledger.index,ledger.config,ledger.state.roots)
    try:return ledger._stage(f.request_at(t,[]),state)['generated']
    finally:
        ledger.index.db.execute('ROLLBACK TO witness_preview');ledger.index.db.execute('RELEASE witness_preview');ledger.index.cache.clear();ledger.index.size=0


def run_case(id,parent,variant=0):
    if id in REPAIR_CASE_IDS:return _repair_run_case(id,parent,variant)
    return _OLD_RUN_CASE(id,parent,variant)

class RepairCheckpointTests(unittest.TestCase):
    def setUp(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        self.root=Path(tempfile.mkdtemp(prefix='checkpoint-',dir=root)).resolve()
    def make(self,records=None,c=None,facts=None):
        records=basic_tape() if records is None and c is None else records or ()
        f=Fixture(self.root/'fixture',records,c,facts);self.addCleanup(f.close);return f
    def test_typed_inventory_and_forged_component(self):
        f=self.make();f.advance(10);cp=f.checkpoint();components={r['component'] for r in cp['files']}
        self.assertTrue({'config','raw_catalogue','facts','adapters','schedule','context','calendar','projection','ownership','dedup','revisions','journal','cursors','control'}<=components)
        f.restore(cp)
        target=next(r for r in cp['files'] if r['component']=='ownership');path=f.path/'store'/target['relative_path'];rows=path.read_bytes().splitlines(keepends=True);path.write_bytes(b''.join(rows[1:]));target.update(bytes=path.stat().st_size,rows=len(rows)-1,sha256=hashlib.sha256(path.read_bytes()).hexdigest());cp['checkpoint_sha256']=sl.digest({k:v for k,v in cp.items() if k!='checkpoint_sha256'})
        expect('STORE_INTEGRITY_FAILURE',lambda:f.restore(cp))
    def test_cursor_membership_and_failure_audit_paging(self):
        c,facts=context_fixture();f=self.make(c=c,facts=facts);f.advance(10,[]);cp=f.checkpoint();bad=deepcopy(cp);bad['adapter_cursors'][0]['last_invocation']=None;bad['checkpoint_sha256']=sl.digest({k:v for k,v in bad.items() if k!='checkpoint_sha256'});expect('CHECKPOINT_MISMATCH',lambda:f.restore(bad))
        request=dict(view_sha256=f.view(10,1)['view_sha256'],component='lots',filter=dict(kind='all'),after=None,limit=257,null_reasons={'after':'START_OF_COMPONENT'})
        expect('RESOURCE_EXHAUSTED_READ',lambda:f.ledger.scan(request));rows=[];after=0
        while True:
            p=f.ledger.audit(dict(after_audit_seq=after,limit=1));rows+=p['rows'];after=p['next_after_audit_seq']
            if after is None:break
        self.assertTrue(any(r['kind']=='failure' and r['error']['code']=='RESOURCE_EXHAUSTED_READ' for r in rows));self.assertEqual(f.ledger.current_head()['status'],'ACTIVE')
    def test_quota_prevents_sqlite_write_before_cap(self):
        f=self.make([one_fill()],primitive_config([one_fill()]));budget=f.ledger.budget;old_head=f.ledger.head.copy();original_stage=f.ledger._stage
        def exhaust(*args,**kw):
            budget.limit=budget.total+budget.book.stat().st_size+budget.reserve+2048
            return original_stage(*args,**kw)
        with patch.object(f.ledger,'_stage',side_effect=exhaust):
            error=expect('RESOURCE_EXHAUSTED',lambda:f.advance(10))
        self.assertEqual(f.ledger.head,old_head);self.assertEqual(f.ledger.current_head()['status'],'RESOURCE_STOPPED')
        actual=sum(p.stat().st_size for p in (f.path/'store').rglob('*') if p.is_file());self.assertLessEqual(actual,budget.limit)
        f.reopen();self.assertEqual(f.ledger.current_head()['status'],'RESOURCE_STOPPED')


class RepairFifoTests(unittest.TestCase):
    def test_multi_lot_snapshot_and_close_share_one_episode(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='fifo-',dir=root));units=[b.unit('a',0,1,'a'),b.unit('b',0,1,'a')]
        snapshot=b.snapshot('snapshot',3,units);revision=b.revision('ob:snapshot','snapshot','0',5,3);revision['allocations']=[b.allocation('ob:snapshot','0',u) for u in units]
        records=[one_fill('a',1),one_fill('b',2),snapshot,one_fill('close',4,-2),revision]
        f=Fixture(parent/'fixture',records,primitive_config(records));self.addCleanup(f.close);f.advance(5)
        self.assertEqual([x['episode_id'] for x in f.page(5,'lots')],['episode:a','episode:a'])
        self.assertEqual([x['remaining_contracts'] for x in f.page(5,'lots')],[0,0]);self.assertEqual(len(f.page(5,'closed_slices')),2)
        self.assertEqual(f.balance(5)['liabilities_usdt'],'0')


def _repair_cli():
    # The human validation gate supersedes the earlier automatic formal dispatch.
    # New full/benchmark runs need a separately approved scope; this candidate
    # deliberately exposes only selected development unit checks by default.
    if any(flag in sys.argv for flag in ('--formal','--benchmark','--freeze')):
        raise SystemExit('USER_VALIDATION_APPROVAL_REQUIRED: full validation disabled for repair-r1 candidate')
    if len(sys.argv)==1:raise SystemExit('Select one directly relevant development test; no automatic full run')
    unittest.main()




class RepairAdmissionTests(unittest.TestCase):
    def test_late_origin_precedes_snapshot_eligibility_for_failed_orders(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='late-',dir=root))
        for variant in (0,1):
            records,kw=case_tape('S01.06',variant);f=Fixture(parent/str(variant),records,kw['c']);self.addCleanup(f.close)
            before=f.ledger.head.copy();expect('LATE_ORIGIN_UNSUPPORTED',lambda:f.advance(10));self.assertEqual(f.ledger.head,before)
    def test_sqlite_size_hint_is_rejected_before_allocation(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='hint-',dir=root));f=Fixture(parent/'fixture',[],primitive_config());self.addCleanup(f.close)
        path=f.path/'store/cache.sqlite3';size=path.stat().st_size;pointer,info=next(iter(sl._VFS_FILES.items()));target=sl.ctypes.c_int64(f.ledger.budget.limit+1)
        rc=sl._FC(info[1].control)(pointer,5,sl.ctypes.cast(sl.ctypes.pointer(target),sl.ctypes.c_void_p));self.assertEqual(rc,13);self.assertEqual(path.stat().st_size,size)
        f.ledger.budget.last_error=None;f.ledger.budget.emergency=False
        if f.ledger.budget.parent:f.ledger.budget.parent.emergency=False




class RepairGuardTests(unittest.TestCase):
    def test_unpublished_semantic_stop_stays_blocked_across_reopen(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='guard-',dir=root));f=Fixture(parent/'fixture',[one_fill()],primitive_config([one_fill()]));self.addCleanup(f.close)
        request=f.request_at(10);request['imported'][0]['body']['fill_price']='bad';control=f.ledger._control
        def stop_failure(kind,*args,**kwargs):
            if kind=='integrity_stop':raise OSError('injected stop publication failure')
            return control(kind,*args,**kwargs)
        with patch.object(f.ledger,'_control',side_effect=stop_failure):expect('COMMIT_OUTCOME_UNKNOWN',lambda:f.ledger.advance(request))
        f.reopen();self.assertEqual(f.ledger.current_head()['status'],'COMMIT_UNKNOWN')
        result=f.ledger.resolve_commit(dict(request_id=request['request_id'],request_sha256=sl.digest(request)))
        self.assertEqual(result['outcome'],'not_committed');self.assertEqual(result['head']['status'],'INTEGRITY_STOPPED');self.assertEqual(result['head']['committed_seq'],0)
    def test_omitted_live_range_witness_is_rejected_without_commit(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='witness-',dir=root));result=_repair_run_case('S04.03',parent);self.assertEqual(result['status'],'PASS')




class RepairVfsFailureTests(unittest.TestCase):
    def test_native_callback_io_error_reaches_guarded_advance(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='vfs-fault-',dir=root));f=Fixture(parent/'fixture',[one_fill()],primitive_config([one_fill()]));self.addCleanup(f.close)
        before=f.ledger.head.copy();budget=f.ledger.budget;issue=budget.issue
        def fail_sqlite(path,end,amount=0):
            if str(path).endswith(('.sqlite3','-journal')):raise OSError('injected VFS prewrite I/O failure')
            return issue(path,end,amount)
        with patch.object(budget,'issue',side_effect=fail_sqlite):expect('COMMIT_OUTCOME_UNKNOWN',lambda:f.advance(10))
        self.assertEqual(f.ledger.head,before);self.assertEqual(f.ledger.current_head()['status'],'COMMIT_UNKNOWN');self.assertIsNotNone(f.ledger.control['guard'])




class RepairCorroborationTests(unittest.TestCase):
    def test_new_source_reference_updates_audit_root_without_repeating_fill(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='corroboration-',dir=root));records=[one_fill(),one_fill()];f=Fixture(parent/'fixture',records,primitive_config(records));self.addCleanup(f.close)
        f.advance(10,[0]);key=list(sl.wire_key(f.records[0]));before=f.ledger.state.get('_dedup',key);past=f.view(10)
        f.advance(11,[1]);after=f.ledger.state.get('_dedup',key);self.assertNotEqual(before['audit_refs_root'],after['audit_refs_root']);self.assertEqual(after['first_commit'],1)
        self.assertEqual(len(f.page(11,'events')),1);self.assertEqual(f.balance(11)['cash_usdt'],'1000');self.assertEqual(f.view(10),past)
        cp=f.checkpoint();f.restore(cp);self.assertEqual(f.ledger.state.get('_dedup',key),after)




class RepairOrphanControlTests(unittest.TestCase):
    def test_validated_orphan_is_preserved_and_resolved_without_importing_tail(self):
        root=Path('research/.data/qd009/stream-repair-r1/tmp/unit-dev');root.mkdir(parents=True,exist_ok=True)
        parent=Path(tempfile.mkdtemp(prefix='orphan-control-',dir=root));f=Fixture(parent/'fixture',[one_fill()],primitive_config([one_fill()]));self.addCleanup(f.close)
        request=f.request_at(10);atomic=sl._atomic
        def failed_pointer(path,value):
            if Path(path).name=='CONTROL' and value['control_seq']==2:raise OSError('after validated row, before CONTROL pointer')
            return atomic(path,value)
        with patch.object(sl,'_atomic',side_effect=failed_pointer):expect('COMMIT_OUTCOME_UNKNOWN',lambda:f.ledger.advance(request))
        row=f.path/'store/control-00000002.json';original=row.read_bytes();f.reopen()
        resolved=f.ledger.resolve_commit(dict(request_id=request['request_id'],request_sha256=sl.digest(request)))
        self.assertEqual(resolved['outcome'],'not_committed');self.assertEqual(resolved['head']['committed_seq'],0);self.assertEqual(row.read_bytes(),original)
        self.assertTrue((f.path/'store/journal-00000001.json').exists(),'orphan financial data remains evidence')

if __name__=='__main__':_repair_cli()
