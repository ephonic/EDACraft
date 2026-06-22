// hb_nonlinear.cpp - Nonlinear Harmonic Balance implementation
//
// 基于完整频域卷积雅可比的阻尼 Newton：
//   1. 装配实数化残差 F 与稠密 Jacobian J
//   2. 直接 LU 求解 Newton 步 J·dx = -F
//   3. 回溯线搜索保证残差下降
//   4. 对极端情况回退到对角近似 safeguard
#include "hb_nonlinear.hpp"
#include "../assembly/hb_jacobian.hpp"
#include "../assembly/lu_solver.hpp"
#include "../assembly/gmres.hpp"
#include "../model/builtin_devices.hpp"
#include "dc_op.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <utility>

namespace rfsim {

namespace {

const double PI = 3.14159265358979323846;

// V2-δ S1 plan0621-v4 §1.3 补丁3：HB-NL verbose 开关，对齐 dc_op.cpp::dcopVerbose。
// RFSIM_HBNL_VERBOSE=0 静默；=1 每外层 Newton 一行；=2 同时打印 source/gmin
// continuation schedule、AC warm-start 状态与 dxMax/alpha。
int hbnlVerbose() {
    static int v = []() {
        const char* s = std::getenv("RFSIM_HBNL_VERBOSE");
        return s ? std::atoi(s) : 0;
    }();
    return v;
}

// 稠密实矩阵 LU 求解（部分选主元）
bool denseLuSolve(const std::vector<double>& A_in,
                  const std::vector<double>& b_in,
                  std::vector<double>& x) {
    int n = static_cast<int>(b_in.size());
    if (n == 0) { x.clear(); return true; }
    std::vector<std::vector<double>> A(n, std::vector<double>(n));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            A[i][j] = A_in[size_t(i) * n + j];
    std::vector<double> b = b_in;
    std::vector<int> piv(n);
    for (int i = 0; i < n; ++i) piv[i] = i;

    for (int k = 0; k < n; ++k) {
        int pivRow = k;
        double maxVal = std::fabs(A[k][k]);
        for (int i = k + 1; i < n; ++i) {
            double v = std::fabs(A[i][k]);
            if (v > maxVal) { maxVal = v; pivRow = i; }
        }
        if (maxVal < 1e-300) return false;
        if (pivRow != k) {
            std::swap(A[k], A[pivRow]);
            std::swap(piv[k], piv[pivRow]);
            std::swap(b[k], b[pivRow]);
        }
        double pivot = A[k][k];
        for (int i = k + 1; i < n; ++i) {
            double f = A[i][k] / pivot;
            A[i][k] = f;
            for (int j = k + 1; j < n; ++j) A[i][j] -= f * A[k][j];
            b[i] -= f * b[k];
        }
    }
    x.assign(n, 0.0);
    for (int i = n - 1; i >= 0; --i) {
        double s = b[i];
        for (int j = i + 1; j < n; ++j) s -= A[i][j] * x[j];
        x[i] = s / A[i][i];
    }
    return true;
}

// 实数解 dx 按实数化布局更新复数谐波未知量 X
void applyRealUpdate(uint32_t numNodes, uint32_t numVS, uint32_t NH,
                     const std::vector<double>& dx, double alpha,
                     std::vector<std::vector<Complex>>& X) {
    uint32_t perEntity = 1 + 2 * NH;
    uint32_t nEntities = numNodes + numVS;
    for (uint32_t e = 1; e <= nEntities; ++e) {
        uint32_t base = (e - 1) * perEntity;  // dx 从 0 开始（entity 1 对应 dx[0]）
        X[e][0] += Complex(alpha * dx[base], 0);
        for (uint32_t k = 1; k <= NH; ++k) {
            X[e][k] += Complex(alpha * dx[base + 2 * k - 1],
                               alpha * dx[base + 2 * k]);
        }
    }
}

// 残差范数
double residualNorm(const std::vector<double>& F) {
    double s = 0;
    for (double v : F) s += v * v;
    return std::sqrt(s);
}

// 稠密 Jacobian 算子（用于 GMRES）
class DenseJacobianOp : public LinearOperator {
public:
    DenseJacobianOp(uint32_t dim, const std::vector<double>& J)
        : dim_(dim), J_(J) {}
    uint32_t dim() const noexcept override { return dim_; }
    void apply(const std::vector<double>& x, std::vector<double>& y) const override {
        y.assign(dim_, 0.0);
        for (uint32_t i = 0; i < dim_; ++i) {
            double s = 0.0;
            size_t base = size_t(i) * dim_;
            for (uint32_t j = 0; j < dim_; ++j) s += J_[base + j] * x[j];
            y[i] = s;
        }
    }
private:
    uint32_t dim_;
    const std::vector<double>& J_;
};

// 对角预条件器（取 Jacobian 对角线倒数）
class DiagonalHbPrecond : public Preconditioner {
public:
    DiagonalHbPrecond(uint32_t dim, const std::vector<double>& J)
        : dim_(dim), invDiag_(dim) {
        for (uint32_t i = 0; i < dim_; ++i) {
            double d = J[size_t(i) * dim_ + i];
            invDiag_[i] = (std::fabs(d) < 1e-30) ? 1.0 : 1.0 / d;
        }
    }
    uint32_t dim() const noexcept override { return dim_; }
    void apply(const std::vector<double>& r, std::vector<double>& z) const override {
        z.resize(dim_);
        for (uint32_t i = 0; i < dim_; ++i) z[i] = invDiag_[i] * r[i];
    }
private:
    uint32_t dim_;
    std::vector<double> invDiag_;
};

// V2-γ post-S2: 块对角（per-harmonic）预条件器。
//
// HB Jacobian 的线性贡献在谐波索引 k 上严格块对角（每个 (k,k) 是该谐波下
// 的 admittance 矩阵 Y(jω_k)），非线性贡献跨 (k,m) 形成卷积式耦合。
// 直接取 J 对角线倒数（Jacobi 预条件器）忽略了每个 k-块内的节点-VS 耦合，
// 对 BSIM4 这类强非线性 HB 几乎不加速。
//
// 本预条件器：
//   1. 对每个谐波 k，从 dense J 中按行/列 gather (k,k) 子块；
//      k=0 块尺寸 nEntities × nEntities（实数 DC 导纳）；
//      k≥1 块尺寸 2·nEntities × 2·nEntities（实虚混合）。
//   2. 每块就地 partial-pivot LU 因子化（构造时一次性）。
//   3. apply(r,z)：按 k 分块 gather → LU 反代 → scatter 回 z；
//      若某块 LU 失败（接近奇异），该块退回到对角 Jacobi。
class BlockHarmonicPrecond : public Preconditioner {
public:
    BlockHarmonicPrecond(uint32_t dim, uint32_t nEntities, uint32_t NH,
                         const std::vector<double>& J)
        : dim_(dim), nEntities_(nEntities), NH_(NH), perEntity_(1 + 2 * NH),
          blocks_(NH + 1), invDiagFallback_(dim) {
        // 1) 准备每块 LU
        for (uint32_t k = 0; k <= NH; ++k) {
            Block& B = blocks_[k];
            B.bdim = (k == 0) ? nEntities_ : 2 * nEntities_;
            B.idx.reserve(B.bdim);
            // 收集全局索引 (entity e=1..nEntities, harmonic component slot)
            for (uint32_t e = 1; e <= nEntities_; ++e) {
                uint32_t base = (e - 1) * perEntity_;
                if (k == 0) {
                    B.idx.push_back(base + 0);
                } else {
                    B.idx.push_back(base + 2 * k - 1); // Re
                    B.idx.push_back(base + 2 * k);     // Im
                }
            }
            B.lu.assign(size_t(B.bdim) * B.bdim, 0.0);
            for (uint32_t i = 0; i < B.bdim; ++i) {
                size_t gr = B.idx[i];
                size_t base = gr * dim_;
                for (uint32_t j = 0; j < B.bdim; ++j) {
                    B.lu[size_t(i) * B.bdim + j] = J[base + B.idx[j]];
                }
            }
            B.piv.assign(B.bdim, 0);
            B.ok = factor(B.lu, B.piv, B.bdim);
        }
        // 2) Fallback Jacobi invDiag
        for (uint32_t i = 0; i < dim_; ++i) {
            double d = J[size_t(i) * dim_ + i];
            invDiagFallback_[i] = (std::fabs(d) < 1e-30) ? 1.0 : 1.0 / d;
        }
    }

    uint32_t dim() const noexcept override { return dim_; }

    void apply(const std::vector<double>& r, std::vector<double>& z) const override {
        z.assign(dim_, 0.0);
        std::vector<double> rb, zb;
        for (uint32_t k = 0; k <= NH_; ++k) {
            const Block& B = blocks_[k];
            if (B.ok) {
                rb.assign(B.bdim, 0.0);
                for (uint32_t i = 0; i < B.bdim; ++i) rb[i] = r[B.idx[i]];
                solveFactored(B.lu, B.piv, B.bdim, rb, zb);
                for (uint32_t i = 0; i < B.bdim; ++i) z[B.idx[i]] = zb[i];
            } else {
                for (uint32_t i = 0; i < B.bdim; ++i) {
                    size_t gi = B.idx[i];
                    z[gi] = invDiagFallback_[gi] * r[gi];
                }
            }
        }
    }

private:
    struct Block {
        uint32_t bdim = 0;
        std::vector<uint32_t> idx;     // 全局索引 (大小 bdim)
        std::vector<double>   lu;      // bdim × bdim factored (LU stored in-place)
        std::vector<int>      piv;     // 行置换
        bool ok = false;
    };

    // In-place partial-pivot LU factor; A becomes [L\U] with unit-diag L.
    static bool factor(std::vector<double>& A, std::vector<int>& piv, uint32_t n) {
        for (uint32_t i = 0; i < n; ++i) piv[i] = static_cast<int>(i);
        for (uint32_t k = 0; k < n; ++k) {
            uint32_t pr = k;
            double mv = std::fabs(A[size_t(k) * n + k]);
            for (uint32_t i = k + 1; i < n; ++i) {
                double v = std::fabs(A[size_t(i) * n + k]);
                if (v > mv) { mv = v; pr = i; }
            }
            if (mv < 1e-30) return false;
            if (pr != k) {
                for (uint32_t j = 0; j < n; ++j)
                    std::swap(A[size_t(k)*n + j], A[size_t(pr)*n + j]);
                std::swap(piv[k], piv[pr]);
            }
            double piv_v = A[size_t(k) * n + k];
            for (uint32_t i = k + 1; i < n; ++i) {
                double f = A[size_t(i)*n + k] / piv_v;
                A[size_t(i)*n + k] = f;
                for (uint32_t j = k + 1; j < n; ++j)
                    A[size_t(i)*n + j] -= f * A[size_t(k)*n + j];
            }
        }
        return true;
    }

    // Solve A x = b using factored A (in-place LU + piv).
    static void solveFactored(const std::vector<double>& A, const std::vector<int>& piv,
                              uint32_t n, const std::vector<double>& b,
                              std::vector<double>& x) {
        std::vector<double> bp(n);
        for (uint32_t i = 0; i < n; ++i) bp[i] = b[piv[i]];
        // Forward L y = bp (L 单位对角，存在 A 严格下三角)
        for (uint32_t i = 0; i < n; ++i) {
            double s = bp[i];
            for (uint32_t j = 0; j < i; ++j) s -= A[size_t(i)*n + j] * bp[j];
            bp[i] = s;
        }
        // Backward U x = y
        x.assign(n, 0.0);
        for (int i = static_cast<int>(n) - 1; i >= 0; --i) {
            double s = bp[i];
            for (uint32_t j = static_cast<uint32_t>(i) + 1; j < n; ++j)
                s -= A[size_t(i)*n + j] * x[j];
            x[i] = s / A[size_t(i)*n + i];
        }
    }

    uint32_t dim_;
    uint32_t nEntities_;
    uint32_t NH_;
    uint32_t perEntity_;
    std::vector<Block>  blocks_;
    std::vector<double> invDiagFallback_;
};

// V2-δ S1 plan0621-v4 §1.3 路径 D：AC 小信号 warm-start。
// DC OP 完成后，X[e][0] 已是 DC 偏置，X[e][k>=1]=0。在 sourceScale=1 装一次
// J & F：因 X[e][k>=1]=0，F[k=0]≈0 (DC 残差已收敛)，F[k>=1]≈-source(k)。
// 一步线性 Newton J·dx = -F 即给出 dx ≈ Y⁻¹(jω_k)·source(k) — 等价于器件
// 线性化后的小信号 AC 解。把 dx[k>=1] 写回 X[e][k>=1]，让 HB Newton 从更
// 接近真稳态的点起步。
//
// 设计要点：
//   1. 只更新 k>=1 谐波；DC 分量保持外部传入的暖启动（dx[k=0] 理论≈0，
//      但数值上仍可能有微小漂移，显式屏蔽更稳）。
//   2. dx 最大幅值若超过 1.0 V 则按 1.0/dxMax 缩放，避免线性化外推到
//      强非线性区（如 BSIM4 截止/饱和翻转）。
//   3. 任何数值异常 (装配失败/求解失败/NaN/Inf) 静默返回；调用方将以
//      原 DC-only 初值继续，行为与原代码一致。
//   4. 与 autoHomotopy 正交：sourceSteps=0 时尤其有效；sourceSteps>0
//      时也能改善每个 ε 段的起点。
void acSmallSignalWarmStart(uint32_t numNodes, uint32_t numVS, uint32_t NH,
                            const std::vector<std::unique_ptr<DeviceModel>>& devices,
                            const HbConfig& config,
                            std::vector<std::vector<Complex>>& X,
                            Diagnostics& diags) {
    if (NH == 0) return;
    HbRealSystem sys;
    if (!assembleHarmonicBalanceReal(numNodes, devices, config, X, sys, diags,
                                     /*sourceScale=*/1.0, /*gmin=*/0.0)) {
        if (hbnlVerbose() >= 1)
            std::fprintf(stderr, "[HB-NL] AC warm-start: assemble failed, skip\n");
        return;
    }
    std::vector<double> negF(sys.dim);
    for (size_t i = 0; i < sys.dim; ++i) negF[i] = -sys.F[i];
    std::vector<double> dx;
    bool solved = false;
    const uint32_t gmresThreshold = 200;
    if (sys.dim <= gmresThreshold) {
        solved = denseLuSolve(sys.J, negF, dx);
    } else {
        DenseJacobianOp op(sys.dim, sys.J);
        BlockHarmonicPrecond pcBlk(sys.dim, sys.nEntities, NH, sys.J);
        DiagonalHbPrecond pcDiag(sys.dim, sys.J);
        dx.assign(sys.dim, 0.0);
        GmresOptions gopts;
        gopts.restart = std::min(uint32_t(50), sys.dim);
        gopts.maxIter = sys.dim * 2;
        gopts.reltol = 1e-8;
        gopts.abstol = 1e-12;
        auto gr = solveGmres(op, &pcBlk, negF, dx, gopts);
        if (!gr.converged) {
            dx.assign(sys.dim, 0.0);
            gr = solveGmres(op, &pcDiag, negF, dx, gopts);
        }
        solved = gr.converged;
    }
    if (!solved || dx.size() != sys.dim) {
        if (hbnlVerbose() >= 1)
            std::fprintf(stderr, "[HB-NL] AC warm-start: linear solve failed, skip\n");
        return;
    }
    double dxMax = 0.0;
    for (double v : dx) {
        if (!std::isfinite(v)) {
            if (hbnlVerbose() >= 1)
                std::fprintf(stderr, "[HB-NL] AC warm-start: non-finite dx, skip\n");
            return;
        }
        dxMax = std::max(dxMax, std::fabs(v));
    }
    if (dxMax < 1e-18) return; // 无激励或全零，无需写入
    const double dxCap = 1.0;
    double alpha = (dxMax > dxCap) ? (dxCap / dxMax) : 1.0;
    uint32_t perEntity = 1 + 2 * NH;
    uint32_t nEntities = numNodes + numVS;
    for (uint32_t e = 1; e <= nEntities; ++e) {
        uint32_t base = (e - 1) * perEntity;
        // 只写 k>=1 谐波；k=0 (DC) 保留外部 warm-start，不被线性化解扰动。
        for (uint32_t k = 1; k <= NH; ++k) {
            double re = alpha * dx[base + 2 * k - 1];
            double im = alpha * dx[base + 2 * k];
            if (!std::isfinite(re) || !std::isfinite(im)) continue;
            X[e][k] += Complex(re, im);
        }
    }
    if (hbnlVerbose() >= 1)
        std::fprintf(stderr,
            "[HB-NL] AC warm-start: dxMax=%.3e  α=%.3e  applied to k>=1\n",
            dxMax, alpha);
}

// 对角近似 safeguard 步
void diagonalSafestep(uint32_t numNodes, uint32_t numVS, uint32_t NH, double w0,
                      const std::vector<std::vector<Complex>>& F,
                      std::vector<std::vector<Complex>>& X) {
    for (uint32_t e = 1; e <= numNodes + numVS; ++e) {
        for (uint32_t k = 0; k <= NH; ++k) {
            Complex jdiag;
            if (k == 0) jdiag = Complex(1e-2, 0);
            else jdiag = Complex(1e-3, k * w0 * 1e-9);
            if (std::abs(jdiag) < 1e-15) jdiag = Complex(1e-3, 0);
            Complex dx = -0.1 * F[e][k] / jdiag;
            double dxMag = std::abs(dx);
            if (dxMag > 1.0) dx *= 1.0 / dxMag;
            if (std::isnan(dx.real()) || std::isnan(dx.imag()) ||
                std::isinf(dx.real()) || std::isinf(dx.imag())) dx = Complex(0, 0);
            X[e][k] += dx;
        }
    }
}

} // namespace

// 计算所有器件（含 OSDI 内部节点）占用的最大全局节点编号
uint32_t computeMaxNodeId(const std::vector<std::unique_ptr<DeviceModel>>& devices) {
    uint32_t maxId = 0;
    for (const auto& d : devices) {
        if (!d) continue;
        for (NodeId n : d->nodes()) {
            if (n > maxId) maxId = n;
        }
    }
    return maxId;
}

// 构建 source/gmin continuation 调度表
std::vector<std::pair<double, double>> buildContinuationSchedule(const HbNlOptions& opts) {
    std::vector<std::pair<double, double>> sched;
    std::vector<double> src;
    if (opts.sourceSteps == 0) {
        src.push_back(1.0);
    } else {
        uint32_t n = opts.sourceSteps + 1;
        for (uint32_t i = 0; i < n; ++i) {
            double t = (n == 1) ? 0.0 : static_cast<double>(i) / static_cast<double>(n - 1);
            src.push_back(opts.sourceStart + t * (opts.sourceStop - opts.sourceStart));
        }
    }
    std::vector<double> gm;
    if (opts.gmin.gminSteps == 0) {
        gm.push_back(opts.gmin.gmin);
    } else {
        uint32_t n = opts.gmin.gminSteps + 1;
        for (uint32_t i = 0; i < n; ++i) {
            double t = (n == 1) ? 0.0 : static_cast<double>(i) / static_cast<double>(n - 1);
            // 对数刻度：gminStart -> gmin
            double logStart = std::log10(std::max(opts.gmin.gminStart, 1e-20));
            double logStop  = std::log10(std::max(opts.gmin.gmin, 1e-20));
            gm.push_back(std::pow(10.0, logStart + t * (logStop - logStart)));
        }
    }
    // 调度策略：先在较大 gmin 下把 source 从 sourceStart ramp 到
    // sourceStop，得到非线性器件已开启的解；再保持满 source
    // 把 gmin 降到目标值。这样避免在源幅度小且 gmin 极小时
    // 矩阵近奇异。
    for (double s : src) sched.emplace_back(s, gm.front());
    for (size_t i = 1; i < gm.size(); ++i)
        sched.emplace_back(src.back(), gm[i]);
    return sched;
}

// 单次 Newton 求解（固定 sourceScale 与 gmin）
bool solveHbNewton(uint32_t numNodes,
                   const std::vector<std::unique_ptr<DeviceModel>>& devices,
                   const HbConfig& config,
                   const HbNlOptions& opts,
                   double sourceScale,
                   double gmin,
                   std::vector<std::vector<Complex>>& X,
                   uint32_t& outIters,
                   Diagnostics& diags) {
    uint32_t NH = config.numHarmonics;
    double w0 = 2.0 * PI * config.fundamental;

    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices)
        if (auto* v = dynamic_cast<VoltageSource*>(d.get())) vsList.push_back(v);
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t nEntities = numNodes + numVS;

    HbRealSystem sys;
    double f0Norm = 0;
    std::vector<double> prevDx;

    auto doSafestep = [&]() {
        std::vector<std::vector<Complex>> Fcplx(nEntities + 1,
            std::vector<Complex>(NH + 1, Complex(0,0)));
        for (uint32_t e = 1; e <= nEntities; ++e) {
            uint32_t base = (e - 1) * sys.perEntity;
            Fcplx[e][0] = Complex(sys.F[base], 0);
            for (uint32_t k = 1; k <= NH; ++k) {
                Fcplx[e][k] = Complex(sys.F[base + 2*k - 1], sys.F[base + 2*k]);
            }
        }
        diagonalSafestep(numNodes, numVS, NH, w0, Fcplx, X);
    };

    for (uint32_t iter = 0; iter < opts.maxIter; ++iter) {
        outIters = iter + 1;

        if (!assembleHarmonicBalanceReal(numNodes, devices, config, X, sys, diags,
                                         sourceScale, gmin)) {
            diags.warn({}, "nonlinear HB: assembly failed");
            return false;
        }
        double fNorm = residualNorm(sys.F);
        if (iter == 0) f0Norm = fNorm;
        if (hbnlVerbose() >= 1) {
            std::fprintf(stderr,
                "[HB-NL] iter=%u  src=%.4g  gmin=%.3g  ||F||=%.6e  ||F||/||F0||=%.3e\n",
                iter, sourceScale, gmin, fNorm,
                (f0Norm > 0 ? fNorm / f0Norm : 0.0));
        }
        if (fNorm < opts.reltol * f0Norm + opts.abstol) {
            if (hbnlVerbose() >= 1)
                std::fprintf(stderr, "[HB-NL] converged at iter=%u (||F||=%.3e)\n",
                             iter, fNorm);
            return true;
        }

        // 解 J·dx = -F：小规模用稠密 LU，大规模用 GMRES
        std::vector<double> negF(sys.dim);
        for (size_t i = 0; i < sys.dim; ++i) negF[i] = -sys.F[i];
        // Tikhonov 正则化，抑制近奇异分量导致的大幅振荡
        std::vector<double> Jreg = sys.J;
        if (opts.lambda != 0.0) {
            for (uint32_t i = 0; i < sys.dim; ++i)
                Jreg[size_t(i) * sys.dim + i] += opts.lambda;
        }
        std::vector<double> dx;
        bool solved = false;
        const uint32_t gmresThreshold = 200;
        if (sys.dim <= gmresThreshold) {
            solved = denseLuSolve(Jreg, negF, dx);
        } else {
            DenseJacobianOp op(sys.dim, Jreg);
            // V2-γ post-S2: 优先块对角 per-harmonic 预条件器；若整体构造失败
            // （所有块都奇异，几乎不会发生），退回 Jacobi。
            BlockHarmonicPrecond pcBlk(sys.dim, nEntities, NH, Jreg);
            DiagonalHbPrecond pcDiag(sys.dim, Jreg);
            dx = prevDx;
            if (dx.size() != sys.dim) dx.assign(sys.dim, 0.0);
            GmresOptions gopts;
            gopts.restart = std::min(uint32_t(50), sys.dim);
            gopts.maxIter = sys.dim * 2;
            gopts.reltol = 1e-8;
            gopts.abstol = 1e-12;
            auto gr = solveGmres(op, &pcBlk, negF, dx, gopts);
            if (!gr.converged) {
                // 退回 Jacobi 再试一次，覆盖块对角失效的极端情况
                dx = prevDx;
                if (dx.size() != sys.dim) dx.assign(sys.dim, 0.0);
                gr = solveGmres(op, &pcDiag, negF, dx, gopts);
            }
            solved = gr.converged;
        }

        if (!solved || dx.size() != sys.dim) {
            doSafestep();
            continue;
        }

        bool dxBad = false;
        for (double v : dx) if (std::isnan(v) || std::isinf(v)) dxBad = true;

        if (dxBad) {
            doSafestep();
            continue;
        }

        // 阻尼 Newton：按 dvmax 限制最大步长，回溯线搜索
        double dxMax = 0.0;
        for (double v : dx) dxMax = std::max(dxMax, std::fabs(v));
        double alpha = (dxMax > 0.0) ? std::min(1.0, opts.dvmax / dxMax) : 1.0;
        HbRealSystem sysTrial;
        std::vector<std::vector<Complex>> Xtrial = X;
        double bestAlpha = alpha, bestF = fNorm;
        bool accepted = false;
        for (int bt = 0; bt < 25; ++bt) {
            Xtrial = X;
            applyRealUpdate(numNodes, numVS, NH, dx, alpha, Xtrial);
            if (!assembleHarmonicBalanceReal(numNodes, devices, config, Xtrial, sysTrial, diags,
                                             sourceScale, gmin)) break;
            double fTrial = residualNorm(sysTrial.F);
            if (fTrial < bestF) { bestF = fTrial; bestAlpha = alpha; }
            // V2-δ S1 plan0621-v4 §1.3 补丁1：Armijo 充分下降条件原写作
            //   fTrial <= fNorm * (1 - 1e-4*alpha)
            // 这是对 ‖F‖（而非 ‖F‖²）的比较，但所用系数 c=1e-4 是
            // 文献中对 ‖F‖² 的常规设置；等价转到 ‖F‖ 比较时系数应该
            // 减半 (因 sqrt 的一阶展开)，且应在两边都平方以避免线
            // 性近似偏差。这里写为 fTrial² ≤ fNorm²·(1 − 2·c·α)。
            // 原实现的门槛事实上严格 2 倍，导致 small α 几乎永远拒绝。
            const double armijoC = 1e-4;
            if (fTrial * fTrial <= fNorm * fNorm * (1.0 - 2.0 * armijoC * alpha)) {
                accepted = true;
                break;
            }
            if (alpha < 1e-7) break;
            alpha *= 0.5;
        }
        if (!accepted) {
            // 回溯结束时未找到满足 Armijo 的步长
            if (bestF >= fNorm * (1.0 - 1e-10)) {
                // 没有任何试验步使残差下降，回退 safeguard
                if (hbnlVerbose() >= 1)
                    std::fprintf(stderr, "[HB-NL] iter=%u  λ-search exhausted, safestep\n",
                                 iter);
                doSafestep();
                continue;
            }
            // 否则使用历史最优步长
            alpha = bestAlpha;
            Xtrial = X;
            applyRealUpdate(numNodes, numVS, NH, dx, alpha, Xtrial);
            if (!assembleHarmonicBalanceReal(numNodes, devices, config, Xtrial, sysTrial, diags,
                                             sourceScale, gmin)) {
                doSafestep();
                continue;
            }
            if (hbnlVerbose() >= 2)
                std::fprintf(stderr, "[HB-NL] iter=%u  accept-best α=%.3e ||F||→%.3e\n",
                             iter, alpha, bestF);
        } else if (hbnlVerbose() >= 2) {
            std::fprintf(stderr, "[HB-NL] iter=%u  armijo-OK α=%.3e\n", iter, alpha);
        }
        X = std::move(Xtrial);
        prevDx = dx;
        for (double& v : prevDx) v *= alpha;

        bool hasNaN = false;
        for (uint32_t e = 1; e <= nEntities; ++e)
            for (uint32_t k = 0; k <= NH; ++k)
                if (std::isnan(X[e][k].real()) || std::isnan(X[e][k].imag()) ||
                    std::isinf(X[e][k].real()) || std::isinf(X[e][k].imag()))
                    hasNaN = true;
        if (hasNaN) {
            doSafestep();
        }
    }
    return false;
}

HbNlResult solveHbNonlinear(uint32_t numNodes,
                            const std::vector<std::unique_ptr<DeviceModel>>& devices,
                            const HbConfig& config,
                            const std::vector<double>* dcOpNodeV,
                            const HbNlOptions& opts) {
    HbNlResult r;
    r.config = config;
    SteadyTimer tWall;
    BenchCounters* bench = benchJsonEnabled() ? &r.bench : nullptr;

    // 把 OSDI 内部节点纳入 HB 未知量
    numNodes = std::max(numNodes, computeMaxNodeId(devices));

    // 检测 OSDI 非线性器件；若无，直接用线性 HB
    bool hasNonlinear = false;
    for (const auto& d : devices)
        if (dynamic_cast<OsdiModel*>(d.get()) && !d->is_linear())
            if (dynamic_cast<OsdiModel*>(d.get())->ready()) hasNonlinear = true;

    if (!hasNonlinear) {
        auto lin = solveHbLinear(numNodes, devices, config);
        r.nodeVoltages = std::move(lin.nodeVoltages);
        r.converged = lin.ok;
        r.iterations = 1;
        if (bench) { bench->wall_ms = tWall.elapsedMs(); bench->newton_iter = 1; bench->peak_rss_mb = currentRssMb(); }
        return r;
    }

    // 跨 HB 求解前重置 OSDI limiting 状态，避免上一次 continuation/DC 的记忆污染
    for (const auto& d : devices)
        if (auto* o = dynamic_cast<OsdiModel*>(d.get()))
            o->resetLimiting();

    uint32_t NH = config.numHarmonics;

    // 收集电压源
    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices)
        if (auto* v = dynamic_cast<VoltageSource*>(d.get())) vsList.push_back(v);
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t nEntities = numNodes + numVS;

    // 若未提供 DC 工作点，先求解以获取内部节点与电压源分支电流初始猜测。
    // DC 未严格收敛仍可作为 HB 的暖启动（比全零更接近真解的非线性平衡），
    // 但需要做 sanitize：
    //   1. NaN/Inf 出现说明 DC Newton 已数值发散，节点电压无意义，必须丢弃；
    //   2. 绝对幅度过大（>1e6 V）说明 DC 解远离可信区间（可能限幅器 latch、
    //      gmin homotopy 失败），同样丢弃。
    //   3. 否则即使 dc.converged=false，仍保留作为暖启动并 warn 一次。
    std::vector<double> localDcOp;
    std::vector<double> localDcBranch;
    if (!dcOpNodeV) {
        auto dc = solveDcOp(numNodes, devices);
        bool sane = !dc.nodeVoltages.empty();
        if (sane) {
            for (double v : dc.nodeVoltages) {
                if (!std::isfinite(v) || std::fabs(v) > 1.0e6) { sane = false; break; }
            }
        }
        if (sane) {
            for (double v : dc.branchCurrents) {
                if (!std::isfinite(v) || std::fabs(v) > 1.0e6) { sane = false; break; }
            }
        }
        if (sane) {
            if (!dc.converged) {
                r.diags.warn({}, "hb-nl: DC OP did not converge; reusing finite DC voltages "
                                 "as warm start (may slow continuation)");
            }
            localDcOp = std::move(dc.nodeVoltages);
            localDcBranch = std::move(dc.branchCurrents);
            dcOpNodeV = &localDcOp;
        } else {
            // DC 完全不可用 → 用全零猜测；后续的 source-stepping/gmin 连续化
            // 通常能从 0 起跳到稳定点，比从 NaN/巨大值起跳鲁棒得多。
            r.diags.warn({}, "hb-nl: DC OP produced non-finite or out-of-range voltages; "
                             "dropping DC warm start and using zero initial guess");
        }
    }

    // 初始猜测
    std::vector<std::vector<Complex>> X(nEntities + 1,
                                        std::vector<Complex>(NH + 1, Complex(0, 0)));
    if (dcOpNodeV) {
        for (uint32_t i = 1; i <= numNodes && i < dcOpNodeV->size(); ++i) {
            X[i][0] = Complex((*dcOpNodeV)[i], 0);
        }
    }
    for (uint32_t vi = 0; vi < numVS && vi < localDcBranch.size(); ++vi) {
        uint32_t brEntity = numNodes + vi + 1;
        X[brEntity][0] = Complex(localDcBranch[vi], 0);
    }

    // V2-γ post-S2: 自动同伦。BSIM4 等 OSDI 强非线性器件在默认 sourceSteps=0
    // 且 gminSteps=0 下，HB-NL Newton 从单点起跳常常落在远离稳态的鞍点，
    // 60 iter 内难以收敛。仅在调用者**两项都没指定**时才介入：
    //   sourceSteps == 0 AND gmin.gminSteps == 0 → 全部覆盖为 (4, 4, 1e-3)。
    // 一旦用户显式设了任一项（如回归测试要 sourceSteps=10/gminSteps=0），
    // 视为用户主动接管同伦策略，本函数不再二次干预，保持 continuationSteps
    // 与调用者预期严格一致。
    HbNlOptions eff = opts;
    if (opts.autoHomotopy &&
        opts.sourceSteps == 0 && opts.gmin.gminSteps == 0) {
        eff.sourceSteps = 4;
        eff.gmin.gminSteps = 4;
        eff.gmin.gminStart = std::max(opts.gmin.gminStart, 1e-3);
    }

    // V2-δ S1 plan0621-v4 §1.3 路径 D：DC 已填，进一步用 AC 小信号解填充
    // X[e][k>=1]，避免 HB Newton 从 k>=1 全零起步（强非线性时直接发散）。
    // 仅在 opts.acWarmStart 开启时执行（默认 true）。
    //
    // 重要：AC warm-start 是按 sourceScale=1 装的线性化解。如果调用方
    // 启用了 source-stepping (sourceSteps>0 且 sourceStart<1)，continuation
    // 第一段会从 ε=sourceStart 起跑——此时预先填入 sourceScale=1 的 X[k>=1]
    // 反而成为"错误初值"，让 ε=sourceStart 段的 ‖F‖ 显著抬高甚至发散。
    // 故只在两种条件下启用 warm-start：
    //   (a) 没有 source-stepping (eff.sourceSteps==0，直接打满 src=1)；
    //   (b) source-stepping 已经从 1.0 起步 (eff.sourceStart>=1)。
    // 否则保持 X[k>=1]=0，由 continuation 自然 ramp，更鲁棒。
    bool srcRamped = (eff.sourceSteps > 0) && (eff.sourceStart < 1.0 - 1e-12);
    if (opts.acWarmStart && NH >= 1 && !srcRamped) {
        acSmallSignalWarmStart(numNodes, numVS, NH, devices, config, X, r.diags);
    }

    auto schedule = buildContinuationSchedule(eff);
    if (schedule.empty()) schedule.emplace_back(1.0, eff.gmin.gmin);

    bool anyOk = false;
    for (size_t si = 0; si < schedule.size(); ++si) {
        double srcScale = schedule[si].first;
        double gm = schedule[si].second;
        uint32_t stepIters = 0;
        bool ok = solveHbNewton(numNodes, devices, config, eff, srcScale, gm,
                                X, stepIters, r.diags);
        r.iterations += stepIters;
        if (!ok) {
            r.diags.warn({}, std::string("nonlinear HB: continuation step ") +
                         std::to_string(si) + " did not converge");
            break;
        }
        anyOk = true;
        r.continuationSteps = static_cast<uint32_t>(si + 1);
    }

    // 提取节点电压结果（忽略分支电流）
    r.nodeVoltages.assign(numNodes + 1, NodeHarmonics{});
    for (uint32_t i = 0; i <= numNodes; ++i) {
        r.nodeVoltages[i].v = X[i];
    }

    r.converged = anyOk && (schedule.empty() ||
        (r.continuationSteps == static_cast<uint32_t>(schedule.size())));
    if (!r.converged)
        r.diags.warn({}, "nonlinear HB: did not converge");
    if (bench) { bench->wall_ms = tWall.elapsedMs(); bench->newton_iter = r.iterations; bench->peak_rss_mb = currentRssMb(); }
    return r;
}

} // namespace rfsim
