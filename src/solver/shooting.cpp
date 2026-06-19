// shooting.cpp — Single Shooting 周期稳态求解器
#include "shooting.hpp"
#include "../assembly/lu_solver.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"

#include <cmath>
#include <iostream>

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
                        Diagnostics& diags) {
    uint32_t numVS = countVoltageSources(devices);
    uint32_t dim = numNodes + numVS;
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

    for (uint32_t step = 1; step <= numSteps; ++step) {
        double t = step * dt;
        std::vector<double> trialNodeV = nodeV;
        std::vector<double> trialBranchI = branchI;

        // 每个时间步内部做 Newton 迭代，以处理非线性器件
        bool localConv = false;
        uint32_t localMaxIter = opts.localNewtonMaxIter > 0 ? opts.localNewtonMaxIter : 50;
        for (uint32_t lit = 0; lit < localMaxIter; ++lit) {
            TransientSystem sys;
            if (!assembleTransient(numNodes, devices, trialNodeV, prevNodeV, t, dt, config.method,
                                   sys, diags)) {
                diags.error({}, "shooting: transient assembly failed");
                return false;
            }
            // 加 gmin 旁路提高非线性/开关电路的可解性
            const double gmin = 1e-12;
            for (uint32_t i = 0; i < numNodes; ++i) {
                sys.G.addPattern(i, i);
                sys.G.add(i, i, gmin);
                sys.F[i] += gmin * trialNodeV[i + 1];
            }
            sys.G.finalize();

            LuSolver solver;
            if (!solver.factorize(sys.G)) {
                diags.error({}, "shooting: LU factorization failed");
                return false;
            }
            Vector negF(sys.F.size());
            for (size_t i = 0; i < sys.F.size(); ++i) negF[i] = -sys.F[i];
            Vector x;
            solver.solve(negF, x);

            bool hasNan = false;
            for (double val : x) if (std::isnan(val) || std::isinf(val)) { hasNan = true; break; }
            if (hasNan) {
                std::cerr << "[shooting debug] NaN update at t=" << t
                          << " step=" << step << " lit=" << lit << "\n";
                std::cerr << "  trialNodeV=";
                for (uint32_t i = 1; i <= numNodes && i < trialNodeV.size(); ++i)
                    std::cerr << trialNodeV[i] << " ";
                std::cerr << "\n  sys.F=";
                for (double val : sys.F) std::cerr << val << " ";
                std::cerr << "\n";
                diags.error({}, "shooting: NaN/Inf in Newton update at t=" + std::to_string(t));
                return false;
            }

            // 局部 Newton 回溯线搜索：若全步导致残差增大则收缩步长
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
                const double gmin = 1e-12;
                for (uint32_t i = 0; i < numNodes; ++i) {
                    sysTry.G.addPattern(i, i);
                    sysTry.G.add(i, i, gmin);
                    sysTry.F[i] += gmin * tV[i + 1];
                }
                sysTry.G.finalize();

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
    uint32_t numVS = countVoltageSources(devices);
    uint32_t dim = numNodes + numVS;
    if (dim == 0) {
        r.diags.error({}, "shooting: empty system");
        return r;
    }

    // 初始猜测
    std::vector<double> nodeV(numNodes + 1, 0.0);
    if (dcOpNodeV && dcOpNodeV->size() > numNodes) {
        for (uint32_t i = 0; i <= numNodes; ++i) nodeV[i] = (*dcOpNodeV)[i];
    } else {
        for (uint32_t i = 0; i <= numNodes; ++i) nodeV[i] = 0.0;
    }

    std::vector<double> y(dim, 0.0);
    for (uint32_t i = 1; i <= numNodes; ++i) y[i - 1] = nodeV[i];
    // 分支电流初始为 0

    double T = 1.0 / config.fundamental;
    uint32_t numSteps = config.numTimePoints ? config.numTimePoints : 100;
    double dt = T / static_cast<double>(numSteps);

    std::vector<std::vector<double>> savedStates;
    saveDeviceStates(devices, savedStates);

    for (uint32_t iter = 0; iter < opts.maxIter; ++iter) {
        r.iterations = iter + 1;

        // 从当前 y 恢复节点电压
        for (uint32_t i = 1; i <= numNodes; ++i) nodeV[i] = y[i - 1];

        // 标称积分
        std::vector<double> xT;
        restoreDeviceStates(devices, savedStates);
        if (!integrateOnePeriod(numNodes, devices, nodeV, config, opts, xT, r.diags)) {
            restoreDeviceStates(devices, savedStates);
            return r;
        }

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

        // 有限差分构造 Jacobian J = dxT/dy
        std::vector<double> J(dim * dim, 0.0);
        for (uint32_t col = 0; col < dim; ++col) {
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
            if (!integrateOnePeriod(numNodes, devices, nodeVPert, config, opts, xTPert, r.diags)) {
                restoreDeviceStates(devices, savedStates);
                return r;
            }
            for (uint32_t row = 0; row < dim; ++row) {
                J[row * dim + col] = (xTPert[row] - xT[row]) / eps;
            }
        }
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
        LuSolver jsolver;
        if (!jsolver.factorize(Jsparse)) {
            r.diags.error({}, "shooting: Jacobian LU failed");
            break;
        }
        Vector negF(dim);
        for (uint32_t i = 0; i < dim; ++i) negF[i] = -F[i];
        Vector dy;
        jsolver.solve(negF, dy);

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
            if (!integrateOnePeriod(numNodes, devices, nodeV, config, opts, xTtrial, r.diags)) {
                alpha *= 0.5;
                yNew = y;
                for (uint32_t i = 0; i < dim; ++i) yNew[i] += alpha * dy[i];
                continue;
            }
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
    }

    // 最终积分，保存波形
    // 确保使用最后一个周期末的内部状态，使波形从周期稳态开始。
    restoreDeviceStates(devices, savedStates);
    for (uint32_t i = 1; i <= numNodes; ++i) nodeV[i] = y[i - 1];

    // 使用 time_stepper 生成完整波形
    TimeStepperOptions tsOpts;
    tsOpts.tstop = T;
    tsOpts.dt = dt;
    tsOpts.method = config.method;
    r.waveform = integrateTransient(numNodes, devices, nodeV, tsOpts);

    restoreDeviceStates(devices, savedStates);
    return r;
}

} // namespace rfsim
