// generated_registry.hpp — Verilog-A 生成模型注册表
//
// 由 rfsim_codegen 生成的 <name>_gen.{h,cpp} 在此登记，device_factory 在
// .model 带 generated=1 参数时按类型名查找并构造（默认仍走 openvaf/OSDI，
// 见 device_factory.cpp 半导体分支）。
//
// 仅在 RFSIM_USE_GENERATED_MODELS=ON 时编译 generated_registry.cpp；
// 调用方需用 #ifdef RFSIM_USE_GENERATED_MODELS 保护。
#ifndef RFSIM_MODEL_GENERATED_REGISTRY_HPP
#define RFSIM_MODEL_GENERATED_REGISTRY_HPP

#include "../device_model.hpp"
#include "../../parser/ast.hpp"
#include <memory>
#include <string>
#include <vector>

namespace rfsim {

// 是否已注册该 VA module 名（即 .model 的 type 或 name）的生成模型
bool hasGeneratedModel(const std::string& modelType);

// 构造生成模型实例；未注册时返回 nullptr
std::unique_ptr<DeviceModel> createGeneratedModel(
    const std::string& modelType,
    const std::string& instName,
    const std::vector<NodeId>& nodes,
    const ParamList& instanceParams,
    const ParamList& modelParams);

} // namespace rfsim

#endif // RFSIM_MODEL_GENERATED_REGISTRY_HPP
