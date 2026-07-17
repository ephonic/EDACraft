// iterative_solver.cpp — BiCGSTAB + ILU(0) 迭代线性求解器实现
//
// Phase A1-6。ILU(0) 保留 A 的稀疏模式做 incomplete LU（dropping=0）；
// BiCGSTAB 做 Krylov 迭代。详见 iterative_solver.hpp。
#include "iterative_solver.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace rfsim {

namespace {

inline double dot(const double* a, const double* b, size_t n) {
    double s = 0.0;
    for (size_t i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

inline double norm2(const double* a, size_t n) {
    return std::sqrt(dot(a, a, n));
}

} // namespace

BiCgStabSolver::BiCgStabSolver() = default;

bool BiCgStabSolver::factorize(const SparseMatrix& A) {
    n_ = A.dim();
    if (n_ == 0) return true;
    // 复制 CSR
    rowPtr_ = A.rowPtr();
    colIdx_ = A.colIdx();
    vals_   = A.values();
    if (rowPtr_.size() != size_t(n_) + 1) return false;
    const size_t nnz = vals_.size();

    // ---- ILU(0)：保留原稀疏模式的 incomplete LU ----
    // 标准算法（按行 i）：
    //   for each (i,j) with j < i:  a_ij -= sum_{k<j, k>i 行已有, (i,k),(k,j) 都在模式} a_ik*a_kj
    //                                ; 若对角 a_kk==0 -> 失败
    //   对角: a_ii -= sum_{k<i, (i,k),(k,i) 模式} a_ik*a_ki
    //   off-diag (j>i): 同 j<i
    // 实现：需要快速查找 (i,j) 在 CSR 中的位置。用每行 colIdx 的 hash map 会复杂；
    // 这里用 "对每行 colIdx 排序假设 + 二分" —— rfsim 的 SparseMatrix finalize 时
    // colIdx 是否按列序排列需确认；保险起见这里建一个查找表 pos[i*n+j] 对稀疏不现实，
    // 改用：对每行预先排序 (col,val) 索引，后续二分查找。
    ilu_.assign(nnz, 0.0);
    // 先把 vals_ 复制进 ilu_（在 ilu_ 上做原地 incomplete 消去）
    std::copy(vals_.begin(), vals_.end(), ilu_.begin());

    // 为快速查找 (row, col) 在 ilu_ 中的下标，建每行有序列副本。
    // colIdx_ 在 finalize 后通常按列递增（CSR 惯例）；若不保证，这里排序一份。
    // 为稳健，构造每行的 (col→pos) 查找：用排序后的索引数组。
    // perRowPos_[i][k] = 排序后第 k 个非零在原 ilu_ 中的下标。
    std::vector<std::vector<uint32_t>> order(n_);  // 每行排序后的 colIdx 引用（存原 ilu_ 下标）
    for (uint32_t i = 0; i < n_; ++i) {
        uint32_t s = rowPtr_[i], e = rowPtr_[i + 1];
        order[i].resize(e - s);
        for (uint32_t k = s; k < e; ++k) order[i][k - s] = k;
        std::sort(order[i].begin(), order[i].end(),
                  [&](uint32_t a, uint32_t b) { return colIdx_[a] < colIdx_[b]; });
    }
    auto findPos = [&](uint32_t row, uint32_t col) -> int32_t {
        // 在 order[row] 中二分找 col，返回在 ilu_ 的下标；-1 表示不在模式内。
        const auto& ord = order[row];
        uint32_t lo = 0, hi = static_cast<uint32_t>(ord.size());
        while (lo < hi) {
            uint32_t mid = lo + (hi - lo) / 2;
            if (colIdx_[ord[mid]] < col) lo = mid + 1;
            else hi = mid;
        }
        if (lo < ord.size() && colIdx_[ord[lo]] == col) return static_cast<int32_t>(ord[lo]);
        return -1;
    };
    // 每行对角位置
    std::vector<int32_t> diagPos(n_, -1);
    for (uint32_t i = 0; i < n_; ++i) diagPos[i] = findPos(i, i);

    // 按行做 incomplete 消去
    for (uint32_t i = 0; i < n_; ++i) {
        uint32_t s = rowPtr_[i], e = rowPtr_[i + 1];
        for (uint32_t jj = s; jj < e; ++jj) {
            uint32_t j = colIdx_[jj];
            if (j >= i) break;  // 只处理下三角与对角（按行序，j<i）
            double aij = ilu_[jj];
            // aij /= a_{j,j}  (U 对角，已在前面行更新)
            int32_t jp = diagPos[j];
            if (jp < 0 || ilu_[jp] == 0.0) {
                // 主元为零：ILU(0) 失败
                return false;
            }
            ilu_[jj] = aij / ilu_[jp];
            double lij = ilu_[jj];
            // 更新行 i 中列 > j 的元素：a_{i,k} -= l_{i,j} * a_{j,k}，要求 (i,k) 与 (j,k) 都在模式
            uint32_t sj = rowPtr_[j], ej = rowPtr_[j + 1];
            for (uint32_t kk = sj; kk < ej; ++kk) {
                uint32_t kc = colIdx_[kk];
                if (kc <= j) continue;  // 只更新 k>j
                int32_t ipos = findPos(i, kc);
                if (ipos < 0) continue;  // (i,k) 不在模式 → drop（ILU(0)）
                ilu_[ipos] -= lij * ilu_[kk];
            }
        }
        // 行 i 的对角已由上面 k>j 的更新覆盖（a_{i,i} -= l_{i,j}*u_{j,i}）；
        // 无需额外处理。若对角最终为零则下次消去会失败。
    }
    // 检查所有对角非零
    for (uint32_t i = 0; i < n_; ++i) {
        if (diagPos[i] < 0 || ilu_[diagPos[i]] == 0.0) return false;
    }
    // 保存 diagPos 供 applyIlu 用
    diagPos_ = std::move(diagPos);
    return true;
}

void BiCgStabSolver::applyIlu(const Vector& r, Vector& z) const {
    // 解 (L+U) z = r，其中 L 单位下三角（对角 1）、U 上三角（含对角）。
    // L、U 同存于 ilu_，按 CSR 行序：每行 j<diag 的元素属 L（单位对角），j>diag 属 U。
    // 前代 L y = r（对角为 1）：
    z.assign(n_, 0.0);
    for (uint32_t i = 0; i < n_; ++i) {
        double s = r[i];
        uint32_t k = rowPtr_[i];
        int32_t dp = diagPos_[i];
        // 扫描到对角前（j<i）的下三角元素
        for (; k < rowPtr_[i + 1]; ++k) {
            if (static_cast<int32_t>(k) == dp) break;
            s -= ilu_[k] * z[colIdx_[k]];
        }
        z[i] = s;  // L 对角 = 1
    }
    // 回代 U z = y：
    for (int32_t ii = static_cast<int32_t>(n_) - 1; ii >= 0; --ii) {
        uint32_t i = static_cast<uint32_t>(ii);
        double s = z[i];
        int32_t dp = diagPos_[i];
        for (int32_t k = rowPtr_[i + 1] - 1; k > dp; --k) {
            s -= ilu_[k] * z[colIdx_[k]];
        }
        z[i] = s / ilu_[dp];
    }
}

void BiCgStabSolver::solve(const Vector& b, Vector& x) const {
    lastConv_ = false;
    lastIter_ = 0;
    lastRes_ = 0.0;
    const uint32_t n = n_;
    if (n == 0) return;
    if (x.size() != n) x.assign(n, 0.0);

    // SpMV: y = A x
    auto spmv = [&](const Vector& v, Vector& y) {
        for (uint32_t i = 0; i < n; ++i) {
            double s = 0.0;
            for (uint32_t k = rowPtr_[i]; k < rowPtr_[i + 1]; ++k) {
                s += vals_[k] * v[colIdx_[k]];
            }
            y[i] = s;
        }
    };

    Vector r(n), rhat(n), p(n), v(n), s(n), t(n), ph(n), sh(n);
    // r0 = b - A x（x 初值通常 0 → r0 = b）
    spmv(x, r);
    for (uint32_t i = 0; i < n; ++i) r[i] = b[i] - r[i];
    rhat = r;  // r̂ = r0（shadow），不能与 r 正交

    double bnorm = norm2(b.data(), n);
    double tol = reltol_ * bnorm + abstol_;
    if (bnorm == 0.0) { std::fill(x.begin(), x.end(), 0.0); lastConv_ = true; return; }

    double rhoOld = 1.0, alpha = 1.0, omega = 1.0;
    std::fill(v.begin(), v.end(), 0.0);
    std::fill(p.begin(), p.end(), 0.0);

    for (uint32_t iter = 0; iter < maxIter_; ++iter) {
        double rho = dot(rhat.data(), r.data(), n);
        if (std::fabs(rho) < 1e-300) {
            // breakdown：r̂ ⊥ r
            lastIter_ = iter; lastRes_ = norm2(r.data(), n); lastConv_ = (lastRes_ <= tol);
            return;
        }
        double beta = (rho / rhoOld) * (alpha / omega);
        // p = r + beta*(p - omega*v)
        for (uint32_t i = 0; i < n; ++i) p[i] = r[i] + beta * (p[i] - omega * v[i]);
        // ph = M^{-1} p
        applyIlu(p, ph);
        // v = A ph
        spmv(ph, v);
        double pdotv = dot(rhat.data(), v.data(), n);
        if (std::fabs(pdotv) < 1e-300) {
            lastIter_ = iter; lastRes_ = norm2(r.data(), n); lastConv_ = (lastRes_ <= tol);
            return;
        }
        alpha = rho / pdotv;
        // s = r - alpha*v
        for (uint32_t i = 0; i < n; ++i) s[i] = r[i] - alpha * v[i];
        double snorm = norm2(s.data(), n);
        lastRes_ = snorm;
        if (snorm <= tol) {
            // x += alpha*ph
            for (uint32_t i = 0; i < n; ++i) x[i] += alpha * ph[i];
            lastIter_ = iter + 1; lastConv_ = true;
            return;
        }
        // sh = M^{-1} s
        applyIlu(s, sh);
        // t = A sh
        spmv(sh, t);
        double tdott = dot(t.data(), t.data(), n);
        if (std::fabs(tdott) < 1e-300) {
            // x += alpha*ph
            for (uint32_t i = 0; i < n; ++i) x[i] += alpha * ph[i];
            lastIter_ = iter + 1; lastRes_ = snorm; lastConv_ = (snorm <= tol);
            return;
        }
        omega = dot(t.data(), s.data(), n) / tdott;
        if (std::fabs(omega) < 1e-300) {
            for (uint32_t i = 0; i < n; ++i) x[i] += alpha * ph[i];
            lastIter_ = iter + 1; lastRes_ = snorm; lastConv_ = (snorm <= tol);
            return;
        }
        // x += alpha*ph + omega*sh；r = s - omega*t
        for (uint32_t i = 0; i < n; ++i) {
            x[i] += alpha * ph[i] + omega * sh[i];
            r[i] = s[i] - omega * t[i];
        }
        rhoOld = rho;
        lastRes_ = norm2(r.data(), n);
        if (lastRes_ <= tol) { lastIter_ = iter + 1; lastConv_ = true; return; }
        if (std::fabs(omega) < 1e-14) { lastIter_ = iter + 1; lastConv_ = (lastRes_ <= tol); return; }
    }
    lastIter_ = maxIter_;
    lastConv_ = false;
}

} // namespace rfsim
