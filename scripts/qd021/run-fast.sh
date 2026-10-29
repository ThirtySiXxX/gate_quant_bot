#!/usr/bin/env bash
set -uo pipefail
task_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$task_root" || exit 1
test -x .venv/bin/python || { echo 'Existing WSL .venv is required.'; exit 1; }
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p local-logs
task_log="local-logs/qd021-$(date -u +%Y%m%dT%H%M%S%N).log"
task_manifest=$(.venv/bin/python -B -c "import json; m=json.load(open('research/.data/qd021-handoff/current.json')); print('research/.data/qd021-handoff/'+m['operation_id']+'.json')") || exit 1
# The Python runner installs its own handlers and pauses after a committed tick.
# Keep tee/the wrapper alive until that clean result and return bundle exist.
trap '' INT TERM
.venv/bin/python -B -m research.qd021.entry --manifest "$task_manifest" --resume 2>&1 | tee "$task_log"
task_result=${PIPESTATUS[0]}
.venv/bin/python -B -m research.qd021.collect --log "$task_log"
echo "Replay exit status: $task_result. Send the return-to-codex-qd021 archive."
exit "$task_result"
