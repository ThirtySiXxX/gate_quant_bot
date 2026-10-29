#!/usr/bin/env bash
set -uo pipefail
task_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$task_root" || exit 1
test -x .venv/bin/python || { echo 'Run setup-wsl.sh first.'; exit 1; }
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
mkdir -p local-logs
task_log="local-logs/qd019-$(date -u +%Y%m%dT%H%M%SZ).log"
.venv/bin/python -B -m research.qd019.entry --resume 2>&1 | tee "$task_log"
task_result=${PIPESTATUS[0]}
.venv/bin/python -B -m research.qd019.collect --log "$task_log"
echo "Replay exit status: $task_result. Send the generated return-to-codex archive."
exit "$task_result"
