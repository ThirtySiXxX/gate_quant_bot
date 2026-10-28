"""Frozen v3/CSV readers. Default is no raw access; no downloads/cache fallback."""
from dataclasses import dataclass
from pathlib import Path
from fractions import Fraction
import csv
import gzip
import hashlib
import json
import re
from research.qd008.repair_history import validate_row, strict_json
from research.qd010.economic_inputs import INSTRUMENTS, HOUR, US, exact

OHLCV_MANIFEST_SHA='c1e6056058fd312d472e96fddfea15e78c778847de9942e5757cb39ad2ac9b91'
MARK_HANDOFF_SHA='30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce'
FUNDING_HANDOFF_SHA='176d0c987d23d4b29b7f901b7dfaa6eeffe56ad84bc57ee07f89a261dab65be5'
POLICY='ARCHIVE_PREFIX_REST_COMPLETE_ROWS_FROM_20251201_R1'
DATASET='gate-btc-eth-exact-ohlcv-v3-candidate'


class SourceError(ValueError):pass
class ActualHistoryOff(PermissionError):pass


def metadata(path,expected_sha):
    """Metadata identity check only; never follows payload paths."""
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise SourceError('MANIFEST_IDENTITY_MISMATCH')
    # Accepted handoffs include decimal runtime measurements. Preserve their
    # lexemes as text; the payload reader below still requires exact v3 strings.
    return strict_json(raw,evidence_numbers=True)


@dataclass(frozen=True)
class ObjectSpec:
    path: str
    sha256: str
    instrument_id: str
    format: str
    bytes: int
    source_id: str
    manifest_sha256: str


@dataclass(frozen=True)
class ReadPermit:
    """Operator-supplied scope, not data acceptance or proof of human authority.

    Real permits must come from a separately approved bounded run. This task uses
    only synthetic permits whose files are under research/.data/qd012/tmp/.
    """
    approval_id: str
    paths: tuple[str,...]
    manifest_sha256: str
    start_us: int
    end_us: int
    max_rows: int
    max_expanded_bytes: int
    kind: str='synthetic'

    def check(self,spec):
        if not self.approval_id or not self.start_us<self.end_us or self.max_rows<=0 or self.max_expanded_bytes<=0:
            raise ActualHistoryOff('EXPLICIT_BOUNDED_READ_APPROVAL_REQUIRED')
        if spec.manifest_sha256!=self.manifest_sha256 or spec.path not in self.paths:
            raise ActualHistoryOff('OBJECT_OUTSIDE_APPROVED_MANIFEST_SCOPE')
        path=Path(spec.path)
        if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in (path,*path.parents)):
            raise SourceError('ABSOLUTE_NON_SYMLINK_SOURCE_REQUIRED')
        if self.kind=='synthetic':
            root=(Path(__file__).resolve().parents[2]/'research/.data/qd012/tmp').resolve()
            if not path.is_relative_to(root):raise ActualHistoryOff('SYNTHETIC_PERMIT_CANNOT_READ_ACTUAL_HISTORY')
        elif self.kind!='separately_approved_actual_history':
            raise ActualHistoryOff('ACTUAL_HISTORY_EXECUTION_OFF')
        if spec.instrument_id not in INSTRUMENTS or path.stat().st_size!=spec.bytes:
            raise SourceError('FROZEN_OBJECT_METADATA_MISMATCH')
        return path


@dataclass(frozen=True)
class Ref:
    raw_sha256: str
    source_row: int
    source_id: str
    manifest_sha256: str


@dataclass(frozen=True)
class Hour:
    instrument_id: str
    open_us: int
    close_us: int
    available_us: int
    open: str
    high: str
    low: str
    close: str
    volume_contracts: str
    row_id: str
    source_segment: str
    refs: tuple[Ref,...]


@dataclass(frozen=True)
class MarkPoint:
    instrument_id: str
    source_us: int
    price: str
    lexemes: tuple[str,...]
    refs: tuple[Ref,...]


@dataclass(frozen=True)
class FundingRow:
    instrument_id: str
    source_us: int
    source_seconds_text: str
    rate: str
    ref: Ref

    @property
    def rate_available_us(self):return (self.source_us//HOUR+1)*HOUR


def seconds_us(value):
    if not re.fullmatch(r'(0|[1-9][0-9]*)(\.[0-9]{1,6})?',value):
        raise SourceError('SOURCE_SECONDS_PRECISION_OR_GRAMMAR')
    result=Fraction(value)*US
    if result.denominator!=1 or result<0 or result>2**63-1:raise SourceError('UTC_US_OUT_OF_RANGE')
    return int(result)


def _lines(spec,permit):
    # Check before opening, including when spec points at an actual-history path.
    if permit is None:raise ActualHistoryOff('ACTUAL_HISTORY_EXECUTION_OFF')
    path=permit.check(spec);count=size=0
    with path.open('rb') as raw:
        stream=gzip.GzipFile(fileobj=raw) if spec.format in ('mark_csv_gzip','funding_csv_gzip') else raw
        try:
            while True:
                line=stream.readline(1024*1024+1)
                if not line:break
                count+=1;size+=len(line)
                if len(line)>1024*1024 or count>permit.max_rows+1 or size>permit.max_expanded_bytes:
                    raise SourceError('READ_SCOPE_RESOURCE_LIMIT')
                yield count,line
        finally:
            if stream is not raw:stream.close()


def iter_hours(spec,permit=None):
    if spec.format!='exact_ohlcv_v3_jsonl':raise SourceError('ONLY_APPROVED_V3_NORMALIZED_ROWS')
    previous=None
    for physical,line in _lines(spec,permit):
        row=strict_json(line)
        if row['bar_open_us']>=permit.end_us:break
        if row['bar_close_us']<=permit.start_us:continue
        validate_row(row)
        if (row['instrument_id']!=spec.instrument_id or row['interval_seconds']!=3600
                or row['source_policy_id']!=POLICY or row['dataset_id']!=DATASET):
            raise SourceError('V3_ROW_IDENTITY_OR_INTERVAL_MISMATCH')
        if previous is not None and row['bar_open_us']!=previous+HOUR:raise SourceError('HOURLY_GAP_OR_DUPLICATE')
        previous=row['bar_open_us']
        yield Hour(spec.instrument_id,row['bar_open_us'],row['bar_close_us'],row['research_available_at_us'],
            row['open'],row['high'],row['low'],row['close'],row['volume_contracts'],row['row_id'],row['source_segment'],
            tuple(Ref(r['raw_sha256'],r['source_row'],spec.source_id,spec.manifest_sha256) for r in row['source_refs']))


def iter_marks(spec,permit=None):
    if spec.format!='mark_csv_gzip':raise SourceError('MARK_FORMAT_NOT_DECLARED')
    previous=None;refs=[];ts=None
    for physical,line in _lines(spec,permit):
        fields=tuple(next(csv.reader([line.decode('utf-8').rstrip('\r\n')],strict=True)))
        if len(fields)!=4:raise SourceError('MARK_FOUR_PHYSICAL_FIELDS_REQUIRED')
        at=seconds_us(fields[0])
        if any(not re.fullmatch(r'(0|[1-9][0-9]*)(\.[0-9]+)?',v) or exact(v)<=0 for v in fields[1:]):
            raise SourceError('INVALID_MARK_PRICE')
        ref=Ref(spec.sha256,physical,spec.source_id,spec.manifest_sha256)
        if ts is not None and at<ts:raise SourceError('DECREASING_MARK_SOURCE')
        if at==ts:
            if fields!=previous:raise SourceError('CONFLICTING_SAME_TIME_MARK_LEXEMES')
            refs.append(ref)
            if len(refs)>1024:raise SourceError('ALIAS_GROUP_RESOURCE_LIMIT')
            continue
        if previous is not None:
            yield MarkPoint(spec.instrument_id,ts,previous[2],previous,tuple(refs))
        if at>=permit.end_us:previous=None;break
        previous=fields;ts=at;refs=[ref]
    if previous is not None:yield MarkPoint(spec.instrument_id,ts,previous[2],previous,tuple(refs))


def iter_funding(spec,permit=None):
    if spec.format!='funding_csv_gzip':raise SourceError('FUNDING_RAW_FORMAT_NOT_DECLARED')
    data_row=0;previous=None
    for physical,line in _lines(spec,permit):
        fields=next(csv.reader([line.decode('utf-8-sig').rstrip('\r\n')],strict=True))
        if physical==1 and fields==['timestamp','funding_rate']:continue
        if len(fields)!=2:raise SourceError('FUNDING_TWO_RAW_FIELDS_REQUIRED')
        data_row+=1;source=seconds_us(fields[0]);exact(fields[1])
        if previous is not None and source<=previous:raise SourceError('FUNDING_SOURCE_ORDER_OR_DUPLICATE')
        previous=source
        if source>=permit.end_us:break
        if source<permit.start_us:continue
        yield FundingRow(spec.instrument_id,source,fields[0],fields[1],Ref(spec.sha256,data_row,spec.source_id,spec.manifest_sha256))


def hourly_specs(root,manifest):
    if manifest['dataset_id']!=DATASET or manifest['source_policy_id']!=POLICY or manifest['dataset_revision']!=3:
        raise SourceError('NO_V2_OR_POLICY_FALLBACK')
    result=[];root=Path(root).absolute()
    for entry in manifest['candles']:
        if entry['interval_seconds']!=3600:continue
        path=root/entry['path']
        if not path.is_relative_to(root) or '..' in Path(entry['path']).parts:raise SourceError('MANIFEST_PATH_ESCAPE')
        result.append(ObjectSpec(str(path),entry['sha256'],entry['instrument_id'],'exact_ohlcv_v3_jsonl',entry['bytes'],entry['path'],OHLCV_MANIFEST_SHA))
    if {s.instrument_id for s in result}!=set(INSTRUMENTS) or len(result)!=2:raise SourceError('BOTH_HOURLY_FILES_REQUIRED')
    return tuple(result)


def monthly_specs(handoff,kind):
    """Descriptor mapping only. Does not stat, glob, hash or open raw objects."""
    if kind not in ('mark','funding'):raise SourceError('UNSUPPORTED_SOURCE_KIND')
    key='objects' if kind=='mark' else 'raw_sources'
    manifest=MARK_HANDOFF_SHA if kind=='mark' else FUNDING_HANDOFF_SHA
    result=[]
    for entry in handoff[key]:
        inst='gate:usdt:'+entry['symbol']
        if inst not in INSTRUMENTS:raise SourceError('UNSUPPORTED_SOURCE_INSTRUMENT')
        result.append(ObjectSpec(entry['path'],entry['sha256'],inst,kind+'_csv_gzip',entry['bytes'],
                                 entry.get('source_id',entry['path']),manifest))
    return tuple(result)
