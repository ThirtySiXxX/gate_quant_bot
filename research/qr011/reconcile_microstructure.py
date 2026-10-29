"""Finite QR011 diagnostics. Shadow arithmetic is evidence, never a valid book.

No fitting, strategy replay, application startup or implicit network access.
QR010 is read-only and hash pinned. Each run uses a new immutable output path.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
OLD_CODE=ROOT/'research/qr010/historical_micro_probe.py'
OLD_SHA='fa9ccfb18d316abc385ad472c7c8a1179a2d2232424be1d0a356db9cb7629b5c'
if hashlib.sha256(OLD_CODE.read_bytes()).hexdigest()!=OLD_SHA:
    raise RuntimeError('Frozen QR010 source changed')
from research.qr010 import historical_micro_probe as p

DATA=ROOT/'research/.data/qr011/reconciliation'
LIMITS=dict(requests=16,received_bytes=512*p.MIB,object_bytes=128*p.MIB,
            disk_bytes=1024*p.MIB,decompressed_bytes=256*p.MIB,
            request_seconds=60,active_seconds=1200,rss_bytes=512*p.MIB)
D=Decimal


def usage():
    records=[json.loads(f.read_text()) for directory in ['operations','receipts']
             for f in (DATA/directory).glob('*.json')]
    return dict(active_seconds=sum(r.get('elapsed_seconds',0) for r in records),
                disk_bytes=sum(f.stat().st_size for f in DATA.rglob('*') if f.is_file()),
                requests=sum('request' in r for r in records),
                received_bytes=sum(r.get('body_bytes',0)+r.get('header_bytes',0) for r in records))


def guard(start,remaining):
    if time.monotonic()-start>=remaining or p.rss_bytes()>LIMITS['rss_bytes']:
        raise p.ProbeError('QR011_TIME_OR_RSS_LIMIT')


def original_receipt(ident):
    r=json.loads((p.DATA/'receipts'/(ident+'.json')).read_text())
    f=p.DATA/r['raw_path']
    if f.stat().st_size!=r['body_bytes'] or p.sha(f.read_bytes())!=r['sha256']:
        raise p.ProbeError('FROZEN_RAW_HASH_MISMATCH')
    return r,f


def observed_previous_quantity(previous,side,price):
    """Absent levels are known zero only inside the prior visible corridor."""
    values=dict(previous[side])
    if price in values:return values[price],'PRESENT_BOTH'
    if side=='bids':
        known=previous['bids'][-1][0]<=price<previous['asks'][0][0]
    else:
        known=previous['bids'][0][0]<price<=previous['asks'][-1][0]
    return (D(0),'PRIOR_VISIBLE_ZERO') if known else (None,'OUTSIDE_PRIOR_DEPTH')


def differential_classification(previous,current,raw_delta):
    error=current-previous-raw_delta
    return dict(error=str(error),exact=error==0,
                integer_censoring_compatible=abs(error)<1,
                reverse_sign_exact=current-previous==-raw_delta and raw_delta!=0)


def floor_depth_bounds(bid,ask,legacy_floor_evidence=False):
    """Conditional bounds, not reconstructed hidden fractions or trade capacity."""
    if not legacy_floor_evidence:
        return dict(status='UNQUALIFIED_ENCODING',imbalance=None)
    if not bid or not ask or any(q<0 or q!=q.to_integral_value() for q in bid+ask):
        raise p.ProbeError('EXPECTED_NONNEGATIVE_INTEGER_FLOORS')
    b=sum(bid,D(0));a=sum(ask,D(0));nb=D(len(bid));na=D(len(ask))
    lo=(b-a-na)/(b+a+na);hi=(b+nb-a)/(b+a+nb)
    return dict(status='CONDITIONAL_LEGACY_FLOOR',bid_depth_lower=str(b),
                bid_depth_upper_exclusive=str(b+nb),ask_depth_lower=str(a),
                ask_depth_upper_exclusive=str(a+na),imbalance_lower=str(lo),
                imbalance_upper=str(hi),zero_floor_does_not_prove_empty=True)


def neighbor_plan():
    items=[]
    for n,symbol in enumerate(p.SYMBOLS,1):
        items.append(dict(id=f'N{n:02}',method='GET',symbol=symbol,
            representative_utc='2026090101',kind='orderbooks',max_body_bytes=32*p.MIB,
            url=f'https://download.gatedata.org/futures_usdt/orderbooks/202609/{symbol}-2026090101.csv.gz',
            purpose='Compare full next-hour initial state with current archive at identical source ID; distinguish boundary seed failure from cross-feed inconsistency'))
    return dict(schema_version=1,task_id='QF-QR-011-MICRO-RECONCILIATION',
        created_at_utc=p.utc_now(),limits=LIMITS,requests=items,
        planned_request_count=2,reserved_slots_unused=14,
        trigger='Existing samples cannot establish adjacent-file seed continuity; initial-only explanation already rejected by differential failures',
        no_redownload_qr010=True,credentials=False,retries=False,redirects=False)


def boundary(current_id,next_id,output):
    start=time.monotonic();remaining=LIMITS['active_seconds']-usage()['active_seconds']
    _,current=original_receipt(current_id)
    receipt=json.loads((DATA/'receipts'/(next_id+'.json')).read_text())
    if not receipt['complete_transport']:raise p.ProbeError('NEXT_HOUR_OBJECT_PARTIAL')
    upcoming=DATA/receipt['raw_path'];seed={};seed_lines={};seed_id=None;next_audit={}
    with localcontext() as ctx:
        ctx.prec=50
        # Full gzip validation, retaining only initial records.
        for line,text in p.gzip_lines(upcoming,next_audit,start+remaining):
            fields=text.split(',')
            if fields[1]!='set':continue
            price,q=D(fields[2]),D(fields[3]);ident=int(fields[4])
            if seed_id is None:seed_id=ident
            if ident!=seed_id:raise p.ProbeError('NEXT_SEED_IDS_DIFFER')
            key=('bids' if q>0 else 'asks',price)
            if key in seed:raise p.ProbeError('NEXT_SEED_DUPLICATE_PRICE')
            seed[key]=abs(q);seed_lines[key]=line
        if not next_audit['gzip_complete']:raise p.ProbeError('NEXT_GZIP_INVALID')
        state={};cursor=None;audit={};matched=False;line_at_seed=None
        dup=p.DeltaDuplicates()
        for line,text in p.gzip_lines(current,audit,start+remaining):
            ts,act,price,q,begin,n=text.split(',');price=D(price);q=D(q);begin=int(begin);n=int(n)
            key=('bids' if q>0 else 'asks',price)
            if act=='set':state[key]=abs(q);cursor=begin;continue
            if dup.observe(begin,text,line) is not None:continue
            if begin!=cursor+1:raise p.ProbeError('BOUNDARY_SOURCE_SEQUENCE_GAP')
            if begin+n-1>seed_id:break
            state[key]=state.get(key,D(0))+(abs(q) if act=='make' else -abs(q));cursor=begin+n-1
            if cursor==seed_id:matched=True;line_at_seed=line;break
        counts=Counter();examples=[];maximum=D(0)
        for key in sorted(set(state)|set(seed)):
            a=state.get(key,D(0));b=seed.get(key,D(0));error=a-b
            if a==0 and b==0:continue
            counts['nonzero_union_levels']+=1;counts['exact_levels']+=int(error==0)
            counts['nonzero_presence_disagreement']+=int((a>0)!=(b>0))
            counts['abs_error_ge_0_1']+=int(abs(error)>=D('0.1'))
            maximum=max(maximum,abs(error))
            if error!=0 and len(examples)<12:
                examples.append(dict(side=key[0],price=str(key[1]),current_shadow=str(a),
                                     next_initial=str(b),difference=str(error),next_line=seed_lines.get(key)))
        result=dict(current_id=current_id,next_id=next_id,next_initial_id=seed_id,
            current_aligned_cursor=cursor,exact_source_id_boundary_found=matched,current_line=line_at_seed,
            counts=dict(counts),maximum_absolute_quantity_difference=str(maximum),examples=examples,
            next_object_gzip=next_audit,arithmetic='decimal50 shadow; negative/precision discrepancies never clipped',
            code_sha256=p.sha(Path(__file__).read_bytes()),no_training_feature_promotion=True)
    p.write_new(output,result)
    p.write_new(DATA/'operations'/('boundary-'+current_id+'.json'),
                dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=p.rss_bytes()))
    return result


def precision_and_snapshot_bounds(output):
    start=time.monotonic();remaining=LIMITS['active_seconds']-usage()['active_seconds']
    _,raw=original_receipt('R27');audit={};counts=Counter();examples=[];max_error=D(0)
    min_positive=None;negative_candidate=0;state={};raw_state={}
    # Nearest 0.1 is a falsification experiment, explicitly not a venue rule.
    with localcontext() as ctx:
        ctx.prec=50
        for line,text in p.gzip_lines(raw,audit,start+remaining):
            ts,act,pr,q,ident,n=text.split(',');q=abs(D(q));signed=D(text.split(',')[3])
            key=('bids' if signed>0 else 'asks',D(pr));nearest=q.quantize(D('0.1'))
            error=abs(q-nearest);max_error=max(max_error,error);counts['rows']+=1
            if q>0:min_positive=q if min_positive is None else min(min_positive,q)
            if error:
                counts['off_tenth_grid']+=1
                if len(examples)<8:examples.append(dict(line=line,raw=text,nearest_tenth=str(nearest),difference=str(error)))
            if nearest==0 and q>0:counts['positive_size_rounded_to_zero']+=1
            if act=='set':state[key]=nearest;raw_state[key]=q
            else:
                sign=1 if act=='make' else -1
                state[key]=state.get(key,D(0))+sign*nearest
                raw_state[key]=raw_state.get(key,D(0))+sign*q
                negative_candidate+=int(state[key]<0)
        counts['negative_shadow_events_after_tenth_rounding']=negative_candidate
    snapshots={}
    for ident in ['R23','R28']:
        _,raw=original_receipt(ident);a={};rows=[];c=Counter();maxwidth=D(0)
        for line,text in p.gzip_lines(raw,a,start+remaining):
            s=p.parse_snapshot(text);c['snapshots']+=1
            c['top_quote_zero_quantity']+=int(s['bids'][0][1]==0 or s['asks'][0][1]==0)
            c['zero_depth_levels']+=sum(q==0 for side in ['bids','asks'] for _,q in s[side])
            bounds=floor_depth_bounds([q for _,q in s['bids'][:5]],[q for _,q in s['asks'][:5]],True)
            width=D(bounds['imbalance_upper'])-D(bounds['imbalance_lower']);maxwidth=max(maxwidth,width)
            if len(rows)<3:rows.append(dict(snapshot_id=s['id'],line=line,source_current_s=str(s['current']),
                spread_bps=str((s['asks'][0][0]-s['bids'][0][0])*20000/(s['asks'][0][0]+s['bids'][0][0])),
                conditional_depth_bounds=bounds,historical_available_at=None))
        snapshots[ident]=dict(counts=dict(c),conditional_max_imbalance_width=str(maxwidth),examples=rows)
    result=dict(code_sha256=p.sha(Path(__file__).read_bytes()),raw_eth_counts=dict(counts),
        maximum_distance_to_tenth=str(max_error),minimum_positive_raw_size=str(min_positive),
        normalization_status='NOT_AUTHORIZED_NO_HISTORICAL_QUANTUM_OR_PRODUCER_ERROR_BOUND',
        rounding_experiment='diagnostic only; not a normalized dataset',examples=examples,
        first_negative_exact_counterexample={'prior':'21.2999999999999','take':'21.3','difference':'-0.0000000000001'},
        snapshots=snapshots,legacy_floor_condition='official legacy integer semantics plus observed integer archive; archive request header not retained, so bounds conditional',
        no_exact_quantity_recovery=True)
    p.write_new(output,result)
    p.write_new(DATA/'operations'/'precision-and-bounds.json',dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=p.rss_bytes()))
    return result


def parse_pair(book_id,snapshot_id,output,book_receipt=None,snapshot_receipt=None,source_root=None):
    """Compare fixed additive mapping; never optimize a reconstruction to fit."""
    start=time.monotonic();before=usage();remaining=LIMITS['active_seconds']-before['active_seconds']
    if remaining<=0 or before['disk_bytes']>=LIMITS['disk_bytes']-p.MIB:
        raise p.ProbeError('QR011_BUDGET_EXHAUSTED')
    if source_root is None:
        br,bfile=original_receipt(book_id);sr,sfile=original_receipt(snapshot_id)
    else:
        br,sr=book_receipt,snapshot_receipt
        bfile=source_root/br['raw_path'];sfile=source_root/sr['raw_path']
    snapshots=[];sa={};deadline=start+remaining
    for line,text in p.gzip_lines(sfile,sa,deadline):
        s=p.parse_snapshot(text);s['line']=line
        if snapshots and (s['id']<=snapshots[-1]['id'] or s['current']<snapshots[-1]['current']):
            raise p.ProbeError('NONMONOTONE_SNAPSHOT')
        snapshots.append(s)
        if len(snapshots)>20000:raise p.ProbeError('SNAPSHOT_CAP')
    if not sa['gzip_complete']:raise p.ProbeError('SNAPSHOT_GZIP_INCOMPLETE')
    counts=Counter();precision=Counter();examples=defaultdict(list)
    initial={};shadow={};initial_lines={};net=defaultdict(lambda:D(0))
    updates=defaultdict(list);update_counts=Counter();residuals={};first_seen={}
    first_id=None;cursor=None;si=0;previous=None;initial_phase=True;valid_sequence=True
    duplicates=p.DeltaDuplicates();ba={};first_negative=None;first_delta=None
    transition_path=output/'transitions.jsonl';output.mkdir(parents=True,exist_ok=True)

    def example(kind,value):
        if len(examples[kind])<8:examples[kind].append(value)

    def compare(s,line,out):
        nonlocal previous,net,updates,update_counts
        counts['exact_boundary_snapshots']+=1
        for side in ['bids','asks']:
            for price,q in s[side]:
                key=(side,price);raw_q=shadow.get(key,D(0));residual=raw_q-q
                counts['observed_levels']+=1
                counts['level_exact']+=int(residual==0)
                r=residuals.setdefault(key,dict(first=residual,min=residual,max=residual,n=0,changed=0))
                r['n']+=1;r['changed']+=int(residual!=r['first'])
                r['min']=min(r['min'],residual);r['max']=max(r['max'],residual)
                rec=dict(snapshot_id=s['id'],snapshot_line=s['line'],book_line=line,
                         source_current_s=str(s['current']),side=side,price=str(price),
                         snapshot_q=str(q),shadow_q=str(raw_q),residual=str(residual))
                if key not in first_seen:
                    first_seen[key]=rec
                    if previous is None and not update_counts[key] and residual!=0:
                        example('first_snapshot_untouched_initial_mismatch',dict(rec,
                            initial_q=str(initial.get(key,D(0))),initial_line=initial_lines.get(key),
                            initial_id=first_id,delta_rows_at_this_level=0))
                if previous is not None:
                    old,scope=observed_previous_quantity(previous,side,price)
                    if old is not None:
                        delta=net[key];classification=differential_classification(old,q,delta)
                        prefix='transition_'+scope.lower()
                        counts[prefix]+=1;counts[prefix+'_exact']+=int(classification['exact'])
                        counts[prefix+'_integer_censoring_compatible']+=int(classification['integer_censoring_compatible'])
                        counts[prefix+'_reverse_sign_exact']+=int(classification['reverse_sign_exact'])
                        evidence=dict(rec,previous_id=previous['id'],previous_line=previous['line'],
                                      previous_q=str(old),raw_net_delta=str(delta),scope=scope,
                                      raw_delta_rows=update_counts[key],raw_examples=updates[key],**classification)
                        out.write(json.dumps(evidence,sort_keys=True)+'\n')
                        if not classification['integer_censoring_compatible']:
                            example('large_transition_mismatch',evidence)
                        elif not classification['exact']:
                            example('subunit_transition_difference',evidence)
                        if scope=='PRIOR_VISIBLE_ZERO' and q==0 and delta>0:
                            example('positive_raw_depth_reported_zero',evidence)
        previous=s;net=defaultdict(lambda:D(0));updates=defaultdict(list);update_counts=Counter()

    with localcontext() as context,transition_path.open('x') as out:
        context.prec=50
        for line,text in p.gzip_lines(bfile,ba,deadline):
            counts['rows']+=1
            ts,action,price,quantity,begin,merged=text.split(',')
            ts=D(ts);price=D(price);q=D(quantity);begin=int(begin);merged=int(merged)
            if not all(x.is_finite() for x in [ts,price,q]) or price<=0 or q==0:
                raise p.ProbeError('INVALID_RAW_VALUE')
            side='bids' if q>0 else 'asks';key=(side,price)
            digits=max(0,-q.as_tuple().exponent);precision[action+'_decimal_places_'+str(digits)]+=1
            counts[action+'_rows']+=1
            if action=='set':
                if not initial_phase or merged!=0 or key in initial:
                    raise p.ProbeError('INVALID_INITIAL_STATE')
                if first_id is None:first_id=begin;cursor=begin
                if begin!=first_id:raise p.ProbeError('MIXED_INITIAL_IDS')
                initial[key]=abs(q);initial_lines[key]=line;shadow[key]=abs(q)
                continue
            initial_phase=False
            if action not in ['make','take']:raise p.ProbeError('UNKNOWN_ACTION')
            if duplicates.observe(begin,text,line) is not None:
                counts['identical_duplicates']+=1;continue
            if begin!=cursor+1 or merged<1:
                valid_sequence=False;example('sequence_failure',dict(line=line,raw=text,cursor=cursor));break
            cursor=begin+merged-1
            if first_delta is None:first_delta=dict(line=line,raw=text)
            change=abs(q) if action=='make' else -abs(q)
            prior=shadow.get(key,D(0));shadow[key]=prior+change;net[key]+=change
            update_counts[key]+=1
            if len(updates[key])<8:updates[key].append(dict(line=line,raw=text))
            if shadow[key]<0:
                counts['negative_shadow_events']+=1
                e=dict(line=line,raw=text,prior=str(prior),after=str(shadow[key]))
                if first_negative is None:first_negative=e
                example('negative_shadow_events',e)
            while si<len(snapshots) and snapshots[si]['id']<=cursor:
                s=snapshots[si];si+=1
                if s['id']==cursor:compare(s,line,out)
                else:counts['interior_snapshot_ids']+=1
            if line%32768==0:
                guard(start,remaining)
                if out.tell()>256*p.MIB or before['disk_bytes']+out.tell()>LIMITS['disk_bytes']-p.MIB:
                    raise p.ProbeError('QR011_OUTPUT_CAP')
    counts['residual_level_keys']=len(residuals)
    counts['revisited_level_keys']=sum(x['n']>1 for x in residuals.values())
    counts['revisited_constant_residual_keys']=sum(x['n']>1 and x['changed']==0 for x in residuals.values())
    counts['revisited_nonzero_constant_residual_keys']=sum(x['n']>1 and x['changed']==0 and x['first']!=0 for x in residuals.values())
    result=dict(schema_version=1,diagnostic='fixed-additive-shadow-and-adjacent-snapshot-differences',
        code_sha256=p.sha(Path(__file__).read_bytes()),qr010_code_sha256=OLD_SHA,
        book_id=book_id,snapshot_id=snapshot_id,book_sha256=br['sha256'],snapshot_sha256=sr['sha256'],
        initial_id=first_id,first_delta=first_delta,first_negative=first_negative,
        counts=dict(counts),numeric_lexeme_precision=dict(precision),examples=dict(examples),
        sequence_contiguous_after_exact_dedup=valid_sequence,book_gzip=ba,snapshot_gzip=sa,
        initial_state_independent_of_snapshot=True,shadow_negative_states_are_invalid=True,
        diagnostic_does_not_emit_qualified_features=True,historical_availability_qualified=False,
        transition_file=str(transition_path.relative_to(DATA)) if transition_path.is_relative_to(DATA) else str(transition_path),
        transition_sha256=p.sha(transition_path.read_bytes()))
    p.write_new(output/'analysis.json',result)
    return result,dict(elapsed_seconds=time.monotonic()-start,peak_rss_bytes=p.rss_bytes())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['diagnose','plan-neighbor','fetch-neighbor','boundary','precision'])
    parser.add_argument('--pairs',default='')
    args=parser.parse_args()
    import subprocess
    if subprocess.run(['git','-C',str(ROOT),'check-ignore','-q',str(DATA/'probe.json')]).returncode:
        raise p.ProbeError('QR011_OUTPUT_NOT_IGNORED')
    if args.command=='plan-neighbor':
        p.write_new(DATA/'request-plan.json',neighbor_plan());print('Two next-hour objects planned; no QR010 redownload.');return
    if args.command=='fetch-neighbor':
        plan=json.loads((DATA/'request-plan.json').read_text());old=p.LIMITS
        try:
            p.LIMITS=LIMITS
            for item in plan['requests']:
                if item['url'] not in {x['url'] for x in neighbor_plan()['requests']}:
                    raise p.ProbeError('UNPLANNED_NEIGHBOR_URL')
                result=p.fetch_one(item,DATA)
                print(json.dumps({k:result[k] for k in ['request','status','body_bytes','complete_transport','sha256']}),flush=True)
        finally:p.LIMITS=old
        return
    if args.command=='boundary':
        for current,nxt in [('R22','N01'),('R27','N02')]:
            print(json.dumps(boundary(current,nxt,DATA/('boundary-'+current+'.json'))),flush=True)
        return
    if args.command=='precision':
        result=precision_and_snapshot_bounds(DATA/'precision-and-snapshot-bounds.json')
        print(json.dumps(result),flush=True);return
    pairs=args.pairs.split(',')
    allowed={'R02:R03','R17:R18','R22:R23','R27:R28'}
    if len(set(pairs))!=len(pairs) or not set(pairs)<=allowed:
        raise p.ProbeError('UNPLANNED_DIAGNOSTIC_PAIR')
    for pair in pairs:
        book,snap=pair.split(':');out=DATA/'diagnostic-v1'/book
        if out.exists():raise p.ProbeError('PRESERVE_EXISTING_DIAGNOSTIC')
        result,operation=parse_pair(book,snap,out)
        p.write_new(DATA/'operations'/('diagnose-'+book+'.json'),operation)
        print(json.dumps({'book':book,'counts':result['counts'],'first_negative':result['first_negative'],
                          'examples':result['examples'].get('first_snapshot_untouched_initial_mismatch',[])[:2]}),flush=True)


if __name__=='__main__':main()
