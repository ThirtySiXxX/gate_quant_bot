# QF-QD-007-LEDGER: schema/API checkpoint

Current status: **CANDIDATE_READY_FOR_QR_INDEPENDENT_VALIDATION**. Implementation
and candidate identities are appended after the preserved schema-review history.

## Resolved B1 dependency (history, 2026-10-28)

Dispatch QF-DISPATCH-20261028-QD007-IMPLEMENT-1; implementation in progress after
QR acceptance `4d2f57a65456c299bb7d05a64e119d01a251a2b9`. Frozen schema unchanged.
**B1: unknown revised fee attribution needs counterpart clarification.** A
closed fill's fee obligation has a known original total, then an allowed fee
ObligationRevision sets cumulative_signed_total_usdt=null/UNKNOWN_AMOUNT. Financial
T/P/A/L/E/budget can remain unknown as required, but ClosedSlice entry_fee_cash_usdt
and exit_fee_cash_usdt are nonnullable D, while current attribution must reflect
the latest cumulative revision. Zero or the previous total would falsely assert
known current fees; adding nullability is outside the frozen code allowlist.
Requested resolution: explicitly permit unknown affected fee attribution with a
null reason, or specify a separate prior-known attribution/validity convention.
No capability is silently rejected or field changed. Continue independent core
implementation while coordinator/QR resolves this concrete schema dependency.
Resolution: coordinator supplied the exact QR-reviewed B1 amendment below;
the formerly blocking dependency is closed in profile qd007-synthetic-r3.

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

## Implemented synthetic ledger, reviewed r2 plus B1

Implementation dispatch: `QF-DISPATCH-20261028-QD007-IMPLEMENT-1`;
parent `a183e40ed27b2250f7030ce3babbe5d579dc268b`. QR's six-request schema ACCEPT
is exact commit `4d2f57a65456c299bb7d05a64e119d01a251a2b9`, review SHA256
`6244a0fce343215ba43f60db76483a945075f4c6bcdfe4bd349dab6d1e30bf54`.
The accepted r2 schema SHA remains historical
`6e5fea553aedcdf6d800ced8a2ba5d0d49b5abd0b60cf931417fd6dff78408b7`.

`QF-DISPATCH-20261028-QD007-B1-AMENDMENT-1` additionally authorized the owned
schema edit after QR's minimal B1 review. Verified exact proposal snapshot
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qr007-b1-reviewed-proposal.txt`,
SHA256 `8e6e1af12fd5bc1257ee78f5fb21d11d58bf8eeb6c7532a9d47ca57f37228bd1`.
Local profile now **qd007-synthetic-r3**, namespace/schema_version still the
standalone local version1. Only the two ClosedSlice fee fields gained reviewed
nullable propagation; no target/net field, cash rule or runtime migration added.

Implemented the frozen public APIs in `research/qd007/event_ledger.py`, standard
library only: strict typed normalization and fixture provenance, canonical hashes,
exact rational arithmetic, quantum/residual FIFO attribution, explicit event
eligibility, original fee claims and independent cash postings, cumulative T/B/P
revisions, after-close credits/surcharges, unknown propagation, synthetic budget,
availability-filtered snapshots, separate restated audit, scoped completeness
diagnostics, global entity ownership, source idempotency and all-batch atomic
commit/integrity stop. Public inputs are copied and all returned data deep-copied.
The module performs no I/O and imports no app/exchange/model code.

Implementation details within the accepted contract: attribution_revision is a
positive deterministic counter from the relevant available source revisions,
so updates to either independent fee side change the current version; it is not
the maximum unrelated revision ordinal. Balance entries remain one per obligation
transition, with separate FIFO slice attribution. Canonical candidate state/hash
and receipt are prepared before commit. Conflicting simultaneous reserve updates
reject rather than selecting a monetary state by ID order. Constant-multiplier
profile rejects undeclared conversion capability.

## Executed producer verification

Added `tests/test_qd_event_ledger.py`: **32 unittest methods passed**, including
hundreds of strict-type/null/shape subcases (not counted as separate tests).
Expected monetary values are literal independent examples, not calls to QD
finance helpers used as oracles. QR's new validator/tests were not read or edited.

- All R01-R06 positive/negative scenarios execute through the public API,
  including cross-fixture future catalogue perturbation, whole-batch late-fill
  rejection, mark availability versus late final rate, 10/20/21/22 completeness,
  two-coin ID ownership, and numeric Posting with unknown total/null deltas.
- Signed/zero fees/funding, explicit no-event calendar, partial closes before and
  after snapshot, adds/reversal attribution, split payments, refunds, revision gaps,
  conflicting IDs and posting restatement rejection execute on synthetic tapes.
- S02 signed 1/1/1 and 2/1 paths, cumulative correction recomputation, invalid
  weights and opposite-sign coarse-quantum residual rejection pass independently
  of ambient Decimal precision/traps.
- B1 tests cover entry unknown, symmetric exit unknown, both unknown, every affected
  closed partial slice, later restoration and separate refund. Known other values,
  original cash/B and earlier cutoff outputs remain intact; malformed null reasons
  reject. No new episode-net output was invented.
- Output field sets/local null maps, source corroboration versus causal hashes,
  deep-copy/input preservation, rehashed semantic corruption and atomic rollback
  are checked. Restated future booking outside its economic cutoff initially
  exposed a DANGLING_ORIGIN error; filtering excluded bookings before finance
  projection fixed it. The corrected focused suite passes; this was not hidden.

Commands from the QD worktree (no installs):

```sh
# Focused: existing interpreter, socket connects blocked before unittest discovery.
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*a, **k):
    raise AssertionError('QD007 offline only')
socket.create_connection = socket.socket.connect = socket.socket.connect_ex = offline
r = unittest.TextTestRunner(verbosity=1).run(
    unittest.defaultTestLoader.discover('tests', pattern='test_qd_event_ledger.py'))
raise SystemExit(not r.wasSuccessful())
PY
# Existing guarded file entry supports macOS spawn and blocks child socket connects.
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python research/qd005/run_offline_tests.py
node tests/web_regressions.cjs
git diff --check
```

Results: focused **32 passed** (0.127s); full Python discovery **262 passed**
(12.264s); **8 frontend regression groups passed**; whitespace checks passed.
These are producer/old-regression results, not QR independent implementation PASS.
Fixture log messages about HTTP responses/disk failure are intentional mocks;
no actual market request or application/engine startup was performed.

Current code/schema identities before candidate generation:

| File | SHA256 |
| --- | --- |
| `research/qd007/schema.md` | `7fd7df5f84a8822f5fdd37243d24e0eb293d9eeacda17514c8b1f1ad04ac475a` |
| `research/qd007/event_ledger.py` | `354df077fba2c7ea0cd2d7cfb83c4a68f9102aa7fb398b1af7106727bf40645a` |
| `tests/test_qd_event_ledger.py` | `628e8a22eb87384e72867f7e673ea58ef4fcc1b2de07efd388c97c77eeb8a1f2` |

The table above records initial tested implementation commit
`69c8bf1d8a060ccdf0b103a3e3226c8f200dc960`. Before publishing candidate outputs,
a narrow receipt correction makes cross-record admission failures hash the full
candidate input, with recoverable_identity=null rather than falsely identifying
the last successfully normalized record. An explicit R02 assertion checks that
receipt. Financial semantics/schema are unchanged. Focused **32 passed** (0.136s)
and full socket-blocked **262 passed** (14.478s) after this change; JS remains the
unchanged-runtime eight-group pass above, not rerun without a frontend change.

Final candidate implementation SHA256:
`7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`.
Final producer-test SHA256:
`aa4ec5c282ab6107c3970c986dd3ba2e45d86638b265eabdc36a86c921f7c8d8`.
The reviewed B1/r3 schema SHA remains
`7fd7df5f84a8822f5fdd37243d24e0eb293d9eeacda17514c8b1f1ad04ac475a`.

## Stage evidence and remaining gates

Executed S1 primitive/ledger evidence covers A01/A02/A04/A05/A07/A09-A14/A17-A20
and R01-R06/B1. Partial S1 evidence only: A03/A06 order/no-event arithmetic,
A08/A15/A16/A31-A33 profile/rule rejection rather than historical proof,
A21/A29 synthetic readiness rather than EpisodeLabel export, A22 units rather
than complete fold purge, A24 FIFO/add arithmetic rather than target export,
A27 local namespace/static isolation, A30 synthetic mark freshness and A34 given-
fill PnL. A23/A25/A26/A28 full fold/selection/counterfactual/training-workflow
acceptance is deferred. Do not label all 34 design IDs implemented PASS.

The 4096-record limit and immutable full fixture catalogue are explicit prototype
capacity/transport boundaries, not a claim that the API can replay full market
history. No historical-exact, fractional-contract, late-origin repair, imported
posting restatement>1, liquidation/ADL or real available-margin support is claimed.
Full-state market replay, historical/volume precision coverage, target exporter,
purge/embargo integration and statistical sufficiency remain separate gates.

The newer human choices (2026-10-01 economic cutoff; repair volume before research;
named clock/integer-ticket/multiplier scenarios; 0.075% main/0.15% stress/0.05%
reference costs) are future market-run configuration, not constants/defaults
inserted into this API. A helper test accepts explicit 0.00075/0.0015 fractions;
no market comparison was run. Volume source recovery/independent acceptance is
required before future market replay/labels/research. Fitting still lacks approval.

Only the four owned files change, including the specifically authorized B1 schema
amendment. No shared runtime/contracts/journals, QR files, original main, frozen
market evidence, live services or configuration changed. Candidate creation will
write only ignored synthetic inputs/actual API outputs with exact code binding;
the module itself has no writer. After publishing those identities, stop for QR.

## Published synthetic candidate and final handoff

Implementation commit: `69c8bf1d8a060ccdf0b103a3e3226c8f200dc960`.
Final receipt correction / candidate code commit:
`0ea2d51901689a351068bb9d33906c3240832afa`.
The source/schema/test hashes immediately above match both committed bytes and
the current worktree. The final report-only commit does not change that binding.

Ignored local candidate root:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd007/candidate-r3/`.
Manifest: `manifest.json`; SHA256:
`e9b3745fb33fb63043033a005cd87240acece29ac1c1daef37e42cc4ba23b2a7`.
The manifest binds exact code/schema/test hashes, QR schema review, B1 proposal,
verification scope and every output file's byte length/SHA256. It does not hash
itself or claim independent validation. These local files are deliberately
ignored and are not transported by a Git checkout; QR must use this exact root
read-only and verify its manifest before independently checking outputs.

Eleven JSON artifacts (592656 bytes excluding manifest) contain complete bound
synthetic configuration/source catalogue/records, explicit query inputs and
actual public API receipts, snapshots, readiness and audit outputs. They are
producer candidates, not financial oracles or market labels. Named scenarios:
A11 literal cash/funding; R01 two future-fact catalogues; R02 whole-batch rejection;
R03 causal proxy mark/late rate; R04 10/20/21/22 assertion heads; R06 cash with
unknown T; B1 entry, exit, both unknown and partial-slice restoration/refunds.
R05 and the remaining acceptance cases stay covered by producer tests; this
candidate set does not claim exhaustive independent acceptance.

| Artifact | SHA256 |
| --- | --- |
| `a11-literal-cash-and-funding.json` | `4522b2b8aaa5ab4c1a0fd54f47cdfade162f5afb1c236eda7b7a7e0012166c63` |
| `b1-both-fees-unknown.json` | `5deff06decc403f6083d9b81ffad8a45afb28a832ff8a76d6416481e6f756d1c` |
| `b1-entry-unknown-restore-refund.json` | `52ac277bdea68d945e1d572db69f5fe87a49ace6b61e74901f36a06ea8c513be` |
| `b1-exit-unknown-restore-refund.json` | `804d8321d69dce82d4f6f5c6ef5eff202bde60e166674f1fa108b14579214f8a` |
| `b1-partial-slices.json` | `0d426371c3366de52198b098b1f522a5f3c6aa0a7a184143b4376e40d4e923f0` |
| `r01-future-a.json` | `44f368445f6041a70220c80908e6582e35f1ffc5d36c2ec228e65128a06a2881` |
| `r01-future-b.json` | `0269e41a8c514c4496b17b0945501ab209a53d7650e591f66b7a4e5098b7e27c` |
| `r02-atomic-cross-record-rejection.json` | `3bc91d6968cbecd45e49dee06ea21af673cc18cc4d091d04aec3ca12eef9840f` |
| `r03-causal-mark-late-rate.json` | `24ecf01911d3207e92aa190e6428722d8b8df1add8217d7041347c0de290842c` |
| `r04-current-assertion.json` | `8cc4388721b56bf7c8ca0c0dd953b84d2cbb16d8bac8daffd72f97c57462641c` |
| `r06-known-cash-unknown-total.json` | `f008eced8209d43c4f328bfce521bc5f5085a89f196c7904a4fcae1838a8596f` |

Generation/reproduction checks used only the existing read-only interpreter,
standard library and own fixture constructors. Socket connects were blocked
before imports. All cases were generated in memory before exclusive file
creation; no prior candidate was overwritten. Each successful case replayed
identically twice, then with its input order reversed (including receipt/audit).
R01 snapshots at10 were identical across the two differently rehashed catalogues,
while audit hashes differed. The invalid R02 case retained its precise failure
receipt and unchanged committed state. Every saved file was re-read, hashed,
parsed and replayed through the public API against its saved outputs. All checks
passed. These are reproducibility checks, not an independent economic validator.

Minimal artifact replay, from this worktree with the manifest hash checked first:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import hashlib, json, pathlib, socket
def offline(*a, **k): raise AssertionError('QD007 offline only')
socket.create_connection = socket.socket.connect = socket.socket.connect_ex = offline
from research.qd007 import event_ledger as el
root = pathlib.Path('research/.data/qd007/candidate-r3')
raw = (root / 'manifest.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'e9b3745fb33fb63043033a005cd87240acece29ac1c1daef37e42cc4ba23b2a7'
manifest = json.loads(raw)
for path, expected in manifest['source_sha256'].items():
    assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest() == expected
for item in manifest['artifacts']:
    raw = (root / item['path']).read_bytes()
    assert len(raw) == item['bytes']
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
    candidate = json.loads(raw)
    c, out = candidate['inputs'], candidate['outputs']
    ledger = el.Ledger(c['config'])
    try:
        receipt = ledger.apply_batch(c['records'])
    except el.LedgerError as error:
        assert error.code == c['expected_error'] == out['error_code']
        assert error.receipt == out['failure_receipt']
    else:
        assert c['expected_error'] is None
        assert receipt == out['receipt']
        assert [ledger.snapshot(t) for t in c['snapshot_at_us']] == out['snapshots']
        assert [ledger.readiness(q['episode_id'], q['as_of_us'])
                for q in c['readiness_queries']] == out['readiness']
    assert ledger.audit() == out['audit']
print('11 synthetic candidate artifacts reproduced; independent QR validation pending')
PY
```

Final main preservation check again passed: HEAD
`cae0d2395adf2cd3905e41cb1c16748c8247c32c`, staged binary-diff SHA256
`c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`, actual
index-byte SHA256 `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.
No main work, production trading rules, QR files or shared journals changed.

QD implementation stops here. Coordinator can forward this exact code commit,
schema and candidate identities for QR's independently authored validator. Await
that result before any correction or next-stage work. No model/scaler fitting,
market intake/replay, target export, service operation, push, merge or integration
is authorized or implied by this candidate publication. Remaining gates and
prototype limits above still apply. Shared journals remain paused for reviewed
integration rather than concurrent edits.
