# QF-QR-CACHE-REVIEW: independent cache review

Task-ID: QF-QR-CACHE-REVIEW
Dispatch-ID: QF-DISPATCH-20261027-QR-CACHE-REVIEW-1
State: PASS
Date: 2026-10-27 (Australia/Melbourne)
Reviewer: QR
Review base SHA: `3d0b6e1783ae18b43baadf29cc1ab76286f66d6a`
Implementation SHA: `481f87ff1601ee4b3f788f8efee923157355c0e6`
QR report branch: `codex/qr-validation-baseline`
QR report parent: `e76215f5829065f008fa0af4533aad4da3d1d949`
QR worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`

PASS means this exact candidate may await user integration review. It is not
permission to merge, deploy or start trading. No actionable defect requiring a
revision was found within the stated cooperative local-filesystem/spawn scope.

## Review inputs and isolation

Reviewed only the implementation commit's delta against its actual parent:
`src/data_fetcher.py`, `tests/test_qd_cache.py` and
`docs/agent-reports/qd/QD-001-cache.md`. The separate acknowledgement at `f0f9eb0`
was read for scope/status, not treated as new functionality. Earlier lifecycle
changes inherited from the parent are not attributed to this cache patch.

Read AGENTS and the applicable architecture/collaboration/interface documents,
the complete added cache tests and QD's declared limitations before execution.
Existing runtime interfaces, signals, units, costs and risk settings were checked
against the exact diff; no shared-contract changes occur in it.

Testing did not run from QD's mutable worktree. An allowlisted snapshot of 59
tracked files (`src/`, `tests/`, static assets beneath src, and config.example.yaml)
was read from the implementation Git object into an isolated temporary directory.
The parent data_fetcher module was read from its Git object for comparisons.
No main.py, real config, credentials, account data or existing cache was copied.
Every snapshotted file's SHA256 still matched after all tests.

Snapshot/evidence root, retained locally:
`/var/folders/1q/m4j26zmj1q75w5_9dqrlm7mm0000gn/T/qf-qr-cache-review-rtp4r6ch`

The guarded `review_runner.py` resides outside that source snapshot. It blocks
socket.create_connection/socket.connect/socket.connect_ex at import time, also
covering spawned children. All exchange responses are synthetic. Filesystem
experiments use fresh TemporaryDirectory instances; there is no engine startup,
service operation, dependency installation or real-cache access.

## Tests actually executed

On macOS 26.6.2, arm64, CPython 3.13.7, using the existing interpreter read-only:

```sh
cd /var/folders/1q/m4j26zmj1q75w5_9dqrlm7mm0000gn/T/qf-qr-cache-review-rtp4r6ch
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python review_runner.py existing > existing-tests.log 2>&1
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python review_runner.py independent > independent-tests.log 2>&1
cd snapshot
node tests/web_regressions.cjs
```

- Existing exact-commit Python suite: **178 passed, no skips**, 8.191 seconds.
  This includes the 16 QD cache tests, not merely the report's claimed result.
- Independent QR suite: **7 passed**, 3.795 seconds, with the subcases below.
- Frontend regressions: **8 groups passed**. These are compatibility checks;
  frontend code is not changed by the cache patch.
- Snapshot byte verification and changed-path/diff whitespace checks passed.

Expected warning output includes injected lock denial and the existing ownership
fixture's simulated disk failure. Neither is an unhandled runtime test failure.

## Independent assertions and negative controls

| Check | Independent observation |
|---|---|
| Exact code and algorithm preservation | Verified all 59 snapshot hashes. AST comparison matched both original public signatures/docstrings and their moved download/merge/filter bodies; every other original function except the intentionally changed saver was identical. |
| Atomic publication failure, both data types | Injected a writer that outputs a partial CSV and raises. The parent implementation corrupts the previous bytes, establishing a negative control. The candidate preserves the old byte-for-byte snapshot for both candles and funding. Separate fsync and replace failures also preserve the old CSV and remove the temporary file. |
| Lock failure and cache-disabled paths | Seeded opaque pre-existing bytes and made cache read/write helpers raise if called. Both public fetch types return synthetic data after an OS lock error without touching those bytes. With use_cache=False, no lock function is called and no sidecar is created. |
| Values, columns, units, filtering and refresh | Compared parent and candidate directly for candles and signed fractional funding, unsorted duplicate timestamps, full/recent windows and disabled/first/repeated cache use: all 12 paired result comparisons and final CSV bytes match. |
| Failure propagation and lock cleanup | A progress callback raises a specific OSError after one candle page. The same exception propagates with one page call; no uncached retry occurs. A different thread can subsequently complete the same-key fetch. |
| Process transaction scope and key independence | For each of candles/funding, three spawned processes run real public fetch wrappers. The first ETH transaction pauses after reading. A second ETH transaction cannot reach cache read; a BTC transaction completes while ETH is still held. After release the final ETH CSV retains all five historical timestamps and replaces only the two fresh overlapping values. |
| Abrupt exit after fsync, before replace | For both candles/funding, a spawned public fetch is paused at os.replace after writing/flushing/fsyncing the temporary. The original CSV remains readable and byte-identical. Termination leaves it intact; a new spawned fetch acquires the persistent sidecar and updates successfully. The orphan temporary is not treated as data. |

The independent runner does not invoke QD's test helper functions. The 178-test
suite separately exercises same-key threads, directory aliases/reentry, different
contract/interval/funding keys, failed first publication, permissions and mid-write
crashes. Combining these checks supplies evidence beyond repeating QD's summary.

## Findings

- **CACHE-R01 — Atomic old/new snapshots: PASS.** Same-directory temporary output
  is closed before os.replace; readers retain the old snapshot until publication.
  Normal serialization/fsync/replace failures cannot truncate the previous CSV.
  The parent negative control demonstrates that this is a material improvement.
- **CACHE-R02 — Cooperative transaction exclusion: PASS within tested scope.**
  Canonical path plus per-key thread lock and permanent OS-lock sidecar surround
  read, download, merge and publish. Keeping the sidecar avoids replacing the
  locked inode together with the CSV. Threads/spawned processes of different
  keys remain independent. Lock acquisition failure disables caching for that
  request instead of performing an unlocked read/merge/write.
- **CACHE-R03 — Recovery and semantics: PASS.** Process termination releases the
  lock for a subsequent spawned writer while the old CSV stays readable. Public
  signatures and underlying paging/gap/merge/filter algorithms match the parent.
  No fee, funding sign, timestamp, volume conversion, signal or risk-rule change
  was introduced by this delta.

These are review conclusions, not new fixes. No REVISE item is raised and no QD
code/test edit was made by QR.

## Platform and operational limitations

1. Only macOS local temporary storage and spawned processes were exercised.
   Windows msvcrt, Linux/TrueNAS, actual NAS service identities, NFS/SMB, and
   multi-user permissions remain untested; no portability/deployment pass is given.
2. Forking while a thread holds locks is explicitly unsupported by the QD report
   and was not tested. This PASS does not broaden that process-model guarantee.
3. Locks are cooperative. Older writers, external editors, sidecar deletion or
   non-cooperating programs are outside the protocol. The private saver is an
   atomic publisher; callers that read/merge must still hold the transaction lock.
4. Same-key lock waiting has no timeout/cancellation policy; a stalled fetch can
   delay later requests. No throughput improvement or bounded latency is claimed.
5. Abrupt exit may leave ignored temporary files. No scavenging or parent-directory
   fsync/full power-loss durability guarantee exists. Killing a process in these
   tests is not a simulated machine power failure.
6. Existing malformed-cache policy, data provenance/semantic quality and historical
   dataset gaps are not repaired by this patch or certified by these tests.

These limitations are already disclosed in the implementation report and are
not silently upgraded by the successful local tests. Before any future NAS use,
target filesystem/platform behavior needs its own authorized validation.

## Evidence fingerprints

| Local evidence | SHA256 |
|---|---|
| snapshot/src/data_fetcher.py | 624339d97918bc7ab99357e0d0513a9d7f356805ee5f6bd01fd7f03a987a2fdf |
| parent-data_fetcher.py | 0cba049063d1df0e0aa32da06516bb60f16b3b52c2125662ac088b0f8ed5c5fe |
| snapshot-manifest.json | 5c2c48c7bf642ffc100c38fbc90ed852c69fddcee5544637db92bbf9b77f720e |
| review_runner.py | 405e69887899eae34b7fea9bc845fda6ddd3bbd1fa491c0a824d2e50ca6ca156 |
| existing-tests.log | c7ef2cac7422dfb3d7106334bd107934ad5ed8f604b0ed4fac86a271508843d0 |
| independent-tests.log | bdec3e9c8b50c3957ea5e35881953e356b623063796783fddf567dbcedd565ad |

Temporary evidence is retained for local inspection but is not a permanent Git
artifact. The exact source commits and this committed report remain the durable
record; no evidence directory or additional source file is added to the QR branch.

## Completed scope and pause

Only `docs/agent-reports/qr/QF-QR-cache-review.md` is committed by this review.
All earlier QR results/specification files remain unchanged. Original main,
QD's worktree and shared/coordinator journals were not modified. No cherry-pick,
merge, push, model activation, real credentials, engine or NAS operation occurred.

Control QF-CONTROL-20261027-PAUSE-AFTER-REVIEW-QR-1 supersedes the earlier automatic
next-task queue. After committing this report QR stops and reports the result.
No model-validator implementation/review, further research or automatic repair is
started. The coordinator will present this PASS and handle scheduler pausing;
user integration approval remains pending.
