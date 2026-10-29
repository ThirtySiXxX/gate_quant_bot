# QF-QR-009 streaming contract: independent r2 review

2026-10-28. **REVISE — one remaining R05 query-status binding.**
RV01–RV04 are closed at the design-review level below. The remaining request is
to specify how a required UNKNOWN MARK selection invalidates the authoritative
view and how later qualified selection restores it. This is a static contract
gap, not an observed implementation failure. No implementation, benchmark,
native/query acceptance, market replay, label generation or fit was run.

Dispatch `QF-DISPATCH-20261028-QR009-CONTRACT-R2-REVIEW-1`; task
`QF-QR-009-STREAMING-CONTRACT-REVIEW-R2`. This is the first rereview after the
first contract amendment. It does not reopen the accepted financial rules,
approve research assumptions or allocate implementation files.

## Exact objects and review scope

The complete 1637-line Git object was read, not a moving workfile:

- Target `9c6d18559e35377d45f0bfc951ab4cbce20cc202`, parent
  `89cf347482c8121a4e3da559c6fb639a30788d6f`; its only changed file is
  `docs/interface-requests/qd-qf009-streaming-ledger.md`.
- Target SHA256 `d3adb32230ceb698d7a9d5372b412471586ec9341a93176a720110811fec927a`.
  All target line references below refer to these bytes: schema_version2,
  profile `qf009-offline-stream-r2`.
- Prior QR review: `4d4e5304be7646e0a4520f4ec8512a7890f847a4`,
  `research/qr009/streaming-ledger-review.md`, SHA256
  `a141bbf5ed69663b2db29ba0c7acffd41712c730eb0c0ce08ad166e6efa8578e`.
- QD engineering review: `89cf347482c8121a4e3da559c6fb639a30788d6f`,
  `docs/agent-reports/qd/QF-QD-009-replay-engineering-review.md`, SHA256
  `8ca4301e21aa599f97fde432695a5b40bfbcb8a58e03751f089430e2d3325e3e`.
- QR proposal r2 remains frozen at
  `5dc72325580259ee8d578625f0ee33d0d13eec73`. Its section7.1 explicitly requires
  current UNKNOWN propagation and later recovery, not merely unknown Fact cells.
- The unchanged r3 source was inspected as text at
  `0ea2d51901689a351068bb9d33906c3240832afa:research/qd007/event_ledger.py`,
  SHA256 `7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636`.
  It was not imported or executed. Historical contract `19cd4c7e461799b9b9a13fef2028902e8dfcd48c`
  supplies the financial-payload/error-registry comparison.

## RV01 — ACCEPT DESIGN: complete cross-port input and state transport

Evidence: target lines442–484,535–581,650–770 and1128–1165. The amendment supplies
typed live lots, orders, decisions, financial changes, episode rows and declared
peer/own states. Fixed selectors specify complete membership, source cutoff,
ordering and role allowlists. Controller-owned selection bindings and the full
read inventory reject a rehashed omission; hashes do not substitute for values.
OrderRecord totals derive from actual distinct Fills, with immutable intents,
partial/cancel/expiry states and terminal-transition restrictions. Each state has
one writer; owner feedback precedes dependent decisions and the whole tick commits
atomically. Oversized complete packets stop rather than truncate. Orders,
decisions, states and invocation cursors survive checkpoints.

This closes the prior P-at10/X-at20/environment funding-input counterexample at
the transport level. Separate roles can obtain actual intent and FIFO ranges
without private scans, hidden state copies or decoding roots. Policy cannot
consume execution_open; audit paths/hashes cannot become numerical inputs.

Remaining implementation acceptance: S02.01–.04, S04.03–.07, S07.02 and S12.02–.03
must demonstrate complete membership, actual partial/cancel quantities, correct
predecessor peer state, causal reads and interrupted continuation. Registered
schemas/validators remain mandatory. A placeholder state is not the native state
inventory; S13 must later exercise the actual timing/sizing/feedback/pending-order
books. None of these tests has run in this review.

## RV02 — ACCEPT DESIGN: original-clock context and lifecycle boundaries

Evidence: lines310–361,399–431,832–854 and1128–1165. InitialContext separates
pre-account closed facts from financial origins. Original availability remains
unchanged; ContextReceipt separates semantic prefix from audit binding; cursors
deduplicate initial admission. Availability equal to genesis belongs to the first
normal release. Required unresolved context rejects before initialization. The
first controlled initialization uses the evidenced prefix once, including after
restart. The exception cannot admit a later backdated delivery or hidden feature
capsule. The financial calendar excludes the proposed2023 warmup; account activity
still starts at its declared2024 origin.

The R03 cutoff connection is also acceptable as a transport design. Reserves
expire no later than end, invalid at equality. A typed lifecycle slot can cancel
orders/update state with events=[]; no new Fill, Valuation, Reserves, snapshot or
decision origin is introduced. Tail selectors supply no fresh market/feature
inputs; only permitted old-origin evidence and saved state are used. Open exposure,
stale U and expired-reserve/null-budget consequences remain visible. Flat U=0 is
an identity, not proof of supported reserves or a new order.

Remaining acceptance: S03.03–.07, S09.06–.07, S02.05 and S10.04–.06, followed by
actual native prefix/initialization parity in S13. Test before/equal-genesis facts,
future-only catalogue perturbation, both restart positions and cutoff equality.
The actual scenario's tail duration and native lifecycle state remain separate
QR/QD/user decisions; this review does not select them.

## RV03 — ACCEPT DESIGN: durable resolution and persistent stops

Evidence: lines916–962,1192–1296. resolve_commit operates under the single-writer
lease, validates reachable committed manifests and exact request identity, and
re-establishes required file/directory fsync plus close/reopen readback barriers.
Readable cached HEAD or an orphan request cannot establish commitment. Continued
barrier failure stays unknown; a durable predecessor with no reachable request
can establish noncommit; conflicting request hash remains a conflict. The saved
ReceiptCore reconstructs one receipt without re-executing financial transitions.

CONTROL is recovered independently of an old checkpoint. Durable pre-validation
guards retain exact input; an interrupted unclassified guard cannot be discharged
merely by proving financial noncommit. Bounded validation must classify it or leave
the run blocked. Integrity/resource stops are monotone, survive a failed stop
publication through the durable guard, and outrank the I/O guard. Resolution cannot
clear them or reset spent resources. A failed initial guard barrier is explicitly
unusable rather than falsely acknowledged. This closes both prior RV03 examples
as a specification, without claiming a filesystem durability result.

Remaining acceptance: all S08.01–.11, S09.05 and S12.04/.07, including the two
continued barrier failures, successful repeated resolution, orphan/wrong-hash
cases, forged projections, stop after old ACTIVE checkpoint, failed CONTROL
publication, and interrupted suffix recovery. Actual injected fault behavior,
atomic receipts/cash and budget accounting still require independent checks.

## RV04 — ACCEPT DESIGN: finite initial inventory and separate native gate

Evidence: lines1353–1545. Static extraction found exactly90 unique contiguous
S01–S12 case IDs and the declared118 fixture instantiations per functional suite.

| Group | Named cases |
| --- | ---: |
| S01 / S02 / S03 / S04 | 12 / 5 / 7 / 8 |
| S05 / S06 / S07 / S08 | 5 / 7 / 3 / 11 |
| S09 / S10 / S11 / S12 | 7 / 9 / 9 / 7 |

The manifest retains R01–R06/B1, separate P/X/environment, pre-initial context,
long history and growing pending sets, exact arithmetic, true query times,
durability faults, invalid inputs and explicit resource rejection. Seeds, variants,
replicas, clocks and size overrides are finite. The8192-body and512-body hard tapes
have concrete constructions. This is adequate for independent fixture/oracle
preparation; it is not proof that the implementation fits the limits.

The unchanged register is eight producer measurements at N512/2048/8192/32768,
two each,60s each/480s total, plus one120s producer and one120s QR functional suite:
720s total,256MiB RSS,8MiB cache,2304MiB aggregate new output and the frozen
transaction/page/read/state limits. QR checks the eight saved benchmark artifacts
and ratios inside its own120s suite, without eight additional timing runs. No
automatic retries, discarded outliers, reduced case universe or larger limits.

Remaining acceptance: pin fixture bytes, literal expected states and exact error
paths/reasons before execution, independent of producer results. Preserve the
three-port S02 manifest and bind any illustrative S02 overview to those named
cases; do not silently run an extra toy trace. Conflicting expected literals need
review. Run each permitted suite once only after dispatch; record each outcome and
every failed/partial artifact. S13 remains outside the90 cases as
NOT_EXECUTED/BLOCKED_NATIVE_PORT/R3_NOT_READY, with its own future finite register.
The R05 regressions below also need an explicit reviewed register mapping; this
review adds no hidden fixtures, attempts or resource allowance.

## R05 — REVISE: connect query qualification to authoritative view and recovery

Accepted portions: lines365–397 distinguish execution-only open facts from closed
OHLCV and distinguish selected raw source time/availability a from consumer q.
qualified_at_slot supplies all required per-q results, including unknowns;
absence is a binding error. Lines772–789 keep stable semantic identities separate
from raw-file hashes and correctly block unassigned native/query schemas. Known
repeated-source selection is covered by S10.08/.09. None of those rules proves
complete-prefix/latest-eligible raw support; that remains an external gate.

The unresolved link is narrower: a mark_selection Fact is not a FinancialBody or
an authoritative query-status component. EconomicView retains the ledger Balance;
its declared financial projection still uses r3 Valuations. The contract does not
specify which current selection invalidates that Balance, when it takes effect
relative to dependent slots, or how the next supported query removes the invalid
state. A generic output validator/no-new-risk noop (lines609–614) can stop an order
but does not define authoritative U/E/budget or historical/checkpoint semantics.
No case in S10 tests required UNKNOWN followed by qualified recovery.

This matters even when the old financial valuation is recent. Two finite static
counterexamples follow; they are requirements reasoning, not executed fixtures or
claims about accepted raw data. All offsets below are seconds converted to integer
microseconds. Let B be a declared month boundary, choose initial<B-20 and an end
after all shown times, and use one held long contract, m1, entry100, C1000, known
zero liabilities and zero reserves valid beyond the example. Source delay60s,
source age limit120s and available age limit60s are the existing proposed primary
clock illustration; no new market parameter is approved here.

### QG01: required missing interval while the old valuation is still age-valid

At q=B+50, the complete source interval [B-70,B-10] is available. The latest
eligible point s=B-10, a=B+50, price100 is qualified and has an existing financial
Valuation at source s, known/available q. At q=B+65, the required eligibility
interval is [B-55,B+5]. Declare the new month's source file absent while the prior
month is present. The old point still passes both age checks: source age75s and
available age15s. Nevertheless the complete-prefix query is UNKNOWN for the
missing required month; it cannot prove absence of a later eligible point.

The amendment can transport four unknown selected-source/value cells at B+65.
It does not bind their effect on the financial view. If an environment port emits
no FinancialBody, unchanged r3 projection gives U0/E1000/budget1000 and
new_risk_supported=true. A port-local risk veto would not make the authoritative
view null. A global hard integrity stop is also not the specified behavior for a
legitimate unsupported query. Required behavior: keep C/inventory/obligations
unchanged, propagate the required MARK uncertainty to held U/E/budget and any
MARK-dependent reserves, forbid new risk, preserve consistent reductions, and
retain the previous as-known result. Independent known reserves need not be
invented as unknown merely because MARK is unknown; the binding must state which
reserve calculation actually depends on this selection.

### QG02: a query-time null Valuation can prevent legitimate recovery

Use a separate fully covered sparse source with points s=B (price100,a=B+60)
and s=B+62 (price99,a=B+122). At q=B+120 the first point is eligible at equality.
At q=B+121 it is stale and the second point is not yet available: required query
UNKNOWN. At q=B+125 the second is eligible, with source age63s and available age3s.

If UNKNOWN is translated into Valuation(mark_price=null, valuation_at=B+121,
known_at=available_at=B+121), then recovery emits a known Valuation with
valuation_at=B+62 and known_at=available_at=B+125. Frozen r3 selection at
event_ledger.py:735 orders by (valuation_at,available_at,record_id); the null
B+121 origin outranks the valid B+62 origin. U/budget remain unknown instead of
the required U=-1/E999/budget999. Retimestamping the known source to B+125 would
violate the accepted source-clock rule. Putting the null at the old known source
B is not a general escape either: r3 lines490–493 reject a different mark_price
at the same (instrument,valuation_at) as AMBIGUOUS_VALUATION. These are properties
of the frozen source, not a runtime assertion that a future port chose this mapping.

### Bounded amendment requested

QD should specify one reviewed query-scoped qualification/status binding, or an
equivalent explicit representation, with all of the following:

1. Typed identity and authority by instrument/clock/query/consumer purpose; exact
   known/unknown reasons or a closed, lossless mapping to the core Cell registry.
   Resolve section3's generic Cell reason list versus section3.2's external query
   reasons before registration. Missing required status remains a binding error.
2. The exact transition into the authoritative Balance/EconomicView before any
   dependent policy/execution/funding/reserve slot, including the flat-account
   first-entry gate, known versus MARK-dependent reserves, true non-tick queries,
   and the existing evidence-only tail. A private state flag alone cannot override
   a still-known public balance without specified projection semantics.
3. Recovery under a later qualified selection without backdating, overwriting the
   old as-known view, fabricating a source clock or leaving a newer null financial
   origin dominant. Preserve actual cash, units, obligations and r3 common-domain
   semantics. Frozen r3 code is not to be edited.
4. Causal economic hashing, complete controller bindings/read accounting, retained
   status/cursors, restart and future-only perturbation behavior. Raw audit hashes
   must still not affect earlier financial/native decisions.
5. An explicit finite acceptance mapping for QG01/QG02, including interrupted
   UNKNOWN/recovery and the intended error/reason/status output. Preserve the
   accepted90/118 initial inventory unless a finite revision is explicitly reviewed;
   do not silently append cases/attempts, drop existing coverage or raise caps.

No scanner, broad ledger rewrite, market run or numerical scenario change is
requested. If QD instead deliberately defers this representation, the known gap
must remain an explicit unimplemented contract dependency, with native registration
and its implementation blocked until a versioned amendment is reviewed. The current
target cannot be described as having closed R05 unknown propagation/recovery.

## Preserved decisions, remaining gates and evidence

The exact FinancialBody/invariant block and76-code r3 error registry match the old
contract byte for byte. Exact C/T/B/P/A/L, FIFO, signed residual allocation, B1
nullable fee attribution, late corrections/refunds, old as-known immutability,
version rejection, source/consumer clocks, stable identities and QF006's34 criteria
are retained. No permissive reinterpretation is needed to close R05.

Static checks:15/15 passed for target hash/parent/one-file scope/1637 lines,
unchanged financial block/error registry, unique contiguous case IDs and replica
membership/count, balanced fences, resource arithmetic and the clean QR base.
Four additional independent stdlib literal clock/ordering checks passed for
QG01/QG02. The frozen r3 source hash was verified. Socket connect/create_connection
were blocked; only documentation/Git text and stdlib arithmetic were used. These
19 checks are not S01–S13 results or a query/ledger/native test run.

All S01–S13 remain NOT_EXECUTED in this task. Initial producer/QR functional
suites, eight benchmarks, fault injections, exact native port/full-state S13,
complete-prefix MARK query validation,18-path market replay, labels and fit are
also NOT_EXECUTED here. S13 remains R3_NOT_READY. QR's U1–U3 scenario proposals
still need the prescribed review and human choices. R4 label/finality/purge/sample
sufficiency and R5 frozen training/evaluation plan remain later gates. Training
readiness has not been established; fitting any model/scaler/calibrator requires
fresh human confirmation, and no candidate activation follows automatically.

Next: coordinator may request one bounded QD R05 amendment and return its exact
commit/hash for review, respecting the existing two-amendment-round limit. Do not
restart RV01–RV04 or infer permission to implement/run from this report. QR edits
only this review and its role report, commits independently, and stops. QD owns
the eventual integration of shared journals; no cross-chat reply, merge, push,
main-checkout edit or deployment is performed.
