from copy import deepcopy
from fractions import Fraction
import json
import unittest
from research.qd021.fast import graph_copy


class CopyChecks(unittest.TestCase):
    def test_alias_cycles_and_mutable_isolation(self):
        shared={'v':[1,2]};source={'a':shared,'b':shared};source['cycle']=source
        result=graph_copy(source)
        self.assertIs(result['a'],result['b']);self.assertIs(result['cycle'],result)
        self.assertIsNot(result['a'],shared);result['a']['v'].append(3)
        self.assertEqual(shared['v'],[1,2])

    def test_fallback_tuple_custom_and_caller_memo(self):
        class Custom:
            def __init__(self):self.value=[1]
        x=Custom();src={'t':(x,x),'f':Fraction(1,3),'b':b'bytes'}
        a,b=deepcopy(src),graph_copy(src)
        self.assertEqual(a['f'],b['f']);self.assertEqual(a['t'][0].value,b['t'][0].value)
        self.assertIs(b['t'][0],b['t'][1]);self.assertIsNot(b['t'][0],x)
        self.assertIsNone(graph_copy(src,{id(src):None}))

    def test_custom_copy_order_matches_standard_copy(self):
        events=[]
        class Item:
            def __init__(self,name):self.name=name
            def __deepcopy__(self,memo):events.append(self.name);return Item(self.name)
        source={Item('key'):Item('value')}
        deepcopy(source);expected=list(events);events.clear();graph_copy(source)
        self.assertEqual(events,expected)

    def test_canonical_validation_preserves_bytes_and_error_codes(self):
        from research.qd009 import streaming_ledger as sl
        from research.qd021.fast import strict_json
        good=[None,True,1,'汉字',[1,'x',{'a':[None,False]}],{'big':2**200,'empty':[]}]
        bad=[1.0,float('nan'),(1,),{1:'bad'},{'x':[Fraction(1,2)]}]
        for value in good:
            sl.strict_json(value);strict_json(value)
            self.assertEqual(sl.canonical_bytes(value),json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
        for value in bad:
            with self.assertRaises(sl.LedgerError) as old:sl.strict_json(value)
            with self.assertRaises(sl.LedgerError) as new:strict_json(value)
            self.assertEqual(old.exception.code,new.exception.code)

    def test_node_hash_matches_original_canonical_algorithm(self):
        from research.qd009 import streaming_ledger as sl
        from research.qd021.fast import node_hash
        for value in [None,{},[1,'汉字'],{'n':2**128,'s':'quote"slash\\','x':[True,False]}]:
            self.assertEqual(node_hash('lots',['x',1],sl.canonical_bytes(value),'a'*64,'b'*64),
                             sl.digest(['qf009.economic-node-v3','lots',['x',1],value,'a'*64,'b'*64]))


if __name__=='__main__':unittest.main()
