# QF-QR-010-HISTORICAL-MICRO — completed bounded evidence task

2026-10-28 · QR · Dispatch `QF-DISPATCH-20261028-QR010-HISTORICAL-MICRO-1`.
Shared-account addition: `QF-CONTROL-20261028-QR010-SHARED-ACCOUNT-1`.

Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
Branch: `codex/qr-validation-baseline`.
Base: `a9815031a75510ac0473f75bd27941fe55fbad44`.
The independent commit containing this report is the delivery commit; no merge,
push or deployment is performed. QD's independently owned implementation paths
and the source checkout are unchanged by this task.

## Completed changes and conclusions

Actual anonymous Gate downloads produced six complete hourly delta-book objects,
six complete hourly snapshot objects, six bounded monthly trade prefixes and two
current contract metadata responses. The three fixed calendar anchors are
2023-01-01, 2024-07-01 and 2026-09-01, 00 UTC, for BTC/ETH only. All eight anonymous
Hyperliquid object/listing requests returned403. No HL data was obtained; paid
access was not enabled. The files, receipts and hashes are retained locally.

The research parser audited9,842,500 depth rows,20,090 snapshots and1,299,844
complete trade rows within truncated prefixes. Canonical v3 emits12,954
snapshot-bridged feature rows and360 trade-minute examples. These are explicit
retrospective diagnostics with null historical availability, not production
signals, trading performance or an approved training dataset.

2023 BTC has a proved identical repeated delta; it is a logged no-op, while
conflicting duplicates fail. The 2024 BTC pair has one quantity mismatch, excluded
from features. The September2026 BTC pair matches0/3275 exact boundaries; ETH
fails reconstruction on a negative residual quantity and also has substantial
snapshot discrepancies. Both recent book samples emit zero qualified features.
Full details and raw-line references remain in the canonical analysis files.
No rounding, zero fill, timestamp backdating or data replacement conceals these
failures. Earlier v1/v2 analyses are retained as development/failure evidence.

Scientific decision: **INCLUDE** verified fragments in finite microstructure
rule/feature research; **DEFER_PENDING_EVIDENCE** for ML promotion; the currently
inconsistent2026 book pair and truncated trades-as-full-month are **NOT_SUITABLE**
for those stronger uses. L2 cannot establish individual-order cancellations,
queue position or exact real fills. No OOS incremental value has been measured.

The assessment freezes a small candidate family, distinct30-second/hourly/
execution questions, chronological split and finite comparisons, including an
exposure/turnover explanation for apparent losing-streak improvements. The
matched-account comparison requirement and effective sample dependence are
explicit; fixed counts of days/trades are not statistical sufficiency guarantees.

The account binding implements the human's approved direction as a specification:
one shared initial10000-USDT account, joint native BTC/ETH allocation and risk
budget×10, simulated margin divisor200, synthetic per-contract1000000-USDT tier,
shared reserves and per-asset finality. Eligible increases receive atomic basket
admission with no hidden asset cash priority. It replaces18 independent paths
with9 joint paths, plus at most6 failed diagnostic restarts, under the existing
absolute24-attempt and4-hour budgets. No account replay ran in this task.

## Files modified — exact exclusive allowlist

| File | Purpose |
|---|---|
| `research/qr010/historical_micro_probe.py` | Anonymous bounded retrieval, immutable receipts, exact-decimal archive decoding and quality diagnostics |
| `research/qr010/historical-micro-data.json` | Version1 manifest:40 request receipts,12 canonical analyses,180 evidence files with hashes, resource usage, source hashes and tests |
| `research/qr010/microstructure-training-assessment.md` | Actual quality findings, inclusion decisions, finite scientific plan, storage scenarios and readiness gaps |
| `research/qr010/shared-account-binding.md` | Implementable joint-account semantics and targeted QD acceptance cases |
| `tests/qr_research/test_qr010_micro_probe.py` | Synthetic bounded-I/O, integrity, decimal, duplicate, gap and snapshot-bridge rejection tests |
| `docs/agent-reports/qr/QF-QR-010-historical-micro.md` | This role-specific delivery and handoff |

Raw/derived files are only under ignored
`research/.data/qr010/historical-micro/`; none is staged. No `.gitignore`, shared
interface, runtime strategy, risk setting, dependency or existing journal is
edited. QD/integrator owns any eventual shared PROGRESS/DECISIONS update.

## Evidence, tests and resource results

The immutable pre-request plan is
`research/.data/qr010/historical-micro/request-plan.json`. It fixed40 requests
and8 reserved slots before network work. All40 executed once, serially; no
reserved slot was used. Application body/header receipts total80,684,514 bytes,
recorded acquisition/parse time102.35273670639796 seconds, recorded peak RSS
179,896,320 bytes, and retained evidence102,702,077 bytes. All stay under the
dispatch caps. Documentation requests are logged separately by URL/query;
transport/TLS overhead and prose-writing time are not represented as data bytes
or parsing CPU. No full-month downloads, unlimited pagination or collectors ran.

The final manifest SHA256 is
`3476bdab44da4631f600c1b99ba41c96a474f05bb6a303e45a8ad868350b3338`.
Canonical parser SHA256 is
`fa9ccfb18d316abc385ad472c7c8a1179a2d2232424be1d0a356db9cb7629b5c`.
Manifest source pins, all40 raw receipt hashes,12 feature hashes and plan hashes
were verified against actual files. Complete archive gzip validation passed;
all six trade prefixes correctly report `TRUNCATED_GZIP` with no complete-month
claim. Scientific failure flags are expected evidence, not a reason to make
unit tests accept inconsistent books.

**12 tests passed**, using the existing source virtual environment with network
blocked at socket connection calls. Fixtures use temporary files and synthetic
responses, including a server ignoring Range, truncated/oversized/multimember
gzip, exact fractional sizes, missing source IDs, negative residual rejection,
conflicting identities, and an end-to-end archive bridge. The bridge test proves
interior merged IDs and mismatched snapshots are omitted and OFI resets across
the mismatch. No dependency installation was needed.

Reproduce just the offline tests from this QR worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*args, **kwargs):
    raise AssertionError('offline test network blocked')
socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
suite = unittest.defaultTestLoader.loadTestsFromName(
    'tests.qr_research.test_qr010_micro_probe')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
PY
```

The evidence is already acquired/analyzed; do not rerun `plan`/`fetch` or reset
its budget. Those commands reject reused IDs/paths. Audit the manifest and
canonical files directly. The original commands were `plan`, three finite
`fetch --ids` groups covering R01–R40, `inspect`, and a final
`analyze --ids R02,R05,R07,R10,R12,R15,R17,R20,R22,R25,R27,R30 --version v3`.
Network requests are not part of the offline test command.

Source-preservation verification matches the earlier reviewed fingerprints:

| Source property | Final observed value |
|---|---|
| HEAD | `cae0d2395adf2cd3905e41cb1c16748c8247c32c` |
| Index SHA256 | `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80` |
| Staged binary diff SHA256 | `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce` |
| Unstaged binary diff SHA256 | `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d` |

This verifies Git/staging preservation, not a read or fingerprint of private
ignored operational files. No credentials, real configuration, account data,
application engine, NAS service or live order was accessed or changed.

## Known limitations, ownership dependencies and next steps

**Training readiness: NOT_READY_FOR_TRAINING.** Six hours establish format and
specific quality findings, not representative OOS coverage. Full trade objects,
continuous paired calendar coverage, qualified/simulated availability rules and
mature execution-cost labels remain missing. Historical metadata/revision
semantics are not supplied by current contract responses. Storage extrapolation
is a measured-rate scenario, not evidence of complete archives. No profitability
or cross-margin liquidation/ADL survival is established.

QD owns the active streaming-ledger and execution implementation. QR supplies
the shared-account specification; targeted new implementation cases are listed
there. This report does not redeploy QD, reopen R05's completed document review,
or request another full review of passed OHLCV/fee/volume evidence. The coordinator
can use this completed research finding to progress without a repeat audit loop.

Next research task: narrowly reconcile the2026 book-state/precision mismatch,
then acquire integrity-checked continuous Gate periods under a newly sized finite
budget. HL needs a separately authorized access/billing route or legitimate
provided archive if the cross-market arm is desired; no paid choice is necessary
to use the Gate evidence already obtained. Keep both assets in the one-account
cost/label comparison. Once the dataset, alignment and labels meet the stated
readiness conditions, report that evidence and ask the human to confirm training.
Do not fit a model/scaler/calibrator, start another task, activate candidates or
run shared-account trajectories merely because this task is complete.
