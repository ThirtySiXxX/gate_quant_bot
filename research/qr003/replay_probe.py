"""Explicit offline Phase A observer; executes the existing replay code once.

No downloads, model training, persistence, app startup or module monkey patches.
The returned original result remains the fill/accounting authority. See the QD
role report for the probe-local schema and interpretation of research skips.
"""
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
from types import FunctionType

from src import backtest


SOURCE_BASELINE = "475aaeaa5b9365b360563294e183d912c382b570"
EXPECTED_SOURCE_SHA256 = {
    "src/backtest.py": "9183091e85c4354720118c53f0d97b72022f018afa03d9e9479f4929f5a8540c",
    "src/strategy_execution.py": "e1eaa17ea1292c7e906d4634b274fe72f2a415dfa409054674a33c22b9b1f5bb",
    "src/execution_timing.py": "41d4593eaf345cdc8d26759605651e3e7bcfcb679604416b29fef80b821d9344",
    "src/position_sizing.py": "e80773ec1bf0ec88fdf8128f368649cf123d3ad92b615b46d3ce3e754c20efad",
    "src/strategy_signals.py": "aa3b9e71512008ff43f49639d8d2cf113e81def7ab031e41676453def86e78dc",
    "src/config.py": "29eed6a35c7ecb8b079b21616754c49774fa0bb9034dbba3fc2112734c968709",
    "src/costs.py": "356d3f5a29df9a64caeb40948fe4408dad81982fa5255cba051deb578b70621e",
    "src/portfolio.py": "1837e2601c2255515644394b6934f45a933d11c758f93aafae926d9bb120397d",
    "src/risk.py": "95410f4adf88f25e1030d108c43f3a4069c162523ba91bdff91e7462966826ad",
}


class ProbeBoundaryError(ValueError):
    """The pinned offline observer cannot faithfully handle the requested scope."""


@dataclass
class ProbeRun:
    result: backtest.PortfolioBacktestResult
    events: list[dict]
    skip_applied: bool
    call_counts: dict[str, int]
    source_sha256: dict[str, str]


def _snapshot(value):
    """Detach observations into finite JSON values; missing is never a zero."""
    if is_dataclass(value):
        return _snapshot(asdict(value))
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _snapshot(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_snapshot(v) for v in value]
    raise ProbeBoundaryError(f"unsupported observation type: {type(value).__name__}")


def _identity(value):
    return hashlib.sha256(json.dumps(_snapshot(value), sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def source_fingerprints():
    """Fail closed on source drift; this is not a general instrumentation API."""
    root = Path(backtest.__file__).resolve().parents[1]
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in EXPECTED_SOURCE_SHA256}
    changed = [name for name in actual if actual[name] != EXPECTED_SOURCE_SHA256[name]]
    if changed:
        raise ProbeBoundaryError("review required for replay source drift: " + ", ".join(changed))
    return actual


class _ForwardingProxy:
    def __init__(self, original, **overrides):
        self.original, self.overrides = original, overrides

    def __getattr__(self, name):
        return self.overrides[name] if name in self.overrides else getattr(self.original, name)


def probe_replay(symbol_inputs, sys_cfg, cost_cfg, initial_capital, *,
                 trajectory_id, skip_entry_at=None, risk_cfg=None, progress_cb=None):
    """Observe one original single-account replay; optionally skip one fresh open.

    Inputs are native replay arguments, plus an explicit trajectory name and one
    decision timestamp. ML must be off and sizing fixed-margin. Caller owns data
    validation, frozen dates/timing scope, branch budget and skip selection. No
    outcome is selected here. Global modules are never patched, even transiently.
    """
    if len(symbol_inputs) != 1 or symbol_inputs[0].symbol not in ("BTC_USDT", "ETH_USDT"):
        raise ProbeBoundaryError("one independent BTC_USDT or ETH_USDT account is required")
    if sys_cfg.ml_model_path or sys_cfg.position_sizing_mode != "fixed_margin":
        raise ProbeBoundaryError("Phase A requires ML off and inherited fixed-margin sizing")
    if not isinstance(trajectory_id, str) or not trajectory_id.strip():
        raise ProbeBoundaryError("trajectory_id must be a nonempty string")
    if skip_entry_at is not None and (isinstance(skip_entry_at, bool)
            or not isinstance(skip_entry_at, Real) or not math.isfinite(skip_entry_at)
            or skip_entry_at < 0):
        raise ProbeBoundaryError("skip_entry_at must be one finite UTC decision timestamp")
    hashes = source_fingerprints()
    original_replay = backtest.run_portfolio_backtest
    execution = original_replay.__globals__["execution"]
    signal_policy = original_replay.__globals__["signal_policy"]
    original_signal, original_decide = signal_policy.signal_at, execution.decide_execution
    original_build, original_fill = execution.build_order_plan, execution.record_fill
    events, contexts = [], {}
    counts = dict(signal_at=0, decide_execution=0, build_order_plan=0, record_fill=0)
    skipped = False

    def observe_signal(symbol, prepared, t, cfg):
        counts["signal_at"] += 1
        signal = original_signal(symbol, prepared, t, cfg)
        index = bisect_right(prepared["short_ts"], t) - 1
        event = dict(schema_version=1, trajectory_id=trajectory_id,
            event_id=f"{trajectory_id}:{symbol}:{float(t)}", symbol=symbol,
            decision_at=float(t), signal_available=signal is not None,
            signal=_snapshot(signal),
            decision_price=float(prepared["short_open"][index]) if index >= 0 else None,
            state_id=None, state_before=None, timing_state_after=None, decision_inputs=None, plan=None,
            pre_ml_entry_proposal=None, order_check=None, emitted_actions=None,
            post_budget_eligibility={"status": "not_evaluated", "reason": "no_shared_execution_decision"},
            skip_applied=False)
        contexts[symbol] = {"event": event, "signal": signal, "plan": None}
        events.append(event)
        return signal

    def observe_decide(symbol, target, signal, current_notional, equity, cfg,
                       timing, sizing, allow_increase=True, force_risk_reduction=False):
        context = contexts[symbol]
        if signal is not context["signal"]:
            raise ProbeBoundaryError("decision is not bound to the original observed signal")
        event = context["event"]
        event["state_before"] = _snapshot(dict(symbol=symbol, decision_at=event["decision_at"],
            current_notional=current_notional, equity=equity,
            timing=timing.dump(), sizing_ratios=sizing.ratios))
        event["state_id"] = _identity(event["state_before"])
        event["decision_inputs"] = _snapshot(dict(target=target,
            allow_increase=allow_increase, force_risk_reduction=force_risk_reduction))
        counts["decide_execution"] += 1
        plan = original_decide(symbol, target, signal, current_notional, equity, cfg,
            timing, sizing, allow_increase=allow_increase, force_risk_reduction=force_risk_reduction)
        context["plan"] = plan
        event["timing_state_after"] = _snapshot(timing.dump())
        event["plan"] = _snapshot(plan)
        event["pre_ml_entry_proposal"] = bool(current_notional == 0 and plan.model_target
                                                  and plan.rebalance and plan.allow_increase)
        event["post_budget_eligibility"] = {
            "status": "not_evaluated" if current_notional == 0 else "not_applicable",
            "reason": plan.block_reason or ("order_check_not_called" if current_notional == 0 else "existing_position"),
        }
        return plan

    def observe_build(symbol, plan, current_side, current_size, price, contract,
                      fee_rate, slippage_bps, *, budget=None, tiers=None):
        nonlocal skipped
        context = contexts[symbol]
        if plan is not context["plan"]:
            raise ProbeBoundaryError("order check is not bound to the observed original plan")
        event = context["event"]
        flat = current_size == 0 and current_side is None and event["state_before"]["current_notional"] == 0
        check = dict(status="pending", current_side=current_side, current_size=current_size,
            price=price, contract=_snapshot(contract), fee_rate=fee_rate,
            slippage_bps=slippage_bps, budget=_snapshot(budget),
            budget_checked=bool(plan.needs_entry_ticket and budget is not None),
            actions=None, ticket=None, error=None)
        event["order_check"] = check
        counts["build_order_plan"] += 1
        try:
            actions, ticket = original_build(symbol, plan, current_side, current_size, price,
                contract, fee_rate, slippage_bps, budget=budget, tiers=tiers)
        except Exception as exc:
            check.update(status="rejected", error={"type": type(exc).__name__, "message": str(exc)})
            event["post_budget_eligibility"] = {
                "status": "rejected" if flat else "not_applicable", "reason": str(exc)}
            raise  # The original loop still decides which exceptions to catch.
        check.update(status="accepted", actions=_snapshot(actions), ticket=_snapshot(ticket))
        eligible = bool(flat and event["pre_ml_entry_proposal"] and ticket is not None
                        and check["budget_checked"] and any(a == "open" and q > 0 for a, _, q in actions))
        event["post_budget_eligibility"] = {
            "status": ("eligible" if eligible else "rejected") if flat else "not_applicable",
            "reason": "executable_fresh_open" if eligible else (
                plan.block_reason or "no_executable_fresh_open" if flat else "existing_position"),
        }
        if eligible and not skipped and event["decision_at"] == skip_entry_at:
            # Only this eligible fresh entry; no decision/state mutation or fill feedback.
            actions = [item for item in actions if not (item[0] == "open" and item[2] > 0)]
            skipped = event["skip_applied"] = True
        event["emitted_actions"] = _snapshot(actions)
        return actions, ticket

    def observe_fill(*args, **kwargs):
        counts["record_fill"] += 1
        return original_fill(*args, **kwargs)

    # Execute the exact original code object, not a copied loop. These bindings
    # exist only for this call; other threads/nested replays keep their globals.
    namespace = dict(original_replay.__globals__)
    namespace["execution"] = _ForwardingProxy(execution, decide_execution=observe_decide,
        build_order_plan=observe_build, record_fill=observe_fill)
    namespace["signal_policy"] = _ForwardingProxy(signal_policy, signal_at=observe_signal)
    replay = FunctionType(original_replay.__code__, namespace, original_replay.__name__,
                          original_replay.__defaults__, original_replay.__closure__)
    replay.__kwdefaults__ = original_replay.__kwdefaults__
    result = replay(symbol_inputs, sys_cfg, cost_cfg, initial_capital,
                    progress_cb=progress_cb, risk_cfg=risk_cfg)

    # As-of metadata from the original ledger, never a second fill/account loop.
    executions = result.executions
    times = [row["time"] for row in executions]
    if times != sorted(times):
        raise ProbeBoundaryError("original execution times are not ordered")
    for event in events:
        index = bisect_left(times, event["decision_at"]) - 1
        previous = executions[index] if index >= 0 else None
        size = previous["position_after"] if previous else 0
        event["position_before"] = dict(size=size,
            side=previous["side"] if size else None,
            position_id=previous["position_id"] if size else None)
        if event["state_before"] is not None:
            event["state_id"] = _identity(dict(observed=event["state_before"],
                                               position_before=event["position_before"]))
    return ProbeRun(result, events, skipped, counts, hashes)
