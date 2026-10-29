"""One explicitly authorized continuation; no raw-reader or new-account path."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

START_WALL=time.monotonic();START_CPU=time.process_time()
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'research/qd016/manifest.json'


def run(*,continue_approved=False,human_authorization_ref=None,manifest_sha256=None):
    if not continue_approved:return dict(status='OFF')
    raw=MANIFEST.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise ValueError('EXACT_CONTINUATION_MANIFEST_REQUIRED')
    m=json.loads(raw)
    if human_authorization_ref!=m['authorization_ref']:raise ValueError('EXACT_CONTINUATION_AUTHORITY_REQUIRED')
    for p,h in m['code_sha256'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('CODE_IDENTITY_MISMATCH:'+p)
    original=ROOT/m['original_manifest']['path'];old_raw=original.read_bytes()
    if hashlib.sha256(old_raw).hexdigest()!=m['original_manifest']['sha256']:raise ValueError('ORIGINAL_MANIFEST_MISMATCH')
    old=json.loads(old_raw);out=ROOT/m['artifact_directory'];store=ROOT/m['store_root']
    if (store/m['record_name']).exists():raise ValueError('CONTINUATION_ALREADY_CONSUMED_NO_RETRY')
    failure=(ROOT/m['prior_failure']['path']).read_bytes()
    if hashlib.sha256(failure).hexdigest()!=m['prior_failure']['sha256']:raise ValueError('BASELINE_FAILURE_MISMATCH')
    previous=json.loads(failure)['observed']
    from research.qd012.actual_snapshot_entry import ObservationBudget,durable_new,network_off
    from research.qd009 import streaming_ledger as sl
    from research.qd011.codec import pack
    from research.qd010.joint_native_bridge import research_config
    from research.qd011.ports import ControlledPort
    from research.qd013.market import MarketCache,cache_identity
    from research.qd013.runner import Replay
    from research.qd013.exports import export_all,write_bundle
    from research.qd015.cache_identity import producer_identity
    from .resident import ContinuationLedger
    limits=deepcopy(m['outer_limits'])
    limits['wall_seconds']-=previous['wall_seconds'];limits['cpu_seconds']-=previous['cpu_seconds']
    if min(limits['wall_seconds'],limits['cpu_seconds'])<=0:raise ValueError('CUMULATIVE_BUDGET_EXHAUSTED')
    budget=ObservationBudget(limits);budget.wall0=START_WALL;budget.cpu0=START_CPU
    out.mkdir(parents=True,exist_ok=False)
    p=old['execution_proposals']['full_p0']
    durable_new(out/'launch.json',dict(status='CONSUMED_NO_AUTOMATIC_RETRY',authorization_ref=human_authorization_ref,
        manifest_sha256=manifest_sha256,prior_observed=previous,remaining_limits=limits,operation=m['operation'],
        before={n:json.loads((store/n).read_bytes()) for n in ('HEAD','CONTROL','SPENT')}),1048576)
    ledger=cache=None
    def observed():
        current=budget.observed()
        return dict(current_invocation=current,cumulative=dict(wall_seconds=previous['wall_seconds']+current['wall_seconds'],
            cpu_seconds=previous['cpu_seconds']+current['cpu_seconds'],peak_rss_bytes=max(previous['peak_rss_bytes'],current['peak_rss_bytes']),
            physical_input_bytes=previous['physical_input_bytes'],expanded_input_bytes=previous['expanded_input_bytes'],
            physical_rows_yielded=previous['physical_rows_yielded']),raw_history_reads_this_invocation=0)
    try:
        with network_off():
            if producer_identity()!=old['market_producer_identity']:raise ValueError('MARKET_PRODUCER_CHANGED')
            identity=cache_identity(sources=p['allowlist'],code=old['market_producer_identity'],config=pack(asdict(research_config())),scope=p['scope'])
            if sl.digest(identity)!=m['cache_key']:raise ValueError('EXACT_CACHE_IDENTITY_REQUIRED')
            cache=MarketCache(ROOT/m['cache_path'],identity)
            if cache.meta['content_sha256']!=m['cache_content_sha256']:raise ValueError('CACHE_CONTENT_BINDING_MISMATCH')
            budget.check()
            allocation=sl.configure_resource_budget(ROOT/'research/.data/qd015',limits['output_bytes']-65536)
            req=sl.load_json((store/'GENESIS').read_bytes())
            if sl.digest(req['config']['schedule'])!=m['schedule_sha256']:raise ValueError('SCHEDULE_CHANGED')
            for d in req['config']['adapters']:sl.register_port(d,ControlledPort())
            ledger=ContinuationLedger(store,operation=m['operation'],record_name=m['record_name'],process_bound=budget.check)
            activation=ledger.activate();budget.check();replay=Replay(ledger)
            durable_new(out/'activated.json',dict(record=activation,head=ledger.head,spent=ledger.spent),1048576)
            for at in ledger.config['_plan_index'].times:
                if at<=ledger.head['cutoff']['at_us']:continue
                budget.check();replay.advance_chunk(at);budget.check()
                if allocation.total+allocation.book.stat().st_size>limits['output_bytes']:raise ValueError('TOTAL_OUTPUT_LIMIT')
            end=ledger.config['_plan_index'].times[-1]
            records=export_all(replay,end);budget.check()
            exported=write_bundle(out/'export-P0-ALLOW_ALL',records,dict(cache_key=cache.key,ledger_head=ledger.head,
                source_manifest=old['validation_evidence'].get('source_manifest',m['original_manifest']['sha256']),
                continuation_manifest=manifest_sha256),write_budget=allocation.issue)
            statuses={}
            for r in records:
                s=r['qr014_episode_fields']['label_status'];statuses[s]=statuses.get(s,0)+1
            result=dict(status='FULL_CONTINUOUS_P0_COMPLETED',head=ledger.head,cache_key=cache.key,
                export=exported,label_status_counts=statuses,observed=observed(),spent=ledger.spent,scope=p['scope'],training_authorized=False)
            durable_new(out/'result.json',result,1048576)
            return result
    except BaseException as e:
        result=dict(status='STOPPED_NO_AUTOMATIC_RETRY',reason=type(e).__name__+':'+str(e),observed=observed(),
            head=ledger.current_head() if ledger else None,spent=ledger.spent if ledger else None,training_authorized=False)
        try:durable_new(out/'failure.json',result,1048576)
        except BaseException:pass
        raise
    finally:
        if ledger:ledger.close()
        if cache:cache.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--continue-approved',action='store_true')
    p.add_argument('--human-authorization-ref');p.add_argument('--manifest-sha256');a=p.parse_args()
    try:print(json.dumps(run(**vars(a)),sort_keys=True));return 0
    except BaseException as e:print(json.dumps(dict(status='STOPPED_NO_AUTOMATIC_RETRY',reason=type(e).__name__+':'+str(e))),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
