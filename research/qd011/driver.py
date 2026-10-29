"""Finite supplied-input normalizer and controlled driver, no data acquisition.

Native observations are causal prepared-feature inputs (not strategy actions).
Version 1 is an explicit synthetic fixture seed. Version 2 requires actual native
cache/covariance/regime inputs. Neither version grants actual-history execution.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from copy import deepcopy
import hashlib
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS, HOUR, US, Mark, FrozenInputs, exact, text, InputGap
from .codec import KINDS, STATE_CONTRACT, state, validate, validate_context, unpack
from .ports import ControlledPort, RUNTIME

BASE_COMMIT='d2493fd62c208c8268acb7174230bfe6b0d59b61'
ROLE={'environment':'environment','execution':'execution','feedback':'execution','policy':'policy','reserve':'environment'}
SCHEMAS={
 'native':dict(kind='native-prepared-observation',view_kind='closed_bar',interval_us=HOUR,fields=[
     dict(name=k,type=t,unit=u) for k,t,u in (
       ('short','D','forecast'),('main','D','forecast'),('vol','D+','annual_std'),('carry','D','forecast'),
       ('risk','D0','fraction'),('quality','D0','fraction'),('extension','D','ATR_multiple'),('close','D+','USDT_per_base'),
       ('atr','D0','USDT_per_base'),('recent_high','D+','USDT_per_base'),('recent_low','D+','USDT_per_base'),
       ('volume','D0','contracts'),('main_open_us','T','UTC_us'),('long_run','I','bars'),('short_run','I','bars'),
       ('cov_cross','D','annual_covariance'))]),
 'open':dict(kind='execution-open',view_kind='execution_open',interval_us=HOUR,fields=[dict(name='open_us',type='T',unit='UTC_us'),dict(name='open_price',type='D+',unit='USDT_per_base')]),
 'rate':dict(kind='funding-rate',view_kind='funding_rate',interval_us=0,fields=[dict(name='event_us',type='T',unit='UTC_us'),dict(name='rate',type='D',unit='fraction')])}
SCHEMAS['native-v2']=deepcopy(SCHEMAS['native'])
SCHEMAS['native-v2']['fields'] += [dict(name=k,type=t,unit=u) for k,t,u in (
    ('regime','ID','native_regime'),('regime_open_us','T','UTC_us'),('regime_available_us','T','UTC_us'),
    ('efficiency','D0','ratio'),('range_vol_ratio','D0','ratio'),('cov_btc_btc','D+','annual_covariance'),
    ('cov_eth_eth','D+','annual_covariance'),('cov_available_us','T','UTC_us'),
    ('breakout_long','bool','flag'),('breakout_short','bool','flag'),('bar_seconds','D+','seconds'))]
SCHEMAS['native-v3']=deepcopy(SCHEMAS['native-v2'])
SCHEMAS['native-v3']['fields'] += [dict(name=k,type=t,unit=u) for k,t,u in (
    ('first_open_us','T','UTC_us'),('short_count','I','closed_bars'),('main_count','I','closed_bars'),('regime_count','I','closed_bars'))]


@dataclass(frozen=True)
class NativeObservation:
    instrument_id: str
    available_us: int
    main_open_us: int
    short: str
    main: str
    vol: str
    carry: str
    risk: str
    quality: str
    extension: str
    close: str
    atr: str
    recent_high: str
    recent_low: str
    volume: str
    long_run: int
    short_run: int
    cov_cross: str | None
    source_ref: str
    regime: str | None = None
    regime_open_us: int | None = None
    regime_available_us: int | None = None
    efficiency: str | None = None
    range_vol_ratio: str | None = None
    cov_btc_btc: str | None = None
    cov_eth_eth: str | None = None
    cov_available_us: int | None = None
    breakout_long: bool | None = None
    breakout_short: bool | None = None
    bar_seconds: str | None = None


@dataclass(frozen=True)
class ExecutionOpen:
    instrument_id: str
    at_us: int
    price: str
    source_ref: str


@dataclass(frozen=True)
class FundingPoint:
    instrument_id: str
    source_us: int
    rate: str
    event_id: str
    source_ref: str


def pinned_files():
    root=Path(__file__).resolve().parents[2]
    paths=('research/qd011/driver.py','research/qd011/ports.py','research/qd011/codec.py',
           'research/qd010/joint_native_bridge.py','research/qd010/economic_inputs.py',
           'src/portfolio.py','src/strategy_signals.py','src/strategy_execution.py','src/execution_timing.py','src/config.py',
           'src/position_sizing.py','src/trend.py','src/vol.py','src/carry.py','src/risk.py','src/data_fetcher.py',
           'research/qd008/repair_history.py',
           'research/qd010/episode_export.py','research/qd011/export.py','research/qd009/streaming_ledger.py',
           'research/qd012/sources.py','research/qd012/native.py','research/qd012/queries.py','research/qd012/prepare.py',
           'research/qd013/compact.py','research/qd013/scenarios.py','research/qd013/market.py','research/qd013/runner.py','research/qd013/exports.py','research/qd013/inputs.py')
    return [dict(relative_path=s,sha256=hashlib.sha256((root/s).read_bytes()).hexdigest()) for s in paths]


def selector(kind,n):
    return dict(selection_id=n,instruments=list(INSTRUMENTS),kind=kind)


def definitions(common):
    files=pinned_files();result=[]
    for kind in KINDS:
        led=[selector('live_lots','01-live'),selector('mark_context','02-marks'),
             selector('orders_active_and_changed','03-orders')]
        if kind in ('environment','feedback'):
            led.extend([selector('financial_changes','04-changes'),selector('episode_lots','05-lots'),
                        selector('episode_slices','06-slices'),selector('episode_obligations','07-obligations')])
        ftypes={'environment':['rate'],'execution':['native','open'],'feedback':['native'],'policy':['native'],'reserve':[]}[kind]
        facts=[dict(selection_id=s,schema_id=common['native_schema_id'] if s=='native' else s,instruments=list(INSTRUMENTS),
                    mode='latest_available' if kind in ('execution','feedback') or (common['native_input_version']==3 and s=='native') else 'available_prefix') for s in ftypes]
        peers={'policy':['feedback'],'feedback':['policy','execution'],'environment':[],'execution':[],'reserve':[]}[kind]
        causal=deepcopy(common)
        if kind!='policy':causal.pop('native_context',None)
        result.append(dict(adapter_id=kind,role=ROLE[kind],code_commit='c761d90d65bb33ef4256d26cba1a48163606e41f' if common['native_input_version']==3 else '61536c823926fb873f9a4a130778f34e0b87c161' if common['native_input_version']==2 else BASE_COMMIT,source_files=files,
            entrypoint='research.qd011.ports.ControlledPort',input_contract_sha256=sl.digest(['qd011.packet.v1',kind]),
            output_contract_sha256=sl.digest(['qd011.result.v1',kind]),state_contract_sha256=STATE_CONTRACT,
            causal_config=causal,approval_ref=sl.digest(['QD011_LOCAL_INPUT_V'+str(common['native_input_version']),kind]),
            fact_selectors=facts,ledger_selectors=led,peer_state_selectors=[dict(adapter_id=k) for k in peers]))
    return result


def fact(schema,inst,at,available,values,key):
    fields=SCHEMAS[schema]['fields']
    cells=[dict(name=f['name'],cell=dict(tag='known',type=f['type'],value=values[f['name']]) if values[f['name']] is not None
                else dict(tag='unknown',type=f['type'],reason='UNKNOWN_AMOUNT')) for f in fields]
    return dict(fact_key=key,instrument_id=inst,schema_id=schema,economic_at_us=at,scenario_available_at_us=available,
                observed_first_available_at_us=None,cells=cells,raw_refs=[],null_reasons={'observed_first_available_at_us':'HISTORICAL_FIRST_AVAILABILITY_UNKNOWN'})


def create(path,*,initial_us,end_us,native,opens,marks,funding=(),seed_forecast='10',seed_vol='0.5',native_input_version=1,native_context=None,economic_end_us=None,mark_selections=None):
    """Fresh finite study store; no API to append inputs or import generated fills."""
    if native_input_version not in (1,2):raise InputGap('UNSUPPORTED_NATIVE_INPUT_VERSION')
    if native_input_version==2:
        if native_context is None:raise InputGap('ACTUAL_NATIVE_WARMUP_CONTEXT_REQUIRED')
        validate_context(native_context,initial_us)
    elif native_context is not None:raise InputGap('NO_V2_CONTEXT_IN_LEGACY_SYNTHETIC_MODE')
    economic_end_us=end_us if economic_end_us is None else economic_end_us
    if not initial_us<economic_end_us<=end_us or economic_end_us%HOUR:raise InputGap('INVALID_ECONOMIC_CUTOFF')
    schema='native-v2' if native_input_version==2 else 'native'
    native,opens,marks,funding=tuple(native),tuple(opens),tuple(marks),tuple(funding)
    if native_input_version==2:
        for n in native:
            if any(getattr(n,f['name']) is None for f in SCHEMAS[schema]['fields']):
                raise InputGap('INCOMPLETE_NATIVE_V2_OBSERVATION')
        for f in funding:
            if f.source_us%US:raise InputGap('LEDGER_SOURCE_T_SECONDS_CANNOT_REPRESENT_SUBSECOND_SOURCE_WITHOUT_CONTRACT_CHANGE')
    path=Path(path);path.mkdir(parents=True,exist_ok=False)
    if initial_us%HOUR or end_us%HOUR or not initial_us<end_us:
        raise InputGap('WHOLE_HOUR_WINDOW_REQUIRED')
    raw=[dict(kind='native-context-v2',context=native_context)] if native_input_version==2 else [dict(kind='seed',initial_us=initial_us,forecast=seed_forecast,vol=seed_vol)]
    for kind,seq in (('native',native),('open',opens),('mark',marks),('funding',funding)):
        raw.extend(dict(kind=kind,record=asdict(v)) for v in seq)
    source=path/'source';source.mkdir()
    raw_rows={}
    for index,item in enumerate(raw,1):
        if index!=1:
            v=item['record'];kind=item['kind'];when=v.get('available_us',v.get('at_us',v.get('source_us')))
            raw_rows[kind,v['instrument_id'],when]=index
    normalized=[]
    seen=set()
    for n in native:
        if n.instrument_id not in INSTRUMENTS or n.available_us%HOUR or not n.source_ref:
            raise InputGap('INVALID_NATIVE_OBSERVATION')
        key=n.instrument_id,n.available_us
        if key in seen:raise InputGap('DUPLICATE_NATIVE_OBSERVATION')
        seen.add(key)
        values={k:asdict(n)[k] for k in [f['name'] for f in SCHEMAS[schema]['fields']]}
        if native_input_version==2 and (any(v is None for v in values.values()) or n.regime not in ('range','trend_up','trend_down')
                or n.regime_available_us>n.available_us or n.regime_open_us+24*HOUR!=n.regime_available_us
                or n.cov_available_us>n.available_us):raise InputGap('INCOMPLETE_OR_FUTURE_NATIVE_V2_OBSERVATION')
        normalized.append(dict(fact(schema,n.instrument_id,n.available_us-HOUR,n.available_us,values,'native:'+n.instrument_id+':'+str(n.available_us)),_source_row=raw_rows['native',n.instrument_id,n.available_us]))
    for o in opens:
        if o.instrument_id not in INSTRUMENTS or o.at_us%HOUR or exact(o.price)<=0 or not o.source_ref:
            raise InputGap('INVALID_EXECUTION_OPEN')
        normalized.append(dict(fact('open',o.instrument_id,o.at_us,o.at_us,dict(open_us=o.at_us,open_price=o.price),'open:'+o.instrument_id+':'+str(o.at_us)),_source_row=raw_rows['open',o.instrument_id,o.at_us]))
    schedule=[dict(instrument_id=f.instrument_id,event_id=f.event_id,snapshot_at_us=f.source_us,mapping_rule_id='funding:'+f.instrument_id) for f in funding]
    ticks=sorted(set([initial_us,end_us]+[n.available_us for n in native if initial_us<=n.available_us<=end_us]
        +[o.at_us for o in opens if initial_us<=o.at_us<end_us]
        +[t for f in funding for t in (f.source_us,(f.source_us//HOUR+1)*HOUR,(f.source_us//HOUR+1)*HOUR+60*US)]))
    if native_input_version==2:ticks=sorted(set(ticks)|set(range(initial_us,end_us+HOUR,HOUR)))
    if any(t<initial_us or t>end_us for t in ticks):raise InputGap('FINITE_WINDOW_TICK_OUTSIDE_SCOPE')
    for f in funding:
        if f.source_us%US:
            raise InputGap('LEDGER_SOURCE_T_SECONDS_CANNOT_REPRESENT_SUBSECOND_SOURCE_WITHOUT_CONTRACT_CHANGE')
        available=(f.source_us//HOUR+1)*HOUR
        normalized.append(dict(fact('rate',f.instrument_id,f.source_us,available,dict(event_us=f.source_us,rate=f.rate),'rate:'+f.event_id),_source_row=raw_rows['funding',f.instrument_id,f.source_us]))
    schemas=[dict(schema_id=k,**deepcopy(v)) for k,v in SCHEMAS.items()]
    roles=['valuation','reservation','decision','permitted_fill','funding_snapshot'];requirements=[]
    finite=FrozenInputs(marks=marks)
    explicit={}
    if mark_selections is not None:
        for dto in mark_selections:
            key=dto['instrument_id'],dto['query_us']
            if key in explicit:raise InputGap('DUPLICATE_MARK_QUERY')
            explicit[key]=deepcopy(dto)
    for t in ticks:
        if t>=economic_end_us:continue
        for i in INSTRUMENTS:
            if mark_selections is None:
                selection=finite.mark(i,t);supported=selection.value is not None
                dto=dict(instrument_id=i,query_us=t,mark_clock_id='mark-clock',roles=roles,status='SUPPORTED' if supported else 'UNKNOWN',
                    source_us=selection.source_us,source_available_us=selection.available_us,
                    source_semantic_key=[i,'archive-mark',selection.source_us] if supported else None,
                    mark_price=text(selection.value) if supported else None,selected_at_us=t,consumer_available_us=t,
                    unknown_reason=None if supported else 'NO_ELIGIBLE_POINT')
            else:
                dto=explicit.pop((i,t),None)
                if dto is None:raise InputGap('EXPLICIT_MARK_QUERY_MISSING')
                supported=dto['status']=='SUPPORTED'
                if supported:
                    match=next((m for m in marks if m.instrument_id==i and m.source_us==dto['source_us']),None)
                    if match is None or exact(match.price)!=exact(dto['mark_price']):raise InputGap('MARK_SELECTION_SOURCE_MISMATCH')
            mf=sl.normalize_mark_selection(dto,'mark',roles)
            if supported:
                mf['_source_row']=raw_rows['mark',i,dto['source_us']]
            else:
                raw.append(dict(kind='unknown-query-specification',instrument_id=i,query_us=t,reason=dto['unknown_reason']))
                mf['_source_row']=len(raw)
            normalized.append(mf)
            for role in roles:
                requirements.append(dict(key=dict(instrument_id=i,clock_id='mark-clock',query_at_us=t,purpose=role),
                    before_slots=[k+':'+str(t) for k in KINDS],for_view=role in ('valuation','reservation')))
    if explicit:raise InputGap('MARK_QUERY_OUTSIDE_DECLARED_DRIVER_TICKS')
    mark=next(f for f in normalized if f['schema_id']=='mark')
    schemas.append(dict(schema_id='mark',kind='mark-selection',view_kind='mark_selection',interval_us=0,
                        fields=[dict(name=c['name'],type=c['cell']['type'],unit='declared_MARK_scenario') for c in mark['cells']]))
    raw_bytes=b''.join(sl.canonical_bytes(v)+b'\n' for v in raw)
    (source/'supplied.jsonl').write_bytes(raw_bytes);raw_sha=hashlib.sha256(raw_bytes).hexdigest()
    for f in normalized:
        f['raw_refs']=[dict(object_id='supplied',raw_sha256=raw_sha,source_row=f.pop('_source_row'))]
    fact_bytes=b''.join(sl.canonical_bytes(v)+b'\n' for v in normalized)
    (source/'facts.jsonl').write_bytes(fact_bytes)
    ref=dict(root_id='source',relative_path='facts.jsonl',sha256=hashlib.sha256(fact_bytes).hexdigest(),bytes=len(fact_bytes),rows=len(normalized))
    scope=dict(ledger_id='qd011-account',trajectory_id='joint',scenario_id='P0')
    common=dict(scope=scope,initial_us=initial_us,end_us=end_us,ticks=ticks,funding_schedule=schedule,
                seed=dict(initial_us=initial_us,forecast=seed_forecast,vol=seed_vol),runtime=RUNTIME,
                input_basis='FINITE_SUPPLIED_NATIVE_PREPARED_FEATURES_NOT_RAW_COVERAGE')
    common.update(native_input_version=native_input_version,native_schema_id=schema,economic_end_us=economic_end_us)
    if native_input_version==2:
        common.pop('seed');common['native_context']=native_context
        common['input_basis']='ACTUAL_NATIVE_CALCULATION_FROM_FROZEN_PREFIX_NOT_RAW_COVERAGE_PROOF'
    defs=definitions(common)
    for a in defs:sl.register_port(a,ControlledPort())
    rules=[]
    for i in INSTRUMENTS:
        pars=dict(fee=dict(role='taker',signed_fraction='0.00075',fee_currency='USDT'),
            multiplier=dict(base_per_contract='0.0001' if i==INSTRUMENTS[0] else '0.01',quantity_unit='contracts'),
            valuation=dict(price_kind='MARK',max_age_us=120*US),sequence=dict(same_time_order='snapshot_before_fills'),
            funding=dict(calendar='explicit_snapshot_list'),booking=dict(policy='explicit_posting_records'),
            finality=dict(policy='explicit_scoped_assertions',authority_id='authority'))
        for kind,params in pars.items():
            rules.append(dict(rule_id=kind+':'+i,kind=kind,instrument_id=i,valid_from_us=0,valid_to_exclusive_us=None,
                available_at_us=0,authority_id='authority',parameters=params,null_reasons={'valid_to_exclusive_us':'OPEN_ENDED_SCENARIO'}))
    config=dict(**scope,instruments=list(INSTRUMENTS),initial_at_us=initial_us,end_exclusive_us=end_us,
        knowledge_end_exclusive_us=end_us+HOUR,initial_cash_usdt='10000',allocation_quantum_usdt='0.000000000000000001',
        rules=rules,expected_snapshots=schedule,ingestion_mode='controlled_adapters',adapters=defs,
        initial_adapter_states=[state(k,dict(timing=unpack(native_context['initial_timing_state'])) if native_input_version==2 and k in ('policy','feedback') else None) for k in KINDS],schedule=[dict(at_us=t,slots=[dict(slot_id=k+':'+str(t),adapter_id=k,phase=n) for n,k in enumerate(KINDS)]) for t in ticks],
        fact_schemas=schemas,initial_context=dict(mode='none',from_us=initial_us,schemas=[]),
        mark_clocks=[dict(instrument_id=i,clock_id='mark-clock',valuation_rule_id='valuation:'+i,multiplier_rule_id='multiplier:'+i,
            source_delay_us=60*US,max_source_age_us=120*US,max_available_age_us=60*US) for i in INSTRUMENTS],
        mark_view_bindings=[dict(instrument_id=i,clock_id='mark-clock') for i in INSTRUMENTS],mark_requirements=requirements,
        limits=deepcopy(sl.LIMITS),random_source='NONE')
    catalogue=dict(namespace='qf009.raw-catalogue',schema_version=1,catalogue_id='qd011-finite',fact_store=ref,qualification_ref=sl.digest(common),
        objects=[dict(object_id='supplied',root_id='source',instrument_id=INSTRUMENTS[0],sha256=raw_sha,bytes=len(raw_bytes),relative_path='supplied.jsonl',
            format='derived_native_v2_jsonl' if native_input_version==2 else 'synthetic_jsonl',source_row_basis='physical_line',original_time_unit='microseconds',retrieved_at_us=None,null_reasons={'retrieved_at_us':'UNKNOWN_RETRIEVAL'})])
    request=dict(namespace=sl.NS,schema_version=3,profile=sl.PROFILE,request_id='create',config=config,raw_catalogue=catalogue,
        fact_store=ref,source_roots=[dict(root_id='source',path=str(source.resolve()))],store_root=str(path/'store'))
    sl.create(request)
    return Continuous(sl.Ledger(path/'store'))


def scan(ledger,view,component,*,limit=64):
    token=None
    while True:
        page=ledger.scan(dict(view_sha256=view['view_sha256'],component=component,filter=dict(kind='all'),after=token,
            limit=limit,null_reasons={} if token else {'after':'START_OF_COMPONENT'}))
        yield from page['items'];token=page['next']
        if token is None:return


class Continuous:
    def __init__(self,ledger):self.ledger=ledger

    def advance(self,through_us):
        # Keep every same-time phase atomic without serializing several hours'
        # registry/frames into one large temporary journal. This does not grant
        # extra source input, a retry, or a second opportunity within a tick.
        times=[t['at_us'] for t in self.ledger.config['schedule']]
        if through_us not in times:
            raise InputGap('DRIVER_CUTOFF_MUST_BE_A_DECLARED_TICK')
        lower=self.ledger.head['cutoff']['at_us'] if self.ledger.head['committed_seq'] else self.ledger.config['initial_at_us']-1
        due=[t for t in times if lower<t<=through_us]
        if not due:raise InputGap('NO_NEW_DECLARED_TICK')
        for at in due:
            receipt=self.ledger.advance(dict(request_id='advance:'+str(at),expected_audit_prefix=self.ledger.head['audit_prefix'],
                                            through_us=at,imported=[],generated=[]))
        return receipt

    def view(self,at_us):
        slots=next(len(t['slots']) for t in self.ledger.config['schedule'] if t['at_us']==at_us)
        return self.ledger.as_known(dict(cutoff=dict(at_us=at_us,slot=slots)))

    def states(self,at_us):
        return {s['adapter_id']:validate(s) for s in scan(self.ledger,self.view(at_us),'adapter_states')}

    def restore_checkpoint(self):
        cp=self.ledger.checkpoint(dict(expected_head=self.ledger.head['audit_prefix']))
        root=self.ledger.root;prefix=self.ledger.head['audit_prefix'];self.ledger.close()
        sl.restore(dict(checkpoint=cp,expected_committed_head=prefix,store_root=str(root)))
        self.ledger=sl.Ledger(root)
        return cp
