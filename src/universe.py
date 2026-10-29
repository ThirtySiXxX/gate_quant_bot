"""Public-data universe and causal, cross-sectional candidate selection.

Huatai (2016), pp. 14, 17, 19-20: standardize, combine related factors,
rank, constrain the portfolio. This is an engineering adaptation, not a fitted
expected-return model. No account credentials, order methods or PnL optimizer.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import asdict
import json
import math
import re
import ssl
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import certifi
import numpy as np
import pandas as pd

from .config import CostConfig, SystematicConfig
from .trend import group_trend_forecast

MODEL_VERSION = "cross_section_v1"
SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9_]{0,59}_USDT$")
TOP_N = 5
MIN_TURNOVER = 1_000_000.0
MAX_PAIR_CORRELATION = 0.85
MAX_AGE_SECONDS = 900


def config_signature(cfg, costs):
    payload = json.dumps({"signal": asdict(cfg), "cost": asdict(costs)}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def number(value, default=math.nan):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def tradable_contract(contract):
    """Exchange catalogue is authoritative; no fixed coin allowlist."""
    return (bool(SYMBOL.fullmatch(str(contract.get("name", ""))))
            and contract.get("status") == "trading"
            and not contract.get("in_delisting", False)
            and not contract.get("is_pre_market", False)
            and contract.get("type") == "direct")


def is_crypto(contract):
    # Current Gate metadata distinguishes stocks, indices, metals, forex, etc.
    # Missing classification is not silently treated as crypto.
    return "contract_type" in contract and contract["contract_type"] in ("", "crypto")


class PublicMarket:
    """Fixed public GET endpoints only. Never instantiate an authenticated client."""
    def __init__(self, timeout=12):
        self.timeout = timeout
        self.context = ssl.create_default_context(cafile=certifi.where())

    def _get(self, endpoint, **params):
        url = "https://api.gateio.ws/api/v4/futures/usdt/" + endpoint
        if params:
            url += "?" + urlencode(params)
        with urlopen(url, timeout=self.timeout, context=self.context) as response:
            data = json.load(response)
        if not isinstance(data, list):
            raise ValueError("交易所行情响应格式错误")
        return data

    def contracts(self):
        return self._get("contracts")

    def tickers(self):
        return self._get("tickers")

    def candles(self, symbol, interval, limit):
        if not SYMBOL.fullmatch(symbol) or interval not in ("1h", "4h"):
            raise ValueError("不支持的行情请求")
        data = self._get("candlesticks", contract=symbol, interval=interval, limit=limit)
        return pd.DataFrame([{"timestamp": number(r.get("t")), "close": number(r.get("c"))}
                             for r in data])


def closed_prices(frame, seconds, as_of, minimum):
    """One common as-of boundary; reject gaps/stale bars instead of filling them."""
    if not {"timestamp", "close"}.issubset(frame.columns):
        raise ValueError("行情字段不完整")
    f = frame[["timestamp", "close"]].copy()
    f = f.apply(pd.to_numeric, errors="coerce")
    f = f[f.timestamp + seconds <= as_of].sort_values("timestamp")
    if f.timestamp.duplicated().any() or len(f) < minimum:
        raise ValueError("历史不足或时间戳重复")
    if not np.isfinite(f.to_numpy()).all() or (f.close <= 0).any():
        raise ValueError("行情包含无效价格")
    if (f.timestamp % seconds != 0).any() or (np.diff(f.timestamp) != seconds).any():
        raise ValueError("历史行情存在缺口")
    expected = math.floor(as_of / seconds) * seconds - seconds
    if f.timestamp.iloc[-1] != expected:
        raise ValueError("最近已收盘行情缺失")
    return pd.Series(f.close.to_numpy(), index=f.timestamp.to_numpy(dtype=np.int64))


def observation(symbol, frames, contract, ticker, as_of, cfg, costs):
    minimum = max(cfg.min_bars_short, cfg.min_bars_main,
                  cfg.forecast_scale_min_periods + cfg.fdm_min_periods + 5)
    h = closed_prices(frames[0], 3600, as_of, minimum)
    m = closed_prices(frames[1], 14400, as_of, minimum)
    fs = number(group_trend_forecast(h.reset_index(drop=True), "1h", cfg).iloc[-1])
    fm = number(group_trend_forecast(m.reset_index(drop=True), "4h", cfg).iloc[-1])
    if not math.isfinite(fs + fm) or fs * fm <= 0 or min(abs(fs), abs(fm)) < 2:
        raise ValueError("趋势方向未一致或强度不足")
    direction = 1 if fs > 0 else -1
    er = []
    for n in (24, 72):
        c = h.iloc[-n-1:]
        distance = c.diff().abs().sum()
        er.append(float(abs(c.iloc[-1] - c.iloc[0]) / distance) if distance > 0 else 0.)
    quality = sum(er) / len(er)
    if quality < 0.10:
        raise ValueError("价格路径过于震荡")
    returns = np.log(h).diff().dropna().tail(168)
    day_vol = float(returns.std(ddof=0) * math.sqrt(24))
    rate = number(ticker.get("funding_rate"))
    funding_interval = number(contract.get("funding_interval"))
    bid, ask = number(ticker.get("highest_bid")), number(ticker.get("lowest_ask"))
    if not all(math.isfinite(x) for x in (rate, funding_interval, bid, ask)) or funding_interval <= 0 or bid <= 0 or ask < bid:
        raise ValueError("资金费或报价缺失")
    spread = (ask-bid) / ((ask+bid)/2) * 10000
    # One-day funding is a scenario using current rate, not a prediction.
    funding_bps = max(0., direction * rate * 86400 / funding_interval * 10000)
    public_fee = number(contract.get("taker_fee_rate"), costs.taker_fee_rate)
    fee = max(costs.taker_fee_rate, public_fee, 0.)
    round_trip_bps = 2 * fee * 10000 + spread + 2 * costs.slippage_bps + funding_bps
    if day_vol <= 0 or not math.isfinite(day_vol):
        raise ValueError("波动率不可用")
    return {
        "symbol": symbol, "side": "long" if direction > 0 else "short",
        "short_forecast": fs, "main_forecast": fm,
        "trend": (abs(fs) + abs(fm)) / 2, "quality": quality,
        "cost": -round_trip_bps / (day_vol * 10000),
        "turnover_24h": number(ticker.get("volume_24h_quote")),
        "spread_bps": spread, "round_trip_cost_bps": round_trip_bps,
        "funding_1d_bps": funding_bps, "daily_vol_pct": day_vol * 100,
        "last_closed_1h": int(h.index[-1]), "last_closed_4h": int(m.index[-1]),
        "returns": returns,
    }


def rank_candidates(rows):
    """Rank standardization, equal category weights, then correlation constraint."""
    if not rows:
        return [], []
    df = pd.DataFrame([{k: r[k] for k in ("trend", "quality", "cost")} for r in rows])
    ranks = df.rank(method="average")
    std = ranks.std(ddof=0).replace(0, 1)
    z = (ranks - ranks.mean()) / std
    selected, excluded = [], []
    ordered = sorted(range(len(rows)), key=lambda i: (-float(z.iloc[i].mean()), rows[i]["symbol"]))
    for i in ordered:
        row = rows[i]
        correlations = []
        invalid = False
        for previous in selected:
            a = pd.concat([row["returns"], previous["returns"]], axis=1).dropna()
            corr = number(a.iloc[:, 0].corr(a.iloc[:, 1])) if len(a) >= 120 else math.nan
            if not math.isfinite(corr):
                invalid = True
                break
            correlations.append(abs(corr))
        if invalid or any(c > MAX_PAIR_CORRELATION for c in correlations):
            excluded.append({"symbol": row["symbol"], "reason": "与已选标的高度相关或相关性样本不足"})
            continue
        row = dict(row, score=float(z.iloc[i].mean()),
                   factor_scores={k: float(z.iloc[i][k]) for k in z.columns},
                   max_abs_correlation=max(correlations, default=0.))
        selected.append(row)
        if len(selected) == TOP_N:
            break
    return [{k: v for k, v in r.items() if k != "returns"} for r in selected], excluded


class UniverseService:
    """Single-flight background scan. Stale/error results cannot be applied."""
    def __init__(self, market=None, clock=time.time, snapshot_dir=None):
        self.market = market or PublicMarket()
        self.clock = clock
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else None
        self.lock = threading.RLock()
        self._catalogue_lock = threading.Lock()
        self._contracts = []
        self._catalogue_at = 0.
        self._generation = 0
        self._result = {"status": "idle", "candidates": [], "model_version": MODEL_VERSION}

    def catalogue(self):
        with self._catalogue_lock:
            if not self._contracts or self.clock() - self._catalogue_at >= 300:
                contracts = self.market.contracts()
                if not contracts:
                    raise ValueError("合约目录为空")
                self._contracts = contracts
                self._catalogue_at = self.clock()
            return copy.deepcopy(self._contracts)

    def validate_symbol(self, symbol):
        if not SYMBOL.fullmatch(symbol):
            raise ValueError("请输入有效的 USDT 永续合约代码")
        c = next((x for x in self.catalogue() if x.get("name") == symbol), None)
        if c is None or not tradable_contract(c):
            raise ValueError("该合约不存在、未开放交易或正在下架")
        return c

    def status(self):
        with self.lock:
            result = copy.deepcopy(self._result)
        result["stale"] = (result.get("status") != "done" or
                           self.clock() - result.get("as_of", 0) >= MAX_AGE_SECONDS)
        return result

    def start(self, cfg=None, costs=None, force=False):
        cfg, costs = copy.deepcopy(cfg or SystematicConfig()), copy.deepcopy(costs or CostConfig())
        with self.lock:
            if self._result["status"] == "running":
                return self.status()
            if (not force and not self.status()["stale"]
                    and self._result.get("config_signature") == config_signature(cfg, costs)):
                return self.status()
            self._generation += 1
            generation = self._generation
            self._result = {"status": "running", "candidates": [], "progress": 0,
                            "model_version": MODEL_VERSION, "as_of": self.clock()}
        threading.Thread(target=self._run, args=(cfg, costs, generation), daemon=True,
                         name="public-universe-scan").start()
        return self.status()

    def _run(self, cfg, costs, generation):
        try:
            result = self.scan(cfg, costs)
        except Exception as exc:
            result = {"status": "error", "candidates": [], "message": str(exc),
                      "model_version": MODEL_VERSION}
        with self.lock:
            if generation == self._generation:
                self._result = result

    def scan(self, cfg=None, costs=None):
        cfg, costs = cfg or SystematicConfig(), costs or CostConfig()
        if cfg.short_trend_interval != "1h" or cfg.main_trend_interval != "4h":
            raise ValueError("自动选币 v1 需要 1H/4H 趋势周期，请使用手动选币或恢复该周期")
        if cfg.invert_direction:
            raise ValueError("自动选币与反向执行不兼容，请恢复模型方向后再筛选")
        if not (math.isfinite(costs.taker_fee_rate) and costs.taker_fee_rate >= 0
                and math.isfinite(costs.slippage_bps) and costs.slippage_bps >= 0
                and math.isfinite(cfg.max_entry_spread_bps) and cfg.max_entry_spread_bps > 0):
            raise ValueError("费率、滑点或点差配置无效")
        as_of = self.clock()
        contracts = self.catalogue()
        tickers = {r["contract"]: r for r in self.market.tickers()}
        pool, rejected = [], []
        active = [c for c in contracts if tradable_contract(c) and is_crypto(c)]
        spread_limit = min(5., cfg.max_entry_spread_bps)
        for c in active:
            t = tickers.get(c["name"], {})
            bid, ask, turnover = (number(t.get(k)) for k in ("highest_bid", "lowest_ask", "volume_24h_quote"))
            if not all(math.isfinite(v) for v in (bid, ask, turnover)) or bid <= 0 or ask < bid:
                reason = "报价缺失"
            elif turnover < MIN_TURNOVER:
                reason = "24小时成交额不足100万USDT"
            elif (ask-bid) / ((bid+ask)/2) * 10000 > spread_limit:
                reason = "点差过大"
            else:
                pool.append((c, t)); continue
            rejected.append({"symbol": c["name"], "reason": reason})
        limit = min(2000, max(600, cfg.forecast_scale_lookback + 128,
                              cfg.min_bars_main + 1, cfg.min_bars_short + 1))
        def compute(pair):
            c, t = pair
            frames = [self.market.candles(c["name"], interval, limit) for interval in ("1h", "4h")]
            return observation(c["name"], frames, c, t, as_of, cfg, costs)
        rows = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(compute, p): p[0]["name"] for p in pool}
            for done, f in enumerate(as_completed(futures), 1):
                try:
                    rows.append(f.result())
                except Exception as exc:
                    rejected.append({"symbol": futures[f], "reason": str(exc)})
                with self.lock:
                    if self._result["status"] == "running":
                        self._result["progress"] = int(done * 100 / max(1, len(pool)))
        selected, diversified_out = rank_candidates(rows)
        rejected.extend(diversified_out)
        result = {"status": "done", "model_version": MODEL_VERSION, "scan_id": uuid.uuid4().hex,
                  "as_of": as_of, "finished_at": self.clock(), "progress": 100,
                  "config_signature": config_signature(cfg, costs),
                  "catalogue_count": len(contracts), "crypto_count": len(active),
                  "liquidity_count": len(pool), "factor_count": len(rows),
                  "candidates": selected, "rejected_counts": dict(Counter(x["reason"] for x in rejected)),
                  "message": "评分是当前相对适配度，不是胜率或收益预测；不足五个时不强行补足。",
                  "method": {"weights": {"trend": 1/3, "quality": 1/3, "cost": 1/3},
                             "min_turnover": MIN_TURNOVER, "max_spread_bps": spread_limit,
                             "max_abs_correlation": MAX_PAIR_CORRELATION,
                             "return_fit": False, "periods": ["1h", "4h"]}}
        if self.snapshot_dir:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            # Public evidence only: captured universe prevents silently reusing today's
            # survivors as a historical universe. These snapshots are not a backtest.
            evidence = dict(result, signal_config=asdict(cfg), cost_config=asdict(costs),
                            catalogue=contracts, tickers=list(tickers.values()),
                            factor_rows=[{k:v for k,v in r.items() if k!='returns'} for r in rows],
                            rejected=rejected)
            path = self.snapshot_dir / (result["scan_id"] + ".json")
            path.write_text(json.dumps(evidence, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        return result

    def selection(self, scan_id, cfg=None, costs=None):
        result = self.status()
        if result["stale"] or result.get("scan_id") != scan_id:
            raise ValueError("筛选结果已过期或扫描仍在进行，请重新筛选")
        if cfg is not None and result.get("config_signature") != config_signature(cfg, costs or CostConfig()):
            raise ValueError("策略或成本配置已改变，请重新筛选")
        symbols = [c["symbol"] for c in result["candidates"]]
        if not symbols:
            raise ValueError("当前没有合格候选")
        # Revalidate catalogue before use (including exchange delisting updates).
        for symbol in symbols:
            self.validate_symbol(symbol)
        return symbols
