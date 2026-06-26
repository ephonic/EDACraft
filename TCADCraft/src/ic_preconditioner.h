#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include <vector>

namespace tcad {

// Incomplete Cholesky(0) preconditioner for symmetric SPD CSR matrices
// Factorizes A ≈ L * L^T where L has the same lower-triangular sparsity as A
class IC0Preconditioner {
public:
    void setup(const SparseMatrix& A);
    Vector apply(const Vector& r) const; // Solve L*L^T * z = r

private:
    // L in CSR (lower triangular including diagonal)
    std::vector<real_t> l_vals_;
    std::vector<size_t> l_cols_;
    std::vector<size_t> l_row_ptr_;
    size_t n_ = 0;

    // L^T in CSR (upper triangular) for efficient back substitution
    std::vector<real_t> lt_vals_;
    std::vector<size_t> lt_cols_;
    std::vector<size_t> lt_row_ptr_;
};

} // namespace tcad
