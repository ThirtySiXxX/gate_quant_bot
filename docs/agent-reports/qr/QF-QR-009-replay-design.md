# QF-QR-009 R3 design and streaming-contract review checkpoint

2026-10-28 Australia/Melbourne. **A–C DESIGN PROPOSED; D REVIEW = REVISE.**
Task QF-QR-009-R3-DESIGN; original dispatch
`QF-DISPATCH-20261028-QR009-R3-DESIGN-1`, continuing controls
`QF-CONTROL-20261028-QR009-QD-EXACT-CONTRACT-1` and
`QF-CONTROL-20261028-QR009-AC-CHECKPOINT-1`.
QR worktree `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`,
branch `codex/qr-validation-baseline`; clean start
`0a90b2555db8e16934053abff31db29bac4296a2`.

A–C exact commit **946e9fcbe2e10c1de3f51efea5f17d7395cd2067** contains only protocol
and JSON. D/report checkpoint is the commit containing this report; resolve with
`git log -1 --format=%H -- docs/agent-reports/qr/QF-QR-009-replay-design.md`.
No shared-journal update, cross-chat reply, merge or push was performed.

## Completed changes / exact file scope

Only four newly allocated QR files; all previously tracked QR files are unchanged:

| File | SHA256 / content |
| --- | --- |
| `research/qr009/replay-protocol-proposal.md` | `e5e9bf76364fa6807e9de3f78ba14de2f80a928522a3a121d9d6e428f289245f`; concrete execution/account/query/projection proposal and three draft user-choice packages |
| `research/qr009/replay-spec-proposal.json` | `da7517514a2973c2abb3ac2ff557b77c898c6d0098bcac629443e97d3d225b52`; complete candidate parameters, versions/hashes, finite matrix/budgets, all execution/fit permissions false |
| `research/qr009/streaming-ledger-review.md` | `a141bbf5ed69663b2db29ba0c7acffd41712c730eb0c0ce08ad166e6efa8578e`; nine ACCEPT directions, four REVISE items, four future BLOCKED gates and file-allocation review |
| This report | Git object in the final checkpoint identifies its exact bytes. |

Read/refreshed AGENTS and six workflow documents, the full QD008 preflight at
d90e368, frozen QR006 requirements and relevant unchanged native policy source.
Verified coordinator requirement-index/funding-lineage hashes. The requirement
index predates final QR008 R2 acceptance; it does not replace newer exact evidence.
No QD009 dynamic content was read before exact handoff. After it arrived, read
all998 lines of commit19cd4c7e461799b9b9a13fef2028902e8dfcd48c target
`docs/interface-requests/qd-qf009-streaming-ledger.md`, SHA
`36a7b157cdba45692b6737ba465d7b2bf4e29b9d2a012a52b67d454fb1c02ac7`;
Git-object/workfile identity and single-new-file commit scope matched.

## Proposed research behavior (not approved choices)

Retain approved BTC/ETH scope, source segmentation, time window, fee fractions,
MARK clocks, funding clocks and integer multipliers. New recommendations:

- Hourly decisions,1s latency to next hourly open,5bps adverse slip; capacity is
  floor(0.001×previous closed hour's exact contract volume), one fill opportunity
  then cancel remainder. Execution-only retrospective open is an explicit new
  simulation assumption; new-hour H/L/C/V stays hidden until close.
- Independent10000USDT accounts,2023 indicator warmup,2024 account start; booked C
  feeds unchanged native allocation/tickets. Exact held/pending margin/fee/slippage
  buffers and synthetic sizing tiers are declared; unknowns block increases while
  supported natural exits remain. No real margin/liquidation survival claim.
- A material new adapter rule waits after natural flat for complete cash-settled
  episode finality before completing native session-PnL/rearm feedback and reentry.
  Unknown is not zero, late refund cannot rewrite past rearm.
- Preserve native4h bar-open sampling of newly delayed rates;28800s is a named
  8h-equivalent annualization unit, not an inferred actual event calendar. Propose
  two-hour evidence-only tail; no new market observations/decisions there.
- Eight fixed one-factor scenarios and18 full-state paths, at most24 started
  attempts including failures; finite clock/CPU/RAM/disk caps. No Cartesian tuning.
- A path-independent MARK superset bounded by279276 lookups across both assets/
  clocks, with complete-prefix/latest-eligible independent checking and actual-query
  subset hard gate. Raw gap hit rate remains NOT_EVALUATED.

Section10 groups material choices into three plain-language draft questions for
coordinator use after QD engineering review. No user choice was assumed or asked
on behalf of the coordinator. All native/default/old contract formats remain intact.

## D review outcome and budget separation

REVISE the exact QD009 contract on four finite points:

1. **RV01 complete controlled inputs:** input contains roots/Balance and only own
   adapter state, but distinct execution/environment ports need stored order intent
   and actual live FIFO ranges. Define bounded authoritative projections/communication
   and input witnesses; no hidden global state or untyped scan bypass.
2. **RV02 initial warmup:** clarify admission of original-clock context facts before
   account initial_at without backdating financial transitions or hiding precomputed
   state. Test2023 warmup with2024 account start and no warmup trades.
3. **RV03 durable commit resolution:** specify barriers after post-HEAD fsync failure,
   committed-chain/request-hash checks and persisted stop-latch recovery. Readable
   cached HEAD is not itself re-established durability; no blind cash retry.
4. **RV04 finite acceptance inventory:** freeze bounded S01–S12 cases and suite
   ownership; initial S13 is NOT_EXECUTED/BLOCKED_NATIVE_PORT, with a later separate
   native gate. No hidden extra QR benchmark runs or unlimited failed-case retries.

Accepted directions include noncircular view/receipt preimages, actual-time
non-tick age/expiry/calendar checks, exact r3 financial semantics, late revisions,
causal provenance/typed port trust boundary and explicit S13/R3 separation.
These are static design judgments; all S01–S13 remain unexecuted.

The initial **ledger engineering** proposal is QD009 section8:8 producer timing
attempts (512/2048/8192/32768 twice),480s plus two120s suites=720s;256MiB RSS,
8MiB cache,2304MiB total outputs and its stated growth/operation limits. QR accepts
those proposed ceilings subject to RV04; feasibility is unmeasured. A–C946e9fc
explicitly supersedes its earlier uncommitted16K/32K/64K alternative. The later
QR query/native/18-path market resource caps are a separate proposed R3 stage;
they do not enlarge/retry the initial ledger register. No benchmark was run.

## Tests/checks actually performed

All Python used the existing interpreter read-only:
`PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python`.
Socket connection methods were blocked before other imports. Stdlib only; no
native/app/training imports, dependency changes, market raw scans or engine start.

Initial **21 document/literal checks passed**: calendar/matrix, one-factor choices,
strict-next-hour clocks/posting/finality/tail, next-open latency, symbolic query
closure/count, exact reservations/asymmetric budget/fractional-volume floor,
A26/A34 literal examples, carry units/lag, disabled permissions,14 native pins,
approved constants and source/QR preservation. These are not end-to-end tests.
Artifact `/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qr009-design-audit-1/result.json`,
SHA `a8a4a12377675d6c0c9c0f2b564caa6630021be08d5e6d0be15dcc1323f1e6e9`,
binds an earlier uncommitted candidate4339fbfb. Subsequent changes were documentation/
identity binding, initial-ledger budget alignment and exact D handoff, not runtime work.
Do not claim that earlier audit hash binds final files.

**28 final document/literal/identity checks passed**, using the saved stdlib script
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qr009-design-audit-1/final_checks.py`
with the interpreter above; its exact command/input is reproducible there.
`final-check.json` in that folder binds final three artifact hashes, A–C commit,
QD target identity, strict JSON/types/permission/count/clock/resource checks and
source preservation. `git diff --cached --check` and exact staged two-file scope
are checked before each independent commit. No market query/support rate, replay,
label, S01–S13 test, benchmark or fit is counted as performed.

Source main remains cae0d2395adf2cd3905e41cb1c16748c8247c32c. Preserved staged diff
SHA c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce;
unstaged35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d;
porcelain2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649;
index7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80.
These are Git-state checks, not a fresh rehash of the coordinator's78 source files.
All old QR008 and QR007 artifacts/native source remain unchanged from starting HEAD.

## Limitations, dependencies and next steps

No execution/scenario hypothesis is approved by this checkpoint; new numbers and
feedback behavior await QD feasibility review then user confirmation. Historical
arrival/depth/tiers/maintenance/liquidation truth is not established. Query support,
scaling and full native causality/feedback are still unverified. An accepted design
subitem cannot be reported as implemented or as all runtime/model approval.

QD should amend only its assigned contract for RV01–RV04, return an exact commit/
hash, and review A–C's fixed Git objects independently. QR rechecks the new exact
contract; coordinator handles file allocation and consolidated user questions.
Then separately authorize implementation/checkers, finite queries and R3 replay;
R4 must validate natural labels/finality/selection, strict24h/cross-asset purging
and training-only information sufficiency. R5 freezes model/features/budgets/
metrics and an actually prospective evaluation reservation.

**Training is NOT_READY. Notify the user when all gates pass and obtain fresh
human confirmation before any model/scaler/calibrator fit.** No automatic next
stage, model activation, source/main integration, deployed NAS/Windows operation
or cross-chat reply. Stop after these independent review checkpoints.
