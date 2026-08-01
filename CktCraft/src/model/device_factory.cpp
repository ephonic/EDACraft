// device_factory.cpp — 器件 wrapper 工厂实现（纯生成模型，无 OSDI 依赖）
#include "device_factory.hpp"
#include "builtin_devices.hpp"
#include "sparam_device.hpp"
#include "../parser/expression.hpp"
#include "generated/generated_registry.hpp"

#include <cmath>
#include <set>
#include <stdexcept>

namespace rfsim {

namespace {

// C2：构建一个 EvalContext，其 vars 包含所有已求值的全局参数。
// 多遍迭代求值：Expr 类型的全局参数（.param x='2*y'）在依赖的参数已求值后求值。
// 这修复了原实现只把 Number 类型全局参数加入 ctx、Expr 参数无法被引用的问题。
// 最多迭代 N 轮（每轮至少求值一个新参数则继续），处理顺序无关的前向引用。
EvalContext buildResolvedEvalContext(const ParamEnv& env) {
    EvalContext ctx;
    registerBuiltinFunctions(ctx);

    // 注册用户 .func 定义到 multiFuncs
    // .func name(a,b,...) 'body' -> 注册为 lambda：把实参绑定到 ctx.vars 后求值 body
    if (env.funcDefs) {
        for (const auto& fd : *env.funcDefs) {
            std::string fname = fd.name;
            for (auto& c : fname) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            std::vector<std::string> argNames = fd.args;
            std::string body = fd.body;
            ctx.multiFuncs[fname] = [argNames, body, &ctx](const std::vector<double>& args) -> double {
                if (args.size() < argNames.size()) return 0.0;
                // 把实参绑定到临时 vars（保存旧值，求值后恢复）
                std::vector<std::pair<std::string, double>> saved;
                for (size_t i = 0; i < argNames.size(); ++i) {
                    auto it = ctx.vars.find(argNames[i]);
                    if (it != ctx.vars.end()) saved.emplace_back(argNames[i], it->second);
                    ctx.vars[argNames[i]] = args[i];
                }
                double result = 0.0;
                std::string err;
                evaluateExpression(body, ctx, result, err);
                // 恢复旧值
                for (auto& [k, v] : saved) ctx.vars[k] = v;
                for (size_t i = 0; i < argNames.size(); ++i) ctx.vars.erase(argNames[i]);
                return result;
            };
        }
    }

    if (!env.globalParams) return ctx;
    // 第一遍：所有 Number 直接加入
    for (const auto& [gn, gv] : *env.globalParams) {
        if (gv.kind == ParamValue::Kind::Number) ctx.vars[gn] = gv.num;
    }
    // 多遍求值 Expr 全局参数，直到一轮无新进展或全部求值完
    const size_t total = env.globalParams->size();
    for (size_t round = 0; round <= total; ++round) {
        bool progressed = false;
        for (const auto& [gn, gv] : *env.globalParams) {
            if (gv.kind != ParamValue::Kind::Expr) continue;
            if (ctx.vars.count(gn)) continue;  // 已求值
            std::string err;
            double v = 0;
            if (evaluateExpression(gv.str, ctx, v, err)) {
                ctx.vars[gn] = v;
                progressed = true;
            } else {
                // 可能是纯参数名引用（未带算术）
                auto it = ctx.vars.find(gv.str);
                if (it != ctx.vars.end()) { ctx.vars[gn] = it->second; progressed = true; }
            }
        }
        if (!progressed) break;  // 剩余的都是无法求值（循环依赖/未定义引用）
    }
    return ctx;
}

// 取参数列表中命名参数的数值；支持 Number 与 Expr(参数引用)。
// Expr 形式会尝试在 env 中查找并求值；找不到返回 has=false。
// 将单个 ParamValue 解析为 double（支持 Number/Expr/字符串数值）。
bool resolveParamValue(const ParamValue& pv, const ParamEnv& env, double& out) {
    if (pv.kind == ParamValue::Kind::Number) { out = pv.num; return true; }
    if (pv.kind == ParamValue::Kind::Expr) {
        EvalContext ctx = buildResolvedEvalContext(env);
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
            EvalContext ctx = buildResolvedEvalContext(env);
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
        EvalContext ctx = buildResolvedEvalContext(env);
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
        Waveform pendingWaveform;  // 默认 type=DC，仅当显式 SIN/PULSE 才覆盖
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
                    // 收集波形参数：sin(vo va freq [td]) / pulse(v1 v2 td tr tf pw period)
                    if (low == "sin") {
                        Waveform wf; wf.type = Waveform::SIN;
                        auto getNum = [&](size_t j, double def) -> double {
                            if (j < fd.positional.size() && fd.positional[j].kind == ParamValue::Kind::Number)
                                return fd.positional[j].num;
                            return def;
                        };
                        wf.vo   = getNum(i+1, 0.0);
                        wf.va   = getNum(i+2, 0.0);
                        wf.freq = getNum(i+3, 0.0);
                        wf.td   = getNum(i+4, 0.0);
                        pendingWaveform = wf;
                        // 同时把 SIN 的 va 视作 AC 基频幅度（HB 用），允许用户后续显式 AC 覆盖
                        if (acMag == rfsim::Complex(0.0, 0.0)) {
                            acMag = rfsim::Complex(wf.va, 0.0);
                        }
                    } else if (low == "pulse") {
                        Waveform wf; wf.type = Waveform::PULSE;
                        auto getNum = [&](size_t j, double def) -> double {
                            if (j < fd.positional.size() && fd.positional[j].kind == ParamValue::Kind::Number)
                                return fd.positional[j].num;
                            return def;
                        };
                        wf.vo     = getNum(i+1, 0.0);
                        wf.va     = getNum(i+2, 0.0) - wf.vo;
                        wf.td     = getNum(i+3, 0.0);
                        wf.tr     = getNum(i+4, 0.0);
                        wf.tf     = getNum(i+5, 0.0);
                        wf.pw     = getNum(i+6, 0.0);
                        wf.period = getNum(i+7, 0.0);
                        pendingWaveform = wf;
                    } else if (low == "exp") {
                        // EXP(v1 v2 td1 tau1 td2 tau2)
                        Waveform wf; wf.type = Waveform::EXP;
                        auto getNum = [&](size_t j, double def) -> double {
                            if (j < fd.positional.size() && fd.positional[j].kind == ParamValue::Kind::Number)
                                return fd.positional[j].num;
                            return def;
                        };
                        wf.vo     = getNum(i+1, 0.0);       // v1
                        wf.va     = getNum(i+2, 0.0) - wf.vo; // v2-v1
                        wf.td     = getNum(i+3, 0.0);        // td1
                        wf.freq   = getNum(i+4, 1e-6);       // tau1
                        wf.pw     = getNum(i+5, 1e-6);       // td2
                        wf.period = getNum(i+6, 1e-6);       // tau2
                        pendingWaveform = wf;
                    } else if (low == "pwl") {
                        // PWL t1 v1 t2 v2 ...
                        Waveform wf; wf.type = Waveform::PWL;
                        for (size_t j = i+1; j + 1 < fd.positional.size(); j += 2) {
                            if (fd.positional[j].kind == ParamValue::Kind::Number &&
                                fd.positional[j+1].kind == ParamValue::Kind::Number)
                                wf.pwlPoints.emplace_back(fd.positional[j].num, fd.positional[j+1].num);
                        }
                        pendingWaveform = wf;
                    }
                }
            }
        }
        auto vs = std::make_unique<VoltageSource>(fd.name, fd.nodes[0], fd.nodes[1], v);
        vs->setAcMag(acMag);
        if (pendingWaveform.type != Waveform::DC) vs->setWaveform(pendingWaveform);
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

    // E: VCVS (电压控电压源)  E name n+ n- nc+ nc- gain
    if (c == 'e') {
        if (fd.nodes.size() < 4) { diags.error(fd.loc, fd.name + ": VCVS needs 4 nodes (n+ n- nc+ nc-)"); return nullptr; }
        double gain = 1.0;
        lookupNumber(fd.params, "gain", env, gain) ||
        lookupFirstPositionalNumber(fd.positional, env, gain);
        return std::make_unique<VCVS>(fd.name, fd.nodes[0], fd.nodes[1], fd.nodes[2], fd.nodes[3], gain);
    }
    // G: VCCS (电压控电流源)  G name n+ n- nc+ nc- gain
    if (c == 'g') {
        if (fd.nodes.size() < 4) { diags.error(fd.loc, fd.name + ": VCCS needs 4 nodes (n+ n- nc+ nc-)"); return nullptr; }
        double gain = 1.0;
        lookupNumber(fd.params, "gain", env, gain) ||
        lookupFirstPositionalNumber(fd.positional, env, gain);
        return std::make_unique<VCCS>(fd.name, fd.nodes[0], fd.nodes[1], fd.nodes[2], fd.nodes[3], gain);
    }
    // S: 压控开关  S name n+ n- nc+ nc- model [ron= roff= vt= vh=]
    if (c == 's') {
        if (fd.nodes.size() < 4) { diags.error(fd.loc, fd.name + ": switch needs 4 nodes"); return nullptr; }
        double ron = 1.0, roff = 1e12, vt = 0.0, vh = 0.0;
        lookupNumber(fd.params, "ron", env, ron);
        lookupNumber(fd.params, "roff", env, roff);
        lookupNumber(fd.params, "vt", env, vt);
        lookupNumber(fd.params, "vh", env, vh);
        return std::make_unique<VCSwitch>(fd.name, fd.nodes[0], fd.nodes[1], fd.nodes[2], fd.nodes[3], ron, roff, vt, vh);
    }
    // F: CCCS (电流控电流源)  F name n+ n- vsrc_name gain
    // 控制电流 = 指定电压源的分支电流
    if (c == 'f') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": CCCS needs 2 nodes (n+ n-)"); return nullptr; }
        // vsrc name is in fd.model (if semiconductor) or fd.positional[0] (if not)
        std::string vsName = fd.model;
        if (vsName.empty() && !fd.positional.empty()) {
            vsName = fd.positional[0].str;
        }
        if (vsName.empty()) { diags.error(fd.loc, fd.name + ": CCCS needs vsrc name as 3rd arg"); return nullptr; }
        double gain = 1.0;
        // gain is in positional (after vsrc name) or named param
        if (!fd.positional.empty() && fd.positional[0].kind == ParamValue::Kind::Number) {
            gain = fd.positional[0].num;
        } else if (fd.positional.size() > 1 && fd.positional[1].kind == ParamValue::Kind::Number) {
            gain = fd.positional[1].num;
        } else {
            lookupNumber(fd.params, "gain", env, gain);
        }
        return std::make_unique<CCCS>(fd.name, fd.nodes[0], fd.nodes[1], vsName, gain);
    }
    // H: CCVS (电流控电压源)  H name n+ n- vsrc_name gain
    if (c == 'h') {
        if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": CCVS needs 2 nodes (n+ n-)"); return nullptr; }
        std::string vsName = fd.model;
        if (vsName.empty() && !fd.positional.empty()) {
            vsName = fd.positional[0].str;
        }
        if (vsName.empty()) { diags.error(fd.loc, fd.name + ": CCVS needs vsrc name as 3rd arg"); return nullptr; }
        double gain = 1.0;
        if (!fd.positional.empty() && fd.positional[0].kind == ParamValue::Kind::Number) {
            gain = fd.positional[0].num;
        } else if (fd.positional.size() > 1 && fd.positional[1].kind == ParamValue::Kind::Number) {
            gain = fd.positional[1].num;
        } else {
            lookupNumber(fd.params, "gain", env, gain);
        }
        return std::make_unique<CCVS>(fd.name, fd.nodes[0], fd.nodes[1], vsName, gain);
    }
    // K: 互感（耦合电感）或 S 参数器件
    // K name L1 L2 k_value -> 互感
    // K name n1 n2 file="*.sNp" -> S 参数器件
    if (c == 'k') {
        // Check if this is S-parameter (has file=) or mutual inductance
        bool isSparam = false;
        std::string touchstonePath;
        double z0 = 50.0;
        for (const auto& [pn, pv] : fd.params) {
            if (pn == "file" && pv.kind != ParamValue::Kind::Number && !pv.str.empty()) {
                isSparam = true;
                touchstonePath = pv.str;
            } else if (pn == "z0" && pv.kind == ParamValue::Kind::Number) {
                z0 = pv.num;
            }
        }
        if (isSparam) {
            // S 参数器件
            if (fd.nodes.size() < 2) { diags.error(fd.loc, fd.name + ": s-param device needs >= 2 nodes"); return nullptr; }
            try {
                return std::make_unique<SParamDevice>(fd.name, fd.nodes, touchstonePath, z0);
            } catch (const std::exception& e) {
                diags.error(fd.loc, fd.name + ": " + e.what()); return nullptr;
            }
        }
        // 互感：K name L1_name L2_name k_value
        // fd.nodes contains L1 and L2 as node references - but for mutual
        // inductance, the first two args are inductor instance names, not nodes.
        // For now, support direct node-based mutual inductance:
        // K name n1a n1b n2a n2b L1= L2= k=
        if (fd.nodes.size() >= 4) {
            double L1 = 0, L2 = 0, k = 0;
            lookupNumber(fd.params, "l1", env, L1);
            lookupNumber(fd.params, "l2", env, L2);
            lookupNumber(fd.params, "k", env, k) ||
            lookupFirstPositionalNumber(fd.positional, env, k);
            if (L1 > 0 && L2 > 0) {
                return std::make_unique<MutualInductance>(fd.name,
                    fd.nodes[0], fd.nodes[1], fd.nodes[2], fd.nodes[3], L1, L2, k);
            }
        }
        diags.error(fd.loc, fd.name + ": K needs either file= (S-param) or L1=/L2=/k= (mutual inductance)");
        return nullptr;
    }

    // 半导体器件 (M/Q/D/Z/J/S/B) → vaParser 生成模型
    if (c == 'm' || c == 'q' || c == 'd' || c == 'z' || c == 'j' || c == 'b') {
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

        // C1-level54：HSPICE level=54/14/4/7（BSIM4）→ 路由到 bsim4.dll (OSDI)。
        // PDK 的 .model nch nmos (level=54 vth0=... u0=...) 是 HSPICE 原生 BSIM4 格式。
        // 仿真器只有 OSDI (Verilog-A bsim4.dll)，但 VA bsim4 接受与 HSPICE 同名的参数
        // （1:1 name-identical：vth0/u0/vsat/toxe/... + 几何/分箱 lmin/ll/xl/dlc/binunit）。
        // 故 level=54 的 MOSFET：强制把 descriptor 搜索导向 "bsim4"，
        // 参数照原样传递（表达式参数由 C2 多遍求值解析）。
        std::string origType = (mdlDef && !mdlDef->type.empty()) ? mdlDef->type : "";

        // vaParser 生成模型路由（Verilog-A -> C++ codegen）。
        // 所有半导体器件均通过生成模型实现，无 OSDI DLL 依赖。
        {
            // 解析 .model 参数（排除路由控制关键字）
            ParamList genModelParams;
            if (mdlDef) {
                for (const auto& [pn, pv] : mdlDef->params) {
                    if (pn == "file" || pn == "osdi" || pn == "lib" || pn == "generated") continue;
                    double val = 0.0;
                    if (resolveParamValue(pv, env, val)) {
                        genModelParams.push_back({pn, ParamValue{ParamValue::Kind::Number, val, "", SourceLoc{}}});
                    }
                }
            }
            // 处理 SPICE "m" (multiplier) 参数：等效于 m 个并联器件
            ParamList scaledInstParams = fd.params;
            double mult = 1.0;
            if (lookupNumber(scaledInstParams, "m", env, mult) && mult != 1.0 && mult > 0.0) {
                static const std::set<std::string> scaleByM = {
                    "w", "nf", "ad", "as", "pd", "ps"
                };
                for (auto& [pn, pv] : scaledInstParams) {
                    if (scaleByM.count(pn) && pv.kind == ParamValue::Kind::Number) {
                        pv.num *= mult;
                    }
                }
            }
            // scale 缩放：HSPICE .option scale=<val>
            if (env.scale != 1.0 && c == 'm') {
                static const std::set<std::string> scaleParams = {
                    "w", "l", "ad", "as", "pd", "ps", "nrd", "nrs", "sa", "sb", "sd"
                };
                for (auto& [pn, pv] : scaledInstParams) {
                    if (scaleParams.count(pn) && pv.kind == ParamValue::Kind::Number) {
                        pv.num *= env.scale;
                        if (env.scalem != 1.0 && (pn == "ad" || pn == "as")) {
                            pv.num *= env.scalem;
                        }
                    }
                }
            }

            // 尝试按 type 查找生成模型
            auto gen = createGeneratedModel(typeOrName, fd.name, fd.nodes, scaledInstParams, genModelParams);
            if (!gen && typeOrName != modelName)
                gen = createGeneratedModel(modelName, fd.name, fd.nodes, scaledInstParams, genModelParams);

            // PDK 风格 level=54/14/4/7 → 路由到 bsim4va
            if (!gen && (origType == "nmos" || origType == "pmos")) {
                double lvl = 0.0;
                if (mdlDef && lookupNumber(mdlDef->params, "level", env, lvl)) {
                    int li = static_cast<int>(lvl);
                    if (li == 54 || li == 14 || li == 4 || li == 7) {
                        bool hasTypeParam = false;
                        for (const auto& [pn, pv] : genModelParams) {
                            if (pn == "type") { hasTypeParam = true; break; }
                        }
                        if (!hasTypeParam) {
                            genModelParams.push_back({"type",
                                ParamValue{ParamValue::Kind::Number,
                                           (origType == "pmos") ? -1.0 : 1.0,
                                           "", SourceLoc{}}});
                        }
                        gen = createGeneratedModel("bsim4va", fd.name, fd.nodes, scaledInstParams, genModelParams);
                    }
                }
            }

            if (gen) {
                gen->setTemperature(env.temperature);
                gen->allocateInternalNodes(internalNodeBase);
                return gen;
            }

            // 生成模型未找到：报错
            diags.error(fd.loc, fd.name + ": no generated model found for type '" + typeOrName +
                        "' (model='" + modelName + "'). Available: bsim4va, bsimcmg, bsimsoi, "
                        "diode_va, diode_vt, ekv_va, bjt505va, bsim3_va, cap_linear, "
                        "nmos_sh, simple_diode");
            return nullptr;
        }
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
        auto dev = buildDevice(fd, mdl, envFull, internalNodeBase, r.diags);
        if (dev) {
            r.devices.push_back(std::move(dev));
        }
    }

    // totalNodes = 电路节点 + 分配的内部节点（internalNodeBase 已递增）
    r.totalNodes = internalNodeBase - 1;  // 最大节点编号

    r.ok = !r.diags.has_errors();
    return r;
}

} // namespace rfsim
