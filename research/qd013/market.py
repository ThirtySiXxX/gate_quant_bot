"""One native causal array pass, reusable immutable SQLite market cache.

Source decimal text and UTC-us survive separately from computed f64 observations.
No account state, model matrix or fitting. A cache hit never estimates anything.
"""
from dataclasses import asdict
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import math
import os
import sqlite3
import uuid
import numpy as np
import pandas as pd
from research.qd009 import streaming_ledger as sl
from research.qd010.economic_inputs import INSTRUMENTS,SYMBOLS,HOUR,US,InputGap
from research.qd010.joint_native_bridge import research_config
from research.qd011.codec import native_context,projection
from research.qd012.native import frame,aggregate,native_decimal
from src import strategy_signals,vol

SCHEMA='qd013.market-cache.v1'


def cache_identity(*,sources,code,config,scope):
    return dict(schema=SCHEMA,sources=sources,code=code,config=config,scope=scope,
                availability='closed_bar_strict_R_native_main_open_MARK_named_clock',decimal_codec='exact_text_and_f64_roundtrip')


class NativeSeries:
    def __init__(self,hours,funding):
        self.hours=hours;self.prepared={};self.prefix={};self.stats=dict(native_prepare_calls=0,covariance_series_calls=0,snapshots=0,cache_serializations=0)
        cfg=research_config();returns={};self.first=None
        for i,s in zip(INSTRUMENTS,SYMBOLS):
            rows=hours[i]
            if not rows or rows[0].open_us%(24*HOUR):raise InputGap('UTC_DAY_WARMUP_START_REQUIRED')
            first=rows[0].open_us
            if self.first is not None and first!=self.first:raise InputGap('JOINT_GRID_START_MISMATCH')
            self.first=first
            for n,r in enumerate(rows):
                if r.instrument_id!=i or r.open_us!=first+n*HOUR or r.close_us!=r.open_us+HOUR or r.available_us!=r.close_us:
                    raise InputGap('HOURLY_GAP_OR_AVAILABILITY_MISMATCH')
            end=rows[-1].close_us
            short=frame([dict(timestamp=r.open_us//US,open=r.open,high=r.high,low=r.low,close=r.close,volume=r.volume_contracts) for r in rows])
            main=frame(aggregate(rows,4*HOUR,end));daily=frame(aggregate(rows,24*HOUR,end))
            fs=funding[i]
            if not fs or any(a.source_us>=b.source_us for a,b in zip(fs,fs[1:])):raise InputGap('MISSING_OR_UNORDERED_FUNDING_PREFIX')
            f=pd.DataFrame([dict(timestamp=r.rate_available_us//US,funding_rate=projection(r.rate)) for r in fs])
            with native_context():p=strategy_signals.prepare_features(short,main,daily,f,28800,cfg)
            self.stats['native_prepare_calls']+=1;self.prepared[s]=p
            ret=vol.log_returns(main['close']);ret.index=main['timestamp'].values
            if not np.isfinite(ret.iloc[1:]).all():raise InputGap('COVARIANCE_RETURN_GAP')
            returns[s]=ret
            digest=hashlib.sha256(b'qd013.prefix.v1\n');prefix=[]
            for r in rows:digest.update(r.row_id.encode()+b'\n');prefix.append(digest.hexdigest())
            self.prefix[i]=prefix
        if not returns[SYMBOLS[0]].index.equals(returns[SYMBOLS[1]].index):raise InputGap('JOINT_COVARIANCE_GRID_MISMATCH')
        with native_context():times,mats,order=vol.ewma_covariance_series(pd.DataFrame(returns),lam=cfg.ewma_lambda)
        self.cov_times=np.asarray(times,dtype=np.int64)*US+4*HOUR
        self.covariances=[m*vol.BARS_PER_YEAR['4h'] for m in mats]
        self.stats['covariance_series_calls']=1

    def snapshot(self,at):
        if at%HOUR:raise InputGap('NONHOURLY_NATIVE_DECISION')
        ci=int(np.searchsorted(self.cov_times,at,side='right'))-1
        if ci<0:raise InputGap('COVARIANCE_WARMUP_UNAVAILABLE')
        cov=self.covariances[ci];result=[];cfg=research_config()
        if not np.isfinite(cov).all() or np.any(np.diag(cov)<=0):raise InputGap('NATIVE_COVARIANCE_UNAVAILABLE')
        for i,s in zip(INSTRUMENTS,SYMBOLS):
            p=self.prepared[s];n=(at-self.first)//HOUR
            if n<cfg.min_bars_short or n>len(self.hours[i]):raise InputGap('NATIVE_SHORT_PREFIX_UNAVAILABLE')
            si=n-1;mi=(at-self.first)//(4*HOUR)-1;ri=(at-self.first)//(24*HOUR)-1
            if mi+1<cfg.min_bars_main or ri<0:raise InputGap('NATIVE_MAIN_PREFIX_UNAVAILABLE')
            r=self.hours[i][si];tf=p['timing_features'][si]
            vals=dict(short=p['short_f'][si],main=p['main_f'][mi],vol=p['vol_ann'][mi],carry=p['carry_f'][mi],
                risk=p['adaptive_risk_multiplier'][si],efficiency=p['adaptive_efficiency_ratio'][si],range_vol_ratio=p['adaptive_vol_ratio'][si],
                cov_btc_btc=cov[0,0],cov_eth_eth=cov[1,1],cov_cross=cov[0,1],
                **{k:tf[k] for k in ('quality','extension','atr','recent_high','recent_low','bar_seconds')})
            if not all(math.isfinite(float(v)) for v in vals.values()):raise InputGap('NATIVE_REQUIRED_CELL_UNKNOWN')
            if vals['vol']<=0:raise InputGap('NATIVE_VOLATILITY_UNAVAILABLE')
            d={k:native_decimal(v) for k,v in vals.items()}
            d.update(instrument_id=i,available_us=at,main_open_us=int(p['main_ts'][mi])*US,close=r.close,volume=r.volume_contracts,
                long_run=int(tf['long_run']),short_run=int(tf['short_run']),source_ref='qd013-prefix:'+self.prefix[i][si],
                regime=str(p['regime'][ri]) if ri+1>=cfg.regime_ema_long+5 else 'range',regime_open_us=int(p['regime_ts'][ri])*US,
                regime_available_us=int(p['regime_ts'][ri])*US+24*HOUR,cov_available_us=int(self.cov_times[ci]),
                breakout_long=bool(tf['breakout_long']),breakout_short=bool(tf['breakout_short']),
                first_open_us=self.first,short_count=n,main_count=mi+1,regime_count=ri+1)
            result.append(d)
        self.stats['snapshots']+=1
        return result


class MarketCache:
    def __init__(self,path,identity):
        self.path=Path(path);self.key=sl.digest(identity);self.stats=dict(hits=0,gets=0,source_reads=0)
        self.db=sqlite3.connect('file:'+str(self.path.resolve())+'?mode=ro',uri=True)
        try:
            meta={k:json.loads(v) for k,v in self.db.execute('SELECT k,v FROM metadata')}
            if meta.get('state')!='COMPLETE' or meta.get('schema')!=SCHEMA or meta.get('key')!=self.key or meta.get('identity')!=identity:
                raise InputGap('CACHE_INCOMPLETE_OR_VERSION_MISMATCH')
            self.meta=meta
        except BaseException:self.db.close();raise
        self.stats['hits']=1

    @classmethod
    def build(cls,path,identity,records,*,write_budget=None):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():return cls(path,identity)
        temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.building')
        db=sqlite3.connect(temporary);count=0;digest=hashlib.sha256()
        try:
            db.execute('CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT)')
            db.execute('CREATE TABLE cells(kind TEXT,inst TEXT,at INTEGER,v BLOB,sha TEXT,PRIMARY KEY(kind,inst,at))')
            db.execute('INSERT INTO metadata VALUES (?,?)',('state',json.dumps('BUILDING')))
            for kind,inst,at,value in records:
                raw=sl.canonical_bytes(value);h=hashlib.sha256(raw).hexdigest();digest.update(sl.canonical_bytes([kind,inst,at,h]))
                if write_budget:write_budget(temporary,db,count,len(raw))
                db.execute('INSERT INTO cells VALUES (?,?,?,?,?)',(kind,inst,at,raw,h));count+=1
            meta=dict(state='COMPLETE',schema=SCHEMA,key=sl.digest(identity),identity=identity,rows=count,content_sha256=digest.hexdigest())
            for k,v in meta.items():db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(k,json.dumps(v,sort_keys=True)))
            db.commit();db.close()
            with temporary.open('rb') as f:os.fsync(f.fileno())
            # Exclusive publication: hard link refuses a concurrent replacement;
            # the temporary remains until the complete inode is published.
            try:os.link(temporary,path)
            except FileExistsError:pass
            else:
                fd=os.open(path.parent,os.O_RDONLY)
                try:os.fsync(fd)
                finally:os.close(fd)
            temporary.unlink()
            return cls(path,identity)
        except BaseException:
            db.close()  # failed .building evidence remains; never a cache hit
            raise

    def get(self,kind,inst,at):
        self.stats['gets']+=1;row=self.db.execute('SELECT v,sha FROM cells WHERE kind=? AND inst=? AND at=?',(kind,inst,at)).fetchone()
        if row is None:raise InputGap('CACHE_CELL_MISSING:'+kind+':'+inst+':'+str(at))
        if hashlib.sha256(row[0]).hexdigest()!=row[1]:raise InputGap('CACHE_CELL_CORRUPTION')
        return sl.load_json(row[0])

    def records(self,kind):
        for inst,at,raw,h in self.db.execute('SELECT inst,at,v,sha FROM cells WHERE kind=? ORDER BY at,inst',(kind,)):
            if hashlib.sha256(raw).hexdigest()!=h:raise InputGap('CACHE_CELL_CORRUPTION')
            yield inst,at,sl.load_json(raw)

    def close(self):self.db.close()
