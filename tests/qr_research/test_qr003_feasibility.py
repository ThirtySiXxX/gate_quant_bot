import copy
import unittest

import numpy as np
import pandas as pd

from research.qr003.feasibility_audit import (
    TERMINAL_REASON, audit_positions, feature_records, interval_clusters,
    mature_before, summarize, input_quality, audit_events, compare_paths, digest,
)


def result_fixture(terminal=False, side="long"):
    """10 units @100; reduce 4 @110 then close 6 @90; signed funding.

    Total fill fees=2, funding=+0.5-0.8=-0.3. Long net=-21.7;
    short net=18.3. Prices already include slippage; never subtract it twice.
    """
    direction = 1 if side == "long" else -1
    events = []
    for idx, (action, t, qty, before, after, price) in enumerate([
            ("open", 3600, 10, 0, 10, 100), ("reduce", 7200, 4, 10, 6, 110),
            ("close", 14400 if terminal else 10800, 6, 6, 0, 90)]):
        events.append(dict(id=idx, symbol="BTC_USDT", side=side,
            position_id="BTC_USDT:3600", action=action, time=t,
            bar_time=t-3600 if terminal and idx == 2 else t,
            quantity=qty, position_before=before, position_after=after,
            price=price, notional=qty*price, fee=(1., .4, .6)[idx],
            pnl=None if idx == 0 else ((40*direction-.8-.5) if idx == 1 else (-60*direction-1.2+.8)),
            reason=TERMINAL_REASON if terminal and idx == 2 else "policy"))
    trades = [dict(symbol="BTC_USDT", side=side, open_time=3600,
        close_time=e["bar_time"], entry_price=100, exit_price=e["price"],
        gross=(40 if i == 0 else -60)*direction, pnl=e["pnl"],
        fees=.8 if i == 0 else 1.2, funding=.5 if i == 0 else -.8,
        reason=e["reason"]) for i, e in enumerate(events[1:])]
    return dict(schema_version=3, executions=events, trades=trades,
        initial_capital=1000, final_equity=1000+sum(t["pnl"] for t in trades),
        total_fees=2, total_funding=-.3, total_slippage_cost=123)


class FeasibilityTests(unittest.TestCase):
    def test_partial_exits_and_signed_funding_count_once(self):
        for side, expected in (("long", -21.7), ("short", 18.3)):
            with self.subTest(side=side):
                rows, cash = audit_positions(result_fixture(side=side), "baseline")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["reductions"], 1)
                self.assertAlmostEqual(rows[0]["realized_net_pnl_usdt"], expected)
                self.assertAlmostEqual(rows[0]["target_net_return_fraction"], expected/1000)
                self.assertEqual(rows[0]["target_positive"], int(expected > 0))
                self.assertAlmostEqual(cash["residual_usdt"], 0)

    def test_terminal_is_censored_even_if_ledger_profitable(self):
        rows, _ = audit_positions(result_fixture(terminal=True, side="short"), "terminal")
        r = rows[0]
        self.assertTrue(r["censored"])
        self.assertIsNone(r["target_net_return_fraction"])
        self.assertIsNone(r["target_positive"])
        self.assertIsNone(r["label_end"])
        self.assertEqual(r["observation_end"], 14400)
        self.assertEqual(r["duration_hours"], 3)
        self.assertFalse(mature_before(r, 999999))

    def test_natural_exit_across_fold_boundary_is_not_artificially_closed(self):
        rows, _ = audit_positions(result_fixture(), "baseline")
        report = summarize(rows, [0, 7200, 18000])
        self.assertEqual(rows[0]["label_end"], 10800)
        self.assertEqual(report["folds"][0]["natural_labels_closed_in_fold"], 0)
        self.assertEqual(report["folds"][0]["natural_labels"], 1)
        self.assertFalse(mature_before(rows[0], 10800+86400))
        self.assertTrue(mature_before(rows[0], 10800+86401))

    def test_data_gap_censors_without_forging_zero_label(self):
        rows, _ = audit_positions(result_fixture(), "gap", [dict(symbol="BTC_USDT",
            start=7200, end=10800, reason="missing_exit_input")])
        self.assertTrue(rows[0]["censored"])
        self.assertIsNone(rows[0]["target_net_return_fraction"])
        rows, _ = audit_positions(result_fixture(), "no_gap", [dict(symbol="ETH_USDT",
            start=7200, end=10800, reason="other_asset_gap")])
        self.assertFalse(rows[0]["censored"])

    def test_rejects_ledger_corruption_duplicates_or_forged_gross(self):
        variants = []
        r = result_fixture(); r["executions"][1]["position_before"] = 9; variants.append(r)
        r = result_fixture(); r["trades"].append(copy.deepcopy(r["trades"][0])); variants.append(r)
        r = result_fixture(); r["executions"][2]["id"] = 1; variants.append(r)
        r = result_fixture(); r["final_equity"] += 1; variants.append(r)
        r = result_fixture(); r["trades"][0]["fees"] += 1; variants.append(r)
        r = result_fixture(); r["trades"][0]["funding"] = float("nan"); variants.append(r)
        r = result_fixture(); r["trades"][0]["gross"] += 1; r["trades"][0]["pnl"] += 1
        r["executions"][1]["pnl"] += 1; r["final_equity"] += 1; variants.append(r)
        r = result_fixture(terminal=True); r["executions"][-1]["time"] -= 3600; variants.append(r)
        for i, bad in enumerate(variants):
            with self.subTest(case=i), self.assertRaises(ValueError):
                audit_positions(bad, "bad")

    def test_duplicate_branches_and_cross_asset_overlap_do_not_create_independence(self):
        rows, _ = audit_positions(result_fixture(), "baseline")
        duplicate = {**rows[0], "trajectory_id": "skip_later"}
        cross_asset = {**rows[0], "symbol": "ETH_USDT", "origin_id": "ETH_USDT:3600:long"}
        report = summarize(rows+[duplicate, cross_asset])
        self.assertEqual(report["position_rows"], 3)
        self.assertEqual(report["distinct_market_origins"], 2)
        self.assertEqual(report["repeated_origin_rows"], 1)
        self.assertEqual(len(report["overlap_clusters"]), 1)
        self.assertIsNone(report["effective_independent_sample_size"])
        separate = {**rows[0], "entry_at": 2*86400, "observation_end": 3*86400}
        self.assertEqual(len(interval_clusters(rows+[separate])), 2)

    def test_closed_bar_feature_prefix_causality_and_gap_reset(self):
        n = 400
        close = 100+np.arange(n)*.1+np.sin(np.arange(n))
        frame = pd.DataFrame(dict(timestamp=np.arange(n)*3600, open=close,
            close=close, high=close+1, low=close-1, volume=np.arange(n)+100))
        times = [200*3600, 201*3600]
        original = feature_records(frame, times)
        changed = frame.copy()
        changed.loc[201:, ["open", "close", "high", "low"]] *= 2
        changed.loc[201:, "volume"] *= 100
        self.assertEqual(feature_records(changed, times), original)
        self.assertEqual(feature_records(frame.iloc[:201], times), original)
        missing = feature_records(frame.drop(index=199), times)
        self.assertEqual(missing[times[0]]["status"], "unavailable")
        self.assertEqual(missing[times[1]]["status"], "unavailable")
        self.assertEqual(original[times[0]]["available_at"], times[0])
        self.assertEqual(len(original[times[0]]["values"]), 21)
        with self.assertRaisesRegex(ValueError, "hourly"):
            feature_records(frame, [200*3600+.5])

    def test_market_quality_marks_missing_closed_bar_and_stale_funding(self):
        def candles(step):
            return pd.DataFrame(dict(timestamp=np.arange(0, 4*86400, step),
                open=100., high=101., low=99., close=100., volume=1.))
        frames = {i: candles(s) for i, s in (("1h", 3600), ("4h", 14400), ("1d", 86400))}
        frames["funding"] = pd.DataFrame(dict(timestamp=np.arange(0, 4*86400, 28800), funding_rate=.0001))
        complete = input_quality("BTC_USDT", frames, 2*86400, 3*86400)
        self.assertTrue(complete["complete_evaluation_inputs"])
        # Missing hour opened at start is first stale when it should have closed.
        frames["1h"] = frames["1h"][frames["1h"].timestamp != 2*86400]
        frames["funding"] = frames["funding"][frames["funding"].timestamp != 2*86400]
        bad = input_quality("BTC_USDT", frames, 2*86400, 3*86400)
        self.assertEqual(bad["coverage"]["1h"]["evaluated_invalid_decisions"], 1)
        self.assertEqual(bad["coverage"]["1h"]["missing_execution_open_decisions"], 1)
        self.assertEqual(bad["coverage"]["funding"]["evaluated_invalid_decisions"], 7)
        hour = next(w for w in bad["invalid_windows"] if w["reason"] == "missing_or_stale_1h")
        self.assertEqual(hour["start"], 2*86400+3600)
        self.assertEqual(hour["end"], 2*86400+7200)
        frames["4h"].loc[2, "timestamp"] = 1
        with self.assertRaisesRegex(ValueError, "timestamp grid"):
            input_quality("BTC_USDT", frames, 2*86400, 3*86400)

    def test_funding_second_offsets_are_not_rounded_into_past(self):
        frames = {i: pd.DataFrame(dict(timestamp=np.arange(0, 4*86400, s),
            open=100., high=101., low=99., close=100., volume=1.))
            for i, s in (("1h", 3600), ("4h", 14400), ("1d", 86400))}
        frames["funding"] = pd.DataFrame(dict(timestamp=np.arange(0, 4*86400, 28800)+3,
            funding_rate=.0001))
        before = frames["funding"].copy(deep=True)
        report = input_quality("ETH_USDT", frames, 2*86400, 3*86400)
        self.assertTrue(report["complete_evaluation_inputs"])
        pd.testing.assert_frame_equal(before, frames["funding"])
        self.assertEqual(report["coverage"]["funding"]["closed_or_settled_before_start"], 6)

    def test_observer_candidates_must_match_actual_fills_and_original_calls(self):
        result = result_fixture()
        events = []
        for i, execution in enumerate(result["executions"]):
            t, flat = execution["time"], i == 0
            state = dict(current_notional=0 if flat else execution["position_before"]*execution["price"])
            events.append(dict(schema_version=1, trajectory_id="baseline", symbol="BTC_USDT",
                decision_at=t, decision_price=execution["price"],
                signal_available=True, signal={"timing_feature": {"bar_ts": t-3600}},
                position_before={"size": execution["position_before"]}, state_before=state,
                state_id=digest({"observed": state, "position_before": {"size": execution["position_before"]}}),
                plan=dict(model_target=1000 if flat else 0, rebalance=True, allow_increase=True),
                pre_ml_entry_proposal=flat, order_check={"budget_checked": flat},
                post_budget_eligibility={"status": "eligible" if flat else "not_applicable", "reason": "held"},
                skip_applied=False))
        frame = pd.DataFrame(dict(timestamp=[0, 3600, 7200, 10800], open=[100,100,110,90],
            high=[101,101,111,91], low=[99,99,109,89], close=[100,100,110,90], volume=1))
        payload = dict(events=events, result=result, trajectory_id="baseline", skip_applied=False,
            skip_entry_at=None, call_counts=dict(signal_at=3, decide_execution=3, build_order_plan=3))
        report = audit_events(payload, frame)
        self.assertEqual(report["counts"]["executable"], 1)
        self.assertEqual(report["counts"]["held"], 2)
        self.assertEqual(report["unlabelled_executable_candidates"], 0)
        bad = copy.deepcopy(payload); bad["events"][0]["post_budget_eligibility"]["status"] = "rejected"
        with self.assertRaisesRegex(ValueError, "ledger open"):
            audit_events(bad, frame)
        bad = copy.deepcopy(payload); bad["call_counts"]["signal_at"] = 4
        with self.assertRaisesRegex(ValueError, "call count"):
            audit_events(bad, frame)
        bad = copy.deepcopy(payload); bad["events"][0]["state_id"] = digest(bad["events"][0]["state_before"])
        with self.assertRaisesRegex(ValueError, "state identity"):
            audit_events(bad, frame)
        bad = copy.deepcopy(payload); bad["events"][0]["signal"]["timing_feature"]["bar_ts"] = 3600
        with self.assertRaisesRegex(ValueError, "unclosed"):
            audit_events(bad, frame)

    def test_branch_new_candidate_is_linked_without_counting_as_independent(self):
        a = dict(decision_at=3600, state_id="same", flat=True, pre_ml_proposed=True, eligible=True, executed=True)
        b = dict(decision_at=7200, state_id="held", flat=False, pre_ml_proposed=False, eligible=False, executed=False)
        baseline = dict(records=[a,b])
        branch = dict(records=[{**a, "executed": False}, {**b, "state_id": "flat", "flat": True,
            "pre_ml_proposed": True, "eligible": True, "executed": True, "proposed_side": "long"}])
        result = compare_paths(baseline, branch, 3600)
        self.assertEqual(result["first_state_divergence"], 7200)
        self.assertEqual(result["first_qualification_divergence"], 7200)
        self.assertTrue(result["new_branch_candidates"][0]["baseline_held"])
        branch["records"][0]["state_id"] = "leaked"
        with self.assertRaisesRegex(ValueError, "before intervention"):
            compare_paths(baseline, branch, 3600)


if __name__ == "__main__":
    unittest.main()
