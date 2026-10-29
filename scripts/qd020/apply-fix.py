"""Run the small bundled repair from the existing Ubuntu project directory."""
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()


def need(ok, message):
    if not ok:raise SystemExit(message)


def safe(root, name):
    p=Path(name);need(not p.is_absolute() and '..' not in p.parts,'Unsafe repair path')
    result=root/p
    need(not any(x.is_symlink() for x in (result,*result.parents)),'Repair path must not contain symlinks')
    return result


def failure_receipt(root, patch):
    known=patch['reported_failure'];archive=root/known['filename']
    need(archive.is_file() and sha(archive)==known['sha256'],
         'Keep the original return-to-codex failure archive in the project directory.')
    with tarfile.open(archive,'r:gz') as t:
        names=t.getnames();need('run/launch.json' not in names and 'run/activated.json' not in names,
                               'A replay was already admitted; stop for review.')
        console=t.extractfile('run/console.log').read()
        need(b"module '_sqlite3' has no attribute '__file__'" in console,'Unexpected original failure')
    logs=[p for p in (root/'local-logs').glob('qd019-*.log') if p.read_bytes()==console]
    need(len(logs)==1,'Expected exactly one matching original startup log; stop for review.')
    match=re.fullmatch(r'qd019-(\d{8}T\d{6}Z)\.log',logs[0].name)
    need(match is not None,'Unrecognized startup log timestamp')
    start=dt.datetime.strptime(match[1],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
    end=dt.datetime.strptime(archive.name[len('return-to-codex-'):-len('.tar.gz')],'%Y%m%dT%H%M%S%fZ').replace(tzinfo=dt.timezone.utc)
    elapsed=math.ceil((end-start).total_seconds())+1
    need(elapsed>=0,'Clock interval is inconsistent; stop for review.')
    cpus=os.cpu_count();need(cpus is not None and cpus>0,'Cannot conservatively bound prior CPU use')
    return dict(schema='qd020.preadmission-failure.v1',base_manifest_sha256=patch['base_manifest_sha256'],
                preadmission_failures=1,wall_seconds_upper_bound=elapsed,cpu_seconds_upper_bound=elapsed*cpus,
                logical_cpu_count_upper_bound=cpus,
                method='UTC_LOG_INTERVAL_PLUS_ONE_SECOND_CPU_BOUNDED_BY_ALL_LOGICAL_CPUS_NOT_MEASURED_CPU',
                evidence=[dict(path=p.relative_to(root).as_posix(),sha256=sha(p)) for p in (archive,logs[0])])


def main():
    bundle=Path(__file__).resolve().parent;root=Path.cwd().resolve()
    need(sys.platform=='linux' and sys.version_info[:3]==(3,13,7),'Use the project .venv Python inside Ubuntu.')
    need(Path(sys.prefix).resolve()==(root/'.venv').resolve(),'Run this command from the existing project, using .venv/bin/python.')
    patch=json.loads((bundle/'patch.json').read_bytes())
    incoming=root/'research/.data/qd019-import';data=incoming/'qd015'
    need(sha(incoming/'migration.json')==patch['base_manifest_sha256'],'Unexpected data handoff manifest; no changes made.')
    manifest=json.loads((incoming/'migration.json').read_bytes())
    store=data/'full-p0-actual-1/P0-ALLOW_ALL/store'
    need(not (data/'migration-run-1/launch.json').exists() and not (store/'MIGRATION-RESUME-1.json').exists(),
         'A replay was already admitted. Do not remove its records; stop for review.')
    for name in ('HEAD','CONTROL','SPENT','GENESIS'):
        rel='full-p0-actual-1/P0-ALLOW_ALL/store/'+name
        need(sha(store/name)==manifest['inventory'][rel]['sha256'],'Account evidence has changed; stop for review.')
    for name,spec in patch['files'].items():
        target=safe(root,name);source=safe(bundle/'payload',name)
        need(sha(source)==spec['after'],'Corrupt repair payload: '+name)
        if target.exists():need(sha(target) in (spec['before'],spec['after']),'Local source was modified; preserved: '+name)
        else:need(spec['before'] is None,'Required original source file is missing: '+name)
    wheel=safe(bundle,patch['wheel']['filename'])
    need(sha(wheel)==patch['wheel']['sha256'],'Repair dependency wheel hash mismatch')
    receipt=failure_receipt(root,patch)
    receipt_path=incoming/'host-fix-1.json'
    if receipt_path.exists():need(json.loads(receipt_path.read_bytes())==receipt,'Prior repair accounting differs; stop for review.')
    uv=Path.home()/'.local/bin/uv';need(uv.is_file(),'Existing setup uv executable was not found.')
    subprocess.run([str(uv),'pip','install','--python',str(root/'.venv/bin/python'),
                    '--no-deps','--no-index',str(wheel)],check=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=root/'research/.data/qd020-code-backup'/stamp;backup.mkdir(parents=True,exist_ok=False)
    for name,spec in patch['files'].items():
        target=safe(root,name)
        if target.exists() and sha(target)==spec['after']:continue
        if target.exists():
            saved=safe(backup,name);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(target.read_bytes())
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.qd020.pending')
        with temp.open('xb') as f:f.write(safe(bundle/'payload',name).read_bytes());f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    if not receipt_path.exists():
        with receipt_path.open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    print('Source-only repair applied. Original dataset, failed log and return archive preserved.',flush=True)
    print('Conservative failed-start budget debit:',receipt['wall_seconds_upper_bound'],'wall seconds,',receipt['cpu_seconds_upper_bound'],'CPU seconds.',flush=True)
    subprocess.run([str(root/'.venv/bin/python'),'-B','-m','research.qd019.entry','--check'],check=True)
    print('Repair preflight passed. Start with: bash scripts/qd019/run-local-replay.sh',flush=True)


if __name__=='__main__':main()
