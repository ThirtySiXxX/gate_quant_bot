"""终端实时仪表盘（基于 rich），展示持仓汇总/总盈亏/胜率/持仓时间等。"""
from __future__ import annotations

import time

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .state import StateStore

console = Console()


def _fmt_secs(s: float) -> str:
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h{m}m"
    if m:
        return f"{m}m{sec}s"
    return f"{sec}s"


def _color_num(v: float) -> str:
    return "green" if v >= 0 else "red"


def build_summary_panel(state: StateStore) -> Panel:
    s = state.summary()
    mode_tag = "[bold yellow]PAPER 模拟盘[/]" if s["mode"] == "paper" else "[bold red]LIVE 实盘[/]"
    cb = "[bold red]熔断中,已停止开新仓[/]" if state.circuit_breaker_active else "[green]正常[/]"

    t = Table.grid(padding=(0, 2))
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="left")
    t.add_column(justify="left")

    t.add_row(
        f"模式: {mode_tag}",
        f"账户权益: [bold]{s['equity']:.2f}[/] USDT",
        f"当日盈亏: [{_color_num(s['day_pnl_pct'])}]{s['day_pnl_pct']:.2f}%[/]",
        f"熔断状态: {cb}",
    )
    t.add_row(
        f"总盈亏(含浮盈): [{_color_num(s['total_pnl'])}]{s['total_pnl']:.2f}[/]",
        f"已实现盈亏: [{_color_num(s['realized_pnl_total'])}]{s['realized_pnl_total']:.2f}[/]",
        f"浮动盈亏: [{_color_num(s['unrealized_pnl'])}]{s['unrealized_pnl']:.2f}[/]",
        f"最大回撤: [red]{s['max_drawdown_pct']:.2f}%[/]",
    )
    t.add_row(
        f"总交易数: {s['trade_count']} (胜{s['win_count']}/负{s['loss_count']})",
        f"胜率: {s['win_rate']:.1f}%",
        f"盈亏比(PF): {s['profit_factor']:.2f}",
        f"平均持仓: {_fmt_secs(s['avg_holding_seconds'])}",
    )
    t.add_row(
        f"累计手续费: [red]{s['total_fees_paid']:.2f}[/]",
        f"累计资金费: [{_color_num(-s['total_funding_paid'])}]{s['total_funding_paid']:.2f}[/]",
        f"当前持仓数: {s['open_position_count']}",
        f"运行时长: {_fmt_secs(s['uptime_seconds'])}",
    )
    return Panel(t, title="策略总览", border_style="cyan")


def build_positions_table(state: StateStore) -> Table:
    t = Table(title="当前持仓", expand=True)
    for col in ["币种", "方向", "张数", "开仓价", "现价", "止损价", "TP1", "浮动盈亏",
                "持仓时长", "市场状态", "TP1已触发"]:
        t.add_column(col)
    for p in state.positions_view():
        color = "green" if p["unrealized_pnl"] >= 0 else "red"
        t.add_row(
            p["symbol"], "多" if p["side"] == "long" else "空", str(p["size"]),
            f"{p['entry_price']:.4f}", f"{p['mark_price']:.4f}", f"{p['stop_price']:.4f}",
            f"{p['take_profit_1']:.4f}", f"[{color}]{p['unrealized_pnl']:.2f}[/]",
            _fmt_secs(p["holding_seconds"]), p["regime"], "是" if p["tp1_done"] else "否",
        )
    return t


def build_signals_table(state: StateStore) -> Table:
    t = Table(title="最近信号扫描", expand=True)
    for col in ["币种", "方向", "评分", "市场状态", "净预期(R)", "原因"]:
        t.add_column(col)
    with state.with_lock():
        items = list(state.last_signals.items())
    for symbol, sig in items:
        color = "green" if sig["action"] == "long" else ("red" if sig["action"] == "short" else "white")
        t.add_row(
            symbol, f"[{color}]{sig['action']}[/]", f"{sig['score']:.0f}",
            sig["regime"], f"{sig['net_edge_r']:.2f}", (sig["reason"] or "")[:60],
        )
    return t


def build_trades_table(state: StateStore) -> Table:
    t = Table(title="最近成交记录", expand=True)
    for col in ["币种", "方向", "开仓价", "平仓价", "净盈亏", "手续费", "资金费", "持仓时长", "离场原因"]:
        t.add_column(col)
    for tr in state.recent_trades_view(15):
        color = "green" if tr["pnl"] >= 0 else "red"
        t.add_row(
            tr["symbol"], "多" if tr["side"] == "long" else "空",
            f"{tr['entry_price']:.4f}", f"{tr['exit_price']:.4f}",
            f"[{color}]{tr['pnl']:.2f}[/]", f"{tr['fees_paid']:.2f}", f"{tr['funding_paid']:.2f}",
            _fmt_secs(tr["close_time"] - tr["open_time"]), tr["exit_reason"],
        )
    return t


def build_logs_panel(state: StateStore) -> Panel:
    with state.with_lock():
        lines = state.logs[-12:]
    return Panel(Text("\n".join(lines) or "暂无日志"), title="运行日志", border_style="dim")


def render(state: StateStore) -> Group:
    return Group(
        build_summary_panel(state),
        build_positions_table(state),
        build_signals_table(state),
        build_trades_table(state),
        build_logs_panel(state),
    )


def run_terminal_dashboard(state: StateStore, refresh_sec: float = 2.0, stop_event=None):
    with Live(render(state), console=console, refresh_per_second=1 / max(refresh_sec, 0.5), screen=False) as live:
        while not (stop_event and stop_event.is_set()):
            live.update(render(state))
            time.sleep(refresh_sec)
