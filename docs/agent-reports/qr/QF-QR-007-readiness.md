# QF-QR-007-READINESS 预检、schema审查及经济覆盖规范

日期：2026-10-28 Australia/Melbourne。角色：QR。
当前结论：**SCHEMA_REVISE_REQUIRED（六项定点修订）**，见schema审查记录。
覆盖规范子步骤：**SPEC_READY_FOR_REVIEW / PROPOSED_NOT_ACTIVE**，见最新记录。
预检结论仍为 PASS（仅文档/验收准备）；以下原预检记录保留。
当前依赖：QD 修订精确 schema 后复核/负责人交接。实现验收未执行；训练就绪仍未达。
Dispatch QF-DISPATCH-20261028-QR007-PREFLIGHT-1，补充 DECIMAL-SCOPE-1；
CAPACITY-1只恢复同一任务，没有改模型或扩大范围。

工作树 `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`，
分支 `codex/qr-validation-baseline`，本检查点基线
`52ce1ebeb054abd49c41fc4acbb4c7b7eb41c762`，起始干净。
先读 AGENTS 与六份必读政策，检查分支/暂存/未暂存/未跟踪；分配目录没有更具体AGENTS。
语义对齐 QR006 `c7e9a2492247fa31e216035f87e8bb20cca6e6ad` 和 QD006
`9bb3c0ec2b57e7154a51e56d795645c273c1308d`。用户已授权普通训练准备继续，
不再援引旧设计文档暂停离线实现；拟合及新范围/重大假设仍保留各自边界。

## 已完成与文件

仅新增三份文档：

- `research/qr007/ledger-review.md`：34项稳定ID逐项阶段映射，费用/资金费/现金待决
  独立字面oracle，幂等/修订/因果/未知/事务失败负例，精确schema到达后的审查清单。
- `research/qr008/coverage-protocol.md`：只读现有BTC/ETH证据、实际精度发现、科学核验
  与候选假设/用户决定分离、14次市场尝试的有界probe及下一步最小训练准备方向。
- 本报告 `docs/agent-reports/qr/QF-QR-007-readiness.md`。

未来也获独占分配 `research/qr007/validate_event_ledger.py` 和
`tests/qr_research/test_qr007_ledger.py`，但QD尚未交精确API，当前不创建这两个文件。
既有src/tests/QR006/共享日志/旧实验没有修改。检查点通过负责人传递，不跨聊天派单。

## 证据与结果

重新hash确认v1 manifest的210份raw及v2的8份normalized/4份lineage匹配，未覆写。
manifest身份：v1 `5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd`；
v2 `cbe95174e6eca704353a06f89e68294ec58a81cc6a59f370bb424c51d1177808`。
这不是重复完整QR005验收，也不证明历史经济完备性。读取现有公开metadata、原始
请求格式、funding来源和时钟，所有本次市场API/数据下载为0。

实际发现：BTC快照enable_decimal=false/min=1，ETH=true/min=0，原请求未声明
小数数量响应header。ETH的0值不能作真实最小量；整数研究执行子集仍可能兼容，
须核验grid/min/乘数；旧JSON volume存在需核验的精度风险，不能泛化到全部CSV归档。
推荐先明确小数格式的单币metadata和相同末端窗口trade核对，不为全合约自动改schema。

研究可继续使用明确命名SCENARIO，不必收集真实账户资料；科学上不可省略来源/单位、
mark price kind、source-to-snapshot映射、可用时间与未知/结清区别。建议的mark代理、
到账/finality时钟仅供review，未自动冻结。若仅部分历史可验证，按规则生效和覆盖
连续交集评审，不按收益改日期；原数据/开发窗口完整保留，训练充分性重新判断。

## 验证方法、局限与后续

本轮只使用既有解释器标准库做文档、hash和字面算例检查；没有导入被测QD算术或
应用训练模块。34项设计不是34个已执行测试；完整labels/purge/replay相关条款被明确
分到后续阶段。交易金额/费率边界仍不能据此认定实际Gate历史已重建。

QD下一步交确切schema.md/API及commit/hash，负责人转交QR；QR再给精确PASS/REVISE/
BLOCKED并编写独立验证代码。若schema不支持某些已接受语义，会指出反例，不能改
测试去迎合实现。市场覆盖缺口不阻止当前纯合成账本准备。

剩余训练路径：合成账本实现/独立验收 → 覆盖补证与具体情景冻结 → 完整状态回放 →
成熟净收益标签与依赖审计 → 可检验训练/样本外计划 → 用户确认后才拟合。
旧QR001已有隔离训练与失败晋级证据；本轮新协议的市场标签与训练均未开始。
不扩币、不运行模型、不改风险默认、主仓、Windows/NAS、引擎或应用，不安装依赖，
不merge/cherry-pick/push。提交此检查点后等待负责人交QD schema，继续同一活动任务。

## 本检查点实测记录

33项文档/独立字面算术/阶段ID/范围/保护断言通过；先前同检查点已重新验证
210份raw与12份v2 normalized/lineage的SHA256。原主仓HEAD、索引字节、暂存diff、
未暂存diff及状态hash均与既有保护基线一致；5份已接受QR006文件hash一致。
检查通过已有venv/bin/python的临时stdin标准库脚本运行，没有保存猜测接口的代码。
本检查点实现测试、市场请求、新市场标签与任何fit均为0。

| 预检文件 | SHA256 |
| --- | --- |
| research/qr007/ledger-review.md | 4d74f207c5c174ff4a3fe789852435f8f963ec9558d6ea0224ff518d18476b8b |
| research/qr008/coverage-protocol.md | e38b60d1e37ca926e2f53b06129b9ff60933c9d48ee529230f70d704a21a899c |

报告本身由最终commit及另外输出的hash识别。提交前执行git diff --cached --check。

## 精确 schema 审查检查点（在预检 commit 之后）

Dispatch `QF-DISPATCH-20261028-QR007-SCHEMA-REVIEW-1`；QR干净起点
`8993073e71b578f34b234403ab8ea7b1d803a16a`。补充只读证据
`QF-CONTROL-20261028-QR007-PROBE-RESULT-1` 不开启新任务。

只读审查 QD commit `d474fdf0fdca7cb22aa47cfb220806b8ea2ab84f` 的完整529行schema
及125行角色报告，二者工作树字节与git对象一致。schema SHA256
`800919cf19f02b7b7f896347f378eeef994607f2f13383d01adac1ef921f191b`；QD报告SHA256
`62185bd1287d96de8ae1769f262858e80a39823c1cf29243892dfa0a5f263d7d`。

局部设计接受严格JSON/decimal/us、T/B/P、FIFO与全批原子拒绝、受限SCENARIO和
明确未知booking的处理方向。S02过粗quantum的反向残差拒绝可接受，补充正负/零、
连续部分平仓和累计修订的字面oracle。其余六项为 **REVISE**：

| ID | 最小修订及验收目的 |
| --- | --- |
| QR007-R01 | 完整未来fixture身份与因果state hash分离，未来修订扰动不能改过去hash |
| QR007-R02 | 可用信息顺序与经济库存排序明确，迟到fill不能经整批排序提前满足快照资格 |
| QR007-R03 | funding formula区分causal mark与后来才可知的final rate，不能用未来mark冒充当时代理 |
| QR007-R04 | 断言入库合法性与当前覆盖充分性分离；合法过期/未知/硬冲突分别表示 |
| QR007-R05 | BTC/ETH业务键与派生episode/lot/allocation ID命名域一致，引用不得串币 |
| QR007-R06 | T未知而Posting已知时仍记录现金，但A/L delta不得伪装数值0；精确输出null字段补齐 |

每项的固定schema行号、最小反例和接受条件在
`research/qr007/ledger-review.md`。这是设计级审查，未对不存在的QD实现报告测试失败。
本轮只修改该review和本报告；`research/qr008/coverage-protocol.md`保持原hash。
QR006协议/接口/验收文件、共享日志、native代码与任何旧数据均未修改。

## 负责人公开探测的补充证据（QR只读验证）

目录 `/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination/public-probe-20261028-r1/`。
`plan.json` SHA256 `5ccfc1ede19464d1a5ae8e1c210ad027628727de558a2c66bc45a757824e3f04`；
`result.json` SHA256 `e1799d0171b6eacd64dbfa87f7aa33229dc9e9ae4b755a6fa512f0b4db7def43`。
QR重算8份公开raw body的bytes/hash，并独立核验两份MARK尾段的唯一时间网格。
不是QR另行请求；所有本轮QR市场请求仍为0。负责人批次8次GET、0retry后按两次
连续硬失败停止；不增加下载，也不修改原始v1/v2。

- `X-Gate-Size-Decimal:1` 当前公开metadata：ETH min="0.1"、enable_decimal=true、
  multiplier="0.01"；BTC min="1"、multiplier="0.0001"。两币taker="0.00075"。
  min不是已证明的quantity step；当前值不补历史规则，也不自动改变合成.0005费率。
- 2026-10-27 07:00—09:00 UTC，两币trade 1h各2条；ETH原始v字符串为
  ["9654416.2","5553894.2"]。旧尾段逐行差异对照由负责人继续，QR不重复执行；
  该证据不能泛化为全部归档存在相同损失。
- 同期MARK 1m两币各120/120，时间网格无缺失/重复。它证明这一固定窗口可得，
  不证明精确瞬时结算mark、来源历史可用时刻或完整长区间覆盖。
- 2023-01-01 07:00—09:00 UTC两币MARK请求各HTTP400，响应为过旧数据/最近10000点
  限制。其余2025/2026固定旧窗口未请求：状态只能为未验证，不能说也失败或可得。

此证据强化coverage限制，不改已冻结probe预算或经济协议；不能以尾段成功宣布
训练条件满足。官方历史归档支持由负责人继续只读核查。

## 本轮验证及停点

使用既有解释器标准库复核文档身份、独立字面算术、六项review ID、34项阶段映射、
公开probe hash/尾段网格、QR006及coverage文件不变、主仓保护基线和本轮两文件范围。
这些检查通过；8份body hash、两币各120点MARK网格、5份QR006冻结文件及coverage
hash一致。主仓HEAD、分支、暂存/未暂存diff、索引字节、状态hash/72条目均匹配。
首轮status校验用了默认目录汇总（53行），改回基线的
`git status --porcelain=v1 --untracked-files=all` 后hash匹配；不是检测到主仓变化。
最终commit/hash在交付消息列出。未创建validator/producer代码，未运行
应用回归或拟合；schema不存在可执行实现，不能记为账本PASS。

QD下一步给出六项修订的具体位置、选择的边界和正负例，负责人转交后QR复核；当前
按交接要求提交独立检查点并停止。无需重复询问普通离线准备授权，但不越过接口
协调边界开始写猜测API的验证器。没有merge/push、实时订单、模型激活或服务变更。
训练仍须完成账本独立验收、覆盖与情景冻结、完整状态回放、成熟标签/切分与依赖
审计、训练/样本外方案冻结；到达条件时再报告，任何fit开始前仍须用户确认。

负责人收束指令 `QF-CONTROL-20261028-QR007-REVIEW-CLOSE-1` 已到达：用户选择先
验证至9月末，经济验证范围截止2026-10-01 00:00UTC，10月待补证，原2024训练/
2025验证划分暂不变。负责人另提供mark归档及9月volume差异证据目录，留待下一
coverage任务精确核验；本次未读取/验收这些新归档，也不据其扩大六项schema审查。

## 经济覆盖规范检查点：QF-DISPATCH-20261028-QR007-COVERAGE-SPEC-1

本轮从干净QR commit `c4b1fdcb90427a6229bd75d8abbff66fcb795047` 继续同一任务。
六项schema review已交QD，当前只推进独立覆盖文档；不修改ledger-review或创建
validator。固定范围 `[2023-01-01,2026-10-01)` UTC，仅BTC/ETH，2023 warmup，
2024/2025训练与验证设计暂不变，2026仍是已暴露开发资料；fit授权仍为否。

### 完成内容与独占文件

- 更新 `research/qr008/coverage-protocol.md`：当前可执行计划、四项待审情景选择、
  分层验收；原预检保留为历史，旧10月/minute-REST方案明确失去当前效力。
- 新增 `research/qr008/coverage-spec.json`：固定45个月/90对象清单规则、2份复用、
  88次GET与最多10次重试；精确资源/类型/时间/缺口/停止规则、41份本地证据身份、
  12份只读代码身份及12项具体验收案例。它是待审数据，不是采集器或账本实现。
- 本报告。QR006、已提交ledger-review、QD源码、native代码与共享日志均不修改。

### 本轮真实核验及结果

1. 复核四个负责人证据目录的plan/result/amendment与原始文件hash。完整解压并逐行
   核验202301两份MARK：共274873行，严格递增无重复、四列正价格、UTC小数秒精确
   转us且在月范围内。BTC/ETH分别202695/72178行，最大gap286.055879/292.342187秒，
   >60秒gap为2/3，>120秒各1。CRC与压缩/解压字节数匹配原记录。
2. 核验8份HEAD记录；保留首个HEAD本地退出56的amendment。202508/202604的200
   不替代完整对象验证，202610的404不进入固定清单。完整已有样本仅2/90。
3. 重hash并逐行对照9月原始candles gzip与两份decimal API：ETH22UTC差0.2合约，
   两币共四行OHLC相同，另三行volume相同。不是全历史修复或误差上界。
4. 已有funding在新范围每币4107条；不把条数解释为真实完整8h日历。只读追踪
   strategy_signals/trend/vol/timing/execution/carry/crypto_ml/backtest等代码依赖。
   固定币种ML-off路径未见volume使用；FEATURE_VERSION=1的ML路径明确使用volume。
   原QD canonical_history.py要求整数volume并按int聚合，故decimal修复需要新数据版本。
5. 重新核验两个官方文档页，确认月度MARK路径和四列格式；未请求任何行情接口。
   所有新市场下载、回放、标签、模型/scaler/校准拟合均0。没有应用导入或执行。

### 推荐与未决项

下载提案上限98市场尝试、单压缩64MiB、全批2GiB（含复用及失败bytes）、单解压流
256MiB、串行、单请求30秒、全批20分钟。缺失/部分/拒绝保留；不改日期直到返回
好数据。采集计划经负责人评审交接可独立推进，本轮不执行。

需在市场回放前记录的四项选择（当前均未生效）：

- D01：MARK源时间+60秒、source age<=120秒为主情景；+120/<=180秒延迟压力。
  source t原样作命名合成funding snapshot、下一整点rate可用、再+60秒booking、
  完整条件成立后+1h assertion。真实settlement/publication未知，不能称historical-exact。
- D02：推荐独立研究版本暂不使用volume相关特征/质量门/容量估计，保留v1/v2及旧
  模型schema。删除volume特征改变特征含义，需要新身份与用户选择；本轮没有激活。
- D03：推荐0.00075为主成本、0.0015为压力，0.0005保留命名参考；不按收益选便宜值。
- D04：整数票据配明确反事实恒定乘数，或另补历史grid/转换依据；当前min不是step，
  成交量精度问题与整数执行政策分开。无实际历史交易/保证金有效性结论。

后续还需QD回放适配延迟funding、明确carry年化cadence及已接受的执行数值参数，
不能直接送入按source timestamp对齐的native carry后声称因果时钟已一致。

### 验证、限制和交接

对JSON做严格解析/无重复key/有限数/清单和预算/UTC边界/整数us/独立时钟字面算例/
来源hash/文件范围检查：**96项文档/spec断言通过**，包括41份证据和12份只读代码
身份，主仓七项保护字段/72条目及5份QR006文件保持基线。git diff --check通过。
这不是96个市场回放或账本测试。完整MARK市场coverage尚未产生；
规范PASS、两份样本PASS、全量完整性、因果经济可用性、模型充分性是不同状态。
新模型还需schema/账本验收、全量覆盖、命名情景冻结、完整状态回放及标签/依赖审计。

按本dispatch独立提交这三份文件后停止，等待负责人转交QD修订schema；不写validator，
不发起新下载或自动调度，不合并/push或改主仓/NAS/Windows。达到训练条件后再报告，
开始任何fit前仍需用户确认。

本覆盖检查点 `coverage-protocol.md` SHA256：
`27475a730b62f929ea8d429dd333fe5fab6e28bdd611d11d1f3f175f7127f675`；
`coverage-spec.json` SHA256：
`bed49515f4b27b0e46d112c0c313826f243053f6cc54c9a813d165de7fc8e08f`。
报告本身由最终commit及另列hash识别。随后收到schema复核交接
`QF-DISPATCH-20261028-QR007-SCHEMA-RECHECK-1`：先独立提交本覆盖检查点，再另一个
提交只复核QD六项修订；不把覆盖选择D01–D04自动批准或加入schema依赖。
