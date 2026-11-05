"""Independent uniform 1D finite-volume rows for returned HFS Newton states."""
import numpy as np
from tcad.core import native_constants


def reference_rows(result, model, coefficients, *, spacing, vt, mobility, dos,
                   bandgap, doping, potential_bc, carrier_bc, lifetime=1e-7,
                   optical=0., auger=(0., 0.), cutoff=0., floor=1e5):
    phi, n, p = [np.asarray(result[key]) for key in ('phi', 'n', 'p')]
    q = float(native_constants()['elementary_charge_C'])
    delta = np.diff(phi)/vt
    bp, bm = np.ones_like(delta), np.ones_like(delta)
    active = np.abs(delta) >= 1e-12
    bp[active] = delta[active]/np.expm1(delta[active])
    bm[active] = -delta[active]/np.expm1(-delta[active])
    mode, refs, enabled, driving, contacts, hfrefs = model
    diffusion = []
    electric = np.abs(np.diff(phi))/spacing
    for c, mu, vsat, beta, sign, ref in [(n, mobility[0], 5e4, 2., -1., hfrefs[0]),
                                        (p, mobility[1], 4e4, 1., 1., hfrefs[1])]:
        force = electric.copy()
        if driving == 0:
            force = np.abs(np.diff(phi)+sign*vt*np.diff(np.log(np.maximum(c+ref, 1.))))/spacing
            if not contacts:
                force[[0, -1]] = electric[[0, -1]]
        force = np.where(force < cutoff, 0., force)
        diffusion.append(mu*vt/spacing/(1.+(mu*force/vsat)**beta)**(1./beta)
                         if enabled else np.full(len(delta), mu*vt/spacing))
    dn, dp = diffusion
    jn = q*dn*(n[1:]*bp-n[:-1]*bm)
    jp = q*dp*(p[:-1]*bp-p[1:]*bm)
    edge = np.zeros_like(delta)
    for c, ref, sign, a, b, current in [(n, refs[0], -1., *coefficients[:2], jn),
                                        (p, refs[1], 1., *coefficients[2:], jp)]:
        force = electric if mode == 0 else np.abs(np.diff(phi)+sign*vt*np.diff(np.log(np.maximum(c+ref, 1e-300))))/spacing
        alpha = np.zeros_like(force)
        active = force >= floor
        alpha[active] = a*np.exp(-b/force[active])
        edge += alpha*np.abs(current)/q
    generation = np.zeros(len(phi)); generation[:-1] += .5*edge; generation[1:] += .5*edge
    np.testing.assert_allclose(result['G_ii'], generation, rtol=2e-11, atol=1e-20)
    ni = np.sqrt(dos[0]*dos[1])*np.exp(-bandgap/(2*8.617333262e-5*300))
    nn, pp = n[1:-1], p[1:-1]
    den = lifetime*(nn+pp+2*ni)
    srh = (nn*pp-ni**2)/den
    reaction = srh+(auger[0]*nn+auger[1]*pp)*(nn*pp-ni**2)
    drn = (pp*(lifetime*ni+lifetime*(pp+ni))+lifetime*ni**2)/den**2
    drp = (nn*(lifetime*ni+lifetime*(nn+ni))+lifetime*ni**2)/den**2
    rows = []
    eps = 11.7*8.854187817e-12
    rhs = q*(pp-nn+doping)
    applied = eps/spacing**2*(2*phi[1:-1]-phi[:-2]-phi[2:])
    scale = 4*vt*eps/spacing**2+q*(nn+pp+abs(doping))+np.abs(rhs)
    rows.append(max(np.max(np.abs(applied-rhs)/scale),
                    np.max(np.abs(phi[[0, -1]]-potential_bc)/vt)))
    for c, d, plus, minus, dr, bc in [(n, dn, bm, bp, drn, carrier_bc[0]),
                                     (p, dp, bp, bm, drp, carrier_bc[1])]:
        diagonal = (d[:-1]*minus[:-1]+d[1:]*plus[1:]+dr*spacing)*c[1:-1]
        left = d[:-1]*plus[:-1]*c[:-2]
        right = d[1:]*minus[1:]*c[2:]
        source = (optical+generation[1:-1]-reaction+dr*c[1:-1])*spacing
        residual = np.abs(diagonal-left-right-source)/(np.abs(diagonal)+np.abs(left)+np.abs(right)+np.abs(source))
        boundary = np.abs(c[[0, -1]]-bc)/(np.abs(c[[0, -1]])+np.abs(bc))
        rows.append(max(np.max(residual), np.max(boundary)))
    return np.array(rows)


def check_rows(result, expected):
    audit = result['steady_equation_audit']
    assert audit['available'] and audit['unavailable_reason'] is None
    assert audit['scope'] == 'classical_Newton_SG_final_returned_state'
    actual = np.array([audit[key] for key in ['poisson_scaled_linf',
                      'electron_backward_error_linf', 'hole_backward_error_linf']])
    assert np.all(np.isfinite(actual)) and np.min(actual) >= 0.
    np.testing.assert_allclose(actual, expected, rtol=2e-8, atol=2e-14)
    assert audit['equations_pass'] == (max(actual) < audit['equation_gate'])
    assert not audit['complete_device_energy'] and not audit['physical_validated']
    return audit


def assert_avalanche_audit_rows(result, ptype, bias, model, coefficients, **extra):
    expected = reference_rows(result, model, coefficients, spacing=1e-6/8,
                              vt=.0258520, mobility=(.1, .035), dos=(2.8e25, 1.04e25),
                              bandgap=1.12, doping=-1e21 if ptype else 1e21,
                              potential_bc=np.array([bias, 0.]),
                              carrier_bc=(1e5 if ptype else 1e21, 1e21 if ptype else 1e5), **extra)
    return check_rows(result, expected)
