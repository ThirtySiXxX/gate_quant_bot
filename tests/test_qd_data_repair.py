"""Bounded synthetic producer tests; expected arithmetic is literal, no QR imports."""
from copy import deepcopy
from decimal import Inexact, Rounded, localcontext
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from research.qd008 import repair_history as r


def wire_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def observation(i, volume="0.1", raw_hash="a"*64):
    prices=[("10","13","9","12"),("12","14","11","13"),("13","15","10","11"),("11","12","8","9")][i%4]
    return dict(timestamp=i*3600,values=dict(zip(r.FIELDS,[*prices,volume])),source_ref=dict(raw_sha256=raw_hash,source_row=i+1))


def hours(count=24, volumes=None, catalog_hash="b"*64,cutover=24*r.HOUR):
    return [r.hourly_row(observation(i,(volumes or ["0.1","0.2","1.25","2.005"])[i%4]),r.INSTRUMENTS[0],catalog_hash,cutover) for i in range(count)]


class DataRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def archive(self,count=4):
        body="".join(f'{i*3600},0.10,12,13,9,10\n' for i in range(count)).encode()
        raw=gzip.compress(body,mtime=0)
        d=dict(start=0,end_exclusive=count*3600,rows=count,expanded_bytes=len(body),expanded_sha256=hashlib.sha256(body).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest())
        return raw,d

    def rest(self,count=4):
        rows=[dict(t=i*3600,o="10.0",h="13",l="9",c="12",v="0.10",sum="1.2") for i in range(count)]
        raw=json.dumps(rows).encode();d=dict(start=0,end_exclusive=count*3600,rows=count,raw_sha256=hashlib.sha256(raw).hexdigest())
        return raw,d,rows

    def fixture(self):
        """Two 48-hour assets, two archives each, one REST suffix, no public data."""
        v1=self.root/'qd004/history-v1';v2=self.root/'qd005/canonical-hourly-v2/normalized'
        v1.mkdir(parents=True);v2.mkdir(parents=True)
        files=[];archives=[];rests=[];receipts=[];diffs=[]
        def save(path,body,kind):
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(body)
            entry=dict(path=str(path),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),kind=kind)
            files.append(entry);return entry
        for inst in r.INSTRUMENTS:
            symbol=inst.split(":")[-1];old_rows=[]
            for day in range(2):
                expanded="".join(f'{i*3600},0.1,12,13,9,10\n' for i in range(day*24,(day+1)*24)).encode()
                body=gzip.compress(expanded,mtime=0);source_id=symbol+str(day)
                entry=save(v1/'raw'/f'{source_id}.bin',body,'hourly_archive')
                d=dict(instrument=symbol,source_id=source_id,path=entry['path'],raw_sha256=entry['sha256'],expanded_sha256=hashlib.sha256(expanded).hexdigest(),expanded_bytes=len(expanded),rows=24,start=day*86400,end_exclusive=(day+1)*86400,url='https://public.invalid/'+source_id,retrieved_at_utc='2026-10-28T00:00:00Z')
                archives.append(d)
                receipts.append(dict(source_id=source_id,sha256=entry['sha256'],accepted=True,complete_object=True,kind='candles',interval_seconds=3600,symbol=symbol,url=d['url'],retrieved_at=d['retrieved_at_utc']))
                for j in range(24):
                    i=day*24+j;old_rows.append(f'{i*3600},10,13,9,12,0.1,{(i+1)*3600},{source_id},{j+1}\n')
            v2_entry=save(v2/f'{symbol}-3600s.csv',('timestamp,open,high,low,close,volume,available_at,source_id,source_row\n'+''.join(old_rows)).encode(),'v2_normalized')
            rawrows=[dict(t=i*3600,o='10',h='13',l='9',c='12',v='0.2' if i==24 else '0.1',sum='0') for i in range(24,48)]
            if symbol=='BTC_USDT':rawrows[0]['c']='11'
            rest_dir=self.root/'rest'/symbol;body=json.dumps(rawrows).encode();entry=save(rest_dir/'bulk.json',body,'decimal_hourly_raw')
            d=dict(instrument=symbol,kind='bulk',request_id=symbol,path=entry['path'],raw_sha256=entry['sha256'],rows=24,start=86400,end_exclusive=172800,request_url='https://public.invalid/'+symbol,received_at_utc='2026-10-28T00:00:00Z')
            rests.append(d)
            receipt=dict(request_id=symbol,sha256=entry['sha256'],http_status=200,curl_exit=0,error='',request_headers={'X-Gate-Size-Decimal':'1'},url=d['request_url'],received_at=d['received_at_utc'])
            save(rest_dir/'result.json',json.dumps(dict(attempts=[receipt])).encode(),'evidence')
            old=archives[-1]
            fields=dict(volume=dict(archive='0.1',rest='0.2',rest_minus_archive='0.1'))
            if symbol=='BTC_USDT':fields['close']=dict(archive='12',rest='11',rest_minus_archive='-1')
            diffs.append(dict(instrument=symbol,timestamp=86400,utc='1970-01-02T00:00:00Z',archive_ref=[old['source_id'],1,old['raw_sha256']],rest_ref=[entry['path'],1,entry['sha256']],v2_ref=[v2_entry['path'],25,v2_entry['sha256']],fields=fields))
        save(v1/'manifest.json',json.dumps(dict(raw_files=receipts)).encode(),'evidence')
        spec=dict(scope=dict(start_us=0,end_exclusive_us=48*r.HOUR,expected_rows_per_instrument={'3600':48,'14400':12,'86400':2}),source_policy=dict(cutover_us=24*r.HOUR),independent_audit=dict(files=files,archive_objects=archives,rest_objects=rests,differences=diffs))
        return spec

    def test_exact_decimals_huge_scale_and_true_zero(self):
        literals=['0','0.00','5623243.7','9007199254740993.1','123456789012345678901234567890123456789.12345678901234567890123456789']
        with localcontext() as ctx:
            ctx.prec=2;ctx.traps[Inexact]=ctx.traps[Rounded]=True
            for text in literals:self.assertEqual(r.fixed(r.decimal(text)),text.rstrip('0').rstrip('.') if '.' in text else text)
            self.assertEqual(r.fixed(r.decimal('0.1')+r.decimal('0.2')),'0.3')
        self.assertEqual(r.fixed(Fraction('-0.7')),'-0.7')
        with self.assertRaises(r.RepairError):r.fixed(Fraction(1,3))

    def test_invalid_decimal_types_grammar_limits(self):
        for x in (None,True,False,1,1.2,'',' 1','1 ','01','+1','-0','-1','1e2','.1','NaN','Infinity','1.','0.'+'1'*65,'1'*129):
            with self.subTest(x=x),self.assertRaises(r.RepairError):r.decimal(x)
        for x in ('0.0','1.00','01','-0'):
            with self.assertRaises(r.RepairError):r.decimal(x,normalized=True)
        self.assertEqual(r.decimal('0'),0)
        with self.assertRaises(r.RepairError):r.decimal(None)

    def test_strict_json_duplicate_and_float_rejection(self):
        for text in (b'{"v":"1","v":"2"}',b'{"v":1.2}',b'{"v":NaN}'):
            with self.assertRaises(r.RepairError):r.strict_json(text)

    def test_archive_physical_rows_and_domains(self):
        raw,d=self.archive();out=r.parse_archive(raw,d)
        self.assertEqual([o['source_ref']['source_row'] for o in out],[1,2,3,4])
        self.assertEqual(out[0]['values'],dict(open='10',high='13',low='9',close='12',volume='0.1'))
        for bad in (raw[:-5],raw+raw):
            with self.assertRaises(r.RepairError):r.parse_archive(bad,d)
        d['expanded_sha256']='f'*64
        with self.assertRaises(r.RepairError):r.parse_archive(raw,d)

    def test_archive_rejects_missing_duplicate_reversed_offgrid(self):
        for times in ([0,3600,3600,10800],[10800,7200,3600,0],[0,3600,7201,10800],[0,3600,10800]):
            expanded=''.join(f'{t},1,12,13,9,10\n' for t in times).encode();raw=gzip.compress(expanded,mtime=0)
            d=dict(start=0,end_exclusive=14400,rows=4,expanded_bytes=len(expanded),expanded_sha256=r.sha(expanded),raw_sha256=r.sha(raw))
            with self.assertRaises(r.RepairError):r.parse_archive(raw,d)

    def test_rest_requires_strings_and_never_sum_fallback(self):
        raw,d,rows=self.rest();out=r.parse_rest(raw,d)
        self.assertEqual(out[0]['values']['volume'],'0.1')
        for key,value in [('v',None),('v',1),('v',True),('v',0.1),('sum','-1'),('t',False),('o','0')]:
            bad=deepcopy(rows);bad[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(r.RepairError):r.parse_rest(json.dumps(bad).encode(),d)
        for key in ('v','sum'):
            bad=deepcopy(rows);bad[0].pop(key)
            with self.assertRaises(r.RepairError):r.parse_rest(json.dumps(bad).encode(),d)
        bad=deepcopy(rows);bad[0]['extra']='1'
        with self.assertRaises(r.RepairError):r.parse_rest(json.dumps(bad).encode(),d)

    def test_rest_grid_order_and_true_zero(self):
        _,d,rows=self.rest()
        for bad in (rows[::-1],rows[:-1],[rows[0],rows[0],*rows[2:]]):
            with self.assertRaises(r.RepairError):r.parse_rest(json.dumps(bad).encode(),d)
        rows[0]['v']='0';self.assertEqual(r.parse_rest(json.dumps(rows).encode(),d)[0]['values']['volume'],'0')

    def test_closed_row_schema_types_clocks_and_hashes(self):
        row=hours(4)[0];self.assertIs(r.validate_row(row),row)
        for field,value in [('schema_version',True),('bar_open_us',False),('interval_seconds',3600.0),('open','0'),('volume_contracts',None),('volume_contracts','0.10'),('observed_first_available_at_us',0),('null_reasons',{}),('parent_rows',[{}]),('source_segment','other'),('bar_close_us',r.HOUR-1),('extra',1)]:
            bad=deepcopy(row);bad[field]=value
            if field!='extra':r.seal(bad)
            with self.subTest(field=field),self.assertRaises(r.RepairError):r.validate_row(bad)
        bad=deepcopy(row);bad['close']='11'
        with self.assertRaises(r.RepairError):r.validate_row(bad)

    def test_row_id_and_content_preimages_independent(self):
        row=hours(4)[0]
        self.assertEqual(row['row_id'],wire_hash([r.NS,1,r.DATASET,'b'*64,r.POLICY,r.AGG,r.INSTRUMENTS[0],3600,0]))
        self.assertEqual(row['content_sha256'],wire_hash({k:v for k,v in row.items() if k!='content_sha256'}))

    def test_literal_4h_day_nested_full_period_sums(self):
        one=hours();four=r.aggregate_rows(one,14400);daily=r.aggregate_rows(one,86400)
        self.assertEqual([four[0][k] for k in ('open','high','low','close','volume_contracts')],['10','15','8','9','3.555'])
        self.assertEqual(daily[0]['volume_contracts'],'21.33')
        self.assertEqual(r.combine(four),r.combine(one))
        self.assertEqual(daily[0]['source_refs'],[x['source_refs'][0] for x in one])
        self.assertEqual(daily[0]['parent_rows'],[dict(row_id=x['row_id'],content_sha256=x['content_sha256']) for x in one])
        self.assertEqual(four[0]['research_available_at_us'],4*r.HOUR)

    def test_sum_exceeds28_digits_and_128_output_boundary(self):
        huge='9'*128
        one=hours(4,[huge]*4)
        with localcontext() as ctx:
            ctx.prec=2;ctx.traps[Inexact]=ctx.traps[Rounded]=True
            out=r.aggregate_rows(one,14400)[0];r.validate_row(out)
        self.assertEqual(out['volume_contracts'],'3'+'9'*127+'6')
        self.assertEqual(r.aggregate_rows(hours(4,['9007199254740993.1']*4),14400)[0]['volume_contracts'],'36028797018963972.4')

    def test_aggregate_rejects_parents_grid_and_segment_mixing(self):
        base=hours(8)
        variants=[base[:-1],base[::-1],[base[0],base[0],*base[2:]]]
        bad=deepcopy(base);bad[1]['bar_open_us']+=1;r.seal(bad[1]);variants.append(bad)
        bad=deepcopy(base);bad[1]['source_segment']='DECIMAL_REST_SUFFIX';r.seal(bad[1]);variants.append(bad)
        for group in variants:
            with self.assertRaises(r.RepairError):r.aggregate_rows(group,14400)

    def test_aligned_source_transition_and_cutoff_availability(self):
        one=hours(48,cutover=24*r.HOUR);daily=r.aggregate_rows(one,86400)
        self.assertEqual([x['source_segment'] for x in daily],['ARCHIVE_PREFIX','DECIMAL_REST_SUFFIX'])
        self.assertEqual(len(r.economic_projection(daily,48*r.HOUR-1,48*r.HOUR)),1)
        self.assertEqual(len(r.economic_projection(daily,24*r.HOUR,48*r.HOUR)),1)
        self.assertEqual(len(r.economic_projection(daily,24*r.HOUR-1,48*r.HOUR)),0)
        self.assertEqual(daily[-1]['bar_close_us'],48*r.HOUR)
        with self.assertRaises(r.RepairError):r.economic_projection(daily,48*r.HOUR,48*r.HOUR)

    def test_future_raw_and_full_catalog_rehash_only_changes_audit_past(self):
        raw,d,rows=self.rest(8)
        past_catalog=dict(raw_hash=r.sha(raw),future_inventory=['declared'])
        first=[r.hourly_row(o,r.INSTRUMENTS[0],wire_hash(past_catalog),0) for o in r.parse_rest(raw,d)]
        rows[-1]['v']='99.123';new_raw=json.dumps(rows).encode();new_d=dict(d,raw_sha256=r.sha(new_raw))
        new_catalog=dict(raw_hash=r.sha(new_raw),future_inventory=['declared'])
        second=[r.hourly_row(o,r.INSTRUMENTS[0],wire_hash(new_catalog),0) for o in r.parse_rest(new_raw,new_d)]
        a,b=r.aggregate_rows(first,14400),r.aggregate_rows(second,14400)
        self.assertNotEqual(a[0],b[0]);self.assertNotEqual(a[0]['source_refs'],b[0]['source_refs'])
        self.assertEqual(r.economic_projection(a,4*r.HOUR,8*r.HOUR),r.economic_projection(b,4*r.HOUR,8*r.HOUR))
        self.assertNotEqual(a[1]['volume_contracts'],b[1]['volume_contracts'])
        self.assertEqual(set(r.economic_projection(a,4*r.HOUR,8*r.HOUR)[0]),set(r.ECONOMIC))

    def test_synthetic_source_catalog_selection_and_complete_differences(self):
        spec=self.fixture();catalog,selected,diffs=r.load_observations(spec,{},r.Budget())
        self.assertEqual(len(catalog['sources']),6)
        self.assertEqual(len(diffs),2)
        for inst in r.INSTRUMENTS:
            self.assertEqual(len(selected[inst]),48)
            self.assertEqual(selected[inst][24]['values']['volume'],'0.2')
        self.assertEqual(selected[r.INSTRUMENTS[0]][24]['values']['close'],'11')
        for d in diffs:
            self.assertEqual(set(d['archive_ohlcv']),set(r.FIELDS));self.assertEqual(set(d['rest_ohlcv']),set(r.FIELDS))
            self.assertEqual(d['fields']['volume'],dict(archive='0.1',rest='0.2',rest_minus_archive='0.1'))
            if d['instrument']=='BTC_USDT':self.assertEqual(d['fields']['close'],dict(archive='12',rest='11',rest_minus_archive='-1'))

    def test_frozen_input_hash_and_rehashed_semantic_corruption(self):
        spec=self.fixture();file=spec['independent_audit']['files'][0];path=Path(file['path'])
        path.write_bytes(path.read_bytes()+b'x')
        with self.assertRaises(r.RepairError):r.load_observations(spec,{},r.Budget())
        # Restore a valid raw body under a valid new hash, but change required grid.
        body=gzip.compress(b'3600,0.1,12,13,9,10\n'*24,mtime=0);path.write_bytes(body)
        file.update(bytes=len(body),sha256=r.sha(body))
        desc=spec['independent_audit']['archive_objects'][0]
        desc.update(raw_sha256=r.sha(body),expanded_bytes=len(b'3600,0.1,12,13,9,10\n'*24),expanded_sha256=r.sha(b'3600,0.1,12,13,9,10\n'*24))
        v1_entry=next(e for e in spec['independent_audit']['files'] if e['path'].endswith('qd004/history-v1/manifest.json'))
        v1=json.loads(Path(v1_entry['path']).read_bytes())
        next(x for x in v1['raw_files'] if x['source_id']==desc['source_id'])['sha256']=r.sha(body)
        changed=json.dumps(v1).encode();Path(v1_entry['path']).write_bytes(changed);v1_entry.update(bytes=len(changed),sha256=r.sha(changed))
        with self.assertRaisesRegex(r.RepairError,'archive grid/order'):r.load_observations(spec,{},r.Budget())

    def test_two_synthetic_derivations_byte_equal_and_no_float_transport(self):
        spec=self.fixture();catalog,obs,diffs=r.load_observations(spec,{},r.Budget())
        scope=dict(spec['scope'],cutover_us=24*r.HOUR)
        a,_,checks=r.derive(catalog,obs,diffs,scope,r.Budget());b,_,_=r.derive(catalog,obs,diffs,scope,r.Budget())
        self.assertEqual(a,b);self.assertEqual(checks['different_fields'],3)
        self.assertEqual(checks['independent_candidate_validation'],'NOT_EXECUTED')
        self.assertIsNone(checks['independent_checker_commit'])
        self.assertEqual(sum(checks['row_counts'].values()),124)

    def test_policy_requires_exact_companion_binding(self):
        scope=dict(instruments=list(r.INSTRUMENTS));segments=[dict(range=[0,1],source='fixture')]
        spec=dict(scope=scope,source_policy=dict(id=r.POLICY,selection=segments,record_rule='whole row'),ohlcv_contract=dict(namespace=r.NS,row_fields={k:'' for k in r.ROW_FIELDS}))
        approval=dict(status='APPROVED',decision_id='QR008-DATA-SOURCE-1',policy_id=r.POLICY,spec_commit=r.SPEC_COMMIT,spec_sha256='placeholder',scope=scope,approved_source_segments=segments,approved_rule='whole row')
        sp=self.root/'spec.json';ap=self.root/'approval.json';sp.write_bytes(r.canonical(spec))
        approval['spec_sha256']=r.sha(sp.read_bytes());ap.write_bytes(r.canonical(approval))
        with patch.object(r,'SPEC_SHA',r.sha(sp.read_bytes())),patch.object(r,'APPROVAL_SHA',r.sha(ap.read_bytes())):
            self.assertEqual(r.load_policy(sp,ap),(spec,approval))
        approval['status']='PROPOSED';ap.write_bytes(r.canonical(approval))
        with patch.object(r,'SPEC_SHA',r.sha(sp.read_bytes())),patch.object(r,'APPROVAL_SHA',r.sha(ap.read_bytes())):
            with self.assertRaises(r.RepairError):r.load_policy(sp,ap)

    def test_publish_atomic_inventory_and_existing_destination(self):
        target=self.root/'published';payloads={'input-catalog.json':b'{}\n','candles/test.jsonl':b''}
        result=r.publish(target,payloads,dict(status='ACCEPTED'),r.Budget())
        self.assertEqual(result['status'],'PENDING_INDEPENDENT_REVIEW')
        r.verify_tree(target,payloads,result['manifest'],r.Budget())
        self.assertEqual(result['bytes'],sum(p.stat().st_size for p in target.rglob('*') if p.is_file()))
        with self.assertRaises(r.RepairError):r.publish(target,payloads,{},r.Budget())
        self.assertTrue((self.root/'.publication.lock').is_file())

    def test_manifest_last_and_failed_write_keeps_unpublished_stage(self):
        calls=[];original=r._write_new
        def record(path,body):calls.append(path.name);original(path,body)
        with patch.object(r,'_write_new',side_effect=record):r.publish(self.root/'ok',{'a.json':b'{}\n'},{},r.Budget())
        self.assertEqual(calls[-1],'manifest.json')
        with patch.object(r,'_write_new',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):r.publish(self.root/'bad',{'a.json':b'{}\n'},{},r.Budget())
        self.assertFalse((self.root/'bad').exists());self.assertEqual(len(list(self.root.glob('.bad.staging-*'))),1)

    def test_budget_time_bytes_and_input_change_fail_before_publish(self):
        for budget in (r.Budget(seconds=-1),r.Budget(maximum=1)):
            with self.assertRaises(r.RepairError):r.publish(self.root/'bad',{'a.json':b'{}\n'},{},budget)
            self.assertFalse((self.root/'bad').exists())
        def changed():raise r.RepairError('fixture frozen input changed')
        with self.assertRaises(r.RepairError):r.publish(self.root/'changed',{'a.json':b'{}\n'},{},r.Budget(),changed)
        self.assertFalse((self.root/'changed').exists())

    def test_two_concurrent_publishers_exactly_one_wins(self):
        target=self.root/'race';barrier=threading.Barrier(2);results=[]
        def writer():
            try:results.append(r.publish(target,{'a.json':b'{}\n'},{},r.Budget(),barrier.wait)['status'])
            except r.RepairError:results.append('REJECTED')
        threads=[threading.Thread(target=writer) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertCountEqual(results,['PENDING_INDEPENDENT_REVIEW','REJECTED'])

    def test_kernel_no_replace_rejects_noncooperating_empty_root(self):
        source=self.root/'source';target=self.root/'target';source.mkdir();target.mkdir()
        with self.assertRaises(r.RepairError):r._rename_exclusive(source,target)
        self.assertTrue(source.is_dir());self.assertTrue(target.is_dir())

    def test_crash_before_publication_retains_stage_and_restarts_fresh(self):
        code="from pathlib import Path; import os; from research.qd008 import repair_history as r; r.publish(Path(%r),{'a.json':b'{}\\n'},{},r.Budget(),lambda:os._exit(7))" % str(self.root/'crashed')
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,7,result.stderr)
        self.assertFalse((self.root/'crashed').exists());self.assertEqual(len(list(self.root.glob('.crashed.staging-*'))),1)
        r.publish(self.root/'fresh',{'a.json':b'{}\n'},{},r.Budget())
        self.assertTrue((self.root/'fresh/manifest.json').exists())

    def test_rehashed_output_and_lineage_corruption_fails_recomputation(self):
        rows=hours(4);expected={'candles/test.jsonl':r.jsonl(rows)}
        result=r.publish(self.root/'out',expected,{},r.Budget())
        for variant in ('source','value'):
            row=deepcopy(rows[0])
            if variant=='source':row['source_refs'][0]['source_row']=99
            else:row['close']='11'
            r.seal(row);r.validate_row(row)
            modified=r.jsonl([row,*rows[1:]])
            (self.root/'out/candles/test.jsonl').write_bytes(modified)
            manifest=deepcopy(result['manifest']);manifest['files'][0].update(sha256=r.sha(modified),bytes=len(modified))
            (self.root/'out/manifest.json').write_bytes(r.canonical(manifest)+b'\n')
            with self.assertRaises(r.RepairError):r.verify_tree(self.root/'out',expected,manifest,r.Budget())

    def test_path_escape_symlink_extra_inventory_rejected(self):
        for path in ('../escape.json','/absolute.json','./alias.json','.'):
            with self.assertRaises(r.RepairError):r.publish(self.root/'out',{path:b'{}\n'},{},r.Budget())
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(r.RepairError):r.publish(link/'out',{'a.json':b'{}\n'},{},r.Budget())
        result=r.publish(self.root/'ok',{'a.json':b'{}\n'},{},r.Budget());(self.root/'ok/extra').mkdir()
        with self.assertRaises(r.RepairError):r.verify_tree(self.root/'ok',{'a.json':b'{}\n'},result['manifest'],r.Budget())


if __name__=='__main__':unittest.main()
