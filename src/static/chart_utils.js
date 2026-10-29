/* Common chart data rules, shared by live and backtest views. */
(function(root){
  const seconds={'1m':60,'5m':300,'15m':900,'30m':1800,'1h':3600,'4h':14400,'8h':28800,'1d':86400};
  function candles(rows){
    const unique=new Map();
    for(const c of rows){
      const values=[c.t,c.o,c.h,c.l,c.c];
      if(!values.every(Number.isFinite)||!Number.isInteger(c.t)||c.t<0||Math.min(c.o,c.h,c.l,c.c)<=0||c.h<Math.max(c.o,c.c,c.l)||c.l>Math.min(c.o,c.c)){
        throw new Error('K线数据无效，请重新下载该区间');
      }
      unique.set(c.t,{time:c.t,open:c.o,high:c.h,low:c.l,close:c.c});
    }
    return [...unique.values()].sort((a,b)=>a.time-b.time);
  }
  function priceFormat(rows){
    const price=rows.length?Math.min(...rows.map(c=>c.low)):1;
    const precision=Math.max(2,Math.min(12,5-Math.floor(Math.log10(price))));
    return {type:'price',precision,minMove:10**-precision};
  }
  function liveMarkers(trades,rows,interval,showText){
    const span=seconds[interval], times=new Set(rows.map(c=>c.time)), markers=[];
    if(!span)return markers;
    for(const t of trades){
      const long=t.side==='long';
      for(const [at,opening] of [[t.open_time,true],[t.close_time,false]]){
        if(!Number.isFinite(at))continue;
        const time=Math.floor(at/span)*span;
        if(!times.has(time))continue;
        markers.push({time,position:opening===long?'belowBar':'aboveBar',
          color:opening?(long?'#3fb950':'#f85149'):(t.pnl>=0?'#3fb950':'#f85149'),
          shape:opening===long?'arrowUp':'arrowDown',
          text:showText?(opening?'开':'平')+(long?'多':'空'):''});
      }
    }
    return markers.sort((a,b)=>a.time-b.time);
  }
  const api={seconds,candles,priceFormat,liveMarkers};
  if(typeof module!=='undefined')module.exports=api;else root.ChartUtils=api;
})(typeof window!=='undefined'?window:globalThis);
