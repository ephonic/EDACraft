// umfpack_solver.cpp — UMFPACK 求解器封装实现
//
// 详见 umfpack_solver.hpp。UMFPACK di（double, int32）接口。
// 工作流：CSR→CSC → umfpack_di_symbolic（首次或结构变）→ umfpack_di_numeric
// → umfpack_di_solve。连续同结构矩阵复用 Symbolic，只重算 Numeric。
#include "umfpack_solver.hpp"

#include <umfpack.h>

#include <algorithm>
#include <cstring>

namespace rfsim {

UmfpackSolver::UmfpackSolver() {
    umfpack_di_defaults(control_);
}

UmfpackSolver::~UmfpackSolver() {
    freeFactors();
}

UmfpackSolver::UmfpackSolver(UmfpackSolver&& o) noexcept {
    n_ = o.n_;
    Ap_ = std::move(o.Ap_);
    Ai_ = std::move(o.Ai_);
    Ax_ = std::move(o.Ax_);
    prevAp_ = std::move(o.prevAp_);
    prevAi_ = std::move(o.prevAi_);
    symbolic_ = o.symbolic_; o.symbolic_ = nullptr;
    numeric_ = o.numeric_; o.numeric_ = nullptr;
    std::memcpy(control_, o.control_, sizeof(control_));
    analyzed_ = o.analyzed_; o.analyzed_ = false;
}

UmfpackSolver& UmfpackSolver::operator=(UmfpackSolver&& o) noexcept {
    if (this != &o) {
        freeFactors();
        n_ = o.n_;
        Ap_ = std::move(o.Ap_);
        Ai_ = std::move(o.Ai_);
        Ax_ = std::move(o.Ax_);
        prevAp_ = std::move(o.prevAp_);
        prevAi_ = std::move(o.prevAi_);
        symbolic_ = o.symbolic_; o.symbolic_ = nullptr;
        numeric_ = o.numeric_; o.numeric_ = nullptr;
        std::memcpy(control_, o.control_, sizeof(control_));
        analyzed_ = o.analyzed_; o.analyzed_ = false;
    }
    return *this;
}

void UmfpackSolver::freeFactors() noexcept {
    if (numeric_) {
        void* p = numeric_;
        umfpack_di_free_numeric(&p);
        numeric_ = nullptr;
    }
    if (symbolic_) {
        void* p = symbolic_;
        umfpack_di_free_symbolic(&p);
        symbolic_ = nullptr;
    }
    analyzed_ = false;
    prevAp_.clear();
    prevAi_.clear();
}

bool UmfpackSolver::factorize(const SparseMatrix& A) {
    if (!A.finalized()) return false;
    n_ = A.dim();
    if (n_ == 0) { freeFactors(); return false; }

    const auto& rp = A.rowPtr();
    const auto& ci = A.colIdx();
    const auto& va = A.values();
    const size_t nnz = va.size();

    // ---- CSR → CSC 转置（UMFPACK 输入 CSC：Ap 列指针，Ai 行索引）----
    Ap_.assign(static_cast<size_t>(n_) + 1, 0);
    for (size_t k = 0; k < nnz; ++k) Ap_[ci[k] + 1]++;
    for (uint32_t j = 0; j < n_; ++j) Ap_[j + 1] += Ap_[j];
    Ai_.assign(nnz, 0);
    Ax_.assign(nnz, 0.0);
    std::vector<int32_t> cursor(n_, 0);
    for (uint32_t i = 0; i < n_; ++i) {
        for (uint32_t k = rp[i]; k < rp[i + 1]; ++k) {
            const uint32_t j = ci[k];
            const int32_t dst = Ap_[j] + cursor[j]++;
            Ai_[dst] = static_cast<int32_t>(i);
            Ax_[dst] = va[k];
        }
    }

    // ---- 结构指纹：判断是否可复用 Symbolic ----
    bool structureSame = analyzed_ && symbolic_ &&
                         prevAp_.size() == Ap_.size() &&
                         prevAi_.size() == Ai_.size();
    if (structureSame) {
        if (std::memcmp(prevAp_.data(), Ap_.data(), Ap_.size() * sizeof(int32_t)) != 0 ||
            std::memcmp(prevAi_.data(), Ai_.data(), Ai_.size() * sizeof(int32_t)) != 0) {
            structureSame = false;
        }
    }
    if (!analyzed_ || !structureSame) {
        // 结构变化或首次：释放 Symbolic + Numeric，重新 symbolic
        if (numeric_) { void* p = numeric_; umfpack_di_free_numeric(&p); numeric_ = nullptr; }
        if (symbolic_) { void* p = symbolic_; umfpack_di_free_symbolic(&p); symbolic_ = nullptr; }
        int status = umfpack_di_symbolic(static_cast<int32_t>(n_), static_cast<int32_t>(n_),
                                         Ap_.data(), Ai_.data(), Ax_.data(),
                                         &symbolic_, control_, nullptr);
        if (status != UMFPACK_OK) { symbolic_ = nullptr; return false; }
        analyzed_ = true;
        prevAp_ = Ap_;
        prevAi_ = Ai_;
    }

    // ---- 数值因子化（每次都重算 Numeric；UMFPACK 的 numeric 不支持纯 refactor，
    //   但 symbolic 复用已省下排序开销）----
    if (numeric_) { void* p = numeric_; umfpack_di_free_numeric(&p); numeric_ = nullptr; }
    int status = umfpack_di_numeric(Ap_.data(), Ai_.data(), Ax_.data(),
                                    symbolic_, &numeric_, control_, nullptr);
    if (status != UMFPACK_OK) { numeric_ = nullptr; return false; }
    return true;
}

void UmfpackSolver::solve(const Vector& b, Vector& x) const {
    // UMFPACK solve：x = A\b（sys = UMFPACK_A = 0）
    if (!numeric_ || n_ == 0) { x.assign(b.size(), 0.0); return; }
    x.assign(b.size(), 0.0);
    if (b.size() != n_) return;
    // UMFPACK 的 solve 不修改 Numeric；control 可用默认
    double info[90];
    umfpack_di_solve(UMFPACK_A, Ap_.data(), Ai_.data(), Ax_.data(),
                     x.data(), const_cast<double*>(b.data()),
                     numeric_, const_cast<double*>(control_), info);
}

} // namespace rfsim
