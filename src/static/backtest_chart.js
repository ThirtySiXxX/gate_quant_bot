/* Backtest fills: exact bar alignment, no fabricated entries for reductions. */
(function(root){
  const names={open:'首次开仓',add:'加仓',reduce:'减仓',close:'完全平仓'};
  function markers(events,showText){
    return events.filter(e=>Number.isFinite(e.chart_time)).map(e=>{
      const opening=e.action==='open'||e.action==='add',long=e.side==='long';
      return {time:e.chart_time,id:String(e.id),position:opening==long?'belowBar':'aboveBar',
        color:e.action==='add'?'#58a6ff':e.action==='reduce'?'#d29922':opening?(long?'#3fb950':'#f85149'):(e.pnl>=0?'#3fb950':'#f85149'),
        shape:e.action==='open'?(long?'arrowUp':'arrowDown'):e.action==='add'?'circle':'square',
        text:showText?names[e.action]+(long?' 多':' 空'):''};
    }).sort((a,b)=>a.time-b.time);
  }
  let payload=null,key='',sequence=0,priceLine=null;
  const fmt=(v,n=4)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(n):'未知';
  function selectedEvents(){const filter=document.getElementById('bt-event-filter').value;return (payload?.events||[]).filter(e=>filter==='all'||e.action===filter);}
  function draw(){
    if(!payload||!btSeries)return;
    const events=selectedEvents();
    btSeries.setMarkers(payload.candles.length?markers(events,document.getElementById('bt-marker-text').checked):[]);
    const body=document.querySelector('#bt-chart-trades tbody');body.replaceChildren();
    events.forEach(e=>{
      const row=document.createElement('tr');row.style.cursor='pointer';row.tabIndex=0;
      const values=[new Date(e.time*1000).toLocaleString(),names[e.action],e.side==='long'?'多':'空',fmt(e.price),e.quantity??'未知',e.pnl===null||e.pnl===undefined?'—':fmt(e.pnl,2),e.reason||''];
      values.forEach(v=>{const cell=document.createElement('td');cell.textContent=String(v);row.appendChild(cell);});
      row.onclick=()=>focus(e);row.onkeydown=event=>{if(event.key==='Enter')focus(e);};body.appendChild(row);
    });
  }
  function focus(e){
    if(!Number.isFinite(e.chart_time)){document.getElementById('bt-selected').textContent='该成交不在现有行情范围内；旧任务可能需要重跑以保存行情快照。';return;}
    const times=payload.candles.map(c=>c.t);const i=times.indexOf(e.chart_time);
    btChart.timeScale().setVisibleLogicalRange({from:Math.max(-1,i-24),to:Math.min(times.length,i+24)});
    if(priceLine)btSeries.removePriceLine(priceLine);
    priceLine=Number.isFinite(e.price)?btSeries.createPriceLine({price:e.price,color:'#58a6ff',lineWidth:2,axisLabelVisible:true,title:names[e.action]}):null;
    document.getElementById('bt-selected').textContent=`${new Date(e.time*1000).toLocaleString()} ${names[e.action]} ${e.side==='long'?'多':'空'} @ ${fmt(e.price)}；${e.reason||''}`;
  }
  async function load(){
    const id=document.getElementById('bt-job').value,symbol=document.getElementById('bt-symbol').value,interval=document.getElementById('bt-interval').value;
    const msg=document.getElementById('bt-msg'),token=++sequence,newKey=[id,symbol,interval].join('|');
    if(!id||!symbol){msg.textContent='暂无已完成的回测，请先运行回测';return;}
    if(key===newKey&&payload){draw();return;}
    msg.textContent='正在加载回测行情与成交…';
    document.getElementById('bt-selected').textContent='';document.getElementById('bt-blocks').textContent='';
    try{
      const response=await fetch(`/api/backtest/job/${encodeURIComponent(id)}/chart?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}`);
      const data=await response.json();if(token!==sequence)return;
      if(!response.ok||!data.ok)throw new Error(data.message||'请求失败');
      if(typeof LightweightCharts==='undefined')throw new Error('图表库未加载，请刷新页面；成交统计不受影响');
      if(!btChart){const built=makeChart('bt-chart');btChart=built.chart;btSeries=built.series;}
      if(priceLine){btSeries.removePriceLine(priceLine);priceLine=null;}
      const candles=ChartUtils.candles(data.candles);
      btSeries.setMarkers([]);btSeries.applyOptions({priceFormat:ChartUtils.priceFormat(candles)});btSeries.setData(candles);
      payload=data;key=newKey;draw();btChart.timeScale().fitContent();
      const s=data.summary;
      document.getElementById('bt-cards').innerHTML=[['完整持仓',s.position_count],['成交记录',data.events.length],['持仓胜率',fmt(s.win_rate_pct,2)+'%'],['最长连亏',s.max_loss_streak]].map(([label,value])=>`<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
      msg.textContent=`${symbol} ${interval} · ${data.source} · ${data.candles.length} 根 K 线 · ${data.events.length} 条${data.legacy?'可还原记录':'真实成交记录'}`+(data.legacy?'。旧任务未保存加仓和首次成交价，这些值标为未知；重跑可获得完整记录。':'')+(data.unmapped_events?`；${data.unmapped_events} 条记录缺少对应行情。`:'');
      if(!data.candles.length)msg.textContent+=' 没有可绘制的 K 线，请重跑该任务。';
      const blocks=data.execution_diagnostics?.entry_blocks||{};
      document.getElementById('bt-blocks').textContent=Object.keys(blocks).length?'空仓期间未入场原因（K线次数，同一机会可能持续多根）：'+Object.entries(blocks).sort((a,b)=>b[1]-a[1]).map(([reason,n])=>`${reason}：${n}`).join('；'):'旧任务没有记录未入场原因；重跑后可查看。';
      document.getElementById('bt-selected').textContent='点击下方成交记录，定位前后24根 K 线并显示成交价。';
    }catch(error){if(token===sequence){key='';payload=null;msg.textContent='回测图表加载失败：'+error.message;if(btSeries){btSeries.setMarkers([]);btSeries.setData([]);}document.querySelector('#bt-chart-trades tbody').replaceChildren();document.getElementById('bt-cards').replaceChildren();}}
  }
  function all(){if(btChart)btChart.timeScale().fitContent();}
  function latest(){const events=selectedEvents().filter(e=>Number.isFinite(e.chart_time));if(events.length)focus(events[events.length-1]);}
  const api={markers,load,draw,all,latest};
  if(typeof module!=='undefined')module.exports=api;
  else root.BacktestChart=api;
})(typeof window!=='undefined'?window:globalThis);
