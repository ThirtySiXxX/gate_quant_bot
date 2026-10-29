# QF-QD-020 — Built-in SQLite host compatibility repair

2026-10-29 Australia/Melbourne. QD worktree/branch unchanged, base3adfd08.
User's first Windows/WSL actual startup failed with
`AttributeError:module '_sqlite3' has no attribute '__file__'`.
The failure occurs before launch receipt/account admission, not at a financial
tick. Keep the user's original console/return archive, dataset and source PID13604
suspended. No credential, live service, trading rule or shared schema change.

Claim: new SQLite host adapter, its targeted tests, small repair installer,
`requirements-qd020.lock`; QD019 entry/collector/setup/release pin overlay and
Windows/QD reports. Original47source pins, data transfer manifest/cache/journal
identities remain unchanged; no600MBdataset regeneration or counter reset.

The exact Astral20250918Linux3.13.7binary was inspected: _sqlite3 is built in and
SQLite C functions are not exported. CDLL(None) cannot repair this build. Loading
an arbitrary system SQLite would register the VFS in a different library and
could bypass quotas; it is explicitly not used.

Use a fixed CPython3.13Linuxx86_64 pysqlite3-binary wheel for both DB-API
connections and C VFS symbols. Its public wheel SHA256 and extension binary SHA256
are pinned. The standard dynamic extension remains in use on native hosts.
Before any account is opened, a scratch-only connection must prove real writes
are charged and a real oversized write is rejected. Numerical checkpoint seals
and all financial checks remain. Tests/publication evidence follows.

## Completed checks and repair delivery

- Ten focused checks passed: fixed binary/version rejection, no system SQLite
  fallback, explicit code-pin overlay rejection, real SQLite writes/oversized
  write rejection, retained failed-start evidence/conservative budget debit,
  existing OFF/inventory/path/runtime checks and return-bundle allowlist.
- Built the pysqlite3 DB-API0.5.4 against a separate SQLite3.50.4 library in an
  isolated Mac test directory (the existing venv was not modified). Both the
  standard driver and this separate DB-API passed actual VFS write/quota tests.
  Initial pip builds failed because its macOS build overrides compiler include
  settings and uses SDK headers without load-extension declarations; an isolated
  direct build against the upstream amalgamation succeeded. This is test tooling,
  not a dependency that the Windows user must build.
- Actual account-copy validation with that separate DB-API passed16/16reference
  states,1026→1042, preserving the known economic hash
  `b4eadcc678fa8a1e17dac97956ea2efbbf40cf09c3c224f671201388ecd69d8e`.
  Wall88.511637/CPU85.030205s, peak327,385,088B. Original account/PID13604 remains
  paused at1026. No real training/full replay was performed on this Mac.
- Linux CPython3.13wheel from PyPI was downloaded and its ELF exports inspected:
  required sqlite3_vfs_find/register/libversion functions are exported in the
  selected pysqlite3 extension. Full native Linux/WSL execution remains a target
  startup check, not a claimed local test. The exact Windows wheel has SHA256
  `930c7597a0863ef3da721e538756c2768cee14cb9b8d2c037263d061b24f66a5`,
  selected C extension SHA256
  `cd39689d669fe7019ae9be11dd4106dd6d8560085a257bb69c0f9605c824ba33`.

The small installer is bound to the user's reported return archive SHA256
`266a25845aa1996b71e4bfb718dc5de428e436527897b0e795681bc372e6f184`.
It proves failure before account admission, finds the matching UTC-named console
log and conservatively charges its interval plus rounding; unavailable prior CPU
measurement is bounded by that interval times all logical CPUs. This is an
explicit conservative estimate, not measured CPU; it may overcharge. Original
failure archive/logs are retained and included by hash in a new receipt outside
the frozen data directory. No attempt or SPENT counter is reset.

Three QD019 source/script pins have explicit before→after replacements in the
source-controlled release overlay; other old pins and the original data manifest
and600MBarchive hashes stay valid. Two new host/requirement pins are added. The
installer checks original code hashes before replacing files, backs up old source,
refuses already admitted accounts or changed checkpoint pointers, installs only
the supplied pinned wheel without a package-index/dependency upgrade, then runs
the expanded --check. It does not launch financial replay automatically.

Files modified: QD019 entry/collector/release and setup script; new host module,
fixed extra dependency lock, repair installer/test, this report and Windows guide.
No QD007–QD016 financial code, QR code, shared contracts/journals or main changed.
Package/build evidence is local under Downloads/qd020*; no datasets were uploaded.

Next: user applies the small patch in Ubuntu, sees READY_FOR_LOCAL_RESUME plus
the VFS probe, then invokes the original run-local-replay.sh. New errors remain
fail-closed; do not remove launch/control records to retry. QR review remains
required before shared/main integration or any training approval; this repair
does not approve a model, alter trading rules, or claim a full2026replay result.
