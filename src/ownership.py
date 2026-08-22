"""
持仓归属登记：区分"引擎自己开的仓"和"账户上本来就有的仓"。

为什么需要这个：
交易所接口只会告诉你"这个合约有多少仓位"，不会告诉你这仓位是谁开的。
如果不做区分，程序一启动就会把账户上所有仓位当成自己的来管理——
不在标的池里的直接市价平掉，在标的池里的按策略目标调整方向和大小。
对手动开过单的用户来说，这等于"启动即接管整个账户"，是实打实的资金风险。

做法：引擎每次成功开仓时把 (symbol, side) 记到这里，完全平仓时删掉。
下次同步持仓时，凡是登记里没有的就判定为"外部持仓"，默认不碰。

必须持久化到磁盘：程序重启后如果记录丢了，自己开的仓会被误判成外部持仓
而失去管理（那样反而更糟——仓位没人看着了）。按运行模式分文件存，
模拟盘和实盘互不干扰。
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Set, Tuple

logger = logging.getLogger("bot.ownership")

_LOCK = threading.RLock()


def _path(data_dir: str, mode: str) -> str:
    return os.path.join(data_dir, f"owned_positions_{mode}.json")


def _key(symbol: str, side: str) -> str:
    return f"{symbol}|{side}"


def _load(data_dir: str, mode: str) -> Set[str]:
    try:
        with open(_path(data_dir, mode), "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("owned", []))
    except (OSError, json.JSONDecodeError, AttributeError):
        return set()


def _save(data_dir: str, mode: str, owned: Set[str]) -> None:
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(_path(data_dir, mode), "w", encoding="utf-8") as f:
            json.dump({"owned": sorted(owned)}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        # 写不进去只记日志，不能因此中断交易流程；最坏情况是重启后把自己的仓
        # 当成外部仓，届时用户可以在界面上手动"纳入管理"
        logger.warning("保存持仓归属记录失败: %s", e)


def mark_owned(data_dir: str, mode: str, symbol: str, side: str) -> None:
    with _LOCK:
        owned = _load(data_dir, mode)
        owned.add(_key(symbol, side))
        _save(data_dir, mode, owned)


def unmark(data_dir: str, mode: str, symbol: str, side: str) -> None:
    with _LOCK:
        owned = _load(data_dir, mode)
        owned.discard(_key(symbol, side))
        _save(data_dir, mode, owned)


def is_owned(data_dir: str, mode: str, symbol: str, side: str) -> bool:
    with _LOCK:
        return _key(symbol, side) in _load(data_dir, mode)


def list_owned(data_dir: str, mode: str) -> Set[str]:
    with _LOCK:
        return _load(data_dir, mode)


def adopt(data_dir: str, mode: str, symbol: str, side: str) -> None:
    """用户在界面上明确点了"纳入策略管理"，把外部持仓登记为引擎自己的。"""
    mark_owned(data_dir, mode, symbol, side)


def adopt_all(data_dir: str, mode: str, pairs) -> int:
    with _LOCK:
        owned = _load(data_dir, mode)
        before = len(owned)
        for symbol, side in pairs:
            owned.add(_key(symbol, side))
        _save(data_dir, mode, owned)
        return len(owned) - before
