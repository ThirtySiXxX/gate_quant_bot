"""Frozen-source preparation only. No CLI/default run, account creation or fit.

Payload access is an explicit iterator call with a separately supplied permit.
Assembly returns QD011 keyword arguments and audit lineage; it never calls create.
"""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS, HOUR
from .sources import (SourceError, ActualHistoryOff, metadata, hourly_specs, monthly_specs,
    iter_hours, iter_funding, OHLCV_MANIFEST_SHA, MARK_HANDOFF_SHA, FUNDING_HANDOFF_SHA, DATASET, POLICY)
from .native import prepare_native, execution_opens, funding_points
from .queries import Query, MarkSelector, mark_objects, query_plan, select_queries

BASE='61536c823926fb873f9a4a130778f34e0b87c161'
ACCEPTED=dict(qr008_report='0a90b2555db8e16934053abff31db29bac4296a2',
    qr008_checker='9cae8458fb85e474a047fc1793abe0458cd83ab3',
    qr010_shared_account='88168f34c8c2855e9e65510bcde749cc459ff12a',
    qr014_sample_plan='f2c931b8335ca8b1840f22d346a040446c50abb2')


def load_catalogues(ohlcv_root,coordination_root):
    """Only the three pinned metadata documents. No raw reads or stat calls."""
    root=Path(ohlcv_root);coord=Path(coordination_root)
    o=metadata(root/'manifest.json',OHLCV_MANIFEST_SHA)
    m=metadata(coord/'mark-r2-raw-handoff.json',MARK_HANDOFF_SHA)
    f=metadata(coord/'funding-raw-lineage-through-september-r1.json',FUNDING_HANDOFF_SHA)
    return dict(ohlcv=hourly_specs(root,o),mark=monthly_specs(m,'mark'),funding=monthly_specs(f,'funding'),
                metadata=dict(ohlcv=o,mark=m,funding=f))


def read_hour_prefix(specs,permits=None,*,max_hours_per_instrument=2048):
    if permits is None:raise ActualHistoryOff('ACTUAL_HISTORY_EXECUTION_OFF')
    result={i:[] for i in INSTRUMENTS}
    for spec in specs:
        for row in iter_hours(spec,permits.get(spec.path)):
            values=result[row.instrument_id]
            if len(values)>=max_hours_per_instrument:raise SourceError('DECLARED_HOURLY_PREFIX_BUDGET')
            if values and row.open_us!=values[-1].open_us+HOUR:raise SourceError('HOURLY_OBJECT_BOUNDARY_GAP')
            values.append(row)
    if any(not rows for rows in result.values()):raise SourceError('BOTH_HOURLY_PREFIXES_REQUIRED')
    return {i:tuple(rows) for i,rows in result.items()}


def read_funding_prefix(specs,permits=None,*,max_records=10000):
    if permits is None:raise ActualHistoryOff('ACTUAL_HISTORY_EXECUTION_OFF')
    result={i:[] for i in INSTRUMENTS};count=0
    for spec in specs:
        for row in iter_funding(spec,permits.get(spec.path)):
            count+=1
            if count>max_records:raise SourceError('DECLARED_FUNDING_PREFIX_BUDGET')
            result[row.instrument_id].append(row)
    for rows in result.values():
        rows.sort(key=lambda f:f.source_us)
        if any(a.source_us==b.source_us for a,b in zip(rows,rows[1:])):raise SourceError('DUPLICATE_RAW_FUNDING_SOURCE')
    return {i:tuple(rows) for i,rows in result.items()}


def mark_selectors(specs,permits=None):
    if permits is None:raise ActualHistoryOff('ACTUAL_HISTORY_EXECUTION_OFF')
    grouped=defaultdict(list)
    for spec in specs:grouped[spec.instrument_id].append(spec)
    return {i:MarkSelector(i,mark_objects(grouped[i],permits)) for i in INSTRUMENTS}


@dataclass
class PreparedInputs:
    driver_kwargs: dict
    lineage: dict
    initial_bundle: object


def assemble(hours,funding,selectors,*,decision_times,economic_end_us,settlement_end_us,max_decisions=24,missing_month=None):
    """Finite bounded caller window, including actual native initial context.

    Unknown required native inputs reject preparation. Unknown MARK is passed as
    an explicit DTO; QD011 suppresses increases when economic inputs are unknown.
    No economic event, future label or model matrix is produced here.
    """
    times=tuple(decision_times)
    if not times or len(times)>max_decisions or list(times)!=sorted(set(times)):
        raise SourceError('DECLARED_DECISION_SCOPE_REQUIRED')
    if any(t%HOUR or t>=economic_end_us for t in times) or settlement_end_us!=economic_end_us+2*HOUR:
        raise SourceError('ECONOMIC_WINDOW_AND_TWO_HOUR_SETTLEMENT_REQUIRED')
    bundles=[prepare_native(hours,funding,t) for t in times]
    for b in bundles:
        if b.status!='AVAILABLE':raise SourceError('NATIVE_INPUT_UNAVAILABLE:'+','.join(b.reasons))
    initial=times[0]
    if times!=tuple(range(initial,economic_end_us,HOUR)):
        raise SourceError('EVERY_ECONOMIC_HOUR_REQUIRES_ACTUAL_NATIVE_OBSERVATION')
    account_funding=[r for rows in funding.values() for r in rows if initial<=r.source_us<economic_end_us]
    fps=funding_points(account_funding)
    queries=query_plan(initial,economic_end_us,funding_source_times=sorted({r.source_us for r in account_funding}))
    selections=list(select_queries(queries,selectors,missing_month))
    # QD011 consumes the very same query DTOs; do not reinterpret UNKNOWN as zero.
    marks={}
    for s in selections:
        if s.point:marks[(s.point.instrument_id,s.point.source_us)]=s.observation()
    opens=[]
    for t in range(initial,economic_end_us,HOUR):opens.extend(execution_opens(hours,t))
    kwargs=dict(initial_us=initial,end_us=settlement_end_us,economic_end_us=economic_end_us,
        native=tuple(o for b in bundles for o in b.observations),opens=tuple(opens),marks=tuple(marks.values()),funding=fps,
        native_input_version=2,native_context=bundles[0].warmup_context,
        mark_selections=tuple(s.dto() for s in selections))
    return PreparedInputs(kwargs,dict(native=[b.lineage for b in bundles],mark=[s.lineage() for s in selections],
        funding=[dict(event_id=f.event_id,source_us=f.source_us,rate_available_us=(f.source_us//HOUR+1)*HOUR,
            posting_us=(f.source_us//HOUR+1)*HOUR+60_000_000,source_ref=f.source_ref) for f in fps]),bundles[0])


def preparation_manifest(catalogues):
    """Metadata-only task deliverable, no source revalidation or acceptance loop."""
    f=catalogues['metadata']['funding']['raw_sources'];m=catalogues['metadata']['mark']['objects']
    at=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp())*1_000_000
    chosen_m=[e for e in m if e['month'] in ('202312','202401')]
    chosen_f=[e for e in f if e['first_source_seconds']*1_000_000<at+HOUR and e['last_source_seconds']>=1672531200]
    return dict(namespace='qd012.frozen-native-preparation',schema_version=2,base_commit=BASE,
        status='NEW_CANDIDATE_SYNTHETIC_CHECKS_ONLY',actual_history_execution='OFF',accepted_conclusions=ACCEPTED,
        dataset_id=DATASET,source_policy_id=POLICY,manifest_sha256=dict(ohlcv=OHLCV_MANIFEST_SHA,mark=MARK_HANDOFF_SHA,funding=FUNDING_HANDOFF_SHA),
        code_sha256={p:sl.hashlib.sha256((Path(__file__).resolve().parents[2]/p).read_bytes()).hexdigest() for p in (
            'research/qd012/sources.py','research/qd012/native.py','research/qd012/queries.py','research/qd012/prepare.py',
            'research/qd011/driver.py','research/qd011/ports.py','research/qd011/codec.py')},
        scope=dict(warmup_start='2023-01-01T00:00:00Z',warmup='INDICATORS_ONLY_NO_POLICY_FILLS_OR_CASHFLOWS',
            account_start='2024-01-01T00:00:00Z',economic_end_exclusive='2026-10-01T00:00:00Z',
            settlement_end_exclusive='2026-10-01T02:00:00Z',initial_shared_cash_usdt='10000',accounts=1,scenarios=10),
        contracts=dict(native_input_version=2,warmup_context='qd011.raw-native-context.v2',cache_codec='zlib-json-f64-v1',
            timestamp='integer_UTC_microseconds',source_seconds='exact_decimal_max_6dp',price='USDT_per_base',volume='decimal_contracts',
            covariance='native_annual_2x2_BTC_ETH_separate_from_sizing_std',carry='8h_equivalent_28800s_1095_per_year_MAIN_BAR_OPEN_alignment',
            mark='source_plus_60s_age_source_le_120s_age_available_le_60s',funding='strict_next_hour_R_post_R_plus_60s_completeness_plus_1h',
            initializer='ExecutionTiming().dump()_indicator_only_warmup',qr014_features='SEPARATE_NOT_ASSEMBLED'),
        next_bounded_actual_scope=dict(status='PROPOSAL_NOT_AUTHORIZATION_OR_EXECUTION',decision_us=at,
            hourly_prefix_start_us=1672531200000000,hourly_prefix_end_exclusive_us=at,
            execution_open_only_us=at+HOUR,mark_queries_us=[at,at+HOUR],
            roles=['valuation','reservation','decision','permitted_fill'],
            no_account_advance=True,no_labels=True,no_fit=True,
            hourly_objects=[s.__dict__ for s in catalogues['ohlcv']],funding_objects=chosen_f,mark_objects=chosen_m,
            whole_selected_compressed_bytes=sum(s.bytes for s in catalogues['ohlcv'])+sum(e['bytes'] for e in chosen_f+chosen_m),
            suggested_observation_limits=dict(wall_seconds=300,cpu_seconds=200,rss_mib=256,new_output_mib=8,compressed_input_mib=128),
            uncertainty='METADATA_ONLY: gzip prefix expansion/CPU/native full-year memory and output unmeasured; reduce scope or seek amended limits if insufficient'),
        limitations=['No raw actual-history payload opened or rehashed by this task',
            'Supplied manifest hash is provenance, partial streams do not prove full-object SHA or gzip CRC',
            'MARK query coverage UNKNOWN until separately approved bounded evaluation',
            'Integer funding source-seconds compatibility untested on actual records; fractional source rejected',
            'Finite assembly materializes only declared scope; no full-account scalability proof or model fitting'])
