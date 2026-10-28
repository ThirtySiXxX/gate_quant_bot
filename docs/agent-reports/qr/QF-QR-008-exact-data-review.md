# QF-QR-008-EXACT-DATA-REVIEW

2026-10-28 Australia/Melbourne。QR独立验收结果：
**OHLCV：PASS_WITH_DISCLOSED_RETROSPECTIVE_SOURCE_LIMITATIONS**；
**MARK原始资料：PASS_WITH_GAPS**。
实际决策/资金费查询覆盖仍为 **NOT_EVALUATED**，经济查询门 **OPEN**，训练未就绪。

派单 `QF-DISPATCH-20261028-QR008-EXACT-DATA-REVIEW-1`。工作树
`/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`，分支
`codex/qr-validation-baseline`，干净起点 `e2211a20bb0919b77506328e68867ff9357ec6c3`。
验证器/测试代码提交 **`9cae8458fb85e474a047fc1793abe0458cd83ab3`**；本报告与机器
报告另作报告提交，从而明确绑定真实代码commit而不制造自引用hash。

## 完成内容和独占文件

只新增六个分配文件，没有修改既有实现或旧规范：

- `research/qr008/validate_exact_history.py`：独立原始数据解析、Fraction精确算术、
  整行来源、封闭字段、可用时钟、catalog/row/content身份、逐行聚合/来源和差异检查。
- `tests/qr_research/test_qr008_exact_history.py`：25项字面与负例测试。
- `research/qr008/validate_mark_raw.py`：一次流式gzip/hash/CRC解析、全部别名引用、
  月内/跨月缺口，及只接受外部显式point/query的可选情景检查函数。
- `tests/qr_research/test_qr008_mark_raw.py`：22项原始格式/别名/查询边界测试。
- `research/qr008/exact-data-review.json`：精确身份、VR01–VR08逐项状态、实际计数、
  证据路径/hash和未执行门。
- 本角色报告。

只在新的`research/.data/qr008/verification-*`目录写入审计。没有第三次producer
构建、另一个行情数据集、MARK规范化point表、特征、信号、市场回放或标签。
未调用/导入QD parser、aggregation、hash、row-construction或采集器helper作oracle。
MARK检查复用的是本轮QR自有的JSON/hash/文件限制工具，不是被审实现。

## 精确输入与代码身份

| 项目 | 精确身份 |
| --- | --- |
| 冻结QR规格commit | `8b9e85e5c041fcf9167940520035693562f761ba` |
| volume-recovery-spec.json | `cd0e123d019b428e7bd12754e553c0322d4aac5593537b07752bab777280bdc0` |
| 用户来源方案A批准记录 | `d3eeb12d0d5348f769a9493a215eb32e2f3be40c13ed4a0eb5607e7cef9effa0` |
| QD builder commit | `383c5acccbaee652c5d9f5c84e936b7cedfa7070` |
| QD repair_history.py | `9e0d36333fc0951f5b7cc51eb10b2873a115f91239fba550bdfd8a178b244448` |
| QD报告/摘要commit | `887d19629726c384a7cb88e9c9de1ff66534ee92` |
| 主候选manifest | `c1e6056058fd312d472e96fddfea15e78c778847de9942e5757cb39ad2ac9b91` |
| 重现候选manifest | `c93557759de54a879aab582b196c8de36c99919712c439f810ab7f1d56e6e8a8` |
| QR OHLCV验证器 | `324ab2d1b4cc1b529f253ac75b12aeb7b30670f75ed1d7941ca53b3ace9c483f` |
| QR MARK验证器 | `1e7e03344f5418f696409243f4d43379bd5fb2dbf6286552300e8627556c9e06` |
| MARK handoff | `30fe38ea8ae0a30aa3ba60da5f7462de37f57849bbe5307435286a3d627407ce` |
| MARK r2 result | `3f601ebf45b2e97825b9c701234060a3348e47e508c28211b98572ed38f5a21e` |
| MARK r2 plan | `19cd063f596746696efb2cfdd308205c8fad040763d55ea02ce7a622e1531ce5` |
| MARK alias amendment | `0b33bf4272bbb87bb33d1e19fe27ab7e5a7765ddd2b98baf4a4678530bc17ece` |

两候选位于QD工作树`research/.data/qd008/exact-ohlcv-v3-candidate/`和
`exact-ohlcv-v3-reproducibility/`。MARK与批准记录位于负责人固定协调目录：
`/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/`。
QD代码、测试、报告和摘要都重新核对了工作文件及精确Git对象的hash；未执行其代码。
用户已经批准整行来源A和BTC close冲突处理，旧spec中的null批准字段作为历史保留，
本轮通过独立批准记录绑定，未再次提问或改写旧文件。

## OHLCV实际验收

范围固定`[2023-01-01,2026-10-01)` UTC，仅BTC/ETH。
每币25560小时来自2025-12-01之前的整行归档；后7296小时来自冻结decimal REST整行。
4h/1d全部从同一小时基础精确计算，没有拼接单字段、容差、价格专用降级或收益筛选。

独立核验148份冻结源/证据文件hash，完整解析90份小时归档、8份批量REST和4份单小时
确认。确认只作佐证，未增加小时数。旧v2每币33489小时按其原始manifest完整检查，
仅比较本任务完整32856小时交集，后633小时保留在旧文件中，不进入本次候选。

| 两份候选分别验收 | BTC_USDT | ETH_USDT |
| --- | ---: | ---: |
| 1h记录 | 32856 | 32856 |
| 4h记录 | 8214 | 8214 |
| 1d记录 | 1369 | 1369 |
| 有小数成交量的小时 | 0 | 4106 |
| 精确总成交量（contracts） | 487594990078 | 147845325893.4 |

每份共84878行。六个网格严格升序/完整且UTC对齐，OHLC域、单位、所有raw引用和
ordered hourly parent引用均通过。每个4h/day的全部五个值精确一致；直接小时→日线
与小时→4h→日线也一致。每币三个周期的总成交量相等，没有乘数/基础币换算。
两根目录各134212899 bytes，9份payload逐字节相同，manifest只差created_at。

独立重算全部4221个差异小时/4222个差异字段，并逐字节核对完整archive/REST/v2
OHLCV元组、字段差值及原始引用。BTC close `79513.6→79509.9`与对应整行一起保留，
未把它当异常删除或仅替换volume。完整差异文件SHA256：
`80215db0e251a700c7fe3d5c20eb07ec24191204b3d3474e40a507077a5f5ba5`。

所有规范数据的`observed_first_available_at_us=null`及未知原因保留；
`research_available_at_us=bar_close_us`只是声明的研究代理。最后一根在截止时刻
收盘的bar可存储，但任何`decision_us<end`的消费者不能使用它。不能声称历史首次
发布、到达、修订已获证明，也不能把全catalog身份或未来文件清单喂给策略。

## MARK实际验收

独立读取90个gzip一次，压缩合计718396794 bytes。每对象核对原始SHA、完整CRC、
UTF-8/四列精确字符串、整数微秒、价格域、所属月和原始顺序。未排序、前填、插值、
改age上限或用trade/index/last替换MARK列。既有19份raw与新71份都按冻结身份读取。

| 完整原始核验 | BTC_USDT | ETH_USDT |
| --- | ---: | ---: |
| 月对象 | 45 | 45 |
| 物理行 | 28549024 | 28036123 |
| 规范观察（仅计数，未落表） | 28549018 | 28036123 |
| 别名行 | 6 | 0 |
| 月内gap >60s / >120s / >180s | 34 / 26 / 21 | 40 / 24 / 19 |
| 最大gap（秒） | 2529.124186 | 2547.948272 |

共56585147物理行。六组别名分别在202310 BTC（5组）和202402 BTC（1组）；逐组
保留全部source_rows、首物理行、四个原字符串及v2 point_id，和handoff完全一致。
同timestamp不同词形、价格冲突或下降时序仍拒绝。

74段>60秒月内gap全部写入审计；88条跨月连接全部检查，最大45.679966秒。
两币最长gap均在202404，约42分钟：BTC物理行90640→90641，
`1712590924042069→1712593453166255us`；ETH物理行23180→23181，
`1712590905034005→1712593452982277us`。缺口存在且保留，不能由总行数推断经济可用性。

可选`select_mark(points, query, covered_months)`只检查外部显式提供的查询。主情景
delay60/age120、压力delay120/age180的可用时间/age等于上限和超出1us、缺月、跨月
新鲜点、未来点、错误price kind及别名引用均通过合成测试。**实际市场query执行0，
required_query_coverage=NOT_EVALUATED**；本轮没有发明策略或资金费查询时刻。

## 测试、实际执行及资源

计数分开报告：**25项OHLCV checker自测 + 22项MARK checker自测 = 47项通过**；
OHLCV真实检查2次（含1次检查器错误），最终一次同时验收两根目录，9.544秒；
MARK真实检查1次、90对象、135.499秒。每个真实检查上限900秒，未扩大预算。
所有新忽略审计输出合计163442 bytes，低于16MiB；MARK第二次额度未使用。
QD的26 producer tests/288 regressions没有在QR执行，不计作QR结果。

字面/负例包括巨大十进制与低Decimal context、错误数值类型、缺行/重复/交换、
重算hash后的数值与来源篡改、完整有序parent、输出规范字节、截止时点、缺月、CRC、
不同chunk切分经过别名组、price kind、延迟/age边界。另对48小时合成原始数据仅改
第二天、重算整份raw/catalog身份，核对过去31个1h/4h/day桶经济投影不变，而审计
ID/引用可变化。未调用producer builder生成测试期望数据。

首个完整OHLCV检查在1.42秒返回REVISE，原因是QR检查器错误地要求旧v2只有32856行；
实际旧manifest明确33489行。现按原声明完整验证旧表，再比对新范围交集，已增加
专门回归测试。失败结果、旧文件身份及诊断保持原样；没有改producer或候选数据。
本轮第二次完整检查已经用完；没有偷偷做第三次完整核验或重建。

测试使用既有解释器，启动包装先禁用socket再导入检查器。自测命令为：

```python
import socket, unittest
def offline(*a, **k): raise AssertionError('Network disabled before imports')
socket.create_connection = socket.socket.connect = socket.socket.connect_ex = offline
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'tests.qr_research.test_qr008_exact_history',
    'tests.qr_research.test_qr008_mark_raw'])
result = unittest.TextTestRunner(verbosity=2).run(suite)
```

解释器：`/Users/lzh/Development/Project/gate_quant_bot/venv/bin/python`，
环境`PYTHONDONTWRITEBYTECODE=1`，cwd为本QR工作树。真实检查调用各模块`main`，
显式传入上述spec/approval/两个候选根，或MARK handoff/result/plan/amendment；输出
分别为`verification-exact-1`、`verification-exact-2`和`verification-mark-1`。
两个CLI都要求全新路径且有900秒alarm；已有目录不可重复运行。复审必须另行分配
新预算/输出范围，不能覆盖本轮证据。Python socket guard不是任意恶意代码的OS沙箱。

| 本地审计文件（research/.data/qr008/下） | SHA256 |
| --- | --- |
| verification-exact-1/result.json | `ac8aee53ff56763e7cf55ddc277e0ebcfbbbf7420d434109974bf425ca60e262` |
| verification-exact-2/result.json | `aad4e77c78d226d809c6634db773e75f3f541c15c3c650562d792a799210f774` |
| verification-mark-1/result.json | `47d54127387b51ac7044bdabfd5d9228576c2ad8f4fba86042611fe11ea60e61` |
| verification-selftests-1/result.json | `2291b4e7cba0472d831d483ee2e7b8879546c76dfa35598e5060686b26686102` |
| verification-preservation-1/result.json | `680bf31c7bc84b3f248e67e5c8f957f2ce1ddaac6e51e65960f11e686c766d32` |

## VR状态、保护边界和后续

VR01–VR05通过当前数据层验收；VR06通过已交付数据的重现性与独立算术/因果检查，
**producer原子发布失败测试未在QR重执行**，没有第三次构建。VR07在明确范围内
通过：主仓7项指纹及72条status保持，15份QR006/QR007/旧QR008文件与起点一致，
148份旧源/证据重新hash，90份MARK逐行核验；QD自报的更广276文件清单不冒充QR复验。
详细逐项状态与未执行子项写入`research/qr008/exact-data-review.json`，没有改旧spec。

共享PROGRESS/DECISIONS由负责人/QD整合，本轮不并发编辑。没有改主仓索引、旧raw、
v1/v2、候选、native代码、风险默认或部署；没有安装依赖、读用凭据、启动应用/引擎、
订单、NAS/Windows、merge/push。QR007合成账本已接受的四文件继续冻结，不重算或
扩展其验收结论。

**VR08仍OPEN。** 负责人下一步提供冻结的R3决策/资金费query计划，评估现有MARK
缺口是否命中实际查询，再完成完整状态回放、成本/资金费/最终性标签、跨时段/跨币
依赖与purge切分以及训练计划审查。历史来源真值和首次可用时间仍未证明；本数据
接受只针对批准的回溯研究假设，不证明盈利、真实成交或高杠杆生存能力。

本检查点提交后停止，等待负责人下一交接，不自行开启R3。达到全部训练条件时
报告证据，并在任何模型/scaler/校准器fit前取得用户确认；本轮所有fit为0。
