# QF-QD-013 — first authorized actual-input pilot

2026-10-29 Australia/Melbourne. **One finite execution completed, zero orders,
fills and episode samples. Not full-period acceptance or training readiness.**

## Authority, identity and preservation

Dispatch `QF-DISPATCH-20261029-QD013-ACTUAL-PILOT-1`; authorization reference
`QF-APPROVAL-QD013-PILOT-1`, recorded at
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qd013-pilot-authorization.json`.
The user requested continuing replay/sample preparation after optimization, with
confirmation before training. The coordinator allocated this finite scope and
numerical budget; these numbers are not claimed as verbatim user choices.

Executed code/parent: `9adcbb01a584b35ba384e1ca6bc461d97a782469`.
Manifest SHA256:
`d6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a`.
All37manifest code-file hashes matched before launch. Existing branch
`codex/qd-cache-safety`, worktree
`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`.
HEAD was exact; no staged/unstaged tracked edits. The pilot and report paths were
absent. Only pre-existing untracked runtime evidence was present and retained.

Exactly **one** new entry invocation, exit0; no probe/help/default run, test,
benchmark, code repair, retry, directory substitution, reset or resume. Store SPENT
records `attempts_started=1`. No code, manifest, ledger, financial assumptions,
production configuration or other agent's files changed. Only this report is
committed; runtime artifacts remain untracked. The resulting report commit is
the commit containing this file, resolvable with
`git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-013-actual-pilot.md`.
Main remains `cae0d2395adf2cd3905e41cb1c16748c8247c32c`; no merge or push.

Executed once from the QD worktree, **not an instruction to execute again**:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd013.entry --authorize-actual-replay --human-authorization-ref QF-APPROVAL-QD013-PILOT-1 --manifest-sha256 d6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a --scope pilot
```

## Finite scope and phases actually reached

BTC/ETH joint account10000USDT, P0/ALLOW_ALL only. Complete2023 indicator-only
warmup; continuous economic interval `[2024-01-01T00:00Z,2024-01-02T00:00Z)`;
settlement-only tail `[2024-01-02T00:00Z,2024-01-02T02:00Z)`. No repeated capital
per coin, window/account reset, forced exit, enlarged universe or modified costs.

1. Named approval, exact manifest/code/metadata gates and exclusive launch receipt
   succeeded. Accepted frozen sources were read through the existing bounded
   transport; no download, source repair or repeated historical acceptance audit.
2.32allowed source objects were opened once. Full warmup/day hourly and funding
   preparation completed. First cache build:2original native prepares,
   1covariance-series computation,24joint hourly snapshots,0full-context cache
   encodes and0raw-cursor reopens.
3. Shared immutable SQLite cache reached COMPLETE; original registered ledger
   admission and continuous advance completed.32declared time points,5adapters
   each =160registry entries. The last discrete tick is2024-01-02T01:00Z,
   strictly inside the declared02:00Z exclusive tail end; no tick at the endpoint
   was invented. Knowledge cutoff slot5, committed_seq32.
4. Episode export completed normally with0records, COMPLETE manifest and empty
   JSONL. No model features/matrix/fit were generated. The CLI returned
   `FINITE_REPLAY_COMPLETED_RESEARCH_ONLY`, training_authorized=false.

The complete2023warmup was retained even though this pilot scores only one day.
It is a separate finite diagnostic, not a segment to concatenate into the final
2024–2026account, and supplies no full-period throughput or profitability proof.

## Generated coverage and zero-sample outcome

Only this invocation's small result, final stored view/component summaries and
derived-cache metadata/availability aggregates were inspected after it finished.
No raw historical payload was rescanned and no ledger was reopened/replayed.
Final component values were read via read-only SQLite root traversal and existing
zlib encoding. Inspection helpers first had a SQL clause-order error, then a
text-versus-BLOB hash lookup mismatch; these were read-only inspection errors,
not additional entry invocations or changes to stored state.

| Generated coverage | BTC | ETH |
| --- | ---: | ---: |
| Closed hourly source bars retained |8784|8784|
| Warmup hours / economic hours |8760/24|8760/24|
| First / last bar-open UTC |2023-01-01T00:00Z /2024-01-01T23:00Z|same|
| Funding source records retained |1098|1098|
| First / last funding source UTC |2023-01-01T00:00Z /2024-01-01T16:00Z|same|
| Native hourly snapshots AVAILABLE / unavailable |24/0|24/0|
| Execution-open cells |24|24|
| Primary MARK distinct query times SUPPORTED / UNKNOWN |30/0|30/0|
| Slow MARK distinct query times SUPPORTED / UNKNOWN |30/0|30/0|

Slow-clock cells were prepared for reuse; this pilot uses the primary P0clock.
Primary economic queries span2024-01-01T00:00Z→23:00Z, including additional
funding settlement/finality time points. Five required purposes across both
instruments produce **300SUPPORTED /0UNKNOWN** ledger query-status records.
This is observed coverage for this declared query set, not every possible clock
or future date. MARK source points consumed270920BTC/212092ETH; primary+slow
window queries60per coin, max retained27BTC/6ETH. No real gzip performance ratio
was measured or inferred from those operation counts.

Policy outcome is recorded as `NO_INCREASE` on all32registry calls (tail and
nonhour calls retain status). All five adapters ran32times. There are0generated
orders,0decision records,0fills,0lots,0closed slices,0mature episodes,0immature
episodes and0censored episodes. No episode exists to label or force-close. The
recorded status does not by itself attribute the absence of orders to a particular
signal threshold or prove all native execution semantics on real data; no new
alpha analysis or window search was performed.

Financial events:60Reserves +6FundingSnapshot =66events. The six snapshots
(00:00/08:00/16:00Z, each coin) have no eligible held ranges. No fee, funding
revision or cash Posting events were generated. Six funding ledger obligations
have zero A/B/L/P/Tamounts and no allocation/posting references. Environment
receipt `amount`/`known` remain null and posted=false for these empty snapshots;
they are not relabeled as successfully settled nonzero-position funding examples.
No fee or nonzero funding cash was incurred. Real held-position funding,
partial fills, natural maturity and censored-target behavior remain supported
only by the prior scoped synthetic evidence, not by this zero-trade actual pilot.

## Final known account state and limits

Cash10000, economic equity10000, unrealized0, liabilities0, receivables0USDT;
no positions, open orders or completed episodes. Ledger head ACTIVE describes
store state, not a running trading service. Head:

- cutoff `1704157200000000`, slot5; committed_seq32;
- audit_prefix `a7cc1c41774e52a4f3bd1cc0f3203e2b149f96f8c94e08979df7cf601e63816e`;
- economic_state_sha256 `fcb8ae48ff4ca48df8e9d1aad28ee61c2925d0bc46ac2dd20bf3b56aadc0c398`;
- view_sha256 `1964a0903607f7c7f2d73b4d4fc84f6d7d1fd00da1dacb917eb14e859778c949`.

At the final tail tick the old economic MARK is STALE, new_risk_supported=false,
reductions_supported=true; simulated budget is null(STALE_VALUATION), reserved
margin/fees null(UNKNOWN_RESERVES), actual available margin null(NOT_MODELED).
These are explicit limitations. No new tail MARK was fetched or fabricated;
there is no inventory requiring a new mark or forced valuation target. Economic
query UNKNOWN count0does not mean the tail's old mark stays fresh.

| Observation | Actual | Allocated outer observation |
| --- | ---: | ---: |
| Wall seconds |17.287150458|300|
| CPU seconds |17.030308|200|
| Peak RSS bytes |164724736|536870912(512MiB)|
| Physical input bytes |26462037|134217728|
| Expanded input bytes |40459311|113724359|
| Physical rows yielded, including parser lookahead |502784|928426|

Wall/CPU start at existing ObservationBudget construction after imports/identity
gates and stop before final result serialization. RSS is the process lifetime
high-water observation. These are not whole-process paired benchmark numbers;
no speedup is calculated. Physical/yielded input rows include warmup, archive
prefixes and parser lookahead, not just selected day bars. Accepted descriptors
bind source identities; the entry did not rehash/revalidate whole old raw payloads.

`observed.output_bytes=25286` is only the receipt writer counter and **is not total
disk output**. Explicit file inventory before its own small metadata file measured
pilot239files/14811736bytes; market cache14204928bytes; entire retained QD013root,
including old synthetic failures/performance evidence,781files/86630934bytes,
below128MiB. Exact final totals including inventory are stated below. Ledger
SPENT active_wall_us5654364, attempts_started1, total_written_bytes63661156;
write-work accounting differs from retained file bytes. Original per-store60s,
512MiB and2MiB page/state limits remain unchanged. Observations/cooperative checks
are not hard OS limits. No resource breach was reported; full-run sufficiency is
unproven.

## QR handoff, immutable artifacts and next steps

All following paths are under the QD worktree; they are local runtime evidence,
not files committed or uploaded with this report:

- Receipt/result: `research/.data/qd013/pilot-actual-1/launch.json`, `result.json`.
- Mature/immature/censored records share
  `research/.data/qd013/pilot-actual-1/export-P0-ALLOW_ALL/episodes.jsonl`, currently
  empty; no separate nonempty mature/censored file exists.
- Export contract/identity:
  `research/.data/qd013/pilot-actual-1/export-P0-ALLOW_ALL/manifest.json`.
- Market cache:
  `research/.data/qd013/markets/5b2c34340cd17a7204c6801aaa8e6f0446465f7afbe66e55845e8e6aec0294e8.sqlite3`.
  COMPLETE,19980cells, cache key equals filename; content_sha256
  `22db34ad6e70bc24793bd01e28784e1ba096c8a9f9857f12f19a15c6b07a06cc`
  (canonical cell-content digest, not SHA of SQLite file bytes).
- Final view/adapter/obligation summary:
  `research/.data/qd013/pilot-actual-1/readonly-summary.json`.
- Sizes/hashes/resource counter definitions:
  `research/.data/qd013/pilot-actual-1/artifact-inventory.json`.

QR015 may handle the empty compatible export with exact provenance; no candidate
labels, candles or examples should be invented to make it nonempty. No repeated
market preparation or ledger replay is needed to inspect these outputs. A zero-row
pilot does not demonstrate usable training sample size, label coverage, class
balance, validation sufficiency or real held-position label-chain correctness.

This task is complete as a **finite zero-trade pilot**, and stops here. The next
review must decide whether a separately bounded continuation/full-span proposal
is appropriate under unchanged strategy rules and known ledger/resource limits.
Do not select a more profitable window or silently stitch/reinitialize accounts.
Any additional invocation needs its own approved scope; this directory/reference
is consumed. Actual fitting of models, scalers or calibrators still requires
explicit user confirmation. QR code and research decisions remain QR-owned.

No tests/old research acceptance or performance comparison were rerun. No model,
training matrix, scaler/calibrator fit, main integration, push, release, app/engine
launch, real credentials/account access, orders to an exchange, Windows/NAS
service change or cloud computation occurred. Shared journals/previous reports
were preserved under the exclusive report-only allocation.

## Artifact byte hashes and final retained sizes

| Artifact relative to pilot root | Bytes | SHA256 |
| --- | ---: | --- |
| `launch.json` | 25286 | `904503c84ba7837f36afabe82c1da265d03839ab5bf821d8af5fe67092aa2f31` |
| `result.json` | 15287 | `29eed196a787866d5c466fb0c51330ab10cde8c27a8dd622fb20e06fd9b80549` |
| `export-P0-ALLOW_ALL/manifest.json` | 650 | `1d313bf5d90782c0564e55e620465c50bc518b4c0c3ba0e6741fbfdf9310f62b` |
| `export-P0-ALLOW_ALL/episodes.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `P0-ALLOW_ALL/store/HEAD` | 290 | `57d4499431703fad047ece1381e462191b4e302fc2b3a19ef98acfb8994feadc` |
| `P0-ALLOW_ALL/store/GENESIS` | 155972 | `6f7f07887d91966e8efb2372403ad6d27aaed12491bb93e6bb756db85c1ee0c0` |
| `readonly-summary.json` | 15820 | `2ecd242fa756614379c3dfd85c15c5f8c7ab185d34846089d2937186c1ce3d6a` |
| `artifact-inventory.json` | 2209 | `af9f9717b1221a19b859a6b4b7447c035eb90a35467acdd47b2ec407bea23777` |

Final retained pilot: **240files / 14813945bytes**. Entire QD013root including prior evidence and this inventory: **782files / 86633143bytes**, below134217728bytes. Report bytes reside outside that runtime root.
