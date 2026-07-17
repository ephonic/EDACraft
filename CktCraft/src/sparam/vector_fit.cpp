// vector_fit.cpp — Vector Fitting 有理逼近算法实现
//
// 两阶段 VF（Gustavsen 1999）：
//   阶段 1 (极点重定位)：迭代求解同伦方程
//       σ(s)·1 = f(s)·H(s)，其中 σ(s)=Σ r̃_k/(s-p_k)+d̃+s·ẽ，
//       f(s)=Σ r_k/(s-p_k)+d+s·e。固定 ẽ=1 消去齐次不定性，最小二乘解
//       出 σ(s)，其零点 = 新极点（σ·Π(s-p_k) 多项式求根 → Durand-Kerner），
//       复数共轭对保留、不稳定极点翻转到左半平面。
//   阶段 2 (最终留数)：极点固定，直接最小二乘解 H(s)=Σ r_k/(s-p_k)+d+s·e。
//
// H(s) = Σ_k (r_k / (s - p_k)) + d + s*e
#include "vector_fit.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace rfsim {

namespace {

using Cplx = std::complex<double>;

// 复数线性方程组最小二乘求解 (A^H * A * x = A^H * b)
// A: m×n（m 个方程，n 个未知数，行优先），b: m，输出 x: n
// 返回 false 表示奇异。
bool solveComplexLinearSystem(
    const std::vector<std::vector<Cplx>>& A,
    const std::vector<Cplx>& b,
    std::vector<Cplx>& x
) {
    int m = static_cast<int>(A.size());
    if (m == 0) return false;
    int n = static_cast<int>(A[0].size());
    if (n == 0) return false;

    // 构造增广矩阵 [A^H * A | A^H * b]  (n × (n+1))
    // 含 Tikhonov 正则化 (岭回归): A^H A + λ·diag(|A^H A|)
    // VF 极点重定位方程存在固有秩亏 (σ/f 模型耦合列)，
    // 正则化保证最小二乘可解，λ 取相对迹的小比例。
    std::vector<std::vector<Cplx>> aug(n, std::vector<Cplx>(n + 1, Cplx(0, 0)));
    // 先计算对角元均值作为正则化尺度
    double diagMean = 0.0;
    for (int i = 0; i < n; ++i) {
        Cplx sum(0, 0);
        for (int k = 0; k < m; ++k) sum += std::conj(A[k][i]) * A[k][i];
        diagMean += std::abs(sum);
    }
    diagMean /= n;
    const double lambda = 1e-8 * diagMean;  // 岭系数

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            Cplx sum(0, 0);
            for (int k = 0; k < m; ++k) sum += std::conj(A[k][i]) * A[k][j];
            aug[i][j] = sum;
        }
        aug[i][i] += Cplx(lambda, 0);  // Tikhonov 项
    }
    for (int i = 0; i < n; ++i) {
        Cplx sum(0, 0);
        for (int k = 0; k < m; ++k) sum += std::conj(A[k][i]) * b[k];
        aug[i][n] = sum;
    }

    // 部分主元高斯消元
    for (int i = 0; i < n; ++i) {
        int piv = i;
        double maxAbs = std::abs(aug[i][i]);
        for (int r = i + 1; r < n; ++r) {
            double a = std::abs(aug[r][i]);
            if (a > maxAbs) { maxAbs = a; piv = r; }
        }
        if (maxAbs < 1e-14) return false;  // 奇异
        if (piv != i) std::swap(aug[i], aug[piv]);
        Cplx pivot = aug[i][i];
        for (int j = i; j <= n; ++j) aug[i][j] /= pivot;
        for (int r = 0; r < n; ++r) {
            if (r == i) continue;
            Cplx f = aug[r][i];
            if (std::abs(f) < 1e-15) continue;
            for (int j = i; j <= n; ++j) aug[r][j] -= f * aug[i][j];
        }
    }

    x.resize(n);
    for (int i = 0; i < n; ++i) x[i] = aug[i][n];
    return true;
}

// 计算拟合值 H_fit(s) = Σ r_k/(s-p_k) + d + s*e
Cplx evalFit(Cplx s, const std::vector<Cplx>& poles,
             const std::vector<Cplx>& residues, Cplx d, Cplx e) {
    Cplx h = d + s * e;
    for (size_t k = 0; k < poles.size(); ++k)
        h += residues[k] / (s - poles[k]);
    return h;
}

// 计算拟合 rms 误差
double computeRmsError(const std::vector<double>& freqs,
                      const std::vector<Cplx>& H,
                      const std::vector<Cplx>& poles,
                      const std::vector<Cplx>& residues,
                      Cplx d, Cplx e) {
    double err = 0.0;
    for (size_t i = 0; i < freqs.size(); ++i) {
        Cplx s(0, 2.0 * M_PI * freqs[i]);
        Cplx hf = evalFit(s, poles, residues, d, e);
        Cplx diff = H[i] - hf;
        err += std::norm(diff);
    }
    return std::sqrt(err / static_cast<double>(freqs.size()));
}

// Durand-Kerner (Weierstrass) 多项式求根。
// poly[K+1]: K 次多项式系数，poly[K] 为最高次（首项）。
// 返回 K 个根。
std::vector<Cplx> polyRoots(const std::vector<Cplx>& poly) {
    int K = static_cast<int>(poly.size()) - 1;
    if (K <= 0) return {};
    if (K == 1) return { -poly[0] / poly[1] };

    // 归一化为首一多项式: c[j] = poly[j] / poly[K]
    std::vector<Cplx> c(K + 1);
    Cplx lead = poly[K];
    if (std::abs(lead) < 1e-20) return {};
    for (int j = 0; j <= K; ++j) c[j] = poly[j] / lead;

    // 估计根模上限 (Cauchy bound): 1 + max|c_j|
    double rmax = 0.0;
    for (int j = 0; j < K; ++j) rmax = std::max(rmax, std::abs(c[j]));
    double R = 1.0 + rmax;

    // 初始猜测: 在半径 R 的圆上均匀分布
    std::vector<Cplx> roots(K);
    for (int j = 0; j < K; ++j) {
        double ang = 2.0 * M_PI * (j + 0.25) / K;  // +0.25 避免落在实轴
        roots[j] = std::polar(R, ang);
    }

    // 迭代
    auto evalPoly = [&](Cplx s) -> Cplx {
        Cplx v(0, 0);
        for (int j = K; j >= 0; --j) v = v * s + c[j];
        return v;
    };

    for (int iter = 0; iter < 200; ++iter) {
        double maxDelta = 0.0;
        for (int j = 0; j < K; ++j) {
            Cplx num = evalPoly(roots[j]);
            Cplx den(1, 0);
            for (int m = 0; m < K; ++m) {
                if (m != j) den *= (roots[j] - roots[m]);
            }
            if (std::abs(den) < 1e-20) continue;
            Cplx delta = num / den;
            roots[j] -= delta;
            maxDelta = std::max(maxDelta, std::abs(delta));
        }
        if (maxDelta < 1e-14) break;
    }
    return roots;
}

// 计算多项式 σ(s)·Π_k(s-p_k) 的系数。
// σ(s) = Σ_k r̃_k/(s-p_k) + d̃ + s·ẽ
// Π_k(s-p_k) = 首一多项式 (s-p_0)(s-p_1)...(s-p_{K-1})
// 乘积是 K 次多项式（因为 σ·Π 中极点抵消，剩余 K 次）。
// 返回 poly[0..K] (poly[K]=首项)。
std::vector<Cplx> sigmaTimesProd(const std::vector<Cplx>& poles,
                                  const std::vector<Cplx>& residues,
                                  Cplx d, Cplx e) {
    int K = static_cast<int>(poles.size());
    if (K == 0) return {};

    // 1) 计算 Π_k(s-p_k) 系数 poly[K+1]，poly[K]=1 首一
    std::vector<Cplx> poly(K + 1, Cplx(0, 0));
    poly[0] = Cplx(1, 0);
    for (int k = 0; k < K; ++k) {
        std::vector<Cplx> np(K + 1, Cplx(0, 0));
        for (int j = 0; j <= k; ++j) {
            np[j + 1] += poly[j];            // s 项
            np[j]     -= poly[j] * poles[k];  // -p_k 项
        }
        poly = np;
    }
    // poly[K]=1(首一), poly[K-1..0] 为低次系数

    // 2) q(s) = Σ_k r̃_k·(poly 除以 (s-p_k)) + (d̃ + s·ẽ)·poly
    //    poly 除以 (s-p_k) = 综合除法，结果为 K 次多项式
    std::vector<Cplx> q(K + 1, Cplx(0, 0));
    for (int k = 0; k < K; ++k) {
        // poly / (s - p_k): 综合除法，rem[j], j=0..K-1
        std::vector<Cplx> rem(K, Cplx(0, 0));
        rem[K - 1] = poly[K];  // 首一
        for (int j = K - 2; j >= 0; --j)
            rem[j] = poly[j + 1] + poles[k] * rem[j + 1];
        for (int j = 0; j < K; ++j) q[j] += residues[k] * rem[j];
    }
    // (d̃ + s·ẽ)·poly → d̃·poly + ẽ·s·poly(升幂)
    for (int j = 0; j <= K; ++j) {
        q[j] += d * poly[j];
        if (j + 1 <= K) q[j + 1] += e * poly[j];
    }
    return q;  // q[K] 为首项，可能非 1
}

// 翻转极点到左半平面（无源性/稳定性：Re(p) ≤ 0）
void flipUnstablePoles(std::vector<Cplx>& poles) {
    for (auto& p : poles) {
        if (p.real() > 0) p = Cplx(-p.real(), p.imag());
    }
}

// 求解固定极点下的留数：H(s) = Σ r_k/(s-p_k) + d + s·e 最小二乘
VFResult solveResidues(const std::vector<double>& freqs,
                       const std::vector<Cplx>& H,
                       const std::vector<Cplx>& poles) {
    VFResult res;
    res.poles = poles;
    int K = static_cast<int>(poles.size());
    int N = static_cast<int>(freqs.size());
    int nUnk = K + 2;  // [r_0..r_{K-1}, d, e]

    std::vector<std::vector<Cplx>> A(N, std::vector<Cplx>(nUnk));
    std::vector<Cplx> b(N);
    for (int i = 0; i < N; ++i) {
        Cplx s(0, 2.0 * M_PI * freqs[i]);
        for (int k = 0; k < K; ++k) A[i][k] = Cplx(1, 0) / (s - poles[k]);
        A[i][K]     = Cplx(1, 0);  // d
        A[i][K + 1] = s;           // e
        b[i] = H[i];
    }
    std::vector<Cplx> x;
    res.residues.assign(K, Cplx(0, 0));
    res.constant = Cplx(0, 0);
    res.proportional = Cplx(0, 0);
    if (solveComplexLinearSystem(A, b, x)) {
        for (int k = 0; k < K; ++k) res.residues[k] = x[k];
        res.constant = x[K];
        res.proportional = x[K + 1];
    }
    res.rms_error = computeRmsError(freqs, H, res.poles, res.residues,
                                    res.constant, res.proportional);
    res.converged = res.rms_error < 1e-6;
    return res;
}

// 初始化极点：在对数频率轴上均匀分布，左半平面共轭对
std::vector<Cplx> initPoles(const std::vector<double>& freqs, int num_poles) {
    std::vector<Cplx> poles;
    if (freqs.empty()) return poles;
    double fMin = freqs.front();
    double fMax = freqs.back();
    if (fMin <= 0) fMin = fMax * 1e-3;
    double logMin = std::log10(fMin);
    double logMax = std::log10(fMax);

    for (int k = 0; k < num_poles; ++k) {
        double t = (num_poles > 1) ? static_cast<double>(k) / (num_poles - 1) : 0.5;
        double f = std::pow(10.0, logMin + (logMax - logMin) * t);
        double omega = 2.0 * M_PI * f;
        poles.emplace_back(-omega * 0.01, omega);
    }
    return poles;
}

} // anonymous namespace

VFResult vectorFitFixedPoles(
    const std::vector<double>& freqs,
    const std::vector<Cplx>& H,
    const std::vector<Cplx>& poles
) {
    VFResult res;
    if (freqs.size() != H.size() || freqs.empty() || poles.empty()) {
        res.rms_error = 1e10;
        res.converged = false;
        return res;
    }
    return solveResidues(freqs, H, poles);
}

VFResult vectorFit(
    const std::vector<double>& freqs,
    const std::vector<Cplx>& H,
    int num_poles,
    int num_iters,
    double tol
) {
    VFResult res;
    res.converged = false;

    if (freqs.size() != H.size() || freqs.empty() || num_poles <= 0) {
        res.rms_error = 1e10;
        return res;
    }

    int N = static_cast<int>(freqs.size());
    int K = num_poles;

    // 阶段 1: 极点重定位迭代
    std::vector<Cplx> poles = initPoles(freqs, K);
    double prevRms = 1e30;

    for (int iter = 0; iter < num_iters; ++iter) {
        // 同伦方程 σ(s)·H(s) = f(s)，固定 ẽ=1 消去齐次不定性:
        //   (Σ_k r̃_k/(s_i-p_k) + d̃ + s_i·1)·H(s_i) = Σ_k r_k/(s_i-p_k) + d + s_i·e
        // 移项 (σ·H - f = 0):
        //   Σ_k r̃_k·H/(s-p_k) + d̃·H + s·H·1 - Σ_k r_k/(s-p_k) - d - s·e = 0
        // 未知数 x = [r̃_0..r̃_{K-1}, d̃, r_0..r_{K-1}, d, e]  (2K+3 个)
        // 行: [H·φ_k, H, -φ_k, -1, -s], RHS = -s·H  (s·H·1 的常数项)
        int nUnk = 2 * K + 3;
        std::vector<std::vector<Cplx>> A(N, std::vector<Cplx>(nUnk));
        std::vector<Cplx> b(N);
        for (int i = 0; i < N; ++i) {
            Cplx s(0, 2.0 * M_PI * freqs[i]);
            Cplx Hi = H[i];
            // σ 基 (乘 H): [H/(s-p_0), ..., H/(s-p_{K-1}), H]
            for (int k = 0; k < K; ++k) A[i][k] = Hi / (s - poles[k]);
            A[i][K] = Hi;                  // d̃·H
            // f 基 (移到左侧取负): [-1/(s-p_0), ..., -1/(s-p_{K-1}), -1, -s]
            for (int k = 0; k < K; ++k) A[i][K + 1 + k] = -Cplx(1, 0) / (s - poles[k]);
            A[i][2 * K + 1] = Cplx(-1, 0);  // -d
            A[i][2 * K + 2] = -s;           // -s·e
            // ẽ=1 的常数项 s·1·H 移到 RHS (取负)
            b[i] = -s * Hi;
        }
        std::vector<Cplx> x;
        if (!solveComplexLinearSystem(A, b, x)) break;

        // 提取 σ(s) = Σ r̃_k/(s-p_k) + d̃ + s·1
        std::vector<Cplx> sigmaRes(K);
        for (int k = 0; k < K; ++k) sigmaRes[k] = x[k];
        Cplx sigmaD = x[K];
        Cplx sigmaE = Cplx(1, 0);  // ẽ=1

        // 新极点 = σ(s) 的零点 = σ·Π(s-p_k) 多项式的根
        std::vector<Cplx> q = sigmaTimesProd(poles, sigmaRes, sigmaD, sigmaE);
        std::vector<Cplx> newPoles = polyRoots(q);
        if (newPoles.empty() || static_cast<int>(newPoles.size()) != K) break;
        flipUnstablePoles(newPoles);

        // 阶段 2: 用新极点解最终留数，计算 rms 误差判断收敛
        VFResult trial = solveResidues(freqs, H, newPoles);
        double rmsChange = std::abs(trial.rms_error - prevRms) /
                           std::max(1.0, prevRms);
        prevRms = trial.rms_error;
        poles = newPoles;

        if (rmsChange < tol || trial.rms_error < tol) {
            res = trial;
            res.converged = true;
            return res;
        }
        res = trial;
    }

    // 最终: 用当前极点解留数
    res = solveResidues(freqs, H, poles);
    res.converged = res.rms_error < tol * 100;  // 放宽收敛判据
    return res;
}

} // namespace rfsim
