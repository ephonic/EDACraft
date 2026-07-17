// sparse_cmpl_matrix.hpp — 复数稀疏矩阵（CSR + pattern固化）
//
// 用于 AC 分析：复数导纳矩阵 G+jωC 的稀疏存储 + KLU 求解。
// 复数存储格式：values_ 按 KLU 的实虚对拆分（Ax[2*k]=Re, Ax[2*k+1]=Im）。
//
// pattern 固化（方案3）：
//   首次 buildPattern + finalize → commitPattern
//   后续每频率点 zeroValues + 只更新 C/L 的 jωC entry
//   R 导纳预计算（方案4）：R 的导纳不随频率变，首次 stamp 后跨频率复用
#ifndef RFSIM_ASSEMBLY_SPARSE_CMPL_MATRIX_HPP
#define RFSIM_ASSEMBLY_SPARSE_CMPL_MATRIX_HPP

#include <complex>
#include <cstdint>
#include <map>
#include <vector>

namespace rfsim {

using Complex = std::complex<double>;

class SparseCmplxMatrix {
public:
    SparseCmplxMatrix() = default;

    void resize(uint32_t n) {
        n_ = n;
        pattern_.clear();
        data_.clear();      // build 期 map (key→Complex)
        finalized_ = false;
        patternCommitted_ = false;
        rowPtr_.clear();
        colIdx_.clear();
        values_.clear();     // CSR: 2*nnz (Re,Im pairs)
        // 预存值（R 导纳，跨频率不变）
        staticValues_.clear();
    }

    void addPattern(uint32_t i, uint32_t j) {
        if (patternCommitted_) return;
        pattern_[key(i, j)];
    }

    // 构建期累加（map）
    void add(uint32_t i, uint32_t j, const Complex& v) {
        if (patternCommitted_) { addCommitted(i, j, v); return; }
        data_[key(i, j)] += v;
    }

    // 预存静态值（R 导纳，不随频率变）—— 方案4
    void addStatic(uint32_t i, uint32_t j, const Complex& v) {
        addPattern(i, j);
        staticValues_[key(i, j)] += v;
    }

    void finalize() {
        if (finalized_) return;
        std::map<uint64_t, Complex> merged = pattern_;
        for (const auto& [k, v] : data_) merged[k] += v;
        for (const auto& [k, v] : staticValues_) merged[k] += v;

        // 建 CSR
        std::vector<uint32_t> counts(n_ + 1, 0);
        for (const auto& [k, v] : merged) {
            uint32_t i = k >> 32;
            counts[i + 1]++;
        }
        for (uint32_t i = 0; i < n_; ++i) counts[i + 1] += counts[i];
        rowPtr_ = std::vector<int>(counts.begin(), counts.end());
        size_t nnz = merged.size();
        colIdx_.resize(nnz);
        values_.resize(2 * nnz);  // Re,Im pairs
        std::vector<uint32_t> cursor(n_, 0);
        for (const auto& [k, v] : merged) {
            uint32_t i = k >> 32;
            uint32_t j = k & 0xFFFFFFFF;
            int idx = rowPtr_[i] + cursor[i]++;
            colIdx_[idx] = static_cast<int>(j);
            values_[2 * idx] = v.real();
            values_[2 * idx + 1] = v.imag();
        }
        finalized_ = true;
    }

    void commitPattern() {
        if (!finalized_) return;
        patternCommitted_ = true;
        data_.clear();
    }

    // 清零 values 但保留 staticValues（R 导纳）
    void zeroValues() {
        // 保留 staticValues（R），清动态值（C/L）
        if (!patternCommitted_ || colIdx_.empty()) return;
        // 重建 values：先清零，再加回 staticValues
        std::fill(values_.begin(), values_.end(), 0.0);
        // 把 staticValues 重新写入 CSR
        for (const auto& [k, v] : staticValues_) {
            uint32_t i = k >> 32;
            uint32_t j = k & 0xFFFFFFFF;
            for (int idx = rowPtr_[i]; idx < rowPtr_[i + 1]; ++idx) {
                if (colIdx_[idx] == static_cast<int>(j)) {
                    values_[2 * idx] += v.real();
                    values_[2 * idx + 1] += v.imag();
                    break;
                }
            }
        }
    }

    void addCommitted(uint32_t i, uint32_t j, const Complex& v) {
        if (!patternCommitted_ || i >= n_) return;
        for (int idx = rowPtr_[i]; idx < rowPtr_[i + 1]; ++idx) {
            if (colIdx_[idx] == static_cast<int>(j)) {
                values_[2 * idx] += v.real();
                values_[2 * idx + 1] += v.imag();
                return;
            }
        }
    }

    [[nodiscard]] bool finalized() const noexcept { return finalized_; }
    [[nodiscard]] bool patternCommitted() const noexcept { return patternCommitted_; }
    [[nodiscard]] uint32_t dim() const noexcept { return n_; }
    [[nodiscard]] const int* rowPtr() const { return rowPtr_.data(); }
    [[nodiscard]] const int* colIdx() const { return colIdx_.data(); }
    [[nodiscard]] const double* values() const { return values_.data(); }
    [[nodiscard]] size_t nnz() const { return colIdx_.size(); }

private:
    static uint64_t key(uint32_t i, uint32_t j) {
        return (uint64_t(i) << 32) | uint64_t(j);
    }

    uint32_t n_ = 0;
    bool finalized_ = false;
    bool patternCommitted_ = false;
    std::map<uint64_t, Complex> pattern_;
    std::map<uint64_t, Complex> data_;
    std::map<uint64_t, Complex> staticValues_;  // 方案4: R 导纳（跨频率不变）
    std::vector<int> rowPtr_;
    std::vector<int> colIdx_;
    std::vector<double> values_;  // 2*nnz (Re,Im pairs for KLU)
};

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_SPARSE_CMPL_MATRIX_HPP
