"""Offline qf009 schema3 candidate. Stdlib only; no app, exchange or model import.

Authoritative commits are immutable canonical journals plus an fsynced HEAD.
SQLite is a rebuildable, hash-checked persistent-node index, not a second HEAD.
No operation materializes the lifetime record journal to remove the r3 cap.
"""
from __future__ import annotations
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import bisect
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
import weakref
import ctypes
import _sqlite3
import math
import zlib

NS = 'qf009.streaming-ledger'
PROFILE = 'qf009-offline-stream-r3'
VERSION = 3
REFERENCE_SHA256 = '7c1a08c569b79618b6de3092e297ef1ed1a51b54da29d62e76e7e2c900620636'
CONTRACT_SHA256 = '0db8014d162ec56f85eddafe289c869c8326f0ea5cbd226aef693050f259a745'
REFERENCE_PATH = Path(__file__).resolve().parents[1] / 'qd007/event_ledger.py'
if hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() != REFERENCE_SHA256:
    raise RuntimeError('pinned r3 source changed')
_spec = importlib.util.spec_from_file_location('_qf009_pinned_r3', REFERENCE_PATH)
_ref = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ref)
INSTRUMENTS = _ref.INSTRUMENTS
COMPONENTS = ('lots','closed_slices','obligations','entries','links','events','registry',
              'adapter_states','orders','decisions','query_status','reserve_dependencies')
ECONOMIC = tuple(c for c in COMPONENTS if c not in ('events','registry'))
TRANSPORT = {'namespace','schema_version','created_at_us','source_refs'}
PURPOSES = ('decision','funding_snapshot','permitted_fill','valuation','reservation','booking','finality_check')
QUERY_REASONS = ('MISSING_REQUIRED_MONTH','NO_ELIGIBLE_POINT','SOURCE_TOO_OLD','AVAILABLE_TOO_OLD','UNRESOLVED_SOURCE_OR_RULE')
LIMITS = dict(max_transaction_records=4096,max_transaction_bytes=8*1024**2,
 max_page_items=256,max_page_bytes=2*1024**2,max_resident_cache_bytes=8*1024**2,
 max_exact_integer_bits=8192,max_adapter_reads=262144,max_adapter_emitted_events=64,
 max_adapter_input_bytes=32*1024**2,max_adapter_state_bytes=2*1024**2,
 max_adapter_wall_us=10000000,max_store_bytes=512*1024**2,max_wall_us=60000000,
 whole_history_record_ceiling=None,null_reasons={'whole_history_record_ceiling':'STORAGE_BOUNDED_NOT_RECORD_TRUNCATED'})
_clock = time.monotonic


class LedgerError(ValueError):
    def __init__(self, code, path='/', **details):
        super().__init__(code+' at '+path)
        self.code, self.path = code, path
        self.receipt = dict(code=code,path=path,request_id=None,before=None,input_sha256=None,
                            disposition='reject',null_reasons={'request_id':'UNKNOWN_INPUT_IDENTITY',
                            'before':'NO_COMMITTED_LEDGER','input_sha256':'NONCANONICAL_INPUT'})
        self.receipt.update(details)


def need(ok, code='SCHEMA_VIOLATION', path='/'):
    if not ok: raise LedgerError(code,path)


def shape(x, fields, path='/'):
    need(type(x) is dict and set(x)==set(fields.split() if isinstance(fields,str) else fields),path=path)


def integer(x, low=0):
    need(type(x) is int and low<=x<=2**63-1,'INTEGER_CONTRACT_VIOLATION')
    return x


def ident(x):
    need(type(x) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}',x),'INVALID_ID')
    return x


def strict_json(x):
    if x is None or type(x) in (str,bool,int): return
    if type(x) is list:
        for v in x: strict_json(v)
    elif type(x) is dict:
        for k,v in x.items(): need(type(k) is str,'JSON_KEY_TYPE');strict_json(v)
    else: raise LedgerError('NONCANONICAL_INPUT')


def canonical_bytes(x):
    strict_json(x)
    return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def digest(x): return hashlib.sha256(canonical_bytes(x)).hexdigest()


def load_json(raw):
    def pairs(items):
        d={}
        for k,v in items: need(k not in d,'NONCANONICAL_INPUT');d[k]=v
        return d
    try:
        return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(LedgerError('NONCANONICAL_INPUT')))
    except (ValueError,TypeError) as e:
        if isinstance(e,LedgerError): raise
        raise LedgerError('NONCANONICAL_INPUT') from e


def number(x, minimum=None):
    need(type(x) is str and re.fullmatch(r'[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?',x),'INVALID_DECIMAL')
    need(sum(c.isdigit() for c in x)<=128 and (len(x.split('.')[1]) if '.' in x else 0)<=64,'DECIMAL_BOUNDS')
    f=Fraction(x);need(minimum is None or f>=minimum,'DECIMAL_DOMAIN');return f


def fmt(n):
    n=Fraction(n)
    if not n: return '0'
    d=n.denominator;a=b=0
    while d%2==0: d//=2;a+=1
    while d%5==0: d//=5;b+=1
    need(d==1,'NONTERMINATING_AMOUNT')
    scale=max(a,b);s=str(abs(n.numerator)*2**(scale-a)*5**(scale-b)).rjust(scale+1,'0')
    return ('-' if n<0 else '')+(s if not scale else (s[:-scale]+'.'+s[-scale:]).rstrip('0').rstrip('.'))


def key_of(r): return {k:r[k] for k in ('instrument_id','record_type','record_id','revision')}
def wire_key(r): return (r['instrument_id'],r['record_type'],r['record_id'],r['revision'])
def economic_time(r):
    return r[{'Fill':'filled_at_us','FundingSnapshot':'snapshot_at_us','ObligationRevision':'economic_at_us',
              'Posting':'booking_at_us','Valuation':'valuation_at_us','Reserves':'effective_at_us',
              'CompletenessAssertion':'asserted_at_us'}[r['record_type']]]

def normalize_body(body):
    need(not(set(body)&TRANSPORT),'SCHEMA_VIOLATION')
    r=dict(body,namespace=_ref.NS,schema_version=1,created_at_us=body['available_at_us'],
           source_refs=[dict(manifest_sha256='0'*64,source_id='validated-external-binding',source_row=1)])
    try: r=_ref.validate_record(r)
    except _ref.LedgerError as e: raise LedgerError(e.code,e.json_pointer) from e
    return {k:v for k,v in r.items() if k not in TRANSPORT}


def allocate(total, weights, quantum):
    # Public pinned arithmetic; no reference Ledger, record scan or cap mutation.
    try: return _ref.allocate_pro_rata(fmt(total),weights,fmt(quantum))
    except _ref.LedgerError as e: raise LedgerError(e.code) from e


def ordered_key(k):
    return tuple(k)


class ResourceBudget:
    """Audit-only, pre-write quota and conservatively durable I/O debit.

    Byte debit means bytes issued to file/VFS xWrite, including DB and rollback
    journal overwrites, not an inference about storage-device amplification.
    Grants survive a crash; unused grant is never silently reset on reopen.
    """
    def __init__(self,root,limit,book=None,reserve=262144):
        self.root=Path(root).resolve();self.limit=limit;self.reserve=min(reserve,limit//8)
        self.book=Path(book or self.root/'RESOURCE_LOG');self.sizes={};self.total=0;self.written=0;self.grant=0;self.last_error=None;self.emergency=False
        self.book.parent.mkdir(parents=True,exist_ok=True);self.previous='0'*64
        if self.book.exists():
            with self.book.open('rb') as source:
                for raw in source:
                    row=load_json(raw);h=row.pop('hash');need(row['previous']==self.previous and digest(row)==h,'STORE_INTEGRITY_FAILURE');self.previous=h
                    self.grant=max(self.grant,row.get('write_upper',0))
                    if row['kind']=='size':self.sizes[row['path']]=row['size']
                    elif row['kind']=='write_grant':self.grant=row['value']
            self.written=self.grant
        for p in self.root.rglob('*'):
            if p.is_file() and p!=self.book:self.sizes[str(p)]=max(self.sizes.get(str(p),0),p.stat().st_size)
        self.total=sum(self.sizes.values());self.parent=None

    def _append(self,kind,**values):
        self.grant=max(self.grant,math.ceil((self.written+4096)/1048576)*1048576)
        row=dict(kind=kind,previous=self.previous,write_upper=self.grant,**values);h=digest(row);raw=canonical_bytes(dict(row,hash=h))+b'\n'
        current=self.book.stat().st_size if self.book.exists() else 0
        need(self.total+current+len(raw)<=self.limit,'RESOURCE_EXHAUSTED','/resource_book')
        if self.parent:self.parent.issue(self.book,current+len(raw),len(raw))
        with self.book.open('ab') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        self.written+=len(raw);self.previous=h

    def issue(self,path,end,amount=0):
        path=str(Path(path).resolve()) if path is not None else str(self.root/'anonymous-sqlite-temp')
        old=self.sizes.get(path,0);end=max(end,old)
        rounded=math.ceil(end/65536)*65536 if path.endswith(('.sqlite3','-journal','-wal','-shm')) else end
        overhead=self.book.stat().st_size if self.book.exists() else 0
        need(self.total+rounded-old+overhead<=self.limit-(0 if self.emergency else self.reserve),'RESOURCE_EXHAUSTED','/prewrite_quota')
        if self.parent:self.parent.issue(path,end,amount)
        if rounded>old:
            self._append('size',path=path,size=rounded);self.sizes[path]=rounded;self.total+=rounded-old
        if self.written+amount>self.grant:
            grant=max(self.grant+1048576,self.written+amount+4096);self._append('write_grant',value=grant);self.grant=grant
        self.written+=amount

    def release(self,path):
        path=str(Path(path).resolve());old=self.sizes.get(path,0)
        if old:self._append('size',path=path,size=0);self.sizes[path]=0;self.total-=old
        if self.parent:self.parent.release(path)

    def rename(self,source,dest):
        source,dest=str(Path(source).resolve()),str(Path(dest).resolve());size=self.sizes.get(source,0)
        self.release(dest);self._append('size',path=dest,size=size);self.sizes[dest]=size;self.total+=size;self.release(source)


_BUDGETS={}
_GLOBAL_BUDGET=None

def configure_resource_budget(root,live_bytes):
    global _GLOBAL_BUDGET
    _GLOBAL_BUDGET=ResourceBudget(root,live_bytes,Path(root)/'aggregate-resource.jsonl',1048576)
    return _GLOBAL_BUDGET


def _budget_for(path):
    p=Path(path).resolve()
    for root,b in sorted(_BUDGETS.items(),key=lambda x:len(x[0]),reverse=True):
        if p.is_relative_to(Path(root)):return b
    return _GLOBAL_BUDGET if _GLOBAL_BUDGET and p.is_relative_to(_GLOBAL_BUDGET.root) else None


# A transparent VFS method-table shim observes SQLite's actual write requests
# before they reach the OS. Other methods, locking and sync are delegated intact.
# Struct layout comes from the installed sqlite3.h, versions1..3 only.
class _IOMethods(ctypes.Structure):
    _fields_=[('version',ctypes.c_int)]+[(n,ctypes.c_void_p) for n in ('close','read','write','truncate','sync','size','lock','unlock','reserved','control','sector','device','shmmap','shmlock','shmbarrier','shmunmap','fetch','unfetch')]
class _VFS(ctypes.Structure):
    _fields_=[('version',ctypes.c_int),('file_size',ctypes.c_int),('max_path',ctypes.c_int),('next',ctypes.c_void_p),('name',ctypes.c_char_p),('app',ctypes.c_void_p)]+[(n,ctypes.c_void_p) for n in ('open','delete','access','fullpath','dlopen','dlerror','dlsym','dlclose','random','sleep','time','error','time64','setsys','getsys','nextsys')]
_SQL=ctypes.CDLL(_sqlite3.__file__);_SQL.sqlite3_vfs_find.argtypes=[ctypes.c_char_p];_SQL.sqlite3_vfs_find.restype=ctypes.POINTER(_VFS)
_SQL.sqlite3_vfs_register.argtypes=[ctypes.POINTER(_VFS),ctypes.c_int];_SQL.sqlite3_vfs_register.restype=ctypes.c_int
_PARENT_VFS=_SQL.sqlite3_vfs_find(None)
need(bool(_PARENT_VFS) and _PARENT_VFS.contents.version==3,'STORE_INTEGRITY_FAILURE')
_BUDGET_VFS=_VFS.from_buffer_copy(_PARENT_VFS.contents);_BUDGET_VFS.name=b'qd009-budget-v1';_BUDGET_VFS.next=None
_VFS_FILES={};_VFS_CALLBACKS=[];_VFS_FAILURE=None

def _c_boundary(function):
    def callback(*args):
        global _VFS_FAILURE
        try:return function(*args)
        except BaseException as error:_VFS_FAILURE=error;return 10
    return callback

def _vfs_error():
    global _VFS_FAILURE
    if _VFS_FAILURE is not None:
        error=_VFS_FAILURE;_VFS_FAILURE=None;raise error
_W=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int64)
_T=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_int64)
_C=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p)
_FC=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p)
_O=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.POINTER(ctypes.c_int))
_D=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int)
_ORIG_OPEN=_O(_PARENT_VFS.contents.open);_ORIG_DELETE=_D(_PARENT_VFS.contents.delete)

def _vfs_open(vfs,name,file,flags,out):
    rc=_ORIG_OPEN(ctypes.cast(_PARENT_VFS,ctypes.c_void_p),name,file,flags,out)
    if rc:return rc
    path=ctypes.string_at(name).decode() if name else None;budget=_budget_for(path) if path else _GLOBAL_BUDGET
    if budget is None:return rc
    pointer=ctypes.cast(file,ctypes.POINTER(ctypes.c_void_p));original=_IOMethods.from_buffer_copy(_IOMethods.from_address(pointer[0]));table=_IOMethods.from_buffer_copy(original)
    write,truncate,close,control=_W(original.write),_T(original.truncate),_C(original.close),_FC(original.control)
    def checked_write(f,data,amount,offset):
        try:budget.issue(path,offset+amount,amount)
        except LedgerError as e:
            budget.last_error=e;budget.emergency=True
            if budget.parent:budget.parent.emergency=True
            return 13
        return write(f,data,amount,offset)
    def checked_truncate(f,length):
        try:budget.issue(path,length)
        except LedgerError as e:
            budget.last_error=e;budget.emergency=True
            if budget.parent:budget.parent.emergency=True
            return 13
        result=truncate(f,length)
        if result==0 and length==0 and path:budget.release(path)
        return result
    def checked_control(f,operation,arg):
        if operation==6:return 12  # optional chunk preallocation cannot bypass quota
        if operation==5 and arg:
            target=ctypes.cast(arg,ctypes.POINTER(ctypes.c_int64))[0]
            try:
                current=Path(path).stat().st_size if path and Path(path).exists() else 0
                budget.issue(path,target,max(0,target-current))
            except LedgerError as e:
                budget.last_error=e;budget.emergency=True
                if budget.parent:budget.parent.emergency=True
                return 13
        return control(f,operation,arg)
    def checked_close(f):
        result=close(f);_VFS_FILES.pop(int(f),None)
        if path is None:budget.release(budget.root/'anonymous-sqlite-temp')
        return result
    callbacks=(_W(_c_boundary(checked_write)),_T(_c_boundary(checked_truncate)),_C(_c_boundary(checked_close)),_FC(_c_boundary(checked_control)));table.control=ctypes.cast(callbacks[3],ctypes.c_void_p).value;table.write=ctypes.cast(callbacks[0],ctypes.c_void_p).value;table.truncate=ctypes.cast(callbacks[1],ctypes.c_void_p).value;table.close=ctypes.cast(callbacks[2],ctypes.c_void_p).value
    _VFS_FILES[int(file)]=(original,table,callbacks);pointer[0]=ctypes.addressof(table);return 0

def _vfs_delete(vfs,name,sync):
    result=_ORIG_DELETE(ctypes.cast(_PARENT_VFS,ctypes.c_void_p),name,sync)
    if result==0:
        budget=_budget_for(name.decode())
        if budget:budget.release(name.decode())
    return result
_VFS_CALLBACKS.extend((_O(_c_boundary(_vfs_open)),_D(_c_boundary(_vfs_delete))))
_BUDGET_VFS.open=ctypes.cast(_VFS_CALLBACKS[0],ctypes.c_void_p).value;_BUDGET_VFS.delete=ctypes.cast(_VFS_CALLBACKS[1],ctypes.c_void_p).value
need(_SQL.sqlite3_vfs_register(ctypes.byref(_BUDGET_VFS),0)==0,'STORE_INTEGRITY_FAILURE')


class _BudgetConnection(sqlite3.Connection):
    def execute(self,*args,**kwargs):
        try:
            result=super().execute(*args,**kwargs);_vfs_error();return result
        except sqlite3.Error:
            _vfs_error();budget=getattr(self,'budget',None)
            if budget and budget.last_error:error=budget.last_error;budget.last_error=None;raise error
            raise
    def commit(self):
        try:
            result=super().commit();_vfs_error();return result
        except sqlite3.Error:
            _vfs_error();budget=getattr(self,'budget',None)
            if budget and budget.last_error:error=budget.last_error;budget.last_error=None;raise error
            raise


def _sql_hash(value):return bytes.fromhex(value)
def _wire_hash(value):return value.hex() if isinstance(value,bytes) else value

def _unpack_node(raw):
    decoder=zlib.decompressobj();value=decoder.decompress(raw,8*1024**2+1)
    need(len(value)<=8*1024**2 and decoder.eof and not decoder.unused_data,'STORE_INTEGRITY_FAILURE');return value


def _resident_size(value):
    return sys.getsizeof(value)+(sum(_resident_size(k)+_resident_size(v) for k,v in value.items()) if isinstance(value,dict) else sum(_resident_size(v) for v in value) if isinstance(value,(list,tuple)) else 0)


class _WorkingNode:
    """Unique copy-on-write node, never serialized into a public/root payload."""
    __slots__=('component','data','charge','__weakref__')
    def __init__(self,component,data,charge):self.component,self.data,self.charge=component,data,charge


class NodeIndex:
    """Disk-backed immutable content-addressed treap with bounded resident cache."""
    def __init__(self,path,cache_bytes):
        self.db=sqlite3.connect(Path(path).resolve().as_uri()+'?vfs=qd009-budget-v1',uri=True,factory=_BudgetConnection)
        self.db.budget=_budget_for(path)
        self.db.execute('PRAGMA journal_mode=DELETE');self.db.execute('PRAGMA synchronous=EXTRA')
        sql_cache=max(1024,min(1024**2,cache_bytes//4))
        self.db.execute('PRAGMA cache_size=-'+str(max(1,sql_cache//1024)));self.db.execute('PRAGMA temp_store=FILE');self.db.execute('PRAGMA mmap_size=0')
        self.db.execute('CREATE TABLE IF NOT EXISTS blobs(h TEXT PRIMARY KEY,b BLOB NOT NULL,born INTEGER) WITHOUT ROWID')
        self.db.execute('CREATE TABLE IF NOT EXISTS nodes(h TEXT PRIMARY KEY,c TEXT,k TEXT,p TEXT,v TEXT,l TEXT,r TEXT,n INTEGER,born INTEGER) WITHOUT ROWID')
        self.birth=0;self._empties={};self.work_bytes=0;self.work_peak=0
        self.cache=OrderedDict();self.size=0;self.cap=max(0,cache_bytes-sql_cache)
        self.visits=0;self.writes=0;self.working_visits=0;self.immutable_visits=0

    def empty(self,c):
        if c not in self._empties:self._empties[c]=digest([c,'empty'])
        return self._empties[c]

    def _evict(self):
        while self.cache and self.size+self.work_bytes>self.cap:
            _,(_,used)=self.cache.popitem(last=False);self.size-=used

    def _remember(self,h,node):
        n=_resident_size(node)+sys.getsizeof(h)+256
        if h in self.cache:old=self.cache.pop(h);self.size-=old[1]
        if n<=self.cap:
            self.cache[h]=(node,n);self.size+=n;self._evict()

    def _release_work(self,charge):self.work_bytes-=charge[0]

    def _working(self,c,data):
        # A node value is detached once per batch, not at every ancestor rewrite.
        owned=dict(data,k=list(data['k']),v=deepcopy(data['v']))
        charge=[512+_resident_size(owned['k'])+_resident_size(owned['p'])+_resident_size(owned['v'])]
        need(self.work_bytes+charge[0]<=self.cap,'RESOURCE_EXHAUSTED','/resident_index')
        self.work_bytes+=charge[0];self.work_peak=max(self.work_peak,self.work_bytes);self._evict()
        node=_WorkingNode(c,owned,charge);weakref.finalize(node,self._release_work,charge);return node

    def ensure_room(self,roots):
        if self.work_bytes>self.cap//2:
            self.freeze_roots(roots)

    def freeze_roots(self,roots):
        for c,h in list(roots.items()):roots[c]=self.freeze(c,h)

    def freeze(self,c,h):
        if not isinstance(h,_WorkingNode):return h
        n=h.data;l=self.freeze(c,n['l']);r=self.freeze(c,n['r']);v=n['v'];k=n['k']
        raw=canonical_bytes(v);vh=hashlib.sha256(raw).hexdigest();result=digest(['qf009.economic-node-v3',c,k,v,l,r])
        if result in self.cache:return result
        if self.db.execute('SELECT 1 FROM nodes WHERE h=?',(_sql_hash(result),)).fetchone():self.node(c,result);return result
        self.db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?,?)',(_sql_hash(vh),zlib.compress(raw,1),self.birth))
        self.db.execute('INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?,?,?,?)',(_sql_hash(result),c,zlib.compress(canonical_bytes(k),1),None,_sql_hash(vh),_sql_hash(l),_sql_hash(r),n['n'],self.birth))
        self.writes+=1;self._remember(result,dict(k=k,p=n['p'],v=v,l=l,r=r,n=n['n']));return result

    def node(self,c,h):
        if isinstance(h,_WorkingNode):self.visits+=1;self.working_visits+=1;return h.data
        if h==self.empty(c): return None
        self.visits+=1;self.immutable_visits+=1
        if h in self.cache:
            node,n=self.cache.pop(h);self.cache[h]=(node,n);return node
        row=self.db.execute('SELECT c,k,p,v,l,r,n FROM nodes WHERE h=?',(_sql_hash(h),)).fetchone()
        need(row is not None and row[0]==c,'STORE_INTEGRITY_FAILURE')
        cc,k,p,v,l,r,count=row;key=load_json(_unpack_node(k));p=digest(['qf009.index-priority-v3',c,key]);l=_wire_hash(l);r=_wire_hash(r)
        raw=self.db.execute('SELECT b FROM blobs WHERE h=?',(v,)).fetchone()
        if raw is not None:raw=(_unpack_node(raw[0]),)
        need(raw is not None and hashlib.sha256(raw[0]).hexdigest()==_wire_hash(v),'STORE_INTEGRITY_FAILURE')
        value=load_json(raw[0]);node=dict(k=key,p=p,v=value,l=l,r=r,n=count)
        need(digest(['qf009.economic-node-v3',c,key,value,l,r])==h,'STORE_INTEGRITY_FAILURE')
        self._remember(h,node);return node

    def put(self,c,k,v,l=None,r=None):
        l=self.empty(c) if l is None else l;r=self.empty(c) if r is None else r
        return self._working(c,dict(k=k,p=digest(['qf009.index-priority-v3',c,k]),v=v,l=l,r=r,n=1+self.count(c,l)+self.count(c,r)))

    def count(self,c,h):
        n=self.node(c,h);return n['n'] if n else 0

    def get(self,c,h,k,default=None):
        target=ordered_key(k)
        while (n:=self.node(c,h)) is not None:
            a=ordered_key(n['k'])
            if target==a:return deepcopy(n['v'])
            h=n['l' if target<a else 'r']
        return default

    def set(self,c,h,k,v):
        n=self.node(c,h)
        if n is None:return self.put(c,k,v)
        a,b=ordered_key(k),ordered_key(n['k'])
        if a==b and n['v']==v:return h
        w=h if isinstance(h,_WorkingNode) else self._working(c,n);n=w.data
        if a==b:
            charge=_resident_size(v)-_resident_size(n['v']);need(self.work_bytes+charge<=self.cap,'RESOURCE_EXHAUSTED','/resident_index')
            self.work_bytes+=charge;w.charge[0]+=charge;n['v']=deepcopy(v);self._evict();return w
        side='l' if a<b else 'r';child=self.set(c,n[side],k,v);n[side]=child;cn=self.node(c,child)
        n['n']=1+self.count(c,n['l'])+self.count(c,n['r'])
        if (cn['p'],ordered_key(cn['k']))<(n['p'],b):
            if not isinstance(child,_WorkingNode):child=self._working(c,cn);cn=child.data
            other='r' if side=='l' else 'l';n[side]=cn[other];n['n']=1+self.count(c,n['l'])+self.count(c,n['r'])
            cn[other]=w;cn['n']=1+self.count(c,cn['l'])+self.count(c,cn['r']);return child
        return w

    def floor(self,c,h,k):
        target=ordered_key(k);result=None
        while (n:=self.node(c,h)) is not None:
            if ordered_key(n['k'])<=target:result=(n['k'],n['v']);h=n['r']
            else:h=n['l']
        return (deepcopy(result[0]),deepcopy(result[1])) if result is not None else None

    def merge(self,c,l,r):
        a,b=self.node(c,l),self.node(c,r)
        if a is None:return r
        if b is None:return l
        if (a['p'],ordered_key(a['k']))<(b['p'],ordered_key(b['k'])):
            w=l if isinstance(l,_WorkingNode) else self._working(c,a);w.data['r']=self.merge(c,a['r'],r)
        else:
            w=r if isinstance(r,_WorkingNode) else self._working(c,b);w.data['l']=self.merge(c,l,b['l'])
        w.data['n']=1+self.count(c,w.data['l'])+self.count(c,w.data['r']);return w

    def delete(self,c,h,k):
        n=self.node(c,h)
        if n is None:return h
        a,b=ordered_key(k),ordered_key(n['k'])
        if a==b:return self.merge(c,n['l'],n['r'])
        w=h if isinstance(h,_WorkingNode) else self._working(c,n);side='l' if a<b else 'r'
        w.data[side]=self.delete(c,n[side],k);w.data['n']=1+self.count(c,w.data['l'])+self.count(c,w.data['r']);return w

    def items(self,c,h,after=None,prefix=None):
        stack=[];bound=ordered_key(after) if after is not None else None
        pre=tuple(prefix) if prefix is not None else None
        while stack or h!=self.empty(c):
            while (n:=self.node(c,h)) is not None:
                if bound is not None and ordered_key(n['k'])<=bound:
                    h=n['r'];continue
                if pre is not None and tuple(n['k'][:len(pre)])<pre:
                    h=n['r'];continue
                stack.append(n);h=n['l']
            if not stack:break
            n=stack.pop();h=n['r']
            if pre is not None and tuple(n['k'][:len(pre)])>pre:break
            yield deepcopy(n['k']),deepcopy(n['v'])

    def close(self):
        self.db.commit();self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()

    def prune(self,roots):
        # Discard only unreachable intermediate nodes born in this transaction.
        # Previously committed versions remain available for historical views.
        self.db.execute('CREATE TEMP TABLE IF NOT EXISTS retained(h TEXT PRIMARY KEY) WITHOUT ROWID')
        self.db.execute('DELETE FROM retained');stack=list(roots.items())
        while stack:
            c,h=stack.pop()
            if h==self.empty(c):continue
            row=self.db.execute('SELECT l,r,born FROM nodes WHERE h=?',(_sql_hash(h),)).fetchone()
            need(row is not None,'STORE_INTEGRITY_FAILURE')
            if row[2]!=self.birth:continue
            if self.db.execute('INSERT OR IGNORE INTO retained VALUES (?)',(_sql_hash(h),)).rowcount==0:continue
            stack.extend(((c,_wire_hash(row[0])),(c,_wire_hash(row[1]))))
            if c=='_timeline':stack.extend(self.node(c,h)['v'].items())
            if c=='_link_roots':stack.append(('links',self.node(c,h)['v']))
            if c=='_audit_ref_roots':stack.append(('_audit_refs',self.node(c,h)['v']))
        self.db.execute('DELETE FROM nodes WHERE born=? AND h NOT IN (SELECT h FROM retained)',(self.birth,))
        self.db.execute('DELETE FROM blobs WHERE born=? AND h NOT IN (SELECT v FROM nodes WHERE born=?)',(self.birth,self.birth))
        self.cache.clear();self.size=0


class State:
    def __init__(self,index,config,roots=None):
        self.index,self.config=index,config;self.roots=dict(roots or {})
        self.rules={r['rule_id']:r for r in config['rules']}
        self.at=(config['initial_at_us'],0)
        self.touched_slices=set();self.delta={};self.private_delta={};self.frames=[]

    def root(self,c):return self.roots.get(c,self.index.empty(c))
    def get(self,c,k,default=None):return self.index.get(c,self.root(c),list(k),default)
    def set(self,c,k,v):
        self.index.ensure_room(self.roots);self.roots[c]=self.index.set(c,self.root(c),list(k),v)
        if c in COMPONENTS:self.delta[(c,sl_key(k))]=(list(k),deepcopy(v))
        elif c in ('_owners','_dedup','_revisions','_assertion_versions','_snapshots'):self.private_delta[(c,sl_key(k))]=(list(k),deepcopy(v))
    def rows(self,c,after=None,prefix=None):return self.index.items(c,self.root(c),after,prefix)
    def meta(self,k,default=None):return self.get('_meta',[k],default)
    def putmeta(self,k,v):self.set('_meta',[k],v)

    def rule(self,rid,kind,inst,at):
        r=self.rules.get(rid)
        need(r is not None and r['kind']==kind and r['instrument_id']==inst and r['valid_from_us']<=at
             and (r['valid_to_exclusive_us'] is None or at<r['valid_to_exclusive_us']),'RULE_MISMATCH')
        return r['parameters']

    def one_rule(self,kind,inst,at):
        rs=[r for r in self.rules.values() if r['kind']==kind and r['instrument_id']==inst and r['valid_from_us']<=at
            and (r['valid_to_exclusive_us'] is None or at<r['valid_to_exclusive_us'])]
        need(len(rs)==1,'RULE_MISMATCH');return rs[0]['parameters']

    def own(self,kind,id,inst):
        v=[inst,self.config['trajectory_id'],self.config['scenario_id']]
        old=self.get('_owners',[kind,id]);need(old is None or old==v,'ID_SCOPE_CONFLICT')
        self.set('_owners',[kind,id],v)

    def reference(self,kind,id):return self.get('_lookup',[kind,id])
    def location(self,c,id):
        key=self.reference(c,id);return self.get(c,key) if key is not None else None
    def save(self,c,k,value,id=None):
        self.set(c,k,value)
        if id is not None:self.set('_lookup',[c,id],list(k))

    def link(self,owner,id,kind,value):
        identity=[owner,id,kind,sl_key(value)]
        if self.get('_link_seen',identity):return
        count=self.get('_link_counts',[owner,id],0)
        item=dict(owner_kind=owner,owner_id=id,ordinal=count,value=dict(kind=kind,**value))
        key=[owner,id,count];self.set('links',key,item);self.set('_link_counts',[owner,id],count+1);self.set('_link_seen',identity,True)
        root=self.get('_link_roots',[owner,id,kind],self.index.empty('links'))
        self.set('_link_roots',[owner,id,kind],self.index.freeze('links',self.index.set('links',root,key,item)))

    def link_root(self,owner,id,kind):return self.get('_link_roots',[owner,id,kind],self.index.empty('links'))

    def levels(self,o):
        if o['T'] is None:return (None,None,None)
        p=Fraction(o['T'])-Fraction(o['B']);return p,max(p,0),max(-p,0)

    def aggregate(self,o,delta):
        before=self.levels(o)
        for label,value in zip(('P','A','L'),before):
            if label=='P':continue
            k=label if value is not None else 'unknown_'+label
            v=Fraction(self.meta(k,'0')) if value is not None else self.meta(k,0)
            self.putmeta(k,fmt(v+delta*value) if value is not None else v+delta)

    def origin_ranges(self,oid):return self.get('_origins',[oid])
    def alloc_id(self,oid,u,inst):
        c=self.config;return digest([c['ledger_id'],c['trajectory_id'],c['scenario_id'],inst,oid,u['lot_id'],u['unit_start'],u['unit_end']])
    def allocations(self,oid,inst,ranges,total):
        vals=allocate(Fraction(total),[u['unit_end']-u['unit_start'] for u in ranges],Fraction(self.config['allocation_quantum_usdt']))
        return [dict(u,allocation_id=self.alloc_id(oid,u,inst),signed_cash_usdt=v) for u,v in zip(ranges,vals)]

    def check_alloc(self,allocs,oid,origin,total):
        pos=0;units=[]
        for base in origin['ranges']:
            cursor=base['unit_start']
            while pos<len(allocs) and allocs[pos]['lot_id']==base['lot_id'] and allocs[pos]['unit_start']<base['unit_end']:
                a=allocs[pos];pos+=1
                need(a['episode_id']==base['episode_id'] and a['unit_start']==cursor and a['unit_end']<=base['unit_end'],'ALLOCATION_MISMATCH')
                need(a['allocation_id']==self.alloc_id(oid,a,origin['instrument']),'ALLOCATION_ID_MISMATCH')
                cursor=a['unit_end'];units.append({k:a[k] for k in ('lot_id','episode_id','unit_start','unit_end')})
            need(cursor==base['unit_end'],'ALLOCATION_MISMATCH')
        need(pos==len(allocs),'ALLOCATION_MISMATCH')
        need(allocs==self.allocations(oid,origin['instrument'],units,total),'ALLOCATION_MISMATCH')

    def cash_entry(self,r,kind,oid,before,after,dc=Fraction(0),sl=None):
        self.putmeta('cash',fmt(Fraction(self.meta('cash',self.config['initial_cash_usdt']))+dc))
        origin=self.origin_ranges(oid) if oid else None
        eps={u['episode_id'] for u in origin['ranges']} if origin else {sl['episode_id']}
        ep=next(iter(eps)) if len(eps)==1 else None
        aid=digest([sl['slice_id'],'realized']) if sl else None
        nr={};ds={}
        for field,a,b in zip(('pending_delta_usdt','receivable_delta_usdt','liability_delta_usdt'),before,after):
            ds[field]=fmt(b-a) if a is not None and b is not None else None
            if ds[field] is None:nr[field]='UNKNOWN_OBLIGATION_TOTAL' if a is None and b is None else 'UNKNOWN_PRIOR_BALANCE' if a is None else 'UNKNOWN_CURRENT_BALANCE'
        if aid is None:nr['allocation_id']='AGGREGATE_OBLIGATION'
        if oid is None:nr['obligation_id']='NOT_APPLICABLE'
        if ep is None:nr['episode_id']='AGGREGATE_OBLIGATION'
        key=key_of(r);eid=digest([key,kind,oid if oid is not None else aid])
        e=dict(entry_id=eid,source_key=key,transition=kind,obligation_id=oid,allocation_id=aid,episode_id=ep,
               economic_at_us=origin['at'] if origin else r['filled_at_us'],available_at_us=r['available_at_us'],
               cash_delta_usdt=fmt(dc),realized_pnl_usdt=fmt(dc if sl else 0),null_reasons=nr,**ds)
        self.save('entries',[eid],e,eid)

    def live(self,inst):
        for _,lid in self.rows('_live',prefix=[inst]):
            lot=self.location('lots',lid)
            if lot and lot['remaining_contracts']:yield lot

    def unit(self,l,a,b):return dict(lot_id=l['lot_id'],episode_id=l['episode_id'],unit_start=a,unit_end=b)

    def save_lot(self,l):
        k=[l['instrument_id'],l['opened_at_us'],l['lot_id']]
        l['live_ranges']=[self.unit(l,l['initial_contracts']-l['remaining_contracts'],l['initial_contracts'])] if l['remaining_contracts'] else []
        self.save('lots',k,l,l['lot_id'])
        self.set('_ep_lots',[l['episode_id'],l['opened_at_us'],l['lot_id']],l['lot_id'])
        if l['remaining_contracts']:self.set('_live',k,l['lot_id'])
        else:self.roots['_live']=self.index.delete('_live',self.root('_live'),k)

    def save_ob(self,oid,o):
        orig=self.origin_ranges(oid)
        for allocation in o['allocations']:self.link('obligation',oid,'allocation',dict(id=allocation['allocation_id']))
        p,a,l=self.levels(o);nr={}
        for k,v in [('latest_revision',o['revision']),('T_usdt',o['T']),('P_usdt',p),('A_usdt',a),('L_usdt',l)]:
            if v is None:nr[k]='UNKNOWN_AMOUNT' if k=='latest_revision' else 'UNKNOWN_OBLIGATION_TOTAL'
        value=dict(instrument_id=orig['instrument'],obligation_id=oid,kind=orig['kind'],origin_id=orig['origin']['record_id'],
          latest_revision=o['revision'],T_usdt=o['T'],B_usdt=o['B'],P_usdt=fmt(p) if p is not None else None,
          A_usdt=fmt(a) if a is not None else None,L_usdt=fmt(l) if l is not None else None,
          allocation_ref_count=self.index.count('links',self.link_root('obligation',oid,'allocation')),allocation_refs_root=self.link_root('obligation',oid,'allocation'),
          posting_ref_count=o['posting_count'],posting_refs_root=self.link_root('obligation',oid,'posting'),null_reasons=nr)
        self.set('_ob',[oid],o);self.save('obligations',[orig['instrument'],oid],value,oid)
        for u in orig['ranges']:
            self.set('_lot_ob',[u['lot_id'],oid],True)
            self.set('_ep_ob',[u['episode_id'],oid],True)
            for _,sid in self.rows('_slice_lot',prefix=[u['lot_id']]):self.touched_slices.add(sid)

    def new_ob(self,r,oid,kind,ranges,total):
        need(self.origin_ranges(oid) is None,'OBLIGATION_ORIGIN_CONFLICT')
        orig=dict(instrument=r['instrument_id'],at=economic_time(r),origin=r,kind=kind,ranges=ranges)
        self.set('_origins',[oid],orig)
        o=dict(T=fmt(total) if total is not None else None,B='0',revision=1 if total is not None else None,
               allocations=self.allocations(oid,orig['instrument'],ranges,total) if total is not None else [],
               available=r['available_at_us'],known=r['available_at_us'],posting_count=0,posting_root=digest([]))
        self.aggregate(o,1);self.save_ob(oid,o)
        if o['revision']:self.set('_revisions',[oid,1],r)
        if kind=='fee':self.cash_entry(r,'fee_claim',oid,(Fraction(0),)*3,self.levels(o))

    def apply(self,body):
        r=normalize_body(body);typ=r['record_type'];inst=r['instrument_id'];at=economic_time(r)
        c=self.config
        need(inst in c['instruments'] and r['trajectory_id']==c['trajectory_id'] and r['scenario_id']==c['scenario_id'],'REFERENCE_SCOPE_MISMATCH')
        if typ in ('Fill','FundingSnapshot','ObligationRevision','Valuation','Reserves'):
            need(c['initial_at_us']<=at<c['end_exclusive_us'],'ORIGIN_OUT_OF_RANGE')
        key=list(wire_key(r));old=self.get('events',key)
        if old is not None:
            need(old['body']==r,{'ObligationRevision':'CONFLICTING_OBLIGATION_REVISION','Posting':'CONFLICTING_POSTING_REVISION'}.get(typ,'CONFLICTING_EVENT_REVISION'))
            return False
        self.own({'Fill':'fill','FundingSnapshot':'funding-event','ObligationRevision':'obligation','Posting':'posting','Valuation':'valuation','Reserves':'reserves','CompletenessAssertion':'assertion'}[typ],r['record_id'],inst)
        if typ=='Fill':self._fill(r)
        elif typ=='FundingSnapshot':self._snapshot(r)
        elif typ=='ObligationRevision':self._revision(r)
        elif typ=='Posting':self._posting(r)
        elif typ=='Valuation':
            self.rule(r['valuation_rule_id'],'valuation',inst,at);self.rule(r['multiplier_rule_id'],'multiplier',inst,at)
            same=self.get('_valuation_at',[inst,at],{'absent':True})
            need(same=={'absent':True} or same==r['mark_price'],'AMBIGUOUS_VALUATION')
            self.set('_valuation_at',[inst,at],r['mark_price'])
            self.set('_marks',[inst,at,r['available_at_us'],r['record_id']],r)
        elif typ=='Reserves':
            same=self.get('_reserve_at',[inst,at,r['available_at_us']])
            content=[r[k] for k in ('expires_at_us','reserved_margin_usdt','reserved_fees_usdt')]
            need(same is None or same==content,'AMBIGUOUS_RESERVES')
            self.set('_reserve_at',[inst,at,r['available_at_us']],content)
            self.set('_reserves',[inst,r['available_at_us'],at,r['record_id']],r)
        else:self._assertion(r)
        self.set('events',key,dict(body=r))
        return True

    def _fill(self,r):
        inst=r['instrument_id'];at=r['filled_at_us'];seq=r['sequence'];q=r['signed_contracts'];side='long' if q>0 else 'short'
        previous=self.meta('fill:'+inst)
        if previous:
            if at==previous[0]:need(seq is not None and previous[1] is not None and seq!=previous[1],'AMBIGUOUS_FILL_SEQUENCE')
            need((at,seq or 0)>=(previous[0],previous[1] or 0),'LATE_ORIGIN_UNSUPPORTED')
        self.putmeta('fill:'+inst,[at,seq])
        calendar=self.calendar(inst)
        fill_first=self.one_rule('sequence',inst,at)['same_time_order']=='fills_before_snapshot'
        start=bisect.bisect_left(calendar,at) if fill_first else bisect.bisect_right(calendar,at)
        need(start==len(calendar) or calendar[start]>=r['available_at_us'],'LATE_ORIGIN_UNSUPPORTED')
        self.rule(r['multiplier_rule_id'],'multiplier',inst,at)
        need(r['multiplier']==self.rule(r['multiplier_rule_id'],'multiplier',inst,at)['base_per_contract'],'MULTIPLIER_MISMATCH')
        fee=self.rule(r['fee_rule_id'],'fee',inst,at)
        need(fee['role']==r['liquidity_role'] and fee['signed_fraction']==r['fee_fraction'],'FEE_RULE_MISMATCH')
        for kind,id in [('obligation',r['fee_obligation_id']),('episode','episode:'+r['record_id']),('lot','lot:'+r['record_id']),('leg','leg:'+r['record_id']+':open'),('leg','leg:'+r['record_id']+':close')]:self.own(kind,id,inst)
        remaining=abs(q);ranges=[];closed=[]
        # Mutation of the active tree must not mutate an in-flight FIFO cursor.
        self.roots['_live']=self.index.freeze('_live',self.root('_live'))
        for l in self.live(inst):
            need(l['multiplier']==r['multiplier'],'MISSING_CONTRACT_CONVERSION')
            if l['direction']==side:break
            take=min(remaining,l['remaining_contracts'])
            if not take:break
            a=l['initial_contracts']-l['remaining_contracts'];b=a+take;u=self.unit(l,a,b);ranges.append(u)
            sid=digest([r['record_id'],l['lot_id'],a,b])
            pnl=Fraction(_ref.realized_pnl(take*(1 if l['direction']=='long' else -1),l['multiplier'],l['entry_price'],r['fill_price']))
            sl=dict(slice_id=sid,lot_id=l['lot_id'],episode_id=l['episode_id'],closing_fill_id=r['record_id'],closed_at_us=at,
             unit_start=a,unit_end=b,realized_price_pnl_usdt=fmt(pnl),entry_fee_cash_usdt='0',exit_fee_cash_usdt='0',funding_cash_usdt='0',attribution_revision=1,null_reasons={})
            self.save('closed_slices',[inst,at,sid],sl,sid);self.set('_slice_lot',[l['lot_id'],a,sid],sid)
            self.set('_ep_slices',[l['episode_id'],at,sid],sid)
            self.link('lot',l['lot_id'],'slice',dict(id=sid))
            self.touched_slices.add(sid);closed.append(sl)
            l['remaining_contracts']-=take;l['closed_slice_count']+=1
            l['closed_slices_root']=self.link_root('lot',l['lot_id'],'slice');self.save_lot(l)
            ep=self.get('_ep',[l['episode_id']]);ep['live']-=take
            if ep['live']==0:ep['exit']=at
            self.set('_ep',[l['episode_id']],ep)
            remaining-=take
            if not remaining:break
        if remaining:
            first=next(self.live(inst),None);eid=first['episode_id'] if first else 'episode:'+r['record_id'];lid='lot:'+r['record_id']
            ep=self.get('_ep',[eid],dict(instrument=inst,entry=at,exit=None,live=0));ep['live']+=remaining;ep['exit']=None
            self.set('_ep',[eid],ep)
            lot=dict(lot_id=lid,episode_id=eid,instrument_id=inst,opening_fill_id=r['record_id'],opened_at_us=at,direction=side,
             initial_contracts=remaining,remaining_contracts=remaining,entry_price=r['fill_price'],multiplier=r['multiplier'],
             live_ranges=[],closed_slice_count=0,closed_slices_root=self.index.empty('links'))
            self.save_lot(lot);ranges.append(self.unit(lot,0,remaining))
        for sl in closed:self.cash_entry(r,'realized_pnl',None,(Fraction(0),)*3,(Fraction(0),)*3,Fraction(sl['realized_price_pnl_usdt']),sl)
        total=Fraction(_ref.fee_cash(q,r['multiplier'],r['fill_price'],r['fee_fraction']))
        self.new_ob(r,r['fee_obligation_id'],'fee',ranges,total)

    def calendar(self,inst):
        return self.config['_calendar_times'][inst]

    def _snapshot(self,r):
        inst=r['instrument_id'];expected=self.config['_calendar_by_id'].get((inst,r['record_id']))
        need(expected is not None and expected['snapshot_at_us']==r['snapshot_at_us'],'UNDECLARED_SNAPSHOT')
        if r['mapping_rule_id'] is not None:
            need(r['mapping_rule_id']==expected['mapping_rule_id'],'SNAPSHOT_MAPPING_MISMATCH')
            self.rule(r['mapping_rule_id'],'funding',inst,r['snapshot_at_us'])
        live=[u for l in self.live(inst) for u in l['live_ranges']]
        need(live==r['eligible_ranges'],'ELIGIBILITY_MISMATCH')
        self.set('_snapshots',[inst,r['record_id']],r)
        if r['mapping_rule_id'] is not None:self.roots['_coverage']=self.index.delete('_coverage',self.root('_coverage'),[inst,r['record_id']])
        self.own('obligation',r['obligation_id'],inst)
        self.new_ob(r,r['obligation_id'],'funding',live,Fraction(0) if not live and r['mapping_rule_id'] is not None else None)

    def _revision(self,r):
        oid=r['record_id'];orig=self.origin_ranges(oid);need(orig is not None,'DANGLING_ORIGIN')
        o=self.get('_ob',[oid]);inst=r['instrument_id']
        need(orig['instrument']==inst and orig['origin']['record_id']==r['origin_id'] and orig['at']==r['economic_at_us'] and orig['kind']==r['obligation_kind'],'REFERENCE_SCOPE_MISMATCH')
        need(r['revision']==(o['revision'] or 0)+1 and r['supersedes_revision']==o['revision'],'REVISION_GAP')
        need(r['known_at_us']>=o['known'] and r['available_at_us']>=o['available'],'CLOCK_CONTRADICTION')
        self.rule(r['rule_id'],orig['kind'],inst,orig['at']);need(r['authority_id']==self.rules[r['rule_id']]['authority_id'],'UNPROVEN_AUTHORITY')
        total=None if r['cumulative_signed_total_usdt'] is None else Fraction(r['cumulative_signed_total_usdt'])
        if total is not None:self.check_alloc(r['allocations'],oid,orig,total)
        calc=r['calculation']
        if calc and calc['kind']=='funding_formula':
            need(orig['kind']=='funding','CALCULATION_CONTRACT');at=orig['at']
            vr=self.rule(calc['valuation_rule_id'],'valuation',inst,at);mr=self.rule(calc['multiplier_rule_id'],'multiplier',inst,at)
            need(calc['valuation_at_us']<=calc['valuation_available_at_us']<=at,'FUTURE_PROXY_MARK')
            need(at-calc['valuation_at_us']<=vr['max_age_us'],'STALE_VALUATION')
            need(max(at,calc['valuation_available_at_us'],calc['rate_available_at_us'])<=r['known_at_us'],'FUTURE_CALCULATION_INPUT')
            quantity=sum((u['unit_end']-u['unit_start'])*(1 if self.location('lots',u['lot_id'])['direction']=='long' else -1) for u in orig['ranges'])
            need(quantity==calc['signed_contracts'] and mr['base_per_contract']==calc['multiplier'],'MULTIPLIER_OR_QUANTITY_MISMATCH')
            need(total==Fraction(_ref.funding_cash(quantity,calc['multiplier'],calc['mark_price'],calc['final_rate'])),'FORMULA_MISMATCH')
        before=self.levels(o);self.aggregate(o,-1)
        o.update(T=fmt(total) if total is not None else None,revision=r['revision'],allocations=r['allocations'],known=r['known_at_us'],available=r['available_at_us'])
        self.aggregate(o,1);self.save_ob(oid,o);self.set('_revisions',[oid,r['revision']],r)
        if before[0] is not None or total is not None:self.cash_entry(r,'fee_claim' if orig['kind']=='fee' else 'funding_claim',oid,before,self.levels(o))

    def _posting(self,r):
        oid=r['obligation_id'];orig=self.origin_ranges(oid);need(orig is not None,'DANGLING_ORIGIN')
        need(orig['instrument']==r['instrument_id'],'REFERENCE_SCOPE_MISMATCH')
        need(r['available_at_us']>=orig['origin']['available_at_us'],'CLOCK_CONTRADICTION')
        self.rule(r['booking_rule_id'],'booking',r['instrument_id'],orig['at'])
        target=r['corrects_posting_id'];seen={r['record_id']}
        while target is not None:
            need(target not in seen,'DEPENDENCY_CYCLE');seen.add(target)
            p=self.get('_postings',[target]);need(p is not None and p['obligation_id']==oid and p['instrument_id']==r['instrument_id'],'REFERENCE_SCOPE_MISMATCH')
            need(p['available_at_us']<=r['available_at_us'],'DEPENDENCY_CYCLE');target=p['corrects_posting_id']
        amount=Fraction(r['signed_amount_usdt']);self.check_alloc(r['allocations'],oid,orig,amount)
        self.link('obligation',oid,'posting',dict(key=key_of(r)))
        for a in r['allocations']:self.link('obligation',oid,'allocation',dict(id=a['allocation_id']))
        o=self.get('_ob',[oid]);before=self.levels(o);self.aggregate(o,-1)
        o['B']=fmt(Fraction(o['B'])+amount);o['posting_count']+=1;o['posting_root']=digest([o['posting_root'],key_of(r)])
        self.aggregate(o,1);self.save_ob(oid,o);self.set('_postings',[r['record_id']],r)
        for u in orig['ranges']:self.set('_ep_postings',[u['episode_id'],r['record_id']],True)
        self.cash_entry(r,'cash_posting',oid,before,self.levels(o),amount)

    def _assertion(self,r):
        sc=r['scope'];ep=self.get('_ep',[sc['episode_id']]);need(ep is not None,'UNKNOWN_EPISODE')
        need(ep['instrument']==r['instrument_id']==sc['instrument_id'] and sc['trajectory_id']==self.config['trajectory_id'],'REFERENCE_SCOPE_MISMATCH')
        rule=self.rule(r['finality_rule_id'],'finality',r['instrument_id'],sc['economic_from_us'])
        if r['authority_id'] is not None:need(r['authority_id']==rule['authority_id'],'UNPROVEN_FINALITY_AUTHORITY')
        prev=self.get('_assertion_heads',[r['record_id']])
        need(r['revision']==(prev['revision']+1 if prev else 1) and r['supersedes_revision']==(prev['revision'] if prev else None),'REVISION_GAP')
        if prev:need(r['known_at_us']>=prev['known_at_us'] and r['available_at_us']>=prev['available_at_us'],'CLOCK_CONTRADICTION')
        for ref in r['obligation_revision_refs']:
            oid=ref['obligation_id'];origin=self.origin_ranges(oid)
            need(origin is not None and self.get('_revisions',[oid,ref['revision']]) is not None,'DANGLING_REFERENCE')
            need(origin['instrument']==r['instrument_id'] and any(u['episode_id']==sc['episode_id'] for u in origin['ranges']),'REFERENCE_SCOPE_MISMATCH')
        for ref in r['posting_refs']:
            p=self.get('_postings',[ref['posting_id']]);need(p is not None and p['instrument_id']==r['instrument_id'],'REFERENCE_SCOPE_MISMATCH')
            need(any(u['episode_id']==sc['episode_id'] for u in p['allocations']),'REFERENCE_SCOPE_MISMATCH')
        self.set('_assertion_versions',[r['record_id'],r['revision']],r)
        self.set('_assertion_heads',[r['record_id']],r);self.set('_ep_assertions',[sc['episode_id'],r['record_id']],r)

    def attribution(self):
        # Reverse indexes visit affected lots/slices only, including an ancient closed lot.
        for sid in sorted(self.touched_slices):
            sl=self.location('closed_slices',sid);values={'entry':Fraction(0),'exit':Fraction(0),'funding':Fraction(0)};versions={}
            for (_,oid),_ in self.rows('_lot_ob',prefix=[sl['lot_id']]):
                orig=self.origin_ranges(oid);o=self.get('_ob',[oid])
                overlap=any(u['lot_id']==sl['lot_id'] and max(u['unit_start'],sl['unit_start'])<min(u['unit_end'],sl['unit_end']) for u in orig['ranges'])
                if not overlap:continue
                versions[oid]=o['revision'] or 0;kind='funding' if orig['kind']=='funding' else 'exit' if sl['closing_fill_id']==orig['origin']['record_id'] else 'entry'
                if o['T'] is None:values[kind]=None;continue
                if values[kind] is None:continue
                for a in o['allocations']:
                    if a['lot_id']!=sl['lot_id']:continue
                    remaining=Fraction(a['signed_cash_usdt']);units=a['unit_end']-a['unit_start']
                    for _,otherid in self.rows('_slice_lot',prefix=[sl['lot_id']]):
                        other=self.location('closed_slices',otherid)
                        take=min(other['unit_end'],a['unit_end'])-max(other['unit_start'],a['unit_start'])
                        if take<=0:continue
                        share=remaining if take==units else Fraction(allocate(remaining,[take,units-take],Fraction(self.config['allocation_quantum_usdt']))[0])
                        remaining-=share;units-=take
                        if otherid==sid:values[kind]+=share;break
            nr={}
            for kind,field in [('entry','entry_fee_cash_usdt'),('exit','exit_fee_cash_usdt'),('funding','funding_cash_usdt')]:
                sl[field]=fmt(values[kind]) if values[kind] is not None else None
                if values[kind] is None:nr[field]='UNKNOWN_OBLIGATION_TOTAL'
            sl['null_reasons']=nr;sl['attribution_revision']=1+sum(versions.values())
            self.save('closed_slices',self.reference('closed_slices',sid),sl)
            self.set('_closed_values',[sid],sl)
        self.touched_slices.clear()

    def advance_clock(self,t):
        for inst in self.config['instruments']:
            old=self.meta('calendar:'+inst,0);upto=bisect.bisect_right(self.calendar(inst),t)
            for e in self.config['_calendar_entries'][inst][old:upto]:
                r=self.get('_snapshots',[inst,e['event_id']])
                if r is None or r['mapping_rule_id'] is None:
                    self.set('_coverage',[inst,e['event_id']],dict(instrument_id=inst,event_id=e['event_id'],reason_code='MISSING_EXPECTED_SNAPSHOT' if r is None else 'UNRESOLVED_SNAPSHOT_MAPPING'))
            self.putmeta('calendar:'+inst,upto)

    def coverage(self,t):
        out=[v for _,v in self.rows('_coverage')]
        for inst in self.config['instruments']:
            old=self.meta('calendar:'+inst,0);upto=bisect.bisect_right(self.calendar(inst),t)
            for e in self.config['_calendar_entries'][inst][old:upto]:
                r=self.get('_snapshots',[inst,e['event_id']])
                if r is None or r['mapping_rule_id'] is None:out.append(dict(instrument_id=inst,event_id=e['event_id'],reason_code='MISSING_EXPECTED_SNAPSHOT' if r is None else 'UNRESOLVED_SNAPSHOT_MAPPING'))
        return out

    def query_cohort(self,inst,t):
        clock=next((x['clock_id'] for x in self.config['mark_view_bindings'] if x['instrument_id']==inst),None)
        if clock is None:return 'NOT_CONFIGURED',[],None
        found=self.index.floor('_query_times',self.root('_query_times'),[inst,clock,t])
        if not found or found[0][:2]!=[inst,clock]:return 'PENDING',[],None
        q=found[0][2];rows=[v for _,v in self.rows('query_status',prefix=[inst,clock,q])]
        need(rows,'INPUT_BINDING_MISMATCH');sample=rows[0]
        if sample['status']=='UNKNOWN':return 'UNKNOWN',[r['key'] for r in rows],sample
        params=next(x for x in self.config['mark_clocks'] if x['instrument_id']==inst and x['clock_id']==clock)
        fresh=t-sample['source_at_us']<=params['max_source_age_us'] and t-sample['source_available_at_us']<=params['max_available_age_us']
        return 'SUPPORTED' if fresh else 'STALE',[r['key'] for r in rows],sample

    def balance(self,t,restated=False):
        coverage=self.coverage(t);unknown='UNRESOLVED_SNAPSHOT_COVERAGE' if coverage else 'UNKNOWN_OBLIGATION_TOTAL' if self.meta('unknown_A',0) else None
        cash=Fraction(self.meta('cash',self.config['initial_cash_usdt']));A=None if unknown else Fraction(self.meta('A','0'));L=None if unknown else Fraction(self.meta('L','0'))
        U=Fraction(0);ur=None;mr=Fraction(0);fr=Fraction(0);rr=None;mreason=None;freason=None;vrefs=[];rrefs=[];queryrefs=[];quals=[]
        for inst in self.config['instruments']:
            qual,refs,selection=self.query_cohort(inst,t);quals.append(qual);queryrefs+=refs
            held=list(self.live(inst))
            mark=None
            if qual=='NOT_CONFIGURED':
                found=self.index.floor('_marks',self.root('_marks'),[inst,t,2**63-1,'~'])
                if found and found[0][0]==inst:mark=found[1]
                if held:
                    if mark is None or mark['mark_price'] is None:ur='UNKNOWN_MARK'
                    elif t-mark['valuation_at_us']>self.rule(mark['valuation_rule_id'],'valuation',inst,mark['valuation_at_us'])['max_age_us']:ur='STALE_VALUATION'
                    else:vrefs.append(mark['record_id'])
            elif qual=='SUPPORTED':
                params=next(x for x in self.config['mark_clocks'] if x['instrument_id']==inst and x['clock_id']==selection['key']['clock_id'])
                mark=dict(mark_price=selection['mark_price'],valuation_at_us=selection['source_at_us'],multiplier_rule_id=params['multiplier_rule_id'])
            elif held:ur='STALE_VALUATION' if qual=='STALE' else 'UNKNOWN_MARK'
            if held and mark is not None and mark['mark_price'] is not None and not (qual in ('PENDING','UNKNOWN','STALE')):
                if qual=='NOT_CONFIGURED' and t-mark['valuation_at_us']>self.rule(mark['valuation_rule_id'],'valuation',inst,mark['valuation_at_us'])['max_age_us']:pass
                else:
                    mul=self.rule(mark['multiplier_rule_id'],'multiplier',inst,mark['valuation_at_us'])['base_per_contract']
                    for lot in held:
                        need(lot['multiplier']==mul,'MISSING_CONTRACT_CONVERSION')
                        U+=Fraction(_ref.realized_pnl(lot['remaining_contracts']*(1 if lot['direction']=='long' else -1),mul,lot['entry_price'],mark['mark_price']))
            found=self.index.floor('_reserves',self.root('_reserves'),[inst,t,2**63-1,'~'])
            reserve=found[1] if found and found[0][0]==inst else None
            if reserve is None or reserve['expires_at_us']<=t:rr=mreason=freason='UNKNOWN_RESERVES';continue
            rrefs.append(reserve['record_id']);dep=self.get('reserve_dependencies',list(wire_key(reserve)))
            for name,field in [('margin','reserved_margin_usdt'),('fees','reserved_fees_usdt')]:
                value=reserve[field]
                if qual!='NOT_CONFIGURED':
                    need(dep is not None,'INPUT_BINDING_MISMATCH')
                    d=dep[name]
                    if d['kind']=='current_mark' and (qual!='SUPPORTED' or not selection or d['query_key']['query_at_us']!=selection['key']['query_at_us']):value=None
                if value is None:
                    rr='UNKNOWN_RESERVES'
                    if name=='margin':mreason=rr
                    else:freason=rr
                elif name=='margin':mr+=Fraction(value)
                else:fr+=Fraction(value)
        eq=None if unknown or ur else cash+A-L+U
        # A required failure in either asset blocks the single shared account.
        bad=next((q for q in ('UNKNOWN','PENDING','STALE') if q in quals),None)
        qreason={'UNKNOWN':'MARK_QUERY_UNKNOWN','PENDING':'MARK_QUERY_NOT_AVAILABLE','STALE':'STALE_VALUATION'}.get(bad)
        reason='RESTATED_VIEW' if restated else unknown or ur or qreason or rr
        budget=None if reason else cash-L+min(U,0)-mr-fr
        nr={'actual_available_margin_usdt':'NOT_MODELED'}
        def value(field,n,why):
            if n is None:nr[field]=why;return None
            return fmt(n)
        qualification=bad or ('SUPPORTED' if 'SUPPORTED' in quals else 'NOT_CONFIGURED')
        b=dict(as_of_us=t,view='restated' if restated else 'as_known',knowledge_cutoff_us=t,
          cash_usdt=fmt(cash),receivables_usdt=value('receivables_usdt',A,unknown),liabilities_usdt=value('liabilities_usdt',L,unknown),
          unrealized_usdt=value('unrealized_usdt',None if ur else U,ur),economic_equity_usdt=value('economic_equity_usdt',eq,unknown or ur),
          reserved_margin_usdt=value('reserved_margin_usdt',None if mreason else mr,mreason),reserved_fees_usdt=value('reserved_fees_usdt',None if freason else fr,freason),
          simulated_budget_usdt=value('simulated_budget_usdt',budget,reason),actual_available_margin_usdt=None,new_risk_supported=budget is not None and budget>0,
          reductions_supported=True,mark_query_refs=sorted(queryrefs,key=canonical_bytes),mark_query_qualification=qualification,
          valuation_refs=sorted(vrefs),reserve_refs=sorted(rrefs),null_reasons=nr)
        return b,coverage

    def view(self,cutoff,restated=False):
        t=cutoff['at_us'];b,coverage=self.balance(t,restated)
        bad=sorted({x['instrument_id'] for x in coverage});previous=self.meta('qualified_bad',[])
        if bad!=previous:
            for inst in set(bad+previous):
                for key,sl in self.rows('closed_slices',prefix=[inst]):
                    base=self.get('_closed_values',[sl['slice_id']],sl)
                    if inst in bad:
                        base['funding_cash_usdt']=None;base['null_reasons']['funding_cash_usdt']='UNRESOLVED_SNAPSHOT_COVERAGE'
                    self.set('closed_slices',key,base)
            self.putmeta('qualified_bad',bad)
        self.index.freeze_roots(self.roots)
        sums=[dict(component=c,count=self.index.count(c,self.root(c)),root_sha256=self.root(c)) for c in COMPONENTS]
        ec=dict(view=b['view'],economic_at_us=t,knowledge_cutoff=cutoff,causal_policy_sha256=self.config['_policy_hash'],balance=b,
                economic_component_roots=[v for v in sums if v['component'] in ECONOMIC],coverage=coverage)
        eh=digest(['qf009.economic-state-v3',ec])
        core=dict(view=b['view'],economic_at_us=t,knowledge_cutoff=cutoff,causal_policy_sha256=self.config['_policy_hash'],balance=b,components=sums,coverage=coverage,economic_state_sha256=eh)
        return dict(core,view_sha256=digest(['qf009.view-v3',core]))

    def readiness(self,eid,t):
        ep=self.get('_ep',[eid]);need(ep is not None,'UNKNOWN_EPISODE')
        assertions=[v for _,v in self.rows('_ep_assertions',prefix=[eid])]
        own=[(k[1],self.get('_ob',[k[1]])) for k,_ in self.rows('_ep_ob',prefix=[eid])]
        status='immature';why='UNRESOLVED_FINALITY';complete=None
        if any(r['authority_id'] is None for r in assertions):status='invalid';why='INVALID_ASSERTION_AUTHORITY'
        elif ep['exit'] is None:status='open';why='OPEN_EPISODE'
        elif any(x['instrument_id']==ep['instrument'] for x in self.coverage(t)):why='UNRESOLVED_SNAPSHOT_COVERAGE'
        elif any(o['T'] is None for _,o in own):why='UNKNOWN_OBLIGATION_TOTAL'
        elif any(o['T']!=o['B'] for _,o in own):why='UNSETTLED_OBLIGATION'
        else:
            wanted_o={(oid,o['revision']) for oid,o in own};wanted_p={(k[1],1) for k,_ in self.rows('_ep_postings',prefix=[eid])}
            found_o={(x['obligation_id'],x['revision']) for r in assertions for x in r['obligation_revision_refs']}
            found_p={(x['posting_id'],x['revision']) for r in assertions for x in r['posting_refs']}
            kinds={'fill','fee'}|({'funding'} if any(self.origin_ranges(oid)['kind']=='funding' for oid,_ in own) else set())|({'posting'} if wanted_p else set())
            covered=True
            for kind in kinds:
                end=ep['entry']
                for a,b in sorted((r['scope']['economic_from_us'],r['scope']['economic_to_exclusive_us']) for r in assertions if kind in r['scope']['event_kinds']):
                    if a<=end:end=max(end,b)
                if end<=ep['exit']:covered=False
            if assertions and covered and wanted_o==found_o and wanted_p==found_p:
                status='complete';why=None
                times=[ep['exit']]+[r['available_at_us'] for r in assertions]+[o['available'] for _,o in own]
                times += [self.get('_postings',[pid])['available_at_us'] for pid,_ in wanted_p]
                complete=max(times)
        nr={}
        if ep['exit'] is None:nr['natural_exit_at_us']='OPEN_EPISODE'
        if complete is None:nr['complete_at_us']=why
        return dict(episode_id=eid,as_of_us=t,natural_exit_at_us=ep['exit'],status=status,complete_at_us=complete,
         assertion_refs=sorted([key_of(r) for r in assertions],key=canonical_bytes),blocking_reasons=[] if why is None else [why],null_reasons=nr)


def _prepare_config(config):
    fields='ledger_id trajectory_id scenario_id instruments initial_at_us end_exclusive_us knowledge_end_exclusive_us initial_cash_usdt allocation_quantum_usdt rules expected_snapshots ingestion_mode adapters initial_adapter_states schedule fact_schemas initial_context mark_clocks mark_view_bindings mark_requirements limits random_source'
    shape(config,fields+(' journal_storage' if 'journal_storage' in config else ''))
    c=deepcopy(config);strict_json(c)
    if 'journal_storage' in c:
        from research.qd015 import journal
        try:journal.validate(c['journal_storage'])
        except journal.JournalError as e:raise LedgerError('UNSUPPORTED_VERSION','/journal_storage') from e
    for k in ('ledger_id','trajectory_id','scenario_id'):ident(c[k])
    need(c['instruments'] and len(set(c['instruments']))==len(c['instruments']) and set(c['instruments'])<=set(INSTRUMENTS),'OUT_OF_SCOPE_INSTRUMENT')
    need(c['random_source']=='NONE','UNSUPPORTED_RANDOMNESS')
    need(c['ingestion_mode'] in ('reference_import','controlled_adapters'))
    need(integer(c['initial_at_us'])<integer(c['end_exclusive_us'])<=integer(c['knowledge_end_exclusive_us']))
    number(c['initial_cash_usdt'],0);number(c['allocation_quantum_usdt'],0)
    shape(c['limits'],LIMITS)
    for k,v in c['limits'].items():
        if k not in ('whole_history_record_ceiling','null_reasons'):integer(v,1)
    need(c['limits']['whole_history_record_ceiling'] is None)
    need(c['limits']['max_resident_cache_bytes']<=8*1024**2,'RESOURCE_EXHAUSTED')
    ids=set()
    for r in c['rules']:
        shape(r,'rule_id kind instrument_id valid_from_us valid_to_exclusive_us available_at_us authority_id parameters null_reasons')
        ident(r['rule_id']);need(r['rule_id'] not in ids,'DUPLICATE_RULE');ids.add(r['rule_id'])
        need(r['instrument_id'] in c['instruments']);need(r['available_at_us']<=c['initial_at_us'],'FUTURE_RULE')
        p=r['parameters'];kind=r['kind'];ident(r['authority_id']);integer(r['valid_from_us'])
        need(r['null_reasons']==({'valid_to_exclusive_us':'OPEN_ENDED_SCENARIO'} if r['valid_to_exclusive_us'] is None else {}),'NULL_REASON_CONTRACT')
        if r['valid_to_exclusive_us'] is not None:need(integer(r['valid_to_exclusive_us'])>r['valid_from_us'])
        if kind=='fee':
            shape(p,'role signed_fraction fee_currency');need(p['role'] in ('maker','taker') and p['fee_currency']=='USDT');p['signed_fraction']=fmt(number(p['signed_fraction']))
        elif kind=='multiplier':
            shape(p,'base_per_contract quantity_unit');need(number(p['base_per_contract'],0)>0 and p['quantity_unit']=='contracts');p['base_per_contract']=fmt(number(p['base_per_contract']))
        elif kind=='valuation':shape(p,'price_kind max_age_us');need(p['price_kind']=='MARK');integer(p['max_age_us'],1)
        elif kind=='sequence':shape(p,'same_time_order');need(p['same_time_order'] in ('snapshot_before_fills','fills_before_snapshot'))
        elif kind in ('funding','booking','finality'):
            field='calendar' if kind=='funding' else 'policy';shape(p,[field]+(['authority_id'] if kind=='finality' else []))
            need(p[field]=={'funding':'explicit_snapshot_list','booking':'explicit_posting_records','finality':'explicit_scoped_assertions'}[kind])
        else:raise LedgerError('UNSUPPORTED_RULE_KIND')
        for other in c['rules']:
            if other is r:continue
            if (r['kind'],r['instrument_id'],r['parameters'].get('role'))==(other['kind'],other['instrument_id'],other['parameters'].get('role')):
                need(max(r['valid_from_us'],other['valid_from_us'])>=min(r['valid_to_exclusive_us'] or 2**63-1,other['valid_to_exclusive_us'] or 2**63-1),'OVERLAPPING_RULES')
    c['_calendar_entries']={i:[] for i in c['instruments']};c['_calendar_by_id']={}
    for e in c['expected_snapshots']:
        shape(e,'instrument_id event_id snapshot_at_us mapping_rule_id')
        need(e['instrument_id'] in c['instruments']);need(c['initial_at_us']<=e['snapshot_at_us']<c['end_exclusive_us'])
        key=(e['instrument_id'],e['event_id']);need(key not in c['_calendar_by_id'],'ID_SCOPE_CONFLICT');c['_calendar_by_id'][key]=e;c['_calendar_entries'][e['instrument_id']].append(e)
    for values in c['_calendar_entries'].values():values.sort(key=lambda e:(e['snapshot_at_us'],e['event_id']))
    c['_calendar_times']={i:[e['snapshot_at_us'] for e in es] for i,es in c['_calendar_entries'].items()}
    shape(c['initial_context'],'mode from_us schemas')
    need(c['initial_context']['mode'] in ('none','closed_fact_prefix'))
    need(c['initial_context']['from_us']<=c['initial_at_us'])
    if c['ingestion_mode']=='reference_import':need(not any(c[k] for k in ('adapters','initial_adapter_states','mark_clocks','mark_view_bindings','mark_requirements')) and c['initial_context']['mode']=='none')
    adapters={a['adapter_id']:a for a in c['adapters']};need(len(adapters)==len(c['adapters']))
    slots={};last=-1
    for t in c['schedule'] if type(c['schedule']) is list else []:
        shape(t,'at_us slots');need(last<t['at_us']<c['knowledge_end_exclusive_us']);last=t['at_us'];phase=-1
        for j,slot in enumerate(t['slots'],1):
            shape(slot,'slot_id adapter_id phase');need(slot['slot_id'] not in slots and slot['adapter_id'] in adapters and slot['phase']>=phase,'SCHEDULE_MISMATCH')
            phase=slot['phase'];slots[slot['slot_id']]=(t['at_us'],j)
    for a in c['adapters']:
        shape(a,'adapter_id role code_commit source_files entrypoint input_contract_sha256 output_contract_sha256 state_contract_sha256 causal_config approval_ref fact_selectors ledger_selectors peer_state_selectors')
        need(a['role'] in ('policy','execution','environment'),'UNSUPPORTED_GENERATOR')
        need(a['role']!='environment' or not a['peer_state_selectors'],'FORBIDDEN_INPUT')
        for selector in a['ledger_selectors']+a['fact_selectors']:
            need(selector['instruments'] and set(selector['instruments'])<=set(c['instruments']),'REFERENCE_SCOPE_MISMATCH')
    clocks={}
    for clock in c['mark_clocks']:
        shape(clock,'instrument_id clock_id valuation_rule_id multiplier_rule_id source_delay_us max_source_age_us max_available_age_us')
        k=(clock['instrument_id'],clock['clock_id']);need(k not in clocks and k[0] in c['instruments']);clocks[k]=clock
        integer(clock['source_delay_us']);integer(clock['max_source_age_us'],1);integer(clock['max_available_age_us'],1)
        vr=next((r for r in c['rules'] if r['rule_id']==clock['valuation_rule_id'] and r['kind']=='valuation' and r['instrument_id']==k[0]),None)
        mr=next((r for r in c['rules'] if r['rule_id']==clock['multiplier_rule_id'] and r['kind']=='multiplier' and r['instrument_id']==k[0]),None)
        need(vr and mr and vr['parameters']['max_age_us']==clock['max_source_age_us'],'RULE_MISMATCH')
    seen=set()
    for binding in c['mark_view_bindings']:
        shape(binding,'instrument_id clock_id');need(binding['instrument_id'] not in seen and (binding['instrument_id'],binding['clock_id']) in clocks);seen.add(binding['instrument_id'])
    seen=set()
    for r in c['mark_requirements'] if type(c['mark_requirements']) is list else []:
        shape(r,'key before_slots for_view');k=r['key'];shape(k,'instrument_id clock_id query_at_us purpose');key=canonical_bytes(k)
        need(key not in seen and (k['instrument_id'],k['clock_id']) in clocks and k['purpose'] in PURPOSES);seen.add(key)
        need(c['initial_at_us']<=integer(k['query_at_us'])<c['end_exclusive_us']);need(type(r['for_view']) is bool)
        need(all(id in slots and slots[id][0]>=k['query_at_us'] for id in r['before_slots']),'SCHEDULE_MISMATCH')
        if r['for_view']:need(k['purpose'] in ('valuation','reservation') and any(x['instrument_id']==k['instrument_id'] and x['clock_id']==k['clock_id'] for x in c['mark_view_bindings']))
    need({a['adapter_id'] for a in c['initial_adapter_states']}==set(adapters),'INPUT_BINDING_MISMATCH')
    for state in c['initial_adapter_states']:_validate_state(state,adapters[state['adapter_id']])
    c['_adapters']=adapters;c['_slots']=slots
    from research.qd014.structure import Plan
    c['_plan_index']=Plan(c)
    causal={k:v for k,v in config.items() if k not in ('limits','journal_storage')}
    causal=deepcopy(causal)
    for a in causal['adapters']:a.pop('approval_ref')
    c['_policy_hash']=digest(causal)
    return c


def _validate_state(state,definition):
    shape(state,'adapter_id contract_sha256 tracked_episode_ids value state_sha256')
    need(state['adapter_id']==definition['adapter_id'] and state['contract_sha256']==definition['state_contract_sha256'],'INPUT_BINDING_MISMATCH')
    need(state['state_sha256']==digest({k:v for k,v in state.items() if k!='state_sha256'}),'INPUT_BINDING_MISMATCH')


def _safe_path(root,relative):
    need(type(relative) is str and not Path(relative).is_absolute() and '..' not in Path(relative).parts,'SCHEMA_VIOLATION')
    need(not Path(root).is_symlink(),'SCHEMA_VIOLATION')
    path=Path(root)/relative
    current=Path(root)
    for p in Path(relative).parts:
        current=current/p;need(not current.is_symlink(),'SCHEMA_VIOLATION')
    need(path.resolve().is_relative_to(Path(root).resolve()),'SCHEMA_VIOLATION');return path


def _file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        while chunk:=source.read(65536):h.update(chunk)
    return h.hexdigest()


def _fsync_directory(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def _atomic(path,value,*,_raw=None):
    path=Path(path);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
    raw=canonical_bytes(value)+b'\n' if _raw is None else _raw
    need(type(raw) is bytes,'STORE_INTEGRITY_FAILURE')
    immutable=path.name.startswith(('control-','guard-input-','journal-','manifest-')) or path.parent.name=='audit-rows'
    if immutable and path.exists():
        need(path.is_file() and path.stat().st_size==len(raw) and _file_sha(path)==hashlib.sha256(raw).hexdigest(),'STORE_INTEGRITY_FAILURE')
        with path.open('rb') as existing:os.fsync(existing.fileno())
        _fsync_directory(path.parent);return
    budget=_budget_for(path)
    if budget:budget.issue(tmp,len(raw),len(raw))
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    if budget:budget.rename(tmp,path)
    _fsync_directory(path.parent)
    need(path.read_bytes()==raw,'STORE_INTEGRITY_FAILURE')


_PORTS={}
_GUARD=threading.local()
_JOURNAL_CREATION=threading.local()


@contextmanager
def journal_creation(profile):
    """Explicit new-store-only binding, persisted in GENESIS; thread local."""
    need(not hasattr(_JOURNAL_CREATION,'profile'),'UNSUPPORTED_VERSION')
    from research.qd015 import journal
    journal.validate(profile);_JOURNAL_CREATION.profile=deepcopy(profile)
    try:yield
    finally:del _JOURNAL_CREATION.profile

def _audit_hook(event,args):
    if getattr(_GUARD,'active',False) and (event=='open' or event.startswith(('socket.','subprocess.','os.system','os.listdir','os.scandir'))):
        raise LedgerError('FORBIDDEN_INPUT')
sys.addaudithook(_audit_hook)


def _guarded_host_read(original,code):
    def read(*args,**kwargs):
        if getattr(_GUARD,'active',False):raise LedgerError(code)
        return original(*args,**kwargs)
    return read


# Thread-local admission flags leave host instrumentation and other threads
# operational. Trusted ports still need review for pre-bound aliases/globals.
os.urandom=_guarded_host_read(os.urandom,'UNSUPPORTED_RANDOMNESS')
time.time=_guarded_host_read(time.time,'FORBIDDEN_INPUT')
time.monotonic=_guarded_host_read(time.monotonic,'FORBIDDEN_INPUT')


def register_port(definition,port):
    """Process-start admission of a reviewed, pinned module; never a per-call callback."""
    for file in definition['source_files']:
        p=Path(__file__).resolve().parents[2]/file['relative_path']
        need(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==file['sha256'],'UNSUPPORTED_GENERATOR')
    need(all(callable(getattr(port,n,None)) for n in ('evaluate','validate_input','validate_output','validate_state')),'UNSUPPORTED_GENERATOR')
    token=digest(definition);old=_PORTS.get(token)
    need(old is None or old is port or (type(old) is type(port) and not old.__dict__ and not port.__dict__),'UNSUPPORTED_GENERATOR')
    _PORTS[token]=old or port


class Ledger:
    def __init__(self,store_root,expected_head=None,_recovery=False):
        self.thread_id=threading.get_ident()
        self.root=Path(store_root);need(self.root.is_dir() and not self.root.is_symlink(),'STORE_INTEGRITY_FAILURE')
        import fcntl
        self.lease=_safe_path(self.root,'LEASE').open('a+b')
        try:fcntl.flock(self.lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as e:self.lease.close();raise LedgerError('STORE_INTEGRITY_FAILURE','/lease') from e
        self.started=_clock();self.written=0;self._closed=False
        try:
            self.request=load_json(_safe_path(self.root,'GENESIS').read_bytes());self.config=_prepare_config(self.request['config'])
            self.head=load_json(_safe_path(self.root,'HEAD').read_bytes());need(expected_head is None or expected_head==self.head['audit_prefix'],'CHECKPOINT_MISMATCH')
            self.budget=_BUDGETS.get(str(self.root.resolve()))
            if self.budget is None:self.budget=ResourceBudget(self.root,self.config['limits']['max_store_bytes']);_BUDGETS[str(self.root.resolve())]=self.budget
            self.budget.parent=_GLOBAL_BUDGET if _GLOBAL_BUDGET and self.root.resolve().is_relative_to(_GLOBAL_BUDGET.root) else None
            self.control=self._load_control();self.unknown=None
            self.spent=load_json((self.root/'SPENT').read_bytes()) if (self.root/'SPENT').exists() else dict(active_wall_us=0,total_written_bytes=0,attempts_started=1)
            self.index=NodeIndex(_safe_path(self.root,'cache.sqlite3'),self.config['limits']['max_resident_cache_bytes'])
            self._init_tables()
            genesis=self._initialize_state();self._genesis_roots=dict(genesis.roots)
            if self.head['committed_seq']:
                payload=self._payload(self.head['committed_seq']);roots=payload['roots']
                if self.index.db.execute('SELECT v FROM local_meta WHERE k="head"').fetchone()!=(self.head['audit_prefix'],):
                    self._rebuild_index()
                else:
                    try:
                        for comp,root in roots.items():self.index.node(comp,root)
                    except LedgerError:self._rebuild_index()
                self.state=State(self.index,self.config,roots)
            else:self.state=genesis
            self.state.at=(self.head['cutoff']['at_us'],self.head['cutoff']['slot'])
            self._load_audit()
        except (OSError,sqlite3.Error) as e:
            if hasattr(self,'index'):self.index.db.close()
            self.lease.close();raise LedgerError('STORE_INTEGRITY_FAILURE') from e
        except Exception:
            if hasattr(self,'index'):self.index.db.close()
            self.lease.close();raise

    def _init_tables(self):
        d=self.index.db
        d.execute('CREATE TABLE IF NOT EXISTS local_meta(k TEXT PRIMARY KEY,v TEXT)')
        d.execute('CREATE TABLE IF NOT EXISTS facts(k TEXT PRIMARY KEY,inst TEXT,schema_id TEXT,at INTEGER,available INTEGER,b BLOB)')
        d.execute('CREATE INDEX IF NOT EXISTS facts_available ON facts(available,k)')
        d.execute('CREATE INDEX IF NOT EXISTS facts_selection ON facts(schema_id,inst,available,k)')
        d.execute('CREATE INDEX IF NOT EXISTS facts_slot ON facts(schema_id,inst,at,available,k)')
        d.execute('CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,sha TEXT,seq INTEGER)')
        d.execute('CREATE TABLE IF NOT EXISTS commits(seq INTEGER PRIMARY KEY,at INTEGER,prefix TEXT)')
        d.execute('CREATE TABLE IF NOT EXISTS views(h TEXT PRIMARY KEY,b BLOB,roots BLOB)')
        d.execute('CREATE TABLE IF NOT EXISTS audit_rows(seq INTEGER PRIMARY KEY,kind TEXT,commit_seq INTEGER,guard_id TEXT,b BLOB)')
        self._load_sources()
        d.commit()

    def _load_sources(self):
        cached=self.index.db.execute('SELECT v FROM local_meta WHERE k="sources"').fetchone()==(digest(self.request['raw_catalogue']),)
        roots={r['root_id']:r['path'] for r in self.request['source_roots']}
        cat=self.request['raw_catalogue'];shape(cat,'namespace schema_version catalogue_id objects fact_store qualification_ref')
        need(cat['namespace']=='qf009.raw-catalogue' and cat['schema_version']==1,'UNSUPPORTED_NAMESPACE')
        objects={}
        for item in cat['objects']:
            p=_safe_path(roots[item['root_id']],item['relative_path']);h=hashlib.sha256();count=0;size=0
            with p.open('rb') as f:
                for raw in f:h.update(raw);size+=len(raw);count+=1
            need(h.hexdigest()==item['sha256'] and size==item['bytes'],'SOURCE_HASH_MISMATCH');objects[item['object_id']]=dict(item,rows=count)
        ref=self.request['fact_store'];need(ref==cat['fact_store'],'SOURCE_HASH_MISMATCH')
        p=_safe_path(roots[ref['root_id']],ref['relative_path']);h=hashlib.sha256();count=size=0
        if not cached:self.index.db.execute('DELETE FROM facts')
        with p.open('rb') as source:
            for raw in source:
                h.update(raw);count+=1;size+=len(raw);row=load_json(raw)
                for rr in row['raw_refs']:
                    obj=objects.get(rr['object_id']);need(obj is not None and obj['sha256']==rr['raw_sha256'] and 1<=rr['source_row']<=obj['rows'],'SOURCE_HASH_MISMATCH')
                if self.config['ingestion_mode']=='reference_import':
                    shape(row,'fact_key instrument_id body scenario_available_at_us raw_refs');body=normalize_body(row['body'])
                    row['body']=body
                    need(row['scenario_available_at_us']==body['available_at_us'] and row['instrument_id']==body['instrument_id'],'INPUT_BINDING_MISMATCH')
                    schema='reference';at=economic_time(body)
                else:
                    shape(row,'fact_key instrument_id schema_id economic_at_us scenario_available_at_us observed_first_available_at_us cells raw_refs null_reasons')
                    schema=row['schema_id'];at=row['economic_at_us'];self._validate_fact(row)
                try:
                    if cached:
                        existing=self.index.db.execute('SELECT b FROM facts WHERE k=?',(row['fact_key'],)).fetchone();need(existing is not None and existing[0]==canonical_bytes(row),'STORE_INTEGRITY_FAILURE')
                    else:self.index.db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?)',(row['fact_key'],row['instrument_id'],schema,at,row['scenario_available_at_us'],canonical_bytes(row)))
                except sqlite3.IntegrityError as e:raise LedgerError('DUPLICATE_SOURCE') from e
        need(h.hexdigest()==ref['sha256'] and count==ref['rows'] and size==ref['bytes'],'SOURCE_HASH_MISMATCH')
        if not cached:self.index.db.execute('INSERT OR REPLACE INTO local_meta VALUES ("sources",?)',(digest(cat),))

    def _validate_fact(self,row):
        schema=next((s for s in self.config['fact_schemas'] if s['schema_id']==row['schema_id']),None);need(schema is not None,'UNSUPPORTED_GENERATOR')
        fields={f['name']:f for f in schema['fields']};need({c['name'] for c in row['cells']}==set(fields),'INPUT_BINDING_MISMATCH')
        if row['scenario_available_at_us'] is not None:need(row['economic_at_us']<=row['scenario_available_at_us'],'FUTURE_DEPENDENCY')
        for x in row['cells']:
            v=x['cell'];f=fields[x['name']];need(v['type']==f['type'],'INPUT_BINDING_MISMATCH')
            if v['tag']=='unknown':shape(v,'tag type reason');need(v['reason'] in ('UNKNOWN_RATE','UNKNOWN_MARK','UNKNOWN_AMOUNT','UNKNOWN_SOURCE_TIME','UNKNOWN_MAPPING','UNKNOWN_FINALITY'),'NULL_REASON_CONTRACT');continue
            shape(v,'tag type value');need(v['tag']=='known')
            if f['type'] in ('D','D0','D+'):
                num=number(v['value'],0 if f['type']!='D' else None);need(f['type']!='D+' or num>0,'DECIMAL_DOMAIN')
            elif f['type']=='bool':need(type(v['value']) is bool)
            elif f['type'] in ('I','SI','T'):integer(v['value'],-(2**63-1) if f['type']=='SI' else 0)
            else:ident(v['value'])

    def _payload(self,seq):
        m=load_json(_safe_path(self.root,f'manifest-{seq:08}.json').read_bytes());need(digest(m)==self.head['audit_prefix'] if seq==self.head['committed_seq'] else True,'STORE_INTEGRITY_FAILURE')
        ref=m['files'][0];p=_safe_path(self.root,ref['relative_path']);profile=self.config.get('journal_storage')
        if profile:
            need(ref['relative_path']==f'journal-{seq:08}.qjz' and ref['bytes']<=profile['max_stored_bytes'] and p.stat().st_size==ref['bytes'],'STORE_INTEGRITY_FAILURE')
        raw=p.read_bytes()
        need(hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes'],'STORE_INTEGRITY_FAILURE')
        if profile:
            from research.qd015 import journal
            try:raw=journal.decode(raw,profile)
            except journal.JournalError as e:raise LedgerError('STORE_INTEGRITY_FAILURE','/journal_decode') from e
        return load_json(raw)

    def _load_control(self):
        p=load_json(_safe_path(self.root,'CONTROL').read_bytes());seq=p['control_seq'];last=digest(['qf009.control-v3',self.request['config']['ledger_id'],PROFILE,'genesis'])
        status='ACTIVE';guard=None;validated=False
        for n in range(1,seq+1):
            row=load_json(_safe_path(self.root,f'control-{n:08}.json').read_bytes());h=row.pop('control_sha256')
            need(h==digest(row) and row['previous_control_sha256']==last,'STORE_INTEGRITY_FAILURE');last=h
            if row['kind']!='write_guard':
                need(guard is not None and all(row[k]==guard[k] for k in ('guard_id','guard_input','request_id','request_sha256')),'STORE_INTEGRITY_FAILURE')
            if row['kind']=='write_guard':guard=row;validated=False
            elif row['kind']=='validated':need(guard is not None and row['guard_id']==guard['guard_id'],'STORE_INTEGRITY_FAILURE');validated=True
            elif row['kind']=='integrity_stop':status='INTEGRITY_STOPPED'
            elif row['kind']=='resource_stop' and status!='INTEGRITY_STOPPED':status='RESOURCE_STOPPED'
            elif row['kind']=='resolution' and row['outcome']!='unknown':guard=None
        need(last==p['control_sha256'],'STORE_INTEGRITY_FAILURE')
        return dict(seq=seq,hash=last,status=status,guard=guard,validated=validated)

    def _control(self,kind,request=None,outcome=None,error=None):
        self.budget.emergency=True
        if self.budget.parent:self.budget.parent.emergency=True
        seq=self.control['seq']+1
        row=dict(ledger_id=self.config['ledger_id'],profile=PROFILE,control_seq=seq,previous_control_sha256=self.control['hash'],
          at_committed_seq=self.head['committed_seq'],audit_prefix=self.head['audit_prefix'],kind=kind,
          guard_id=self.control['guard']['guard_id'] if self.control['guard'] else 'g:'+str(seq),
          guard_input=self.control['guard']['guard_input'] if self.control['guard'] else self.guard_input,
          request_id=request.get('request_id') if request else None,request_sha256=digest(request) if request else None,
          error=error,outcome=outcome,null_reasons={**({'request_id':'UNKNOWN_INPUT_IDENTITY'} if not request or request.get('request_id') is None else {}),**({'request_sha256':'NONCANONICAL_INPUT'} if request is None else {}),**({'error':'NOT_APPLICABLE'} if error is None else {}),**({'outcome':'NOT_APPLICABLE'} if outcome is None else {})})
        row['control_sha256']=digest(row)
        _atomic(self.root/f'control-{seq:08}.json',row)
        _atomic(self.root/'CONTROL',dict(control_seq=seq,control_sha256=row['control_sha256']))
        # Both barriers/readbacks succeeded. Advance the already-verified chain
        # in O(1); a cold open verifies the entire durable chain once.
        current=dict(self.control,seq=seq,hash=row['control_sha256'])
        if kind=='write_guard':current['guard']=row;current['validated']=False
        elif kind=='validated':current['validated']=True
        elif kind=='integrity_stop':current['status']='INTEGRITY_STOPPED'
        elif kind=='resource_stop' and current['status']!='INTEGRITY_STOPPED':current['status']='RESOURCE_STOPPED'
        elif kind=='resolution' and outcome!='unknown':current['guard']=None
        self.control=current;self.budget.emergency=False
        if self.budget.parent:self.budget.parent.emergency=False

    def current_head(self):
        h=deepcopy(self.head);h['status']=self.control['status'] if self.control['status']!='ACTIVE' else 'COMMIT_UNKNOWN' if self.control['guard'] or self.unknown else 'ACTIVE';return h

    def close(self):
        if not self._closed:
            self.index.close();self.lease.close();self._closed=True
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

    def _initialize_state(self):
        s=State(self.index,self.config)
        for a in self.config['initial_adapter_states']:s.set('adapter_states',[a['adapter_id']],a)
        context=self.config['initial_context'];semantic=hashlib.sha256();audit=hashlib.sha256();count=0
        if context['mode']=='closed_fact_prefix':
            for key,blob in self.index.db.execute('SELECT k,b FROM facts WHERE at>=? AND (available<? OR available IS NULL) ORDER BY available,k',
                                                (context['from_us'],self.config['initial_at_us'])):
                row=load_json(blob)
                if row['schema_id'] not in context['schemas']:continue
                need(row['scenario_available_at_us'] is not None,'FUTURE_DEPENDENCY')
                schema=self.schema(row['schema_id']);need(schema['view_kind'] in ('closed_bar','funding_rate','synthetic_price'),'FORBIDDEN_INPUT')
                need(schema['view_kind']!='closed_bar' or row['economic_at_us']+schema['interval_us']<=row['scenario_available_at_us'],'FUTURE_DEPENDENCY')
                projection=self.projection(row);semantic.update(canonical_bytes(projection)+b'\n');audit.update(canonical_bytes(row)+b'\n');count+=1
        s.putmeta('context_receipt',dict(from_us=context['from_us'],before_us=self.config['initial_at_us'],fact_count=count,
                    economic_prefix_sha256=semantic.hexdigest(),audit_binding_sha256=audit.hexdigest()))
        self.index.freeze_roots(s.roots);s.delta.clear();s.private_delta.clear();return s

    def schema(self,id):
        found=next((x for x in self.config['fact_schemas'] if x['schema_id']==id),None)
        need(found is not None,'UNSUPPORTED_GENERATOR');return found

    @staticmethod
    def projection(row):return {k:deepcopy(row[k]) for k in ('fact_key','instrument_id','schema_id','economic_at_us','scenario_available_at_us','cells')}

    def _assert_thread(self):need(threading.get_ident()==self.thread_id,'STORE_INTEGRITY_FAILURE','/writer_thread')

    def _assert_active(self):
        self._assert_thread()
        need(self.control['status']=='ACTIVE','RESOURCE_EXHAUSTED' if self.control['status']=='RESOURCE_STOPPED' else 'STORE_INTEGRITY_FAILURE')
        need(self.control['guard'] is None and not self.unknown,'COMMIT_OUTCOME_UNKNOWN')

    def _bound(self):
        need((_clock()-self.started)*1000000+self.spent['active_wall_us']<=self.config['limits']['max_wall_us'],'RESOURCE_EXHAUSTED','/wall')
        size=(self.budget.total+(self.budget.book.stat().st_size if self.budget.book.exists() else 0)) if self.config['_plan_index'].compact else sum(p.stat().st_size for p in self.root.iterdir() if p.is_file())
        need(size<=self.config['limits']['max_store_bytes'],'RESOURCE_EXHAUSTED','/store')

    def _envelope(self,e):
        shape(e,'namespace schema_version profile body origin created_at_us')
        need(e['namespace']==NS,'UNSUPPORTED_NAMESPACE');need(e['schema_version']==VERSION and e['profile']==PROFILE,'UNSUPPORTED_VERSION')
        integer(e['created_at_us']);r=normalize_body(e['body']);o=e['origin']
        shape(o,'kind fact_key');need(o['kind']=='reference_import','UNSUPPORTED_GENERATOR')
        row=self.index.db.execute('SELECT b FROM facts WHERE k=?',(o['fact_key'],)).fetchone()
        need(row is not None,'SOURCE_HASH_MISMATCH');fact=load_json(row[0])
        need(fact['body']==r,'INPUT_BINDING_MISMATCH')
        return dict(e,body=r)

    def _group(self,envelopes,st,applied,duplicates):
        # Reject a late fill crossing the frozen calendar before a snapshot in
        # the same delivery can fail inventory eligibility for a secondary reason.
        for e in envelopes:
            r=e['body']
            if r['record_type']=='Fill' and st.get('events',list(wire_key(r))) is None:
                calendar=st.calendar(r['instrument_id']);fill_first=st.one_rule('sequence',r['instrument_id'],r['filled_at_us'])['same_time_order']=='fills_before_snapshot'
                start=bisect.bisect_left(calendar,r['filled_at_us']) if fill_first else bisect.bisect_right(calendar,r['filled_at_us'])
                need(start==len(calendar) or calendar[start]>=r['available_at_us'],'LATE_ORIGIN_UNSUPPORTED')
        def order(e):
            r=e['body'];typ=r['record_type'];at=economic_time(r)
            tie=st.one_rule('sequence',r['instrument_id'],at).get('same_time_order') if typ in ('Fill','FundingSnapshot') else ''
            stage={'Valuation':0,'Reserves':0,'FundingSnapshot':1 if tie=='snapshot_before_fills' else 3,
                   'Fill':2,'ObligationRevision':4,'Posting':5,'CompletenessAssertion':6}[typ]
            return (r['available_at_us'],at,stage,r.get('sequence') or 0,r['revision'],r['record_id'])
        for e in sorted(envelopes,key=order):
            r=e['body'];key=list(wire_key(r));old=st.get('events',key)
            if old is None:
                need(not self.head['committed_seq'] or r['available_at_us']>self.head['cutoff']['at_us'],'PAST_AVAILABILITY')
            changed=st.apply(r)
            refs=st.get('_audit_ref_roots',key,self.index.empty('_audit_refs'));refs=self.index.freeze('_audit_refs',self.index.set('_audit_refs',refs,[digest(e['origin'])],e['origin']));st.set('_audit_ref_roots',key,refs)
            dedup=st.get('_dedup',key,dict(key=key_of(r),body_sha256=digest(r),first_commit=self.head['committed_seq']+1,audit_refs_root=refs));dedup['audit_refs_root']=refs;st.set('_dedup',key,dedup)
            if changed:
                st.set('events',key,e);st.set('_accepted',[st.at[0],st.at[1],*key],r);applied.append(key_of(r))
            else:duplicates.append(key_of(r))
        st.attribution()

    def _queries(self,st,lower,t):
        # Query events are released even at non-tick times. The frozen plan, not
        # a historical Valuation's source time, chooses the active cohort.
        due=self.config['_plan_index'].due(lower,t)
        for requirement in due:
            key=requirement['key'];q=key['query_at_us'];inst=key['instrument_id'];clock=key['clock_id']
            matches=[]
            for (blob,) in self.index.db.execute('SELECT b FROM facts WHERE inst=? AND available=? AND at=? ORDER BY k',(inst,q,q)):
                row=load_json(blob)
                if self.schema(row['schema_id'])['view_kind']!='mark_selection':continue
                cells={c['name']:c['cell'] for c in row['cells']}
                if cells['clock_id'].get('value')==clock and cells['role_'+key['purpose']].get('value') is True:matches.append((row,cells))
            need(len(matches)==1,'INPUT_BINDING_MISMATCH','/mark_requirement')
            row,cells=matches[0];params=next(c for c in self.config['mark_clocks'] if c['instrument_id']==inst and c['clock_id']==clock)
            status=cells['status']['value'];need(status in ('SUPPORTED','UNKNOWN'),'INPUT_BINDING_MISMATCH')
            need(cells['query_at_us'].get('value')==q,'CLOCK_CONTRADICTION')
            nr={};values={}
            for name,cellname in [('source_at_us','source_at_us'),('source_available_at_us','source_available_at_us'),('source_semantic_key','source_fact_key'),('mark_price','selected_price')]:
                cell=cells[cellname];values[name]=cell.get('value')
                if cell['tag']=='unknown':nr[name]=cell['reason']
            reason=cells['unknown_reason'].get('value')
            if status=='SUPPORTED':
                need(all(v is not None for v in values.values()) and cells['unknown_reason'].get('value')=='NOT_APPLICABLE','INPUT_BINDING_MISMATCH')
                source=values['source_at_us'];available=values['source_available_at_us']
                need(values['source_semantic_key']==f'mk:{inst}:{source}','INPUT_BINDING_MISMATCH')
                need(source+params['source_delay_us']==available<=q,'CLOCK_CONTRADICTION')
                need(q-source<=params['max_source_age_us'] and q-available<=params['max_available_age_us'],'STALE_VALUATION')
                reason=None;nr['unknown_reason']='NOT_APPLICABLE'
            else:
                need(reason in QUERY_REASONS and all(v is None for v in values.values()),'NULL_REASON_CONTRACT')
            qs=dict(key=deepcopy(key),fact_key=row['fact_key'],available_at_us=q,status=status,unknown_reason=reason,null_reasons=nr,**values)
            need(row['fact_key']=='mq:'+digest(['qf009.query-fact-v1',inst,clock,q]),'INPUT_BINDING_MISMATCH')
            expected=self.config['_plan_index'].purposes(key)
            need({p for p in PURPOSES if cells['role_'+p].get('value') is True}==expected,'INPUT_BINDING_MISMATCH')
            st.set('query_status',[inst,clock,q,key['purpose']],qs)
            if requirement['for_view'] or requirement['before_slots']:st.set('_query_times',[inst,clock,q],True)

    def _frame(self,st,cutoff):
        self.index.freeze_roots(st.roots)
        if st.delta or st.private_delta:
            st.frames.append(dict(cutoff=deepcopy(cutoff),projection=[dict(component=c,item=v) for (c,_),(key,v) in sorted(st.delta.items())],private=[dict(component=c,key=key,value=v) for (c,_),(key,v) in sorted(st.private_delta.items())]));st.delta.clear();st.private_delta.clear()
        roots={k:v for k,v in st.roots.items() if k!='_timeline'}
        st.set('_timeline',[cutoff['at_us'],cutoff['slot']],roots)
        st.roots['_timeline']=self.index.freeze('_timeline',st.roots['_timeline'])

    def _stage(self,request,st=None,partial=None):
        st=st or self.state;applied=[];duplicates=[];generated=[];noops=[]
        lower=self.head['cutoff']['at_us'] if self.head['committed_seq'] else self.config['initial_at_us']-1
        t=request['through_us'] if partial is None else partial['at_us']
        need(t>=self.config['initial_at_us'],'SCHEDULE_MISMATCH')
        need(lower<=t<self.config['knowledge_end_exclusive_us'],'SCHEDULE_MISMATCH')
        imported=request['imported'];need(type(imported) is list and type(request['generated']) is list)
        if self.config['ingestion_mode']=='reference_import':
            need(not request['generated'],'UNSUPPORTED_GENERATOR');envelopes=[]
            for e in imported:
                e=self._envelope(e);r=e['body']
                need(r['available_at_us']<=request['through_us'],'FUTURE_DEPENDENCY')
                if r['available_at_us']<=t:envelopes.append(e)
            st.at=(t,0);self._group(envelopes,st,applied,duplicates)
        else:
            need(not imported,'UNSUPPORTED_GENERATOR')
            plan=self.config['_plan_index']
            points=sorted(set(plan.between(lower,t)) | {r['key']['query_at_us'] for r in plan.due(lower,t)} | {t})
            previous=lower
            for at in points:
                self._queries(st,previous,at);st.advance_clock(at);st.at=(at,0);self._frame(st,dict(at_us=at,slot=0))
                tick=plan.tick(at)
                if tick:
                    for slotno,slot in enumerate(tick['slots'],1):
                        if partial and at==t and slotno>partial['slot']:break
                        st.at=(at,slotno);g=self._invoke(st,slot)
                        generated.append(g)
                        self._accept_result(st,slot,g,applied,duplicates)
                        if g['result']['outcome']=='noop':noops.append(dict(at_us=at,slot=slotno))
                        self._frame(st,dict(at_us=at,slot=slotno))
                previous=at
            if partial is None and request['generated']:
                need(len(request['generated'])==len(generated),'SCHEDULE_MISMATCH')
                for proposed,actual in zip(request['generated'],generated):
                    for read in proposed.get('reads',[]):
                        if read.get('kind')=='fact':
                            row=self.index.db.execute('SELECT available FROM facts WHERE k=?',(read['fact_key'],)).fetchone()
                            need(row is not None and row[0] is not None and row[0]<=actual['slot']['at_us'],'FUTURE_DEPENDENCY')
                    for field in ('slot','slot_id','adapter_id','input_projection_sha256','prior_adapter_state_sha256','reads','selection_bindings'):
                        need(proposed.get(field)==actual[field],'INPUT_BINDING_MISMATCH')
                    need(proposed==actual,'ADAPTER_RESULT_MISMATCH')
        st.advance_clock(t);self._check_exact(st)
        slot=st.at[1] if st.at[0]==t else 0;st.at=(t,slot)
        return dict(applied_keys=applied,duplicate_keys=duplicates,no_op_slots=noops,generated=generated)

    def _check_exact(self,st):
        cap=self.config['limits']['max_exact_integer_bits']
        for k in ('cash','A','L'):
            f=Fraction(st.meta(k,self.config['initial_cash_usdt'] if k=='cash' else '0'))
            need(max(abs(f.numerator).bit_length(),f.denominator.bit_length())<=cap,'RESOURCE_EXHAUSTED','/exact_integer')

    def advance(self,request):
        self._assert_thread()
        if type(request) is dict:
            for e in request.get('imported',[]) if type(request.get('imported')) is list else []:
                if type(e) is dict and type(e.get('body')) is dict:
                    for field in ('fill_price','multiplier','fee_fraction','signed_amount_usdt','cumulative_signed_total_usdt','mark_price','reserved_margin_usdt','reserved_fees_usdt'):
                        need(type(e['body'].get(field)) is not float,'INVALID_DECIMAL')
        strict_json(request);raw=canonical_bytes(request);sha=hashlib.sha256(raw).hexdigest()
        rid=request.get('request_id') if type(request) is dict else None
        saved=self.index.db.execute('SELECT sha,seq FROM requests WHERE id=?',(rid,)).fetchone() if type(rid) is str else None
        if saved and saved[0]==sha:
            self._assert_active();r=self._receipt(saved[1]);r['status']='replayed';return r
        if not saved and type(request) is dict and request.get('expected_audit_prefix')!=self.head['audit_prefix']:
            error=LedgerError('PREFIX_MISMATCH');self._failure(error,request,read=False);raise error
        self._assert_active();before=deepcopy(self.head);roots=dict(self.state.roots);publication=False
        try:
            guard=f'guard-input-{self.control["seq"]+1:08}.json';_atomic(self.root/guard,request)
            guardraw=(self.root/guard).read_bytes();self.guard_input=dict(relative_path=guard,sha256=hashlib.sha256(guardraw).hexdigest(),bytes=len(guardraw),rows=1)
            self._control('write_guard',request)
        except (OSError,LedgerError) as e:
            self.unknown=True;raise LedgerError('COMMIT_OUTCOME_UNKNOWN',disposition='inspect_committed_head',before=before) from e
        try:
            shape(request,'request_id expected_audit_prefix through_us imported generated');ident(rid);integer(request['through_us'])
            need(not saved,'REQUEST_CONFLICT');need(len(raw)<=self.config['limits']['max_transaction_bytes'],'RESOURCE_EXHAUSTED')
            need(len(request['imported'])<=self.config['limits']['max_transaction_records'],'RESOURCE_EXHAUSTED')
            self._bound();self.index.db.commit();self.index.db.execute('BEGIN');seq=before['committed_seq']+1;self.index.birth=seq
            try:result=self._stage(request)
            except (KeyError,TypeError,IndexError,StopIteration,ValueError) as error:
                if isinstance(error,LedgerError):raise
                raise LedgerError('SCHEMA_VIOLATION') from error
            self._bound();cutoff=dict(at_us=request['through_us'],slot=self.state.at[1]);self._frame(self.state,cutoff)
            view=self.state.view(cutoff);self._frame(self.state,cutoff);self._remember_view(view,self.state.roots)
            after=dict(ledger_id=self.config['ledger_id'],committed_seq=seq,cutoff=cutoff,economic_state_sha256=view['economic_state_sha256'],status='ACTIVE')
            core=dict(request_id=rid,request_sha256=sha,status='committed',before=before,after=after,
                entries=self._handle(view,'entries'),registry_from=self.state.meta('registry_start',1),registry_to=self.state.meta('registry_next',1)-1,
                **{k:result[k] for k in ('applied_keys','duplicate_keys','no_op_slots')})
            payload=dict(request=request,receipt=core,roots=self.state.roots,generated=result['generated'],frames=self.state.frames)
            self.state.frames=[]
            profile=self.config.get('journal_storage')
            if profile:
                from research.qd015 import journal
                try:encoded=journal.encode(canonical_bytes(payload)+b'\n',profile)
                except journal.JournalError as e:raise LedgerError('RESOURCE_EXHAUSTED','/journal_encode') from e
                name=f'journal-{seq:08}.qjz';_atomic(self.root/name,None,_raw=encoded)
            else:
                name=f'journal-{seq:08}.json';_atomic(self.root/name,payload)
            data=(self.root/name).read_bytes()
            file=dict(relative_path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),rows=1)
            manifest=dict(seq=seq,previous_prefix=before['audit_prefix'],request_id=rid,request_sha256=sha,before=before,after=after,files=[file])
            _atomic(self.root/f'manifest-{seq:08}.json',manifest);prefix=digest(manifest)
            self._bound();self._control('validated',request)
            self.index.db.execute('INSERT INTO requests VALUES (?,?,?)',(rid,sha,seq))
            self.index.db.execute('INSERT OR REPLACE INTO local_meta VALUES ("head",?)',(prefix,))
            self.index.db.execute('INSERT OR REPLACE INTO commits VALUES (?,?,?)',(seq,cutoff['at_us'],prefix))
            self.index.prune(self.state.roots);self.index.db.commit();self.index.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            publication=True;_atomic(self.root/'HEAD',dict(after,audit_prefix=prefix));self.head=dict(after,audit_prefix=prefix)
            self._append_audit('commit',manifest=manifest);self._save_spent();self._control('resolution',request,'committed')
            return self._receipt(seq)
        except LedgerError as e:
            if publication:self.unknown=True;raise LedgerError('COMMIT_OUTCOME_UNKNOWN',before=before,disposition='inspect_committed_head') from e
            self.index.db.rollback();self.index.cache.clear();self.index.size=0;self.state=State(self.index,self.config,roots);self.head=before
            e.receipt.update(request_id=rid,before=before,input_sha256=sha,disposition='stop_resource' if e.code=='RESOURCE_EXHAUSTED' else 'quarantine')
            e.receipt['null_reasons']={}
            try:
                self._failure(e,request,read=False);self._control('resource_stop' if e.code=='RESOURCE_EXHAUSTED' else 'integrity_stop',request,error=e.receipt)
            except (OSError,LedgerError) as failure:
                self.unknown=True;raise LedgerError('COMMIT_OUTCOME_UNKNOWN',before=before,disposition='inspect_committed_head') from failure
            raise
        except OSError as e:
            self.index.db.rollback();self.index.cache.clear();self.index.size=0;self.state=State(self.index,self.config,roots);self.head=before;self.unknown=True
            raise LedgerError('COMMIT_OUTCOME_UNKNOWN',before=before,disposition='inspect_committed_head') from e

    def _receipt(self,seq):
        p=self._payload(seq);r=deepcopy(p['receipt']);m=load_json((self.root/f'manifest-{seq:08}.json').read_bytes());r['after']['audit_prefix']=digest(m);return r

    @staticmethod
    def _handle(view,c):
        return dict(next(x for x in view['components'] if x['component']==c),view_sha256=view['view_sha256'])

    def _remember_view(self,view,roots):
        self.index.db.execute('INSERT OR REPLACE INTO views VALUES (?,?,?)',(view['view_sha256'],canonical_bytes(view),canonical_bytes(roots)))

    def _cutoff(self,cutoff):
        shape(cutoff,'at_us slot');t=integer(cutoff['at_us']);slot=integer(cutoff['slot'])
        need(self.head['committed_seq'] and self.config['initial_at_us']<=t<=self.head['cutoff']['at_us'])
        tick=self.config['_plan_index'].tick(t)
        maxslot=len(tick['slots']) if tick and self.config['ingestion_mode']=='controlled_adapters' else 0
        need(slot<=maxslot and (t,slot)<=tuple(self.head['cutoff'][x] for x in ('at_us','slot')))
        return t,slot

    def _at(self,cutoff):
        t,slot=self._cutoff(cutoff)
        if self.config['ingestion_mode']=='controlled_adapters':
            found=self.index.floor('_timeline',self.state.root('_timeline'),[t,slot]);need(found is not None,'STORE_INTEGRITY_FAILURE')
            s=State(self.index,self.config,found[1]);s.at=(t,slot);return s
        row=self.index.db.execute('SELECT seq FROM commits WHERE at<=? ORDER BY seq DESC LIMIT 1',(t,)).fetchone()
        seq=row[0] if row else 0
        roots=self._payload(seq)['roots'] if seq else self._genesis_roots
        s=State(self.index,self.config,roots)
        nextrow=self.index.db.execute('SELECT seq FROM commits WHERE seq>? ORDER BY seq LIMIT 1',(seq,)).fetchone()
        if nextrow:
            p=self._payload(nextrow[0]);oldhead=self.head
            self.head=p['receipt']['before']
            try:self._stage(p['request'],s,cutoff)
            finally:self.head=oldhead
        s.at=(t,slot);return s

    def as_known(self,request):
        shape(request,'cutoff');self._assert_active()
        s=self._at(request['cutoff']);v=s.view(request['cutoff']);self._remember_view(v,s.roots);return deepcopy(v)

    def restated(self,request):
        shape(request,'economic_at_us knowledge_cutoff');self._assert_active();self._cutoff(request['knowledge_cutoff']);t=integer(request['economic_at_us'])
        need(self.config['initial_at_us']<=t<=request['knowledge_cutoff']['at_us'])
        known=self._at(request['knowledge_cutoff']);st=State(self.index,self.config,self._genesis_roots)
        d=self.index.db;d.execute('CREATE TEMP TABLE IF NOT EXISTS restate(at INTEGER,econ INTEGER,stage INTEGER,k TEXT,b BLOB)')
        d.execute('DELETE FROM restate')
        for key,e in known.rows('events'):
            r=e['body']
            if economic_time(r)<=t:
                stage={'Valuation':0,'Reserves':0,'Fill':2,'FundingSnapshot':3,'ObligationRevision':4,'Posting':5,'CompletenessAssertion':6}[r['record_type']]
                d.execute('INSERT INTO restate VALUES (?,?,?,?,?)',(r['available_at_us'],economic_time(r),stage,sl_key(key),canonical_bytes(e)))
        oldhead=self.head;self.head=dict(oldhead,committed_seq=0);pending=[];available=None
        try:
            for at,blob in d.execute('SELECT at,b FROM restate ORDER BY at,econ,stage,k'):
                if available is not None and at!=available:
                    self._group(pending,st,[],[]);pending=[]
                pending.append(load_json(blob));available=at
                need(len(pending)<=self.config['limits']['max_transaction_records'],'RESOURCE_EXHAUSTED_READ')
            if pending:self._group(pending,st,[],[])
        finally:self.head=oldhead;d.execute('DELETE FROM restate')
        for component in ('query_status','reserve_dependencies'):
            for key,value in known.rows(component):
                if component=='query_status' and value['key']['query_at_us']>t:continue
                if component=='reserve_dependencies' and st.get('events',list(value['reserve_key'][k] for k in ('instrument_id','record_type','record_id','revision'))) is None:continue
                st.set(component,key,value)
                if component=='query_status':st.set('_query_times',key[:3],True)
        st.advance_clock(t);v=st.view(dict(at_us=t,slot=0),True);v['knowledge_cutoff']=request['knowledge_cutoff'];v['balance']['knowledge_cutoff_us']=request['knowledge_cutoff']['at_us']
        ec=dict(view='restated',economic_at_us=t,knowledge_cutoff=v['knowledge_cutoff'],causal_policy_sha256=v['causal_policy_sha256'],balance=v['balance'],economic_component_roots=[x for x in v['components'] if x['component'] in ECONOMIC],coverage=v['coverage'])
        v['economic_state_sha256']=digest(['qf009.economic-state-v3',ec]);v.pop('view_sha256');v['view_sha256']=digest(['qf009.view-v3',v]);self._remember_view(v,st.roots);return v

    def scan(self,request):
        shape(request,'view_sha256 component filter after limit null_reasons');self._assert_active();c=request['component'];need(c in COMPONENTS)
        limit=integer(request['limit'],1);need(limit<=min(256,self.config['limits']['max_page_items']),'RESOURCE_EXHAUSTED_READ')
        row=self.index.db.execute('SELECT b,roots FROM views WHERE h=?',(request['view_sha256'],)).fetchone();need(row is not None)
        view=load_json(row[0]);roots=load_json(row[1]);need(digest(['qf009.view-v3',{k:v for k,v in view.items() if k!='view_sha256'}])==request['view_sha256'],'STORE_INTEGRITY_FAILURE')
        filt=request['filter'];kind=filt.get('kind');after=request['after']
        if kind=='all':shape(filt,'kind')
        elif kind=='owner':
            shape(filt,'kind owner_kind owner_id');allowed={'lots':('lot',),'closed_slices':('lot',),'obligations':('obligation',),'entries':('obligation',),'links':('lot','obligation'),'registry':('adapter',),'adapter_states':('adapter',),'orders':('order',),'decisions':('decision',)}
            need(filt['owner_kind'] in allowed.get(c,()))
        elif kind=='record':
            shape(filt,'kind key');need(c in ('events','reserve_dependencies'))
            if c=='reserve_dependencies':need(filt['key']['record_type']=='Reserves')
        elif kind=='query':shape(filt,'kind key');need(c=='query_status')
        else:raise LedgerError('SCHEMA_VIOLATION')
        last=None
        if after is None:need(request['null_reasons']=={'after':'START_OF_COMPONENT'})
        else:
            need(request['null_reasons']=={},'NULL_REASON_CONTRACT')
            shape(after,'view_sha256 component filter last_business_key');need(all(after[k]==request[k] for k in ('view_sha256','component','filter')))
            last=after['last_business_key'];need(self.index.get(c,roots.get(c,self.index.empty(c)),last) is not None)
        def matches(k,v):
            if kind=='all':return True
            if kind=='record':return (key_of(v['body']) if c=='events' else v['reserve_key'])==filt['key']
            if kind=='query':return v['key']==filt['key']
            owner=filt['owner_kind'];id=filt['owner_id']
            if c=='links':return v['owner_kind']==owner and v['owner_id']==id
            if c=='orders':return v['intent']['order_id']==id
            return v.get({'lot':'lot_id','obligation':'obligation_id','adapter':'adapter_id','decision':'decision_id'}[owner])==id
        items=[];keys=[];more=False
        for k,v in self.index.items(c,roots.get(c,self.index.empty(c)),last):
            if not matches(k,v):continue
            if len(items)==limit:more=True;break
            items.append(v);keys.append(k)
        token=dict(view_sha256=request['view_sha256'],component=c,filter=filt,last_business_key=keys[-1]) if more else None
        page=dict(view_sha256=request['view_sha256'],component=c,items=items,next=token,null_reasons={} if more else {'next':'END_OF_COMPONENT'})
        need(len(canonical_bytes(page))<=self.config['limits']['max_page_bytes'],'RESOURCE_EXHAUSTED_READ');return page

    def readiness(self,request):
        shape(request,'episode_id cutoff');self._assert_active();s=self._at(request['cutoff']);return s.readiness(request['episode_id'],request['cutoff']['at_us'])

    def _fact_candidates(self,selector,schema,at,allowed_at=None):
        """Immutable-source selection; fetch only the records the packet exposes.

        Closure legality is checked over newly eligible rows before limiting,
        including older rows that latest selection will not expose. The memo and
        operation counts are rebuildable local instrumentation, never evidence.
        """
        stats=self.__dict__.setdefault('_fact_selection_work',dict(queries=0,rows=0,closure_queries=0))
        mode=selector['mode'];insts=sorted(selector['instruments']);sid=selector['schema_id']
        if at>=self.config['end_exclusive_us'] and schema['view_kind'] in ('closed_bar','execution_open','mark_point','mark_selection','synthetic_price'):
            return
        lower=None if sid in self.config['initial_context']['schemas'] else self.config['initial_at_us']
        base='schema_id=? AND inst=? AND available<=?';args=lambda i:[sid,i,at]
        if lower is not None:base+=' AND available>=?';args=lambda i:[sid,i,at,lower]
        if schema['view_kind']=='closed_bar':
            checked=self.__dict__.setdefault('_fact_closure_checked',{})
            for i in insts:
                key=(sid,i,lower);previous=checked.get(key)
                if previous is not None and previous>=at:continue
                where=base;values=args(i)
                if previous is not None:where+=' AND available>?';values.append(previous)
                stats['closure_queries']+=1
                bad=self.index.db.execute('SELECT 1 FROM facts WHERE '+where+' AND at>available-? LIMIT 1',values+[schema['interval_us']]).fetchone()
                need(bad is None,'FUTURE_DEPENDENCY');checked[key]=at
        selected=[]
        for i in insts:
            sources=allowed_at.get(i,[]) if allowed_at is not None else [None]
            for source_at in sources:
                where=base;values=args(i)
                if mode=='qualified_at_slot' or source_at is not None:
                    where+=' AND at=?';values.append(at if source_at is None else source_at)
                stats['queries']+=1
                order=' ORDER BY available DESC,k DESC LIMIT 1' if mode=='latest_available' else ' ORDER BY available,k'
                cursor=self.index.db.execute('SELECT available,k,b FROM facts WHERE '+where+order,values)
                if mode=='latest_available':
                    row=cursor.fetchone()
                    if row:selected.append(row)
                else:selected.append(cursor)
        if mode=='latest_available':records=iter(sorted(selected,key=lambda r:(r[0],r[1])))
        else:
            import heapq
            records=heapq.merge(*selected,key=lambda r:(r[0],r[1]))
        for _,_,blob in records:
            stats['rows']+=1
            yield (blob,)

    def _invoke(self,st,slot):
        definition=self.config['_adapters'][slot['adapter_id']];port=_PORTS.get(digest(definition));need(port is not None,'UNSUPPORTED_GENERATOR')
        at=dict(at_us=st.at[0],slot=st.at[1]);before_at=dict(at_us=st.at[0],slot=st.at[1]-1)
        previous=st.meta('adapter_cursor:'+slot['adapter_id']);prior=st.get('adapter_states',[slot['adapter_id']])
        facts=[];reads=[];bindings=[];selections=[];peers=[];selected_orders=[]
        allow={'policy':('closed_bar','funding_rate','synthetic_price'), 'execution':('closed_bar','execution_open','mark_point','mark_selection','synthetic_price'),
               'environment':('mark_point','mark_selection','funding_rate','billed_total','synthetic_price')}
        for selector in sorted(definition['fact_selectors'],key=lambda v:v['selection_id']):
            shape(selector,'selection_id schema_id instruments mode');schema=self.schema(selector['schema_id']);mode=selector['mode'];need(schema['view_kind'] in allow[definition['role']],'FORBIDDEN_INPUT')
            need((mode=='qualified_at_slot')==(schema['view_kind']=='mark_selection'),'FORBIDDEN_INPUT')
            selected=[];selected_bytes=0;selected_reads=0
            allowed_at=None
            if mode=='qd014.pending-funding.v1':
                need(self.config['_plan_index'].compact and definition['adapter_id']=='environment' and schema['view_kind']=='funding_rate','FORBIDDEN_INPUT')
                allowed_at={i:[] for i in selector['instruments']}
                for item in self.config['_plan_index'].pending(prior):
                    allowed_at[item['instrument_id']].append(item['snapshot_at_us'])
            for (blob,) in self._fact_candidates(selector,schema,at['at_us'],allowed_at=allowed_at):
                r=load_json(blob)
                if r['instrument_id'] not in selector['instruments']:continue
                if at['at_us']>=self.config['end_exclusive_us'] and schema['view_kind'] in ('closed_bar','execution_open','mark_point','mark_selection','synthetic_price'):continue
                if r['scenario_available_at_us']<self.config['initial_at_us'] and r['schema_id'] not in self.config['initial_context']['schemas']:continue
                if mode=='qualified_at_slot' and r['economic_at_us']!=at['at_us']:continue
                need(schema['view_kind']!='closed_bar' or r['economic_at_us']+schema['interval_us']<=r['scenario_available_at_us'],'FUTURE_DEPENDENCY')
                selected_bytes+=len(canonical_bytes(self.projection(r)));selected_reads+=len(r['cells'])
                need(selected_reads+len(reads)<=self.config['limits']['max_adapter_reads'] and selected_bytes<=self.config['limits']['max_adapter_input_bytes'],'RESOURCE_EXHAUSTED')
                selected.append(r)
            if mode=='latest_available':
                latest={}
                for r in selected:latest[r['instrument_id']]=r
                selected=sorted(latest.values(),key=lambda r:(r['scenario_available_at_us'],r['fact_key']))
            if mode=='qualified_at_slot' and at['at_us']<self.config['end_exclusive_us']:need(selected,'INPUT_BINDING_MISMATCH')
            projections=[self.projection(r) for r in selected];facts+=projections
            for r in selected:
                for cell in r['cells']:reads.append(dict(kind='fact',fact_key=r['fact_key'],field=cell['name'],cell=cell['cell'],raw_refs=r['raw_refs']))
            bindings.append(dict(selection_id=selector['selection_id'],source_cutoff=before_at,source_roots=[dict(component='facts',root_sha256=digest(projections))],item_count=len(projections),
                                 selected_keys_sha256=digest([r['fact_key'] for r in selected]),selected_values_sha256=digest(projections)))
        for selector in sorted(definition['ledger_selectors'],key=lambda v:v['selection_id']):
            shape(selector,'selection_id instruments kind');kind=selector['kind'];items=[];insts=selector['instruments']
            if kind=='live_lots':
                for inst in insts:
                    for l in st.live(inst):items.append(dict(kind='live_lot',value={k:v for k,v in l.items() if k not in ('initial_contracts','remaining_contracts','closed_slice_count','closed_slices_root')}))
            elif kind=='orders_active_and_changed':
                orderids=set();lower=previous or dict(at_us=self.config['initial_at_us'],slot=0)
                for inst in insts:
                    for key,_ in st.rows('_active_orders',prefix=[inst]):orderids.add(key[1])
                for _,id in st.rows('_order_changes',after=[lower['at_us'],lower['slot'],'~']):
                    order=st.get('orders',[id])
                    if order['intent']['instrument_id'] in insts:orderids.add(id)
                    need(len(orderids)<=self.config['limits']['max_adapter_reads'],'RESOURCE_EXHAUSTED')
                for id in sorted(orderids):
                    order=st.get('orders',[id]);items.append(dict(kind='order',value=order));selected_orders.append(order)
            elif kind=='decisions_for_selected_orders':
                need(definition['role']!='environment','FORBIDDEN_INPUT');ids=sorted({o['intent']['decision_id'] for o in selected_orders})
                items=[dict(kind='decision',value=st.get('decisions',[id])) for id in ids]
            elif kind=='financial_changes':
                lower=previous or dict(at_us=self.config['initial_at_us'],slot=0)
                for key,r in st.rows('_accepted',after=[lower['at_us'],lower['slot'],'~']):
                    if r['instrument_id'] in insts:items.append(dict(kind='financial',value=r))
            elif kind in ('episode_lots','episode_slices','episode_obligations'):
                component={'episode_lots':'lots','episode_slices':'closed_slices','episode_obligations':'obligations'}[kind]
                # Episode reverse indexes bound the retained affected subset.
                for eid in prior['tracked_episode_ids']:
                    if component=='obligations':
                        values=(st.location('obligations',k[1]) for k,_ in st.rows('_ep_ob',prefix=[eid]))
                    else:values=(st.location(component,id) for _,id in st.rows('_ep_lots' if component=='lots' else '_ep_slices',prefix=[eid]))
                    for v in values:
                        inst=v.get('instrument_id',st.location('lots',v.get('lot_id',''))['instrument_id'] if component=='closed_slices' else None)
                        if inst in insts:items.append(dict(kind={'lots':'lot','closed_slices':'slice','obligations':'obligation'}[component],value=v))
            elif kind=='mark_context':
                for inst in insts:
                    _,keys,_=st.query_cohort(inst,at['at_us'])
                    due=self.config['_plan_index'].for_slot(slot['slot_id'],inst,at['at_us'])
                    for key in sorted({canonical_bytes(x):x for x in keys+due}.values(),key=canonical_bytes):
                        v=st.get('query_status',[inst,key['clock_id'],key['query_at_us'],key['purpose']]);need(v is not None,'INPUT_BINDING_MISMATCH');items.append(dict(kind='query_status',value=v))
                    found=self.index.floor('_reserves',st.root('_reserves'),[inst,at['at_us'],2**63-1,'~'])
                    if found and found[0][0]==inst:
                        dep=st.get('reserve_dependencies',list(wire_key(found[1])))
                        if dep:items.append(dict(kind='reserve_dependency',value=dep))
            else:raise LedgerError('FORBIDDEN_INPUT')
            need(len(items)+len(reads)<=self.config['limits']['max_adapter_reads'],'RESOURCE_EXHAUSTED')
            selections.append(dict(selection_id=selector['selection_id'],items=items))
            keys=[]
            for i,item in enumerate(items):
                key=_item_key(item);keys.append(key);reads.append(dict(kind='ledger',selection_id=selector['selection_id'],item_kind=item['kind'],business_key=key,source_cutoff=before_at,value=item))
            bindings.append(dict(selection_id=selector['selection_id'],source_cutoff=before_at,source_roots=[dict(component=c,root_sha256=st.root(c)) for c in ECONOMIC],item_count=len(items),selected_keys_sha256=digest(keys),selected_values_sha256=digest(items)))
        for selector in definition['peer_state_selectors']:
            need(definition['role']!='environment' and selector['adapter_id']!=definition['adapter_id'],'FORBIDDEN_INPUT')
            peer=st.get('adapter_states',[selector['adapter_id']]);need(peer is not None,'INPUT_BINDING_MISMATCH');peers.append(peer)
        for state in [prior]+peers:reads.append(dict(kind='state',adapter_id=state['adapter_id'],source_cutoff=before_at,state=state))
        view=st.view(before_at);economic={k:v for k,v in view.items() if k not in ('components','view_sha256')};economic['economic_component_roots']=[x for x in view['components'] if x['component'] in ECONOMIC]
        packet=dict(slot=at,slot_id=slot['slot_id'],causal_policy_sha256=self.config['_policy_hash'],permitted_facts=facts,before=economic,
                    economic_inputs=selections,peer_states=peers,previous_invocation=previous,prior_state=prior,causal_config=self.config['_plan_index'].window(definition,prior,at['at_us']) if self.config['_plan_index'].compact else definition['causal_config'])
        limits=self.config['limits'];need(len(reads)<=limits['max_adapter_reads'] and len(canonical_bytes(packet))<=limits['max_adapter_input_bytes'],'RESOURCE_EXHAUSTED')
        start=_clock();_GUARD.active=True
        try:
            port.validate_input(deepcopy(packet));port.validate_state(deepcopy(prior));result=port.evaluate(deepcopy(packet));strict_json(result);port.validate_output(deepcopy(result))
        finally:_GUARD.active=False
        need((_clock()-start)*1000000<=limits['max_adapter_wall_us'],'RESOURCE_EXHAUSTED')
        shape(result,'outcome events decisions orders order_transitions reserve_dependencies next_state');need(result['outcome'] in ('emit','noop'))
        need(result['outcome']!='noop' or not result['events'],'INPUT_BINDING_MISMATCH')
        need(len(result['events'])<=limits['max_adapter_emitted_events'] and len(canonical_bytes(result['next_state']))<=limits['max_adapter_state_bytes'],'RESOURCE_EXHAUSTED')
        _validate_state(result['next_state'],definition);_GUARD.active=True
        try:port.validate_state(deepcopy(result['next_state']))
        finally:_GUARD.active=False
        seq=st.meta('registry_next',1);st.putmeta('registry_next',seq+1)
        entry=dict(registry_seq=seq,slot=at,slot_id=slot['slot_id'],adapter_id=definition['adapter_id'],parent_audit_prefix=self.head['audit_prefix'],
           parent_registry_sha256=st.meta('registry_last',digest(['qf009.registry-v3',self.config['ledger_id'],'genesis'])),before_economic_state=view['economic_state_sha256'],
           adapter_definition_sha256=digest(definition),input_projection_sha256=digest(packet),prior_adapter_state_sha256=prior['state_sha256'],reads=reads,selection_bindings=bindings,result=result,result_sha256=digest(result))
        entry['entry_sha256']=digest(entry);return entry

    def _accept_result(self,st,slot,g,applied,duplicates):
        result=g['result'];role=self.config['_adapters'][slot['adapter_id']]['role'];at=g['slot'];inputs=g['input_projection_sha256']
        if at['at_us']>=self.config['end_exclusive_us']:
            need(not result['decisions'] and not result['orders'] and all(r['record_type'] in ('ObligationRevision','Posting','CompletenessAssertion') for r in result['events']),'ORIGIN_OUT_OF_RANGE')
        for i,d in enumerate(result['decisions']):
            need(role=='policy','FORBIDDEN_INPUT');shape(d,'decision_id at_us instrument_id order_ids input_projection_sha256 prior_adapter_state_sha256 intent_contract_sha256 intent')
            need(d['decision_id']==business_id(self.config,d['instrument_id'],'decision',at['at_us'],slot['slot_id'],i),'INPUT_BINDING_MISMATCH')
            need(d['at_us']==at['at_us'] and d['input_projection_sha256']==inputs and d['prior_adapter_state_sha256']==g['prior_adapter_state_sha256'],'INPUT_BINDING_MISMATCH')
            st.own('decision',d['decision_id'],d['instrument_id']);need(st.get('decisions',[d['decision_id']]) is None,'INPUT_BINDING_MISMATCH');st.set('decisions',[d['decision_id']],d)
        for i,o in enumerate(result['orders']):
            need(role=='policy','FORBIDDEN_INPUT');shape(o,'order_id decision_id instrument_id action direction requested_contracts submitted_at_us eligible_at_us expires_at_us payload_contract_sha256 payload')
            need(o['order_id']==business_id(self.config,o['instrument_id'],'order',at['at_us'],slot['slot_id'],i),'INPUT_BINDING_MISMATCH')
            d=st.get('decisions',[o['decision_id']]);need(d and o['order_id'] in d['order_ids'] and d['instrument_id']==o['instrument_id'],'INPUT_BINDING_MISMATCH')
            need(o['submitted_at_us']==at['at_us']<=o['eligible_at_us'] and o['expires_at_us']>at['at_us'],'CLOCK_CONTRADICTION');integer(o['requested_contracts'],1)
            st.own('order',o['order_id'],o['instrument_id']);need(st.get('orders',[o['order_id']]) is None,'INPUT_BINDING_MISMATCH')
            st.set('orders',[o['order_id']],dict(intent=o,status='pending',filled_contracts=0,remaining_contracts=o['requested_contracts'],last_changed=at,fill_keys=[],terminal_reason=None))
            st.set('_active_orders',[o['instrument_id'],o['order_id']],True)
            st.set('_order_changes',[at['at_us'],at['slot'],o['order_id']],o['order_id'])
        envelopes=[]
        for i,body in enumerate(result['events']):
            r=normalize_body(body)
            need(not self.head['committed_seq'] or r['available_at_us']>self.head['cutoff']['at_us'],'PAST_AVAILABILITY')
            need(r['available_at_us']==at['at_us'],'FUTURE_DEPENDENCY')
            if r['record_type'] in ('Fill','Posting'):
                kind='fill' if r['record_type']=='Fill' else 'posting';need(r['record_id']==business_id(self.config,r['instrument_id'],kind,at['at_us'],slot['slot_id'],i),'INPUT_BINDING_MISMATCH')
            if r['record_type']=='Fill':
                need(role=='execution','FORBIDDEN_INPUT');o=st.get('orders',[r['order_id']]);d=st.get('decisions',[r['decision_id']])
                need(o and d and o['intent']['decision_id']==d['decision_id'] and o['intent']['instrument_id']==r['instrument_id'],'INPUT_BINDING_MISMATCH')
                need(o['status'] in ('pending','partially_filled') and o['intent']['eligible_at_us']<=r['filled_at_us']<o['intent']['expires_at_us'],'SCHEDULE_MISMATCH')
                need(r['decision_at_us']==d['at_us'] and abs(r['signed_contracts'])<=o['remaining_contracts'],'INPUT_BINDING_MISMATCH')
                o['filled_contracts']+=abs(r['signed_contracts']);o['remaining_contracts']-=abs(r['signed_contracts']);o['fill_keys'].append(key_of(r));o['last_changed']=at
                st.set('orders',[r['order_id']],o)
                st.set('_order_changes',[at['at_us'],at['slot'],r['order_id']],r['order_id'])
            envelopes.append(dict(namespace=NS,schema_version=VERSION,profile=PROFILE,body=r,origin=dict(kind='generated',registry_seq=g['registry_seq'],output_index=i),created_at_us=at['at_us']))
        self._group(envelopes,st,applied,duplicates)
        for dep in result['reserve_dependencies']:
            shape(dep,'reserve_key margin fees');key=dep['reserve_key'];need(key['record_type']=='Reserves' and st.get('events',list(key[k] for k in ('instrument_id','record_type','record_id','revision'))) is not None,'INPUT_BINDING_MISMATCH')
            for field in ('margin','fees'):
                d=dep[field]
                if d['kind']=='independent':shape(d,'kind')
                else:
                    shape(d,'kind query_key');need(d['kind']=='current_mark');q=d['query_key'];need(q['instrument_id']==key['instrument_id'] and q['purpose']=='reservation','INPUT_BINDING_MISMATCH')
                    status=st.get('query_status',[q['instrument_id'],q['clock_id'],q['query_at_us'],q['purpose']]);need(status is not None,'INPUT_BINDING_MISMATCH')
            st.set('reserve_dependencies',list(key[k] for k in ('instrument_id','record_type','record_id','revision')),dep)
        for r in result['events']:
            if r['record_type']=='Reserves' and any(v['instrument_id']==r['instrument_id'] for v in self.config['mark_view_bindings']):need(st.get('reserve_dependencies',list(wire_key(r))) is not None,'INPUT_BINDING_MISMATCH')
        for tr in result['order_transitions']:
            need(role!='environment','FORBIDDEN_INPUT');shape(tr,'order_id at status fill_keys reason');need(tr['at']==at)
            order=st.get('orders',[tr['order_id']]);need(order is not None and order['status'] not in ('cancelled','expired','filled'),'INPUT_BINDING_MISMATCH')
            need(all(k in order['fill_keys'] for k in tr['fill_keys']),'INPUT_BINDING_MISMATCH')
            status=tr['status'];need(status in ('partially_filled','filled','cancelled','expired'))
            need(status!='filled' or order['remaining_contracts']==0,'INPUT_BINDING_MISMATCH');need(status!='partially_filled' or 0<order['filled_contracts']<order['intent']['requested_contracts'],'INPUT_BINDING_MISMATCH')
            order.update(status=status,last_changed=at,terminal_reason=tr['reason'] if status!='partially_filled' else None);st.set('orders',[tr['order_id']],order)
            st.set('_order_changes',[at['at_us'],at['slot'],tr['order_id']],tr['order_id'])
            if status!='partially_filled':st.roots['_active_orders']=self.index.delete('_active_orders',st.root('_active_orders'),[order['intent']['instrument_id'],tr['order_id']])
        st.set('adapter_states',[slot['adapter_id']],result['next_state']);st.putmeta('adapter_cursor:'+slot['adapter_id'],at)
        st.set('registry',[g['registry_seq']],g);st.putmeta('registry_last',g['entry_sha256'])

    def _save_spent(self):
        now=_clock();self.spent['active_wall_us']+=int((now-self.started)*1000000);self.started=now
        self.spent['total_written_bytes']=max(self.spent['total_written_bytes'],self.budget.written)
        _atomic(self.root/'SPENT',self.spent)

    def _rebuild_index(self):
        target=deepcopy(self.head);d=self.index.db
        for table in ('nodes','blobs','requests','commits','views'):d.execute('DELETE FROM '+table)
        self.index.cache.clear();self.index.size=0;self.index.birth=0;st=self._initialize_state();self._genesis_roots=dict(st.roots)
        previous=genesis_head(self.request,st);self.head=previous
        try:
            for seq in range(1,target['committed_seq']+1):
                self._bound();m=load_json((self.root/f'manifest-{seq:08}.json').read_bytes())
                need(m['previous_prefix']==previous['audit_prefix'] and m['before']==previous,'STORE_INTEGRITY_FAILURE')
                p=self._payload(seq);need(digest(p['request'])==m['request_sha256'],'STORE_INTEGRITY_FAILURE');self.index.birth=seq
                result=self._stage(p['request'],st);cutoff=p['receipt']['after']['cutoff'];self._frame(st,cutoff)
                v=st.view(cutoff);self._frame(st,cutoff)
                need(st.frames==p['frames'],'STORE_INTEGRITY_FAILURE');st.frames=[]
                need(st.roots==p['roots'] and result['generated']==p['generated'] and v['economic_state_sha256']==m['after']['economic_state_sha256'],'STORE_INTEGRITY_FAILURE')
                previous=dict(m['after'],audit_prefix=digest(m));self.head=previous
                d.execute('INSERT INTO requests VALUES (?,?,?)',(m['request_id'],m['request_sha256'],seq));d.execute('INSERT INTO commits VALUES (?,?,?)',(seq,cutoff['at_us'],digest(m)))
                self.index.prune(st.roots);d.commit()
            need(previous==target,'STORE_INTEGRITY_FAILURE');d.execute('INSERT OR REPLACE INTO local_meta VALUES ("head",?)',(target['audit_prefix'],));d.commit()
            self.state=st
        finally:self.head=target

    def _fact_cursors(self,at):
        out=[]
        for schema in self.config['fact_schemas']:
            row=self.index.db.execute('SELECT available,k FROM facts WHERE schema_id=? AND available<=? AND (available>=? OR schema_id IN (%s)) ORDER BY available DESC,k DESC LIMIT 1'%(','.join('?' for _ in self.config['initial_context']['schemas']) or 'NULL'),
                (schema['schema_id'],at,self.config['initial_at_us'],*self.config['initial_context']['schemas'])).fetchone()
            out.append(dict(schema_id=schema['schema_id'],last_available_us=row[0] if row else None,last_fact_key=row[1] if row else None))
        return out

    def _query_cursors(self,st,at):
        out=[]
        for c in self.config['mark_clocks']:
            inst,clock=c['instrument_id'],c['clock_id'];plan=self.config['_plan_index']
            admitted=[v['key']['query_at_us'] for _,v in st.rows('query_status',prefix=[inst,clock])];authority=self.index.floor('_query_times',st.root('_query_times'),[inst,clock,at])
            out.append(dict(instrument_id=inst,clock_id=clock,next_requirement_index=plan.cursor_count(inst,clock,at),last_admitted_query_us=max(admitted) if admitted else None,
                            last_authoritative_query_us=authority[0][2] if authority and authority[0][:2]==[inst,clock] else None))
        return out

    def _write_rows(self,relative,rows,component):
        path=_safe_path(self.root,relative);path.parent.mkdir(parents=True,exist_ok=True);pending=path.with_name(path.name+'.'+uuid.uuid4().hex+'.pending')
        count=size=0;h=hashlib.sha256();buffer=bytearray();budget=_budget_for(path)
        # If a previous checkpoint export exists, independently recompute the
        # exact closed rows and compare, never trust a leftover filename.
        if path.exists():
            for row in rows:
                raw=canonical_bytes(row)+b'\n';h.update(raw);size+=len(raw);count+=1
            need(path.stat().st_size==size and _file_sha(path)==h.hexdigest(),'STORE_INTEGRITY_FAILURE')
        else:
            with pending.open('xb') as f:
                for row in rows:
                    raw=canonical_bytes(row)+b'\n';h.update(raw);size+=len(raw);count+=1;buffer.extend(raw)
                    if len(buffer)>=65536:
                        if budget:budget.issue(pending,f.tell()+len(buffer),len(buffer))
                        f.write(buffer);buffer.clear()
                if buffer:
                    if budget:budget.issue(pending,f.tell()+len(buffer),len(buffer))
                    f.write(buffer)
                f.flush();os.fsync(f.fileno())
            os.replace(pending,path)
            if budget:budget.rename(pending,path)
            _fsync_directory(path.parent)
            need(_file_sha(path)==h.hexdigest(),'STORE_INTEGRITY_FAILURE')
        return dict(component=component,relative_path=relative,format_version=3,bytes=size,rows=count,sha256=h.hexdigest())

    def _export_segments(self,upto,verify_all=False):
        cached=getattr(self,'_export_inventory',None)
        if cached is not None and not verify_all and upto>=self._export_upto:
            inventory=deepcopy(cached);start_seq=self._export_upto+1
        else:inventory=[];start_seq=1
        if start_seq==1:
            base={'config':[self.request['config']],'raw_catalogue':[self.request['raw_catalogue']],'adapters':self.config['adapters'],'schedule':iter(self.config['_plan_index'])}
            for component,rows in base.items():inventory.append(self._write_rows('exports/base-'+component+'.jsonl',iter(rows),component))
            def facts():
                for (blob,) in self.index.db.execute('SELECT b FROM facts ORDER BY available,k'):yield load_json(blob)
            inventory.append(self._write_rows('exports/base-facts.jsonl',facts(),'facts'))
            def context():
                yield self.state.meta('context_receipt')
                if self.config['initial_context']['mode']=='closed_fact_prefix':
                    for (blob,) in self.index.db.execute('SELECT b FROM facts WHERE at>=? AND available<? ORDER BY available,k',(self.config['initial_context']['from_us'],self.config['initial_at_us'])):
                        row=load_json(blob)
                        if row['schema_id'] in self.config['initial_context']['schemas']:yield self.projection(row)
            inventory.append(self._write_rows('exports/base-context.jsonl',context(),'context'))
            inventory.append(self._write_rows('exports/base-calendar.jsonl',(dict(entry=e,seen_key=None,null_reasons={'seen_key':'MISSING_EXPECTED_SNAPSHOT'}) for e in self.config['expected_snapshots']),'calendar'))
        for seq in range(start_seq,upto+1):
            payload=self._payload(seq)
            # Export immutable segment rows once; subsequent checkpoints reuse
            # the same confined file identities, not repeated full snapshots.
            for ordinal,frame in enumerate(payload['frames']):
                cutoff=frame['cutoff'];prefix=f'exports/{seq:08}-{ordinal:04}-'
                items=frame['projection'];private=frame['private']
                inventory.append(self._write_rows(prefix+'projection.jsonl',(dict(cutoff=cutoff,**row) for row in items),'projection'))
                for component in ('adapter_states','orders','decisions','query_status','reserve_dependencies'):
                    rows=[row['item'] for row in items if row['component']==component]
                    if rows:inventory.append(self._write_rows(prefix+component+'.jsonl',iter(rows),component))
                registry=[row['item'] for row in items if row['component']=='registry']
                if registry:inventory.append(self._write_rows(prefix+'registry.jsonl',iter(registry),'registry'))
                events=[dict(committed_seq=seq,slot=cutoff,envelope=row['item']) for row in items if row['component']=='events']
                if events:inventory.append(self._write_rows(prefix+'journal.jsonl',iter(events),'journal'))
                owners=[dict(kind=row['key'][0],entity_id=row['key'][1],instrument_id=row['value'][0],trajectory_id=row['value'][1],scenario_id=row['value'][2]) for row in private if row['component']=='_owners']
                if owners:inventory.append(self._write_rows(prefix+'ownership.jsonl',iter(owners),'ownership'))
                dedup=[row['value'] for row in private if row['component']=='_dedup']
                if dedup:inventory.append(self._write_rows(prefix+'dedup.jsonl',iter(dedup),'dedup'))
                revisions=[dict(kind='obligation' if row['component']=='_revisions' else 'assertion',entity_id=row['key'][0],revision=row['key'][1],key=key_of(row['value']),cutoff=cutoff) for row in private if row['component'] in ('_revisions','_assertion_versions')]
                if revisions:inventory.append(self._write_rows(prefix+'revisions.jsonl',iter(revisions),'revisions'))
                calendar=[dict(entry=self.config['_calendar_by_id'][(row['value']['instrument_id'],row['value']['record_id'])],seen_key=key_of(row['value']),null_reasons={}) for row in private if row['component']=='_snapshots']
                if calendar:inventory.append(self._write_rows(prefix+'calendar.jsonl',iter(calendar),'calendar'))
        self._export_inventory=deepcopy(inventory);self._export_upto=upto
        return inventory

    def checkpoint(self,request):
        shape(request,'expected_head');need(request['expected_head']==self.head['audit_prefix'],'CHECKPOINT_MISMATCH');self._assert_active()
        before=deepcopy(self.head);established=False
        try:
            name=f'guard-input-{self.control["seq"]+1:08}.json';_atomic(self.root/name,request);path=self.root/name
            self.guard_input=dict(relative_path=name,sha256=_file_sha(path),bytes=path.stat().st_size,rows=1);self._control('write_guard',request);established=True
            result=self._checkpoint(request)
            self._control('validated',request);self._save_spent();self._control('resolution',request,'not_committed')
            return result
        except LedgerError as error:
            if not established:
                self.unknown=True;raise LedgerError('COMMIT_OUTCOME_UNKNOWN',before=before,disposition='inspect_committed_head') from error
            if self.control['guard']:
                error.receipt.update(before=before,input_sha256=digest(request),disposition='stop_resource' if error.code=='RESOURCE_EXHAUSTED' else 'quarantine')
                self._failure(error,request,False);self._control('resource_stop' if error.code=='RESOURCE_EXHAUSTED' else 'integrity_stop',request,error=error.receipt)
            raise
        except OSError as error:
            self.unknown=True;raise LedgerError('COMMIT_OUTCOME_UNKNOWN',before=before,disposition='inspect_committed_head') from error

    def _checkpoint(self,request):
        shape(request,'expected_head');need(request['expected_head']==self.head['audit_prefix'],'CHECKPOINT_MISMATCH');self._bound()
        h=self.head;c=self.config;inventory=self._export_segments(h['committed_seq']);self._save_spent()
        fact_cursors=self._fact_cursors(h['cutoff']['at_us'] if h['committed_seq'] else h['cutoff']['at_us']-1);adapter_cursors=[dict(adapter_id=a['adapter_id'],last_invocation=self.state.meta('adapter_cursor:'+a['adapter_id'])) for a in c['adapters']]
        query_cursors=self._query_cursors(self.state,h['cutoff']['at_us'])
        name=f'exports/cursors-{h["committed_seq"]:08}.jsonl'
        inventory.append(self._write_rows(name,iter([dict(kind='fact',value=v) for v in fact_cursors]+[dict(kind='adapter',value=v) for v in adapter_cursors]+[dict(kind='query',value=v) for v in query_cursors]),'cursors'))
        for seq in range(1,self.control['seq']+1):
            path=_safe_path(self.root,f'control-{seq:08}.json');raw=path.read_bytes();inventory.append(dict(component='control',relative_path=path.name,format_version=3,bytes=len(raw),rows=1,sha256=hashlib.sha256(raw).hexdigest()))
        cp=dict(namespace='qf009.streaming-checkpoint',schema_version=VERSION,profile=PROFILE,ledger_id=c['ledger_id'],trajectory_id=c['trajectory_id'],scenario_id=c['scenario_id'],
           committed_seq=h['committed_seq'],cutoff=h['cutoff'],audit_prefix=h['audit_prefix'],economic_state_sha256=h['economic_state_sha256'],config_sha256=digest(self.request['config']),
           causal_policy_sha256=c['_policy_hash'],raw_catalogue_sha256=digest(self.request['raw_catalogue']),fact_store_sha256=self.request['fact_store']['sha256'],adapters_sha256=digest(c['adapters']),schedule_sha256=digest(c['schedule']),
           journal_prefix_sha256=h['audit_prefix'],registry_prefix_sha256=self.state.root('registry'),calendar_cursor=sum(self.state.meta('calendar:'+i,0) for i in c['instruments']),
           next_tick_index=bisect.bisect_right(c['_plan_index'].times,h['cutoff']['at_us']) if h['committed_seq'] else 0,registry_next_seq=self.state.meta('registry_next',1),files=inventory,
           context_receipt=self.state.meta('context_receipt'),fact_cursors=fact_cursors,adapter_cursors=adapter_cursors,query_cursors=query_cursors,
           control_seq=self.control['seq'],control_sha256=self.control['hash'],resource_spent=deepcopy(self.spent),runner_state_coverage='CAPTURED_DECLARED_ADAPTER_STATE_NOT_R3_ACCEPTANCE')
        cp['checkpoint_sha256']=digest(cp);return cp

    def _adopt_control_tail(self,outcome,allow_resolution=False):
        # Do not overwrite a fully written companion whose pointer publication
        # failed. Verify it under the same lease and advance only its control
        # proof; it never imports an orphan financial segment.
        current=self.control;guard=current['guard'];seq=current['seq'];last=current['hash'];tip=None
        if guard is None:return
        for _ in range(64):
            path=_safe_path(self.root,f'control-{seq+1:08}.json')
            if not path.exists():break
            row=load_json(path.read_bytes());h=row.pop('control_sha256')
            need(h==digest(row) and row['previous_control_sha256']==last and all(row[k]==guard[k] for k in ('guard_id','guard_input','request_id','request_sha256')),'STORE_INTEGRITY_FAILURE')
            need(row['kind'] in ('validated','integrity_stop','resource_stop','resolution'),'STORE_INTEGRITY_FAILURE')
            if row['kind']=='resolution':
                if not allow_resolution:break
                need(row['outcome'] in (outcome,'unknown'),'STORE_INTEGRITY_FAILURE')
            with path.open('rb') as source:os.fsync(source.fileno())
            seq+=1;last=h;tip=dict(control_seq=seq,control_sha256=h)
            if row['kind']=='resolution' and row['outcome']!='unknown':break
        else:raise LedgerError('RESOURCE_EXHAUSTED','/control_tail')
        if tip:
            _fsync_directory(self.root);_atomic(self.root/'CONTROL',tip);self.control=self._load_control()

    def resolve_commit(self,request):
        self._assert_thread()
        shape(request,'request_id request_sha256');self._bound();guard=self.control['guard']
        need(guard is None or (guard['request_id']==request['request_id'] and guard['request_sha256']==request['request_sha256']),'REQUEST_CONFLICT')
        try:
            if guard:
                saved_path=_safe_path(self.root,guard['guard_input']['relative_path']);need(saved_path.is_file() and saved_path.stat().st_size==guard['guard_input']['bytes'] and _file_sha(saved_path)==guard['guard_input']['sha256'],'STORE_INTEGRITY_FAILURE')
                saved_value=load_json(saved_path.read_bytes());need(digest(saved_value)==guard['request_sha256'] and saved_value.get('request_id')==guard['request_id'],'STORE_INTEGRITY_FAILURE')
            # Re-fsync every reachable object plus HEAD/CONTROL and the directory;
            # readability alone does not prove durable commit.
            head=load_json((self.root/'HEAD').read_bytes());oldhead=self.head;self.head=head;found=None;prefix=genesis_head(self.request,State(self.index,self.config,self._genesis_roots))['audit_prefix']
            for seq in range(1,head['committed_seq']+1):
                self._bound();m=load_json((self.root/f'manifest-{seq:08}.json').read_bytes());need(m['previous_prefix']==prefix,'STORE_INTEGRITY_FAILURE');prefix=digest(m);p=self._payload(seq)
                if m['request_id']==request['request_id']:
                    need(m['request_sha256']==request['request_sha256'],'REQUEST_CONFLICT');found=seq
                for ref in m['files']:
                    path=_safe_path(self.root,ref['relative_path'])
                    with path.open('rb') as f:os.fsync(f.fileno())
                with (self.root/f'manifest-{seq:08}.json').open('rb') as f:os.fsync(f.fileno())
            need(prefix==head['audit_prefix'],'STORE_INTEGRITY_FAILURE')
            for name in ('HEAD','CONTROL','GENESIS'):
                with (self.root/name).open('rb') as f:os.fsync(f.fileno())
            _fsync_directory(self.root);need(load_json((self.root/'HEAD').read_bytes())==head,'STORE_INTEGRITY_FAILURE')
            self._adopt_control_tail('committed' if found else 'not_committed',bool(found))
            if found:
                self._rebuild_index();outcome='committed';receipt=self._receipt(found)
                for seq in range(1,head['committed_seq']+1):self._append_audit('commit',manifest=load_json(_safe_path(self.root,f'manifest-{seq:08}.json').read_bytes()))
            else:
                self._rebuild_index();outcome='not_committed';receipt=None
                if guard and not self.control.get('validated'):
                    source=_safe_path(self.root,guard['guard_input']['relative_path']);need(_file_sha(source)==guard['guard_input']['sha256'],'STORE_INTEGRITY_FAILURE');saved=load_json(source.read_bytes())
                    roots=dict(self.state.roots);self.index.db.execute('SAVEPOINT admission_resolution')
                    try:
                        if set(saved)=={'request_id','expected_audit_prefix','through_us','imported','generated'}:
                            need(len(saved['imported'])<=self.config['limits']['max_transaction_records'],'RESOURCE_EXHAUSTED');self._stage(saved,State(self.index,self.config,roots))
                        elif set(saved)=={'expected_head'}:need(saved['expected_head']==head['audit_prefix'],'CHECKPOINT_MISMATCH')
                        else:raise LedgerError('SCHEMA_VIOLATION')
                    except LedgerError as error:
                        self.index.db.execute('ROLLBACK TO admission_resolution');self._failure(error,saved,False);self._control('resource_stop' if error.code=='RESOURCE_EXHAUSTED' else 'integrity_stop',saved,error=error.receipt)
                    finally:
                        try:self.index.db.execute('ROLLBACK TO admission_resolution');self.index.db.execute('RELEASE admission_resolution')
                        except sqlite3.Error:pass
            self._adopt_control_tail(outcome,True);self._save_spent()
            if self.control['guard']:
                supplied=load_json(_safe_path(self.root,guard['guard_input']['relative_path']).read_bytes());self.guard_input=guard['guard_input'];self._control('resolution',supplied,outcome)
            self.unknown=None;return dict(request_id=request['request_id'],outcome=outcome,head=self.current_head(),receipt=receipt,null_reasons={} if found else {'receipt':'NOT_COMMITTED'})
        except LedgerError as e:
            if e.code=='REQUEST_CONFLICT':raise
            return dict(request_id=request['request_id'],outcome='unknown',head=None,receipt=None,null_reasons={'head':'COMMIT_OUTCOME_UNKNOWN','receipt':'COMMIT_OUTCOME_UNKNOWN'})
        except OSError:
            return dict(request_id=request['request_id'],outcome='unknown',head=None,receipt=None,null_reasons={'head':'COMMIT_OUTCOME_UNKNOWN','receipt':'COMMIT_OUTCOME_UNKNOWN'})

    def _load_audit(self):
        pointer=self.root/'AUDIT';self.audit_tip=dict(seq=0,hash=digest(['qf009.audit-v3',self.config['ledger_id'],'genesis']))
        if not pointer.exists():return
        tip=load_json(_safe_path(self.root,'AUDIT').read_bytes());cached=self.index.db.execute('SELECT count(*) FROM audit_rows').fetchone()[0]==tip['seq']
        if not cached:self.index.db.execute('DELETE FROM audit_rows')
        for seq in range(1,tip['seq']+1):
            wrapped=load_json(_safe_path(self.root,f'audit-rows/{seq:08}.json').read_bytes());row=wrapped['row']
            need(wrapped['previous']==self.audit_tip['hash'] and wrapped['sha256']==digest({k:v for k,v in wrapped.items() if k!='sha256'}) and row['audit_seq']==seq,'STORE_INTEGRITY_FAILURE')
            if row['kind']=='failure':need(row['failure_sha256']==digest({k:v for k,v in row.items() if k!='failure_sha256'}),'STORE_INTEGRITY_FAILURE')
            else:need(row['prefix']==digest(row['manifest']),'STORE_INTEGRITY_FAILURE')
            expected=(row['kind'],row.get('manifest',{}).get('seq'),wrapped['guard_id'],canonical_bytes(row))
            if cached:need(self.index.db.execute('SELECT kind,commit_seq,guard_id,b FROM audit_rows WHERE seq=?',(seq,)).fetchone()==expected,'STORE_INTEGRITY_FAILURE')
            else:self.index.db.execute('INSERT INTO audit_rows VALUES (?,?,?,?,?)',(seq,*expected))
            self.audit_tip=dict(seq=seq,hash=wrapped['sha256'])
        need(self.audit_tip==tip,'STORE_INTEGRITY_FAILURE');self.index.db.commit()

    def _append_audit(self,kind,manifest=None,error=None):
        if kind=='commit' and self.index.db.execute('SELECT 1 FROM audit_rows WHERE kind="commit" AND commit_seq=?',(manifest['seq'],)).fetchone():return
        seq=self.audit_tip['seq']+1;guard=self.control['guard']['guard_id'] if self.control['guard'] else None
        if kind=='commit':row=dict(audit_seq=seq,kind=kind,manifest=manifest,prefix=digest(manifest))
        else:
            row=dict(audit_seq=seq,kind='failure',at_committed_seq=self.head['committed_seq'],error=deepcopy(error));row['failure_sha256']=digest(row)
        wrapped=dict(row=row,previous=self.audit_tip['hash'],guard_id=guard);wrapped['sha256']=digest(wrapped)
        directory=self.root/'audit-rows';directory.mkdir(exist_ok=True)
        self.budget.emergency=True
        if self.budget.parent:self.budget.parent.emergency=True
        try:
            _atomic(directory/f'{seq:08}.json',wrapped);tip=dict(seq=seq,hash=wrapped['sha256']);_atomic(self.root/'AUDIT',tip)
            self.index.db.execute('INSERT INTO audit_rows VALUES (?,?,?,?,?)',(seq,kind,manifest['seq'] if manifest else None,guard,canonical_bytes(row)));self.index.db.commit();self.audit_tip=tip
        finally:
            self.budget.emergency=False
            if self.budget.parent:self.budget.parent.emergency=False

    def _failure(self,error,request,read=True):
        error.receipt.update(request_id=request.get('request_id') if type(request) is dict else None,before=error.receipt.get('before') or self.current_head(),input_sha256=digest(request),disposition='reject' if read else error.receipt['disposition'])
        error.receipt['null_reasons']={'request_id':'NOT_APPLICABLE' if read else 'UNKNOWN_INPUT_IDENTITY'} if error.receipt['request_id'] is None else {}
        self._append_audit('failure',error=error.receipt)

    def audit(self,request):
        self._assert_thread()
        shape(request,'after_audit_seq limit');start=integer(request['after_audit_seq']);limit=integer(request['limit'],1);need(limit<=256,'RESOURCE_EXHAUSTED_READ')
        rows=[load_json(row[0]) for row in self.index.db.execute('SELECT b FROM audit_rows WHERE seq>? ORDER BY seq LIMIT ?',(start,limit))]
        last=rows[-1]['audit_seq'] if rows else start;more=last<self.audit_tip['seq']
        page=dict(rows=rows,next_after_audit_seq=last if more else None,null_reasons={} if more else {'next_after_audit_seq':'END_OF_AUDIT'})
        need(len(canonical_bytes(page))<=self.config['limits']['max_page_bytes'],'RESOURCE_EXHAUSTED_READ');return page


def sl_key(key):return canonical_bytes(key).decode()

def _audited_read(method):
    def read(self,request):
        self._assert_thread()
        try:return method(self,request)
        except LedgerError as error:
            self._failure(error,request,True);raise
    read.__name__=method.__name__;return read
for _read_name in ('as_known','restated','scan','readiness'):
    setattr(Ledger,_read_name,_audited_read(getattr(Ledger,_read_name)))



def _item_key(item):
    value=item['value'];kind=item['kind']
    if kind=='financial':return list(wire_key(value))
    if kind=='query_status':return [value['key'][k] for k in ('instrument_id','clock_id','query_at_us','purpose')]
    if kind=='reserve_dependency':return [value['reserve_key'][k] for k in ('instrument_id','record_type','record_id','revision')]
    if kind=='order':return [value['intent']['order_id']]
    return [value[{'live_lot':'lot_id','lot':'lot_id','slice':'slice_id','obligation':'obligation_id','decision':'decision_id'}[kind]]]


def business_id(config,inst,kind,t,slot,ordinal):
    prefix={'fill':'f:','posting':'p:','decision':'d:','order':'o:'}[kind]
    return prefix+digest(['qf009.id-v3',config['ledger_id'],config['trajectory_id'],config['scenario_id'],inst,kind,t,slot,ordinal])


def genesis_head(request,state):
    c=request['config'];cutoff=dict(at_us=c['initial_at_us'],slot=0);v=state.view(cutoff)
    return dict(ledger_id=c['ledger_id'],committed_seq=0,cutoff=cutoff,audit_prefix=digest(['qf009.genesis-v3',{k:v for k,v in request.items() if k not in ('store_root','source_roots','request_id')}]),economic_state_sha256=v['economic_state_sha256'],status='ACTIVE')


def create(request):
    selected=getattr(_JOURNAL_CREATION,'profile',None)
    if selected is not None:
        need('journal_storage' not in request['config'],'UNSUPPORTED_VERSION')
        request=dict(request,config=dict(request['config'],journal_storage=deepcopy(selected)))
    shape(request,'namespace schema_version profile request_id config raw_catalogue fact_store source_roots store_root');strict_json(request)
    need(request['namespace']==NS,'UNSUPPORTED_NAMESPACE');need(request['schema_version']==VERSION and request['profile']==PROFILE,'UNSUPPORTED_VERSION')
    config=_prepare_config(request['config']);ident(request['request_id']);root=Path(request['store_root'])
    need(not root.exists() and not root.is_symlink(),'STORE_INTEGRITY_FAILURE')
    for parent in root.parents:need(not parent.is_symlink(),'SCHEMA_VIOLATION')
    root.mkdir(parents=False);_fsync_directory(root.parent)
    budget=ResourceBudget(root,config['limits']['max_store_bytes']);budget.parent=_GLOBAL_BUDGET if _GLOBAL_BUDGET and root.is_relative_to(_GLOBAL_BUDGET.root) else None;_BUDGETS[str(root.resolve())]=budget
    _atomic(root/'GENESIS',request)
    _atomic(root/'CONTROL',dict(control_seq=0,control_sha256=digest(['qf009.control-v3',config['ledger_id'],PROFILE,'genesis'])))
    # Initial source validation and context admission share the same implementation
    # as cold open. No financial genesis is acknowledged before they succeed.
    placeholder=dict(ledger_id=config['ledger_id'],committed_seq=0,cutoff=dict(at_us=config['initial_at_us'],slot=0),audit_prefix='0'*64,economic_state_sha256='0'*64,status='ACTIVE')
    _atomic(root/'HEAD',placeholder)
    with Ledger(root) as ledger:
        ledger.head=genesis_head(request,ledger.state);_atomic(root/'HEAD',ledger.head);ledger.index.db.commit();return deepcopy(ledger.head)


def restore(request):
    shape(request,'checkpoint expected_committed_head store_root');cp=request['checkpoint']
    need(cp.get('namespace')=='qf009.streaming-checkpoint' and cp.get('schema_version')==VERSION and cp.get('profile')==PROFILE,'UNSUPPORTED_VERSION')
    need(digest({k:v for k,v in cp.items() if k!='checkpoint_sha256'})==cp['checkpoint_sha256'],'CHECKPOINT_MISMATCH')
    with Ledger(request['store_root'],request['expected_committed_head'],_recovery=True) as ledger:
        need(cp['committed_seq']<=ledger.head['committed_seq'],'CHECKPOINT_MISMATCH')
        for key,value in [('config_sha256',digest(ledger.request['config'])),('raw_catalogue_sha256',digest(ledger.request['raw_catalogue'])),('fact_store_sha256',ledger.request['fact_store']['sha256']),('adapters_sha256',digest(ledger.config['adapters'])),('schedule_sha256',digest(ledger.config['schedule']))]:need(cp[key]==value,'CHECKPOINT_MISMATCH')
        for ref in cp['files']:
            shape(ref,'component relative_path format_version bytes rows sha256');need(ref['format_version']==3,'UNSUPPORTED_VERSION')
            p=_safe_path(ledger.root,ref['relative_path']);need(p.is_file(),'STORE_INTEGRITY_FAILURE')
            need(p.stat().st_size==ref['bytes'] and _file_sha(p)==ref['sha256'],'STORE_INTEGRITY_FAILURE')
        ledger._rebuild_index();seq=cp['committed_seq']
        if seq:
            payload=ledger._payload(seq);manifest=load_json(_safe_path(ledger.root,f'manifest-{seq:08}.json').read_bytes())
            need(digest(manifest)==cp['audit_prefix'] and manifest['after']['economic_state_sha256']==cp['economic_state_sha256'],'STORE_INTEGRITY_FAILURE')
            st=State(ledger.index,ledger.config,payload['roots'])
        else:st=State(ledger.index,ledger.config,ledger._genesis_roots)
        cutoff=cp['cutoff'];at=cutoff['at_us']
        need(cp['context_receipt']==st.meta('context_receipt'),'CHECKPOINT_MISMATCH')
        expected_facts=ledger._fact_cursors(at if seq else at-1);expected_adapters=[dict(adapter_id=a['adapter_id'],last_invocation=st.meta('adapter_cursor:'+a['adapter_id'])) for a in ledger.config['adapters']]
        expected_queries=ledger._query_cursors(st,at)
        need(cp['fact_cursors']==expected_facts and cp['adapter_cursors']==expected_adapters and cp['query_cursors']==expected_queries,'CHECKPOINT_MISMATCH')
        need(cp['calendar_cursor']==sum(st.meta('calendar:'+i,0) for i in ledger.config['instruments']) and cp['registry_next_seq']==st.meta('registry_next',1),'CHECKPOINT_MISMATCH')
        need(cp['next_tick_index']==(bisect.bisect_right(ledger.config['_plan_index'].times,at) if seq else 0),'CHECKPOINT_MISMATCH')
        need(cp['registry_prefix_sha256']==st.root('registry') and cp['journal_prefix_sha256']==cp['audit_prefix'],'CHECKPOINT_MISMATCH')
        need(cp['control_seq']<=ledger.control['seq'],'CHECKPOINT_MISMATCH')
        control_hash=load_json(_safe_path(ledger.root,f'control-{cp["control_seq"]:08}.json').read_bytes())['control_sha256'] if cp['control_seq'] else digest(['qf009.control-v3',ledger.config['ledger_id'],PROFILE,'genesis'])
        need(cp['control_sha256']==control_hash,'CHECKPOINT_MISMATCH')
        refs=ledger._export_segments(seq,True)
        # Current live state may be newer; source-independent context is fixed,
        # while snapshot cursors must be reconstructed at this checkpoint cutoff.
        cursor_rows=[dict(kind='fact',value=v) for v in expected_facts]+[dict(kind='adapter',value=v) for v in expected_adapters]+[dict(kind='query',value=v) for v in expected_queries]
        cursor_bytes=b''.join(canonical_bytes(v)+b'\n' for v in cursor_rows)
        refs.append(dict(component='cursors',relative_path=f'exports/cursors-{seq:08}.jsonl',format_version=3,bytes=len(cursor_bytes),rows=len(cursor_rows),sha256=hashlib.sha256(cursor_bytes).hexdigest()))
        for n in range(1,cp['control_seq']+1):
            path=_safe_path(ledger.root,f'control-{n:08}.json');raw=path.read_bytes();refs.append(dict(component='control',relative_path=path.name,format_version=3,bytes=len(raw),rows=1,sha256=hashlib.sha256(raw).hexdigest()))
        need(refs==cp['files'],'STORE_INTEGRITY_FAILURE')
        for ref in cp['files']:
            path=_safe_path(ledger.root,ref['relative_path']);need(path.is_file(),'STORE_INTEGRITY_FAILURE')
            h=hashlib.sha256();size=count=0
            with path.open('rb') as source:
                for raw in source:
                    obj=load_json(raw);need(raw==canonical_bytes(obj)+b'\n','STORE_INTEGRITY_FAILURE');h.update(raw);size+=len(raw);count+=1
            need(h.hexdigest()==ref['sha256'] and size==ref['bytes'] and count==ref['rows'],'STORE_INTEGRITY_FAILURE')
        shape(cp['resource_spent'],'active_wall_us total_written_bytes attempts_started')
        for value in cp['resource_spent'].values():integer(value)
        need(cp['resource_spent']['attempts_started']==ledger.spent['attempts_started'] and cp['resource_spent']['active_wall_us']<=ledger.spent['active_wall_us'] and cp['resource_spent']['total_written_bytes']<=max(ledger.budget.grant,ledger.spent['total_written_bytes']),'CHECKPOINT_MISMATCH')
        ledger.spent['active_wall_us']=max(ledger.spent['active_wall_us'],cp['resource_spent']['active_wall_us']);ledger.spent['total_written_bytes']=max(ledger.spent['total_written_bytes'],cp['resource_spent']['total_written_bytes'])
        ledger._save_spent();return ledger.current_head()


def normalize_mark_selection(dto,schema_id,required_roles,raw_refs=None):
    """Lossless QR009 consumer DTO -> closed schema3 fifteen-Cell Fact.

    The caller must already possess external qualification. This mapper never
    selects a point, fills a missing price or proves archive completeness.
    """
    shape(dto,'instrument_id query_us mark_clock_id roles status source_us source_available_us source_semantic_key mark_price selected_at_us consumer_available_us unknown_reason')
    strict_json(dto);symbol=dto['instrument_id'];inst={'BTC_USDT':INSTRUMENTS[0],'ETH_USDT':INSTRUMENTS[1]}.get(symbol,symbol);need(inst in INSTRUMENTS,'OUT_OF_SCOPE_INSTRUMENT')
    q=integer(dto['query_us']);need(dto['selected_at_us']==dto['consumer_available_us']==q,'INPUT_BINDING_MISMATCH')
    ident(dto['mark_clock_id']);roles=dto['roles'];need(type(roles) is list and len(roles)==len(set(roles)) and set(roles)==set(required_roles)<=set(PURPOSES),'INPUT_BINDING_MISMATCH')
    def known(typ,value):return dict(tag='known',type=typ,value=value)
    cells={'query_at_us':known('T',q),'clock_id':known('ID',dto['mark_clock_id']),'status':known('ID',dto['status'])}
    if dto['status']=='SUPPORTED':
        source=integer(dto['source_us']);available=integer(dto['source_available_us']);need(source<=available<=q,'FUTURE_DEPENDENCY')
        need(dto['source_semantic_key']==[symbol,'archive-mark',source] or dto['source_semantic_key']==[inst,'archive-mark',source],'INPUT_BINDING_MISMATCH')
        need(dto['unknown_reason'] is None and number(dto['mark_price'],0)>0,'INPUT_BINDING_MISMATCH')
        for name,typ,value in [('source_at_us','T',source),('source_available_at_us','T',available),('source_fact_key','ID',f'mk:{inst}:{source}'),('selected_price','D+',fmt(number(dto['mark_price']))),('unknown_reason','ID','NOT_APPLICABLE')]:cells[name]=known(typ,value)
    else:
        need(dto['status']=='UNKNOWN' and dto['unknown_reason'] in QUERY_REASONS,'INPUT_BINDING_MISMATCH')
        need(all(dto[n] is None for n in ('source_us','source_available_us','source_semantic_key','mark_price')),'INPUT_BINDING_MISMATCH')
        for name,typ,reason in [('source_at_us','T','UNKNOWN_SOURCE_TIME'),('source_available_at_us','T','UNKNOWN_SOURCE_TIME'),('source_fact_key','ID','UNKNOWN_MAPPING'),('selected_price','D+','UNKNOWN_MARK')]:cells[name]=dict(tag='unknown',type=typ,reason=reason)
        cells['unknown_reason']=known('ID',dto['unknown_reason'])
    cells.update({'role_'+p:known('bool',p in roles) for p in PURPOSES})
    return dict(fact_key='mq:'+digest(['qf009.query-fact-v1',inst,dto['mark_clock_id'],q]),instrument_id=inst,schema_id=schema_id,economic_at_us=q,scenario_available_at_us=q,
                observed_first_available_at_us=None,cells=[dict(name=k,cell=v) for k,v in sorted(cells.items())],raw_refs=deepcopy(raw_refs or []),null_reasons={'observed_first_available_at_us':'HISTORICAL_FIRST_AVAILABILITY_UNKNOWN'})


def normalize_execution_open(fact,schema_id):
    shape(fact,'fact_key instrument_id schema_id economic_at_us scenario_available_at_us observed_first_available_at_us cells raw_refs null_reasons')
    need(fact['schema_id']=='qr009.exec-open-fact-v1' and len(fact['cells'])==1 and fact['cells'][0]['name']=='open_price','INPUT_BINDING_MISMATCH')
    need(fact['economic_at_us']==fact['scenario_available_at_us'],'INPUT_BINDING_MISMATCH');q=integer(fact['economic_at_us'])
    price=fact['cells'][0]['cell'];shape(price,'tag type value');need(price['tag']=='known' and price['type']=='D+' and number(price['value'],0)>0,'INPUT_BINDING_MISMATCH')
    result=deepcopy(fact);result['schema_id']=schema_id;result['instrument_id']={'BTC_USDT':INSTRUMENTS[0],'ETH_USDT':INSTRUMENTS[1]}.get(fact['instrument_id'],fact['instrument_id']);need(result['instrument_id'] in INSTRUMENTS,'OUT_OF_SCOPE_INSTRUMENT')
    result['cells']=[dict(name='open_us',cell=dict(tag='known',type='T',value=q)),dict(name='open_price',cell=dict(price,value=fmt(number(price['value']))))];return result
