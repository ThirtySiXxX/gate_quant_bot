"""One pure-storage comparison on pinned existing synthetic QD014 journals.

No ledger import/replay, history input or model. The reference prototype removes
only generated entries already present byte-for-byte in the same file's registry
projection. It is measured, not a proposed persistent dependency on SQLite.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import zlib


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    expected=root/'research/.data/qd014/engineering-1567562231992666/compact/store'
    if args.source.resolve()!=expected.resolve():raise ValueError('PINNED_SYNTHETIC_SOURCE_ONLY')
    args.output.mkdir(parents=True,exist_ok=False)
    variants={k:dict(bytes=0,encode_seconds=0.0,write_seconds=0.0,read_decode_seconds=0.0,files=0) for k in ('plain','zlib1','zlib6','refs_zlib1')}
    for k in variants:(args.output/k).mkdir()
    sources=[];source_read_seconds=0.0;source_hash=hashlib.sha256();started=time.perf_counter()
    for index in range(1,17):
        p=args.source/f'journal-{index:08}.json';begin=time.perf_counter();raw=p.read_bytes();source_read_seconds+=time.perf_counter()-begin
        h=hashlib.sha256(raw).hexdigest();sources.append(dict(path=str(p),bytes=len(raw),sha256=h));source_hash.update(bytes.fromhex(h))
        payload=json.loads(raw)
        registry={r['item']['entry_sha256']:r['item'] for f in payload['frames'] for r in f['projection'] if r['component']=='registry'}
        if any(registry.get(g['entry_sha256'])!=g for g in payload['generated']):raise ValueError('REFERENCE_RECONSTRUCTION_NOT_EXACT')
        prototype=dict(payload,generated=[dict(registry_ref=g['entry_sha256']) for g in payload['generated']])
        restored=dict(prototype,generated=[registry[g['registry_ref']] for g in prototype['generated']])
        if canonical(restored)!=raw:raise ValueError('REFERENCE_BYTES_NOT_EXACT')
        for name,stats in variants.items():
            before=time.perf_counter()
            encoded=raw if name=='plain' else zlib.compress(canonical(prototype) if name=='refs_zlib1' else raw,6 if name=='zlib6' else 1)
            stats['encode_seconds']+=time.perf_counter()-before
            path=args.output/name/p.name;before=time.perf_counter()
            with path.open('xb') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
            stats['write_seconds']+=time.perf_counter()-before;stats['bytes']+=len(encoded);stats['files']+=1
            before=time.perf_counter();read=path.read_bytes();decoded=read if name=='plain' else zlib.decompress(read)
            if name=='refs_zlib1':
                v=json.loads(decoded);by_ref={r['item']['entry_sha256']:r['item'] for f in v['frames'] for r in f['projection'] if r['component']=='registry'}
                decoded=canonical(dict(v,generated=[by_ref[g['registry_ref']] for g in v['generated']]))
            if decoded!=raw:raise ValueError('STORAGE_NOT_LOSSLESS')
            stats['read_decode_seconds']+=time.perf_counter()-before
        if time.perf_counter()-started>30:raise ValueError('STORAGE_MEASUREMENT_OBSERVATION_STOP')
    for name in variants:
        fd=os.open(args.output/name,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    result=dict(schema='qd015.synthetic-storage-measurement.v1',status='EXACT_BYTE_RECONSTRUCTION_PASS',
        source_identity_sha256=source_hash.hexdigest(),sources=sources,variants=variants,source_read_seconds=source_read_seconds,
        wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time(),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),
        repetitions=1,note='serial single storage pass, source OS cache uncontrolled; fsync per file, same original bytes; codec framing not yet included; no financial replay',training_authorized=False)
    with (args.output/'result.json').open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sources'},sort_keys=True))


if __name__=='__main__':main()
