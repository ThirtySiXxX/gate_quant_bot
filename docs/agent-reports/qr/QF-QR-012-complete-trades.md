# QF-QR-012-COMPLETE-TRADES — completed

2026-10-28 · QR · dispatch `QF-DISPATCH-20261028-QR012-COMPLETE-TRADES-1`.
Worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`;
branch `codex/qr-validation-baseline`; base
`3b97e4f56588574e9fd7231e8ffac88c2952378f`.

## Changes and result

Completed the fixed September 2026 BTC_USDT/ETH_USDT public-trades pilot using
four serial anonymous requests. Both complete objects pass version/length checks,
overlap verification and full gzip CRC. Streamed exact-decimal analysis covers
20,458,327 BTC and 30,927,796 ETH rows. Each asset has records in all 43,200 minutes
and 720 hours, with no invalid row, duplicate/conflicting ID, adjacent ID gap or
timestamp reversal. ETH's 17,457,765 fractional quantity rows retain their source
precision. Every minute's count, contract sum and line partition reconciles to
its hour and file.

Neutral count/absolute-contract aggregates and quality masks are available for
retrospective research. Archive aggressor mapping and event inclusion remain
unresolved; all directional features are null. Historical receive/available
clocks are also null and decision eligibility is false. **Training NOT_READY.**
Structural completeness does not prove the exchange event universe, historical
availability, predictive value or profitability.

## Files modified

Exactly five assigned new tracked files:

- `research/qr012/complete_trades_pilot.py`: bounded acquisition, exact-decimal
  streaming quality checks, duplicate/conflict handling and minute/hour outputs.
- `research/qr012/complete-trades-result.json`: plan, receipts, source pins,
  measurements, resource use, tests, preservation and hashed evidence inventory.
- `research/qr012/complete-trades-findings.md`: semantics, measurements,
  limitations, recovery evidence and training gates.
- `tests/qr_research/test_qr012_complete_trades.py`: eight focused offline tests.
- `docs/agent-reports/qr/QF-QR-012-complete-trades.md`: this report.

New raw/derived evidence is only under ignored `research/.data/qr012/tmp/`.
No expanded CSV is retained. Prior evidence files are not overwritten.

Result manifest SHA256:
`1a7ca17bbb2c1799d91dcc226a201d2d4f5828a004dba55e962a5acf2122788c`.
Parser/source SHA256:
`396aef1a0abc3c56ca8ff9590d03d86153f824faf01f21c55af12ad8409716c9`.
The manifest inventories 28 evidence files totalling 561,928,885 bytes. Its
conservative first-request-to-manifest wall envelope is 612.705269 seconds,
including time between commands and inventory hashing outside operation timers.

## Tests and execution

**Eight focused tests passed with socket connections blocked**, with zero errors
or failures and 0.035204 seconds total recorded test wall time. They cover exact
fractional parsing/invalid values, unknown direction, strict range/version
checks, prefix-plus-tail assembly, rejection of a 200 as a continuation, duplicate
and conflicting IDs, exclusive boundaries/empty-minute uncertainty, truncated
gzip rejection and partial-transport rejection. No old suite was rerun.

Actual data commands, using the existing interpreter, were:

```text
research/qr012/complete_trades_pilot.py plan
research/qr012/complete_trades_pilot.py fetch
research/qr012/complete_trades_pilot.py analyze
```

Do not rerun completed evidence commands against these paths: they refuse to
overwrite the immutable request plan, receipts or derived outputs. Reproduce the
new offline fixtures without network access:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*args, **kwargs):
    raise AssertionError('Network disabled during offline verification')
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
suite = unittest.defaultTestLoader.loadTestsFromName(
    'tests.qr_research.test_qr012_complete_trades')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

An additional evidence audit reconciled all 86,400 minute records to the 1,440
hours and 51,386,123 source rows, verified output hashes/line partitions and
confirmed every direction/arrival-time field remains null. This is arithmetic
and provenance verification, not a model fit or return test.

Data requests received 486,461,306 application body/header bytes. Longest request:
8.795 seconds; largest decompressed object: 1,243,902,808 bytes; peak recorded RSS:
62,849,024 bytes. Recorded acquisition, parsing, preservation and aggregate-check
work took 289.909 seconds. Exact evidence sizes and a conservative acquisition-to-
report wall envelope are included in the result manifest. All QR012 resource
limits passed; eight request slots and both full-fallback paths remain unused.
Official-document browsing is separately disclosed, not counted as raw-data I/O.

## Preservation and counterpart dependency

Verified unchanged: all 180 QR010 and 33 QR011 evidence files and their source
pins/manifests. Source `main` remains at
`cae0d2395adf2cd3905e41cb1c16748c8247c32c`; real index, staged binary diff and
unstaged binary diff hashes match the prior preservation record. Its staging
boundary and user work are preserved. No source application, shared contract,
risk default, dependency, real credential/account data, NAS service or trading
process was touched. No push, merge, model/scaler/calibrator fit, strategy/account
replay, collector, price search or parameter search occurred.

QD continues `QF-QD-009-STREAM-REPAIR-1` independently. This task supplies data
quality evidence; it does not assign QD a new task or change the frozen shared
account binding. Runtime adapters and shared PROGRESS/DECISIONS integration stay
with QD/integrator after review. Only these five QR files are committed locally;
the exact resulting commit is reported in the handoff, without automatic merge.

## Known limitations and next step

Obtain archive-specific aggressor/event-scope evidence before directional flow
features. Resolve availability or obtain an explicit simulated timing choice,
plan adequate contiguous BTC/ETH coverage, and complete shared-account cost/label
acceptance before a training-readiness review. QR011's exact public-L2 mismatch
is not repaired by this trades pilot. No extra currency is included.

The suggested 2024 train / 2025-H1 validation / 2025-H2 test calendar remains a QR
candidate; it did not replace the user's earlier 2024 train / 2025 validation
direction. No training split was applied. The human must choose the final
calendar later and give fresh confirmation before any training. Do not infer
that completing a one-month file pilot grants that confirmation or authorizes
another acquisition task.
