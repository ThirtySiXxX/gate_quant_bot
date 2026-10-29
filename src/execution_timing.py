"""Causal entry/exit policy shared by live execution and the backtester.

All features use completed candles. This is a deterministic timing model, not
a calibrated probability of profitability. It never selects margin mode.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, replace
import math
from typing import Optional
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimingConfig:
    enabled: bool = True
    symbols: tuple = ()
    entry_confirm_bars: int = 2
    min_entry_quality: float = 0.0
    min_entry_forecast: float = 0.0
    require_trend_agreement: bool = False
    require_breakout_in_noise: bool = False
    max_entry_extension_atr: float = 2.0
    chase_quality_threshold: float = 0.7
    weak_forecast: float = 2.0
    weak_quality: float = 0.35
    weak_confirm_bars: int = 3
    confirm_reversals: bool = True
    flatten_before_reverse: bool = True
    partial_rebalance: float = 0.5
    rearm_after_loss: bool = False
    trail_atr: float = 0.0
    trail_activation_atr: float = 2.0
    adverse_exit: bool = False


    def for_symbol(self, symbol: str):
        return replace(self, enabled=self.enabled and (not self.symbols or symbol in self.symbols))

    def __post_init__(self):
        if not isinstance(self.symbols,(tuple,list)) or not all(isinstance(s,str) for s in self.symbols):
            raise ValueError("symbols must be a list of contract names")
        for name in ('enabled','require_trend_agreement','require_breakout_in_noise','confirm_reversals','flatten_before_reverse','rearm_after_loss','adverse_exit'):
            if not isinstance(getattr(self,name),bool):
                raise ValueError(f'{name} must be boolean')
        for name in ('entry_confirm_bars','weak_confirm_bars'):
            value=getattr(self,name)
            if not isinstance(value,int) or isinstance(value,bool) or value < (1 if name=='weak_confirm_bars' else 0):
                raise ValueError(f'{name} must be a valid candle count')
        for name in ('min_entry_quality','chase_quality_threshold','weak_quality','partial_rebalance'):
            value=getattr(self,name)
            if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
                raise ValueError(f'{name} must be between zero and one')
        for name in ('min_entry_forecast','max_entry_extension_atr','weak_forecast','trail_atr','trail_activation_atr'):
            value=getattr(self,name)
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError(f'{name} must be finite and nonnegative')


def _runs(condition: pd.Series) -> pd.Series:
    yes=condition.fillna(False).astype(bool)
    return yes.astype(int).groupby((~yes).cumsum()).cumsum()


def timing_features(df: pd.DataFrame) -> pd.DataFrame:
    """Past-only recovery, path efficiency and extension features per candle."""
    c=df['close'].astype(float)
    tr=pd.concat([df.high-df.low,(df.high-c.shift()).abs(),(df.low-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/24,adjust=False,min_periods=24).mean()
    ema8=c.ewm(span=8,adjust=False,min_periods=8).mean()
    ema16=c.ewm(span=16,adjust=False,min_periods=16).mean()
    ers=[]
    for n,scale in [(24,.35),(72,.20),(168,.12)]:
        er=(c-c.shift(n)).abs()/c.diff().abs().rolling(n).sum().replace(0,np.nan)
        ers.append((er/scale).clip(0,1))
    quality=pd.concat(ers,axis=1).mean(axis=1).ewm(span=4,adjust=False).mean()
    hi=df.high.shift(1).rolling(3,min_periods=3).max()
    lo=df.low.shift(1).rolling(3,min_periods=3).min()
    return pd.DataFrame({
        'bar_ts':df.timestamp.astype(float), 'bar_seconds':df.timestamp.diff().rolling(5).median(), 'close':c, 'atr':atr,
        'quality':quality, 'extension':(c-ema16)/atr.replace(0,np.nan),
        'long_run':_runs((c>ema8)&(ema8>ema8.shift())),
        'short_run':_runs((c<ema8)&(ema8<ema8.shift())),
        'breakout_long':c>hi, 'breakout_short':c<lo,
        'recent_high':df.high.rolling(3,min_periods=3).max(),
        'recent_low':df.low.rolling(3,min_periods=3).min(),
    },index=df.index)


@dataclass
class TimingState:
    last_bar: float = -1.0
    weak_count: int = 0
    last_fill_bar: float = -1.0
    blocked_side: int = 0
    rearm_price: float = 0.0
    session_pnl: float = 0.0
    entry_price: float = 0.0
    best_close: float = 0.0


@dataclass(frozen=True)
class TimingDecision:
    target_notional: float
    force_rebalance: bool = False
    reason: str = ''


class ExecutionTiming:
    def __init__(self):
        self.states: dict[str,TimingState]={}

    def decide(self,symbol: str,target: float,current: float,forecast: float,
               short_forecast: float,main_forecast: float,
               feature: Optional[dict],cfg: TimingConfig) -> TimingDecision:
        if not cfg.enabled:return TimingDecision(target)
        # Missing input must never introduce risk; the original target can still
        # reduce a same-side position or close an opposite position.
        if not feature or not all(math.isfinite(float(feature.get(k,float('nan')))) for k in ('bar_ts','quality','extension','close','recent_high','recent_low')):
            safe=0.0 if current*target<=0 else math.copysign(min(abs(target),abs(current)),current)
            return TimingDecision(safe,False,'时机数据不足，仅允许减少风险')
        st=self.states.setdefault(symbol,TimingState())
        bar=float(feature['bar_ts'])
        q=float(feature['quality'])
        if bar<st.last_bar:
            safe=0.0 if current*target<=0 else math.copysign(min(abs(target),abs(current)),current)
            return TimingDecision(safe,False,'时机数据过期，仅允许减少风险')
        if bar!=st.last_bar:
            # Missing hours break a consecutive confirmation sequence.
            if st.last_bar>=0 and bar-st.last_bar>float(feature.get("bar_seconds",3600))+1:st.weak_count=0
            st.weak_count=st.weak_count+1 if abs(forecast)<cfg.weak_forecast and q<cfg.weak_quality else 0
            st.last_bar=bar
        if st.blocked_side and st.blocked_side*(float(feature['close'])-st.rearm_price)>0:
            st.blocked_side=0;st.rearm_price=0.0
        side=1 if target>0 else -1 if target<0 else 0
        old=1 if current>0 else -1 if current<0 else 0
        if current and st.entry_price > 0 and bar > st.last_fill_bar:
            close = float(feature['close'])
            st.best_close = max(st.best_close, close) if old > 0 else min(st.best_close, close)
            atr = float(feature.get('atr', 0.))
            if cfg.trail_atr > 0 and atr > 0 and old*(st.best_close-st.entry_price) >= cfg.trail_activation_atr*atr and old*(st.best_close-close) >= cfg.trail_atr*atr:
                return TimingDecision(0.0, True, '盈利后回撤达到ATR退出阈值')
        if current and cfg.adverse_exit and old*float(feature['extension']) < -.5 and old*short_forecast < 0:
            return TimingDecision(0.0, True, '价格与短趋势共同反向，退出')
        if current and st.weak_count>=cfg.weak_confirm_bars:
            return TimingDecision(0.0,True,'低质量弱信号持续确认，退出')
        if current and target==0:return TimingDecision(target)
        if current*target<0:
            recovery=int(feature['long_run' if side>0 else 'short_run'])
            if cfg.confirm_reversals and recovery<cfg.entry_confirm_bars:
                return TimingDecision(current,False,'反向恢复尚未确认，保持原仓')
            if cfg.flatten_before_reverse:
                return TimingDecision(0.0,True,'反向信号确认，先平后开')
        if st.last_fill_bar==bar:
            return TimingDecision(current,False,'本根信号已执行，等待新收盘K线')
        new_direction=current==0 or current*target<0
        if new_direction and side:
            if cfg.rearm_after_loss and st.blocked_side==side:
                return TimingDecision(0.0,bool(current),'亏损后等待新的价格突破')
            if abs(forecast)<cfg.min_entry_forecast:
                return TimingDecision(0.0,bool(current),"信号幅度不足，暂缓入场")
            if q<cfg.min_entry_quality:
                return TimingDecision(0.0,bool(current),'路径质量不足，暂缓入场')
            if int(feature['long_run' if side>0 else 'short_run'])<cfg.entry_confirm_bars:
                return TimingDecision(0.0,bool(current),'短期价格恢复尚未确认')
            if cfg.require_trend_agreement and not(side*short_forecast>0 and side*main_forecast>0):
                return TimingDecision(0.0,bool(current),'短长周期方向未一致')
            if cfg.require_breakout_in_noise and q<cfg.chase_quality_threshold and not bool(feature['breakout_long' if side>0 else 'breakout_short']):
                return TimingDecision(0.0,bool(current),'噪声环境等待局部突破')
            if side*float(feature['extension'])>cfg.max_entry_extension_atr and q<cfg.chase_quality_threshold:
                return TimingDecision(0.0,bool(current),'入场偏离过大，暂缓追价')
        return TimingDecision(target)

    @staticmethod
    def execution_target(decision: TimingDecision,current: float,cfg: TimingConfig) -> float:
        target=decision.target_notional
        if cfg.enabled and not decision.force_rebalance and current*target>0:
            alpha=min(max(cfg.partial_rebalance,0.0),1.0)
            return current+alpha*(target-current)
        return target

    def record_fill(self,symbol: str,bar_ts: float,pnl: float=0.,closed: bool=False,
                    side: int=0,feature: Optional[dict]=None,entry_price: float=0.):
        st=self.states.setdefault(symbol,TimingState())
        st.last_fill_bar=bar_ts
        st.session_pnl+=pnl
        if entry_price > 0 and st.entry_price == 0:
            st.entry_price = entry_price
            st.best_close = entry_price
        if closed:
            if st.session_pnl<0 and feature:
                st.blocked_side=side
                st.rearm_price=float(feature['recent_high' if side>0 else 'recent_low'])
            st.session_pnl=0.
            st.entry_price=0.
            st.best_close=0.

    def dump(self) -> dict:
        return {symbol:asdict(state) for symbol,state in self.states.items()}

    def restore(self,data: dict):
        if not isinstance(data, dict):
            raise ValueError('Invalid saved execution timing state')
        restored = {}
        for symbol, raw in data.items():
            if not isinstance(raw, dict) or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in raw.values()):
                raise ValueError('Invalid saved execution timing state')
            st = TimingState(**{k:v for k,v in raw.items() if k in TimingState.__dataclass_fields__})
            if st.blocked_side not in (-1,0,1) or st.weak_count < 0 or int(st.weak_count) != st.weak_count:
                raise ValueError('Invalid saved execution timing state')
            restored[symbol] = st
        self.states = restored
