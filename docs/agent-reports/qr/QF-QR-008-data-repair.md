# QF-QR-008-DATA-REPAIR：有界数据修复审查

2026-10-28 Australia/Melbourne，QR。
Dispatch QF-DISPATCH-20261028-QR008-DATA-REPAIR-REVIEW-1；补充工程输入
QF-CONTROL-20261028-QR008-QD-ENGINEERING-INPUT-1。
基线 c6b685aeaf1484212fd628623a86a2366c741510；
工作树 /Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot；
分支 codex/qr-validation-baseline，开始时干净。
结果提交标题 Review BTC ETH exact volume recovery and MARK alias proposal；
确切commit/hash由Git结果随交接给出，不在提交内容中自引用。

**READY_FOR_BOUNDED_ENGINEERING：** 精确格式/聚合/血缘/拒绝规则可交QD准备实现。
**REQUIRES_USER_DECISION：** 整段来源政策及BTC close冲突，只有QR008-DATA-SOURCE-1。
**BLOCKED：** 数据晋级、市场回放/标签/训练；本报告不是新数据验收PASS或训练READY。

## 已完成及四文件独占范围

- research/qr008/volume-recovery-protocol.md：独立事实、来源选项、精确OHLCV与周期
  规则、分工/门槛，附可完整重现的只读审核脚本和oracle自测脚本。
- research/qr008/volume-recovery-spec.json：封闭新候选schema、来源policy、单位/时钟、
  聚合/哈希/发布/资源边界、分阶段验收；148文件身份、90归档/12REST及全部4221条
  不同小时（4222字段差异）保留双方行号/hash和值；MARK独立结果及保护指纹。
- research/qr008/mark-archive-amendment.md：仅完全相同四字符串的相邻别名规则v2、
  原始row全部保留、正反例、剩余gap/required-query验收、固定71GET续段预算提案。
- 本报告：当前结论、执行证据、限制、对QD和负责人的交接要求。

三份交付SHA256：

| 文件 | SHA256 |
| --- | --- |
| volume-recovery-protocol.md | c71cae75331346e000c231c522db88e383a41cbefcdfb7deb44fd97f8fd67327 |
| volume-recovery-spec.json | cd0e123d019b428e7bd12754e553c0322d4aac5593537b07752bab777280bdc0 |
| mark-archive-amendment.md | 0b33bf4272bbb87bb33d1e19fe27ab7e5a7765ddd2b98baf4a4678530bc17ece |

QR006五份、QR007四份、旧QR008 coverage两份共11个冻结文件与base字节完全相同。
未写其他角色文件、共享PROGRESS/DECISIONS、native代码、旧数据或主仓。

## 实际独立核验

输入handoff SHA256 c5379daae4134db20f3077d1d15c8552798996b6cb4fd45de80290b03c5f6baa，
完整读取并验证其12个文件，明确plan目录名与原PROPOSED状态不代表采集未执行。
独立脚本没有运行intake、导入QD helper或抄用其汇总作为结论；原始数据用Fraction
精确读取/算术，本轮脚本禁用socket连接。

| 检查 | 实际结果 |
| --- | --- |
| 148份原证据/数据文件SHA | 全部匹配；包含v1/v2 manifest、v2八数据文件及四lineage |
| 90份小时归档 | 完整gzip/CRC；每币45份/32856小时；严格全格、OHLCV域、源行、v2值与available全一致 |
| 8份decimal原始响应 | 1605089 bytes，两币各7296小时；1900/1900/1900/1596四段、精确唯一完整时间格；无空/错域量 |
| 4份固定单小时确认 | 446 bytes，所有原字段与对应bulk完全相同；不增加canonical小时数 |
| 原v2 4h/day与原小时 | 两币各8214/1369桶，所有OHLCV和父行血缘精确一致，截至9月末 |
| 差异全枚举 | BTC volume70/close1；ETH volume4151；完整4221个不同小时记录，无策略/收益筛选 |
| MARK对象 | 19份既有raw hash/bytes复核；只对隔离202310BTC完整逐行解析 |
| 独立规则自测 | 33项通过，包括精度/非法值/聚合缺行及顺序/UTC边界/别名正反例/可用与新鲜度边界 |
| 重现 | 从Markdown抽取两段脚本重新执行，输出与spec保存audit/selftest对象结构全等 |

ETH非整数REST volume4106小时，首条在2026-03-24 02:00 UTC；不能视作历史规则
生效日。BTC70和ETH97条差异不能仅由整数截断解释；ETH其中52条同时有小数差异，
4,054条仅呈小数部分差异。90份旧archive量均整数，未发现本地额外损失，但未证明
供应商归档生成前/历史修订中没有损失。

唯一BTC close冲突：2026-08-28 14:00 UTC，79513.6→79509.9，volume同时
108955655→108945436；原归档request-00211行663、v2行32055、bulk行795及固定
确认行1全被hash定位。4个确认支持窗口一致，不证明REST或归档何者是真值。

MARK隔离对象d5e832810809baeb9aa1663e23b5b92a03a49cabe70f6778aedb2f8898dafb53：
206377行、5个相邻四字符串完全相同别名、0降序/冲突；候选规范点206372。
最大间隔147.973929秒，>60/>120/>180计数1/1/0，不能据重复规则直接宣称查询覆盖。
只在内存分析，未发布规范point表；required_query_coverage仍NOT_EVALUATED。

另只读3个官方页面核验公告计划/能力字段及CSV格式，链接和边界在protocol/spec；
未增加行情请求。另用git show读取QD精确commit
74839dfc67d0db3c368d85761dfe6d41f29ce1c6的工程plan/report并验证两个SHA：
dfa460f4c8aa9646f12da0a88d4122198371c46fdbf13849e71653a3f5d75331、
35ce317e3dae6379fea5cb2572e223c884831d899ec2a0e3481753a9e84a64ac。
只接受其独立builder/whole-row/精确算术/原子发布方向；未读取或执行动态QD007。

## 重现命令及保护检查

在QR工作树执行以下命令，输出两组FULL STRUCTURAL EQUALITY PASS：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python - <<'PY'
from pathlib import Path
import json, os, re, subprocess
doc = Path('research/qr008/volume-recovery-protocol.md').read_text()
spec = json.loads(Path('research/qr008/volume-recovery-spec.json').read_bytes())
for marker in ('QR008_RAW_AUDIT', 'QR008_POLICY_SELFTEST'):
    code = re.search(r'<!-- '+marker+r' -->\s*```python\n(.*?)\n```', doc, re.S).group(1)
    result = subprocess.run(
        ['/Users/lzh/Development/Project/gate_quant_bot/venv/bin/python', '-c', code],
        capture_output=True, text=True, check=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    expected = ({'independent_audit': spec['independent_audit']} if marker == 'QR008_RAW_AUDIT'
                else spec['verification']['oracle_selftests'])
    assert json.loads(result.stdout) == expected
    print(marker, 'FULL STRUCTURAL EQUALITY PASS')
PY
```

审计代码hash d7ebf8814956e90de04fc41c3ab8eb8c1f4568e4f42587140b3b07c164d1dda1，
oracle自测代码hash b29e5a8236bddacbfc9182846e8c0609d40aca83d2a725a02b92f17a7043d71a。
spec额外交叉核验148/90/12/4221/4222计数、84878总行数、null用户批准、33自测、
98-17剩余attempt与2GiB-34975986剩余bytes均通过。不是QD producer测试。

主仓HEAD/分支/staged diff/原始index/unstaged diff/完整porcelain status及72行数量
与既有7项基线一致；源main HEAD仍cae0d2395adf2cd3905e41cb1c16748c8247c32c。
原staged diff SHA c8dbdd039635d01220423816909d3b87f04bfe550ee8c79efc078bc6a1e144ce，
index SHA 7b518de8325f6f420207fcd49f1821a8fddbe76ffc214fea922180b006c1cf80。
提交前核验仅四个新授权文件、工作树/暂存diff检查；不运行与文档提案无关的应用测试。

## 依赖、唯一决策和下一步

建议负责人转交QR008-DATA-SOURCE-1：A采用事先固定的整段whole-row分源规则
（20251201前archive，此后完整decimal REST），保留历史修订未知并生成候选重验；
B暂不选主源、保留冲突并停止晋级，后续官方澄清另定边界。推荐A，但尚未获得选择。
不能把用户“先修成交量”当成选择有close冲突的来源授权；intake明确要求单独解决。

普通QD工程可先准备解析/精确聚合/类型负例/血缘/无覆盖发布，完整candidate build
等明确来源选择和精确spec交接。新格式JSONL/UTC微秒是本局部契约；不改旧CSV/秒。
后续工程限定两次离线构建、每次300秒/512MiB、合计1GiB，不含网络/原样复制旧数据。
funding/MARK变换、float特征投影、native adapter不在这个最小builder中。

MARK方案只允许相邻四字符串全同别名且保留全row；不同字符串/降序仍隔离。
恢复需owner/QR评审及负责人明确续段交接。旧连续1200秒窗口已过；提案显式继承
已用26.732秒、续段活动处理至多1173.268秒，不假装旧截止有效。固定余71GET，累计
98attempt/2GiB和已用17次/34975986bytes不清零；已收19个raw只复用，不自动重试
隔离对象或重下旧对象。这里没有执行续段。

数据精度修复只是训练条件之一；来源决策/新数据版本验收、MARK所需查询覆盖、
账本独立验收、完整状态回放、成熟自然标签、因果特征与严格时间切分仍须后续完成。
2026年1—9月已暴露开发资料不升级为未见测试集。没有新标签/回放/优化/fit，
没有额外币种、merge/push、应用/交易启动、credentials、Windows/NAS或自动调度。
达到训练条件后先报告证据，开始模型/标准化器/校准器拟合前仍等用户确认。
本四文件提交后按派单停止等待负责人，不发跨聊天回复或自行继续实现。

## 决策问题已转交，答案仍未到

QF-CONTROL-20261028-QR008-SOURCE-QUESTION-PENDING-1确认负责人已向用户提交
QR008-DATA-SOURCE-1。其冻结提案SHA256
c0af38b60d44838b4a684286b87be6b4170f97f38eacb50619643cf9f5d32f3e已只读核验，
与当前协议来源决策节一致，未实质修改该节。当前无用户答案，仍保留
user_approval_ref=null / REQUIRES_USER_DECISION；不重复提问、不等待或轮询负责人，
完成本四文件提交后停止。推荐选项不是授权。

## 审计身份与因果投影澄清

QF-CONTROL-20261028-QR008-CAUSAL-VS-AUDIT-IDENTITY-1已纳入protocol的
“审计身份与因果投影分开验收”段、spec identities/invariants/expected_tests。
同固定catalog重复构建要求数据/血缘/差异字节稳定；合法未来内容改变且全catalog
重hash时，旧行的审计身份可以变化，已闭合桶经济值及可用时钟投影必须不变。
全catalog证据保留，禁止以audit hash/来源身份/未来目录作特征、经济状态、策略分支
或随机种子；不能删provenance来伪造整行不变。此为测试断言一致性澄清，未改变
来源A/B、原始数据、拟合门或新建经济字段。对应未来污染producer测试仍待QD实现，
不把这段文字计为已执行的测试。
