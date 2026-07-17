#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include <vector>

namespace tcad {

// Incomplete LU(0) preconditioner for CSR matrices
// Factorizes A ≈ L*U where L and U have the same sparsity pattern as A
class ILU0Preconditioner {
public:
    void setup(const SparseMatrix& A);
    Vector apply(const Vector& r) const; // Solve M*z = r, where M = L*U

private:
    // Store L (unit diagonal, implicit) and U in CSR-like format
    // We reuse the CSR structure of A
    std::vector<real_t> lu_vals_;
    std::vector<size_t> cols_;
    std::vector<size_t> row_ptr_;
    size_t n_ = 0;
};

} // namespace tcad
