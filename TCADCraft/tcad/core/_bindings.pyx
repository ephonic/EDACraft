# distutils: language = c++
# cython: language_level = 3

from libcpp.vector cimport vector
from libcpp.map cimport map
from libcpp.set cimport set as cset
from libcpp.string cimport string
from libcpp cimport bool as cbool
from libc.stddef cimport size_t
import numpy as np
cimport numpy as np

np.import_array()

cdef extern from "linear_solver.h" namespace "tcad":
    cdef cppclass CppLinearSolver "tcad::LinearSolver":
        @staticmethod
        void validate_solver_type(int type) except +


cdef extern from "boltzmann_affine_powerlaw.h" namespace "tcad":
    vector[string] cpp_native_mb_affine_powerlaw_root "tcad::native_mb_affine_powerlaw_root_raw"(const vector[string]&, const vector[string]&) except +


def native_mb_affine_powerlaw_root_raw(endpoint, command):
    cdef vector[string] a = [str(x).encode('ascii') for x in endpoint]
    cdef vector[string] b = [str(x).encode('ascii') for x in command]
    return [x.decode('ascii') for x in cpp_native_mb_affine_powerlaw_root(a,b)]


cdef extern from "boltzmann_affine_collision.h" namespace "tcad":
    vector[string] cpp_native_mb_affine_collision "tcad::native_mb_affine_collision_raw"(const vector[string]&, const vector[string]&) except +


def native_mb_affine_collision_raw(endpoint, command):
    cdef vector[string] a = [str(x).encode('ascii') for x in endpoint]
    cdef vector[string] b = [str(x).encode('ascii') for x in command]
    return [x.decode('ascii') for x in cpp_native_mb_affine_collision(a,b)]


cdef extern from "boltzmann_nonisothermal_transport.h" namespace "tcad":
    vector[string] cpp_native_mb_nonisothermal_face "tcad::native_mb_nonisothermal_face_raw"(const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_mb_nonisothermal_face_raw(owner, neighbor, geometry):
    cdef vector[string] a = [x.encode('ascii') for x in owner]
    cdef vector[string] b = [x.encode('ascii') for x in neighbor]
    cdef vector[string] g = [x.encode('ascii') for x in geometry]
    return [x.decode('ascii') for x in cpp_native_mb_nonisothermal_face(a,b,g)]


cdef extern from "boltzmann_affine_transport.h" namespace "tcad":
    vector[string] cpp_native_mb_affine_face "tcad::native_mb_affine_face_raw"(const vector[string]&, const vector[string]&, const vector[string]&) except +
    vector[string] cpp_native_mb_affine_cell "tcad::native_mb_affine_cell_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_mb_affine_face_raw(owner, neighbor, geometry):
    cdef vector[string] a = [x.encode('ascii') for x in owner]
    cdef vector[string] b = [x.encode('ascii') for x in neighbor]
    cdef vector[string] g = [x.encode('ascii') for x in geometry]
    return [x.decode('ascii') for x in cpp_native_mb_affine_face(a,b,g)]


def native_mb_affine_cell_raw(endpoint, nn, np_, un, up):
    cdef vector[string] f = [x.encode('ascii') for x in endpoint]
    cdef vector[string] n = [x.encode('ascii') for x in nn]
    cdef vector[string] p = [x.encode('ascii') for x in np_]
    cdef vector[string] u = [x.encode('ascii') for x in un]
    cdef vector[string] v = [x.encode('ascii') for x in up]
    return [x.decode('ascii') for x in cpp_native_mb_affine_cell(f,n,p,u,v)]

cdef extern from "boltzmann_frozen_finite_volume.h" namespace "tcad":
    vector[string] cpp_native_mb_fv_integrate "tcad::native_mb_fv_integrate_raw"(const vector[string]&, const string&) except +
    vector[string] cpp_native_mb_fv_cell "tcad::native_mb_fv_cell_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_mb_fv_integrate_raw(values, dt):
    cdef vector[string] v = [x.encode('ascii') for x in values]
    cdef string t = dt.encode('ascii')
    return [x.decode('ascii') for x in cpp_native_mb_fv_integrate(v,t)]


def native_mb_fv_cell_raw(frame, en, ep, nn, np_, un, up):
    cdef vector[string] f = [x.encode('ascii') for x in frame]
    cdef vector[string] a = [x.encode('ascii') for x in en]
    cdef vector[string] b = [x.encode('ascii') for x in ep]
    cdef vector[string] n = [x.encode('ascii') for x in nn]
    cdef vector[string] p = [x.encode('ascii') for x in np_]
    cdef vector[string] u = [x.encode('ascii') for x in un]
    cdef vector[string] v = [x.encode('ascii') for x in up]
    return [x.decode('ascii') for x in cpp_native_mb_fv_cell(f,a,b,n,p,u,v)]

cdef extern from "boltzmann_expanded_flat_face.h" namespace "tcad":
    vector[string] cpp_native_mb_expanded_flat_face "tcad::native_boltzmann_expanded_flat_face_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_boltzmann_expanded_flat_face_raw(owner, on, op, neighbor, nn, np_, geometry):
    cdef vector[string] a = [x.encode('ascii') for x in owner]
    cdef vector[string] an = [x.encode('ascii') for x in on]
    cdef vector[string] ap = [x.encode('ascii') for x in op]
    cdef vector[string] b = [x.encode('ascii') for x in neighbor]
    cdef vector[string] bn = [x.encode('ascii') for x in nn]
    cdef vector[string] bp = [x.encode('ascii') for x in np_]
    cdef vector[string] g = [x.encode('ascii') for x in geometry]
    return [x.decode('ascii') for x in cpp_native_mb_expanded_flat_face(a,an,ap,b,bn,bp,g)]

cdef extern from "boltzmann_expanded_collision.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_expanded_collision "tcad::native_boltzmann_expanded_collision_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, int) except +


def native_boltzmann_expanded_collision_raw(frame, electron_excess, hole_excess, laws, impulses, max_nfev=256):
    """Explicit MB lineage collision/source step; no scalar carrier reduction."""
    if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('integer expanded MB evaluation budget required')
    cdef vector[string] f = [x.encode('ascii') for x in frame]
    cdef vector[string] n = [x.encode('ascii') for x in electron_excess]
    cdef vector[string] p = [x.encode('ascii') for x in hole_excess]
    cdef vector[string] l = [x.encode('ascii') for x in laws]
    cdef vector[string] q = [x.encode('ascii') for x in impulses]
    return [x.decode('ascii') for x in cpp_native_boltzmann_expanded_collision(f,n,p,l,q,max_nfev)]

cdef extern from "boltzmann_particle_energy.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_particle_energy "tcad::native_boltzmann_particle_energy_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_boltzmann_particle_energy_raw(frame, electron_excess, hole_excess, commands):
    """Explicit bounded MB density/band transaction with carrier energy expansions."""
    cdef vector[string] f = [x.encode('ascii') for x in frame]
    cdef vector[string] n = [x.encode('ascii') for x in electron_excess]
    cdef vector[string] p = [x.encode('ascii') for x in hole_excess]
    cdef vector[string] c = [x.encode('ascii') for x in commands]
    return [x.decode('ascii') for x in cpp_native_boltzmann_particle_energy(f,n,p,c)]

cdef extern from "boltzmann_reference_rebase.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_reference_rebase "tcad::native_boltzmann_reference_rebase_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, const string&) except +


def native_boltzmann_reference_rebase_raw(state, parameters, valleys_n, valleys_p, reference):
    """Change only the closed MB lattice energy reference, preserving its journal."""
    cdef vector[string] s = [x.encode('ascii') for x in state]
    cdef vector[string] p = [x.encode('ascii') for x in parameters]
    cdef vector[string] n = [x.encode('ascii') for x in valleys_n]
    cdef vector[string] h = [x.encode('ascii') for x in valleys_p]
    cdef string r = reference.encode('ascii')
    return [x.decode('ascii') for x in cpp_native_boltzmann_reference_rebase(s,p,n,h,r)]

cdef extern from "boltzmann_relaxation.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_relaxation "tcad::native_boltzmann_relaxation_raw"(const vector[string]&, const vector[string]&, const vector[string]&, const vector[string]&, cbool, int) except +


def native_boltzmann_relaxation_raw(state, parameters, valleys_n, valleys_p, initialize=False, max_nfev=256):
    """Explicit closed equal-offset MB cell, b=0; signed energy states."""
    if type(initialize) is not bool or isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('boolean initialization and integer evaluation budget required')
    cdef vector[string] s = [x.encode('ascii') for x in state]
    cdef vector[string] p = [x.encode('ascii') for x in parameters]
    cdef vector[string] n = [x.encode('ascii') for x in valleys_n]
    cdef vector[string] h = [x.encode('ascii') for x in valleys_p]
    return [x.decode('ascii') for x in cpp_native_boltzmann_relaxation(s,p,n,h,initialize,max_nfev)]

cdef extern from "boltzmann_energy_coordinates.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_energy_coordinates "tcad::native_boltzmann_energy_coordinates_raw"(const vector[string]&, const vector[string]&, cbool, int) except +


def native_boltzmann_energy_coordinates_raw(states, valleys, initialize=False, max_iterations=128):
    """Native MB energy inversion preserving signed authoritative excess."""
    if type(initialize) is not bool or isinstance(max_iterations, (bool, np.bool_)) or not isinstance(max_iterations, (int, np.integer)):
        raise ValueError('boolean initialization and integer iteration budget required')
    cdef vector[string] s = [x.encode('ascii') for x in states]
    cdef vector[string] p = [x.encode('ascii') for x in valleys]
    return [x.decode('ascii') for x in cpp_native_boltzmann_energy_coordinates(s,p,initialize,max_iterations)]

cdef extern from "boltzmann_spectral.h" namespace "tcad":
    vector[string] cpp_native_boltzmann_reservoir "tcad::native_boltzmann_reservoir_raw"(const vector[string]&, const vector[string]&) except +
    vector[string] cpp_native_boltzmann_bulk_face "tcad::native_boltzmann_bulk_face_raw"(const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_boltzmann_reservoir_raw(states, valleys):
    """Explicit MB DOS moments; physical inputs and outputs are native decimals."""
    cdef vector[string] s = [v.encode('ascii') for v in states]
    cdef vector[string] p = [v.encode('ascii') for v in valleys]
    return [v.decode('ascii') for v in cpp_native_boltzmann_reservoir(s,p)]


def native_boltzmann_bulk_face_raw(states, geometry, valleys):
    """Native MB bulk moments from physical n/T/band states, not supplied mu."""
    cdef vector[string] s = [v.encode('ascii') for v in states]
    cdef vector[string] g = [v.encode('ascii') for v in geometry]
    cdef vector[string] p = [v.encode('ascii') for v in valleys]
    return [v.decode('ascii') for v in cpp_native_boltzmann_bulk_face(s,g,p)]

cdef extern from "three_temperature_excess_local.h" namespace "tcad":
    vector[string] cpp_native_three_temperature_excess_local "tcad::native_three_temperature_excess_local_raw"(
        const vector[string]&, const vector[string]&, const string&) except +


def native_three_temperature_excess_local_raw(cells, faces, timestep):
    """Explicit local b_Tc=0 carrier-energy elimination; decimal state/output.

    Candidate DOS energies and oriented face/source moments are supplied by the
    caller. This primitive does not advance or validate a whole device.
    """
    cdef vector[string] c = [v.encode('ascii') for v in cells]
    cdef vector[string] f = [v.encode('ascii') for v in faces]
    cdef string dt = timestep.encode('ascii')
    return [v.decode('ascii') for v in cpp_native_three_temperature_excess_local(c,f,dt)]

cdef extern from "isolated_relaxation.h" namespace "tcad":
    vector[string] cpp_native_isolated_relaxation "tcad::native_isolated_relaxation_raw"(
        const vector[string]&, const vector[string]&, const vector[double]&, const vector[double]&, cbool, int) except +

def native_isolated_relaxation_raw(state, parameters, valleys_n, valleys_p, initialize=False, max_nfev=256):
    """Explicit closed single-cell FD BE step with a signed energy-excess state."""
    if type(initialize) is not bool or isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('boolean initialization and integer evaluation budget required')
    cdef vector[string] s = [v.encode('ascii') for v in state]
    cdef vector[string] p = [v.encode('ascii') for v in parameters]
    cdef vector[double] n = valleys_n
    cdef vector[double] h = valleys_p
    return [v.decode('ascii') for v in cpp_native_isolated_relaxation(s,p,n,h,initialize,max_nfev)]

cdef extern from "spectral_auger.h" namespace "tcad":
    vector[vector[double]] cpp_native_spectral_auger "tcad::native_spectral_auger_raw"(const vector[string]&, const vector[string]&) except +

def native_spectral_auger_raw(state, events):
    """On-shell parabolic FD Auger/impact event-table moments."""
    cdef vector[string] s = [v.encode('ascii') for v in state]
    cdef vector[string] e = [v.encode('ascii') for v in events]
    return cpp_native_spectral_auger(s,e)

cdef extern from "spectral_radiative.h" namespace "tcad":
    vector[double] cpp_native_spectral_radiative "tcad::native_spectral_radiative_raw"(const vector[string]&) except +


def native_spectral_radiative_raw(state):
    """Instantaneous matched direct-gap FD/Planck source moments."""
    cdef vector[string] s = [v.encode('ascii') for v in state]
    return cpp_native_spectral_radiative(s)

cdef extern from "spectral_trap_capture.h" namespace "tcad":
    vector[double] cpp_native_spectral_trap_capture "tcad::native_spectral_trap_capture_raw"(const vector[string]&, const vector[string]&, const vector[string]&) except +


def native_spectral_trap_capture_raw(state, valleys_n, valleys_p):
    """Standalone energy-resolved FD capture/emission and trap source moments."""
    cdef vector[string] s = [v.encode('ascii') for v in state]
    cdef vector[string] n = [v.encode('ascii') for v in valleys_n]
    cdef vector[string] p = [v.encode('ascii') for v in valleys_p]
    return cpp_native_spectral_trap_capture(s,n,p)

cdef extern from "math_types.h" namespace "tcad":
    cbool uses_float128()
    int real_mantissa_bits()
    int real_max_decimal_exponent()
    const char* constants_profile_name()
    const char* compiled_constants_profile_name()
    string compiled_elementary_charge_decimal() except +


cdef extern from "si_transport_constants.h" namespace "tcad::si_transport":
    double si_transport_charge "tcad::si_transport::charge_as_double"()


def native_constants():
    """Report constants from the loaded core, independent of the environment.

    legacy-charge selects shared QE only; independent model constants are
    outside this profile. It is not a general commercial-physics preset.
    Cut-cell spectral transport has an independent, fixed SI charge contract.
    """
    profile = compiled_constants_profile_name().decode('ascii')
    if profile != constants_profile_name().decode('ascii'):
        raise RuntimeError("TCAD core and binding constants profiles differ; rebuild in a clean directory")
    return dict(schema_version=1, profile=profile,
                elementary_charge_C=compiled_elementary_charge_decimal().decode('ascii'),
                elementary_charge_definition_C=("1.602192e-19" if profile == "legacy-charge"
                                                else "1.602176634e-19"),
                boltzmann_definition_J_K="1.380649e-23",
                vacuum_permittivity_definition_F_m="8.854187817e-12",
                scope="shared_QE_only", all_model_constants_profiled=False,
                standalone_transport_scope="SI_cut_cell_spectral",
                standalone_elementary_charge_C=si_transport_charge(),
                standalone_elementary_charge_definition_C="1.602176634e-19")


def native_precision():
    """Describe the compiled scalar backend; Python arrays still use float64."""
    return dict(backend="float128" if uses_float128() else "long_double",
                mantissa_bits=real_mantissa_bits(),
                max_decimal_exponent=real_max_decimal_exponent(),
                exported_array_dtype="float64")


cdef extern from "fermi_spectral.h" namespace "tcad":
    vector[double] cpp_native_spectral_face "tcad::native_spectral_face_raw"(const vector[double]&, const vector[double]&) except +


def native_spectral_face_raw(inputs, valleys):
    """Execute native spectral particle, energy and entropy integration."""
    cdef vector[double] parameters = inputs
    cdef vector[double] valley_parameters = valleys
    return cpp_native_spectral_face(parameters, valley_parameters)


cdef extern from "fermi_local.h" namespace "tcad":
    vector[double] cpp_native_fermi_reservoir "tcad::native_fermi_reservoir_raw"(const vector[string]&, const vector[double]&) except +
    vector[double] cpp_native_fermi_local "tcad::native_fermi_local_raw"(const vector[string]&, const vector[string]&, double) except +


def native_fermi_reservoir_raw(states, valleys):
    """FD reservoirs: decimal state boundary preserves longdouble density."""
    cdef vector[string] parameters = [s.encode('ascii') for s in states]
    cdef vector[double] valley_parameters = valleys
    return cpp_native_fermi_reservoir(parameters, valley_parameters)


def native_fermi_local_raw(cells, faces, double dt_s):
    """Assemble actual shared-temperature local conservation equations."""
    cdef vector[string] cell_parameters = [s.encode('ascii') for s in cells]
    cdef vector[string] face_parameters = [s.encode('ascii') for s in faces]
    return cpp_native_fermi_local(cell_parameters, face_parameters, dt_s)


cdef extern from "three_temperature_local.h" namespace "tcad":
    vector[double] cpp_native_three_temperature_local "tcad::native_three_temperature_local_raw"(const vector[string]&, const vector[string]&, double) except +
    vector[double] cpp_native_three_temperature_exchange_local "tcad::native_three_temperature_exchange_local_raw"(const vector[string]&, const vector[string]&, double, const vector[string]&) except +
    vector[double] cpp_native_three_temperature_generation_local "tcad::native_three_temperature_generation_local_raw"(const vector[string]&, const vector[string]&, double, const vector[string]&, const vector[string]&) except +


def native_three_temperature_local_raw(cells, faces, double dt_s):
    """Assemble the five independent-temperature conservation rows natively."""
    cdef vector[string] cell_parameters = [s.encode('ascii') for s in cells]
    cdef vector[string] face_parameters = [s.encode('ascii') for s in faces]
    return cpp_native_three_temperature_local(cell_parameters, face_parameters, dt_s)


def native_three_temperature_exchange_local_raw(cells, faces, double dt_s, exchange):
    """Five native rows with conservative electron-to-hole energy exchange."""
    cdef vector[string] cell_parameters = [s.encode('ascii') for s in cells]
    cdef vector[string] face_parameters = [s.encode('ascii') for s in faces]
    cdef vector[string] exchange_parameters = [s.encode('ascii') for s in exchange]
    return cpp_native_three_temperature_exchange_local(cell_parameters, face_parameters, dt_s, exchange_parameters)


def native_three_temperature_generation_local_raw(cells, faces, double dt_s, exchange, generation):
    """Five native rows with a prescribed neutral pair and absorbed energy source."""
    cdef vector[string] cell_parameters = [s.encode('ascii') for s in cells]
    cdef vector[string] face_parameters = [s.encode('ascii') for s in faces]
    cdef vector[string] exchange_parameters = [s.encode('ascii') for s in exchange]
    cdef vector[string] generation_parameters = [s.encode('ascii') for s in generation]
    return cpp_native_three_temperature_generation_local(cell_parameters, face_parameters, dt_s,
        exchange_parameters, generation_parameters)


cdef extern from "hybrid_poisson.h" namespace "tcad":
    vector[vector[double]] cpp_native_hybrid_poisson "tcad::native_hybrid_poisson_raw"(const vector[string]&, const vector[string]&, double) except +


def native_hybrid_poisson_raw(cells, faces, double charge_atol_C):
    """Assemble geometry, charge and HMM Poisson equations in native real_t."""
    cdef vector[string] cell_parameters = [s.encode('ascii') for s in cells]
    cdef vector[string] face_parameters = [s.encode('ascii') for s in faces]
    return cpp_native_hybrid_poisson(cell_parameters, face_parameters, charge_atol_C)


cdef extern from "fermi_newton.h" namespace "tcad":
    ctypedef int (*FermiResidualCallback)(void*, const vector[double]&, vector[double]&, double*) noexcept
    vector[vector[double]] cpp_native_fermi_newton "tcad::native_fermi_newton_raw"(
        const vector[double]&, const vector[double]&, const vector[double]&, int,
        FermiResidualCallback, void*) except +


cdef int fermi_residual_callback(void* context_pointer, const vector[double]& x,
                                vector[double]& residual, double* merit) noexcept with gil:
    context = <object>context_pointer
    try:
        values, physical_merit = context['callback'](x)
        residual.clear()
        for value in values:
            residual.push_back(value)
        merit[0] = physical_merit
        return 0
    except BaseException as error:
        context['error'] = error
        return -1


def native_fermi_newton_raw(callback, initial, lower, upper, max_nfev=400):
    """Native Newton iteration; residual dispatch explicitly remains in Python.

    max_nfev counts every residual call, including central Jacobian probes.
    The callback returns (normalized_residual, absolute_physical_budget_ratio).
    """
    if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('max_nfev must be a positive integer')
    cdef int budget = max_nfev
    cdef vector[double] x = initial
    cdef vector[double] lo = lower
    cdef vector[double] hi = upper
    context = dict(callback=callback, error=None)
    try:
        return cpp_native_fermi_newton(x, lo, hi, budget, fermi_residual_callback, <void*>context)
    except BaseException:
        if context['error'] is not None:
            raise context['error']
        raise


cdef extern from "fermi_dispatch.h" namespace "tcad":
    cdef cppclass FermiDispatchResult:
        FermiDispatchResult() except +
        int density_mantissa_bits
        vector[string] n,p
        vector[double] temperature,local,fn,fp,energy_flux,old_energy,new_energy
        vector[vector[double]] old_poisson,new_poisson,moments,newton
    FermiDispatchResult cpp_native_fermi_dispatch "tcad::native_fermi_dispatch_raw"(
        const vector[string]&, const vector[string]&, const vector[double]&, const vector[double]&,
        const vector[double]&, int) except + nogil


def native_fermi_dispatch_raw(cells, faces, valleys_n, valleys_p, parameters, max_nfev=400):
    """Run actual native FD residuals and Newton, without a Python callback."""
    if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('max_nfev must be a positive integer')
    cdef int budget = max_nfev
    cdef vector[string] c = [s.encode('ascii') for s in cells]
    cdef vector[string] f = [s.encode('ascii') for s in faces]
    cdef vector[double] vn = valleys_n
    cdef vector[double] vp = valleys_p
    cdef vector[double] args = parameters
    cdef FermiDispatchResult result
    with nogil:
        result = cpp_native_fermi_dispatch(c, f, vn, vp, args, budget)
    return dict(n=[v.decode('ascii') for v in result.n],p=[v.decode('ascii') for v in result.p],
        temperature=result.temperature,local=result.local,fn=result.fn,fp=result.fp,
        energy_flux=result.energy_flux,old_energy=result.old_energy,new_energy=result.new_energy,
        old_poisson=result.old_poisson,new_poisson=result.new_poisson,moments=result.moments,
        newton=result.newton,density_mantissa_bits=result.density_mantissa_bits)


cdef extern from "three_temperature_dispatch.h" namespace "tcad":
    cdef cppclass ThreeTemperatureDispatchResult:
        ThreeTemperatureDispatchResult() except +
        int density_mantissa_bits
        vector[string] n,p
        vector[double] temperature_n,temperature_p,temperature_l,local,fn,fp,energy_n,energy_p
        vector[double] tau_n,tau_p
        vector[double] trap_fraction
        vector[vector[double]] trap_moments
        vector[vector[double]] radiative_moments
        vector[vector[vector[double]]] auger_moments
        vector[vector[double]] old_poisson,new_poisson,moments,newton
    ThreeTemperatureDispatchResult cpp_native_three_temperature_dispatch "tcad::native_three_temperature_dispatch_raw"(
        const vector[string]&, const vector[string]&, const vector[double]&, const vector[double]&,
        const vector[double]&, int) except + nogil


def native_three_temperature_dispatch_raw(cells, faces, valleys_n, valleys_p, parameters, max_nfev=600):
    """Run five-equation three-temperature physics and Newton without Python callbacks."""
    if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
        raise ValueError('max_nfev must be a positive integer')
    cdef int budget = max_nfev
    cdef vector[string] c = [s.encode('ascii') for s in cells]
    cdef vector[string] f = [s.encode('ascii') for s in faces]
    cdef vector[double] vn = valleys_n
    cdef vector[double] vp = valleys_p
    cdef vector[double] args = parameters
    cdef ThreeTemperatureDispatchResult result
    with nogil:
        result = cpp_native_three_temperature_dispatch(c, f, vn, vp, args, budget)
    return three_temperature_result(result)


cdef dict three_temperature_result(ThreeTemperatureDispatchResult result):
    cdef dict value = dict(n=[v.decode('ascii') for v in result.n],p=[v.decode('ascii') for v in result.p],
        temperature_n=result.temperature_n,temperature_p=result.temperature_p,temperature_l=result.temperature_l,
        tau_n=result.tau_n,tau_p=result.tau_p,
        local=result.local,fn=result.fn,fp=result.fp,energy_n=result.energy_n,energy_p=result.energy_p,
        old_poisson=result.old_poisson,new_poisson=result.new_poisson,moments=result.moments,
        newton=result.newton,density_mantissa_bits=result.density_mantissa_bits)
    if not result.trap_fraction.empty():
        value.update(trap_fraction=result.trap_fraction,trap_moments=result.trap_moments)
    if not result.radiative_moments.empty():
        value.update(radiative_moments=result.radiative_moments)
    if not result.auger_moments.empty():
        value.update(auger_moments=result.auger_moments)
    return value


cdef extern from "fermi_energy_coordinates.h" namespace "tcad":
    vector[string] cpp_native_fermi_energy_coordinates "tcad::native_fermi_energy_coordinates_raw"(
        const vector[string]&, const vector[double]&, cbool) except +


cdef vector[string] energy_input_literals(object values) except *:
    from tcad.physics.native_energy_encoding import native_energy_literal
    return [native_energy_literal(v).encode('ascii') for v in values]


def native_fermi_energy_coordinates_raw(states, valleys, initialize=False):
    if type(initialize) is not bool:
        raise ValueError('boolean energy-coordinate initialization required')
    values = list(states)
    if not initialize:
        from tcad.physics.native_energy_encoding import native_energy_literal
        values[2::4] = [native_energy_literal(v) for v in values[2::4]]
    cdef vector[string] s = [v.encode('ascii') for v in values]
    cdef vector[double] packed_valleys = valleys
    return [x.decode('ascii') for x in cpp_native_fermi_energy_coordinates(s,packed_valleys,initialize)]


cdef extern from "energy_coordinate_transport.h" namespace "tcad":
    cdef cppclass EnergyCoordinateTransportResult:
        EnergyCoordinateTransportResult() except +
        ThreeTemperatureDispatchResult transport
        vector[string] excess,ledger,local_cells,local_faces,temperature_cells
        int seed_evaluations
    EnergyCoordinateTransportResult cpp_native_energy_coordinate_transport "tcad::native_energy_coordinate_transport_raw"(
        const vector[string]&, const vector[string]&, const vector[double]&, const vector[double]&, const vector[double]&,
        const vector[string]&, const vector[string]&, int) except + nogil

cdef extern from "energy_coordinate_device.h" namespace "tcad":
    cdef cppclass EnergyCoordinateSnapshot:
        EnergyCoordinateSnapshot() except +
        EnergyCoordinateTransportResult result
        double time
        size_t token


def native_energy_coordinate_transport_raw(cells, faces, valleys_n, valleys_p, parameters, laws, excess, max_nfev=600):
    """Explicit b=0 fixed-band energy-coordinate solve, no Python callbacks."""
    if isinstance(max_nfev,(bool,np.bool_)) or not isinstance(max_nfev,(int,np.integer)):
        raise ValueError('integer shared evaluation budget required')
    cdef vector[string] c = [v.encode('ascii') for v in cells]
    cdef vector[string] f = [v.encode('ascii') for v in faces]
    cdef vector[string] l = [v.encode('ascii') for v in laws]
    cdef vector[string] e = energy_input_literals(excess)
    cdef vector[double] vn = valleys_n
    cdef vector[double] vp = valleys_p
    cdef vector[double] p = parameters
    cdef int budget = max_nfev
    cdef EnergyCoordinateTransportResult result
    with nogil:
        result = cpp_native_energy_coordinate_transport(c,f,vn,vp,p,l,e,budget)
    return energy_coordinate_result(result)


cdef dict energy_coordinate_result(EnergyCoordinateTransportResult result):
    return dict(transport=three_temperature_result(result.transport),
        excess=[v.decode('ascii') for v in result.excess],ledger=[v.decode('ascii') for v in result.ledger],
        local_cells=[v.decode('ascii') for v in result.local_cells],local_faces=[v.decode('ascii') for v in result.local_faces],
        temperature_cells=[v.decode('ascii') for v in result.temperature_cells],seed_evaluations=result.seed_evaluations)


cdef vector[double] np_to_vec(np.ndarray[np.float64_t, ndim=1, mode="c"] arr):
    """Convert 1D numpy float64 array to C++ vector<double>."""
    cdef vector[double] v
    cdef size_t n = arr.size
    v.resize(n)
    for i in range(n):
        v[i] = arr[i]
    return v


cdef vector[signed char] np_to_vec_char(np.ndarray[np.int8_t, ndim=1, mode="c"] arr):
    """Convert 1D numpy int8 array to C++ vector<signed char>."""
    cdef vector[signed char] v
    cdef size_t n = arr.size
    v.resize(n)
    for i in range(n):
        v[i] = <signed char>arr[i]
    return v


# C++ class declarations
cdef extern from "device_simulator_double.h" namespace "tcad":
    cdef cppclass SteadyThermalLedgerDouble:
        cbool available, linear_solve_converged, current_projected
        double projected_Jx, source_power, outward_heat, balance_residual, max_cell_residual
        vector[double] node_volumes, power_density, flux_x, flux_y, flux_z, bath_heat
        vector[size_t] bath_nodes
        vector[double] bath_temperatures
        cbool mobility_feedback, feedback_converged, transient_storage
        size_t feedback_iterations
        double feedback_residual, feedback_tolerance, dt, storage_power, carrier_temperature, carrier_VT
        vector[double] mobility_temperature, mobility_n, mobility_p, previous_temperature, heat_capacity, node_storage_power
    cdef cppclass EquilibriumResultDouble:
        vector[double] phi, n, p
        vector[double] residual_history, update_history, damping_history
        cbool converged
        size_t iterations
        string status
    cdef cppclass NonlinearSolveHistoryDouble:
        string solver
        cbool converged
        double final_poisson_residual
        vector[vector[double]] samples
    cdef cppclass TransientTrialHistoryDouble:
        string role
        string solver
        double start_time, end_time, step_dt
        cbool solver_called, converged, retained, exception
        vector[vector[double]] samples
    cdef cppclass TransientAttemptHistoryDouble:
        double start_time, end_time, step_dt
        size_t retry_index
        cbool error_control, accepted, error_estimate_available
        cbool polarization_control, electrical_control
        double polarization_error_ratio, electrical_error_ratio
        double exported_polarization_error_ratio, exported_electrical_error_ratio
        string status, stopping_reason
        vector[TransientTrialHistoryDouble] trials
    cdef cppclass TransientResultDouble:
        vector[double] phi, n, p, Ex, Ey, Ez, P
        vector[double] Jn_x, Jn_y, Jn_z, Jp_x, Jp_y, Jp_z
        double time, attempted_time, accepted_dt
        cbool converged, initial_state, majority_frozen, phi_frozen
        size_t iterations
        cbool charge_ledger_available
        double mobile_charge
        vector[double] terminal_currents
        cbool electrostatic_flux_available, displacement_current_available
        cbool electrode_charge_available, total_terminal_current_available
        vector[double] D_x, D_y, D_z, Jdisp_x, Jdisp_y, Jdisp_z
        vector[double] Jdielectric_x, Jdielectric_y, Jdielectric_z
        vector[double] Jpolarization_x, Jpolarization_y, Jpolarization_z
        vector[int] electrode_faces
        vector[double] electrode_voltages, electrode_charges
        vector[double] electrode_conduction_currents
        vector[double] electrode_displacement_currents, electrode_total_currents
        vector[double] electrode_dielectric_currents, electrode_polarization_currents
        vector[double] electrode_charge_increments
        cbool dielectric_energy_available, dielectric_energy_increment_available
        double dielectric_energy, dielectric_energy_increment
        cbool lk_energy_available, lk_energy_increment_available
        cbool lk_coupled
        cbool lk_material_field
        cbool lk_substepping
        double lk_step_limit
        cbool lk_error_control, lk_error_estimate_available
        double lk_error_ratio, lk_error_interval, lk_error_end
        double lk_error_rtol, lk_error_atol
        size_t lk_rejected_attempts
        string lk_error_status
        vector[double] lk_coarse_P, lk_error_delta_P
        cbool lk_electrical_error_control
        cbool electrical_error_control
        cbool nls_error_control
        double lk_electrical_error_ratio, lk_phi_atol, lk_carrier_rtol, lk_carrier_atol
        vector[double] lk_coarse_phi, lk_coarse_n, lk_coarse_p
        vector[double] lk_delta_phi, lk_delta_n, lk_delta_p
        double lk_free_energy, lk_free_energy_increment
        double lk_dissipation, lk_field_work, lk_be_correction
        vector[double] lk_node_volumes, lk_parameters, lk_drive_field, lk_polarization_increment
    cdef cppclass IsolatedRelaxationSnapshot:
        vector[string] state
        double time
    cdef cppclass NlsTransientContinuationDouble:
        NlsTransientContinuationDouble() except +
        vector[TransientResultDouble] history() except +
        vector[TransientAttemptHistoryDouble] trace() except +
        int status()
        size_t allocation_failures()
        size_t solver_failures()
        size_t retries()
        double suggested_dt()
        size_t accuracy_rejections()

    cdef cppclass DeviceSimulatorDouble:
        void configure_isolated_relaxation(const vector[string]&,const vector[string]&,const vector[double]&,const vector[double]&,double) except +
        void configure_lattice_excess(const vector[string]&,const vector[string]&,const vector[string]&,const vector[double]&,const vector[double]&,double,const vector[string]&,const vector[string]&) except +
        vector[string] prepare_isolated_relaxation(double,double,double,double,int,const vector[string]&) except + nogil
        size_t isolated_relaxation_token() except +
        void discard_isolated_relaxation(size_t) except +
        void commit_isolated_relaxation(size_t) except +
        IsolatedRelaxationSnapshot isolated_relaxation_state() except +
        cbool isolated_relaxation_enabled()

        void configure_three_temperature(const vector[string]&,const vector[string]&,const vector[double]&,const vector[double]&,const vector[double]&,double) except +
        ThreeTemperatureDispatchResult prepare_three_temperature(double,double,double,double,int) except + nogil
        size_t three_temperature_token() except +
        void discard_three_temperature(size_t) except +
        void commit_three_temperature(size_t) except +
        ThreeTemperatureDispatchResult three_temperature_state() except +
        double three_temperature_time() except +
        vector[vector[double]] structured_three_temperature_seed() except +
        void configure_energy_coordinate(const vector[string]&,const vector[string]&,const vector[double]&,const vector[double]&,
            const vector[double]&,const vector[string]&,const vector[string]&,double) except +
        EnergyCoordinateSnapshot prepare_energy_coordinate(double,double,double,double,int) except + nogil
        void commit_energy_coordinate(size_t) except +
        void discard_energy_coordinate(size_t) except +
        EnergyCoordinateSnapshot energy_coordinate_state() except +
        cbool energy_coordinate_enabled()
        cbool three_temperature_enabled()
        vector[vector[double]] three_temperature_result() except +
        DeviceSimulatorDouble(size_t nx, size_t ny, size_t nz, double dx, double dy, double dz) except +
        void set_permittivity(const vector[double]& eps) except +
        void set_edge_permittivity(const vector[double]& x_plus,
                                   const vector[double]& x_minus,
                                   const vector[double]& y_plus,
                                   const vector[double]& y_minus,
                                   const vector[double]& z_plus,
                               const vector[double]& z_minus) except +
        void set_mobility(const vector[double]& mu_n, const vector[double]& mu_p) except +
        void set_doping(const vector[double]& Nd_minus_Na) except +
        void set_charge_volume_fraction(const vector[double]& fraction) except +
        void set_optical_generation(const vector[double]& G_opt) except +
        void set_btbt_weight(const vector[double]& weight) except +
        void set_recombination(const vector[double]& tau_n, const vector[double]& tau_p) except +
        void set_thermal_voltage(double VT) except +
        void set_effective_dos(const vector[double]& Nc, const vector[double]& Nv) except +
        void set_bandgap(const vector[double]& Eg) except +
        void set_dirichlet_potential(const map[size_t, double]& bc) except +
        void set_electron_bc(const map[size_t, double]& bc) except +
        void set_hole_bc(const map[size_t, double]& bc) except +
        void set_quantum_enabled(cbool enable)
        void set_density_gradient_coefficients(double bn, double bp) except +
        void set_density_gradient_silicon_multivalley(
            cbool enable, double longitudinal_mass, double transverse_mass,
            size_t subbands) except +
        void set_density_gradient_interface_distance_factor(double factor) except +
        void set_density_gradient_potential_form(cbool enable)
        void set_density_gradient_step_boundary(
            cbool enable, double electron_barrier_eV, double hole_barrier_eV,
            double electron_barrier_mass, double hole_barrier_mass,
            double electron_gamma, double hole_gamma,
            double electron_theta, double hole_theta) except +
        void set_z_positions(const vector[double]& z_pos) except +
        void set_x_positions(const vector[double]& x_pos) except +
        void set_y_positions(const vector[double]& y_pos) except +
        void set_gummel_max_iter(size_t max_iter)
        void set_nonlinear_history_enabled(cbool enable)
        void set_tolerance(double tol) except +
        void set_poisson_solver_type(int type) except +
        void set_continuity_solver_type(int type) except +
        void set_use_newton(cbool enable)
        void set_newton_primary(cbool enable)
        EquilibriumResultDouble solve_equilibrium(size_t max_iter, double tolerance, const vector[char]& carrier_mask) except +
        void set_ohmic_contacts(const cset[size_t]& nodes,
                                const map[size_t, double]& EFn,
                                const map[size_t, double]& EFp,
                                double ni) except +
        void clear_ohmic_contacts()
        void set_newton_freeze_phi(cbool enable)
        void set_newton_freeze_n(cbool enable)
        void set_newton_freeze_p(cbool enable)
        void set_newton_damping(double damping)
        void set_newton_min_damping(double min_damping)
        void set_newton_use_line_search(cbool enable)
        void set_newton_line_search_max(size_t max)
        void set_newton_use_log_damping(cbool enable)
        void set_newton_use_log_space(cbool enable)
        void set_newton_log_density_update(const string& mode) except +
        string get_newton_log_density_update()
        void set_newton_jacobian_reuse_threshold(double threshold)
        void set_thermal_coupling_enabled(cbool enable)
        void set_lattice_mobility_feedback(cbool enable, size_t max_iter, double temperature_tol, double relaxation) except +
        void solve_lattice_step(const vector[double]& previous_temperature, const vector[double]& heat_capacity, double dt) except +
        void set_thermal_conductivity(const vector[double]& kappa) except +
        void set_ambient_temperature(double T_ambient) except +
        void set_thermal_dirichlet(const map[size_t, double]& bc) except +
        void set_btbt_enabled(cbool enable)
        void set_btbt_params(double A, double B, double D)
        void set_btbt_field_mode(int mode)
        void set_btbt_field_options(int mode, double cap)
        void set_btbt_field_shape(int mode, double cap, double alpha, double ref)
        void set_btbt_continuity_scale(double scale) except +
        void set_btbt_use_nonlocal(cbool enable)
        void set_btbt_nonlocal_params(double tunnel_path_frac, size_t wkb_npts) except +
        void set_btbt_nonlocal_mass(double mass_ratio) except +
        void set_high_field_saturation(cbool enable, double vsat_n, double vsat_p, double beta_n, double beta_p, int driving) except +
        void set_hfs_quasi_fermi_at_contacts(bint enabled)
        bint get_hfs_quasi_fermi_at_contacts() const
        void set_high_field_reference_density(double n0, double p0) except +
        double get_high_field_reference_density_n() const
        double get_high_field_reference_density_p() const
        void set_hfs_low_field_cutoff(double cutoff) except +
        double get_hfs_low_field_cutoff() const
        void set_ii_enabled(cbool enable)
        void set_ii_reference_density(double n0, double p0) except +
        double get_ii_reference_density_n() const
        double get_ii_reference_density_p() const
        void set_ii_driving(int driving) except +
        int get_ii_driving() const
        void set_ii_field_floor(double floor) except +
        double get_ii_field_floor() const
        void set_ii_params(double A_n, double B_n, double A_p, double B_p) except +
        void set_auger_enabled(cbool enable)
        void set_auger_params(double Cn, double Cp) except +
        void set_breakdown_enabled(cbool enable)
        void set_breakdown_params(const vector[signed char]& bd_mask,
                                  const vector[double]& E_bd, double sigma_bd) except +
        vector[signed char] breakdown_state()
        void set_ferroelectric_enabled(cbool enable)
        void set_history_updates_enabled(cbool enable)
        void begin_reliability_transaction() except +
        void commit_reliability_transaction() except +
        void rollback_reliability_transaction() except +
        void set_ferroelectric_params(const vector[signed char]& fe_mask, double alpha, double beta) except +
        void set_ferroelectric_model(int model)
        void set_ferroelectric_preisach(double ps, double ec, double escale) except +
        void set_ferroelectric_builtin_field(double E_bi) except +
        void set_ferroelectric_depol(double eps_fe) except +
        void set_ferroelectric_nls(double tau0, double E0, double dt) except +
        void set_ferroelectric_polar_axis(int axis)
        void set_leakage(const vector[signed char]& mask,
                         double C_pf, double B_pf, double phi_t,
                         double C_fn, double B_fn, double phi_b,
                         double E_floor, double sigma_cap) except +
        void set_leakage_fn_polarity(double C_positive, double B_positive,
                                     double C_negative, double B_negative) except +
        void set_leakage_enabled(cbool enable)
        void set_interface_traps(const vector[signed char]& mask, double D_it, double E_t) except +
        void set_oxide_traps(const vector[double]& Q_ot) except +
        vector[double] fe_polarization()

        void set_initial_guess(const vector[double]& phi,
                               const vector[double]& n,
                               const vector[double]& p) except +
        void clear_initial_guess()

        void set_temperature(double T) except +
        void set_statistics_type(int type)
        void set_mobility_model(int type)

        void set_transient_enabled(cbool enable)
        void set_transient_dt(double dt) except +
        void set_transient_t_final(double t_final) except +
        void set_transient_lk_coupled(cbool enable)
        void set_transient_lk_material_field(cbool enable)
        void set_transient_lk_zero_d_faces(const string& faces) except +
        void set_transient_lk_substepping(cbool enable, double safety) except +
        void set_transient_lk_error_control(cbool enable, double rtol, double atol,
            double min_dt, size_t max_reject) except +
        void set_transient_lk_electrical_error_control(cbool enable, double phi_atol,
            double carrier_rtol, double carrier_atol) except +
        void set_transient_electrical_error_control(cbool enable, double phi_atol,
            double carrier_rtol, double carrier_atol, double min_dt, size_t max_reject) except +
        void set_transient_nls_error_control(cbool enable, double rtol, double atol,
            double phi_atol, double carrier_rtol, double carrier_atol,
            double min_dt, size_t max_reject) except +
        void set_transient_nls_event_control(cbool enable, double half_width) except +
        void set_transient_voltage_waveforms(const vector[double]& times, const map[size_t, vector[double]]& offsets) except +
        void clear_transient_voltage_waveforms() except +
        void set_ferroelectric_gamma(double gamma) except +
        void set_ferroelectric_history(const vector[double]& polarization) except +
        vector[double] get_ferroelectric_history()
        void set_ferroelectric_ensemble_history(const vector[double]& p, const vector[double]& play) except +
        vector[double] get_ferroelectric_play_history()
        vector[double] get_ferroelectric_ensemble_parameters()
        vector[int] get_ferroelectric_mask()
        vector[double] get_ferroelectric_lk_parameters()
        vector[double] get_permittivity()
        void set_transient_start_time(double time) except +

        vector[double] solve_potential() except +
        vector[double] solve_electrons()
        vector[double] solve_holes()
        vector[double] solve_Ex()
        vector[double] solve_Ey()
        vector[double] solve_Ez()
        vector[double] solve_temperature()
        SteadyThermalLedgerDouble solve_thermal_ledger() except +
        vector[double] solve_Qn()
        vector[double] solve_Qp()
        vector[double] solve_Jn_x()
        vector[double] solve_Jn_y()
        vector[double] solve_Jn_z()
        vector[double] solve_Jp_x()
        vector[double] solve_Jp_y()
        vector[double] solve_Jp_z()
        vector[double] solve_Jleak_x()
        vector[double] solve_Jleak_y()
        vector[double] solve_Jleak_z()
        vector[double] solve_G_btbt()
        vector[double] solve_G_ii()
        cbool solve_converged()

        void reset_solved()
        size_t solve_iterations()
        double solve_poisson_residual()
        double solve_quantum_residual()
        vector[double] solve_steady_gummel_audit()
        void audit_steady_equations() except +
        string solve_steady_gummel_audit_status()
        cbool solve_nonlinear_history_enabled()
        vector[NonlinearSolveHistoryDouble] solve_nonlinear_history()
        vector[TransientAttemptHistoryDouble] transient_attempt_history()

        vector[vector[double]] solve_transient_phi()
        vector[vector[double]] solve_transient_n()
        vector[vector[double]] solve_transient_p()
        vector[cbool] solve_transient_converged()
        vector[TransientResultDouble] solve_transient_results() except +
        void advance_transient_nls(NlsTransientContinuationDouble&, size_t) except +

        size_t nx()
        size_t ny()
        size_t nz()
        size_t npts()


cdef object _export_transient_trace(const vector[TransientAttemptHistoryDouble]& groups):
    cdef size_t i, j
    result = []
    columns = ('relative_block_max', 'raw_phi_l2', 'raw_n_l2', 'raw_p_l2',
               'scaled_merit_rms', 'equilibrated_linf')
    for i in range(groups.size()):
        entry = dict(group_index=i, start_time_s=groups[i].start_time,
                     attempted_time_s=groups[i].end_time, dt_s=groups[i].step_dt,
                     retry_index=groups[i].retry_index, error_control=bool(groups[i].error_control),
                     polarization_control=bool(groups[i].polarization_control),
                     electrical_control=bool(groups[i].electrical_control),
                     accepted=bool(groups[i].accepted), status=groups[i].status.decode('utf-8'),
                     stopping_reason=groups[i].stopping_reason.decode('utf-8'),
                     error_estimate_available=bool(groups[i].error_estimate_available),
                     polarization_error_ratio=(groups[i].polarization_error_ratio
                         if groups[i].error_estimate_available and groups[i].polarization_control else None),
                     electrical_error_ratio=(groups[i].electrical_error_ratio
                         if groups[i].error_estimate_available and groups[i].electrical_control else None),
                     exported_polarization_error_ratio=(groups[i].exported_polarization_error_ratio
                         if groups[i].error_estimate_available and groups[i].polarization_control else None),
                     exported_electrical_error_ratio=(groups[i].exported_electrical_error_ratio
                         if groups[i].error_estimate_available and groups[i].electrical_control else None), trials=[])
        for j in range(groups[i].trials.size()):
            solver = groups[i].trials[j].solver.decode('utf-8')
            columns = (('voltage_residual_V', 'd_voltage_d_displacement_m2_F')
                if solver == 'lk_material_field_1d' else
                ('relative_block_max', 'raw_phi_l2', 'raw_n_l2', 'raw_p_l2',
                 'scaled_merit_rms', 'equilibrated_linf'))
            trial = dict(role=groups[i].trials[j].role.decode('utf-8'), solver=solver,
                         start_time_s=groups[i].trials[j].start_time,
                         attempted_time_s=groups[i].trials[j].end_time,
                         dt_s=groups[i].trials[j].step_dt,
                         solver_called=bool(groups[i].trials[j].solver_called),
                         converged=bool(groups[i].trials[j].converged),
                         retained=bool(groups[i].trials[j].retained),
                         exception=bool(groups[i].trials[j].exception),
                         sample_scope=('voltage_constraint_base_states' if solver == 'lk_material_field_1d'
                                       else 'outer_base_states_before_line_search'))
            samples = np.array(groups[i].trials[j].samples, dtype=np.float64).reshape(-1, len(columns))
            for column_index, column in enumerate(columns):
                trial[column] = samples[:, column_index].copy()
            entry['trials'].append(trial)
        result.append(entry)
    return result

cdef object _export_transient_results(const vector[TransientResultDouble]& history):
    cdef size_t n_steps = history.size()
    results = []
    for i in range(n_steps):
        item = {
            "phi": np.array(history[i].phi, dtype=np.float64),
            "n": np.array(history[i].n, dtype=np.float64),
            "p": np.array(history[i].p, dtype=np.float64),
            "P": np.array(history[i].P, dtype=np.float64),
            "Ex": np.array(history[i].Ex, dtype=np.float64),
            "Ey": np.array(history[i].Ey, dtype=np.float64),
            "Ez": np.array(history[i].Ez, dtype=np.float64),
            "Jn_x": np.array(history[i].Jn_x, dtype=np.float64),
            "Jn_y": np.array(history[i].Jn_y, dtype=np.float64),
            "Jn_z": np.array(history[i].Jn_z, dtype=np.float64),
            "Jp_x": np.array(history[i].Jp_x, dtype=np.float64),
            "Jp_y": np.array(history[i].Jp_y, dtype=np.float64),
            "Jp_z": np.array(history[i].Jp_z, dtype=np.float64),
            "converged": bool(history[i].converged),
            "valid": bool(history[i].converged),
            "iterations": int(history[i].iterations),
            "time_s": history[i].time,
            "attempted_time_s": history[i].attempted_time,
            "dt_s": history[i].accepted_dt,
            "initial_state": bool(history[i].initial_state),
            "phi_frozen": bool(history[i].phi_frozen),
            "majority_frozen": bool(history[i].majority_frozen),
            "charge_ledger_available": bool(history[i].charge_ledger_available),
            "electrostatic_flux_available": bool(history[i].electrostatic_flux_available),
            "displacement_current_available": bool(history[i].displacement_current_available),
            "electrode_charge_available": bool(history[i].electrode_charge_available),
            "total_terminal_current_available": bool(history[i].total_terminal_current_available),
            "dielectric_energy_available": bool(history[i].dielectric_energy_available),
            "dielectric_energy_increment_available": bool(history[i].dielectric_energy_increment_available),
            "dielectric_energy_scope": "linear_lossless_charge_free_dielectric",
            "lk_energy_available": bool(history[i].lk_energy_available),
            "lk_coupled": bool(history[i].lk_coupled),
            "lk_material_field": bool(history[i].lk_material_field),
            "lk_substepping": bool(history[i].lk_substepping),
            "lk_step_limit_s": history[i].lk_step_limit if history[i].lk_substepping else 0.,
            "lk_energy_increment_available": bool(history[i].lk_energy_increment_available),
            "lk_energy_scope": "lk_local_backward_euler_nodal_quadrature",
            "electrode_scope": (
                "complete equipotential potential-contact planes; free-node volume "
                "with unit charge fractions and reciprocal face permittivity; "
                "contact-to-contact edges excluded; positive charge/current into device; "
                "total current requires matching active-carrier contacts or pure dielectric; "
                "backward-Euler interval currents; initial/rejected intervals undefined"
            ),
            "charge_ledger_scope": (
                "mobile free-node control volumes; prescribed carrier-contact "
                "nodes and contact-to-contact edges excluded; inward face-current "
                "convention; unit Poisson charge fractions; finite optical/SRH "
                "pair sources cancel in net charge, without an energy claim; "
                "two active carriers throughout, or validated material-side "
                "1-D transport with neutral empty paired-zero-mobility nodes"
            ),
        }
        if history[i].charge_ledger_available:
            item["stored_charge_C"] = history[i].mobile_charge
            item["terminal_currents_A"] = np.array(history[i].terminal_currents, dtype=np.float64)
        if history[i].electrostatic_flux_available:
            item["D_x"] = np.array(history[i].D_x, dtype=np.float64)
            item["D_y"] = np.array(history[i].D_y, dtype=np.float64)
            item["D_z"] = np.array(history[i].D_z, dtype=np.float64)
        if history[i].displacement_current_available:
            item["Jdisp_x"] = np.array(history[i].Jdisp_x, dtype=np.float64)
            item["Jdisp_y"] = np.array(history[i].Jdisp_y, dtype=np.float64)
            item["Jdisp_z"] = np.array(history[i].Jdisp_z, dtype=np.float64)
            item["Jdielectric_x"] = np.array(history[i].Jdielectric_x, dtype=np.float64)
            item["Jdielectric_y"] = np.array(history[i].Jdielectric_y, dtype=np.float64)
            item["Jdielectric_z"] = np.array(history[i].Jdielectric_z, dtype=np.float64)
            item["Jpolarization_x"] = np.array(history[i].Jpolarization_x, dtype=np.float64)
            item["Jpolarization_y"] = np.array(history[i].Jpolarization_y, dtype=np.float64)
            item["Jpolarization_z"] = np.array(history[i].Jpolarization_z, dtype=np.float64)
        if history[i].electrode_charge_available:
            names = ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")
            item["electrode_names"] = [names[face] for face in history[i].electrode_faces]
            item["electrode_voltages_V"] = np.array(history[i].electrode_voltages, dtype=np.float64)
            item["electrode_charges_C"] = np.array(history[i].electrode_charges, dtype=np.float64)
        if history[i].total_terminal_current_available:
            item["electrode_conduction_currents_A"] = np.array(history[i].electrode_conduction_currents, dtype=np.float64)
            item["electrode_displacement_currents_A"] = np.array(history[i].electrode_displacement_currents, dtype=np.float64)
            item["electrode_total_currents_A"] = np.array(history[i].electrode_total_currents, dtype=np.float64)
            item["electrode_dielectric_currents_A"] = np.array(history[i].electrode_dielectric_currents, dtype=np.float64)
            item["electrode_polarization_currents_A"] = np.array(history[i].electrode_polarization_currents, dtype=np.float64)
            item["electrode_charge_increments_C"] = np.array(history[i].electrode_charge_increments, dtype=np.float64)
        if history[i].dielectric_energy_available:
            item["dielectric_energy_J"] = history[i].dielectric_energy
        if history[i].dielectric_energy_increment_available:
            item["dielectric_energy_increment_J"] = history[i].dielectric_energy_increment
        if history[i].lk_error_control:
            item["lk_error_control"] = True
            item["lk_error_scope"] = "lk_polarization_step_doubling_BE"
            item["lk_error_estimate_available"] = bool(history[i].lk_error_estimate_available)
            item["lk_error_ratio"] = history[i].lk_error_ratio
            item["lk_error_interval_s"] = history[i].lk_error_interval
            item["lk_error_end_s"] = history[i].lk_error_end
            item["lk_error_rtol"] = history[i].lk_error_rtol
            item["lk_error_atol_C_per_m2"] = history[i].lk_error_atol
            item["lk_rejected_attempts"] = history[i].lk_rejected_attempts
            item["lk_error_status"] = history[i].lk_error_status.decode("ascii")
            if not history[i].lk_coarse_P.empty():
                item["lk_coarse_P_C_per_m2"] = np.array(history[i].lk_coarse_P, dtype=np.float64)
                item["lk_error_delta_P_C_per_m2"] = np.array(history[i].lk_error_delta_P, dtype=np.float64)
        if history[i].lk_electrical_error_control:
            item["lk_electrical_error_control"] = True
            item["lk_electrical_error_scope"] = "lk_electrical_step_doubling_BE"
            item["lk_electrical_error_ratio"] = history[i].lk_electrical_error_ratio
            item["lk_phi_atol_V"] = history[i].lk_phi_atol
            item["lk_carrier_rtol"] = history[i].lk_carrier_rtol
            item["lk_carrier_atol_per_m3"] = history[i].lk_carrier_atol
            if not history[i].lk_coarse_phi.empty():
                item["lk_coarse_phi_V"] = np.array(history[i].lk_coarse_phi, dtype=np.float64)
                item["lk_coarse_n_per_m3"] = np.array(history[i].lk_coarse_n, dtype=np.float64)
                item["lk_coarse_p_per_m3"] = np.array(history[i].lk_coarse_p, dtype=np.float64)
            if not history[i].lk_delta_phi.empty():
                item["lk_delta_phi_V"] = np.array(history[i].lk_delta_phi, dtype=np.float64)
                item["lk_delta_n_per_m3"] = np.array(history[i].lk_delta_n, dtype=np.float64)
                item["lk_delta_p_per_m3"] = np.array(history[i].lk_delta_p, dtype=np.float64)
        if history[i].electrical_error_control:
            item["electrical_error_control"] = True
            item["electrical_error_scope"] = "classical_electrical_step_doubling_BE"
            item["electrical_error_estimate_available"] = bool(history[i].lk_error_estimate_available)
            item["electrical_error_ratio"] = history[i].lk_electrical_error_ratio
            item["electrical_error_interval_s"] = history[i].lk_error_interval
            item["electrical_error_end_s"] = history[i].lk_error_end
            item["electrical_step_limit_s"] = history[i].lk_step_limit
            item["electrical_rejected_attempts"] = history[i].lk_rejected_attempts
            item["electrical_error_status"] = history[i].lk_error_status.decode("ascii")
            item["electrical_phi_atol_V"] = history[i].lk_phi_atol
            item["electrical_carrier_rtol"] = history[i].lk_carrier_rtol
            item["electrical_carrier_atol_per_m3"] = history[i].lk_carrier_atol
            if not history[i].lk_coarse_phi.empty():
                item["electrical_coarse_phi_V"] = np.array(history[i].lk_coarse_phi, dtype=np.float64)
                item["electrical_coarse_n_per_m3"] = np.array(history[i].lk_coarse_n, dtype=np.float64)
                item["electrical_coarse_p_per_m3"] = np.array(history[i].lk_coarse_p, dtype=np.float64)
            if not history[i].lk_delta_phi.empty():
                item["electrical_delta_phi_V"] = np.array(history[i].lk_delta_phi, dtype=np.float64)
                item["electrical_delta_n_per_m3"] = np.array(history[i].lk_delta_n, dtype=np.float64)
                item["electrical_delta_p_per_m3"] = np.array(history[i].lk_delta_p, dtype=np.float64)
        if history[i].nls_error_control:
            item["nls_error_control"] = True
            item["nls_error_scope"] = "split_nls_polarization_electrical_step_doubling"
            item["nls_error_estimate_available"] = bool(history[i].lk_error_estimate_available)
            item["nls_error_ratio"] = max(history[i].lk_error_ratio, history[i].lk_electrical_error_ratio)
            item["nls_error_interval_s"] = history[i].lk_error_interval
            item["nls_error_end_s"] = history[i].lk_error_end
            item["nls_step_limit_s"] = history[i].lk_step_limit
            item["nls_rejected_attempts"] = history[i].lk_rejected_attempts
            item["nls_error_status"] = history[i].lk_error_status.decode("ascii")
            item["nls_phi_atol_V"] = history[i].lk_phi_atol
            item["nls_carrier_rtol"] = history[i].lk_carrier_rtol
            item["nls_carrier_atol_per_m3"] = history[i].lk_carrier_atol
            item["nls_polarization_rtol"] = history[i].lk_error_rtol
            item["nls_polarization_atol_C_per_m2"] = history[i].lk_error_atol
            if not history[i].lk_coarse_P.empty():
                item["nls_coarse_P_C_per_m2"] = np.array(history[i].lk_coarse_P, dtype=np.float64)
                item["nls_delta_P_C_per_m2"] = np.array(history[i].lk_error_delta_P, dtype=np.float64)
            if not history[i].lk_coarse_phi.empty():
                item["nls_coarse_phi_V"] = np.array(history[i].lk_coarse_phi, dtype=np.float64)
                item["nls_coarse_n_per_m3"] = np.array(history[i].lk_coarse_n, dtype=np.float64)
                item["nls_coarse_p_per_m3"] = np.array(history[i].lk_coarse_p, dtype=np.float64)
            if not history[i].lk_delta_phi.empty():
                item["nls_delta_phi_V"] = np.array(history[i].lk_delta_phi, dtype=np.float64)
                item["nls_delta_n_per_m3"] = np.array(history[i].lk_delta_n, dtype=np.float64)
                item["nls_delta_p_per_m3"] = np.array(history[i].lk_delta_p, dtype=np.float64)
        if history[i].lk_energy_available:
            item["lk_free_energy_J"] = history[i].lk_free_energy
            item["lk_node_volumes_m3"] = np.array(history[i].lk_node_volumes, dtype=np.float64)
            # alpha, beta, gamma, imprint field, extra depolarization eps_r, polar axis
            item["lk_parameters"] = np.array(history[i].lk_parameters, dtype=np.float64)
        if history[i].lk_energy_increment_available:
            item["lk_free_energy_increment_J"] = history[i].lk_free_energy_increment
            item["lk_dissipation_J"] = history[i].lk_dissipation
            item["lk_field_work_J"] = history[i].lk_field_work
            item["lk_be_correction_J"] = history[i].lk_be_correction
            item["lk_drive_field_V_per_m"] = np.array(history[i].lk_drive_field, dtype=np.float64)
            item["lk_polarization_increment_C_per_m2"] = np.array(history[i].lk_polarization_increment, dtype=np.float64)
        results.append(item)
    return results


cdef class PyDeviceSimulator:
    cdef DeviceSimulatorDouble* _sim
    cdef size_t _nx, _ny, _nz, _npts

    def __cinit__(self, size_t nx, size_t ny, size_t nz,
                  double dx, double dy, double dz):
        self._sim = new DeviceSimulatorDouble(nx, ny, nz, dx, dy, dz)
        self._nx = nx
        self._ny = ny
        self._nz = nz
        self._npts = nx * ny * nz

    def __dealloc__(self):
        if self._sim != NULL:
            del self._sim

    def configure_isolated_relaxation(self, initial, parameters, valleys_n, valleys_p, double time_s=0.):
        cdef vector[string] state = [v.encode('ascii') for v in initial]
        cdef vector[string] args = [v.encode('ascii') for v in parameters]
        cdef vector[double] vn = valleys_n
        cdef vector[double] vp = valleys_p
        self._sim.configure_isolated_relaxation(state, args, vn, vp, time_s)

    def configure_lattice_excess(self, initial, parameters, faces, valleys_n, valleys_p, double time_s=0., baths=(), varshni=()):
        cdef vector[string] state = [v.encode('ascii') for v in initial]
        cdef vector[string] args = [v.encode('ascii') for v in parameters]
        cdef vector[string] edges = [v.encode('ascii') for v in faces]
        cdef vector[string] boundary = [v.encode('ascii') for v in baths]
        cdef vector[string] band = [v.encode('ascii') for v in varshni]
        cdef vector[double] vn = valleys_n
        cdef vector[double] vp = valleys_p
        self._sim.configure_lattice_excess(state, args, edges, vn, vp, time_s, boundary, band)

    def prepare_isolated_relaxation(self, double dt_s, double charge_atol_C, double particle_atol,
                                    double energy_atol_J, max_nfev=256, source_impulses_J=()):
        if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)) or max_nfev <= 0:
            raise ValueError('max_nfev must be a positive integer')
        cdef int budget = max_nfev
        cdef vector[string] result
        cdef vector[string] source = [v.encode('ascii') for v in source_impulses_J]
        cdef size_t token
        with nogil:
            result = self._sim.prepare_isolated_relaxation(dt_s, charge_atol_C, particle_atol, energy_atol_J, budget, source)
        token = self._sim.isolated_relaxation_token()
        try:
            return [v.decode('ascii') for v in result], token
        except BaseException:
            self._sim.discard_isolated_relaxation(token)
            raise

    def commit_isolated_relaxation(self, size_t token):
        self._sim.commit_isolated_relaxation(token)

    def discard_isolated_relaxation(self, size_t token):
        self._sim.discard_isolated_relaxation(token)

    def isolated_relaxation_state(self):
        cdef IsolatedRelaxationSnapshot result = self._sim.isolated_relaxation_state()
        return dict(state=[v.decode('ascii') for v in result.state], time_s=result.time)

    def configure_three_temperature(self, cells, faces, valleys_n, valleys_p, parameters, double time_s=0.):
        cdef vector[string] c = [v.encode('ascii') for v in cells]
        cdef vector[string] f = [v.encode('ascii') for v in faces]
        cdef vector[double] vn = valleys_n
        cdef vector[double] vp = valleys_p
        cdef vector[double] args = parameters
        self._sim.configure_three_temperature(c, f, vn, vp, args, time_s)

    def prepare_three_temperature(self, double dt_s, double charge_atol_C, double particle_atol,
                                  double energy_atol_J, max_nfev=600):
        if isinstance(max_nfev, (bool, np.bool_)) or not isinstance(max_nfev, (int, np.integer)):
            raise ValueError('max_nfev must be a positive integer')
        cdef int budget = max_nfev
        cdef ThreeTemperatureDispatchResult result
        with nogil:
            result = self._sim.prepare_three_temperature(dt_s, charge_atol_C, particle_atol, energy_atol_J, budget)
        return three_temperature_result(result), self._sim.three_temperature_token()

    def commit_three_temperature(self, size_t token):
        self._sim.commit_three_temperature(token)

    def discard_three_temperature(self, size_t token):
        self._sim.discard_three_temperature(token)

    def three_temperature_state(self):
        result = three_temperature_result(self._sim.three_temperature_state())
        result['time_s'] = self._sim.three_temperature_time()
        return result

    def structured_three_temperature_seed(self):
        """Owned actual native coefficients/BCs; reject unsupported source physics."""
        values = self._sim.structured_three_temperature_seed()
        names = ('epsilon','mu_n','mu_p','doping_m3','Nc_m3','Nv_m3','Eg_eV','conductivity',
                 'temperature_ambient_K','phi_bc','n_bc','p_bc','thermal_bc','x_positions','y_positions',
                 'z_positions','spacings')
        return dict(zip(names, values))

    def three_temperature_result(self):
        """Committed SimulationResult buffers; decimal state is available separately."""
        values = self._sim.three_temperature_result()
        return dict(zip(('phi_V','n_m3','p_m3','Tn_K','Tp_K','Tl_K'), values))

    def configure_energy_coordinate(self, cells, faces, valleys_n, valleys_p, parameters, laws, excess, double time_s=0.):
        cdef vector[string] c = [v.encode('ascii') for v in cells]
        cdef vector[string] f = [v.encode('ascii') for v in faces]
        cdef vector[string] l = [v.encode('ascii') for v in laws]
        cdef vector[string] e = energy_input_literals(excess)
        cdef vector[double] vn = valleys_n
        cdef vector[double] vp = valleys_p
        cdef vector[double] args = parameters
        self._sim.configure_energy_coordinate(c,f,vn,vp,args,l,e,time_s)

    def prepare_energy_coordinate(self, double dt_s, double charge_atol_C, double particle_atol,
                                   double energy_atol_J, max_nfev=600):
        if isinstance(max_nfev,(bool,np.bool_)) or not isinstance(max_nfev,(int,np.integer)) or max_nfev<=0:
            raise ValueError('max_nfev must be a positive integer')
        cdef int budget = max_nfev
        cdef EnergyCoordinateSnapshot snapshot
        with nogil:
            snapshot = self._sim.prepare_energy_coordinate(dt_s,charge_atol_C,particle_atol,energy_atol_J,budget)
        try:
            return dict(raw=energy_coordinate_result(snapshot.result),time_s=snapshot.time),snapshot.token
        except BaseException:
            self._sim.discard_energy_coordinate(snapshot.token)
            raise

    def commit_energy_coordinate(self, size_t token):
        self._sim.commit_energy_coordinate(token)

    def discard_energy_coordinate(self, size_t token):
        self._sim.discard_energy_coordinate(token)

    def energy_coordinate_state(self):
        cdef EnergyCoordinateSnapshot snapshot = self._sim.energy_coordinate_state()
        return dict(raw=energy_coordinate_result(snapshot.result),time_s=snapshot.time)

    def set_permittivity(self, np.ndarray[np.float64_t, ndim=1, mode="c"] eps not None):
        self._sim.set_permittivity(np_to_vec(eps))

    def set_edge_permittivity(self,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] x_plus not None,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] x_minus not None,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] y_plus not None,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] y_minus not None,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] z_plus not None,
                              np.ndarray[np.float64_t, ndim=1, mode="c"] z_minus not None):
        self._sim.set_edge_permittivity(
            np_to_vec(x_plus), np_to_vec(x_minus),
            np_to_vec(y_plus), np_to_vec(y_minus),
            np_to_vec(z_plus), np_to_vec(z_minus))

    def set_mobility(self, np.ndarray[np.float64_t, ndim=1, mode="c"] mu_n not None,
                     np.ndarray[np.float64_t, ndim=1, mode="c"] mu_p not None):
        self._sim.set_mobility(np_to_vec(mu_n), np_to_vec(mu_p))

    def set_doping(self, np.ndarray[np.float64_t, ndim=1, mode="c"] Nd_minus_Na not None):
        self._sim.set_doping(np_to_vec(Nd_minus_Na))

    def set_charge_volume_fraction(
            self, np.ndarray[np.float64_t, ndim=1, mode="c"] fraction not None):
        self._sim.set_charge_volume_fraction(np_to_vec(fraction))

    def set_optical_generation(self, np.ndarray[np.float64_t, ndim=1, mode="c"] G_opt not None):
        self._sim.set_optical_generation(np_to_vec(G_opt))

    def set_btbt_weight(self, np.ndarray[np.float64_t, ndim=1, mode="c"] weight not None):
        self._sim.set_btbt_weight(np_to_vec(weight))

    def set_recombination(self, np.ndarray[np.float64_t, ndim=1, mode="c"] tau_n not None,
                          np.ndarray[np.float64_t, ndim=1, mode="c"] tau_p not None):
        self._sim.set_recombination(np_to_vec(tau_n), np_to_vec(tau_p))

    def set_thermal_voltage(self, double VT):
        self._sim.set_thermal_voltage(VT)

    def set_effective_dos(self, np.ndarray[np.float64_t, ndim=1, mode="c"] Nc not None,
                          np.ndarray[np.float64_t, ndim=1, mode="c"] Nv not None):
        self._sim.set_effective_dos(np_to_vec(Nc), np_to_vec(Nv))

    def set_bandgap(self, np.ndarray[np.float64_t, ndim=1, mode="c"] Eg not None):
        self._sim.set_bandgap(np_to_vec(Eg))

    def set_dirichlet_potential(self, dict bc):
        cdef map[size_t, double] m
        for key, val in bc.items():
            m[<size_t>int(key)] = <double>val
        self._sim.set_dirichlet_potential(m)

    def set_electron_bc(self, dict bc):
        cdef map[size_t, double] m
        for key, val in bc.items():
            m[<size_t>int(key)] = <double>val
        self._sim.set_electron_bc(m)

    def set_hole_bc(self, dict bc):
        cdef map[size_t, double] m
        for key, val in bc.items():
            m[<size_t>int(key)] = <double>val
        self._sim.set_hole_bc(m)

    def set_quantum_enabled(self, bint enable):
        self._sim.set_quantum_enabled(enable)

    def set_density_gradient_coefficients(self, double bn, double bp):
        """Set electron/hole DG coefficients in V*m^2."""
        self._sim.set_density_gradient_coefficients(bn, bp)

    def set_density_gradient_silicon_multivalley(
        self, bint enable, double longitudinal_mass=0.916,
        double transverse_mass=0.190, size_t subbands=4
    ):
        """Configure the Si <100> Delta-valley/subband DG closure."""
        self._sim.set_density_gradient_silicon_multivalley(
            enable, longitudinal_mass, transverse_mass, subbands
        )

    def set_density_gradient_interface_distance_factor(self, double factor):
        """Set the semiconductor-to-inactive-neighbor DG distance scale."""
        self._sim.set_density_gradient_interface_distance_factor(factor)

    def set_density_gradient_potential_form(self, bint enable):
        """Select the opt-in Sentaurus potential-form DG solver."""
        self._sim.set_density_gradient_potential_form(enable)

    def set_density_gradient_step_boundary(
            self, bint enable, double electron_barrier_eV,
            double hole_barrier_eV, double electron_barrier_mass,
            double hole_barrier_mass, double electron_gamma,
            double hole_gamma, double electron_theta, double hole_theta):
        """Configure the potential-form material-step DG boundary closure."""
        self._sim.set_density_gradient_step_boundary(
            enable, electron_barrier_eV, hole_barrier_eV,
            electron_barrier_mass, hole_barrier_mass,
            electron_gamma, hole_gamma, electron_theta, hole_theta)

    def set_z_positions(self, np.ndarray[np.float64_t, ndim=1, mode="c"] z_pos not None):
        """Set non-uniform z-node positions for local mesh refinement.
        When set, the Poisson/continuity/current assembly uses per-edge
        spacing derived from these positions instead of the uniform dz."""
        self._sim.set_z_positions(np_to_vec(z_pos))

    def set_x_positions(self, np.ndarray[np.float64_t, ndim=1, mode="c"] x_pos not None):
        self._sim.set_x_positions(np_to_vec(x_pos))

    def set_y_positions(self, np.ndarray[np.float64_t, ndim=1, mode="c"] y_pos not None):
        """Set non-uniform y-node positions for local mesh refinement."""
        self._sim.set_y_positions(np_to_vec(y_pos))

    def set_gummel_max_iter(self, size_t max_iter):
        self._sim.set_gummel_max_iter(max_iter)

    def set_nonlinear_history_enabled(self, enable):
        """Opt in to steady and transient nonlinear outer-iteration diagnostics.

        Stages/retries remain separate; update norms and equation residuals
        have distinct names. Transient groups include discarded trials.
        No line-search or inner linear-solve trace.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("nonlinear history flag must be a boolean")
        self._sim.set_nonlinear_history_enabled(bool(enable))

    def set_tolerance(self, double tol):
        self._sim.set_tolerance(tol)

    def validate_linear_solver_type(self, int type):
        """Validate this build's backend without changing device options."""
        CppLinearSolver.validate_solver_type(type)

    def set_poisson_solver_type(self, int type):
        self._sim.set_poisson_solver_type(type)

    def set_continuity_solver_type(self, int type):
        self._sim.set_continuity_solver_type(type)

    def set_use_newton(self, bint enable):
        self._sim.set_use_newton(enable)

    def set_newton_primary(self, bint enable):
        self._sim.set_newton_primary(enable)

    def solve_equilibrium(self, max_iter=100, tolerance=1e-10, *, carrier_mask=None):
        """Build a classical zero-Fermi PB seed; failed runs preserve the prior seed.

        Residuals use the unlinearized Poisson operator with row scaling
        VT*sum|Aij| + q*f*(n+p+|doping|). Updates are absolute volts and
        must be <= VT*tolerance; the scaled residual must be <= tolerance.
        No transport, quantum, ferroelectric or interface-injection solve is
        implied. Non-Boltzmann statistics and incompatible reservoirs reject.
        carrier_mask is an optional boolean array of length npts. False nodes
        have exactly zero PB n/p; their fixed Poisson charge and permittivity
        remain active. The mask applies only to this initialization call.
        Omitting it preserves the existing charge-volume-based selection.
        """
        if (isinstance(max_iter, (bool, np.bool_)) or
                not isinstance(max_iter, (int, np.integer)) or max_iter < 0):
            raise ValueError("max_iter must be a nonnegative integer")
        if (isinstance(tolerance, (bool, np.bool_)) or
                not isinstance(tolerance, (int, float, np.integer, np.floating)) or
                not np.isfinite(tolerance) or tolerance <= 0):
            raise ValueError("tolerance must be positive and finite")
        cdef vector[char] selected
        cdef size_t index
        cdef char mask_value
        if carrier_mask is not None:
            mask_array = np.asarray(carrier_mask)
            if mask_array.dtype.kind != 'b' or mask_array.shape != (self._sim.npts(),):
                raise ValueError("carrier_mask must be a boolean array with one entry per mesh node")
            for index in range(self._sim.npts()):
                # Keep the value in typed storage: a conditional expression
                # passed to push_back(const char&) can become a dangling
                # temporary reference in generated Cython C++.
                mask_value = 0
                if mask_array[index]:
                    mask_value = 1
                selected.push_back(mask_value)
        cdef EquilibriumResultDouble r = self._sim.solve_equilibrium(max_iter, tolerance, selected)
        return dict(phi=np.array(r.phi, dtype=np.float64),
                    n=np.array(r.n, dtype=np.float64), p=np.array(r.p, dtype=np.float64),
                    residual_history=np.array(r.residual_history, dtype=np.float64),
                    update_history_V=np.array(r.update_history, dtype=np.float64),
                    damping_history=np.array(r.damping_history, dtype=np.float64),
                    iterations=r.iterations, converged=bool(r.converged),
                    initial_guess_committed=bool(r.converged), status=r.status.decode('utf-8'),
                    model='classical_poisson_boltzmann_zero_fermi', physical_validated=False)

    def set_ohmic_contacts(self, nodes, EFn, EFp, double ni):
        cdef cset[size_t] c_nodes
        cdef map[size_t, double] c_efn
        cdef map[size_t, double] c_efp
        for n in nodes: c_nodes.insert(n)
        for k, v in EFn.items(): c_efn[k] = v
        for k, v in EFp.items(): c_efp[k] = v
        self._sim.set_ohmic_contacts(c_nodes, c_efn, c_efp, ni)

    def clear_ohmic_contacts(self):
        self._sim.clear_ohmic_contacts()

    def set_newton_freeze_phi(self, bint enable):
        self._sim.set_newton_freeze_phi(enable)

    def set_newton_freeze_n(self, bint enable):
        self._sim.set_newton_freeze_n(enable)

    def set_newton_freeze_p(self, bint enable):
        self._sim.set_newton_freeze_p(enable)

    def set_newton_damping(self, double damping):
        self._sim.set_newton_damping(damping)

    def set_newton_min_damping(self, double min_damping):
        self._sim.set_newton_min_damping(min_damping)

    def set_newton_use_line_search(self, bint enable):
        self._sim.set_newton_use_line_search(enable)

    def set_newton_line_search_max(self, size_t max):
        self._sim.set_newton_line_search_max(max)

    def set_newton_use_log_damping(self, bint enable):
        self._sim.set_newton_use_log_damping(enable)

    def set_newton_use_log_space(self, bint enable):
        self._sim.set_newton_use_log_space(enable)

    def set_newton_log_density_update(self, mode):
        """Choose exponential (default) or additive updates of log-space carriers.

        Per-instance; independent of process environment. Does not enable Newton
        or log-space. Additive updates reject nonpositive trial density factors.
        """
        if not isinstance(mode, str) or mode not in ('exponential', 'additive'):
            raise ValueError("Newton log-density update must be exponential or additive")
        self._sim.set_newton_log_density_update(mode.encode('ascii'))

    def get_newton_log_density_update(self):
        return self._sim.get_newton_log_density_update().decode('ascii')

    def set_newton_jacobian_reuse_threshold(self, double threshold):
        self._sim.set_newton_jacobian_reuse_threshold(threshold)

    def set_lattice_mobility_feedback(self, bint enable=True, max_iter=100,
                                     double temperature_tol_K=1e-7, double relaxation=0.5):
        if isinstance(max_iter, (bool, np.bool_)) or not isinstance(max_iter, (int, np.integer)) or not 1 <= max_iter <= 10000:
            raise ValueError("max_iter must be an integer in [1, 10000]")
        self._sim.set_lattice_mobility_feedback(enable, max_iter, temperature_tol_K, relaxation)

    def solve_lattice_step(self, previous_temperature_K, heat_capacity_J_m3_K, double dt_s):
        if np.asarray(previous_temperature_K).dtype.kind not in 'iuf' or np.asarray(heat_capacity_J_m3_K).dtype.kind not in 'iuf':
            raise ValueError("lattice history and capacity require real numeric values")
        previous = np.ascontiguousarray(previous_temperature_K, dtype=np.float64)
        capacity = np.ascontiguousarray(heat_capacity_J_m3_K, dtype=np.float64)
        if previous.shape != (self._npts,) or capacity.shape != (self._npts,):
            raise ValueError("lattice history and capacity require one value per node")
        self._sim.solve_lattice_step(np_to_vec(previous), np_to_vec(capacity), dt_s)
        return self._export_result()

    def set_thermal_coupling_enabled(self, bint enable):
        self._sim.set_thermal_coupling_enabled(enable)

    def set_thermal_conductivity(self, np.ndarray[np.float64_t, ndim=1, mode="c"] kappa not None):
        self._sim.set_thermal_conductivity(np_to_vec(kappa))

    def set_ambient_temperature(self, double T_ambient):
        self._sim.set_ambient_temperature(T_ambient)

    def set_thermal_dirichlet(self, dict bc):
        cdef map[size_t, double] bc_map
        for idx, val in bc.items():
            bc_map[<size_t>idx] = <double>val
        self._sim.set_thermal_dirichlet(bc_map)

    def set_btbt_enabled(self, bint enable):
        self._sim.set_btbt_enabled(enable)

    def set_btbt_params(self, double A, double B, double D):
        self._sim.set_btbt_params(A, B, D)

    def set_btbt_field_mode(self, int mode):
        self._sim.set_btbt_field_mode(mode)

    def set_btbt_field_options(self, int mode, double cap):
        self._sim.set_btbt_field_options(mode, cap)

    def set_btbt_field_shape(self, int mode, double cap, double alpha, double ref):
        self._sim.set_btbt_field_shape(mode, cap, alpha, ref)

    def set_btbt_continuity_scale(self, double scale):
        self._sim.set_btbt_continuity_scale(scale)

    def set_btbt_use_nonlocal(self, bint enable):
        self._sim.set_btbt_use_nonlocal(enable)

    def set_btbt_nonlocal_params(self, double tunnel_path_frac, size_t wkb_npts):
        self._sim.set_btbt_nonlocal_params(tunnel_path_frac, wkb_npts)

    def set_btbt_nonlocal_mass(self, double mass_ratio):
        self._sim.set_btbt_nonlocal_mass(mass_ratio)

    def set_high_field_saturation(self, bint enable, double vsat_n,
                                  double vsat_p, double beta_n,
                                  double beta_p, int driving):
        self._sim.set_high_field_saturation(enable, vsat_n, vsat_p,
                                            beta_n, beta_p, driving)

    def set_hfs_quasi_fermi_at_contacts(self, enabled):
        """Use the configured HFS driving at carrier contacts (default True)."""
        if not isinstance(enabled, (bool, np.bool_)):
            raise ValueError("HFS quasi-Fermi contact policy must be boolean")
        self._sim.set_hfs_quasi_fermi_at_contacts(bool(enabled))

    def get_hfs_quasi_fermi_at_contacts(self):
        return bool(self._sim.get_hfs_quasi_fermi_at_contacts())

    def set_high_field_reference_density(self, double n0, double p0):
        """Set finite nonnegative HFS GQF reference densities [m^-3]."""
        self._sim.set_high_field_reference_density(n0,p0)

    def get_high_field_reference_density(self):
        return (self._sim.get_high_field_reference_density_n(),self._sim.get_high_field_reference_density_p())

    def set_hfs_low_field_cutoff(self, cutoff):
        """Set a finite nonnegative numerical HFS driving-force cutoff [V/m]."""
        if isinstance(cutoff, (bool, np.bool_)) or not isinstance(
                cutoff, (int, float, np.integer, np.floating)):
            raise ValueError("HFS low-field cutoff must be a finite nonnegative real [V/m]")
        self._sim.set_hfs_low_field_cutoff(float(cutoff))

    def get_hfs_low_field_cutoff(self):
        return self._sim.get_hfs_low_field_cutoff()

    def set_ii_enabled(self, bint enable):
        self._sim.set_ii_enabled(enable)

    def set_ii_reference_density(self, double n0, double p0):
        """Set finite nonnegative II GQF reference densities [m^-3]."""
        self._sim.set_ii_reference_density(n0,p0)

    def get_ii_reference_density(self):
        return (self._sim.get_ii_reference_density_n(),self._sim.get_ii_reference_density_p())

    def set_ii_driving(self, driving):
        """II driving: integer 0 ElectricField, 1 GradQuasiFermi."""
        if isinstance(driving,(bool,np.bool_)) or not isinstance(driving,(int,np.integer)) or driving not in (0,1):
            raise ValueError("impact ionization driving must be integer 0 (ElectricField) or 1 (GradQuasiFermi)")
        self._sim.set_ii_driving(int(driving))

    def get_ii_driving(self):
        return self._sim.get_ii_driving()

    def set_ii_field_floor(self, floor):
        """Set a finite positive numerical avalanche cutoff [V/m]."""
        if isinstance(floor, (bool, np.bool_)) or not isinstance(
                floor, (int, float, np.integer, np.floating)):
            raise ValueError("impact ionization field floor must be a finite positive real [V/m]")
        self._sim.set_ii_field_floor(float(floor))

    def get_ii_field_floor(self):
        return self._sim.get_ii_field_floor()

    def set_ii_params(self, double A_n, double B_n, double A_p, double B_p):
        self._sim.set_ii_params(A_n, B_n, A_p, B_p)

    def set_auger_enabled(self, bint enable):
        self._sim.set_auger_enabled(enable)

    def set_auger_params(self, double Cn, double Cp):
        self._sim.set_auger_params(Cn, Cp)

    def set_breakdown_enabled(self, bint enable):
        self._sim.set_breakdown_enabled(enable)

    def set_breakdown_params(self,
                             np.ndarray[np.int8_t, ndim=1, mode="c"] bd_mask not None,
                             np.ndarray[np.float64_t, ndim=1, mode="c"] E_bd not None,
                             double sigma_bd):
        self._sim.set_breakdown_params(np_to_vec_char(bd_mask), np_to_vec(E_bd), sigma_bd)

    def breakdown_state(self):
        cdef vector[signed char] s = self._sim.breakdown_state()
        return np.array(s, dtype=np.int8)

    def set_ferroelectric_enabled(self, bint enable):
        self._sim.set_ferroelectric_enabled(enable)

    def set_history_updates_enabled(self, bint enable):
        """Keep FE and breakdown history fixed during numerical helper solves."""
        self._sim.set_history_updates_enabled(enable)

    def set_ferroelectric_params(self, np.ndarray[np.int8_t, ndim=1, mode="c"] fe_mask not None,
                                 double alpha, double beta):
        self._sim.set_ferroelectric_params(np_to_vec_char(fe_mask), alpha, beta)

    def set_ferroelectric_model(self, int model):
        self._sim.set_ferroelectric_model(model)

    def set_ferroelectric_preisach(self, double ps, double ec, double escale):
        self._sim.set_ferroelectric_preisach(ps, ec, escale)

    def set_ferroelectric_builtin_field(self, double E_bi):
        # P2.1: internal/imprint field offset [V/m]; 0 => symmetric loop.
        self._sim.set_ferroelectric_builtin_field(E_bi)

    def set_ferroelectric_depol(self, double eps_fe):
        # comments2.docx P3: depolarization field E_dep=-P/(eps_fe*eps0).
        self._sim.set_ferroelectric_depol(eps_fe)

    def set_ferroelectric_nls(self, double tau0, double E0, double dt):
        # P3: NLS Merz-law tau(E)=tau0*exp(E0/|E|); dt = dwell time per step.
        self._sim.set_ferroelectric_nls(tau0, E0, dt)

    def set_ferroelectric_polar_axis(self, int axis):
        self._sim.set_ferroelectric_polar_axis(axis)

    def set_leakage(self, np.ndarray[np.int8_t, ndim=1, mode="c"] mask not None,
                    double C_pf, double B_pf, double phi_t,
                    double C_fn, double B_fn, double phi_b,
                    double E_floor, double sigma_cap):
        # P2.2: Poole-Frenkel / Fowler-Nordheim leakage current.
        self._sim.set_leakage(np_to_vec_char(mask),
                              C_pf, B_pf, phi_t, C_fn, B_fn, phi_b, E_floor, sigma_cap)

    def set_leakage_fn_polarity(self, double C_positive, double B_positive,
                                double C_negative, double B_negative):
        self._sim.set_leakage_fn_polarity(
            C_positive, B_positive, C_negative, B_negative)

    def set_leakage_enabled(self, bint enable):
        self._sim.set_leakage_enabled(enable)

    def set_interface_traps(self, np.ndarray[np.int8_t, ndim=1, mode="c"] mask not None,
                            double D_it, double E_t):
        # P6: interface trap charge injection into Poisson RHS.
        self._sim.set_interface_traps(np_to_vec_char(mask), D_it, E_t)

    def set_oxide_traps(self, np.ndarray[np.float64_t, ndim=1, mode="c"] Q_ot not None):
        # P6: persistent bulk oxide trap charge [C/m^3].
        self._sim.set_oxide_traps(np_to_vec(Q_ot))

    def set_initial_guess(self, np.ndarray[np.float64_t, ndim=1, mode="c"] phi not None,
                          np.ndarray[np.float64_t, ndim=1, mode="c"] n not None,
                          np.ndarray[np.float64_t, ndim=1, mode="c"] p not None):
        self._sim.set_initial_guess(np_to_vec(phi), np_to_vec(n), np_to_vec(p))

    def clear_initial_guess(self):
        self._sim.clear_initial_guess()

    def begin_reliability_transaction(self):
        self._sim.begin_reliability_transaction()

    def commit_reliability_transaction(self):
        self._sim.commit_reliability_transaction()

    def rollback_reliability_transaction(self):
        self._sim.rollback_reliability_transaction()

    def set_temperature(self, double T):
        self._sim.set_temperature(T)

    def set_statistics_type(self, int type):
        self._sim.set_statistics_type(type)

    def set_mobility_model(self, int type):
        self._sim.set_mobility_model(type)

    def set_transient_enabled(self, bint enable):
        self._sim.set_transient_enabled(enable)

    def set_transient_dt(self, double dt):
        self._sim.set_transient_dt(dt)

    def set_transient_t_final(self, double t_final):
        self._sim.set_transient_t_final(t_final)

    def set_transient_lk_coupled(self, enable=True):
        """Override integration selection: True requires coupled LK; False
        retains split kinetics. With neither LK mode override set, eligible
        1-D dielectric, carrier and midpoint insulator/semiconductor chains use
        coupled material fields when all
        actual steps have unique monotone LK roots.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("coupled LK enable must be a boolean")
        self._sim.set_transient_lk_coupled(bool(enable))

    def set_transient_lk_material_field(self, enable=True):
        """Override automatic 1-D coupled-LK selection: True requires material
        fields; False retains legacy centered fields. With no override, eligible
        1-D dielectric and carrier chains select material fields on each run.
        Explicit True also supports structured 2-D/3-D material fields.
        This includes carrier transport, generation and SRH,
        retaining the full coupled equations and nonlocal LK susceptibility.
        Paired zero-mobility nodes require carriers <=1e-20 m^-3, zero
        generation and disabled SRH (lifetimes >=1e90 s). Material interfaces
        lie at node midpoints, with full node storage/source volumes.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("material-field LK enable must be a boolean")
        self._sim.set_transient_lk_material_field(bool(enable))

    def set_transient_lk_zero_d_faces(self, faces=""):
        """Declare cell-centred natural faces for multidimensional material LK.

        Unique xXyYzZ characters select lower/upper Cartesian faces. Each face
        lies half the adjacent edge beyond its endpoint and has D.n=0. LK uses
        the complete support, including exterior E=-P/eps; Poisson already
        omits exterior D flux. Use only for whole insulating faces, with
        contacts on other face normals. Empty string restores legacy support.
        This does not clip cells or define partial contacts. Requires coupled
        material-field LK on a 2-D/3-D grid. Coordinates must match this domain.
        """
        if not isinstance(faces, str):
            raise ValueError("zero-D faces must be a string")
        if any(c not in 'xXyYzZ' for c in faces) or len(set(faces)) != len(faces):
            raise ValueError("zero-D faces must be unique characters from xXyYzZ")
        self._sim.set_transient_lk_zero_d_faces(faces.encode('ascii'))

    def set_transient_lk_substepping(self, enable=True, safety=0.5):
        """Limit actual coupled LK steps to safety*gamma/abs(alpha) for alpha<0.

        Every accepted substep is returned; this is a monotonicity bound,
        not an error estimator. Requires coupled LK when solving.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("LK substepping enable must be a boolean")
        value = np.asarray(safety)
        if (value.shape != () or value.dtype.kind not in "iuf"
                or not np.isfinite(value) or not 0. < float(safety) < 1.):
            raise ValueError("LK substepping safety must be a finite real scalar in (0, 1)")
        self._sim.set_transient_lk_substepping(bool(enable), float(safety))

    def set_transient_lk_error_control(self, enable=True, rtol=1e-3, atol=1e-6,
                                       min_dt=1e-15, max_reject=20):
        """Control local P error with one BE step versus two accepted half steps.

        atol is in C/m2. Requires coupled LK substepping. No extrapolation;
        rejected trials consume no physical dwell. This does not bound global
        error or directly control phi/carriers. min_dt bounds retry proposals;
        voltage knots/final time can force shorter accepted intervals.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("LK error control enable must be a boolean")
        for name, scalar in (("rtol", rtol), ("atol", atol), ("min_dt", min_dt)):
            value = np.asarray(scalar)
            if (value.shape != () or value.dtype.kind not in "iuf"
                    or not np.isfinite(value) or not np.isfinite(float(scalar))
                    or float(scalar) <= 0. or (name == "rtol" and float(scalar) >= 1.)):
                raise ValueError("LK error control requires 0<rtol<1, positive real atol and min_dt")
        if (isinstance(max_reject, (bool, np.bool_))
                or not isinstance(max_reject, (int, np.integer))
                or not 0 <= max_reject <= np.iinfo(np.uintp).max):
            raise ValueError("LK error control max_reject must be a nonnegative integer")
        self._sim.set_transient_lk_error_control(bool(enable), float(rtol), float(atol),
            float(min_dt), int(max_reject))

    def set_transient_lk_electrical_error_control(self, enable=True, phi_atol=1e-6,
                                                carrier_rtol=1e-3, carrier_atol=1e10):
        """Also constrain local phi/n/p estimates in coupled LK step doubling.

        phi_atol is in V; carrier_atol is in m^-3. Requires LK P error control.
        All four fields share acceptance, retry limits and transactional rollback.
        This local estimator does not bound the global trajectory error.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("LK electrical error control enable must be a boolean")
        for name, scalar in (("phi_atol", phi_atol), ("carrier_rtol", carrier_rtol),
                             ("carrier_atol", carrier_atol)):
            value = np.asarray(scalar)
            if (value.shape != () or value.dtype.kind not in "iuf"
                    or not np.isfinite(value) or not np.isfinite(float(scalar))
                    or float(scalar) <= 0. or (name == "carrier_rtol" and float(scalar) >= 1.)):
                raise ValueError("LK electrical error control requires positive real atol and 0<carrier_rtol<1")
        self._sim.set_transient_lk_electrical_error_control(bool(enable), float(phi_atol),
            float(carrier_rtol), float(carrier_atol))

    def set_transient_electrical_error_control(self, enable=True, phi_atol=1e-6,
            carrier_rtol=1e-3, carrier_atol=1e10, min_dt=1e-15, max_reject=20):
        """Local BE step-doubling control for classical coupled phi/n/p.

        Requires no FE/LK controls or frozen equations. phi_atol is in V and
        carrier_atol in m^-3. Rejected groups roll back; accepted half steps
        keep their physical clocks/ledgers. This does not bound global error.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("electrical error control enable must be a boolean")
        for name, scalar in (("phi_atol", phi_atol), ("carrier_rtol", carrier_rtol),
                             ("carrier_atol", carrier_atol), ("min_dt", min_dt)):
            value = np.asarray(scalar)
            if (value.shape != () or value.dtype.kind not in "iuf"
                    or not np.isfinite(value) or not np.isfinite(float(scalar))
                    or float(scalar) <= 0. or (name == "carrier_rtol" and float(scalar) >= 1.)):
                raise ValueError("electrical error control requires positive real atol/min_dt and 0<carrier_rtol<1")
        if (isinstance(max_reject, (bool, np.bool_))
                or not isinstance(max_reject, (int, np.integer))
                or not 0 <= max_reject <= np.iinfo(np.uintp).max):
            raise ValueError("electrical error control max_reject must be a nonnegative integer")
        self._sim.set_transient_electrical_error_control(bool(enable), float(phi_atol),
            float(carrier_rtol), float(carrier_atol), float(min_dt), int(max_reject))

    def set_transient_nls_error_control(self, enable=True, rtol=1e-3, atol=1e-8,
            phi_atol=1e-6, carrier_rtol=1e-3, carrier_atol=1e10, min_dt=1e-15, max_reject=20):
        """Joint local P/phi/n/p control for split volume-ensemble NLS.

        atol is in C/m^2, phi_atol in V, carrier_atol in m^-3. Requires NLS
        FE with no other controllers or frozen equations. Compares one split
        step with two half steps, including field-predictor splitting error.
        Accepted states retain physical intervals; this is not full coupling
        or a global error bound. Rate-independent Preisach is unsupported.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("NLS error control enable must be a boolean")
        for name, scalar in (("rtol", rtol), ("atol", atol), ("phi_atol", phi_atol),
                ("carrier_rtol", carrier_rtol), ("carrier_atol", carrier_atol), ("min_dt", min_dt)):
            value = np.asarray(scalar)
            if (value.shape != () or value.dtype.kind not in "iuf"
                    or not np.isfinite(value) or not np.isfinite(float(scalar))
                    or float(scalar) <= 0. or (name in ("rtol", "carrier_rtol") and float(scalar) >= 1.)):
                raise ValueError("NLS error control requires positive real budgets and relative budgets in (0,1)")
        if (isinstance(max_reject, (bool, np.bool_)) or not isinstance(max_reject, (int, np.integer))
                or not 0 <= max_reject <= np.iinfo(np.uintp).max):
            raise ValueError("NLS error control max_reject must be a nonnegative integer")
        self._sim.set_transient_nls_error_control(bool(enable), float(rtol), float(atol),
            float(phi_atol), float(carrier_rtol), float(carrier_atol), float(min_dt), int(max_reject))

    def set_transient_nls_event_control(self, enable=True, half_width=1e-18):
        """Opt in to two-sided NLS field-reversal sampling; disabled initially.

        half_width is a positive finite physical interval in seconds, also
        when disabling. solve_transient requires float128 fixed split NLS,
        full FE support, complete polar contact planes, driven waveforms,
        zero depolarization, unfrozen equations and no other time controllers.
        The interval must be smaller than dt/8 and resolve the native clock.
        User knots clip event steps. Python inputs and snapshots use float64;
        rounded states do not preserve a native quad-precision checkpoint.
        This samples reversals; it does not bound the global trajectory error.
        """
        if not isinstance(enable, (bool, np.bool_)):
            raise ValueError("NLS event control enable must be a boolean")
        value = np.asarray(half_width)
        if value.shape != () or value.dtype.kind not in "iuf":
            raise ValueError("NLS event half width must be a positive finite real scalar")
        width = float(half_width)
        if not np.isfinite(value) or not np.isfinite(width) or width <= 0.:
            raise ValueError("NLS event half width must be a positive finite real scalar")
        self._sim.set_transient_nls_event_control(bool(enable), width)

    def set_transient_voltage_waveforms(self, times_s, dict offsets_V):
        """Piecewise-linear offsets to configured potential contact nodes.

        Times start at zero; every knot becomes an accepted step endpoint.
        Profiles apply only within solve_transient and leave DC contacts intact.
        """
        cdef vector[double] clock
        cdef map[size_t, vector[double]] profiles
        cdef np.ndarray[np.float64_t, ndim=1, mode="c"] values
        arr = np.asarray(times_s)
        if arr.ndim != 1 or arr.dtype.kind not in "iuf":
            raise ValueError("waveform times must be a real one-dimensional array")
        values = np.ascontiguousarray(arr, dtype=np.float64)
        if not np.all(np.isfinite(values)):
            raise ValueError("waveform times must be finite")
        clock = np_to_vec(values)
        for node, profile in offsets_V.items():
            if (isinstance(node, (bool, np.bool_)) or
                    not isinstance(node, (int, np.integer)) or node < 0 or node >= self._npts):
                raise ValueError("waveform node must be a valid integer node index")
            arr = np.asarray(profile)
            if arr.ndim != 1 or arr.dtype.kind not in "iuf":
                raise ValueError("waveform offsets must be real one-dimensional arrays")
            values = np.ascontiguousarray(arr, dtype=np.float64)
            if not np.all(np.isfinite(values)):
                raise ValueError("waveform offsets must be finite")
            profiles[<size_t>node] = np_to_vec(values)
        self._sim.set_transient_voltage_waveforms(clock, profiles)

    def clear_transient_voltage_waveforms(self):
        self._sim.clear_transient_voltage_waveforms()

    def set_ferroelectric_gamma(self, double gamma):
        self._sim.set_ferroelectric_gamma(gamma)

    def set_ferroelectric_history(self, polarization):
        """Install an owned finite (N,3) cubic-LK state without solving."""
        raw = np.asarray(polarization)
        if np.iscomplexobj(raw) or raw.ndim != 2 or raw.shape != (self._sim.npts(), 3):
            raise ValueError("polarization history must have shape (N,3)")
        a = np.ascontiguousarray(raw, dtype=np.float64).ravel()
        self._sim.set_ferroelectric_history(np_to_vec(a))

    def get_ferroelectric_history(self):
        """Read installed/accepted P without an implicit solve or history advance."""
        cdef vector[double] p = self._sim.get_ferroelectric_history()
        return np.array(p, dtype=np.float64).reshape(-1, 3)

    def set_transient_start_time(self, double time):
        """Set the absolute initial clock; voltage waveforms retain their clock."""
        self._sim.set_transient_start_time(time)

    def get_ferroelectric_ensemble_history(self):
        """Owned exported compact-model memory, including all turning points."""
        return dict(schema='compact_FE_ensemble_v1',
            parameters=np.array(self._sim.get_ferroelectric_ensemble_parameters(),dtype=np.float64),
            mask=self.get_ferroelectric_mask(),polarization=self.get_ferroelectric_history(),
            play=np.array(self._sim.get_ferroelectric_play_history(),dtype=np.float64))

    def set_ferroelectric_ensemble_history(self, state):
        """Atomic same-model memory import; never advances dwell or solves."""
        current=self.get_ferroelectric_ensemble_history()
        if (not isinstance(state,dict) or state.get('schema')!='compact_FE_ensemble_v1'
                or not np.array_equal(state.get('parameters'),current['parameters'])
                or not np.array_equal(state.get('mask'),current['mask'])):
            raise ValueError('ensemble model, coefficients or material mask differ')
        raw=np.asarray(state.get('polarization'));memory=np.asarray(state.get('play'))
        if (raw.dtype.kind not in 'fiu' or raw.shape!=(self._sim.npts(),3)
                or memory.dtype.kind not in 'fiu' or memory.ndim!=1):
            raise ValueError('invalid ensemble state array shapes/types')
        self._sim.set_ferroelectric_ensemble_history(np_to_vec(np.ascontiguousarray(raw,dtype=np.float64).ravel()),
            np_to_vec(np.ascontiguousarray(memory,dtype=np.float64)))

    def get_ferroelectric_mask(self):
        return np.array(self._sim.get_ferroelectric_mask(), dtype=bool)

    def get_ferroelectric_lk_parameters(self):
        return np.array(self._sim.get_ferroelectric_lk_parameters(), dtype=np.float64)

    def get_permittivity(self):
        return np.array(self._sim.get_permittivity(), dtype=np.float64)

    def solve(self, *, audit_newton=False):
        """Solve; optionally reassemble supported classical Newton SG rows.

        The optional audit scores the returned state, including failed-state
        rollback. Its SG row gate is separate from Newton's stopping metric.
        It does not establish device energy or experimental validity.
        """
        if not isinstance(audit_newton, (bool, np.bool_)):
            raise ValueError('audit_newton must be a boolean')
        if self._sim.three_temperature_enabled() or self._sim.isolated_relaxation_enabled() or self._sim.energy_coordinate_enabled():
            raise RuntimeError('legacy solve unavailable in explicit-cell three-temperature mode')
        self._sim.reset_solved()
        if audit_newton:
            self._sim.audit_steady_equations()
        return self._export_result()

    def _export_result(self):
        if self._sim.three_temperature_enabled() or self._sim.isolated_relaxation_enabled() or self._sim.energy_coordinate_enabled():
            raise RuntimeError('legacy result layout unavailable in explicit-cell three-temperature mode')
        cdef vector[double] phi = self._sim.solve_potential()
        cdef vector[double] n   = self._sim.solve_electrons()
        cdef vector[double] p   = self._sim.solve_holes()
        cdef vector[double] Ex  = self._sim.solve_Ex()
        cdef vector[double] Ey  = self._sim.solve_Ey()
        cdef vector[double] Ez  = self._sim.solve_Ez()
        cdef vector[double] T   = self._sim.solve_temperature()
        cdef SteadyThermalLedgerDouble heat = self._sim.solve_thermal_ledger()
        cdef vector[double] Qn  = self._sim.solve_Qn()
        cdef vector[double] Qp  = self._sim.solve_Qp()
        cdef vector[double] Jn_x = self._sim.solve_Jn_x()
        cdef vector[double] Jn_y = self._sim.solve_Jn_y()
        cdef vector[double] Jn_z = self._sim.solve_Jn_z()
        cdef vector[double] Jp_x = self._sim.solve_Jp_x()
        cdef vector[double] Jp_y = self._sim.solve_Jp_y()
        cdef vector[double] Jp_z = self._sim.solve_Jp_z()
        cdef vector[double] Jleak_x = self._sim.solve_Jleak_x()
        cdef vector[double] Jleak_y = self._sim.solve_Jleak_y()
        cdef vector[double] Jleak_z = self._sim.solve_Jleak_z()
        cdef vector[double] G_btbt = self._sim.solve_G_btbt()
        cdef vector[double] G_ii = self._sim.solve_G_ii()
        cdef vector[double] P   = self._sim.fe_polarization()
        cdef cbool conv = self._sim.solve_converged()
        cdef size_t iters = self._sim.solve_iterations()
        cdef double poisson_residual = self._sim.solve_poisson_residual()
        cdef double quantum_residual = self._sim.solve_quantum_residual()
        cdef vector[double] equation_rows = self._sim.solve_steady_gummel_audit()
        equation_audit = dict(available=False, scope='classical_Gummel_final_returned_state',
            unavailable_reason=self._sim.solve_steady_gummel_audit_status().decode('utf-8'),
            poisson_scaled_linf=None, electron_backward_error_linf=None,
            hole_backward_error_linf=None, equation_gate=None, requested_update_tolerance=None,
            equations_pass=None, complete_device_energy=False, physical_validated=False)
        if self._sim.solve_steady_gummel_audit_status() == b'available_newton_sg':
            equation_audit['scope'] = 'classical_Newton_SG_final_returned_state'
        if self._sim.solve_steady_gummel_audit_status() == b'available_quantum_newton_sg':
            equation_audit['scope'] = 'quantum_Newton_SG_final_returned_state'
        if equation_rows.size() == 6:
            equation_audit.update(available=True, poisson_scaled_linf=equation_rows[0],
                electron_backward_error_linf=equation_rows[1], hole_backward_error_linf=equation_rows[2],
                equation_gate=equation_rows[3], requested_update_tolerance=equation_rows[4],
                unavailable_reason=None, equations_pass=bool(equation_rows[5]))
        cdef vector[NonlinearSolveHistoryDouble] stages = self._sim.solve_nonlinear_history()
        cdef size_t stage_index
        diagnostics = []
        for stage_index in range(stages.size()):
            solver = stages[stage_index].solver.decode('utf-8')
            columns = (('relative_phi_update', 'relative_n_update', 'relative_p_update',
                        'poisson_relative_l2', 'poisson_scaled_linf')
                       if solver == 'gummel' else
                       ('relative_block_max', 'raw_phi_l2', 'raw_n_l2', 'raw_p_l2', 'scaled_merit_rms', 'equilibrated_linf'))
            samples = np.array(stages[stage_index].samples, dtype=np.float64).reshape(-1, len(columns))
            entry = dict(solver=solver, converged=bool(stages[stage_index].converged),
                         final_poisson_residual=stages[stage_index].final_poisson_residual,
                         poisson_residual_metric='physical_scaled_linf',
                         sample_scope=('completed_outer_updates_before_polish' if solver == 'gummel'
                                       else 'outer_base_states_before_line_search'))
            for column_index, column in enumerate(columns):
                entry[column] = samples[:, column_index].copy()
            diagnostics.append(entry)

        cdef size_t N = self._npts
        # fe_polarization() is empty when ferroelectric is disabled (never
        # allocated); expose a (N,3) zeros array in that case so "P" always has
        # the documented vector shape.
        cdef np.ndarray P_arr = (np.array(P, dtype=np.float64).reshape(N, 3)
                                 if P.size() == 3 * N
                                 else np.zeros((N, 3), dtype=np.float64))
        return {
            "phi": np.array(phi, dtype=np.float64),
            "n": np.array(n, dtype=np.float64),
            "p": np.array(p, dtype=np.float64),
            "Ex": np.array(Ex, dtype=np.float64),
            "Ey": np.array(Ey, dtype=np.float64),
            "Ez": np.array(Ez, dtype=np.float64),
            "temperature": np.array(T, dtype=np.float64),
            "thermal_ledger": dict(
                available=bool(heat.available), linear_solve_converged=bool(heat.linear_solve_converged),
                current_projected=bool(heat.current_projected), projected_Jx_A_m2=heat.projected_Jx,
                source_power_W=heat.source_power, outward_heat_W=heat.outward_heat,
                balance_residual_W=heat.balance_residual, max_cell_residual_W=heat.max_cell_residual,
                node_volumes_m3=np.array(heat.node_volumes,dtype=np.float64),
                power_density_W_m3=np.array(heat.power_density,dtype=np.float64),
                flux_x_W=np.array(heat.flux_x,dtype=np.float64),
                flux_y_W=np.array(heat.flux_y,dtype=np.float64),
                flux_z_W=np.array(heat.flux_z,dtype=np.float64),
                bath_heat_W=np.array(heat.bath_heat,dtype=np.float64),
                bath_nodes=np.array(heat.bath_nodes,dtype=np.int64),
                bath_temperatures_K=np.array(heat.bath_temperatures,dtype=np.float64),
                mobility_feedback=bool(heat.mobility_feedback), feedback_converged=bool(heat.feedback_converged),
                feedback_iterations=heat.feedback_iterations, feedback_residual_K=heat.feedback_residual,
                feedback_tolerance_K=heat.feedback_tolerance, transient_storage=bool(heat.transient_storage),
                dt_s=heat.dt, storage_power_W=heat.storage_power,
                carrier_reference_temperature_K=heat.carrier_temperature, carrier_reference_VT_V=heat.carrier_VT,
                mobility_temperature_K=np.array(heat.mobility_temperature,dtype=np.float64),
                mobility_n_m2_V_s=np.array(heat.mobility_n,dtype=np.float64),
                mobility_p_m2_V_s=np.array(heat.mobility_p,dtype=np.float64),
                previous_temperature_K=np.array(heat.previous_temperature,dtype=np.float64),
                heat_capacity_J_m3_K=np.array(heat.heat_capacity,dtype=np.float64),
                node_storage_power_W=np.array(heat.node_storage_power,dtype=np.float64),
                scope=('BE_lattice_absolute_JE_quasistatic_DD' if heat.transient_storage
                       else 'steady_lattice_absolute_JE_with_optional_1d_projection'),
                complete_device_energy=False, physical_validated=False),
            "Qn": np.array(Qn, dtype=np.float64),
            "Qp": np.array(Qp, dtype=np.float64),
            "Jn_x": np.array(Jn_x, dtype=np.float64),
            "Jn_y": np.array(Jn_y, dtype=np.float64),
            "Jn_z": np.array(Jn_z, dtype=np.float64),
            "Jp_x": np.array(Jp_x, dtype=np.float64),
            "Jp_y": np.array(Jp_y, dtype=np.float64),
            "Jp_z": np.array(Jp_z, dtype=np.float64),
            "Jleak_x": np.array(Jleak_x, dtype=np.float64),
            "Jleak_y": np.array(Jleak_y, dtype=np.float64),
            "Jleak_z": np.array(Jleak_z, dtype=np.float64),
            "G_btbt": np.array(G_btbt, dtype=np.float64),
            "G_ii": np.array(G_ii, dtype=np.float64),
            "P": P_arr,
            "converged": bool(conv),
            "iterations": int(iters),
            "poisson_residual": poisson_residual,
            "poisson_residual_metric": "physical_scaled_linf",
            "quantum_residual": quantum_residual,
            "steady_equation_audit": equation_audit,
            "nonlinear_history_enabled": bool(self._sim.solve_nonlinear_history_enabled()),
            "nonlinear_history": diagnostics,
        }

    def create_nls_continuation(self):
        """Create an unstarted, owner-bound native precision continuation."""
        return PyNlsTransientContinuation(self)

    def get_transient_attempt_history(self):
        """Return owned diagnostics for the latest native transient run.

        Enabled by set_nonlinear_history_enabled(). Groups survive rollback;
        retained trials alone contribute to the accepted timeline. Residuals
        describe the named solver and sample_scope; no line-search/linear trials.
        Empty before a run, when recording was disabled, or on preflight failure.
        Unavailable error ratios are None, including fixed-step runs.
        """
        cdef vector[TransientAttemptHistoryDouble] groups = self._sim.transient_attempt_history()
        return _export_transient_trace(groups)

    def solve_transient(self):
        """Return t=0 plus accepted BE steps and any final rejected attempt.

        Time is local to this run. Rejected attempts have valid=False, dt_s=0
        and retain the accepted time/state; attempted_time_s gives the rejected
        endpoint. Classical transport couples Poisson and both carriers by
        default; FE adds an operator-split update before the electrical solve.
        BE carrier storage, pair sources and terminal fluxes share full
        node-centred volumes in every orientation, including blocked faces.
        This geometry does not model cut cells or select an LK field policy.
        Complete equipotential electrodes can export conduction/displacement/
        total current on mixed grids. Mobile carrier reservoirs must match
        those electrodes; blocked rows must preserve zero net charge across
        both ends of an accepted interval and have no active pair source.
        """
        cdef vector[TransientResultDouble] history = self._sim.solve_transient_results()
        return _export_transient_results(history)

    @property
    def nx(self): return self._nx
    @property
    def ny(self): return self._ny
    @property
    def nz(self): return self._nz
    @property
    def npts(self): return self._npts


cdef class PyNlsTransientContinuation:
    """Persistent split-NLS accepted state. The originating simulator stays alive.

    advance() performs native work only. history and trace export fresh float64
    copies; export failure cannot discard the retained native accepted state.
    Configuration changes are rejected by the native continuation preflight.
    This object is process-local and cannot be copied or serialized.
    """
    cdef NlsTransientContinuationDouble* _state
    cdef PyDeviceSimulator _owner

    def __cinit__(self, PyDeviceSimulator owner not None):
        self._owner = owner
        self._state = new NlsTransientContinuationDouble()

    def __dealloc__(self):
        if self._state != NULL:
            del self._state

    def advance(self, max_retries=1):
        """Run to completion or a bounded stop; return the status name.

        max_retries is an extra resource/solver retry budget per group per call.
        Accuracy rejection limits remain those configured on the simulator.
        The GIL stays held, preventing concurrent Python mutation of this owner.
        """
        if isinstance(max_retries, (bool, np.bool_)) or not isinstance(max_retries, (int, np.integer)) or max_retries < 0:
            raise ValueError('max_retries must be a nonnegative integer')
        cdef size_t budget = max_retries
        self._owner._sim.advance_transient_nls(self._state[0], budget)
        return self.status

    @property
    def history(self):
        return _export_transient_results(self._state.history())

    @property
    def trace(self):
        return _export_transient_trace(self._state.trace())

    @property
    def status(self):
        return ('not_started', 'complete', 'allocation_failure', 'solver_failure',
                'unexpected_failure', 'max_reject', 'minimum_step',
                'time_resolution', 'unrepresentable_estimate')[self._state.status()]

    @property
    def diagnostics(self):
        return dict(status=self.status, allocation_failures=self._state.allocation_failures(),
                    solver_failures=self._state.solver_failures(), retries=self._state.retries(),
                    suggested_dt_s=self._state.suggested_dt(),
                    accuracy_rejections=self._state.accuracy_rejections())

    def __copy__(self):
        raise TypeError('native NLS continuations cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('native NLS continuations cannot be copied')

    def __reduce__(self):
        raise TypeError('native NLS continuations cannot be serialized')
