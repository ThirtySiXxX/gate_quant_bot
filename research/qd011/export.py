"""Registry-bound adapter into the existing economic episode exporter."""
from research.qd009 import streaming_ledger as sl
from research.qd010.episode_export import export_episode
from research.qd010.economic_inputs import InputGap
from .driver import scan
from .codec import plan_read
from .ports import INTENT_CONTRACT


def controlled_episode(continuous,at_us,episode_id):
    if any(d['causal_config'].get('native_input_version')==3 for d in continuous.ledger.config['adapters']):
        from research.qd013.exports import export_all
        return next(r for r in export_all(continuous,at_us) if r['qr014_episode_fields']['episode_id']==episode_id)
    ledger=continuous.ledger;view=continuous.view(at_us)
    lots=[x for x in scan(ledger,view,'lots') if x['episode_id']==episode_id]
    if not lots:raise InputGap('CONTROLLED_EPISODE_MISSING')
    first=min(lots,key=lambda l:(l['opened_at_us'],l['lot_id']))
    slices=[s for s in scan(ledger,view,'closed_slices') if s['episode_id']==episode_id]
    wanted={first['opening_fill_id']}|{s['closing_fill_id'] for s in slices}
    accepted={e['body']['record_id']:e for e in scan(ledger,view,'events')
              if e['body']['record_type']=='Fill' and e['body']['record_id'] in wanted}
    orders={};generated={};proofs=[]
    for g in scan(ledger,view,'registry'):
        if g['entry_sha256']!=sl.digest({k:v for k,v in g.items() if k!='entry_sha256'}) or g['result_sha256']!=sl.digest(g['result']):
            raise InputGap('CONTROLLED_REGISTRY_HASH_MISMATCH')
        for order in g['result']['orders']:
            if any(e['body']['order_id']==order['order_id'] for e in accepted.values()):
                if g['adapter_id']!='policy' or order['payload_contract_sha256']!=INTENT_CONTRACT:
                    raise InputGap('NATIVE_POLICY_LINEAGE_REQUIRED')
                plan_read(order['payload']['plan']);orders[order['order_id']]=order
        for index,body in enumerate(g['result']['events']):
            if body['record_type']=='Fill' and body['record_id'] in wanted:
                event=accepted[body['record_id']]
                if g['adapter_id']!='execution' or event['origin']!=dict(kind='generated',registry_seq=g['registry_seq'],output_index=index) or event['body']!=body:
                    raise InputGap('ACTUAL_GENERATED_FILL_LINEAGE_REQUIRED')
                generated[body['record_id']]=body;proofs.append(g['entry_sha256'])
    if set(generated)!=wanted:raise InputGap('GENERATED_EPISODE_FILL_MISSING')
    entry=generated[first['opening_fill_id']];intent=orders[entry['order_id']];p=intent['payload'];cut=p['decision_cutoff']
    decision_view=ledger.as_known(dict(cutoff=cut))
    proposal=dict(account_id=ledger.config['ledger_id'],trajectory_id=ledger.config['trajectory_id'],instrument_id=entry['instrument_id'],
        proposal_id=entry['decision_id'],pre_decision_state_ref=decision_view['view_sha256'],scenario_id='P0',policy_id='ALLOW_ALL',
        account_binding_id='QR010_SHARED_NATIVE_X10',decision_us=entry['decision_at_us'],side=1 if entry['signed_contracts']>0 else -1,
        flat_before=True,action='flat_entry',source_refs=('qf009:registry:'+proofs[0],))
    close_receipts={}
    for s in slices:
        b=generated[s['closing_fill_id']];o=orders[b['order_id']];payload=o['payload'];before=ledger.as_known(dict(cutoff=payload['decision_cutoff']))
        close_receipts[b['record_id']]=dict(fill_id=b['record_id'],order_id=b['order_id'],decision_id=b['decision_id'],instrument_id=b['instrument_id'],
            action=o['action'],decision_us=b['decision_at_us'],committed_audit_prefix=ledger.head['audit_prefix'],
            native_plan_sha256=sl.digest(payload['plan']),decision_cutoff=payload['decision_cutoff'],decision_view_ref=before['view_sha256'])
    exported=export_episode(ledger,cutoff=view['knowledge_cutoff'],episode_id=episode_id,proposal=proposal,close_receipts=close_receipts,
                            proposal_cutoff=cut,scan_maximum=None)
    exported['schema']='qd011.controlled-episode.v1'
    exported['accepted_export_ref']='qd011-scoped:'+sl.digest([ledger.config['_policy_hash'],proofs,exported['proof_ref']])
    exported['acceptance']='REGISTRY_BOUND_RESEARCH_ONLY_NOT_GLOBAL_TRAINING_READINESS'
    exported['training_authorized']=False
    return exported
