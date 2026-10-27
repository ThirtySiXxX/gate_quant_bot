"""Offline QR-003 label accounting and dependence diagnostics. Never fits models.

Consumes the native replay ledger; it does not simulate orders or change exits.
The caller must separately provide the complete decision/probe trace and data
quality windows before claiming entry-opportunity coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.result.read_bytes()
    positions, reconciliation = audit_positions(json.loads(raw), args.trajectory)
    write_fresh(args.output, dict(input_sha256=hashlib.sha256(raw).hexdigest(),
        positions=positions, reconciliation=reconciliation, summary=summarize(positions),
        scope="ledger-only; data-quality windows and complete opportunity audit pending"))
