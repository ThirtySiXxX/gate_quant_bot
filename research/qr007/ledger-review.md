# QR007 账本独立验收预检

2026-10-28 Australia/Melbourne。任务 QF-QR-007-READINESS。
当前状态：**PREPARED_NOT_EXECUTED**；独立验证器及23项自身测试已完成，21项producer用例未执行。
r2设计复核记录保留；B1费用未知值修订等待QD精确schema/profile交接，尚无实现验收结论。
QR 起点 52ce1ebeb054abd49c41fc4acbb4c7b7eb41c762。
语义基线 QR006 c7e9a2492247fa31e216035f87e8bb20cca6e6ad；对应 QD006
9bb3c0ec2b57e7154a51e56d795645c273c1308d 接受 34 项设计标准。
用户已授权继续 BTC/ETH 训练准备；旧文档的“等待实现批准”不阻止此授权内的普通工作。
模型、scaler、校准器拟合仍需训练前确认；本检查点不产生市场标签。

## 原预检阶段独占边界及下一交付（历史记录；当前边界见末节）

QR 允许编辑本文件、research/qr007/validate_event_ledger.py、
tests/qr_research/test_qr007_ledger.py、research/qr008/coverage-protocol.md
和 docs/agent-reports/qr/QF-QR-007-readiness.md。预检提交三份 Markdown。
当前 schema 审查只修改本文件与角色报告；在修订接口复核和负责人交接前，不创建两份
Python 验证代码，不猜测函数签名。
不改 QR006、共享 schema、src、他人测试、旧数据或共享日志。

后续由负责人传递 QD schema 的确切 commit/hash，QR 对照下表评审；通过后按实际
接口实现独立验证器。验证器可调用被测 QD 公共入口产生实际结果，但期望值只能由
本地字面常量/独立 Decimal 恒等式计算，不能调用 QD 费用、资金费、分摊或状态归约
函数当 oracle。还需接受被测结果文件的独立检查，不能只验证其自报 success/hash。

## 34 项标准的阶段映射

S1 表示合成账本/输入状态阶段可测；S2 表示实际资料覆盖；S3 表示完整状态回放；
S4 表示标签生产/训练切分。全部“待测”，不是已通过；阶段1的小例子不替代后续验收。

| 稳定 ID | 独立字面 oracle / 负例 | 本阶段与剩余范围 |
| --- | --- | --- |
| QF006-A01 | 10×0.001×49900=499；fee=0.2495，cash=-0.2495 | S1 |
| QF006-A02 | 合成 maker rate=-0.0001，fee=-0.0499，cash=+0.0499；role_basis=scenario | S1；不声称实际 maker 费率 |
| QF006-A03 | 未成交量0，成交费用0，不凭提交订单记费 | S1；无 episode 的 target=null 属 S4 |
| QF006-A04 | 100/25 张分别收费0.1/0.025，总0.125；未成交75不收费 | S1 |
| QF006-A05 | Q=±10,m=.001,mark=50000,f=±.0001，signed cash 为±.05；零率0 | S1，四种符号独立检查 |
| QF006-A06 | 01—02时持仓，只有00/08/16快照：费用0，不能按小时摊 | S1 |
| QF006-A07 | 快照10张，平仓后才入账仍归旧 episode，金额-.05 | S1；实际快照映射另属 S2 |
| QF006-A08 | HISTORICAL_EXACT 同时刻顺序无证据，资格未知/拒绝，不能猜排序 | S1拒绝语义；真实序列 S2 |
| QF006-A09 | snapshot-before-fills：旧10张在S平仓资格10；S开仓资格0；先开4/S开6资格4；旧10先减4/S减6资格6 | S1；另一顺序是单独已命名压力情景 |
| QF006-A10 | 旧多10反手空6，16张fee=.4，close=.25/open=.15；旧funding=-.05、新0 | S1 |
| QF006-A11 | entry49900/exit50100、10张、m=.001、费率.0005：gross2，fees.5，funding-.05，net1.45 | S1，逐状态见下表 |
| QF006-A12 | 快照后减6余4：funding分摊.03/.02；最终net .87/.58合1.45 | S1分摊；一个训练 episode 属 S4 |
| QF006-A13 | 两笔独立posting -.02/-.01；重复同内容无影响，冲突隔离，posting revision>1拒绝 | S1；不得因新entry_id绕过源事件去重 |
| QF006-A14 | 已付-.05后总额修订-.10再-.08，只改L .05→.03；另付-.03才改C | S1；含转正退款、平仓后fee修订；新标签成熟属 S4 |
| QF006-A15 | exact缺mark，金额未知；不得用trade close代替 | S1拒绝/未知；实际mark覆盖 S2 |
| QF006-A16 | 当前metadata historical_effective_at未知，不回填2023 | S1拒绝；历史有效区间 S2 |
| QF006-A17 | bool/fractional integer-contract quantity、NaN、负价格、百分数字符串、单位错配拒绝 | S1；当前整数研究 schema 不默许小数扩展 |
| QF006-A18 | 可用时刻1,000,000us：999,999不可用，等于可用 | S1信息门；模型端到端另审 |
| QF006-A19 | 已知资格但最终金额未可用：null不作0，新风险阻断，历史预算不回写 | S1 |
| QF006-A20 | C1000,A20,L30,reserve100+5：U0/+50预算865，U-40预算825；未知/陈旧U不能增加风险 | S1；不声称Gate真实可用保证金 |
| QF006-A21 | 08:00:01退出、08:00:04入账可知、完整断言10:00:02才可用；不可提前成熟 | S1可保存时钟/断言输入；完整label状态 S4 |
| QF006-A22 | 24h=86,400,000,000us；严格小于边界，等号失败，跨币信息区间重叠要purge | S1可查单位；切分/purge整体 S4 |
| QF006-A23 | 跨折不清空状态，终端强平不冒充自然退出 | S3/S4，不由孤立账本宣告通过 |
| QF006-A24 | 两次开仓notional100+200，退出500，fee.4，net199.6；分母300，target12dp=.665333333333 | S1费用/库存算术；标签分母/序列化 S4 |
| QF006-A25 | 被拒/未成交机会保留状态，不生成零回报目标 | S4；S1只不记无发生现金 |
| QF006-A26 | cash100、ticket80、首单亏50会阻挡后单；跳过首单须重走状态 | S3，不删除旧交易行冒充反事实 |
| QF006-A27 | qf006 不被自动当 native schema 接受；字段/版本变化拒绝 | S1命名空间及静态隔离；未来adapter兼容另验 |
| QF006-A28 | 未来验证拟合、暴露测试集重命名、无用户确认拟合均禁止 | 全阶段约束；不以触发真实fit作为负例 |
| QF006-A29 | 未知booking/finality保留待决；没有target/label_known_at | S1未知义务保留；完整标签 S4 |
| QF006-A30 | 合成max_age60秒：59可用61拒绝，trade冒充mark拒绝 | S1；实际代理参数与覆盖 S2，合成60不是已批准市场阈值 |
| QF006-A31 | multiplier .001→.01但无转换依据，拒绝计算连续lot盈利 | S1拒绝；真实转换证据 S2 |
| QF006-A32 | effective10:00、published11:30，不能视为10:30已知 | S1因果；历史规则证据 S2 |
| QF006-A33 | source t=08:00:03，无映射则snapshot未知，禁止floor到08:00 | S1拒绝；映射 S2 |
| QF006-A34 | reference entry100、实际fill101、exit110，净价格利润9，滑点不再减一次 | S1给定fill算术；执行价格形成/全路径 S3 |

独立状态 oracle（A11，合成U）：

| 状态 | C | A | L | U | E=C+A-L+U |
| --- | ---: | ---: | ---: | ---: | ---: |
| 开仓费后 | 9999.7505 | 0 | 0 | 0 | 9999.7505 |
| 资金费识别 | 9999.7505 | 0 | .05 | 1 | 10000.7005 |
| 平仓、未入账 | 10001.5 | 0 | .05 | 0 | 10001.45 |
| 入账后 | 10001.45 | 0 | 0 | 0 | 10001.45 |

A13/A14独立恒等式：每义务 P=T-B；A=max(P,0)，L=max(-P,0)，不同义务的A/L
分别求和。C0=1000，已付B=-.05后 C999.95。T=-.10时 L.05/E999.90；T=-.08
时 L.03/E999.92；再付-.02后 C999.93/L.01；再付-.01后 C999.92/L0。
若T转为+.02，未付退款为+.07，到账前C999.95/A.07，到账后C1000.02/A0。
平仓后fee原-.25，修订-.20只产生A.05；另退款+.05才改现金；再次修订-.30产生
L.10，再付-.10才消除。所有归属保持旧episode，不能转给新反向仓位。

## API/schema 交付时的审查与事务负例

以下是实现约束/验收准备，不能用未见API假装已经执行：

- **身份与修订：** 独立 obligation/posting ID，明确instrument/trajectory/scenario
  隔离域；相同ID同内容幂等，同ID冲突不得改现金；缺失前序修订、跨义务引用、
  错币或重复allocation拒绝。真正退款用新posting；不能把累计T当新增扣款。
- **时钟：** 精确整数us；保留来源秒精度。future append/perturb 不能改变过去前缀
  的现金、预算、资格和hash；乱序消息由文档明确的排序/拒绝规则处理，不猜交易所优先。
  booking/economic_at/known/available区别必须可见，未知不能默认0或当前时间。
- **原子拒绝：** 单事件验证失败，金融状态、已消费ID、lot/义务余额及序列不得半更新；
  可追加独立拒绝审计记录，但不能据此声称财务状态改变。批处理需明确“全批原子”或
  “已提交前缀+失败位置”语义，验证器只按已审API断言，禁止隐式半成功。
- **持久化失败：** 若S1导出文件，写出中断/JSON非有限值/目标已存在/路径越界应
  保留原文件，不发布半成品成功manifest。若S1纯函数无I/O，标注不适用，不能虚构
  已测持久化能力。失败重试不得造成双计；输入对象不能被函数原地污染。
- **经济不变量：** partial/reversal/FIFO分配合计守恒；未发布收款不计预算；已付
  负债不重复预留；未知义务不能被默认余额掩盖；原始入账和旧因果历史保持不可变。
- **独立产物核对：** schema严格字段/enum/Decimal/单位检查，加上从原始合成事件
  独立重算金额、状态和身份。故意改结果后连同hash重算的污染仍应被识别。
- **环境边界：** 测试socket阻断、临时目录、没有模型或应用模块导入副作用；不读配置、
  私有账户、市场缓存以外的运营资料，不启动引擎，不更改既有策略/风险参数。

期望 QD 精确交付：typed字段/空值与状态组合、身份/修订域、Decimal精度/规范序列化、
输入/输出函数及异常、同时间顺序、纯状态与I/O边界、失败原子性、实际支持的验收ID。
QR将给 PASS/REVISE/BLOCKED，并列出“合成实现”和“实际经济覆盖”各自未达项。

本预检只对范围和验收准备给 PASS；没有执行被测账本、完整回放或标签切分。
训练仍依赖：schema/实现独立验收 → 覆盖与情景冻结 → 完整状态回放 → 标签/依赖
验收 → 冻结训练/样本外计划 → 用户确认。没有为通过测试而放宽已接受语义。

## QD007 精确 schema 审查：REVISE

Dispatch `QF-DISPATCH-20261028-QR007-SCHEMA-REVIEW-1`。只读审查 QD commit
`d474fdf0fdca7cb22aa47cfb220806b8ea2ab84f`（父 `9bb3c0ec2b57e7154a51e56d795645c273c1308d`）。
以下行号均指该 commit 的 `research/qd007/schema.md`（529 行），不是以后修订的行号。
已逐段读完 schema，并核对工作树与 commit 字节完全一致：

| 文件 | SHA256 |
| --- | --- |
| research/qd007/schema.md | 800919cf19f02b7b7f896347f378eeef994607f2f13383d01adac1ef921f191b |
| docs/agent-reports/qd/QF-QD-007-ledger.md | 62185bd1287d96de8ae1769f262858e80a39823c1cf29243892dfa0a5f263d7d |

**结论：设计级 REVISE，六项修订要求；不是运行失败，也不是已运行34项验收。**
QD 仍独占 schema/实现，QR 不修改 QD 文件。优先收紧这个小型合成 API 的明确边界，
不要求增加历史数据导入、网络、标签、动态规则或一个通用事件框架。

### 已接受的局部设计及 S01–S04

- **S01：局部传输拆分可接受，待 R01/R05/R06 统一身份及输出定义。** 严格 JSON、
  bool/float 拒绝、UTC us、decimal string、未知 null 原因、源内容 hash 与完整审计
  hash 分开，符合独立离线工具边界；不能冒充 qf006/native wire。
- **S02：分摊算法和过粗 quantum 拒绝可接受。** 保留精确父金额、HALF_EVEN、最终
  残差、按剩余量连续 FIFO 分摊；这是有界输入拒绝，不是 silently 改费率/现金。
  必须把下表写成生产者与独立验收的字面案例，并明确后续修订按相同历史关闭顺序
  重算当前归属版本；不能把新的累计金额再次加到旧归属或现金。
- **S03：全批原子拒绝及独立 integrity stop 可接受。** 失败后只能 audit，比较
  committed_state 做 rollback；合法未知值必须保留未决，不能触发同类硬错误。
- **S04：限制 HISTORICAL_EXACT、fractional qty、未确立时钟的 Posting、late-origin
  repair 可接受。** 未知 booking 留在义务中，已知现金与未知总额可并存；R02/R04/R06
  须把这些边界写清。该限制不证明 ETH 真实合约只能整数交易。

| S02 字面输入 | 期望 |
| --- | --- |
| total=.02，weights=[6,6,6,2]，quantum=.01 | 前三项各 .01，未经保护的残差 -.01；整体 ALLOCATION_QUANTUM_TOO_COARSE，不能提交任一归属 |
| total=-.02，同 weights/quantum | 前三项各 -.01、残差 +.01；同样整体拒绝 |
| total=0，weights=[6,6,6,2] | [0,0,0,0]；不存在相反符号残差 |
| total=0，weights=[]；非零total，weights=[]；weights中0/负数 | 前者 []；后两类拒绝，即使父金额0也不能接受无效权重 |
| lot金额±.01、3单位、quantum=.0001；依次关闭1、1、1单位 | 顺序归属 ±[.0033,.0034,.0033]，总计±.01；第二次按剩余 .0067/2 计算 |
| 同一lot先关闭2，再关闭1 | ±[.0067,.0033]；按关闭路径分摊，不能要求每个单位与另一关闭路径同舍入 |
| 同一路径1/1/1，累计修订从 -.01 到 -.02 | 当前归属变为 [-.0067,-.0066,-.0067]，差额和=-.01；旧 cutoff 保留旧归属，修订现金变化0 |

### QR007-R01 — 因果状态 hash 与完整 fixture 身份必须拆开

**REVISE。** schema 95–141、451–455、465–493。config 包含完整未来 SourceManifest，
每个旧 record 的 source_refs 又引用其整体 hash；451–455 声称 state hash 包含 config
身份，却要求改未来修订后过去 hash 不变。465–474 的 Snapshot 字段表还没有 config
身份字段，故当前 hash 前像定义也不唯一。

最小反例：两个 fixture 具有相同 genesis、规则与 t=10 前事件；仅把 t=20 可用的
修订 T 从 -.05 改成 -.08，并重算 future payload、manifest 和全部 source_refs。
完整 config/manifest hash 必须不同，但 snapshot(10) 的金融内容与因果 state hash
必须相同。只在同一个完整 fixture 内少提交几条未来记录，不能替代这个扰动检查。

**验收要求：** 分别定义（a）完整 config/source/journal 审计身份，（b）因果经济状态
的精确 canonical preimage；后者不含未来 catalogue、未来 record/source-ref hash
或导出时间。已在 initial 前声明的情景规则/日历可属于明确的因果配置，不要求对
不同已知政策保持 hash 相同。固定相同政策，只扰动未来事实时，past state/hash
严格相同；audit identity 不同且仍绑定全输入。不得仅取消过去 hash 不变的断言。

### QR007-R02 — 迟到成交不能通过整批经济排序提前满足资格

**REVISE。** schema 171–178、214–226、413–420、451–463。
最小反例（时间为合成 us）：起初 flat；F filled=7、available=9、buy10；S snapshot=8、
available=8。若完整批按 economic 排序先 F 后 S，会把 snapshot(8) 的资格记成10，
尽管F尚不可用；先单独处理S再F又可能触发 LATE_ORIGIN_UNSUPPORTED。完整批的
input 顺序和是否分批不能成为绕过 late-origin 限制的方式。

**验收要求：** 明确可用信息推进与库存经济顺序的组合。对当前不支持 late repair
的 profile，建议对这种跨越已到达资格截面的迟到 fill 作确定性拒绝：整批 [F,S]
和 [S,F] 均原子失败；先已提交 S 的路径在后续 F 处停止且不修改 S 旧状态。
尚不可用 fill 不能证明历史库存完整，restated 不得声称该拒绝案例已被重建。
F available=7、S available=8 的正常路径应通过；合法同经济时刻 tie policy 独立测试。
若 QD 选另一有限实现，须明确 known inventory、经济库存未知范围和支持标志，
不能让未来 fill 进入早期决策/资格或悄悄扩为历史修复实现。

### QR007-R03 — 资金费公式的 mark 时钟不能只检查 revision 到达时刻

**REVISE。** schema 252–263；QR006 protocol 175–178 的主情景是 causal last-available
MARK。反例：snapshot=80；mark valuation_at=79、valuation_available=90；final rate
available=95；revision known/available=100。当前只要求两输入 available<=100，允许
将80时尚不可用的 mark 当作80时的 causal proxy，虽然价格时间看起来足够旧。

**验收要求：** 此 profile 的 funding_formula 若代表 causal proxy，应明确
valuation_at<=valuation_available<=snapshot、年龄上限按 snapshot 计算，并验证
对应规则/乘数；输入时间自身不能倒置。final rate 可以晚于 snapshot，T 只在该
revision 可用后识别，**不要求 final_rate 在 snapshot 已知**。在 mark=79/available=79、
rate available=95、revision available=100 的正例中，99仍未决、100才识别T。
明确 formula 的 known_at 是何种已知信息，不让其冒充更早得到计算输入；若量价输入
只在后来提供而总额更早由账单得知，使用已声明 authoritative_total 语义并保持真实
消费门。若要允许事后 settlement mark 估值，应另标用途及规则，不能称 causal proxy
或进入旧决策预算；本轮不自动批准该新情景。

### QR007-R04 — 完整断言的入库合法性与当前充分性需要分别定义

**REVISE。** schema 214–227、294–316、428–435、476–485。已过期但曾有效的 assertion
必须保留，而311–313的“refs=current、P=0”未区分入库条件与查询条件。合法未来修订
不应把整个运行变成 integrity failure，也不能让旧 assertion 持续 complete。

最小轨迹：自然平仓后 T1=-.05、B=-.05，A1于10可用且完整；T2=-.08于20可用；
追加posting -.03于21可用；正确覆盖T2/全部postings的A2于22可用。
**期望：** readiness(10)=complete/complete_at10；20为immature/P=-.03；21虽P=0仍
immature（旧A1过期）；22才complete/complete_at22；早期状态保持不变，合法过期
不能触发 INTEGRITY_STOPPED。A1/T2/A2同批与按可用时间分批应有相同查询结果。

**还须给出明确状态表：** 缺 expected snapshot、mapping=null、非空资格但未知T、
P未结清、缺assertion/旧revision refs均不能complete；无事件日历可明确证明无事件，
却不能消除已有非空资格的未知费用。合法无finality信息的自然平仓为immature；
提交authority=null的无效断言按本profile可标invalid，未注册nonnull authority为硬
拒绝。只评估该cutoff当前有效的断言版本，不让被有效successor替代的旧无效记录永久
污染未来状态。明确 null mapping 在rev1-only snapshot API中是否永久未决；不能把
后续总额自动当作来源映射补证。硬冲突、合法未知与过时断言须有不同诊断。

### QR007-R05 — BTC/ETH 业务键与派生 ID 的命名域不一致

**REVISE。** schema 87–93、171–175、243–250、407、476。业务键包含instrument，故
BTC fill record_id=f1 与 ETH fill record_id=f1 是不同且允许的键，但二者都派生
episode:f1/lot:f1；readiness(episode_id, t) 没有instrument参数。相同 obligation_id
下 allocation hash 也未含instrument，可能串接归属。

**验收要求：** 选择并写明一个最小一致方案：派生 ID/引用/API 使用完整 instrument
命名域；或明确在本ledger内需全局唯一的 fill/obligation/episode/lot ID，冲突在
任何状态变更前拒绝。不是通过一个币种测试后宣称双币通过。两币相同本地fill ID
必须明确被隔离或拒绝；两币不同 ID 的正常共同账户必须通过，资金费/退款不得串币。
所有 allocation/posting/assertion 引用仍核验 instrument、trajectory、scenario。

### QR007-R06 — 已知 Posting、未知 T 的输出类型与 delta 不能矛盾

**REVISE。** schema 265–268、285–290、384–390、437–449、465–474。
允许T未知时接受独立Posting，但LedgerEntry要求A/L delta为非null decimal，又说
unknown obligation totals produce no numeric entry；这无法同时记录已知现金与未知
应收/负债变化。Snapshot的“exactly”列表还遗漏了随后要求的null_reasons字段。

最小反例：C0=1000，已知非空资格、T未知；独立Posting b=-.02 在10可用。
**期望：** C=999.98、B=-.02；T/P/A/L未知、预算null，不能把未知delta写0或漏掉
真实现金。20时T=-.05变得可用：C仍999.98、P=-.03、A=0、L=.03、E=999.95
（U=0），未知到已知的delta也不能伪称0→.03已获证。Posting在T已知时才可断言
现金与pending同步转移且E不变；未知阶段不能输出数值E不变的证明。

**验收要求：** 把所有输出字段、nullable原因路径和conditional delta定义列全。
可用nullable delta或明确区分记录种类，但不能改变T/B/P公式或拒绝原先接受的
“已知现金、未知总额”能力来绕过问题。缺 expected event但尚未创建义务时也应
说明未知聚合A/L/E的表示，不能给零负债/完整权益只靠budget=false隐藏未知。
列明应拒绝的异常字段/额外字段；审查的是返回对象本身，不只JSON哈希。

## 本轮审查边界和交接

六项为确定性文档/API修订要求，等待 QD 精确修订 checkpoint 后复核；未执行 ledger
测试、未创建 validator。S02表是独立字面验收要求，不是运行了 QD 分摊器。
当前 schema 其余已列出部分接受，不重复推翻34项经济协议。QD只需回答各R项的
修订位置、选定边界及正/负例，不需要重写工程。覆盖探测的新证据见同任务角色报告；
不以合成schema修订宣布历史数据/标签完整或训练已就绪。

## r2 有界复核：六项 ACCEPT（仅设计）

Dispatch `QF-DISPATCH-20261028-QR007-SCHEMA-RECHECK-1`。覆盖规范先独立提交为
`2f283ee17a59d48b9e8bcc5cb523c4ef39ccbc36`，本复核另作提交，只修改review与角色报告。
只读 QD commit `a183e40ed27b2250f7030ce3babbe5d579dc268b`，相对已审
`d474fdf0fdca7cb22aa47cfb220806b8ea2ab84f` 的完整两文件差异及相邻条文。
QD工作树与提交字节一致；`qd007-synthetic-r2`精确身份：

| 文件 | SHA256 |
| --- | --- |
| research/qd007/schema.md | 6e5fea553aedcdf6d800ced8a2ba5d0d49b5abd0b60cf931417fd6dff78408b7 |
| docs/agent-reports/qd/QF-QD-007-ledger.md | 3b129fe20f3ad74ec01d1257f25154f61967a8c3b34503e7ada48d3da129476a |

下列行号只对应上述r2 commit。**QR007-R01—R06全部设计级ACCEPT，无剩余schema
修订请求；可供负责人交接有界实现与独立验证。** 不把允许的profile限制扩大为
历史重建能力，也不因覆盖方案尚待决而阻塞此合成接口交接。

| 项目 | 精确闭合位置与结论 | 实现后仍须独立验证的原反例 |
| --- | --- | --- |
| R01 ACCEPT | schema126–137、573–605：完整config/catalogue留在Audit，causal_policy精确排除source_manifest，Snapshot含policy hash且明确preimage，不含未来source/hash | 相同初始政策，仅改20时future T并重hash整个catalogue与旧source_refs，snapshot10内容/hash相同，audit不同；换已声明政策不要求hash相同 |
| R02 ACCEPT | 208–220、512–523：whole-candidate对预声明calendar先检查可用性，再只用已可用库存经济排序；还拒绝可用顺序中的逆向fill；限制明确且可接受 | F7/available9跨S8时，F单独或[F,S]/[S,F]都拒绝，已提交S保持；F7/available7正例通过；同刻两种tie仍各自固定 |
| R03 ACCEPT | 295–317：valuation<=valuation_available<=snapshot，年龄按snapshot，known覆盖全部公式输入；允许final rate较晚；不添加posthoc mark情景 | S80/mark79 available90拒绝；mark79 available79、rate95、known95/available100通过，99仍未知，100才识别T |
| R04 ACCEPT | 364–390、619–639：入库合法性与query充分性分开，current available assertion heads确定状态；合法过期不stop；null mapping在本实例明确永久未决 | 10 complete，20 T修订后immature，21现金结清但旧refs仍immature，22 successor才complete；整批/分批一致；null-authority可被有效successor替代 |
| R05 ACCEPT | 95–108、285–294：各逻辑kind的ID在ledger内有唯一owner，派生ID同受约束；allocation hash纳入完整owner域，跨引用再核对kind/币种/trajectory/scenario | BTC/ETH同fill f1拒绝，f_btc/f_eth及不同义务可共用账户；跨币退款/lot/assertion引用拒绝，未变更状态 |
| R06 ACCEPT | 474–498、544–571、591–655：已知Posting始终记录现金，未知pending/A/L delta为null；未知聚合/coverage issues可见，输出字段及本地null原因明确 | T未知、b=-.02时C999.98/B-.02，P/A/L/E/budget未知；后T=-.05时C不变、P-.03/L.03/E999.95，未知前值delta仍null |

直接回归检查：S02在448–462保留正负/零、过粗残差拒绝、1/1/1与2/1剩余FIFO
路径及累计-.01→-.02归属重算；不新增现金。R06选择每个义务/Posting一条余额entry，
逐lot归属另由allocation/slice保存，因此不能把同一现金在每个分配行重复累计。
无新增native adapter、网络或市场情景；namespace保持局部，profile明确r2。

使用标准库进行38项身份/差异范围/独立字面算例/结构检查，全部通过。其中hash
与排序例子是逻辑见证，不是伪造完整producer payload来声称已通过API；期望值未
调用QD helper。34项稳定A ID仍恰好映射一次，代码/测试文件仍不存在。账本实现、
原子事务、逐字段输出检查、独立污染检测与完整数据回放均要等实际代码后验收。

覆盖D01–D04仍待负责人持具体方案与用户决策，与本合成schema ACCEPT分开。
当前不写validator或QD代码；提交此复核后停止等待实现交接。没有启动任何fit。

## B1 — 费用总额未知时的当前切片归属（实现准备发现，待QD落版）

`QF-CONTROL-20261028-QR007-FEE-NULL-B1-1`。r2允许fee ObligationRevision将T变为
null/UNKNOWN_AMOUNT，但ClosedSlice两个fee字段仍是D，无法表示当前未知归属。
QR同意下列最小修订建议，**不替QD编辑schema**，等待精确修订commit/hash后更新
验证器的schema绑定；r2原六项设计ACCEPT记录保留，不把新问题算成已通过的实现。

建议精确文字：`ClosedSlice.entry_fee_cash_usdt`与`exit_fee_cash_usdt`改为`D|null`。
在当前查询cutoff，若其对应entry/exit fee obligation的最新可用T未知，该字段为null，
该切片本地null_reasons的同名字段必须为UNKNOWN_OBLIGATION_TOTAL。两侧分别判定；
另一侧已知费用、funding（若已知）、数量、时间、归属ID、realized_price_pnl保留。
后续已知累计修订按已接受FIFO历史关闭路径恢复当前精确归属，不能重记现金；旧
cutoff的已知归属保持不可变。不得用旧值或0替代当前未知值。

独立最小轨迹：开10张，m=.001，entry49900/exit50100；entry费-.2495、exit费-.2505，
gross2，无funding，原费用均已Posting，C10001.5。

| 当前可用修订/Posting | entry_fee | exit_fee | 当前净切片派生值 | 现金与其他状态 |
| --- | --- | --- | --- | --- |
| 原已知两侧 | -.2495 | -.2505 | 1.5 | C10001.5，gross2 |
| entry fee revision2：T=null | null/UNKNOWN_OBLIGATION_TOTAL | -.2505 | null | C仍10001.5，entry B仍-.2495；P/A/L未知，聚合A/L/E/budget按R06未知 |
| entry fee revision3：T=-.2 | -.2 | -.2505 | 1.5495 | C仍10001.5；entry A=.0495，E10001.5495，旧未知cutoff仍未知 |
| 独立refund Posting +.0495 | -.2 | -.2505 | 1.5495 | C10001.5495，A0；不能因恢复归属先行改现金 |

对exit费做对称案例，另测两侧同时未知；未知条件仅影响对应字段。部分平仓时同一
费用义务影响的所有已关闭片段都应未知，不能只清最后一片；恢复后分摊仍合计为
精确累计费用，旧记录不可回写。错误负例包括null缺原因、已知T却返回null、未知T
返回旧数/0、清空另一侧已知费用、错误传播到gross/数量、恢复T时自动退款。

连带传播：S1没有新增episode净额字段，不需发明字段或新状态枚举。独立检查器若
派生切片fee总额/net，当任一必需费用/funding归属未知时结果也是null；不得忽略null
求和。账户T/B/P与aggregate A/L/E/budget继续执行已有R06。原Fill/Leg描述原始成交
费的审计值仍保留已知原值，不作为当前修订归属；已知Posting/C/B不随归属未知而
消失。此补丁不改输入手续费公式、已观察现金或标签目标定义。

## VALIDATOR-1 — 独立验证器准备检查点

基线 `4d2f57a65456c299bb7d05a64e119d01a251a2b9`，分支
`codex/qr-validation-baseline`。本轮仅四个独占文件：本文件、
`research/qr007/validate_event_ledger.py`、`tests/qr_research/test_qr007_ledger.py`
和QR007角色报告；coverage两文件、QR006、native/QD代码、共享日志均冻结。

验证器绑定已接受r2 schema commit `a183e40ed27b2250f7030ce3babbe5d579dc268b`、
SHA256 `6e5fea553aedcdf6d800ced8a2ba5d0d49b5abd0b60cf931417fd6dff78408b7`、
profile `qd007-synthetic-r2`。这不代表B1已落版；代码保留原r2字段类型，并通过
`PENDING_CONTRACTS`拒绝任何producer执行。负责人已冻结B1提案，SHA256
`8e6e1af12fd5bc1257ee78f5fb21d11d58bf8eeb6c7532a9d47ca57f37228bd1`，交QD编辑；
QR仅记录交接身份，未读取动态producer，也未认定其实现已通过。

新模块只使用标准库。21个已准备用例覆盖精确费用与返佣、正负资金费、累计总额
与独立现金Posting、FIFO分批/加仓/反手、未知传播、事件可用时钟、未来事实污染、
成熟断言失效/接替、双币归属、重复/冲突/原子失败、深复制、覆盖缺失、保守预算、
同刻资格及as-known/restated。34项A标准逐项保留本阶段与后续覆盖/回放/标签范围。
期望金额由字面常量和独立Fraction恒等式提供；不调用QD helper计算期望值。

输出检查包括递归封闭字段/类型、null原因、输入来源hash、现金源逐笔与FIFO价格
盈亏对账、T/B/P和分开汇总A/L、预算、单位守恒。`--snapshot`只检查显式给定的
A11单状态文件；重新计算输出hash仍不能掩盖协调篡改C/E/budget或T/B。它不对
producer签发PASS，也不完成市场回放。实际实现入口仅接受显式文件、commit、
SHA256和schema，并核对精确提交字节；不搜索候选文件。输出只写新路径，原子发布，
拒绝覆盖和符号链接。Python socket guard不是任意代码的操作系统沙箱。

验证结果：**23项自身测试通过**，含成熟度未来时点/阻断状态负例；CLI `--prepare`
返回 `PREPARED_NOT_EXECUTED`，21 prepared / 0 passed / 0 failed / 21 not executed，
producer_executed=false、target=null、market_requests=0、model_fits=0。
测试临时路径显式resolve，避免macOS `/var`别名触发预期外的符号链接拒绝；真正的
符号链接负例仍被拒绝。这是测试fixture修正，不是producer问题。

下一步：负责人交接QD的B1精确schema/profile与已提交producer身份后，另行更新
绑定、补B1对称未知/恢复用例，再执行真实producer独立验收。当前提交是PREPARED，
不是S1实现通过、市场就绪或训练批准。用户选择的成交量精度前置条件继续有效。
