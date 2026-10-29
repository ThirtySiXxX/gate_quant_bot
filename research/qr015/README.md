# QR015 local dataset consumer

This is a local preparation tool, default **OFF**. It uses the frozen QR014
12-feature/episode-return implementation. It has no estimator, scaler, replay,
native preparation, exchange, network or raw-market loader. A completed import
never authorizes training or certifies statistical adequacy.

## Invocation

From the QR worktree, this prints OFF without reading any dataset:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qr015.dataset
```

After a separately allocated real-data preparation run has an exact handoff and
budget, the invocation shape is:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qr015.dataset --enable-local-assembly --request /absolute/path/to/approved-import-request.json --request-sha256 EXACT_REQUEST_SHA256 --authorization-ref EXACT_PREPARATION_AUTHORIZATION_REF --output /absolute/path/to/new-output-directory --batch-size 128
```

This command is a future example, not an executed real-data import or training
request. The output directory must not exist. No implicit retry, overwrite,
resume, fallback to main, or cache building occurs. Python callers use:

```python
from research.qr015.dataset import assemble_local

result = assemble_local(
    request_path,
    expected_request_sha256=request_sha256,
    output_dir=new_output_path,
    enabled=True,
    authorization_ref=preparation_authorization_ref,
    batch_size=128,
)
```

`enabled=False` is the default, including when paths are supplied. Explicit
enablement applies only to dataset preparation. `training_authorized` remains
false in the request and every output.

## Coordinator-supplied import request

The request is JSON, hashed over exact file bytes. Unknown actual paths or
identities must be supplied by the coordinator; the consumer does not search for
the latest export or infer missing bindings. All input file paths are absolute.

| Field | Required content |
| --- | --- |
| `schema` | `qr015.import-request.v1` |
| `training_authorized` | `false` |
| `input_kind` | `ACTUAL` for a separately authorized real run; `SYNTHETIC` for literal development fixtures |
| `qd_commit` | `9adcbb01a584b35ba384e1ca6bc461d97a782469` |
| `qd_manifest_sha256` | `d6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a` |
| `qd_code_sha256` | Exactly the three `QD_CODE` path/hash entries in `dataset.py` for QD013 exports, market and inputs |
| `source_metadata` | Four kind/hash entries matching `SOURCE_METADATA` for actual inputs; no source payload is opened |
| `source_binding_ref` | Accepted handoff reference linking the exact export, cache, producer code, source manifests, account and scope |
| `binding` | Exact `account_id`, `trajectory_id`, `scenario_id=P0`, `policy_id=ALLOW_ALL`, `account_binding_id=QR010_SHARED_NATIVE_X10`, ordered BTC/ETH `instruments`, and `scope` |
| `binding.scope` | Integer UTC-us `warmup_start_us`, `initial_us`, `economic_end_us`, `tail_end_us`; matches the cache scope exactly; economic end at most 2026-10-01 UTC and tail at most two hours later |
| `input_received_at_us`, `assembled_at_us` | Actual research receipt/assembly UTC-us; receipt no earlier than declared export tail and no later than assembly |
| `export` | `manifest_path`, exact `manifest_sha256`, `episodes_path`, and the complete expected producer `identity` object |
| `market_cache` | `path`, complete expected `identity`, `key`, `content_sha256`, and `rows`, copied exactly from the accepted immutable cache handoff |
| `purge` | Boolean `complete`, ordered BTC/ETH `instruments`, and completeness evidence `source_ref`; optionally `additional_intervals` |
| `limits` | Positive integer `max_records`, `max_input_bytes`, `max_row_bytes` (at most 2 MiB), and `max_output_bytes` |

The three QD code hashes, four source manifest hashes and QR014 module hash are
literal pins in the consumer. Actual source metadata must match the frozen
values. The QR014 file hash is checked on enabled imports. The consumer does not
import QD code, run Git, or load its transitive trading/native dependencies.
It reads the published storage format with the standard library.

The producer's `write_bundle(..., identity)` accepts an arbitrary identity object;
the cache factory likewise accepts caller-supplied sources/code/config objects.
These opaque objects are compared **in full** to the supplied handoff. The
consumer does not invent undocumented inner field names or independently prove
their relationship. `source_binding_ref` must therefore identify a reviewed
mapping of those exact objects to this request's producer/source/account/scope
pins. A matching arbitrary self-authored request is not research acceptance.

`purge.complete=true` additionally requires a declared full account range from
2024-01-01 through exclusive 2026-10-01 UTC and a scoped two-asset inventory
attestation. A one-day pilot cannot claim this. Its rows are still exported with
the original calendar partitions and `PURGE_CONTEXT_INCOMPLETE` when applicable.
Scope declarations are attestations, not evidence created by the consumer.

Optional `purge.additional_intervals` has `path`, `rows`, and exact `sha256` for a
JSONL inventory. Each line has the frozen QR014 InformationInterval fields:

```json
{"instrument_id":"gate:usdt:ETH_USDT","start_us":1704067200000000,"end_us":null,"source_ref":"EXACT_HELDOUT_EVIDENCE_REF"}
```

Those literals illustrate the shape, not actual evidence. Intervals have closed
endpoints; null end is open-ended. They must be enumerated from accepted heldout
information, including any relevant lookback scope. The consumer also records
every episode's decision-to-label-known interval and adds all validation/audit
episodes to the heldout inventory. The owner must attest that the combined
inventory is complete; an omitted additional inventory does not establish it.

## Streaming and integrity behavior

1. Verify request/producer/version and export-manifest identity. Stream the
   episode JSONL once, check exact byte hash/count, and index records in a new
   local SQLite file. Duplicate proposal or episode identities fail, including
   repeated identical records or a second revision. As-known revision resolution
   remains the exporter’s responsibility.
2. Preserve actual P0/ALLOW_ALL identity; reject incompatible scenario or policy
   flags. Convert only the declared QR014 fields and use the frozen validator.
   Keep upstream label status and censoring marker separately: an open episode
   censored at the economic cutoff stays `open`, with a null target.
3. Read only 169 required closed-hour cells per proposal from the immutable
   MarketCache v1 file. No funding, MARK or native-array cells are read. Verify
   exact cache metadata and each selected cell's byte hash/key. Missing cells,
   sidecars, corrupt data or changed cache file identity stop the import.
4. Call `features_for_proposal` and `assemble_samples`. A completed disk inventory
   is queried across both instruments before each row. One intersecting witness
   is sufficient for QR014's any-overlap predicate; disjoint intervals need not
   be loaded into memory. This preserves cross-batch and cross-asset purging.
5. Emit deterministic decision/instrument/proposal-ordered outputs. Publish the
   COMPLETE manifest only after successful export/hash/selection checks. Keep
   partial outputs and `failure.json` on failure, with no automatic continuation.

The reader records the producer's whole-cache digest without scanning/recomputing
it. This is selected-cell integrity verification against a trusted immutable
handoff, not full-source or ledger revalidation. Dataset output bytes are checked
cooperatively, including the derived index; wall/CPU/RSS observations belong to
the explicitly budgeted calling run. They are not hard OS limits.

## Output contract and counting

| Artifact | Meaning |
| --- | --- |
| `manifest.json` | `qr015.local-dataset.v1`, COMPLETE, request/export/code/source/cache bindings and portable artifact byte hashes/counts; always training false/ready false |
| `request.json` | Exact parsed input request in consumer-canonical JSON, preserving the original byte-hash reference in the manifest |
| `samples.jsonl` | One row per unique exported realized episode and nested proposal; QR014 features/targets/splits/reasons plus source row byte location/hash, original episode fields, revision, availability tuples, as-known/finality refs, censoring, raw cost attribution and units |
| `information-intervals.jsonl` | Versioned full local interval inventory, including episode and heldout roles; the same interval may appear once per role |
| `summary.json` | Row/episode/proposal counts, exclusions, asset/year/split/state/censoring strata, observed decision bounds, train-only target sign/distinct-value counts and overlap diagnostics |
| `index.sqlite` | Derived join/interval scratch index, not an account ledger or authoritative portable output; intentionally not included in portable artifact hashes |
| `failure.json` | Failure evidence only; its directory has no COMPLETE manifest |

Unique episode/proposal counts refer only to records present in this accepted
export. QD013 currently exports realized episodes with their nested entry
proposals. It does **not** supply a standalone inventory of unfilled/rejected
proposals, so that count is null, never zero or an invented candidate universe.
Standalone proposal-only export needs an explicit future schema/allocation.

The 2024 train / 2025 validation / Jan–Sep 2026 exposed-audit boundaries remain
frozen. Both strict 24-hour training cutoffs are delegated to QR014. The consumer
does not redefine them for a pilot. Open/immature/censored/invalid targets remain
null, while excluded mature raw targets can remain available for provenance.

`closed_endpoint_overlap_clusters` is a descriptive connectivity count over
episode information intervals across both coins. An open end can connect all
later episodes. This is not an estimate of independent sample size. No mean,
scaler, learned parameter, confidence interval, adequacy threshold or model is
estimated. Empty/partial data is a valid preparation result and never means
training-ready. Finality and scientific sufficiency still require accepted
upstream evidence and a separately authorized readiness assessment.
