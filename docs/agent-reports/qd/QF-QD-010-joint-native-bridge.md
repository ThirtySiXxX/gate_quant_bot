# QF-QD-010-JOINT-NATIVE-BRIDGE

2026-10-29 Australia/Melbourne (test log timestamps use UTC).
Dispatch: QF-DISPATCH-20261028-QD010-JOINT-NATIVE-BRIDGE-1.

**Delivery: implemented offline connection components with bounded synthetic
evidence. PARTIAL: complete continuous joint native replay remains blocked by
the concrete controlled-port/feedback/persistence gaps below. No real replay,
real labels, scaler/model fit or training readiness is claimed.**

## Scope and adopted inputs

QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, clean base
`5284c14b6b6e78808238e95b7d9023e3d5747da0`. Only the five dispatched new files:

- `research/qd010/joint_native_bridge.py`
- `research/qd010/economic_inputs.py`
- `research/qd010/episode_export.py`
- `tests/test_qd010_joint_native_bridge.py`
- `docs/agent-reports/qd/QF-QD-010-joint-native-bridge.md`

QR010 binding at `88168f34c8c2855e9e65510bcde749cc459ff12a`, SHA256
`ed9971f0e47811acdbf54442be51828d26e1684a22c7681237d8cfd0d55aed95`, was
adopted directly. QR014 consumer at `f2c931b8335ca8b1840f22d346a040446c50abb2`,
`feature_samples.py` SHA256
`1f98cf75e68be73683f174b9eeac34db978b2dd331973dacad0d3b65f69906c5`, was
read for field mapping only, not imported/copied/integrated or independently
revalidated. QD006 constraints and the approved QR006/008/009 clocks, cost and
dynamic-budget binding informed the new adapters. No research choice was changed.

Old ledger, launcher, fixtures/oracle, reports, ignored S07.02 evidence, production
sources, shared docs and main are untouched. No new chat/subagent, dependency,
network, download, account, engine, Windows/NAS, merge/cherry-pick or push action.

## Implemented connection

`JointNativeBridge` attaches to a real existing QD009 `Ledger`. It checks one
account with both instruments and initial 10000 USDT. Its default requires
`controlled_adapters`; a separately named `synthetic_reference_demo` mode permits
small import fixtures, never claims they are generated historical native paths.

- `research_config()` constructs research-only native volatility sizing with
  target vol 100%, instrument cap 550%, crypto-major group cap 600%, allocation
  gross cap 40 and no ML. Native ETH timing/trend agreement/trail ATR 3 remain;
  BTC timing remains disabled. Production defaults/leverage are not changed.
- `decide()` calls real `strategy_signals.signal_at`, exactly one real
  `portfolio.allocate_portfolio` with stable BTC/ETH order and full annual 2x2
  covariance, then real `decide_execution` / `build_order_plan`. Conviction and
  adaptive risk run once in the native core. Quantity comparison uses exact
  rational inputs versus native ties-to-even conversion and rejects disagreement.
  No fixed-margin ticket or final-notional/quantity x10 is substituted.
- `finance()` reads real `as_known` balance plus pinned public component scans.
  C/A/L/U/E and slice economics come exclusively from the ledger. It checks E's
  identity, recomputes the research margin/held exit-fee reservation from actual
  lots and qualified supplied MARK, and derives the one shared budget:
  `C-L+min(U_BTC+U_ETH,0)-M_held-F_held-M_pending-F_pending-S_pending`.
  It does not clip U per asset or spend A/positive net U. Controlled mode checks
  actual query-status cohort/source/price binding; the synthetic mode requires
  a matching actual ledger Valuation. No query-time dummy Valuation is created.
- `admit()` checks the frozen increase basket together: known finance/MARK,
  integer min/max, per-instrument total projected 1m tier, current E-based
  instrument/group caps and summed exact reservations. Budget equality passes;
  insufficiency rejects all increases without priority or quantity rescue.
- Unknown finance or missing joint inputs suppress allocation/increases. Healthy
  own-asset native forced exits remain available via real `ExecutionTiming.decide`
  without substituting dummy equity. Missing another coin's execution open does
  not block such a reduction. Native reversal is masked to close first; a later
  flat entry requires a rechecked scoped mature export, without redistributing
  its masked risk target. ETH completion additionally requires the missing port.
- `opportunity()` stages full-basket revalidation before capacity, excluding only
  its own pending reservation. Reductions precede increases; capacity is
  per-asset floor(0.001 x exact previous closed-hour contract volume), each price
  uses adverse 5 bps once, and all residuals are canceled in the staged result.
  One opportunity cannot be consumed twice. Staging does **not** assert fills
  occurred; it returns `REQUIRES_BOUND_LEDGER_TRANSACTION`.
- `commit_bound_transaction()` validates every actual Fill's frozen order,
  decision, quantity, clock, price, fee and multiplier, then calls real
  `Ledger.advance` once with the caller-supplied accepted-source request. It
  neither fabricates generated witnesses nor edits a source registry. Controlled
  requests require generated witnesses from already registered ports. Financial
  batch commit is separate from native feedback publication; ETH commits stop
  with `R01_R04_ATOMIC_NATIVE_FEEDBACK_PORT_NOT_BOUND` rather than fake success.

`FrozenInputs` consumes only caller-supplied frozen records. MARK selects the
latest eligible raw point with source+60s availability, source age <=120s and
available age <=60s (inclusive boundaries). Missing/stale returns null/reason.
Funding retains original source-us as the scenario snapshot, rate available at
the strictly next UTC hour, amount null until qualified inputs exist, posting
amount-known+60s, and finality not-before max(required clocks)+1h. Fees are
0.00075/side and integer fixed multipliers are BTC .0001, ETH .01. Execution-open
projection exposes only instrument/open-us/open-price/source/basis; strategy sees
the previous closed full row. No historical MARK/cadence/availability/raw coverage
is claimed proven merely because the supplied records can be queried.

`export_episode()` uses actual `as_known`, paged lots/slices/events, and actual
scoped `Ledger.readiness`. It checks flat pre-proposal view identity, side/account/
trajectory, closing native-plan/decision/fill bindings, current accepted assertion
references, settled costs and the extra 1h assertion clock. Valid net is a sum of
the existing ledger's exact slice PnL/entry fees/exit fees/funding; gross entry
notional sums all opening lots including adds. It does not maintain a second
economic ledger or deduct costs again. Late corrections make the current export
immature until scoped evidence catches up; exact source/revision/availability
and exclusion reasons are retained. Missing native close lineage yields invalid,
not a valid target. No path-exists or caller `accepted=True` shortcut exists.

## Local consumer mapping and runnable entry

These are new research-local v1 APIs, not INTERFACES shared envelopes, old native
model bundles/21 features, or native backtest result schema 3. No shared contract
file is changed. `qr014_candle_fields(row)` maps to QR014 Candle fields.
`exported['qr014_episode_fields']` contains its Episode field names; a future
consumer constructs its own `EntryProposal(**fields['proposal'])`, then its own
Episode using that object in place of the proposal dict. No QR module import is
performed here. Exact values remain Fraction internally and terminating decimal
text for QR014; target division/12dp HALF_EVEN remains the QR014 consumer's job.

`accepted_export_ref` deliberately remains null, with
`PROTOTYPE_NOT_RELEASED_OR_TRAINING_APPROVED`. Local `label_status='valid'` means
the checks above succeeded for that small supplied prefix; it is not a release,
real-data completeness certificate or permission to assemble a training matrix.

Concrete public calling sequence:

```python
from research.qd010.economic_inputs import FrozenInputs
from research.qd010.joint_native_bridge import JointNativeBridge, NativeInputs
from research.qd010.episode_export import export_episode

# Caller supplies actual Ledger, frozen records and closed native prepared input.
bridge = JointNativeBridge(ledger)  # Default refuses a reference-import ledger.
decision = bridge.decide(decision_us, frozen_inputs, native_inputs)
staged = bridge.opportunity(fill_us, frozen_inputs)
# Requires the registered controlled-port request; not invented by this example.
receipt = bridge.commit_bound_transaction(staged, bound_generated_request)
```

The runnable small synthetic examples are the new test methods, in particular
`test_real_ledger_commit_and_mature_episode_export` and
`test_joint_native_signals_allocation_and_timing`. The former exercises real
small reference-import financial transactions and a real native BTC close plan;
the latter exercises real joint native entry allocation/timing. They are separate
finite component examples, **not one continuous accepted BTC/ETH market replay**.
The exact test commands actually used are below; do not automatically rerun them.

## Actual checks, failures and resource evidence

Only new connection tests ran, with socket connections blocked. Old test-module
constructors were loaded to build literal records; no old test/oracle Ledger,
S07.02, 90/118 suite, growth benchmark, raw query, real label or fit was executed.

| Execution | Result | Wall s | User / system CPU s | Observed max RSS bytes |
| --- | --- | ---: | ---: | ---: |
| Initial one group, 13 methods | 12 PASS, 1 ERROR | 1.22 | 0.46 / 0.19 | 124715008 |
| Failed episode method after constructor repair | 1 PASS | 0.91 | 0.50 / 0.18 | 124715008 |
| New input-isolation defect and affected capacity paths, 4 named methods | 4 PASS | 0.71 | 0.40 / 0.12 | 124174336 |

First failure was `ALLOCATION_ID_MISMATCH`: the **new** fixture factory changed
scenario from its constructor template to P0 without rebuilding scenario-bound
allocation IDs. Only the new test factory was corrected; neither financial
expected values nor old source/oracle changed. That failed evidence is retained.
During new-code inspection another defect was found: missing joint covariance/
unrelated execution-open could suppress a healthy asset's capital-independent
exit. Only the new adapter and focused tests were corrected. This justified the
last named check; the whole group was not repeated.

Across three short processes: 18 method executions, 14 distinct new scenarios;
each has a PASS observation in the scoped sequence above, not a final full-suite
run. The bounded synthetic inputs total 51 financial records across 9 tiny stores,
maximum 11/store. Literal checks include U=+100-60=40, E=10039.85, shared budget
9998.66991, 60+60 against 100/120 budget in both orderings, partial/zero per-coin
capacity, full-request failure before capacity, unknown funding and actual native
ETH forced exit with unknown finance/missing joint data. Real ledger episode net
is 9.8425 on 100 entry notional; a late .005 fee correction invalidates prior
finality then yields 9.8375 after the current assertion clock. No research return
claim follows from these synthetic amounts.

`/usr/bin/time -l` supplied the resource numbers. Summed wall 2.84s, CPU 1.85s;
highest RSS ~118.94 MiB, below the 256 MiB observation budget. All new preserved
evidence at the final snapshot totals **1,829,856 bytes**, 203 files, below 8 MiB.
These are observed process maxima and retained output, not OS hard RSS/disk or
instantaneous filesystem peak guarantees. No new supervisor framework was built.

Exact commands (cwd above; stdout/stderr plus time stats redirected to the named
files beneath `research/.data/qd010/tmp/`; exclusive shell redirection):

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest discover -s tests -p test_qd010_joint_native_bridge.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd010_joint_native_bridge.ConnectionTests.test_real_ledger_commit_and_mature_episode_export -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /usr/bin/time -l /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m unittest test_qd010_joint_native_bridge.ConnectionTests.test_covariance_rejected_before_native_fillna test_qd010_joint_native_bridge.ConnectionTests.test_missing_covariance_and_other_asset_open_preserve_native_exit test_qd010_joint_native_bridge.ConnectionTests.test_partial_zero_fill_and_residual_cancellation test_qd010_joint_native_bridge.ConnectionTests.test_zero_eth_capacity_does_not_use_btc_capacity -v
```

Logs: `connection-run-1.log`, `connection-failed-item-2.log`,
`connection-input-isolation-3.log`. Only the new `synthetic-*` subdirectories were
inspected for sizes/counts. Git whitespace checks passed; five-file staged scope
is checked before committing. No full-suite/integration validation was performed.

## Concrete remaining dependencies: no market/label/training readiness

1. **Registered controlled native port:** QD009 `_invoke` runs registered
   `validate_input/validate_state/evaluate/validate_output` ports with frozen fact/
   ledger selectors and typed state. No such joint native feature/covariance/
   order-intent/state codec definition is registered by this prototype. Actual
   generated decisions/orders/order_transitions/reserve_dependencies and their
   witnesses must be connected to these methods, including scenario phase order.
   Default `commit_bound_transaction` refuses absent generated witnesses.
2. **Execution phase versus sealed reads:** public `as_known` reads already
   admitted cutoffs; an external reader cannot read a new fill-time prefix then
   append new same-time origins behind a sealed frontier. Actual continuous
   execution must call the connection inside the controlled slot transaction.
   The synthetic import demonstration is not a workaround for that constraint;
   pre-recorded future fills are not a valid production/generated source binding.
3. **Atomic native feedback/persistence:** exact delivered cash D, actual native
   session bits S, R01 sign/full-state/rounding guards, saved actual-close feedback
   feature, delayed completion, duplicate completion suppression and their atomic
   publication with ledger orders/cancellations/reserves remain unbound. ETH
   financial commit stops explicitly before further policy use. In-memory order
   reservations/timing/reentry metadata are not restart-safe or a registered
   checkpoint state. Financial-batch atomicity alone is not whole-adapter atomicity.
4. **Real input evidence:** no real frozen MARK/funding/OHLCV query coverage,
   cadence, fact-schema normalization/source catalogue or generated economic body
   binding was verified/generated here. `funding_terms` returns exact local terms,
   not an automatically accepted FinancialBody. Full raw qualification and typed
   controlled facts must arrive through separately approved scopes.
5. **Export release:** native intent receipts are research-local producer
   evidence, not yet registered/persisted controlled-registry records. Full scoped
   acceptance, terminal/censoring provenance, state/code/input manifests and the
   accepted exporter identity must be supplied before QR014 assembly can accept
   real samples. No sample count/statistical sufficiency or heldout result exists.
   Public component materialization is deliberately capped at 512 items; exceeding
   it is an explicit prototype gap, not truncation or a claim of replay scalability.

The old repaired ledger's general suite remains incomplete and S07.02 assertions
UNKNOWN. These tiny direct API calls do not upgrade it to globally PASS. No known
budget is claimed to guarantee that future real replay or S07.02 can finish.

Recommended next step: coordinator chooses a separately bounded **implementation**
scope for the registered joint native port/atomic feedback state, using these
components. No QR re-review or next task was dispatched by this agent. Any actual
market replay/real-label validation requires a concrete resource/window request
and human approval; training requires its own explicit confirmation. Stop here.

## Exact code identities

The resulting five-file commit is provided with the handoff. Source hashes:

| New file | SHA256 |
| --- | --- |
| joint_native_bridge.py | `c9a585429abb7e0f89ecd3754dba61abc739a0a92860f7d6a6aa617c00dacb33` |
| economic_inputs.py | `440611367c847942b42c46450233b5e608648723d9fcbdc651f4d89ee9450bf1` |
| episode_export.py | `70c25b8890901e1aebf79bdbc203fb02d26ade78c38bdb2cda0f10bb2fde153e` |
| new tests | `1b1351aad1c670fc96c0326c320daeae7a1a84b010f52c67ced81467ff234c92` |

Real unchanged core identities used: streaming ledger
`251b7e9ead45b66972680dc5594d4e80fabc88e9bdd613fc522e3d79569b16fb`, r3
`7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`;
native signal `aa3b9e71512008ff43f49639d8d2cf113e81def7ab031e41676453def86e78dc`,
portfolio `1837e2601c2255515644394b6934f45a933d11c758f93aafae926d9bb120397d`,
execution `e1eaa17ea1292c7e906d4634b274fe72f2a415dfa409054674a33c22b9b1f5bb`,
timing `41d4593eaf345cdc8d26759605651e3e7bcfcb679604416b29fef80b821d9344`,
config `29eed6a35c7ecb8b079b21616754c49774fa0bb9034dbba3fc2112734c968709`.
