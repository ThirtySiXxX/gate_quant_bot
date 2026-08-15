"""
线程安全的全局运行状态 + SQLite 持久化。

engine 线程写入，网页仪表盘线程只读，所有读写都过 RLock，避免脏读。

双向持仓改造：positions 现在按 "symbol|side" 复合键存储（同一个symbol可以
同时存在 long 和 short 两条腿），role 字段区分是策略主仓(primary)还是
对冲仓(hedge)。

模拟盘/实盘账本完全隔离：模拟盘的权益是虚拟资金（比如默认1万U），实盘是账户
真实余额（可能只有几十几百U），如果两者共用同一份交易记录/权益曲线，会导致
"最大回撤"、"胜率"、"总盈亏"等统计出现荒谬的数字（比如从模拟盘的1万U"回撤"到
实盘的151U，显示回撤98%，但这只是数据口径污染，不是真的亏了98%）。
因此每个模式各自使用独立的 sqlite 文件（state_paper.sqlite3 / state_live.sqlite3），
切换模式(switch_mode)时会重新加载对应模式自己的历史记录，两边互不干扰。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import asdict
from typing import Dict, List, Optional

from .models import Position, Trade, now_ts


def _mode_db_path(base_path: str, mode: str) -> str:
    root, ext = os.path.splitext(base_path)
    if root.endswith(f"_{mode}"):
        return base_path
    return f"{root}_{mode}{ext or '.sqlite3'}"


class StateStore:
    def __init__(self, db_path: str, mode: str = "paper"):
        self._base_db_path = db_path
        self.db_path = _mode_db_path(db_path, mode)
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._lock = threading.RLock()

        self.mode = mode
        self.positions: Dict[str, Position] = {}      # "symbol|side" -> Position
        self.trades: List[Trade] = []                  # 已平仓交易历史(内存缓存，完整历史在sqlite)
        self.equity_curve: List[tuple] = []             # (timestamp, equity)
        self.equity: float = 0.0
        self.day_start_equity: float = 0.0
        self.day_start_ts: float = now_ts()
        self.started_at: float = now_ts()
        self.last_signals: Dict[str, dict] = {}         # symbol -> 最近一次信号快照(供界面展示)
        self.circuit_breaker_active: bool = False
        self.logs: List[str] = []                        # 最近N条日志，供界面展示
        self.errors: List[str] = []
        self.engine_running: bool = False
        self.engine_started_at: Optional[float] = None
        self.dual_mode_ready: bool = False
        self.portfolio_snapshot: dict = {}   # 新版系统性引擎用：组合层诊断信息(目标/实际波动率、杠杆、分散化收益等)

        self._init_db()
        self._load_trades_from_db()

    def switch_mode(self, new_mode: str):
        """切换 paper/live 模式对应的独立账本。会清空内存里的持仓/信号(不同模式的持仓没有意义)，
        并重新加载新模式自己的历史成交与权益曲线，避免两个模式的统计数据互相污染。"""
        with self._lock:
            self.mode = new_mode
            self.db_path = _mode_db_path(self._base_db_path, new_mode)
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            self.positions = {}
            self.trades = []
            self.equity_curve = []
            self.equity = 0.0
            self.day_start_equity = 0.0
            self.day_start_ts = now_ts()
            self.circuit_breaker_active = False
            self.last_signals = {}
            self.portfolio_snapshot = {}
        self._init_db()
        self._load_trades_from_db()
        self.add_log(f"已切换到 [{new_mode}] 模式的独立账本（{self.db_path}），历史统计与之前的模式互不影响")

    # ---------------------------------------------------------- DB
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY, symbol TEXT, side TEXT, size REAL,
                    entry_price REAL, exit_price REAL, open_time REAL, close_time REAL,
                    pnl REAL, gross_pnl REAL, fees_paid REAL, funding_paid REAL,
                    exit_reason TEXT, role TEXT DEFAULT 'primary'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS equity_curve (
                    ts REAL PRIMARY KEY, equity REAL
                )
            """)
            conn.commit()

    def _load_trades_from_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM trades ORDER BY close_time ASC").fetchall()
            for r in rows:
                keys = r.keys()
                self.trades.append(Trade(
                    id=r["id"], symbol=r["symbol"], side=r["side"], size=r["size"],
                    entry_price=r["entry_price"], exit_price=r["exit_price"],
                    open_time=r["open_time"], close_time=r["close_time"], pnl=r["pnl"],
                    gross_pnl=r["gross_pnl"], fees_paid=r["fees_paid"],
                    funding_paid=r["funding_paid"], exit_reason=r["exit_reason"],
                    role=(r["role"] if "role" in keys and r["role"] else "primary"),
                ))
            eq_rows = conn.execute("SELECT * FROM equity_curve ORDER BY ts ASC").fetchall()
            self.equity_curve = [(r["ts"], r["equity"]) for r in eq_rows]

    def persist_trade(self, t: Trade):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.id, t.symbol, t.side, t.size, t.entry_price, t.exit_price,
                 t.open_time, t.close_time, t.pnl, t.gross_pnl, t.fees_paid,
                 t.funding_paid, t.exit_reason, t.role),
            )
            conn.commit()

    def persist_equity_point(self, ts: float, equity: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO equity_curve VALUES (?,?)", (ts, equity))
            conn.commit()

    # ---------------------------------------------------------- 线程安全操作
    def with_lock(self):
        return self._lock

    def add_log(self, msg: str, level: str = "INFO"):
        with self._lock:
            line = f"[{time.strftime('%H:%M:%S')}] {level} {msg}"
            self.logs.append(line)
            self.logs = self.logs[-300:]
            if level == "ERROR":
                self.errors.append(line)
                self.errors = self.errors[-50:]

    def update_equity(self, equity: float):
        with self._lock:
            self.equity = equity
            ts = now_ts()
            self.equity_curve.append((ts, equity))
            self.equity_curve = self.equity_curve[-5000:]
        self.persist_equity_point(ts, equity)

        # 日切：过了24h重置当日起始权益
        with self._lock:
            if now_ts() - self.day_start_ts > 86400:
                self.day_start_equity = equity
                self.day_start_ts = now_ts()
                self.circuit_breaker_active = False

    # ---------------------------------------------------------- 持仓（双向）
    def upsert_position(self, pos: Position):
        with self._lock:
            self.positions[pos.position_key] = pos

    def remove_position(self, symbol: str, side: str) -> Optional[Position]:
        with self._lock:
            return self.positions.pop(f"{symbol}|{side}", None)

    def get_position(self, symbol: str, side: str) -> Optional[Position]:
        with self._lock:
            return self.positions.get(f"{symbol}|{side}")

    def get_primary(self, symbol: str) -> Optional[Position]:
        with self._lock:
            for p in self.positions.values():
                if p.symbol == symbol and p.role == "primary":
                    return p
        return None

    def get_by_id(self, position_id: str) -> Optional[Position]:
        with self._lock:
            for p in self.positions.values():
                if p.id == position_id:
                    return p
        return None

    def get_hedge_of(self, primary_id: str) -> Optional[Position]:
        with self._lock:
            for p in self.positions.values():
                if p.role == "hedge" and p.linked_id == primary_id:
                    return p
        return None

    def list_primaries(self) -> List[Position]:
        with self._lock:
            return [p for p in self.positions.values() if p.role == "primary"]

    def list_hedges(self) -> List[Position]:
        with self._lock:
            return [p for p in self.positions.values() if p.role == "hedge"]

    def record_trade(self, trade: Trade):
        with self._lock:
            self.trades.append(trade)
        self.persist_trade(trade)

    def set_signal(self, symbol: str, signal_dict: dict):
        with self._lock:
            self.last_signals[symbol] = signal_dict

    def set_portfolio_snapshot(self, snapshot: dict):
        with self._lock:
            self.portfolio_snapshot = snapshot

    # ---------------------------------------------------------- 统计
    def summary(self) -> dict:
        with self._lock:
            trades = list(self.trades)
            positions = dict(self.positions)
            equity = self.equity
            day_start_equity = self.day_start_equity
            engine_running = self.engine_running
            engine_started_at = self.engine_started_at

        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = sum(t.pnl for t in trades if t.pnl < 0)
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
        avg_holding = (sum(t.holding_seconds for t in trades) / len(trades)) if trades else 0.0
        open_fees = sum(p.fees_paid for p in positions.values())
        open_funding = sum(p.funding_paid for p in positions.values())
        total_fees = sum(t.fees_paid for t in trades) + open_fees
        total_funding = sum(t.funding_paid for t in trades) + open_funding
        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else (float("inf") if gross_profit > 0 else 0.0)

        hedge_trades = [t for t in trades if t.role == "hedge"]
        hedge_pnl_total = sum(t.pnl for t in hedge_trades)

        # 最大回撤
        eq_curve = self.equity_curve or [(now_ts(), equity)]
        peak = eq_curve[0][1]
        max_dd = 0.0
        for _, e in eq_curve:
            peak = max(peak, e)
            if peak > 0:
                dd = (peak - e) / peak * 100.0
                max_dd = max(max_dd, dd)

        unrealized = sum(p.unrealized_pnl for p in positions.values())
        day_pnl_pct = ((equity - day_start_equity) / day_start_equity * 100.0) if day_start_equity else 0.0

        primaries = [p for p in positions.values() if p.role == "primary"]
        hedges = [p for p in positions.values() if p.role == "hedge"]

        return {
            "mode": self.mode,
            "engine_running": engine_running,
            "engine_started_at": engine_started_at,
            "equity": equity,
            "unrealized_pnl": unrealized,
            "realized_pnl_total": total_pnl,
            # 未平仓的开仓费/资金费已经发生，必须和浮盈亏一起纳入。
            # funding_paid 为负数时表示收到资金费，减负数自然会增加净盈亏。
            "total_pnl": total_pnl + unrealized - open_fees - open_funding,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "trade_count": len(trades),
            "win_count": len(wins),
            "loss_count": len(losses),
            "avg_holding_seconds": avg_holding,
            "total_fees_paid": total_fees,
            "total_funding_paid": total_funding,
            "hedge_trade_count": len(hedge_trades),
            "hedge_pnl_total": hedge_pnl_total,
            "max_drawdown_pct": max_dd,
            "day_pnl_pct": day_pnl_pct,
            "open_position_count": len(primaries),
            "open_hedge_count": len(hedges),
            "uptime_seconds": now_ts() - self.started_at,
        }

    def positions_view(self) -> List[dict]:
        with self._lock:
            positions = list(self.positions.values())
        out = []
        for p in positions:
            out.append({
                "symbol": p.symbol, "side": p.side, "size": p.size,
                "entry_price": p.entry_price, "mark_price": p.mark_price,
                "stop_price": p.stop_price, "take_profit_1": p.take_profit_1,
                "leverage": p.leverage, "unrealized_pnl": p.unrealized_pnl,
                "holding_seconds": p.holding_seconds, "regime": p.regime,
                "tp1_done": p.tp1_done, "reason": p.reason,
                "role": p.role, "linked_id": p.linked_id, "id": p.id,
                "open_time": p.open_time,
            })
        return out

    def recent_trades_view(self, limit: int = 30) -> List[dict]:
        with self._lock:
            trades = list(self.trades[-limit:])
        return [asdict(t) for t in reversed(trades)]
