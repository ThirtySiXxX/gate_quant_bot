"""Run with the existing project .venv; install only reviewed new QD021 paths."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root=Path.cwd().resolve();package=Path(__file__).resolve().parent
    payload=package/'payload';release=json.loads((payload/'research/qd021/release.json').read_bytes())
    if not (root/'research/qd019/transfer.json').is_file():raise ValueError('RUN_FROM_EXISTING_GATE_QUANT_BOT_DIRECTORY')
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    # Validate every old pinned module BEFORE installing anything. Never repair
    # unknown edits by overwriting them with our package.
    for name,h in release['base_code_sha256'].items():
        if digest(root/name)!=h:raise ValueError('EXISTING_CODE_CHANGED:'+name)
    names=release['new_files']+['research/qd021/release.json']
    for name in names:
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('UNSAFE_PACKAGE_PATH')
        source=payload/p;dest=root/p
        if name in release['code_sha256'] and digest(source)!=release['code_sha256'][name]:raise ValueError('PACKAGE_HASH_MISMATCH:'+name)
        if any(d.is_symlink() for d in [dest,*dest.parents]):raise ValueError('SYMLINK_DESTINATION')
        if dest.exists() and digest(dest)!=digest(source):raise ValueError('EXISTING_NEW_FILE_DIFFERS:'+name)
    for name in names:
        dest=root/name
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write((payload/name).read_bytes())
    print('Reviewed update installed. Preparing a separate copy at the CURRENT checkpoint...',flush=True)
    result=subprocess.run([sys.executable,'-B','-m','research.qd021.handoff'],cwd=root)
    return result.returncode


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as e:print('UPDATE_STOPPED: '+type(e).__name__+':'+str(e));raise SystemExit(1)
