# QF-QR-003 Phase A — BTC/ETH feasibility report

Date: 2026-10-28 (Australia/Melbourne)
Engineering integrity: **PASS WITH DISCLOSED DATA LIMITATIONS**
Training readiness: **D2 REQUIRED — EXPLORATORY ONLY, NOT AUTHORIZED**
Strategy edge: **NOT TESTED**
Role: QR. Worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
Branch `codex/qr-validation-baseline`. Phase A base `7650d59cc2983394c38ea8fa5bd102ca90288017`.
QR accounting checkpoint `79cf60b`; frozen run code/input checkpoint `5e15b67`.
Final report/evidence commit is the commit containing this report; no subsequent experiment starts.

## Completed scope and changes

The user approved Phase A and expanded it to BTC and ETH. Completed exactly eight
full offline trajectories: allow-all plus three chronological skip-once diagnostics
per asset, each starting from an independent 10,000 USDT account. Decision interval
`[1785319200,1793091600)` (UTC 2026-07-29 10:00 to 2026-10-27 09:00).
No model fitting, parameter search, additional branches, multi-asset portfolio
comparison, runtime activation or unseen-test claim.

QD supplied a read-only isolated observer of the original replay code. QR added
independent cash-flow/label verification, completed-bar features, source hash and
coverage checks, candidate-to-fill validation, chronological maturity, origin/time
dependence diagnostics and a finite runner. The strategy direction, exit numbers,
costs, sizing and risk defaults remain unchanged. The research-only timing symbol
scope explicitly includes both BTC/ETH; production settings were not read or edited.

Exclusive QR modified files: `research/qr003/protocol-proposal.md`,
`research/qr003/feasibility_audit.py`, `tests/qr_research/test_qr003_feasibility.py`,
`research/qr003/results/` and this report. QD probe/tests/report were reviewed and
executed read-only in the QD worktree, never copied/cherry-picked into the QR branch.
Shared journals remain QD integration-owned; this report supplies their update evidence.

## Results

| Baseline observation | ETH_USDT | BTC_USDT |
|---|---:|---:|
| Decision observations, all signals available | 2,159 | 2,159 |
| Flat decisions with all 21 closed-bar features | 687 | 722 |
| Pre-ML entry proposals / executable / actually opened | 32 / 32 / 32 | 33 / 33 / 33 |
| Natural complete position labels | 31 | 32 |
| Terminal censored positions | 1 | 1 |
| Entries per old time fold | 8 / 12 / 12 | 10 / 9 / 14 |
| Natural labels mature before fold start, including 24h embargo | 0 / 7 / 18 | 0 / 9 / 18 |

These are entry/position counts, not counts of bars or independent samples. The
remaining flat observations include legitimate zero-target/timing/buffer blocks;
none is relabelled as a losing or zero-return trade. In this dataset all true
pre-ML proposals passed budget/quantity checks; synthetic tests cover real failures.

Each skip trajectory has exactly one unfilled eligible proposal and the same
position count as its own baseline. Each observes one newly executable entry that
was unavailable while the baseline held a position. BTC's new entries occur at the
next hourly decision; ETH folds 2/3 do too. ETH fold 1 resumes original conditions
immediately but does not next execute until four hours later. No extra cooldown is
introduced. All six paths first diverge in state/flat qualification one hour after
the intervention. Prefix state/action checks pass through the intervention boundary.

BTC skip times were saved after baseline and before any branch, selected only by
first entry time in each old fold: 1785391200 (Jul 30 06:00), 1788048000 (Aug 30
00:00), 1790676000 (Sep 29 10:00), UTC. ETH retains the three preregistered times.
No branch was ranked, selected, promoted or interpreted as an optimal policy.

Across all eight paths there are **266 proposals, 260 actual position rows and
71 distinct instrument/time/side origins**. Of the 260 position rows, 189 repeat
an origin already present in another trajectory; equal origin does not mean equal
account state or equal outcome. The six intentionally skipped events have null
labels in their own trajectories. There are also eight trajectory-specific terminal
censors. The two allow-all baselines contain **65 positions / 63 natural labels /
2 terminal censors**, not 252 independent natural labels from the repeated paths.

Baseline positions form 28 connected overlapping market-time groups across both
assets, or 7 groups after a 24h buffer. These are dependence diagnostics, **not an
estimated effective sample size** or proof that the groups are independent. The
joint old-fold mature counts are 0 / 16 / 36; the first old fold cannot be scored
as a trained exit-label model test. Combined holding duration is 7–134 hours,
median 41 hours, including terminal censors.

Complete eligible-event observation is established only on the eight executed
paths. Arbitrary future filters can reach other account states and opportunities;
this audit does not construct their counterfactual labels. Labels estimate local
position net PnL / initial filled notional under a continuation policy, not the
advantage of trading versus skipping and not an additive portfolio return.

## Integrity checks and actual tests

- Independently reviewed QD commit `1a2bf705050a0fdc4f47da7e834487f3c37cd800`, parent
  `144ce5b75f9548c471cf537425cb7d3847fa3311`. Delta exactly probe, probe tests, QD report.
  Current file matched committed bytes; probe SHA256
  `4a0e520fa7b0a98565435aec07936bd4425592850a6e2e64b2116acd7d1d45aa`.
- **12 QD focused synthetic tests independently rerun and passed**, sockets blocked:
  exact allow-all result and original call counts for both assets; real synthetic
  signal pipeline; one valid skip; held full/partial exits; budget rejection; missing
  order boundary; causal observations; source drift; exception/nested-call isolation.
- **11 QR focused tests passed**, plus **4 existing causal signal/timing checks**:
  signed funding, reductions counted once, long/short cash identity, terminal and
  missing-data censoring, real label maturity, duplicate/corrupt records, dependency
  grouping, closed-bar feature causality/gap reset, settlement-second offsets,
  candidate/actual-fill consistency, state identity and pre-intervention isolation.
  Focused QR checks were rerun after aligning the exact final QD identity schema.
- Reviewed state ID is digest of `{observed: state_before, position_before: ...}`.
  QR rejects an obsolete state-only digest rather than weakening validation.
- **Eight full approved trajectories completed**, all 17,272 original signal-call
  observations accounted for. No additional stateful calls were made by observation.
  Every actual open matches a non-skipped eligible event; every skipped event is a
  budget-approved fresh entry. All candidate entry features use an exactly closed
  hour; all flat decisions have available feature vectors.
- **All eight position ledgers reconcile** gross PnL, allocated entry/exit fees,
  signed funding, quantities, fill notional and final equity. Largest cash residual
  is 4.55e-12 USDT versus the fixed 1e-8 tolerance. Slippage is already in prices.
- ETH exact 64-execution SHA256 remains
  `c305f8477860be4b3fddbfef1b52113b163caa8b7a6fd5c39c689dcbdcafda1e`;
  BTC new baseline 66-execution SHA256 is
  `088e9ffb3dffd2944df60f0f3894ca478182665ea13ce0c20d39dafe9ee0b3c2`.
- Nine original source CSV hashes match. BTC final intake manifest, three used CSVs
  and all retained raw response hashes independently match. Future funding-rate
  perturbation leaves previous native Carry features identical for both assets.
- QD reported 197 full Python tests and 8 frontend groups; QR did **not** rerun those
  broad suites, because this change touches only isolated research/report paths.

Test commands (use the relevant worktree; all validation ran with socket connect
and create_connection patched to raise, except pure local focused QR unittest runs):

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest tests.qr_research.test_qr003_feasibility -v
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest tests.test_execution_parity.CausalSignalTests tests.test_execution_timing.TimingTests.test_prefix_causality -v
# In QD worktree:
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p test_qd_qr003_probe.py -v
```

## Data limits and corrected timing

Both assets use 3,659 hourly, 2,039 four-hour and 333 daily candles, with identical
raw warmup start ranges. BTC hourly data is a declared slice of its original frozen
file, not a new/reconstructed history. There are no missing evaluated candle or
execution-open slots. Arrival timestamps are unknown; closed-bar availability is
an explicitly idealized assumption.

BTC funding has 536 public records starting 1777680001; the endpoint rejected older
than 180 days. ETH has 768 starting 1770998400. Timestamps can be 1–3 seconds past
settlement grid and remain unrounded. At the first scored main bar, BTC has 528
valid past raw Carry observations and ETH 993; both exceed the native minimum 100,
but neither has the full 1000-bar scaler window. BTC first reaches a full window
at main bar 1792094400, ETH at 1785398400. All scored Carry values/signals are finite
and all scored funding costs have an as-of historical record. Early missing Carry
history remains missing; it was not filled with current rates or interpolated.

Funding completeness diagnostics allow one hourly observation step beyond the
nominal interval for actual delayed timestamps; this never advances timestamps or
changes native rates/costs. Native funding costs use elapsed-time accrual of the
latest known rate, not exact settlement accounting. Static contract/tier snapshots
are not historical point-in-time metadata; no order-book, full liquidation or ADL
simulation is added. These limits preclude profitability/high-leverage-survival claims.

r1 incorrectly described terminal execution time as bar open. Current execution.time
is already bar_time+3600; only terminal trade.close_time retains bar open. QR uses
correct terminal observation availability and **always nulls terminal targets**.

## Training decision D2 — when a model is needed

**Phase A is complete; now is the training-protocol decision point, not automatic
permission to train.** Engineering can generate reproducible labels on observed
paths. Evidence for generalization remains limited: only 63 baseline natural labels,
one short already-inspected historical period, correlated assets/overlapping holds,
0/16/36 mature examples at old fold starts, unequal incomplete funding warmup and
unobserved states under other filters. No confidence interval about model improvement
has been estimated, and no economic precision goal was supplied.

Recommended default: decide the research precision target and broader frozen data
coverage before claiming a model comparison is meaningful. If the user instead
wants an immediate workflow demonstration, D2 may separately authorize **one fixed
low-dimensional linear exploratory baseline**, with training-only preprocessing,
label-end purge + 24h embargo, a seed period, fixed comparisons and budget. It must
remain explicitly exploratory and use full account paths for any later policy
comparison. Do not add algorithms/threshold searches or count repeated branches as
extra evidence. Freeze feature/target population, acceptable uncertainty, stopping
rule and genuinely new final observation period before fitting.

**Deep learning is not supported by this event dataset.** It is deferred until a
larger, diverse, properly validated event history and a specific hypothesis justify
challenging a simple baseline. A large number of hourly bars does not increase the
number of independent exit labels. No GPU/cloud training, model activation or new
history request is initiated here.

## Evidence and reproduction

Tracked `research/qr003/results/summary.json` contains all eight cases and counts;
`candidate-events.json` contains all 266 proposals and entry vectors with null
unobserved/censored targets; `position-labels.json` contains 260 trajectory-labelled
cash-flow rows. Full observations/native results are preserved locally under
`research/runs/qr003-phase-a/` (ignored, about 92.5 MB), pinned by
`results/evidence-sha256.json`. All cases and BTC time-only skip selection remain,
including worse outcomes. No outcome was used to select an intervention.

Inputs and full QR source fingerprints are pinned in `results/phase-a-input-spec.json`.
Run code is commit `5e15b67`; future source drift intentionally fails closed. With
those exact inputs and the external QD probe available, reproduction in a fresh
output directory is:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m research.qr003.feasibility_audit --phase-a-spec research/qr003/results/phase-a-input-spec.json --probe /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/qr003/replay_probe.py --output-directory research/runs/qr003-phase-a-reproduction
```

The actual run additionally blocked network sockets. The runner refuses output
replacement. The original source checkout, staging boundary and QD branch were
not modified. No merge, push, production config/credentials, app/engine startup,
model activation, scheduler or deployed service change occurred.

## Dependencies and next steps

QD implementation and coordinator BTC intake are consumed read-only; no further
engineering change is required for this finite audit. Shared-document integration
and any runtime contract change remain separate approval items. Stop at D2. Present
this evidence to the user, then wait for a specific choice about data/precision and
an explicitly bounded training protocol; do not continue the backlog automatically.
