/* Public screening only; adding candidates never starts an engine. */
const UniverseUI = (() => {
  let scan = null, timer = null, loading = false;
  const el = id => document.getElementById(id);
  async function json(url, options){
    const response = await fetch(url, options);
    const data = await response.json();
    if(!response.ok) throw new Error(data.message || '公共行情请求失败');
    return data;
  }
  function render(data){
    scan = data;
    el('universe-rows').replaceChildren();
    el('universe-cards').replaceChildren();
    el('universe-empty').hidden=!!(data.candidates||[]).length;
    el('universe-apply').hidden=!(data.candidates||[]).length;
    el('universe-apply').disabled = data.status !== 'done' || data.stale || !(data.candidates || []).length;
    el('universe-refresh').disabled = data.status === 'running';
    if(data.status === 'running') el('universe-status').textContent = `正在扫描公共市场 ${data.progress || 0}%（无需 API Key）`;
    else if(data.status === 'error') el('universe-status').textContent = `筛选失败：${data.message || '行情暂不可用'}。未更改交易池。`;
    else if(data.status === 'done') el('universe-status').textContent = `${data.stale ? '已过期 · ' : ''}${new Date(data.as_of * 1000).toLocaleString()} · ${data.crypto_count} 个可交易加密合约 → ${data.liquidity_count} 个通过流动性检查 → ${data.factor_count} 个符合趋势条件 → ${(data.candidates || []).length} 个候选`;
    if(!(data.candidates||[]).length){
      el('universe-empty-title').textContent=data.status==='running'?'正在检查市场':data.status==='error'?'本次筛选未完成':'暂无符合条件的候选';
      el('universe-empty-note').textContent=data.status==='running'?'正在检查趋势、路径质量与成本，完成后显示候选。':data.status==='error'?'可点击右上方按钮重试；已有交易池未改变。':'本次条件下没有合格候选，不放宽规则凑满五个。';
    }
    const add=(parent,tag,cls,text)=>{const node=document.createElement(tag);node.className=cls;if(text!==undefined)node.textContent=text;parent.appendChild(node);return node;};
    for(const [index,c] of (data.candidates || []).entries()){
      const card=add(el('universe-cards'),'li','candidate-card');
      const top=add(card,'div','candidate-top');add(top,'span','candidate-rank',String(index+1).padStart(2,'0'));
      add(top,'span','side-tag '+(c.side==='long'?'long':'short'),c.side==='long'?'做多候选':'做空候选');
      add(card,'h3','',c.symbol.replace(/_USDT$/,''));add(card,'div','contract-label','USDT PERPETUAL');
      add(card,'div','candidate-score',c.score.toFixed(2));add(card,'div','candidate-score-label','本次相对评分');
      const metrics=add(card,'dl','');
      for(const [label,value] of [['1H / 4H',`${c.short_forecast.toFixed(1)} / ${c.main_forecast.toFixed(1)}`],['路径效率',`${(c.quality*100).toFixed(1)}%`],['往返成本',`${c.round_trip_cost_bps.toFixed(1)} bps`],['24H 成交额',`${(c.turnover_24h/1e6).toFixed(1)} M`]]){
        const row=add(metrics,'div','');add(row,'dt','',label);add(row,'dd','',value);
      }
      const tr = document.createElement('tr');
      const values = [c.symbol, c.side === 'long' ? '多' : '空', c.score.toFixed(2),
        `${c.short_forecast.toFixed(1)} / ${c.main_forecast.toFixed(1)}`, `${(c.quality*100).toFixed(1)}%`,
        `${c.round_trip_cost_bps.toFixed(1)} bps`, `${(c.turnover_24h / 1e6).toFixed(1)} M USDT`];
      for(const value of values){ const td = document.createElement('td'); td.textContent = value; tr.appendChild(td); }
      el('universe-rows').appendChild(tr);
    }
    el('universe-rejections').textContent = Object.entries(data.rejected_counts || {}).map(([reason,n])=>`${reason}：${n}`).join(' · ');
  }
  async function poll(){
    try { const data = await json('/api/universe'); render(data); }
    catch(error){ el('universe-status').textContent = error.message; el('universe-apply').disabled = true; }
    timer = setTimeout(poll, scan && scan.status === 'running' ? 2000 : 30000);
  }
  async function start(force=false){
    if(loading) return;
    loading = true; clearTimeout(timer);
    scan = null;
    el('universe-apply').disabled = true;
    el('universe-refresh').disabled = true;
    el('universe-rows').replaceChildren();
    el('universe-cards').replaceChildren();
    el('universe-empty').hidden=false;
    el('universe-apply').hidden=true;
    el('universe-empty-title').textContent='正在提交筛选';
    el('universe-empty-note').textContent='等待公共行情响应…';
    el('universe-rejections').textContent = '';
    el('universe-status').textContent = '正在提交筛选…';
    try { render(await json('/api/universe/scan', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force})})); }
    catch(error){ el('universe-status').textContent = error.message;el('universe-empty-title').textContent='本次筛选未完成';el('universe-empty-note').textContent='请稍后点击按钮重试。'; }
    finally {
      loading=false;
      if(scan) timer=setTimeout(poll,2000);
      else el('universe-refresh').disabled=false;
    }
  }
  async function apply(){
    if(!scan || scan.stale || scan.status !== 'done') return;
    el('universe-apply').disabled=true;
    try {
      const result = await json('/api/universe/apply', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scan_id:scan.scan_id})});
      if(!result.ok) throw new Error(result.message || '更新失败');
      toast('候选已加入交易池；原有手动标的保留',true); await refreshBootstrap();
    } catch(error){ toast(error.message,false); }
    finally { await pollOnce(); }
  }
  async function pollOnce(){ try{render(await json('/api/universe'));}catch(_){el('universe-apply').disabled=true;} }
  async function init(onCatalogue=()=>{}){
    el('universe-refresh').onclick=()=>start(true);
    el('universe-apply').onclick=apply;
    const catalogueRequest=json('/api/universe/catalogue').then(data=>{
      if(!data.ok) throw new Error('公共合约目录不可用');
      el('market-symbols').replaceChildren();
      for(const c of data.contracts){const option=document.createElement('option');option.value=c.symbol;option.label=c.crypto?'加密货币':'其他永续合约';el('market-symbols').appendChild(option);}
      onCatalogue(data.contracts);
      el('bt-symbol-hint').textContent=`可搜索 ${data.contracts.length} 个 Gate USDT 合约；每次一个，无需加入交易池。`;
    }).catch(()=>{el('bt-symbol-hint').textContent='合约提示暂不可用，仍可输入完整代码或币名回测，例如 BTC_USDT 或 BTC。';});
    // Opening/reloading the page never initiates or displays a recommendation.
    el('universe-apply').disabled=true;
    el('universe-status').textContent='点击“筛选五个候选”后开始扫描公共行情。';
    await catalogueRequest;
  }
  return {init};
})();
