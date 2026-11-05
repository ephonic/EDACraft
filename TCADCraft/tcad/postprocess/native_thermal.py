"""Independent power balance for the native steady lattice heat equation."""
from collections.abc import Mapping
import math

import numpy as np

from .device_energy import _scalar, _sum
from .current import QE, _validated_elementary_charge


def _array(value, size, name, *, positive=False):
    raw = np.asarray(value)
    if raw.shape != (size,) or raw.dtype.kind not in 'iuf':
        raise ValueError(f'{name} requires {size} real values')
    result = raw.astype(float)
    if not np.all(np.isfinite(result)) or (positive and np.any(result <= 0)):
        raise ValueError(f'{name} requires finite' + (' positive' if positive else '') + ' values')
    return result


def audit_native_steady_thermal(result, axes_m, conductivity_W_m_K, thermal_dirichlet_K,
                                *, extrusion_m, power_atol_W, temperature_atol_K):
    """Audit steady lattice power; reject transient reports without history."""
    if result.get('thermal_ledger', {}).get('transient_storage', False):
        raise ValueError('use audit_native_lattice_step with independent history/capacity')
    return _audit_native_lattice(result, axes_m, conductivity_W_m_K, thermal_dirichlet_K,
        extrusion_m=extrusion_m, power_atol_W=power_atol_W, temperature_atol_K=temperature_atol_K)


def audit_native_lattice_step(result, axes_m, conductivity_W_m_K, thermal_dirichlet_K,
                              previous_temperature_K, heat_capacity_J_m3_K, dt_s,
                              *, extrusion_m, power_atol_W, temperature_atol_K):
    """Rebuild BE heat storage and local/bath balance from caller-owned history."""
    dt = _scalar(dt_s, 'dt_s')
    if dt <= 0:
        raise ValueError('positive time step required')
    return _audit_native_lattice(result, axes_m, conductivity_W_m_K, thermal_dirichlet_K,
        extrusion_m=extrusion_m, power_atol_W=power_atol_W, temperature_atol_K=temperature_atol_K,
        previous_temperature_K=previous_temperature_K, heat_capacity_J_m3_K=heat_capacity_J_m3_K, dt_s=dt)


def _audit_native_lattice(result, axes_m, conductivity_W_m_K, thermal_dirichlet_K,
                         *, extrusion_m, power_atol_W, temperature_atol_K,
                         previous_temperature_K=None, heat_capacity_J_m3_K=None, dt_s=None):
    """Reconstruct edge heating, conduction and bath removal from native states.

    The electrical model supplies absolute J.E heating, optionally using its
    existing 1-D median-current projection. This audits that declared steady
    lattice equation, including heat deposited directly at pinned bath nodes.
    It does not certify carrier heat transport or transient device energy.
    The required power budget is absolute, in W, without a unit-sized floor.
    Geometry and boundary conditions must be supplied independently by caller.
    """
    budget = _scalar(power_atol_W, 'power_atol_W')
    t_budget = _scalar(temperature_atol_K, 'temperature_atol_K')
    if budget <= 0 or t_budget < 0:
        raise ValueError('positive power budget and nonnegative temperature budget required')
    if not isinstance(result, Mapping) or result.get('converged') is not True:
        raise ValueError('converged native result required')
    ledger = result.get('thermal_ledger')
    if not isinstance(ledger, Mapping) or ledger.get('available') is not True:
        raise ValueError('available native thermal ledger required')
    if not isinstance(axes_m, (list, tuple)) or len(axes_m) != 3:
        raise ValueError('three coordinate axes required')
    axes = []
    for index, value in enumerate(axes_m):
        raw = np.asarray(value)
        if raw.ndim != 1 or not raw.size:
            raise ValueError('nonempty coordinate axes required')
        axis = _array(value, raw.size, f'axis {index}')
        if np.any(np.diff(axis) <= 0):
            raise ValueError('strictly increasing coordinate axes required')
        axes.append(axis)
    extrusion = _array(extrusion_m, 3, 'extrusion_m', positive=True)
    count = [len(a) for a in axes]
    nx, ny, nz = count
    size = nx * ny * nz
    width = []
    for axis, thickness in zip(axes, extrusion):
        edges = np.diff(axis)
        width.append(np.array([thickness]) if len(axis) == 1 else
                     np.r_[edges[0], (edges[:-1] + edges[1:]) / 2, edges[-1]])
    kappa = _array(conductivity_W_m_K, size, 'conductivity', positive=True)
    phi = _array(result['phi'], size, 'phi')
    temperature = _array(result['temperature'], size, 'temperature', positive=True)
    volume = np.array([width[0][i]*width[1][j]*width[2][k]
                       for k in range(nz) for j in range(ny) for i in range(nx)])
    if np.any(~np.isfinite(volume)) or np.any(volume <= 0):
        raise ValueError('geometry volumes exceed supported range')
    if not isinstance(thermal_dirichlet_K, Mapping) or not thermal_dirichlet_K:
        raise ValueError('explicit nonempty thermal boundary mapping required')
    for node, value in thermal_dirichlet_K.items():
        if isinstance(node, (bool, np.bool_)) or not isinstance(node, (int, np.integer)) or not 0 <= node < size:
            raise ValueError('thermal boundary node outside grid')
        if _scalar(value, 'bath temperature') <= 0:
            raise ValueError('bath temperature must be positive')
    bath_nodes = np.array(sorted(thermal_dirichlet_K), dtype=int)
    bath_temperatures = np.array([thermal_dirichlet_K[n] for n in bath_nodes], dtype=float)
    given_nodes = np.asarray(ledger['bath_nodes'])
    if given_nodes.dtype.kind not in 'iu' or not np.array_equal(given_nodes, bath_nodes):
        raise ValueError('thermal bath coverage mismatch')
    given_temperatures = _array(ledger['bath_temperatures_K'], len(bath_nodes), 'bath temperatures', positive=True)
    currents = []
    leakage = []
    for axis in 'xyz':
        currents.append(_array(result['Jn_'+axis], size, 'electron current') +
                        _array(result['Jp_'+axis], size, 'hole current'))
        leakage.append(_array(result['Jleak_'+axis], size, 'leakage current'))
    projected = ny == nz == 1 and nx > 4 and ledger.get('mobility_feedback', False) is False
    interior = currents[0][1:nx-2]
    projected_j = float(np.sort(interior)[len(interior)//2]) if projected else 0.
    source = np.zeros(size)
    divergence = np.zeros(size)
    flux = [np.zeros(size) for _ in range(3)]
    projection_weight = 0.
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                node = i + nx*(j + ny*k)
                coordinate = (i, j, k)
                for axis, stride in enumerate((1, nx, nx*ny)):
                    q = coordinate[axis]
                    if q + 1 == count[axis]:
                        continue
                    neighbor = node + stride
                    distance = axes[axis][q+1] - axes[axis][q]
                    area = math.prod(width[b][coordinate[b]] for b in range(3) if b != axis)
                    mobile = projected_j if projected and axis == 0 else currents[axis][node]
                    edge_power = (abs(mobile*(phi[node]-phi[neighbor])) +
                                  abs(leakage[axis][node]*(phi[node]-phi[neighbor]))) * area
                    source[node] += edge_power/2
                    source[neighbor] += edge_power/2
                    if projected and axis == 0:
                        projection_weight += abs(phi[node]-phi[neighbor])*area
                    conductance = 2/(1/kappa[node]+1/kappa[neighbor])*area/distance
                    value = conductance*(temperature[node]-temperature[neighbor])
                    flux[axis][node] = value
                    divergence[node] += value
                    divergence[neighbor] -= value
    free = np.ones(size, dtype=bool)
    free[bath_nodes] = False
    storage = np.zeros(size)
    storage_valid = ledger.get('transient_storage', False) is False
    if dt_s is not None:
        previous = _array(previous_temperature_K, size, 'previous temperature', positive=True)
        capacity = _array(heat_capacity_J_m3_K, size, 'heat capacity', positive=True)
        storage = capacity*volume*(temperature-previous)/dt_s
        reported_storage = _array(ledger['node_storage_power_W'], size, 'node storage power')
        storage_valid = bool(ledger.get('transient_storage') is True and
            _scalar(ledger['dt_s'], 'reported dt') == dt_s and
            np.array_equal(_array(ledger['previous_temperature_K'], size, 'reported history'), previous) and
            np.array_equal(_array(ledger['heat_capacity_J_m3_K'], size, 'reported capacity'), capacity) and
            np.max(abs(reported_storage-storage), initial=0.) <= budget)
    bath_heat = np.zeros(size)
    bath_heat[bath_nodes] = source[bath_nodes] - divergence[bath_nodes] - storage[bath_nodes]
    local = divergence[free] + storage[free] - source[free]
    source_total = _sum(source, 'integrated heat source')
    heat_total = _sum(bath_heat, 'integrated bath heat')
    storage_total = _sum(storage, 'integrated storage power')
    residual = _sum((source_total, -heat_total, -storage_total), 'global heat residual')
    max_cell = float(np.max(abs(local), initial=0.))
    errors = dict(source_power_W=_scalar(ledger['source_power_W'], 'source power')-source_total,
                  outward_heat_W=_scalar(ledger['outward_heat_W'], 'outward heat')-heat_total,
                  balance_residual_W=_scalar(ledger['balance_residual_W'], 'balance residual')-residual,
                  max_cell_residual_W=_scalar(ledger['max_cell_residual_W'], 'cell residual')-max_cell)
    if dt_s is not None:
        errors['storage_power_W'] = _scalar(ledger['storage_power_W'], 'storage power')-storage_total
    power_errors = _array(ledger['power_density_W_m3'], size, 'power density')*volume-source
    bath_errors = _array(ledger['bath_heat_W'], size, 'bath heat')-bath_heat
    flux_errors = np.concatenate([_array(ledger['flux_'+a+'_W'], size, 'heat flux')-f for a, f in zip('xyz', flux)])
    projection_error = _scalar(ledger['projected_Jx_A_m2'], 'projected current')-projected_j
    reported_volume = _array(ledger['node_volumes_m3'], size, 'node volumes', positive=True)
    numbers = np.r_[source, divergence, local, bath_heat, list(errors.values()),
                    power_errors, bath_errors, flux_errors, residual, max_cell, source_total, heat_total]
    if not np.all(np.isfinite(numbers)):
        raise ValueError('thermal balance exceeds supported scalar range')
    geometry_valid = bool(np.allclose(reported_volume, volume, rtol=1e-13, atol=0.))
    boundary_valid = bool(np.array_equal(given_temperatures, bath_temperatures) and
                          np.max(abs(temperature[bath_nodes]-bath_temperatures), initial=0.) <= t_budget)
    contract_valid = (ledger.get('linear_solve_converged') is True and
                      ledger.get('current_projected') is projected and
                      (projected or projection_error == 0.) and
                      ledger.get('complete_device_energy') is False and
                      ledger.get('physical_validated') is False and
                      ledger.get('scope') == ('BE_lattice_absolute_JE_quasistatic_DD' if dt_s is not None
                                             else 'steady_lattice_absolute_JE_with_optional_1d_projection'))
    error_max = max(np.max(abs(power_errors), initial=0.), np.max(abs(bath_errors), initial=0.),
                    np.max(abs(flux_errors), initial=0.), max(map(abs, errors.values())),
                    abs(projection_error)*projection_weight if projected else 0.)
    valid = bool(geometry_valid and boundary_valid and storage_valid and contract_valid and
                 max(error_max, max_cell, abs(residual)) <= budget)
    return dict(valid=valid, modeled_lattice_power_balance_validated=valid,
                backend='cpp_native', scope=('independent_BE_lattice_power_balance' if dt_s is not None
                                             else 'independent_steady_lattice_power_balance'),
                complete_device_energy=False, physical_validated=False,
                source_power_W=source_total, outward_heat_W=heat_total,
                storage_power_W=storage_total, node_storage_power_W=storage, storage_valid=storage_valid,
                direct_bath_deposition_W=float(np.sum(source[bath_nodes])),
                balance_residual_W=residual, free_node_residuals_W=local,
                max_cell_residual_W=max_cell, report_errors_W=errors,
                max_report_error_W=float(error_max), geometry_valid=geometry_valid,
                boundary_valid=boundary_valid, power_atol_W=budget,
                missing_physics=['carrier energy flux and temperature-dependent carrier statistics',
                                 *([] if dt_s is not None else ['transient thermal storage']), 'trap and quantum energy',
                                 'FE domain coupling and commercial heat-flux validation'])


def audit_native_lattice_mobility(result, axes_m, base_mobility_n, base_mobility_p, doping_m3,
                                   mobility_model, reference_temperature_K, reference_VT_V, *,
                                   fixed_point_atol_K, current_rtol, current_atol_A_m2,
                                   elementary_charge_C=QE):
    """Independently check local mobility, SG edge currents and the thermal fixed point.

    This covers the declared classical mobility-only feedback model, whose
    reference VT is held fixed. It does not certify a nonisothermal carrier
    energy or thermoelectric transport model. Geometry/model inputs are caller
    supplied; native mobility values are used only as quantities to compare.
    The standalone charge default is SI. Pass the producing kernel's charge
    explicitly when auditing another constants profile; it is not inferred
    from the currents under audit.
    """
    charge = _validated_elementary_charge(elementary_charge_C)
    if result.get('converged') is not True:
        raise ValueError('converged native result required')
    ledger = result['thermal_ledger']
    axes = [np.asarray(a, dtype=float) for a in axes_m]
    if len(axes) != 3 or any(a.ndim != 1 or not a.size or not np.all(np.isfinite(a)) or
                             np.any(np.diff(a) <= 0) for a in axes):
        raise ValueError('three finite increasing coordinate axes required')
    nx, ny, nz = [len(a) for a in axes]
    size = nx*ny*nz
    tref = _scalar(reference_temperature_K, 'reference temperature')
    vt = _scalar(reference_VT_V, 'reference VT')
    budgets = [_scalar(v, n) for v, n in zip(
        (fixed_point_atol_K, current_rtol, current_atol_A_m2), ('fixed point budget', 'current rtol', 'current atol'))]
    if min(tref, vt) <= 0 or min(budgets) < 0:
        raise ValueError('positive reference temperature/VT and nonnegative budgets required')
    T = _array(ledger['mobility_temperature_K'], size, 'mobility temperature', positive=True)
    temperature = _array(result['temperature'], size, 'temperature', positive=True)
    doping = _array(doping_m3, size, 'doping')
    bases = [_array(base_mobility_n, size, 'base electron mobility'),
             _array(base_mobility_p, size, 'base hole mobility')]
    if any(np.any(a < 0) for a in bases):
        raise ValueError('nonnegative base mobilities required')
    expected = []
    for carrier, base in enumerate(bases):
        if mobility_model == 'constant':
            mu = base.copy()
        elif mobility_model == 'arora':
            low, high, nref, alpha, beta = ((52.2, 1417., 9.68e16, .68, -.66) if carrier == 0
                                           else (49.9, 470.5, 2.23e17, .72, -2.05))
            # The declared minimum is additive; only the doping-dependent
            # contribution carries this model's temperature power law.
            mu = (low+(high-low)/(1+(abs(doping)*1e-6/nref)**alpha)*(T/300.)**beta)*1e-4
            mu = np.where(base == 0, 0., mu)
        elif mobility_model == 'low_temp':
            phonon = (1400. if carrier == 0 else 450.)*(T/300.)**-1.5
            dopant = np.maximum(doping if carrier == 0 else -doping, 0.)*1e-6
            impurity = np.where(dopant > 1., 1e17*T**1.5/np.maximum(dopant, 1.), phonon*1e6)
            mu = np.where(base == 0, 0., 1/(1/phonon+1/impurity)*1e-4)
        else:
            raise ValueError('unknown mobility model')
        expected.append(mu)
    mu_valid = all(np.allclose(_array(ledger['mobility_'+c+'_m2_V_s'], size, 'reported mobility'), mu,
                              rtol=1e-12, atol=0.) for c, mu in zip('np', expected))
    feedback = ledger.get('mobility_feedback') is True
    delta = float(np.max(abs(T-temperature), initial=0.)) if feedback else 0.
    if feedback:
        fp_valid = bool(ledger.get('feedback_converged') is True and delta <= budgets[0] and
            abs(_scalar(ledger['feedback_residual_K'], 'reported residual')-delta) <= 1e-10 and
            ledger.get('current_projected') is False)
    else:
        fp_valid = bool(np.all(T == tref))
    reference_valid = bool(ledger.get('carrier_reference_temperature_K') == tref and
                           ledger.get('carrier_reference_VT_V') == vt)
    phi = _array(result['phi'], size, 'phi')
    densities = [_array(result[c], size, c) for c in 'np']
    if any(np.any(d < 0) for d in densities):
        raise ValueError('nonnegative carrier densities required')
    def bernoulli(x):
        if abs(x) < 1e-5:
            return 1-x/2+x*x/12-x**4/720+x**6/30240
        if x > 100:
            return 0.
        if x < -100:
            return -x
        return x/np.expm1(x)
    current_valid = True
    max_error = 0.
    for axis, stride in enumerate((1, nx, nx*ny)):
        predicted = [np.zeros(size), np.zeros(size)]
        for node in range(size):
            index = (node % nx, (node//nx) % ny, node//(nx*ny))[axis]
            if index+1 == len(axes[axis]):
                continue
            neighbor = node+stride
            d = axes[axis][index+1]-axes[axis][index]
            x = (np.longdouble(phi[neighbor])-np.longdouble(phi[node]))/vt
            plus, minus = bernoulli(x), bernoulli(-x)
            for carrier in range(2):
                mu = expected[carrier]
                edge_mu = 2*np.longdouble(mu[node])*mu[neighbor]/(mu[node]+mu[neighbor]+1e-30)
                density = np.asarray(densities[carrier], dtype=np.longdouble)
                term = (density[neighbor]*plus-density[node]*minus if carrier == 0
                        else density[node]*plus-density[neighbor]*minus)
                predicted[carrier][node] = charge*edge_mu*vt/d*term
        for carrier, c in enumerate('np'):
            observed = _array(result['J'+c+'_'+'xyz'[axis]], size, 'edge current')
            error = abs(observed-predicted[carrier])
            max_error = max(max_error, float(np.max(error, initial=0.)))
            current_valid &= bool(np.all(error <= budgets[2]+budgets[1]*abs(predicted[carrier])))
    valid = bool(ledger.get('available') is True and mu_valid and fp_valid and reference_valid and current_valid)
    return dict(valid=valid, mobility_valid=mu_valid, fixed_point_valid=fp_valid,
        reference_valid=reference_valid, edge_current_valid=current_valid,
        max_current_error_A_m2=max_error, fixed_point_residual_K=delta,
        scope='classical_quasistatic_DD_lattice_mobility_only',
        complete_device_energy=False, physical_validated=False)
