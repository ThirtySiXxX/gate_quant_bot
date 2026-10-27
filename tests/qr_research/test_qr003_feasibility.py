import copy
import unittest

import numpy as np
import pandas as pd

from research.qr003.feasibility_audit import (
    TERMINAL_REASON, audit_positions, feature_records, interval_clusters,
    mature_before, summarize,
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


if __name__ == "__main__":
    unittest.main()
