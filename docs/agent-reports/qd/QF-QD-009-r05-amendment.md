# QF-QD-009: bounded R05 authority/recovery amendment

2026-10-28 Australia/Melbourne. **READY_FOR_QR_REVIEW; DESIGN ONLY.**
This is the same adopted task `QF-QD-009-R05-AMENDMENT`, not a duplicate attempt.
No implementation, suite/benchmark, raw-query scan, native replay, label or fit
has run. QR must review the exact resulting contract before execution work.

## Allocation and review evidence

- Branch `codex/qd-cache-safety`; worktree
  `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
- Clean base `436b923f4ac046b9f032abcdc3d1df8f8593c0a6`. Only this unique report
  and `docs/interface-requests/qd-qf009-streaming-ledger.md` are writable.
- QR's forwarded human request was adopted by leader control
  `QF-CONTROL-20261028-QD009-R05-ADOPT-1`, tracking
  `QF-EXTERNAL-20261028-QR009-TO-QD-R05-1`. The active allocation was checked;
  no second worktree/claim, retry or cross-chat reply was created. Coordinator
  state was inspected read-only before the adoption control and was not edited.
- Exact QR review commit `689414ca9714e020a48161bcec8fee402dfd365b`, parent
  `5dc72325580259ee8d578625f0ee33d0d13eec73`, read as Git objects:
  `research/qr009/streaming-ledger-review-r2.md`, SHA256
  `b8e99c0eb506304be926e6740626dc812fd834308f9d862d64348be299232013`;
  `docs/agent-reports/qr/QF-QR-009-streaming-review-r2.md`, SHA256
  `000ac1e92d64ddf8f72b43cd8c7a317e0e73bcb955ca92b8f086426cd8527252`.
- Frozen QD N1/N2 report at436b923, SHA256
  `0ac0b76af5b1222f0969683da87b1c0ffbe6f44f4e0bba9259f4fe93b27381c0`;
  predecessor contract9c6d185, SHA256
  `d3adb32230ceb698d7a9d5372b412471586ec9341a93176a720110811fec927a`.
  These and all QR/native/r3/source files remain unchanged.

## Changes and offered closure

The proposal is now schema3 / `qf009-offline-stream-r3`, revision
`qd009-r05-amendment-2`. Old profile-r1/r2 stores/objects are rejected, not silently
migrated. New hash domains/view/checkpoint formats are explicit. RV01–RV04's
design acceptance from QR689414c is preserved; runtime acceptance is still pending.
The exact r3 FinancialBody/invariant block and76-code financial registry remain
byte-identical. Config/read/view/checkpoint additions are the bounded R05 delta.
Resulting contract SHA256:
`0db8014d162ec56f85eddafe289c869c8326f0ea5cbd226aef693050f259a745`.

| Requested item | Concrete contract change / required effect |
| --- | --- |
| N1 open shape | §4.3 maps QR's one-price-cell source Fact DTO to a separately named core schema with exactly open_us and open_price Cells, copying/checking original header time. H/L/C/V remain absent. |
| N1 MARK DTO/reasons/roles | Fixed15-Cell normalized shape: original six fields, status/reason and seven role bools. Five exact external reasons roundtrip via a known reason Cell plus existing generic unknown source/price Cells; no arbitrary Cell reason or fake price. Source/consumer clocks, canonical symbols/source key and DTO identity are explicit. |
| N2 authority identity | MarkClock/MarkViewBinding/MarkRequirement and QueryKey scope by instrument, clock, q and purpose. QueryStatus is controller-derived from the approved immutable Fact/requirement prefix, not fabricated by an adapter. |
| Before dependent slots | At every declared q, even without a Tick, derive status before slot0 views/dependent slots. Missing required evidence is a binding failure; legitimate UNKNOWN is data in an ACTIVE ledger. Its effect is in the shared Balance/EconomicView reducer. |
| Held versus flat | UNKNOWN/PENDING masks held U/E, MARK-dependent reserves and budget/risk support; independent fields remain known. Flat U0 and possibly E remain identities, but unsupported query still blocks its first entry. Consistent reductions/closure and settled scoped episode readiness remain available. |
| Recovery | Select the latest authoritative cohort by query time, never by source time. SUPPORTED125/source62 supersedes UNKNOWN121 without fake valuation origin or rewritten history. No null Valuation sentinel is generated. Other unknown claims can independently keep E/budget null. |
| Reserve masking | Immutable ReserveDependency identifies independent/current_mark margin and fee aggregates, validated with the registered formula. UNKNOWN hides only dependent fields; recovery needs a current known measurement for MARK-dependent reserves, preserving ordinary recomputation/expiry. Independent zero reserves yield QG02 budget999 directly. |
| History / non-tick / tail | Reads create no lookup. They choose the past cohort and evaluate true source/available age and expiry. Restated past time cannot import a later query price. Tail admits no current query and preserves stored evidence/unknowns/flat identity. |
| Binding / hash / restart | mark_context supplies complete typed statuses/dependencies; two new retained paged components and QueryCursors join view roots/checkpoint. Restore recomputes membership/authority from the accepted prefix; UNKNOWN cannot reset. Audit hashes stay outside economic inputs; CONTROL stops remain monotone. |

This is a view/status supplement under a new explicit profile, not a change to
cash, T/B/P/A/L, FIFO, posting/finality or FinancialBody origin semantics. Common-
domain fixtures without query bindings retain original financial values. QG01's
stricter qualified UNKNOWN is an intentional profile result; no differential
alias hides it. Native error/field/codec/query qualification identities remain
separately reviewed registration prerequisites, not undocumented runtime fields.

## Finite QG mapping; no larger register

§8.2 explicitly proposes the following changes for QR review. All90 existing IDs,
118 fixture instantiations, seeds NONE and attempt counts are unchanged. Only two
existing one-fixture S10 tapes gain the required query-state coverage:

- **S10.08 / QG01:** BTC, B-relative queries50/51 select source-10/availability50,
  price100; first supported query gates the entry. Query65 crosses the absent
  required new month although old source age75/available age15 still pass. Current
  held U/E/budget become null before the dependent slot. The explicitly declared
  synthetic reserve measurement has independent margin7, MARK-dependent fees.1;
  margin stays7, fees become null. C1000/units/claims are unchanged. Checkpoint65 /
  restore / non-tick66 retain UNKNOWN; old views and repeated-source clocks remain
  exact. Flat pre-entry budget1000 and held pre-mask budget992.9 are explicit.
- **S10.09 / QG02:** ETH, source0@100/a60 and source62@99/a122. Query120 supports
  the old source at equality; query121 is genuinely unknown; after checkpoint /
  restore, query125 supports source62. U=-1, E999, budget999 with independent zero
  reserves. Prior121 remains unknown. A final new financial body available120
  behind sealed125 still rejects PAST_AVAILABILITY without committing changes,
  retaining the original S10.09 negative coverage in the same fixture.

Each stays within64 bodies/16 market Facts/8 ticks/4 slots per tick/2 checkpoints/
16 reads. The source proof is a synthetic literal premise, not an actual raw
query. The coefficient.001/m1/executed fee0 test values are not a new market
parameter or a capital/sizing recommendation. Five-reason/seven-role mapping
coverage is statically specified; these tapes exercise their stated actual
queries, not additional hidden fixtures. Exact fixture bytes/expected tables and
normalizer identities must still be pinned before the single permitted suites.
S09.01 mechanically changes the unknown-version literal3->4 for the new schema;
its two replicas/rejection remain unchanged. All other case rows are unchanged.

The initial eight producer benchmarks at512/2048/8192/32768 twice each still have
60s each/480s total. The two functional suites remain120s each ->720s total,
RSS256MiB/cache8MiB/aggregate new output2304MiB, with all prior absolute/growth
limits. QR checks saved benchmark artifacts, not eight new timing runs. New status /
dependency logical rows, reads, persistent bytes and recovery count under the
same caps. S13 is still NOT_EXECUTED/BLOCKED_NATIVE_PORT under its separate future
finite register. No case deletion, cap increase, automatic retry or new runtime
Q_i time/scenario/path follows from this amendment.

## Verification and preservation

Checks actually performed are static Git/text/type/manifest comparisons and small
stdlib literal calculations only: exact review hashes; current branch/base/scope;
unchanged r3 financial/error blocks;90 IDs/118 replicas; version/reason/role/type
references; fences/whitespace; unchanged register arithmetic; QG clock eligibility,
mask/recovery and exact U/E/budget literals. The report's final commit identifies
the exact resulting contract bytes; hashes are reported at handoff.

No initial functional suite, benchmark, fault injection, native wrapper/state run,
MARK/latest-eligible scan/query, replay, labels, feature/model/scaler/calibrator
fit, dependency installation, app/engine launch, credential access or service
operation was performed. Static/literal PASS is not implementation acceptance.
One draft text-lint predicate matched a legitimate positive .05 funding literal;
the formatting check was narrowed without changing that financial fixture. Final
static/literal checks passed; this was a checker issue, not a runtime test failure.
No source/main merge, cherry-pick, push, deployment, NAS or Windows work.

Original source preservation witnesses before/after: main HEAD
cae0d2395adf2cd3905e41cb1c16748c8247c32c; staged binary diff SHA256
c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce;
unstaged diff SHA25635d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d;
full porcelain/untracked status SHA256
2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649.
These are Git/staging witnesses, not a new raw/private-file census.

## Current user decisions and remaining gates

The later control USER-SIZING-DIRECTION-1 supersedes old all-pending wording:
U1 execution and U3 observation/finite validation are approved. U2 is now the
native dynamic-risk-budget x10 research candidate; its precise versioned sizing,
capital/reserve/reentry policy remains QR-owned and pending. The old fixed5%
ticket proposal is not approved. This generic amendment implements neither,
changes no production risk/leverage/default and starts no collector. BTC/ETH
remain the only research instruments. No hidden fourth human type question.

Next is one independent QR exact-object review, including this explicit finite
manifest mapping. Only after design acceptance and separately registered bounded
dispatch do implementation/verification proceed. All34 QF006 criteria remain;
native S13, actual complete-prefix query proof, full-state market replay, natural
episode labels/finality/purge/statistical sufficiency and frozen prospective
feature/model/evaluation plans remain outstanding. Tell the user when training
conditions are reached and obtain fresh explicit confirmation before any fit.
This task stops at READY_FOR_QR_REVIEW. Coordinator reads the result; no cross-chat
reply or automatic next task is authorized. Result commit is the one adding this
report and changing only the allocated contract.
