"""QD015 compressed-journal full P0 candidate. Default OFF; no prior approval reuse.

No actual history execution is authorized by implementing this module. Only a
new reviewed named reference plus exact manifest identity can enter a run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'research/qd015/manifest.json'
AUTH_PATTERN=r'QF-APPROVAL-QD015-FULL-P0-[1-9][0-9]*'


def run(*,authorize_actual_replay=False,human_authorization_ref=None,manifest_sha256=None,scope='full_p0',resume=False):
    if not authorize_actual_replay:return dict(status='OFF',reason='NEW_EXPLICIT_REPLAY_AUTHORIZATION_REQUIRED')
    if not re.fullmatch(AUTH_PATTERN,human_authorization_ref or ''):raise ValueError('NAMED_QD015_APPROVAL_REFERENCE_REQUIRED')
    if resume:raise ValueError('RESUME_REQUIRES_SEPARATE_OPERATION_REVIEW_NOT_AUTOMATIC_RETRY')
    raw=MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise ValueError('EXACT_REVIEWED_MANIFEST_SHA_REQUIRED')
    m=json.loads(raw)
    if scope!='full_p0':raise ValueError('UNDECLARED_SCOPE')
    p=m['execution_proposals'][scope]
    if human_authorization_ref!=p['proposed_authorization_ref']:raise ValueError('APPROVAL_SCOPE_MISMATCH')
    # All source code/metadata identities checked before raw data access. The
    # existing snapshot entry is not invoked; only its simple budget/IO helpers
    # are reused to avoid creating another supervision platform.
    for relative,h in m['code_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=h:raise ValueError('CODE_IDENTITY_MISMATCH:'+relative)
    for item in m['metadata_identities']:
        if hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('METADATA_IDENTITY_MISMATCH')
    from research.qd012.actual_snapshot_entry import ObservationBudget,bounded_inputs,network_off,durable_new
    from research.qd012 import sources
    from research.qd012.prepare import read_hour_prefix,read_funding_prefix
    from research.qd012.queries import mark_objects
    from research.qd011.codec import pack
    from research.qd010.joint_native_bridge import research_config
    from dataclasses import asdict
    from research.qd013.market import MarketCache,cache_identity
    from research.qd013.inputs import build_cache
    from .runner import create
    from .cache_identity import producer_identity
    from research.qd013.exports import export_all,write_bundle
    from research.qd009 import streaming_ledger as sl
    out=ROOT/p['artifact_directory'];out.mkdir(parents=True,exist_ok=False)
    import os
    fd=os.open(out.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    budget=ObservationBudget(p['limits']);budget.output=durable_new(out/'launch.json',dict(status='CONSUMED_NO_RETRY',human_authorization_ref=human_authorization_ref,
        manifest_sha256=manifest_sha256,proposal=p),p['limits']['output_bytes']-65536)
    try:
        with network_off():
            producer=producer_identity()
            if producer!=m['market_producer_identity']:raise ValueError('MARKET_PRODUCER_IDENTITY_MISMATCH')
            identity=cache_identity(sources=p['allowlist'],code=producer,config=pack(asdict(research_config())),scope=p['scope'])
            key=sl.digest(identity);cache_path=ROOT/'research/.data/qd015/markets'/(key+'.sqlite3')
            work={}
            if cache_path.exists():cache=MarketCache(cache_path,identity);work['cache_hit']=True
            else:
                legacy=cache_identity(sources=p['allowlist'],code=m['legacy_cache_code_sha256'],config=pack(asdict(research_config())),scope=p['scope'])
                legacy_path=ROOT/'research/.data/qd014/markets'/(sl.digest(legacy)+'.sqlite3')
                if legacy_path.exists():raise ValueError('LEGACY_FULL_CACHE_PRESENT_EXPLICIT_COMPATIBLE_BINDING_REQUIRED_NO_RAW_REBUILD')
                existing_output=sum(f.stat().st_size for f in (ROOT/'research/.data/qd015').rglob('*') if f.is_file())
                def cache_watch(path,db,count,next_bytes):
                    if count%256:return
                    budget.check()
                    logical=db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]
                    if existing_output+logical+next_bytes>p['limits']['output_bytes']:raise ValueError('OBSERVED_CACHE_OUTPUT_LIMIT')
                specs={a['path']:sources.ObjectSpec(**a['object']) for a in p['allowlist']};permits={}
                for a in p['allowlist']:
                    x=a['permit'];s=specs[a['path']]
                    permits[s.path]=sources.ReadPermit(human_authorization_ref,(s.path,),s.manifest_sha256,x['start_us'],x['end_us'],x['physical_rows'],x['expanded_input_bytes'],kind='separately_approved_actual_history')
                with bounded_inputs(sources,budget,p['allowlist']):
                    hours=read_hour_prefix([specs[a['path']] for a in p['allowlist'] if a['kind']=='ohlcv'],permits,max_hours_per_instrument=p['hour_cap'])
                    funding=read_funding_prefix([specs[a['path']] for a in p['allowlist'] if a['kind']=='funding'],permits,max_records=p['funding_cap'])
                    marks={i:mark_objects([specs[a['path']] for a in p['allowlist'] if a['kind']=='mark' and a['object']['instrument_id']==i],permits) for i in m['instruments']}
                    cache=build_cache(cache_path,identity,hours=hours,funding=funding,mark_streams=marks,
                        initial_us=p['scope']['initial_us'],economic_end_us=p['scope']['economic_end_us'],work=work,write_budget=cache_watch)
                del hours,funding,marks
            budget.check()
            # Existing persistent quota guards ledger writes; cache/build outputs
            # are included in the separate total-size observation below.
            allocation=sl.configure_resource_budget(ROOT/'research/.data/qd015',p['limits']['output_bytes']-65536)
            accounts=[]
            for item in p['trajectories']:
                replay=create(out/(item['scenario']+'-'+item['policy']),cache,initial_us=p['scope']['initial_us'],
                    economic_end_us=p['scope']['economic_end_us'],tail_end_us=p['scope']['tail_end_us'],scenario_id=item['scenario'],policy_id=item['policy'],write_budget=allocation.issue,ledger_limits=p['ledger_limits'],journal_profile=m['journal_storage'])
                try:
                    for tick in replay.ledger.config['_plan_index']:
                        budget.check();replay.advance_chunk(tick['at_us']);budget.check()
                        size=allocation.total+allocation.book.stat().st_size
                        if size>p['limits']['output_bytes']:raise ValueError('OBSERVED_OUTPUT_LIMIT')
                    end=replay.ledger.config['_plan_index'].times[-1];records=export_all(replay,end)
                    exported=write_bundle(out/('export-'+item['scenario']+'-'+item['policy']),records,
                        dict(cache_key=cache.key,ledger_head=replay.ledger.head,source_manifest=manifest_sha256),write_budget=allocation.issue)
                    accounts.append(dict(scenario=item,head=replay.ledger.head,export=exported))
                finally:replay.ledger.close()
            cache.close();result=dict(status='FINITE_REPLAY_COMPLETED_RESEARCH_ONLY',accounts=accounts,work=work,
                observed=budget.observed(),input_objects=budget.objects,training_authorized=False,scope=p['scope'])
            durable_new(out/'result.json',result,p['limits']['output_bytes']-budget.output-65536)
            return result
    except BaseException as e:
        try:durable_new(out/'failure.json',dict(status='STOPPED_NO_RETRY',reason=type(e).__name__+':'+str(e),observed=budget.observed()),65536)
        except BaseException:pass
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authorize-actual-replay',action='store_true')
    p.add_argument('--human-authorization-ref');p.add_argument('--manifest-sha256');p.add_argument('--scope',choices=('full_p0',),default='full_p0')
    a=p.parse_args()
    try:r=run(**vars(a));print(json.dumps(r,sort_keys=True));return 0 if r.get('status')!='OFF' else 2
    except BaseException as e:print(json.dumps(dict(status='STOPPED_NO_RETRY',reason=type(e).__name__+':'+str(e))),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
