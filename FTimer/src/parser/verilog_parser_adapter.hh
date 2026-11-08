#pragma once

#include <string>
#include "network/network.hh"

namespace te {

// Build Network from parsed Verilog gate-level netlist.
// Uses the streaming GateNetlistParser for large designs (no AST).
// Returns the top module name.
std::string build_network_from_verilog(
    Network& network,
    std::string_view filepath,
    std::string_view include_dir = "",
    std::string_view preferred_top_name = "");

} // namespace te
