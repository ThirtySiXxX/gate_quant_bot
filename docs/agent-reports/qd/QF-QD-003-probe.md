# QF-QD-003-PROBE: isolated offline observer and skip-once boundary

Date: 2026-10-28 (Australia/Melbourne).
Dispatch: `QF-DISPATCH-20261028-QD-003-PROBE-1`.
State: implemented and locally verified; awaiting independent QR acceptance.

## Claim and specification

QD owns only `research/qr003/replay_probe.py`,
`tests/test_qd_qr003_probe.py`, and this report. Worktree:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, parent `144ce5b75f9548c471cf537425cb7d3847fa3311`.
Read protocol r1 at QR commit `7650d59cc2983394c38ea8fa5bd102ca90288017`
with the dispatch's approved BTC extension. QR exclusively edits its protocol,
feasibility consumer, results and semantic tests. No production/shared-file edits.
Read r2 correction at `79cf60bbe6e6bbef9170c85ab68643701172bd11` too: native
terminal execution time is bar close; terminal trade close_time remains bar open.
The implementation commit is the commit containing this report; resolve with
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-003-probe.md`.

## Callable contract (probe-local schema 1)

```python
from research.qr003.replay_probe import probe_replay

run = probe_replay(
    [single_symbol_input], sys_cfg, cost_cfg, initial_capital,
    trajectory_id="ETH:allow-all", skip_entry_at=None,
    risk_cfg=risk_cfg, progress_cb=None,
)
result = run.result          # Original PortfolioBacktestResult, unmodified
events = run.events          # Ordered list of plain dictionaries
skipped = run.skip_applied   # False unless exactly the requested eligible open skipped
counts = run.call_counts    # Original signal_at/decide_execution/build_order_plan/record_fill calls
hashes = run.source_sha256  # Pinned baseline source fingerprints
```

One invocation runs one original account trajectory and one symbol (BTC_USDT or
ETH_USDT), with ML disabled and fixed-margin sizing. The function does not build
inputs, fetch data, run a batch, select a skip timestamp, train or write results.
Caller supplies the frozen scored interval and immutable warmup data and explicitly
sets research timing scope to BTC_USDT and ETH_USDT without changing actual config.
`skip_entry_at` is one UTC Unix decision/open timestamp or None. If that timestamp
has no eligible fresh open it stays unapplied; no later substitute is searched.

Each original `signal_at` call produces one event. It is enriched in place only
when the original loop calls shared decision and order boundaries. Fields include
schema/trajectory/event identity, symbol, decision time, causal signal/timing
feature snapshot, decision-time open price, observed state fingerprint, timing
state before/after, sizing ratios, current notional/equity, plan flags/reasons,
pre-ML entry proposal, original order-check budget/actions/ticket, emitted actions
and skip flag. Post-run `position_before` is an as-of lookup of original execution
records strictly before the decision, not a second position simulator.

`post_budget_eligibility.status` explicitly distinguishes `not_evaluated` (the
original order boundary was not called), `not_applicable` (already held), `rejected`
(actual order error/no positive fresh open), and `eligible` (real executable fresh
open before the research filter). Rejection carries the original reason; no
synthetic zero-PnL labels are added. Actions are proposals, not fill confirmations;
the original result executions/trades remain the authoritative accounting output.

Times are UTC seconds; decision t uses current open and completed source candles.
Prices are USDT/base, signed notionals/equity/budget are USDT, quantities are integer
contracts, fees are fractions and slippage is bps. State fingerprints exclude
trajectory ID so matching pre-decision states can be linked across branches.
They include observed account/timing/sizing state and prior position identity;
they are not serialized restart checkpoints. Nonfinite
observations become null, never zero. No current-bar close/high/low, future funding,
trade outcome or terminal equity is copied into decision snapshots.

The existing replay code object executes once with a private globals dictionary
and forwarding proxies only for shared execution/signal calls. No module/global
monkey patch is installed; normal or exceptional exit leaves globals unchanged.
Original shared functions are each called once per original call site. The one
intervention removes only positive fresh-open actions after successful original
order planning at the requested time; it never rewrites decisions or timing state,
creates fill feedback, filters held-position actions or changes subsequent rules.

## Verification and data inventory

Production core files were checked byte-for-byte against common baseline
`475aaeaa5b9365b360563294e183d912c382b570`; all nine match: backtest,
strategy_execution, execution_timing, position_sizing, strategy_signals, config,
costs, portfolio and risk. Their SHA256 values are pinned in
`EXPECTED_SOURCE_SHA256`; the probe fails closed on drift. Backtest SHA256:
`9183091e85c4354720118c53f0d97b72022f018afa03d9e9479f4929f5a8540c`.
No production/QR/config/dependency file changed. The only task delta is the three
claimed files; no source-checkout writes, integration or network fetch occurred.

**12 focused synthetic tests passed** (1.270 seconds), verifying:

- Complete allow-all result JSON identity for BTC and ETH accounts and unchanged
  original signal/decision/order/fill call counts, including stateful
  ExecutionTiming.decide. An additional actual signal-pipeline test uses 700
  synthetic bars, rather than only substituting controlled signal data.
- Skip exactly once after real budget checks, no suppressed fill feedback,
  next-bar entry still possible, held full/partial exits unchanged, and original
  entry-gate flags still block openings without consuming the requested skip.
- Genuine insufficient-available-margin rejection stays rejected, not a skipped
  event, realized zero or fabricated positive/negative label. Missing signal or
  uncalled order checks remain explicitly not evaluated.
- Perturb current-bar close/high/low, later opens and later funding: event
  snapshots through that decision remain identical, including state identities.
- Original uncaught exception object propagates without retry/wrapping; nested
  probes have independent observers and module globals remain unchanged.
- Unsupported scope, active ML, non-fixed sizing and source drift fail closed.

**197 full Python tests passed** with socket connections blocked (10.407 seconds),
including the prior 185 tests plus 12 probe tests. The ownership fixture's injected
disk-failure log is expected. **8 frontend regression groups passed**. Working and
staged delta whitespace checks passed. Reproduction commands from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p test_qd_qr003_probe.py -v
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

### Read-only inventory (before coordinator acquisition handoff)

QD had no research directory/data at task start. It now contains only the new
probe; no approved data was copied into it. These existing approved immutable
inputs were independently hashed in QR's research data area:
`/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot/research/.data/qr001/`.
Paths below are relative to that exact root. All six files match the frozen QR
`research/qr001/data_manifest.json`. UTC coverage is first/last row, inclusive;
candle timestamps are opens, not ingestion times. No real-data replay was run.

| File | Rows / first timestamp / last timestamp | SHA256 |
| --- | --- | --- |
| classification/BTC_USDT_1h.csv | 9600 / 1758531600 / 1793088000 | f7e607751584c0d5f24273340000642b643230f5b0a693ff2a0ab24872458e58 |
| classification/ETH_USDT_1h.csv | 9600 / 1758531600 / 1793088000 | e3b799053d4c729f0d660c74f6ce50f688b0b59878392d6e3bfc9aeb83a2c87b |
| replay/1h.csv (ETH) | 3659 / 1779919200 / 1793088000 | 8fac19a74ec2421f539e1f88a3cfc63e1bed1c50688abec4642925a46848e336 |
| replay/4h.csv (ETH) | 2039 / 1763726400 / 1793073600 | 80094c6ad49398bdd8aac8dc00ec7421e3c87c41dfda846f619dafae345b3dd6 |
| replay/1d.csv (ETH) | 333 / 1764288000 / 1792972800 | d3055bb3d125d27e527f0ea98b3760eada9a11741369765f73ee5de162282692 |
| replay/funding.csv (ETH) | 768 / 1770998400 / 1793088000 | f7fec7e61222c7031010bca0027a005bd4ec78eea42b75af02d57ce09717e41c |

Source declared by the frozen manifest: previously downloaded Gate public research
CSVs, public candlestick v representation preserved without volume-unit conversion.
Original arrival times are unavailable. Funding starts after the earliest ETH 4h
warmup: retain the original incomplete-history warning. ETH public contract/tier
snapshot: QR `research/qr001/replay_fixture.json`, SHA256
`e7ab2cfabfe09ec233ed64a809b1584255265254b572dce0427a74fac751879b`,
snapshot_asof 2026-10-27T07:16:05.542349+00:00. It is not historical tier evolution
or account/config data. Do not combine ETH classification/replay files.

No complete frozen BTC4h/1d/funding set or BTC contract/tier manifest was present
in QD's research area; these are also absent from the inspected QR-001 manifest.
The dispatch reports existing BTC public contract/tier files elsewhere, but their
exact paths/hashes were not supplied or verified by this inventory. No broader
absence claim is made; never substitute ETH metadata or manufacture BTC inputs.

Control `QF-CONTROL-20261028-QD003-R2-1` assigns bounded BTC acquisition solely to
the coordinator. It reports newly fetched BTC4h (2039 rows) and daily (333 rows),
with funding coverage still under review. This task has not independently verified
those new files or a final manifest. QR should await that manifest/gap report
before declaring BTC replay ready. No duplicate download or operational data,
config, credential or account inspection was performed.

## Consumer handoff and limits

QR owns position cashflow/label attribution, feature-availability diagnostics,
label maturity/censoring and statistical sufficiency. The probe supplies original
results and observations, not training labels or evidence of a trading advantage.
QR runs at most allow-all plus three predeclared skip trajectories per independent
BTC/ETH account on [1785319200,1793091600). ETH skips are 1785607200, 1788040800,
1790618400; BTC skips use first baseline entry timestamps in each old fold, never
PnL. Verify ETH execution hash
`c305f8477860be4b3fddbfef1b52113b163caa8b7a6fd5c39c689dcbdcafda1e`
before comparisons. QD will not run those real-data trajectories in this task.
Training requires a later user decision after Phase A, not this probe delivery.

Important consumer limits:

- Original `result.execution_diagnostics` retains the loop's no-actions diagnostic
  for a deliberately suppressed eligible opening (it may say minimum quantity).
  Use event `skip_applied=True` with `post_budget_eligibility.status=eligible` to
  distinguish the research filter; do not count it as a genuine budget rejection.
  The original result object is not rewritten to hide this diagnostic artifact.
- State IDs describe selected observable state, not complete Markov-state
  equivalence or independent training samples. Position IDs/accounting remain
  authoritative in original executions/trades.
- `decision_price` is the current open. Close-time equity-curve values, future
  position PnL and terminal equity do not enter event state. Static contract/tier
  snapshots retain the replay's approximation, not a new claim of historical
  metadata arrival at every decision.
- The original result contains retrospective charts/summaries; QR must not use
  these as entry features. Preserve native execution.time=bar_time+3600 versus
  terminal trade.close_time=bar_time, and terminal censoring under r2.
- The probe does not enforce the experiment-level four-trajectory cap or choose
  BTC skips; QR's manifest/consumer owns that protocol. No model fitting,
  activation, schema migration, main merge or performance claim is made.

Next: coordinator supplies verified BTC manifest, then QR independently checks the
ETH allow-all hash, BTC/ETH trajectories, accounting, availability and statistical
sufficiency against this exact probe commit. Stop after the implementation commit;
do not resume queued QF-QD-002 or other backlog tasks.
