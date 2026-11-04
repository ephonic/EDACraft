#include "verilog_parser_adapter.hh"

#include <stdexcept>
#include <filesystem>

#include "gate_netlist_parser.hh"

namespace te {

std::string build_network_from_verilog(
    Network& network,
    std::string_view filepath,
    std::string_view /*include_dir*/,
    std::string_view preferred_top_name)
{
    // The new GateNetlistParser handles:
    //   - Multi-line port lists & instantiations
    //   - Escaped identifiers
    //   - Bit-select / part-select
    //   - assign statements (modelled as __assign__ cells)
    //   - Automatic black-box cell inference (no stubs needed)
    //   - Constant literals
    //
    // It is streaming-based: no AST, no OOM on 86K+ cell designs.
    GateNetlistParser parser(network);
    return parser.parse(filepath, preferred_top_name);
}

} // namespace te
