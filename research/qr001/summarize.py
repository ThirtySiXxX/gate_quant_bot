"""Recompute UTC-day uncertainty from immutable predictions, without retraining."""
import argparse
from pathlib import Path
import json
import subprocess

import pandas as pd

from .validation import block_interval, paired_daily_losses, sha256, write_json

HERE = Path(__file__).resolve().parent


def run(run_root, output):
    source, output = Path(run_root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('use a fresh summary output directory')
    protocol = json.loads((HERE / 'protocol.json').read_text())
    manifest = json.loads((source / 'run_manifest.json').read_text())
    if manifest['protocol_sha256'] != sha256(HERE / 'protocol.json'):
        raise ValueError('protocol changed since fitting; do not re-label the experiment')
    summary = json.loads((source / 'summary.json').read_text())
    daily = paired_daily_losses(pd.read_csv(source / 'paired_losses.csv'))
    original_intervals = summary['intervals']
    summary['intervals'] = [block_interval(daily, b, protocol['bootstrap_repetitions'], protocol['seed'])
                            for b in protocol['bootstrap_block_days']]
    summary['predictive_gate_passed'] = bool(summary['intervals'][0]['upper_95'] < 0
                                             and summary['improved_folds'] >= 2)
    summary['uncertainty_amendment'] = dict(
        reason='UTC days crossing fold boundaries were counted twice; aggregate each UTC day once',
        applied_after_results=True, training_predictions_thresholds_unchanged=True,
        source_run_revision=manifest['revision'],
        analysis_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE).decode().strip(),
        analysis_source_sha256={p.name: sha256(p) for p in [HERE / 'validation.py', HERE / 'summarize.py']},
        input_paired_losses_sha256=sha256(source / 'paired_losses.csv'),
        original_summary_sha256=sha256(source / 'summary.json'),
        original_intervals_superseded=original_intervals)
    summary['recommendation'] = 'No model promotion: primary replay has zero entries; new prospective evidence required'
    output.mkdir(parents=True)
    daily.to_csv(output / 'daily_paired_losses.csv', index=False)
    write_json(output / 'summary.json', summary)
    print(json.dumps(summary['intervals']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.run_root, args.output)
