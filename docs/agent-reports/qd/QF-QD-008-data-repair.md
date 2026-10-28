# QF-QD-008-DATA-REPAIR: engineering preflight

2026-10-28 Australia/Melbourne. **IMPLEMENTATION_IN_PROGRESS; MARK_DESIGN_ACCEPT.**
Current dispatch `QF-DISPATCH-20261028-QD008-EXACT-CANDIDATE-1` authorizes
the exact JSONL/UTC-microsecond builder and two bounded offline candidate builds.
Earlier preflight statements below are preserved history, superseded by the
frozen spec and explicit external human approval in the checkpoint appended here.
Dispatch `QF-DISPATCH-20261028-QD008-ENGINEERING-PREFLIGHT-1`.
QD worktree `/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`;
branch `codex/qd-cache-safety`; clean base
`45bf3e036516b97570b3630cc19684af26713132`. Only two new owned Markdown files:
`research/qd008/engineering-plan.md` and this report. Result commit is the commit
containing these files (`git log -1 --format='%H' -- research/qd008/engineering-plan.md`).

## Findings and completed work

The plan maps exact old source locations, downstream type boundaries, proposed
minimal builder/tests/artifacts, decimal arithmetic, aggregation/lineage, atomic
publication and restart/conflict behavior, literal acceptance cases and required
QR inputs. It does not decide whether archive or current REST is historical truth.

- QD004 parses Decimal and writes decimal text; it does not impose QD005's integer
  volume gate. Its diagnostic float conversion/QC arithmetic must not become a
  new exact-data path. Provider-omitted precision cannot be recovered locally.
- QD005 v2 both rejects fractional volume and sums `int(volume)`. Relaxing only
  validation would silently truncate. Preserve that frozen builder/data/spec and
  implement any approved repair as a separate candidate version.
- Native cache/SDK and ML use floating-point numeric frames, not an exact decimal
  transport. ML validation's temporary cast does not make original Decimal/string
  volume safe for later rolling/log operations. No direct adapter is approved.
- Whole-row source selection matters: the saved BTC case at `1787925600` differs
  in close (`79513.6` old / `79509.9` new) and volume (`108955655` / `108945436`).
  Saved ETH at `1774317600` has `5623243` old / `5623243.7` new volume. These are
  source observations, not a source-choice verdict or proof of full-period truth.

## Read-only checks and evidence

Verified fixed handoff:
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/readiness-r2-raw-evidence-handoff-r1.json`,
SHA256 `c5379daae4134db20f3077d1d15c8552798996b6cb4fd45de80290b03c5f6baa`.
Checked its exact hashes for seven necessary saved planning/result/comparison/
diagnostic files: recovery plan, recovery result, recovery comparison, cross-source
diagnosis, local archive-lineage audit, fixed-confirmation result and comparison.
Read their source-policy limitations without rerunning the full source audit.

Additionally hash/length-checked only the two saved confirmation bodies above:
BTC `2945128cd3c0eeff0bf01597bfa5a4dbb9bf3171ca9327f7bda482e130c1cc56`;
ETH `119e77121dddb18c0f963ed21adb5bbd08f5ddb5cc165ba2bd0621915b1e2874`.
Compared their exact strings to the corresponding old hourly rows after checking
v2 manifest SHA `cbe95174e6eca704353a06f89e68294ec58a81cc6a59f370bb424c51d1177808`
and both selected hourly file hashes. No dataset construction or full-market
revalidation was performed. Evidence reports of whole-period counts remain their
authors' observations, not new independent QD008 acceptance.

Inspected source fingerprints at the base:

| Source | SHA256 |
| --- | --- |
| `research/qd004/history_intake.py` | `79e35285ec03afa4b346cb41b441d7919a3489584f20f511dfbce2fe750b9afd` |
| `research/qd005/canonical_history.py` | `7f2e0a11b96c97d833437b2c4dcdf20337a56e2199b05f4e153ac5ec92263de5` |
| `src/crypto_ml.py` | `63d0d9569cb261c83867b18cde03f9f74c7b54626172eeb5bb36eac09c19a7f6` |
| `src/data_fetcher.py` | `624339d97918bc7ab99357e0d0513a9d7f356805ee5f6bd01fd7f03a987a2fdf` |
| `research/qr003/replay_probe.py` | `4a0e520fa7b0a98565435aec07936bd4425592850a6e2e64b2116acd7d1d45aa` |

Checks used the existing read-only interpreter and stdlib, `rg`/source reads and
Git inspection; no imports of application/replay code. Documentation-only scope:
no new tests or runtime regression suite needed or claimed. Document structure,
literal acceptance arithmetic, diff/staged whitespace and exact two-file scope
are checked before commit. No dependency installation or network access occurred.

Main preservation matched HEAD `cae0d2395adf2cd3905e41cb1c16748c8247c32c`, staged
binary-diff SHA `c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce`
and index-byte SHA `7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80`.
QD007 code/tests/schema/candidates, old raw/v1/v2 and native features/risk/strategy
remain unchanged. Shared journals remain paused; this role report records progress.

## Dependencies, limits and stop

QR must hand off a precise frozen source policy/spec and independent acceptance
criteria, including full-row partitions, disputed close/prefix assumptions,
availability/decimal/duplicate rules and exact input hashes. Any necessary user
source-choice decision must precede the actual build. The plan enumerates those
inputs; no in-progress QR file was read or polled.

Next: coordinator allocates the small implementation/test/output scope against
that frozen spec. Stop after this document commit. No implementation, new raw
acquisition, market build/replay, labels/features, model/scaler fit, activation,
main edit, push/merge, app/engine launch, Windows/NAS change or scheduling occurred.
Data repair feasibility is not dataset acceptance, ledger independent PASS,
economic label validity, training readiness or a profitability claim.

## QD data-owner review: MARK_EXACT_OBSERVATION_ALIAS_R2 — ACCEPT

Decision: **ACCEPT as a bounded representation/continuation design**, not MARK
implementation/data acceptance or permission to execute requests in this task.
Exact QR commit `8b9e85e5c041fcf9167940520035693562f761ba`; working and committed
bytes match amendment SHA256
`0b33bf4272bbb87bb33d1e19fe27ab7e5a7765ddd2b98baf4a4678530bc17ece`.
Protocol SHA `c71cae75331346e000c231c522db88e383a41cbefcdfb7deb44fd97f8fd67327`;
machine-spec SHA `cd0e123d019b428e7bd12754e553c0322d4aac5593537b07752bab777280bdc0`.

The rule is implementable without modifying or discarding raw evidence: within
one fixed raw object/instrument/month, only a maximal adjacent run with all four
parsed original strings identical aliases to the first physical row. Preserve
every physical row in its consecutive source_rows group, primary first row,
alias_count and exact raw text. A greater timestamp creates a new observation
even at identical prices; equal numeric time with any different spelling/value
and descending time still reject the whole object. Runs spanning read chunks
require retained parser state, not per-chunk deduplication. No cross-object alias
or general sorting/cleaning is inferred. Version2 point identity includes namespace,
version, instrument, raw hash and first physical row; downstream references must
use that version/complete group, without double valuation or changed availability.

Budget arithmetic agrees: 98-17=81 attempts remaining, 71 fixed GETs plus at most
10 global retries; 2147483648-34975986=2112507662 bytes. Reuse/hash-check all19 old
objects, including the originally quarantined complete body, in a new manifest;
do not rewrite the old result or re-fetch those bodies. Existing and new audit
bytes count toward the same16MiB ceiling. The old continuous deadline has expired.
The explicit proposed continuation inherits26.732s and permits1173.268s additional
active processing (sum1200s), including revalidation/requests/waits/checks. Paused
human review is excluded only by this explicit amendment; this is not a fresh
20-minute reset. A separate coordinator continuation dispatch must activate it.
All remaining per-object/global disk, bytes, time, retry and stop rules stand.

Required-query coverage remains NOT_EVALUATED until both accepted delay/age
scenarios are checked against explicit required queries, including all gaps and
month boundaries. No finite count or removal of five aliases proves support.
Unsupported queries retain null/reasons and risk blocking. This document review
does not reparse MARK, run QR oracle tests, implement conversion or change the
coordinator collector. Those future owner tests remain required as specified.

## Exact OHLCV implementation handoff accepted

Human decision QR008-DATA-SOURCE-1 is supplied by external companion
`qr008-source-policy-approval.json`, verified SHA256
`d3eeb12d0d5348f769a9493a215eb32e2f3be40c13ed4a0eb5607e7cef9effa0` in the fixed
coordination directory. It binds the exact QR spec/commit and policy
ARCHIVE_PREFIX_REST_COMPLETE_ROWS_FROM_20251201_R1, including the BTC close change.
QR's original null approval fields remain historical and are not rewritten.
Only complete rows are selected: archive before2025-12-01, frozen decimal REST
afterward until2026-10-01, for both instruments. Native code and old data stay frozen.

Only the five allocated QD paths and two new ignored output roots are permitted.
Candidate status will be PENDING_INDEPENDENT_REVIEW. No independent candidate
checker has executed: manifest will explicitly distinguish null checker execution
from the known normative QR commit and oracle script hashes. No ambiguous self-
acceptance is inferred from the schema's generic checker-identity requirement.
No network, funding/MARK transform, native adapter, replay/labels or fitting is
part of this implementation. Subsequent sections will record actual code/tests,
two-build resource usage, hashes, preservation and remaining independent gates.

## Builder implementation and synthetic verification

Implemented only allocated `research/qd008/repair_history.py` and
`tests/test_qd_data_repair.py`, with current-contract notes prepended to the plan.
Standard library only, no download/app/exchange/model imports. Raw/source hashes,
full grids, whole-row selection, v2 lineage and independently recomputed4221-hour
differences are checked before deriving exact hourly/4h/day closed-schema rows.
Fraction arithmetic and plain canonical strings preserve fractional contracts;
embedded ordered raw and direct-hourly parent references remain fully auditable.
The input catalogue binds selected/shadow/corroborating objects and full request/
response provenance available in the immutable receipts; unavailable historical
arrival/revisions stay UNKNOWN. Canonical catalogue and per-row identity preimages
follow the frozen spec, independent of the later output manifest.

Both roots use a dedicated permanent publication lock and macOS RENAME_EXCL
(Linux renameat2 RENAME_NOREPLACE supported but not target-tested), not an
overwrite-capable rename. Files are exclusive, fsynced, manifest last; staged
inventory/rows and exact bytes are reread against frozen-raw recomputation, and
all148 input identities/spec/approval are rechecked before publication. Failures
retain staging and publish no final candidate. Fixed two full-build destination
names and retained-attempt rejection prevent an implicit third build/retry.
No power-loss/full filesystem durability or network filesystem claim is made.

Focused socket-blocked producer tests: **26 methods passed** (0.122s). They include
literal3.555/21.33 aggregation, >2^53, >28-digit and129-digit sums, hostile Decimal
context, true zero versus unknown, strict type/field/domain rejection, raw grid
errors, row/hash preimages, complete whole-row close/volume conflicts and delta
preservation, ordered direct-hourly lineage, cutoff availability, legal future raw
mutation/full-catalog rehash with invariant past economic projection, rehashed
value/lineage corruption, byte reproducibility, symlink/inventory rejection,
concurrent publishers, kernel no-replace races, disk/input failure and process
death before publication. All fixtures are small synthetic files; no full build
is counted as a test. An initial synthetic failure found receipt lookup assumed
unique hashes across instruments; matching source_id plus hash resolves it without
changing source-ref schema. No failed test or source disagreement was suppressed.

Exact implementation SHA256:
`9e0d36333fc0951f5b7cc51eb10b2873a115f91239fba550bdfd8a178b244448`.
Exact producer-test SHA256:
`ec0306a8ceb3b1f846862097959f4f26e7e5096381bcee3633327abbed10bb0c`.
The commit containing these bytes is the pre-build code identity; full candidate
generation remains bounded to two attempts after that commit, not before it.

Commands from this worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
import socket, unittest
def offline(*a, **k): raise AssertionError('QD008 offline only')
socket.create_connection = socket.socket.connect = socket.socket.connect_ex = offline
result = unittest.TextTestRunner(verbosity=1).run(
    unittest.defaultTestLoader.discover('tests', pattern='test_qd_data_repair.py'))
raise SystemExit(not result.wasSuccessful())
PY
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python research/qd005/run_offline_tests.py
git diff --check
git diff --cached --check
```

Pre-build preservation: all7 frozen main fingerprints match, including full
`git status --porcelain --untracked-files=all` SHA
`2a358fa935fea949c6c34fba46c5f07d6e08f6f1ed5066da7e6f12c570904649` /72 entries
and unstaged binary-diff SHA
`35d57c81948f2de4c2c6e56db9cda60a507b06e0aa39583585cdb30505d8fc2d`.
An initial check using compact untracked-directory status differed in command
format only; the exact full-status command matches the frozen baseline.
All276 old evidence files (v1, both v2 roots, QD007 candidate and four QD007
code/schema/test/report paths) have sorted path->SHA inventory fingerprint
`cf6326f363b42995db505c55439c56ae6a1d013be0c4a87bb875fed526a340fc`.
The inventory hash is SHA256 of compact sorted-key UTF-8 JSON, paths relative to
the QD worktree. It will be rechecked after both builds. These read-only hashes
are preservation evidence, not fresh market/ledger independent acceptance.

Final full offline Python regression after the last test refinements:
**288 passed in11.361s**, using the existing guarded socket-blocked runner above.
Mock HTTP200/500 and injected disk-failure logs are fixtures, not real requests.
No frontend/runtime code changed; no new JS run or old JS pass is claimed here.
