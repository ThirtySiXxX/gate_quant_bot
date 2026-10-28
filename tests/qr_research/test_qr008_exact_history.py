"""Independent exact-data checker tests. No producer imports or real data scans."""
import copy
from decimal import localcontext
from fractions import Fraction
import gzip
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest

from research.qr008 import validate_exact_history as v


def archive(lines):
    expanded=("\n".join(lines)+"\n").encode()
    return gzip.compress(expanded,mtime=0),dict(start=0,end_exclusive=len(lines)*3600,rows=len(lines),
        expanded_bytes=len(expanded),expanded_sha256=v.sha(expanded))


def rest(rows):
    return v.canonical(rows),dict(start=0,end_exclusive=len(rows)*3600,rows=len(rows))


def raw_rest(t=0,volume="0.1"):
    return dict(t=t,o="100.00",h="104",l="99",c="102",v=volume,sum="10.2")


def hour(index=0,catalog="a"*64):
    return v.expected_row("BTC_USDT",3600,v.START+index*3600*v.U,
        tuple(map(Fraction,("100","104","99","102","0.1"))),
        [dict(raw_sha256="b"*64,source_row=index+1)],[],catalog)


def rehash(row):
    row["content_sha256"]=v.digest({k:x for k,x in row.items() if k!="content_sha256"})


class ExactInputTests(unittest.TestCase):
    def test_decimal_literals_and_large_sum_ignore_ambient_context(self):
        with localcontext() as context:
            context.prec=2
            self.assertEqual(v.decimal_text(v.raw_decimal("0.10")+v.raw_decimal("0.20")),"0.3")
            self.assertEqual(v.decimal_text(Fraction("123456789012345678901234567890.123456789")+Fraction("0.000000001")),"123456789012345678901234567890.12345679")
            self.assertEqual(v.decimal_text(Fraction("0.000")),"0")
            self.assertEqual(v.decimal_text(Fraction("79509.9")-Fraction("79513.6")),"-3.7")

    def test_raw_decimals_reject_nonstring_sign_exponent_and_bounds(self):
        for bad in (None,True,1,1.0,"+1","-0","-1","1e3","NaN"," 1","01",".1","1.","1"*129,"0."+"1"*65):
            with self.subTest(value=bad),self.assertRaises(v.ReviewError):v.raw_decimal(bad)

    def test_output_stricter_than_valid_source_spelling(self):
        self.assertEqual(v.raw_decimal("100.00"),100)
        for text in ("100.00","0.0","+1","01"):
            with self.assertRaises(v.ReviewError):v.output_decimal(text)
        self.assertEqual(v.output_decimal("0"),0)
        with self.assertRaises(v.ReviewError):v.output_decimal("0",True)

    def test_hourly_archive_column_mapping_and_zero_volume(self):
        body,desc=archive(["0,0.1,102,104,99,100.00","3600,0,103,105,100,102"])
        parsed=v.parse_archive(body,desc)
        self.assertEqual(parsed[0],(0,tuple(map(Fraction,("100","104","99","102","0.1"))),1))
        self.assertEqual(parsed[1][1][-1],0)

    def test_archive_duplicate_descending_offgrid_and_missing(self):
        for lines in (["0,1,102,104,99,100","0,1,102,104,99,100"],
                      ["3600,1,102,104,99,100","0,1,102,104,99,100"],
                      ["0,1,102,104,99,100","3601,1,102,104,99,100"],
                      ["0,1,102,104,99,100","7200,1,102,104,99,100"]):
            with self.subTest(lines=lines),self.assertRaises(v.ReviewError):v.parse_archive(*archive(lines))

    def test_archive_closed_fields_domains_and_bad_utf8(self):
        for line in ("", "timestamp,volume,close,high,low,open", "0,1,102,104,99", "0,1,102,104,99,100,extra",
                     "0,-1,102,104,99,100","0,1,102,101,99,100","0,1,102,104,0,100"):
            with self.subTest(line=line),self.assertRaises((v.ReviewError,StopIteration)):
                v.parse_archive(*archive([line]))

    def test_archive_crc_and_expanded_identity(self):
        body,desc=archive(["0,1,102,104,99,100"])
        for corrupt in (body[:-3],body[:-8]+bytes([body[-8]^1])+body[-7:]):
            with self.assertRaises((EOFError,gzip.BadGzipFile)):v.parse_archive(corrupt,desc)
        desc["expanded_sha256"]="0"*64
        with self.assertRaises(v.ReviewError):v.parse_archive(body,desc)

    def test_rest_exact_mapping_and_no_sum_volume_fallback(self):
        parsed,raw=v.parse_rest(*rest([raw_rest(),raw_rest(3600,"0.2")]))
        self.assertEqual(sum(r[1][-1] for r in parsed),Fraction("0.3"))
        self.assertEqual(raw[0]["o"],"100.00")
        bad=raw_rest();bad.pop("v")
        with self.assertRaises(v.ReviewError):v.parse_rest(*rest([bad]))

    def test_rest_bad_types_extra_fields_and_domains(self):
        for change in ({"t":True},{"t":0.0},{"v":1},{"v":None},{"sum":"NaN"},{"h":"90"},{"extra":"x"}):
            row=raw_rest();row.update(change)
            with self.subTest(change=change),self.assertRaises(v.ReviewError):v.parse_rest(*rest([row]))

    def test_rest_grid_duplicate_and_missing(self):
        for times in ([0,0],[3600,0],[0,7200],[0,3601]):
            with self.subTest(times=times),self.assertRaises(v.ReviewError):v.parse_rest(*rest([raw_rest(t) for t in times]))

    def test_json_duplicate_nonfinite_and_bool_uint(self):
        for text in ('{"x":1,"x":2}','{"v":NaN}','{"v":Infinity}'):
            with self.assertRaises(v.ReviewError):v.loads(text)
        for value in (True,1.0,-1,2**63):
            with self.assertRaises(v.ReviewError):v.uint(value)

    def test_old_v2_explicit_clocks_and_physical_refs(self):
        header=b"timestamp,open,high,low,close,volume,available_at,source_id,source_row\n"
        body=header+b"1672531200,100,104,99,102,12,1672534800,request-1,1\n"
        self.assertEqual(v.parse_v2(body,1)[0][-2:],("request-1",1))
        with self.assertRaises(v.ReviewError):v.parse_v2(body.replace(b"1672534800",b"1672531200"),1)

    def test_old_v2_later_tail_is_retained_but_not_in_new_scope(self):
        rows=[(v.START//v.U+i*3600, "literal") for i in range(3)]
        self.assertEqual(v.v2_overlap(rows,v.START,v.START+2*3600*v.U),rows[:2])
        self.assertEqual(len(rows),3)
        with self.assertRaises(v.ReviewError):v.v2_overlap(rows[1:],v.START,v.START+2*3600*v.U)


class ExactOutputTests(unittest.TestCase):
    def test_literal_aggregate_and_nested_equality(self):
        parents=[tuple(map(Fraction,p)) for p in [(100,103,99,101,"0.1"),(101,104,100,103,"0.2"),
            (103,106,98,105,"0.03"),(105,107,104,106,"0.004")]]
        self.assertEqual(v.aggregate(parents),tuple(map(Fraction,(100,107,98,106,"0.334"))))
        daily=parents*6
        self.assertEqual(v.aggregate(daily),v.aggregate([v.aggregate(daily[i:i+4]) for i in range(0,24,4)]))

    def test_closed_schema_and_integer_bool_rejection(self):
        expected=hour()
        for key,value in (("schema_version",True),("interval_seconds",3600.0),("bar_open_us",float(v.START)),
                          ("open",100.0),("volume_contracts",None),("price_kind","MARK")):
            bad=copy.deepcopy(expected);bad[key]=value;rehash(bad)
            with self.subTest(key=key),self.assertRaises(v.ReviewError):v.check_row(bad,expected)
        for mutate in (lambda r:r.pop("availability_basis"),lambda r:r.update(fake="x")):
            bad=copy.deepcopy(expected);mutate(bad);rehash(bad)
            with self.assertRaises(v.ReviewError):v.check_row(bad,expected)

    def test_rehashed_ohlcv_corruption_rejected(self):
        expected=hour()
        for k,value in (("open","101"),("high","105"),("low","98"),("close","103"),("volume_contracts","0.1001")):
            bad=copy.deepcopy(expected);bad[k]=value;rehash(bad)
            with self.subTest(field=k),self.assertRaises(v.ReviewError):v.check_row(bad,expected)

    def test_rehashed_source_swaps_and_omissions_rejected(self):
        expected=hour()
        for refs in ([],[dict(raw_sha256="c"*64,source_row=1)],[dict(raw_sha256="b"*64,source_row=2)],
                     [dict(raw_sha256="b"*64,source_row=True)],expected["source_refs"]*2):
            bad=copy.deepcopy(expected);bad["source_refs"]=refs;rehash(bad)
            with self.subTest(refs=refs),self.assertRaises(v.ReviewError):v.check_row(bad,expected)

    def test_parent_lineage_is_ordered_hourly_and_complete(self):
        parents=[hour(i) for i in range(4)]
        expected=v.expected_row("BTC_USDT",14400,v.START,tuple(map(Fraction,(100,104,99,102,"0.4"))),
            [p["source_refs"][0] for p in parents],[{k:p[k] for k in ("row_id","content_sha256")} for p in parents],"a"*64)
        v.check_row(expected,expected)
        for refs in (expected["parent_rows"][:-1],list(reversed(expected["parent_rows"])),expected["parent_rows"][:1]*4):
            bad=copy.deepcopy(expected);bad["parent_rows"]=refs;rehash(bad)
            with self.assertRaises(v.ReviewError):v.check_row(bad,expected)

    def test_available_at_proxy_and_exclusive_cutoff(self):
        expected=hour();close=expected["bar_close_us"]
        self.assertFalse(v.usable(expected,close-1));self.assertTrue(v.usable(expected,close))
        last=v.expected_row("BTC_USDT",3600,v.END-3600*v.U,tuple(map(Fraction,(100,104,99,102,1))),[],[],"a"*64)
        self.assertFalse(v.usable(last,v.END-1));self.assertFalse(v.usable(last,v.END))
        bad=copy.deepcopy(expected);bad["observed_first_available_at_us"]=close;bad["null_reasons"]={};rehash(bad)
        with self.assertRaises(v.ReviewError):v.check_row(bad,expected)

    def test_future_only_catalog_perturbation_changes_audit_not_past_projection(self):
        # Same past raw, two genuinely different future catalog entries. No producer.
        a=v.digest(dict(past="same",future="future-source-A"));b=v.digest(dict(past="same",future="future-source-B"))
        before,after=hour(catalog=a),hour(catalog=b)
        self.assertNotEqual(before["row_id"],after["row_id"])
        self.assertNotEqual(before["content_sha256"],after["content_sha256"])
        self.assertEqual(v.economic_projection(before),v.economic_projection(after))
        self.assertNotIn("input_catalog_sha256",v.economic_projection(before))
        bad=copy.deepcopy(after);bad["close"]="103";rehash(bad)
        self.assertNotEqual(v.economic_projection(before),v.economic_projection(bad))
        with self.assertRaises(v.ReviewError):v.check_row(bad,after)

    def test_future_raw_perturbation_rehashes_whole_source_but_preserves_past_buckets(self):
        # One 48-hour immutable raw object, with the change only in day two.
        rows=[raw_rest(v.START//v.U+i*3600) for i in range(48)]
        changed=copy.deepcopy(rows);changed[36].update(v="0.7",c="103")
        desc=dict(start=v.START//v.U,end_exclusive=v.START//v.U+48*3600,rows=48)
        snapshots=[]
        for source in (rows,changed):
            body=v.canonical(source);source_hash=v.sha(body)
            parsed,_=v.parse_rest(body,desc)
            catalog_hash=v.digest(dict(sources=[dict(raw_sha256=source_hash,bytes=len(body),start=desc['start'],end_exclusive=desc['end_exclusive'])]))
            past=[];hourly_refs=[]
            for i,(_,numbers,line) in enumerate(parsed[:24]):
                row=v.expected_row("BTC_USDT",3600,v.START+i*3600*v.U,numbers,
                    [dict(raw_sha256=source_hash,source_row=line)],[],catalog_hash)
                past.append(row);hourly_refs.append({k:row[k] for k in ('row_id','content_sha256')})
            for width in (4,24):
                for offset in range(0,24,width):
                    group=parsed[offset:offset+width]
                    past.append(v.expected_row("BTC_USDT",width*3600,v.START+offset*3600*v.U,
                        v.aggregate([r[1] for r in group]),[dict(raw_sha256=source_hash,source_row=r[2]) for r in group],
                        hourly_refs[offset:offset+width],catalog_hash))
            snapshots.append(past)
        self.assertEqual(len(snapshots[0]),31)
        self.assertNotEqual(v.canonical(snapshots[0]),v.canonical(snapshots[1]))
        self.assertEqual([v.economic_projection(r) for r in snapshots[0]],[v.economic_projection(r) for r in snapshots[1]])

    def test_stream_omission_swap_duplicate_and_noncanonical_bytes(self):
        a,b=hour(),hour(1);ca=v.canonical(a)+b"\n";cb=v.canonical(b)+b"\n"
        for raw in (b"",cb,json.dumps(a,indent=2).encode()+b"\n",ca[:-1],b"\n"):
            with self.subTest(size=len(raw)),self.assertRaises((v.ReviewError,json.JSONDecodeError)):
                v.read_expected_row(io.BytesIO(raw),a)
        stream=io.BytesIO(ca+ca)
        v.read_expected_row(stream,a)
        with self.assertRaises(v.ReviewError):v.require_eof(stream)
        stream=io.BytesIO(ca+cb);v.read_expected_row(stream,a);v.read_expected_row(stream,b);v.require_eof(stream)

    def test_same_catalog_same_canonical_bytes(self):
        self.assertEqual(v.canonical(hour()),v.canonical(hour()))
        self.assertNotEqual(hour()["row_id"],hour(1)["row_id"])

    def test_no_overwrite_and_symbolic_link_refusal(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name).resolve();out=folder/"verification-synthetic";out.mkdir()
            v.publish_new(out,"result.json",dict(status="REVISE"));original=(out/"result.json").read_bytes()
            with self.assertRaises(FileExistsError):v.publish_new(out,"result.json",dict(status="PASS"))
            self.assertEqual((out/"result.json").read_bytes(),original)
            link=folder/"link";link.symlink_to(out,target_is_directory=True)
            with self.assertRaises(v.ReviewError):v.publish_new(link,"new.json",{})

    def test_offline_guard_restores_original(self):
        original=socket.create_connection
        with v.offline():
            with self.assertRaises(v.ReviewError):socket.create_connection(("invalid.example",443))
        self.assertIs(socket.create_connection,original)


if __name__=="__main__":unittest.main()
