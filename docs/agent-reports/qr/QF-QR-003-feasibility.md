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

- `PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest tests.qr_research.test_qr003_feasibility -v`: **7 passed**.
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
- No new model fitted or promoted. No app/engine/credential/NAS operations.

## Next steps

Verify QD observer, run the bounded paired-asset audit, report limitations and D2 options.
