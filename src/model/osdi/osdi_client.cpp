// osdi_client.cpp — OSDI 器件实例客户端实现
#include "osdi_client.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>

#ifdef _WIN32
#include <windows.h>
#endif

namespace rfsim {

// 判断指针是否指向可读内存。用于防护 OSDI 模型表尾越界访问：
// 实测部分 OpenVAF/OpenVAF-Reloaded 编译的 dll 在 param_opvar[] 与
// jacobian_entries[] 末尾会接续其它 dll 内部数据（非 NULL，但不是有效指针），
// 直接 deref 会 SEGV。本函数轻量探测：地址在用户态范围 (0..0x7FFFFFFFFFFF) 且
// 第一字节可读（_WIN32 下用 VirtualQuery，其它平台用读自陷）。
// 注意：OSDI 表条目的 name 字段总是指向 dll .rdata 段的 C 字符串；任何越界"指针"
// 通常是小整数 (0x500000004 之类)，明显不在合法用户态段。
static bool isReadableCString(const char* p) {
    if (!p) return false;
    // 合法用户态虚拟地址范围 (x86_64): 0..0x00007FFFFFFFFFFF
    // 排除明显的小整数伪装指针 (param_opvar 末尾越界条目的典型形态)
    auto addr = reinterpret_cast<uintptr_t>(p);
    if (addr < 0x10000) return false;        // 低于 64KB：必定不是有效映射
    if (addr > 0x7FFFFFFFFFFFull) return false;
#ifdef _WIN32
    MEMORY_BASIC_INFORMATION mbi;
    if (VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return false;
    if (mbi.State != MEM_COMMIT) return false;
    if (mbi.Protect & PAGE_NOACCESS) return false;
    if (mbi.Protect & PAGE_GUARD) return false;
    return true;
#else
    // 非 Windows: 尝试 1 字节读，触发 SIGSEGV 即不安全。这里保守返回 true
    // 让调用方依赖 errno/signal；非 Windows 暂无生产路径，故省略复杂逻辑。
    return true;
#endif
}

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
    // 防护：部分 OSDI dll 在 param_opvar[] 末尾接续其它 dll 内部数据
    // (非 NULL，但不是有效 C 字符串指针)。表尾哨兵必须经 isReadableCString
    // 验证，否则 deref p.name[0] 触发 SEGV。
    for (uint32_t i = 0; i < n; ++i) {
        const OsdiParamOpvar& p = d->param_opvar[i];
        // p.name 是 char** (别名数组指针)；空指针或越界非指针要排除。
        // 实测部分 OpenVAF dll 的 param_opvar[] 末尾接续其它数据，
        // .name 字段是 0x500000004 之类小整数，deref 触发 SEGV。
        const char* firstAlias = (p.name && isReadableCString(reinterpret_cast<const char*>(p.name)))
                                  ? p.name[0] : nullptr;
        if (!isReadableCString(firstAlias)) break;
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

// OSDI $simparam 默认表
//
// OpenVAF 把 Verilog-A 中的 `$simparam("name", default)` 翻译为线性扫描：
//     while (paras.names[i] != NULL) {
//         if (strcmp(paras.names[i], "name") == 0) return paras.vals[i];
//         ++i;
//     }
//     return default;
// 因此 paras.names 必须至少是一个 NULL-terminated 数组（可以只有终结符）。
// 如果 paras.names == NULL，模型在 setup_model / setup_instance / eval 中
// 一旦调用 $simparam 就会解引用空指针而崩溃（如 diode_va 在参数初始化阶段
// 访问 $simparam("minr",1m)，eval 期间访问 $simparam("gmin",1e-12)）。
//
// 这里提供一组常见仿真器参数默认值，让模型可以在未显式传值时拿到合理值；
// 同时配合 NULL 终结符兜住未列出的查询，保证 default 分支返回。
struct DefaultSimParas {
    std::vector<std::string> ownedNames;     // 持有 char* 的所有权
    std::vector<char*>       names;          // [n+1]，最后一个为 nullptr
    std::vector<double>      vals;           // [n]
    std::vector<char*>       namesStr;       // [1] = nullptr
    std::vector<char*>       valsStr;        // [1] = nullptr

    DefaultSimParas() {
        const std::pair<const char*, double> kv[] = {
            {"gmin",         1e-12 },
            {"minr",         1e-3  },
            {"imax",         1.0   },
            {"imelt",        1e-3  },
            {"scale",        1.0   },
            {"shrink",       0.0   },
            {"tnom",         300.15},
            {"temp",         300.15},
            {"rthresh",      1e-3  },
            {"sourceFactor", 1.0   },
            {"abstol",       1e-12 },
            {"reltol",       1e-3  },
        };
        constexpr size_t N = sizeof(kv) / sizeof(kv[0]);
        ownedNames.reserve(N);
        names.reserve(N + 1);
        vals.reserve(N);
        for (const auto& p : kv) {
            ownedNames.emplace_back(p.first);
            vals.push_back(p.second);
        }
        // 在 ownedNames 全部 push 完之后再取地址，防止重分配让指针失效
        for (auto& s : ownedNames) names.push_back(s.data());
        names.push_back(nullptr);
        namesStr.push_back(nullptr);
        valsStr.push_back(nullptr);
    }

    OsdiSimParas build() const {
        OsdiSimParas p{};
        p.names     = const_cast<char**>(names.data());
        p.vals      = const_cast<double*>(vals.data());
        p.names_str = const_cast<char**>(namesStr.data());
        p.vals_str  = const_cast<char**>(valsStr.data());
        return p;
    }
};

const DefaultSimParas& defaultSimParas() {
    static const DefaultSimParas s;
    return s;
}

} // namespace

bool OsdiClient::init(std::shared_ptr<OsdiLibrary> lib,
                      std::shared_ptr<OsdiModelBlock> modelBlock,
                      std::vector<NodeId> nodes,
                      Diagnostics& diags,
                      const std::vector<std::pair<std::string, double>>& modelParams,
                      double temperature) {
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
            OsdiSimParas paras = defaultSimParas().build();
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
        double temp = temperature; // 来自调用方（默认 300.15K，可由 .options temp 覆盖）
        OsdiSimParas paras = defaultSimParas().build();
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
    // L7: 检查 state 向量（prevState_ 可能有 NaN）
    for (double v : prevState_)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;

    const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, nodeVoltages, solveBuf_);

    OsdiSimInfo info{};
    info.paras = defaultSimParas().build();
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
    // 默认启用 limiting 并计算 lim_rhs；装配层可选择是否使用。
    flags |= CALC_RESIST_LIM_RHS | ENABLE_LIM;
    if (!limitingInitialized_) flags |= INIT_LIM;
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
    // L7: 检查 state 向量
    for (double v : prevState_)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;
    (void)dt; (void)alpha;

    const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, prevSolve, solveBuf_);

    OsdiSimInfo info{};
    info.paras = defaultSimParas().build();
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

// V3-MR Phase2: 只算 residual 不算 jacobian（省 jacobian 计算开销）
uint32_t OsdiClient::evalTransientResidOnly(const std::vector<double>& prevSolve,
                                             double t, double dt, double alpha) {
    if (!desc_ || !desc_->eval || !instData_) return EVAL_RET_FLAG_FATAL;
    for (double v : prevSolve)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;
    // L7: 检查 state 向量
    for (double v : prevState_)
        if (std::isnan(v) || std::isinf(v)) return EVAL_RET_FLAG_FATAL;
    (void)dt; (void)alpha;

    const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, prevSolve, solveBuf_);

    OsdiSimInfo info{};
    info.paras = defaultSimParas().build();
    info.abstime = t;
    info.prev_solve = const_cast<double*>(solvePtr->data());
    info.prev_state = prevState_.empty() ? nullptr : prevState_.data();
    info.next_state = nextState_.empty() ? nullptr : nextState_.data();
    // 只算 residual + lim_rhs，不算 jacobian
    uint32_t flags = CALC_RESIST_RESIDUAL | CALC_REACT_RESIDUAL |
                     CALC_RESIST_LIM_RHS | CALC_REACT_LIM_RHS |
                     ENABLE_LIM | ANALYSIS_TRAN;
    if (!limitingInitialized_) flags |= INIT_LIM;
    info.flags = flags;

    uint32_t ret = desc_->eval((void*)lib_.get(), instData_, modelBlock_->modelData, &info);
    limitingInitialized_ = true;
    return ret;
}

namespace {

// V2-γ C3 修复：OSDI load_residual_resist / load_spice_rhs / load_limit_rhs
// 按规范向 GLOBAL 求解向量散射写入（dst[node_mapping[localIdx]] += contrib），
// 但本仓库的装配层将 dst 视为 LOCAL 索引（dst[localIdx] 对应 nodes_[localIdx]）。
// 这两种不一致导致 BSIM4 collapse 时（dnodeprime → drain）当 drain NodeId 数值
// 恰好等于某个本地索引时，散射写到的 dst 位置被装配层错误地解释为另一个
// 本地节点的残差，导致对称性破坏（C3 / EightFingerBalanced "node-ID-4 specific"）。
//
// 解法：在 OSDI 调用前分配 GLOBAL-sized 暂存（按 nodes_ 的最大 NodeId 决定大小），
// 调用后再做带 collapse 去重的 gather：每个全局 NodeId 只允许第一个本地索引取走值，
// 后续同 NodeId 的本地索引置 0；ground 节点丢弃。
//
// 关于符号约定（V2-γ C3 续）：
//   OSDI 0.3 / OpenVAF 的 load_residual_resist 写入的是 KCL "current OUT of node"
//   形式残差（外部网络看到该器件在该节点上"抽走"的电流）。本仓库的线性器件 stamp
//   遵循同一约定（resistor.cpp 中 F[n1]+=iL，iL 为流出 n1 的电流）。因此 gather
//   阶段**不**做符号翻转，把 OpenVAF 的 "out" 残差原样交给装配层；装配层
//   （dc_op.cpp / transient_assembly.cpp）使用 F += dc.f / G += jac 同号累加，
//   与线性器件保持符号一致。
void scatterGlobalThenGatherLocal(
    const OsdiDescriptor* desc,
    const std::vector<NodeId>& nodes,
    std::vector<double>& dstLocal,
    const std::function<void(double* globalBuf)>& callOsdi) {
    if (!desc) {
        dstLocal.clear();
        return;
    }
    NodeId maxId = 0;
    for (NodeId n : nodes) if (n > maxId) maxId = n;
    std::vector<double> globalBuf(static_cast<size_t>(maxId) + 1, 0.0);
    callOsdi(globalBuf.data());
    dstLocal.assign(desc->num_nodes, 0.0);
    std::vector<uint8_t> taken(globalBuf.size(), 0);
    uint32_t n = desc->num_nodes;
    for (uint32_t i = 0; i < n && i < nodes.size(); ++i) {
        NodeId g = nodes[i];
        if (g == 0) continue;                  // 接地：丢弃
        if (g >= globalBuf.size()) continue;   // 越界保护
        if (taken[g]) continue;                // collapse 去重：值已由更早的本地索引取走
        dstLocal[i] = globalBuf[g];           // 不翻转：保留 OpenVAF 残差原符号
        taken[g] = 1;
    }
}

} // namespace

void OsdiClient::loadResidualResist(std::vector<double>& dst) const {
    if (!desc_ || !desc_->load_residual_resist || !instData_) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
        desc_->load_residual_resist(instData_, modelBlock_->modelData, g);
    });
}

// H4 修复：取回反应性残差（电荷 Q）。需 eval 时传 CALC_REACT_RESIDUAL flag。
void OsdiClient::loadResidualReact(std::vector<double>& dst) const {
    if (!desc_ || !desc_->load_residual_react || !instData_) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
        desc_->load_residual_react(instData_, modelBlock_->modelData, g);
    });
}

void OsdiClient::loadSpiceRhsTran(std::vector<double>& dst,
                                  const std::vector<double>& prevSolve,
                                  double alpha) const {
    if (!desc_ || !instData_) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    if (desc_->load_spice_rhs_tran) {
        const std::vector<double>* solvePtr = ensureSolveBuf(nodes_, prevSolve, solveBuf_);
        scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
            desc_->load_spice_rhs_tran(instData_, modelBlock_->modelData, g,
                                       const_cast<double*>(solvePtr->data()), alpha);
        });
    } else if (desc_->load_residual_resist) {
        // H8: fallback 用 load_residual_resist，但 SPICE RHS = -residual，需翻转符号
        scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
            desc_->load_residual_resist(instData_, modelBlock_->modelData, g);
        });
        for (double& v : dst) v = -v;  // residual → SPICE RHS
    } else {
        dst.assign(desc_->num_nodes, 0.0);
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

void OsdiClient::loadJacobianReactWith(double** targets, const std::vector<uint32_t>& nodeMap,
                                       double alpha) {
    if (!desc_ || !instData_ || !targets) return;

    if (desc_->node_mapping_offset != 0) {
        uint32_t* nm = reinterpret_cast<uint32_t*>(
            reinterpret_cast<char*>(instData_) + desc_->node_mapping_offset);
        for (uint32_t i = 0; i < desc_->num_nodes && i < nodeMap.size(); ++i) nm[i] = nodeMap[i];
    }

    // reactive Jacobian 使用每个 entry 独立的 react_ptr_off 指针槽
    for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e) {
        uint32_t off = desc_->jacobian_entries[e].react_ptr_off;
        if (off == 0 || off + sizeof(void*) > desc_->instance_size) continue;
        *reinterpret_cast<void**>(reinterpret_cast<char*>(instData_) + off) = targets[e];
    }

    if (desc_->load_jacobian_react) {
        desc_->load_jacobian_react(instData_, modelBlock_->modelData, alpha);
        return;
    }

    // 回退：tran - resist 近似电荷 Jacobian（使用电阻性指针数组）
    if (!desc_->load_jacobian_tran || !desc_->load_jacobian_resist) return;

    uint32_t off = desc_->jacobian_ptr_resist_offset;
    if (off == 0 || off + sizeof(void*) * desc_->num_jacobian_entries > desc_->instance_size) return;
    void** slot = reinterpret_cast<void**>(reinterpret_cast<char*>(instData_) + off);
    for (uint32_t e = 0; e < desc_->num_jacobian_entries; ++e) slot[e] = targets[e];

    uint32_t nE = desc_->num_jacobian_entries;
    std::vector<double> tranVal(nE, 0.0);
    desc_->load_jacobian_tran(instData_, modelBlock_->modelData, alpha);
    for (uint32_t e = 0; e < nE; ++e) tranVal[e] = *targets[e];
    for (uint32_t e = 0; e < nE; ++e) *targets[e] = 0.0;
    desc_->load_jacobian_resist(instData_, modelBlock_->modelData);
    for (uint32_t e = 0; e < nE; ++e) {
        *targets[e] = tranVal[e] - *targets[e];
    }
}

void OsdiClient::loadLimitRhsResist(std::vector<double>& dst) const {
    if (!desc_ || !instData_ || !desc_->load_limit_rhs_resist) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
        desc_->load_limit_rhs_resist(instData_, modelBlock_->modelData, g);
    });
}

void OsdiClient::loadLimitRhsReact(std::vector<double>& dst) const {
    if (!desc_ || !instData_ || !desc_->load_limit_rhs_react) {
        dst.assign(desc_ ? desc_->num_nodes : 0, 0.0);
        return;
    }
    scatterGlobalThenGatherLocal(desc_, nodes_, dst, [&](double* g) {
        desc_->load_limit_rhs_react(instData_, modelBlock_->modelData, g);
    });
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
