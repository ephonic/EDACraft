#pragma once
#include "gate_compiler.hpp"
namespace dsim {
// Conservative gate-only analysis. This does not change executable scheduling.
std::string gate_partition_report(const GateDesign&,size_t partitions);
}
