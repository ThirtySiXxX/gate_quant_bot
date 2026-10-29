"""Offline boundary examples and rejection tests; no config, DB or exchange I/O."""
import copy
import json
import unittest

from src.contracts import SCHEMAS, validate_contract, validate_exchange
from src.crypto_ml import FEATURE_NAMES, FEATURE_VERSION
from src.backtest import PortfolioBacktestResult


T = 1_700_000_000
H = "a" * 64
I = "gate:usdt:ETH_USDT"
J = "gate:usdt:BTC_USDT"


def examples():
    def record(kind, **fields):
        return dict(kind=kind, schema_version=1, created_at=T, **fields)
    risk = record("risk_limits", risk_limits_id="risk-1", effective_at=T, expires_at=T+86400,
        margin_mode="cross", require_verified_cross=True, max_gross_notional_to_equity=4.,
        max_instrument_notional_to_equity=1., max_order_notional_usdt=1000., max_leverage=20.,
        daily_loss_limit_enabled=False, daily_loss_limit_fraction=.08, allow_increase=False, allow_reduce=True)
    config = record("strategy_config", strategy_id="trend-carry", config_id="config-1", mode="paper",
        instrument_ids=[I], effective_at=T, parameters={"short_trend_interval": "1h"},
        position_sizing_mode="volatility", model_id="", risk_limits_id="risk-1", config_sha256=H)
    return {
        "market_data": record("market_data", instrument_id=I, interval_seconds=3600,
            bar_open_ts=T-3600, bar_close_ts=T, available_at=T, open=100., high=110., low=90.,
            close=105., volume=10., volume_unit="contracts", quanto_multiplier=.01,
            source="synthetic-test", data_sha256=H,
            funding=dict(settlement_at=T-1, available_at=T, rate=.0001, interval_seconds=28800)),
        "features": record("features", instrument_id=I, interval_seconds=3600,
            bar_open_ts=T-3600, as_of=T, available_at=T, max_source_available_at=T,
            feature_set_id="crypto-hourly", feature_version=FEATURE_VERSION,
            names=list(FEATURE_NAMES), units=["dimensionless"]*len(FEATURE_NAMES),
            values=[0.]*len(FEATURE_NAMES), status="ok", reason=""),
        "prediction": record("prediction", instrument_id=I, model_id="model-1", artifact_sha256=H,
            feature_set_id="crypto-hourly", feature_version=FEATURE_VERSION, as_of=T,
            available_at=T, valid_until=T+3600, horizon_seconds=14400,
            probabilities=dict(short=.2, neutral=.3, long=.5), status="ok", reason=""),
        "signal": record("signal", instrument_id=I, strategy_id="trend-carry", config_sha256=H,
            risk_limits_id="risk-1", decision_at=T, sources_available_at=T, expires_at=T+3600,
            action="target", target_notional_usdt=-100., reason="synthetic short target"),
        "model_metadata": record("model_metadata", model_id="model-1", artifact_sha256=H,
            bundle_schema_version=1, model_kind="logistic", instrument_ids=[I], interval_seconds=3600,
            feature_set_id="crypto-hourly", feature_version=FEATURE_VERSION,
            feature_names=list(FEATURE_NAMES), classes=[-1,0,1], trained_until=T-86401,
            valid_from=T, valid_until=T+86400, embargo_seconds=86400, label_horizon_seconds=14400,
            label_entry="next_bar_open", round_trip_cost_fraction=.0014, edge_fraction=.001,
            data_sha256=H, code_revision="b"*40, package_versions={"sklearn": "test-fixture"}, seed=17,
            validation={"protocol": "synthetic fixture, not trained"}, activation="research"),
        "strategy_config": config,
        "backtest_request": record("backtest_request", request_id="request-1", instrument_ids=[I],
            start_ts=T-86400, end_ts=T, data_sha256=H, config_sha256=H, code_revision="b"*40,
            initial_equity_usdt=1000., strategy_config=config, risk_limits=risk,
            costs=dict(taker_fee_fraction=.0005, slippage_bps=2., funding_policy="settled_history"),
            completeness_policy="strict"),
        "backtest_result": record("backtest_result", request_id="request-1",
            requested_instrument_ids=[I], accepted_instrument_ids=[I], start_ts=T-86400, end_ts=T,
            data_sha256=H, config_sha256=H, code_revision="b"*40, initial_equity_usdt=1000.,
            final_equity_usdt=900., return_fraction=-.1, max_drawdown_fraction=.1, fees_usdt=1.,
            funding_paid_usdt=-.2, completed_positions=1, execution_count=3, warnings=[],
            completeness_policy="strict", legacy_result_schema_version=3),
        "risk_limits": risk,
    }


class SharedContractTests(unittest.TestCase):
    def setUp(self):
        self.records = examples()

    def reject(self, kind, **changes):
        payload = copy.deepcopy(self.records[kind])
        payload.update(changes)
        with self.assertRaises(ValueError):
            validate_contract(kind, payload)

    def test_all_nine_kinds_round_trip_without_mutation(self):
        self.assertEqual(set(self.records), set(SCHEMAS))
        before = copy.deepcopy(self.records)
        for kind, payload in self.records.items():
            with self.subTest(kind=kind):
                validate_contract(kind, json.loads(json.dumps(payload, allow_nan=False)))
        self.assertEqual(self.records, before)

    def test_strict_version_and_field_negotiation(self):
        for kind in SCHEMAS:
            with self.subTest(kind=kind):
                self.reject(kind, schema_version=2)
                self.reject(kind, schema_version=True)
                self.reject(kind, future_field="uncoordinated addition")
                payload = dict(self.records[kind])
                del payload["created_at"]
                with self.assertRaises(ValueError):
                    validate_contract(kind, payload)

    def test_explicit_scope_seconds_and_finite_json(self):
        self.reject("market_data", instrument_id="ETH_USDT")
        self.reject("market_data", instrument_id="gate:usdt:../ETH_USDT")
        self.reject("market_data", available_at=T*1000)
        self.reject("market_data", close=float("nan"))
        self.reject("strategy_config", parameters={"nested": [float("inf")]})
        self.reject("market_data", volume=True)
        self.reject("market_data", volume_unit="unknown")

    def test_unclosed_bars_ohlc_and_future_settled_funding(self):
        self.reject("market_data", bar_close_ts=T+1)
        self.reject("market_data", high=99.)
        self.reject("market_data", volume=-1.)
        self.reject("market_data", funding=dict(settlement_at=T+1, available_at=T+1,
                                                rate=.001, interval_seconds=28800))

    def test_features_require_available_sources_ordered_values_and_units(self):
        self.reject("features", max_source_available_at=T+1)
        self.reject("features", as_of=T-1)
        self.reject("features", values=[0.])
        self.reject("features", units=["dimensionless"])
        self.reject("features", names=["duplicate", "duplicate"])
        self.reject("features", values=None)

    def test_unavailable_features_and_predictions_are_explicit(self):
        for kind, field in (("features", "values"), ("prediction", "probabilities")):
            payload = dict(self.records[kind], status="unavailable", reason="missing source", **{field: None})
            validate_contract(kind, payload)
            self.reject(kind, status="unavailable", reason="", **{field: None})

    def test_probabilities_are_three_class_fractions_with_exclusive_expiry(self):
        self.reject("prediction", probabilities=dict(short=.2, neutral=.3, long=.6))
        self.reject("prediction", probabilities=dict(short=-.1, neutral=.5, long=.6))
        self.reject("prediction", probabilities=dict(short=.2, long=.8))
        self.reject("prediction", valid_until=T)

    def test_model_provenance_class_order_and_embargo(self):
        self.reject("model_metadata", artifact_sha256="unhashed")
        self.reject("model_metadata", classes=[1,0,-1])
        self.reject("model_metadata", classes=[-1,False,1])
        self.reject("model_metadata", trained_until=T)
        self.reject("model_metadata", trained_until=T-86399)
        self.reject("model_metadata", valid_until=T)
        self.reject("model_metadata", label_entry="same_bar_close")

    def test_inference_cross_record_identity_order_and_time(self):
        f, p, m = (self.records[k] for k in ("features", "prediction", "model_metadata"))
        validate_exchange(f, p, m, T)
        changes = [("prediction", "instrument_id", J), ("prediction", "artifact_sha256", "c"*64),
                   ("prediction", "model_id", "other"), ("prediction", "feature_version", 2),
                   ("model_metadata", "feature_names", list(reversed(FEATURE_NAMES))),
                   ("prediction", "horizon_seconds", 7200)]
        for kind, field, value in changes:
            with self.subTest(kind=kind, field=field):
                records = copy.deepcopy(self.records)
                records[kind][field] = value
                with self.assertRaises(ValueError):
                    validate_exchange(records["features"], records["prediction"], records["model_metadata"], T)
        for decision_at in (T-1, T+3600):
            with self.assertRaises(ValueError):
                validate_exchange(f, p, m, decision_at)

    def test_signal_is_signed_usdt_and_exit_cannot_increase_exposure(self):
        self.reject("signal", action="exit", target_notional_usdt=100.)
        self.reject("signal", decision_at=T-1)
        self.reject("signal", expires_at=T)
        validate_contract("signal", dict(self.records["signal"], action="exit", target_notional_usdt=0.))

    def test_risk_blocks_increases_without_blocking_reductions(self):
        validate_contract("risk_limits", self.records["risk_limits"])
        self.reject("risk_limits", allow_reduce=False)
        self.reject("risk_limits", margin_mode="isolated")
        self.reject("risk_limits", require_verified_cross=False)
        self.reject("risk_limits", expires_at=T)
        self.reject("risk_limits", daily_loss_limit_fraction=8.)
        self.reject("strategy_config", mode="live")

    def test_requests_bind_config_risk_and_cost_snapshots(self):
        self.reject("backtest_request", end_ts=T-86400)
        self.reject("backtest_request", instrument_ids=[J])
        self.reject("backtest_request", config_sha256="c"*64)
        self.reject("backtest_request", costs=dict(taker_fee_fraction=5., slippage_bps=2., funding_policy="history"))

    def test_strict_coverage_and_warned_replay_are_distinct(self):
        self.reject("backtest_result", requested_instrument_ids=[I,J])
        self.reject("backtest_result", accepted_instrument_ids=[I,J])
        self.reject("backtest_result", requested_instrument_ids=[I,J], completeness_policy="replay_with_warnings")
        validate_contract("backtest_result", dict(self.records["backtest_result"],
            requested_instrument_ids=[I,J], completeness_policy="replay_with_warnings", warnings=["BTC missing"]))

    def test_result_percent_conversion_and_legacy_version_are_separate(self):
        self.reject("backtest_result", return_fraction=-10.)
        self.reject("backtest_result", fees_usdt=-1.)
        # Minimal adapter check against the actual existing result serializer.
        legacy = PortfolioBacktestResult(initial_capital=1000., final_equity=900., return_pct=-10.,
                                         max_drawdown_pct=10.).to_dict()
        payload = dict(self.records["backtest_result"], return_fraction=legacy["return_pct"]/100,
                       max_drawdown_fraction=legacy["max_drawdown_pct"]/100,
                       legacy_result_schema_version=legacy["schema_version"])
        validate_contract("backtest_result", payload)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["legacy_result_schema_version"], 3)


if __name__ == "__main__":
    unittest.main()
