# QF-QD-017 — Local data and local training preference

2026-10-29, Australia/Melbourne. User instruction: “现在包括以后的所有数据都要写成本地训练类型”.
Interpretation: existing and future project datasets must remain locally stored
and have local, machine-readable training inputs when eligible. Local storage
does not by itself establish label maturity, dataset completeness or training
approval. This records the user's preference; it is not a new runtime schema.

## Execution and storage

- Existing and future data preparation, replay and any subsequently authorized
  training use local files and local computation by default. Do not upload
  datasets or use remote/cloud training without a subsequent user instruction.
- Preserve original market snapshots, SQLite caches, economic ledgers, failed-run
  evidence and provenance. Do not overwrite these with a training matrix or put
  credentials/account secrets into a training dataset or Git.
- Reuse the existing versioned `qd013.controlled-episode.v1` JSONL export and
  `qd013.episode-export.v1` manifest for eligible replay output. JSONL is locally
  readable; no format migration is needed to make computation local. Source and
  cache SQLite files remain reusable local inputs.
- Training preparation must retain instrument identity, UTC timestamps and data
  availability, feature order/version, label status/known time, units, costs,
  provenance hashes and chronological split boundaries. Preserve invalid, open
  and immature records for audit with their existing statuses; they must not be
  relabelled as valid training targets. Existing QR feature/label and consumer
  contracts remain authoritative.
- A final feature/target matrix and fitted model have not been produced by this
  instruction. Feature/label schema or exporter changes require the existing
  QD/QR review process. This instruction does not resume the paused replay or
  authorize model/scaler/calibrator fitting.

## Verified current state

Worktree: `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`, branch
`codex/qd-cache-safety`, inspected at commit
`71351b58d72b954417ba0e21299a415e4fcbcdc0`.

The local Python process PID 13604 running `research.qd016.entry` is suspended
(`Ts`), following the user's “先暂停”. Its latest committed ledger sequence is
1026, at `2024-02-04T03:00:00Z`. The process is retained in memory; no resume
signal was sent during this task. A future resume must account explicitly for
the suspended interval in the wall-clock budget; the current observation timer
uses monotonic elapsed time and does not automatically exclude suspension.

All following paths are local, relative to this worktree:

- Market cache: `research/.data/qd015/markets/`.
- Original continued account: `research/.data/qd015/full-p0-actual-1/P0-ALLOW_ALL/store/`.
- Continuation records: `research/.data/qd015/full-p0-resume-1/`.
- Intended completed export: `research/.data/qd015/full-p0-resume-1/export-P0-ALLOW_ALL/episodes.jsonl`
  with `manifest.json`. This export does **not** exist yet; only launch and
  activation records were present in the continuation directory when checked.

## Change report

- Completed: recorded the local-only data/computation preference and distinguished
  retained source/evidence from eligible training inputs and completed datasets.
- Files modified: this QD-owned report only. Shared journals and instructions
  remain untouched to preserve the existing concurrent-document editing boundary.
- Verification: inspected local process status, worktree/branch/status, existing
  exporter implementation and continuation directory. Documentation whitespace
  check only; no replay, data conversion, fitting or test suite was launched.
- Limitations: this is a persistent workflow instruction in the QD branch, not a
  repository-wide network enforcement mechanism or an implemented matrix builder.
- QR dependency: review any future feature/label/schema change and validate sample
  eligibility and temporal isolation before consuming a completed training set.
- Next step: retain the pause until the user requests resumption. Integrate this
  preference into shared policy when document ownership is handed back; no main
  merge, push, deployment or automatic restart is performed.
