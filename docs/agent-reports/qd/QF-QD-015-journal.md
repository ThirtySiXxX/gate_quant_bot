# QF-QD-015 — bounded lossless journal compression

2026-10-29 Australia/Melbourne. **Journal candidate verified on synthetic input;
actual full P0 remains OFF. No training or actual historical payload reading.**

## Authority, ownership and preserved baseline

Dispatch `QF-DISPATCH-20261029-QD015-JOURNAL-1`; exact parent
`71448a8cf5a341813e1c266803834136b159618b`. Existing worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`. Initial tracked tree/index were clean, prior runtime
evidence untracked. QD014's seven checks, older benchmark and QD013actual pilot
are adopted without rerun. No new agent, timer or broader audit system.

Only existing file edited: `research/qd009/streaming_ledger.py`, in journal
read/write, explicit physical-format genesis binding and the shared atomic writer's
optional byte path. Financial reducers, QD014plan/algorithms, amounts, timestamps,
risk rules, old LIMITS and QR files are unchanged. Added under `research/qd015/`:
`journal.py`, `runner.py`, `entry.py`, `cache_identity.py`, `measure.py`,
`manifest.json`, `synthetic-input.json`; added `tests/test_qd015_journal.py` and
this report. No old test/report/evidence, public exporter/cache schema, source
checkout or shared journal was edited. Runtime artifacts remain untracked.

Result commit is the commit containing this report; resolve with
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-015-journal.md`.
Main remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; no merge/push.

## First measurement and deliberately small choice

One pure-storage pass over exactly16existing synthetic QD014journals:
`research/.data/qd014/engineering-1567562231992666/compact/store/journal-*.json`.
No ledger execution/import or raw market source read. Per-file byte hashes and
measurements are retained in `research/.data/qd015/storage-1/result.json`;
combined source identity
`6556b2b414cb4c2bc6104b19df7c8253735e315df67b95aa6194cda89af0f020`.

The reference prototype replaces only `generated` entries already exactly present
in the same journal's registry projection with their existing entry_sha256 refs;
it reconstructs and compares the full original bytes. It never relies on the
rebuildable SQLite index as authoritative missing evidence. This prototype was
measured only; **no reference/delta journal format was implemented**.

| Same16input files | Stored B | Encode s | Fsynced write s | Read + decode s |
| --- | ---: | ---: | ---: | ---: |
| Original byte copy |8568465|0.000004959|0.005357084|0.001069836|
| zlib level1 |1124976|0.021322210|0.002598085|0.004607085|
| zlib level6 |876018|0.051852081|0.001950291|0.003940291|
| Existing-entry refs + zlib1prototype |640162|0.033845791|0.002035873|0.059349291|

All alternatives reconstructed identical original bytes. Level1already removes
about86.9%of journal bytes at low codec CPU cost. Level6saves more bytes but needs
more compression time; the reference prototype adds reconstruction complexity and
much more decode/JSON work. Simple level1therefore meets this task's concrete disk
goal without adding durable reference dependencies or a generic audit framework.

These are one serial storage observation, not repeated statistical benchmarks.
Source read time0.011486917s; OS/filesystem caches and ordering are uncontrolled.
Writes fsync each file. Copying plain bytes is faster than compression plus writing
on this small input, and compressed reads are slower than plain reads. **No whole
replay speedup or memory reduction is inferred.** First table excludes framing.

New actual framing check, same original bytes:8568465→**1129056B**, an
**86.8231%journal reduction**. Encode0.023745957s, fsynced write0.002193416s,
read/decode0.007879667s. These include header/hash work, still a single observation.
Separate short registered accounts yielded8568465Bplain versus1128662Bcompressed
journals; audit parent hashes differ, while financial outputs are identical.

## Format, publication and recovery

Opt-in profile `qd015.journal-storage.v1` is explicitly inserted only into a new
GENESIS config via a thread-local `journal_creation(profile)` context. The runner
copies the create request instead of mutating its caller. No global default,
existing store or consumed resource counter is migrated. The profile binds exact
codec implementation SHA256, level1and64MiBraw/stored per-journal ceilings.

Files are `journal-NNNNNNNN.qjz`:8-byte versioned magic,4-byte big-endian header
length, canonical bounded JSON header and one zlib stream. Header cap1024B; header
records codec version, compressed/uncompressed lengths and independent SHA256s.
The commit manifest additionally binds physical file bytes/hash. Decoder rejects
wrong versions, noncanonical headers, NaN/constants, changed/truncated/trailing
streams, size contradictions and checksum mismatches. It checks stored file size
before reading and limits decompressor output to declared raw length+1, bounded
by the admitted64MiBprofile. It does not use unbounded decompress in production.

The physical profile is excluded from the *economic causal-policy* hash, like
resource limits, while GENESIS/config/checkpoint hashes still bind it. Thus a
storage choice changes audit addresses but not financial policy. Short paired
accounts additionally assert identical economic_state_sha256, not just cash.

Publication order remains: complete atomic journal write/fsync/readback, immutable
manifest, existing index/control barriers, atomic HEAD, audit/resource records.
`_atomic` retains exclusive immutable-file checks and durable directory barriers;
only an optional explicit bytes path is added. Rename failure leaves a pending
file and does not replace a valid journal. No financial record is discarded.

Without a journal_storage declaration, `.json` read/write remains the previous
path. This does not waive the existing pinned-code port-admission rule or promise
automatic advancement of an old differently pinned study under new source code.
QD015reopen rejects a store without its format binding. No silent migration.

`_payload` verifies physical bytes then returns the original decoded JSON payload.
All existing checkpoint/export/rebuild callers use it. Checkpoint exports keep
format3logical JSONL; they can be larger than compressed live storage. New tests
actually performed checkpoint, complete16commit index rebuild and restore, then
verified exact state/head/events. Deliberately corrupted final journal rejected
reopen with HEAD bytes unchanged. Its valid byte backup and corrupted fixture are
retained, never repaired/retried as an allegedly successful store.

## Focused new checks and observation budget

Initial five new methods all passed. A source review then tightened the producer
identity boundary to include portfolio math, interval constants and Python/NumPy/
pandas versions; only the affected identity/OFF method ran again and passed.
No old QD014check, old performance benchmark, S07, research or full suite ran.

| New method | Evidence |
| --- | --- |
|01 exact_codec_corruption_and_decompression_bound|Exact16journal byte reconstruction; version/implementation/hash/truncation/trailing/declared-output rejection; actual framed bytes and I/O times|
|02 atomic_bytes_do_not_replace_valid_immutable_evidence|Existing valid file preserved on inconsistent rewrite; synthetic rename failure leaves unpublished pending evidence|
|03 registered_financial_equality_and_close_reopen|Two8hour+2h synthetic registered accounts using the same64frozen native/open/funding/MARKprojections. Identical57financial events,10fills, economic hash, balances, lots/slices/obligations/entries/links/orders/decisions, mature/censored target/times/costs. Known prefix closed/reopened with exact state/head equality. Plain format remains plain|
|04 checkpoint_restore_and_persisted_corruption_rejection|Actual16commit checkpoint/index rebuild/restore;457logical export/control refs, exact states/head/events; final compressed-file corruption rejects without changing HEAD|
|05 off_gate_and_market_identity_excludes_journal|OFF reads no files; QD014approval rejected; changing journal identity leaves producer key unchanged; runtime/constants included|

`synthetic-input.json` is a45,779Bportable test fixture, SHA256
`270640538be2a91b09e77b66e6eb86b5fb29c0714f55521abe1dfc808c35bb27`.
It freezes only derived projections from the explicitly synthetic QD014cache;
no actual candles, fake historical trades or training samples. Earlier source
preparation conclusions are reused, not recalculated to retest research. Full
source warmup bars are intentionally absent from this *storage* fixture, and no
claim of fresh native-feature validation is made.

Actual commands, from the QD worktree (already executed, not instructions to rerun):

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd015.measure --source research/.data/qd014/engineering-1567562231992666/compact/store --output research/.data/qd015/storage-1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd015_journal -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd015_journal.JournalStorage.test_05_off_gate_and_market_identity_excludes_journal -v
```

| Retained log | Wall s | CPU(user+sys)s | Peak RSS B |
| --- | ---: | ---: | ---: |
|storage-1.log|0.35|0.29|35389440|
|initial-five-1.log,5/5PASS|13.89|12.69|154091520|
|identity-one-1.log,1/1PASS|0.76|0.48|124518400|
|final-metadata-1.log, source/profile metadata only|0.80|0.50|119111680|
|Total / peak|15.80|13.96|154091520(146.953125MiB)|

Budget120wall/90CPU s,512MiBpeak observation,128MiBnew retained evidence.
Final749files/41472431Bincluding all comparison copies, pending/corrupted fixtures,
valid backup, account/checkpoint evidence and resource summary. No evidence was
deleted to pass. `research/.data/qd015/resource-summary.json` binds all four logs,
45code pins and final manifest. Socket guards are not an OS sandbox; observation
and decompressor bounds do not constitute a whole-process hard memory guarantee.
No paired total-RSS improvement is claimed from these combined-worker peaks.

## Cache boundary and unchanged QR producer output

QD014's cache key included all ledger/driver code, so journal-only changes would
invalidate it. New `qd015.market-producer-code.v1` records18market-producing file
hashes, five unchanged canonical primitive function hashes, interval constants and
Python/NumPy/pandas identities. Whole journal/ledger storage and execution/driver
code are excluded. Financial/execution code still has independent exact pins in
the actual-run manifest. Existing cache envelope/schema, exact price/volume/time,
cell hashes and QR public output are unchanged; only the internal code-identity
scope is versioned explicitly.

No old cache is relabeled. A new-key hit is reused before raw reads. If an exact
old broad-key full-scope cache exists with no new-key hit, the entry stops before
raw access with `LEGACY_FULL_CACHE_PRESENT_EXPLICIT_COMPATIBLE_BINDING_REQUIRED_NO_RAW_REBUILD`.
The minimum remaining compatibility action would bind that exact accepted cache
identity after comparing the unchanged producer boundary, not reparse its history
or claim it was created by new code. No alias/migration approval is inferred.
Metadata check found the expected old full-cache path absent:
`research/.data/qd014/markets/4208c026561b40505ed518f78b6ecfefaa4f9b74c743949b5d07c0035bf4ecd9.sqlite3`.
No actual cache contents or raw payloads were read to establish that absence.

QR015episode/cache contract is unchanged, including exact cost/denominator,
provenance, mature/open/censored distinctions and filled-episode nested proposal.
No exporter or training feature order changed. QR016separately evaluates the
unfilled/rejected proposal gap; this task creates no proposal inventory, model
matrix, scaler, calibrator or fit. Compression does not select a sample universe.

## Lower proposed full-P0 allocation and limitations

New default-OFF entry `research.qd015.entry`, manifest SHA256
`a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2`.
It retains complete2023warmup, BTCETH shared10000USDT, one P0/ALLOW_ALL account
from2024-01-01through exclusive2026-10-01, settlement-only+2h.160accepted objects,
32856hour cap/coin and frozen permits remain. No yearly resets, truncation,
window/profit selection, omitted UNKNOWN or forced closing. Other eight registered
trajectories remain for later fixed execution; none is launched or dropped here.

Proposed command, **not executed or authorized by this implementation**:

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd015.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD015-FULL-P0-1 --manifest-sha256 a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2 --scope full_p0
```

Fresh fixed destination `research/.data/qd015/full-p0-actual-1/` is absent. Exact
named authority/manifest/source/codec gates, exclusive receipt and no automatic
retry/resume remain. Coordinator allocates any actual invocation after reading
this result; this development task does not start it.

Proposed once-run disk ceiling is **12GiBtotal /10GiBledger**, down from the
unapproved QD01432/30GiBproposal. This is a lower stopping allocation, not measured
full-period demand. First storage measurement alone leaves all other known short
account files unchanged:12182373−8568465+1129056=4742964B, a **61.067%physical
account projection**, not an observed whole-store reduction. Constant-per-tick
scaling of that illustration to30122/16is about8.316GiB, before increased trade
history and preparation overhead. It motivates the smaller10/12GiBceiling but
does not prove adequacy. Functional account journal sizes independently confirm
the physical saving; the post-checkpoint store is not compared against a store
without checkpoint exports to manufacture a total-disk percentage.

Time/RSS improvement has not been measured for full execution; keep proposed
outer wall4h/CPU3h/RSS1GiB as ceilings only, not needed/approved amounts. Source
physical1GiB, expanded2356028624B/53820701rows remain metadata-backed bounds,
not new observed source work. New store profile retains QD0148MiBadapter state,
16MiBpage and4hwall proposal while reducing its store cap to10GiB; other original
read/event/input/request/exact/cache bounds remain. Old LIMITS/experiments/counters
are untouched. New64MiBper-journal raw/stored ceilings may stop even earlier.

**Remaining bottleneck is explicit:** compression changes constants, not O(N²)
worst-case accumulation. Completed episode/fill state, registry reads and frames
can repeatedly serialize growing histories; JSON creation, exact arithmetic,
full checkpoint expansion and index persistence remain. Compression still builds
the original payload and raw bytes in memory and adds an encoded buffer. It
does not reduce model/ledger computation or guarantee lower RSS. Frame/decoded
journal size, output quotas, runtime or state/page bounds may stop a full run.
Keep the first precise stopping cause and committed head; do not delete settled
trades, loosen guards or create a replacement reset account to get a PASS.

This concrete disk bottleneck is addressed without extending scope indefinitely.
The next step is a separately allocated full P0attempt or an explicit targeted
response to an actual stopping cause, not another generic review/benchmark loop.
No full-history success, profitability or training readiness is asserted. Fitting
still requires user confirmation. No main integration/push, engine/app, real-money
credentials/orders, NAS/Windows, network/download, cloud, timer or new agent.
Candidate and report are committed; all evidence is retained; stop here.
