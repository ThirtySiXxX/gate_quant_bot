# QF-QD-007-LEDGER: schema/API checkpoint

Date: 2026-10-28 Australia/Melbourne.
Status: **READY_FOR_QR_SCHEMA_REVIEW**. No ledger or test code written.
Current proposal: `qd007-synthetic-r2`; six-request revision response is appended
below. The original checkpoint record is retained for traceability.
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

Original checkpoint `d474fdf0fdca7cb22aa47cfb220806b8ea2ab84f`
`research/qd007/schema.md` SHA256 (superseded by the revision below):
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

## Revision checkpoint: QR007-R01 through R06

Dispatch `QF-DISPATCH-20261028-QD007-SCHEMA-REVISION-1`; QD parent
`d474fdf0fdca7cb22aa47cfb220806b8ea2ab84f`.
Read-only QR review commit `c4b1fdcb90427a6229bd75d8abbff66fcb795047`;
committed bytes and working files verified against:

| QR file | SHA256 |
| --- | --- |
| `research/qr007/ledger-review.md` | `bb4ebc1b93de7404d271301853392a8947b69203e88abb032713491555566a49` |
| `docs/agent-reports/qr/QF-QR-007-readiness.md` | `d78f56a16a955d7807f4ae20b80f807668357a484c8f45aab26971e8216e5662` |

All six requests have concrete document revisions, **pending QR recheck**, not
self-approved implementation acceptance. Only schema.md and this report change.

| Request | Revision location / selected bounded rule | Fixed positive and negative future acceptance case |
| --- | --- | --- |
| QR007-R01 | Sections 3/6: separate full config/source/journal audit identities from causal_policy_sha256; exact Snapshot-minus-state_sha preimage includes policy only, no catalogue/source/content/export hash | Same declared policy/past facts, future T at20 changed and whole catalogue/all source_refs rehashed: snapshot10 content/hash identical, audit hashes different. A genuinely different initial policy may change causal hash. |
| QR007-R02 | Sections 4.1/6: whole-candidate admission guard against the predeclared calendar, followed by availability-first visibility; no late-origin repair | F filled7/available9 crosses S8: [F,S], [S,F] and F alone reject. Prior committed S is unchanged on later F failure. F filled=available7 and S8 passes; same-economic-time tie rules remain separate. |
| QR007-R03 | Section 4.3: causal proxy mark valuation<=availability<=snapshot, age measured at snapshot; revision known time covers all formula inputs | S80/mark79 available90 rejects even with rate95/revision100. Mark79 available79 and rate95, revision known95/available100 passes; T stays unknown at99 and is recognized at100. No new posthoc mark scenario. |
| QR007-R04 | Sections 4.5/6: admission checks legality; readiness evaluates only current available assertion heads/refs, scope and settled balances; old legal assertions never latch | A1 at10 complete for T1/B=-.05; T2=-.08 at20 makes immature; Posting-.03 at21 settles but old refs stay stale; A2 at22 restores complete_at22. Same full batch and ordered batches agree, earlier query unchanged. Null authority can yield invalid readiness but a proper successor replaces it. |
| QR007-R05 | Sections 2/4.3: per-logical-kind IDs globally owned within ledger, with mandatory instrument/trajectory/scenario reference checks; allocation hash explicitly contains full owner scope | BTC f1 plus ETH f1 rejects ID_SCOPE_CONFLICT before mutation; f_btc/f_eth and distinct obligations work together. Cross-instrument lot/posting/refund/assertion links reject even with unique text IDs. |
| QR007-R06 | Sections 5/6: all output fields/null reasons explicit, cash Posting entry preserved with unknown T, conditional pending/A/L deltas, coverage_issues for absent origins | C0=1000,U0,T unknown; Posting-.02 available10 gives C999.98/B-.02 while T/P/A/L/E/budget remain null. T=-.05 available20 gives C999.98/P-.03/A0/L.03/E999.95, but unknown-prior deltas are null. Missing due snapshot yields unknown aggregates without inventing a zero obligation. |

R04 also includes an explicit query state table: missing expected snapshot,
mapping=null, unknown nonempty T, unsettled P and missing/stale assertion each
remain unresolved/immature; empty calendar does not erase an existing unknown
claim. Null mapping is permanently unqualified in this rev1-only snapshot
instance, requiring a separately approved corrected fixture rather than a later
total silently proving the mapping. Unregistered authority/hard identity errors
remain integrity failures; legal staleness/unknowns do not.

R06 keeps one per-obligation balance entry for each known Posting/claim change,
with separate source allocations for lot attribution; cash is never copied into
each allocation row. Null delta is conditional on unknown before/after level,
not a fabricated zero. Snapshot, ClosedSlice, Readiness, LedgerEntry and failure
receipt have local null-reason maps and closed field sets. Full audit identities
remain available for independent checking outside the causal snapshot preimage.

Accepted S02 remains unchanged economically. The schema now includes the exact
positive/negative/zero/invalid-weight literals from QR, 1/1/1 versus 2/1 FIFO
rounding paths, and the -.01 to -.02 revision oracle. Later current attribution
recomputes the same original closing path with the new cumulative amount; it
does not add a new total to old slices or cash. Parent amounts are conserved;
opposite-sign residuals reject atomically.

The user's actual economic-validation cutoff is now **2026-10-01 00:00 UTC**;
October is pending evidence. This is coverage-stage context only: no real dataset
is rewritten/recertified here and no default is injected into synthetic config.
Scope remains integer-contract BTC/ETH SCENARIO; no actual history/precision,
mark coverage, market label or training readiness is established by this revision.

Status remains READY_FOR_QR_SCHEMA_REVIEW. After document-only checks and an
independent commit, stop for the coordinator's exact QR recheck. Do not write
event_ledger.py/tests, collect data or begin replay/labels/fitting.

Revision verification passed using the existing read-only interpreter and Python
standard library only: two exact QR committed/file hashes; separate causal/audit
preimage algebra for a rehashed future-fact perturbation; R02 availability guard
inequalities for both input orders and the valid prefix; R03 mark/rate clocks;
R04 10/20/21/22 readiness/ref/pending literal trajectory; R05 scoped identity/hash
positive/negative examples; R06 known-cash/unknown-total and later known-level
arithmetic; accepted S02 signed/zero/remaining-FIFO/revision oracles. All 34 A IDs
are still mapped exactly once; Markdown/output declarations and whitespace checks
pass. These are document/oracle checks, not execution of a producer or validator.
No application regression or implementation tests were run.

Revised `research/qd007/schema.md` SHA256:
`6e5fea553aedcdf6d800ced8a2ba5d0d49b5abd0b60cf931417fd6dff78408b7`.
The original main HEAD, staged-diff SHA and index-byte SHA again match the
preservation values above. Git changes are exactly the two owned Markdown files;
ledger/test Python files remain absent. No existing evidence or shared document
was changed, and no market/operational action was performed.
