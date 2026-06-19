// osdi_client.cpp — OSDI 器件实例客户端实现
#include "osdi_client.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace rfsim {

OsdiModelBlock::~OsdiModelBlock() {
    if (modelData) std::free(modelData);
}

OsdiClient::~OsdiClient() {
    if (instData_) std::free(instData_);
}

namespace {

std::string toLower(std::string s) {
    for (auto& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

// 通过 descriptor->access 查找参数 id（按名字）。
// 遍历 param_opvar 表匹配名字或别名。返回 id，未找到返回 UINT32_MAX。
uint32_t findParamId(const OsdiDescriptor* d, const std::string& name, uint32_t kindMask) {
    if (!d || !d->param_opvar) return 0xFFFFFFFFu;
    std::string low = toLower(name);
    uint32_t n = d->num_params + d->num_instance_params + d->num_opvars;
    for (uint32_t i = 0; i < n; ++i) {
        const OsdiParamOpvar& p = d->param_opvar[i];
        // 某些 OSDI 库（如 bsimcmg）的计数会把实例参数重复计入 num_params，
        // 导致表尾出现无效条目。以 name 指针为空作为实际结束哨兵。
        if (!p.name || !p.name[0]) break;
        if ((p.flags & PARA_KIND_MASK) != kindMask) continue;
        if (toLower(p.name[0]) == low) return i;
        // name[1..num_alias] 是别名；做边界保护，避免异常 alias 数量导致越界
        uint32_t aliasCount = p.num_alias;
        if (aliasCount > 8) aliasCount = 8;
        for (uint32_t a = 1; a <= aliasCount; ++a) {
            if (p.name[a] && toLower(p.name[a]) == low) return i;
        }
    }
    return 0xFFFFFFFFu;
}

} // namespace

bool OsdiClient::init(std::shared_ptr<OsdiLibrary> lib,
                      std::shared_ptr<OsdiModelBlock> modelBlock,
                      std::vector<NodeId> nodes,
                      Diagnostics& diags,
                      const std::vector<std::pair<std::string, double>>& modelParams) {
    lib_ = std::move(lib);
    modelBlock_ = std::move(modelBlock);
    nodes_ = std::move(nodes);

    if (!modelBlock_ || !modelBlock_->descriptor) {
        diags.error({}, "OsdiClient::init: null model block");
        return false;
    }
    desc_ = modelBlock_->descriptor;

    // 分配并初始化模型数据块
    if (!modelBlock_->setup) {
        if (desc_->model_size == 0) {
            diags.error({}, std::string("OSDI model ") + (desc_->name ? desc_->name : "?") +
                        ": model_size is 0");
            return false;
        }
        modelBlock_->modelData = std::calloc(1, desc_->model_size);
        if (!modelBlock_->modelData) {
            diags.error({}, "calloc model data failed");
            return false;
        }

        // 先分配实例块：部分 access 实现写入模型参数时也需要非空 inst 指针
        if (desc_->instance_size == 0) {
            diags.error({}, std::string("OSDI model ") + (desc_->name ? desc_->name : "?") +
                        ": instance_size is 0");
            return false;
        }
        instData_ = std::calloc(1, desc_->instance_size);
        if (!instData_) {
            diags.error({}, "calloc instance data failed");
            return false;
        }

        // 先绑定模型参数，再调用 setup_model，使其基于给定值计算默认值
        for (const auto& [pn, pv] : modelParams) {
            if (!setModelParam(pn, pv)) {
                diags.warn({}, std::string("OSDI set model param '") + pn + "' failed");
            }
        }

        if (desc_->setup_model) {
            OsdiInitInfo info{};
            OsdiInitError errBuf[16];
            info.errors = errBuf;
            OsdiSimParas paras{};
            desc_->setup_model((void*)lib_.get(), modelBlock_->modelData, &paras, &info);
            if (info.num_errors > 0 && errBuf[0].code != 0) {
                diags.error({}, std::string("OSDI setup_model error code ") +
                            std::to_string(errBuf[0].code));
                // 不致命，继续
            }
        }
        modelBlock_->setup = true;
    } else {
        // 共享模型块：本实例仍需要独立的实例数据块
        if (desc_->instance_size == 0) {
            diags.error({}, std::string("OSDI model ") + (desc_->name ? desc_->name : "?") +
                        ": instance_size is 0");
            return false;
        }
        instData_ = std::calloc(1, desc_->instance_size);
        if (!instData_) {
            diags.error({}, "calloc instance data failed");
            return false;
        }
    }

    // setup_instance
    if (desc_->setup_instance) {
        OsdiInitInfo info{};
        OsdiInitError errBuf[16];
        info.errors = errBuf;
        double temp = 300.0; // 室温 300K，后续从 .options temp 读取
        OsdiSimParas paras{};
        desc_->setup_instance((void*)lib_.get(), instData_, modelBlock_->modelData,
                              temp, desc_->num_terminals, &paras, &info);
        if (info.num_errors > 0 && errBuf[0].code != 0) {
            diags.error({}, std::string("OSDI setup_instance error code ") +
                        std::to_string(errBuf[0].code));
        }
    }

    // 预分配 solve 缓冲与雅可比 scratch
    solveBuf_.assign(nodes_.size(), 0.0);
    jacScratch_.assign(desc_->num_jacobian_entries, 0.0);
    // node_mapping 由调用方在 eval/load_jacobian 前设置（全局行号）。
    // 初始化为本地序作为安全默认。
    if (desc_->node_mapping_offset != 0 && desc_->node_mapping_offset < desc_->instance_size) {
        uint32_t* nodeMap = reinterpret_cast<uint32_t*>(
            reinterpret_cast<char*>(instData_) + desc_->node_mapping_offset);
        for (uint32_t i = 0; i < desc_->num_nodes; ++i) nodeMap[i] = i;
    }

    // 分配瞬态状态向量并在实例块中写入起始索引（使用 0，表示各实例独立数组）
    if (desc_->num_states > 0) {
        prevState_.assign(desc_->num_states, 0.0);
        nextState_.assign(desc_->num_states, 0.0);
        if (desc_->state_idx_off != 0 &&
            desc_->state_idx_off + sizeof(uint32_t) <= desc_->instance_size) {
            uint32_t* idxPtr = reinterpret_cast<uint32_t*>(
                reinterpret_cast<char*>(instData_) + desc_->state_idx_off);
            *idxPtr = 0;
        }
    }
    return true;
}

// 设置 node_mapping（本地节点 -> 全局求解向量位置，0-based）
void OsdiClient::setNodeMapping(const std::vector<uint32_t>& nodeMap) {
    if (!desc_ || !instData_ || desc_->node_mapping_offset == 0) return;
    uint32_t* nm = reinterpret_cast<uint32_t*>(
        reinterpret_cast<char*>(instData_) + desc_->node_mapping_offset);
    for (uint32_t i = 0; i < desc_->num_nodes && i < nodeMap.size(); ++i) nm[i] = nodeMap[i];
}

bool OsdiClient::setModelParam(const std::string& name, double value) {
    if (!desc_ || !desc_->access || !modelBlock_ || !modelBlock_->modelData) return false;
    uint32_t id = findParamId(desc_, name, PARA_KIND_MODEL);
    if (id == 0xFFFFFFFFu) return false;
    void* ptr = desc_->access(nullptr, modelBlock_->modelData, id, ACCESS_FLAG_SET);
    if (!ptr) return false;
    *static_cast<double*>(ptr) = value;
    return true;
}

bool OsdiClient::setInstanceParam(const std::string& name, double value) {
    if (!desc_ || !desc_->access || !instData_) return false;
    uint32_t id = findParamId(desc_, name, PARA_KIND_INST);
    if (id == 0xFFFFFFFFu) return false;
    void* ptr = desc_->access(instData_, modelBlock_->modelData, id, ACCESS_FLAG_SET | ACCESS_FLAG_INSTANCE);
    if (!ptr) return false;
    *static_cast<double*>(ptr) = value;
    return true;
}

namespace {

const std::vector<double>* ensureSolveBuf(const std::vector<NodeId>& nodes,
                                          const std::vector<double>& nodeVoltages,
                                          std::vector<double>& solveBuf) {
    NodeId maxId = 0;
    for (NodeId n : nodes) if (n > maxId) maxId = n;
    if (nodeVoltages.size() <= maxId) {
        solveBuf = nodeVoltages;
        if (solveBuf.size() <= maxId) solveBuf.resize(maxId + 1, 0.0);
        return &solveBuf;
    }
    return &nodeVoltages;
}

} // namespace

uint32_t OsdiClient::evalDC(const std::vector<double>& nodeVoltages, uint32_t extraFlags,
                            bool calcJacobian) {
    if (!desc_ || !desc_->eval || !instData_) return EVAL_RET_FLAG_FATAL;
    for (double v : nodeVoltages)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;

    const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, nodeVoltages, solveBuf_);

    OsdiSimInfo info{};
    info.paras.names = nullptr;
    info.paras.vals = nullptr;
    info.paras.names_str = nullptr;
    info.paras.vals_str = nullptr;
    info.abstime = 0.0;
    info.prev_solve = const_cast<double*>(solvePtr->data());
    // 某些模型（如 BSIM4）即使在 DC 下也会访问 prev/next_state 指针，
    // 因此提供非空零数组避免空指针解引用。prev/next 必须指向不同缓冲区，
    // 防止模型在写入 next_state 时破坏 prev_state。
    // 使用实例私有缓冲，避免 static 共享导致状态污染或崩溃。
    if (desc_->num_states > dcPrevState_.size()) dcPrevState_.assign(desc_->num_states, 0.0);
    if (desc_->num_states > dcNextState_.size()) dcNextState_.assign(desc_->num_states, 0.0);
    if (desc_->num_states > 0) {
        std::fill(dcPrevState_.begin(), dcPrevState_.end(), 0.0);
        std::fill(dcNextState_.begin(), dcNextState_.end(), 0.0);
    }
    info.prev_state = desc_->num_states > 0 ? dcPrevState_.data() : nullptr;
    info.next_state = desc_->num_states > 0 ? dcNextState_.data() : nullptr;
    uint32_t flags = CALC_RESIST_RESIDUAL | ANALYSIS_DC | extraFlags;
    if (calcJacobian) flags |= CALC_RESIST_JACOBIAN;
    info.flags = flags;

    // eval 前把 jacobian 指针数组指向安全 scratch，避免写入已释放的调用方缓冲区
    if (desc_->jacobian_ptr_resist_offset != 0 &&
        desc_->jacobian_ptr_resist_offset + sizeof(void*) * desc_->num_jacobian_entries <= desc_->instance_size) {
        void** slot = reinterpret_cast<void**>(
            reinterpret_cast<char*>(instData_) + desc_->jacobian_ptr_resist_offset);
        for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e)
            slot[e] = &jacScratch_[e];
    }

    uint32_t ret = desc_->eval((void*)lib_.get(), instData_, modelBlock_->modelData, &info);
    limitingInitialized_ = true;
    return ret;
}

uint32_t OsdiClient::evalTransient(const std::vector<double>& prevSolve,
                                   double t, double dt, double alpha,
                                   uint32_t extraFlags) {
    if (!desc_ || !desc_->eval || !instData_) return EVAL_RET_FLAG_FATAL;
    for (double v : prevSolve)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;
    (void)dt; (void)alpha;

    const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, prevSolve, solveBuf_);

    OsdiSimInfo info{};
    info.paras.names = nullptr;
    info.paras.vals = nullptr;
    info.paras.names_str = nullptr;
    info.paras.vals_str = nullptr;
    info.abstime = t;
    info.prev_solve = const_cast<double*>(solvePtr->data());
    info.prev_state = prevState_.empty() ? nullptr : prevState_.data();
    info.next_state = nextState_.empty() ? nullptr : nextState_.data();
    uint32_t flags = CALC_RESIST_RESIDUAL | CALC_REACT_RESIDUAL |
                     CALC_RESIST_JACOBIAN | CALC_REACT_JACOBIAN |
                     CALC_RESIST_LIM_RHS | CALC_REACT_LIM_RHS |
                     ENABLE_LIM | ANALYSIS_TRAN | extraFlags;
    if (!limitingInitialized_) flags |= INIT_LIM;
    info.flags = flags;

    // eval 前把 jacobian 指针数组指向安全 scratch
    if (desc_->jacobian_ptr_resist_offset != 0 &&
        desc_->jacobian_ptr_resist_offset + sizeof(void*) * desc_->num_jacobian_entries <= desc_->instance_size) {
        void** slot = reinterpret_cast<void**>(
            reinterpret_cast<char*>(instData_) + desc_->jacobian_ptr_resist_offset);
        for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e)
            slot[e] = &jacScratch_[e];
    }

    uint32_t ret = desc_->eval((void*)lib_.get(), instData_, modelBlock_->modelData, &info);
    limitingInitialized_ = true;
    return ret;
}

void OsdiClient::loadResidualResist(std::vector<double>& dst) const {
    if (!desc_ || !desc_->load_residual_resist || !instData_) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    dst.assign(desc_->num_nodes, 0.0);
    desc_->load_residual_resist(instData_, modelBlock_->modelData, dst.data());
}

void OsdiClient::loadSpiceRhsTran(std::vector<double>& dst,
                                  const std::vector<double>& prevSolve,
                                  double alpha) const {
    if (!desc_ || !instData_) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    dst.assign(desc_->num_nodes, 0.0);
    if (desc_->load_spice_rhs_tran) {
        const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, prevSolve, solveBuf_);
        desc_->load_spice_rhs_tran(instData_, modelBlock_->modelData, dst.data(),
                                   const_cast<double*>(solvePtr->data()), alpha);
    } else if (desc_->load_residual_resist) {
        // 回退到 DC 残差（适用于无内部动态状态的模型）
        desc_->load_residual_resist(instData_, modelBlock_->modelData, dst.data());
    }
}

void OsdiClient::loadJacobianResistWith(double** targets, const std::vector<uint32_t>& nodeMap) {
    if (!desc_ || !instData_ || !desc_->load_jacobian_resist || !targets) return;

    // 1. 更新 node_mapping（本地节点 -> 全局行号）
    if (desc_->node_mapping_offset != 0) {
        uint32_t* nm = reinterpret_cast<uint32_t*>(
            reinterpret_cast<char*>(instData_) + desc_->node_mapping_offset);
        for (uint32_t i = 0; i < desc_->num_nodes && i < nodeMap.size(); ++i) nm[i] = nodeMap[i];
    }

    // 2. 写入 per-entry 目标指针数组
    uint32_t off = desc_->jacobian_ptr_resist_offset;
    if (off == 0 || off + sizeof(void*) * desc_->num_jacobian_entries > desc_->instance_size) return;
    void** slot = reinterpret_cast<void**>(
        reinterpret_cast<char*>(instData_) + off);
    for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e) slot[e] = targets[e];

    // 3. 调用 OSDI load（累加贡献到 targets 指向的位置）
    desc_->load_jacobian_resist(instData_, modelBlock_->modelData);
}

void OsdiClient::loadJacobianResist() {
    // OSDI load_jacobian_resist(inst, model):
    //   对每个 jacobian entry e:
    //     ptr = inst.jacobian_ptr_resist[e]   // double*
    //     *ptr += jac_value(e)               // 累加贡献
    // 即 jacobian_ptr_resist_offset 处存的是 [double*; num_entries] 指针数组，
    // 每个指针指向仿真器矩阵中该 entry 的目标位置。
    // 仿真器需先把这些目标指针写入实例块。
    if (!desc_ || !instData_ || !desc_->load_jacobian_resist || !jacTargets_) return;

    uint32_t off = desc_->jacobian_ptr_resist_offset;
    if (off == 0 || off + sizeof(void*) * desc_->num_jacobian_entries > desc_->instance_size) return;
    // 写入指针数组
    void** slot = reinterpret_cast<void**>(
        reinterpret_cast<char*>(instData_) + off);
    for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e) {
        slot[e] = static_cast<void*>(jacTargets_[e]);
    }
    // 调用 OSDI load：它会通过这些指针把雅可比值累加进矩阵
    desc_->load_jacobian_resist(instData_, modelBlock_->modelData);
}

void OsdiClient::loadJacobianTranWith(double** targets, const std::vector<uint32_t>& nodeMap,
                                      double alpha) {
    if (!desc_ || !instData_ || !targets) return;

    // 更新 node_mapping
    if (desc_->node_mapping_offset != 0) {
        uint32_t* nm = reinterpret_cast<uint32_t*>(
            reinterpret_cast<char*>(instData_) + desc_->node_mapping_offset);
        for (uint32_t i = 0; i < desc_->num_nodes && i < nodeMap.size(); ++i) nm[i] = nodeMap[i];
    }

    uint32_t off = desc_->jacobian_ptr_resist_offset;
    if (off == 0 || off + sizeof(void*) * desc_->num_jacobian_entries > desc_->instance_size) return;
    void** slot = reinterpret_cast<void**>(
        reinterpret_cast<char*>(instData_) + off);
    for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e) slot[e] = targets[e];

    if (desc_->load_jacobian_tran) {
        desc_->load_jacobian_tran(instData_, modelBlock_->modelData, alpha);
    } else if (desc_->load_jacobian_resist) {
        desc_->load_jacobian_resist(instData_, modelBlock_->modelData);
    }
}

void OsdiClient::swapState() {
    prevState_.swap(nextState_);
    std::fill(nextState_.begin(), nextState_.end(), 0.0);
}

double OsdiClient::readJacobianEntryResist(uint32_t entryIdx) const {
    // loadJacobianResist 已通过 jacTargets_[entryIdx] 指针把值累加到目标位置。
    // 但仿真器矩阵是稀疏的，目标位置可能被多个 entry 共享。
    // 这里返回 jacTargets_[entryIdx] 所指位置的当前值。
    if (!desc_ || entryIdx >= desc_->num_jacobian_entries || !jacTargets_) return 0.0;
    return *jacTargets_[entryIdx];
}

double OsdiClient::readBoundStep() const {
    if (!desc_ || desc_->bound_step_offset == 0 ||
        desc_->bound_step_offset + sizeof(double) > desc_->instance_size || !instData_) {
        return 0.0;
    }
    const double* ptr = reinterpret_cast<const double*>(
        reinterpret_cast<const char*>(instData_) + desc_->bound_step_offset);
    double v = *ptr;
    return (v > 0.0) ? v : 0.0;
}

} // namespace rfsim
