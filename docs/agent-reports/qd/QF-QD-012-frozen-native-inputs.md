# QF-QD-012 — frozen raw inputs to native v2 preparation

2026-10-29, Australia/Melbourne. **Implemented; new bounded synthetic checks
passed across the initial invocation and named affected-method reruns. Actual
historical execution remains OFF. This is a new candidate, not extension of the
old QD011 lifecycle PASS.**

## Authority, baseline and scope

- Dispatch `QF-DISPATCH-20261028-QD012-FROZEN-NATIVE-INPUTS-1` and same-task
  amendment `QF-AMEND-20261028-QD012-EXACT-NATIVE-FIELDS-1`; persisted coordinator
  records `qd012-frozen-native-inputs.txt` and
  `qd012-exact-native-fields-amendment.txt` were read completely.
- Role QD; existing branch `codex/qd-cache-safety`, worktree
  `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Exact parent/base `61536c823926fb873f9a4a130778f34e0b87c161`. The initial clean
  state was checked before this task's implementation. After context recovery,
  the unstaged QD011 edits and untracked QD012 modules were identified as this
  task's own in-progress implementation and preserved.
- A recovery error briefly returned to read-only QD-001 cache inspection and an
  incorrect old-task completion response. No cache edits/tests, new worktree or
  main changes resulted. Current task resumed after reading the two records.
- Exclusive edits: `research/qd012/{sources,native,queries,prepare}.py`,
  `research/qd012/preparation_manifest.json`, `research/qd011/{driver,ports,codec}.py`,
  `tests/test_qd012_frozen_native_inputs.py`, and this report. New synthetic
  evidence only in ignored `research/.data/qd012/tmp/`.
- No production, QD009/QD010, QR, shared interfaces/journals, old tests/reports,
  existing evidence, dependencies or source-checkout staging changes. Commit
  identity: resolve the commit containing this report with
  `git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-012-frozen-native-inputs.md`.

## Actual callable connection

`load_catalogues` reads and checks only the three authoritative metadata SHA256s.
It maps exactly two v3 hourly objects and 90 MARK / 90 funding descriptors; no raw
payload path is followed. Accepted QR008/QR010/QR014 conclusions are adopted;
stale PENDING fields inside the original candidate metadata do not trigger review
or revalidation. No old v2/cache/application source or download fallback exists.

`ReadPermit` is an explicit bounded invocation input, not proof of human approval.
Default payload entry points reject before opening a file. This task used only
synthetic permits constrained to QD012's temporary directory. A later actual run
requires separately approved paths, exact manifest identity, interval, row and
expanded-byte bounds. Nonabsolute paths, parent traversal and symlinks reject.

| Boundary | Implemented behavior / units |
| --- | --- |
| OHLCV | Actual v3 producer validation, UTC integer microseconds, exact decimal OHLC and contract volume retained as strings; immutable row IDs, source segment and raw references retained. Complete adjacent hourly parents form exact-Fraction UTC 4h/daily bars. |
| Native features | Calls unchanged `strategy_signals.prepare_features` and `signal_at` with actual short/main/regime frames and `research_config`; no model/scaler fit or replacement forecast. Only closed, decision-available rows enter indicators. Missing hour/funding/required indicator is explicit UNAVAILABLE. |
| Carry | Raw funding source time retained; rate becomes available strictly at next hour R. That R is passed as the funding timestamp to the unchanged native **main-bar-open** alignment. Named 28800-second/1095-per-year 8h-equivalent convention retained, independent of actual event spacing. Source 08:00:03 -> R09:00 -> main open12:00 -> decision16:00. |
| Covariance | Calls actual native log-return/EWMA annual covariance for BTC/ETH in fixed order. Only the structurally undefined first differenced return reaches the native initialization convention; other missing returns/grids reject. Full 2x2 matrix is independent of native sizing standard deviations. |
| Warmup / timing | Actual native arrays and every timing-feature field are encoded losslessly using finite-f64 hex, explicit early warmup NaN markers and bounded zlib JSON. Initial timing is the real `ExecutionTiming().dump()` initializer `{}`: approved 2023 is indicator-only, so no fabricated warmup trades, fills, policy state or cashflows exist. |
| Execution opens | Named execution-only retrospective open proxy, exact price, raw row reference, no H/L/C/V returned by `execution_opens`. |
| MARK | Actual four-column gzip CSV, MARK field index2; all-four-lexeme adjacent aliases coalesce with every raw reference retained. Conflicts reject. Ordered selector keeps one lookahead and latest eligible point, not millions of records. Availability source+60s, source age <=120s and availability age <=60s, inclusive. Missing month/no eligible/stale reasons remain UNKNOWN. |
| Funding accounting | Actual gzip CSV `timestamp,funding_rate`, optional exact header, data-row index excludes header. Original source T is the snapshot proxy; R is strict next hour; posting R+60s and finality convention +1h retained. Fractional source microseconds are parsed exactly but QD011 accounting mapping rejects any noninteger source second, without rounding. |

`prepare_native` returns native observations, actual prepared cache, signals,
covariance and prefix lineage. `assemble` prepares every declared economic hour,
execution opens, funding points, query DTOs and exact QD011 `create` keyword
arguments. It returns these and lineage; it **does not call create/advance**, build
model matrices, export labels or fit anything. Its default finite assembly scope
is at most24 decisions, caller-declared. Payload readers have separate explicit
prefix bounds. A long history/account is not silently materialized by default.

## Local QD011 v2 gaps fixed

The original local fixture interface rebuilt constant300-bar arrays, fixed range
regime, adaptive ER/VR=1 and covariance diagonals from sizing sigma squared. Those
approximations are retained only under explicit version1 fixture mode.

Version2 requires `native_context` version `qd011.raw-native-context.v2` and a
separate `native-v2` fact schema. Added observation fields:

- `regime`, `regime_open_us`, `regime_available_us`;
- `efficiency`, `range_vol_ratio`;
- `cov_btc_btc`, `cov_eth_eth`, `cov_available_us` (existing `cov_cross` retained);
- `breakout_long`, `breakout_short`, `bar_seconds`.

Missing required v2 fields/context reject before a store is created. Context hash,
cache hashes/codec/size, aligned arrays, closed timestamps and real initializer
are checked. The policy reconstructs from actual warmup arrays and appends causal
observations; mutated already-closed values and gaps reject. Adaptive fields,
daily regime history and complete timing features are passed to the unchanged
native signal function. Execution/feedback select the declared v2 fact schema.
The policy uses both actual covariance diagonals and cross-term, validates the
joint matrix and records a timestamped native receipt separately from sizing vol.
Unknown account equity cannot produce a new allocation; stale receipts clear.

Explicit MARK DTOs are consumed without discarding UNKNOWN reasons. The supplied
catalogue labels v2 input `derived_native_v2_jsonl`, not actual raw-history coverage
or synthetic fixture history. Source hashes include the parser, native bridge,
carry and existing producer. The local base identity and actual source-file hashes
are recorded; they are not an actual-run approval.

An optional `economic_end_us` distinguishes the economic cutoff from the declared
settlement end. V2 registers hourly settlement ticks but no tail MARK requirements,
policy decisions, fills or reserve renewal. Due orders at/after economic cutoff
cancel. Assembly requires exactly +2h settlement tail. This expresses the approved
window, not forced liquidation or a newly invented terminal label. Only initial
economic tick execution was tested; tail execution is not claimed validated.

Compatibility: native v1 constructors/default arguments remain available for old
fixtures; production interfaces are untouched. Registry hashes and new optional
policy receipt differ, so old checkpoints/registry receipts must not be treated
as interchangeable. Old fixtures/lifecycle were **not rerun**. The one-shot PASS
at61536c8 remains valid for its old exact candidate and scope only.

## New checks and retained failures

All five new methods eventually passed. The initial group was not rerun wholesale;
only named failed/affected methods were subsequently invoked. Each invocation
used the same1600 distinct synthetic hours/coin (60-day closed prefix at the first
decision), no actual market data. Python socket connections were blocked in the
test fixture; this is not an OS network sandbox. Existing interpreter reused.

Base command from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd012_frozen_native_inputs -v
```

Subsequent unittest arguments were full names under
`test_qd012_frozen_native_inputs.FrozenNativeInputs` as listed below. All output
was exclusively retained in `research/.data/qd012/tmp/`; no old artifact deleted.

| Log / invocation | Result / repair | Wall seconds | Peak RSS bytes |
| --- | --- | ---: | ---: |
| `initial-group-1.log` / all5 new methods | 1pass,2fail,2error; actual pandas regime StringArray missing from the lossless converter | 3.59 | 135118848 |
| `failed-native-diagnostic-1.log` / `test_raw_decimal_actual_native_covariance_and_context` | Failed; improved type diagnostic identified StringArray, then converted extension arrays explicitly | 1.54 | 135217152 |
| `affected-methods-1.log` / native/context, future perturbation, funding/gate, registered single tick | First3passed; port failed from stale legacy variable in explicit MARK source-row lookup | 5.08 | 151699456 |
| `failed-port-1.log` / `test_v2_actual_registered_policy_single_tick` | Passed after using DTO source timestamp for lookup | 4.21 | 154419200 |
| `affected-port-final-1.log` / same named port method | Passed after source binding/derived-format labels and timestamped receipt were finalized | 4.26 | 154599424 |
| `metadata-preparation-1.log` / metadata-only manifest generation | Rejected accepted handoff decimal runtime counter511.265; no raw opened | 0.56 | 121487360 |
| `metadata-preparation-2.log` / same metadata-only operation | Passed after preserving metadata decimal-number lexemes as text; raw row validation unchanged | 0.58 | 121618432 |

The initial shell redirection failed because the new evidence directory did not
yet exist. Python/tests did not start in that shell attempt. The directory was
then created; the unique initial log was created once, with no overwrite.

Exact method coverage:

- `test_raw_decimal_actual_native_covariance_and_context`: actual parser/native
  preparation, ETH17.9 contracts retained, raw row index, actual warmup arrays and
  early NaNs, full matrix positive and diag demonstrably different from sigma²,
  float-bit-preserving projection and real initializer.
- `test_future_perturbation_and_explicit_missing_data`: changes all future OHLCV
  and future-available funding; observations/context/covariance unchanged. Missing
  hourly row and missing funding reject explicitly.
- `test_raw_mark_aliases_and_clock_boundaries`: MARK-column selection, aliases,
  exact freshness endpoints, stale/required-month UNKNOWN, exact microseconds,
  conflicting same-time lexemes. Passed in initial group and was not rerun.
- `test_funding_source_semantics_and_execution_off_gate`: actual raw header/row
  convention, strict R/native main-open alignment, fractional rejection, default
  no-read gates and missing v2 covariance early rejection.
- `test_v2_actual_registered_policy_single_tick`: raw adapters -> assembler ->
  reconstructed next-hour native cache -> actual registered QD011 store/one tick.
  Full covariance f64 values, separate sizing vol, actual regime/adaptive fields,
  warmup identity and zero fills checked. No restore/lifecycle/export/labels.

**Cumulative timed process wall19.82s; peak154599424 bytes =147.4375MiB.** Includes
both metadata-generation attempts, so remains below60s/256MiB. No new supervisor
or hard OS-limit claim. Existing ledger/fixture resource budget63MiB was used;
logs and inventory were observed separately. Before the small summary was added,
all retained new evidence totaled21521270 bytes in74files. Including the summary,
the final retained evidence is21524446 bytes in75files (~20.53MiB); all failed
artifacts remain included. The
machine-readable `resource-summary.json` contains log SHA256s and measured values.
Retained output stays below64MiB. No old suite, QD011 lifecycle, S07.02, QR check,
performance benchmark, training, private config/account/credential or engine ran.

## Metadata-only next scope and concrete remaining work

Tracked `research/qd012/preparation_manifest.json` records the three exact source
metadata identities, accepted QR references, code hashes,2023 indicator warmup,
one shared10000USDT account across ten declared scenarios, account interval
2024-01-01 through exclusive2026-10-01 and +2h settlement. It is an execution-OFF
preparation artifact, not evidence that those scenarios ran.

The exact next bounded **proposal**, requiring separate approval, is one native
snapshot at2024-01-01T00:00Z from the full2023 hourly/funding prefix for BTC/ETH,
an execution-only open at01:00Z, and MARK queries00:00/01:00Z for the named
valuation/reservation/decision/permitted-fill roles. No account advance, labels,
fit or new data acquisition. The manifest lists exact existing paths/SHA256s:
2hourly,26funding and4December2023/January2024 MARK descriptors. Their **whole
selected object** byte sizes sum87478614 (~83.43MiB); this is metadata accounting,
not bytes actually consumed. Propose observed wall300s/CPU200s/RSS256MiB/output8MiB/
compressed input128MiB; gzip prefix traversal/expansion, full-year native memory
and output remain unmeasured and may require narrowing or amended limits. No
actual payload was consumed to estimate them. No permission is inferred here.

Known limits / no claims:

- Full raw-object SHA256/gzip CRC are not re-established by bounded partial
  iteration. Expected hashes are accepted manifest provenance; per-v3-row content
  checks run only on supplied synthetic records here. Do not call this a fresh
  validation of the historical dataset.
- Accepted MARK raw evidence with gaps/aliases is not required-query coverage.
  Coverage and integer funding-source compatibility remain UNKNOWN on actual
  history. Missing-month knowledge is supplied to the selector explicitly.
- The synthetic60-day prefix legitimately yields native range fallback because
  the production regime requires a longer daily lookback. Transport of actual
  regime arrays is checked, but real long-lookback trend regimes are not exercised
  or scientifically validated by this small check.
- V2 fill/completion feedback, settlement-tail transitions, full lifecycle and
  checkpoint compatibility are not demonstrated by this one-tick input check.
  Actual risk/sizing/strategy production functions were not changed.
- Full native preparation is prefix-based and recomputed for each declared
  decision; finite assembly retains its bounded input/output set. No full-history
  throughput, memory scalability, numerical portability or replay equivalence
  claim; raw MARK traversal itself is streaming.
- Current native cache encoding is intended for the pinned runtime. No candidate
  model activation, future-profitability or high-leverage-survival claim.

No QR dependency requires action in this task: adopted decisions remain the
authority; QR is idle, no re-review loop or messages spawned. Recommended next
step is integrator review of this exact scoped commit, then a separately approved
bounded actual-input preparation if desired. No automatic continuation, merge,
cherry-pick, push, deployment or trading follows this commit.

## Changed adapter identities

| File | SHA256 |
| --- | --- |
| `research/qd011/driver.py` | `7ec3ff4e59afc8e5954aa6ca34aa47b13b4b0d6c037ee13e2fb213c70a07c895` |
| `research/qd011/ports.py` | `6edd8b255237ec97c965766c83393a523cd2bb343323cd495e555d3c9481fd38` |
| `research/qd011/codec.py` | `bddbab9dd1d7647a484b8188dd162093103c85a2146370bd2594f0724e44b0c8` |
| `research/qd012/sources.py` | `6e59916879ab34ad051cfc7a00fb326979f78c2b6dbd59b59de07f98fe856881` |
| `research/qd012/native.py` | `02337f8929fe2c0468ef065572f140b794e278062d86b3a22e876c37a3ec9f10` |
| `research/qd012/queries.py` | `04287c87ab148dba74c972cad7213f4eec77d62a01f9d1ce6b0ef40fab2e2def` |
| `research/qd012/prepare.py` | `aa3a99a70b3285178c045d753c327c943b07775ec112645bc47523c3db1c5807` |
| `research/qd012/preparation_manifest.json` | `b03c81e6bee732cd592f4c0c079f7c94034eb84d4b8ef78947919c5158106296` |
| `tests/test_qd012_frozen_native_inputs.py` | `1c534c5a00c3443020cd43d180a6f28abfdeb0c4ebce38b4755f8c08d92cfb0e` |

The final metadata-only decimal parser fix was exercised by successful metadata
generation. The last port invocation preceded that metadata-only fix; it did not
change payload parsing or the controlled port. No fresh whole-suite final-candidate
PASS is claimed. Hashes describe final source, not a claim that all historical or
legacy paths were exercised at those hashes.
