// time_stepper.cpp — 固定步长时域积分器
#include "time_stepper.hpp"
#include "../assembly/linear_solver_factory.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <string>

namespace rfsim {

namespace {

uint32_t countVoltageSources(const std::vector<std::unique_ptr<DeviceModel>>& devices) {
    uint32_t cnt = 0;
    for (const auto& d : devices)
        if (dynamic_cast<VoltageSource*>(d.get())) ++cnt;
    return cnt;
}

void initializeDeviceStates(const std::vector<std::unique_ptr<DeviceModel>>& devices,
                            const std::vector<double>& nodeV) {
    for (const auto& d : devices) {
        if (d->hasTransientState()) d->initializeTransientState(nodeV);
    }
}

void updateDeviceStates(const std::vector<std::unique_ptr<DeviceModel>>& devices,
                        const std::vector<double>& nodeV,
                        const std::vector<double>& prevNodeV,
                        double t, double dt, IntegrationMethod method) {
    TransientOpPoint op;
    op.v = nodeV;
    op.v_prev = prevNodeV;
    op.time = t;
    op.dt = dt;
    op.method = method;
    for (const auto& d : devices) {
        if (!d->hasTransientState()) continue;
        // V3-MR: multi-rate——只对到达 K 步的器件调 swapState
        if (auto* osdi = dynamic_cast<OsdiModel*>(d.get())) {
            if (osdi->mrAdvance()) {
                osdi->updateTransientState(op);
            }
        } else {
            d->updateTransientState(op);
        }
    }
}

} // namespace

TimeDomainResult integrateTransient(uint32_t numNodes,
                                    const std::vector<std::unique_ptr<DeviceModel>>& devices,
                                    const std::vector<double>& initialNodeV,
                                    const TimeStepperOptions& opts) {
    TimeDomainResult r;
    r.numNodes = numNodes;
    r.numBranches = countVoltageSources(devices);

    uint32_t dim = numNodes + r.numBranches;
    if (dim == 0 || opts.dt <= 0.0 || opts.tstop < 0.0) {
        r.diags.error({}, "invalid transient parameters");
        return r;
    }

    // 初始节点电压（确保大小足够）
    std::vector<double> nodeV = initialNodeV;
    nodeV.resize(numNodes + 1, 0.0);
    std::vector<double> branchI(r.numBranches, 0.0);

    // 跨分析重置 OSDI limiting，防止上一次 DC/HB 求解的 limiting 锚点
    // （V_old）泄漏到 transient 的第一次 evalTransient。这里走的是
    // OsdiClient::limitingInitialized_ 的 reset，下一次 eval 会重新带 INIT_LIM。
    for (const auto& d : devices)
        if (auto* o = dynamic_cast<OsdiModel*>(d.get())) o->resetLimiting();

    auto buildSol = [&]() {
        std::vector<double> s(dim, 0.0);
        for (uint32_t i = 1; i <= numNodes; ++i) s[i - 1] = nodeV[i];
        for (uint32_t i = 0; i < r.numBranches; ++i) s[numNodes + i] = branchI[i];
        return s;
    };

    // B2：自动 multi-rate——opts.multiRate 开启时对所有 OSDI 器件启用 mrAutoTune。
    // 现有 mrRateRatio/mrStepCounter/mrAutoTune 机制自动分级（稳定器件 K 增大）。
    if (opts.multiRate) {
        for (const auto& d : devices)
            if (auto* o = dynamic_cast<OsdiModel*>(d.get())) o->setMrAutoTune(true);
    }

    // 用 DC 工作点初始化所有动态器件状态
    initializeDeviceStates(devices, nodeV);

    // 起始点 t=0
    r.points.push_back({0.0, buildSol()});

    uint32_t numSteps = static_cast<uint32_t>(std::round(opts.tstop / opts.dt));
    if (numSteps == 0) numSteps = 1;
    double dt = opts.tstop / static_cast<double>(numSteps);

    std::vector<double> prevNodeV = nodeV;

    // A1-4：求解器提到时间步循环外。同一电路拓扑下跨时间步 + 跨内层 Newton
    // 迭代复用 KLU 符号分解（sym_），只做数值 refactor——大幅省 klu_analyze 开销。
    // 固定步长 transient 中雅可比结构（节点/分支拓扑）全程稳定，refactor 命中率高。
    std::unique_ptr<LinearSolver> solver;
    const SolverMethod solverMethod = opts.solver;

    for (uint32_t step = 1; step <= numSteps; ++step) {
        double t = step * dt;
        std::vector<double> trialNodeV = nodeV;
        std::vector<double> trialBranchI = branchI;

        // 把 stamp 装配 + gmin 旁路 + 残差范数计算合到一处，方便线搜索复用。
        // 失败返回 false。成功填充 sysOut 与 fNormOut。
        // B1: residOnly=true 时 OSDI 器件走 evalTransientResidOnly（复用本 Newton 步的 jac），
        //     仅用于 line-search 试验点的 ‖F‖ 判断（不消费 sysOut.G）。首次装配必须 false。
        auto assembleAndNorm = [&](const std::vector<double>& tV,
                                   TransientSystem& sysOut,
                                   double& fNormOut,
                                   bool residOnly = false) -> bool {
            sysOut = TransientSystem();
            if (!assembleTransient(numNodes, devices, tV, prevNodeV, t, dt, opts.method,
                                   sysOut, r.diags, residOnly)) return false;
            if (opts.gmin.gmin != 0.0) {
                for (uint32_t i = 0; i < numNodes; ++i) {
                    sysOut.G.add(i, i, opts.gmin.gmin);  // add 自动走 addCommitted
                    sysOut.F[i] += opts.gmin.gmin * tV[i + 1];
                }
                if (!sysOut.G.patternCommitted()) sysOut.G.finalize();
            }
            double s = 0.0;
            for (double v : sysOut.F) s += v * v;
            fNormOut = std::sqrt(s);
            return true;
        };

        // 每个时间步内部做 Newton 迭代，含 dvmax 限幅 + Armijo 回溯线搜索。
        bool localConv = false;
        double prevAlphaApplied = 1.0;
        double prevMaxDxApplied = 0.0;
        // P1-7 stagnant 检测：保留最近的 ‖F‖ 序列，若 K 次迭代后无可见下降
        // 则判定停滞早退。该检测仅用于 standalone transient 调用路径
        //（runTransientPath/integrateTransient）；shooting 内层 Newton 在
        // integrateOnePeriod 中需保持 main↔FD 路径一致，不引入此检测。
        std::vector<double> fHistory;
        fHistory.reserve(opts.localNewtonMaxIter);
        for (uint32_t lit = 0; lit < opts.localNewtonMaxIter; ++lit) {
            // B1: 新 Newton 步——重置 OSDI 器件的 resid-only 标记，首装配算完整 jac。
            for (const auto& d : devices)
                if (auto* o = dynamic_cast<OsdiModel*>(d.get())) o->beginNewtonStep();
            TransientSystem sys;
            double fNorm = 0.0;
            if (!assembleAndNorm(trialNodeV, sys, fNorm)) {
                r.diags.error({}, "transient assembly failed at t=" + std::to_string(t));
                return r;
            }
            fHistory.push_back(fNorm);
            // 连续 5 次 ‖F‖ 比例>0.999 且 lit≥8 时判为停滞。
            if (fHistory.size() >= 6 && lit >= 8) {
                size_t n = fHistory.size();
                bool stagnant = true;
                for (size_t k = n - 5; k < n; ++k) {
                    if (fHistory[k] < fHistory[k - 1] * 0.999) {
                        stagnant = false;
                        break;
                    }
                }
                if (stagnant) {
                    r.diags.warn({}, "transient: inner Newton stagnant at t=" +
                                     std::to_string(t) +
                                     " fNorm=" + std::to_string(fNorm) +
                                     " after " + std::to_string(lit + 1) +
                                     " iters; breaking early");
                    break;
                }
            }

            // Shooting/Transient 雅可比是稀疏不对称结构，KLU(BTF+AMD+部分选主元 LU)
            // 比稠密 LuSolver 在 O(n) 节点规模下渐进更优，且电路矩阵特别契合 KLU 设计。
            // A1-4：solver 已提到时间步循环外，复用 KLU 符号分解。
            // 升级：method==Auto 且大矩阵时走经验基准选择。
            if (!sys.G.finalized() && !sys.G.patternCommitted()) sys.G.finalize();
            if (!solver) solver = (solverMethod == SolverMethod::Auto)
                                  ? makeAutoSolver(sys.G)
                                  : makeLinearSolver(solverMethod, hintsFromMatrix(sys.G));
            if (!solver || !solver->factorize(sys.G)) {
                r.diags.error({}, "transient linear factorization failed at t=" + std::to_string(t));
                return r;
            }
            Vector negF(sys.F.size());
            for (size_t i = 0; i < sys.F.size(); ++i) negF[i] = -sys.F[i];
            Vector dx;
            solver->solve(negF, dx);

            // NaN/Inf 防护
            bool dxBad = false;
            for (double v : dx) if (std::isnan(v) || std::isinf(v)) { dxBad = true; break; }
            if (dxBad) break;

            // 节点电压列上的未缩放 Newton 步：用作 dvmax 限幅基准 + 步长收敛准则。
            double dxMaxNode = 0.0;
            for (uint32_t i = 0; i < numNodes && i < dx.size(); ++i)
                dxMaxNode = std::max(dxMaxNode, std::fabs(dx[i]));

            // 当前节点电压尺度
            double scale = 0.0;
            for (uint32_t i = 1; i <= numNodes; ++i)
                scale = std::max(scale, std::fabs(trialNodeV[i]));
            double convThr = opts.abstol + opts.reltol * scale;

            // 步长收敛判定优先于 Armijo：MNA 残差 F 只在节点行包含电导支路项，
            // 不显式包含 I_VS 列，因此线性电路在 iter≥1 处可能出现 dx_V≈0 但
            // ||F||>0 的"伪非下降"假象。此时若先做 Armijo，会在 fTrial==fNorm
            // 时误判 Newton 方向不下降而提前退出。改为：dx 已小于容差就直接
            // 应用全步并判收敛，让支路电流列也按 Newton 步更新到位。
            if (dxMaxNode < convThr) {
                for (uint32_t i = 1; i <= numNodes && (i - 1) < dx.size(); ++i)
                    trialNodeV[i] += dx[i - 1];
                for (uint32_t i = 0; i < r.numBranches && (numNodes + i) < dx.size(); ++i)
                    trialBranchI[i] += dx[numNodes + i];
                prevAlphaApplied = 1.0;
                prevMaxDxApplied = dxMaxNode;
                localConv = true;
                break;
            }

            // dvmax 限幅
            double alpha = (dxMaxNode > 0.0)
                ? std::min(1.0, opts.dvmax / dxMaxNode) : 1.0;

            // Armijo 回溯线搜索：f(x+α dx) ≤ f(x) (1 - 1e-4 α)。
            // bestF/bestAlpha 跟踪所有试探中 fTrial 的最小值（不要求 < fNorm），
            // 用作严格 Armijo 失败时的安全兜底。原因：器件强非线性区（如二极管
            // 指数 I-V、BSIM 弱反型）下，OSDI 返回的雅可比相对真实 ∂F/∂x 存在
            // 一定误差，可能让 Newton 方向在当前点不严格满足 ½||F||² 的下降条件，
            // 但仍是合理的探测方向（最小残差点出现在 α>0 的某处）。此时若强制
            // Armijo 失败就 break，会让首次迭代 0 步推进，外层判定不收敛。
            std::vector<double> tV, tI;
            double bestAlpha = 0.0;
            double bestF = std::numeric_limits<double>::infinity();
            bool   accepted = false;
            for (int bt = 0; bt < 15; ++bt) {
                tV = trialNodeV;
                tI = trialBranchI;
                for (uint32_t i = 1; i <= numNodes && (i - 1) < dx.size(); ++i)
                    tV[i] += alpha * dx[i - 1];
                for (uint32_t i = 0; i < r.numBranches && (numNodes + i) < dx.size(); ++i)
                    tI[i] += alpha * dx[numNodes + i];

                TransientSystem sysTry;
                double fTrial = 0.0;
                // B1: line-search 试验点走 resid-only（复用本 Newton 步的 jac，省 jac 计算）。
                if (!assembleAndNorm(tV, sysTry, fTrial, /*residOnly=*/true)) {
                    alpha *= 0.5;
                    if (alpha < 1e-8) break;
                    continue;
                }
                if (fTrial < bestF) { bestF = fTrial; bestAlpha = alpha; }
                if (fTrial <= fNorm * (1.0 - 1e-4 * alpha) || fTrial < opts.abstol) {
                    trialNodeV = std::move(tV);
                    trialBranchI = std::move(tI);
                    accepted = true;
                    break;
                }
                if (alpha < 1e-6) break;
                alpha *= 0.5;
            }

            if (!accepted) {
                // 严格 Armijo 失败：判断是否所有试探都已"灾难性发散"（fTrial 远
                // 大于 fNorm，比如指数项已被激活到 10× 以上）；若是则 Newton 方向
                // 不可用，跳出外层迭代留待报错。否则取 bestAlpha 推进一小步 ——
                // 即使 fTrial 略 > fNorm（如 1e-4 量级的相对误差），下一次 Newton
                // 在新点重新计算雅可比，通常能恢复严格下降。这是电路仿真器面对
                // 强非线性 device 的常用兜底策略，比直接 break 更鲁棒。
                if (!std::isfinite(bestF) || bestF > fNorm * 10.0) {
                    break;
                }
                alpha = bestAlpha;
                tV = trialNodeV;
                tI = trialBranchI;
                for (uint32_t i = 1; i <= numNodes && (i - 1) < dx.size(); ++i)
                    tV[i] += alpha * dx[i - 1];
                for (uint32_t i = 0; i < r.numBranches && (numNodes + i) < dx.size(); ++i)
                    tI[i] += alpha * dx[numNodes + i];
                trialNodeV = std::move(tV);
                trialBranchI = std::move(tI);
            }

            // 应用步后再做一次步长收敛判定（针对 alpha<1 的情形）
            double maxDxApplied = 0.0;
            for (uint32_t i = 0; i < numNodes && i < dx.size(); ++i)
                maxDxApplied = std::max(maxDxApplied, std::fabs(alpha * dx[i]));
            prevAlphaApplied = alpha;
            prevMaxDxApplied = maxDxApplied;
            if (maxDxApplied < convThr) {
                localConv = true;
                break;
            }
        }

        if (!localConv) {
            std::string msg = "transient: inner Newton not converged at t=" +
                              std::to_string(t) +
                              " (last alpha=" + std::to_string(prevAlphaApplied) +
                              " maxDx=" + std::to_string(prevMaxDxApplied) + ")";
            if (opts.failOnNonConverge) {
                r.diags.error({}, msg);
                return r;
            }
            r.diags.warn({}, msg);
        }

        nodeV = trialNodeV;
        branchI = trialBranchI;

        // 更新动态器件状态
        updateDeviceStates(devices, nodeV, prevNodeV, t, dt, opts.method);
        prevNodeV = nodeV;

        r.points.push_back({t, buildSol()});
    }

    r.ok = true;
    return r;
}

} // namespace rfsim
