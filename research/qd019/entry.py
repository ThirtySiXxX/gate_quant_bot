"""Local migration admission and one-shot continuation; default OFF."""
import argparse
import json
from pathlib import Path
import time
from .migration import (SCHEMA, STORE, RECORD, read, sha, require, verify_inventory,
                        verify_code, admit_runtime, verify_chain, install_budgets,
                        open_ledger, activate)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / 'research/.data/qd019-import/migration.json'


def check(manifest_path):
    path = Path(manifest_path).resolve(); m = read(path); data = path.parent / 'qd015'
    release = read(ROOT/'research/qd019/transfer.json')
    require(release['manifest_sha256'] == sha(path), 'TRANSFER_MANIFEST_HASH_MISMATCH')
    require(m['schema'] == SCHEMA, 'MIGRATION_MANIFEST_VERSION')
    verify_code(ROOT, m['code_sha256'])
    require(not (data / RECORD).exists() and not (data / STORE / RECORD).exists(),
            'MIGRATION_ALREADY_CONSUMED_NO_RETRY')
    require(not (data / 'migration-run-1/launch.json').exists(), 'MIGRATION_ALREADY_ATTEMPTED_NO_RETRY')
    require(len(m['numeric_seals']) >= 16, 'NUMERICAL_REFERENCE_SEALS_REQUIRED')
    actual = admit_runtime(m['source_runtime'])
    print('Checking local data hashes...', flush=True)
    size = verify_inventory(data, m['inventory'])
    require(read(data / STORE / 'HEAD') == m['frozen']['head'], 'FROZEN_HEAD_MISMATCH')
    return m, data, dict(status='READY_FOR_LOCAL_RESUME', data_bytes=size,
                          runtime=actual, checkpoint=m['frozen']['head'], training_authorized=False)


def run(manifest_path=DEFAULT_MANIFEST, *, resume=False, validate_only=False):
    if not resume and not validate_only:
        return dict(status='OFF')
    started_wall = time.monotonic(); started_cpu = time.process_time()
    m, data, preflight = check(manifest_path)
    from research.qd012.actual_snapshot_entry import ObservationBudget, network_off, durable_new, encoded
    from research.qd009 import streaming_ledger as sl
    from research.qd013.market import MarketCache
    from research.qd013.runner import Replay
    from research.qd013.exports import export_all, write_bundle
    before = m['prior_observed_upper_bounds']
    limits = dict(m['outer_limits'])
    limits['wall_seconds'] -= before['wall_seconds']
    limits['cpu_seconds'] -= before['cpu_seconds']
    require(min(limits['wall_seconds'], limits['cpu_seconds']) > 0, 'CUMULATIVE_BUDGET_EXHAUSTED')
    budget = ObservationBudget(limits); budget.wall0 = started_wall; budget.cpu0 = started_cpu
    out = data / 'migration-run-1'; out.mkdir(exist_ok=False)
    durable_new(out / 'launch.json', dict(status='CONSUMED_NO_AUTOMATIC_RETRY',
                manifest_sha256=sha(manifest_path), authorization_ref=m['authorization_ref'],
                mode='ENGINEERING_COPY_VALIDATION' if validate_only else 'CONTINUE_ORIGINAL_ACCOUNT',
                preflight=preflight, prior_observed_upper_bounds=before, remaining_limits=limits), 1048576)
    ledger = cache = None; allocation = None

    def write(name, value):
        size = len(encoded(value))
        if allocation:
            allocation.issue(out / name, size, size)
        durable_new(out / name, value, 1048576)

    def observations():
        current = budget.observed()
        return dict(current=current, cumulative_upper_bounds=dict(
                    wall_seconds=before['wall_seconds']+current['wall_seconds'],
                    cpu_seconds=before['cpu_seconds']+current['cpu_seconds']),
                    original_input_observations=m['original_input_observations'],
                    raw_history_reads_this_invocation=0, prior_rss=m['source_rss_evidence'])

    try:
        with network_off():
            print('Verifying published journal chain...', flush=True)
            budget.check(); verify_chain(data / STORE, m['frozen']['head']); budget.check()
            allocation, child = install_budgets(data, m)
            cache = MarketCache(data / m['cache_relative_path'], m['cache_identity'])
            require(cache.meta['content_sha256'] == m['cache_content_sha256'], 'CACHE_CONTENT_MISMATCH')
            print('Opening relocated account and verifying derived inputs...', flush=True)
            ledger = open_ledger(data, m, budget.check)
            record = activate(ledger, m); budget.check(); replay = Replay(ledger)
            write('activated.json', dict(record=record, head=ledger.head, spent=ledger.spent))
            progress_at = time.monotonic(); end = ledger.config['_plan_index'].times[-1]
            for at in ledger.config['_plan_index'].times:
                if at <= ledger.head['cutoff']['at_us']:
                    continue
                budget.check(); replay.advance_chunk(at); budget.check()
                if len(ledger.seals_passed) == len(m['numeric_seals']) and not (out/'runtime-validation.json').exists():
                    write('runtime-validation.json', dict(status='EXACT_REFERENCE_SEALS_PASSED',
                          ticks=len(ledger.seals_passed), runtime=ledger.admitted_runtime, head=ledger.head))
                    print('New machine numerical validation passed.', flush=True)
                    if validate_only:
                        result = dict(status='RELOCATED_COPY_VALIDATED_NOT_FULL_REPLAY', head=ledger.head,
                                      seals_passed=len(ledger.seals_passed), observed=observations(),
                                      spent=ledger.spent, training_authorized=False)
                        write('result.json', result)
                        return result
                require(allocation.total + allocation.book.stat().st_size <= allocation.limit, 'TOTAL_OUTPUT_LIMIT')
                if time.monotonic() - progress_at >= 30:
                    progress_at = time.monotonic()
                    status = dict(committed_seq=ledger.head['committed_seq'], cutoff=ledger.head['cutoff'],
                                  observed=observations(), spent=ledger.spent)
                    sl._atomic(out / 'progress.json', None, _raw=encoded(status))
                    print(json.dumps(status, sort_keys=True), flush=True)
            require(len(ledger.seals_passed) == len(m['numeric_seals']), 'NUMERICAL_SEALS_INCOMPLETE')
            records = export_all(replay, end); budget.check()
            exported = write_bundle(out/'export-P0-ALLOW_ALL', records, dict(
                       cache_key=cache.key, ledger_head=ledger.head,
                       source_manifest=m['original_manifest_sha256'], migration_manifest=sha(manifest_path)),
                       write_budget=allocation.issue)
            statuses = {}
            for row in records:
                name = row['qr014_episode_fields']['label_status']
                statuses[name] = statuses.get(name, 0) + 1
            result = dict(status='FULL_CONTINUOUS_P0_COMPLETED', head=ledger.head,
                          export=exported, label_status_counts=statuses, observed=observations(),
                          spent=ledger.spent, scope=m['scope'], training_authorized=False)
            write('result.json', result)
            return result
    except BaseException as error:
        result = dict(status='STOPPED_NO_AUTOMATIC_RETRY', reason=type(error).__name__+':'+str(error),
                      head=ledger.current_head() if ledger else None, spent=ledger.spent if ledger else None,
                      observed=observations(), training_authorized=False)
        try:
            write('failure.json', result)
        except BaseException:
            # The outer allocation leaves 64 KiB for a final failure receipt.
            try:
                if not (out/'failure.json').exists():
                    durable_new(out/'failure.json', result, 65536)
            except BaseException:
                pass
        raise
    finally:
        if ledger:
            ledger.close()
        if cache:
            cache.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', default=str(DEFAULT_MANIFEST))
    mode = p.add_mutually_exclusive_group(); mode.add_argument('--check', action='store_true')
    mode.add_argument('--resume', action='store_true'); mode.add_argument('--validate-only', action='store_true')
    a = p.parse_args()
    try:
        result = check(a.manifest)[2] if a.check else run(a.manifest, resume=a.resume, validate_only=a.validate_only)
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except BaseException as e:
        print(json.dumps(dict(status='STOPPED_NO_AUTOMATIC_RETRY', reason=type(e).__name__+':'+str(e))), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
