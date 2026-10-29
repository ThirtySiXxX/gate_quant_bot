"""Freeze only the approved local research root; make an explicit handoff."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from .migration import (SCHEMA, STORE, inventory, read, require, runtime, sha,
                        verify_inventory)

ROOT = Path(__file__).resolve().parents[2]


def put(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write('\n')


def build(output, pid):
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'research/.data/qd015'
    command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'stat=,command='], text=True)
    require('T' in command.split()[0] and 'research.qd016.entry --continue-approved' in command,
            'SOURCE_PROCESS_MUST_REMAIN_SUSPENDED')
    source_inventory = inventory(source)
    require(not any(Path(n).name in ('.env', 'config.yaml', 'credentials.json') for n in source_inventory),
            'SENSITIVE_FILE_IN_RESEARCH_ROOT')
    payload = output / 'payload/research/.data/qd019-import'; payload.mkdir(parents=True)
    data = payload / 'qd015'; shutil.copytree(source, data)
    verify_inventory(data, source_inventory); verify_inventory(source, source_inventory)
    old = read(ROOT/'research/qd015/manifest.json'); resume = read(ROOT/'research/qd016/manifest.json')
    store = data / STORE; genesis = read(store/'GENESIS'); head = read(store/'HEAD')
    require(head['committed_seq'] == 1026 and head['audit_prefix'] ==
            '7152d4294c0e71df250ef03632d865c101a1c8ae9d3c80d3826b03059ca4340d', 'EXPECTED_PAUSED_ACCOUNT')
    control = read(store/'CONTROL'); guard = read(store/f"control-{control['control_seq']:08}.json")
    prior_failure = read(data/'full-p0-actual-1/failure.json')['observed']
    source_runtime = runtime(); source_runtime['port_runtime'] = genesis['config']['adapters'][0]['causal_config']['runtime']
    require(source_runtime['python'] == source_runtime['port_runtime']['python'], 'REFERENCE_HOST_CHANGED')
    original_launch = read(data/'full-p0-resume-1/launch.json')
    # Recorded immediately after SIGSTOP: elapsed 23:41, CPU 21:34.71.
    # Round UP and retain every persisted counter. Suspension/transport is idle.
    suspended_wall_upper, suspended_cpu_upper = 1422, 1296
    persisted_before = original_launch['before']['SPENT']['active_wall_us']
    spent = read(store/'SPENT')
    pins = deepcopy(resume['code_sha256'])
    pins.update({p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT/'research/qd019').glob('*.py')})
    for p in [ROOT/'requirements-qd019.lock', *(ROOT/'scripts/qd019').glob('*.sh')]:
        pins[p.relative_to(ROOT).as_posix()] = sha(p)
    cache_relative = str(Path(resume['cache_path']).relative_to('research/.data/qd015'))
    import sqlite3
    db = sqlite3.connect((data/cache_relative).resolve().as_uri()+'?mode=ro', uri=True)
    try:
        meta = {k: json.loads(v) for k, v in db.execute('SELECT k,v FROM metadata')}
    finally:
        db.close()
    manifest = dict(schema=SCHEMA, authorization_ref='QF-APPROVAL-QD019-TRANSFER-1',
        source_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        old_data_root=str(source.resolve()), source_runtime=source_runtime,
        frozen=dict(head=head, control=control, spent=spent, guard_request_sha256=guard['request_sha256']),
        inventory=source_inventory, code_sha256=pins, numeric_seals=[],
        source_unpersisted_active_us_upper_bound=max(0, persisted_before+suspended_wall_upper*1000000-spent['active_wall_us']),
        prior_observed_upper_bounds=dict(wall_seconds=prior_failure['wall_seconds']+suspended_wall_upper,
                                         cpu_seconds=prior_failure['cpu_seconds']+suspended_cpu_upper),
        pause_accounting=dict(recorded_elapsed='23:41', recorded_cpu='21:34.71',
                              source_wall_upper_seconds=suspended_wall_upper, source_cpu_upper_seconds=suspended_cpu_upper,
                              rounding='UP', suspended_transport_time_charged=False),
        original_input_observations={k: prior_failure[k] for k in ('physical_input_bytes','expanded_input_bytes','physical_rows_yielded')},
        source_rss_evidence=dict(prior_recorded_peak_bytes=prior_failure['peak_rss_bytes'],
                                 suspended_current_rss_kib=134384, continuation_peak_not_observed=True,
                                 continuation_peak_upper_bound_bytes=resume['outer_limits']['rss_bytes']),
        outer_limits=resume['outer_limits'], original_manifest_sha256=sha(ROOT/'research/qd015/manifest.json'),
        cache_relative_path=cache_relative, cache_identity=meta['identity'], cache_content_sha256=meta['content_sha256'],
        scope=old['execution_proposals']['full_p0']['scope'], training_authorized=False)
    draft = output/'reference-input.json'; put(draft, manifest)
    probe_data = output/'reference-copy/qd015'; probe_data.parent.mkdir()
    shutil.copytree(data, probe_data)
    reference = output/'reference-result.json'
    command = [sys.executable, '-B', '-m', 'research.qd019.probe', '--data', str(probe_data),
               '--manifest', str(draft), '--out', str(reference)]
    with (output/'reference.log').open('x') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    manifest['numeric_seals'] = read(reference)['numeric_seals']
    require(len(manifest['numeric_seals']) == 16, 'REFERENCE_SEALS_INCOMPLETE')
    put(payload/'migration.json', manifest)
    verify_inventory(source, source_inventory); verify_inventory(data, source_inventory)
    archive = output/'gate-qd-data.tar.gz'
    with tarfile.open(archive, 'x:gz', compresslevel=1) as tar:
        tar.add(output/'payload/research', arcname='research', recursive=True)
    put(output/'data-package-receipt.json', dict(status='FROZEN_LOCAL_HANDOFF', archive_sha256=sha(archive),
        archive_bytes=archive.stat().st_size, files=len(source_inventory),
        source_bytes=sum(r['bytes'] for r in source_inventory.values()),
        source_head=head, numeric_seals=len(manifest['numeric_seals']), original_unchanged=True))
    print(json.dumps(read(output/'data-package-receipt.json'), sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True)
    p.add_argument('--paused-pid',type=int,required=True); a = p.parse_args()
    build(a.output, a.paused_pid)
