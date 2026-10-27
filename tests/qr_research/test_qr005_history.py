"""Adversarial offline contracts; synthetic data, no downloads or model fits."""
import copy
import csv
from decimal import Decimal, localcontext
import json
from pathlib import Path
import tempfile
import unittest

from research.qr005.validate_history import (
    check_derived, decimal_text, funding_diagnostics, inspect_candidate,
    reference_buckets, sha256, verify_base, verify_hours,
)
from research.qr004.validate_history import inside


class CanonicalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.top = Path(self.tmp.name)
        self.base, self.root = self.top/"base", self.top/"candidate"
        for root in (self.base, self.root):
            (root/"normalized").mkdir(parents=True)
            (root/"lineage").mkdir()
        self.spec = json.loads((Path(__file__).resolve().parents[2]/"research/qr005/data-acceptance.json").read_text())
        self.start = self.spec["calendar"]["raw_start"]
        self.end = self.start+33*3600
        self.spec["calendar"]["raw_end_exclusive"] = self.end
        self.base_manifest = {"dataset_id": "synthetic-base", "normalized_files": []}
        self.manifest = dict(schema_version=2, protocol_id=self.spec["protocol_id"],
            dataset_id="synthetic-v2", created_at="2026-10-28T00:00:00Z", spec_sha256="synthetic-spec",
            base_manifest_sha256=self.spec["base"]["manifest_sha256"], symbols=self.spec["scope"]["symbols"],
            data_range={"start":self.start,"end_exclusive":self.end}, files=[], withheld_buckets=[],
            network_attempts=0, model_fits=0, limitations=["synthetic test, no historical truth"])
        patterns = [(10,13,9,12,1),(12,14,11,13,2),(13,15,10,11,3),(11,12,8,9,4)]
        for symbol in self.spec["scope"]["symbols"]:
            hours = []
            for i in range(33):
                t=self.start+i*3600
                row=dict(zip(["open","high","low","close","volume"],patterns[i%4]))
                hours.append(dict(timestamp=t, **row, available_at=t+3600, source_id="synthetic",source_row=i+1))
            funding = [dict(timestamp=self.start+8*3600*i+offset,funding_rate="0.0001",
                available_at=self.start+8*3600*i+offset,source_id="synthetic-funding",source_row=i+1)
                for i,offset in enumerate([0,1,2,1,0])]
            for kind,seconds,rows in (("candles",3600,hours),("funding",0,funding)):
                prefix="funding" if kind=="funding" else "candle"
                path=f"normalized/{symbol}-{str(seconds)+'s' if seconds else 'funding'}.csv"
                columns=self.spec["normalization"][prefix+"_columns"]
                self.write_csv(self.base/path,columns,rows)
                (self.root/path).write_bytes((self.base/path).read_bytes())
                entry=self.entry(symbol,kind,seconds,path,columns,rows)
                parent=dict(entry);parent.pop("derivation",None)
                self.base_manifest["normalized_files"].append(parent)
                entry["derivation"]=dict(method="copy_frozen_bytes",parent_path=path,parent_sha256=entry["sha256"])
                self.manifest["files"].append(entry)
            parent_path=f"normalized/{symbol}-3600s.csv"
            for seconds in (14400,86400):
                n=seconds//3600
                # Hard-coded expected numeric example; never call QR reference
                # aggregation to construct the acceptance fixture.
                rows=[dict(timestamp=t,open=10,high=15,low=8,close=9,volume=10*n//4,available_at=t+seconds)
                      for t in range(self.start,self.end-seconds+1,seconds)]
                path=f"normalized/{symbol}-{seconds}s.csv"
                columns=self.spec["derived_columns"]
                self.write_csv(self.root/path,columns,rows)
                native=[dict(r,source_id="synthetic-native",source_row=i) for i,r in enumerate(rows,1)]
                self.write_csv(self.base/path,self.spec["normalization"]["candle_columns"],native)
                self.base_manifest["normalized_files"].append(dict(symbol=symbol,kind="candles",interval_seconds=seconds,
                    path=path,columns=self.spec["normalization"]["candle_columns"],sha256=sha256(self.base/path)))
                lineage=[dict(normalized_row=i+1,timestamp=r["timestamp"],parent_rows=list(range(i*n+1,(i+1)*n+1))) for i,r in enumerate(rows)]
                lp=f"lineage/{symbol}-{seconds}s.jsonl"
                (self.root/lp).write_text(''.join(json.dumps(r)+'\n' for r in lineage))
                entry=self.entry(symbol,"candles",seconds,path,columns,rows)
                entry["derivation"]=dict(method="utc_ohlcv_from_frozen_hourly",parent_path=parent_path,
                    parent_sha256=sha256(self.base/parent_path),lineage_path=lp,lineage_sha256=sha256(self.root/lp),lineage_rows=len(rows))
                self.manifest["files"].append(entry)
                tail_start=self.end//seconds*seconds
                self.manifest["withheld_buckets"].append(dict(symbol=symbol,interval_seconds=seconds,timestamp=tail_start,
                    end_exclusive=tail_start+seconds,available_parent_rows=list(range((tail_start-self.start)//3600+1,34)),
                    unavailable_hours=(tail_start+seconds-self.end)//3600,reason="cutoff_before_bucket_close"))

    def write_csv(self,path,columns,rows):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n')
            writer.writeheader();writer.writerows(rows)

    def entry(self,symbol,kind,seconds,path,columns,rows):
        return dict(symbol=symbol,kind=kind,interval_seconds=seconds,path=path,sha256=sha256(self.root/path),
            rows=len(rows),columns=columns,units=({'timestamp':'UTC_unix_seconds','funding_rate':'fraction_per_settlement'}
            if kind=='funding' else {'timestamp':'UTC_unix_seconds','price':'USDT_per_base','volume':'contracts'}),
            availability_basis=self.spec['normalization'][('funding' if kind=='funding' else 'candle')+'_available_at'])

    def audit(self):
        (self.root/'manifest.json').write_text(json.dumps(self.manifest))
        return inspect_candidate(self.root,self.base,self.spec,'synthetic-spec',self.base_manifest)

    def item(self,seconds=14400):
        return next(x for x in self.manifest['files'] if x['symbol']=='BTC_USDT' and x['interval_seconds']==seconds)

    def rows(self,item,root=None):
        with ((root or self.root)/item['path']).open(newline='') as f:return list(csv.DictReader(f))

    def rewrite(self,item,rows):
        self.write_csv(self.root/item['path'],item['columns'],rows)
        item.update(sha256=sha256(self.root/item['path']),rows=len(rows))

    def test_known_ohlcv_example_and_all_lineage(self):
        r=self.audit()
        self.assertEqual(r['exact_child_lineage_rows'],18)
        self.assertEqual(set(r['preserved_native_disagreement_counts'].values()),{0})
        self.assertEqual(r['funding']['BTC_USDT']['offset_seconds_counts'],{0:2,1:2,2:1})
        self.assertFalse(r['funding']['BTC_USDT']['authoritative_historical_schedule_proven'])
        self.assertEqual(self.rows(self.item())[0]['volume'],'10')

    def test_rehashed_price_volume_and_available_time_corruption_rejected(self):
        item=self.item();original=self.rows(item)
        for field,new in [('close','10'),('volume','11'),('available_at',str(self.start+14400-1))]:
            with self.subTest(field=field):
                changed=copy.deepcopy(original);changed[0][field]=new;self.rewrite(item,changed)
                with self.assertRaisesRegex(ValueError,'derived '+field+' mismatch'):self.audit()
        self.rewrite(item,original)

    def test_rehashed_lineage_reordering_rejected(self):
        d=self.item()['derivation'];p=self.root/d['lineage_path']
        rows=[json.loads(x) for x in p.read_text().splitlines()];rows[0]['parent_rows']=[2,1,3,4]
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows));d['lineage_sha256']=sha256(p)
        with self.assertRaisesRegex(ValueError,'lineage child identity'):self.audit()

    def test_funding_rounding_even_with_rehashed_descriptor_rejected(self):
        item=self.item(0);rows=self.rows(item);rows[1]['timestamp']=str(self.start+8*3600)
        rows[1]['available_at']=rows[1]['timestamp'];self.rewrite(item,rows)
        with self.assertRaisesRegex(ValueError,'copied input differs'):self.audit()

    def test_hourly_source_replacement_rejected(self):
        item=self.item(3600);rows=self.rows(item);rows[0]['volume']='999';self.rewrite(item,rows)
        with self.assertRaisesRegex(ValueError,'copied input differs'):self.audit()

    def test_missing_coarse_row_and_partial_tail_injection_rejected(self):
        item=self.item();rows=self.rows(item);self.rewrite(item,rows[:-1])
        with self.assertRaisesRegex(ValueError,'row count'):self.audit()
        self.rewrite(item,rows+[dict(rows[-1],timestamp=str(self.start+32*3600))])
        with self.assertRaisesRegex(ValueError,'row count'):self.audit()

    def test_tail_omission_and_unit_confusion_rejected(self):
        tail=self.manifest['withheld_buckets'].pop()
        with self.assertRaisesRegex(ValueError,'tail accounting'):self.audit()
        self.manifest['withheld_buckets'].append(tail)
        self.item()['units']['volume']='USDT'
        with self.assertRaisesRegex(ValueError,'units differ'):self.audit()

    def test_duplicate_or_other_symbol_inventory_rejected(self):
        self.manifest['files'].append(copy.deepcopy(self.item()))
        with self.assertRaisesRegex(ValueError,'file identity'):self.audit()
        self.manifest['files'][-1]['symbol']='SOL_USDT'
        with self.assertRaisesRegex(ValueError,'file identity'):self.audit()

    def test_path_traversal_and_symlink_escape_rejected(self):
        with self.assertRaises(ValueError):inside(self.root,'../base/manifest.json')
        outside=self.top/'outside';outside.write_text('outside')
        link=self.root/'normalized'/'escape';link.symlink_to(outside)
        with self.assertRaisesRegex(ValueError,'escapes'):inside(self.root,'normalized/escape')

    def test_hourly_gap_duplicate_nonfinite_and_fractional_contracts_rejected(self):
        rows=self.rows(self.item(3600),self.base)
        cases=[rows[:10]+rows[11:],rows[:10]+[rows[9]]+rows[10:]]
        for field,value in [('high','NaN'),('volume','0.5'),('low','20')]:
            edited=copy.deepcopy(rows);edited[3][field]=value;cases.append(edited)
        for case in cases:
            with self.assertRaises(ValueError):verify_hours(case,self.start,self.end)

    def test_future_perturbation_preserves_available_prefix(self):
        rows=self.rows(self.item(3600),self.base)
        old,_=reference_buckets(rows,14400,self.start,self.end)
        rows[20].update(open='20',high='30',low='19',close='29',volume='99')
        new,_=reference_buckets(rows,14400,self.start,self.end)
        cutoff=self.start+20*3600
        self.assertEqual([x for x in old if x['available_at']<=cutoff],
                         [x for x in new if x['available_at']<=cutoff])
        self.assertNotEqual(old[5],new[5])

    def test_close_boundary_is_inclusive_availability_not_open(self):
        expected,_=reference_buckets(self.rows(self.item(3600),self.base),14400,self.start,self.end)
        t=self.start+14400
        self.assertEqual(sum(r['available_at']<=t-1 for r in expected),0)
        self.assertEqual(sum(r['available_at']<=t for r in expected),1)

    def test_contract_sum_independent_of_ambient_decimal_precision(self):
        rows=self.rows(self.item(3600),self.base)
        value=123456789012345678901234567890
        for row in rows:row['volume']=str(value)
        with localcontext() as context:
            context.prec=3
            result,_=reference_buckets(rows,14400,self.start,self.end)
            self.assertEqual(result[0]['volume'],Decimal(value*4))

    def test_base_binding_rejects_before_parsing(self):
        (self.base/'manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'base manifest hash'):verify_base(self.base,self.spec,self.top)

    def test_decimal_encoding_and_no_funding_future_leak(self):
        self.assertEqual(decimal_text(Decimal('100.000')),'100')
        self.assertEqual(decimal_text(Decimal('0.0100')),'0.01')
        self.assertEqual(decimal_text(Decimal('-0.0')),'0')
        import pandas as pd
        from src.carry import align_funding_to_bars
        from src.backtest import _funding_rate_at
        t=self.start+28800
        frame=pd.DataFrame({'timestamp':[self.start,t+1],'funding_rate':[.01,-.02]})
        self.assertEqual(list(align_funding_to_bars(frame,[t,t+1])),[.01,-.02])
        data={'funding_ts':list(frame.timestamp),'funding_rates':frame.funding_rate.values,'funding_rate':0}
        self.assertEqual(_funding_rate_at(data,t),.01)
        self.assertEqual(_funding_rate_at(data,t+1),-.02)

    def test_data_validation_never_grants_training_or_acquisition(self):
        self.manifest['model_fits']=1
        with self.assertRaisesRegex(ValueError,'model_fits'):self.audit()
        self.manifest['model_fits']=0;self.manifest['network_attempts']=1
        with self.assertRaisesRegex(ValueError,'network_attempts'):self.audit()


if __name__=='__main__':
    unittest.main()
