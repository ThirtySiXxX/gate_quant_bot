"""Literal MARK raw/alias/query checks; never loads the coordinator collector."""
import copy
import gzip
import io
import unittest

from research.qr008 import validate_mark_raw as v
from research.qr008 import validate_exact_history as common


def text_time(us):
    return str(us//common.U)+"."+str(us%common.U).zfill(6)


def fields(us,mark="2"):
    return [text_time(us),"1",mark,"3"]


def body_for(rows):
    return gzip.compress(("\n".join(",".join(r) for r in rows)+"\n").encode(),mtime=0)


def scan(rows,chunk=1024*1024):
    body=body_for(rows)
    return v.scan_object(io.BytesIO(body),"BTC_USDT","202301",common.sha(body),len(body),chunk_bytes=chunk)


def point(us,source_row=1,mark="2",refs=None):
    return v.make_point("BTC_USDT","a"*64,source_row,[source_row] if refs is None else refs,fields(us,mark))


def query(us,scenario="MARK_ARCHIVE_DELAY60_AGE120_R1"):
    return dict(instrument_id="gate:usdt:BTC_USDT",query_us=us,kind="decision",price_kind="MARK",scenario_id=scenario)


class MarkRawTests(unittest.TestCase):
    def test_exact_microseconds_no_rounding(self):
        f=[b"1672531200.000001",b"1",b"2",b"3"]
        self.assertEqual(v.parse_fields(f),common.START+1)
        for timestamp in (b"1672531200.0000001",b"1672531200.0000000",b"1e9",b"+1672531200",b"01672531200",b"NaN"):
            with self.subTest(t=timestamp),self.assertRaises(common.ReviewError):v.parse_fields([timestamp,*f[1:]])

    def test_positive_price_grammar_bounds(self):
        for price in (b"0",b"0.000",b"-1",b"+1",b"NaN",b"1e3",b" 1",b"1."+b"0"*65,b"1"*129):
            with self.subTest(price=price),self.assertRaises(common.ReviewError):
                v.parse_fields([b"1672531200",b"1",price,b"3"])
        self.assertEqual(v.parse_fields([b"1672531200",b"1",b"2.00",b"3"]),common.START)

    def test_aliases_retain_all_physical_references_and_mark_column(self):
        t=common.START+1
        checked=scan([fields(t)]*3+[fields(t+1)])
        self.assertEqual((checked["physical_rows"],checked["canonical_observations"],checked["alias_rows"]),(4,2,2))
        alias=checked["alias_groups"][0]
        self.assertEqual(alias["source_rows"],[1,2,3]);self.assertEqual(alias["source_row"],1)
        self.assertEqual(alias["raw_observation_text"],fields(t))
        self.assertEqual(alias["point_id"],common.digest([v.NS,2,"gate:usdt:BTC_USDT",alias["raw_sha256"],1]))
        self.assertEqual(point(t)["mark_price"],"2")

    def test_alias_lexeme_conflict_even_if_numerically_equal(self):
        a=fields(common.START)
        for i,replacement in ((0,str(common.START//common.U)+".0"),(1,"1.00"),(2,"2.0"),(2,"2.1"),(3,"3.00")):
            b=a.copy();b[i]=replacement
            with self.subTest(column=i,value=replacement),self.assertRaisesRegex(common.ReviewError,"conflicting"):
                scan([a,b])

    def test_descending_cannot_be_deduplicated_or_sorted(self):
        t=common.START
        for rows in ([fields(t+2),fields(t+1)],[fields(t),fields(t+2),fields(t)]):
            with self.assertRaisesRegex(common.ReviewError,"descending"):scan(rows)

    def test_alias_across_arbitrary_chunk_boundaries(self):
        t=common.START+1;rows=[fields(t)]*3+[fields(t+61*common.U)]*2+[fields(t+62*common.U)]
        wanted=scan(rows)
        for chunk in (1,2,7,31,1024):
            with self.subTest(chunk=chunk):self.assertEqual(scan(rows,chunk),wanted)

    def test_exact_gap_thresholds_and_boundary_distance(self):
        t=common.START+1
        rows=[fields(t),fields(t+60*common.U),fields(t+180*common.U+1),fields(t+360*common.U+2)]
        result=scan(rows)
        self.assertEqual(result["gap_counts_seconds"],{"60":2,"120":2,"180":1})
        self.assertEqual(result["max_gap_us"],180*common.U+1)
        self.assertEqual(result["start_boundary_gap_us"],1)
        self.assertEqual(result["end_boundary_gap_us"],v.month_bounds("202301")[1]-(t+360*common.U+2))
        self.assertEqual(result["gaps_gt60_us_and_source_rows"][0],[t+60*common.U,t+180*common.U+1,2,3])

    def test_month_and_instrument_scope(self):
        for t in (common.START-1,v.month_bounds("202301")[1]):
            with self.assertRaisesRegex(common.ReviewError,"month"):scan([fields(t)])
        body=body_for([fields(common.START)])
        with self.assertRaises(common.ReviewError):v.scan_object(io.BytesIO(body),"SOL_USDT","202301",common.sha(body),len(body))

    def test_empty_bad_columns_header_bad_utf8_and_long_line(self):
        for expanded in (b"",b"\n",b"timestamp,index,mark,last\n",b"1672531200,1,2\n",b"1672531200,1,2,3,4\n",
                         b"1672531200,1,\xff,3\n",b"1"*1025+b"\n"):
            body=gzip.compress(expanded,mtime=0)
            with self.subTest(length=len(expanded)),self.assertRaises((common.ReviewError,UnicodeDecodeError)):
                v.scan_object(io.BytesIO(body),"BTC_USDT","202301",common.sha(body),len(body))

    def test_crc_and_compressed_hash_not_just_row_count(self):
        body=body_for([fields(common.START)])
        broken=body[:-8]+bytes([body[-8]^1])+body[-7:]
        for bad in (body[:-3],broken):
            with self.assertRaises((EOFError,gzip.BadGzipFile)):
                v.scan_object(io.BytesIO(bad),"BTC_USDT","202301",common.sha(bad),len(bad))
        with self.assertRaisesRegex(common.ReviewError,"hash"):
            v.scan_object(io.BytesIO(body),"BTC_USDT","202301","0"*64,len(body))

    def test_all_90_month_objects_required_no_duplicate_or_swap(self):
        complete=[dict(month=m,symbol=s) for m,s in v.fixed_queue()];v.check_queue(complete)
        self.assertEqual(len(complete),90)
        for broken in (complete[:-1],complete+[complete[0]],list(reversed(complete)),[complete[1]]+complete[1:]):
            with self.assertRaises(common.ReviewError):v.check_queue(broken)

    def test_missing_final_lf_does_not_invent_or_drop_point(self):
        rows=[fields(common.START)]
        expanded=",".join(rows[0]).encode();body=gzip.compress(expanded,mtime=0)
        result=v.scan_object(io.BytesIO(body),"BTC_USDT","202301",common.sha(body),len(body),chunk_bytes=5)
        self.assertEqual(result["physical_rows"],1)

    def test_same_prices_at_later_timestamp_are_distinct_observations(self):
        result=scan([fields(common.START),fields(common.START+1)])
        self.assertEqual(result["canonical_observations"],2);self.assertEqual(result["alias_rows"],0)

    def test_raw_complete_does_not_claim_query_coverage(self):
        result=scan([fields(common.START)])
        self.assertIsNone(result["required_query_count"])
        self.assertEqual(result["query_support_status"],"NOT_EVALUATED")
        self.assertFalse(result["normalized_points_written"])


class MarkQueryTests(unittest.TestCase):
    def setUp(self):self.covered={("BTC_USDT","202301")};self.t=common.START+common.U

    def test_lag_boundary_one_microsecond_before_and_equality(self):
        p=point(self.t)
        for scenario,(lag,_,_) in v.SCENARIOS.items():
            self.assertEqual(v.select_mark([p],query(self.t+lag-1,scenario),self.covered)["status"],"UNAVAILABLE")
            self.assertEqual(v.select_mark([p],query(self.t+lag,scenario),self.covered)["mark_price"],"2")

    def test_source_available_age_equality_and_one_microsecond_outside(self):
        p=point(self.t)
        for scenario,(_,age,_) in v.SCENARIOS.items():
            self.assertEqual(v.select_mark([p],query(self.t+age,scenario),self.covered)["status"],"AVAILABLE_SCENARIO_ONLY")
            self.assertEqual(v.select_mark([p],query(self.t+age+1,scenario),self.covered)["reason"],"NO_CAUSAL_FRESH_MARK")

    def test_latest_causally_available_mark_not_latest_future_point(self):
        p=point(self.t);future=point(self.t+70*common.U,2,"20")
        before=v.select_mark([p],query(self.t+120*common.U),self.covered)
        self.assertEqual(v.select_mark([p,future],query(self.t+120*common.U),self.covered),before)
        self.assertEqual(before["mark_price"],"2")

    def test_wrong_price_kind_or_field_tampering_rejected(self):
        p=point(self.t);q=query(self.t+60*common.U)
        for kind in ("TRADE","INDEX","LAST"):
            bad=dict(q,price_kind=kind)
            with self.assertRaises(common.ReviewError):v.select_mark([p],bad,self.covered)
        bad=copy.deepcopy(p);bad["mark_price"]="3"
        with self.assertRaises(common.ReviewError):v.select_mark([bad],q,self.covered)

    def test_missing_current_month_blocks_fresh_prior_month(self):
        boundary=v.month_bounds("202301")[1];p=point(boundary-60*common.U)
        missing=v.select_mark([p],query(boundary),{("BTC_USDT","202301")})
        self.assertEqual(missing["reason"],"MISSING_SOURCE_MONTH")
        supported=v.select_mark([p],query(boundary),{("BTC_USDT","202301"),("BTC_USDT","202302")})
        self.assertEqual(supported["status"],"AVAILABLE_SCENARIO_ONLY")

    def test_empty_points_retains_unknown_not_zero_or_trade_fallback(self):
        result=v.select_mark([],query(self.t+60*common.U),self.covered)
        self.assertIsNone(result["mark_price"]);self.assertEqual(result["reason"],"NO_CAUSAL_FRESH_MARK")

    def test_query_order_duplicate_identity_and_cutoff(self):
        a,b=point(self.t),point(self.t+common.U,2)
        for points in ([b,a],[a,a]):
            with self.assertRaises(common.ReviewError):v.select_mark(points,query(self.t+90*common.U),self.covered)
        for q in (query(common.END),query(common.START-1),query(True)):
            with self.assertRaises(common.ReviewError):v.select_mark([a],q,self.covered)

    def test_alias_reference_completeness_and_types(self):
        for refs in ([],[1,3],[True],[1,1]):
            with self.assertRaises(common.ReviewError):point(self.t,refs=refs)
        p=point(self.t,refs=[1,2,3]);self.assertEqual(p["alias_count"],2)
        result=v.select_mark([p],query(self.t+60*common.U),self.covered)
        self.assertEqual(result["source_rows"],[1,2,3])


if __name__=="__main__":unittest.main()
