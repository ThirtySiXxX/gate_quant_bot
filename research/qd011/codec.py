"""Deterministic QD011 state/float codec. No host reads during evaluation."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Context, localcontext, ROUND_HALF_EVEN, InvalidOperation, DivisionByZero, Overflow
from fractions import Fraction
import math
import base64
import zlib
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
    raise InputGap('UNSUPPORTED_NATIVE_STATE_TYPE:'+type(v).__name__)


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
             'policy':{'timing','decisions','basket_status','native_receipt'},'reserve':set()}
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


def pack_prepared(v):
    """Preserve actual early native NaNs explicitly; never turn them into zero."""
    if type(v) is float and math.isnan(v):return {'native_unavailable':'INDICATOR_WARMUP'}
    if type(v) is float:return pack(v)
    if isinstance(v,(list,tuple)):return [pack_prepared(x) for x in v]
    if type(v) is dict:return {k:pack_prepared(x) for k,x in v.items()}
    return pack(v)


def unpack_prepared(v):
    if type(v) is dict and v=={'native_unavailable':'INDICATOR_WARMUP'}:return float('nan')
    if type(v) is dict and set(v)=={'f64'}:return unpack(v)
    if type(v) is dict:return {k:unpack_prepared(x) for k,x in v.items()}
    if type(v) is list:return [unpack_prepared(x) for x in v]
    return v


def encode_cache(data):
    raw=sl.canonical_bytes(pack_prepared(data))
    return dict(codec='zlib-json-f64-v1',expanded_bytes=len(raw),sha256=sl.hashlib.sha256(raw).hexdigest(),
                payload=base64.b64encode(zlib.compress(raw,9)).decode('ascii'))


def decode_cache(cache):
    sl.shape(cache,'codec expanded_bytes sha256 payload')
    sl.need(cache['codec']=='zlib-json-f64-v1' and 0<cache['expanded_bytes']<=32*1024**2,'INPUT_BINDING_MISMATCH')
    decoder=zlib.decompressobj();raw=decoder.decompress(base64.b64decode(cache['payload'],validate=True),32*1024**2+1)
    sl.need(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and len(raw)==cache['expanded_bytes']
            and sl.hashlib.sha256(raw).hexdigest()==cache['sha256'],'INPUT_BINDING_MISMATCH')
    return unpack_prepared(sl.load_json(raw))


def validate_context(context,initial_us):
    """Versioned actual native cache, not the old constant-forecast fixture seed."""
    sl.shape(context,'version initial_us prepared initial_timing_state prefix native_code_sha256 context_sha256')
    sl.need(context['version']=='qd011.raw-native-context.v2' and context['initial_us']==initial_us,'INPUT_BINDING_MISMATCH')
    sl.need(context['context_sha256']==sl.digest({k:v for k,v in context.items() if k!='context_sha256'}),'INPUT_BINDING_MISMATCH')
    sl.need(unpack(context['initial_timing_state'])==ExecutionTiming().dump(),'INPUT_BINDING_MISMATCH')
    from research.qd010.economic_inputs import SYMBOLS, HOUR, US
    sl.need(set(context['prepared'])==set(SYMBOLS) and set(context['prefix'])==set(SYMBOLS),'INPUT_BINDING_MISMATCH')
    result={}
    for symbol,packed in context['prepared'].items():
        data=decode_cache(packed)
        for names in (('short_ts','short_f','adaptive_risk_multiplier','adaptive_efficiency_ratio','adaptive_vol_ratio','timing_features'),
                      ('main_ts','main_f','carry_f','vol_ann'),('regime_ts','regime')):
            sl.need(all(type(data[n]) is list for n in names) and len({len(data[n]) for n in names})==1,'INPUT_BINDING_MISMATCH')
        sl.need(len(data['short_ts'])>=300 and len(data['main_ts'])>=300,'INPUT_BINDING_MISMATCH')
        for name,width in (('short_ts',HOUR),('main_ts',4*HOUR),('regime_ts',24*HOUR)):
            times=data[name]
            sl.need(all(math.isfinite(x) and x*US+width<=initial_us for x in times),'FUTURE_DEPENDENCY')
            sl.need(all(a<b for a,b in zip(times,times[1:])),'INPUT_BINDING_MISMATCH')
        sl.need(data['short_ts'][-1]*US==initial_us-HOUR,'INPUT_BINDING_MISMATCH')
        sl.need(context['prefix'][symbol]['max_available_us']<=initial_us,'FUTURE_DEPENDENCY')
        result[symbol]=data
    return result


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
