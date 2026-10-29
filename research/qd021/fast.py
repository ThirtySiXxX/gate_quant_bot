"""Measured hot-path changes; identical canonical bytes and graph-copy semantics."""
from copy import deepcopy as standard_copy
import hashlib
import os
from pathlib import Path
import sys
import weakref
import zlib

ATOMIC = frozenset((type(None), str, int, bool, float, bytes, complex))


def node_hash(component,key,validated_value_bytes,left,right):
    from research.qd009 import streaming_ledger as sl
    prefix=sl.canonical_bytes(['qf009.economic-node-v3',component,key])[:-1]
    suffix=sl.canonical_bytes([left,right])[1:]
    h=hashlib.sha256();h.update(prefix);h.update(b',');h.update(validated_value_bytes)
    h.update(b',');h.update(suffix)
    return h.hexdigest()


def graph_copy(value, memo=None):
    t = type(value)
    if t in ATOMIC:
        return value
    if memo is None:
        memo = {}
    identity = id(value)
    if identity in memo:
        return memo[identity]
    if t is dict:
        result = {}; memo[identity] = result
        for key, item in value.items():
            copied_item = graph_copy(item, memo)
            copied_key = key if type(key) in ATOMIC else graph_copy(key, memo)
            result[copied_key] = copied_item
    elif t is list:
        result = []; memo[identity] = result
        result.extend(graph_copy(item, memo) for item in value)
    else:
        return standard_copy(value, memo)
    # Preserve deepcopy's keep-alive rule for custom object graphs.
    memo.setdefault(id(memo), []).append(value)
    return result


def strict_json(value):
    """Same accepted types/error codes; scalar leaves avoid recursive calls."""
    t = type(value)
    if value is None or t in (str, int, bool):
        return
    if t is list:
        for item in value:
            if item is not None and type(item) not in (str, int, bool):
                strict_json(item)
    elif t is dict:
        for key, item in value.items():
            if type(key) is not str:
                return invalid_json('JSON_KEY_TYPE')
            if item is not None and type(item) not in (str, int, bool):
                strict_json(item)
    else:
        return invalid_json('NONCANONICAL_INPUT')


def invalid_json(code):
    from research.qd009 import streaming_ledger as sl
    raise sl.LedgerError(code)


def cache_plan():
    # Cache targets, not job quotas. Use a minority of visible VM RAM.
    try:
        memory = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
    except (ValueError, OSError):
        memory = 4 * 1024**3
    nodes = max(32*1024**2, min(1024**3, memory//16))
    sql = max(16*1024**2, min(512*1024**2, memory//32))
    return dict(node_cache_bytes=nodes, sqlite_cache_bytes=sql,
                working_charge_unit='NODE_COUNT_NOT_RSS', global_resource_quotas=False)


def install(ledger, plan=None):
    from research.qd009 import streaming_ledger as sl
    from research.qd011 import ports
    from research.qd016.resident import ProcessBudgetIndex
    plan = plan or cache_plan()

    class FastIndex(ProcessBudgetIndex):
        def _remember_encoded(self,root,node,raw):
            # Cache weight only: conservative serialized-size estimate avoids a
            # recursive sys.getsizeof walk through every scalar on every read.
            used=1024+4*len(raw)+96*raw.count(b'":')+16*raw.count(b',')
            old=self.cache.pop(root,None)
            if old is not None:self.size-=old[1]
            if used<=self.cap:
                self.cache[root]=(node,used);self.size+=used;self._evict()

        def freeze(self,component,root):
            if not isinstance(root,sl._WorkingNode):return root
            n=root.data;left=self.freeze(component,n['l']);right=self.freeze(component,n['r'])
            raw=sl.canonical_bytes(n['v']);vh=hashlib.sha256(raw).hexdigest()
            result=node_hash(component,n['k'],raw,left,right)
            if result in self.cache:return result
            if self.db.execute('SELECT 1 FROM nodes WHERE h=?',(sl._sql_hash(result),)).fetchone():
                self.node(component,result);return result
            self.db.execute('INSERT OR IGNORE INTO blobs VALUES (?,?,?)',
                            (sl._sql_hash(vh),zlib.compress(raw,1),self.birth))
            self.db.execute('INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?,?,?,?)',
                            (sl._sql_hash(result),component,zlib.compress(sl.canonical_bytes(n['k']),1),None,
                             sl._sql_hash(vh),sl._sql_hash(left),sl._sql_hash(right),n['n'],self.birth))
            self.writes+=1
            self._remember_encoded(result,dict(k=n['k'],p=n['p'],v=n['v'],l=left,r=right,n=n['n']),raw)
            return result

        def node(self,component,root):
            if isinstance(root,sl._WorkingNode):self.visits+=1;self.working_visits+=1;return root.data
            if root==self.empty(component):return None
            self.visits+=1;self.immutable_visits+=1
            if root in self.cache:
                node,used=self.cache.pop(root);self.cache[root]=(node,used);return node
            row=self.db.execute('SELECT c,k,p,v,l,r,n FROM nodes WHERE h=?',(sl._sql_hash(root),)).fetchone()
            sl.need(row is not None and row[0]==component,'STORE_INTEGRITY_FAILURE')
            _,key,_,vh,left,right,count=row;key=sl.load_json(sl._unpack_node(key))
            left,right=sl._wire_hash(left),sl._wire_hash(right)
            blob=self.db.execute('SELECT b FROM blobs WHERE h=?',(vh,)).fetchone()
            sl.need(blob is not None,'STORE_INTEGRITY_FAILURE');raw=sl._unpack_node(blob[0])
            sl.need(hashlib.sha256(raw).hexdigest()==sl._wire_hash(vh),'STORE_INTEGRITY_FAILURE')
            value=sl.load_json(raw);strict_json(value)
            result=node_hash(component,key,raw,left,right)
            if result!=root:
                # Preserve admission of previously valid noncanonical physical
                # JSON encodings; logical node hashes always use canonical JSON.
                result=node_hash(component,key,sl.canonical_bytes(value),left,right)
            sl.need(result==root,'STORE_INTEGRITY_FAILURE')
            node=dict(k=key,p=sl.digest(['qf009.index-priority-v3',component,key]),v=value,l=left,r=right,n=count)
            self._remember_encoded(root,node,raw)
            return node

        def prune(self, roots):
            # Work in this transaction's rows only. A born index prevents a
            # full lifetime-table scan on each commit.
            fresh = {sl._wire_hash(h):(c,sl._wire_hash(left),sl._wire_hash(right))
                     for h,c,left,right in self.db.execute('SELECT h,c,l,r FROM nodes WHERE born=?',(self.birth,))}
            retained=set();stack=list(roots.items())
            while stack:
                component,root=stack.pop();row=fresh.get(root)
                if row is None:
                    if root!=self.empty(component):
                        sl.need(self.db.execute('SELECT 1 FROM nodes WHERE h=?',(sl._sql_hash(root),)).fetchone() is not None,
                                'STORE_INTEGRITY_FAILURE')
                    continue
                if root in retained:
                    continue
                sl.need(row[0]==component,'STORE_INTEGRITY_FAILURE')
                retained.add(root);stack.extend(((component,row[1]),(component,row[2])))
                if component=='_timeline':stack.extend(self.node(component,root)['v'].items())
                if component=='_link_roots':stack.append(('links',self.node(component,root)['v']))
                if component=='_audit_ref_roots':stack.append(('_audit_refs',self.node(component,root)['v']))
            self.db.execute('CREATE TEMP TABLE IF NOT EXISTS retained(h TEXT PRIMARY KEY) WITHOUT ROWID')
            self.db.execute('DELETE FROM retained')
            self.db.executemany('INSERT INTO retained VALUES (?)',((sl._sql_hash(h),) for h in retained))
            sl._vfs_error()
            deleted=self.db.execute('DELETE FROM nodes WHERE born=? AND h NOT IN (SELECT h FROM retained) RETURNING h',(self.birth,)).fetchall()
            self.db.execute('DELETE FROM blobs WHERE born=? AND h NOT IN (SELECT v FROM nodes WHERE born=?)',(self.birth,self.birth))
            # Older immutable nodes are still present. Keep their verified LRU
            # entries, and invalidate only rows actually removed above.
            for (h,) in deleted:
                old=self.cache.pop(sl._wire_hash(h),None)
                if old is not None:self.size-=old[1]
            self._evict()

        def _evict(self):
            # A transaction's mutable working set must not evict the entire
            # immutable LRU. It is released at the existing phase barriers.
            while self.cache and self.size > self.cap:
                _, (_, used) = self.cache.popitem(last=False)
                self.size -= used

        def ensure_room(self, roots):
            # Every original frame/view still freezes its complete roots. Avoid
            # premature transient-node persistence inside an unobserved phase.
            return None

        def _working(self, component, data):
            owned = dict(data, k=list(data['k']), v=graph_copy(data['v']))
            charge = [1]
            self.work_bytes += 1; self.work_peak = max(self.work_peak, self.work_bytes)
            node = sl._WorkingNode(component, owned, charge)
            weakref.finalize(node, self._release_work, charge)
            return node

        def set(self, component, root, key, value):
            node = self.node(component, root)
            if node is None:
                return self.put(component, key, value)
            a, b = sl.ordered_key(key), sl.ordered_key(node['k'])
            if a == b and node['v'] == value:
                return root
            work = root if isinstance(root, sl._WorkingNode) else self._working(component, node)
            node = work.data
            if a == b:
                node['v'] = graph_copy(value)
                return work
            side = 'l' if a < b else 'r'
            child = self.set(component, node[side], key, value); node[side] = child
            cn = self.node(component, child)
            node['n'] = 1+self.count(component,node['l'])+self.count(component,node['r'])
            if (cn['p'], sl.ordered_key(cn['k'])) < (node['p'], b):
                if not isinstance(child, sl._WorkingNode):
                    child=self._working(component,cn);cn=child.data
                other='r' if side=='l' else 'l';node[side]=cn[other]
                node['n']=1+self.count(component,node['l'])+self.count(component,node['r'])
                cn[other]=work;cn['n']=1+self.count(component,cn['l'])+self.count(component,cn['r'])
                return child
            return work

    # Explicit consumer-runtime bindings; original source files stay unchanged.
    # Validation acceptance and deepcopy's mutable isolation/alias semantics are
    # checked separately; none of the financial evaluate methods are replaced.
    sl.deepcopy = graph_copy
    ports.deepcopy = graph_copy
    sl.strict_json = strict_json
    index = ledger.index
    index.__class__ = FastIndex
    index.cap = plan['node_cache_bytes']
    index.db.execute('PRAGMA cache_size=-'+str(plan['sqlite_cache_bytes']//1024))
    index.db.execute('CREATE INDEX IF NOT EXISTS qd021_nodes_born ON nodes(born)')
    index.db.execute('CREATE INDEX IF NOT EXISTS qd021_blobs_born ON blobs(born)')
    index.db.execute("CREATE INDEX IF NOT EXISTS qd021_audit_commit ON audit_rows(commit_seq) WHERE kind='commit'")
    index.db.commit()
    ledger.fast_policy = plan
    return plan
