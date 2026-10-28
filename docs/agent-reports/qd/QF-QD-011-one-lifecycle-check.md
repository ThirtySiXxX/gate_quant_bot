# QF-QD-011-ONE-LIFECYCLE-CHECK

2026-10-29 Australia/Melbourne.
Dispatch: QF-DISPATCH-20261028-QD011-ONE-LIFECYCLE-CHECK-1.

**PASS — one authorized named invocation, exit 0, no repair/retry.** Both internal
continuous/restored branches completed. This supersedes the prior NOT_DEMONSTRATED
status only for this finite lifecycle check, not general ledger/research acceptance.

## Authority, exact candidate and changes

The coordinator relayed the direct human answer “批准这一次定点检查（推荐）”.
Authorized: the final per-tick implementation at
`fbdd50741de4e463ecd121883fcb41c2f36e3b80`, one lifecycle method, aggregate
prewrite allocation 7 -> 63 MiB, retained output target 64 MiB including all older
QD011 evidence, 60s process-wall and 256 MiB peak-RSS observation budgets.

- Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Branch: `codex/qd-cache-safety`; initial worktree/index clean.
- Exact parent/base: `fbdd50741de4e463ecd121883fcb41c2f36e3b80`.
- Test file line 53 changed **only** `7*1024**2` to `63*1024**2` in
  `configure_resource_budget(Path('research/.data/qd011/tmp'), ...)`.
- Only other tracked change is this new report. Economic expectations, fixture
  inputs, methods, implementation, old results and main remain unchanged.
- Launch receipt/log were absent, then exclusively created before invocation;
  approval was consumed at invocation, including any possible setup failure.
- No discovery, joint-rejection rerun, helper probe/default entry, other test,
  historical replay, old suite/S07.02/benchmark, fit or implementation repair.

## Actual invocation and resource record

Exact command, executed once from the worktree above:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd011_controlled_path.ControlledPathTests.test_actual_continuous_joint_native_feedback_and_checkpoint -v
```

stdout/stderr/time output was redirected exclusively to
`research/.data/qd011/tmp/one-lifecycle-approved-1.log`.
Prelaunch receipt: sibling `one-lifecycle-approved-1.launch.txt`.
Tool session 74403 was polled once to receive completion of the same invocation.

| Measurement | Actual |
| --- | --- |
| Invocations / retries | 1 / 0 |
| Unittest result | 1 test, OK, 4.833s inside unittest |
| Process/wrapper exit | 0; no signal exit reported |
| `/usr/bin/time -l` wall | 5.50s |
| CPU user / system / sum | 4.44s / 0.73s / 5.17s |
| Peak RSS | 149946368 bytes = 143 MiB |
| Aggregate retained files, including old QD011 evidence | 452 |
| Aggregate retained output | 18658805 bytes (~17.79 MiB), below 64 MiB |
| New run directory retained bytes | 13058712 |
| Aggregate prewrite allocation | 66060288 bytes = 63 MiB, same existing root |

Prelaunch UTC `2026-10-28T14:24:13Z` corresponds to **2026-10-29 01:24:13 AEDT**.
The log's final mtime was `2026-10-28T14:24:18.870989Z`; this is a filesystem
observation, not a separately measured exact process-end timestamp. Wall/CPU/RSS
come from the actual time wrapper. These are observations, not hard OS guarantees.
No new supervisor was introduced.

New artifacts:
`research/.data/qd011/tmp/new-path-1520397559205875/{continuous,restored}/`.
The shared durable aggregate resource log appended new allocations; all prior
failed stores/logs remain. The aggregate total therefore includes more than the
new run directory plus the previous snapshot. No fresh-budget root or cleanup.

## Completed stages and actual assertions

**All stages below were reached and passed within the named method.**

- One shared account initialized at 10000 USDT. Initial registered native joint
  decisions produced two pending orders and actual reserved margin.
- Each branch committed 8 declared ticks and 30 financial records through
  synthetic cutoff `1704088800000000`, slot 5. Every event origin was generated.
  The two branches contain 60 new published financial records, not imports.
- Each branch had exactly four actual generated fills:

| Instrument | Signed contracts | Price (USDT/base) | Synthetic fill UTC-us |
| --- | ---: | ---: | ---: |
| BTC_USDT | +20 | 100.05 | 1704070800000000 |
| ETH_USDT | +20 | 100.05 | 1704070800000000 |
| ETH_USDT | -20 | 94.9525 | 1704081600000000 |
| BTC_USDT | -20 | 109.945 | 1704085200000000 |

- The opening orders partially filled 20 contracts each; residuals were canceled.
  At least three canceled orders were checked. No extra fill survived restoration.
- Required UNKNOWN at synthetic hour 3 made account equity null. The actual
  native own-asset ETH exit was still generated while account increases were
  suppressed. Policy did not substitute a made-up account equity.
- Actual fee/funding recognition, posting and scoped completeness led to two
  mature exports. BTC timing is disabled, so its completion is a financial/reentry
  marker, **not** a fabricated native timing callback. ETH exercised real native
  fill feedback and one delayed native completion.
- ETH exact delivered fill feedback D = `-1.048750375`; mature net N =
  `-1.050950375`; completion delta = `-0.0022`. Its recorded native pre-reset sum
  was negative. Full-state/sign/error checks passed; final blocked_side=1,
  rearm_price=106 and session_pnl=0 were asserted.
- Exported BTC net `0.0194530075` and ETH net `-1.050950375` matched independent
  literal expectations; final shared cash was `9998.9685026325`. These are tiny
  synthetic accounting examples, not market return or profitability evidence.
- ETH label-known time was `1704085200000000`; BTC was `1704088800000000`, each
  bound to its actual accepted scoped completeness assertion. Both statuses were
  valid and carried registry-bound research exporter references; both retained
  `training_authorized=False`.
- The restored branch checkpointed/restored twice: after the initial pending
  basket and after synthetic hour 4 with delayed ETH finality and a pending BTC
  close. Packed states were equal immediately before/after each restoration.
- The final economic-state hash, all five packed adapter states and both exported
  label dictionaries matched the uninterrupted branch exactly. Waiting episodes
  ended empty, completed episodes numbered two, and fill counts stayed four.

There was no unreached step or assertion failure inside this named method.
The published final journals were inspected read-only afterward for event counts,
actual Fill/Assertion identities and completion state; no second execution or
replay was used to gather this report.

## Identity verification

Full Git diff confirms only the one budget line changed in the existing test.
All implementation hashes match before/after and the exact adopted candidate:

| File | SHA256 |
| --- | --- |
| qd011/codec.py | `c9030054203dee02dda083df830e3ea5477cd887a4b51ab1c2d560475dfb7321` |
| qd011/ports.py | `a648c7739800a0e29c9766a446c4b4bb1189e57e019201986d987983b4499607` |
| qd011/driver.py | `7d3de0c0efbd891a82946e9f94effe0402c71fb3fccee0e75249921694a9298b` |
| qd011/export.py | `8c8664dfd8946929d6aaa76e39ec74b18bb7dac36a331a4a84cf63c8e66ba6ca` |
| qd010/joint_native_bridge.py | `affff49af5477290a0cd0a00c71a9ec9aae9cd9b6c609281731ac36a30313987` |
| qd010/episode_export.py | `4077a9214c29ab4a83ce94f21f179e9db9267db11da7c02d3310fcffa86b5bfe` |
| QD009 ledger | `251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb` |

Test SHA before: `d774b0bf71367329406d073e46b5bea566300800bfd8a8dd523c3595c83f3110`.
After approved budget edit:
`55e28d99047c49ebdf8aa1e71faa894795f22743956254104b00ca5ae52c9a2d`.
Whitespace checks passed; only the test budget line and this report are staged.

## Limitations and handoff

This establishes one finite controlled synthetic lifecycle and restoration
comparison on the adopted implementation. It does not certify the whole ledger,
S07.02, large history/resource scaling, all adversarial/native branches, real
MARK/funding coverage, raw OHLCV feature construction, true historical labels,
research returns or training readiness. Prepared feature observations/warmup are
the existing synthetic fixture, unchanged. Prior unrelated limitations are not
erased by this PASS.

No QR followup, new task, actual replay, further validation or fit is started.
No dependencies/network, app/engine, funds/credentials, main integration/push,
Windows or NAS action. Coordinator can adopt this exact narrow result. The agent
stops after committing the one-line budget change and this report and remains idle.
