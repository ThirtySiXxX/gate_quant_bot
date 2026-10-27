"""
全图形化 Web 控制台 —— 程序唯一的操作界面。

所有 IO 都在这里完成：填写/测试 API Key、选择模式(模拟盘/实盘)、增删交易标的
（含黄金 XAU_USDT）、调整多资产 Trend+Carry+波动率目标系统的全部参数、
一键启动/停止交易引擎、查看组合层持仓/盈亏/每标的信号/运行日志、
下载历史K线做组合级回测（和实盘引擎完全独立，可以一边跑实盘一边回测）。

用户全程只需要"双击启动脚本"一次，之后所有操作都在浏览器里点击/输入完成。
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict

from flask import Flask, jsonify, render_template_string, request
from flask.json.provider import DefaultJSONProvider
from .json_utils import json_safe

from .backtest_runner import BacktestController
from .config import ConfigStore
from .credentials import CredentialStore
from .engine import EngineController
from .state import StateStore
from .universe import UniverseService, tradable_contract, is_crypto, SYMBOL as CONTRACT_SYMBOL
from .config import SystematicConfig, CostConfig, RiskConfig

logger = logging.getLogger("bot.web")


class StrictJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs["allow_nan"] = False
        return super().dumps(json_safe(obj), **kwargs)



def _friendly_api_error(e) -> str:
    """把 Gate 的原始异常翻译成"发生了什么 + 该怎么办"。

    原样抛给用户的话，真正有用的那一句会淹没在一堆 HTTP header 里。
    这几类错误都有稳定特征，识别出来直接给操作步骤。
    """
    label = (getattr(e, "label", "") or "").upper()
    body = str(getattr(e, "message", "") or getattr(e, "body", "") or e)
    raw = f"{label} {body}"

    m = re.search(r"Request IP not in whitelist:\s*([0-9a-fA-F:.]+)", body)
    if m or "not in whitelist" in body.lower():
        ip = m.group(1) if m else "（见下方原始信息）"
        return (f"IP 白名单拦截。\n"
                f"你当前的公网出口 IP 是 {ip}，不在这个 API Key 的白名单里。\n"
                f"解决：登录 Gate → API 管理 → 编辑该 Key → 把 {ip} 加入 IP 白名单，几分钟后生效。\n"
                f"注意家用宽带 IP 通常会变，变了需要重新添加；挂 VPN 时要填代理的出口 IP。\n"
                f"（原始信息：{raw[:160]}）")
    if label in ("INVALID_KEY", "INVALID_SIGNATURE") or "invalid key" in body.lower() \
            or "signature mismatch" in body.lower():
        return ("API Key 或 Secret 不正确。\n"
                "解决：确认复制时没有多余空格/换行；Secret 只在创建时显示一次，"
                "记不清就重新创建一个 Key。\n"
                f"（原始信息：{raw[:160]}）")
    if "expired" in body.lower() or "timestamp" in body.lower():
        return ("请求时间戳超出允许范围，通常是本机系统时间不准。\n"
                "解决：打开系统的「自动设置时间」，或手动校时后重试。\n"
                f"（原始信息：{raw[:160]}）")
    if label == "FORBIDDEN" or "permission" in body.lower():
        return ("权限不足。这个 Key 可能没有勾选「合约交易」或「读取」权限。\n"
                "解决：Gate → API 管理 → 编辑该 Key → 勾选 合约交易(Futures Trade) 和 读取(Read)。\n"
                f"（原始信息：{raw[:160]}）")
    return str(e)[:400]


# ============================================================ 共享 UI 片段
# 四个页面以前各自复制了一份 CSS 和导航，改一处要改四处、还容易漏。
# 这里抽成公共常量，样式统一、维护也只需改一个地方。
BASE_CSS = """
  :root { --bg:#0d1117; --panel:#161b22; --panel2:#1c2333; --border:#30363d;
          --text:#c9d1d9; --muted:#8b949e; --accent:#58a6ff; --accent2:#a371f7;
          --pos:#3fb950; --neg:#f85149; --warn:#e3b341; }
  * { box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); margin:0;
         font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;
         font-size:14px; line-height:1.6; }
  header { display:flex; align-items:center; justify-content:space-between; gap:16px;
           padding:12px 24px; border-bottom:1px solid var(--border);
           position:sticky; top:0; background:rgba(13,17,23,.92);
           backdrop-filter:blur(8px); z-index:50; }
  .brand { display:flex; align-items:center; gap:10px; font-size:16px; font-weight:600;
           color:var(--accent); white-space:nowrap; }
  .brand .ver { font-size:11px; color:var(--muted); font-weight:400; }
  nav { display:flex; gap:4px; flex-wrap:wrap; }
  nav a, nav button { background:transparent; border:1px solid transparent; color:var(--muted);
        padding:7px 14px; border-radius:7px; cursor:pointer; font-size:13.5px;
        text-decoration:none; transition:all .15s; white-space:nowrap; }
  nav a:hover, nav button:hover { color:var(--text); background:var(--panel); }
  nav a.active, nav button.active { background:var(--accent); color:#04121f;
        border-color:var(--accent); font-weight:600; }
  main { padding:20px 24px 60px; max-width:1300px; margin:0 auto; }
  section { background:var(--panel); border:1px solid var(--border); border-radius:10px;
            padding:16px 18px; margin-bottom:16px; }
  section h3 { margin:0 0 12px; font-size:15px; color:var(--accent); font-weight:600; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
          gap:10px; margin-bottom:16px; }
  .card { background:var(--panel2); border:1px solid var(--border); border-radius:9px; padding:11px 14px; }
  .card .label { font-size:11.5px; color:var(--muted); }
  .card .value { font-size:19px; font-weight:600; margin-top:3px; }
  .pos { color:var(--pos); } .neg { color:var(--neg); } .warn { color:var(--warn); }
  .warn-box { background:#3a2a0d; border:1px solid #6b4f14; color:#f0c674; border-radius:8px;
              padding:10px 12px; margin-bottom:10px; font-size:13px; line-height:1.6; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th,td { border-bottom:1px solid #21262d; padding:7px 8px; text-align:left; }
  th { color:var(--muted); font-weight:500; font-size:12px; }
  tbody tr:hover { background:rgba(255,255,255,.02); }
  input,select { background:#0d1117; color:var(--text); border:1px solid var(--border);
        border-radius:7px; padding:8px 11px; font-size:13.5px; font-family:inherit; }
  input:focus,select:focus { outline:none; border-color:var(--accent); }
  button.btn { background:#0d1117; color:var(--text); border:1px solid var(--border);
        border-radius:7px; padding:8px 15px; font-size:13.5px; cursor:pointer;
        font-family:inherit; transition:all .15s; }
  button.btn:hover { border-color:var(--accent); background:var(--panel2); }
  button.primary { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:600; }
  button.primary:hover { background:#79b8ff; }
  button.success { background:#12351f; color:var(--pos); border-color:#1a5c30; font-weight:600; }
  button.danger { background:#3a0d0d; color:var(--neg); border-color:#5c1a1a; font-weight:600; }
  button.btn:disabled { opacity:.45; cursor:not-allowed; }
  .row { display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap; margin-bottom:12px; }
  .field { display:flex; flex-direction:column; gap:4px; }
  .field label { font-size:11.5px; color:var(--muted); }
  .hint { font-size:12px; color:var(--muted); line-height:1.65; }
  .badge { padding:2px 9px; border-radius:10px; font-size:11.5px; font-weight:600; }
  .badge.paper { background:#4b3b00; color:var(--warn); }
  .badge.live { background:#4a0d0d; color:var(--neg); }
  .badge.on { background:#0d3b1f; color:var(--pos); }
  .badge.off { background:#30363d; color:var(--muted); }
  .badge.upd { background:var(--accent2); color:#0d1117; }
  .warnbox { background:#3a2400; border:1px solid var(--warn); color:var(--warn);
             padding:11px 14px; border-radius:9px; margin-bottom:14px; font-size:13px; }
  .okbox { background:#0d3b1f; border:1px solid var(--pos); color:var(--pos);
           padding:11px 14px; border-radius:9px; margin-bottom:14px; font-size:13px; }
  .errbox { background:#3a0d0d; border:1px solid var(--neg); color:#ff9d97;
            padding:11px 14px; border-radius:9px; margin-bottom:14px; font-size:13px; }
"""


def nav_html(active: str) -> str:
    """生成统一的顶部导航。active 用于高亮当前页。"""
    items = [("/", "dashboard", "仪表盘"), ("/backtest", "backtest", "回测"),
             ("/charts", "charts", "K线图"), ("/manual", "manual", "手动开单"),
             ("/update", "update", "检查更新")]
    out = []
    for href, key, label in items:
        if key == "backtest":
            continue          # 回测是仪表盘内的标签页，不单独占导航位
        cls = " class='active'" if key == active else ""
        out.append(f"<a href='{href}'{cls}>{label}</a>")
    return "<nav>" + "".join(out) + "</nav>"


def header_html(active: str, extra_badges: str = "") -> str:
    return f"""<header>
  <div class="brand">⚙️ Gate.io 量化控制台
    <span class="ver" id="app-version"></span>
    <span class="badge upd" id="upd-badge" style="display:none;cursor:pointer"
          onclick="location.href='/update'">有新版本</span>
    {extra_badges}
  </div>
  {nav_html(active)}
</header>
<script>
fetch('/api/version').then(r=>r.json()).then(v=>{{
  document.getElementById('app-version').textContent = 'v' + v.current;
  if(v.update_available) document.getElementById('upd-badge').style.display='inline-block';
}}).catch(()=>{{}});
</script>"""


WORKSPACE_NAV = """
<aside class="workspace-sidebar">
  <a class="workspace-brand" href="/?view=backtest" aria-label="Quant Desk 首页"><span class="brand-mark">q<span>·</span></span><span>QUANT DESK<small>GATE / RESEARCH</small></span></a>
  <p class="nav-label">研究工作台</p>
  <nav class="workspace-nav" aria-label="主导航">
    <a id="nav-universe" data-view="universe" href="/?view=universe"><span class="nav-symbol" aria-hidden="true">◎</span>五币推荐<span class="nav-note">手动</span></a>
    <a id="nav-backtest" data-view="backtest" href="/?view=backtest"><span class="nav-symbol" aria-hidden="true">▥</span>回测实验室</a>
    <a id="nav-charts" data-view="charts" href="/charts"><span class="nav-symbol" aria-hidden="true">⌁</span>K 线分析</a>
    <a id="nav-dashboard" data-view="dashboard" href="/?view=dashboard"><span class="nav-symbol" aria-hidden="true">◫</span>持仓概览</a>
  </nav>
  <div class="sidebar-bottom"><a id="nav-settings" data-view="settings" href="/?view=settings">设置与维护 <span aria-hidden="true">↗</span></a><div class="sidebar-foot">Trend + Carry<small>先验证，再决策。</small></div></div>
</aside>
"""


PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Gate.io 量化策略控制台</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/workspace.css">
</head>
<body class="workspace" data-page="main">
__WORKSPACE_NAV__
<div class="workspace-content">
<header class="workspace-topbar"><span class="workspace-crumb">研究 / <strong id="workspace-current">回测实验室</strong></span><div class="status-cluster"><span id="mode-badge" class="badge"></span><span id="engine-badge" class="badge"></span><span id="invert-badge" class="badge live" style="display:none;">反向执行</span></div></header>
<main>

<div id="tab-universe" class="tabpage">
  <div class="page-heading"><div><span class="eyebrow">MARKET DISCOVERY</span><h1>五币推荐</h1><p>从全市场寻找更适合当前趋势的候选，最多五个。</p></div><button class="btn primary" id="universe-refresh">筛选五个候选 <span aria-hidden="true">↗</span></button></div>
  <section id="universe-panel" class="discovery-panel">
    <div class="section-heading"><h2>本次候选</h2><span class="subtle-tag">手动触发 · 不自动开仓</span></div>
    <p id="universe-status" class="hint" role="status">点击“筛选五个候选”后开始扫描公共行情。</p>
    <div id="universe-empty" class="discovery-empty"><div class="candidate-placeholders" aria-hidden="true"><span>01</span><span>02</span><span>03</span><span>04</span><span>05</span></div><h3 id="universe-empty-title">让机会先通过筛选</h3><p id="universe-empty-note">点击右上方按钮，检查趋势、路径质量与执行成本。<br>打开或刷新页面都不会自动扫描。</p></div>
    <ol id="universe-cards" class="candidate-grid" aria-label="本次推荐候选"></ol>
    <div class="discovery-footer"><span class="hint">评分用于本次相对排序，不代表胜率；无合格信号时允许空缺。</span><button class="btn" id="universe-apply" disabled hidden>把候选加入交易池</button></div>
  </section>
  <div class="method-strip"><div><span>01</span><strong>全市场初筛</strong><p>检查交易状态、成交额与点差</p></div><div><span>02</span><strong>因子排序</strong><p>趋势强度、路径质量、执行成本</p></div><div><span>03</span><strong>相关性约束</strong><p>避免候选过度集中于同一走势</p></div></div>
  <details class="panel-details"><summary>筛选明细与方法说明</summary><div class="table-scroll"><table><thead><tr><th>币种</th><th>趋势方向</th><th>相对评分</th><th>1H / 4H 趋势</th><th>路径效率</th><th>往返成本</th><th>24H成交额</th></tr></thead><tbody id="universe-rows"></tbody></table></div><p class="hint" id="universe-rejections"></p><p class="hint">成本含双边手续费、点差、滑点及按当前费率估计的1天不利资金费，不含下单量对应的实际冲击。候选加入交易池后仍须通过策略的全仓与执行检查；不会移除已有手动标的。不要用今天的候选倒推历史选币表现。</p></details>
</div>

<div id="tab-dashboard" class="tabpage">
  <div class="page-heading"><div><span class="eyebrow">PORTFOLIO MONITOR</span><h1>持仓概览</h1><p>关注账户、持仓与策略运行状态。</p></div></div>
  <div class="row">
    <button class="btn success" onclick="engineAction('start')">▶ 启动引擎</button>
    <button class="btn danger" onclick="engineAction('stop')">■ 停止引擎</button>
    <span id="engine-msg" class="hint"></span>
  </div>
  <div class="grid" id="summary-grid"></div>

  <section><h3>组合层概览</h3><div class="grid" id="portfolio-grid"></div></section>

  <section><h3>当前持仓</h3>
    <div id="ownership-notice" style="display:none;"></div>
    <div class="table-scroll"><table id="positions"><thead><tr>
    <th>币种</th><th>方向</th><th>张数</th><th>开仓价</th><th>现价</th>
    <th>浮动盈亏</th><th>持仓时长</th><th>归属</th><th>操作</th></tr></thead><tbody></tbody></table></div></section>

  <section><h3>标的信号（趋势 / Carry / 合成预测）</h3><div class="table-scroll"><table id="signals"><thead><tr>
    <th>币种</th><th>方向</th><th>信号强度</th><th>合成预测(F)</th><th>明细</th></tr></thead><tbody></tbody></table></div></section>

  <section><h3>最近成交</h3><div class="table-scroll"><table id="trades"><thead><tr>
    <th>币种</th><th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>手续费</th><th>资金费</th><th>持仓时长</th><th>离场原因</th></tr></thead><tbody></tbody></table></div></section>

  <section><h3>运行日志</h3><div id="logs"></div></section>
</div>

<div id="tab-backtest" class="tabpage">
  <div class="page-heading"><div><span class="eyebrow">STRATEGY LAB</span><h1>回测实验室</h1><p>配置一次实验，查看复利表现，再到图上复盘成交。</p></div><a class="text-link" href="/charts">打开 K 线分析 ↗</a></div>
  <div class="backtest-workspace">
    <section class="bt-setup">
      <div class="section-heading"><h2>新建回测</h2><span class="subtle-tag">单币回测</span></div>
      <div class="field symbol-search" id="bt-symbol-picker"><label for="bt-symbol-search">搜索回测币种</label><input id="bt-symbol-search" type="search" placeholder="例如 BTC、SOL 或 DOGE_USDT" autocomplete="off" spellcheck="false" aria-describedby="bt-symbol-hint" aria-controls="bt-symbol-matches"><div id="bt-symbol-matches" class="symbol-search-results" role="group" aria-label="匹配的回测合约" hidden></div><p class="hint" id="bt-symbol-hint" role="status">正在加载全市场合约目录；每次回测一个币种。</p></div>
      <div class="form-pair"><div class="field"><label for="bt-days">回测天数</label><input id="bt-days" type="number" min="1" value="90"></div><div class="field"><label for="bt-capital">初始资金 · USDT</label><input id="bt-capital" type="number" min="1" placeholder="策略默认"></div></div>
      <div class="presetbar" id="bt-preset-bar"><button class="btn" onclick="setBtDays(30)">30 天</button><button class="btn" onclick="setBtDays(90)">90 天</button><button class="btn" onclick="setBtDays(180)">180 天</button><button class="btn" onclick="setBtDays(365)">1 年</button></div>
      <details class="inline-details"><summary>更多选项</summary><label class="check-line"><input type="checkbox" id="bt-walkforward"> 同时做跨时间窗口验证</label><div class="field"><label for="bt-wf-folds">验证折数</label><input id="bt-wf-folds" type="number" min="2" max="10" value="5"></div><p class="hint">仅查询历史行情，不影响运行中的引擎；首次下载需要更长时间，使用设置中保存的 API Key。</p></details>
      <button class="btn primary full-width" id="bt-run" onclick="startBacktest()">开始回测 <span aria-hidden="true">→</span></button><p id="bt-start-msg" class="hint" role="status"></p>
    </section>
    <section class="bt-history"><div class="section-heading"><h2>实验记录</h2><span class="hint" id="bt-job-count"></span></div><div class="joblist" id="bt-joblist"></div></section>
    <div class="bt-result-area">
      <section id="bt-empty" class="result-empty"><span class="empty-chart" aria-hidden="true">▁ ▂ ▂ ▄ ▃ ▆</span><h2>从一次回测开始</h2><p>选择左侧历史记录，或运行一个新实验。<br>结果和权益曲线会显示在这里。</p></section>
      <section id="bt-detail-section" style="display:none;">
        <div class="section-heading"><div><span class="eyebrow">EXPERIMENT RESULT</span><h2>回测结果</h2></div><a id="bt-chart-link" class="btn" href="/charts" hidden>查看成交 K 线 ↗</a></div>
        <p id="bt-result-caption" class="hint"></p>
        <div class="grid result-metrics" id="bt-summary-grid"></div>
        <div class="equity-heading"><h3>账户权益</h3><span>USDT · 含成本 · 复利</span></div><canvas id="btEquityCanvas" aria-label="组合账户权益曲线"></canvas>
        <details class="result-notes"><summary>数据与模型限制 <span id="bt-warning-count"></span></summary><div id="bt-warnings"></div></details>
        <p class="hint">本回测尚未覆盖完整全仓盘中强平，收益不能证明高杠杆账户的真实存活率。</p>
        <details class="panel-details"><summary>月度复利与详细统计</summary><div id="bt-compound"></div><div class="grid" id="bt-secondary-grid"></div></details>
        <details class="panel-details"><summary>交易成本与分标的贡献</summary><div id="bt-costs"></div><div class="table-scroll"><table id="bt-per-symbol"><thead><tr><th>标的</th><th>交易数</th><th>净盈亏</th><th>手续费</th><th>资金费</th><th>趋势</th><th>Carry</th><th>风险乘数</th></tr></thead><tbody></tbody></table></div></details>
        <details class="panel-details"><summary>趋势捕获与跨时间验证</summary><div id="bt-diagnosis"></div><div id="bt-walkforward-box"></div></details>
        <details class="panel-details"><summary>逐笔成交记录</summary><div class="table-scroll"><table id="bt-trades"><thead><tr><th>标的</th><th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>手续费</th><th>资金费</th><th>持仓时长</th><th>原因</th></tr></thead><tbody></tbody></table></div></details>
      </section>
    </div>
  </div>
</div>

<div id="tab-settings" class="tabpage">
<div class="page-heading"><div><span class="eyebrow">WORKSPACE SETTINGS</span><h1>设置与维护</h1><p>账户连接、交易池与运行配置。</p></div></div>

  <section>
    <h3>账户连接</h3>
    <div class="warnbox">申请API Key时请只勾选"合约交易+读取"权限，不要开启"提现"权限，并绑定IP白名单。模拟盘也建议填真实Key（只读行情，不会下单）。</div>
    <div class="row">
      <div class="field"><label>API Key</label><input id="api-key" type="text" placeholder="你的API Key"></div>
      <div class="field"><label>API Secret</label><input id="api-secret" type="password" placeholder="你的API Secret"></div>
      <div class="field"><label>API Host（一般无需修改）</label><input id="api-host" type="text" value="https://api.gateio.ws/api/v4"></div>
    </div>
    <div class="row">
      <button class="btn primary" onclick="saveCredentials()">保存 API Key</button>
      <button class="btn" onclick="testCredentials()">测试连接</button>
      <span id="cred-status" class="hint"></span>
    </div>
  </section>

  <section>
    <h3>运行模式</h3>
    <div class="row presetbar" id="mode-bar">
      <button class="btn" data-mode="paper" onclick="setMode('paper')">模拟盘 PAPER（推荐先用这个）</button>
      <button class="btn" data-mode="live" onclick="setMode('live')">实盘 LIVE（真实资金，请谨慎）</button>
    </div>
    <div class="hint">切换到实盘前请务必确认已用模拟盘验证过策略表现，且账户内没有其它未平仓位（双向持仓模式切换要求无持仓）。</div>
  </section>

  <section>
    <h3>手动交易池</h3>
    <div class="row">
      <input id="symbol-input" list="market-symbols" placeholder="搜索合约，如 BTC_USDT" size="28">
      <datalist id="market-symbols"></datalist>
      <button class="btn primary" onclick="addSymbol()">添加到交易池</button>
    </div>
    <div id="symbols-chips"></div>
    <div class="hint">可添加交易所当前开放的合约。自动筛选只评估加密货币；手动选择的贵金属等合约仍可保留。</div>
  </section>
  <section>
    <h3>资金与仓位规则</h3>
    <div class="hint" id="sizing-policy">每次新开仓按当前权益的 5% 作为初始保证金，全仓模式。BTC/ETH 请求 200x；SOL 请求 200x，最高 100x 时用 10% 保证金；其余加密货币请求 20x，最高 10x 时用 10% 保证金。等价换算保持名义仓位，手续费另计；同一持仓不重复追加额度。全仓亏损可超过初始保证金。</div>
    <div class="subgrid" id="sys-core-fields" style="margin-top:10px;"></div>
    <div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveSysCore()">保存资金与风险边界</button></div>
  </section>
  <details>
    <summary>研究参数与运行维护</summary>
    <div class="row"><a class="btn" href="/manual">手动开单测试 ↗</a><a class="btn" href="/update">版本与更新 ↗</a><span id="app-version" class="hint"></span><a id="upd-badge" class="text-link" href="/update" style="display:none;">有新版本</a></div>
    <p class="hint">预测权重、周期与过滤阈值属于版本化模型参数。改动前先提出假设并做独立检验，不按历史收益反复调参。</p>
    <section><h3>模型参数 · 只读</h3><pre id="model-settings" style="white-space:pre-wrap;"></pre></section>
    <section>
      <h3>实际交易成本</h3><div class="subgrid" id="costs-fields"></div>
      <button class="btn" onclick="saveCosts()">保存实际成本</button>
    </section>
  </details>

</div>

</main>
</div>
<div id="toast" class="toast" style="display:none;"></div>

<script src="/static/universe.js"></script>
<script src="/static/backtest_symbol_search.js"></script>
<script>
let ACTIVE_TAB = 'backtest';
let CUR_MODE = 'paper';
let CUR_CONFIG = {};
let BT_VIEW_JOB_ID = null;

const SYS_CORE_LABELS = {
  initial_capital_usdt: "模拟盘/回测初始资金(USDT)",
};
const COST_LABELS = {
  taker_fee_rate: "吃单费率(填你账户真实值，0.0005=0.05%)",
  maker_fee_rate: "挂单费率(0.0002=0.02%)",
  use_account_fee_rate: "优先读取账户/VIP实际吃单费率",
  use_contract_fee_rate: "改用交易所公开基础费率(通常偏高，一般填0)",
  slippage_bps: "模拟滑点(bps)",
};
const COST_TYPES = { use_account_fee_rate: 'bool', use_contract_fee_rate: 'bool' };

function showTab(name){
  if(!['dashboard','universe','backtest','settings'].includes(name))name='backtest';
  ACTIVE_TAB = name;
  const titles={dashboard:'持仓概览',universe:'五币推荐',backtest:'回测实验室',settings:'设置与维护'};
  ['dashboard','universe','backtest','settings'].forEach(n => {
    document.getElementById('tab-'+n).classList.toggle('active', n===name);
    document.getElementById('nav-'+n).classList.toggle('active', n===name);
    if(n===name)document.getElementById('nav-'+n).setAttribute('aria-current','page');
    else document.getElementById('nav-'+n).removeAttribute('aria-current');
  });
  document.getElementById('workspace-current').textContent=titles[name];
  const url=new URL(window.location.href);url.searchParams.set('view',name);
  history.replaceState(null,'',url);
  if(name==='backtest' && BT_EQUITY_POINTS.length)requestAnimationFrame(()=>drawEquityCurve(BT_EQUITY_POINTS));
}

function toast(msg, ok){
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'toast ' + (ok ? 'ok':'err');
  el.style.display = 'block';
  setTimeout(()=>{ el.style.display='none'; }, 4500);
}

let STATE_REFRESH_TOKEN=0;
const ADOPT_PENDING=new Set();
async function adoptPos(symbol, side, button){
  const key=symbol+'|'+side;
  if(ADOPT_PENDING.has(key))return;
  const d = side==='long'?'多':'空';
  if(!confirm(`确认让策略接管 ${symbol} 的${d}仓？\n\n接管后这笔仓位会按策略目标被调整、减仓甚至反向平掉，\n不再由你手动控制。`)) return;
  ADOPT_PENDING.add(key);++STATE_REFRESH_TOKEN;
  if(button){button.disabled=true;button.textContent='正在登记…';}
  try{
    const r=await api('/api/positions/adopt',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,side})});
    if(r.ok)toast(r.message,true);
  }catch(error){toast('归属登记失败：'+error.message,false);}
  finally{
    ADOPT_PENDING.delete(key);
    if(button){button.disabled=false;button.textContent='纳入策略管理';}
    try{await refresh();}catch(error){toast('持仓刷新失败，将自动重试：'+error.message,false);}
  }
}

async function confirmClosePos(symbol, side){
  const d = side==='long'?'多':'空';
  if(!confirm(`确认市价平掉 ${symbol} 的${d}仓？\n\n该标的已不在标的池中，平掉后不会再自动开回来。`)) return;
  const r = await (await fetch('/api/positions/confirm-close',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,side})})).json();
  toast(r.message, r.ok);
  refresh();
}

function buildFields(containerId, obj, labels, types){
  types = types || {};
  const el = document.getElementById(containerId);
  el.innerHTML = Object.keys(labels).map(k => {
    const v = obj[k];
    const type = types[k] || 'number';
    if(type === 'bool'){
      const checked = v ? 'checked' : '';
      return `<div class="field"><label>${labels[k]}</label>
        <label style="display:flex;align-items:center;gap:8px;font-size:14px;">
          <input data-key="${k}" data-type="bool" type="checkbox" ${checked}> 启用
        </label></div>`;
    }
    const inputType = type === 'number' ? 'number' : 'text';
    const step = type === 'number' ? ' step="any"' : '';
    return `<div class="field"><label>${labels[k]}</label><input data-key="${k}" data-type="${type}" type="${inputType}"${step} value="${v!==undefined?v:''}"></div>`;
  }).join('');
}
function readFields(containerId){
  const el = document.getElementById(containerId);
  const out = {};
  el.querySelectorAll('input[data-key]').forEach(inp => {
    if(inp.dataset.type === 'number') out[inp.dataset.key] = parseFloat(inp.value);
    else if(inp.dataset.type === 'bool') out[inp.dataset.key] = inp.checked;
    else out[inp.dataset.key] = inp.value;
  });
  return out;
}

async function api(path, opts){
  const res = await fetch(path, opts);
  const data = await res.json().catch(()=>({}));
  if(!res.ok || data.ok === false){ toast(data.message || '操作失败', false); }
  return data;
}

async function saveCredentials(){
  const r = await api('/api/credentials', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({api_key: document.getElementById('api-key').value, api_secret: document.getElementById('api-secret').value, api_host: document.getElementById('api-host').value})});
  if(r.ok){ toast('API Key 已保存', true); document.getElementById('cred-status').textContent = 'Key: ' + r.masked.api_key; }
}
async function testCredentials(){
  document.getElementById('cred-status').textContent = '测试中...';
  const r = await api('/api/credentials/test', {method:'POST'});
  document.getElementById('cred-status').textContent = r.message || '';
  if(r.ok) toast('连接测试成功', true);
}

async function setMode(mode){
  if(mode === 'live'){
    if(!confirm('切换到实盘模式将使用真实资金下单，请确认你已经充分测试过策略。是否继续？')) return;
  }
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mode})});
  if(r.ok !== false){ toast('运行模式已切换为 ' + (mode==='live'?'实盘':'模拟盘') + '，如引擎正在运行请重启使其生效', true); CUR_MODE = mode; refreshBootstrap(); }
}

async function saveSysCore(){
  const patch = { systematic: readFields('sys-core-fields') };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false) toast('策略核心参数已保存', true);
}
function updateInvertBadge(on){
  const el = document.getElementById('invert-badge');
  if(!el) return;
  el.style.display = on ? 'inline-block' : 'none';
}
async function saveCosts(){
  const patch = { costs: readFields('costs-fields') };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false) toast('成本参数已保存', true);
}

async function addSymbol(){
  const v = document.getElementById('symbol-input').value.trim().toUpperCase();
  if(!v) return;
  const result = await api('/api/symbols', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol:v})});
  if(!result.ok){ toast(result.message || '添加失败', false); return; }
  document.getElementById('symbol-input').value = '';
  refreshBootstrap();
}
async function removeSymbol(sym){
  await api('/api/symbols', {method:'DELETE', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol:sym})});
  refreshBootstrap();
}

async function engineAction(action){
  const r = await api('/api/engine/' + action, {method:'POST'});
  document.getElementById('engine-msg').textContent = r.message || '';
  if(r.ok) toast(r.message, true);
  refresh();
}

function fmtSecs(s){ s=Math.floor(s||0); const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=s%60;
  if(h) return h+'h'+m+'m'; if(m) return m+'m'+sec+'s'; return sec+'s'; }
function cls(v){ return v>=0 ? 'pos':'neg'; }
function fmtTs(t){ if(!t) return '-'; const d = new Date(t*1000); return d.toLocaleString(); }
function fmtNum(v, digits){ return (typeof v === 'number' && isFinite(v)) ? v.toFixed(digits==null?2:digits) : '-'; }

// ---------------------------------------------------------------- 回测页
function setBtDays(n){ document.getElementById('bt-days').value = n; }

function rememberBacktest(jobId){
  BT_VIEW_JOB_ID=jobId;
  const url=new URL(window.location.href);url.searchParams.set('job',jobId);
  history.replaceState(null,'',url);
}

function normalizeBacktestSymbol(value){
  let symbol=value.trim().toUpperCase().replace(/[-/]/g,'_');
  if(!symbol)return '';
  if(!symbol.endsWith('_USDT'))symbol=symbol.endsWith('USDT')?symbol.slice(0,-4)+'_USDT':symbol+'_USDT';
  return /^[A-Z0-9][A-Z0-9_]{0,59}_USDT$/.test(symbol)?symbol:'';
}

async function startBacktest(){
  const button=document.getElementById('bt-run');
  if(button.disabled)return;
  const input=document.getElementById('bt-symbol-search');
  const symbol=normalizeBacktestSymbol(input.value);
  const days = parseFloat(document.getElementById('bt-days').value);
  const capitalRaw = document.getElementById('bt-capital').value;
  if(!symbol){ toast('请输入一个回测币种，例如 BTC 或 SOL_USDT；每次只能回测一个币种', false); input.focus(); return; }
  input.value=symbol;
  const body = {symbols:[symbol], days_back: days};
  if(capitalRaw) body.initial_capital = parseFloat(capitalRaw);
  if(document.getElementById('bt-walkforward').checked){
    body.walkforward = true;
    body.wf_folds = parseInt(document.getElementById('bt-wf-folds').value) || 5;
  }
  button.disabled=true;button.textContent='正在提交…';
  try {
    const r = await api('/api/backtest/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    if(r.ok){
      toast('回测已提交，结果将在右侧自动更新', true);
      document.getElementById('bt-start-msg').textContent = '实验 ' + r.job_id;
      rememberBacktest(r.job_id);
      await refreshBacktestList();
    }
  }catch(error){toast('回测提交失败：'+error.message,false);}
  finally{button.disabled=false;button.textContent='开始回测 →';}
}

function jobStatusLabel(s){
  return {pending:'排队中', fetching:'下载数据中', running:'回测运行中', done:'已完成', error:'失败'}[s] || s;
}

let BT_LIST_RENDER_KEY='';
async function refreshBacktestList(){
  const el = document.getElementById('bt-joblist');
  let list;
  try {
    const response = await fetch('/api/backtest/list');
    if(!response.ok) throw new Error('HTTP ' + response.status);
    list = await response.json();
  } catch(error) {
    BT_LIST_RENDER_KEY='';
    el.textContent = '回测列表加载失败：' + error.message + '；稍后自动重试。';
    return;
  }
  document.getElementById('bt-job-count').textContent=(list.jobs||[]).length+' 次实验';
  if(!BT_VIEW_JOB_ID)BT_VIEW_JOB_ID=(list.jobs||[]).find(j=>j.status==='done')?.id||null;
  const renderKey=JSON.stringify([BT_VIEW_JOB_ID,list.jobs]);
  if(renderKey!==BT_LIST_RENDER_KEY){
  BT_LIST_RENDER_KEY=renderKey;
  if(!list.jobs || list.jobs.length === 0){
    el.innerHTML = '<div class="hint">还没有实验记录。运行一次回测后，结果会保存在这里。</div>';
  } else {
    el.innerHTML = list.jobs.map(j => {
      const active = ['pending','fetching','running'].includes(j.status);
      const symTxt = (j.symbols||[]).join(', ');
      const value=j.summary?.return_pct;
      const sumTxt=j.summary?`累计 ${fmtNum(value)}% · ${j.summary.position_summary?.position_count??j.summary.trade_count} 个持仓`:(j.error||j.message||'等待执行');
      return `<button type="button" class="jobrow ${j.id===BT_VIEW_JOB_ID?'selected':''}" aria-pressed="${j.id===BT_VIEW_JOB_ID}" onclick="viewBacktest('${j.id}')">
        <span class="job-top"><span class="sym" title="${symTxt}">${symTxt}</span><span class="badge ${j.status}">${jobStatusLabel(j.status)}</span></span>
        <span class="meta">${sumTxt}</span>
        ${active?`<div class="progressbar"><div style="width:${j.progress_pct||0}%"></div></div>`:''}
        <span class="job-bottom"><span>${new Date(j.created_at*1000).toLocaleDateString()}</span><span>${j.days_back} 天</span></span>
      </button>`;
    }).join('');
  }
  }
  if(BT_VIEW_JOB_ID){
    const cur = (list.jobs||[]).find(j => j.id === BT_VIEW_JOB_ID);
    if(cur && (['pending','fetching','running'].includes(cur.status) || BT_DETAIL_VERSION !== [cur.id,cur.status,cur.finished_at].join('|'))){
      await loadBacktestDetail(BT_VIEW_JOB_ID);
    }
  }
}

function viewBacktest(jobId){
  rememberBacktest(jobId);
  loadBacktestDetail(jobId);
  refreshBacktestList();
}

let BT_DETAIL_TOKEN=0, BT_DETAIL_VERSION='';
async function loadBacktestDetail(jobId){
  const token=++BT_DETAIL_TOKEN;
  let job;
  try {
    const response=await fetch('/api/backtest/job/' + encodeURIComponent(jobId));
    if(!response.ok) throw new Error('HTTP ' + response.status);
    job=await response.json();
  } catch(error) {
    if(token===BT_DETAIL_TOKEN){
      document.getElementById('bt-detail-section').style.display='block';
      document.getElementById('bt-empty').hidden=true;
      document.getElementById('bt-chart-link').hidden=true;
      document.getElementById('bt-result-caption').textContent='实验 '+jobId+' · 详情暂不可用';
      ['bt-summary-grid','bt-secondary-grid','bt-compound','bt-costs','bt-diagnosis','bt-walkforward-box'].forEach(id=>document.getElementById(id).replaceChildren());
      document.querySelector('#bt-trades tbody').replaceChildren();
      document.querySelector('#bt-per-symbol tbody').replaceChildren();
      document.querySelector('.result-notes').open=true;
      drawEquityCurve([]);
      document.getElementById('bt-warnings').textContent='回测详情加载失败：'+error.message;
    }
    return;
  }
  if(token!==BT_DETAIL_TOKEN)return;
  BT_DETAIL_VERSION=[job.id,job.status,job.finished_at].join('|');
  const sec = document.getElementById('bt-detail-section');
  document.getElementById('bt-empty').hidden=true;
  if(job.status !== 'done'){
    sec.style.display = 'block';
    document.getElementById('bt-chart-link').hidden=true;
    document.getElementById('bt-result-caption').textContent=job.message||'';
    document.getElementById('bt-secondary-grid').replaceChildren();
    document.getElementById('bt-warning-count').textContent=job.error?'· 错误':'';
    document.querySelector('.result-notes').open=!!job.error;
    document.getElementById('bt-summary-grid').innerHTML = `<div class="card"><div class="label">状态</div><div class="value">${jobStatusLabel(job.status)}（${job.progress_pct||0}%）</div></div>`;
    document.getElementById('bt-warnings').innerHTML = job.error ? `<div class="warnbox">${job.error}</div>` : '';
    document.querySelector('#bt-trades tbody').innerHTML = '';
    document.querySelector('#bt-per-symbol tbody').innerHTML = '';
    ['bt-costs','bt-diagnosis','bt-walkforward-box','bt-compound'].forEach(id=>{const el=document.getElementById(id);if(el)el.replaceChildren();});
    drawEquityCurve([]);
    return;
  }
  sec.style.display = 'block';
  const s = job.summary;
  const performance = s.performance;
  const cagr = performance ? performance.cagr_pct : s.annualized_return_pct;
  const compoundBox = document.getElementById('bt-compound');
  compoundBox.replaceChildren();
  if(performance){
    const note = document.createElement('p'); note.className='hint'; note.textContent=performance.note; compoundBox.appendChild(note);
    const table = document.createElement('table');
    const heading = document.createElement('tr');
    for(const title of ['月份(UTC，首尾可不完整)','期初净权益','期末净权益','区间复利收益']){const th=document.createElement('th');th.textContent=title;heading.appendChild(th);} table.appendChild(heading);
    for(const month of performance.calendar_months || []){
      const tr=document.createElement('tr');
      for(const value of [month.month,fmtNum(month.start_equity),fmtNum(month.end_equity),month.return_pct == null ? '不可计算' : fmtNum(month.return_pct)+'%']){const td=document.createElement('td');td.textContent=value;tr.appendChild(td);} table.appendChild(tr);
    }
    compoundBox.appendChild(table);
  }
  document.getElementById('bt-warnings').innerHTML = (s.warnings||[]).map(w => `<div class="warnbox">${w}</div>`).join('');
  document.getElementById('bt-secondary-grid').innerHTML = `
    <div class="card"><div class="label">回测标的</div><div class="value" style="font-size:13px;">${(s.symbols||[]).join(', ')}</div></div>
    <div class="card"><div class="label">数据窗口</div><div class="value" style="font-size:13px;">${fmtTs(s.start_ts)} ~ ${fmtTs(s.end_ts)}</div></div>
    <div class="card"><div class="label">初始资金 → 结束资金</div><div class="value" style="font-size:15px;">${fmtNum(s.initial_capital,0)} → ${fmtNum(s.final_equity)}</div></div>
    <div class="card"><div class="label">累计复利收益</div><div class="value ${cls(s.return_pct)}">${fmtNum(s.return_pct)}%</div></div>
    <div class="card"><div class="label">复利年化收益(CAGR)</div><div class="value ${cls(cagr)}">${fmtNum(cagr)}%</div></div>
    <div class="card"><div class="label">年化波动率</div><div class="value">${fmtNum(s.annualized_vol_pct)}%</div></div>
    <div class="card"><div class="label">Sharpe</div><div class="value ${cls(s.sharpe)}">${fmtNum(s.sharpe)}</div></div>
    <div class="card"><div class="label">Sortino</div><div class="value ${cls(s.sortino)}">${fmtNum(s.sortino)}</div></div>
    <div class="card"><div class="label">最大回撤</div><div class="value neg">${fmtNum(s.max_drawdown_pct)}%</div></div>
    <div class="card"><div class="label">Calmar</div><div class="value ${cls(s.calmar)}">${fmtNum(s.calmar)}</div></div>
    <div class="card"><div class="label">年化换手率(倍)</div><div class="value">${fmtNum(s.turnover_annualized)}</div></div>
    <div class="card"><div class="label">完整持仓 / 减平仓记录</div><div class="value">${s.position_summary?.position_count??'未知'} / ${s.trade_count}</div></div>
    <div class="card"><div class="label">完整持仓胜率 / 最长连亏</div><div class="value">${fmtNum(s.position_summary?.win_rate_pct)}% / ${s.position_summary?.max_loss_streak??'未知'}</div></div>
    <div class="card"><div class="label">平均自适应风险乘数</div><div class="value">${fmtNum((s.avg_adaptive_risk_multiplier??1)*100,1)}%</div></div>
    <div class="card"><div class="label">最低自适应风险乘数</div><div class="value">${fmtNum((s.min_adaptive_risk_multiplier??1)*100,1)}%</div></div>
    <div class="card"><div class="label">自适应缩仓触发占比</div><div class="value">${fmtNum(s.adaptive_risk_active_pct||0,1)}%</div></div>
  `;
  document.getElementById('bt-summary-grid').innerHTML = [
    ['累计复利收益',fmtNum(s.return_pct)+'%',cls(s.return_pct)],
    ['最大回撤',fmtNum(s.max_drawdown_pct)+'%','neg'],
    ['期末权益',fmtNum(s.final_equity),''],
    ['完整持仓',s.position_summary?.position_count??'未知',''],
    ['完整持仓胜率',fmtNum(s.position_summary?.win_rate_pct)+'%',''],
    ['最长连续亏损',s.position_summary?.max_loss_streak??'未知',''],
  ].map(([label,value,tone])=>`<div class="card"><div class="label">${label}</div><div class="value ${tone}">${value}</div></div>`).join('');
  const chartLink=document.getElementById('bt-chart-link');chartLink.hidden=false;
  chartLink.href='/charts?job='+encodeURIComponent(jobId);
  document.getElementById('bt-result-caption').textContent=(s.symbols||[]).join(' · ')+'  /  '+fmtTs(s.start_ts)+' — '+fmtTs(s.end_ts);
  document.getElementById('bt-warning-count').textContent=(s.warnings||[]).length?'· '+s.warnings.length+' 项说明':'';

  renderCostBreakdown(s);
  drawEquityCurve(job.equity_curve || []);
  renderTrendDiagnosis(job.trend_diagnosis || (s.trend_diagnosis));
  renderWalkForward(s.walkforward);

  const perSymBody = document.querySelector('#bt-per-symbol tbody');
  const perSym = s.per_symbol || {};
  perSymBody.innerHTML = Object.keys(perSym).map(sym => {
    const p = perSym[sym];
    return `<tr><td>${sym}</td><td>${p.trade_count}</td>
      <td class="${cls(p.net_pnl)}">${fmtNum(p.net_pnl)}</td><td>${fmtNum(p.fees)}</td><td>${fmtNum(p.funding)}</td>
      <td>${fmtNum(p.last_trend_forecast,1)}</td><td>${fmtNum(p.last_carry_forecast,1)}</td>
      <td>${fmtNum((p.last_adaptive_risk_multiplier??1)*100,1)}%</td></tr>`;
  }).join('');

  const trBody = document.querySelector('#bt-trades tbody');
  trBody.innerHTML = (job.trades||[]).map(t => `<tr>
    <td>${t.symbol}</td><td>${t.side==='long'?'多':'空'}</td>
    <td>${fmtNum(t.entry_price,4)}</td><td>${fmtNum(t.exit_price,4)}</td>
    <td class="${cls(t.pnl)}">${fmtNum(t.pnl)}</td><td>${fmtNum(t.fees)}</td>
    <td>${fmtNum(t.funding)}</td><td>${fmtSecs(t.close_time-t.open_time)}</td>
    <td>${t.reason}</td></tr>`).join('');
}

function renderCostBreakdown(s){
  const el = document.getElementById('bt-costs');
  if(!el) return;
  if(s.gross_pnl_before_costs === undefined){ el.innerHTML=''; return; }
  const cost = (s.total_fees||0) + (s.total_slippage_cost||0) + (s.total_funding||0);
  const hasPositiveGross = s.gross_pnl_before_costs > 1e-9;
  const ratio = hasPositiveGross ? cost / s.gross_pnl_before_costs : null;
  const ratioText = hasPositiveGross ? `${fmtNum(ratio,2)}x` : '不适用（毛利≤0）';
  const ratioClass = hasPositiveGross && ratio <= 1 ? 'pos' : 'neg';
  el.innerHTML = `
    <h3 style="font-size:14px; color:var(--accent); margin-top:22px;">成本分解（这才是盈亏的真正去向）</h3>
    <div class="hint" style="margin-bottom:10px;">
      <b>滑点不在"手续费"里</b>——它直接体现为更差的成交价，很容易被忽略，所以单独列出来。
      净盈亏 = 未扣成本毛利 − 手续费 − 滑点 − 资金费。
      只有未扣成本毛利为正时，"总成本/毛利"才有意义；比值大于1表示正毛利被成本吃掉。
      毛利本身为负时显示“不适用”，不再用负比值误判为赚钱。
    </div>
    <div class="grid">
      <div class="card"><div class="label">未扣成本毛利</div><div class="value ${s.gross_pnl_before_costs>=0?'pos':'neg'}">${fmtNum(s.gross_pnl_before_costs)}</div></div>
      <div class="card"><div class="label">手续费</div><div class="value neg">-${fmtNum(s.total_fees)}</div></div>
      <div class="card"><div class="label">滑点(隐性)</div><div class="value neg">-${fmtNum(s.total_slippage_cost)}</div></div>
      <div class="card"><div class="label">资金费</div><div class="value ${(s.total_funding||0)<=0?'pos':'neg'}">${fmtNum(-(s.total_funding||0))}</div></div>
      <div class="card"><div class="label">总成本 / 毛利</div><div class="value ${ratioClass}">${ratioText}</div></div>
      <div class="card"><div class="label">实际使用的吃单费率</div><div class="value">${fmtNum((s.effective_taker_rate||0)*100,4)}%</div></div>
      <div class="card"><div class="label">平均每笔成交额</div><div class="value">${fmtNum(s.avg_trade_notional,0)} U</div></div>
      <div class="card"><div class="label">总成交名义额</div><div class="value">${fmtNum(s.total_traded_notional,0)} U</div></div>
      <div class="card"><div class="label">平均总杠杆</div><div class="value">${fmtNum(s.avg_gross_leverage,2)}x</div></div>
      <div class="card"><div class="label">峰值总杠杆</div><div class="value">${fmtNum(s.max_gross_leverage,2)}x</div></div>
    </div>`;
}

function renderTrendDiagnosis(d){
  const el = document.getElementById('bt-diagnosis');
  if(!d || !d.episode_count){
    el.innerHTML = d && d.note ? `<div class="hint" style="margin:12px 0;">趋势捕获诊断：${d.note}</div>` : '';
    return;
  }
  const rows = (d.episodes||[]).map(e => {
    const mark = e.participated ? '<span class="pos">✓</span>' : '<span class="neg">✗ 漏掉</span>';
    const f = (v,suf) => (typeof v==='number' && isFinite(v)) ? v.toFixed(0)+suf : '-';
    return `<tr><td>${mark}</td><td>${e.symbol}</td><td>${e.direction==='up'?'上涨':'下跌'}</td>
      <td class="${e.move_pct>=0?'pos':'neg'}">${fmtNum(e.move_pct,1)}%</td>
      <td>${f(e.capture_pct,'%')}</td><td>${f(e.entry_lag_pct,'%')}</td><td>${f(e.exit_early_pct,'%')}</td></tr>`;
  }).join('');
  el.innerHTML = `
    <h3 style="font-size:14px; color:var(--accent); margin-top:22px;">趋势捕获诊断（自动识别幅度≥${d.min_move_pct}%的行情段，逐段打分）</h3>
    <div class="hint" style="margin-bottom:10px;">
      这是事后诊断，用来分辨到底是"漏趋势"还是"抓到了但拿不满"：<b>参与率</b>低=真的漏了；
      <b>捕获率</b>低但参与率高=方向对但仓位太小（主要由目标年化波动率决定）；
      <b>入场滞后</b>高=进场太慢；<b>离场过早</b>高=拿不住。
    </div>
    <div class="grid">
      <div class="card"><div class="label">趋势段总数</div><div class="value">${d.episode_count}</div></div>
      <div class="card"><div class="label">参与率</div><div class="value ${d.participation_rate_pct>=80?'pos':'neg'}">${fmtNum(d.participation_rate_pct,0)}%</div></div>
      <div class="card"><div class="label">漏掉段数 / 平均幅度</div><div class="value">${d.missed_count} / ${fmtNum(d.missed_avg_move_pct,1)}%</div></div>
      <div class="card"><div class="label">捕获率(中位数)</div><div class="value">${fmtNum(d.median_capture_pct,0)}%</div></div>
      <div class="card"><div class="label">入场滞后(中位数)</div><div class="value">${fmtNum(d.median_entry_lag_pct,0)}%</div></div>
      <div class="card"><div class="label">离场过早(中位数)</div><div class="value">${fmtNum(d.median_exit_early_pct,0)}%</div></div>
    </div>
    <table><thead><tr><th>参与</th><th>标的</th><th>方向</th><th>行情幅度</th>
      <th>捕获率</th><th>入场滞后</th><th>离场过早</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderWalkForward(wf){
  const el = document.getElementById('bt-walkforward-box');
  if(!wf || !wf.folds || !wf.folds.length){ el.innerHTML=''; return; }
  const rows = wf.folds.map(f => f.error
    ? `<tr><td>第${f.fold_index}折</td><td colspan="5" class="neg">${f.error}</td></tr>`
    : `<tr><td>第${f.fold_index}折</td>
        <td>${fmtTs(f.start_ts)} ~ ${fmtTs(f.end_ts)}</td>
        <td class="${f.return_pct>=0?'pos':'neg'}">${fmtNum(f.return_pct)}%</td>
        <td>${fmtNum(f.sharpe)}</td><td class="neg">${fmtNum(f.max_drawdown_pct)}%</td>
        <td>${f.trade_count}</td></tr>`).join('');
  const good = wf.positive_fold_ratio_pct >= 70;
  el.innerHTML = `
    <h3 style="font-size:14px; color:var(--accent); margin-top:22px;">滚动样本外验证（${wf.folds.length}折）</h3>
    <div class="warnbox" style="${good?'background:#0d3b1f;border-color:var(--pos);color:var(--pos);':''}">
      ${wf.consistency_note}
    </div>
    <div class="hint" style="margin-bottom:10px;">
      看法：<b>不要只看均值</b>。重点看各折之间的离散程度、有多少折是正收益、最差一折有多差。
      如果只有一两折特别好、其余平平，说明整体收益是被某段特殊行情撑起来的，不能指望未来重现。
      另外注意：本策略参数是人工设定、不是从数据拟合的，所以这是<b>跨时间稳定性检验</b>，
      不等于"已做过防过拟合验证"——以后若引入需要训练的模型，还需要额外的 purged 交叉验证。
    </div>
    <div class="grid">
      <div class="card"><div class="label">各折收益均值</div><div class="value ${wf.mean_return_pct>=0?'pos':'neg'}">${fmtNum(wf.mean_return_pct)}%</div></div>
      <div class="card"><div class="label">中位数</div><div class="value">${fmtNum(wf.median_return_pct)}%</div></div>
      <div class="card"><div class="label">标准差(越小越稳)</div><div class="value">${fmtNum(wf.std_return_pct)}%</div></div>
      <div class="card"><div class="label">正收益折数占比</div><div class="value ${good?'pos':'neg'}">${fmtNum(wf.positive_fold_ratio_pct,0)}%</div></div>
      <div class="card"><div class="label">最差一折</div><div class="value neg">${fmtNum(wf.worst_fold_return_pct)}%</div></div>
      <div class="card"><div class="label">平均Sharpe</div><div class="value">${fmtNum(wf.mean_sharpe)}</div></div>
    </div>
    <table><thead><tr><th>折</th><th>时间窗口</th><th>收益</th><th>Sharpe</th><th>最大回撤</th><th>交易数</th></tr></thead>
      <tbody>${rows}</tbody></table>`;
}

let BT_EQUITY_POINTS=[];
function drawEquityCurve(points){
  BT_EQUITY_POINTS=points||[];
  const canvas = document.getElementById('btEquityCanvas');
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 800, cssH = 220;
  canvas.width = cssW * dpr; canvas.height = cssH * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,cssW,cssH);
  if(!points || points.length < 2){
    ctx.fillStyle = '#8b949e'; ctx.fillText('数据点不足，无法绘制曲线', 10, 20);
    return;
  }
  const vals = points.map(p => p.e);
  const minV = Math.min(...vals), maxV = Math.max(...vals);
  const pad = 24;
  const range = (maxV - minV) || 1;
  ctx.strokeStyle = '#8de0c1'; ctx.lineWidth = 1.75; ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad + ((p.t-points[0].t)/Math.max(points[points.length-1].t-points[0].t,1)) * (cssW - pad*2);
    const y = pad + (1 - (p.e - minV)/range) * (cssH - pad*2);
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
  ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
  ctx.fillText(maxV.toFixed(1), 2, pad);
  ctx.fillText(minV.toFixed(1), 2, cssH - 6);
  ctx.fillText(new Date(points[0].t*1000).toLocaleDateString(),pad+40,cssH-6);
  ctx.fillText(new Date(points[points.length-1].t*1000).toLocaleDateString(),Math.max(cssW-110,pad),cssH-6);
}

// ---------------------------------------------------------------- 引导与轮询
async function refreshBootstrap(){
  const data = await (await fetch('/api/config')).json();
  CUR_CONFIG = data;
  CUR_MODE = data.mode || 'paper';
  document.getElementById('api-host').value = (data._creds && data._creds.api_host) || 'https://api.gateio.ws/api/v4';
  document.getElementById('cred-status').textContent = data._creds && data._creds.is_set ? ('已保存: ' + data._creds.api_key) : '尚未设置';
  document.querySelectorAll('#mode-bar button').forEach(b => b.classList.toggle('selected', b.dataset.mode===CUR_MODE));

  buildFields('sys-core-fields', data.systematic || {}, SYS_CORE_LABELS);
  if ((data.systematic || {}).position_sizing_mode === 'volatility') {
    document.getElementById('sizing-policy').textContent = '当前显式使用旧版波动率分配研究模式，固定 5% 保证金票据未启用。';
  }
  document.getElementById('model-settings').textContent = JSON.stringify(data.systematic || {}, null, 2);
  buildFields('costs-fields', data.costs || {}, COST_LABELS, COST_TYPES);
  updateInvertBadge((data.systematic || {}).invert_direction);

  document.getElementById('symbols-chips').innerHTML = (data.symbols||[]).map(s =>
    `<span class="chip">${s}<button onclick="removeSymbol('${s}')">×</button></span>`).join('');
  // Public candidate screening is available before connecting an account.
}

async function refresh(){
  const token=++STATE_REFRESH_TOKEN;
  const res = await fetch('/api/state');
  if(!res.ok)throw new Error('HTTP '+res.status);
  const data = await res.json();
  if(token!==STATE_REFRESH_TOKEN)return;
  const s = data.summary;
  document.getElementById('mode-badge').className = 'badge ' + s.mode;
  document.getElementById('mode-badge').innerText = s.mode === 'paper' ? 'PAPER 模拟盘' : 'LIVE 实盘';
  document.getElementById('engine-badge').className = 'badge ' + (s.engine_running ? 'on':'off');
  document.getElementById('engine-badge').innerText = s.engine_running ? '引擎运行中' : '引擎已停止';

  document.getElementById('summary-grid').innerHTML = `
    <div class="card"><div class="label">账户权益</div><div class="value">${fmtNum(s.equity)} USDT</div></div>
    <div class="card"><div class="label">总盈亏(含浮盈)</div><div class="value ${cls(s.total_pnl)}">${fmtNum(s.total_pnl)}</div></div>
    <div class="card"><div class="label">当日盈亏</div><div class="value ${cls(s.day_pnl_pct)}">${fmtNum(s.day_pnl_pct)}%</div></div>
    <div class="card"><div class="label">最大回撤</div><div class="value neg">${fmtNum(s.max_drawdown_pct)}%</div></div>
    <div class="card"><div class="label">胜率 / 交易数</div><div class="value">${fmtNum(s.win_rate,1)}% (${s.trade_count})</div></div>
    <div class="card"><div class="label">盈亏比 PF</div><div class="value">${s.profit_factor===null?'不适用（无亏损分母）':fmtNum(s.profit_factor)}</div></div>
    <div class="card"><div class="label">累计手续费/资金费</div><div class="value neg">${fmtNum(s.total_fees_paid)} / ${fmtNum(s.total_funding_paid)}</div></div>
    <div class="card"><div class="label">当前持仓数</div><div class="value">${s.open_position_count}</div></div>
    <div class="card"><div class="label">日亏损熔断</div><div class="value ${data.circuit_breaker?'neg':''}">${data.daily_loss_limit_enabled === false ? '已关闭' : (data.circuit_breaker ? '熔断中':'正常')}</div></div>
    <div class="card"><div class="label">运行时长</div><div class="value">${fmtSecs(s.uptime_seconds)}</div></div>
  `;

  const p = data.portfolio || {};
  document.getElementById('portfolio-grid').innerHTML = `
    <div class="card"><div class="label">开仓额度模式</div><div class="value">${p.position_sizing_mode==='fixed_margin'?'固定保证金 5%':'波动率分配'}</div></div>
    <div class="card"><div class="label">当前组合信号置信度</div><div class="value">${fmtNum((p.portfolio_conviction||0)*100,1)}%</div></div>
    <div class="card"><div class="label">当前自适应风险乘数</div><div class="value">${fmtNum((p.average_risk_multiplier||1)*100,1)}%</div></div>
    <div class="card"><div class="label">缩放前组合波动率</div><div class="value">${fmtNum(p.portfolio_vol_before_scale_pct,1)}%</div></div>
    <div class="card"><div class="label">组合缩放系数</div><div class="value">${fmtNum(p.scale_factor,2)}</div></div>
    <div class="card"><div class="label">实际名义敞口 / 权益</div><div class="value">${fmtNum(p.actual_gross_leverage,2)}x</div></div>
    <div class="card"><div class="label">分散化收益</div><div class="value pos">${fmtNum(p.diversification_benefit_pct,1)}%</div></div>
    <div class="card"><div class="label">上次组合计算时间</div><div class="value" style="font-size:13px;">${fmtTs(p.ts)}</div></div>
  `;

  const posList = data.positions || [];
  const externals = posList.filter(p => p.role === 'external');
  const pendings = posList.filter(p => p.pending_close);
  const notice = document.getElementById('ownership-notice');
  let noticeHtml = '';
  if(externals.length){
    noticeHtml += `<div class="warn-box">⚠️ 检测到 <b>${externals.length}</b> 笔<b>不是本程序开的持仓</b>。
      程序不会平掉、也不会调整它们，并且会<b>跳过这些标的的全部交易</b>，直到你明确处理。
      要让策略接管，请在下方点“纳入策略管理”。</div>`;
  }
  if(pendings.length){
    noticeHtml += `<div class="warn-box">⚠️ 有 <b>${pendings.length}</b> 笔持仓的标的已从标的池移除，
      不会再收到任何调仓/退出指令。程序<b>不会自动平掉它</b>——请点“确认平仓”，或把该标的加回标的池。</div>`;
  }
  notice.innerHTML = noticeHtml;
  notice.style.display = noticeHtml ? 'block' : 'none';

  const posBody = document.querySelector('#positions tbody');
  posBody.innerHTML = posList.map(p => {
    const ext = p.role === 'external';
    const own = ext ? '<span class="neg">外部持仓</span>'
              : (p.pending_close ? '<span class="neg">待确认平仓</span>' : '策略管理中');
    let act = '—';
    if(ext) act = `<button class="btn" ${ADOPT_PENDING.has(p.symbol+'|'+p.side)?'disabled':''} onclick="adoptPos('${p.symbol}','${p.side}',this)">${ADOPT_PENDING.has(p.symbol+'|'+p.side)?'正在登记…':'纳入策略管理'}</button>`;
    else if(p.pending_close) act = `<button class="btn danger" onclick="confirmClosePos('${p.symbol}','${p.side}')">确认平仓</button>`;
    return `<tr>
    <td>${p.symbol}</td><td>${p.side==='long'?'多':'空'}</td><td>${p.size}</td>
    <td>${fmtNum(p.entry_price,4)}</td><td>${fmtNum(p.mark_price,4)}</td>
    <td class="${cls(p.unrealized_pnl)}">${fmtNum(p.unrealized_pnl)}</td>
    <td>${fmtSecs(p.holding_seconds)}</td><td>${own}</td><td>${act}</td></tr>`;
  }).join('');

  const sigBody = document.querySelector('#signals tbody');
  sigBody.innerHTML = (data.signals||[]).map(sg => `<tr>
    <td>${sg.symbol}</td><td>${sg.action==='long'?'多':(sg.action==='short'?'空':'观望')}</td>
    <td>${fmtNum(sg.score,0)}</td><td>${fmtNum((sg.net_edge_r||0)*10,1)}</td><td>${sg.reason}</td></tr>`).join('');

  const trBody = document.querySelector('#trades tbody');
  trBody.innerHTML = (data.trades||[]).map(t => `<tr>
    <td>${t.symbol}</td>
    <td>${t.side==='long'?'多':'空'}</td>
    <td>${fmtNum(t.entry_price,4)}</td><td>${fmtNum(t.exit_price,4)}</td>
    <td class="${cls(t.pnl)}">${fmtNum(t.pnl)}</td><td>${fmtNum(t.fees_paid)}</td>
    <td>${fmtNum(t.funding_paid)}</td><td>${fmtSecs(t.close_time-t.open_time)}</td>
    <td>${t.exit_reason}</td></tr>`).join('');

  document.getElementById('logs').innerText = (data.logs||[]).join('\\n');
}

fetch('/api/version').then(r=>r.json()).then(v=>{
  document.getElementById('app-version').textContent = 'v'+v.current;
  if(v.update_available) document.getElementById('upd-badge').style.display='inline-block';
}).catch(()=>{});

const requestedView=new URLSearchParams(window.location.search).get('view');
BT_VIEW_JOB_ID=new URLSearchParams(window.location.search).get('job');
showTab(requestedView||'backtest');
document.querySelectorAll('.workspace-sidebar [data-view]').forEach(link=>{
  if(link.dataset.view!=='charts')link.addEventListener('click',event=>{event.preventDefault();showTab(link.dataset.view);});
});
new ResizeObserver(()=>{if(ACTIVE_TAB==='backtest'&&BT_EQUITY_POINTS.length)drawEquityCurve(BT_EQUITY_POINTS);}).observe(document.getElementById('btEquityCanvas'));
refreshBootstrap().catch(error=>toast('配置加载失败：'+error.message,false));
BacktestSymbolSearch.init();
UniverseUI.init(BacktestSymbolSearch.setContracts);
refresh();
refreshBacktestList();
setInterval(refresh, 3000);
setInterval(refreshBacktestList, 3000);
</script>
</body>
</html>
"""


CHARTS_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>K线图 · Gate.io 量化策略控制台</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="/static/vendor/lightweight-charts-4.1.3.js"></script>
<script src="/static/chart_utils.js"></script>
<script src="/static/backtest_chart.js"></script>
<link rel="stylesheet" href="/static/workspace.css">
</head>
<body class="workspace" data-page="charts">
__WORKSPACE_NAV__
<div class="workspace-content">
<header class="workspace-topbar"><span class="workspace-crumb">研究 / <strong>K 线分析</strong></span><a id="chart-backtest-link" class="text-link" href="/?view=backtest">返回回测 ↗</a></header>
<main>
<div class="page-heading chart-page-heading"><div><h1>K 线分析</h1><p>价格走势与真实成交，一起复盘。</p></div><nav class="segmented-nav" aria-label="图表数据来源"><button id="nav-bt" onclick="showSub('bt')">回测成交</button><button id="nav-live" onclick="showSub('live')">实时 / 模拟盘</button></nav></div>
<div id="invert-warn" class="warnbox" style="display:none;">反向执行已开启：标记显示实际执行方向。</div>
<div id="sub-bt" class="subpage">
  <section class="chart-panel">
    <div class="chart-controls"><div class="field job-selector"><label for="bt-job">回测任务</label><select id="bt-job"></select></div><div class="field"><label for="bt-symbol">标的</label><select id="bt-symbol"></select></div><div class="field"><label for="bt-interval">K 线周期</label><select id="bt-interval"><option value="15m">15 分钟</option><option value="1h" selected>1 小时</option><option value="4h">4 小时</option><option value="1d">1 天</option></select></div><button class="btn" onclick="loadBtChart()">刷新</button></div>
    <p class="hint" id="bt-msg" role="status"></p>
    <div class="cards" id="bt-cards"></div>
    <div class="chart-toolbar"><button class="btn" onclick="BacktestChart.all()">全部区间</button><button class="btn" onclick="BacktestChart.latest()">最近成交</button><select id="bt-event-filter" aria-label="成交动作筛选" onchange="BacktestChart.draw()"><option value="all">全部动作</option><option value="open">首次开仓</option><option value="add">加仓</option><option value="reduce">减仓</option><option value="close">完全平仓</option></select><details class="chart-options"><summary>显示选项</summary><label><input type="checkbox" id="bt-marker-text" onchange="BacktestChart.draw()">显示标记文字</label></details></div>
    <div id="bt-chart" aria-label="回测行情与成交图"></div>
    <div class="chart-caption"><div class="legend"><span><span class="dot" style="background:#7edbb4"></span>开多 / 盈利平仓</span><span><span class="dot" style="background:#ef8c93"></span>开空 / 亏损平仓</span><span><span class="dot" style="background:#58a6ff"></span>加仓</span><span><span class="dot" style="background:#d29922"></span>减仓</span></div><span class="hint">滚轮缩放 · 拖拽平移</span></div>
    <div class="hint" id="bt-selected"></div>
    <div class="section-heading" style="margin:24px 0 8px"><h2>成交明细</h2><span class="hint">点击记录定位成交</span></div>
    <div class="table-scroll chart-table"><table id="bt-chart-trades"><thead><tr><th>成交时间</th><th>动作</th><th>方向</th><th>实际成交价</th><th>数量</th><th>已实现净盈亏</th><th>原因</th></tr></thead><tbody></tbody></table></div>
    <details class="panel-details"><summary>未入场原因与图表说明</summary><div class="hint" id="bt-blocks"></div><p class="hint">成交过密时可关闭标记文字，或使用动作筛选。“最近成交”定位当前筛选中的最后一笔；详细价格以下方记录为准。</p></details>
    <div class="chart-caption"><span class="hint"><a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView Lightweight Charts™</a> · © 2023 TradingView, Inc. · <a href="/static/vendor/LICENSE-lightweight-charts">Apache 2.0</a></span></div>
  </section>
</div>
<div id="sub-live" class="subpage">
  <section class="chart-panel">
    <div class="chart-controls"><div class="field"><label for="live-symbol">标的</label><select id="live-symbol"></select></div><div class="field"><label for="live-interval">K 线周期</label><select id="live-interval"><option value="1h">1 小时</option><option value="4h">4 小时</option><option value="1d">1 天</option></select></div><button class="btn" onclick="loadLiveChart()">刷新行情</button><details class="chart-options"><summary>显示选项</summary><div class="field"><label for="live-limit">K 线根数</label><input id="live-limit" type="number" value="300" min="50" max="2000"></div><label><input type="checkbox" id="live-auto" checked>每30秒自动刷新</label><label><input type="checkbox" id="live-marker-text" checked onchange="loadLiveChart()">显示标记文字</label></details></div>
    <p class="hint" id="live-msg" role="status"></p><div id="live-chart" aria-label="实时行情与成交图"></div>
    <div class="chart-caption"><div class="legend"><span><span class="dot" style="background:#7edbb4"></span>开多 / 盈利平仓</span><span><span class="dot" style="background:#ef8c93"></span>开空 / 亏损平仓</span><span><span class="dot" style="background:#58a6ff"></span>持仓成本</span></div><span class="hint">滚轮缩放 · 拖拽平移</span></div>
    <div class="section-heading" style="margin:24px 0 8px"><h2>最近成交</h2></div><div class="table-scroll chart-table"><table id="live-trades"><thead><tr><th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>开仓时间</th><th>平仓时间</th><th>原因</th></tr></thead><tbody></tbody></table></div>
  </section>
</div>
</main>
</div>

<script>
let ACTIVE_SUB = 'live';
let liveChart = null, liveSeries = null;
let livePriceLines = [];
let btChart = null, btSeries = null;
let liveAutoTimer = null;
let ALL_SYMBOLS = [];
let ALL_JOBS = [];

function showSub(name){
  ACTIVE_SUB = name;
  ['live','bt'].forEach(n => {
    document.getElementById('sub-'+n).classList.toggle('active', n===name);
    document.getElementById('nav-'+n).classList.toggle('active', n===name);
  });
  if(name==='bt')loadBtChart();
  else if(ALL_SYMBOLS.length)loadLiveChart();
  requestAnimationFrame(()=>{
    if(btChart && name==='bt')btChart.resize(document.getElementById('bt-chart').clientWidth,document.getElementById('bt-chart').clientHeight);
    if(liveChart && name==='live')liveChart.resize(document.getElementById('live-chart').clientWidth,document.getElementById('live-chart').clientHeight);
  });
}

function fmtNum(v, d){ return (typeof v === 'number' && isFinite(v)) ? v.toFixed(d==null?2:d) : '-'; }
function fmtTs(t){ if(!t) return '-'; return new Date(t*1000).toLocaleString(); }
function fmtSecs(s){ s=Math.floor(s||0); const h=Math.floor(s/3600), m=Math.floor((s%3600)/60);
  if(h) return h+'h'+m+'m'; return m+'m'; }

function makeChart(containerId){
  const el = document.getElementById(containerId);
  const chart = LightweightCharts.createChart(el, {
    width: el.clientWidth, height: el.clientHeight || 480,
    layout: { background: { color: '#101922' }, textColor: '#8fa5b4' },
    grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#30363d' },
    rightPriceScale: { borderColor: '#30363d' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  const series = chart.addCandlestickSeries({
    upColor: '#7edbb4', downColor: '#ef8c93', borderVisible: false,
    wickUpColor: '#7edbb4', wickDownColor: '#ef8c93',
  });
  new ResizeObserver(()=>{if(el.clientWidth>0)chart.applyOptions({width:el.clientWidth,height:el.clientHeight});}).observe(el);
  return { chart, series };
}

async function loadSymbolsIntoSelects(){
  const cfg = await (await fetch('/api/config')).json();
  ALL_SYMBOLS = cfg.symbols || [];
  const liveSel = document.getElementById('live-symbol');
  liveSel.innerHTML = ALL_SYMBOLS.map(s => `<option value="${s}">${s}</option>`).join('');
  document.getElementById('invert-warn').style.display =
    (cfg.systematic || {}).invert_direction ? 'block' : 'none';
}

async function loadJobsIntoSelect(){
  const data = await (await fetch('/api/backtest/list')).json();
  ALL_JOBS = (data.jobs || []).filter(j => j.status === 'done');
  const sel = document.getElementById('bt-job');
  const prev = sel.value;
  sel.innerHTML = ALL_JOBS.map(j => {
    const symTxt = (j.symbols||[]).join(',');
    const label = `${symTxt.length>40?symTxt.slice(0,40)+'…':symTxt} · ${new Date(j.created_at*1000).toLocaleString()}`;
    return `<option value="${j.id}">${label}</option>`;
  }).join('');
  if(prev) sel.value = prev;
  onBtJobChange();
}

function onBtJobChange(){
  const jobId = document.getElementById('bt-job').value;
  const job = ALL_JOBS.find(j => j.id === jobId);
  const back=document.getElementById('chart-backtest-link');back.href='/?view=backtest'+(jobId?'&job='+encodeURIComponent(jobId):'');
  const symSel = document.getElementById('bt-symbol');
  const prev = symSel.value;
  const syms = (job && job.symbols) || [];
  symSel.innerHTML = syms.map(s => `<option value="${s}">${s}</option>`).join('');
  if(prev && syms.includes(prev)) symSel.value = prev;
  const intervalSelect=document.getElementById('bt-interval');
  const source=job?.summary?.short_interval;
  for(const option of intervalSelect.options){
    option.disabled=!!source && (ChartUtils.seconds[option.value]<ChartUtils.seconds[source] || ChartUtils.seconds[option.value]%ChartUtils.seconds[source]!==0);
  }
  if(intervalSelect.selectedOptions[0]?.disabled){
    intervalSelect.value=[...intervalSelect.options].find(option=>!option.disabled)?.value||'1h';
  }
  if(ACTIVE_SUB==='bt')loadBtChart();
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('bt-job').addEventListener('change', onBtJobChange);
  for(const id of ['bt-symbol','bt-interval'])document.getElementById(id).addEventListener('change',loadBtChart);
  for(const id of ['live-symbol','live-interval'])document.getElementById(id).addEventListener('change',loadLiveChart);
});

// ---------------------------------------------------------- 实时/模拟盘图表
let LIVE_SEQUENCE=0, LIVE_KEY='';
async function loadLiveChart(){
  const token=++LIVE_SEQUENCE;
  const symbol = document.getElementById('live-symbol').value;
  const interval = document.getElementById('live-interval').value;
  const limit = document.getElementById('live-limit').value;
  const key=[symbol,interval,limit].join('|');
  const msg=document.getElementById('live-msg');
  if(!symbol){msg.textContent='请先在设置页添加交易标的';return;}
  msg.textContent='加载中…';
  try {
    const response=await fetch(`/api/klines?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=${encodeURIComponent(limit)}`);
    const data=await response.json();
    if(token!==LIVE_SEQUENCE)return;
    if(!response.ok||!data.ok)throw new Error(data.message||'行情请求失败');
    const candles=ChartUtils.candles(data.candles);
    if(typeof LightweightCharts==='undefined')throw new Error('图表库未加载，请刷新页面');
    if(!liveChart){const r=makeChart('live-chart');liveChart=r.chart;liveSeries=r.series;}
    liveSeries.setMarkers([]);
    livePriceLines.forEach(line=>liveSeries.removePriceLine(line));livePriceLines=[];
    liveSeries.applyOptions({priceFormat:ChartUtils.priceFormat(candles)});
    liveSeries.setData(candles);
    if(key!==LIVE_KEY)liveChart.timeScale().fitContent();
    LIVE_KEY=key;
    document.querySelector('#live-trades tbody').replaceChildren();
    msg.textContent=`${symbol} ${interval} 共${candles.length}根K线`;
    // A failed account-state request must not hide successfully loaded candles.
    try {
      const stateResponse=await fetch('/api/state');
      if(!stateResponse.ok)throw new Error('账户状态请求失败');
      const stateRes=await stateResponse.json();
      if(token!==LIVE_SEQUENCE)return;
      const trades=(stateRes.trades||[]).filter(t=>t.symbol===symbol);
      const positions=(stateRes.positions||[]).filter(p=>p.symbol===symbol);
      const markers=ChartUtils.liveMarkers(trades,candles,interval,document.getElementById('live-marker-text').checked);
      liveSeries.setMarkers(markers);
      livePriceLines=positions.filter(p=>Number.isFinite(p.entry_price)&&p.entry_price>0).map(p=>liveSeries.createPriceLine({
        price:p.entry_price,color:'#58a6ff',lineWidth:1,
        lineStyle:LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title:`${p.side==='long'?'多':'空'}仓开仓价`,
      }));
      msg.textContent+=`，当前区间${markers.length}个成交标记，持仓${positions.length}笔`;
      const tbody=document.querySelector('#live-trades tbody');
      tbody.innerHTML=trades.map(t=>`<tr>
        <td>${t.side==='long'?'多':'空'}</td><td>${fmtNum(t.entry_price,6)}</td><td>${fmtNum(t.exit_price,6)}</td>
        <td class="${t.pnl>=0?'pos':'neg'}">${fmtNum(t.pnl)}</td>
        <td>${fmtTs(t.open_time)}</td><td>${fmtTs(t.close_time)}</td><td>${t.exit_reason||''}</td>
      </tr>`).join('');
    } catch(error){if(token===LIVE_SEQUENCE)msg.textContent+='；成交标记暂不可用：'+error.message;}
  } catch(error){
    if(token!==LIVE_SEQUENCE)return;
    if(liveSeries){
      liveSeries.setMarkers([]);liveSeries.setData([]);
      livePriceLines.forEach(line=>liveSeries.removePriceLine(line));livePriceLines=[];
    }
    LIVE_KEY='';document.querySelector('#live-trades tbody').replaceChildren();
    msg.textContent='K线加载失败：'+error.message;
  }
}

function scheduleLiveAuto(){
  if(liveAutoTimer) clearInterval(liveAutoTimer);
  liveAutoTimer = setInterval(() => {
    if(ACTIVE_SUB === 'live' && document.getElementById('live-auto').checked){
      loadLiveChart();
    }
  }, 30000);
}

// ---------------------------------------------------------- 回测图表
async function loadBtChart(){ return BacktestChart.load(); }

(async function init(){
  try {await loadSymbolsIntoSelects();}
  catch(error){document.getElementById('live-msg').textContent='标的加载失败：'+error.message;}
  try {await loadJobsIntoSelect();}
  catch(error){document.getElementById('bt-msg').textContent='回测列表加载失败：'+error.message;}
  const params = new URLSearchParams(window.location.search);
  if(params.get('job')){
    document.getElementById('bt-job').value=params.get('job');onBtJobChange();showSub('bt');
  }else{showSub(ALL_JOBS.length?'bt':'live');}
  document.getElementById('nav-charts').setAttribute('aria-current','page');
  scheduleLiveAuto();
})();
</script>
</body>
</html>
"""


MANUAL_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>手动开单测试 · Gate.io 量化策略控制台</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#c9d1d9; --muted:#8b949e;
          --accent:#58a6ff; --pos:#3fb950; --neg:#f85149; --warn:#e3b341; }
  * { box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',Arial,sans-serif; margin:0; }
  header { display:flex; align-items:center; justify-content:space-between; padding:14px 24px;
           border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--bg); z-index:10; }
  header h1 { font-size:18px; margin:0; color:var(--accent); }
  header a { color:var(--text); text-decoration:none; border:1px solid var(--border); border-radius:6px;
             padding:8px 16px; font-size:14px; }
  header a:hover { border-color:var(--accent); }
  main { padding:20px 24px; max-width:1250px; margin:0 auto; }
  .panels { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media(max-width:1000px){ .panels{ grid-template-columns:1fr; } }
  section { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px 18px; margin-bottom:16px; }
  section h3 { margin-top:0; font-size:15px; color:var(--accent); }
  .row { display:flex; gap:10px; align-items:flex-end; flex-wrap:wrap; margin-bottom:12px; }
  input,select,button.btn { background:#0d1117; color:var(--text); border:1px solid var(--border);
        border-radius:6px; padding:8px 12px; font-size:14px; }
  input { width:100%; }
  button.btn { cursor:pointer; } button.btn:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:700; }
  button.danger { background:#3a0d0d; color:var(--neg); border-color:#5c1a1a; font-weight:700; }
  .field { display:flex; flex-direction:column; gap:4px; flex:1; min-width:110px; }
  .field label { font-size:12px; color:var(--muted); }
  .hint { font-size:12px; color:var(--muted); line-height:1.6; }
  .warnbox { background:#3a2400; border:1px solid var(--warn); color:var(--warn); padding:10px 14px;
             border-radius:8px; margin-bottom:14px; font-size:13px; line-height:1.6; }
  .livebox { background:#4a0d0d; border:1px solid var(--neg); color:#ff9d97; padding:12px 14px;
             border-radius:8px; margin-bottom:14px; font-size:13px; line-height:1.6; font-weight:600; }
  .badge { padding:2px 10px; border-radius:10px; font-size:12px; font-weight:600; }
  .badge.paper { background:#4b3b00; color:var(--warn); }
  .badge.live { background:#4a0d0d; color:var(--neg); }
  table { width:100%; border-collapse:collapse; font-size:13px; margin-top:8px; }
  th,td { border-bottom:1px solid #21262d; padding:6px 8px; text-align:left; }
  th { color:var(--muted); font-weight:500; }
  .pos { color:var(--pos); } .neg { color:var(--neg); } .warn { color:var(--warn); }
  .steps li { margin:6px 0; font-size:13px; line-height:1.5; }
  .preview { background:#0d1117; border:1px dashed var(--border); border-radius:6px;
             padding:10px 14px; margin:10px 0; font-size:13px; line-height:1.9; }
</style>
</head>
<body>
<header>
  <h1>🧪 手动开单测试 <span id="mode-badge" class="badge"></span></h1>
  <div style="display:flex;gap:6px;align-items:center">
    <a href="/charts" style="color:var(--text);text-decoration:none;border:1px solid var(--border);border-radius:6px;padding:8px 14px;font-size:14px;">📈 K线图</a>
    <a href="/update" style="color:var(--text);text-decoration:none;border:1px solid var(--border);border-radius:6px;padding:8px 14px;font-size:14px;">⬆️ 检查更新</a>
    <a href="/">← 返回控制台</a>
  </div>
</header>
<main>
  <div id="mode-warn"></div>
  <div class="warnbox">
    这个页面用来验证 API 连通性和下单参数换算，<b>完全独立于策略引擎</b>——它不会写入策略持仓账本，
    这里开出来的仓位会被策略引擎标记为<b>外部持仓</b>：引擎不会平掉、也不会调整它，
    并且会跳过该标的的全部交易，直到你在「控制台」里点“纳入策略管理”。测试完请记得手动平掉。
    <br>加密货币按固定保证金规则计算；预览会显示杠杆、名义价值和初始保证金。非加密合约可自填名义价值与杠杆。
  </div>

  <div class="panels">
    <section>
      <h3>① 贵金属（黄金/白银）</h3>
      <div class="hint" style="margin-bottom:12px;">Gate 的贵金属也是永续合约，同样有资金费率。合约代码以官网实际上线为准。</div>
      <div id="form-metal"></div>
    </section>
    <section>
      <h3>② 加密货币</h3>
      <div class="hint" style="margin-bottom:12px;">BTC/ETH 等 USDT 本位永续合约。</div>
      <div id="form-crypto"></div>
    </section>
  </div>

  <section>
    <h3>执行结果</h3>
    <div id="result"><div class="hint">还没有执行任何操作。建议先点「预览换算」确认张数和保证金无误，再点「确认下单」。</div></div>
  </section>

  <section>
    <h3>当前账户持仓（实时查询交易所）</h3>
    <div class="row">
      <button class="btn" onclick="loadPositions()">刷新持仓</button>
      <span class="hint" id="pos-msg"></span>
    </div>
    <table id="positions"><thead><tr>
      <th>合约</th><th>方向</th><th>张数</th><th>开仓价</th><th>标记价</th><th>保证金模式</th><th>未实现盈亏</th><th>操作</th>
    </tr></thead><tbody></tbody></table>
  </section>
</main>

<script>
let CUR_MODE = 'paper';

const PRESETS = {
  metal:  { id:'metal',  symbols:['XAU_USDT','XAG_USDT'], defLev:10 },
  crypto: { id:'crypto', symbols:['BTC_USDT','ETH_USDT','SOL_USDT'], defLev:10 },
};

function formHtml(p){
  return `
    <div class="row">
      <div class="field"><label>合约代码</label>
        <input id="${p.id}-symbol" list="${p.id}-list" value="${p.symbols[0]}">
        <datalist id="${p.id}-list">${p.symbols.map(s=>`<option value="${s}">`).join('')}</datalist>
      </div>
      <div class="field" style="max-width:110px;"><label>方向</label>
        <select id="${p.id}-side"><option value="long">做多</option><option value="short">做空</option></select>
      </div>
    </div>
    <div class="hint">加密货币按账户权益 5% × 币种杠杆生成全仓票据，预览显示实际额度；下列自定义额度仅适用于非加密合约。</div>
    <div class="row" ${p.id==='crypto'?'style="display:none"':''}>
      <div class="field"><label>非加密合约名义价值(USDT)</label><input id="${p.id}-notional" type="number" min="0" step="any" value="100"></div>
      <div class="field" style="max-width:100px;"><label>杠杆(倍)</label><input id="${p.id}-lev" type="number" min="1" step="1" value="${p.defLev}"></div>
    </div>
    <div class="row">
      <div class="field"><label>止盈价(留空=不挂)</label><input id="${p.id}-tp" type="number" min="0" step="any" placeholder="可留空"></div>
      <div class="field"><label>止损价(留空=不挂)</label><input id="${p.id}-sl" type="number" min="0" step="any" placeholder="可留空"></div>
    </div>
    <div class="row">
      <button class="btn" onclick="preview('${p.id}')">预览换算</button>
      <button class="btn danger" onclick="submitOrder('${p.id}')">确认下单</button>
    </div>
    <div id="${p.id}-preview"></div>`;
}

document.getElementById('form-metal').innerHTML = formHtml(PRESETS.metal);
document.getElementById('form-crypto').innerHTML = formHtml(PRESETS.crypto);

function readForm(id){
  const g = k => document.getElementById(id+'-'+k).value;
  return { symbol:g('symbol').trim().toUpperCase(), side:g('side'),
           notional:parseFloat(g('notional')), leverage:parseFloat(g('lev')),
           tp: g('tp')===''?null:parseFloat(g('tp')), sl: g('sl')===''?null:parseFloat(g('sl')) };
}

async function preview(id){
  const body = readForm(id);
  const el = document.getElementById(id+'-preview');
  el.innerHTML = '<div class="hint">查询中...</div>';
  const r = await (await fetch('/api/manual/preview',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
  if(!r.ok){ el.innerHTML = `<div class="preview neg">${r.message}</div>`; return; }
  const warn = r.warnings && r.warnings.length
    ? `<div class="warn">⚠️ ${r.warnings.join('<br>⚠️ ')}</div>` : '';
  el.innerHTML = `<div class="preview">
    当前标记价：<b>${r.mark_price}</b><br>
    换算张数：<b>${r.contracts}</b> 张（每张 ${r.quanto_multiplier} ${r.base}）<br>
    实际名义价值：<b>${r.actual_notional.toFixed(2)}</b> USDT（目标 ${r.requested_notional.toFixed(2)}）<br>
    占用保证金：<b>${r.margin.toFixed(2)}</b> USDT （= 名义价值 ÷ ${r.leverage}x）<br>
    预估开仓手续费：${r.est_fee.toFixed(4)} USDT<br>
    ${r.tp?`止盈 ${r.tp}（距现价 ${r.tp_pct}%）<br>`:''}
    ${r.sl?`止损 ${r.sl}（距现价 ${r.sl_pct}%，按此仓位约亏 ${r.sl_loss.toFixed(2)} USDT）<br>`:''}
    ${warn}</div>`;
}

async function submitOrder(id){
  const body = readForm(id);
  if(!body.symbol){ alert('请填写合约代码'); return; }
  const quote = await (await fetch('/api/manual/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
  if(!quote.ok){ alert(quote.message); return; }
  const modeTxt = CUR_MODE==='live' ? '【实盘 LIVE·真实资金】' : '【模拟盘 PAPER】';
  const msg = `${modeTxt}\\n\\n${body.symbol} ${body.side==='long'?'做多':'做空'}\\n`
            + `全仓名义价值约 ${quote.actual_notional.toFixed(2)} USDT，${quote.leverage}x，保证金约 ${quote.margin.toFixed(2)} USDT\\n`
            + `止盈 ${body.tp??'不挂'}　止损 ${body.sl??'不挂'}\\n\\n确认下单？`;
  if(!confirm(msg)) return;
  const el = document.getElementById('result');
  el.innerHTML = '<div class="hint">下单中...</div>';
  const r = await (await fetch('/api/manual/order',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();
  const steps = (r.steps||[]).map(s =>
    `<li>${s.ok?'<span class="pos">✔</span>':'<span class="neg">✘</span>'} <b>${s.name}</b>：${s.message}</li>`).join('');
  el.innerHTML = `<div class="${r.ok?'pos':'neg'}" style="font-weight:600;margin-bottom:8px;">
      ${r.ok?'执行完成':'执行失败或部分失败'}　${r.message||''}</div>
    <ul class="steps">${steps}</ul>`;
  loadPositions();
}

async function loadPositions(){
  const el = document.querySelector('#positions tbody');
  document.getElementById('pos-msg').textContent = '查询中...';
  const r = await (await fetch('/api/manual/positions')).json();
  if(!r.ok){ document.getElementById('pos-msg').textContent = r.message; el.innerHTML=''; return; }
  document.getElementById('pos-msg').textContent = `共 ${r.positions.length} 条持仓`;
  el.innerHTML = r.positions.map(p=>`<tr>
    <td>${p.contract}</td><td>${p.side==='long'?'多':'空'}</td><td>${p.size}</td>
    <td>${p.entry_price}</td><td>${p.mark_price}</td>
    <td class="${p.margin_mode==='cross'?'pos':'neg'}">${p.margin_mode==='cross'?('全仓 '+(p.cross_leverage_limit||'')+'x'):'⚠️ 逐仓'}</td>
    <td class="${p.unrealised_pnl>=0?'pos':'neg'}">${Number(p.unrealised_pnl).toFixed(4)}</td>
    <td><button class="btn danger" onclick="closePos('${p.contract}','${p.side}')">平掉</button></td>
  </tr>`).join('') || '<tr><td colspan="8" class="hint">当前无持仓</td></tr>';
}

async function closePos(symbol, side){
  if(!confirm(`确认市价平掉 ${symbol} 的${side==='long'?'多':'空'}仓？`)) return;
  const r = await (await fetch('/api/manual/close',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,side})})).json();
  document.getElementById('result').innerHTML =
    `<div class="${r.ok?'pos':'neg'}">${r.message}</div>`;
  loadPositions();
}

(async function init(){
  const cfg = await (await fetch('/api/config')).json();
  CUR_MODE = cfg.mode || 'paper';
  const b = document.getElementById('mode-badge');
  b.className = 'badge ' + CUR_MODE;
  b.textContent = CUR_MODE==='live' ? 'LIVE 实盘·真实资金' : 'PAPER 模拟盘';
  document.getElementById('mode-warn').innerHTML = CUR_MODE==='live'
    ? `<div class="livebox">⚠️ 当前是实盘模式，这个页面下的单会用<b>真实资金</b>在 Gate 上成交。
       建议先把「设置 → 运行模式」切到模拟盘验证参数换算，确认无误后再切回实盘做小额连通性测试。</div>`
    : `<div class="warnbox">当前是模拟盘：下单只在本地账本模拟，不会碰真实资金。
       注意模拟盘<b>不会真正触发止盈止损</b>，那部分只验证参数是否被正确接受。</div>`;
  loadPositions();
})();
</script>
</body>
</html>
"""


UPDATE_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>检查更新 · Gate.io 量化控制台</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>__BASE_CSS__
  .verbox { display:flex; align-items:center; gap:24px; flex-wrap:wrap;
            background:var(--panel2); border:1px solid var(--border);
            border-radius:10px; padding:18px 22px; margin-bottom:16px; }
  .verbox .big { font-size:30px; font-weight:700; letter-spacing:.5px; }
  .verbox .arrow { font-size:22px; color:var(--muted); }
  .verbox .col { display:flex; flex-direction:column; gap:2px; }
  .verbox .col span:first-child { font-size:11.5px; color:var(--muted); }
  .changelog { background:#0d1117; border:1px solid var(--border); border-radius:9px;
               padding:16px 20px; max-height:440px; overflow-y:auto; font-size:13.5px; }
  .changelog h2 { font-size:16px; color:var(--accent); margin:0 0 10px; }
  .changelog h3 { font-size:14px; color:var(--accent2); margin:18px 0 8px; }
  .changelog ul { margin:6px 0; padding-left:22px; }
  .changelog li { margin:5px 0; }
  .changelog code { background:var(--panel2); padding:1px 5px; border-radius:4px; font-size:12.5px; }
  .changelog strong { color:#e6edf3; }
  .steps li { margin:7px 0; }
  .spin { display:inline-block; width:13px; height:13px; border:2px solid var(--border);
          border-top-color:var(--accent); border-radius:50%; animation:sp .7s linear infinite;
          vertical-align:-2px; margin-right:6px; }
  @keyframes sp { to { transform:rotate(360deg); } }
</style>
</head>
<body>
__HEADER__
<main>
  <div id="banner"></div>

  <section>
    <h3>版本信息</h3>
    <div class="verbox">
      <div class="col"><span>当前版本</span><span class="big" id="cur">—</span></div>
      <div class="arrow" id="arrow" style="display:none">→</div>
      <div class="col" id="latest-col" style="display:none">
        <span>最新版本</span><span class="big pos" id="latest">—</span>
      </div>
      <div style="flex:1"></div>
      <div class="col" style="align-items:flex-end">
        <span id="lastcheck" class="hint"></span>
        <div class="row" style="margin:6px 0 0">
          <button class="btn primary" id="btn-check" onclick="doCheck()">立即检查</button>
        </div>
      </div>
    </div>

    <div class="row">
      <div class="field" style="flex:1;min-width:260px">
        <label>GitHub 仓库（用户名/仓库名）</label>
        <input id="repo" placeholder="例如 someone/gate_quant_bot">
      </div>
      <div class="field" style="max-width:120px">
        <label>分支</label><input id="branch" value="main">
      </div>
      <button class="btn" onclick="saveCfg()">保存</button>
      <label class="hint" style="display:flex;align-items:center;gap:6px">
        <input type="checkbox" id="autocheck"> 启动时自动检查
      </label>
    </div>
    <div class="hint">留空会自动从 git remote 推断。私有仓库无法用匿名接口检查。</div>
  </section>

  <section id="action-sec" style="display:none">
    <h3>更新操作</h3>
    <div id="action-body"></div>
    <div id="steps-box"></div>
  </section>

  <section>
    <h3 id="cl-title">更新内容</h3>
    <div class="changelog" id="changelog"><span class="hint">加载中…</span></div>
  </section>
</main>

<script>
let INFO = null;

function md2html(md){
  if(!md) return '<span class="hint">（没有提供更新说明）</span>';
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  let out = [], inList = false;
  for(let raw of md.split('\\n')){
    let t = esc(raw.trimEnd());
    if(/^###\\s+/.test(t)){ if(inList){out.push('</ul>');inList=false;} out.push('<h3>'+t.replace(/^###\\s+/,'')+'</h3>'); continue; }
    if(/^##\\s+/.test(t)){ if(inList){out.push('</ul>');inList=false;} out.push('<h2>'+t.replace(/^##\\s+/,'')+'</h2>'); continue; }
    if(/^\\s*[-*]\\s+/.test(t)){
      if(!inList){ out.push('<ul>'); inList=true; }
      out.push('<li>'+inline(t.replace(/^\\s*[-*]\\s+/,''))+'</li>'); continue;
    }
    if(inList){ out.push('</ul>'); inList=false; }
    if(t.trim()==='' ) { out.push(''); continue; }
    if(/^---+$/.test(t.trim())) { out.push('<hr style="border:none;border-top:1px solid var(--border);margin:14px 0">'); continue; }
    out.push('<p style="margin:8px 0">'+inline(t)+'</p>');
  }
  if(inList) out.push('</ul>');
  return out.join('\\n');
  function inline(x){
    return x.replace(/`([^`]+)`/g,'<code>$1</code>')
            .replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>');
  }
}

function fmtTs(t){ return t ? new Date(t*1000).toLocaleString() : '从未检查过'; }

async function loadInit(){
  const cfg = await (await fetch('/api/update/config')).json();
  document.getElementById('repo').value = cfg.repo || '';
  document.getElementById('branch').value = cfg.branch || 'main';
  document.getElementById('autocheck').checked = !!cfg.auto_check;
  document.getElementById('cur').textContent = 'v' + cfg.current;
  document.getElementById('lastcheck').textContent = '上次检查：' + fmtTs(cfg.last_check_ts);
  const cl = await (await fetch('/api/update/changelog')).json();
  document.getElementById('changelog').innerHTML = md2html(cl.changelog);
  document.getElementById('cl-title').textContent = '当前版本的更新内容（v' + cfg.current + '）';
  if(cfg.cached) render(cfg.cached);
}

async function doCheck(){
  const btn = document.getElementById('btn-check');
  btn.disabled = true; btn.innerHTML = '<span class="spin"></span>检查中…';
  try{
    const r = await (await fetch('/api/update/check',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({repo:document.getElementById('repo').value.trim(),
                            branch:document.getElementById('branch').value.trim()||'main'})})).json();
    render(r);
    document.getElementById('lastcheck').textContent = '上次检查：' + fmtTs(r.last_check_ts||Date.now()/1000);
  } finally { btn.disabled=false; btn.textContent='立即检查'; }
}

function render(r){
  INFO = r;
  const banner = document.getElementById('banner');
  const sec = document.getElementById('action-sec');
  const body = document.getElementById('action-body');
  document.getElementById('steps-box').innerHTML = '';

  if(!r.ok){
    banner.innerHTML = '<div class="errbox">'+r.message+'</div>';
    sec.style.display='none'; return;
  }
  if(!r.has_update){
    banner.innerHTML = '<div class="okbox">✔ '+r.message+'</div>';
    document.getElementById('arrow').style.display='none';
    document.getElementById('latest-col').style.display='none';
    sec.style.display='none'; return;
  }

  document.getElementById('arrow').style.display='block';
  document.getElementById('latest-col').style.display='flex';
  document.getElementById('latest').textContent = 'v'+r.latest;
  banner.innerHTML = r.skipped
    ? '<div class="warnbox">发现新版本 v'+r.latest+'，但你之前选择了跳过这个版本。想装的话点下面的「仍要更新」。</div>'
    : '<div class="warnbox">🎉 '+r.message+'</div>';

  if(r.changelog){
    document.getElementById('cl-title').textContent = '新版本更新内容（v'+r.latest+'）';
    document.getElementById('changelog').innerHTML = md2html(r.changelog);
  }

  sec.style.display='block';
  let html = '';
  if(r.can_auto_update){
    html += '<div class="hint" style="margin-bottom:12px">'
         +  '检测到本地是 git 克隆，可以直接一键更新（<code>git pull</code>）。'
         +  '你的 <code>data/</code>（API Key、数据库、缓存）和 <code>config.yaml</code> '
         +  '都被 gitignore 忽略，<b>不会被更新覆盖</b>。</div>'
         +  '<div class="row">'
         +  '<button class="btn success" onclick="doUpdate()">立即更新到 v'+r.latest+'</button>'
         +  '<button class="btn" onclick="doSkip()">跳过这个版本</button>'
         +  '<a class="btn" href="'+r.html_url+'" target="_blank" style="text-decoration:none">在 GitHub 查看</a>'
         +  '</div>';
  } else {
    html += '<div class="warnbox">当前目录不是 git 克隆（可能是下载 zip 解压的），'
         +  '无法一键更新。请手动下载新版，解压后<b>把旧目录里的 <code>data/</code> 和 '
         +  '<code>config.yaml</code> 复制过去</b>——这两个是你的密钥和配置。</div>'
         +  '<div class="row">'
         +  '<a class="btn primary" href="'+r.download_url+'" target="_blank" style="text-decoration:none">下载 v'+r.latest+'</a>'
         +  '<button class="btn" onclick="doSkip()">跳过这个版本</button>'
         +  '<a class="btn" href="'+r.html_url+'" target="_blank" style="text-decoration:none">在 GitHub 查看</a>'
         +  '</div>';
  }
  body.innerHTML = html;
}

async function doUpdate(){
  if(!confirm('确认更新到 v'+INFO.latest+'？\\n\\n更新前请确保：\\n· 交易引擎已停止\\n· 没有未平仓的持仓\\n\\n更新后需要重启程序。')) return;
  const box = document.getElementById('steps-box');
  box.innerHTML = '<div class="hint"><span class="spin"></span>正在更新…</div>';
  const r = await (await fetch('/api/update/perform',{method:'POST'})).json();
  const steps = (r.steps||[]).map(s=>
    '<li>'+(s.ok?'<span class="pos">✔</span>':'<span class="neg">✘</span>')+' <b>'+s.name+'</b>：'
    + String(s.message).replace(/\\n/g,'<br>')+'</li>').join('');
  box.innerHTML = '<div class="'+(r.ok?'okbox':'errbox')+'" style="margin-top:12px">'+r.message+'</div>'
                + (steps ? '<ul class="steps">'+steps+'</ul>' : '');
}

async function doSkip(){
  await fetch('/api/update/skip',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({version:INFO.latest})});
  document.getElementById('banner').innerHTML =
    '<div class="okbox">已跳过 v'+INFO.latest+'，之后不会再提醒这个版本。'
    +'<a href="#" onclick="unskip();return false" style="color:inherit;text-decoration:underline"> 取消跳过</a></div>';
  document.getElementById('action-sec').style.display='none';
}

async function unskip(){
  await fetch('/api/update/unskip',{method:'POST'});
  doCheck();
}

async function saveCfg(){
  await fetch('/api/update/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({repo:document.getElementById('repo').value.trim(),
                         branch:document.getElementById('branch').value.trim()||'main',
                         auto_check:document.getElementById('autocheck').checked})});
  document.getElementById('banner').innerHTML='<div class="okbox">设置已保存</div>';
  setTimeout(()=>{document.getElementById('banner').innerHTML='';},2000);
}

loadInit();
</script>
</body>
</html>
"""


def create_app(state: StateStore, config_store: ConfigStore, cred_store: CredentialStore,
               controller: EngineController, backtest_controller: BacktestController,
               universe_service=None) -> Flask:
    app = Flask(__name__)
    app.json = StrictJSONProvider(app)
    from pathlib import Path
    universe = universe_service or UniverseService(
        snapshot_dir=Path(getattr(backtest_controller, "result_dir", "./data/backtests")).parent / "universe")
    app.extensions["universe"] = universe
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    @app.route("/")
    def index():
        return render_template_string(PAGE.replace("__WORKSPACE_NAV__", WORKSPACE_NAV))

    @app.route("/charts")
    def charts_page():
        return render_template_string(CHARTS_PAGE.replace("__WORKSPACE_NAV__", WORKSPACE_NAV))

    @app.route("/manual")
    def manual_page():
        return render_template_string(MANUAL_PAGE)


    # ---------------------------------------------------------- 版本 / 在线更新
    def _upd_cfg() -> dict:
        return (config_store.snapshot().get("update") or {})

    @app.route("/update")
    def update_page():
        html = (UPDATE_PAGE.replace("__BASE_CSS__", BASE_CSS)
                            .replace("__HEADER__", header_html("update")))
        return render_template_string(html)

    @app.route("/api/version")
    def api_version():
        """顶栏用：显示版本号，以及是否有可用更新（只读缓存，不发网络请求，
        避免每次翻页都去连 GitHub）。"""
        from . import updater
        cached = (updater._load_state().get("last_result") or {})
        has = bool(cached.get("has_update")) and not updater.is_skipped(cached.get("latest", ""))
        return jsonify({"current": updater.current_version(), "update_available": has,
                         "latest": cached.get("latest", "")})

    @app.route("/api/update/config", methods=["GET"])
    def api_update_config_get():
        from . import updater
        cfg = _upd_cfg()
        cached = (updater._load_state().get("last_result") or {})
        return jsonify({
            "current": updater.current_version(),
            "repo": cfg.get("repo") or (updater.detect_repo_slug() or ""),
            "branch": cfg.get("branch", "main"),
            "auto_check": cfg.get("auto_check", True),
            "last_check_ts": updater.last_check_ts(),
            "cached": cached or None,
        })

    @app.route("/api/update/config", methods=["POST"])
    def api_update_config_post():
        d = request.get_json(force=True) or {}
        config_store.save({"update": {
            "repo": (d.get("repo") or "").strip(),
            "branch": (d.get("branch") or "main").strip(),
            "auto_check": bool(d.get("auto_check", True)),
        }})
        return jsonify({"ok": True})

    @app.route("/api/update/check", methods=["POST"])
    def api_update_check():
        from . import updater
        d = request.get_json(force=True) or {}
        cfg = _upd_cfg()
        repo = (d.get("repo") or cfg.get("repo") or "").strip() or None
        branch = (d.get("branch") or cfg.get("branch") or "main").strip()
        info = updater.check_for_update(repo, branch).to_dict()
        info["last_check_ts"] = updater.last_check_ts()
        if info.get("has_update"):
            state.add_log(f"检查更新：发现新版本 {info.get('latest')}（当前 {info.get('current')}）")
        return jsonify(info)

    @app.route("/api/update/changelog")
    def api_update_changelog():
        from . import updater
        return jsonify({"changelog": updater.local_changelog()})

    @app.route("/api/update/skip", methods=["POST"])
    def api_update_skip():
        from . import updater
        v = (request.get_json(force=True) or {}).get("version", "")
        if v:
            updater.skip_version(v)
            state.add_log(f"已跳过版本 {v}")
        return jsonify({"ok": True})

    @app.route("/api/update/unskip", methods=["POST"])
    def api_update_unskip():
        from . import updater
        updater.unskip_all()
        return jsonify({"ok": True})

    @app.route("/api/update/perform", methods=["POST"])
    def api_update_perform():
        from . import updater
        # 两道闸：引擎在跑 / 还有持仓时不允许自动更新（详见 updater.perform_update 的说明）
        running = controller.is_running()
        try:
            has_pos = len(state.positions_view()) > 0
        except Exception:
            has_pos = False
        r = updater.perform_update(running, has_pos)
        state.add_log(("更新成功: " if r.get("ok") else "更新未执行: ") + str(r.get("message"))[:200],
                       "INFO" if r.get("ok") else "WARN")
        return jsonify(r)

    # ---------------------------------------------------------- 手动开单测试
    def _manual_exchange():
        """按当前模式返回可下单的交易所对象。
        模拟盘用 PaperExchange(不碰真钱)，实盘用 GateExchange。
        这里刻意每次都新建一个实例，和策略引擎完全隔离——手动测试不应该也不会
        影响正在运行的引擎状态。"""
        cfg = config_store.snapshot()
        creds = cred_store.load()
        if not creds.is_set:
            raise RuntimeError("请先在“设置”页填写并保存 API Key")
        from .exchange_gate import GateExchange
        settle = cfg.get("settle", "usdt")
        market = GateExchange(creds.api_key, creds.api_secret, settle=settle, host=creds.api_host)
        if cfg.get("mode", "paper") == "live":
            return market, "live"
        from .exchange_paper import PaperExchange
        sys_cfg = cfg.get("systematic", {})
        cost_cfg = cfg.get("costs", {})
        paper = PaperExchange(market,
                               initial_capital=sys_cfg.get("initial_capital_usdt", 10000.0),
                               slippage_bps=cost_cfg.get("slippage_bps", 2.0))
        return paper, "paper"

    def _manual_calc(ex, data):
        """把'名义价值'换算成张数，并返回预览需要的全部数字。"""
        symbol = (data.get("symbol") or "").strip().upper()
        side = data.get("side", "long")
        notional = float(data.get("notional") or 0)
        leverage = float(data.get("leverage") or 1)
        if not symbol:
            raise RuntimeError("请填写合约代码")
        if side not in ("long", "short"):
            raise RuntimeError("方向只能是 long / short")

        info = ex.get_entry_contract(symbol)
        mark = float(ex.get_ticker(symbol)["mark_price"])
        ticket = None
        if info.get("contract_type", "") in ("", "crypto"):
            from .position_sizing import entry_ticket
            if any(p["contract"] == symbol for p in ex.get_dual_positions()):
                raise RuntimeError("该合约已有持仓；固定保证金规则不重复追加额度")
            cfg = config_store.snapshot()
            costs_cfg = CostConfig.build(cfg.get("costs", {}))
            sys_cfg = SystematicConfig.build(cfg.get("systematic", {}))
            funds = ex.get_entry_budget()
            fee_rate = costs_cfg.effective_taker_rate(info.get("taker_fee_rate"), ex.get_account_taker_fee_rate(symbol))
            ticket = entry_ticket(symbol, funds["equity"], mark, info, ex.get_risk_limit_tiers(symbol),
                                  funds["available"], fee_rate,
                                  max(costs_cfg.slippage_bps, sys_cfg.max_entry_slippage_bps))
            notional, leverage = ticket.desired_notional, ticket.leverage
        if notional <= 0:
            raise RuntimeError("仓位价值必须大于0")
        qm = float(info["quanto_multiplier"])
        step = max(1, int(info.get("order_size_min", 1)))
        if mark <= 0 or qm <= 0:
            raise RuntimeError(f"{symbol} 行情或合约参数异常(标记价={mark}, 面值={qm})")

        raw_contracts = notional / (mark * qm)
        contracts = ticket.quantity if ticket else int(raw_contracts // step) * step
        warnings = []
        if contracts < step:
            raise RuntimeError(
                f"仓位价值太小：{notional} USDT 只能换算成 {raw_contracts:.4f} 张，"
                f"不足最小下单单位 {step} 张（每张约 {mark*qm:.4f} USDT），请调大仓位价值")
        actual_notional = contracts * mark * qm
        if abs(actual_notional - notional) / notional > 0.05:
            warnings.append(f"因为要取整到 {step} 张的倍数，实际名义价值 {actual_notional:.2f} "
                             f"和你填的 {notional:.2f} 相差超过5%")
        lev_min, lev_max = float(info["leverage_min"]), float(info["leverage_max"])
        if not (lev_min <= leverage <= lev_max):
            warnings.append(f"杠杆 {leverage}x 超出该合约允许范围 [{lev_min:.0f}, {lev_max:.0f}]，"
                             f"下单时会被自动夹到范围内")

        tp = data.get("tp")
        sl = data.get("sl")
        tp = float(tp) if tp not in (None, "") else None
        sl = float(sl) if sl not in (None, "") else None
        # 方向校验：多头止盈必须高于现价、止损低于现价；空头相反
        if tp is not None:
            if side == "long" and tp <= mark:
                warnings.append(f"做多的止盈价 {tp} 不高于现价 {mark}，会立刻触发")
            if side == "short" and tp >= mark:
                warnings.append(f"做空的止盈价 {tp} 不低于现价 {mark}，会立刻触发")
        if sl is not None:
            if side == "long" and sl >= mark:
                warnings.append(f"做多的止损价 {sl} 不低于现价 {mark}，会立刻触发")
            if side == "short" and sl <= mark:
                warnings.append(f"做空的止损价 {sl} 不高于现价 {mark}，会立刻触发")

        direction = 1 if side == "long" else -1
        sl_loss = abs(sl - mark) * contracts * qm if sl is not None else 0.0
        taker = fee_rate if ticket else float(info.get("taker_fee_rate") or 0.0005)
        return {
            "entry_ticket": ticket.to_dict() if ticket else None,
            "symbol": symbol, "side": side, "contracts": contracts,
            "mark_price": mark, "quanto_multiplier": qm,
            "base": symbol.split("_")[0],
            "requested_notional": notional, "actual_notional": actual_notional,
            "leverage": leverage, "margin": actual_notional / max(leverage, 1e-9),
            "est_fee": actual_notional * taker,
            "tp": tp, "sl": sl,
            "tp_pct": (round((tp - mark) / mark * 100 * direction, 2) if tp is not None else None),
            "sl_pct": (round((sl - mark) / mark * 100 * direction, 2) if sl is not None else None),
            "sl_loss": sl_loss, "warnings": warnings,
        }

    @app.route("/api/manual/preview", methods=["POST"])
    def manual_preview():
        try:
            ex, _ = _manual_exchange()
            calc = _manual_calc(ex, request.get_json(force=True) or {})
            calc["ok"] = True
            return jsonify(calc)
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})

    @app.route("/api/manual/order", methods=["POST"])
    def manual_order():
        steps = []
        try:
            ex, mode = _manual_exchange()
            data = request.get_json(force=True) or {}
            calc = _manual_calc(ex, data)
        except Exception as e:
            return jsonify({"ok": False, "message": str(e), "steps": []})

        symbol, side, contracts = calc["symbol"], calc["side"], calc["contracts"]

        r = ex.set_leverage_checked(symbol, calc["leverage"])
        steps.append({"name": "设为全仓并校验", "ok": r["ok"], "message": r["message"]})
        if r.get("margin_mode") != "cross" or r.get("verified") is not True or r.get("cross_leverage_limit") != calc["leverage"]:
            state.add_log(f"[手动测试] {symbol} 未确认全仓及计划杠杆，已拒绝开仓", "ERROR")
            return jsonify({"ok": False, "steps": steps,
                             "message": "未回读确认全仓及计划杠杆，已中止下单"})

        r = ex.open_market(symbol, side, contracts, text="t-manual")
        steps.append({"name": f"市价开仓 {contracts}张", "ok": r["ok"], "message": r["message"]})
        if not r["ok"]:
            state.add_log(f"[手动测试] {symbol} 开仓失败: {r['message']}", "ERROR")
            return jsonify({"ok": False, "message": "开仓未成功，后续止盈止损已跳过", "steps": steps})

        for kind, price in (("tp", calc["tp"]), ("sl", calc["sl"])):
            if price is None:
                continue
            rr = ex.create_tp_sl(symbol, side, price, kind)
            steps.append({"name": ("挂止盈单" if kind == "tp" else "挂止损单"),
                           "ok": rr["ok"], "message": rr["message"]})

        ok = all(s["ok"] for s in steps)
        state.add_log(f"[手动测试·{mode}] {symbol} {side} {contracts}张 "
                       f"名义{calc['actual_notional']:.2f}U 杠杆{calc['leverage']:.0f}x "
                       f"-> {'全部成功' if ok else '部分失败'}")
        return jsonify({"ok": ok, "steps": steps,
                         "message": f"{symbol} {side} {contracts}张（名义 {calc['actual_notional']:.2f} USDT，"
                                     f"占用保证金约 {calc['margin']:.2f} USDT）"})

    @app.route("/api/manual/positions")
    def manual_positions():
        try:
            ex, _ = _manual_exchange()
            return jsonify({"ok": True, "positions": ex.get_dual_positions()})
        except Exception as e:
            return jsonify({"ok": False, "message": str(e), "positions": []})

    @app.route("/api/manual/close", methods=["POST"])
    def manual_close():
        try:
            ex, _ = _manual_exchange()
            data = request.get_json(force=True) or {}
            symbol = (data.get("symbol") or "").strip().upper()
            side = data.get("side", "long")
            r = ex.close_dual(symbol, side)
            state.add_log(f"[手动测试] 平仓 {symbol}[{side}]")
            return jsonify({"ok": True, "message": f"{symbol} {side} 平仓请求已提交：{r}"})
        except Exception as e:
            return jsonify({"ok": False, "message": f"平仓失败: {e}"})

    @app.route("/api/state")
    def api_state():
        config_snapshot = config_store.snapshot()
        sizing_mode = SystematicConfig.build(config_snapshot.get("systematic", {})).position_sizing_mode
        risk_cfg = RiskConfig.build(config_snapshot.get("risk", {}))
        with state.with_lock():
            signals = [{"symbol": k, **v} for k, v in state.last_signals.items()]
            logs = list(state.logs[-150:])
            portfolio = dict(state.portfolio_snapshot)
            portfolio["position_sizing_mode"] = sizing_mode
            portfolio["actual_gross_leverage"] = (sum(abs(p.size * p.mark_price * p.quanto_multiplier)
                for p in state.positions.values()) / state.equity if state.equity > 0 else 0.0)
            payload = {
                "summary": state.summary(),
                "positions": state.positions_view(),
                "signals": signals,
                "trades": state.recent_trades_view(40),
                "logs": logs,
                "daily_loss_limit_enabled": risk_cfg.daily_loss_limit_enabled,
                "circuit_breaker": risk_cfg.daily_loss_limit_enabled and state.circuit_breaker_active,
                "portfolio": portfolio,
            }
        return jsonify(payload)

    def _position_action(handler_name: str, ok_msg: str):
        """/api/positions/* 两个动作的公共部分：校验参数、确认这笔仓位确实存在、
        再把动作转交给正在运行的引擎实例。都是"改变程序会不会动用户仓位"的操作，
        必须显式校验，不能拿着前端传来的字符串直接执行。"""
        data = request.get_json(force=True) or {}
        symbol = (data.get("symbol") or "").strip().upper()
        side = (data.get("side") or "").strip().lower()
        if not symbol or side not in ("long", "short"):
            return jsonify({"ok": False, "message": "参数不完整：需要 symbol 和 side(long/short)"})
        engine = getattr(controller, "engine", None)
        if not controller.is_running() or engine is None:
            return jsonify({"ok": False, "message": "引擎未运行，请先启动引擎再执行该操作"})
        if not state.get_position(symbol, side):
            return jsonify({"ok": False, "message": f"未找到 {symbol} 的{side}仓，请刷新后重试"})
        try:
            getattr(engine, handler_name)(symbol, side)
        except Exception as exc:
            state.add_log(f"{symbol}[{side}] 持仓操作失败：{exc}", "ERROR")
            return jsonify({"ok": False, "message": f"持仓操作未完成：{exc}，请刷新后重试"}), 409
        return jsonify({"ok": True, "message": ok_msg.format(symbol=symbol,
                                                             side="多" if side == "long" else "空")})

    @app.route("/api/positions/adopt", methods=["POST"])
    def api_positions_adopt():
        return _position_action(
            "adopt_external", "{symbol} {side}仓已纳入策略管理，下一轮开始按策略目标调整")

    @app.route("/api/positions/confirm-close", methods=["POST"])
    def api_positions_confirm_close():
        return _position_action(
            "request_close", "{symbol} {side}仓已排入平仓队列，下一轮执行")

    @app.route("/api/universe", methods=["GET"])
    def universe_status():
        return jsonify(universe.status())

    @app.route("/api/universe/scan", methods=["POST"])
    def universe_scan():
        cfg = config_store.snapshot()
        result = universe.start(SystematicConfig.build(cfg.get("systematic", {})),
                                CostConfig.build(cfg.get("costs", {})),
                                force=bool((request.get_json(silent=True) or {}).get("force")))
        return jsonify(result)

    @app.route("/api/universe/catalogue", methods=["GET"])
    def universe_catalogue():
        try:
            return jsonify({"ok": True, "contracts": [
                {"symbol": c["name"], "crypto": is_crypto(c)}
                for c in universe.catalogue() if tradable_contract(c)]})
        except Exception:
            return jsonify({"ok": False, "message": "公共合约目录获取失败，请稍后重试"}), 503

    @app.route("/api/universe/apply", methods=["POST"])
    def universe_apply():
        data = request.get_json(silent=True) or {}
        # Altering a running live pool has immediate order consequences. Queue no
        # implicit trade: the operator can stop, review the pool, then start it.
        if controller.is_running():
            return jsonify({"ok": False, "message": "请先停止引擎，再更新候选交易池"}), 409
        try:
            cfg = config_store.snapshot()
            symbols = universe.selection(data.get("scan_id"),
                SystematicConfig.build(cfg.get("systematic", {})), CostConfig.build(cfg.get("costs", {})))
            config_store.add_symbols(symbols)
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception:
            return jsonify({"ok": False, "message": "候选校验或保存失败，请重新筛选"}), 503
        state.add_log("加入候选交易池: " + ", ".join(symbols))
        return jsonify({"ok": True, "symbols": config_store.snapshot()["symbols"]})

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        cfg = config_store.snapshot()
        cfg["systematic"] = asdict(SystematicConfig.build(cfg.get("systematic", {})))
        cfg["_creds"] = cred_store.load().masked()
        return jsonify(cfg)

    @app.route("/api/config", methods=["POST"])
    def api_config_post():
        patch = request.get_json(force=True) or {}
        cfg = config_store.save(patch)
        state.add_log(f"设置已更新: {list(patch.keys())}")
        return jsonify({"ok": True, "config": cfg})

    @app.route("/api/symbols", methods=["POST"])
    def add_symbol():
        data = request.get_json(force=True) or {}
        symbol = (data.get("symbol") or "").strip().upper()
        try:
            universe.validate_symbol(symbol)
            config_store.add_symbol(symbol)
        except ValueError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400
        except Exception:
            return jsonify({"ok": False, "message": "公共合约目录验证失败，请稍后重试"}), 503
        state.add_log(f"添加交易标的: {symbol}")
        return jsonify({"ok": True})

    @app.route("/api/symbols", methods=["DELETE"])
    def remove_symbol():
        data = request.get_json(force=True) or {}
        symbol = (data.get("symbol") or "").strip().upper()
        if symbol:
            config_store.remove_symbol(symbol)
            state.add_log(f"移除交易标的: {symbol}")
        return jsonify({"ok": True})

    @app.route("/api/credentials", methods=["POST"])
    def save_credentials():
        data = request.get_json(force=True) or {}
        api_key = data.get("api_key", "")
        api_secret = data.get("api_secret", "")
        api_host = data.get("api_host") or "https://api.gateio.ws/api/v4"
        # 如果用户没有改 secret（前端留空表示不修改），保留原有值
        existing = cred_store.load()
        if not api_key:
            api_key = existing.api_key
        if not api_secret:
            api_secret = existing.api_secret
        creds = cred_store.save(api_key, api_secret, api_host)
        state.add_log("API Key 已通过网页更新")
        return jsonify({"ok": True, "masked": creds.masked()})

    @app.route("/api/credentials/test", methods=["POST"])
    def test_credentials():
        creds = cred_store.load()
        if not creds.is_set:
            return jsonify({"ok": False, "message": "尚未填写 API Key/Secret"})
        try:
            from .exchange_gate import GateExchange
            settle = config_store.snapshot().get("settle", "usdt")
            ex = GateExchange(creds.api_key, creds.api_secret, settle=settle, host=creds.api_host)
            d = ex.get_account_detail()
            cur = d["currency"]
            msg = (f"连接成功 · {d['margin_mode_text']} · 权益 {d['equity']:.2f} {cur}"
                    f"（可用 {d['available']:.2f}／仓位保证金 {d['position_margin']:.2f}"
                    f"／浮动盈亏 {d['unrealised_pnl']:+.2f}）")
            if d["equity"] <= 0:
                # 权益为0时光报一个数字没用，直接把最可能的原因和排查顺序给出来
                hints = [
                    f"合约账户（{settle.upper()} 本位）里没有资金。",
                    "最常见原因：钱还在**现货/理财账户**里没划转过来 —— "
                    "Gate 的现货和合约是两个独立钱包，需要在官网「资产 → 划转」把 USDT "
                    "从现货划到「USDT 合约」账户。",
                ]
                if d["margin_mode"] not in (0, None):
                    hints.append(f"另外你的账户是「{d['margin_mode_text']}」模式，资金可能记在统一账户下，"
                                  f"当前读到 cross_margin_balance={d['cross_margin_balance']:.2f}。")
                hints.append(f"也请确认结算币种设置正确：当前配置 settle={settle}，"
                              f"如果你用的是币本位合约需要改成对应币种。")
                return jsonify({"ok": True, "warn": True,
                                 "message": msg + "\n\n⚠️ " + "\n⚠️ ".join(hints),
                                 "detail": d})
            return jsonify({"ok": True, "message": msg, "detail": d})
        except Exception as e:
            return jsonify({"ok": False, "message": f"连接失败: {_friendly_api_error(e)}"})

    @app.route("/api/engine/start", methods=["POST"])
    def engine_start():
        ok, msg = controller.start()
        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/engine/stop", methods=["POST"])
    def engine_stop():
        ok, msg = controller.stop()
        return jsonify({"ok": ok, "message": msg})

    @app.route("/api/engine/status")
    def engine_status():
        return jsonify(controller.status())

    # ---------------------------------------------------------- 网页回测（单币；旧组合结果仍可查看）
    @app.route("/api/backtest/start", methods=["POST"])
    def backtest_start():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "message": "请提交一个回测币种"}), 400
        symbols = data.get("symbols") if "symbols" in data else [data.get("symbol")]
        if not isinstance(symbols, list) or len(symbols) != 1 or not isinstance(symbols[0], str):
            return jsonify({"ok": False, "message": "每次只能回测一个币种，请搜索并选择一个合约"}), 400
        symbol = symbols[0].strip().upper().replace("/", "_").replace("-", "_")
        if not symbol.endswith("_USDT"):
            symbol = (symbol[:-4] if symbol.endswith("USDT") else symbol) + "_USDT"
        if not CONTRACT_SYMBOL.fullmatch(symbol):
            return jsonify({"ok": False, "message": "请输入一个有效的 USDT 合约，例如 BTC 或 SOL_USDT"}), 400
        symbols = [symbol]
        days_back = data.get("days_back", 90)
        initial_capital = data.get("initial_capital")
        try:
            days_back = float(days_back)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "message": "回测天数格式不正确"})
        try:
            job = backtest_controller.start_job(
                symbols, days_back, initial_capital,
                walkforward=bool(data.get("walkforward", False)),
                wf_folds=int(data.get("wf_folds", 5) or 5))
        except Exception as e:
            return jsonify({"ok": False, "message": str(e)})
        state.add_log(f"发起单币回测任务: {', '.join(job.symbols)} 最近{job.days_back}天"
                       + ("（含滚动样本外验证）" if job.walkforward else "") + f" (job={job.id})")
        return jsonify({"ok": True, "job_id": job.id})

    @app.route("/api/backtest/list")
    def backtest_list():
        return jsonify({"jobs": backtest_controller.list_jobs()})

    @app.route("/api/backtest/job/<job_id>")
    def backtest_job_detail(job_id):
        job = backtest_controller.get_job(job_id)
        if job is None:
            return jsonify({"ok": False, "message": "任务不存在"}), 404
        return jsonify(job.to_full())

    @app.route("/api/backtest/job/<job_id>", methods=["DELETE"])
    def backtest_job_delete(job_id):
        ok = backtest_controller.delete_job(job_id)
        return jsonify({"ok": ok})

    # ---------------------------------------------------------- K线图数据（供 /charts 页面用）
    @app.route("/api/klines")
    def api_klines():
        """实时/模拟盘图表用：只读行情，按需下载(经本地缓存)最近N根K线。"""
        symbol = (request.args.get("symbol") or "").strip().upper()
        interval = request.args.get("interval", "1h")
        limit = request.args.get("limit", 300, type=int)
        if not symbol:
            return jsonify({"ok": False, "message": "缺少symbol参数"})
        creds = cred_store.load()
        if not creds.is_set:
            return jsonify({"ok": False, "message": "请先在设置页填写并保存 API Key"})
        try:
            from . import data_fetcher
            from .exchange_gate import GateExchange
            settle = config_store.snapshot().get("settle", "usdt")
            exchange = GateExchange(creds.api_key, creds.api_secret, settle=settle, host=creds.api_host)
            interval_sec = data_fetcher.INTERVAL_SECONDS.get(interval, 3600)
            days_back = max(limit * interval_sec / 86400.0 * 1.15, 1.0)
            df = data_fetcher.fetch_candles(exchange, symbol, interval, days_back,
                                             cache_dir=controller.kline_cache_dir)
            df = df.tail(max(limit, 1))
            candles = [
                {"t": float(row.timestamp), "o": float(row.open), "h": float(row.high),
                 "l": float(row.low), "c": float(row.close), "v": float(row.volume)}
                for row in df.itertuples()
            ]
            return jsonify({"ok": True, "candles": candles})
        except Exception as e:
            return jsonify({"ok": False, "message": f"获取K线失败: {e}"})

    @app.route("/api/backtest/job/<job_id>/chart")
    def backtest_chart(job_id):
        from .backtest_reporting import chart_payload
        from . import data_fetcher
        job = backtest_controller.get_job(job_id)
        if job is None or job.result is None:
            return jsonify({"ok": False, "message": "回测任务不存在或尚未完成"}), 404
        symbol = (request.args.get("symbol") or "").strip().upper()
        interval = request.args.get("interval", "1h")
        if symbol not in job.symbols:
            return jsonify({"ok": False, "message": "标的不属于该回测任务"}), 400
        if interval not in data_fetcher.INTERVAL_SECONDS:
            return jsonify({"ok": False, "message": "不支持的周期"}), 400
        try:
            cached = None
            if symbol not in job.result.get("chart_candles", {}):
                seconds = data_fetcher.INTERVAL_SECONDS[interval]
                df = data_fetcher.read_cached_candles(backtest_controller.cache_dir, symbol, interval,
                    job.result.get("start_ts", 0)-seconds, job.result.get("end_ts"))
                cached = [{"t": float(r.timestamp), "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)} for r in df.itertuples()]
            return jsonify(chart_payload(job.result, symbol, interval, cached))
        except (ValueError, TypeError, KeyError) as e:
            return jsonify({"ok": False, "message": str(e)}), 400

    @app.route("/api/klines/cache")
    def api_klines_cache():
        """回测图表用：只读本地缓存(该回测任务下载数据时已经缓存过)，不发起任何网络请求。"""
        symbol = (request.args.get("symbol") or "").strip().upper()
        interval = request.args.get("interval", "1h")
        start_ts = request.args.get("start_ts", type=float)
        end_ts = request.args.get("end_ts", type=float)
        if not symbol:
            return jsonify({"ok": False, "message": "缺少symbol参数"})
        try:
            from . import data_fetcher
            df = data_fetcher.read_cached_candles(backtest_controller.cache_dir, symbol, interval,
                                                    start_ts, end_ts)
            candles = [
                {"t": float(row.timestamp), "o": float(row.open), "h": float(row.high),
                 "l": float(row.low), "c": float(row.close), "v": float(row.volume)}
                for row in df.itertuples()
            ]
            if not candles:
                return jsonify({"ok": False, "message": f"本地没有 {symbol} {interval} 的缓存K线"})
            return jsonify({"ok": True, "candles": candles})
        except Exception as e:
            return jsonify({"ok": False, "message": f"读取K线缓存失败: {e}"})

    return app


def run_web_dashboard(state: StateStore, config_store: ConfigStore, cred_store: CredentialStore,
                       controller: EngineController, backtest_controller: BacktestController,
                       host: str = "127.0.0.1", port: int = 8765):
    app = create_app(state, config_store, cred_store, controller, backtest_controller)
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
