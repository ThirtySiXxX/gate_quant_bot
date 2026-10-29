"""QR012 bounded complete-object pilot. No credentials, fitting or trading.

An immutable plan precedes I/O. Anonymous range continuation requires an exact
strong ETag, S3 version ID, total length and overlapping byte check. Otherwise
the plan permits an independent full GET; a 200 is never appended as a 206 tail.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import closing
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OLD=ROOT/'research/qr010/historical_micro_probe.py'
if hashlib.sha256(OLD.read_bytes()).hexdigest()!='fa9ccfb18d316abc385ad472c7c8a1179a2d2232424be1d0a356db9cb7629b5c':
    raise RuntimeError('Frozen QR010 helper hash changed')
from research.qr010 import historical_micro_probe as p

DATA=ROOT/'research/.data/qr012/tmp'
MIB=1024**2
LIMITS=dict(requests=12,received_bytes=640*MIB,object_bytes=384*MIB,
            disk_bytes=2048*MIB,decompressed_bytes=2048*MIB,request_seconds=60,
            active_seconds=1800,rss_bytes=512*MIB,test_seconds=120,
            minimum_free_bytes=10*1024**3)
START=1788220800
END=1790812800
D=Decimal
AGGRESSOR_STATUS='UNKNOWN_ARCHIVE_TO_PUBLIC_FEED_BINDING'


def file_sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(MIB),b''):h.update(chunk)
    return h.hexdigest()


def read(path):return json.loads(path.read_text())


def usage(root=DATA):
    receipts=[read(f) for f in (root/'receipts').glob('*.json')]
    ops=[read(f) for f in (root/'operations').glob('*.json')]
    return dict(requests=len(receipts),received_bytes=sum(x['body_bytes']+x['header_bytes'] for x in receipts),
        active_seconds=sum(x['elapsed_seconds'] for x in receipts+ops),
        disk_bytes=sum(f.stat().st_size for f in root.rglob('*') if f.is_file()))


def check_resources(start,before,body=0,disk_added=0,request=False):
    if time.monotonic()-start+before['active_seconds']>=LIMITS['active_seconds']:
        raise p.ProbeError('ACTIVE_TIME_CAP')
    if request and time.monotonic()-start>=LIMITS['request_seconds']:
        raise p.ProbeError('REQUEST_TIME_CAP')
    if before['received_bytes']+body>LIMITS['received_bytes']:raise p.ProbeError('NETWORK_CAP')
    if before['disk_bytes']+disk_added>LIMITS['disk_bytes']-MIB:raise p.ProbeError('DISK_CAP')
    if p.rss_bytes()>LIMITS['rss_bytes']:raise p.ProbeError('RSS_CAP')
    if shutil.disk_usage(DATA.parent).free<LIMITS['minimum_free_bytes']:raise p.ProbeError('FREE_DISK_RESERVE')


def build_plan():
    assets=[]
    for symbol,ident in [('BTC_USDT','R25'),('ETH_USDT','R30')]:
        old=read(p.DATA/'receipts'/(ident+'.json'));h=old['response_headers']
        total=int(h['content-range'].split('/')[-1])
        assets.append(dict(symbol=symbol,url=old['request']['url'],old_id=ident,
            expected_size=total,expected_etag=h['etag'],expected_s3_version=h['x-amz-version-id'],
            prefix_path=str(p.DATA/old['raw_path']),prefix_bytes=old['body_bytes'],prefix_sha256=old['sha256'],
            requests=[dict(id=symbol+'-probe',kind='probe',method='GET',range=[0,65535],max_body_bytes=65536),
                      dict(id=symbol+'-tail',kind='tail',method='GET',range=[old['body_bytes'],total-1],max_body_bytes=total-old['body_bytes']),
                      dict(id=symbol+'-full',kind='full',method='GET',range=None,max_body_bytes=LIMITS['object_bytes'],condition='Only if probe/tail cannot be safely continued and remaining byte/time/disk budget suffices')]))
    return dict(schema_version=1,task_id='QF-QR-012-COMPLETE-TRADES',created_at_utc=p.utc_now(),
        base_commit='3b97e4f56588574e9fd7231e8ffac88c2952378f',limits=LIMITS,assets=assets,
        planned_normal_requests=4,conditional_full_requests=2,unassigned_slots=6,
        version_rule='Reuse prefix only after local SHA, exact strong ETag, S3 version, total length and first64KiB byte match; every tail response repeats version checks',
        etag_is_not_md5=True,partial_rule='Keep failed/partial bytes and receipts; never count partial as complete or reset budget',
        schema_gate='PASS_FOUR_FIELDS_TIMESTAMP_ID_PRICE_SIGNED_CONTRACTS_ON_FROZEN_PREFIX_AND_OFFICIAL_ARCHIVE_FORMAT',
        aggressor_status=AGGRESSOR_STATUS,availability_at=None,no_credentials=True,no_retries=True,no_redirects=True,
        calendar='2026-09 UTC only; no training split applied; prior QR calendar remains candidate pending user decision')


def validate_headers(item,asset,status,headers):
    length=headers.get('content-length')
    if length is None or not length.isdigit():raise p.ProbeError('MISSING_CONTENT_LENGTH')
    if item['kind']=='full':
        if status!=200 or int(length)>LIMITS['object_bytes']:raise p.ProbeError('FULL_RESPONSE_REJECTED')
        return
    begin,end=item['range']
    if status!=206 or headers.get('content-range')!=f'bytes {begin}-{end}/{asset["expected_size"]}':
        raise p.ProbeError('RANGE_RESPONSE_REJECTED')
    if int(length)!=end-begin+1:raise p.ProbeError('RANGE_LENGTH_MISMATCH')
    if not asset['expected_etag'].startswith('"') or headers.get('etag')!=asset['expected_etag']:
        raise p.ProbeError('STRONG_ETAG_MISMATCH')
    if headers.get('x-amz-version-id')!=asset['expected_s3_version']:
        raise p.ProbeError('S3_VERSION_MISMATCH')


def fetch(item,asset,root=DATA,opener=None):
    if asset['url'] not in {x['url'] for x in build_plan()['assets']}:raise p.ProbeError('UNPLANNED_URL')
    path=root/'raw'/(item['id']+'.bin');receipt=root/'receipts'/(item['id']+'.json')
    if path.exists() or receipt.exists():raise p.ProbeError('PRESERVE_REQUEST_EVIDENCE')
    before=usage(root)
    if before['requests']>=LIMITS['requests']:raise p.ProbeError('REQUEST_COUNT_CAP')
    prefix=Path(asset['prefix_path'])
    if file_sha(prefix)!=asset['prefix_sha256'] or prefix.stat().st_size!=asset['prefix_bytes']:
        raise p.ProbeError('OLD_PREFIX_HASH_MISMATCH')
    proposed=item['max_body_bytes']+(asset['prefix_bytes'] if item['kind']=='tail' else 0)
    # Refuse to start an operation whose declared maximum exceeds remaining limits.
    if before['received_bytes']+item['max_body_bytes']+65536>LIMITS['received_bytes']:
        raise p.ProbeError('INSUFFICIENT_REMAINING_NETWORK_BUDGET')
    if before['disk_bytes']+proposed+MIB>LIMITS['disk_bytes']:raise p.ProbeError('INSUFFICIENT_DISK_BUDGET')
    start=time.monotonic();r=dict(request_id=item['id'],request=item,url=asset['url'],
        requested_at_utc=p.utc_now(),status=None,response_headers={},body_bytes=0,header_bytes=0,
        complete_transport=False,error=None,reused_prefix_bytes=0,raw_path=str(path.relative_to(root)))
    headers={'Accept-Encoding':'identity','User-Agent':'QR012-public-trades-pilot/1'}
    if item['range'] is not None:
        headers['Range']='bytes=%d-%d'%tuple(item['range']);headers['If-Match']=asset['expected_etag']
    r['request_headers']=headers
    path.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256()
    def alarm(*_):check_resources(start,before,r['body_bytes']+r['header_bytes'],r['body_bytes']+r['reused_prefix_bytes'],True)
    old_alarm=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,.25,.25)
    try:
        req=urllib.request.Request(asset['url'],headers=headers)
        try:response=(opener or p.anonymous_opener()).open(req,timeout=10)
        except urllib.error.HTTPError as e:response=e
        with closing(response):
            r['status']=response.code;r['response_headers']={k.lower():v for k,v in response.headers.items()}
            r['header_bytes']=len(str(response.headers).encode());alarm()
            # Preserve headers on rejected status; do not drain an unexpected full body.
            validate_headers(item,asset,response.code,r['response_headers'])
            with path.open('xb') as out:
                if item['kind']=='tail':
                    with prefix.open('rb') as old:shutil.copyfileobj(old,out,MIB)
                    r['reused_prefix_bytes']=asset['prefix_bytes']
                length=int(r['response_headers']['content-length'])
                while r['body_bytes']<length:
                    alarm();chunk=response.read(min(MIB,length-r['body_bytes']))
                    if not chunk:raise p.ProbeError('EARLY_RESPONSE_EOF')
                    out.write(chunk);digest.update(chunk);r['body_bytes']+=len(chunk)
                if item['kind']=='probe':
                    with prefix.open('rb') as old:
                        out.flush()
                        if path.read_bytes()!=old.read(65536):raise p.ProbeError('PREFIX_OVERLAP_MISMATCH')
                r['complete_transport']=True
    except (OSError,ValueError,p.ProbeError) as e:r['error']=f'{type(e).__name__}: {e}'
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_alarm)
        r.update(completed_at_utc=p.utc_now(),elapsed_seconds=time.monotonic()-start,
            peak_rss_bytes=p.rss_bytes(),received_body_sha256=digest.hexdigest(),
            stored_bytes=path.stat().st_size if path.exists() else 0,
            stored_sha256=file_sha(path) if path.exists() else None,
            plan_sha256=file_sha(root/'request-plan.json'))
        p.write_new(receipt,r)
    return r


def parse_row(text):
    row=text.split(',')
    if len(row)!=4 or any(len(x)>80 for x in row):raise p.ProbeError('ROW_SCHEMA_OR_FIELD_LENGTH')
    if not re.fullmatch(r'[0-9]+',row[1]):raise p.ProbeError('INVALID_TRADE_ID')
    try:ts,price,size=map(D,[row[0],row[2],row[3]])
    except InvalidOperation as e:raise p.ProbeError('INVALID_DECIMAL') from e
    if not all(x.is_finite() for x in [ts,price,size]) or ts<0 or price<=0 or size==0:
        raise p.ProbeError('INVALID_PRICE_SIZE_TIME')
    if any(len(x.as_tuple().digits)>40 or abs(x.as_tuple().exponent)>20 for x in [ts,price,size]):
        raise p.ProbeError('UNSUPPORTED_NUMERIC_EXTENT')
    return ts,int(row[1]),price,size


def lines(path,audit,start,before):
    pending=b'';audit.update(decompressed_bytes=0,physical_lines=0,gzip_complete=False)
    for chunk in p.gzip_chunks(path,LIMITS['decompressed_bytes']):
        check_resources(start,before);audit['decompressed_bytes']+=len(chunk);pending+=chunk
        rows=pending.split(b'\n');pending=rows.pop()
        if len(pending)>4096:raise p.ProbeError('LINE_LENGTH_CAP')
        for row in rows:
            audit['physical_lines']+=1
            if len(row)>4096:raise p.ProbeError('LINE_LENGTH_CAP')
            yield audit['physical_lines'],row.decode('ascii')
    if pending:raise p.ProbeError('NON_NEWLINE_TERMINATED_FINAL_ROW')
    audit['gzip_complete']=True


def direction_fields(status):
    # Unknown archive aggressor semantics cannot be replaced by price movement.
    if status!=AGGRESSOR_STATUS:raise p.ProbeError('UNREVIEWED_DIRECTION_BINDING')
    return dict(aggressor_status=status,buy_contracts=None,sell_contracts=None,
                signed_flow_contracts=None,trade_pressure=None)


def analyze(receipt,symbol,out,root=DATA):
    if not receipt['complete_transport'] or receipt['request']['kind']=='probe':
        raise p.ProbeError('PARTIAL_TRANSPORT_NOT_ANALYZABLE_AS_FULL_OBJECT')
    start=time.monotonic();before=usage(root);path=root/receipt['raw_path']
    if file_sha(path)!=receipt['stored_sha256']:raise p.ProbeError('COMPLETE_OBJECT_HASH_MISMATCH')
    out.mkdir(parents=True,exist_ok=False);counts=Counter();audit={};mins={};issues=[];gaps=[]
    targets=set();high_id=None;prev_id=None;prev_ts=None;first=last=None;maximum_gap=D(0)
    unknown_invalid=False;error=None
    def bucket(ts):
        if not D(START)<=ts<D(END):return None
        key=int((ts-START)//60)
        return mins.setdefault(key,dict(observed_count=0,observed_contracts=D(0),unique_count=0,
            unique_contracts=D(0),first_line=None,last_line=None,issues=set()))
    def add_issue(kind,line,text,ts=None):
        nonlocal unknown_invalid
        if len(issues)<1000:issues.append(dict(kind=kind,line=line,raw=text))
        b=bucket(ts) if ts is not None else None
        if b is not None:b['issues'].add(kind)
        elif ts is None:unknown_invalid=True
    with localcontext() as ctx:
        ctx.prec=50
        try:
            for line,text in lines(path,audit,start,before):
                counts['physical_rows']+=1
                if line%2000000==0:
                    print(json.dumps(dict(symbol=symbol,parsed_rows=line,decompressed_bytes=audit['decompressed_bytes'],
                                          elapsed_seconds=round(time.monotonic()-start,2))),flush=True)
                try:ts,ident,price,size=parse_row(text)
                except p.ProbeError as e:
                    counts['invalid_rows']+=1;add_issue(str(e),line,text);continue
                counts['valid_rows']+=1;counts['fractional_quantity_rows']+=int(size!=size.to_integral_value())
                counts['raw_positive_sign_rows' if size>0 else 'raw_negative_sign_rows']+=1
                first=ts if first is None else min(first,ts);last=ts if last is None else max(last,ts)
                if not START<=ts<END:counts['out_of_month_rows']+=1;add_issue('OUT_OF_MONTH',line,text,ts)
                if prev_ts is not None:
                    if ts<prev_ts:counts['time_reversals']+=1;add_issue('TIME_REVERSAL',line,text,ts)
                    gap=ts-prev_ts;maximum_gap=max(maximum_gap,gap)
                    if gap>60:
                        counts['event_gaps_gt60s']+=1
                        if len(gaps)<10000:gaps.append(dict(previous_event_s=str(prev_ts),next_event_s=str(ts),seconds=str(gap),next_line=line))
                if prev_id is not None:
                    counts['id_adjacent_steps_gt1']+=int(ident>prev_id+1)
                    counts['unobserved_integer_ids_between_adjacent_rows']+=max(ident-prev_id-1,0)
                if high_id is not None and ident<=high_id:
                    targets.add(ident);counts['id_nonincreasing_vs_high_water_rows']+=1
                    if len(targets)>10000:raise p.ProbeError('IDENTITY_ANOMALY_CAP')
                high_id=ident if high_id is None else max(high_id,ident);prev_id=ident;prev_ts=ts
                b=bucket(ts)
                if b is not None:
                    b['observed_count']+=1;b['unique_count']+=1;b['observed_contracts']+=abs(size);b['unique_contracts']+=abs(size)
                    b['first_line']=line if b['first_line'] is None else b['first_line'];b['last_line']=line
        except Exception as e:
            # Evidence remains available; no successful full-source mask after failure.
            error=f'{type(e).__name__}: {e}'
        identity_resolved=not targets
        resolutions=[]
        if targets and error is None:
            collected=defaultdict(list);second={};n=0
            try:
                for line,text in lines(path,second,start,before):
                    try:ts,ident,price,size=parse_row(text)
                    except p.ProbeError:continue
                    if ident in targets:
                        n+=1
                        if n>100000:raise p.ProbeError('IDENTITY_OCCURRENCE_CAP')
                        collected[ident].append((line,text,ts,price,size))
                for ident,records in collected.items():
                    conflict=len({(x[2],x[3],x[4]) for x in records})>1
                    removed=records if conflict else records[1:]
                    counts['conflicting_duplicate_ids' if conflict else 'identical_duplicate_ids']+=int(len(records)>1)
                    counts['conflicting_rows_excluded' if conflict else 'identical_duplicate_rows_excluded']+=len(removed)
                    if len(records)==1:counts['unique_out_of_order_ids']+=1
                    for line,text,ts,price,size in removed:
                        b=bucket(ts)
                        if b is not None:b['unique_count']-=1;b['unique_contracts']-=abs(size)
                    for line,text,ts,price,size in records:
                        add_issue('CONFLICTING_ID' if conflict else 'EXACT_DUPLICATE' if len(records)>1 else 'OUT_OF_ORDER_ID',line,text,ts)
                    resolutions.append(dict(id=ident,classification='CONFLICT' if conflict else 'EXACT_DUPLICATE' if len(records)>1 else 'UNIQUE_REORDERED',occurrences=[dict(line=x[0],raw=x[1]) for x in records]))
                identity_resolved=True
            except Exception as e:error=f'IDENTITY_RESOLUTION: {e}'
        p.write_new(out/'identity-anomalies.json',dict(target_ids=len(targets),resolved=identity_resolved,records=resolutions))
        transport_and_crc=receipt['complete_transport'] and audit['gzip_complete'] and error is None
        minute_file=out/'minutes.jsonl';hours=defaultdict(lambda:dict(observed_count=0,unique_count=0,observed_contracts=D(0),minutes_with_records=0,minutes_with_issues=0))
        with minute_file.open('x') as f:
            for minute in range((END-START)//60):
                b=mins.get(minute);flags=sorted(b['issues']) if b else ['NO_OBSERVED_TRADES_NOT_PROVEN_NO_TRADING']
                if not transport_and_crc:flags.append('OBJECT_NOT_FULLY_VALIDATED')
                if unknown_invalid:flags.append('UNLOCATED_INVALID_ROW')
                if not identity_resolved:flags.append('IDENTITIES_UNRESOLVED')
                structural=bool(b and transport_and_crc and identity_resolved and not flags)
                record=dict(schema_version=1,instrument_id='gate:usdt:'+symbol,minute_start_s=START+minute*60,minute_end_s=START+(minute+1)*60,
                    observed_count=b['observed_count'] if b else 0,observed_total_contracts=str(b['observed_contracts']) if b else '0',
                    deduplicated_valid_count=b['unique_count'] if b and identity_resolved else None,
                    deduplicated_total_contracts=str(b['unique_contracts']) if b and identity_resolved else None,
                    first_source_line=b['first_line'] if b else None,last_source_line=b['last_line'] if b else None,
                    retrospective_structural_mask=structural,quality_reasons=flags,
                    historical_available_at=None,historical_receive_at=None,decision_eligible=False,
                    quality_evaluation='retrospective complete-file audit; not a historical online availability mask',
                    source_sha256=receipt['stored_sha256'],**direction_fields(AGGRESSOR_STATUS))
                f.write(json.dumps(record,sort_keys=True)+'\n')
                h=hours[minute//60]
                if b:
                    h['observed_count']+=b['observed_count'];h['unique_count']+=b['unique_count'];h['observed_contracts']+=b['observed_contracts'];h['minutes_with_records']+=1
                h['minutes_with_issues']+=int(bool(flags))
                if minute%1000==0:check_resources(start,before,disk_added=f.tell())
        hour_records=[dict(hour_start_s=START+i*3600,**{k:None if k=='unique_count' and not identity_resolved else str(v) if isinstance(v,D) else v for k,v in x.items()}) for i,x in sorted(hours.items())]
        p.write_new(out/'hours.json',hour_records)
        p.write_new(out/'quality-issues.json',dict(first_examples=issues,examples_cap=1000,event_gaps_gt60s=gaps,gap_records_cap=10000))
        result=dict(schema_version=1,symbol=symbol,code_sha256=file_sha(Path(__file__)),source_sha256=receipt['stored_sha256'],
            compressed_bytes=path.stat().st_size,gzip=audit,error=error,counts=dict(counts),identity_resolution_complete=identity_resolved,
            complete_transport_and_gzip=transport_and_crc,exchange_event_completeness_proven=False,
            first_event_s=str(first),last_event_s=str(last),maximum_interevent_gap_s=str(maximum_gap),
            start_boundary_without_observed_trade_s=str(first-START) if first is not None else None,
            end_boundary_without_observed_trade_s=str(D(END)-last) if last is not None else None,
            minutes_with_records=len(mins),calendar_minutes=(END-START)//60,calendar_hours=(END-START)//3600,
            no_observed_trade_minutes=(END-START)//60-len(mins),aggressor_status=AGGRESSOR_STATUS,
            signed_flow_emitted=False,availability_scenario=None,training_ready=False,
            minutes_sha256=file_sha(minute_file),hours_sha256=file_sha(out/'hours.json'))
        p.write_new(out/'analysis.json',result)
        p.write_new(root/'operations'/('analysis-'+symbol+'.json'),dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=p.rss_bytes()))
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['plan','fetch','analyze']);args=parser.parse_args()
    if subprocess.run(['git','-C',str(ROOT),'check-ignore','-q',str(DATA/'probe.json')]).returncode:raise p.ProbeError('DATA_NOT_IGNORED')
    DATA.mkdir(parents=True,exist_ok=True)
    if args.command=='plan':p.write_new(DATA/'request-plan.json',build_plan());print('Immutable plan saved; four normal requests, two conditional full GETs.');return
    plan=read(DATA/'request-plan.json')
    for asset in plan['assets']:
        symbol=asset['symbol']
        if args.command=='fetch':
            probe,tail,full=asset['requests'];a=fetch(probe,asset)
            b=fetch(tail,asset) if a['complete_transport'] else None
            chosen=b if b and b['complete_transport'] else fetch(full,asset)
            p.write_new(DATA/'objects'/(symbol+'.json'),dict(symbol=symbol,receipt_id=chosen['request_id'],complete_transport=chosen['complete_transport'],
                version_matches_qr010=chosen['response_headers'].get('etag')==asset['expected_etag'] and chosen['response_headers'].get('x-amz-version-id')==asset['expected_s3_version']))
            print(json.dumps(dict(symbol=symbol,complete=chosen['complete_transport'],stored_bytes=chosen['stored_bytes'],sha256=chosen['stored_sha256'],error=chosen['error'])),flush=True)
        else:
            obj=read(DATA/'objects'/(symbol+'.json'));receipt=read(DATA/'receipts'/(obj['receipt_id']+'.json'))
            print(json.dumps(analyze(receipt,symbol,DATA/'derived'/symbol)),flush=True)


if __name__=='__main__':main()
