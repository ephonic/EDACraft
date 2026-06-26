#pragma once

#include "math_types.h"
#include <vector>
#include <map>
#include <stdexcept>

namespace tcad {

// Simple CSR sparse matrix for 128-bit real_t
// Suitable for moderate-scale 3D device simulation (up to ~1M unknowns)
class SparseMatrix {
public:
    SparseMatrix() = default;
    explicit SparseMatrix(size_t n) : n_(n), row_ptr_(n + 1, 0) {}
    SparseMatrix(const SparseMatrix& other)
        : n_(other.n_), vals_(other.vals_), cols_(other.cols_),
          row_ptr_(other.row_ptr_), finalized_(other.finalized_) {}

    // Build from triplet list (row, col, val)
    void add_entry(size_t i, size_t j, real_t val);
    void finalize();

    // Matrix-vector product: y = A * x
    void matvec(const real_t* x, real_t* y) const;
    // y = A * x (allocate interface)
    std::vector<real_t> apply(const std::vector<real_t>& x) const;

    size_t rows() const { return n_; }
    size_t num_cols() const { return n_; }
    size_t nnz() const { return vals_.size(); }

    // Direct access for solvers
    const std::vector<real_t>& vals() const { return vals_; }
    const std::vector<size_t>& col_indices() const { return cols_; }
    const std::vector<size_t>& row_offsets() const { return row_ptr_; }

    std::vector<real_t>& vals_mut() { return vals_; }

private:
    size_t n_ = 0;
    std::vector<real_t> vals_;
    std::vector<size_t> cols_;
    std::vector<size_t> row_ptr_;
    bool finalized_ = false;
    std::vector<std::map<size_t, real_t>> temp_entries_;
};

// Dense vector utilities
using Vector = std::vector<real_t>;

Vector operator+(const Vector& a, const Vector& b);
Vector operator-(const Vector& a, const Vector& b);
Vector operator*(real_t s, const Vector& v);
real_t dot(const Vector& a, const Vector& b);
real_t norm_l2(const Vector& v);

} // namespace tcad
