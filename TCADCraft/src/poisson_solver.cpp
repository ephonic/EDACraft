#include "poisson_solver.h"
#include <iostream>

namespace tcad {

PoissonSolver::PoissonSolver(const Grid3D& grid)
    : g_(grid), eps_(grid.npts(), EPS0 * 11.7Q), // Default: Silicon
      Nd_minus_Na_(grid.npts(), 0.0Q),
      charge_volume_fraction_(grid.npts(), 1.0Q),
      is_dirichlet_(grid.npts(), 0),
      solver_(LinearSolver(LinearSolver::default_poisson_options())) {}

void PoissonSolver::set_permittivity(const std::vector<real_t>& eps) {
    if (eps.size() != g_.npts()) throw std::invalid_argument("Permittivity size mismatch");
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
    edge_eps_x_plus_ = x_plus;
    edge_eps_x_minus_ = x_minus;
    edge_eps_y_plus_ = y_plus;
    edge_eps_y_minus_ = y_minus;
    edge_eps_z_plus_ = z_plus;
    edge_eps_z_minus_ = z_minus;
}

void PoissonSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    if (Nd_minus_Na.size() != g_.npts()) throw std::invalid_argument("Doping size mismatch");
    Nd_minus_Na_ = Nd_minus_Na;
}

void PoissonSolver::set_charge_volume_fraction(
    const std::vector<real_t>& fraction) {
    if (fraction.size() != g_.npts())
        throw std::invalid_argument("Charge volume fraction size mismatch");
    for (real_t value : fraction) {
        if (value < 0.0Q || value > 1.0Q)
            throw std::invalid_argument("Charge volume fraction must be in [0,1]");
    }
    charge_volume_fraction_ = fraction;
}

void PoissonSolver::set_solver_options(const SolverOptions& opt) {
    solver_ = LinearSolver(opt);
}

void PoissonSolver::set_dirichlet(const std::map<size_t, real_t>& bc) {
    dirichlet_bc_ = bc;
    is_dirichlet_.assign(g_.npts(), 0);
    for (const auto& [idx, val] : bc) {
        if (idx >= g_.npts()) throw std::out_of_range("Dirichlet index out of bounds");
        is_dirichlet_[idx] = true;
    }
}

void PoissonSolver::set_neumann_faces(char face) {
    // Neumann BC means d(phi)/dn = 0, implemented by mirroring
    // This is a placeholder for future implementation
    // For now, zero-field Neumann is naturally handled by omitting boundary flux
}

real_t PoissonSolver::cx_plus(size_t idx) const {
    size_t i = idx % g_.nx;
    if (i + 1 >= g_.nx) return 0.0Q;
    real_t ec = g_.dx_edge(i) * g_.dx_cell(i);
    if (!edge_eps_x_plus_.empty() && edge_eps_x_plus_[idx] > 0.0Q) {
        return edge_eps_x_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + 1];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + 1] / eps_sum / ec;
}

real_t PoissonSolver::cx_minus(size_t idx) const {
    size_t i = idx % g_.nx;
    if (i == 0) return 0.0Q;
    real_t ec = g_.dx_edge(i-1) * g_.dx_cell(i);
    if (!edge_eps_x_minus_.empty() && edge_eps_x_minus_[idx] > 0.0Q) {
        return edge_eps_x_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - 1];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - 1] / eps_sum / ec;
}

real_t PoissonSolver::cy_plus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j + 1 >= g_.ny) return 0.0Q;
    real_t ec = g_.dy_edge(j) * g_.dy_cell(j);
    if (!edge_eps_y_plus_.empty() && edge_eps_y_plus_[idx] > 0.0Q) {
        return edge_eps_y_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + g_.nx] / eps_sum / ec;
}

real_t PoissonSolver::cy_minus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j == 0) return 0.0Q;
    real_t ec = g_.dy_edge(j-1) * g_.dy_cell(j);
    if (!edge_eps_y_minus_.empty() && edge_eps_y_minus_[idx] > 0.0Q) {
        return edge_eps_y_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - g_.nx] / eps_sum / ec;
}

real_t PoissonSolver::cz_plus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k + 1 >= g_.nz) return 0.0Q;
    real_t ec = g_.dz_edge(k) * g_.dz_cell(k);
    if (!edge_eps_z_plus_.empty() && edge_eps_z_plus_[idx] > 0.0Q) {
        return edge_eps_z_plus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx * g_.ny];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + g_.nx * g_.ny] / eps_sum / ec;
}

real_t PoissonSolver::cz_minus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k == 0) return 0.0Q;
    real_t ec = g_.dz_edge(k-1) * g_.dz_cell(k);
    if (!edge_eps_z_minus_.empty() && edge_eps_z_minus_[idx] > 0.0Q) {
        return edge_eps_z_minus_[idx] / ec;
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx * g_.ny];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - g_.nx * g_.ny] / eps_sum / ec;
}

void PoissonSolver::assemble(const std::vector<real_t>& n, const std::vector<real_t>& p) {
    if (n.size() != g_.npts() || p.size() != g_.npts())
        throw std::invalid_argument("Carrier density size mismatch");

    A_ = SparseMatrix(g_.npts());
    rhs_.assign(g_.npts(), 0.0Q);

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_dirichlet_[idx]) {
                    A_.add_entry(idx, idx, 1.0Q);
                    rhs_[idx] = dirichlet_bc_.at(idx);
                    continue;
                }
                // Vacuum / outside device: zero permittivity -> freeze potential
                if (eps_[idx] < EPSILON) {
                    A_.add_entry(idx, idx, 1.0Q);
                    rhs_[idx] = 0.0Q;
                    continue;
                }

                real_t center = 0.0Q;
                real_t c;

                // x-direction
                c = cx_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + 1, c); center -= c; }
                c = cx_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - 1, c); center -= c; }

                // y-direction
                c = cy_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + g_.nx, c); center -= c; }
                c = cy_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - g_.nx, c); center -= c; }

                // z-direction
                c = cz_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + g_.nx * g_.ny, c); center -= c; }
                c = cz_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - g_.nx * g_.ny, c); center -= c; }

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
                    real_t phi_old = leak_phi_.empty() ? 0.0Q :
                        (idx < leak_phi_.size() ? leak_phi_[idx] : 0.0Q);
                    real_t EFn = (ohmic_EFn_.count(idx)) ? ohmic_EFn_.at(idx) : 0.0Q;
                    real_t EFp = (ohmic_EFp_.count(idx)) ? ohmic_EFp_.at(idx) : 0.0Q;
                    real_t arg_n = (phi_old - EFn) / VT_;
                    real_t arg_p = -(phi_old + EFp) / VT_;
                    if (arg_n > 50.0Q) arg_n = 50.0Q;
                    if (arg_n < -50.0Q) arg_n = -50.0Q;
                    if (arg_p > 50.0Q) arg_p = 50.0Q;
                    if (arg_p < -50.0Q) arg_p = -50.0Q;
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
                    const real_t kT_eV = 0.02585Q;   // kT at 300 K [eV]
                    // Use the cached phi from set_leakage_field (or set_trap_field).
                    real_t phi_val = 0.0Q;
                    if (!leak_phi_.empty() && idx < leak_phi_.size())
                        phi_val = leak_phi_[idx];
                    // E_F - E_i [eV] == phi [V] numerically (see comment above).
                    real_t arg = (trap_E_t_ - phi_val) / kT_eV;
                    real_t f_t = 1.0Q / (1.0Q + exp_q(arg));
                    real_t dE = 1.0Q;   // effective trap energy range [eV]
                    // Q_it in [C/m^2], divide by the trap layer thickness to
                    // get a mesh-invariant [C/m^3] for the RHS.
                    real_t D_it_m2 = trap_D_it_ * 1.0e4Q;   // cm^-2 -> m^-2
                    real_t t_layer = (trap_layer_thickness_ > 0.0Q)
                                     ? trap_layer_thickness_ : g_.dx;
                    real_t Q_it = -QE * D_it_m2 * dE * (f_t - 0.5Q) / t_layer;
                    rhs_[idx] += Q_it;
                }
                if (!Q_ot_.empty() && idx < Q_ot_.size()) {
                    rhs_[idx] += Q_ot_[idx];   // bulk oxide trap charge [C/m^3]
                }

                // Ferroelectric polarization bound charge: -div(P) added to RHS.
                // Vector divergence div(P) = dPx/dx + dPy/dy + dPz/dz, each
                // component differenced along its OWN axis. fe_polarization_ is
                // interleaved [Px,Py,Pz] per node (length 3*npts).
                // (A4: the prior scalar form differenced the SAME scalar on all
                // three axes, which is physically wrong; the vector form fixes it.)
                if (fe_enabled_ && fe_mask_[idx]) {
                    auto Pxc = [this](size_t id){ return fe_polarization_[3*id + 0]; };
                    auto Pyc = [this](size_t id){ return fe_polarization_[3*id + 1]; };
                    auto Pzc = [this](size_t id){ return fe_polarization_[3*id + 2]; };
                    real_t divP = 0.0Q;
                    // div(P) = dPx/dx + dPy/dy + dPz/dz (correct central difference).
                    // BUG FIX (comments2.docx): the old code used a MINUS sign on
                    // the lower-neighbor term, turning the divergence into a second
                    // difference (Laplacian) for interior nodes — which injected a
                    // grossly wrong bound charge and pinned P at a non-physical value.
                    if (i + 1 < g_.nx && i > 0)
                        divP += (Pxc(idx + 1) - Pxc(idx - 1)) / (2.0Q * g_.dx);
                    else if (i + 1 < g_.nx)
                        divP += (Pxc(idx + 1) - Pxc(idx)) / g_.dx;
                    else if (i > 0)
                        divP += (Pxc(idx) - Pxc(idx - 1)) / g_.dx;
                    if (j + 1 < g_.ny && j > 0)
                        divP += (Pyc(idx + g_.nx) - Pyc(idx - g_.nx)) / (2.0Q * g_.dy);
                    else if (j + 1 < g_.ny)
                        divP += (Pyc(idx + g_.nx) - Pyc(idx)) / g_.dy;
                    else if (j > 0)
                        divP += (Pyc(idx) - Pyc(idx - g_.nx)) / g_.dy;
                    if (k + 1 < g_.nz && k > 0)
                        divP += (Pzc(idx + g_.nx * g_.ny) - Pzc(idx - g_.nx * g_.ny)) / (2.0Q * g_.dz);
                    else if (k + 1 < g_.nz)
                        divP += (Pzc(idx + g_.nx * g_.ny) - Pzc(idx)) / g_.dz;
                    else if (k > 0)
                        divP += (Pzc(idx) - Pzc(idx - g_.nx * g_.ny)) / g_.dz;
                    rhs_[idx] -= divP;
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

void PoissonSolver::assemble_thermal(const std::vector<real_t>& power_density) {
    const size_t N = g_.npts();
    A_ = SparseMatrix(N);
    rhs_.assign(N, 0.0Q);
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_dirichlet_[idx]) {
                    A_.add_entry(idx, idx, 1.0Q);
                    rhs_[idx] = dirichlet_bc_.at(idx);
                    continue;
                }
                if (eps_[idx] < EPSILON) {
                    A_.add_entry(idx, idx, 1.0Q);
                    rhs_[idx] = 0.0Q;
                    continue;
                }

                real_t center = 0.0Q;
                real_t c;

                c = cx_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + 1, c); center -= c; }
                c = cx_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - 1, c); center -= c; }
                c = cy_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + g_.nx, c); center -= c; }
                c = cy_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - g_.nx, c); center -= c; }
                c = cz_plus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx + g_.nx * g_.ny, c); center -= c; }
                c = cz_minus(idx);
                if (c != 0.0Q) { A_.add_entry(idx, idx - g_.nx * g_.ny, c); center -= c; }

                A_.add_entry(idx, idx, center);
                rhs_[idx] = -power_density[idx];
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
    fe_mask_ = fe_mask;
    fe_alpha_ = alpha;
    fe_beta_ = beta;
    fe_enabled_ = true;
    // Preserve an externally-injected persistent P (from DeviceSimulator) across
    // a GummelSolver rebuild; only allocate on first call / size mismatch.
    // Vector storage: 3*npts interleaved [Px,Py,Pz] per node.
    if (fe_polarization_.size() != 3 * g_.npts())
        fe_polarization_.assign(3 * g_.npts(), 0.0Q);
}

void PoissonSolver::update_ferroelectric_polarization(const std::vector<real_t>& phi) {
    if (!fe_enabled_) return;

    // ---- Sentaurus-compatible Preisach saturation-loop path ----
    // Sentaurus Device W-2024.09, User Guide Eq. 986-987:
    //   P = Ps*tanh(w*(E +/- Ec)),
    //   w = log((Ps+Pr)/(Ps-Pr))/(2*Ec).
    // fe_escale_ stores 1/w so the existing public Ps/Ec/Escale API remains
    // ABI compatible. Unlike the legacy one-play model below, this permits
    // saturation Ps and remanence Pr to be calibrated independently. The
    // first monotonic excursion uses a centered virgin branch; after the
    // first reversal, the two major-loop branches follow Eq. 986 exactly.
    if (fe_model_ == 3) {
        const size_t N = g_.npts();
        if (fe_play_state_.size() != 2 * N)
            fe_play_state_.assign(2 * N, 0.0Q);
        if (fe_polarization_.size() != 3 * N)
            fe_polarization_.assign(3 * N, 0.0Q);
        const real_t Ps = fe_ps_;
        const real_t Ec = fe_ec_;
        const real_t Escale = (fe_escale_ > 0.0Q) ? fe_escale_
                            : ((Ec > 0.0Q) ? Ec : 1.0Q);

        real_t E = 0.0Q, P_old = 0.0Q, E_previous = 0.0Q;
        real_t branch_accum = 0.0Q;
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    const size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    E += e_field_component(phi, i, j, k, fe_axis_);
                    P_old += fe_polarization_[3 * idx + fe_axis_];
                    E_previous += fe_play_state_[idx];
                    branch_accum += fe_play_state_[N + idx];
                    ++n_fe;
                }
        if (n_fe == 0) return;
        E /= (real_t)n_fe;
        P_old /= (real_t)n_fe;
        E_previous /= (real_t)n_fe;
        E -= fe_E_bi_;
        if (fe_eps_fe_ > 0.0Q) {
            const real_t eps0 = 8.854187817e-12Q;
            E -= P_old / (fe_eps_fe_ * eps0);
        }

        int branch = 0;
        if (branch_accum > 0.5Q * (real_t)n_fe) branch = 1;
        else if (branch_accum < -0.5Q * (real_t)n_fe) branch = -1;
        // Virgin states are encoded as +/-2. Recover them from the average.
        if (branch_accum > 1.5Q * (real_t)n_fe) branch = 2;
        else if (branch_accum < -1.5Q * (real_t)n_fe) branch = -2;

        const real_t field_tol = std::max(1.0Q, abs_q(E) * 1.0e-12Q);
        const real_t delta = E - E_previous;
        if (branch == 0 && abs_q(delta) > field_tol)
            branch = (delta > 0.0Q) ? 2 : -2;
        else if (branch == 2 && delta < -field_tol) branch = -1;
        else if (branch == -2 && delta > field_tol) branch = 1;
        else if (branch == 1 && delta < -field_tol) branch = -1;
        else if (branch == -1 && delta > field_tol) branch = 1;

        real_t P_target = P_old;
        if (abs_q(delta) > field_tol || branch == 0) {
            if (branch == 2 || branch == -2) {
                // Centered initial curve: deterministic P(0)=0 and the same
                // saturation limits as the major loop.
                P_target = Ps * tanh_q(E / (2.0Q * Escale));
            } else if (branch > 0) {
                P_target = Ps * tanh_q((E - Ec) / Escale);
            } else if (branch < 0) {
                P_target = Ps * tanh_q((E + Ec) / Escale);
            }
        }
        const real_t P = fe_relax_ * P_target + (1.0Q - fe_relax_) * P_old;
        for (size_t idx = 0; idx < N; ++idx) {
            if (!fe_mask_[idx]) {
                fe_polarization_[3 * idx + 0] = 0.0Q;
                fe_polarization_[3 * idx + 1] = 0.0Q;
                fe_polarization_[3 * idx + 2] = 0.0Q;
                fe_play_state_[idx] = 0.0Q;
                fe_play_state_[N + idx] = 0.0Q;
                continue;
            }
            fe_polarization_[3 * idx + fe_axis_] = P;
            for (int component = 0; component < 3; ++component)
                if (component != fe_axis_)
                    fe_polarization_[3 * idx + component] = 0.0Q;
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
        if (fe_play_state_.size() != N) fe_play_state_.assign(N, 0.0Q);
        if (fe_polarization_.size() != 3 * N) fe_polarization_.assign(3 * N, 0.0Q);
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
        const real_t Escale = (fe_escale_ > 0.0Q) ? fe_escale_
                            : ((Ec > 0.0Q) ? Ec : 1.0Q);
        for (size_t k = 0; k < g_.nz; ++k) {
            for (size_t j = 0; j < g_.ny; ++j) {
                for (size_t i = 0; i < g_.nx; ++i) {
                    size_t idx = g_.index(i, j, k);
                    // Reset masked-off nodes (Px=Py=Pz=0, play=0).
                    if (!fe_mask_[idx]) {
                        fe_polarization_[3*idx+0] = 0.0Q;
                        fe_polarization_[3*idx+1] = 0.0Q;
                        fe_polarization_[3*idx+2] = 0.0Q;
                        fe_play_state_[idx] = 0.0Q;
                        continue;
                    }
                    // E = -grad(phi) along the polar axis fe_axis_ (scalar
                    // Preisach; the vector generalisation would run three
                    // independent play operators, matching L-K's A4 form).
                    // (P0-1 fix: was hard-wired to the x component, so a
                    // z-stacked FeFET never drove the polarization.)
                    // P2.1: apply the internal/imprint field offset E_bi so the
                    // effective switching drive is E_eff = E - E_bi. This models
                    // a built-in bias / imprint that breaks +/- symmetry.
                    real_t E = e_field_component(phi, i, j, k, fe_axis_);
                    E -= fe_E_bi_;   // imprint / built-in offset (P2.1)
                    // Depolarization field (comments2.docx P3):
                    // E_dep = -P_current / (eps_fe * eps_0), opposes P.
                    if (fe_eps_fe_ > 0.0Q) {
                        real_t P_cur = fe_polarization_[3*idx+fe_axis_];
                        real_t eps0 = 8.854187817e-12Q;
                        E -= P_cur / (fe_eps_fe_ * eps0);
                    }

                    // Play operator update: w follows E but lags by Ec.
                    real_t w = fe_play_state_[idx];
                    if (E > w + Ec)       w = E - Ec;
                    else if (E < w - Ec)  w = E + Ec;
                    // else: w unchanged (inside the deadband -> memory)
                    fe_play_state_[idx] = w;

                    // Saturating output: P = Ps * tanh((E - w)/Escale).
                    real_t arg = (E - w) / Escale;
                    real_t P_new = Ps * tanh_q(arg);
                    // Under-relaxation (comments2.docx): blend new and old P.
                    real_t P_old_p = fe_polarization_[3*idx+fe_axis_];
                    fe_polarization_[3*idx+fe_axis_] = fe_relax_ * P_new + (1.0Q - fe_relax_) * P_old_p;
                    // Off-axis components stay 0 (scalar Preisach along fe_axis_).
                    for (int c = 0; c < 3; ++c)
                        if (c != fe_axis_) fe_polarization_[3*idx+c] = 0.0Q;
                }
            }
        }
        return;
    }

    // ---- NLS (Nucleation-Limited Switching) path (P3, model==2) ----
    // Suitable for wurtzite ferroelectrics like AlScN whose 180° switching is
    // domain-nucleation-limited rather than homogeneous (LK) or play-operator
    // (Preisach). Under NLS the switching dynamics follow Merz's law:
    //     tau(E) = tau0 * exp(E0 / |E|)     [switching time, |E| in V/m]
    // In quasi-static operation each bias step applies an effective
    // dwell time dt_eff (a configurable fraction of the external sweep), so the
    // polarization relaxes toward the field-favored target
    //     P_target = sign(E_eff) * Ps
    // by a fractional amount f = 1 - exp(-dt_eff / tau(E)). Crucially, near the
    // coercive field |E|~Ec, tau(E) is large, so f is small and the loop has a
    // FINITE slope (S-shaped) rather than an instantaneous vertical jump. This
    // fixes the "switching is completely vertical" failure mode reported for
    // AlScN FeFETs. Off-axis components stay 0 (scalar NLS along fe_axis_).
    // The state P persists across solve() so the loop has path-dependent
    // memory. The state is advanced exactly ONCE per Gummel solve() call (see
    // GummelSolver::solve), so the physical dwell time is decoupled from the
    // iteration count (P0-2 fix).
    if (fe_model_ == 2) {
        const size_t N = g_.npts();
        if (fe_polarization_.size() != 3 * N) fe_polarization_.assign(3 * N, 0.0Q);
        const real_t Ps = fe_ps_;
        const real_t Ec = fe_ec_;
        const real_t tau0 = fe_nls_tau0_;     // characteristic switching time [s]
        const real_t E0 = fe_nls_E0_;         // Merz activation field [V/m]
        // Effective dwell time per bias step. In quasi-static operation this is
        // not a physical time but a relaxation strength parameter: larger =>
        // faster (more vertical) switching. Default 1e-6 s gives moderate slope.
        const real_t dt_eff = fe_nls_dt_;
        // NLS is a domain-ensemble (volume-averaged) switching model, not a
        // phase-field model.  Advancing every mesh node from its local field
        // let tiny discretisation variations create artificial domains; their
        // bound charge then reversed the local field on the return branch and
        // drove P back to +Ps under a negative applied voltage.  Use the FE
        // volume-average drive and state, as in compact NLS formulations, and
        // write one uniform ensemble polarization into the FE region.
        real_t E = 0.0Q, E_abs_peak = 0.0Q, P_old = 0.0Q;
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    real_t E_local = e_field_component(phi, i, j, k, fe_axis_);
                    E += E_local;
                    if (abs_q(E_local) > E_abs_peak) E_abs_peak = abs_q(E_local);
                    P_old += fe_polarization_[3*idx+fe_axis_];
                    ++n_fe;
                }
        if (n_fe == 0) return;
        E /= (real_t)n_fe;
        P_old /= (real_t)n_fe;
        real_t uniform_field_offset = fe_E_bi_;
        E -= fe_E_bi_;
        if (fe_eps_fe_ > 0.0Q) {
            const real_t eps0 = 8.854187817e-12Q;
            real_t E_dep = P_old / (fe_eps_fe_ * eps0);
            E -= E_dep;
            uniform_field_offset += E_dep;
        }

        real_t P_target = (E > 0.0Q) ? Ps : ((E < 0.0Q) ? -Ps : P_old);
        // Fringing fields in a finite FeFET partly cancel in the signed
        // volume average.  NLS is nucleation-limited: the highest-field part
        // of the film sets the Merz nucleation rate, while the volume-average
        // sign selects the favored branch.
        real_t E_peak_eff = E_abs_peak - abs_q(uniform_field_offset);
        if (E_peak_eff < 0.0Q) E_peak_eff = 0.0Q;
        real_t Eabs = std::max(abs_q(E), E_peak_eff);
        real_t f = 0.0Q;
        if (Eabs > Ec * 0.1Q) {
            real_t tau = tau0 * exp_q(E0 / Eabs);
            real_t r = dt_eff / tau;
            f = (r > 50.0Q) ? 1.0Q : 1.0Q - exp_q(-r);
        }
        real_t P_step = P_old + f * (P_target - P_old);
        real_t P = fe_relax_ * P_step + (1.0Q - fe_relax_) * P_old;
        if (P > Ps) P = Ps;
        if (P < -Ps) P = -Ps;
        for (size_t idx = 0; idx < N; ++idx) {
            if (!fe_mask_[idx]) {
                fe_polarization_[3*idx+0] = 0.0Q;
                fe_polarization_[3*idx+1] = 0.0Q;
                fe_polarization_[3*idx+2] = 0.0Q;
                continue;
            }
            fe_polarization_[3*idx+fe_axis_] = P;
            for (int c = 0; c < 3; ++c)
                if (c != fe_axis_) fe_polarization_[3*idx+c] = 0.0Q;
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
        const real_t Ps = sqrt_q(-fe_alpha_ / fe_beta_);
        const real_t P_sp = sqrt_q(-fe_alpha_ / (3.0Q * fe_beta_));
        const real_t Ec = (2.0Q / 3.0Q) * abs_q(fe_alpha_) * P_sp;

        // This is a single-domain LK compact model, not a phase-field/domain-
        // wall solver.  Per-node branch updates amplified round-off into
        // alternating mesh domains whose artificial div(P) locked the branch.
        // Use the volume-average field and state independently for all three
        // vector components, and write one deterministic domain state to the
        // FE film.  This retains simultaneous Px/Py response in a 2-D field.
        real_t E[3] = {0.0Q, 0.0Q, 0.0Q};
        real_t P_old[3] = {0.0Q, 0.0Q, 0.0Q};
        size_t n_fe = 0;
        for (size_t k = 0; k < g_.nz; ++k)
            for (size_t j = 0; j < g_.ny; ++j)
                for (size_t i = 0; i < g_.nx; ++i) {
                    size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) continue;
                    for (int c = 0; c < 3; ++c) {
                        E[c] += e_field_component(phi, i, j, k, c);
                        P_old[c] += fe_polarization_[3*idx + c];
                    }
                    ++n_fe;
                }
        if (n_fe == 0) return;
        for (int c = 0; c < 3; ++c) {
            E[c] /= (real_t)n_fe;
            P_old[c] /= (real_t)n_fe;
        }
        E[fe_axis_] -= fe_E_bi_;
        if (fe_eps_fe_ > 0.0Q)
            E[fe_axis_] -= P_old[fe_axis_] / (fe_eps_fe_ * 8.854187817e-12Q);

        real_t P[3];
        for (int c = 0; c < 3; ++c) {
            P[c] = P_old[c];
            if (abs_q(P[c]) < 1.0e-18Q) {
                if (E[c] > 1.0Q) P[c] = Ps;
                else if (E[c] < -1.0Q) P[c] = -Ps;
            } else if (Ec > 0.0Q && abs_q(E[c]) > Ec && P[c] * E[c] < 0.0Q) {
                P[c] = (E[c] > 0.0Q) ? Ps : -Ps;
            }
            for (int iter = 0; iter < 20; ++iter) {
                real_t f = fe_alpha_ * P[c] + fe_beta_ * P[c] * P[c] * P[c] - E[c];
                real_t df = fe_alpha_ + 3.0Q * fe_beta_ * P[c] * P[c];
                if (abs_q(df) < 1e-30Q) break;
                real_t dP = f / df;
                P[c] -= dP;
                if (abs_q(dP) < 1e-15Q * std::max(abs_q(P[c]), 1.0Q)) break;
            }
            if (P[c] > Ps) P[c] = Ps;
            if (P[c] < -Ps) P[c] = -Ps;
            P[c] = fe_relax_ * P[c] + (1.0Q - fe_relax_) * P_old[c];
        }

        for (size_t idx = 0; idx < N; ++idx) {
            for (int c = 0; c < 3; ++c)
                fe_polarization_[3*idx + c] = fe_mask_[idx] ? P[c] : 0.0Q;
        }
        return;
    }

    const real_t Ps = sqrt_q(-fe_alpha_ / fe_beta_);  // double-well minimum
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!fe_mask_[idx]) {
                    fe_polarization_[3*idx + 0] = 0.0Q;
                    fe_polarization_[3*idx + 1] = 0.0Q;
                    fe_polarization_[3*idx + 2] = 0.0Q;
                    continue;
                }

                // Compute E = -grad(phi) components
                real_t Ex = 0.0Q, Ey = 0.0Q, Ez = 0.0Q;
                if (i > 0 && i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                else if (i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                else if (i > 0)
                    Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                if (j > 0 && j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (2.0Q * g_.dy);
                else if (j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
                else if (j > 0)
                    Ey = -(phi[idx] - phi[idx - g_.nx]) / g_.dy;
                if (k > 0 && k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (2.0Q * g_.dz);
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
                if (fe_eps_fe_ > 0.0Q) {
                    real_t eps0 = 8.854187817e-12Q;
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
                const real_t P_sp = sqrt_q(-fe_alpha_ / (3.0Q * fe_beta_));
                const real_t Ec = (2.0Q / 3.0Q) * abs_q(fe_alpha_) * P_sp;
                // Do not nucleate a pristine domain from round-off in an
                // otherwise zero-field Poisson solution.  Previously an
                // O(1e-20 V) mesh perturbation selected random +/- wells at
                // different nodes; their artificial bound charge then locked
                // the slab into a mesh-dependent multidomain state.  One V/m
                // is far below any physical FE switching field while safely
                // above the numerical field floor.
                const real_t field_seed_floor = 1.0Q;
                for (int c = 0; c < 3; ++c) {
                    real_t E_i = Ei[c];
                    // Initial guess: continue from the previous P_i (path dependence).
                    // A pristine component (P_i==0) is seeded ONLY where the field
                    // drives it (|E_i|>0): pin to sign(E_i)*Ps (double-well minimum,
                    // Newton-safe, branch-correct). Where E_i==0 a pristine component
                    // stays at 0 — so a 1D field (Ey=Ez=0) yields Py=Pz==0 exactly,
                    // matching the prior scalar behavior with no spurious off-axis P.
                    real_t P = fe_polarization_[3*idx + c];
                    if (P == 0.0Q) {
                        if (E_i > field_seed_floor)       P = Ps;
                        else if (E_i < -field_seed_floor) P = -Ps;
                        // Numerically zero field: leave P=0, including all
                        // un-driven off-axis components.
                    } else if (Ec > 0.0Q) {
                        // Switching test: drive opposes P and exceeds coercive field.
                        // Re-seed to the opposite well so Newton crosses the barrier.
                        real_t drive_sign = (E_i > 0.0Q) ? 1.0Q : -1.0Q;
                        if ((P * drive_sign < 0.0Q) && abs_q(E_i) > Ec) {
                            P = drive_sign * Ps;
                        }
                    }

                    // Solve alpha*P + beta*P^3 = E_i (signed) by Newton.
                    for (int iter = 0; iter < 20; ++iter) {
                        real_t f = fe_alpha_ * P + fe_beta_ * P * P * P - E_i;
                        real_t df = fe_alpha_ + 3.0Q * fe_beta_ * P * P;
                        if (abs_q(df) < 1e-30Q) break;
                        real_t dP = f / df;
                        P -= dP;
                        if (abs_q(dP) < 1e-15Q * abs_q(P)) break;
                    }
                    // BUG FIX (comments2.docx): clamp P to [-Ps, +Ps].
                    if (P > Ps) P = Ps;
                    if (P < -Ps) P = -Ps;
                    // Under-relaxation (comments2.docx): blend new and old P.
                    real_t P_prev = fe_polarization_[3*idx + c];
                    P = fe_relax_ * P + (1.0Q - fe_relax_) * P_prev;
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
    fe_ps_ = ps;
    fe_ec_ = ec;
    fe_escale_ = escale;   // 0 => Ec (legacy loop-shape default)
}

void PoissonSolver::set_ferroelectric_builtin_field(real_t E_bi) {
    fe_E_bi_ = E_bi;       // P2.1: internal/imprint offset; 0 => symmetric
}

void PoissonSolver::set_ferroelectric_depol(real_t eps_fe) {
    fe_eps_fe_ = eps_fe;   // comments2.docx P3: depol E_dep = -P/(eps_fe*eps0)
}

void PoissonSolver::set_interface_traps(const std::vector<char>& mask,
                                        real_t D_it, real_t E_t) {
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
    if (trap_mask_.empty()) return 0.0Q;
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
    if (cx == 0 || cy == 0 || cz == 0) return 0.0Q;   // no masked nodes
    const real_t ex = (real_t)cx * g_.dx, ey = (real_t)cy * g_.dy,
                 ez = (real_t)cz * g_.dz;
    const bool span_x = (cx == g_.nx), span_y = (cy == g_.ny), span_z = (cz == g_.nz);
    // Embedded layer: choose among the non-spanning axes (smallest extent).
    if (!span_x || !span_y || !span_z) {
        real_t best = -1.0Q;
        if (!span_x) best = ex;
        if (!span_y && (best < 0.0Q || ey < best)) best = ey;
        if (!span_z && (best < 0.0Q || ez < best)) best = ez;
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
            return -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
        if (i + 1 < g_.nx)
            return -(phi[idx + 1] - phi[idx]) / g_.dx;
        if (i > 0)
            return -(phi[idx] - phi[idx - 1]) / g_.dx;
    } else if (axis == 1) {
        if (j > 0 && j + 1 < g_.ny)
            return -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (2.0Q * g_.dy);
        if (j + 1 < g_.ny)
            return -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
        if (j > 0)
            return -(phi[idx] - phi[idx - g_.nx]) / g_.dy;
    } else {
        if (k > 0 && k + 1 < g_.nz)
            return -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (2.0Q * g_.dz);
        if (k + 1 < g_.nz)
            return -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz;
        if (k > 0)
            return -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz;
    }
    return 0.0Q;   // degenerate (single-node axis): no field
}

real_t PoissonSolver::residual_norm(const std::vector<real_t>& phi,
                                    const std::vector<real_t>& n,
                                    const std::vector<real_t>& p) {
    // True Poisson equation residual (P0-3 fix): reassemble A_ and rhs_ for
    // the given state (WITHOUT solving) and return ||A*phi - rhs||/(||rhs||+tiny).
    assemble(n, p);
    std::vector<real_t> Ax = A_.apply(phi);
    real_t num = 0.0Q, den = 0.0Q;
    for (size_t i = 0; i < g_.npts(); ++i) {
        real_t r = Ax[i] - rhs_[i];
        num += r * r;
        den += rhs_[i] * rhs_[i];
    }
    return sqrt_q(num) / (sqrt_q(den) + 1.0e-300Q);
}

void PoissonSolver::set_oxide_traps(const std::vector<real_t>& Q_ot) {
    Q_ot_ = Q_ot;          // [C/m^3], persistent (evolved by caller)
}

void PoissonSolver::set_ferroelectric_nls(real_t tau0, real_t E0, real_t dt) {
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
    leak_phi_ = phi;
    if (leak_mask_.empty()) return;
    const size_t N = g_.npts();
    leak_E_mag_.assign(N, 0.0Q);
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (idx >= leak_mask_.size() || !leak_mask_[idx]) continue;
                real_t Ex = 0.0Q, Ey = 0.0Q, Ez = 0.0Q;
                if (i > 0 && i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                else if (i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                else if (i > 0)
                    Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                if (j > 0 && j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (2.0Q * g_.dy);
                else if (j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
                else if (j > 0)
                    Ey = -(phi[idx] - phi[idx - g_.nx]) / g_.dy;
                if (k > 0 && k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (2.0Q * g_.dz);
                else if (k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz;
                else if (k > 0)
                    Ez = -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz;
                leak_E_mag_[idx] = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
            }
        }
    }
}

void PoissonSolver::update_ferroelectric_polarization_transient(const std::vector<real_t>& phi, real_t dt) {
    if (!fe_enabled_ || fe_gamma_ <= 0.0Q) return;

    // Isotropic vector LK time step (mirrors the steady path): each component
    // evolves with its own signed drive, so a reversing field can flip a
    // component and the trajectory retains memory. Clamps that forced P>=0 are
    // removed. NOTE: the update below evaluates the RHS at P_old, so this is
    // explicit (forward) Euler in P despite the "BE" name; preserved as-is in A4.
    const real_t Ps = sqrt_q(-fe_alpha_ / fe_beta_);
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!fe_mask_[idx]) {
                    fe_polarization_[3*idx + 0] = 0.0Q;
                    fe_polarization_[3*idx + 1] = 0.0Q;
                    fe_polarization_[3*idx + 2] = 0.0Q;
                    continue;
                }

                // Compute E = -grad(phi) components
                real_t Ex = 0.0Q, Ey = 0.0Q, Ez = 0.0Q;
                if (i > 0 && i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                else if (i + 1 < g_.nx)
                    Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                else if (i > 0)
                    Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                if (j > 0 && j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (2.0Q * g_.dy);
                else if (j + 1 < g_.ny)
                    Ey = -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
                else if (j > 0)
                    Ey = -(phi[idx] - phi[idx - g_.nx]) / g_.dy;
                if (k > 0 && k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (2.0Q * g_.dz);
                else if (k + 1 < g_.nz)
                    Ez = -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz;
                else if (k > 0)
                    Ez = -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz;

                // P2.1: apply the internal/imprint field offset to the polar
                // axis (fe_axis_) component. (P0-1 fix: was Ex only.)
                real_t Ei[3] = {Ex, Ey, Ez};
                Ei[fe_axis_] -= fe_E_bi_;
                for (int c = 0; c < 3; ++c) {
                    real_t E_i = Ei[c];
                    real_t P_old = fe_polarization_[3*idx + c];
                    if (P_old == 0.0Q) {
                        // Pristine component: pin to the signed well minimum only
                        // where the field drives it (Newton-safe, branch-correct);
                        // leave 0 where E_i==0 (no spurious off-axis P). Same
                        // convention as the steady path.
                        if (E_i > 0.0Q)       P_old = Ps;
                        else if (E_i < 0.0Q)  P_old = -Ps;
                    }
                    // LK step: P^{k+1} = P^k + (dt/gamma)*(E_i - alpha*P^k - beta*(P^k)^3)
                    real_t residual = E_i - fe_alpha_ * P_old - fe_beta_ * P_old * P_old * P_old;
                    real_t P_new = P_old + (dt / fe_gamma_) * residual;
                    // No P_new>=0 clamp: the -Ps branch must persist.
                    fe_polarization_[3*idx + c] = P_new;
                }
            }
        }
    }
}

void PoissonSolver::assemble_newton(const std::vector<real_t>& phi,
                                    const std::vector<real_t>& n,
                                    const std::vector<real_t>& p,
                                    real_t VT,
                                    SparseMatrix& J,
                                    Vector& F) const {
    if (!assembled_) throw std::runtime_error("System not assembled");

    J = SparseMatrix(A_);  // copy CSR structure
    F.assign(g_.npts(), 0.0Q);

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
            real_t sum = 0.0Q;
            for (size_t idx = A_.row_offsets()[i]; idx < A_.row_offsets()[i + 1]; ++idx) {
                sum += A_.vals()[idx] * phi[A_.col_indices()[idx]];
            }
            F[i] = sum + QE * (p[i] - n[i] + Nd_minus_Na_[i]);
        }
    }
}

bool PoissonSolver::solve(std::vector<real_t>& phi) {
    if (!assembled_) throw std::runtime_error("System not assembled");
    if (phi.size() != g_.npts()) phi.assign(g_.npts(), 0.0Q);

    Vector x(phi.begin(), phi.end());

    // --- Jacobi smoothing to provide a good initial guess for iterative solvers ---
    try {
        LinearSolver jacobi_solver({SolverType::JACOBI, 20, 1e-6Q, 30, false});
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
    Ex.assign(g_.npts(), 0.0Q);
    Ey.assign(g_.npts(), 0.0Q);
    Ez.assign(g_.npts(), 0.0Q);

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                // Central differences
                if (i > 0 && i + 1 < g_.nx)
                    Ex[idx] = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                else if (i + 1 < g_.nx)
                    Ex[idx] = -(phi[idx + 1] - phi[idx]) / g_.dx;
                else if (i > 0)
                    Ex[idx] = -(phi[idx] - phi[idx - 1]) / g_.dx;

                if (j > 0 && j + 1 < g_.ny)
                    Ey[idx] = -(phi[idx + g_.nx] - phi[idx - g_.nx]) / (2.0Q * g_.dy);
                else if (j + 1 < g_.ny)
                    Ey[idx] = -(phi[idx + g_.nx] - phi[idx]) / g_.dy;
                else if (j > 0)
                    Ey[idx] = -(phi[idx] - phi[idx - g_.nx]) / g_.dy;

                if (k > 0 && k + 1 < g_.nz)
                    Ez[idx] = -(phi[idx + g_.nx * g_.ny] - phi[idx - g_.nx * g_.ny]) / (2.0Q * g_.dz);
                else if (k + 1 < g_.nz)
                    Ez[idx] = -(phi[idx + g_.nx * g_.ny] - phi[idx]) / g_.dz;
                else if (k > 0)
                    Ez[idx] = -(phi[idx] - phi[idx - g_.nx * g_.ny]) / g_.dz;
            }
        }
    }
}

} // namespace tcad
