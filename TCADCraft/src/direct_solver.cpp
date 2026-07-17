#include "direct_solver.h"
#include <algorithm>
#include <iostream>
#include <cmath>

namespace tcad {

Vector DenseDirectSolver::solve(const SparseMatrix& A, const Vector& b) {
    const size_t n = A.rows();
    if (b.size() != n) throw std::invalid_argument("Dimension mismatch");

    // Convert CSR to dense column-major (for cache efficiency)
    std::vector<real_t> M(n * n, 0.0Q);
    const auto& vals = A.vals();
    const auto& cols = A.col_indices();
    const auto& rp = A.row_offsets();

    for (size_t i = 0; i < n; ++i) {
        for (size_t idx = rp[i]; idx < rp[i + 1]; ++idx) {
            M[i + n * cols[idx]] = vals[idx];
        }
    }

    // DEBUG output removed for production builds
    // (was verifying M[7,7] and M[19,19])

    std::vector<size_t> pivot(n);
    lu_factorize(M, n, pivot);

    Vector x(n, 0.0Q);
    lu_solve(M, n, pivot, b, x);
    return x;
}

void DenseDirectSolver::lu_factorize(std::vector<real_t>& M, size_t n, std::vector<size_t>& pivot) {
    for (size_t i = 0; i < n; ++i) pivot[i] = i;

    for (size_t k = 0; k < n; ++k) {
        // Partial pivoting
        size_t max_row = k;
        real_t max_val = abs_q(M[k + n * k]);
        for (size_t i = k + 1; i < n; ++i) {
            real_t v = abs_q(M[i + n * k]);
            if (v > max_val) { max_val = v; max_row = i; }
        }
        if (max_val < EPSILON) {
            // Debug: find rows with near-zero diagonal
            std::cerr << "DenseDirectSolver: singular matrix at column " << k << std::endl;
            for (size_t dbg = 0; dbg < n && dbg < 20; ++dbg) {
                std::cerr << "  diag[" << dbg << "] = " << (double)M[dbg + n * dbg] << std::endl;
            }
            throw std::runtime_error("DenseDirectSolver: singular matrix detected");
        }
        if (max_row != k) {
            std::swap(pivot[k], pivot[max_row]);
            for (size_t j = 0; j < n; ++j) {
                std::swap(M[k + n * j], M[max_row + n * j]);
            }
        }

        // Elimination
        for (size_t i = k + 1; i < n; ++i) {
            real_t factor = M[i + n * k] / M[k + n * k];
            M[i + n * k] = factor;
            for (size_t j = k + 1; j < n; ++j) {
                M[i + n * j] -= factor * M[k + n * j];
            }
        }
    }
}

void DenseDirectSolver::lu_solve(const std::vector<real_t>& M, size_t n,
                                 const std::vector<size_t>& pivot,
                                 const Vector& b, Vector& x) {
    // Forward substitution (Ly = Pb)
    Vector y(n);
    for (size_t i = 0; i < n; ++i) {
        y[i] = b[pivot[i]];
        for (size_t j = 0; j < i; ++j) {
            y[i] -= M[i + n * j] * y[j];
        }
    }

    // Back substitution (Ux = y)
    for (int ii = static_cast<int>(n) - 1; ii >= 0; --ii) {
        size_t i = static_cast<size_t>(ii);
        x[i] = y[i];
        for (size_t j = i + 1; j < n; ++j) {
            x[i] -= M[i + n * j] * x[j];
        }
        x[i] /= M[i + n * i];
    }
}

} // namespace tcad
