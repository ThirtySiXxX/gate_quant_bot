"""Admit an exported SQLite DB-API backend before importing the pinned ledger.

Astral Linux CPython has built-in _sqlite3 with hidden C symbols. A separately
pinned DB-API extension supplies BOTH Python connections and their VFS symbols;
loading an unrelated system libsqlite3 would not enforce connection write caps.
"""
import ctypes
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile
from .migration import sha, require

PACKAGE = 'pysqlite3-binary'
VERSION = '0.5.4.post2'
BINARY_SHA256 = 'cd39689d669fe7019ae9be11dd4106dd6d8560085a257bb69c0f9605c824ba33'
_INFO = None


def admitted_code_pins(base, release):
    pins = dict(base); fix = release.get('sqlite_host_fix')
    if not fix:
        return pins
    require(fix['schema'] == 'qd020.sqlite-host-fix.v1' and
            fix['base_manifest_sha256'] == release['manifest_sha256'], 'HOST_FIX_RELEASE_MISMATCH')
    for name, change in fix['replacements'].items():
        require(pins.get(name) == change['before'], 'HOST_FIX_BASE_CODE_MISMATCH:' + name)
        pins[name] = change['after']
    for name, digest in fix['additional'].items():
        require(name not in pins, 'HOST_FIX_DUPLICATE_CODE_PIN')
        pins[name] = digest
    return pins


def bind_backend(dbapi, extension):
    """Single connection implementation for SQLite consumers and the C shim."""
    require('research.qd009.streaming_ledger' not in sys.modules, 'SQLITE_BACKEND_MUST_BE_SELECTED_BEFORE_LEDGER')
    sys.modules['sqlite3'] = dbapi
    sys.modules['sqlite3.dbapi2'] = importlib.import_module(dbapi.__name__ + '.dbapi2')
    sys.modules['_sqlite3'] = extension


def select_backend():
    dbapi = importlib.import_module('sqlite3'); extension = importlib.import_module('_sqlite3')
    if getattr(extension, '__file__', None):
        return dict(mode='NATIVE_SHARED_EXTENSION', sqlite_version=dbapi.sqlite_version,
                    library_sha256=sha(extension.__file__))
    require(sys.platform == 'linux' and platform.machine() == 'x86_64',
            'BUILTIN_SQLITE_REQUIRES_APPROVED_LINUX_X86_64_BACKEND')
    try:
        installed = importlib.metadata.version(PACKAGE)
    except importlib.metadata.PackageNotFoundError as e:
        raise ValueError('INSTALL_REQUIREMENTS_QD020_LOCK_BEFORE_RESUME') from e
    require(installed == VERSION, 'SQLITE_BACKEND_PACKAGE_VERSION_MISMATCH')
    candidate = importlib.import_module('pysqlite3')
    native = importlib.import_module('pysqlite3._sqlite3')
    require(sha(native.__file__) == BINARY_SHA256, 'SQLITE_BACKEND_BINARY_HASH_MISMATCH')
    original_version = dbapi.sqlite_version
    bind_backend(candidate, native)
    return dict(mode='APPROVED_PYSQLITE3_BINARY', package=PACKAGE, package_version=VERSION,
                library_sha256=BINARY_SHA256, original_builtin_sqlite_version=original_version,
                sqlite_version=candidate.sqlite_version)


def probe_vfs(sl):
    """Real connection writes and real quota rejection, entirely in scratch."""
    dbapi = importlib.import_module('sqlite3')
    f = sl._SQL.sqlite3_libversion; f.argtypes = []; f.restype = ctypes.c_char_p
    require(f().decode() == dbapi.sqlite_version, 'SQLITE_C_AND_DBAPI_VERSION_MISMATCH')
    with tempfile.TemporaryDirectory(prefix='qd020-vfs-') as directory:
        root = Path(directory).resolve(); budget = sl.ResourceBudget(root, 2*1024**2)
        key = str(root); require(key not in sl._BUDGETS, 'HOST_PROBE_BUDGET_CONFLICT')
        sl._BUDGETS[key] = budget; db = None
        try:
            path = root/'probe.sqlite3'
            db = dbapi.connect(path.as_uri()+'?vfs=qd009-budget-v1', uri=True, factory=sl._BudgetConnection)
            db.budget = budget
            db.execute('CREATE TABLE probe(value BLOB)'); db.execute('INSERT INTO probe VALUES (?)',(b'approved',)); db.commit()
            require(db.execute('SELECT value FROM probe').fetchone() == (b'approved',) and budget.written > 0,
                    'SQLITE_VFS_WRITES_NOT_OBSERVED')
            original_limit = budget.limit; denied = False
            try:
                budget.limit = budget.total + budget.book.stat().st_size
                try:
                    db.execute('INSERT INTO probe VALUES (?)',(b'x'*65536,)); db.commit()
                except sl.LedgerError as e:
                    require(e.code == 'RESOURCE_EXHAUSTED', 'UNEXPECTED_HOST_PROBE_ERROR')
                    denied = True
            finally:
                budget.limit = original_limit; budget.emergency = False
                db.rollback()
            require(denied and db.execute('SELECT count(*) FROM probe').fetchone() == (1,),
                    'SQLITE_VFS_QUOTA_REJECTION_FAILED')
            return dict(status='PASS', writes_observed=True, oversized_write_rejected=True,
                        write_debit_bytes=budget.written, account_files_opened=False)
        finally:
            if db is not None:
                db.close()
            sl._BUDGETS.pop(key, None)


def prepare_sqlite_host():
    global _INFO
    if _INFO is None:
        info = select_backend()
        sl = importlib.import_module('research.qd009.streaming_ledger')
        info['vfs_probe'] = probe_vfs(sl)
        _INFO = info
    return dict(_INFO)


def prior_host_failure(root, manifest_sha256):
    path = Path(root)/'research/.data/qd019-import/host-fix-1.json'
    if not path.exists():
        return dict(wall_seconds=0, cpu_seconds=0, preadmission_failures=0)
    record = json.loads(path.read_bytes())
    require(record['schema'] == 'qd020.preadmission-failure.v1' and
            record['base_manifest_sha256'] == manifest_sha256, 'HOST_FAILURE_ACCOUNTING_BINDING_MISMATCH')
    for source in record['evidence']:
        p = Path(root)/source['path']
        require(p.resolve().is_relative_to(Path(root).resolve()) and sha(p) == source['sha256'],
                'HOST_FAILURE_EVIDENCE_CHANGED')
    require(record['wall_seconds_upper_bound'] >= 0 and record['cpu_seconds_upper_bound'] >= 0,
            'NEGATIVE_HOST_FAILURE_ACCOUNTING')
    return dict(wall_seconds=record['wall_seconds_upper_bound'], cpu_seconds=record['cpu_seconds_upper_bound'],
                preadmission_failures=record['preadmission_failures'], receipt_sha256=sha(path))
