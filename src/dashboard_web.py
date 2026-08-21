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

from flask import Flask, jsonify, render_template_string, request

from .backtest_runner import BacktestController
from .config import ConfigStore
from .credentials import CredentialStore
from .engine import EngineController
from .state import StateStore

logger = logging.getLogger("bot.web")


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


PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>Gate.io 量化策略控制台</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#c9d1d9; --muted:#8b949e;
          --accent:#58a6ff; --pos:#3fb950; --neg:#f85149; --warn:#e3b341; }
  * { box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',Arial,sans-serif; margin:0; }
  header { display:flex; align-items:center; justify-content:space-between; padding:14px 24px;
           border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--bg); z-index:10; }
  header h1 { font-size:18px; margin:0; color:var(--accent); }
  nav { display:flex; gap:6px; }
  nav button { background:transparent; border:1px solid var(--border); color:var(--text); padding:8px 18px;
               border-radius:6px; cursor:pointer; font-size:14px; }
  nav button.active { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:600; }
  main { padding:20px 24px; max-width:1300px; margin:0 auto; }
  .tabpage { display:none; } .tabpage.active { display:block; }
  .grid { display:grid; grid-template-columns: repeat(4,1fr); gap:10px; margin-bottom:16px; }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:12px 16px; }
  .card .label { font-size:12px; color:var(--muted); }
  .card .value { font-size:20px; font-weight:600; margin-top:4px; }
  .pos { color:var(--pos); } .neg { color:var(--neg); }
  table { width:100%; border-collapse:collapse; margin-bottom:20px; font-size:13px; }
  th,td { border-bottom:1px solid #21262d; padding:6px 8px; text-align:left; }
  th { color:var(--muted); font-weight:500; }
  section { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px 18px; margin-bottom:16px; }
  section h3 { margin-top:0; font-size:15px; color:var(--accent); }
  .badge { padding:2px 10px; border-radius:10px; font-size:12px; font-weight:600; }
  .badge.paper { background:#4b3b00; color:var(--warn); }
  .badge.live { background:#4a0d0d; color:var(--neg); }
  .badge.on { background:#0d3b1f; color:var(--pos); }
  .badge.off { background:#3a3a3a; color:var(--muted); }
  .badge.pending, .badge.fetching, .badge.running { background:#0d2b3b; color:var(--accent); }
  .badge.done { background:#0d3b1f; color:var(--pos); }
  .badge.error { background:#3a0d0d; color:var(--neg); }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:12px; }
  input,select,button.btn { background:#0d1117; color:var(--text); border:1px solid var(--border);
        border-radius:6px; padding:8px 12px; font-size:14px; }
  input[type=number] { width:110px; }
  input[type=text], input[type=password] { min-width:220px; }
  button.btn { cursor:pointer; } button.btn:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:700; }
  button.danger { background:#3a0d0d; color:var(--neg); border-color:#5c1a1a; font-weight:700; }
  button.success { background:#0d3b1f; color:var(--pos); border-color:#1a5c30; font-weight:700; }
  .field { display:flex; flex-direction:column; gap:4px; }
  .field label { font-size:12px; color:var(--muted); }
  .presetbar button { margin-right:8px; }
  .presetbar button.selected { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); }
  .hint { font-size:12px; color:var(--muted); margin-top:6px; line-height:1.6; }
  .chip { display:inline-block; background:#21262d; border:1px solid var(--border); border-radius:14px;
          padding:3px 10px; margin:2px; font-size:12px; }
  .chip button { background:none; border:none; color:var(--neg); cursor:pointer; margin-left:6px; font-weight:700; }
  #logs { white-space:pre-wrap; font-family:monospace; font-size:12px; max-height:260px; overflow-y:auto; }
  .toast { position:fixed; bottom:20px; right:20px; background:var(--panel); border:1px solid var(--border);
           padding:12px 18px; border-radius:8px; max-width:420px; z-index:100; }
  .toast.err { border-color:var(--neg); color:var(--neg); }
  .toast.ok { border-color:var(--pos); color:var(--pos); }
  .subgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:10px; }
  details summary { cursor:pointer; color:var(--accent); margin:10px 0; }
  .warnbox { background:#3a2400; border:1px solid var(--warn); color:var(--warn); padding:10px 14px;
             border-radius:8px; margin-bottom:14px; font-size:13px; line-height:1.6; }
  .joblist { display:flex; flex-direction:column; gap:6px; }
  .jobrow { display:flex; align-items:center; gap:10px; padding:8px 10px; border:1px solid var(--border);
            border-radius:6px; cursor:pointer; font-size:13px; }
  .jobrow:hover { border-color:var(--accent); }
  .jobrow.selected { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); }
  .jobrow .sym { font-weight:600; min-width:160px; }
  .jobrow .meta { color:var(--muted); flex:1; }
  .progressbar { background:#21262d; border-radius:6px; height:6px; width:100%; overflow:hidden; margin-top:4px; }
  .progressbar > div { background:var(--accent); height:100%; }
  #btEquityCanvas { width:100%; height:220px; display:block; }
  .symcheckbox { margin-right:16px; font-size:13px; }
</style>
</head>
<body>
<header>
  <h1>⚙️ Gate.io 多资产 Trend+Carry+波动率目标 控制台 <span id="mode-badge" class="badge"></span> <span id="engine-badge" class="badge"></span> <span id="invert-badge" class="badge live" style="display:none;">⚠️ 反向执行已开启</span>
  <span class="ver" id="app-version" style="font-size:11px;color:var(--muted);font-weight:400;"></span>
  <span class="badge" id="upd-badge" style="display:none;background:#a371f7;color:#0d1117;cursor:pointer;"
        onclick="location.href='/update'">有新版本</span></h1>
  <nav>
    <button id="nav-dashboard" onclick="showTab('dashboard')">仪表盘</button>
    <button id="nav-backtest" onclick="showTab('backtest')">回测</button>
    <button id="nav-settings" onclick="showTab('settings')">设置</button>
    <button onclick="window.location.href='/charts'">📈 K线图</button>
    <button onclick="window.location.href='/manual'">🧪 手动开单</button>
    <button onclick="window.location.href='/update'">⬆️ 检查更新</button>
  </nav>
</header>

<main>

<div id="tab-dashboard" class="tabpage">
  <div class="row">
    <button class="btn success" onclick="engineAction('start')">▶ 启动引擎</button>
    <button class="btn danger" onclick="engineAction('stop')">■ 停止引擎</button>
    <span id="engine-msg" class="hint"></span>
  </div>
  <div class="grid" id="summary-grid"></div>

  <section><h3>组合层概览</h3><div class="grid" id="portfolio-grid"></div></section>

  <section><h3>当前持仓</h3><table id="positions"><thead><tr>
    <th>币种</th><th>方向</th><th>张数</th><th>开仓价</th><th>现价</th>
    <th>浮动盈亏</th><th>持仓时长</th></tr></thead><tbody></tbody></table></section>

  <section><h3>标的信号（趋势 / Carry / 合成预测）</h3><table id="signals"><thead><tr>
    <th>币种</th><th>方向</th><th>信号强度</th><th>合成预测(F)</th><th>明细</th></tr></thead><tbody></tbody></table></section>

  <section><h3>最近成交</h3><table id="trades"><thead><tr>
    <th>币种</th><th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>手续费</th><th>资金费</th><th>持仓时长</th><th>离场原因</th></tr></thead><tbody></tbody></table></section>

  <section><h3>运行日志</h3><div id="logs"></div></section>
</div>

<div id="tab-backtest" class="tabpage">
  <div class="warnbox">
    回测和实盘/模拟盘完全独立运行，可以放心地在实盘正在跑的同时随时发起回测，不会互相影响。
    这是"组合级"回测：一次任务对你选的整组标的同时跑，直接复用当前"设置"页保存的策略参数，
    得到的是组合层面的权益曲线（不是逐个标的分开测）。下载历史K线需要用到已保存的 API Key（只读查询，不会下单）。
    第一次测某个标的会下载较多历史数据，之后再测同一标的会命中本地缓存，速度快很多。
  </div>
  <section>
    <h3>发起新回测</h3>
    <div class="row">
      <div class="field" style="flex:1; min-width:280px;">
        <label>参与回测的标的（默认=当前配置的全部标的，可取消勾选）</label>
        <div id="bt-symbol-checks"></div>
      </div>
    </div>
    <div class="row">
      <div class="field"><label>额外标的（逗号分隔，不在上面列表里也可以临时测）</label>
        <input id="bt-symbol-extra" placeholder="如 DOGE_USDT, LTC_USDT" style="min-width:240px;"></div>
      <div class="field"><label>回测天数</label><input id="bt-days" type="number" min="1" value="90" style="width:100px;"></div>
      <div class="field"><label>初始资金(USDT，留空=用当前策略参数里的值)</label><input id="bt-capital" type="number" min="0" placeholder="默认" style="width:180px;"></div>
    </div>
    <div class="row">
      <label class="hint"><input type="checkbox" id="bt-walkforward"> 同时做「滚动样本外验证」（把窗口切成多折分别统计，看表现是否稳定，会明显增加耗时）</label>
      <div class="field"><label>折数</label><input id="bt-wf-folds" type="number" min="2" max="10" value="5" style="width:70px;"></div>
    </div>
    <div class="row presetbar" id="bt-preset-bar">
      <button class="btn" onclick="setBtDays(30)">近30天</button>
      <button class="btn" onclick="setBtDays(90)">近90天</button>
      <button class="btn" onclick="setBtDays(180)">近180天</button>
      <button class="btn" onclick="setBtDays(365)">近1年</button>
    </div>
    <div class="row">
      <button class="btn primary" onclick="startBacktest()">▶ 开始回测</button>
      <span id="bt-start-msg" class="hint"></span>
    </div>
  </section>

  <section>
    <h3>回测任务</h3>
    <div class="joblist" id="bt-joblist"></div>
  </section>

  <section id="bt-detail-section" style="display:none;">
    <h3>回测结果（组合层面）</h3>
    <div id="bt-warnings"></div>
    <div class="grid" id="bt-summary-grid"></div>
    <canvas id="btEquityCanvas"></canvas>
    <div class="hint" style="margin:8px 0 16px;">权益曲线（横轴=时间，纵轴=组合账户权益 USDT）</div>

    <div id="bt-costs"></div>
    <div id="bt-diagnosis"></div>
    <div id="bt-walkforward-box"></div>

    <h3 style="font-size:14px; color:var(--accent);">分标的贡献</h3>
    <table id="bt-per-symbol"><thead><tr>
      <th>标的</th><th>交易数</th><th>净盈亏</th><th>手续费</th><th>资金费</th>
      <th>最新趋势预测</th><th>最新Carry预测</th><th>自适应风险</th></tr></thead><tbody></tbody></table>

    <h3 style="font-size:14px; color:var(--accent);">逐笔成交</h3>
    <table id="bt-trades"><thead><tr>
      <th>标的</th><th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>手续费</th><th>资金费</th>
      <th>持仓时长</th><th>原因</th></tr></thead><tbody></tbody></table>
  </section>
</div>

<div id="tab-settings" class="tabpage">

  <section>
    <h3>① Gate.io API Key</h3>
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
    <h3>② 运行模式</h3>
    <div class="row presetbar" id="mode-bar">
      <button class="btn" data-mode="paper" onclick="setMode('paper')">模拟盘 PAPER（推荐先用这个）</button>
      <button class="btn" data-mode="live" onclick="setMode('live')">实盘 LIVE（真实资金，请谨慎）</button>
    </div>
    <div class="hint">切换到实盘前请务必确认已用模拟盘验证过策略表现，且账户内没有其它未平仓位（双向持仓模式切换要求无持仓）。</div>
  </section>

  <section>
    <h3>③ 交易标的（含黄金 XAU_USDT）</h3>
    <div class="row">
      <input id="symbol-input" placeholder="输入合约代码，如 SOL_USDT / XAU_USDT" size="24">
      <button class="btn primary" onclick="addSymbol()">添加</button>
    </div>
    <div id="symbols-chips"></div>
  </section>

  <section>
    <h3>④ 策略核心参数</h3>
    <div class="hint">趋势/Carry信号权重、组合目标年化波动率、杠杆与敞口约束、调仓缓冲区——这些是最常调的参数。</div>
    <div class="subgrid" id="sys-core-fields" style="margin-top:10px;"></div>
    <div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveSysCore()">保存策略核心参数</button></div>
  </section>

  <section>
    <h3>⑤ ⚠️ 反向执行（人工干预开关，谨慎使用）</h3>
    <div class="warnbox">
      开启后：预测计算、波动率归一化、组合风险分配、杠杆/敞口约束、反手确认防抖——全部照常按原逻辑计算，
      <b>只在最后真正下单这一步，把方向对调</b>：算出来该开多，实际执行开空；算出来该开空，实际执行开多。
      这不代表模型认为反过来更对，纯粹是人工干预开关。<b>务必先在"回测"页用相同标的池验证过"反向执行"确实
      表现更好，再考虑在模拟盘/实盘打开它</b>，否则很可能只是把亏损方向从"做多"换成"做空"而已。
      仪表盘和K线图页面在此模式开启时都会有醒目提示，运行日志里每次调仓也会标注"计算方向"和"实际执行方向"。
    </div>
    <div id="invert-direction-field"></div>
    <div class="row" style="margin-top:12px;"><button class="btn danger" onclick="saveInvertDirection()">保存反向执行开关</button></div>
  </section>

  <section>
    <h3>⑥ 大周期 Regime 过滤（1D）</h3>
    <div class="hint">日线EMA+ADX判定趋势/震荡市场状态，用来给趋势预测做门控：逆势时衰减，震荡市整体衰减。</div>
    <div class="subgrid" id="sys-regime-fields" style="margin-top:10px;"></div>
    <div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveSysRegime()">保存Regime参数</button></div>
  </section>

  <details>
    <summary>高级参数：EWMAC/协方差/执行节奏 / 成本模型（一般无需修改）</summary>
    <section>
      <h3>EWMAC / 协方差 / 执行节奏</h3>
      <div class="subgrid" id="sys-adv-fields"></div>
      <div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveSysAdv()">保存高级参数</button></div>
    </section>
    <section>
      <h3>成本模型参数</h3>
      <div class="subgrid" id="costs-fields"></div>
      <div class="row" style="margin-top:12px;"><button class="btn primary" onclick="saveCosts()">保存成本参数</button></div>
    </section>
  </details>

</div>

</main>
<div id="toast" class="toast" style="display:none;"></div>

<script>
let ACTIVE_TAB = 'dashboard';
let CUR_MODE = 'paper';
let CUR_CONFIG = {};
let BT_VIEW_JOB_ID = null;

const SYS_CORE_LABELS = {
  initial_capital_usdt: "模拟盘/回测初始资金(USDT)",
  trend_weight: "趋势信号权重", carry_weight: "Carry信号权重",
  short_trend_weight: "短趋势(1H)权重", main_trend_weight: "主趋势(4H)权重",
  target_annual_vol_pct: "组合目标年化波动率(%)", max_leverage: "组合总杠杆上限(倍)",
  max_instrument_exposure_pct: "单标的敞口上限(%权益)", max_correlated_group_exposure_pct: "相关分组敞口上限(%权益)",
  no_trade_buffer_pct: "调仓缓冲区(%，越大换手越少)",
  exit_buffer_multiplier: "减仓/平仓缓冲区倍数(越大越能让趋势走满，减仓更迟钝)",
};
const SYS_REGIME_LABELS = {
  regime_ema_fast: "Regime快线EMA周期", regime_ema_slow: "Regime慢线EMA周期", regime_ema_long: "Regime趋势EMA周期",
  regime_adx_period: "Regime ADX周期", regime_adx_trend_threshold: "Regime ADX趋势阈值",
  regime_oppose_dampen: "逆势衰减系数(0-1)", regime_range_dampen: "震荡市衰减系数(0-1)",
};
const SYS_ADV_LABELS = {
  ewma_lambda: "EWMA衰减因子λ(波动率/协方差)", forecast_scale_lookback: "预测缩放回看窗口(根K线)",
  forecast_scale_min_periods: "预测缩放最小样本数", fdm_max: "分散化乘数(FDM)上限",
  fdm_lookback: "FDM回看窗口(根K线)", fdm_min_periods: "FDM最小样本数",
  carry_scale_lookback: "Carry缩放回看窗口(根K线)", min_bars_short: "短趋势最少K线数(不足则跳过该标的)",
  min_bars_main: "主趋势最少K线数", min_bars_regime: "Regime最少K线数",
  tick_interval_sec: "主循环复核间隔(秒，默认900=15分钟)",
  short_trend_interval: "短趋势周期", main_trend_interval: "主趋势周期",
  regime_interval: "Regime周期", covariance_interval: "组合协方差周期",
  adaptive_risk_enabled: "启用高波动震荡自适应缩仓",
  adaptive_er_lookback: "方向效率ER回看(1H根数)", adaptive_er_full_risk: "保留完整风险的ER门槛",
  adaptive_vol_fast_lambda: "影线波动快EWMA λ", adaptive_vol_slow_lambda: "影线波动慢EWMA λ",
  adaptive_vol_ratio_start: "快/慢波动比缩仓起点", adaptive_vol_ratio_full: "快/慢波动比完整压力点",
  adaptive_max_risk_reduction: "最大风险削减比例(0.65=65%)",
  adaptive_multiplier_smoothing_span: "风险乘数平滑跨度(1H根数)",
  adaptive_fast_reduce_threshold: "已有持仓极端风险快速减仓门槛",
  depth_guard_enabled: "启用开/加仓盘口保护", depth_levels: "盘口估算档数",
  max_entry_spread_bps: "开/加仓最大点差(bps)", max_entry_slippage_bps: "开/加仓最大预估冲击(bps)",
  min_depth_fill_ratio: "盘口最小覆盖率(1=完整覆盖)",
};
const SYS_ADV_TYPES = {
  short_trend_interval: 'text', main_trend_interval: 'text',
  regime_interval: 'text', covariance_interval: 'text',
  adaptive_risk_enabled: 'bool', depth_guard_enabled: 'bool',
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
  ACTIVE_TAB = name;
  ['dashboard','backtest','settings'].forEach(n => {
    document.getElementById('tab-'+n).classList.toggle('active', name===n);
    document.getElementById('nav-'+n).classList.toggle('active', name===n);
  });
}

function toast(msg, ok){
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'toast ' + (ok ? 'ok':'err');
  el.style.display = 'block';
  setTimeout(()=>{ el.style.display='none'; }, 4500);
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
async function saveInvertDirection(){
  const fields = readFields('invert-direction-field');
  if(fields.invert_direction){
    if(!confirm('确定要开启"反向执行"吗？开启后所有标的的实际下单方向都会和策略计算结果相反。\\n\\n请确认你已经在"回测"页用相同参数验证过这样确实表现更好，否则不建议开启。')) return;
  }
  const patch = { systematic: fields };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false){
    toast(fields.invert_direction ? '⚠️ 反向执行已开启' : '反向执行已关闭', true);
    updateInvertBadge(fields.invert_direction);
  }
}
function updateInvertBadge(on){
  const el = document.getElementById('invert-badge');
  if(!el) return;
  el.style.display = on ? 'inline-block' : 'none';
}
async function saveSysRegime(){
  const patch = { systematic: readFields('sys-regime-fields') };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false) toast('Regime参数已保存', true);
}
async function saveSysAdv(){
  const patch = { systematic: readFields('sys-adv-fields') };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false) toast('高级参数已保存', true);
}
async function saveCosts(){
  const patch = { costs: readFields('costs-fields') };
  const r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if(r.ok !== false) toast('成本参数已保存', true);
}

async function addSymbol(){
  const v = document.getElementById('symbol-input').value.trim().toUpperCase();
  if(!v) return;
  await api('/api/symbols', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol:v})});
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

async function startBacktest(){
  const checked = Array.from(document.querySelectorAll('.bt-sym-cb:checked')).map(cb=>cb.value);
  const extraRaw = document.getElementById('bt-symbol-extra').value.trim();
  const extra = extraRaw ? extraRaw.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean) : [];
  const symbols = Array.from(new Set([...checked, ...extra]));
  const days = parseFloat(document.getElementById('bt-days').value);
  const capitalRaw = document.getElementById('bt-capital').value;
  if(symbols.length === 0){ toast('请至少选择/填写一个标的', false); return; }
  const body = {symbols, days_back: days};
  if(capitalRaw) body.initial_capital = parseFloat(capitalRaw);
  if(document.getElementById('bt-walkforward').checked){
    body.walkforward = true;
    body.wf_folds = parseInt(document.getElementById('bt-wf-folds').value) || 5;
  }
  const r = await api('/api/backtest/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  if(r.ok){
    toast('回测任务已提交，正在后台下载数据并运行', true);
    document.getElementById('bt-start-msg').textContent = '任务ID: ' + r.job_id;
    BT_VIEW_JOB_ID = r.job_id;
    refreshBacktestList();
  }
}

function jobStatusLabel(s){
  return {pending:'排队中', fetching:'下载数据中', running:'回测运行中', done:'已完成', error:'失败'}[s] || s;
}

async function refreshBacktestList(){
  const list = await (await fetch('/api/backtest/list')).json();
  const el = document.getElementById('bt-joblist');
  if(!list.jobs || list.jobs.length === 0){
    el.innerHTML = '<div class="hint">还没有回测任务，在上方勾选标的后点击"开始回测"。</div>';
  } else {
    el.innerHTML = list.jobs.map(j => {
      const active = ['pending','fetching','running'].includes(j.status);
      const symTxt = (j.symbols||[]).join(', ');
      const sumTxt = j.summary ? `年化收益 ${fmtNum(j.summary.annualized_return_pct)}%　Sharpe ${fmtNum(j.summary.sharpe)}　交易${j.summary.trade_count}笔` : (j.error || j.message || '');
      return `<div class="jobrow ${j.id===BT_VIEW_JOB_ID?'selected':''}" onclick="viewBacktest('${j.id}')">
        <span class="sym" title="${symTxt}">${symTxt.length>28 ? symTxt.slice(0,28)+'…' : symTxt}</span>
        <span class="badge ${j.status}">${jobStatusLabel(j.status)}</span>
        <span class="meta">${sumTxt}
          ${active ? `<div class="progressbar"><div style="width:${j.progress_pct||0}%"></div></div><div>${j.message||''}</div>` : ''}
        </span>
        <span class="hint">${fmtTs(j.created_at)}</span>
      </div>`;
    }).join('');
  }
  if(BT_VIEW_JOB_ID){
    const cur = (list.jobs||[]).find(j => j.id === BT_VIEW_JOB_ID);
    if(cur && ['pending','fetching','running'].includes(cur.status)){
      loadBacktestDetail(BT_VIEW_JOB_ID);
    }
  }
}

function viewBacktest(jobId){
  BT_VIEW_JOB_ID = jobId;
  loadBacktestDetail(jobId);
  refreshBacktestList();
}

async function loadBacktestDetail(jobId){
  const job = await (await fetch('/api/backtest/job/' + jobId)).json();
  const sec = document.getElementById('bt-detail-section');
  if(job.status !== 'done'){
    sec.style.display = 'block';
    document.getElementById('bt-summary-grid').innerHTML = `<div class="card"><div class="label">状态</div><div class="value">${jobStatusLabel(job.status)}（${job.progress_pct||0}%）</div></div>`;
    document.getElementById('bt-warnings').innerHTML = job.error ? `<div class="warnbox">${job.error}</div>` : '';
    document.querySelector('#bt-trades tbody').innerHTML = '';
    document.querySelector('#bt-per-symbol tbody').innerHTML = '';
    return;
  }
  sec.style.display = 'block';
  const s = job.summary;
  document.getElementById('bt-warnings').innerHTML = (s.warnings||[]).map(w => `<div class="warnbox">${w}</div>`).join('');
  document.getElementById('bt-summary-grid').innerHTML = `
    <div class="card"><div class="label">回测标的</div><div class="value" style="font-size:13px;">${(s.symbols||[]).join(', ')}</div></div>
    <div class="card"><div class="label">数据窗口</div><div class="value" style="font-size:13px;">${fmtTs(s.start_ts)} ~ ${fmtTs(s.end_ts)}</div></div>
    <div class="card"><div class="label">初始资金 → 结束资金</div><div class="value" style="font-size:15px;">${fmtNum(s.initial_capital,0)} → ${fmtNum(s.final_equity)}</div></div>
    <div class="card"><div class="label">总收益率</div><div class="value ${cls(s.return_pct)}">${fmtNum(s.return_pct)}%</div></div>
    <div class="card"><div class="label">年化收益率(CAGR)</div><div class="value ${cls(s.annualized_return_pct)}">${fmtNum(s.annualized_return_pct)}%</div></div>
    <div class="card"><div class="label">年化波动率</div><div class="value">${fmtNum(s.annualized_vol_pct)}%</div></div>
    <div class="card"><div class="label">Sharpe</div><div class="value ${cls(s.sharpe)}">${fmtNum(s.sharpe)}</div></div>
    <div class="card"><div class="label">Sortino</div><div class="value ${cls(s.sortino)}">${fmtNum(s.sortino)}</div></div>
    <div class="card"><div class="label">最大回撤</div><div class="value neg">${fmtNum(s.max_drawdown_pct)}%</div></div>
    <div class="card"><div class="label">Calmar</div><div class="value ${cls(s.calmar)}">${fmtNum(s.calmar)}</div></div>
    <div class="card"><div class="label">年化换手率(倍)</div><div class="value">${fmtNum(s.turnover_annualized)}</div></div>
    <div class="card"><div class="label">交易数</div><div class="value">${s.trade_count}</div></div>
    <div class="card"><div class="label">平均自适应风险乘数</div><div class="value">${fmtNum((s.avg_adaptive_risk_multiplier||1)*100,1)}%</div></div>
    <div class="card"><div class="label">最低自适应风险乘数</div><div class="value">${fmtNum((s.min_adaptive_risk_multiplier||1)*100,1)}%</div></div>
    <div class="card"><div class="label">自适应缩仓触发占比</div><div class="value">${fmtNum(s.adaptive_risk_active_pct||0,1)}%</div></div>
  `;
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
      <td>${fmtNum((p.last_adaptive_risk_multiplier||1)*100,1)}%</td></tr>`;
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

function drawEquityCurve(points){
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
  ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 1.5; ctx.beginPath();
  points.forEach((p, i) => {
    const x = pad + (i/(points.length-1)) * (cssW - pad*2);
    const y = pad + (1 - (p.e - minV)/range) * (cssH - pad*2);
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
  ctx.fillStyle = '#8b949e'; ctx.font = '11px monospace';
  ctx.fillText(maxV.toFixed(1), 2, pad);
  ctx.fillText(minV.toFixed(1), 2, cssH - 6);
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
  buildFields('invert-direction-field', data.systematic || {},
              {invert_direction: '反向执行(开多↔开空对调)'}, {invert_direction: 'bool'});
  buildFields('sys-regime-fields', data.systematic || {}, SYS_REGIME_LABELS);
  buildFields('sys-adv-fields', data.systematic || {}, SYS_ADV_LABELS, SYS_ADV_TYPES);
  buildFields('costs-fields', data.costs || {}, COST_LABELS, COST_TYPES);
  updateInvertBadge((data.systematic || {}).invert_direction);

  document.getElementById('symbols-chips').innerHTML = (data.symbols||[]).map(s =>
    `<span class="chip">${s}<button onclick="removeSymbol('${s}')">×</button></span>`).join('');
  document.getElementById('bt-symbol-checks').innerHTML = (data.symbols||[]).map(s =>
    `<label class="symcheckbox"><input type="checkbox" class="bt-sym-cb" value="${s}" checked> ${s}</label>`).join('');

  if(!(data._creds && data._creds.is_set)){
    showTab('settings');
  }
}

async function refresh(){
  const res = await fetch('/api/state'); const data = await res.json();
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
    <div class="card"><div class="label">盈亏比 PF</div><div class="value">${isFinite(s.profit_factor)?s.profit_factor.toFixed(2):'∞'}</div></div>
    <div class="card"><div class="label">累计手续费/资金费</div><div class="value neg">${fmtNum(s.total_fees_paid)} / ${fmtNum(s.total_funding_paid)}</div></div>
    <div class="card"><div class="label">当前持仓数</div><div class="value">${s.open_position_count}</div></div>
    <div class="card"><div class="label">熔断状态</div><div class="value ${s.day_pnl_pct<0?'neg':'pos'}">${data.circuit_breaker ? '熔断中':'正常'}</div></div>
    <div class="card"><div class="label">运行时长</div><div class="value">${fmtSecs(s.uptime_seconds)}</div></div>
  `;

  const p = data.portfolio || {};
  document.getElementById('portfolio-grid').innerHTML = `
    <div class="card"><div class="label">目标年化波动率</div><div class="value">${fmtNum(p.target_vol_pct,1)}%</div></div>
    <div class="card"><div class="label">当前组合信号置信度</div><div class="value">${fmtNum((p.portfolio_conviction||0)*100,1)}%</div></div>
    <div class="card"><div class="label">当前自适应风险乘数</div><div class="value">${fmtNum((p.average_risk_multiplier||1)*100,1)}%</div></div>
    <div class="card"><div class="label">缩放前组合波动率</div><div class="value">${fmtNum(p.portfolio_vol_before_scale_pct,1)}%</div></div>
    <div class="card"><div class="label">组合缩放系数</div><div class="value">${fmtNum(p.scale_factor,2)}</div></div>
    <div class="card"><div class="label">组合总杠杆</div><div class="value">${fmtNum(p.gross_leverage,2)}</div></div>
    <div class="card"><div class="label">分散化收益</div><div class="value pos">${fmtNum(p.diversification_benefit_pct,1)}%</div></div>
    <div class="card"><div class="label">上次组合计算时间</div><div class="value" style="font-size:13px;">${fmtTs(p.ts)}</div></div>
  `;

  const posBody = document.querySelector('#positions tbody');
  posBody.innerHTML = (data.positions||[]).map(p => `<tr>
    <td>${p.symbol}</td><td>${p.side==='long'?'多':'空'}</td><td>${p.size}</td>
    <td>${fmtNum(p.entry_price,4)}</td><td>${fmtNum(p.mark_price,4)}</td>
    <td class="${cls(p.unrealized_pnl)}">${fmtNum(p.unrealized_pnl)}</td>
    <td>${fmtSecs(p.holding_seconds)}</td></tr>`).join('');

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

refreshBootstrap().then(() => showTab(ACTIVE_TAB));
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
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
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
  main { padding:20px 24px; max-width:1300px; margin:0 auto; }
  nav { display:flex; gap:6px; margin-bottom:16px; }
  nav button { background:transparent; border:1px solid var(--border); color:var(--text); padding:8px 18px;
               border-radius:6px; cursor:pointer; font-size:14px; }
  nav button.active { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:600; }
  .subpage { display:none; } .subpage.active { display:block; }
  section { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px 18px; margin-bottom:16px; }
  section h3 { margin-top:0; font-size:15px; color:var(--accent); }
  .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:12px; }
  input,select,button.btn { background:#0d1117; color:var(--text); border:1px solid var(--border);
        border-radius:6px; padding:8px 12px; font-size:14px; }
  button.btn { cursor:pointer; } button.btn:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); color:#04121f; border-color:var(--accent); font-weight:700; }
  .field { display:flex; flex-direction:column; gap:4px; }
  .field label { font-size:12px; color:var(--muted); }
  #live-chart, #bt-chart { width:100%; height:480px; border:1px solid var(--border); border-radius:6px; }
  .hint { font-size:12px; color:var(--muted); margin-top:6px; line-height:1.6; }
  .legend { display:flex; gap:18px; flex-wrap:wrap; margin:10px 0; font-size:12px; color:var(--muted); }
  .legend span.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; }
  table { width:100%; border-collapse:collapse; margin-top:14px; font-size:13px; }
  th,td { border-bottom:1px solid #21262d; padding:6px 8px; text-align:left; }
  th { color:var(--muted); font-weight:500; }
  .pos { color:var(--pos); } .neg { color:var(--neg); }
  .cards { display:grid; grid-template-columns: repeat(4,1fr); gap:10px; margin-bottom:14px; }
  .card { background:#0d1117; border:1px solid var(--border); border-radius:8px; padding:10px 14px; }
  .card .label { font-size:12px; color:var(--muted); }
  .card .value { font-size:17px; font-weight:600; margin-top:4px; }
  .warnbox { background:#3a2400; border:1px solid var(--warn); color:var(--warn); padding:10px 14px;
             border-radius:8px; margin-bottom:14px; font-size:13px; line-height:1.6; }
</style>
</head>
<body>
<header>
  <h1>📈 K线图 —— 买卖点可视化</h1>
  <div style="display:flex;gap:6px;align-items:center">
    <a href="/manual" style="color:var(--text);text-decoration:none;border:1px solid var(--border);border-radius:6px;padding:8px 14px;font-size:14px;">🧪 手动开单</a>
    <a href="/update" style="color:var(--text);text-decoration:none;border:1px solid var(--border);border-radius:6px;padding:8px 14px;font-size:14px;">⬆️ 检查更新</a>
    <a href="/">← 返回控制台</a>
  </div>
</header>
<main>
  <nav>
    <button id="nav-live" onclick="showSub('live')">实时 / 模拟盘</button>
    <button id="nav-bt" onclick="showSub('bt')">回测</button>
  </nav>

  <div id="invert-warn" class="warnbox" style="display:none;">
    ⚠️ 反向执行模式已开启：下面图表上标注的开多/开空标记是"实际执行方向"（已经和策略原始计算方向对调过）。
  </div>

  <div id="sub-live" class="subpage">
    <section>
      <div class="row">
        <div class="field"><label>标的</label><select id="live-symbol"></select></div>
        <div class="field"><label>K线周期</label>
          <select id="live-interval">
            <option value="1h">1H（短趋势）</option>
            <option value="4h">4H（主趋势）</option>
            <option value="1d">1D（Regime）</option>
          </select>
        </div>
        <div class="field"><label>根数</label><input id="live-limit" type="number" value="300" min="50" max="2000" style="width:100px;"></div>
        <button class="btn primary" onclick="loadLiveChart()">刷新</button>
        <label class="hint"><input type="checkbox" id="live-auto" checked> 每30秒自动刷新</label>
        <label class="hint"><input type="checkbox" id="live-marker-text" checked onchange="loadLiveChart()"> 显示标记文字</label>
      </div>
      <div class="hint" id="live-msg"></div>
      <div class="hint">提示：图表支持鼠标滚轮缩放、拖拽平移；成交较密集时标记文字会互相遮挡，
        可以放大到具体时间段查看，或取消勾选上面的"显示标记文字"只看颜色/形状。</div>
      <div id="live-chart"></div>
      <div class="legend">
        <span><span class="dot" style="background:#3fb950;"></span>开多/平空盈利</span>
        <span><span class="dot" style="background:#f85149;"></span>开空/平多亏损</span>
        <span><span class="dot" style="background:#58a6ff;"></span>当前持仓开仓价(虚线)</span>
      </div>
      <table id="live-trades"><thead><tr>
        <th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>开仓时间</th><th>平仓时间</th><th>原因</th>
      </tr></thead><tbody></tbody></table>
    </section>
  </div>

  <div id="sub-bt" class="subpage">
    <section>
      <div class="row">
        <div class="field" style="min-width:320px;"><label>回测任务</label><select id="bt-job"></select></div>
        <div class="field"><label>标的</label><select id="bt-symbol"></select></div>
        <div class="field"><label>K线周期</label>
          <select id="bt-interval">
            <option value="1h">1H（短趋势）</option>
            <option value="4h">4H（主趋势）</option>
            <option value="1d">1D（Regime）</option>
          </select>
        </div>
        <button class="btn primary" onclick="loadBtChart()">加载</button>
        <label class="hint"><input type="checkbox" id="bt-marker-text" checked onchange="loadBtChart()"> 显示标记文字</label>
      </div>
      <div class="hint" id="bt-msg"></div>
      <div class="hint">提示：图表支持鼠标滚轮缩放、拖拽平移；回测时间跨度较长、成交较密集时标记文字会
        互相遮挡看不清，可以放大到具体时间段查看，或取消勾选上面的"显示标记文字"只看颜色/形状，
        详细数值以下方"逐笔成交"表格为准。</div>
      <div class="cards" id="bt-cards"></div>
      <div id="bt-chart"></div>
      <div class="legend">
        <span><span class="dot" style="background:#3fb950;"></span>开多 / 盈利平仓</span>
        <span><span class="dot" style="background:#f85149;"></span>开空 / 亏损平仓</span>
      </div>
      <table id="bt-chart-trades"><thead><tr>
        <th>方向</th><th>开仓价</th><th>平仓价</th><th>净盈亏</th><th>持仓时长</th><th>原因</th>
      </tr></thead><tbody></tbody></table>
    </section>
  </div>
</main>

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
}

function fmtNum(v, d){ return (typeof v === 'number' && isFinite(v)) ? v.toFixed(d==null?2:d) : '-'; }
function fmtTs(t){ if(!t) return '-'; return new Date(t*1000).toLocaleString(); }
function fmtSecs(s){ s=Math.floor(s||0); const h=Math.floor(s/3600), m=Math.floor((s%3600)/60);
  if(h) return h+'h'+m+'m'; return m+'m'; }

function makeChart(containerId){
  const el = document.getElementById(containerId);
  const chart = LightweightCharts.createChart(el, {
    width: el.clientWidth, height: 480,
    layout: { background: { color: '#0d1117' }, textColor: '#c9d1d9' },
    grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#30363d' },
    rightPriceScale: { borderColor: '#30363d' },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
  });
  const series = chart.addCandlestickSeries({
    upColor: '#3fb950', downColor: '#f85149', borderVisible: false,
    wickUpColor: '#3fb950', wickDownColor: '#f85149',
  });
  window.addEventListener('resize', () => chart.applyOptions({ width: el.clientWidth }));
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
  const symSel = document.getElementById('bt-symbol');
  const prev = symSel.value;
  const syms = (job && job.symbols) || [];
  symSel.innerHTML = syms.map(s => `<option value="${s}">${s}</option>`).join('');
  if(prev && syms.includes(prev)) symSel.value = prev;
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('bt-job').addEventListener('change', onBtJobChange);
});

// ---------------------------------------------------------- 实时/模拟盘图表
async function loadLiveChart(){
  const symbol = document.getElementById('live-symbol').value;
  const interval = document.getElementById('live-interval').value;
  const limit = document.getElementById('live-limit').value;
  if(!symbol){ document.getElementById('live-msg').textContent = '请先在设置页添加交易标的'; return; }
  document.getElementById('live-msg').textContent = '加载中...';

  if(!liveChart){ const r = makeChart('live-chart'); liveChart = r.chart; liveSeries = r.series; }

  const klineRes = await (await fetch(`/api/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`)).json();
  if(!klineRes.ok){ document.getElementById('live-msg').textContent = 'K线加载失败: ' + klineRes.message; return; }
  const candles = klineRes.candles.map(c => ({ time: c.t, open: c.o, high: c.h, low: c.l, close: c.c }));
  liveSeries.setData(candles);

  const stateRes = await (await fetch('/api/state')).json();
  const trades = (stateRes.trades||[]).filter(t => t.symbol === symbol);
  const positions = (stateRes.positions||[]).filter(p => p.symbol === symbol);

  const showText = document.getElementById('live-marker-text').checked;
  const markers = [];
  trades.forEach(t => {
    const isLong = t.side === 'long';
    markers.push({
      time: Math.floor(t.open_time), position: isLong ? 'belowBar' : 'aboveBar',
      color: isLong ? '#3fb950' : '#f85149', shape: isLong ? 'arrowUp' : 'arrowDown',
      text: showText ? (isLong ? '开多' : '开空') : '',
    });
    markers.push({
      time: Math.floor(t.close_time), position: isLong ? 'aboveBar' : 'belowBar',
      color: t.pnl >= 0 ? '#3fb950' : '#f85149', shape: isLong ? 'arrowDown' : 'arrowUp',
      text: showText ? `平${isLong?'多':'空'}(${t.pnl>=0?'+':''}${fmtNum(t.pnl,1)})` : '',
    });
  });
  markers.sort((a,b) => a.time - b.time);
  liveSeries.setMarkers(markers);

  livePriceLines.forEach(pl => liveSeries.removePriceLine(pl));
  livePriceLines = positions.map(p => liveSeries.createPriceLine({
    price: p.entry_price, color: '#58a6ff', lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed, axisLabelVisible: true,
    title: `${p.side==='long'?'多':'空'}仓开仓价`,
  }));

  document.getElementById('live-msg').textContent =
    `${symbol} ${interval} 共${candles.length}根K线，标注${trades.length}笔历史成交` +
    (positions.length ? `，当前持仓${positions.length}笔` : '，当前无持仓');

  const tbody = document.querySelector('#live-trades tbody');
  tbody.innerHTML = trades.map(t => `<tr>
    <td>${t.side==='long'?'多':'空'}</td><td>${fmtNum(t.entry_price,4)}</td><td>${fmtNum(t.exit_price,4)}</td>
    <td class="${t.pnl>=0?'pos':'neg'}">${fmtNum(t.pnl)}</td>
    <td>${fmtTs(t.open_time)}</td><td>${fmtTs(t.close_time)}</td><td>${t.exit_reason||''}</td>
  </tr>`).join('');
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
async function loadBtChart(){
  const jobId = document.getElementById('bt-job').value;
  const symbol = document.getElementById('bt-symbol').value;
  const interval = document.getElementById('bt-interval').value;
  if(!jobId || !symbol){ document.getElementById('bt-msg').textContent = '请先选择回测任务和标的'; return; }
  document.getElementById('bt-msg').textContent = '加载中...';

  if(!btChart){ const r = makeChart('bt-chart'); btChart = r.chart; btSeries = r.series; }

  const job = await (await fetch('/api/backtest/job/' + jobId)).json();
  const s = job.summary || {};

  const klineRes = await (await fetch(
    `/api/klines/cache?symbol=${symbol}&interval=${interval}&start_ts=${s.start_ts||0}&end_ts=${s.end_ts||9999999999}`
  )).json();
  if(!klineRes.ok){ document.getElementById('bt-msg').textContent = 'K线加载失败: ' + klineRes.message; return; }
  const candles = klineRes.candles.map(c => ({ time: c.t, open: c.o, high: c.h, low: c.l, close: c.c }));
  btSeries.setData(candles);

  const symTrades = (job.trades||[]).filter(t => t.symbol === symbol);
  const showText = document.getElementById('bt-marker-text').checked;
  const markers = [];
  symTrades.forEach(t => {
    const isLong = t.side === 'long';
    markers.push({
      time: Math.floor(t.open_time), position: isLong ? 'belowBar' : 'aboveBar',
      color: isLong ? '#3fb950' : '#f85149', shape: isLong ? 'arrowUp' : 'arrowDown',
      text: showText ? (isLong ? '开多' : '开空') : '',
    });
    markers.push({
      time: Math.floor(t.close_time), position: isLong ? 'aboveBar' : 'belowBar',
      color: t.pnl >= 0 ? '#3fb950' : '#f85149', shape: isLong ? 'arrowDown' : 'arrowUp',
      text: showText ? `平${isLong?'多':'空'}(${t.pnl>=0?'+':''}${fmtNum(t.pnl,1)})` : '',
    });
  });
  markers.sort((a,b) => a.time - b.time);
  btSeries.setMarkers(markers);

  document.getElementById('bt-msg').textContent =
    candles.length === 0
      ? `本地没有 ${symbol} ${interval} 的缓存K线，可能该回测没有用到这个周期，换个周期试试`
      : `${symbol} ${interval} 共${candles.length}根K线，标注${symTrades.length}笔交易`;

  const perSym = (s.per_symbol || {})[symbol] || {};
  document.getElementById('bt-cards').innerHTML = `
    <div class="card"><div class="label">交易数</div><div class="value">${perSym.trade_count||0}</div></div>
    <div class="card"><div class="label">净盈亏</div><div class="value ${(perSym.net_pnl||0)>=0?'pos':'neg'}">${fmtNum(perSym.net_pnl)}</div></div>
    <div class="card"><div class="label">手续费/资金费</div><div class="value">${fmtNum(perSym.fees)} / ${fmtNum(perSym.funding)}</div></div>
  `;

  const tbody = document.querySelector('#bt-chart-trades tbody');
  tbody.innerHTML = symTrades.map(t => `<tr>
    <td>${t.side==='long'?'多':'空'}</td><td>${fmtNum(t.entry_price,4)}</td><td>${fmtNum(t.exit_price,4)}</td>
    <td class="${t.pnl>=0?'pos':'neg'}">${fmtNum(t.pnl)}</td>
    <td>${fmtSecs(t.close_time-t.open_time)}</td><td>${t.reason||''}</td>
  </tr>`).join('');
}

(async function init(){
  await loadSymbolsIntoSelects();
  await loadJobsIntoSelect();
  showSub('live');
  if(ALL_SYMBOLS.length) loadLiveChart();
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
    策略引擎下一轮同步时会把这里开出来的仓位当成"外部已有持仓"接管。测试完请记得手动平掉。
    <br>「仓位价值」填的是<b>不含杠杆的名义价值</b>：填 1000 就是开 1000 USDT 的仓，
    杠杆只决定占用多少保证金（1000÷杠杆），不改变仓位大小。
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
    <div class="row">
      <div class="field"><label>仓位价值(USDT，不含杠杆)</label><input id="${p.id}-notional" type="number" min="0" step="any" value="100"></div>
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
    实际名义价值：<b>${r.actual_notional.toFixed(2)}</b> USDT（你填的是 ${r.requested_notional.toFixed(2)}）<br>
    占用保证金：<b>${r.margin.toFixed(2)}</b> USDT （= 名义价值 ÷ ${r.leverage}x）<br>
    预估开仓手续费：${r.est_fee.toFixed(4)} USDT<br>
    ${r.tp?`止盈 ${r.tp}（距现价 ${r.tp_pct}%）<br>`:''}
    ${r.sl?`止损 ${r.sl}（距现价 ${r.sl_pct}%，按此仓位约亏 ${r.sl_loss.toFixed(2)} USDT）<br>`:''}
    ${warn}</div>`;
}

async function submitOrder(id){
  const body = readForm(id);
  if(!body.symbol || !(body.notional>0)){ alert('请填写合约代码和仓位价值'); return; }
  const modeTxt = CUR_MODE==='live' ? '【实盘 LIVE·真实资金】' : '【模拟盘 PAPER】';
  const msg = `${modeTxt}\\n\\n${body.symbol} ${body.side==='long'?'做多':'做空'}\\n`
            + `仓位价值 ${body.notional} USDT，杠杆 ${body.leverage}x\\n`
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
  for(let raw of md.split('\n')){
    let t = esc(raw.trimEnd());
    if(/^###\s+/.test(t)){ if(inList){out.push('</ul>');inList=false;} out.push('<h3>'+t.replace(/^###\s+/,'')+'</h3>'); continue; }
    if(/^##\s+/.test(t)){ if(inList){out.push('</ul>');inList=false;} out.push('<h2>'+t.replace(/^##\s+/,'')+'</h2>'); continue; }
    if(/^\s*[-*]\s+/.test(t)){
      if(!inList){ out.push('<ul>'); inList=true; }
      out.push('<li>'+inline(t.replace(/^\s*[-*]\s+/,''))+'</li>'); continue;
    }
    if(inList){ out.push('</ul>'); inList=false; }
    if(t.trim()==='' ) { out.push(''); continue; }
    if(/^---+$/.test(t.trim())) { out.push('<hr style="border:none;border-top:1px solid var(--border);margin:14px 0">'); continue; }
    out.push('<p style="margin:8px 0">'+inline(t)+'</p>');
  }
  if(inList) out.push('</ul>');
  return out.join('\n');
  function inline(x){
    return x.replace(/`([^`]+)`/g,'<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
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
  if(!confirm('确认更新到 v'+INFO.latest+'？\n\n更新前请确保：\n· 交易引擎已停止\n· 没有未平仓的持仓\n\n更新后需要重启程序。')) return;
  const box = document.getElementById('steps-box');
  box.innerHTML = '<div class="hint"><span class="spin"></span>正在更新…</div>';
  const r = await (await fetch('/api/update/perform',{method:'POST'})).json();
  const steps = (r.steps||[]).map(s=>
    '<li>'+(s.ok?'<span class="pos">✔</span>':'<span class="neg">✘</span>')+' <b>'+s.name+'</b>：'
    + String(s.message).replace(/\n/g,'<br>')+'</li>').join('');
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
               controller: EngineController, backtest_controller: BacktestController) -> Flask:
    app = Flask(__name__)
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    @app.route("/")
    def index():
        return render_template_string(PAGE)

    @app.route("/charts")
    def charts_page():
        return render_template_string(CHARTS_PAGE)

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
        if notional <= 0:
            raise RuntimeError("仓位价值必须大于0")
        if side not in ("long", "short"):
            raise RuntimeError("方向只能是 long / short")

        info = ex.get_contract(symbol)
        mark = float(ex.get_ticker(symbol)["mark_price"])
        qm = float(info["quanto_multiplier"])
        step = max(1, int(info.get("order_size_min", 1)))
        if mark <= 0 or qm <= 0:
            raise RuntimeError(f"{symbol} 行情或合约参数异常(标记价={mark}, 面值={qm})")

        raw_contracts = notional / (mark * qm)
        contracts = int(raw_contracts // step) * step        # 向下取整到最小下单单位
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
        taker = float(info.get("taker_fee_rate") or 0.0005)
        return {
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
        if r.get("margin_mode") == "isolated":
            state.add_log(f"[手动测试] {symbol} 仍是逐仓，已拒绝开仓", "ERROR")
            return jsonify({"ok": False, "steps": steps,
                             "message": "保证金模式仍是逐仓，已中止下单（不会在逐仓下开单）"})

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
        with state.with_lock():
            signals = [{"symbol": k, **v} for k, v in state.last_signals.items()]
            logs = list(state.logs[-150:])
            portfolio = dict(state.portfolio_snapshot)
        summary = state.summary()
        return jsonify({
            "summary": summary,
            "positions": state.positions_view(),
            "signals": signals,
            "trades": state.recent_trades_view(40),
            "logs": logs,
            "circuit_breaker": state.circuit_breaker_active,
            "portfolio": portfolio,
        })

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        cfg = config_store.snapshot()
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
        if symbol:
            config_store.add_symbol(symbol)
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
            equity = ex.get_account_equity()
            return jsonify({"ok": True, "message": f"连接成功，账户权益 {equity:.2f} USDT"})
        except Exception as e:
            return jsonify({"ok": False, "message": f"连接失败: {e}"})

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

    # ---------------------------------------------------------- 回测（组合级）
    @app.route("/api/backtest/start", methods=["POST"])
    def backtest_start():
        data = request.get_json(force=True) or {}
        symbols = data.get("symbols") or ([data["symbol"]] if data.get("symbol") else None)
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
        state.add_log(f"发起组合回测任务: {', '.join(job.symbols)} 最近{job.days_back}天"
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
