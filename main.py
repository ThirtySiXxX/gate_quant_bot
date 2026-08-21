#!/usr/bin/env python3
"""
Gate.io 多因子量化策略机器人 —— 图形化启动入口。

用法（正常情况下你不需要在终端输入任何东西，双击"启动.command"即可）：
    python main.py

启动后会自动打开浏览器，之后所有操作——填写API Key、选择模式、调整参数、
增删币种、启动/停止交易、下载历史K线做回测——全部在网页里用鼠标/键盘完成，
不需要再碰终端。

首次使用会自动从 config.example.yaml 生成 config.yaml，无需手动复制。
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import threading
import time
import webbrowser

# 确保无论从哪个目录启动，都能找到本目录下的 config.yaml / data/ 等文件
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from src.backtest_runner import BacktestController
from src.config import ConfigStore
from src.credentials import CredentialStore
from src.engine import EngineController
from src.state import StateStore


def setup_logging(log_path: str):
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def ensure_config_file(path: str):
    if os.path.exists(path):
        return
    example = os.path.join(SCRIPT_DIR, "config.example.yaml")
    if os.path.exists(example):
        shutil.copy(example, path)
        print(f">> 首次运行，已根据模板自动生成 {path}")
    else:
        raise SystemExit(f"找不到 {path} 也找不到 config.example.yaml，程序无法启动。")


def open_browser_later(url: str, delay: float = 1.5):
    def _run():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="Gate.io 多因子量化策略机器人（图形化版）")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--no-browser", action="store_true", help="启动后不要自动打开浏览器")
    parser.add_argument("--port", type=int, default=None, help="覆盖网页端口")
    args = parser.parse_args()

    ensure_config_file(args.config)
    config_store = ConfigStore(args.config)
    cfg = config_store.snapshot()

    storage_cfg = cfg.get("storage", {})
    web_cfg = cfg.get("web", {"enabled": True, "host": "127.0.0.1", "port": 8765})

    setup_logging(storage_cfg.get("log_path", "./data/bot.log"))
    logger = logging.getLogger("bot.main")

    cred_store = CredentialStore("./data/credentials.json")
    state = StateStore(storage_cfg.get("db_path", "./data/state.sqlite3"), mode=cfg.get("mode", "paper"))
    controller = EngineController(config_store, cred_store, state)
    # 回测控制器和实盘/模拟盘引擎完全独立（不同数据、不同线程），
    # 可以在引擎运行的同时随时在网页"回测"页发起回测任务。
    backtest_controller = BacktestController(
        config_store, cred_store,
        result_dir=storage_cfg.get("backtest_result_dir", "./data/backtests"),
        cache_dir=storage_cfg.get("kline_cache_dir", "./data/klines"),
    )

    host = web_cfg.get("host", "127.0.0.1")
    port = args.port or web_cfg.get("port", 8765)
    url = f"http://{host}:{port}"

    print("=" * 60)
    print("  Gate.io 多因子量化策略机器人 —— 图形化控制台")
    print(f"  正在启动网页界面: {url}")
    print("  接下来的所有操作（填写API Key、启停策略、调参、看盈亏、跑回测）")
    print("  都请在浏览器里完成，这个终端窗口不需要再输入任何命令，")
    print("  保持它开着即可（关闭窗口会停止程序）。")
    print("=" * 60)

    # 启动时在后台静默检查一次更新。刻意放在后台线程并全程吞异常——
    # 更新检查是锦上添花的功能，绝不能因为它失败/超时而拖慢或阻断交易程序启动。
    def _bg_check_update():
        try:
            from src import updater
            ucfg = cfg.get("update") or {}
            if not ucfg.get("auto_check", True):
                return
            info = updater.check_for_update(ucfg.get("repo") or None,
                                             ucfg.get("branch", "main"))
            if info.has_update and not info.skipped:
                state.add_log(f"发现新版本 {info.latest}（当前 {info.current}），"
                               f"可在「检查更新」页查看更新内容", "INFO")
        except Exception:
            pass
    threading.Thread(target=_bg_check_update, daemon=True, name="update-check").start()

    if not args.no_browser:
        open_browser_later(url)

    from src.dashboard_web import run_web_dashboard
    try:
        run_web_dashboard(state, config_store, cred_store, controller, backtest_controller, host=host, port=port)
    except KeyboardInterrupt:
        pass
    finally:
        if controller.is_running():
            controller.stop()
        print("\n程序已退出。持仓/成交历史已保存在 data/state.sqlite3 中，下次启动会自动读取。")


if __name__ == "__main__":
    main()
