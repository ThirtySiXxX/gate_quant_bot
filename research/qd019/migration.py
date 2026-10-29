"""Explicit relocation of a frozen QD016 account; original identities survive.

Only IO roots, resident-working policy and admitted host-build identity differ.
Original financial modules, packets, GENESIS, manifests and control history stay
unchanged. A saved numerical seal is checked before publishing new commits.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import platform
import sys


SCHEMA = 'qd019.local-migration.v1'
STORE = 'full-p0-actual-1/P0-ALLOW_ALL/store'
RECORD = 'MIGRATION-RESUME-1.json'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def relative(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'UNSAFE_BUNDLE_PATH')
    root = Path(root).resolve()
    result = root / p
    require(not any(x.is_symlink() for x in (result, *result.parents)), 'BUNDLE_SYMLINK')
    require(result.resolve().is_relative_to(root), 'BUNDLE_PATH_ESCAPE')
    return result


def inventory(root):
    root = Path(root)
    result = {}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'BUNDLE_SYMLINK')
        if p.is_file():
            result[p.relative_to(root).as_posix()] = dict(bytes=p.stat().st_size, sha256=sha(p))
    return result


def verify_inventory(root, expected):
    actual = inventory(root)
    require(actual == expected, 'BUNDLE_FILE_INTEGRITY_MISMATCH')
    return sum(x['bytes'] for x in actual.values())


def runtime():
    import numpy as np
    import pandas as pd
    import sqlite3
    return dict(python=sys.version, python_version=platform.python_version(),
                implementation=platform.python_implementation(), numpy=np.__version__,
                pandas=pd.__version__, sqlite=sqlite3.sqlite_version, platform=sys.platform,
                machine=platform.machine())


def admit_runtime(expected):
    actual = runtime()
    require(actual['implementation'] == 'CPython' and actual['python_version'] == expected['python_version'],
            'PYTHON_VERSION_MISMATCH')
    require(actual['numpy'] == expected['numpy'] and actual['pandas'] == expected['pandas'],
            'NUMERIC_DEPENDENCY_VERSION_MISMATCH')
    require(sys.platform in ('darwin', 'linux'), 'USE_WSL2_UBUNTU_NOT_NATIVE_WINDOWS')
    return actual


def verify_code(root, pins):
    for name, expected in pins.items():
        require(sha(relative(root, name)) == expected, 'CODE_IDENTITY_MISMATCH:' + name)


def relocate_path(value, old_root, new_root):
    p, old = Path(value), Path(old_root)
    require(p.is_absolute(), 'RESOURCE_PATH_NOT_ABSOLUTE')
    require('..' not in p.parts, 'RESOURCE_PATH_TRAVERSAL')
    if p.is_relative_to(old):
        return str(Path(new_root).resolve() / p.relative_to(old))
    new = Path(new_root).resolve()
    require(p.is_relative_to(new), 'UNDECLARED_RESOURCE_PATH:' + value)
    return str(p)


def install_budgets(data, manifest):
    """Verify the old chain, map its size keys in memory, keep every write debit."""
    from research.qd009 import streaming_ledger as sl

    class RelocatedBudget(sl.ResourceBudget):
        def __init__(self, root, limit, book=None, reserve=262144):
            self.root = Path(root).resolve()
            self.limit, self.reserve = limit, min(reserve, limit // 8)
            self.book = Path(book or self.root / 'RESOURCE_LOG')
            self.sizes = {}; self.total = self.written = self.grant = 0
            self.last_error = None; self.emergency = False; self.parent = None
            self.previous = '0' * 64
            with self.book.open('rb') as source:
                for raw in source:
                    row = sl.load_json(raw); h = row.pop('hash')
                    sl.need(row['previous'] == self.previous and sl.digest(row) == h,
                            'STORE_INTEGRITY_FAILURE')
                    self.previous = h
                    self.grant = max(self.grant, row.get('write_upper', 0))
                    if row['kind'] == 'size':
                        name = relocate_path(row['path'], manifest['old_data_root'], data)
                        self.sizes[name] = row['size']
                    elif row['kind'] == 'write_grant':
                        self.grant = row['value']
            self.written = self.grant
            for p in self.root.rglob('*'):
                sl.need(not p.is_symlink(), 'STORE_INTEGRITY_FAILURE')
                if p.is_file() and p != self.book:
                    self.sizes[str(p)] = max(self.sizes.get(str(p), 0), p.stat().st_size)
            self.total = sum(self.sizes.values())

    total = RelocatedBudget(data, manifest['outer_limits']['output_bytes'] - 65536,
                            Path(data) / 'aggregate-resource.jsonl', 1048576)
    store = Path(data) / STORE
    req = read(store / 'GENESIS')
    child = RelocatedBudget(store, req['config']['limits']['max_store_bytes'])
    child.parent = total
    require(total.total + total.book.stat().st_size <= total.limit, 'TOTAL_STORAGE_LIMIT')
    require(child.total + child.book.stat().st_size <= child.limit, 'STORE_STORAGE_LIMIT')
    sl._GLOBAL_BUDGET = total
    sl._BUDGETS[str(store.resolve())] = child
    return total, child


def verify_chain(store, expected_head):
    """Hash all published journals without replaying old financial decisions."""
    from research.qd009 import streaming_ledger as sl
    from research.qd015 import journal
    store = Path(store); req = read(store / 'GENESIS'); previous = None
    for n in range(1, expected_head['committed_seq'] + 1):
        m = read(store / f'manifest-{n:08}.json')
        require(m['seq'] == n, 'MANIFEST_SEQUENCE_MISMATCH')
        if previous is not None:
            require(m['before'] == previous and m['previous_prefix'] == previous['audit_prefix'],
                    'MANIFEST_CHAIN_MISMATCH')
        require(len(m['files']) == 1, 'UNSUPPORTED_JOURNAL_LAYOUT')
        ref = m['files'][0]; p = relative(store, ref['relative_path'])
        require(p.stat().st_size == ref['bytes'] and sha(p) == ref['sha256'], 'JOURNAL_HASH_MISMATCH')
        raw = p.read_bytes()
        if 'journal_storage' in req['config']:
            raw = journal.decode(raw, req['config']['journal_storage'])
        payload = sl.load_json(raw)
        require(sl.digest(payload['request']) == m['request_sha256'] and
                payload['receipt']['after'] == m['after'], 'JOURNAL_REQUEST_MISMATCH')
        previous = dict(m['after'], audit_prefix=sl.digest(m))
    require(previous == expected_head, 'FROZEN_HEAD_CHAIN_MISMATCH')


def open_ledger(data, manifest, process_bound, *, verify_seals=True, reference=False):
    from research.qd009 import streaming_ledger as sl
    from research.qd011.ports import ControlledPort, RUNTIME
    from research.qd016.resident import ContinuationLedger
    data = Path(data).resolve(); store = data / STORE
    expected_runtime = manifest['source_runtime']['port_runtime']
    actual = admit_runtime(manifest['source_runtime'])

    class AdmittedPort(ControlledPort):
        def validate_input(self, packet):
            # Preserve the actual recorded packet/config; adapt only the host
            # validation argument after explicit version admission above.
            sl.need(packet['causal_config']['runtime'] == expected_runtime, 'UNSUPPORTED_GENERATOR')
            adapted = dict(packet, causal_config=dict(packet['causal_config'], runtime=RUNTIME))
            super().validate_input(adapted)

    req = read(store / 'GENESIS')
    if reference:
        require(RUNTIME == expected_runtime, 'REFERENCE_REQUIRES_ORIGINAL_RUNTIME')
    for definition in req['config']['adapters']:
        require(definition['causal_config']['runtime'] == expected_runtime, 'MIXED_SOURCE_RUNTIMES')
        require(sl.digest(definition) not in sl._PORTS, 'MIGRATION_REQUIRES_FRESH_PROCESS')
        sl.register_port(definition, ControlledPort() if reference else AdmittedPort())

    resident = read(store / 'RESIDENT-CONTINUATION-1.json')

    class RelocatedLedger(ContinuationLedger):
        def _load_sources(self):
            original = self.request['source_roots']
            self.request['source_roots'] = [dict(r, path=relocate_path(r['path'], manifest['old_data_root'], data))
                                            for r in original]
            try:
                return super()._load_sources()
            finally:
                self.request['source_roots'] = original

        def _rebuild_index(self):
            # Do not accidentally repeat the whole accepted financial history.
            raise sl.LedgerError('MIGRATION_INDEX_REBUILD_REQUIRES_REVIEW')

        def _remember_view(self, view, roots):
            seal = self.seals.get((view['knowledge_cutoff']['at_us'], view['knowledge_cutoff']['slot']))
            if seal is not None:
                sl.need(view['economic_state_sha256'] == seal['economic_state_sha256'] and
                        view['view_sha256'] == seal['view_sha256'], 'MIGRATION_NUMERIC_DIVERGENCE')
                self.seals_passed.add(view['knowledge_cutoff']['at_us'])
            return super()._remember_view(view, roots)

    # These are accessed only by as_known/advance, after construction.
    RelocatedLedger.seals = {(r['cutoff']['at_us'], r['cutoff']['slot']): r
                             for r in manifest.get('numeric_seals', [])} if verify_seals else {}
    ledger = RelocatedLedger(store, operation=resident['operation'],
                             record_name='RESIDENT-CONTINUATION-1.json', process_bound=process_bound)
    ledger.seals_passed = set()
    ledger.admitted_runtime = actual
    return ledger


def activate(ledger, manifest):
    """Resolve the frozen *unvalidated, unpublished* request from durable proof."""
    from research.qd009 import streaming_ledger as sl
    from research.qd012.actual_snapshot_entry import durable_new
    store = ledger.root; expected = manifest['frozen']
    require(not (store / RECORD).exists(), 'MIGRATION_ALREADY_CONSUMED_NO_RETRY')
    require(ledger.head == expected['head'] and read(store / 'CONTROL') == expected['control'],
            'FROZEN_POINTER_MISMATCH')
    require(ledger.control['status'] == 'ACTIVE' and not ledger.control['validated'], 'UNEXPECTED_FROZEN_STATUS')
    guard = ledger.control['guard']
    require(guard is not None and guard['kind'] == 'write_guard', 'EXPECTED_UNRESOLVED_GUARD')
    path = relative(store, guard['guard_input']['relative_path'])
    require(path.stat().st_size == guard['guard_input']['bytes'] and sha(path) == guard['guard_input']['sha256'],
            'GUARD_BYTES_MISMATCH')
    request = read(path)
    require(sl.digest(request) == guard['request_sha256'] == expected['guard_request_sha256'], 'GUARD_REQUEST_MISMATCH')
    sl.shape(request, 'request_id expected_audit_prefix through_us imported generated')
    require(request['expected_audit_prefix'] == ledger.head['audit_prefix'] and
            not request['imported'] and not request['generated'], 'UNEXPECTED_PENDING_REQUEST')
    n = ledger.head['committed_seq'] + 1
    require(not list(store.glob(f'journal-{n:08}.*')) and not (store / f'manifest-{n:08}.json').exists(),
            'PENDING_PUBLICATION_REQUIRES_REVIEW')
    require(ledger.index.db.execute('SELECT 1 FROM requests WHERE id=?', (request['request_id'],)).fetchone() is None,
            'PENDING_REQUEST_ALREADY_COMMITTED')
    require(ledger.index.db.execute('SELECT v FROM local_meta WHERE k="head"').fetchone() == (ledger.head['audit_prefix'],),
            'INDEX_HEAD_MISMATCH')
    payload = ledger._payload(ledger.head['committed_seq'])
    require(payload['roots'] == ledger.state.roots and payload['receipt']['after']['economic_state_sha256'] ==
            ledger.head['economic_state_sha256'], 'COMMITTED_STATE_MISMATCH')
    plan = ledger.config['_plan_index'].times
    require(next(t for t in plan if t > ledger.head['cutoff']['at_us']) == request['through_us'], 'PENDING_TICK_MISMATCH')
    before = deepcopy(ledger.spent)
    record = dict(schema=SCHEMA, authorization_ref=manifest['authorization_ref'],
                  frozen=expected, original_spent=before, runtime=ledger.admitted_runtime,
                  original_runtime=manifest['source_runtime'], paths=dict(original=manifest['old_data_root'],
                  current=str(store.parents[2])), numeric_seals_sha256=sl.digest(manifest.get('numeric_seals', [])),
                  retained_genesis_sha256=sha(store / 'GENESIS'), training_authorized=False)
    record['sha256'] = sl.digest(record)
    raw_size = len(sl.canonical_bytes(record)) + 1
    ledger.budget.issue(store / RECORD, raw_size, raw_size)
    durable_new(store / RECORD, record, 1048576)
    ledger.guard_input = guard['guard_input']
    ledger._control('resolution', request, 'not_committed')
    ledger.spent['active_wall_us'] += manifest['source_unpersisted_active_us_upper_bound']
    ledger.spent['attempts_started'] += 1
    ledger._save_spent()
    require(ledger.head == expected['head'] and ledger.current_head()['status'] == 'ACTIVE', 'ACTIVATION_CHANGED_HEAD')
    return record
