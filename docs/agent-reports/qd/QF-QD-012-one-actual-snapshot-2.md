# QF-QD-012 — separately authorized actual snapshot, invocation 2

2026-10-29 Australia/Melbourne. **PASS for this bounded actual-input snapshot
only.** Exact entry outcome `SNAPSHOT_COMPUTED_FOR_REVIEW`, exit0. This is not
full replay, controlled-account acceptance, model/sample-matrix readiness or
permission to train. No retry or follow-up execution.

## Authority, identities and invocation count

- Dispatch `QF-DISPATCH-20261029-QD012-ONE-ACTUAL-SNAPSHOT-2`.
- New human answer “批准更正引用后执行一次（推荐）”, source
  `request_user_input_async/call_4d3d1bb15aba4fd1a75948f70d13edeb/item0`.
  Named reference **`QF-APPROVAL-QD012-ACTUAL-SNAPSHOT-2`** maps to:
  `/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qd012-actual-snapshot-approval-2.json`.
  This new approval was read before launch. Its answered_at is
  2026-10-29T01:00:59.335133+00:00 (12:00:59.335133 AEDT).
- QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
  `codex/qd-cache-safety`; initially clean at report parent
  **`ad402601c09ff6d89a7d51dadc341c5263f40297`**.
- Actual implementation remains exactly
  **`7f481daa70735c7619f385d0843b02e05f9dd11f`**. Entry SHA256
  `90478fa9fdc0a98d6db49e10adea1e9f35bc4ed5c9f08808b7c38707ed1c01b2`;
  manifest SHA256
  `657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a`.
  Permitted preflight verified all28 code pins and absent fixed attempt directory.
  The entry then checked its pinned metadata/code identities before consuming data.
- **This dispatch:1 CLI invocation,0 retries. Cumulative:2 CLI invocations.** The
  first invocation failed before launch/raw access and remains preserved in
  `QF-QD-012-one-actual-snapshot.md` atad40260. Its approval was not reused.
  The second invocation is the first actual payload consumption/launch receipt.
  The original fixed directory name `attempt-1` is not a claim of one cumulative
  CLI call and was not renamed to hide the earlier failure.
- This report is the sole committed change. Resolve its exact report commit with
  `git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-012-one-actual-snapshot-2.md`.
  Runtime evidence is retained uncommitted at its authorized path. No implementation,
  manifest, budget, strategy, old report or shared document changed.

## Exact command and lifecycle evidence

Executed once, from the QD worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd012.actual_snapshot_entry --authorize-actual-snapshot --human-authorization-ref 'QF-APPROVAL-QD012-ACTUAL-SNAPSHOT-2' --manifest-sha256 657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a
```

No wrapper/supervisor, help/default/dry-run, import probe, test or repair. Tool
session22800 was polled to receive this same invocation's completion, not another
execution. Final output:

```json
{"artifacts": "/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd012/actual-snapshot-20240101-attempt-1", "status": "SNAPSHOT_COMPUTED_FOR_REVIEW"}
```

Exit0; no remaining process/session. Exclusive launch receipt timestamp
2026-10-29T01:01:53.238727+00:00 = **12:01:53.238727 AEDT**. The receipt records
the new named reference, manifest/code identities and consumed-attempt status.
The approval JSON's prelaunch counters were not edited because they are outside
this task's exclusive scope; receipt/result and this report record the actual run.
No exact end timestamp was separately recorded or inferred from polling.

| Stage | Reached / actual outcome |
| --- | --- |
| Exact source/branch/approval preflight | Completed; clean parent,28 code identities match, attempt path absent |
| Named reference / manifest gate | Passed with new explicit approval mapping |
| Exclusive directory and durable launch receipt | Created before input consumption; original fixed path used |
| Runtime source/metadata identity checks | Completed before payload read |
| Full2023closed hourly/funding prefix | Read; actual8760native warmup bars/coin, no shortened period |
| Execution-only01:00open | Projected for both assets, separate from warmup |
| Native causal features/regime/vol/full2x2 covariance | Computed at00:00snapshot; real initializer and cache identities returned |
| MARK00:00/01:00queries | Four selections SUPPORTED, all four requested roles each |
| Compact durable result | Written; actual counters and runtime identities retained |
| Account/registered port advance, order/fill, labels/matrix/fit | Not executed / not authorized |

## Native warmup, cutoff and outputs

Result `snapshot_us=1704067200000000` (2024-01-01T00:00Z). Both native prefixes:

- `count=8760`, first open `1672531200000000` (2023-01-01T00:00Z).
- Last close **and max source availability** `1704067200000000` (snapshot).
- Last native short bar open `1704063600000000` (2023-12-31T23:00Z).
- Main open `1704052800000000` (2023-12-31T20:00Z), covariance availability00:00Z.
- Regime open `1703980800000000` (2023-12-31T00:00Z), availability00:00Z.

Actual native regime is **trend_up for BTC and ETH**, rather than the shorter
synthetic fixture's legitimate range fallback. Native output examples below are
computed values, not exact economic amounts or profitability evidence:

| Instrument | Short forecast | Main forecast | Carry forecast | Sizing annual std | Adaptive risk | Efficiency ratio | Range vol ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC_USDT | -1.1568900654353231 | 1.7079759033709871 | -20.0 | 0.31045896727353556 | 0.9999999999846065 | 0.05862112374638299 | 1.048338414482248 |
| ETH_USDT | -5.105846843244831 | 5.974132731796924 | -20.0 | 0.4054775151924779 | 0.9859285079774681 | 0.07207562032296184 | 1.0438944903275604 |

Full native annual covariance, fixed order `[BTC_USDT, ETH_USDT]`:

```text
[[0.09373963874314814, 0.09559736479282131],
 [0.09559736479282131, 0.16012611157030962]]
```

The result retains exact native f64 representations:

```text
BTC diagonal  0x1.7ff522abd9ceep-4
cross         0x1.87911a35e7377p-4
ETH diagonal  0x1.47f032e370e67p-3
```

Both diagonals and cross-term are computed independently of sizing std and exposed
in v2 observations. No covariance or scaler/model estimator was fitted/replaced.
No allocation/trade decision was made from these diagnostic forecasts. Selected
timing fields include actual3600s bar duration, recent ranges, quality/extension
and breakout booleans. ML entry fields are null; no model activation/fitting.

Native timing initializer is `{}` from the real constructor, with indicator-only
warmup: no2023policy calls, trades, fills or cashflows. Context identity:
`3f1d2e30db6f889639edefbc4fb9e2daac4f25d220425f5ac37aaa8cf9a6128f`.

| Identity | BTC_USDT | ETH_USDT |
| --- | --- | --- |
| Hour prefix SHA256 | `e78b401be25194e942d4654e7b3787c18354a34705df39d9a463c5241e00c07b` | `456c72acc0424a71d3726bcaf832e535d78756b9897e2f3f3ca164d5c469fc7c` |
| Encoded cache expanded bytes | 5051050 | 5051639 |
| Encoded cache SHA256 | `41c0e52d7541dec73f30a8a34af4fa8e22b3761ce905ef5206d7399efceea0a5` | `2c7f93f67454b90cd449093ca8c9fdefffddf3556323bc043c646ee056b1be96` |

Full prefix/context payloads were not dumped. Prefix source-lineage hashes and six
native code hashes remain in result.json; all exact observed fields are retained
there without rerunning a native function to fill this report.

### Execution-open isolation and exact source values

Last closed exact source prices/volumes are BTC close`42316.8`, volume`5177057`
contracts; ETH close`2283.9`, volume`566781` contracts. Decimal source text remains
separate from computed f64 projections. The execution-only proxy is:

| Instrument | UTC time | Exact open USDT/base | Native data linkage |
| --- | --- | ---: | --- |
| BTC_USDT | 2024-01-01T01:00Z | 42507.9 | `qd012-open:529680d06f8fd6e601f328412b9c3d3920617cc1ca1fb4966606a0f149d4851f` |
| ETH_USDT | 2024-01-01T01:00Z | 2297.55 | `qd012-open:f9c8ee434fc4285799a163a9e2addb5029a39164764ec26a0082b82c43af7bb4` |

Hourly readers yielded8763physical lines/file: the8760warmup, hour00traversal,
hour01execution row and hour02stop sentinel. The executed entry separately clipped
warmup to close <=00:00 before native preparation and projected only open from the
hour01record. Result max native availability remains00:00 and native close remains
the prior closed hour. Future H/L/C/V/availability was not passed to native input.
No extra future-perturbation test was run or claimed by this invocation.

### Funding time compatibility

Read24funding objects covering2023; the two allowlisted January2024objects were
left unopened from their metadata cutoff. Actual funding physical rows2190.
Returned prefix source-time check: `compatible=true`, `fractional_count=0`,
`examples=[]`, `no_rounding=true`. This concerns **the consumed2023prefix only**,
not all8214historical records or a future account window. Accounting mapping was
explicitly not executed. Funding prefix identity:
`9a22595abe6a81d733bc1670cb9b74ee6b42763826e7d4807aab1034cc495eaa`.

Native carry retains approved strict-next-hour R, unchanged main-bar-open alignment
and named28800-second8h-equivalent units. This diagnostic creates no funding
snapshot obligations, posting or finality/account event and does not prove
historically observed exchange arrival clocks.

## All MARK selections and provenance

For every row below, the **four roles valuation/reservation/decision/permitted_fill
are each SUPPORTED** using that same selection. `unknown_reason=null`; no required
query is UNKNOWN. There were4point selections /16role uses, not16independent source
observations. Prices are exact source decimal USDT/base; times are UTC microseconds.

| Instrument / query UTC | Price | Source UTC-us | Scenario available UTC-us | Raw object / physical row |
| --- | ---: | ---: | ---: | --- |
| BTC /2024-01-01T00:00Z | 42312.98 | 1704067113838945 | 1704067173838945 | `021-202312-BTC_USDT.part` /264998 |
| ETH /2024-01-01T00:00Z | 2284 | 1704067104829104 | 1704067164829104 | `022-202312-ETH_USDT.part` /209997 |
| BTC /2024-01-01T01:00Z | 42522.31 | 1704070706841732 | 1704070766841732 | `023-202401-BTC_USDT.part` /291 |
| ETH /2024-01-01T01:00Z | 2298.51 | 1704070725828546 | 1704070785828546 | `024-202401-ETH_USDT.part` /95 |

These four files are under the accepted coordinator root:
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/mark-archive-intake-through-september-r2/raw/`.

| Raw object | Accepted expected SHA256 |
| --- | --- |
| 021 BTC Dec2023 | `fbdacc13ce32402ed776bfcbd20d92c78b0411725841c4f915ac0b04d7c1405c` |
| 022 ETH Dec2023 | `f6ef2ff9cd1dbd6fd5e88f463d1663d6850492c501b9ba98ca75501c006b2759` |
| 023 BTC Jan2024 | `d8328375a768294c5c70b11ffc47bbca8741f072e7bf31eb6b5e0f7eb83a817c` |
| 024 ETH Jan2024 | `9a8c08a9fbd8f50114066908543409b0f3e6dc7cc32f1d9704f0787ce8e4595f` |

Every selected lineage also binds MARK handoff SHA
`30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce`.
Each selected point has one retained raw reference. Expected raw hashes are source
provenance, not a new whole-object rehash. Scenario available time is source+60s,
not an observed historical arrival time. Source / availability ages, derived only
from these saved result timestamps:

| Query | Source age seconds | Availability age seconds |
| --- | ---: | ---: |
| BTC00:00 | 86.161055 | 26.161055 |
| ETH00:00 | 95.170896 | 35.170896 |
| BTC01:00 | 93.158268 | 33.158268 |
| ETH01:00 | 74.171454 | 14.171454 |

This establishes support for these four named query points/roles only. It is not
full-history MARK coverage, alternate-clock sensitivity or gap/alias validation.

## Observed resources, actual input and retained files

Values below are from the one result's observer/per-object counters, not another
run, OS sampler or benchmark:

| Measurement | Actual | Approved bound |
| --- | ---: | ---: |
| Observed wall seconds | 11.733512791106477 | 300 |
| Observed CPU seconds | 11.258683 | 200 |
| Peak RSS bytes | 214499328 =204.5625MiB | 268435456 =256MiB |
| Physical/compressed payload input bytes | 26305583 (~25.09MiB) | 134217728 |
| Expanded input bytes | 40087527 (~38.23MiB) | 113724359 |
| Yielded physical source lines | 495109 | 928382 |
| Actual retained runtime evidence bytes | 28440 | 8388608 |

Observation sampling precedes final result serialization/write/fsync; no separate
exact total-process wall/CPU/RSS measurement was added afterward. Result's
`observed.output_bytes=3347` is the receipt-only count at sampling time, and its
including-result upper bound is28646. Final two-file stat sum is **28440bytes**.
No observed budget breach was reported; these are cooperative checks, not hard
OS guarantees or device-level physical I/O measurements. Input counters account
binary read bytes/decompressor output, including buffered lookahead, and exclude
code/metadata inspection bytes and OS/filesystem read amplification.

| Actual consumed group | Opened objects | Physical bytes | Expanded bytes | Physical rows |
| --- | ---: | ---: | ---: | ---: |
| OHLCV | 2 | 20025344 | 20025344 | 17526 |
| Funding | 24 | 11515 | 43335 | 2190 |
| MARK | 4 | 6268724 | 20018848 | 475393 |
| Total | **30** | **26305583** | **40087527** | **495109** |

The frozen32-object metadata's whole physical total87478614bytes remains **metadata
provenance**, not actual consumption. Both December MARK prefixes were traversed;
January BTC/ETH used only8192/4096physical bytes and294/97yielded rows respectively.
No later-year source was reopened. `full_payload_sha_or_crc_revalidation=false`:
no accepted dataset checker or full payload hashing run. Normal decoding/format
checks in the consumed prefix are not a new whole-history acceptance pass.

Fixed retained directory:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd012/actual-snapshot-20240101-attempt-1/`

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `launch-receipt.json` | 3347 | `4139a4b584a18838edd612721a7afb5c4bf93114705d531fffe96aa279e79f7c` |
| `result.json` | 25093 | `b3098f526cdf3cd8f4fefd8bf535da8de4e8f8ff5cc2c4dd4268945ab637e701` |
| `failure.json` | Absent | No failure summary was generated |

Runtime recorded Python3.13.7 (Clang16.0.0), NumPy2.5.2, pandas3.0.5. No dependencies
were installed/upgraded. Only the small generated receipt/result were read after
completion to write this report, calculate simple timestamp ages/group totals and
hash these two evidence files. No source data was reread to supplement measurements.

## Limits and stop

One successful actual source/native snapshot now exists for this exact cutoff,
implementation, warmup, sources and four queries. Registered QD011 account/port
execution, full replay, checkpointing, fills, settlement tail, full funding window,
full query coverage, labels/model matrix, future model validation and production
behavior remain outside this evidence. Prior synthetic results are not promoted
to actual-account acceptance. No profitability or survival claim follows.

The new approval is consumed; the fixed receipt directory now exists and must not
be deleted/renamed/reused for another run. Both previous failure evidence/report
and this successful result are preserved. No implementation, clocks, data or
limits were repaired, and no additional test/research validation was dispatched.

Only this report is committed; the two authorized runtime artifacts remain
untracked local evidence, not unrelated user modifications. No ignore rule was
changed to conceal them. No other agent/user changes were observed. Main/source
checkout remains unchanged; no shared-doc/QR edit, account/engine/real credential,
network/download, order, fit/scaler/calibration, label/matrix, push/integration,
Windows or NAS action occurred. Coordinator can review this exact report/result;
any next step requires its own scope and authorization. Stop after reporting.
