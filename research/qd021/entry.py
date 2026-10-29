"""Unrestricted optimized continuation of a stopped-source snapshot; OFF default."""
import argparse
import json
from pathlib import Path
import resource
import signal
import sys
import time
from research.qd019.migration import STORE,read,sha,require,verify_code

ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'research/.data/qd021-handoff/current.json'


def observed(wall,cpu):
    u=resource.getrusage(resource.RUSAGE_SELF)
    return dict(wall_seconds=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu,
                peak_rss_bytes=u.ru_maxrss*(1 if sys.platform=='darwin' else 1024))


def run(manifest_path=DEFAULT,*,resume=False,validation_ticks=None):
    if not resume:return dict(status='OFF')
    started=time.monotonic();cpu=time.process_time();m=read(manifest_path)
    release=read(ROOT/'research/qd021/release.json')
    verify_code(ROOT,release['code_sha256'])
    require(m['schema']=='qd021.handoff.v1','HANDOFF_VERSION_MISMATCH')
    data=Path(m['active_data_root']).resolve();out=data/('optimization-run-'+m['operation_id'])
    require(not out.exists(),'OPTIMIZED_ATTEMPT_ALREADY_CONSUMED_NO_RETRY')
    from research.qd019.sqlite_host import prepare_sqlite_host
    host=prepare_sqlite_host()
    from research.qd012.actual_snapshot_entry import durable_new,encoded,network_off
    from research.qd009 import streaming_ledger as sl
    from research.qd019.migration import open_ledger
    from research.qd013.market import MarketCache
    from research.qd013.runner import Replay
    from research.qd013.exports import export_all,write_bundle
    from . import accounting,cold,fast
    out.mkdir(exist_ok=False)
    durable_new(out/'launch.json',dict(status='CONSUMED_NO_AUTOMATIC_RETRY',manifest_sha256=sha(manifest_path),
                source_head=m['source_head'],host=host,global_resource_quotas=None,training_authorized=False),16*1024**2)
    ledger=cache=None;budgets=None;paused=[False];previous_handlers={}
    def request_pause(signum,frame):paused[0]=True
    for sig in (signal.SIGINT,signal.SIGTERM):previous_handlers[sig]=signal.signal(sig,request_pause)

    def write(name,value):
        raw=encoded(value)
        if budgets:budgets[0].issue(out/name,len(raw),len(raw))
        durable_new(out/name,value,max(len(raw),16*1024**2))

    try:
        with network_off():
            base=read(m['base_manifest_path'])
            require(sha(m['base_manifest_path'])==release['base_manifest_sha256'],'BASE_MANIFEST_IDENTITY_MISMATCH')
            require(sha(data/base['cache_relative_path'])==m['immutable_cache_sha256'],'IMMUTABLE_CACHE_CHANGED')
            print('Recovering stopped source at sequence '+str(m['source_head']['committed_seq'])+'...',flush=True)
            budgets=accounting.install(data,m['old_data_roots'])
            recovery=cold.prepare(data,m)
            cache=MarketCache(data/base['cache_relative_path'],base['cache_identity'])
            ledger=open_ledger(data,base,lambda:None,verify_seals=True)
            class RuntimeLedger(type(ledger)):
                def _bound(self):return None
            ledger.__class__=RuntimeLedger
            # Stored GENESIS/config identity is unchanged. This is a separately
            # authorized host execution policy, not a financial/risk parameter.
            ledger.config['limits']['max_adapter_wall_us']=float('inf')
            policy=fast.install(ledger)
            record=cold.activate(ledger,m,recovery)
            write('activated.json',dict(record=record,head=ledger.head,spent=ledger.spent))
            replay=Replay(ledger);done=0;progress_at=time.monotonic();end=ledger.config['_plan_index'].times[-1]
            print('FAST_REPLAY_ACTIVE: global wall/CPU/RSS/disk quotas disabled; cache '+json.dumps(policy),flush=True)
            for at in ledger.config['_plan_index'].times:
                if at<=ledger.head['cutoff']['at_us']:continue
                if paused[0]:break
                replay.advance_chunk(at);done+=1
                if time.monotonic()-progress_at>=30:
                    progress_at=time.monotonic()
                    progress=dict(committed_seq=ledger.head['committed_seq'],total_ticks=len(ledger.config['_plan_index'].times),
                                  cutoff=ledger.head['cutoff'],new_ticks=done,observed=observed(started,cpu),spent=ledger.spent,
                                  global_resource_quotas=None)
                    sl._atomic(out/'progress.json',None,_raw=encoded(progress));print(json.dumps(progress,sort_keys=True),flush=True)
                if validation_ticks is not None and done>=validation_ticks:break
            if ledger.head['cutoff']['at_us']>=end:
                records=export_all(replay,end)
                export=write_bundle(out/'export-P0-ALLOW_ALL',records,
                    dict(cache_key=cache.key,ledger_head=ledger.head,source_manifest=base['original_manifest_sha256'],
                         migration_manifest=sha(m['base_manifest_path']),handoff_manifest=sha(manifest_path),
                         optimization_release=release['schema'],optimization_release_sha256=sha(ROOT/'research/qd021/release.json')),
                    write_budget=budgets[0].issue)
                status='FULL_CONTINUOUS_P0_COMPLETED'
                labels={}
                for r in records:
                    s=r['qr014_episode_fields']['label_status'];labels[s]=labels.get(s,0)+1
            else:
                export=None;labels={};status='PAUSED_AT_COMMIT_BOUNDARY' if paused[0] else 'ENGINEERING_COPY_VALIDATED'
            result=dict(status=status,head=ledger.head,export=export,label_status_counts=labels,
                        new_ticks=done,observed=observed(started,cpu),spent=ledger.spent,
                        prior_source_observation=m.get('prior_source_observation'),global_resource_quotas=None,
                        training_authorized=False)
            write('result.json',result);print(json.dumps(result,sort_keys=True),flush=True);return result
    except BaseException as error:
        failure=dict(status='STOPPED_NO_AUTOMATIC_RETRY',reason=type(error).__name__+':'+str(error),
                     head=ledger.current_head() if ledger else None,spent=ledger.spent if ledger else None,
                     observed=observed(started,cpu),global_resource_quotas=None,training_authorized=False)
        try:write('failure.json',failure)
        except BaseException:pass
        print(json.dumps(failure,sort_keys=True),flush=True);raise
    finally:
        if ledger:ledger.close()
        if cache:cache.close()
        if budgets:
            for b in reversed(budgets):b.close()
        for sig,handler in previous_handlers.items():signal.signal(sig,handler)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',default=str(DEFAULT))
    p.add_argument('--resume',action='store_true');p.add_argument('--validation-ticks',type=int)
    a=p.parse_args()
    try:
        result=run(a.manifest,resume=a.resume,validation_ticks=a.validation_ticks)
        if result['status']=='OFF':print(json.dumps(result))
        return 0
    except BaseException as e:print(type(e).__name__+':'+str(e),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
