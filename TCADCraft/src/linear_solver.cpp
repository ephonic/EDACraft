#include "linear_solver.h"
#include <iostream>
#include <algorithm>
#include <limits>
#include <vector>
#include <cstdint>

// Optional direct LAPACK/BLAS linkage (TCAD_USE_LAPACK=1 at build time).  It is
// disabled in portable wheels because an extension linked against a system
// LAPACK can collide with the private BLAS/LAPACK bundled in SciPy wheels.
#ifdef TCAD_USE_LAPACK
// Match the linked library's Fortran INTEGER ABI explicitly. LP64 is the
// default; ILP64 libraries require TCAD_LAPACK_ILP64 for dimensions AND pivots.
#ifdef TCAD_LAPACK_ILP64
using lapack_int = std::int64_t;
#else
using lapack_int = int;
#endif
extern "C" {
void dgesv_(const lapack_int* n, const lapack_int* nrhs, double* A, const lapack_int* lda,
            lapack_int* ipiv, double* B, const lapack_int* ldb, lapack_int* info);
void dgbtrf_(const lapack_int* m, const lapack_int* n, const lapack_int* kl, const lapack_int* ku,
             double* AB, const lapack_int* ldab, lapack_int* ipiv, lapack_int* info);
void dgbtrs_(const char* trans, const lapack_int* n, const lapack_int* kl, const lapack_int* ku,
             const lapack_int* nrhs, const double* AB, const lapack_int* ldab,
            const lapack_int* ipiv, double* B, const lapack_int* ldb, lapack_int* info);
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

void LinearSolver::validate_solver_type(int type) {
    if (type < static_cast<int>(SolverType::BICGSTAB) ||
        type > static_cast<int>(SolverType::PETSC))
        throw std::invalid_argument("invalid linear solver type");
#ifndef TCAD_USE_PETSC
    if (type == static_cast<int>(SolverType::PETSC))
        throw std::runtime_error("PETSc backend unavailable in this build (not compiled)");
#endif
}

SolverOptions LinearSolver::default_poisson_options() {
    SolverOptions opt;
    opt.type = SolverType::DENSE_DIRECT;
    opt.max_iter = 5000;
#ifdef TCAD_USE_FLOAT128
    opt.tol = TCAD_CONST(1e-28);
#else
    opt.tol = TCAD_CONST(1e-12); // Double precision: match data precision
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
    opt.tol = TCAD_CONST(1e-28);
#else
    opt.tol = TCAD_CONST(1e-8);
#endif
    opt.prec = PreconditionerType::ILU0;
    opt.verbose = false;
    return opt;
}

LinearSolver::LinearSolver(const SolverOptions& opt) : opt_(opt) {}

LinearSolver& LinearSolver::operator=(const LinearSolver& other) {
    if (this != &other) {
#ifdef TCAD_USE_PETSC
        petsc_free();
#endif
        opt_ = other.opt_;
    }
    return *this;
}

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
    petsc_row_offsets_.clear();
    petsc_col_indices_.clear();
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
    real_t rho = TCAD_CONST(1.0), alpha = TCAD_CONST(1.0), omega = TCAD_CONST(1.0);
    Vector p(n, TCAD_CONST(0.0)), v(n, TCAD_CONST(0.0));

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
    if (bnrm < EPSILON) bnrm = TCAD_CONST(1.0);

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
            rho = TCAD_CONST(1.0); alpha = TCAD_CONST(1.0); omega = TCAD_CONST(1.0);
            std::fill(p.begin(), p.end(), TCAD_CONST(0.0));
            std::fill(v.begin(), v.end(), TCAD_CONST(0.0));
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
            rho = TCAD_CONST(1.0); alpha = TCAD_CONST(1.0); omega = TCAD_CONST(1.0);
            std::fill(p.begin(), p.end(), TCAD_CONST(0.0));
            std::fill(v.begin(), v.end(), TCAD_CONST(0.0));
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
        if (t_scale < EPSILON || abs_q(ts) > TCAD_CONST(1e10) * t_scale) {
            if (opt_.verbose) std::cerr << "BiCGSTAB breakdown (t_dot_t) at iter " << iter << ", using safe fallback" << std::endl;
            for (size_t i = 0; i < n; ++i) {
                x[i] += alpha * ph[i];
                r[i] = s[i];
            }
            omega = TCAD_CONST(0.0);
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
    x.assign(n, TCAD_CONST(0.0));
    SolverOptions saved = opt_;

    // Initial solve: loose tolerance, limited iterations
    opt_.tol = TCAD_CONST(1e-3);
    opt_.max_iter = std::min((size_t)100, saved.max_iter);
    size_t inner_iters = bicgstab(A, b, x);

    // Iterative refinement: each step tightens by ~2 digits
    for (int ir = 0; ir < 8; ++ir) {
        Vector Ax = A.apply(x);
        Vector r(n);
        for (size_t i = 0; i < n; ++i) r[i] = b[i] - Ax[i];
        real_t rmax = 0;
        for (size_t i = 0; i < n; ++i) rmax = std::max(rmax, abs_q(r[i]));
        if (rmax < TCAD_CONST(1e-18)) break;

        Vector dx(n, TCAD_CONST(0.0));
        opt_.tol = TCAD_CONST(1e-4);
        opt_.max_iter = 50;
        bicgstab(A, r, dx);
        for (size_t i = 0; i < n; ++i) x[i] += dx[i];
    }
    opt_ = saved;
    return inner_iters;
}

size_t LinearSolver::gmres(const SparseMatrix& A, const Vector& b, Vector& x) {
    const size_t n = b.size();
    // Scaling the RHS (or a homogeneous initial error) must not change the
    // relative stopping criterion. Squaring unscaled quad values can overflow
    // or underflow even when their L2 norm is representable.
    const auto scaled_norm = [](const Vector& v) -> real_t {
        real_t scale = TCAD_CONST(0.0);
        for (real_t value : v) {
            if (!isfinite_q(value)) return abs_q(value);
            scale = std::max(scale, abs_q(value));
        }
        if (scale == TCAD_CONST(0.0)) return scale;
        real_t sum = TCAD_CONST(0.0);
        for (real_t value : v) {
            const real_t normalized = value / scale;
            sum += normalized * normalized;
        }
        return scale * sqrt_q(sum);
    };
    const size_t restart = opt_.restart > 0 ? opt_.restart : 30;
    // A zero Arnoldi budget must leave even a non-solution initial guess alone.
    if (opt_.max_iter == 0) return 0;

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

    Vector r = b - A.apply(x);
    real_t bnrm = scaled_norm(b);
    // A nonzero RHS always supplies its own scale, however small. For b=0,
    // use the fixed initial residual scale instead of an absolute unit floor.
    if (bnrm == TCAD_CONST(0.0)) bnrm = scaled_norm(r);
    if (bnrm == TCAD_CONST(0.0)) return 0;
    real_t initial_res = scaled_norm(r) / bnrm;
    if (initial_res < opt_.tol) return 0;

    std::vector<Vector> V;
    V.reserve(restart + 1);
    std::vector<std::vector<real_t>> H;
    H.reserve(restart);
    size_t total_iter = 0;

    while (total_iter < opt_.max_iter) {
        r = b - A.apply(x);
        real_t beta = scaled_norm(r);
        if (beta / bnrm < opt_.tol) return total_iter;

        V.clear();
        H.clear();

        V.emplace_back(n, TCAD_CONST(0.0));
        for (size_t i = 0; i < n; ++i) V[0][i] = r[i] / beta;

        std::vector<real_t> g(restart + 1, TCAD_CONST(0.0));
        g[0] = beta;
        std::vector<real_t> cs(restart, TCAD_CONST(0.0));
        std::vector<real_t> sn(restart, TCAD_CONST(0.0));

        const size_t cycle_budget = std::min(restart, opt_.max_iter - total_iter);
        bool breakdown = false;
        for (size_t j = 0; j < cycle_budget; ++j) {
            Vector z = precondition(V[j]);
            Vector w = A.apply(z);
            const real_t arnoldi_scale = scaled_norm(w);

            std::vector<real_t> h(j + 2, TCAD_CONST(0.0));
            for (size_t i = 0; i <= j; ++i) {
                h[i] = dot(w, V[i]);
                for (size_t k = 0; k < n; ++k) w[k] -= h[i] * V[i][k];
            }
            h[j + 1] = scaled_norm(w);
            H.push_back(h);

            breakdown = h[j + 1] <= EPSILON * arnoldi_scale;
            if (!breakdown) {
                V.emplace_back(n, TCAD_CONST(0.0));
                for (size_t k = 0; k < n; ++k) V[j + 1][k] = w[k] / h[j + 1];
            }

            // Apply previous Givens rotations
            for (size_t i = 0; i < j; ++i) {
                real_t temp = cs[i] * H[j][i] + sn[i] * H[j][i + 1];
                H[j][i + 1] = -sn[i] * H[j][i] + cs[i] * H[j][i + 1];
                H[j][i] = temp;
            }

            // Compute new Givens rotation
            real_t a = H[j][j];
            real_t b_val = H[j][j + 1];
            if (b_val == TCAD_CONST(0.0)) {
                cs[j] = (a >= 0) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
                sn[j] = TCAD_CONST(0.0);
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
            H[j][j + 1] = TCAD_CONST(0.0);

            total_iter++;

            // A happy breakdown still needs this column's rotations and
            // least-squares update. The original equation decides convergence.
            if (breakdown || abs_q(g[j + 1]) / bnrm < opt_.tol) break;
        }

        // A zero trailing pivot is an inconsistent/rank-deficient breakdown,
        // not permission to invent an EPSILON diagonal. Retain the correction
        // from the nonsingular leading columns and report its actual residual.
        size_t columns = H.size();
        while (columns && H[columns - 1][columns - 1] == TCAD_CONST(0.0)) --columns;
        if (columns) {
            Vector y(columns, TCAD_CONST(0.0));
            for (int ii = static_cast<int>(columns) - 1; ii >= 0; --ii) {
                size_t i = static_cast<size_t>(ii);
                y[i] = g[i];
                for (size_t k = i + 1; k < columns; ++k) {
                    y[i] -= H[k][i] * y[k];
                }
                y[i] /= H[i][i];
            }

            for (size_t i = 0; i < columns; ++i) {
                Vector zi = precondition(V[i]);
                for (size_t k = 0; k < n; ++k) x[k] += y[i] * zi[k];
            }
        }
        r = b - A.apply(x);
        if (scaled_norm(r) / bnrm < opt_.tol) {
            if (opt_.verbose) std::cout << "GMRES converged at iter " << total_iter << std::endl;
            return total_iter;
        }
        // No further independent Krylov direction exists in this cycle.
        // Preserve the best guess on inconsistent systems; callers retain
        // their original-equation residual acceptance checks.
        if (breakdown) break;
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
    if (bnrm < EPSILON) bnrm = TCAD_CONST(1.0);

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
    if (bnrm < EPSILON) bnrm = TCAD_CONST(1.0);
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
    inv_diag_.assign(n, TCAD_CONST(0.0));
    const auto& vals = A.vals();
    const auto& cols = A.col_indices();
    const auto& rp = A.row_offsets();
    for (size_t i = 0; i < n; ++i) {
        for (size_t idx = rp[i]; idx < rp[i + 1]; ++idx) {
            if (cols[idx] == i) {
                if (abs_q(vals[idx]) > EPSILON)
                    inv_diag_[i] = TCAD_CONST(1.0) / vals[idx];
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

bool LinearSolver::try_banded_direct(const SparseMatrix& A, const Vector& b, Vector& x) {
    if (A.rows() != b.size())
        throw std::invalid_argument("banded solve RHS dimension mismatch");
    Vector candidate;
    try {
        dense_direct(A, b, candidate, true);
    } catch (const std::runtime_error&) {
        return false;
    }
    x = std::move(candidate);
    return true;
}

size_t LinearSolver::dense_direct(const SparseMatrix& A, const Vector& b, Vector& x, bool banded_only) {
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
        if (candidate.size() != n) return TCAD_CONST(1.0e100);
        const Vector applied = A.apply(candidate);
        real_t worst = TCAD_CONST(0.0);
        for (size_t i = 0; i < n; ++i) {
            real_t scale = abs_q(b[i]);
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                scale += abs_q(vals[entry] * candidate[cols[entry]]);
            const real_t relative =
                abs_q(applied[i] - b[i]) / std::max(scale, TCAD_CONST(1.0));
            if (!std::isfinite((double)relative)) return TCAD_CONST(1.0e100);
            worst = std::max(worst, relative);
        }
        return worst;
    };
    [[maybe_unused]] auto candidate_is_acceptable = [&](const Vector& candidate) {
        return candidate_backward_residual(candidate) <= TCAD_CONST(1.0e-8);
    };
    // Species-block Newton ordering hides the small physical bandwidth of
    // a 1-D device. Reduce the bandwidth using the undirected nonzero graph;
    // this is a symmetric permutation, not an approximation of the matrix.
    // Only recurse after proving the new matrix qualifies for the band path,
    // so an unsuccessful ordering cannot trigger repeated reordering.
    if (n >= 96 && !(band_width <= 257 && 4 * band_width < n)) {
        std::vector<std::vector<size_t>> adjacency(n);
        for (size_t i = 0; i < n; ++i) {
            for (size_t e = rp[i]; e < rp[i + 1]; ++e) {
                const size_t j = cols[e];
                if (i == j || vals[e] == TCAD_CONST(0.0)) continue;
                adjacency[i].push_back(j);
                adjacency[j].push_back(i);
            }
        }
        for (auto& neighbours : adjacency) {
            std::sort(neighbours.begin(), neighbours.end());
            neighbours.erase(std::unique(neighbours.begin(), neighbours.end()),
                             neighbours.end());
        }
        auto degree_order = [&](size_t i, size_t j) {
            if (adjacency[i].size() != adjacency[j].size())
                return adjacency[i].size() < adjacency[j].size();
            return i < j;
        };
        std::vector<size_t> seeds(n), order;
        for (size_t i = 0; i < n; ++i) seeds[i] = i;
        std::sort(seeds.begin(), seeds.end(), degree_order);
        std::vector<char> visited(n, 0);
        order.reserve(n);
        for (const size_t seed : seeds) {
            if (visited[seed]) continue;
            const size_t component_start = order.size();
            visited[seed] = 1;
            order.push_back(seed);
            for (size_t head = component_start; head < order.size(); ++head) {
                std::vector<size_t> next;
                for (const size_t j : adjacency[order[head]]) {
                    if (!visited[j]) { visited[j] = 1; next.push_back(j); }
                }
                std::sort(next.begin(), next.end(), degree_order);
                order.insert(order.end(), next.begin(), next.end());
            }
        }
        std::reverse(order.begin(), order.end());
        std::vector<size_t> position(n);
        for (size_t i = 0; i < n; ++i) position[order[i]] = i;
        size_t lower = 0, upper = 0;
        for (size_t i = 0; i < n; ++i) {
            for (size_t e = rp[i]; e < rp[i + 1]; ++e) {
                if (vals[e] == TCAD_CONST(0.0)) continue;
                const size_t row = position[i], col = position[cols[e]];
                if (row > col) lower = std::max(lower, row - col);
                else upper = std::max(upper, col - row);
            }
        }
        const size_t reduced_width = lower + upper + 1;
        if (reduced_width <= 257 && 4 * reduced_width < n &&
            reduced_width < band_width) {
            SparseMatrix permuted(n);
            Vector permuted_rhs(n), permuted_x(n, TCAD_CONST(0.0));
            for (size_t i = 0; i < n; ++i) {
                permuted_rhs[position[i]] = b[i];
                for (size_t e = rp[i]; e < rp[i + 1]; ++e)
                    if (vals[e] != TCAD_CONST(0.0))
                        permuted.add_entry(position[i], position[cols[e]], vals[e]);
            }
            permuted.finalize();
            dense_direct(permuted, permuted_rhs, permuted_x, banded_only);
            Vector candidate(n);
            for (size_t i = 0; i < n; ++i) candidate[i] = permuted_x[position[i]];
            if (candidate_is_acceptable(candidate)) {
                if (getenv("TCAD_LIN_DEBUG"))
                    std::cerr << "[reordered direct n=" << n << " bw="
                              << band_width << " -> " << reduced_width << "]\n";
                x = std::move(candidate);
                return 1;
            }
        }
    }
    if (n > 32 && band_width <= 257 && 4 * band_width < n) {
#ifdef TCAD_USE_LAPACK
        // Try the optimized double-precision band factorization first.  Row
        // equilibration is formed in float128 and the candidate is judged on
        // the original float128 equations, so this fast path cannot weaken
        // the continuity residual gate.  The portable float128 band solver
        // below remains the accuracy fallback.
        const lapack_int ni = static_cast<lapack_int>(n);
        const lapack_int nrhsi = 1;
        const lapack_int kli = static_cast<lapack_int>(lower_bw);
        const lapack_int kui = static_cast<lapack_int>(upper_bw);
        const lapack_int ldab = 2 * kli + kui + 1;
        std::vector<real_t> row_scale(n, TCAD_CONST(1.0));
        bool valid_rows = true;
        for (size_t i = 0; i < n; ++i) {
            real_t scale = TCAD_CONST(0.0);
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                scale = std::max(scale, abs_q(vals[entry]));
            if (!(scale > TCAD_CONST(0.0))) {
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
                std::vector<lapack_int> ipiv(n);
                lapack_int info = 0;
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
        std::vector<real_t> band(n * band_width, TCAD_CONST(0.0));
        Vector rhs = b;

        bool banded_ok = true;
        auto at = [&](size_t row, size_t col) -> real_t& {
            return band[row * band_width + col + lower_bw - row];
        };
        for (size_t i = 0; i < n; ++i) {
            real_t row_scale = TCAD_CONST(0.0);
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                row_scale = std::max(row_scale, abs_q(vals[entry]));
            if (!(row_scale > EPSILON) ||
                !std::isfinite((double)row_scale)) {
                banded_ok = false;
                break;
            }
            for (size_t entry = rp[i]; entry < rp[i + 1]; ++entry)
                at(i, cols[entry]) = vals[entry] / row_scale;
            rhs[i] /= row_scale;
        }
        for (size_t k = 0; banded_ok && k < n; ++k) {
            const real_t pivot = at(k, k);
            if (abs_q(pivot) < TCAD_CONST(1.0e-28) ||
                !std::isfinite((double)pivot)) {
                banded_ok = false;
                break;
            }
            const size_t i_end = std::min(n - 1, k + lower_bw);
            const size_t j_end = std::min(n - 1, k + upper_bw);
            for (size_t i = k + 1; i <= i_end; ++i) {
                const real_t factor = at(i, k) / pivot;
                at(i, k) = TCAD_CONST(0.0);
                for (size_t j = k + 1; j <= j_end; ++j)
                    at(i, j) -= factor * at(k, j);
                rhs[i] -= factor * rhs[k];
            }
        }
        if (banded_ok) {
            x.assign(n, TCAD_CONST(0.0));
            for (size_t reverse = n; reverse-- > 0;) {
                real_t value = rhs[reverse];
                const size_t j_end = std::min(n - 1, reverse + upper_bw);
                for (size_t j = reverse + 1; j <= j_end; ++j)
                    value -= at(reverse, j) * x[j];
                const real_t pivot = at(reverse, reverse);
                if (abs_q(pivot) < TCAD_CONST(1.0e-28) ||
                    !std::isfinite((double)pivot)) {
                    banded_ok = false;
                    break;
                }
                x[reverse] = value / pivot;
            }
            if (banded_ok && candidate_is_acceptable(x))
                return 1;
        }
        // Partial pivoting in band storage retains quad precision without
        // expanding a rejected no-pivot band to n*n. Pivot search is bounded
        // by the original lower bandwidth; row swaps can add at most that
        // much upper fill. Transform RHS during elimination so no out-of-band
        // L entries from earlier row interchanges need to be stored.
        const size_t pivot_upper = upper_bw + lower_bw;
        const size_t pivot_width = lower_bw + pivot_upper + 1;
        std::vector<real_t> pivot_band(n * pivot_width, TCAD_CONST(0.0));
        auto entry_at = [&](size_t row, size_t col) -> real_t& {
            return pivot_band[row * pivot_width + col + lower_bw - row];
        };
        Vector pivot_rhs = b, column_scale(n, TCAD_CONST(0.0));
        bool pivot_ok = true;
        for (size_t i = 0; i < n; ++i) {
            real_t scale = TCAD_CONST(0.0);
            for (size_t e = rp[i]; e < rp[i + 1]; ++e)
                scale = std::max(scale, abs_q(vals[e]));
            if (!(scale > TCAD_CONST(0.0)) || !isfinite_q(scale)) {
                pivot_ok = false;
                break;
            }
            pivot_rhs[i] /= scale;
            for (size_t e = rp[i]; e < rp[i + 1]; ++e) {
                entry_at(i, cols[e]) = vals[e] / scale;
                column_scale[cols[e]] = std::max(column_scale[cols[e]],
                                                abs_q(entry_at(i, cols[e])));
            }
        }
        for (size_t j = 0; pivot_ok && j < n; ++j) {
            if (!(column_scale[j] > TCAD_CONST(0.0)) ||
                !isfinite_q(column_scale[j])) { pivot_ok = false; break; }
        }
        for (size_t i = 0; pivot_ok && i < n; ++i)
            for (size_t e = rp[i]; e < rp[i + 1]; ++e)
                entry_at(i, cols[e]) /= column_scale[cols[e]];
        for (size_t k = 0; pivot_ok && k < n; ++k) {
            const size_t i_end = std::min(n - 1, k + lower_bw);
            const size_t j_end = std::min(n - 1, k + pivot_upper);
            size_t selected = k;
            for (size_t i = k + 1; i <= i_end; ++i)
                if (abs_q(entry_at(i, k)) > abs_q(entry_at(selected, k)))
                    selected = i;
            const real_t pivot = entry_at(selected, k);
            if (pivot == TCAD_CONST(0.0) || !isfinite_q(pivot)) {
                pivot_ok = false;
                break;
            }
            if (selected != k) {
                for (size_t j = k; j <= j_end; ++j)
                    std::swap(entry_at(k, j), entry_at(selected, j));
                std::swap(pivot_rhs[k], pivot_rhs[selected]);
            }
            for (size_t i = k + 1; i <= i_end; ++i) {
                if (entry_at(i, k) == TCAD_CONST(0.0)) continue;
                const real_t factor = entry_at(i, k) / pivot;
                entry_at(i, k) = TCAD_CONST(0.0);
                for (size_t j = k + 1; j <= j_end; ++j)
                    entry_at(i, j) -= factor * entry_at(k, j);
                pivot_rhs[i] -= factor * pivot_rhs[k];
            }
        }
        if (pivot_ok) {
            Vector candidate(n, TCAD_CONST(0.0));
            for (size_t i = n; i-- > 0;) {
                real_t value = pivot_rhs[i];
                const size_t j_end = std::min(n - 1, i + pivot_upper);
                for (size_t j = i + 1; j <= j_end; ++j)
                    value -= entry_at(i, j) * candidate[j];
                candidate[i] = value / entry_at(i, i);
            }
            for (size_t i = 0; i < n; ++i) candidate[i] /= column_scale[i];
            if (candidate_is_acceptable(candidate)) {
                if (getenv("TCAD_LIN_DEBUG"))
                    std::cerr << "[quad pivot band n=" << n << " bw="
                              << band_width << "]\n";
                x = std::move(candidate);
                return 1;
            }
        }
        // A high-field Scharfetter-Gummel continuity block can be narrow but
        // not safely solvable by the portable no-pivot banded eliminator.
        // Keep that fast path for diagonally dominant cases, but fall through
        // to the general dense solver below when a tiny pivot or poor
        // backward residual is detected.  The dense fallback uses partial
        // pivoting (and LAPACK when available), which avoids reporting a
        // recoverable Gummel substep as a hard zero-pivot failure.
        if (getenv("TCAD_LIN_DEBUG"))
            std::cerr << "[banded direct rejected -> dense pivot fallback]\n";
    }

    // The optional large-Newton attempt is memory bounded even for a graph
    // that cannot be ordered narrowly, a singular band or a rejected pivot.
    // The caller then retains its original iterative backend and audit.
    if (banded_only)
        throw std::runtime_error("bounded banded direct solve unavailable");

    // Convert sparse to dense (flattened row-major)
    std::vector<real_t> M(n * n, TCAD_CONST(0.0));
    for (size_t i = 0; i < n; ++i) {
        for (size_t idx = rp[i]; idx < rp[i + 1]; ++idx) {
            M[i * n + cols[idx]] = vals[idx];
        }
    }

    Vector rhs = b;

    // Eliminate exact one-entry diagonal constraints before pivoting the
    // quiet-carrier block. Otherwise near-null pivots can mix a tiny contact
    // value into a huge carrier equation and corrupt the fixed row itself.
    std::vector<char> fixed(n, 0);
    Vector fixed_value(n, TCAD_CONST(0.0));
    for (size_t i = 0; i < n; ++i) {
        if (M[i*n+i] == TCAD_CONST(0.0)) continue;
        bool diagonal_only = true;
        for (size_t j = 0; j < n; ++j)
            if (j != i && M[i*n+j] != TCAD_CONST(0.0)) { diagonal_only = false; break; }
        if (diagonal_only) {
            fixed[i] = 1;
            fixed_value[i] = rhs[i] / M[i*n+i];
        }
    }
    for (size_t i = 0; i < n; ++i) {
        if (fixed[i]) {
            M[i*n+i] = TCAD_CONST(1.0);
            rhs[i] = fixed_value[i];
        } else {
            for (size_t j = 0; j < n; ++j) if (fixed[j]) {
                rhs[i] -= M[i*n+j] * fixed_value[j];
                M[i*n+j] = TCAD_CONST(0.0);
            }
        }
    }

    // Sparsity counts do not establish adjacency: a 2-D three-point row can
    // connect non-neighbouring flattened indices. Never discard such links.
    bool is_tridiag = true;
    for (size_t i = 0; i < n && is_tridiag; ++i) {
        for (size_t j = 0; j < n; ++j) {
            if (M[i * n + j] != TCAD_CONST(0.0) && (j + 1 < i || j > i + 1)) {
                is_tridiag = false;
                break;
            }
        }
    }

    // Tridiagonal system with Dirichlet rows at both boundaries: solve interior
    // using Thomas algorithm and set boundary values directly.
    if (is_tridiag && n > 2) {
        bool dirichlet_0 = M[0] != TCAD_CONST(0.0);
        for (size_t j = 1; j < n; ++j) {
            if (M[j] != TCAD_CONST(0.0)) { dirichlet_0 = false; break; }
        }
        bool dirichlet_n1 = M[(n-1)*n + (n-1)] != TCAD_CONST(0.0);
        for (size_t j = 0; j < n-1; ++j) {
            if (M[(n-1)*n + j] != TCAD_CONST(0.0)) { dirichlet_n1 = false; break; }
        }
        if (dirichlet_0 && dirichlet_n1) {
            const real_t left_value = rhs[0] / M[0];
            const real_t right_value = rhs[n-1] / M[(n-1)*n + n-1];
            size_t m = n - 2;
            if (m == 0) {
                x[0] = left_value;
                x[n-1] = right_value;
                return 1;
            }
            std::vector<real_t> a(m, TCAD_CONST(0.0)), d(m, TCAD_CONST(0.0)), c_t(m, TCAD_CONST(0.0)), b(m, TCAD_CONST(0.0));
            for (size_t i = 0; i < m; ++i) {
                size_t row = i + 1;
                d[i] = M[row * n + row];
                if (i > 0) a[i] = M[row * n + (row - 1)];
                if (i + 1 < m) c_t[i] = M[row * n + (row + 1)];
                b[i] = rhs[row];
            }
            // Subtract Dirichlet contributions from RHS
            b[0] -= M[1 * n + 0] * left_value;
            b[m-1] -= M[(n-2) * n + (n-1)] * right_value;
            // A valid tridiagonal matrix can still require pivoting. A zero
            // Thomas pivot must fall through to the general solver below.
            bool valid_thomas = true;
            for (size_t i = 1; i < m; ++i) {
                if (d[i-1] == TCAD_CONST(0.0) || !isfinite_q(d[i-1])) { valid_thomas = false; break; }
                real_t w = a[i] / d[i - 1];
                d[i] -= w * c_t[i - 1];
                b[i] -= w * b[i - 1];
            }
            if (valid_thomas && d[m-1] != TCAD_CONST(0.0) && isfinite_q(d[m-1])) {
                Vector candidate(n, TCAD_CONST(0.0));
                candidate[0] = left_value;
                candidate[n-1] = right_value;
                candidate[n-2] = b[m-1] / d[m-1];
                for (int ii = static_cast<int>(m) - 2; ii >= 0; --ii) {
                    size_t i = static_cast<size_t>(ii);
                    candidate[i+1] = (b[i] - c_t[i] * candidate[i+2]) / d[i];
                }
                if (candidate_is_acceptable(candidate)) {
                    x = std::move(candidate);
                    return 1;
                }
            }
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
        const lapack_int ni = static_cast<lapack_int>(n);
        const lapack_int nrhsi = 1;
        lapack_int info = 0;
        bool validate_lapack_candidate = true;
        std::vector<double> B(n);
        const size_t bw = kl + ku + 1;
        if (getenv("TCAD_LIN_DEBUG")) { static long long c=0; if(++c<=8) std::cerr << "[LAPACK n=" << n << " bw=" << bw << " banded=" << (n>32 && 4*bw<n) << "]\n"; }
        if (n > 32 && 4 * bw < n) {
            for (size_t i = 0; i < n; ++i)
                B[i] = static_cast<double>(rhs[i]);
            // Banded: LAPACK column-major band storage AB[(2*kl+ku+1) x n].
            const lapack_int kli = static_cast<lapack_int>(kl);
            const lapack_int kui = static_cast<lapack_int>(ku);
            const lapack_int ldab = 2 * kli + kui + 1;
            std::vector<double> AB(static_cast<size_t>(ldab) * n, 0.0);
            for (size_t i = 0; i < n; ++i) {
                for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx) {
                    size_t j = cols_csr[idx];
                    int row = static_cast<int>(kl + ku + i - j);  // AB row (LAPACK band layout)
                    AB[static_cast<size_t>(j) * ldab + row] = static_cast<double>(M[i*n+j]);  // column-major
                }
            }
            std::vector<lapack_int> ipiv(n);
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
            std::vector<real_t> row_scale(n, TCAD_CONST(1.0));
            for (size_t i = 0; i < n; ++i) {
                real_t scale = TCAD_CONST(0.0);
                for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx)
                    scale = std::max(scale, abs_q(M[i*n+cols_csr[idx]]));
                if (scale > TCAD_CONST(0.0)) row_scale[i] = scale;
            }
            auto factor_scaled = [&](double diagonal_shift) {
                std::vector<double> AD(n * n, 0.0);
                for (size_t i = 0; i < n; ++i) {
                    B[i] = static_cast<double>(rhs[i] / row_scale[i]);
                    for (size_t idx = rp_csr[i]; idx < rp_csr[i + 1]; ++idx)
                        AD[cols_csr[idx] * n + i] =
                            static_cast<double>(M[i*n+cols_csr[idx]] / row_scale[i]);
                    AD[i * n + i] += diagonal_shift;
                }
                std::vector<lapack_int> ipiv(n);
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
            for (size_t i = 0; i < n; ++i)
                if (fixed[i]) candidate[i] = fixed_value[i];
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

    // Normalize equation and unknown scales before quad elimination. A fixed
    // absolute pivot floor changes nonsingular quiet-carrier equations when
    // their units put every coefficient below 1e-20.
    for (size_t i = 0; i < n; ++i) {
        real_t scale = TCAD_CONST(0.0);
        for (size_t j = 0; j < n; ++j) scale = std::max(scale, abs_q(M[i*n+j]));
        if (scale > TCAD_CONST(0.0) && isfinite_q(scale)) {
            for (size_t j = 0; j < n; ++j) M[i*n+j] /= scale;
            rhs[i] /= scale;
        }
    }
    Vector quad_column_scale(n, TCAD_CONST(1.0));
    for (size_t j = 0; j < n; ++j) {
        real_t scale = TCAD_CONST(0.0);
        for (size_t i = 0; i < n; ++i) scale = std::max(scale, abs_q(M[i*n+j]));
        if (scale > TCAD_CONST(0.0) && isfinite_q(scale)) {
            quad_column_scale[j] = TCAD_CONST(1.0) / scale;
            for (size_t i = 0; i < n; ++i) M[i*n+j] /= scale;
        }
    }

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
        if (max_val == TCAD_CONST(0.0)) {
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
    for (size_t i = 0; i < n; ++i) x[i] *= quad_column_scale[i];
    return 1;
}

#ifdef TCAD_USE_PETSC
size_t LinearSolver::solve_petsc(const SparseMatrix& A, const Vector& b, Vector& x) {
    auto check = [](PetscErrorCode code, const char* operation) {
        if (code) throw std::runtime_error(std::string("PETSc ") + operation +
            " failed with error code " + std::to_string(code));
    };
    if (b.size() > static_cast<size_t>(std::numeric_limits<PetscInt>::max()))
        throw std::overflow_error("PETSc matrix dimension exceeds PetscInt range");
    // Ensure PETSc is initialized (idempotent)
    PetscBool petsc_initialized;
    check(PetscInitialized(&petsc_initialized), "PetscInitialized");
    if (!petsc_initialized) {
        check(PetscInitialize(nullptr, nullptr, nullptr, nullptr), "PetscInitialize");
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
    bool reuse = (petsc_n_ == N && petsc_A_ != nullptr && petsc_ksp_ != nullptr &&
        petsc_row_offsets_ == row_ptr && petsc_col_indices_ == col_idx);
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
            check(MatSetValues(petsc_A_, 1, &row, ncols, cols.data(), vals.data(), INSERT_VALUES), "MatSetValues");
        }
        check(MatAssemblyBegin(petsc_A_, MAT_FINAL_ASSEMBLY), "MatAssemblyBegin");
        check(MatAssemblyEnd(petsc_A_, MAT_FINAL_ASSEMBLY), "MatAssemblyEnd");
    };

    if (!reuse) {
        petsc_free();
        std::vector<PetscInt> row_nnz(n);
        for (size_t i = 0; i < n; ++i)
            row_nnz[i] = static_cast<PetscInt>(row_ptr[i + 1] - row_ptr[i]);
        check(MatCreateSeqAIJ(PETSC_COMM_SELF, N, N, 0, row_nnz.data(), &petsc_A_), "MatCreateSeqAIJ");
        fill_matrix();
        // Lock the nonzero pattern so SuperLU reuses the symbolic factorization
        // on subsequent calls (only the numeric factorization is redone).
        check(MatSetOption(petsc_A_, MAT_NEW_NONZERO_LOCATIONS, PETSC_FALSE), "MatSetOption");
        check(VecCreateSeq(PETSC_COMM_SELF, N, &petsc_b_), "VecCreateSeq");
        check(VecCreateSeq(PETSC_COMM_SELF, N, &petsc_x_), "VecCreateSeq");
        check(KSPCreate(PETSC_COMM_SELF, &petsc_ksp_), "KSPCreate");
        check(KSPSetOperators(petsc_ksp_, petsc_A_, petsc_A_), "KSPSetOperators");
        check(KSPSetTolerances(petsc_ksp_, static_cast<PetscReal>(opt_.tol), PETSC_DEFAULT,
                         PETSC_DEFAULT, static_cast<PetscInt>(opt_.max_iter)), "KSPSetTolerances");
        PC pc;
        check(KSPGetPC(petsc_ksp_, &pc), "KSPGetPC");
        if (n < 80000) {
            check(KSPSetType(petsc_ksp_, KSPPREONLY), "KSPSetType");
            check(PCSetType(pc, PCLU), "PCSetType");
            check(PCFactorSetMatSolverType(pc, MATSOLVERSUPERLU), "PCFactorSetMatSolverType");
        } else {
            check(KSPSetType(petsc_ksp_, KSPBCGS), "KSPSetType");
            check(PCSetType(pc, PCGAMG), "PCSetType");
        }
        check(KSPSetFromOptions(petsc_ksp_), "KSPSetFromOptions");
        petsc_n_ = N;
        petsc_row_offsets_ = row_ptr;
        petsc_col_indices_ = col_idx;
    } else {
        // Same complete CSR pattern: update values and reuse the cached KSP.
        // Structural changes above rebuild the matrix and factorization.
        check(MatZeroEntries(petsc_A_), "MatZeroEntries");
        check(MatSetOption(petsc_A_, MAT_NEW_NONZERO_LOCATIONS, PETSC_FALSE), "MatSetOption");
        fill_matrix();
    }

    // RHS
    PetscScalar* b_arr;
    check(VecGetArray(petsc_b_, &b_arr), "VecGetArray");
    for (size_t i = 0; i < n; ++i) b_arr[i] = static_cast<PetscScalar>(b[i]);
    check(VecRestoreArray(petsc_b_, &b_arr), "VecRestoreArray");
    // Initial guess
    PetscScalar* x_arr;
    check(VecGetArray(petsc_x_, &x_arr), "VecGetArray");
    for (size_t i = 0; i < n; ++i) x_arr[i] = static_cast<PetscScalar>(x[i]);
    check(VecRestoreArray(petsc_x_, &x_arr), "VecRestoreArray");

    check(KSPSolve(petsc_ksp_, petsc_b_, petsc_x_), "KSPSolve");

    KSPConvergedReason reason;
    check(KSPGetConvergedReason(petsc_ksp_, &reason), "KSPGetConvergedReason");
    if (reason <= 0) {
        std::cerr << "PETSc KSP failed (reason " << static_cast<int>(reason)
                  << "): " << KSPConvergedReasons[reason] << std::endl;
        throw std::runtime_error("PETSc linear solve failed");
    }

    PetscInt its;
    check(KSPGetIterationNumber(petsc_ksp_, &its), "KSPGetIterationNumber");

    check(VecGetArray(petsc_x_, &x_arr), "VecGetArray");
    for (size_t i = 0; i < n; ++i) x[i] = static_cast<real_t>(x_arr[i]);
    check(VecRestoreArray(petsc_x_, &x_arr), "VecRestoreArray");

    // NOTE: no KSPDestroy/MatDestroy here — objects are cached for reuse.
    return static_cast<size_t>(its);
}
#endif

} // namespace tcad
