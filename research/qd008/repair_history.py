"""Pinned, offline exact OHLCV candidate producer; no runtime consumers or downloads.

Financial decimals are strings/Fractions. Raw objects remain at their immutable
locations. A successful publication is still PENDING_INDEPENDENT_REVIEW.
"""
import argparse
import csv
import ctypes
from datetime import datetime, timezone
import fcntl
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import zlib

SPEC_COMMIT = "8b9e85e5c041fcf9167940520035693562f761ba"
SPEC_SHA = "cd0e123d019b428e7bd12754e553c0322d4aac5593537b07752bab777280bdc0"
APPROVAL_SHA = "d3eeb12d0d5348f769a9493a215eb32e2f3be40c13ed4a0eb5607e7cef9effa0"
NS = "qr008.exact-ohlcv"
DATASET = "gate-btc-eth-exact-ohlcv-v3-candidate"
POLICY = "ARCHIVE_PREFIX_REST_COMPLETE_ROWS_FROM_20251201_R1"
AGG = "UTC_EXACT_HOURLY_PARENTS_R1"
INSTRUMENTS = ("gate:usdt:BTC_USDT", "gate:usdt:ETH_USDT")
FIELDS = ("open", "high", "low", "close", "volume")
HOUR = 3_600_000_000
ROW_FIELDS = set("namespace schema_version dataset_id input_catalog_sha256 source_policy_id aggregation_version row_id content_sha256 instrument_id market price_kind interval_seconds bar_open_us bar_close_us open high low close volume_contracts research_available_at_us observed_first_available_at_us availability_basis null_reasons source_refs parent_rows source_segment".split())
ECONOMIC = tuple("instrument_id market price_kind interval_seconds bar_open_us bar_close_us open high low close volume_contracts research_available_at_us observed_first_available_at_us availability_basis null_reasons".split())
STATUS = "PENDING_INDEPENDENT_REVIEW"


class RepairError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise RepairError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def identity(value):
    return sha(canonical(value))


def strict_json(body, *, evidence_numbers=False):
    def pairs(items):
        result = dict(items)
        require(len(result) == len(items), "duplicate JSON key")
        return result
    def reject(value):
        raise RepairError("noninteger JSON number/constant: " + value)
    return json.loads(body, object_pairs_hook=pairs, parse_float=str if evidence_numbers else reject, parse_constant=reject)


def integer(value, lower=0):
    require(type(value) is int and lower <= value <= 2**63 - 1, "invalid integer")
    return value


def decimal(value, *, normalized=False, positive=False):
    pattern = r"(0|[1-9][0-9]*)(\.[0-9]*[1-9])?" if normalized else r"(0|[1-9][0-9]*)(\.[0-9]+)?"
    require(type(value) is str and len(value) <= (160 if normalized else 128)
            and re.fullmatch(pattern, value) is not None, "invalid decimal text/type")
    require(len(value.split(".")[1]) <= 64 if "." in value else True, "decimal scale exceeds64")
    result = Fraction(value)
    require(not positive or result > 0, "nonpositive price")
    return result


def fixed(value):
    """Exact terminating Fraction, including signed differences; no Decimal context."""
    value = Fraction(value)
    sign = "-" if value < 0 else ""
    numerator, denominator = abs(value.numerator), value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1; denominator //= 2
    while denominator % 5 == 0:
        fives += 1; denominator //= 5
    require(denominator == 1, "nonterminating amount")
    scale = max(twos, fives)
    numerator *= 2**(scale-twos) * 5**(scale-fives)
    digits = str(numerator).zfill(scale + 1)
    text = digits if not scale else (digits[:-scale] + "." + digits[-scale:]).rstrip("0").rstrip(".")
    return sign + text


def normalized_values(values, *, normalized=False):
    require(type(values) is dict and set(values) == set(FIELDS), "OHLCV fields")
    numbers = {k: decimal(v, normalized=normalized, positive=k != "volume") for k, v in values.items()}
    require(numbers["low"] <= min(numbers["open"], numbers["close"])
            <= max(numbers["open"], numbers["close"]) <= numbers["high"], "OHLC domain")
    return {k: fixed(numbers[k]) for k in FIELDS}


def checked_path(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink path")
    return path


def file_hash(path):
    h = hashlib.sha256()
    with checked_path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def checked_body(path, expected, size=None):
    path = checked_path(path)
    if size is not None:
        require(path.stat().st_size == size, "input size mismatch: " + str(path))
    body = path.read_bytes()
    require(sha(body) == expected, "input hash mismatch: " + str(path))
    return body


class Budget:
    def __init__(self, seconds=300, maximum=512*1024*1024):
        self.start = time.monotonic()
        self.seconds, self.maximum, self.bytes = seconds, maximum, 0

    def check(self, more=0):
        require(time.monotonic()-self.start <= self.seconds, "build time limit")
        require(self.bytes + more <= self.maximum, "output byte limit")
        self.bytes += more


def load_policy(spec_path, approval_path):
    s = strict_json(checked_body(spec_path, SPEC_SHA))
    a = strict_json(checked_body(approval_path, APPROVAL_SHA))
    require(a["status"] == "APPROVED" and a["decision_id"] == "QR008-DATA-SOURCE-1"
            and a["policy_id"] == POLICY and a["spec_commit"] == SPEC_COMMIT
            and a["spec_sha256"] == SPEC_SHA and a["scope"] == s["scope"]
            and a["approved_source_segments"] == s["source_policy"]["selection"]
            and a["approved_rule"] == s["source_policy"]["record_rule"], "approval binding")
    require(s["ohlcv_contract"]["namespace"] == NS and s["source_policy"]["id"] == POLICY
            and set(s["ohlcv_contract"]["row_fields"]) == ROW_FIELDS, "unsupported frozen contract")
    return s, a


def parse_archive(body, descriptor):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    expanded = decoder.decompress(body, descriptor["expanded_bytes"] + 1)
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            "archive incomplete/extra gzip/expansion")
    require(len(expanded) == descriptor["expanded_bytes"] and sha(expanded) == descriptor["expanded_sha256"], "expanded identity")
    lines = expanded.decode("utf-8").splitlines()
    require(len(lines) == descriptor["rows"] and len(lines) > 0, "archive row count")
    out = []
    for i, line in enumerate(lines, 1):
        columns = next(csv.reader([line], strict=True))
        require(len(columns) == 6 and re.fullmatch(r"0|[1-9][0-9]*", columns[0]) is not None, "archive physical row/schema")
        t = int(columns[0]); integer(t)
        require(t == descriptor["start"] + (i-1)*3600 and t < descriptor["end_exclusive"], "archive grid/order")
        vals = normalized_values(dict(zip(FIELDS, [columns[5], columns[3], columns[4], columns[2], columns[1]])))
        out.append(dict(timestamp=t, values=vals,
                        source_ref=dict(raw_sha256=descriptor["raw_sha256"], source_row=i)))
    require(out[-1]["timestamp"] + 3600 == descriptor["end_exclusive"], "archive missing tail")
    return out


def parse_rest(body, descriptor):
    rows = strict_json(body)
    require(type(rows) is list and len(rows) == descriptor["rows"] and rows, "REST row count")
    out = []
    for i, r in enumerate(rows, 1):
        require(type(r) is dict and set(r) == set("t o h l c v sum".split()), "REST fields")
        t = integer(r["t"])
        require(t == descriptor["start"] + (i-1)*3600 and t < descriptor["end_exclusive"], "REST grid/order")
        decimal(r["sum"])
        vals = normalized_values(dict(zip(FIELDS, [r[k] for k in ("o", "h", "l", "c", "v")])))
        out.append(dict(timestamp=t, values=vals, raw_record=r,
                        source_ref=dict(raw_sha256=descriptor["raw_sha256"], source_row=i)))
    require(out[-1]["timestamp"] + 3600 == descriptor["end_exclusive"], "REST missing tail")
    return out


def row_identity(row):
    return identity([NS, 1, DATASET, row["input_catalog_sha256"], POLICY, AGG,
                     row["instrument_id"], row["interval_seconds"], row["bar_open_us"]])


def seal(row):
    row["row_id"] = row_identity(row)
    row["content_sha256"] = identity({k: v for k, v in row.items() if k != "content_sha256"})
    return row


def validate_row(row):
    require(type(row) is dict and set(row) == ROW_FIELDS, "closed row schema")
    require(row["namespace"] == NS and type(row["schema_version"]) is int and row["schema_version"] == 1
            and row["dataset_id"] == DATASET and row["source_policy_id"] == POLICY
            and row["aggregation_version"] == AGG and row["instrument_id"] in INSTRUMENTS
            and row["market"] == "USDT_linear_perpetual" and row["price_kind"] == "TRADE", "row literals")
    seconds = integer(row["interval_seconds"])
    require(seconds in (3600,14400,86400), "row interval")
    t = integer(row["bar_open_us"])
    require(t % (seconds*1_000_000) == 0 and integer(row["bar_close_us"]) == t + seconds*1_000_000
            and integer(row["research_available_at_us"]) == row["bar_close_us"], "row clocks/alignment")
    require(row["observed_first_available_at_us"] is None and row["availability_basis"] == "BAR_CLOSE_PROXY_NOT_OBSERVED"
            and row["null_reasons"] == dict(observed_first_available_at_us="HISTORICAL_FIRST_AVAILABILITY_UNKNOWN"), "unknown availability")
    vals = {k: row["volume_contracts" if k == "volume" else k] for k in FIELDS}
    for k,v in vals.items():decimal(v, normalized=True, positive=k != "volume")
    require(normalized_values(vals, normalized=True) == vals, "row OHLC normalization")
    require(row["source_segment"] in ("ARCHIVE_PREFIX", "DECIMAL_REST_SUFFIX"), "row source segment")
    def hash_value(value):require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}",value) is not None, "invalid hash")
    for k in ("input_catalog_sha256", "row_id", "content_sha256"):hash_value(row[k])
    refs = row["source_refs"]
    require(type(refs) is list and len(refs) == seconds//3600, "source ref cardinality")
    for ref in refs:
        require(type(ref) is dict and set(ref) == {"raw_sha256","source_row"}, "source ref schema")
        hash_value(ref["raw_sha256"]); integer(ref["source_row"],1)
    parents = row["parent_rows"]
    require(type(parents) is list and len(parents) == (0 if seconds == 3600 else seconds//3600), "parent ref cardinality")
    for ref in parents:
        require(type(ref) is dict and set(ref) == {"row_id","content_sha256"}, "parent ref schema")
        for v in ref.values():hash_value(v)
    require(row["row_id"] == row_identity(row), "row ID mismatch")
    require(row["content_sha256"] == identity({k:v for k,v in row.items() if k != "content_sha256"}), "row content hash mismatch")
    return row


def hourly_row(observation, instrument, catalog_hash, cutover):
    t = observation["timestamp"]*1_000_000
    vals = normalized_values(observation["values"])
    return seal(dict(namespace=NS,schema_version=1,dataset_id=DATASET,
        input_catalog_sha256=catalog_hash,source_policy_id=POLICY,aggregation_version=AGG,
        instrument_id=instrument,market="USDT_linear_perpetual",price_kind="TRADE",
        interval_seconds=3600,bar_open_us=t,bar_close_us=t+HOUR,
        **{k:vals[k] for k in FIELDS if k != "volume"},volume_contracts=vals["volume"],
        research_available_at_us=t+HOUR,observed_first_available_at_us=None,
        availability_basis="BAR_CLOSE_PROXY_NOT_OBSERVED",
        null_reasons=dict(observed_first_available_at_us="HISTORICAL_FIRST_AVAILABILITY_UNKNOWN"),
        source_refs=[observation["source_ref"]],parent_rows=[],
        source_segment="ARCHIVE_PREFIX" if t < cutover else "DECIMAL_REST_SUFFIX"))


def combine(rows):
    return dict(open=rows[0]["open"], high=fixed(max(Fraction(r["high"]) for r in rows)),
        low=fixed(min(Fraction(r["low"]) for r in rows)), close=rows[-1]["close"],
        volume_contracts=fixed(sum((Fraction(r["volume_contracts"]) for r in rows),Fraction(0))))


def aggregate_rows(hours, seconds):
    require(type(seconds) is int and seconds in (14400,86400), "aggregate interval")
    width = seconds//3600
    require(type(hours) is list and hours and len(hours)%width == 0, "missing aggregate parents")
    first = hours[0]
    require(first["bar_open_us"] % (seconds*1_000_000) == 0, "aggregate alignment")
    for i,r in enumerate(hours):
        validate_row(r)
        require(r["interval_seconds"] == 3600 and r["bar_open_us"] == first["bar_open_us"]+i*HOUR
                and all(r[k] == first[k] for k in ("instrument_id","input_catalog_sha256")), "aggregate parent grid/identity")
    result = []
    for i in range(0,len(hours),width):
        children = hours[i:i+width]
        require(len({r["source_segment"] for r in children}) == 1, "cross-segment bucket")
        r = dict(children[0]);r.update(combine(children))
        r.update(interval_seconds=seconds,bar_close_us=children[-1]["bar_close_us"],
                 research_available_at_us=children[-1]["research_available_at_us"],
                 source_refs=[ref for child in children for ref in child["source_refs"]],
                 parent_rows=[dict(row_id=c["row_id"],content_sha256=c["content_sha256"]) for c in children])
        result.append(seal(r))
    return result


def economic_projection(rows, decision_us, end_us):
    integer(decision_us);integer(end_us)
    require(decision_us < end_us, "decision outside economic window")
    return [{k:r[k] for k in ECONOMIC} for r in rows if r["research_available_at_us"] <= decision_us]


def jsonl(rows):
    return b"".join(canonical(r)+b"\n" for r in rows)


def _fingerprints(entries, budget):
    out = []
    seen = set()
    for e in entries:
        budget.check()
        require(e["path"] not in seen, "duplicate frozen file identity")
        seen.add(e["path"])
        p = checked_path(e["path"])
        require(p.stat().st_size == e["bytes"] and file_hash(p) == e["sha256"], "frozen input changed: "+str(p))
        out.append(dict(path=e["path"],sha256=e["sha256"],bytes=e["bytes"],kind=e["kind"]))
    return out


def load_observations(spec, approval, budget):
    audit = spec["independent_audit"]
    inventory = _fingerprints(audit["files"],budget)
    by_path = {e["path"]:e for e in inventory}
    def read(path):
        e=by_path[path];return checked_body(path,e["sha256"],e["bytes"])
    v1_path = next(e["path"] for e in inventory if e["path"].endswith("qd004/history-v1/manifest.json"))
    v1 = strict_json(read(v1_path),evidence_numbers=True)
    receipts = {(r["source_id"],r["sha256"]):r for r in v1["raw_files"]}
    archive = {i:[] for i in INSTRUMENTS};rest = {i:[] for i in INSTRUMENTS}
    catalog_sources=[];bulk_raw={}
    cutover=spec["source_policy"]["cutover_us"]
    for d in audit["archive_objects"]:
        budget.check();inst="gate:usdt:"+d["instrument"];require(inst in archive,"archive instrument")
        receipt=receipts[(d["source_id"],d["raw_sha256"])]
        require(receipt["accepted"] is True and receipt["complete_object"] is True and receipt["kind"]=="candles"
                and receipt["interval_seconds"]==3600 and receipt["symbol"]==d["instrument"]
                and receipt["url"]==d["url"] and receipt["retrieved_at"]==d["retrieved_at_utc"],"archive receipt")
        rows=parse_archive(read(d["path"]),d)
        for r in rows:
            r["archive_ref"]=[d["source_id"],r["source_ref"]["source_row"],d["raw_sha256"]]
        archive[inst].extend(rows)
        catalog_sources.append(dict(role="SELECTED_ARCHIVE_PREFIX" if d["end_exclusive"]*1_000_000<=cutover else "SHADOW_ARCHIVE_SUFFIX",
            format="gzip_utf8_csv_six_physical_fields",instrument_id=inst,
            raw_descriptor=d,receipt=receipt,original_time_unit="UTC_unix_seconds",source_row_basis="one_based_physical_line"))
    confirmations=[]
    for d in audit["rest_objects"]:
        budget.check();inst="gate:usdt:"+d["instrument"];require(inst in rest,"REST instrument")
        result_path=str(Path(d["path"]).parent/"result.json")
        result=strict_json(read(result_path),evidence_numbers=True)
        receipt=next(r for r in result["attempts"] if r["request_id"]==d["request_id"] and r["sha256"]==d["raw_sha256"])
        require(receipt["http_status"]==200 and receipt["curl_exit"]==0 and not receipt["error"]
                and receipt["request_headers"].get("X-Gate-Size-Decimal")=="1"
                and receipt["url"]==d["request_url"] and receipt["received_at"]==d["received_at_utc"],"REST receipt")
        rows=parse_rest(read(d["path"]),d)
        for r in rows:r["rest_ref"]=[d["path"],r["source_ref"]["source_row"],d["raw_sha256"]]
        if d["kind"]=="bulk":
            rest[inst].extend(rows)
            for r in rows:bulk_raw[(inst,r["timestamp"])]=r["raw_record"]
        else:
            require(d["kind"]=="confirmation","REST descriptor kind")
            confirmations.extend((inst,r) for r in rows)
        catalog_sources.append(dict(role="SELECTED_DECIMAL_REST_SUFFIX" if d["kind"]=="bulk" else "CORROBORATION_ONLY",
            format="utf8_json_array",instrument_id=inst,raw_descriptor=d,receipt=receipt,
            original_time_unit="UTC_unix_seconds",source_row_basis="one_based_JSON_array_element"))
    for inst,r in confirmations:
        require(bulk_raw[(inst,r["timestamp"])]==r["raw_record"],"confirmation raw mismatch")
    differences=[];selected={}
    start,end=spec["scope"]["start_us"],spec["scope"]["end_exclusive_us"]
    for inst in INSTRUMENTS:
        ar,rr=archive[inst],rest[inst]
        require([r["timestamp"]*1_000_000 for r in ar]==list(range(start,end,HOUR)),"full archive grid")
        require([r["timestamp"]*1_000_000 for r in rr]==list(range(cutover,end,HOUR)),"full REST grid")
        symbol=inst.split(":")[-1]
        v2_path=next(e["path"] for e in inventory if e["kind"]=="v2_normalized" and e["path"].endswith(symbol+"-3600s.csv"))
        v2=csv.DictReader(io.StringIO(read(v2_path).decode()),strict=True)
        require(v2.fieldnames==["timestamp",*FIELDS,"available_at","source_id","source_row"],"v2 columns")
        for i,r in enumerate(ar,1):
            old=next(v2,None);require(old is not None,"v2 missing hour")
            require(old["timestamp"]==str(r["timestamp"]) and old["available_at"]==str(r["timestamp"]+3600)
                    and old["source_id"]==r["archive_ref"][0] and old["source_row"]==str(r["archive_ref"][1])
                    and normalized_values({k:old[k] for k in FIELDS})==r["values"],"archive/v2 row or lineage mismatch")
            r["v2_ref"]=[v2_path,i,by_path[v2_path]["sha256"]]
        amap={r["timestamp"]:r for r in ar}
        for r in rr:
            old=amap[r["timestamp"]]
            fields={k:dict(archive=old["values"][k],rest=r["values"][k],rest_minus_archive=fixed(Fraction(r["values"][k])-Fraction(old["values"][k])))
                    for k in FIELDS if old["values"][k]!=r["values"][k]}
            if fields:
                differences.append(dict(instrument=symbol,timestamp=r["timestamp"],
                    utc=datetime.fromtimestamp(r["timestamp"],timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    archive_ref=old["archive_ref"],rest_ref=r["rest_ref"],v2_ref=old["v2_ref"],fields=fields,
                    archive_ohlcv=old["values"],rest_ohlcv=r["values"],v2_ohlcv=old["values"]))
        selected[inst]=[r for r in ar if r["timestamp"]*1_000_000<cutover]+rr
    expected_keys=set(audit["differences"][0])
    require([{k:r[k] for k in expected_keys} for r in differences]==audit["differences"],"difference enumeration differs from frozen review")
    catalog=dict(namespace="qd008.exact-ohlcv-input-catalog",schema_version=1,
        specification=dict(commit=SPEC_COMMIT,sha256=SPEC_SHA),approval_sha256=APPROVAL_SHA,
        source_policy_id=POLICY,scope=spec["scope"],historical_first_availability="UNKNOWN",
        historical_revision_history="UNKNOWN",sources=catalog_sources,evidence_files=inventory)
    return catalog,selected,differences


def derive(catalog, observations, differences, scope, budget):
    catalog_hash=identity(catalog)
    payloads={"input-catalog.json":canonical(catalog)+b"\n","source-discrepancies.jsonl":jsonl(differences)}
    descriptors=[];totals={};fractional={}
    for inst in INSTRUMENTS:
        budget.check()
        hours=[hourly_row(o,inst,catalog_hash,scope["cutover_us"]) for o in observations[inst]]
        require([r["bar_open_us"] for r in hours]==list(range(scope["start_us"],scope["end_exclusive_us"],HOUR)),"selected hourly grid")
        groups={3600:hours,14400:aggregate_rows(hours,14400),86400:aggregate_rows(hours,86400)}
        four=groups[14400]
        for i,day in enumerate(groups[86400]):require(combine(four[i*6:i*6+6])==combine(hours[i*24:i*24+24]),"nested daily mismatch")
        sums={str(k):fixed(sum((Fraction(r["volume_contracts"]) for r in v),Fraction(0))) for k,v in groups.items()}
        require(len(set(sums.values()))==1,"full-period volume mismatch")
        totals[inst]=sums;fractional[inst]=sum(Fraction(r["volume_contracts"]).denominator!=1 for r in hours)
        for seconds,rows in groups.items():
            require(len(rows)==scope["expected_rows_per_instrument"][str(seconds)],"output count")
            for r in rows:validate_row(r)
            path=f"candles/{inst.split(':')[-1]}-{seconds}s.jsonl"
            body=jsonl(rows);payloads[path]=body
            descriptors.append(dict(path=path,sha256=sha(body),bytes=len(body),rows=len(rows),instrument_id=inst,
                interval_seconds=seconds,first_bar_open_us=rows[0]["bar_open_us"],last_bar_open_us=rows[-1]["bar_open_us"],
                last_bar_close_us=rows[-1]["bar_close_us"],last_bar_usable_before_cutoff=False))
    checks=dict(status="PASS_PRODUCER_RECOMPUTATION_ONLY",independent_candidate_validation="NOT_EXECUTED",
        independent_checker_commit=None,independent_checker_sha256=None,
        row_counts={e["path"]:e["rows"] for e in descriptors},full_period_volume_contracts=totals,
        fractional_hourly_volume_rows=fractional,different_hours=len(differences),
        different_fields=sum(len(d["fields"]) for d in differences),network_requests=0,model_fits=0,
        native_activation=False,historical_first_availability="UNKNOWN",historical_revision_history="UNKNOWN")
    payloads["candidate-checks.json"]=canonical(checks)+b"\n"
    return payloads,descriptors,checks


def _write_new(path, body):
    with path.open("xb") as handle:
        handle.write(body);handle.flush();os.fsync(handle.fileno())


def _rename_exclusive(source, destination):
    """Atomic kernel no-replace, including a noncooperating destination race."""
    libc=ctypes.CDLL(None,use_errno=True)
    if sys.platform=="darwin":
        call=libc.renamex_np;call.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint]
        result=call(os.fsencode(source),os.fsencode(destination),4)  # RENAME_EXCL
    elif sys.platform.startswith("linux") and hasattr(libc,"renameat2"):
        call=libc.renameat2;call.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
        result=call(-100,os.fsencode(source),-100,os.fsencode(destination),1)  # RENAME_NOREPLACE
    else:raise RepairError("atomic no-replace unsupported platform")
    require(result==0,"atomic no-replace publish failed: "+os.strerror(ctypes.get_errno()))


def verify_tree(root, payloads, manifest, budget):
    expected={**payloads,"manifest.json":canonical(manifest)+b"\n"}
    actual=set()
    directories={str(p) for rel in expected for p in Path(rel).parents if str(p)!="."}
    for path in root.rglob("*"):
        require(not path.is_symlink(),"output symlink")
        if path.is_file():actual.add(str(path.relative_to(root)))
        elif path.is_dir():require(str(path.relative_to(root)) in directories,"unexpected output directory")
    require(actual==set(expected),"output inventory mismatch")
    for relative,body in expected.items():
        budget.check()
        require((root/relative).read_bytes()==body,"output semantic/byte recomputation mismatch: "+relative)
        if relative.endswith(".jsonl"):
            for line in body.splitlines():
                r=strict_json(line)
                if relative.startswith("candles/"):validate_row(r)
        else:strict_json(body)


def publish(output_root, payloads, metadata, budget, prepublish=None):
    destination=checked_path(output_root)
    parent=destination.parent
    require(parent.is_dir() and not destination.exists(),"output root exists or parent missing")
    require(all(type(p) is str and re.fullmatch(r"[a-zA-Z0-9_./-]+",p) and not Path(p).is_absolute()
                and ".." not in Path(p).parts and str(Path(p))==p and p!="." for p in payloads),"unsafe output path")
    manifest=dict(metadata,created_at_utc=datetime.now(timezone.utc).isoformat(),status=STATUS,
        files=[dict(path=p,sha256=sha(b),bytes=len(b)) for p,b in sorted(payloads.items())])
    stage=parent/("."+destination.name+".staging-"+uuid.uuid4().hex)
    stage.mkdir()
    for relative,body in payloads.items():
        budget.check(len(body));path=stage/relative;path.parent.mkdir(parents=True,exist_ok=True);_write_new(path,body)
    body=canonical(manifest)+b"\n";budget.check(len(body));_write_new(stage/"manifest.json",body)
    verify_tree(stage,payloads,manifest,budget)
    if prepublish:prepublish()
    budget.check()
    # The permanent sidecar is never unlinked. A failed staging root is retained.
    lock_path=parent/".publication.lock"
    require(not lock_path.is_symlink(),"publication lock symlink")
    fd=os.open(lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"a+b") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        try:
            budget.check();require(not destination.exists(),"output root already published")
            _rename_exclusive(stage,destination)
        finally:fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
    return dict(root=str(destination),manifest_sha256=sha(body),bytes=budget.bytes,
                elapsed_seconds=time.monotonic()-budget.start,status=STATUS,manifest=manifest)


def build(spec_path,approval_path,output_root,builder_commit):
    budget=Budget()
    require(type(builder_commit) is str and re.fullmatch(r"[0-9a-f]{40}",builder_commit),"exact builder commit required")
    source=Path(__file__).resolve()
    destination=checked_path(output_root)
    allowed_parent=source.parents[2]/"research/.data/qd008"
    require(destination.parent==allowed_parent and destination.name in
            ("exact-ohlcv-v3-candidate","exact-ohlcv-v3-reproducibility"),"output outside two allocated roots")
    require(not list(allowed_parent.glob("."+destination.name+".staging-*")),"prior full-build attempt retained; no implicit retry")
    committed=subprocess.check_output(["git","show",builder_commit+":research/qd008/repair_history.py"],cwd=source.parents[2])
    require(committed==source.read_bytes(),"builder code differs from committed identity")
    spec,approval=load_policy(spec_path,approval_path)
    catalog,observations,differences=load_observations(spec,approval,budget)
    scope=dict(spec["scope"],cutover_us=spec["source_policy"]["cutover_us"])
    payloads,descriptors,checks=derive(catalog,observations,differences,scope,budget)
    require(sum(d["rows"] for d in descriptors)==84878 and len(differences)==4221
            and checks["different_fields"]==4222,"frozen full-build counts")
    metadata=dict(namespace=NS,schema_version=1,dataset_revision=3,dataset_id=DATASET,
        source_policy_id=POLICY,aggregation_version=AGG,specification_commit=SPEC_COMMIT,specification_sha256=SPEC_SHA,
        approval_sha256=APPROVAL_SHA,approval_decision_id=approval["decision_id"],input_catalog_sha256=identity(catalog),
        builder_commit=builder_commit,builder_sha256=sha(source.read_bytes()),scope=spec["scope"],candles=descriptors,
        source_discrepancies_sha256=sha(payloads["source-discrepancies.jsonl"]),
        normative_review=dict(commit=SPEC_COMMIT,raw_audit_script_sha256=spec["verification"]["raw_audit_script_sha256"],
            oracle_script_sha256=spec["verification"]["policy_selftest_script_sha256"]),
        independent_candidate_checker=dict(status="NOT_EXECUTED",commit=None,sha256=None),
        network_requests=0,model_fits=0,market_replays=0,labels=0,native_activation=False,
        limitations=["Retrospective source snapshot; historical first availability/revisions UNKNOWN.",
            "Bar-close research proxy, not historical PIT evidence.","Source segmentation explicitly approved; provider historical truth unproved.",
            "No funding/MARK transform, query-coverage acceptance, ledger acceptance or label/training readiness."])
    def unchanged():
        load_policy(spec_path,approval_path);_fingerprints(spec["independent_audit"]["files"],budget)
    return publish(destination,payloads,metadata,budget,unchanged)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec",required=True);p.add_argument("--approval",required=True)
    p.add_argument("--output",required=True);p.add_argument("--builder-commit",required=True)
    a=p.parse_args()
    result=build(a.spec,a.approval,a.output,a.builder_commit)
    print(json.dumps({k:v for k,v in result.items() if k!="manifest"},sort_keys=True))


if __name__=="__main__":main()
