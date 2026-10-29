"""Durable IO accounting without artificial execution/storage quotas."""
import math
import os
from pathlib import Path


def install(data, old_roots):
    from research.qd009 import streaming_ledger as sl
    data=Path(data).resolve()
    roots=sorted({str(Path(p)) for p in old_roots}|{str(data)},key=len,reverse=True)

    def translate(name):
        path=Path(name)
        sl.need(path.is_absolute() and '..' not in path.parts,'STORE_INTEGRITY_FAILURE')
        for old in roots:
            if path.is_relative_to(old):return str(data/path.relative_to(old))
        raise sl.LedgerError('UNDECLARED_RESOURCE_PATH')

    class Accounting(sl.ResourceBudget):
        def __init__(self,root,book=None):
            self.root=Path(root).resolve();self.book=Path(book or self.root/'RESOURCE_LOG')
            self.limit=None;self.reserve=0;self.parent=None;self.last_error=None;self.emergency=False
            self.sizes={};self.total=self.written=self.grant=0;self.previous='0'*64;self.file=None
            with self.book.open('rb') as source:
                for raw in source:
                    row=sl.load_json(raw);h=row.pop('hash')
                    sl.need(row['previous']==self.previous and sl.digest(row)==h,'STORE_INTEGRITY_FAILURE')
                    self.previous=h;self.grant=max(self.grant,row.get('write_upper',0))
                    if row['kind']=='size':self.sizes[translate(row['path'])]=row['size']
                    elif row['kind']=='write_grant':self.grant=row['value']
            self.written=self.grant;self.book_bytes=self.book.stat().st_size
            for p in self.root.rglob('*'):
                sl.need(not p.is_symlink(),'STORE_INTEGRITY_FAILURE')
                if p.is_file() and p!=self.book:self.sizes[str(p)]=max(self.sizes.get(str(p),0),p.stat().st_size)
            self.total=sum(self.sizes.values())

        def path(self,value):
            # Roots and archive-relative paths were checked before activation.
            # Absolute lexical normalization avoids filesystem walks per xWrite.
            return os.path.abspath(os.fspath(value)) if value is not None else str(self.root/'anonymous-sqlite-temp')

        def _append(self,kind,**values):
            self.grant=max(self.grant,math.ceil((self.written+4096)/1048576)*1048576)
            row=dict(kind=kind,previous=self.previous,write_upper=self.grant,**values)
            h=sl.digest(row);raw=sl.canonical_bytes(dict(row,hash=h))+b'\n'
            if self.parent:self.parent.issue(self.book,self.book_bytes+len(raw),len(raw))
            if self.file is None:self.file=self.book.open('ab',buffering=0)
            if self.file.write(raw)!=len(raw):raise OSError('Short resource-accounting write')
            os.fsync(self.file.fileno())
            self.book_bytes+=len(raw);self.written+=len(raw);self.previous=h

        def issue(self,path,end,amount=0):
            path=self.path(path);old=self.sizes.get(path,0);end=max(end,old)
            rounded=((end+65535)//65536)*65536 if path.endswith(('.sqlite3','-journal','-wal','-shm')) else end
            if self.parent:self.parent.issue(path,end,amount)
            if rounded>old:
                self._append('size',path=path,size=rounded);self.sizes[path]=rounded;self.total+=rounded-old
            if self.written+amount>self.grant:
                grant=max(self.grant+1048576,self.written+amount+4096)
                self._append('write_grant',value=grant);self.grant=grant
            self.written+=amount

        def release(self,path):
            path=self.path(path);old=self.sizes.get(path,0)
            if old:self._append('size',path=path,size=0);self.sizes[path]=0;self.total-=old
            if self.parent:self.parent.release(path)

        def rename(self,source,dest):
            source,dest=self.path(source),self.path(dest);size=self.sizes.get(source,0)
            self.release(dest);self._append('size',path=dest,size=size)
            self.sizes[dest]=size;self.total+=size;self.release(source)

        def close(self):
            if self.file is not None:self.file.close();self.file=None

    global_budget=Accounting(data,data/'aggregate-resource.jsonl')
    child=Accounting(data/'full-p0-actual-1/P0-ALLOW_ALL/store');child.parent=global_budget
    sl._GLOBAL_BUDGET=global_budget;sl._BUDGETS[str(child.root)]=child
    return global_budget,child
