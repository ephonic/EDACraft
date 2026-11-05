"""Physical-DG SG audit of actual returned Newton/hybrid fields, not history."""
import numpy as np
import pytest
from tcad.core import PyDeviceSimulator, native_constants
from test_hfs_contact_policy import bar as base_bar, PHI, N, P, H, VT
from test_newton_returned_audit import same_value


def make_bar(axis, primary, logs, driving, policy, layout, ii, reactions):
    sim = base_bar(axis, primary, driving, ii, policy,
                   'ends' if layout == 'ends' else 'potential_only')
    sim.set_use_newton(True)
    if layout == 'interior':
        sim.set_electron_bc({1: N[1]}); sim.set_hole_bc({3: P[3]})
    sim.set_quantum_enabled(True)
    sim.set_density_gradient_coefficients(1e-15, 7e-16)
    sim.set_newton_use_log_space(logs)
    if reactions:
        sim.set_recombination(np.full(5, 1e-12), np.full(5, 2e-12))
        sim.set_optical_generation(np.full(5, 1e29))
        sim.set_auger_enabled(True); sim.set_auger_params(2.8e-43, 9.9e-44)
    return sim


def reference_rows(r, driving, policy, layout, ii, reactions):
    phi, n, p = (np.asarray(r[k]) for k in ('phi', 'n', 'p'))
    q = float(native_constants()['elementary_charge_C'])
    nb, pb = ({0, 4}, {0, 4}) if layout == 'ends' else (({1}, {3}) if layout == 'interior' else (set(), set()))
    physical_q = []
    for c, coefficient, contacts in [(n, 1e-15, nb), (p, 7e-16, pb)]:
        u = np.sqrt(np.maximum(c, 1.))
        correction = np.zeros(5)
        correction[1:-1] = np.clip(coefficient*np.diff(u, 2)/H**2/u[1:-1], -4*VT, 4*VT)
        for i in contacts: correction[i] = 0.
        physical_q.append(correction)
    for name, expected in zip(['Qn', 'Qp'], physical_q):
        np.testing.assert_allclose(r[name], expected, rtol=2e-10, atol=2e-14)
    data = []
    for c, quantum, mu, vs, beta, contacts, hole in [(n, physical_q[0], .1, 5e4, 2., nb, False),
                                                   (p, physical_q[1], .05, 4e4, 1., pb, True)]:
        v = phi-quantum if hole else phi+quantum
        delta = np.diff(v)/VT
        bp, bm = np.ones(4), np.ones(4)
        active = abs(delta) >= 1e-12
        bp[active] = delta[active]/np.expm1(delta[active])
        bm[active] = -delta[active]/np.expm1(-delta[active])
        force = abs(np.diff(v))/H
        if driving == 0:
            force = abs(np.diff(v)+(1 if hole else -1)*VT*np.diff(np.log(np.maximum(c, 1.))))/H
            if not policy:
                for edge in range(4):
                    if edge in contacts or edge+1 in contacts: force[edge] = abs(v[edge+1]-v[edge])/H
        d = mu*VT/H/(1+(mu*force/vs)**beta)**(1/beta)
        j = q*d*(c[:-1]*bp-c[1:]*bm if hole else c[1:]*bp-c[:-1]*bm)
        data.append((d, bp, bm, j))
    generation = np.zeros(5)
    if ii:
        field = abs(np.diff(phi))/H
        for (a,b), (_,_,_,j) in zip([(1e5,2e5),(2e5,3e5)], data):
            alpha = np.zeros(4); active = field >= 1e5
            alpha[active] = a*np.exp(-b/field[active])
            edge = .5*alpha*abs(j)/q
            generation[:-1] += edge; generation[1:] += edge
    eps = 11.7*8.854187817e-12
    rhs = q*(p[1:-1]-n[1:-1])
    applied = eps/H**2*(2*phi[1:-1]-phi[:-2]-phi[2:])
    rows = [max(np.max(abs(applied-rhs)/(4*VT*eps/H**2+q*(n[1:-1]+p[1:-1])+abs(rhs))),
                np.max(abs(phi[[0,4]]-PHI[[0,4]])/VT))]
    tn,tp,light,cn,cp = (1e-12,2e-12,1e29,2.8e-43,9.9e-44) if reactions else (1e100,1e100,0.,0.,0.)
    # ni/n < 1e-49 for Eg=6 eV: omitted ni terms are below the check's
    # 2e-14 absolute allowance, which also covers binary64 field export.
    den = tp*n+tn*p
    reaction = n*p/den+(cn*n+cp*p)*n*p
    for hole, c, contacts, bc, dr in [(False,n,nb,N,tn*p*p/den**2),(True,p,pb,P,tp*n*n/den**2)]:
        d,bp,bm,_ = data[int(hole)]; values=[]
        for i in range(5):
            if i in contacts:
                values.append(abs(c[i]-bc[i])/(abs(c[i])+abs(bc[i]))); continue
            diagonal = dr[i]*H; neighbors = 0.
            if i:
                diagonal += d[i-1]*(bm[i-1] if hole else bp[i-1])
                neighbors += d[i-1]*(bp[i-1] if hole else bm[i-1])*c[i-1]
            if i<4:
                diagonal += d[i]*(bp[i] if hole else bm[i])
                neighbors += d[i]*(bm[i] if hole else bp[i])*c[i+1]
            diagonal *= c[i]
            source = (light+generation[i]-reaction[i]+dr[i]*c[i])*H
            values.append(abs(diagonal-neighbors-source)/(abs(diagonal)+abs(neighbors)+abs(source)))
        rows.append(max(values))
    return np.asarray(rows)


def check_audit(r, expected):
    audit = r['steady_equation_audit']
    assert audit['available'] and audit['unavailable_reason'] is None
    assert audit['scope'] == 'quantum_Newton_SG_final_returned_state'
    actual = np.asarray([audit[k] for k in ['poisson_scaled_linf','electron_backward_error_linf','hole_backward_error_linf']])
    np.testing.assert_allclose(actual, expected, rtol=2e-8, atol=2e-14)
    assert audit['equations_pass'] == (max(actual) < audit['equation_gate'])
    assert not audit['complete_device_energy'] and not audit['physical_validated']
    return audit


@pytest.mark.parametrize('axis', range(3))
@pytest.mark.parametrize('primary', [False, True])
@pytest.mark.parametrize('logs', [False, True])
@pytest.mark.parametrize('driving', [0,1])
@pytest.mark.parametrize('policy,layout', [(True,'ends'),(False,'interior'),(True,'potential_only')])
@pytest.mark.parametrize('ii', [False,True])
@pytest.mark.parametrize('reactions', [False,True])
def test_actual_returned_quantum_fields(axis, primary, logs, driving, policy, layout, ii, reactions):
    args=(axis,primary,logs,driving,policy,layout,ii,reactions)
    default=make_bar(*args).solve()
    audited=make_bar(*args).solve(audit_newton=True)
    assert not default['converged'] and not audited['converged']
    same_value({k:v for k,v in default.items() if k!='steady_equation_audit'},
               {k:v for k,v in audited.items() if k!='steady_equation_audit'})
    assert not default['steady_equation_audit']['available']
    check_audit(audited, reference_rows(audited,driving,policy,layout,ii,reactions))


@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('logs',[False,True])
def test_uniform_public_success_and_cache_isolation(axis,logs):
    shape=[1,1,1];shape[axis]=5
    def make():
        sim=PyDeviceSimulator(*shape,H,H,H)
        sim.set_quantum_enabled(True);sim.set_density_gradient_coefficients(1e-15,7e-16)
        sim.set_effective_dos(np.full(5,1e19),np.full(5,1e19));sim.set_bandgap(np.full(5,6.))
        sim.set_mobility(np.full(5,.1),np.full(5,.05));sim.set_recombination(np.full(5,1e100),np.full(5,1e100))
        sim.set_dirichlet_potential({0:0.,4:0.});sim.set_electron_bc({1:2e19});sim.set_hole_bc({3:2e19})
        sim.set_initial_guess(np.zeros(5),np.full(5,2e19),np.full(5,2e19));sim.set_thermal_voltage(VT)
        sim.set_use_newton(True);sim.set_newton_primary(True);sim.set_gummel_max_iter(1);sim.set_newton_use_log_space(logs)
        return sim
    plain=make(); audited=make()
    first=audited.solve(audit_newton=True); default=plain.solve()
    assert first['converged'] and default['converged'] and check_audit(first,np.zeros(3))['equations_pass']
    same_value({k:v for k,v in first.items() if k!='steady_equation_audit'},
               {k:v for k,v in default.items() if k!='steady_equation_audit'})
    saved=dict(first['steady_equation_audit']); same_value(audited.solve(),plain.solve())
    assert first['steady_equation_audit']==saved


@pytest.mark.parametrize('feature',['multivalley','step','potential_form','interface_factor','mobility'])
def test_unqualified_quantum_variants_stay_unavailable(feature):
    sim=make_bar(0,True,False,0,True,'ends',False,False)
    if feature=='multivalley':sim.set_density_gradient_silicon_multivalley(True)
    elif feature=='step':sim.set_density_gradient_step_boundary(True,3.17,4.70,.42,1.,1.,1.,.5,.5)
    elif feature=='potential_form':sim.set_density_gradient_potential_form(True)
    elif feature=='interface_factor':sim.set_density_gradient_interface_distance_factor(2.)
    else:sim.set_mobility(np.array([.1,.11,.1,.1,.1]),np.full(5,.05))
    audit=sim.solve(audit_newton=True)['steady_equation_audit']
    assert not audit['available'] and audit['unavailable_reason']=='unsupported_newton_audit_physics'
    assert all(audit[k] is None for k in ['poisson_scaled_linf','electron_backward_error_linf','hole_backward_error_linf','equations_pass'])
