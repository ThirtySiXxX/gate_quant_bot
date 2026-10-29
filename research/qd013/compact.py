"""Sparse *actual* prefix views for native signal_at, no invented warmup values.

signal_at only needs true grid lengths/timestamps and each selected last cell.
Access to an unprovided historical cell is an error, never a constant seed.
"""
from research.qd010.economic_inputs import HOUR, US, SYMBOLS, INSTRUMENTS, InputGap
from research.qd011.codec import projection
from src.strategy_signals import signal_at
from research.qd010.joint_native_bridge import research_config


class Grid:
    def __init__(self,first,count,width):self.first,self.count,self.width=first,count,width
    def __len__(self):return self.count
    def __getitem__(self,index):
        if not 0<=index<self.count:raise IndexError(index)
        return (self.first+index*self.width)/US


class Last:
    def __init__(self,count,value):self.count,self.value=count,value
    def __getitem__(self,index):
        if index in (-1,self.count-1):return self.value
        raise InputGap('UNPROVIDED_HISTORICAL_NATIVE_CELL')


def signal(symbol,f):
    cfg=research_config();first=f['first_open_us'];at=f['available'];counts=(f['short_count'],f['main_count'],f['regime_count'])
    if counts[0]*HOUR+first!=at or f['main_open_us']!=first+(counts[1]-1)*4*HOUR or f['regime_open_us']!=first+(counts[2]-1)*24*HOUR:
        raise InputGap('COMPACT_NATIVE_GRID_MISMATCH')
    from research.qd011.ports import timing_feature
    p={k+'_ts':Grid(first,n,w) for k,n,w in zip(('short','main','regime'),counts,(HOUR,4*HOUR,24*HOUR))}
    for k,v,n in (('short_f',projection(f['short']),counts[0]),('main_f',projection(f['main']),counts[1]),
        ('carry_f',projection(f['carry']),counts[1]),('vol_ann',projection(f['vol']),counts[1]),
        ('regime',f['regime'],counts[2]),('adaptive_risk_multiplier',projection(f['risk']),counts[0]),
        ('adaptive_efficiency_ratio',projection(f['efficiency']),counts[0]),('adaptive_vol_ratio',projection(f['range_vol_ratio']),counts[0]),
        ('timing_features',timing_feature(f,True),counts[0])):p[k]=Last(n,v)
    return signal_at(symbol,p,at/US,cfg)


def inputs(packet):
    from research.qd011.ports import native_facts
    at=packet['slot']['at_us'];latest={};result={}
    for f in native_facts(packet):
        if f['available']==at and f['at']==at-HOUR:latest[f['instrument_id']]=f
    for i,s in zip(INSTRUMENTS,SYMBOLS):
        f=latest.get(i)
        if f is None or any(v is None for k,v in f.items() if k not in ('status_reason',)):continue
        value=signal(s,f)
        if value is not None:result[s]=value
    return result,latest
