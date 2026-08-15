"""
引擎生命周期管理——供网页界面调用："启动"/"停止"按钮背后真正创建/销毁交易线程的地方。

本文件只负责生命周期（创建交易所连接、双向持仓模式检查、模拟盘/实盘账本切换、
启停线程），具体的策略逻辑在 systematic_engine.py 的 SystematicEngine 里
（多资产 Trend + Carry + 波动率目标系统）。

旧版"15分钟多因子+双向对冲"的策略实现整体移到了 engine_legacy_hedge.py，
默认不再使用，但代码原样保留、可以随时参考或切回。
"""
from __future__ import annotations

import threading
from typing import Optional, Tuple

from .config import ConfigStore
from .credentials import CredentialStore
from .exchange_gate import GateExchange
from .exchange_paper import PaperExchange
from .models import now_ts
from .state import StateStore
from .systematic_engine import SystematicEngine


class EngineController:
    """供网页界面调用的引擎生命周期管理：启动/停止/状态查询。"""

    def __init__(self, config_store: ConfigStore, cred_store: CredentialStore, state: StateStore,
                 kline_cache_dir: str = "./data/klines"):
        self.config_store = config_store
        self.cred_store = cred_store
        self.state = state
        self.kline_cache_dir = kline_cache_dir
        self.engine: Optional[SystematicEngine] = None
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> Tuple[bool, str]:
        with self._lock:
            if self.is_running():
                return False, "引擎已在运行"

            cfg = self.config_store.snapshot()
            mode = cfg.get("mode", "paper")
            settle = cfg.get("settle", "usdt")
            creds = self.cred_store.load()
            if not creds.is_set:
                return False, "请先在“设置”页填写并保存 Gate.io API Key / Secret"

            # 模拟盘和实盘各自独立账本，切换模式(或重启同一模式)时都重新加载对应账本，
            # 避免模拟盘的虚拟资金和实盘的真实余额混在一起，导致盈亏/回撤统计失真
            self.state.switch_mode(mode)

            try:
                market_source = GateExchange(creds.api_key, creds.api_secret, settle=settle, host=creds.api_host)
            except Exception as e:
                return False, f"创建交易所连接失败: {e}"

            if mode == "live":
                exchange = market_source
                ok, msg = exchange.ensure_dual_mode()
                self.state.dual_mode_ready = ok
                self.state.add_log(f"双向持仓模式检查: {msg}", "INFO" if ok else "ERROR")
                if not ok:
                    return False, msg
            else:
                sys_cfg_raw = cfg.get("systematic", {})
                cost_cfg = cfg.get("costs", {})
                exchange = PaperExchange(
                    market_source,
                    initial_capital=sys_cfg_raw.get("initial_capital_usdt", 10000.0),
                    slippage_bps=cost_cfg.get("slippage_bps", 5.0),
                    taker_fee_rate=cost_cfg.get("taker_fee_rate", 0.0005),
                )
                exchange.ensure_dual_mode()
                self.state.dual_mode_ready = True

            self.engine = SystematicEngine(self.config_store, exchange, self.state,
                                            cache_dir=self.kline_cache_dir)
            self.thread = threading.Thread(target=self.engine.run, daemon=True, name="systematic-engine")
            self.state.engine_running = True
            self.state.engine_started_at = now_ts()
            self.thread.start()
            return True, f"引擎已启动（{'实盘 LIVE' if mode=='live' else '模拟盘 PAPER'}）"

    def stop(self) -> Tuple[bool, str]:
        with self._lock:
            if not self.is_running() or not self.engine:
                self.state.engine_running = False
                return False, "引擎未运行"
            self.engine.stop()
            self.thread.join(timeout=15)
            self.state.engine_running = False
            return True, "引擎已停止"

    def status(self) -> dict:
        return {
            "running": self.is_running(),
            "mode": self.config_store.snapshot().get("mode", "paper"),
            "started_at": self.state.engine_started_at,
        }
