// osdi_client.hpp — 单个 OSDI 器件实例的客户端封装
//
// 管理 OSDI 器件的完整生命周期：
//   1. 分配模型数据块(model_size) + setup_model
//   2. 绑定模型参数(.model 卡)
//   3. 分配实例数据块(instance_size) + setup_instance
//   4. 绑定实例参数(器件卡 W/L 等)
//   5. eval 在工作点计算残差/雅可比
//   6. load_residual_resist/load_jacobian_resist 取回贡献
//
// 对应 OsdiDescriptor 的函数指针调用。
// 模型数据块在所有同模型实例间共享（一个 model 块 + N 个 instance 块）。
#ifndef RFSIM_MODEL_OSDI_OSDI_CLIENT_HPP
#define RFSIM_MODEL_OSDI_OSDI_CLIENT_HPP

#include "osdi_0_3.h"
#include "osdi_library.hpp"
#include "../../rfsim.hpp"
#include "../device_model.hpp"
#include "../../circuit/circuit.hpp"
#include <memory>
#include <string>
#include <vector>

namespace rfsim {

// 共享的模型数据块：同一 OsdiDescriptor 的所有实例共用一个
struct OsdiModelBlock {
    const OsdiDescriptor* descriptor = nullptr;  // 描述符（函数指针+元数据）
    void* modelData = nullptr;                   // setup_model 填充的数据块
    bool  setup = false;

    OsdiModelBlock() = default;
    ~OsdiModelBlock();
    // 禁拷贝
    OsdiModelBlock(const OsdiModelBlock&) = delete;
    OsdiModelBlock& operator=(const OsdiModelBlock&) = delete;
};

// 单个 OSDI 器件实例客户端
class OsdiClient {
public:
    OsdiClient() = default;
    ~OsdiClient();

    // 初始化：绑定 descriptor + 共享模型块，分配实例数据块并 setup_instance。
    // nodes 为该实例的节点连接（对齐 descriptor->nodes 顺序）。
    bool init(std::shared_ptr<OsdiLibrary> lib,
              std::shared_ptr<OsdiModelBlock> modelBlock,
              std::vector<NodeId> nodes,
              Diagnostics& diags,
              const std::vector<std::pair<std::string, double>>& modelParams = {});

    // 设置模型参数（setup_model 之后、setup_instance 之前调用）
    bool setModelParam(const std::string& name, double value);

    [[nodiscard]] bool ready() const noexcept { return instData_ != nullptr; }
    [[nodiscard]] const OsdiDescriptor* descriptor() const noexcept { return desc_; }
    [[nodiscard]] const std::vector<NodeId>& nodes() const noexcept { return nodes_; }
    [[nodiscard]] uint32_t numNodes() const noexcept { return desc_ ? desc_->num_nodes : 0; }
    [[nodiscard]] void* instanceData() const noexcept { return instData_; }

    // 设置实例参数（在 init 之后、eval 之前调用）
    bool setInstanceParam(const std::string& name, double value);

    // 设置 node_mapping（本地节点 -> 全局求解向量位置，0-based）。
    // eval 和 load_jacobian 共用此映射。
    void setNodeMapping(const std::vector<uint32_t>& nodeMap);

    // DC 评估：给定节点电压 prev_solve（对齐 nodes_，地节点0），
    // 计算电阻性残差与雅可比，结果存入实例块。
    // extraFlags 可传入 INIT_LIM / ANALYSIS_IC 等。
    // 返回 EVAL_RET_FLAG_*。
    uint32_t evalDC(const std::vector<double>& nodeVoltages, uint32_t extraFlags = 0,
                    bool calcJacobian = true);

    // 瞬态评估：prevSolve 为上一时刻全局节点电压，t/dt 当前时间与步长。
    // alpha: SPICE 电荷模型参数（Backward Euler=1.0）。
    // extraFlags 可传入 INIT_LIM / ANALYSIS_IC 等。
    // 返回 EVAL_RET_FLAG_*。
    uint32_t evalTransient(const std::vector<double>& prevSolve,
                           double t, double dt, double alpha, uint32_t extraFlags = 0);

    // 取回电阻性残差（电流注入各节点）到 dst（长度 = num_nodes）
    void loadResidualResist(std::vector<double>& dst) const;

    // 取回瞬态 RHS（电流注入）到 dst。若模型未提供 tran hook，则回退到 DC 残差。
    void loadSpiceRhsTran(std::vector<double>& dst,
                          const std::vector<double>& prevSolve,
                          double alpha) const;

    // 取回 limiting RHS（电阻性 / 反应性）。若模型未提供则 dst 填零。
    void loadLimitRhsResist(std::vector<double>& dst) const;
    void loadLimitRhsReact(std::vector<double>& dst) const;

    // OSDI 的 jacobian_entries 描述对矩阵的贡献位置与实例块偏移。
    [[nodiscard]] const OsdiJacobianEntry* jacobianEntries() const noexcept {
        return desc_ ? desc_->jacobian_entries : nullptr;
    }
    [[nodiscard]] uint32_t numJacobianEntries() const noexcept {
        return desc_ ? desc_->num_jacobian_entries : 0;
    }

    // OSDI 雅可比加载：仿真器为每个 jacobian entry 提供一个 double* 指针，
    // 指向全局矩阵中对应 (node1,node2) 位置。这些指针组成数组，
    // 存到实例块的 jacobian_ptr_resist_offset 处。
    // setJacobianTargets: targets[entryIdx] = &matrix[node1*dim+node2]
    // 一步完成：设 node_mapping + targets + 调用 load_jacobian_resist。
    // targets[e] 指向仿真器矩阵位置；nodeMap[localNode]=全局行号。
    void loadJacobianResistWith(double** targets, const std::vector<uint32_t>& nodeMap);

    void loadJacobianResist();

    // 瞬态雅可比加载。alpha 含义同上。未提供则回退到 load_jacobian_resist。
    void loadJacobianTranWith(double** targets, const std::vector<uint32_t>& nodeMap,
                              double alpha);

    // 反应性（电荷/电容）雅可比加载。优先 load_jacobian_react；
    // 若不存在则用 load_jacobian_tran - load_jacobian_resist 近似。
    void loadJacobianReactWith(double** targets, const std::vector<uint32_t>& nodeMap,
                               double alpha);

    // 读取第 entryIdx 个雅可比 entry 的贡献值（需先 loadJacobianResist）
    [[nodiscard]] double readJacobianEntryResist(uint32_t entryIdx) const;

    // 读取模型建议的最大时间步长（0 表示未提供）
    [[nodiscard]] double readBoundStep() const;

    // 瞬态状态管理（num_states > 0 时有效）
    [[nodiscard]] bool hasTransientState() const {
        return desc_ && desc_->num_states > 0;
    }
    [[nodiscard]] uint32_t numStates() const {
        return desc_ ? desc_->num_states : 0;
    }
    [[nodiscard]] const std::vector<double>& prevState() const { return prevState_; }
    [[nodiscard]] std::vector<double>& prevState() { return prevState_; }
    [[nodiscard]] const std::vector<double>& nextState() const { return nextState_; }
    [[nodiscard]] std::vector<double>& nextState() { return nextState_; }
    void swapState();  // next -> prev，并清零 next

private:
    std::shared_ptr<OsdiLibrary>    lib_;
    std::shared_ptr<OsdiModelBlock> modelBlock_;
    const OsdiDescriptor* desc_ = nullptr;
    void* instData_ = nullptr;       // setup_instance 填充的实例块
    std::vector<NodeId> nodes_;
    mutable std::vector<double> solveBuf_;
    // 雅可比加载：仿真器为每个 entry 提供目标指针（指向全局矩阵位置）
    double** jacTargets_ = nullptr;  // [num_entries] 个 double*，每个指向矩阵元素
    uint32_t jacDim_ = 0;
    // eval 期间使用的安全 scratch，避免 stale 指针写回已释放内存
    std::vector<double> jacScratch_;
    // 是否已经用 INIT_LIM 初始化过 limiting 状态
    bool limitingInitialized_ = false;
public:
    // 强制下一次 eval 使用 INIT_LIM（用于进入新分析前重置 limiting）
    void resetLimiting() { limitingInitialized_ = false; }
    // 瞬态状态向量（prev_state / next_state）
    std::vector<double> prevState_;
    std::vector<double> nextState_;
    // DC eval 使用的独立状态缓冲，避免 static 共享导致的状态污染
    std::vector<double> dcPrevState_;
    std::vector<double> dcNextState_;
};

} // namespace rfsim

#endif // RFSIM_MODEL_OSDI_OSDI_CLIENT_HPP
