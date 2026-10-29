"""Immutable market cache -> streamed facts -> one continuous registered ledger.

Chunking only bounds advance calls/output consumption. It never creates a fresh
account or truncates native warmup. No generated fills are supplied by this code.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import os
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS,HOUR,US,InputGap,exact
from research.qd011.driver import (SCHEMAS,ROLE,definitions,fact,Continuous,scan)
from research.qd011.codec import KINDS,state
from research.qd011.ports import ControlledPort,RUNTIME
from .scenarios import scenario


def calendar(cache,initial,economic_end,tail_end):
    funding=[];ticks=set(range(initial,tail_end,HOUR))
    for i,at,row in cache.records('funding'):
        if not initial<=at<economic_end:continue
        if at%US:raise InputGap('INTEGER_FUNDING_SOURCE_SECONDS_REQUIRED_NO_ROUNDING')
        available=(at//HOUR+1)*HOUR
        event='fund:'+i+':'+str(at)
        funding.append(dict(instrument_id=i,event_id=event,snapshot_at_us=at,mapping_rule_id='funding:'+i))
        ticks.update(t for t in (at,available,available+60*US,available+HOUR+60*US) if initial<=t<tail_end)
    return sorted(ticks),sorted(funding,key=lambda f:(f['snapshot_at_us'],f['instrument_id']))


def create(path,cache,*,initial_us,economic_end_us,tail_end_us,scenario_id='P0',policy_id='ALLOW_ALL',write_budget=None):
    if initial_us%HOUR or economic_end_us%HOUR or not initial_us<economic_end_us or tail_end_us!=economic_end_us+2*HOUR:
        raise InputGap('FIXED_ECONOMIC_AND_TWO_HOUR_TAIL_REQUIRED')
    s=scenario(scenario_id,policy_id);path=Path(path)
    if path.exists():raise InputGap('EXCLUSIVE_NEW_TRAJECTORY_REQUIRED')
    path.mkdir(parents=True);source=path/'source';source.mkdir()
    ticks,funding=calendar(cache,initial_us,economic_end_us,tail_end_us)
    scope=dict(ledger_id='qd013:'+scenario_id+':'+policy_id,trajectory_id=scenario_id+':'+policy_id,scenario_id=scenario_id)
    context=dict(version='qd013.compact-native-context.v3',initial_us=initial_us,cache_key=cache.key,
        market_content_sha256=cache.meta['content_sha256'],first_open_us=cache.meta['identity']['scope']['warmup_start_us'],
        initial_timing_state={},input_schema='native-v3')
    context['context_sha256']=sl.digest(context)
    common=dict(scope=scope,initial_us=initial_us,end_us=economic_end_us,economic_end_us=economic_end_us,tail_end_us=tail_end_us,
        ticks=ticks,funding_schedule=funding,runtime=RUNTIME,input_basis='FROZEN_NATIVE_CAUSAL_CACHE_NOT_ACCOUNT_REPLAY_ACCEPTANCE',
        native_input_version=3,native_schema_id='native-v3',native_context=context,scenario=s)
    defs=definitions(common)
    for d in defs:sl.register_port(d,ControlledPort())
    raw_path=source/'supplied.jsonl';fact_path=source/'facts.pending.jsonl'
    row_number=0;raw_sha=hashlib.sha256();raw_bytes=0;fact_rows=0
    def write(handle,raw):
        if write_budget:write_budget(handle.name,handle.tell()+len(raw),len(raw))
        handle.write(raw)
    schemas=[dict(schema_id=k,**deepcopy(v)) for k,v in SCHEMAS.items()];mark_schema=None
    # Pending fact stream refers to source row indices; after the one raw hash is
    # known, rewrite this derived stream once, never retain all facts in RAM.
    with raw_path.open('xb') as raw,fact_path.open('xb') as facts:
        def emit(record,normalized):
            nonlocal row_number,raw_bytes,fact_rows,mark_schema
            row_number+=1;b=sl.canonical_bytes(record)+b'\n';write(raw,b);raw_sha.update(b);raw_bytes+=len(b)
            normalized['raw_refs']=[dict(object_id='supplied',raw_sha256='0'*64,source_row=row_number)]
            write(facts,sl.canonical_bytes(normalized)+b'\n');fact_rows+=1
        for kind in ('native','open','funding'):
            for i,at,r in cache.records(kind):
                if not initial_us<=at<economic_end_us:continue
                if kind=='native':
                    vals={f['name']:r.get(f['name']) for f in SCHEMAS['native-v3']['fields']}
                    normalized=fact('native-v3',i,at-HOUR,at,vals,'native:'+i+':'+str(at))
                elif kind=='open':normalized=fact('open',i,at,at,dict(open_us=at,open_price=r['price']),'open:'+i+':'+str(at))
                else:
                    normalized=fact('rate',i,at,(at//HOUR+1)*HOUR,dict(event_us=at,rate=r['rate']),'rate:fund:'+i+':'+str(at))
                emit(dict(kind=kind,record=r,cache_key=cache.key),normalized)
        mark_kind='mark_slow' if scenario_id=='M_SLOW' else 'mark_primary';roles=['valuation','reservation','decision','permitted_fill','funding_snapshot']
        for i,at,r in cache.records(mark_kind):
            if not initial_us<=at<economic_end_us:continue
            dto=r['dto'];normalized=sl.normalize_mark_selection(dto,'mark',roles)
            if mark_schema is None:mark_schema=dict(schema_id='mark',kind='mark-selection',view_kind='mark_selection',interval_us=0,
                fields=[dict(name=c['name'],type=c['cell']['type'],unit='declared_MARK_scenario') for c in normalized['cells']])
            emit(dict(kind=mark_kind,record=r,cache_key=cache.key),normalized)
        raw.flush();os.fsync(raw.fileno());facts.flush();os.fsync(facts.fileno())
    if mark_schema is None:raise InputGap('MARK_QUERY_PLAN_EMPTY')
    schemas.append(mark_schema);raw_hash=raw_sha.hexdigest();h=hashlib.sha256();size=0
    with fact_path.open('rb') as old,(source/'facts.jsonl').open('xb') as final:
        for line in old:
            v=sl.load_json(line);v['raw_refs'][0]['raw_sha256']=raw_hash;b=sl.canonical_bytes(v)+b'\n'
            write(final,b);h.update(b);size+=len(b)
        final.flush();os.fsync(final.fileno())
    # Only a successfully flushed replacement supersedes this new temporary;
    # a failed preparation leaves its partial files for diagnosis.
    fact_path.unlink()
    ref=dict(root_id='source',relative_path='facts.jsonl',sha256=h.hexdigest(),bytes=size,rows=fact_rows)
    requirements=[]
    for at in ticks:
        if at>=economic_end_us:continue
        for i in INSTRUMENTS:
            for role in roles:requirements.append(dict(key=dict(instrument_id=i,clock_id='mark-clock',query_at_us=at,purpose=role),
                before_slots=[k+':'+str(at) for k in KINDS],for_view=role in ('valuation','reservation')))
    rules=[]
    for i in INSTRUMENTS:
        parameters=dict(fee=dict(role='taker',signed_fraction=s['fee'],fee_currency='USDT'),
            multiplier=dict(base_per_contract='0.0001' if i==INSTRUMENTS[0] else '0.01',quantity_unit='contracts'),
            valuation=dict(price_kind='MARK',max_age_us=s['mark_max_age_us']),
            sequence=dict(same_time_order='fills_before_snapshot' if s['fill_first'] else 'snapshot_before_fills'),
            funding=dict(calendar='explicit_snapshot_list'),booking=dict(policy='explicit_posting_records'),
            finality=dict(policy='explicit_scoped_assertions',authority_id='authority'))
        for k,v in parameters.items():rules.append(dict(rule_id=k+':'+i,kind=k,instrument_id=i,valid_from_us=0,valid_to_exclusive_us=None,
            available_at_us=0,authority_id='authority',parameters=v,null_reasons={'valid_to_exclusive_us':'OPEN_ENDED_SCENARIO'}))
    order=('execution','environment','feedback','policy','reserve') if s['fill_first'] else KINDS
    config=dict(**scope,instruments=list(INSTRUMENTS),initial_at_us=initial_us,end_exclusive_us=economic_end_us,
        knowledge_end_exclusive_us=tail_end_us,initial_cash_usdt='10000',allocation_quantum_usdt='0.000000000000000001',
        rules=rules,expected_snapshots=funding,ingestion_mode='controlled_adapters',adapters=defs,
        initial_adapter_states=[state(k,dict(timing={}) if k in ('policy','feedback') else None) for k in KINDS],
        schedule=[dict(at_us=t,slots=[dict(slot_id=k+':'+str(t),adapter_id=k,phase=n) for n,k in enumerate(order)]) for t in ticks],
        fact_schemas=schemas,initial_context=dict(mode='none',from_us=initial_us,schemas=[]),
        mark_clocks=[dict(instrument_id=i,clock_id='mark-clock',valuation_rule_id='valuation:'+i,multiplier_rule_id='multiplier:'+i,
            source_delay_us=s['mark_delay_us'],max_source_age_us=s['mark_max_age_us'],max_available_age_us=s['mark_available_age_us']) for i in INSTRUMENTS],
        mark_view_bindings=[dict(instrument_id=i,clock_id='mark-clock') for i in INSTRUMENTS],mark_requirements=requirements,
        limits=deepcopy(sl.LIMITS),random_source='NONE')
    catalogue=dict(namespace='qf009.raw-catalogue',schema_version=1,catalogue_id='qd013:'+scenario_id+':'+policy_id,fact_store=ref,
        qualification_ref=sl.digest([common,cache.meta]),objects=[dict(object_id='supplied',root_id='source',instrument_id=INSTRUMENTS[0],
        sha256=raw_hash,bytes=raw_bytes,relative_path='supplied.jsonl',format='derived_native_v3_jsonl',source_row_basis='physical_line',
        original_time_unit='microseconds',retrieved_at_us=None,null_reasons={'retrieved_at_us':'UNKNOWN_RETRIEVAL'})])
    request=dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,request_id='create',config=config,raw_catalogue=catalogue,
        fact_store=ref,source_roots=[dict(root_id='source',path=str(source.resolve()))],store_root=str(path/'store'))
    sl.create(request)
    return Replay(sl.Ledger(path/'store'))


class Replay(Continuous):
    def advance_chunk(self,through_us):return self.advance(through_us)

    @classmethod
    def reopen(cls,store):
        request=sl.load_json((Path(store)/'GENESIS').read_bytes())
        for d in request['config']['adapters']:sl.register_port(d,ControlledPort())
        return cls(sl.Ledger(store))

    def censored_or_mature(self,at):
        from .exports import export_all
        return export_all(self,at)
