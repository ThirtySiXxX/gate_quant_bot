"""Explicit journal format for a new QD014 continuous account only."""
import hashlib
from pathlib import Path
from research.qd009 import streaming_ledger as sl
from research.qd014.runner import create as original_create, Replay as OriginalReplay
from . import journal


def profile():
    return dict(schema=journal.SCHEMA,codec=journal.CODEC,level=1,
        max_raw_bytes=journal.HARD_MAX,max_stored_bytes=journal.HARD_MAX,
        implementation_sha256=hashlib.sha256(Path(journal.__file__).read_bytes()).hexdigest())


class Replay(OriginalReplay):
    @classmethod
    def reopen(cls,store):
        request=sl.load_json((Path(store)/'GENESIS').read_bytes())
        spec=request['config'].get('journal_storage')
        sl.need(spec is not None and spec.get('schema')==journal.SCHEMA,'UNSUPPORTED_VERSION')
        old=super().reopen(store)
        return cls(old.ledger)


def create(path,cache,*,journal_profile=None,**kwargs):
    with sl.journal_creation(journal_profile or profile()):
        old=original_create(path,cache,**kwargs)
    return Replay(old.ledger)
