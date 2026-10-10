"""Resumable two-dimensional bounded quadrature with charged work reservations.

SQLite stores only numeric JSON, never pickle. Restoring an Arb radius can
round it outward; that widens a bound but cannot narrow it. Completed outputs
are read without restoring/re-evaluating the numerical state.
"""
from dataclasses import asdict
import heapq
import json
from pathlib import Path
import sqlite3
from flint import arb
from verified_cubature import Cell,rectangle_rule


def pack(x):
    m,e=x.mid().man_exp();r,s=x.rad().man_exp()
    return [[str(m),int(e)],[str(r),int(s)]]


def unpack(x):
    if not isinstance(x,list) or len(x)!=2:raise ValueError('Invalid ball encoding')
    return arb((int(x[0][0]),int(x[0][1])),(int(x[1][0]),int(x[1][1])))


def encode_cell(cell):
    return dict(box=[pack(arb(x)) for x in cell.box],value=[pack(x) for x in cell.value],
                remainder=[pack(x) for x in cell.remainder],evaluations=cell.evaluations)


def decode_cell(d):return Cell(tuple(unpack(x) for x in d['box']),[unpack(x) for x in d['value']],
    [unpack(x) for x in d['remainder']],d['evaluations'])


def encode_state(state):
    return {**state,'quadrature':[[pack(x) for x in row] for row in state['quadrature']],
                    'error':[[pack(x) for x in row] for row in state['error']]}


def decode_state(state):
    return {**state,'quadrature':[[unpack(x) for x in row] for row in state['quadrature']],
                    'error':[[unpack(x) for x in row] for row in state['error']]}


class Engine:
    def __init__(self,path,identity,value,fourth,boxes,priorities,*,method,maximum_cells,
                 maximum_charged_evaluations,charge_per_cell=None):
        self.path=Path(path);self.value=value;self.fourth=fourth;self.method=method
        self.maximum_cells=maximum_cells;self.maximum_work=maximum_charged_evaluations
        self.charge=charge_per_cell or (6 if method=='gauss2' else 11)
        self.priorities=[[arb(x) for x in row] for row in priorities]
        if any(not x>0 for row in self.priorities for x in row):raise ValueError('Positive priorities required')
        self.db=sqlite3.connect(path);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS cells (id INTEGER PRIMARY KEY,region INTEGER NOT NULL,value TEXT NOT NULL)')
        bound=dict(identity=identity,method=method,maximum_cells=maximum_cells,maximum_charged_evaluations=maximum_charged_evaluations,charge_per_cell=self.charge,
                   boxes=[[pack(arb(x)) for x in b] for b in boxes],priorities=priorities)
        previous=self.get('binding')
        if previous is None:
            if self.get('state') is not None:raise ValueError('Unbound numerical state')
            self.set('binding',bound);self.set('charged',0);self.db.commit()
        elif previous!=bound:raise ValueError('Checkpoint identity/settings differ')
        self.cells={};self.heap=[]
        state=self.get('state')
        if state is None:
            self.reserve(len(boxes)*self.charge)
            cells=[rectangle_rule(value,fourth,b,method) for b in boxes]
            self.state=dict(quadrature=[list(c.value) for c in cells],error=[list(c.remainder) for c in cells],
                completed_external_callbacks=sum(c.evaluations for c in cells),next_id=len(cells),splits=0)
            for i,c in enumerate(cells):self.add(i,i,c);self.persist_cell(i,i,c)
            self.persist_state();self.db.commit()
        else:
            self.state=decode_state(state)
            for index,region,payload in self.db.execute('SELECT id,region,value FROM cells ORDER BY id'):
                self.add(index,region,decode_cell(json.loads(payload)))
            if not self.cells:raise ValueError('Empty saved integration partition')

    def get(self,key):
        row=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        return None if row is None else json.loads(row[0])

    def set(self,key,value):self.db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',(key,json.dumps(value,separators=(',',':'),allow_nan=False)))

    def reserve(self,amount):
        charged=self.get('charged')
        if charged+amount>self.maximum_work:raise RuntimeError('Work reservation exceeds frozen budget')
        self.set('charged',charged+amount);self.db.commit()

    def add(self,index,region,cell):
        self.cells[index]=(region,cell)
        priority=max(float(e/t) for e,t in zip(cell.remainder,self.priorities[region]))
        heapq.heappush(self.heap,(-priority,index))

    def persist_cell(self,index,region,cell):self.db.execute('INSERT OR REPLACE INTO cells VALUES (?,?,?)',(index,region,json.dumps(encode_cell(cell),separators=(',',':'))))

    def persist_state(self):self.set('state',encode_state(self.state))

    def enclosures(self):
        return [[q+arb(0,e.upper()) for q,e in zip(qs,es)] for qs,es in zip(self.state['quadrature'],self.state['error'])]

    def advance(self,steps=128,stop=None):
        possible=min(steps,self.maximum_cells-len(self.cells),(self.maximum_work-self.get('charged'))//(2*self.charge))
        if possible<=0:return 'work_limit'
        # Charge the entire block before evaluating. An interrupted block stays
        # charged, so recovery cannot silently obtain additional evaluations.
        self.reserve(possible*2*self.charge)
        changed={};deleted=[];status='continue'
        for _ in range(possible):
            if stop is not None and stop(self.enclosures()):status='tolerance_met';break
            _,key=heapq.heappop(self.heap);region,old=self.cells[key];a,b,c,d=old.box
            if b-a>=d-c:
                middle=(a+b)/2
                boxes=[(a,middle,c,d),(middle,b,c,d)]
                resolved=middle>a and middle<b
            else:
                middle=(c+d)/2;boxes=[(a,b,c,middle),(a,b,middle,d)]
                resolved=middle>c and middle<d
            if not resolved:
                heapq.heappush(self.heap,(0.,key));status='coordinate_resolution';break
            children=[rectangle_rule(self.value,self.fourth,box,self.method) for box in boxes]
            del self.cells[key];deleted.append(key);changed.pop(key,None)
            self.state['completed_external_callbacks']+=sum(x.evaluations for x in children)
            self.state['splits']+=1
            self.state['quadrature'][region]=[q-old.value[i]+sum((x.value[i] for x in children),arb(0)) for i,q in enumerate(self.state['quadrature'][region])]
            self.state['error'][region]=[e-old.remainder[i]+sum((x.remainder[i] for x in children),arb(0)) for i,e in enumerate(self.state['error'][region])]
            for child in children:
                index=self.state['next_id'];self.state['next_id']+=1
                self.add(index,region,child);changed[index]=(region,child)
        # No transaction containing cells is open while scientific evaluations
        # run. Persist all changed cells and aggregates as one atomic checkpoint.
        with self.db:
            self.db.executemany('DELETE FROM cells WHERE id=?',[(i,) for i in deleted])
            for index,(region,cell) in changed.items():self.persist_cell(index,region,cell)
            self.persist_state()
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        return status

    def counters(self):return dict(active_cells=len(self.cells),charged_evaluations_upper_bound=self.get('charged'),
        completed_external_callbacks=self.state['completed_external_callbacks'],committed_splits=self.state['splits'])

    def close(self):
        self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');self.db.close()
