"""One targeted check for the observed resident stop and exact-state continuation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import patch
from research.qd009 import streaming_ledger as sl
from research.qd013.market import MarketCache
from research.qd013.runner import Replay
from research.qd015.runner import create
from research.qd016.resident import ContinuationLedger
from research.qd016.entry import run


class ResidentContinuation(unittest.TestCase):
    def test_observed_stop_safe_resolution_and_process_bound(self):
        root=Path(__file__).resolve().parents[1];data=root/'research/.data/qd016';data.mkdir(parents=True,exist_ok=True)
        out=data/('engineering-'+str(time.monotonic_ns()));out.mkdir();budget=sl.configure_resource_budget(data,32*1024**2)
        def deny(*a,**k):raise AssertionError('OFFLINE_ONLY')
        with patch.object(socket,'create_connection',deny),patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny):
            raw=(root/'research/qd015/synthetic-input.json').read_bytes();h=hashlib.sha256(raw).hexdigest()
            self.assertEqual(h,'270640538be2a91b09e77b66e6eb86b5fb29c0714f55521abe1dfc808c35bb27')
            f=json.loads(raw);identity=deepcopy(f['source_cache_identity']);identity['code']={'qd015_fixture_sha256':h}
            cache=MarketCache.build(out/'market.sqlite3',identity,iter(f['records']));scope=identity['scope']
            replay=create(out/'account',cache,initial_us=scope['initial_us'],economic_end_us=scope['economic_end_us'],tail_end_us=scope['tail_end_us'],write_budget=budget.issue)
            try:
                times=replay.ledger.config['_plan_index'].times;replay.advance_chunk(times[2]);head=deepcopy(replay.ledger.head)
                replay.ledger.index.cap=1
                with self.assertRaisesRegex(sl.LedgerError,'RESOURCE_EXHAUSTED'):replay.advance_chunk(times[3])
                self.assertEqual(replay.ledger.head,head);self.assertEqual(replay.ledger.control['status'],'RESOURCE_STOPPED')
                store=replay.ledger.root;replay.ledger.close()
                pointer=sl.load_json((store/'CONTROL').read_bytes());stop=sl.load_json((store/f"control-{pointer['control_seq']:08}.json").read_bytes())
                op=dict(authorization_ref='QD016_SYNTHETIC',expected_head=head,stop_control=pointer,
                    failed_request_sha256=stop['request_sha256'],process_rss_limit_bytes=536870912)
                old_stop_bytes=(store/f"control-{pointer['control_seq']:08}.json").read_bytes()
                bad=dict(op,failed_request_sha256='0'*64)
                wrong=ContinuationLedger(store,operation=bad,record_name='wrong-operation.json',process_bound=lambda:None)
                try:
                    with self.assertRaises(sl.LedgerError):wrong.activate()
                    self.assertFalse((store/'wrong-operation.json').exists());self.assertEqual(wrong.head,head)
                finally:wrong.close()
                checks=[]
                def bound():checks.append(True)
                resumed=ContinuationLedger(store,operation=op,record_name='resident-operation.json',process_bound=bound)
                replay=Replay(resumed);record=resumed.activate()
                self.assertEqual(resumed.head,head);self.assertEqual(resumed.current_head()['status'],'ACTIVE')
                self.assertIsNone(resumed.control['guard']);self.assertEqual(resumed.spent['attempts_started'],2)
                self.assertEqual((store/f"control-{pointer['control_seq']:08}.json").read_bytes(),old_stop_bytes)
                resumed.index.cap=1  # prove the old independent working guard is absent
                replay.advance_chunk(times[3]);self.assertTrue(checks)
                saved=deepcopy(resumed.head);resumed.close()
                resumed=ContinuationLedger(store,operation=op,record_name='resident-operation.json',process_bound=bound);replay=Replay(resumed)
                self.assertEqual(resumed.head,saved);self.assertEqual(resumed.current_head()['status'],'ACTIVE')
                replay.advance_chunk(times[-1]);view=replay.view(times[-1])
                self.assertEqual(view['economic_state_sha256'],'cdc0fefc3582f3e3381c1781017dac965155a5cdd9933c081489e1de0fd0d301')
                self.assertEqual(resumed.spent['attempts_started'],2)
                # A later, different stop is not waived by this authority.
                saved_request=sl.load_json((store/stop['guard_input']['relative_path']).read_bytes())
                resumed.guard_input=stop['guard_input'];resumed._control('write_guard',saved_request)
                resumed._control('resource_stop',saved_request,error=dict(code='RESOURCE_EXHAUSTED',path='/process_budget'))
                self.assertEqual(resumed._load_control()['status'],'RESOURCE_STOPPED')
                evidence=dict(status='PASS',before=head,after=resumed.head,known_economic_hash=view['economic_state_sha256'],
                    process_bound_checks=len(checks),activation=record,prior_failure_preserved=True,attempts=resumed.spent['attempts_started'],later_stop_not_waived=True)
                (out/'result.json').write_text(json.dumps(evidence,sort_keys=True,indent=2)+'\n')
                with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF_READ')):self.assertEqual(run()['status'],'OFF')
            finally:
                replay.ledger.close();cache.close()


if __name__=='__main__':unittest.main()
