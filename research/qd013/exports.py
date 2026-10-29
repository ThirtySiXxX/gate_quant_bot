"""One indexed export pass over actual accepted ledger/registry, never supplied PnL.

Actual scenario identity is preserved. QR014 currently accepts only P0/ALLOW_ALL;
other trajectories remain explicitly separate research diagnostics.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import os
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import exact,text,finality_not_before,HOUR,InputGap
from research.qd011.driver import scan
from research.qd011.ports import INTENT_CONTRACT_V2
from research.qd011.codec import plan_read,pack


def export_all(replay,at):
    ledger=replay.ledger;view=replay.view(at);cfg=ledger.config
    policy=next(d['causal_config']['scenario']['policy_id'] for d in cfg['adapters'] if d['adapter_id']=='policy')
    groups=defaultdict(list);slices=defaultdict(list);bodies={};origins={};orders={};generated={};proofs={}
    for l in scan(ledger,view,'lots'):groups[l['episode_id']].append(l)
    for s in scan(ledger,view,'closed_slices'):slices[s['episode_id']].append(s)
    for e in scan(ledger,view,'events'):
        b=e['body'];bodies[tuple(sl.wire_key(b))]=b;origins[b['record_id']]=e['origin']
    for g in scan(ledger,view,'registry',limit=1):
        if g['entry_sha256']!=sl.digest({k:v for k,v in g.items() if k!='entry_sha256'}) or g['result_sha256']!=sl.digest(g['result']):
            raise InputGap('REGISTRY_EXPORT_HASH_MISMATCH')
        for o in g['result']['orders']:
            if g['adapter_id']!='policy' or o['payload_contract_sha256']!=INTENT_CONTRACT_V2:raise InputGap('QD013_NATIVE_INTENT_REQUIRED')
            plan_read(o['payload']['plan']);orders[o['order_id']]=o
        for index,b in enumerate(g['result']['events']):
            if b['record_type']!='Fill':continue
            if g['adapter_id']!='execution' or bodies.get(tuple(sl.wire_key(b)))!=b or origins[b['record_id']]!=dict(kind='generated',registry_seq=g['registry_seq'],output_index=index):
                raise InputGap('GENERATED_FILL_LINEAGE_REQUIRED')
            generated[b['record_id']]=b;proofs[b['record_id']]=g['entry_sha256']
    by_obligation=defaultdict(list);snapshots=defaultdict(list)
    for b in bodies.values():
        if b['record_type']=='FundingSnapshot':
            for eid in {a['episode_id'] for a in b['eligible_ranges']}:snapshots[eid].append(b)
        if b['record_type'] in ('ObligationRevision','Posting'):by_obligation[b['record_id'] if b['record_type']=='ObligationRevision' else b['obligation_id']].append(b)
    result=[]
    for eid,lots in sorted(groups.items()):
        first=min(lots,key=lambda l:(l['opened_at_us'],l['lot_id']));own=slices[eid]
        ids={l['opening_fill_id'] for l in lots}|{s['closing_fill_id'] for s in own}
        if not ids<=set(generated):raise InputGap('GENERATED_EPISODE_FILL_MISSING')
        entry=generated[first['opening_fill_id']];intent=orders[entry['order_id']];payload=intent['payload'];cut=payload['decision_cutoff']
        if payload['scenario_id']!=cfg['scenario_id'] or payload['policy_id']!=policy:raise InputGap('SCENARIO_LABEL_CONTAMINATION')
        flat=payload['pre_positions'][entry['instrument_id']]==0
        if not flat or intent['action']!='open':raise InputGap('ACTUAL_FLAT_ENTRY_REQUIRED')
        before=ledger.as_known(dict(cutoff=cut));ready=ledger.readiness(dict(episode_id=eid,cutoff=view['knowledge_cutoff']))
        proposal=dict(account_id=cfg['ledger_id'],trajectory_id=cfg['trajectory_id'],instrument_id=entry['instrument_id'],proposal_id=entry['decision_id'],
            pre_decision_state_ref=before['view_sha256'],scenario_id=cfg['scenario_id'],policy_id=policy,account_binding_id='QR010_SHARED_NATIVE_X10',
            decision_us=entry['decision_at_us'],side=1 if entry['signed_contracts']>0 else -1,flat_before=True,action='flat_entry',
            source_refs=('qf009:registry:'+proofs[entry['record_id']],))
        relevant=[generated[id] for id in ids]+snapshots[eid]
        obligations={b['fee_obligation_id'] for b in relevant if b['record_type']=='Fill'}|{b['obligation_id'] for b in snapshots[eid]}
        for oid in obligations:relevant.extend(by_obligation[oid])
        assertions=[bodies[tuple(k[n] for n in ('instrument_id','record_type','record_id','revision'))] for k in ready['assertion_refs']]
        inputs=tuple(sorted({b['available_at_us'] for b in relevant if b['record_type']!='Posting'}))
        postings=tuple(sorted({b['available_at_us'] for b in relevant if b['record_type']=='Posting'}));assert_times=tuple(sorted({b['available_at_us'] for b in assertions}))
        reasons=list(ready['blocking_reasons']);natural=ready['natural_exit_at_us'] is not None
        for b in (generated[id] for id in {s['closing_fill_id'] for s in own}):
            o=orders[b['order_id']]
            if o['action'] not in ('close','reduce') or not o['payload']['plan'] or o['submitted_at_us']!=b['decision_at_us']:
                reasons.append('NATURAL_CLOSE_INTENT_LINEAGE_MISSING')
        if natural and ready['status']=='complete':
            threshold=finality_not_before(ready['natural_exit_at_us'],inputs,postings)
            if not assertions or any(b['asserted_at_us']<threshold or b['available_at_us']<threshold for b in assertions):reasons.append('FINALITY_PLUS_ONE_HOUR_NOT_MET')
        keys=('realized_price_pnl_usdt','entry_fee_cash_usdt','exit_fee_cash_usdt','funding_cash_usdt')
        if any(s[k] is None for s in own for k in keys):reasons.append('SLICE_AMOUNT_UNKNOWN')
        denominator=sum((l['initial_contracts']*exact(l['multiplier'])*exact(l['entry_price']) for l in lots),exact(0))
        if denominator<=0:reasons.append('NONPOSITIVE_GROSS_ENTRY_DENOMINATOR')
        valid=natural and ready['status']=='complete' and not reasons
        costs={k:text(sum((exact(s[k]) for s in own),exact(0))) if all(s[k] is not None for s in own) else None for k in keys}
        net=sum((exact(v) for v in costs.values()),exact(0)) if valid else None
        status='valid' if valid else 'open' if not natural else 'invalid' if ready['status']=='invalid' else 'immature'
        if not valid and not reasons:reasons.append('EPISODE_NOT_FINAL')
        known=max((ready['natural_exit_at_us'],)+inputs+postings+assert_times) if valid else None
        proof=sl.digest(pack([view['view_sha256'],ready,sorted(proofs[id] for id in ids),proposal]))
        fields=dict(proposal=proposal,episode_id=eid,label_revision=max(1,sum(b['revision'] for b in relevant+assertions)),label_status=status,
            first_fill_us=first['opened_at_us'],label_end_us=ready['natural_exit_at_us'] if natural else None,label_known_at_us=known,
            net_cash_exact=text(net) if valid else None,gross_entry_notional_exact=text(denominator),natural_exit=natural,cash_settled=ready['status']=='complete',
            completeness_verified=valid,input_available_us=inputs,posting_available_us=postings,assertion_available_us=assert_times,
            as_known_view_ref=view['view_sha256'],scoped_completeness_ref=proof if valid else None,
            source_refs=tuple('qf009:event:'+sl.digest(b) for b in relevant+assertions),reasons=tuple(dict.fromkeys(reasons)))
        compatible=(cfg['scenario_id'],policy)==('P0','ALLOW_ALL')
        result.append(dict(schema='qd013.controlled-episode.v1',qr014_episode_fields=fields,cost_breakdown_exact=costs,
            cost_attribution_scope='WHOLE_MATURE_EPISODE' if valid else 'CLOSED_SLICES_ONLY_NOT_A_LABEL_TARGET',
            pre_decision_equity_exact=payload['pre_equity'],pre_decision_positions=payload['pre_positions'],
            accepted_export_ref='qd013-scoped:'+proof,registry_refs=sorted(proofs[id] for id in ids),
            qr014_compatible=compatible,qr014_exclusion_reason=None if compatible else 'QR014_BASELINE_ONLY',
            censoring=None if valid else 'ECONOMIC_CUTOFF_OPEN' if not natural and at>=cfg['end_exclusive_us'] else 'TAIL_END_IMMATURE' if at>=cfg['end_exclusive_us'] else 'PENDING',
            training_authorized=False))
    return result


def write_bundle(path,records,identity,*,write_budget=None):
    """Exclusive once-produced reusable research export; no feature/model matrix."""
    path=Path(path);path.mkdir(parents=True,exist_ok=False);digest=hashlib.sha256();count=0
    with (path/'episodes.jsonl').open('xb') as f:
        for row in records:
            raw=sl.canonical_bytes(pack(row))+b'\n'
            if write_budget:write_budget(f.name,f.tell()+len(raw),len(raw))
            f.write(raw);digest.update(raw);count+=1
        f.flush();os.fsync(f.fileno())
    manifest=dict(schema='qd013.episode-export.v1',state='COMPLETE',identity=identity,rows=count,sha256=digest.hexdigest(),training_authorized=False)
    with (path/'manifest.json').open('xb') as f:
        raw=sl.canonical_bytes(manifest)+b'\n'
        if write_budget:write_budget(f.name,len(raw),len(raw))
        f.write(raw);f.flush();os.fsync(f.fileno())
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return manifest


def qr014_fields(row):
    if not row['qr014_compatible']:raise InputGap('QR014_BASELINE_ONLY_NO_SCENARIO_RELABEL')
    fields=dict(row['qr014_episode_fields']);fields['proposal']=dict(fields['proposal'])
    for name in ('input_available_us','posting_available_us','assertion_available_us','source_refs','reasons'):fields[name]=tuple(fields[name])
    fields['proposal']['source_refs']=tuple(fields['proposal']['source_refs'])
    return fields


def qr014_candles(cache,instrument,decision_us):
    """Exactly the169 closed source records; consumer builds its own Candle.

    This is a typed field mapping, not a feature matrix or invocation of QR code.
    """
    for opened in range(decision_us-169*HOUR,decision_us,HOUR):
        r=cache.get('hour',instrument,opened)
        if r['close_us']>decision_us or r['available_us']>decision_us:raise InputGap('FUTURE_QR014_SOURCE')
        yield dict(instrument_id=instrument,bar_open_us=r['open_us'],bar_close_us=r['close_us'],research_available_at_us=r['available_us'],
            open=r['open'],high=r['high'],low=r['low'],close=r['close'],volume_contracts=r['volume_contracts'],
            source_ref='qd013:'+cache.key+':'+r['row_id'])
