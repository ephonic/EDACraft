#include "linear_solver.h"
#include <iostream>
#include <algorithm>
#include <limits>
#include <vector>

// Optional direct LAPACK/BLAS linkage (TCAD_USE_LAPACK=1 at build time).  It is
// disabled in portable wheels because an extension linked against a system
// LAPACK can collide with the private BLAS/LAPACK bundled in SciPy wheels.
#ifdef TCAD_USE_LAPACK
extern "C" {
void dgesv_(const int* n, const int* nrhs, double* A, const int* lda,
            int* ipiv, double* B, const int* ldb, int* info);
void dgbtrf_(const int* m, const int* n, const int* kl, const int* ku,
             double* AB, const int* ldab, int* ipiv, int* info);
void dgbtrs_(const char* trans, const int* n, const int* kl, const int* ku,
             const int* nrhs, const double* AB, const int* ldab,
            const int* ipiv, double* B, const int* ldb, int* info);
}
#endif

#ifdef __APPLE__
// Accelerate framework available but native dense direct solver is self-contained
// #include <Accelerate/Accelerate.h>
#endif

#ifdef TCAD_USE_PETSC
#include <petsc.h>
#include <petscksp.h>
#endif

namespace tcad {

SolverOptions LinearSolver::default_poisson_options() {
    SolverOptions opt;
    opt.type = SolverType::DENSE_DIRECT;
    opt.max_iter = 5000;
#ifdef TCAD_USE_FLOAT128
    opt.tol = 1e-28Q;
#else
    opt.tol = 1e-12Q; // Double precision: match data precision
#endif
    opt.prec = PreconditionerType::NONE;
    opt.verbose = false;
    return opt;
}

SolverOptions LinearSolver::default_continuity_options() {
    SolverOptions opt;
    // Use dense direct for small systems (<2000 nodes) for guaranteed convergence
    opt.type = SolverType::DENSE_DIRECT;
    opt.max_iter = 5000;
    opt.restart = 50;
#ifdef TCAD_USE_FLOAT128
    opt.tol = 1e-28Q;
#else
    opt.tol = 1e-8Q;
#endif
    opt.prec = PreconditionerType::ILU0;
    opt.verbose = false;
    return opt;
}

LinearSolver::LinearSolver(const SolverOptions& opt) : opt_(opt) {}

LinearSolver::~LinearSolver() {
#ifdef TCAD_USE_PETSC
    petsc_free();
#endif
}

#ifdef TCAD_USE_PETSC
void LinearSolver::petsc_free() {
    if (petsc_ksp_) { KSPDestroy(&petsc_ksp_); petsc_ksp_ = nullptr; }
    if (petsc_A_)   { MatDestroy(&petsc_A_);   petsc_A_ = nullptr; }
    if (petsc_b_)   { VecDestroy(&petsc_b_);   petsc_b_ = nullptr; }
    if (petsc_x_)   { VecDestroy(&petsc_x_);   petsc_x_ = nullptr; }
    petsc_n_ = -1;
}
#endif

size_t LinearSolver::solve(const SparseMatrix& A, const Vector& b, Vector& x) {
    switch (opt_.type) {
        case SolverType::BICGSTAB:
        case SolverType::BICGSTAB_ILU0:
            return bicgstab(A, b, x);
        case SolverType::GMRES: return gmres(A, b, x);
        case SolverType::CG: return cg(A, b, x);
        case SolverType::JACOBI: return jacobi(A, b, x);
        case SolverType::GAUSS_SEIDEL: return gauss_seidel(A, b, x);
        case SolverType::DENSE_DIRECT:
            return dense_direct(A, b, x);
        case SolverType::IR_BICGSTAB:
            return solve_ir_bicgstab(A, b, x);
#ifdef TCAD_USE_PETSC
        case SolverType::PETSC:
            return solve_petsc(A, b, x);
#else
        case SolverType::PETSC:
            break;
#endif
    }
    // Unknown/unsupported solver type (e.g. SolverType::PETSC requested
    // without PETSc compiled in).  Previously this fell through to a silent
    // `return 0` WITHOUT SOLVING — the Newton step was identically zero,
    // producing the universal line-search stall on all >2000-node problems.
    throw std::runtime_error("LinearSolver: unsupported solver type " +
                             std::to_string(static_cast<int>(opt_.type)) +
                             " (PETSc not compiled?)");
}

size_t LinearSolver::bicgstab(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();
    Vector r = b - A.apply(x);
    Vector r0 = r;
    real_t rho = 1.0Q, alpha = 1.0Q, omega = 1.0Q;
    Vector p(n, 0.0Q), v(n, 0.0Q);

    DiagonalPreconditioner M_diag;
    ILU0Preconditioner M_ilu;
    bool use_ilu = (opt_.prec == PreconditionerType::ILU0);
    if (use_ilu) {
        try {
            M_ilu.setup(A);
        } catch (const std::exception& e) {
            if (opt_.verbose) std::cerr << "ILU0 setup failed, falling back to diagonal: " << e.what() << std::endl;
            use_ilu = false;
            M_diag.setup(A);
        }
    } else {
        M_diag.setup(A);
    }

    auto precondition = [&](const Vector& vec) -> Vector {
        if (use_ilu) return M_ilu.apply(vec);
        return M_diag.apply(vec);
    };

    real_t bnrm = norm_l2(b);
    if (bnrm < EPSILON) bnrm = 1.0Q;

    real_t initial_res = norm_l2(r) / bnrm;
    if (initial_res < opt_.tol) {
        if (opt_.verbose) std::cout << "BiCGSTAB converged immediately (res=" << (double)initial_res << ")" << std::endl;
        return 0;
    }

    for (size_t iter = 1; iter <= opt_.max_iter; ++iter) {
        real_t rho_new = dot(r0, r);
        if (abs_q(rho_new) < EPSILON) {
            if (opt_.verbose) std::cerr << "BiCGSTAB breakdown (rho) at iter " << iter << std::endl;
            r0 = r;
            rho = 1.0Q; alpha = 1.0Q; omega = 1.0Q;
            std::fill(p.begin(), p.end(), 0.0Q);
            std::fill(v.begin(), v.end(), 0.0Q);
            continue;
        }
        real_t beta = (rho_new / rho) * (alpha / omega);
        rho = rho_new;

        for (size_t i = 0; i < n; ++i) {
            p[i] = r[i] + beta * (p[i] - omega * v[i]);
        }
        Vector ph = precondition(p);
        v = A.apply(ph);
        real_t rv = dot(r0, v);
        if (abs_q(rv) < EPSILON) {
            if (opt_.verbose) std::cerr << "BiCGSTAB breakdown (rv) at iter " << iter << std::endl;
            for (size_t i = 0; i < n; ++i) x[i] += alpha * ph[i];
            r0 = r;
            rho = 1.0Q; alpha = 1.0Q; omega = 1.0Q;
            std::fill(p.begin(), p.end(), 0.0Q);
            std::fill(v.begin(), v.end(), 0.0Q);
            continue;
        }
        alpha = rho / rv;
        Vector s(n);
        for (size_t i = 0; i < n; ++i) s[i] = r[i] - alpha * v[i];

        real_t snrm = norm_l2(s);
        if (snrm / bnrm < opt_.tol) {
            for (size_t i = 0; i < n; ++i) x[i] += alpha * ph[i];
            if (opt_.verbose) std::cout << "BiCGSTAB converged at iter " << iter << " (s-step)" << std::endl;
            return iter;
        }

        Vector sh = precondition(s);
        Vector t = A.apply(sh);
        real_t t_dot_t = dot(t, t);
        real_t ts = dot(t, s);
        real_t t_scale = abs_q(t_dot_t);
        if (t_scale < EPSILON || abs_q(ts) > 1e10Q * t_scale) {
            if (opt_.verbose) std::cerr << "BiCGSTAB breakdown (t_dot_t) at iter " << iter << ", using safe fallback" << std::endl;
            for (size_t i = 0; i < n; ++i) {
                x[i] += alpha * ph[i];
                r[i] = s[i];
            }
            omega = 0.0Q;
        } else {
            omega = ts / t_dot_t;
            for (size_t i = 0; i < n; ++i) {
                x[i] += alpha * ph[i] + omega * sh[i];
                r[i] = s[i] - omega * t[i];
            }
        }

        real_t rnrm = norm_l2(r) / bnrm;
        if (rnrm < opt_.tol) {
            if (opt_.verbose) std::cout << "BiCGSTAB converged at iter " << iter << " (res=" << (double)rnrm << ")" << std::endl;
            return iter;
        }
    }
    if (opt_.verbose) std::cerr << "BiCGSTAB did not converge within max_iter, returning best guess" << std::endl;
    return opt_.max_iter;
}

// Iterative refinement: use existing float128 BICGSTAB with loose tolerance
// for the inner solve, then refine in float128. The loose tolerance makes
// the inner solve ~5× faster, and IR recovers full precision in 2-3 steps.
size_t LinearSolver::solve_ir_bicgstab(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();
    x.assign(n, 0.0Q);
    SolverOptions saved = opt_;

    // Initial solve: loose tolerance, limited iterations
    opt_.tol = 1e-3Q;
    opt_.max_iter = std::min((size_t)100, saved.max_iter);
    size_t inner_iters = bicgstab(A, b, x);

    // Iterative refinement: each step tightens by ~2 digits
    for (int ir = 0; ir < 8; ++ir) {
        Vector Ax = A.apply(x);
        Vector r(n);
        for (size_t i = 0; i < n; ++i) r[i] = b[i] - Ax[i];
        real_t rmax = 0;
        for (size_t i = 0; i < n; ++i) rmax = std::max(rmax, abs_q(r[i]));
        if (rmax < 1e-18Q) break;

        Vector dx(n, 0.0Q);
        opt_.tol = 1e-4Q;
        opt_.max_iter = 50;
        bicgstab(A, r, dx);
        for (size_t i = 0; i < n; ++i) x[i] += dx[i];
    }
    opt_ = saved;
    return inner_iters;
}

size_t LinearSolver::gmres(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();
    const size_t restart = opt_.restart > 0 ? opt_.restart : 30;

    DiagonalPreconditioner M_diag;
    ILU0Preconditioner M_ilu;
    bool use_ilu = (opt_.prec == PreconditionerType::ILU0);
    if (use_ilu) {
        try {
            M_ilu.setup(A);
        } catch (const std::exception& e) {
            if (opt_.verbose) std::cerr << "ILU0 setup failed, falling back to diagonal: " << e.what() << std::endl;
            use_ilu = false;
            M_diag.setup(A);
        }
    } else {
        M_diag.setup(A);
    }

    auto precondition = [&](const Vector& vec) -> Vector {
        if (use_ilu) return M_ilu.apply(vec);
        return M_diag.apply(vec);
    };

    real_t bnrm = norm_l2(b);
    if (bnrm < EPSILON) bnrm = 1.0Q;

    Vector r = b - A.apply(x);
    real_t initial_res = norm_l2(r) / bnrm;
    if (initial_res < opt_.tol) return 0;

    std::vector<Vector> V;
    V.reserve(restart + 1);
    std::vector<std::vector<real_t>> H;
    H.reserve(restart);
    size_t total_iter = 0;

    for (size_t outer = 0; outer <= opt_.max_iter / restart; ++outer) {
        r = b - A.apply(x);
        real_t beta = norm_l2(r);
        if (beta / bnrm < opt_.tol) return total_iter;

        V.clear();
        H.clear();

        V.emplace_back(n, 0.0Q);
        for (size_t i = 0; i < n; ++i) V[0][i] = r[i] / beta;

        std::vector<real_t> g(restart + 1, 0.0Q);
        g[0] = beta;
        std::vector<real_t> cs(restart, 0.0Q);
        std::vector<real_t> sn(restart, 0.0Q);

        for (size_t j = 0; j < restart; ++j) {
            Vector z = precondition(V[j]);
            Vector w = A.apply(z);

            std::vector<real_t> h(j + 2, 0.0Q);
            for (size_t i = 0; i <= j; ++i) {
                h[i] = dot(w, V[i]);
                for (size_t k = 0; k < n; ++k) w[k] -= h[i] * V[i][k];
            }
            h[j + 1] = norm_l2(w);
            H.push_back(h);

            if (abs_q(h[j + 1]) < EPSILON) {
                break;
            }

            V.emplace_back(n, 0.0Q);
            for (size_t k = 0; k < n; ++k) V[j + 1][k] = w[k] / h[j + 1];

            // Apply previous Givens rotations
            for (size_t i = 0; i < j; ++i) {
                real_t temp = cs[i] * H[j][i] + sn[i] * H[j][i + 1];
                H[j][i + 1] = -sn[i] * H[j][i] + cs[i] * H[j][i + 1];
                H[j][i] = temp;
            }

            // Compute new Givens rotation
            real_t a = H[j][j];
            real_t b_val = H[j][j + 1];
            if (abs_q(b_val) < EPSILON) {
                cs[j] = (a >= 0) ? 1.0Q : -1.0Q;
                sn[j] = 0.0Q;
            } else {
                real_t scale = abs_q(a) + abs_q(b_val);
                real_t norm = scale * sqrt_q((a / scale) * (a / scale) + (b_val / scale) * (b_val / scale));
                cs[j] = a / norm;
                sn[j] = b_val / norm;
            }

            // Apply to H and g
            real_t temp = cs[j] * g[j] + sn[j] * g[j + 1];
            g[j + 1] = -sn[j] * g[j] + cs[j] * g[j + 1];
            g[j] = temp;

            H[j][j] = cs[j] * H[j][j] + sn[j] * H[j][j + 1];
            H[j][j + 1] = 0.0Q;

            total_iter++;

            // Check convergence
            if (abs_q(g[j + 1]) / bnrm < opt_.tol) {
                // Solve upper triangular system
                Vector y(j + 1, 0.0Q);
                for (int ii = static_cast<int>(j); ii >= 0; --ii) {
                    size_t i = static_cast<size_t>(ii);
                    y[i] = g[i];
                    for (size_t k = i + 1; k <= j; ++k) {
                        y[i] -= H[k][i] * y[k];
                    }
                    if (abs_q(H[i][i]) < EPSILON) H[i][i] = EPSILON;
                    y[i] /= H[i][i];
                }

                for (size_t i = 0; i <= j; ++i) {
                    Vector zi = precondition(V[i]);
                    for (size_t k = 0; k < n; ++k) x[k] += y[i] * zi[k];
                }
                if (opt_.verbose) std::cout << "GMRES converged at iter " << total_iter << std::endl;
                return total_iter;
            }
        }

        // Solve for y before restart
        size_t j = H.size() - 1;
        if (!H.empty()) {
            Vector y(j + 1, 0.0Q);
            for (int ii = static_cast<int>(j); ii >= 0; --ii) {
                size_t i = static_cast<size_t>(ii);
                y[i] = g[i];
                for (size_t k = i + 1; k <= j; ++k) {
                    y[i] -= H[k][i] * y[k];
                }
                if (abs_q(H[i][i]) < EPSILON) H[i][i] = EPSILON;
                y[i] /= H[i][i];
            }

            for (size_t i = 0; i <= j; ++i) {
                Vector zi = precondition(V[i]);
                for (size_t k = 0; k < n; ++k) x[k] += y[i] * zi[k];
            }
        }
    }

    if (opt_.verbose) std::cerr << "GMRES did not converge within max_iter, returning best guess" << std::endl;
    return total_iter;
}

size_t LinearSolver::cg(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();

    DiagonalPreconditioner M_diag;
    IC0Preconditioner M_ic;
    bool use_ic = (opt_.prec == PreconditionerType::IC0);
    if (use_ic) {
        try {
            M_ic.setup(A);
        } catch (const std::exception& e) {
            if (opt_.verbose) std::cerr << "IC0 setup failed, falling back to diagonal: " << e.what() << std::endl;
            use_ic = false;
            M_diag.setup(A);
        }
    } else {
        M_diag.setup(A);
    }

    auto precondition = [&](const Vector& vec) -> Vector {
        if (use_ic) return M_ic.apply(vec);
        return M_diag.apply(vec);
    };

    real_t bnrm = norm_l2(b);
    if (bnrm < EPSILON) bnrm = 1.0Q;

    Vector r = b - A.apply(x);
    real_t initial_res = norm_l2(r) / bnrm;
    if (initial_res < opt_.tol) return 0;

    Vector z = precondition(r);
    Vector p = z;
    real_t rz_old = dot(r, z);

    for (size_t iter = 1; iter <= opt_.max_iter; ++iter) {
        Vector Ap = A.apply(p);
        real_t pAp = dot(p, Ap);
        if (abs_q(pAp) < EPSILON) {
            if (opt_.verbose) std::cerr << "CG breakdown (pAp) at iter " << iter << std::endl;
            return iter;
        }

        real_t alpha = rz_old / pAp;
        for (size_t i = 0; i < n; ++i) x[i] += alpha * p[i];
        for (size_t i = 0; i < n; ++i) r[i] -= alpha * Ap[i];

        real_t rnrm = norm_l2(r) / bnrm;
        if (rnrm < opt_.tol) {
            if (opt_.verbose) std::cout << "CG converged at iter " << iter << " (res=" << (double)rnrm << ")" << std::endl;
            return iter;
        }

        z = precondition(r);
        real_t rz_new = dot(r, z);
        real_t beta = rz_new / rz_old;
        for (size_t i = 0; i < n; ++i) p[i] = z[i] + beta * p[i];
        rz_old = rz_new;
    }

    if (opt_.verbose) std::cerr << "CG did not converge within max_iter, returning best guess" << std::endl;
    return opt_.max_iter;
}

size_t LinearSolver::jacobi(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();
    DiagonalPreconditioner M;
    M.setup(A);
    real_t bnrm = norm_l2(b);
    if (bnrm < EPSILON) bnrm = 1.0Q;
    for (size_t iter = 1; iter <= opt_.max_iter; ++iter) {
        Vector r = b - A.apply(x);
        Vector dx = M.apply(r);
        for (size_t i = 0; i < n; ++i) x[i] += dx[i];
        if (norm_l2(r) / bnrm < opt_.tol) return iter;
    }
    if (opt_.verbose) std::cerr << "Jacobi did not converge within max_iter, returning best guess" << std::endl;
    return opt_.max_iter;
}

size_t LinearSolver::gauss_seidel(const SparseMatrix& A, const Vector& b, Vector& x) {
    return jacobi(A, b, x);
}

// Diagonal preconditioner
void DiagonalPreconditioner::setup(const SparseMatrix& A) {
    const size_t n = A.rows();
    inv_diag_.assign(n, 0.0Q);
    const auto& vals = A.vals();
    const auto& cols = A.col_indices();
    const auto& rp = A.row_offsets();
    for (size_t i = 0; i < n; ++i) {
        for (size_t idx = rp[i]; idx < rp[i + 1]; ++idx) {
            if (cols[idx] == i) {
                if (abs_q(vals[idx]) > EPSILON)
                    inv_diag_[i] = 1.0Q / vals[idx];
                break;
            }
        }
    }
}

Vector DiagonalPreconditioner::apply(const Vector& r) const {
    Vector y(r.size());
    for (size_t i = 0; i < r.size(); ++i) y[i] = inv_diag_[i] * r[i];
    return y;
}

size_t LinearSolver::dense_direct(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = A.rows();
    const auto& vals = A.vals();
    const auto& cols = A.col_indices();
    const auto& rp = A.row_offsets();

    // Portable narrow-band direct solve.  Structured 1-D/2-D device matrices
    // just above the old 2,000-node cutoff have a small geometric bandwidth
    // (the 3 nm MOS calibration is n=2,009, bw=41).  Sending these systems to
    // an iterative fallback is both slower and less reliable, while expanding
    // them to n*n defeats the point of a portable build.  A diagonally
    // dominant Poisson/SG matrix needs no pivot interchange, so banded
    // Gaussian elimination is O(n*bw^2) and stores O(n*bw).
    size_t lower_bw = 0, upper_bw = 0;
    for (size_t i = 0; i < n; ++i) {
        for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry) {
            const size_t j = cols[entry];
            if (j < i) lower_bw = std::max(lower_bw, i - j);
            else upper_bw = std::max(upper_bw, j - i);
        }
    }
    const size_t band_width = lower_bw + upper_bw + 1;
    auto candidate_backward_residual = [&](const Vector& candidate) {
        if (candidate.size() != n) return 1.0e100Q;
        const Vector applied = A.apply(candidate);
        real_t worst = 0.0Q;
        for (size_t i = 0; i < n; ++i) {
            real_t scale = abs_q(b[i]);
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                scale += abs_q(vals[entry] * candidate[cols[entry]]);
            const real_t relative =
                abs_q(applied[i] - b[i]) / std::max(scale, 1.0Q);
            if (!std::isfinite((double)relative)) return 1.0e100Q;
            worst = std::max(worst, relative);
        }
        return worst;
    };
    [[maybe_unused]] auto candidate_is_acceptable = [&](const Vector& candidate) {
        return candidate_backward_residual(candidate) <= 1.0e-8Q;
    };
    if (n > 32 && band_width <= 257 && 4 * band_width < n) {
#ifdef TCAD_USE_LAPACK
        // Try the optimized double-precision band factorization first.  Row
        // equilibration is formed in float128 and the candidate is judged on
        // the original float128 equations, so this fast path cannot weaken
        // the continuity residual gate.  The portable float128 band solver
        // below remains the accuracy fallback.
        const int ni = static_cast<int>(n);
        const int nrhsi = 1;
        const int kli = static_cast<int>(lower_bw);
        const int kui = static_cast<int>(upper_bw);
        const int ldab = 2 * kli + kui + 1;
        std::vector<real_t> row_scale(n, 1.0Q);
        bool valid_rows = true;
        for (size_t i = 0; i < n; ++i) {
            real_t scale = 0.0Q;
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                scale = std::max(scale, abs_q(vals[entry]));
            if (!(scale > 0.0Q)) {
                valid_rows = false;
                break;
            }
            row_scale[i] = scale;
        }
        if (valid_rows) {
            const double shifts[] = {
                0.0, 64.0 * std::numeric_limits<double>::epsilon(),
                1.0e-12, 1.0e-10, 1.0e-8};
            for (const double shift : shifts) {
                std::vector<double> AB(
                    static_cast<size_t>(ldab) * n, 0.0);
                std::vector<double> B(n);
                for (size_t i = 0; i < n; ++i) {
                    B[i] = static_cast<double>(b[i] / row_scale[i]);
                    for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry) {
                        const size_t j = cols[entry];
                        const int row = static_cast<int>(
                            lower_bw + upper_bw + i - j);
                        AB[j * static_cast<size_t>(ldab) + row] =
                            static_cast<double>(vals[entry] / row_scale[i]);
                    }
                    AB[i * static_cast<size_t>(ldab) + lower_bw + upper_bw]
                        += shift;
                }
                std::vector<int> ipiv(n);
                int info = 0;
                dgbtrf_(&ni, &ni, &kli, &kui, AB.data(), &ldab,
                        ipiv.data(), &info);
                if (info == 0) {
                    const char trans = 'N';
                    dgbtrs_(&trans, &ni, &kli, &kui, &nrhsi, AB.data(),
                            &ldab, ipiv.data(), B.data(), &ni, &info);
                }
                if (info != 0) continue;
                Vector candidate(n);
                for (size_t i = 0; i < n; ++i)
                    candidate[i] = static_cast<real_t>(B[i]);
                if (candidate_is_acceptable(candidate)) {
                    x = std::move(candidate);
                    return 1;
                }
                // A successful factorization with a poor original-system
                // residual will not be improved by a larger diagonal shift.
                break;
            }
        }
#endif
        std::vector<real_t> band(n * band_width, 0.0Q);
        Vector rhs = b;
        auto at = [&](size_t row, size_t col) -> real_t& {
            return band[row * band_width + col + lower_bw - row];
        };
        for (size_t i = 0; i < n; ++i) {
            real_t row_scale = 0.0Q;
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                row_scale = std::max(row_scale, abs_q(vals[entry]));
            if (!(row_scale > EPSILON) ||
                !std::isfinite((double)row_scale))
                throw std::runtime_error("banded direct solver: invalid row");
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                at(i, cols[entry]) = vals[entry] / row_scale;
            rhs[i] /= row_scale;
        }
        for (size_t k = 0; k < n; ++k) {
            const real_t pivot = at(k, k);
            if (abs_q(pivot) < 1.0e-28Q ||
                !std::isfinite((double)pivot))
                throw std::runtime_error(
                    "banded direct solver: zero/non-finite pivot at row " +
                    std::to_string(k));
            const size_t i_end = std::min(n - 1, k + lower_bw);
            const size_t j_end = std::min(n - 1, k + upper_bw);
            for (size_t i = k + 1; i <= i_end; ++i) {
                const real_t factor = at(i, k) / pivot;
                at(i, k) = 0.0Q;
                for (size_t j = k + 1; j <= j_end; ++j)
                    at(i, j) -= factor * at(k, j);
                rhs[i] -= factor * rhs[k];
            }
        }
        x.assign(n, 0.0Q);
        for (size_t reverse = n; reverse-- > 0;) {
            real_t value = rhs[reverse];
            const size_t j_end = std::min(n - 1, reverse + upper_bw);
            for (size_t j = reverse + 1; j <= j_end; ++j)
                value -= at(reverse, j) * x[j];
            const real_t pivot = at(reverse, reverse);
            if (abs_q(pivot) < 1.0e-28Q ||
                !std::isfinite((double)pivot))
                throw std::runtime_error(
                    "banded direct solver: singular back substitution");
            x[reverse] = value / pivot;
        }
        return 1;
    }

    // Convert sparse to dense (flattened row-major)
    std::vector<real_t> M(n * n, 0.0Q);
    for (size_t i = 0; i < n; ++i) {
        for (size_t idx = rp[i]; idx < rp[i + 1]; ++idx) {
            M[i * n + cols[idx]] = vals[idx];
        }
    }

    Vector rhs = b;

    // Check if matrix is tridiagonal (including Dirichlet rows at boundaries)
    bool is_tridiag = true;
    for (size_t i = 0; i < n && is_tridiag; ++i) {
        size_t row_nnz = 0;
        for (size_t j = 0; j < n; ++j) {
            if (abs_q(M[i * n + j]) > EPSILON) row_nnz++;
        }
        if (i == 0 || i == n - 1) {
            if (row_nnz > 2) is_tridiag = false;
        } else {
            if (row_nnz > 3) is_tridiag = false;
        }
    }

    // Tridiagonal system with Dirichlet rows at both boundaries: solve interior
    // using Thomas algorithm and set boundary values directly.
    if (is_tridiag && n > 2) {
        bool dirichlet_0 = (abs_q(M[0]) > EPSILON);
        for (size_t j = 1; j < n; ++j) {
            if (abs_q(M[j]) > EPSILON) { dirichlet_0 = false; break; }
        }
        bool dirichlet_n1 = (abs_q(M[(n-1)*n + (n-1)]) > EPSILON);
        for (size_t j = 0; j < n-1; ++j) {
            if (abs_q(M[(n-1)*n + j]) > EPSILON) { dirichlet_n1 = false; break; }
        }
        if (dirichlet_0 && dirichlet_n1) {
            size_t m = n - 2;
            if (m == 0) {
                x[0] = rhs[0];
                x[n-1] = rhs[n-1];
                return 1;
            }
            std::vector<real_t> a(m, 0.0Q), d(m, 0.0Q), c_t(m, 0.0Q), b(m, 0.0Q);
            for (size_t i = 0; i < m; ++i) {
                size_t row = i + 1;
                d[i] = M[row * n + row];
                if (i > 0) a[i] = M[row * n + (row - 1)];
                if (i + 1 < m) c_t[i] = M[row * n + (row + 1)];
                b[i] = rhs[row];
            }
            // Subtract Dirichlet contributions from RHS
            b[0] -= M[1 * n + 0] * rhs[0];
            b[m-1] -= M[(n-2) * n + (n-1)] * rhs[n-1];
            // Thomas forward elimination
            for (size_t i = 1; i < m; ++i) {
                real_t w = a[i] / d[i - 1];
                d[i] -= w * c_t[i - 1];
                b[i] -= w * b[i - 1];
            }
            // Back substitution
            x[n-1] = rhs[n-1];
            x[0] = rhs[0];
            std::vector<real_t> xi(m);
            xi[m-1] = b[m-1] / d[m-1];
            for (int ii = static_cast<int>(m) - 2; ii >= 0; --ii) {
                size_t i = static_cast<size_t>(ii);
                xi[i] = (b[i] - c_t[i] * xi[i + 1]) / d[i];
            }
            for (size_t i = 0; i < m; ++i) x[i + 1] = xi[i];
            return 1;
        }
    }
    // LAPACK direct solve in double precision.  The linear solve inside
    // Newton/Gummel is done in double (the nonlinear outer iteration restores
    // full accuracy), via optimized BLAS/LAPACK -- ~100x faster than manual
    // __float128 Gaussian elimination.  Detect the bandwidth from the CSR
    // structure: genuinely banded systems (coupled DD Jacobian on a structured
    // grid, bw ~ 2*neq+1 ~ 9) use dgbtrf/dgbtrs O(n*bw^2); otherwise dgesv
    // O(n^3) in double.  Makes the 200-2000-node "dead zone" fast.
#ifdef TCAD_USE_LAPACK
    {
        const auto& cols_csr = A.col_indices();
        const auto& rp_csr = A.row_offsets();
        size_t kl = 0, ku = 0;
        for (size_t i = 0; i < n; ++i) {
            for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx) {
                size_t j = cols_csr[idx];
                if (j < i) kl = std::max(kl, i - j);
                else if (j > i) ku = std::max(ku, j - i);
            }
        }
        const int ni = static_cast<int>(n);
        const int nrhsi = 1;
        int info = 0;
        bool validate_lapack_candidate = false;
        std::vector<double> B(n);
        const size_t bw = kl + ku + 1;
        if (getenv("TCAD_LIN_DEBUG")) { static long long c=0; if(++c<=8) std::cerr << "[LAPACK n=" << n << " bw=" << bw << " banded=" << (n>32 && 4*bw<n) << "]\n"; }
        if (n > 32 && 4 * bw < n) {
            for (size_t i = 0; i < n; ++i)
                B[i] = static_cast<double>(rhs[i]);
            // Banded: LAPACK column-major band storage AB[(2*kl+ku+1) x n].
            const int kli = static_cast<int>(kl);
            const int kui = static_cast<int>(ku);
            const int ldab = 2 * kli + kui + 1;
            std::vector<double> AB(static_cast<size_t>(ldab) * n, 0.0);
            for (size_t i = 0; i < n; ++i) {
                for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx) {
                    size_t j = cols_csr[idx];
                    int row = static_cast<int>(kl + ku + i - j);  // AB row (LAPACK band layout)
                    AB[static_cast<size_t>(j) * ldab + row] = static_cast<double>(vals[idx]);  // column-major
                }
            }
            std::vector<int> ipiv(n);
            dgbtrf_(&ni, &ni, &kli, &kui, AB.data(), &ldab, ipiv.data(), &info);
            if (info == 0) {
                const char trans = 'N';
                dgbtrs_(&trans, &ni, &kli, &kui, &nrhsi, AB.data(), &ldab,
                        ipiv.data(), B.data(), &ni, &info);
            }
        } else {
            validate_lapack_candidate = true;
            // General dense: equilibrate each row in float128 before casting
            // to double.  Minority-carrier equations in depleted 3-D devices
            // can be many orders smaller than contact rows; casting the raw
            // matrix can make an otherwise solvable row numerically singular
            // and trigger the O(n^3) float128 fallback below.
            std::vector<real_t> row_scale(n, 1.0Q);
            for (size_t i = 0; i < n; ++i) {
                real_t scale = 0.0Q;
                for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx)
                    scale = std::max(scale, abs_q(vals[idx]));
                if (scale > 0.0Q) row_scale[i] = scale;
            }
            auto factor_scaled = [&](double diagonal_shift) {
                std::vector<double> AD(n * n, 0.0);
                for (size_t i = 0; i < n; ++i) {
                    B[i] = static_cast<double>(rhs[i] / row_scale[i]);
                    for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx)
                        AD[cols_csr[idx] * n + i] =
                            static_cast<double>(vals[idx] / row_scale[i]);
                    AD[i * n + i] += diagonal_shift;
                }
                std::vector<int> ipiv(n);
                info = 0;
                dgesv_(&ni, &nrhsi, AD.data(), &ni, ipiv.data(),
                       B.data(), &ni, &info);
            };
            factor_scaled(0.0);
            if (info > 0) {
                // A rank-deficient quiet-carrier block can retain an exact
                // zero pivot after equilibration.  Retry a bounded sequence
                // of roundoff-scale shifts: a severely depleted 3-D block can
                // need more than machine epsilon before double-precision
                // pivoting sees full numerical rank.  Every successful
                // candidate is still checked against the original float128
                // equations below, so a larger shift cannot silently relax
                // the physical residual gate.
                const double shifts[] = {
                    64.0 * std::numeric_limits<double>::epsilon(),
                    1.0e-12, 1.0e-10, 1.0e-8};
                for (const double shift : shifts) {
                    factor_scaled(shift);
                    if (info == 0) break;
                }
            }
        }
        if (info == 0) {
            Vector candidate(n);
            for (size_t i = 0; i < n; ++i)
                candidate[i] = static_cast<real_t>(B[i]);
            bool candidate_acceptable = true;
            if (validate_lapack_candidate) {
                // An equilibrated (and possibly shifted) solve is accepted
                // only when it still solves the unmodified float128 equations.
                // Small generic meshes can contain a genuine null block; for
                // those, keep the original quad fallback instead of returning
                // a row-scaled or regularized state with a poor backward error.
                candidate_acceptable = candidate_is_acceptable(candidate);
                if (!candidate_acceptable && getenv("TCAD_LIN_DEBUG"))
                    std::cerr << "[LAPACK equilibrated residual rejected] "
                              << "-> quad fallback\n";
            }
            if (candidate_acceptable) {
                x = std::move(candidate);
                return 1;
            }
            info = 1;
        }
        if (getenv("TCAD_LIN_DEBUG"))
            std::cerr << "[LAPACK info=" << info << " n=" << n << "] -> quad fallback\n";
    }
#endif

    // Gaussian elimination with partial pivoting (__float128 fallback)
    for (size_t k = 0; k < n; ++k) {
        size_t max_row = k;
        real_t max_val = abs_q(M[k * n + k]);
        for (size_t i = k + 1; i < n; ++i) {
            if (abs_q(M[i * n + k]) > max_val) {
                max_val = abs_q(M[i * n + k]);
                max_row = i;
            }
        }
        if (max_val < EPSILON) {
            M[k * n + k] = EPSILON;
            max_val = EPSILON;
        }
        if (max_row != k) {
            for (size_t j = 0; j < n; ++j) {
                real_t tmp = M[k * n + j];
                M[k * n + j] = M[max_row * n + j];
                M[max_row * n + j] = tmp;
            }
            real_t tmp_rhs = rhs[k];
            rhs[k] = rhs[max_row];
            rhs[max_row] = tmp_rhs;
        }

        for (size_t i = k + 1; i < n; ++i) {
            real_t factor = M[i * n + k] / M[k * n + k];
            for (size_t j = k; j < n; ++j) {
                M[i * n + j] -= factor * M[k * n + j];
            }
            rhs[i] -= factor * rhs[k];
        }
    }

    for (int ii = static_cast<int>(n) - 1; ii >= 0; --ii) {
        size_t i = static_cast<size_t>(ii);
        x[i] = rhs[i];
        for (size_t j = i + 1; j < n; ++j) {
            x[i] -= M[i * n + j] * x[j];
        }
        x[i] /= M[i * n + i];
    }
    return 1;
}

#ifdef TCAD_USE_PETSC
size_t LinearSolver::solve_petsc(const SparseMatrix& A, const Vector& b, Vector& x) {
    // Ensure PETSc is initialized (idempotent)
    PetscBool petsc_initialized;
    PetscInitialized(&petsc_initialized);
    if (!petsc_initialized) {
        PetscInitialize(nullptr, nullptr, nullptr, nullptr);
    }

    const size_t n = b.size();
    const PetscInt N = static_cast<PetscInt>(n);
    const auto& row_ptr = A.row_offsets();
    const auto& col_idx = A.col_indices();
    const auto& values = A.vals();

    // ---- Reuse cache: keep Mat/KSP/Vecs across calls when the problem size
    // is unchanged.  On a fixed mesh the sparsity pattern is constant, so we
    // lock MAT_NEW_NONZERO_LOCATIONS=FALSE after the first assembly and
    // SuperLU reuses the SYMBOLIC factorization (only numeric refactor each
    // call).  This removes the per-call MatCreate/KSPCreate/symbolic-analysis
    // overhead (~the dominant cost for the 10k-node nMOS Gummel loop).
    bool reuse = (petsc_n_ == N && petsc_A_ != nullptr && petsc_ksp_ != nullptr);
    if (getenv("TCAD_PETSC_DEBUG")) { static long long cc=0; ++cc; if(cc<=8) std::cerr << "[petsc n=" << N << " reuse=" << reuse << "]\n"; }
    auto fill_matrix = [&]() {
        for (size_t i = 0; i < n; ++i) {
            PetscInt row = static_cast<PetscInt>(i);
            PetscInt ncols = static_cast<PetscInt>(row_ptr[i + 1] - row_ptr[i]);
            if (ncols == 0) continue;
            std::vector<PetscInt> cols;
            std::vector<PetscScalar> vals;
            cols.reserve(ncols); vals.reserve(ncols);
            for (size_t j = row_ptr[i]; j < row_ptr[i + 1]; ++j) {
                cols.push_back(static_cast<PetscInt>(col_idx[j]));
                vals.push_back(static_cast<PetscScalar>(values[j]));
            }
            MatSetValues(petsc_A_, 1, &row, ncols, cols.data(), vals.data(), INSERT_VALUES);
        }
        MatAssemblyBegin(petsc_A_, MAT_FINAL_ASSEMBLY);
        MatAssemblyEnd(petsc_A_, MAT_FINAL_ASSEMBLY);
    };

    if (!reuse) {
        petsc_free();
        const PetscInt nz_row = (PetscInt)std::min<size_t>(30, n);
        MatCreateSeqAIJ(PETSC_COMM_SELF, N, N, nz_row, nullptr, &petsc_A_);
        fill_matrix();
        // Lock the nonzero pattern so SuperLU reuses the symbolic factorization
        // on subsequent calls (only the numeric factorization is redone).
        MatSetOption(petsc_A_, MAT_NEW_NONZERO_LOCATIONS, PETSC_FALSE);
        VecCreateSeq(PETSC_COMM_SELF, N, &petsc_b_);
        VecCreateSeq(PETSC_COMM_SELF, N, &petsc_x_);
        KSPCreate(PETSC_COMM_SELF, &petsc_ksp_);
        KSPSetOperators(petsc_ksp_, petsc_A_, petsc_A_);
        KSPSetTolerances(petsc_ksp_, static_cast<PetscReal>(opt_.tol), PETSC_DEFAULT,
                         PETSC_DEFAULT, static_cast<PetscInt>(opt_.max_iter));
        PC pc;
        KSPGetPC(petsc_ksp_, &pc);
        if (n < 80000) {
            KSPSetType(petsc_ksp_, KSPPREONLY);
            PCSetType(pc, PCLU);
            PCFactorSetMatSolverType(pc, MATSOLVERSUPERLU);
        } else {
            KSPSetType(petsc_ksp_, KSPBCGS);
            PCSetType(pc, PCGAMG);
        }
        KSPSetFromOptions(petsc_ksp_);
        petsc_n_ = N;
    } else {
        // Same size/pattern: update values in place and reuse the cached KSP
        // (SuperLU numeric refactor only; symbolic reused).
        MatSetOption(petsc_A_, MAT_NEW_NONZERO_LOCATIONS, PETSC_FALSE);
        fill_matrix();
    }

    // RHS
    PetscScalar* b_arr;
    VecGetArray(petsc_b_, &b_arr);
    for (size_t i = 0; i < n; ++i) b_arr[i] = static_cast<PetscScalar>(b[i]);
    VecRestoreArray(petsc_b_, &b_arr);
    // Initial guess
    PetscScalar* x_arr;
    VecGetArray(petsc_x_, &x_arr);
    for (size_t i = 0; i < n; ++i) x_arr[i] = static_cast<PetscScalar>(x[i]);
    VecRestoreArray(petsc_x_, &x_arr);

    KSPSolve(petsc_ksp_, petsc_b_, petsc_x_);

    KSPConvergedReason reason;
    KSPGetConvergedReason(petsc_ksp_, &reason);
    if (reason < 0) {
        std::cerr << "PETSc KSP failed (reason " << static_cast<int>(reason)
                  << "): " << KSPConvergedReasons[reason] << std::endl;
        throw std::runtime_error("PETSc linear solve failed");
    }

    PetscInt its;
    KSPGetIterationNumber(petsc_ksp_, &its);

    VecGetArray(petsc_x_, &x_arr);
    for (size_t i = 0; i < n; ++i) x[i] = static_cast<real_t>(x_arr[i]);
    VecRestoreArray(petsc_x_, &x_arr);

    // NOTE: no KSPDestroy/MatDestroy here — objects are cached for reuse.
    return static_cast<size_t>(its);
}
#endif

} // namespace tcad
