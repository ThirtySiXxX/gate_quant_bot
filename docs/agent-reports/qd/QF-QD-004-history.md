# QF-QD-004-HISTORY: official source feasibility, discovery only

Date: 2026-10-28 Australia/Melbourne. Dispatch:
`QF-DISPATCH-20261028-QD004-SOURCE-FEASIBILITY-1`.
Parent: `1a2bf705050a0fdc4f47da7e834487f3c37cd800`.
Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`. Status: finite discovery complete, conditional
source feasibility established; bulk intake awaits the coordinator's frozen QR spec.

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
