#include "poisson_solver.h"
#include <iostream>

namespace tcad {

PoissonSolver::PoissonSolver(const Grid3D& grid)
    : g_(grid), eps_(grid.npts(), EPS0 * 11.7Q), // Default: Silicon
      Nd_minus_Na_(grid.npts(), 0.0Q),
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
    if (!edge_eps_x_plus_.empty() && edge_eps_x_plus_[idx] > 0.0Q) {
        return edge_eps_x_plus_[idx] / (g_.dx * g_.dx);
    }
    real_t eps_sum = eps_[idx] + eps_[idx + 1];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + 1] / eps_sum / (g_.dx * g_.dx);
}

real_t PoissonSolver::cx_minus(size_t idx) const {
    size_t i = idx % g_.nx;
    if (i == 0) return 0.0Q;
    if (!edge_eps_x_minus_.empty() && edge_eps_x_minus_[idx] > 0.0Q) {
        return edge_eps_x_minus_[idx] / (g_.dx * g_.dx);
    }
    real_t eps_sum = eps_[idx] + eps_[idx - 1];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - 1] / eps_sum / (g_.dx * g_.dx);
}

real_t PoissonSolver::cy_plus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j + 1 >= g_.ny) return 0.0Q;
    if (!edge_eps_y_plus_.empty() && edge_eps_y_plus_[idx] > 0.0Q) {
        return edge_eps_y_plus_[idx] / (g_.dy * g_.dy);
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + g_.nx] / eps_sum / (g_.dy * g_.dy);
}

real_t PoissonSolver::cy_minus(size_t idx) const {
    size_t j = (idx / g_.nx) % g_.ny;
    if (j == 0) return 0.0Q;
    if (!edge_eps_y_minus_.empty() && edge_eps_y_minus_[idx] > 0.0Q) {
        return edge_eps_y_minus_[idx] / (g_.dy * g_.dy);
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - g_.nx] / eps_sum / (g_.dy * g_.dy);
}

real_t PoissonSolver::cz_plus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k + 1 >= g_.nz) return 0.0Q;
    if (!edge_eps_z_plus_.empty() && edge_eps_z_plus_[idx] > 0.0Q) {
        return edge_eps_z_plus_[idx] / (g_.dz * g_.dz);
    }
    real_t eps_sum = eps_[idx] + eps_[idx + g_.nx * g_.ny];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx + g_.nx * g_.ny] / eps_sum / (g_.dz * g_.dz);
}

real_t PoissonSolver::cz_minus(size_t idx) const {
    size_t k = idx / (g_.nx * g_.ny);
    if (k == 0) return 0.0Q;
    if (!edge_eps_z_minus_.empty() && edge_eps_z_minus_[idx] > 0.0Q) {
        return edge_eps_z_minus_[idx] / (g_.dz * g_.dz);
    }
    real_t eps_sum = eps_[idx] + eps_[idx - g_.nx * g_.ny];
    if (eps_sum < EPSILON) return 0.0Q;
    return 2.0Q * eps_[idx] * eps_[idx - g_.nx * g_.ny] / eps_sum / (g_.dz * g_.dz);
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
                rhs_[idx] = -QE * (p[idx] - n[idx] + Nd_minus_Na_[idx]);

                // Interface traps (Dit) + bulk oxide traps (P6).
                // Interface trap charge: Q_it = -q * D_it * dE * (f_t - 0.5),
                // where f_t = 1/(1+exp((E_t - E_F)/kT)) is the trap occupancy.
                // E_F relative to intrinsic is approximated by phi/VT (the
                // local potential in units of thermal voltage). D_it is in
                // cm^-2 eV^-1, converted: D_it * 1e4 [m^-2 eV^-1]. dE is the
                // energy range over which traps are active (bandgap, ~1 eV).
                // The (f_t - 0.5) term gives zero charge at flatband (E_F=E_t).
                // Bulk oxide traps Q_ot_ are a persistent charge [C/m^3].
                if (!trap_mask_.empty() && idx < trap_mask_.size() && trap_mask_[idx]) {
                    real_t VT = 0.02585Q;   // thermal voltage at 300K [V]
                    // Use the cached phi from set_leakage_field (or set_trap_field).
                    real_t phi_val = 0.0Q;
                    if (!leak_phi_.empty() && idx < leak_phi_.size())
                        phi_val = leak_phi_[idx];
                    real_t E_F_shift = phi_val / VT;   // E_F - E_i in units of kT [eV]
                    real_t arg = (trap_E_t_ - E_F_shift);
                    real_t f_t = 1.0Q / (1.0Q + exp_q(arg));
                    real_t dE = 1.0Q;   // effective trap energy range [eV]
                    // Q_it in [C/m^2], divide by dx to get [C/m^3] for the RHS.
                    real_t D_it_m2 = trap_D_it_ * 1.0e4Q;   // cm^-2 -> m^-2
                    real_t Q_it = -QE * D_it_m2 * dE * (f_t - 0.5Q) / g_.dx;
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
                    if (i + 1 < g_.nx) divP += (Pxc(idx + 1) - Pxc(idx)) / g_.dx;
                    if (i > 0)         divP -= (Pxc(idx) - Pxc(idx - 1)) / g_.dx;
                    if (j + 1 < g_.ny) divP += (Pyc(idx + g_.nx) - Pyc(idx)) / g_.dy;
                    if (j > 0)         divP -= (Pyc(idx) - Pyc(idx - g_.nx)) / g_.dy;
                    if (k + 1 < g_.nz) divP += (Pzc(idx + g_.nx * g_.ny) - Pzc(idx)) / g_.dz;
                    if (k > 0)         divP -= (Pzc(idx) - Pzc(idx - g_.nx * g_.ny)) / g_.dz;
                    rhs_[idx] -= divP;
                }

                // Dielectric soft-breakdown leakage (M7b, audit §22).  A node
                // that has irreversibly broken down gets +sigma_bd on the
                // Poisson diagonal (and +0 RHS), locally relaxing phi toward 0
                // — a soft short that develops a gate leak.  Physically this
                // models the post-breakdown conductive filament raising the
                // local oxide permittivity-density.
                // (A档: sigma_bd is [F/m^3], the SAME units as the Laplacian
                //  diagonal eps/dx^2 — adding it is dimensionally consistent.
                //  Was previously documented [S/m], which was wrong by ~1e9.)
                if (!bd_state_.empty() && idx < bd_state_.size() && bd_state_[idx] &&
                    sigma_bd_ > 0.0Q) {
                    A_.add_entry(idx, idx, sigma_bd_);
                    // RHS unchanged (drives phi -> 0, i.e. soft ground).
                }

                // Leakage current (PF/FN) field-dependent conductance (P2.2).
                // Adds sigma_leak(|E|) to the Poisson diagonal of leaky nodes,
                // modelling a residual conduction path across the dielectric.
                // This relaxes phi slightly at the leaky layer so the P-V loop
                // does NOT close at V=0 (reproducing the experimental 0V
                // non-closure and off-state gate leakage). sigma_leak is a
                // fraction of the local Laplacian diagonal eps/dx^2 — so the
                // PF/FN prefactors C_pf/C_fn are normalised to the dielectric
                // scale and need not be tuned to absolute current units.
                if (!leak_mask_.empty() && idx < leak_mask_.size() && leak_mask_[idx] &&
                    idx < leak_E_mag_.size()) {
                    real_t E_mag = leak_E_mag_[idx];
                    if (E_mag > leak_E_floor_) {
                        // Reference conductance = local Laplacian diagonal eps/dx^2.
                        real_t g_ref = eps_[idx] / (g_.dx * g_.dx);
                        real_t frac = 0.0Q;
                        if (leak_C_pf_ > 0.0Q && leak_phi_t_ > 0.0Q) {
                            // Poole-Frenkel: J = C_pf * |E| * exp(-B_pf*sqrt(phi_t/|E|))
                            // Normalised to a diagonal fraction.
                            real_t arg = leak_B_pf_ * sqrt_q(leak_phi_t_ / E_mag);
                            frac += leak_C_pf_ * E_mag * exp_q(-arg) / E_mag;
                        }
                        if (leak_C_fn_ > 0.0Q && leak_phi_b_ > 0.0Q) {
                            // Fowler-Nordheim: J = C_fn * |E|^2 * exp(-B_fn*phi_b^(3/2)/|E|)
                            real_t arg = leak_B_fn_ * pow_q(leak_phi_b_, 1.5Q) / E_mag;
                            frac += leak_C_fn_ * E_mag * E_mag * exp_q(-arg) / E_mag;
                        }
                        real_t sigma_leak = frac * g_ref;
                        // Cap to avoid dominating the Laplacian diagonal.
                        if (sigma_leak > leak_sigma_cap_ * g_ref)
                            sigma_leak = leak_sigma_cap_ * g_ref;
                        if (sigma_leak > 0.0Q)
                            A_.add_entry(idx, idx, sigma_leak);
                    }
                }
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

    // ---- Preisach (play-operator) path (M7c) ----
    // Classical scalar Preisach realised as a moving (play) model: each node
    // carries a single internal "play" value w (the delayed field). On a field
    // step the play follows E but lags by the coercive half-width Ec, and the
    // output P = Ps*tanh((E - w)/Escale) saturates at +/-Ps. This produces the
    // correct rectangular-ish hysteresis loop (remanence at E=0, switching when
    // |E| crosses Ec) WITHOUT the L-K alpha/beta dimensional mess, and with a
    // natural memory (the play value w). Only Px is driven in 1-D; the scalar
    // behavior is the special case. The output P is written into
    // fe_polarization_ (Px component) so assemble()'s -div(P) term is shared
    // with the L-K path. The play state fe_play_state_ persists across solve().
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
                    // E = -grad(phi), only the x component is driven here
                    // (scalar Preisach; the vector generalisation would run
                    // three independent play operators, matching L-K's A4 form).
                    // P2.1: apply the internal/imprint field offset E_bi so the
                    // effective switching drive is E_eff = E - E_bi. This models
                    // a built-in bias / imprint that breaks +/- symmetry.
                    real_t Ex = 0.0Q;
                    if (i > 0 && i + 1 < g_.nx)
                        Ex = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                    else if (i + 1 < g_.nx)
                        Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                    else if (i > 0)
                        Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                    Ex -= fe_E_bi_;   // imprint / built-in offset (P2.1)

                    // Play operator update: w follows E but lags by Ec.
                    real_t w = fe_play_state_[idx];
                    if (Ex > w + Ec)       w = Ex - Ec;
                    else if (Ex < w - Ec)  w = Ex + Ec;
                    // else: w unchanged (inside the deadband -> memory)
                    fe_play_state_[idx] = w;

                    // Saturating output: P = Ps * tanh((E - w)/Escale).
                    real_t arg = (Ex - w) / Escale;
                    real_t P = Ps * tanh_q(arg);
                    fe_polarization_[3*idx+0] = P;
                    // Off-axis components stay 0 (scalar Preisach in 1-D).
                    fe_polarization_[3*idx+1] = 0.0Q;
                    fe_polarization_[3*idx+2] = 0.0Q;
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
    // In quasi-static operation each Gummel iteration applies an effective
    // dwell time dt_eff (a configurable fraction of the external sweep), so the
    // polarization relaxes toward the field-favored target
    //     P_target = sign(E_eff) * Ps
    // by a fractional amount f = 1 - exp(-dt_eff / tau(E)). Crucially, near the
    // coercive field |E|~Ec, tau(E) is large, so f is small and the loop has a
    // FINITE slope (S-shaped) rather than an instantaneous vertical jump. This
    // fixes the "switching is completely vertical" failure mode reported for
    // AlScN FeFETs. Off-axis components stay 0 (scalar NLS in 1-D). The state
    // P persists across solve() so the loop has path-dependent memory.
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
        for (size_t k = 0; k < g_.nz; ++k) {
            for (size_t j = 0; j < g_.ny; ++j) {
                for (size_t i = 0; i < g_.nx; ++i) {
                    size_t idx = g_.index(i, j, k);
                    if (!fe_mask_[idx]) {
                        fe_polarization_[3*idx+0] = 0.0Q;
                        fe_polarization_[3*idx+1] = 0.0Q;
                        fe_polarization_[3*idx+2] = 0.0Q;
                        continue;
                    }
                    // E = -grad(phi) along x (scalar NLS); apply E_bi offset.
                    real_t Ex = 0.0Q;
                    if (i > 0 && i + 1 < g_.nx)
                        Ex = -(phi[idx + 1] - phi[idx - 1]) / (2.0Q * g_.dx);
                    else if (i + 1 < g_.nx)
                        Ex = -(phi[idx + 1] - phi[idx]) / g_.dx;
                    else if (i > 0)
                        Ex = -(phi[idx] - phi[idx - 1]) / g_.dx;
                    Ex -= fe_E_bi_;   // imprint / built-in offset (P2.1)

                    real_t P_old = fe_polarization_[3*idx+0];
                    real_t P_target;
                    if (Ex > 0.0Q)       P_target = Ps;
                    else if (Ex < 0.0Q)  P_target = -Ps;
                    else                 P_target = P_old;  // no field -> hold

                    // Merz switching time tau(E) = tau0 * exp(E0/|E|).
                    // Below the coercive field switching is exponentially slow
                    // (f->0, P holds); well above it tau->tau0 (fast switching).
                    real_t Eabs = abs_q(Ex);
                    real_t f;   // fractional relaxation toward target
                    if (Eabs > Ec * 0.1Q) {
                        real_t tau = tau0 * exp_q(E0 / Eabs);
                        // f = 1 - exp(-dt_eff/tau): bounded in [0, 1].
                        real_t r = dt_eff / tau;
                        if (r > 50.0Q) f = 1.0Q;            // saturated (fast switch)
                        else            f = 1.0Q - exp_q(-r);
                    } else {
                        f = 0.0Q;   // sub-threshold: P frozen (memory)
                    }
                    // Only relax if the target opposes the current state (switching
                    // direction); if aligned, P is already near the well.
                    real_t P = P_old + f * (P_target - P_old);
                    // Smooth saturation: P must stay in [-Ps, +Ps].
                    if (P > Ps) P = Ps;
                    if (P < -Ps) P = -Ps;
                    fe_polarization_[3*idx+0] = P;
                    fe_polarization_[3*idx+1] = 0.0Q;
                    fe_polarization_[3*idx+2] = 0.0Q;
                }
            }
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

                // P2.1: apply the internal/imprint field offset to the primary
                // (x) switching axis. E_eff = E - E_bi breaks +/- symmetry.
                Ex -= fe_E_bi_;
                const real_t Ei[3] = {Ex, Ey, Ez};
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
                        if (E_i > 0.0Q)       P = Ps;
                        else if (E_i < 0.0Q)  P = -Ps;
                        // E_i == 0: leave P = 0 (no off-axis polarization seeded)
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
                        // No P>=0 clamp: the -Ps branch must be reachable for hysteresis.
                        if (abs_q(dP) < 1e-15Q * abs_q(P)) break;
                    }
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
    // bd_state is length npts (1 = node broken down).  Empty disables the
    // leakage term.  sigma_bd is the soft-breakdown conductance [S/m].
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
    fe_escale_ = escale;   // 0 => Ec/3 (P1.3)
}

void PoissonSolver::set_ferroelectric_builtin_field(real_t E_bi) {
    fe_E_bi_ = E_bi;       // P2.1: internal/imprint offset; 0 => symmetric
}

void PoissonSolver::set_interface_traps(const std::vector<char>& mask,
                                        real_t D_it, real_t E_t) {
    trap_mask_ = mask;
    trap_D_it_ = D_it;     // [cm^-2 eV^-1]
    trap_E_t_ = E_t;       // [eV] relative to intrinsic Fermi level
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

                // P2.1: apply the internal/imprint field offset (x axis).
                Ex -= fe_E_bi_;
                const real_t Ei[3] = {Ex, Ey, Ez};
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
