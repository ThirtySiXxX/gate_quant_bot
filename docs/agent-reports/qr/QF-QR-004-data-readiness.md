# QF-QR-004 BTC/ETH data readiness

Date: 2026-10-28 (Australia/Melbourne). Role: QR.
Current state: **NOT_READY — sealed history acquired; required semantic checks blocked**.
Training: **NOT AUTHORIZED; fresh human confirmation required before fitting**.
Branch: `codex/qr-validation-baseline`.
Worktree: `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`.
Base: `9a598866b642fd121c3d09196bc2befd367b4a4a`.
Dispatch: QF-DISPATCH-20261028-QR004-DATA-SPEC-1.

## Actual sealed-candidate assessment

Continuation: QF-DISPATCH-20261028-QR004-DATA-ACCEPTANCE-1. Immutable dataset root:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/history-v1`.
Manifest SHA256 `5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd`.
Generating collector commit `5209a13847615214f5c8ca86cdbcc38bed627c1e`, exact source
SHA256 `2adfed92c3204244a9ed5e66732d8ce2cee89af624eb1b18feb57bdf7ee0299a`.
QR did not import the collector as its validator or make any network request.

| Gate | Independent result |
|---|---|
| G1 raw provenance/transport | PASS: all raw hashes/bytes, complete gzip streams, request identities, row values and metadata lineage checked. |
| G2 usable normalized semantics | BLOCKED: cross-interval discrepancies below; historical schedule/metadata meaning remains limited. No automatic source preference or tolerance change. |
| G3 events | NOT RUN: prerequisites fail. Full-window indicator warmup passes as a conditional diagnostic, not acceptance of the discrepant inputs. |
| G4 protocol | Proposal recorded; final future holdout and economic effect/precision decision still pending. |
| G5 training permission | NOT GIVEN. Zero model/preprocessing fits, baseline replays or new trading labels in QR004. |

Both assets have exactly **33,489 hourly, 8,372 four-hour, 1,395 daily and 4,187
settled-funding records** over the frozen range. There are zero missing expected
candle slots, invalid normalized OHLCV, shifted availability values, unresolved
raw-to-normalized omissions or same-key conflicting versions. All 94,886 unique
market-record origins match normalized membership. The 94,914 retained raw origins
include 28 identical duplicate groups; every duplicate reference and destination
is independently accounted for. Four current metadata snapshots retain their true
retrieval times and null historical effective dates. No rows were repaired.

The independent attempt audit matches each begin/end reservation to its frozen
planned request and manifest entry. There were **210 new GET attempts, all HTTP
200, zero retries/failures**, plus the original 12 probes: **222/450 attempts**,
**3,540,596 bytes including probes**. The 210 new payloads use 3,530,520 bytes.
All original probe hashes and their declared full/prefix limits were verified.
The remaining 228 attempts are a resource ceiling, not a reason to keep searching.

### Unresolved discrepancies (all dates below UTC)

Each comparison uses exact Decimal arithmetic and original native records, with
1h aggregation used only as a consistency diagnostic. Counts are discrepant
coarse bars, not bad hourly rows or independent trading samples.

| Asset / native interval | Compared | Discrepant | Fields | First–last affected bar open |
|---|---:|---:|---|---|
| BTC 4h | 8,372 | 188 | 188 volume | 2023-01-22 00:00 – 2026-09-29 08:00 |
| BTC 1d | 1,395 | 148 | 148 volume; 11 also close | 2023-01-22 – 2026-10-25 |
| ETH 4h | 8,372 | 1,393 | 1,392 volume; 1 low | 2023-01-22 00:00 – 2026-10-27 00:00 |
| ETH 1d | 1,395 | 339 | 339 volume; 21 also close | 2023-01-22 – 2026-10-26 |

Concrete examples retained with every original source row in the diagnostic JSON:

- BTC 2025-01-15 12:00 four-hour volume: native **68,553,170 contracts** versus
  hourly sum **53,530,783** (28.0631% difference relative to hourly sum). The same
  day's volume differs 170,403,591 versus 155,381,204 (9.6681%).
- ETH 2025-08-07 08:00 four-hour volume: 30,531,634 versus 28,977,869 (5.3619%);
  daily volume 135,386,918 versus 133,833,153 (1.1610%). These are the largest
  absolute relative volume differences in their respective streams.
- ETH 2023-02-24 20:00 four-hour low: native **1592.75** versus hourly minimum
  **1592.85**, the only four-hour price discrepancy.
- BTC daily close differences begin 2025-12-11; ETH daily close differences begin
  2025-12-10. There are 11 and 21 respectively. For example, BTC 2026-02-11 closes
  at 67041.8 versus 67051.7; ETH 2026-01-11 at 3122.04 versus 3121.66.
- October BTC/ETH daily-close discrepancies exist even when both constituent 1h
  and native 1d inputs come from REST. Archive conversion alone cannot explain all
  differences. Neither a first/last-write choice nor replacing native bars with
  aggregates has been authorized.

**Confirmed:** different official native streams disagree despite faithful local
parsing and complete provenance. **Not established:** which stream is historically
correct, whether exchange aggregation/revisions explain the discrepancy, or whether
any affected input can be accepted under the frozen rules. No collector corruption
was found by these checks. Large volume differences cannot all be dismissed as
floating-point rounding. These unresolved input differences block G2.

### Funding and warmup

Both assets have 4,187 records and 4,187 unique expected slots under a diagnostic
8-hour reference grid, from 2023-01-01 00:00 to 2026-10-27 08:00. Exact source
timestamps remain unchanged. BTC has 562 nonzero offsets, ranging 1–3 seconds;
ETH has 561, ranging 1–5 seconds. Inter-event durations differ from 28,800 seconds
41 times for BTC and 109 for ETH. These counts describe different quantities.
No missing reference slot was observed, but this alignment does **not** prove an
intended historical settlement schedule or observed feed arrival time. Inter-event
deviations must not be converted into invented missing events, filled rates or
rounded timestamps. The fixed reference interval is still a declared assumption.

At 2024-01-01, both assets have 8,760 closed hourly bars, 2,190 four-hour bars and
365 daily bars. All four native trend horizons have 1,500 finite prior raw values;
both FDM windows have 500 complete prior rows; Carry has the full 1,000 prior raw
observations; the original causal hourly feature vector is finite. Native source
hashes match the frozen QR003 fixture. These are indicator calculations, not model
or preprocessing fitting. They establish enough warmup under the supplied inputs
and 8-hour reference assumption; they do not override the failed quality gate.

### Bounded next evidence and training decision

Frozen proposal commit `fcf49886af32c13185cf93b621f4c146004d0f17` contains
`research/qr004/results/source-check-proposal.json`, SHA256
`7118d0648d3daf6c7ca37d002876b3780923113d1b90e6d1360e703aaa07406d`.
It proposes 11 precise public requests for QD, at most 14 attempts including retries:
five native 4h/daily archives for the earliest discrepancy categories, paired
REST 1h/day checks for one October close discrepancy per coin, and two exact
funding overlap checks for the last shared timestamp-offset cluster. Selection
uses data-quality categories/times, never strategy returns. Original v1 stays
immutable; new evidence must be separate. Repeated differences are evidence of
persistence, not automatic acceptance. This report does not execute those requests.

There is **no training start date yet**. Resolve required input semantics first,
then, only if the frozen gates pass, use the two permitted unchanged baselines to
assess mature labels and dependence. The human subsequently confirms the final
evaluation/precision/holdout plan and permission to train. Do not generate labels
from knowingly unresolved inputs or increase model search to compensate.

### Additional-data recommendation

1. Prioritize reconciliation of existing same-venue BTC/ETH candles and actual
   settled funding, then documented historical funding/contract-rule changes.
   Current snapshots cannot be relabelled as point-in-time metadata.
2. Defer extra coins: they would add listing/delisting and survivorship problems
   before the current pipeline has passed. More rows alone do not prove better
   generalization or independent information.
3. Mark/index and order-book/spread history may support a later specific basis or
   execution hypothesis; keep separate instrument/price-type and availability keys.
   Never reconstruct order flow from OHLC or splice spot/other venues into Gate
   perpetual history. No new acquisition is requested here beyond the frozen check.
4. News, on-chain and macro data are lower priority because release times, revisions,
   coverage and as-of vintages need separate validation. External data is not
   inherently dirty, but adding it before those checks would add contamination risk.

### Actual tests and reproducible evidence

**23 QR focused offline tests pass** with sockets blocked, including the new sealed
attempt-ledger test: a lost reservation or changed request identity fails. Earlier
17 exact-commit QD tests were independently rerun and passed. No new runtime changes
justify rerunning the whole application. Actual-candidate verification is separate
from these synthetic tests and intentionally returns FAIL/NOT_READY.

`validate_dataset` produced `results/history-v1-independent-validation.json`
(SHA256 `c4a9174eeb0212d3bfb74530070f419788ed6164e5bb4813a00edfb094afa1e7`).
`sealed_diagnostics` produced `results/history-v1-diagnostics.json`
(SHA256 `1f6316d400233b7cbbad5a068257beff614e9aecb907313b15b82891cadf14fa`).
The latter records exact native/aggregate values, source rows, monthly counts,
request audit and conditional full-window results. A working diagnostic initially
used an unnecessary 3-second reference-offset boolean; before publication it was
replaced by observed min/max and exact slot indices. Its previous digest and the
correction are retained in the final JSON. No timestamp or acceptance gate changed.

Reproduce with the existing interpreter, sockets blocked, from the QR worktree:

```python
from pathlib import Path
from research.qr004.validate_history import validate_dataset, sealed_diagnostics
root = Path('/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/history-v1')
spec = Path('research/qr004/data-acceptance.json')
validation = validate_dataset(root, root/'manifest.json', spec)
diagnostic = sealed_diagnostics(root, spec,
    Path('research/qr003/results/phase-a-input-spec.json'), root.parent/'source-probes')
```

The following earlier sections preserve implementation checkpoints and their
then-pending status; the actual sealed-candidate decision above supersedes them.

## Completed changes

Published research-local BTC/ETH history calendar, source/units/availability rules,
immutable provenance manifest, duplicate/conflict/quarantine policy, bounded
acquisition budget, full native warmup checks and training-readiness gates.
The calendar is independent of returns. QR explicitly accepts QD sole collector
ownership as listed in `research/qr004/data-protocol.md`; no shared/runtime schema
change. The protocol ranks additional data without authorizing its acquisition.

## Files modified

Specification checkpoint `b573d5278b2bf74770b996bc03ba11fe2cb19a08`:
`research/qr004/data-protocol.md`, `research/qr004/data-acceptance.json`, and this
report. Validator checkpoint additionally changes `research/qr004/validate_history.py`
and `tests/qr_research/test_qr004_history.py`. `research/qr004/results/` is reserved
for independent acceptance evidence. Shared progress/decisions remain under
their integration editor; this report is the handoff evidence.

## Tests and results

Spec JSON parse and date/budget checks pass; `git diff --check` passes.
**22 focused offline tests pass**, with socket connections blocked: valid fixture
cannot grant training permission; raw hash/normalization tampering; advanced
availability; deleted/duplicate bars; conflicting raw overlap; mark/trade confusion;
unit/row lineage drift; traversal/symlink escape; cross-interval discrepancy;
invalid OHLCV/grid/NaN; funding offsets/interval ambiguity; truncated gzip;
206 completeness; manifest universe/spec drift. The native warmup fixture exercises
the original long-window EMA/scaler/FDM/Carry functions and causal feature code:
a year passes full windows; changing future funding leaves the result unchanged;
500 past Carry observations produce a finite native signal but correctly fail the
full 1000-observation requirement. This is a synthetic test, not actual data acceptance.

Coordinator review identified that row-to-raw equality alone did not detect an
omitted raw funding record. The validator now checks raw-to-normalized coverage
as well. Added negative fixtures for omitted funding, incomplete duplicate lineage,
mislabelled quarantine exclusions and metadata backdating. Duplicate destination,
every retained reference, conflict variants and boundary exclusions are compared
to independent raw parsing, not accepted based on file hashes alone. Non-boundary
exclusions remain blocked for separate reason review. Historical funding schedule
is still not inferred from inter-event durations.
The final transport fixture also rejects a valid-looking JSON body marked
incomplete/failed and independently checks saved bytes against HTTP Content-Length.

Command: load `tests.qr_research.test_qr004_history` through `unittest`, using
`PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python`
and patched `socket.create_connection`, `socket.socket.connect`, `connect_ex`
raising on use. Independent validator never downloads, repairs, fits or reads
operational config. No actual downloaded dataset is accepted yet; QD intake and
semantic evidence are pending. No model has been fitted.

## Known limitations

Gate documents appropriate archives; this is not proof each monthly file is
available or complete. QD is probing official sources. Phase A previously had
63 natural baseline labels, overlapping asset/time dependence and incomplete
funding warmup. Expanded data may still fail source coverage, schedule semantics
or useful event-count/precision checks. Current metadata is not historical truth.
No period already inspected will be described as an untouched test set.

## Dependencies and next steps

QD: acquire only the approved universe/calendar within the total-attempt budget;
retain payloads/failures, supply manifest and source/schedule evidence. QR: build
offline independent validation and inspect that exact handoff. Only if data gates
pass, generate at most two unchanged baseline trajectories to assess labels.
Then report READY_FOR_USER_TRAINING_CONFIRMATION or concrete NOT_READY blockers.
At the future training decision, the human must confirm the holdout and economic
precision goal as well as permission to fit. No automatic merge or integration.

Early QD adapter `research/qd004/results/intake-contract.json` reviewed and accepted:
hybrid_native_v1 uses monthly 1h/settled funding plus native REST 4h/daily and
October tail, with declared overlap checks. Exact JSON conventions agree; funding
`interval_seconds: null` records that schedule is not assumed. Identical duplicate
lineage in the quarantine partition is provenance, not automatically invalid data.
No downloaded dataset or final collector candidate is accepted by this early review.

## Collector checkpoint review

QR independently reviewed QD commit `5209a13847615214f5c8ca86cdbcc38bed627c1e`
(parent `e68813c273c66e29eb9950b6d52d144b1e89ab2d`) and the committed
`research/qd004/results/lineage-examples.json`. Examples match the QR adapter.
Collector SHA256 `2adfed92c3204244a9ed5e66732d8ce2cee89af624eb1b18feb57bdf7ee0299a`;
test SHA256 `d1931696ad7fc199767ef2cd7967b260816c5d8ad1f95c2e62d2fce80c5e280e`.
Both local files matched the exact committed bytes before execution.

**17 QD focused tests independently rerun and passed**, with sockets blocked:
fixed scope/spec/routes, total attempt and byte limits, retry/resume accounting,
access restrictions, incomplete transport, gzip integrity, original column units,
duplicates/conflicts/exclusions and dropped funding, funding-second preservation,
immutable paths, interrupted reservations, authentic extremes, exclusive collector
lease and current-only metadata. Tests used only temporary synthetic fixtures.
QD reported 214 broader Python tests and 8 frontend groups; QR did not rerun
those broad suites because this review does not change runtime or frontend code.

This technical review supports bounded intake and preserves all unresolved
semantic gates. Actual collection was still running without a final immutable
manifest at this checkpoint. No actual dataset acceptance, baseline replay,
training-readiness approval, merge or runtime integration is implied. QR validator
code checkpoint is `56e80c975cac260a8ffc8a0af793999e0109bf98`; specification hash
remains `6e3d4fb99c62d0658fcb3bb779a35b072d65b29df399e9b287fa315943687862`.
