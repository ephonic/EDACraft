# distutils: language = c++
# cython: language_level = 3

from libcpp.vector cimport vector
from libcpp.map cimport map
from libcpp cimport bool as cbool
from libc.stddef cimport size_t
import numpy as np
cimport numpy as np

np.import_array()


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
    cdef cppclass DeviceSimulatorDouble:
        DeviceSimulatorDouble(size_t nx, size_t ny, size_t nz, double dx, double dy, double dz)
        void set_permittivity(const vector[double]& eps)
        void set_edge_permittivity(const vector[double]& x_plus,
                                   const vector[double]& x_minus,
                                   const vector[double]& y_plus,
                                   const vector[double]& y_minus,
                                   const vector[double]& z_plus,
                                   const vector[double]& z_minus)
        void set_mobility(const vector[double]& mu_n, const vector[double]& mu_p)
        void set_doping(const vector[double]& Nd_minus_Na)
        void set_optical_generation(const vector[double]& G_opt)
        void set_recombination(const vector[double]& tau_n, const vector[double]& tau_p)
        void set_thermal_voltage(double VT)
        void set_effective_dos(const vector[double]& Nc, const vector[double]& Nv)
        void set_bandgap(const vector[double]& Eg)
        void set_dirichlet_potential(const map[size_t, double]& bc)
        void set_electron_bc(const map[size_t, double]& bc)
        void set_hole_bc(const map[size_t, double]& bc)
        void set_quantum_enabled(cbool enable)
        void set_gummel_max_iter(size_t max_iter)
        void set_tolerance(double tol)
        void set_poisson_solver_type(int type)
        void set_continuity_solver_type(int type)
        void set_use_newton(cbool enable)
        void set_newton_freeze_phi(cbool enable)
        void set_newton_freeze_n(cbool enable)
        void set_newton_freeze_p(cbool enable)
        void set_newton_damping(double damping)
        void set_newton_min_damping(double min_damping)
        void set_newton_use_line_search(cbool enable)
        void set_newton_line_search_max(size_t max)
        void set_newton_use_log_damping(cbool enable)
        void set_newton_use_log_space(cbool enable)
        void set_newton_jacobian_reuse_threshold(double threshold)
        void set_thermal_coupling_enabled(cbool enable)
        void set_thermal_conductivity(const vector[double]& kappa)
        void set_ambient_temperature(double T_ambient)
        void set_thermal_dirichlet(const map[size_t, double]& bc)
        void set_btbt_enabled(cbool enable)
        void set_btbt_params(double A, double B, int D)
        void set_btbt_use_nonlocal(cbool enable)
        void set_ii_enabled(cbool enable)
        void set_ii_params(double A_n, double B_n, double A_p, double B_p)
        void set_breakdown_enabled(cbool enable)
        void set_breakdown_params(const vector[signed char]& bd_mask,
                                  const vector[double]& E_bd, double sigma_bd)
        vector[signed char] breakdown_state()
        void set_ferroelectric_enabled(cbool enable)
        void set_ferroelectric_params(const vector[signed char]& fe_mask, double alpha, double beta)
        void set_ferroelectric_model(int model)
        void set_ferroelectric_preisach(double ps, double ec, double escale)
        void set_ferroelectric_builtin_field(double E_bi)
        void set_ferroelectric_nls(double tau0, double E0, double dt)
        void set_leakage(const vector[signed char]& mask,
                         double C_pf, double B_pf, double phi_t,
                         double C_fn, double B_fn, double phi_b,
                         double E_floor, double sigma_cap)
        void set_leakage_enabled(cbool enable)
        void set_interface_traps(const vector[signed char]& mask, double D_it, double E_t)
        void set_oxide_traps(const vector[double]& Q_ot)
        vector[double] fe_polarization()

        void set_initial_guess(const vector[double]& phi,
                               const vector[double]& n,
                               const vector[double]& p)
        void clear_initial_guess()

        void set_temperature(double T)
        void set_statistics_type(int type)
        void set_mobility_model(int type)

        void set_transient_enabled(cbool enable)
        void set_transient_dt(double dt)
        void set_transient_t_final(double t_final)
        void set_ferroelectric_gamma(double gamma)

        vector[double] solve_potential()
        vector[double] solve_electrons()
        vector[double] solve_holes()
        vector[double] solve_Ex()
        vector[double] solve_Ey()
        vector[double] solve_Ez()
        vector[double] solve_temperature()
        vector[double] solve_Jn_x()
        vector[double] solve_Jn_y()
        vector[double] solve_Jn_z()
        vector[double] solve_Jp_x()
        vector[double] solve_Jp_y()
        vector[double] solve_Jp_z()
        cbool solve_converged()

        void reset_solved()
        size_t solve_iterations()

        vector[vector[double]] solve_transient_phi()
        vector[vector[double]] solve_transient_n()
        vector[vector[double]] solve_transient_p()
        vector[cbool] solve_transient_converged()

        size_t nx()
        size_t ny()
        size_t nz()
        size_t npts()


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

    def set_optical_generation(self, np.ndarray[np.float64_t, ndim=1, mode="c"] G_opt not None):
        self._sim.set_optical_generation(np_to_vec(G_opt))

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

    def set_gummel_max_iter(self, size_t max_iter):
        self._sim.set_gummel_max_iter(max_iter)

    def set_tolerance(self, double tol):
        self._sim.set_tolerance(tol)

    def set_poisson_solver_type(self, int type):
        self._sim.set_poisson_solver_type(type)

    def set_continuity_solver_type(self, int type):
        self._sim.set_continuity_solver_type(type)

    def set_use_newton(self, bint enable):
        self._sim.set_use_newton(enable)

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

    def set_newton_jacobian_reuse_threshold(self, double threshold):
        self._sim.set_newton_jacobian_reuse_threshold(threshold)

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

    def set_btbt_params(self, double A, double B, int D):
        self._sim.set_btbt_params(A, B, D)

    def set_btbt_use_nonlocal(self, bint enable):
        self._sim.set_btbt_use_nonlocal(enable)

    def set_ii_enabled(self, bint enable):
        self._sim.set_ii_enabled(enable)

    def set_ii_params(self, double A_n, double B_n, double A_p, double B_p):
        self._sim.set_ii_params(A_n, B_n, A_p, B_p)

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

    def set_ferroelectric_nls(self, double tau0, double E0, double dt):
        # P3: NLS Merz-law tau(E)=tau0*exp(E0/|E|); dt = dwell time per step.
        self._sim.set_ferroelectric_nls(tau0, E0, dt)

    def set_leakage(self, np.ndarray[np.int8_t, ndim=1, mode="c"] mask not None,
                    double C_pf, double B_pf, double phi_t,
                    double C_fn, double B_fn, double phi_b,
                    double E_floor, double sigma_cap):
        # P2.2: Poole-Frenkel / Fowler-Nordheim leakage current.
        self._sim.set_leakage(np_to_vec_char(mask),
                              C_pf, B_pf, phi_t, C_fn, B_fn, phi_b, E_floor, sigma_cap)

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

    def set_ferroelectric_gamma(self, double gamma):
        self._sim.set_ferroelectric_gamma(gamma)

    def solve(self):
        """Run simulation and return dict of numpy arrays."""
        self._sim.reset_solved()
        cdef vector[double] phi = self._sim.solve_potential()
        cdef vector[double] n   = self._sim.solve_electrons()
        cdef vector[double] p   = self._sim.solve_holes()
        cdef vector[double] Ex  = self._sim.solve_Ex()
        cdef vector[double] Ey  = self._sim.solve_Ey()
        cdef vector[double] Ez  = self._sim.solve_Ez()
        cdef vector[double] T   = self._sim.solve_temperature()
        cdef vector[double] Jn_x = self._sim.solve_Jn_x()
        cdef vector[double] Jn_y = self._sim.solve_Jn_y()
        cdef vector[double] Jn_z = self._sim.solve_Jn_z()
        cdef vector[double] Jp_x = self._sim.solve_Jp_x()
        cdef vector[double] Jp_y = self._sim.solve_Jp_y()
        cdef vector[double] Jp_z = self._sim.solve_Jp_z()
        cdef vector[double] P   = self._sim.fe_polarization()
        cdef cbool conv = self._sim.solve_converged()
        cdef size_t iters = self._sim.solve_iterations()

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
            "Jn_x": np.array(Jn_x, dtype=np.float64),
            "Jn_y": np.array(Jn_y, dtype=np.float64),
            "Jn_z": np.array(Jn_z, dtype=np.float64),
            "Jp_x": np.array(Jp_x, dtype=np.float64),
            "Jp_y": np.array(Jp_y, dtype=np.float64),
            "Jp_z": np.array(Jp_z, dtype=np.float64),
            "P": P_arr,
            "converged": bool(conv),
            "iterations": int(iters),
        }

    def solve_transient(self):
        """Run transient simulation and return list of result dicts."""
        cdef vector[vector[double]] phi_history = self._sim.solve_transient_phi()
        cdef vector[vector[double]] n_history = self._sim.solve_transient_n()
        cdef vector[vector[double]] p_history = self._sim.solve_transient_p()
        cdef vector[cbool] conv_history = self._sim.solve_transient_converged()

        cdef size_t n_steps = phi_history.size()
        results = []
        for i in range(n_steps):
            results.append({
                "phi": np.array(phi_history[i], dtype=np.float64),
                "n": np.array(n_history[i], dtype=np.float64),
                "p": np.array(p_history[i], dtype=np.float64),
                "converged": bool(conv_history[i]),
            })
        return results

    @property
    def nx(self): return self._nx
    @property
    def ny(self): return self._ny
    @property
    def nz(self): return self._nz
    @property
    def npts(self): return self._npts
