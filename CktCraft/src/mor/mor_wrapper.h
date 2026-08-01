// mor_wrapper.h — MOR (Model Order Reduction) 集成接口
//
// 两种模式：
//   1. 文件模式（mor_wrapper.cpp 已有）：amor 读网表 → 输出降阶网表 → 重新解析
//   2. 内存模式（新增）：amor 降阶后直接生成 R/C DeviceModel，插入仿真器器件列表
//
// 内存模式的核心：
//   amor 降阶后 _red_g_list / _red_c_list 是降阶后的稀疏矩阵（端口→端口的等效 G/C）。
//   从中提取 R=1/G 和 C 值，直接构造 Resistor/Capacitor DeviceModel，
//   替换原始 RC 网络中的内部节点——无需中间文件。
//
// 接口设计：
//   reduceRCDevices() 接收仿真器的器件列表 + 节点表，
//   把其中的线性 R/C 器件做 amor 降阶，
//   返回降阶后的器件列表（保留非线性器件 + 降阶后的等效 R/C）。
#ifndef RFSIM_MOR_WRAPPER_H
#define RFSIM_MOR_WRAPPER_H

#include "../model/device_model.hpp"
#include "../circuit/circuit.hpp"
#include <memory>
#include <string>
#include <vector>

namespace rfsim {

// MOR 降阶选项
struct MorOptions {
    int maxBlockSize = 35;      // amor 最大分区端口数
    double relativeTol = 1e-4;  // 分区相对容差
};

// 文件模式：对输入网表做 MOR 降阶，输出简化网表到 reducedPath。
bool runMorReduction(const std::string& inputPath,
                     const std::string& reducedPath,
                     const MorOptions& opts = {});

// 内存模式（核心）：对仿真器内部的 R/C 器件做降阶。
//
// 输入：
//   devices — 仿真器的器件列表（含 R/C/MOSFET 等）
//   circuit — 电路结构（节点表，用于确定端口节点）
//   portNodeIds — 端口节点列表（非线性器件连接的节点 = RC 网络的端口，降阶保留）
//
// 输出：
//   返回降阶后的器件列表——非线性器件原样保留，RC 部分被降阶后的等效 R/C 替换。
//   若降阶失败（MOR 未编译 / 无 RC 器件），返回空 vector（调用方用原始器件）。
//
// 原理：
//   1. 从 devices 中提取所有 R/C 器件，构建 G/C 矩阵（端口感知的）
//   2. 调用 amor 的 partition + reduction 做降阶
//   3. 从降阶矩阵提取等效 R/C 器件（R=1/G_ij, C=C_ij）
//   4. 非线性器件 + 降阶后的等效 R/C 组成新器件列表
std::vector<std::unique_ptr<DeviceModel>> reduceRCDevices(
    const std::vector<std::unique_ptr<DeviceModel>>& devices,
    const Circuit& circuit,
    const std::vector<NodeId>& portNodeIds,
    const MorOptions& opts = {});

// 判断 MOR 是否可用（编译时是否启用了 RFSIM_USE_MOR）
bool isMorAvailable();

} // namespace rfsim

#endif // RFSIM_MOR_WRAPPER_H
