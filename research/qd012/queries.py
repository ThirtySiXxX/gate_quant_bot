"""Bounded ordered source consumption and explicit MARK query clocks.

No query-coverage conclusion follows from metadata acceptance. UNKNOWN remains
UNKNOWN. No MARK query is created in the settlement-only tail.
"""
from dataclasses import dataclass, asdict
from heapq import merge
from itertools import groupby
from research.qd010.economic_inputs import INSTRUMENTS, HOUR, US, Mark
from .sources import SourceError, MarkPoint, iter_marks

ROLES=('valuation','reservation','decision','permitted_fill','funding_snapshot')


@dataclass(frozen=True)
class Query:
    instrument_id: str
    query_us: int
    roles: tuple=ROLES


@dataclass(frozen=True)
class MarkSelection:
    query: Query
    status: str
    reason: str | None
    point: MarkPoint | None

    def dto(self):
        p=self.point;q=self.query
        return dict(instrument_id=q.instrument_id,query_us=q.query_us,mark_clock_id='mark-clock',roles=list(q.roles),
            status=self.status,source_us=p.source_us if p else None,source_available_us=p.source_us+60*US if p else None,
            source_semantic_key=[q.instrument_id,'archive-mark',p.source_us] if p else None,mark_price=p.price if p else None,
            selected_at_us=q.query_us,consumer_available_us=q.query_us,unknown_reason=self.reason)

    def observation(self):
        if self.point is None:raise SourceError('UNKNOWN_MARK_HAS_NO_OBSERVATION')
        p=self.point
        # All alias refs, including distinct raw objects, remain traceable.
        ref=';'.join(r.raw_sha256+':'+str(r.source_row) for r in p.refs)
        return Mark(p.instrument_id,p.source_us,p.price,ref)

    def lineage(self):
        return dict(query_us=self.query.query_us,instrument_id=self.query.instrument_id,status=self.status,reason=self.reason,
                    refs=[asdict(r) for r in self.point.refs] if self.point else [])


def mark_objects(specs,permits):
    """Supplied chronological monthly descriptors; one pending alias group."""
    pending=None
    for spec in specs:
        for point in iter_marks(spec,permits.get(spec.path)):
            if pending is not None:
                if point.instrument_id!=pending.instrument_id or point.source_us<pending.source_us:
                    raise SourceError('MARK_OBJECT_ORDER_OR_INSTRUMENT')
                if point.source_us==pending.source_us:
                    if point.lexemes!=pending.lexemes:raise SourceError('CONFLICTING_CROSS_OBJECT_MARK')
                    refs=pending.refs+point.refs
                    if len(refs)>1024:raise SourceError('ALIAS_GROUP_RESOURCE_LIMIT')
                    pending=MarkPoint(point.instrument_id,point.source_us,point.price,point.lexemes,refs);continue
                yield pending
            pending=point
    if pending is not None:yield pending


class MarkSelector:
    """One lookahead and one latest eligible point; queries must be monotonic."""
    def __init__(self,instrument_id,points):
        self.instrument_id=instrument_id;self.points=iter(points);self.pending=None;self.latest=None
        self.previous_query=-1;self.previous_source=-1;self.ended=False

    def select(self,query,*,missing_required_month=False):
        if query.instrument_id!=self.instrument_id or query.query_us<self.previous_query:
            raise SourceError('MARK_QUERY_ORDER_OR_IDENTITY')
        self.previous_query=query.query_us
        while True:
            if self.pending is None and not self.ended:
                self.pending=next(self.points,None)
                if self.pending is None:self.ended=True
                else:
                    if self.pending.instrument_id!=self.instrument_id or self.pending.source_us<=self.previous_source:
                        raise SourceError('MARK_STREAM_NOT_STRICTLY_ORDERED')
                    self.previous_source=self.pending.source_us
            if self.pending is None or self.pending.source_us+60*US>query.query_us:break
            self.latest=self.pending;self.pending=None
        p=self.latest
        reason=('MISSING_REQUIRED_MONTH' if missing_required_month else 'NO_ELIGIBLE_POINT' if p is None else
                'SOURCE_TOO_OLD' if query.query_us-p.source_us>120*US else
                'AVAILABLE_TOO_OLD' if query.query_us-(p.source_us+60*US)>60*US else None)
        return MarkSelection(query,'UNKNOWN' if reason else 'SUPPORTED',reason,None if reason else p)


def query_plan(initial_us,economic_end_us,*,funding_source_times=(),extra_tick_times=()):
    """Finite caller-approved clocks; streaming merge, no account execution.

    Matches QD011's hourly policy/open ticks and funding snapshot/R/posting ticks.
    Completeness in the +2h tail does not introduce new MARK requirements.
    """
    if initial_us%HOUR or economic_end_us%HOUR or initial_us>=economic_end_us:
        raise SourceError('QUERY_WINDOW_MUST_BE_WHOLE_HOURS')
    # Funding input is a small approved event calendar, never MARK history.
    funding=tuple(funding_source_times)
    if any(type(t) is not int or not initial_us<=t<economic_end_us for t in funding):
        raise SourceError('FUNDING_SNAPSHOT_OUTSIDE_ECONOMIC_WINDOW')
    rate=sorted({t for s in funding for t in (s,(s//HOUR+1)*HOUR,(s//HOUR+1)*HOUR+60*US)})
    extra=sorted(set(extra_tick_times))
    for t,_ in groupby(merge(range(initial_us,economic_end_us,HOUR),rate,extra)):
        if initial_us<=t<economic_end_us:
            for i in INSTRUMENTS:yield Query(i,t)


def select_queries(queries,selectors,missing_month=None):
    for q in queries:
        yield selectors[q.instrument_id].select(q,missing_required_month=bool(missing_month and missing_month(q)))
