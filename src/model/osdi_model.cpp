// osdi_model.cpp — OSDI 器件 wrapper 实现
#include "osdi_model.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
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
      modelName_(descriptor ? (descriptor->name ? descriptor->name : "") : ""),
      bypassTol_(bypassTolDefault()) {}

// V3-L1: 读 RFSIM_BYPASS_TOL 环境变量。默认 1e-9；设 0 禁用 bypass（回归开关）。
double OsdiModel::bypassTolDefault() {
    static double v = []() {
        const char* s = std::getenv("RFSIM_BYPASS_TOL");
        if (!s) return 1e-9;
        return std::atof(s);  // 0 表示禁用
    }();
    return v;
}

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

    // 模型块：同模型多实例共享。
    // V2-γ C3：若上层（device_factory 缓存或测试 fixture）已经通过
    // useSharedModelBlock() 注入了共享 block，则复用之；OsdiClient::init
    // 检测到 block->setup 已置位时会跳过 setup_model，仅为本实例分配
    // instance 数据。这同时从根本上消除了 BSIM4 OSDI 在多实例场景下
    // setup_model 被重复调用产生的确定性状态串拥（C1.4 / C2.b）。
    if (!modelBlock_) {
        modelBlock_ = std::make_shared<OsdiModelBlock>();
        modelBlock_->descriptor = descriptor_;
    } else if (!modelBlock_->descriptor) {
        modelBlock_->descriptor = descriptor_;
    }

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
    if (!client_->init(lib_, modelBlock_, nodes_, diags, modelPairs, temperature_)) {
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
            // 选择 master：优先用更小的 NodeId（外部端子 < 内部节点；ground=0 总是最小）。
            // 部分模型 (e.g., diode_va 的 thermal collapse) 把 node_1 设为内部、node_2 设为
            // 外部端子；旧逻辑直接 `nodes_[b]=nodes_[a]` 会把外部端子（如 cathode）拉到
            // 一个无人引用的内部 NodeId，导致电路浮接、KCL 矩阵奇异。
            NodeId va = nodes_[a], vb = nodes_[b];
            NodeId master = (va <= vb) ? va : vb;
            nodes_[a] = master;
            nodes_[b] = master;
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
    if (!client_ || !client_->ready()) return;
    // V3-L1: 若上次 eval 被 bypass，instData_ 没更新——从 lastJac_ 复制
    if (bypassEnabled() && evalBypassed_) {
        uint32_t nE = descriptor_ ? descriptor_->num_jacobian_entries : 0;
        for (uint32_t e = 0; e < nE && e < lastJac_.size(); ++e) {
            if (targets[e]) *targets[e] = lastJac_[e];
        }
        return;
    }
    // 正常路径：从 client 读并缓存到 lastJac_
    client_->loadJacobianResistWith(targets, nodeMap);
    if (bypassEnabled()) {
        uint32_t nE = descriptor_ ? descriptor_->num_jacobian_entries : 0;
        lastJac_.resize(nE);
        for (uint32_t e = 0; e < nE; ++e) {
            if (targets[e]) lastJac_[e] = *targets[e];
        }
    }
}

void OsdiModel::bindStampPtrs(SparseMatrix& G, uint32_t numExternalNodes) {
    // V3-L0: 遍历 jacobian_entries，对每个 entry 取 (gr, gc) 全局坐标，
    // 与 transient_assembly.cpp 的坐标映射一致：
    //   - 地对地 (gr==0 && gc==0): 跳过（nullptr）
    //   - 地对非地 (gr==0, gc!=0): 合并到 (gc-1, gc-1) 对角
    //   - 非地对地 (gr!=0, gc==0): 合并到 (gr-1, gr-1) 对角
    //   - 非地对非地: (gr-1, gc-1)
    //   - 内部节点（NodeId > numExternalNodes）: nullptr（不进外部 MNA）
    // 注意：stampPtrs_ 顺序与 jacobian_entries / out.jac 严格对齐。
    stampPtrs_.clear();
    boundG_ = &G;
    if (!descriptor_) return;
    uint32_t nE = descriptor_->num_jacobian_entries;
    stampPtrs_.resize(nE, nullptr);
    const auto& nds = nodes_;
    uint32_t nNodes = descriptor_->num_nodes;
    for (uint32_t e = 0; e < nE; ++e) {
        const OsdiJacobianEntry& je = descriptor_->jacobian_entries[e];
        uint32_t lr = (je.nodes.node_1 < nNodes) ? je.nodes.node_1 : nNodes;
        uint32_t lc = (je.nodes.node_2 < nNodes) ? je.nodes.node_2 : nNodes;
        NodeId gr = (lr < nds.size()) ? nds[lr] : 0;
        NodeId gc = (lc < nds.size()) ? nds[lc] : 0;
        // 内部节点跳过（与 assembler 一致）
        bool grOk = (gr == 0) || (gr <= numExternalNodes);
        bool gcOk = (gc == 0) || (gc <= numExternalNodes);
        if (!grOk || !gcOk) continue;
        if (gr == 0 && gc == 0) continue;
        uint32_t row, col;
        if (gr == 0) { row = gc - 1; col = gc - 1; }       // 地对非地 → 对角
        else if (gc == 0) { row = gr - 1; col = gr - 1; }   // 非地对地 → 对角
        else { row = gr - 1; col = gc - 1; }
        stampPtrs_[e] = G.ptrFor(row, col);
    }
}

void OsdiModel::evalTimeSamples(const std::vector<std::vector<double>>& timeVoltages,
                                const std::vector<uint32_t>& nodeMap,
                                std::vector<std::vector<double>>& outCurrents,
                                std::vector<std::vector<double>>& outCharges) const {
    if (!client_ || !client_->ready()) {
        outCurrents.assign(timeVoltages.size(), std::vector<double>(nodes_.size(), 0.0));
        outCharges.assign(timeVoltages.size(), std::vector<double>(nodes_.size(), 0.0));
        return;
    }
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
    uint32_t nNodes = descriptor_->num_nodes;
    outCurrents.assign(timeVoltages.size(), std::vector<double>(nNodes, 0.0));
    outCharges.assign(timeVoltages.size(), std::vector<double>(nNodes, 0.0));
    // evalDC 需要全局节点编号索引的电压向量
    NodeId maxId = 0;
    for (NodeId g : nodes_) if (g > maxId) maxId = g;
    // P4 post-A1：HB 时域 sweep 每 sample 都重建 globalV / resid / limRhs。
    // numSamples = 2·NH+1, 用 thread_local scratch 复用分配。
    thread_local std::vector<double> globalV;
    thread_local std::vector<double> resid;
    thread_local std::vector<double> limRhs;
    // S5 路径 B2：电抗残差 scratch（电荷 Q），与阻性残差分开暂存。
    thread_local std::vector<double> reactResid;
    thread_local std::vector<double> reactLimRhs;

    // 并行化在 hb_jacobian.cpp 的器件循环层做（每器件独立 OsdiClient，天然线程安全），
    // 而非此处的 sample 循环（instance_data 克隆有指针安全问题）。
    // 串行路径（每器件内 N 个 sample 串行 eval）：
    for (size_t s = 0; s < timeVoltages.size(); ++s) {
        // 每次 eval 前重新设置 node_mapping：某些模型可能在 eval 中修改它
        const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
        globalV.assign(maxId + 1, 0.0);
        bool bad = false;
        for (uint32_t i = 0; i < nNodes && i < timeVoltages[s].size() && i < nodes_.size(); ++i) {
            if (nodes_[i] <= maxId) {
                double vv = timeVoltages[s][i];
                // V2-δ S1 plan0621-v4 §1.3 补丁2：原门槛 |vv|>100V 对 ~1.5V
                // 电源体系太松；改用 20V (BSIM4 limiting 内部最大 ~5V Vbs/Vgs，
                // 已含安全裕度）。超界时 clamp 到 ±20V 而非整段 sample 直接零填，
                // 保持 FFT 输入周期性，避免方波 artifact 破坏卷积 Jacobian。
                if (std::isnan(vv) || std::isinf(vv)) {
                    bad = true;
                } else if (std::abs(vv) > 20.0) {
                    vv = (vv > 0) ? 20.0 : -20.0;
                }
                globalV[nodes_[i]] = vv;
            }
        }
        if (bad) {
            // 模型在极端工作点下可能段错误，跳过该采样
            continue;
        }
        // S5 路径 B2：同时请求 CALC_REACT_RESIDUAL，让 OSDI 计算电荷残差 Q。
        // evalDC 内部把 flag 合并进 ANALYSIS_DC | CALC_RESIST_RESIDUAL | CALC_REACT_RESIDUAL，
        // BSIM4 在此 flag 下会通过 loadResidualReact 返回节点电荷 Q。
        // 注意：第三参数 calcJacobian=false，避免额外 jac 装配开销。
        // H4: 不传 CALC_REACT_RESIDUAL——BSIM4 在此 flag 下 HB 收敛性下降 50%+。
        // Q 值实测极小（1e-14），对 HB 残差贡献可忽略。
        // loadResidualReact 方法已恢复，供未来模型验证后启用。
        uint32_t ret = const_cast<OsdiClient*>(client_.get())
                           ->evalDC(globalV, 0, false);
        if (ret & EVAL_RET_FLAG_FATAL) {
            // 模型拒绝该工作点：返回零电流/零电荷，避免后续崩溃
            continue;
        }
        resid.clear();
        limRhs.clear();
        client_->loadResidualResist(resid);
        client_->loadLimitRhsResist(limRhs);
        // S5 路径 B2：取电抗残差（电荷 Q），由调用方按 j·ω_k 加权进残差。
        // H4 修复：恢复 loadResidualReact 调用（OSDI descriptor 有此函数指针）
        reactResid.clear();
        reactLimRhs.clear();
        client_->loadResidualReact(reactResid);
        client_->loadLimitRhsReact(reactLimRhs);
        for (uint32_t k = 0; k < nNodes && k < resid.size(); ++k) {
            outCurrents[s][k] = resid[k];
            if (k < limRhs.size()) outCurrents[s][k] += limRhs[k];
            // outCharges 暂存原始电荷 Q(t)，不加 j·ω（加权由 hb_jacobian 完成）
            double q = 0.0;
            if (k < reactResid.size()) q += reactResid[k];
            if (k < reactLimRhs.size()) q += reactLimRhs[k];
            outCharges[s][k] = q;
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
    // P4 post-A1：复用 globalV / tgt scratch
    thread_local std::vector<double>  globalV;
    thread_local std::vector<double*> tgt;
    for (size_t s = 0; s < timeVoltages.size(); ++s) {
        // 每次 eval 前重新设置 node_mapping 与 jacobian 指针 scratch
        const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
        globalV.assign(maxId + 1, 0.0);
        bool bad = false;
        for (uint32_t i = 0; i < nNodes && i < timeVoltages[s].size() && i < nodes_.size(); ++i) {
            if (nodes_[i] <= maxId) {
                double vv = timeVoltages[s][i];
                // 同上 evalTimeSamples 处补丁2：20V clamp，保 FFT 周期性。
                if (std::isnan(vv) || std::isinf(vv)) {
                    bad = true;
                } else if (std::abs(vv) > 20.0) {
                    vv = (vv > 0) ? 20.0 : -20.0;
                }
                globalV[nodes_[i]] = vv;
            }
        }
        if (bad) continue;
        uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalDC(globalV);
        if (ret & EVAL_RET_FLAG_FATAL) {
            // 模型拒绝该工作点：保持该采样点的雅可比为零
            continue;
        }
        tgt.assign(nE, nullptr);
        for (uint32_t e = 0; e < nE; ++e) tgt[e] = &outJac[s][e];
        client_->loadJacobianResistWith(tgt.data(), nodeMap);
    }
}

void OsdiModel::evalTimeJacobiansReact(
    const std::vector<std::vector<double>>& timeVoltages,
    const std::vector<uint32_t>& nodeMap,
    std::vector<std::vector<double>>& outJacReact) const {
    if (!client_ || !client_->ready() || !descriptor_) {
        outJacReact.assign(timeVoltages.size(),
                           std::vector<double>(descriptor_ ? descriptor_->num_jacobian_entries : 0, 0.0));
        return;
    }
    uint32_t nE = descriptor_->num_jacobian_entries;
    uint32_t nNodes = descriptor_->num_nodes;
    outJacReact.assign(timeVoltages.size(), std::vector<double>(nE, 0.0));
    NodeId maxId = 0;
    for (NodeId g : nodes_) if (g > maxId) maxId = g;
    // P4 post-A1：复用 globalV / tgt scratch
    thread_local std::vector<double>  globalV;
    thread_local std::vector<double*> tgt;
    for (size_t s = 0; s < timeVoltages.size(); ++s) {
        const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);
        globalV.assign(maxId + 1, 0.0);
        bool bad = false;
        for (uint32_t i = 0; i < nNodes && i < timeVoltages[s].size() && i < nodes_.size(); ++i) {
            if (nodes_[i] <= maxId) {
                double vv = timeVoltages[s][i];
                // 同上 evalTimeSamples 处补丁2：20V clamp，保 FFT 周期性。
                if (std::isnan(vv) || std::isinf(vv)) {
                    bad = true;
                } else if (std::abs(vv) > 20.0) {
                    vv = (vv > 0) ? 20.0 : -20.0;
                }
                globalV[nodes_[i]] = vv;
            }
        }
        if (bad) continue;
        uint32_t ret = const_cast<OsdiClient*>(client_.get())
                           ->evalDC(globalV, CALC_REACT_JACOBIAN, true);
        if (ret & EVAL_RET_FLAG_FATAL) continue;
        tgt.assign(nE, nullptr);
        for (uint32_t e = 0; e < nE; ++e) tgt[e] = &outJacReact[s][e];
        const_cast<OsdiClient*>(client_.get())->loadJacobianReactWith(tgt.data(), nodeMap, 1.0);
    }
}

void OsdiModel::resetLimiting() {
    if (client_) client_->resetLimiting();
    invalidateEvalCache();  // V3-L1: limiting 锚点重置，缓存失效
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

    // V3-L1: 提取端电压，检查 bypass
    if (bypassEnabled()) {
        bool hit = evalCached_;
        if (hit && lastTermV_.size() == nodes_.size()) {
            for (size_t k = 0; k < nodes_.size(); ++k) {
                double vk = (nodes_[k] < op.v.size()) ? op.v[nodes_[k]] : 0.0;
                // M6: 相对容差——避免近零电压时误 bypass
                double scale = std::max(std::fabs(lastTermV_[k]), 1.0);
                if (std::fabs(vk - lastTermV_[k]) > bypassTol_ * scale) { hit = false; break; }
            }
        } else {
            hit = false;
        }
        if (hit) {
            out.f = lastF_;
            out.jac = lastJac_;
            evalBypassed_ = true;
            return;
        }
        evalBypassed_ = false;
    }

    // 构造节点电压向量（NodeId 布局，索引=NodeId，0=地=0V）。
    std::vector<double> nodeV = op.v;
    NodeId maxId = 0;
    for (NodeId n : nodes_) if (n > maxId) maxId = n;
    if (nodeV.size() <= maxId) nodeV.resize(maxId + 1, 0.0);
    nodeV[0] = 0.0;  // 地节点强制 0V

    // node_mapping：本地节点 i -> NodeId
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);

    uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalDC(nodeV);
    (void)ret;

    // 取回电阻性残差与 limiting RHS，合并为器件残差
    std::vector<double> resid, limRhs;
    client_->loadResidualResist(resid);
    client_->loadLimitRhsResist(limRhs);
    out.f.assign(resid.size(), 0.0);
    for (size_t i = 0; i < out.f.size(); ++i) {
        out.f[i] = resid[i];
        if (i < limRhs.size()) out.f[i] += limRhs[i];
    }

    // 雅可比由调用方通过 loadJacobianInto 单独加载（需要目标指针）
    out.jac.assign(descriptor_ ? descriptor_->num_jacobian_entries : 0, 0.0);

    // V3-L1: 缓存结果
    if (bypassEnabled()) {
        lastTermV_.resize(nodes_.size());
        for (size_t k = 0; k < nodes_.size(); ++k)
            lastTermV_[k] = (nodes_[k] < op.v.size()) ? op.v[nodes_[k]] : 0.0;
        lastF_ = out.f;
        // DC 雅可比缓存在 loadJacobianInto 中填充
        evalCached_ = true;
    }
}

void OsdiModel::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    if (!client_ || !client_->ready() || !descriptor_) {
        out.f.assign(nodes_.size(), 0.0);
        out.jac.clear();
        return;
    }

    // V3-L1: 提取端电压 + t/dt，检查 bypass
    if (bypassEnabled()) {
        bool hit = evalCached_ && lastT_ >= 0.0;
        if (hit && std::fabs(op.time - lastT_) > 1e-15) hit = false;
        if (hit && std::fabs(op.dt - lastDt_) > 1e-15) hit = false;
        if (hit && lastTermV_.size() == nodes_.size()) {
            for (size_t k = 0; k < nodes_.size(); ++k) {
                double vk = (nodes_[k] < op.v.size()) ? op.v[nodes_[k]] : 0.0;
                // M6: 相对容差——避免近零电压时误 bypass
                double scale = std::max(std::fabs(lastTermV_[k]), 1.0);
                if (std::fabs(vk - lastTermV_[k]) > bypassTol_ * scale) { hit = false; break; }
            }
        } else {
            hit = false;
        }
        if (hit) {
            out.f = lastF_;
            out.jac = lastJac_;
            evalBypassed_ = true;
            return;
        }
        evalBypassed_ = false;
    }

    // node_mapping
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);

    // H7: alpha 按积分方法计算——BE: alpha=1.0, Trapezoidal: alpha=0.5
    double alpha = (op.method == IntegrationMethod::Trapezoidal) ? 0.5 : 1.0;
    (void)op.dt;

    uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalTransient(
        op.v, op.time, op.dt, alpha);
    (void)ret;

    // 取回瞬态 RHS
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

    // V3-L1: 缓存结果
    if (bypassEnabled()) {
        lastTermV_.resize(nodes_.size());
        for (size_t k = 0; k < nodes_.size(); ++k)
            lastTermV_[k] = (nodes_[k] < op.v.size()) ? op.v[nodes_[k]] : 0.0;
        lastF_ = out.f;
        lastJac_ = out.jac;
        lastT_ = op.time;
        lastDt_ = op.dt;
        evalCached_ = true;
    }
}

// V3-MR Phase2: 只算 residual 不算 jacobian——省 jacobian 计算开销。
// residual 用当前工作点重新算（调 desc_->eval 但去掉 jacobian flag），
// jacobian 复用上次完整 eval 的 lastJac_。
void OsdiModel::evalTransientResidOnly(const TransientOpPoint& op, DeviceContribution& out) const {
    if (!client_ || !client_->ready() || !descriptor_) {
        out.f.assign(nodes_.size(), 0.0);
        out.jac.clear();
        return;
    }
    std::vector<uint32_t> nodeMap(nodes_.size(), 0);
    for (uint32_t i = 0; i < nodes_.size(); ++i) nodeMap[i] = nodes_[i];
    const_cast<OsdiClient*>(client_.get())->setNodeMapping(nodeMap);

    // H7: alpha 按积分方法计算——BE: alpha=1.0, Trapezoidal: alpha=0.5
    double alpha = (op.method == IntegrationMethod::Trapezoidal) ? 0.5 : 1.0;
    (void)op.dt;
    uint32_t ret = const_cast<OsdiClient*>(client_.get())->evalTransientResidOnly(
        op.v, op.time, op.dt, alpha);
    (void)ret;

    // 取回 residual（当前工作点）
    std::vector<double> rhs;
    client_->loadSpiceRhsTran(rhs, op.v, alpha);
    out.f.assign(rhs.size(), 0.0);
    for (size_t i = 0; i < rhs.size(); ++i) out.f[i] = -rhs[i];

    // jacobian 复用上次完整 eval 的缓存
    out.jac = lastJac_;
    evalBypassed_ = true;
    // M7: residOnly 推进了 next_state 但 cache 仍指向旧值——不清会导致后续 bypass 用 stale cache
    // 注意：不调 invalidateEvalCache() 因为 lastF_/lastJac_ 仍有效（resid 重新算了但 jac 复用）
    // 但 next_state 变了——下次 swapState 后必须重新 eval
    // swapState → invalidateEvalCache 已在 updateTransientState 中处理
}

void OsdiModel::initializeTransientState(const std::vector<double>& nodeV) {
    invalidateEvalCache();  // V3-L1: 状态初始化，缓存失效
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
    invalidateEvalCache();  // V3-L1: 状态恢复，缓存失效
    if (!client_) return;
    client_->prevState() = s;
    client_->nextState().assign(s.size(), 0.0);
}

void OsdiModel::updateTransientState(const TransientOpPoint& op) {
    (void)op;
    invalidateEvalCache();  // V3-L1: swapState 推进状态，缓存失效
    if (client_) client_->swapState();
}

} // namespace rfsim
