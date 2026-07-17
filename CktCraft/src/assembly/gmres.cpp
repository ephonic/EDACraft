// gmres.cpp - 右预条件 GMRES(m) 实现
#include "gmres.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace rfsim {

namespace {

inline double dot(const std::vector<double>& a, const std::vector<double>& b) {
    double s = 0.0;
    for (size_t i = 0; i < a.size(); ++i) s += a[i] * b[i];
    return s;
}

inline double norm2(const std::vector<double>& a) {
    return std::sqrt(dot(a, a));
}

inline void axpy(double alpha, const std::vector<double>& x, std::vector<double>& y) {
    for (size_t i = 0; i < y.size(); ++i) y[i] += alpha * x[i];
}

inline void scale(std::vector<double>& x, double alpha) {
    for (double& v : x) v *= alpha;
}

// Givens 旋转 (c,s) 作用于 [a;b] -> [r;0]
void applyGivens(double& a, double& b, double c, double s) {
    double t = c * a + s * b;
    b = -s * a + c * b;
    a = t;
}

void computeGivens(double a, double b, double& c, double& s) {
    if (b == 0.0) {
        c = std::copysign(1.0, a); s = 0.0;
    } else if (std::fabs(b) > std::fabs(a)) {
        double tau = a / b;
        s = std::copysign(1.0 / std::sqrt(1.0 + tau * tau), b);
        c = s * tau;
    } else {
        double tau = b / a;
        c = std::copysign(1.0 / std::sqrt(1.0 + tau * tau), a);
        s = c * tau;
    }
}

} // namespace

GmresResult solveGmres(const LinearOperator& A, const Preconditioner* M,
                       const std::vector<double>& b, std::vector<double>& x,
                       const GmresOptions& opts) {
    GmresResult r;
    const uint32_t n = A.dim();
    if (n == 0 || b.size() != n) { r.residual = 0.0; r.converged = true; return r; }
    if (x.size() != n) x.assign(n, 0.0);

    const uint32_t m = std::max(uint32_t(1), opts.restart);
    const double tol = opts.reltol * norm2(b) + opts.abstol;

    std::vector<std::vector<double>> V(m + 1, std::vector<double>(n, 0.0));
    std::vector<std::vector<double>> H(m + 1, std::vector<double>(m, 0.0));
    std::vector<double> cs(m, 0.0), sn(m, 0.0);
    std::vector<double> g(m + 1, 0.0);     // 右端项经过 Givens 旋转后的值
    std::vector<double> work(n, 0.0);

    uint32_t totalIter = 0;

    for (uint32_t cycle = 0; cycle <= opts.maxIter / m + 1; ++cycle) {
        // r = b - A x
        A.apply(x, work);
        for (uint32_t i = 0; i < n; ++i) V[0][i] = b[i] - work[i];
        double beta = norm2(V[0]);
        r.residual = beta;
        if (beta <= tol) { r.converged = true; r.iterations = totalIter; return r; }
        scale(V[0], 1.0 / beta);

        std::fill(g.begin(), g.end(), 0.0);
        g[0] = beta;
        for (auto& row : H) std::fill(row.begin(), row.end(), 0.0);

        for (uint32_t j = 0; j < m && totalIter < opts.maxIter; ++j, ++totalIter) {
            // z = M^{-1} v_j; w = A z
            if (M) M->apply(V[j], work);
            else work = V[j];
            A.apply(work, V[j + 1]);

            // Arnoldi 正交化（修正 Gram-Schmidt）
            for (uint32_t i = 0; i <= j; ++i) {
                H[i][j] = dot(V[i], V[j + 1]);
                axpy(-H[i][j], V[i], V[j + 1]);
            }
            H[j + 1][j] = norm2(V[j + 1]);
            if (H[j + 1][j] < 1e-300) {
                //  breakdown
                r.iterations = totalIter;
                return r;
            }
            scale(V[j + 1], 1.0 / H[j + 1][j]);

            // 应用前序 Givens 旋转到 H[:,j]
            for (uint32_t i = 0; i < j; ++i) {
                applyGivens(H[i][j], H[i + 1][j], cs[i], sn[i]);
            }
            // 计算新的 Givens 旋转消去 H[j+1][j]
            computeGivens(H[j][j], H[j + 1][j], cs[j], sn[j]);
            applyGivens(H[j][j], H[j + 1][j], cs[j], sn[j]);
            applyGivens(g[j], g[j + 1], cs[j], sn[j]);

            r.residual = std::fabs(g[j + 1]);
            if (r.residual <= tol) {
                // 收敛：解上三角系统 H[0..j][0..j] y = g[0..j]
                std::vector<double> y(j + 1, 0.0);
                for (int ii = static_cast<int>(j); ii >= 0; --ii) {
                    double s = g[ii];
                    for (uint32_t k = ii + 1; k <= j; ++k) s -= H[ii][k] * y[k];
                    y[ii] = s / H[ii][ii];
                }
                // x += M^{-1} V y
                std::fill(work.begin(), work.end(), 0.0);
                for (uint32_t k = 0; k <= j; ++k) axpy(y[k], V[k], work);
                if (M) {
                    std::vector<double> tmp(n);
                    M->apply(work, tmp);
                    work = std::move(tmp);
                }
                axpy(1.0, work, x);
                r.converged = true;
                r.iterations = totalIter;
                return r;
            }
        }

        // 重启：解上三角系统 H[0..m-1][0..m-1] y = g[0..m-1]
        std::vector<double> y(m, 0.0);
        for (int ii = static_cast<int>(m) - 1; ii >= 0; --ii) {
            double s = g[ii];
            for (uint32_t k = ii + 1; k < m; ++k) s -= H[ii][k] * y[k];
            y[ii] = s / H[ii][ii];
        }
        std::fill(work.begin(), work.end(), 0.0);
        for (uint32_t k = 0; k < m; ++k) axpy(y[k], V[k], work);
        if (M) {
            std::vector<double> tmp(n);
            M->apply(work, tmp);
            work = std::move(tmp);
        }
        axpy(1.0, work, x);
    }

    r.iterations = totalIter;
    return r;
}

} // namespace rfsim
