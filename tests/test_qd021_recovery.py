"""Synthetic interrupted-publication recovery and real VFS accounting checks."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib
from research.qd009 import streaming_ledger as sl
from research.qd011 import ports
from research.qd013.market import MarketCache
from research.qd013.runner import Replay
from research.qd015.runner import create
from research.qd019.migration import STORE,read
from research.qd021 import accounting,cold,fast


class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name).resolve();self.store=self.data/STORE
        self.original=(sl.deepcopy,sl.strict_json,ports.deepcopy,sl._GLOBAL_BUDGET,dict(sl._BUDGETS))
        self.addCleanup(self.restore)
        fixture=Path(__file__).resolve().parents[1]/'research/qd015/synthetic-input.json'
        f=json.loads(fixture.read_bytes());identity=deepcopy(f['source_cache_identity'])
        identity['code']={'qd015_fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest()}
        self.cache=MarketCache.build(self.data/'market.sqlite3',identity,iter(f['records']));self.addCleanup(self.cache.close)
        budget=sl.configure_resource_budget(self.data,128*1024**2)
        scope=identity['scope'];self.replay=create(self.store.parent,self.cache,initial_us=scope['initial_us'],
            economic_end_us=scope['economic_end_us'],tail_end_us=scope['tail_end_us'],write_budget=budget.issue)
        self.times=self.replay.ledger.config['_plan_index'].times
        self.replay.advance_chunk(self.times[2]);self.head=deepcopy(self.replay.ledger.head)
        self.addCleanup(lambda:self.replay.ledger.close())

    def restore(self):
        for budget in list(sl._BUDGETS.values())+[sl._GLOBAL_BUDGET]:
            if budget is not None and hasattr(budget,'close'):budget.close()
        sl.deepcopy,sl.strict_json,ports.deepcopy,sl._GLOBAL_BUDGET,books=self.original
        sl._BUDGETS.clear();sl._BUDGETS.update(books)

    def resume(self,operation):
        self.replay.ledger.close()
        manifest=dict(source_head=read(self.store/'HEAD'),operation_id=operation,source_snapshot={})
        self.budgets=accounting.install(self.data,[str(self.data)])
        self.addCleanup(lambda:[b.close() for b in reversed(self.budgets)])
        recovery=cold.prepare(self.data,manifest)
        ledger=sl.Ledger(self.store);fast.install(ledger)
        cold.activate(ledger,manifest,recovery)
        self.replay=Replay(ledger)
        return recovery

    def finish(self):
        for at in self.times:
            if at>self.replay.ledger.head['cutoff']['at_us']:self.replay.advance_chunk(at)
        self.assertEqual(self.replay.view(self.times[-1])['economic_state_sha256'],
                         'cdc0fefc3582f3e3381c1781017dac965155a5cdd9933c081489e1de0fd0d301')

    def test_sql_commit_before_head_is_rewound_without_replaying_history(self):
        original=sl._atomic
        def fail_head(path,*a,**k):
            if Path(path)==self.store/'HEAD':raise OSError('INJECTED_BEFORE_HEAD_PUBLICATION')
            return original(path,*a,**k)
        with patch.object(sl,'_atomic',fail_head):
            with self.assertRaises(sl.LedgerError):self.replay.advance_chunk(self.times[3])
        self.assertEqual(read(self.store/'HEAD'),self.head)
        recovery=self.resume('before-head')
        self.assertEqual(recovery['guard_outcome'],'not_committed')
        self.assertTrue(recovery['quarantined']);self.assertTrue(recovery['index_recovery']['removed_unpublished_requests'])
        self.assertEqual(self.replay.ledger.head,self.head);self.finish()

    def test_head_published_before_audit_is_not_charged_a_second_time(self):
        ledger=self.replay.ledger
        with patch.object(ledger,'_append_audit',side_effect=OSError('INJECTED_AFTER_HEAD')):
            with self.assertRaises(sl.LedgerError):self.replay.advance_chunk(self.times[3])
        published=read(self.store/'HEAD');self.assertEqual(published['committed_seq'],self.head['committed_seq']+1)
        recovery=self.resume('after-head')
        self.assertEqual(recovery['guard_outcome'],'committed');self.assertEqual(self.replay.ledger.head,published)
        self.assertEqual(self.replay.ledger.index.db.execute("SELECT count(*) FROM audit_rows WHERE kind='commit' AND commit_seq=?",
                         (published['committed_seq'],)).fetchone(),(1,))
        self.finish()

    def test_real_vfs_writes_ignore_old_quota_and_keep_durable_debits(self):
        ledger=self.replay.ledger;ledger.close()
        old=read(self.store/'SPENT')['total_written_bytes']
        budgets=accounting.install(self.data,[str(self.data)]);self.addCleanup(lambda:[b.close() for b in reversed(budgets)])
        ledger=sl.Ledger(self.store);self.replay=Replay(ledger)
        before=budgets[0].written
        self.assertIsNone(budgets[0].limit);self.assertIsNone(budgets[1].limit)
        # An issue exceeding the previous 128 MiB quota must be accounted, not
        # rejected. No large physical allocation is made by this assertion.
        budgets[0].issue(self.data/'hypothetical-output',2**35,2**35)
        self.replay.advance_chunk(self.times[3])
        self.assertGreater(budgets[0].written,before+2**35)
        self.assertGreaterEqual(ledger.spent['total_written_bytes'],old)
        ledger.close()
        for b in reversed(budgets):b.close()
        again=accounting.install(self.data,[str(self.data)]);self.addCleanup(lambda:[b.close() for b in reversed(again)])
        self.assertGreaterEqual(again[0].written,budgets[0].written)

    def test_integrity_stop_is_never_waived(self):
        ledger=self.replay.ledger
        with patch.object(ledger,'_stage',side_effect=sl.LedgerError('INPUT_BINDING_MISMATCH')):
            with self.assertRaises(sl.LedgerError):self.replay.advance_chunk(self.times[3])
        ledger.close();manifest=dict(source_head=read(self.store/'HEAD'),operation_id='bad',source_snapshot={})
        with self.assertRaisesRegex(ValueError,'INTEGRITY_STOP'):cold.prepare(self.data,manifest)
        self.assertEqual(read(self.store/'HEAD'),self.head)

    def test_published_audit_tail_is_adopted_without_overwrite(self):
        original=sl._atomic
        def fail_pointer(path,*a,**k):
            if Path(path)==self.store/'AUDIT':raise OSError('INJECTED_AFTER_AUDIT_OBJECT')
            return original(path,*a,**k)
        with patch.object(sl,'_atomic',fail_pointer):
            with self.assertRaises(sl.LedgerError):self.replay.advance_chunk(self.times[3])
        recovery=self.resume('audit-tail')
        self.assertEqual(len(recovery['audit_tail']['adopted']),1)
        self.assertEqual(recovery['guard_outcome'],'committed');self.finish()


class IndexChecks(unittest.TestCase):
    def test_prune_follows_cross_component_historical_references(self):
        with tempfile.TemporaryDirectory() as d:
            saved=(sl.deepcopy,sl.strict_json,ports.deepcopy)
            indexes=[sl.NodeIndex(Path(d)/(name+'.sqlite3'),16*1024**2) for name in ('old','new')]
            indexes[1].db.execute('CREATE TABLE audit_rows(kind TEXT,commit_seq INTEGER)')
            try:
                fast.install(SimpleNamespace(index=indexes[1]))
                for idx in indexes:
                    idx.birth=1
                    def make(c,k,v):return idx.freeze(c,idx.set(c,idx.empty(c),[k],v))
                    lots=make('lots',1,{'v':1});make('lots',2,{'orphan':True})
                    links=make('links',1,{'v':2});lr=make('_link_roots',1,links)
                    refs=make('_audit_refs',1,{'v':3});ar=make('_audit_ref_roots',1,refs)
                    timeline=make('_timeline',1,dict(lots=lots,_link_roots=lr,_audit_ref_roots=ar))
                    idx.prune({'_timeline':timeline})
                    for component,root in (('lots',lots),('links',links),('_audit_refs',refs)):
                        self.assertIsNotNone(idx.node(component,root))
                self.assertEqual(indexes[0].db.execute('SELECT h FROM nodes ORDER BY h').fetchall(),
                                 indexes[1].db.execute('SELECT h FROM nodes ORDER BY h').fetchall())
            finally:
                for idx in indexes:idx.close()
                sl.deepcopy,sl.strict_json,ports.deepcopy=saved

    def test_random_updates_historical_roots_pruning_and_blob_corruption(self):
        import random
        with tempfile.TemporaryDirectory() as d:
            saved=(sl.deepcopy,sl.strict_json,ports.deepcopy)
            a=sl.NodeIndex(Path(d)/'original.sqlite3',16*1024**2)
            b=sl.NodeIndex(Path(d)/'fast.sqlite3',16*1024**2)
            b.db.execute('CREATE TABLE audit_rows(kind TEXT,commit_seq INTEGER)')
            try:
                fast.install(SimpleNamespace(index=b))
                roots=[a.empty('lots'),b.empty('lots')];historical=[];rng=random.Random(42)
                for birth in range(1,7):
                    for index in (a,b):index.birth=birth
                    for _ in range(50):
                        key=[rng.randrange(40)];value={'v':[rng.randrange(1000),'汉字']}
                        roots=[idx.set('lots',root,key,value) for idx,root in zip((a,b),roots)]
                    roots=[idx.freeze('lots',root) for idx,root in zip((a,b),roots)]
                    self.assertEqual(*roots);historical.append(roots[0])
                    for idx,root in zip((a,b),roots):idx.prune({'lots':root});idx.db.commit()
                    self.assertEqual(a.db.execute('SELECT h FROM nodes ORDER BY h').fetchall(),b.db.execute('SELECT h FROM nodes ORDER BY h').fetchall())
                for root in historical:self.assertEqual(a.node('lots',root),b.node('lots',root))
                with self.assertRaises(sl.LedgerError):b.prune({'lots':'f'*64})
                b.cache.clear();b.size=0
                row=b.db.execute('SELECT v FROM nodes WHERE h=?',(sl._sql_hash(roots[1]),)).fetchone()
                b.db.execute('UPDATE blobs SET b=? WHERE h=?',(zlib.compress(b'{}'),row[0]))
                with self.assertRaises(sl.LedgerError):b.node('lots',roots[1])
            finally:
                a.close();b.close();sl.deepcopy,sl.strict_json,ports.deepcopy=saved


if __name__=='__main__':unittest.main()
