"""Default-OFF local QD013 export consumer; no replay, estimator or raw loader.

Reads the published SQLite/JSONL formats, not the QD application or its imports.
Only the pinned QR014 feature/label functions perform research calculations.
The import request is a coordinator-supplied binding, not a completeness proof.
"""
import argparse
from collections import Counter
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from research.qr014 import feature_samples as qr

SCHEMA = 'qr015.local-dataset.v1'
REQUEST_SCHEMA = 'qr015.import-request.v1'
QD_COMMIT = '9adcbb01a584b35ba384e1ca6bc461d97a782469'
QD_MANIFEST_SHA256 = 'd6d26df2f17b818e1d3a0518c226102a38955ff8c54cf68eba9e82343d18f82a'
QR014_COMMIT = 'f2c931b8335ca8b1840f22d346a040446c50abb2'
QR014_MODULE_SHA256 = '1f98cf75e68be73683f174b9eeac34db978b2dd331973dacad0d3b65f69906c5'
QD_CODE = {
    'research/qd013/exports.py': 'bbd8e0f79fa4ff597f064ade8fb70eae1d5e323fdb3d9a454a069526bd842f46',
    'research/qd013/market.py': 'c0017f6c5d8d464395888a8c91d284dbdf9cd85b8b457dee87c5e99e605e2729',
    'research/qd013/inputs.py': '545b6959faf9113084286abf5ec133529feac8e98d46231c071e0b10b5977bed',
}
SOURCE_METADATA = {
    'ohlcv': 'c1e6056058fd312d472e96fddfea15e78c778847de9942e5757cb39ad2ac9b91',
    'funding': '176d0c987d23d4b29b7f901b7dfaa6eeffe56ad84bc57ee07f89a261dab65be5',
    'mark': '30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce',
    'mark_result': '3f601ebf45b2e97825b9c701234060a3348e47e508c28211b98572ed38f5a21e',
}


class DatasetError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise DatasetError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'DUPLICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def load(raw):
    def bad(value):
        raise DatasetError('NONFINITE_JSON:' + value)
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=bad)


def _hash(value):
    require(isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value), 'INVALID_SHA256')
    return value


def _text(value):
    require(isinstance(value, str) and bool(value.strip()), 'MISSING_BINDING')
    return value


def _integer(value, minimum=0):
    require(type(value) is int and value >= minimum, 'INVALID_NONNEGATIVE_INTEGER')
    return value


def _path(value):
    p = Path(value)
    require(p.is_absolute() and p.is_file() and not p.is_symlink(), 'LOCAL_REGULAR_FILE_REQUIRED')
    return p


def _stat(path):
    s = path.stat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def _small_json(path, expected_hash, limit=2 * 1024 * 1024):
    path = _path(path)
    require(path.stat().st_size <= limit, 'METADATA_SIZE_LIMIT')
    raw = path.read_bytes()
    require(digest(raw) == _hash(expected_hash), 'METADATA_HASH_MISMATCH')
    return load(raw)


def _request(request):
    require(request['schema'] == REQUEST_SCHEMA and request['training_authorized'] is False,
            'REQUEST_SCHEMA_OR_TRAINING_FLAG')
    require(request['input_kind'] in ('SYNTHETIC', 'ACTUAL'), 'INPUT_KIND_REQUIRED')
    require(request['qd_commit'] == QD_COMMIT and request['qd_manifest_sha256'] == QD_MANIFEST_SHA256
            and request['qd_code_sha256'] == QD_CODE, 'QD_VERSION_MISMATCH')
    require(digest(Path(qr.__file__).read_bytes()) == QR014_MODULE_SHA256, 'QR014_VERSION_MISMATCH')
    require(set(request['source_metadata']) == set(SOURCE_METADATA), 'SOURCE_SCOPE_MISMATCH')
    for value in request['source_metadata'].values():
        _hash(value)
    if request['input_kind'] == 'ACTUAL':
        require(request['source_metadata'] == SOURCE_METADATA, 'ACTUAL_SOURCE_VERSION_MISMATCH')
    _text(request['source_binding_ref'])
    b = request['binding']
    _text(b['account_id']); _text(b['trajectory_id'])
    require((b['scenario_id'], b['policy_id'], b['account_binding_id']) ==
            ('P0', 'ALLOW_ALL', 'QR010_SHARED_NATIVE_X10'), 'BASELINE_ONLY_NO_RELABEL')
    require(b['instruments'] == list(qr.INSTRUMENTS), 'BOTH_ASSET_SCOPE_REQUIRED')
    scope = b['scope']
    for key in ('warmup_start_us', 'initial_us', 'economic_end_us', 'tail_end_us'):
        _integer(scope[key])
    require(scope['warmup_start_us'] <= scope['initial_us'] < scope['economic_end_us']
            <= qr.ECONOMIC_END_US and scope['economic_end_us'] <= scope['tail_end_us']
            <= scope['economic_end_us'] + 2 * qr.HOUR_US, 'INVALID_DECLARED_SCOPE')
    for key in ('warmup_start_us', 'initial_us', 'economic_end_us'):
        require(scope[key] % qr.HOUR_US == 0, 'SCOPE_NOT_HOURLY')
    require(_integer(request['input_received_at_us']) <= _integer(request['assembled_at_us']),
            'INPUT_RECEIPT_IN_FUTURE')
    require(scope['tail_end_us'] <= request['input_received_at_us'], 'EXPORT_AFTER_RECEIPT')
    purge = request['purge']
    require(type(purge['complete']) is bool and purge['instruments'] == list(qr.INSTRUMENTS),
            'PURGE_SCOPE_REQUIRES_BOTH_ASSETS')
    _text(purge['source_ref'])
    if purge['complete']:
        require(scope['initial_us'] == qr.TRAIN_START_US and scope['economic_end_us'] == qr.ECONOMIC_END_US,
                'PARTIAL_SCOPE_CANNOT_CLAIM_COMPLETE_HELDOUT_INVENTORY')
    limits = request['limits']
    for name in ('max_records', 'max_input_bytes', 'max_row_bytes', 'max_output_bytes'):
        _integer(limits[name], 1)
    require(limits['max_row_bytes'] <= 2 * 1024 * 1024, 'ROW_LIMIT_TOO_LARGE')
    return scope


class ClosedHourReader:
    """Read-only consumer of MarketCache v1 storage; never builds native arrays.

    Metadata is matched to the complete handoff identity. Only needed hour cells
    are read/hash-checked. The producer's whole-cache digest is recorded, not
    recomputed by scanning unrelated market/mark/funding cells.
    """
    def __init__(self, spec, scope):
        self.path = _path(spec['path'])
        self.before = _stat(self.path)
        for suffix in ('-wal', '-journal', '-shm'):
            require(not Path(str(self.path) + suffix).exists(), 'CACHE_MUST_BE_PUBLISHED_IMMUTABLE')
        self.key = _hash(spec['key'])
        self.reads = 0
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        self.db.execute('PRAGMA query_only=ON')
        try:
            meta = {key: load(value) for key, value in self.db.execute('SELECT k,v FROM metadata')}
            require(meta['state'] == 'COMPLETE' and meta['schema'] == 'qd013.market-cache.v1'
                    and meta['key'] == self.key and meta['identity'] == spec['identity']
                    and meta['content_sha256'] == _hash(spec['content_sha256'])
                    and meta['rows'] == _integer(spec['rows']), 'CACHE_IDENTITY_MISMATCH')
            require(meta['identity']['schema'] == meta['schema']
                    and meta['identity']['scope'] == scope, 'CACHE_SCOPE_MISMATCH')
            # sources/code/config are producer-owned opaque structures, pinned
            # whole by the request; their relationship is attested by its owner.
            for name in ('sources', 'code', 'config', 'availability', 'decimal_codec'):
                require(bool(meta['identity'][name]), 'CACHE_IDENTITY_FIELD_MISSING:' + name)
        except BaseException:
            self.db.close()
            raise

    def candles(self, instrument, decision):
        for opened in range(decision - 169 * qr.HOUR_US, decision, qr.HOUR_US):
            rows = self.db.execute('SELECT v,sha FROM cells WHERE kind=? AND inst=? AND at=?',
                                   ('hour', instrument, opened)).fetchmany(2)
            require(len(rows) == 1, 'MISSING_OR_DUPLICATE_CLOSED_HOUR')
            raw, h = rows[0]
            require(isinstance(raw, bytes) and digest(raw) == h, 'CACHE_CELL_CORRUPTION')
            self.reads += 1
            row = load(raw)
            require(row['instrument_id'] == instrument and row['open_us'] == opened,
                    'CACHE_CELL_KEY_MISMATCH')
            yield qr.Candle(instrument, opened, row['close_us'], row['available_us'],
                            row['open'], row['high'], row['low'], row['close'],
                            row['volume_contracts'], 'qd013:' + self.key + ':' + _text(row['row_id']))

    def close(self):
        self.db.close()
        require(_stat(self.path) == self.before, 'CACHE_CHANGED_DURING_READ')


def decode_episode(row, request):
    require(row['schema'] == 'qd013.controlled-episode.v1' and row['training_authorized'] is False,
            'EPISODE_SCHEMA_OR_TRAINING_FLAG')
    require(row['qr014_compatible'] is True and row['qr014_exclusion_reason'] is None,
            'BASELINE_ONLY_NO_RELABEL')
    data = dict(row['qr014_episode_fields'])
    require(set(data) == {x.name for x in fields(qr.Episode)}, 'EPISODE_FIELD_VERSION_MISMATCH')
    proposal = dict(data['proposal'])
    require(set(proposal) == {x.name for x in fields(qr.EntryProposal)}, 'PROPOSAL_FIELD_VERSION_MISMATCH')
    require(type(proposal['source_refs']) is list, 'WIRE_ARRAY_REQUIRED')
    proposal['source_refs'] = tuple(proposal['source_refs'])
    p = qr.EntryProposal(**proposal)
    b = request['binding']; scope = b['scope']
    for key in ('account_id', 'trajectory_id', 'scenario_id', 'policy_id', 'account_binding_id'):
        require(getattr(p, key) == b[key], 'PROPOSAL_BINDING_MISMATCH:' + key)
    require(scope['initial_us'] <= p.decision_us < scope['economic_end_us'], 'PROPOSAL_OUTSIDE_EXPORT_SCOPE')
    data['proposal'] = p
    for key in ('input_available_us', 'posting_available_us', 'assertion_available_us', 'source_refs', 'reasons'):
        require(type(data[key]) is list, 'WIRE_ARRAY_REQUIRED:' + key)
        data[key] = tuple(data[key])
    e = qr.Episode(**data)
    qr._episode(e)  # Frozen validator, pinned by exact QR014 module hash above.
    require(e.first_fill_us < scope['economic_end_us'], 'ENTRY_OUTSIDE_EXPORT_SCOPE')
    require(e.label_end_us is None or e.label_end_us < scope['economic_end_us'], 'EXIT_OUTSIDE_EXPORT_SCOPE')
    times = e.input_available_us + e.posting_available_us + e.assertion_available_us
    require(all(t <= scope['tail_end_us'] for t in times), 'EVIDENCE_OUTSIDE_EXPORT_SCOPE')
    require(row['censoring'] in (None, 'ECONOMIC_CUTOFF_OPEN', 'TAIL_END_IMMATURE', 'PENDING'), 'UNKNOWN_CENSORING')
    require((row['censoring'] is None) == (e.label_status == 'valid'), 'CENSORING_STATUS_CONFLICT')
    require(row['cost_attribution_scope'] == ('WHOLE_MATURE_EPISODE' if e.label_status == 'valid'
            else 'CLOSED_SLICES_ONLY_NOT_A_LABEL_TARGET'), 'COST_SCOPE_CONFLICT')
    _text(row['accepted_export_ref'])
    require(type(row['registry_refs']) is list and bool(row['registry_refs']), 'REGISTRY_LINEAGE_REQUIRED')
    for ref in row['registry_refs']:
        _text(ref)
    return e


def stream_jsonl(spec, limits):
    path = _path(spec['path']); before = _stat(path)
    _integer(spec['rows']); _hash(spec['sha256'])
    require(before[2] <= limits['max_input_bytes'], 'INPUT_BYTE_BUDGET')
    h = hashlib.sha256(); count = 0
    with path.open('rb') as handle:
        while True:
            offset = handle.tell()
            raw = handle.readline(limits['max_row_bytes'] + 1)
            if not raw:
                break
            require(len(raw) <= limits['max_row_bytes'] and raw.endswith(b'\n'), 'ROW_SIZE_OR_FRAMING')
            count += 1
            require(count <= limits['max_records'], 'INPUT_RECORD_BUDGET')
            h.update(raw)
            yield load(raw), dict(line=count, offset_bytes=offset, bytes=len(raw), sha256=digest(raw))
    require(count == spec['rows'] and h.hexdigest() == _hash(spec['sha256']), 'EXPORT_COUNT_OR_HASH_MISMATCH')
    require(_stat(path) == before, 'EXPORT_CHANGED_DURING_READ')


class Writer:
    def __init__(self, root, limit):
        self.root = root; self.limit = limit
        self.files = {}

    def check(self):
        require(sum(p.stat().st_size for p in self.root.iterdir() if p.is_file()) <= self.limit,
                'OUTPUT_BYTE_BUDGET')

    def jsonl(self, name, rows):
        h = hashlib.sha256(); count = 0
        with (self.root / name).open('xb') as handle:
            for row in rows:
                raw = canonical(row) + b'\n'; handle.write(raw); h.update(raw); count += 1
                handle.flush(); self.check()
        self.files[name] = dict(sha256=h.hexdigest(), rows=count, bytes=(self.root / name).stat().st_size)

    def json(self, name, value):
        raw = canonical(value) + b'\n'
        require(sum(p.stat().st_size for p in self.root.iterdir() if p.is_file()) + len(raw) <= self.limit,
                'OUTPUT_BYTE_BUDGET')
        with (self.root / name).open('xb') as handle:
            handle.write(raw)
        self.check()
        self.files[name] = dict(sha256=digest(raw), bytes=len(raw))


def _intervals(db):
    for inst, start, end, source, role in db.execute(
            'SELECT inst,start,end,source,role FROM intervals ORDER BY start,inst,source'):
        yield dict(instrument_id=inst, start_us=start, end_us=end, source_ref=source,
                   role=role, schema='qr015.information-interval.v1', end_inclusive=True)


def _dependence(db):
    clusters = largest = size = open_ended = count = 0
    end = -1
    for start, finish in db.execute('SELECT start,end FROM intervals WHERE role=? ORDER BY start,inst', ('episode',)):
        count += 1; open_ended += finish is None
        if end is not None and start > end:
            clusters += 1; size = 0; end = finish
        elif end is not None:
            end = None if finish is None else max(end, finish)
        size += 1; largest = max(largest, size)
    return dict(episode_intervals=count, closed_endpoint_overlap_clusters=clusters,
                largest_cluster_episodes=largest, open_ended_intervals=open_ended,
                effective_independent_sample_size=None,
                interpretation='Overlap diagnostics only; clusters are not IID sample counts or a sufficiency test.')


def assemble_local(request_path=None, *, expected_request_sha256=None, output_dir=None,
                   enabled=False, authorization_ref=None, batch_size=128):
    """Default OFF returns without touching files; explicit binding enables preparation only."""
    if not enabled:
        return dict(state='OFF', training_authorized=False, input_reads=0, fit_calls=0)
    _text(authorization_ref)
    require(type(batch_size) is int and 1 <= batch_size <= 4096, 'INVALID_BATCH_SIZE')
    request = _small_json(request_path, expected_request_sha256)
    scope = _request(request)
    source = request['export']
    manifest = _small_json(source['manifest_path'], source['manifest_sha256'])
    require(manifest['schema'] == 'qd013.episode-export.v1' and manifest['state'] == 'COMPLETE'
            and manifest['training_authorized'] is False, 'EXPORT_SCHEMA_OR_STATE')
    require(manifest['identity'] == source['identity'], 'EXPORT_IDENTITY_MISMATCH')
    spec = dict(path=source['episodes_path'], rows=_integer(manifest['rows']), sha256=_hash(manifest['sha256']))
    extra = request['purge'].get('additional_intervals')
    input_bytes = _path(spec['path']).stat().st_size
    if extra is not None:
        input_bytes += _path(extra['path']).stat().st_size
    require(input_bytes <= request['limits']['max_input_bytes'], 'TOTAL_INPUT_BYTE_BUDGET')
    root = Path(output_dir)
    require(root.is_absolute() and not root.exists(), 'NEW_ABSOLUTE_OUTPUT_DIRECTORY_REQUIRED')
    root.mkdir(parents=True, exist_ok=False)
    writer = Writer(root, request['limits']['max_output_bytes'])
    db = None; cache = None
    try:
        writer.json('request.json', request)
        db = sqlite3.connect(root / 'index.sqlite')
        db.executescript('''
            CREATE TABLE records(inst TEXT,proposal TEXT,episode TEXT,decision INTEGER,partition TEXT,raw BLOB,lineage BLOB,
                PRIMARY KEY(inst,proposal),UNIQUE(inst,episode));
            CREATE TABLE intervals(inst TEXT,start INTEGER,end INTEGER,source TEXT,role TEXT);
            CREATE INDEX interval_lookup ON intervals(role,start,end);
            CREATE TABLE selected_targets(inst TEXT,target TEXT);
        ''')
        count = 0
        for row, lineage in stream_jsonl(spec, request['limits']):
            e = decode_episode(row, request); p = e.proposal; part = qr._partition(p.decision_us)
            try:
                db.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?)',
                           (p.instrument_id, p.proposal_id, e.episode_id, p.decision_us, part, canonical(row), canonical(lineage)))
            except sqlite3.IntegrityError as exc:
                raise DatasetError('DUPLICATE_PROPOSAL_OR_EPISODE_REVISION') from exc
            db.execute('INSERT INTO intervals VALUES (?,?,?,?,?)',
                       (p.instrument_id, p.decision_us, e.label_known_at_us, row['accepted_export_ref'], 'episode'))
            if part in ('validation_2025', 'exposed_audit_2026'):
                db.execute('INSERT INTO intervals VALUES (?,?,?,?,?)',
                           (p.instrument_id, p.decision_us, e.label_known_at_us, row['accepted_export_ref'], 'heldout'))
            count += 1
            if count % batch_size == 0:
                db.commit(); writer.check()
        extra_count = 0
        if extra is not None:
            for item, _ in stream_jsonl(extra, request['limits']):
                extra_count += 1
                require(count + extra_count <= request['limits']['max_records'], 'TOTAL_INPUT_RECORD_BUDGET')
                interval = qr.InformationInterval(**item); qr._interval(interval)
                db.execute('INSERT INTO intervals VALUES (?,?,?,?,?)',
                           (interval.instrument_id, interval.start_us, interval.end_us, interval.source_ref, 'heldout'))
        db.commit(); writer.check()
        cache = ClosedHourReader(request['market_cache'], scope)
        counts = Counter(rows=0, included=0, train_eligible=0, excluded=0, censored_markers=0)
        reasons = Counter(); strata = Counter(); signs = Counter(); bounds = {}
        def samples():
            cursor = db.execute('SELECT raw,lineage FROM records ORDER BY decision,inst,proposal')
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    return
                for raw, lineage in batch:
                    row = load(raw); e = decode_episode(row, request); p = e.proposal
                    feature = qr.features_for_proposal(cache.candles(p.instrument_id, p.decision_us), p)
                    overlap = ()
                    if e.label_known_at_us is not None:
                        witness = db.execute('''SELECT inst,start,end,source FROM intervals
                            WHERE role='heldout' AND start<=? AND (end IS NULL OR end>=?)
                            ORDER BY start,inst,source LIMIT 1''', (e.label_known_at_us, p.decision_us)).fetchone()
                        if witness:
                            overlap = (qr.InformationInterval(*witness),)
                    # Query the complete disk inventory before every row. QR014
                    # needs only an overlap witness, never all disjoint intervals.
                    purge = qr.PurgeContext(request['purge']['complete'], qr.INSTRUMENTS,
                                           request['purge']['source_ref'], overlap)
                    result = qr.assemble_samples([feature], [e], accepted_export_ref=row['accepted_export_ref'],
                        input_received_at_us=request['input_received_at_us'], assembled_at_us=request['assembled_at_us'],
                        purge_context=purge)[0]
                    result['proposal'] = asdict(result['proposal'])
                    result.update(schema=SCHEMA, qr014_schema=qr.LOCAL_SCHEMA,
                        source_line=load(lineage), source_episode_fields=row['qr014_episode_fields'],
                        censoring=row['censoring'], registry_refs=row['registry_refs'],
                        cost_breakdown_exact=row['cost_breakdown_exact'], cost_attribution_scope=row['cost_attribution_scope'],
                        export_manifest_sha256=source['manifest_sha256'], market_cache_key=cache.key,
                        feature_units=qr.FEATURE_UNITS, feature_set=qr.FEATURE_SET,
                        overlap_witness=[asdict(x) for x in overlap],
                        source_qualification='SYNTHETIC_ONLY' if request['input_kind']=='SYNTHETIC' else 'BOUND_EXPORT_NOT_TRAINING_ACCEPTANCE')
                    counts['rows'] += 1; counts['included'] += result['included']; counts['train_eligible'] += result['train_eligible']
                    counts['excluded'] += not result['included']; counts['censored_markers'] += row['censoring'] is not None
                    for reason in result['reasons']:
                        reasons[reason] += 1
                    year = datetime.fromtimestamp(p.decision_us / 1_000_000, timezone.utc).year
                    strata[(p.instrument_id, str(year), result['partition'], e.label_status,
                            row['censoring'] or 'NONE', str(result['included']))] += 1
                    bounds[p.instrument_id] = [min(bounds.get(p.instrument_id, [p.decision_us])[0], p.decision_us), p.decision_us]
                    if result['train_eligible']:
                        target = result['model_target_fraction_12']
                        sign = 'zero' if target == '0.000000000000' else 'negative' if target.startswith('-') else 'positive'
                        signs[(p.instrument_id, sign)] += 1
                        db.execute('INSERT INTO selected_targets VALUES (?,?)', (p.instrument_id, target))
                    yield result
        writer.jsonl('samples.jsonl', samples())
        cache_reads = cache.reads; cache.close(); cache = None
        writer.jsonl('information-intervals.jsonl', _intervals(db))
        support = {inst: dict(train_rows=db.execute('SELECT COUNT(*) FROM selected_targets WHERE inst=?', (inst,)).fetchone()[0],
                             distinct_rounded_targets=db.execute('SELECT COUNT(DISTINCT target) FROM selected_targets WHERE inst=?', (inst,)).fetchone()[0])
                   for inst in qr.INSTRUMENTS}
        readiness_reasons = ['SAMPLE_DEPENDENCE_AND_PRECISION_NOT_ACCEPTED', 'TRAINING_REQUIRES_FRESH_HUMAN_CONFIRMATION']
        if request['input_kind'] == 'SYNTHETIC':
            readiness_reasons.append('SYNTHETIC_NOT_RESEARCH_EVIDENCE')
        if not counts['train_eligible']:
            readiness_reasons.append('NO_TRAINING_ROWS')
        if any(not x['train_rows'] for x in support.values()):
            readiness_reasons.append('MISSING_TRAINING_ASSET_SUPPORT')
        if not request['purge']['complete']:
            readiness_reasons.append('INCOMPLETE_HELDOUT_INVENTORY')
        summary = dict(schema='qr015.dataset-summary.v1', counts=dict(counts),
            unique_proposals=count, unique_episodes=count, proposal_inventory='EPISODE_BACKED_ONLY_NOT_ALL_DECISIONS',
            standalone_unfilled_proposals=None, standalone_null_reason='QD013 export contains realized episodes and their nested entry proposals only.',
            exclusion_reasons=dict(sorted(reasons.items())),
            strata=[dict(zip(('instrument_id','year','partition','label_status','censoring','included','rows'), (*key,n))) for key,n in sorted(strata.items())],
            decision_bounds_us=bounds, train_asset_support=support,
            train_target_sign_counts=[dict(instrument_id=k[0],sign=k[1],rows=v) for k,v in sorted(signs.items())],
            dependence=_dependence(db), declared_scope=scope, frozen_splits=dict(train='2024',validation='2025',exposed_audit='2026-01-01/2026-10-01'),
            source_kind=request['input_kind'], training_ready=False, training_authorized=False,
            readiness_reasons=readiness_reasons, fit_calls=0, market_hour_cell_reads=cache_reads)
        db.commit(); db.close(); db = None
        writer.json('summary.json', summary)
        writer.check()
        result = dict(schema=SCHEMA, state='COMPLETE', import_request_sha256=expected_request_sha256,
            authorization_ref=authorization_ref, qd_commit=QD_COMMIT, qd_manifest_sha256=QD_MANIFEST_SHA256,
            qr014_commit=QR014_COMMIT, qr014_module_sha256=QR014_MODULE_SHA256,
            consumer_module_sha256=digest(Path(__file__).read_bytes()), source_metadata=request['source_metadata'],
            export_manifest_sha256=source['manifest_sha256'], export_identity=manifest['identity'],
            market_cache_key=request['market_cache']['key'], market_content_sha256=request['market_cache']['content_sha256'],
            source_binding_ref=request['source_binding_ref'], binding=request['binding'],
            source_qualification=summary['source_kind'], files=dict(writer.files), training_authorized=False,
            training_ready=False, fit_calls=0,
            integrity_scope='Exact request/export hash and counts; immutable cache metadata and selected hour-cell hashes. No raw-source/full-cache revalidation.',
            index_role='Local derived join/interval index; not a replay ledger or portable authoritative output.')
        writer.json('manifest.json', result)
        return result
    except BaseException as exc:
        # Preserve failed output and index. Never retry, overwrite or publish COMPLETE.
        if db is not None:
            db.close()
        if cache is not None:
            cache.db.close()
        if not (root / 'manifest.json').exists():
            raw = canonical(dict(state='FAILED', error=type(exc).__name__ + ':' + str(exc), training_authorized=False)) + b'\n'
            with (root / 'failure.json').open('xb') as handle:
                handle.write(raw)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable-local-assembly', action='store_true')
    parser.add_argument('--request'); parser.add_argument('--request-sha256')
    parser.add_argument('--output'); parser.add_argument('--authorization-ref')
    parser.add_argument('--batch-size', type=int, default=128)
    args = parser.parse_args(argv)
    result = assemble_local(args.request, expected_request_sha256=args.request_sha256,
        output_dir=args.output, enabled=args.enable_local_assembly,
        authorization_ref=args.authorization_ref, batch_size=args.batch_size)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
