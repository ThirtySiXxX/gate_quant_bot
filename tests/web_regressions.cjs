// Run with Node.js; exercises the shipped browser functions without third-party DOM packages.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const utils=require(path.join(root,'src/static/chart_utils.js'));
function element(){return {value:'',checked:false,disabled:false,style:{},children:[],textContent:'',innerHTML:'',
  replaceChildren(){this.children=[];this.textContent='';this.innerHTML='';},appendChild(x){this.children.push(x);},
  insertAdjacentHTML(_,html){this.innerHTML+=html;},addEventListener(){},focus(){this.focused=true;}};}
function dom(){const nodes=new Map();return {nodes,getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},
  querySelector(id){return this.getElementById(id);},createElement:element,addEventListener(){}};}
const response=data=>({ok:true,status:200,json:async()=>data});
const source=fs.readFileSync(path.join(root,'src/dashboard_web.py'),'utf8');
function script(page){const part=source.split(page+' = """')[1];return part.match(/<script>([\s\S]*?)<\/script>/)[1];}

async function main(){
  const rows=utils.candles([{t:7200,o:2,h:3,l:1,c:2},{t:3600,o:1,h:2,l:1,c:2},{t:7200,o:2,h:4,l:1,c:3}]);
  assert.deepEqual(rows.map(c=>c.time),[3600,7200]);assert.equal(rows[1].close,3);
  assert.throws(()=>utils.candles([{t:1,o:NaN,h:2,l:1,c:2}]),/K线数据无效/);
  assert.throws(()=>utils.candles([{t:1,o:3,h:2,l:1,c:2}]),/K线数据无效/);
  const marks=utils.liveMarkers([{side:'long',open_time:3601,close_time:7300,pnl:1},
    {side:'short',open_time:1,close_time:10800,pnl:-1}],rows,'1h',true);
  assert.deepEqual(marks.map(m=>m.time),[3600,7200]);
  assert.equal(utils.priceFormat([{low:0.00000013}]).precision,12);
  console.log('PASS chart sorting, duplicate replacement, invalid OHLC, marker alignment/range, small-price precision');

  const document=dom(),calls=[],timers=[];
  const context=vm.createContext({document,fetch:async(url,options)=>{calls.push([url,options?.method||'GET']);
    return response(url.includes('catalogue')?{ok:true,contracts:[{symbol:'SOL_USDT',crypto:true}]}:url.endsWith('/scan')?{status:'running'}:
      {status:'done',as_of:1,candidates:[{symbol:'ETH_USDT',side:'long',score:1,short_forecast:3,main_forecast:4,quality:.2,round_trip_cost_bps:12,turnover_24h:2e6}]});},
    setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){}});
  vm.runInContext(fs.readFileSync(path.join(root,'src/static/universe.js'),'utf8')+'\nglobalThis.ui=UniverseUI;',context);
  let catalogue;
  await context.ui.init(items=>{catalogue=items;});
  assert.equal(catalogue[0].symbol,'SOL_USDT');
  assert.equal(calls.filter(x=>x[1]==='POST').length,0);assert.equal(timers.length,0);
  assert.equal(document.getElementById('universe-apply').disabled,true);
  const click=document.getElementById('universe-refresh').onclick;
  await Promise.all([click(),click()]);assert.equal(calls.filter(x=>x[1]==='POST').length,1);
  await timers.shift()();assert.equal(document.getElementById('universe-rows').children.length,1);
  assert.equal(document.getElementById('universe-apply').disabled,false);
  console.log('PASS manual-only recommendations, duplicate-click guard, polling/result rendering');

  const pageDocument=dom();let status='running',detailCount=0,fail=false;
  const job=()=>({id:'test',status,finished_at:status==='done'?10:null,symbols:['ETH_USDT'],progress_pct:40,
    summary:status==='done'?{symbols:['ETH_USDT'],warnings:[],per_symbol:{},trade_count:2,return_pct:3}:null});
  const page=vm.createContext({document:pageDocument,fetch:async url=>{
    if(fail)throw new Error('offline');
    if(url==='/api/backtest/list')return response({jobs:[job()]});
    detailCount++;return response(job());
  }});
  vm.runInContext(script('PAGE').split("fetch('/api/version')")[0],page);
  vm.runInContext("BT_VIEW_JOB_ID='test';drawEquityCurve=()=>{};",page);
  await page.refreshBacktestList();assert.equal(detailCount,1);
  status='done';await page.refreshBacktestList();assert.equal(detailCount,2);
  assert.match(pageDocument.getElementById('bt-summary-grid').innerHTML,/累计复利收益/);
  await page.refreshBacktestList();assert.equal(detailCount,2);
  fail=true;await page.refreshBacktestList();assert.match(pageDocument.getElementById('bt-joblist').textContent,/加载失败/);
  fail=false;await page.refreshBacktestList();assert.match(pageDocument.getElementById('bt-joblist').innerHTML,/已完成/);
  console.log('PASS running-to-done refresh, stable completed view, request failure/recovery');

  // Each UI submission uses the search field alone, never the configured trading pool.
  const singleDocument=dom(),submitted=[],notices=[];
  const single=vm.createContext({document:singleDocument,URL,window:{location:{href:'http://localhost/?view=backtest'}},
    history:{replaceState(){}},fetch:async()=>{throw new Error('Unexpected request');}});
  vm.runInContext(script('PAGE').split("fetch('/api/version')")[0],single);
  single.toast=message=>notices.push(message);single.refreshBacktestList=async()=>{};
  let completeSubmission;
  single.api=async(url,options)=>{submitted.push(JSON.parse(options.body));return new Promise(resolve=>{completeSubmission=resolve;});};
  for(const [input,expected] of [['btc','BTC_USDT'],[' SOL/USDT ','SOL_USDT'],['DOGE-USDT','DOGE_USDT'],
    ['zecusdt','ZEC_USDT'],['NEWTOKEN42','NEWTOKEN42_USDT'],['1000PEPE_USDT','1000PEPE_USDT'],
    ['',''],['BTC,ETH',''],['BTC ETH',''],['../ETH',''],['币种','']])assert.equal(single.normalizeBacktestSymbol(input),expected);
  singleDocument.getElementById('bt-days').value='30';singleDocument.getElementById('bt-symbol-search').value='sol';
  const submission=single.startBacktest();await single.startBacktest();assert.equal(submitted.length,1);
  assert.deepEqual(submitted[0].symbols,['SOL_USDT']);assert.equal(singleDocument.getElementById('bt-symbol-search').value,'SOL_USDT');
  completeSubmission({ok:true,job_id:'sol-job'});await submission;assert.equal(singleDocument.getElementById('bt-run').disabled,false);
  for(const invalid of ['', 'BTC,ETH']){singleDocument.getElementById('bt-symbol-search').value=invalid;await single.startBacktest();}
  assert.equal(submitted.length,1);assert.match(notices.at(-1),/每次只能回测一个/);
  console.log('PASS single-symbol search normalization, independent selection, duplicate submission and invalid input guard');

  const searchDocument=dom(),search=vm.createContext({document:searchDocument});
  vm.runInContext(fs.readFileSync(path.join(root,'src/static/backtest_symbol_search.js'),'utf8')+'\nglobalThis.picker=BacktestSymbolSearch;',search);
  search.picker.init();search.picker.setContracts(['BNSOL_USDT','SOL_USDT','BTC_USDT','SOL_USDT'].map(symbol=>({symbol})));
  const input=searchDocument.getElementById('bt-symbol-search'),matches=searchDocument.getElementById('bt-symbol-matches');
  input.value='sol';input.oninput();assert.deepEqual(matches.children.map(x=>x.textContent),['SOL_USDT','BNSOL_USDT']);
  matches.children[0].onclick();assert.equal(input.value,'SOL_USDT');assert.equal(matches.hidden,true);
  input.value='missing';input.oninput();assert.match(matches.children[0].textContent,/没有匹配/);
  input.value='';input.oninput();assert.equal(matches.hidden,true);
  search.picker.setContracts([]);input.value='BTC';input.oninput();assert.match(matches.children[0].textContent,/直接输入/);
  console.log('PASS visible contract search, exact-match ranking, single selection, no-match and unavailable catalogue');

  // Adoption must refresh immediately; an older poll must not restore the external role.
  const ownerDocument=dom(),ownerRequests=[],ownerNotices=[];
  const owner=vm.createContext({document:ownerDocument,confirm:()=>true,
    fetch:(url,options)=>new Promise(resolve=>ownerRequests.push({url,options,resolve}))});
  vm.runInContext(script('PAGE').split("fetch('/api/version')")[0],owner);
  owner.toast=(message,ok)=>ownerNotices.push({message,ok});
  const ownerState=role=>({summary:{mode:'paper'},positions:[{symbol:'ETH_USDT',side:'long',role,size:10}],logs:[]});
  const oldPoll=owner.refresh();
  const ownerButton=element(),adoption=owner.adoptPos('ETH_USDT','long',ownerButton);
  await owner.adoptPos('ETH_USDT','long',ownerButton);
  assert.equal(ownerRequests.length,2);assert.equal(ownerButton.disabled,true);
  assert.equal(ownerRequests[1].url,'/api/positions/adopt');
  ownerRequests[1].resolve(response({ok:true,message:'已纳入策略管理'}));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(ownerRequests[2].url,'/api/state');
  ownerRequests[2].resolve(response(ownerState('primary')));await adoption;
  const adoptedHTML=ownerDocument.querySelector('#positions tbody').innerHTML;
  assert.match(adoptedHTML,/策略管理中/);assert.doesNotMatch(adoptedHTML,/纳入策略管理/);
  ownerRequests[0].resolve(response(ownerState('external')));await oldPoll;
  assert.equal(ownerDocument.querySelector('#positions tbody').innerHTML,adoptedHTML);
  assert.equal(ownerDocument.getElementById('ownership-notice').style.display,'none');
  const rejected=owner.adoptPos('ETH_USDT','long',ownerButton);
  ownerRequests[3].resolve({...response({ok:false,message:'登记失败'}),ok:false,status:409});
  await new Promise(resolve=>setImmediate(resolve));
  ownerRequests[4].resolve(response(ownerState('external')));await rejected;
  assert.match(ownerDocument.querySelector('#positions tbody').innerHTML,/外部持仓/);
  assert.equal(ownerButton.disabled,false);assert.equal(ownerNotices.at(-1).ok,false);
  console.log('PASS immediate ownership refresh, stale-poll guard, duplicate adoption and failed-persistence display');

  for (const [enabled,active,label] of [[false,false,'已关闭'],[true,false,'正常'],[true,true,'熔断中']]) {
    const update=owner.refresh();
    ownerRequests.at(-1).resolve(response({...ownerState('primary'),
      daily_loss_limit_enabled:enabled,circuit_breaker:active}));
    await update;
    const cards=ownerDocument.getElementById('summary-grid').innerHTML;
    assert.match(cards,new RegExp('日亏损熔断</div><div[^>]*>'+label));
  }
  console.log('PASS daily loss gate disabled, enabled and active status labels');

  // Real live-chart function: an older request completing late must not overwrite a new symbol.
  const liveDocument=dom(),pending=[];let lastData=[],fit=0;
  const series={setMarkers(){},applyOptions(){},setData(data){lastData=data;},removePriceLine(){},createPriceLine(){return {};}};
  const live=vm.createContext({document:liveDocument,ChartUtils:utils,LightweightCharts:{LineStyle:{Dashed:2}},
    fetch:async url=>url==='/api/state'?response({trades:[],positions:[]}):new Promise(resolve=>pending.push(resolve))});
  vm.runInContext(script('CHARTS_PAGE').split('(async function init(){')[0],live);
  live.built={chart:{timeScale:()=>({fitContent(){fit++;}})},series};
  vm.runInContext('makeChart=()=>built;',live);
  liveDocument.getElementById('live-symbol').value='ETH_USDT';liveDocument.getElementById('live-interval').value='1h';
  liveDocument.getElementById('live-limit').value='300';const first=live.loadLiveChart();
  liveDocument.getElementById('live-symbol').value='SOL_USDT';const second=live.loadLiveChart();
  pending[1](response({ok:true,candles:[{t:3600,o:1,h:2,l:1,c:2}]}));await second;
  pending[0](response({ok:true,candles:[{t:3600,o:100,h:200,l:100,c:200}]}));await first;
  assert.equal(lastData[0].close,2);assert.equal(fit,1);
  const failed=live.loadLiveChart();pending[2](response({ok:false,message:'network failed'}));await failed;
  assert.equal(lastData.length,0);assert.match(liveDocument.getElementById('live-msg').textContent,/network failed/);
  console.log('PASS live-chart request race, viewport fit, failure clears stale candles');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
