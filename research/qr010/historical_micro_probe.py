"""Bounded anonymous historical-data probe; never imports the trading app.

CLI: plan, fetch --ids ID,..., inspect. Research only; no background collection,
credentials, fitting, order submission, implicit retries or redirects.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import heapq
import json
from pathlib import Path
from collections import Counter, OrderedDict
import resource
import signal
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

MIB = 1024**2
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "research/.data/qr010/historical-micro"
LIMITS = dict(requests=48, received_bytes=1024*MIB, object_bytes=128*MIB,
              disk_bytes=2048*MIB, decompressed_bytes=256*MIB,
              request_seconds=60, active_seconds=1200, rss_bytes=512*MIB)
DATES = ("2023010100", "2024070100", "2026090100")
SYMBOLS = ("BTC_USDT", "ETH_USDT")


class ProbeError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json_bytes(value))


def allowed_url(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.username or u.password or u.port:
        return False
    if u.hostname == "download.gatedata.org":
        return u.path.startswith("/futures_usdt/") and not u.query
    if u.hostname == "api.gateio.ws":
        return u.path in ["/api/v4/futures/usdt/contracts/"+s for s in SYMBOLS] and not u.query
    if u.hostname in {"hyperliquid-archive.s3.amazonaws.com",
                       "hl-mainnet-node-data.s3.amazonaws.com"}:
        return set(urllib.parse.parse_qs(u.query)) <= {"list-type", "prefix", "max-keys"}
    return False


def build_plan():
    requests = []

    def add(method, url, kind, symbol, stamp, cap):
        assert allowed_url(url)
        requests.append(dict(id=f"R{len(requests)+1:02}", method=method, url=url,
                             kind=kind, symbol=symbol, representative_utc=stamp,
                             max_body_bytes=cap))
    for stamp in DATES:
        for symbol in SYMBOLS:
            base = "https://download.gatedata.org/futures_usdt/"
            book = base+f"orderbooks/{stamp[:6]}/{symbol}-{stamp}.csv.gz"
            snap = base+f"orderbooks_slice/{stamp[:6]}/{symbol}-{stamp}.gz"
            trades = base+f"trades/{stamp[:6]}/{symbol}-{stamp[:6]}.csv.gz"
            add("HEAD", book, "orderbooks", symbol, stamp, 0)
            add("GET", book, "orderbooks", symbol, stamp, 32*MIB)
            add("GET", snap, "orderbooks_slice", symbol, stamp, 16*MIB)
            add("HEAD", trades, "trades", symbol, stamp, 0)
            add("GET", trades, "trades", symbol, stamp, 2*MIB)
    for stamp in DATES:
        for symbol in SYMBOLS:
            coin = symbol.split("_")[0]
            url = f"https://hyperliquid-archive.s3.amazonaws.com/market_data/{stamp[:8]}/0/l2Book/{coin}.lz4"
            add("GET", url, "hl_l2_anonymous", coin, stamp, 64*1024)
    for prefix in ("node_fills_by_block/", "node_trades/"):
        url = "https://hl-mainnet-node-data.s3.amazonaws.com/?"+urllib.parse.urlencode(
            {"list-type": "2", "prefix": prefix, "max-keys": "1"})
        add("GET", url, "hl_anonymous_listing", "BTC_ETH_SCOPE_ONLY", None, 64*1024)
    for symbol in SYMBOLS:
        add("GET", "https://api.gateio.ws/api/v4/futures/usdt/contracts/"+symbol,
            "current_public_metadata_not_historical", symbol, None, 128*1024)
    return dict(schema_version=1, task_id="QF-QR-010-HISTORICAL-MICRO",
                created_at_utc=utc_now(), base_commit="a9815031a75510ac0473f75bd27941fe55fbad44",
                target_interval_utc=["2023-01-01T00:00:00Z", "2026-10-01T00:00:00Z"],
                selection="Fixed calendar early/middle/recent month-start UTC hour; no PnL selection",
                limits=LIMITS, requests=requests, reserved_amendments=8,
                amendment_rule="Append exact public BTC/ETH URL and cap before request; same hard global limits; no auth/payment",
                documentation_requests_separate=True,
                credentials=False, requester_pays=False, redirects=False, retries=False)


def ensure_data_root():
    if not subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q",
                           str(DATA/"probe.json")]).returncode == 0:
        raise ProbeError("Research data root must already be ignored")
    DATA.mkdir(parents=True, exist_ok=True)


def rss_bytes():
    n = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(n if sys.platform == "darwin" else n*1024)


def usage(root):
    receipts = [json.loads(p.read_text()) for p in sorted((root/"receipts").glob("*.json"))]
    ops = [json.loads(p.read_text()) for p in sorted((root/"operations").glob("*.json"))]
    return dict(requests=len(receipts), received_bytes=sum(r["body_bytes"]+r.get("header_bytes", 0) for r in receipts),
                active_seconds=sum(r["elapsed_seconds"] for r in receipts+ops),
                disk_bytes=sum(p.stat().st_size for p in root.rglob("*") if p.is_file()))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def anonymous_opener():
    # Empty proxy map, no cookie/auth handlers or AWS SDK/credential chain.
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    return urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                      urllib.request.HTTPSHandler(context=ctx), NoRedirect())


def transport_complete(status, headers, received, stopped):
    if stopped or status not in (200, 206):
        return False
    length = headers.get("content-length")
    if length is None or received != int(length):
        return False  # unknown/chunked EOF is conservatively not promoted
    if status == 200:
        return True
    import re
    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", headers.get("content-range", ""))
    return bool(match and int(match[1]) == 0 and int(match[2])+1 == int(match[3])
                and received == int(match[3]))


def fetch_one(item, root=DATA, opener=None):
    if not allowed_url(item["url"]) or item["method"] not in ("GET", "HEAD"):
        raise ProbeError("URL/method outside public allowlist")
    receipt_path = root/"receipts"/(item["id"]+".json")
    if receipt_path.exists() or (root/"raw"/(item["id"]+".bin")).exists():
        raise ProbeError("Request ID already used; preserve evidence")
    before = usage(root)
    if before["requests"] >= LIMITS["requests"] or before["active_seconds"] >= LIMITS["active_seconds"]:
        raise ProbeError("Request/time budget exhausted")
    cap = min(item["max_body_bytes"], LIMITS["object_bytes"],
              LIMITS["received_bytes"]-before["received_bytes"],
              LIMITS["disk_bytes"]-before["disk_bytes"]-MIB)
    if cap < 0 or (item["method"] == "GET" and cap == 0):
        raise ProbeError("Byte/disk budget exhausted")
    start = time.monotonic()
    deadline = start + min(LIMITS["request_seconds"], LIMITS["active_seconds"]-before["active_seconds"])

    def guard(*_):
        if time.monotonic() >= deadline:
            raise ProbeError("REQUEST_DEADLINE")
        if rss_bytes() > LIMITS["rss_bytes"]:
            raise ProbeError("RSS_LIMIT")

    headers = {"User-Agent": "QR010-public-history-research/1", "Accept-Encoding": "identity"}
    if item["method"] == "GET":
        headers["Range"] = f"bytes=0-{cap-1}"
    r = dict(request=item, requested_at_utc=utc_now(), status=None, response_headers={},
             body_bytes=0, header_bytes=0, stopped=None, error=None, complete_transport=False,
             historical_receive_clock_available=False)
    raw = root/"raw"/(item["id"]+".bin")
    raw.parent.mkdir(parents=True, exist_ok=True)
    previous = signal.signal(signal.SIGALRM, guard)
    signal.setitimer(signal.ITIMER_REAL, 0.1, 0.1)
    digest = hashlib.sha256()
    try:
        req = urllib.request.Request(item["url"], headers=headers, method=item["method"])
        try:
            response = (opener or anonymous_opener()).open(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc  # preserve status and bounded public error body
        with contextlib.closing(response), raw.open("xb") as out:
            r["status"] = response.code
            r["response_headers"] = {k.lower(): v for k,v in response.headers.items()}
            r["header_bytes"] = len(str(response.headers).encode())
            cap = max(0, min(cap, LIMITS["received_bytes"]-before["received_bytes"]-r["header_bytes"]))
            if response.code not in (200,206):
                cap = min(cap, 64*1024)
            while item["method"] != "HEAD" and r["body_bytes"] < cap:
                guard()
                chunk = response.read(min(64*1024, cap-r["body_bytes"]))
                if not chunk:
                    break
                out.write(chunk); digest.update(chunk); r["body_bytes"] += len(chunk)
            if item["method"] != "HEAD" and r["body_bytes"] == cap:
                length = r["response_headers"].get("content-length")
                if length is None or int(length) != r["body_bytes"]:
                    r["stopped"] = "BODY_CAP"
            r["complete_transport"] = item["method"] == "GET" and transport_complete(
                r["status"], r["response_headers"], r["body_bytes"], r["stopped"])
    except (OSError, ValueError, ProbeError) as exc:
        r["error"] = f"{type(exc).__name__}: {exc}"
        r["stopped"] = r["stopped"] or "REQUEST_ERROR"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        r.update(completed_at_utc=utc_now(), elapsed_seconds=round(time.monotonic()-start, 6),
                 peak_rss_bytes=rss_bytes(), raw_path=str(raw.relative_to(root)) if raw.exists() else None,
                 sha256=digest.hexdigest() if raw.exists() else None,
                 range_requested=headers.get("Range"), plan_sha256=sha((root/"request-plan.json").read_bytes()))
        write_new(receipt_path, r)
    return r


def gzip_chunks(path, max_output=256*MIB):
    """Yield bounded decompressed chunks; caller inspects terminal state.

    Retains complete lines from truncated prefixes; never labels them full gzip.
    No unconstrained zlib flush/decompress allocation. Multiple members rejected.
    """
    d = zlib.decompressobj(16+zlib.MAX_WBITS)
    total = 0
    with path.open("rb") as f:
        for compressed in iter(lambda:f.read(64*1024), b""):
            tail = compressed
            while tail:
                if total >= max_output:
                    raise ProbeError("DECOMPRESSED_CAP")
                out = d.decompress(tail, min(64*1024, max_output-total))
                total += len(out)
                tail = d.unconsumed_tail
                if out:
                    yield out
                if d.eof and (d.unused_data or f.peek(1)):
                    raise ProbeError("TRAILING_OR_MULTIMEMBER_GZIP")
    if not d.eof:
        raise ProbeError("TRUNCATED_GZIP")


def inspect_prefix(receipt, root=DATA):
    path = root/receipt["raw_path"]
    lines, pending, count, output, error = [], b"", 0, 0, None
    deadline = time.monotonic()+max(0, LIMITS["active_seconds"]-usage(root)["active_seconds"])
    try:
        for chunk in gzip_chunks(path):
            if time.monotonic() >= deadline or rss_bytes() > LIMITS["rss_bytes"]:
                raise ProbeError("PARSE_TIME_OR_RSS_LIMIT")
            output += len(chunk)
            pending += chunk
            split = pending.split(b"\n")
            pending = split.pop()
            count += len(split)
            if len(lines) < 4:
                lines.extend(x[:1600].decode("utf-8", "replace") for x in split[:4-len(lines)])
            if len(pending) > 8*MIB:
                raise ProbeError("LINE_CAP")
    except (ProbeError, zlib.error) as exc:
        error = str(exc)
    return dict(id=receipt["request"]["id"], decompressed_bytes=output,
                complete_lines=count, trailing_line_bytes=len(pending),
                preview=lines, gzip_error=error, gzip_complete=error is None)


def decimal(value):
    if isinstance(value, (float, bool)):
        raise ProbeError("FLOAT_OR_BOOL_INPUT")
    x = Decimal(value)
    if not x.is_finite():
        raise ProbeError("NONFINITE")
    return x


def text_decimal(x):
    return None if x is None else format(x, "f")


def gzip_lines(path, audit, deadline):
    pending = b""
    audit.update(decompressed_bytes=0, physical_lines=0, blank_lines=0,
                 gzip_complete=False, gzip_error=None, trailing_line_bytes=0)
    try:
        for block in gzip_chunks(path, LIMITS["decompressed_bytes"]):
            if time.monotonic() >= deadline or rss_bytes() > LIMITS["rss_bytes"]:
                raise ProbeError("PARSE_TIME_OR_RSS_LIMIT")
            audit["decompressed_bytes"] += len(block)
            pending += block
            lines = pending.split(b"\n"); pending = lines.pop()
            for line in lines:
                audit["physical_lines"] += 1
                if not line.strip():
                    audit["blank_lines"] += 1
                    continue
                yield audit["physical_lines"], line.decode("utf-8")
            if len(pending) > 8*MIB:
                raise ProbeError("LINE_CAP")
        audit["gzip_complete"] = True
    except (ProbeError, zlib.error, UnicodeDecodeError) as exc:
        audit["gzip_error"] = str(exc)
    audit["trailing_line_bytes"] = len(pending)
    # A truncated final row is never emitted as a record.


def parse_snapshot(text):
    x = json.loads(text, parse_float=Decimal, parse_int=Decimal)
    current, update = decimal(x["current"]), decimal(x["update"])
    ident = decimal(x["id"])
    if ident != ident.to_integral_value() or update > current:
        raise ProbeError("SNAPSHOT_CLOCK_OR_ID")
    result = dict(id=int(ident), current=current, update=update)
    for side in ("bids", "asks"):
        if not isinstance(x[side], list) or len(x[side])>1000:
            raise ProbeError("SNAPSHOT_DEPTH_CAP")
        values = [(decimal(v["p"]), decimal(v["s"])) for v in x[side]]
        if not values or any(p<=0 or q<0 for p,q in values):
            raise ProbeError("INVALID_BOOK_PRICE_OR_SIZE")
        prices = [p for p,_ in values]
        if len(set(prices)) != len(prices) or prices != sorted(prices, reverse=side=="bids"):
            raise ProbeError("UNSORTED_OR_DUPLICATE_LEVEL")
        result[side] = values
    if result["bids"][0][0] >= result["asks"][0][0]:
        raise ProbeError("CROSSED_SNAPSHOT")
    return result


class LevelBook:
    """Archive set + signed make/take delta candidate, checked against snapshots.

    No order IDs or queue inference. A make/take row spans merged source IDs;
    interior source states cannot be reconstructed from its aggregate quantity.
    """
    def __init__(self):
        self.levels = {"bids":{}, "asks":{}}
        self.heaps = {"bids":[], "asks":[]}
        self.in_heap = {"bids":set(), "asks":set()}
        self.cursor = None
        self.in_initial = True
        self.clean = True

    def apply(self, action, price, signed_size, begin, merged):
        if price<=0 or signed_size==0 or action not in {"set","make","take"}:
            raise ProbeError("INVALID_DELTA")
        side = "bids" if signed_size>0 else "asks"
        size = abs(signed_size)
        if action == "set":
            if not self.in_initial or merged!=0 or (self.cursor is not None and begin!=self.cursor):
                raise ProbeError("INVALID_INITIAL_SNAPSHOT")
            if price in self.levels[side]:
                raise ProbeError("DUPLICATE_INITIAL_PRICE")
            self.cursor = begin
            updated = size
        else:
            if self.cursor is None or merged<1 or begin!=self.cursor+1:
                self.clean=False
                raise ProbeError("SEQUENCE_GAP_OR_OVERLAP")
            self.in_initial = False
            self.cursor=begin+merged-1
            updated=self.levels[side].get(price, Decimal(0)) + (size if action=="make" else -size)
            if updated<0:
                self.clean=False
                raise ProbeError("NEGATIVE_RECONSTRUCTED_SIZE")
        if updated:
            self.levels[side][price]=updated
            key=-price if side=="bids" else price
            if key not in self.in_heap[side]:
                heapq.heappush(self.heaps[side],key);self.in_heap[side].add(key)
        else:
            self.levels[side].pop(price,None)

    def top(self, side, n=10):
        found=[];held=[]
        heap=self.heaps[side]
        while heap and len(found)<n:
            key=heapq.heappop(heap);price=-key if side=="bids" else key
            size=self.levels[side].get(price)
            if size:
                found.append((price,size));held.append(key)
            else:
                self.in_heap[side].remove(key)
        for key in held:heapq.heappush(heap,key)
        return found


class DeltaDuplicates:
    """Finite corroboration cache. Older unprovable repeats fail sequence checks."""
    def __init__(self, capacity=50000):
        self.capacity=capacity
        self.rows=OrderedDict()

    def observe(self, begin, text, line):
        if begin in self.rows:
            old,origin=self.rows[begin]
            if old!=text:raise ProbeError("CONFLICTING_DELTA_ID")
            return origin
        self.rows[begin]=(text,line)
        if len(self.rows)>self.capacity:self.rows.popitem(last=False)
        return None


def book_features(snapshot, previous=None):
    bid,ask=snapshot["bids"],snapshot["asks"]
    if len(bid)<5 or len(ask)<5 or any(q<=0 for _,q in bid+ask):
        raise ProbeError("NONPOSITIVE_OR_SHALLOW_SNAPSHOT")
    bp,bq=bid[0];ap,aq=ask[0]
    if bp>=ap:raise ProbeError("CROSSED_SNAPSHOT")
    bd=sum(q for _,q in bid[:5]);ad=sum(q for _,q in ask[:5])
    ofi=None
    if previous and Decimal(0)<snapshot["current"]-previous["current"]<=2:
        pb,pbq=previous["bids"][0];pa,paq=previous["asks"][0]
        ofi=(int(bp>=pb)*bq-int(bp<=pb)*pbq)-(int(ap<=pa)*aq-int(ap>=pa)*paq)
    return dict(source_current_s=text_decimal(snapshot["current"]),
                source_update_s=text_decimal(snapshot["update"]), historical_receive_at=None,
                historical_available_at=None, snapshot_id=snapshot["id"],
                spread_bps=text_decimal((ap-bp)*20000/(ap+bp)),
                bid_depth5_contracts=text_decimal(bd),ask_depth5_contracts=text_decimal(ad),
                depth_imbalance5=text_decimal((bd-ad)/(bd+ad)),
                observed_ofi_contracts=text_decimal(ofi),
                ofi_scope="adjacent qualified snapshots <=2s; sampled proxy, not L3 flow",
                quality="RETROSPECTIVE_STRUCTURAL_ONLY_NOT_HISTORICAL_PIT")


def analyze_pair(book_receipt, snap_receipt, output, root=DATA):
    before=usage(root);start=time.monotonic()
    code_hash=sha(Path(__file__).read_bytes())
    deadline=start+max(0,LIMITS["active_seconds"]-before["active_seconds"])
    snapshots=[];sa={};counts=Counter();bad=[];prior=None
    for line,text in gzip_lines(root/snap_receipt["raw_path"],sa,deadline):
        try:
            s=parse_snapshot(text);s["source_line"]=line
            if prior and (s["id"]<=prior["id"] or s["current"]<prior["current"]):
                counts["snapshot_nonmonotone_or_duplicate"]+=1
            if prior:counts["snapshot_gaps_over_2s"]+=int(s["current"]-prior["current"]>2)
            counts["snapshot_zero_quantity_levels"]+=sum(q==0 for _,q in s["bids"]+s["asks"])
            if len(snapshots)>=20000:raise ProbeError("SNAPSHOT_COUNT_CAP")
            snapshots.append(s);prior=s
        except (ProbeError,ValueError,KeyError,InvalidOperation) as exc:
            counts["invalid_snapshots"]+=1
            if len(bad)<5:bad.append(dict(line=line,error=str(exc)))
    if len(snapshots)>20000:raise ProbeError("SNAPSHOT_COUNT_CAP")
    book=LevelBook();ba={};first_ts=last_ts=None;si=0;last_group=None;prior_feature=None
    duplicates=DeltaDuplicates();duplicate_examples=[]
    t0=Decimal(int(datetime.strptime(book_receipt["request"]["representative_utc"],"%Y%m%d%H").replace(tzinfo=timezone.utc).timestamp()))
    features_path=output/"book-features.jsonl"; features_path.parent.mkdir(parents=True,exist_ok=True)
    matches=[];mismatches=[];errors=[];first_bad_line=None
    def compare_snapshot(s,line,out):
        nonlocal prior_feature
        actual={side:book.top(side,len(s[side])) for side in ("bids","asks")}
        exact=all(actual[side]==s[side] for side in actual)
        prices=all([p for p,q in actual[side]]==[p for p,q in s[side]] for side in actual)
        truncated=prices and all(int(aq)==sq for side in actual for (_,aq),(_,sq) in zip(actual[side],s[side]))
        counts["snapshot_at_exact_merged_boundary"]+=1
        counts["exact_top10_matches"]+=int(exact)
        counts["price_ladder_matches"]+=int(prices)
        counts["integer_truncation_compatible_matches"]+=int(truncated)
        record=dict(snapshot_id=s["id"],snapshot_line=s["source_line"],book_line=line,
                    source_current_s=text_decimal(s["current"]),exact=exact,
                    price_ladder=prices,truncation_compatible=truncated)
        if exact and len(matches)<5:matches.append(record)
        if not exact and len(mismatches)<5:
            record["first_level_differences"]=[dict(side=side,archive_p=text_decimal(p),archive_q=text_decimal(q),
                   reconstructed_q=text_decimal(book.levels[side].get(p,Decimal(0))))
                   for side in ("bids","asks") for p,q in s[side]
                   if book.levels[side].get(p,Decimal(0))!=q][:5]
            mismatches.append(record)
        if exact and book.clean:
            try:
                f=book_features(s,prior_feature);prior_feature=s
                f.update(raw_book_id=book_receipt["request"]["id"],raw_book_sha256=book_receipt["sha256"],
                         raw_snapshot_id=snap_receipt["request"]["id"],raw_snapshot_sha256=snap_receipt["sha256"],
                         snapshot_line=s["source_line"],book_line=line)
                out.write(json.dumps(f,sort_keys=True).encode()+b"\n");counts["structural_feature_rows"]+=1
            except ProbeError:prior_feature=None;counts["feature_rejected"]+=1
        else:prior_feature=None
    with features_path.open("xb") as out:
        for line,text in gzip_lines(root/book_receipt["raw_path"],ba,deadline):
            counts["book_rows"]+=1
            try:
                row=text.split(",")
                if len(row)!=6:raise ProbeError("DELTA_FIELD_COUNT")
                ts,action,price,q,begin,n=row
                ts=decimal(ts);price=decimal(price);q=decimal(q);begin=int(begin);n=int(n)
                counts["action_"+action]+=1;counts["fractional_size_rows"]+=int(q!=q.to_integral_value())
                if last_ts is not None and ts<last_ts:counts["time_reversals"]+=1
                first_ts=ts if first_ts is None else min(first_ts,ts);last_ts=ts
                counts["rows_at_hour_exclusive_end"]+=int(ts==t0+3600)
                counts["rows_outside_hour_beyond_endpoint"]+=int(ts<t0 or ts>t0+3600)
                if action!="set":
                    origin=duplicates.observe(begin,text,line)
                    if origin is not None:
                        counts["duplicate_identical_delta_rows"]+=1
                        if len(duplicate_examples)<5:duplicate_examples.append(dict(original_line=origin,duplicate_line=line,begin_id=begin,raw=text))
                        continue
                if last_group is not None and ts<last_group:counts["normalized_time_reversals"]+=1
                if last_group is not None and ts!=last_group and book.clean:
                    bb,aa=book.top("bids",1),book.top("asks",1)
                    if not bb or not aa or bb[0][0]>=aa[0][0]:counts["crossed_or_empty_timestamp_end"]+=1
                last_group=ts
                if first_bad_line is not None:continue
                # A merged row cannot reconstruct a snapshot inside its ID span.
                if action!="set":
                    while si<len(snapshots) and snapshots[si]["id"]<begin:
                        s=snapshots[si];si+=1
                        if s["id"]==book.cursor:compare_snapshot(s,line-1,out)
                        else:counts["snapshot_unbridgeable"]+=1;prior_feature=None
                book.apply(action,price,q,begin,n)
                if action!="set":
                    while si<len(snapshots) and snapshots[si]["id"]<=book.cursor:
                        s=snapshots[si];si+=1
                        if s["id"]==book.cursor:compare_snapshot(s,line,out)
                        else:counts["snapshot_inside_merged_span"]+=1;prior_feature=None
            except (ProbeError,ValueError,InvalidOperation) as exc:
                counts["reconstruction_errors"]+=1
                if first_bad_line is None:first_bad_line=line
                if len(errors)<5:errors.append(dict(line=line,error=str(exc),raw=text))
    counts["snapshots_remaining_unbridged"]=len(snapshots)-si
    result=dict(probe_code_sha256=code_hash,book_id=book_receipt["request"]["id"],snapshot_id=snap_receipt["request"]["id"],
                symbol=book_receipt["request"]["symbol"],representative_utc=book_receipt["request"]["representative_utc"],
                book_gzip=ba,snapshot_gzip=sa,counts=dict(counts),
                book_first_event_s=text_decimal(first_ts),book_last_event_s=text_decimal(last_ts),
                snapshot_first_current_s=text_decimal(snapshots[0]["current"]) if snapshots else None,
                snapshot_last_current_s=text_decimal(snapshots[-1]["current"]) if snapshots else None,
                first_bad_book_line=first_bad_line,invalid_snapshot_examples=bad,
                reconstruction_errors=errors,duplicate_examples=duplicate_examples,
                exact_match_examples=matches,mismatch_examples=mismatches,
                source_mapping="Official Gate archive set/make/take + begin-id/merged-count; aggregate-delta reconstruction tested against snapshot IDs",
                historical_pit_qualified=False, feature_path=str(features_path.relative_to(root)),
                feature_sha256=sha(features_path.read_bytes()),
                complete_raw_objects=book_receipt["complete_transport"] and snap_receipt["complete_transport"])
    write_new(output/"analysis.json",result)
    write_new(root/"operations"/(output.parent.name+"-"+output.name+"-book.json"),
              dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=rss_bytes()))
    return result


def analyze_trades(receipt, output, root=DATA):
    start=time.monotonic();deadline=start+max(0,LIMITS["active_seconds"]-usage(root)["active_seconds"])
    code_hash=sha(Path(__file__).read_bytes())
    audit={};counts=Counter();seen={};first=last=previous=None;last_id=None;minutes={};bad=[]
    stamp=receipt["request"]["representative_utc"]
    t0=Decimal(int(datetime.strptime(stamp,"%Y%m%d%H").replace(tzinfo=timezone.utc).timestamp()))
    for line,text in gzip_lines(root/receipt["raw_path"],audit,deadline):
        counts["rows"]+=1
        try:
            row=text.split(",")
            if len(row)!=4:raise ProbeError("TRADE_FIELD_COUNT")
            ts,ident,price,size=decimal(row[0]),int(row[1]),decimal(row[2]),decimal(row[3])
            if price<=0 or size==0:raise ProbeError("INVALID_TRADE_PRICE_OR_SIZE")
            semantic=(ts,price,size)
            if ident in seen:
                counts["duplicate_identical" if seen[ident]==semantic else "duplicate_conflict"]+=1
                continue
            if len(seen)>=500000:raise ProbeError("IDENTITY_MEMORY_CAP")
            seen[ident]=semantic
            if previous is not None and ts<previous:counts["time_reversals"]+=1
            if last_id is not None:
                counts["id_backward_steps"]+=int(ident<last_id)
                counts["id_missing_between_observed"]+=max(ident-last_id-1,0)
            previous=ts;last_id=ident
            first=ts if first is None else min(first,ts);last=ts if last is None else max(last,ts)
            counts["fractional_quantity_rows"]+=int(size!=size.to_integral_value())
            counts["buy_prints" if size>0 else "sell_prints"]+=1
            if t0<=ts<t0+3600:
                minute=int((ts-t0)//60)
                x=minutes.setdefault(minute,dict(first_line=line,last_line=line,buy=Decimal(0),sell=Decimal(0),
                                                buy_weighted=Decimal(0),sell_weighted=Decimal(0),prints=0))
                side="buy" if size>0 else "sell"
                x[side]+=abs(size);x[side+"_weighted"]+=abs(size)*price;x["prints"]+=1;x["last_line"]=line
        except (ProbeError,ValueError,InvalidOperation) as exc:
            counts["invalid_rows"]+=1
            if len(bad)<5:bad.append(dict(line=line,error=str(exc)))
            if str(exc)=="IDENTITY_MEMORY_CAP":
                audit["gzip_error"]="IDENTITY_MEMORY_CAP"
                break
    feature_rows=[]
    for minute,x in sorted(minutes.items()):
        covered=last is not None and last>=t0+(minute+1)*60 and not any(counts[k] for k in
            ("time_reversals","duplicate_conflict","invalid_rows","id_backward_steps","id_missing_between_observed"))
        denom=x["buy_weighted"]+x["sell_weighted"]
        feature_rows.append(dict(minute_start_s=str(t0+minute*60),minute_end_s=str(t0+(minute+1)*60),
            raw_id=receipt["request"]["id"],raw_sha256=receipt["sha256"],first_line=x["first_line"],last_line=x["last_line"],
            observed_prints=x["prints"],buy_contracts=str(x["buy"]),sell_contracts=str(x["sell"]),
            pressure_price_weighted_contract_ratio=str((x["buy_weighted"]-x["sell_weighted"])/denom) if covered and denom else None,
            prefix_extends_past_window=covered, historical_available_at=None,
            quality="RETROSPECTIVE_PREFIX_NOT_PIT_OR_MONTH_COVERAGE",
            internal_trade_flag_available=False, multiplier_conversion="withheld: no point-in-time contract metadata"))
    output.mkdir(parents=True,exist_ok=True)
    feature_path=output/"trade-minute-examples.jsonl"
    with feature_path.open("xb") as f:
        for x in feature_rows:f.write(json.dumps(x,sort_keys=True).encode()+b"\n")
    result=dict(probe_code_sha256=code_hash,id=receipt["request"]["id"],symbol=receipt["request"]["symbol"],representative_utc=stamp,
                gzip=audit,counts=dict(counts),first_event_s=text_decimal(first),last_event_s=text_decimal(last),
                full_selected_hour_in_observed_prefix=last is not None and first>=t0 and first<t0+60 and last>=t0+3600,
                month_complete=False,historical_pit_qualified=False,examples=bad,
                feature_path=str(feature_path.relative_to(root)),feature_sha256=sha(feature_path.read_bytes()))
    write_new(output/"analysis.json",result)
    write_new(root/"operations"/(output.parent.name+"-"+output.name+"-trades.json"),
              dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=rss_bytes()))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["plan", "fetch", "inspect", "analyze"])
    p.add_argument("--ids", default="")
    p.add_argument("--version", choices=["v1","v2","v3"], default="v1")
    args = p.parse_args()
    ensure_data_root()
    if args.command == "plan":
        write_new(DATA/"request-plan.json", build_plan())
        print(json.dumps({"plan":str(DATA/"request-plan.json"), "requests":40, "limits":LIMITS}))
        return
    plan = json.loads((DATA/"request-plan.json").read_text())
    chosen = args.ids.split(",")
    if not args.ids or len(set(chosen)) != len(chosen):
        raise ProbeError("Explicit unique finite IDs required")
    by_id = {r["id"]:r for r in plan["requests"]}
    if not set(chosen) <= set(by_id):
        raise ProbeError("Unplanned request")
    for ident in chosen:
        if args.command == "fetch":
            r = fetch_one(by_id[ident])
            print(json.dumps({k:r[k] for k in ("request","status","body_bytes","complete_transport","error","sha256")} ),flush=True)
        elif args.command == "inspect":
            start = time.monotonic()
            r = json.loads((DATA/"receipts"/(ident+".json")).read_text())
            result = inspect_prefix(r)
            write_new(DATA/"operations"/(ident+"-inspect.json"),
                      dict(elapsed_seconds=time.monotonic()-start, result=result, peak_rss_bytes=rss_bytes()))
            print(json.dumps(result), flush=True)
        else:
            r=json.loads((DATA/"receipts"/(ident+".json")).read_text())
            out=DATA/"derived"/args.version/ident
            if out.exists():raise ProbeError("Preserve previous analysis; new finite version required")
            if by_id[ident]["kind"]=="orderbooks":
                sid=f"R{int(ident[1:])+1:02}"
                s=json.loads((DATA/"receipts"/(sid+".json")).read_text())
                result=analyze_pair(r,s,out)
            elif by_id[ident]["kind"]=="trades":result=analyze_trades(r,out)
            else:raise ProbeError("Only frozen Gate book pairs and trade prefix analyzers are supported")
            print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
