"""Offline rejection and bounded-download tests, with synthetic byte streams."""
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from decimal import Decimal as D

from research.qr010 import historical_micro_probe as p


class Response(io.BytesIO):
    def __init__(self, body, code=200, headers=None):
        super().__init__(body)
        self.code = code
        self.headers = headers or {"Content-Length":str(len(body))}


class Opener:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def open(self, req, timeout):
        self.calls += 1
        return self.response


class MicroProbeTests(unittest.TestCase):
    def test_plan_scope(self):
        plan = p.build_plan()
        self.assertEqual(len(plan["requests"]), 40)
        self.assertEqual(len({r["id"] for r in plan["requests"]}), 40)
        self.assertTrue(all(p.allowed_url(r["url"]) for r in plan["requests"]))
        self.assertEqual(plan["reserved_amendments"]+40,48)
        self.assertFalse(p.allowed_url("https://api.gateio.ws/api/v4/futures/usdt/accounts"))
        self.assertFalse(p.allowed_url("https://x:y@download.gatedata.org/futures_usdt/trades/a"))
        self.assertFalse(p.allowed_url("https://hyperliquid-archive.s3.amazonaws.com/a?X-Amz-Signature=x"))

    def test_range_completeness(self):
        self.assertTrue(p.transport_complete(206,{"content-length":"10","content-range":"bytes 0-9/10"},10,None))
        self.assertFalse(p.transport_complete(206,{"content-length":"10","content-range":"bytes 0-9/100"},10,None))
        self.assertFalse(p.transport_complete(200,{"content-length":"100"},10,"BODY_CAP"))
        self.assertFalse(p.transport_complete(403,{"content-length":"10"},10,None))

    def test_ignored_range_is_capped_and_partial(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p.write_new(root/"request-plan.json",p.build_plan())
            item = dict(p.build_plan()["requests"][1],max_body_bytes=5)
            opener=Opener(Response(b"abcdefghij"))
            r=p.fetch_one(item,root,opener)
            self.assertEqual((root/r["raw_path"]).read_bytes(),b"abcde")
            self.assertEqual(r["body_bytes"],5)
            self.assertEqual(r["stopped"],"BODY_CAP")
            self.assertFalse(r["complete_transport"])
            with self.assertRaises(p.ProbeError):p.fetch_one(item,root,opener)
            self.assertEqual(opener.calls,1)

    def test_gzip_truncation_corruption_and_expansion_bound(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"object.bin"
            packed=gzip.compress(b"header\n"+b"x\n"*10000)
            f.write_bytes(packed)
            self.assertEqual(b"".join(p.gzip_chunks(f)),b"header\n"+b"x\n"*10000)
            with self.assertRaisesRegex(p.ProbeError,"DECOMPRESSED_CAP"):
                list(p.gzip_chunks(f,max_output=100))
            f.write_bytes(packed[:-4])
            with self.assertRaisesRegex(p.ProbeError,"TRUNCATED_GZIP"):
                list(p.gzip_chunks(f))
            f.write_bytes(packed+packed)
            with self.assertRaisesRegex(p.ProbeError,"TRAILING_OR_MULTIMEMBER"):
                list(p.gzip_chunks(f))

    def test_delta_side_span_and_fractional_quantity(self):
        b=p.LevelBook()
        b.apply('set',D('100'),D('2.5'),100,0)
        b.apply('set',D('101'),D('-3.6'),100,0)
        b.apply('take',D('101'),D('-0.5'),101,3)
        self.assertEqual(b.cursor,103)
        self.assertEqual(b.top('asks'),[(D('101'),D('3.1'))])
        b.apply('make',D('100'),D('1.1'),104,1)
        self.assertEqual(b.top('bids'),[(D('100'),D('3.6'))])
        with self.assertRaisesRegex(p.ProbeError,'SEQUENCE_GAP'):b.apply('make',D('100'),D(1),106,1)
        self.assertFalse(b.clean)

    def test_no_negative_repair_or_heap_duplicates(self):
        b=p.LevelBook();b.apply('set',D(100),D(2),1,0)
        b.apply('take',D(100),D(2),2,1)
        b.apply('make',D(100),D(3),3,1)
        self.assertEqual(b.top('bids'),[(D(100),D(3))])
        with self.assertRaisesRegex(p.ProbeError,'NEGATIVE_RECONSTRUCTED'):
            b.apply('take',D(100),D(4),4,1)

    def snapshot(self,at='100',ident=1):
        return {'id':ident,'current':D(at),'update':D(at),
                'bids':[(D(100-i),D(2)) for i in range(5)],
                'asks':[(D(101+i),D(3)) for i in range(5)]}

    def test_snapshot_features_no_gap_ofi_no_clock_invention(self):
        a=self.snapshot();b=self.snapshot('101',2)
        b['bids'][0]=(D(100),D(4))
        f=p.book_features(b,a)
        self.assertEqual(f['observed_ofi_contracts'],'2')
        self.assertIsNone(f['historical_available_at'])
        self.assertIsNone(p.book_features(self.snapshot('104',3),b)['observed_ofi_contracts'])
        b['asks'][0]=(D(101),D(0))
        with self.assertRaises(p.ProbeError):p.book_features(b)

    def test_snapshot_clock_cross_and_decimal_validation(self):
        text='{"id":1,"current":100.123456,"update":100.123455,"bids":[{"p":"100","s":1.2}],"asks":[{"p":"101","s":2.3}]}'
        s=p.parse_snapshot(text)
        self.assertEqual(s['current'],D('100.123456'))
        self.assertEqual(s['bids'][0][1],D('1.2'))
        with self.assertRaises(p.ProbeError):p.parse_snapshot(text.replace('"101"','"99"'))
        with self.assertRaises(p.ProbeError):p.decimal(float('nan'))
        with self.assertRaises(p.ProbeError):p.decimal('NaN')

    def test_trade_duplicate_conflict_masks_pressure(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'raw').mkdir()
            data=b'1672531200.1,1,100,1.5\n1672531200.1,1,100,1.5\n1672531200.1,1,100,-1.5\n1672531261,2,100,-1\n'
            raw=gzip.compress(data);(root/'raw/a').write_bytes(raw)
            r=dict(raw_path='raw/a',sha256=p.sha(raw),request=dict(id='R05',symbol='BTC_USDT',representative_utc='2023010100'))
            result=p.analyze_trades(r,root/'derived/v1/R05',root)
            self.assertEqual(result['counts']['duplicate_identical'],1)
            self.assertEqual(result['counts']['duplicate_conflict'],1)
            first=json.loads((root/result['feature_path']).read_text().splitlines()[0])
            self.assertIsNone(first['pressure_price_weighted_contract_ratio'])
            self.assertFalse(result['month_complete'])

    def test_truncated_last_line_is_not_a_trade(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a';f.write_bytes(gzip.compress(b'a\nb')[:-4]);audit={}
            import time
            self.assertEqual(list(p.gzip_lines(f,audit,time.monotonic()+10)),[(1,'a')])
            self.assertFalse(audit['gzip_complete'])
            self.assertEqual(audit['trailing_line_bytes'],1)

    def test_exact_delta_duplicate_is_noop_conflict_rejected_cache_bounded(self):
        c=p.DeltaDuplicates(capacity=2)
        self.assertIsNone(c.observe(100,'same',1))
        self.assertEqual(c.observe(100,'same',20),1)
        with self.assertRaisesRegex(p.ProbeError,'CONFLICTING'):c.observe(100,'different',21)
        c.observe(101,'b',22);c.observe(102,'c',23)
        self.assertEqual(len(c.rows),2)
        self.assertNotIn(100,c.rows)

    def test_archive_bridge_excludes_interior_and_mismatch_resets_ofi(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'raw').mkdir();t=1672531200
            rows=[f'{t},set,{100-i},2,100,0' for i in range(5)]
            rows += [f'{t},set,{101+i},-3,100,0' for i in range(5)]
            rows += [f'{t}.1,make,100,1,101,2',f'{t}.2,take,100,1,103,1',
                     f'{t}.3,make,100,1,104,1',f'{t}.2,take,100,1,103,1',
                     f'{t}.4,make,101,-1,105,1']
            snapshots=[]
            for ident,bid,ask,at in [(101,2,3,'.05'),(102,3,3,'.1'),
                                      (103,9,3,'.2'),(104,3,3,'.3'),(105,3,4,'.4')]:
                s={'id':ident,'current':str(t)+at,'update':str(t)+at,
                   'bids':[{'p':str(100-i),'s':bid if i==0 else 2} for i in range(5)],
                   'asks':[{'p':str(101+i),'s':ask if i==0 else 3} for i in range(5)]}
                snapshots.append(json.dumps(s))
            receipts=[]
            for ident,lines in [('R02',rows),('R03',snapshots)]:
                raw=gzip.compress(('\n'.join(lines)+'\n').encode())
                (root/'raw'/ident).write_bytes(raw)
                receipts.append(dict(raw_path='raw/'+ident,sha256=p.sha(raw),complete_transport=True,
                    request=dict(id=ident,symbol='BTC_USDT',representative_utc='2023010100')))
            result=p.analyze_pair(*receipts,root/'derived/v3/R02',root)
            self.assertEqual(result['counts']['snapshot_inside_merged_span'],1)
            self.assertEqual(result['counts']['snapshot_at_exact_merged_boundary'],4)
            self.assertEqual(result['counts']['exact_top10_matches'],3)
            self.assertEqual(result['counts']['duplicate_identical_delta_rows'],1)
            features=[json.loads(line) for line in (root/result['feature_path']).read_text().splitlines()]
            self.assertEqual([f['snapshot_id'] for f in features],[102,104,105])
            self.assertEqual([f['observed_ofi_contracts'] for f in features],[None,None,'-1'])
            self.assertTrue(all(f['historical_available_at'] is None for f in features))


if __name__ == "__main__":
    unittest.main()
