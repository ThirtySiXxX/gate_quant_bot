# QF-QR-002: explicit offline artifact consistency validator

Task-ID: QF-QR-002-SPEC
Dispatch-ID: QF-DISPATCH-20261027-QR-SPEC-1
State: READY_FOR_QD
Spec-Revision: r1
Date: 2026-10-27 (Australia/Melbourne)
QR baseline: `fea901bba10d9c70d233a0ec008a7b4e044503a6`
Common source baseline: `475aaeaa5b9365b360563294e183d912c382b570`

## 1. Scope, ownership and compatibility

Build one explicitly invoked, read-only Python utility. QD exclusively owns new
`src/model_artifact_validation.py`, `tests/test_qd_model_artifact_validation.py`
and `docs/agent-reports/qd/QF-QD-002-implementation.md`. QR owns this specification
and its QR reports and reviews the exact resulting QD commit. No CLI, service,
training pipeline, backtest refactor or dependency installation is required.

This is a finite prototype on an independent feature branch. The function and
local manifest profile below are proposed for this prototype only; they are not
additions to native registry 1.0.0 or `contracts.py` envelope schema 1. Do not edit
`crypto_ml.py`, shared schemas/tests, configuration, risk settings or shared
journals. No existing caller imports or invokes this module by default. Reading
existing feature constants is allowed. The coordinator allocates implementation
after QD's current cache work; QR does not edit that worktree.

QR-001's negative trading decision remains in force. A successful consistency
report neither approves a model nor establishes predictive quality. Runtime
adoption, schema migration and model activation are separate proposals requiring
their own review/approval; they do not block this offline implementation.

## 2. Function and evidence boundary

Proposed public API:

```python
validate_artifact(
    artifact_path, manifest_path, data_manifest_path, *,
    expected_manifest_sha256, instrument_id, decision_at
) -> dict
```

The caller supplies three explicit local paths and a separately recorded expected
SHA256 of the sidecar manifest. Do not discover files, follow paths inside JSON,
download data, read app configuration, infer wall-clock time, mutate inputs or
write outputs. Read each file once into bounded bytes (artifact <=20,000,000 bytes,
each manifest <=2,000,000 bytes), then hash and parse those same bytes. Subsequent
disk changes are outside the report; it describes the bytes actually read.

Compare raw SHA256 of the sidecar against `expected_manifest_sha256`, raw artifact
bytes against sidecar `artifact_sha256`, and raw data-manifest bytes against
`data_manifest_bytes_sha256`. Never reserialize JSON before these comparisons.
These byte hashes are deliberately distinct from `contracts.py`'s canonical
`data_sha256` convention. No self-referential hash is embedded in the sidecar.
SHA256 pins identity; it does not authenticate the author or prove training ran.

Return only after all required checks pass, with at least these exact keys:

```python
{
    "status": "consistent",
    "profile": "qf002-offline-v1",
    "activation_authorized": False,
    "instrument_id": instrument_id,
    "decision_at": decision_at,
    "active_model_index": 0,  # actual selected index
    "verified_hashes": {
        "artifact_sha256": "...",
        "manifest_sha256": "...",
        "data_manifest_bytes_sha256": "..."
    },
    "declared_conditions_checked": ["scope", "features", "classes", "label_policy", "stage_times", "windows"],
    "unverified": ["raw_dataset_bytes", "training_execution", "actual_label_extrema",
                   "physical_volume_unit", "historical_arrival_times", "predictive_quality"]
}
```

For any folded calibration add `calibration_transform` to `unverified`: without
the base artifact/training evidence this tool cannot prove that the final weights
were derived using the declared temperature. Metadata consistency is not a proof
of absence of leakage. Do not return `verified`, `safe`, `approved` or an empty
uncertainty list. Missing required stage/scope/unit declarations cause rejection,
not a successful result with invented values. Unsupported inputs are rejected.

On failure raise `ArtifactValidationError(ValueError)` with a stable `.code` and
concise field/index detail, never raw file contents. Codes used below are the
acceptance contract; exact prose is not. No partial-success return on failure.

## 3. Local sidecar profile (all fields required)

Top-level keys are exactly the following. `F` is the ordered feature list below.
The display uses Python notation; files use strict JSON.

```python
{
  "profile": "qf002-offline-v1",
  "artifact_sha256": "<lowercase 64 hex>",
  "data_manifest_bytes_sha256": "<lowercase 64 hex>",
  "instrument_ids": ["gate:usdt:ETH_USDT"],
  "time_unit": "unix_seconds_utc",
  "interval_seconds": 3600,
  "feature_version": 1,
  "feature_names": F,
  "feature_units": ["dimensionless"] * 21,
  "classes": [-1, 0, 1],
  "label_policy": {
    "id": "crypto-hourly-next-open-4h-v1",
    "entry": "next_bar_open",
    "horizon_seconds": 14400,
    "return_unit": "fraction",
    "round_trip_cost_fraction": 0.0014,
    "edge_fraction": 0.001
  },
  "folds": [{
    "model_index": 0,
    "fit": {"first_feature_at": 1728000000, "last_label_end": 1728360000},
    "calibration": {"method": "none"},
    "embargo_seconds": 86400,
    "valid_from": 1728630000,
    "valid_until": 1728716400
  }]
}
```

`F`, exactly 21 entries:

```python
[
 "return_1h", "return_4h", "return_12h", "return_24h", "return_72h", "return_168h",
 "volatility_6h", "volatility_24h", "volatility_72h",
 "volume_relative_6h", "volume_relative_24h", "volume_relative_168h",
 "range_pct", "body_pct", "upper_wick_pct", "lower_wick_pct", "efficiency_24h",
 "hour_sin", "hour_cos", "weekday_sin", "weekday_cos"
]
```

Reject unknown/missing profile, sidecar, fold, stage or label-policy fields.
Only `none` and the following calibration object are supported in r1:

```python
{"method": "temperature_folded", "temperature": 2.0,
 "first_feature_at": 1728450000, "last_label_end": 1728540000}
```

Folded temperature is finite and in [.25,4]. No embedded isotonic/sigmoid model,
external calibrator or new `kind: calibrated_*` is supported. `none` means an
explicit uncalibrated declaration, not absence of evidence interpreted as none.
The existing native format can represent folded temperature: QR-001 divides
logistic coefficients/intercepts or GBT initial_raw/learning_rate by T. Its
existence does not let this validator infer T or calibration times from weights.

All JSON must be strict UTF-8 objects with no duplicate keys or nonfinite numbers,
including overflow such as 1e999. No pickle or dynamic deserialization. Booleans
are not numbers; integer fields require actual JSON integers. Timestamps may be
integer or integer-valued float Unix seconds, finite and nonnegative, at most
253402300799 (the supported year-9999 bound); never silently convert milliseconds.
Explicit unit declarations are still not independent proof of source units.
Hashes must be lowercase 64-hex strings. Lists described as unique must be unique.

## 4. Required cross-checks

### Identity, scope and data manifest

- Sidecar feature version/order and class order must exactly match the native
  artifact and current feature version 1/F/[-1,0,1]. Units are exactly 21
  `dimensionless` strings; output `_pct` features are fractions. No feature
  reordering, case normalization or unit conversion is performed.
- Instrument IDs form a nonempty unique list matching
  `gate:usdt:[A-Z0-9]+_USDT`. Caller instrument must match one exactly. No bare
  ticker inference in the caller or sidecar, and no wildcard scope.
- The third file uses the existing QR data-manifest shape: JSON object with
  `schema_version: 1` and nonempty `files` list of objects with string roles.
  Other top-level fields are opaque evidence and allowed. Select entries with
  `role: classification` only.
  Each selected entry needs unique nonempty `file`, unique canonical `symbol`
  matching `[A-Z0-9]+_USDT`, `interval_seconds: 3600`, and a well-formed `sha256`.
  Their symbol set, prefixed with `gate:usdt:`, must equal sidecar scope. Other
  roles are not used to enlarge scope. Do not open any referenced file.
  This verifies the data manifest's bytes and declared scope, not its CSV hashes,
  coverage, samples, volume units, or whether those bytes were used in training.

### Label policy and stage timing

- r1 supports only the exact label-policy object in section 3. It denotes simple
  return from the next hourly open to the open four hours later; up if return
  > .0024, down if return < -.0024, neutral otherwise. Cost .0014 is a total
  round-trip fraction and edge .001 is a fraction. Do not confuse these with
  per-side fees, basis points, runtime slippage or realized strategy PnL. Other
  horizons, costs, units, policies or inferred defaults are unsupported in r1.
- Require one sidecar fold per artifact model, indices exactly 0..N-1 in order.
  Validate every fold, even those not active at decision time. Sidecar validity
  times must equal the corresponding native model times exactly.
- For every fit or calibration stage, `first_feature_at + 14400 <= last_label_end`.
  Embargo is explicitly 86400 for this prototype; shorter/different policies
  require a new reviewed profile. For `none`, native `trained_until` must equal
  fit.last_label_end and `fit.last_label_end + 86400 < valid_from`.
- For folded calibration require
  `fit.last_label_end + 86400 < calibration.first_feature_at` and
  `calibration.last_label_end + 86400 < valid_from`. Native `trained_until` equals
  calibration.last_label_end, not the earlier fit label. These strict inequalities
  preserve QR-001's experiment convention: equality is rejected. This is a
  narrower offline policy than envelope v1's non-strict minimum-gap check, not
  a modification to that shared contract.
- Require `trained_until < valid_from < valid_until`. Artifact windows must be
  ordered and nonoverlapping (`previous.valid_until <= next.valid_from`). Gaps
  are permitted, but exactly one model must cover the supplied decision timestamp
  under `[valid_from, valid_until)`. No nearest-window fallback. At an adjacent
  boundary choose the new window; at the last expiry or inside a gap reject.
  Earlier expired folds and later folds are allowed in a retrospective bundle;
  do not incorrectly compare every inactive fold's training time to decision_at.

### Native artifact structure

Native bundle keys are exactly `feature_version`, `feature_names`, `classes`,
`models`. Models share `kind`, `trained_until`, `valid_from`, `valid_until`,
`train_rows` (positive integer). Kind is logistic or gradient_boosting only.
Allow only their existing fields below; other payload kinds require review.

- Logistic: finite mean/scale vectors length 21, strictly positive scales, finite
  coef matrix 3x21 and intercept length 3.
- GBT: finite initial_raw length 3, finite positive learning_rate, nonempty trees
  with exactly three class trees per stage. Optional feature_importance, if
  present, is a nonnegative finite vector of length 21; no sum=1 requirement.
  Each tree has exactly left/right/feature/threshold/value arrays of the same
  nonzero length. Child/feature indices are integers, never booleans. From root
  0 all nodes must be reachable without cycles or shared/multiply-parented nodes.
  A leaf has both children -1, feature -2 and finite threshold/value; an internal
  node has two distinct in-range children and feature in [0,20]. Thresholds and
  values are finite. Reject one-sided leaves and disconnected nodes.

Do not trust native load_bundle alone: it currently does not check all these
structures. Static checks must terminate for corrupt trees; no recursive descent
without a visited-node guard. The prototype need not fit models or claim numeric
inference safety for every possible feature input. Tests can use the current
predict_probabilities for independent compatibility evidence on synthetic rows.

## 5. Deterministic acceptance fixtures

QD embeds synthetic fixture builders in its own test file and uses temporary
directories. No training or real dataset is necessary. Serialize fixture bytes
with `json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)`
encoded UTF-8. Compute real expected hashes; do not use fake hashes as successes.
For semantic-negative mutations, recompute the relevant parent hashes so the
case tests its intended rule rather than failing early on byte identity.

Base data manifest: `{"schema_version":1,"files":[{"role":"classification",
"file":"ETH_USDT_1h.csv","symbol":"ETH_USDT","interval_seconds":3600,
"sha256":sha256(b"synthetic data reference only").hexdigest()}]}`. It intentionally
does not supply CSV bytes; `raw_dataset_bytes` must remain unverified.

Base artifact: native header F/version1/classes[-1,0,1], one model with
train_rows=1000, trained_until=1728360000, valid_from=1728630000,
valid_until=1728716400. The train-row count is a synthetic declaration, not a
claim of a real fit. Caller: gate:usdt:ETH_USDT, decision_at=1728630000.

- Logistic model: mean=[0.0]*21, scale=[1.0]*21, coef=zeros(3,21),
  intercept=[ln(.2), ln(.3), ln(.5)].
- GBT model: initial_raw=[ln(.2), ln(.3), ln(.5)], learning_rate=.04,
  one stage containing three separate identical leaf trees:
  `{"left":[-1],"right":[-1],"feature":[-2],"threshold":[-2.0],"value":[0.0]}`.
  Optional feature_importance=[0.0]*21.
- Folded variant of each: use the calibration object in section 3, advance
  trained_until to 1728540000, divide the relevant native raw-score parameters
  by 2. For GBT divide both initial_raw and learning_rate; for logistic divide
  coef/intercept, preserving mean/scale. This representation is supported;
  a new model kind or unapplied separate calibrator is not.

| ID | Input / mutation | Required result |
|---|---|---|
| P01–P02 | Base logistic and base GBT | consistent; active index 0; all three byte hashes equal actual bytes; activation false; mandatory unverified list |
| P03–P04 | Folded logistic and folded GBT | consistent only with complete calibrated timing; calibration_transform explicitly unverified |
| P05 | Native inference on one all-zero 21-feature row for each of the four fixtures | p=[.2,.3,.5] for base; folded p approximately [.2627510660959602,.32180302065369965,.4154459132503401]; tolerance 1e-12; test compatibility, not a training claim |
| P06 | Two adjacent valid windows, corresponding fit times consistent; decision equals second start | index 1; prior expired window is allowed |
| P07 | Call twice with identical files and arguments | identical report, no wall-clock dependency, no input writes or calls to network/config/engine |
| N01 | Missing/unreadable file; oversized file | E_IO; E_SIZE respectively |
| N02 | Append whitespace to artifact without updating sidecar | E_ARTIFACT_HASH despite identical JSON semantics |
| N03 | Append whitespace to sidecar without updating expected hash | E_MANIFEST_HASH |
| N04 | Mutate data-manifest bytes without updating sidecar | E_DATA_MANIFEST_HASH |
| N05 | Invalid JSON, duplicate keys, NaN/Infinity/1e999 | E_JSON; recompute hashes when needed to reach parsing |
| N06 | Missing/wrong profile; unknown sidecar key | E_PROFILE; E_METADATA respectively |
| N07 | Missing calibration/fit/unit/scope/label field; bool numeric; invalid hash text | E_METADATA; no inferred defaults |
| N08 | Caller ETH absent; bare ETH ticker; duplicate scope; data classification set differs | E_SCOPE |
| N09 | Feature swap, missing feature, wrong version, unit percent, class reorder or boolean label | E_FEATURES |
| N10 | Horizon 3600, cost .14, negative cost, per-side/bps wording or nonmatching policy | E_LABEL_POLICY |
| N11 | Fit/calibration stage shorter than label horizon; missing/mismatched native trained_until | E_TIMING or E_METADATA for missing field |
| N12 | fit.last_label_end=cal.first_feature_at-86400 | E_TIMING: equality fails first embargo |
| N13 | cal.last_label_end=valid_from-86400 (native trained_until updated too) | E_TIMING: equality fails second embargo |
| N14 | none: fit.last_label_end=valid_from-86400 (native updated too) | E_TIMING: equality fails uncalibrated embargo |
| N15 | Folded metadata with native trained_until left at base fit time | E_TIMING |
| N16 | Negative/nonfinite/fractional timestamp, explicit millisecond unit or epoch milliseconds beyond bound | E_METADATA or E_JSON for nonfinite parsed JSON |
| N17 | Missing/duplicate/reordered fold index, sidecar/native window mismatch | E_METADATA / E_TIMING respectively |
| N18 | Overlapping/unsorted/reversed windows | E_WINDOW; validate full sequence, including inactive folds |
| N19 | decision=start-1, decision=last_end, or decision inside a gap | E_WINDOW |
| N20 | Unsupported calibration method, T<=0, T outside [.25,4], separate calibrator fields | E_CALIBRATION (unknown generic fields may be E_METADATA) |
| N21 | kind=calibrated_gbt or another unsupported model kind | E_MODEL_STRUCTURE; never silently route through GBT fallback |
| N22 | Logistic wrong coef shape, scale<=0 or bool weight | E_MODEL_STRUCTURE |
| N23 | GBT wrong class-tree count, child out of range, cycle, shared child, orphan node, one-sided leaf, invalid feature or mismatched arrays | E_MODEL_STRUCTURE; terminate promptly |
| N24 | Unsupported data manifest version; missing/duplicate classification symbol/file; malformed source hash | E_METADATA (scope mismatch itself is E_SCOPE) |
| N25 | Run manifest/old QR summary supplied as this new sidecar | E_PROFILE; do not fabricate a sidecar from research filenames |

For P06 construct a second window starting at 1728716400 and ending 24h later,
with a fit stage shifted +24h and calibration none; update trained_until and
manifest model_index=1. Derive gap/overlap cases from this fixture. Tests with
multiple independent defects need not require a single particular error; the
one-defect vectors above should target the stated code.

## 6. Delivery and explicit exclusions

QD reports exact base and resulting commit(s), accepted spec revision, changed
paths, focused and relevant existing offline checks, results, limitations and
any departures needing QR review. Test every acceptance row and meaningful
subcases; test doubles may verify absence of network/config/engine side effects.
Use standard library plus existing runtime dependencies only. Full QR research
data, sklearn fitting and QR-001 reruns are not prerequisites.

The stored QR-001 artifact is native-compatible but does not already carry this
new sidecar. It must not be labeled validated by this tool without supplying
truthful explicit metadata. A retrospective decision_at must be labeled as such
by the caller; it is not evidence of a historically deployed model. Neither
hashes nor positive fixture checks overturn QR-001's rejected-for-promotion status.

Out of scope: raw CSV verification, recomputing label extrema, proof of training
lineage, verifying temperature from a base artifact, historical feed availability,
model quality, prediction execution, activation and runtime adapters. These are
explicitly unverified, not silently certified. Any later runtime adapter must
address richer provenance and authorization in its own review.

Next step: coordinator dispatches r1 to QD after its cache milestone. QR waits for
the exact QD commit range and then writes a separate PASS/REVISE/BLOCKED review.
No main merge, push, real configuration/credentials, engine or NAS operation is
authorized by this specification.
