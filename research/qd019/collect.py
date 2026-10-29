"""Collect a small local result bundle; never rerun the ledger or upload data."""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import tarfile
from .migration import STORE, read, sha

ROOT = Path(__file__).resolve().parents[2]


def collect(log=None):
    bundle = ROOT/'research/.data/qd019-import'; data = bundle/'qd015'
    store = data/STORE; run = data/'migration-run-1'
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT/f'return-to-codex-{stamp}.tar.gz'
    files = []
    if (bundle/'migration.json').exists():
        files.append((bundle/'migration.json','migration-manifest.json'))
    if (bundle/'host-fix-1.json').exists():
        files.append((bundle/'host-fix-1.json','compatibility/host-fix-1.json'))
    for name in ('launch','activated','runtime-validation','progress','result','failure'):
        p=run/(name+'.json')
        if p.exists(): files.append((p,'run/'+p.name))
    for name in ('HEAD','CONTROL','SPENT','AUDIT','MIGRATION-RESUME-1.json'):
        p=store/name
        if p.exists(): files.append((p,'checkpoint/'+name))
    if (store/'CONTROL').exists():
        c=read(store/'CONTROL');p=store/f"control-{c['control_seq']:08}.json"
        if p.exists():files.append((p,'checkpoint/'+p.name))
    for name in ('manifest.json','episodes.jsonl'):
        p=run/'export-P0-ALLOW_ALL'/name
        if p.exists():files.append((p,'export-P0-ALLOW_ALL/'+name))
    if log:
        p=Path(log).resolve()
        if not p.is_relative_to((ROOT/'local-logs').resolve()):raise ValueError('LOG_MUST_BE_LOCAL_RUN_LOG')
        files.append((p,'run/console.log'))
    summary=dict(schema='qd019.return-summary.v1',training_authorized=False,
                 files={name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p,name in files})
    # Cached read-only view, without reopening/replaying an economic ledger.
    if (store/'HEAD').exists():
        h=read(store/'HEAD');summary['head']=h
        try:
            db=sqlite3.connect((store/'cache.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)
            try:
                row=db.execute("SELECT b FROM views WHERE json_extract(b,'$.knowledge_cutoff.at_us')=? AND json_extract(b,'$.knowledge_cutoff.slot')=? LIMIT 1",
                               (h['cutoff']['at_us'],h['cutoff']['slot'])).fetchone()
                summary['cached_view']=json.loads(row[0]) if row else None
            finally:db.close()
        except sqlite3.Error as e:summary['cached_view_unavailable']=str(e)
    import io
    with tarfile.open(output,'x:gz') as tar:
        raw=(json.dumps(summary,sort_keys=True,indent=2)+'\n').encode();info=tarfile.TarInfo('return-summary.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        for p,name in files:tar.add(p,arcname=name,recursive=False)
    print('Return bundle:',output)
    print('SHA256:',sha(output))
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--log');a=p.parse_args();collect(a.log)
