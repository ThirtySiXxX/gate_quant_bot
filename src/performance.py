"""Geometrically linked equity returns, without deposits/withdrawals.

Position sizing already uses marked account equity. Never compound individual
trade returns: concurrent positions and partial closes make that incorrect.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone


def compounded_performance(initial_equity, equity_curve):
    initial = float(initial_equity)
    if not math.isfinite(initial) or initial <= 0:
        raise ValueError("初始权益必须为正的有限数")
    points = sorted(equity_curve, key=lambda p: p["t"])
    previous = initial
    months = {}
    broken = False
    for p in points:
        t, equity = float(p["t"]), float(p["e"])
        if not math.isfinite(t) or not math.isfinite(equity):
            raise ValueError("权益曲线包含无效数值")
        key = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")
        month = months.setdefault(key, {"month": key, "start_equity": previous,
                                       "end_equity": equity, "observations": 0})
        month["end_equity"] = equity
        month["observations"] += 1
        broken = broken or previous <= 0 or equity <= 0
        previous = equity
    final = previous
    # Negative equity reports actual loss, but geometrical annualization is undefined.
    ratio = final / initial
    days = (points[-1]["t"] - points[0]["t"]) / 86400 if len(points) > 1 else 0
    def equivalent(period):
        if broken or days <= 0:
            return None
        exponent = math.log(ratio) * period / days
        return math.expm1(exponent) * 100 if exponent < 700 else None
    monthly = []
    for m in months.values():
        m["return_pct"] = (m["end_equity"] / m["start_equity"] - 1) * 100 if m["start_equity"] > 0 else None
        monthly.append(m)
    return {"method": "equity_geometric", "compounded_return_pct": (ratio-1)*100,
            "equivalent_30d_return_pct": equivalent(30), "cagr_pct": equivalent(365),
            "calendar_months": monthly, "geometric_valid": not broken,
            "note": "按账户净权益连乘；无出入金。自然月使用UTC，首尾月可不完整；30天等效收益不是实际月收益或预测。"}
