// transient_assembly.hpp — 时域瞬态 MNA 装配
//
// 在每个时间步构造线性化方程组 G·x + F = 0，其中：
//   - x 为当前时刻未知量 [节点电压(1..numNodes), 电压源分支电流]
//   - G 为雅可比（含 companion model 等效电导）
//   - F 为残差（RHS 常数项、源值、上一时刻状态贡献）
// 时步推进器直接解 G·dx = -F 得到 x。
#ifndef RFSIM_ASSEMBLY_TRANSIENT_ASSEMBLY_HPP
#define RFSIM_ASSEMBLY_TRANSIENT_ASSEMBLY_HPP

#include "matrix.hpp"
#include "../model/device_model.hpp"
#include <memory>
#include <vector>

namespace rfsim {

struct TransientSystem {
    SparseMatrix G;          // dim x dim
    Vector       F;          // dim
    uint32_t     numNodes = 0;
    uint32_t     numBranches = 0;
    uint32_t     dim() const noexcept { return numNodes + numBranches; }
    // V3-L0: pattern 固化标记。首次 assembleTransient 建 pattern + commit + bind
    // 后置 true，后续调用走 zeroCommitted + 指针 stamp 快路径。
    bool patternBound = false;
    // 首次 bind 时记录的 dim（若 numNodes/numVS 变化需重新 bind）
    uint32_t boundDim = 0;
};

// 装配一个时间点的瞬态方程。
//   numNodes: 非地节点数
//   devices:  器件列表
//   nodeV:    当前时刻节点电压猜测（索引=NodeId，0=地=0）
//   prevNodeV:上一时刻节点电压（用于 C/L companion）
//   t, dt:    当前时刻与步长
//   method:   积分方法（当前仅 BackwardEuler）
//   sys:      输出装配结果
//   residOnly: B1——Newton 内层 line-search 时置 true：OSDI 器件走 evalTransientResidOnly
//              （复用本 Newton 步已算的 jacobian，只重算 residual），省 jac 计算开销。
//              首次装配（Newton 步首）必须 false 以算完整 f+jac。
bool assembleTransient(uint32_t numNodes,
                       const std::vector<std::unique_ptr<DeviceModel>>& devices,
                       const std::vector<double>& nodeV,
                       const std::vector<double>& prevNodeV,
                       double t,
                       double dt,
                       IntegrationMethod method,
                       TransientSystem& sys,
                       Diagnostics& diags,
                       bool residOnly = false);

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_TRANSIENT_ASSEMBLY_HPP
