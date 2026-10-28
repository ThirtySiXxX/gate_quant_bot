"""QR014 research-local features and sample assembly; no I/O, signals or fitting.

These dataclasses are explicit adapter inputs, NOT the current QD export schema.
The caller must map an accepted, scoped, as-known episode export to Episode.
Finality/settlement flags and evidence references attest upstream work: this module
does not reconstruct cashflows, prove completeness or replace the economic ledger.
"""
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import math
import re

HOUR_US = 3_600_000_000
EMBARGO_US = 24 * HOUR_US
TRAIN_START_US = 1_704_067_200_000_000
TRAIN_END_US = 1_735_689_600_000_000
VALID_END_US = 1_767_225_600_000_000
ECONOMIC_END_US = 1_790_812_800_000_000
TAIL_END_US = ECONOMIC_END_US + 2 * HOUR_US
INSTRUMENTS = ('gate:usdt:BTC_USDT', 'gate:usdt:ETH_USDT')
FEATURE_SET = 'qr013.hourly-episode-entry-v1-proposed'
LOCAL_SCHEMA = 'qr014.feature-samples.v1'
FEATURE_NAMES = (
    'proposal_aligned_return_1h', 'proposal_aligned_return_4h',
    'proposal_aligned_return_24h', 'proposal_aligned_return_168h',
    'volatility_24h', 'volatility_72h', 'volume_relative_24h',
    'volume_relative_168h', 'range_pct', 'efficiency_24h',
    'proposal_side', 'is_eth',
)
FEATURE_UNITS = (
    ('dimensionless_log_return',) * 4
    + ('hourly_log_return_standard_deviation_not_annualized',) * 2
    + ('dimensionless_log_ratio',) * 2
    + ('dimensionless_ratio_not_percentage_points', 'dimensionless_ratio',
       'signed_category', 'binary_indicator')
)
LABEL_STATES = ('valid', 'open', 'immature', 'censored', 'invalid')


class InputError(ValueError):
    """Malformed or conflicting adapter input: stop, never overwrite silently."""


def _time(value, name):
    if type(value) is not int or value < 0:
        raise InputError('INVALID_UTC_MICROSECONDS:' + name)
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise InputError('MISSING_IDENTITY:' + name)
    return value


def _refs(values, name, required=True):
    if not isinstance(values, tuple) or (required and not values):
        raise InputError('MISSING_EVIDENCE:' + name)
    for value in values:
        _text(value, name)


def _decimal(value):
    # Canonical exact sources use ordinary decimal text, never binary floats.
    if (not isinstance(value, str) or len(value) > 1024
            or re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', value) is None):
        raise InputError('INVALID_EXACT_DECIMAL')
    number = Decimal(value)
    if not number.is_finite():
        raise InputError('NONFINITE_DECIMAL')
    return number


def _finite_projection(number):
    value = float(number)
    if not math.isfinite(value) or (number != 0 and value == 0):
        raise InputError('UNREPRESENTABLE_BINARY64')
    return value


@dataclass(frozen=True)
class Candle:
    instrument_id: str
    bar_open_us: int
    bar_close_us: int
    research_available_at_us: int
    open: str
    high: str
    low: str
    close: str
    volume_contracts: str
    source_ref: str


@dataclass(frozen=True)
class EntryProposal:
    account_id: str
    trajectory_id: str
    instrument_id: str
    proposal_id: str
    pre_decision_state_ref: str
    scenario_id: str
    policy_id: str
    account_binding_id: str
    decision_us: int
    side: int
    flat_before: bool
    action: str
    source_refs: tuple[str, ...]


def _proposal(p):
    for key in ('account_id', 'trajectory_id', 'proposal_id', 'pre_decision_state_ref'):
        _text(getattr(p, key), key)
    if p.instrument_id not in INSTRUMENTS:
        raise InputError('UNSUPPORTED_INSTRUMENT')
    if (p.scenario_id, p.policy_id, p.account_binding_id) != ('P0', 'ALLOW_ALL', 'QR010_SHARED_NATIVE_X10'):
        raise InputError('ONLY_APPROVED_BASELINE_LABEL_SOURCE')
    if _time(p.decision_us, 'decision') % HOUR_US:
        raise InputError('DECISION_NOT_HOURLY')
    if type(p.side) is not int or p.side not in (-1, 1):
        raise InputError('INVALID_PROPOSAL_SIDE')
    if p.flat_before is not True or p.action != 'flat_entry':
        raise InputError('ONLY_PRE_MODEL_FLAT_ENTRY_PROPOSALS')
    _refs(p.source_refs, 'proposal')
    return (p.account_id, p.trajectory_id, p.instrument_id, p.proposal_id)


@dataclass(frozen=True)
class FeatureRow:
    proposal: EntryProposal
    values: tuple[float, ...] | None
    reasons: tuple[str, ...]
    available_at_us: int | None
    max_source_available_at_us: int | None
    candle_source_refs: tuple[str, ...]
    feature_set: str = FEATURE_SET
    names: tuple[str, ...] = FEATURE_NAMES
    units: tuple[str, ...] = FEATURE_UNITS


def features_for_proposal(candles, proposal):
    """Consume only the supplied ordered single-asset prefix before decision.

    Caller supplies in-memory Candle records; no raw loader or full-matrix runner.
    Future rows are not inspected beyond their open timestamp. No sorting, gap
    repair or fallback to an older available vector. Invalid/unavailable rows
    reset the 169-hour window; duplicate/decreasing prefix times are hard errors.
    """
    _proposal(proposal)
    tail = deque(maxlen=169)
    previous = None
    last_issue = 'INSUFFICIENT_CONTIGUOUS_HISTORY'
    for bar in candles:
        opened = _time(bar.bar_open_us, 'bar_open')
        if opened >= proposal.decision_us:
            break
        if bar.instrument_id != proposal.instrument_id:
            raise InputError('MIXED_INSTRUMENT_PREFIX')
        if previous is not None and opened <= previous:
            raise InputError('DUPLICATE_OR_DECREASING_CANDLE')
        if previous is not None and opened != previous + HOUR_US:
            tail.clear()
            last_issue = 'HOURLY_GAP'
        previous = opened
        try:
            closed = _time(bar.bar_close_us, 'bar_close')
            available = _time(bar.research_available_at_us, 'bar_available')
            if opened % HOUR_US or closed != opened + HOUR_US:
                raise InputError('INVALID_HOURLY_BOUNDARY')
            if available < closed:
                raise InputError('AVAILABILITY_BEFORE_CLOSE')
            if closed > proposal.decision_us or available > proposal.decision_us:
                raise InputError('CANDLE_NOT_AVAILABLE_AT_DECISION')
            if available != closed:
                raise InputError('UNAPPROVED_BAR_AVAILABILITY_BASIS')
            _text(bar.source_ref, 'candle_source')
            raw = tuple(_decimal(getattr(bar, name)) for name in
                        ('open', 'high', 'low', 'close', 'volume_contracts'))
            o, h, l, c, v = raw
            if min(o, h, l, c) <= 0 or v < 0 or h < max(o, l, c) or l > min(o, c):
                raise InputError('INVALID_OHLCV_DOMAIN')
            projected = tuple(_finite_projection(number) for number in raw)
        except InputError as exc:
            tail.clear()
            last_issue = str(exc)
            continue
        tail.append((bar, projected))

    def unavailable(reason):
        return FeatureRow(proposal, None, (reason,), None, None, ())

    if previous != proposal.decision_us - HOUR_US:
        return unavailable('LATEST_CLOSED_HOUR_MISSING')
    if len(tail) != 169:
        return unavailable(last_issue + ':NEED_169_CONTIGUOUS_VALID_AVAILABLE_BARS')
    close = [item[1][3] for item in tail]
    volume = [item[1][4] for item in tail]
    try:
        values = [proposal.side * math.log(close[-1] / close[-1-h])
                  for h in (1, 4, 24, 168)]
        returns = [math.log(close[i] / close[i-1]) for i in range(1, len(close))]
        for h in (24, 72):
            recent = returns[-h:]
            mean = math.fsum(recent) / h
            values.append(math.sqrt(math.fsum((r-mean)**2 for r in recent) / (h-1)))
        for h in (24, 168):
            values.append(math.log((volume[-1]+1) / (math.fsum(volume[-h:])/h+1)))
        values.append((tail[-1][1][1]-tail[-1][1][2]) / close[-1])
        travel = math.fsum(abs(close[i]-close[i-1]) for i in range(len(close)-24, len(close)))
        if travel == 0:
            return unavailable('ZERO_EFFICIENCY_DENOMINATOR')
        values.extend((abs(close[-1]-close[-25])/travel, float(proposal.side),
                       float(proposal.instrument_id == INSTRUMENTS[1])))
        if not all(math.isfinite(value) for value in values):
            return unavailable('NONFINITE_FEATURE')
    except (OverflowError, ZeroDivisionError, ValueError):
        return unavailable('NUMERIC_FEATURE_FAILURE')
    return FeatureRow(proposal, tuple(values), (), proposal.decision_us,
                      max(item[0].research_available_at_us for item in tail),
                      tuple(item[0].source_ref for item in tail))


@dataclass(frozen=True)
class Episode:
    """One accepted as-known revision; totals/evidence are supplied by producer.

    Availability tuples include EVERY required input, posting and current scoped
    completeness assertion. completeness_verified means the accepted upstream
    checker verified fills/fees/funding plus all linked revisions/postings, not
    simply a funding-only watermark. A reference is not a proof generated here.
    """
    proposal: EntryProposal
    episode_id: str
    label_revision: int
    label_status: str
    first_fill_us: int | None
    label_end_us: int | None
    label_known_at_us: int | None
    net_cash_exact: str | None
    gross_entry_notional_exact: str | None
    natural_exit: bool
    cash_settled: bool
    completeness_verified: bool
    input_available_us: tuple[int, ...]
    posting_available_us: tuple[int, ...]
    assertion_available_us: tuple[int, ...]
    as_known_view_ref: str
    scoped_completeness_ref: str | None
    source_refs: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class InformationInterval:
    instrument_id: str
    start_us: int
    end_us: int | None
    source_ref: str


@dataclass(frozen=True)
class PurgeContext:
    """Externally enumerated heldout information scope, including both coins."""
    complete: bool
    instruments: tuple[str, ...]
    source_ref: str
    intervals: tuple[InformationInterval, ...]


def _interval(value):
    if value.instrument_id not in INSTRUMENTS:
        raise InputError('UNSUPPORTED_PURGE_INSTRUMENT')
    _time(value.start_us, 'information_start')
    if value.end_us is not None and _time(value.end_us, 'information_end') < value.start_us:
        raise InputError('REVERSED_INFORMATION_INTERVAL')
    _text(value.source_ref, 'information_source')


def _overlap(start, end, interval):
    # Closed endpoints are deliberately conservative: touching information purges.
    return start <= (interval.end_us if interval.end_us is not None else math.inf) and interval.start_us <= end


def _episode(e):
    key = _proposal(e.proposal)
    _text(e.episode_id, 'episode')
    _text(e.as_known_view_ref, 'as_known_view')
    _refs(e.source_refs, 'episode')
    if type(e.label_revision) is not int or e.label_revision < 1:
        raise InputError('INVALID_LABEL_REVISION')
    if e.label_status not in LABEL_STATES:
        raise InputError('INVALID_LABEL_STATUS')
    for flag in (e.natural_exit, e.cash_settled, e.completeness_verified):
        if type(flag) is not bool:
            raise InputError('INVALID_FINALITY_FLAG')
    for name in ('input_available_us', 'posting_available_us', 'assertion_available_us'):
        times = getattr(e, name)
        if not isinstance(times, tuple):
            raise InputError('AVAILABILITY_TUPLE_REQUIRED')
        for ts in times:
            _time(ts, name)
    for name in ('first_fill_us', 'label_end_us', 'label_known_at_us'):
        if getattr(e, name) is not None:
            _time(getattr(e, name), name)
    if e.first_fill_us is None:
        raise InputError('EPISODE_REQUIRES_REALIZED_ENTRY')
    if e.first_fill_us is not None and e.first_fill_us < e.proposal.decision_us:
        raise InputError('FILL_PRECEDES_PROPOSAL')
    if e.label_end_us is not None and (e.first_fill_us is None or e.label_end_us < e.first_fill_us):
        raise InputError('END_WITHOUT_ORDERED_ENTRY_FILL')
    if e.label_end_us is not None and not e.natural_exit:
        raise InputError('LABEL_END_MUST_BE_A_NATURAL_EXIT')
    for value in (e.net_cash_exact, e.gross_entry_notional_exact):
        if value is not None:
            _decimal(value)
    if e.label_status != 'valid':
        _refs(e.reasons, 'nonvalid_reason')
        if e.label_known_at_us is not None:
            raise InputError('NONVALID_LABEL_CANNOT_HAVE_KNOWN_TARGET_TIME')
        if e.label_status == 'open' and (e.label_end_us is not None or e.natural_exit):
            raise InputError('OPEN_EPISODE_CANNOT_BE_NATURALLY_CLOSED')
        if e.label_status == 'immature' and (e.label_end_us is None or not e.natural_exit):
            raise InputError('IMMATURE_EPISODE_REQUIRES_NATURAL_CLOSE')
        return key
    if not (e.natural_exit and e.cash_settled and e.completeness_verified):
        raise InputError('VALID_LABEL_REQUIRES_NATURAL_SETTLED_COMPLETE')
    if e.first_fill_us is None or e.label_end_us is None or e.label_known_at_us is None:
        raise InputError('VALID_LABEL_MISSING_CLOCK')
    if not e.input_available_us or not e.assertion_available_us:
        raise InputError('VALID_LABEL_MISSING_AVAILABILITY_EVIDENCE')
    _text(e.scoped_completeness_ref, 'scoped_completeness')
    expected = max((e.label_end_us,) + e.input_available_us + e.posting_available_us + e.assertion_available_us)
    if e.label_known_at_us != expected:
        raise InputError('LABEL_KNOWN_AT_DOES_NOT_MATCH_REQUIRED_EVIDENCE')
    _decimal(e.net_cash_exact)
    if _decimal(e.gross_entry_notional_exact) <= 0:
        raise InputError('NONPOSITIVE_GROSS_ENTRY_DENOMINATOR')
    if e.reasons:
        raise InputError('VALID_LABEL_WITH_INVALIDITY_REASONS')
    return key


def target_fraction_12(net_cash_exact, gross_entry_notional_exact):
    """Exact rational rounding to 12 decimals, HALF_EVEN; no cost deductions."""
    numerator, denominator = _decimal(net_cash_exact), _decimal(gross_entry_notional_exact)
    if denominator <= 0:
        raise InputError('NONPOSITIVE_GROSS_ENTRY_DENOMINATOR')
    ratio = Fraction(numerator) / Fraction(denominator)
    q, remainder = divmod(abs(ratio.numerator) * 10**12, ratio.denominator)
    if remainder * 2 > ratio.denominator or (remainder * 2 == ratio.denominator and q % 2):
        q += 1
    sign = '-' if ratio < 0 and q else ''
    return f'{sign}{q // 10**12}.{q % 10**12:012d}'


def _feature(row):
    key = _proposal(row.proposal)
    if row.feature_set != FEATURE_SET or row.names != FEATURE_NAMES or row.units != FEATURE_UNITS:
        raise InputError('FEATURE_IDENTITY_OR_ORDER_MISMATCH')
    if row.values is None:
        _refs(row.reasons, 'feature_unavailable_reason')
    else:
        if (len(row.values) != 12 or row.reasons
                or any(type(v) not in (float, int) or not math.isfinite(v) for v in row.values)):
            raise InputError('INVALID_FEATURE_VECTOR')
        _refs(row.candle_source_refs, 'feature_lineage')
        if len(row.candle_source_refs) != 169:
            raise InputError('FEATURE_REQUIRES_169_SOURCE_REFS')
        if (row.available_at_us is None or row.max_source_available_at_us is None
                or not _time(row.max_source_available_at_us, 'feature_source')
                <= _time(row.available_at_us, 'feature_available') <= row.proposal.decision_us):
            raise InputError('FEATURE_NOT_AVAILABLE_AT_DECISION')
    return key


def _partition(decision):
    if TRAIN_START_US <= decision < TRAIN_END_US:
        return 'train_2024'
    if TRAIN_END_US <= decision < VALID_END_US:
        return 'validation_2025'
    if VALID_END_US <= decision < ECONOMIC_END_US:
        return 'exposed_audit_2026'
    return 'outside_approved_window'


def assemble_samples(feature_rows, episodes, *, accepted_export_ref,
                     input_received_at_us, assembled_at_us, purge_context):
    """Return eligible/excluded records only; never estimates parameters or fits.

    Actual data receipt is separate from simulated historical eligibility.
    Caller must later check receipt<=real fit time. All declared identities are
    unique, even if repeated records are identical or have different revisions.
    The accepted exporter, not this function, resolves as-known revisions.
    """
    _text(accepted_export_ref, 'accepted_export')
    if _time(input_received_at_us, 'receipt') > _time(assembled_at_us, 'assembled'):
        raise InputError('INPUT_RECEIPT_IN_FUTURE')
    if (type(purge_context.complete) is not bool or
            set(purge_context.instruments) != set(INSTRUMENTS) or len(purge_context.instruments) != 2):
        raise InputError('PURGE_CONTEXT_REQUIRES_BOTH_INSTRUMENTS')
    _text(purge_context.source_ref, 'purge_context')
    intervals = list(purge_context.intervals)
    for interval in intervals:
        _interval(interval)
    features, labels, episode_keys = {}, {}, set()
    for row in feature_rows:
        key = _feature(row)
        if key in features:
            raise InputError('DUPLICATE_OR_CONFLICTING_PROPOSAL_FEATURE')
        features[key] = row
    for e in episodes:
        key = _episode(e)
        episode_key = key[:3] + (e.episode_id,)
        if key in labels or episode_key in episode_keys:
            raise InputError('DUPLICATE_OR_CONFLICTING_EPISODE_IDENTITY')
        labels[key] = e
        episode_keys.add(episode_key)
        if key in features and features[key].proposal != e.proposal:
            raise InputError('LABEL_PROPOSAL_IDENTITY_CONFLICT')
        if _partition(e.proposal.decision_us) in ('validation_2025', 'exposed_audit_2026'):
            intervals.append(InformationInterval(e.proposal.instrument_id,
                             e.proposal.decision_us, e.label_known_at_us, e.source_refs[0]))
    records = []
    for key in list(features) + [key for key in labels if key not in features]:
        row, e = features.get(key), labels.get(key)
        p = row.proposal if row is not None else e.proposal
        split = _partition(p.decision_us)
        reasons, target = [], None
        if row is None:
            reasons.append('MISSING_PROPOSAL_FEATURE')
        elif row.values is None:
            reasons.extend(row.reasons)
        if split == 'outside_approved_window':
            reasons.append('OUTSIDE_APPROVED_WINDOW')
        if e is None:
            reasons.append('NO_REALIZED_EPISODE_LABEL')
        elif e.label_status != 'valid':
            reasons.extend(('LABEL_' + e.label_status.upper(),) + e.reasons)
        else:
            target = target_fraction_12(e.net_cash_exact, e.gross_entry_notional_exact)
            if e.label_end_us >= ECONOMIC_END_US:
                reasons.append('NATURAL_EXIT_OUTSIDE_ECONOMIC_WINDOW')
            if split == 'train_2024':
                if e.label_end_us + EMBARGO_US >= TRAIN_END_US:
                    reasons.append('LABEL_END_STRICT_24H_FAILED')
                if e.label_known_at_us + EMBARGO_US >= TRAIN_END_US:
                    reasons.append('LABEL_KNOWN_STRICT_24H_FAILED')
                if not purge_context.complete:
                    reasons.append('PURGE_CONTEXT_INCOMPLETE')
                if any(_overlap(p.decision_us, e.label_known_at_us, interval) for interval in intervals):
                    reasons.append('CROSS_ASSET_HELDOUT_INFORMATION_OVERLAP')
            elif split == 'validation_2025':
                if e.label_end_us >= VALID_END_US or e.label_known_at_us > VALID_END_US:
                    reasons.append('NOT_MATURE_BY_VALIDATION_BOUNDARY')
            elif split == 'exposed_audit_2026' and e.label_known_at_us >= TAIL_END_US:
                reasons.append('NOT_MATURE_BEFORE_EVIDENCE_TAIL_END')
        eligible = not reasons
        records.append(dict(
            schema=LOCAL_SCHEMA, proposal=p, episode_id=e.episode_id if e else None,
            label_revision=e.label_revision if e else None, label_status=e.label_status if e else None,
            partition=split, included=eligible, train_eligible=eligible and split == 'train_2024',
            reasons=tuple(dict.fromkeys(reasons)), feature_names=FEATURE_NAMES,
            features=row.values if row else None, feature_available_at_us=row.available_at_us if row else None,
            candle_source_refs=row.candle_source_refs if row else (),
            episode_source_refs=e.source_refs if e else (), accepted_export_ref=accepted_export_ref,
            as_known_view_ref=e.as_known_view_ref if e else None,
            scoped_completeness_ref=e.scoped_completeness_ref if e else None,
            net_cash_exact=e.net_cash_exact if e else None,
            gross_entry_notional_exact=e.gross_entry_notional_exact if e else None,
            target_fraction_12=target, model_target_fraction_12=target if eligible else None,
            label_end_us=e.label_end_us if e else None, label_known_at_us=e.label_known_at_us if e else None,
            actual_input_received_at_us=input_received_at_us, assembled_at_us=assembled_at_us,
            training_authorized=False,
        ))
    return tuple(records)
