// dc_sweep.cpp — DC 扫描实现
#include "dc_sweep.hpp"

#include <cmath>

namespace rfsim {

namespace {

// 按名查找并设置电压源/电流源的值。返回是否找到。
bool setSourceValue(const std::string& name, double value,
                    std::vector<std::unique_ptr<DeviceModel>>& devices) {
    for (auto& d : devices) {
        if (d->name() != name) continue;
        // 通过重建对应 wrapper 设值（wrapper 当前为值类型，无 setter）。
        // 这里用 dynamic_cast + const_cast 不优雅；改用替换实例。
        auto& nodes = const_cast<std::vector<NodeId>&>(d->nodes());
        if (auto* v = dynamic_cast<VoltageSource*>(d.get())) {
            auto nd = std::make_unique<VoltageSource>(v->name(), nodes[0], nodes[1], value);
            d = std::move(nd);
            return true;
        }
        if (auto* i = dynamic_cast<CurrentSource*>(d.get())) {
            auto nd = std::make_unique<CurrentSource>(i->name(), nodes[0], nodes[1], value);
            d = std::move(nd);
            return true;
        }
    }
    return false;
}

} // namespace

DcSweepResult solveDcSweep(uint32_t numNodes,
                           std::vector<std::unique_ptr<DeviceModel>>& devices,
                           const DcSweepSpec& spec) {
    DcSweepResult r;
    r.sweepSourceName = spec.sourceName;

    double step = std::fabs(spec.step);
    if (step == 0.0) {
        r.diags.error({}, ".dc sweep: step is zero");
        return r;
    }
    bool ascending = spec.stop >= spec.start;
    double dir = ascending ? 1.0 : -1.0;

    // 扫描点数（含两端）
    int npts = static_cast<int>(std::floor(std::fabs(spec.stop - spec.start) / step + 0.5)) + 1;
    if (npts < 1) npts = 1;
    if (npts > 1000000) { r.diags.error({}, ".dc sweep: too many points"); return r; }

    r.points.reserve(npts);
    for (int k = 0; k < npts; ++k) {
        double val = spec.start + dir * step * k;
        // 到达 stop 停止（避免浮点越过）
        if (ascending && val > spec.stop + step * 0.5) break;
        if (!ascending && val < spec.stop - step * 0.5) break;

        if (!setSourceValue(spec.sourceName, val, devices)) {
            r.diags.error({}, ".dc sweep: source '" + spec.sourceName + "' not found");
            return r;
        }
        auto dc = solveDcOp(numNodes, devices);
        if (!dc.converged) {
            r.diags.error({}, ".dc sweep: no convergence at " + spec.sourceName + "=" +
                          std::to_string(val));
            // 仍记录该点（NaN 或上一点的值）；此处跳过
            continue;
        }
        DcSweepPoint p;
        p.sweepValue = val;
        p.nodeVoltages = dc.nodeVoltages;
        r.points.push_back(std::move(p));
    }

    r.ok = !r.points.empty() && !r.diags.has_errors();
    return r;
}

} // namespace rfsim
