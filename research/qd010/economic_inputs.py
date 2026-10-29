"""QD010 local SCENARIO adapters for caller-frozen records, never a data loader.

Times are integer UTC microseconds; quantities are contracts, prices USDT/base,
money USDT. A lookup proves support in the supplied prefix, not raw coverage.
No account data, network, historical MARK reconstruction or zero imputation.
"""
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import re

US = 1_000_000
HOUR = 3600 * US
INSTRUMENTS = ('gate:usdt:BTC_USDT', 'gate:usdt:ETH_USDT')
SYMBOLS = ('BTC_USDT', 'ETH_USDT')
MULTIPLIERS = dict(zip(INSTRUMENTS, ('0.0001', '0.01')))
FEE = Fraction('0.00075')
SLIP = Fraction('0.0005')
G = Fraction('0.0008')


class InputGap(ValueError):
    pass


def exact(value):
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if not isinstance(value, str) or not re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', value):
        raise InputGap('EXACT_DECIMAL_TEXT_REQUIRED')
    return Fraction(Decimal(value))


def text(value):
    """Lossless terminating rational to decimal, independent of Decimal context."""
    v = exact(value)
    denominator, a, b = v.denominator, 0, 0
    while denominator % 2 == 0:
        denominator //= 2
        a += 1
    while denominator % 5 == 0:
        denominator //= 5
        b += 1
    if denominator != 1:
        raise InputGap('NONTERMINATING_DECIMAL_KEEP_FRACTION')
    scale = max(a, b)
    digits = str(abs(v.numerator) * 2**(scale-a) * 5**(scale-b)).rjust(scale+1, '0')
    s = digits if not scale else (digits[:-scale] + '.' + digits[-scale:]).rstrip('0').rstrip('.')
    return ('-' if v < 0 else '') + s


def clock(value):
    if type(value) is not int or value < 0:
        raise InputGap('INTEGER_UTC_MICROSECONDS_REQUIRED')
    return value


@dataclass(frozen=True)
class Mark:
    instrument_id: str
    source_us: int
    price: str
    source_ref: str
    observed_available_us: int | None = None


@dataclass(frozen=True)
class Candle:
    instrument_id: str
    open_us: int
    open: str
    high: str
    low: str
    close: str
    volume_contracts: str
    source_ref: str
    available_us: int  # Full row; execution_open below exposes only the named proxy.


@dataclass(frozen=True)
class Funding:
    instrument_id: str
    source_us: int
    rate: str
    source_ref: str
    event_id: str


@dataclass(frozen=True)
class Selection:
    value: Fraction | None
    query_us: int
    source_us: int | None
    available_us: int | None
    source_refs: tuple
    reason: str | None
    basis: str = 'FROZEN_SUPPLIED_PREFIX_SCENARIO_NOT_RAW_COVERAGE_PROOF'


class FrozenInputs:
    def __init__(self, *, marks=(), candles=(), funding=()):
        self.marks, self.candles, self.funding = tuple(marks), tuple(candles), tuple(funding)
        for rows, time_name in ((self.marks, 'source_us'), (self.candles, 'open_us'), (self.funding, 'source_us')):
            seen = set()
            for row in rows:
                if row.instrument_id not in INSTRUMENTS or not row.source_ref:
                    raise InputGap('INSTRUMENT_OR_LINEAGE_MISSING')
                key = row.instrument_id, clock(getattr(row, time_name))
                if key in seen:
                    raise InputGap('DUPLICATE_FROZEN_KEY')
                seen.add(key)
        for row in self.marks:
            if exact(row.price) <= 0:
                raise InputGap('NONPOSITIVE_MARK')
        for row in self.candles:
            o, h, l, c, v = [exact(getattr(row, k)) for k in ('open', 'high', 'low', 'close', 'volume_contracts')]
            if (row.open_us % HOUR or clock(row.available_us) != row.open_us + HOUR
                    or min(o, h, l, c) <= 0 or v < 0 or h < max(o, l, c) or l > min(o, c)):
                raise InputGap('INVALID_CLOSED_HOURLY_ROW')
        for row in self.funding:
            exact(row.rate)
            if not row.event_id:
                raise InputGap('FUNDING_EVENT_ID_REQUIRED')

    def mark(self, instrument, at_us):
        clock(at_us)
        eligible = [r for r in self.marks if r.instrument_id == instrument
                    and r.source_us + 60*US <= at_us
                    and at_us - r.source_us <= 120*US
                    and at_us - (r.source_us + 60*US) <= 60*US]
        if not eligible:
            return Selection(None, at_us, None, None, (), 'MISSING_OR_STALE_MARK')
        row = max(eligible, key=lambda r: r.source_us)
        return Selection(exact(row.price), at_us, row.source_us, row.source_us + 60*US,
                         (row.source_ref,), None)

    def closed(self, instrument, at_us):
        rows = [r for r in self.candles if r.instrument_id == instrument
                and r.open_us == at_us-HOUR and r.available_us <= at_us]
        if len(rows) != 1:
            raise InputGap('LATEST_CLOSED_HOUR_UNAVAILABLE')
        return rows[0]

    def execution_open(self, instrument, at_us):
        """Approved retrospective open proxy. Never return H/L/C/V to a decision."""
        rows = [r for r in self.candles if r.instrument_id == instrument and r.open_us == at_us]
        if len(rows) != 1 or at_us % HOUR:
            raise InputGap('EXECUTION_OPEN_UNAVAILABLE')
        r = rows[0]
        return dict(instrument_id=instrument, open_us=at_us, open_price=r.open,
                    source_ref=r.source_ref, basis='EXECUTION_ONLY_RETROSPECTIVE_OPEN_PROXY')

    def funding_terms(self, event_id, signed_contracts, as_of_us):
        if type(signed_contracts) is not int:
            raise InputGap('INTEGER_SNAPSHOT_CONTRACTS_REQUIRED')
        rows = [r for r in self.funding if r.event_id == event_id]
        if len(rows) != 1:
            raise InputGap('FUNDING_EVENT_ID_NOT_UNIQUE')
        r = rows[0]
        available = (r.source_us // HOUR + 1) * HOUR
        mark = self.mark(r.instrument_id, r.source_us)
        amount = None if as_of_us < available or mark.value is None else (
            -signed_contracts * exact(MULTIPLIERS[r.instrument_id]) * mark.value * exact(r.rate))
        return dict(schema='qd010.economic-inputs.v1', event_id=event_id,
                    snapshot_us=r.source_us, nominal_settlement_us=None,
                    rate_available_us=available, amount_available_us=available if mark.value is not None else None,
                    signed_amount_usdt=amount, posting_us=available+60*US if amount is not None else None,
                    source_refs=(r.source_ref,) + mark.source_refs,
                    reason=mark.reason or ('RATE_NOT_YET_AVAILABLE' if as_of_us < available else None),
                    basis='FUNDING_SOURCE_T_PROXY_HOUR_KNOWLEDGE_R1')


def execution_boundary(decision_us):
    return ((clock(decision_us) + US + HOUR - 1) // HOUR) * HOUR


def finality_not_before(natural_close_us, required_input_us, posting_us):
    return max((clock(natural_close_us),) + tuple(required_input_us) + tuple(posting_us)) + HOUR


def pending_reserve(quantity, instrument, price):
    n = quantity * exact(MULTIPLIERS[instrument]) * exact(price)
    return n*(1+G)/200 + 2*FEE*n*(1+G) + n*G


def qr014_candle_fields(row):
    """Field mapping only; consumer constructs its own Candle, without imports here."""
    return dict(instrument_id=row.instrument_id,bar_open_us=row.open_us,bar_close_us=row.open_us+HOUR,
                research_available_at_us=row.available_us,open=row.open,high=row.high,low=row.low,
                close=row.close,volume_contracts=row.volume_contracts,source_ref=row.source_ref)
