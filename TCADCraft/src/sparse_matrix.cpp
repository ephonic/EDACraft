#include "sparse_matrix.h"
#include <algorithm>
#include <cassert>

namespace tcad {

void SparseMatrix::add_entry(size_t i, size_t j, real_t val) {
    if (finalized_) throw std::runtime_error("Matrix already finalized");
    if (i >= n_ || j >= n_) throw std::out_of_range("Index out of bounds");
    if (temp_entries_.empty()) temp_entries_.resize(n_);
    temp_entries_[i][j] += val;
}

void SparseMatrix::finalize() {
    if (finalized_) return;
    row_ptr_.assign(n_ + 1, 0);
    size_t nnz = 0;
    for (size_t i = 0; i < n_; ++i) {
        row_ptr_[i] = nnz;
        nnz += temp_entries_[i].size();
    }
    row_ptr_[n_] = nnz;
    vals_.reserve(nnz);
    cols_.reserve(nnz);
    for (size_t i = 0; i < n_; ++i) {
        for (const auto& [j, v] : temp_entries_[i]) {
            cols_.push_back(j);
            vals_.push_back(v);
        }
    }
    temp_entries_.clear();
    temp_entries_.shrink_to_fit();
    finalized_ = true;
}

void SparseMatrix::matvec(const real_t* x, real_t* y) const {
    assert(finalized_);
    for (size_t i = 0; i < n_; ++i) {
        real_t sum = 0.0Q;
        for (size_t idx = row_ptr_[i]; idx < row_ptr_[i + 1]; ++idx) {
            sum += vals_[idx] * x[cols_[idx]];
        }
        y[i] = sum;
    }
}

std::vector<real_t> SparseMatrix::apply(const std::vector<real_t>& x) const {
    assert(x.size() == n_);
    std::vector<real_t> y(n_, 0.0Q);
    matvec(x.data(), y.data());
    return y;
}

Vector operator+(const Vector& a, const Vector& b) {
    Vector c(a.size());
    for (size_t i = 0; i < a.size(); ++i) c[i] = a[i] + b[i];
    return c;
}

Vector operator-(const Vector& a, const Vector& b) {
    Vector c(a.size());
    for (size_t i = 0; i < a.size(); ++i) c[i] = a[i] - b[i];
    return c;
}

Vector operator*(real_t s, const Vector& v) {
    Vector r(v.size());
    for (size_t i = 0; i < v.size(); ++i) r[i] = s * v[i];
    return r;
}

real_t dot(const Vector& a, const Vector& b) {
    real_t s = 0.0Q;
    for (size_t i = 0; i < a.size(); ++i) s += a[i] * b[i];
    return s;
}

real_t norm_l2(const Vector& v) {
    return sqrt_q(dot(v, v));
}

} // namespace tcad
