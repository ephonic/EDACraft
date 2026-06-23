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
#include "../assembly/matrix.hpp"
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

    // 设置器件温度（K）；必须在 initialize() 之前调用才能生效。
    // 默认 300.15K（室温）。OSDI setup_instance 基于此值预计算温度依赖项。
    void setTemperature(double tempK) { temperature_ = tempK; }
    [[nodiscard]] double temperature() const noexcept { return temperature_; }

    // V3-MR: multi-rate 仿真接口。
    // setRateRatio(K): 慢器件的步长是快器件的 K 倍（K=1=统一步长）。
    //   K>1 时器件在 K 个快步长内只 eval 一次，其余 K-1 步复用缓存。
    // mrNeedsEval(): 本步是否需要重新 eval（由积分循环调用）。
    // mrAdvance(): 步末推进 stepCounter，返回是否到达 K 步（需 swapState）。
    // mrCheckVoltages(): 自适应检查——端电压变化超 mrRelTol_ 则强制重新 eval。
    void setRateRatio(uint32_t K) { mrRateRatio_ = K > 0 ? K : 1; mrStepCounter_ = 0; mrNeedsEval_ = true; mrForcedEvalCount_ = 0; }
    void setMrRelTol(double tol) { mrRelTol_ = tol; }
    void setMrAutoTune(bool enable) { mrAutoTune_ = enable; if (enable) mrRateRatio_ = std::max(mrRateRatio_, (uint32_t)1); }
    [[nodiscard]] uint32_t rateRatio() const noexcept { return mrRateRatio_; }
    [[nodiscard]] bool mrNeedsEval() const noexcept { return mrNeedsEval_; }
    void mrMarkEvalDone() { mrNeedsEval_ = false; }
    // 自适应：检查当前端电压 vs lastTermV_，变化超阈值则设 needsEval
    void mrCheckVoltages(const std::vector<double>& nodeV) {
        if (mrNeedsEval_ || mrRateRatio_ <= 1) return;
        if (lastTermV_.size() != nodes_.size()) { mrNeedsEval_ = true; return; }
        for (size_t k = 0; k < nodes_.size(); ++k) {
            double vk = (nodes_[k] < nodeV.size()) ? nodeV[nodes_[k]] : 0.0;
            double ref = std::fabs(lastTermV_[k]);
            double scale = std::max(ref, 1.0);
            if (std::fabs(vk - lastTermV_[k]) > mrRelTol_ * scale) {
                mrNeedsEval_ = true;
                ++mrForcedEvalCount_;  // 自动分级：记录强制 eval 次数
                return;
            }
        }
    }
    // 步末推进：stepCounter++，若达到 K 则返回 true（需 swapState + 重置 needsEval）
    // V3-MR Phase4: 自动速率分级——K 步到时检查 forcedEvalCount：
    //   forcedEvalCount == 0 → K 步全 bypass，电压稳定 → K *= 2（上限 16）
    //   forcedEvalCount >= K/2 → 超半数步触发强制 eval → K = 1（回退快步长）
    bool mrAdvance() {
        ++mrStepCounter_;
        if (mrStepCounter_ >= mrRateRatio_) {
            mrStepCounter_ = 0;
            mrNeedsEval_ = true;
            // 自动分级
            if (mrAutoTune_) {
                if (mrForcedEvalCount_ == 0 && mrRateRatio_ < 16) {
                    mrRateRatio_ *= 2;  // 电压稳定，加大步长
                } else if (mrForcedEvalCount_ >= (mrRateRatio_ + 1) / 2) {
                    mrRateRatio_ = 1;   // 电压变化频繁，回退快步长
                }
                mrForcedEvalCount_ = 0;
            }
            return true;
        }
        return false;
    }
    void mrForceEval() { mrNeedsEval_ = true; }  // FD 扰动路径用
    [[nodiscard]] bool evalCached() const { return evalCached_; }  // V3-MR: cache 是否有效
    void invalidateEvalCache() { evalCached_ = false; }  // M1: 外部清 cache（gmin 步间）

    [[nodiscard]] bool ready() const noexcept { return client_ && client_->ready(); }
    [[nodiscard]] const OsdiDescriptor* descriptor() const noexcept { return descriptor_; }

    // V3-MR: multi-rate bypass——从 V3-L1 cache 复用 f/jac，不调 desc_->eval。
    // 调用前需确保 mrNeedsEval()==false 且 lastF_/lastJac_ 有效。
    void evalTransientCached(DeviceContribution& out) const {
        out.f = lastF_;
        out.jac = lastJac_;
        evalBypassed_ = true;
    }
    // V3-MR Phase2: 只算 residual（调 desc_->eval 但不算 jacobian），jac 从 cache 复用
    void evalTransientResidOnly(const TransientOpPoint& op, DeviceContribution& out) const;

    // V2-γ C3：同 modelcard 多实例共享 OsdiModelBlock。
    // 在 initialize() 之前注入预存的 block；OsdiClient::init 检测到 block->setup
    // 已置位时只为新实例分配 instance 数据，跳过 setup_model（避免多次 setup_model
    // 在 BSIM4 OSDI 多实例场景下产生的确定性状态串拥）。
    // 调用方典型用法：第 1 个实例 initialize() 后 modelBlock() 取出，
    // 后续同模型实例 useSharedModelBlock() 注入。
    void useSharedModelBlock(std::shared_ptr<OsdiModelBlock> b) { modelBlock_ = std::move(b); }
    [[nodiscard]] std::shared_ptr<OsdiModelBlock> modelBlock() const { return modelBlock_; }

    // 加载雅可比到仿真器提供的 per-entry 目标指针。
    void loadJacobianInto(double** targets, uint32_t matDim,
                          const std::vector<uint32_t>& nodeMap);

    // V3-L0: pattern 固化后从 SparseMatrix 取出每个 jacobian entry 对应的
    // values_ 指针。坐标映射与 transient assembler 一致（地对地跳过，
    // 地对非地合并到对角）。内部节点（NodeId > maxExternalNode）指针为 nullptr。
    void bindStampPtrs(SparseMatrix& G, uint32_t numExternalNodes) override;

    // 时域批量评估（HB 用）：对每个时域采样点，设置节点电压、调 OSDI eval、
    // 取回各节点电流（电阻性残差）。
    // timeVoltages[sample][localNode] = 第 sample 个时刻的本地节点电压。
    // 输出 outCurrents[sample][localNode] = 该时刻流经各节点的电流。
    // nodeMap: 本地节点 -> 全局电压向量位置（与 eval 一致）。
    void evalTimeSamples(const std::vector<std::vector<double>>& timeVoltages,
                         const std::vector<uint32_t>& nodeMap,
                         std::vector<std::vector<double>>& outCurrents) const {
        std::vector<std::vector<double>> discard;
        evalTimeSamples(timeVoltages, nodeMap, outCurrents, discard);
    }

    // S5 路径 B2：新增 overload 同时返回电荷（电抗性残差 Q(t)）。
    // outCharges[sample][localNode] = 该时刻储存在各节点的电荷 Q（来自
    // loadResidualReact + loadLimitRhsReact）。调用方 (hb_jacobian.cpp) 对
    // outCharges 做 FFT 得 qHarm[k]，再按 j·ω_k·qHarm[k] 装配进残差 F，
    // 实现 F/J 一致（雅可比侧 addSusceptanceBlock 已含 jωQ 项）。
    // 旧 overload 保留向后兼容，内部丢弃 outCharges。
    void evalTimeSamples(const std::vector<std::vector<double>>& timeVoltages,
                         const std::vector<uint32_t>& nodeMap,
                         std::vector<std::vector<double>>& outCurrents,
                         std::vector<std::vector<double>>& outCharges) const;

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
    double temperature_ = 300.15;   // setup_instance 时使用的温度

    // V3-L1: 器件级 eval bypass。Newton line-search 阶段端电压变化 < bypassTol_ 时
    // 复用上次 f/jac，跳过 desc_->eval。bypassTol_=0 禁用（回归开关）。
    // 缓存在 resetLimiting/setTransientState/swapState/initializeTransientState
    // 时失效（器件内部状态变化）。
    // mutable: eval/evalTransient 是 const 但需修改缓存
    mutable std::vector<double> lastTermV_;   // 上次 eval 的端电压（nodes_ 对应子集）
    mutable std::vector<double> lastF_;       // 上次残差
    mutable std::vector<double> lastJac_;     // 上次雅可比（DC 路径 loadJacobianInto + Transient 共用）
    mutable double lastT_ = -1.0;             // 上次 transient 的 t
    mutable double lastDt_ = -1.0;            // 上次 transient 的 dt
    mutable bool evalCached_ = false;
    mutable bool evalBypassed_ = false;  // V3-L1: 上次 eval 是否被 bypass（loadJacobianInto 用）
    double bypassTol_ = 0.0;           // 构造时调 bypassTolDefault() 初始化
    static double bypassTolDefault();  // 读 RFSIM_BYPASS_TOL，默认 1e-9
    bool bypassEnabled() const { return bypassTol_ > 0.0; }

    // V3-MR: multi-rate 状态
    uint32_t mrRateRatio_ = 1;      // K = dt_slow / dt_fast
    uint32_t mrStepCounter_ = 0;    // [0..K-1]
    bool mrNeedsEval_ = true;       // 本步是否需 eval
    double mrRelTol_ = 1e-3;        // 自适应电压变化阈值（相对）
    bool mrAutoTune_ = false;       // V3-MR Phase4: 自动速率分级
    uint32_t mrForcedEvalCount_ = 0; // K 步周期内强制 eval 次数
};

} // namespace rfsim

#endif // RFSIM_MODEL_OSDI_MODEL_HPP
