"""New finite controlled path only. Never imports an old test or Fill tape."""
from pathlib import Path
from fractions import Fraction
import socket
import time
import unittest
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS, HOUR, US, Mark, exact
from research.qd011.driver import create, NativeObservation, ExecutionOpen, FundingPoint, scan
from research.qd011.export import controlled_episode
from research.qd011.codec import pack

D=1_704_067_200*US
ROOT=Path('research/.data/qd011/tmp')/('new-path-'+str(time.monotonic_ns()))
STORES=[]


def inputs(*,insufficient=False):
    native=[];opens=[];marks=[]
    for hour in range(6):
        at=D+hour*HOUR
        for i in INSTRUMENTS:
            eth=i==INSTRUMENTS[1]
            close='110' if eth and hour==2 else '105' if eth and hour in (3,4) else '100'
            native.append(NativeObservation(i,at,D-4*HOUR if hour<4 else D,
                '10' if hour<4 else '-10','10' if hour<4 else '-10','0.5','0','1','1','0',close,'1',
                str(int(close)+1),str(int(close)-1),'20000',3,3,'0.1','known-native:'+str(hour)))
            if hour:
                price=('10000000' if insufficient and hour==1 else '95' if eth and hour==4 else '110' if not eth and hour==5 else '100')
                opens.append(ExecutionOpen(i,at,price,'execution-open:'+str(hour)))
    ticks=[D+h*HOUR for h in range(6)]+[D+3*HOUR+60*US]
    for at in ticks:
        for i in INSTRUMENTS:
            if i==INSTRUMENTS[1] and at==D+3*HOUR:continue
            price='110' if at==D+2*HOUR else '105' if i==INSTRUMENTS[1] and at>=D+3*HOUR else '100'
            marks.append(Mark(i,at-60*US,price,'supplied-mark:'+str(at)))
    funding=[FundingPoint(i,D+2*HOUR,'0.0001','fund:'+i,'supplied-rate') for i in INSTRUMENTS]
    return dict(initial_us=D,end_us=D+6*HOUR,native=native,opens=opens,marks=marks,funding=funding)


def make(name,**options):
    c=create(ROOT/name,**inputs(**options));STORES.append(c)
    return c


class ControlledPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ROOT.mkdir(parents=True)
        cls.connect=socket.socket.connect
        def offline(*a,**kw):raise AssertionError('QD011 new offline path: network forbidden')
        socket.socket.connect=offline
        sl.configure_resource_budget(Path('research/.data/qd011/tmp'),63*1024**2)

    @classmethod
    def tearDownClass(cls):
        for c in STORES:c.ledger.close()
        socket.socket.connect=cls.connect

    def test_actual_continuous_joint_native_feedback_and_checkpoint(self):
        results=[]
        for name,restarting in (('continuous',False),('restored',True)):
            c=make(name);c.advance(D)
            first=c.states(D)
            self.assertEqual(len(first['policy']['decisions']),2)
            self.assertEqual(c.view(D)['balance']['cash_usdt'],'10000')
            self.assertGreater(exact(c.view(D)['balance']['reserved_margin_usdt']),0)
            if restarting:
                c.restore_checkpoint()
                self.assertEqual(pack(c.states(D)),pack(first))
            c.advance(D+4*HOUR)
            mid=c.states(D+4*HOUR)
            self.assertIn(INSTRUMENTS[1],mid['feedback']['waiting'])
            self.assertIsNone(c.view(D+3*HOUR)['balance']['economic_equity_usdt'])
            unknown_policy=c.states(D+3*HOUR)['policy']
            self.assertEqual([d['instrument'] for d in unknown_policy['decisions']],[INSTRUMENTS[1]])
            if restarting:
                c.restore_checkpoint()
                self.assertEqual(pack(c.states(D+4*HOUR)),pack(mid))
            c.advance(D+6*HOUR)
            final=c.view(D+6*HOUR);states=c.states(D+6*HOUR)
            self.assertEqual(len(states['feedback']['completed']),2)
            self.assertEqual(states['feedback']['waiting'],{})
            self.assertEqual(states['feedback']['timing']['ETH_USDT']['blocked_side'],1)
            self.assertEqual(states['feedback']['timing']['ETH_USDT']['rearm_price'],106.)
            self.assertEqual(states['feedback']['timing']['ETH_USDT']['session_pnl'],0.)
            self.assertEqual(final['balance']['cash_usdt'],'9998.9685026325')
            events=list(scan(c.ledger,final,'events'))
            fills=[e for e in events if e['body']['record_type']=='Fill']
            self.assertEqual(len(fills),4)
            self.assertTrue(all(e['origin']['kind']=='generated' for e in events))
            orders=list(scan(c.ledger,final,'orders'))
            self.assertGreaterEqual(sum(o['status']=='cancelled' for o in orders),3)
            self.assertEqual([o['filled_contracts'] for o in orders if o['filled_contracts'] and o['intent']['action']=='open'],[20,20])
            exported=[]
            for eid,completion in states['feedback']['completed'].items():
                exported.append(controlled_episode(c,D+6*HOUR,eid))
                if completion['completion'] is not None:
                    self.assertLess(float.fromhex(completion['completion']['pre_reset']),0)
                    self.assertEqual(exact(completion['completion']['delta']),Fraction('-0.0022'))
            labels={e['qr014_episode_fields']['proposal']['instrument_id']:e['qr014_episode_fields'] for e in exported}
            self.assertEqual(labels[INSTRUMENTS[0]]['net_cash_exact'],'0.0194530075')
            self.assertEqual(labels[INSTRUMENTS[1]]['net_cash_exact'],'-1.050950375')
            self.assertTrue(all(e['label_status']=='valid' for e in labels.values()))
            self.assertEqual(labels[INSTRUMENTS[0]]['label_known_at_us'],D+6*HOUR)
            self.assertEqual(labels[INSTRUMENTS[1]]['label_known_at_us'],D+5*HOUR)
            self.assertTrue(all(e['accepted_export_ref'].startswith('qd011-scoped:') and not e['training_authorized'] for e in exported))
            results.append((final['economic_state_sha256'],pack(states),labels))
        self.assertEqual(results[0],results[1])

    def test_full_joint_request_rejected_before_partial_capacity(self):
        c=make('insufficient',insufficient=True)
        c.advance(D);c.advance(D+HOUR)
        view=c.view(D+HOUR);state=c.states(D+HOUR)
        self.assertNotEqual(state['execution']['risk_status'],'ADMITTED')
        self.assertEqual([e for e in scan(c.ledger,view,'events') if e['body']['record_type']=='Fill'],[])
        changed=[o for o in scan(c.ledger,view,'orders') if o['intent']['submitted_at_us']==D]
        self.assertEqual(len(changed),2)
        self.assertTrue(all(o['status']=='cancelled' and o['filled_contracts']==0 for o in changed))


if __name__=='__main__':unittest.main()
