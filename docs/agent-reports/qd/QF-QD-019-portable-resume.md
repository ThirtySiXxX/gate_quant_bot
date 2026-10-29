# QF-QD-019 — Portable local resume and Windows handoff

2026-10-29 Australia/Melbourne. User authorizes implementation, testing on
copies, packaging local research data/source/start instructions and pushing the
QD feature branch. No main merge or actual Mac replay continuation is requested.

Claim: new `research/qd019/*.py`, `tests/test_qd019_migration.py`,
`requirements-qd019.lock`, `scripts/qd019/*.sh`, this report and
`docs/WINDOWS_LOCAL_REPLAY.md`. Worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, base `274a3f0`. Existing financial, QR and shared-schema
files remain unchanged. Shared journals remain with the integration editor.

Implementation and actual validation results are recorded below. Original
PID 13604 stays suspended and original research evidence is retained. A migrated
copy has its own filesystem lease, operation record and one-shot invocation;
it resumes the same economic account, not a reset account or a new strategy.

## Completed implementation

Implementation commit `9f26560` adds a one-shot relocation runner, frozen data
builder, reference producer, small return-bundle collector, pinned dependencies
and WSL2 setup/start scripts. Final release binding is
`research/qd019/transfer.json`; it pins the exact transfer manifest and compressed
data archive. Source/manifest/runtime/data mismatch refuses admission.

The data bundle contains the complete approved QD015 research directory, including
the immutable market cache, derived source files, journals/control/audit history,
resource logs, original failures and the suspended account's SQLite rollback
journal. All 7,958 files (1,948,540,497 bytes) are copied and hashed while the
source process stays suspended. No real credentials, source app runtime files,
Mac venv, raw-history download or remote dataset upload is included.

The copied SQLite transaction is recovered by SQLite in the new directory.
Unvalidated guard 3082 is resolved as not committed only after verifying the
frozen pointers/input, full published journal chain, matching index/HEAD roots,
absence of the next journal/manifest and absence of a committed request row.
Ambiguous or stopped states fail closed. Old control records are retained; a new
resolution and migration operation record are appended. No prior financial tick
is replayed/rebuilt; a required index rebuild is explicitly refused for review.

Resource logs retain their original hash chains and write grants; absolute size
keys are mapped in memory to the new root. Original source-root bindings are
translated only during IO admission, then restored in memory. Original GENESIS,
cache producer identity and all 47 QD016 code pins remain unchanged. Store quota,
RSS and outer cumulative wall/CPU limits remain. Attempts increase 2 to 3, not 1.
The source continuation's recorded SIGSTOP elapsed 23:41 and CPU 21:34.71 are
rounded up to 1422/1296 seconds; the missing final SPENT interval is conservatively
added. Suspension/transport idle time is excluded explicitly. Earlier input
observations remain, and this invocation reads no original raw-history objects.

CPython 3.13.7 and exact NumPy/pandas versions are required. The changed host build
string is explicitly recorded, never forged into `sys.version` or old metadata.
A separate admitted port validates a shallow host-validation copy, while the
actual packet/causal configuration and original financial evaluate/state/output
methods remain unchanged. New operational code has its own pins and provenance.
Sixteen reference states produced by original ControlledPort on a copy are
checked by view/economic hashes *before publication* on the destination.

## Verification and results

- Five focused helper/return-bundle tests passed: OFF/no read, data corruption/
  deletion/addition, relocation/path escape/symlink rejection, exact numeric
  dependency/platform admission, and return-file allowlist/read-only cached view.
- Actual frozen-copy negative test passed in 57.608 seconds: an intentionally
  wrong numerical seal raises `MIGRATION_NUMERIC_DIVERGENCE`; HEAD stays1026,
  no1027manifest is published, status becomes INTEGRITY_STOPPED, and subsequent
  advance is refused. Recorded check wall57.009628/CPU53.484484s, peak141,590,528B.
- Actual independent-directory continuation passed: 16/16 seals, 1026→1042,
  last cutoff `2024-02-04T17:00:00Z`, economic hash
  `b4eadcc678fa8a1e17dac97956ea2efbbf40cf09c3c224f671201388ecd69d8e`.
  Invocation wall86.507561/CPU84.282435s, peak362,086,400B. Attempts3, cumulative
  write counter9,403,038,215B; these are copy-test results, not actual full replay.
- First relocation trial reached1041 with15matching seals, then found that the
  progress writer incorrectly used the ledger's no-float canonical codec for
  measured resource values. Corrected operational JSON encoding and reserved
  failure receipt fallback; reran the same frozen-copy validation successfully.
  Failed trial and logs remain, including102.05s wall/92.64s CPU/386,678,784B RSS.
- Bash syntax and Python syntax checks passed; no dependencies installed on the
  Mac. The required NumPy/pandas CPython3.13 Linux wheels were confirmed available
  from PyPI. Whole-account recovery does not require scikit-learn, GPU or CUDA.
- Consumed-invocation refusal passed with unchanged HEAD/CONTROL/SPENT. All47
  original code pins and original source HEAD/CONTROL/SPENT/GENESIS matched.
  Every one of the7958archived files was streamed out and checked against its
  recorded length/SHA256; the release manifest and archive hashes also matched.
- Actual copy-test return collection passed:381,988B archive, cached view present,
  result marked engineering validation, no database/.env payload. Remote branch
  identity is verified after the final authorized feature-branch push; the
  delivery summary reports the final commit and combined artifact path.

Commands (existing interpreter, PYTHONDONTWRITEBYTECODE and numeric threads=1):

```sh
PYTHONPATH=tests python -B -m unittest test_qd019_migration.MigrationChecks test_qd019_migration.LocalReturnBundle -v
QD019_FAULT_COPY=<disposable-qd015-copy> QD019_TRANSFER_MANIFEST=<frozen-manifest> PYTHONPATH=tests python -B -m unittest test_qd019_migration.FrozenAccountRejection -v
python -B -m research.qd019.entry --manifest <relocated-frozen-manifest> --validate-only
bash -n scripts/qd019/setup-wsl.sh scripts/qd019/run-local-replay.sh
```

Evidence is retained locally in
`/Users/lzh/Downloads/gate-qd-migration-check-20261029/` and
`/Users/lzh/Downloads/gate-qd-transfer-20261029/`. Compressed final data is
629,912,635 bytes, SHA256
`4e678a03c0ce24e863184ce2520446251de6c947b7d3fc4b321cf14b8710a394`.
Transfer manifest SHA256
`74503e758b758a7a53ac4f4798b6265858c8ae9d3ca6abc193be3046c28bb81c`.

## Files, limitations, counterpart dependency and next step

Files: claimed implementation/tests/scripts/lock/doc paths above, release JSON,
and a historical-status annotation in the QD018 report. Shared journals, QR files,
financial modules and main are untouched. Local runtime data is not Git content.

No physical Windows/WSL run was performed here; Windows performs mandatory
admission and initial numerical checks before proceeding. Fixed versions and an
initial exact-state seal do not prove bit-identical behavior for every future
transaction on every CPU. The existing cooperative RSS observation is retained;
there is no new hard OS memory guarantee. A faster CPU may still exhaust remaining
wall/CPU/storage limits. No completed2026replay, accepted training matrix, fitting,
profitability or live-execution claim follows from this copy test.

QR dependency: review this explicit host-build admission and numerical evidence
before shared/main integration or training approval; no field/schema/label/feature
order change is made or self-approved. User has explicitly authorized this feature
branch's push and local migration use, not main integration or model fitting.

Next: follow `docs/WINDOWS_LOCAL_REPLAY.md` on the new PC, keep the Mac process
suspended, run the one-shot continuation, and send the automatically generated
`return-to-codex-<UTC>.tar.gz` on either success or failure. It contains small
results/logs/checkpoint pointers/cached view and any final JSONL export; full
ledger/source data stays on the new machine unless specifically needed later.
