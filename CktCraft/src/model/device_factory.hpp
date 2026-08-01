// device_factory.hpp — 从扁平化器件数据构造 DeviceModel wrapper 实例
//
// 连接解析层(FlatDevice/FlatModel)与模型层(DeviceModel)。
// 内置线性器件直接构造 wrapper；半导体器件通过 vaParser 生成模型构造。
#ifndef RFSIM_MODEL_DEVICE_FACTORY_HPP
#define RFSIM_MODEL_DEVICE_FACTORY_HPP

#include "device_model.hpp"
#include "../circuit/circuit.hpp"
#include "../parser/ast.hpp"
#include <memory>
#include <string>
#include <unordered_map>

namespace rfsim {

// 工厂结果：器件实例列表 + 诊断
struct FactoryResult {
    std::vector<std::unique_ptr<DeviceModel>> devices;
    // 总节点数（电路节点 + 器件内部节点），供求解器分配矩阵
    uint32_t totalNodes = 0;
    Diagnostics diags;
    bool ok = false;
};

using ModelLookup = std::unordered_map<std::string, const FlatModel*>;

// 参数求值上下文
struct ParamEnv {
    const ParamList* globalParams = nullptr;
    const ModelLookup* models = nullptr;
    // 模型库搜索路径。历史 OSDI 库搜索目录，OSDI 路径移除后暂无消费者，
    // 保留字段以兼容 CLI -L 参数（deprecated）。
    std::string libSearchDir;
    // 器件温度（K），默认 300.15K（室温）。.options temp=<C> 或 .temp 扫描覆盖。
    double temperature = 300.15;
    // scale：HSPICE .option scale=<val> 指定的几何缩放因子。
    // MOSFET 的 W/L/AD/AS/PD/PS/NRD/NRS 值 × scale = 实际尺寸（米）。
    // 例如 scale=1u -> W=2 意味着 W=2e-6 米。默认 1（无缩放）。
    double scale = 1.0;
    // scalem：面积缩放因子（HSPICE .option scalem=<val>）。
    // AD/AS 额外乘 scalem（W/PD/PS/L/NRD/NRS 不受影响）。默认 1。
    double scalem = 1.0;
    // 用户 .func 定义（从 Netlist.funcDefs 传入）
    const std::vector<FuncDef>* funcDefs = nullptr;
};

// 从扁平化电路构造器件 wrapper 列表
FactoryResult buildDeviceModels(const Circuit& circuit, const ParamEnv& env);

// 单个器件构造（供测试单独调用）
// internalNodeBase: 器件内部节点全局编号分配基数（in/out）。
std::unique_ptr<DeviceModel> buildDevice(const FlatDevice& fd,
                                         const FlatModel* model,
                                         const ParamEnv& env,
                                         NodeId& internalNodeBase,
                                         Diagnostics& diags);

} // namespace rfsim

#endif // RFSIM_MODEL_DEVICE_FACTORY_HPP
