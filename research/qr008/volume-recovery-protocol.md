# QR008：BTC/ETH 成交量恢复与统一周期协议

2026-10-28 Australia/Melbourne。QF-QR-008-DATA-REPAIR。
派单 QF-DISPATCH-20261028-QR008-DATA-REPAIR-REVIEW-1；
基线 c6b685aeaf1484212fd628623a86a2366c741510，分支 codex/qr-validation-baseline。
工作树 /Users/lzh/.codex/worktrees/qr-validation-baseline/gate_quant_bot。

**解析与聚合规范 READY_FOR_BOUNDED_ENGINEERING；主线来源选择
REQUIRES_USER_DECISION；市场回放、标签及训练 BLOCKED。**
本轮核验原始证据、冻结提案，没有构建/激活新数据集。
[机器规范](volume-recovery-spec.json)包含148个证据文件身份、90个归档对象、
12个REST对象、完整4,221条不同小时及MARK记录。不改QR006、QR007、
旧coverage协议/spec、旧数据、native接口或共享日志。

## 独立核验

handoff SHA256：c5379daae4134db20f3077d1d15c8552798996b6cb4fd45de80290b03c5f6baa。
完整读取并核验其12份文件；未运行负责人的intake或复用其解析/比较函数。
下附标准库脚本用Fraction精确解析，禁止网络，验证148份文件身份。
proposal目录及plan里的PROPOSED_NOT_EXECUTED是原计划历史；result与本轮原始
对象核验确认8份bulk和4份确认已存在。本轮新市场请求为0。

| 独立核验 | BTC | ETH |
| --- | ---: | ---: |
| 45份月归档解压/CRC、小时网格/血缘 | 32,856小时 | 32,856小时 |
| 2025-12-01前归档前缀 | 25,560小时 | 25,560小时 |
| 4份decimal REST完整固定区间 | 7,296小时 | 7,296小时 |
| REST非整数volume小时 | 0 | 4,106 |
| archive/v2与REST的volume差异 | 70 | 4,151 |
| 不能仅用向零截断REST解释的差异 | 70 | 97 |
| OHLC冲突 | close 1条 | 0 |
| 原归档到v2的数值/来源行/时钟差异 | 0 | 0 |

8份bulk共1,605,089 bytes；4份固定单小时确认共446 bytes，逐字段完全等于对应
bulk记录。网格递增、唯一、无缺失/超界；非空精确十进制、正价格、非负量、
OHLC关系通过。90份原归档volume全部整数，本地没有额外截断；不证明供应商
生成归档前没有损失/修订。v2两币4h各8,214、日线各1,369也逐桶与原小时精确
聚合及父行血缘一致，仅检查截至9月末区间。

ETH首个观察到的小数量是2026-03-24 02:00 UTC、5623243.7张；这不是合约实际
开通小数张的生效时间。4,151条差异中4,054条数值上仅为小数部分，97条还含整数
差异，其中52条兼有小数与整数差异、45条REST为整数。BTC70条全含整数差异。
BTC差值[-10219,312616]张、合计1226933；ETH[-6203,1373287]张、合计1802138.4。
有正有负，不能靠加0.2、整数转换或容差修补。这不是误差上界或盈利证据。

唯一OHLC冲突在 **2026-08-28 14:00 UTC**：

| 字段 | 原归档 / v2 | decimal REST / 单小时确认 |
| --- | ---: | ---: |
| close（USDT/BTC） | 79513.6 | 79509.9 |
| volume（张） | 108955655 | 108945436 |

归档request-00211物理行663，SHA256
f7720f6f8a8096944cc45cddda92f41dff3f06d47d03d6ce888020bac9252870；
v2数据行32055，文件SHA256
e292642723c6f76e97c7565e4b7ed97a76cf382402a3dcad22a7d902ff069789；
bulk 04-BTC_USDT-4.json数组行795，SHA256
e1ade222608f755a000fcd1042a7f2f9febab120384a741347c7c6210d1e955c；
确认02-btc-close-conflict.json数组行1，SHA256
2945128cd3c0eeff0bf01597bfa5a4dbb9bf3171ca9327f7bda482e130c1cc56。
完整4,221条差异保留逐字段旧/新值、精确差值、双方行号/hash及v2行号/hash，
没有按差值大小或策略结果抽样删除。非差异行的全网格/来源范围也在对象registry中。

## 一个来源决策

推荐 ARCHIVE_PREFIX_REST_COMPLETE_ROWS_FROM_20251201_R1：

- [2023-01-01,2025-12-01)：两币采用已核验的70份小时归档。
- [2025-12-01,2026-10-01)：两币整段采用8份冻结decimal REST的完整OHLCV记录，
  包括BTC close冲突；不只替换volume，不逐字段挑选来源。
- 4份确认只作佐证，不增加小时；旧v1/v2及90份归档保留，20份重叠月归档是影子
  差异证据。所有周期从同一小时基准重算，不按收益或差值大小选主源。

这是可审计的回溯研究政策。“保存响应精度”已验证，“跨周期版本一致性”可由工程
验证；“真实历史没有修订、数据当时已知”未证明。
官方[48788](https://www.gate.com/announcements/article/48788)描述数量字段迁移、
兼容截断与分阶段计划，没有证明每个合约实际生效日或归档正确性。
[49639](https://www.gate.com/zh/announcements/article/49639)的enable_decimal是
能力字段，不能反填历史有效区间。公告与已查整数前缀支持披露后的研究假设，
不是历史真值证明。四个确认只证明所查时点的查询窗口一致性。本轮只读3个官方
页面（另含[归档格式](https://www.gate.com/announcements/article/21688)），无市场GET。

**QR008-DATA-SOURCE-1：是否接受上述整段整记录规则作为新候选研究口径？**

A（推荐）：接受明确披露的来源/修订不确定性，按固定政策生成candidate并独立
重新验收；不会直接开始回放或训练。
B：暂不选主源，保留双方与冲突、阻断晋级；若需官方澄清再单独界定工作。
B不意味着无限采集、缩短区间、price-only、容差或剔除冲突。

需要此决定是因为已批准intake规定non-volume冲突另行解决；这次要改变一条BTC
close，超出纯十进制编码修复。本轮仅供负责人转交，user_approval_ref仍null，
不替用户选择。D01/D04命名情景、每成交0.075%主/0.15%压力/0.05%参考、
BTC/ETH及9月末截止都已确定，不重复提问。

## 精确OHLCV与跨周期契约

候选dataset_revision=3、dataset_id=gate-btc-eth-exact-ohlcv-v3-candidate；
局部namespace=qr008.exact-ohlcv、schema_version=1，与native版本无关。
spec封闭列出所有字段/类型/null原因/身份/发布规则。QD拥有producer，QR拥有
研究语义及独立验收；新增契约先评审，不直接接入旧引擎。

价格为USDT/base，volume为合约张数精确字符串。整数执行票据/反事实乘数与观察
到的小数成交量分开，不把volume乘当前乘数冒充历史base量。缺失、空串、NaN、
float、bool、指数或负量拒绝；真实来源0保留，未知不补0。规范输出去尾零，
原文本留在raw并通过source refs可追踪。算术用系数/scale整数或Fraction；
Decimal必须显式足够精度及Inexact/Rounded异常，不能依赖默认28位上下文。
REST sum留作raw审计，不为旧归档制造quote turnover。

只用选定完整小时流。4h按UTC 00/04/08/12/16/20开桶，日线按00开桶，全部半开区间。
每4h恰4根、每日恰24根相邻小时：O=首O、H=max H、L=min L、C=末C、V=精确和。
日线保存直接小时血缘，1h→1d与1h→4h→1d全部值精确相等；每币全期V三周期和相等。
缺一根不发布完整桶，本任务全覆盖验收失败；不排序修复、插值、前填或补0。
切换时点对齐日/4h边界，不允许跨来源段桶。native 4h/day仅作诊断，不能补改新结果。

每币1h=32856、4h=8214、1d=1369，两币所有周期合84878行。
末桶bar_close恰为2026-10-01可存为完整历史桶；消费者须decision<截止且
research_available_at<=decision，不能在窗口内用到这些末桶或读取10月完成标签。
canonical bar时间为UTC整数微秒，原整数秒精确×1000000。
research_available_at=bar_close是代理；observed_first_available_at固定null及
HISTORICAL_FIRST_AVAILABILITY_UNKNOWN原因。实际取得UTC留在catalog，不能将
2026年取得的快照伪称2023年已送达。修订偏差不会因工程一致性而消失。

独占新输出目录、无覆盖原子发布；manifest绑定批准policy、代码/检查器版本、
输入catalog、各文件hash/计数/范围及差异hash。小时raw引用覆盖全记录；
派生parent/source refs逐小时展开，身份算法避免manifest自引用。
旧v1/v2保留，不改默认/latest、native adapter或FEATURE_VERSION。

**审计身份与因果投影分开验收。** 固定input catalog、policy和代码的重复构建，
canonical数据/血缘/差异输出须字节稳定。若只改变未来原始内容且重新计算整个
catalog，过去行的catalog hash、row_id、content_sha256及raw引用允许随审计身份
改变，仍保留真实全catalog provenance。此时应比较过去已闭合桶的经济投影：
instrument/market/price_kind、周期、开闭时间、OHLCV、research_available_at、
observed_first_available_at及其basis/null原因必须不变；固定来源分段、时钟与
范围，且只扰动尚未可用的合法未来观察。不能对含全catalog身份的整行误断言字节
不变，也不能删来源证据来满足它。catalog/hash/行身份及未来目录信息仅供审计，
不得作为决策特征、已知经济状态、策略分支或随机种子。独立未来污染测试应按此
投影断言；hash匹配只是完整性检查，不是因果保证或历史PIT证明。

QD工程预检精确commit 74839dfc67d0db3c368d85761dfe6d41f29ce1c6的两份文档已
用git show读取并核验hash（见spec工程交接区），未读取/运行动态producer。
其独立标准库builder、保留旧v2、whole-row与原子发布方向与本提案一致。
本新契约选择JSONL封闭记录及UTC微秒；QD预检的CSV/秒属于先前提议，native
CSV/秒格式不改变。父行引用嵌入记录，父文件hash另入manifest；冲突产物还需
保存双方完整OHLCV元组（含未改变字段），不能只输出差值。
后续候选工程限两次离线构建（复现一次），每次含核验最多300秒、每根目录512MiB，
两根合计1GiB；超限保留未发布stage并停止，不扩大。6份candles JSONL及catalog、
discrepancies、checks、manifest的精确交付边界见spec。funding/MARK转换及native
float投影不在这个最小builder内，不把小数市场volume扩展为小数执行票据。

## 分工、验收及停止

| 工作 | 状态 / 下一步 |
| --- | --- |
| 解析、精确聚合、血缘、原子输出、离线fixture | READY_FOR_BOUNDED_ENGINEERING，负责人分配QD文件后可做 |
| 主线policy / BTC close处置 | REQUIRES_USER_DECISION，A/B后才选主线candidate |
| 新候选全量精度/周期/时钟验收 | NOT_EXECUTED，QD精确提交后QR独立核验 |
| MARK重复观察修订 | [最小方案](mark-archive-amendment.md)，待owner审查；不在本轮下载 |
| 市场回放/策略优化/标签/训练充分性 | BLOCKED，仍需数据版本、MARK查询覆盖、账本、标签与切分验收 |
| model/scaler/calibrator拟合 | 0；达到条件后先报告，再取得用户确认 |

本轮33项oracle自测通过，不是QD实现、候选数据集、MARK全90对象或训练PASS。
四文件提交后停止，不同时运行QD007账本，不自行扩大采集或继续实现。

## 重现本轮核验

现有解释器 /Users/lzh/Development/Project/gate_quant_bot/venv/bin/python，
设置PYTHONDONTWRITEBYTECODE=1，无需安装依赖。抽取下面两个标记后的Python代码块
在子进程执行。RAW_AUDIT只读显式绝对路径，stdout是{"independent_audit":...}；
与spec中相同对象结构全等比较。不要将stdout覆盖spec或当成市场数据集。
POLICY_SELFTEST输出33项自测结果。脚本不导入生产模块或QD helper。

<!-- QR008_RAW_AUDIT -->

```python
from pathlib import Path
from fractions import Fraction
from collections import Counter
import csv, datetime as dt, gzip, hashlib, io, json, re, socket

def offline(*a, **k): raise AssertionError("No network in QR008 audit")
socket.create_connection=socket.socket.connect=socket.socket.connect_ex=offline
C=Path("/Users/lzh/Documents/Codex/2026-10-27/referenced-chatgpt-conversation-this-is-an/work/quantflow-coordination")
D=Path("/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot/research/.data")
A=D/"qd004/history-v1"; N=D/"qd005/canonical-hourly-v2"
START,SWITCH,END=1672531200,1764547200,1790812800
SYMS=("BTC_USDT","ETH_USDT"); FIELDS=("open","high","low","close","volume")
REGISTRY={}; checks=Counter()
def sha(b): return hashlib.sha256(b).hexdigest()
def require(ok, why):
    if not ok: raise AssertionError(why)
    checks[why]+=1
def read(p, expected=None, kind="evidence"):
    p=Path(p);b=p.read_bytes();h=sha(b)
    if expected: require(h==expected,"file_hash")
    key=str(p)
    if key in REGISTRY: require(REGISTRY[key]["sha256"]==h,"immutable_repeat")
    REGISTRY[key]=dict(path=key,sha256=h,bytes=len(b),kind=kind)
    return b
def pairs(v):
    d=dict(v);require(len(d)==len(v),"no_duplicate_json_keys");return d
def js(b): return json.loads(b,object_pairs_hook=pairs,parse_float=lambda v: (_ for _ in ()).throw(AssertionError("numeric JSON float")),parse_constant=lambda v: (_ for _ in ()).throw(AssertionError("nonfinite JSON")))
def meta(b): return json.loads(b,object_pairs_hook=pairs)
def dec(s, positive=False):
    require(type(s) is str and len(s)<=128 and re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]+)?",s) is not None and len(s.partition(".")[2])<=64,"bounded_decimal_text")
    q=Fraction(s);require(q>0 if positive else q>=0,"decimal_domain");return q
def text(q):
    q=Fraction(q);n=abs(q.numerator);d=q.denominator;a=b=0
    while d%2==0:a+=1;d//=2
    while d%5==0:b+=1;d//=5
    require(d==1,"terminating_exact_decimal")
    scale=max(a,b);digits=str(n*2**(scale-a)*5**(scale-b)).zfill(scale+1)
    out=digits if not scale else (digits[:-scale]+"."+digits[-scale:]).rstrip("0").rstrip(".")
    return ("-" if q<0 else "")+out
def utc(t):return dt.datetime.fromtimestamp(t,dt.timezone.utc).isoformat().replace("+00:00","Z")
def values(row):
    v={k:dec(row[k],k!="volume") for k in FIELDS}
    require(v["low"]<=min(v["open"],v["close"])<=max(v["open"],v["close"])<=v["high"],"OHLC_domain")
    return v
def canon(v):return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
handoff_path=C/"readiness-r2-raw-evidence-handoff-r1.json"
handoff=meta(read(handoff_path,"c5379daae4134db20f3077d1d15c8552798996b6cb4fd45de80290b03c5f6baa"))
for f in handoff["files"]:read(f["path"],f["sha256"])
v1=meta(read(A/"manifest.json","5f5319175c42ba4a82e25ca128ac58ae3b71be4b82911fd7935cfa3678407cfd"))
v2=meta(read(N/"manifest.json","cbe95174e6eca704353a06f89e68294ec58a81cc6a59f370bb424c51d1177808"))
norm={}; norm_info={}
for f in v2["files"]:
    body=read(N/f["path"],f["sha256"],"v2_normalized")
    if f["kind"]=="candles":
        rows=list(csv.DictReader(io.StringIO(body.decode("utf-8"))))
        require(len(rows)==f["rows"],"v2_file_count")
        norm_info[(f["symbol"],f["interval_seconds"])]=dict(path=str(N/f["path"]),sha256=f["sha256"])
        if f["interval_seconds"]==3600:
            full=[int(r["timestamp"]) for r in rows]
            require(full==list(range(v2["data_range"]["start"],v2["data_range"]["end_exclusive"],3600)),"v2_entire_hour_grid")
            norm[f["symbol"]]={int(r["timestamp"]):(i,r) for i,r in enumerate(rows,1) if START<=int(r["timestamp"])<END}
        if "lineage_path" in f.get("derivation",{}):
            d=f["derivation"];read(N/d["lineage_path"],d["lineage_sha256"],"v2_derived_lineage")
archive={s:{} for s in SYMS}; archive_objects=[]
for f in v1["raw_files"]:
    if f["kind"]!="candles" or f.get("interval_seconds")!=3600 or f["format"]!="candles_csv_gzip":continue
    raw=read(A/f["path"],f["sha256"],"hourly_archive")
    expanded=gzip.decompress(raw)
    lines=expanded.decode("utf-8").splitlines(); require(bool(lines),"archive_nonempty")
    stamps=[];fractional=0
    for line_no,line in enumerate(lines,1):
        r=next(csv.reader([line]));require(len(r)==6,"archive_six_fields")
        require(re.fullmatch(r"(0|[1-9][0-9]*)",r[0]) is not None,"archive_integer_seconds")
        t=int(r[0]);stamps.append(t)
        row=dict(zip(("timestamp","volume","close","high","low","open"),r));v=values(row)
        fractional+=v["volume"].denominator!=1
        require(t not in archive[f["symbol"]],"archive_unique_hour")
        nrow,n=norm[f["symbol"]][t]
        require(all(v[k]==dec(n[k],k!="volume") for k in FIELDS),"archive_to_v2_exact_OHLCV")
        require(n["source_id"]==f["source_id"] and int(n["source_row"])==line_no and int(n["available_at"])==t+3600,"archive_to_v2_lineage_and_clock")
        archive[f["symbol"]][t]=dict(values=v,strings={k:row[k] for k in FIELDS},source_id=f["source_id"],source_row=line_no,normalized_row=nrow,raw_sha256=f["sha256"],path=str(A/f["path"]))
    require(stamps==list(range(f["expected_start"],f["expected_end"],3600)),"archive_exact_month_grid_order")
    archive_objects.append(dict(instrument=f["symbol"],source_id=f["source_id"],path=str(A/f["path"]),raw_sha256=f["sha256"],expanded_sha256=sha(expanded),expanded_bytes=len(expanded),rows=len(lines),source_rows_inclusive=[1,len(lines)],start=stamps[0],end_exclusive=stamps[-1]+3600,fractional_volume_rows=fractional,crc_complete=True,url=f["url"],retrieved_at_utc=f["retrieved_at"]))
require(len(archive_objects)==90,"ninety_hourly_archives")
for s in SYMS:require(list(archive[s])==list(range(START,END,3600)),"full_32856_hour_archive_grid")
rest={s:{} for s in SYMS}; rest_objects=[]; confirmations=[]
for directory,confirmation in ((C/"volume-precision-recovery-proposal-r1",False),(C/"volume-discrepancy-fixed-confirmation-r1",True)):
    plan=meta(read(directory/"plan.json"));result=meta(read(directory/"result.json"));reqs={r["id"]:r for r in plan["requests"]}
    require(result["plan_sha256"]==sha((directory/"plan.json").read_bytes()),"result_plan_identity")
    byte_sum=0
    for a in result["attempts"]:
        req=reqs[a["request_id"]];raw=read(directory/a["body_file"],a["sha256"],"confirmation_raw" if confirmation else "decimal_hourly_raw")
        require(len(raw)==a["body_bytes"] and a["http_status"]==200 and a["curl_exit"]==0,"rest_raw_receipt")
        require(a["request_headers"]["X-Gate-Size-Decimal"]=="1","decimal_header_recorded")
        byte_sum+=len(raw);rows=js(raw);require(type(rows) is list and bool(rows),"nonempty_rest_rows")
        stamps=[];frac=0;max_scale=0
        for i,r in enumerate(rows,1):
            require(type(r) is dict and set(r)=={"t","o","h","l","c","v","sum"},"rest_closed_observed_fields")
            require(type(r["t"]) is int,"rest_integer_timestamp")
            t=r["t"];stamps.append(t)
            row=dict(zip(FIELDS,(r["o"],r["h"],r["l"],r["c"],r["v"])));v=values(row)
            dec(r["sum"]);frac+=v["volume"].denominator!=1;max_scale=max(max_scale,len(r["v"].partition(".")[2]))
            item=dict(values=v,strings=row,source_row=i,raw_sha256=a["sha256"],path=str(directory/a["body_file"]),raw_record=r)
            if confirmation:
                bulk=rest[a["instrument"]][t]
                require(r==bulk["raw_record"],"confirmation_exact_all_raw_fields")
                confirmations.append(dict(id=a["request_id"],instrument=a["instrument"],timestamp=t,utc=utc(t),confirmation_ref=[item["path"],i,item["raw_sha256"]],bulk_ref=[bulk["path"],bulk["source_row"],bulk["raw_sha256"]],raw_record=r,all_raw_fields_equal=True))
            else:
                require(t not in rest[a["instrument"]],"rest_unique_hour")
                rest[a["instrument"]][t]=item
        require(stamps==list(range(req["start"],req["end_exclusive"],3600)) and len(rows)==req["expected_hourly_rows"],"rest_exact_requested_grid_order")
        rest_objects.append(dict(kind="confirmation" if confirmation else "bulk",instrument=a["instrument"],request_id=a["request_id"],path=str(directory/a["body_file"]),raw_sha256=a["sha256"],bytes=len(raw),rows=len(rows),source_rows_inclusive=[1,len(rows)],start=stamps[0],end_exclusive=stamps[-1]+3600,fractional_volume_rows=frac,max_volume_fraction_digits=max_scale,request_url=a["url"],request_headers=a["request_headers"],received_at_utc=a["received_at"]))
    require(byte_sum==result["total_bytes"],"rest_total_bytes")
for s in SYMS:require(list(rest[s])==list(range(SWITCH,END,3600)),"rest_full_7296_hour_grid")
differences=[];summaries={}
for s in SYMS:
    counts=Counter();by_month={};deltas=[];first_fraction=None;first_change=None;close=[]
    for t,new in rest[s].items():
        old=archive[s][t];changes={}
        for k in FIELDS:
            if new["values"][k]!=old["values"][k]:
                counts[k]+=1;changes[k]=dict(archive=old["strings"][k],rest=new["strings"][k],rest_minus_archive=text(new["values"][k]-old["values"][k]))
        if new["values"]["volume"].denominator!=1:
            counts["fractional_rest"]+=1;first_fraction=first_fraction or t
        delta=new["values"]["volume"]-old["values"]["volume"]
        if delta:
            deltas.append(delta);first_change=first_change or t
            counts["abs_volume_delta_ge_1"]+=abs(delta)>=1
            counts["volume_delta_negative"]+=delta<0
            counts["archive_differs_from_trunc_rest"]+=int(new["values"]["volume"])!=old["values"]["volume"]
            month=utc(t)[:7];by_month.setdefault(month,Counter())["volume_changes"]+=1
            by_month[month]["abs_delta_ge_1"]+=abs(delta)>=1
        if changes:
            ref=dict(instrument=s,timestamp=t,utc=utc(t),archive_ref=[old["source_id"],old["source_row"],old["raw_sha256"]],rest_ref=[new["path"],new["source_row"],new["raw_sha256"]],v2_ref=[norm_info[(s,3600)]["path"],old["normalized_row"],norm_info[(s,3600)]["sha256"]],fields=changes)
            differences.append(ref)
            if any(k!="volume" for k in changes):close.append(ref)
    summaries[s]=dict(archive_hours=len(archive[s]),archive_objects=sum(r["instrument"]==s for r in archive_objects),archive_fractional_volume_rows=sum(r["fractional_volume_rows"] for r in archive_objects if r["instrument"]==s),prefix_hours=sum(t<SWITCH for t in archive[s]),rest_hours=len(rest[s]),counts=dict(counts),first_fractional_utc=utc(first_fraction) if first_fraction else None,first_volume_change_utc=utc(first_change) if first_change else None,min_volume_delta=text(min(deltas)),max_volume_delta=text(max(deltas)),sum_volume_delta=text(sum(deltas,Fraction())),monthly_differences=by_month,nonvolume_conflicts=close)
# Check v2 derived aggregates and original parent lineage, without creating a new dataset.
derived_checks=[]
for f in v2["files"]:
    if f["kind"]!="candles" or f["interval_seconds"]==3600:continue
    step=f["interval_seconds"];s=f["symbol"];rows=list(csv.DictReader(io.StringIO((N/f["path"]).read_text())))
    lines=[js(l) for l in (N/f["derivation"]["lineage_path"]).read_bytes().splitlines()]
    checked=0
    for index,(r,lin) in enumerate(zip(rows,lines),1):
        t=int(r["timestamp"])
        if t>=END:break
        parents=[archive[s][u] for u in range(t,t+step,3600)]
        expected=dict(open=parents[0]["values"]["open"],high=max(p["values"]["high"] for p in parents),low=min(p["values"]["low"] for p in parents),close=parents[-1]["values"]["close"],volume=sum((p["values"]["volume"] for p in parents),Fraction()))
        require(all(dec(r[k],k!="volume")==expected[k] for k in FIELDS),"v2_derived_exact_from_hourly")
        require(int(r["available_at"])==t+step,"v2_derived_clock")
        require(lin==dict(normalized_row=index,parent_rows=[p["normalized_row"] for p in parents],timestamp=t),"v2_derived_parent_lineage")
        checked+=1
    require(checked==(END-START)//step,"v2_derived_full_count")
    derived_checks.append(dict(instrument=s,interval_seconds=step,checked=checked,exact=True))
# Hash all existing MARK attempt/reuse objects; parse only the quarantined object in full.
mark_dir=C/"mark-archive-intake-through-september-r1";mr=meta(read(mark_dir/"result.json"));mark_objects=[]
for a in mr["attempts"]:
    b=read(mark_dir/a["body_file"],a["raw_sha256"],"mark_attempt_raw")
    require(len(b)==a["raw_bytes"],"mark_attempt_bytes")
    mark_objects.append(dict(path=str(mark_dir/a["body_file"]),sha256=a["raw_sha256"],bytes=len(b)))
for o in mr["objects"]:
    if o["status"]=="ACCEPTED_REUSE":
        b=read(o["path"],o["raw_sha256"],"mark_reuse_raw")
        mark_objects.append(dict(path=o["path"],sha256=o["raw_sha256"],bytes=len(b)))
require(len(mark_objects)==19 and len(mr["attempts"])==17 and sum(o["bytes"] for o in mark_objects)==34975986,"mark_cumulative_budget")
p=mark_dir/"raw/017-202310-BTC_USDT.part";compressed=read(p,"d5e832810809baeb9aa1663e23b5b92a03a49cabe70f6778aedb2f8898dafb53","mark_quarantine_raw")
expanded=gzip.decompress(compressed);require(len(expanded)<256*1024*1024,"mark_expansion_limit")
rows=[];duplicates=[];gaps=[];previous=None
for line_no,line in enumerate(expanded.decode("utf-8").splitlines(),1):
    require(len(line.encode())<=1024,"mark_line_bound")
    r=next(csv.reader([line]));require(len(r)==4,"mark_four_fields")
    require(re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]{1,6})?",r[0]) is not None,"mark_time_text")
    t=Fraction(r[0])*1000000;require(t.denominator==1,"mark_exact_microseconds");t=int(t)
    require(1696118400000000<=t<1698796800000000,"mark_month_range")
    for x in r[1:]:dec(x,True)
    if previous:
        prev_t,prev_r,prev_line=previous
        require(t>=prev_t,"mark_no_descending_time")
        if t==prev_t:
            require(r==prev_r,"mark_same_timestamp_all_raw_strings_equal")
            duplicates.append(dict(canonical_row=prev_line,alias_row=line_no,timestamp_us=t,raw_fields=r))
            continue
        if t-prev_t>60000000:gaps.append(dict(previous_row=prev_line,row=line_no,from_us=prev_t,to_us=t,gap_us=t-prev_t))
    rows.append((t,line_no));previous=t,r,line_no
maxgap=max((b[0]-a[0] for a,b in zip(rows,rows[1:])),default=0)
mark=dict(path=str(p),raw_sha256=sha(compressed),raw_bytes=len(compressed),expanded_bytes=len(expanded),expanded_sha256=sha(expanded),physical_rows=len(expanded.splitlines()),canonical_observations=len(rows),duplicates=duplicates,descending_rows=0,conflicting_equal_timestamps=0,crc_full_read=True,first_us=rows[0][0],last_us=rows[-1][0],start_boundary_gap_us=rows[0][0]-1696118400000000,end_boundary_gap_us=1698796800000000-rows[-1][0],max_gap_us=maxgap,gaps_gt60=gaps,gap_counts={str(s):sum(g["gap_us"]>s*1000000 for g in gaps) for s in (60,120,180)},required_query_coverage="NOT_EVALUATED",existing_raw_objects_hash_verified=mark_objects,cumulative_get_attempts=17,cumulative_bytes=34975986,remaining_fixed_gets=71,max_cumulative_attempts=98,max_cumulative_bytes=2147483648)
require(len(duplicates)==5 and len(rows)==206372 and len(expanded.splitlines())==206377,"mark_exact_observed_duplicate_count")
audit=dict(status="INDEPENDENT_RAW_AND_LINEAGE_REVIEW_ONLY",handoff_sha256=sha(handoff_path.read_bytes()),files=list(REGISTRY.values()),archive_objects=archive_objects,rest_objects=rest_objects,summary=summaries,confirmations=confirmations,difference_row_reference_format="archive:[source_id,physical_1_based_row,raw_sha256]; rest:[path,1_based_JSON_array_row,raw_sha256]; v2:[path,1_based_data_row_excluding_header,file_sha256]",differences=differences,difference_list_sha256=sha(canon(differences)),derived_v2_checks=derived_checks,mark=mark,checks=dict(checks),network_requests=0,data_promoted=False,model_fits=0)
print(json.dumps(dict(independent_audit=audit),ensure_ascii=False,indent=2,allow_nan=False))

```

<!-- QR008_POLICY_SELFTEST -->

```python
from fractions import Fraction as F
import json,re
CASES=[]
def dec(s,positive=False):
    if type(s) is not str or not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]+)?",s) or len(s)>128 or len(s.partition(".")[2])>64:raise ValueError("decimal")
    q=F(s)
    if (q<=0 if positive else q<0):raise ValueError("domain")
    return q
def aggregate(rows,step):
    if len(rows)!=step//3600 or rows[0]["t"]%step or [r["t"] for r in rows]!=list(range(rows[0]["t"],rows[0]["t"]+step,3600)):raise ValueError("grid")
    for r in rows:
        if not dec(r["l"],True)<=min(dec(r["o"],True),dec(r["c"],True))<=max(dec(r["o"],True),dec(r["c"],True))<=dec(r["h"],True):raise ValueError("OHLC")
    return dict(t=rows[0]["t"],o=dec(rows[0]["o"],True),h=max(dec(r["h"],True) for r in rows),l=min(dec(r["l"],True) for r in rows),c=dec(rows[-1]["c"],True),v=sum((dec(r["v"]) for r in rows),F()))
def alias(rows):
    result=[]
    for n,r in enumerate(rows,1):
        if len(r)!=4 or not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]{1,6})?",r[0]):raise ValueError("mark fields/time")
        t=F(r[0])*1000000
        for p in r[1:]:dec(p,True)
        if result and t<result[-1]["t"]:raise ValueError("descending")
        if result and t==result[-1]["t"]:
            if list(r)!=result[-1]["raw"]:raise ValueError("conflict")
            result[-1]["rows"].append(n)
        else:result.append(dict(t=t,raw=list(r),rows=[n]))
    if not result:raise ValueError("empty")
    return result
def eq(a,b):
    if a!=b:raise AssertionError((a,b))
def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid fixture accepted")
def run(name,fn):fn();CASES.append(dict(id=name,status="PASS_ORACLE_SELFTEST"))
run("D01_exact_fraction",lambda:eq(dec("0.1")+dec("0.2"),F("0.3")))
run("D02_more_than_28_digits",lambda:eq(dec("123456789012345678901234567890.1")+dec("0.2"),F("123456789012345678901234567890.3")))
run("D03_true_zero",lambda:eq(dec("0"),F(0)))
for name,bad in (("bool",True),("float",0.1),("null",None),("integer",1),("negative","-0.1"),("NaN","NaN"),("exponent","1e-2"),("empty",""),("whitespace"," 1"),("overprecision","0."+"1"*65)):
    run("D04_reject_"+name,lambda bad=bad:rejected(lambda:dec(bad)))
rows=[dict(t=i*3600,o=str(10+i),h=str(12+i),l=str(9+i),c=str(11+i),v=["0.1","0.2","0.3","0.4"][i]) for i in range(4)]
run("A01_literal_4h",lambda:eq(aggregate(rows,14400),dict(t=0,o=F(10),h=F(15),l=F(9),c=F(14),v=F(1))))
run("A02_missing_parent",lambda:rejected(lambda:aggregate(rows[:-1],14400)))
run("A03_duplicate_parent",lambda:rejected(lambda:aggregate(rows[:3]+[rows[2]],14400)))
run("A04_descending_parent",lambda:rejected(lambda:aggregate(rows[::-1],14400)))
run("A05_off_grid",lambda:rejected(lambda:aggregate([{**r,"t":r["t"]+1} for r in rows],14400)))
day=[dict(t=i*3600,o="1",h="3",l="1",c="2",v="0.1") for i in range(24)]
run("A06_daily_exact_sum_and_nested",lambda:eq((aggregate(day,86400)["v"],sum((aggregate(day[i:i+4],14400)["v"] for i in range(0,24,4)),F())),(F("2.4"),F("2.4"))))
switch=1764547200
run("A07_source_switch_boundary",lambda:eq(["ARCHIVE" if t<switch else "REST" for t in (switch-3600,switch)],["ARCHIVE","REST"]))
end=1790812800
run("A08_last_bar_stored_not_decidable_at_cutoff",lambda:eq((end-3600+3600==end,end<end),(True,False)))
m=["100.000001","1","2","3"]
run("M01_alias_two",lambda:eq(alias([m,m])[0]["rows"],[1,2]))
run("M02_alias_run_three",lambda:eq(alias([m,m,m])[0]["rows"],[1,2,3]))
run("M03_next_time_equal_price_new_point",lambda:eq(len(alias([m,["101.000001","1","2","3"]])),2))
run("M04_changed_field_conflict",lambda:rejected(lambda:alias([m,[m[0],"1","2.1","3"]])))
run("M05_price_lexically_different_conflict",lambda:rejected(lambda:alias([m,[m[0],"1","2.0","3"]])))
run("M06_timestamp_lexically_different_conflict",lambda:rejected(lambda:alias([["100.0","1","2","3"],["100.00","1","2","3"]])))
run("M07_descending_even_repeat",lambda:rejected(lambda:alias([m,["99","1","2","3"],m])))
run("M08_submicrosecond",lambda:rejected(lambda:alias([["100.0000001","1","2","3"]])))
run("M09_missing_column",lambda:rejected(lambda:alias([m[:-1]])))
run("M10_nonfinite_price",lambda:rejected(lambda:alias([[m[0],"1","NaN","3"]])))
run("M11_empty_object",lambda:rejected(lambda:alias([])))
def supported(source,query,delay,age):return source+delay<=query and 0<=query-source<=age
run("M12_clock_and_age_boundaries",lambda:eq([supported(0,q,60000000,120000000) for q in (59999999,60000000,120000000,120000001)],[False,True,True,False]))
print(json.dumps(dict(status="ORACLE_SELFTEST_ONLY",count=len(CASES),cases=CASES,producer_tests_executed=0,network_requests=0,model_fits=0)))

```
