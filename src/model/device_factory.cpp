// device_factory.cpp — 器件 wrapper 工厂实现
#include "device_factory.hpp"
#include "builtin_devices.hpp"
#include "osdi_model.hpp"
#include "../parser/expression.hpp"

#include <cmath>
#include <stdexcept>

namespace rfsim {

namespace {

// 取参数列表中命名参数的数值；支持 Number 与 Expr(参数引用)。
// Expr 形式会尝试在 env 中查找并求值；找不到返回 has=false。
// 将单个 ParamValue 解析为 double（支持 Number/Expr/字符串数值）。
bool resolveParamValue(const ParamValue& pv, const ParamEnv& env, double& out) {
    if (pv.kind == ParamValue::Kind::Number) { out = pv.num; return true; }
    if (pv.kind == ParamValue::Kind::Expr) {
        EvalContext ctx;
        registerBuiltinFunctions(ctx);
        if (env.globalParams) {
            for (const auto& [gn, gv] : *env.globalParams) {
                if (gv.kind == ParamValue::Kind::Number) ctx.vars[gn] = gv.num;
            }
        }
        std::string err;
        if (evaluateExpression(pv.str, ctx, out, err)) return true;
        auto it = ctx.vars.find(pv.str);
        if (it != ctx.vars.end()) { out = it->second; return true; }
        return false;
    }
    if (pv.kind == ParamValue::Kind::String) {
        try { out = std::stod(pv.str); return true; } catch (...) { return false; }
    }
    return false;
}

bool lookupNumber(const ParamList& params, const std::string& name,
                  const ParamEnv& env, double& out) {
    for (const auto& [pn, pv] : params) {
        if (pn != name) continue;
        if (pv.kind == ParamValue::Kind::Number) { out = pv.num; return true; }
        if (pv.kind == ParamValue::Kind::Expr) {
            // 尝试作为表达式求值（含全局参数引用）
            EvalContext ctx;
            registerBuiltinFunctions(ctx);
            if (env.globalParams) {
                for (const auto& [gn, gv] : *env.globalParams) {
                    if (gv.kind == ParamValue::Kind::Number) ctx.vars[gn] = gv.num;
                }
            }
            std::string err;
            double v = 0;
            if (evaluateExpression(pv.str, ctx, v, err)) { out = v; return true; }
            // 表达式也可能是纯参数名引用
            auto it = ctx.vars.find(pv.str);
            if (it != ctx.vars.end()) { out = it->second; return true; }
        }
        return false;
    }
    return false;
}

// 取位置参数第一个数值（用于 R/L/C/V/I 的主值）
bool lookupFirstPositionalNumber(const std::vector<ParamValue>& positional,
                                 const ParamEnv& env, double& out) {
    if (positional.empty()) return false;
    const auto& pv = positional.front();
    if (pv.kind == ParamValue::Kind::Number) { out = pv.num; return true; }
    if (pv.kind == ParamValue::Kind::Expr || pv.kind == ParamValue::Kind::String) {
        EvalContext ctx;
        registerBuiltinFunctions(ctx);
        if (env.globalParams) {
            for (const auto& [gn, gv] : *env.globalParams) {
                if (gv.kind == ParamValue::Kind::Number) ctx.vars[gn] = gv.num;
            }
        }
        std::string err; double v = 0;
        if (evaluateExpression(pv.str, ctx, v, err)) { out = v; return true; }
        auto it = ctx.vars.find(pv.str);
        if (it != ctx.vars.end()) { out = it->second; return true; }
    }
    return false;
}

} // namespace

std::unique_ptr<DeviceModel> buildDevice(const FlatDevice& fd,
                                         const FlatModel* model,
                                         const ParamEnv& env,
                                         std::vector<std::shared_ptr<OsdiLibrary>>& libCache,
                                         NodeId& internalNodeBase,
                                         Diagnostics& diags) {
    char c = fd.firstLetter;

    // 电阻 R: name n1 n2 value
    if (c == 'r') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": resistor needs 2 nodes"); return nullptr; }
        double r = 0;
        if (!lookupNumber(fd.params, "", env, r) &&
            !lookupFirstPositionalNumber(fd.positional, env, r)) {
            // R 也可能用 r=<value> 或第一个位置参
            if (!lookupNumber(fd.params, "r", env, r)) {
                diags.error(fd.loc, fd.name + ": resistor missing value"); return nullptr;
            }
        }
        try { return std::make_unique<Resistor>(fd.name, fd.nodes[0], fd.nodes[1], r); }
        catch (const std::exception& e) { diags.error(fd.loc, fd.name + ": " + e.what()); return nullptr; }
    }

    // 电流源 I: name n1 n2 value
    if (c == 'i') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": isource needs 2 nodes"); return nullptr; }
        double i = 0;
        if (!lookupFirstPositionalNumber(fd.positional, env, i)) {
            // I 源常带 SIN/PULSE 等波形，DC 值暂取第一个数值或 0
            i = 0;
        }
        return std::make_unique<CurrentSource>(fd.name, fd.nodes[0], fd.nodes[1], i);
    }

    // 电压源 V: name n1 n2 [dcval] [AC mag [phase]] [PULSE/SIN/...]
    if (c == 'v') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": vsource needs 2 nodes"); return nullptr; }
        double v = 0;
        bool haveDc = false;
        rfsim::Complex acMag(0.0, 0.0);
        // 遍历位置参数：首个数值为 DC 值；遇到 "ac"/"AC" 后的数值为 AC 幅度(+相位)
        for (size_t i = 0; i < fd.positional.size(); ++i) {
            const auto& pv = fd.positional[i];
            if (pv.kind == ParamValue::Kind::Number) {
                if (!haveDc) { v = pv.num; haveDc = true; }
            } else if (pv.kind == ParamValue::Kind::String || pv.kind == ParamValue::Kind::Expr) {
                std::string low = pv.str;
                for (auto& ch : low) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
                if (low == "ac") {
                    // 下一个数值是 AC 幅度，再下一个是相位
                    if (i + 1 < fd.positional.size() && fd.positional[i+1].kind == ParamValue::Kind::Number) {
                        double mag = fd.positional[i+1].num;
                        double phase = 0.0;
                        if (i + 2 < fd.positional.size() && fd.positional[i+2].kind == ParamValue::Kind::Number) {
                            phase = fd.positional[i+2].num;
                        }
                        double rad = phase * 3.14159265358979323846 / 180.0;
                        acMag = rfsim::Complex(mag * std::cos(rad), mag * std::sin(rad));
                        i += (i + 2 < fd.positional.size() && fd.positional[i+2].kind == ParamValue::Kind::Number) ? 2 : 1;
                    }
                } else if (low == "pulse" || low == "sin" || low == "exp" || low == "sffm") {
                    // 波形源：DC 值取其第一个参数（简化）
                    if (i + 1 < fd.positional.size() && fd.positional[i+1].kind == ParamValue::Kind::Number) {
                        if (!haveDc) { v = fd.positional[i+1].num; haveDc = true; }
                    }
                }
            }
        }
        auto vs = std::make_unique<VoltageSource>(fd.name, fd.nodes[0], fd.nodes[1], v);
        vs->setAcMag(acMag);
        return vs;
    }

    // 电容 C / 电感 L: DC 阶段 C 开路(不 stamp 导纳)、L 短路(小电阻近似)。
    // AC/频域由装配层用频域导纳 stamp。
    if (c == 'c') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": capacitor needs 2 nodes"); return nullptr; }
        double cap = 0;
        if (!lookupFirstPositionalNumber(fd.positional, env, cap) &&
            !lookupNumber(fd.params, "c", env, cap)) {
            diags.error(fd.loc, fd.name + ": capacitor missing value"); return nullptr;
        }
        try { return std::make_unique<Capacitor>(fd.name, fd.nodes[0], fd.nodes[1], cap); }
        catch (const std::exception& e) { diags.error(fd.loc, fd.name + ": " + e.what()); return nullptr; }
    }
    if (c == 'l') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": inductor needs 2 nodes"); return nullptr; }
        double ind = 0;
        if (!lookupFirstPositionalNumber(fd.positional, env, ind) &&
            !lookupNumber(fd.params, "l", env, ind)) {
            diags.error(fd.loc, fd.name + ": inductor missing value"); return nullptr; }
        try { return std::make_unique<Inductor>(fd.name, fd.nodes[0], fd.nodes[1], ind); }
        catch (const std::exception& e) { diags.error(fd.loc, fd.name + ": " + e.what()); return nullptr; }
    }

    // 半导体器件 (M/Q/D/Z/J/S/B) → OsdiModel
    if (c == 'm' || c == 'q' || c == 'd' || c == 'z' || c == 'j' || c == 's' || c == 'b') {
        std::string modelName = fd.model;
        // 确定模型类型名（用于匹配 OSDI descriptor）
        // SPICE 约定 .model name type：descriptor 通常以 type 或 name 命名
        const FlatModel* mdlDef = model;
        std::string typeOrName = modelName;
        if (mdlDef && !mdlDef->type.empty()) {
            // OSDI descriptor->name 通常对应模型实现名（如 bsim4, diode）
            // 而 .model 的 type 字段（如 nmos）是类别。descriptor 匹配优先用 type。
            typeOrName = mdlDef->type;
        }

        // 尝试加载 OSDI 库：
        //   1. .model 参数 file=<path>
        //   2. <libSearchDir>/<modelName>.dll|.so
        //   3. <libSearchDir>/<type>.dll|.so
        std::shared_ptr<OsdiLibrary> lib;
        const OsdiDescriptor* desc = nullptr;

        // 收集候选库路径
        std::vector<std::string> candidates;
        if (mdlDef) {
            for (const auto& [pn, pv] : mdlDef->params) {
                if (pn == "file" || pn == "osdi" || pn == "lib") {
                    if (pv.kind != ParamValue::Kind::Number && !pv.str.empty()) {
                        candidates.push_back(pv.str);
                    }
                }
            }
        }
        if (!env.libSearchDir.empty() && !modelName.empty()) {
#ifdef _WIN32
            candidates.push_back(env.libSearchDir + "\\" + modelName + ".dll");
            candidates.push_back(env.libSearchDir + "\\" + typeOrName + ".dll");
#else
            candidates.push_back(env.libSearchDir + "/lib" + modelName + ".so");
            candidates.push_back(env.libSearchDir + "/lib" + typeOrName + ".so");
#endif
        }

        for (const auto& path : candidates) {
            // 检查缓存（同路径只加载一次）
            for (auto& cached : libCache) {
                if (cached->path() == path) { lib = cached; break; }
            }
            if (!lib) {
                auto newLib = std::make_shared<OsdiLibrary>();
                std::string err;
                if (newLib->load(path, err)) {
                    lib = newLib;
                    libCache.push_back(lib);
                } else {
                    diags.warn(fd.loc, fd.name + ": cannot load OSDI lib " + path + ": " + err);
                    lib.reset();
                }
            }
            if (lib) {
                // 在库中查找匹配的 descriptor（先按 type，再按 name）
                desc = lib->findDescriptor(typeOrName);
                if (!desc && !modelName.empty()) desc = lib->findDescriptor(modelName);
                if (desc) break;
                lib.reset();
            }
        }

        if (!lib || !desc) {
            // 未找到库：构造占位 OsdiModel（ready=false），保留器件信息供诊断
            // 发出信息（非错误）：无 OSDI 库时该器件无法评估
            if (!candidates.empty()) {
                diags.warn(fd.loc, fd.name + ": no OSDI library found for model '" +
                           modelName + "' (tried " + std::to_string(candidates.size()) +
                           " paths); device will not be evaluated");
            }
            // 占位 OsdiModel：传 nullptr lib/descriptor，ready()=false
            auto placeholder = std::make_unique<OsdiModel>(fd.name, fd.nodes, nullptr, nullptr, fd.params, ParamList{});
            placeholder->setFallbackTypeName(typeOrName);
            (void)internalNodeBase;  // 占位不分配内部节点
            return placeholder;
        }

        // 提取并解析 .model 级参数（排除 OSDI 库控制关键字）
        ParamList modelParams;
        if (mdlDef) {
            for (const auto& [pn, pv] : mdlDef->params) {
                if (pn == "file" || pn == "osdi" || pn == "lib") continue;
                double val = 0.0;
                if (resolveParamValue(pv, env, val)) {
                    modelParams.push_back({pn, ParamValue{ParamValue::Kind::Number, val, "", SourceLoc{}}});
                } else {
                    diags.warn(fd.loc, fd.name + ": cannot resolve model parameter '" + pn + "'; skipped");
                }
            }
        }

        auto m = std::make_unique<OsdiModel>(fd.name, fd.nodes, lib, desc, fd.params, modelParams);
        m->setFallbackTypeName(typeOrName);
        if (!m->initialize(diags, internalNodeBase)) {
            diags.warn(fd.loc, fd.name + ": OSDI initialize failed");
        }
        return m;
    }

    diags.error(fd.loc, fd.name + ": unknown device type '" + std::string(1, c) + "'");
    return nullptr;
}

FactoryResult buildDeviceModels(const Circuit& circuit, const ParamEnv& env) {
    FactoryResult r;

    // 构建模型查找表
    ModelLookup models;
    for (const auto& m : circuit.models) models[m.name] = &m;

    ParamEnv envFull = env;
    envFull.models = &models;
    if (!envFull.globalParams) envFull.globalParams = &circuit.globalParams;

    // 内部节点编号分配基数：从电路最大节点号+1 开始（紧凑编号）
    NodeId internalNodeBase = static_cast<NodeId>(circuit.nodes.size()) + 1;
    r.totalNodes = static_cast<uint32_t>(circuit.nodes.size());

    for (const auto& fd : circuit.devices) {
        const FlatModel* mdl = nullptr;
        if (!fd.model.empty()) {
            auto it = models.find(fd.model);
            if (it != models.end()) mdl = it->second;
        }
        auto dev = buildDevice(fd, mdl, envFull, r.libraries, internalNodeBase, r.diags);
        if (dev) {
            // 累计内部节点数（OSDI 器件的 nodes 超过 num_terminals 的部分）
            r.devices.push_back(std::move(dev));
        }
    }

    // totalNodes = 电路节点 + 分配的内部节点（internalNodeBase 已递增）
    r.totalNodes = internalNodeBase - 1;  // 最大节点编号

    r.ok = !r.diags.has_errors();
    return r;
}

} // namespace rfsim
