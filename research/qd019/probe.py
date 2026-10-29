"""Numerical reference on a frozen *copy*, with original registered ports."""
import argparse
import json
from pathlib import Path
import time
from .migration import read, install_budgets, open_ledger, activate, verify_chain


def main():
    p = argparse.ArgumentParser(); p.add_argument('--data', required=True)
    p.add_argument('--manifest', required=True); p.add_argument('--out', required=True)
    p.add_argument('--ticks', type=int, default=16); a = p.parse_args()
    m = read(a.manifest); data = Path(a.data)
    from research.qd012.actual_snapshot_entry import ObservationBudget, network_off, durable_new
    from research.qd013.runner import Replay
    budget = ObservationBudget(dict(wall_seconds=300, cpu_seconds=240, rss_bytes=1073741824))
    started = time.monotonic()
    with network_off():
        verify_chain(data / 'full-p0-actual-1/P0-ALLOW_ALL/store', m['frozen']['head'])
        install_budgets(data, m)
        ledger = open_ledger(data, m, budget.check, verify_seals=False, reference=True)
        try:
            activate(ledger, m); replay = Replay(ledger); seals = []
            remaining = [t for t in ledger.config['_plan_index'].times if t > ledger.head['cutoff']['at_us']]
            for at in remaining[:a.ticks]:
                budget.check(); replay.advance_chunk(at); budget.check()
                view = replay.view(at)
                seals.append(dict(cutoff=ledger.head['cutoff'],
                                  economic_state_sha256=view['economic_state_sha256'],
                                  view_sha256=view['view_sha256']))
                print('reference tick', ledger.head['committed_seq'], flush=True)
            durable_new(Path(a.out), dict(status='REFERENCE_ONLY_NOT_A_NEW_REPLAY', numeric_seals=seals,
                        observed=budget.observed(), elapsed=time.monotonic()-started, head=ledger.head), 1048576)
        finally:
            ledger.close()


if __name__ == '__main__':
    main()
