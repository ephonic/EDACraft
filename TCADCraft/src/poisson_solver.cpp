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

                const real_t Ei[3] = {Ex, Ey, Ez};
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
