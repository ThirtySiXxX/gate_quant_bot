"""Versioned collaboration payloads; standalone, with no trading or data I/O.

Not a replacement for legacy runtime formats. Consumers must call validate at
an explicit adapter boundary; see docs/INTERFACES.md for units and ownership.
"""
import json
import math
import re


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _strings(value):
    return (isinstance(value, list) and bool(value) and all(_text(v) for v in value)
            and len(set(value)) == len(value))


def _instrument(value):
    # v1 intentionally supports the existing Gate USDT linear-perpetual scope.
    return isinstance(value, str) and re.fullmatch(r"gate:usdt:[A-Z0-9]+_USDT", value) is not None


def _instruments(value):
    return _strings(value) and all(_instrument(v) for v in value)


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _choice(*choices):
    return lambda value: isinstance(value, str) and value in choices


RULES = {
    "text": _text,
    "reason": lambda v: isinstance(v, str),
    "number": _number,
    "positive": lambda v: _number(v) and v > 0,
    "nonnegative": lambda v: _number(v) and v >= 0,
    "fraction": lambda v: _number(v) and 0 <= v <= 1,
    "integer": lambda v: type(v) is int and v > 0,
    "count": lambda v: type(v) is int and v >= 0,
    "bool": lambda v: type(v) is bool,
    "instrument": _instrument,
    "instruments": _instruments,
    "strings": _strings,
    "labels": lambda v: isinstance(v, list) and bool(v) and all(_text(x) for x in v),
    "hash": _hash,
    "mapping": lambda v: isinstance(v, dict) and bool(v),
    "warnings": lambda v: isinstance(v, list) and all(_text(x) for x in v),
    "mode": _choice("paper"),  # v1 is not an authorization channel for live.
    "status": _choice("ok", "unavailable"),
    "volume_unit": _choice("contracts", "base", "quote"),
    "policy": _choice("strict", "replay_with_warnings"),
    "action": _choice("target", "hold", "exit"),
    "model_kind": _choice("logistic", "gradient_boosting"),
    "nullable": lambda v: v is None or isinstance(v, (dict, list)),
    "sizing": _choice("fixed_margin", "volatility"),
    "activation": _choice("research", "paper_approved"),
}

# Every field is required; optional information uses explicit null. Changes to
# these definitions are shared-contract changes, even if no runtime imports us.
SCHEMAS = {
    "market_data": dict(instrument_id="instrument", interval_seconds="integer",
        bar_open_ts="nonnegative", bar_close_ts="nonnegative", available_at="nonnegative",
        open="positive", high="positive", low="positive", close="positive", volume="nonnegative",
        volume_unit="volume_unit", quanto_multiplier="positive", source="text",
        data_sha256="hash", funding="nullable"),
    "features": dict(instrument_id="instrument", interval_seconds="integer",
        bar_open_ts="nonnegative", as_of="nonnegative", available_at="nonnegative",
        max_source_available_at="nonnegative", feature_set_id="text", feature_version="integer",
        names="strings", units="labels", values="nullable", status="status", reason="reason"),
    "prediction": dict(instrument_id="instrument", model_id="text", artifact_sha256="hash",
        feature_set_id="text", feature_version="integer", as_of="nonnegative",
        available_at="nonnegative", valid_until="nonnegative", horizon_seconds="integer",
        probabilities="nullable", status="status", reason="reason"),
    "signal": dict(instrument_id="instrument", strategy_id="text", config_sha256="hash",
        risk_limits_id="text", decision_at="nonnegative", sources_available_at="nonnegative",
        expires_at="nonnegative", action="action", target_notional_usdt="number", reason="text"),
    "model_metadata": dict(model_id="text", artifact_sha256="hash", bundle_schema_version="integer", model_kind="model_kind",
        instrument_ids="instruments", interval_seconds="integer", feature_set_id="text",
        feature_version="integer", feature_names="strings", classes="nullable",
        trained_until="nonnegative", valid_from="nonnegative", valid_until="nonnegative",
        embargo_seconds="count", label_horizon_seconds="integer", label_entry="text",
        round_trip_cost_fraction="fraction", edge_fraction="fraction", data_sha256="hash",
        code_revision="text", package_versions="mapping", seed="count",
        validation="mapping", activation="activation"),
    "strategy_config": dict(strategy_id="text", config_id="text", mode="mode",
        instrument_ids="instruments", effective_at="nonnegative", parameters="mapping",
        position_sizing_mode="sizing", model_id="reason", risk_limits_id="text",
        config_sha256="hash"),
    "backtest_request": dict(request_id="text", instrument_ids="instruments",
        start_ts="nonnegative", end_ts="nonnegative", data_sha256="hash",
        config_sha256="hash", code_revision="text", initial_equity_usdt="positive",
        strategy_config="mapping", risk_limits="mapping", costs="mapping",
        completeness_policy="policy"),
    "backtest_result": dict(request_id="text", requested_instrument_ids="instruments",
        accepted_instrument_ids="instruments", start_ts="nonnegative", end_ts="nonnegative",
        data_sha256="hash", config_sha256="hash", code_revision="text",
        initial_equity_usdt="positive", final_equity_usdt="number", return_fraction="number",
        max_drawdown_fraction="nonnegative", fees_usdt="nonnegative", funding_paid_usdt="number",
        completed_positions="count", execution_count="count", warnings="warnings",
        completeness_policy="policy", legacy_result_schema_version="integer"),
    "risk_limits": dict(risk_limits_id="text", effective_at="nonnegative", expires_at="nonnegative",
        margin_mode="text", require_verified_cross="bool", max_gross_notional_to_equity="positive",
        max_instrument_notional_to_equity="positive", max_order_notional_usdt="positive",
        max_leverage="positive", daily_loss_limit_enabled="bool", daily_loss_limit_fraction="fraction",
        allow_increase="bool", allow_reduce="bool"),
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(record, expected):
    _require(isinstance(record, dict) and set(record) == set(expected),
             "fields do not match the versioned contract")
    for key, rule in expected.items():
        _require(RULES[rule](record[key]), "invalid field: " + key)


def validate_contract(kind, record):
    """Raise ValueError for invalid v1 payloads; no mutation, I/O or activation.

    Local invariants only. Call validate_exchange for cross-record identity and
    availability checks. Hash content verification belongs to the adapter.
    """
    _require(isinstance(kind, str) and kind in SCHEMAS, "unknown contract kind")
    fields = dict(SCHEMAS[kind], schema_version="integer", kind="text", created_at="nonnegative")
    _fields(record, fields)
    r = record
    _require(r["schema_version"] == 1 and r["kind"] == kind, "unsupported version or kind")
    try:
        json.dumps(r, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("payload must be finite JSON") from exc
    if "available_at" in r:
        _require(r["available_at"] <= r["created_at"], "emission precedes availability")

    if kind == "market_data":
        _require(r["bar_open_ts"] + r["interval_seconds"] == r["bar_close_ts"] <= r["available_at"],
                 "bar is not closed/available")
        _require(r["low"] <= min(r["open"], r["close"]) <= max(r["open"], r["close"]) <= r["high"],
                 "invalid OHLC bounds")
        if r["funding"] is not None:
            _fields(r["funding"], dict(settlement_at="nonnegative", available_at="nonnegative",
                                      rate="number", interval_seconds="integer"))
            _require(r["funding"]["settlement_at"] <= r["funding"]["available_at"] <= r["available_at"],
                     "future funding")
    elif kind == "features":
        _require(r["bar_open_ts"] + r["interval_seconds"] <= r["max_source_available_at"]
                 <= r["as_of"] <= r["available_at"], "feature source is unavailable")
        # Units may repeat; unlike names they are not identifiers.
        _require(len(r["names"]) == len(r["units"]), "feature units mismatch")
        if r["status"] == "ok":
            _require(isinstance(r["values"], list) and len(r["values"]) == len(r["names"])
                     and all(_number(v) for v in r["values"]), "invalid feature vector")
        else:
            _require(r["values"] is None and _text(r["reason"]), "unavailable features need reason/null")
    elif kind == "prediction":
        _require(r["as_of"] <= r["available_at"] <= r["created_at"] < r["valid_until"], "invalid prediction window")
        if r["status"] == "ok":
            _fields(r["probabilities"], dict(short="fraction", neutral="fraction", long="fraction"))
            _require(abs(sum(r["probabilities"].values()) - 1) <= 1e-8, "probabilities must sum to one")
        else:
            _require(r["probabilities"] is None and _text(r["reason"]), "unavailable prediction needs reason/null")
    elif kind == "signal":
        _require(r["sources_available_at"] <= r["decision_at"] <= r["created_at"] < r["expires_at"],
                 "signal uses future/stale data")
        _require(r["action"] != "exit" or r["target_notional_usdt"] == 0, "exit target must be zero")
    elif kind == "model_metadata":
        _require(r["bundle_schema_version"] == 1 and r["interval_seconds"] == 3600
                 and r["classes"] == [-1, 0, 1] and all(type(x) is int for x in r["classes"]),
                 "unsupported model scope/classes")
        _require(r["label_entry"] == "next_bar_open", "unsupported label timing")
        _require(r["trained_until"] < r["valid_from"] < r["valid_until"]
                 and r["trained_until"] + r["embargo_seconds"] <= r["valid_from"], "training/embargo overlap")
    elif kind == "strategy_config":
        _require(r["effective_at"] >= r["created_at"], "config effective before creation")
    elif kind in ("backtest_request", "backtest_result"):
        _require(r["start_ts"] < r["end_ts"], "empty backtest interval")
        if kind == "backtest_request":
            validate_contract("strategy_config", r["strategy_config"])
            validate_contract("risk_limits", r["risk_limits"])
            _fields(r["costs"], dict(taker_fee_fraction="fraction", slippage_bps="nonnegative",
                                     funding_policy="text"))
            _require(r["strategy_config"]["instrument_ids"] == r["instrument_ids"]
                     and r["strategy_config"]["config_sha256"] == r["config_sha256"]
                     and r["strategy_config"]["risk_limits_id"] == r["risk_limits"]["risk_limits_id"],
                     "request snapshots disagree")
        else:
            requested, accepted = set(r["requested_instrument_ids"]), set(r["accepted_instrument_ids"])
            _require(accepted <= requested, "unexpected accepted instruments")
            _require(r["completeness_policy"] != "strict" or accepted == requested, "strict coverage incomplete")
            _require(accepted == requested or bool(r["warnings"]), "partial replay needs warnings")
            _require(math.isclose(r["return_fraction"], r["final_equity_usdt"] / r["initial_equity_usdt"] - 1,
                                  rel_tol=1e-9, abs_tol=1e-9), "return/equity units disagree")
    elif kind == "risk_limits":
        _require(r["effective_at"] <= r["created_at"] < r["expires_at"], "stale risk snapshot")
        _require(r["margin_mode"] == "cross" and r["require_verified_cross"] and r["allow_reduce"],
                 "cross verification and reductions must remain enabled")


def validate_exchange(features, prediction, model, decision_at):
    """Validate one usable research inference exchange, not order authorization."""
    for kind, record in (("features", features), ("prediction", prediction), ("model_metadata", model)):
        validate_contract(kind, record)
    _require(_number(decision_at), "invalid decision time")
    _require(features["status"] == prediction["status"] == "ok", "unavailable inference")
    _require(features["instrument_id"] == prediction["instrument_id"] in model["instrument_ids"],
             "instrument mismatch")
    for key in ("feature_set_id", "feature_version"):
        _require(features[key] == prediction[key] == model[key], "feature identity mismatch")
    _require(features["names"] == model["feature_names"] and features["units"] == ["dimensionless"] * len(features["names"])
             and features["interval_seconds"] == model["interval_seconds"], "model feature order/units mismatch")
    _require(prediction["model_id"] == model["model_id"] and prediction["artifact_sha256"] == model["artifact_sha256"],
             "artifact identity mismatch")
    _require(model["valid_from"] <= features["as_of"] == prediction["as_of"]
             <= features["available_at"] <= prediction["available_at"] <= decision_at
             < prediction["valid_until"] <= model["valid_until"], "inference unavailable or expired")
    _require(prediction["horizon_seconds"] == model["label_horizon_seconds"], "label horizon mismatch")
