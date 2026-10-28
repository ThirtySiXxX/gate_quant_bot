# QF-QD-007-LEDGER: schema/API checkpoint

Date: 2026-10-28 Australia/Melbourne.
Status: **READY_FOR_QR_SCHEMA_REVIEW**. No ledger or test code written.
Dispatch: `QF-DISPATCH-20261028-QD007-SCHEMA-1`, bounded by
`QF-CONTROL-20261028-QD007-SCHEMA-BOUND-1`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`; clean parent:
`9bb3c0ec2b57e7154a51e56d795645c273c1308d`.

## Ownership and authorization

Current checkpoint edits only `research/qd007/schema.md` and this report.
The allocated subsequent QD paths are `research/qd007/event_ledger.py` and
`tests/test_qd_event_ledger.py`, plus ignored synthetic results under
`research/.data/qd007/`. Those code/test/output paths are not created now.
QD is the sole future implementation editor. QR owns its independent validator
and tests. The user authorized the bounded preparation objective; the next
dependency is exact QR schema review and coordinator implementation handoff,
not another general engineering permission question to the user.

Read AGENTS and required policy/architecture/ownership/context documents; no more
specific tracked AGENTS was found under research/docs/tests. Main worktree/index
remain independent and unchanged. No new worktree or branch was necessary.

## Frozen inputs checked

Semantic QR commit: `c7e9a2492247fa31e216035f87e8bb20cca6e6ad`.
Committed bytes rechecked read-only:

| QR file | SHA256 |
| --- | --- |
| `research/qr006/protocol.md` | `4957875f25168ea33d630fb63be00a712d86ac049b932bdc11f731e8b980e270` |
| `research/qr006/acceptance.json` | `d75fb7d7274ab2da41c71cd097f27982a3d2a7d103b5c1146d84da2429f9058c` |
| `docs/interface-requests/qr-qf006-execution-cost-label.md` | `d62c42ddc5cbac286e3b4ebf821fd977a693d7c3986ab019942560fa1348a6d8` |

QD006 accepted design/plan remains unchanged in its exact parent commit. The
universe assessment `52ce1ebeb054abd49c41fc4acbb4c7b7eb41c762` is read-only scope
context: it explicitly warns that fractional contract migration/current API
examples do not prove historical BTC/ETH precision. This stage restricts inputs
to integer-contract synthetic BTC/ETH scenarios, without truncation or expansion.

## Design delivered

The schema specifies typed scalars, strict bool/float rejection, decimal grammar
and canonicalization, integer UTC microseconds, nullable reasons, canonical hashes
and scoped business identities. The public in-memory Python API supports atomic
batches, independent inspection/deep copies, as-known snapshots, separate restated
audit views and synthetic completeness diagnostics. It does not emit market labels
or expose a training API.

Records cover Fill, funding eligibility snapshot, cumulative ObligationRevision,
independent Posting, scoped CompletenessAssertion, Valuation and Reserves. Lots
use FIFO integer unit ranges, so funding can follow the specific units eligible
at snapshot through partial reduction, reversal and later closed-state corrections.
Fee recognition and fee posting are distinct; T/B/P revision arithmetic preserves
cash until an independent posting is available. Unknown amounts and stale mark or
reserve inputs cannot become spendable zeroes. The synthetic budget remains
C-L+min(U,0)-reserves, with no actual-margin or liquidation claim.

Invalid batch prefixes cannot change the committed financial ledger, quantities,
accepted IDs or revisions. A separate integrity failure receipt stops that run;
audit remains inspectable, and no automatic recovery is invented. Unsupported
late fill reordering, imported posting restatements >1, fractional quantity,
hedged/conversion/historical modes and direct native payload use explicitly reject.

## Precise details requiring counterpart review

These are concrete typed-profile refinements, not unilateral changes to accepted
economic formulas or permission to implement before QR review:

- **S01 local transport:** namespace `qd007.synthetic-ledger`, explicit `_us`
  clocks and split snapshot/revision/posting records. It implements qf006 semantics
  but is not the qf006 wire exporter. Source-manifest binding avoids self-hashing.
- **S02 proportional amounts:** explicit allocation quantum, exact rational share,
  HALF_EVEN slices and final exact residual; no parent cash rounding. The 1/3
  example conserves 0.01 as 0.0033+0.0033+0.0034. Too-coarse rounding that would
  invent an opposite-sign share rejects. Partial-close attribution carries residue.
- **S03 transaction failure:** committed-state rollback plus a separate integrity
  stop/quarantine receipt; snapshots cannot be used to claim finality after conflict.
- **S04 bounded unsupported inputs:** no late origin repair or nullable-time paid
  Posting. Unknown booking stays an obligation without a posting; established
  postings require clocks. Authority/current revision coverage is explicit.

QR should confirm or give a minimal counterexample for these details, scalar
domains, genesis fee/funding revisions, public inspection APIs and the per-ID stage
map. Required implementation remains only the two allocated Python files after
handoff. No extra framework, database, dependency or file claim is requested.

## Checks and stage accounting

Only document/source-hash, schema structure and independent synthetic arithmetic
checks are appropriate here; no full application regression suite is run. The
schema has an explicit mapping of all 34 A IDs to synthetic stage-1 proof, partial
primitive proof or deferred coverage/replay/export/permission obligations. None is
marked implementation PASS. In particular historical exact evidence, full-state
counterfactuals, fold purge, market labels and training remain later gates.

No existing runtime, tests, configuration, shared journals/contracts, QR files or
previous research evidence changed. No source operational/private files, credentials
or account data were read. No market intake, replay, labels, fits, engine/app
operation, scheduling, integration, cherry-pick, push, merge, release or NAS/Windows
work occurred. No claim of training readiness or profitability follows.

Checkpoint verification passed with the existing read-only interpreter and Python
standard library: all 34 A IDs mapped exactly once; no ledger/test implementation
file exists; Markdown code fences balance; decimal lexical examples validate as
declared; positive/negative 1/3 allocations conserve the parent; the coarse-quantum
counterexample requires rejection; literal T/B/P and 24h microsecond identities
agree. `git diff --check` passed. These are document checks, not producer tests.

Exact `research/qd007/schema.md` SHA256:
`800919cf19f02b7b7f896347f378eeef994607f2f13383d01adac1ef921f191b`.
Original main HEAD is still `cae0d2395adf2cd3905e41cb1c16748c8247c32c`;
staged-diff SHA256 is still
`c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce` and actual
index-byte SHA256 is still
`7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.

## Handoff and stop

Coordinator reads this exact committed checkpoint and forwards QR's precise
review. Status remains READY_FOR_QR_SCHEMA_REVIEW until that handoff. Do not write
the ledger/test implementation or poll for a review in this turn. Record any
revision in these owned documents; implementation must use the reviewed schema.
