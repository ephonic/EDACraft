// mna.hpp — MNA(修正节点分析)装配器
//
// 从器件列表构建线性方程组 G·x = b：
//   - G: 导纳矩阵 (n x n)，n = 节点数 + 电压源数
//   - x: 未知数 = [节点电压..., 电压源分支电流...]
//   - b: RHS（电流源注入 + 电压源约束值）
//
// MNA stamp 约定（地节点 0 不进方程，从 1 开始）：
//   Resistor(n1,n2,g): G[n1,n1]+=g  G[n2,n2]+=g  G[n1,n2]-=g  G[n2,n1]-=g
//   CurrentSource(n1,n2,I): b[n1]+=I  b[n2]-=I  (I 从 n2→n1 注入 n1 为正)
//   VoltageSource(n1,n2,V): 引入分支电流 i_k
//       G[n1, k] += 1   G[k, n1] += 1
//       G[n2, k] -= 1   G[k, n2] -= 1
//       b[k] = V
//
// 对非线性器件(OSDI)，DC 阶段在 Newton 迭代中用工作点线性化(G 为雅可比)，
// 装配接口相同。线性器件只装配一次。
#ifndef RFSIM_ASSEMBLY_MNA_HPP
#define RFSIM_ASSEMBLY_MNA_HPP

#include "matrix.hpp"
#include "../model/device_model.hpp"
#include "../circuit/circuit.hpp"
#include <memory>
#include <vector>

namespace rfsim {

// MNA 装配结果
struct MnaSystem {
    SparseMatrix G;          // 系统矩阵 (n x n)
    Vector       b;          // RHS
    uint32_t     numNodes = 0;     // 非地节点数
    uint32_t     numBranches = 0; // 电压源分支数
    uint32_t     dim() const noexcept { return numNodes + numBranches; }

    // 节点电压求解结果（求解后填充，索引=NodeId）
    std::vector<double> nodeVoltages;
};

struct AssembleResult {
    MnaSystem   system;
    // 电压源实例索引 -> 分支电流未知数偏移（dim - numBranches 起）
    std::vector<uint32_t> vsBranchOffsets;
    Diagnostics diags;
    bool ok = false;
};

// 装配 MNA 系统。
//   numNodes: 非地节点数（节点 1..numNodes）
//   devices:  器件 wrapper 列表
// 先 stamp 线性器件；非线性器件在工作点未给时跳过（Newton 迭代时再 stamp）。
AssembleResult assembleMna(uint32_t numNodes,
                           const std::vector<std::unique_ptr<DeviceModel>>& devices,
                           const std::vector<double>* nodeVoltages = nullptr);

// 在已有 MnaSystem 上重新装配雅可比/RHS（Newton 迭代每步），
// 用器件在当前工作点的线性化贡献。
void reassemble(MnaSystem& sys,
                const std::vector<std::unique_ptr<DeviceModel>>& devices,
                const std::vector<double>& nodeVoltages,
                const std::vector<uint32_t>& vsBranchOffsets);

} // namespace rfsim

#endif // RFSIM_ASSEMBLY_MNA_HPP
