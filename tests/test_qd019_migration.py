"""Focused rejection checks; actual relocation is tested on a frozen copy."""
from pathlib import Path
from copy import deepcopy
import json
import os
import sqlite3
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from research.qd019 import migration as m
from research.qd019.entry import run


class MigrationChecks(unittest.TestCase):
    def test_default_off_does_not_read_data(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('OFF_READ')):
            self.assertEqual(run()['status'], 'OFF')

    def test_inventory_detects_changed_missing_and_added_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data';p.mkdir();f=p/'candle.jsonl';f.write_bytes(b'original\n')
            expected=m.inventory(p);self.assertEqual(m.verify_inventory(p,expected),9)
            f.write_bytes(b'changed!\n')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)
            f.unlink()
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)
            f.write_bytes(b'original\n');(p/'extra').write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)

    def test_io_relocation_is_explicit_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as d:
            new=Path(d).resolve()
            self.assertEqual(m.relocate_path('/old/qd015/a.db','/old/qd015',new),str(new/'a.db'))
            with self.assertRaisesRegex(ValueError,'UNDECLARED'):m.relocate_path('/other/a','/old/qd015',new)
            with self.assertRaisesRegex(ValueError,'TRAVERSAL'):m.relocate_path('/old/qd015/../outside','/old/qd015',new)
            with self.assertRaisesRegex(ValueError,'UNSAFE'):m.relative(new,'../outside')
            (new/'link').symlink_to(new)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):m.relative(new,'link/x')

    def test_host_build_admission_does_not_ignore_numeric_versions(self):
        expected=dict(python_version='3.13.7',numpy='2.5.2',pandas='3.0.5')
        host=dict(expected,implementation='CPython',python='different Linux GCC build')
        with patch.object(m,'runtime',return_value=host),patch.object(m.sys,'platform','linux'):
            self.assertEqual(m.admit_runtime(expected),host)
        for name in ('python_version','numpy','pandas'):
            with patch.object(m,'runtime',return_value=dict(host,**{name:'wrong'})):
                with self.assertRaises(ValueError):m.admit_runtime(expected)
        with patch.object(m,'runtime',return_value=host),patch.object(m.sys,'platform','win32'):
            with self.assertRaisesRegex(ValueError,'WSL2'):m.admit_runtime(expected)


class LocalReturnBundle(unittest.TestCase):
    def test_only_result_allowlist_and_cached_view_are_returned(self):
        from research.qd019 import collect as c
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'research/.data/qd019-import/qd015';store=data/m.STORE
            store.mkdir(parents=True);run=data/'migration-run-1';run.mkdir()
            (root/'.env').write_text('FICTITIOUS_TEST_SENTINEL')
            head=dict(committed_seq=1,cutoff=dict(at_us=1,slot=5))
            (store/'HEAD').write_text(json.dumps(head));(run/'failure.json').write_text('{"reason":"synthetic"}')
            db=sqlite3.connect(store/'cache.sqlite3');db.execute('CREATE TABLE views(b BLOB)')
            db.execute('INSERT INTO views VALUES (?)',(json.dumps(dict(knowledge_cutoff=head['cutoff'],balance=dict(cash='100'))).encode(),));db.commit();db.close()
            with patch.object(c,'ROOT',root),patch('builtins.print'):
                output=c.collect()
            with tarfile.open(output) as t:
                names=t.getnames();summary=json.load(t.extractfile('return-summary.json'))
            self.assertIn('run/failure.json',names);self.assertIn('checkpoint/HEAD',names)
            self.assertFalse(any('.env' in n or 'sqlite3' in n for n in names))
            self.assertEqual(summary['cached_view']['balance']['cash'],'100')


@unittest.skipUnless(os.environ.get('QD019_FAULT_COPY'), 'requires an explicitly prepared disposable frozen copy')
class FrozenAccountRejection(unittest.TestCase):
    def test_numeric_mismatch_stops_before_publication(self):
        from research.qd009 import streaming_ledger as sl
        from research.qd012.actual_snapshot_entry import ObservationBudget, network_off
        from research.qd013.runner import Replay
        data=Path(os.environ['QD019_FAULT_COPY'])
        manifest=deepcopy(m.read(os.environ['QD019_TRANSFER_MANIFEST']))
        manifest['numeric_seals'][0]['economic_state_sha256']='0'*64
        budget=ObservationBudget(dict(wall_seconds=300,cpu_seconds=240,rss_bytes=1073741824))
        with network_off():
            m.install_budgets(data,manifest);ledger=m.open_ledger(data,manifest,budget.check)
            try:
                m.activate(ledger,manifest);before=deepcopy(ledger.head)
                at=manifest['numeric_seals'][0]['cutoff']['at_us']
                with self.assertRaisesRegex(sl.LedgerError,'MIGRATION_NUMERIC_DIVERGENCE'):
                    Replay(ledger).advance_chunk(at)
                self.assertEqual(ledger.head,before)
                self.assertEqual(ledger.current_head()['status'],'INTEGRITY_STOPPED')
                self.assertFalse((ledger.root/f"manifest-{before['committed_seq']+1:08}.json").exists())
                with self.assertRaises(sl.LedgerError):Replay(ledger).advance_chunk(at)
                (data.parent/'numeric-rejection-result.json').write_text(json.dumps(dict(
                    status='PASS',head_unchanged=True,new_commit_published=False,
                    later_advance_rejected=True,head=ledger.head,observed=budget.observed()),sort_keys=True,indent=2)+'\n')
            finally:ledger.close()


if __name__=='__main__':unittest.main()
