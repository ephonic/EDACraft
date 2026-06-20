// osdi_model.hpp — OpenVAF/OSDI 器件模型 wrapper（plan.md §4.3.3）
//
// 把 OSDI 接口适配到 DeviceModel 抽象。
// 持有 OsdiClient（管理实例/模型数据块与 eval 调用），
// 在 DeviceModel::eval 中调用 OSDI eval 并把贡献映射到 DeviceContribution。
//
// OSDI (Open Source Device Interface) v0.3 是 SemiMod 制定的仿真器无关器件接口，
// OpenVAF 把 Verilog-A 模型编译为符合 OSDI 的共享库。
#ifndef RFSIM_MODEL_OSDI_MODEL_HPP
#define RFSIM_MODEL_OSDI_MODEL_HPP

#include "device_model.hpp"
#include "osdi/osdi_library.hpp"
#include "osdi/osdi_client.hpp"
#include "../circuit/circuit.hpp"
#include <memory>
#include <string>

namespace rfsim {

// OSDI 器件实例的 DeviceModel 适配器
class OsdiModel : public DeviceModel {
public:
    // externalNodes: 外部端子（d,g,s,b 等），长度 = num_terminals。
    // initialize() 会为内部节点(num_nodes - num_terminals)自动分配全局节点编号，
    // 从 internalNodeBase 开始递增。调用后 nextInternalNode 更新为下一个可用编号。
    OsdiModel(std::string name,
              std::vector<NodeId> externalNodes,
              std::shared_ptr<OsdiLibrary> lib,
              const OsdiDescriptor* descriptor,
              ParamList instanceParams,
              ParamList modelParams = {});

    // 完成初始化（分配数据块、setup、绑定参数、展开内部节点）。失败返回 false。
    // internalNodeBase: 内部节点全局编号起始（in/out，返回下一个可用）。
    bool initialize(Diagnostics& diags, NodeId& internalNodeBase);
    // 便捷重载（内部节点从 100000 开始）
    bool initialize(Diagnostics& diags) { NodeId b = 100000; return initialize(diags, b); }

    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }

    // 重置模型内部 limiting 状态（跨 Newton 迭代前调用）
    void resetLimiting();

    // 瞬态状态管理
    [[nodiscard]] bool hasTransientState() const override {
        return client_ && client_->hasTransientState();
    }
    [[nodiscard]] size_t transientStateSize() const override {
        return client_ ? client_->numStates() : 0;
    }
    void initializeTransientState(const std::vector<double>& nodeV) override;
    [[nodiscard]] std::vector<double> getTransientState() const override;
    void setTransientState(const std::vector<double>& s) override;
    void updateTransientState(const TransientOpPoint& op) override;

    [[nodiscard]] bool ready() const noexcept { return client_ && client_->ready(); }
    [[nodiscard]] const OsdiDescriptor* descriptor() const noexcept { return descriptor_; }

    // 加载雅可比到仿真器提供的 per-entry 目标指针。
    void loadJacobianInto(double** targets, uint32_t matDim,
                          const std::vector<uint32_t>& nodeMap);

    // 时域批量评估（HB 用）：对每个时域采样点，设置节点电压、调 OSDI eval、
    // 取回各节点电流（电阻性残差）。
    // timeVoltages[sample][localNode] = 第 sample 个时刻的本地节点电压。
    // 输出 outCurrents[sample][localNode] = 该时刻流经各节点的电流。
    // nodeMap: 本地节点 -> 全局电压向量位置（与 eval 一致）。
    void evalTimeSamples(const std::vector<std::vector<double>>& timeVoltages,
                         const std::vector<uint32_t>& nodeMap,
                         std::vector<std::vector<double>>& outCurrents) const;

    // 时域批量雅可比评估：对每个采样点取回雅可比（用于 HB 频域卷积装配）。
    // outJac[sample][entryIdx] = 该时刻第 entryIdx 个雅可比值。
    void evalTimeJacobians(const std::vector<std::vector<double>>& timeVoltages,
                           const std::vector<uint32_t>& nodeMap,
                           std::vector<std::vector<double>>& outJac) const;

    // 时域批量电荷雅可比评估：取回 ∂Q/∂V（alpha=1.0），用于 HB 电纳块。
    void evalTimeJacobiansReact(const std::vector<std::vector<double>>& timeVoltages,
                                const std::vector<uint32_t>& nodeMap,
                                std::vector<std::vector<double>>& outJacReact) const;

    [[nodiscard]] const std::string& modelName() const {
        return descriptor_ && descriptor_->name ? modelName_ : fallbackTypeName_;
    }
    // 无 OSDI 库时的后备类型名（用于诊断与测试）
    void setFallbackTypeName(const std::string& t) { fallbackTypeName_ = t; }

private:
    std::string name_;
    std::vector<NodeId> nodes_;
    std::shared_ptr<OsdiLibrary> lib_;
    const OsdiDescriptor* descriptor_ = nullptr;
    ParamList instanceParams_;
    ParamList modelParams_;
    std::shared_ptr<OsdiModelBlock> modelBlock_;
    std::unique_ptr<OsdiClient> client_;
    std::string modelName_;
    std::string fallbackTypeName_;  // 无 descriptor 时的后备（来自 .model type）
};

} // namespace rfsim

#endif // RFSIM_MODEL_OSDI_MODEL_HPP
