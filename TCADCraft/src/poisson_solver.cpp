#include "poisson_solver.h"
#include "structured_field.h"
#include "polarization_flux.h"
#include <algorithm>
#include <iostream>

namespace tcad {

PoissonSolver::PoissonSolver(const Grid3D& grid)
    : g_(grid), eps_(grid.npts(), EPS0 * TCAD_CONST(11.7)), // Default: Silicon
      Nd_minus_Na_(grid.npts(), TCAD_CONST(0.0)),
      charge_volume_fraction_(grid.npts(), TCAD_CONST(1.0)),
      is_dirichlet_(grid.npts(), 0),
      solver_(LinearSolver(LinearSolver::default_poisson_options())) {}

void PoissonSolver::set_permittivity(const std::vector<real_t>& eps) {
    if (eps.size() != g_.npts()) throw std::invalid_argument("Permittivity size mismatch");
    for (real_t value : eps)
        if (!isfinite_q(value))
            throw std::invalid_argument("permittivity values must be finite");
    eps_ = eps;
}

void PoissonSolver::set_edge_permittivity(const std::vector<real_t>& x_plus,
                                          const std::vector<real_t>& x_minus,
                                          const std::vector<real_t>& y_plus,
                                          const std::vector<real_t>& y_minus,
                                          const std::vector<real_t>& z_plus,
                                          const std::vector<real_t>& z_minus) {
    const size_t N = g_.npts();
    if (!x_plus.empty() && x_plus.size() != N)
        throw std::invalid_argument("edge_eps_x_plus size mismatch");
    if (!x_minus.empty() && x_minus.size() != N)
        throw std::invalid_argument("edge_eps_x_minus size mismatch");
    if (!y_plus.empty() && y_plus.size() != N)
        throw std::invalid_argument("edge_eps_y_plus size mismatch");
    if (!y_minus.empty() && y_minus.size() != N)
        throw std::invalid_argument("edge_eps_y_minus size mismatch");
    if (!z_plus.empty() && z_plus.size() != N)
        throw std::invalid_argument("edge_eps_z_plus size mismatch");
    if (!z_minus.empty() && z_minus.size() != N)
        throw std::invalid_argument("edge_eps_z_minus size mismatch");
    for (const auto* values : {&x_plus, &x_minus, &y_plus, &y_minus,
                               &z_plus, &z_minus})
        for (real_t value : *values)
            if (!isfinite_q(value))
                throw std::invalid_argument("edge permittivity values must be finite");
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
}

void PoissonSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    if (Nd_minus_Na.size() != g_.npts()) throw std::invalid_argument("Doping size mismatch");
    for (real_t value : Nd_minus_Na)
        if (!isfinite_q(value)) throw std::invalid_argument("Doping must be finite");
    Nd_minus_Na_ = Nd_minus_Na;
}

void PoissonSolver::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("Charge volume fraction size mismatch");
    for (real_t value : fraction) {
        if (!isfinite_q(value) || value < TCAD_CONST(0.0) || value > TCAD_CONST(1.0))
            throw std::invalid_argument("Charge volume fraction must be in [0,1]");
    }
    charge_volume_fraction_ = fraction;
}

void PoissonSolver::set_solver_options(const SolverOptions& opt) {
    solver_ = LinearSolver(opt);
}

void PoissonSolver::set_dirichlet(const std::map<size_t, real_t>& bc) {
    for (const auto& [idx, val] : bc) {
        if (idx >= g_.npts()) throw std::out_of_range("Dirichlet index out of bounds");
    }
    std::vector<char> mask(g_.npts(), 0);
    for (const auto& [idx, val] : bc) {
        if (!isfinite_q(val)) throw std::invalid_argument("Dirichlet values must be finite");
        mask[idx] = true;
    }
    auto validated_bc = bc;
    dirichlet_bc_.swap(validated_bc);
    is_dirichlet_.swap(mask);
}

void PoissonSolver::set_neumann_faces(char face) {
    // Neumann BC means d(phi)/dn = 0, implemented by mirroring
    // This is a placeholder for future implementation
    // For now, zero-field Neumann is naturally handled by omitting boundary flux
}

real_t PoissonSolver::cx_plus(size_t idx) const {
    size_t i = idx % g_.nx;
    if (i + 1 >= g_.nx) return TCAD_CONST(0.0);
    real_t ec = g_.dx_edge(i) * g_.dx_cell(i);
    if (!edge_eps_x_plus_.empty() && edge_eps_x_plus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_x_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + 1];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx + 1] / eps_sum / ec;
}

real_t PoissonSolver::cx_minus(size_t idx) const {
    size_t i = idx % g_.nx;
    if (i == 0) return TCAD_CONST(0.0);
    real_t ec = g_.dx_edge(i-1) * g_.dx_cell(i);
    if (!edge_eps_x_minus_.empty() && edge_eps_x_minus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_x_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - 1];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx - 1] / eps_sum / ec;
}

real_t PoissonSolver::cy_plus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j + 1 >= g_.ny) return TCAD_CONST(0.0);
    real_t ec = g_.dy_edge(j) * g_.dy_cell(j);
    if (!edge_eps_y_plus_.empty() && edge_eps_y_plus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_y_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx + g_.nx] / eps_sum / ec;
}

real_t PoissonSolver::cy_minus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j == 0) return TCAD_CONST(0.0);
    real_t ec = g_.dy_edge(j-1) * g_.dy_cell(j);
    if (!edge_eps_y_minus_.empty() && edge_eps_y_minus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_y_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx - g_.nx] / eps_sum / ec;
}

real_t PoissonSolver::cz_plus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k + 1 >= g_.nz) return TCAD_CONST(0.0);
    real_t ec = g_.dz_edge(k) * g_.dz_cell(k);
    if (!edge_eps_z_plus_.empty() && edge_eps_z_plus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_z_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx * g_.ny];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx + g_.nx * g_.ny] / eps_sum / ec;
}

real_t PoissonSolver::cz_minus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k == 0) return TCAD_CONST(0.0);
    real_t ec = g_.dz_edge(k-1) * g_.dz_cell(k);
    if (!edge_eps_z_minus_.empty() && edge_eps_z_minus_[idx] > TCAD_CONST(0.0)) {
        return edge_eps_z_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx * g_.ny];
    if (eps_sum < EPSILON) return TCAD_CONST(0.0);
    return TCAD_CONST(2.0) * eps_[idx] * eps_[idx - g_.nx * g_.ny] / eps_sum / ec;
}

void PoissonSolver::assemble(const std::vector<real_t>& n, const std::vector<real_t>& p) {
    if (n.size() != g_.npts() || p.size() != g_.npts())
        throw std::invalid_argument("Carrier density size mismatch");

    A_ = SparseMatrix(g_.npts());
    rhs_.assign(g_.npts(), TCAD_CONST(0.0));

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_dirichlet_[idx]) {
                    A_.add_entry(idx, idx, TCAD_CONST(1.0));
                    rhs_[idx] = dirichlet_bc_.at(idx);
                    continue;
                }
                // Vacuum / outside device: zero permittivity -> freeze potential
                if (eps_[idx] < EPSILON) {
                    A_.add_entry(idx, idx, TCAD_CONST(1.0));
                    rhs_[idx] = TCAD_CONST(0.0);
                    continue;
                }

                real_t center = TCAD_CONST(0.0);
                real_t c;

                // x-direction
                c = cx_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + 1, c); center -= c; }
                c = cx_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - 1, c); center -= c; }

                // y-direction
                c = cy_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + g_.nx, c); center -= c; }
                c = cy_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - g_.nx, c); center -= c; }

                // z-direction
                c = cz_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + g_.nx * g_.ny, c); center -= c; }
                c = cz_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - g_.nx * g_.ny, c); center -= c; }

                A_.add_entry(idx, idx, center);
                const real_t charge_fraction = charge_volume_fraction_[idx];
                rhs_[idx] = -QE * charge_fraction *
                    (p[idx] - n[idx] + Nd_minus_Na_[idx]);

                // Ohmic contact: replace frozen n,p with Boltzmann n(phi_old).
                // At Ohmic nodes, n=NSD from continuity BC is physically wrong
                // when phi is gate-controlled (phi≈0V but n=NSD).  Using
                // n=ni*exp((phi_old-EFn)/VT) makes Poisson self-consistent:
                // the D term gives dn/dphi = n/VT, so phi can change freely.
                if (!ohmic_nodes_.empty() && ohmic_nodes_.count(idx)) {
                    real_t phi_old = leak_phi_.empty() ? TCAD_CONST(0.0) :
                        (idx < leak_phi_.size() ? leak_phi_[idx] : TCAD_CONST(0.0));
                    real_t EFn = (ohmic_EFn_.count(idx)) ? ohmic_EFn_.at(idx) : TCAD_CONST(0.0);
                    real_t EFp = (ohmic_EFp_.count(idx)) ? ohmic_EFp_.at(idx) : TCAD_CONST(0.0);
                    real_t arg_n = (phi_old - EFn) / VT_;
                    real_t arg_p = -(phi_old + EFp) / VT_;
                    if (arg_n > TCAD_CONST(50.0)) arg_n = TCAD_CONST(50.0);
                    if (arg_n < -TCAD_CONST(50.0)) arg_n = -TCAD_CONST(50.0);
                    if (arg_p > TCAD_CONST(50.0)) arg_p = TCAD_CONST(50.0);
                    if (arg_p < -TCAD_CONST(50.0)) arg_p = -TCAD_CONST(50.0);
                    real_t n_ohmic = ohmic_ni_ * exp_q(arg_n);
                    real_t p_ohmic = ohmic_ni_ * exp_q(arg_p);
                    rhs_[idx] = -QE * charge_fraction *
                        (p_ohmic - n_ohmic + Nd_minus_Na_[idx]);
                }

                // Stabilized-Gummel Boltzmann linearization (plan0728 §1.2):
                // the carrier charge rho(phi) is linearized about the
                // previous iterate (leak_field_):
                //   (A - D) phi_new = rhs - D phi_old,  D = (q/VT)(n+p).
                // The fixed point is unchanged (the D terms cancel), but
                // the iteration becomes semi-implicit: a node whose carrier
                // density overshoots (depletion-edge Boltzmann swing,
                // p ~ 1e6 x Na) gets a huge negative diagonal and freezes
                // instead of driving the next Poisson solve by ~26 V and
                // ratcheting into a limit cycle (observed on the Na=1e24 /
                // Nd=1e22 junction, oscillation localised at the junction
                // node; plain damping 1/256 and Anderson(1) both failed).
                if (boltzmann_lin_ && !leak_phi_.empty()) {
                    real_t D = charge_fraction * (QE / VT_) * (n[idx] + p[idx]);
                    A_.add_entry(idx, idx, -D);
                    rhs_[idx] -= D * leak_phi_[idx];
                }

                // Interface traps (Dit) + bulk oxide traps (P6).
                // Interface trap charge: Q_it = -q * D_it * dE * (f_t - 0.5),
                // where f_t = 1/(1+exp((E_t - E_F)/kT)) is the trap occupancy.
                // Energies are in eV throughout: E_F - E_i in eV equals the
                // local potential phi in volts NUMERICALLY (E [eV] = q*phi/e),
                // so f_t = 1/(1+exp((E_t[eV] - phi[V])/kT[eV])) with
                // kT = 0.02585 eV at 300 K. (P0-6 fix: the old code compared
                // E_t [eV] against phi/VT [dimensionless], a unit mismatch
                // that made the occupancy essentially 0/1-step-like.)
                // D_it is in cm^-2 eV^-1, converted: D_it * 1e4 [m^-2 eV^-1].
                // dE is the energy range over which traps are active (~1 eV).
                // The (f_t - 0.5) term gives zero charge at flatband (E_F=E_t).
                // The surface charge Q_it [C/m^2] is spread UNIFORMLY over the
                // trap layer thickness t_layer (extent of the mask along its
                // non-spanning axis = interface normal) so the total trapped charge
                // D_it * area * dE * (f_t-0.5) is invariant under mesh
                // refinement along the normal. (P0-6 fix: the old code divided
                // by g_.dx unconditionally, multiplying the total charge by the
                // node count whenever the mesh was refined.)
                // Bulk oxide traps Q_ot_ are a persistent charge [C/m^3].
                if (!trap_mask_.empty() && idx < trap_mask_.size() && trap_mask_[idx]) {
                    const real_t kT_eV = VT_;   // configured kT [eV] equals VT [V] numerically
                    // Use the cached phi from set_leakage_field (or set_trap_field).
                    real_t phi_val = TCAD_CONST(0.0);
                    if (!leak_phi_.empty() && idx < leak_phi_.size())
                        phi_val = leak_phi_[idx];
                    // E_F - E_i [eV] == phi [V] numerically (see comment above).
                    real_t arg = (trap_E_t_ - phi_val) / kT_eV;
                    real_t f_t = TCAD_CONST(1.0) / (TCAD_CONST(1.0) + exp_q(arg));
                    real_t dE = TCAD_CONST(1.0);   // effective trap energy range [eV]
                    // Q_it in [C/m^2], divide by the trap layer thickness to
                    // get a mesh-invariant [C/m^3] for the RHS.
                    real_t D_it_m2 = trap_D_it_ * TCAD_CONST(1.0e4);   // cm^-2 -> m^-2
                    real_t t_layer = (trap_layer_thickness_ > TCAD_CONST(0.0))
                                     ? trap_layer_thickness_ : g_.dx;
                    real_t Q_it = -QE * D_it_m2 * dE * (f_t - TCAD_CONST(0.5)) / t_layer;
                    // Trap charge is physical rho [C/m^3], hence -rho in
                    // div(eps*grad(phi))=-rho_free+div(P).
                    rhs_[idx] -= Q_it;
                }
                if (!Q_ot_.empty() && idx < Q_ot_.size()) {
                    rhs_[idx] -= Q_ot_[idx];   // bulk oxide trap charge [C/m^3]
                }

                // div(D)=rho_free, D=-eps*grad(phi)+P implies
                // div(eps*grad(phi))=-rho_free+div(P). Bound charge
                // rho_bound=-div(P) enters this RHS with +div(P).
                if (fe_enabled_) {
                    auto edge_eps = [&](int axis, bool upper, size_t node, size_t) {
                        if (axis == 0) return upper
                            ? cx_plus(node)*g_.dx_edge(i)*g_.dx_cell(i)
                            : cx_minus(node)*g_.dx_edge(i-1)*g_.dx_cell(i);
                        if (axis == 1) return upper
                            ? cy_plus(node)*g_.dy_edge(j)*g_.dy_cell(j)
                            : cy_minus(node)*g_.dy_edge(j-1)*g_.dy_cell(j);
                        return upper
                            ? cz_plus(node)*g_.dz_edge(k)*g_.dz_cell(k)
                            : cz_minus(node)*g_.dz_edge(k-1)*g_.dz_cell(k);
                    };
                    rhs_[idx] += polarization_divergence(g_, fe_mask_,
                        fe_polarization_, eps_, i, j, k, edge_eps);
                }

                // Dielectric PF/FN and post-breakdown filament conduction are
                // transport currents [A/m^2], not electrostatic charge. Both
                // are evaluated on dielectric edges after the solve and
                // exposed as Jleak_{x,y,z}. Do not add a conductance to the
                // Poisson diagonal: that would create a mesh-dependent,
                // fictitious connection to zero volts.
            }
        }
    }
    A_.finalize();
    assembled_ = true;

}

void PoissonSolver::assemble_thermal(const std::vector<real_t>& power_density,
    const std::vector<real_t>& heat_capacity,
    const std::vector<real_t>& previous_temperature, real_t dt) {
    const size_t N = g_.npts();
    if (power_density.size() != N || !isfinite_q(dt) || dt < TCAD_CONST(0.0))
        throw std::invalid_argument("invalid lattice source or time step");
    const bool storage = dt > TCAD_CONST(0.0);
    if (storage && (heat_capacity.size() != N || previous_temperature.size() != N))
        throw std::invalid_argument("lattice history/capacity size mismatch");
    for (size_t i=0; i<N; ++i) {
        if (!isfinite_q(power_density[i]) || (storage &&
            (!isfinite_q(heat_capacity[i]) || heat_capacity[i] <= TCAD_CONST(0.0) ||
             !isfinite_q(previous_temperature[i]) || previous_temperature[i] <= TCAD_CONST(0.0))))
            throw std::invalid_argument("invalid lattice source, capacity or history");
    }
    A_ = SparseMatrix(N);
    rhs_.assign(N, TCAD_CONST(0.0));
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_dirichlet_[idx]) {
                    A_.add_entry(idx, idx, TCAD_CONST(1.0));
                    rhs_[idx] = dirichlet_bc_.at(idx);
                    continue;
                }
                if (eps_[idx] < EPSILON) {
                    A_.add_entry(idx, idx, TCAD_CONST(1.0));
                    rhs_[idx] = TCAD_CONST(0.0);
                    continue;
                }

                real_t center = TCAD_CONST(0.0);
                real_t c;

                c = cx_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + 1, c); center -= c; }
                c = cx_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - 1, c); center -= c; }
                c = cy_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + g_.nx, c); center -= c; }
                c = cy_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - g_.nx, c); center -= c; }
                c = cz_plus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx + g_.nx * g_.ny, c); center -= c; }
                c = cz_minus(idx);
                if (c != TCAD_CONST(0.0)) { A_.add_entry(idx, idx - g_.nx * g_.ny, c); center -= c; }

                const real_t rate = storage ? heat_capacity[idx]/dt : TCAD_CONST(0.0);
                // A represents div(k grad T), with a negative diagonal.
                A_.add_entry(idx, idx, center-rate);
                rhs_[idx] = -power_density[idx] - (storage ? rate*previous_temperature[idx] : TCAD_CONST(0.0));
            }
        }
    }
    A_.finalize();
    assembled_ = true;
}

void PoissonSolver::set_ferroelectric(const std::vector<char>& fe_mask,
                                      real_t alpha, real_t beta) {
    if (fe_mask.size() != g_.npts())
        throw std::invalid_argument("fe_mask size mismatch");
    if (!isfinite_q(alpha) || !isfinite_q(beta))
        throw std::invalid_argument("FE alpha and beta must be finite");
    fe_mask_ = fe_mask;
    fe_alpha_ = alpha;
    fe_beta_ = beta;
    fe_enabled_ = true;
    // Preserve an externally-injected persistent P (from DeviceSimulator) across
    // a GummelSolver rebuild; only allocate on first call / size mismatch.
    // Vector storage: 3*npts interleaved [Px,Py,Pz] per node.
    if (fe_polarization_.size() != 3 * g_.npts())
        fe_polarization_.assign(3 * g_.npts(), TCAD_CONST(0.0));
}

FerroelectricNlsDrive PoissonSolver::ferroelectric_nls_drive(const std::vector<real_t>& phi) const {
    if (!fe_enabled_ || fe_model_ != 2)
        throw std::logic_error("NLS drive requires enabled NLS");
    const size_t N = g_.npts();
    if (phi.size() != N || fe_polarization_.size() != 3 * N ||
        !std::all_of(phi.begin(), phi.end(), isfinite_q) ||
        !std::all_of(fe_polarization_.begin(), fe_polarization_.end(), isfinite_q))
        throw std::invalid_argument("NLS requires finite potential and polarization fields");
    real_t E = TCAD_CONST(0.0), P_old = TCAD_CONST(0.0), volume = TCAD_CONST(0.0);
    std::vector<real_t> local_fields;
    for (size_t k = 0; k < g_.nz; ++k)
        for (size_t j = 0; j < g_.ny; ++j)
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!fe_mask_[idx]) continue;
                const real_t weight = fe_node_volume(i, j, k);
                real_t E_local = e_field_component(phi, i, j, k, fe_axis_);
                local_fields.push_back(E_local);
                E += weight * E_local;
                P_old += weight * fe_polarization_[3*idx+fe_axis_];
                volume += weight;
            }
    if (local_fields.empty()) return {};
    if (!isfinite_q(volume) || !isfinite_q(E) || !isfinite_q(P_old) || volume <= TCAD_CONST(0.0))
        throw std::invalid_argument("NLS volume quadrature overflowed");
    E /= volume;
    P_old /= volume;
    real_t uniform_field_offset = fe_E_bi_;
    E -= fe_E_bi_;
    if (fe_eps_fe_ > TCAD_CONST(0.0)) {
        const real_t eps0 = TCAD_CONST(8.854187817e-12);
        real_t E_dep = P_old / (fe_eps_fe_ * eps0);
        E -= E_dep;
        uniform_field_offset += E_dep;
    }

    // Retain the existing compact peak-rate closure: volume-average sign
    // selects the branch, maximal local effective field sets the rate.
    // This is a declared approximation, not resolved spatial nucleation.
    real_t E_peak_eff = TCAD_CONST(0.0);
    for (real_t field : local_fields)
        E_peak_eff = std::max(E_peak_eff, abs_q(field - uniform_field_offset));
    // A converged zero-bias solve can leave a sub-quad-precision residual
    // field. Treat only that numerical residue as zero; this is a
    // scale-relative roundoff guard, not a material coercive-field cutoff.
    const real_t raw_mean = E;
    real_t field_scale = std::max(abs_q(E), E_peak_eff);
    field_scale = std::max(field_scale, TCAD_CONST(1.0));
    const real_t zero_field_tol = TCAD_CONST(1.0e-24) * field_scale;
    if (abs_q(E) <= zero_field_tol) E = TCAD_CONST(0.0);
    if (E_peak_eff <= zero_field_tol) E_peak_eff = TCAD_CONST(0.0);
    real_t Eabs = std::max(abs_q(E), E_peak_eff);
    if (!isfinite_q(Eabs) || !isfinite_q(E))
        throw std::invalid_argument("NLS effective field overflowed");
    return {true, raw_mean, E, E_peak_eff, P_old, volume, zero_field_tol};
}

void PoissonSolver::update_ferroelectric_polarization(const std::vector<real_t>& phi) {
    if (!fe_enabled_) return;
    // Validate before any model normalizes persistent P or play memory.
    // Keep the established NLS diagnostic and the disabled-FE no-op.
    if (phi.size() != g_.npts())
        throw std::invalid_argument(fe_model_ == 2
            ? "NLS requires finite potential and polarization fields"
            : "FE potential size mismatch");
    if (!std::all_of(phi.begin(), phi.end(), isfinite_q))
        throw std::invalid_argument(fe_model_ == 2
            ? "NLS requires finite potential and polarization fields"
            : "FE potential values must be finite");

    // ---- Sentaurus-compatible Preisach turning-point path ----
    // Sentaurus Device W-2024.09, User Guide Eq. 986-987:
    //   P = Ps*tanh(w*(E +/- Ec)),
    //   w = log((Ps+Pr)/(Ps-Pr))/(2*Ec).
    // fe_escale_ stores 1/w so the existing public Ps/Ec/Escale API remains
    // ABI compatible. Unlike the legacy one-play model below, this permits
    // saturation Ps and remanence Pr to be calibrated independently.
    // Turning-point pairs determine c and Poff in Eq. 986. Preserve the
    // default asymmetric initial history, nested loops and memory wipeout
    // (User Guide, pp. 949-950), rather than jumping between major branches.
    if (fe_model_ == 3) {
        const size_t N = g_.npts();
        const size_t history_start = 2 * N;
        if (fe_play_state_.size() >= history_start + 4 &&
            (fe_play_state_.size() - history_start) % 2 != 0)
            throw std::invalid_argument("FE turning-point history must contain complete field/polarization pairs");
        const bool has_prefix = fe_play_state_.size() >= history_start;
        const bool has_polarization = fe_polarization_.size() == 3 * N;
        const real_t Ps = fe_ps_;
        const real_t Ec = fe_ec_;
        const real_t Escale = (fe_escale_ > TCAD_CONST(0.0)) ? fe_escale_
                            : ((Ec > TCAD_CONST(0.0)) ? Ec : TCAD_CONST(1.0));

        real_t E = TCAD_CONST(0.0), P_old = TCAD_CONST(0.0), E_previous = TCAD_CONST(0.0);
        real_t branch_accum = TCAD_CONST(0.0);
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    const size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    E += e_field_component(phi, i, j, k, fe_axis_);
                    P_old += has_polarization ? fe_polarization_[3 * idx + fe_axis_] : TCAD_CONST(0.0);
                    E_previous += has_prefix ? fe_play_state_[idx] : TCAD_CONST(0.0);
                    branch_accum += has_prefix ? fe_play_state_[N + idx] : TCAD_CONST(0.0);
                    ++n_fe;
                }
        if (n_fe == 0) {
            if (!has_prefix) fe_play_state_.assign(history_start, TCAD_CONST(0.0));
            if (!has_polarization) fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
            return;
        }
        E /= (real_t)n_fe;
        P_old /= (real_t)n_fe;
        E_previous /= (real_t)n_fe;
        E -= fe_E_bi_;
        if (fe_eps_fe_ > TCAD_CONST(0.0)) {
            const real_t eps0 = TCAD_CONST(8.854187817e-12);
            E -= P_old / (fe_eps_fe_ * eps0);
        }

        // The tail stores (field, P) turning points, newest first. Saturation
        // endpoints use a finite sentinel well beyond any physical field.
        // Work only on the shared turning-point tail until its bracket is
        // known to be complete. Invalid histories must not change P/prefixes.
        std::vector<real_t> turning_points;
        if (fe_play_state_.size() < history_start + 4) {
            const real_t Pr = Ps * tanh_q(Ec / Escale);
            const real_t Pb = TCAD_CONST(0.5) * (Ps - Pr);
            const real_t ratio = Ps > TCAD_CONST(0.0) ? Pb / Ps : TCAD_CONST(0.0);
            const real_t Eb = Ec + TCAD_CONST(0.5) * Escale *
                log_q((TCAD_CONST(1.0) + ratio) / (TCAD_CONST(1.0) - ratio));
            turning_points = {Eb, Pb, -TCAD_CONST(1.0e300), -Ps, TCAD_CONST(1.0e300), Ps};
            // Pini=0 lies on the decreasing curve between b and negative
            // saturation. Positive first loading adds (0,0) to the history.
            branch_accum = -(real_t)n_fe;
        } else {
            turning_points.assign(fe_play_state_.begin() + history_start, fe_play_state_.end());
        }
        int branch = branch_accum > TCAD_CONST(0.0) ? 1 : -1;
        const real_t field_tol = std::max(TCAD_CONST(1.0), abs_q(E) * TCAD_CONST(1.0e-12));
        const real_t delta = E - E_previous;
        real_t P_target = P_old;
        if (abs_q(delta) > field_tol) {
            const int direction = delta > TCAD_CONST(0.0) ? 1 : -1;
            if (direction != branch) {
                turning_points.insert(turning_points.begin(), {E_previous, P_old});
                branch = direction;
            }
            // Crossing either endpoint erases the newest nested loop. Repeat
            // when a large field step crosses several enclosing loops.
            while (turning_points.size() > 4) {
                const real_t first = turning_points[0];
                const real_t second = turning_points[2];
                if (E >= std::min(first, second) &&
                    E <= std::max(first, second)) break;
                if (turning_points.size() < 8)
                    throw std::invalid_argument("FE turning-point history has incomplete wipeout bracket");
                turning_points.erase(turning_points.begin(), turning_points.begin() + 4);
            }
            const real_t E1 = turning_points[0];
            const real_t P1 = turning_points[1];
            const real_t E2 = turning_points[2];
            const real_t P2 = turning_points[3];
            const real_t t1 = tanh_q((E1 - branch * Ec) / Escale);
            const real_t t2 = tanh_q((E2 - branch * Ec) / Escale);
            const real_t t = tanh_q((E - branch * Ec) / Escale);
            // Interpolating in tanh-space is Eq. 986 with c/Poff chosen to
            // pass through both memory endpoints. In a numerically saturated
            // tiny loop both endpoints coincide; retain its polarization.
            P_target = abs_q(t2 - t1) > EPSILON
                ? P1 + (P2 - P1) * (t - t1) / (t2 - t1) : P_old;
        }
        const real_t P = fe_relax_ * P_target + (TCAD_CONST(1.0) - fe_relax_) * P_old;
        if (!has_polarization) fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
        fe_play_state_.resize(history_start);
        fe_play_state_.insert(fe_play_state_.end(), turning_points.begin(), turning_points.end());
        for (size_t idx = 0; idx < N; ++idx) {
            if (!fe_mask_[idx]) {
                fe_polarization_[3 * idx + 0] = TCAD_CONST(0.0);
                fe_polarization_[3 * idx + 1] = TCAD_CONST(0.0);
                fe_polarization_[3 * idx + 2] = TCAD_CONST(0.0);
                fe_play_state_[idx] = TCAD_CONST(0.0);
                fe_play_state_[N + idx] = TCAD_CONST(0.0);
                continue;
            }
            fe_polarization_[3 * idx + fe_axis_] = P;
            for (int component = 0; component < 3; ++component)
                if (component != fe_axis_)
                    fe_polarization_[3 * idx + component] = TCAD_CONST(0.0);
            fe_play_state_[idx] = E;
            fe_play_state_[N + idx] = (real_t)branch;
        }
        return;
    }

    // ---- Preisach (play-operator) path (M7c) ----
    // Classical scalar Preisach realised as a moving (play) model: each node
    // carries a single internal "play" value w (the delayed field). On a field
    // step the play follows E but lags by the coercive half-width Ec, and the
    // output P = Ps*tanh((E - w)/Escale) saturates at +/-Ps. This produces the
    // correct rectangular-ish hysteresis loop (remanence at E=0, switching when
    // |E| crosses Ec) WITHOUT the L-K alpha/beta dimensional mess, and with a
    // natural memory (the play value w). Only the polar-axis component
    // (fe_axis_; scalar Preisach) is driven; the output P is written into
    // fe_polarization_ (fe_axis_ component) so assemble()'s -div(P) term is
    // shared with the L-K path. The play state fe_play_state_ persists across
    // solve().
    if (fe_model_ == 1) {
        const size_t N = g_.npts();
        if (fe_play_state_.size() != N) fe_play_state_.assign(N, TCAD_CONST(0.0));
        if (fe_polarization_.size() != 3 * N) fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
        const real_t Ps = fe_ps_;
        const real_t Ec = fe_ec_;
        // Tanh output width. Escale=0 (default) falls back to Ec, which keeps
        // the play-operator hysteresis correctly shaped: inside the ±Ec deadband
        // the output tanh((E-w)/Ec) varies smoothly with |arg|<=1, giving a
        // nonzero remanence window at E=0. A smaller Escale steepens the tanh,
        // letting |P| approach the named saturation Ps on a monotonic ramp, but
        // too small (e.g. Ec/3) collapses the loop because once the drive leaves
        // the deadband the saturated output pins P at +/-Ps and the remanence
        // window vanishes. So Ec is the safe default; set Escale<Ec explicitly
        // only when monotonic-saturation (not loop shape) is the priority.
        const real_t Escale = (fe_escale_ > TCAD_CONST(0.0)) ? fe_escale_
                            : ((Ec > TCAD_CONST(0.0)) ? Ec : TCAD_CONST(1.0));
        // Treat the compact Preisach model as a uniform FE domain ensemble.
        // Updating one play operator per mesh node lets self-consistent bound
        // charge seed artificial node-to-node domains in a nominally uniform
        // thin film, which weakens built-in/imprint-field shifts and makes the
        // result grid-dependent.  Average the polar-axis drive over the FE
        // region, advance one ensemble play state, then write the same
        // polarization back to all FE nodes.  This matches the compact nature
        // of the model and the NLS path below.
        //
        // Drive and imprint semantics (imprint/Vc audit, 2026-09-18):
        // (1) The ensemble drive is the electrode-screened potential drop
        //     across the FE region along the polar axis.  The node-averaged
        //     gradient mixes in the unscreened self-consistent depolarization
        //     field ~P/(eps0*epsr) >> Ec of a saturated uniform film (through
        //     the boundary-node one-sided stencils), which flipped the play
        //     state on every bias step (period-2 +/-Ps chatter).
        // (2) The internal/imprint field E_bi offsets the OUTPUT comparison
        //     only; the play history tracks the applied field.  Feeding
        //     E - E_bi into the play as well made the saturated major-loop
        //     crossings E_bi-invariant (E_bi re-absorbed by the play reset),
        //     i.e. the imprint vanished from the major loop.
        real_t E = TCAD_CONST(0.0), P_old = TCAD_CONST(0.0), w_old = TCAD_CONST(0.0);
        real_t E_grad = TCAD_CONST(0.0);
        real_t phi_lo_sum = TCAD_CONST(0.0), phi_hi_sum = TCAD_CONST(0.0);
        size_t n_lo = 0, n_hi = 0;
        long lo = -1, hi = -1;
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    const size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    E_grad += e_field_component(phi, i, j, k, fe_axis_);
                    P_old += fe_polarization_[3 * idx + fe_axis_];
                    w_old += fe_play_state_[idx];
                    const long coord = (fe_axis_ == 0) ? (long)i
                                   : ((fe_axis_ == 1) ? (long)j : (long)k);
                    if (lo < 0 || coord < lo) { lo = coord; phi_lo_sum = TCAD_CONST(0.0); n_lo = 0; }
                    if (hi < 0 || coord > hi) { hi = coord; phi_hi_sum = TCAD_CONST(0.0); n_hi = 0; }
                    if (coord == lo) { phi_lo_sum += phi[idx]; ++n_lo; }
                    if (coord == hi) { phi_hi_sum += phi[idx]; ++n_hi; }
                    ++n_fe;
                }
        if (n_fe == 0) return;
        P_old /= (real_t)n_fe;
        w_old /= (real_t)n_fe;
        E_grad /= (real_t)n_fe;
        const real_t d_axis = (fe_axis_ == 0) ? g_.dx
                          : ((fe_axis_ == 1) ? g_.dy : g_.dz);
        if (hi > lo && n_lo > 0 && n_hi > 0 && d_axis > TCAD_CONST(0.0)) {
            E = (phi_lo_sum / (real_t)n_lo - phi_hi_sum / (real_t)n_hi)
                / ((real_t)(hi - lo) * d_axis);
        } else {
            E = E_grad;
        }
        if (fe_eps_fe_ > TCAD_CONST(0.0)) {
            const real_t eps0 = TCAD_CONST(8.854187817e-12);
            E -= P_old / (fe_eps_fe_ * eps0);
        }

        // Play operator update: w follows E but lags by Ec.
        real_t w = w_old;
        if (E > w + Ec)       w = E - Ec;
        else if (E < w - Ec)  w = E + Ec;

        // Saturating output: P = Ps * tanh((E - E_bi - w)/Escale); the
        // imprint offset enters the output comparison only (see above).
        const real_t arg = (E - fe_E_bi_ - w) / Escale;
        const real_t P_new = Ps * tanh_q(arg);
        const real_t P = fe_relax_ * P_new + (TCAD_CONST(1.0) - fe_relax_) * P_old;

        for (size_t idx = 0; idx < N; ++idx) {
            if (!fe_mask_[idx]) {
                fe_polarization_[3*idx+0] = TCAD_CONST(0.0);
                fe_polarization_[3*idx+1] = TCAD_CONST(0.0);
                fe_polarization_[3*idx+2] = TCAD_CONST(0.0);
                fe_play_state_[idx] = TCAD_CONST(0.0);
                continue;
            }
            fe_polarization_[3*idx+fe_axis_] = P;
            for (int c = 0; c < 3; ++c)
                if (c != fe_axis_) fe_polarization_[3*idx+c] = TCAD_CONST(0.0);
            fe_play_state_[idx] = w;
        }
        return;
    }

    // ---- NLS (Nucleation-Limited Switching) path (P3, model==2) ----
    // Suitable for wurtzite ferroelectrics like AlScN whose 180° switching is
    // domain-nucleation-limited rather than homogeneous (LK) or play-operator
    // (Preisach). Under NLS the switching dynamics follow Merz's law:
    //     tau(E) = tau0 * exp(E0 / |E|)     [switching time, |E| in V/m]
    // Each accepted clocked bias step applies the configured physical
    // dwell time dt_eff, so the
    // polarization relaxes toward the field-favored target
    //     P_target = sign(E_eff) * Ps
    // by a fractional amount f = 1 - exp(-dt_eff / tau(E)). The rate depends
    // on tau0 and E0, rather than a hard coercive-field cutoff. This compact
    // relaxation does not by itself validate AlScN switching kinetics.
    // Off-axis components stay 0 (scalar NLS along fe_axis_).
    // The state P persists across solve() so the loop has path-dependent
    // memory. The state is advanced exactly ONCE per Gummel solve() call (see
    // GummelSolver::solve), so the physical dwell time is decoupled from the
    // iteration count (P0-2 fix).
    if (fe_model_ == 2) {
        const size_t N = g_.npts();
        if (fe_polarization_.size() != 3 * N) fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
        const real_t Ps = fe_ps_;
        const real_t tau0 = fe_nls_tau0_;     // characteristic switching time [s]
        const real_t E0 = fe_nls_E0_;         // Merz activation field [V/m]
        // Physical dwell of this accepted clocked bias step. Updating once
        // from a field predictor is still an operator split, not a coupled
        // transient solution.
        const real_t dt_eff = fe_nls_dt_;
        // NLS is a domain-ensemble (volume-averaged) switching model, not a
        // phase-field model.  Advancing every mesh node from its local field
        // let tiny discretisation variations create artificial domains; their
        // bound charge then reversed the local field on the return branch and
        // drove P back to +Ps under a negative applied voltage.  Use the FE
        // volume-average drive and state, as in compact NLS formulations, and
        // write one uniform ensemble polarization into the FE region.
        const auto drive = ferroelectric_nls_drive(phi);
        if (!drive.active) return;
        const real_t E = drive.mean_field, P_old = drive.mean_polarization;
        const real_t Eabs = std::max(abs_q(E), drive.peak_field);
        // Select the target from the guarded mean drive. A finite local peak
        // must not turn a mean-field roundoff residual into ensemble switching.
        const real_t P_target = (E > TCAD_CONST(0.0)) ? Ps : ((E < TCAD_CONST(0.0)) ? -Ps : P_old);
        real_t f = TCAD_CONST(0.0);
        if (Eabs > TCAD_CONST(0.0)) {
            // Merz has no hard Ec/10 cutoff. Log-domain evaluation avoids an
            // overflowing intermediate tau even when the final fraction is
            // representable; expm1 preserves short-pulse switching increments.
            const real_t log_r = log_q(dt_eff) - log_q(tau0) - E0 / Eabs;
            f = (log_r > log_q(TCAD_CONST(100.0))) ? TCAD_CONST(1.0) : -expm1_q(-exp_q(log_r));
        }
        real_t P_step = P_old + f * (P_target - P_old);
        real_t P = fe_relax_ * P_step + (TCAD_CONST(1.0) - fe_relax_) * P_old;
        if (P > Ps) P = Ps;
        if (P < -Ps) P = -Ps;
        for (size_t idx = 0; idx < N; ++idx) {
            if (!fe_mask_[idx]) {
                fe_polarization_[3*idx+0] = TCAD_CONST(0.0);
                fe_polarization_[3*idx+1] = TCAD_CONST(0.0);
                fe_polarization_[3*idx+2] = TCAD_CONST(0.0);
                continue;
            }
            fe_polarization_[3*idx+fe_axis_] = P;
            for (int c = 0; c < 3; ++c)
                if (c != fe_axis_) fe_polarization_[3*idx+c] = TCAD_CONST(0.0);
        }
        return;
    }

    // ---- Landau-Khalatnikov path (default) ----
    // Quasi-static isotropic vector Landau-Khalatnikov: each component solves
    //   alpha*P_i + beta*P_i^3 = E_i   (i = x,y,z)
    // independently (isotropic Landau, appropriate for polycrystalline HfO2;
    // no cross-coupling / tensor alpha_ij, beta_ijkl). The per-component sign is
    // the branch / memory, so hysteresis arises from continuation in the Newton
    // initial guess (previous P_i): P_i stays on its branch until E_i crosses
    // the opposite spinodal (-Ec), where Newton snaps to the other well.
    // (A4: supersedes the signed-scalar "dominant component E_drive" form; the
    //  1D scalar behavior is recovered as the special case where only Px!=0.)
    {
        const size_t N = g_.npts();
        // An explicitly cleared static state starts from pristine zero P.
        // Delay allocation until commit so an empty FE support stays a no-op.
        const bool has_polarization = fe_polarization_.size() == 3 * N;
        const real_t Ps = sqrt_q(-fe_alpha_ / fe_beta_);
        const real_t P_sp = sqrt_q(-fe_alpha_ / (TCAD_CONST(3.0) * fe_beta_));
        const real_t Ec = (TCAD_CONST(2.0) / TCAD_CONST(3.0)) * abs_q(fe_alpha_) * P_sp;

        // This is a single-domain LK compact model, not a phase-field/domain-
        // wall solver.  Per-node branch updates amplified round-off into
        // alternating mesh domains whose artificial div(P) locked the branch.
        // Use the volume-average field and state independently for all three
        // vector components, and write one deterministic domain state to the
        // FE film.  This retains simultaneous Px/Py response in a 2-D field.
        real_t E[3] = {TCAD_CONST(0.0), TCAD_CONST(0.0), TCAD_CONST(0.0)};
        real_t P_old[3] = {TCAD_CONST(0.0), TCAD_CONST(0.0), TCAD_CONST(0.0)};
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    for (int c = 0; c < 3; ++c) {
                        E[c] += e_field_component(phi, i, j, k, c);
                        P_old[c] += has_polarization
                            ? fe_polarization_[3*idx + c] : TCAD_CONST(0.0);
                    }
                    ++n_fe;
                }
        if (n_fe == 0) return;
        for (int c = 0; c < 3; ++c) {
            E[c] /= (real_t)n_fe;
            P_old[c] /= (real_t)n_fe;
        }
        E[fe_axis_] -= fe_E_bi_;
        if (fe_eps_fe_ > TCAD_CONST(0.0))
            E[fe_axis_] -= P_old[fe_axis_] / (fe_eps_fe_ * TCAD_CONST(8.854187817e-12));

        real_t P[3];
        for (int c = 0; c < 3; ++c) {
            P[c] = P_old[c];
            if (abs_q(P[c]) < TCAD_CONST(1.0e-18)) {
                if (E[c] > TCAD_CONST(1.0)) P[c] = Ps;
                else if (E[c] < -TCAD_CONST(1.0)) P[c] = -Ps;
            } else if (Ec > TCAD_CONST(0.0) && abs_q(E[c]) > Ec && P[c] * E[c] < TCAD_CONST(0.0)) {
                P[c] = (E[c] > TCAD_CONST(0.0)) ? Ps : -Ps;
            }
            for (int iter = 0; iter < 20; ++iter) {
                real_t f = fe_alpha_ * P[c] + fe_beta_ * P[c] * P[c] * P[c] - E[c];
                real_t df = fe_alpha_ + TCAD_CONST(3.0) * fe_beta_ * P[c] * P[c];
                if (abs_q(df) < TCAD_CONST(1e-30)) break;
                real_t dP = f / df;
                P[c] -= dP;
                if (abs_q(dP) < TCAD_CONST(1e-15) * std::max(abs_q(P[c]), TCAD_CONST(1.0))) break;
            }
            if (P[c] > Ps) P[c] = Ps;
            if (P[c] < -Ps) P[c] = -Ps;
            P[c] = fe_relax_ * P[c] + (TCAD_CONST(1.0) - fe_relax_) * P_old[c];
        }

        if (!has_polarization)
            fe_polarization_.assign(3 * N, TCAD_CONST(0.0));
        for (size_t idx = 0; idx < N; ++idx) {
            for (int c = 0; c < 3; ++c)
                fe_polarization_[3*idx + c] = fe_mask_[idx] ? P[c] : TCAD_CONST(0.0);
        }
        return;
    }

    const real_t Ps = sqrt_q(-fe_alpha_ / fe_beta_);  // double-well minimum
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!fe_mask_[idx]) {
                    fe_polarization_[3*idx + 0] = TCAD_CONST(0.0);
                    fe_polarization_[3*idx + 1] = TCAD_CONST(0.0);
                    fe_polarization_[3*idx + 2] = TCAD_CONST(0.0);
                    continue;
                }

                // Compute E = -grad(phi) components
                real_t Ex = TCAD_CONST(0.0), Ey = TCAD_CONST(0.0), Ez = TCAD_CONST(0.0);
                if (i > 0 && i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx - 1]) / (TCAD_CONST(2.0) * g_.dx);
                else if (i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                else if (i > 0)
                    Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                if (j > 0 && j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (TCAD_CONST(2.0) * g_.dy);
                else if (j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
                else if (j > 0)
                    Ey = -(phi[idx] - phi[idx - g_.nx]) / g_.dy;
                if (k > 0 && k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (TCAD_CONST(2.0) * g_.dz);
                else if (k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz;
                else if (k > 0)
                    Ez = -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz;

                // P2.1: apply the internal/imprint field offset to the polar
                // axis (fe_axis_) switching component. E_eff = E - E_bi breaks
                // +/- symmetry. (P0-1 fix: was applied to Ex only, so a
                // z-stacked FeFET never saw the imprint/depol drive.)
                real_t Ei[3] = {Ex, Ey, Ez};
                Ei[fe_axis_] -= fe_E_bi_;
                // Depolarization field (comments2.docx P3): E_dep = -P/(eps_fe*eps0),
                // using the polar-axis component of P.
                if (fe_eps_fe_ > TCAD_CONST(0.0)) {
                    real_t eps0 = TCAD_CONST(8.854187817e-12);
                    Ei[fe_axis_] -= fe_polarization_[3*idx + fe_axis_] / (fe_eps_fe_ * eps0);
                }
                // Spinodal polarization / coercive field of the double well:
                //   P_sp = sqrt(-alpha/(3*beta)),  Ec = (2|alpha|/3)*P_sp.
                // A component whose drive E_i opposes its current sign AND exceeds
                // Ec is PAST the spinodal -> the current well no longer exists and
                // P must switch to the opposite well.  Newton started from the old
                // well's P converges back to it (local minimum past the barrier),
                // which is the sporadic-non-switching failure mode.  Re-seeding to
                // the opposite signed well minimum lets Newton land on the correct
                // branch.  (FE-coupling fix, audit §21.)
                const real_t P_sp = sqrt_q(-fe_alpha_ / (TCAD_CONST(3.0) * fe_beta_));
                const real_t Ec = (TCAD_CONST(2.0) / TCAD_CONST(3.0)) * abs_q(fe_alpha_) * P_sp;
                // Do not nucleate a pristine domain from round-off in an
                // otherwise zero-field Poisson solution.  Previously an
                // O(1e-20 V) mesh perturbation selected random +/- wells at
                // different nodes; their artificial bound charge then locked
                // the slab into a mesh-dependent multidomain state.  One V/m
                // is far below any physical FE switching field while safely
                // above the numerical field floor.
                const real_t field_seed_floor = TCAD_CONST(1.0);
                for (int c = 0; c < 3; ++c) {
                    real_t E_i = Ei[c];
                    // Initial guess: continue from the previous P_i (path dependence).
                    // A pristine component (P_i==0) is seeded ONLY where the field
                    // drives it (|E_i|>0): pin to sign(E_i)*Ps (double-well minimum,
                    // Newton-safe, branch-correct). Where E_i==0 a pristine component
                    // stays at 0 — so a 1D field (Ey=Ez=0) yields Py=Pz==0 exactly,
                    // matching the prior scalar behavior with no spurious off-axis P.
                    real_t P = fe_polarization_[3*idx + c];
                    if (P == TCAD_CONST(0.0)) {
                        if (E_i > field_seed_floor)       P = Ps;
                        else if (E_i < -field_seed_floor) P = -Ps;
                        // Numerically zero field: leave P=0, including all
                        // un-driven off-axis components.
                    } else if (Ec > TCAD_CONST(0.0)) {
                        // Switching test: drive opposes P and exceeds coercive field.
                        // Re-seed to the opposite well so Newton crosses the barrier.
                        real_t drive_sign = (E_i > TCAD_CONST(0.0)) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                        if ((P * drive_sign < TCAD_CONST(0.0)) && abs_q(E_i) > Ec) {
                            P = drive_sign * Ps;
                        }
                    }

                    // Solve alpha*P + beta*P^3 = E_i (signed) by Newton.
                    for (int iter = 0; iter < 20; ++iter) {
                        real_t f = fe_alpha_ * P + fe_beta_ * P * P * P - E_i;
                        real_t df = fe_alpha_ + TCAD_CONST(3.0) * fe_beta_ * P * P;
                        if (abs_q(df) < TCAD_CONST(1e-30)) break;
                        real_t dP = f / df;
                        P -= dP;
                        if (abs_q(dP) < TCAD_CONST(1e-15) * abs_q(P)) break;
                    }
                    // BUG FIX (comments2.docx): clamp P to [-Ps, +Ps].
                    if (P > Ps) P = Ps;
                    if (P < -Ps) P = -Ps;
                    // Under-relaxation (comments2.docx): blend new and old P.
                    real_t P_prev = fe_polarization_[3*idx + c];
                    P = fe_relax_ * P + (TCAD_CONST(1.0) - fe_relax_) * P_prev;
                    fe_polarization_[3*idx + c] = P;
                }
            }
        }
    }
}

void PoissonSolver::set_ferroelectric_gamma(real_t gamma) {
    fe_gamma_ = gamma;
}

void PoissonSolver::set_breakdown_state(const std::vector<char>& bd_state, real_t sigma_bd) {
    // Retained for API compatibility/debugging. Breakdown conduction is an
    // explicit edge current evaluated by DeviceSimulator and never belongs in
    // the electrostatic Poisson equation.
    bd_state_ = bd_state;
    sigma_bd_ = sigma_bd;
}

void PoissonSolver::set_ferroelectric_model(int model) {
    // 0 = Landau-Khalatnikov (default), 1 = Preisach (play operator). M7c.
    fe_model_ = model;
}

void PoissonSolver::set_ferroelectric_preisach(real_t ps, real_t ec, real_t escale) {
    if (!isfinite_q(ps) || !isfinite_q(ec) || !isfinite_q(escale) ||
        ps < TCAD_CONST(0.0) || ec < TCAD_CONST(0.0) || escale < TCAD_CONST(0.0))
        throw std::invalid_argument("FE Ps, Ec and Escale must be finite and nonnegative");
    fe_ps_ = ps;
    fe_ec_ = ec;
    fe_escale_ = escale;   // 0 => Ec (legacy loop-shape default)
}

void PoissonSolver::set_ferroelectric_builtin_field(real_t E_bi) {
    if (!isfinite_q(E_bi))
        throw std::invalid_argument("FE builtin field must be finite");
    fe_E_bi_ = E_bi;       // P2.1: internal/imprint offset; 0 => symmetric
}

void PoissonSolver::set_ferroelectric_depol(real_t eps_fe) {
    if (!isfinite_q(eps_fe) || eps_fe < TCAD_CONST(0.0))
        throw std::invalid_argument("extra depolarization permittivity must be finite and nonnegative");
    fe_eps_fe_ = eps_fe;   // comments2.docx P3: depol E_dep = -P/(eps_fe*eps0)
}

void PoissonSolver::set_interface_traps(const std::vector<char>& mask,
                                        real_t D_it, real_t E_t) {
    if (!mask.empty() && mask.size() != g_.npts())
        throw std::invalid_argument("trap mask size mismatch");
    if (!isfinite_q(D_it) || D_it < TCAD_CONST(0.0))
        throw std::invalid_argument("interface trap density must be finite and nonnegative");
    if (!isfinite_q(E_t))
        throw std::invalid_argument("interface trap energy must be finite");
    trap_mask_ = mask;
    trap_D_it_ = D_it;     // [cm^-2 eV^-1]
    trap_E_t_ = E_t;       // [eV] relative to intrinsic Fermi level
    // P0-6 fix: cache the trap layer thickness (extent of the mask along its
    // non-spanning axis = interface normal) for the mesh-invariant surface->volume
    // charge conversion in assemble().
    trap_layer_thickness_ = compute_trap_layer_thickness();
}

real_t PoissonSolver::compute_trap_layer_thickness() const {
    // The interface normal is the axis along which the mask does NOT span the
    // whole grid (a layer/plane embedded in the device): t_layer is the mask
    // extent along that axis. For the FeFET gate stack (mask = FE region,
    // partial z span, full x/y span) this picks z with t_layer = t_fe — so
    // the total trapped charge is D_it x (interface area), invariant under
    // mesh refinement along z. If the mask spans the whole grid along every
    // axis (bulk mask, e.g. the 1-D test slabs), fall back to the axis with
    // the smallest FULL physical extent (the device's thin dimension), which
    // is also mesh-invariant. An empty/all-zero mask yields 0 (caller falls
    // back to dx).
    if (trap_mask_.empty()) return TCAD_CONST(0.0);
    std::vector<char> px(g_.nx, 0), py(g_.ny, 0), pz(g_.nz, 0);
    for (size_t k = 0; k < g_.nz; ++k)
        for (size_t j = 0; j < g_.ny; ++j)
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (idx < trap_mask_.size() && trap_mask_[idx]) {
                    px[i] = 1; py[j] = 1; pz[k] = 1;
                }
            }
    size_t cx = 0, cy = 0, cz = 0;
    for (size_t i = 0; i < g_.nx; ++i) cx += px[i];
    for (size_t j = 0; j < g_.ny; ++j) cy += py[j];
    for (size_t k = 0; k < g_.nz; ++k) cz += pz[k];
    if (cx == 0 || cy == 0 || cz == 0) return TCAD_CONST(0.0);   // no masked nodes
    const real_t ex = (real_t)cx * g_.dx, ey = (real_t)cy * g_.dy,
                 ez = (real_t)cz * g_.dz;
    const bool span_x = (cx == g_.nx), span_y = (cy == g_.ny), span_z = (cz == g_.nz);
    // Embedded layer: choose among the non-spanning axes (smallest extent).
    if (!span_x || !span_y || !span_z) {
        real_t best = -TCAD_CONST(1.0);
        if (!span_x) best = ex;
        if (!span_y && (best < TCAD_CONST(0.0) || ey < best)) best = ey;
        if (!span_z && (best < TCAD_CONST(0.0) || ez < best)) best = ez;
        return best;
    }
    // Bulk mask: smallest full physical extent.
    real_t best = ex;
    if (ey < best) best = ey;
    if (ez < best) best = ez;
    return best;
}

void PoissonSolver::set_ferroelectric_polar_axis(int axis) {
    // Polar axis 0 = x, 1 = y, 2 = z; clamped to the valid range.
    if (axis < 0) axis = 0;
    if (axis > 2) axis = 2;
    fe_axis_ = axis;
}

real_t PoissonSolver::e_field_component(const std::vector<real_t>& phi,
                                        size_t i, size_t j, size_t k, int axis) const {
    // E_axis = -d(phi)/d(axis): central differences interior, one-sided at
    // the domain boundary — the same differencing template as the legacy
    // Ex code and compute_electric_field. Neighbor strides: x -> +/-1,
    // y -> +/-nx, z -> +/-nx*ny (row-major grid, g_.index(i,j,k)).
    const size_t idx = g_.index(i, j, k);
    if (axis == 0) {
        if (i > 0 && i + 1 < g_.nx)
            return -(phi[idx + 1] - phi[idx - 1]) / (g_.dx_edge(i-1) + g_.dx_edge(i));
        if (i + 1 < g_.nx)
            return -(phi[idx + 1] - phi[idx]) / g_.dx_edge(i);
        if (i > 0)
            return -(phi[idx] - phi[idx - 1]) / g_.dx_edge(i-1);
    } else if (axis == 1) {
        if (j > 0 && j + 1 < g_.ny)
            return -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (g_.dy_edge(j-1) + g_.dy_edge(j));
        if (j + 1 < g_.ny)
            return -(phi[idx + g_.nx] - phi[idx]) / g_.dy_edge(j);
        if (j > 0)
            return -(phi[idx] - phi[idx - g_.nx]) / g_.dy_edge(j-1);
    } else {
        if (k > 0 && k + 1 < g_.nz)
            return -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (g_.dz_edge(k-1) + g_.dz_edge(k));
        if (k + 1 < g_.nz)
            return -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz_edge(k);
        if (k > 0)
            return -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz_edge(k-1);
    }
    return TCAD_CONST(0.0);   // degenerate (single-node axis): no field
}

real_t PoissonSolver::fe_node_volume(size_t i, size_t j, size_t k) const {
    auto width = [](size_t index, size_t count, real_t spacing,
                    const std::vector<real_t>& positions) {
        if (count == 0 || (!positions.empty() && positions.size() != count))
            throw std::invalid_argument("NLS grid position size mismatch");
        auto edge = [&](size_t n) {
            const real_t distance = positions.empty() ? spacing : positions[n+1]-positions[n];
            if (!isfinite_q(distance) || distance <= TCAD_CONST(0.0))
                throw std::invalid_argument("NLS grid spacings must be finite and positive");
            return distance;
        };
        if (count == 1) {
            if (!isfinite_q(spacing) || spacing <= TCAD_CONST(0.0))
                throw std::invalid_argument("NLS extrusion must be finite and positive");
            return spacing;
        }
        return (index > 0 ? edge(index-1)/TCAD_CONST(2.0) : TCAD_CONST(0.0))
             + (index+1 < count ? edge(index)/TCAD_CONST(2.0) : TCAD_CONST(0.0));
    };
    const real_t volume = width(i, g_.nx, g_.dx, g_.xx)
                        * width(j, g_.ny, g_.dy, g_.yx)
                        * width(k, g_.nz, g_.dz, g_.zx);
    if (!isfinite_q(volume) || volume <= TCAD_CONST(0.0))
        throw std::invalid_argument("NLS node volume overflowed or underflowed");
    return volume;
}

real_t PoissonSolver::residual_norm(const std::vector<real_t>& phi,
                                    const std::vector<real_t>& n,
                                    const std::vector<real_t>& p) {
    const size_t count = g_.npts();
    if (phi.size() != count || n.size() != count || p.size() != count)
        throw std::invalid_argument("physical Poisson residual requires full states");
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite_q(phi[i]) || !isfinite_q(n[i]) || !isfinite_q(p[i]) ||
            n[i] < TCAD_CONST(0.0) || p[i] < TCAD_CONST(0.0))
            throw std::invalid_argument("physical Poisson residual requires finite potential and nonnegative carriers");
    }
    // Audit the physical equation, independently of the artificial D term
    // used to stabilize a Gummel iteration. Even when D*phi cancels from
    // the numerator, retaining it in ||rhs|| can hide incorrect charge.
    // Refresh state-dependent physics locally, preserving the live solve.
    PoissonSolver physical(*this);
    physical.boltzmann_lin_ = false;
    physical.set_leakage_field(phi);
    physical.assemble(n, p);
    std::vector<real_t> Ax = physical.A_.apply(phi);
    real_t num = TCAD_CONST(0.0), den = TCAD_CONST(0.0);
    for (size_t i = 0; i < count; ++i) {
        real_t r = Ax[i] - physical.rhs_[i];
        num += r * r;
        den += physical.rhs_[i] * physical.rhs_[i];
    }
    if (!isfinite_q(num) || !isfinite_q(den))
        throw std::invalid_argument("physical Poisson residual overflow or nonfinite equation");
    return sqrt_q(num) / (sqrt_q(den) + TCAD_CONST(1.0e-300));
}

real_t PoissonSolver::scaled_residual_norm(const std::vector<real_t>& phi,
                                           const std::vector<real_t>& n,
                                           const std::vector<real_t>& p,
                                           real_t thermal_voltage) const {
    const size_t count = g_.npts();
    if (phi.size() != count || n.size() != count || p.size() != count ||
        !isfinite_q(thermal_voltage) || thermal_voltage <= TCAD_CONST(0.0))
        throw std::invalid_argument("physical Poisson audit requires full states and finite positive VT");
    for (size_t i = 0; i < count; ++i) {
        if (!isfinite_q(phi[i]) || !isfinite_q(n[i]) || !isfinite_q(p[i]) ||
            n[i] < TCAD_CONST(0.0) || p[i] < TCAD_CONST(0.0))
            throw std::invalid_argument("physical Poisson audit requires finite potential and nonnegative carriers");
    }
    PoissonSolver physical(*this);
    physical.boltzmann_lin_ = false;
    physical.set_leakage_field(phi);
    physical.assemble(n, p);
    const auto& rows = physical.A_.row_offsets();
    const auto& cols = physical.A_.col_indices();
    const auto& values = physical.A_.vals();
    real_t worst = TCAD_CONST(0.0);
    for (size_t i = 0; i < count; ++i) {
        real_t applied = TCAD_CONST(0.0), stiffness = TCAD_CONST(0.0);
        for (size_t j = rows[i]; j < rows[i + 1]; ++j) {
            applied += values[j] * phi[cols[j]];
            stiffness += abs_q(values[j]);
        }
        // Dirichlet and vacuum rows are voltage constraints, not charge
        // balances. Never scale them by the imposed absolute potential.
        const bool voltage_row = dirichlet_bc_.count(i) || eps_[i] < EPSILON;
        const real_t scale = voltage_row ? thermal_voltage :
            thermal_voltage * stiffness +
            QE * charge_volume_fraction_[i] * (abs_q(n[i]) + abs_q(p[i]) + abs_q(Nd_minus_Na_[i])) +
            abs_q(physical.rhs_[i]);
        const real_t residual = abs_q(applied - physical.rhs_[i]);
        if (!isfinite_q(scale) || !isfinite_q(residual) || scale < TCAD_CONST(0.0))
            throw std::invalid_argument("physical Poisson audit overflow or nonfinite equation");
        // An unconstrained row with neither stiffness nor charge can only
        // pass when its equation is exactly zero; no dimensional tiny floor.
        const real_t value = scale > TCAD_CONST(0.0) ? residual / scale :
            (residual == TCAD_CONST(0.0) ? TCAD_CONST(0.0) : TCAD_CONST(1.0));
        worst = std::max(worst, value);
    }
    return worst;
}

void PoissonSolver::set_oxide_traps(const std::vector<real_t>& Q_ot) {
    if (!Q_ot.empty() && Q_ot.size() != g_.npts())
        throw std::invalid_argument("oxide trap charge size mismatch");
    for (real_t value : Q_ot)
        if (!isfinite_q(value))
            throw std::invalid_argument("oxide trap charge must be finite");
    Q_ot_ = Q_ot;          // [C/m^3], persistent (evolved by caller)
}

void PoissonSolver::set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt) {
    if (!isfinite_q(tau0) || !isfinite_q(E0) || !isfinite_q(dt) ||
        tau0 <= TCAD_CONST(0.0) || E0 < TCAD_CONST(0.0) || dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("NLS requires finite tau0>0, E0>=0 and dt>0");
    fe_nls_tau0_ = tau0;   // P3: Merz tau(E) = tau0*exp(E0/|E|)
    fe_nls_E0_ = E0;
    fe_nls_dt_ = dt;
}

void PoissonSolver::set_leakage(const std::vector<char>& mask,
                                real_t C_pf, real_t B_pf, real_t phi_t,
                                real_t C_fn, real_t B_fn, real_t phi_b,
                                real_t E_floor, real_t sigma_cap) {
    leak_mask_ = mask;
    leak_C_pf_ = C_pf; leak_B_pf_ = B_pf; leak_phi_t_ = phi_t;
    leak_C_fn_ = C_fn; leak_B_fn_ = B_fn; leak_phi_b_ = phi_b;
    leak_E_floor_ = E_floor;
    leak_sigma_cap_ = sigma_cap;
}

void PoissonSolver::set_leakage_field(const std::vector<real_t>& phi) {
    // P2.2: cache phi and compute per-node |E| via central differences so the
    // field-dependent leakage conductance can be applied in assemble() without
    // changing its signature. No-op when leakage is disabled (empty mask).
    const size_t masked_count = std::min(g_.npts(), leak_mask_.size());
    const bool reads_field = g_.npts() > 1 && std::any_of(
        leak_mask_.begin(), leak_mask_.begin() + masked_count,
        [](char value) { return value != 0; });
    if (reads_field && phi.size() < g_.npts())
        throw std::invalid_argument("leakage potential must cover all nodes");
    for (real_t value : phi)
        if (!isfinite_q(value))
            throw std::invalid_argument("leakage potential must be finite");
    leak_phi_ = phi;
    if (leak_mask_.empty()) return;
    const size_t N = g_.npts();
    leak_E_mag_.assign(N, TCAD_CONST(0.0));
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (idx >= leak_mask_.size() || !leak_mask_[idx]) continue;
                // Node field: actual coordinates on graded axes, legacy arithmetic otherwise.
                const real_t Ex = structured_node_field(phi, idx, i, 1, g_.nx, g_.xx, g_.dx);
                const real_t Ey = structured_node_field(phi, idx, j, g_.nx, g_.ny, g_.yx, g_.dy);
                const real_t Ez = structured_node_field(phi, idx, k, g_.nx*g_.ny, g_.nz, g_.zx, g_.dz);
                leak_E_mag_[idx] = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
            }
        }
    }
}

void PoissonSolver::update_ferroelectric_polarization_transient(const std::vector<real_t>& phi, real_t dt) {
    if (!fe_enabled_) return;
    if (!isfinite_q(dt) || dt <= TCAD_CONST(0.0))
        throw std::invalid_argument("FE transient dt must be finite and positive");

    // Preisach is a rate-independent turning-point model.  NLS is rate
    // dependent through its Merz dwell, so use the actual accepted BE step
    // instead of the static protocol dwell configured for a bias sweep.  Both
    // paths update their persistent memory exactly once per accepted step;
    // failed electrical attempts restore the DeviceSimulator checkpoint.
    if (fe_model_ == 1 || fe_model_ == 3) {
        update_ferroelectric_polarization(phi);
        return;
    }
    if (fe_model_ == 2) {
        const real_t saved_dwell = fe_nls_dt_;
        fe_nls_dt_ = dt;
        try {
            update_ferroelectric_polarization(phi);
        } catch (...) {
            fe_nls_dt_ = saved_dwell;
            throw;
        }
        fe_nls_dt_ = saved_dwell;
        return;
    }
    if (!isfinite_q(fe_gamma_) || fe_gamma_ <= TCAD_CONST(0.0))
        throw std::invalid_argument("LK FE transient requires finite positive gamma");

    const size_t N = g_.npts();
    if (!isfinite_q(fe_alpha_) || !isfinite_q(fe_beta_) || fe_beta_ <= TCAD_CONST(0.0) ||
        !isfinite_q(fe_E_bi_) || phi.size() != N || fe_polarization_.size() != 3*N ||
        !std::all_of(phi.begin(), phi.end(), isfinite_q) ||
        !std::all_of(fe_polarization_.begin(), fe_polarization_.end(), isfinite_q))
        throw std::invalid_argument("LK requires finite fields/coefficients and positive beta");

    // Backward Euler in each vector component, at the previous electrical
    // field: beta*P^3 + (alpha+gamma/dt)*P = gamma/dt*P_old + E.
    // This remains an electrical/FE split, but no longer seeds pristine P at
    // Ps or takes an unstable explicit step. For a nonconvex cubic retain the
    // old stable branch while it exists; switch only when that branch vanishes.
    // Undriven pristine components stay zero by symmetry.
    const real_t rate = fe_gamma_ / dt;
    auto implicit_component = [&](real_t old, real_t field, real_t alpha) {
        const real_t a = alpha + rate;
        const real_t b = rate * old + field;
        if (!isfinite_q(a) || !isfinite_q(b))
            throw std::invalid_argument("LK backward-Euler coefficients overflowed");
        if (old == TCAD_CONST(0.0) && field == TCAD_CONST(0.0)) return TCAD_CONST(0.0);
        const real_t turning = a < TCAD_CONST(0.0) ? sqrt_q(-a / (TCAD_CONST(3.0) * fe_beta_)) : TCAD_CONST(0.0);
        const real_t limit = a < TCAD_CONST(0.0) ? -(fe_beta_*turning*turning + a)*turning : TCAD_CONST(0.0);
        real_t sign = b < TCAD_CONST(0.0) ? -TCAD_CONST(1.0) : TCAD_CONST(1.0);
        if (a < TCAD_CONST(0.0)) {
            if (old > TCAD_CONST(0.0) && b >= -limit) sign = TCAD_CONST(1.0);
            if (old < TCAD_CONST(0.0) && b <= limit) sign = -TCAD_CONST(1.0);
        }
        const real_t target = sign * b;
        auto residual = [&](real_t q) { return (fe_beta_*q*q + a)*q - target; };
        real_t lo = turning;
        // Scale the bracket from the coefficients instead of an arbitrary
        // polarization cap. The outer stable branch is monotonic.
        real_t hi = std::max(abs_q(old), turning);
        if (a >= TCAD_CONST(0.0)) {
            // For a monotone cubic both b/a and cbrt(b/beta) bound |P|
            // from above. A coefficient-only sqrt(a/beta) bracket creates
            // a spurious polarization floor after a fixed number of bisections
            // when the field is many orders smaller than these coefficients.
            hi = b == TCAD_CONST(0.0) ? TCAD_CONST(0.0) :
                exp_q((log_q(abs_q(b)) - log_q(fe_beta_)) / TCAD_CONST(3.0));
            if (a > TCAD_CONST(0.0)) hi = std::min(hi, abs_q(b) / a);
        } else {
            hi = std::max(hi, sqrt_q(abs_q(a) / fe_beta_));
            if (b != TCAD_CONST(0.0))
                hi = std::max(hi, exp_q((log_q(abs_q(b)) - log_q(fe_beta_)) / TCAD_CONST(3.0)));
        }
        if (hi == TCAD_CONST(0.0)) return TCAD_CONST(0.0);
        while (residual(hi) < TCAD_CONST(0.0)) {
            hi *= TCAD_CONST(2.0);
            if (!isfinite_q(hi)) throw std::invalid_argument("LK root bracket overflowed");
        }
        for (int iteration = 0; iteration < 160; ++iteration) {
            const real_t mid = lo + (hi - lo) / TCAD_CONST(2.0);
            if (mid == lo || mid == hi) break;
            if (residual(mid) > TCAD_CONST(0.0)) hi = mid;
            else lo = mid;
        }
        return sign * (lo + (hi - lo) / TCAD_CONST(2.0));
    };
    auto candidate = fe_polarization_;
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!fe_mask_[idx]) {
                    candidate[3*idx + 0] = TCAD_CONST(0.0);
                    candidate[3*idx + 1] = TCAD_CONST(0.0);
                    candidate[3*idx + 2] = TCAD_CONST(0.0);
                    continue;
                }
                for (int c = 0; c < 3; ++c) {
                    real_t field = e_field_component(phi, i, j, k, c);
                    real_t alpha = fe_alpha_;
                    if (c == fe_axis_) {
                        field -= fe_E_bi_;
                        if (fe_eps_fe_ > TCAD_CONST(0.0)) alpha += TCAD_CONST(1.0) / (fe_eps_fe_ * EPS0);
                    }
                    candidate[3*idx+c] = implicit_component(fe_polarization_[3*idx+c], field, alpha);
                }
            }
        }
    }
    fe_polarization_ = std::move(candidate);
}

void PoissonSolver::assemble_newton(const std::vector<real_t>& phi,
                                    const std::vector<real_t>& n,
                                    const std::vector<real_t>& p,
                                    real_t VT,
                                    SparseMatrix& J,
                                    Vector& F) const {
    if (!assembled_) throw std::runtime_error("System not assembled");

    J = SparseMatrix(A_);  // copy CSR structure
    F.assign(g_.npts(), TCAD_CONST(0.0));

    for (size_t i = 0; i < g_.npts(); ++i) {
        if (is_dirichlet_[i]) {
            F[i] = phi[i] - dirichlet_bc_.at(i);
        } else {
            // Add -(q/VT)*(n+p) to diagonal of J
            for (size_t idx = J.row_offsets()[i]; idx < J.row_offsets()[i + 1]; ++idx) {
                if (J.col_indices()[idx] == i) {
                    J.vals_mut()[idx] += (QE / VT) * (n[i] + p[i]);
                    break;
                }
            }
            // F = A_*phi - rhs_  where rhs_ = QE*(p-n+Nd-Na)
            real_t sum = TCAD_CONST(0.0);
            for (size_t idx = A_.row_offsets()[i]; idx < A_.row_offsets()[i + 1]; ++idx) {
                sum += A_.vals()[idx] * phi[A_.col_indices()[idx]];
            }
            F[i] = sum + QE * (p[i] - n[i] + Nd_minus_Na_[i]);
        }
    }
}

bool PoissonSolver::solve(std::vector<real_t>& phi) {
    if (!assembled_) throw std::runtime_error("System not assembled");
    if (phi.size() != g_.npts()) phi.assign(g_.npts(), TCAD_CONST(0.0));

    Vector x(phi.begin(), phi.end());

    // --- Jacobi smoothing to provide a good initial guess for iterative solvers ---
    try {
        LinearSolver jacobi_solver({SolverType::JACOBI, 20, TCAD_CONST(1e-6), 30, false});
        jacobi_solver.solve(A_, rhs_, x);
    } catch (...) {
        // If Jacobi fails, continue with original guess
    }
    try {
        solver_.solve(A_, rhs_, x);
        // std::cerr << "Poisson solved, max |x|=" << (double)norm_l2(x) << std::endl;
        for (size_t i = 0; i < g_.npts(); ++i) phi[i] = x[i];
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Poisson solve failed: " << e.what() << std::endl;
        return false;
    }
}

void PoissonSolver::compute_electric_field(const std::vector<real_t>& phi,
                                           std::vector<real_t>& Ex,
                                           std::vector<real_t>& Ey,
                                           std::vector<real_t>& Ez) const {
    Ex.assign(g_.npts(), TCAD_CONST(0.0));
    Ey.assign(g_.npts(), TCAD_CONST(0.0));
    Ez.assign(g_.npts(), TCAD_CONST(0.0));

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                Ex[idx] = e_field_component(phi, i, j, k, 0);
                Ey[idx] = e_field_component(phi, i, j, k, 1);
                Ez[idx] = e_field_component(phi, i, j, k, 2);
            }
        }
    }
}

} // namespace tcad
