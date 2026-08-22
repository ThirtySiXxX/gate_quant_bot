"""
持仓归属边界的回归测试。

这里守的是一条资金安全底线：**程序绝不能去动一笔它自己没开过的仓位。**
以前 _reconcile_positions() 会把交易所上的所有持仓一律当成自己的接管，
_handle_orphaned_positions() 又会把不在标的池里的仓位直接市价平掉——
两条路径加起来等于"启动即接管整个账户"。下面每个用例都对应其中一种翻车方式。

测试方法是给引擎一个假交易所，记录它到底下了哪些单。
断言"没下单"比断言"状态对"更有意义：状态可以改回来，钱平掉了就回不来了。
"""
import os
import shutil
import tempfile
import unittest

from src import ownership
from src.config import ConfigStore, CostConfig, SystematicConfig
from src.state import StateStore
from src.systematic_engine import SystematicEngine


class FakeExchange:
    """只实现引擎会用到的接口；所有下单调用都记进 self.orders 供断言。"""

    def __init__(self, positions):
        # positions: [(symbol, side, size)]
        self._positions = [
            {"contract": s, "side": d, "size": n, "entry_price": 100.0,
             "mark_price": 100.0, "leverage": 0.0}
            for s, d, n in positions
        ]
        self.orders = []

    # --- 行情/账户 ---
    def get_dual_positions(self):
        return list(self._positions)

    def get_account_equity(self):
        return 10000.0

    def get_contract(self, symbol):
        return {"quanto_multiplier": 1.0, "order_size_min": 1, "taker_fee_rate": 0.0005,
                "funding_rate": 0.0, "funding_interval": 28800, "mark_price": 100.0}

    def get_account_taker_fee_rate(self, symbol):
        return 0.0005

    def get_ticker(self, symbol):
        return {"last": 100.0}

    def estimate_market_order(self, symbol, side, qty, is_entry=True, levels=20):
        return {"ok": True, "spread_bps": 0.0, "slippage_bps": 0.0, "fill_ratio": 1.0,
                "avg_price": 100.0, "message": ""}

    def ensure_cross_margin(self, symbol, leverage):
        return {"ok": True, "verified": True, "margin_mode": "cross", "message": ""}

    # --- 下单 ---
    def open_dual(self, symbol, side, qty, **kw):
        self.orders.append(("open", symbol, side, qty))
        return {"left": 0, "fill_price": 100.0, "fee": 0.0}

    def reduce_dual(self, symbol, side, qty, **kw):
        self.orders.append(("reduce", symbol, side, qty))
        # 真实平仓后交易所上就没这条腿了
        self._positions = [p for p in self._positions
                           if not (p["contract"] == symbol and p["side"] == side)]
        return {"left": 0, "fill_price": 100.0, "fee": 0.0}

    def closed_keys(self):
        return {(o[1], o[2]) for o in self.orders if o[0] == "reduce"}


BASE_CFG = """
mode: paper
settle: usdt
symbols:
- BTC_USDT
systematic:
  tick_interval_sec: 900
  min_bars_short: 999999
risk: {}
costs: {}
storage: {}
web: {}
"""


class OwnershipTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmp, "data")
        os.makedirs(os.path.join(self.data_dir, "klines"), exist_ok=True)
        self.cfg_path = os.path.join(self.tmp, "config.yaml")
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            f.write(BASE_CFG)
        self.state = StateStore(db_path=os.path.join(self.data_dir, "state.sqlite3"))
        self.state.switch_mode("paper")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _engine(self, exchange, **sys_overrides):
        store = ConfigStore(path=self.cfg_path)
        if sys_overrides:
            store.save({"systematic": {**store.snapshot().get("systematic", {}), **sys_overrides}})
        return SystematicEngine(store, exchange, self.state,
                                cache_dir=os.path.join(self.data_dir, "klines"))

    def _sys_cfg(self, engine):
        return SystematicConfig.build(engine.config_store.snapshot().get("systematic", {}))

    # ------------------------------------------------------------------ 用例

    def test_foreign_position_in_pool_is_not_adopted(self):
        """账户上本来就有的 BTC 多仓（在标的池里）不能被当成引擎自己的仓。"""
        ex = FakeExchange([("BTC_USDT", "long", 10)])
        eng = self._engine(ex)
        self.assertTrue(eng._reconcile_positions(self._sys_cfg(eng)))

        pos = self.state.get_position("BTC_USDT", "long")
        self.assertIsNotNone(pos)
        self.assertEqual(pos.role, "external", "外部持仓必须标成 external，不能是 primary")
        self.assertEqual(self.state.external_positions, ["BTC_USDT|long"])
        # list_primaries 不返回它 —— 这是孤儿清仓不会碰它的根本保证
        self.assertEqual(self.state.list_primaries(), [])

    def test_foreign_position_outside_pool_is_never_closed(self):
        """最危险的老行为：手动开的 SOL 仓不在标的池里，启动第一个tick就被市价平掉。"""
        ex = FakeExchange([("SOL_USDT", "long", 5)])
        eng = self._engine(ex)
        sys_cfg = self._sys_cfg(eng)
        eng._reconcile_positions(sys_cfg)
        eng._handle_orphaned_positions(["BTC_USDT"], sys_cfg, CostConfig.build({}))

        self.assertEqual(ex.orders, [], "外部持仓在任何情况下都不允许被下单动到")
        self.assertIsNotNone(self.state.get_position("SOL_USDT", "long"))

    def test_own_orphan_needs_confirmation_before_closing(self):
        """引擎自己开的仓，标的被移出标的池后也不再自动平，只登记待确认。"""
        ownership.mark_owned(self.data_dir, "paper", "SOL_USDT", "long")
        ex = FakeExchange([("SOL_USDT", "long", 5)])
        eng = self._engine(ex)
        sys_cfg = self._sys_cfg(eng)

        eng._reconcile_positions(sys_cfg)
        self.assertEqual(self.state.get_position("SOL_USDT", "long").role, "primary")

        eng._handle_orphaned_positions(["BTC_USDT"], sys_cfg, CostConfig.build({}))
        self.assertEqual(ex.orders, [], "默认不再自动清仓")
        self.assertEqual(self.state.pending_close_positions, ["SOL_USDT|long"])

        # 用户点了"确认平仓"之后才真的平
        eng.request_close("SOL_USDT", "long")
        eng._reconcile_positions(sys_cfg)
        eng._handle_orphaned_positions(["BTC_USDT"], sys_cfg, CostConfig.build({}))
        self.assertEqual(ex.closed_keys(), {("SOL_USDT", "long")})
        self.assertFalse(ownership.is_owned(self.data_dir, "paper", "SOL_USDT", "long"),
                         "平完仓要把归属登记一并清掉")

    def test_auto_close_flag_restores_old_behavior(self):
        ownership.mark_owned(self.data_dir, "paper", "SOL_USDT", "long")
        ex = FakeExchange([("SOL_USDT", "long", 5)])
        eng = self._engine(ex, auto_close_removed_symbols=True)
        sys_cfg = self._sys_cfg(eng)
        eng._reconcile_positions(sys_cfg)
        eng._handle_orphaned_positions(["BTC_USDT"], sys_cfg, CostConfig.build({}))
        self.assertEqual(ex.closed_keys(), {("SOL_USDT", "long")})

    def test_adopt_makes_position_managed(self):
        ex = FakeExchange([("BTC_USDT", "long", 10)])
        eng = self._engine(ex)
        sys_cfg = self._sys_cfg(eng)
        eng._reconcile_positions(sys_cfg)
        self.assertEqual(self.state.get_position("BTC_USDT", "long").role, "external")

        eng.adopt_external("BTC_USDT", "long")
        eng._reconcile_positions(sys_cfg)
        self.assertEqual(self.state.get_position("BTC_USDT", "long").role, "primary")
        self.assertEqual(self.state.external_positions, [])

    def test_manage_existing_flag_restores_old_behavior(self):
        ex = FakeExchange([("BTC_USDT", "long", 10)])
        eng = self._engine(ex, manage_existing_positions=True)
        eng._reconcile_positions(self._sys_cfg(eng))
        self.assertEqual(self.state.get_position("BTC_USDT", "long").role, "primary")

    def test_ownership_survives_restart(self):
        """归属记录必须落盘：重启后引擎不能把自己的仓误判成外部持仓而撒手不管。"""
        ownership.mark_owned(self.data_dir, "paper", "BTC_USDT", "long")
        ex = FakeExchange([("BTC_USDT", "long", 10)])
        eng = self._engine(ex)                      # 全新的引擎实例，等价于重启
        eng._reconcile_positions(self._sys_cfg(eng))
        self.assertEqual(self.state.get_position("BTC_USDT", "long").role, "primary")

    def test_stale_ownership_entry_is_pruned(self):
        """归属登记里的僵尸条目必须清掉，否则用户之后手动开的同名仓会被误判成引擎的仓。"""
        ownership.mark_owned(self.data_dir, "paper", "BTC_USDT", "long")
        eng = self._engine(FakeExchange([]))        # 交易所上已经没有这笔仓了
        eng._reconcile_positions(self._sys_cfg(eng))
        self.assertFalse(ownership.is_owned(self.data_dir, "paper", "BTC_USDT", "long"))

        # 用户随后手动开了一笔同标的同方向的仓，必须被认成外部持仓
        eng2 = self._engine(FakeExchange([("BTC_USDT", "long", 3)]))
        eng2._reconcile_positions(self._sys_cfg(eng2))
        self.assertEqual(self.state.get_position("BTC_USDT", "long").role, "external")

    def test_paper_and_live_ledgers_are_separate(self):
        ownership.mark_owned(self.data_dir, "paper", "BTC_USDT", "long")
        self.assertTrue(ownership.is_owned(self.data_dir, "paper", "BTC_USDT", "long"))
        self.assertFalse(ownership.is_owned(self.data_dir, "live", "BTC_USDT", "long"),
                         "模拟盘的归属记录不能泄漏到实盘")

    def test_tick_skips_symbols_with_foreign_positions(self):
        """有外部持仓的标的整体不交易——否则策略的仓会和用户的仓合并成同一条腿。"""
        ex = FakeExchange([("BTC_USDT", "long", 10)])
        eng = self._engine(ex)
        eng._tick()
        self.assertEqual(ex.orders, [], "该标的本轮不应该产生任何订单")
        self.assertTrue(any("跳过交易" in l for l in self.state.logs),
                        f"应当有明确的跳过提示，实际日志: {self.state.logs}")


if __name__ == "__main__":
    unittest.main()
