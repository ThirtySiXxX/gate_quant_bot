"""Bounded, lossless journal framing. No ledger/account/market dependency.

Physical format: magic + big-endian header length + canonical JSON header + one
zlib stream. Both compressed and original bytes have independent SHA256 checks.
"""
import hashlib
import json
import struct
import zlib

MAGIC = b'QFJ015\x00\x01'
SCHEMA = 'qd015.journal-storage.v1'
CODEC = 'qd015.zlib-framed.v1'
HARD_MAX = 64*1024**2
HEADER_MAX = 1024


class JournalError(ValueError):pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def validate(spec):
    if type(spec) is not dict or set(spec)!={'schema','codec','level','max_raw_bytes','max_stored_bytes','implementation_sha256'}:
        raise JournalError('JOURNAL_PROFILE_FIELDS')
    if spec['schema']!=SCHEMA or spec['codec']!=CODEC or type(spec['level']) is not int or spec['level']!=1:
        raise JournalError('JOURNAL_UNSUPPORTED_VERSION')
    if any(type(spec[k]) is not int or not 1<=spec[k]<=HARD_MAX for k in ('max_raw_bytes','max_stored_bytes')):
        raise JournalError('JOURNAL_SIZE_LIMIT')
    with open(__file__,'rb') as source:identity=hashlib.sha256(source.read()).hexdigest()
    if spec['implementation_sha256']!=identity:
        raise JournalError('JOURNAL_IMPLEMENTATION_IDENTITY')
    return spec


def encode(raw, spec):
    if type(raw) is not bytes or len(raw)>spec['max_raw_bytes']:
        raise JournalError('JOURNAL_RAW_LIMIT')
    compressed=zlib.compress(raw,1)
    header=canonical(dict(codec=CODEC,raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),
        compressed_bytes=len(compressed),compressed_sha256=hashlib.sha256(compressed).hexdigest()))
    result=MAGIC+struct.pack('>I',len(header))+header+compressed
    if len(header)>HEADER_MAX or len(result)>spec['max_stored_bytes']:
        raise JournalError('JOURNAL_STORED_LIMIT')
    return result


def decode(encoded, spec):
    if len(encoded)>spec['max_stored_bytes'] or encoded[:len(MAGIC)]!=MAGIC or len(encoded)<len(MAGIC)+4:
        raise JournalError('JOURNAL_HEADER')
    size=struct.unpack('>I',encoded[len(MAGIC):len(MAGIC)+4])[0]
    if not 0<size<=HEADER_MAX or len(encoded)<len(MAGIC)+4+size:
        raise JournalError('JOURNAL_HEADER_SIZE')
    try:
        def reject_constant(value):raise JournalError('JOURNAL_HEADER_CONSTANT')
        header=json.loads(encoded[len(MAGIC)+4:len(MAGIC)+4+size],parse_constant=reject_constant)
    except (ValueError,UnicodeError) as e:raise JournalError('JOURNAL_HEADER_JSON') from e
    expected={'codec','raw_bytes','raw_sha256','compressed_bytes','compressed_sha256'}
    if type(header) is not dict or set(header)!=expected or header['codec']!=CODEC or canonical(header)!=encoded[len(MAGIC)+4:len(MAGIC)+4+size]:
        raise JournalError('JOURNAL_HEADER_CANONICAL')
    if type(header['raw_bytes']) is not int or not 0<=header['raw_bytes']<=spec['max_raw_bytes']:
        raise JournalError('JOURNAL_RAW_LIMIT')
    body=encoded[len(MAGIC)+4+size:]
    if type(header['compressed_bytes']) is not int or header['compressed_bytes']!=len(body) or hashlib.sha256(body).hexdigest()!=header['compressed_sha256']:
        raise JournalError('JOURNAL_COMPRESSED_INTEGRITY')
    try:
        decoder=zlib.decompressobj();raw=decoder.decompress(body,header['raw_bytes']+1)
    except zlib.error as e:raise JournalError('JOURNAL_DECOMPRESSION') from e
    if len(raw)!=header['raw_bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or hashlib.sha256(raw).hexdigest()!=header['raw_sha256']:
        raise JournalError('JOURNAL_RAW_INTEGRITY')
    return raw
