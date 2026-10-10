"""Finite-rectangle tensor rules with explicit fourth-derivative remainders.

This certifies an interior integral only if the supplied interval derivative
bounds are valid on the entire rectangle. Tail, input and ratio certification
are separate obligations. No empirical difference of rules is an error bound.
"""
from dataclasses import dataclass
import heapq
import itertools
from flint import arb


def integer_power(x, n):
    """Interval-safe nonnegative integer power, including balls crossing zero."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Nonnegative integer exponent required")
    out=arb(1)
    for _ in range(n):
        out=out*x
    return out


@dataclass
class Cell:
    box: tuple
    value: list
    remainder: list
    evaluations: int

    def enclosures(self):
        return [q+arb(0,e.upper()) for q,e in zip(self.value,self.remainder)]


def rectangle_rule(value, fourth, box, method='gauss2'):
    """Tensor product bound Iy(Ex) + Qx(Ey); positive weights sum to width."""
    if method not in ('gauss2','simpson'):raise ValueError('Unsupported bounded rule')
    a,b,c,d=map(arb,box)
    if not b>a or not d>c:raise ValueError('Strictly positive rectangle widths required')
    hx,hy=b-a,d-c;mx,my=(a+b)/2,(c+d)/2
    if method=='gauss2':
        z=1/arb(3).sqrt();nodes=(-z,z);weights=(arb(1),arb(1));constant=4320
    else:
        nodes=(arb(-1),arb(0),arb(1));weights=(arb(1)/3,arb(4)/3,arb(1)/3);constant=2880
    result=None
    for nx,wx in zip(nodes,weights):
        for ny,wy in zip(nodes,weights):
            q=list(value(mx+hx*nx/2,my+hy*ny/2))
            if result is None:result=[arb(0) for _ in q]
            if len(q)!=len(result) or any(not item.is_finite() for item in q):raise ValueError('Nonfinite/inconsistent integrand')
            result=[old+item*wx*wy*hx*hy/4 for old,item in zip(result,q)]
    xx=a.union(b);yy=c.union(d)
    dx=list(fourth(xx,yy,0));dy=list(fourth(xx,yy,1))
    if len(dx)!=len(result) or len(dy)!=len(result):raise ValueError('Derivative vector dimension differs')
    if any(not z.is_finite() for z in dx+dy):raise ValueError('Nonfinite derivative bound')
    errors=[(hy*hx**5*x.abs_upper()+hx*hy**5*y.abs_upper())/constant for x,y in zip(dx,dy)]
    # Store point upper bounds: replacing a parent must remove its old error,
    # not keep the old radius twice through interval subtraction.
    return Cell(tuple(box),result,[e.upper() for e in errors],len(nodes)**2+2)


def integrate(value,fourth,box,tolerances,*,method='gauss2',max_cells=4096,max_evaluations=100000,checkpoint=None):
    tol=[arb(t) for t in tolerances]
    if not tol or any(not t>0 for t in tol):raise ValueError('Positive vector tolerances required')
    cost=6 if method=='gauss2' else 11
    if max_cells<1 or max_evaluations<cost:raise ValueError('Insufficient positive work budget')
    counter=itertools.count();first=rectangle_rule(value,fourth,box,method)
    if len(first.value)!=len(tol):raise ValueError('Tolerance dimension differs')
    def priority(cell):return max(float(e/t) for e,t in zip(cell.remainder,tol))
    cells={0:first};heap=[(-priority(first),0)];next(counter)
    quadrature=list(first.value);error=list(first.remainder);used=first.evaluations;history=[]
    while True:
        enclosed=[q+arb(0,e.upper()) for q,e in zip(quadrature,error)]
        met=all(z.rad()<=t for z,t in zip(enclosed,tol))
        state='interior_tolerance_met' if met else 'work_limit'
        if met or len(cells)>=max_cells or used+2*cost>max_evaluations:break
        _,key=heapq.heappop(heap);old=cells[key];a,b,c,d=old.box
        if b-a>=d-c:
            middle=(a+b)/2
            if middle in (a,b):state='coordinate_resolution';break
            boxes=[(a,middle,c,d),(middle,b,c,d)]
        else:
            middle=(c+d)/2
            if middle in (c,d):state='coordinate_resolution';break
            boxes=[(a,b,c,middle),(a,b,middle,d)]
        children=[rectangle_rule(value,fourth,z,method) for z in boxes]
        del cells[key]
        used+=sum(z.evaluations for z in children)
        quadrature=[q-old.value[i]+sum((z.value[i] for z in children),arb(0)) for i,q in enumerate(quadrature)]
        error=[e-old.remainder[i]+sum((z.remainder[i] for z in children),arb(0)) for i,e in enumerate(error)]
        for child in children:
            key=next(counter);cells[key]=child;heapq.heappush(heap,(-priority(child),key))
        if len(cells)&(len(cells)-1)==0:
            step=dict(cells=len(cells),evaluations=used,enclosures=[str(q+arb(0,e.upper())) for q,e in zip(quadrature,error)])
            history.append(step)
            if checkpoint:checkpoint(step)
    return dict(status=state,enclosures=enclosed,cells=len(cells),evaluations=used,history=history,
                method=method,scope='finite rectangle only; no tail or normalized-posterior certification')
