"""
配置加载与热重载模块。
支持运行期间修改 config.yaml（比如增删币种、调整风险参数），
引擎会周期性检测文件 mtime 变化并自动重新加载，无需重启进程。

所有修改现在都通过网页界面完成：网页表单提交后调用 ConfigStore.save(patch)
直接把变更深度合并写回 config.yaml 文件，用户不需要手动打开/编辑这个文件。
"""
from __future__ import annotations

import copy
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(Exception):
    pass


DEFAULT_CONFIG_PATH = os.environ.get("BOT_CONFIG_PATH", "config.yaml")


def _deep_merge(base: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


class ConfigStore:
    """线程安全的配置存储，支持文件热重载 + 网页表单写回。"""

    def __init__(self, path: str = DEFAULT_CONFIG_PATH):
        self.path = path
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._mtime: float = 0.0
        self._extra_symbols: List[str] = []  # 网页临时追加的币种（未写回文件前的缓冲）
        self.reload(force=True)

    # ---------------------------------------------------------
    def reload(self, force: bool = False) -> bool:
        try:
            mtime = os.path.getmtime(self.path)
        except FileNotFoundError as exc:
            raise ConfigError(f"找不到配置文件: {self.path}") from exc

        if not force and mtime == self._mtime:
            return False

        with open(self.path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        with self._lock:
            self._data = raw
            self._mtime = mtime
        return True

    def maybe_reload(self) -> bool:
        try:
            return self.reload(force=False)
        except ConfigError:
            return False

    # ---------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            data = copy.deepcopy(self._data)
        symbols = list(dict.fromkeys(data.get("symbols", []) + self._extra_symbols))
        data["symbols"] = symbols
        return data

    def add_symbol(self, symbol: str) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            return
        with self._lock:
            symbols = list(self._data.get("symbols", []))
            if symbol not in symbols and symbol not in self._extra_symbols:
                symbols.append(symbol)
                self._data["symbols"] = symbols
        self._write_to_disk()

    def remove_symbol(self, symbol: str) -> None:
        symbol = symbol.strip().upper()
        with self._lock:
            if symbol in self._extra_symbols:
                self._extra_symbols.remove(symbol)
            symbols = list(self._data.get("symbols", []))
            if symbol in symbols:
                symbols.remove(symbol)
                self._data["symbols"] = symbols
        self._write_to_disk()

    def save(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """把网页表单提交的变更（可以是任意嵌套结构，如 {"risk": {"max_leverage": 10}}）
        深度合并进当前配置并写回磁盘，返回合并后的完整快照。"""
        with self._lock:
            _deep_merge(self._data, copy.deepcopy(patch))
        self._write_to_disk()
        return self.snapshot()

    def _write_to_disk(self) -> None:
        with self._lock:
            data_copy = copy.deepcopy(self._data)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data_copy, f, allow_unicode=True, sort_keys=False)
        with self._lock:
            self._mtime = os.path.getmtime(self.path)

    # convenience getters -------------------------------------
    def get(self, *keys, default=None):
        data = self.snapshot()
        cur = data
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur


@dataclass
class RiskConfig:
    initial_capital_usdt: float = 10000.0
    risk_per_trade_pct: float = 5.0
    max_leverage: int = 15
    max_concurrent_positions: int = 6
    max_portfolio_heat_pct: float = 20.0
    daily_loss_limit_pct: float = 8.0
    max_correlated_positions: int = 3
    atr_stop_multiplier: float = 1.6
    atr_trail_multiplier: float = 2.2
    time_stop_bars: int = 8
    tp1_r_multiple: float = 1.0
    tp1_close_ratio: float = 0.5

    @classmethod
    def build(cls, d: Dict[str, Any]) -> "RiskConfig":
        base = cls()
        d = d or {}
        for k in base.__dataclass_fields__.keys():
            if k in d:
                setattr(base, k, d[k])
        return base


@dataclass
class StrategyConfig:
    min_score_to_enter: float = 65
    ema_fast: int = 21
    ema_slow: int = 55
    ema_regime: int = 200
    adx_period: int = 14
    adx_trend_threshold: float = 20
    rsi_period: int = 14
    rsi_oversold: float = 35
    rsi_overbought: float = 65
    bb_period: int = 20
    bb_std: float = 2.0
    keltner_period: int = 20
    keltner_atr_mult: float = 1.5
    atr_period: int = 14
    volume_ma_period: int = 20
    volume_spike_mult: float = 1.5
    min_net_edge_r: float = 0.15

    @classmethod
    def build(cls, d: Dict[str, Any]) -> "StrategyConfig":
        base = cls()
        d = d or {}
        for k in base.__dataclass_fields__.keys():
            if k in d:
                setattr(base, k, d[k])
        return base


@dataclass
class CostConfig:
    # ⚠️ 这里填你账户的**真实**费率。Gate 合约接口返回的 taker_fee_rate 是"公开基础费率"，
    # 不含你的 VIP 等级/点卡抵扣等折扣，通常比实际支付的高。之前的实现把合约返回值
    # 当成优先值、把这里填的当"兜底值"，导致用户在界面上改费率其实完全不生效，
    # 回测成本被系统性高估(实测某次回测隐含费率0.069%，而用户实际是0.05%，高估39%)。
    # 现在默认以这里填的为准；想用交易所返回的公开费率就把 use_contract_fee_rate 设为 true。
    taker_fee_rate: float = 0.0005            # 吃单费率，0.0005 = 0.05%
    maker_fee_rate: float = 0.0002            # 挂单费率，0.0002 = 0.02%
    use_account_fee_rate: bool = True         # true=优先读取当前账户/VIP等级的真实费率
    use_contract_fee_rate: bool = False       # true=改用交易所合约的公开基础费率(通常偏高)

    # 滑点：注意这项成本**不会出现在"手续费"里**，它直接体现为更差的成交价，
    # 所以很容易被忽略。BTC/ETH 这种深度很好的品种，几千U的市价单真实滑点通常
    # 只有 1bp 上下；5bp 是相当保守(悲观)的假设，会让回测成本显著高于实盘。
    slippage_bps: float = 2
    use_live_funding_rate: bool = True

    def effective_taker_rate(self, contract_taker_rate: Optional[float],
                             account_taker_rate: Optional[float] = None) -> float:
        """按配置决定实际使用哪个吃单费率。"""
        if self.use_account_fee_rate and account_taker_rate is not None:
            return float(account_taker_rate)
        if self.use_contract_fee_rate and contract_taker_rate:
            return float(contract_taker_rate)
        return float(self.taker_fee_rate)

    @classmethod
    def build(cls, d: Dict[str, Any]) -> "CostConfig":
        base = cls()
        d = d or {}
        for k in base.__dataclass_fields__.keys():
            if k in d:
                setattr(base, k, d[k])
        return base


@dataclass
class HedgeConfig:
    """[legacy，新版系统性策略默认不再使用] 旧版15分钟多因子+双向对冲策略的对冲参数，
    仅保留给 engine_legacy_hedge.py 用，新的 SystematicEngine 不读取这个配置。"""
    enabled: bool = True
    trigger_loss_r: float = 0.6          # 主仓浮亏达到止损距离的多少倍(R)时考虑对冲
    require_regime_flip: bool = True      # 是否要求高周期市场状态走弱/反转才触发对冲(更保守)
    hedge_ratio: float = 1.0              # 对冲仓位占主仓名义价值的比例，1.0=完全对冲
    max_hedge_bars: int = 12              # 对冲最长持续K线数(15m*12=3小时)，到期强制处理两条腿
    unwind_recovery_r: float = 0.2        # 主仓浮亏收窄到这个R值以内，撤销对冲、恢复正常持仓管理
    max_active_hedges: int = 3            # 同时最多几组对冲

    @classmethod
    def build(cls, d: Dict[str, Any]) -> "HedgeConfig":
        base = cls()
        d = d or {}
        for k in base.__dataclass_fields__.keys():
            if k in d:
                setattr(base, k, d[k])
        return base


_DEFAULT_EWMAC_HORIZONS = [(8, 32), (16, 64), (32, 128), (64, 256)]


def _as_horizon_tuples(v) -> List[tuple]:
    out = []
    for pair in v:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            out.append((int(pair[0]), int(pair[1])))
    return out or list(_DEFAULT_EWMAC_HORIZONS)


@dataclass
class SystematicConfig:
    """新版系统性策略：多资产 Time-Series Momentum(趋势) + Carry(资金费率) +
    波动率目标(volatility targeting) + 相关性感知组合风险分配。

    设计参考 Moskowitz/Ooi/Pedersen 的 TSMOM 研究和 Robert Carver 的
    pysystemtrade 开源框架思路，按你确认的多周期方案实现：
        执行/复核周期 = 15分钟；短趋势 = 1H EWMAC；主趋势 = 4H EWMAC；
        大周期regime过滤 = 1D；波动率 = 1H+4H；资金费Carry按实际funding周期；
        组合协方差按 covariance_interval（默认4H）。
    """
    # ---- 资金 ----
    initial_capital_usdt: float = 10000.0     # 仅 paper 模式/回测默认初始资金使用

    # ---- 信号权重 ----
    # trend_weight 相对 carry 调高：carry(资金费率)信号强度天然远小于趋势，混合权重太高会在强趋势期间
    # "稀释"趋势信号、拖慢入场/减小仓位，trend_weight 提高到0.8让趋势信号更主导，减少"漏趋势"。
    trend_weight: float = 0.8                 # 趋势 vs Carry 的最终合成权重
    carry_weight: float = 0.2
    # 短趋势(1H)权重调高：1H比4H更快对新趋势的启动做出反应，主趋势(4H)仍保留0.4权重防止纯噪声驱动，
    # 但让策略整体更快进入刚形成的趋势，而不是等4H信号也确认后才半路上车。
    short_trend_weight: float = 0.6           # 趋势内部: 1H(短趋势) vs 4H(主趋势) 权重
    main_trend_weight: float = 0.4

    # ---- EWMAC 趋势 ----
    ewmac_horizons: List[tuple] = field(default_factory=lambda: list(_DEFAULT_EWMAC_HORIZONS))
    ewma_lambda: float = 0.94                 # 波动率/协方差EWMA衰减因子(RiskMetrics经典默认值)
    # 预测缩放回看窗口缩短(2500→1500根)：causal rolling normalization 的"标定基准"更快跟上最近的
    # 波动率环境，避免用几个月前、可能完全不同波动率环境下的均值当分母，压低了当前这一波趋势的forecast强度。
    forecast_scale_lookback: int = 1500       # forecast scaling 用的滚动窗口(纯因果，不看未来)
    forecast_scale_min_periods: int = 100
    fdm_max: float = 2.5                      # Forecast Diversification Multiplier 上限
    fdm_lookback: int = 500
    fdm_min_periods: int = 60

    # ---- 大周期 Regime 过滤(1D) ----
    regime_ema_fast: int = 21
    regime_ema_slow: int = 55
    regime_ema_long: int = 200
    regime_adx_period: int = 14
    # ADX趋势判定门槛调低(20→15)：门槛越高，越多真实在萌芽期的趋势会被误判成"震荡市"进而被压制；
    # 调低门槛让更多真实趋势更早被识别为"趋势市"，避免刚起步的趋势因为regime还没跟上而被砍仓位。
    regime_adx_trend_threshold: float = 15.0
    # 逆势/震荡衰减系数都调松：regime是日线级别的判断，天然滞后于1H/4H趋势信号，新趋势刚启动时
    # regime可能还没转向、甚至还在原来的震荡/反向状态里——压得太死正好会错过趋势最早、往往也是
    # 最赚钱的一段。调松之后regime过滤依然在，只是不会一上来就把仓位砍掉一半以上。
    regime_oppose_dampen: float = 0.5         # regime方向与趋势预测相反时的衰减系数
    regime_range_dampen: float = 0.8          # 震荡regime下对趋势预测的整体衰减系数

    # ---- Carry ----
    carry_scale_lookback: int = 1000


    # ---- 组合层风险分配 / 波动率目标 ----
    target_annual_vol_pct: float = 15.0       # 组合目标年化波动率
    covariance_interval: str = "4h"           # 组合协方差计算用的K线周期: "4h" 或 "1d"
    # ⚠️ 杠杆/敞口上限适度放宽：让真正被高置信度识别出的强趋势能拿到更接近目标仓位的实际仓位，
    # 而不是提前被约束砍掉一部分、"赚得不够多"。这两个改动会直接提高最大回撤/爆仓风险，
    # 建议先用回测/模拟盘观察一段时间，觉得风险偏大可以随时在设置页调回3.0/40.0。
    max_leverage: float = 4.0                 # 组合总名义敞口 / 权益 的杠杆上限(硬约束)
    max_instrument_exposure_pct: float = 55.0  # 单标的名义敞口占权益上限
    max_correlated_group_exposure_pct: float = 60.0  # 同相关分组名义敞口占权益上限
    # 调仓缓冲区。这个值是相对"满预测(F=10)时的仓位规模"来算的，所以 6% 实际上只相当于
    # forecast 抖动 0.6 个单位就触发一次调仓——而 forecast 每根1H K线都会重算，
    # 结果就是海量零信息交易。实测(90天双标的、多随机路径)：
    #     6%  -> 116笔  年化换手61  手续费76   毛利618
    #     25% ->  29笔  年化换手38  手续费47   毛利951
    # 注意毛利也变好了：频繁再平衡不只是费钱，它在系统性地砍掉盈利仓位——
    # 价格上涨→持仓名义值变大→触发"再平衡减仓"→在上涨途中不断卖出。
    # 20%~30% 是一片平坦的最优区间(不是尖峰)，取中间值25%。
    no_trade_buffer_pct: float = 25.0         # 目标仓位相对当前仓位变化小于这个比例则不调仓(降低换手)
    exit_buffer_multiplier: float = 3.0       # 减仓/平仓比加仓更"迟钝"：同方向减仓、或平到0仓位时，
                                                # 实际用的缓冲区是 no_trade_buffer_pct * 这个倍数(默认3倍)，
                                                # 加仓/开仓仍然用原始的no_trade_buffer_pct，灵敏度不变。
                                                # 目的：forecast只是短暂走弱、趋势本身没走完时，不要立刻削减仓位，
                                                # 让趋势有机会走满；只有forecast真的明显走弱/反转才会真正减仓/平仓
                                                # (设为1.0等价于旧行为，加减仓用同一个缓冲区)。
    invert_direction: bool = False            # ⚠️ 反向执行：预测/波动率目标/组合风险分配/约束/防抖 全部照常计算，
                                                # 只在最后下单这一步把方向对调(算出来该开多就实际开空，反之亦然)。
                                                # 平仓方向由持仓方向决定，也会自动跟着倒过来，不需要额外处理。
                                                # 这是人工干预开关，不代表模型认为这样更对，开启前务必先用回测验证。

    # ---- 账户接管边界（默认最保守：只管自己开的仓）----
    manage_existing_positions: bool = False   # ⚠️ 是否接管"不是本程序开的"已有持仓。
                                                # 默认 false：程序只管理自己开过的仓位，
                                                # 你手动开的单一律不碰、不平、不调整，只在网页上列出来提示；
                                                # 存在外部持仓的标的会被整体跳过交易，避免双向持仓模式下
                                                # 策略的仓和你的仓合并成同一条腿，之后策略平仓把你的仓一起平掉。
                                                # 设为 true 才恢复"启动即接管整个账户"的旧行为。
    auto_close_removed_symbols: bool = False  # ⚠️ 从标的池里删掉某个标的后，它的遗留持仓怎么处理。
                                                # 默认 false：只在网页上提示，等你点"确认平仓"再平。
                                                # 设为 true 则由程序自动市价平掉(旧行为)。

    # ---- 执行节奏 ----
    tick_interval_sec: int = 900              # 主循环复核间隔(默认15分钟)
    short_trend_interval: str = "1h"
    main_trend_interval: str = "4h"
    regime_interval: str = "1d"
    min_bars_short: int = 300
    min_bars_main: int = 300
    min_bars_regime: int = 220

    # ---- 高波动震荡自适应风险覆盖层 ----
    # 只在“短期影线波动率突增 + 价格路径方向效率低”时缩小最终目标仓位；
    # 不修改 EWMAC/Carry 信号方向，高波动但方向明确的趋势仍保留完整风险预算。
    adaptive_risk_enabled: bool = True
    adaptive_er_lookback: int = 24            # 1H根数；24=近24小时价格方向效率
    adaptive_er_full_risk: float = 0.35       # ER达到此值时视为方向足够清晰，不降风险
    adaptive_vol_fast_lambda: float = 0.75    # 1H Rogers-Satchell 影线波动率快EWMA
    adaptive_vol_slow_lambda: float = 0.995   # 慢EWMA(约6天半衰期)，避免乱扎持续两天后就被当成“新常态”
    adaptive_vol_ratio_start: float = 1.10    # 快/慢波动率比从此开始缩风险
    adaptive_vol_ratio_full: float = 1.60     # 快/慢比到此视为完整波动压力
    adaptive_max_risk_reduction: float = 0.65 # 最多减65%，即仍保留原目标仓位的35%
    adaptive_multiplier_smoothing_span: int = 4  # 对乘数做4根1H EWM平滑，减少来回调仓
    adaptive_fast_reduce_threshold: float = 0.45 # 仅极端状态绕过3倍退出缓冲，避免换手/费用反噬

    # ---- 执行层盘口保护（只约束如何成交，不参与趋势/Carry方向判断） ----
    depth_guard_enabled: bool = True
    depth_levels: int = 20
    max_entry_spread_bps: float = 5.0
    max_entry_slippage_bps: float = 8.0
    min_depth_fill_ratio: float = 1.0

    @classmethod
    def build(cls, d: Dict[str, Any]) -> "SystematicConfig":
        base = cls()
        d = d or {}
        for k in base.__dataclass_fields__.keys():
            if k in d:
                if k == "ewmac_horizons":
                    setattr(base, k, _as_horizon_tuples(d[k]))
                else:
                    setattr(base, k, d[k])
        return base
