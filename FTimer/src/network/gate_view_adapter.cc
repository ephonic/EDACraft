#include "network/gate_view_adapter.hh"

#include "edacraft/core/gate_netlist_view.hpp"
#include "network/network.hh"

#include <utility>
#include <unordered_set>
#include <cstdlib>
#include <iostream>

namespace te {

namespace {

PortDirection convert_direction(edacraft::core::PortDirection dir) {
    switch (dir) {
        case edacraft::core::PortDirection::Input:
            return PortDirection::Output;
        case edacraft::core::PortDirection::Output:
            return PortDirection::Input;
        case edacraft::core::PortDirection::Inout:
            return PortDirection::Inout;
        default:
            return PortDirection::Internal;
    }
}

} // namespace

GateViewNetworkBuildResult network_from_gate_view(
    const edacraft::core::GateNetlistView& view,
    const std::unordered_map<std::string, std::vector<std::string>>& port_aliases,
    edacraft::core::StringPool* shared_string_pool) {
    GateViewNetworkBuildResult result;
    // Seed an owning per-network pool with the core strings so Liberty
    // StringIds remain identical, then keep generated net/instance/pin names
    // local to this timing-network generation. Using the mutable overload
    // here used to append every full STA rebuild's temporary names to the
    // long-lived DesignDB pool, so releasing an old Network did not release
    // most of its string memory.
    auto network = shared_string_pool
        ? std::make_unique<Network>(
              static_cast<const edacraft::core::StringPool&>(
                  *shared_string_pool))
        : std::make_unique<Network>();

    size_t instance_pin_count = 0;
    for (const auto& inst : view.instances()) {
        instance_pin_count += inst.pins.size();
    }
    const size_t port_count = view.ports().size();

    std::unordered_map<uint32_t, NetId> net_ids;
    net_ids.reserve(view.nets().size());
    for (const auto& net : view.nets()) {
        NetId net_id = network->create_net(net.name);
        net_ids[net.handle.id] = net_id;
        if (net.constant_value == 0 || net.constant_value == 1) {
            network->set_net_constant(net_id, net.constant_value);
        }
    }

    std::unordered_map<std::string, CellId> cell_ids;
    std::unordered_map<uint32_t, std::unordered_set<std::string>> cell_port_names;
    cell_ids.reserve(view.instances().size() + 1);
    cell_port_names.reserve(view.instances().size() + 1);
    result.pins_by_full_name.reserve(instance_pin_count + port_count * 2 + 8);
    result.pin_to_core_pin.reserve(instance_pin_count + port_count);
    result.core_pin_to_pin.reserve(instance_pin_count + port_count);
    result.port_aliases.reserve(port_count + port_aliases.size());
    auto get_cell = [&](const std::string& cell_name) -> CellId {
        auto it = cell_ids.find(cell_name);
        if (it != cell_ids.end()) return it->second;
        CellId cell = network->create_cell(cell_name);
        cell_ids[cell_name] = cell;
        return cell;
    };
    auto add_cell_port_once = [&](CellId cell, const std::string& port_name) {
        auto& names = cell_port_names[cell.id];
        if (names.insert(port_name).second) {
            network->add_port(cell, port_name);
        }
    };

    CellId top_cell = get_cell("__top__");
    InstanceId top_inst = network->create_instance("design", top_cell);

    std::unordered_map<uint32_t, InstanceId> inst_ids;
    inst_ids.reserve(view.instances().size());
    for (const auto& inst : view.instances()) {
        if (inst.inst_name == "design" && inst.cell_name == "__top__") {
            inst_ids[inst.handle.id] = top_inst;
            continue;
        }
        CellId cell = get_cell(inst.cell_name);
        InstanceId instance = network->create_instance(inst.inst_name, cell);
        inst_ids[inst.handle.id] = instance;
    }

    for (const auto& inst : view.instances()) {
        auto inst_it = inst_ids.find(inst.handle.id);
        if (inst_it == inst_ids.end()) continue;
        InstanceId instance = inst_it->second;
        CellId cell = network->instance(instance).cell;
        for (const auto& pc : inst.pins) {
            PortDirection dir = pc.is_output ? PortDirection::Output : PortDirection::Input;
            if (inst.inst_name == "design" && inst.cell_name == "__top__") {
                dir = pc.is_output ? PortDirection::Output : PortDirection::Input;
            }
            add_cell_port_once(cell, pc.pin_name);
            PinId pin = network->create_pin(pc.pin_name, instance, dir);
            network->add_pin(instance, pin);
            if (edacraft::core::valid(pc.net)) {
                auto net_it = net_ids.find(pc.net.id);
                if (net_it != net_ids.end()) {
                    network->connect_pin_to_net(pin, net_it->second);
                }
            }
            if (const char* filter = std::getenv("FSYN_TIMING_DEBUG_PIN");
                filter && *filter && pc.pin_name == "D" &&
                (inst.inst_name + "/" + pc.pin_name).find(filter) != std::string::npos) {
                const auto& core_net = edacraft::core::valid(pc.net)
                    ? view.net(pc.net) : edacraft::core::GateNet{};
                std::cerr << "[timing_debug_adapter] pin=" << inst.inst_name
                          << "/" << pc.pin_name
                          << " is_output=" << pc.is_output
                          << " core_net=" << (edacraft::core::valid(pc.net) ? core_net.name : "none")
                          << " core_driver=" << (edacraft::core::valid(pc.net) ? core_net.driver_pin : "none")
                          << " core_loads=" << (edacraft::core::valid(pc.net) ? core_net.load_pins.size() : 0)
                          << "\n";
            }
            if (inst.inst_name.empty() || inst.inst_name == "design") {
                result.pins_by_full_name[pc.pin_name] = pin;
                result.pins_by_full_name["design/" + pc.pin_name] = pin;
            } else {
                result.pins_by_full_name[inst.inst_name + "/" + pc.pin_name] = pin;
            }
            if (edacraft::core::valid(pc.handle)) {
                result.pin_to_core_pin[pin.id] = pc.handle;
                result.core_pin_to_pin[pc.handle.id] = pin;
            }
        }
    }

    for (const auto& port : view.ports()) {
        add_cell_port_once(top_cell, port.name);
        PinId pin = network->create_pin(port.name, top_inst, convert_direction(port.direction));
        network->add_pin(top_inst, pin);
        if (edacraft::core::valid(port.net)) {
            auto net_it = net_ids.find(port.net.id);
            if (net_it != net_ids.end()) {
                network->connect_pin_to_net(pin, net_it->second);
            }
        }
        result.pins_by_full_name[port.name] = pin;
        result.pins_by_full_name["design/" + port.name] = pin;
        if (edacraft::core::valid(port.pin)) {
            result.pin_to_core_pin[pin.id] = port.pin;
            result.core_pin_to_pin[port.pin.id] = pin;
        }
        result.port_aliases[port.name].push_back(pin);
    }

    for (const auto& [base, names] : port_aliases) {
        auto& pins = result.port_aliases[base];
        for (const auto& name : names) {
            auto it = result.pins_by_full_name.find(name);
            if (it == result.pins_by_full_name.end()) {
                it = result.pins_by_full_name.find("design/" + name);
            }
            if (it != result.pins_by_full_name.end()) {
                pins.push_back(it->second);
            }
        }
    }

    network->rebuild_net_connections();
    result.network = std::move(network);
    return result;
}

} // namespace te
