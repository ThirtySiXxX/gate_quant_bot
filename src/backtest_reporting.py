"""Read-only presentation of exact fills and clearly labelled legacy records."""
from collections import Counter
from bisect import bisect_right
from .data_fetcher import INTERVAL_SECONDS


def position_summary(trades, executions=None):
    groups = {}
    for trade in trades:
        key = (trade['symbol'], trade['open_time'], trade['side'])
        row = groups.setdefault(key, {'pnl': 0., 'close_time': 0.})
        row['pnl'] += trade['pnl']
        row['close_time'] = max(row['close_time'], trade['close_time'])
    streaks = {}; longest = 0
    for key, row in sorted(groups.items(), key=lambda item:item[1]['close_time']):
        symbol = key[0]
        streaks[symbol] = streaks.get(symbol, 0) + 1 if row['pnl'] < 0 else 0
        longest = max(longest, streaks[symbol])
    counts = Counter(e['action'] for e in executions) if executions is not None else {}
    return {'position_count':len(groups), 'closed_leg_count':len(trades),
            'win_rate_pct':sum(r['pnl'] > 0 for r in groups.values())/len(groups)*100 if groups else 0.,
            'max_loss_streak':longest, 'fill_count':len(executions) if executions is not None else None,
            'open_count':counts.get('open',0) if executions is not None else len(groups),
            'add_count':counts.get('add',0) if executions is not None else None,
            'reduce_count':counts.get('reduce',0) if executions is not None else None,
            'close_count':counts.get('close',0) if executions is not None else None}


def legacy_events(trades):
    """No first-entry price/size can be recovered after weighted adds. Do not invent it."""
    events=[];seen=set()
    for trade in sorted(trades,key=lambda t:t['close_time']):
        key=(trade['symbol'],trade['open_time'],trade['side'])
        common={'symbol':trade['symbol'],'side':trade['side'],'quantity':None,'estimated':True}
        if key not in seen:
            events.append(dict(common,time=trade['open_time'],bar_time=trade['open_time'],price=None,
                               action='open',pnl=None,reason='旧版仅保存入场时间，首次成交价及加仓记录不可恢复'))
            seen.add(key)
        action='reduce' if '减仓' in trade.get('reason','') else 'close'
        events.append(dict(common,time=trade['close_time'],bar_time=trade['close_time'],price=trade['exit_price'],
                           action=action,pnl=trade['pnl'],reason=trade.get('reason','')))
    return [dict(e,id=i) for i,e in enumerate(sorted(events,key=lambda e:e['time']))]


def chart_payload(result, symbol, interval, cached=None):
    seconds=INTERVAL_SECONDS.get(interval)
    if seconds is None:raise ValueError('不支持的 K 线周期')
    source=result.get('chart_candles',{}).get(symbol)
    from_snapshot=source is not None
    source_seconds=INTERVAL_SECONDS.get(result.get('short_interval','1h'),3600)
    if from_snapshot:
        if seconds < source_seconds or seconds % source_seconds:
            raise ValueError('所选周期小于本次回测保存的行情粒度，无法还原')
    else:
        source=cached or []
        source_seconds=seconds
    buckets={}
    for candle in sorted(source,key=lambda c:c['t']):
        t=int(candle['t']//seconds)*seconds
        row=buckets.get(t)
        if row is None: buckets[t]=dict(candle,t=t)
        else:
            row['h']=max(row['h'],candle['h']);row['l']=min(row['l'],candle['l']);row['c']=candle['c']
    candles=list(buckets.values());times=[c['t'] for c in candles]
    exact=result.get('schema_version',0)>=2 and 'executions' in result
    raw=result.get('executions',[]) if exact else legacy_events(result.get('trades',[]))
    events=[]
    for original in raw:
        if original['symbol']!=symbol:continue
        e=dict(original);at=e.get('bar_time',e['time']);index=bisect_right(times,at)-1
        e['chart_time']=times[index] if index>=0 and at<times[index]+seconds else None
        events.append(e)
    trades=[t for t in result.get('trades',[]) if t['symbol']==symbol]
    return {'ok':True,'candles':candles,'events':events,'summary':position_summary(trades,[e for e in raw if e['symbol']==symbol] if exact else None),
            'legacy':not exact, 'source':'本次回测行情快照' if from_snapshot else '共享行情缓存（旧版任务）',
            'execution_diagnostics':result.get('execution_diagnostics',{}).get(symbol,{}),
            'unmapped_events':sum(e['chart_time'] is None for e in events)}
