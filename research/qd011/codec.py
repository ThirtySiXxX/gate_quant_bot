"""Deterministic QD011 state/float codec. No host reads during evaluation."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Context, localcontext, ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow
from fractions import Fraction
import math
from research.qd009 import streaming_ledger as sl
from src.execution_timing import ExecutionTiming, TimingConfig, TimingDecision, TimingState
from src.strategy_execution import ExecutionPlan, record_fill
from research.qd010.economic_inputs import exact, text, InputGap

KINDS = ('environment','execution','feedback','policy','reserve')
STATE_CONTRACT = sl.digest(dict(name='qd011.state.v1',version=1,kinds=list(KINDS),float_codec='finite-f64-hex-v1'))


def pack(v):
    if type(v) is float:
        if not math.isfinite(v):
            raise InputGap('NONFINITE_NATIVE_STATE')
        return {'f64':v.hex()}
    if type(v) in (tuple,list):
        return [pack(x) for x in v]
    if type(v) is dict:
        return {k:pack(x) for k,x in v.items()}
    if v is None or type(v) in (str,int,bool):
        return v
    raise InputGap('UNSUPPORTED_NATIVE_STATE_TYPE')


def unpack(v):
    if type(v) is dict:
        if set(v)=={'f64'}:
            f=float.fromhex(v['f64'])
            if not math.isfinite(f) or f.hex()!=v['f64']:
                raise InputGap('NONCANONICAL_F64')
            return f
        return {k:unpack(x) for k,x in v.items()}
    return [unpack(x) for x in v] if type(v) is list else v


def projection(v):
    v=exact(v)
    f=float(v)
    if not math.isfinite(f) or (v and not f):
        raise InputGap('UNSUPPORTED_NUMERIC_PROJECTION')
    error=abs(Fraction.from_float(f)-v)
    if error>Fraction('0.000000000001')*max(1,abs(v)):
        raise InputGap('NUMERIC_BOUND_EXCEEDED')
    return f


def native_context():
    c=Context(prec=50,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,capitals=1,clamp=0)
    for key in c.traps:
        c.traps[key]=key in (InvalidOperation,DivisionByZero,Overflow)
    c.clear_flags()
    return localcontext(c)


def state(kind,data=None,episodes=()):
    s=dict(adapter_id=kind,contract_sha256=STATE_CONTRACT,tracked_episode_ids=sorted(set(episodes)),
           value=dict(version=1,kind=kind,data=pack(data or {})))
    s['state_sha256']=sl.digest(s)
    return s


def validate(s):
    sl.shape(s,'adapter_id contract_sha256 tracked_episode_ids value state_sha256')
    sl.need(s['adapter_id'] in KINDS and s['contract_sha256']==STATE_CONTRACT,'INPUT_BINDING_MISMATCH')
    sl.shape(s['value'],'version kind data')
    sl.need(s['value']['version']==1 and s['value']['kind']==s['adapter_id'],'INPUT_BINDING_MISMATCH')
    sl.need(s['state_sha256']==sl.digest({k:v for k,v in s.items() if k!='state_sha256'}),'INPUT_BINDING_MISMATCH')
    data=unpack(s['value']['data']);sl.need(type(data) is dict,'INPUT_BINDING_MISMATCH')
    allowed={'environment':{'episodes','funding','heads'},'execution':{'fills','risk_status'},
             'feedback':{'source_policy','timing','delivered','waiting','completed','seen_fills','fill_receipts'},
             'policy':{'timing','decisions','basket_status'},'reserve':set()}
    sl.need(set(data)<=allowed[s['adapter_id']],'INPUT_BINDING_MISMATCH')
    for amount in data.get('delivered',{}).values():exact(amount)
    if 'timing' in data:
        t=ExecutionTiming();t.restore(data['timing'])
        sl.need(pack(t.dump())==pack(data['timing']),'INPUT_BINDING_MISMATCH')
    return data


def plan_wire(plan):
    return pack(asdict(plan))


def plan_read(w):
    d=unpack(w);d['decision']=TimingDecision(**d['decision']);d['timing_config']=TimingConfig(**d['timing_config'])
    return ExecutionPlan(**d)


def feedback(timing,symbol,plan,feature,delta,*,closed=False,direction=0,entry_price=0,net=None):
    """Predict every native field independently; publish only a matching candidate."""
    before=timing.dump();candidate=ExecutionTiming();candidate.restore(before)
    old=deepcopy(before.get(symbol,asdict(TimingState())))
    amount=projection(delta);r=old['session_pnl']+amount
    if not math.isfinite(r):
        raise InputGap('NONFINITE_NATIVE_RECURRENCE')
    error=None
    if closed:
        net=exact(net)
        sign=lambda x:(x>0)-(x<0)
        error=Fraction.from_float(r)-net
        if sign(r)!=sign(net) or abs(error)>Fraction('0.000000000001')*max(1,abs(net)):
            raise InputGap('R01_R04_COMPLETION_SIGN_OR_ERROR')
    expected=deepcopy(before)
    old.update(last_fill_bar=feature['bar_ts'],session_pnl=r)
    if entry_price>0 and old['entry_price']==0:
        old.update(entry_price=entry_price,best_close=entry_price)
    if closed:
        if r<0:
            old.update(blocked_side=direction,rearm_price=float(feature['recent_high' if direction>0 else 'recent_low']))
        old.update(session_pnl=0.,entry_price=0.,best_close=0.)
    expected[symbol]=old
    with native_context():
        record_fill(candidate,symbol,plan,feature,entry_price=entry_price,pnl=amount,closed=closed,direction=direction)
    if pack(candidate.dump())!=pack(expected):
        raise InputGap('R04_FULL_NATIVE_STATE_MISMATCH')
    timing.restore(candidate.dump())
    return dict(delta=text(delta),projected=amount.hex(),pre_reset=r.hex(),
                exact_error=text(error) if error is not None else None,
                before=pack(before),after=pack(candidate.dump()))
