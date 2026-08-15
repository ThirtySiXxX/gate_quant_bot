"""
组合级回测引擎——对配置的整个标的池同时逐周期走查，直接复用生产环境的
vol.py / trend.py / carry.py / portfolio.py / systematic_engine.plan_orders
(和实盘/模拟盘用的是同一套函数)，不是另外写的简化近似版。

关键性能/正确性设计：趋势/Carry/波动率/协方差这些信号只在各自的K线周期
(1H短趋势 / 4H主趋势 / 1D regime / 协方差周期)边界更新，两根边界K线之间信号
完全不变。所以回测按"短趋势周期"(默认1H)这个最细粒度走查，得到的调仓决策
和实盘每15分钟复核一次是完全等价的（15分钟只是实盘的"复核频率"，不代表
信号真的每15分钟都会变），但快得多，几年的多标的历史也能在合理时间内跑完。

协方差矩阵同理：用 vol.ewma_covariance_series 一次性算出"逐协方差周期K线"的
协方差矩阵快照序列(O(bars))，回测时对每个时间点做 asof 二分查找定位到对应快照，
而不是每一步都重新对截至当时的全部历史重算一遍(那样是 O(bars^2)，会很慢)。
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from . import carry as carry_mod
from . import costs
from . import data_fetcher
from . import portfolio as pf
from . import trend as trend_mod
from . import vol as vol_mod
from .config import CostConfig, SystematicConfig
from .systematic_engine import plan_orders

ProgressCB = Optional[Callable[[int, str], None]]


@dataclass
class SymbolBacktestInputs:
    symbol: str
    df_short: pd.DataFrame        # 短趋势周期K线(默认1H)
    df_main: pd.DataFrame         # 主趋势周期K线(默认4H)
    df_regime: pd.DataFrame       # regime周期K线(默认1D)
    df_cov: pd.DataFrame          # 协方差周期K线(默认4H，可以和df_main是同一份)
    funding_rate: float            # 当前实时费率，仅在拿不到历史费率时作为降级回退用
    funding_interval_sec: float
    quanto_multiplier: float
    taker_fee_rate: float
    order_size_min: int = 1
    # 真实历史资金费率 DataFrame(columns=[timestamp, funding_rate])，
    # 来自 data_fetcher.fetch_funding_history()；为空则回退到常数 funding_rate 近似
    funding_history: Optional[pd.DataFrame] = None
    # 指标可以使用此前的预热数据，但交易和绩效统计只能从该时间开始。
    test_start_ts: Optional[float] = None


@dataclass
class PortfolioBacktestResult:
    symbols: List[str] = field(default_factory=list)
    start_ts: float = 0.0
    end_ts: float = 0.0
    initial_capital: float = 0.0
    final_equity: float = 0.0
    return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    annualized_vol_pct: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar: float = 0.0
    turnover_annualized: float = 0.0
    trade_count: int = 0
    # ---- 成本与仓位诊断(把之前只能靠反推的数字直接摆出来) ----
    gross_pnl_before_costs: float = 0.0   # 完全不扣任何成本的毛利
    total_fees: float = 0.0               # 手续费合计
    total_slippage_cost: float = 0.0      # 滑点合计(这项不在"手续费"里，藏在成交价里)
    total_funding: float = 0.0            # 资金费合计(正=支出)
    total_traded_notional: float = 0.0    # 总成交名义额
    avg_trade_notional: float = 0.0       # 平均每笔成交名义额 -> "一次开多少"
    avg_gross_leverage: float = 0.0       # 平均总杠杆(持仓名义额/权益)
    max_gross_leverage: float = 0.0       # 峰值总杠杆
    effective_taker_rate: float = 0.0     # 本次回测实际使用的吃单费率
    avg_adaptive_risk_multiplier: float = 1.0
    min_adaptive_risk_multiplier: float = 1.0
    adaptive_risk_active_pct: float = 0.0  # 乘数<0.999的有效信号样本占比
    trades: List[dict] = field(default_factory=list)
    equity_curve: List[dict] = field(default_factory=list)
    per_symbol: Dict[str, dict] = field(default_factory=dict)
    bar_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "symbols": self.symbols, "start_ts": self.start_ts, "end_ts": self.end_ts,
            "initial_capital": self.initial_capital, "final_equity": self.final_equity,
            "return_pct": self.return_pct, "annualized_return_pct": self.annualized_return_pct,
            "annualized_vol_pct": self.annualized_vol_pct, "sharpe": self.sharpe,
            "sortino": self.sortino, "max_drawdown_pct": self.max_drawdown_pct,
            "calmar": self.calmar, "turnover_annualized": self.turnover_annualized,
            "trade_count": self.trade_count,
            "gross_pnl_before_costs": self.gross_pnl_before_costs,
            "total_fees": self.total_fees, "total_slippage_cost": self.total_slippage_cost,
            "total_funding": self.total_funding,
            "total_traded_notional": self.total_traded_notional,
            "avg_trade_notional": self.avg_trade_notional,
            "avg_gross_leverage": self.avg_gross_leverage,
            "max_gross_leverage": self.max_gross_leverage,
            "effective_taker_rate": self.effective_taker_rate,
            "avg_adaptive_risk_multiplier": self.avg_adaptive_risk_multiplier,
            "min_adaptive_risk_multiplier": self.min_adaptive_risk_multiplier,
            "adaptive_risk_active_pct": self.adaptive_risk_active_pct,
            "trades": self.trades,
            "equity_curve": self.equity_curve, "per_symbol": self.per_symbol,
            "bar_counts": self.bar_counts, "warnings": self.warnings,
        }


def _prep(sb: SymbolBacktestInputs, cfg: SystematicConfig) -> dict:
    df_short = sb.df_short.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df_main = sb.df_main.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df_regime = sb.df_regime.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df_cov = sb.df_cov.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)

    short_f = trend_mod.group_trend_forecast(df_short["close"], cfg.short_trend_interval, cfg)
    main_f = trend_mod.group_trend_forecast(df_main["close"], cfg.main_trend_interval, cfg)
    if len(df_regime) >= cfg.regime_ema_long + 5:
        regime_s = trend_mod.daily_regime_series(df_regime, cfg)
    else:
        regime_s = pd.Series(["range"] * len(df_regime), index=df_regime.index)
    # carry 优先用真实的逐期历史资金费率(严格因果对齐到K线时间轴)；
    # 拿不到历史时才退回"当前实时费率当常数"的近似
    carry_f = carry_mod.carry_forecast_series_from_history(
        df_main["close"], cfg.main_trend_interval, sb.funding_history,
        sb.funding_interval_sec, cfg,
        bar_timestamps=df_main["timestamp"].values,
        fallback_funding_rate=sb.funding_rate,
    )
    used_funding_history = sb.funding_history is not None and len(sb.funding_history) > 0
    funding_history_complete = bool(
        used_funding_history
        and len(df_main) > 0
        and float(sb.funding_history["timestamp"].min()) <= float(df_main["timestamp"].iloc[0])
    )
    vol_ann = vol_mod.price_vol_annualized(df_main["close"], cfg.main_trend_interval, lam=cfg.ewma_lambda)
    adaptive = vol_mod.adaptive_chop_risk_from_config(df_short, cfg)
    returns_cov = vol_mod.log_returns(df_cov["close"])
    returns_cov.index = df_cov["timestamp"].values


    return {
        "symbol": sb.symbol,
        "short_ts": df_short["timestamp"].tolist(), "short_open": df_short["open"].values,
        "short_close": df_short["close"].values,
        "main_ts": df_main["timestamp"].tolist(), "main_f": main_f.values, "short_f": short_f.values,
        "regime_ts": df_regime["timestamp"].tolist(), "regime": regime_s.values,
        "carry_f": carry_f.values, "vol_ann": vol_ann.values,
        "adaptive_risk_multiplier": adaptive["risk_multiplier"].values,
        "adaptive_efficiency_ratio": adaptive["efficiency_ratio"].values,
        "adaptive_vol_ratio": adaptive["vol_ratio"].values,
        "returns_cov": returns_cov,
        "quanto_multiplier": sb.quanto_multiplier, "taker_fee_rate": sb.taker_fee_rate,
        "funding_rate": sb.funding_rate, "funding_interval_sec": sb.funding_interval_sec,
        "funding_history": sb.funding_history, "used_funding_history": used_funding_history,
        "funding_history_complete": funding_history_complete,
        "test_start_ts": sb.test_start_ts,
        # 供资金费"实际成本"计提时按时间asof查找当期真实费率(不是只用一个常数)
        "funding_ts": (sb.funding_history["timestamp"].tolist() if used_funding_history else []),
        "funding_rates": (sb.funding_history["funding_rate"].values if used_funding_history else None),
        "order_size_min": max(1, int(sb.order_size_min or 1)),
        "bar_counts": {"short": len(df_short), "main": len(df_main),
                        "regime": len(df_regime), "cov": len(df_cov)},
    }


def _asof(ts_list: List[float], t: float) -> int:
    return bisect.bisect_right(ts_list, t) - 1


def _funding_rate_at(d: dict, t: float) -> float:
    """取 t 时刻实际生效的资金费率(因果asof查找)；没有历史数据时回退到常数费率。"""
    ts_list = d.get("funding_ts") or []
    rates = d.get("funding_rates")
    if not ts_list or rates is None:
        return d["funding_rate"]
    i = _asof(ts_list, t)
    if i < 0:
        return d["funding_rate"]
    return float(rates[i])


def _mark_to_market_equity(realized_equity: float, positions: Dict[str, dict],
                           prices: Dict[str, float], prepared: Dict[str, dict]) -> float:
    """现金/已实现权益 + 持仓浮盈亏 - 尚未结算进现金的开仓费和资金费。"""
    mtm = float(realized_equity)
    for symbol, pos in positions.items():
        price = prices.get(symbol)
        if price is None:
            continue
        direction = 1 if pos["side"] == "long" else -1
        qm = prepared[symbol]["quanto_multiplier"]
        mtm += (price - pos["entry_price"]) * pos["size"] * qm * direction
        mtm -= pos.get("fees_accum", 0.0)
        mtm -= pos.get("funding_accum", 0.0)
    return mtm


def _performance_stats(equity_curve: List[dict], initial_capital: float) -> dict:
    if len(equity_curve) < 2:
        return {"annualized_return_pct": 0.0, "annualized_vol_pct": 0.0, "sharpe": 0.0,
                "sortino": 0.0, "max_drawdown_pct": 0.0, "calmar": 0.0}

    df = pd.DataFrame(equity_curve)
    df["dt"] = pd.to_datetime(df["t"], unit="s")
    daily = df.set_index("dt")["e"].resample("1D").last().ffill().dropna()
    daily_ret = daily.pct_change().dropna()

    total_days = max((df["t"].iloc[-1] - df["t"].iloc[0]) / 86400.0, 1.0)
    years = total_days / 365.0
    final_e, start_e = df["e"].iloc[-1], df["e"].iloc[0]
    if start_e > 0 and years > 0:
        cagr = (final_e / start_e) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    ann_vol = float(daily_ret.std() * np.sqrt(365)) if len(daily_ret) > 1 else 0.0
    mean_daily = float(daily_ret.mean()) if len(daily_ret) > 0 else 0.0
    sharpe = (mean_daily * 365) / ann_vol if ann_vol > 1e-9 else 0.0

    downside = daily_ret[daily_ret < 0]
    downside_vol = float(downside.std() * np.sqrt(365)) if len(downside) > 1 else 0.0
    sortino = (mean_daily * 365) / downside_vol if downside_vol > 1e-9 else 0.0

    peak = df["e"].iloc[0]
    max_dd = 0.0
    for e in df["e"]:
        peak = max(peak, e)
        if peak > 0:
            max_dd = max(max_dd, (peak - e) / peak * 100.0)

    calmar = (cagr * 100.0 / max_dd) if max_dd > 1e-9 else 0.0

    return {
        "annualized_return_pct": cagr * 100.0, "annualized_vol_pct": ann_vol * 100.0,
        "sharpe": sharpe, "sortino": sortino, "max_drawdown_pct": max_dd, "calmar": calmar,
    }


def run_portfolio_backtest(
    symbol_inputs: List[SymbolBacktestInputs],
    sys_cfg: SystematicConfig,
    cost_cfg: CostConfig,
    initial_capital: float,
    progress_cb: ProgressCB = None,
) -> PortfolioBacktestResult:
    warnings: List[str] = []
    prepared: Dict[str, dict] = {}
    for sb in symbol_inputs:
        try:
            p = _prep(sb, sys_cfg)
        except Exception as e:
            warnings.append(f"{sb.symbol} 数据准备失败，已跳过该标的: {e}")
            continue
        if p["bar_counts"]["short"] < sys_cfg.min_bars_short or p["bar_counts"]["main"] < sys_cfg.min_bars_main:
            warnings.append(
                f"{sb.symbol} 历史数据不足(短趋势{p['bar_counts']['short']}根/主趋势{p['bar_counts']['main']}根)，"
                "已跳过该标的（可能是新上线合约，或者历史数据下载范围不够）"
            )
            continue
        if not p["used_funding_history"]:
            warnings.append(
                f"{sb.symbol} 没有拿到历史资金费率，carry信号和资金费成本都退回用"
                f"当前实时费率({sb.funding_rate:.6f})当常数近似——这段回测里 carry 的贡献"
                "会失真(真实费率会随行情反号)，结果仅供参考"
            )
        elif not p["funding_history_complete"]:
            first_funding = float(sb.funding_history["timestamp"].min())
            warnings.append(
                f"{sb.symbol} 历史资金费率只覆盖到 {pd.to_datetime(first_funding, unit='s')} 之后，"
                "早于该时刻的carry预热和资金费成本不完整；交易所公开接口最多返回最近约180天，"
                "本次长区间结果必须结合此限制解读"
            )
        prepared[sb.symbol] = p

    if not prepared:
        return PortfolioBacktestResult(warnings=warnings or ["没有任何标的成功准备好可用数据，无法回测"])

    symbols = list(prepared.keys())

    # ---- 组合协方差：逐协方差周期K线的快照序列(一次遍历，O(bars)) ----
    combined_returns = pd.DataFrame({s: prepared[s]["returns_cov"] for s in symbols})
    cov_min_periods = min(30, max(5, len(combined_returns) // 4))
    cov_ts, cov_mats_raw, cov_cols = vol_mod.ewma_covariance_series(
        combined_returns, lam=sys_cfg.ewma_lambda, min_periods=cov_min_periods)
    bars_per_year_cov = vol_mod.BARS_PER_YEAR.get(sys_cfg.covariance_interval, 365)
    cov_mats = [m * bars_per_year_cov for m in cov_mats_raw]

    def cov_asof(t: float) -> Optional[pd.DataFrame]:
        idx = _asof(cov_ts, t)
        if idx < 0:
            return None
        return pd.DataFrame(cov_mats[idx], index=cov_cols, columns=cov_cols)

    # ---- 主时间轴：所有标的"短趋势"K线时间戳的并集 ----
    all_ts_set = set()
    for s in symbols:
        all_ts_set.update(prepared[s]["short_ts"])
    all_ts = sorted(all_ts_set)
    requested_starts = [prepared[s].get("test_start_ts") for s in symbols
                        if prepared[s].get("test_start_ts") is not None]
    if requested_starts:
        test_start = max(float(x) for x in requested_starts)
        all_ts = [t for t in all_ts if t >= test_start]
    total_steps = len(all_ts)
    if total_steps == 0:
        return PortfolioBacktestResult(symbols=symbols, warnings=warnings + ["主时间轴为空，无法回测"])

    equity = initial_capital
    positions: Dict[str, dict] = {}
    trades: List[dict] = []
    equity_curve: List[dict] = []
    total_traded_notional = 0.0
    total_slippage_cost = 0.0
    lev_samples: List[float] = []
    adaptive_mult_samples: List[float] = []
    last_pct = -1

    for step, t in enumerate(all_ts):
        if progress_cb and total_steps:
            pct = int(step / total_steps * 100)
            if pct != last_pct and pct % 2 == 0:
                progress_cb(pct, f"组合回测中 {step}/{total_steps} 步（{len(symbols)}个标的）")
                last_pct = pct

        signals: Dict[str, pf.InstrumentSignal] = {}
        price_now: Dict[str, float] = {}       # 本根短周期K线开盘价：模拟真实可成交时点
        mark_price_now: Dict[str, float] = {}  # 本根收盘价：用于逐bar MTM权益

        for s in symbols:
            d = prepared[s]
            exec_i = _asof(d["short_ts"], t)
            if exec_i < 0:
                continue
            price_now[s] = float(d["short_open"][exec_i])
            mark_price_now[s] = float(d["short_close"][exec_i])

            # Gate K线时间戳是该根K线的起点。t时刻只能使用 t-周期 及更早、已经完整收盘的K线，
            # 然后在t这根K线的开盘成交；不能用本根close算信号后又按同一个close成交。
            short_cutoff = t - data_fetcher.INTERVAL_SECONDS.get(sys_cfg.short_trend_interval, 3600)
            main_cutoff = t - data_fetcher.INTERVAL_SECONDS.get(sys_cfg.main_trend_interval, 14400)
            regime_cutoff = t - data_fetcher.INTERVAL_SECONDS.get(sys_cfg.regime_interval, 86400)
            si = _asof(d["short_ts"], short_cutoff)
            mi = _asof(d["main_ts"], main_cutoff)
            if si < 0 or mi < 0:
                continue
            short_val, main_val = d["short_f"][si], d["main_f"][mi]
            if np.isnan(short_val) or np.isnan(main_val):
                continue
            combined_trend = trend_mod.combine_trend(float(short_val), float(main_val), sys_cfg)
            ri = _asof(d["regime_ts"], regime_cutoff)
            regime = d["regime"][ri] if ri >= 0 else "range"
            gated_trend = trend_mod.apply_regime_gate(combined_trend, regime, sys_cfg)
            carry_val = d["carry_f"][mi]
            carry_val = 0.0 if np.isnan(carry_val) else float(carry_val)
            combined = pf.combine_forecast(gated_trend, carry_val, sys_cfg)
            vol_ann = d["vol_ann"][mi]
            if np.isnan(vol_ann) or vol_ann <= 0:
                continue
            risk_multiplier = float(d["adaptive_risk_multiplier"][si])
            efficiency_ratio = float(d["adaptive_efficiency_ratio"][si])
            range_vol_ratio = float(d["adaptive_vol_ratio"][si])
            if not np.isfinite(risk_multiplier):
                risk_multiplier = 1.0
            if not np.isfinite(efficiency_ratio):
                efficiency_ratio = 1.0
            if not np.isfinite(range_vol_ratio):
                range_vol_ratio = 1.0
            signals[s] = pf.InstrumentSignal(
                symbol=s, trend_forecast=gated_trend, carry_forecast=carry_val,
                combined_forecast=combined, vol_annual=float(vol_ann),
                risk_multiplier=risk_multiplier, efficiency_ratio=efficiency_ratio,
                range_vol_ratio=range_vol_ratio,
            )
            adaptive_mult_samples.append(risk_multiplier)

        # ---- 逐仓 mark-to-market + 资金费累计(即使这一步没有新信号，已有仓位也要照常计提) ----
        for s, pos in positions.items():
            price = price_now.get(s)
            if price is None:
                continue
            d = prepared[s]
            elapsed = t - pos["last_ts"]
            pos["last_ts"] = t
            if elapsed > 0 and d["funding_interval_sec"] > 0:
                notional = pos["size"] * price * d["quanto_multiplier"]
                events = elapsed / d["funding_interval_sec"]
                # 用该时刻真实生效的历史费率计提，而不是全程一个常数
                rate_now = _funding_rate_at(d, t)
                pos["funding_accum"] += costs.funding_fee(notional, rate_now, pos["side"]) * events

        portfolio_equity = _mark_to_market_equity(equity, positions, price_now, prepared)

        if not signals:
            curve_equity = _mark_to_market_equity(equity, positions, mark_price_now, prepared)
            equity_curve.append({"t": float(t), "e": curve_equity})
            continue

        cov_cutoff = t - data_fetcher.INTERVAL_SECONDS.get(sys_cfg.covariance_interval, 14400)
        cov_df = cov_asof(cov_cutoff)
        if cov_df is None:
            curve_equity = _mark_to_market_equity(equity, positions, mark_price_now, prepared)
            equity_curve.append({"t": float(t), "e": curve_equity})
            continue

        alloc = pf.allocate_portfolio(signals, portfolio_equity, cov_df, sys_cfg)

        for s, target in alloc.targets.items():
            d = prepared[s]
            price = price_now[s]
            pos = positions.get(s)
            current_side = pos["side"] if pos else None
            current_size = pos["size"] if pos else 0
            direction = 1 if current_side == "long" else (-1 if current_side == "short" else 0)
            current_notional = current_size * price * d["quanto_multiplier"] * direction

            # ⚠️ 反向执行模式：预测/波动率目标/组合风险分配/约束照常按 target 计算，
            # 只在这里把最终要执行的名义仓位方向对调，回测和实盘用完全一样的转换逻辑，
            # 这样才能先用回测验证"反向执行"到底是不是真的有效，再决定要不要用到实盘。
            exec_target_notional = -target.target_notional if sys_cfg.invert_direction else target.target_notional

            if not pf.should_rebalance(current_notional, exec_target_notional, portfolio_equity,
                                        signals[s].vol_annual, sys_cfg,
                                        risk_multiplier=target.risk_multiplier):
                continue

            actions = plan_orders(current_side, current_size, exec_target_notional, price,
                                   d["quanto_multiplier"], d["order_size_min"])
            for action, side, qty in actions:
                if qty <= 0:
                    continue
                is_entry = action == "open"
                fill_price = costs.slippage_adjusted_price(price, side, cost_cfg.slippage_bps, is_entry)
                notional_abs = qty * fill_price * d["quanto_multiplier"]
                fee = costs.taker_fee(notional_abs, d["taker_fee_rate"])
                total_traded_notional += notional_abs
                # 滑点成本 = |成交价 - 中间价| * 数量，它不进"手续费"，而是直接让盈亏变差
                total_slippage_cost += abs(fill_price - price) * qty * d["quanto_multiplier"]

                if action == "open":
                    if pos:
                        new_size = pos["size"] + qty
                        pos["entry_price"] = (pos["entry_price"] * pos["size"] + fill_price * qty) / max(new_size, 1)
                        pos["size"] = new_size
                        pos["fees_accum"] += fee
                    else:
                        pos = {"side": side, "size": qty, "entry_price": fill_price,
                               "fees_accum": fee, "funding_accum": 0.0, "last_ts": t, "open_time": t}
                        positions[s] = pos
                else:
                    pos_direction = 1 if side == "long" else -1
                    gross = (fill_price - pos["entry_price"]) * qty * d["quanto_multiplier"] * pos_direction
                    if action == "close":
                        total_fee = pos["fees_accum"] + fee
                        total_funding = pos["funding_accum"]
                        net = gross - total_fee - total_funding
                        equity += net
                        trades.append({
                            "symbol": s, "side": side, "entry_price": pos["entry_price"], "exit_price": fill_price,
                            "pnl": net, "gross": gross, "fees": total_fee, "funding": total_funding,
                            "open_time": pos["open_time"], "close_time": t, "reason": "调仓平仓/反向",
                        })
                        del positions[s]
                        pos = None
                        current_side, current_size = None, 0
                    else:  # reduce
                        proportion = min(qty / max(pos["size"], 1), 1.0)
                        entry_fee_share = pos["fees_accum"] * proportion
                        pos["fees_accum"] -= entry_fee_share
                        funding_share = pos["funding_accum"] * proportion
                        pos["funding_accum"] -= funding_share
                        net = gross - entry_fee_share - fee - funding_share
                        equity += net
                        trades.append({
                            "symbol": s, "side": side, "entry_price": pos["entry_price"], "exit_price": fill_price,
                            "pnl": net, "gross": gross, "fees": entry_fee_share + fee, "funding": funding_share,
                            "open_time": pos["open_time"], "close_time": t, "reason": "组合再平衡(减仓)",
                        })
                        pos["size"] -= qty
                        current_size = pos["size"]

        curve_equity = _mark_to_market_equity(equity, positions, mark_price_now, prepared)
        if curve_equity > 0 and positions:
            gross_notional = sum(
                p["size"] * mark_price_now.get(sym, p["entry_price"]) * prepared[sym]["quanto_multiplier"]
                for sym, p in positions.items())
            lev_samples.append(gross_notional / curve_equity)

        equity_curve.append({"t": float(t), "e": curve_equity})

    # ---- 收尾：按最后价格强平所有剩余持仓 ----
    if all_ts:
        last_t = all_ts[-1]
        for s, pos in list(positions.items()):
            d = prepared[s]
            si = _asof(d["short_ts"], last_t)
            mid_price = float(d["short_close"][si]) if si >= 0 else pos["entry_price"]
            last_price = costs.slippage_adjusted_price(
                mid_price, pos["side"], cost_cfg.slippage_bps, is_entry=False)
            direction = 1 if pos["side"] == "long" else -1
            gross = (last_price - pos["entry_price"]) * pos["size"] * d["quanto_multiplier"] * direction
            close_notional = pos["size"] * last_price * d["quanto_multiplier"]
            fee = costs.taker_fee(close_notional, d["taker_fee_rate"])
            total_traded_notional += close_notional
            total_slippage_cost += abs(last_price - mid_price) * pos["size"] * d["quanto_multiplier"]
            net = gross - pos["fees_accum"] - fee - pos["funding_accum"]
            equity += net
            trades.append({
                "symbol": s, "side": pos["side"], "entry_price": pos["entry_price"], "exit_price": last_price,
                "pnl": net, "gross": gross, "fees": pos["fees_accum"] + fee, "funding": pos["funding_accum"],
                "open_time": pos["open_time"], "close_time": last_t, "reason": "回测结束强平",
            })
        if positions and equity_curve:
            equity_curve[-1]["e"] = equity
        positions.clear()

    stats = _performance_stats(equity_curve, initial_capital)
    avg_equity = float(np.mean([p["e"] for p in equity_curve])) if equity_curve else initial_capital
    years_covered = max((all_ts[-1] - all_ts[0]) / (365 * 86400.0), 1e-6)
    turnover_annualized = (total_traded_notional / max(avg_equity, 1e-9)) / years_covered

    per_symbol: Dict[str, dict] = {}
    for s in symbols:
        s_trades = [tr for tr in trades if tr["symbol"] == s]
        per_symbol[s] = {
            "trade_count": len(s_trades),
            "net_pnl": sum(tr["pnl"] for tr in s_trades),
            "fees": sum(tr["fees"] for tr in s_trades),
            "funding": sum(tr["funding"] for tr in s_trades),
            "bar_counts": prepared[s]["bar_counts"],
            "last_trend_forecast": float(prepared[s]["main_f"][-1]) if len(prepared[s]["main_f"]) else 0.0,
            "last_carry_forecast": float(prepared[s]["carry_f"][-1]) if len(prepared[s]["carry_f"]) else 0.0,
            "last_adaptive_risk_multiplier": (
                float(prepared[s]["adaptive_risk_multiplier"][-1])
                if len(prepared[s]["adaptive_risk_multiplier"]) else 1.0
            ),
        }

    ret_pct = ((equity - initial_capital) / initial_capital * 100.0) if initial_capital else 0.0

    total_fees_sum = sum(tr["fees"] for tr in trades)
    total_funding_sum = sum(tr["funding"] for tr in trades)
    # 净盈亏 = 毛利 - 手续费 - 资金费，且滑点已经体现在成交价里(所以要加回来才是"完全不扣成本的毛利")
    net_sum = sum(tr["pnl"] for tr in trades)
    gross_before_costs = net_sum + total_fees_sum + total_funding_sum + total_slippage_cost
    eff_rate = prepared[symbols[0]]["taker_fee_rate"] if symbols else 0.0
    avg_adaptive = float(np.mean(adaptive_mult_samples)) if adaptive_mult_samples else 1.0
    min_adaptive = float(np.min(adaptive_mult_samples)) if adaptive_mult_samples else 1.0
    adaptive_active_pct = (
        float(np.mean(np.asarray(adaptive_mult_samples) < 0.999) * 100.0)
        if adaptive_mult_samples else 0.0
    )

    return PortfolioBacktestResult(
        symbols=symbols, start_ts=float(all_ts[0]), end_ts=float(all_ts[-1]),
        initial_capital=initial_capital, final_equity=equity, return_pct=ret_pct,
        annualized_return_pct=stats["annualized_return_pct"], annualized_vol_pct=stats["annualized_vol_pct"],
        sharpe=stats["sharpe"], sortino=stats["sortino"], max_drawdown_pct=stats["max_drawdown_pct"],
        calmar=stats["calmar"], turnover_annualized=turnover_annualized,
        trade_count=len(trades), trades=trades, equity_curve=equity_curve,
        gross_pnl_before_costs=gross_before_costs, total_fees=total_fees_sum,
        total_slippage_cost=total_slippage_cost, total_funding=total_funding_sum,
        total_traded_notional=total_traded_notional,
        avg_trade_notional=(total_traded_notional / len(trades)) if trades else 0.0,
        avg_gross_leverage=(float(np.mean(lev_samples)) if lev_samples else 0.0),
        max_gross_leverage=(float(np.max(lev_samples)) if lev_samples else 0.0),
        effective_taker_rate=eff_rate,
        avg_adaptive_risk_multiplier=avg_adaptive,
        min_adaptive_risk_multiplier=min_adaptive,
        adaptive_risk_active_pct=adaptive_active_pct,
        per_symbol=per_symbol, bar_counts={s: prepared[s]["bar_counts"] for s in symbols},
        warnings=warnings,
    )
