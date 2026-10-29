"""Recover a stopped, copied account at its authoritative HEAD, not genesis."""
from copy import deepcopy
import os
from pathlib import Path
from research.qd019.migration import STORE,read,sha,require,relative,verify_chain

ALLOWED_OLD_QUOTAS={'/wall','/store','/prewrite_quota','/resource_book','/resident_index','/process_budget'}


def journal_payload(store,seq):
    from research.qd009 import streaming_ledger as sl
    from research.qd015 import journal
    m=read(Path(store)/f'manifest-{seq:08}.json');ref=m['files'][0];p=relative(store,ref['relative_path'])
    require(p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256'],'JOURNAL_HASH_MISMATCH')
    cfg=read(Path(store)/'GENESIS')['config']
    raw=p.read_bytes()
    if 'journal_storage' in cfg:raw=journal.decode(raw,cfg['journal_storage'])
    payload=sl.load_json(raw)
    require(sl.digest(payload['request'])==m['request_sha256'],'JOURNAL_REQUEST_MISMATCH')
    return m,payload


def adopt_control_tail(store):
    from research.qd009 import streaming_ledger as sl
    original=read(store/'CONTROL');tip=dict(original);adopted=[]
    for n in range(original['control_seq']+1,original['control_seq']+257):
        path=store/f'control-{n:08}.json'
        if not path.exists():break
        row=read(path);body={k:v for k,v in row.items() if k!='control_sha256'}
        require(row['control_seq']==n and row['previous_control_sha256']==tip['control_sha256'] and
                sl.digest(body)==row['control_sha256'],'ORPHAN_CONTROL_CHAIN_MISMATCH')
        tip=dict(control_seq=n,control_sha256=row['control_sha256']);adopted.append(sha(path))
    if adopted:sl._atomic(store/'CONTROL',tip)
    return dict(before=original,after=tip,adopted=adopted)


def adopt_audit_tail(store,head):
    from research.qd009 import streaming_ledger as sl
    original=read(store/'AUDIT');tip=dict(original);adopted=[]
    for n in range(original['seq']+1,original['seq']+257):
        path=store/'audit-rows'/f'{n:08}.json'
        if not path.exists():break
        wrapped=read(path);row=wrapped['row'];body={k:v for k,v in wrapped.items() if k!='sha256'}
        require(wrapped['previous']==tip['hash'] and sl.digest(body)==wrapped['sha256'] and
                row['audit_seq']==n,'ORPHAN_AUDIT_CHAIN_MISMATCH')
        if row['kind']=='commit':
            manifest=read(store/f"manifest-{row['manifest']['seq']:08}.json")
            require(row['manifest']==manifest and row['prefix']==sl.digest(manifest) and
                    manifest['seq']<=head['committed_seq'],'UNPUBLISHED_AUDIT_COMMIT')
        elif row['kind']=='failure':
            require(row['at_committed_seq']<=head['committed_seq'] and
                    row['failure_sha256']==sl.digest({k:v for k,v in row.items() if k!='failure_sha256'}),
                    'ORPHAN_AUDIT_FAILURE_MISMATCH')
        else:raise ValueError('UNKNOWN_AUDIT_KIND')
        tip=dict(seq=n,hash=wrapped['sha256']);adopted.append(sha(path))
    if adopted:sl._atomic(store/'AUDIT',tip)
    return dict(before=original,after=tip,adopted=adopted)


def reconcile_index(data,head,guard):
    """Rewind only unpublished *derived index* rows; keep immutable history."""
    from research.qd009 import streaming_ledger as sl
    store=Path(data)/STORE;index=sl.NodeIndex(store/'cache.sqlite3',8*1024**2)
    try:
        m,payload=journal_payload(store,head['committed_seq'])
        require(sl.digest(m)==head['audit_prefix'],'HEAD_MANIFEST_MISMATCH')
        for component,root in payload['roots'].items():index.node(component,root)
        old=index.db.execute('SELECT v FROM local_meta WHERE k="head"').fetchone()
        if old!=(head['audit_prefix'],):
            require(guard is not None,'INDEX_HEAD_MISMATCH_WITHOUT_GUARD')
            future=store/f"manifest-{head['committed_seq']+1:08}.json"
            require(future.exists(),'UNRECOGNIZED_INDEX_HEAD')
            next_manifest,next_payload=journal_payload(store,head['committed_seq']+1)
            require(old==(sl.digest(next_manifest),) and next_manifest['before']==head and
                    next_manifest['request_sha256']==guard['request_sha256'],'UNRECOGNIZED_INDEX_HEAD')
        removed=index.db.execute('SELECT id,sha,seq FROM requests WHERE seq>?',(head['committed_seq'],)).fetchall()
        for rid,h,n in removed:
            require(guard is not None and rid==guard['request_id'] and h==guard['request_sha256'] and
                    n==head['committed_seq']+1,'UNRECOGNIZED_UNPUBLISHED_REQUEST')
        index.db.execute('DELETE FROM requests WHERE seq>?',(head['committed_seq'],))
        index.db.execute('DELETE FROM commits WHERE seq>?',(head['committed_seq'],))
        index.db.execute("DELETE FROM views WHERE json_extract(b,'$.knowledge_cutoff.at_us')>? OR (json_extract(b,'$.knowledge_cutoff.at_us')=? AND json_extract(b,'$.knowledge_cutoff.slot')>?)",
                         (head['cutoff']['at_us'],head['cutoff']['at_us'],head['cutoff']['slot']))
        index.db.execute('INSERT OR REPLACE INTO local_meta VALUES ("head",?)',(head['audit_prefix'],))
        index.db.commit()
        return dict(previous_cached_head=list(old) if old is not None else None,
                    removed_unpublished_requests=[list(row) for row in removed],published_roots_verified=True)
    finally:index.close()


def prepare(data,manifest):
    from research.qd009 import streaming_ledger as sl
    from research.qd016.resident import ContinuationLedger
    data=Path(data).resolve();store=data/STORE;head=read(store/'HEAD')
    require(head==manifest['source_head'],'HANDOFF_HEAD_CHANGED')
    verify_chain(store,head)
    tail=adopt_control_tail(store)
    audit_tail=adopt_audit_tail(store,head)
    # Read the entire control chain through the original validator, before SQL
    # repair or granting any formerly artificial resource-stop continuation.
    reader=object.__new__(sl.Ledger);reader.root=store;reader.request=read(store/'GENESIS')
    control=sl.Ledger._load_control(reader)
    require(control['status']!='INTEGRITY_STOPPED','INTEGRITY_STOP_REQUIRES_REVIEW')
    waived=[]
    for n in range(1,control['seq']+1):
        row=read(store/f'control-{n:08}.json')
        require(row['at_committed_seq']<=head['committed_seq'],'CONTROL_AHEAD_OF_PUBLISHED_HEAD')
        if row['kind']=='resource_stop':
            require(row['error']['code']=='RESOURCE_EXHAUSTED' and row['error'].get('path') in ALLOWED_OLD_QUOTAS,
                    'STRUCTURAL_RESOURCE_STOP_REQUIRES_REVIEW')
            waived.append(row['control_sha256'])
    guard=control['guard'];request=None;outcome=None
    if guard is not None:
        p=relative(store,guard['guard_input']['relative_path'])
        require(p.stat().st_size==guard['guard_input']['bytes'] and sha(p)==guard['guard_input']['sha256'],'GUARD_HASH_MISMATCH')
        request=read(p);require(sl.digest(request)==guard['request_sha256'],'GUARD_REQUEST_MISMATCH')
        sl.shape(request,'request_id expected_audit_prefix through_us imported generated')
        m,payload=journal_payload(store,head['committed_seq'])
        if m['request_id']==request['request_id'] and m['request_sha256']==guard['request_sha256']:
            require(payload['request']==request,'COMMIT_REQUEST_MISMATCH');outcome='committed'
        else:
            require(request['expected_audit_prefix']==head['audit_prefix'] and request['through_us']>head['cutoff']['at_us'] and
                    not request['imported'] and not request['generated'],'UNRECOGNIZED_PENDING_REQUEST')
            outcome='not_committed'
    rewind=reconcile_index(data,head,guard)
    # Never overwrite a leftover unpublished journal with a different payload.
    # Preserve it in a documented quarantine in the cloned account instead.
    quarantined=[];n=head['committed_seq']+1
    pending=list(store.glob(f'journal-{n:08}.*'))+list(store.glob(f'manifest-{n:08}.*'))
    require(not pending or outcome=='not_committed','UNEXPECTED_UNPUBLISHED_ARTIFACT')
    if pending:
        q=store/('qd021-unpublished-'+manifest['operation_id']);q.mkdir(exist_ok=False)
        for p in pending:
            record=dict(name=p.name,sha256=sha(p),bytes=p.stat().st_size)
            os.rename(p,q/p.name)
            budget=sl._budget_for(p)
            if budget:budget.rename(p,q/p.name)
            quarantined.append(record)
    return dict(head=head,tail=tail,audit_tail=audit_tail,index_recovery=rewind,guard_request=request,guard_outcome=outcome,
                waived_resource_controls=waived,quarantined=quarantined)


def activate(ledger,manifest,recovery):
    from research.qd009 import streaming_ledger as sl
    from research.qd012.actual_snapshot_entry import durable_new
    path=ledger.root/('PERFORMANCE-CONTINUATION-'+manifest['operation_id']+'.json')
    require(not path.exists(),'PERFORMANCE_INVOCATION_ALREADY_CONSUMED')
    require(ledger.head==manifest['source_head'],'SOURCE_HEAD_CHANGED_DURING_ADMISSION')
    request=recovery['guard_request']
    if request is not None and recovery['guard_outcome']=='not_committed':
        require(next(t for t in ledger.config['_plan_index'].times if t>ledger.head['cutoff']['at_us'])==request['through_us'],
                'PENDING_REQUEST_IS_NOT_NEXT_TICK')
    record=dict(schema='qd021.continuation.v1',authorization_ref='USER_QD021_OPTIMIZE_UNRESTRICTED',
                recovery=recovery,source_operation=manifest['source_snapshot'],original_spent=deepcopy(ledger.spent),
                policy=dict(global_wall_cpu_rss_disk_quotas=None,adapter_time_quota=None,
                            finite_format_and_integrity_bounds_retained=True),cache=ledger.fast_policy,
                training_authorized=False)
    record['sha256']=sl.digest(record)
    size=len(sl.canonical_bytes(record))+1;ledger.budget.issue(path,size,size);durable_new(path,record,16*1024**2)
    if not ledger.index.db.execute("SELECT 1 FROM audit_rows WHERE kind='commit' AND commit_seq=?",
                                   (ledger.head['committed_seq'],)).fetchone():
        require(request is not None and recovery['guard_outcome']=='committed','MISSING_PUBLISHED_COMMIT_AUDIT')
        ledger._append_audit('commit',manifest=read(ledger.root/f"manifest-{ledger.head['committed_seq']:08}.json"))
    if request is not None:
        ledger.guard_input=ledger.control['guard']['guard_input']
        ledger._control('resolution',request,recovery['guard_outcome'])
    ledger.control['status']='ACTIVE'
    ledger.spent['attempts_started']+=1;ledger._save_spent()
    require(ledger.current_head()['status']=='ACTIVE','CONTINUATION_NOT_ACTIVE')
    return record
