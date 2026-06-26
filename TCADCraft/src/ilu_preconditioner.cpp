#include "ilu_preconditioner.h"
#include <iostream>

namespace tcad {

void ILU0Preconditioner::setup(const SparseMatrix& A) {
    n_ = A.rows();
    lu_vals_ = A.vals(); // copy
    cols_ = A.col_indices();
    row_ptr_ = A.row_offsets();

    for (size_t i = 0; i < n_; ++i) {
        size_t diag_idx = row_ptr_[i];
        // Find diagonal position in row i
        for (; diag_idx < row_ptr_[i + 1]; ++diag_idx) {
            if (cols_[diag_idx] == i) break;
        }
        if (diag_idx >= row_ptr_[i + 1] || cols_[diag_idx] != i) {
            throw std::runtime_error("ILU0: zero diagonal element");
        }

        for (size_t k_idx = row_ptr_[i]; k_idx < diag_idx; ++k_idx) {
            size_t k = cols_[k_idx];
            if (k >= i) continue;

            // Find A[k,k]
            size_t k_diag = row_ptr_[k];
            for (; k_diag < row_ptr_[k + 1]; ++k_diag) {
                if (cols_[k_diag] == k) break;
            }
            if (k_diag >= row_ptr_[k + 1] || cols_[k_diag] != k) continue;

            real_t diag_val = lu_vals_[k_diag];
            if (abs_q(diag_val) < 1e-12Q) diag_val = 1e-12Q;
            real_t multiplier = lu_vals_[k_idx] / diag_val;
            lu_vals_[k_idx] = multiplier;

            // Update remaining elements in row i
            size_t j_idx = k_idx + 1;
            size_t l_idx = k_diag + 1;
            while (j_idx < row_ptr_[i + 1] && l_idx < row_ptr_[k + 1]) {
                size_t col_j = cols_[j_idx];
                size_t col_l = cols_[l_idx];
                if (col_j == col_l) {
                    lu_vals_[j_idx] -= multiplier * lu_vals_[l_idx];
                    ++j_idx; ++l_idx;
                } else if (col_j < col_l) {
                    ++j_idx;
                } else {
                    ++l_idx;
                }
            }
        }
    }

    // Post-process: ensure all diagonal entries in U are non-zero
    for (size_t i = 0; i < n_; ++i) {
        size_t diag_idx = row_ptr_[i];
        for (; diag_idx < row_ptr_[i + 1]; ++diag_idx) {
            if (cols_[diag_idx] == i) break;
        }
        if (diag_idx < row_ptr_[i + 1] && abs_q(lu_vals_[diag_idx]) < EPSILON) {
            lu_vals_[diag_idx] = (lu_vals_[diag_idx] >= 0) ? EPSILON : -EPSILON;
        }
    }
}

Vector ILU0Preconditioner::apply(const Vector& r) const {
    Vector z(n_, 0.0Q);
    Vector y(n_, 0.0Q);

    // Forward solve L*y = r (L has unit diagonal)
    for (size_t i = 0; i < n_; ++i) {
        y[i] = r[i];
        for (size_t idx = row_ptr_[i]; idx < row_ptr_[i + 1]; ++idx) {
            size_t j = cols_[idx];
            if (j < i) {
                y[i] -= lu_vals_[idx] * y[j];
            }
        }
    }

    // Backward solve U*z = y
    for (int ii = static_cast<int>(n_) - 1; ii >= 0; --ii) {
        size_t i = static_cast<size_t>(ii);
        z[i] = y[i];
        size_t diag_idx = row_ptr_[i];
        for (; diag_idx < row_ptr_[i + 1]; ++diag_idx) {
            if (cols_[diag_idx] == i) break;
        }
        for (size_t idx = diag_idx + 1; idx < row_ptr_[i + 1]; ++idx) {
            size_t j = cols_[idx];
            if (j > i) {
                z[i] -= lu_vals_[idx] * z[j];
            }
        }
        if (diag_idx >= row_ptr_[i + 1]) {
            throw std::runtime_error("ILU0 apply: missing diagonal in U");
        }
        z[i] /= lu_vals_[diag_idx];
    }
    return z;
}

} // namespace tcad
