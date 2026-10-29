# QF-QR-002 specification handoff

Task-ID: QF-QR-002-SPEC
Dispatch-ID: QF-DISPATCH-20261027-QR-SPEC-1
State: READY_FOR_QD
Spec-Revision: r1
Date: 2026-10-27 (Australia/Melbourne)
Role: QR semantic reviewer
Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`
Branch: `codex/qr-validation-baseline`
Baseline: `fea901bba10d9c70d233a0ec008a7b4e044503a6`
Common source snapshot: `475aaeaa5b9365b360563294e183d912c382b570`

## Completed work and file ownership

Read AGENTS and collaboration/architecture/interface/roadmap/progress/decision
documents, current model exporter/calibration/inference, QR-001 evidence and the
coordinator's read-only state. Branch was clean at fea901b. No nested AGENTS was
found in tracked/nonignored project files. The existing model and negative trading
conclusion are preserved.

Only this report and `docs/interface-requests/qr-qf002.md` are changed. The latter
is the normative finite r1 specification. QD is assigned exclusive implementation
of new `src/model_artifact_validation.py`,
`tests/test_qd_model_artifact_validation.py` and its implementation report. QR
owns these two documents and later semantic review. Original main, the QD cache
worktree, shared journals, code, data and coordinator state are unchanged by QR.

The proposed tool reads three explicit files, validates exact artifact/sidecar/
data-manifest byte hashes, checks declared scope/features/units/classes and
label/timing policy, validates native model shapes and selects exactly one active
window at an explicitly supplied time. No CLI or default-runtime integration is
needed. Its successful status is `consistent`, never model approval.

## Acceptance and compatibility decisions

The spec defines seven positive groups and 25 rejection groups with deterministic
synthetic examples. Cases cover both native model kinds, folded calibration,
actual-byte mutations, missing evidence, label/cost units, both strict 24h
embargo boundaries, expiry/gaps/adjacent windows, corrupt trees and mismatched
scope/order. Unknown data provenance is exposed in mandatory `unverified` fields;
missing required declarations fail. Source hashes do not prove training lineage.

Verified from existing code: QR-001 temperature scaling is folded into supported
logistic/GBT parameters. Native inference can read that representation. New
calibrator kinds or a separate runtime calibration layer are unsupported and must
be rejected. The validator cannot infer or prove folded calibration from weights
alone, so transformation provenance remains explicitly unverified. This prevents
both falsely claiming full calibration verification and incorrectly rejecting all
already representable folded artifacts as a format problem.

The local offline profile is not a modification to native registry 1.0.0,
contracts v1, feature version 1, strategy/risk defaults or runtime callers. Its
strict embargo comparison matches QR-001; the existing shared envelope minimum
gap rule is not changed. Runtime migration/activation would be a separate approval
item. The coordinator's dispatch permits this isolated reviewable candidate only.

## Checks performed and results

- Git branch/status/log and applicable file ownership were inspected read-only.
- In-memory synthetic logistic and one-leaf GBT fixtures were passed to the
  existing `src.crypto_ml.predict_probabilities`, with bytecode writes disabled.
  For each kind, raw probabilities were [.2,.3,.5]; parameters folded at T=2
  produced [.2627510660959602,.32180302065369965,.4154459132503401]. All four
  `numpy.testing.assert_allclose` checks passed at rtol/atol 1e-12.
- This verifies fixture compatibility only. No new validator exists yet and no
  proposed rejection case is represented as an implementation test already passed.
- Documentation formatting, exact changed-path allowlist and preservation of
  all fea901b tracked files are checked before committing. The previous 160-test
  research result remains historical evidence; the suite is not rerun for these
  two documentation-only changes.

## Limitations, dependencies and next step

The spec deliberately does not certify raw dataset bytes, actual label extrema,
training execution, physical volume units, historical arrival time, temperature
derivation or model quality. It rejects missing mandatory stage evidence and
reports remaining unverifiable conditions. The QR-001 historic bundle needs an
explicit truthful sidecar before this tool could check it; no adapter is fabricated
in this task. No retraining or search for a favorable result occurred.

Dependency: QD must accept r1 or record any proposed changes, implement in its
assigned worktree after the current cache task, run the defined acceptance cases
and report exact commits. The coordinator then assigns those commits to QR for
independent review. READY_FOR_QD means the specification is actionable; it does
not mean QD implementation, runtime integration or model activation is approved.
No cross-chat reply or polling is required from QR. No merge, push, service,
credentials, engine or NAS operation was performed.
