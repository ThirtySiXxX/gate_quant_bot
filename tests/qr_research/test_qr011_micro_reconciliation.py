"""Focused offline fixtures for QR011's falsification and interval semantics."""
import gzip
import json
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.qr011 import reconcile_microstructure as r


class ReconciliationTests(unittest.TestCase):
    def test_known_zero_requires_visible_corridor(self):
        s={'bids':[(D(100),D(5)),(D(98),D(2))],
           'asks':[(D(101),D(6)),(D(103),D(4))]}
        self.assertEqual(r.observed_previous_quantity(s,'bids',D(99)),(D(0),'PRIOR_VISIBLE_ZERO'))
        self.assertEqual(r.observed_previous_quantity(s,'asks',D(102)),(D(0),'PRIOR_VISIBLE_ZERO'))
        self.assertIsNone(r.observed_previous_quantity(s,'bids',D(97))[0])
        self.assertIsNone(r.observed_previous_quantity(s,'asks',D(104))[0])
        self.assertIsNone(r.observed_previous_quantity(s,'bids',D(101))[0])
        self.assertEqual(r.observed_previous_quantity(s,'bids',D(100))[0],D(5))

    def test_censoring_compatibility_does_not_mean_exact(self):
        v=r.differential_classification(D(0),D(239),D('239.3'))
        self.assertFalse(v['exact']);self.assertTrue(v['integer_censoring_compatible'])
        v=r.differential_classification(D(2258),D(2258),D(128))
        self.assertEqual(v['error'],'-128');self.assertFalse(v['integer_censoring_compatible'])

    def test_floor_bound_requires_explicit_encoding_evidence(self):
        self.assertEqual(r.floor_depth_bounds([D(1)],[D(2)])['status'],'UNQUALIFIED_ENCODING')
        with self.assertRaises(r.p.ProbeError):r.floor_depth_bounds([D('1.2')],[D(2)],True)
        with self.assertRaises(r.p.ProbeError):r.floor_depth_bounds([D(-1)],[D(2)],True)

    def test_censored_depth_returns_bounds_not_fabricated_fraction(self):
        b=r.floor_depth_bounds([D(2),D(0)],[D(3),D(1)],True)
        self.assertEqual((b['bid_depth_lower'],b['bid_depth_upper_exclusive']),('2','4'))
        self.assertEqual((b['ask_depth_lower'],b['ask_depth_upper_exclusive']),('4','6'))
        self.assertEqual(D(b['imbalance_lower']),D('-0.5'))
        self.assertEqual(D(b['imbalance_upper']),D(0))
        z=r.floor_depth_bounds([D(0)],[D(0)],True)
        self.assertEqual((z['imbalance_lower'],z['imbalance_upper']),('-1','1'))
        self.assertTrue(z['zero_floor_does_not_prove_empty'])

    def test_neighbor_plan_is_two_new_public_objects_only(self):
        p=r.neighbor_plan();self.assertEqual(len(p['requests']),2)
        old={x['url'] for x in r.p.build_plan()['requests']}
        self.assertTrue(all(x['url'] not in old for x in p['requests']))
        self.assertEqual({x['representative_utc'] for x in p['requests']},{'2026090101'})
        self.assertEqual({x['symbol'] for x in p['requests']},{'BTC_USDT','ETH_USDT'})
        self.assertEqual(p['limits']['requests'],16)
        self.assertTrue(all(x['max_body_bytes']<=p['limits']['object_bytes'] for x in p['requests']))

    def test_raw_negative_residual_is_never_epsilon_repaired(self):
        self.assertEqual(D('21.2999999999999')-D('21.3'),D('-0.0000000000001'))
        v=r.differential_classification(D('21.2999999999999'),D(0),D('-21.3'))
        self.assertFalse(v['exact'])

    def test_shadow_counterexample_cannot_be_promoted_to_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'raw').mkdir()
            rows=['100,set,100,10,1,0','100,set,101,-20,1,0',
                  '101,make,100,5,2,1','102,make,100,128,3,1','103,take,100,168,4,1']
            snapshots=[dict(id=i,current=str(99+i),update=str(99+i),
                            bids=[dict(p='100',s=q)],asks=[dict(p='101',s=20)])
                       for i,q in [(2,15),(3,15),(4,5)]]
            receipts=[]
            for ident,content in [('B','\n'.join(rows)+'\n'),('S','\n'.join(map(json.dumps,snapshots))+'\n')]:
                raw=gzip.compress(content.encode());(root/'raw'/ident).write_bytes(raw)
                receipts.append(dict(raw_path='raw/'+ident,sha256=r.p.sha(raw)))
            result,_=r.parse_pair('B','S',root/'out',*receipts,source_root=root)
            self.assertEqual(result['counts']['transition_present_both'],4)
            self.assertEqual(result['counts']['negative_shadow_events'],1)
            self.assertTrue(result['shadow_negative_states_are_invalid'])
            self.assertTrue(result['diagnostic_does_not_emit_qualified_features'])
            self.assertFalse(result['historical_availability_qualified'])
            self.assertEqual(result['examples']['large_transition_mismatch'][0]['error'],'-128')

    def test_boundary_preserves_small_decimal_discrepancy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'raw').mkdir();(root/'receipts').mkdir()
            current=root/'current';current.write_bytes(gzip.compress(
                b'100,set,100,21.2999999999999,1,0\n100,set,101,-2,1,0\n101,take,100,21.3,2,1\n'))
            raw=gzip.compress(b'101,set,101,-2,2,0\n102,make,100,1,3,1\n')
            (root/'raw/N01').write_bytes(raw)
            (root/'receipts/N01.json').write_text(json.dumps(dict(raw_path='raw/N01',complete_transport=True)))
            with patch.object(r,'DATA',root),patch.object(r,'original_receipt',return_value=({},current)):
                result=r.boundary('B','N01',root/'result.json')
            self.assertTrue(result['exact_source_id_boundary_found'])
            self.assertEqual(result['maximum_absolute_quantity_difference'],'1E-13')
            self.assertEqual(result['counts']['exact_levels'],1)


if __name__=='__main__':unittest.main()
