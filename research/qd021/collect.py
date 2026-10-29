"""Export compact local evidence; never upload or replay the account."""
import argparse
import datetime
import io
import json
from pathlib import Path
import tarfile
from research.qd019.migration import STORE,read,sha

ROOT=Path(__file__).resolve().parents[2]


def collect(log=None):
    manifest=ROOT/'research/.data/qd021-handoff/current.json';m=read(manifest)
    data=Path(m['active_data_root']);store=data/STORE;run=data/('optimization-run-'+m['operation_id'])
    files=[(manifest,'handoff.json'),(ROOT/'research/qd021/release.json','release.json')]
    for name in ('launch.json','activated.json','progress.json','result.json','failure.json'):
        if (run/name).exists():files.append((run/name,'run/'+name))
    for name in ('HEAD','CONTROL','SPENT','AUDIT','PERFORMANCE-CONTINUATION-'+m['operation_id']+'.json'):
        if (store/name).exists():files.append((store/name,'checkpoint/'+name))
    if (store/'CONTROL').exists():
        name=f"control-{read(store/'CONTROL')['control_seq']:08}.json";files.append((store/name,'checkpoint/'+name))
    for name in ('manifest.json','episodes.jsonl'):
        p=run/'export-P0-ALLOW_ALL'/name
        if p.exists():files.append((p,'export-P0-ALLOW_ALL/'+name))
    if log:
        p=Path(log).resolve()
        if not p.is_relative_to(ROOT/'local-logs'):raise ValueError('LOG_OUTSIDE_LOCAL_LOGS')
        files.append((p,'run/console.log'))
    summary=dict(schema='qd021.return.v1',head=read(store/'HEAD'),training_authorized=False,
                 files={name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p,name in files})
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=ROOT/('return-to-codex-qd021-'+stamp+'.tar.gz')
    with tarfile.open(output,'x:gz') as tar:
        raw=(json.dumps(summary,sort_keys=True,indent=2)+'\n').encode();info=tarfile.TarInfo('summary.json');info.size=len(raw)
        tar.addfile(info,io.BytesIO(raw))
        for p,name in files:tar.add(p,arcname=name,recursive=False)
    print('Return bundle:',output);print('SHA256:',sha(output));return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--log');a=p.parse_args();collect(a.log)
