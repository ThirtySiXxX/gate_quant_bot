#!/usr/bin/env bash
# Run inside Ubuntu/WSL2 after installing the WSL feature and extracting code.
set -euo pipefail
task_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$task_root"
if [[ $(uname -s) != Linux || "$task_root" == /mnt/* ]]; then
  echo 'Use Ubuntu/WSL2, with the project under ~/projects (Linux disk).'; exit 1
fi
if [[ $# -ne 1 ]]; then
  echo 'Usage: bash scripts/qd019/setup-wsl.sh /mnt/c/quant-transfer/gate-qd-data.tar.gz'; exit 1
fi
task_archive=$(realpath "$1")
test -f "$task_archive"
test ! -e research/.data/qd019-import
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
task_uv="$HOME/.local/bin/uv"
if [[ ! -x "$task_uv" ]]; then
  task_installer=$(mktemp)
  curl --fail --location --proto '=https' --tlsv1.2 https://astral.sh/uv/0.13.6/install.sh --output "$task_installer"
  sh "$task_installer"
fi
"$task_uv" python install 3.13.7
test ! -e .venv
"$task_uv" venv --python 3.13.7 .venv
"$task_uv" pip sync --python .venv/bin/python --only-binary=:all: requirements-qd019.lock
"$task_uv" pip install --python .venv/bin/python --no-deps --require-hashes -r requirements-qd020.lock
# Verify the archive against the source-controlled release binding before use.
.venv/bin/python -B - "$task_archive" <<'PY'
from research.qd019.migration import read,sha,require
import sys
r=read('research/qd019/transfer.json')
require(sha(sys.argv[1])==r['data_archive_sha256'],'DATA_ARCHIVE_HASH_MISMATCH')
PY
# Extract only regular files/directories under the declared handoff prefix.
.venv/bin/python -B - "$task_archive" <<'PY'
import pathlib,sys,tarfile
with tarfile.open(sys.argv[1], 'r:gz') as t:
    for m in t.getmembers():
        p=pathlib.PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts or p.parts[:4] != ('research','.data','qd019-import','qd015') and p.as_posix() not in ('research','research/.data','research/.data/qd019-import','research/.data/qd019-import/migration.json'):
            raise SystemExit('UNSAFE_TRANSFER_ARCHIVE')
        if not (m.isdir() or m.isfile()):
            raise SystemExit('UNSAFE_TRANSFER_ARCHIVE_MEMBER')
    t.extractall('.', filter='data')
PY
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
.venv/bin/python -B -m research.qd019.entry --check
echo 'Environment and data check passed. Start with: bash scripts/qd019/run-local-replay.sh'
