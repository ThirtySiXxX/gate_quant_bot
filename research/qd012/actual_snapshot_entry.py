"""One proposed actual-input snapshot. OFF unless a human explicitly authorizes.

STATIC CANDIDATE: this module/CLI has not been run. No default probe/dry-run.
No account, assemble, policy execution, labels, fit, download, retry or resume.
Resource checks are cooperative observations, not hard OS enforcement.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
import zlib

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'research/qd012/preparation_manifest.json'
ARTIFACTS=ROOT/'research/.data/qd012/actual-snapshot-20240101-attempt-1'
DISPATCH='QF-DISPATCH-20261028-QD012-SNAPSHOT-ENTRY-PREP-1'


class SnapshotStop(ValueError):
    pass


def require(ok,reason):
    if not ok:raise SnapshotStop(reason)


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'


def digest(value):return hashlib.sha256(encoded(value)).hexdigest()


def durable_new(path,value,remaining):
    raw=encoded(value);require(len(raw)<=remaining,'OUTPUT_LIMIT_BEFORE_WRITE')
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return len(raw)


def local_path(path):
    p=Path(path)
    require(p.is_absolute() and '..' not in p.parts and not any(x.is_symlink() for x in (p,*p.parents)),
            'ABSOLUTE_NON_SYMLINK_PATH_REQUIRED')
    return p


class ObservationBudget:
    def __init__(self,limits):
        import resource
        self.resource=resource;self.limits=limits;self.wall0=time.monotonic();u=resource.getrusage(resource.RUSAGE_SELF)
        self.cpu0=u.ru_utime+u.ru_stime;self.physical=0;self.expanded=0;self.rows=0;self.output=0;self.objects={}

    def observed(self):
        u=self.resource.getrusage(self.resource.RUSAGE_SELF)
        require(sys.platform in ('darwin','linux'),'RSS_UNITS_UNSUPPORTED_PLATFORM')
        return dict(wall_seconds=time.monotonic()-self.wall0,cpu_seconds=u.ru_utime+u.ru_stime-self.cpu0,
            peak_rss_bytes=u.ru_maxrss*(1 if sys.platform=='darwin' else 1024),physical_input_bytes=self.physical,
            expanded_input_bytes=self.expanded,physical_rows_yielded=self.rows,output_bytes=self.output)

    def check(self):
        o=self.observed()
        for measured,limit in (('wall_seconds','wall_seconds'),('cpu_seconds','cpu_seconds'),('peak_rss_bytes','rss_bytes')):
            require(o[measured]<=self.limits[limit],'OBSERVED_'+limit.upper()+'_LIMIT')

    def add(self,counter,amount,entry):
        require(amount>=0,'NEGATIVE_RESOURCE_ACCOUNTING')
        total=getattr(self,counter)+amount
        limit={'physical':'physical_input_bytes','expanded':'expanded_input_bytes','rows':'physical_rows'}[counter]
        require(total<=self.limits[limit] and entry[counter]+amount<=entry['permit'][limit],limit.upper()+'_LIMIT')
        setattr(self,counter,total);entry[counter]+=amount;self.check()


class BoundedTransport:
    """Temporary reader transport hook; actual QD012 parsers remain unchanged.

    Counts raw/compressed read bytes and *all* decompressor output, including
    lookahead. It does not hash whole accepted payloads or collect MARK history.
    """
    def __init__(self,budget,allowlist):
        self.budget=budget;self.allowed={x['path']:x for x in allowlist};self.handles=[]

    def physical_chunk(self,handle,entry):
        self.budget.check();p=entry['permit']
        remaining=min(p['physical_input_bytes']-entry['physical'],self.budget.limits['physical_input_bytes']-self.budget.physical)
        if entry['physical']==p['expected_file_bytes']:return b''
        require(remaining>0,'PHYSICAL_INPUT_LIMIT')
        raw=handle.read(min(4096,remaining));self.budget.add('physical',len(raw),entry)
        return raw

    def chunks(self,handle,entry,compressed):
        if not compressed:
            while True:
                raw=self.physical_chunk(handle,entry)
                if not raw:return
                self.budget.add('expanded',len(raw),entry);yield raw
        else:
            decoder=zlib.decompressobj(16+zlib.MAX_WBITS);pending=b'';drain=False
            while True:
                if not pending and not drain:
                    pending=self.physical_chunk(handle,entry)
                    if not pending:
                        require(decoder.eof,'TRUNCATED_GZIP_PREFIX_AT_EOF');return
                if decoder.eof:decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
                remaining=min(entry['permit']['expanded_input_bytes']-entry['expanded'],
                              self.budget.limits['expanded_input_bytes']-self.budget.expanded)
                # An empty-output trailer can still be consumed at the exact cap.
                limit=max(1,min(65536,remaining))
                out=decoder.decompress(pending,limit)
                pending=decoder.unused_data if decoder.eof else decoder.unconsumed_tail
                drain=len(out)==limit and not decoder.eof and not pending
                self.budget.add('expanded',len(out),entry)
                if out:yield out

    def lines(self,spec,permit):
        self.budget.check();a=self.allowed.get(spec.path)
        require(a is not None and permit is not None,'SOURCE_OUTSIDE_FROZEN_ALLOWLIST')
        require(spec.path not in self.budget.objects,'SOURCE_REOPEN_FORBIDDEN')
        require(all(getattr(spec,k)==a['object'][k] for k in a['object']),'FROZEN_DESCRIPTOR_MISMATCH')
        path=permit.check(spec)  # original absolute/symlink/stat/manifest checks
        entry=dict(permit=a['permit'],physical=0,expanded=0,rows=0,expected_sha256=spec.sha256)
        self.budget.objects[spec.path]=entry
        with path.open('rb',buffering=0) as handle:
            self.handles.append(handle)
            require(os.fstat(handle.fileno()).st_size==spec.bytes,'SOURCE_SIZE_CHANGED')
            buffer=bytearray()
            for chunk in self.chunks(handle,entry,spec.format in ('mark_csv_gzip','funding_csv_gzip')):
                buffer.extend(chunk)
                while True:
                    end=buffer.find(b'\n')
                    if end<0:break
                    require(end+1<=1024*1024,'PHYSICAL_LINE_LIMIT')
                    line=bytes(buffer[:end+1]);del buffer[:end+1]
                    self.budget.add('rows',1,entry);yield entry['rows'],line
                require(len(buffer)<=1024*1024,'PHYSICAL_LINE_LIMIT')
            if buffer:
                self.budget.add('rows',1,entry);yield entry['rows'],bytes(buffer)

    def close(self):
        for h in self.handles:h.close()


@contextmanager
def bounded_inputs(sources,budget,allowlist):
    old=sources._lines;transport=BoundedTransport(budget,allowlist)
    sources._lines=transport.lines
    try:yield
    finally:sources._lines=old;transport.close()


@contextmanager
def network_off():
    def blocked(*args,**kwargs):raise SnapshotStop('NETWORK_FORBIDDEN')
    previous=socket.create_connection,socket.socket.connect,socket.socket.connect_ex
    socket.create_connection=socket.socket.connect=socket.socket.connect_ex=blocked
    try:yield
    finally:socket.create_connection,socket.socket.connect,socket.socket.connect_ex=previous


def verify_identities(manifest,plan,budget):
    for relative,expected in manifest['code_sha256'].items():
        p=local_path(str(ROOT/relative));require(p.is_relative_to(ROOT),'CODE_PATH_ESCAPE')
        require(hashlib.sha256(p.read_bytes()).hexdigest()==expected,'CODE_IDENTITY_MISMATCH:'+relative);budget.check()
    metadata={}
    for identity in plan['metadata_identities']:
        p=local_path(identity['path']);raw=p.read_bytes()
        require(hashlib.sha256(raw).hexdigest()==identity['sha256'],'METADATA_IDENTITY_MISMATCH:'+str(p))
        metadata[identity['kind']]=json.loads(raw);budget.check()
    require(len(plan['allowlist'])==32 and len({x['path'] for x in plan['allowlist']})==32,'ALLOWLIST_COUNT_MISMATCH')
    # Every descriptor must still match its authoritative metadata, not just size.
    known={}
    o=metadata['ohlcv'];base=Path(plan['ohlcv_root'])
    for row in o['candles']:
        if row['interval_seconds']==3600:known[str(base/row['path'])]=(row['sha256'],row['bytes'])
    for row in metadata['mark']['objects']+metadata['funding']['raw_sources']:
        known[row['path']]=(row['sha256'],row['bytes'])
    for a in plan['allowlist']:
        require(known.get(a['path'])==(a['object']['sha256'],a['object']['bytes']),'ALLOWLIST_METADATA_MISMATCH')


def snapshot(manifest,plan,budget,human_authorization_ref):
    # These imports happen only AFTER the exclusive authorization receipt and
    # metadata/code identity checks. No application/config/account is started.
    from . import sources
    from .prepare import read_hour_prefix, read_funding_prefix, mark_selectors
    from .native import prepare_native, execution_opens
    from .queries import Query
    from research.qd011.codec import pack
    import numpy as np
    import pandas as pd
    budget.check();specs={};permits={}
    for a in plan['allowlist']:
        spec=sources.ObjectSpec(**a['object']);specs[spec.path]=spec;p=a['permit']
        permits[spec.path]=sources.ReadPermit(human_authorization_ref,(spec.path,),spec.manifest_sha256,
            p['start_us'],p['end_us'],p['physical_rows'],p['expanded_input_bytes'],kind='separately_approved_actual_history')
    instruments=tuple(plan['instruments']);at=plan['snapshot_us'];start=plan['warmup_start_us']
    with bounded_inputs(sources,budget,plan['allowlist']):
        hourly=[specs[a['path']] for a in plan['allowlist'] if a['kind']=='ohlcv']
        all_hours=read_hour_prefix(hourly,permits,max_hours_per_instrument=8762)
        warmup={i:tuple(r for r in all_hours[i] if start<=r.open_us and r.close_us<=at) for i in instruments}
        require(all(len(r)==8760 and r[0].open_us==start and r[-1].close_us==at for r in warmup.values()),'FULL_2023_WARMUP_MISSING')
        future={i:tuple(r for r in all_hours[i] if r.open_us==plan['execution_open_us']) for i in instruments}
        opens=execution_opens(future,plan['execution_open_us'])
        # January funding objects are allowlisted but metadata proves no source
        # before the warmup cutoff; leave them unopened instead of reading future.
        fs=[specs[a['path']] for a in plan['allowlist'] if a['kind']=='funding' and a['first_source_us']<at]
        funding=read_funding_prefix(fs,permits,max_records=plan['funding_data_row_cap'])
        require(all(f.rate_available_us<=at for rows in funding.values() for f in rows),'FUTURE_FUNDING_IN_NATIVE_PREFIX')
        budget.check();bundle=prepare_native(warmup,funding,at);budget.check()
        require(bundle.status=='AVAILABLE','NATIVE_INPUT_UNAVAILABLE:'+','.join(bundle.reasons))
        selectors=mark_selectors([specs[a['path']] for a in plan['allowlist'] if a['kind']=='mark'],permits)
        selections=[]
        for t in plan['mark_queries_us']:
            for i in instruments:
                budget.check();q=selectors[i].select(Query(i,t,tuple(plan['mark_roles'])))
                selections.append(dict(selection=q.dto(),lineage=q.lineage()));budget.check()
    native={}
    for symbol,sig in bundle.signals.items():
        native[symbol]=pack(asdict(sig))
    context=bundle.warmup_context
    fractional=[dict(instrument_id=f.instrument_id,source_us=f.source_us,ref=asdict(f.ref))
                for rows in funding.values() for f in rows if f.source_us%1_000_000]
    supported=all(s['selection']['status']=='SUPPORTED' for s in selections)
    return dict(status='SNAPSHOT_COMPUTED_FOR_REVIEW' if supported else 'SNAPSHOT_WITH_UNKNOWN_MARK',
        snapshot_us=at,source_exact=dict(last_closed_hour={i:asdict(warmup[i][-1]) for i in instruments},
            execution_opens=[asdict(o) for o in opens],units=dict(price='USDT_per_base',volume='decimal_contracts',time='integer_UTC_microseconds')),
        computed_native=dict(float_codec='finite_f64_hex_v1',signals=native,covariance=pack(bundle.covariance.to_numpy().tolist()),
            covariance_order=list(bundle.covariance.index),observations=[asdict(o) for o in bundle.observations],
            note='Computed decimal observation fields roundtrip native f64; they are not exact source prices'),
        warmup_identity=dict(context_sha256=context['context_sha256'],initializer=context['initial_timing_state'],
            native_code_sha256=context['native_code_sha256'],prefix={s:{k:v for k,v in p.items() if k!='funding_refs'} for s,p in context['prefix'].items()},
            encoded_cache_identity={s:{k:v for k,v in cache.items() if k!='payload'} for s,cache in context['prepared'].items()},
            funding_prefix_sha256=digest({i:[asdict(f) for f in rows] for i,rows in funding.items()})),
        mark_queries=selections,funding_integer_source_seconds=dict(compatible=not fractional,fractional_count=len(fractional),
            examples=fractional[:16],accounting_mapping_executed=False,no_rounding=True),
        runtime=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__),
        no_account=True,no_labels=True,no_fit=True,training_authorized=False)


def run(*,authorize_actual_snapshot=False,human_authorization_ref=None,manifest_sha256=None):
    if not authorize_actual_snapshot:
        return dict(status='OFF',reason='EXPLICIT_HUMAN_AUTHORIZATION_REQUIRED'),2
    require(type(human_authorization_ref) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{5,255}',human_authorization_ref) is not None,
            'NAMED_HUMAN_AUTHORIZATION_REFERENCE_REQUIRED')
    require(type(manifest_sha256) is str and re.fullmatch(r'[0-9a-f]{64}',manifest_sha256) is not None,'EXACT_REVIEWED_MANIFEST_SHA256_REQUIRED')
    # Metadata-only gate; no payload imports/consumption and no retry here.
    raw=MANIFEST.read_bytes();require(hashlib.sha256(raw).hexdigest()==manifest_sha256,'REVIEWED_MANIFEST_IDENTITY_MISMATCH')
    manifest=json.loads(raw);plan=manifest['snapshot_entry_plan']
    require(manifest['actual_history_execution']=='OFF' and plan['authorization_status']=='PROPOSED_REQUIRES_SEPARATE_HUMAN_AUTHORIZATION',
            'PLAN_IS_NOT_THE_REVIEWED_EXECUTION_OFF_PROPOSAL')
    require(local_path(plan['artifact_directory'])==ARTIFACTS,'FIXED_ONE_ATTEMPT_ARTIFACT_PATH_REQUIRED')
    budget=ObservationBudget(plan['limits']);local_path(str(ARTIFACTS))
    ARTIFACTS.mkdir(mode=0o700,parents=False,exist_ok=False)  # never reset/reuse/change attempt path
    parent_fd=os.open(ARTIFACTS.parent,os.O_RDONLY)
    try:os.fsync(parent_fd)  # persist the consumed-attempt directory itself
    finally:os.close(parent_fd)
    launched=False
    try:
        receipt=dict(status='ATTEMPT_CONSUMED_NO_RETRY_OR_RESUME',dispatch=DISPATCH,human_authorization_ref=human_authorization_ref,
            at_utc=datetime.now(timezone.utc).isoformat(),manifest_sha256=manifest_sha256,code_sha256=manifest['code_sha256'],
            snapshot_us=plan['snapshot_us'],limits=plan['limits'],raw_payload_consumption_at_receipt='NOT_STARTED',
            later_execution_without_terminal_summary='UNKNOWN',
            warning='Authorization reference is an operator assertion, not proof issued by this program; cooperative limits can overshoot')
        budget.output+=durable_new(ARTIFACTS/'launch-receipt.json',receipt,plan['limits']['output_bytes']-65536);launched=True
        with network_off():
            verify_identities(manifest,plan,budget)
            result=snapshot(manifest,plan,budget,human_authorization_ref);budget.check()
        result.update(human_authorization_ref=human_authorization_ref,manifest_sha256=manifest_sha256,
            observed=budget.observed(),objects=budget.objects,whole_selected_metadata_bytes=plan['whole_selected_metadata_bytes'],
            metadata_bytes_are_provenance_not_consumed_bytes=True,full_payload_sha_or_crc_revalidation=False)
        size=len(encoded(result));result['observed']['output_bytes_including_result_upper_bound']=budget.output+size+256
        budget.check();budget.output+=durable_new(ARTIFACTS/'result.json',result,plan['limits']['output_bytes']-budget.output-65536)
        return dict(status=result['status'],artifacts=str(ARTIFACTS)),0 if result['status']=='SNAPSHOT_COMPUTED_FOR_REVIEW' else 3
    except BaseException as e:
        # Catch interruption for a best-effort durable failure, then stop. Kill/
        # power loss can prevent this: receipt-only state remains UNKNOWN.
        if launched:
            # Include any result file whose write/fsync failed after allocation;
            # never spend its bytes a second time on a failure summary.
            budget.output=sum(p.stat().st_size for p in (ARTIFACTS/'launch-receipt.json',ARTIFACTS/'result.json',ARTIFACTS/'failure.json') if p.exists())
            failure=dict(status='FAILED_STOP_NO_RETRY_OR_RESUME',reason=type(e).__name__+':'+str(e)[:2048],
                observed=budget.observed(),objects=budget.objects,manifest_sha256=manifest_sha256,
                human_authorization_ref=human_authorization_ref,missing_input_reason=str(e)[:2048],
                planned_mark_query_times_us=plan['mark_queries_us'],query_evaluation_status='NOT_COMPLETED_NO_COVERAGE_CLAIM')
            try:durable_new(ARTIFACTS/'failure.json',failure,plan['limits']['output_bytes']-budget.output)
            except BaseException:pass  # receipt-only is UNKNOWN, never implicit retry approval
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-actual-snapshot',action='store_true',default=False)
    parser.add_argument('--human-authorization-ref')
    parser.add_argument('--manifest-sha256')
    args=parser.parse_args(argv)
    try:result,code=run(**vars(args))
    except BaseException as e:
        print(json.dumps(dict(status='STOPPED_NO_RETRY',reason=type(e).__name__+':'+str(e)[:2048]),sort_keys=True),file=sys.stderr);return 1
    print(json.dumps(result,sort_keys=True));return code


if __name__=='__main__':raise SystemExit(main())
