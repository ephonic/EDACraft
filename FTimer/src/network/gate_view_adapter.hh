#pragma once

#include "edacraft/core/ids.hpp"
#include "edacraft/core/string_pool.hpp"
#include "network/network.hh"
#include "time_engine/types.hh"

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace edacraft::core {
class GateNetlistView;
}

namespace te {

struct GateViewPinRef {
    std::string instance_name;
    std::string pin_name;
};

struct GateViewNetworkBuildResult {
    std::unique_ptr<Network> network;
    std::unordered_map<std::string, PinId> pins_by_full_name;
    std::unordered_map<uint32_t, edacraft::core::PinHandle> pin_to_core_pin;
    std::unordered_map<uint32_t, PinId> core_pin_to_pin;
    std::unordered_map<std::string, std::vector<PinId>> port_aliases;
};

GateViewNetworkBuildResult network_from_gate_view(
    const edacraft::core::GateNetlistView& view,
    const std::unordered_map<std::string, std::vector<std::string>>& port_aliases = {},
    edacraft::core::StringPool* shared_string_pool = nullptr);

} // namespace te
