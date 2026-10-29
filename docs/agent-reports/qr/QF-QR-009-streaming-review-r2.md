# QF-QR-009 streaming contract r2 — QR handoff

2026-10-28. Task `QF-QR-009-STREAMING-CONTRACT-REVIEW-R2`; dispatch
`QF-DISPATCH-20261028-QR009-CONTRACT-R2-REVIEW-1`.

**Result: REVISE. RV01–RV04 accepted at design level; one bounded R05
UNKNOWN-to-authoritative-view/recovery binding remains.** No implementation
failure or runtime PASS is asserted. Training is not ready and no fit was run.

## Completed changes and exact review objects

Read the entire1637-line target from Git:
`9c6d18559e35377d45f0bfc951ab4cbce20cc202`, parent
`89cf347482c8121a4e3da559c6fb639a30788d6f`, sole changed file
`docs/interface-requests/qd-qf009-streaming-ledger.md`, SHA256
`d3adb32230ceb698d7a9d5372b412471586ec9341a93176a720110811fec927a`.
Reviewed schema2/profile `qf009-offline-stream-r2` against QR4d4e530, QD89cf347,
the frozen QR proposal r2 at5dc7232, historical contract19cd4c7 and unchanged
r3 source text0ea2d519. No moving QD draft or implementation was substituted.

| Item | Design conclusion / evidence still required |
| --- | --- |
| RV01 | ACCEPT: complete role-scoped facts/economic selections, stored intent/order status, actual FIFO ranges, own/peer state, read inventory, source cutoffs and oversize rejection. Independent P/X/environment, forged membership, interrupted partial/cancel and actual native S13 remain unexecuted. |
| RV02 / R03 | ACCEPT: original-clock genesis context, receipt/dedup/cursors and first initialization; no warmup finance. Cutoff expiry/lifecycle and evidence-only tail retain unknown budgets/open exposure. Synthetic boundaries/restarts and actual native prefix parity remain unexecuted. |
| RV03 | ACCEPT: lease, reachable exact request, repeated fsync/readback, durable guard/CONTROL and monotone integrity/resource stops. Old checkpoint cannot clear a latch or spent budget. All fault-injection/receipt/recovery acceptance remains unexecuted. |
| RV04 | ACCEPT:90 named S01–S12 outcomes/118 fixtures per suite, no hidden QR benchmarks, unchanged8 producer measurements/two120s suites/720s and resource caps. Exact fixture bytes/oracles still must be frozen before execution. S13 remains a separate mandatory gate. |
| R05 | REVISE: qualified mark_selection transports unknown cells, but its effect on authoritative U/E/budget and later recovery is unspecified. Known source/consumer clocks, stable identities and separate external query qualification are accepted. |

The detailed review supplies two finite static counterexamples. QG01 has a
missing required adjacent month while the old MARK remains age-valid; merely
transporting UNKNOWN/noop leaves unchanged r3 U0/budget1000 supported. QG02 has
UNKNOWN at B+121 then an eligible source B+62 selected at B+125; a null financial
Valuation at query origin B+121 would dominate the recovered older source.
Changing the old source's price to null also conflicts with r3's same-source
valuation rule. These show why the binding must be explicit; they are not claims
that native/query code has already executed either erroneous mapping.

QD must define typed query-status authority, reason mapping, slot/view effect,
recovery, causality, historical/restart state and a finite regression mapping.
Frozen r3 remains unchanged. Do not solve it only with a private veto while the
authoritative balance stays known; do not fabricate source clocks. No scanner,
new strategy, broader universe or increased resource allowance is requested.

## Modified files

Only two new QR-owned documents on `codex/qr-validation-baseline`, based on
`5dc72325580259ee8d578625f0ee33d0d13eec73`:

- `research/qr009/streaming-ledger-review-r2.md` — full evidence, closed RV items,
  two R05 counterexamples and bounded acceptance request; SHA256
  `b8e99c0eb506304be926e6740626dc812fd834308f9d862d64348be299232013`.
- `docs/agent-reports/qr/QF-QR-009-streaming-review-r2.md` — this handoff.

Old QR proposals/specs/reports, QR006/007/008, QD files, native code, data and shared
journals are frozen. The independent delivery commit is the commit adding these
two files; obtain its exact SHA with:

```sh
git -C /Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot log -1 --format='%H' -- research/qr009/streaming-ledger-review-r2.md docs/agent-reports/qr/QF-QR-009-streaming-review-r2.md
```

## Checks performed and results

- Full static type/dataflow/clock/persistence/manifest review of the exact target.
- 15/15 initial documentation checks passed: target SHA/parent/one-file scope/
  line count, unchanged FinancialBody/invariant block and error-registry text,
  unique contiguous90-case inventory/replica membership/118 count, fences,
  budget arithmetic and clean QR base.
- 4/4 independent stdlib clock/ordering calculations passed for QG01/QG02. These
  reason about the proposed clocks and frozen selection ordering; no producer
  arithmetic, native module, raw archive or query implementation was imported.
- Supplementary checks confirmed both exact review-basis hashes, the76 unique
  retained r3 error codes and frozen r3 source SHA256
  `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`.
  One supplementary check initially failed because its copied expected QD-report
  hash omitted `cb`; correcting that literal against the dispatch and exact Git
  object made the comparison pass. No source/expected financial outcome changed.
- Socket create_connection/connect/connect_ex were blocked for the inline stdlib
  checks. No dependencies were installed, implementation test files written,
  native code imported, raw data scanned, benchmark/query/replay/labels/fit run,
  trading engine started, external message sent or service changed.
- Delivery verification checks the two-file allowlist, whitespace/diff, exact
  hashes, unchanged tracked base files, source preservation and clean commit scope.
  These are document/Git checks, not extra functional-suite attempts.

Source checkout preservation baseline and recheck use HEAD
`cae0d2395adf2cd3905e41cb1c16748c8247c32c`,72 status entries:

| Fingerprint | SHA256 |
| --- | --- |
| Real index bytes | `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80` |
| Staged binary diff | `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce` |
| Unstaged binary diff | `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d` |
| Full porcelain status | `2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649` |

These Git/index fingerprints preserve the observed staging boundary; they are
not a fresh byte-hash census of every ignored/untracked file. No such scan or
credential/config/account-data read was performed.

## Limitations, dependencies and next step

All S01–S13 are NOT_EXECUTED in this task. Initial suites, eight benchmarks and
persistence fault injection are unexecuted; S13 remains BLOCKED_NATIVE_PORT /
R3_NOT_READY. MARK complete-prefix/latest-eligible query proof, actual native
timing/sizing/feedback/full-state parity, finite native acceptance, market replay,
labels/purge/sufficiency and frozen model evaluation are still separate gates.
The original QF00634 criteria and BTC/ETH-only scope remain unchanged.

QR's U1–U3 are proposals, not approved capital/latency/slippage/capacity/reserve/
feedback choices. This contract review grants no research choice, market run or
training permission. Before any model/scaler/calibrator fit, report readiness and
obtain fresh human confirmation. No activation, live order, credential use or
NAS/Windows/deployment change is authorized.

Coordinator next: request one bounded QD R05 amendment with exact commit/hash,
then QR rereview. Preserve accepted RV01–RV04, initial budgets and existing file
ownership. Respect the two-amendment-round limit; do not turn this into an
automatic retry loop or start implementation while the binding is unresolved.
If representation is deferred, explicitly block native registration/implementation
until its versioned contract is reviewed. QD integrates shared journals after
review. Stop after this independent two-file commit; no cross-chat reply, merge,
push or main-checkout edit.
