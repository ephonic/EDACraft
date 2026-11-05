"""DG avalanche generation uses the returned saturated carrier currents."""
import json
import os
import math
from decimal import Decimal, localcontext
import numpy as np
import pytest
from tcad.core import native_constants
from test_hfs_contact_policy import bar as classical_bar, contacts, VT, H
from test_ii_field_floor import thin_result


def bar(axis=0, primary=False, driving=0, policy=True, layout='ends', cutoff=0., floor=1e5, quantum=True, ii=True):
    sim = classical_bar(axis, primary, driving, ii, policy, layout)
    sim.set_quantum_enabled(quantum)
    sim.set_density_gradient_coefficients(1e-15, 7e-16)
    sim.set_hfs_low_field_cutoff(cutoff)
    sim.set_ii_field_floor(floor)
    return sim


def expected_flux(result, driving, policy, layout, cutoff):
    n, p = np.asarray(result['n']), np.asarray(result['p'])
    phi = np.asarray(result['phi'])
    qn, qp = np.asarray(result['Qn']), np.asarray(result['Qp'])
    flux = []
    for v, carrier, mu, vsat, beta, sign, boundary in [
        (phi+qn, n, .1, 5e4, 2., -1., contacts(layout)[0]),
        (phi-qp, p, .05, 4e4, 1., 1., contacts(layout)[1])]:
        delta = np.diff(v)/VT
        bp = np.where(abs(delta)<1e-10, 1-delta/2+delta*delta/12, delta/np.expm1(delta))
        bm = np.where(abs(delta)<1e-10, 1+delta/2+delta*delta/12, -delta/np.expm1(-delta))
        force = abs(np.diff(v+sign*VT*np.log(np.maximum(carrier, 1.)/1e19)))/H
        contact = np.array([i in boundary or i+1 in boundary for i in range(4)])
        force = np.where((driving == 1) | ((not policy) & contact), abs(np.diff(v))/H, force)
        force = np.where(force < cutoff, 0., force)
        mobility = mu/(1+(mu*force/vsat)**beta)**(1/beta)
        flux.append(mobility*VT/H*((carrier[1:]*bp-carrier[:-1]*bm) if sign < 0 else (carrier[:-1]*bp-carrier[1:]*bm)))
    q = float(native_constants()['elementary_charge_C'])
    return [q*f for f in flux]


def expected_generation(result, jn, jp, floor):
    field = abs(np.diff(result['phi']))/H
    q = float(native_constants()['elementary_charge_C'])
    alpha_n = np.where(field < floor, 0., 1e5*np.exp(-2e5/field))
    alpha_p = np.where(field < floor, 0., 2e5*np.exp(-3e5/field))
    edge = (alpha_n*abs(jn)+alpha_p*abs(jp))/q
    source = np.zeros(5); source[:-1] += .5*edge; source[1:] += .5*edge
    return source


class Interval:
    """Outward Decimal intervals for binary64 observations of native quad fields."""
    def __init__(self, lo, hi=None):
        self.lo = Decimal(lo); self.hi = Decimal(lo if hi is None else hi)

    @staticmethod
    def point(value):
        return Interval(Decimal.from_float(float(value)))

    @staticmethod
    def observation(value):
        v = float(value); d = Decimal.from_float
        return Interval(((d(math.nextafter(v, -math.inf))+d(v))/2).next_minus(),
                        ((d(v)+d(math.nextafter(v, math.inf)))/2).next_plus())

    def __add__(self, other):
        return Interval((self.lo+other.lo).next_minus(), (self.hi+other.hi).next_plus())

    def __neg__(self):
        return Interval(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -other

    def __mul__(self, other):
        values = [a*b for a in (self.lo,self.hi) for b in (other.lo,other.hi)]
        return Interval(min(values).next_minus(), max(values).next_plus())

    def __truediv__(self, other):
        assert not other.lo <= 0 <= other.hi
        values = [a/b for a in (self.lo,self.hi) for b in (other.lo,other.hi)]
        return Interval(min(values).next_minus(), max(values).next_plus())

    def absolute(self):
        return Interval(0 if self.lo<=0<=self.hi else min(abs(self.lo),abs(self.hi)), max(abs(self.lo),abs(self.hi)))

    def log(self):
        return Interval(self.lo.ln().next_minus(), self.hi.ln().next_plus())

    def sqrt(self):
        return Interval(self.lo.sqrt().next_minus(), self.hi.sqrt().next_plus())

    def bernoulli(self):
        # B is monotone decreasing. Evaluate endpoints with 90 decimal digits;
        # these fixture deltas are far above the context's cancellation limit.
        def b(v):
            return Decimal(1) if v == 0 else v/(v.exp()-1)
        return Interval(b(self.hi).next_minus(), b(self.lo).next_plus())


def interval_reference(result, driving, policy, layout, cutoff, floor, axis=0):
    """Propagate observation cells instead of widening a relative tolerance.

    Near SG drift/diffusion cancellation, rounding n/phi/Q to binary64 can
    change a reconstructed net current by many relative binary64 ulps.
    Native inputs (VT, spacing, mobility) retain their known exact binary64
    values; only returned observations get rounding cells.
    """
    with localcontext() as context:
        context.prec = 90
        I=Interval; point=I.point; observe=I.observation
        phi=[observe(v) for v in result['phi']]
        charge=Decimal(native_constants()['elementary_charge_definition_C'])
        unit_roundoff=Decimal(2)**-112
        q=I(charge*(1-unit_roundoff),charge*(1+unit_roundoff))
        current=[]
        for hole in [False,True]:
            carrier=[observe(v) for v in result['p' if hole else 'n']]
            quantum=[observe(v) for v in result['Qp' if hole else 'Qn']]
            potential=[v-qv if hole else v+qv for v,qv in zip(phi,quantum)]
            mu=point(.05 if hole else .1)
            mu=point(2.)*mu*mu/(point(2.)*mu+point(1e-30))
            vsat=point(4e4 if hole else 5e4)
            boundary=contacts(layout)[1 if hole else 0]
            flux=[]
            for i in range(4):
                delta=(potential[i+1]-potential[i])/point(VT)
                force=(potential[i+1]-potential[i])/point(H)
                if driving==0 and (policy or (i not in boundary and i+1 not in boundary)):
                    chemical=[potential[j]+(point(VT) if hole else -point(VT))*(carrier[j]/point(1e19)).log() for j in [i,i+1]]
                    force=(chemical[1]-chemical[0])/point(H)
                force=force.absolute()
                if force.hi < Decimal.from_float(float(cutoff)):force=point(0.)
                elif force.lo < Decimal.from_float(float(cutoff)):force=I(0,force.hi)
                ratio=mu*force/vsat
                divisor=point(1.)+ratio if hole else (point(1.)+ratio*ratio).sqrt()
                diffusion=mu/divisor*point(VT)/point(H)
                bp=delta.bernoulli();bm=(-delta).bernoulli()
                net=carrier[i]*bp-carrier[i+1]*bm if hole else carrier[i+1]*bp-carrier[i]*bm
                flux.append(q*diffusion*net)
            current.append(flux)

        def generation(jn,jp):
            source=[point(0.) for _ in range(5)]
            for i in range(4):
                field=((phi[i+1]-phi[i])/point(H)).absolute()
                coefficients=[]
                for a,b in [(1e5,2e5),(2e5,3e5)]:
                    if field.hi<Decimal.from_float(float(floor)):alpha=point(0.)
                    else:
                        high=Decimal.from_float(a)*(-Decimal.from_float(b)/field.hi).exp()
                        low=Decimal(0) if field.lo<Decimal.from_float(float(floor)) else Decimal.from_float(a)*(-Decimal.from_float(b)/field.lo).exp()
                        alpha=I(low.next_minus(),high.next_plus())
                    coefficients.append(alpha)
                edge=(coefficients[0]*jn[i].absolute()+coefficients[1]*jp[i].absolute())/q*point(.5)
                source[i]=source[i]+edge;source[i+1]=source[i+1]+edge
            return source
        rebuilt=generation(*current)
        label='xyz'[axis]
        returned=generation([observe(v) for v in result['Jn_'+label][:4]],
                            [observe(v) for v in result['Jp_'+label][:4]])
        return current,rebuilt,returned


def assert_observations_intersect(values, intervals):
    with localcontext() as context:
        context.prec=90
        for value, expected in zip(values,intervals):
            actual=Interval.observation(value)
            assert actual.lo<=expected.hi and expected.lo<=actual.hi, (value,str(expected.lo),str(expected.hi))


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('driving', [0, 1])
@pytest.mark.parametrize('policy,layout', [(True,'ends'), (False,'ends'), (False,'asymmetric'), (True,'potential_only')])
@pytest.mark.parametrize('cutoff,floor', [(0.,1e5), (3.3e5,1e5), (1e6,6e5)])
def test_quantum_generation_reconstructs_actual_returned_currents(axis, primary, driving, policy, layout, cutoff, floor):
    r = bar(axis, primary, driving, policy, layout, cutoff, floor).solve()
    assert not r['converged']  # Returned operator qualification, never a device solve claim.
    if native_constants()['profile']=='legacy-charge' and (primary,driving,policy,layout,cutoff,floor)==(False,1,True,'potential_only',0.,1e5):
        # Existing failed-state cleanup clips this uncontacted fixture to a
        # uniform density floor. Its zero DG correction is an explicit
        # inactive-Q control, not a nonzero-quantum success.
        for key in ['n','p']:np.testing.assert_array_equal(r[key],np.full(5,1e6))
        for key in ['Qn','Qp']:np.testing.assert_array_equal(r[key],np.zeros(5))
    else:
        assert max(abs(np.asarray(r['Qn']))) > 1e-7
        assert max(abs(np.asarray(r['Qp']))) > 1e-7
    label = 'xyz'[axis]
    (jn,jp),expected,source_from_returned = interval_reference(r,driving,policy,layout,cutoff,floor,axis)
    assert_observations_intersect(r['Jn_'+label][:4],jn)
    assert_observations_intersect(r['Jp_'+label][:4],jp)
    assert_observations_intersect(r['G_ii'],expected)
    assert_observations_intersect(r['G_ii'],source_from_returned)
    returned = expected_generation(r, np.asarray(r['Jn_'+label][:4]), np.asarray(r['Jp_'+label][:4]), floor)
    np.testing.assert_allclose(r['G_ii'], returned, rtol=2e-13, atol=0.)


CONTROL_CASES = [(axis, primary, quantum, ii) for axis in range(3) for primary in [False,True]
                 for quantum, ii in [(False,True), (False,False), (True,False)]]


@pytest.mark.parametrize('axis,primary,quantum,ii', CONTROL_CASES)
def test_unaffected_classical_and_quantum_no_ii_preserve_parent(axis, primary, quantum, ii):
    with open(os.environ['TCAD_QUANTUM_II_ORACLE'], encoding='utf8') as f:
        expected = json.load(f)['controls'][str((axis,primary,quantum,ii))]
    r = bar(axis=axis, primary=primary, quantum=quantum, ii=ii).solve()
    actual = thin_result(r)
    actual.update(Qn=list(r['Qn']), Qp=list(r['Qp']), history=r['nonlinear_history'])
    actual = json.loads(json.dumps(actual, default=lambda value: value.tolist()))
    assert actual == expected


def test_frozen_parent_exposes_quantum_current_source_counterexample():
    with open(os.environ['TCAD_QUANTUM_II_ORACLE'], encoding='utf8') as f:
        before = json.load(f)['counterexample']
    assert before['relative_error'] > 1e-3
    parent = dict(before['result']['arrays'])
    # Returned-current generation needs phi and J, independently of Q. Supply
    # unused zero Q only for the other result of the shared reference helper.
    parent.update(Qn=[0.]*5, Qp=[0.]*5)
    _, _, parent_expected = interval_reference(parent,0,True,'ends',0.,1e5)
    with pytest.raises(AssertionError):
        assert_observations_intersect(parent['G_ii'],parent_expected)
    r = bar().solve()
    jn, jp = expected_flux(r, 0, True, 'ends', 0.)
    np.testing.assert_allclose(r['G_ii'], expected_generation(r, jn, jp, 1e5), rtol=2e-11)
