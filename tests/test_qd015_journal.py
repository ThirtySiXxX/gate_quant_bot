"""Journal-only engineering checks. No raw history or prior test invocation."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import os
import socket
import struct
import time
import unittest
from unittest.mock import patch
from research.qd009 import streaming_ledger as sl
from research.qd011.driver import scan
from research.qd013.market import MarketCache
from research.qd013.exports import export_all
from research.qd014.runner import create as plain_create
from research.qd015 import journal
from research.qd015.runner import create, Replay, profile
from research.qd015.cache_identity import producer_identity
from research.qd015.entry import run

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/.data/qd015'
FIXTURE=ROOT/'research/qd015/synthetic-input.json'
FIXTURE_SHA='270640538be2a91b09e77b66e6eb86b5fb29c0714f55521abe1dfc808c35bb27'


class JournalStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def deny(*a,**k):raise AssertionError('QD015_OFFLINE_ONLY')
        cls.patches=[patch.object(socket,'create_connection',deny),patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny)]
        for p in cls.patches:p.start()
        DATA.mkdir(parents=True,exist_ok=True);cls.root=DATA/('engineering-'+str(time.monotonic_ns()));cls.root.mkdir()
        cls.budget=sl.configure_resource_budget(DATA,127*1024**2)
        cls.observations={};cls.account=None

    @classmethod
    def tearDownClass(cls):
        if cls.account is not None:cls.account.ledger.close()
        raw=json.dumps(cls.observations,sort_keys=True,indent=2).encode()+b'\n';p=cls.root/'observations.json'
        cls.budget.issue(p,len(raw),len(raw));p.write_bytes(raw)
        for p in reversed(cls.patches):p.stop()

    def test_01_exact_codec_corruption_and_decompression_bound(self):
        spec=profile();journal.validate(spec);totals=dict(raw_bytes=0,framed_bytes=0,encode_seconds=0.,write_seconds=0.,read_decode_seconds=0.)
        for n in range(1,17):
            source=DATA/'storage-1/plain'/f'journal-{n:08}.json'
            # Optional benchmark fixture absent in a clean checkout: the frozen
            # typed input below still exercises the same codec without old data.
            raw=source.read_bytes() if source.exists() else sl.canonical_bytes(dict(synthetic=True,record=n,repeat=['exact evidence']*1000))+b'\n'
            started=time.perf_counter();encoded=journal.encode(raw,spec);totals['encode_seconds']+=time.perf_counter()-started
            target=self.root/f'codec-{n:08}.qjz';self.budget.issue(target,len(encoded),len(encoded));started=time.perf_counter()
            with target.open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
            totals['write_seconds']+=time.perf_counter()-started;started=time.perf_counter()
            self.assertEqual(journal.decode(target.read_bytes(),spec),raw);totals['read_decode_seconds']+=time.perf_counter()-started
            totals['raw_bytes']+=len(raw);totals['framed_bytes']+=len(encoded)
        self.observations['framed_storage']=totals
        for bad in (encoded[:4],b'BADMAGIC'+encoded[8:],encoded[:-1],encoded+b'trailing',encoded[:-1]+bytes([encoded[-1]^1])):
            with self.assertRaises(journal.JournalError):journal.decode(bad,spec)
        size=struct.unpack('>I',encoded[8:12])[0];header=json.loads(encoded[12:12+size]);body=encoded[12+size:]
        for declared in (journal.HARD_MAX+1,0):
            changed=dict(header,raw_bytes=declared);raw_header=journal.canonical(changed)
            bomb=journal.MAGIC+struct.pack('>I',len(raw_header))+raw_header+body
            with self.assertRaises(journal.JournalError):journal.decode(bomb,spec)
        with self.assertRaises(journal.JournalError):journal.validate(dict(spec,codec='unknown'))
        with self.assertRaises(journal.JournalError):journal.validate(dict(spec,implementation_sha256='0'*64))

    def test_02_atomic_bytes_do_not_replace_valid_immutable_evidence(self):
        spec=profile();path=self.root/'journal-atomic.qjz';raw=journal.encode(b'{"evidence":1}\n',spec)
        sl._atomic(path,None,_raw=raw)
        with self.assertRaisesRegex(sl.LedgerError,'STORE_INTEGRITY_FAILURE'):sl._atomic(path,None,_raw=raw+b'bad')
        self.assertEqual(path.read_bytes(),raw)
        unpublished=self.root/'journal-unpublished.qjz'
        with patch.object(os,'replace',side_effect=OSError('synthetic rename failure')):
            with self.assertRaises(OSError):sl._atomic(unpublished,None,_raw=raw)
        self.assertFalse(unpublished.exists());self.assertTrue(list(self.root.glob('journal-unpublished.qjz.*.pending')))
        self.assertEqual(path.read_bytes(),raw)

    def test_03_registered_financial_equality_and_close_reopen(self):
        raw=FIXTURE.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),FIXTURE_SHA)
        f=json.loads(raw);self.assertEqual(f['source_cache_identity']['sources'],['QD014_SYNTHETIC'])
        identity=deepcopy(f['source_cache_identity']);identity['code']={'qd015_fixture_sha256':FIXTURE_SHA}
        cache=MarketCache.build(self.root/'fixture-market.sqlite3',identity,iter(f['records']))
        scope=identity['scope'];args=dict(initial_us=scope['initial_us'],economic_end_us=scope['economic_end_us'],tail_end_us=scope['tail_end_us'],write_budget=self.budget.issue)
        plain=new=None
        try:
            plain=plain_create(self.root/'plain',cache,**args);new=create(self.root/'compressed',cache,**args)
            split=new.ledger.config['_plan_index'].times[5]
            plain.advance_chunk(split);new.advance_chunk(split)
            head=deepcopy(new.ledger.head);states=new.states(split);new.ledger.close();new=Replay.reopen(self.root/'compressed/store')
            self.assertEqual(new.ledger.head,head);self.assertEqual(new.states(split),states)
            last=new.ledger.config['_plan_index'].times[-1];plain.advance_chunk(last);new.advance_chunk(last)
            pv,nv=plain.view(last),new.view(last)
            self.assertEqual(pv['economic_state_sha256'],nv['economic_state_sha256'])
            self.assertEqual(pv['balance'],nv['balance'])
            for c in ('lots','closed_slices','obligations','entries','links','orders','decisions'):
                self.assertEqual(list(scan(plain.ledger,pv,c)),list(scan(new.ledger,nv,c)),c)
            pe=[r['body'] for r in scan(plain.ledger,pv,'events')];ne=[r['body'] for r in scan(new.ledger,nv,'events')]
            self.assertEqual(pe,ne);self.assertGreater(sum(r['record_type']=='Fill' for r in ne),2)
            keys=('label_status','net_cash_exact','gross_entry_notional_exact','label_end_us','label_known_at_us','cash_settled','natural_exit','completeness_verified')
            pr,nr=export_all(plain,last),export_all(new,last)
            self.assertEqual([{k:r['qr014_episode_fields'][k] for k in keys} for r in pr],[{k:r['qr014_episode_fields'][k] for k in keys} for r in nr])
            self.assertEqual([r['cost_breakdown_exact'] for r in pr],[r['cost_breakdown_exact'] for r in nr])
            self.assertTrue(any(r['qr014_episode_fields']['label_status']=='valid' for r in nr))
            self.assertTrue(any(r['censoring']=='ECONOMIC_CUTOFF_OPEN' for r in nr))
            plain_files=list(plain.ledger.root.glob('journal-*.json'));new_files=list(new.ledger.root.glob('journal-*.qjz'))
            self.assertEqual(len(plain_files),len(new_files));self.assertFalse(list(new.ledger.root.glob('journal-*.json')))
            self.assertNotIn('journal_storage',plain.ledger.config);self.assertIn('journal_storage',new.ledger.request['config'])
            self.assertLess(sum(p.stat().st_size for p in new_files),sum(p.stat().st_size for p in plain_files))
            self.observations['registered']=dict(events=len(ne),fills=sum(r['record_type']=='Fill' for r in ne),exports=len(nr),plain_journal_bytes=sum(p.stat().st_size for p in plain_files),compressed_journal_bytes=sum(p.stat().st_size for p in new_files),journals=len(new_files),economic_state_sha256=nv['economic_state_sha256'],same_economic_state=True)
            self.__class__.account=new;self.__class__.last=last;self.__class__.before_head=deepcopy(new.ledger.head);self.__class__.before_states=new.states(last)
            self.__class__.before_events=ne;new=None
        finally:
            if plain:plain.ledger.close()
            if new:new.ledger.close()
            cache.close()

    def test_04_checkpoint_restore_and_persisted_corruption_rejection(self):
        self.assertIsNotNone(self.account,'registered test must succeed first')
        cp=self.account.restore_checkpoint()
        self.assertEqual(self.account.ledger.head,self.before_head);self.assertEqual(self.account.states(self.last),self.before_states)
        self.assertEqual([r['body'] for r in scan(self.account.ledger,self.account.view(self.last),'events')],self.before_events)
        self.assertTrue(cp['files']);self.assertTrue(all(r['format_version']==3 for r in cp['files']))
        self.observations['checkpoint']=dict(committed_seq=cp['committed_seq'],files=len(cp['files']),checkpoint_sha256=cp['checkpoint_sha256'],full_index_rebuild=True)
        store=self.account.ledger.root;self.account.ledger.close();last=store/f"journal-{cp['committed_seq']:08}.qjz"
        valid=last.read_bytes();backup=self.root/'valid-last-before-corruption.qjz';self.budget.issue(backup,len(valid),len(valid));backup.write_bytes(valid)
        head=(store/'HEAD').read_bytes();last.write_bytes(valid[:-1]+bytes([valid[-1]^1]))
        with self.assertRaisesRegex(sl.LedgerError,'STORE_INTEGRITY_FAILURE'):Replay.reopen(store)
        self.assertEqual((store/'HEAD').read_bytes(),head);self.assertEqual(backup.read_bytes(),valid)
        self.observations['checkpoint']['corruption_rejected_head_unchanged']=True

    def test_05_off_gate_and_market_identity_excludes_journal(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF_READ')):
            self.assertEqual(run()['status'],'OFF')
            with self.assertRaisesRegex(ValueError,'NAMED_QD015'):
                run(authorize_actual_replay=True,human_authorization_ref='QF-APPROVAL-QD014-FULL-P0-1')
        before=producer_identity()
        with patch.object(journal,'__file__','unused-unrelated-journal-change'):
            self.assertEqual(producer_identity(),before)
        self.assertNotIn('research/qd009/streaming_ledger.py',before['files'])
        self.assertTrue(before['primitives'])
        self.assertTrue(before['runtime']['numpy']);self.assertTrue(before['runtime']['pandas'])
        self.assertTrue(before['constants']['interval_seconds'])


if __name__=='__main__':unittest.main()
