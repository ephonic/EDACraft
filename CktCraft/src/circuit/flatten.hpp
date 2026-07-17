// flatten.hpp — 将 AST 网表扁平化为 Circuit（展开子电路、解析节点）
#ifndef RFSIM_CIRCUIT_FLATTEN_HPP
#define RFSIM_CIRCUIT_FLATTEN_HPP

#include "circuit.hpp"
#include "../parser/ast.hpp"
#include "../rfsim.hpp"

namespace rfsim {

struct FlattenResult {
    Circuit     circuit;
    Diagnostics diags;
    bool        ok = false;
};

// 扁平化网表 AST 为电路对象
FlattenResult flatten(const Netlist& netlist);

} // namespace rfsim

#endif // RFSIM_CIRCUIT_FLATTEN_HPP
