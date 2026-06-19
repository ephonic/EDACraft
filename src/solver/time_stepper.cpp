// time_stepper.cpp — 固定步长时域积分器
#include "time_stepper.hpp"
#include "../assembly/lu_solver.hpp"
#include "../model/builtin_devices.hpp"

#include <cmath>

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
        if (d->hasTransientState()) d->updateTransientState(op);
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

    auto buildSol = [&]() {
        std::vector<double> s(dim, 0.0);
        for (uint32_t i = 1; i <= numNodes; ++i) s[i - 1] = nodeV[i];
        for (uint32_t i = 0; i < r.numBranches; ++i) s[numNodes + i] = branchI[i];
        return s;
    };

    // 用 DC 工作点初始化所有动态器件状态
    initializeDeviceStates(devices, nodeV);

    // 起始点 t=0
    r.points.push_back({0.0, buildSol()});

    uint32_t numSteps = static_cast<uint32_t>(std::round(opts.tstop / opts.dt));
    if (numSteps == 0) numSteps = 1;
    double dt = opts.tstop / static_cast<double>(numSteps);

    std::vector<double> prevNodeV = nodeV;

    for (uint32_t step = 1; step <= numSteps; ++step) {
        double t = step * dt;
        std::vector<double> trialNodeV = nodeV;
        std::vector<double> trialBranchI = branchI;

        // 每个时间步内部做 Newton 迭代，以处理非线性器件
        bool localConv = false;
        for (uint32_t lit = 0; lit < 10; ++lit) {
            TransientSystem sys;
            if (!assembleTransient(numNodes, devices, trialNodeV, prevNodeV, t, dt, opts.method,
                                   sys, r.diags)) {
                r.diags.error({}, "transient assembly failed at t=" + std::to_string(t));
                return r;
            }

            // 添加 gmin 旁路（提高可解性）
            if (opts.gmin != 0.0) {
                for (uint32_t i = 0; i < numNodes; ++i) {
                    sys.G.addPattern(i, i);
                    sys.G.add(i, i, opts.gmin);
                    sys.F[i] += opts.gmin * trialNodeV[i + 1];
                }
                sys.G.finalize();
            }

            LuSolver solver;
            if (!solver.factorize(sys.G)) {
                r.diags.error({}, "transient LU factorization failed at t=" + std::to_string(t));
                return r;
            }
            Vector negF(sys.F.size());
            for (size_t i = 0; i < sys.F.size(); ++i) negF[i] = -sys.F[i];
            Vector x;
            solver.solve(negF, x);

            double maxDx = 0.0;
            for (uint32_t i = 1; i <= numNodes && (i - 1) < x.size(); ++i) {
                trialNodeV[i] += x[i - 1];
                maxDx = std::max(maxDx, std::fabs(x[i - 1]));
            }
            for (uint32_t i = 0; i < r.numBranches && (numNodes + i) < x.size(); ++i)
                trialBranchI[i] += x[numNodes + i];

            if (maxDx < 1e-9) { localConv = true; break; }
        }
        (void)localConv;

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
