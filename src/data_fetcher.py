"""
历史K线批量下载模块，专供图形化界面的"回测"页使用。

设计要点：
  1) 完全只读行情接口，不碰任何下单/账户写操作，因此可以在实盘引擎正在运行的
     同时随时发起回测下载，两者互不干扰（不同线程、不共享任何交易状态）。
  2) Gate.io 单次K线请求有根数上限，这里保守按 PAGE_LIMIT 分页，用 `to` 时间戳
     不断向更早的时间翻页，直到覆盖用户要求的天数或者交易所没有更早数据为止。
  3) 本地按 合约+周期 缓存成 CSV（data/klines/ 目录）。重复对同一标的回测时，
     只需要补最新的一小段增量数据，不用每次都从头重新下载几个月的历史，
     大幅减少等待时间和对交易所接口的压力。
"""
from __future__ import annotations

import logging
import os
import time
from typing import Callable, Optional

import pandas as pd

try:
    from gate_api.exceptions import ApiException, GateApiException
except ImportError:  # 允许在未安装 gate-api 时仍能 import 本模块做静态检查
    ApiException = Exception
    GateApiException = Exception

logger = logging.getLogger("bot.data_fetcher")

INTERVAL_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "4h": 14400, "8h": 28800, "1d": 86400,
}

PAGE_LIMIT = 1000          # 每页请求的K线根数（保守值）
REQUEST_SLEEP_SEC = 0.2    # 分页请求之间的间隔，避免触发交易所限频
MAX_PAGES = 500             # 安全阀，防止意外死循环
FUNDING_HISTORY_MAX_DAYS = 180

# Gate 对每个周期能查询的历史深度有硬性上限（目前是最近约10000根K线，
# 超过范围会直接报错 INVALID_PARAM_VALUE / "Candlestick too long ago"），
# 不是分页能绕过的限制，遇到时应当把它当作"已到达交易所允许的最早历史"处理，
# 而不是当成异常让整个回测任务失败。
EXCHANGE_MAX_POINTS = 10000

_EMPTY_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

ProgressCB = Optional[Callable[[int, int, str], None]]


class HistoryLimitReached(Exception):
    """交易所返回"历史数据超出可查询范围"时抛出，用于让上层区分"正常到底"和"真正的接口错误"。"""


def max_days_for_interval(interval: str) -> float:
    """交易所对该周期允许查询的最大历史天数（近似值，留一点安全余量）。"""
    interval_sec = INTERVAL_SECONDS.get(interval, 900)
    return EXCHANGE_MAX_POINTS * interval_sec / 86400.0 * 0.97


def drop_unclosed_last_bar(df: pd.DataFrame, interval: str, now: Optional[float] = None) -> pd.DataFrame:
    """K线接口通常会把"当前正在走的这一根"也一起返回——这一根还没收盘，high/low/close/volume
    会随时间推移持续变化，同一根K线在不同时刻被查询到的值是不一样的。

    实盘信号计算(EWMAC/波动率/carry)如果直接用这根未收盘K线：
      1) 同一根K线内会因为价格波动反复触发信号变化，造成"同一根K线看起来产生了好几次开平仓"；
      2) 和回测的口径不一致——回测只处理已经走完的历史K线，永远不会看到"半根"K线。

    这里按"这根K线的结束时间是否已经过去"过滤掉还没走完的最后一根，只保留已收盘的K线用于
    信号计算。注意：这只应该在"算信号"的路径上调用，K线图表展示用的数据不需要(也不应该)
    砍掉最新这根——用户在图表上本来就期望能看到当前正在走的K线，和大多数行情软件一致。
    """
    if len(df) == 0:
        return df
    interval_sec = INTERVAL_SECONDS.get(interval, 900)
    now = now if now is not None else time.time()
    last_ts = float(df["timestamp"].iloc[-1])
    if last_ts + interval_sec > now:
        return df.iloc[:-1].reset_index(drop=True)
    return df


def _cache_path(cache_dir: str, contract: str, interval: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    safe_contract = contract.replace("/", "_")
    return os.path.join(cache_dir, f"{safe_contract}_{interval}.csv")


def _load_cache(cache_dir: str, contract: str, interval: str) -> pd.DataFrame:
    path = _cache_path(cache_dir, contract, interval)
    if not os.path.exists(path):
        return pd.DataFrame(columns=_EMPTY_COLUMNS)
    try:
        df = pd.read_csv(path)
        if "timestamp" not in df.columns:
            return pd.DataFrame(columns=_EMPTY_COLUMNS)
        return df.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    except Exception as e:
        logger.warning("读取K线缓存失败 %s: %s", path, e)
        return pd.DataFrame(columns=_EMPTY_COLUMNS)


def _save_cache(cache_dir: str, contract: str, interval: str, df: pd.DataFrame) -> None:
    path = _cache_path(cache_dir, contract, interval)
    try:
        df.sort_values("timestamp").drop_duplicates("timestamp", keep="last").to_csv(path, index=False)
    except Exception as e:
        logger.warning("写入K线缓存失败 %s: %s", path, e)


def read_cached_candles(cache_dir: str, contract: str, interval: str,
                         start_ts: Optional[float] = None, end_ts: Optional[float] = None) -> pd.DataFrame:
    """只读本地K线缓存(不发起任何网络请求)，专供网页"K线图"页面展示回测区间的K线背景用——
    这份数据在对应的回测任务下载数据时已经缓存到本地了(data/klines/下的CSV)，
    直接读缓存最快，也不会对交易所接口造成额外压力。取不到数据返回空DataFrame，
    调用方应据此判断"还没缓存过这个标的/周期"并提示用户。"""
    df = _load_cache(cache_dir, contract, interval)
    if len(df) == 0:
        return df
    if start_ts is not None:
        df = df[df["timestamp"] >= start_ts]
    if end_ts is not None:
        df = df[df["timestamp"] <= end_ts]
    return df.reset_index(drop=True)


def fetch_funding_history(exchange, contract: str, days_back: float,
                           cache_dir: str = "./data/klines", use_cache: bool = True,
                           progress_cb: ProgressCB = None) -> pd.DataFrame:
    """拉取最近 days_back 天的历史资金费率(自动向历史翻页 + 本地CSV缓存)。

    回测里的 carry 信号应该用这份真实的逐期历史费率，而不是"下载那一刻的实时费率"
    当常数——资金费率在行情转换时经常反号甚至数量级变化，用常数近似会让 carry 的
    历史贡献严重失真。

    返回 DataFrame(columns=[timestamp, funding_rate])，按时间升序；
    取不到数据(接口不支持/该合约没有历史)时返回空表，调用方应回退到实时费率近似。
    """
    now_ts = int(time.time())
    earliest_needed = now_ts - int(days_back * 86400)
    # Gate 拒绝 from 早于最近180天的请求。保留用户真正需要的 earliest_needed 用于
    # 最终裁剪，但请求起点夹到限制以内；若本地缓存有更早记录，仍会一并保留使用。
    earliest_query = max(earliest_needed, now_ts - FUNDING_HISTORY_MAX_DAYS * 86400 + 300)
    cache_key = "funding"

    cached = _load_cache(cache_dir, contract, cache_key) if use_cache else pd.DataFrame(columns=["timestamp", "funding_rate"])
    if len(cached) > 0 and "funding_rate" not in cached.columns:
        cached = pd.DataFrame(columns=["timestamp", "funding_rate"])

    chunks = [cached] if len(cached) > 0 else []
    # 已经覆盖到足够早的历史时，只需要补最新的一段
    need_deep_history = not (len(cached) > 0 and cached["timestamp"].min() <= earliest_query)
    to_cursor = now_ts

    for page_i in range(MAX_PAGES):
        try:
            page = exchange.get_funding_rate_history(contract, from_ts=earliest_query,
                                                      to_ts=to_cursor, limit=1000)
        except Exception as e:
            if progress_cb:
                progress_cb(0, 0, f"{contract} 获取历史资金费率失败({e})，将回退用实时费率近似")
            logger.warning("获取历史资金费率失败 %s: %s", contract, e)
            break
        if page is None or len(page) == 0:
            break
        chunks.append(page)
        oldest = int(page["timestamp"].min())
        if progress_cb:
            progress_cb(0, 0, f"{contract} 已下载资金费率历史至 {pd.to_datetime(oldest, unit='s')}")
        if oldest <= earliest_query or not need_deep_history or len(page) < 2:
            break
        to_cursor = oldest - 1
        time.sleep(REQUEST_SLEEP_SEC)

    if not chunks:
        return pd.DataFrame(columns=["timestamp", "funding_rate"])
    df = pd.concat(chunks, ignore_index=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if use_cache and len(df) > 0:
        _save_cache(cache_dir, contract, cache_key, df)
    return df[df["timestamp"] >= earliest_needed].reset_index(drop=True)


def _fetch_page(exchange, contract: str, interval: str, limit: int,
                 to_ts: Optional[int] = None) -> pd.DataFrame:
    kwargs = {"interval": interval, "limit": limit}
    if to_ts is not None:
        kwargs["to"] = to_ts
    try:
        raw = exchange.api.list_futures_candlesticks(exchange.settle, contract, **kwargs)
    except GateApiException as e:
        label = (getattr(e, "label", "") or "").upper()
        message = getattr(e, "message", "") or str(e)
        if label == "INVALID_PARAM_VALUE" or "too long ago" in message.lower() or "maximum" in message.lower():
            raise HistoryLimitReached(message) from e
        raise
    except ApiException as e:
        body = str(getattr(e, "body", "") or e)
        if "INVALID_PARAM_VALUE" in body or "too long ago" in body.lower():
            raise HistoryLimitReached(body) from e
        raise
    rows = [{
        "timestamp": float(c.t), "open": float(c.o), "high": float(c.h),
        "low": float(c.l), "close": float(c.c),
        "volume": float(c.v) if c.v is not None else float(c.sum or 0),
    } for c in raw]
    return pd.DataFrame(rows, columns=_EMPTY_COLUMNS)


def fetch_candles(
    exchange,
    contract: str,
    interval: str,
    days_back: float,
    cache_dir: str = "./data/klines",
    use_cache: bool = True,
    progress_cb: ProgressCB = None,
) -> pd.DataFrame:
    """拉取最近 days_back 天的K线，自动分页 + 本地缓存增量更新。

    exchange: GateExchange 实例（只用到其只读行情接口 api.list_futures_candlesticks）。
    progress_cb(fetched_bars, target_bars, message): 可选进度回调，用于网页界面显示下载进度。
    """
    interval_sec = INTERVAL_SECONDS.get(interval, 900)

    # Gate对每个周期能查询的历史深度有硬性上限（约10000根K线），超出会报错而不是返回空，
    # 提前把请求的天数夹到这个上限以内，避免明知会失败还去请求；如果确实被夹了，
    # 通过 progress_cb 提示一下，方便网页界面/日志里能看到原因。
    hard_cap_days = max_days_for_interval(interval)
    if days_back > hard_cap_days:
        if progress_cb:
            progress_cb(0, 0, (
                f"{contract} {interval} 请求的{days_back:.0f}天超出交易所该周期可查询的历史深度"
                f"(约{hard_cap_days:.0f}天)，已自动改为拉取最近{hard_cap_days:.0f}天"
            ))
        days_back = hard_cap_days

    target_bars = int(days_back * 86400 / interval_sec) + 5
    now_ts = int(time.time())
    earliest_needed = now_ts - int(days_back * 86400)

    cached = _load_cache(cache_dir, contract, interval) if use_cache else pd.DataFrame(columns=_EMPTY_COLUMNS)

    if len(cached) > 0 and cached["timestamp"].min() <= earliest_needed:
        # 本地缓存已覆盖所需区间，只需要补最新的一小段
        newest_cached = int(cached["timestamp"].max())
        gap_bars = int((now_ts - newest_cached) / interval_sec) + 2
        if gap_bars > 1:
            if progress_cb:
                progress_cb(len(cached), target_bars, f"{contract} {interval} 命中本地缓存，正在补充最新K线")
            try:
                fresh = _fetch_page(exchange, contract, interval, limit=min(gap_bars, PAGE_LIMIT))
            except HistoryLimitReached:
                fresh = pd.DataFrame(columns=_EMPTY_COLUMNS)
            if len(fresh) > 0:
                # fresh 是刚从交易所重新拉取的，遇到和 cached 里时间戳重复的K线(最典型的就是
                # 上次缓存的时候还没走完的那一根)，应该以 fresh 为准——之前这里
                # drop_duplicates() 默认 keep="first"，会保留 concat 顺序里排在前面的 cached
                # (旧、可能不完整的快照)，把刚拉取到的新数据丢掉，导致同一根K线的旧快照被
                # 永久锁死在缓存里，signal计算一直用着错的成交量/收盘价。
                cached = pd.concat([cached, fresh], ignore_index=True)
                cached = cached.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
                if use_cache:
                    _save_cache(cache_dir, contract, interval, cached)
        if progress_cb:
            progress_cb(len(cached), target_bars, f"{contract} {interval} 数据已就绪（来自本地缓存）")
        return cached[cached["timestamp"] >= earliest_needed].sort_values("timestamp").reset_index(drop=True)

    # 缓存不够，需要向历史深处分页拉取
    all_chunks = [cached] if len(cached) > 0 else []
    to_cursor = now_ts
    fetched_total = len(cached)
    for page_i in range(MAX_PAGES):
        try:
            page = _fetch_page(exchange, contract, interval, limit=PAGE_LIMIT, to_ts=to_cursor)
        except HistoryLimitReached as e:
            # 交易所明确表示"再往前没有可查询的数据了"，当作正常到达历史尽头处理，
            # 用已经拿到的数据继续，而不是让整个回测任务失败。
            if progress_cb:
                progress_cb(min(fetched_total, target_bars), target_bars,
                            f"{contract} {interval} 已到达交易所允许查询的最早历史（{e}），停止继续往前翻页")
            break
        if page is None or len(page) == 0:
            break
        all_chunks.append(page)
        fetched_total += len(page)
        oldest = int(page["timestamp"].min())
        if progress_cb:
            progress_cb(
                min(fetched_total, target_bars), target_bars,
                f"{contract} {interval} 已下载至 {pd.to_datetime(oldest, unit='s')}（第{page_i+1}页）",
            )
        if oldest <= earliest_needed:
            break
        to_cursor = oldest - interval_sec
        time.sleep(REQUEST_SLEEP_SEC)

    df = pd.concat(all_chunks, ignore_index=True) if all_chunks else pd.DataFrame(columns=_EMPTY_COLUMNS)
    # 同上：重复时间戳保留最后一条(更晚拉取到的数据)，不要保留可能过时的旧缓存快照
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    if use_cache and len(df) > 0:
        _save_cache(cache_dir, contract, interval, df)
    if progress_cb:
        progress_cb(len(df), target_bars, f"{contract} {interval} 下载完成，共 {len(df)} 根")
    return df[df["timestamp"] >= earliest_needed].sort_values("timestamp").reset_index(drop=True)
