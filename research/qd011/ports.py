"""Pinned stateless ports. All information comes from the controlled packet.

Order: environment -> execution -> feedback -> policy -> reserve. No ambient
filesystem/time/network access; no financial reducer or external cutoff read.
"""
from copy import deepcopy
from fractions import Fraction
import math
import numpy as np
import numpy.rec  # Eager dependency admission; lazy file imports are forbidden in evaluate.
import pandas as pd
from numpy.linalg import eigvalsh
import sys
from src import portfolio as pf, strategy_signals, strategy_execution as sx
from src.execution_timing import ExecutionTiming, TimingConfig
from src.position_sizing import EntrySizingBook
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import (INSTRUMENTS, SYMBOLS, MULTIPLIERS, HOUR, US,
    FEE, SLIP, G, exact, text, InputGap, Selection, pending_reserve, execution_boundary)
from research.qd010.joint_native_bridge import research_config, JointNativeBridge, Order
from .codec import state, validate, pack, unpack, projection, plan_wire, plan_read, feedback, native_context, validate_context

INTENT_CONTRACT=sl.digest({'name':'qd011.native-intent.v1','fields':['action','plan','price','native_target','basket','decision_cutoff']})
RUNTIME=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__)


def selected(p,kind):
    return [x['value'] for s in p['economic_inputs'] for x in s['items'] if x['kind']==kind]


def facts(p,schema):
    return [dict(instrument_id=f['instrument_id'],at=f['economic_at_us'],available=f['scenario_available_at_us'],
                 key=f['fact_key'],**{c['name']:c['cell'].get('value') for c in f['cells']})
            for f in p['permitted_facts'] if f['schema_id']==schema]


def native_facts(p):
    return facts(p,p['causal_config'].get('native_schema_id','native'))


def timing_feature(f,v2=False):
    feature={k:projection(f[k]) for k in ('quality','extension','close','atr','recent_high','recent_low')}
    feature.update(bar_ts=f['at']/US,bar_seconds=projection(f['bar_seconds']) if v2 else 3600.,
                   long_run=f['long_run'],short_run=f['short_run'])
    if v2:feature.update(breakout_long=f['breakout_long'],breakout_short=f['breakout_short'])
    return feature


def prepared_v2(p):
    """Replay available observations onto the actual closed native warmup cache."""
    cfg=p['causal_config'];at=p['slot']['at_us']
    prepared=validate_context(cfg['native_context'],cfg['initial_us']);latest={}
    for i,symbol in zip(INSTRUMENTS,SYMBOLS):
        data=prepared[symbol]
        fs=sorted((f for f in native_facts(p) if f['instrument_id']==i and f['available']<=at),key=lambda f:f['at'])
        for f in fs:
            if any(f.get(k) is None for k in ('short','main','vol','carry','risk','efficiency','range_vol_ratio',
                'regime','regime_open_us','regime_available_us','cov_btc_btc','cov_eth_eth','cov_cross','cov_available_us',
                'quality','extension','close','atr','recent_high','recent_low','bar_seconds','long_run','short_run','breakout_long','breakout_short')):
                raise InputGap('INCOMPLETE_NATIVE_V2_OBSERVATION')
            if f['main_open_us']+4*HOUR>f['available'] or f['regime_available_us']>f['available'] or f['cov_available_us']>f['available']:
                raise InputGap('FUTURE_NATIVE_V2_FEATURE')
            short=dict(short_f=projection(f['short']),adaptive_risk_multiplier=projection(f['risk']),
                       adaptive_efficiency_ratio=projection(f['efficiency']),adaptive_vol_ratio=projection(f['range_vol_ratio']),
                       timing_features=timing_feature(f,True))
            ts=f['at']/US
            if ts==data['short_ts'][-1]:
                if any(data[k][-1]!=v for k,v in short.items()):raise InputGap('MUTATED_INITIAL_NATIVE_CACHE')
            elif ts==data['short_ts'][-1]+3600:
                data['short_ts'].append(ts)
                for k,v in short.items():data[k].append(v)
            else:raise InputGap('NATIVE_V2_SHORT_GRID_GAP_OR_REWIND')
            for name,ts,values,width in (
                ('main',f['main_open_us']/US,dict(main_f=projection(f['main']),vol_ann=projection(f['vol']),carry_f=projection(f['carry'])),14400),
                ('regime',f['regime_open_us']/US,dict(regime=f['regime']),86400)):
                previous=data[name+'_ts'][-1]
                if ts==previous:
                    if any(data[k][-1]!=v for k,v in values.items()):raise InputGap('MUTATED_CLOSED_NATIVE_'+name.upper())
                elif ts==previous+width:
                    data[name+'_ts'].append(ts)
                    for k,v in values.items():data[k].append(v)
                else:raise InputGap('NATIVE_V2_'+name.upper()+'_GRID_GAP_OR_REWIND')
        if fs and fs[-1]['at']==at-HOUR:latest[i]=fs[-1]
    return prepared,latest


def peer(p,kind):
    return validate(next(s for s in p['peer_states'] if s['adapter_id']==kind))


def live(p):
    return selected(p,'live_lot')


def quantity(lot):
    return sum(u['unit_end']-u['unit_start'] for u in lot['live_ranges'])


def marks(p):
    at=p['slot']['at_us'];result={}
    for i in INSTRUMENTS:
        q=[s for s in selected(p,'query_status') if s['key']['instrument_id']==i and s['key']['purpose']=='valuation']
        s=max(q,key=lambda s:s['key']['query_at_us']) if q else None
        supported=s and s['status']=='SUPPORTED' and at-s['source_at_us']<=120*US and at-s['source_available_at_us']<=60*US
        result[i]=Selection(exact(s['mark_price']) if supported else None,at,
            s['source_at_us'] if supported else None,s['source_available_at_us'] if supported else None,
            (s['fact_key'],) if s else (),None if supported else 'MARK_UNKNOWN')
    return result


def active(p):
    return [o for o in selected(p,'order') if o['status'] in ('pending','partially_filled')]


def order_object(o):
    a=o['intent'];payload=a['payload']
    return Order(a['order_id'],a['decision_id'],a['instrument_id'],a['action'],1 if a['direction']=='long' else -1,
                 a['requested_contracts'],a['submitted_at_us'],exact(payload['price']),exact(payload['native_target']))


def finance(p,*,ignore_pending=False):
    b=p['before']['balance'];ms=marks(p);positions={i:0 for i in INSTRUMENTS}
    margin=Fraction(0);fees=Fraction(0)
    for l in live(p):
        q=quantity(l);i=l['instrument_id'];positions[i]+=q*(1 if l['direction']=='long' else -1)
        margin+=q*exact(l['multiplier'])*exact(l['entry_price'])/200
    known=all(b[k] is not None for k in ('cash_usdt','liabilities_usdt','unrealized_usdt','economic_equity_usdt'))
    for i,q in positions.items():
        if q and ms[i].value is None:
            known=False
        elif q:
            fees+=abs(q)*exact(MULTIPLIERS[i])*ms[i].value*(1+SLIP)*FEE
    pending=Fraction(0) if ignore_pending else sum((pending_reserve(o['intent']['requested_contracts'],
        o['intent']['instrument_id'],o['intent']['payload']['price']) for o in active(p) if o['intent']['action']=='open'),Fraction(0))
    budget=(exact(b['cash_usdt'])-exact(b['liabilities_usdt'])+min(exact(b['unrealized_usdt']),0)-margin-fees-pending) if known else None
    return dict(equity=exact(b['economic_equity_usdt']) if known else None,budget=budget,positions=positions,marks=ms,
                held_margin=margin,held_fees=fees if known else None)


def body(p,typ,id,inst,**fields):
    cfg=p['causal_config'];at=p['slot']['at_us']
    return dict(record_type=typ,record_id=id,revision=1,instrument_id=inst,trajectory_id=cfg['scope']['trajectory_id'],
                scenario_id=cfg['scope']['scenario_id'],evidence_mode='SCENARIO',source_time_precision='microseconds',
                available_at_us=at,null_reasons={},**fields)


def allocation(p,oid,total,ranges,inst):
    c=p['causal_config']['scope'];values=sl.allocate(total,[u['unit_end']-u['unit_start'] for u in ranges],Fraction('0.000000000000000001'))
    return [dict(u,allocation_id=sl.digest([c['ledger_id'],c['trajectory_id'],c['scenario_id'],inst,oid,u['lot_id'],u['unit_start'],u['unit_end']]),
                 signed_cash_usdt=v) for u,v in zip(ranges,values)]


def posting(p,id,oid,amount,ranges,inst):
    r=body(p,'Posting',id,inst,obligation_id=oid,signed_amount_usdt=text(amount),booking_at_us=p['slot']['at_us'],
           booking_known_at_us=p['slot']['at_us'],booking_basis='scenario',booking_rule_id='booking:'+inst,
           corrects_posting_id=None,allocations=allocation(p,oid,amount,ranges,inst))
    r['null_reasons']={'corrects_posting_id':'NOT_APPLICABLE'}
    return r


def native_inputs(p):
    """Supplied causal native feature observations, not a constant action script."""
    if p['causal_config'].get('native_input_version',1)==2:
        prepared,latest=prepared_v2(p);cfg=research_config();at=p['slot']['at_us']
        signals={}
        for i,symbol in zip(INSTRUMENTS,SYMBOLS):
            if i in latest:
                sig=strategy_signals.signal_at(symbol,prepared[symbol],at/US,cfg)
                if sig is not None:signals[symbol]=sig
        return signals,latest
    at=p['slot']['at_us'];seed=p['causal_config']['seed'];cfg=research_config();native={};latest={}
    for i,symbol in zip(INSTRUMENTS,SYMBOLS):
        fs=sorted((f for f in native_facts(p) if f['instrument_id']==i and f['available']<=at),key=lambda f:f['at'])
        if not fs or fs[-1]['at']!=at-HOUR:
            continue
        start=seed['initial_us'];base=projection(seed['forecast']);vol=projection(seed['vol'])
        data=dict(short_ts=[(start-(301-j)*HOUR)/US for j in range(300)],
                  main_ts=[(start-(301-j)*4*HOUR)/US for j in range(300)],regime_ts=[(start-HOUR*24)/US],
                  short_f=[base]*300,main_f=[base]*300,vol_ann=[vol]*300,carry_f=[0.]*300,
                  regime=['range'],adaptive_risk_multiplier=[1.]*300,adaptive_efficiency_ratio=[1.]*300,
                  adaptive_vol_ratio=[1.]*300,timing_features=[{}]*300)
        valid=True
        for f in fs:
            names=('short','main','vol','carry','risk','quality','extension','close','atr','recent_high','recent_low')
            if any(f[k] is None for k in names):
                valid=False;break
            feature={k:projection(f[k]) for k in ('quality','extension','close','atr','recent_high','recent_low')}
            feature.update(bar_ts=f['at']/US,bar_seconds=3600.,long_run=f['long_run'],short_run=f['short_run'])
            data['short_ts'].append(f['at']/US);data['short_f'].append(projection(f['short']))
            for key,value in [('adaptive_risk_multiplier',projection(f['risk'])),('adaptive_efficiency_ratio',1.),('adaptive_vol_ratio',1.),('timing_features',feature)]:
                data[key].append(value)
            main_us=f['main_open_us']
            if main_us+4*HOUR>f['available']:
                raise InputGap('FUTURE_MAIN_FEATURE')
            if main_us/US>data['main_ts'][-1]:
                data['main_ts'].append(main_us/US);data['main_f'].append(projection(f['main']))
                data['vol_ann'].append(projection(f['vol']));data['carry_f'].append(projection(f['carry']))
            elif data['main_f'][-1]!=projection(f['main']) or data['vol_ann'][-1]!=projection(f['vol']):
                raise InputGap('MUTATED_ALREADY_CLOSED_MAIN_FEATURE')
        if valid:
            sig=strategy_signals.signal_at(symbol,data,at/US,cfg)
            if sig is not None:
                native[symbol]=sig;latest[i]=fs[-1]
    return native,latest


class ControlledPort:
    def validate_input(self,p):
        sl.shape(p,'slot slot_id causal_policy_sha256 permitted_facts before economic_inputs peer_states previous_invocation prior_state causal_config')
        validate(p['prior_state'])
        sl.need(p['causal_config']['runtime']==RUNTIME,'UNSUPPORTED_GENERATOR')
        sl.need(all(f['scenario_available_at_us']<=p['slot']['at_us'] for f in p['permitted_facts']),'FUTURE_DEPENDENCY')
        for s in p['peer_states']:validate(s)

    def validate_state(self,s):
        validate(s)

    def validate_output(self,r):
        sl.shape(r,'outcome events decisions orders order_transitions reserve_dependencies next_state')
        validate(r['next_state']);sl.strict_json(r)
        for b in r['events']:sl.normalize_body(b)
        for o in r['orders']:
            sl.need(o['payload_contract_sha256']==INTENT_CONTRACT,'INPUT_BINDING_MISMATCH')
            plan_read(o['payload']['plan'])

    def evaluate(self,p):
        kind=p['prior_state']['adapter_id'];d=validate(p['prior_state'])
        r=dict(outcome='noop',events=[],decisions=[],orders=[],order_transitions=[],reserve_dependencies=[],next_state=None)
        episodes=set(p['prior_state']['tracked_episode_ids'])
        with native_context():
            globals()['_'+kind](p,d,r,episodes)
        r['outcome']='emit' if r['events'] else 'noop'
        r['next_state']=state(kind,d,episodes)
        return r


def _policy(p,d,r,episodes):
    at=p['slot']['at_us'];cfg=p['causal_config'];fback=peer(p,'feedback')
    if fback.get('source_policy') not in (None,p['prior_state']['state_sha256']):
        raise InputGap('NATIVE_STATE_HANDOFF_MISMATCH')
    timing=ExecutionTiming();timing.restore(fback.get('timing',d.get('timing',{})))
    d['timing']=timing.dump();d['decisions']=[]
    if cfg.get('native_input_version',1)==2:d.pop('native_receipt',None)
    economic_end=cfg.get('economic_end_us',cfg['end_us'])
    if at>=economic_end or at%HOUR:
        return
    native,latest=native_inputs(p);f=finance(p);plans={};allocation=None
    if len(native)==2 and all(latest[i]['cov_cross'] is not None for i in INSTRUMENTS) and f['equity'] is not None and f['equity']>0:
        vols=[native[s].vol_annual for s in SYMBOLS];cross=[exact(latest[i]['cov_cross']) for i in INSTRUMENTS]
        if cross[0]!=cross[1]:raise InputGap('COVARIANCE_CROSS_MISMATCH')
        if cfg.get('native_input_version',1)==2:
            rows=[latest[i] for i in INSTRUMENTS]
            if any(rows[0][k]!=rows[1][k] for k in ('cov_btc_btc','cov_eth_eth','cov_available_us')):
                raise InputGap('JOINT_NATIVE_COVARIANCE_MISMATCH')
            a=np.array([[projection(rows[0]['cov_btc_btc']),projection(cross[0])],
                        [projection(cross[0]),projection(rows[0]['cov_eth_eth'])]])
            d['native_receipt']=dict(version=2,decision_us=at,cov_available_us=rows[0]['cov_available_us'],covariance=a.tolist(),sizing_vol=vols,
                regime={s:latest[i]['regime'] for i,s in zip(INSTRUMENTS,SYMBOLS)},
                efficiency={s:native[s].efficiency_ratio for s in SYMBOLS},
                range_vol_ratio={s:native[s].range_vol_ratio for s in SYMBOLS},
                warmup_context_sha256=cfg['native_context']['context_sha256'])
        else:a=np.array([[vols[0]**2,projection(cross[0])],[projection(cross[0]),vols[1]**2]])
        if not np.isfinite(a).all() or np.any(np.diag(a)<=0) or np.min(eigvalsh(a)) < -1e-12:
            raise InputGap('INVALID_NATIVE_COVARIANCE')
        allocation=pf.allocate_portfolio(native,projection(f['equity']),pd.DataFrame(a,index=SYMBOLS,columns=SYMBOLS),research_config())
    candidates=[];order_plans={};waiting=fback.get('waiting',{})
    for i,s in zip(INSTRUMENTS,SYMBOLS):
        if s not in native:continue
        sig=native[s];held=f['positions'][i];price=exact(latest[i]['close']);current=held*exact(MULTIPLIERS[i])*price
        if not held and i in waiting:continue  # No timing.decide while awaiting exact finality.
        if allocation is None:
            decision=timing.decide(s,projection(current),projection(current),sig.combined_forecast,sig.short_forecast,sig.main_forecast,
                                   sig.timing_feature,TimingConfig(**research_config().execution_timing).for_symbol(s))
            if not held or not decision.force_rebalance or decision.target_notional!=0:continue
            plan=sx.ExecutionPlan(decision,TimingConfig(**research_config().execution_timing).for_symbol(s),0.,0.,True,False,False,False)
            actions=[('close','long' if held>0 else 'short',abs(held))]
        else:
            plan=sx.decide_execution(s,allocation.targets[s],sig,projection(current),projection(f['equity']),research_config(),
                                     timing,EntrySizingBook(),allow_increase=f['budget'] is not None)
            actions,_=sx.build_order_plan(s,plan,'long' if held>0 else 'short' if held<0 else None,abs(held),projection(price),
                dict(quanto_multiplier=projection(MULTIPLIERS[i]),order_size_min=1),projection(FEE),projection(SLIP*10000))
            ratio=Fraction.from_float(plan.target_notional)/(price*exact(MULTIPLIERS[i]))
            if round(abs(ratio))!=sx.notional_to_contracts(plan.target_notional,projection(price),projection(MULTIPLIERS[i])):
                raise InputGap('NATIVE_QUANTITY_ROUND_DISAGREEMENT')
        for action,side,q in actions:
            if execution_boundary(at)>=economic_end:continue
            if action=='open' and held and held*(1 if side=='long' else -1)<0:continue
            o=Order('', '', i,action,1 if side=='long' else -1,q,at,price,Fraction.from_float(plan.target_notional))
            candidates.append(o);order_plans[i]=plan
    pending=active(p)
    if pending:
        opposing=any(o.action!='open' or any(x['intent']['instrument_id']==o.instrument_id and
            (x['intent']['direction']=='long')!=(o.side>0) for x in pending) for o in candidates)
        if opposing:
            r['order_transitions']=[dict(order_id=x['intent']['order_id'],at=p['slot'],status='cancelled',fill_keys=[],reason='OPPOSING_WHOLE_BASKET') for x in pending]
        else:candidates=[o for o in candidates if o.action!='open']
    inc=[o for o in candidates if o.action=='open'];prices={i:exact(v['close']) for i,v in latest.items()}
    reason=JointNativeBridge._validate(None,inc,f,prices) if inc and len(prices)==2 else 'NO_INCREASE'
    d['basket_status']=reason
    candidates=[o for o in candidates if o.action!='open' or reason=='ADMITTED']
    for ordinal,o in enumerate(candidates):
        i=o.instrument_id;plan=order_plans[i]
        did=sl.business_id(cfg['scope'],i,'decision',at,p['slot_id'],ordinal)
        oid=sl.business_id(cfg['scope'],i,'order',at,p['slot_id'],ordinal)
        payload=dict(action=o.action,plan=plan_wire(plan),price=text(o.price),native_target=text(o.native_target),
                     basket='basket:'+str(at),decision_cutoff=dict(at_us=at,slot=p['slot']['slot']-1))
        r['decisions'].append(dict(decision_id=did,at_us=at,instrument_id=i,order_ids=[oid],
            input_projection_sha256=sl.digest(p),prior_adapter_state_sha256=p['prior_state']['state_sha256'],
            intent_contract_sha256=INTENT_CONTRACT,intent=payload))
        r['orders'].append(dict(order_id=oid,decision_id=did,instrument_id=i,action=o.action,direction='long' if o.side>0 else 'short',
            requested_contracts=o.quantity,submitted_at_us=at,eligible_at_us=execution_boundary(at),expires_at_us=execution_boundary(at)+1,
            payload_contract_sha256=INTENT_CONTRACT,payload=payload))
        d['decisions'].append(dict(instrument=i,decision_id=did,order_id=oid))
    d['timing']=timing.dump()


def _execution(p,d,r,episodes):
    at=p['slot']['at_us'];cfg=p['causal_config'];orders=[o for o in active(p) if o['intent']['eligible_at_us']<=at]
    d['fills']=[];d['risk_status']='NO_DUE_BASKET'
    if not orders:return
    if at>=cfg.get('economic_end_us',cfg['end_us']):
        d['risk_status']='ECONOMIC_WINDOW_CLOSED'
        r['order_transitions']=[dict(order_id=o['intent']['order_id'],at=p['slot'],status='cancelled',fill_keys=[],reason='ECONOMIC_WINDOW_CLOSED') for o in orders]
        return
    if any(o['intent']['eligible_at_us']!=at for o in orders):raise InputGap('MISSED_SINGLE_EXECUTION_BOUNDARY')
    prices={f['instrument_id']:exact(f['open_price']) for f in facts(p,'open') if f['at']==at}
    closed={f['instrument_id']:f for f in native_facts(p) if f['at']==at-HOUR}
    pending=[order_object(o) for o in orders if o['intent']['action']=='open'];f=finance(p,ignore_pending=True)
    needed={o.instrument_id for o in pending}|{i for i,q in f['positions'].items() if q}
    status=('EXECUTION_INPUT_MISSING' if needed-set(prices) else JointNativeBridge._validate(None,pending,f,prices,filling=True)) if pending else 'ADMITTED'
    d['risk_status']=status
    capacities={i:int(exact(v['volume'])*Fraction('0.001')) for i,v in closed.items()}
    for ordinal,o in enumerate(sorted(orders,key=lambda o:(o['intent']['action']=='open',INSTRUMENTS.index(o['intent']['instrument_id'])))):
        a=o['intent'];i=a['instrument_id'];opening=a['action']=='open'
        permitted=not opening or status=='ADMITTED'
        q=min(a['requested_contracts'],capacities.get(i,0)) if permitted and i in prices else 0
        if not opening:q=min(q,abs(f['positions'][i]))
        capacities[i]=capacities.get(i,0)-q;keys=[]
        if q:
            direction=1 if a['direction']=='long' else -1;signed=q*direction*(1 if opening else -1)
            price=prices[i]*(1+SLIP if signed>0 else 1-SLIP)
            id=sl.business_id(cfg['scope'],i,'fill',at,p['slot_id'],len(r['events']))
            if opening:
                own=next((l for l in live(p) if l['instrument_id']==i),None)
                eid=own['episode_id'] if own else 'episode:'+id
                ranges=[dict(lot_id='lot:'+id,episode_id=eid,unit_start=0,unit_end=q)]
            else:
                ranges=[];left=q
                for l in sorted((l for l in live(p) if l['instrument_id']==i),key=lambda l:(l['opened_at_us'],l['lot_id'])):
                    for u in l['live_ranges']:
                        take=min(left,u['unit_end']-u['unit_start'])
                        if take:ranges.append(dict(u,unit_end=u['unit_start']+take));left-=take
                    if not left:break
                if left:raise InputGap('CLOSE_RANGE_BINDING_MISSING')
                eid=ranges[0]['episode_id']
            fill=body(p,'Fill',id,i,order_id=a['order_id'],decision_id=a['decision_id'],decision_at_us=a['submitted_at_us'],
                filled_at_us=at,sequence=ordinal+1,signed_contracts=signed,fill_price=text(price),multiplier=MULTIPLIERS[i],
                multiplier_rule_id='multiplier:'+i,fee_fraction=text(FEE),fee_rule_id='fee:'+i,liquidity_role='taker',
                role_basis='scenario',fee_currency='USDT',fee_obligation_id='fee:'+id)
            r['events'].append(fill);keys=[sl.key_of(fill)]
            fee=-q*exact(MULTIPLIERS[i])*price*FEE
            pid=sl.business_id(cfg['scope'],i,'posting',at,p['slot_id'],len(r['events']))
            r['events'].append(posting(p,pid,'fee:'+id,fee,ranges,i))
            d['fills'].append(dict(fill=fill,episode_id=eid,plan=a['payload']['plan'],order_payload=a['payload']))
            episodes.add(eid)
        r['order_transitions'].append(dict(order_id=a['order_id'],at=p['slot'],status='filled' if q==a['requested_contracts'] else 'cancelled',
            fill_keys=keys,reason='FILLED' if q==a['requested_contracts'] else 'SINGLE_OPPORTUNITY_RESIDUAL_CANCELLED:'+status))


def _feedback(p,d,r,episodes):
    at=p['slot']['at_us'];policy=peer(p,'policy');policy_state=next(x for x in p['peer_states'] if x['adapter_id']=='policy')
    source=policy_state['state_sha256']
    timing=ExecutionTiming()
    timing.restore(policy.get('timing',{}) if source!=d.get('source_policy') else d.get('timing',{}))
    d['source_policy']=source
    delivered=d.setdefault('delivered',{});waiting=d.setdefault('waiting',{});completed=d.setdefault('completed',{})
    fills=peer(p,'execution').get('fills',[]);seen=d.setdefault('seen_fills',[]);receipts=d.setdefault('fill_receipts',{})
    changes=selected(p,'financial');slices=selected(p,'slice');obligations=selected(p,'obligation')
    latest={i:max((f for f in native_facts(p) if f['instrument_id']==i and f['at']+HOUR<=at),key=lambda f:f['at'],default=None) for i in INSTRUMENTS}
    for info in fills:
        b=info['fill'];fid=b['record_id'];i=b['instrument_id'];eid=info['episode_id']
        if fid in seen:continue
        if not any(sl.key_of(x)==sl.key_of(b) for x in changes):raise InputGap('FEEDBACK_FILL_NOT_ACCEPTED')
        own=[s for s in slices if s['closing_fill_id']==fid]
        price_cash=sum((exact(s['realized_price_pnl_usdt']) for s in own),Fraction(0))
        fee_posts=[x for x in changes if x['record_type']=='Posting' and x['obligation_id']==b['fee_obligation_id']]
        if len(fee_posts)!=1:raise InputGap('ACTUAL_FEE_POSTING_MISSING')
        cash=price_cash+exact(fee_posts[0]['signed_amount_usdt'])
        plan=plan_read(info['plan']);symbol=SYMBOLS[INSTRUMENTS.index(i)];record=None
        feature=latest[i]
        if feature is None or feature['at']!=at-HOUR:raise InputGap('ACTUAL_FILL_CLOSED_FEATURE_MISSING')
        tf=timing_feature(feature,p['causal_config'].get('native_input_version',1)==2)
        if plan.timing_config.enabled:
            record=feedback(timing,symbol,plan,tf,cash,entry_price=projection(b['fill_price']) if info['order_payload']['action']=='open' else 0.)
            delivered[eid]=text(exact(delivered.get(eid,'0'))+cash)
        receipts[fid]=dict(episode_id=eid,fill_key=sl.key_of(b),plan=info['plan'],feature=pack(tf),
                          direction=1 if b['signed_contracts']<0 else -1,delta=text(cash),recurrence=record,
                          decision_cutoff=info['order_payload']['decision_cutoff'])
        if info['order_payload']['action']!='open' and not any(l['instrument_id']==i for l in live(p)):
            waiting[i]=dict(episode_id=eid,close_fill_id=fid)
        seen.append(fid);episodes.add(eid)
    for i,w in list(waiting.items()):
        eid=w['episode_id'];ss=[s for s in slices if s['episode_id']==eid]
        assertions=[x for x in changes if x['record_type']=='CompletenessAssertion' and x['scope']['episode_id']==eid]
        if not assertions:continue
        a=max(assertions,key=lambda a:(a['available_at_us'],a['revision']))
        ownobs=[o for o in obligations if o['obligation_id'] in {z['obligation_id'] for z in a['obligation_revision_refs']}]
        if len(ownobs)!=len(a['obligation_revision_refs']) or any(o['T_usdt'] is None or o['P_usdt']!='0' for o in ownobs):continue
        if {(o['obligation_id'],o['latest_revision']) for o in ownobs}!={(x['obligation_id'],x['revision']) for x in a['obligation_revision_refs']}:continue
        if not ss or any(s[k] is None for s in ss for k in ('realized_price_pnl_usdt','entry_fee_cash_usdt','exit_fee_cash_usdt','funding_cash_usdt')):continue
        if eid in completed:raise InputGap('DUPLICATE_OR_SUPERSEDED_NATIVE_COMPLETION')
        net=sum((exact(s[k]) for s in ss for k in ('realized_price_pnl_usdt','entry_fee_cash_usdt','exit_fee_cash_usdt','funding_cash_usdt')),Fraction(0))
        saved=receipts[w['close_fill_id']];plan=plan_read(saved['plan']);tf=unpack(saved['feature']);s=SYMBOLS[INSTRUMENTS.index(i)]
        rec=feedback(timing,s,plan,tf,net-exact(delivered.get(eid,'0')),closed=True,direction=saved['direction'],net=net) if plan.timing_config.enabled else None
        completed[eid]=dict(net=text(net),delivered=delivered.get(eid,'0'),completion=rec,assertion_key=sl.key_of(a),completed_at_us=at)
        del waiting[i]
    d['timing']=timing.dump()


def _reserve(p,d,r,episodes):
    at=p['slot']['at_us'];cfg=p['causal_config']
    if at>=cfg.get('economic_end_us',cfg['end_us']):return
    ms=marks(p);pending=active(p)
    for i in INSTRUMENTS:
        ls=[l for l in live(p) if l['instrument_id']==i];qs=sum(quantity(l) for l in ls)
        margin=sum((quantity(l)*exact(l['multiplier'])*exact(l['entry_price'])/200 for l in ls),Fraction(0))
        fees=None if qs and ms[i].value is None else qs*exact(MULTIPLIERS[i])*(ms[i].value or 0)*(1+SLIP)*FEE
        for o in pending:
            a=o['intent']
            if a['instrument_id']==i and a['action']=='open':
                n=a['requested_contracts']*exact(MULTIPLIERS[i])*exact(a['payload']['price'])
                margin+=n*(1+G)/200
                if fees is not None:fees+=2*FEE*n*(1+G)+n*G
        id='reserve:'+str(at)+':'+i
        rec=body(p,'Reserves',id,i,effective_at_us=at,known_at_us=at,expires_at_us=min(next(t for t in cfg['ticks'] if t>at),cfg['end_us']),
                 reserved_margin_usdt=text(margin),reserved_fees_usdt=text(fees) if fees is not None else None,
                 excludes_counted_losses_liabilities_and_posted_fees=True)
        if fees is None:rec['null_reasons']={'reserved_fees_usdt':'UNKNOWN_AMOUNT'}
        r['events'].append(rec)
        r['reserve_dependencies'].append(dict(reserve_key=sl.key_of(rec),margin=dict(kind='independent'),
            fees=dict(kind='current_mark',query_key=dict(instrument_id=i,clock_id='mark-clock',query_at_us=at,purpose='reservation')) if qs else dict(kind='independent')))


def _environment(p,d,r,episodes):
    at=p['slot']['at_us'];cfg=p['causal_config'];changes=selected(p,'financial')
    current=live(p);history=d.setdefault('episodes',{});funds=d.setdefault('funding',{});heads=d.setdefault('heads',{})
    for l in current:
        eid=l['episode_id'];episodes.add(eid)
        meta=history.setdefault(eid,dict(instrument=l['instrument_id'],entry=l['opened_at_us'],exit=None,obs=[],posts=[],last_input=l['opened_at_us'],issued=None))
        if 'fee:'+l['opening_fill_id'] not in meta['obs']:meta['obs'].append('fee:'+l['opening_fill_id'])
    for s in selected(p,'slice'):
        eid=s['episode_id']
        if eid in history:
            meta=history[eid];meta['exit']=max(meta['exit'] or 0,s['closed_at_us'])
            if 'fee:'+s['closing_fill_id'] not in meta['obs']:meta['obs'].append('fee:'+s['closing_fill_id'])
    for b in changes:
        if b['record_type']=='Posting':
            for a in b['allocations']:
                if a['episode_id'] in history:
                    m=history[a['episode_id']]
                    if b['record_id'] not in m['posts']:m['posts'].append(b['record_id'])
                    m['last_input']=max(m['last_input'],b['available_at_us'])
        if b['record_type'] in ('Fill','ObligationRevision'):
            oid=b.get('fee_obligation_id',b['record_id'])
            for m in history.values():
                if oid in m['obs']:m['last_input']=max(m['last_input'],b['available_at_us'])
    for item in cfg['funding_schedule']:
        i=item['instrument_id'];id=item['event_id'];ts=item['snapshot_at_us']
        if at==ts and id not in funds:
            ranges=[u for l in current if l['instrument_id']==i for u in l['live_ranges']]
            snap=body(p,'FundingSnapshot',id,i,nominal_settlement_at_us=None,snapshot_at_us=at,snapshot_sequence=None,
                source_t_seconds=at//US,source_record_at_us=at,mapping_rule_id='funding:'+i,obligation_id='ob:'+id,eligible_ranges=ranges)
            snap['null_reasons']={'nominal_settlement_at_us':'UNKNOWN_MAPPING','snapshot_sequence':'UNKNOWN_SEQUENCE'}
            r['events'].append(snap);mark=marks(p)[i]
            signed=sum(quantity(l)*(1 if l['direction']=='long' else -1) for l in current if l['instrument_id']==i)
            funds[id]=dict(instrument=i,ranges=ranges,signed=signed,mark=text(mark.value) if mark.value is not None else None,
                mark_source=mark.source_us,mark_available=mark.available_us,revision=False,posted=False,amount=None,known=None)
            for u in ranges:
                m=history[u['episode_id']]
                if 'ob:'+id not in m['obs']:m['obs'].append('ob:'+id)
        if id not in funds:continue
        f=funds[id];rates=[v for v in facts(p,'rate') if v['event_us']==ts and v['instrument_id']==i]
        if rates and not f['revision'] and f['mark'] is not None and f['ranges']:
            rate=rates[-1];amount=-f['signed']*exact(MULTIPLIERS[i])*exact(f['mark'])*exact(rate['rate'])
            known=rate['available'];f.update(revision=True,amount=text(amount),known=known)
            rev=body(p,'ObligationRevision','ob:'+id,i,origin_id=id,obligation_kind='funding',economic_at_us=ts,known_at_us=known,
                supersedes_revision=None,authority_id='authority',rule_id='funding:'+i,cumulative_signed_total_usdt=text(amount),
                allocations=allocation(p,'ob:'+id,amount,f['ranges'],i),calculation=dict(kind='funding_formula',signed_contracts=f['signed'],
                    multiplier=MULTIPLIERS[i],mark_price=f['mark'],final_rate=rate['rate'],valuation_at_us=f['mark_source'],
                    valuation_available_at_us=f['mark_available'],rate_available_at_us=known,valuation_rule_id='valuation:'+i,multiplier_rule_id='multiplier:'+i))
            rev['null_reasons']={'supersedes_revision':'NOT_APPLICABLE'};r['events'].append(rev)
            for u in f['ranges']:history[u['episode_id']]['last_input']=max(history[u['episode_id']]['last_input'],known)
        if f['revision'] and not f['posted'] and at==f['known']+60*US:
            if exact(f['amount']):
                pid=sl.business_id(cfg['scope'],i,'posting',at,p['slot_id'],len(r['events']))
                r['events'].append(posting(p,pid,'ob:'+id,exact(f['amount']),f['ranges'],i))
                for u in f['ranges']:
                    m=history[u['episode_id']]
                    if pid not in m['posts']:m['posts'].append(pid)
                    m['last_input']=max(m['last_input'],at)
            f['posted']=True
    obs={o['obligation_id']:o for o in selected(p,'obligation')}
    for eid,m in history.items():
        if any(l['episode_id']==eid for l in current) or m['exit'] is None:continue
        own=[obs.get(oid) for oid in m['obs']]
        if any(o is None or o['T_usdt'] is None or o['P_usdt']!='0' for o in own):continue
        if at<max(m['exit'],m['last_input'])+HOUR:continue
        refs=[dict(obligation_id=o['obligation_id'],revision=o['latest_revision']) for o in own]
        signature=sl.digest([refs,sorted(m['posts'])])
        if signature==m['issued']:continue
        if m['issued'] is not None:raise InputGap('POST_COMPLETION_CORRECTION_REQUIRES_NEW_PROTOCOL')
        proof=body(p,'CompletenessAssertion','proof:'+eid,m['instrument'],supersedes_revision=None,authority_id='authority',
            finality_rule_id='finality:'+m['instrument'],scope=dict(instrument_id=m['instrument'],trajectory_id=cfg['scope']['trajectory_id'],
            episode_id=eid,event_kinds=['fill','fee','posting']+(['funding'] if any(o['kind']=='funding' for o in own) else []),
            economic_from_us=m['entry'],economic_to_exclusive_us=m['exit']+1),obligation_revision_refs=refs,
            posting_refs=[dict(posting_id=id,revision=1) for id in m['posts']],asserted_at_us=at,known_at_us=at)
        proof['null_reasons']={'supersedes_revision':'NOT_APPLICABLE'};r['events'].append(proof);m['issued']=signature
