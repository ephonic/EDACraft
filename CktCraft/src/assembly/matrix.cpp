// matrix.cpp — 稀疏矩阵实现
#include "matrix.hpp"

#include <cmath>
#include <sstream>

namespace rfsim {

double SparseMatrix::get(uint32_t i, uint32_t j) const {
    if (finalized_) {
        // CSR 查找
        for (uint32_t k = rowPtr_[i]; k < rowPtr_[i + 1]; ++k) {
            if (colIdx_[k] == j) return values_[k];
        }
        return 0.0;
    }
    auto it = data_.find(key(i, j));
    return it != data_.end() ? it->second : 0.0;
}

// V3-L0: pattern 固化后返回 (i,j) 在 values_ 中的指针。
// 仅在 bindStampPtrs 阶段调用（每器件每 entry 一次）。
// 若 (i,j) 不在 pattern 中，返回 nullptr（器件应跳过）。
double* SparseMatrix::ptrFor(uint32_t i, uint32_t j) {
    if (!patternCommitted_ || i >= n_) return nullptr;
    for (uint32_t k = rowPtr_[i]; k < rowPtr_[i + 1]; ++k) {
        if (colIdx_[k] == j) return &values_[k];
    }
    return nullptr;
}

void SparseMatrix::zeroValues() {
    if (finalized_) {
        // 已 finalize：把 CSR 值清零，保留结构
        std::fill(values_.begin(), values_.end(), 0.0);
        finalized_ = true;
        return;
    }
    // 构建期：保留 pattern 的 key，值清零
    data_.clear();
    for (const auto& [k, v] : pattern_) {
        (void)v;
        data_[k] = 0.0;
    }
}

void SparseMatrix::finalize() {
    if (finalized_) return;
    // 收集所有非零位置：pattern_ ∪ data_ 的 key
    std::map<uint64_t, double> merged = pattern_;
    for (const auto& [k, v] : data_) merged[k] += v;  // pattern 内已有的累加

    // 按 (row, col) 排序建 CSR（std::map 已按 key=(i<<32|j) 升序，正好行优先）
    rowPtr_.assign(n_ + 1, 0);
    colIdx_.clear();
    values_.clear();
    colIdx_.reserve(merged.size());
    values_.reserve(merged.size());

    // 先统计每行非零数
    for (const auto& [k, v] : merged) {
        uint32_t i = uint32_t(k >> 32);
        if (i < n_) rowPtr_[i + 1]++;
        (void)v;
    }
    for (uint32_t i = 0; i < n_; ++i) rowPtr_[i + 1] += rowPtr_[i];
    // 填充（map 已按 key 排序，直接顺序填）
    for (const auto& [k, v] : merged) {
        uint32_t i = uint32_t(k >> 32);
        uint32_t j = uint32_t(k & 0xFFFFFFFFu);
        if (i < n_) {
            colIdx_.push_back(j);
            values_.push_back(v);
        }
    }
    finalized_ = true;
}

void matVec(const SparseMatrix& A, const Vector& x, Vector& y) {
    // 仅支持 finalize 后的 CSR
    uint32_t n = A.dim();
    y.assign(n, 0.0);
    if (!A.finalized()) {
        // 退化：构建期不支持 SpMV
        return;
    }
    const auto& rp = A.rowPtr();
    const auto& ci = A.colIdx();
    const auto& va = A.values();
    for (uint32_t i = 0; i < n; ++i) {
        double s = 0.0;
        for (uint32_t k = rp[i]; k < rp[i + 1]; ++k) {
            s += va[k] * x[ci[k]];
        }
        y[i] = s;
    }
}

std::string formatMatrix(const SparseMatrix& A) {
    std::ostringstream os;
    uint32_t n = A.dim();
    os << n << "x" << n << ":\n";
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            double v = A.get(i, j);
            if (std::fabs(v) < 1e-15) os << "   .   ";
            else {
                os.width(7);
                os.precision(3);
                os << v << " ";
            }
        }
        os << "\n";
    }
    return os.str();
}

} // namespace rfsim
