#pragma once

#include "math_types.h"
#include "sparse_matrix.h"
#include <vector>

namespace tcad {

// Small-scale dense direct solver (Gaussian elimination with partial pivoting)
// Used as a fallback for n < 2000 to guarantee robustness during debugging
// and for small device prototypes.
class DenseDirectSolver {
public:
    // Convert CSR to dense, factorize, and solve A*x = b
    static Vector solve(const SparseMatrix& A, const Vector& b);

    static bool is_small_enough(size_t n) { return n <= 2000; }

private:
    static void lu_factorize(std::vector<real_t>& M, size_t n, std::vector<size_t>& pivot);
    static void lu_solve(const std::vector<real_t>& M, size_t n,
                         const std::vector<size_t>& pivot,
                         const Vector& b, Vector& x);
};

} // namespace tcad
