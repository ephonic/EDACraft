#include "ic_preconditioner.h"
#include <iostream>
#include <cmath>

namespace tcad {

void IC0Preconditioner::setup(const SparseMatrix& A) {
    n_ = A.rows();
    const auto& a_vals = A.vals();
    const auto& a_cols = A.col_indices();
    const auto& a_rp = A.row_offsets();

    // Extract lower triangular part of A (including diagonal) into L CSR
    size_t nnz = 0;
    for (size_t i = 0; i < n_; ++i) {
        for (size_t idx = a_rp[i]; idx < a_rp[i + 1]; ++idx) {
            if (a_cols[idx] <= i) nnz++;
        }
    }

    l_vals_.resize(nnz);
    l_cols_.resize(nnz);
    l_row_ptr_.resize(n_ + 1);

    size_t pos = 0;
    for (size_t i = 0; i < n_; ++i) {
        l_row_ptr_[i] = pos;
        for (size_t idx = a_rp[i]; idx < a_rp[i + 1]; ++idx) {
            if (a_cols[idx] <= i) {
                l_cols_[pos] = a_cols[idx];
                l_vals_[pos] = a_vals[idx];
                pos++;
            }
        }
    }
    l_row_ptr_[n_] = pos;

    // IC(0) factorization
    for (size_t i = 0; i < n_; ++i) {
        // Find diagonal position in row i
        size_t diag_idx = l_row_ptr_[i];
        for (; diag_idx < l_row_ptr_[i + 1]; ++diag_idx) {
            if (l_cols_[diag_idx] == i) break;
        }
        if (diag_idx >= l_row_ptr_[i + 1]) {
            throw std::runtime_error("IC0: missing diagonal element");
        }

        for (size_t k_idx = l_row_ptr_[i]; k_idx < diag_idx; ++k_idx) {
            size_t k = l_cols_[k_idx];
            // Find L(k,k)
            size_t k_diag = l_row_ptr_[k];
            for (; k_diag < l_row_ptr_[k + 1]; ++k_diag) {
                if (l_cols_[k_diag] == k) break;
            }
            if (k_diag >= l_row_ptr_[k + 1]) continue;

            real_t lk_diag = l_vals_[k_diag];
            if (abs_q(lk_diag) < EPSILON) lk_diag = (lk_diag >= 0 ? EPSILON : -EPSILON);
            l_vals_[k_idx] /= lk_diag;

            // Update remaining elements in row i
            size_t j_idx = k_idx + 1;
            size_t l_idx = k_diag + 1;
            while (j_idx < l_row_ptr_[i + 1] && l_idx < l_row_ptr_[k + 1]) {
                size_t col_j = l_cols_[j_idx];
                size_t col_l = l_cols_[l_idx];
                if (col_j == col_l) {
                    l_vals_[j_idx] -= l_vals_[k_idx] * l_vals_[l_idx];
                    ++j_idx; ++l_idx;
                } else if (col_j < col_l) {
                    ++j_idx;
                } else {
                    ++l_idx;
                }
            }
        }

        // Diagonal: L(i,i) = sqrt(A(i,i) - sum_{k<i} L(i,k)^2)
        real_t diag_val = l_vals_[diag_idx];
        for (size_t k_idx = l_row_ptr_[i]; k_idx < diag_idx; ++k_idx) {
            diag_val -= l_vals_[k_idx] * l_vals_[k_idx];
        }
        if (diag_val <= 0.0Q) {
            // Perturb to maintain positive definiteness
            diag_val = abs_q(diag_val) + 1e-12Q;
        }
        l_vals_[diag_idx] = sqrt_q(diag_val);
    }

    // Build L^T CSR for efficient back substitution
    std::vector<size_t> count(n_, 0);
    for (size_t i = 0; i < n_; ++i) {
        for (size_t idx = l_row_ptr_[i]; idx < l_row_ptr_[i + 1]; ++idx) {
            count[l_cols_[idx]]++;
        }
    }

    lt_row_ptr_.resize(n_ + 1);
    lt_row_ptr_[0] = 0;
    for (size_t i = 0; i < n_; ++i) {
        lt_row_ptr_[i + 1] = lt_row_ptr_[i] + count[i];
    }

    std::fill(count.begin(), count.end(), 0);
    lt_cols_.resize(lt_row_ptr_[n_]);
    lt_vals_.resize(lt_row_ptr_[n_]);

    for (size_t i = 0; i < n_; ++i) {
        for (size_t idx = l_row_ptr_[i]; idx < l_row_ptr_[i + 1]; ++idx) {
            size_t j = l_cols_[idx];
            size_t p = lt_row_ptr_[j] + count[j];
            lt_cols_[p] = i;
            lt_vals_[p] = l_vals_[idx];
            count[j]++;
        }
    }
}

Vector IC0Preconditioner::apply(const Vector& r) const {
    Vector y(n_, 0.0Q);
    Vector z(n_, 0.0Q);

    // Forward solve L * y = r
    for (size_t i = 0; i < n_; ++i) {
        y[i] = r[i];
        size_t diag_idx = l_row_ptr_[i + 1];
        for (size_t idx = l_row_ptr_[i]; idx < l_row_ptr_[i + 1]; ++idx) {
            if (l_cols_[idx] == i) {
                diag_idx = idx;
                break;
            }
            y[i] -= l_vals_[idx] * y[l_cols_[idx]];
        }
        real_t diag = l_vals_[diag_idx];
        if (abs_q(diag) < EPSILON) diag = EPSILON;
        y[i] /= diag;
    }

    // Backward solve L^T * z = y
    for (int ii = static_cast<int>(n_) - 1; ii >= 0; --ii) {
        size_t i = static_cast<size_t>(ii);
        z[i] = y[i];
        size_t diag_idx = lt_row_ptr_[i];
        for (; diag_idx < lt_row_ptr_[i + 1]; ++diag_idx) {
            if (lt_cols_[diag_idx] == i) break;
        }
        for (size_t idx = diag_idx + 1; idx < lt_row_ptr_[i + 1]; ++idx) {
            z[i] -= lt_vals_[idx] * z[lt_cols_[idx]];
        }
        real_t diag = lt_vals_[diag_idx];
        if (abs_q(diag) < EPSILON) diag = EPSILON;
        z[i] /= diag;
    }

    return z;
}

} // namespace tcad
