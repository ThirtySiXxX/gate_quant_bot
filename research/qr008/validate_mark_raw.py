"""Independent streaming QR008 MARK raw audit; no point table or market queries.

Only exact adjacent four-string aliases are accepted. Gaps are reported, never
filled. Optional query checking is for explicitly supplied points/queries only.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import time

from research.qr008 import validate_exact_history as common

require = common.require
ReviewError = common.ReviewError
HANDOFF_SHA = "30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce"
RESULT_SHA = "3f601ebf45b2e97825b9c701234060a3348e47e508c28211b98572ed38f5a21e"
PLAN_SHA = "19cd063f596746696efb2cfdd308205c8fad040763d55ea02ce7a622e1531ce5"
COLLECTOR_SHA = "57c696566c5f89c1187569645c4f6dc6bba220d477a8017166c4a260f67a6cfc"
AMENDMENT_SHA = "0b33bf4272bbb87bb33d1e19fe27ab7e5a7765ddd2b98baf4a4678530bc17ece"
COVERAGE_SHA = "bed49515f4b27b0e46d112c0c313826f243053f6cc54c9a813d165de7fc8e08f"
AUTH_SHA = "831b95c025c4d7805602d9d3634961a62215458d34c6dc67c1b0df682888bb0e"
NS = "qr008.mark-archive-observation"
TIME_RE = re.compile(rb"(0|[1-9][0-9]*)(?:\.([0-9]{1,6}))?\Z", re.ASCII)
PRICE_RE = re.compile(rb"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z", re.ASCII)
SCENARIOS = {
    "MARK_ARCHIVE_DELAY60_AGE120_R1": (60_000_000, 120_000_000, 60_000_000),
    "MARK_ARCHIVE_DELAY120_AGE180_R1": (120_000_000, 180_000_000, 60_000_000),
}


def month_bounds(month):
    require(type(month) is str and re.fullmatch(r"[0-9]{6}",month),"month identity")
    y,m=int(month[:4]),int(month[4:]);require(1<=m<=12,"calendar month")
    first=datetime(y,m,1,tzinfo=timezone.utc)
    end=datetime(y+1,1,1,tzinfo=timezone.utc) if m==12 else datetime(y,m+1,1,tzinfo=timezone.utc)
    return int(first.timestamp())*common.U,int(end.timestamp())*common.U


def month_of(timestamp_us):
    return datetime.fromtimestamp(timestamp_us//common.U,timezone.utc).strftime("%Y%m")


def parse_fields(fields):
    require(len(fields)==4,"MARK requires four physical fields")
    match=TIME_RE.fullmatch(fields[0])
    require(match is not None,"MARK exact timestamp precision/type")
    fraction=match[2] or b""
    timestamp=int(match[1])*common.U+int(fraction.ljust(6,b"0"))
    require(timestamp<=2**63-1,"MARK timestamp bound")
    for price in fields[1:]:
        # No float or Decimal conversion; grammar plus nonzero digits proves >0.
        require(len(price.replace(b".",b""))<=128 and PRICE_RE.fullmatch(price),"MARK exact positive price grammar")
        dot=price.find(b".")
        require(dot<0 or len(price)-dot-1<=64,"MARK price fractional precision")
        require(bool(price.strip(b"0.")),"MARK zero price")
    return timestamp


def physical_fields(line):
    require(0<len(line)<=1024,"MARK physical line size/empty row")
    if line.endswith(b"\r"):line=line[:-1]
    if b'"' in line:
        text=next(csv.reader([line.decode("utf-8")],strict=True))
        return tuple(x.encode("utf-8") for x in text)
    return tuple(line.split(b","))


def alias_identity(symbol, raw_sha, first_row, source_rows, fields):
    instrument="gate:usdt:"+symbol
    return dict(namespace=NS,schema_version=2,instrument_id=instrument,raw_sha256=raw_sha,
                source_row=first_row,source_rows=list(source_rows),alias_count=len(source_rows)-1,
                raw_observation_text=[x.decode("utf-8") for x in fields],
                point_id=common.digest([NS,2,instrument,raw_sha,first_row]))


class HashReader:
    """Hash compressed bytes while gzip consumes them; never reread raw."""
    def __init__(self,stream):
        self.stream=stream;self.hash=hashlib.sha256();self.count=0

    def read(self,size=-1):
        body=self.stream.read(size);self.count+=len(body);self.hash.update(body)
        require(self.count<=64*1024*1024,"MARK compressed object budget")
        return body

    def tell(self):return self.count


def scan_object(stream, symbol, month, raw_sha, raw_bytes, *, chunk_bytes=1024*1024, checkpoint=None):
    """One gzip pass with CRC, bounded chunks and stable physical row references."""
    require(symbol in common.SYMBOLS and common.HEX_RE.fullmatch(raw_sha),"MARK object instrument/hash")
    require(type(chunk_bytes) is int and 1<=chunk_bytes<=1024*1024,"MARK chunk bound")
    start,end=month_bounds(month)
    require(common.START<=start<end<=common.END,"MARK month outside approved scope")
    reader=HashReader(stream);expanded_hash=hashlib.sha256();expanded_bytes=0
    physical=canonical_count=alias_count=0;first_time=last_time=None;first_text=last_text=None
    previous_fields=None;previous_time=None;primary_row=None;source_rows=[]
    aliases=[];gaps=[];counts={"60":0,"120":0,"180":0};maximum=0;pending=b""
    checkpoint={} if checkpoint is None else checkpoint

    def finish_alias():
        if len(source_rows)>1:
            aliases.append(alias_identity(symbol,raw_sha,primary_row,source_rows,previous_fields))

    def consume(line):
        nonlocal physical,canonical_count,alias_count,first_time,last_time,first_text,last_text
        nonlocal previous_fields,previous_time,primary_row,source_rows,maximum
        physical+=1
        require(physical<=8_000_000,"MARK physical row budget")
        fields=physical_fields(line);t=parse_fields(fields)
        require(start<=t<end,"MARK row month membership")
        if previous_time is not None:
            require(t>=previous_time,"MARK descending timestamp")
            if t==previous_time:
                require(fields==previous_fields,"MARK conflicting same-time raw lexemes")
                source_rows.append(physical);alias_count+=1
                require(alias_count*32<=16*1024*1024,"MARK alias audit budget")
                return
            finish_alias()
            gap=t-previous_time;maximum=max(maximum,gap)
            for seconds in (60,120,180):
                if gap>seconds*common.U:counts[str(seconds)]+=1
            if gap>60*common.U:
                gaps.append([previous_time,t,primary_row,physical])
                require(len(gaps)*128<=16*1024*1024,"MARK gap audit budget")
        else:
            first_time=t;first_text=fields[0].decode("ascii")
        canonical_count+=1;last_time=t;last_text=fields[0].decode("ascii")
        previous_fields=fields;previous_time=t;primary_row=physical;source_rows=[physical]

    with gzip.GzipFile(fileobj=reader,mode="rb") as expanded:
        while True:
            block=expanded.read(chunk_bytes)
            if not block:break
            expanded_bytes+=len(block);expanded_hash.update(block)
            require(expanded_bytes<=256*1024*1024,"MARK expanded object budget")
            lines=(pending+block).split(b"\n");pending=lines.pop()
            require(len(pending)<=1024,"MARK unterminated line budget")
            for line in lines:consume(line)
            checkpoint.update(physical_row=physical,expanded_bytes=expanded_bytes)
    if pending:consume(pending)
    require(physical>0,"MARK empty object")
    finish_alias()
    require(reader.count==raw_bytes and reader.hash.hexdigest()==raw_sha,"MARK compressed bytes/hash")
    return dict(physical_rows=physical,canonical_observations=canonical_count,alias_rows=alias_count,
                alias_groups=aliases,expanded_bytes=expanded_bytes,expanded_sha256=expanded_hash.hexdigest(),crc_complete=True,
                first_timestamp_us=first_time,last_timestamp_us=last_time,first_timestamp_text=first_text,last_timestamp_text=last_text,
                start_boundary_gap_us=first_time-start,end_boundary_gap_us=end-last_time,max_gap_us=maximum,
                gaps_gt60_us_and_source_rows=gaps,gap_counts_seconds=counts,strict_canonical_order=True,
                required_query_count=None,query_support_status="NOT_EVALUATED",point_schema_version=2,normalized_points_written=False)


def make_point(symbol, raw_sha, source_row, source_rows, fields):
    """Small explicit point for declared queries; never scans/builds a point table."""
    require(symbol in common.SYMBOLS and common.HEX_RE.fullmatch(raw_sha),"point identity")
    common.uint(source_row,positive=True)
    require(type(source_rows) is list,"alias references list")
    for row in source_rows:common.uint(row,positive=True)
    require(source_rows==list(range(source_row,source_row+len(source_rows))) and bool(source_rows),"complete alias references")
    encoded=tuple(x.encode("utf-8") for x in fields);t=parse_fields(encoded)
    point=alias_identity(symbol,raw_sha,source_row,source_rows,encoded)
    point.update(timestamp_us=t,mark_price=fields[2],price_kind="MARK",observed_available_at_us=None,
                 availability_basis="archive_publication_and_historical_receipt_unknown")
    return point


def select_mark(points, query, covered_months):
    """Optional deterministic API for an EXTERNAL frozen query; no inferred times.

    covered_months is a set of (symbol, YYYYMM) from accepted raw coverage.
    This helper's synthetic tests do not evaluate actual market query coverage.
    """
    require(type(query) is dict and set(query)=={"instrument_id","query_us","kind","price_kind","scenario_id"},"query closed fields")
    require(query["instrument_id"] in {"gate:usdt:"+s for s in common.SYMBOLS}
            and query["kind"] in {"decision","funding"} and query["price_kind"]=="MARK"
            and query["scenario_id"] in SCENARIOS,"query scope/price kind")
    q=common.uint(query["query_us"]);require(common.START<=q<common.END,"query economic cutoff")
    symbol=query["instrument_id"].rsplit(":",1)[1]
    missing=dict(status="UNAVAILABLE",mark_price=None,reason="MISSING_SOURCE_MONTH",query_us=q,point_id=None)
    if (symbol,month_of(q)) not in covered_months:return missing
    lag,source_age,available_age=SCENARIOS[query["scenario_id"]]
    chosen=None;previous=-1
    for point in points:
        require(point["instrument_id"]==query["instrument_id"] and point["price_kind"]=="MARK","point price kind/instrument")
        # Independently reconstruct the supplied identity and value from raw text.
        expected=make_point(symbol,point["raw_sha256"],point["source_row"],point["source_rows"],point["raw_observation_text"])
        require(point==expected,"declared query point differs from raw provenance")
        t=point["timestamp_us"];require(t>previous,"query points not strictly ordered");previous=t
        if t+lag<=q:chosen=point
    if chosen is None:
        return dict(missing,reason="NO_CAUSAL_FRESH_MARK")
    t=chosen["timestamp_us"]
    if (symbol,month_of(t)) not in covered_months:return missing
    if not (0<=q-t<=source_age and 0<=q-(t+lag)<=available_age):
        return dict(missing,reason="NO_CAUSAL_FRESH_MARK")
    return dict(status="AVAILABLE_SCENARIO_ONLY",mark_price=chosen["mark_price"],reason=None,query_us=q,
                point_id=chosen["point_id"],source_timestamp_us=t,available_at_us=t+lag,
                source_rows=chosen["source_rows"],observed_available_at_us=None,scenario_id=query["scenario_id"])


def fixed_queue():
    return [(f"{year}{month:02}",symbol) for year in range(2023,2027) for month in range(1,13)
            if (year,month)<(2026,10) for symbol in common.SYMBOLS]


def check_queue(items):
    require(type(items) is list and [(r["month"],r["symbol"]) for r in items]==fixed_queue(),"MARK complete fixed object queue")


def verify_raw(handoff_path, result_path, plan_path, amendment_path, checkpoint=None):
    started=time.monotonic();checkpoint={} if checkpoint is None else checkpoint
    handoff=common.loads(common.pinned(handoff_path,HANDOFF_SHA))
    result=common.loads(common.pinned(result_path,RESULT_SHA));plan=common.loads(common.pinned(plan_path,PLAN_SHA))
    common.pinned(amendment_path,AMENDMENT_SHA)
    common.pinned(Path(result_path).parent/"intake.py",COLLECTOR_SHA)
    common.pinned(Path(result_path).parent/"authorization.json",AUTH_SHA)
    common.pinned(plan["original_spec"]["path"],COVERAGE_SHA)
    require(handoff["result_sha256"]==RESULT_SHA and handoff["plan_sha256"]==PLAN_SHA
            and result["plan_sha256"]==PLAN_SHA and result["collector_sha256"]==COLLECTOR_SHA
            and result["authorization_sha256"]==AUTH_SHA,"MARK metadata pins")
    queue=fixed_queue()
    require(len(queue)==90,"MARK queue scope")
    check_queue(handoff["objects"]);check_queue(result["objects"])
    require([(r["month"],r["symbol"]) for r in plan["reuse"]]==queue[:19]
            and [(r["month"],r["symbol"]) for r in plan["fixed_remaining_gets"]]==queue[19:],"MARK inherited/remaining queues")
    require(len(result["attempts"])==71 and [(r["month"],r["symbol"]) for r in result["attempts"]]==queue[19:],"MARK actual request queue")
    for i,attempt in enumerate(result["attempts"],18):
        month,symbol=attempt["month"],attempt["symbol"]
        require(attempt["number"]==i and attempt["method"]=="GET" and attempt["retry"]==0
                and attempt["http_status"]==200 and attempt["curl_exit"]==0 and attempt["error"]==""
                and attempt["url"]==f"https://download.gatedata.org/futures_usdt/mark_prices/{month}/{symbol}-{month}.csv.gz","MARK request provenance")
    require(result["attempts_cumulative"]==handoff["cumulative_requests"]==88 and result["retries_used"]==0
            and result["inherited_attempts"]==17 and result["cumulative_active_seconds"]<=1200,"MARK cumulative resource evidence")
    objects=[];all_aliases=[];cross=[];last={};by_symbol={s:dict(objects=0,physical_rows=0,canonical_observations=0,alias_rows=0,
        compressed_bytes=0,within_month_max_gap_us=0,within_month_gaps_gt60=0,within_month_gaps_gt120=0,within_month_gaps_gt180=0) for s in common.SYMBOLS}
    for descriptor,record in zip(handoff["objects"],result["objects"]):
        month,symbol=descriptor["month"],descriptor["symbol"]
        checkpoint.update(phase="MARK gzip stream",month=month,symbol=symbol,path=descriptor["path"],raw_sha256=descriptor["sha256"],physical_row=0)
        require(record["path"]==descriptor["path"] and record["raw_sha256"]==descriptor["sha256"],"MARK handoff/result object binding")
        path=common.regular(descriptor["path"],64*1024*1024)
        require(path.stat().st_size==descriptor["bytes"],"MARK compressed size declaration")
        with path.open("rb") as stream:
            checked=scan_object(stream,symbol,month,descriptor["sha256"],descriptor["bytes"],checkpoint=checkpoint)
        # Recomputed values, not collector values, determine acceptance. This
        # comparison also detects incorrect saved collector accounting.
        require({k:v for k,v in checked.items() if k!="expanded_sha256"}==record["checks"],"independent MARK raw/collector discrepancy")
        objects.append(dict(descriptor,checks=checked))
        all_aliases.extend(dict(month=month,symbol=symbol,**a) for a in checked["alias_groups"])
        summary=by_symbol[symbol];summary["objects"]+=1;summary["compressed_bytes"]+=descriptor["bytes"]
        for key in ("physical_rows","canonical_observations","alias_rows"):summary[key]+=checked[key]
        summary["within_month_max_gap_us"]=max(summary["within_month_max_gap_us"],checked["max_gap_us"])
        for sec in (60,120,180):summary[f"within_month_gaps_gt{sec}"]+=checked["gap_counts_seconds"][str(sec)]
        if symbol in last:
            prev_month,previous=last[symbol]
            require(month_bounds(prev_month)[1]==month_bounds(month)[0] and checked["first_timestamp_us"]>previous,"MARK cross-month order/missing object")
            cross.append(dict(symbol=symbol,previous_month=prev_month,month=month,from_us=previous,
                              to_us=checked["first_timestamp_us"],gap_us=checked["first_timestamp_us"]-previous))
        last[symbol]=(month,checked["last_timestamp_us"])
        print(f"QR008 MARK {month} {symbol}: {checked['physical_rows']} rows, {checked['alias_rows']} aliases",flush=True)
    require(by_symbol==handoff["by_symbol"] and all_aliases==handoff["aliases"] and cross==handoff["cross_month_gaps"],"MARK independent aggregate/alias/boundary discrepancy")
    require(sum(r["bytes"] for r in handoff["objects"])==718396794
            and sum(x["physical_rows"] for x in by_symbol.values())==56585147 and len(all_aliases)==6,"MARK total scope")
    checkpoint["phase"]="complete"
    return dict(status="PASS_WITH_GAPS",checker_sha256=common.sha(Path(__file__).read_bytes()),common_checker_sha256=common.sha(Path(common.__file__).read_bytes()),
                handoff_sha256=HANDOFF_SHA,result_sha256=RESULT_SHA,plan_sha256=PLAN_SHA,amendment_sha256=AMENDMENT_SHA,
                objects=objects,by_symbol=by_symbol,aliases=all_aliases,cross_month_gaps=cross,
                all_gaps_gt60_count=sum(s["within_month_gaps_gt60"] for s in by_symbol.values())+sum(r["gap_us"]>60*common.U for r in cross),
                raw_objects=90,compressed_bytes=718396794,physical_rows=56585147,canonical_points_written=0,
                required_queries="NOT_EVALUATED",economic_query_gate="OPEN",training_ready=False,
                historical_first_availability="UNKNOWN",market_requests=0,model_fits=0,elapsed_seconds=round(time.monotonic()-started,3))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("handoff","result","plan","amendment","output"):parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args(argv)
    require(args.output.name in {"verification-mark-1","verification-mark-2"},"at most two explicit real-check destinations")
    require(args.output.parent.absolute()==Path(__file__).absolute().parents[1]/".data"/"qr008","audit output scope")
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();checkpoint={}
    try:
        with common.offline(),common.bounded():
            result=verify_raw(args.handoff,args.result,args.plan,args.amendment,checkpoint)
    except Exception as exc:
        result=dict(status="REVISE",error_type=type(exc).__name__,detail=str(exc),checkpoint=checkpoint,
                    elapsed_seconds=round(time.monotonic()-started,3),training_ready=False,market_requests=0,model_fits=0)
    identity=common.publish_new(args.output,"result.json",result)
    print(json.dumps(dict(status=result["status"],sha256=identity,path=str(args.output/"result.json"),detail=result.get("detail"))))
    return 0 if result["status"]=="PASS_WITH_GAPS" else 1


if __name__=="__main__":raise SystemExit(main())
