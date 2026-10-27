# QF-QR-003 Phase A feasibility audit

State: IN_PROGRESS
Role: QR
Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`
Branch: `codex/qr-validation-baseline`
Base: `7650d59cc2983394c38ea8fa5bd102ca90288017`

User approved Phase A with BTC and ETH on 2026-10-28; model training waits for D2.
Exclusive QR paths: research/qr003/protocol-proposal.md, feasibility_audit.py,
research/qr003/results/, tests/qr_research/test_qr003_feasibility.py, this report.
QD observer, infrastructure, source, shared journals and original checkout are not QR edits.

## Work and dependencies

- r2 records BTC/ETH independent-account scope, fixed dates, bounded skip probes,
  unchanged production settings, missing BTC inputs, and training decision gate.
- Corrected r1 terminal timing: execution.time already uses bar close; trade.close_time
  uses bar open. Terminal outcomes remain censored.
- Developing independent ledger/label/feature/coverage checks using old ETH evidence
  and synthetic fixtures while QD supplies the approved observer and BTC inputs.
- Full Phase A acceptance requires both instruments and verified probe trajectories;
  existing trade-only results cannot establish complete pre-ML opportunity coverage.

## Tests/results

Preflight complete, full observer acceptance pending.

- `PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest tests.qr_research.test_qr003_feasibility -v`: **11 passed**.
- Frozen QR-001 inputs: **9/9 SHA256 match**. ETH saved baseline execution hash still
  `c305f8477860be4b3fddbfef1b52113b163caa8b7a6fd5c39c689dcbdcafda1e`.
- Independently reconstructed position cash flows, including partial-reduction test
  vectors and signed funding. Saved ETH result reconciles within 3.41e-12 USDT.
- ETH archived ledger: 32 positions, 31 natural labels, 1 terminal censor; all 32
  entry times have available 21-feature vectors. Mature labels before old fold starts
  remain 0/7/18. The 24h-buffer overlap diagnostic yields 11 connected time clusters;
  this is **not** an effective independent sample-size estimate.
- `research/qr003/results/archived-eth-preflight.json` preserves these results as
  explicitly archived-ledger evidence; no new full replay is claimed by this file.
- Added input-quality coverage tests: ETH has no missing/stale input decisions in
  the evaluated interval. Funding timestamp offsets of 1–3 seconds are retained;
  one hourly observation-step grace applies only to completeness diagnostics.
  Funding warmup still starts later than 4h history and remains disclosed.
- No new model fitted or promoted. No app/engine/credential/NAS operations.

## Exact QD candidate review

Reviewed QD `1a2bf705050a0fdc4f47da7e834487f3c37cd800` relative to
`144ce5b75f9548c471cf537425cb7d3847fa3311`. The delta contains only the
probe, its synthetic tests and QD report. Current file matches committed bytes;
probe SHA256 `4a0e520fa7b0a98565435aec07936bd4425592850a6e2e64b2116acd7d1d45aa`.
QR independently reran **12 QD synthetic tests** with socket connections blocked,
and **11 QR tests + 4 existing causal signal/timing checks** passed.
No extra stateful decision calls, global monkey patches or copied simulation loop.
Reviewed state ID is digest of `{observed: state_before, position_before: ...}`;
QR rejects an obsolete state-only hash and corruption rather than relaxing checks.
The original skip/minimum-quantity diagnostic artifact is classified by explicit
probe flags, not treated as a genuine budget rejection or zero-return sample.
Full two-asset path acceptance is pending the following frozen runs.

## Next steps

Verify QD observer, run the bounded paired-asset audit, report limitations and D2 options.
