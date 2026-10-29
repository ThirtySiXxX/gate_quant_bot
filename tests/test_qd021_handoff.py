import json
from pathlib import Path
import signal
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from research.qd019.migration import STORE
from research.qd021 import handoff,collect
from research.qd021.entry import run


class HandoffChecks(unittest.TestCase):
    def test_default_off_has_no_data_access(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF_READ')):
            self.assertEqual(run(),{'status':'OFF'})

    def test_only_unique_verified_process_can_be_paused(self):
        original=dict(pid=123,start_ticks=456,state='R')
        with patch.object(handoff,'replay_processes',return_value=[original]),patch.object(handoff.os,'kill') as kill:
            with patch.object(handoff,'process_info',return_value=dict(original,state='T')):
                self.assertEqual(handoff.stop_writer(Path('/example'))['state'],'T')
            kill.assert_called_once_with(123,signal.SIGSTOP)
        with patch.object(handoff,'replay_processes',return_value=[original,original]),patch.object(handoff.os,'kill') as kill:
            with self.assertRaisesRegex(ValueError,'MULTIPLE'):handoff.stop_writer(Path('/example'))
            kill.assert_not_called()
        with patch.object(handoff,'replay_processes',return_value=[original]),patch.object(handoff.os,'kill'):
            with patch.object(handoff,'process_info',return_value=dict(original,start_ticks=789)):
                with self.assertRaisesRegex(ValueError,'PID_CHANGED'):handoff.stop_writer(Path('/example'))

    def test_previous_integrity_failure_is_not_automatically_retried(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d);p=data/'migration-run-1';p.mkdir()
            (p/'failure.json').write_text(json.dumps({'reason':'LedgerError:STORE_INTEGRITY_FAILURE'}))
            with self.assertRaisesRegex(ValueError,'NONQUOTA_FAILURE'):handoff.check_previous_failure(data)
            (p/'failure.json').write_text(json.dumps({'reason':'LedgerError:RESOURCE_EXHAUSTED at /wall'}))
            handoff.check_previous_failure(data)
            (p/'failure.json').write_text(json.dumps({'reason':'LedgerError:RESOURCE_EXHAUSTED_READ at /'}))
            with self.assertRaisesRegex(ValueError,'NONQUOTA_FAILURE'):handoff.check_previous_failure(data)
            for reason in ('OBSERVED_WALL_SECONDS_LIMIT','OBSERVED_CPU_SECONDS_LIMIT','OBSERVED_RSS_BYTES_LIMIT'):
                (p/'failure.json').write_text(json.dumps({'reason':'ValueError:'+reason}))
                handoff.check_previous_failure(data)

    def test_return_archive_only_contains_allowlisted_evidence_and_exports(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'research/.data/qd021-active/test/qd015';store=data/STORE;store.mkdir(parents=True)
            manifest=root/'research/.data/qd021-handoff/current.json';manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps(dict(active_data_root=str(data),operation_id='test')))
            release=root/'research/qd021/release.json';release.parent.mkdir(parents=True);release.write_text('{}')
            (store/'HEAD').write_text('{"committed_seq":123}')
            (store/'cache.sqlite3').write_text('NOT_FOR_RETURN')
            run_dir=data/'optimization-run-test';run_dir.mkdir();(run_dir/'result.json').write_text('{"status":"PAUSED_AT_COMMIT_BOUNDARY"}')
            (root/'.env').write_text('FICTITIOUS_SECRET_SENTINEL')
            with patch.object(collect,'ROOT',root),patch('builtins.print'):output=collect.collect()
            with tarfile.open(output) as tar:
                names=tar.getnames();summary=json.load(tar.extractfile('summary.json'))
            self.assertIn('checkpoint/HEAD',names);self.assertIn('run/result.json',names)
            self.assertFalse(any('sqlite3' in name or '.env' in name for name in names))
            self.assertEqual(summary['head']['committed_seq'],123)


if __name__=='__main__':unittest.main()
