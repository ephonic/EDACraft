// klu_z_solver.cpp — 复数版 KLU 稀疏求解器实现
#include "klu_z_solver.hpp"
#include <klu.h>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <utility>

namespace rfsim {

namespace {
inline klu_symbolic* sym(void* p) { return static_cast<klu_symbolic*>(p); }
inline klu_numeric*  num(void* p) { return static_cast<klu_numeric*>(p); }
inline klu_common*   cmn(void* p) { return static_cast<klu_common*>(p); }
}

KluZSolver::KluZSolver() {
    auto* c = new klu_common;
    klu_defaults(c);
    common_ = c;
}

KluZSolver::~KluZSolver() {
    freeFactors();
    delete cmn(common_);
}

void KluZSolver::freeFactors() noexcept {
    if (num_) {
        klu_numeric* p = num(num_);
        klu_z_free_numeric(&p, cmn(common_));
        num_ = nullptr;
    }
    if (sym_) {
        klu_symbolic* p = sym(sym_);
        klu_free_symbolic(&p, cmn(common_));
        sym_ = nullptr;
    }
    analyzed_ = false;
}

KluZSolver::KluZSolver(KluZSolver&& o) noexcept {
    n_ = o.n_;
    sym_ = o.sym_; o.sym_ = nullptr;
    num_ = o.num_; o.num_ = nullptr;
    common_ = o.common_; o.common_ = nullptr;
    analyzed_ = o.analyzed_;
    factorMs_ = o.factorMs_; o.factorMs_ = 0.0;
    solveMs_ = o.solveMs_; o.solveMs_ = 0.0;
}

KluZSolver& KluZSolver::operator=(KluZSolver&& o) noexcept {
    if (this != &o) {
        freeFactors();
        delete cmn(common_);
        n_ = o.n_;
        sym_ = o.sym_; o.sym_ = nullptr;
        num_ = o.num_; o.num_ = nullptr;
        common_ = o.common_; o.common_ = nullptr;
        analyzed_ = o.analyzed_;
        factorMs_ = o.factorMs_; o.factorMs_ = 0.0;
        solveMs_ = o.solveMs_; o.solveMs_ = 0.0;
    }
    return *this;
}

bool KluZSolver::factorize(int n, const int* Ap, const int* Ai, const double* Ax) {
    SteadyTimer tFact;
    n_ = n;

    // CSR→CSC 转置（KLU 需要 CSC 格式）
    // Ax 是实虚对：Ax[2*k]=Re, Ax[2*k+1]=Im
    int nnz = Ap[n];
    cscAp_.assign(n + 1, 0);
    cscAi_.assign(nnz, 0);
    cscAx_.assign(2 * nnz, 0.0);

    // 计算每列非零数
    for (int k = 0; k < nnz; ++k) cscAp_[Ai[k] + 1]++;
    for (int i = 0; i < n; ++i) cscAp_[i + 1] += cscAp_[i];
    // 散射
    std::vector<int> cursor(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int k = Ap[i]; k < Ap[i + 1]; ++k) {
            int j = Ai[k];
            int dst = cscAp_[j] + cursor[j]++;
            cscAi_[dst] = i;
            cscAx_[2 * dst]     = Ax[2 * k];      // Re
            cscAx_[2 * dst + 1] = Ax[2 * k + 1];  // Im
        }
    }

    // Symbolic factorization（仅首次）
    if (!analyzed_) {
        if (sym_) {
            klu_symbolic* p = sym(sym_);
            klu_free_symbolic(&p, cmn(common_));
            sym_ = nullptr;
        }
        sym_ = klu_analyze(n, cscAp_.data(), cscAi_.data(), cmn(common_));
        if (!sym_) {
            if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
            return false;
        }
        analyzed_ = true;
    }

    // Numeric factorization
    if (num_) {
        klu_numeric* p = num(num_);
        klu_z_free_numeric(&p, cmn(common_));
        num_ = nullptr;
    }
    num_ = klu_z_factor(cscAp_.data(), cscAi_.data(), cscAx_.data(),
                        sym(sym_), cmn(common_));
    if (!num_ || cmn(common_)->status != KLU_OK) {
        if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
        return false;
    }

    if (benchJsonEnabled()) factorMs_ += tFact.elapsedMs();
    return true;
}

void KluZSolver::solve(double* B) const {
    assert(num_ != nullptr && "KluZSolver::solve called before factorize");
    SteadyTimer tSolve;
    klu_z_solve(sym(sym_), num(num_), n_, 1, B, cmn(common_));
    if (benchJsonEnabled()) solveMs_ += tSolve.elapsedMs();
}

} // namespace rfsim
