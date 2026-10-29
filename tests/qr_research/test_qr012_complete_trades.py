"""QR012 new parser/transport risks only; all network is synthetic."""
import gzip
import io
import json
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.qr012 import complete_trades_pilot as c


class Response(io.BytesIO):
    def __init__(self,body,headers,code=206):
        super().__init__(body);self.headers=headers;self.code=code


class Opener:
    def __init__(self,response):self.response=response
    def open(self,request,timeout):return self.response


class CompleteTradesTests(unittest.TestCase):
    def test_exact_decimal_and_invalid_fields(self):
        ts,ident,price,size=c.parse_row('1788220800.123456,900,2466.470000,-0.10000000000000001')
        self.assertEqual(ts,D('1788220800.123456'));self.assertEqual(size,D('-0.10000000000000001'))
        for text in ['1,2,NaN,1','1,2,3,0','1,-1,3,1','1,2,3','1,2,-3,1','1,2,3,Infinity']:
            with self.assertRaises(c.p.ProbeError):c.parse_row(text)

    def test_unknown_side_never_becomes_pressure(self):
        fields=c.direction_fields(c.AGGRESSOR_STATUS)
        self.assertTrue(all(fields[k] is None for k in ['buy_contracts','sell_contracts','signed_flow_contracts','trade_pressure']))
        with self.assertRaises(c.p.ProbeError):c.direction_fields('INFER_FROM_PRICE_MOVE')

    def test_range_response_requires_exact_version_and_status(self):
        item={'kind':'tail','range':[4,11]};asset={'expected_size':12,'expected_etag':'"x"','expected_s3_version':'v'}
        h={'content-length':'8','content-range':'bytes 4-11/12','etag':'"x"','x-amz-version-id':'v'}
        c.validate_headers(item,asset,206,h)
        for status,header in [(200,h),(206,{**h,'etag':'W/"x"'}),(206,{**h,'x-amz-version-id':'other'}),(206,{**h,'content-range':'bytes 0-7/12'})]:
            with self.assertRaises(c.p.ProbeError):c.validate_headers(item,asset,status,header)

    def test_tail_assembly_and_unexpected_full_body_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prefix=root/'prefix';prefix.write_bytes(b'abcd')
            c.p.write_new(root/'request-plan.json',{'synthetic':True})
            asset={**c.build_plan()['assets'][0],'prefix_path':str(prefix),'prefix_bytes':4,'prefix_sha256':c.file_sha(prefix),
                   'expected_size':12,'expected_etag':'"x"','expected_s3_version':'v'}
            item={'id':'tail-fixture','kind':'tail','range':[4,11],'max_body_bytes':8}
            h={'content-length':'8','content-range':'bytes 4-11/12','etag':'"x"','x-amz-version-id':'v'}
            result=c.fetch(item,asset,root,Opener(Response(b'efghijkl',h)))
            self.assertTrue(result['complete_transport']);self.assertEqual(result['body_bytes'],8)
            self.assertEqual((root/result['raw_path']).read_bytes(),b'abcdefghijkl')
            result=c.fetch({**item,'id':'ignored-range'},asset,root,Opener(Response(b'abcdefghijkl',{'content-length':'12'},200)))
            self.assertFalse(result['complete_transport']);self.assertEqual(result['body_bytes'],0)

    def run_fixture(self,rows,corrupt=False):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        raw=gzip.compress(('\n'.join(rows)+'\n').encode())
        if corrupt:raw=raw[:-4]
        (root/'full').write_bytes(raw)
        receipt=dict(complete_transport=True,request={'kind':'full'},raw_path='full',stored_sha256=c.file_sha(root/'full'))
        with patch.object(c,'END',c.START+120):result=c.analyze(receipt,'BTC_USDT',root/'out',root)
        minutes=[json.loads(line) for line in (root/'out/minutes.jsonl').read_text().splitlines()]
        return result,minutes

    def test_exact_duplicates_and_conflicts_are_explicit(self):
        t=c.START
        result,minutes=self.run_fixture([f'{t}.1,1,100,0.1',f'{t}.1,1,100,0.1',f'{t}.2,2,100,2',f'{t}.2,2,100,-2'])
        self.assertEqual(result['counts']['identical_duplicate_rows_excluded'],1)
        self.assertEqual(result['counts']['conflicting_rows_excluded'],2)
        self.assertEqual(minutes[0]['observed_count'],4)
        self.assertEqual(minutes[0]['deduplicated_valid_count'],1)
        self.assertEqual(minutes[0]['deduplicated_total_contracts'],'0.1')
        self.assertFalse(minutes[0]['retrospective_structural_mask'])

    def test_boundary_and_empty_minute_do_not_claim_no_trading(self):
        t=c.START
        result,minutes=self.run_fixture([f'{t},1,100,0.1',f'{t+120},2,100,0.2'])
        self.assertEqual(result['counts']['out_of_month_rows'],1)
        self.assertEqual(minutes[0]['observed_count'],1)
        self.assertIn('NO_OBSERVED_TRADES_NOT_PROVEN_NO_TRADING',minutes[1]['quality_reasons'])
        self.assertIsNone(minutes[0]['historical_available_at']);self.assertFalse(minutes[0]['decision_eligible'])

    def test_truncated_gzip_cannot_pass_full_source_mask(self):
        result,minutes=self.run_fixture([f'{c.START},1,100,1'],True)
        self.assertFalse(result['complete_transport_and_gzip'])
        self.assertTrue(all(not x['retrospective_structural_mask'] for x in minutes))
        self.assertIn('TRUNCATED_GZIP',result['error'])

    def test_partial_transport_is_rejected_before_analysis(self):
        with self.assertRaisesRegex(c.p.ProbeError,'PARTIAL_TRANSPORT'):
            c.analyze({'complete_transport':False},'BTC_USDT',Path('/unused'))


if __name__=='__main__':unittest.main()
