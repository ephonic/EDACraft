// transient_assembly.cpp — 时域瞬态 MNA 装配实现
#include "transient_assembly.hpp"
#include "../model/builtin_devices.hpp"
#include "../model/sparam_device.hpp"

#include <cmath>
#include <cstdio>

namespace rfsim {

namespace {

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

inline double getV(const std::vector<double>& nodeV, NodeId id) {
    return id == 0 ? 0.0 : (id < nodeV.size() ? nodeV[id] : 0.0);
}

} // namespace

bool assembleTransient(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const std::vector<double>& nodeV,
                       const std::vector<double>& prevNodeV,
                       double t,
                       double dt,
                       IntegrationMethod method,
                       TransientSystem& sys,
                       Diagnostics& diags,
                       bool residOnly) {
    (void)diags;
    static thread_local std::vector<uint32_t> vsIdx;
    vsIdx.clear();
    uint32_t numVS = countVoltageSources(devices, vsIdx);
    uint32_t dim = numNodes + numVS;

    sys.numNodes = numNodes;
    sys.numBranches = numVS;
    sys.F.assign(dim, 0.0);

    auto branchIndex = [&](uint32_t deviceIdx) -> uint32_t {
        for (uint32_t k = 0; k < vsIdx.size(); ++k) {
            if (vsIdx[k] == deviceIdx) return numNodes + k;
        }
        return UINT32_MAX;  // L10: 不应到达——非 VS 器件不应调此
    };

    // V3-L0: 两阶段装配。
    // 如果 sys.G 已被外部 commitPattern（如 shooting 的 sysShared），走 fast path：
    //   zeroCommitted + addCommitted（直接写 CSR values_）。
    // 否则走 slow path（原始行为）：resize + addPattern + add + finalize。
    // 注意：assembleTransient 自身不调 commitPattern——由调用方控制固化。
    bool committed = sys.G.patternCommitted();
    if (!committed) {
        sys.G.resize(dim);
        for (uint32_t i = 0; i < numNodes; ++i) sys.G.addPattern(i, i);
    } else {
        sys.G.zeroCommitted();
    }

    // === Stamp（add 自动走 addCommitted 若已 commit）===
    for (uint32_t di = 0; di < devices.size(); ++di) {
        const auto& dev = devices[di];
        const auto& nds = dev->nodes();
        const uint32_t nTerm = static_cast<uint32_t>(nds.size());

        if (auto* res = dynamic_cast<Resistor*>(dev.get())) {
            double g = res->conductance();
            NodeId n1 = nds.size() > 0 ? nds[0] : 0;
            NodeId n2 = nds.size() > 1 ? nds[1] : 0;
            if (n1 != 0) { sys.G.addPattern(n1 - 1, n1 - 1); sys.G.add(n1 - 1, n1 - 1, g); }
            if (n2 != 0) { sys.G.addPattern(n2 - 1, n2 - 1); sys.G.add(n2 - 1, n2 - 1, g); }
            if (n1 != 0 && n2 != 0) {
                sys.G.addPattern(n1 - 1, n2 - 1); sys.G.add(n1 - 1, n2 - 1, -g);
                sys.G.addPattern(n2 - 1, n1 - 1); sys.G.add(n2 - 1, n1 - 1, -g);
            }
            double iR = g * (getV(nodeV, n1) - getV(nodeV, n2));
            if (n1 != 0) sys.F[n1 - 1] += iR;
            if (n2 != 0) sys.F[n2 - 1] -= iR;
            continue;
        }

        if (auto* cs = dynamic_cast<CurrentSource*>(dev.get())) {
            double I = cs->waveform().type == Waveform::DC ? cs->current() : cs->waveform().valueAt(t);
            NodeId n1 = nds.size() > 0 ? nds[0] : 0;
            NodeId n2 = nds.size() > 1 ? nds[1] : 0;
            if (n1 != 0) sys.F[n1 - 1] -= I;
            if (n2 != 0) sys.F[n2 - 1] += I;
            continue;
        }

        if (auto* vs = dynamic_cast<VoltageSource*>(dev.get())) {
            uint32_t br = branchIndex(di);
            NodeId n1 = nds.size() > 0 ? nds[0] : 0;
            NodeId n2 = nds.size() > 1 ? nds[1] : 0;
            double V = vs->waveform().type == Waveform::DC ? vs->voltage() : vs->valueAt(t);
            if (n1 != 0) { sys.G.addPattern(n1 - 1, br); sys.G.add(n1 - 1, br, 1.0); sys.G.addPattern(br, n1 - 1); sys.G.add(br, n1 - 1, 1.0); }
            if (n2 != 0) { sys.G.addPattern(n2 - 1, br); sys.G.add(n2 - 1, br, -1.0); sys.G.addPattern(br, n2 - 1); sys.G.add(br, n2 - 1, -1.0); }
            sys.G.addPattern(br, br);
            sys.F[br] = (getV(nodeV, n1) - getV(nodeV, n2)) - V;
            continue;
        }

        if (dynamic_cast<Capacitor*>(dev.get()) || dynamic_cast<Inductor*>(dev.get())) {
            TransientOpPoint op;
            op.v = nodeV; op.v_prev = prevNodeV;
            op.time = t; op.dt = dt; op.method = method;
            DeviceContribution contrib;
            dev->evalTransient(op, contrib);
            if (contrib.f.size() != nTerm || contrib.jac.size() != nTerm * nTerm) {
                contrib.f.assign(nTerm, 0.0);
                contrib.jac.assign(nTerm * nTerm, 0.0);
            }
            for (uint32_t r = 0; r < nTerm; ++r) {
                NodeId gr = nds[r];
                if (gr == 0) continue;
                sys.F[gr - 1] += contrib.f[r];
                for (uint32_t c = 0; c < nTerm; ++c) {
                    NodeId gc = nds[c];
                    if (gc == 0) continue;
                    sys.G.addPattern(gr - 1, gc - 1);
                    sys.G.add(gr - 1, gc - 1, contrib.jac[r * nTerm + c]);
                }
            }
            continue;
        }

        // SParamDevice: Vector Fitting companion model
        if (auto* sp = dynamic_cast<SParamDevice*>(dev.get())) {
            TransientOpPoint op;
            op.v = nodeV;
            op.v_prev = prevNodeV;
            op.time = t;
            op.dt = dt;
            op.method = method;

            DeviceContribution dc;
            sp->evalTransient(op, dc);

            if (dc.f.size() != nTerm || dc.jac.size() != nTerm * nTerm) {
                dc.f.assign(nTerm, 0.0);
                dc.jac.assign(nTerm * nTerm, 0.0);
            }
            for (uint32_t r = 0; r < nTerm; ++r) {
                NodeId gr = nds[r];
                if (gr == 0) continue;
                sys.F[gr - 1] += dc.f[r];
                for (uint32_t c = 0; c < nTerm; ++c) {
                    NodeId gc = nds[c];
                    if (gc == 0) continue;
                    sys.G.addPattern(gr - 1, gc - 1);
                    sys.G.add(gr - 1, gc - 1, dc.jac[r * nTerm + c]);
                }
            }
            continue;
        }

        // 通用非线性 DeviceModel 路径（Verilog-A 生成模型等）：
        // 上面 dynamic_cast 未命中的非线性器件，走 evalTransient 虚接口装配。
        // 符号约定与 Capacitor/OSDI 一致：F += f（流出节点电流），G += df/dv，
        // jac 按 stamp_pattern entries 顺序对齐。
        if (!dev->is_linear()) {
            TransientOpPoint op;
            op.v = nodeV; op.v_prev = prevNodeV;
            op.time = t; op.dt = dt; op.method = method;
            DeviceContribution dc;
            dev->evalTransient(op, dc);
            for (size_t k = 0; k < nds.size() && k < dc.f.size(); ++k) {
                NodeId nk = nds[k];
                if (nk == 0) continue;
                sys.F[nk - 1] += dc.f[k];
            }
            StampPattern sp;
            dev->stamp_pattern(sp);
            for (size_t e = 0; e < sp.entries.size() && e < dc.jac.size(); ++e) {
                NodeId gr = sp.entries[e].first, gc = sp.entries[e].second;
                if (gr == 0 || gc == 0) continue;
                sys.G.addPattern(gr - 1, gc - 1);
                sys.G.add(gr - 1, gc - 1, dc.jac[e]);
            }
            continue;
        }
    }  // end main device loop

    if (!committed) sys.G.finalize();
    return true;
}

} // namespace rfsim
