"""Only new QR014 code, small synthetic inputs, no market data or fitting."""
import ast
from dataclasses import replace
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
import unittest

from research.qr014 import feature_samples as f


def proposal(symbol=f.INSTRUMENTS[1], decision=None, ident='p1'):
    return f.EntryProposal(
        account_id='synthetic-shared-10000', trajectory_id='synthetic-P0-baseline',
        instrument_id=symbol, proposal_id=ident, pre_decision_state_ref='fixture:pre-state',
        scenario_id='P0', policy_id='ALLOW_ALL', account_binding_id='QR010_SHARED_NATIVE_X10',
        decision_us=decision if decision is not None else f.TRAIN_START_US + 200*f.HOUR_US,
        side=-1, flat_before=True, action='flat_entry', source_refs=('fixture:proposal',))


def candles(p, count=169, flat=False):
    result=[]
    with localcontext() as ctx:
        ctx.prec=400
        for i in range(count):
            opened=p.decision_us-(count-i)*f.HOUR_US
            price=Decimal(100 if flat else 2**i)
            result.append(f.Candle(p.instrument_id, opened, opened+f.HOUR_US, opened+f.HOUR_US,
                str(price), str(price*Decimal('1.1')), str(price*Decimal('.9')), str(price),
                '0.2' if i==count-1 else '0.1', f'fixture:candle:{p.instrument_id}:{opened}'))
    return result


def episode(p, ident='e1', net='-2', denominator='3', end=None, known=None):
    end=p.decision_us+2*f.HOUR_US if end is None else end
    known=end+f.HOUR_US if known is None else known
    return f.Episode(p, ident, 1, 'valid', p.decision_us+f.HOUR_US, end, known,
        net, denominator, True, True, True, (p.decision_us, end), (), (known,),
        'fixture:accepted-as-known-view', 'fixture:all-event-revision-posting-scope',
        ('fixture:episode-export-row',), ())


def assemble(rows, labels, intervals=(), complete=True):
    return f.assemble_samples(rows, labels, accepted_export_ref='fixture:accepted-export',
        input_received_at_us=f.ECONOMIC_END_US+5*f.HOUR_US,
        assembled_at_us=f.ECONOMIC_END_US+6*f.HOUR_US,
        purge_context=f.PurgeContext(complete, f.INSTRUMENTS, 'fixture:complete-heldout-scope', intervals))


class FeatureSampleTests(unittest.TestCase):
    def test_approved_plan_and_exact_feature_identity(self):
        plan=json.loads((Path(__file__).resolve().parents[2]/'research/qr014/approved-training-plan.json').read_text())
        self.assertEqual(plan['status'],'RESEARCH_DESIGN_APPROVED_TRAINING_NOT_AUTHORIZED')
        self.assertIs(plan['training_authorized'],False)
        self.assertEqual(plan['learning_problem']['task_choice']['selected'],'REGRESSION')
        self.assertTrue(all(x['selected'] is not None for x in plan['user_decisions']))
        self.assertEqual(tuple(plan['feature_set']['order']),f.FEATURE_NAMES)
        self.assertEqual(tuple(x['unit'] for x in plan['feature_set']['features']),f.FEATURE_UNITS)
        self.assertIsNone(plan['local_feature_sample_adapter']['actual_sample_count'])

    def test_literal_formulas_order_and_fractional_eth_volume(self):
        p=proposal(); result=f.features_for_proposal(candles(p),p)
        self.assertEqual(result.names,(
            'proposal_aligned_return_1h','proposal_aligned_return_4h',
            'proposal_aligned_return_24h','proposal_aligned_return_168h',
            'volatility_24h','volatility_72h','volume_relative_24h',
            'volume_relative_168h','range_pct','efficiency_24h','proposal_side','is_eth'))
        expected=[-h*math.log(2) for h in (1,4,24,168)] + [0,0]
        expected += [math.log(1.2/(1+(0.1*(h-1)+0.2)/h)) for h in (24,168)]
        expected += [0.2,1,-1,1]
        for actual,want in zip(result.values,expected):self.assertAlmostEqual(actual,want,places=12)
        self.assertGreater(result.values[6],0)  # Integer-volume conversion would give zero.
        self.assertEqual(len(result.candle_source_refs),169)
        self.assertEqual(result.available_at_us,p.decision_us)

    def test_future_perturbation_and_current_unclosed_values_are_not_read(self):
        p=proposal(); past=candles(p)
        future=f.Candle(p.instrument_id,p.decision_us,p.decision_us+f.HOUR_US,
            p.decision_us+f.HOUR_US,'1','2','1','2','999','fixture:future')
        before=f.features_for_proposal(past+[future],p)
        poisoned=replace(future,open='NaN',high='NaN',low=None,close='-1',volume_contracts='NaN')
        self.assertEqual(before,f.features_for_proposal(past+[poisoned],p))
        self.assertEqual(before,f.features_for_proposal(past,p))

    def test_unavailable_latest_bar_and_no_stale_fallback(self):
        p=proposal(); bars=candles(p)
        bars[-1]=replace(bars[-1],research_available_at_us=p.decision_us+1)
        result=f.features_for_proposal(bars,p)
        self.assertIsNone(result.values)
        self.assertIn('CANDLE_NOT_AVAILABLE_AT_DECISION',result.reasons[0])
        self.assertIn('LATEST_CLOSED_HOUR_MISSING',f.features_for_proposal(bars[:-1],p).reasons)

    def test_gap_requires_exactly_169_new_valid_bars(self):
        p=proposal(decision=f.TRAIN_START_US+500*f.HOUR_US)
        bars=candles(p,340);del bars[170]
        earlier=replace(p,decision_us=p.decision_us-f.HOUR_US)
        self.assertIsNone(f.features_for_proposal(bars,earlier).values)
        self.assertIsNotNone(f.features_for_proposal(bars,p).values)

    def test_missing_nonfinite_and_invalid_domain_are_not_imputed(self):
        p=proposal(); bars=candles(p)
        for invalid in [None,'NaN','Infinity',0.1,'-0.1','9'*310]:
            with self.subTest(invalid=str(invalid)[:20]):
                result=f.features_for_proposal(bars[:-1]+[replace(bars[-1],volume_contracts=invalid)],p)
                self.assertIsNone(result.values)
        self.assertIsNone(f.features_for_proposal(bars[:-1]+[replace(bars[-1],close='0')],p).values)
        self.assertIsNone(f.features_for_proposal(candles(p,flat=True),p).values)
        # A genuinely observed zero volume is valid, not an unknown value.
        self.assertIsNotNone(f.features_for_proposal([replace(b,volume_contracts='0') for b in bars],p).values)

    def test_invalid_row_resets_history_and_then_recovers(self):
        p=proposal(decision=f.TRAIN_START_US+500*f.HOUR_US);bars=candles(p,340)
        bars[170]=replace(bars[170],volume_contracts=None)
        self.assertIsNone(f.features_for_proposal(bars,replace(p,decision_us=p.decision_us-f.HOUR_US)).values)
        self.assertIsNotNone(f.features_for_proposal(bars,p).values)

    def test_scope_and_duplicate_candles_rejected(self):
        p=proposal();bars=candles(p)
        for bad in [replace(p,flat_before=False),replace(p,action='add'),replace(p,side=0),
                    replace(p,instrument_id='gate:usdt:SOL_USDT'),replace(p,scenario_id='F_HIGH'),
                    replace(p,decision_us=p.decision_us+1)]:
            with self.assertRaises(f.InputError):f.features_for_proposal(bars,bad)
        with self.assertRaisesRegex(f.InputError,'DUPLICATE_OR_DECREASING'):
            f.features_for_proposal(bars[:2]+[bars[1]]+bars[2:],p)

    def test_exact_targets_half_even_and_no_extra_cost_charge(self):
        self.assertEqual(f.target_fraction_12('-2','3'),'-0.666666666667')
        self.assertEqual(f.target_fraction_12('1','2000000000000'),'0.000000000000')
        self.assertEqual(f.target_fraction_12('3','2000000000000'),'0.000000000002')
        self.assertEqual(f.target_fraction_12('-3','2000000000000'),'-0.000000000002')
        p=proposal(); row=f.features_for_proposal(candles(p),p)
        for net,want in [('90','0.009000000000'),('-90','-0.009000000000'),('0','0.000000000000')]:
            output=assemble([row],[episode(p,net=net,denominator='10000')])[0]
            self.assertTrue(output['train_eligible']);self.assertEqual(output['model_target_fraction_12'],want)
            self.assertEqual(output['net_cash_exact'],net);self.assertEqual(output['gross_entry_notional_exact'],'10000')
            self.assertFalse(output['training_authorized'])
        with self.assertRaises(f.InputError):assemble([row],[episode(p,denominator='0')])

    def test_nonvalid_and_unfilled_proposals_keep_states_not_zero_labels(self):
        p=proposal(); row=f.features_for_proposal(candles(p),p);e=episode(p)
        for state in ('open','immature','censored','invalid'):
            item=replace(e,label_status=state,label_known_at_us=None,reasons=('fixture:'+state,),
                net_cash_exact=None,cash_settled=False,completeness_verified=False)
            if state=='open':item=replace(item,label_end_us=None,natural_exit=False)
            output=assemble([row],[item])[0]
            self.assertEqual(output['label_status'],state);self.assertFalse(output['included'])
            self.assertIsNone(output['model_target_fraction_12']);self.assertIsNone(output['target_fraction_12'])
        unfilled=assemble([row],[])[0]
        self.assertIn('NO_REALIZED_EPISODE_LABEL',unfilled['reasons'])
        self.assertIsNone(unfilled['target_fraction_12'])

    def test_claimed_valid_requires_actual_clock_and_finality_inputs(self):
        p=proposal();row=f.features_for_proposal(candles(p),p);e=episode(p)
        for bad in [replace(e,cash_settled=False),replace(e,natural_exit=False),
                    replace(e,completeness_verified=False),replace(e,scoped_completeness_ref=None),
                    replace(e,assertion_available_us=()),replace(e,label_known_at_us=e.label_end_us),
                    replace(e,first_fill_us=None)]:
            with self.assertRaises(f.InputError):assemble([row],[bad])

    def test_one_episode_one_row_duplicates_and_identity_conflicts_fail(self):
        p=proposal();row=f.features_for_proposal(candles(p),p);e=episode(p)
        with self.assertRaisesRegex(f.InputError,'DUPLICATE_OR_CONFLICTING_PROPOSAL_FEATURE'):
            assemble([row,row],[e])
        for other in [e,replace(e,label_revision=2),replace(e,episode_id='e2')]:
            with self.assertRaisesRegex(f.InputError,'DUPLICATE_OR_CONFLICTING_EPISODE'):
                assemble([row],[e,other])
        with self.assertRaisesRegex(f.InputError,'LABEL_PROPOSAL_IDENTITY_CONFLICT'):
            assemble([row],[replace(e,proposal=replace(p,pre_decision_state_ref='fixture:other'))])

    def test_strict_both_24h_boundaries_and_receipt_clock_separation(self):
        limit=f.TRAIN_END_US-f.EMBARGO_US
        p=proposal(decision=f.TRAIN_END_US-3*f.EMBARGO_US);row=f.features_for_proposal(candles(p),p)
        cases=[(limit-1,limit-1,True),(limit,limit,False),(limit-f.HOUR_US,limit,False)]
        for end,known,want in cases:
            output=assemble([row],[episode(p,end=end,known=known)])[0]
            self.assertEqual(output['train_eligible'],want)
            self.assertGreater(output['actual_input_received_at_us'],f.TRAIN_END_US)
        equality=assemble([row],[episode(p,end=limit,known=limit)])[0]
        self.assertIn('LABEL_END_STRICT_24H_FAILED',equality['reasons'])
        self.assertIn('LABEL_KNOWN_STRICT_24H_FAILED',equality['reasons'])

    def test_cross_asset_purge_and_incomplete_inventory(self):
        p=proposal(symbol=f.INSTRUMENTS[0]);row=f.features_for_proposal(candles(p),p);e=episode(p)
        eth=f.InformationInterval(f.INSTRUMENTS[1],e.label_known_at_us,e.label_known_at_us+1,'fixture:ETH-heldout')
        output=assemble([row],[e],(eth,))[0]
        self.assertIn('CROSS_ASSET_HELDOUT_INFORMATION_OVERLAP',output['reasons'])
        self.assertFalse(output['train_eligible'])
        self.assertIn('PURGE_CONTEXT_INCOMPLETE',assemble([row],[e],complete=False)[0]['reasons'])
        nonoverlap=replace(eth,start_us=e.label_known_at_us+1,end_us=None)
        self.assertTrue(assemble([row],[e],(nonoverlap,))[0]['train_eligible'])

    def test_validation_audit_and_missing_feature_are_never_training_rows(self):
        for decision,part in [(f.TRAIN_END_US,'validation_2025'),(f.VALID_END_US,'exposed_audit_2026')]:
            p=proposal(decision=decision);row=f.features_for_proposal(candles(p),p);e=episode(p)
            output=assemble([row],[e])[0]
            self.assertEqual(output['partition'],part);self.assertTrue(output['included'])
            self.assertFalse(output['train_eligible'])
            missing=assemble([],[e])[0]
            self.assertIn('MISSING_PROPOSAL_FEATURE',missing['reasons'])
            self.assertIsNone(missing['model_target_fraction_12'])

    def test_receipt_and_feature_availability_cannot_be_forged(self):
        p=proposal();row=f.features_for_proposal(candles(p),p)
        with self.assertRaisesRegex(f.InputError,'FEATURE_NOT_AVAILABLE'):
            assemble([replace(row,available_at_us=p.decision_us+1)],[episode(p)])
        with self.assertRaisesRegex(f.InputError,'INPUT_RECEIPT_IN_FUTURE'):
            f.assemble_samples([row],[episode(p)],accepted_export_ref='fixture:accepted',
                input_received_at_us=2,assembled_at_us=1,
                purge_context=f.PurgeContext(True,f.INSTRUMENTS,'fixture:purge',()))

    def test_module_has_no_training_network_or_file_io_entrypoint(self):
        tree=ast.parse(Path(f.__file__).read_text())
        forbidden={'fit','fit_transform','partial_fit','train','open','read_text','read_bytes','write_text','write_bytes'}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ''
                self.assertNotIn(name,forbidden)
            if isinstance(node,ast.Import):
                self.assertTrue(all(alias.name in ('math','re') for alias in node.names))
            if isinstance(node,ast.ImportFrom):
                self.assertIn(node.module,('collections','dataclasses','decimal','fractions'))


if __name__=='__main__':
    unittest.main()
