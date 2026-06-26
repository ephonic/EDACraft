#include "linear_solver.h"
#include <iostream>
#include <algorithm>

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

LinearSolver::~LinearSolver() = default;

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
#ifdef TCAD_USE_PETSC
        case SolverType::PETSC:
            return solve_petsc(A, b, x);
#endif
    }
    return 0;
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
    // Convert sparse to dense (flattened row-major)
    std::vector<real_t> M(n * n, 0.0Q);
    const auto& vals = A.vals();
    const auto& cols = A.col_indices();
    const auto& rp = A.row_offsets();
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

    // Gaussian elimination with partial pivoting
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
    const size_t nnz = A.nnz();

    Mat petsc_A;
    Vec petsc_b, petsc_x;
    KSP ksp;
    PC pc;

    MatCreateSeqAIJ(PETSC_COMM_SELF, static_cast<PetscInt>(n), static_cast<PetscInt>(n),
                    static_cast<PetscInt>(nnz), nullptr, &petsc_A);

    // Copy CSR data to PETSc matrix
    const auto& row_ptr = A.row_offsets();
    const auto& col_idx = A.col_indices();
    const auto& values = A.vals();
    for (size_t i = 0; i < n; ++i) {
        PetscInt row = static_cast<PetscInt>(i);
        PetscInt ncols = static_cast<PetscInt>(row_ptr[i+1] - row_ptr[i]);
        if (ncols == 0) continue;
        std::vector<PetscInt> cols;
        cols.reserve(ncols);
        std::vector<PetscScalar> vals;
        vals.reserve(ncols);
        for (size_t j = row_ptr[i]; j < row_ptr[i+1]; ++j) {
            cols.push_back(static_cast<PetscInt>(col_idx[j]));
            vals.push_back(static_cast<PetscScalar>(values[j]));
        }
        MatSetValues(petsc_A, 1, &row, ncols, cols.data(), vals.data(), INSERT_VALUES);
    }
    MatAssemblyBegin(petsc_A, MAT_FINAL_ASSEMBLY);
    MatAssemblyEnd(petsc_A, MAT_FINAL_ASSEMBLY);

    VecCreateSeq(PETSC_COMM_SELF, static_cast<PetscInt>(n), &petsc_b);
    VecCreateSeq(PETSC_COMM_SELF, static_cast<PetscInt>(n), &petsc_x);

    PetscScalar* b_arr;
    VecGetArray(petsc_b, &b_arr);
    for (size_t i = 0; i < n; ++i) {
        b_arr[i] = static_cast<PetscScalar>(b[i]);
    }
    VecRestoreArray(petsc_b, &b_arr);

    // Set initial guess
    PetscScalar* x_arr;
    VecGetArray(petsc_x, &x_arr);
    for (size_t i = 0; i < n; ++i) {
        x_arr[i] = static_cast<PetscScalar>(x[i]);
    }
    VecRestoreArray(petsc_x, &x_arr);

    KSPCreate(PETSC_COMM_SELF, &ksp);
    KSPSetOperators(ksp, petsc_A, petsc_A);
    KSPSetTolerances(ksp, static_cast<PetscReal>(opt_.tol), PETSC_DEFAULT,
                     PETSC_DEFAULT, static_cast<PetscInt>(opt_.max_iter));

    KSPGetPC(ksp, &pc);

    // For moderate-sized systems (< 50k nodes), use direct LU via PETSc
    // for guaranteed robustness.  For larger systems, iterative solvers
    // can be selected via -ksp_type / -pc_type command-line options.
    if (n < 50000) {
        KSPSetType(ksp, KSPPREONLY);
        PCSetType(pc, PCLU);
    } else {
        KSPSetType(ksp, KSPBCGS);
        PCSetType(pc, PCILU);
    }

    // Allow command-line override (e.g., -ksp_type cg -pc_type hypre)
    KSPSetFromOptions(ksp);

    KSPSolve(ksp, petsc_b, petsc_x);

    PetscInt its;
    KSPGetIterationNumber(ksp, &its);

    VecGetArray(petsc_x, &x_arr);
    for (size_t i = 0; i < n; ++i) {
        x[i] = static_cast<real_t>(x_arr[i]);
    }
    VecRestoreArray(petsc_x, &x_arr);

    KSPDestroy(&ksp);
    VecDestroy(&petsc_b);
    VecDestroy(&petsc_x);
    MatDestroy(&petsc_A);

    return static_cast<size_t>(its);
}
#endif

} // namespace tcad
