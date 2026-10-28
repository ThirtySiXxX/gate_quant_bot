# QF-QR-011-MICRO-RECONCILIATION — completed

2026-10-28 · QR · dispatch `QF-DISPATCH-20261028-QR011-MICRO-RECONCILIATION-1`.
Worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`;
branch `codex/qr-validation-baseline`; base
`88168f34c8c2855e9e65510bcde749cc459ff12a`.

## Completed findings

The September 2026 archive/snapshot mismatch is now isolated beyond QR010's
whole-book failures. Adjacent-snapshot differences, which eliminate the initial
seed, still fail for8485/56195 comparable BTC level transitions and8004/55324 ETH
transitions beyond any subunit integer-floor difference. A BTC single-ID example
has net+128 contracts while snapshot quantity stays2258. Initial-state-only,
uniform multiplier, reversed sign and merged-ID-only repairs cannot explain it.
The two fixed older controls give58827/58827 and57541/57541 exact transitions.

Two new complete next-hour archives establish internal boundary continuity:
BTC44,067/44,067 levels match exactly at ID123746036996; ETH's maximum difference
at ID107316992580 is2.908e−11 contracts. The original archive's additive mapping
therefore has strong internal support. This is not independent proof of public,
API-executable liquidity. The mismatch may reflect different liquidity/event
scope or a source snapshot defect; RPI specifically remains unproved.

The first ETH negative quantity is directly attributable to raw decimal text:
1238.3999999999999−1217.1−21.3=−1e−13. The entire raw chain is retained. A bounded
nearest-tenth diagnostic removes negative shadow states, but no historical lot
quantum/producer-error guarantee exists and no normalization is approved. It
cannot repair large snapshot differences. Official legacy integer-response
documentation explains why fractional quantities can be censored; the archived
request header is not retained. Conditional interval bounds and their uncertainty
are produced, with no invented fractional quantities or executable capacity.

**No qualified exact public L2 stream has been recovered.** Standalone indicative
snapshot price/spread and conditional depth-interval research remain possible;
complete exact-string trades remain a separate flow candidate. Microstructure
research is retained. This is a conclusive rejection of the current combined
adapter, not a claim that all microstructure data is unusable.

## Files modified and evidence

Exactly five new, exclusively assigned files:

- `research/qr011/reconcile_microstructure.py`: executable differential, boundary,
  precision and conditional-interval diagnostics with bounded planned acquisition.
- `research/qr011/reconciliation-result.json`: request plan/receipts,33-file evidence
  inventory with hashes, measurements, source pins, test and preservation records.
- `research/qr011/reconciliation-findings.md`: counterexamples, hypothesis
  dispositions, recovery criteria and retained research/data paths.
- `tests/qr_research/test_qr011_micro_reconciliation.py`:8 focused offline fixtures.
- `docs/agent-reports/qr/QF-QR-011-micro-reconciliation.md`: this report.

Raw and derived evidence is only in ignored
`research/.data/qr011/reconciliation/`. QR010's180 original evidence files and
four source pins were hash-verified unchanged, including its manifest
`3476bdab44da4631f600c1b99ba41c96a474f05bb6a303e45a8ad868350b3338`.
The exact initial diagnostic source is retained in
`versions/diagnostic-v1.py`; later CLI additions do not overwrite its results.

Final result manifest SHA256:
`403613fc98461f2137620bb36bfbc89cf7423f51346927390306442861a8dd92`.
Final diagnostic source SHA256:
`8ab9733e6225fb9330deeb588165a6d09244cd02a7993006842b5128840f1987`.

## Actual execution and validation

Completed commands used only the existing Python environment:

```text
reconcile_microstructure.py diagnose --pairs R02:R03,R17:R18,R22:R23,R27:R28
reconcile_microstructure.py plan-neighbor
reconcile_microstructure.py fetch-neighbor
reconcile_microstructure.py boundary
reconcile_microstructure.py precision
```

The immutable network plan was written before either new request. Exactly two
serial GETs fetched BTC/ETH `2026090101.csv.gz`, both HTTP206 with complete
Content-Range and valid full gzip. No old object was downloaded again. Actual
application body/header receipt bytes:48,632,063; retained new evidence:
181,915,995 bytes; recorded acquisition/parse/hash time:49.902709210113464 seconds;
peak recorded RSS:166,903,808 bytes; longest request:2.064311 seconds. The largest
new decompressed object is164,297,327 bytes. All dispatch limits passed;14 request
slots remain unused. Header/body accounting excludes TLS framing. Official web
research was separate:four search batches/12 queries and two document finds,
recorded in the manifest; no private API or current order-book access occurred.

**8 focused tests passed**, with socket access blocked. They check visible-depth
zero versus unknown, exact versus censoring-compatible differences, explicit
encoding evidence, non-fabricated interval bounds, two-object request scope,
unclipped residuals, a seed-independent mismatch and exact boundary arithmetic.
No old suite or already-accepted OHLCV/fee/volume tests were rerun.

Reproduce only the offline fixtures from the QR worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*args, **kwargs):
    raise AssertionError('offline network blocked')
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
suite = unittest.defaultTestLoader.loadTestsFromName(
    'tests.qr_research.test_qr011_micro_reconciliation')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

Completed immutable evidence commands should not be rerun against the same paths;
they reject overwrites. The manifests allow direct verification. No old budgets
were reset and no model, scaler, calibrator or strategy/account replay ran.

## Preservation, limitations and next handoff

Source `main` remains at `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; its actual
index, staged binary diff and unstaged binary diff hashes match the previously
verified values in the result manifest. No source, shared account binding,
runtime contract, risk default, dependency, credential, account configuration or
deployed service was changed. No merge/push, vendor message or collector start
is part of this task. Commit only these five files in the QR branch.

The supplier's precise event/liquidity-scope and numeric encoding are unresolved;
public ordinary/RPI API documentation does not identify historical archive scope.
The next source decision should obtain that versioned mapping or use a documented
compatible feed. A minimal structural pilot needs one contiguous paired BTC/ETH
interval, a full seed, at least two independent snapshots, complete intervening
trades/deltas and an hourly boundary. Broader calendar coverage and statistical
adequacy are separate gates. Snapshot/transactions-only research is a concrete
alternative, with explicit quantity intervals and no exact-OFI/fill assertion.

QD continues its already-assigned streaming ledger. This task neither sends QD
a new assignment nor reopens R05's document review. Any later data adapter is
QD-owned; this report supplies the incompatibility evidence and acceptance rules.
QR010's shared10000-USDT account binding remains frozen. QD/integrator retains
exclusive shared PROGRESS/DECISIONS editing ownership.

Training remains **NOT_READY**. Once compatible data, availability semantics,
continuous coverage and mature shared-account cost labels are ready, report the
evidence to the human and obtain fresh confirmation before any fitting. Do not
start another acquisition task or broaden scope on completion of this report.
