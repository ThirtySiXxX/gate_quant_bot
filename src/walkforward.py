"""
滚动样本外验证(walk-forward) + 趋势捕获率诊断。

解决两个一直没法回答的问题：

1) "这次改动到底有没有用？"
   单次整段回测很容易被某一段特殊行情主导——一段大牛市能让任何做多倾向的策略
   看起来都很好。把窗口切成若干段、每段单独统计，就能看出表现是稳定的还是
   只靠某一段撑起来的(fold之间方差很大 = 结果不可信)。

   注意：本策略的参数是人工设定的、不是从数据里拟合出来的，所以这里的
   walk-forward 是"跨时间稳定性检验"，不是"样本内定参数、样本外验证"的
   那种参数拟合流程。这一点必须说清楚，不能把它当成"已经做过防过拟合验证"——
   等以后真的引入需要训练的模型(比如你说的反转分类器)，才需要在这个框架上
   再加 purged & embargoed 的交叉验证。

2) "到底是漏趋势，还是抓到了但拿不住？"
   先客观地把行情里的趋势段找出来(这是事后诊断，允许用全量数据，因为它不参与
   任何交易决策)，然后逐段量化：
     - 参与率      : 有多少趋势段我们压根没有仓位(直接回答"漏了多少")
     - 捕获率      : 这段行情涨/跌了X%，我们的账户赚了Y%，Y/X是多少
     - 入场滞后    : 趋势走了百分之多少我们才进场
     - 离场过早    : 趋势还剩百分之多少我们就走了
   这四个数能直接分辨"入场慢"和"出场早"哪个才是主要矛盾，避免继续凭感觉调参。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .backtest import PortfolioBacktestResult, SymbolBacktestInputs, run_portfolio_backtest
from .config import CostConfig, SystematicConfig


# ============================================================ 趋势段识别
@dataclass
class TrendEpisode:
    symbol: str
    direction: str          # 'up' / 'down'
    start_ts: float
    end_ts: float
    start_price: float
    end_price: float

    @property
    def move_pct(self) -> float:
        if self.start_price <= 0:
            return 0.0
        return (self.end_price - self.start_price) / self.start_price * 100.0

    @property
    def abs_move_pct(self) -> float:
        return abs(self.move_pct)

    @property
    def duration_sec(self) -> float:
        return max(self.end_ts - self.start_ts, 1.0)


def detect_trend_episodes(df: pd.DataFrame, symbol: str, min_move_pct: float = 5.0) -> List[TrendEpisode]:
    """用 zigzag(折返过滤)把价格序列切成若干"显著单向行情段"。

    算法：从第一根K线开始跟踪极值，价格从最近极值反向回撤超过 min_move_pct 时，
    就认为上一段行情结束、方向反转，记录这一段。只保留净幅度也超过阈值的段，
    过滤掉噪声。

    这是**事后诊断工具**，会用到整段数据(包括"未来")，因为它的作用是给已经跑完的
    回测打分，不参与任何交易决策，不存在前视偏差问题。
    """
    if len(df) < 3:
        return []
    d = df.sort_values("timestamp").reset_index(drop=True)
    ts = d["timestamp"].values.astype(float)
    px = d["close"].values.astype(float)
    thr = min_move_pct / 100.0

    episodes: List[TrendEpisode] = []
    pivot_i = 0                      # 上一个已确认的转折点
    ext_i = 0                        # 自 pivot 以来的极值位置
    direction: Optional[str] = None  # 当前正在形成的这一段的方向

    def _emit(kind: str, a: int, b: int):
        if b <= a:
            return
        lo, hi = px[a], px[b]
        if lo <= 0:
            return
        if kind == "up" and (hi - lo) / lo < thr:
            return
        if kind == "down" and (lo - hi) / lo < thr:
            return
        episodes.append(TrendEpisode(symbol, kind, ts[a], ts[b], lo, hi))

    for i in range(1, len(px)):
        if px[pivot_i] <= 0 or px[ext_i] <= 0:
            pivot_i = ext_i = i
            continue

        if direction is None:
            # 还没确定方向：等价格相对起点走出足够幅度，才确定第一段的方向
            move = (px[i] - px[pivot_i]) / px[pivot_i]
            if move >= thr:
                direction, ext_i = "up", i
            elif move <= -thr:
                direction, ext_i = "down", i
            elif px[i] < px[pivot_i]:
                pivot_i = i      # 还在原地徘徊，把起点挪到更低处，便于识别后续上涨
            continue

        if direction == "up":
            if px[i] > px[ext_i]:
                ext_i = i
            elif (px[ext_i] - px[i]) / px[ext_i] >= thr:
                _emit("up", pivot_i, ext_i)       # 从高点回撤够多，确认上涨段结束
                pivot_i, ext_i, direction = ext_i, i, "down"
        else:
            if px[i] < px[ext_i]:
                ext_i = i
            elif (px[i] - px[ext_i]) / px[ext_i] >= thr:
                _emit("down", pivot_i, ext_i)     # 从低点反弹够多，确认下跌段结束
                pivot_i, ext_i, direction = ext_i, i, "up"

    # 收尾：最后一段还没被折返确认，但幅度够大也算
    if direction == "up":
        _emit("up", pivot_i, ext_i)
    elif direction == "down":
        _emit("down", pivot_i, ext_i)

    return [e for e in episodes if e.abs_move_pct >= min_move_pct and e.end_ts > e.start_ts]


# ============================================================ 趋势捕获率诊断
def _equity_at(equity_curve: List[dict], t: float) -> Optional[float]:
    if not equity_curve:
        return None
    ts = [p["t"] for p in equity_curve]
    i = int(np.searchsorted(ts, t, side="right")) - 1
    if i < 0:
        return None
    return float(equity_curve[i]["e"])


def diagnose_trend_capture(result: PortfolioBacktestResult,
                            price_by_symbol: Dict[str, pd.DataFrame],
                            min_move_pct: float = 5.0) -> dict:
    """对一次回测结果做"趋势捕获"诊断，回答漏没漏、拿没拿满、进晚了还是出早了。"""
    all_eps: List[TrendEpisode] = []
    for sym, df in price_by_symbol.items():
        all_eps.extend(detect_trend_episodes(df, sym, min_move_pct=min_move_pct))

    if not all_eps:
        return {"episode_count": 0, "note": f"这段行情里没有幅度超过{min_move_pct}%的显著趋势段，无法诊断"}

    trades = result.trades or []
    rows = []
    for ep in all_eps:
        want_side = "long" if ep.direction == "up" else "short"
        # 找出和这段趋势时间重叠、且方向正确的成交
        overlap = [t for t in trades
                   if t["symbol"] == ep.symbol and t["side"] == want_side
                   and t["close_time"] > ep.start_ts and t["open_time"] < ep.end_ts]
        participated = len(overlap) > 0

        entry_lag = np.nan
        exit_early = np.nan
        if participated:
            first_in = min(t["open_time"] for t in overlap)
            last_out = max(t["close_time"] for t in overlap)
            entry_lag = np.clip((first_in - ep.start_ts) / ep.duration_sec, 0.0, 1.0) * 100.0
            exit_early = np.clip((ep.end_ts - last_out) / ep.duration_sec, 0.0, 1.0) * 100.0

        # 捕获率：这段行情价格动了X%，同期账户权益变化Y%，Y/X 就是捕获率
        e0 = _equity_at(result.equity_curve, ep.start_ts)
        e1 = _equity_at(result.equity_curve, ep.end_ts)
        capture = np.nan
        if e0 and e1 and e0 > 0 and ep.abs_move_pct > 1e-9:
            equity_ret_pct = (e1 - e0) / e0 * 100.0
            capture = equity_ret_pct / ep.abs_move_pct * 100.0

        rows.append({
            "symbol": ep.symbol, "direction": ep.direction,
            "start_ts": ep.start_ts, "end_ts": ep.end_ts,
            "move_pct": ep.move_pct, "participated": participated,
            "capture_pct": capture, "entry_lag_pct": entry_lag, "exit_early_pct": exit_early,
            "trade_count": len(overlap),
        })

    df = pd.DataFrame(rows)
    part = df[df["participated"]]

    def _med(col, src=part):
        v = src[col].dropna()
        return float(v.median()) if len(v) else float("nan")

    return {
        "episode_count": len(df),
        "participated_count": int(df["participated"].sum()),
        "participation_rate_pct": float(df["participated"].mean() * 100.0),
        "missed_count": int((~df["participated"]).sum()),
        # 漏掉的趋势里，本来有多大空间(用来判断漏的是不是大行情)
        "missed_avg_move_pct": float(df[~df["participated"]]["move_pct"].abs().mean())
                                if (~df["participated"]).any() else 0.0,
        "median_capture_pct": _med("capture_pct"),
        "median_entry_lag_pct": _med("entry_lag_pct"),
        "median_exit_early_pct": _med("exit_early_pct"),
        "episodes": rows,
        "min_move_pct": min_move_pct,
    }


# ============================================================ 滚动样本外验证
@dataclass
class FoldResult:
    fold_index: int
    start_ts: float
    end_ts: float
    return_pct: float
    annualized_return_pct: float
    sharpe: float
    max_drawdown_pct: float
    trade_count: int
    error: Optional[str] = None


@dataclass
class WalkForwardResult:
    mode: str = "expanding"
    folds: List[FoldResult] = field(default_factory=list)
    mean_return_pct: float = 0.0
    median_return_pct: float = 0.0
    std_return_pct: float = 0.0
    positive_fold_ratio_pct: float = 0.0
    mean_sharpe: float = 0.0
    worst_fold_return_pct: float = 0.0
    consistency_note: str = ""

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "folds": [f.__dict__ for f in self.folds],
            "mean_return_pct": self.mean_return_pct,
            "median_return_pct": self.median_return_pct,
            "std_return_pct": self.std_return_pct,
            "positive_fold_ratio_pct": self.positive_fold_ratio_pct,
            "mean_sharpe": self.mean_sharpe,
            "worst_fold_return_pct": self.worst_fold_return_pct,
            "consistency_note": self.consistency_note,
        }


def _slice_inputs(symbol_inputs: List[SymbolBacktestInputs],
                   start_ts: float, end_ts: float) -> List[SymbolBacktestInputs]:
    """按时间窗口裁剪每个标的的K线。注意趋势/波动率指标需要预热，所以这里
    不裁掉窗口之前的历史——只把窗口"结束时间"之后的数据砍掉，并让回测从
    start_ts 之后才开始产生交易(靠 test_start_ts 实现)。这样每一折的
    指标预热都是用它自己之前的真实历史，不存在跨折泄漏。"""
    out = []
    for sb in symbol_inputs:
        new = copy.copy(sb)
        # 短周期指标同样需要窗口前预热；test_start_ts 负责阻止预热区间产生交易。
        new.df_short = sb.df_short[sb.df_short["timestamp"] <= end_ts].reset_index(drop=True)
        new.test_start_ts = start_ts
        # 其余序列保留窗口结束前的全部历史，用于指标预热(纯因果，不含未来)
        new.df_main = sb.df_main[sb.df_main["timestamp"] <= end_ts].reset_index(drop=True)
        new.df_regime = sb.df_regime[sb.df_regime["timestamp"] <= end_ts].reset_index(drop=True)
        new.df_cov = sb.df_cov[sb.df_cov["timestamp"] <= end_ts].reset_index(drop=True)
        if sb.funding_history is not None and len(sb.funding_history) > 0:
            new.funding_history = sb.funding_history[
                sb.funding_history["timestamp"] <= end_ts].reset_index(drop=True)
        out.append(new)
    return out


def run_walk_forward(symbol_inputs: List[SymbolBacktestInputs], sys_cfg: SystematicConfig,
                      cost_cfg: CostConfig, initial_capital: float, n_folds: int = 5,
                      mode: str = "expanding",
                      progress_cb: Optional[Callable[[int, str], None]] = None) -> WalkForwardResult:
    """把整段历史切成 n_folds 折，逐折统计表现。

    mode='expanding': 每折的测试窗口依次往后推(第k折测第k段)，指标预热用它之前的全部历史；
    mode='rolling'  : 同上，但只是把窗口等分——本策略参数不从数据拟合，两种模式的差别
                      仅在于预热历史的长度。

    看结果的方法：**不要只看平均值**。要看 fold 之间的方差、有多少折是正收益、
    最差的一折有多差。如果只有一折特别好、其余都平平，说明整体表现是被某一段
    特殊行情撑起来的，不能指望它在未来重现。
    """
    all_ts = []
    for sb in symbol_inputs:
        if len(sb.df_short) > 0:
            all_ts.extend(sb.df_short["timestamp"].tolist())
    if not all_ts:
        return WalkForwardResult(mode=mode, consistency_note="没有可用数据")

    data_min, t_max = float(min(all_ts)), float(max(all_ts))
    requested_starts = [float(sb.test_start_ts) for sb in symbol_inputs
                        if sb.test_start_ts is not None]
    # 回测任务会在 df_short 里额外带入指标预热K线。这些数据可以用于
    # 每一折起点的指标计算，但绝不能被算入用户选择的90/180天测试窗口。
    t_min = max(data_min, max(requested_starts)) if requested_starts else data_min
    total = t_max - t_min
    if total <= 0 or n_folds < 2:
        return WalkForwardResult(mode=mode, consistency_note="数据跨度太短或折数太少，无法做滚动验证")

    # 有显式 test_start_ts 时，窗口前的 df_short/df_main 已经是预热数据，
    # 所以测试窗口本身不需要再丢掉20%。只有旧调用方没有指定起点时才保留旧预热行为。
    warmup = 0.0 if requested_starts else total * 0.20
    test_span = (total - warmup) / n_folds

    folds: List[FoldResult] = []
    for k in range(n_folds):
        f_start = t_min + warmup + k * test_span
        f_end = f_start + test_span
        if progress_cb:
            progress_cb(int(k / n_folds * 100), f"滚动验证 第{k+1}/{n_folds}折")
        try:
            sliced = _slice_inputs(symbol_inputs, f_start, f_end)
            if all(len(s.df_short) < 10 for s in sliced):
                folds.append(FoldResult(k + 1, f_start, f_end, 0, 0, 0, 0, 0, error="该折数据不足"))
                continue
            r = run_portfolio_backtest(sliced, sys_cfg, cost_cfg, initial_capital)
            folds.append(FoldResult(
                fold_index=k + 1, start_ts=f_start, end_ts=f_end,
                return_pct=r.return_pct, annualized_return_pct=r.annualized_return_pct,
                sharpe=r.sharpe, max_drawdown_pct=r.max_drawdown_pct, trade_count=r.trade_count,
            ))
        except Exception as e:
            folds.append(FoldResult(k + 1, f_start, f_end, 0, 0, 0, 0, 0, error=str(e)))

    ok = [f for f in folds if f.error is None]
    if not ok:
        return WalkForwardResult(mode=mode, folds=folds, consistency_note="所有折都失败了")

    rets = np.array([f.return_pct for f in ok], dtype=float)
    sharpes = np.array([f.sharpe for f in ok], dtype=float)
    pos_ratio = float((rets > 0).mean() * 100.0)
    std = float(rets.std())
    mean = float(rets.mean())

    if pos_ratio >= 70 and std <= abs(mean) * 1.5:
        note = "表现在各折之间比较一致，可信度相对较高"
    elif pos_ratio >= 50:
        note = "各折表现分化明显，整体结果对时间段比较敏感，建议再拉长回测窗口观察"
    else:
        note = ("超过一半的折是亏损的，说明整体正收益可能主要来自某一两段特殊行情，"
                "不建议据此认为策略稳定有效")

    return WalkForwardResult(
        mode=mode, folds=folds,
        mean_return_pct=mean, median_return_pct=float(np.median(rets)),
        std_return_pct=std, positive_fold_ratio_pct=pos_ratio,
        mean_sharpe=float(sharpes.mean()), worst_fold_return_pct=float(rets.min()),
        consistency_note=note,
    )


# ============================================================ 参数敏感性扫描
def parameter_sweep(symbol_inputs: List[SymbolBacktestInputs], sys_cfg: SystematicConfig,
                     cost_cfg: CostConfig, initial_capital: float,
                     param_name: str, values: List[float],
                     progress_cb: Optional[Callable[[int, str], None]] = None) -> List[dict]:
    """扫描单个参数，看收益/Sharpe 随它怎么变化。

    判读方法：**曲线应该是平滑的小山包，而不是某个值上孤立的尖峰**。
    如果只有某一个特定取值表现突出、邻近取值明显变差，几乎可以肯定是拟合了
    历史噪声，换到未来数据上不会重现——这种参数不要用。
    """
    out = []
    for i, v in enumerate(values):
        if progress_cb:
            progress_cb(int(i / max(len(values), 1) * 100), f"参数扫描 {param_name}={v}")
        cfg = copy.copy(sys_cfg)
        setattr(cfg, param_name, v)
        try:
            r = run_portfolio_backtest(symbol_inputs, cfg, cost_cfg, initial_capital)
            out.append({"value": v, "return_pct": r.return_pct, "sharpe": r.sharpe,
                         "max_drawdown_pct": r.max_drawdown_pct, "trade_count": r.trade_count})
        except Exception as e:
            out.append({"value": v, "error": str(e)})
    return out
