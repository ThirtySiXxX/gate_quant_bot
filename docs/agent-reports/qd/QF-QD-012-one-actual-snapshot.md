# QF-QD-012 — single authorized actual-input invocation

2026-10-29 Australia/Melbourne. **FAILED_BEFORE_LAUNCH / NOT PASS.**
Exactly one authorized CLI invocation exited1 at the human-reference format gate.
No launch receipt, raw input consumption, native snapshot or MARK query occurred.
**The single authorized invocation is consumed. Do not retry because the attempt
directory is absent.** No entry/manifest/budget repair was performed.

## Authority, exact implementation and preservation

- Dispatch `QF-DISPATCH-20261029-QD012-ONE-ACTUAL-SNAPSHOT-1`;
  task `QF-QD-012-ONE-ACTUAL-SNAPSHOT`.
- Human answer: “批准这一次真实输入检查（推荐）”, from
  `request_user_input_async/call_8dcc09a7ef3e45768567a3505db61ac5/item0`.
  The recorded answer time is2026-10-28T15:49:19.413571+00:00, equivalent to
  2026-10-29T02:49:19.413571+11:00 Melbourne. This is the approval record's time,
  not a newly inferred exact invocation time.
- Approval reference passed **exactly as instructed**, the absolute path:
  `/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qd012-actual-snapshot-user-approval.json`.
  The approval exists and was read; the failure does not mean human authorization
  was absent. The CLI rejected the representation of that valid reference.
- Exact implementation / parent commit:
  `7f481daa70735c7619f385d0843b02e05f9dd11f`.
  Branch `codex/qd-cache-safety`, worktree
  `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, initially clean.
- Reviewed manifest SHA256:
  `657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a`.
  All28 saved code identities matched in the permitted read-only preflight.
  Entry source SHA256:
  `90478fa9fdc0a98d6db49e10adea1e9f35bc4ed5c9f08808b7c38707ed1c01b2`.
- Original preparation report is preserved at the exact implementation commit,
  `docs/agent-reports/qd/QF-QD-012-snapshot-entry-prep.md`.
  Adopted48a09a6 synthetic delivery was neither rerun nor re-reviewed.
- This new report is the only edited/committed file. Report commit identity is
  the commit containing this file, resolvable with:
  `git log -1 --format='%H %s' -- docs/agent-reports/qd/QF-QD-012-one-actual-snapshot.md`.
  No other changes were present after invocation. Main remains at
  `cae0d2395adf2cd3905e41cb1c16748c8247c32c`.

## Actual invocation and sole result

The preflight checked worktree/branch/commit, approval metadata, manifest/code
identities and presence of the existing attempt directory/receipt/results. The
directory and all three expected artifacts were absent. It did not import the
entry/native module or run a default/help/test/probe. Code and approval/manifest
reads are metadata/source inspection, not historical payload reads.

Executed **once**, with no wrapper, supervisor, alternate identifier or retry:

```sh
qd012_human_approval_ref='/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/qd012-actual-snapshot-user-approval.json'
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python -B -m research.qd012.actual_snapshot_entry \
  --authorize-actual-snapshot \
  --human-authorization-ref "${qd012_human_approval_ref:?Set only after explicit human approval}" \
  --manifest-sha256 657a4ebc73408e76c8a61f26ec334a68ebe17044148451930c8e80ab0699ae0a
```

Tool call output for the one command (`exec_command`, chunk `cfa735`):

```json
{"reason": "SnapshotStop:NAMED_HUMAN_AUTHORIZATION_REFERENCE_REQUIRED", "status": "STOPPED_NO_RETRY"}
```

Exit code1; no continuing process/session. Tool-reported shell-command elapsed
time0.01951325 seconds. This is the tool's elapsed field, **not** an in-entry
resource observation or independent CPU/RSS measurement. No second invocation
was made to obtain measurements or repair the failure.

The direct cause is visible in the pinned `actual_snapshot_entry.py:253`:

```python
re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{5,255}', human_authorization_ref)
```

The prescribed reference starts with `/`, while this regex requires its first
character to be a letter or digit. It therefore rejects the instructed absolute
path at line254. This precedes even the entry's own manifest read at line257,
ObservationBudget initialization at line262, directory creation at line263 and
receipt creation at line274. The external preflight's successful manifest/code
verification is distinct from these **unreached** in-entry stages.

No authorization prefix, path spelling, entry code or manifest was changed to
work around the mismatch. The existing approval JSON still contains its original
prelaunch `actual_attempts:0` / `APPROVED_NOT_LAUNCHED` fields because it is outside
this task's exclusive edit scope. **Those stale prelaunch fields and an absent
receipt do not authorize another invocation; actual CLI invocation count is1.**

## Reached and unreached stages

| Stage | Actual result |
| --- | --- |
| Read-only source/worktree/approval/identity preflight | Completed; clean exact base,28 code hashes and manifest matched |
| CLI argument parse / explicit authorization flag | Reached; authorized flag and instructed reference passed |
| Human reference format gate | Rejected, `NAMED_HUMAN_AUTHORIZATION_REFERENCE_REQUIRED` |
| In-entry manifest/metadata/source identity checks | Not reached |
| ObservationBudget / fixed attempt directory | Not reached |
| Exclusive durable launch receipt | Not created |
| Read/parse2023hourly/funding prefix | Not reached;0records/bars consumed |
| Execution-only open projection | Not reached |
| Native features/regime/volatility/full covariance/warmup context | Not computed |
| MARK raw prefix traversal / selections | Not reached;0queries evaluated |
| Durable result/failure summary | Not created; gate rejection occurs before its try/receipt block |
| Account creation/advance, orders, labels, matrices, fit | Not executed / not authorized |

Required full warmup was2023-01-01T00:00Z through2024-01-01T00:00Z,8760closed
hours/coin, snapshot at `1704067200000000` UTC-us. **Actual consumed bar count:
BTC0 / ETH0; no evaluated data cutoff or latest closed timestamp exists.** No
shorter warmup was substituted. Native context/covariance identities, sizing
volatility, regime/adaptive/timing fields and funding integer-source-seconds
compatibility are **NOT_EVALUATED**, not inferred from old synthetic results.

Execution-only open was scheduled for `1704070800000000` UTC-us (01:00Z).
It was not read/projected. Future H/L/C/V/availability did not enter native inputs
because no native inputs were consumed; no executed isolation test is claimed.

Required MARK selections (same four roles for each row):

| Instrument | Query UTC / UTC-us | Roles | Actual status / source |
| --- | --- | --- | --- |
| BTC_USDT | 2024-01-01T00:00Z /1704067200000000 | valuation, reservation, decision, permitted_fill | NOT_EVALUATED; no selected source/availability/price/lineage |
| ETH_USDT | 2024-01-01T00:00Z /1704067200000000 | valuation, reservation, decision, permitted_fill | NOT_EVALUATED; no selected source/availability/price/lineage |
| BTC_USDT | 2024-01-01T01:00Z /1704070800000000 | valuation, reservation, decision, permitted_fill | NOT_EVALUATED; no selected source/availability/price/lineage |
| ETH_USDT | 2024-01-01T01:00Z /1704070800000000 | valuation, reservation, decision, permitted_fill | NOT_EVALUATED; no selected source/availability/price/lineage |

No selector-generated UNKNOWN was produced. Every required query's support is
unestablished because the entry stopped at the authorization-reference gate.
Do not invent MISSING_REQUIRED_MONTH, NO_ELIGIBLE_POINT or stale-source reasons;
the data was not consulted. The gate failure says nothing about actual MARK
coverage or the research strategy.

## Resources, metadata versus consumption, and retained evidence

Approved observed limits were300s wall /200s CPU /256MiB RSS;128MiB physical input,
113724359expanded bytes,928382physical rows and8MiB new runtime output. They were
cooperative checks, not hard OS limits. Their observer was not initialized:

| Item | Actual evidence |
| --- | --- |
| CLI invocations / exit | **1 /1**, no retries |
| Tool shell-command elapsed | 0.01951325s, limited meaning described above |
| In-entry observed wall / CPU / peak RSS | Unavailable; observer not reached, no supplemental measurement |
| Actual historical raw physical / expanded input | **0 /0 bytes**, execution rejected before any payload entry point |
| Actual physical source rows | **0** |
| Consumed hourly/funding/MARK objects | **0 /0 /0** |
| Runtime artifact files / retained bytes | **0 /0 bytes** |
| Native full-year completion or resource sufficiency | Not demonstrated |

The frozen32-object metadata describes2hourly/26funding/4MARK objects,
87478614whole selected physical bytes,113724359expanded bytes and928382row cap.
These are unchanged approved **metadata bounds**, not observed reads. No raw
object was opened/hashed, no coverage checker/replay ran, no later year was read.

Post-failure read-only existence check confirmed the fixed path remained absent:

`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data/qd012/actual-snapshot-20240101-attempt-1/`

- `launch-receipt.json`: absent, no file size.
- `result.json`: absent, no file size.
- `failure.json`: absent, no file size.

No receipt/result was fabricated after the fact. No directory was created,
deleted or renamed, and no old evidence was changed. The console rejection and
exit code above are the only result of this invocation and are preserved in this
report. Absence here is explained by a known prelaunch gate failure, rather than
an unknown long-running actual-input outcome. No CPU/RSS PASS is asserted.

## Handoff and stop

Only this report is committed. No implementation, manifest, scientific rules,
budgets, shared documents, QR files, main/source checkout or original user work
changed. No tests/help/default/import probe, service/engine, account, credential,
network/download, fit/scaler/calibration, labels, push/integration, Windows or NAS
operation occurred.

Concrete unresolved dependency is the entry's authorization-reference interface:
the approved absolute-file reference conflicts with the pinned first-character
regex. Any correction or alternative representation, and any subsequent attempt,
needs a new explicit task/authorization; this consumed approval cannot be reused.
No QR/scientific validation is triggered by this infrastructure gate failure.
Report this failure and stop; no automatic follow-up execution or review loop.
