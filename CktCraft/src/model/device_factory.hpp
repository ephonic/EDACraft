// device_factory.hpp — 从扁平化器件数据构造 DeviceModel wrapper 实例
//
// 连接解析层(FlatDevice/FlatModel)与模型层(DeviceModel)。
// 内置线性器件直接构造 wrapper；半导体器件构造 OsdiModel（加载 OSDI 库）。
#ifndef RFSIM_MODEL_DEVICE_FACTORY_HPP
#define RFSIM_MODEL_DEVICE_FACTORY_HPP

#include "device_model.hpp"
#include "osdi/osdi_library.hpp"
#include "osdi/osdi_client.hpp"
#include "../circuit/circuit.hpp"
#include "../parser/ast.hpp"
#include <memory>
#include <string>
#include <unordered_map>

namespace rfsim {

// 工厂结果：器件实例列表 + 诊断
struct FactoryResult {
    std::vector<std::unique_ptr<DeviceModel>> devices;
    // 已加载的 OSDI 库（工厂持有所有权，OsdiModel 共享引用）
    std::vector<std::shared_ptr<OsdiLibrary>> libraries;
    // 总节点数（电路节点 + OSDI 器件内部节点），供求解器分配矩阵
    uint32_t totalNodes = 0;
    Diagnostics diags;
    bool ok = false;
};

using ModelLookup = std::unordered_map<std::string, const FlatModel*>;

// 参数求值上下文
struct ParamEnv {
    const ParamList* globalParams = nullptr;
    const ModelLookup* models = nullptr;
    // OSDI 库搜索路径（用于查找模型共享库）
    // 工厂会尝试: <libSearchDir>/<modelname>.dll|.so 以及 .model 里的 file= 参数
    std::string libSearchDir;
};

// 从扁平化电路构造器件 wrapper 列表
FactoryResult buildDeviceModels(const Circuit& circuit, const ParamEnv& env);

// V2-γ C3：同 modelcard 多实例共享 OsdiModelBlock。key 用 FlatModel*（同一 .model
// 定义指向同一指针）；value 是首个实例 setup_model 后的 block。后续相同 key 的
// OsdiModel 通过 useSharedModelBlock() 复用之，OsdiClient 跳过重复 setup_model。
using OsdiModelBlockCache =
    std::unordered_map<const FlatModel*, std::shared_ptr<OsdiModelBlock>>;

// 单个器件构造（供测试单独调用）
// internalNodeBase: OSDI 器件内部节点全局编号分配基数（in/out）。
// blockCache: 可选的共享模型块缓存（nullptr = 每实例独占 block，旧行为）。
std::unique_ptr<DeviceModel> buildDevice(const FlatDevice& fd,
                                         const FlatModel* model,
                                         const ParamEnv& env,
                                         std::vector<std::shared_ptr<OsdiLibrary>>& libCache,
                                         NodeId& internalNodeBase,
                                         Diagnostics& diags,
                                         OsdiModelBlockCache* blockCache = nullptr);

} // namespace rfsim

#endif // RFSIM_MODEL_DEVICE_FACTORY_HPP
