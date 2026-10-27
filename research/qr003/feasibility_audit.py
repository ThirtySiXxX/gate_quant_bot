"""Offline QR-003 label accounting and dependence diagnostics. Never fits models.

Consumes the native replay ledger; it does not simulate orders or change exits.
The caller must separately provide the complete decision/probe trace and data
quality windows before claiming entry-opportunity coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from src.crypto_ml import FEATURE_NAMES, FEATURE_VERSION, causal_features

FOLD_EDGES = (1785319200, 1787911200, 1790503200, 1793091600)
TERMINAL_REASON = "回测结束强平"
TOLERANCE_USDT = 1e-8


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"nonfinite/non-numeric {name}")
    return float(value)


def equal(a, b, name):
    if abs(finite(a, name) - finite(b, name)) > TOLERANCE_USDT:
        raise ValueError(f"accounting mismatch: {name}: {a} != {b}")


def audit_positions(result, trajectory_id, invalid_windows=()):
    """One label per actual position, including all reduction cash flows once.

    invalid_windows contains {symbol, start, end, reason}, in UTC seconds, where
    [start,end) covers decision times with missing/stale exit inputs. Any contact
    with a position's inclusive decision/exit range censors its research label.
    Replay accounting is still reconciled, including terminal forced closes.
    """
    if result.get("schema_version") != 3:
        raise ValueError("expected native replay result schema 3")
    executions, trades = result["executions"], result["trades"]
    if len({e["id"] for e in executions}) != len(executions):
        raise ValueError("duplicate execution id")
    if any(executions[i]["time"] > executions[i+1]["time"] for i in range(len(executions)-1)):
        raise ValueError("out-of-order executions")
    groups = defaultdict(list)
    for event in executions:
        for key in ("time", "bar_time", "price", "notional", "fee", "quantity", "position_before", "position_after"):
            finite(event[key], key)
        if min(event["price"], event["notional"], event["quantity"]) <= 0 or event["fee"] < 0:
            raise ValueError("invalid fill values")
        groups[event["position_id"]].append(event)
    unmatched = set(range(len(trades)))
    rows = []
    for position_id, events in groups.items():
        first = events[0]
        if first["action"] != "open" or first["position_before"] != 0:
            raise ValueError("position missing unique initial open")
        if first["side"] not in ("long", "short"):
            raise ValueError("invalid position side")
        quanto = first["notional"] / first["quantity"] / first["price"]
        if any(e["action"] == "add" for e in events):
            raise ValueError("Phase A fixed-ticket policy must not pyramid")
        size = 0
        matched = []
        for index, event in enumerate(events):
            if (event["symbol"], event["side"]) != (first["symbol"], first["side"]):
                raise ValueError("position identity/side changed")
            equal(event["position_before"], size, "quantity continuity")
            equal(event["notional"], event["quantity"] * event["price"] * quanto, "fill notional")
            if event["action"] == "open":
                if index != 0 or event["pnl"] is not None:
                    raise ValueError("duplicate open or realized entry pnl")
                size += event["quantity"]
            elif event["action"] in ("reduce", "close"):
                size -= event["quantity"]
                if size < 0 or (event["action"] == "close") != (size == 0):
                    raise ValueError("invalid reduction/close quantity")
                # Terminal trade.close_time is legacy bar-open time; execution.time
                # is bar-close availability. Natural fills use decision time.
                trade_time = event["bar_time"] if event["reason"] == TERMINAL_REASON else event["time"]
                candidates = [i for i in unmatched if
                    trades[i]["symbol"] == first["symbol"] and trades[i]["side"] == first["side"]
                    and trades[i]["open_time"] == first["time"] and trades[i]["close_time"] == trade_time]
                if len(candidates) != 1:
                    raise ValueError("exit/trade mapping is missing or ambiguous")
                ti = candidates[0]
                trade = trades[ti]
                for key in ("pnl", "gross", "fees", "funding"):
                    finite(trade[key], key)
                equal(trade["pnl"], event["pnl"], "exit pnl")
                equal(trade["gross"] - trade["fees"] - trade["funding"], trade["pnl"], "net cash flow")
                equal(trade["exit_price"], event["price"], "exit price")
                equal(trade["entry_price"], first["price"], "entry price")
                equal(trade["gross"], (event["price"]-first["price"])*event["quantity"]
                      * quanto * (1 if first["side"] == "long" else -1), "gross pnl")
                unmatched.remove(ti)
                matched.append(trade)
            else:
                raise ValueError("unsupported execution action")
            equal(event["position_after"], size, "quantity after fill")
        last = events[-1]
        # Native replay always closes at end; failure to do so cannot reconcile a
        # final cash-only equity with the current result schema.
        if size != 0 or last["action"] != "close":
            raise ValueError("unsettled replay ledger")
        equal(sum(e["fee"] for e in events), sum(t["fees"] for t in matched), "position fee allocation")
        terminal = last["reason"] == TERMINAL_REASON
        available_end = last["bar_time"] + 3600 if terminal else last["time"]
        if terminal:
            equal(last["time"], available_end, "terminal execution availability")
        reasons = ["terminal_forced_close"] if terminal else []
        for window in invalid_windows:
            if not finite(window["start"], "gap start") < finite(window["end"], "gap end"):
                raise ValueError("invalid data-quality window")
            if (window["symbol"] == first["symbol"] and window["start"] <= available_end
                    and first["time"] < window["end"]):
                reasons.append(window["reason"])
        net = sum(t["pnl"] for t in matched)
        row = dict(schema_version=1, instrument_id="gate:usdt:" + first["symbol"],
            symbol=first["symbol"], trajectory_id=trajectory_id, position_id=position_id,
            origin_id=f'{first["symbol"]}:{first["time"]:.0f}:{first["side"]}',
            entry_at=first["time"], side=first["side"], initial_notional_usdt=first["notional"],
            observation_end=available_end, duration_hours=(available_end-first["time"])/3600,
            label_end=None if reasons else available_end, censored=bool(reasons),
            censor_reasons=sorted(set(reasons)),
            realized_net_pnl_usdt=net, realized_fees_usdt=sum(t["fees"] for t in matched),
            signed_funding_paid_usdt=sum(t["funding"] for t in matched),
            reductions=sum(e["action"] == "reduce" for e in events), exit_reason=last["reason"],
            target_net_return_fraction=None if reasons else net / first["notional"],
            target_positive=None if reasons else int(net > 0))
        rows.append(row)
    if unmatched:
        raise ValueError("unmatched or duplicate trade records")
    cash = math.fsum(t["pnl"] for t in trades)
    equal(result["initial_capital"] + cash, result["final_equity"], "final equity")
    equal(math.fsum(t["fees"] for t in trades), result["total_fees"], "total fees")
    equal(math.fsum(t["funding"] for t in trades), result["total_funding"], "total funding")
    equal(math.fsum(e["fee"] for e in executions), result["total_fees"], "execution fees")
    return rows, dict(initial_equity_usdt=result["initial_capital"],
        final_equity_usdt=result["final_equity"], ledger_net_pnl_usdt=cash,
        residual_usdt=result["final_equity"]-result["initial_capital"]-cash,
        tolerance_usdt=TOLERANCE_USDT, execution_sha256=digest(executions),
        terminal_cash_included=True, slippage_already_in_fill_prices=True)


def feature_records(candles, decision_times):
    """Use only exactly the hour closed at t; never forward-fill across a gap."""
    frame = candles.reset_index(drop=True)
    values = causal_features(frame)
    indices = {int(t): i for i, t in enumerate(frame.timestamp)}
    records = {}
    for decision_at in sorted(set(decision_times)):
        if finite(decision_at, "decision time") % 3600 != 0:
            raise ValueError("decision time must be an hourly boundary")
        i = indices.get(int(decision_at)-3600)
        ok = i is not None and np.isfinite(values.iloc[i].to_numpy()).all()
        records[decision_at] = dict(feature_version=FEATURE_VERSION,
            feature_names=list(FEATURE_NAMES), units="dimensionless",
            decision_at=decision_at, bar_open_at=decision_at-3600,
            available_at=decision_at if ok else None,
            status="available" if ok else "unavailable",
            values=values.iloc[i].to_numpy().tolist() if ok else None,
            reason=None if ok else "missing_closed_bar_or_169_contiguous_hour_warmup",
            availability_assumption="bar close; actual feed arrival not observed")
    return records


def input_quality(symbol, frames, start, end, funding_interval=28800):
    """Audit raw inputs before replay; report missing/stale decision-time windows.

    Funding timestamps are settlement/as-of times; bar timestamps are opens. An
    ideal close-time arrival assumption is disclosed, never fabricated provenance.
    A full periodic grid is required only over evaluated decision times; limited
    funding warmup is separately visible in the coverage table.
    """
    if not start < end or start % 3600 or end % 3600 or funding_interval <= 0:
        raise ValueError("invalid observation interval")
    windows, coverage = [], {}
    for name, step in (("1h", 3600), ("4h", 14400), ("1d", 86400), ("funding", funding_interval)):
        if name not in frames or frames[name].empty:
            raise ValueError("missing input: " + name)
        frame = frames[name]
        columns = ["timestamp", "funding_rate"] if name == "funding" else [
            "timestamp", "open", "high", "low", "close", "volume"]
        if any(c not in frame for c in columns) or not np.isfinite(frame[columns].to_numpy(dtype=float)).all():
            raise ValueError("invalid input values: " + name)
        times = frame.timestamp.to_numpy(dtype=float)
        if ((times < 0).any() or (np.diff(times) <= 0).any() or (times % 1 != 0).any()
                or (name != "funding" and (times % step != 0).any())):
            raise ValueError("invalid timestamp grid: " + name)
        if name != "funding":
            if ((frame[["open", "high", "low", "close"]] <= 0).any().any()
                    or (frame.volume < 0).any()
                    or (frame.high < frame[["open", "close", "low"]].max(axis=1)).any()
                    or (frame.low > frame[["open", "close"]].min(axis=1)).any()):
                raise ValueError("invalid OHLC: " + name)
        availability = times if name == "funding" else times + step
        decisions = np.arange(start, end, 3600, dtype=float)
        idx = np.searchsorted(availability, decisions, side="right") - 1
        found = availability[np.maximum(idx, 0)]
        # Never silently use a stale candle or stale funding snapshot as a complete
        # label window. The production replay can continue; these labels censor.
        # Public settlement timestamps can be seconds after the nominal grid.
        # Keep the exact timestamps and original as-of rates. For completeness
        # diagnosis allow their next hourly observation; this does NOT advance
        # any rate's availability or alter the existing funding cost formula.
        grace = 3600 if name == "funding" else 0
        invalid = (idx < 0) | (decisions - found >= step + grace)
        bad = decisions[invalid]
        if len(bad):
            beginning = previous = bad[0]
            for t in list(bad[1:]) + [None]:
                if t is None or t != previous + 3600:
                    windows.append(dict(symbol=symbol, start=float(beginning),
                        end=float(previous+3600), reason="missing_or_stale_" + name))
                    beginning = t
                previous = t
        missing_execution = decisions[~np.isin(decisions, times)] if name == "1h" else []
        for t in missing_execution:
            windows.append(dict(symbol=symbol, start=float(t), end=float(t+3600),
                                reason="missing_execution_open_1h"))
        coverage[name] = dict(rows=len(frame), first_open_or_settlement=float(times[0]),
            last_open_or_settlement=float(times[-1]),
            internal_missing_periods=None if name == "funding" else int(np.sum(np.diff(times)/step-1)),
            observed_gap_seconds_min=float(np.min(np.diff(times))) if len(times) > 1 else None,
            observed_gap_seconds_max=float(np.max(np.diff(times))) if len(times) > 1 else None,
            funding_freshness_grace_seconds=grace,
            closed_or_settled_before_start=int(np.sum(availability <= start)),
            evaluated_invalid_decisions=int(invalid.sum()),
            missing_execution_open_decisions=len(missing_execution),
            available_at_assumption="settlement timestamp" if name == "funding" else "bar open plus interval",
            real_arrival_times_observed=False)
    return dict(symbol=symbol, start=start, end_exclusive=end, coverage=coverage,
                invalid_windows=windows, complete_evaluation_inputs=not windows,
                volume_units="raw source v representation preserved; no cross-asset absolute-volume comparison")


def interval_clusters(rows, buffer_seconds=86400):
    """Connected overlapping market-time windows across ALL assets/branches.

    This is a diagnostic grouping, not an estimate of effective sample size.
    The 24h buffer retains the preregistered embargo dependence conservatively.
    """
    if buffer_seconds < 0:
        raise ValueError("negative cluster buffer")
    output = []
    for row in sorted(rows, key=lambda r: (r["entry_at"], r["observation_end"])):
        start, end = row["entry_at"], row["observation_end"] + buffer_seconds
        if end < start:
            raise ValueError("negative duration")
        if not output or start > output[-1]["end"]:
            output.append(dict(start=start, end=end, origins=set(), rows=0, symbols=set()))
        cluster = output[-1]
        cluster["end"] = max(cluster["end"], end)
        cluster["origins"].add(row["origin_id"])
        cluster["symbols"].add(row["symbol"])
        cluster["rows"] += 1
    return [{**c, "origins": sorted(c["origins"]), "symbols": sorted(c["symbols"])} for c in output]


def audit_events(payload, candles):
    """Validate QD probe-local schema 1 and link candidates to actual fills.

    Repeated hourly proposals remain visible with their state identities. They
    are not new independently labelled opportunities; unfilled targets stay null.
    """
    events, result = payload["events"], payload["result"]
    times = [e["decision_at"] for e in events]
    if len(set(times)) != len(times) or times != sorted(times):
        raise ValueError("duplicate/out-of-order observer events")
    if len(events) != payload["call_counts"]["signal_at"]:
        raise ValueError("observer changed/missed signal call count")
    features = feature_records(candles, times)
    opens = {e["time"]: e for e in result["executions"] if e["action"] == "open"}
    prices = dict(zip(candles.timestamp, candles.open))
    records, counts, blocks = [], Counter(), Counter()
    for event in events:
        t, signal, plan = event["decision_at"], event["signal"], event["plan"]
        if event["schema_version"] != 1 or event["trajectory_id"] != payload["trajectory_id"]:
            raise ValueError("probe schema or trajectory mismatch")
        equal(event["decision_price"], prices[t], "decision uses current open")
        flat = event["position_before"]["size"] == 0
        if plan is not None:
            state = event["state_before"]
            identity = {"observed": state, "position_before": event["position_before"]}
            if digest(identity) != event["state_id"] or (state["current_notional"] == 0) != flat:
                raise ValueError("state identity or ledger flat status differs")
            proposed = bool(flat and plan["model_target"] and plan["rebalance"] and plan["allow_increase"])
            if proposed != event["pre_ml_entry_proposal"]:
                raise ValueError("pre-ML proposal predicate differs")
        else:
            proposed = False
        if signal is not None and signal.get("timing_feature"):
            if signal["timing_feature"]["bar_ts"] > t-3600:
                raise ValueError("future/current unclosed timing bar")
        status = event["post_budget_eligibility"]["status"]
        eligible, skipped = status == "eligible", event["skip_applied"]
        if eligible and (not flat or not proposed or not event["order_check"]["budget_checked"]):
            raise ValueError("invalid executable candidate")
        if skipped and (not eligible or t != payload["skip_entry_at"]):
            raise ValueError("skip beyond the fixed fresh-entry boundary")
        executed = t in opens
        if executed != (eligible and not skipped):
            raise ValueError("observer eligibility does not match actual ledger open")
        counts["decisions"] += 1
        counts["flat" if flat else "held"] += 1
        counts["signal_available"] += int(event["signal_available"])
        counts["proposed"] += int(proposed)
        counts["executable"] += int(eligible)
        counts["skipped"] += int(skipped)
        counts["executed"] += int(executed)
        if flat:
            counts["flat_with_features"] += int(features[t]["status"] == "available")
            if not eligible:
                blocks[event["post_budget_eligibility"]["reason"]] += 1
        record = dict(trajectory_id=payload["trajectory_id"], symbol=event["symbol"],
            decision_at=t, state_id=event["state_id"], flat=flat,
            signal_available=event["signal_available"], pre_ml_proposed=proposed,
            eligibility=status, eligible=eligible, skipped=skipped, executed=executed,
            proposed_side=("long" if plan["model_target"] > 0 else "short") if proposed else None,
            rejection_reason=None if eligible else event["post_budget_eligibility"]["reason"],
            feature_status=features[t]["status"] if flat else "not_candidate_held",
            label_status="actual_position_pending_label_join" if executed else "no_executed_position_label",
            position_id=opens[t]["position_id"] if executed else None)
        records.append(record)
    if counts["skipped"] != int(payload["skip_applied"]):
        raise ValueError("skip count differs")
    if sum(e["plan"] is not None for e in events) != payload["call_counts"]["decide_execution"]:
        raise ValueError("missing original execution decision")
    if sum(e["order_check"] is not None for e in events) != payload["call_counts"]["build_order_plan"]:
        raise ValueError("missing original order check")
    return dict(counts=dict(counts), flat_rejection_reasons=dict(blocks), records=records,
        unlabelled_executable_candidates=counts["executable"]-counts["executed"],
        claim="Complete observations for this single trajectory; not all possible filtering policies")


def compare_paths(baseline, branch, skip_at):
    """Describe path changes without choosing a profitable branch."""
    base = {e["decision_at"]: e for e in baseline["records"]}
    other = {e["decision_at"]: e for e in branch["records"]}
    first_state, first_qualification = None, None
    new_candidates = []
    for t in sorted(base.keys() & other.keys()):
        a, b = base[t], other[t]
        if t <= skip_at and a["state_id"] != b["state_id"]:
            raise ValueError("branch changed state before intervention")
        if t < skip_at and (a["eligible"], a["executed"]) != (b["eligible"], b["executed"]):
            raise ValueError("branch changed actions before intervention")
        if t > skip_at and a["state_id"] != b["state_id"] and first_state is None:
            first_state = t
        if t > skip_at and (a["flat"], a["pre_ml_proposed"], a["eligible"]) != (
                b["flat"], b["pre_ml_proposed"], b["eligible"]) and first_qualification is None:
            first_qualification = t
        if t > skip_at and b["eligible"] and not a["eligible"]:
            new_candidates.append(dict(decision_at=t, side=b["proposed_side"],
                baseline_held=not a["flat"], executed=b["executed"], state_id=b["state_id"]))
    return dict(skip_entry_at=skip_at, first_state_divergence=first_state,
        first_qualification_divergence=first_qualification, new_branch_candidates=new_candidates,
        unmatched_decision_times=sorted(base.keys() ^ other.keys()),
        qualification="Related counterfactual paths, not independent extra training samples")


def mature_before(row, boundary, embargo_seconds=86400):
    return (not row["censored"] and row["label_end"] is not None
            and row["label_end"] + embargo_seconds < boundary)


def summarize(rows, fold_edges=FOLD_EDGES):
    if any(a >= b for a, b in zip(fold_edges, fold_edges[1:])):
        raise ValueError("invalid chronological folds")
    folds = []
    for a, b in zip(fold_edges, fold_edges[1:]):
        selected = [r for r in rows if a <= r["entry_at"] < b]
        folds.append(dict(start=a, end_exclusive=b, entries=len(selected),
            natural_labels=sum(not r["censored"] for r in selected),
            natural_labels_closed_in_fold=sum(not r["censored"] and r["label_end"] < b for r in selected),
            mature_before_start=sum(mature_before(r, a) for r in rows),
            censored=sum(r["censored"] for r in selected),
            side_counts=dict(Counter(r["side"] for r in selected))))
    origins = Counter(r["origin_id"] for r in rows)
    return dict(position_rows=len(rows), natural_labels=sum(not r["censored"] for r in rows),
        censored=sum(r["censored"] for r in rows), distinct_market_origins=len(origins),
        repeated_origin_rows=sum(n-1 for n in origins.values()), folds=folds,
        exit_reasons=dict(Counter(r["exit_reason"] for r in rows)),
        side_counts=dict(Counter(r["side"] for r in rows)),
        holding_hours={"min": min((r["duration_hours"] for r in rows), default=None),
                       "median": float(np.median([r["duration_hours"] for r in rows])) if rows else None,
                       "max": max((r["duration_hours"] for r in rows), default=None)},
        overlap_clusters=interval_clusters(rows, 0), embargo_clusters=interval_clusters(rows),
        effective_independent_sample_size=None,
        limitation="Executed position labels alone do not cover all eligible opportunities; clusters are not independent sample estimates")


def write_fresh(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_phase_a_inputs(spec):
    """Explicit frozen public file paths only; no app config, network or models."""
    from src.backtest import SymbolBacktestInputs
    from src.config import CostConfig, RiskConfig, SystematicConfig
    if spec["schema_version"] != 1 or set(spec["instruments"]) != {"BTC_USDT", "ETH_USDT"}:
        raise ValueError("Phase A must include exactly BTC and ETH")
    output = {}
    for symbol, record in spec["instruments"].items():
        fixture = record["fixture"]
        contract = fixture["contract"]
        if contract["name"] != symbol or fixture["strategy_config"]["ml_model_path"]:
            raise ValueError("wrong contract or ML enabled")
        frames = {}
        for interval in ("1h", "4h", "1d", "funding"):
            source = record["files"][interval]
            if source["select_until"] > FOLD_EDGES[-1] or source["select_from"] >= source["select_until"]:
                raise ValueError("selection exceeds frozen cutoff or is empty")
            raw = Path(source["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError("input hash mismatch: " + source["path"])
            frame = pd.read_csv(source["path"])
            # Selection boundaries are frozen before looking at baseline outcomes.
            frames[interval] = frame[(frame.timestamp >= source["select_from"])
                & (frame.timestamp < source["select_until"])].reset_index(drop=True)
        quality = input_quality(symbol, frames, FOLD_EDGES[0], FOLD_EDGES[-1],
                                float(contract["funding_interval"]))
        if not quality["complete_evaluation_inputs"]:
            raise ValueError("missing evaluation input coverage: " + symbol)
        sb = SymbolBacktestInputs(symbol=symbol, df_short=frames["1h"], df_main=frames["4h"],
            df_cov=frames["4h"], df_regime=frames["1d"], funding_history=frames["funding"],
            funding_rate=float(contract["funding_rate"]), funding_interval_sec=float(contract["funding_interval"]),
            quanto_multiplier=float(contract["quanto_multiplier"]),
            taker_fee_rate=fixture["cost_config"]["taker_fee_rate"],
            order_size_min=int(contract["order_size_min"]), test_start_ts=FOLD_EDGES[0],
            leverage_min=float(contract["leverage_min"]), leverage_max=float(contract["leverage_max"]),
            order_size_max=int(contract["order_size_max"]),
            market_order_size_max=float(contract["market_order_size_max"]),
            risk_limit_tiers=fixture["risk_limit_tiers"])
        output[symbol] = dict(input=sb, frames=frames, quality=quality, fixture=fixture,
            config=SystematicConfig.build(fixture["strategy_config"]),
            costs=CostConfig.build(fixture["cost_config"]), risk=RiskConfig.build(fixture["risk_config"]))
    return output


def run_phase_a(spec_path, probe_path, output_dir):
    """Run the finite predeclared trajectories through the separately reviewed QD probe."""
    spec = json.loads(Path(spec_path).read_text())
    raw_probe = Path(probe_path).read_bytes()
    if hashlib.sha256(raw_probe).hexdigest() != spec["qd_probe_sha256"]:
        raise ValueError("QD probe hash differs from reviewed candidate")
    root = Path(__file__).resolve().parents[2]
    for path, expected in spec["source_sha256"].items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen strategy/consumer source changed: " + path)
    output = Path(output_dir)
    if output.exists():
        raise ValueError("use a new output directory; previous evidence is immutable")
    inputs = load_phase_a_inputs(spec)
    loader = importlib.util.spec_from_file_location("qr003_reviewed_qd_probe", probe_path)
    module = importlib.util.module_from_spec(loader)
    sys.modules[loader.name] = module
    loader.loader.exec_module(module)
    output.mkdir(parents=True)
    write_fresh(output / "input-spec.json", spec)
    audits = {}
    for symbol in ("ETH_USDT", "BTC_USDT"):
        data = inputs[symbol]
        fixture = data["fixture"]
        write_fresh(output / f"{symbol}-quality.json", data["quality"])
        cases = [("allow_all", None)]
        baseline = None
        for case, skip_at in cases:
            trajectory = symbol + ":" + case
            run = module.probe_replay([data["input"]], data["config"], data["costs"],
                fixture["initial_capital"], trajectory_id=trajectory, skip_entry_at=skip_at,
                risk_cfg=data["risk"])
            result = run.result.to_dict()
            if result["symbols"] != [symbol] or result["start_ts"] != FOLD_EDGES[0]:
                raise ValueError("replay changed requested symbol/start")
            positions, reconciliation = audit_positions(result, trajectory, data["quality"]["invalid_windows"])
            if case == "allow_all":
                baseline = result
                if symbol == "ETH_USDT":
                    if reconciliation["execution_sha256"] != fixture["expected_execution_sha256"]:
                        raise ValueError("ETH baseline no longer reproduces exactly")
                    equal(result["final_equity"], fixture["expected_final_equity"], "ETH baseline equity")
                first_entries = []
                # Time-only selection; no profit, exit, or diagnostic score lookup.
                for fold, (a, b) in enumerate(zip(FOLD_EDGES, FOLD_EDGES[1:]), 1):
                    opens = [e["time"] for e in baseline["executions"]
                             if e["action"] == "open" and a <= e["time"] < b]
                    if opens:
                        first_entries.append((f"skip_fold_{fold}", min(opens)))
                if symbol == "ETH_USDT" and [v for _, v in first_entries] != [1785607200,1788040800,1790618400]:
                    raise ValueError("ETH preregistered skip timestamps changed")
                write_fresh(output / f"{symbol}-skip-selection.json", dict(
                    method="first baseline entry per fixed old fold, selected by time only",
                    candidates=first_entries, baseline_execution_sha256=reconciliation["execution_sha256"]))
                cases.extend(first_entries)
            if bool(run.skip_applied) != (skip_at is not None):
                raise ValueError("skip was not applied exactly at selected eligible entry")
            payload = dict(result=result, events=run.events, skip_applied=run.skip_applied,
                call_counts=run.call_counts, source_sha256=run.source_sha256,
                trajectory_id=trajectory, skip_entry_at=skip_at)
            write_fresh(output / f"{symbol}-{case}.json", payload)
            opportunity = audit_events(payload, data["frames"]["1h"])
            for position in positions:
                entry = next(e for e in opportunity["records"] if e["decision_at"] == position["entry_at"])
                position["state_id"] = entry["state_id"]
                position["feature_status"] = entry["feature_status"]
                entry["label_status"] = "censored" if position["censored"] else "natural_label"
            write_fresh(output / f"{symbol}-{case}-opportunities.json", opportunity)
            audit = dict(positions=positions, reconciliation=reconciliation, summary=summarize(positions),
                call_counts=run.call_counts, raw_run_sha256=digest(payload),
                opportunity_counts=opportunity["counts"], flat_rejection_reasons=opportunity["flat_rejection_reasons"])
            if case == "allow_all":
                baseline_opportunity = opportunity
            else:
                audit["path_dependence"] = compare_paths(baseline_opportunity, opportunity, skip_at)
            write_fresh(output / f"{symbol}-{case}-ledger-audit.json", audit)
            audits[trajectory] = audit
            print(json.dumps(dict(trajectory=trajectory, entries=len(positions),
                natural_labels=audit["summary"]["natural_labels"],
                censored=audit["summary"]["censored"], skip_applied=run.skip_applied)), flush=True)
    write_fresh(output / "ledger-summary.json", audits)
    return audits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--trajectory")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--phase-a-spec", type=Path)
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    if args.phase_a_spec:
        if not args.probe or not args.output_directory or args.result:
            parser.error("Phase A requires --probe and --output-directory, no --result")
        run_phase_a(args.phase_a_spec, args.probe, args.output_directory)
        raise SystemExit(0)
    if not args.result or not args.trajectory or not args.output:
        parser.error("ledger audit requires --result, --trajectory and --output")
    raw = args.result.read_bytes()
    positions, reconciliation = audit_positions(json.loads(raw), args.trajectory)
    write_fresh(args.output, dict(input_sha256=hashlib.sha256(raw).hexdigest(),
        positions=positions, reconciliation=reconciliation, summary=summarize(positions),
        scope="ledger-only; data-quality windows and complete opportunity audit pending"))
