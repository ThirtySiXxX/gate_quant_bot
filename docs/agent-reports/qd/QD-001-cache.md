# QD-001: atomic cache publication and concurrent updates

Date: 2026-10-27 (Australia/Melbourne). Status: implemented and verified locally;
pending review/integration. This report records progress and engineering decisions
without resuming the paused edits to shared PROGRESS/DECISIONS journals.

## Claim, baseline and files

- User allocation: fix cache atomicity/concurrency, test and commit in an
  independent worktree, preserve trading rules, do not merge into main.
- Role/branch: QD, `codex/qd-cache-safety`.
- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Parent: `3d0b6e1783ae18b43baadf29cc1ab76286f66d6a`
  (`codex/qd-lifecycle-safety`, previous QD milestone).
- This branch inherits local source snapshot `475aaeaa5b9365b360563294e183d912c382b570`.
  That snapshot contains earlier user work and is not an approved main/shared
  baseline. Review this milestone's delta against `3d0b6e1`, not against main.
- Exact exclusive write scope: `src/data_fetcher.py`, `tests/test_qd_cache.py`,
  `docs/agent-reports/qd/QD-001-cache.md`. No QR-owned or shared-schema files edited.
- Resulting commit: the commit containing this report; resolve with
  `git log -1 --format='%H %s' -- docs/agent-reports/qd/QD-001-cache.md`.

## Findings and completed changes

The old `_save_cache` truncated the destination CSV before serialization finished.
A chart reader could see a partial file; serialization failure destroyed the last
good snapshot. Concurrent downloads could both read the same earlier cache and
later overwrite each other's expanded history or refreshed rows. Candles and
funding history shared this implementation.

1. Serialize each complete public fetch transaction (read, download, merge, write)
   by canonical cache path. A per-key reentrant thread lock and OS file lock on a
   permanent `.csv.lock` sidecar coordinate cooperating threads and processes.
   Different contracts, intervals and funding keys retain parallelism. Unused
   in-process lock states are reclaimed through weak references.
2. Write CSV to a unique temporary file in the destination directory, flush/fsync,
   close it, then publish with `os.replace`. Readers remain lock-free and see an
   old or new complete snapshot. Existing file permission bits are retained;
   new caches use the temporary file's private mode (0600 on POSIX).
3. Ordinary serialization/fsync/replace failures retain the previous CSV and
   remove the temporary file. Existing nonfatal cache-save behavior is retained:
   the caller can still use the downloaded DataFrame.
4. If directory creation or lock acquisition fails with an OS error, log a
   warning and run that request with caching disabled. Never perform an unlocked
   read/modify/write as a fallback. Fetch errors propagate according to existing
   behavior; the new acquisition handler does not retry or swallow them.
5. Cache-disabled calls do not create cache directories or sidecars. OS locks
   release when the holder exits; a sidecar's presence does not mean it is locked.

Public method signatures, filenames, CSV columns, timestamp/volume/funding units,
native contract versions and result filtering remain unchanged. Existing paging,
gap repair, history limits, sorting/deduplication and fresh-row merge logic remain
unchanged. No strategy, signal, model, sizing, risk, order or trading-mode changes.

## Verification

The initial three regressions were run against the old implementation and all
failed: partial-file visibility, old-file corruption after serialization failure,
and a same-key fetch reading before its predecessor published. They pass after
the fix.

Final results on macOS, Python 3.13 (existing interpreter reused read-only):

- **16 focused cache tests passed** (3.736 seconds). Real controlled threads and
  spawned processes use synthetic temporary-directory data. Coverage includes
  candles/funding overlapping requests, expanded history and refreshed values,
  distinct-key concurrency, directory aliases/reentry, failure cleanup and
  fallback, disabled cache, value/column/filter parity, and existing permissions.
- Crash tests cover both termination of a lock holder and process exit midway
  through CSV serialization. The old CSV survives, the OS lock releases, and a
  subsequent writer succeeds without treating an orphan temporary as cache data.
- **178 Python tests passed** with Python socket connections blocked (7.692
  seconds): the prior 162 tests plus 16 cache tests. The expected ownership-store
  fixture error log is from an existing injected-failure test.
- **8 frontend regression groups passed**.
- AST comparison against `3d0b6e1` confirms both public fetch signatures and the
  original download/merge/filter function bodies are unchanged; those bodies
  now execute inside transaction wrappers.
- Working/staged delta whitespace checks passed. The original source checkout's
  HEAD remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; its index-entry SHA-256
  remains `77931f7f4b2fc2bf8f354bb924b8f799d3d2ec76968d6141e754fabfdb6eedba`.

Reproduction commands, from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p test_qd_cache.py -v
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -c '
import socket, unittest
offline = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("offline test: network blocked"))
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.discover("tests"))
raise SystemExit(not result.wasSuccessful())
'
node tests/web_regressions.cjs
git diff --check
git diff --cached --check
```

Use `-c` or a guarded real runner file for the full suite, rather than a stdin
script: spawned-process tests must be able to initialize their main module.
All exchange methods in these tests are mocked; no app/engine, real credential,
account data, real cache, NAS service or live order is involved. No dependencies
were installed or updated.

## Decisions, limits and remaining backlog

- **Transaction boundary:** locking only the final write cannot prevent a stale
  read/merge from overwriting another writer. Hold the same-key lock throughout
  download and merge. A slow fetch therefore delays another fetch of that key;
  readers and other keys remain independent. No throughput speedup is claimed.
- **Permanent sidecar:** never unlink `.lock` files while writers/waiters might
  exist, because that can split them across lock inodes. Do not use file existence
  as a stale-lock test. The application does not currently impose a lock timeout
  or cancel a waiting download; such lifecycle changes need a separate task.
- **Cooperative local storage:** all writers must use these wrappers and the same
  physical path. The private `_save_cache` publishes an already assembled snapshot;
  callers doing read/merge must hold the transaction lock. Older app versions,
  manual CSV edits and unrelated programs do not honor this advisory protocol.
- **Platform boundary:** POSIX `flock` was exercised on macOS. Windows uses
  `msvcrt` byte-range locking but has not been executed on Windows; Linux/TrueNAS,
  network-mounted NFS/SMB and multi-user cache permissions need target validation.
  Tests use spawned processes; forking while a thread holds locks is not supported.
- **Crash boundary:** normal failures clean temporary files. Abrupt process exit
  may leave `.tmp` files; readers ignore them. No automatic scavenger is included
  because deleting another writer's temporary file would be unsafe. File fsync is
  used, but parent-directory fsync/full power-loss durability is not claimed.
- **Existing data semantics:** this is not a cache schema/corruption/provenance
  migration. Existing malformed caches and semantic validation remain separate
  work; no historical datasets were repaired or experiments rerun.
- Job-admission and worker-lifecycle fixes remain in parent `3d0b6e1`; paper-account
  restart policy and uncertain-order reconciliation remain open engineering tasks.

## QR dependency and recommended next steps

No QR mathematical or shared-interface change is required for this patch. QR can
continue independent research. Counterpart/integrator review should check the
unchanged data contract and the operational lock-wait tradeoff before integration.
After approval, QD can consolidate this report into shared journals in a dedicated
integration worktree and run combined regression tests. Main was not merged or
modified by this milestone; no push/deployment was performed.

Next engineering priority: reproduce uncertain order timeout/restart behavior with
synthetic exchange responses before changing retry/idempotency policy. Before
eventual NAS deployment, validate the cache protocol on the actual target local
filesystem and service identity. Neither action is part of this completed patch.
