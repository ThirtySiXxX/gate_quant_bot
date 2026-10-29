# Decisions

## D-001 — Preserve the current implementation (2026-10-27)

Accepted for this workflow task: audit the actual working tree; add instructions,
documentation and contract tests only. Preserve pre-existing source, documents,
ignored local handoff and staged changes. No rewrite, commit, push, deployment,
live trading or service operation is part of this task.

## D-002 — One editor per file, two development worktrees (2026-10-27)

QD owns infrastructure/production; QR owns research. The collaboration ownership
table resolves mixed-file boundaries. Concurrent development requires disjoint
file claims, separate feature branches and worktrees, independent commits and
counterpart review. Shared journals have QD as integration editor. User/integrator
approval is required before integration; no automatic merges.

## D-003 — Freeze native formats before migration (2026-10-27)

Native registry revision 1.0.0 and its tests preserve ML feature version 1,
result schema 3 and existing unversioned structures. A concurrent setup chat
supplied a separate additive envelope schema 1, standalone validator and rejection
tests; these are preserved as a collaboration proposal, not approved runtime
adoption. INTERFACES distinguishes both layers. Missing provenance/arrival times
remain runtime limitations. Adapter adoption and required-field changes need a
versioned request, counterpart review and user integration approval.

## D-004 — Snapshot a reviewed baseline without touching the source index (2026-10-27)

Current HEAD omits extensive uncommitted functionality. Startup instructions use
a temporary index and local snapshot commit after review, then branch both roles
from that exact commit. This workflow task only documents the commands; it does
not create those commits/worktrees. Never stash/reset the source to obtain a base.

## D-005 — Preserve safety and research evidence boundaries (2026-10-27)

PAPER and offline fixtures are the defaults. Real credentials/orders, LIVE and
NAS changes need explicit user authorization. Current fixed-margin sizing,
disabled daily-loss gate and empty default ML path remain unchanged. Tests prove
engineering properties, not profitability or high-leverage survival. Existing
data-gap corrections and negative research findings take precedence over older
optimistic notes; historical experiments were not repeated in this audit.

## Pending decisions

- CR-001: data/model provenance manifest and validation; QR proposes, QD reviews.
- CR-002: requested/effective universe and data failure policy; QD proposes, QR reviews.
- True rolling/expanding retraining semantics, paper restart persistence and any
  risk-default change require separate reviewed decisions. No pending proposal
  may be described as accepted or implemented.

## D-006 — Reconcile concurrent setup output (2026-10-27)

The user confirmed another chat was writing this checkout and said they would
stop that writer. Its coordination message also reported pausing shared edits.
Preserve its `src/contracts.py`, `tests/test_shared_contracts.py`,
`docs/REPOSITORY_AUDIT.md` and useful INTERFACES specification. This chat supplies
the native compatibility tests and consolidates status/ownership documentation.
No existing runtime source is replaced. Standalone validation is not production
enforcement, and no self-approval of a runtime migration is inferred.
