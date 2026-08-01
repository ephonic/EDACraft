// generated_registry.cpp — Verilog-A 生成模型注册表实现
//
// 每新增一个生成模型：
//   1. vaParser <model>.va src/model/generated/<name> --format=rfsim
//      （同时产出 <name>_reg.inc 注册片段）
//   2. CktCraft/tools/regen_registry.sh  自动重写下面两个 AUTO 标记段
// AUTO 标记段内请勿手改。
#include "generated_registry.hpp"
// >>> AUTO-INCLUDES (regen_registry.sh)
#include "bjt505_gen.h"
#include "bsim3_gen.h"
#include "bsim4va_gen.h"
#include "bsimcmg_gen.h"
#include "bsimsoi_gen.h"
#include "cap_linear_gen.h"
#include "diode_va_gen.h"
#include "diode_vt_gen.h"
#include "ekv_gen.h"
#include "nmos_sh_gen.h"
#include "simple_diode_gen.h"
// <<< AUTO-INCLUDES

#include <unordered_map>

namespace rfsim {

using GenFactoryFn = std::unique_ptr<DeviceModel> (*)(
    const std::string&, const std::vector<NodeId>&, const ParamList&, const ParamList&);

template <typename T>
static std::unique_ptr<DeviceModel> makeGen(const std::string& name,
                                            const std::vector<NodeId>& nodes,
                                            const ParamList& instanceParams,
                                            const ParamList& modelParams) {
    return std::make_unique<T>(name, nodes, instanceParams, modelParams);
}

static const std::unordered_map<std::string, GenFactoryFn> kRegistry = {
// >>> AUTO-REGISTRY (regen_registry.sh)
    {"bjt505va", &makeGen<Bjt505vaGenModel>},
    {"bsim3_va", &makeGen<Bsim3_vaGenModel>},
    {"bsim4va", &makeGen<Bsim4vaGenModel>},
    {"bsimcmg", &makeGen<BsimcmgGenModel>},
    {"bsimsoi", &makeGen<BsimsoiGenModel>},
    {"cap_linear", &makeGen<Cap_linearGenModel>},
    {"diode_va", &makeGen<Diode_vaGenModel>},
    {"diode_vt", &makeGen<Diode_vtGenModel>},
    {"ekv_va", &makeGen<Ekv_vaGenModel>},
    {"nmos_sh", &makeGen<Nmos_shGenModel>},
    {"simple_diode", &makeGen<Simple_diodeGenModel>},
// <<< AUTO-REGISTRY
};

bool hasGeneratedModel(const std::string& modelType) {
    return kRegistry.find(modelType) != kRegistry.end();
}

std::unique_ptr<DeviceModel> createGeneratedModel(
    const std::string& modelType,
    const std::string& instName,
    const std::vector<NodeId>& nodes,
    const ParamList& instanceParams,
    const ParamList& modelParams) {
    auto it = kRegistry.find(modelType);
    if (it == kRegistry.end()) return nullptr;
    return it->second(instName, nodes, instanceParams, modelParams);
}

} // namespace rfsim
