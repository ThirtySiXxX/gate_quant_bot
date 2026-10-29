"""Actual native causal preparation on a frozen available hourly prefix.

No trading, fitting, policy warmup trades or account execution. QR014 model
features remain a different consumer. Full covariance is never inferred from vol.
"""
from dataclasses import dataclass
from fractions import Fraction
from decimal import Decimal
from copy import deepcopy
from pathlib import Path
import hashlib
import math
import numpy as np
import pandas as pd
from src import strategy_signals, portfolio, vol
from src.execution_timing import ExecutionTiming
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS, SYMBOLS, HOUR, US, exact, text
from research.qd010.joint_native_bridge import research_config
from research.qd011.codec import projection, pack, encode_cache, native_context
from research.qd011.driver import NativeObservation, ExecutionOpen, FundingPoint
from .sources import SourceError


@dataclass
class NativeBundle:
    decision_us: int
    status: str
    reasons: tuple
    prepared: dict
    signals: dict
    covariance: object
    observations: tuple
    warmup_context: dict | None
    lineage: dict


def native_decimal(value):
    if not math.isfinite(float(value)):raise SourceError('NATIVE_VALUE_UNAVAILABLE')
    # Computational output: shortest decimal roundtrip preserves the f64 bits.
    # This is never relabeled an exact source price or exact economic amount.
    s=format(Decimal(repr(float(value))),'f')
    if len(s)>128 or ('.' in s and len(s.split('.')[1])>64):
        raise SourceError('NATIVE_DECIMAL_CELL_PRECISION_UNSUPPORTED')
    return s


def aggregate(hours,width,decision_us):
    groups={}
    for row in hours:groups.setdefault(row.open_us//width*width,[]).append(row)
    result=[]
    for at,children in sorted(groups.items()):
        if at+width>decision_us:continue  # Explicitly unclosed tail, not a repaired gap.
        if len(children)!=width//HOUR or children[0].open_us!=at:
            raise SourceError('INCOMPLETE_UTC_AGGREGATE_PARENTS')
        result.append(dict(timestamp=at//US,open=children[0].open,close=children[-1].close,
            high=text(max(exact(x.high) for x in children)),low=text(min(exact(x.low) for x in children)),
            volume=text(sum((exact(x.volume_contracts) for x in children),Fraction(0)))))
    return result


def frame(rows):
    records=[]
    for r in rows:
        record=dict(r)
        for k in ('open','high','low','close','volume'):record[k]=projection(record[k])
        if abs(record['timestamp'])>2**53:raise SourceError('NATIVE_SECONDS_RANGE')
        records.append(record)
    return pd.DataFrame(records,columns=['timestamp','open','high','low','close','volume'])


def _plain(v):
    if isinstance(v,(np.ndarray,pd.api.extensions.ExtensionArray)):return [_plain(x) for x in v.tolist()]
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,list):return [_plain(x) for x in v]
    if isinstance(v,dict):return {k:_plain(x) for k,x in v.items()}
    return v


def prepare_native(hours_by_instrument,funding_by_instrument,decision_us):
    unavailable=lambda reason:NativeBundle(decision_us,'UNAVAILABLE',(reason,),{},{},None,(),None,{})
    if decision_us%HOUR:raise SourceError('NATIVE_DECISION_NOT_HOURLY')
    cfg=research_config();prepared={};signals={};returns={};prefix={};latest={};main_frames={}
    try:
        for i,symbol in zip(INSTRUMENTS,SYMBOLS):
            hours=[]
            if i not in hours_by_instrument or i not in funding_by_instrument:raise SourceError('JOINT_INPUT_INSTRUMENT_MISSING')
            for r in hours_by_instrument[i]:
                if r.open_us>=decision_us:break
                if r.instrument_id!=i or r.close_us!=r.open_us+HOUR or r.available_us>decision_us:
                    raise SourceError('CLOSED_NATIVE_PREFIX_UNAVAILABLE')
                if hours and r.open_us!=hours[-1].open_us+HOUR:raise SourceError('HOURLY_GAP_OR_DUPLICATE')
                hours.append(r)
            if not hours or hours[-1].close_us!=decision_us:raise SourceError('LATEST_CLOSED_HOUR_MISSING')
            if hours[0].open_us%(24*HOUR):raise SourceError('WARMUP_START_NOT_UTC_DAY')
            short=frame([dict(timestamp=r.open_us//US,open=r.open,high=r.high,low=r.low,close=r.close,volume=r.volume_contracts) for r in hours])
            main=frame(aggregate(hours,4*HOUR,decision_us));regime=frame(aggregate(hours,24*HOUR,decision_us))
            fs=[f for f in funding_by_instrument[i] if f.rate_available_us<=decision_us]
            if any(f.instrument_id!=i for f in fs) or any(a.source_us>=b.source_us for a,b in zip(fs,fs[1:])):
                raise SourceError('FUNDING_IDENTITY_OR_ORDER')
            if not fs:raise SourceError('MISSING_FUNDING_PREFIX_NO_ZERO_FALLBACK')
            funding=pd.DataFrame([dict(timestamp=f.rate_available_us//US,funding_rate=projection(f.rate)) for f in fs])
            with native_context():
                p=strategy_signals.prepare_features(short,main,regime,funding,28800,cfg)
            if len(short)<cfg.min_bars_short or len(main)<cfg.min_bars_main:raise SourceError('NATIVE_WARMUP_NOT_READY')
            for key in ('short_f','main_f','carry_f','vol_ann','adaptive_risk_multiplier','adaptive_efficiency_ratio','adaptive_vol_ratio'):
                if not math.isfinite(float(p[key][-1])):raise SourceError('NATIVE_REQUIRED_INDICATOR_UNKNOWN:'+key)
            tf=p['timing_features'][-1]
            if any(not math.isfinite(float(tf[k])) for k in ('quality','extension','close','atr','recent_high','recent_low','bar_seconds')):
                raise SourceError('NATIVE_TIMING_FEATURE_UNKNOWN')
            sig=strategy_signals.signal_at(symbol,p,decision_us//US,cfg)
            if sig is None:raise SourceError('NATIVE_SIGNAL_UNAVAILABLE')
            r=vol.log_returns(main['close']);r.index=main['timestamp'].values
            if r.iloc[1:].isna().any() or not np.isfinite(r.iloc[1:]).all():raise SourceError('COVARIANCE_REQUIRED_RETURN_UNKNOWN')
            prepared[symbol]=p;signals[symbol]=sig;returns[symbol]=r;main_frames[i]=main
            latest[i]=(hours[-1],tf,p)
            prefix[symbol]=dict(first_open_us=hours[0].open_us,last_close_us=decision_us,count=len(hours),max_available_us=max(x.available_us for x in hours),
                prefix_sha256=sl.digest([r.row_id for r in hours]),
                ohlcv_manifest_sha256=sorted({ref.manifest_sha256 for r in hours for ref in r.refs}),
                source_lineage_sha256=sl.digest([[r.row_id,[[v.raw_sha256,v.source_row,v.source_id] for v in r.refs]] for r in hours]),
                funding_refs=[dict(source_us=f.source_us,rate_available_us=f.rate_available_us,source_seconds=f.source_seconds_text,
                    raw_sha256=f.ref.raw_sha256,source_row=f.ref.source_row,source_id=f.ref.source_id,manifest_sha256=f.ref.manifest_sha256) for f in fs])
        if not returns[SYMBOLS[0]].index.equals(returns[SYMBOLS[1]].index):raise SourceError('JOINT_COVARIANCE_GRID_MISMATCH')
        # Only the structurally undefined first differenced return reaches native
        # initialization; missing observed returns never reach its fillna path.
        with native_context():cov=portfolio.build_covariance(returns,'4h',cfg)
        values=cov.loc[list(SYMBOLS),list(SYMBOLS)].to_numpy(dtype=float)
        if not np.isfinite(values).all() or np.any(np.diag(values)<=0):raise SourceError('COVARIANCE_NOT_POSITIVE_FINITE')
        observations=[]
        for i,symbol in zip(INSTRUMENTS,SYMBOLS):
            row,tf,p=latest[i];main=main_frames[i]
            reg_index=len(p['regime_ts'])-1
            reg_open=int(p['regime_ts'][reg_index]*US)
            lineage='qd012-prefix:'+prefix[symbol]['prefix_sha256']
            observations.append(NativeObservation(i,decision_us,int(main['timestamp'].iloc[-1])*US,
                native_decimal(p['short_f'][-1]),native_decimal(p['main_f'][-1]),native_decimal(p['vol_ann'][-1]),native_decimal(p['carry_f'][-1]),
                native_decimal(p['adaptive_risk_multiplier'][-1]),native_decimal(tf['quality']),native_decimal(tf['extension']),row.close,
                native_decimal(tf['atr']),native_decimal(tf['recent_high']),native_decimal(tf['recent_low']),row.volume_contracts,
                int(tf['long_run']),int(tf['short_run']),native_decimal(values[0,1]),lineage,
                regime=p['regime'][reg_index],regime_open_us=reg_open,regime_available_us=reg_open+24*HOUR,
                efficiency=native_decimal(p['adaptive_efficiency_ratio'][-1]),range_vol_ratio=native_decimal(p['adaptive_vol_ratio'][-1]),
                cov_btc_btc=native_decimal(values[0,0]),cov_eth_eth=native_decimal(values[1,1]),
                cov_available_us=int(main['timestamp'].iloc[-1])*US+4*HOUR,
                breakout_long=bool(tf['breakout_long']),breakout_short=bool(tf['breakout_short']),bar_seconds=native_decimal(tf['bar_seconds'])))
        paths=('src/strategy_signals.py','src/trend.py','src/carry.py','src/vol.py','src/portfolio.py','src/execution_timing.py')
        root=Path(__file__).resolve().parents[2]
        context=dict(version='qd011.raw-native-context.v2',initial_us=decision_us,
            prepared={s:encode_cache(_plain(p)) for s,p in prepared.items()},initial_timing_state=pack(ExecutionTiming().dump()),prefix=prefix,
            native_code_sha256={path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in paths})
        context['context_sha256']=sl.digest(context)
        return NativeBundle(decision_us,'AVAILABLE',(),prepared,signals,cov,tuple(observations),context,
            dict(prefix=prefix,funding_clock='STRICT_NEXT_HOUR_THEN_NATIVE_MAIN_OPEN_ALIGNMENT',carry_unit_seconds=28800,
                 timing_initialization='NATIVE_INITIALIZER_INDICATOR_ONLY_WARMUP_NO_POLICY_OR_FILLS'))
    except (SourceError,ValueError) as e:
        return unavailable(str(e))


def execution_opens(hours_by_instrument,at_us):
    result=[]
    for i in INSTRUMENTS:
        r=next((r for r in hours_by_instrument[i] if r.open_us==at_us),None)
        if r is None:raise SourceError('EXECUTION_ONLY_OPEN_MISSING')
        result.append(ExecutionOpen(i,at_us,r.open,'qd012-open:'+r.row_id))
    return tuple(result)


def funding_points(rows):
    result=[]
    for f in rows:
        if f.source_us%US:raise SourceError('QD011_INTEGER_SOURCE_SECONDS_UNREPRESENTABLE_NO_ROUNDING')
        result.append(FundingPoint(f.instrument_id,f.source_us,f.rate,
            'fund:'+f.instrument_id+':'+str(f.source_us),f.ref.raw_sha256+':'+str(f.ref.source_row)))
    return tuple(result)
