"""Research-local QD009 -> QR014 Episode-field mapping, qd010.episode.v1.

Read the actual as-known ledger, its public component roots and scoped readiness.
Never accept a path, accepted=True or a caller-supplied net as a label proof.
This is not an INTERFACES envelope or an old native backtest-result conversion.
"""
from .economic_inputs import INSTRUMENTS, InputGap, exact, text, finality_not_before
from .joint_native_bridge import rows, fingerprint


def export_episode(ledger, *, cutoff, episode_id, proposal, close_receipts, proposal_cutoff=None, scan_maximum=512):
    view = ledger.as_known(dict(cutoff=cutoff))
    ready = ledger.readiness(dict(episode_id=episode_id, cutoff=cutoff))
    read=lambda component:rows(ledger,view,component,maximum=scan_maximum)
    lots = [l for l in read('lots') if l['episode_id'] == episode_id]
    if not lots:
        raise InputGap('EPISODE_LOTS_MISSING')
    instrument = lots[0]['instrument_id']
    required_proposal = ('account_id', 'trajectory_id', 'instrument_id', 'proposal_id', 'pre_decision_state_ref',
                         'scenario_id', 'policy_id', 'account_binding_id', 'decision_us', 'side',
                         'flat_before', 'action', 'source_refs')
    if (set(proposal) != set(required_proposal) or instrument not in INSTRUMENTS
            or proposal['instrument_id'] != instrument or proposal['account_id'] != ledger.config['ledger_id']
            or proposal['trajectory_id'] != ledger.config['trajectory_id']
            or (proposal['scenario_id'], proposal['policy_id'], proposal['account_binding_id'])
            != ('P0', 'ALLOW_ALL', 'QR010_SHARED_NATIVE_X10')
            or proposal['action'] != 'flat_entry' or proposal['flat_before'] is not True
            or not proposal['source_refs'] or proposal['side'] not in (-1, 1)):
        raise InputGap('QR014_PROPOSAL_BINDING_MISMATCH')
    slices = [s for s in read('closed_slices') if s['episode_id'] == episode_id]
    bodies = [r['body'] for r in read('events')]
    opening_ids = {l['opening_fill_id'] for l in lots}
    closing_ids = {s['closing_fill_id'] for s in slices}
    fills = [b for b in bodies if b['record_type'] == 'Fill' and b['record_id'] in opening_ids | closing_ids]
    first = min(l['opened_at_us'] for l in lots)
    if proposal['decision_us'] > first or proposal['decision_us'] % 3_600_000_000:
        raise InputGap('PROPOSAL_CLOCK_AFTER_ENTRY_OR_NOT_HOURLY')
    before = ledger.as_known(dict(cutoff=proposal_cutoff or dict(at_us=proposal['decision_us'], slot=0)))
    if proposal['pre_decision_state_ref'] != before['view_sha256'] or any(
            l['instrument_id'] == instrument and l['remaining_contracts'] for l in rows(ledger, before, 'lots',maximum=scan_maximum)):
        raise InputGap('PROPOSAL_NOT_BOUND_TO_ACTUAL_FLAT_PREFIX')
    if proposal['side'] != (1 if lots[0]['direction'] == 'long' else -1):
        raise InputGap('PROPOSAL_SIDE_MISMATCH')
    # Native intent receipts must bind the actual accepted closing fills.
    natural = ready['natural_exit_at_us'] is not None
    lineage = True
    for b in fills:
        if b['record_id'] not in closing_ids:
            continue
        p = close_receipts.get(b['record_id'])
        if not p or any(p.get(k) != b[k] for k in ('order_id', 'decision_id', 'instrument_id')) or (
            p.get('action') not in ('close', 'reduce') or p.get('decision_us') != b['decision_at_us']
            or not p.get('committed_audit_prefix') or not p.get('native_plan_sha256')
            or p.get('decision_view_ref') != ledger.as_known(dict(cutoff=p.get('decision_cutoff') or dict(at_us=b['decision_at_us'],slot=0)))['view_sha256']):
            lineage = False
    snapshots = [b for b in bodies if b['record_type'] == 'FundingSnapshot'
                 and any(a['episode_id'] == episode_id for a in b['eligible_ranges'])]
    obligations = {b['fee_obligation_id'] for b in fills} | {b['obligation_id'] for b in snapshots}
    relevant = []
    for b in bodies:
        if b['instrument_id'] != instrument:
            continue
        kind = b['record_type']
        if (kind == 'Fill' and b['record_id'] in opening_ids | closing_ids
                or kind == 'FundingSnapshot' and b in snapshots
                or kind == 'ObligationRevision' and b['record_id'] in obligations
                or kind == 'Posting' and b['obligation_id'] in obligations):
            relevant.append(b)
    by_key = {(b['instrument_id'], b['record_type'], b['record_id'], b['revision']): b for b in bodies}
    assertions = [by_key[tuple(k[n] for n in ('instrument_id', 'record_type', 'record_id', 'revision'))]
                  for k in ready['assertion_refs']]
    inputs = tuple(sorted({b['available_at_us'] for b in relevant if b['record_type'] != 'Posting'}))
    postings = tuple(sorted({b['available_at_us'] for b in relevant if b['record_type'] == 'Posting'}))
    assertion_times = tuple(sorted({b['available_at_us'] for b in assertions}))
    reasons = list(ready['blocking_reasons'])
    if natural and not lineage:
        reasons.append('NATURAL_CLOSE_NATIVE_INTENT_LINEAGE_MISSING')
    if natural and ready['status'] == 'complete':
        threshold = finality_not_before(ready['natural_exit_at_us'], inputs, postings)
        if not assertions or any(b['asserted_at_us'] < threshold or b['available_at_us'] < threshold for b in assertions):
            reasons.append('SCOPED_FINALITY_PLUS_ONE_HOUR_NOT_MET')
    cost_keys = ('realized_price_pnl_usdt', 'entry_fee_cash_usdt', 'exit_fee_cash_usdt', 'funding_cash_usdt')
    if any(s[k] is None for s in slices for k in cost_keys):
        reasons.append('SLICE_AMOUNT_UNKNOWN')
    denominator = sum((l['initial_contracts']*exact(l['multiplier'])*exact(l['entry_price']) for l in lots), exact(0))
    if denominator <= 0:
        reasons.append('NONPOSITIVE_GROSS_ENTRY_NOTIONAL')
    status = 'open' if not natural else 'valid' if ready['status'] == 'complete' and not reasons else (
        'invalid' if ready['status'] == 'invalid' or not lineage else 'immature')
    valid = status == 'valid'
    net = sum((exact(s[k]) for s in slices for k in cost_keys), exact(0)) if valid else None
    known = max((ready['natural_exit_at_us'],) + inputs + postings + assertion_times) if valid else None
    # Monotone local revision from all scoped accepted record revisions; no native label schema implied.
    revision = max(1, sum(b['revision'] for b in relevant + assertions))
    proof = fingerprint(dict(view=view['view_sha256'], readiness=ready, close_receipts=close_receipts,
                             episode_id=episode_id))
    fields = dict(proposal=proposal, episode_id=episode_id, label_revision=revision, label_status=status,
                  first_fill_us=first, label_end_us=ready['natural_exit_at_us'] if natural and lineage else None,
                  label_known_at_us=known, net_cash_exact=text(net) if valid else None,
                  gross_entry_notional_exact=text(denominator), natural_exit=natural and lineage,
                  cash_settled=ready['status'] == 'complete', completeness_verified=valid,
                  input_available_us=inputs, posting_available_us=postings, assertion_available_us=assertion_times,
                  as_known_view_ref=view['view_sha256'], scoped_completeness_ref=proof if valid else None,
                  source_refs=tuple('qf009:event:' + fingerprint(b) for b in relevant + assertions),
                  reasons=tuple(dict.fromkeys(reasons or ([] if valid else ['EPISODE_NOT_FINAL']))))
    return dict(schema='qd010.episode.v1', qr014_episode_fields=fields, proof_ref=proof,
                accepted_export_ref=None, acceptance='PROTOTYPE_NOT_RELEASED_OR_TRAINING_APPROVED',
                raw_coverage_verified=False, ledger_candidate_suite_status='INCOMPLETE_S0702_UNKNOWN')
