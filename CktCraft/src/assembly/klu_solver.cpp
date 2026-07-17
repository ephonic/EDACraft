// klu_solver.cpp — KluSolver 实现
//
// 工作流：
//   1) SparseMatrix（CSR, uint32_t）→ 本类的 CSC（int）。
//      CSC[i] = CSR[A^T][i]：对 CSR 而言，遍历 (i, j, v) 装到 col=j 的桶里即可。
//   2) klu_defaults() 一次性初始化 common（构造时做）。
//   3) 若 (n, nnz) 变化或首次：klu_analyze 重新做 symbolic（AMD/BTF）。
//      否则复用已有 sym_。
//   4) 旧 num_ 若存在先 free，再 klu_factor。
//   5) solve：拷贝 b → x，原位 klu_solve（KLU 是 in-place）。
//
// 备注：KLU 的 klu_solve 不会修改 numeric/symbolic，所以 solve() 标 const 是安全的。

#include "klu_solver.hpp"

#include <klu.h>

#include <cassert>
#include <cstring>
#include <stdexcept>
#include <utility>

namespace rfsim {

namespace {
// 把 .hpp 里的 void* 句柄转回真实 KLU 类型（仅 .cpp 内可见）。
inline klu_symbolic* sym(void* p)  { return static_cast<klu_symbolic*>(p); }
inline klu_numeric*  num(void* p)  { return static_cast<klu_numeric*>(p); }
inline klu_common*   cmn(void* p)  { return static_cast<klu_common*>(p); }
} // namespace

KluSolver::KluSolver() {
    auto* c = new klu_common;
    klu_defaults(c);
    common_ = c;
    // KLU 的默认配置已经满足电路 MNA 需求；如需调整可在此 set common 字段。
    // 例：c->btf = 1; c->ordering = 0(AMD)/1(COLAMD)/2(natural)。
}

KluSolver::~KluSolver() {
    freeFactors();
    delete cmn(common_);
    common_ = nullptr;
}

KluSolver::KluSolver(KluSolver&& o) noexcept {
    n_ = o.n_;
    Ap_ = std::move(o.Ap_);
    Ai_ = std::move(o.Ai_);
    Ax_ = std::move(o.Ax_);
    prevAp_ = std::move(o.prevAp_);
    prevAi_ = std::move(o.prevAi_);
    sym_ = o.sym_; o.sym_ = nullptr;
    num_ = o.num_; o.num_ = nullptr;
    common_ = o.common_; o.common_ = nullptr;
    factorMs_ = o.factorMs_; o.factorMs_ = 0.0;  // L1: 转移 bench 计时器
    solveMs_ = o.solveMs_; o.solveMs_ = 0.0;
    analyzed_ = o.analyzed_; o.analyzed_ = false;
}

KluSolver& KluSolver::operator=(KluSolver&& o) noexcept {
    if (this != &o) {
        freeFactors();
        delete cmn(common_);
        n_ = o.n_;
        Ap_ = std::move(o.Ap_);
        Ai_ = std::move(o.Ai_);
        Ax_ = std::move(o.Ax_);
        prevAp_ = std::move(o.prevAp_);
        prevAi_ = std::move(o.prevAi_);
        sym_ = o.sym_; o.sym_ = nullptr;
        num_ = o.num_; o.num_ = nullptr;
        common_ = o.common_; o.common_ = nullptr;
        factorMs_ = o.factorMs_; o.factorMs_ = 0.0;  // L1
        solveMs_ = o.solveMs_; o.solveMs_ = 0.0;
        analyzed_ = o.analyzed_; o.analyzed_ = false;
    }
    return *this;
}

void KluSolver::freeFactors() noexcept {
    if (num_ && common_) {
        klu_numeric* p = num(num_);
        klu_free_numeric(&p, cmn(common_));
    }
    num_ = nullptr;
    if (sym_ && common_) {
        klu_symbolic* p = sym(sym_);
        klu_free_symbolic(&p, cmn(common_));
    }
    sym_ = nullptr;
    analyzed_ = false;  // 方案2: 重置 symbolic 状态
    prevAp_.clear();
    prevAi_.clear();
}

bool KluSolver::factorize(const SparseMatrix& A) {
    SteadyTimer tFact;
    if (!A.finalized()) {
        // 调用方契约：必须 finalize 后传入。
        return false;
    }
    n_ = A.dim();
    if (n_ == 0) {
        freeFactors();
        return false;
    }

    const auto& rp = A.rowPtr();   // size n+1
    const auto& ci = A.colIdx();   // size nnz
    const auto& va = A.values();   // size nnz
    const size_t nnz = va.size();

    // ---- CSR → CSC 转置 ------------------------------------------------------
    // 第一遍：列计数 → Ap_ 累加和。
    Ap_.assign(static_cast<size_t>(n_) + 1, 0);
    for (size_t k = 0; k < nnz; ++k) {
        Ap_[ci[k] + 1]++;  // 注意 +1，方便后面 prefix sum
    }
    for (uint32_t j = 0; j < n_; ++j) {
        Ap_[j + 1] += Ap_[j];
    }
    // 第二遍：把每个 (i, j=ci[k], v=va[k]) 放到 col=j 的下一个空位。
    Ai_.assign(nnz, 0);
    Ax_.assign(nnz, 0.0);
    std::vector<int> cursor(n_, 0);
    for (uint32_t i = 0; i < n_; ++i) {
        for (uint32_t k = rp[i]; k < rp[i + 1]; ++k) {
            const uint32_t j = ci[k];
            const int dst = Ap_[j] + cursor[j]++;
            Ai_[static_cast<size_t>(dst)] = static_cast<int>(i);
            Ax_[static_cast<size_t>(dst)] = va[k];
        }
    }

    // ---- 符号因子化（方案2: pattern 不变时复用 symbolic）---
    // 结构指纹：判断新矩阵的稀疏模式是否与已分析的完全相同。
    // A1-4：把求解器提到 Newton 循环外后，连续 factorize 会在同结构（不同值）
    // 矩阵间调用——此时复用 sym_ 走 klu_refactor。但 klu_refactor 要求**完全相同**
    // 的稀疏模式（Ap_/Ai_）；若结构变了（哪怕 nnz 巧合相同），refactor 会在错误
    // 的数值因子内存布局上写值 → 堆腐败（实测 0xC0000374 on BSIM4 LcTank）。
    // 故必须做完整的 Ap_ + Ai_ 逐元素比较（O(nnz)，远低于 factor 的 O(nnz·fill)）。
    // prevAi_/prevAp_ 在首次 analyze 后保存，后续每次 factorize 比对。
    bool structureSame = analyzed_ && sym_ &&
                         prevAp_.size() == Ap_.size() &&
                         prevAi_.size() == Ai_.size();
    if (structureSame) {
        // Ap_ 已是 size n+1；Ai_ 已是 size nnz。逐元素 memcmp（int 数组）。
        if (std::memcmp(prevAp_.data(), Ap_.data(), Ap_.size() * sizeof(int)) != 0 ||
            std::memcmp(prevAi_.data(), Ai_.data(), Ai_.size() * sizeof(int)) != 0) {
            structureSame = false;
        }
    }
    if (!analyzed_ || !structureSame) {
        // 结构变化（或首次）：必须重新 analyze。注意 num_（数值因子）绑定在旧 sym_
        // 的内存布局上——若只 free sym_ 而保留 num_，后续 klu_factor/klu_refactor 会用
        // 不匹配的 sym_/num_ 组合 → 堆腐败（实测 BSIM-CMG dc_op 多 gmin 步崩溃 0xC0000374）。
        // 故结构变化时同时释放 num_ 与 sym_，强制下一节重新 klu_factor。
        if (num_) {
            klu_numeric* pn = num(num_);
            klu_free_numeric(&pn, cmn(common_));
            num_ = nullptr;
        }
        if (sym_) {
            klu_symbolic* p = sym(sym_);
            klu_free_symbolic(&p, cmn(common_));
            sym_ = nullptr;
        }
        sym_ = klu_analyze(static_cast<int>(n_), Ap_.data(), Ai_.data(), cmn(common_));
        if (!sym_) {
            if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
            return false;
        }
        analyzed_ = true;
        // 保存本次结构供下次比对
        prevAp_ = Ap_;
        prevAi_ = Ai_;
    }

    // ---- 数值因子化（方案2: 尝试 refactor，失败则 full factor）---
    if (num_) {
        // pattern 相同——尝试 klu_refactor（只做数值更新，省 symbolic）
        klu_numeric* p = num(num_);
        int ok = klu_refactor(Ap_.data(), Ai_.data(), Ax_.data(),
                              sym(sym_), p, cmn(common_));
        if (!ok || cmn(common_)->status != KLU_OK) {
            // refactor 失败——重新 factor
            klu_free_numeric(&p, cmn(common_));
            num_ = nullptr;
        }
    }
    if (!num_) {
        num_ = klu_factor(Ap_.data(), Ai_.data(), Ax_.data(), sym(sym_), cmn(common_));
        if (!num_ || cmn(common_)->status != KLU_OK) {
            if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
            return false;
        }
    }
    if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
    return true;
}

void KluSolver::solve(const Vector& b, Vector& x) const {
    assert(num_ != nullptr && "KluSolver::solve called before successful factorize()");
    assert(b.size() == n_ && "rhs dimension mismatch");
    SteadyTimer tSolve;
    x.assign(b.begin(), b.end());
    if (n_ == 0) return;
    // klu_solve 是原位求解，第 4 个参数 nrhs=1，第 5 个参数为 x（即 b）。
    klu_solve(sym(sym_), num(num_), static_cast<int>(n_), 1, x.data(), cmn(common_));
    if (benchJsonEnabled()) {
        solveMs_ += tSolve.elapsedMs();
    }
}

} // namespace rfsim
