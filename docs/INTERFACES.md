# Shared interfaces v1

**Coordination status (2026-10-27):** this additive envelope specification and
`src/contracts.py` were supplied by the concurrent QD setup chat and preserved.
Treat envelope v1 as a tested **proposal for collaboration**, pending counterpart
review and user integration approval. Its presence is not approval to migrate
runtime producers/consumers. Existing native interfaces remain the compatibility
baseline, also guarded by `tests/test_interface_contracts.py` (registry 1.0.0).
CR-001/CR-002 cover future adapter adoption and policy enforcement, not permission
to alter current execution. QD is the exclusive shared-schema file editor;
QR owns feature/prediction/model semantics and reviews those schema changes.

## Status, ownership and compatibility

Eight interface areas, nine payload kinds (backtesting has request and result).
`src/contracts.py:SCHEMAS` is the exact required-field/type definition;
`validate_contract(kind, payload)` enforces per-record constraints and
`validate_exchange(features, prediction, model, decision_at)` checks one inference
exchange. Valid examples and rejection cases are executable in
`tests/test_shared_contracts.py:examples`. No extra validation dependency is needed.

**Established here:** a standalone, versioned collaboration proposal and tests.
**Pending:** production adapters and calls to validation. Existing DataFrames,
dataclasses, API/job JSON, legacy result schema 3, feature version 1 and model
bundles remain as they were. Do not send a v1 record directly to a legacy API or
describe current producers as already conforming. Backtest dates below use
half-open intervals; a future adapter must explicitly translate existing inclusive
bar filters and include the preceding closed bar when required.

| Area / kind | Designated owner | Producer → consumer / legacy mapping | Contract tests |
| --- | --- | --- | --- |
| Market data / `market_data` | QD | exchange/data_fetcher → QR features, backtest; legacy timestamp/OHLCV frame + contract metadata | OHLC, closed bars, future funding, units, scope |
| Features / `features` | QR semantics; QD shared-file writer | causal_features/prepare_features → model; legacy ordered feature frame | ordered values/units, availability, unavailable/null; existing ML prefix/gap tests |
| Predictions / `prediction` | QR semantics; QD shared-file writer | crypto_ml → shared entry policy; legacy status/short/long dict | class fractions, sum, identity, exclusive expiry |
| Model metadata / `model_metadata` | QR semantics; QD shared-file writer | offline exporter → inference loader; new sidecar, legacy bundle unchanged | provenance shape, class order, embargo, artifact/scope association |
| Trading signals / `signal` | QD; QR review | InstrumentSignal/allocation → execution; legacy InstrumentTarget lacks times | signed USDT, decision availability, exit target zero |
| Strategy configuration / `strategy_config` | QD; QR review | ConfigStore snapshot → research/runtime adapter | paper mode, configuration identity, bound request snapshots |
| Backtesting / `backtest_request`, `backtest_result` | QD; QR validation review | controller/replay → reports/QR; legacy result percent fields require conversion | coverage policy, cost units, equity identity, legacy version separation |
| Risk limits / `risk_limits` | QD; QR review | risk/budget snapshot → execution/QR | cross verification required, stale snapshot, entry/exit independence |

QD alone edits contracts.py, this document and shared contract tests. QR edits its
owned implementations and submits contract change requests. Both roles must
approve changes as described in AGENT_COLLABORATION.md. These setup contracts are
not permission to change risk policy or activate a model.

## Common conventions

- Every record includes `kind`, integer `schema_version: 1`, and `created_at`.
  Unknown versions, kinds, extra fields and missing fields are rejected. Use a
  new negotiated schema for additions; do not silently mutate v1.
- All times are finite, nonnegative **UTC Unix seconds**, never local time or
  milliseconds. `created_at` is record emission time on the replay clock or real
  clock, declared by the experiment; never relabel a retrospective export as an
  actually deployed historical artifact. Validity ends are exclusive.
- `instrument_id`: `gate:usdt:ETH_USDT` (exchange:settlement:canonical contract).
  v1 supports Gate USDT linear perpetuals only. A ticker alone is ambiguous.
  Broader venues/settlements require coordinated scope/version changes.
- Price: USDT per base unit. `quanto_multiplier`: base units per contract.
  Volume has explicit `volume_unit` of contracts/base/quote; an adapter must
  establish raw SDK volume semantics rather than guessing. Notional, equity,
  fees and PnL: USDT. Signed targets: positive long, negative short.
- `_fraction` means ratio (0.08 = 8%); `_bps` means basis points (2 = 0.0002).
  Gross exposure/equity and leverage are multiples, not percentages. Legacy
  `_pct` result fields require division by 100.
- All JSON numbers must be finite; booleans are not numeric values. Unavailable
  feature/prediction values are null with `status: unavailable` and a reason,
  never zeros standing in for missing predictions. Unknown result metrics are
  outside this minimal success-summary schema; do not fabricate values.
- SHA256 fields are lowercase 64-character hashes. `data_sha256` identifies a
  canonical immutable manifest of source snapshots, coverage and their hashes;
  `artifact_sha256` identifies exact model bytes. `config_sha256` identifies
  canonical JSON of the effective parameters/cost/risk/version snapshot,
  excluding the hash itself and volatile envelope times. Adapters must define
  canonical serialization (sorted keys, compact separators, UTF-8, finite JSON),
  compute/verify content and persist the manifests. Shape checks alone do not
  prove a hash matches data.

## Payload semantics

### Market data

Required OHLCV, interval, instrument, open/close/availability times, multiplier,
source and data hash describe one closed bar. `bar_close_ts = bar_open_ts +
interval_seconds <= available_at <= created_at`. Interval is a positive integer
in seconds. A feature consumer additionally checks actual staleness, sorted
unique timestamps, requested coverage and contiguous bars; one record cannot
prove a complete series. Missing bars are not interpolated for research.

`funding` is null or exactly `{settlement_at, available_at, rate,
interval_seconds}`. `rate` is the signed decimal fraction per settlement;
positive means long pays/short receives. Its availability must follow settlement
and precede the market snapshot availability. It is settled history, not a
future rate retrospectively known. Funding costs may be approximated only when
explicitly declared in backtest costs/warnings; never feed future settled rates
into Carry. Candle timestamps refer to bar opens in the legacy frame.

### Features

`feature_set_id`, `feature_version`, ordered unique `names`, equally sized
`units`/`values`, instrument, interval and `bar_open_ts` identify the vector.
Names and order must match model metadata, and each unit must be explicit.
`bar_open_ts + interval <= max_source_available_at <= as_of <= available_at
<= created_at`; a consumer may use it only after availability. `as_of` is the
source information cutoff, not an assurance that a feed had zero delay.

For the current crypto-hourly feature set, all 21 existing FEATURE_NAMES are
dimensionless, interval is 3600 seconds, and feature version is 1. After a gap,
the existing causal implementation restarts the 168-hour lookback; do not fill
missing vectors or normalize with the whole sample. `unavailable` requires null
values and a reason. The general vector validator allows other explicitly
versioned feature sets; inference exchange v1 is scoped to current hourly ML.

### Predictions

Bind instrument, model ID/hash, feature identity, `as_of`, `available_at`,
exclusive `valid_until` and `horizon_seconds`. `probabilities` is exactly
`{short, neutral, long}`, each in [0,1], sum within 1e-8 of one, or null when
unavailable. They describe the model's three-class label, not a guaranteed profit
probability. Consumers require feature/model identity and
`feature.available_at <= prediction.available_at <= decision_at < valid_until`
within the model window. Invalid/expired ML blocks fresh entries only; existing
positions retain their normal exits. Local validation does not place orders.

### Model metadata

Record model ID, exact artifact hash, `bundle_schema_version: 1`, model kind,
supported instruments, hourly interval, feature identity/order, class order
`[-1,0,1]`, last training-label `trained_until`, validity window, embargo, label
horizon, next-bar-open entry, round-trip costs/edge fractions, training data hash,
code revision, package versions, seed, validation manifest and activation state.
`trained_until < valid_from < valid_until` and `trained_until + embargo_seconds
<= valid_from`. Every fold needs its own manifest. Adjacent model windows must
not overlap; the multi-model adapter must check the full sequence.

`validation` is a versioned experiment manifest reference/content containing
protocol, development/validation/evaluation windows, data coverage, metrics and
limitations. Its experiment-specific content is reviewed by QR; v1 only checks
it is nonempty finite JSON. Embargo length must be declared, not silently inferred
from the four-hour label. The current exporter does not itself enforce the
documented external 24-hour embargo; v1 adds a boundary check.

`activation` is research or paper_approved. It is descriptive metadata, never
live authorization. A model sidecar and its hash must be reviewed before any
adapter consumes it. Actual bytes, tree shapes, package parity, unseen-sample
validation and promotion approval need additional checks. Existing load_bundle
checks remain; a shape-valid manifest does not imply a safe or useful model.

### Trading signals

`strategy_id`, `config_sha256`, `risk_limits_id`, instrument, decision/source
times, expiry, reason and signed `target_notional_usdt` define a target. Action
is target, hold or exit; exit requires zero target. This is a model decision,
not a fill/order, contract count, leveraged PnL or implicit execution permission.
Fixed-margin execution may translate model targets using the existing sizing
book. Legacy Signal and InstrumentSignal are not interchangeable with this DTO.

### Strategy configuration

Identity, paper mode, instruments, `effective_at`, parameters, sizing mode,
optional model ID (empty string disables ML), risk ID and hash form an immutable
snapshot. Parameters use the existing ConfigStore/SystematicConfig meanings,
not a second set of numerical defaults. Effective time cannot precede snapshot
creation. Validation does not load config.yaml or change current runtime mode.

### Backtesting

Requests require request ID, exact instruments, half-open `[start_ts, end_ts)`,
initial USDT equity, data/config/code identities, nested validated strategy/risk
snapshots, costs and completeness policy. Costs are exactly
`{taker_fee_fraction, slippage_bps, funding_policy}`: fee and slippage are **per
side**, funding policy is an explicit method/source label. A snapshot hash must
also include these cost assumptions. Asset lists and config/risk IDs must agree.
Pre-window warmup is allowed; scored trades must fall in the evaluation interval.
Adapters must bind snapshots to the requested simulation period and keep risk
budgets fresh at each decision, rather than reusing a single initial budget.

Success results bind the same request/data/config/code identities, requested and
accepted instruments, actual evaluated interval, equity, return/drawdown
fractions, fees, signed funding paid, completed-position and execution counts,
warnings and legacy result schema version. Positive funding_paid means expense;
negative means received. `return_fraction = final/initial - 1`; drawdown can
exceed one in an insolvent approximation. Counts distinguish fills/adds/reduces
from completed positions. A result with no accepted instruments is an error,
not a success summary. Failure transport remains a future adapter concern.

`strict` requires full asset/period/continuity coverage or adapter rejection.
`replay_with_warnings` permits explicitly recorded omissions for historical
diagnosis. Local validation checks asset coverage; series/time completeness,
matching result to request, fill accounting and hash verification are adapter
responsibilities. Never silently promote a warned replay into strict research.
Full cross-margin liquidation and historical tiers remain unresolved regardless
of schema validity. Legacy results are read compatibly, not rewritten.

### Risk limits

Record risk ID, effective/expiry times, cross-margin policy, gross/instrument
notional-to-equity caps, single-order USDT cap, leverage multiple, daily-loss
enable/fraction, and independent allow_increase/allow_reduce. Snapshot must be
current at emission; a consumer also rechecks expiry at decision time and fetches
fresh actual equity, available margin, contract tiers, ownership and verified
cross state. A `require_verified_cross` flag is a requirement, not verification.

v1 requires cross verification and keeps reductions allowed even when increases
are blocked. Limits are declared constraints, not new defaults: current fixed
tickets and old volatility sizing have different enforcement (see audit).
An adapter must reject unsupported caps rather than pretend they are enforced.
No validator call enables live trading, changes leverage or re-enables the
currently disabled daily-loss gate.

## Required coordination and tests

Any field, unit, availability, class order, label or completeness change requires
a written contract request, explicit owner/reviewer approval and producer/consumer
acceptance tests before integration. Existing tests remain required alongside
the new suite: ML prefix/future perturbation and gap reset, execution parity and
exit precedence, position sizing, history gaps, strict JSON and report accounting.
Missing exporter holdout parity, full-window coverage and runtime adapter tests
are tracked on ROADMAP.md; this setup does not claim they now exist.

## Native compatibility contract tests

`tests/test_interface_contracts.py` freezes the current native boundary in eight
tests alongside the proposed envelope rejection tests. Owner means semantic
owner; QD is the editor of this shared test file and QR reviews changes.

| Native boundary | Owner | Test / existing additional coverage |
|---|---|---|
| Candle frame and open/close availability | QD | `test_market_data_open_time_and_closed_bar_boundary`; history-gap tests |
| Exact 21-feature order/version and training availability | QR | `test_feature_order_version_and_availability`; ML prefix/gap/label tests |
| Probability classes and half-open model window | QR | `test_prediction_probabilities_and_half_open_window`; stale/intrahour/exit tests |
| InstrumentSignal/InstrumentTarget and signed USDT-to-contract conversion | QR semantics, QD execution | `test_signal_and_target_signed_units`; order invariants/parity tests |
| Existing JSON bundle feature identity and training cutoff | QR | `test_model_metadata_rejects_future_training_and_wrong_version`; malformed-bundle tests |
| PAPER/config defaults and supported ML interval | QD | `test_configuration_defaults_and_ml_interval_guard`; risk/config propagation tests |
| Python backtest inputs, result schema 3 and JSON behavior | QD | `test_backtest_schema_request_and_strict_json_result`; reporting/web/parity tests |
| Disabled default loss gate, percentage units and elapsed 24h window | QD | `test_risk_limit_units_defaults_and_window`; cross verification and exit-priority tests |

Native dataclasses/frames have no new envelope fields. Symbol, interval, decision
time and artifact context must remain associated by the caller. Missing observed
ingestion timestamps cannot be reconstructed by assigning ideal bar-close times.
Hourly volatility features are standard deviations of hourly log returns, not
annualized volatility; native OHLC feature `_pct` names are ratios, while result
and configuration `_pct` fields are percentage points. Native order-plan quantities
are positive contracts with side specified separately; adapters handle exchange
sign conventions. Do not confuse the native result schema 3, feature version 1,
native registry 1.0.0 and proposed envelope schema 1.
