# QF-QD-021 — Replay performance and unrestricted local execution

2026-10-29 Australia/Melbourne. User authorizes code/algorithm optimization and a
new Windows export; i7-12700KF/RTX4060. User explicitly removes artificial global
wall/CPU/RSS/disk resource quotas. Preserve economic rules, data availability,
exact accounting and integrity validation; actual errors still stop with evidence.

QD branch `codex/qd-replay-performance`, worktree
`/Users/lzh/.codex/worktrees/qd-replay-performance/gate_quant_bot`, base dfc5798.
Base tracked tree/index clean; old untracked research evidence stays in the
separate qd-cache-safety checkout. No original policy/financial modules or QR
files are claimed. Claim: new `research/qd021/*`, `scripts/qd021/*`,
`tests/test_qd021*`, this report and `docs/WINDOWS_FAST_REPLAY.md`.

First measure a short frozen account-copy segment, then optimize measured work
and compare identical per-tick public/economic states. Preserve current Windows
progress through a controlled stopped-source snapshot and explicit cold recovery;
do not clear its authorization records, reset capital or silently restart history.
Current running Windows/Mac source files/processes are not modified by development.
No main merge, model fit, live exchange action or dataset upload is authorized.

## Completed changes

- `research/qd021/fast.py`: graph-copy fast paths preserving aliases/cycles and
  fallback semantics; equivalent strict canonical-JSON checks; reuse encoded
  values for node hashes; weighted immutable LRU retained across commits; indexed
  transaction-local pruning including timeline/link/audit-reference closure.
  Existing phase barriers, content hashes, exact arithmetic and fsync remain.
- `accounting.py`: verify/relocate existing resource chains and retain conservative
  durable write debits, while removing artificial aggregate storage/write quotas.
  Reuse append descriptors and avoid repeated filesystem path walks per VFS write.
- `cold.py`, `handoff.py`: freeze only the uniquely identified current replay,
  verify PID start identity, preserve source, hash-check and sync an independent
  copy at its current HEAD. Recover copied hot SQLite state; rewind only derived
  unpublished rows, preserve/quarantine unpublished journal artifacts, adopt
  verified control/audit tails and resolve committed/uncommitted guards with proof.
  Integrity and ambiguous structural failures are never waived. Repeated handoffs
  identify immutable per-operation manifests, ignoring older paused generations.
- `entry.py`: explicit opt-in, one-shot continuation; remove total wall/CPU/RSS/
  storage and adapter-time quotas; retain finite format/precision/decoder checks,
  runtime/source identity admission, old numerical seals and error evidence.
  SIGINT/SIGTERM requests pause after completing the current commit.
- `collect.py`, `scripts/qd021/*`, `docs/WINDOWS_FAST_REPLAY.md`: standalone small
  update installer, existing WSL environment reuse, safe startup and local return
  bundle. Export existing episode schema and provenance; no training or upload.
- `release.json`: pin the admitted old code and new update files. No old QD019,
  ledger, port, financial, risk, strategy, ML or QR source file was edited.
- `profile.py` and three `tests/test_qd021*.py` files supply measurements and checks.
  This role-specific report records progress/decisions; shared journals remain
  untouched under the existing concurrent-document editing boundary.

## Tests and results

Evidence stays locally under `/Users/lzh/Downloads/qd021-performance/`.
Only approved public-data research copies and synthetic fixtures were used.

1. Same segment, 16 ticks, **without cProfile**: baseline 24.7356696 wall / 22.416796
   CPU seconds, optimized 7.9002201 wall / 6.248303 CPU seconds: **3.131x wall**.
   New writes 168,962,216 vs 174,593,355 bytes (issued IO, not disk occupancy).
   Startup/admission is excluded from both loop timings. Preliminary 8-tick
   profiling located the hot paths; its speed ratios are not production estimates.
2. **29 distinct ticks, sequences 1027–1055**: per-tick full HEAD, complete view
   hash and economic-state hash match the original implementation exactly.
   Includes current-HEAD cold handoff 1050→1054, then a real SIGINT pause at1055.
   Cold preflight is still substantial (roughly 100 seconds in these copies);
   history verification is performed once, not silently skipped for speed.
3. Final new focused suite: **16 tests passed**. Copy alias/cycle/custom semantics,
   canonical bytes/errors, randomized treap roots/history, cross-component pruning,
   corrupt blobs/missing roots, real VFS writes beyond the old quota with retained
   durable debits, pre/post-HEAD publication interruption, orphan audit tail,
   integrity-stop rejection, default OFF, PID ambiguity/reuse and return allowlist.
4. Isolated separately compiled pysqlite3 DBAPI: real VFS probe passes and all
   **16 checks pass**. This is an alternative-backend Mac test; it does not claim
   that this update's entire Windows replay has already completed. The pinned
   Linux wheel/backend was previously verified on the user's Windows/WSL host.
5. Full network-blocked offline suite: **374 tests, OK, 1 explicitly gated fault-
   copy test skipped**. Initial stdin-launched full suite had four cache-process
   subcase failures because macOS spawn could not import `<stdin>`; preserved the
   log, used a real guarded runner file, then reran the complete suite successfully.
   Later focused checks cover the final quota-error whitelist and handoff edits.
6. Real process signal: SIGINT after a new published HEAD finishes cleanly with
   `PAUSED_AT_COMMIT_BOUNDARY`, one new tick, exact baseline state. A synthetic
   process-group SIGINT check also proves wrapper/tee survive to collect the result.
7. `node tests/web_regressions.cjs`: all checks pass. `bash -n` for the new wrapper
   and Git whitespace checks pass. Original main remains cae0d23; old paused Mac
   PID13604 remains stopped. No original data, source staging boundary or process
   was resumed/reset by development.

Useful reproduction commands (use a disposable account copy for profile/cold work):

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest discover -s tests -p 'test_qd021*.py' -v
node tests/web_regressions.cjs
bash -n scripts/qd021/run-fast.sh
git diff --check
```

The full offline runner follows AGENT_COLLABORATION socket blocking, using a saved
Python file with an `if __name__ == '__main__'` guard for macOS multiprocessing.
Benchmark CLI: `python -B -m research.qd021.profile --data COPY --manifest MANIFEST
--output NEW_OUTPUT --ticks 16 --continue-copy --no-profiler [--optimized]`.

## Decisions, limitations and next steps

- Preserve the original sequential shared BTC/ETH account and financial algorithms.
  Parallel independent accounts or different fill/risk rules would change the task.
  The measured JSON/ledger workload uses CPU/SQLite; no GPU or model fit is added.
- The user authorizes unrestricted resource use. Cache capacity targets are not
  job quotas; actual disk exhaustion, OS memory pressure or integrity errors can
  still stop the process. Prior durable counters are retained; copied source
  process/progress observations are reported separately rather than inventing
  complete historical CPU/wall observations.
- Retain old source and every checkpoint copy; an interrupted update never sends
  SIGCONT. Do not run the old source concurrently with its continuation. Multiple
  or unidentifiable writers and genuine nonquota failures require review.
- This is short-segment equivalence and engineering recovery evidence, **not** a
  completed multi-year replay or a guaranteed 3.13x Windows speedup. The optimized
  long run remains the user's Windows task. Do not automatically retry errors.
- No shared financial contract was changed. No immediate QR implementation is
  needed; after completion QR must assess mature cost-adjusted labels, sample
  sufficiency and temporal isolation before any separate training authorization.
- Deliver the small update ZIP; reuse current Windows data/environment and send
  the generated local return archive when finished. Commit/push only the QD
  feature branch under the user's existing push authorization; never merge main.
