"""Ball-arithmetic W1 target, directional derivatives, and log-concave tails.

All supplied floats are exact binary inputs. The finite integration algorithm
and positive-normalizer/ratio analysis remain separate from this component.
"""
import math
from collections import Counter
from flint import arb
from verified_cubature import integer_power as power


def sigmoid(x):
    # Monotonic endpoint evaluation avoids division by a wide exp ball whose
    # rounded radius may extend below zero. No domain clipping is used.
    lo=1/(1+(-x.lower()).exp());hi=1/(1+(-x.upper()).exp())
    return lo.union(hi)


def logistic_derivatives(x,slope):
    p=sigmoid(x);v=p*(1-p)
    return [p,slope*v,power(slope,2)*v*(1-2*p),
            power(slope,3)*v*(1-6*p+6*p*p),
            power(slope,4)*v*(1-14*p+36*p*p-24*p*p*p)]


class WellsBallTarget:
    def __init__(self,dist,switched,center,factor):
        if len(dist)!=len(switched) or not len(dist):raise ValueError('Data length differs')
        if any(y not in (0,1) for y in switched):raise ValueError('Binary outcomes required')
        # Match exactly the original binary64 distance/100 operation.
        groups=Counter((float(d)/100.,int(y)) for d,y in zip(dist,switched))
        if any(not math.isfinite(x) or x<0 or y not in (0,1) for x,y in groups):raise ValueError('Invalid observations')
        self.groups=[(arb(x),y,n) for (x,y),n in sorted(groups.items())]
        self.center=list(map(arb,center));self.factor=[list(map(arb,row)) for row in factor]
        if len(self.center)!=2 or len(self.factor)!=2 or any(len(x)!=2 for x in self.factor):raise ValueError('Two-dimensional geometry required')
        a=self.factor;self.jac=abs(a[0][0]*a[1][1]-a[0][1]*a[1][0])
        if not self.jac>0:raise ValueError('Nonsingular exact binary transform required')
        self.base=self.log_gradient(*self.center)[0]
        self.calls=dict(value=0,derivative=0,log_gradient=0)
        self._cached_box=None

    def coordinates(self,x,y):
        a=self.factor;c=self.center
        return c[0]+a[0][0]*x+a[0][1]*y,c[1]+a[1][0]*x+a[1][1]*y

    def log_gradient(self,alpha,beta):
        total=arb(0);g=[arb(0),arb(0)]
        for distance,label,n in self.groups:
            eta=alpha+distance*beta;signed=eta if label else -eta
            total-=n*(1+(-signed).exp()).log()
            residual=n*(label-sigmoid(eta));g[0]+=residual;g[1]+=distance*residual
        if hasattr(self,'calls'):self.calls['log_gradient']+=1
        return total,g

    def value(self,x,y):
        alpha,beta=self.coordinates(x,y);lp,_=self.log_gradient(alpha,beta)
        density=(lp-self.base).exp()*self.jac
        self.calls['value']+=1
        return [density,alpha*density,beta*density,alpha*alpha*density,beta*beta*density,
                sigmoid(alpha)*density,sigmoid(alpha+beta)*density]

    def fourth(self,x,y,axis):
        key=(x.repr(),y.repr())
        if self._cached_box is None or self._cached_box[0]!=key:
            alpha,beta=self.coordinates(x,y)
            # Concavity supplies an upper density bound without inflating each
            # observation's log likelihood independently over a large box.
            am,bm=self.coordinates(x.mid(),y.mid());lp,g=self.log_gradient(am,bm)
            gz=[sum((self.factor[j][k]*g[j] for j in range(2)),arb(0)) for k in range(2)]
            upper=(lp-self.base+gz[0].abs_upper()*x.rad()+gz[1].abs_upper()*y.rad()).exp()*self.jac
            f=arb(0).union(upper.upper())
            derivatives=[[arb(0) for _ in range(4)] for _ in range(2)]
            for distance,label,n in self.groups:
                p=sigmoid(alpha+distance*beta);v=p*(1-p)
                for k in range(2):
                    slope=self.factor[0][k]+distance*self.factor[1][k];r=derivatives[k]
                    r[0]+=n*(label-p)*slope
                    r[1]-=n*v*power(slope,2)
                    r[2]-=n*v*(1-2*p)*power(slope,3)
                    r[3]-=n*v*(1-6*p+6*p*p)*power(slope,4)
            result=[]
            for k,(l1,l2,l3,l4) in enumerate(derivatives):
                fd=[f,f*l1,f*(l1*l1+l2),f*(power(l1,3)+3*l1*l2+l3),
                    f*(power(l1,4)+6*l1*l1*l2+3*l2*l2+4*l1*l3+l4)]
                aa,bb=self.factor[0][k],self.factor[1][k]
                multipliers=[[arb(1),arb(0),arb(0),arb(0),arb(0)],
                    [alpha,aa,arb(0),arb(0),arb(0)],[beta,bb,arb(0),arb(0),arb(0)],
                    [alpha*alpha,2*alpha*aa,2*aa*aa,arb(0),arb(0)],
                    [beta*beta,2*beta*bb,2*bb*bb,arb(0),arb(0)],
                    logistic_derivatives(alpha,aa),logistic_derivatives(alpha+beta,aa+bb)]
                result.append([sum((math.comb(4,j)*fd[4-j]*h[j] for j in range(5)),arb(0)) for h in multipliers])
            self._cached_box=(key,result)
        self.calls['derivative']+=1
        return self._cached_box[1][axis]

    def tail(self,radius=12,sectors=256):
        """Scaled original-coordinate tail bounds outside a whitened disk.

        A global supporting plane is integrated over each angular sector.
        Negative radial slope and bounded tangential slope give kappa>0.
        The disk complement contains the omitted square complement.
        """
        if radius<=0 or sectors<4:raise ValueError('Positive radius and >=4 sectors required')
        R=arb(radius);width=2*arb.pi()/sectors;half=width/2
        norms=[(row[0]*row[0]+row[1]*row[1]).sqrt() for row in self.factor]
        bounds=[arb(0) for _ in range(5)];minimum=None
        for k in range(sectors):
            angle=(arb(k)+arb(1)/2)*width;u=[angle.cos(),angle.sin()];v=[-u[1],u[0]]
            alpha,beta=self.coordinates(R*u[0],R*u[1]);lp,g=self.log_gradient(alpha,beta)
            gz=[sum((self.factor[j][i]*g[j] for j in range(2)),arb(0)) for i in range(2)]
            radial=sum((gz[i]*u[i] for i in range(2)),arb(0));tangent=sum((gz[i]*v[i] for i in range(2)),arb(0))
            if not radial<0:raise ValueError('Cannot certify outward negative radial slope')
            kappa=-(radial*half.cos()+tangent.abs_upper()*half.sin())
            if not kappa>0:raise ValueError('Cannot certify integrable sector')
            lower=kappa.lower();minimum=lower if minimum is None or lower<minimum else minimum
            constant=lp-self.base-R*radial
            weight=width*(constant-kappa*R).exp()*self.jac
            i1=R/kappa+1/(kappa*kappa)
            i2=R*R/kappa+2*R/(kappa*kappa)+2/power(kappa,3)
            i3=power(R,3)/kappa+3*R*R/(kappa*kappa)+6*R/power(kappa,3)+6/power(kappa,4)
            bounds[0]+=weight*i1
            for j in range(2):
                a=self.center[j].abs_upper();b=norms[j]
                bounds[1+j]+=weight*(a*i1+b*i2)
                bounds[3+j]+=weight*(a*a*i1+2*a*b*i2+b*b*i3)
        return dict(bounds=[b.upper() for b in bounds],minimum_decay=minimum,
                    scope='mass, absolute alpha, absolute beta, alpha squared, beta squared outside square; includes fixed-transform Jacobian')
