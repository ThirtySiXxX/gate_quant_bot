"""
EWMA 波动率估计——整个新版系统性策略(趋势信号归一化 / carry信号归一化 /
组合协方差 / 波动率目标仓位)共用的地基模块。

用指数加权移动平均(RiskMetrics风格，默认 lambda=0.94)估计收益率的方差，
比固定窗口的滚动标准差更快响应波动率变化（近期数据权重更高），
这也是 Moskowitz/Ooi/Pedersen 以及 pysystemtrade 里常见的做法。

本模块只做纯计算，不碰任何网络/交易所接口。
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd

DEFAULT_LAMBDA = 0.94   # EWMA衰减因子，越接近1记忆越长；0.94是RiskMetrics经典默认值
MIN_PERIODS = 20

# 各周期一年大约有多少根K线，用于把"每根K线尺度"的方差年化
BARS_PER_YEAR = {
    "15m": 365 * 24 * 4,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
}


def log_returns(close: pd.Series) -> pd.Series:
    """对数收益率，长期复利下比简单收益率更适合做方差/协方差建模。"""
    return np.log(close / close.shift(1))


def ewma_var(returns: pd.Series, lam: float = DEFAULT_LAMBDA, min_periods: int = MIN_PERIODS) -> pd.Series:
    """逐期 EWMA 方差(未年化，"每根K线"尺度)。
    数学上等价于 var_t = lam*var_{t-1} + (1-lam)*r_t^2 （均值近似为0的简化版，
    对短周期高频收益率这个近似很常见也足够稳健）。
    """
    r = returns.fillna(0.0)
    return r.ewm(alpha=1 - lam, adjust=False, min_periods=min_periods).var(bias=False)


def ewma_vol(returns: pd.Series, lam: float = DEFAULT_LAMBDA, min_periods: int = MIN_PERIODS) -> pd.Series:
    """逐期 EWMA 标准差(未年化)。"""
    return np.sqrt(ewma_var(returns, lam=lam, min_periods=min_periods))


def annualize_vol(vol_per_bar: pd.Series, interval: str) -> pd.Series:
    bars_per_year = BARS_PER_YEAR.get(interval, 365)
    return vol_per_bar * np.sqrt(bars_per_year)


def price_vol_annualized(close: pd.Series, interval: str, lam: float = DEFAULT_LAMBDA,
                          min_periods: int = MIN_PERIODS) -> pd.Series:
    """从收盘价序列直接算年化波动率(比例，如 0.6 代表 60%/年)，用于:
      - carry信号的分母
      - 组合协方差矩阵的对角线校验
      - 仪表盘展示
    """
    r = log_returns(close)
    v = ewma_vol(r, lam=lam, min_periods=min_periods)
    return annualize_vol(v, interval)


def price_vol_in_price_units(close: pd.Series, interval: str, lam: float = DEFAULT_LAMBDA,
                              min_periods: int = MIN_PERIODS) -> pd.Series:
    """把"每根K线尺度"的波动率换算回价格单位(未年化)：sigma_P = P * sigma_r。
    这是趋势信号做 volatility-adjust 时要用的分母:
        Trend_{f,s} = (EMA_f(P) - EMA_s(P)) / sigma_P
    不能用年化后的波动率，因为分子(EMA差)也是"每根K线尺度"的价格量纲，两边尺度要匹配。
    """
    r = log_returns(close)
    v = ewma_vol(r, lam=lam, min_periods=min_periods)
    return close * v


def rogers_satchell_variance(df: pd.DataFrame) -> pd.Series:
    """Rogers-Satchell 单根K线方差估计。

    和 close-to-close 收益率不同，它同时使用 open/high/low/close，因此能看到
    “盘中猛拉/猛砍、收盘又回到原位”的长影线风险。RS 对非零漂移过程也保持一致，
    适合这里用来判断“高波动是否突然放大”，不参与多空方向预测。
    """
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return pd.Series(np.nan, index=df.index, dtype=float)
    o = pd.to_numeric(df["open"], errors="coerce")
    h = pd.to_numeric(df["high"], errors="coerce")
    l = pd.to_numeric(df["low"], errors="coerce")
    c = pd.to_numeric(df["close"], errors="coerce")
    valid = (o > 0) & (h > 0) & (l > 0) & (c > 0)
    out = pd.Series(np.nan, index=df.index, dtype=float)
    rs = np.log(h[valid] / o[valid]) * np.log(h[valid] / c[valid]) + \
         np.log(l[valid] / o[valid]) * np.log(l[valid] / c[valid])
    out.loc[valid] = rs.clip(lower=0.0)
    return out


def adaptive_chop_risk_series(
    df: pd.DataFrame,
    er_lookback: int = 24,
    er_full_risk: float = 0.35,
    fast_lambda: float = 0.75,
    slow_lambda: float = 0.995,
    vol_ratio_start: float = 1.10,
    vol_ratio_full: float = 1.60,
    max_risk_reduction: float = 0.65,
    smoothing_span: int = 4,
) -> pd.DataFrame:
    """计算“高波动 + 低方向效率”风险乘数，返回逐根因果序列。

    ER = |C_t-C_(t-n)| / sum(|dC|)：越接近1越像单向趋势，越接近0越像来回乱走。
    VR = RS_vol_fast / RS_vol_slow：当前影线波动相对自身慢基准的放大倍数。
    multiplier = 1 - max_reduction * vol_stress * chop_stress。

    这个乘数永远在 [1-max_risk_reduction, 1] 内，只能缩小仓位，不能改变方向或放大风险。
    """
    if "close" not in df.columns:
        return pd.DataFrame({
            "efficiency_ratio": np.nan, "range_vol_fast": np.nan,
            "range_vol_slow": np.nan, "vol_ratio": np.nan,
            "vol_stress": 0.0, "chop_stress": 0.0,
            "raw_multiplier": 1.0, "risk_multiplier": 1.0,
        }, index=df.index)

    n = max(int(er_lookback), 2)
    er_threshold = max(float(er_full_risk), 1e-6)
    fast_lam = min(max(float(fast_lambda), 0.01), 0.999)
    slow_lam = min(max(float(slow_lambda), fast_lam + 1e-6), 0.9999)
    ratio_start = max(float(vol_ratio_start), 0.01)
    ratio_full = max(float(vol_ratio_full), ratio_start + 1e-6)
    max_reduction = min(max(float(max_risk_reduction), 0.0), 0.95)
    smooth = max(int(smoothing_span), 1)

    close = pd.to_numeric(df.get("close"), errors="coerce")
    path = close.diff().abs().rolling(n, min_periods=n).sum()
    efficiency = (close - close.shift(n)).abs() / path.replace(0.0, np.nan)
    efficiency = efficiency.clip(lower=0.0, upper=1.0)

    rs_var = rogers_satchell_variance(df)
    fast_var = rs_var.ewm(alpha=1.0 - fast_lam, adjust=False,
                          min_periods=max(4, min(n, 8))).mean()
    slow_var = rs_var.ewm(alpha=1.0 - slow_lam, adjust=False,
                          min_periods=max(12, n)).mean()
    fast_vol = np.sqrt(fast_var.clip(lower=0.0))
    slow_vol = np.sqrt(slow_var.clip(lower=0.0))
    vol_ratio = fast_vol / slow_vol.replace(0.0, np.nan)

    vol_stress = ((vol_ratio - ratio_start) / (ratio_full - ratio_start)).clip(0.0, 1.0)
    direction_quality = (efficiency / er_threshold).clip(0.0, 1.0)
    chop_stress = 1.0 - direction_quality
    raw_multiplier = 1.0 - max_reduction * vol_stress * chop_stress
    # 预热不足时保持中性(1.0)，不因数据不足意外缩仓。
    raw_multiplier = raw_multiplier.fillna(1.0).clip(1.0 - max_reduction, 1.0)
    multiplier = raw_multiplier.ewm(span=smooth, adjust=False).mean().clip(1.0 - max_reduction, 1.0)

    return pd.DataFrame({
        "efficiency_ratio": efficiency,
        "range_vol_fast": fast_vol,
        "range_vol_slow": slow_vol,
        "vol_ratio": vol_ratio,
        "vol_stress": vol_stress,
        "chop_stress": chop_stress,
        "raw_multiplier": raw_multiplier,
        "risk_multiplier": multiplier,
    }, index=df.index)


def adaptive_chop_risk_from_config(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """用 SystematicConfig 构建自适应风险序列。关闭时返回全程1.0，
    使实盘、回测和消融测试可以共用同一入口。
    """
    if not bool(getattr(cfg, "adaptive_risk_enabled", True)):
        return pd.DataFrame({
            "efficiency_ratio": np.nan, "range_vol_fast": np.nan,
            "range_vol_slow": np.nan, "vol_ratio": np.nan,
            "vol_stress": 0.0, "chop_stress": 0.0,
            "raw_multiplier": 1.0, "risk_multiplier": 1.0,
        }, index=df.index)
    return adaptive_chop_risk_series(
        df,
        er_lookback=getattr(cfg, "adaptive_er_lookback", 24),
        er_full_risk=getattr(cfg, "adaptive_er_full_risk", 0.35),
        fast_lambda=getattr(cfg, "adaptive_vol_fast_lambda", 0.75),
        slow_lambda=getattr(cfg, "adaptive_vol_slow_lambda", 0.995),
        vol_ratio_start=getattr(cfg, "adaptive_vol_ratio_start", 1.10),
        vol_ratio_full=getattr(cfg, "adaptive_vol_ratio_full", 1.60),
        max_risk_reduction=getattr(cfg, "adaptive_max_risk_reduction", 0.65),
        smoothing_span=getattr(cfg, "adaptive_multiplier_smoothing_span", 4),
    )


def ewma_covariance_matrix(returns_df: pd.DataFrame, lam: float = DEFAULT_LAMBDA,
                            min_periods: int = MIN_PERIODS) -> pd.DataFrame:
    """多资产收益率矩阵(列=标的，行=时间)的 EWMA 协方差矩阵（取最后一期状态，未年化，"每根K线"尺度）。

    实现方式：把 EWMA 更新写成显式递推 Sigma_t = lam*Sigma_{t-1} + (1-lam)*r_t r_t^T，
    比 pandas 内置的 ewm().cov() 更透明也更容易核对数值是否正确。
    缺失值(某标的在早期还没有数据)用0填充参与递推——影响很小，因为早期权重本来就被后续数据快速衰减掉。
    """
    cols = list(returns_df.columns)
    n = len(cols)
    r_mat = returns_df.fillna(0.0).values
    sigma = np.zeros((n, n))
    warm = min(min_periods, len(r_mat))
    if warm > 0:
        sigma = np.cov(r_mat[:warm].T, bias=True) if n > 1 else np.array([[np.var(r_mat[:warm, 0])]])
        if sigma.shape != (n, n):
            sigma = np.atleast_2d(sigma)
    for t in range(warm, len(r_mat)):
        rt = r_mat[t].reshape(-1, 1)
        sigma = lam * sigma + (1 - lam) * (rt @ rt.T)
    return pd.DataFrame(sigma, index=cols, columns=cols)


def annualize_covariance(sigma_per_bar: pd.DataFrame, interval: str) -> pd.DataFrame:
    bars_per_year = BARS_PER_YEAR.get(interval, 365)
    return sigma_per_bar * bars_per_year


def ewma_covariance_series(returns_df: pd.DataFrame, lam: float = DEFAULT_LAMBDA,
                            min_periods: int = MIN_PERIODS):
    """和 ewma_covariance_matrix 类似，但一次性算出"逐期"的协方差矩阵快照序列(未年化)，
    而不是只返回处理完整段历史后的最终状态。

    用于回测：如果每次只需要"某个时间点为止"的协方差矩阵，重新对截至该时间点的全部历史
    跑一次递推是 O(bars^2)，在几千根K线的回测里会很慢；这里改成一次遍历同时产出每一步的
    快照(O(bars))，回测时用 asof 二分查找定位到对应时间点的快照即可，既正确(只用因果数据)
    又快。

    返回: (timestamps: List[float], matrices: List[np.ndarray])，两个列表按时间升序一一对应，
    cols 属性另外返回，供调用方知道矩阵每一行/列对应哪个标的。
    """
    cols = list(returns_df.columns)
    n = len(cols)
    idx = list(returns_df.index)
    r_mat = returns_df.fillna(0.0).values
    sigma = np.zeros((n, n))
    warm = min(min_periods, len(r_mat))
    if warm > 0:
        sigma = np.atleast_2d(np.cov(r_mat[:warm].T, bias=True)) if n > 1 else np.array([[np.var(r_mat[:warm, 0])]])
    timestamps: List = []
    matrices: List[np.ndarray] = []
    for t in range(len(r_mat)):
        if t >= warm:
            rt = r_mat[t].reshape(-1, 1)
            sigma = lam * sigma + (1 - lam) * (rt @ rt.T)
        timestamps.append(idx[t])
        matrices.append(sigma.copy())
    return timestamps, matrices, cols
