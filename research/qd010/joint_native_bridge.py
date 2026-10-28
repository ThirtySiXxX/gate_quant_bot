"""Small offline native/ledger connection, qd010.joint-native.v1.

Research-local prototype, not a registered QD009 controlled adapter or exchange.
Financial state is read from the real ledger; this module owns order reservations
only. Imported tapes are permitted solely by explicit synthetic_reference_demo.
ETH feedback publication is deliberately blocked until the atomic R01/R04 port
is bound. It must never be silently represented by an accepted mock callback.
"""
from copy import deepcopy
from dataclasses import dataclass, asdict
from fractions import Fraction
import hashlib
import json
import math

import numpy as np
import pandas as pd
from src.config import SystematicConfig
from src.execution_timing import ExecutionTiming
from src.position_sizing import EntrySizingBook
from src import portfolio as pf, strategy_signals as signals_core, strategy_execution as execution
from .economic_inputs import (INSTRUMENTS, SYMBOLS, MULTIPLIERS, HOUR, FEE, SLIP, G,
                              FrozenInputs, InputGap, exact, text, execution_boundary, pending_reserve)


def research_config():
    return SystematicConfig(position_sizing_mode='volatility', initial_capital_usdt=10000,
                            target_annual_vol_pct=100, max_instrument_exposure_pct=550,
                            max_correlated_group_exposure_pct=600, max_leverage=40,
                            ml_model_path='')


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def rows(ledger, view, component, maximum=512):
    """Actual pinned public scans; reject unbounded prototype materialization."""
    result, token = [], None
    while True:
        page = ledger.scan(dict(view_sha256=view['view_sha256'], component=component,
                               filter=dict(kind='all'), after=token, limit=64,
                               null_reasons={} if token else {'after': 'START_OF_COMPONENT'}))
        result.extend(page['items'])
        if len(result) > maximum:
            raise InputGap('PROTOTYPE_PAGE_BOUND_EXCEEDED:' + component)
        token = page['next']
        if token is None:
            return result


@dataclass(frozen=True)
class NativeInputs:
    prepared: dict
    available_us: int
    source_refs: tuple
    covariance: pd.DataFrame
    covariance_available_us: int
    covariance_interval: str = '4h'


@dataclass(frozen=True)
class Order:
    order_id: str
    decision_id: str
    instrument_id: str
    action: str
    side: int
    quantity: int
    decision_us: int
    price: Fraction
    native_target: Fraction
    plan: object = None
    decision_view_ref: str | None = None


@dataclass(frozen=True)
class FillIntent:
    order: Order
    quantity: int
    signed_contracts: int
    price: Fraction
    at_us: int
    fee_cash: Fraction


class JointNativeBridge:
    def __init__(self, ledger, *, mode='controlled_required'):
        if mode not in ('controlled_required', 'synthetic_reference_demo'):
            raise InputGap('UNSUPPORTED_BRIDGE_MODE')
        c = ledger.config
        if (set(c['instruments']) != set(INSTRUMENTS) or exact(c['initial_cash_usdt']) != 10000
                or (mode == 'controlled_required' and c['ingestion_mode'] != 'controlled_adapters')):
            raise InputGap('ONE_SHARED_10000_ACCOUNT_AND_CONTROLLED_PORT_REQUIRED')
        self.ledger, self.mode, self.cfg = ledger, mode, research_config()
        self.timing, self.sizing = ExecutionTiming(), EntrySizingBook()
        self.pending, self.reductions = (), ()
        self.last_decision = None
        self.stopped = None
        self.close_receipts = {}
        self.finalized_episodes = {}
        self.used_opportunities = set()

    def release_episode(self, *, proposal, episode_id, cutoff):
        from .episode_export import export_episode
        exported = export_episode(self.ledger, cutoff=cutoff, episode_id=episode_id,
                                  proposal=proposal, close_receipts=self.close_receipts)
        if exported['qr014_episode_fields']['label_status'] != 'valid':
            raise InputGap('EPISODE_NOT_SETTLED_SCOPED_FINAL')
        if proposal['instrument_id'] == INSTRUMENTS[1]:
            raise InputGap('R01_R04_FINALITY_FEEDBACK_PORT_NOT_BOUND')
        self.finalized_episodes[episode_id] = deepcopy(proposal)
        return exported

    def finance(self, at_us, market, *, exclude_own_pending=False):
        view = self.ledger.as_known(dict(cutoff=dict(at_us=at_us, slot=0)))
        b = view['balance']
        lots = rows(self.ledger, view, 'lots')
        positions = {i: 0 for i in INSTRUMENTS}
        margin, exit_fees = Fraction(0), Fraction(0)
        reasons = []
        marks = {i: market.mark(i, at_us) for i in INSTRUMENTS}
        valuations = None
        for lot in lots:
            q, i = lot['remaining_contracts'], lot['instrument_id']
            positions[i] += q * (1 if lot['direction'] == 'long' else -1)
            margin += q * exact(lot['multiplier']) * exact(lot['entry_price']) / 200
        for i, q in positions.items():
            if not q:
                continue  # Proved flat U=0; no MARK needed merely to value zero.
            mark = marks[i]
            if mark.value is None:
                reasons.append('HELD_MARK_UNKNOWN:' + i)
                continue
            if self.mode == 'controlled_required':
                statuses = rows(self.ledger, view, 'query_status')
                known = [s for s in statuses if s['key']['instrument_id'] == i
                         and s['key']['query_at_us'] <= at_us]
                latest = max((s['key']['query_at_us'] for s in known), default=None)
                cohort = [s for s in known if s['key']['query_at_us'] == latest]
                if not cohort or any(s['status'] != 'SUPPORTED' or exact(s['mark_price']) != mark.value
                                     or s['source_at_us'] != mark.source_us for s in cohort):
                    reasons.append('R05_QUERY_BINDING_MISMATCH:' + i)
            else:
                if valuations is None:
                    valuations = [r['body'] for r in rows(self.ledger, view, 'events')
                                  if r['body']['record_type'] == 'Valuation']
                matched = [v for v in valuations if v['record_id'] in b['valuation_refs']
                           and v['instrument_id'] == i and v['mark_price'] is not None
                           and exact(v['mark_price']) == mark.value and v['valuation_at_us'] == mark.source_us]
                if not matched:
                    reasons.append('SYNTHETIC_LEDGER_MARK_MISMATCH:' + i)
            exit_fees += abs(q) * exact(MULTIPLIERS[i]) * mark.value * (1+SLIP) * FEE
        fields = ('cash_usdt', 'receivables_usdt', 'liabilities_usdt', 'unrealized_usdt', 'economic_equity_usdt')
        if any(b[k] is None for k in fields) or b['simulated_budget_usdt'] is None or view['coverage']:
            reasons.append('LEDGER_FINANCE_UNKNOWN')
        equity = budget = None
        if not reasons:
            cash, a, liability, u, equity = (exact(b[k]) for k in fields)
            if equity != cash+a-liability+u:
                raise InputGap('LEDGER_EQUITY_IDENTITY_MISMATCH')
            reserves = 0 if exclude_own_pending else sum((pending_reserve(o.quantity, o.instrument_id, o.price)
                                                        for o in self.pending), Fraction(0))
            budget = cash-liability+min(u, 0)-margin-exit_fees-reserves
        return dict(view=view, lots=lots, positions=positions, marks=marks, equity=equity, budget=budget,
                    held_margin=margin, held_exit_fees=None if reasons else exit_fees,
                    reasons=tuple(reasons), actual_exchange_margin=None)

    def _signals(self, inputs, at_us):
        if (not inputs.source_refs or inputs.available_us > at_us
                or inputs.covariance_available_us > at_us or inputs.covariance_interval != self.cfg.covariance_interval
                or set(inputs.prepared) != set(SYMBOLS)):
            raise InputGap('NATIVE_CAUSAL_INPUTS_UNAVAILABLE')
        cov = inputs.covariance
        if list(cov.index) != list(SYMBOLS) or list(cov.columns) != list(SYMBOLS):
            raise InputGap('FULL_ORDERED_JOINT_COVARIANCE_REQUIRED')
        a = np.asarray(cov, dtype=float)
        if (not np.isfinite(a).all() or np.any(np.diag(a) <= 0)
                or not np.array_equal(a, a.T) or np.min(np.linalg.eigvalsh(a)) < -1e-12):
            raise InputGap('INVALID_JOINT_COVARIANCE')
        result = {}
        for symbol in SYMBOLS:
            data = inputs.prepared[symbol]
            # No native fallback from a missing carry/adaptive cell to zero/one.
            sig = signals_core.signal_at(symbol, data, at_us/1_000_000, self.cfg)
            if sig is None:
                raise InputGap('NATIVE_SIGNAL_NOT_AVAILABLE:' + symbol)
            for key in ('carry_f', 'adaptive_risk_multiplier', 'adaptive_efficiency_ratio', 'adaptive_vol_ratio'):
                if not all(math.isfinite(float(v)) for v in data[key]):
                    raise InputGap('NATIVE_REQUIRED_CELL_UNKNOWN:' + key)
            if data['short_ts'][-1] != at_us/1_000_000-3600:
                raise InputGap('LATEST_NATIVE_CLOSED_HOUR_MISSING')
            if not math.isclose(float(cov.loc[symbol, symbol]), sig.vol_annual**2, rel_tol=1e-10, abs_tol=1e-12):
                raise InputGap('SIGNAL_AND_COVARIANCE_ANNUAL_UNITS_MISMATCH')
            result[symbol] = sig
        return result

    def decide(self, at_us, market, inputs):
        if self.stopped or at_us % HOUR or (self.last_decision is not None and at_us <= self.last_decision):
            raise InputGap('STOPPED_OR_DUPLICATE_OR_NONHOURLY_DECISION')
        joint_reason = None
        try:
            native = self._signals(inputs, at_us)
        except InputGap as exc:
            joint_reason = str(exc)
            native = {}
            # Missing joint inputs suppress allocation, not a healthy own-asset exit.
            if inputs.source_refs and inputs.available_us <= at_us:
                for symbol in SYMBOLS:
                    data = inputs.prepared.get(symbol)
                    if not data or data['short_ts'][-1] != at_us/1_000_000-3600:
                        continue
                    if any(not all(math.isfinite(float(v)) for v in data[k]) for k in
                           ('carry_f','adaptive_risk_multiplier','adaptive_efficiency_ratio','adaptive_vol_ratio')):
                        continue
                    sig = signals_core.signal_at(symbol, data, at_us/1_000_000, self.cfg)
                    if sig is not None:
                        native[symbol] = sig
        f = self.finance(at_us, market)
        prices = {}
        for i in INSTRUMENTS:
            try:
                prices[i] = exact(market.closed(i, at_us).close)
            except InputGap:
                joint_reason = 'JOINT_CLOSED_INPUT_MISSING'
        detached = ExecutionTiming()
        detached.restore(self.timing.dump())
        orders, allocation = [], None
        if joint_reason is None and f['equity'] is not None and f['equity'] > 0:
            # Exactly ONE allocation with both assets and the full covariance.
            allocation = pf.allocate_portfolio(native, float(f['equity']), inputs.covariance, self.cfg)
        for i, symbol in zip(INSTRUMENTS, SYMBOLS):
            if i not in prices or symbol not in native:
                continue
            held = f['positions'][i]
            current = held * exact(MULTIPLIERS[i]) * prices[i]
            sig = native[symbol]
            plan = None
            if allocation is None:
                # Only genuine capital-independent native forced exits. No dummy E.
                decision = detached.decide(symbol, float(current), float(current), sig.combined_forecast,
                                           sig.short_forecast, sig.main_forecast, sig.timing_feature,
                                           execution.TimingConfig(**self.cfg.execution_timing).for_symbol(symbol))
                actions = [('close', 'long' if held > 0 else 'short', abs(held))] if (
                    held and decision.force_rebalance and decision.target_notional == 0) else []
                target = Fraction(0)
            else:
                target_object = allocation.targets[symbol]
                plan = execution.decide_execution(symbol, target_object, sig, float(current), float(f['equity']),
                                                  self.cfg, detached, self.sizing, allow_increase=f['budget'] is not None)
                actions, _ = execution.build_order_plan(symbol, plan, 'long' if held > 0 else 'short' if held < 0 else None,
                                                       abs(held), float(prices[i]),
                                                       dict(quanto_multiplier=float(exact(MULTIPLIERS[i])), order_size_min=1),
                                                       float(FEE), float(SLIP*10000))
                target = Fraction.from_float(plan.target_notional)
                expected = round(abs(target)/(prices[i]*exact(MULTIPLIERS[i])))
                native_q = execution.notional_to_contracts(plan.target_notional, float(prices[i]), float(exact(MULTIPLIERS[i])))
                if expected != native_q:
                    raise InputGap('NATIVE_EXACT_QUANTITY_BOUNDARY_DISAGREEMENT')
            for action, side, q in actions:
                # Close-then-later-decision reversal, including timing-disabled BTC.
                if action == 'open' and held and (held > 0) != (side == 'long'):
                    continue
                if action == 'open' and not held:
                    old = [l for l in f['lots'] if l['instrument_id'] == i]
                    if old:
                        latest = max(old, key=lambda l: l['opened_at_us'])['episode_id']
                        prior = self.finalized_episodes.get(latest)
                        if prior is None:
                            continue
                        from .episode_export import export_episode
                        if export_episode(self.ledger,cutoff=dict(at_us=at_us,slot=0),episode_id=latest,
                                          proposal=prior,close_receipts=self.close_receipts)['qr014_episode_fields']['label_status'] != 'valid':
                            continue
                        if i == INSTRUMENTS[1]:
                            raise InputGap('R01_R04_FINALITY_FEEDBACK_PORT_NOT_BOUND')
                orders.append(Order(f'order:{at_us}:{symbol}:{action}', f'decision:{at_us}:{symbol}', i, action,
                                    1 if side == 'long' else -1, q, at_us, prices[i], target, plan, f['view']['view_sha256']))
        self.timing = detached
        self.last_decision = at_us
        if self.pending and any(o.action != 'open' or any(o.instrument_id == p.instrument_id and o.side != p.side
                                                       for p in self.pending) for o in orders):
            self.pending = ()  # Whole old basket, never only the selected coin.
        self.reductions = tuple(o for o in orders if o.action != 'open')
        increases = tuple(o for o in orders if o.action == 'open')
        reason = self.admit(increases, f, prices) if increases else 'NO_INCREASE'
        return dict(schema='qd010.joint-native.v1', decision_us=at_us, view_ref=f['view']['view_sha256'],
                    allocation=allocation, orders=tuple(orders), increase_status=reason,
                    finance_reasons=f['reasons'], joint_input_block_reason=joint_reason, production_ready=False)

    def _validate(self, orders, f, prices, *, filling=False):
        if f['equity'] is None or f['budget'] is None or f['equity'] <= 0:
            return 'ACCOUNT_FINANCE_UNKNOWN_OR_INSOLVENT'
        if len({o.instrument_id for o in orders}) != len(orders):
            return 'DUPLICATE_BASKET_INSTRUMENT'
        projected = dict(f['positions'])
        required = Fraction(0)
        for o in orders:
            i = o.instrument_id
            if (i not in INSTRUMENTS or o.action != 'open' or type(o.quantity) is not int
                    or not 1 <= o.quantity <= 10**9 or o.side not in (-1, 1) or prices[i] <= 0
                    or f['marks'][i].value is None):
                return 'INVALID_INCREASE_METADATA_OR_MARK'
            if projected[i] and projected[i] * o.side < 0:
                return 'REVERSAL_REQUIRES_LATER_DECISION'
            projected[i] += o.side*o.quantity
            required += pending_reserve(o.quantity, i, prices[i])
            sub = max(abs(o.native_target), abs(projected[i])*exact(MULTIPLIERS[i])*o.price)*(1+G)
            tier = max(sub, abs(projected[i])*exact(MULTIPLIERS[i])*prices[i]*(1+G))
            if tier > 1_000_000:
                return 'PER_INSTRUMENT_SYNTHETIC_TIER'
        values = {i: abs(q)*exact(MULTIPLIERS[i])*prices[i]*(1+SLIP if filling else 1+G) if q else Fraction(0)
                  for i, q in projected.items()}
        if any(v > f['equity']*Fraction('5.5') for v in values.values()) or sum(values.values()) > f['equity']*6:
            return 'JOINT_PROJECTED_EXPOSURE_CAP'
        return 'ADMITTED' if required <= f['budget'] else 'BASKET_BUDGET_INSUFFICIENT'

    def admit(self, orders, finance, prices):
        if self.pending:
            return 'BASKET_ALREADY_PENDING'
        reason = self._validate(orders, finance, prices)
        if reason == 'ADMITTED':
            self.pending = tuple(sorted(orders, key=lambda o: INSTRUMENTS.index(o.instrument_id)))
        return reason

    def opportunity(self, at_us, market):
        orders = self.reductions + self.pending
        if not orders or any(execution_boundary(o.decision_us) != at_us for o in orders):
            raise InputGap('NOT_THE_SINGLE_ELIGIBLE_OPPORTUNITY')
        key = at_us, tuple(o.order_id for o in orders)
        if key in self.used_opportunities:
            raise InputGap('OPPORTUNITY_ALREADY_CONSUMED')
        self.used_opportunities.add(key)
        f = self.finance(at_us, market, exclude_own_pending=True)
        opened = {}
        for i in INSTRUMENTS:
            try:
                opened[i] = exact(market.execution_open(i, at_us)['open_price'])
            except InputGap:
                pass
        required = {o.instrument_id for o in self.pending} | {i for i,q in f['positions'].items() if q}
        reason = ('EXECUTION_OPEN_UNAVAILABLE' if required-set(opened) else self._validate(self.pending, f, opened, filling=True)) if self.pending else 'ADMITTED'
        accepted = tuple(o for o in self.reductions if o.instrument_id in opened) + (self.pending if reason == 'ADMITTED' else ())
        capacities = {}
        for i in {o.instrument_id for o in accepted}:
            try:
                capacities[i] = int(exact(market.closed(i, at_us).volume_contracts)*Fraction('0.001'))
            except InputGap:
                capacities[i] = 0
        fills = []
        residuals = [(o.order_id, o.quantity) for o in self.pending] if reason != 'ADMITTED' else []
        residuals += [(o.order_id,o.quantity) for o in self.reductions if o.instrument_id not in opened]
        for o in sorted(accepted, key=lambda o: (o.action == 'open', INSTRUMENTS.index(o.instrument_id))):
            q = min(o.quantity, capacities[o.instrument_id])
            if o.action != 'open':
                q = min(q, abs(f['positions'][o.instrument_id]))
            capacities[o.instrument_id] -= q
            signed = o.side*q*(1 if o.action == 'open' else -1)
            price = opened[o.instrument_id]*(1+SLIP if signed > 0 else 1-SLIP)
            if q:
                fills.append(FillIntent(o, q, signed, price, at_us,
                                        -q*exact(MULTIPLIERS[o.instrument_id])*price*FEE))
            residuals.append((o.order_id, o.quantity-q))
        return dict(at_us=at_us, fills=tuple(fills), cancelled_residuals=tuple(residuals),
                    basket_status=reason, before=f['view']['view_sha256'],
                    status='REQUIRES_BOUND_LEDGER_TRANSACTION', finality_callbacks='NOT_PUBLISHED')

    def commit_bound_transaction(self, stage, request):
        """Commit a supplied real ledger request, never fabricate source witnesses.

        Controlled mode requires externally registered policy/execution ports and
        generated witnesses; these are an explicit remaining integration gap.
        Demo import requests can exercise the real ledger with tiny synthetic facts.
        """
        if self.stopped or request['through_us'] != stage['at_us']:
            raise InputGap('STOPPED_OR_TRANSACTION_CLOCK_MISMATCH')
        if self.mode == 'controlled_required':
            if request['imported'] or not request['generated']:
                raise InputGap('REGISTERED_NATIVE_PORT_AND_GENERATED_WITNESS_REQUIRED')
            bodies = [b for g in request['generated'] for b in g['result']['events']]
        else:
            bodies = [e['body'] for e in request['imported']]
        actual = [b for b in bodies if b['record_type'] == 'Fill']
        expected = stage['fills']
        if len(actual) != len(expected):
            raise InputGap('FILL_BATCH_COUNT_MISMATCH')
        for b, f in zip(sorted(actual, key=lambda b: b['order_id']), sorted(expected, key=lambda f: f.order.order_id)):
            if (b['order_id'] != f.order.order_id or b['decision_id'] != f.order.decision_id
                    or b['instrument_id'] != f.order.instrument_id or b['signed_contracts'] != f.signed_contracts
                    or b['filled_at_us'] != f.at_us or b['decision_at_us'] != f.order.decision_us
                    or b['available_at_us'] != f.at_us or exact(b['fill_price']) != f.price
                    or exact(b['fee_fraction']) != FEE or exact(b['multiplier']) != exact(MULTIPLIERS[f.order.instrument_id])):
                raise InputGap('FROZEN_FILL_BATCH_BINDING_MISMATCH')
        receipt = self.ledger.advance(request)  # One actual atomic financial transaction.
        self.pending, self.reductions = (), ()
        for body in actual:
            intent = next(f for f in expected if f.order.order_id == body['order_id'])
            if intent.order.action in ('close', 'reduce'):
                self.close_receipts[body['record_id']] = dict(fill_id=body['record_id'], order_id=body['order_id'],
                    decision_id=body['decision_id'], action=intent.order.action, decision_us=intent.order.decision_us,
                    instrument_id=body['instrument_id'], committed_audit_prefix=receipt['after']['audit_prefix'],
                    native_plan_sha256=fingerprint(asdict(intent.order.plan)) if intent.order.plan is not None else None,
                    decision_view_ref=intent.order.decision_view_ref)
        if any(f.order.instrument_id == INSTRUMENTS[1] for f in expected):
            self.stopped = 'LEDGER_COMMITTED_R01_R04_ATOMIC_NATIVE_FEEDBACK_PORT_NOT_BOUND'
        return dict(ledger_receipt=receipt, status='FINANCIAL_BATCH_COMMITTED',
                    native_feedback_status=self.stopped or 'BTC_TIMING_DISABLED', production_ready=False)
