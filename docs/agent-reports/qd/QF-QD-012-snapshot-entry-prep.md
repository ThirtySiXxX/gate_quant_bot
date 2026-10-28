# QF-QD-012 — one-shot snapshot entry, static preparation

2026-10-29 Australia/Melbourne. **STATIC_ONLY / NOT_EXECUTED.** This task prepares
a concrete invocation for human review. It grants no actual-input execution.
No tests, CLI/help/default probe, new-module imports, actual payload reads,
native computation, query evaluation, account creation/advance, labels or fit ran.

## Authority, baseline, files and correction

Dispatch `QF-DISPATCH-20261028-QD012-SNAPSHOT-ENTRY-PREP-1`, read completely from
the persisted coordinator record `qd012-snapshot-entry-prep.txt`. Existing worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, initially clean at exact base
`48a09a6b1f162f3ae39ad971bd006f9a8f6145b7`. No new worktree or agent.

Exactly four edited/new files:

- `research/qd012/prepare.py`: authoritative trajectory register and metadata
  factory correction, explicit optional entry plan, code identity path list.
- `research/qd012/preparation_manifest.json`: corrected scope and reviewed-source
  metadata identities,32 frozen descriptors/permits and one-attempt limits.
- `research/qd012/actual_snapshot_entry.py`: gated callable/CLI and compact
  one-shot diagnostic with bounded input transport/cooperative resource checks.
- This new report. Old report48a09a6, old tests, adapters, production/shared docs,
  source checkout, index/user work, QR and old evidence remain untouched.

QR010 binding at `88168f34c8c2855e9e65510bcde749cc459ff12a`,
`research/qr010/shared-account-binding.md`, was read directly with `git show`.
It specifies **8 scenarios / 9 joint account trajectories**, one shared BTC+ETH
10000USDT account per trajectory. The old manifest's `scenarios=10` was a counting
error, not authority for another path. Its old report remains historical.

| Scenario | Exact trajectory name |
| --- | --- |
| P0 | ALLOW_ALL |
| P0 | SKIP_FIRST_ADMISSIBLE_BASKET |
| F_HIGH | ALLOW_ALL |
| F_REFERENCE | ALLOW_ALL |
| S_HIGH | ALLOW_ALL |
| L_EXTRA | ALLOW_ALL |
| Q_LOW | ALLOW_ALL |
| M_SLOW | ALLOW_ALL |
| T_FILL_FIRST | ALLOW_ALL |

No trajectory executes in this diagnostic. It does not select an account cutoff
or call `assemble` to manufacture a scenario. No new scientific assumptions.

## Exact proposed command — NOT run, NOT currently authorized

Only after a separate explicit human approval, set
`qd012_human_approval_ref` to the reference for that approval. This variable is
deliberately unset by this task. The shell rejects an absent reference; the entry
also requires its authorization flag, a named reference and the exact manifest
SHA. A reference string is an operator assertion, not independent proof of consent.

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd012.actual_snapshot_entry \
  --authorize-actual-snapshot \
  --human-authorization-ref "${qd012_human_approval_ref:?Set only after explicit human approval}" \
  --manifest-sha256 657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a
```

The default callable `run()` is OFF; no default/raw probe or dry-run switch exists.
No budget/scope/output-path overrides or automatic retry/resume are exposed.
The command above has not been executed, including without its flags or with help.

Scope is fixed by the hashed manifest:

- Both BTC/ETH: full2023-01-01T00:00Z through2024-01-01T00:00Z closed hourly
  indicator/funding prefix; **8760 closed bars per coin**, no shortening to fit.
- Exactly one native snapshot at2024-01-01T00:00Z (`1704067200000000` UTC-us).
- Execution-only open at2024-01-01T01:00Z (`1704070800000000` UTC-us).
  Sequential parsing may encounter hour00 and the hour02 stop sentinel. Only
  hour01 open is projected; future H/L/C/V and availability never enter the
  `warmup` dict supplied to `prepare_native`.
- MARK queries at00:00 and01:00 for each coin, roles exactly valuation,
  reservation, decision, permitted_fill. No funding snapshot, account trajectory,
  order or label is created by this diagnostic.
- Calls actual QD012 prefix readers, `prepare_native`, `execution_opens`,
  `mark_selectors` and `Query`/selector directly. No allocation/policy/trade call.
  Forecasts from unchanged native `signal_at` are diagnostic fields only.

## Frozen allowlist and scalar permits

`snapshot_entry_plan.allowlist` enumerates the exact32 absolute paths, accepted
object SHA256/byte identities, source units, intervals and per-object bounds.
No glob, latest-file selection, additional month or later-year object is opened.
Every descriptor must match its authoritative metadata before payload consumption.
Current files are not whole-object rehashed or passed through a history checker.

Four metadata identities are checked (metadata bytes only):

| Metadata | SHA256 |
| --- | --- |
| OHLCV v3 manifest | `c1e6056058fd312d472e96fddfea15e78c778847de9942e5757cb39ad2ac9b91` |
| MARK r2 raw handoff | `30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce` |
| Funding raw lineage handoff | `176d0c987d23d4b29b7f901b7dfaa6eeffe56ad84bc57ee07f89a261dab65be5` |
| MARK r2 result, referenced by that handoff | `3f601ebf45b2e97825b9c701234060a3348e47e508c28211b98572ed38f5a21e` |

The fourth document provides existing accepted per-object expanded byte/physical
row counts. It is read as metadata; its checks are adopted rather than rerun.

| Source group | Objects | Whole accepted physical bytes | Expanded byte bound | Physical row bound |
| --- | ---: | ---: | ---: | ---: |
| Hourly BTC/ETH JSONL | 2 | 75211578 | 75211578 | 17526 |
| Funding Jan2023–Jan2024 | 26 | 12321 | 46780 | 2402 |
| MARK Dec2023/Jan2024 | 4 | 12254715 | 38466001 | 908454 |
| Total | 32 | **87478614** | **113724359** | **928382** |

These are accepted metadata upper bounds, **not observed consumed bytes**.

- Hourly: each file's physical/expanded cap equals its exact accepted file size;
  row cap is8763:8760warmup +hour00 traversal +hour01 execution row +one hour02
  stop sentinel. Permit `[1672531200000000,1704074400000000)` applies only to
  parsing. Native receives separately clipped8760 rows with close <=snapshot.
  No2026-hour scan. Each accepted row is locally parsed/validated by the existing
  reader, without a full-dataset checker or full-payload hash pass.
- Funding: per file cap is accepted `rows+1` for an optional exact header and the
  accepted expanded byte count; total2376 data rows +26 possible headers. Permit
  `[1672531200000000,1704067200000000)`. The two January2024 objects remain in the
  frozen32-object allowlist but metadata proves their first source >=cutoff;
  the entry leaves them **unopened**. The total cap conservatively includes them.
  Rates retain original exact decimal UTC seconds (max6dp), strict-next-hour R;
  only rate availability <=snapshot enters native preparation. Integer source
  compatibility is reported separately, without rounding/accounting mapping.
- MARK: per-object bounds from accepted result metadata:

| Month / symbol | Physical bytes | Expanded bytes | Physical rows |
| --- | ---: | ---: | ---: |
| 202312 BTC_USDT | 3763846 | 11396140 | 265003 |
| 202312 ETH_USDT | 2492590 | 8585874 | 209999 |
| 202401 BTC_USDT | 4873368 | 14842338 | 344443 |
| 202401 ETH_USDT | 1124911 | 3641649 | 89009 |

MARK permits start at the declared month start and end2024-01-01T01:00Z. Ordered
selection may traverse December from gzip start and retain minimal lookahead;
it stops in early January and does not consume that month's later history.
Original source seconds/max6dp, MARK field index2, exact lexeme aliases and
source+60s /120s /60s freshness semantics remain in the unchanged QD012 parsers.
No list of all MARK points is retained. Selected query DTOs keep UNKNOWN reasons
and raw lineage; a failed preparation never becomes a coverage PASS.

## One attempt, observations and artifacts

Proposed limits **for human review, not already approved**:

- Observed wall300s, CPU200s, peak RSS268435456 bytes (256MiB).
- Global physical/compressed input134217728 bytes (128MiB), additionally capped
  by each accepted object's exact physical bytes and no reopening.
- Global expanded input113724359 bytes (~108.46MiB), derived from the selected
  metadata, and928382 yielded physical lines. Both have per-object caps above.
- New output8388608 bytes (8MiB), including receipt/result/failure;64KiB reserved
  from normal result allocation for a failure summary. No full prefix/cache dump.

The entry temporarily replaces only `sources._lines` in its own future process
with a counted transport; source files/adapters stay unchanged. Actual QD012 format
parsers and causal calculations remain the consumers. Physical reads are <=4096
bytes/chunk, decompressor output <=65536 bytes/chunk and physical lines <=1MiB.
All produced expanded bytes, including lookahead, are counted; row bounds include
headers/sentinels. Each path can open once. The hook and handles restore/close in
`finally`; this is a synchronous reader wrapper, not a supervisor/platform.

Resource checks occur before/after input chunks, rows, query selections and the
single native call. `resource.getrusage` reports cumulative CPU delta and observed
peak RSS with explicit macOS/Linux units; no Windows/NAS claim. Python socket
connections are blocked during the identity/preparation block. No network tool,
service or deployment is involved; this is not an OS network sandbox.

**Checks are cooperative, not hard OS enforcement.** Native preparation, imports,
decompression, JSON encoding and fsync can overshoot observed budgets before the
next check. Full-year native memory and the new transport have not been executed;
256MiB sufficiency is unknown. Stop at the first known limit/failure; do not
silently shorten the full year or increase a limit. No killpg/process supervisor,
automatic retry, checkpoint restore or resumption.

Fixed future artifact directory (not created by this task):

`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd012/actual-snapshot-20240101-attempt-1/`

1. `launch-receipt.json`: exclusive directory/file creation, parent-directory
   barrier for the new attempt directory, and receipt file/directory
   fsync **before payload imports/consumption**. Records human reference, reviewed
   manifest/code identity, limits and consumed-attempt/no-retry status. Metadata/
   code identity checks and permitted execution follow this receipt.
2. `result.json`: exclusive durable compact result: exact source last closed row
   and execution open, computed f64 signal/full covariance, actual warmup cache/
   prefix hashes and initializer, selected MARK DTOs/UNKNOWN lineage, funding
   source compatibility, actual per-object input counters and observed resources.
   Exact financial source text is separate from computed float/decimal projections.
3. `failure.json`: best-effort exclusive durable reason, observed counters,
   missing-input reason and planned query times with NOT_COMPLETED status. Partial
   result writes are counted before spending any failure reserve. No retry loop.

Presence of the fixed directory forbids another invocation, even with a different
reference. A receipt without a terminal result, partial output, interruption or
unknown outcome is **UNKNOWN and consumed**, never permission to run again.
Hard termination/fsync failure can prevent a terminal summary; the entry cannot
guarantee a durable final report under every failure. A new human decision is
needed to resolve any subsequent action; do not delete/reset/relabel this path.

Future exit/result meanings: OFF (2); completed snapshot for review (0); computed
snapshot with required MARK UNKNOWN (3); failure/limit/identity/missing-source or
existing-attempt rejection (1). None imply training readiness or account acceptance.

## Static checks, identities and remaining dependencies

Performed only standard-library AST/JSON/metadata/hash inspection and Git diff
checks. No repository/new runner/native module was imported as verification.

- Parsed `prepare.py` and `actual_snapshot_entry.py` syntax with `ast.parse`.
- Inspected call names: no `assemble`, account `create`/`advance`, allocation,
  fit/training/download, Popen or killpg calls in the entry. This is limited static
  inspection, **not proof of runtime correctness/security**.
- Confirmed literal default authorization=False,8/9 trajectory metadata,32 unique
  paths, scalar totals from descriptors,28 code hashes matching saved source and
  future attempt directory absent. This did not evaluate a MARK query.
- `git diff --check` / staged whitespace checks completed; no tests, dry-run,
  smoke run, old QD012 checks or native data experiment.
- Optional `snapshot-prep/` was not ignored in this checkout; its newly generated
  metadata-only JSON was removed and the static results preserved here instead.
  No ignore rule or old evidence was changed.

Final static identities:

| File | SHA256 |
| --- | --- |
| `actual_snapshot_entry.py` | `90478fa9fdc0a98d6db49e10adea1e9f35bc4ed5c9f08808b7c38707ed1c01b2` |
| `prepare.py` | `9d27d4130cd3d1c5bbca8b7eb0a126147c55072e55c6380ee75c894f86e0e831` |
| `preparation_manifest.json` | `657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a` |

Manifest `code_sha256` pins28 local implementation/dependency files (including
the dynamically loaded ledger reference); their code bytes may be read to check
identity, not actual data. Existing Python/NumPy/pandas/gate-api/YAML dependencies
and immutable accepted source availability are required at future invocation;
no install/upgrade performed. Runtime versions will be recorded if approved.
External package binaries are not comprehensively locked/hashed by this task.

This is a new **unexecuted static candidate**. The adopted48a09a6 synthetic result
is not retested or claimed to certify this entry, counted gzip transport, resource
handling, output durability or a full-year snapshot. Actual-file existence,
observed consumed bytes, missing records, MARK coverage, successful full-year
native preparation and resource sufficiency are unknown. Full-object integrity
is inherited provenance; normal decoding/local format checks are not a new
historical dataset acceptance pass. No QR response/review or new research choice
is required here; the concrete remaining dependency is a separate human decision
on this exact one-attempt command/scope/budget. Commit scoped files and stop.
