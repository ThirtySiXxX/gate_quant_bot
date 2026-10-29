"""Opt-in new-plan runner; never migrate a QD013 state or resource ledger."""
from pathlib import Path
from research.qd009 import streaming_ledger as sl
from research.qd011.ports import ControlledPort
from research.qd013.runner import create as original_create, Replay as OriginalReplay
from .structure import SCHEDULE


class Replay(OriginalReplay):
    @classmethod
    def reopen(cls, store):
        request = sl.load_json((Path(store)/'GENESIS').read_bytes())
        wire = request['config']['schedule']
        sl.need(type(wire) is dict and wire.get('schema') == SCHEDULE, 'UNSUPPORTED_VERSION')
        for definition in request['config']['adapters']:
            sl.register_port(definition, ControlledPort())
        return cls(sl.Ledger(store))


def create(path, cache, *, initial_us, economic_end_us, tail_end_us,
           scenario_id='P0', policy_id='ALLOW_ALL', write_budget=None, ledger_limits=None):
    replay = original_create(path, cache, initial_us=initial_us, economic_end_us=economic_end_us,
        tail_end_us=tail_end_us, scenario_id=scenario_id, policy_id=policy_id,
        write_budget=write_budget, static_plan=True, ledger_limits=ledger_limits)
    return Replay(replay.ledger)
