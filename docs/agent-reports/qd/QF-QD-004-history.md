# QF-QD-004-HISTORY: official source feasibility, discovery only

Date: 2026-10-28 Australia/Melbourne. Dispatch:
`QF-DISPATCH-20261028-QD004-SOURCE-FEASIBILITY-1`.
Parent: `1a2bf705050a0fdc4f47da7e834487f3c37cd800`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`. Current status: finite acquisition complete;
candidate **NOT_READY** pending QR source/semantic review. Discovery findings below
are preserved as history; the final handoff has current coverage and hashes.

## Ownership and scope

QD accepts exclusive ownership of this report and ignored
`research/.data/qd004/source-probes/`. The latter contains sanitized public bodies,
`probe-ledger.json`, `verification.json`, and a local self-ignoring `.gitignore`.
No root ignore policy was changed. Only this report is committed. Resolve its
commit with `git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-004-history.md`.

Proposed next-stage exclusive QD paths: `research/qd004/history_intake.py`,
`research/qd004/results/` for metadata manifests, `tests/test_qd_history_intake.py`,
and separately assigned ignored raw/normalized/quarantine storage. These are
proposals, not files created or an authorization to begin bulk intake. QR owns
semantic readiness criteria/validation and its reports. Preserve previous probe,
runtime, strategy/risk/config/contracts and shared journals. No additional symbols,
venues, model training, full replay, source-checkout writes or scheduling occurred.

## Primary sources and semantics

- [Gate perpetual REST reference](https://www.gate.com/docs/developers/apiv4/en/futures/):
  public `GET /api/v4/futures/usdt/candlesticks`, `/funding_rate`,
  `/contracts/{contract}`, `/risk_limit_tiers?contract={contract}`. Candle requests
  allow up to 2000 points; explicit from/to cannot be combined with limit.
  Use unprefixed BTC_USDT/ETH_USDT for traded-price bars. UTC seconds; OHLC is
  USDT/base, v is contract-count volume, sum is quote volume. Do not substitute
  sum for v or relabel price-index/mark bars. Funding t/r is event time/rate.
  Contract multiplier is base/contract; current tiers are configurations, not a
  documented historical version series. No historical tier archive was verified.
- [Current official historical page](https://www.gate.com/developer/historical_quotes):
  advertises candles from January 2023 and defines monthly gzip objects under
  `https://download.gatedata.org/futures_usdt/{type}/{YYYYMM}/{symbol}-{YYYYMM}.csv.gz`.
  Relevant types: candlesticks_1h, candlesticks_4h, candlesticks_1d, funding_applies.
  Its current code example uses UTC month folders and monthly names for these types.
- [Official 2021 announcement](https://www.gate.com/zh/announcements/article/21688):
  distinguishes six-column futures candle CSV (time, contracts, close/high/low/open)
  and settled two-column funding_applies (time/rate). funding_updates describes
  the next-period indication and is not a replacement. Preserve signed decimal
  rate per settlement; do not divide an already fractional rate by 100.

The old announcement establishes documentation/history of the archive, not current
file completeness. Publication/ingestion timestamps are unavailable; neither bar
close nor an object's Last-Modified establishes actual decision-time availability.

## Bounded GET evidence

Exactly **12 sequential unauthenticated GET attempts**, no retry/redirect following,
one-second minimum pause after each, certificate validation enabled, 8-second
socket timeout. REST responses capped at 65,536 bytes; archives requested with
`Range: bytes=0-4095`, saved-body cap 8,192 bytes, decompression preview cap 2,048
bytes. Only a complete small funding object was subsequently decompressed offline
with an 8,192-byte limit. All calls succeeded at transport level; no access/auth
barrier was bypassed. Public documentation browsing is separate from these twelve
data probes. No account/private endpoints, auth headers or cookies were used.

Observed UTC: 2026-10-27T14:33:01 through 14:35:55 (2026-10-28 Melbourne).
Saved body bytes: **10,076**. All 12 body hashes and caps verified offline.
Exact URLs, params, timestamps, selected non-cookie response headers, status,
units/time interpretation and hash scope are in the ignored ledger:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/source-probes/probe-ledger.json`.
Ledger SHA256: `33e234f0fa851993c3de62e795174b75af91e4dd69d037e5f017f302a6157c78`.

REST query base: `https://api.gateio.ws/api/v4/futures/usdt/`.
For IDs 2–7 from=1672531200 and to=from+2*interval_seconds-1, no limit.
IDs 8–9 use funding_rate with from=1672531200, to=1672617599, limit=2.

| ID | Exact family / symbol / interval | HTTP and observation | Saved-body SHA256 |
| --- | --- | --- | --- |
| 1 | candlesticks BTC_USDT 1h; from=1793084400,to=1793091599 | 200, two recent positive-control bars | e62d690bf8b9e05e60793f2a582c7ff703d47012b2f3e5f30e8455745da49938 |
| 2 | candlesticks BTC_USDT 1h, 2023 | 400, older than recent 10000 points | 244bec6b614af6d2fc9a2907fbe8699ea8b9418aaeb4afa6e0d6a5f51bf76182 |
| 3 | candlesticks ETH_USDT 1h, 2023 | 400, same retention error | 244bec6b614af6d2fc9a2907fbe8699ea8b9418aaeb4afa6e0d6a5f51bf76182 |
| 4 | candlesticks BTC_USDT 4h, 2023 | 200, opens 1672531200/1672545600 | c01cc48c90a481f691b60a0914954bd232715abd5f5092e149e85cdb29f019d5 |
| 5 | candlesticks ETH_USDT 4h, 2023 | 200, same two open timestamps | f4ff3d5aecfed9c8f5ec2ef0e058625cc41c21509b6f263343b5c4317d0e2e38 |
| 6 | candlesticks BTC_USDT 1d, 2023 | 200, opens 1672531200/1672617600 | c96f3b506e1b096adce90c952e7b842f0e2b54748f7590c080dab485a8fd19f6 |
| 7 | candlesticks ETH_USDT 1d, 2023 | 200, same two open timestamps | 55420c461febf32e19175124049f5c4bd6a04eabb61569045842adfaf6122425 |
| 8 | funding_rate BTC_USDT, 2023 | 400, from exceeds 180-day limit | fc6b3014e9efc29e95773802ee20c2b252a5d870e46028b47ac1127a95280b10 |
| 9 | funding_rate ETH_USDT, 2023 | 400, same 180-day error | fc6b3014e9efc29e95773802ee20c2b252a5d870e46028b47ac1127a95280b10 |
| 10 | archive BTC_USDT candlesticks_1h 202301 | 206, first 4096 of 14132 bytes | 1264c2598b9b28c4949c64e9f62cc81a864243c87d1ce64f43c9f65f46950e5d |
| 11 | archive ETH_USDT candlesticks_1h 202301 | 206, first 4096 of 12505 bytes | 055b9d7950f1e5ff5ae5d19fec85c32427bc75d8ae4c61826b3bd724e7d1ff03 |
| 12 | archive BTC_USDT funding_applies 202301 | 206, complete 473-byte object | 062c1d564d5db9c8fb50cfd2cf0040eed21a176981077c08d252f988ea6ef5a1 |

Exact archive objects:

- [BTC hourly January 2023](https://download.gatedata.org/futures_usdt/candlesticks_1h/202301/BTC_USDT-202301.csv.gz)
- [ETH hourly January 2023](https://download.gatedata.org/futures_usdt/candlesticks_1h/202301/ETH_USDT-202301.csv.gz)
- [BTC settled funding January 2023](https://download.gatedata.org/futures_usdt/funding_applies/202301/BTC_USDT-202301.csv.gz)

IDs 10–11 hashes cover **prefix bytes only**, not full files; previews begin at
1672531200 (2023-01-01 00:00 UTC). Complete-month candle coverage/CRC is unverified.
ID 12 fully validates gzip and 93 strictly increasing settlement records from
1672531200 through 1675180800 (January 31 16:00 UTC). Its uncompressed 1842-byte
CSV SHA256 is `1c4cd4229b716af808f2eff67f4343c8b555c5345d5324b882975c581dac0472`.
No ETH funding archive, 4h/daily archive, other month or pre-2023 object was probed.
Do not infer their availability from a template or from BTC's funding success.

## Retention, earliest-date bounds and decision

- REST hourly cannot supply the requested 2023 start; smaller historical pages
  do not bypass the observed 10000-recent-bar rejection. At observation time,
  10000 hours reaches roughly September 2025; exact rolling boundary was not
  probed. This retention limit differs from the documented per-request cap.
- REST 4h/daily demonstrably reach 2023-01-01 for both symbols. That is a verified
  accessible date, not their absolute earliest date or proof of continuous history.
- REST rejects the old funding request for both symbols; no bypass attempted.
  Public archive provides a separate documented source, with BTC January 2023
  settled funding actually observed. Full ETH historical funding remains to verify.
- Pre-2023 availability and absolute earliest dates remain unknown under this
  finite budget. A 2021 announcement/example is not a coverage certificate.
- Conditional recommendation: official archive-first hourly/settled funding intake,
  with approved REST or archive coarser bars and overlap checks. No third-party
  mixture, resampled stand-in, zero-filled funding or substituted current rate.
  A full 2023 score start additionally needs pre-2023 warmup defined/verified by QR;
  a calendar beginning in 2023 alone does not establish indicator readiness.

## Planning estimates (not a completed acquisition)

For [2023-01-01 00:00Z, 2026-10-27 09:00Z), excluding bars whose close exceeds
cutoff=1793091600: per asset 33489 hourly, 8372 four-hour, 1395 daily bars; two assets
total 86512 candles. Funding at an illustrative constant eight hours would be about
4.2k events/asset; actual settlement/interval changes must be validated, not imposed.

- Archive-only four-family plan: 46 monthly partitions × 2 assets × 4 families =
  368 object GETs, plus four current public contract/tier snapshots and agreed
  overlap/quality checks. A hybrid REST 4h/day plan at 1000 bars/page needs 22
  coarser-bar requests instead of 184 monthly coarser objects. Do not apply this
  arithmetic to inaccessible REST hourly/funding history.
- These are nominal partitions, not a claim that the unfinished October 2026
  archive is already published. January samples were last modified in February.
  Prefer verified complete-month archives through September plus bounded official
  REST October tails (all within observed recent limits), with overlap checks and
  strict cutoff. That candidate hybrid would use 180 hourly/funding monthly
  objects, four recent tail requests, 22 coarser REST requests and four metadata
  requests: about 210 base GETs if all required files exist. QR must freeze the
  exact partition plan; do not silently include later October data.
- January hourly gzip objects total 26637 bytes for the two assets: linear
  extrapolation over 46 months is about 1.2 MB for hourly alone, **not** a promised
  download size. Plan roughly 1–10 MiB compressed four-family data, 10–25 MiB
  normalized/provenance storage, and 100 MiB working allowance to be frozen with
  the actual spec. No trades/depth/other symbols are included.
- At an illustrative one request/second, 372 requests need at least 6.2 minutes
  of pacing plus network/verification/retries, not an ETA guarantee. These public
  samples required no paid API/account; no commercial quote or future data fee
  was established. Training/computation cost is outside this discovery task.

## Proposed intake manifest, pending QR freeze

This is a standalone research proposal, not a runtime/shared-schema change.
Each accepted partition should have schema_version=1 and:

```text
intake_id, frozen_qr_spec_sha256, normalizer_revision, cutoff_ts
instrument_id: gate:usdt:BTC_USDT | gate:usdt:ETH_USDT
family: traded_ohlcv | settled_funding | contract_snapshot | risk_tiers_snapshot
source: official_url, method, exact_params, retrieved_at_utc, status,
        selected_headers, source_document_url, no_auth=true
raw: relative_path, bytes, sha256, compression, complete_object,
     content_range, hash_scope (full_object or prefix_only)
normalized: relative_path, sha256, schema, rows, interval_seconds,
            requested_half_open_range, first_ts, last_ts, volume_unit=contracts,
            price_unit=USDT_per_base, funding_unit=decimal_per_settlement,
            timestamp_semantics, historical_arrival_known=false
quality: candidate | accepted | quarantined, gaps, conflicts,
         OHLC/finite/grid/closed_cutoff checks, settlement_schedule_evidence,
         REST_archive_overlap_report, validator_revision
quarantine: raw_sha256, reason_code, expected_vs_observed, affected_range,
            reviewer_resolution (never silently promote/overwrite)
```

Raw objects stay immutable; normalized partitions link their exact source hashes.
Prefix probes cannot be promoted into full-object manifests. Preserve raw decimal
representations/contract volume; model volume representation is not interchangeable
after conversion. Candle opens and settlement times must remain distinct; unknown
historical arrival stays unknown. Static metadata gets retrieval/snapshot time,
not a fabricated point-in-time history. Overlap disagreements are quarantined,
not resolved by cherry-picking whichever source improves outcomes.

Future ignored raw/normalized/quarantine paths require the intake allocation.
QD writes acquisition/normalization and technical checks; QR freezes exact ranges,
warmup, feature availability, funding coverage and semantic acceptance. No two
writers modify a manifest/partition. No dataset is training-ready until those
criteria pass and the user separately confirms training.

## Verification, limits and next handoff

Offline checks verified 12 sequential IDs, allowed official GET paths, no auth or
redirects, all saved-body SHA256/byte caps, gzip preview limits, complete funding
CRC/row ordering, and ignore status. `git diff --check`/staged delta check passed.
No code changed, so no runtime test suite was rerun or new simulator/test claimed.
Only this report is staged/committed; prior commits/main/index and user work remain
untouched. Local evidence is ignored and not a portable committed dataset.

Ready for the coordinator's exact QR frozen spec and bounded intake allocation.
Do not bulk download, extend dates, implement the proposed tool, run experiments,
train, restore scheduling, merge/push or operate the app/NAS under this discovery
dispatch. Exhausted probe budget is 12/12; further probing belongs to a separately
bounded handoff. Full history, historical tiers and genuine unseen data readiness
have not been established by these samples.

## Authorized intake continuation (2026-10-28, in progress)

Dispatch `QF-DISPATCH-20261028-QD004-INTAKE-1` authorizes the finite implementation
and public acquisition stage. Earlier discovery-only stop instructions above are
historical. QR frozen spec commit is `b573d5278b2bf74770b996bc03ba11fe2cb19a08`,
JSON SHA256 `6e3d4fb99c62d0658fcb3bb779a35b072d65b29df399e9b287fa315943687862`;
exact committed bytes were checked before implementation. Current parent e68813c.

The new exclusive QD paths are history_intake.py, results metadata, its dedicated
test file, this report, and ignored research/.data/qd004/. Source-probes remain
intact. Initial adapter/API example: `research/qd004/results/intake-contract.json`.
Frozen route `hybrid_native_v1`: monthly native 1h/funding_applies through 202609,
native REST 4h/day throughout, October REST tails with September overlaps, four
current-only metadata snapshots. Source route is fixed before any new response
or return inspection. Budget includes 12 prior attempts and their 10076 bytes.
Only one collector runs, sequentially, with no automatic redirect handling.

Candidate dataset root is
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/history-v1`.
Root manifest/normalized keys follow the frozen JSON exactly; source_row is one
based after any recognized CSV header. All duplicate references and conflicting
variants are retained separately. No runtime/schema migration, replay or fitting.
Collection status, final counts/hashes, tests and unresolved quality issues will
be recorded below after execution. Training remains NOT_READY pending QR G1–G4
review and fresh direct user G5 permission.

Implementation pre-collection verification: 17 offline intake fixtures passed;
full socket-blocked suite **214 passed** (10.972 seconds), frontend **8 groups
passed**, whitespace checks passed. Fixtures cover persistent attempt/retry
budgets, access barriers, bounded/partial responses, gzip CRC/EOF/expansion,
one-based header mapping and volume meaning, invalid/boundary row retention,
all-version conflict quarantine, complete duplicate lineage, unrounded funding
seconds offsets, dropped-funding detection even with altered manifest hashes,
authentic extreme retention, current-only metadata and exclusive collector lease.
Concrete synthetic duplicate/conflict/exclusion examples are published in
`research/qd004/results/lineage-examples.json`; QR accepted the initial adapter.
The pinned plan has **210 new requests**, expected **222 total** with the 12 probes
and no retries. Collector source SHA256 before acquisition:
`2adfed92c3204244a9ed5e66732d8ce2cee89af624eb1b18feb57bdf7ee0299a`.

## Final intake handoff (2026-10-28)

Acquisition implementation commit:
`5209a13847615214f5c8ca86cdbcc38bed627c1e` (parent e68813c).
The final follow-up commit containing this section adds offline cross-interval
quarantine evidence support and metadata summary; resolve its exact SHA with
`git log -1 --format='%H %s' -- research/qd004/results/intake-summary.json`.
No source route or acquired market record was changed after inspection.

**Dataset root:**
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/history-v1`.

- Final review manifest: `candidate-reviewed.json`, SHA256
  `16035c8f9065ea79e4c572ce444b7af6a6b038f2526e5bda9273bf6580274dac`.
- Original immutable acquisition manifest: `manifest.json`, SHA256
  `5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd`.
- Spec: exact b573d527 JSON SHA256
  `6e3d4fb99c62d0658fcb3bb779a35b072d65b29df399e9b287fa315943687862`;
  ignored exact copy at `research/.data/qd004/specification-b573d527.json`.
- Metadata-only tracked summary: `research/qd004/results/intake-summary.json`,
  SHA256 `9bd0cd3c66e9d9feee5104bf945c1bf45eef3a79c0adcde9e99bdec037f732a4`.
  Full raw/normalized/quarantine records remain ignored; they are not copied into Git.

The offline review manifest references an additional quarantine file; the parent
manifest and every raw/normalized file are unchanged. `postprocessing` records
the parent hash and review-code hash
`79e35285ec03afa4b346cb41b441d7919a3489584f20f511dfbce2fe750b9afd`.
Original `collector_sha256` still identifies the acquisition code, not the later
offline supplement. This preserves both phases' provenance without rewriting it.

### Acquisition/resource accounting

All **210/210** planned new tasks returned complete HTTP 200 responses: 180 monthly
gzip objects and 30 public JSON requests. **222/450 total attempts** includes the
12 source probes. No retries, redirects, paid/authenticated endpoints, extra
symbols/venues or replacement sources. Sequential collector, one-second pauses,
15-second socket timeout. Total retained response bytes including probes:
**3,540,596**; new raw bytes **3,530,520**; largest new response **111,586 bytes**.
All source objects are below the 10 MiB per-file and 250 MiB total limits; full gzip
CRC/EOF/expanded-size checks passed. Remaining 228 attempts were not consumed.
No further acquisition is scheduled or implied by that remainder.

Attempt ledger: `attempts.jsonl` (begin/end reservations, IDs 13–222); prior probe
ledger/body hashes were rechecked unchanged. The request plan is frozen in
`plan.json`. Public current-only metadata was retrieved around
2026-10-27T15:04:31–15:04:36Z, after the historical cutoff; its actual observed_at
is retained and historical_effective_at is null. It is not a historical tier,
multiplier or funding-interval reconstruction.

### Exact candidate coverage

All stream timestamps below are inclusive first/last source event/open times.
The declared data_range remains [1672531200,1793091600); candles whose close
exceeds cutoff are not included. Counts are data rows, not independent labels.

| Symbol / series | Rows | First / last timestamp | Normalized CSV SHA256 |
| --- | ---: | --- | --- |
| BTC 1h | 33489 | 1672531200 / 1793088000 | e292642723c6f76e97c7565e4b7ed97a76cf382402a3dcad22a7d902ff069789 |
| BTC 4h | 8372 | 1672531200 / 1793073600 | 063fe0aa8856063bb545e3a02ba207b898af94f7ff7e53e6c5745e2f9cc82b8a |
| BTC 1d | 1395 | 1672531200 / 1792972800 | 371d46b75a0f25c53a9bc1a552a13e5c799ec7b005d7b0e9c3f62bf0278c8935 |
| BTC settled funding | 4187 | 1672531200 / 1793088000 | d962b994e147a791ee148ae07b0884b0bb8430bc9e4a4b72b48ee51a6782f9a4 |
| ETH 1h | 33489 | 1672531200 / 1793088000 | b258376d40a44fb5f3a5cfeddbdc3710a39f360f57881e52af6c497d7690acfc |
| ETH 4h | 8372 | 1672531200 / 1793073600 | 04be5a081dd08aeb49088b8541fa5ab056cde7f6f2eb249e9bbaa049f29aa7a4 |
| ETH 1d | 1395 | 1672531200 / 1792972800 | 24af98956640bd404f36745340bab14bd8abfdfe292d7e0d705c579bee7b0ba1 |
| ETH settled funding | 4187 | 1672531200 / 1793088000 | b4a0bc1adce31a6d23c381a92ced45f72062cecd27101a236d52e240eaf60fcd |

Files are `normalized/{symbol}-{3600s|14400s|86400s|funding}.csv`.
Four additional JSON files retain public current contract/tier snapshots.
Local reread verification accounts for **94,914 eligible raw origins** and
**94,886 normalized market rows**. The difference is 28 identical duplicate groups,
each retaining both source references. No invalid/excluded row, same-stream numeric
conflict or missing candle-grid interval was observed. This does not assert a
historically complete funding schedule or satisfy QR's later warmup/event gates.

Duplicate overlaps, per asset: eight 4h API page joins, one daily page join, two
hourly September/October rows, three funding September/October rows. All matched
numerically. Old disjoint monthly files also underwent grid continuity and native
coarser-bar QC; that is not claimed as independent same-row old-funding overlap.

### Unresolved quality blockers — keep NOT_READY

**2,068 cross-interval QC windows disagree.** No native stream was replaced by an
hourly aggregate, no volume correction was selected, and no outcome was inspected.

| Native comparison | Mismatch windows | Volume only | Windows with price differences |
| --- | ---: | ---: | ---: |
| BTC 4h vs 1h aggregate | 188 | 188 | 0 |
| BTC day vs 1h aggregate | 148 | 137 | 11 (close) |
| ETH 4h vs 1h aggregate | 1393 | 1392 | 1 (low) |
| ETH day vs 1h aggregate | 339 | 318 | 21 (close) |

All involved native records and hourly component values/references are retained
in `quarantine/cross-interval-disagreements.json` (2068 evidence records, 5,971,571
bytes), SHA256
`b154d32d8e1f4ef67c42b633dc0850363baa7d5120c8a450877fdcc344603529`.
Resolution is `pending_QR_source_review_no_preference`. Native and hourly streams
remain **unaccepted candidates**; neither member is declared corrupt merely from
the comparison. 2035 windows differ only in volume, 33 include price differences.
This evidence quarantine does not silently drop authentic rows or manufacture
replacement inputs. Independent local reread reproduces every disagreement from
its referenced raw rows.

Funding inter-event durations, in seconds (all source timestamps kept unrounded):

- BTC: 28800×4145, 28799×21, 28801×19, 28802×1; **41 deviations** from strict 8h.
- ETH: 28800×4077, 28799×51, 28801×52, 28797×2, 28798×1, 28802×2, 28803×1;
  **109 deviations**.

The counts/near-eight-hour durations do not establish intended historical
settlement scheduling. Source timestamp/processing jitter is another possible
explanation; no event is rounded, shifted, inserted or zero-filled. These are
unresolved semantics for unchanged constant-interval replay, not proven missing
payments or proof that the venue deliberately changed intervals. Full exact
deviation pairs are in quality_summary.funding_schedule for QR review.

One ETH daily >20% close-to-close move at timestamp 1746662400 was flagged and
retained. Its OHLC agrees with the independently sourced hourly aggregation;
price authenticity is supported by that cross-check, not clipped or claimed
fully certified. The source reference is in the tracked metadata summary.

Current metadata remains hypothetical historical simulation input only. No
historical tier/multiplier schedule was reconstructed. G2 is blocked pending
source/semantic review; QD ran **no real-data replay, baseline labels or model fit**.
G3 full native warmup/usable events belongs to QR after prerequisites pass. G4
proposal and fresh direct human G5 permission remain required before training.

### Verification, reproducibility and next steps

Final dedicated fixtures: **18 passed** (0.063 seconds). Final socket-blocked full
suite: **215 passed** (10.879 seconds). The added fixture proves cross-interval
quarantine preserves the original manifest and normalized bytes while binding all
variants to raw row references. Frontend's 8 regression groups passed before
collection; no frontend/runtime code changed. Delta whitespace checks passed.

Actual acquisition command, after committing the tested collector:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m research.qd004.history_intake --spec research/.data/qd004/specification-b573d527.json --root research/.data/qd004/history-v1 --prior-probe-ledger research/.data/qd004/source-probes/probe-ledger.json --fetch
```

The later `--quarantine-qc` phase ran with socket connects blocked. To reproduce
the final offline file/CRC/hash/schema/lineage/evidence reread, without networking:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m research.qd004.history_intake --spec research/.data/qd004/specification-b573d527.json --root research/.data/qd004/history-v1 --manifest candidate-reviewed.json --verify-only
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -m unittest discover -s tests -p test_qd_history_intake.py -v
```

Both base and final reviewed manifests passed local full-file/origin-accountability
checks; `verification.json` and `reviewed-verification.json` record their distinct
hashes. This is a second disk-reading pass, not independent QR semantic acceptance.
All source-probe hashes remain unchanged. Raw/normalized bytes were not rewritten
by the offline evidence supplement, and no data files are staged in Git.

Handoff to QR: independently revalidate the final review manifest and retained
evidence, resolve/characterize the cross-interval and funding timestamp semantics,
and assess historical metadata/warmup compatibility before any permitted baseline.
Do not silently switch routes, correct volume, round settlements, shrink dates or
train to work around these blockers. A changed source/resolution policy needs a
versioned handoff. This task stops after this report/metadata/code/test commit;
no extra acquisition, replay, training, backlog work, automation or integration.

Final preservation check: original source main HEAD remains
`cae0d2395adf2cd3905e41cb1c16748c8247c32c`, staged binary-diff SHA256 remains
`c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`,
and original index-byte SHA256 remains
`7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.
Control `QF-CONTROL-20261028-QD004-FINALIZE-INTAKE-1` requests ending this stage.
Any separately proposed diagnostic acquisition is not executed under this handoff.

## Frozen source diagnostics completed (2026-10-28)

Dispatch `QF-DISPATCH-20261028-QD004-SOURCE-CHECKS-1` separately authorized only
the 11 requests in QR commit `fcf49886af32c13185cf93b621f4c146004d0f17`, proposal
SHA256 `7118d0648d3daf6c7ca37d002876b3780923113d1b90e6d1360e703aaa07406d`.
Exact committed bytes were checked. Base for this stage: 6c0c5c8. The final report
commit is obtainable with `git log -1 --format='%H %s' -- research/qd004/results/source-check-summary.json`.
The five coarse-archive objects were explicitly diagnostic exceptions, not an
intake route change. No production or research-tool source code was edited;
existing tested bounded parser/TLS/no-redirect primitives were reused in an ad-hoc
runner restricted to the frozen URLs. No new subsystem was built.

Evidence root:
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd004/source-checks-v1`.
It retains exact proposal, begin/end attempt ledger, all raw responses, compressed
and expanded hashes, response/Content-Range evidence, source mappings, full record
comparisons and a before/after v1 hash inventory. Only metadata summary/report
are committed; raw values and detailed comparisons remain ignored.

- `diagnostic-manifest.json` SHA256:
  `784be6cfdece0267abd66c117ad42c15ed7783b82b59bd7e044c5c216d1780d3`.
- `comparison-evidence.json` SHA256:
  `81aedd5bea6734cfd05fc27d3a9f8402bc3fb9f2c1445ecc131eb2b76dfca373`.
- `diagnostic-verification.json` SHA256:
  `db451b2c4c9cea738bc8f086acfe30b3894cb2235dc1835900a0c4e665d2092f`.
- Tracked concise metadata: `research/qd004/results/source-check-summary.json`.

All **11/11** requested objects returned HTTP 200, **11 attempts of the 14 maximum**,
zero retries/redirects/failures. Additional bytes **17,647**; shared cumulative
attempts **233/450** and bytes **3,558,243**. Sequential, one-second pauses,
15-second socket timeout, 10 MiB response / 25 MiB additional / 100 MiB expanded
caps. Five gzip archives passed full CRC/EOF validation; all eleven bodies have
complete-response and SHA256 evidence, with no parser exclusions.

### Exact route comparisons (observations, no source preference)

Frozen targets were selected by QR discrepancy category/earliest affected date,
not by strategy returns. Comparisons use exact parsed numeric equality without
rounding, tolerance changes, replacement or a waiver.

| Request(s) | Diagnostic observations |
| --- | --- |
| 1 BTC 4h January 2023 | All 186 archive rows equal retained hourly aggregates; 185 equal retained native REST rows. The frozen January 22 volume target differs from retained REST, while archive/hourly agree. |
| 2 ETH 4h January 2023 | Same 186/186 hourly agreement and 185/186 native REST agreement; frozen January 22 target differs in volume. |
| 3 ETH 4h February 2023 | All 168 archive rows equal hourly aggregates; 166 equal retained native REST. The frozen February 24 20:00 target differs in low; another row differs in volume. |
| 4 BTC daily December 2025 | All 31 archive rows equal hourly aggregates; 19 equal retained native REST. Twelve rows differ in volume, including two with close differences. Frozen December 11 target differs in close/volume. |
| 5 ETH daily December 2025 | All 31 archive rows equal hourly aggregates; 24 equal retained native REST. Seven volume differences, one also close; frozen December 10 target differs in close/volume. |
| 6–7 BTC October REST repeat | New 24 hourly bars and one daily bar each exactly reproduce their retained REST counterparts. New daily vs new hourly aggregate still differs in close and volume at timestamp 1792886400. |
| 8–9 ETH October REST repeat | New 24 hourly bars and one daily bar each exactly reproduce retained counterparts. Daily vs hourly aggregate still differs in close and volume at timestamp 1792281600. |
| 10 BTC, 11 ETH settled funding | Each five-record new REST window exactly matches retained archive timestamp/rate pairs, including the selected offset cluster. Zero added/missing exact records and zero chronological timestamp deltas in the compared windows. |

Thus all **602** checked coarse-archive rows agree with retained hourly aggregates;
23 differ from retained native REST rows. This is limited to five specified
objects, not certification of every archive or proof one route is universally
correct. The two fresh REST-vs-REST pairs show the sampled discrepancy is not
explained solely by archive/API mixing or a nonrepeatable earlier fetch. Funding
cross-route agreement supports that the sampled offsets are present in official
source records; it does not establish intended settlement timing, permit rounding,
or prove the full historical schedule.

Every detailed comparison retains diagnostic raw path/source row/value plus v1
normalized path/row and original raw path/source row/value. Aggregates retain all
hourly component references. Funding keeps both exact record sets; optional
chronological rate/timestamp comparison is descriptive, not event relabeling.

### Preservation and handoff

Before/after hashes confirm **229 v1 files unchanged**, including all 210 raw
objects, normalized streams, quarantine evidence, original manifest
`5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd`
and reviewed candidate
`16035c8f9065ea79e4c572ce444b7af6a6b038f2526e5bda9273bf6580274dac`.
No route, units, period, data values, normalization or tolerance changed. Source
main HEAD/index preservation was checked again. No tool code changed, so focused
or full regression suites were not unnecessarily rerun; record-specific raw/hash,
gzip/EOF/schema/numeric comparisons, immutability and delta-whitespace checks passed.

Status remains **NOT_READY**. QR must assess source semantics and any explicitly
versioned resolution policy; persistent differences are not automatically resolved.
No full replay, labels, model fit, training, current-metadata backdating, app/NAS
operation, main integration, push or scheduling occurred. This finite diagnostic
stage ends after its report/metadata commit; no further queue or fetch is started.
