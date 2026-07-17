// mna.cpp — MNA 装配实现
#include "mna.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/osdi_model.hpp"
#include "../model/sparam_device.hpp"

namespace rfsim {

namespace {

// 收集电压源，确定分支数
uint32_t countVoltageSources(const std::vector<std::unique_ptr<DeviceModel>>& devices,
                             std::vector<uint32_t>& vsIdx) {
    uint32_t cnt = 0;
    for (uint32_t i = 0; i < devices.size(); ++i) {
        if (dynamic_cast<VoltageSource*>(devices[i].get())) {
            vsIdx.push_back(i);
            ++cnt;
        }
    }
    return cnt;
}

} // namespace

AssembleResult assembleMna(uint32_t numNodes,
                           const std::vector<std::unique_ptr<DeviceModel>>& devices,
                           const std::vector<double>* nodeVoltages) {
    AssembleResult r;
    std::vector<uint32_t> vsIdx;
    uint32_t numVS = countVoltageSources(devices, vsIdx);
    uint32_t n = numNodes + numVS;

    r.system.numNodes = numNodes;
    r.system.numBranches = numVS;
    r.system.G.resize(n);
    r.system.b.assign(n, 0.0);

    // 分配电压源分支偏移
    r.vsBranchOffsets.clear();
    for (uint32_t k = 0; k < numVS; ++k) {
        r.vsBranchOffsets.push_back(numNodes + k);  // 第 k 个电压源的分支电流在未知数 numNodes+k
    }

    // 声明模式 + stamp 线性器件
    for (uint32_t di = 0; di < devices.size(); ++di) {
        const auto& dev = devices[di];
        const auto& nodes = dev->nodes();

        // 电阻：stamp 导纳
        if (auto* res = dynamic_cast<Resistor*>(dev.get())) {
            double g = res->conductance();
            uint32_t n1 = nodes.size() > 0 ? nodes[0] : 0;
            uint32_t n2 = nodes.size() > 1 ? nodes[1] : 0;
            // 地节点(0)不进矩阵；非地节点才 stamp
            if (n1 != 0) { r.system.G.addPattern(n1 - 1, n1 - 1); r.system.G.add(n1 - 1, n1 - 1, g); }
            if (n2 != 0) { r.system.G.addPattern(n2 - 1, n2 - 1); r.system.G.add(n2 - 1, n2 - 1, g); }
            if (n1 != 0 && n2 != 0) {
                r.system.G.addPattern(n1 - 1, n2 - 1); r.system.G.add(n1 - 1, n2 - 1, -g);
                r.system.G.addPattern(n2 - 1, n1 - 1); r.system.G.add(n2 - 1, n1 - 1, -g);
            }
            continue;
        }

        // 电流源：stamp RHS
        if (auto* cs = dynamic_cast<CurrentSource*>(dev.get())) {
            double I = cs->current();
            uint32_t n1 = nodes.size() > 0 ? nodes[0] : 0;
            uint32_t n2 = nodes.size() > 1 ? nodes[1] : 0;
            if (n1 != 0) r.system.b[n1 - 1] += I;
            if (n2 != 0) r.system.b[n2 - 1] -= I;
            continue;
        }

        // 电压源：分支电流扩维 stamp
        if (dynamic_cast<VoltageSource*>(dev.get())) {
            // 找到这是第几个电压源
            uint32_t branchIdx = 0;
            for (uint32_t k = 0; k < vsIdx.size(); ++k) {
                if (vsIdx[k] == di) { branchIdx = numNodes + k; break; }
            }
            uint32_t n1 = nodes.size() > 0 ? nodes[0] : 0;
            uint32_t n2 = nodes.size() > 1 ? nodes[1] : 0;
            double V = dynamic_cast<VoltageSource*>(dev.get())->voltage();
            // MNA stamp: KCL 加入分支电流 i_b
            //   行 n1: +i_b  → G[n1, b]+=1
            //   行 n2: -i_b  → G[n2, b]-=1
            //   行 b:  v_n1 - v_n2 = V → G[b,n1]+=1, G[b,n2]-=1, b_rhs=V
            if (n1 != 0) {
                r.system.G.addPattern(n1 - 1, branchIdx); r.system.G.add(n1 - 1, branchIdx, 1.0);
                r.system.G.addPattern(branchIdx, n1 - 1); r.system.G.add(branchIdx, n1 - 1, 1.0);
            }
            if (n2 != 0) {
                r.system.G.addPattern(n2 - 1, branchIdx); r.system.G.add(n2 - 1, branchIdx, -1.0);
                r.system.G.addPattern(branchIdx, n2 - 1); r.system.G.add(branchIdx, n2 - 1, -1.0);
            }
            r.system.G.addPattern(branchIdx, branchIdx); r.system.G.add(branchIdx, branchIdx, 0.0);
            r.system.b[branchIdx] = V;
            continue;
        }

        // 电容 C: DC 开路，不 stamp 导纳（0 电流）。AC 由频域装配处理。
        if (dynamic_cast<Capacitor*>(dev.get())) {
            continue;
        }

        // 电感 L: DC 短路，用极小电阻近似（G=1e6）保证连通，避免奇异
        if (dynamic_cast<Inductor*>(dev.get())) {
            double g = 1e6;  // 1/(1μΩ) 近似短路
            uint32_t n1 = nodes.size() > 0 ? nodes[0] : 0;
            uint32_t n2 = nodes.size() > 1 ? nodes[1] : 0;
            if (n1 != 0 && n2 != 0) {
                r.system.G.addPattern(n1 - 1, n1 - 1); r.system.G.add(n1 - 1, n1 - 1, g);
                r.system.G.addPattern(n2 - 1, n2 - 1); r.system.G.add(n2 - 1, n2 - 1, g);
                r.system.G.addPattern(n1 - 1, n2 - 1); r.system.G.add(n1 - 1, n2 - 1, -g);
                r.system.G.addPattern(n2 - 1, n1 - 1); r.system.G.add(n2 - 1, n1 - 1, -g);
            } else if (n1 != 0) {
                r.system.G.addPattern(n1 - 1, n1 - 1); r.system.G.add(n1 - 1, n1 - 1, g);
            } else if (n2 != 0) {
                r.system.G.addPattern(n2 - 1, n2 - 1); r.system.G.add(n2 - 1, n2 - 1, g);
            }
            continue;
        }

        // S 参数器件: DC 使用 Y(ω→0) 的实部作为电导
        if (auto* sp = dynamic_cast<SParamDevice*>(dev.get())) {
            auto Y = sp->dcAdmittanceMatrix();
            uint32_t N = sp->numPorts();

            // Stamp N×N Y 矩阵到 MNA（取实部作为电导）
            for (uint32_t i = 0; i < N; ++i) {
                uint32_t ni = nodes.size() > i ? nodes[i] : 0;
                if (ni == 0) continue;  // 地节点跳过

                for (uint32_t j = 0; j < N; ++j) {
                    uint32_t nj = nodes.size() > j ? nodes[j] : 0;
                    if (nj == 0) continue;  // 地节点跳过

                    double g = Y[i * N + j].real();
                    r.system.G.addPattern(ni - 1, nj - 1);
                    r.system.G.add(ni - 1, nj - 1, g);
                }
            }
            continue;
        }

        // 非线性器件(OSDI)：DC 阶段若提供工作点则 stamp 雅可比，否则用 1e-12 Gmin 保险
        // M2 暂不实现非线性 stamp（待 OSDI 库接入校准后）
    }

    r.system.G.finalize();
    r.ok = !r.diags.has_errors();
    return r;
}

void reassemble(MnaSystem& sys,
                const std::vector<std::unique_ptr<DeviceModel>>& devices,
                const std::vector<double>& nodeVoltages,
                const std::vector<uint32_t>& vsBranchOffsets) {
    // 清零值保留模式，重新 stamp
    sys.G.zeroValues();
    std::fill(sys.b.begin(), sys.b.end(), 0.0);

    // 复用 assembleMna 的 stamp 逻辑（线性器件导纳不变，RHS 重置）
    // 此处简化：对线性器件重新 stamp（与首次相同）；非线性器件按工作点 stamp。
    (void)nodeVoltages; (void)vsBranchOffsets;
    // TODO: 非线性 Newton 重装配
}

} // namespace rfsim
