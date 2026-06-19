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
#include <utility>

namespace rfsim {

namespace {

const double PI = 3.14159265358979323846;

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
    if (opts.gminSteps == 0) {
        gm.push_back(opts.gmin);
    } else {
        uint32_t n = opts.gminSteps + 1;
        for (uint32_t i = 0; i < n; ++i) {
            double t = (n == 1) ? 0.0 : static_cast<double>(i) / static_cast<double>(n - 1);
            // 对数刻度：gminStart -> gmin
            double logStart = std::log10(std::max(opts.gminStart, 1e-20));
            double logStop  = std::log10(std::max(opts.gmin, 1e-20));
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
        if (fNorm < opts.reltol * f0Norm + opts.abstol) {
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
            DiagonalHbPrecond pc(sys.dim, Jreg);
            dx = prevDx;
            if (dx.size() != sys.dim) dx.assign(sys.dim, 0.0);
            GmresOptions gopts;
            gopts.restart = std::min(uint32_t(50), sys.dim);
            gopts.maxIter = sys.dim * 2;
            gopts.reltol = 1e-8;
            gopts.abstol = 1e-12;
            auto gr = solveGmres(op, &pc, negF, dx, gopts);
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
            // Armijo 充分下降：f(x+alpha p) <= f(x) - c*alpha*||J p||^2
            // J p = -F, 所以 ||J p||^2 = fNorm^2
            if (fTrial <= fNorm * (1.0 - 1e-4 * alpha)) {
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
        return r;
    }

    uint32_t NH = config.numHarmonics;

    // 收集电压源
    std::vector<const VoltageSource*> vsList;
    for (const auto& d : devices)
        if (auto* v = dynamic_cast<VoltageSource*>(d.get())) vsList.push_back(v);
    uint32_t numVS = static_cast<uint32_t>(vsList.size());
    uint32_t nEntities = numNodes + numVS;

    // 若未提供 DC 工作点，先求解以获取内部节点与电压源分支电流初始猜测。
    // 即使 DC 未严格收敛，也把它作为 HB 的初始猜测（比全零好）。
    std::vector<double> localDcOp;
    std::vector<double> localDcBranch;
    if (!dcOpNodeV) {
        auto dc = solveDcOp(numNodes, devices);
        if (!dc.nodeVoltages.empty()) {
            localDcOp = std::move(dc.nodeVoltages);
            localDcBranch = std::move(dc.branchCurrents);
            dcOpNodeV = &localDcOp;
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

    auto schedule = buildContinuationSchedule(opts);
    if (schedule.empty()) schedule.emplace_back(1.0, opts.gmin);

    bool anyOk = false;
    for (size_t si = 0; si < schedule.size(); ++si) {
        double srcScale = schedule[si].first;
        double gm = schedule[si].second;
        uint32_t stepIters = 0;
        bool ok = solveHbNewton(numNodes, devices, config, opts, srcScale, gm,
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
    return r;
}

} // namespace rfsim
