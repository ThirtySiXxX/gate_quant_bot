"""
回测任务控制器：管理后台组合回测任务的生命周期(排队/下载数据/运行/完成)。

和实盘/模拟盘的 EngineController、StateStore 完全独立、不共享任何状态或数据库，
只用到只读的行情下载接口，因此可以在实盘引擎正在运行的同时，
随时在网页"回测"页发起新的回测任务，互不干扰、互不阻塞。

新版是"组合级"回测：一次任务对整个标的池（默认=当前配置的全部交易标的，
也可以只选其中几个）同时跑，直接复用生产环境的 vol/trend/carry/portfolio/backtest
模块，得到的是组合层面的权益曲线和统计指标，而不是逐个标的分开测。

每个任务在独立的后台线程里跑完整流程：连接交易所(只读) -> 为每个标的分页下载
短趋势/主趋势/regime/协方差 K线(本地CSV缓存) -> 调用 backtest.run_portfolio_backtest()
逐步走查 -> 把结果持久化为 JSON（data/backtests/<job_id>.json），网页界面轮询任务状态
显示进度，完成后展示组合权益曲线/统计指标/分标的贡献，任务历史重启程序后依然能看到。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import data_fetcher
from .backtest import SymbolBacktestInputs, run_portfolio_backtest
from .config import ConfigStore, CostConfig, SystematicConfig
from .credentials import CredentialStore

logger = logging.getLogger("bot.backtest_runner")


@dataclass
class BacktestJob:
    id: str
    symbols: List[str]
    days_back: float
    initial_capital: float
    walkforward: bool = False    # 是否额外做滚动样本外验证 + 趋势捕获诊断
    wf_folds: int = 5
    status: str = "pending"      # pending | fetching | running | done | error
    progress_pct: int = 0
    message: str = ""
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None

    def to_summary(self) -> dict:
        d = {
            "id": self.id, "symbols": self.symbols, "days_back": self.days_back,
            "initial_capital": self.initial_capital, "status": self.status,
            "walkforward": self.walkforward, "wf_folds": self.wf_folds,
            "progress_pct": self.progress_pct, "message": self.message,
            "created_at": self.created_at, "finished_at": self.finished_at,
            "error": self.error,
        }
        if self.result is not None:
            # trend_diagnosis 里的 episodes 明细比较大，列表页不需要，详情页(to_full)才给
            d["summary"] = {k: v for k, v in self.result.items()
                             if k not in ("trades", "equity_curve", "trend_diagnosis")}
            td = self.result.get("trend_diagnosis")
            if td:
                d["summary"]["trend_diagnosis"] = {k: v for k, v in td.items() if k != "episodes"}
        return d

    def to_full(self) -> dict:
        d = self.to_summary()
        if self.result is not None:
            d["trades"] = self.result.get("trades", [])
            d["equity_curve"] = self.result.get("equity_curve", [])
            if self.result.get("trend_diagnosis"):
                d["trend_diagnosis"] = self.result["trend_diagnosis"]
        return d


class BacktestController:
    """线程安全的回测任务管理器；同一时刻最多允许 MAX_CONCURRENT 个任务并行，
    避免同时发起过多下载对交易所接口造成压力。"""

    MAX_CONCURRENT = 2

    def __init__(self, config_store: ConfigStore, cred_store: CredentialStore,
                 result_dir: str = "./data/backtests", cache_dir: str = "./data/klines"):
        self.config_store = config_store
        self.cred_store = cred_store
        self.result_dir = result_dir
        self.cache_dir = cache_dir
        os.makedirs(result_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        self._lock = threading.RLock()
        self._jobs: Dict[str, BacktestJob] = {}
        self._load_persisted()

    # ------------------------------------------------------------------
    def _load_persisted(self):
        if not os.path.isdir(self.result_dir):
            return
        for fname in sorted(os.listdir(self.result_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.result_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                symbols = data.get("symbols")
                if symbols is None:  # 兼容旧版单标的任务留下的历史记录
                    symbols = [data.get("symbol")] if data.get("symbol") else []
                job = BacktestJob(
                    id=data["id"], symbols=symbols, days_back=data["days_back"],
                    initial_capital=data["initial_capital"],
                    walkforward=data.get("walkforward", False), wf_folds=data.get("wf_folds", 5),
                    status=data.get("status", "done"),
                    progress_pct=100 if data.get("status") == "done" else 0,
                    message=data.get("message", ""),
                    created_at=data.get("created_at", 0), finished_at=data.get("finished_at"),
                    result=data.get("result"), error=data.get("error"),
                )
                self._jobs[job.id] = job
            except Exception as e:
                logger.warning("加载历史回测结果失败 %s: %s", fname, e)

    def _persist(self, job: BacktestJob):
        path = os.path.join(self.result_dir, f"{job.id}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": job.id, "symbols": job.symbols, "days_back": job.days_back,
                    "initial_capital": job.initial_capital, "status": job.status,
                    "walkforward": job.walkforward, "wf_folds": job.wf_folds,
                    "message": job.message, "created_at": job.created_at,
                    "finished_at": job.finished_at, "result": job.result, "error": job.error,
                }, f, ensure_ascii=False)
        except Exception as e:
            logger.warning("保存回测结果失败: %s", e)

    def _active_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status in ("pending", "fetching", "running"))

    # ------------------------------------------------------------------
    def start_job(self, symbols: Optional[List[str]], days_back: float,
                  initial_capital: Optional[float] = None,
                  walkforward: bool = False, wf_folds: int = 5) -> BacktestJob:
        cfg = self.config_store.snapshot()
        if not symbols:
            symbols = list(cfg.get("symbols", []))
        symbols = [s.strip().upper() for s in symbols if s and s.strip()]
        symbols = list(dict.fromkeys(symbols))  # 去重，保持顺序
        if not symbols:
            raise RuntimeError("请至少选择一个要回测的合约代码（默认使用当前配置的交易标的池）")
        if days_back <= 0:
            raise RuntimeError("回测天数必须大于0")

        creds = self.cred_store.load()
        if not creds.is_set:
            raise RuntimeError("请先在“设置”页填写并保存 Gate.io API Key（下载历史行情需要，但回测只做只读查询，不会下单/不涉及资金）")

        with self._lock:
            if self._active_count() >= self.MAX_CONCURRENT:
                raise RuntimeError(f"当前已有 {self.MAX_CONCURRENT} 个回测任务在运行，请等待其中一个完成后再发起新的")

        settle = cfg.get("settle", "usdt")
        sys_cfg = SystematicConfig.build(cfg.get("systematic", {}))
        capital = initial_capital if (initial_capital and initial_capital > 0) else sys_cfg.initial_capital_usdt

        job = BacktestJob(id=uuid.uuid4().hex[:10], symbols=symbols, days_back=days_back,
                           initial_capital=capital, walkforward=bool(walkforward),
                           wf_folds=max(2, min(int(wf_folds or 5), 10)))
        with self._lock:
            self._jobs[job.id] = job

        t = threading.Thread(target=self._run_job, args=(job, settle, creds, cfg, sys_cfg, capital),
                              daemon=True, name=f"backtest-{job.id}")
        t.start()
        return job

    def _run_job(self, job: BacktestJob, settle: str, creds, cfg: dict,
                 sys_cfg: SystematicConfig, capital: float):
        try:
            from .exchange_gate import GateExchange

            job.status = "fetching"
            job.message = "正在连接交易所（只读行情）..."
            exchange = GateExchange(creds.api_key, creds.api_secret, settle=settle, host=creds.api_host)
            cost_cfg = CostConfig.build(cfg.get("costs", {}))

            short_sec = data_fetcher.INTERVAL_SECONDS.get(sys_cfg.short_trend_interval, 3600)
            main_sec = data_fetcher.INTERVAL_SECONDS.get(sys_cfg.main_trend_interval, 14400)
            cov_sec = data_fetcher.INTERVAL_SECONDS.get(sys_cfg.covariance_interval, main_sec)
            warmup_days_short = max(sys_cfg.forecast_scale_lookback,
                                    max(s for _, s in sys_cfg.ewmac_horizons) + sys_cfg.forecast_scale_min_periods) * short_sec / 86400.0
            warmup_days_main = max(sys_cfg.forecast_scale_lookback,
                                   max(s for _, s in sys_cfg.ewmac_horizons) + sys_cfg.forecast_scale_min_periods) * main_sec / 86400.0
            warmup_days_cov = max(100, sys_cfg.fdm_lookback) * cov_sec / 86400.0
            regime_days = job.days_back + sys_cfg.regime_ema_long + sys_cfg.regime_adx_period + 30
            test_start_ts = time.time() - job.days_back * 86400.0

            n_symbols = len(job.symbols)
            symbol_inputs = []
            fetch_warnings = []

            for i, symbol in enumerate(job.symbols):
                def progress(fetched, target, msg, _i=i):
                    stage_pct = fetched / max(target, 1)
                    job.progress_pct = min(int((_i + stage_pct) / max(n_symbols, 1) * 40), 40)
                    job.message = msg

                try:
                    contract_info = exchange.get_contract(symbol)
                    df_short = data_fetcher.fetch_candles(exchange, symbol, sys_cfg.short_trend_interval,
                                                            job.days_back + warmup_days_short,
                                                            cache_dir=self.cache_dir, progress_cb=progress)
                    df_main = data_fetcher.fetch_candles(exchange, symbol, sys_cfg.main_trend_interval,
                                                          job.days_back + warmup_days_main, cache_dir=self.cache_dir,
                                                          progress_cb=progress)
                    df_regime = data_fetcher.fetch_candles(exchange, symbol, sys_cfg.regime_interval,
                                                            regime_days, cache_dir=self.cache_dir, progress_cb=progress)
                    if sys_cfg.covariance_interval == sys_cfg.short_trend_interval:
                        df_cov = df_short
                    elif sys_cfg.covariance_interval == sys_cfg.main_trend_interval:
                        df_cov = df_main
                    else:
                        df_cov = data_fetcher.fetch_candles(exchange, symbol, sys_cfg.covariance_interval,
                                                             job.days_back + warmup_days_cov, cache_dir=self.cache_dir,
                                                             progress_cb=progress)
                except Exception as e:
                    fetch_warnings.append(f"{symbol} 下载历史数据失败，已跳过: {e}")
                    continue

                # 回测和实盘统一：所有指标只看已完整收盘K线，执行发生在下一根短周期K线开盘。
                df_short = data_fetcher.drop_unclosed_last_bar(df_short, sys_cfg.short_trend_interval)
                df_main = data_fetcher.drop_unclosed_last_bar(df_main, sys_cfg.main_trend_interval)
                df_regime = data_fetcher.drop_unclosed_last_bar(df_regime, sys_cfg.regime_interval)
                df_cov = data_fetcher.drop_unclosed_last_bar(df_cov, sys_cfg.covariance_interval)

                if len(df_short) < 20 or len(df_main) < 20:
                    fetch_warnings.append(f"{symbol} 拉取到的K线过少，已跳过")
                    continue

                # 真实历史资金费率：让回测的 carry 信号和资金费成本都按逐期真实费率计算，
                # 而不是拿"下载那一刻的实时费率"当常数贴一整段历史。拿不到就降级(backtest里会警告)。
                try:
                    funding_history = data_fetcher.fetch_funding_history(
                        exchange, symbol, job.days_back + max(warmup_days_short, warmup_days_main),
                        cache_dir=self.cache_dir, progress_cb=progress)
                except Exception as e:
                    funding_history = None
                    fetch_warnings.append(f"{symbol} 历史资金费率下载失败，将退回实时费率近似: {e}")

                try:
                    account_taker_rate = exchange.get_account_taker_fee_rate(symbol)
                except Exception as e:
                    account_taker_rate = None
                    fetch_warnings.append(f"{symbol} 账户实际费率读取失败，已按成本配置回退: {e}")

                symbol_inputs.append(SymbolBacktestInputs(
                    symbol=symbol, df_short=df_short, df_main=df_main, df_regime=df_regime, df_cov=df_cov,
                    funding_rate=float(contract_info.get("funding_rate") or 0.0),
                    funding_interval_sec=float(contract_info.get("funding_interval") or 28800),
                    quanto_multiplier=contract_info["quanto_multiplier"],
                    taker_fee_rate=cost_cfg.effective_taker_rate(
                        contract_info.get("taker_fee_rate"), account_taker_rate),
                    order_size_min=contract_info.get("order_size_min", 1),
                    funding_history=funding_history,
                    test_start_ts=test_start_ts,
                ))

            if not symbol_inputs:
                raise RuntimeError("所有标的都未能成功下载到可用历史数据，无法回测：" + "；".join(fetch_warnings))

            job.status = "running"

            def bt_progress(pct, msg):
                job.progress_pct = 40 + int(pct * 0.6)
                job.message = msg

            result = run_portfolio_backtest(symbol_inputs, sys_cfg, cost_cfg, capital, progress_cb=bt_progress)
            if fetch_warnings:
                result.warnings = fetch_warnings + result.warnings

            result_dict = result.to_dict()

            # 趋势捕获诊断：客观找出显著趋势段，逐段量化"漏没漏/拿没拿满/进晚了还是出早了"
            try:
                from .walkforward import diagnose_trend_capture
                price_by_symbol = {
                    sb.symbol: sb.df_short[
                        (sb.df_short["timestamp"] >= result.start_ts)
                        & (sb.df_short["timestamp"] <= result.end_ts)
                    ].reset_index(drop=True)
                    for sb in symbol_inputs
                }
                result_dict["trend_diagnosis"] = diagnose_trend_capture(
                    result, price_by_symbol, min_move_pct=8.0)
            except Exception as e:
                logger.warning("趋势捕获诊断失败: %s", e)
                result_dict["trend_diagnosis"] = {"episode_count": 0, "note": f"诊断失败: {e}"}

            # 滚动样本外验证(可选，比较耗时，所以做成开关)
            if job.walkforward:
                try:
                    from .walkforward import run_walk_forward
                    job.message = "正在做滚动样本外验证..."

                    def wf_progress(pct, msg):
                        job.progress_pct = 90 + int(pct * 0.1)
                        job.message = msg

                    wf = run_walk_forward(symbol_inputs, sys_cfg, cost_cfg, capital,
                                           n_folds=job.wf_folds, progress_cb=wf_progress)
                    result_dict["walkforward"] = wf.to_dict()
                except Exception as e:
                    logger.warning("滚动样本外验证失败: %s", e)
                    result_dict["walkforward"] = {"folds": [], "consistency_note": f"验证失败: {e}"}

            job.result = result_dict
            job.status = "done"
            job.progress_pct = 100
            job.message = "回测完成"
            job.finished_at = time.time()
        except Exception as e:
            logger.exception("回测任务失败 %s", job.id)
            job.status = "error"
            job.error = str(e)
            job.message = f"回测失败: {e}"
            job.finished_at = time.time()
        finally:
            self._persist(job)

    # ------------------------------------------------------------------
    def get_job(self, job_id: str) -> Optional[BacktestJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_summary() for j in jobs]

    def delete_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        path = os.path.join(self.result_dir, f"{job_id}.json")
        if os.path.exists(path):
            os.remove(path)
        return True
