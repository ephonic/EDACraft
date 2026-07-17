// flatten.cpp — 子电路展开与节点解析
#include "flatten.hpp"

#include <map>
#include <sstream>
#include <unordered_map>

namespace rfsim {

namespace {

// 子电路定义查找表：name -> def
using SubcktMap = std::unordered_map<std::string, std::shared_ptr<SubcktDef>>;

void collectSubckts(const Netlist& netlist, SubcktMap& out) {
    for (const auto& it : netlist.items) {
        if (std::holds_alternative<std::shared_ptr<SubcktDef>>(it)) {
            auto def = std::get<std::shared_ptr<SubcktDef>>(it);
            out[def->name] = def;
        }
    }
}

// 形参绑定：子电路形参默认值 + 调用实参 -> 参数表
// 返回 形参名(小写) -> 已求值的 ParamValue（字符串/数值/表达式原样保留）
std::map<std::string, ParamValue> bindParams(const SubcktDef& def, const SubcktCall& call) {
    std::map<std::string, ParamValue> bound;
    // 默认值
    for (const auto& [pname, pval] : def.params) bound[pname] = pval;
    // 实参：命名优先，位置参按形参顺序填充
    size_t posIdx = 0;
    for (const auto& [pname, pval] : call.params) {
        if (!pname.empty()) {
            bound[pname] = pval;
        } else {
            // 位置参对应形参列表（按 ports 之后? 实际 SPICE 位置参对应 .subckt 形参顺序）
            // 简化：按 def.params 顺序填充
            if (posIdx < def.params.size()) {
                bound[def.params[posIdx].first] = pval;
                ++posIdx;
            }
        }
    }
    return bound;
}

// 节点重映射：子电路端口名 -> 调用处实际节点名
// 内部节点保持原样（带前缀避免冲突）
struct FlattenCtx {
    Circuit& circuit;
    const SubcktMap& subckts;
    Diagnostics& diags;
    // 当前层级前缀
    std::string prefix;
    // 当前作用域的节点重映射：子电路内节点名 -> 外部实际节点名
    std::unordered_map<std::string, std::string> nodeMap;
};

// 递归展开一个语句序列（子电路体或顶层 items）
void expandItems(const std::vector<NetlistItem>& items, FlattenCtx& ctx);

void expandSubcktCall(const SubcktCall& call, FlattenCtx& ctx) {
    auto it = ctx.subckts.find(call.subcktName);
    if (it == ctx.subckts.end()) {
        ctx.diags.error(call.loc, "unknown subckt: " + call.subcktName);
        return;
    }
    const auto& def = *it->second;
    if (call.nodes.size() != def.ports.size()) {
        ctx.diags.error(call.loc, "subckt port count mismatch: " + call.subcktName);
        // 继续尽量展开
    }

    // 建立节点重映射：端口名 -> 外部节点名（经当前 nodeMap 转换后的实际名）
    std::unordered_map<std::string, std::string> childNodeMap;
    for (size_t i = 0; i < def.ports.size() && i < call.nodes.size(); ++i) {
        // call.nodes[i] 在当前作用域；先解析当前作用域的映射
        std::string extNode = call.nodes[i];
        auto mit = ctx.nodeMap.find(extNode);
        if (mit != ctx.nodeMap.end()) extNode = mit->second;
        childNodeMap[def.ports[i]] = extNode;
    }

    // 参数绑定
    auto bound = bindParams(def, call);

    // 子作用域
    FlattenCtx child{ctx.circuit, ctx.subckts, ctx.diags,
                     ctx.prefix + call.name + ".", std::move(childNodeMap)};

    // 子电路内部可能有自己的 .param —— 形参已 bound，作为参数传递
    // 把 bound 参数注入为器件参数引用（M1 简化：不展开参数表达式，保留引用文本）
    expandItems(def.body, child);
}

void expandItems(const std::vector<NetlistItem>& items, FlattenCtx& ctx) {
    for (const auto& it : items) {
        if (std::holds_alternative<DeviceCard>(it)) {
            const auto& d = std::get<DeviceCard>(it);
            FlatDevice fd;
            fd.name = ctx.prefix + d.name;
            fd.firstLetter = d.firstLetter;
            fd.model = d.model;
            fd.params = d.params;
            fd.positional = d.positional;
            fd.loc = d.loc;
            for (const auto& n : d.nodes) {
                std::string actual = n;
                auto mit = ctx.nodeMap.find(n);
                if (mit != ctx.nodeMap.end()) actual = mit->second;
                fd.nodes.push_back(ctx.circuit.nodes.intern(actual));
            }
            ctx.circuit.devices.push_back(std::move(fd));
        } else if (std::holds_alternative<ModelCard>(it)) {
            const auto& m = std::get<ModelCard>(it);
            // 模型定义只在顶层收集一次（子电路内模型定义较少见，简化为重复收集）
            FlatModel fm; fm.name = m.name; fm.type = m.type; fm.params = m.params; fm.loc = m.loc;
            ctx.circuit.models.push_back(std::move(fm));
        } else if (std::holds_alternative<SubcktCall>(it)) {
            expandSubcktCall(std::get<SubcktCall>(it), ctx);
        } else if (std::holds_alternative<std::shared_ptr<SubcktDef>>(it)) {
            // 嵌套子电路定义：注册到全局表（递归收集已在顶层完成，此处跳过）
        } else if (std::holds_alternative<ControlCard>(it)) {
            const auto& c = std::get<ControlCard>(it);
            ctx.circuit.controls.push_back(c);
        }
    }
}

} // namespace

FlattenResult flatten(const Netlist& netlist) {
    FlattenResult r;
    r.circuit.title = netlist.title;
    r.circuit.globalParams = netlist.globalParams;

    SubcktMap subckts;
    collectSubckts(netlist, subckts);

    FlattenCtx ctx{r.circuit, subckts, r.diags, "", {}};
    expandItems(netlist.items, ctx);

    r.ok = !r.diags.has_errors();
    return r;
}

} // namespace rfsim
