# QD013 concrete out-of-scope dependency request

Current dispatch QF-DISPATCH-20261029-QD013-CONTINUOUS-REPLAY-1 and performance
amendment QF-AMEND-20261029-QD013-LOCAL-PERFORMANCE-1. QD009 selection/index edits were subsequently allocated by the explicit amendment
below; codec remains unchanged.

Resolved by explicit amendment QF-AMEND-20261029-QD013-INDEXED-FACT-SELECTION-1.
Allocated and implemented owner extension: `research/qd009/streaming_ledger.py`, specifically
`Ledger._invoke` fact selection around lines1655–1688. `latest_available` currently
loads/counts every historical candidate BEFORE retaining one per instrument.
With two instruments and native fields, a full2024–2026 run exceeds the existing
262144 max_adapter_reads even though only two latest observations are consumed.
It also performs quadratic JSON scans. Changing driver selectors alone cannot
avoid this; deleting facts/private SQL mutation would violate immutable sources.

Minimal requested change: apply the exact same per-instrument latest ordering
(`available`, then fact key) in an indexed SQL selection BEFORE materializing/
counting projections. Keep the public selector/schema, source cutoff, unknown
cells, deterministic tie ordering, result packet, bindings and audit semantics.
All records actually exposed/read still count. Acceptance: exact packet equality
to old selection on bounded literals, ties/missing/unknown/future cutoffs; work
count independent of older history. No source data, cap increase or ledger reducer
change. The extension was received before this file was edited. Tests01–03 and
the new registered continuation exercised selection within the current budget;
full-history scalability is not measured.

Independent work continues on a reusable local native preparation/cache/spool,
compact causal inputs, registered ports, continuous finite synthetic account,
scenario identity and mature/censored exports. No full-history throughput or
resource acceptance is claimed. Remaining ledger schedule/config growth,
per-store wall/storage and per-state limits are documented in the final report;
no additional ledger contract/storage/VFS edits were made.
