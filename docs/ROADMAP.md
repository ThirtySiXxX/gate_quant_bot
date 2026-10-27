# Roadmap

This is a prioritized backlog, not approval to change contracts or deploy.
Paper/offline work is the default. Tasks start only after disjoint file claims.

| ID / owner | Deliverable | Acceptance evidence | Dependency |
|---|---|---|---|
| W-001 / integrator | Review current source snapshot; start independent QD/QR branches/worktrees | Matching baseline commits, original HEAD/index preserved, claims published | User review of existing dirty baseline |
| QD-001 / QD | Atomic per-key cache writing and coordinated admission | Concurrent read/write and failed-write recovery; simultaneous starts cannot exceed limit; offline suite | No schema change intended; request one if necessary |
| QR-001 / QR | Portable offline experiment runner and explicit embargo | Synthetic end-to-end reproduction, dataset/label/feature/config hashes, deterministic seed, negative results; boundary tests for label end and embargo | Work from declared data fixture; CR-001 for shared manifest |
| QD-002 / QD | Accurate stop/timeout lifecycle and defined paper restart policy | Blocked-thread and restart tests, truthful status, no real engine launch | QR review if results/restart assumptions change |
| CR-001 / QR owner, QD reviewer | Immutable data/model provenance manifest proposal | Units, instrument scope, source/availability/coverage/hash, training code/deps, costs/labels, validity, old-bundle compatibility and contract tests | Joint review and user integration approval before runtime requirement |
| CR-002 / QD owner, QR reviewer | Requested/effective universe and data failure policy proposal | Invalid/short history cannot silently change comparisons; version/migration plan and negative tests | Joint review and user integration approval |
| QR-002 / QR methodology, QD runner | Correctly named fold validation; optional true training folds | Frozen-parameter behavior distinguished from retraining; explicit rolling/expanding semantics, purging/embargo and unseen test isolation | Separate file assignment; no concurrent edits to walkforward.py |
| QD-003 / QD | Reproducible environment and offline CI | Reviewed version pins/lock strategy, no secrets/network/trading in tests; Python + JS checks | Dependency compatibility evidence |
| QD-004 / QD + QR reviewer | Point-in-time market metadata and explicit volume units | Source-recorded units, ingestion/availability semantics, listed/delisted coverage and gap manifests | CR-001; no fabricated historical metadata |
| QR-003 / QR | Research aligned with actual holding periods and costs | Multi-instrument/time holdouts, normal/doubled costs, turnover/drawdown/trade counts, multiple-testing disclosure | Reproducible data/runner; no activation implied |
| QD-005 / QD | Execution-risk realism and operational hardening | Documented liquidation/ADL/margin assumptions, failure simulation, API exposure controls, monitoring/runbooks | Explicit separate authorization for any deployed NAS/service work |

Completed workflow foundation: repository audit, exclusive ownership, shared
interface registry, contract tests and startup instructions. None of the backlog
defects is fixed merely by documenting it. Deep learning is deferred until a
testable research hypothesis and data/validation baseline justify it.
