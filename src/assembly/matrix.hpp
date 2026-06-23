// matrix.hpp — 稀疏矩阵(CSR)与密向量
//
// MNA 装配用。支持：
//   - 预声明非零模式后批量累加（装配阶段反复 A(i,j)+=<贡献>）
//   - CSR 存储供求解器
//   - 清零保留模式（Newton 迭代每步重置值）
//
// 实现策略：构建期用"坐标累加表"(map<(i,j),val>)，finalize() 转 CSR。
// 对 DC 工作点的小规模电路足够；大规模电路(§4.4 HB)将用块稀疏(BSR)另实现。
#ifndef RFSIM_ASSEMBLY_MATRIX_HPP
#define RFSIM_ASSEMBLY_MATRIX_HPP

#include <cstdint>
#include <cstdio>
#include <map>
#include <string>
#include <vector>

namespace rfsim {

// 密向量
using Vector = std::vector<double>;

// 稀疏方阵：构建期用 map 累加，finalize 后转 CSR 供求解。
class SparseMatrix {
public:
    explicit SparseMatrix(uint32_t n = 0) : n_(n) {}

    void resize(uint32_t n) { n_ = n; pattern_.clear(); data_.clear(); finalized_ = false; }

    [[nodiscard]] uint32_t dim() const noexcept { return n_; }

    // 声明非零模式 (i,j)（重复声明幂等）
    void addPattern(uint32_t i, uint32_t j) {
        if (patternCommitted_) return;  // 已固化：pattern 不变，忽略
        ensureFinalizedFalse();
        pattern_[key(i, j)];  // 插入默认 0
    }

    // 累加: A(i,j) += v（需先 addPattern 或直接用 set 允许隐式创建）
    void add(uint32_t i, uint32_t j, double v) {
        if (patternCommitted_) { addCommitted(i, j, v); return; }
        ensureFinalizedFalse();
        data_[key(i, j)] += v;
    }

    // 设置: A(i,j) = v
    void set(uint32_t i, uint32_t j, double v) {
        ensureFinalizedFalse();
        data_[key(i, j)] = v;
    }

    // 读取（仅 finalize 前从 data_ 读，finalize 后从 csr 读）
    [[nodiscard]] double get(uint32_t i, uint32_t j) const;

    // 把所有非零清零，保留模式（用于 Newton 迭代重装配）
    void zeroValues();

    // 转为 CSR（求解前调用）。之后不可再 add/set。
    void finalize();

    [[nodiscard]] bool finalized() const noexcept { return finalized_; }

    // V3-L0: pattern 固化模式。
    void commitPattern() {
        // M4: commit 前必须 finalize
        if (!finalized_) return;  // 静默跳过（调用方应保证顺序）
        patternCommitted_ = true;
        data_.clear();  // H10: 清 data_ 避免残留
    }
    [[nodiscard]] bool patternCommitted() const noexcept { return patternCommitted_; }
    // V3-L0: pattern 固化后返回 (i,j) 在 values_ 中的指针。
    // M5: 返回的指针在 values_ vector 不被 resize/finalize 重建时有效。
    // 调用方（bindStampPtrs）必须在 finalize+commit 后调用，且之后不再 resize。
    // boundG_ 检查（DeviceModel）提供跨 G 对象的额外保护。
    [[nodiscard]] double* ptrFor(uint32_t i, uint32_t j);
    void zeroCommitted() {
        if (patternCommitted_) {
            std::fill(values_.begin(), values_.end(), 0.0);
        }
    }
    // 固化后直接累加到 CSR（row scan 找 col）
    void addCommitted(uint32_t i, uint32_t j, double v) {
        if (!patternCommitted_ || i >= n_) return;
        for (uint32_t k = rowPtr_[i]; k < rowPtr_[i + 1]; ++k) {
            if (colIdx_[k] == j) { values_[k] += v; return; }
        }
    }

    // CSR 访问（finalize 后）
    [[nodiscard]] const std::vector<uint32_t>& rowPtr() const { return rowPtr_; }
    [[nodiscard]] const std::vector<uint32_t>& colIdx() const { return colIdx_; }
    [[nodiscard]] const std::vector<double>&   values() const { return values_; }

private:
    uint32_t n_ = 0;
    bool finalized_ = false;
    bool patternCommitted_ = false;
    // 构建期：用 (i*n+j) 作为 key
    std::map<uint64_t, double> pattern_;  // 声明的非零模式（含零值占位）
    std::map<uint64_t, double> data_;     // 实际值（finalize 前用）
    // finalize 后：CSR
    std::vector<uint32_t> rowPtr_;
    std::vector<uint32_t> colIdx_;
    std::vector<double>   values_;

    uint64_t key(uint32_t i, uint32_t j) const {
        return (uint64_t(i) << 32) | uint64_t(j);
    }
    void ensureFinalizedFalse() {
        if (finalized_) finalized_ = false;  // 修改自动转回构建态
    }
};

// 矩阵-向量乘: y = A*x（finalize 后用 CSR；否则用 data_）
void matVec(const SparseMatrix& A, const Vector& x, Vector& y);

// 打印（调试用）
std::string formatMatrix(const SparseMatrix& A);

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_MATRIX_HPP
