# QF-QR-UNIVERSE-ASSESS：合约池必要性评估

2026-10-28，Australia/Melbourne。QR。状态 ASSESSMENT_COMPLETE_STOP。
Dispatch：QF-DISPATCH-20261028-QR-UNIVERSE-ASSESS-1；另纳入 SOURCE-NOTE-1
字段语义提醒及 BOUND-CLOSE-1 收尾要求。用户仍在考虑全合约，本次仅文档评估。

工作树 `/Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot`，
分支 `codex/qr-validation-baseline`，干净起点
`c7e9a2492247fa31e216035f87e8bb20cca6e6ad`。
QD 最终设计审查只读基线 `9bb3c0ec2b57e7154a51e56d795645c273c1308d`。
核对其 review.json：34 项 ACCEPT，明确属于设计，不是已实现测试。

## 结论

现在不需要先下载/训练全部合约。建议先完成 BTC/ETH 的经济账本和标签链路，
若目标需要跨币泛化，再批准按历史时点流动性/质量资格的有界子集；全部合资格
合约留待总体覆盖目标、资料能力和资源预算均明确以后。没有运行三池收益比较，
因此这是条件性路线建议，不是数据已经证明哪一池盈利最好。

训练池、固定评估池与未来允许交易池分别定义。当前只评估 Gate 加密货币标的
USDT 线性永续；币本位/反向、交割及非加密标的另列范围，不能混合单位和标签。
报告列出 T1—T7：池/目标决策、账本实现复核、数据/执行情景、完整状态回放、
成熟净收益标签/依赖、冻结训练与样本外方案、用户确认。

## 修改文件与内容

仅新增三个已分配文件：

- `research/universe-assessment/assessment.md`：中文三方案决策表、PIT 与数据/单位
  规则、模型结构/公平验证、定性资源边界、可执行验收建议及训练关键路径。
- `research/universe-assessment/evidence.json`：10 份已核验本地文件身份，4 个官方
  页面观察、访问时间/主张/局限及未能访问的论文记录，源码保护基线。
- 本角色报告 `docs/agent-reports/qr/QF-QR-universe-assessment.md`。

没有更改已接受 QR006、src/universe.py、docs/universe-model.md、运行代码、
tests、共享日志、旧实验或已计划 qr007 目录。此次任务不产生新实现文件 claim。

## 证据与新发现的兼容依赖

现有候选扫描是当前目录/报价上的工程筛选，不是历史训练总体；旧 QR001
确实已在五资产完成隔离训练与校准，主候选未通过交易适用性，不能说项目从未训练。
BTC/ETH QR005 只达到数据一致性合格带限制，新经济标签与训练仍未就绪。

官方文档支持按合约核验 enable_decimal。QR006 的整数张数约定不能未经审核就
扩展到所有合约；可能需要独立版本化类型/单位/解析变更，也需确认 BTC/ETH
选定期间/情景的假设。文档 launch_time 的说明与字段名直觉不同，create_time
亦非已证明可交易上线时刻；保留语义未决，不能虚构完整历史目录。

当前准确合约数、完整历史目录、历史经济证据与每币有效样本量均未取得。
只核验公开文档，无当前市场目录/行情 API 请求，无账户或凭据访问。
NBER 页面返回 403，未用于论文主张；没有为此扩大资料搜索。

## 验证与结果

采用既有 Python 解释器和标准库进行文档检查，不导入应用/研究训练模块。
检查证据 JSON、ID/来源引用、精确 Git 提交与文件 SHA256、三文件范围、
七步关键路径、已接受协议保持、主仓 HEAD/索引/暂存及未暂存状态保持，
以及 Git 空白检查。最终实测结果与内容 hash 在本报告收尾记录。
没有运行完整测试套件：本次没有源码变化或新增可执行测试。

## 依赖、用户决定与停止边界

QD 继续等待；没有恢复自动任务队列。未来账本与生产者由 QD 独占实现，QR 做
语义/独立复核；需各自有界授权和路径分配。扩池前用户需决定目标总体、是否批准
子集资格/覆盖评估及资料预算；训练前则需看到 T1—T6 实际证据和具体训练计划，
再单独确认。当前不请求立即训练，也不实施扩池或修改风险默认。

提交后停止，供负责人读取。没有集成、合并、cherry-pick、push、启停应用/引擎、
模型启用、Windows/NAS 或真实交易操作。

## 最终核验记录

73 项标准库文档断言全部通过：来源 ID/引用/日期/局限、10 份本地证据 hash、
七步关键路径、三文件独占范围、34 项设计接受状态、5 份 QR006 原文件 hash，
以及原主仓 HEAD/分支/索引/暂存差异/未暂存差异/状态与 72 条原状态记录均保持。
核验命令为既有 `venv/bin/python` 的临时 stdin 文档脚本，使用 pathlib/json/
hashlib/re/subprocess；没有保存或运行应用实现、市场模拟或模型代码。
既有策略及旧 QR001 结果仅阅读，不在此轮重新验证其经济结论。

| 本次文件 | SHA256 |
| --- | --- |
| research/universe-assessment/assessment.md | ccdbbb79851f4aeaadab618b83f28e91c2bf2a3122a90c20ecc2b81380d60988 |
| research/universe-assessment/evidence.json | c56e8a13e4e48aa973e1593c65e0b10d0241c4fcda9628ea8c81afa24dc50e24 |

报告自身通过最终提交与单独输出的 hash 识别，避免自引用 hash。
Git 暂存空白检查通过后仅提交这三个文件；完成状态为 ASSESSMENT_COMPLETE_STOP。
本轮新增行情请求、市场回放、标签、模型/scaler/校准拟合、性能 benchmark 均为 0。
