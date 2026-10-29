"""Short account-copy timing, no old-history financial replay or training."""
import argparse
import cProfile
import json
from pathlib import Path
import pstats
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--output',required=True);p.add_argument('--ticks',type=int,default=8)
    p.add_argument('--optimized',action='store_true');p.add_argument('--continue-copy',action='store_true')
    p.add_argument('--no-profiler',action='store_true');a=p.parse_args();out=Path(a.output);out.mkdir(exist_ok=False)
    from research.qd019.sqlite_host import prepare_sqlite_host
    prepare_sqlite_host()
    from research.qd019.migration import read,install_budgets,open_ledger,activate
    from research.qd012.actual_snapshot_entry import network_off
    from research.qd013.runner import Replay
    data=Path(a.data);m=read(a.manifest);profile=cProfile.Profile()
    with network_off():
        budgets=None
        if a.optimized:
            from .accounting import install as free_accounting
            budgets=free_accounting(data,[m['old_data_root'],str(data.resolve())])
        else:install_budgets(data,m)
        ledger=open_ledger(data,m,lambda:None)
        try:
            if not a.continue_copy:activate(ledger,m)
            if a.optimized:
                from .fast import install
                install(ledger)
            replay=Replay(ledger);times=[t for t in ledger.config['_plan_index'].times if t>ledger.head['cutoff']['at_us']][:a.ticks]
            baseline=ledger.budget.written;wall=time.monotonic();cpu=time.process_time();states=[]
            if not a.no_profiler:profile.enable()
            for at in times:
                tw=time.monotonic();replay.advance_chunk(at);v=replay.view(at)
                states.append(dict(head=ledger.head,view_sha256=v['view_sha256'],
                                   economic_state_sha256=v['economic_state_sha256'],seconds=time.monotonic()-tw))
                print('profile tick',ledger.head['committed_seq'],flush=True)
            if not a.no_profiler:profile.disable()
            result=dict(mode='optimized' if a.optimized else 'baseline',wall=time.monotonic()-wall,
                        cpu=time.process_time()-cpu,written=ledger.budget.written-baseline,ticks=states,
                        index=dict(visits=ledger.index.visits,writes=ledger.index.writes,immutable=ledger.index.immutable_visits,
                                   working=ledger.index.working_visits,cache_bytes=ledger.index.size))
            (out/'result.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
            if not a.no_profiler:
                profile.dump_stats(str(out/'profile.pstats'))
                with (out/'profile.txt').open('x') as f:pstats.Stats(profile,stream=f).strip_dirs().sort_stats('cumtime').print_stats(45)
            print(json.dumps({k:v for k,v in result.items() if k!='ticks'}),flush=True)
        finally:
            ledger.close()
            if budgets:
                for budget in reversed(budgets):budget.close()


if __name__=='__main__':main()
