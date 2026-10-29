"""One cold paired synthetic native-preparation observation, never a replay.

Both variants return the same eight full signals, covariance matrices and native
observations. Version-specific context/provenance encodings are not the common
product; the unchanged old function still pays its intrinsic context cost. No
warm-cache ratio, trade, model, MARK or actual-history access is involved.
"""
import time

START_WALL = time.perf_counter()
START_CPU = time.process_time()

import argparse
from contextlib import ExitStack
from dataclasses import asdict, fields
import hashlib
import json
from pathlib import Path
import resource
import socket
import sys
from unittest.mock import patch

BASELINE_COMMIT = 'c761d90d65bb33ef4256d26cba1a48163606e41f'
BASELINE_NATIVE_SHA = '02337f8929fe2c0468ef065572f140b794e278062d86b3a22e876c37a3ec9f10'


def deny(*args, **kwargs):
    raise RuntimeError('SYNTHETIC_BENCHMARK_NETWORK_FORBIDDEN')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=('baseline', 'candidate'))
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be exclusive; never overwrite prior evidence')
    if (args.variant == 'candidate') != (args.expected is not None):
        parser.error('only candidate requires --expected baseline result')
    root = Path(__file__).resolve().parents[2]
    evidence_root = (root/'research/.data/qd013').resolve()
    if not args.fixture.resolve().is_relative_to(evidence_root):
        parser.error('fixture must be the explicitly selected local synthetic evidence')
    socket.create_connection = deny
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    # Identical import set in both fresh workers, including candidate modules.
    from research.qd009 import streaming_ledger as sl
    from research.qd010.economic_inputs import INSTRUMENTS, SYMBOLS, HOUR
    from research.qd011.codec import pack
    from research.qd011.driver import NativeObservation
    from research.qd012 import native
    from research.qd012.sources import Hour, Ref, FundingRow
    from research.qd013.market import NativeSeries
    from research.qd013.compact import signal
    from src import strategy_signals, portfolio, vol

    source_paths = ('research/qd012/native.py', 'research/qd013/market.py',
                    'research/qd013/compact.py', 'research/qd013/benchmark.py',
                    'research/qd011/codec.py', 'src/strategy_signals.py',
                    'src/portfolio.py', 'src/vol.py', 'src/trend.py',
                    'src/carry.py', 'src/execution_timing.py', 'src/config.py')
    pins = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in source_paths}
    if pins['research/qd012/native.py'] != BASELINE_NATIVE_SHA:
        raise RuntimeError('UNCHANGED_BASELINE_NATIVE_IDENTITY_REQUIRED')
    before = time.perf_counter()
    raw = args.fixture.read_bytes()
    fixture = json.loads(raw)
    if fixture['schema'] != 'qd013.synthetic-performance.v1':
        raise RuntimeError('SYNTHETIC_FIXTURE_SCHEMA_REQUIRED')
    hours, funding = {}, {}
    for i in INSTRUMENTS:
        rows = []
        for v in fixture['hours'][i]:
            if v['source_segment'] != 'SYNTHETIC' or any(r['source_id'] != 'qd013-synthetic' for r in v['refs']):
                raise RuntimeError('SYNTHETIC_HOURS_ONLY')
            rows.append(Hour(**dict(v, refs=tuple(Ref(**r) for r in v['refs']))))
        hours[i] = tuple(rows)
        funding[i] = tuple(FundingRow(**dict(v, ref=Ref(**v['ref']))) for v in fixture['funding'][i])
        if len(rows) != 1600 or len(funding[i]) != 201 or any(f.ref.source_id != 'synthetic-funding' for f in funding[i]):
            raise RuntimeError('FIXED_SYNTHETIC_INPUT_COUNTS_REQUIRED')
    decisions = fixture['decisions']
    initial = 1672531200000000 + 1440*HOUR
    if decisions != list(range(initial, initial+8*HOUR, HOUR)):
        raise RuntimeError('FIXED_EIGHT_HOURLY_DECISIONS_REQUIRED')
    load_seconds = time.perf_counter()-before
    counts = dict(native_prepare_calls=0, covariance_build_calls=0,
                  covariance_series_calls=0, full_cache_encodes=0)

    def counted(name, function):
        def call(*a, **kw):
            counts[name] += 1
            return function(*a, **kw)
        return call

    observation_names = [f.name for f in fields(NativeObservation) if f.name != 'source_ref']
    products = []
    prep_wall, prep_cpu = time.perf_counter(), time.process_time()
    with ExitStack() as stack:
        for owner, name, counter in ((strategy_signals, 'prepare_features', 'native_prepare_calls'),
                (portfolio, 'build_covariance', 'covariance_build_calls'),
                (vol, 'ewma_covariance_series', 'covariance_series_calls'),
                (native, 'encode_cache', 'full_cache_encodes')):
            stack.enter_context(patch.object(owner, name, counted(counter, getattr(owner, name))))
        series = NativeSeries(hours, funding) if args.variant == 'candidate' else None
        for at in decisions:
            if args.variant == 'baseline':
                bundle = native.prepare_native(hours, funding, at)
                if bundle.status != 'AVAILABLE':
                    raise RuntimeError('BASELINE_UNAVAILABLE:'+str(bundle.reasons))
                signals = {s: asdict(bundle.signals[s]) for s in SYMBOLS}
                covariance = bundle.covariance.loc[list(SYMBOLS), list(SYMBOLS)].to_numpy().tolist()
                observations = [{k: asdict(o)[k] for k in observation_names} for o in bundle.observations]
                del bundle  # No artificial retention of all old warmup contexts.
            else:
                snapshots = series.snapshot(at)
                signals = {s: asdict(signal(s, dict(f, available=at, at=at-HOUR))) for s, f in zip(SYMBOLS, snapshots)}
                f = snapshots[0]
                covariance = [[float(f['cov_btc_btc']), float(f['cov_cross'])],
                              [float(f['cov_cross']), float(f['cov_eth_eth'])]]
                observations = [{k: f[k] for k in observation_names} for f in snapshots]
            products.append(pack(dict(at_us=at, signals=signals, covariance=covariance,
                observations=observations, source_row_ids={i: hours[i][(at-hours[i][0].open_us)//HOUR-1].row_id for i in INSTRUMENTS})))
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024)
            if time.perf_counter()-START_WALL > 55 or time.process_time()-START_CPU > 40 or rss > 256*1024**2:
                raise RuntimeError('PER_WORKER_OBSERVATION_BUDGET_EXCEEDED')
    prep_seconds, prep_cpu_seconds = time.perf_counter()-prep_wall, time.process_time()-prep_cpu
    product_raw = sl.canonical_bytes(products)
    product_sha = hashlib.sha256(product_raw).hexdigest()
    equivalent = None
    if args.expected:
        expected = json.loads(args.expected.read_bytes())
        equivalent = (expected['fixture_sha256'] == hashlib.sha256(raw).hexdigest()
                      and expected['product_sha256'] == product_sha and expected['products'] == products)
    result = dict(schema='qd013.paired-native-benchmark.v1', variant=args.variant,
        baseline_commit=BASELINE_COMMIT, code_sha256=pins, fixture_sha256=hashlib.sha256(raw).hexdigest(),
        status='PASS' if equivalent is not False else 'OUTPUT_MISMATCH',
        equivalent_to_baseline=equivalent, product_sha256=product_sha, products=products,
        product_bytes=len(product_raw), fixture_bytes=len(raw), load_seconds=load_seconds,
        preparation_wall_seconds=prep_seconds, preparation_cpu_seconds=prep_cpu_seconds,
        worker_wall_seconds_through_comparison=time.perf_counter()-START_WALL,
        worker_cpu_seconds_through_comparison=time.process_time()-START_CPU,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform == 'darwin' else 1024),
        operations=dict(counts, fixture_reads=1, fixture_rows=3602, decisions=8,
                        raw_history_reads=0, gzip_decompressions=0, ledger_scans=0,
                        persistent_cache_builds=0, persistent_cache_hits=0),
        scope='cold native preparation only, same 8 full signals/covariance/observation products; no persisted cache or replay',
        provenance_note='v2/v3 source_ref formats excluded; exact selected source row IDs and common fixture hash included',
        warm_comparison='NOT_RUN_NO_COMPARABLE_ORIGINAL_REUSABLE_CACHE',
        repetitions=1, training_authorized=False)
    with args.output.open('x') as output:
        json.dump(result, output, sort_keys=True, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps({k: result[k] for k in ('variant', 'status', 'product_sha256', 'preparation_wall_seconds', 'peak_rss_bytes', 'operations')}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
