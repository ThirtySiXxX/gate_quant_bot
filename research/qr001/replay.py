"""Compare research bundles through the existing QD portfolio replay, offline."""
import argparse
from dataclasses import replace
from pathlib import Path
import hashlib
import json

from src.backtest import SymbolBacktestInputs, run_portfolio_backtest
from src.backtest_reporting import position_summary
from src.config import CostConfig, RiskConfig, SystematicConfig
from .validation import load_manifest_data, sha256, write_json

HERE = Path(__file__).resolve().parent


def make_inputs(frames, fixture):
    contract = fixture['contract']
    return SymbolBacktestInputs(symbol='ETH_USDT', df_short=frames['replay/1h.csv'],
        df_main=frames['replay/4h.csv'], df_cov=frames['replay/4h.csv'], df_regime=frames['replay/1d.csv'],
        funding_rate=float(contract['funding_rate']), funding_interval_sec=float(contract['funding_interval']),
        quanto_multiplier=float(contract['quanto_multiplier']), taker_fee_rate=fixture['cost_config']['taker_fee_rate'],
        order_size_min=int(contract['order_size_min']), funding_history=frames['replay/funding.csv'],
        test_start_ts=fixture['start_ts'], leverage_min=float(contract['leverage_min']),
        leverage_max=float(contract['leverage_max']), order_size_max=int(contract['order_size_max']),
        market_order_size_max=float(contract['market_order_size_max']), risk_limit_tiers=fixture['risk_limit_tiers'])


def run(data_root, model_root, output):
    output, model_root = Path(output).resolve(), Path(model_root).resolve()
    if output.exists():
        raise ValueError('use a fresh replay output directory')
    protocol = json.loads((HERE / 'protocol.json').read_text())
    manifest = json.loads((HERE / 'data_manifest.json').read_text())
    if sha256(HERE / 'replay_fixture.json') != manifest['replay_fixture_sha256']:
        raise ValueError('replay fixture hash mismatch')
    fixture = json.loads((HERE / 'replay_fixture.json').read_text())
    frames = load_manifest_data(data_root, manifest, protocol['symbols'])
    inputs = make_inputs(frames, fixture)
    cfg = SystematicConfig.build(fixture['strategy_config'])
    risk = RiskConfig.build(fixture['risk_config'])
    costs = CostConfig.build(fixture['cost_config'])
    output.mkdir(parents=True)
    cases = [('existing_strategy', None, .45)] + [(name, model_root / (name + '.json'), .45)
             for name in protocol['models'] if name != 'prior']
    cases += [(f'calibrated_gbt_threshold_{threshold}', model_root / 'calibrated_gbt.json', threshold)
              for threshold in protocol['sensitivity_entry_probabilities']]
    summaries = []
    for multiplier in protocol['cost_multipliers']:
        for name, artifact, threshold in cases:
            settings = replace(cfg, ml_model_path=str(artifact) if artifact else '',
                               ml_min_entry_probability=threshold)
            cost = replace(costs, taker_fee_rate=costs.taker_fee_rate * multiplier,
                           maker_fee_rate=costs.maker_fee_rate * multiplier,
                           slippage_bps=costs.slippage_bps * multiplier)
            sb = replace(inputs, taker_fee_rate=inputs.taker_fee_rate * multiplier)
            result = run_portfolio_backtest([sb], settings, cost, fixture['initial_capital'], risk_cfg=risk).to_dict()
            if result['symbols'] != ['ETH_USDT']:
                raise ValueError('replay silently changed instrument set')
            if name == 'existing_strategy' and multiplier == 1:
                if (abs(result['return_pct'] - fixture['expected_return_pct']) > 1e-8
                        or abs(result['final_equity'] - fixture['expected_final_equity']) > 1e-6
                        or len(result['executions']) != fixture['expected_executions']):
                    raise AssertionError('existing baseline did not reproduce; stop comparison')
                actual = hashlib.sha256(json.dumps(result['executions'], sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                if actual != fixture['expected_execution_sha256']:
                    raise AssertionError('baseline exact execution hash differs; inspect before comparison')
            label = f'{name}_cost{multiplier}'
            summary = {k: result[k] for k in ['return_pct', 'final_equity', 'max_drawdown_pct',
                'sharpe', 'sortino', 'total_fees', 'total_slippage_cost', 'total_funding',
                'turnover_annualized', 'avg_gross_leverage', 'max_gross_leverage', 'warnings']}
            summary.update(case=label, threshold=threshold, cost_multiplier=multiplier,
                artifact_sha256=sha256(artifact) if artifact else None,
                entries=sum(e['action'] == 'open' for e in result['executions']),
                position_summary=position_summary(result['trades'], result['executions']),
                equity_points=len(result['equity_curve']), start_ts=result['start_ts'], end_ts=result['end_ts'])
            summaries.append(summary)
            write_json(output / (label + '.json'), result)
            print(json.dumps({k: summary[k] for k in ['case', 'return_pct', 'max_drawdown_pct', 'entries']}), flush=True)
    write_json(output / 'summary.json', dict(cases=summaries,
        source_data_manifest_sha256=sha256(HERE / 'data_manifest.json'),
        replay_fixture_sha256=sha256(HERE / 'replay_fixture.json'),
        limitations=['Single ETH historical research replay; windows previously inspected',
                     'No complete intrabar liquidation/ADL/order-book/partial-fill model',
                     'Double costs multiply fees and slippage, not historical funding',
                     'No runtime configuration/credentials/services were accessed']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--model-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.data_root, args.model_root, args.output)
