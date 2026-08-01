// mor_wrapper.cpp — MOR 集成 wrapper 实现（纯内存模式）
//
// 不经过任何文件 I/O。从仿真器的 DeviceModel 列表提取 R/C → 内存字符串 →
// amor parseFromString → partition → reduction → getReducedRC → 直接生成 DeviceModel。
#include "mor_wrapper.h"
#include "../model/builtin_devices.hpp"

#include <cmath>
#include <sstream>

#ifdef RFSIM_USE_MOR
#include "amor_amor.h"
#include "amor_ckt.h"
#include "amor_element.h"
#include "amor_res.h"
#include "amor_cap.h"
#include "amor_node_list.h"
#include "amor_orth_list.h"
#include "graph.h"

using namespace rfsim::mor;

bool rfsim::runMorReduction(const std::string& inputPath,
                            const std::string& reducedPath,
                            const MorOptions& opts) {
    ::amor am;
    am.set_maxblocksize(opts.maxBlockSize);
    int ret = am.run(inputPath.c_str(), reducedPath.c_str());
    return (ret == 0);
}

bool rfsim::isMorAvailable() { return true; }

// 纯内存降阶：仿真器器件列表 → amor 内存降阶 → 等效 R/C DeviceModel
std::vector<std::unique_ptr<rfsim::DeviceModel>> rfsim::reduceRCDevices(
    const std::vector<std::unique_ptr<DeviceModel>>& devices,
    const Circuit& circuit,
    const std::vector<NodeId>& portNodeIds,
    const MorOptions& opts) {

    // 1. 分离 R/C 和非线性器件
    struct RCEntry { NodeId n1, n2; double val; bool isCap; };
    std::vector<RCEntry> rcList;

    for (const auto& d : devices) {
        if (auto* res = dynamic_cast<Resistor*>(d.get())) {
            const auto& nds = d->nodes();
            rcList.push_back({nds[0], nds[1], res->resistance(), false});
        } else if (auto* cap = dynamic_cast<Capacitor*>(d.get())) {
            const auto& nds = d->nodes();
            rcList.push_back({nds[0], nds[1], cap->capacitance(), true});
        }
    }

    if (rcList.size() < 10) return {};  // 太少不值得降阶

    // 2. 构建内存 SPICE 格式字符串（amor parseFromString 的输入）
    std::ostringstream oss;
    oss << "* MOR inline RC\n";
    // 端口声明
    for (NodeId nid : portNodeIds) {
        if (nid > 0 && nid <= circuit.nodes.size()) {
            oss << "* port " << circuit.nodes.nameOf(nid) << "\n";
        }
    }
    // R/C 器件
    int idx = 0;
    for (const auto& rc : rcList) {
        auto nodeName = [&](NodeId id) -> std::string {
            if (id == 0) return "0";
            if (id <= circuit.nodes.size()) return circuit.nodes.nameOf(id);
            return "n" + std::to_string(id);
        };
        char prefix = rc.isCap ? 'C' : 'R';
        oss << prefix << "mor" << idx << " " << nodeName(rc.n1) << " " << nodeName(rc.n2)
            << " " << std::setprecision(15) << rc.val << "\n";
        ++idx;
    }
    oss << ".end\n";

    // 3. amor 内存降阶（不碰文件）
    ::ckt cktObj;
    cktObj.set_max_blocksize(opts.maxBlockSize);
    cktObj.parseFromString(oss.str());
    cktObj.post_parse();
    cktObj.partition();
    cktObj.reduction();

    // 4. 从降阶矩阵直接提取等效 R/C（不经过 dump_netlist）
    auto reducedRC = cktObj.getReducedRC();

    // 5. 转换为 DeviceModel（Resistor / Capacitor）
    std::vector<std::unique_ptr<DeviceModel>> result;
    int devId = 0;
    for (const auto& rc : reducedRC) {
        // 节点名 → NodeId
        auto resolveNode = [&](const std::string& name) -> NodeId {
            if (name == "0" || name == "gnd" || name == "GND") return 0;
            NodeId id = circuit.nodes.lookup(name);
            return (id == 0xFFFFFFFFu) ? 0 : id;
        };
        NodeId id1 = resolveNode(rc.n1);
        NodeId id2 = resolveNode(rc.n2);

        if (rc.value <= 0 || !std::isfinite(rc.value)) continue;

        try {
            if (rc.isCap) {
                result.push_back(std::make_unique<Capacitor>(
                    "morC" + std::to_string(devId), id1, id2, rc.value));
            } else {
                result.push_back(std::make_unique<Resistor>(
                    "morR" + std::to_string(devId), id1, id2, rc.value));
            }
            ++devId;
        } catch (...) {}
    }

    cktObj.free_subckt_list();
    return result;
}

#else
// 无 MOR 编译：stub
bool rfsim::runMorReduction(const std::string&, const std::string&, const MorOptions&) {
    return false;
}
bool rfsim::isMorAvailable() { return false; }
std::vector<std::unique_ptr<rfsim::DeviceModel>> rfsim::reduceRCDevices(
    const std::vector<std::unique_ptr<rfsim::DeviceModel>>&,
    const rfsim::Circuit&,
    const std::vector<rfsim::NodeId>&,
    const MorOptions&) {
    return {};
}
#endif
