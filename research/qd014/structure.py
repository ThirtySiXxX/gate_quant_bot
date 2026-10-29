"""Versioned local schedule compression and rebuildable bounded-range indexes.

Wire plans are JSON. Runtime indexes never enter a hash, checkpoint or adapter
state. Financial events and results remain in their existing formats.
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from research.qd009 import streaming_ledger as sl

SCHEDULE = 'qd014.schedule-grid.v1'
REQUIREMENTS = 'qd014.mark-grid.v1'
REFERENCE = 'qd014.static-plan-ref.v1'
WINDOW = 'qd014.plan-window.v1'
RECEIPTS = 'qd014.active-funding-receipts.v1'
PENDING_RATES = 'qd014.pending-funding.v1'


def wire(times, order, instruments, purposes, economic_end):
    return (dict(schema=SCHEDULE, times_us=times, order=list(order)),
            dict(schema=REQUIREMENTS, clock_id='mark-clock',
                 instruments=list(instruments), purposes=list(purposes), before_end_us=economic_end))


def reference(schedule, requirements, funding):
    return dict(schema=REFERENCE, sha256=sl.digest(dict(schedule=schedule,
                mark_requirements=requirements, expected_snapshots=funding)))


class Plan:
    def __init__(self, config):
        sl.need(type(config['schedule']) in (list,dict), 'UNSUPPORTED_VERSION')
        self.compact = type(config['schedule']) is dict
        self.end = config['end_exclusive_us']
        self.schedule = config['schedule']
        self.requirements = config['mark_requirements']
        sl.need(type(self.requirements) is (dict if self.compact else list), 'UNSUPPORTED_VERSION')
        self.by_cohort, self.by_slot, self.by_time = defaultdict(list), defaultdict(list), defaultdict(list)
        if self.compact:
            s, r = self.schedule, self.requirements
            sl.shape(s, 'schema times_us order'); sl.need(s['schema'] == SCHEDULE, 'UNSUPPORTED_VERSION')
            sl.shape(r, 'schema clock_id instruments purposes before_end_us')
            sl.need(r['schema'] == REQUIREMENTS and r['before_end_us'] == self.end, 'UNSUPPORTED_VERSION')
            self.times = tuple(s['times_us']); self.order = tuple(s['order'])
            sl.need(self.times and len(self.order) == len(set(self.order)) and set(self.order) == {a['adapter_id'] for a in config['adapters']}, 'SCHEDULE_MISMATCH')
            sl.need(all(type(t) is int and config['initial_at_us'] <= t < config['knowledge_end_exclusive_us'] for t in self.times), 'SCHEDULE_MISMATCH')
            sl.need(all(a < b for a, b in zip(self.times, self.times[1:])), 'SCHEDULE_MISMATCH')
            sl.need(type(r['instruments']) is list and r['instruments'] and len(set(r['instruments'])) == len(r['instruments']), 'SCHEDULE_MISMATCH')
            sl.need(set(r['instruments']) <= set(config['instruments']) and r['purposes'] and len(set(r['purposes'])) == len(r['purposes']) and set(r['purposes']) <= set(sl.PURPOSES), 'SCHEDULE_MISMATCH')
            clocks = {(x['instrument_id'], x['clock_id']) for x in config['mark_clocks']}
            sl.need(all((i, r['clock_id']) in clocks for i in r['instruments']), 'SCHEDULE_MISMATCH')
            bindings = {(x['instrument_id'],x['clock_id']) for x in config['mark_view_bindings']}
            if set(r['purposes']) & {'valuation','reservation'}:
                sl.need(all((i,r['clock_id']) in bindings for i in r['instruments']), 'SCHEDULE_MISMATCH')
            self.ref = reference(s, r, config['expected_snapshots'])
            for a in config['adapters']:
                cfg = a['causal_config']
                sl.need(cfg.get('static_plan_ref') == self.ref and 'ticks' not in cfg and 'funding_schedule' not in cfg, 'INPUT_BINDING_MISMATCH')
        else:
            self.times = tuple(t['at_us'] for t in self.schedule)
            self.ticks = {t['at_us']: t for t in self.schedule}
            for r in self.requirements:
                k = r['key']; self.by_time[k['query_at_us']].append(r)
                self.by_cohort[(k['instrument_id'], k['clock_id'], k['query_at_us'])].append(k['purpose'])
                for slot in r['before_slots']: self.by_slot[(slot, k['instrument_id'])].append(k)
            self.query_times = sorted(self.by_time)
        self.funding_by_id = {e['event_id']: e for e in config['expected_snapshots']}
        if self.compact:
            sl.need(len(self.funding_by_id)==len(config['expected_snapshots']), 'ID_SCOPE_CONFLICT')
        self.funding_at = defaultdict(list)
        for e in config['expected_snapshots']: self.funding_at[e['snapshot_at_us']].append(e)
        self.work = dict(tick_lookups=0, range_lookups=0, requirements_returned=0, window_funding_rows=0)

    def tick(self, at):
        self.work['tick_lookups'] += 1
        pos = bisect_left(self.times, at)
        if pos == len(self.times) or self.times[pos] != at: return None
        if not self.compact: return self.ticks[at]
        return dict(at_us=at, slots=[dict(slot_id=k+':'+str(at), adapter_id=k, phase=n) for n, k in enumerate(self.order)])

    def between(self, lower, upper):
        self.work['range_lookups'] += 1
        return self.times[bisect_right(self.times, lower):bisect_right(self.times, upper)]

    def __iter__(self):
        for at in self.times: yield self.tick(at)

    def due(self, lower, upper):
        times = self.between(lower, min(upper, self.end-1)) if self.compact else self.query_times[bisect_right(self.query_times, lower):bisect_right(self.query_times, upper)]
        for at in times:
            if self.compact:
                r = self.requirements
                rows = (dict(key=dict(instrument_id=i, clock_id=r['clock_id'], query_at_us=at, purpose=p),
                    before_slots=[k+':'+str(at) for k in self.order], for_view=p in ('valuation','reservation'))
                    for i in r['instruments'] for p in r['purposes'])
            else: rows = self.by_time[at]
            for row in rows:
                self.work['requirements_returned'] += 1
                yield row

    def purposes(self, key):
        if self.compact: return set(self.requirements['purposes'])
        return set(self.by_cohort[(key['instrument_id'], key['clock_id'], key['query_at_us'])])

    def for_slot(self, slot, inst, at):
        if not self.compact: return self.by_slot[(slot, inst)]
        return [r['key'] for r in self.due(at-1, at) if r['key']['instrument_id'] == inst and slot in r['before_slots']]

    def cursor_count(self, inst, clock, at):
        if self.compact:
            r = self.requirements
            return bisect_right(self.times, min(at, self.end-1))*len(r['purposes']) if inst in r['instruments'] and clock == r['clock_id'] else 0
        return sum(1 for r in self.requirements if (r['key']['instrument_id'],r['key']['clock_id']) == (inst,clock) and r['key']['query_at_us'] <= at)

    def pending(self, prior):
        funds = prior['value']['data'].get('funding', {})
        return [self.funding_by_id[k] for k, f in funds.items() if not f['posted'] and f['ranges']]

    def window(self, definition, prior, at):
        cfg = dict(definition['causal_config'])
        pos = bisect_right(self.times, at)
        cfg['ticks'] = list(self.times[pos:pos+1])
        pending = self.pending(prior) if definition['adapter_id'] == 'environment' else []
        rows = {e['event_id']: e for e in pending + self.funding_at.get(at, [])} if definition['adapter_id'] == 'environment' else {}
        cfg['funding_schedule'] = sorted(rows.values(), key=lambda e: (e['snapshot_at_us'], e['instrument_id']))
        self.work['window_funding_rows'] += len(rows)
        cfg['static_window'] = dict(schema=WINDOW, plan_sha256=self.ref['sha256'], at_us=at)
        return cfg


def validate_window(packet):
    cfg = packet['causal_config']; ref = cfg['static_plan_ref']; w = cfg['static_window']
    sl.shape(ref, 'schema sha256'); sl.shape(w, 'schema plan_sha256 at_us')
    sl.need(ref['schema'] == REFERENCE and w['schema'] == WINDOW and w['plan_sha256'] == ref['sha256'] and w['at_us'] == packet['slot']['at_us'], 'INPUT_BINDING_MISMATCH')
    if packet['prior_state']['adapter_id'] == 'environment' and packet['previous_invocation'] is not None:
        marker = packet['prior_state']['value']['data'].get('heads', {}).get('_qd014_storage')
        sl.need(marker == dict(schema=RECEIPTS, plan_sha256=ref['sha256']), 'UNSUPPORTED_VERSION')


def compact_receipts(data, ref):
    # Only receipts with no remaining computation are removed. All original
    # generated snapshots/revisions/postings remain in the immutable ledger.
    data['funding'] = {k: f for k, f in data.get('funding', {}).items() if f['ranges'] and not f['posted']}
    data.setdefault('heads', {})['_qd014_storage'] = dict(schema=RECEIPTS, plan_sha256=ref['sha256'])
