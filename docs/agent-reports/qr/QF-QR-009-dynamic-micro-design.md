# QF-QR-009-DYNAMIC-MICRO-DESIGN: bounded design handoff

2026-10-28. **DESIGN_READY_FOR_QD_REVIEW — implementation acceptance and training
readiness are NOT established.**

Task: `QF-QR-009-DYNAMIC-MICRO-DESIGN`.
Dispatch: `QF-DISPATCH-20261028-QR009-DYNAMIC-MICRO-DESIGN-1`.
Service-failure continuation: `QF-RESUME-20261028-QR009-DYNAMIC-MICRO-1`.
Targeted fidelity clarification: `QF-CONTROL-20261028-QR009-DYNAMIC-FIDELITY-1`.
No new task, agent, model, experiment or file allowance was introduced by resuming.

Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
Branch: `codex/qr-validation-baseline`.
Parent/base: `689414ca9714e020a48161bcec8fee402dfd365b`, initially clean.
The independent delivery commit adds exactly the three files below; its SHA is
reported with the final handoff rather than embedded recursively in this file.

## Completed changes and approvals

The coordinator relayed the human's confirmed U1 execution and U3 observation/
acceptance choices from frozen proposal `5dc72325580259ee8d578625f0ee33d0d13eec73`.
The human selected native dynamic risk budget ×10, replacing pending fixed5%
margin sizing. That selection is not reopened. Other U2 assumptions remain
unapproved until the concrete reviewed packet is confirmed.

The dynamic amendment specifies native allocation, conviction/adaptive risk/caps,
the 10% reference rather than current15% default, buffer scaling, ties-to-even
quantity conversion and partial/add/reduce/close behavior. It retires fixed
EntrySizingBook ticket/ratio clauses and preserves R01/R04 state/feedback guards.
The existing dynamic path lacks fixed-ticket-equivalent pre-increase funds/tier
checks; a minimal research validator is proposed, not described as implemented.
Gross allocation cap40 is a reviewed mapping proposal, not exchange leverage.

Following the fidelity clarification, qualified as-known `E=C+A-L+U` is the main
allocation/buffer candidate, consistent with native equity-based intent. Booked
C is an explicitly different alternative, never an UNKNOWN-E fallback. The
proposal distinguishes economic equity from cash affordability and discloses
differences from legacy backtest prices, fee/funding clocks and unverified real
exchange equity composition. Reserve/tier/capital/finality-reentry assumptions
remain a concrete U2 decision packet. Production defaults are unchanged.

The microstructure preregistration records official venue semantics, separate
units/settlement, immutable raw data, decimal/clock/availability rules, gap and
recovery masks, and a finite future public pilot. It defines four feature families,
mechanisms/confounds and a bounded six-arm baseline/venue/entry/exit comparison.
Weights/transforms remain unassigned until future authorized training-window
work; no best-of-many search or inference from tick counts. A short forward study
may be insufficient and cannot silently expand until statistically attractive.

Cross margin remains intended; neither proposal implements a shared BTC/ETH
account, liquidation or ADL. Independent per-asset returns cannot be combined as
proof of that account. Microstructure is a future independent direction, **not an
additional mandatory prerequisite for current historical training readiness**.

## Files added

| File | SHA256 |
|---|---|
| `research/qr009/dynamic-sizing-amendment.md` | `be76ac93aa1956ce611914dab99b41779be181c7dd46e29d4e5b7eadd2c9e7c0` |
| `research/qr009/microstructure-research-plan.md` | `87eb051b2df8ed5568706eb886dec69d1e309f9d70ab12df728622d3337de269` |
| `docs/agent-reports/qr/QF-QR-009-dynamic-micro-design.md` | Report hash emitted in final Git verification |

No old frozen proposal, native source, tests, configuration, QD contract or shared
journal was edited. Read-only source inspection did not transfer ownership:
QR owns `src/portfolio.py`, factors and `src/execution_timing.py`; QD owns execution/
systematic engine/config/risk adapters and existing shared tests. New future paths
are suggestions awaiting coordinator assignment, not approvals from QD.

## Checks performed and results

All computations below were bounded inline stdlib Python, with bytecode writes
disabled and socket create/connect/connect_ex blocked. Native, ledger, query,
collector and market strategy code were not imported or executed.

- Initial26 checks passed:18 literal/arithmetic examples and8 static checks.
  Examples cover parameter scaling, ideal scalar target840→8400 and buffer500→5000,
  strict buffer equality, nearest-even/min-lot behavior, a cap-overshoot
  counterexample, actual partial position, exact reserve14.6104, full-request
  rejection despite sufficient partial funding, fee-liability nonduplication,
  Gate fractional units, sequence bridge/gap, HL scoped identity, observed OFI,
  causal availability and finite resource/arm arithmetic.
- After the equity/ownership clarification,8 targeted checks passed: exact net
  E1024 vs cash budget982.3896 in a synthetic example, UNKNOWN E distinct from C,
  primary-E/no-fallback text, corrected exclusive ownership, source pins, format,
  unchanged DS01–DS12/MP01–MP12 registers, and no existing tracked edits.
- All14 frozen native source hashes and19 entries in the amendment's source/pin
  table matched current QR files and immutable base objects. The frozen r3 ledger
  text hash also matched; its FIFO active-episode and `E=C+A-L+U` behavior was read.
  Historical reported performance artifacts were not independently rerun.
- Required AGENTS/workflow/ownership documentation was read. Official HL/Gate
  documentation was browsed and linked next to facts in the research plan.
  No market endpoint, authenticated API or account/wallet subscription was called.
- Markdown fences, trailing whitespace, finite fixture IDs, allowed new-file
  scope, clean initial index and preserved source fingerprints were checked.
  Final staged diff and commit-content checks accompany delivery.

These checks validate arithmetic and the written proposal only. DS01–DS12 and
MP01–MP12 are finite **proposed** acceptance fixtures, not passed implementation
tests. No pytest run, benchmark, S01–S13 implementation acceptance, query run,
native market replay, dataset production, collector or model/scaler/calibrator/
weight fit occurred in this task. No dependencies were installed or upgraded.

## Known limitations and QD dependencies

1. R05 UNKNOWN invalidation/recovery remains QD's exclusive active amendment.
   Its moving draft was not read or edited here, and no R05 approval is issued.
   A fixed QD commit/hash must return for the separate QR review.
2. Dynamic increases need the proposed causal exact validator and accounting/
   availability integration. UNKNOWN E must suppress capital-dependent sizing
   without falling back to C; independently safe natural exits need explicit
   adapter coverage. No unreviewed change to native risk settings is implied.
3. Human-confirmed ×10 and U1/U3 do not approve initial10000, simulation margin
   divisor200, synthetic tiers, reserve predicates or finality/reentry adaptation.
   QD should review one concrete U2 packet, with qualified-E as the main proposal.
4. Legacy historical ETH results, chronology and cost differences do not establish
   future superiority or BTC performance. No multiplier was reselected from PnL.
5. Public finite-depth books cannot establish complete order-level flow or queues.
   Pilot timestamp/heartbeat/schema details require fixtures; lack of a contiguous
   trade sequence prevents proof of complete market trade history. Statistics
   require independent episodes/blocks, not the number of packets or updates.
6. Future collection and microstructure study budgets are proposals, separate
   from the unchanged historical8-scenario/18-path/24-attempt budget. Fit and
   actual training require a fresh human confirmation after readiness evidence.

## Preservation evidence and next steps

The main checkout was not written. Its observed fingerprints at the start and
pre-delivery audit are expected unchanged in final verification:

| Main checkout evidence | Value |
|---|---|
| HEAD | `cae0d2395adf2cd3905e41cb1c16748c8247c32c` |
| Index SHA256 | `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80` |
| Staged binary diff SHA256 | `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce` |
| Unstaged binary diff SHA256 | `35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d` |
| Full porcelain status SHA256 | `2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649` |

This is Git/staging preservation evidence, not a claim that ignored operational
files were read or exhaustively audited. No credential/config/account file was
read; only the explicitly permitted historical `agent.md` sizing excerpts were
consulted among ignored local files. No push, merge, deployment, live operation,
NAS/Windows change, process startup or cross-thread dispatch was performed.

Coordinator next: read this independent commit; send the proposal for QD review
under the existing coordination route, respecting R05 ownership; settle the
concrete remaining U2 packet; then allocate finite implementation/acceptance work.
QR stops after this design commit/report and does not contact QD or self-start a
next task. BTC/ETH only. Training readiness has not been reached; when evidence
meets it, report first and obtain the human's confirmation before any training.
