// osdi_model.cpp — OSDI 器件 wrapper 实现
#include "osdi_model.hpp"

#include <cmath>
#include <iostream>

namespace rfsim {

OsdiModel::OsdiModel(std::string name,
                     std::vector<NodeId> nodes,
                     std::shared_ptr<OsdiLibrary> lib,
                     const OsdiDescriptor* descriptor,
                     ParamList instanceParams,
                     ParamList modelParams)
    : name_(std::move(name)),
      nodes_(std::move(nodes)),
      lib_(std::move(lib)),
      descriptor_(descriptor),
      instanceParams_(std::move(instanceParams)),
      modelParams_(std::move(modelParams)),
      modelName_(descriptor ? (descriptor->name ? descriptor->name : "") : "") {}

bool OsdiModel::initialize(Diagnostics& diags, NodeId& internalNodeBase) {
    if (!lib_ || !lib_->loaded()) {
        diags.error({}, name_ + ": OSDI library not loaded");
        return false;
    }
    if (!descriptor_) {
        diags.error({}, name_ + ": null OSDI descriptor");
        return false;
    }

    // 展开内部节点：num_nodes 含外部端子 + 内部隐式方程节点。
    // 外部节点(0..num_terminals-1) 来自构造参数；内部节点分配新全局编号。
    uint32_t nTerm = descriptor_->num_terminals;
    uint32_t nAll = descriptor_->num_nodes;
    if (nodes_.size() < nTerm) {
        // 外部节点不足，补 0（地）
        nodes_.resize(nTerm, 0);
    }
    // 为内部节点(num_terminals..num_nodes-1)分配全局编号
    while (nodes_.size() < nAll) {
        nodes_.push_back(internalNodeBase++);
    }

    // 模型块：同模型多实例共享。此处为简化，每个 OsdiModel 独占一个模型块。
    // M2 优化：在 device_factory 层按模型名缓存共享模型块。
    modelBlock_ = std::make_shared<OsdiModelBlock>();
    modelBlock_->descriptor = descriptor_;

    // 将模型参数转换为可传递的数值对
    std::vector<std::pair<std::string, double>> modelPairs;
    modelPairs.reserve(modelParams_.size());
    for (const auto& [pn, pv] : modelParams_) {
        double val = 0.0;
        if (pv.kind == ParamValue::Kind::Number) {
            val = pv.num;
        } else if (pv.kind == ParamValue::Kind::Expr || pv.kind == ParamValue::Kind::String) {
            try { val = std::stod(pv.str); } catch (...) { continue; }
        }
        modelPairs.emplace_back(pn, val);
    }

    client_ = std::make_unique<OsdiClient>();
    if (!client_->init(lib_, modelBlock_, nodes_, diags, modelPairs)) {
        return false;
    }

    // 处理可折叠节点：setup_instance 后读取 collapsed 数组，把被折叠的内部节点
    // 映射到对应的外部节点（或同一 master 节点），使它们贡献到同一个 MNA 未知量。
    if (descriptor_ && descriptor_->num_collapsible > 0 &&
        descriptor_->collapsed_offset != 0 &&
        descriptor_->collapsed_offset + descriptor_->num_collapsible <= descriptor_->instance_size) {
        const uint8_t* collapsed = reinterpret_cast<const uint8_t*>(
            reinterpret_cast<const char*>(client_->instanceData()) + descriptor_->collapsed_offset);
        for (uint32_t i = 0; i < descriptor_->num_collapsible; ++i) {
            if (!collapsed[i]) continue;
            uint32_t a = descriptor_->collapsible[i].node_1;
            uint32_t b = descriptor_->collapsible[i].node_2;
            if (a >= nodes_.size() || b >= nodes_.size()) continue;
            // 将 b 折叠到 a（a 通常是外部端子或已折叠的 master）
            nodes_[b] = nodes_[a];
        }
    }

    // 绑定实例参数（W/L/M 等）
    for (const auto& [pn, pv] : instanceParams_) {
        double val = 0;
        if (pv.kind == ParamValue::Kind::Number) {
            val = pv.num;
        } else if (pv.kind == ParamValue::Kind::Expr || pv.kind == ParamValue::Kind::String) {
            // 表达式参数：M2 后续接入参数环境求值；当前尝试直接 atof
            try { val = std::stod(pv.str); } catch (...) { continue; }
        }
        client_->setInstanceParam(pn, val);
    }
    return true;
}

void OsdiModel::loadJacobianInto(double** targets, uint32_t /*matDim*/,
                                 const std::vector<uint32_t>& nodeMap) {
    if (client_ && client_->ready()) {
        client_->loadJacobianResistWith(targets, nodeMap);
    }
}

void OsdiModel::evalTimeSamples(const std::vector<std::vector<double>>& timeVoltages,
                                const std::vector<uint32_t>& nodeMap,
                                std::vector<std::vector<double>>& outCurrents) const {
    if (!client_ || !client_->ready()) {
        outCurrents.assign(timeVoltages.size(), std::vector<double>(nodes_.size(), 0.0));
        return;
    }
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
    uint32_t nNodes = descriptor_->num_nodes;
    outCurrents.assign(timeVoltages.size(), std::vector<double>(nNodes, 0.0));
    // evalDC 需要全局节点编号索引的电压向量
    NodeId maxId = 0;
    for (NodeId g : nodes_) if (g > maxId) maxId = g;
    for (size_t s = 0; s < timeVoltages.size(); ++s) {
        // 每次 eval 前重新设置 node_mapping：某些模型可能在 eval 中修改它
        const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
        std::vector<double> globalV(maxId + 1, 0.0);
        bool bad = false;
        for (uint32_t i = 0; i < nNodes && i < timeVoltages[s].size() && i < nodes_.size(); ++i) {
            if (nodes_[i] <= maxId) {
                double vv = timeVoltages[s][i];
                if (std::isnan(vv) || std::isinf(vv) || std::abs(vv) > 100.0) bad = true;
                globalV[nodes_[i]] = vv;
            }
        }
        if (bad) {
            // 模型在极端工作点下可能段错误，跳过该采样
            continue;
        }
        // HB 电流采样不需要雅可比；关闭 CALC_RESIST_JACOBIAN 避免 eval 写入 stale 指针
        uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalDC(globalV, 0, false);
        if (ret & EVAL_RET_FLAG_FATAL) {
            // 模型拒绝该工作点：返回零电流，避免后续崩溃
            continue;
        }
        std::vector<double> resid;
        client_->loadResidualResist(resid);
        for (uint32_t k = 0; k < nNodes && k < resid.size(); ++k) {
            outCurrents[s][k] = resid[k];
        }
    }
}

void OsdiModel::evalTimeJacobians(const std::vector<std::vector<double>>& timeVoltages,
                                  const std::vector<uint32_t>& nodeMap,
                                  std::vector<std::vector<double>>& outJac) const {
    if (!client_ || !client_->ready() || !descriptor_) {
        outJac.assign(timeVoltages.size(),
                      std::vector<double>(descriptor_?descriptor_->num_jacobian_entries:0, 0.0));
        return;
    }
    uint32_t nE = descriptor_->num_jacobian_entries;
    uint32_t nNodes = descriptor_->num_nodes;
    outJac.assign(timeVoltages.size(), std::vector<double>(nE, 0.0));
    NodeId maxId = 0;
    for (NodeId g : nodes_) if (g > maxId) maxId = g;
    for (size_t s = 0; s < timeVoltages.size(); ++s) {
        // 每次 eval 前重新设置 node_mapping 与 jacobian 指针 scratch
        const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
        std::vector<double> globalV(maxId + 1, 0.0);
        bool bad = false;
        for (uint32_t i = 0; i < nNodes && i < timeVoltages[s].size() && i < nodes_.size(); ++i) {
            if (nodes_[i] <= maxId) {
                double vv = timeVoltages[s][i];
                if (std::isnan(vv) || std::isinf(vv) || std::abs(vv) > 100.0) bad = true;
                globalV[nodes_[i]] = vv;
            }
        }
        if (bad) continue;
        uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalDC(globalV);
        if (ret & EVAL_RET_FLAG_FATAL) {
            // 模型拒绝该工作点：保持该采样点的雅可比为零
            continue;
        }
        std::vector<double*> tgt(nE, nullptr);
        for (uint32_t e = 0; e < nE; ++e) tgt[e] = &outJac[s][e];
        client_->loadJacobianResistWith(tgt.data(), nodeMap);
    }
}

void OsdiModel::stamp_pattern(StampPattern& out) const {
    // OSDI 的 jacobian_entries 描述实际非零位置。
    // stamp 时按这些 entry 的 (node1, node2) 登记（映射到全局 NodeId）。
    if (!descriptor_) return;
    out.entries.reserve(out.entries.size() + descriptor_->num_jacobian_entries);
    for (uint32_t i = 0; i < descriptor_->num_jacobian_entries; ++i) {
        const OsdiJacobianEntry& e = descriptor_->jacobian_entries[i];
        // OSDI 节点索引是器件本地的（0..num_nodes-1），映射到全局
        NodeId n1 = (e.nodes.node_1 < nodes_.size()) ? nodes_[e.nodes.node_1] : 0;
        NodeId n2 = (e.nodes.node_2 < nodes_.size()) ? nodes_[e.nodes.node_2] : 0;
        out.entries.emplace_back(n1, n2);
    }
}

void OsdiModel::eval(const OperatingPoint& op, DeviceContribution& out) const {
    if (!client_ || !client_->ready()) {
        out.f.assign(nodes_.size(), 0.0);
        out.jac.clear();
        return;
    }

    // 构造节点电压向量（NodeId 布局，索引=NodeId，0=地=0V）。
    // OSDI 通过 node_mapping[localNode]=NodeId 索引它。
    std::vector<double> nodeV = op.v;
    NodeId maxId = 0;
    for (NodeId n : nodes_) if (n > maxId) maxId = n;
    if (nodeV.size() <= maxId) nodeV.resize(maxId + 1, 0.0);
    nodeV[0] = 0.0;  // 地节点强制 0V

    // node_mapping：本地节点 i -> NodeId（prev_solve 按 NodeId 索引，0=地）
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);

    uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalDC(nodeV);
    (void)ret;

    // 取回电阻性残差
    std::vector<double> resid;
    client_->loadResidualResist(resid);
    out.f = std::move(resid);

    // 雅可比由调用方通过 loadJacobianInto 单独加载（需要目标指针）
    out.jac.assign(descriptor_ ? descriptor_->num_jacobian_entries : 0, 0.0);
}

void OsdiModel::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    if (!client_ || !client_->ready() || !descriptor_) {
        out.f.assign(nodes_.size(), 0.0);
        out.jac.clear();
        return;
    }

    // node_mapping
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);

    // alpha：OSDI 建议 transient 中静态/电阻项 alpha=1.0，
    // 电荷项由模型内部使用 dt 处理，仿真器不再额外乘以 1/dt。
    double alpha = 1.0;
    (void)op.dt;

    uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalTransient(
        op.v, op.time, op.dt, alpha);
    (void)ret;

    // 取回瞬态 RHS（SPICE 牛顿 RHS）。对静态器件它等于 -residual，
    // 仿真器期望 out.f 为 residual，故取反。
    std::vector<double> rhs;
    client_->loadSpiceRhsTran(rhs, op.v, alpha);
    out.f.assign(rhs.size(), 0.0);
    for (size_t i = 0; i < rhs.size(); ++i) out.f[i] = -rhs[i];

    // 取回瞬态雅可比
    uint32_t nE = descriptor_->num_jacobian_entries;
    out.jac.assign(nE, 0.0);
    std::vector<double*> tgt(nE, nullptr);
    for (uint32_t e = 0; e < nE; ++e) tgt[e] = &out.jac[e];
    const_cast<OsdiClient*>(client_.get())->loadJacobianTranWith(tgt.data(), nodeMap, alpha);
}

void OsdiModel::initializeTransientState(const std::vector<double>& nodeV) {
    if (!client_ || !client_->ready() || !descriptor_) {
        if (client_) {
            client_->prevState().assign(client_->numStates(), 0.0);
            client_->nextState().assign(client_->numStates(), 0.0);
        }
        return;
    }

    // node_mapping：本地节点 i -> NodeId（prev_solve 按 NodeId 索引，0=地）
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    client_->setNodeMapping(nodeMap);

    // 分配并清零状态向量
    client_->prevState().assign(client_->numStates(), 0.0);
    client_->nextState().assign(client_->numStates(), 0.0);

    // 构造完整节点电压向量（按 NodeId 索引）
    std::vector<double> v = nodeV;
    NodeId maxId = 0;
    for (NodeId n : nodes_) if (n > maxId) maxId = n;
    if (v.size() <= maxId) v.resize(maxId + 1, 0.0);
    v[0] = 0.0;

    // 用 DC eval + INIT_LIM 初始化模型内部 limiting 状态与初始工作点。
    // 动态状态向量先保持为 0，第一个时间步会自然计算出正确的 next_state。
    client_->resetLimiting();
    client_->evalDC(v, INIT_LIM);
}

std::vector<double> OsdiModel::getTransientState() const {
    if (!client_) return {};
    return client_->prevState();
}

void OsdiModel::setTransientState(const std::vector<double>& s) {
    if (!client_) return;
    client_->prevState() = s;
    client_->nextState().assign(s.size(), 0.0);
}

void OsdiModel::updateTransientState(const TransientOpPoint& op) {
    (void)op;
    if (client_) client_->swapState();
}

} // namespace rfsim
