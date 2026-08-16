#include "gummel_solver.h"
#include "linear_solver.h"
#include "statistics.h"
#include <iostream>
#include <cmath>

namespace tcad {

namespace {
real_t scaled_linear_residual(const SparseMatrix& matrix,
                              const Vector& rhs, const Vector& solution) {
    const Vector applied = matrix.apply(solution);
    const auto& rows = matrix.row_offsets();
    const auto& values = matrix.vals();
    real_t worst = 0.0Q;
    for (size_t i = 0; i < rhs.size(); ++i) {
        real_t scale = abs_q(rhs[i]);
        for (size_t entry = rows[i]; entry < rows[i + 1]; ++entry)
            scale += abs_q(values[entry] * solution[matrix.col_indices()[entry]]);
        const real_t residual = abs_q(applied[i] - rhs[i]);
        const real_t relative = residual / std::max(scale, 1.0Q);
        if (!std::isfinite((double)relative)) return 1.0e100Q;
        worst = std::max(worst, relative);
    }
    return worst;
}

void report_linear_residual_peak(const SparseMatrix& matrix,
                                 const Vector& rhs,
                                 const Vector& solution,
                                 const char* species) {
    const Vector applied = matrix.apply(solution);
    const auto& rows = matrix.row_offsets();
    const auto& values = matrix.vals();
    size_t worst_row = 0;
    real_t worst = -1.0Q;
    real_t worst_scale = 1.0Q;
    for (size_t i = 0; i < rhs.size(); ++i) {
        real_t scale = abs_q(rhs[i]);
        for (size_t entry = rows[i]; entry < rows[i + 1]; ++entry)
            scale += abs_q(
                values[entry] * solution[matrix.col_indices()[entry]]);
        scale = std::max(scale, 1.0Q);
        const real_t relative = abs_q(applied[i] - rhs[i]) / scale;
        if (relative > worst) {
            worst = relative;
            worst_row = i;
            worst_scale = scale;
        }
    }
    std::cerr << species << " continuity residual peak row=" << worst_row
              << " relative=" << (double)worst
              << " absolute="
              << (double)abs_q(applied[worst_row] - rhs[worst_row])
              << " scale=" << (double)worst_scale
              << " applied=" << (double)applied[worst_row]
              << " rhs=" << (double)rhs[worst_row]
              << " solution=" << (double)solution[worst_row]
              << std::endl;
}

bool has_narrow_banded_structure(const SparseMatrix& matrix) {
    const size_t n = matrix.rows();
    if (n <= 32) return false;
    size_t bandwidth = 1;
    const auto& rows = matrix.row_offsets();
    const auto& columns = matrix.col_indices();
    for (size_t row = 0; row < n; ++row) {
        for (size_t entry = rows[row]; entry < rows[row + 1]; ++entry) {
            const size_t column = columns[entry];
            const size_t distance = column > row ? column - row : row - column;
            bandwidth = std::max(bandwidth, distance + 1);
            if (bandwidth > 257 || 4 * bandwidth >= n) return false;
        }
    }
    return true;
}

bool finite_vector(const Vector& values) {
    for (const real_t value : values)
        if (!std::isfinite((double)value)) return false;
    return true;
}

void equilibrated_copy(const SparseMatrix& matrix, const Vector& rhs,
                       SparseMatrix& scaled_matrix, Vector& scaled_rhs,
                       Vector& row_scale, Vector& column_scale) {
    scaled_matrix = matrix;
    scaled_rhs = rhs;
    auto& scaled_values = scaled_matrix.vals_mut();
    const auto& rows = matrix.row_offsets();
    const auto& values = matrix.vals();
    row_scale.assign(matrix.rows(), 1.0Q);
    for (size_t row = 0; row < matrix.rows(); ++row) {
        real_t scale = 0.0Q;
        for (size_t entry = rows[row]; entry < rows[row + 1]; ++entry)
            scale = std::max(scale, abs_q(values[entry]));
        if (!(scale > EPSILON) || !std::isfinite((double)scale))
            throw std::runtime_error(
                "continuity row equilibration encountered an invalid row");
        row_scale[row] = scale;
        for (size_t entry = rows[row]; entry < rows[row + 1]; ++entry)
            scaled_values[entry] /= scale;
        scaled_rhs[row] /= scale;
    }
    // Row scaling alone leaves carrier columns with very different norms.
    // Apply the same second equilibration phase used by coupled Newton.
    column_scale.assign(matrix.rows(), 0.0Q);
    const auto& columns = scaled_matrix.col_indices();
    for (size_t entry = 0; entry < scaled_values.size(); ++entry)
        column_scale[columns[entry]] = std::max(
            column_scale[columns[entry]], abs_q(scaled_values[entry]));
    for (real_t& scale : column_scale)
        scale = scale > EPSILON ? 1.0Q / scale : 1.0Q;
    for (size_t entry = 0; entry < scaled_values.size(); ++entry)
        scaled_values[entry] *= column_scale[columns[entry]];
}

bool solve_continuity_linear_system(
    const SparseMatrix& matrix, const Vector& rhs, const Vector& initial,
    LinearSolver& primary, const SolverOptions& options,
    const char* species, bool& use_banded_direct, Vector& solution) {
    const real_t residual_gate = std::max(100.0Q * options.tol, 1.0e-8Q);
    const bool narrow_banded =
        options.type != SolverType::DENSE_DIRECT &&
        has_narrow_banded_structure(matrix);
    // A small 3-D structured matrix can be too wide for the banded path while
    // still being cheap enough for a one-off float128 dense solve.  Keep this
    // as an accuracy fallback only: the normal Gummel iterations continue to
    // use PETSc, avoiding the minutes-long all-dense sweep.
    const bool manageable_dense_retry =
        options.type != SolverType::DENSE_DIRECT && matrix.rows() <= 1024;
    if (use_banded_direct && !narrow_banded)
        use_banded_direct = false;

    bool primary_completed = !use_banded_direct;
    solution = initial;
    if (primary_completed) {
        try {
            // Iterative backends ultimately operate in double precision. Do
            // the row/column scaling in float128 first, so contact-reservoir
            // rows and refined semiconductor flux rows reach PETSc on
            // comparable scales. Acceptance is still checked against the
            // unscaled float128 matrix below.
            if (options.type == SolverType::DENSE_DIRECT) {
                primary.solve(matrix, rhs, solution);
            } else {
                SparseMatrix scaled_matrix;
                Vector scaled_rhs, row_scale, column_scale;
                equilibrated_copy(
                    matrix, rhs, scaled_matrix, scaled_rhs,
                    row_scale, column_scale);
                for (size_t i = 0; i < solution.size(); ++i)
                    solution[i] /= column_scale[i];
                primary.solve(scaled_matrix, scaled_rhs, solution);
                for (size_t i = 0; i < solution.size(); ++i)
                    solution[i] *= column_scale[i];

                // Mixed-precision iterative refinement: PETSc/SuperLU solves
                // each correction in double, while residual formation and
                // accumulation remain float128. This recovers the digits
                // lost to cancellation without paying for a full float128
                // factorization on every Gummel step.
                for (size_t refinement = 0; refinement < 8; ++refinement) {
                    if (!finite_vector(solution) ||
                        scaled_linear_residual(matrix, rhs, solution) <=
                            residual_gate)
                        break;
                    const Vector applied = matrix.apply(solution);
                    Vector correction_rhs(rhs.size());
                    for (size_t i = 0; i < rhs.size(); ++i)
                        correction_rhs[i] =
                            (rhs[i] - applied[i]) / row_scale[i];
                    Vector correction(rhs.size(), 0.0Q);
                    primary.solve(
                        scaled_matrix, correction_rhs, correction);
                    for (size_t i = 0; i < solution.size(); ++i)
                        solution[i] += column_scale[i] * correction[i];
                }
            }
        } catch (const std::exception& error) {
            primary_completed = false;
            std::cerr << species << " continuity linear solve failed: "
                      << error.what() << std::endl;
        }
    }
    real_t residual = primary_completed && finite_vector(solution)
        ? scaled_linear_residual(matrix, rhs, solution)
        : 1.0e100Q;
    if (residual <= residual_gate) return true;
    const real_t primary_residual = residual;

    // Carrier densities span roughly 1e6--1e26 m^-3 in a heavily doped 3-D
    // FET.  Pure matrix-norm column scaling need not make the unknown itself
    // dimensionless, leaving a minority-carrier Neumann row to cancel O(1e13)
    // flux terms down to an O(1e4) source.  Use the previous finite carrier
    // state as a physical column scale for a failed solve: x = D*y with y~1,
    // then row-equilibrate A*D.  The accepted result is still checked against
    // the unscaled float128 equation.
    if (options.type != SolverType::DENSE_DIRECT && finite_vector(initial)) {
        SparseMatrix physical_matrix = matrix;
        auto& physical_values = physical_matrix.vals_mut();
        const auto& physical_rows = matrix.row_offsets();
        const auto& physical_columns = matrix.col_indices();
        Vector carrier_scale(matrix.rows(), 1.0Q);
        for (size_t i = 0; i < carrier_scale.size(); ++i)
            carrier_scale[i] = std::max(abs_q(initial[i]), 1.0Q);
        for (size_t entry = 0; entry < physical_values.size(); ++entry)
            physical_values[entry] *= carrier_scale[physical_columns[entry]];

        Vector physical_rhs = rhs;
        Vector physical_row_scale(matrix.rows(), 1.0Q);
        for (size_t row = 0; row < matrix.rows(); ++row) {
            real_t scale = abs_q(physical_rhs[row]);
            for (size_t entry = physical_rows[row];
                 entry < physical_rows[row + 1]; ++entry)
                scale = std::max(scale, abs_q(physical_values[entry]));
            if (!(scale > EPSILON) || !std::isfinite((double)scale))
                scale = 1.0Q;
            physical_row_scale[row] = scale;
            for (size_t entry = physical_rows[row];
                 entry < physical_rows[row + 1]; ++entry)
                physical_values[entry] /= scale;
            physical_rhs[row] /= scale;
        }

        solution.resize(initial.size());
        for (size_t i = 0; i < initial.size(); ++i)
            solution[i] = initial[i] / carrier_scale[i];
        try {
            primary.solve(physical_matrix, physical_rhs, solution);
            for (size_t i = 0; i < solution.size(); ++i)
                solution[i] *= carrier_scale[i];
            for (size_t refinement = 0; refinement < 8; ++refinement) {
                if (!finite_vector(solution) ||
                    scaled_linear_residual(matrix, rhs, solution) <=
                        residual_gate)
                    break;
                const Vector applied = matrix.apply(solution);
                Vector correction_rhs(rhs.size());
                for (size_t i = 0; i < rhs.size(); ++i)
                    correction_rhs[i] =
                        (rhs[i] - applied[i]) / physical_row_scale[i];
                Vector correction(rhs.size(), 0.0Q);
                primary.solve(
                    physical_matrix, correction_rhs, correction);
                for (size_t i = 0; i < solution.size(); ++i)
                    solution[i] += carrier_scale[i] * correction[i];
            }
            residual = finite_vector(solution)
                ? scaled_linear_residual(matrix, rhs, solution)
                : 1.0e100Q;
            if (residual <= residual_gate) {
                std::cerr << species
                          << " continuity recovered with carrier-state "
                             "equilibration after matrix-norm residual "
                          << (double)primary_residual << std::endl;
                return true;
            }
        } catch (const std::exception& error) {
            std::cerr << species
                      << " continuity carrier-state retry failed: "
                      << error.what() << std::endl;
        }
    }

    // A column equilibration that is beneficial for majority carriers can
    // amplify an almost-empty minority-carrier unknown by many decades on a
    // 3-D contact-reservoir system.  SuperLU then solves the transformed
    // double-precision system accurately, while the reconstructed float128
    // state can still miss the original equation by O(1e-2).  Retry only the
    // failed case with row equilibration (which normalizes equation units but
    // leaves the physical carrier unknowns untouched), followed by the same
    // mixed-precision refinement and the same original-equation gate.
    if (options.type != SolverType::DENSE_DIRECT) {
        SparseMatrix row_matrix = matrix;
        Vector row_rhs = rhs;
        Vector row_scale(matrix.rows(), 1.0Q);
        auto& row_values = row_matrix.vals_mut();
        const auto& row_offsets = matrix.row_offsets();
        const auto& original_values = matrix.vals();
        for (size_t row = 0; row < matrix.rows(); ++row) {
            real_t scale = 0.0Q;
            for (size_t entry = row_offsets[row];
                 entry < row_offsets[row + 1]; ++entry)
                scale = std::max(scale, abs_q(original_values[entry]));
            if (!(scale > EPSILON) || !std::isfinite((double)scale)) {
                scale = 1.0Q;
            }
            row_scale[row] = scale;
            for (size_t entry = row_offsets[row];
                 entry < row_offsets[row + 1]; ++entry)
                row_values[entry] /= scale;
            row_rhs[row] /= scale;
        }
        solution = initial;
        try {
            primary.solve(row_matrix, row_rhs, solution);
            for (size_t refinement = 0; refinement < 8; ++refinement) {
                if (!finite_vector(solution) ||
                    scaled_linear_residual(matrix, rhs, solution) <=
                        residual_gate)
                    break;
                const Vector applied = matrix.apply(solution);
                Vector correction_rhs(rhs.size());
                for (size_t i = 0; i < rhs.size(); ++i)
                    correction_rhs[i] =
                        (rhs[i] - applied[i]) / row_scale[i];
                Vector correction(rhs.size(), 0.0Q);
                primary.solve(row_matrix, correction_rhs, correction);
                for (size_t i = 0; i < solution.size(); ++i)
                    solution[i] += correction[i];
            }
            residual = finite_vector(solution)
                ? scaled_linear_residual(matrix, rhs, solution)
                : 1.0e100Q;
            if (residual <= residual_gate) {
                std::cerr << species
                          << " continuity recovered with row-only "
                             "equilibration after row/column residual "
                          << (double)primary_residual << std::endl;
                return true;
            }
        } catch (const std::exception& error) {
            std::cerr << species
                      << " continuity row-only retry failed: "
                      << error.what() << std::endl;
        }
    }

    // PETSc and other double-precision iterative backends can satisfy their
    // own norm while losing several digits after row scales span the contact
    // reservoir and refined semiconductor equations.  Preserve the honest
    // residual gate, but retry structured narrow-band systems with the
    // internal float128 banded direct path instead of rejecting an otherwise
    // solvable nonlinear iterate.  Wide 3-D matrices never take this path.
    if (narrow_banded || manageable_dense_retry) {
        SolverOptions fallback_options = options;
        fallback_options.type = SolverType::DENSE_DIRECT;
        LinearSolver fallback(fallback_options);
        solution = initial;
        try {
            fallback.solve(matrix, rhs, solution);
        } catch (const std::exception& error) {
            std::cerr << species << " continuity banded-direct retry failed: "
                      << error.what() << std::endl;
            return false;
        }
        residual = finite_vector(solution)
            ? scaled_linear_residual(matrix, rhs, solution)
            : 1.0e100Q;
        if (residual <= residual_gate) {
            if (narrow_banded && !use_banded_direct)
                std::cerr << species
                          << " continuity switched to float128 banded direct "
                          << "after equilibrated primary residual "
                          << (double)primary_residual << " exceeded gate "
                          << (double)residual_gate
                          << std::endl;
            // Only a genuinely narrow system can reuse the fast banded
            // direct path on later nonlinear iterations.  A wide 3-D retry
            // remains an exceptional one-shot fallback.
            use_banded_direct = narrow_banded;
            return true;
        }
    }

    std::cerr << species << " continuity linear residual "
              << (double)residual << " exceeds gate "
              << (double)residual_gate << std::endl;
    report_linear_residual_peak(matrix, rhs, solution, species);
    return false;
}
}  // namespace

GummelSolver::GummelSolver(const Grid3D& grid, const GummelOptions& opt)
    : g_(grid), opt_(opt), poisson_(grid), dg_(grid) {
    const size_t N = g_.npts();
    mu_n_.assign(N, 0.14Q);   // Default Si m^2/(V*s)
    mu_p_.assign(N, 0.045Q);
    tau_n_.assign(N, 1e-7Q);
    tau_p_.assign(N, 1e-7Q);
    Nd_minus_Na_.assign(N, 0.0Q);
    // Configure Poisson solver
    SolverOptions poisson_opt = LinearSolver::default_poisson_options();
    poisson_opt.type = opt_.poisson_solver;
    if (poisson_opt.type == SolverType::GMRES ||
        poisson_opt.type == SolverType::BICGSTAB_ILU0)
        poisson_opt.prec = PreconditionerType::ILU0;
    poisson_.set_solver_options(poisson_opt);
    // Stabilized Gummel (plan0728 §1.2): semi-implicit carrier-charge
    // linearization in the Poisson solve.
    poisson_.set_boltzmann_linearization(opt_.boltzmann_lin, opt_.VT);
    // Ferroelectric
    if (opt_.ferro.enabled && !opt_.ferro.fe_mask.empty()) {
        poisson_.set_ferroelectric(opt_.ferro.fe_mask, opt_.ferro.alpha, opt_.ferro.beta);
        // Model selection + Preisach params (M7c).
        poisson_.set_ferroelectric_model(static_cast<int>(opt_.ferro.model));
        poisson_.set_ferroelectric_preisach(opt_.ferro.ps, opt_.ferro.ec, opt_.ferro.escale);
        // P2.1: internal/imprint field offset.
        poisson_.set_ferroelectric_builtin_field(opt_.ferro.E_bi);
        // comments2.docx P3: depolarization field.
        poisson_.set_ferroelectric_depol(opt_.ferro.eps_fe);
        // P3: NLS Merz-law parameters.
        poisson_.set_ferroelectric_nls(opt_.ferro.nls_tau0, opt_.ferro.nls_E0,
                                       opt_.ferro.nls_dt);
        // P0-1: polar axis for the scalar FE models (0=x, 1=y, 2=z).
        poisson_.set_ferroelectric_polar_axis(opt_.ferro.polar_axis);
    }
    // Leakage current (PF/FN) (P2.2)
    if (opt_.leakage.enabled && !opt_.leakage.mask.empty()) {
        poisson_.set_leakage(opt_.leakage.mask,
                             opt_.leakage.C_pf, opt_.leakage.B_pf, opt_.leakage.phi_t,
                             opt_.leakage.C_fn, opt_.leakage.B_fn, opt_.leakage.phi_b,
                             opt_.leakage.E_floor, opt_.leakage.sigma_cap);
    }
}

void GummelSolver::set_mobility(const std::vector<real_t>& mu_n, const std::vector<real_t>& mu_p) {
    mu_n_ = mu_n; mu_p_ = mu_p;
}

void GummelSolver::set_recombination(const std::vector<real_t>& tau_n, const std::vector<real_t>& tau_p) {
    tau_n_ = tau_n; tau_p_ = tau_p;
}

void GummelSolver::set_optical_generation(const std::vector<real_t>& G_opt) {
    G_opt_ = G_opt;
}

void GummelSolver::set_btbt_weight(const std::vector<real_t>& weight) {
    btbt_weight_ = weight;
}

void GummelSolver::set_doping(const std::vector<real_t>& Nd_minus_Na) {
    Nd_minus_Na_ = Nd_minus_Na;
    poisson_.set_doping(Nd_minus_Na);
}

void GummelSolver::set_effective_dos(const std::vector<real_t>& Nc, const std::vector<real_t>& Nv) {
    Nc_ = Nc;
    Nv_ = Nv;
    dg_.set_effective_dos(Nc, Nv);
}

void GummelSolver::set_bandgap(const std::vector<real_t>& Eg) {
    Eg_ = Eg;
}

void GummelSolver::set_electron_bc(const std::map<size_t, real_t>& bc) { n_bc_.insert(bc.begin(), bc.end()); }
void GummelSolver::set_hole_bc(const std::map<size_t, real_t>& bc) { p_bc_.insert(bc.begin(), bc.end()); }

void GummelSolver::compute_btbt(const std::vector<real_t>& phi,
                                std::vector<real_t>& G_btbt) const {
    const size_t N = g_.npts();
    G_btbt.assign(N, 0.0Q);
    if (!opt_.btbt.enabled) return;

    // Non-local (path-integral WKB) model
    if (opt_.btbt.use_nonlocal) {
        compute_nonlocal_btbt(phi, G_btbt);
        return;
    }

    // Local Kane's model (original)
    // Scale A_kane from cm^-3 to m^-3: multiply by 1e6
    real_t A = opt_.btbt.A_kane * 1.0e6Q;
    real_t B = opt_.btbt.B_kane;
    real_t D = opt_.btbt.D;

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                // Skip insulator/metal regions
                if (mu_n_[idx] < EPSILON) continue;

                // Compute |E| from potential gradients (central differences)
                real_t Ex = 0.0Q, Ey = 0.0Q, Ez = 0.0Q;
                if (i > 0 && i + 1 < g_.nx) {
                    Ex = -(phi[g_.index(i+1, j, k)] - phi[g_.index(i-1, j, k)]) / (2.0Q * g_.dx);
                } else if (i + 1 < g_.nx) {
                    Ex = -(phi[g_.index(i+1, j, k)] - phi[idx]) / g_.dx;
                } else if (i > 0) {
                    Ex = -(phi[idx] - phi[g_.index(i-1, j, k)]) / g_.dx;
                }
                if (j > 0 && j + 1 < g_.ny) {
                    Ey = -(phi[g_.index(i, j+1, k)] - phi[g_.index(i, j-1, k)]) / (2.0Q * g_.dy);
                } else if (j + 1 < g_.ny) {
                    Ey = -(phi[g_.index(i, j+1, k)] - phi[idx]) / g_.dy;
                } else if (j > 0) {
                    Ey = -(phi[idx] - phi[g_.index(i, j-1, k)]) / g_.dy;
                }
                if (k > 0 && k + 1 < g_.nz) {
                    Ez = -(phi[g_.index(i, j, k+1)] - phi[g_.index(i, j, k-1)]) / (2.0Q * g_.dz);
                } else if (k + 1 < g_.nz) {
                    Ez = -(phi[g_.index(i, j, k+1)] - phi[idx]) / g_.dz;
                } else if (k > 0) {
                    Ez = -(phi[idx] - phi[g_.index(i, j, k-1)]) / g_.dz;
                }

                real_t E_mag = 0.0Q;
                if (opt_.btbt.field_mode == 1) {
                    E_mag = abs_q(Ex);
                } else if (opt_.btbt.field_mode == 2) {
                    E_mag = abs_q(Ey);
                } else if (opt_.btbt.field_mode == 3) {
                    E_mag = abs_q(Ez);
                } else {
                    E_mag = sqrt_q(Ex*Ex + Ey*Ey + Ez*Ez);
                }
                if (opt_.btbt.field_cap > 0.0Q && E_mag > opt_.btbt.field_cap) {
                    E_mag = opt_.btbt.field_cap;
                }
                if (E_mag < 1.0e4Q) continue;  // negligible field threshold
                if (opt_.btbt.field_alpha != 0.0Q && opt_.btbt.field_ref > 0.0Q) {
                    E_mag *= pow_q(E_mag / opt_.btbt.field_ref, opt_.btbt.field_alpha);
                }

                // Kane's model: G = A * |E|^D * exp(-B / |E|).  D is a
                // real-valued exponent so indirect-tunnelling fits (e.g. 2.5)
                // are not silently truncated to the direct-tunnelling D=2
                // form.
                real_t E_D = pow_q(E_mag, D);
                real_t G = A * E_D * exp_q(-B / E_mag);
                if (btbt_weight_.size() == N) {
                    G *= btbt_weight_[idx];
                }
                G_btbt[idx] = G;
            }
        }
    }
}

void GummelSolver::compute_impact_ionization(const std::vector<real_t>& phi,
                                             const std::vector<real_t>& n,
                                             const std::vector<real_t>& p,
                                             std::vector<real_t>& G_ii) const {
    // Avalanche impact ionization (Chynoweth).  alpha(E) = A*exp(-B/|E|) [1/m].
    // Per-pair generation rate G_ii = (alpha_n*|Jn| + alpha_p*|Jp|)/q [m^-3 s^-1].
    //
    // We use the EDGE form, which is the physically correct and numerically
    // stable convention used by commercial tools (Sentaurus/DESSIS): for each
    // interior edge (idx -> nbr) the Scharfetter-Gummel current density is
    //   Jn = q*Dn/d * (n[idx]*B(-dphi/VT) - n[nbr]*B(+dphi/VT))   [A/m^2]
    // (identical to DeviceSimulator::compute_edge_currents, audit §20).
    // The ionization integral contribution of that edge is
    //   alpha_n(|E_edge|) * |Jn_edge| / q   [+ alpha_p*|Jp_edge|/q],
    // and it is deposited half to each endpoint with a 1/d weighting so the
    // returned per-node G_ii has units [m^-3 s^-1] matching SRH/BTBT.  |E_edge|
    // is the edge-aligned field component (the gradient along the edge), which
    // is what accelerates carriers across that edge — using the full |grad phi|
    // here would double-count across the three axes.
    const size_t N = g_.npts();
    G_ii.assign(N, 0.0Q);
    if (!opt_.ii.enabled) return;

    const real_t VT = opt_.VT;
    const real_t E_floor = opt_.ii.E_floor;

    // Helper: ionization coefficient alpha for a given |E| and (A,B) pair.
    auto alpha_of = [&](real_t E_mag, real_t A, real_t B) -> real_t {
        if (E_mag < E_floor) return 0.0Q;     // negligible below ~1e5 V/m
        return A * exp_q(-B / E_mag);
    };

    // Process one axis using the actual edge spacing.  The previous generic
    // loop incorrectly used the x-loop bound for y/z and a single uniform
    // spacing even on nonuniform meshes, making 3-D ionization orientation-
    // dependent and shifting breakdown under mesh refinement.
    auto process_axis = [&](int axis) {
        for (size_t k = 0; k < g_.nz; ++k) {
            for (size_t j = 0; j < g_.ny; ++j) {
                for (size_t i = 0; i < g_.nx; ++i) {
                    if ((axis == 0 && i + 1 >= g_.nx) ||
                        (axis == 1 && j + 1 >= g_.ny) ||
                        (axis == 2 && k + 1 >= g_.nz)) continue;
                    size_t idx = g_.index(i, j, k);
                    size_t stride = (axis == 0) ? 1
                                  : (axis == 1) ? g_.nx : g_.nx * g_.ny;
                    size_t nbr = idx + stride;
                    real_t d = (axis == 0) ? g_.dx_edge(i)
                             : (axis == 1) ? g_.dy_edge(j) : g_.dz_edge(k);
                    // Skip edges touching insulator/metal: no carrier flux there.
                    if (mu_n_[idx] < EPSILON && mu_p_[idx] < EPSILON) continue;
                    if (mu_n_[nbr] < EPSILON && mu_p_[nbr] < EPSILON) continue;

                    real_t dphi = phi[nbr] - phi[idx];
                    real_t delta = dphi / VT;
                    real_t Bm = bernoulli(-delta);
                    real_t Bp = bernoulli(delta);
                    // Edge-aligned electric field magnitude [V/m] along this edge.
                    real_t E_edge = abs_q(dphi / d);

                    real_t alpha_n = alpha_of(E_edge, opt_.ii.A_n, opt_.ii.B_n);
                    real_t alpha_p = alpha_of(E_edge, opt_.ii.A_p, opt_.ii.B_p);
                    if (alpha_n == 0.0Q && alpha_p == 0.0Q) continue;

                    // SG current densities along this edge [A/m^2].
                    real_t mu_ne = 2.0Q * mu_n_[idx] * mu_n_[nbr] /
                        (mu_n_[idx] + mu_n_[nbr] + 1e-30Q);
                    real_t mu_pe = 2.0Q * mu_p_[idx] * mu_p_[nbr] /
                        (mu_p_[idx] + mu_p_[nbr] + 1e-30Q);
                    real_t Dn = mu_ne * VT / d;
                    real_t Dp = mu_pe * VT / d;
                    real_t Jn = QE * Dn * (n[idx] * Bm - n[nbr] * Bp);
                    real_t Jp = QE * Dp * (p[idx] * Bp - p[nbr] * Bm);

                    // alpha*|J|/q [m^-3 s^-1], split half to each endpoint.
                    // (The 1/d already implicit in D = mu*VT/d is the per-edge
                    //  volume weighting; depositing half to each node matches the
                    //  box-integration of the continuity source term.)
                    real_t g_node = (alpha_n * abs_q(Jn) + alpha_p * abs_q(Jp)) / QE * 0.5Q;
                    G_ii[idx] += g_node;
                    G_ii[nbr] += g_node;
                }
            }
        }
    };

    process_axis(0);
    process_axis(1);
    process_axis(2);
}

void GummelSolver::compute_nonlocal_btbt(const std::vector<real_t>& phi,
                                         std::vector<real_t>& G_btbt) const {
    const size_t N = g_.npts();
    G_btbt.assign(N, 0.0Q);

    // Physical constants for WKB tunneling (SI units)
    const double hbar = 1.054571817e-34;  // reduced Planck constant [J*s]
    const double m0 = 9.1093837015e-31;   // electron rest mass [kg]
    const double qe = 1.602176634e-19;    // elementary charge [C]
    // Si effective tunneling mass ~ 0.25 m0 (averaged over valleys)
    const double mt_eff = 0.25 * m0;
    // Prefactor for BTBT generation
    const double pre_wkb = 1.0e27; // m^-3 s^-1

    size_t n_wkb = opt_.btbt.wkb_npts;
    if (n_wkb >= 4 && (n_wkb % 2) != 0) ++n_wkb;
    const double path_fraction = (double)opt_.btbt.tunnel_path_frac;

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);

                // Skip insulator/metal regions
                if (mu_n_[idx] < EPSILON) continue;

                // Tunneling primarily along x (source-channel direction for TFETs).
                //
                // Phase 3.3 fix (audit §12.3): the path length is no longer
                // fixed to a single grid spacing dx.  The old code set
                // path_L = dx, which truncated the WKB integral at one cell
                // whenever the band-crossing distance d_min = Eg/(qE) exceeded
                // dx (i.e. in the off-state / low-field regime).  That
                // under-estimated the true barrier and over-estimated T by
                // many orders of magnitude, making BTBT-Ioff unreliable.
                //
                // The correct path extends until the linearised barrier
                // actually exhausts (2*d_min, where barrier(x)=Eg-qEx drops
                // from Eg to 0 and back to 0 on the far side of the well).
                // We cap at the available grid (distance to the nearer x
                // boundary) so the linear band-edge model — which only sees
                // the local field — is not extrapolated past the device.
                const double dx_m = (double)g_.dx;

                // Local electric field along x
                double Ex_val = 0.0;
                if (i > 0 && i + 1 < g_.nx) {
                    Ex_val = -((double)phi[g_.index(i+1, j, k)] - (double)phi[g_.index(i-1, j, k)])
                           / (2.0 * dx_m);
                } else if (i + 1 < g_.nx) {
                    Ex_val = -((double)phi[g_.index(i+1, j, k)] - (double)phi[idx]) / dx_m;
                } else if (i > 0) {
                    Ex_val = -((double)phi[idx] - (double)phi[g_.index(i-1, j, k)]) / dx_m;
                }

                // Local bandgap from per-node material property
                const double Eg_eV = (idx < Eg_.size()) ? (double)Eg_[idx] : 1.12;

                // WKB integral: integrate sqrt(2*mt*(Ec(x) - Ev(x))) / hbar along path
                // Model band profile: linear drop across tunneling window, offset by local Ec-Ev
                // The tunneling window where Ec < Ev is when q*E*x > Eg
                const double Eg_J = Eg_eV * qe;
                const double E_field = fabs(Ex_val);

                // Band-crossing distance: where the linearised barrier would
                // reach zero.  For negligible field there is no crossing and
                // the barrier is effectively infinite -> no tunnelling.
                const double d_min = (E_field > 1.0) ? (Eg_J / (qe * E_field))
                                                    : 1.0e-6;  // 1 µm sentinel

                // Path length is the full band-crossing window (2*d_min), so
                // the WKB integral covers the *actual* barrier rather than a
                // single-cell slice.  Capped at the distance to the nearer x
                // boundary so we do not extrapolate the local linear field
                // beyond the simulated device.
                const double avail_lo = (double)i * dx_m;            // to x=0 face
                const double avail_hi = (double)(g_.nx - 1 - i) * dx_m; // to x=Lx face
                const double avail = std::min(avail_lo, avail_hi);
                double path_L = std::min(2.0 * d_min, avail);
                if (path_fraction > 0.0) {
                    const double domain_L = (double)(g_.nx - 1) * dx_m;
                    path_L = std::min(path_L, path_fraction * domain_L);
                }

                // effective_L == path_L now (no second truncation); kept for
                // clarity of the integration loop below.
                const double effective_L = path_L;

                if (effective_L < 1e-12) {
                    // Path is zero (boundary node with no interior room): no
                    // tunnelling can be represented at this node.
                    G_btbt[idx] = 0.0Q;
                    continue;
                }

                // Simpson's rule integration
                double wkb_integral = 0.0;
                if (n_wkb >= 4) {
                    const double h = effective_L / (double)(n_wkb);
                    for (size_t s = 0; s <= n_wkb; ++s) {
                        const double x = (double)s * h;
                        // Linear band drop: barrier height at position x
                        const double barrier = std::max(Eg_J - qe * E_field * x, 0.0);
                        if (barrier <= 0.0) {
                            // Classically allowed: no contribution
                            continue;
                        }
                        const double integrand = sqrt(2.0 * mt_eff * barrier) / hbar;
                        if (std::isinf(integrand)) {
                            wkb_integral = 1e10; // cap to avoid overflow
                            break;
                        }
                        double weight = (s == 0 || s == n_wkb) ? 1.0 :
                                        (s % 2 == 1 ? 4.0 : 2.0);
                        wkb_integral += weight * integrand;
                    }
                    wkb_integral *= h / 3.0;
                } else {
                    // Fallback: single-step estimate
                    wkb_integral = sqrt(2.0 * mt_eff * Eg_J) / hbar * effective_L;
                }

                // Tunneling probability: T = exp(-2 * WKB integral)
                const double exponent = -2.0 * wkb_integral;
                if (exponent < -700.0) {
                    // T ~ exp(-700) ~ 10^-304: effectively zero
                    G_btbt[idx] = 0.0Q;
                    continue;
                }
                const double T_prob = std::exp(exponent);

                // BTBT generation rate
                double G_val = pre_wkb * T_prob;
                if (btbt_weight_.size() == N) {
                    G_val *= (double)btbt_weight_[idx];
                }
                if (G_val > 1e50) {
                    G_btbt[idx] = (real_t)1e50;
                } else {
                    G_btbt[idx] = (real_t)G_val;
                }
            }
        }
    }
}

real_t GummelSolver::bernoulli(real_t x) {
    if (abs_q(x) < 1e-12Q) return 1.0Q;
    if (x > 100.0Q) return 0.0Q;
    if (x < -100.0Q) return -x;
    return x / expm1_q(x);
}

bool GummelSolver::solve_electron_density(const std::vector<real_t>& phi,
                                           std::vector<real_t>& n,
                                           const std::vector<real_t>& p,
                                           const std::vector<real_t>* transport_phi) {
    // Compute BTBT generation and add to optical generation
    std::vector<real_t> G_btbt;
    if (opt_.btbt.enabled) {
        compute_btbt(phi, G_btbt);
    }
    // Compute avalanche impact-ionization generation
    std::vector<real_t> G_ii;
    if (opt_.ii.enabled) {
        compute_impact_ionization(phi, n, p, G_ii);
    }

    const size_t N = g_.npts();
    SparseMatrix A(N);
    Vector rhs(N, 0.0Q);
    std::vector<char> is_bc(N, 0);
    for (const auto& [idx, val] : n_bc_) { is_bc[idx] = 1; }

    // Scharfetter-Gummel discretization
    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_bc[idx]) {
                    A.add_entry(idx, idx, 1.0Q);
                    rhs[idx] = n_bc_.at(idx);
                    continue;
                }
                // Insulator / metal: zero mobility -> freeze carrier density
                if (mu_n_[idx] < EPSILON) {
                    // Use a large diagonal to prevent pivot swapping in dense direct
                    A.add_entry(idx, idx, 1.0e20Q);
                    rhs[idx] = 1.0e20Q * EPSILON;
                    continue;
                }

                real_t center = 0.0Q;

                // Face-area weighting (2026-08 fix): FV/FD continuity row.
                // At a semiconductor/insulator interface the shared material
                // node lies on the physical interface.  Its carrier control
                // volume therefore ends at that node; it must not include the
                // half-cell on the zero-mobility side.  Using Grid::dy/dz_cell
                // unconditionally made the continuity equation conserve a
                // fictitious slice of oxide while terminal-current integration
                // used the real semiconductor thickness.  The two observables
                // then differed by several percent even for a converged state.
                auto active_width = [&](int axis) -> real_t {
                    if (axis == 1) {
                        real_t width = g_.dy_cell(j);
                        if (j > 0 && mu_n_[idx - g_.nx] < EPSILON)
                            width -= 0.5Q * g_.dy_edge(j - 1);
                        if (j + 1 < g_.ny && mu_n_[idx + g_.nx] < EPSILON)
                            width -= 0.5Q * g_.dy_edge(j);
                        return width > EPSILON ? width : g_.dy_cell(j);
                    }
                    real_t width = g_.dz_cell(k);
                    const size_t z_stride = g_.nx * g_.ny;
                    if (k > 0 && mu_n_[idx - z_stride] < EPSILON)
                        width -= 0.5Q * g_.dz_edge(k - 1);
                    if (k + 1 < g_.nz && mu_n_[idx + z_stride] < EPSILON)
                        width -= 0.5Q * g_.dz_edge(k);
                    return width > EPSILON ? width : g_.dz_cell(k);
                };
                const real_t w_y = g_.dx_cell(i) / active_width(1);
                const real_t w_z = g_.dx_cell(i) / active_width(2);
                const real_t dz_p = g_.dz_edge(k);       // z+ edge length
                const real_t dz_m = (k > 0) ? g_.dz_edge(k-1) : g_.dz;  // z- edge
                auto add_link = [&](size_t nbr, real_t dx, real_t mu, real_t w) {
                    // Skip coupling to insulator/metal neighbors: zero carrier flux
                    if (mu_n_[nbr] < EPSILON) return (real_t)0.0;
                    const std::vector<real_t>& phi_sg = transport_phi ? *transport_phi : phi;
                    real_t dphi = phi_sg[nbr] - phi_sg[idx];
                    real_t B_plus = bernoulli(dphi / opt_.VT);
                    real_t B_minus = bernoulli(-dphi / opt_.VT);
                    // Edge mobility: HARMONIC mean of the two nodes (2026-08
                    // fix).  The previous node-upwind value (mu_n_[idx]) gave
                    // each node a DIFFERENT flux on the shared edge wherever
                    // mobility varies (junctions!), breaking current
                    // conservation (div J != 0) and corrupting terminal
                    // currents (NPN BJT Ic error ~4x).
                    real_t mu_e = 2.0Q * mu * mu_n_[nbr] / (mu + mu_n_[nbr] + 1e-30Q);
                    real_t D = w * mu_e * opt_.VT / dx;
                    // Original SG discretization (kept for self-consistency)
                    real_t a_ii = D * B_minus;   // contribution to diagonal (positive)
                    real_t a_ij = -D * B_plus;   // off-diagonal (negative)
                    A.add_entry(idx, nbr, a_ij);
                    return a_ii;
                };

                const real_t dx_p = g_.dx_edge(i);
                const real_t dx_m = (i > 0) ? g_.dx_edge(i-1) : g_.dx;
                if (i + 1 < g_.nx) center += add_link(idx + 1, dx_p, mu_n_[idx], 1.0Q);
                if (i > 0)        center += add_link(idx - 1, dx_m, mu_n_[idx], 1.0Q);
                if (j + 1 < g_.ny) center += add_link(idx + g_.nx, g_.dy_edge(j), mu_n_[idx], w_y);
                if (j > 0)        center += add_link(idx - g_.nx, g_.dy_edge(j-1), mu_n_[idx], w_y);
                if (k + 1 < g_.nz) center += add_link(idx + g_.nx * g_.ny, dz_p, mu_n_[idx], w_z);
                if (k > 0)        center += add_link(idx - g_.nx * g_.ny, dz_m, mu_n_[idx], w_z);

                // Recombination (SRH simplified): R = (n*p - ni^2) / (tau_p*(n+ni) + tau_n*(p+ni))
                // Explicit treatment in Gummel iteration
                real_t ni = intrinsic_density(Eg_[idx], opt_.temperature, Nc_[idx], Nv_[idx], opt_.statistics_type);
                real_t R = 0.0Q;
                if (idx < tau_n_.size() && idx < tau_p_.size() &&
                    tau_n_[idx] > EPSILON && tau_p_[idx] > EPSILON) {
                    real_t np = n[idx] * p[idx];
                    real_t denom = tau_p_[idx] * (n[idx] + ni) + tau_n_[idx] * (p[idx] + ni);
                    if (denom > EPSILON)
                        R = (np - ni * ni) / denom;
                }
                // Auger recombination: R_A = (Cn*n + Cp*p) * (n*p - ni²)
                if (opt_.auger.enabled) {
                    real_t np_ni2 = n[idx] * p[idx] - ni * ni;
                    R += (opt_.auger.Cn * n[idx] + opt_.auger.Cp * p[idx]) * np_ni2;
                }
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.btbt.enabled && idx < G_btbt.size()) {
                    G += opt_.btbt.continuity_scale * G_btbt[idx];
                }
                if (opt_.ii.enabled && idx < G_ii.size()) G += G_ii[idx];
                real_t source_scale = g_.dx_cell(i);
                A.add_entry(idx, idx, center);
                rhs[idx] = (G - R) * source_scale;
                // Transient term: backward Euler.  The cell-integrated BE
                // continuity eqn is (n - n_prev)/dt*dx = center*n + flux + (G-R)*dx.
                // Moving the n_new terms left and knowns right gives
                //   (center + dx/dt)*n_new + flux = (G-R)*dx + n_prev*dx/dt
                // so the diagonal gets +dx/dt and the rhs gets +n_prev*dx/dt.
                // (The previous code had -dx/dt on the diagonal and used the
                // current iterate n instead of n_prev on the rhs — a sign and
                // consistency bug.  See audit §17.)
                if (opt_.transient_enabled && idx < opt_.n_prev.size()) {
                    A.add_entry(idx, idx, source_scale / opt_.transient_dt);
                    rhs[idx] += opt_.n_prev[idx] / opt_.transient_dt * source_scale;
                }
            }
        }
    }
    A.finalize();
    SolverOptions cont_opt = LinearSolver::default_continuity_options();
    cont_opt.type = opt_.continuity_solver;
    if (!cont_e_solver_) cont_e_solver_ = std::make_unique<LinearSolver>(cont_opt);
    const Vector initial(n.begin(), n.end());
    Vector x;
    if (!solve_continuity_linear_system(
            A, rhs, initial, *cont_e_solver_, cont_opt, "Electron",
            cont_e_use_banded_direct_, x))
        return false;
    // Commit only a fully finite linear solution.  A failed iterative solve
    // must not poison the previous nonlinear iterate with a partial NaN tail.
    for (size_t i = 0; i < N; ++i)
        n[i] = (x[i] < 0.0Q) ? EPSILON : x[i];
    return true;
}

bool GummelSolver::solve_hole_density(const std::vector<real_t>& phi,
                                       const std::vector<real_t>& n,
                                       std::vector<real_t>& p,
                                       const std::vector<real_t>* transport_phi) {
    // Compute BTBT generation and add to optical generation
    std::vector<real_t> G_btbt;
    if (opt_.btbt.enabled) {
        compute_btbt(phi, G_btbt);
    }
    // Compute avalanche impact-ionization generation
    std::vector<real_t> G_ii;
    if (opt_.ii.enabled) {
        compute_impact_ionization(phi, n, p, G_ii);
    }

    // Symmetric to electron solve with sign flips for holes
    const size_t N = g_.npts();
    SparseMatrix A(N);
    Vector rhs(N, 0.0Q);
    std::vector<char> is_bc(N, 0);
    for (const auto& [idx, val] : p_bc_) { is_bc[idx] = 1; }

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (is_bc[idx]) {
                    A.add_entry(idx, idx, 1.0Q);
                    rhs[idx] = p_bc_.at(idx);
                    continue;
                }
                // Insulator / metal: zero mobility -> freeze carrier density
                if (mu_p_[idx] < EPSILON) {
                    // Use a large diagonal to prevent pivot swapping in dense direct
                    A.add_entry(idx, idx, 1.0e20Q);
                    rhs[idx] = 1.0e20Q * EPSILON;
                    continue;
                }
                real_t center = 0.0Q;
                const real_t w_x = 1.0Q;
                // Match the electron equation's material-clipped transverse
                // control volume, using the hole mobility mask for this row.
                auto active_width = [&](int axis) -> real_t {
                    if (axis == 1) {
                        real_t width = g_.dy_cell(j);
                        if (j > 0 && mu_p_[idx - g_.nx] < EPSILON)
                            width -= 0.5Q * g_.dy_edge(j - 1);
                        if (j + 1 < g_.ny && mu_p_[idx + g_.nx] < EPSILON)
                            width -= 0.5Q * g_.dy_edge(j);
                        return width > EPSILON ? width : g_.dy_cell(j);
                    }
                    real_t width = g_.dz_cell(k);
                    const size_t z_stride = g_.nx * g_.ny;
                    if (k > 0 && mu_p_[idx - z_stride] < EPSILON)
                        width -= 0.5Q * g_.dz_edge(k - 1);
                    if (k + 1 < g_.nz && mu_p_[idx + z_stride] < EPSILON)
                        width -= 0.5Q * g_.dz_edge(k);
                    return width > EPSILON ? width : g_.dz_cell(k);
                };
                const real_t w_y = g_.dx_cell(i) / active_width(1);
                const real_t w_z = g_.dx_cell(i) / active_width(2);
                const real_t dz_p = g_.dz_edge(k);
                const real_t dz_m = (k > 0) ? g_.dz_edge(k-1) : g_.dz;
                auto add_link = [&](size_t nbr, real_t dx, real_t mu, real_t w) {
                    // Skip coupling to insulator/metal neighbors: zero carrier flux
                    if (mu_p_[nbr] < EPSILON) return (real_t)0.0;
                    const std::vector<real_t>& phi_sg = transport_phi ? *transport_phi : phi;
                    real_t dphi = phi_sg[nbr] - phi_sg[idx];
                    real_t B_plus = bernoulli(dphi / opt_.VT);
                    real_t B_minus = bernoulli(-dphi / opt_.VT);
                    // Edge mobility: HARMONIC mean (current conservation fix,
                    // see electron block comment).
                    real_t mu_e = 2.0Q * mu * mu_p_[nbr] / (mu + mu_p_[nbr] + 1e-30Q);
                    // Face-area weighting (see electron block comment).
                    real_t D = w * mu_e * opt_.VT / dx;
                    // Hole SG: J_p = -q*D*[B(dphi/VT)*p_i - B(-dphi/VT)*p_j]
                    // Equation: B_plus*p_i - B_minus*p_j = 0
                    // => diagonal coeff = D*B_plus, off-diagonal = -D*B_minus
                    real_t a_ii = D * B_plus;    // contribution to diagonal (positive)
                    real_t a_ij = -D * B_minus;  // off-diagonal (negative)
                    A.add_entry(idx, nbr, a_ij);
                    return a_ii;
                };
                const real_t hdx_p = g_.dx_edge(i);
                const real_t hdx_m = (i > 0) ? g_.dx_edge(i-1) : g_.dx;
                if (i + 1 < g_.nx) center += add_link(idx + 1, hdx_p, mu_p_[idx], w_x);
                if (i > 0)        center += add_link(idx - 1, hdx_m, mu_p_[idx], w_x);
                if (j + 1 < g_.ny) center += add_link(idx + g_.nx, g_.dy_edge(j), mu_p_[idx], w_y);
                if (j > 0)        center += add_link(idx - g_.nx, g_.dy_edge(j-1), mu_p_[idx], w_y);
                if (k + 1 < g_.nz) center += add_link(idx + g_.nx * g_.ny, dz_p, mu_p_[idx], w_z);
                if (k > 0)        center += add_link(idx - g_.nx * g_.ny, dz_m, mu_p_[idx], w_z);
                real_t ni = intrinsic_density(Eg_[idx], opt_.temperature, Nc_[idx], Nv_[idx], opt_.statistics_type);
                real_t R = 0.0Q;
                if (idx < tau_n_.size() && idx < tau_p_.size() &&
                    tau_n_[idx] > EPSILON && tau_p_[idx] > EPSILON) {
                    real_t np = n[idx] * p[idx];
                    real_t denom = tau_p_[idx] * (n[idx] + ni) + tau_n_[idx] * (p[idx] + ni);
                    if (denom > EPSILON)
                        R = (np - ni * ni) / denom;
                }
                // Auger recombination: R_A = (Cn*n + Cp*p) * (n*p - ni²)
                if (opt_.auger.enabled) {
                    real_t np_ni2 = n[idx] * p[idx] - ni * ni;
                    R += (opt_.auger.Cn * n[idx] + opt_.auger.Cp * p[idx]) * np_ni2;
                }
                real_t G = (idx < G_opt_.size()) ? G_opt_[idx] : 0.0Q;
                if (opt_.btbt.enabled && idx < G_btbt.size()) {
                    G += opt_.btbt.continuity_scale * G_btbt[idx];
                }
                if (opt_.ii.enabled && idx < G_ii.size()) G += G_ii[idx];
                real_t source_scale = g_.dx_cell(i);
                A.add_entry(idx, idx, center);
                rhs[idx] = (G - R) * source_scale;
                // Transient term: backward Euler (see electron block above).
                if (opt_.transient_enabled && idx < opt_.p_prev.size()) {
                    A.add_entry(idx, idx, source_scale / opt_.transient_dt);
                    rhs[idx] += opt_.p_prev[idx] / opt_.transient_dt * source_scale;
                }
            }
        }
    }
    A.finalize();

    SolverOptions cont_opt = LinearSolver::default_continuity_options();
    cont_opt.type = opt_.continuity_solver;
    if (!cont_h_solver_) cont_h_solver_ = std::make_unique<LinearSolver>(cont_opt);
    const Vector initial(p.begin(), p.end());
    Vector x;
    if (!solve_continuity_linear_system(
            A, rhs, initial, *cont_h_solver_, cont_opt, "Hole",
            cont_h_use_banded_direct_, x))
        return false;
    for (size_t i = 0; i < N; ++i)
        p[i] = (x[i] < 0.0Q) ? EPSILON : x[i];
    return true;
}

bool GummelSolver::solve_continuity(const std::vector<real_t>& phi,
                                    std::vector<real_t>& n,
                                    std::vector<real_t>& p,
                                    real_t quantum_mix_scale) {
    // Keep an immutable entry state for failure rollback.  Carrier damping
    // inside a multi-step fixed-phi quantum polish must instead use the
    // immediately preceding inner iterate.  Reusing the entry state on every
    // inner step solves a different, anchored equation
    //
    //     x = d F(x) + (1-d) x_entry,
    //
    // so the update norm can vanish while Q(x)-Q_transport remains finite.
    // This showed up as an irreducible DG residual plateau in strongly
    // inverted refined MOS meshes.
    const std::vector<real_t> n_entry = n, p_entry = p;
    const std::vector<real_t> Qn_ref = Qn_prev_, Qp_ref = Qp_prev_;
    std::vector<real_t> phi_eff_n, phi_eff_p;
    std::vector<real_t> previous_quantum_fixed_point_residual;
    const bool potential_pde = use_potential_form_pde();
    // Preserve the outer Gummel cycle stabilizer during the fixed-phi
    // equation audit.  Resetting this ceiling to its nominal value made a
    // state that was contracting at x0.25 jump back onto the same DG cycle
    // every time the final continuity polish ran.
    const real_t nominal_quantum_mix_ceiling =
        potential_pde ? 0.50Q : 0.05Q;
    const real_t quantum_mix_ceiling = std::max(
        1.0e-5Q, nominal_quantum_mix_ceiling * quantum_mix_scale);
    // A fixed absolute Aitken floor silently defeated the outer x0.0625 and
    // x0.03125 stabilizer levels: once the scalar candidate reached 0.005,
    // further reductions of the ceiling could not reduce the actual update.
    // Preserve the historical 0.005 floor through x0.125.  Only deeper levels
    // (which require an equation-audited stall below) scale it to one percent
    // of the reduced ceiling, so every advertised damping level is effective
    // without destabilizing ordinary continuation points.  Keep a small
    // positive guard against a zero update.
    const real_t aitken_floor_fraction =
        quantum_mix_scale < 0.125Q ? 0.01Q : 0.10Q;
    const real_t minimum_quantum_mix = std::max(
        1.0e-8Q,
        std::min(0.005Q,
                 aitken_floor_fraction * quantum_mix_ceiling));
    real_t quantum_mix = quantum_mix_ceiling;
    real_t best_quantum_residual = 1.0e100Q;
    std::vector<real_t> best_n, best_p, best_Qn, best_Qp;
    // In a converged unipolar MOS state one carrier block can already be
    // orders of magnitude quieter than the other.  Re-solving that settled
    // block after every small Q update is unnecessary block Gauss-Seidel
    // work (and can dominate runtime when it needs the float128 band solver).
    // Lag only the demonstrably quieter block, but solve both species every
    // eighth inner step.  Residual snapshots and early acceptance are allowed
    // only at those full checkpoints, so the returned state still satisfies
    // both continuity equations for the audited transport potential.
    const bool lag_electron_in_polish =
        opt_.enable_quantum && opt_.inner_iterations > 1 &&
        electron_update_final_ >= 0.0Q && hole_update_final_ > 0.0Q &&
        10.0Q * electron_update_final_ < hole_update_final_;
    const bool lag_hole_in_polish =
        opt_.enable_quantum && opt_.inner_iterations > 1 &&
        hole_update_final_ >= 0.0Q && electron_update_final_ > 0.0Q &&
        10.0Q * hole_update_final_ < electron_update_final_;
    auto update_quantum_residual = [&]() -> real_t {
        if (!opt_.enable_quantum || Qn_prev_.size() != n.size()) {
            quantum_residual_final_ = 0.0Q;
            return quantum_residual_final_;
        }
        std::vector<real_t> Qn_state, Qp_state;
        if (potential_pde) {
            dg_.quantum_potential_potential_form(
                n, p, Qn_prev_, Qp_prev_, Qn_state, Qp_state);
        } else {
            dg_.quantum_potential(n, p, Qn_state, Qp_state);
        }
        for (const auto& bc : n_bc_) Qn_state[bc.first] = 0.0Q;
        for (const auto& bc : p_bc_) Qp_state[bc.first] = 0.0Q;
        real_t difference = 0.0Q;
        real_t scale = opt_.VT > 0.0Q ? opt_.VT : 1.0Q;
        for (size_t i = 0; i < n.size(); ++i) {
            const real_t local_carriers = n[i] + p[i] + EPSILON;
            const real_t wn = sqrt_q(std::max(0.0Q, n[i] / local_carriers));
            const real_t wp = sqrt_q(std::max(0.0Q, p[i] / local_carriers));
            difference = std::max(
                difference, wn * abs_q(Qn_state[i] - Qn_prev_[i]));
            difference = std::max(
                difference, wp * abs_q(Qp_state[i] - Qp_prev_[i]));
            scale = std::max(scale, wn * abs_q(Qn_state[i]));
            scale = std::max(scale, wp * abs_q(Qp_state[i]));
        }
        quantum_residual_final_ = difference / scale;
        return quantum_residual_final_;
    };
    for (size_t inner = 0; inner < opt_.inner_iterations; ++inner) {
        const std::vector<real_t> n_previous = n, p_previous = p;
        const bool full_carrier_checkpoint =
            (!lag_electron_in_polish && !lag_hole_in_polish) ||
            inner == 0 || (inner + 1) % 8 == 0;
        const std::vector<real_t>* phi_n = nullptr;
        const std::vector<real_t>* phi_p = nullptr;
        if (opt_.enable_quantum) {
            // Include the lagged density-gradient potential in the SG fluxes.
            // The former post-convergence density rewrite returned a state
            // that satisfied neither Poisson nor continuity and suppressed the
            // DG effect in subthreshold transport.
            dg_.set_thermal_voltage(opt_.VT);
            std::vector<real_t> Qn_new, Qp_new;
            if (potential_pde && Qn_prev_.size() == n.size()) {
                dg_.quantum_potential_potential_form(
                    n, p, Qn_prev_, Qp_prev_, Qn_new, Qp_new);
            } else {
                dg_.quantum_potential(n, p, Qn_new, Qp_new);
            }
            // Ohmic contacts are classical reservoirs.  Remove their DG
            // correction before fixed-point acceleration so permanently
            // constrained boundary entries cannot pollute the Aitken norm.
            for (const auto& bc : n_bc_) Qn_new[bc.first] = 0.0Q;
            for (const auto& bc : p_bc_) Qp_new[bc.first] = 0.0Q;
            if (Qn_prev_.size() != n.size()) {
                Qn_prev_ = Qn_new;
                Qp_prev_ = Qp_new;
            } else {
                // During the nonlinear outer iteration a lagged, damped Q
                // keeps the DG fixed-point map contractive.  The final
                // undamped continuity polish, however, must use the Q
                // computed from the state it returns; otherwise terminal
                // currents are evaluated with a different transport
                // potential and can violate KCL by orders of magnitude in
                // subthreshold operation.
                // Q(n) is the stiffest part of the DG fixed-point map. Keep
                // it under-relaxed even during the final continuity polish;
                // an undamped Q update alternates between interface- and
                // centre-localised charge profiles on refined meshes.
                // Aitken Delta-squared relaxation for the multi-step final
                // polish. Ultra-thin films can make a fixed update alternate
                // between interface- and centre-localised charge.  The same
                // mode occurs in potential form on wider, strongly inverted
                // films, so both DG formulations need the bounded scalar
                // factor.  The ordinary one-step outer Gummel update is not
                // affected.
                if (opt_.inner_iterations > 1) {
                    std::vector<real_t> residual(2 * n.size(), 0.0Q);
                    for (size_t i = 0; i < n.size(); ++i) {
                        const real_t local_carriers = n[i] + p[i] + EPSILON;
                        const real_t wn = sqrt_q(
                            std::max(0.0Q, n[i] / local_carriers));
                        const real_t wp = sqrt_q(
                            std::max(0.0Q, p[i] / local_carriers));
                        if (!lag_electron_in_polish) {
                            residual[i] =
                                wn * (Qn_new[i] - Qn_prev_[i]);
                        }
                        if (!lag_hole_in_polish) {
                            residual[n.size() + i] =
                                wp * (Qp_new[i] - Qp_prev_[i]);
                        }
                    }
                    if (previous_quantum_fixed_point_residual.size() ==
                        residual.size()) {
                        real_t numerator = 0.0Q, denominator = 0.0Q;
                        real_t current_norm2 = 0.0Q, previous_norm2 = 0.0Q;
                        for (size_t i = 0; i < residual.size(); ++i) {
                            const real_t delta = residual[i] -
                                previous_quantum_fixed_point_residual[i];
                            numerator +=
                                previous_quantum_fixed_point_residual[i] * delta;
                            denominator += delta * delta;
                            current_norm2 += residual[i] * residual[i];
                            previous_norm2 +=
                                previous_quantum_fixed_point_residual[i] *
                                previous_quantum_fixed_point_residual[i];
                        }
                        if (denominator > 1.0e-40Q) {
                            real_t candidate =
                                -quantum_mix * numerator / denominator;
                            if (current_norm2 > 1.44Q * previous_norm2) {
                                // Reject aggressive extrapolation as soon as
                                // the fixed-point residual grows by >20%.
                                candidate = std::min(
                                    candidate,
                                    std::max(minimum_quantum_mix,
                                             0.5Q * quantum_mix));
                            }
                            if (std::isfinite((double)candidate)) {
                                quantum_mix = std::max(
                                    minimum_quantum_mix,
                                    std::min(quantum_mix_ceiling, candidate));
                            }
                        }
                    }
                    previous_quantum_fixed_point_residual = std::move(residual);
                } else {
                    quantum_mix = quantum_mix_ceiling;
                }
                for (size_t i = 0; i < n.size(); ++i) {
                    if (!lag_electron_in_polish ||
                        full_carrier_checkpoint) {
                        Qn_prev_[i] =
                            (1.0Q - quantum_mix) * Qn_prev_[i] +
                            quantum_mix * Qn_new[i];
                    }
                    if (!lag_hole_in_polish ||
                        full_carrier_checkpoint) {
                        Qp_prev_[i] =
                            (1.0Q - quantum_mix) * Qp_prev_[i] +
                            quantum_mix * Qp_new[i];
                    }
                }
            }
            // Ohmic contacts are classical reservoirs with prescribed quasi-
            // Fermi levels; do not add a confinement offset at the boundary.
            for (const auto& bc : n_bc_) Qn_prev_[bc.first] = 0.0Q;
            for (const auto& bc : p_bc_) Qp_prev_[bc.first] = 0.0Q;
            phi_eff_n.resize(phi.size());
            phi_eff_p.resize(phi.size());
            for (size_t i = 0; i < phi.size(); ++i) {
                phi_eff_n[i] = phi[i] + Qn_prev_[i];
                phi_eff_p[i] = phi[i] - Qp_prev_[i];
            }
            phi_n = &phi_eff_n;
            phi_p = &phi_eff_p;
        }
        const bool solve_electron_this_inner =
            !lag_electron_in_polish || full_carrier_checkpoint;
        const bool solve_hole_this_inner =
            !lag_hole_in_polish || full_carrier_checkpoint;
        if ((solve_electron_this_inner &&
             !solve_electron_density(phi, n, p, phi_n)) ||
            (solve_hole_this_inner &&
             !solve_hole_density(phi, n, p, phi_p))) {
            n = n_entry;
            p = p_entry;
            Qn_prev_ = Qn_ref;
            Qp_prev_ = Qp_ref;
            return false;
        }
        // Apply carrier damping relative to the immediately preceding inner
        // iterate, not the immutable function-entry rollback state.
        for (size_t i = 0; i < n.size(); ++i) {
            if (opt_.use_log_damping && n[i] > EPSILON && p[i] > EPSILON &&
                n_previous[i] > EPSILON && p_previous[i] > EPSILON) {
                real_t ratio_n = n[i] / n_previous[i];
                real_t ratio_p = p[i] / p_previous[i];
                if (ratio_n > opt_.log_damping_threshold || ratio_n < 1.0Q / opt_.log_damping_threshold) {
                    n[i] = n_previous[i] * exp_q(opt_.cont_damping * log_q(ratio_n));
                } else {
                    n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_previous[i];
                }
                if (ratio_p > opt_.log_damping_threshold || ratio_p < 1.0Q / opt_.log_damping_threshold) {
                    p[i] = p_previous[i] * exp_q(opt_.cont_damping * log_q(ratio_p));
                } else {
                    p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_previous[i];
                }
            } else {
                n[i] = opt_.cont_damping * n[i] + (1.0Q - opt_.cont_damping) * n_previous[i];
                p[i] = opt_.cont_damping * p[i] + (1.0Q - opt_.cont_damping) * p_previous[i];
            }
            if (n[i] < 0.0Q) n[i] = EPSILON;
            if (p[i] < 0.0Q) p[i] = EPSILON;
        }
        // Final fixed-phi DG polishes use a generous iteration cap, but stop
        // as soon as the lagged transport Q is consistent with the returned
        // carrier state.  Linking the gate to the requested nonlinear
        // tolerance avoids both a hidden fixed-iteration error and needless
        // work in bias sweeps with looser accuracy targets.
        if (opt_.enable_quantum && opt_.inner_iterations > 1 && inner >= 7 &&
            full_carrier_checkpoint) {
            const real_t quantum_tol = std::min(
                std::max(100.0Q * opt_.continuity_tol, 1.0e-8Q), 1.0e-4Q);
            const real_t residual = update_quantum_residual();
            if (residual < best_quantum_residual) {
                best_quantum_residual = residual;
                best_n = n; best_p = p;
                best_Qn = Qn_prev_; best_Qp = Qp_prev_;
            }
            if (residual <= quantum_tol) break;
        }
    }
    const real_t final_quantum_residual = update_quantum_residual();
    // Aitken can occasionally propose a poor final step exactly at the
    // iteration cap. Return the best internally consistent (n,p,Q) state
    // visited by the polish instead of leaking that last extrapolation into
    // the outer Gummel iteration.
    if (opt_.enable_quantum && opt_.inner_iterations > 1 &&
        best_quantum_residual < final_quantum_residual && !best_n.empty()) {
        n = std::move(best_n); p = std::move(best_p);
        Qn_prev_ = std::move(best_Qn); Qp_prev_ = std::move(best_Qp);
        quantum_residual_final_ = best_quantum_residual;
    }
    return true;
}

bool GummelSolver::solve(std::vector<real_t>& phi,
                         std::vector<real_t>& n,
                         std::vector<real_t>& p) {
    poisson_res_.clear();
    cont_res_.clear();
    poisson_residual_final_ = -1.0Q;
    quantum_residual_final_ = opt_.enable_quantum ? -1.0Q : 0.0Q;
    electron_update_final_ = -1.0Q;
    hole_update_final_ = -1.0Q;
    phi_was_frozen_ = false;
    const size_t N = Nd_minus_Na_.size();
    // A potential-form bias continuation must start from the transport
    // quantum potential accepted at the preceding bias. Clearing it here made
    // every 25 mV step fall back to one density-form update before slowly
    // returning to the equation-(248) branch, producing a growing oscillatory
    // tail in strong inversion. The legacy density-form map retains its
    // historical per-solve reset; the potential-form state is size-checked
    // and its fixed-point residual is still enforced before acceptance.
    if (!opt_.enable_quantum || !dg_.potential_form_enabled() ||
        Qn_prev_.size() != N || Qp_prev_.size() != N) {
        Qn_prev_.clear();
        Qp_prev_.clear();
    }
    auto quantum_state_acceptable = [&]() -> bool {
        if (!opt_.enable_quantum) return true;
        const real_t quantum_tol = std::min(
            std::max(100.0Q * opt_.continuity_tol, 1.0e-8Q), 1.0e-4Q);
        return quantum_residual_final_ >= 0.0Q &&
               quantum_residual_final_ <= quantum_tol;
    };
    const bool has_mobile_carriers = [&]() {
        for (size_t i = 0; i < N; ++i)
            if (mu_n_[i] > EPSILON || mu_p_[i] > EPSILON) return true;
        return false;
    }();
    const bool has_transport_barrier = [&]() {
        for (size_t i = 0; i < N; ++i)
            if (mu_n_[i] <= EPSILON && mu_p_[i] <= EPSILON) return true;
        return false;
    }();

    // DG semiconductor mask from mobility (mu>0 => semiconductor; mu=0 oxide).
    // Restricts the density-gradient quantum potential to the active region so
    // it doesn't blow up across the Si-oxide material boundary.
    if (opt_.enable_quantum && !mu_n_.empty()) {
        std::vector<char> semi(N, 0);
        for (size_t i = 0; i < N; ++i) semi[i] = (mu_n_[i] > EPSILON || mu_p_[i] > EPSILON) ? 1 : 0;
        dg_.set_semiconductor_mask(semi);
    }

    std::vector<real_t> phi_old(N);
    std::vector<real_t> n_old(N), p_old(N);

    bool phi_frozen = false;
    // P0-3: set when the loop exited via a permanent phi freeze; the
    // convergence verdict is then taken from the true Poisson residual of
    // the polished frozen state (post-loop block below), never from the
    // frozen rel_dPhi==0.
    bool frozen_exit = false;
    // A hybrid warm-up limit cycle is not a Gummel acceptance candidate.  It
    // is a finite seed for the coupled Newton system.  Track that exit
    // separately so the post-loop max-iteration polish does not spend up to
    // 256 additional DG fixed-point solves before the advertised hand-off.
    bool warmup_cycle_handoff = false;
    // P0-3 fix: rel_dphi of the most recent UNFROZEN Poisson update. Once phi
    // is frozen the naive rel_dphi is exactly 0 (phi == phi_old), which used
    // to fake convergence; the convergence test below uses this honest value
    // instead.
    real_t rel_dphi_last_unfrozen = 1.0Q;
    // P0-3 fix: limit-cycle retries. When the freeze condition fires, first
    // pin phi to the cycle mean (average of the last two iterates) and halve
    // the damping — a genuine attempt to break the cycle — up to
    // freeze_retries_left times; only then freeze permanently.
    // issues0719 follow-up: 2 retries (min scale 0.25) were not enough for
    // the stiff inversion-onset feedback of the MoS2 FeFET template, whose
    // phi <-> exp(phi/VT) channel-charge loop has gain < -1 and needs alpha
    // down to O(1e-2) to contract. 8 retries reach scale 1/256 ~ 0.004,
    // which stabilises any real-spectrum fixed-point map; a permanent freeze
    // (judged by the TRUE Poisson residual) remains the last resort.
    size_t freeze_retries_left = 8;
    real_t damping_scale = 1.0Q;
    // Continuity-update damping scale, halved together with the phi damping
    // on limit-cycle retries: the observed cycles on PN junctions and the
    // MoS2 FeFET are dominated by the n/p map (rel_dN ~ 0.3-4 while
    // rel_dPhi ~ 0.05), so damping phi alone cannot break them.
    real_t cont_damping_scale = 1.0Q;
    // Quantum-specific fixed-point damping.  A finite barrier starts at
    // qmix=0.05, but refined material-side meshes can still form a small DG
    // cycle.  Reduce only Q mixing on repeated detections before escalating to
    // Newton; a cooldown gives each new spectral radius time to reveal itself.
    constexpr real_t minimum_quantum_damping_scale = 0.0078125Q;
    real_t quantum_damping_scale = 1.0Q;
    size_t quantum_damping_cooldown = 0;
    // Quantum unipolar sweeps often leave the minority-carrier block settled
    // while the majority carrier and Q map continue to contract.  After three
    // genuinely solved quiet updates, lag only the much quieter species and
    // re-solve it every eighth outer iteration.  Convergence is never tested
    // on a lagged iteration, and the final continuity polish remains an
    // independent equation-level audit.
    size_t electron_quiet_solves = 0;
    size_t hole_quiet_solves = 0;
    // Equation-audit residual progress is a stronger signal than a small
    // phi/update-norm cycle in a DG solve.  Remember only genuine best-value
    // improvements so a rapidly contracting Q audit gets one bounded chance
    // to finish instead of being handed to Newton one checkpoint before the
    // gate.  The grace window expires unless another strong improvement is
    // observed, so a true plateau still takes the normal rescue path.
    real_t best_quantum_audit_residual = 1.0e100Q;
    size_t quantum_audit_improvement_iter = 0;
    bool quantum_audit_strongly_contracting = false;
    // A fixed-point stall can be visible only in the independent Q audit:
    // the lagged outer carrier and Poisson updates may already be tiny while
    // Q(n,p)-Q_transport remains above its equation gate.  Keep a short
    // per-mixing-level audit history so that state also receives the next
    // bounded Q-damping reduction instead of spinning until max_iter.
    std::vector<real_t> quantum_audit_history;
    real_t quantum_audit_history_scale = quantum_damping_scale;
    // A deeply damped Q map can reach the correct branch but contract too
    // slowly to finish before a tiny outer update cycle is detected.  Once
    // per solve, allow that equation-audited state to restart the Q damping
    // spectrum instead of sending it to a coupled Newton solve that cannot
    // repair a lagged-Q fixed point.  The state itself is retained and all
    // equation gates remain unchanged.
    bool quantum_terminal_restart_used = false;
    // Anderson(1) acceleration state (plan0728 §1.2): activated at the
    // FIRST detected limit cycle.  Scalar damping cannot break a cycle
    // whose fixed point is a spiral source (eigenvalue a+bi with a>1 —
    // observed on the Na=1e24/Nd=1e22 junction: oscillation localised at
    // the depletion-edge node, amplitude unchanged at damping 1/256).
    // Anderson mixing extrapolates past the spiral using the previous
    // update residual; if it also cycles, we fall back to damping retries.
    bool anderson_active = false;
    bool anderson_failed = false;
    std::vector<real_t> f_prev(N, 0.0Q);
    bool has_f_prev = false;
    for (size_t iter = 0; iter < opt_.max_iter; ++iter) {
        if (quantum_damping_cooldown > 0)
            --quantum_damping_cooldown;
        phi_old = phi;
        n_old = n;
        p_old = p;
        const std::vector<real_t> Qn_old = Qn_prev_;
        const std::vector<real_t> Qp_old = Qp_prev_;
        const bool carrier_checkpoint = (iter % 8 == 0);
        const bool lag_electron = opt_.enable_quantum &&
            electron_quiet_solves >= 3 && electron_update_final_ >= 0.0Q &&
            hole_update_final_ > 0.0Q &&
            10.0Q * electron_update_final_ < hole_update_final_;
        const bool lag_hole = opt_.enable_quantum &&
            hole_quiet_solves >= 3 && hole_update_final_ >= 0.0Q &&
            electron_update_final_ > 0.0Q &&
            10.0Q * hole_update_final_ < electron_update_final_;

        // --- Step 1: Solve Poisson with frozen n, p (skip if phi already frozen) ---
        // Only the quasi-static LK model (model 0) is refreshed EVERY
        // iteration: it seeks the instantaneous equilibrium P(E) and its
        // spinodal branch memory damps the algebraic P <-> -div(P) loop.
        // The MEMORY models (Preisach model 1, NLS model 2, transient LK)
        // advance their switching state exactly ONCE per solve() — after the
        // FIRST Poisson solve of the step, so phi already carries the new
        // contact BCs — and are then held fixed for the remaining iterations.
        // This (a) decouples the NLS physical dwell time from the iteration
        // count (P0-2 fix), and (b) breaks the stiff P -> -div(P) -> E -> P
        // algebraic cycle: with the play operator refreshed every iteration at
        // fe_relax_=1 the depolarization feedback (gain ~ Ps/(eps*Ec) >> 1)
        // made P flip sign every iteration, so solves never converged and the
        // loop remanence collapsed (observed P alternating +/-Ps*tanh(1) on
        // consecutive bias steps). Stepping the memory state once per bias
        // point is also the correct quasi-static semantics: the loop develops
        // across the sweep, not inside one solve.
        if (opt_.ferro.enabled &&
            opt_.ferro.model == FerroelectricModel::LANDAU_KHALATNIKOV &&
            !opt_.transient_enabled) {
            poisson_.update_ferroelectric_polarization(phi);
        }
        if (!phi_frozen) {
            std::vector<real_t> n_solve = n, p_solve = p;
            // Fermi-Dirac statistics: correct the carrier densities used in
            // Poisson.  The SG continuity solve gives Boltzmann n; for Poisson
            // charge we need n_FD = Nc * F_{1/2}(ln(n/Nc)).  At moderate
            // doping (n << Nc) the correction γ = F_{1/2}/exp ≈ 1 (Boltzmann).
            // At high doping (n ~ Nc) γ < 1 (degenerate, lower effective n).
            if (opt_.statistics_type == StatisticsType::FERMI_DIRAC) {
                for (size_t i = 0; i < N; ++i) {
                    if (n_solve[i] > 1.0Q && Nc_[i] > 1.0Q) {
                        real_t eta = log_q(n_solve[i] / Nc_[i]);
                        n_solve[i] = Nc_[i] * fermi_dirac_half(eta);
                    }
                    if (p_solve[i] > 1.0Q && Nv_[i] > 1.0Q) {
                        real_t eta = log_q(p_solve[i] / Nv_[i]);
                        p_solve[i] = Nv_[i] * fermi_dirac_half(eta);
                    }
                }
            }
            poisson_.set_leakage_field(phi);
            poisson_.assemble(n_solve, p_solve);
            if (!poisson_.solve(phi)) {
                std::cerr << "Gummel iter " << iter << ": Poisson solve failed\n";
                phi = phi_old; n = n_old; p = p_old;
                Qn_prev_ = Qn_old; Qp_prev_ = Qp_old;
                return false;
            }
            // Memory-model FE state advance (Preisach model 1, NLS model 2,
            // transient LK), exactly once per solve() call, at iteration 0 —
            // using the UNDAMPED predictor phi right out of the linear solve
            // (exact field for the old P and the new contact BCs). Using the
            // damped/log-capped phi here was wrong: on the first iteration
            // the cap distorts phi along x, so E is non-uniform and the
            // memory state gets permanently graded (observed P graded
            // 1e-3..1 C/m^2 and >100-iteration non-convergence on an AlScN
            // slab that is exactly linear with fixed P).
            if (opt_.ferro.enabled && iter == 0 &&
                (opt_.ferro.model != FerroelectricModel::LANDAU_KHALATNIKOV ||
                 opt_.transient_enabled)) {
                if (opt_.transient_enabled) {
                    poisson_.update_ferroelectric_polarization_transient(phi, opt_.transient_dt);
                } else {
                    poisson_.update_ferroelectric_polarization(phi);
                }
            }
            // Damping for phi: uniform linear damping + optional log cap for extremes
            real_t current_damping = opt_.damping * damping_scale;
            if (opt_.adaptive_damping && iter >= 10 && poisson_res_.size() >= opt_.oscillation_window) {
                // Detect oscillation: rel_dPhi increasing for several consecutive iterations
                bool increasing = true;
                for (size_t k = 1; k <= opt_.oscillation_window; ++k) {
                    if (poisson_res_[poisson_res_.size() - k] <=
                        poisson_res_[poisson_res_.size() - k - 1]) {
                        increasing = false;
                        break;
                    }
                }
                if (increasing) {
                    current_damping *= 0.7Q;
                    if (current_damping < opt_.min_damping) current_damping = opt_.min_damping;
                    std::cout << "  [Adaptive] phi damping reduced to " << (double)current_damping << std::endl;
                }
            }
            {
                // Fixed-point residual of THIS Poisson map (undamped update).
                std::vector<real_t> f_k(N);
                for (size_t i = 0; i < N; ++i) f_k[i] = phi[i] - phi_old[i];
                if (anderson_active && !anderson_failed) {
                    // Anderson(1): x_{k+1} = G(x_k) - beta*(f_k - f_{k-1}),
                    // beta = <f_k - f_{k-1}, f_k> / ||f_k - f_{k-1}||^2.
                    real_t beta = 0.0Q;
                    if (has_f_prev) {
                        real_t num = 0.0Q, den = 0.0Q;
                        for (size_t i = 0; i < N; ++i) {
                            real_t d = f_k[i] - f_prev[i];
                            num += d * f_k[i];
                            den += d * d;
                        }
                        if (den > 1e-300Q) beta = num / den;
                    }
                    // Safeguard: clamp the extrapolation factor and cap the
                    // final update (as in the damped path).
                    if (beta > 3.0Q) beta = 3.0Q;
                    if (beta < -3.0Q) beta = -3.0Q;
                    for (size_t i = 0; i < N; ++i) {
                        real_t upd = f_k[i] - beta * (f_k[i] - f_prev[i]);
                        real_t cap = opt_.phi_log_damp_threshold * opt_.VT;
                        if (has_mobile_carriers && abs_q(upd) > cap) {
                            real_t sign = (upd > 0.0Q) ? 1.0Q : -1.0Q;
                            upd = sign * cap * log_q(1.0Q + abs_q(upd) / cap);
                        }
                        phi[i] = phi_old[i] + upd;
                    }
                } else {
                    for (size_t i = 0; i < N; ++i) {
                        real_t upd = f_k[i] * current_damping;
                        // Step 2: soft log cap for extreme swings (prevents Inf/NaN)
                        real_t cap = opt_.phi_log_damp_threshold * opt_.VT;
                        if (has_mobile_carriers && abs_q(upd) > cap) {
                            real_t sign = (upd > 0.0Q) ? 1.0Q : -1.0Q;
                            upd = sign * cap * log_q(1.0Q + abs_q(upd) / cap);
                        }
                        phi[i] = phi_old[i] + upd;
                    }
                }
                f_prev = f_k;
                has_f_prev = true;
            }
            // P0-3 fix: honest update norm of THIS unfrozen iteration,
            // recorded BEFORE any freeze reset below.
            {
                real_t dphi_u = 0.0Q, scale_u = 1.0Q;
                for (size_t i = 0; i < N; ++i) {
                    dphi_u = std::max(dphi_u, abs_q(phi[i] - phi_old[i]));
                    scale_u = std::max(scale_u, abs_q(phi[i]));
                }
                rel_dphi_last_unfrozen = dphi_u / (scale_u + 1.0Q);
            }
            // Detect stable limit-cycle oscillation:
            // Requirements:
            //  1. iter >= 20 (don't freeze early)
            //  2. Amplitude is small (< 0.1 relative)
            //  3. At least 2 rises in the last 5 consecutive pairs (true oscillation)
            //  4. Overall variation in the last 6 iters is modest (< 30%)
            // Condition 3 is the key discriminator: slow monotonic convergence has
            // 0 or 1 rises, while a limit-cycle has 2+.
            // NEVER freeze while the quasi-static LK model is actively
            // re-seeding P every iteration: there the phi oscillation can be
            // GENUINE well-hopping during ferroelectric switching, and
            // pinning phi to the cycle mean parks the field between the two
            // spinodal points so P relaxes back into the old well —
            // destroying the very switching the drive is supposed to cause
            // (regression: test_p_switches_when_drive_exceeds_coercive_field).
            // The memory models (Preisach/NLS/transient) hold P fixed after
            // iter 0, so their limit cycles are purely numerical and remain
            // eligible for freeze/retry.
            const bool lk_active = opt_.ferro.enabled &&
                opt_.ferro.model == FerroelectricModel::LANDAU_KHALATNIKOV &&
                !opt_.transient_enabled;
            if (!lk_active && iter >= 20 && poisson_res_.size() >= 6 &&
                quantum_damping_cooldown == 0) {
                real_t max_r = poisson_res_[poisson_res_.size()-1];
                real_t min_r = max_r;
                size_t rises = 0, phi_reversals = 0;
                real_t prev_delta = 0.0Q;
                for (size_t k = 0; k < 5; ++k) {
                    real_t r1 = poisson_res_[poisson_res_.size()-1-k];
                    real_t r2 = poisson_res_[poisson_res_.size()-2-k];
                    if (r1 > r2) ++rises;
                    real_t delta = r1 - r2;
                    if (prev_delta * delta < 0.0Q) ++phi_reversals;
                    prev_delta = delta;
                    max_r = std::max(max_r, r1);
                    max_r = std::max(max_r, r2);
                    min_r = std::min(min_r, r1);
                    min_r = std::min(min_r, r2);
                }
                // 2026-08: ALSO detect a period-2 CARRIER cycle (rel_dN/rel_dP
                // alternating high/low while rel_dPhi drifts down slowly) —
                // the GAA nanosheet cycles exactly this way (rel_dN flipping
                // 6.389 <-> 0.865 for 100+ iterations with rel_dPhi < 0.01,
                // invisible to the phi-only detector above).
                bool carrier_cycle = false;
                if (cont_res_.size() >= 6) {
                    // A period-2 cycle must reverse direction repeatedly.
                    // The old ratio-only test classified ordinary geometric
                    // convergence (r, r/2, r/4, ...) as a cycle because every
                    // consecutive pair differed by >2x.
                    size_t reversals = 0, large_jumps = 0;
                    real_t prev_delta = 0.0Q;
                    const size_t first = cont_res_.size() - 6;
                    for (size_t t = first + 1; t < cont_res_.size(); ++t) {
                        real_t a = cont_res_[t];
                        real_t b = cont_res_[t - 1];
                        real_t delta = a - b;
                        if (prev_delta * delta < 0.0Q) ++reversals;
                        if (a > 0.0Q && b > 0.0Q &&
                            (a / b > 2.0Q || b / a > 2.0Q)) ++large_jumps;
                        prev_delta = delta;
                    }
                    carrier_cycle = (reversals >= 3 && large_jumps >= 3);
                }
                // A refined DG map can also settle onto a small nonzero
                // plateau without the >2x jumps required by the period-2
                // detector.  Waiting for max_iter in that state is wasted
                // work: the only contracting action is another Q-mixing
                // reduction.  Require 24 consecutive carrier updates with
                // <25% spread, less than 20% net improvement, and a level at
                // least 20x above the requested gate.  Restrict this trigger
                    // to quantum solves that still have a lower mixing level, so
                    // ordinary slow convergence and the terminal mixing policy
                // are never handed to Newton merely for being monotone.
                bool quantum_stall = false;
                if (opt_.enable_quantum &&
                    quantum_damping_scale > minimum_quantum_damping_scale &&
                    cont_res_.size() >= 24) {
                    const size_t first = cont_res_.size() - 24;
                    real_t carrier_min = cont_res_[first];
                    real_t carrier_max = carrier_min;
                    for (size_t t = first + 1; t < cont_res_.size(); ++t) {
                        carrier_min = std::min(carrier_min, cont_res_[t]);
                        carrier_max = std::max(carrier_max, cont_res_[t]);
                    }
                    const real_t carrier_first = cont_res_[first];
                    const real_t carrier_last = cont_res_.back();
                    quantum_stall = carrier_min > 20.0Q * opt_.continuity_tol &&
                        carrier_max < 1.25Q * carrier_min &&
                        carrier_last > 0.80Q * carrier_first;
                }
                // Only freeze when oscillation amplitude is small (< 0.1),
                // and there are at least 2 rises in the last 5 pairs (true oscillation).
                if (carrier_cycle || quantum_stall ||
                    (opt_.enable_phi_freezing && min_r > 0 && max_r < 1e-1Q && rises >= 2 &&
                    phi_reversals >= 3 &&
                    (max_r - min_r) / min_r < 0.3Q)) {
                    // Warm-up mode (Gummel->Newton cascade): hand the
                    // cycle-mean state to the Newton polish at the FIRST
                    // detected cycle (see GummelOptions).
                    if (opt_.exit_on_limit_cycle) {
                        const bool quantum_audit_grace =
                            opt_.enable_quantum &&
                            quantum_damping_scale <= 0.125Q &&
                            quantum_audit_strongly_contracting &&
                            iter <= quantum_audit_improvement_iter + 16;
                        if (quantum_audit_grace) {
                            quantum_damping_cooldown = 8;
                            std::cout
                                << "  [Stabilize] update cycle at iter "
                                << iter
                                << " while audited quantum residual is "
                                   "contracting; allowing one checkpoint"
                                << std::endl;
                            continue;
                        }
                        for (size_t i = 0; i < N; ++i)
                            phi[i] = 0.5Q * (phi[i] + phi_old[i]);
                        const bool audited_current_quantum_level =
                            quantum_audit_history_scale ==
                                quantum_damping_scale &&
                            !quantum_audit_history.empty();
                        if (opt_.enable_quantum &&
                            quantum_damping_scale >
                                minimum_quantum_damping_scale &&
                            (quantum_damping_scale > 0.125Q ||
                             audited_current_quantum_level)) {
                            quantum_damping_scale *= 0.5Q;
                            quantum_damping_cooldown = 20;
                            std::cout << "  [Stabilize] quantum "
                                      << (quantum_stall ? "fixed-point stall" :
                                                          "limit cycle")
                                      << " at iter " << iter
                                      << "; reducing Q mixing to x"
                                      << (double)quantum_damping_scale
                                      << " before Newton handoff" << std::endl;
                            continue;
                        }
                        const real_t quantum_tol = std::min(
                            std::max(100.0Q * opt_.continuity_tol, 1.0e-8Q),
                            1.0e-4Q);
                        const bool terminal_quantum_restart =
                            opt_.enable_quantum &&
                            quantum_damping_scale <=
                                minimum_quantum_damping_scale &&
                            audited_current_quantum_level &&
                            !quantum_terminal_restart_used &&
                            std::isfinite(
                                (double)best_quantum_audit_residual) &&
                            best_quantum_audit_residual <
                                100.0Q * quantum_tol;
                        if (terminal_quantum_restart) {
                            quantum_terminal_restart_used = true;
                            quantum_damping_scale = 1.0Q;
                            quantum_damping_cooldown = 20;
                            quantum_audit_history.clear();
                            quantum_audit_history_scale =
                                quantum_damping_scale;
                            quantum_audit_strongly_contracting = false;
                            std::cout
                                << "  [Stabilize] terminal Q cycle with "
                                   "audited residual "
                                << (double)best_quantum_audit_residual
                                << "; restarting Q mixing from the accepted "
                                   "state"
                                << std::endl;
                            continue;
                        }
                        warmup_cycle_handoff = true;
                        std::cout << "  [Stabilize] limit cycle at iter " << iter
                                  << " (rel_dPhi=" << (double)max_r
                                  << "); handing off to Newton polish" << std::endl;
                        break;
                    }
                    if (freeze_retries_left > 0) {
                        // Cycle-mean retry (P0-3): pin phi to the average of
                        // the last two iterates (a better fixed-point estimate
                        // than either endpoint of a 2-cycle) and halve the
                        // damping, then keep iterating — a genuine attempt to
                        // break the limit cycle before freezing permanently.
                        for (size_t i = 0; i < N; ++i)
                            phi[i] = 0.5Q * (phi[i] + phi_old[i]);
                        // First detection: engage Anderson(1) acceleration
                        // instead of blind damping — a spiral-source cycle
                        // cannot be damped away but can be extrapolated.
                        // If Anderson also fails (a later detection), the
                        // damping retry path below remains as fallback.
                        if (!anderson_active && !anderson_failed) {
                            anderson_active = true;
                            has_f_prev = false;
                            std::cout << "  [Stabilize] limit cycle at iter " << iter
                                      << " (rel_dPhi=" << (double)max_r
                                      << "); engaging Anderson(1) acceleration"
                                      << std::endl;
                            continue;
                        }
                        // Anderson was tried and the cycle persists: fall
                        // back to damping retries from here on.
                        if (anderson_active && !anderson_failed) {
                            anderson_failed = true;
                            std::cout << "  [Stabilize] Anderson acceleration "
                                      << "did not break the cycle; falling "
                                      << "back to damping retries" << std::endl;
                        }
                        // Early honest acceptance, judged the SAME way as
                        // the frozen/max_iter exits: polish continuity
                        // EXACTLY at the cycle-mean phi, then take the true
                        // Poisson residual. The polish runs on copies. A
                        // complete Poisson-consistent (n,p,Q) candidate can
                        // continue as an intermediate iterate; a candidate
                        // that fails the Poisson gate is rolled back.
                        {
                            std::vector<real_t> n_try = n, p_try = p;
                            const std::vector<real_t> Qn_try_start = Qn_prev_;
                            const std::vector<real_t> Qp_try_start = Qp_prev_;
                            bool polish_ok = true;
                            if (opt_.cont_damping < 1.0Q || opt_.use_log_damping) {
                                GummelOptions saved = opt_;
                                opt_.cont_damping = 1.0Q;
                                opt_.use_log_damping = false;
                                opt_.inner_iterations = opt_.enable_quantum
                                    ? (use_potential_form_pde() ? 64 : 256)
                                    : 1;
                                polish_ok = solve_continuity(
                                    phi, n_try, p_try,
                                    quantum_damping_scale);
                                opt_ = saved;
                            }
                            real_t cyc_res = polish_ok
                                ? compute_poisson_residual(phi, n_try, p_try)
                                : 1.0e100Q;
                            if (polish_ok &&
                                std::isfinite((double)cyc_res) &&
                                cyc_res < opt_.frozen_residual_gate &&
                                quantum_state_acceptable()) {
                                n = n_try;
                                p = p_try;
                                phi_was_frozen_ = true;
                                poisson_residual_final_ = cyc_res;
                                std::cout << "Gummel converged (cycle-mean at iter "
                                          << iter << ", true Poisson residual="
                                          << (double)cyc_res << ")\n";
                                return true;
                            }
                            // solve_continuity advances Q together with n/p.
                            // If the true Poisson equation already passes,
                            // keep the complete intermediate state for the
                            // next outer iteration, but do not report success
                            // until the explicit Q gate also passes. Otherwise
                            // roll Q back with the discarded carrier fields.
                            if (polish_ok && std::isfinite((double)cyc_res) &&
                                cyc_res < opt_.frozen_residual_gate) {
                                n = std::move(n_try);
                                p = std::move(p_try);
                            } else {
                                Qn_prev_ = Qn_try_start;
                                Qp_prev_ = Qp_try_start;
                            }
                        }
                        --freeze_retries_left;
                        damping_scale *= 0.5Q;
                        cont_damping_scale *= 0.5Q;
                        std::cout << "  [Stabilize] limit cycle at iter " << iter
                                  << " (rel_dPhi=" << (double)max_r
                                  << "): retry with damping x" << (double)damping_scale
                                  << std::endl;
                    } else {
                        // Permanent freeze (P0-3): pin phi to the cycle mean
                        // and EXIT the loop immediately. Continuing to iterate
                        // with a pinned phi only drifts n,p away from
                        // consistency with it (the old code then declared
                        // "convergence" on the fake rel_dPhi=0 while the true
                        // Poisson residual of the returned state was O(1)).
                        // The verdict is decided after the loop from the TRUE
                        // Poisson residual of the polished frozen state.
                        phi_frozen = true;
                        phi_was_frozen_ = true;
                        frozen_exit = true;
                        for (size_t i = 0; i < N; ++i)
                            phi[i] = 0.5Q * (phi[i] + phi_old[i]);
                        std::cout << "  [Stabilize] phi frozen at iter " << iter
                                  << " (rel_dPhi=" << (double)max_r
                                  << "); judging by true residual" << std::endl;
                        break;
                    }
                }
            }
        }

        // --- Step 2: solve continuity with the physical electrostatic
        // potential plus a lagged density-gradient transport potential. ---
        std::vector<real_t> phi_eff_n, phi_eff_p;
        const std::vector<real_t>* phi_n = nullptr;
        const std::vector<real_t>* phi_p = nullptr;
        if (opt_.enable_quantum) {
            dg_.set_thermal_voltage(opt_.VT);
            std::vector<real_t> Qn_new, Qp_new;
            if (use_potential_form_pde() && Qn_prev_.size() == N) {
                dg_.quantum_potential_potential_form(
                    n_old, p_old, Qn_prev_, Qp_prev_, Qn_new, Qp_new);
            } else {
                dg_.quantum_potential(n_old, p_old, Qn_new, Qp_new);
            }
            if (Qn_prev_.size() != N) {
                Qn_prev_ = Qn_new;
                Qp_prev_ = Qp_new;
            } else {
                // A finite hard-wall barrier needs contractive Q mixing from
                // the first iteration: once a wider film jumps to the other
                // DG branch, reducing the factor after cycle detection is too
                // late. Bulk all-semiconductor DG remains stable at 0.10.
                const real_t qmix = use_potential_form_pde()
                    ? 0.20Q
                    : (has_transport_barrier ? 0.05Q : 0.10Q);
                const real_t qmix_effective =
                    qmix * quantum_damping_scale;
                for (size_t q = 0; q < N; ++q) {
                    if (!lag_electron || carrier_checkpoint) {
                        Qn_prev_[q] =
                            (1.0Q - qmix_effective) * Qn_prev_[q] +
                            qmix_effective * Qn_new[q];
                    }
                    if (!lag_hole || carrier_checkpoint) {
                        Qp_prev_[q] =
                            (1.0Q - qmix_effective) * Qp_prev_[q] +
                            qmix_effective * Qp_new[q];
                    }
                }
            }
            for (const auto& bc : n_bc_) Qn_prev_[bc.first] = 0.0Q;
            for (const auto& bc : p_bc_) Qp_prev_[bc.first] = 0.0Q;
            phi_eff_n.resize(N);
            phi_eff_p.resize(N);
            for (size_t q = 0; q < N; ++q) {
                phi_eff_n[q] = phi[q] + Qn_prev_[q];
                phi_eff_p[q] = phi[q] - Qp_prev_[q];
            }
            phi_n = &phi_eff_n;
            phi_p = &phi_eff_p;
        }
        const bool solved_electron = !lag_electron || carrier_checkpoint;
        const bool solved_hole = !lag_hole || carrier_checkpoint;
        if (solved_electron && !solve_electron_density(phi, n, p, phi_n)) {
            std::cerr << "Gummel iter " << iter << ": Electron continuity failed\n";
            phi = phi_old; n = n_old; p = p_old;
            Qn_prev_ = Qn_old; Qp_prev_ = Qp_old;
            return false;
        }
        if (solved_hole && !solve_hole_density(phi, n, p, phi_p)) {
            std::cerr << "Gummel iter " << iter << ": Hole continuity failed\n";
            phi = phi_old; n = n_old; p = p_old;
            Qn_prev_ = Qn_old; Qp_prev_ = Qp_old;
            return false;
        }
        // Damping for n and p (cont_damping_scale is halved on limit-cycle
        // retries together with the phi damping — see declaration above).
        const real_t cont_damp = opt_.cont_damping * cont_damping_scale;
        for (size_t i = 0; i < N; ++i) {
            if (opt_.use_log_damping && n_old[i] > EPSILON && p_old[i] > EPSILON) {
                // Log-space blend for ALL ratios (plan0728 §1.2): the linear
                // blend n_new = a*n + (1-a)*n_old is USELESS across orders of
                // magnitude (dominated by whichever side is larger), and the
                // old threshold version let ratios of 1e6 through with a 0.5
                // exponent (= 1e3 change per iteration).  The depletion-edge
                // limit cycle on extreme-doping junctions (node-level
                // p ~ 1e6x Na overshoot) is fed by exactly that unbounded
                // multiplicative swing.  Blend in log space and hard-cap the
                // per-iteration log change, so a single Boltzmann swing
                // cannot move a node by orders of magnitude.
                real_t dl_n = cont_damp * log_q(n[i] / n_old[i]);
                real_t dl_p = cont_damp * log_q(p[i] / p_old[i]);
                const real_t LOG_CAP = 2.0Q;   // max ~7.4x change per iteration
                if (dl_n > LOG_CAP) dl_n = LOG_CAP; else if (dl_n < -LOG_CAP) dl_n = -LOG_CAP;
                if (dl_p > LOG_CAP) dl_p = LOG_CAP; else if (dl_p < -LOG_CAP) dl_p = -LOG_CAP;
                n[i] = n_old[i] * exp_q(dl_n);
                p[i] = p_old[i] * exp_q(dl_p);
            } else {
                n[i] = cont_damp * n[i] + (1.0Q - cont_damp) * n_old[i];
                p[i] = cont_damp * p[i] + (1.0Q - cont_damp) * p_old[i];
            }
            if (n[i] < 0.0Q) n[i] = EPSILON;
            if (p[i] < 0.0Q) p[i] = EPSILON;
        }

        // --- Step 3: Convergence check ---
        real_t dphi = 0.0Q, dn = 0.0Q, dp = 0.0Q;
        real_t phi_scale = 1.0Q, n_scale = 1.0Q, p_scale = 1.0Q;
        bool has_nan = false;
        for (size_t i = 0; i < N; ++i) {
            if (std::isnan((double)phi[i]) || std::isnan((double)n[i]) || std::isnan((double)p[i]) ||
                std::isinf((double)phi[i]) || std::isinf((double)n[i]) || std::isinf((double)p[i])) {
                has_nan = true;
                break;
            }
            dphi = std::max(dphi, abs_q(phi[i] - phi_old[i]));
            dn   = std::max(dn,   abs_q(n[i]   - n_old[i]));
            dp   = std::max(dp,   abs_q(p[i]   - p_old[i]));
            phi_scale = std::max(phi_scale, abs_q(phi[i]));
            n_scale   = std::max(n_scale,   abs_q(n[i]));
            p_scale   = std::max(p_scale,   abs_q(p[i]));
        }

        if (has_nan) {
            std::cerr << "Gummel iter " << iter << ": NaN/Inf detected, aborting\n";
            phi = phi_old; n = n_old; p = p_old;
            Qn_prev_ = Qn_old; Qp_prev_ = Qp_old;
            return false;
        }

        real_t rel_dphi = dphi / (phi_scale + 1.0Q);
        // Scale both species by the total mobile-charge scale.  Independent
        // species normalization lets an exponentially small minority carrier
        // dominate the coupled convergence/cycle detector despite having no
        // measurable effect on Poisson.  The final undamped continuity polish
        // still solves both carrier equations exactly before acceptance.
        const real_t carrier_scale = std::max(n_scale, p_scale);
        real_t rel_dn   = dn / (carrier_scale + 1.0Q);
        real_t rel_dp   = dp / (carrier_scale + 1.0Q);
        real_t rel_cont = std::max(rel_dn, rel_dp);
        electron_update_final_ = rel_dn;
        hole_update_final_ = rel_dp;
        const real_t quiet_gate = 0.5Q * opt_.continuity_tol;
        const bool electron_relatively_quiet =
            rel_dp > 100.0Q * opt_.continuity_tol &&
            100.0Q * rel_dn < rel_dp;
        const bool hole_relatively_quiet =
            rel_dn > 100.0Q * opt_.continuity_tol &&
            100.0Q * rel_dp < rel_dn;
        if (solved_electron) {
            electron_quiet_solves =
                (rel_dn < quiet_gate || electron_relatively_quiet)
                ? electron_quiet_solves + 1 : 0;
        }
        if (solved_hole) {
            hole_quiet_solves =
                (rel_dp < quiet_gate || hole_relatively_quiet)
                ? hole_quiet_solves + 1 : 0;
        }

        poisson_res_.push_back(rel_dphi);
        cont_res_.push_back(rel_cont);

        std::cout << "Gummel iter " << iter
                  << "  rel_dPhi=" << (double)rel_dphi
                  << "  rel_dN=" << (double)rel_dn
                  << "  rel_dP=" << (double)rel_dp << std::endl;

        // P0-3 fix: once phi is frozen the naive rel_dphi is exactly 0
        // (phi == phi_old), which used to fake convergence even though the
        // true update norm at freeze time was O(1e-2); use the honest
        // last-unfrozen update norm instead.
        real_t rel_dphi_test = phi_frozen ? rel_dphi_last_unfrozen : rel_dphi;
        // The update norm is only a trigger for the transactional equation
        // audit below, not an acceptance residual.  In a strongly unipolar
        // quantum state the minority-carrier linear solve can sit a few ulps
        // above the requested update tolerance after normalization by the
        // total mobile charge.  Requiring that harmless block to cross the
        // exact threshold before running the undamped two-carrier polish can
        // create an artificial outer cycle.  Permit a bounded near-gate
        // audit on a simultaneous carrier checkpoint; the candidate is still
        // accepted only after the checked continuity solve plus the original
        // Poisson and quantum equation gates pass.
        bool quantum_near_update_audit = false;
        if (opt_.enable_quantum && iter >= 20 &&
            rel_cont >= opt_.continuity_tol &&
            rel_cont < 8.0Q * opt_.continuity_tol &&
            cont_res_.size() >= 8) {
            const size_t first = cont_res_.size() - 8;
            real_t near_min = cont_res_[first];
            real_t near_max = near_min;
            for (size_t t = first + 1; t < cont_res_.size(); ++t) {
                near_min = std::min(near_min, cont_res_[t]);
                near_max = std::max(near_max, cont_res_[t]);
            }
            quantum_near_update_audit =
                near_max < 1.10Q * near_min &&
                cont_res_.back() > 0.95Q * cont_res_[first];
        }
        if (solved_electron && solved_hole &&
            rel_dphi_test < opt_.poisson_tol &&
            (rel_cont < opt_.continuity_tol ||
             quantum_near_update_audit)) {
            std::cout << "Gummel update norms reached equation-audit gate in "
                      << iter + 1
                      << " iterations; checking final equation residuals.\n";

            // --- Final undamped continuity polish --------------------------------
            // Throughout the iteration the carrier updates were under-relaxed
            // (cont_damping < 1) for stability.  The returned (n,p) therefore
            // do *not* exactly satisfy the discrete continuity equations for
            // the converged phi, which breaks Kirchhoff's current law by O(1)
            // on biased devices (see audit0618.md §10.3).  Re-solve continuity
            // once with damping disabled so the returned fields are the true
            // discrete steady state at this phi.  phi is held fixed here, so
            // the Poisson-continuity coupling is not perturbed.
            // Polish on copies. A Poisson-consistent intermediate state may
            // continue iterating toward the Q gate; a Poisson-inconsistent
            // candidate is rolled back transactionally.
            std::vector<real_t> n_try = n, p_try = p;
            const std::vector<real_t> Qn_try_start = Qn_prev_;
            const std::vector<real_t> Qp_try_start = Qp_prev_;
            const real_t quantum_audit_reference =
                best_quantum_audit_residual;
            bool polish_ok = true;
            if (opt_.cont_damping < 1.0Q || opt_.use_log_damping) {
                GummelOptions polish_opt = opt_;
                polish_opt.cont_damping = 1.0Q;       // no relaxation
                polish_opt.use_log_damping = false;    // no log-space blend
                // Allow a bounded fixed-phi solve; the explicit
                // Q(n,p)-to-transport-Q residual provides early exit.
                polish_opt.inner_iterations = opt_.enable_quantum
                    ? (use_potential_form_pde() ? 64 : 256)
                    : 1;
                // Temporarily swap options for the polish call.
                GummelOptions saved = opt_;
                opt_ = polish_opt;
                polish_ok = solve_continuity(
                    phi, n_try, p_try, quantum_damping_scale);
                opt_ = saved;
                if (!polish_ok) {
                    std::cerr << "Gummel final continuity polish failed; "
                              << "rejecting candidate\n";
                    return false;
                }
            }
            // P0-3: true Poisson equation residual at the returned state.
            // Re-solve Poisson to ensure phi is consistent with the polished
            // n,p.  Critical for the cycle-mean exit path where phi was pinned
            // to the average of two oscillating iterates — the averaged phi
            // gives wrong SG Bernoulli edge currents.
            poisson_residual_final_ = compute_poisson_residual(phi, n_try, p_try);
            // The fixed-phi DG polish is a transactional equation audit.  A
            // bounded Aitken solve can occasionally land on the opposite
            // confinement branch at its iteration cap, producing a Q
            // residual many orders larger than the already accepted audit.
            // Do not commit that branch to the outer state: besides being a
            // worse approximation, it injects an artificial carrier spike
            // and prevents the per-level audit history from recognizing the
            // otherwise smooth residual plateau.  Modest regressions remain
            // visible to the normal stall/cycle logic; only a non-finite or
            // catastrophic (>8x best) candidate is rolled back.
            const bool quantum_polish_regressed =
                opt_.enable_quantum &&
                (!std::isfinite((double)quantum_residual_final_) ||
                 (quantum_audit_reference < 1.0e99Q &&
                  quantum_residual_final_ >
                      8.0Q * quantum_audit_reference));
            if (opt_.enable_quantum &&
                !quantum_polish_regressed &&
                std::isfinite((double)quantum_residual_final_) &&
                quantum_residual_final_ < best_quantum_audit_residual) {
                quantum_audit_strongly_contracting =
                    best_quantum_audit_residual < 1.0e99Q &&
                    quantum_residual_final_ <
                        0.5Q * best_quantum_audit_residual;
                best_quantum_audit_residual = quantum_residual_final_;
                quantum_audit_improvement_iter = iter;
            }
            if (opt_.enable_quantum &&
                !quantum_polish_regressed &&
                std::isfinite((double)quantum_residual_final_)) {
                if (quantum_damping_scale != quantum_audit_history_scale) {
                    quantum_audit_history.clear();
                    quantum_audit_history_scale = quantum_damping_scale;
                }
                quantum_audit_history.push_back(quantum_residual_final_);
                if (quantum_audit_history.size() > 3) {
                    quantum_audit_history.erase(
                        quantum_audit_history.begin());
                }
            }
            if (std::isfinite((double)poisson_residual_final_) &&
                poisson_residual_final_ < opt_.frozen_residual_gate &&
                !quantum_polish_regressed &&
                quantum_state_acceptable()) {
                n = std::move(n_try);
                p = std::move(p_try);
                std::cout << "Gummel converged in " << iter + 1
                          << " iterations (Poisson residual="
                          << (double)poisson_residual_final_
                          << ", quantum residual="
                          << (double)quantum_residual_final_ << ").\n";
                return true;
            }
            if (polish_ok && std::isfinite((double)poisson_residual_final_) &&
                poisson_residual_final_ < opt_.frozen_residual_gate &&
                !quantum_polish_regressed) {
                // A near-update audit is invoked specifically because a
                // strongly unipolar minority block has stalled just above
                // the update gate.  If its Q equation is not yet acceptable,
                // retain the audited transport-Q progress but let the outer
                // damped continuity iteration absorb it.  Committing the
                // undamped minority candidate here can replace a 1e-7-scale
                // plateau by a 1e-3 carrier jump and recreate the cycle this
                // audit is intended to remove.  Ordinary audits still commit
                // their Poisson-consistent carrier candidate immediately.
                if (!quantum_near_update_audit) {
                    n = std::move(n_try);
                    p = std::move(p_try);
                }
            } else {
                Qn_prev_ = Qn_try_start;
                Qp_prev_ = Qp_try_start;
                if (quantum_polish_regressed) {
                    std::cerr
                        << "Gummel quantum audit candidate regressed from "
                        << (double)quantum_audit_reference << " to "
                        << (double)quantum_residual_final_
                        << "; restoring pre-audit state" << std::endl;
                }
            }
            if (opt_.enable_quantum &&
                quantum_audit_history.size() == 3) {
                const real_t quantum_tol = std::min(
                    std::max(100.0Q * opt_.continuity_tol, 1.0e-8Q),
                    1.0e-4Q);
                const real_t audit_min = *std::min_element(
                    quantum_audit_history.begin(),
                    quantum_audit_history.end());
                const real_t audit_max = *std::max_element(
                    quantum_audit_history.begin(),
                    quantum_audit_history.end());
                const real_t audit_first = quantum_audit_history.front();
                const real_t audit_last = quantum_audit_history.back();
                const bool audited_quantum_stall =
                    audit_min > 2.0Q * quantum_tol &&
                    audit_max < 1.5Q * audit_min &&
                    audit_last > 0.75Q * audit_first;
                if (audited_quantum_stall &&
                    quantum_damping_scale > minimum_quantum_damping_scale) {
                    quantum_damping_scale *= 0.5Q;
                    quantum_damping_cooldown = 20;
                    quantum_audit_history.clear();
                    quantum_audit_history_scale = quantum_damping_scale;
                    quantum_audit_strongly_contracting = false;
                    std::cout
                        << "  [Stabilize] audited quantum residual stalled at "
                        << (double)quantum_residual_final_
                        << "; reducing Q mixing to x"
                        << (double)quantum_damping_scale
                        << " before Newton handoff" << std::endl;
                } else if (audited_quantum_stall &&
                           quantum_damping_scale <=
                               minimum_quantum_damping_scale &&
                           !quantum_terminal_restart_used &&
                           audit_min < 256.0Q * quantum_tol) {
                    // A monotone minimum-damping plateau does not satisfy the
                    // period-2 carrier-cycle detector, so the terminal restart
                    // in that branch is otherwise unreachable.  Three
                    // independent equation audits provide the equivalent,
                    // stronger signal.  Keep the same once-per-solve bound and
                    // require the retained state to be within one eight-bit
                    // damping spectrum of the Q gate before restoring full
                    // mixing.  Acceptance still requires the original
                    // Poisson, continuity and Q equation gates.
                    quantum_terminal_restart_used = true;
                    quantum_damping_scale = 1.0Q;
                    quantum_damping_cooldown = 20;
                    quantum_audit_history.clear();
                    quantum_audit_history_scale =
                        quantum_damping_scale;
                    quantum_audit_strongly_contracting = false;
                    std::cout
                        << "  [Stabilize] terminal audited Q plateau at "
                        << (double)quantum_residual_final_
                        << "; restarting Q mixing from the retained state"
                        << std::endl;
                }
            }
            std::cerr << "Gummel update-norm convergence rejected: Poisson residual="
                      << (double)poisson_residual_final_ << " (gate "
                      << (double)opt_.frozen_residual_gate << ")"
                      << ", quantum residual="
                      << (double)quantum_residual_final_ << std::endl;
        }
    }

    if (warmup_cycle_handoff) {
        // Returning false is intentional: the Gummel stage did not satisfy
        // its equation gates.  DeviceSimulator will keep this finite state as
        // the Newton seed and only report convergence if Newton itself passes.
        poisson_residual_final_ = compute_poisson_residual(phi, n, p);
        return false;
    }

    if (frozen_exit) {
        // P0-3: verdict for a permanently frozen state. Solve the continuity
        // equations EXACTLY at the frozen phi (undamped polish) so the
        // returned (phi, n, p) is at least continuity-consistent, then take
        // the TRUE Poisson equation residual as the acceptance criterion:
        // the frozen state is reported converged only if it actually solves
        // the discrete Poisson equation to frozen_residual_gate.
        if (opt_.cont_damping < 1.0Q || opt_.use_log_damping) {
            GummelOptions saved = opt_;
            opt_.cont_damping = 1.0Q;
            opt_.use_log_damping = false;
            opt_.inner_iterations = opt_.enable_quantum
                ? (use_potential_form_pde() ? 64 : 256)
                : 1;
            bool polish_ok = solve_continuity(
                phi, n, p, quantum_damping_scale);
            opt_ = saved;
            if (!polish_ok) {
                std::cerr << "Gummel frozen-state continuity polish failed; "
                          << "rejecting candidate\n";
                return false;
            }
        }
        poisson_residual_final_ = compute_poisson_residual(phi, n, p);
        if (std::isfinite((double)poisson_residual_final_) &&
            poisson_residual_final_ < opt_.frozen_residual_gate &&
            quantum_state_acceptable()) {
            std::cout << "Gummel converged (frozen state, true Poisson residual="
                      << (double)poisson_residual_final_ << ")\n";
            return true;
        }
        std::cerr << "Gummel frozen state rejected: true Poisson residual="
                  << (double)poisson_residual_final_ << " >= gate "
                  << (double)opt_.frozen_residual_gate << std::endl;
        return false;
    }

    std::cerr << "Gummel did not converge within max_iter\n";
    // P0-3 final honest verdict at the max_iter exit: a stagnated iteration
    // whose update norm never reached tol may STILL satisfy the discrete
    // equations.  Polish the continuity equations exactly (as in the
    // converged/frozen paths) and judge the TRUE Poisson residual against
    // the gate: accepted only if the equations are actually satisfied;
    // genuinely diverged states have O(1) residuals and remain rejected.
    // (Observed: the 2D PN junction current tests stagnate at rel_dPhi~1e-3
    // with a true residual of 1.1e-4 — a valid solution that the update-norm
    // criterion alone would dishonestly fail.)
    // In warm-up mode (exit_on_limit_cycle) the cycle-mean break left phi
    // as the average of two oscillating iterates and n,p from the previous
    // iteration's continuity solve — an inconsistent pair that gives WRONG
    // edge currents (the SG Bernoulli of an averaged phi ≠ average of
    // Bernoullis).  Re-solve Poisson + continuity + Poisson to restore
    // full phi-n consistency before judging the residual.
    if (opt_.exit_on_limit_cycle) {
        poisson_.set_leakage_field(phi);
        poisson_.assemble(n, p);
        if (!poisson_.solve(phi)) return false;
        GummelOptions saved = opt_;
        opt_.cont_damping = 1.0Q;
        opt_.use_log_damping = false;
        opt_.inner_iterations = opt_.enable_quantum
            ? (use_potential_form_pde() ? 64 : 256)
            : 1;
        bool polish_ok = solve_continuity(
            phi, n, p, quantum_damping_scale);
        opt_ = saved;
        if (!polish_ok) {
            std::cerr << "Gummel warm-up continuity polish failed; "
                      << "rejecting candidate\n";
            return false;
        }
        poisson_.assemble(n, p);
        if (!poisson_.solve(phi)) return false;
    } else if (opt_.cont_damping < 1.0Q || opt_.use_log_damping) {
        GummelOptions saved = opt_;
        opt_.cont_damping = 1.0Q;
        opt_.use_log_damping = false;
        opt_.inner_iterations = opt_.enable_quantum
            ? (use_potential_form_pde() ? 64 : 256)
            : 1;
        bool polish_ok = solve_continuity(
            phi, n, p, quantum_damping_scale);
        opt_ = saved;
        if (!polish_ok) {
            std::cerr << "Gummel max_iter continuity polish failed; "
                      << "rejecting candidate\n";
            return false;
        }
    }
    poisson_residual_final_ = compute_poisson_residual(phi, n, p);
    if (std::isfinite((double)poisson_residual_final_) &&
        poisson_residual_final_ < opt_.frozen_residual_gate &&
        quantum_state_acceptable()) {
        std::cout << "Gummel accepted at max_iter (true Poisson residual="
                  << (double)poisson_residual_final_ << " < gate)\n";
        return true;
    }
    return false;
}

real_t GummelSolver::compute_poisson_residual(const std::vector<real_t>& phi,
                                              const std::vector<real_t>& n,
                                              const std::vector<real_t>& p) {
    // The trap occupancy and leakage conductance read the cached phi, so
    // refresh it before re-assembling (mirrors the in-loop usage). NOTE: the
    // Density-Gradient correction is not re-applied here: n and p are the
    // physical charge densities.  Fermi-Dirac statistics, however, MUST use
    // the same effective charge passed to assemble() in the solve loop.  The
    // old residual used raw Boltzmann densities here, so a solved FD system
    // could be rejected forever with zero updates and a finite "true"
    // residual.
    poisson_.set_leakage_field(phi);
    if (opt_.statistics_type != StatisticsType::FERMI_DIRAC)
        return poisson_.residual_norm(phi, n, p);

    std::vector<real_t> n_score = n, p_score = p;
    for (size_t i = 0; i < n_score.size(); ++i) {
        if (n_score[i] > 1.0Q && Nc_[i] > 1.0Q) {
            real_t eta = log_q(n_score[i] / Nc_[i]);
            n_score[i] = Nc_[i] * fermi_dirac_half(eta);
        }
        if (p_score[i] > 1.0Q && Nv_[i] > 1.0Q) {
            real_t eta = log_q(p_score[i] / Nv_[i]);
            p_score[i] = Nv_[i] * fermi_dirac_half(eta);
        }
    }
    return poisson_.residual_norm(phi, n_score, p_score);
}

bool GummelSolver::recompute_poisson(std::vector<real_t>& phi,
                                     const std::vector<real_t>& n,
                                     const std::vector<real_t>& p) {
    poisson_.set_leakage_field(phi);
    poisson_.assemble(n, p);
    return poisson_.solve(phi);
}

void GummelSolver::set_poisson_solver_type(SolverType type) {
    opt_.poisson_solver = type;
    SolverOptions poisson_opt = LinearSolver::default_poisson_options();
    poisson_opt.type = type;
    poisson_.set_solver_options(poisson_opt);
}

void GummelSolver::set_continuity_solver_type(SolverType type) {
    opt_.continuity_solver = type;
}

} // namespace tcad
