"""Producer tests use literal cash/lot oracles, not producer arithmetic as expected."""
from copy import deepcopy
from decimal import Inexact, localcontext
import hashlib
import json
import unittest

from research.qd007 import event_ledger as el

BTC, ETH = el.INSTRUMENTS


def wire_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def record(typ, ident, at, inst=BTC, **fields):
    return dict(namespace=el.NS,schema_version=1,record_type=typ,record_id=ident,revision=1,
        instrument_id=inst,trajectory_id="trajectory",scenario_id="scenario",evidence_mode="SCENARIO",
        created_at_us=999,available_at_us=at,source_time_precision="microseconds",
        source_refs=[dict(manifest_sha256="0"*64,source_id="pending",source_row=1)],null_reasons={},**fields)


def rid(kind, inst=BTC):return kind+":"+("btc" if inst==BTC else "eth")


def fill(ident="open", at=1, qty=10, price="49900", fee="0.0005", inst=BTC, available=None):
    r=record("Fill",ident,at if available is None else available,inst,
        order_id="order:"+ident,decision_id="decision:"+ident,decision_at_us=at,filled_at_us=at,
        sequence=None,signed_contracts=qty,fill_price=price,multiplier="0.001",
        multiplier_rule_id=rid("multiplier",inst),fee_fraction=fee,fee_rule_id=rid("fee",inst),
        liquidity_role="taker",role_basis="scenario",fee_currency="USDT",fee_obligation_id="fee:"+ident)
    r["null_reasons"]={"sequence":"UNKNOWN_SEQUENCE"}
    return r


def unit(lot="open", start=0, end=10, episode="open"):
    return dict(lot_id="lot:"+lot,episode_id="episode:"+episode,unit_start=start,unit_end=end)


def allocation(oid, amount, u=None, inst=BTC):
    u=deepcopy(u or unit())
    return dict(u,allocation_id=wire_hash(["ledger","trajectory","scenario",inst,oid,u["lot_id"],u["unit_start"],u["unit_end"]]),signed_cash_usdt=amount)


def snapshot(ident="fund", at=8, units=None, inst=BTC, mapping=True):
    r=record("FundingSnapshot",ident,at,inst,nominal_settlement_at_us=at,snapshot_at_us=at,snapshot_sequence=None,
        source_t_seconds=None,source_record_at_us=None,mapping_rule_id=rid("funding",inst) if mapping else None,
        obligation_id="ob:"+ident,eligible_ranges=deepcopy([unit()] if units is None else units))
    r["null_reasons"]=dict(snapshot_sequence="UNKNOWN_SEQUENCE",source_t_seconds="UNKNOWN_SOURCE_TIME",source_record_at_us="UNKNOWN_SOURCE_TIME")
    if not mapping:r["null_reasons"]["mapping_rule_id"]="UNKNOWN_MAPPING"
    return r


def revision(oid="ob:fund", origin="fund", total="-0.05", at=8, economic=8, version=1, kind="funding", units=None, inst=BTC):
    r=record("ObligationRevision",oid,at,inst,obligation_kind=kind,origin_id=origin,
        supersedes_revision=version-1 if version>1 else None,authority_id="authority",rule_id=rid(kind,inst),
        economic_at_us=economic,known_at_us=at,cumulative_signed_total_usdt=total,
        allocations=[] if total is None else [allocation(oid,total,units,inst)],
        calculation=None if total is None else dict(kind="authoritative_total"))
    r["revision"]=version
    if version==1:r["null_reasons"]["supersedes_revision"]="NOT_APPLICABLE"
    if total is None:r["null_reasons"].update(cumulative_signed_total_usdt="UNKNOWN_AMOUNT",calculation="UNKNOWN_AMOUNT")
    return r


def posting(ident="payment", oid="ob:fund", amount="-0.05", at=10, units=None, inst=BTC):
    r=record("Posting",ident,at,inst,obligation_id=oid,signed_amount_usdt=amount,booking_at_us=at,
        booking_known_at_us=at,booking_basis="scenario",booking_rule_id=rid("booking",inst),
        corrects_posting_id=None,allocations=[allocation(oid,amount,units,inst)])
    r["null_reasons"]={"corrects_posting_id":"NOT_APPLICABLE"}
    return r


def reserves(inst=BTC):
    return record("Reserves",rid("reserve",inst),0,inst,effective_at_us=0,expires_at_us=10000,
        known_at_us=0,reserved_margin_usdt="0",reserved_fees_usdt="0",
        excludes_counted_losses_liabilities_and_posted_fees=True)


def mark(ident="mark", at=8, price="50000", inst=BTC):
    return record("Valuation",ident,at,inst,valuation_at_us=at,known_at_us=at,price_kind="MARK",
        mark_price=price,valuation_rule_id=rid("valuation",inst),multiplier_rule_id=rid("multiplier",inst))


def assertion(at=10, version=1, fund_version=1, payments=("payment",), ident="assertion"):
    r=record("CompletenessAssertion",ident,at,supersedes_revision=version-1 if version>1 else None,
        authority_id="authority",finality_rule_id=rid("finality"),scope=dict(instrument_id=BTC,trajectory_id="trajectory",
        episode_id="episode:open",event_kinds=["fill","fee","funding","posting"],economic_from_us=1,economic_to_exclusive_us=10),
        obligation_revision_refs=[dict(obligation_id="fee:open",revision=1),dict(obligation_id="fee:close",revision=1),dict(obligation_id="ob:fund",revision=fund_version)],
        posting_refs=[dict(posting_id=p,revision=1) for p in payments],asserted_at_us=at,known_at_us=at)
    r["revision"]=version
    if version==1:r["null_reasons"]["supersedes_revision"]="NOT_APPLICABLE"
    return r


def bind(records, fee="0.0005", instruments=(BTC,), quantum="0.0001", calendar=None, tie="snapshot_before_fills"):
    records=deepcopy(records)
    rules=[]
    for inst in instruments:
        for kind,params in dict(fee=dict(role="taker",signed_fraction=fee,fee_currency="USDT"),
            multiplier=dict(base_per_contract="0.001",quantity_unit="contracts"),
            valuation=dict(price_kind="MARK",max_age_us=100),sequence=dict(same_time_order=tie),
            funding=dict(calendar="explicit_snapshot_list"),booking=dict(policy="explicit_posting_records"),
            finality=dict(policy="explicit_scoped_assertions",authority_id="authority")).items():
            rules.append(dict(rule_id=rid(kind,inst),kind=kind,instrument_id=inst,valid_from_us=0,
                valid_to_exclusive_us=None,available_at_us=0,authority_id="authority",parameters=params,
                null_reasons=dict(valid_to_exclusive_us="OPEN_ENDED_SCENARIO")))
    rows=[]
    for i,r in enumerate(records):
        rows.append(dict(source_id=f"source:{i:04}",source_row=1,payload_sha256=el.content_sha256(r)))
    manifest=dict(namespace="qd007.synthetic-sources",schema_version=1,fixture_id="literal-fixture",rows=rows)
    mh=wire_hash(manifest)
    for i,r in enumerate(records):r["source_refs"]=[dict(manifest_sha256=mh,source_id=f"source:{i:04}",source_row=1)]
    if calendar is None:calendar=[dict(instrument_id=r["instrument_id"],event_id=r["record_id"],snapshot_at_us=r["snapshot_at_us"],mapping_rule_id=rid("funding",r["instrument_id"])) for r in records if r["record_type"]=="FundingSnapshot"]
    config=dict(namespace=el.NS,schema_version=1,ledger_id="ledger",trajectory_id="trajectory",scenario_id="scenario",
        instruments=list(instruments),initial_at_us=0,end_exclusive_us=10000,initial_cash_usdt="10000",
        allocation_quantum_usdt=quantum,rules=rules,expected_funding_snapshots=deepcopy(calendar),source_manifest=manifest)
    return config,records


def economic_tape():
    return [reserves(),fill(),posting("entryfee","fee:open","-0.2495",1),mark("entrymark",1,"49900"),
        snapshot(),revision(),mark(),fill("close",9,-10,"50100"),
        posting("exitfee","fee:close","-0.2505",9),posting()]


class EventLedgerTests(unittest.TestCase):
    def ledger(self, records=None, **kwargs):
        c,rs=bind(economic_tape() if records is None else records,**kwargs)
        ledger=el.Ledger(c);ledger.apply_batch(rs)
        return ledger,rs,c

    def test_literal_fees_funding_signs_and_price_pnl(self):
        self.assertEqual(el.fee_cash(10,"0.001","49900","0.0005"),"-0.2495")
        self.assertEqual(el.fee_cash(10,"0.001","49900","-0.0001"),"0.0499")
        self.assertEqual(el.fee_cash(0,"0.001","1","0.0005"),"0")
        for q,rate,expected in [(10,"0.0001","-0.05"),(10,"-0.0001","0.05"),(-10,"0.0001","0.05"),(-10,"-0.0001","-0.05"),(10,"0","0")]:
            with self.subTest(q=q,rate=rate):self.assertEqual(el.funding_cash(q,"0.001","50000",rate),expected)
        self.assertEqual(el.realized_pnl(1,"1","101","110"),"9")
        self.assertEqual(el.fee_cash(10,"0.001","49900","0.00075"),"-0.37425")
        self.assertEqual(el.fee_cash(10,"0.001","49900","0.0015"),"-0.7485")

    def test_quantum_signed_zero_and_invalid_weights(self):
        self.assertEqual(el.allocate_pro_rata("0.01",[1,1,1],"0.0001"),["0.0033","0.0033","0.0034"])
        self.assertEqual(el.allocate_pro_rata("-0.01",[1,1,1],"0.0001"),["-0.0033","-0.0033","-0.0034"])
        self.assertEqual(el.allocate_pro_rata("0",[6,6,6,2],"0.01"),["0"]*4)
        self.assertEqual(el.allocate_pro_rata("0",[],"0.01"),[])
        for total,weights in [("0.02",[6,6,6,2]),("-0.02",[6,6,6,2]),("0",[0]),("0",[-1]),("1",[])]:
            with self.subTest(total=total,weights=weights),self.assertRaises(el.LedgerError):el.allocate_pro_rata(total,weights,"0.01")

    def test_decimal_context_independence_and_invalid_lexical_types(self):
        with localcontext() as ctx:
            ctx.prec=2;ctx.traps[Inexact]=True
            self.assertEqual(el.fee_cash(10,"0.001","49900","0.0005"),"-0.2495")
            self.assertEqual(el.allocate_pro_rata("0.01",[1,1,1],"0.0001"),["0.0033","0.0033","0.0034"])
            ledger,_,_=self.ledger()
            self.assertEqual(ledger.snapshot(10)["balances"]["cash_usdt"],"10001.45")
        for value in (True,1.5,".1","01","NaN","1e-4","0.05%"," 1"):
            with self.subTest(value=value),self.assertRaises(el.LedgerError):el.fee_cash(10,"0.001","1",value)
        for q in (True,0.5,"1"):
            with self.subTest(q=q),self.assertRaises(el.LedgerError):el.funding_cash(q,"1","1","0.1")

    def test_exact_time_and_canonicalization(self):
        self.assertEqual(el.seconds_to_us(86400),86400000000)
        self.assertEqual(el.seconds_to_us("0.000001"),1)
        for value in (True,1.0,"0.0000001"):
            with self.subTest(value=value),self.assertRaises(el.LedgerError):el.seconds_to_us(value)
        r=fill();r["fill_price"]="+49900.00"
        self.assertEqual(el.validate_record(r)["fill_price"],"49900")
        self.assertFalse(el.canonical_bytes(r).endswith(b"\n"))
        same=deepcopy(r);same["created_at_us"]+=1
        self.assertEqual(el.content_sha256(r),el.content_sha256(same))

    def test_a11_full_late_booking_cash_and_equity_literals(self):
        ledger,_,_=self.ledger()
        for t,C,L,U,E in [(1,"9999.7505","0","0","9999.7505"),(8,"9999.7505","0.05","1","10000.7005"),(9,"10001.5","0.05","0","10001.45"),(10,"10001.45","0","0","10001.45")]:
            with self.subTest(t=t):
                b=ledger.snapshot(t)["balances"]
                self.assertEqual([b[k] for k in ("cash_usdt","liabilities_usdt","unrealized_usdt","economic_equity_usdt")],[C,L,U,E])
        sl=ledger.snapshot(10)["closed_slices"][0]
        self.assertEqual([sl[k] for k in ("realized_price_pnl_usdt","entry_fee_cash_usdt","exit_fee_cash_usdt","funding_cash_usdt")],["2","-0.2495","-0.2505","-0.05"])

    def test_partial_reduction_and_pre_snapshot_unit_eligibility(self):
        tape=economic_tape()
        tape[7]=fill("close",9,-6,"50100")
        tape[8]=posting("exitfee","fee:close","-0.1503",9,unit(start=0,end=6))
        tape += [fill("last",11,-4,"50100"),posting("lastfee","fee:last","-0.1002",11,unit(start=6,end=10))]
        ledger,_,_=self.ledger(tape)
        slices=ledger.snapshot(11)["closed_slices"]
        self.assertEqual([[s[k] for k in ("realized_price_pnl_usdt","entry_fee_cash_usdt","exit_fee_cash_usdt","funding_cash_usdt")] for s in slices],[["1.2","-0.1497","-0.1503","-0.03"],["0.8","-0.0998","-0.1002","-0.02"]])
        records=[reserves(),fill(fee="0"),fill("early",7,-4,"49900",fee="0"),snapshot(units=[unit(start=4,end=10)]),
            revision(total="-0.03",units=unit(start=4,end=10)),fill("late",9,-6,"49900",fee="0")]
        ledger,_,_=self.ledger(records,fee="0")
        self.assertEqual([s["funding_cash_usdt"] for s in ledger.snapshot(9)["closed_slices"]],["0","-0.03"])

    def test_reversal_old_lot_funding_and_single_fee_cash(self):
        tape=economic_tape()[:7]
        rev=fill("reverse",9,-16,"50000")
        pay=posting("reversalfee","fee:reverse","-0.4",9)
        pay["allocations"]=[allocation("fee:reverse","-0.25"),allocation("fee:reverse","-0.15",unit("reverse",0,6,"reverse"))]
        tape += [rev,pay,posting(),mark("after",10,"50000")]
        ledger,_,_=self.ledger(tape)
        state=ledger.snapshot(10)
        self.assertEqual([l["remaining_contracts"] for l in state["lots"]],[0,6])
        self.assertEqual(state["lots"][1]["episode_id"],"episode:reverse")
        self.assertEqual(state["closed_slices"][0]["funding_cash_usdt"],"-0.05")
        cash=[e for e in ledger.audit()["committed_state"]["derived_entries"] if e["source_key"]["record_id"]=="reversalfee"]
        self.assertEqual(len(cash),1);self.assertEqual(cash[0]["cash_delta_usdt"],"-0.4")

    def test_r01_cross_fixture_future_hash_isolation(self):
        common=[reserves(),fill(fee="0"),snapshot(),revision(total="-0.05",at=10)]
        a=common+[revision(total="-0.08",at=20,version=2)]
        b=common+[revision(total="-0.10",at=20,version=2)]
        la,ra,_=self.ledger(a,fee="0");lb,rb,_=self.ledger(b,fee="0")
        self.assertNotEqual(ra[0]["source_refs"],rb[0]["source_refs"])
        self.assertEqual(la.snapshot(10),lb.snapshot(10))
        self.assertNotEqual(la.audit()["config_sha256"],lb.audit()["config_sha256"])
        self.assertNotEqual(la.audit()["committed_sha256"],lb.audit()["committed_sha256"])

    def test_r02_whole_batch_late_origin_and_atomicity(self):
        f=fill(at=7,available=9,fee="0");s=snapshot(units=[])
        for records in ([f,s],[s,f]):
            c,rs=bind(records,fee="0");ledger=el.Ledger(c);before=ledger.audit()["committed_state"]
            with self.assertRaisesRegex(el.LedgerError,"LATE_ORIGIN_UNSUPPORTED"):ledger.apply_batch(rs)
            self.assertEqual(before,ledger.audit()["committed_state"])
        c,rs=bind([s,f],fee="0");ledger=el.Ledger(c);ledger.apply_batch(rs[:1]);before=ledger.audit()["committed_state"]
        with self.assertRaises(el.LedgerError):ledger.apply_batch(rs[1:])
        self.assertEqual(before,ledger.audit()["committed_state"])
        with self.assertRaisesRegex(el.LedgerError,"INTEGRITY_STOPPED"):ledger.snapshot(8)
        self.ledger([fill(at=7,fee="0"),snapshot()],fee="0")

    def test_r03_proxy_mark_and_late_final_rate(self):
        r=revision(at=100,economic=80);r["known_at_us"]=95
        r["calculation"]=dict(kind="funding_formula",signed_contracts=10,multiplier="0.001",mark_price="50000",final_rate="0.0001",
            valuation_at_us=79,valuation_available_at_us=79,rate_available_at_us=95,valuation_rule_id=rid("valuation"),multiplier_rule_id=rid("multiplier"))
        ledger,_,_=self.ledger([fill(fee="0"),snapshot(at=80),r],fee="0")
        self.assertIsNone(next(o for o in ledger.snapshot(99)["obligations"] if o["kind"]=="funding")["T_usdt"])
        self.assertEqual(next(o for o in ledger.snapshot(100)["obligations"] if o["kind"]=="funding")["T_usdt"],"-0.05")
        bad=deepcopy(r);bad["calculation"]["valuation_available_at_us"]=90
        c,rs=bind([fill(fee="0"),snapshot(at=80),bad],fee="0")
        with self.assertRaisesRegex(el.LedgerError,"FUTURE_PROXY_MARK"):el.Ledger(c).apply_batch(rs)

    def test_r04_assertion_supersession_grouping_and_old_queries(self):
        records=[reserves(),fill(fee="0"),snapshot(),revision(),posting(at=8),fill("close",9,-10,"49900",fee="0"),assertion(),
            revision(total="-0.08",at=20,version=2),posting("extra",amount="-0.03",at=21),assertion(22,2,2,("payment","extra"))]
        c,rs=bind(records,fee="0");all_at_once=el.Ledger(c);all_at_once.apply_batch(list(reversed(rs)))
        batches=el.Ledger(c)
        for t in sorted({r["available_at_us"] for r in rs}):batches.apply_batch([r for r in rs if r["available_at_us"]==t])
        for t,status,known in [(10,"complete",10),(20,"immature",None),(21,"immature",None),(22,"complete",22)]:
            a=all_at_once.readiness("episode:open",t)
            self.assertEqual((a["status"],a["complete_at_us"]),(status,known))
            self.assertEqual(a,batches.readiness("episode:open",t))
        self.assertEqual(batches.audit()["integrity"],"clean")

    def test_r05_dual_instrument_id_conflict_and_legal_shared_account(self):
        c,rs=bind([fill("same",fee="0"),fill("same",fee="0",inst=ETH)],fee="0",instruments=(BTC,ETH))
        ledger=el.Ledger(c);before=ledger.audit()["committed_state"]
        with self.assertRaisesRegex(el.LedgerError,"ID_SCOPE_CONFLICT"):ledger.apply_batch(rs)
        self.assertEqual(ledger.audit()["committed_state"],before)
        ledger,_,_=self.ledger([reserves(),reserves(ETH),fill("btc",fee="0"),fill("eth",fee="0",inst=ETH),mark(inst=BTC),mark("ethmark",inst=ETH)],fee="0",instruments=(BTC,ETH))
        self.assertEqual(len(ledger.snapshot(8)["lots"]),2)

    def test_r06_known_posting_unknown_total_then_known_levels(self):
        records=[reserves(),fill(fee="0"),snapshot(),fill("close",9,-10,"49900",fee="0"),posting(amount="-0.02"),revision(at=20)]
        c,rs=bind(records,fee="0");c["initial_cash_usdt"]="1000";ledger=el.Ledger(c);receipt=ledger.apply_batch(rs)
        b=ledger.snapshot(10)["balances"]
        self.assertEqual(b["cash_usdt"],"999.98")
        self.assertTrue(all(b[k] is None for k in ("receivables_usdt","liabilities_usdt","economic_equity_usdt","simulated_budget_usdt")))
        o=next(o for o in ledger.snapshot(10)["obligations"] if o["kind"]=="funding")
        self.assertEqual(o["B_usdt"],"-0.02");self.assertIsNone(o["T_usdt"])
        e=next(e for e in receipt["entries"] if e["source_key"]["record_id"]=="payment")
        self.assertEqual(e["cash_delta_usdt"],"-0.02")
        self.assertTrue(all(e[k] is None for k in ("pending_delta_usdt","receivable_delta_usdt","liability_delta_usdt")))
        b=ledger.snapshot(20)["balances"]
        self.assertEqual([b[k] for k in ("cash_usdt","liabilities_usdt","economic_equity_usdt")],["999.98","0.03","999.95"])
        e=next(e for e in receipt["entries"] if e["source_key"]["record_type"]=="ObligationRevision")
        self.assertEqual(e["null_reasons"]["pending_delta_usdt"],"UNKNOWN_PRIOR_BALANCE")

    def test_duplicate_conflict_rollback_and_deepcopy(self):
        c,rs=bind(economic_tape());ledger=el.Ledger(c);original=deepcopy(rs)
        ledger.apply_batch(rs);before=ledger.audit()
        receipt=ledger.apply_batch(rs)
        self.assertEqual(receipt["status"],"duplicate");self.assertFalse(receipt["entries"])
        self.assertEqual(ledger.audit(),before);self.assertEqual(rs,original)
        mutated=ledger.snapshot(10);mutated["balances"]["cash_usdt"]="0"
        self.assertEqual(ledger.snapshot(10)["balances"]["cash_usdt"],"10001.45")
        a=ledger.audit();a["committed_state"]["records"].clear();self.assertTrue(ledger.audit()["committed_state"]["records"])
        bad=deepcopy(rs[-1]);bad["signed_amount_usdt"]="-0.1"
        with self.assertRaisesRegex(el.LedgerError,"CONFLICTING_POSTING_REVISION"):ledger.apply_batch([bad])
        self.assertEqual(ledger.audit()["committed_state"],before["committed_state"])
        self.assertEqual(ledger.audit()["integrity"],"stopped")

    def test_rehashed_corruption_and_extra_fields_cannot_bless_inputs(self):
        tape=economic_tape();tape[4]["eligible_ranges"][0]["unit_end"]=9
        c,rs=bind(tape);ledger=el.Ledger(c)
        with self.assertRaisesRegex(el.LedgerError,"ELIGIBILITY_MISMATCH"):ledger.apply_batch(rs)
        c,rs=bind([fill()]);ledger=el.Ledger(c);before=ledger.audit()["committed_state"]
        bad=deepcopy(rs[0]);bad["extra"]=1
        with self.assertRaises(el.LedgerError):ledger.apply_batch([rs[0],bad])
        self.assertEqual(before,ledger.audit()["committed_state"])

    def test_restated_cash_never_supplies_decision_budget(self):
        records=[fill(fee="0"),snapshot(),revision(),posting(at=10)]
        records[-1]["booking_at_us"]=8;records[-1]["booking_known_at_us"]=9
        ledger,_,_=self.ledger(records,fee="0")
        self.assertEqual(ledger.snapshot(8)["balances"]["cash_usdt"],"10000")
        b=ledger.restated(8,10)["balances"]
        self.assertEqual(b["cash_usdt"],"9999.95")
        self.assertIsNone(b["simulated_budget_usdt"]);self.assertFalse(b["new_risk_supported"])

    def test_missing_snapshot_stale_mark_unknown_reserves_and_no_event(self):
        expected=[dict(instrument_id=BTC,event_id="fund",snapshot_at_us=8,mapping_rule_id=rid("funding"))]
        ledger,_,_=self.ledger([reserves(),fill(fee="0"),mark(at=1,price="49900")],fee="0",calendar=expected)
        state=ledger.snapshot(8)
        self.assertEqual(state["coverage_issues"][0]["reason_code"],"MISSING_EXPECTED_SNAPSHOT")
        self.assertIsNone(state["balances"]["liabilities_usdt"])
        ledger,_,_=self.ledger([fill(fee="0"),mark(at=1,price="49900")],fee="0")
        self.assertEqual(ledger.snapshot(102)["balances"]["null_reasons"]["unrealized_usdt"],"STALE_VALUATION")
        self.assertEqual(ledger.snapshot(1)["balances"]["null_reasons"]["simulated_budget_usdt"],"UNKNOWN_RESERVES")
        ledger,_,_=self.ledger([reserves(),fill(fee="0"),fill("close",2,-10,"49900",fee="0")],fee="0")
        self.assertEqual(ledger.snapshot(3)["closed_slices"][0]["funding_cash_usdt"],"0")

    def test_s02_remaining_fifo_paths_and_late_cumulative_revision(self):
        for sign in ("-",""):
            records=[fill(qty=3,price="100",fee="0"),revision("fee:open","open",sign+"0.01",2,1,2,"fee",unit(end=3)),
                fill("c1",3,-1,"100",fee="0"),fill("c2",4,-1,"100",fee="0"),fill("c3",5,-1,"100",fee="0"),
                revision("fee:open","open",sign+"0.02",6,1,3,"fee",unit(end=3))]
            ledger,_,_=self.ledger(records,fee="0")
            self.assertEqual([s["entry_fee_cash_usdt"] for s in ledger.snapshot(5)["closed_slices"]],[sign+v for v in ("0.0033","0.0034","0.0033")])
            self.assertEqual([s["entry_fee_cash_usdt"] for s in ledger.snapshot(6)["closed_slices"]],[sign+v for v in ("0.0067","0.0066","0.0067")])
            self.assertEqual(ledger.snapshot(6)["balances"]["cash_usdt"],"10000")
            alternate=records[:2]+[fill("c1",3,-2,"100",fee="0"),fill("c2",4,-1,"100",fee="0")]
            ledger,_,_=self.ledger(alternate,fee="0")
            self.assertEqual([s["entry_fee_cash_usdt"] for s in ledger.snapshot(5)["closed_slices"]],[sign+v for v in ("0.0067","0.0033")])

    def test_late_funding_and_fee_refunds_post_only_when_available(self):
        records=[reserves(),fill(fee="0"),snapshot(),revision(),posting(at=8),fill("close",9,-10,"49900",fee="0"),
            revision(total="0.02",at=20,version=2),posting("refund",amount="0.07",at=21)]
        records[-1]["corrects_posting_id"]="payment";records[-1]["null_reasons"]={}
        c,rs=bind(records,fee="0");c["initial_cash_usdt"]="1000";ledger=el.Ledger(c);ledger.apply_batch(rs)
        for t,expected in [(20,["999.95","0.07","0","1000.02"]),(21,["1000.02","0","0","1000.02"])]:
            b=ledger.snapshot(t)["balances"]
            self.assertEqual([b[k] for k in ("cash_usdt","receivables_usdt","liabilities_usdt","economic_equity_usdt")],expected)
        fee_records=[reserves(),fill(fee="0"),fill("close",9,-10,"49900",fee="0"),
            revision("fee:open","open","-0.25",10,1,2,"fee"),posting("originalfee","fee:open","-0.25",11),
            revision("fee:open","open","-0.20",20,1,3,"fee"),posting("feerefund","fee:open","0.05",21),
            revision("fee:open","open","-0.30",30,1,4,"fee"),posting("surcharge","fee:open","-0.10",31)]
        c,rs=bind(fee_records,fee="0");c["initial_cash_usdt"]="1000";ledger=el.Ledger(c);ledger.apply_batch(rs)
        for t,expected in [(20,["999.75","0.05","0","999.8"]),(21,["999.8","0","0","999.8"]),(30,["999.8","0","0.1","999.7"]),(31,["999.7","0","0","999.7"])]:
            b=ledger.snapshot(t)["balances"]
            self.assertEqual([b[k] for k in ("cash_usdt","receivables_usdt","liabilities_usdt","economic_equity_usdt")],expected)
        self.assertEqual(ledger.snapshot(31)["closed_slices"][0]["entry_fee_cash_usdt"],"-0.3")

    def test_split_payments_posting_restatement_gaps_and_cycles(self):
        records=[fill(fee="0"),snapshot(),revision(total="-0.08"),posting("p1",amount="-0.02",at=10),posting("p2",amount="-0.01",at=11)]
        ledger,rs,_=self.ledger(records,fee="0")
        o=next(o for o in ledger.snapshot(11)["obligations"] if o["kind"]=="funding")
        self.assertEqual((o["B_usdt"],o["P_usdt"]),("-0.03","-0.05"))
        before=ledger.audit();ledger.apply_batch(rs[3:]);self.assertEqual(before,ledger.audit())
        bad=deepcopy(rs[3]);bad["revision"]=2
        with self.assertRaisesRegex(el.LedgerError,"UNSUPPORTED_POSTING_RESTATEMENT"):ledger.apply_batch([bad])
        for case in ("gap","cycle"):
            bad_records=deepcopy(records)
            if case=="gap":
                bad_records[2]["revision"]=2;bad_records[2]["supersedes_revision"]=1;bad_records[2]["null_reasons"]={}
            else:
                for p,target in zip(bad_records[3:],("p2","p1")):
                    p["corrects_posting_id"]=target;p["null_reasons"]={};p["available_at_us"]=11
            c,rs=bind(bad_records,fee="0")
            with self.subTest(case=case),self.assertRaises(el.LedgerError):el.Ledger(c).apply_batch(rs)

    def test_both_boundary_policies_and_pre_snapshot_partial_fills(self):
        for tie,expected in [("snapshot_before_fills",[]),("fills_before_snapshot",[unit()])]:
            ledger,_,_=self.ledger([fill(at=8,fee="0"),snapshot(units=expected)],fee="0",tie=tie)
            o=next(o for o in ledger.snapshot(8)["obligations"] if o["kind"]=="funding")
            self.assertEqual(o["T_usdt"],"0" if not expected else None)
        records=[fill("first",7,4,fee="0"),fill("second",8,6,fee="0"),snapshot(units=[unit("first",0,4,"first")])]
        ledger,_,_=self.ledger(records,fee="0")
        self.assertEqual(ledger.snapshot(8)["lots"][1]["episode_id"],"episode:first")

    def test_budget_losses_receivables_reserves_and_stale_unknown_values(self):
        reserve=reserves();reserve.update(reserved_margin_usdt="100",reserved_fees_usdt="5")
        records=[reserve,fill("credit",1,1000,"100",fee="0"),fill("debit",2,1000,"100",fee="0"),
            revision("fee:credit","credit","20",3,1,2,"fee",unit("credit",0,1000,"credit")),
            revision("fee:debit","debit","-30",3,2,2,"fee",unit("debit",0,1000,"credit")),
            mark("m0",3,"100"),mark("mplus",5,"125"),mark("mminus",6,"80"),
            posting("paiddebit","fee:debit","-30",7,unit("debit",0,1000,"credit"))]
        c,rs=bind(records,fee="0");c["initial_cash_usdt"]="1000";ledger=el.Ledger(c);ledger.apply_batch(rs)
        for t,budget in [(4,"865"),(5,"865"),(6,"825"),(7,"825")]:
            self.assertEqual(ledger.snapshot(t)["balances"]["simulated_budget_usdt"],budget)
        b=ledger.snapshot(7)["balances"]
        self.assertEqual(b["cash_usdt"],"970");self.assertEqual(b["receivables_usdt"],"20")
        self.assertIsNone(b["actual_available_margin_usdt"])

    def test_unqualified_mapping_and_null_authority_do_not_hard_stop(self):
        records=[fill(fee="0"),snapshot(mapping=False),revision(),fill("close",9,-10,"49900",fee="0"),posting()]
        ledger,_,_=self.ledger(records,fee="0")
        self.assertEqual(ledger.readiness("episode:open",10)["status"],"immature")
        self.assertEqual(ledger.snapshot(10)["coverage_issues"][0]["reason_code"],"UNRESOLVED_SNAPSHOT_MAPPING")
        records=[fill(fee="0"),snapshot(),revision(),posting(at=8),fill("close",9,-10,"49900",fee="0"),assertion(),assertion(20,2)]
        records[-2]["authority_id"]=None;records[-2]["null_reasons"]["authority_id"]="UNKNOWN_FINALITY"
        ledger,_,_=self.ledger(records,fee="0")
        self.assertEqual(ledger.readiness("episode:open",10)["status"],"invalid")
        self.assertEqual(ledger.readiness("episode:open",20)["status"],"complete")
        self.assertEqual(ledger.audit()["integrity"],"clean")

    def test_scoped_cross_coin_posting_and_assertion_references_reject(self):
        records=[fill("btc",fee="0"),fill("eth",fee="0",inst=ETH),posting("cross","fee:btc","-1",2,unit("btc",0,10,"btc"),ETH)]
        c,rs=bind(records,fee="0",instruments=(BTC,ETH));ledger=el.Ledger(c);before=ledger.audit()["committed_state"]
        with self.assertRaisesRegex(el.LedgerError,"REFERENCE_SCOPE_MISMATCH"):ledger.apply_batch(rs)
        self.assertEqual(before,ledger.audit()["committed_state"])

    def test_strict_shapes_null_reasons_types_and_source_binding(self):
        prototypes=[fill(),snapshot(),revision(),posting(),reserves(),mark(),assertion()]
        for original in prototypes:
            for field in ("namespace","schema_version","record_type","record_id","revision","instrument_id","source_refs","null_reasons"):
                for value in ([],{},True,1.5,None):
                    if value==original[field] and type(value)==type(original[field]):continue
                    bad=deepcopy(original);bad[field]=value
                    with self.subTest(typ=original["record_type"],field=field,value=value),self.assertRaises(el.LedgerError):el.validate_record(bad)
            for field in ("created_at_us","available_at_us","trajectory_id","scenario_id"):
                bad=deepcopy(original);bad[field]=None
                with self.subTest(typ=original["record_type"],field=field),self.assertRaises(el.LedgerError):el.validate_record(bad)
        c,rs=bind([fill()]);rs[0]["source_refs"][0]["manifest_sha256"]="f"*64
        ledger=el.Ledger(c);before=ledger.audit()["committed_state"]
        with self.assertRaisesRegex(el.LedgerError,"SOURCE_HASH_MISMATCH"):ledger.apply_batch(rs)
        self.assertEqual(before,ledger.audit()["committed_state"])

    def test_exact_output_shapes_and_local_null_reason_maps(self):
        ledger,_,_=self.ledger()
        for state in (ledger.snapshot(0),ledger.snapshot(8),ledger.snapshot(10),ledger.restated(8,10)):
            self.assertEqual(set(state),set("namespace schema_version profile ledger_id trajectory_id scenario_id view as_of_us knowledge_cutoff_us causal_policy_sha256 balances lots closed_slices obligations coverage_issues null_reasons state_sha256".split()))
            self.assertEqual(state["null_reasons"],{})
            for obj in [state["balances"]]+state["obligations"]+state["closed_slices"]:
                self.assertEqual({k for k,v in obj.items() if v is None},set(obj["null_reasons"]))
            actual=deepcopy(state);sha=actual.pop("state_sha256")
            self.assertEqual(sha,wire_hash(actual))
        for e in ledger.audit()["committed_state"]["derived_entries"]:
            self.assertEqual(set(e),set("entry_id source_key transition obligation_id allocation_id episode_id economic_at_us available_at_us cash_delta_usdt pending_delta_usdt receivable_delta_usdt liability_delta_usdt realized_pnl_usdt null_reasons".split()))
            self.assertEqual({k for k,v in e.items() if v is None},set(e["null_reasons"]))

    def test_b1_entry_unknown_restore_and_separate_refund(self):
        records=[reserves(),fill(),posting("entryfee","fee:open","-0.2495",1),fill("close",9,-10,"50100"),
            posting("exitfee","fee:close","-0.2505",9),revision("fee:open","open",None,20,1,2,"fee"),
            revision("fee:open","open","-0.2",21,1,3,"fee"),posting("refund","fee:open","0.0495",22)]
        ledger,_,_=self.ledger(records)
        before=ledger.snapshot(10);unknown=ledger.snapshot(20);restored=ledger.snapshot(21);paid=ledger.snapshot(22)
        self.assertEqual(before["closed_slices"][0]["entry_fee_cash_usdt"],"-0.2495")
        sl=unknown["closed_slices"][0]
        self.assertIsNone(sl["entry_fee_cash_usdt"])
        self.assertEqual(sl["null_reasons"],{"entry_fee_cash_usdt":"UNKNOWN_OBLIGATION_TOTAL"})
        self.assertEqual([sl[k] for k in ("exit_fee_cash_usdt","funding_cash_usdt","realized_price_pnl_usdt")],["-0.2505","0","2"])
        self.assertEqual(unknown["balances"]["cash_usdt"],"10001.5")
        self.assertIsNone(unknown["balances"]["economic_equity_usdt"])
        self.assertEqual(next(o for o in unknown["obligations"] if o["obligation_id"]=="fee:open")["B_usdt"],"-0.2495")
        self.assertEqual(restored["closed_slices"][0]["entry_fee_cash_usdt"],"-0.2")
        self.assertEqual([restored["balances"][k] for k in ("cash_usdt","receivables_usdt","economic_equity_usdt")],["10001.5","0.0495","10001.5495"])
        self.assertEqual([paid["balances"][k] for k in ("cash_usdt","receivables_usdt","economic_equity_usdt")],["10001.5495","0","10001.5495"])
        self.assertEqual(ledger.snapshot(20),unknown)
        self.assertEqual(ledger.snapshot(10),before)

    def test_b1_exit_symmetric_and_both_unknown(self):
        base=[reserves(),fill(),posting("entryfee","fee:open","-0.2495",1),fill("close",9,-10,"50100"),posting("exitfee","fee:close","-0.2505",9)]
        exit_unknown=revision("fee:close","close",None,20,9,2,"fee")
        ledger,_,_=self.ledger(base+[exit_unknown,revision("fee:close","close","-0.2",21,9,3,"fee"),posting("refund","fee:close","0.0505",22)])
        sl=ledger.snapshot(20)["closed_slices"][0]
        self.assertEqual(sl["entry_fee_cash_usdt"],"-0.2495");self.assertIsNone(sl["exit_fee_cash_usdt"])
        self.assertEqual(sl["null_reasons"],{"exit_fee_cash_usdt":"UNKNOWN_OBLIGATION_TOTAL"})
        self.assertEqual(ledger.snapshot(21)["balances"]["cash_usdt"],"10001.5")
        self.assertEqual(ledger.snapshot(22)["balances"]["cash_usdt"],"10001.5505")
        ledger,_,_=self.ledger(base+[exit_unknown,revision("fee:open","open",None,20,1,2,"fee")])
        sl=ledger.snapshot(20)["closed_slices"][0]
        self.assertIsNone(sl["entry_fee_cash_usdt"]);self.assertIsNone(sl["exit_fee_cash_usdt"])
        self.assertEqual(sl["funding_cash_usdt"],"0");self.assertEqual(sl["realized_price_pnl_usdt"],"2")
        self.assertEqual(len(sl["null_reasons"]),2)

    def test_b1_all_affected_partial_slices_unknown_then_restore(self):
        records=[reserves(),fill(),posting("entryfee","fee:open","-0.2495",1),
            fill("c1",3,-6,"50100"),posting("cf1","fee:c1","-0.1503",3,unit(end=6)),
            fill("c2",4,-4,"50100"),posting("cf2","fee:c2","-0.1002",4,unit(start=6)),
            revision("fee:open","open",None,20,1,2,"fee"),revision("fee:open","open","-0.2",21,1,3,"fee")]
        ledger,_,_=self.ledger(records)
        unknown=ledger.snapshot(20)
        self.assertEqual([s["entry_fee_cash_usdt"] for s in unknown["closed_slices"]],[None,None])
        self.assertEqual([s["exit_fee_cash_usdt"] for s in unknown["closed_slices"]],["-0.1503","-0.1002"])
        self.assertEqual([s["entry_fee_cash_usdt"] for s in ledger.snapshot(21)["closed_slices"]],["-0.12","-0.08"])
        self.assertEqual(ledger.snapshot(20),unknown)
        self.assertEqual(ledger.snapshot(21)["balances"]["cash_usdt"],"10001.5")
        bad=revision("fee:open","open",None,20,1,2,"fee");bad["null_reasons"].pop("cumulative_signed_total_usdt")
        with self.assertRaisesRegex(el.LedgerError,"NULL_REASON_CONTRACT"):el.validate_record(bad)

    def test_source_corroboration_changes_audit_not_causal_state(self):
        original=fill();second=deepcopy(original)
        c,rs=bind([original,second]);ledger=el.Ledger(c);ledger.apply_batch(rs[:1])
        state=ledger.snapshot(1);audit=ledger.audit()
        receipt=ledger.apply_batch(rs[1:])
        self.assertEqual(receipt["status"],"duplicate");self.assertEqual(receipt["entries"],[])
        self.assertEqual(ledger.snapshot(1),state)
        self.assertNotEqual(ledger.audit()["committed_sha256"],audit["committed_sha256"])
        self.assertEqual(len(ledger.audit()["committed_state"]["corroborating_source_refs"]),1)

    def test_constructor_rejects_invalid_config_and_conversion(self):
        c,_=bind([])
        variants=[]
        for field,value in [("schema_version",True),("instruments",["gate:usdt:SOL_USDT"]),("allocation_quantum_usdt","0.0011"),("initial_cash_usdt",-1)]:
            bad=deepcopy(c);bad[field]=value;variants.append(bad)
        bad=deepcopy(c);first=next(r for r in bad["rules"] if r["kind"]=="multiplier")
        first["valid_to_exclusive_us"]=5;first["null_reasons"]={}
        new=deepcopy(first);new.update(rule_id="conversion",valid_from_us=5,valid_to_exclusive_us=None,null_reasons={"valid_to_exclusive_us":"OPEN_ENDED_SCENARIO"})
        new["parameters"]["base_per_contract"]="0.01";bad["rules"].append(new);variants.append(bad)
        for bad in variants:
            with self.subTest(config=bad),self.assertRaises(el.LedgerError):el.Ledger(bad)

    def test_attribution_revision_changes_for_independent_fee_updates(self):
        records=[fill(fee="0"),fill("close",3,-10,"49900",fee="0"),
            revision("fee:open","open","-0.1",5,1,2,"fee"),
            revision("fee:open","open","-0.2",6,1,3,"fee"),
            revision("fee:close","close","-0.1",7,3,2,"fee")]
        ledger,_,_=self.ledger(records,fee="0")
        a=ledger.snapshot(6)["closed_slices"][0];b=ledger.snapshot(7)["closed_slices"][0]
        self.assertNotEqual(a["attribution_revision"],b["attribution_revision"])
        self.assertEqual(a["entry_fee_cash_usdt"],b["entry_fee_cash_usdt"])
        self.assertEqual(b["exit_fee_cash_usdt"],"-0.1")


if __name__=="__main__":unittest.main()
