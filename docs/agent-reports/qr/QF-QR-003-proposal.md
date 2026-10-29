# QF-QR-003 proposal handoff

Task-ID: QF-QR-003-PROPOSAL
Dispatch-ID: QF-DISPATCH-20261028-QR-003-PROPOSAL-1
State: PROPOSAL_AWAITING_USER
Spec-Revision: r1
Date: 2026-10-28 (Australia/Melbourne)
Role: QR
Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`
Branch: `codex/qr-validation-baseline`
Baseline: `e1e903ed5d6d5bcd4d387936bbcfe704d4b224ce`

## Completed and exact scope

Created only this report and `research/qr003/protocol-proposal.md`. Existing QR-001
results, QF-QR-002 specification and cache review are preserved. Branch was clean
at the expected baseline. Read AGENTS and applicable workflow documents, the
actual signal/ML/timing/sizing/execution/backtest/cost code and frozen research
inputs/evidence. No nested AGENTS was found in nonignored project files.

Prepared a bounded, unapproved preregistration proposal. Recommendation: **M1 is
Phase A: an ETH entry-event/label feasibility audit, not model training.** It would permit
at most one allow-all baseline replay plus three fixed skip-once diagnostic
trajectories and synthetic causal/accounting tests, only after user approval.
It explicitly addresses unexecuted candidates, portfolio path dependence,
variable label-end purging, censoring, different-target metric comparisons and
the absence of an untouched test period.

## Read-only verification actually performed

- Git branch/log/status confirmed expected HEAD and no pre-existing QR changes.
- Recomputed SHA256 directly from the nine already approved local research input
  files; all match `research/qr001/data_manifest.json`. No refresh/download.
- Counted existing ledger records, rather than rerunning strategy/backtest:
  32 baseline opens, no adds/reductions, 31 natural exits and one terminal forced
  close; entry counts by old fold 8/12/12. Mature natural-exit counts before those
  fold starts with strict 24h isolation are 0/7/18. One natural position crosses
  each of the first two fold boundaries. QR-001 primary candidate has zero opens;
  .40 sensitivity has two, both in fold 1, lasting 11h/89h.
- Source confirms next-open execution, shared timing/exit state, equity-dependent
  fixed-margin sizing and prorated as-of funding costs. Current rearm_after_loss,
  adverse_exit and daily-loss gate are disabled; no new rule is inferred from
  unused config fields. Final forced close is censored for the proposed label.
- Documentation field/path/whitespace checks are performed before commit. No
  implementation tests or prior 160/178-test suites were rerun for this proposal;
  no model fitting, new replay, new dataset construction or alpha search occurred.

The deterministic counts are descriptive evidence, not an effective sample-size
claim or an exit-label dataset. A 31-event selected reference path cannot establish
coverage of counterfactual entry states or robust model value.

## Main conclusions and dependencies

Five hourly series do not provide five-asset strategy replay readiness. Complete
approved 1h/4h/daily/funding replay evidence is only available for ETH, with known
warmup/funding, historical-tier, arrival-time and liquidation limitations.
Only executed-trade labels miss new opportunities after skipping entries; forcing
every hour to start flat changes the question. A local position payoff is not
the opportunity cost of skipping and its sum is not portfolio return.

M1 must report candidate-stage counts, censored/closed labels, branch ancestry and
state divergence, and may finish as engineering-feasible but statistically
insufficient. Existing historical folds are already inspected; the first has no
earlier mature event labels in this frozen replay. No magic accuracy/trade-count
gate, winning threshold search or automatic progression to training is proposed.

Suggested future exclusive paths: QD owns `research/qr003/replay_probe.py`,
`tests/test_qd_qr003_probe.py` and its probe report; QR owns feasibility audit,
QR tests and results. Those are proposed allocations only. QD must assess whether
a research observer can preserve the existing engine without runtime edits or a
second simulator; otherwise return a concrete dependency to the user. QR does not
contact QD or initiate that work in this task. QF-QD-002 remains deferred.

## User decision and stop point

**当前请用户决定：是否只批准 Phase A / M1（ETH、最多四条固定诊断回放、无训练）？**
批准后也须在 M1 结果出来时再次决定 D2：停止/获取更合适资料/批准一个有明确预算、
精度目标和新数据计划的模型试验。所有数值实验门槛都是研究提案，不是用户已接受的
风险限额；运行方向、退出、仓位和风险默认值保持不变。

Control QF-CONTROL-20261028-QR003-FINALIZE-1 narrows the handoff to this first
user decision; later modeling is only a conditional outline. Unresolved candidate
coverage, path dependence and sample sufficiency remain audit questions.

This task stops after committing the two proposal documents and reporting their
paths/commit. No further task, automation, main merge, model activation, runtime
schema migration, real configuration/credentials, app/engine or NAS operation.
The launcher fix reported by the coordinator was not re-applied or launched here.
