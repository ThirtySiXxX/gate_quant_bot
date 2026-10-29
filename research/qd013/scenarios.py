"""QR010's eight scenarios/nine independent joint trajectories, no new policy."""
from fractions import Fraction
from research.qd010.economic_inputs import exact, MULTIPLIERS, INSTRUMENTS, HOUR, US

REGISTER=(('P0','ALLOW_ALL'),('P0','SKIP_FIRST_ADMISSIBLE_BASKET'),
          ('F_HIGH','ALLOW_ALL'),('F_REFERENCE','ALLOW_ALL'),('S_HIGH','ALLOW_ALL'),
          ('L_EXTRA','ALLOW_ALL'),('Q_LOW','ALLOW_ALL'),('M_SLOW','ALLOW_ALL'),('T_FILL_FIRST','ALLOW_ALL'))


def scenario(name='P0',policy='ALLOW_ALL'):
    if (name,policy) not in REGISTER:raise ValueError('UNAPPROVED_TRAJECTORY')
    return dict(scenario_id=name,policy_id=policy,fee='0.0015' if name=='F_HIGH' else '0.0005' if name=='F_REFERENCE' else '0.00075',
        slip='0.001' if name=='S_HIGH' else '0.0005',latency_us=3601*US if name=='L_EXTRA' else US,
        participation='0.0001' if name=='Q_LOW' else '0.001',mark_delay_us=120*US if name=='M_SLOW' else 60*US,
        mark_max_age_us=180*US if name=='M_SLOW' else 120*US,mark_available_age_us=60*US,
        fill_first=name=='T_FILL_FIRST',account_binding_id='QR010_SHARED_NATIVE_X10')


def costs(cfg):
    s=cfg.get('scenario',scenario());fee=exact(s['fee']);slip=exact(s['slip'])
    return fee,slip,max(slip,Fraction('0.0008'))


def boundary(at,cfg):
    delay=cfg.get('scenario',scenario())['latency_us']
    return ((at+delay+HOUR-1)//HOUR)*HOUR


def reserve(q,i,price,cfg):
    fee,_,g=costs(cfg);n=q*exact(MULTIPLIERS[i])*exact(price)
    return n*(1+g)/200+2*fee*n*(1+g)+n*g


def validate_basket(orders,f,prices,cfg,*,filling=False):
    """Exact same frozen predicates as QD010, parameterized by approved scenario."""
    if f['equity'] is None or f['budget'] is None or f['equity']<=0:return 'ACCOUNT_FINANCE_UNKNOWN_OR_INSOLVENT'
    if len({o.instrument_id for o in orders})!=len(orders):return 'DUPLICATE_BASKET_INSTRUMENT'
    _,slip,g=costs(cfg);projected=dict(f['positions']);required=Fraction(0)
    for o in orders:
        i=o.instrument_id
        if i not in INSTRUMENTS or o.action!='open' or type(o.quantity) is not int or not 1<=o.quantity<=10**9 or o.side not in (-1,1) or prices[i]<=0 or f['marks'][i].value is None:
            return 'INVALID_INCREASE_METADATA_OR_MARK'
        if projected[i] and projected[i]*o.side<0:return 'REVERSAL_REQUIRES_LATER_DECISION'
        projected[i]+=o.side*o.quantity;required+=reserve(o.quantity,i,prices[i],cfg)
        sub=max(abs(o.native_target),abs(projected[i])*exact(MULTIPLIERS[i])*o.price)*(1+g)
        if max(sub,abs(projected[i])*exact(MULTIPLIERS[i])*prices[i]*(1+g))>1_000_000:return 'PER_INSTRUMENT_SYNTHETIC_TIER'
    values={i:abs(q)*exact(MULTIPLIERS[i])*prices[i]*(1+slip if filling else 1+g) if q else Fraction(0) for i,q in projected.items()}
    if any(v>f['equity']*Fraction('5.5') for v in values.values()) or sum(values.values())>f['equity']*6:return 'JOINT_PROJECTED_EXPOSURE_CAP'
    return 'ADMITTED' if required<=f['budget'] else 'BASKET_BUDGET_INSUFFICIENT'
