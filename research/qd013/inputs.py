"""Single-pass raw cursors -> shared immutable local market cells."""
from collections import deque
from dataclasses import asdict
from research.qd010.economic_inputs import INSTRUMENTS,HOUR,US,InputGap
from research.qd012.queries import query_plan,ROLES
from .market import NativeSeries,MarketCache
from research.qd011.codec import pack


class MarkWindow:
    def __init__(self,instrument,points,maximum=16384):
        self.instrument=instrument;self.points=iter(points);self.pending=None;self.ended=False
        self.window=deque();self.old=None;self.last_query=-1;self.last_source=-1;self.maximum=maximum
        self.work=dict(source_points=0,queries=0,max_retained=0)

    def select(self,at,*,slow=False):
        if at<self.last_query:raise InputGap('DECREASING_QUERY')
        self.last_query=at;self.work['queries']+=1
        while True:
            if self.pending is None and not self.ended:
                self.pending=next(self.points,None)
                if self.pending is None:self.ended=True
                else:
                    p=self.pending
                    if p.instrument_id!=self.instrument or p.source_us<=self.last_source:raise InputGap('UNORDERED_MARK_SOURCE')
                    self.last_source=p.source_us;self.work['source_points']+=1
            if self.pending is None or self.pending.source_us>at-60*US:break
            self.window.append(self.pending);self.pending=None
            while self.window and self.window[0].source_us<at-180*US:self.old=self.window.popleft()
            if len(self.window)>self.maximum:raise InputGap('MARK_DENSITY_RESOURCE_BOUND')
        self.work['max_retained']=max(self.work['max_retained'],len(self.window)+int(self.pending is not None)+int(self.old is not None))
        lag=120*US if slow else 60*US;maxage=180*US if slow else 120*US
        p=next((p for p in reversed(self.window) if p.source_us+lag<=at),self.old)
        reason='NO_ELIGIBLE_POINT' if p is None else 'SOURCE_TOO_OLD' if at-p.source_us>maxage else 'AVAILABLE_TOO_OLD' if at-p.source_us-lag>60*US else None
        if p is not None and p.source_us+lag>at:p=None;reason='NO_ELIGIBLE_POINT'
        supported=reason is None
        dto=dict(instrument_id=self.instrument,query_us=at,mark_clock_id='mark-clock',roles=list(ROLES),status='SUPPORTED' if supported else 'UNKNOWN',
            source_us=p.source_us if supported else None,source_available_us=p.source_us+lag if supported else None,
            source_semantic_key=[self.instrument,'archive-mark',p.source_us] if supported else None,mark_price=p.price if supported else None,
            selected_at_us=at,consumer_available_us=at,unknown_reason=reason)
        return dict(dto=dto,source_refs=[asdict(r) for r in p.refs] if supported else [],clock='slow' if slow else 'primary')


def build_cache(path,identity,*,hours,funding,mark_streams,initial_us,economic_end_us,work=None,write_budget=None):
    # Cache hit precedes native construction and cursor consumption.
    if path.exists():
        hit=MarketCache(path,identity)
        if work is not None:work.update(cache_hit=True,native_prepare_calls=0,covariance_series_calls=0,raw_cursor_reopens=0)
        return hit
    start=identity['scope']['warmup_start_us']
    if any(not rows or rows[0].open_us!=start or rows[-1].close_us<economic_end_us for rows in hours.values()):
        raise InputGap('FULL_DECLARED_WARMUP_AND_ECONOMIC_SOURCE_SCOPE_REQUIRED')
    series=NativeSeries(hours,funding);windows={i:MarkWindow(i,mark_streams[i]) for i in INSTRUMENTS}
    sources=[f.source_us for rows in funding.values() for f in rows if initial_us<=f.source_us<economic_end_us]
    def records():
        for i in INSTRUMENTS:
            for row in hours[i]:
                yield 'hour',i,row.open_us,pack(asdict(row))
                if initial_us<=row.open_us<economic_end_us:
                    yield 'open',i,row.open_us,dict(instrument_id=i,at_us=row.open_us,price=row.open,source_ref='qd013-open:'+row.row_id)
            for f in funding[i]:yield 'funding',i,f.source_us,asdict(f)
        for at in range(initial_us,economic_end_us,HOUR):
            try:values=series.snapshot(at)
            except InputGap as error:
                values=[dict(instrument_id=i,available_us=at,status='UNAVAILABLE',reason=str(error)) for i in INSTRUMENTS]
            for row in values:yield 'native',row['instrument_id'],at,row
        finality_ticks=[(t//HOUR+2)*HOUR+60*US for t in sources]
        for q in query_plan(initial_us,economic_end_us,funding_source_times=sorted(set(sources)),extra_tick_times=finality_ticks):
            w=windows[q.instrument_id]
            for slow in (False,True):yield 'mark_slow' if slow else 'mark_primary',q.instrument_id,q.query_us,w.select(q.query_us,slow=slow)
    cache=MarketCache.build(path,identity,records(),write_budget=write_budget)
    if work is not None:work.update(cache_hit=False,**series.stats,mark={i:w.work for i,w in windows.items()},raw_cursor_reopens=0)
    return cache
