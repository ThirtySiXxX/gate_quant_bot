"""Stop one known replay writer and copy its current checkpoint, never its genesis."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import time
from research.qd019.migration import STORE,read,sha,require,inventory,verify_code

ROOT=Path(__file__).resolve().parents[2]


def process_info(pid):
    p=Path('/proc')/str(pid)
    # comm can contain spaces and parentheses; fields after the final ')' start
    # with Linux stat field 3 (state). starttime protects against PID reuse.
    fields=(p/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,state=fields[0],start_ticks=int(fields[19]),
                cpu_ticks=int(fields[11])+int(fields[12]),clock_ticks_per_second=os.sysconf('SC_CLK_TCK'))


def replay_processes(root,module='research.qd019.entry',manifest_path=None):
    found=[]
    if not Path('/proc').is_dir():return found
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().split(b'\0')
            if not any(args[i:i+2]==[b'-m',module.encode()] for i in range(len(args)-1)):continue
            if (p/'cwd').resolve()!=root:continue
            if manifest_path is not None:
                if b'--manifest' not in args:
                    require(module=='research.qd019.entry','OPTIMIZED_PROCESS_HAS_NO_FIXED_MANIFEST_REVIEW_REQUIRED')
                    argument=root/'research/.data/qd019-import/migration.json'
                else:argument=Path(os.fsdecode(args[args.index(b'--manifest')+1]))
                if not argument.is_absolute():argument=root/argument
                if argument.resolve()!=manifest_path.resolve():continue
            found.append(process_info(int(p.name)))
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    return found


def stop_writer(root,module='research.qd019.entry',manifest_path=None):
    matches=replay_processes(root,module,manifest_path)
    require(len(matches)<=1,'MULTIPLE_REPLAY_WRITERS_REVIEW_REQUIRED')
    if not matches:return None
    original=matches[0];os.kill(original['pid'],signal.SIGSTOP)
    for _ in range(500):
        current=process_info(original['pid'])
        require(current['start_ticks']==original['start_ticks'],'REPLAY_PID_CHANGED')
        if current['state'] in ('T','t'):return current
        time.sleep(.01)
    raise ValueError('SOURCE_PROCESS_DID_NOT_STOP')


def source_location(root):
    current=root/'research/.data/qd021-handoff/current.json'
    if current.exists():
        previous=read(current)
        data=Path(previous['active_data_root']).resolve()
        return data,Path(previous['base_manifest_path']),previous['old_data_roots']+[str(data)]
    base=root/'research/.data/qd019-import/migration.json'
    m=read(base);data=base.parent/'qd015'
    return data,base,[m['old_data_root'],str(data)]


def check_previous_failure(data):
    runs=list(data.glob('optimization-run-*'))+[data/'migration-run-1']
    for run in runs:
        if (run/'result.json').exists():
            require(read(run/'result.json')['status']!='FULL_CONTINUOUS_P0_COMPLETED','REPLAY_ALREADY_COMPLETED_COLLECT_RESULTS')
        if (run/'failure.json').exists():
            reason=read(run/'failure.json').get('reason','')
            # A fresh optimization may waive only former host resource quotas.
            # Schema/integrity errors are never an excuse for automatic retries.
            from .cold import ALLOWED_OLD_QUOTAS
            known_ledger_quota=(reason.startswith('LedgerError:RESOURCE_EXHAUSTED at ') and
                                reason.split(' at ',1)[1] in ALLOWED_OLD_QUOTAS)
            require(known_ledger_quota or any(reason=='ValueError:'+x for x in
                    ('OBSERVED_WALL_SECONDS_LIMIT','OBSERVED_CPU_SECONDS_LIMIT','OBSERVED_RSS_BYTES_LIMIT',
                     'TOTAL_OUTPUT_LIMIT','CUMULATIVE_BUDGET_EXHAUSTED')),
                    'PREVIOUS_NONQUOTA_FAILURE_REQUIRES_REVIEW:'+reason)


def prepare(root=ROOT):
    root=Path(root).resolve();release=read(root/'research/qd021/release.json')
    verify_code(root,release['code_sha256'])
    data,base_path,old_roots=source_location(root)
    require(data.is_relative_to(root/'research/.data'),'SOURCE_OUTSIDE_LOCAL_RESEARCH_DATA')
    base=read(base_path)
    require(sha(base_path)==release['base_manifest_sha256'],'BASE_MANIFEST_IDENTITY_MISMATCH')
    from research.qd019.sqlite_host import prepare_sqlite_host
    prepare_sqlite_host()
    # Do slow admission checks before freezing the current writer.
    require(sha(data/base['cache_relative_path'])==base['inventory'][base['cache_relative_path']]['sha256'],
            'IMMUTABLE_CACHE_CHANGED')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=root/'research/.data/qd021-handoff';evidence.mkdir(exist_ok=True,parents=True)
    # Serialize installers too; the ledger's LEASE belongs to the paused source.
    with (evidence/'PREPARE_LEASE').open('a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current=evidence/'current.json'
        previous=read(current) if current.exists() else None
        fixed=evidence/(previous['operation_id']+'.json') if previous else base_path
        stopped=stop_writer(root,'research.qd021.entry' if previous else 'research.qd019.entry',fixed)
        if stopped:print('Original replay paused. It will remain paused; do not resume it while the new copy runs.',flush=True)
        lease=None
        try:
            if stopped is None:
                lease=(data/STORE/'LEASE').open('a+b');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            check_previous_failure(data)
            before=inventory(data)
            head=read(data/STORE/'HEAD')
            target=root/'research/.data/qd021-active'/stamp/'qd015'
            target.parent.mkdir(exist_ok=False,parents=True)
            print('Copying the current checkpoint at sequence '+str(head['committed_seq'])+'...',flush=True)
            shutil.copytree(data,target)
            require(inventory(target)==before,'SNAPSHOT_COPY_HASH_MISMATCH')
            require(read(data/STORE/'HEAD')==head,'SOURCE_CHANGED_DURING_COPY')
            for p in target.rglob('*'):
                if p.is_file():
                    with p.open('rb') as f:os.fsync(f.fileno())
            for directory in [p for p in target.rglob('*') if p.is_dir()]+[target,target.parent]:
                fd=os.open(directory,os.O_RDONLY)
                try:os.fsync(fd)
                finally:os.close(fd)
            observation=None
            for p in sorted(data.glob('optimization-run-*/progress.json'))+[data/'migration-run-1/progress.json']:
                if p.exists():observation=read(p).get('observed')
            manifest=dict(schema='qd021.handoff.v1',operation_id=stamp,active_data_root=str(target),
                base_manifest_path=str(base_path),source_head=head,old_data_roots=old_roots,
                immutable_cache_sha256=base['inventory'][base['cache_relative_path']]['sha256'],
                prior_source_observation=observation,source_snapshot=dict(source_data_root=str(data),
                process=stopped,files=len(before),bytes=sum(v['bytes'] for v in before.values()),
                inventory_sha256=__import__('hashlib').sha256(json.dumps(before,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                pointers={name:sha(data/STORE/name) for name in ('HEAD','CONTROL','SPENT','AUDIT')}))
            raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
            with (evidence/(stamp+'.json')).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            temp=evidence/('current-'+stamp+'.tmp')
            with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(temp,evidence/'current.json')
            fd=os.open(evidence,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
            print('Ready at current sequence '+str(head['committed_seq'])+'. Start: bash scripts/qd021/run-fast.sh',flush=True)
            return manifest
        except BaseException as error:
            receipt=dict(status='HANDOFF_STOPPED_NO_AUTOMATIC_RETRY',reason=type(error).__name__+':'+str(error),
                         source_data_root=str(data),source_process=stopped,original_retained=True)
            with (evidence/(stamp+'-failure.json')).open('x') as f:
                json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
            raise
        finally:
            if lease:lease.close()
            # No SIGCONT: two divergent account continuations must never run.


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    try:prepare()
    except BaseException as e:
        print('HANDOFF_STOPPED_NO_RETRY: '+type(e).__name__+':'+str(e),flush=True)
        print('Source data retained. If a replay was paused, leave it paused and send this error.');raise SystemExit(1)
