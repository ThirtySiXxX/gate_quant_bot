"""Market-producing identities exclude journal/driver/execution storage code.

The existing market-cache envelope is unchanged. This is an explicit new code
identity scope; an old broad-key cache is never silently relabeled or rebuilt.
"""
import hashlib
import inspect
from pathlib import Path
import sys

FILES=('research/qd008/repair_history.py','research/qd010/economic_inputs.py',
    'research/qd010/joint_native_bridge.py','research/qd011/codec.py',
    'research/qd012/sources.py','research/qd012/queries.py','research/qd012/prepare.py',
    'research/qd012/native.py','research/qd013/market.py','research/qd013/inputs.py',
    'src/strategy_signals.py','src/trend.py','src/carry.py','src/vol.py',
    'src/indicators.py','src/execution_timing.py','src/config.py','src/portfolio.py')


def producer_identity():
    from research.qd009 import streaming_ledger as sl
    from src.data_fetcher import INTERVAL_SECONDS
    import numpy as np
    import pandas as pd
    root=Path(__file__).resolve().parents[2]
    primitives={k:hashlib.sha256(inspect.getsource(getattr(sl,k)).encode()).hexdigest()
                for k in ('strict_json','canonical_bytes','digest','load_json','need')}
    return dict(schema='qd015.market-producer-code.v1',
        files={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in FILES},primitives=primitives,
        constants=dict(interval_seconds=INTERVAL_SECONDS),
        runtime=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__))
