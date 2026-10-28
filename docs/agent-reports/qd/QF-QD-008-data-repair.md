# QF-QD-008-DATA-REPAIR: engineering preflight

2026-10-28 Australia/Melbourne. **PLAN_COMPLETE_PENDING_FROZEN_QR_SPEC.**
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
