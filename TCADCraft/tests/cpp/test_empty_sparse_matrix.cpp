// An unpopulated matrix is a legal zero operator, including zero rows.
#include "sparse_matrix.h"
#include <iostream>
int main() {
    using namespace tcad;
    for (size_t n : {size_t(0), size_t(1), size_t(9)}) {
        SparseMatrix matrix(n);
        matrix.finalize(); matrix.finalize();
        if (matrix.row_offsets() != std::vector<size_t>(n + 1, 0) ||
            !matrix.vals().empty() || !matrix.col_indices().empty()) return 1;
        if (matrix.apply(Vector(n, TCAD_CONST(3.0))) != Vector(n, TCAD_CONST(0.0))) return 1;
        if (n) {
            bool rejected=false;
            try { matrix.add_entry(0, 0, TCAD_CONST(1.0)); }
            catch (const std::runtime_error&) { rejected=true; }
            if (!rejected) return 1;
        }
    }
    std::cout << "empty sparse matrices: zero, one and nine rows passed\n";
}
