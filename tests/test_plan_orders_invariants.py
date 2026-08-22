"""
下单规划(plan_orders)的不变量穷举验证。

这里要回答的问题是："调仓到底是按差额调，还是无脑全平再重开？"
逐个用例手写容易漏掉边界，所以直接穷举一大片 (当前方向, 当前张数, 目标名义值)
组合，对每种组合断言下面这几条必须永远成立：

  1. reduce 的张数必须**严格小于**当前持仓 —— 减仓永远只减差额，
     不会把仓位减没(减没了应该走 close 分支，语义不同：close 才结清全部手续费)。
  2. close 的张数必须**恰好等于**当前持仓 —— 平仓就是全平，不多不少。
  3. 执行完这批动作后的净持仓，必须等于目标张数。
  4. 同一轮里不会既 open 又 reduce(自相矛盾的动作)。
  5. 只有方向反转时才会出现 close+open 组合，且顺序必须是先 close 后 open。

第 1 条是最要紧的：如果 reduce 的张数算大了，reduce_only 单会被交易所截断，
本地账本却按请求量记账，从此本地和交易所的仓位就永久对不上了。
"""
import unittest

from src.systematic_engine import notional_to_contracts, plan_orders

PRICE = 100.0
QM = 1.0


def apply_actions(current_side, current_size, actions):
    """把动作列表实际"执行"一遍，返回最终 (方向, 张数)。"""
    side, size = current_side, current_size
    for action, act_side, qty in actions:
        if action == "open":
            if side is None:
                side, size = act_side, qty
            else:
                assert act_side == side, "open 的方向必须和当前持仓一致"
                size += qty
        elif action == "reduce":
            assert act_side == side
            size -= qty
        elif action == "close":
            assert act_side == side
            size -= qty
            if size == 0:
                side = None
    return (side, size) if size else (None, 0)


class PlanOrdersInvariantTest(unittest.TestCase):

    def _cases(self):
        for order_size_min in (1, 5):
            for current_side in (None, "long", "short"):
                sizes = (0,) if current_side is None else (1, 3, 5, 10, 37, 100)
                for current_size in sizes:
                    # 目标名义值扫过：大空头 → 0 → 大多头，含各种零碎值
                    for tn in (-10000, -3700, -1000, -500, -99, -1, 0,
                               1, 99, 500, 1000, 3700, 10000):
                        yield order_size_min, current_side, current_size, float(tn)

    def test_invariants(self):
        checked = 0
        for osm, cur_side, cur_size, tn in self._cases():
            actions = plan_orders(cur_side, cur_size, tn, PRICE, QM, osm)
            ctx = f"osm={osm} cur={cur_side}x{cur_size} target_notional={tn}"

            target_qty = (notional_to_contracts(tn, PRICE, QM) // osm) * osm
            target_side = None
            if target_qty >= osm:
                target_side = "long" if tn > 0 else "short"
            else:
                target_qty = 0

            kinds = [a[0] for a in actions]

            for action, side, qty in actions:
                self.assertGreater(qty, 0, f"不允许出现0张或负数张的动作: {ctx}")

                if action == "reduce":
                    # 【不变量1】减仓只减差额，永远不会减到0或减过头
                    self.assertLess(qty, cur_size,
                                    f"reduce 张数不能≥当前持仓(那是close的活): {ctx} -> {actions}")
                    self.assertEqual(side, cur_side, ctx)

                if action == "close":
                    # 【不变量2】平仓就是全平
                    self.assertEqual(qty, cur_size,
                                     f"close 必须恰好平掉全部持仓: {ctx} -> {actions}")
                    self.assertEqual(side, cur_side, ctx)

            # 【不变量4】不会同时加仓又减仓
            self.assertFalse("open" in kinds and "reduce" in kinds,
                             f"同一轮不能既open又reduce: {ctx} -> {actions}")

            # 【不变量5】close+open 只在方向反转时出现，且必须先close
            if "close" in kinds and "open" in kinds:
                self.assertNotEqual(cur_side, target_side, ctx)
                self.assertLess(kinds.index("close"), kinds.index("open"),
                                f"反手必须先平后开: {ctx} -> {actions}")

            # 【不变量3】执行完就是目标仓位
            final_side, final_size = apply_actions(cur_side, cur_size, actions)
            if not actions:
                # 没动作 = 差额小于最小下单单位，本来就该不动
                self.assertLess(abs(target_qty - (cur_size if cur_side == target_side else 0)), osm,
                                f"不该无动作: {ctx} -> target_qty={target_qty}")
            else:
                self.assertEqual((final_side, final_size), (target_side, target_qty),
                                 f"执行后仓位必须等于目标: {ctx} -> {actions}")
            checked += 1

        self.assertGreater(checked, 300, "用例覆盖数量不足，穷举网格可能被改坏了")

    def test_shrink_is_partial_not_full_close(self):
        """核心问题的正面回答：目标变小但没到0时，只减差额，不是全平重开。"""
        # 持有100张多仓，目标缩到60张
        actions = plan_orders("long", 100, 60 * PRICE * QM, PRICE, QM, 1)
        self.assertEqual(actions, [("reduce", "long", 40)])

    def test_grow_is_incremental_not_reopen(self):
        """目标变大时只补差额，不会先平掉再按新规模重开(那样要付两次手续费)。"""
        actions = plan_orders("long", 60, 100 * PRICE * QM, PRICE, QM, 1)
        self.assertEqual(actions, [("open", "long", 40)])

    def test_target_below_min_order_size_closes_everything(self):
        """"如果不够了就全平"：目标小到不足一个最小下单单位时，全平而不是留个零头。"""
        actions = plan_orders("long", 100, 4 * PRICE * QM, PRICE, QM, 5)
        self.assertEqual(actions, [("close", "long", 100)])

    def test_target_zero_closes_everything(self):
        actions = plan_orders("long", 37, 0.0, PRICE, QM, 1)
        self.assertEqual(actions, [("close", "long", 37)])

    def test_reversal_is_full_close_then_open(self):
        """方向反转必须整条腿平掉再反向开，不能只减到负数。"""
        actions = plan_orders("long", 30, -50 * PRICE * QM, PRICE, QM, 1)
        self.assertEqual(actions, [("close", "long", 30), ("open", "short", 50)])

    def test_tiny_change_does_nothing(self):
        """差额不足最小下单单位就不动，避免制造无意义的手续费。"""
        # 目标101/104张、最小单位5张：向下取整后都是100张，和当前持平，无动作
        self.assertEqual(plan_orders("long", 100, 101 * PRICE * QM, PRICE, QM, 5), [])
        self.assertEqual(plan_orders("long", 100, 104 * PRICE * QM, PRICE, QM, 5), [])

    def test_plan_orders_itself_has_no_percentage_buffer(self):
        """明确记录一件容易误解的事：plan_orders 只做"最小下单单位"级别的取整，
        它**不含**任何百分比意义上的调仓缓冲。目标98张、最小单位5张会被取整到95张，
        于是产生一笔5张的减仓——单看这里像是很容易被小波动触发。

        真正防止频繁调仓的是上游的 portfolio.should_rebalance()：目标与当前的差额
        必须超过 no_trade_buffer_pct(默认25%)才会走到这里。两层职责分开，
        不要在 plan_orders 里再加一层阈值，否则两处阈值会互相干扰、难以调参。
        """
        self.assertEqual(plan_orders("long", 100, 98 * PRICE * QM, PRICE, QM, 5),
                         [("reduce", "long", 5)])

    def test_target_rounds_down_never_up(self):
        """目标张数按最小单位向下取整——宁可少开，不能超出目标风险。"""
        actions = plan_orders(None, 0, 99 * PRICE * QM, PRICE, QM, 10)
        self.assertEqual(actions, [("open", "long", 90)])


if __name__ == "__main__":
    unittest.main()
