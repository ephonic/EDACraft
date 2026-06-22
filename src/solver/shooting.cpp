// shooting.cpp — Single Shooting 周期稳态求解器
#include "shooting.hpp"
#include "../assembly/klu_solver.hpp"
#include "../assembly/hb_jacobian.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <cmath>
#include <iostream>
#include <sstream>

namespace rfsim {

namespace {

uint32_t countVoltageSources(const std::vector<std::unique_ptr<DeviceModel>>& devices) {
    uint32_t cnt = 0;
    for (const auto& d : devices)
        if (dynamic_cast<VoltageSource*>(d.get())) ++cnt;
    return cnt;
}

void saveDeviceStates(const std::vector<std::unique_ptr<DeviceModel>>& devices,
                      std::vector<std::vector<double>>& states) {
    states.clear();
    for (const auto& d : devices) {
        if (d->hasTransientState()) states.push_back(d->getTransientState());
        else states.emplace_back();
    }
}

void restoreDeviceStates(const std::vector<std::unique_ptr<DeviceModel>>& devices,
                         const std::vector<std::vector<double>>& states) {
    for (size_t i = 0; i < devices.size(); ++i) {
        if (devices[i]->hasTransientState() && i < states.size())
            devices[i]->setTransientState(states[i]);
    }
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
        if (d->hasTransientState()) d->updateTransientState(op);
    }
}

// 从给定初始节点电压积分一个周期，返回最终 MNA 解 xFinal。
bool integrateOnePeriod(uint32_t numNodes,
                        const std::vector<std::unique_ptr<DeviceModel>>& devices,
                        const std::vector<double>& initialNodeV,
                        const ShootingConfig& config,
                        const ShootingOptions& opts,
                        std::vector<double>& xFinal,
                        Diagnostics& diags,
                        TransientSystem& sys) {
    uint32_t numVS = countVoltageSources(devices);
    uint32_t dim = numNodes + numVS;
    // V3-L0: 首次调用时做一次 dry-run assemble 建 pattern + commit。
    // 后续 assembleTransient 走 fast path（zeroCommitted + add()→addCommitted）。
    // 不用 bindStampPtrs——所有 stamp 统一走 add()，避免指针生命周期问题。
    if (!sys.G.patternCommitted()) {
        // 建 vsIdx（与 assembleTransient 一致）
        std::vector<uint32_t> vsIdx;
        uint32_t vsCnt = 0;
        for (uint32_t i = 0; i < devices.size(); ++i) {
            if (dynamic_cast<VoltageSource*>(devices[i].get())) {
                vsIdx.push_back(i);
                ++vsCnt;
            }
        }
        auto vsBranch = [&](uint32_t di) -> uint32_t {
            for (uint32_t k = 0; k < vsIdx.size(); ++k)
                if (vsIdx[k] == di) return numNodes + k;
            return numNodes;
        };
        sys.numNodes = numNodes;
        sys.numBranches = vsCnt;
        sys.F.assign(dim, 0.0);
        sys.G.resize(dim);
        for (uint32_t i = 0; i < numNodes; ++i) sys.G.addPattern(i, i);
        for (uint32_t di = 0; di < devices.size(); ++di) {
            const auto& dev = devices[di];
            const auto& nds = dev->nodes();
            if (dynamic_cast<Resistor*>(dev.get())) {
                NodeId n1 = nds.size() > 0 ? nds[0] : 0;
                NodeId n2 = nds.size() > 1 ? nds[1] : 0;
                if (n1 != 0) sys.G.addPattern(n1 - 1, n1 - 1);
                if (n2 != 0) sys.G.addPattern(n2 - 1, n2 - 1);
                if (n1 != 0 && n2 != 0) { sys.G.addPattern(n1 - 1, n2 - 1); sys.G.addPattern(n2 - 1, n1 - 1); }
            } else if (dynamic_cast<VoltageSource*>(dev.get())) {
                uint32_t br = vsBranch(di);
                NodeId n1 = nds.size() > 0 ? nds[0] : 0;
                NodeId n2 = nds.size() > 1 ? nds[1] : 0;
                if (n1 != 0) { sys.G.addPattern(n1 - 1, br); sys.G.addPattern(br, n1 - 1); }
                if (n2 != 0) { sys.G.addPattern(n2 - 1, br); sys.G.addPattern(br, n2 - 1); }
                sys.G.addPattern(br, br);
            } else if (dynamic_cast<Capacitor*>(dev.get()) || dynamic_cast<Inductor*>(dev.get())) {
                for (uint32_t r = 0; r < nds.size(); ++r) {
                    if (nds[r] == 0) continue;
                    for (uint32_t c = 0; c < nds.size(); ++c) {
                        if (nds[c] == 0) continue;
                        sys.G.addPattern(nds[r] - 1, nds[c] - 1);
                    }
                }
            } else if (auto* osdi = dynamic_cast<OsdiModel*>(dev.get())) {
                if (!osdi->ready()) continue;
                const OsdiDescriptor* d = osdi->descriptor();
                const auto& onds = osdi->nodes();
                for (uint32_t e = 0; e < d->num_jacobian_entries; ++e) {
                    const OsdiJacobianEntry& je = d->jacobian_entries[e];
                    NodeId gr = (je.nodes.node_1 < onds.size()) ? onds[je.nodes.node_1] : 0;
                    NodeId gc = (je.nodes.node_2 < onds.size()) ? onds[je.nodes.node_2] : 0;
                    if (gr == 0 && gc == 0) continue;
                    if (gr == 0) sys.G.addPattern(gc - 1, gc - 1);
                    else if (gc == 0) sys.G.addPattern(gr - 1, gr - 1);
                    else sys.G.addPattern(gr - 1, gc - 1);
                }
            }
        }
        sys.G.finalize();
        sys.G.commitPattern();
        // V3-L0: 绑定 OSDI stamp 指针
        for (uint32_t di = 0; di < devices.size(); ++di) {
            if (auto* osdi = dynamic_cast<OsdiModel*>(devices[di].get())) {
                if (osdi->ready()) osdi->bindStampPtrs(sys.G, numNodes);
            }
        }
    }
    double T = 1.0 / config.fundamental;
    uint32_t numSteps = config.numTimePoints;
    if (numSteps == 0) numSteps = 100;
    double dt = T / static_cast<double>(numSteps);

    std::vector<double> nodeV = initialNodeV;
    nodeV.resize(numNodes + 1, 0.0);
    std::vector<double> branchI(numVS, 0.0);

    auto buildSol = [&]() {
        std::vector<double> s(dim, 0.0);
        for (uint32_t i = 1; i <= numNodes; ++i) s[i - 1] = nodeV[i];
        for (uint32_t i = 0; i < numVS; ++i) s[numNodes + i] = branchI[i];
        return s;
    };

    std::vector<double> prevNodeV = nodeV;

    // 动态器件状态从初始猜测初始化
    initializeDeviceStates(devices, nodeV);

    // P1-5: gmin log-spaced homotopy schedule。
    // 调度仅依赖 opts（不依赖 trialNodeV / step），且在函数入口一次性建好，
    // 确保 Shooting 主路径与 FD 扰动路径使用完全相同的 gmin 序列，从而保持
    // (G[u+ε]-G[u])/ε 的噪声底。
    // 默认 gminSteps=0 → schedule={opts.gmin.gmin}，与原行为完全一致（零开销）。
    std::vector<double> gminSchedule;
    if (opts.gmin.gminSteps == 0) {
        gminSchedule.push_back(opts.gmin.gmin);
    } else {
        double gStart = opts.gmin.gminStart > 0.0 ? opts.gmin.gminStart : 1e-2;
        double gEnd   = opts.gmin.gmin      > 0.0 ? opts.gmin.gmin      : 1e-12;
        if (gEnd >= gStart) {
            // 配置异常时退化为单点
            gminSchedule.push_back(gEnd);
        } else {
            uint32_t n = opts.gmin.gminSteps + 1;
            double logS = std::log(gStart);
            double logE = std::log(gEnd);
            gminSchedule.reserve(n);
            for (uint32_t k = 0; k < n; ++k) {
                double f = static_cast<double>(k) / static_cast<double>(n - 1);
                gminSchedule.push_back(std::exp(logS + (logE - logS) * f));
            }
        }
    }

    for (uint32_t step = 1; step <= numSteps; ++step) {
        double t = step * dt;
        std::vector<double> trialNodeV = nodeV;
        std::vector<double> trialBranchI = branchI;

        // 每个时间步内部做 Newton 迭代，以处理非线性器件。
        //
        // 注意：这里使用宽松的接受准则（f1 ≤ f0·(1+1e-10) || λ<1e-4）而非
        // 严格 Armijo（f1 ≤ f0·(1-1e-4·λ)）—— 这是 Shooting 的固有需求：
        //   1. 该函数同时被 Shooting 主路径和 FD 雅可比扰动路径调用；
        //   2. FD 雅可比要求扰动后的轨迹与主路径保持"同一接受准则下的"
        //      一致演化，否则 (G[u+ε]-G[u])/ε 引入显著噪声；
        //   3. 严格 Armijo 在强非线性器件（如二极管整流）下会让两条路径
        //      在 best-α 兜底分支取到不同 α，造成 FD 噪声爆炸，外层 Newton
        //      失去线性化精度而不收敛。
        // 对应的强收敛性保证由 P1-5（gmin log-spaced homotopy）和 P1-7
        // （stagnant/floor 检测）从外层提供。
        uint32_t localMaxIter = opts.localNewtonMaxIter > 0 ? opts.localNewtonMaxIter : 50;
        // P1-5: 沿 gmin 调度逐级求解，每级把上一级的 trialNodeV/trialBranchI
        // 当作初始猜测。schedule 的最后一项即 opts.gmin.gmin（目标值）。
        // 当 gminSteps=0 时 schedule 仅一项，外层循环退化为单次执行，与原代码等价。
        for (double gminCur : gminSchedule) {
            bool localConv = false;
            for (uint32_t lit = 0; lit < localMaxIter; ++lit) {
                if (!assembleTransient(numNodes, devices, trialNodeV, prevNodeV, t, dt, config.method,
                                       sys, diags)) {
                    diags.error({}, "shooting: transient assembly failed");
                    return false;
                }
                // 加 gmin 旁路提高非线性/开关电路的可解性
                const double gmin = gminCur;
                for (uint32_t i = 0; i < numNodes; ++i) {
                    sys.G.add(i, i, gmin);  // add 自动走 addCommitted（若已 commit）
                    sys.F[i] += gmin * trialNodeV[i + 1];
                }
                if (!sys.G.patternCommitted()) sys.G.finalize();

                // Shooting 内层 Newton：稀疏不对称 MNA → KLU 直接求解器。
                KluSolver solver;
                if (!solver.factorize(sys.G)) {
                    diags.error({}, "shooting: KLU factorization failed");
                    return false;
                }
                Vector negF(sys.F.size());
                for (size_t i = 0; i < sys.F.size(); ++i) negF[i] = -sys.F[i];
                Vector x;
                solver.solve(negF, x);

                bool hasNan = false;
                for (double val : x) if (std::isnan(val) || std::isinf(val)) { hasNan = true; break; }
                if (hasNan) {
                    diags.error({}, "shooting: NaN/Inf in Newton update at t=" + std::to_string(t));
                    return false;
                }

                // 局部 Newton 回溯线搜索：若全步导致残差严重增大则收缩步长。
                // 接受准则故意宽松（见上方注释）。
                double f0 = 0.0;
                for (double val : sys.F) f0 += val * val;
                f0 = std::sqrt(f0);

                double lambda = 1.0;
                bool accepted = false;
                for (int bt = 0; bt < 8; ++bt) {
                    std::vector<double> tV = trialNodeV;
                    std::vector<double> tI = trialBranchI;
                    for (uint32_t i = 1; i <= numNodes && (i - 1) < x.size(); ++i)
                        tV[i] += lambda * x[i - 1];
                    for (uint32_t i = 0; i < numVS && (numNodes + i) < x.size(); ++i)
                        tI[i] += lambda * x[numNodes + i];

                    TransientSystem sysTry;
                    if (!assembleTransient(numNodes, devices, tV, prevNodeV, t, dt, config.method,
                                           sysTry, diags)) {
                        lambda *= 0.5;
                        continue;
                    }
                    for (uint32_t i = 0; i < numNodes; ++i) {
                        sysTry.G.add(i, i, gmin);  // add 自动走 addCommitted
                        sysTry.F[i] += gmin * tV[i + 1];
                    }
                    if (!sysTry.G.patternCommitted()) sysTry.G.finalize();

                    double f1 = 0.0;
                    for (double val : sysTry.F) f1 += val * val;
                    f1 = std::sqrt(f1);
                    if (f1 <= f0 * (1.0 + 1e-10) || lambda < 1e-4) {
                        trialNodeV = std::move(tV);
                        trialBranchI = std::move(tI);
                        accepted = true;
                        break;
                    }
                    lambda *= 0.5;
                }
                (void)accepted;

                double maxDx = 0.0;
                for (uint32_t i = 1; i <= numNodes && (i - 1) < x.size(); ++i)
                    maxDx = std::max(maxDx, std::fabs(lambda * x[i - 1]));

                if (maxDx < 1e-9) { localConv = true; break; }
            }
            (void)localConv;
        }

        nodeV = trialNodeV;
        branchI = trialBranchI;

        updateDeviceStates(devices, nodeV, prevNodeV, t, dt, config.method);
        prevNodeV = nodeV;

        if (step == numSteps) xFinal = buildSol();
    }
    return true;
}

} // namespace

ShootingResult solveShooting(uint32_t numNodes,
                             const std::vector<std::unique_ptr<DeviceModel>>& devices,
                             const ShootingConfig& config,
                             const std::vector<double>* dcOpNodeV,
                             const ShootingOptions& opts) {
    ShootingResult r;
    SteadyTimer tWall;
    BenchCounters* bench = benchJsonEnabled() ? &r.bench : nullptr;
    uint32_t numVS = countVoltageSources(devices);
    uint32_t dim = numNodes + numVS;
    if (dim == 0) {
        r.diags.error({}, "shooting: empty system");
        if (bench) bench->wall_ms = tWall.elapsedMs();
        return r;
    }

    // 初始猜测
    std::vector<double> nodeV(numNodes + 1, 0.0);
    if (dcOpNodeV && dcOpNodeV->size() > numNodes) {
        for (uint32_t i = 0; i <= numNodes; ++i) nodeV[i] = (*dcOpNodeV)[i];
    } else {
        for (uint32_t i = 0; i <= numNodes; ++i) nodeV[i] = 0.0;
    }

    // 跨分析重置 OSDI limiting，避免上一次 DC/HB 求解的 limiting 锚点污染
    // shooting 的内层 transient evalTransient。
    auto resetAllLimiting = [&]() {
        for (const auto& d : devices)
            if (auto* o = dynamic_cast<OsdiModel*>(d.get())) o->resetLimiting();
    };
    resetAllLimiting();

    std::vector<double> y(dim, 0.0);
    for (uint32_t i = 1; i <= numNodes; ++i) y[i - 1] = nodeV[i];
    // 分支电流初始为 0

    double T = 1.0 / config.fundamental;
    uint32_t numSteps = config.numTimePoints ? config.numTimePoints : 100;
    double dt = T / static_cast<double>(numSteps);

    std::vector<std::vector<double>> savedStates;
    saveDeviceStates(devices, savedStates);

    // V2-γ C4: 分段 chrono 计时（仅 bench 模式），定位 Shooting wall 热点
    double tIntegrate = 0.0, tFDJacobian = 0.0, tKluOuter = 0.0, tNewtonOuter = 0.0;
    uint64_t nIntegrations = 0;  // 含标称 + FD 扰动

    // V3-L0: 持久化 TransientSystem，让 pattern 固化跨 integrateOnePeriod 复用。
    // 首次 assembleTransient 建 pattern + commit + bind 指针，后续 zeroCommitted + O(1) stamp。
    TransientSystem sysShared;

    // Stagnant/floor 历史记录（P1-7）：在外层 Newton 监测 ‖F‖ 序列，及早
    // 退出无效迭代。仅在 outer 级做检测——inner Newton（integrateOnePeriod）
    // 必须保持主路径与 FD 扰动路径决策一致，不能引入此类提前退出。
    std::vector<double> fNormHistory;
    fNormHistory.reserve(opts.maxIter);

    for (uint32_t iter = 0; iter < opts.maxIter; ++iter) {
        r.iterations = iter + 1;
        SteadyTimer tIter;

        // 从当前 y 恢复节点电压
        for (uint32_t i = 1; i <= numNodes; ++i) nodeV[i] = y[i - 1];

        // 标称积分
        std::vector<double> xT;
        restoreDeviceStates(devices, savedStates);
        resetAllLimiting();   // 让积分从同一 limiting 锚点起步
        SteadyTimer tInt;
        if (!integrateOnePeriod(numNodes, devices, nodeV, config, opts, xT, r.diags, sysShared)) {
            restoreDeviceStates(devices, savedStates);
            if (bench) { bench->wall_ms = tWall.elapsedMs(); bench->newton_iter = r.iterations; bench->peak_rss_mb = currentRssMb(); }
            return r;
        }
        if (bench) { tIntegrate += tInt.elapsedMs(); ++nIntegrations; }

        // 保存本轮周期末的内部状态，作为下一轮/下一次扰动的初始猜测
        // 这样内部状态也参与 Shooting 不动点迭代。
        saveDeviceStates(devices, savedStates);

        // 残差 F = xT - y
        Vector F(dim);
        for (uint32_t i = 0; i < dim; ++i) F[i] = xT[i] - y[i];
        double fNorm = 0.0;
        for (double v : F) fNorm += v * v;
        fNorm = std::sqrt(fNorm);
        if (opts.verbose) {
            std::cerr << "[Shooting] iter=" << iter << " fNorm=" << fNorm << "\n";
            if (iter == 0) {
                std::cerr << "[Shooting] y=";
                for (double v : y) std::cerr << v << " ";
                std::cerr << "\n[Shooting] xT=";
                for (double v : xT) std::cerr << v << " ";
                std::cerr << "\n";
            }
        }
        if (fNorm < opts.abstol) {
            r.converged = true;
            break;
        }

        // P1-7 stagnant/floor 检测：连续 K 次迭代 ‖F‖ 几乎不变（比例>0.999）
        // 且已过最小观察期 → 早退出。protect against:
        //   - limiting 锚点导致的固有残差 floor（Newton 永远卡在某个非零值）
        //   - 雅可比病态导致的微步徘徊（无可见进展）
        // K=5 / 比例 0.999 / 最小迭代 10 的设置较保守，宁可多迭代几次也不
        // 在临界点误退出。
        fNormHistory.push_back(fNorm);
        if (fNormHistory.size() >= 6 && iter >= 10) {
            size_t n = fNormHistory.size();
            bool stagnant = true;
            for (size_t k = n - 5; k < n; ++k) {
                if (fNormHistory[k] < fNormHistory[k - 1] * 0.999) {
                    stagnant = false;
                    break;
                }
            }
            if (stagnant) {
                r.diags.warn({}, "shooting: outer Newton stagnant at fNorm=" +
                                 std::to_string(fNorm) +
                                 " after " + std::to_string(iter + 1) +
                                 " iterations; breaking early");
                break;
            }
        }

        // 有限差分构造 Jacobian J = dxT/dy
        SteadyTimer tFD;
        std::vector<double> J(dim * dim, 0.0);

        // V3-L2: 预扫描线性节点——只被线性器件触及的节点列跳过 FD 积分。
        // 仅当电路含非线性器件时启用：纯线性电路的 monodromy 不是 -1，不能跳过。
        bool hasNonlinear = false;
        for (const auto& dev : devices)
            if (!dev->is_linear()) { hasNonlinear = true; break; }
        std::vector<bool> nodeIsLinear(numNodes + 1, true);
        if (hasNonlinear) {
            for (const auto& dev : devices) {
                if (!dev->is_linear()) {
                    for (NodeId n : dev->nodes())
                        if (n != 0 && n <= numNodes) nodeIsLinear[n] = false;
                }
            }
        } else {
            // 纯线性电路：所有节点都需要 FD
            std::fill(nodeIsLinear.begin(), nodeIsLinear.end(), false);
        }

        for (uint32_t col = 0; col < dim; ++col) {
            // V3-L2: 线性节点列跳过 FD 积分
            if (col < numNodes && nodeIsLinear[col + 1]) {
                J[col * dim + col] = -1.0;
                continue;
            }
            // 扰动 y[col]
            std::vector<double> yPert = y;
            double eps = opts.epsilon;
            if (col < numNodes) {
                // 节点电压扰动
                yPert[col] += eps;
            } else {
                // 分支电流扰动不影响积分，但影响残差
                // Jacobian 列 = 0，对角为 -1
                J[col * dim + col] = -1.0;
                continue;
            }

            std::vector<double> nodeVPert = nodeV;
            nodeVPert[col + 1] += eps;

            std::vector<double> xTPert;
            restoreDeviceStates(devices, savedStates);
            resetAllLimiting();   // FD 扰动从同一 limiting 锚点起步，消除噪声
            SteadyTimer tInt2;
            if (!integrateOnePeriod(numNodes, devices, nodeVPert, config, opts, xTPert, r.diags, sysShared)) {
                restoreDeviceStates(devices, savedStates);
                if (bench) { bench->wall_ms = tWall.elapsedMs(); bench->newton_iter = r.iterations; bench->peak_rss_mb = currentRssMb(); }
                return r;
            }
            if (bench) { tIntegrate += tInt2.elapsedMs(); ++nIntegrations; }
            for (uint32_t row = 0; row < dim; ++row) {
                J[row * dim + col] = (xTPert[row] - xT[row]) / eps;
            }
        }
        if (bench) tFDJacobian += tFD.elapsedMs();
        // 分支电流列已填好；对节点电压列，残差对 y 还有 -I 项
        for (uint32_t col = 0; col < numNodes; ++col) {
            J[col * dim + col] -= 1.0;
        }

        // 解 J * dy = -F
        SparseMatrix Jsparse(dim);
        for (uint32_t i = 0; i < dim; ++i) {
            for (uint32_t j = 0; j < dim; ++j) {
                double v = J[i * dim + j];
                if (std::fabs(v) > 1e-30) {
                    Jsparse.addPattern(i, j);
                    Jsparse.add(i, j, v);
                }
            }
        }
        Jsparse.finalize();
        // 外层 monodromy 雅可比：稀疏稠密混合（含 ∂x_T/∂x_0），KLU 仍是合理选择。
        SteadyTimer tKlu;
        KluSolver jsolver;
        if (!jsolver.factorize(Jsparse)) {
            r.diags.error({}, "shooting: Jacobian KLU failed");
            if (bench) tKluOuter += tKlu.elapsedMs();
            break;
        }
        Vector negF(dim);
        for (uint32_t i = 0; i < dim; ++i) negF[i] = -F[i];
        Vector dy;
        jsolver.solve(negF, dy);
        if (bench) {
            tKluOuter += tKlu.elapsedMs();
            bench->klu_factor_ms += jsolver.factorMs();
            bench->klu_solve_ms  += jsolver.solveMs();
        }

        // 阻尼更新
        double alpha = 1.0;
        double dyMax = 0.0;
        for (double v : dy) dyMax = std::max(dyMax, std::fabs(v));
        if (dyMax > 0.0) alpha = std::min(1.0, opts.dvmax / dyMax);

        std::vector<double> yNew = y;
        for (uint32_t i = 0; i < dim; ++i) yNew[i] += alpha * dy[i];

        // 简单的回溯：若残差上升则减小 alpha
        for (int bt = 0; bt < 10; ++bt) {
            for (uint32_t i = 1; i <= numNodes; ++i) nodeV[i] = yNew[i - 1];
            std::vector<double> xTtrial;
            restoreDeviceStates(devices, savedStates);
            resetAllLimiting();   // 每次试探从同一 limiting 锚点起步
            SteadyTimer tInt3;
            if (!integrateOnePeriod(numNodes, devices, nodeV, config, opts, xTtrial, r.diags, sysShared)) {
                if (bench) { tIntegrate += tInt3.elapsedMs(); ++nIntegrations; }
                alpha *= 0.5;
                yNew = y;
                for (uint32_t i = 0; i < dim; ++i) yNew[i] += alpha * dy[i];
                continue;
            }
            if (bench) { tIntegrate += tInt3.elapsedMs(); ++nIntegrations; }
            double fTrial = 0.0;
            for (uint32_t i = 0; i < dim; ++i) {
                double d = xTtrial[i] - yNew[i];
                fTrial += d * d;
            }
            fTrial = std::sqrt(fTrial);
            if (fTrial <= fNorm * (1.0 + 1e-10) || alpha < 1e-6) break;
            alpha *= 0.5;
            yNew = y;
            for (uint32_t i = 0; i < dim; ++i) yNew[i] += alpha * dy[i];
        }
        y = yNew;
        if (bench) tNewtonOuter += tIter.elapsedMs();
    }

    // 最终积分，保存波形
    // 确保使用最后一个周期末的内部状态，使波形从周期稳态开始。
    restoreDeviceStates(devices, savedStates);
    resetAllLimiting();
    for (uint32_t i = 1; i <= numNodes; ++i) nodeV[i] = y[i - 1];

    // 使用 time_stepper 生成完整波形
    TimeStepperOptions tsOpts;
    tsOpts.tstop = T;
    tsOpts.dt = dt;
    tsOpts.method = config.method;
    r.waveform = integrateTransient(numNodes, devices, nodeV, tsOpts);

    restoreDeviceStates(devices, savedStates);
    if (bench) {
        bench->wall_ms = tWall.elapsedMs();
        bench->newton_iter = r.iterations;
        bench->peak_rss_mb = currentRssMb();
        // C4 分段计时报告：定位 Shooting wall 热点
        std::fprintf(stderr,
            "[bench.Shooting] iters=%u integrations=%llu  "
            "tIntegrate=%.1fms tFDJacobian=%.1fms tKluOuter=%.1fms "
            "tNewtonOuter=%.1fms wall=%.1fms\n",
            r.iterations, (unsigned long long)nIntegrations,
            tIntegrate, tFDJacobian, tKluOuter, tNewtonOuter, bench->wall_ms);
    }
    return r;
}

HbResult shootingToHarmonics(const ShootingResult& sr,
                             uint32_t numNodes,
                             uint32_t numHarmonics,
                             double fundamental) {
    HbResult r;
    r.config.fundamental = fundamental;
    r.config.numHarmonics = numHarmonics;
    r.nodeVoltages.assign(numNodes + 1, NodeHarmonics{});
    for (auto& nh : r.nodeVoltages) nh.v.assign(numHarmonics + 1, Complex(0, 0));

    // 采样点数：waveform.points 来自 integrateTransient 在 [0, T] 上
    // 用 dt = T/numTimePoints 积分 numTimePoints 步，得到 numTimePoints+1 个点
    // （含 t=0 和 t=T，二者对周期函数等价）。FFT 时只用前 numTimePoints 个点
    // 覆盖一个完整周期。
    const auto& pts = sr.waveform.points;
    if (pts.empty()) {
        r.diags.errors.push_back({SourceLoc{}, "shooting->harmonics: empty waveform"});
        r.ok = false;
        return r;
    }
    uint32_t N = static_cast<uint32_t>(pts.size());
    // 若最后一个点是 T 时刻（与 t=0 等价），舍弃避免重复计入
    if (N >= 2) {
        double t0 = pts.front().time;
        double tN = pts.back().time;
        double T = 1.0 / fundamental;
        if (std::abs((tN - t0) - T) < 0.5 * T / N) {
            N -= 1;
        }
    }
    uint32_t needed = 2u * (numHarmonics + 1);
    if (N < needed) {
        std::ostringstream oss;
        oss << "shooting->harmonics: 采样点数 " << N << " < 2*(NH+1)=" << needed;
        r.diags.errors.push_back({SourceLoc{}, oss.str()});
        r.ok = false;
        return r;
    }

    // 抽取每个非地节点的实数采样并 DFT
    std::vector<double> samples(N, 0.0);
    for (uint32_t nodeId = 1; nodeId <= numNodes; ++nodeId) {
        for (uint32_t n = 0; n < N; ++n) {
            // TimePoint::x 大小 = numNodes + numBranches；前 numNodes 个为节点电压
            const auto& xv = pts[n].x;
            samples[n] = (nodeId - 1u) < xv.size() ? xv[nodeId - 1u] : 0.0;
        }
        r.nodeVoltages[nodeId].v = realSamplesToHarmonics(samples, numHarmonics);
    }
    r.ok = true;
    return r;
}

} // namespace rfsim
