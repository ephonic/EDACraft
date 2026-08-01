// rfsim_codegen.cpp - 生成继承 DeviceModel 的 C++ 代码
//
// 从 module AST 生成：
//   <name>_gen.h  - 类声明（继承 DeviceModel，声明参数成员、eval/stamp 方法）
//   <name>_gen.cpp - 类实现（eval 逻辑从 module._main._steps 生成，
//                    Jacobian 从 derivation.cpp 的 calculate_deriv 生成）
//
// 变量映射（Xyce -> rfsim）：
//   nextSolVectorRawPtr[NetName]  -> op.v[nodes_[netIdx]]
//   fRHS[i] / qRHS[i]            -> out.f[i] (残差)
//   fMat_r<i>c<j> / qMat_r<i>c<j> -> out.jac[jacIdx]
//   model_.param                  -> param_ (成员变量)
//   DdtExp<i> / DdtAns<i>        -> state_[i]
//   instance params (W, L, ...)   -> w_, l_, ... (成员变量)
#include "rfsim_codegen.h"
// derivation.h 和 vaParser.h 都定义了 struct statement，不重复 include。
// calculate_deriv 的声明在 derivation.h 中，但 statement 已由 vaParser.h 提供。
// 用 extern 声明避免重复定义。
extern std::string calculate_deriv(const statement& input_state, std::set<std::string>& temp_map);

// 前向声明（定义在文件后部）
static void EmitDerivLines(const std::string& derivResult,
                           const std::map<std::string, int>& params,
                           std::ofstream& ofs);
void RfsimEmitEvalBody(module* mod, std::ofstream& ofs, bool transient);
void RfsimEmitValueStatements(module* mod, std::ofstream& ofs);
#include <stdio.h>
#include <string>
#include <list>
#include <set>
#include <vector>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <sstream>
using namespace std;

extern module* gModule;

// 辅助：int 转 string
static string i2s(int v) { ostringstream ss; ss << v; return ss.str(); }

// 辅助：首字母大写
static string capitalize(const string& s) {
    if (s.empty()) return s;
    string r = s;
    r[0] = toupper(r[0]);
    return r;
}

// 辅助：替换字符串中的子串
static string replaceAll(string str, const string& from, const string& to) {
    if (from.empty()) return str;
    size_t pos = 0;
    while ((pos = str.find(from, pos)) != string::npos) {
        str.replace(pos, from.length(), to);
        pos += to.length();
    }
    return str;
}

// 辅助：VA 的 max/min 在 C++ 无全局函数（std::max 需 <algorithm> 且与
// Windows 宏冲突），替换为生成文件顶部的 rfsim_va_max/min 辅助函数。
static string RfsimReplaceMathFuncs(string s) {
    const char* fns[2] = {"max", "min"};
    for (int i = 0; i < 2; ++i) {
        string fn = fns[i];
        string rep = "rfsim_va_" + fn;
        size_t pos = 0;
        while ((pos = s.find(fn + "(", pos)) != string::npos) {
            bool leftOK = (pos == 0) || (!isalnum(s[pos-1]) && s[pos-1] != '_');
            if (leftOK) {
                s.replace(pos, fn.size(), rep);
                pos += rep.size();
            } else {
                pos += fn.size();
            }
        }
    }
    return s;
}

// 辅助：VA 系统函数替换为 C++ 等价表达式
// analysis("dc") -> 1.0, analysis("ac") -> 0.0, etc.
// param_given(x) -> given_x_
// port_connected(x) -> 1.0
// exp_lim(x) -> exp(x), lln(x) -> log(x), limexp(x) -> exp(x)
// ac_stim(...) -> 0.0, transition(x,...) -> x, slew(x,...) -> x
// last_crossing/timer/above/cross -> 0.0
static string RfsimReplaceVAFunctions(string s) {
    // analysis("xxx") -> 1.0 for dc, 0.0 otherwise
    size_t pos = 0;
    while ((pos = s.find("analysis(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        string arg = s.substr(pos + 9, rp - pos - 9);
        // Remove quotes
        for (size_t i = 0; i < arg.size(); ++i)
            if (arg[i] == '"') arg.erase(i--, 1);
        string rep = (arg == "dc" || arg == "op") ? "1.0" : "0.0";
        s.replace(pos, rp - pos + 1, rep);
        pos += rep.size();
    }
    // param_given(x) -> given_x_
    pos = 0;
    while ((pos = s.find("param_given(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        string arg = s.substr(pos + 12, rp - pos - 12);
        string rep = "given_" + arg + "_";
        s.replace(pos, rp - pos + 1, rep);
        pos += rep.size();
    }
    // port_connected(x) -> 1.0
    pos = 0;
    while ((pos = s.find("port_connected(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        s.replace(pos, rp - pos + 1, "1.0");
        pos += 3;
    }
    // exp_lim(x) -> exp(x)
    pos = 0;
    while ((pos = s.find("exp_lim(", pos)) != string::npos) {
        s.replace(pos, 7, "exp");
        pos += 3;
    }
    // lln(x) -> log(x)
    pos = 0;
    while ((pos = s.find("lln(", pos)) != string::npos) {
        s.replace(pos, 3, "log");
        pos += 3;
    }
    // limexp(x) -> exp(x) (simplified; should clamp for large args)
    pos = 0;
    while ((pos = s.find("limexp(", pos)) != string::npos) {
        s.replace(pos, 6, "exp");
        pos += 3;
    }
    // ac_stim(...) -> 0.0
    pos = 0;
    while ((pos = s.find("ac_stim(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        s.replace(pos, rp - pos + 1, "0.0");
        pos += 3;
    }
    // transition(x, ...) -> x (extract first arg)
    pos = 0;
    while ((pos = s.find("transition(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        // Find first comma or end
        size_t comma = s.find(',', pos + 11);
        if (comma != string::npos && comma < rp) {
            string firstArg = s.substr(pos + 11, comma - pos - 11);
            s.replace(pos, rp - pos + 1, "(" + firstArg + ")");
        } else {
            string arg = s.substr(pos + 11, rp - pos - 11);
            s.replace(pos, rp - pos + 1, "(" + arg + ")");
        }
        pos += 3;
    }
    // slew(x, ...) -> x (same as transition)
    pos = 0;
    while ((pos = s.find("slew(", pos)) != string::npos) {
        size_t rp = s.find(')', pos);
        if (rp == string::npos) break;
        size_t comma = s.find(',', pos + 5);
        if (comma != string::npos && comma < rp) {
            string firstArg = s.substr(pos + 5, comma - pos - 5);
            s.replace(pos, rp - pos + 1, "(" + firstArg + ")");
        } else {
            string arg = s.substr(pos + 5, rp - pos - 5);
            s.replace(pos, rp - pos + 1, "(" + arg + ")");
        }
        pos += 3;
    }
    // last_crossing/timer/above/cross -> 0.0
    const char* zeroFns[] = {"last_crossing", "timer", "above", "cross"};
    for (int i = 0; i < 4; ++i) {
        string fn = zeroFns[i];
        pos = 0;
        while ((pos = s.find(fn + "(", pos)) != string::npos) {
            size_t rp = s.find(')', pos);
            if (rp == string::npos) break;
            s.replace(pos, rp - pos + 1, "0.0");
            pos += 3;
        }
    }
    return s;
}

// 辅助：switch(doubleExpr){ → switch((int)(doubleExpr)){
static string RfsimWrapSwitchCond(const string& desc) {
    size_t lp = desc.find('(');
    size_t rp = desc.rfind(')');
    if (lp == string::npos || rp == string::npos || rp <= lp) return desc;
    return desc.substr(0, lp + 1) + "(int)(" + desc.substr(lp + 1, rp - lp - 1) + ")" + desc.substr(rp);
}

// 辅助：rfsim 版的 ReplaceModelParam
// 把模型参数引用替换为成员变量（model_.vth0 -> vth0_）
static string RfsimReplaceModelParam(const statement& st) {
    string result = st._describ;
    for (map<string, int>::const_iterator it = st._param.begin(); it != st._param.end(); ++it) {
        if (it->second == 0) {
            // model param: name -> name_
            string from = it->first;
            string to = from + "_";
            // 精确匹配标识符边界
            size_t pos = 0;
            while ((pos = result.find(from, pos)) != string::npos) {
                // 检查前一个字符不是标识符字符
                bool leftOK = (pos == 0) || (!isalnum(result[pos-1]) && result[pos-1] != '_');
                // 检查后一个字符不是标识符字符
                size_t end = pos + from.size();
                bool rightOK = (end >= result.size()) || (!isalnum(result[end]) && result[end] != '_');
                if (leftOK && rightOK) {
                    result.replace(pos, from.size(), to);
                    pos += to.size();
                } else {
                    pos += from.size();
                }
            }
        }
    }
    result = RfsimReplaceMathFuncs(result);
    result = RfsimReplaceVAFunctions(result);
    // switch 条件为 double（VA 枚举参数）→ 转 int
    {
        size_t p = result.find_first_not_of(" \t");
        if (p != string::npos && result.compare(p, 6, "switch") == 0)
            result = RfsimWrapSwitchCond(result);
    }
    return result;
}

// 辅助：把 V(node) / I(branch) 电压/电流访问替换为 op.v[nodes_[idx]]
// module._dervar 存了 "dV(node1)Dv(node2)" -> net index 的映射
// 但 statement._describ 里的原始表达式用的是 net 名（如 V(d,g) -> 电压差）
// 简化：把 nextSolVectorRawPtr[NetName] 替换为 op.v[nodes_[netIdx]]
static string RfsimReplaceNodeAccess(const string& expr, module* mod) {
    string result = expr;
    // 替换 nextSolVectorRawPtr[NetName] -> op_v[netIdx]
    // 这在 _dervar 的 describ 中出现
    for (size_t i = 0; i < mod->_net.size(); ++i) {
        string from = "nextSolVectorRawPtr[" + mod->_net[i]._name + "]";
        string to = "op_v[" + i2s(i) + "]";
        result = replaceAll(result, from, to);
    }
    return result;
}

// ===== 生成头文件 =====
void RfsimGenerateHeader(module* mod, const string& filename) {
    string hfn = filename + "_gen.h";
    ofstream ofs(hfn);
    if (!ofs) { cerr << "Cannot open " << hfn << endl; return; }

    string className = capitalize(mod->_name) + "GenModel";
    string guard = "RFSIM_GEN_" + mod->_name + "_H_";
    for (auto& c : guard) c = toupper(c);

    ofs << "// Auto-generated by rfsim_codegen. DO NOT EDIT.\n";
    ofs << "// Source: " << mod->_name << " Verilog-A module\n";
    ofs << "#ifndef " << guard << "\n";
    ofs << "#define " << guard << "\n\n";
    ofs << "#include \"model/device_model.hpp\"\n";
    ofs << "#include \"parser/ast.hpp\"\n";
    ofs << "#include <string>\n";
    ofs << "#include <vector>\n\n";
    ofs << "namespace rfsim {\n\n";
    ofs << "class " << className << " : public DeviceModel {\n";
    ofs << "public:\n";
    ofs << "    " << className << "(const std::string& name,\n";
    ofs << "                       const std::vector<NodeId>& nodes,\n";
    ofs << "                       const ParamList& instanceParams,\n";
    ofs << "                       const ParamList& modelParams);\n\n";

    // DeviceModel 接口
    ofs << "    const std::vector<NodeId>& nodes() const override { return nodes_; }\n";
    ofs << "    void stamp_pattern(StampPattern& out) const override;\n";
    ofs << "    void eval(const OperatingPoint& op, DeviceContribution& out) const override;\n";
    ofs << "    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;\n";
    ofs << "    bool is_linear() const override { return false; }\n";
    ofs << "    std::string name() const override { return name_; }\n";
    // 内部节点分配（factory 在构造后调用，internalNodeBase 递增）
    ofs << "    void allocateInternalNodes(NodeId& internalNodeBase) override;\n";

    // 瞬态状态
    int ddtNum = mod->_ddtnum;
    if (ddtNum > 0) {
        ofs << "    bool hasTransientState() const override { return true; }\n";
        ofs << "    size_t transientStateSize() const override { return " << 2*ddtNum << "; }  // [Q_prev,I_prev] per ddt\n";
        ofs << "    void initializeTransientState(const std::vector<double>& nodeV) override;\n";
        ofs << "    void updateTransientState(const TransientOpPoint& op) override;\n";
        ofs << "    std::vector<double> getTransientState() const override { return state_; }\n";
        ofs << "    void setTransientState(const std::vector<double>& s) override { state_ = s; }\n";
    } else {
        ofs << "    bool hasTransientState() const override { return false; }\n";
    }
    ofs << "\n";

    // 参数设置接口（供 device_factory 调用）
    ofs << "    void setModelParam(const std::string& name, double value);\n";
    ofs << "    void setInstanceParam(const std::string& name, double value);\n";
    // 温度接口：$temperature/$vt 经此注入（SPICE .options temp / .temp）
    ofs << "    void setTemperature(double tempK) override { temp_ = tempK; }\n\n";

    ofs << "private:\n";
    ofs << "    std::string name_;\n";
    ofs << "    std::vector<NodeId> nodes_;\n";
    ofs << "    uint32_t numTerminals_;\n";

    // 参数成员
    ofs << "    // Model parameters\n";
    ofs << "    double temp_ = 300.15;  // 器件温度 (K)，setTemperature 注入\n";
    // $simparam 成员（模拟器选项，默认值来自 VA 调用点）
    for (map<string, string>::iterator sit = mod->_simparamDflt.begin();
         sit != mod->_simparamDflt.end(); ++sit) {
        ofs << "    double simparam_" << sit->first << "_ = " << sit->second << ";\n";
    }
    char numbuf[40];
    for (list<parameter>::iterator pit = mod->_param.begin(); pit != mod->_param.end(); ++pit) {
        if (pit->_type == 0) {  // model param
            // %.17g：保留完整 double 精度（NOT_GIVEN=-12345789 等大字面值
            // 若用默认 6 位精度会舍入，导致 Given 检查失效）
            if (!pit->_defexpr.empty()) {
                // 默认值是表达式（如 VSAT1 = VSAT）：参数名替换为成员名
                string expr = pit->_defexpr;
                for (list<parameter>::iterator qit = mod->_param.begin(); qit != mod->_param.end(); ++qit) {
                    expr = ReplaceIdent(expr, qit->_name, qit->_name + "_");
                }
                ofs << "    double " << pit->_name << "_ = " << expr << ";\n";
            } else {
                snprintf(numbuf, sizeof(numbuf), "%.17g", pit->_defvalue);
                ofs << "    double " << pit->_name << "_ = " << numbuf << ";\n";
            }
        }
    }
    ofs << "    // Instance parameters\n";
    for (list<parameter>::iterator pit = mod->_param.begin(); pit != mod->_param.end(); ++pit) {
        if (pit->_type == 1) {  // instance param
            snprintf(numbuf, sizeof(numbuf), "%.17g", pit->_defvalue);
            ofs << "    double " << pit->_name << "_ = " << numbuf << ";\n";
        }
    }
    // $param_given 支持：参数被 .model/实例显式设置后置 1
    if (!mod->_param.empty()) {
        ofs << "    // $param_given flags\n";
        for (list<parameter>::iterator pit = mod->_param.begin(); pit != mod->_param.end(); ++pit) {
            ofs << "    double given_" << pit->_name << "_ = 0.0;\n";
        }
    }

    // 状态
    if (ddtNum > 0) {
        ofs << "    // Transient state (ddt)\n";
        ofs << "    std::vector<double> state_;\n";
    }

    // Jacobian 非零模式缓存
    ofs << "    // Jacobian pattern\n";
    ofs << "    std::vector<std::pair<uint32_t,uint32_t>> jacPattern_;\n";

    ofs << "};\n\n";
    ofs << "} // namespace rfsim\n\n";
    ofs << "#endif // " << guard << "\n";
}

// ===== 生成注册片段（generated_registry 自动化）=====
// 输出 <filename>_reg.inc，两行：
//   第 1 行: #include "<base>_gen.h"   → 放入 registry 的 AUTO-INCLUDES 段
//   第 2 行: {"<module>", &makeGen<<Class>GenModel>}, → AUTO-REGISTRY 段
// 由 CktCraft/tools/regen_registry.sh 汇总重写 generated_registry.cpp。
void RfsimGenerateRegSnippet(module* mod, const string& filename) {
    string rfn = filename + "_reg.inc";
    ofstream ofs(rfn);
    if (!ofs) { cerr << "Cannot open " << rfn << endl; return; }

    string base = filename;
    size_t slash = base.find_last_of("/\\");
    if (slash != string::npos) base = base.substr(slash + 1);

    string className = capitalize(mod->_name) + "GenModel";
    ofs << "#include \"" << base << "_gen.h\"\n";
    ofs << "    {\"" << mod->_name << "\", &makeGen<" << className << ">},\n";
}

// ===== 生成源文件 =====
void RfsimGenerateSource(module* mod, const string& filename) {
    string sfn = filename + "_gen.cpp";
    ofstream ofs(sfn);
    if (!ofs) { cerr << "Cannot open " << sfn << endl; return; }

    string className = capitalize(mod->_name) + "GenModel";
    // include 用 basename：输出路径可能带目录（如 src/model/generated/simple_diode），
    // 生成的 .h/.cpp 在同一目录，避免把相对目录写进 #include。
    string base = filename;
    size_t slash = base.find_last_of("/\\");
    if (slash != string::npos) base = base.substr(slash + 1);
    string hfn = base + "_gen.h";

    ofs << "// Auto-generated by rfsim_codegen. DO NOT EDIT.\n";
    ofs << "#include \"" << hfn << "\"\n";
    ofs << "#include <cmath>\n";
    ofs << "#include <cstring>\n";
    ofs << "#include <cstdlib>\n\n";
    ofs << "// VA max/min 的 C++ 实现（避免 std::max/min 与 Windows 宏冲突）\n";
    ofs << "static inline double rfsim_va_max(double a, double b) { return a > b ? a : b; }\n";
    ofs << "static inline double rfsim_va_min(double a, double b) { return a < b ? a : b; }\n\n";
    ofs << "namespace rfsim {\n\n";

    int numNets = mod->_net.size();
    int numPorts = mod->_port.size();
    int ddtNum = mod->_ddtnum;

    // ===== 构造函数 =====
    ofs << className << "::" << className << "(const std::string& name,\n";
    ofs << "                       const std::vector<NodeId>& nodes,\n";
    ofs << "                       const ParamList& instanceParams,\n";
    ofs << "                       const ParamList& modelParams)\n";
    ofs << "    : name_(name), numTerminals_(" << numPorts << ") {\n";
    // nodes_ 按 _net 索引布局：外部端口映射 + 内部节点待分配
    ofs << "    nodes_.assign(" << numNets << ", 0);\n";
    for (size_t i = 0; i < mod->_port.size(); ++i) {
        int netIdx = -1;
        for (size_t j = 0; j < mod->_net.size(); ++j) {
            if (mod->_net[j]._name == mod->_port[i]._name) { netIdx = (int)j; break; }
        }
        if (netIdx >= 0)
            // 网表未连接的端口（如 D 器件第 3 端被 maxNodes 截断）接地兜底
            ofs << "    nodes_[" << netIdx << "] = (nodes.size() > " << i << ") ? nodes[" << i << "] : 0;  // port " << mod->_port[i]._name << "\n";
    }

    // 从 ParamList 读取参数
    ofs << "    // Read model parameters\n";
    ofs << "    for (const auto& [pn, pv] : modelParams) {\n";
    ofs << "        if (pv.kind == ParamValue::Kind::Number) setModelParam(pn, pv.num);\n";
    ofs << "    }\n";
    ofs << "    // Read instance parameters\n";
    ofs << "    for (const auto& [pn, pv] : instanceParams) {\n";
    ofs << "        if (pv.kind == ParamValue::Kind::Number) setInstanceParam(pn, pv.num);\n";
    ofs << "    }\n";

    if (ddtNum > 0) {
        ofs << "    state_.assign(" << 2*ddtNum << ", 0.0);\n";
    }

    // 构建 Jacobian 非零模式
    ofs << "    // Build Jacobian sparsity pattern\n";
    for (map<int, map<int,int> >::iterator mit = mod->_matstructrue.begin();
         mit != mod->_matstructrue.end(); ++mit) {
        int row = mit->first;
        for (map<int,int>::iterator it2 = mit->second.begin(); it2 != mit->second.end(); ++it2) {
            int col = it2->first;
            if (it2->second) {
                ofs << "    jacPattern_.emplace_back(" << row << ", " << col << ");\n";
            }
        }
    }
    ofs << "}\n\n";

    // ===== allocateInternalNodes：为非端口网络分配全局 NodeId =====
    ofs << "void " << className << "::allocateInternalNodes(NodeId& internalNodeBase) {\n";
    for (size_t j = 0; j < mod->_net.size(); ++j) {
        bool isPort = false;
        for (size_t pi = 0; pi < mod->_port.size(); ++pi) {
            if (mod->_port[pi]._name == mod->_net[j]._name) { isPort = true; break; }
        }
        if (!isPort)
            ofs << "    nodes_[" << j << "] = internalNodeBase++;  // internal net " << mod->_net[j]._name << "\n";
    }
    ofs << "}\n\n";

    // ===== setModelParam / setInstanceParam =====
    // 参数名比较用小写（netlist parser 全部 tolower，OSDI findParamId 同样小写匹配）
    ofs << "void " << className << "::setModelParam(const std::string& name, double value) {\n";
    for (list<parameter>::iterator pit = mod->_param.begin(); pit != mod->_param.end(); ++pit) {
        if (pit->_type == 0) {
            string lowname = pit->_name;
            for (auto& c : lowname) c = tolower(c);
            ofs << "    if (name == \"" << lowname << "\") { " << pit->_name << "_ = value; given_" << pit->_name << "_ = 1.0; return; }\n";
        }
    }
    ofs << "}\n\n";

    ofs << "void " << className << "::setInstanceParam(const std::string& name, double value) {\n";
    for (list<parameter>::iterator pit = mod->_param.begin(); pit != mod->_param.end(); ++pit) {
        if (pit->_type == 1) {
            string lowname = pit->_name;
            for (auto& c : lowname) c = tolower(c);
            ofs << "    if (name == \"" << lowname << "\") { " << pit->_name << "_ = value; given_" << pit->_name << "_ = 1.0; return; }\n";
        }
    }
    // VA 语义：实例可覆盖任意模型参数（如 BSIM4 的 w/l 是 model parameter）
    ofs << "    setModelParam(name, value);\n";
    ofs << "}\n\n";

    // ===== stamp_pattern =====
    ofs << "void " << className << "::stamp_pattern(StampPattern& out) const {\n";
    ofs << "    for (const auto& [r, c] : jacPattern_) {\n";
    ofs << "        if (r < nodes_.size() && c < nodes_.size())\n";
    ofs << "            out.entries.emplace_back(nodes_[r], nodes_[c]);\n";
    ofs << "    }\n";
    ofs << "}\n\n";

    // ===== eval (DC) =====
    ofs << "void " << className << "::eval(const OperatingPoint& op, DeviceContribution& out) const {\n";
    ofs << "    // Node voltages (indexed by local node index)\n";
    ofs << "    const auto& op_v = op.v;\n";
    ofs << "    // Initialize residual\n";
    ofs << "    out.f.assign(" << numNets << ", 0.0);\n";
    ofs << "    out.jac.assign(jacPattern_.size(), 0.0);\n\n";

    // 单趟发射（值行与导数行交错）：scratch 变量 T0-T10 被反复复用，
    // 残差/雅可比分段发射会使导数引用到被覆盖的 scratch 值（BSIM4 NaN）。
    RfsimEmitEvalBody(mod, ofs, false);

    ofs << "}\n\n";

    // ===== evalTransient =====
    ofs << "void " << className << "::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {\n";
    if (ddtNum > 0) {
        ofs << "    // Node voltages (indexed by local node index)\n";
        ofs << "    const auto& op_v = op.v;\n";
        ofs << "    out.f.assign(" << numNets << ", 0.0);\n";
        ofs << "    out.jac.assign(jacPattern_.size(), 0.0);\n\n";
        RfsimEmitEvalBody(mod, ofs, true);
    } else {
        ofs << "    // No transient state, degrade to DC\n";
        ofs << "    OperatingPoint dcOp{op.v};\n";
        ofs << "    eval(dcOp, out);\n";
    }
    ofs << "}\n\n";

    // ===== 瞬态状态管理 =====
    if (ddtNum > 0) {
        // initializeTransientState: 在 DC 工作点求 DdtExp 存入 Q_prev
        ofs << "void " << className << "::initializeTransientState(const std::vector<double>& nodeV) {\n";
        ofs << "    state_.assign(" << 2*ddtNum << ", 0.0);\n";
        ofs << "    const auto& op_v = nodeV;\n";
        RfsimEmitValueStatements(mod, ofs);
        for (int i = 0; i < ddtNum; ++i) {
            ofs << "    state_[" << 2*i << "] = DdtExp" << i << ";\n";
        }
        ofs << "}\n\n";

        // updateTransientState: 步收敛后推进状态 (I_prev 用伴随公式, Q_prev 取当前 DdtExp)
        ofs << "void " << className << "::updateTransientState(const TransientOpPoint& op) {\n";
        ofs << "    const auto& op_v = op.v;\n";
        ofs << "    double myadms_t1 = 0., myadms_t2 = 0.;\n";  // 初始化 0 避免 C4701 / NaN
        RfsimEmitValueStatements(mod, ofs);
        for (int i = 0; i < ddtNum; ++i) {
            ofs << "    {\n";
            ofs << "        double ddtAnsNew = (op.method == IntegrationMethod::Trapezoidal)\n";
            ofs << "            ? (2.0*(DdtExp" << i << " - state_[" << 2*i << "])/op.dt - state_[" << 2*i+1 << "])\n";
            ofs << "            : ((DdtExp" << i << " - state_[" << 2*i << "])/op.dt);\n";
            ofs << "        state_[" << 2*i+1 << "] = ddtAnsNew;\n";
            ofs << "        state_[" << 2*i << "] = DdtExp" << i << ";\n";
            ofs << "    }\n";
        }
        ofs << "}\n\n";
    }

    ofs << "} // namespace rfsim\n";
}

// ===== 条件块内 V<+ 支路的回退方程 =====
// V(a,b) <+ ... 被解糖为伪网络 brIdx 的电压方程（见 vaYacc.y R_contribution）。
// 若某 if/else 或 switch 分支只有部分支路含 V<+，未覆盖的支路上 brIdx 行
// 无方程 → MNA 奇异。此处静态分析块结构，为每个缺失的支路段生成回退：
//   f[brIdx] += Ibr （即 Ibr = 0，支路电流未知量归零）
//   jac[brIdx][brIdx] += 1
// 返回: 语句索引（在该语句之前发射） -> 伪网络列表
static map<int, vector<int> > ComputeBranchFlowFallbacks(module* mod) {
    map<int, vector<int> > fallbacks;
    if (mod->_branchFlowNets.empty()) return fallbacks;

    struct Group {
        vector<set<int> > segCovered;  // 每段覆盖的伪网络
        vector<int> segEnd;            // 每段结束位置（边界语句索引）
        set<int> cur() { return segCovered.back(); }
    };
    vector<Group> stack;

    auto trimStr = [](const string& s) {
        size_t p = s.find_first_not_of(" \t");
        return p == string::npos ? string("") : s.substr(p);
    };

    list<source*>::iterator srcIt = mod->_contribute.begin();
    int idx = 0;
    for (list<statement>::iterator it = mod->_main._steps.begin();
         it != mod->_main._steps.end(); ++it, ++idx) {
        if (it->_mode == 2) {
            source* src = *srcIt++; 
            if (mod->_branchFlowNets.count(src->_pos) && !stack.empty())
                stack.back().segCovered.back().insert(src->_pos);
            continue;
        }
        if (it->_mode != 0 || it->_type) continue;  // 只看结构语句
        string d = trimStr(it->_describ);
        if (d.rfind("if(", 0) == 0 || d.rfind("if (", 0) == 0 ||
            d.rfind("switch(", 0) == 0 || d.rfind("switch (", 0) == 0) {
            stack.push_back(Group());
            stack.back().segCovered.push_back(set<int>());
        } else if (d == "} else {" || d.rfind("case ", 0) == 0 || d == "break;") {
            if (!stack.empty()) {
                stack.back().segEnd.push_back(idx);
                stack.back().segCovered.push_back(set<int>());
            }
        } else if (d == "}") {
            if (!stack.empty()) {
                Group& g = stack.back();
                g.segEnd.push_back(idx);
                set<int> uni;
                for (auto& s : g.segCovered) {
                    for (int b : s) uni.insert(b);
                }
                for (size_t k = 0; k < g.segEnd.size(); ++k) {
                    for (int b : uni) {
                        if (!g.segCovered[k].count(b))
                            fallbacks[g.segEnd[k]].push_back(b);
                    }
                }
                stack.pop_back();
                // 整组覆盖情况传播到外层段
                if (!stack.empty()) {
                    for (int b : uni) stack.back().segCovered.back().insert(b);
                }
            }
        }
    }
    return fallbacks;
}

// ===== 单趟发射 eval 主体（值行与导数行交错）=====
// transient=false: DC 语义（_der0=0, DdtAns=0）
// transient=true: 瞬态伴随模型（_der0=coef, DdtAns=梯形/BE 伴随电流）
void RfsimEmitEvalBody(module* mod, ofstream& ofs, bool transient) {
    int numNets = mod->_net.size();
    // ---- 声明区 ----
    if (mod->_ddtnum != 0) {
        string ddtexp, ddtans;
        for (int i = 0; i < mod->_ddtnum; ++i) {
            ddtexp += ", DdtExp" + i2s(i);
            ddtans += ", DdtAns" + i2s(i);
        }
        ofs << "    double" << ddtexp.substr(1) << ";\n";
        ofs << "    double" << ddtans.substr(1) << ";\n";
        if (!transient) {
            for (int i = 0; i < mod->_ddtnum; ++i)
                ofs << "    DdtExp" << i << " = state_[" << 2*i << "];\n";
        }
    }
    ofs << "    double myadms_t1, myadms_t2;\n";
    for (list<variable>::iterator vit = mod->_variable.begin(); vit != mod->_variable.end(); ++vit)
        ofs << "    double " << vit->_name << " = 0.;\n";  // 初始化 0 避免 C4701 / NaN
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        string varName = dit->first.substr(1, dit->first.find("Dv") - 1);
        int netIdx = dit->second;
        ofs << "    double " << varName << " = op_v[nodes_[" << netIdx << "]];\n";
    }
    // 导数种子与临时变量
    if (transient)
        ofs << "    const double _der0 = ((op.method == IntegrationMethod::Trapezoidal) ? 2.0 : 1.0) / op.dt;  // ddt 积分系数\n";
    else
        ofs << "    const double _der0 = 0.0;  // DC: ddt conductance factor\n";
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit)
        ofs << "    double " << dit->first << " = 1.;\n";
    for (map<string, int>::iterator tit = mod->_tmpdervar.begin(); tit != mod->_tmpdervar.end(); ++tit)
        ofs << "    double " << tit->first << " = 0.;\n";  // 初始化 0 避免 C4701 / NaN
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        string varName = dit->first.substr(1, dit->first.find("Dv") - 1);
        for (int b = 0; b < numNets; ++b) {
            string declName = "d" + varName + "Dv" + i2s(b);
            if (declName == dit->first) continue;
            ofs << "    double " << declName << " = 0.;\n";
        }
    }
    ofs << "    double contributetmp = 0.;\n";
    for (int b = 0; b < numNets; ++b)
        ofs << "    double dcontributetmpDv" << b << " = 0.;\n";

    // ---- f 初始化 ----
    for (int i = 0; i < numNets; ++i)
        ofs << "    out.f[" << i << "] = 0.;\n";

    // ---- 单趟遍历：值行与导数行交错 ----
    list<statement>::iterator iter = mod->_main._steps.begin();
    list<source*>::iterator sourceiter = mod->_contribute.begin();
    map<int, vector<int> > fallbacks = ComputeBranchFlowFallbacks(mod);
    int stmtIdx = 0;

    while (iter != mod->_main._steps.end()) {
        // V<+ 条件支路回退方程（f + jac）
        if (!fallbacks.empty()) {
            map<int, vector<int> >::iterator fb = fallbacks.find(stmtIdx);
            if (fb != fallbacks.end()) {
                for (int brIdx : fb->second) {
                    string brVar = "V" + mod->_net[brIdx]._name;
                    ofs << "    out.f[" << brIdx << "] += " << brVar << ";  // fallback: Ibr=0 (inactive V<+ branch)\n";
                    ofs << "    for (size_t ji = 0; ji < jacPattern_.size(); ++ji) {\n";
                    ofs << "        if (jacPattern_[ji].first == " << brIdx << " && jacPattern_[ji].second == " << brIdx << ")\n";
                    ofs << "            out.jac[ji] += 1.0;\n";
                    ofs << "    }\n";
                }
            }
        }
        ++stmtIdx;

        if (iter->_mode == 5) {
            ++iter; continue;
        } else if (iter->_mode == 4) {
            // 导数专用语句（if/else 支路导数清零、ddt 导数链）
            ofs << "    " << iter->_describ << "\n";
            ++iter; continue;
        } else if (iter->_mode == 2) {
            // Contribution: 先 f stamp，再导数，再 jac stamp
            string destmp = RfsimReplaceModelParam(*iter);
            source* mysource = *sourceiter;
            ++sourceiter;

            if (mysource->_type == 1 || mysource->_type == 2) {
                if (mysource->_nodenum == 1) {
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                } else if (mysource->_nodenum == 2) {
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                    ofs << "    out.f[" << mysource->_neg << "] -= myadms_t1;\n";
                }
            } else if (mysource->_type == 0 || mysource->_type == 3) {
                if (mysource->_nodenum == 2) {
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                }
            }

            // 贡献导数（一般 RHS 直接符号微分）
            set<int> depVarIndices;
            set<string> depVarNames;
            for (map<string, bitset<BIT_> >::iterator vit = iter->_var.begin();
                 vit != iter->_var.end(); ++vit) {
                depVarNames.insert(vit->first);
                for (int b = 0; b < BIT_; ++b)
                    if (vit->second[b]) depVarIndices.insert(b);
            }
            if (!depVarIndices.empty() && iter->_type) {
                statement mystat = *iter;
                mystat._describ = "contributetmp = " + iter->_describ + ";";
                string derivResult = calculate_deriv(mystat, depVarNames);
                EmitDerivLines(derivResult, iter->_param, ofs);
            }
            int posNode = mysource->_pos;
            int negNode = (mysource->_nodenum >= 2) ? mysource->_neg : -1;
            for (set<int>::iterator dit = depVarIndices.begin(); dit != depVarIndices.end(); ++dit) {
                int depIdx = *dit;
                ofs << "    for (size_t ji = 0; ji < jacPattern_.size(); ++ji) {\n";
                ofs << "        if (jacPattern_[ji].first == " << posNode << " && jacPattern_[ji].second == " << depIdx << ")\n";
                ofs << "            out.jac[ji] += dcontributetmpDv" << depIdx << ";\n";
                if (negNode >= 0) {
                    ofs << "        if (jacPattern_[ji].first == " << negNode << " && jacPattern_[ji].second == " << depIdx << ")\n";
                    ofs << "            out.jac[ji] -= dcontributetmpDv" << depIdx << ";\n";
                }
                ofs << "    }\n";
            }
        } else {
            // Normal / structural：值行 + 导数行（若有）
            string desc = RfsimReplaceModelParam(*iter);
            if (desc.rfind("DdtAns", 0) == 0) {
                size_t eq = desc.find('=');
                if (transient) {
                    // 瞬态伴随模型: DdtAns<i> = dQ/dt
                    //   BE:   (Q_n - Q_{n-1})/dt
                    //   Trap: 2*(Q_n - Q_{n-1})/dt - I_{n-1}
                    // state_[2i]=Q_{n-1}, state_[2i+1]=I_{n-1}
                    int di = atoi(desc.c_str() + 6);
                    char cbuf[512];
                    snprintf(cbuf, sizeof(cbuf),
                        "DdtAns%d = (op.method == IntegrationMethod::Trapezoidal)\n"
                        "        ? (2.0*(DdtExp%d - state_[%d])/op.dt - state_[%d])\n"
                        "        : ((DdtExp%d - state_[%d])/op.dt);",
                        di, di, 2*di, 2*di+1, di, 2*di);
                    desc = cbuf;
                } else {
                    // DC: ddt 电荷残差为 0（DdtAns<i> = DdtExp<i> 是瞬态伴随模型占位）
                    if (eq != string::npos) desc = desc.substr(0, eq + 1) + " 0.0;";
                }
            }
            ofs << "    " << desc << "\n";
            if (iter->_type) {
                set<string> depVarNames;
                for (map<string, bitset<BIT_> >::iterator vit = iter->_var.begin();
                     vit != iter->_var.end(); ++vit)
                    depVarNames.insert(vit->first);
                string derivResult = calculate_deriv(*iter, depVarNames);
                EmitDerivLines(derivResult, iter->_param, ofs);
            }
        }
        ++iter;
    }
}

// ===== 纯值语句发射（initialize/updateTransientState 用）=====
// 只发射声明与 mode-0 赋值/结构语句（不含贡献/导数），用于在指定工作点
// 重新计算 DdtExp<i>（电荷表达式）。调用前需已有 `const auto& op_v = ...`。
void RfsimEmitValueStatements(module* mod, ofstream& ofs) {
    if (mod->_ddtnum != 0) {
        string ddtexp, ddtans;
        for (int i = 0; i < mod->_ddtnum; ++i) {
            ddtexp += ", DdtExp" + i2s(i);
            ddtans += ", DdtAns" + i2s(i);
        }
        ofs << "    double" << ddtexp.substr(1) << ";\n";
        ofs << "    double" << ddtans.substr(1) << ";\n";
    }
    for (list<variable>::iterator vit = mod->_variable.begin(); vit != mod->_variable.end(); ++vit)
        ofs << "    double " << vit->_name << " = 0.;\n";  // 初始化 0 避免 C4701 / NaN
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        string varName = dit->first.substr(1, dit->first.find("Dv") - 1);
        int netIdx = dit->second;
        ofs << "    double " << varName << " = op_v[nodes_[" << netIdx << "]];\n";
    }
    for (list<statement>::iterator iter = mod->_main._steps.begin();
         iter != mod->_main._steps.end(); ++iter) {
        if (iter->_mode == 0) {
            ofs << "    " << RfsimReplaceModelParam(*iter) << "\n";
        }
    }
}

// ===== rfsim 版 EquationGenerator（残差计算）=====
void RfsimEquationGenerator(module* mod, ofstream& ofs) {
    // 变量声明
    if (mod->_ddtnum != 0) {
        string ddtexp, ddtans;
        for (int i = 0; i < mod->_ddtnum; ++i) {
            ddtexp += ", DdtExp" + i2s(i);
            ddtans += ", DdtAns" + i2s(i);
        }
        ofs << "    double" << ddtexp.substr(1) << ";\n";
        ofs << "    double" << ddtans.substr(1) << ";\n";
        // ddt state 引用
        for (int i = 0; i < mod->_ddtnum; ++i) {
            ofs << "    DdtExp" << i << " = state_[" << i << "];\n";
        }
    }

    ofs << "    double myadms_t1, myadms_t2;\n";

    // 局部变量
    for (list<variable>::iterator vit = mod->_variable.begin(); vit != mod->_variable.end(); ++vit) {
        ofs << "    double " << vit->_name << " = 0.;\n";  // 初始化 0 避免 C4701 / NaN
    }

    // 节点电压访问变量（从 _dervar）
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        string varName = dit->first.substr(1, dit->first.find("Dv") - 1);
        int netIdx = dit->second;
        ofs << "    double " << varName << " = op_v[nodes_[" << netIdx << "]];\n";
    }

    // 初始化 fRHS
    for (int i = 0; i < (int)mod->_net.size(); ++i) {
        ofs << "    out.f[" << i << "] = 0.;\n";
    }

    // 遍历语句
    list<statement>::iterator iter = mod->_main._steps.begin();
    list<source*>::iterator sourceiter = mod->_contribute.begin();
    map<int, vector<int> > fallbacks = ComputeBranchFlowFallbacks(mod);
    int stmtIdx = 0;
    int dbgCounter = 0;

    while (iter != mod->_main._steps.end()) {
        // V<+ 条件支路回退方程（Ibr = 0）
        if (!fallbacks.empty()) {
            map<int, vector<int> >::iterator fb = fallbacks.find(stmtIdx);
            if (fb != fallbacks.end()) {
                for (int brIdx : fb->second) {
                    string brVar = "V" + mod->_net[brIdx]._name;
                    ofs << "    out.f[" << brIdx << "] += " << brVar << ";  // fallback: Ibr=0 (inactive V<+ branch)\n";
                }
            }
        }
        ++stmtIdx;
        if (iter->_mode == 4 || iter->_mode == 5) {
            ++iter; continue;  // 残差段跳过导数专用语句（mode 4/5）
        } else if (iter->_mode == 2) {
            // Contribution: stamp into out.f
            string destmp = RfsimReplaceModelParam(*iter);
            string org_destmp = destmp;
            source* mysource = *sourceiter;
            ++sourceiter;

            if (mysource->_type == 1 || mysource->_type == 2) {
                // Current/Power contribution
                if (mysource->_nodenum == 1) {
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                } else if (mysource->_nodenum == 2) {
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                    ofs << "    out.f[" << mysource->_neg << "] -= myadms_t1;\n";
                }
            } else if (mysource->_type == 0 || mysource->_type == 3) {
                // Voltage/Temperature contribution
                if (mysource->_nodenum == 2) {
                    // Flow node = GetFlowNode(pos, neg) -> 简化为 pos
                    ofs << "    myadms_t1 = " << destmp << ";\n";
                    ofs << "    out.f[" << mysource->_pos << "] += myadms_t1;\n";
                }
            }
        } else {
            // Normal assignment
            string desc = RfsimReplaceModelParam(*iter);
            // DC: ddt 电荷残差为 0（DdtAns<i> = DdtExp<i> 是瞬态伴随模型占位，
            // DC 工作点处 dQ/dt = 0）。瞬态 companion 见 evalTransient TODO。
            if (desc.rfind("DdtAns", 0) == 0) {
                size_t eq = desc.find('=');
                if (eq != string::npos) desc = desc.substr(0, eq + 1) + " 0.0;";
            }
            ofs << "    " << desc << "\n";
        }
        ++iter;
    }
}

// 辅助：从 calculate_deriv 的输出中过滤出导数行（含 Dv 与 =），
// 做模型参数名替换（name → name_）后写入 ofs。
static void EmitDerivLines(const string& derivResult,
                           const map<string, int>& params,
                           ofstream& ofs) {
    size_t pos = 0;
    while (pos < derivResult.size()) {
        size_t semi = derivResult.find(';', pos);
        if (semi == string::npos) break;
        string line = derivResult.substr(pos, semi - pos);
        pos = semi + 1;
        while (!line.empty() && (line[0] == '\n' || line[0] == ' ' || line[0] == '\t')) line.erase(0, 1);
        while (!line.empty() && (line.back() == '\n' || line.back() == ' ' || line.back() == '\t')) line.pop_back();
        if (line.empty()) continue;
        // 只输出导数行（d<var>Dv<idx> = ...），跳过原始表达式（残差段已输出）
        if (line.find("Dv") == string::npos || line.find("=") == string::npos) continue;
        string lineRfsim = line;
        for (map<string, int>::const_iterator pit = params.begin(); pit != params.end(); ++pit) {
            if (pit->second == 0) {
                string from = pit->first;
                string to = from + "_";
                size_t epos = 0;
                while ((epos = lineRfsim.find(from, epos)) != string::npos) {
                    bool leftOK = (epos == 0) || (!isalnum(lineRfsim[epos-1]) && lineRfsim[epos-1] != '_');
                    size_t eend = epos + from.size();
                    bool rightOK = (eend >= lineRfsim.size()) || (!isalnum(lineRfsim[eend]) && lineRfsim[eend] != '_');
                    if (leftOK && rightOK) {
                        lineRfsim.replace(epos, from.size(), to);
                        epos += to.size();
                    } else {
                        epos += from.size();
                    }
                }
            }
        }
        ofs << "    " << RfsimReplaceVAFunctions(RfsimReplaceMathFuncs(lineRfsim)) << ";\n";
    }
}

// ===== rfsim 版 JacobiGenerator（雅可比计算）=====
void RfsimJacobiGenerator(module* mod, ofstream& ofs) {
    // Jacobian 部分不重复声明变量（已在残差部分声明）
    // 只声明导数临时变量

    // DC 下 ddt 电导系数为 0（瞬态时在 evalTransient 中取积分系数）
    ofs << "    const double _der0 = 0.0;  // DC: ddt conductance factor\n";

    // 节点电压访问变量（不重复声明）
    // 导数种子: d<nodevar>Dv<self> = 1（节点电压对自身的导数）
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        ofs << "    double " << dit->first << " = 1.;\n";
    }

    // 局部变量（不重复声明）
    // 导数变量声明
    for (list<variable>::iterator vit = mod->_variable.begin(); vit != mod->_variable.end(); ++vit) {
        // skip
    }

    // 临时导数变量声明
    for (map<string, int>::iterator tit = mod->_tmpdervar.begin(); tit != mod->_tmpdervar.end(); ++tit) {
        ofs << "    double " << tit->first << " = 0.;\n";  // 初始化 0 避免 C4701 / NaN
    }

    // 导数变量声明（didDv0, didDv1, dvdDv0 等）
    // 从 _dervar 的名字生成 d<var>Dv<idx> 声明；
    // 跳过与种子同名的对角元（上面已声明并初始化为 1）
    for (map<string, int>::iterator dit = mod->_dervar.begin(); dit != mod->_dervar.end(); ++dit) {
        string varName = dit->first.substr(1, dit->first.find("Dv") - 1);
        for (int b = 0; b < (int)mod->_net.size(); ++b) {
            string declName = "d" + varName + "Dv" + i2s(b);
            if (declName == dit->first) continue;  // 对角种子已声明
            ofs << "    double " << declName << " = 0.;\n";
        }
    }

    ofs << "    double contributetmp = 0.;\n";
    // dcontributetmpDv 声明
    for (int b = 0; b < (int)mod->_net.size(); ++b) {
        ofs << "    double dcontributetmpDv" << b << " = 0.;\n";
    }

    // 初始化 jac
    for (size_t i = 0; i < mod->_net.size(); ++i) {
        // 每个贡献的导数变量
    }
    ofs << "    // (jac already zero-initialized in eval)\n";

    // 遍历语句：normal 语句先微分（生成 d<var>Dv<i> 变量），
    // contribution 语句用 dcontributetmpDv<i> = d<var>Dv<i> 链接
    list<statement>::iterator iter = mod->_main._steps.begin();
    list<source*>::iterator sourceiter = mod->_contribute.begin();
    map<int, vector<int> > fallbacks = ComputeBranchFlowFallbacks(mod);
    int stmtIdx = 0;
    int dbgCounter = 0;

    while (iter != mod->_main._steps.end()) {
        static bool dbgProg = getenv("VA_DEBUG_PROG") != NULL;
        if (dbgProg && (dbgCounter % 50 == 0 || dbgCounter > 8700)) { fprintf(stderr, "[jacobi] stmt %d: %.90s\n", dbgCounter, iter->_describ.c_str()); fflush(stderr); }
        ++dbgCounter;
        // V<+ 条件支路回退方程的雅可比（对角 1）
        if (!fallbacks.empty()) {
            map<int, vector<int> >::iterator fb = fallbacks.find(stmtIdx);
            if (fb != fallbacks.end()) {
                for (int brIdx : fb->second) {
                    ofs << "    for (size_t ji = 0; ji < jacPattern_.size(); ++ji) {\n";
                    ofs << "        if (jacPattern_[ji].first == " << brIdx << " && jacPattern_[ji].second == " << brIdx << ")\n";
                    ofs << "            out.jac[ji] += 1.0;  // fallback: Ibr=0\n";
                    ofs << "    }\n";
                }
            }
        }
        ++stmtIdx;
        if (iter->_mode == 5) {
            ++iter; continue;
        } else if (iter->_mode == 4) {
            // 导数专用语句（if/else 支路导数清零、ddt 导数链）：
            // 在 Jacobian 段发射（_der0=0 使 ddt 导数在 DC 下为 0）
            ofs << "    " << iter->_describ << "\n";
            ++iter; continue;
        } else if (iter->_mode == 2) {
            // Contribution: 一般 RHS 直接符号微分（包装为 contributetmp = <rhs>）
            source* mysource = *sourceiter;
            ++sourceiter;

            // 收集依赖变量索引与名称
            set<int> depVarIndices;
            set<string> depVarNames;
            for (map<string, bitset<BIT_> >::iterator vit = iter->_var.begin();
                 vit != iter->_var.end(); ++vit) {
                depVarNames.insert(vit->first);
                for (int b = 0; b < BIT_; ++b) {
                    if (vit->second[b]) depVarIndices.insert(b);
                }
            }

            if (!depVarIndices.empty() && iter->_type) {
                statement mystat = *iter;
                // deriv 语法要求结尾分号（derYacc program: assign ';'）
                mystat._describ = "contributetmp = " + iter->_describ + ";";
                string derivResult = calculate_deriv(mystat, depVarNames);
                EmitDerivLines(derivResult, iter->_param, ofs);
            }

            // Stamp 导数到 out.jac
            int posNode = mysource->_pos;
            int negNode = (mysource->_nodenum >= 2) ? mysource->_neg : -1;

            for (set<int>::iterator dit = depVarIndices.begin(); dit != depVarIndices.end(); ++dit) {
                int depIdx = *dit;
                ofs << "    for (size_t ji = 0; ji < jacPattern_.size(); ++ji) {\n";
                ofs << "        if (jacPattern_[ji].first == " << posNode << " && jacPattern_[ji].second == " << depIdx << ")\n";
                ofs << "            out.jac[ji] += dcontributetmpDv" << depIdx << ";\n";
                if (negNode >= 0) {
                    ofs << "        if (jacPattern_[ji].first == " << negNode << " && jacPattern_[ji].second == " << depIdx << ")\n";
                    ofs << "            out.jac[ji] -= dcontributetmpDv" << depIdx << ";\n";
                }
                ofs << "    }\n";
            }
        } else {
            if (iter->_type) {
                // Normal assignment: 输出微分结果（只导数行，不重复原始表达式）
                set<string> depVarNames;
                for (map<string, bitset<BIT_> >::iterator vit = iter->_var.begin();
                     vit != iter->_var.end(); ++vit) {
                    depVarNames.insert(vit->first);
                }
                string derivResult = calculate_deriv(*iter, depVarNames);
                EmitDerivLines(derivResult, iter->_param, ofs);
            } else {
                // 结构语句（if/else/}/switch/case/break/default）：保留控制流，
                // 使 Jacobian 与残差同分支；其他 _type=false 语句（纯参数重算）跳过。
                string desc = iter->_describ;
                size_t p = desc.find_first_not_of(" \t");
                string trimmed = (p == string::npos) ? "" : desc.substr(p);
                if (trimmed.rfind("if(", 0) == 0 || trimmed.rfind("if (", 0) == 0 ||
                    trimmed.rfind("}", 0) == 0 ||
                    trimmed.rfind("while(", 0) == 0 || trimmed.rfind("while (", 0) == 0 ||
                    trimmed.rfind("for(", 0) == 0 || trimmed.rfind("for (", 0) == 0 ||
                    trimmed.rfind("switch(", 0) == 0 || trimmed.rfind("switch (", 0) == 0 ||
                    trimmed.rfind("case ", 0) == 0 || trimmed.rfind("default", 0) == 0 ||
                    trimmed.rfind("break;", 0) == 0) {
                    ofs << "    " << RfsimReplaceModelParam(*iter) << "\n";
                }
            }
        }
        ++iter;
    }
}
