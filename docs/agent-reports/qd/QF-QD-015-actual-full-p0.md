# QF-QD-015 — single authorized complete BTC/ETH P0 invocation

2026-10-29 Australia/Melbourne. **STOPPED ON INTERNAL RESOURCE LIMIT; complete account target not reached.**

Direct user authorization: “按刚才的资源上限执行一次完整 BTC/ETH P0 回放，失败或超限就停止并保留证据”.
This authorizes one invocation under the previously proposed explicit limits;
training/scaler/calibrator fitting and other scenarios remain unauthorized.

Code commit `577aeed903b9eefdb2c176dac7e3e67f999731ea`, existing QD worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`. Before launch the tracked tree/index were clean; only
existing runtime evidence was untracked. All45code pins matched. Manifest SHA256
`a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2`.
The fixed actual destination and this report were absent before launch.

Single command already launched; **do not repeat**:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd015.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD015-FULL-P0-1 --manifest-sha256 a6c03c4f38cc520ebb56491a6f443843724e93734afbf0e3ce91edff4f7c0da2 --scope full_p0
```

Full2023warmup; one joint BTCETH10000USDT P0/ALLOW_ALL account; economic
`[2024-01-01T00:00Z,2026-10-01T00:00Z)`; settlement-only tail to
`2026-10-01T02:00Z`exclusive. No reset, window selection or forced exit.

Approved ceilings: wall14400s,CPU10800s,RSS1073741824B; input physical1GiB,
expanded2356028624B/53820701rows; total output12GiB/ledger10GiB. Explicit
manifest state/page/request/input/exact/codec ceilings remain, including64MiB
raw/stored journal. Observations/cooperative checks are not hard OS limits.
Stop at the first failure, known breach or unknown result; preserve all evidence;
no repair/retry, limit increase, directory substitution or model fitting.

## Actual result and stopping boundary

The single invocation exited1with
`LedgerError:RESOURCE_EXHAUSTED at /resident_index`; no retry, repair, resume,
new directory or limit change.45code pins/manifest remain unchanged. Only this
report is committed; runtime artifacts remain untracked. Resulting report commit
is the commit containing this file, resolvable with
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-015-actual-full-p0.md`.
Main remains`cae0d2395adf2cd3905e41cb1c16748c8247c32c`; no merge/push.

Last committed HEAD: **321time points /1605adapter invocations**, through
**2024-01-11T16:00Z**, cutoff1704988800000000slot5. Next request
`advance:1704992400000000` targeted2024-01-11T17:00Z and failed before commit.
No journal00000322exists. The last known audit prefix is
`d05e60b02a2917de8a46b5c04bd0ba3c49cac2aa4d5a7ce269b536f34f8859bc`,
economic_state_sha256
`0e7cf4cf7b93249ff0234afe29a7228dc1a30dc62894cceea51f2ea553fa828f`.

CONTROL seq965records`kind=resource_stop`, disposition`stop_resource`, the
same committed sequence/prefix and failed request hash. This is an intentional
resource-stopped store, **not an ACTIVE resumable run**: HEAD's ACTIVE field is
the status of the last committed head, while CONTROL carries RESOURCE_STOPPED.
The write guard is retained. No Ledger reopen/recovery/financial replay was
performed after failure. The original OS process exited; no trading application
or service was launched.

Specific bound: configured resident index8388608B(8MiB), including1048576Breserved
SQLite cache, leaves7340032B(7MiB)working-node capacity. The failure comes from
`NodeIndex._working` checking live charged working nodes plus the next owned
copy against that capacity. The receipt does not record the exact component or
requested allocation, so no more specific root cause is claimed here. This is
distinct from the outer1GiBprocess RSS ceiling. No limit was raised to continue.

## Phases reached and preserved complete input cache

- Named authority, exact code/manifest/metadata gates and exclusive launch receipt
  succeeded. No default/help/test invocation or extra historical acceptance run.
- Complete frozen input preparation succeeded:32856closed hourly bars/coin
  (8760warmup +24096economic),4107funding records/coin. First bar2023-01-01T00:00Z,
  last bar-open2026-09-30T23:00Z. Original full warmup and account scope remain.
- Both coins have24096AVAILABLEnative snapshots and24096execution-open cells.
  No unavailable native cell in the generated full-scope cache. This is input
  preparation evidence, not completed account execution or new prefix research
  validation.
- Actual funding calendar has6024economic entries. Its real time grid generates
  **31109declared ticks**, including2tail ticks, rather than the earlier regular
  synthetic30122tick size illustration. No source times were rounded or replaced
  with the illustration's regular schedule.
- Each coin/clock has31107economic MARKqueries:31105SUPPORTED,2UNKNOWN with
  SOURCE_TOO_OLD, for primary and slow clocks separately. P0uses primary only;
  full primary cache therefore has4UNKNOWNcells across both coins. The committed
  prefix has3210SUPPORTEDledger purpose queries,0UNKNOWN. Cached future
  availability summaries do not imply those future account times were executed.
- Cache reached COMPLETE,294738cells,273457152B. Canonical content digest
  `499fc9cdabbed68cbbaf2c3cc57e5c99f06e0e416404d05a8d5582d13ac0b966`; key
  `eac8926c3a4a568335c229836295bbd6d5bf0d56a4d56543c99ca65b28e7065d`.
  It remains for later explicitly compatible reuse; this failure does not require
  rereading accepted raw history solely to rebuild that identical cache.
- Source normalization/admission and partial continuous account execution reached
 321committed ticks;840financial events,1605registry entries. No annual/block
  account or indicator reset, shortened target or forced exit.
- Failure occurred before the complete economic target and settlement tail, and
  before the normal episode export/result stage. There is **no result.json,
  episodes.jsonl or episode-export manifest** for this invocation. No ad-hoc
  partial exporter was called after failure.

## Partial committed financial state, not a performance result

| Committed records | Count |
| --- | ---: |
| Orders /decisions |22/22|
| Filled /cancelled order states |18/4|
| Fill events |20|
| Lots /closed slices |15/12|
| Reserves |642|
| FundingSnapshot |66|
| ObligationRevision |44|
| Posting |64|
| CompletenessAssertion |4|
| Obligations /entries /links |86/140/190|

Environment tracks6episodes and4issued assertions; native feedback has4completed
entries. These are existing committed receipts, **not4accepted exported training
samples**. Full mature/immature/censored export counts are unavailable because
export was never reached; they must not be reported as zero or inferred as a
finished training dataset. No censoring cutoff at failure was invented.

Known cash8501.3184412174925USDT; unrealized1044.19983495USDT. Signed inventory
BTC3133contracts, ETH226contracts (both long). Already posted fee cash
-97.3550625709125USDT across20postings; funding cash-33.015597641595USDT across44.
These sums use exact arithmetic over existing posting values and describe only
posted cash, not final lifecycle costs or return. No realized-return/performance
percentage is derived from this incomplete account.

Two current funding receipts from2024-01-11T16:00Z have nonempty held ranges,
unknown amount/known-time and posted=false; their rate availability is in the
following hour, whose advance failed. At the last committed view:

- MARKqualificationSUPPORTED, reserved margin97.49148188025USDT and reserved
  fees15.414575594329125USDT;
- economic equity, liabilities, receivables and simulated budget are **null**,
  reasonUNKNOWN_OBLIGATION_TOTAL; actual available margin null(NOT_MODELED);
- new_risk_supported=false, reductions_supported=true.

Unknown obligations were preserved. Cash is not final NAV; no zero liability,
forced liquidation, invented settlement or forecast about future profitability.

## Actual resource observations and preserved evidence

| Observation | Actual | Approved ceiling |
| --- | ---: | ---: |
| Wall seconds |1033.799001416(17m13.8s)|14400|
| CPU seconds |1002.052071|10800|
| Process peak RSS B |260440064(248.375MiB)|1073741824|
| Physical input B |753004474|1073741824|
| Expanded input B |2355936333|2356028624|
| Physical rows yielded |53818194|53820701|

The outer time/RSS/input ceilings were not the stopping cause. The explicit
internal resident-index bound stopped the account first. Time observations start
at the existing budget construction after imports/identity gates and stop before
failure-file serialization; RSS is a process lifetime high-water observation.
They are not OS-hard limits or a paired performance benchmark. No tests, old
benchmark, raw source rescan or second invocation were performed.

SPENT records attempts_started1, active_wall_us216575623, cumulative
total_written_bytes3031332172. Cumulative write-work is not retained disk size.
The failure file's output_bytes136324counts only the launch writer, **not total
output**. Explicit filesystem inventory before its own small metadata file:

- run directory2265files/951012668B, including normalized source2files/412586856B;
- ledger store2259files/538143466B, including321compressed journals/33453971B;
- full cache273457152B;
- all retained QD015evidence including earlier synthetic artifacts and resource
  books3015files/1459515239B, below the12GiBouter ceiling; store below10GiB.

Final totals including inventory are stated below. All old/new evidence, the
failed guard/control, source/fact files, compressed journals and complete cache
remain. No cleanup, ledger mutation, source repair or counter reset occurred.
Only readonly process/file metadata was monitored while the original process
ran. After exit, readonly SQLite queries decoded the committed view and generated
component summaries plus cache availability aggregates; no adapter/readiness/
export API was called, and no recovery or replay was triggered.

## Handoff paths and stop

Under the existing QD worktree:

- launch/failure:`research/.data/qd015/full-p0-actual-1/{launch,failure}.json`;
- committed store:`research/.data/qd015/full-p0-actual-1/P0-ALLOW_ALL/store/`;
- failed request:`.../store/guard-input-00000964.json`, control tip
  `.../store/control-00000965.json`;
- input cache:`research/.data/qd015/markets/eac8926c3a4a568335c229836295bbd6d5bf0d56a4d56543c99ca65b28e7065d.sqlite3`;
- preserved readonly summaries:`.../full-p0-actual-1/readonly-summary.json`,
  `financial-summary.json`,`artifact-inventory.json`.

The complete input cache can reduce future preparation cost under exact producer/
data/config/scope identity. The resource-stopped account directory/reference is
consumed and is **not automatically resumed or replaced**. Any future continuation
requires a concrete resident-index fix and explicit handling of the existing
resource-stop/guard and committed state, preserving the continuous account. That
work is not performed here and no resource increase is proposed as a silent fix.

No QR export contract, proposal inventory, model features/matrix, scaler/calibrator
or fit was created. Training remains unapproved. No shared source, strategy/risk
rule, application/engine, real account/credentials/orders, deployment, NAS/Windows,
network/download, main merge or push was changed. The user requested stopping on
failure: execution is stopped, evidence/report retained, and this task stops after
committing the report.

## Small artifact hashes and final retained sizes

| Artifact relative to actual run root | SHA256 |
| --- | --- |
| `launch.json` | `5e2d6ebcf78bc9955386fd81b99d2cf5defb17f4f00714701a0dffdb06760744` |
| `failure.json` | `1b70bae171cf299c50b47fd5ea61521484c6b2591b3a7ac84504cbd672a89f69` |
| `readonly-summary.json` | `64321503b2373aa127db54046ebc3aea261eeb6b72e6d1580d2d17872556df35` |
| `financial-summary.json` | `0cf23df68e2c9c40e6946455791bd99a3083e80c74a8196acd26f13b6badf17b` |
| `P0-ALLOW_ALL/store/HEAD` | `10fbf1454f0437167d43066f014b4ce635a17c914678fc07bb79154bf7564b3d` |
| `P0-ALLOW_ALL/store/CONTROL` | `45b4b6ed407acd49187cf8ccaa1f15b6300af57131a634611a9aa6a1564fef31` |
| `P0-ALLOW_ALL/store/GENESIS` | `abedf0620b632134f1d5dff91a00e838dc028b48c1031ae23b045e17f887cc40` |
| `P0-ALLOW_ALL/store/SPENT` | `3c54684d7c1c499e6b9f8b628a19eb7f732d72372b3c58e0573619df0977ec4c` |
| `P0-ALLOW_ALL/store/control-00000965.json` | `bb4f693c6e407d3a7fa4930bd20b6cd3dafd81c1261cf45addc97e4d898137cb` |
| `P0-ALLOW_ALL/store/guard-input-00000964.json` | `4aab00f8fcd618545a6ecce21715822808a9a90d3988c468bf6a7915d2ac0c22` |
| `artifact-inventory.json` | `2eebbc213dee9ee2a8ae670b918d30a4d39aea63dd623cc9d1f7f06202a1e2c0` |

Inventory bytes2487. Final run directory2266files/951015155B; all QD015evidence3016files/1459517726B. Report bytes are outside the runtime root.
