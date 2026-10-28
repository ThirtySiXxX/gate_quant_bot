# QF-QR-007-READINESS 预检检查点

日期：2026-10-28 Australia/Melbourne。角色：QR。
预检结论：**PASS（仅文档/验收准备）**。
当前依赖：**AWAITING_QD_EXACT_SCHEMA**。实现验收未执行；市场经济覆盖/训练就绪仍未达。
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
