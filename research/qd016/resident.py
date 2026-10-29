"""Explicit operational continuation of a known uncommitted resident-index stop.

Original ledger/ports remain pinned and byte-identical. Only the independent
working-node quota is removed: charges, cache eviction, exact arithmetic,
journals, hashes, guards and financial transitions are inherited unchanged.
"""
from copy import deepcopy
from pathlib import Path
import weakref
from research.qd009 import streaming_ledger as sl
from research.qd012.actual_snapshot_entry import durable_new

SCHEMA='qd016.resident-continuation.v1'


class ProcessBudgetIndex(sl.NodeIndex):
    def _working(self,c,data):
        # Same copy/accounting/finalizer as the pinned implementation, without
        # its per-working-node hard rejection. Whole-process RSS is the bound.
        owned=dict(data,k=list(data['k']),v=deepcopy(data['v']))
        charge=[512+sl._resident_size(owned['k'])+sl._resident_size(owned['p'])+sl._resident_size(owned['v'])]
        if self.work_bytes+charge[0]>self.cap:
            try:self.process_bound()
            except Exception as e:raise sl.LedgerError('RESOURCE_EXHAUSTED','/process_budget',reason=str(e)) from e
        self.work_bytes+=charge[0];self.work_peak=max(self.work_peak,self.work_bytes);self._evict()
        node=sl._WorkingNode(c,owned,charge);weakref.finalize(node,self._release_work,charge);return node

    def set(self,c,h,k,v):
        # Pinned treap operation, with only the second working-size rejection
        # replaced by the same process bound as allocation above.
        n=self.node(c,h)
        if n is None:return self.put(c,k,v)
        a,b=sl.ordered_key(k),sl.ordered_key(n['k'])
        if a==b and n['v']==v:return h
        w=h if isinstance(h,sl._WorkingNode) else self._working(c,n);n=w.data
        if a==b:
            charge=sl._resident_size(v)-sl._resident_size(n['v'])
            if self.work_bytes+charge>self.cap:
                try:self.process_bound()
                except Exception as e:raise sl.LedgerError('RESOURCE_EXHAUSTED','/process_budget',reason=str(e)) from e
            self.work_bytes+=charge;w.charge[0]+=charge;n['v']=deepcopy(v);self._evict();return w
        side='l' if a<b else 'r';child=self.set(c,n[side],k,v);n[side]=child;cn=self.node(c,child)
        n['n']=1+self.count(c,n['l'])+self.count(c,n['r'])
        if (cn['p'],sl.ordered_key(cn['k']))<(n['p'],b):
            if not isinstance(child,sl._WorkingNode):child=self._working(c,cn);cn=child.data
            other='r' if side=='l' else 'l';n[side]=cn[other];n['n']=1+self.count(c,n['l'])+self.count(c,n['r'])
            cn[other]=w;cn['n']=1+self.count(c,cn['l'])+self.count(c,cn['r']);return child
        return w


class ContinuationLedger(sl.Ledger):
    def __init__(self,store_root,*,operation,record_name,process_bound):
        self.operation=operation;self.record_name=record_name
        original_head=None if (Path(store_root)/record_name).exists() else operation['expected_head']['audit_prefix']
        super().__init__(store_root,expected_head=original_head)
        # Keep the existing LRU/SQL cache sizes and all counters. The type adds
        # no state/layout; its sole method difference is the authorized guard.
        self.index.__class__=ProcessBudgetIndex
        self.index.process_bound=process_bound

    def _load_control(self):
        control=super()._load_control();path=self.root/self.record_name
        if not path.exists() or control['status']=='INTEGRITY_STOPPED':return control
        record=sl.load_json(path.read_bytes());expected={k:v for k,v in record.items() if k!='record_sha256'}
        sl.need(record.get('record_sha256')==sl.digest(expected),'STORE_INTEGRITY_FAILURE')
        sl.need(record['operation']==self.operation and record['schema']==SCHEMA,'CHECKPOINT_MISMATCH')
        old=self.operation['expected_head']
        sl.need(self.head['committed_seq']>=old['committed_seq'],'CHECKPOINT_MISMATCH')
        if old['committed_seq']:
            manifest=sl.load_json((self.root/f"manifest-{old['committed_seq']:08}.json").read_bytes())
            sl.need(sl.digest(manifest)==old['audit_prefix'],'STORE_INTEGRITY_FAILURE')
        n=record['resolution_seq']
        if control['seq']<n:return control  # grant alone never clears a guard
        row=sl.load_json((self.root/f'control-{n:08}.json').read_bytes())
        sl.need(row['kind']=='resolution' and row['outcome']=='not_committed' and row['request_sha256']==self.operation['failed_request_sha256'],'CHECKPOINT_MISMATCH')
        sl.need(row['previous_control_sha256']==self.operation['stop_control']['control_sha256'],'CHECKPOINT_MISMATCH')
        for seq in range(n+1,control['seq']+1):
            later=sl.load_json((self.root/f'control-{seq:08}.json').read_bytes())
            if later['kind'] in ('resource_stop','integrity_stop'):return control
        control['status']='ACTIVE'
        return control

    def activate(self):
        """Resolve this exact failed request as not committed; never restage it.

        Proof is the resource-stop before-HEAD disposition, bound HEAD/guard,
        absent next journal/manifest and absent committed request. No old account
        replay, source change, or ambiguous-commit resolution is performed.
        """
        op=self.operation;self._assert_thread()
        sl.need(not (self.root/self.record_name).exists(),'REQUEST_CONFLICT')
        sl.need(self.head==op['expected_head'] and self.control['status']=='RESOURCE_STOPPED','CHECKPOINT_MISMATCH')
        pointer=sl.load_json((self.root/'CONTROL').read_bytes())
        sl.need(pointer==op['stop_control'],'CHECKPOINT_MISMATCH')
        stop=sl.load_json((self.root/f"control-{pointer['control_seq']:08}.json").read_bytes())
        err=stop.get('error',{})
        sl.need(stop['kind']=='resource_stop' and err.get('code')=='RESOURCE_EXHAUSTED' and err.get('path')=='/resident_index' and err.get('disposition')=='stop_resource','STORE_INTEGRITY_FAILURE')
        sl.need(stop['at_committed_seq']==self.head['committed_seq'] and stop['audit_prefix']==self.head['audit_prefix'] and not self.control['validated'],'CHECKPOINT_MISMATCH')
        guard=self.control['guard'];sl.need(guard is not None,'COMMIT_OUTCOME_UNKNOWN')
        path=sl._safe_path(self.root,guard['guard_input']['relative_path']);raw=path.read_bytes()
        sl.need(len(raw)==guard['guard_input']['bytes'] and sl._file_sha(path)==guard['guard_input']['sha256'],'STORE_INTEGRITY_FAILURE')
        saved=sl.load_json(raw)
        sl.need(sl.digest(saved)==op['failed_request_sha256']==stop['request_sha256'],'REQUEST_CONFLICT')
        sl.shape(saved,'request_id expected_audit_prefix through_us imported generated')
        sl.need(saved['expected_audit_prefix']==self.head['audit_prefix'] and not saved['imported'] and not saved['generated'],'CHECKPOINT_MISMATCH')
        sl.need(saved['through_us']>self.head['cutoff']['at_us'] and self.config['_plan_index'].tick(saved['through_us']) is not None,'SCHEDULE_MISMATCH')
        next_seq=self.head['committed_seq']+1
        sl.need(not any(self.root.glob(f'journal-{next_seq:08}.*')) and not (self.root/f'manifest-{next_seq:08}.json').exists(),'COMMIT_OUTCOME_UNKNOWN')
        sl.need(self.index.db.execute('SELECT 1 FROM requests WHERE id=?',(saved['request_id'],)).fetchone() is None,'COMMIT_OUTCOME_UNKNOWN')
        # Verify the actual committed payload identity/root link without replay.
        payload=self._payload(self.head['committed_seq'])
        sl.need(payload['roots']==self.state.roots and payload['receipt']['after']['economic_state_sha256']==self.head['economic_state_sha256'],'STORE_INTEGRITY_FAILURE')
        before_spent=deepcopy(self.spent)
        record=dict(schema=SCHEMA,operation=op,resolution_seq=pointer['control_seq']+1,
            prior_spent=before_spent,policy=dict(working_node_hard_quota='REMOVED_PROCESS_RSS_BOUND',
                immutable_cache_cap_bytes=self.index.cap,charges_retained=True,process_rss_limit_bytes=op['process_rss_limit_bytes']))
        record['record_sha256']=sl.digest(record)
        self.budget.issue(self.root/self.record_name,len(sl.canonical_bytes(record))+1,len(sl.canonical_bytes(record))+1)
        durable_new(self.root/self.record_name,record,65536)
        self._control('resolution',saved,'not_committed')
        self.control=self._load_control()
        sl.need(self.control['status']=='ACTIVE' and self.control['guard'] is None,'COMMIT_OUTCOME_UNKNOWN')
        self.spent['attempts_started']+=1;self._save_spent()
        sl.need(self.head==op['expected_head'] and self.spent['active_wall_us']>=before_spent['active_wall_us'],'CHECKPOINT_MISMATCH')
        return record
