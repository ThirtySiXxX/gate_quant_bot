"""Six bounded consumer checks. Literal fixtures only; no QD/old test imports."""
import ast
import copy
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from research.qr015 import dataset as d

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'research/.data/qr015/fixtures'


def episode(instrument=None, ident='1', decision=None, status='valid', end=None, known=None):
    q = d.qr
    instrument = instrument or q.INSTRUMENTS[0]
    decision = q.TRAIN_START_US + 200*q.HOUR_US if decision is None else decision
    end = decision + 2*q.HOUR_US if end is None else end
    known = end + q.HOUR_US if known is None else known
    p = q.EntryProposal('synthetic-account', 'synthetic-P0', instrument, 'p'+ident, 'fixture:pre-'+ident,
        'P0', 'ALLOW_ALL', 'QR010_SHARED_NATIVE_X10', decision, 1, True, 'flat_entry', ('fixture:proposal-'+ident,))
    valid = status == 'valid'
    e = q.Episode(p, 'e'+ident, 1, status, decision+q.HOUR_US, end if valid else None, known if valid else None,
        '2' if valid else None, '1000', valid, valid, valid,
        (decision, end) if valid else (decision,), (), (known,) if valid else (),
        'fixture:as-known', 'fixture:scoped-complete' if valid else None, ('fixture:episode-'+ident,),
        () if valid else ('fixture:open-at-cutoff',))
    return dict(schema='qd013.controlled-episode.v1', qr014_episode_fields=asdict(e),
        cost_breakdown_exact={'realized_price_pnl_usdt':'3','entry_fee_cash_usdt':'-0.5','exit_fee_cash_usdt':'-0.5','funding_cash_usdt':'0'},
        cost_attribution_scope='WHOLE_MATURE_EPISODE' if valid else 'CLOSED_SLICES_ONLY_NOT_A_LABEL_TARGET',
        pre_decision_equity_exact='10000', pre_decision_positions={i:0 for i in q.INSTRUMENTS},
        accepted_export_ref='fixture:accepted-'+ident, registry_refs=['fixture:registry-'+ident],
        qr014_compatible=True, qr014_exclusion_reason=None,
        censoring=None if valid else 'ECONOMIC_CUTOFF_OPEN', training_authorized=False)


def put_json(path, value):
    raw = d.canonical(value)+b'\n'; path.write_bytes(raw)
    return d.digest(raw)


def put_lines(path, rows):
    raw = b''.join(d.canonical(x)+b'\n' for x in rows); path.write_bytes(raw)
    return dict(path=str(path), rows=len(rows), sha256=d.digest(raw))


def fixture(root, rows, *, complete=True, intervals=(), scope=None):
    root.mkdir()
    scope = scope or dict(warmup_start_us=1_672_531_200_000_000, initial_us=d.qr.TRAIN_START_US,
        economic_end_us=d.qr.ECONOMIC_END_US, tail_end_us=d.qr.TAIL_END_US)
    sources = {k:d.digest(('synthetic:'+k).encode()) for k in d.SOURCE_METADATA}
    identity = dict(schema='qd013.market-cache.v1', sources=sources, code=d.QD_CODE,
        config={'synthetic':True}, scope=scope, availability='closed_bar_strict_R_native_main_open_MARK_named_clock',
        decimal_codec='exact_text_and_f64_roundtrip')
    key = d.digest(d.canonical(identity)); cache = root/'market.sqlite'; db=sqlite3.connect(cache)
    db.executescript('CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT);CREATE TABLE cells(kind TEXT,inst TEXT,at INTEGER,v BLOB,sha TEXT,PRIMARY KEY(kind,inst,at));')
    cells = {}
    for row in rows:
        p=row['qr014_episode_fields']['proposal']; at=p['decision_us']; inst=p['instrument_id']
        for opened in range(at-169*d.qr.HOUR_US, at, d.qr.HOUR_US):
            price=100+(opened//d.qr.HOUR_US)%97
            value=dict(instrument_id=inst,open_us=opened,close_us=opened+d.qr.HOUR_US,available_us=opened+d.qr.HOUR_US,
                open=str(price),high=str(price+2),low=str(price-2),close=str(price+1),volume_contracts='0.1',
                row_id='fixture:'+inst+':'+str(opened))
            cells[inst,opened]=d.canonical(value)
    for (inst,at),raw in cells.items():
        db.execute('INSERT INTO cells VALUES (?,?,?,?,?)',('hour',inst,at,raw,d.digest(raw)))
    content_hash=d.digest(d.canonical(sorted((inst,at,d.digest(raw)) for (inst,at),raw in cells.items())))
    meta=dict(state='COMPLETE',schema=identity['schema'],key=key,identity=identity,rows=len(cells),content_sha256=content_hash)
    for k,v in meta.items():db.execute('INSERT INTO metadata VALUES (?,?)',(k,json.dumps(v)))
    db.commit();db.close()
    export=put_lines(root/'episodes.jsonl',rows)
    export_identity=dict(fixture=True,account='synthetic-account',trajectory='synthetic-P0',scope=scope,cache_key=key)
    manifest=dict(schema='qd013.episode-export.v1',state='COMPLETE',identity=export_identity,
        rows=len(rows),sha256=export['sha256'],training_authorized=False)
    manifest_hash=put_json(root/'export-manifest.json',manifest)
    purge=dict(complete=complete,instruments=list(d.qr.INSTRUMENTS),source_ref='fixture:scoped-heldout-inventory')
    if intervals:purge['additional_intervals']=put_lines(root/'heldout.jsonl',intervals)
    request=dict(schema=d.REQUEST_SCHEMA,training_authorized=False,input_kind='SYNTHETIC',
        qd_commit=d.QD_COMMIT,qd_manifest_sha256=d.QD_MANIFEST_SHA256,qd_code_sha256=d.QD_CODE,
        source_metadata=sources,source_binding_ref='fixture:export-cache-source-link',
        binding=dict(account_id='synthetic-account',trajectory_id='synthetic-P0',scenario_id='P0',policy_id='ALLOW_ALL',
            account_binding_id='QR010_SHARED_NATIVE_X10',instruments=list(d.qr.INSTRUMENTS),scope=scope),
        input_received_at_us=d.qr.TAIL_END_US+d.qr.HOUR_US,assembled_at_us=d.qr.TAIL_END_US+2*d.qr.HOUR_US,
        purge=purge,export=dict(manifest_path=str(root/'export-manifest.json'),manifest_sha256=manifest_hash,
            episodes_path=export['path'],identity=export_identity),
        market_cache=dict(path=str(cache),identity=identity,key=key,content_sha256=content_hash,rows=len(cells)),
        limits=dict(max_records=100,max_input_bytes=1024*1024,max_row_bytes=64*1024,max_output_bytes=2*1024*1024))
    return request


class LocalDatasetTests(unittest.TestCase):
    def setUp(self):
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        self.root=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=EVIDENCE))
        self.serial=0

    def run_request(self,request,**kwargs):
        self.serial+=1; path=self.root/f'request-{self.serial}.json'
        sha=put_json(path,request); out=self.root/f'output-{self.serial}'
        result=d.assemble_local(path,expected_request_sha256=sha,output_dir=out,enabled=True,
            authorization_ref='fixture:synthetic-development-only',**kwargs)
        return out,result

    def test_01_mature_and_censored_preserve_labels_and_lineage(self):
        records=[episode(),episode(d.qr.INSTRUMENTS[1],ident='2',status='open')]
        request=fixture(self.root/'input',records);out,result=self.run_request(request)
        rows=[d.load(x) for x in (out/'samples.jsonl').read_bytes().splitlines()]
        self.assertEqual(rows[0]['model_target_fraction_12'],'0.002000000000')
        self.assertTrue(rows[0]['train_eligible']);self.assertEqual(len(rows[0]['features']),12)
        self.assertEqual(rows[0]['feature_names'],list(d.qr.FEATURE_NAMES))
        self.assertEqual(rows[0]['source_episode_fields']['net_cash_exact'],'2')
        self.assertEqual(rows[0]['source_episode_fields']['label_revision'],1)
        self.assertEqual(rows[1]['label_status'],'open');self.assertIsNone(rows[1]['model_target_fraction_12'])
        self.assertEqual(rows[1]['censoring'],'ECONOMIC_CUTOFF_OPEN')
        self.assertEqual(rows[1]['source_episode_fields']['as_known_view_ref'],'fixture:as-known')
        self.assertFalse(result['training_authorized']);self.assertFalse(result['training_ready'])
        for name,spec in result['files'].items():self.assertEqual(d.digest((out/name).read_bytes()),spec['sha256'])
        summary=d.load((out/'summary.json').read_bytes())
        self.assertEqual(summary['unique_episodes'],2);self.assertEqual(summary['counts']['censored_markers'],1)
        self.assertEqual(summary['market_hour_cell_reads'],338)

    def test_02_pinned_source_version_scope_and_corruption_rejected(self):
        request=fixture(self.root/'input',[episode()])
        mutations=[('qd_commit','0'*40,'QD_VERSION'),('source_metadata',{},'SOURCE_SCOPE')]
        for key,value,error in mutations:
            bad=copy.deepcopy(request);bad[key]=value
            with self.assertRaisesRegex(d.DatasetError,error):self.run_request(bad)
        bad=copy.deepcopy(request);bad['export']['identity']['trajectory']='wrong'
        with self.assertRaisesRegex(d.DatasetError,'EXPORT_IDENTITY'):self.run_request(bad)
        bad=copy.deepcopy(request);bad['market_cache']['identity']=copy.deepcopy(bad['market_cache']['identity'])
        bad['market_cache']['identity']['scope']['initial_us']+=d.qr.HOUR_US
        with self.assertRaisesRegex(d.DatasetError,'CACHE_IDENTITY'):self.run_request(bad)
        bad=copy.deepcopy(request);bad['binding']['scenario_id']='F_HIGH'
        with self.assertRaisesRegex(d.DatasetError,'BASELINE_ONLY'):self.run_request(bad)
        bad=copy.deepcopy(request);bad['input_kind']='ACTUAL'
        with self.assertRaisesRegex(d.DatasetError,'ACTUAL_SOURCE_VERSION'):self.run_request(bad)
        bad=copy.deepcopy(request);corrupt=self.root/'corrupt-market.sqlite'
        corrupt.write_bytes(Path(request['market_cache']['path']).read_bytes())
        bad['market_cache']['path']=str(corrupt);db=sqlite3.connect(corrupt)
        db.execute("UPDATE cells SET sha=?",('0'*64,));db.commit();db.close()
        with self.assertRaisesRegex(d.DatasetError,'CACHE_CELL_CORRUPTION'):self.run_request(bad)
        self.assertTrue((self.root/f'output-{self.serial}'/'failure.json').exists())
        self.assertFalse((self.root/f'output-{self.serial}'/'manifest.json').exists())

    def test_03_revisions_duplicates_and_wire_hash_conflicts_rejected(self):
        first=episode();second=copy.deepcopy(first);second['qr014_episode_fields']['label_revision']=2
        request=fixture(self.root/'duplicate',[first,second])
        with self.assertRaisesRegex(d.DatasetError,'DUPLICATE_PROPOSAL_OR_EPISODE_REVISION'):
            self.run_request(request,batch_size=1)
        changed=copy.deepcopy(first);changed['qr014_episode_fields']['proposal']['proposal_id']='another'
        request=fixture(self.root/'episode-conflict',[first,changed])
        with self.assertRaisesRegex(d.DatasetError,'DUPLICATE_PROPOSAL_OR_EPISODE_REVISION'):self.run_request(request)
        request=fixture(self.root/'hash',[first]);path=Path(request['export']['episodes_path'])
        path.write_bytes(path.read_bytes().replace(b'"net_cash_exact":"2"',b'"net_cash_exact":"3"'))
        with self.assertRaisesRegex(d.DatasetError,'EXPORT_COUNT_OR_HASH_MISMATCH'):self.run_request(request)

    def test_04_strict_time_purge_cross_asset_and_frozen_splits(self):
        btc=episode(); start=btc['qr014_episode_fields']['label_known_at_us']
        limit=d.qr.TRAIN_END_US-d.qr.EMBARGO_US
        rows=[btc,episode(d.qr.INSTRUMENTS[1],ident='2',decision=d.qr.TRAIN_END_US-3*d.qr.EMBARGO_US,
            end=limit-1,known=limit),episode(ident='3',decision=d.qr.TRAIN_END_US),
            episode(d.qr.INSTRUMENTS[1],ident='4',decision=d.qr.VALID_END_US)]
        intervals=[dict(instrument_id=d.qr.INSTRUMENTS[1],start_us=start,end_us=start+1,source_ref='fixture:ETH-heldout-overlap')]
        request=fixture(self.root/'input',rows,intervals=intervals);out,_=self.run_request(request,batch_size=1)
        results=[d.load(x) for x in (out/'samples.jsonl').read_bytes().splitlines()]
        self.assertIn('CROSS_ASSET_HELDOUT_INFORMATION_OVERLAP',results[0]['reasons'])
        self.assertEqual(results[0]['overlap_witness'][0]['instrument_id'],d.qr.INSTRUMENTS[1])
        self.assertIn('LABEL_KNOWN_STRICT_24H_FAILED',results[1]['reasons'])
        self.assertEqual([x['partition'] for x in results],['train_2024','train_2024','validation_2025','exposed_audit_2026'])
        self.assertFalse(any(x['train_eligible'] for x in results))
        bad=copy.deepcopy(request);bad['binding']['scope']['economic_end_us']=d.qr.TRAIN_END_US
        bad['binding']['scope']['tail_end_us']=d.qr.TRAIN_END_US+2*d.qr.HOUR_US
        with self.assertRaisesRegex(d.DatasetError,'PARTIAL_SCOPE_CANNOT'):self.run_request(bad)

    def test_05_batched_and_continuous_outputs_identical(self):
        rows=[episode(ident='3',decision=d.qr.VALID_END_US),episode(),
              episode(d.qr.INSTRUMENTS[1],ident='2',status='open')]
        request=fixture(self.root/'input',rows)
        first,a=self.run_request(request,batch_size=1);second,b=self.run_request(request,batch_size=3)
        self.assertEqual(a,b)
        for name in ('samples.jsonl','information-intervals.jsonl','summary.json','manifest.json'):
            self.assertEqual((first/name).read_bytes(),(second/name).read_bytes())

    def test_06_default_off_empty_insufficient_and_no_fit_entrypoint(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('OFF must not read inputs')):
            result=d.assemble_local('/missing',output_dir='/missing',expected_request_sha256='wrong')
        self.assertEqual(result,dict(state='OFF',training_authorized=False,input_reads=0,fit_calls=0))
        request=fixture(self.root/'empty',[],complete=False);out,_=self.run_request(request)
        summary=d.load((out/'summary.json').read_bytes())
        self.assertEqual(summary['counts']['rows'],0);self.assertEqual(summary['unique_episodes'],0)
        self.assertIn('NO_TRAINING_ROWS',summary['readiness_reasons'])
        self.assertIsNone(summary['dependence']['effective_independent_sample_size'])
        self.assertIsNone(summary['standalone_unfilled_proposals']);self.assertFalse(summary['training_ready'])
        tree=ast.parse(Path(d.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=node.func.attr if isinstance(node.func,ast.Attribute) else getattr(node.func,'id','')
                self.assertNotIn(name,{'fit','fit_transform','partial_fit','train','export_all','build_cache','advance_chunk'})
            if isinstance(node,ast.Import):
                self.assertTrue(all(x.name.split('.')[0] not in ('numpy','pandas','sklearn','torch','src') for x in node.names))


if __name__ == '__main__':
    unittest.main()
