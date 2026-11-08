#include "edacraft/core/gate_netlist_view.hpp"
#include <sstream>
#include <algorithm>

namespace edacraft::core {

GateNetlistView::GateNetlistView() = default;
GateNetlistView::~GateNetlistView() = default;

void GateNetlistView::reserve(std::size_t instance_count,
                              std::size_t net_count,
                              std::size_t port_count) {
    instances_.reserve(instance_count);
    nets_.reserve(net_count);
    ports_.reserve(port_count);
    inst_name_map_.reserve(instance_count);
    net_name_map_.reserve(net_count);
}

InstanceHandle GateNetlistView::add_instance(const std::string& name,
                                              const std::string& cell_name) {
    auto existing = inst_name_map_.find(name);
    if (existing != inst_name_map_.end()) return existing->second;

    uint32_t id = static_cast<uint32_t>(instances_.size());
    InstanceHandle handle{id};
    GateInstance inst;
    inst.inst_name = name;
    inst.cell_name = cell_name;
    inst.handle = handle;
    instances_.push_back(std::move(inst));
    inst_name_map_[name] = handle;
    return handle;
}

NetHandle GateNetlistView::add_net(const std::string& name) {
    auto existing = net_name_map_.find(name);
    if (existing != net_name_map_.end()) return existing->second;

    uint32_t id = static_cast<uint32_t>(nets_.size());
    NetHandle handle{id};
    GateNet net;
    net.name = name;
    net.handle = handle;
    nets_.push_back(std::move(net));
    net_name_map_[name] = handle;
    return handle;
}

InstanceHandle GateNetlistView::get_or_add_instance(const std::string& name,
                                                    const std::string& cell_name) {
    auto it = inst_name_map_.find(name);
    if (it != inst_name_map_.end()) return it->second;
    return add_instance(name, cell_name);
}

NetHandle GateNetlistView::get_or_add_net(const std::string& name) {
    auto it = net_name_map_.find(name);
    if (it != net_name_map_.end()) return it->second;
    return add_net(name);
}

void GateNetlistView::set_net_constant(NetHandle net, int value) {
    if (!valid(net) || net.id >= nets_.size()) return;
    nets_[net.id].constant_value = value ? 1 : 0;
}

std::optional<int> GateNetlistView::net_constant(NetHandle net) const {
    if (!valid(net) || net.id >= nets_.size()) return std::nullopt;
    int8_t value = nets_[net.id].constant_value;
    if (value != 0 && value != 1) return std::nullopt;
    return static_cast<int>(value);
}

void GateNetlistView::connect_pin(InstanceHandle inst, const std::string& pin_name,
                                    NetHandle net, bool is_output) {
    if (inst.id >= instances_.size()) return;
    if (!valid(net)) return;

    auto& inst_data = instances_[inst.id];
    std::string full_pin = inst_data.inst_name + "/" + pin_name;

    auto remove_from_net = [&](NetHandle old_net) {
        if (!valid(old_net) || old_net.id >= nets_.size()) return;
        auto& old_net_data = nets_[old_net.id];
        if (old_net_data.driver_pin == full_pin) {
            old_net_data.driver_pin.clear();
        }
        old_net_data.load_pins.erase(
            std::remove(old_net_data.load_pins.begin(),
                        old_net_data.load_pins.end(),
                        full_pin),
            old_net_data.load_pins.end());
    };

    PinConnection* existing = nullptr;
    for (auto& existing_pin : inst_data.pins) {
        if (existing_pin.pin_name == pin_name) {
            existing = &existing_pin;
            break;
        }
    }

    PinHandle pin_handle = existing ? existing->handle : PinHandle{next_pin_id_++};
    if (existing) {
        remove_from_net(existing->net);
        existing->handle = pin_handle;
        existing->net = net;
        existing->is_output = is_output;
    } else {
        PinConnection pc;
        pc.handle = pin_handle;
        pc.pin_name = pin_name;
        pc.net = net;
        pc.is_output = is_output;
        inst_data.pins.push_back(pc);
    }

    // Record driver/load on the net
    auto& net_data = nets_[net.id];
    if (is_output) {
        net_data.driver_pin = full_pin;
    } else {
        net_data.load_pins.push_back(full_pin);
    }
}

void GateNetlistView::add_port(const std::string& name, PortDirection dir,
                                 NetHandle net, uint16_t bus_width) {
    NetlistPort port;
    port.pin = PinHandle{next_pin_id_++};
    port.name = name;
    port.direction = dir;
    port.net = net;
    port.bus_width = bus_width;
    ports_.push_back(std::move(port));

    if (!valid(net) || net.id >= nets_.size()) return;
    auto& net_data = nets_[net.id];
    std::string full_pin = "design/" + name;
    if (dir == PortDirection::Input || dir == PortDirection::Inout) {
        net_data.driver_pin = full_pin;
    }
    if (dir == PortDirection::Output || dir == PortDirection::Inout) {
        net_data.load_pins.push_back(full_pin);
    }
}

const GateInstance& GateNetlistView::instance(InstanceHandle h) const {
    return instances_[h.id];
}

const GateNet& GateNetlistView::net(NetHandle h) const {
    return nets_[h.id];
}

std::optional<PinHandle> GateNetlistView::find_pin_handle(
    InstanceHandle inst, const std::string& pin_name) const {
    if (!valid(inst) || inst.id >= instances_.size()) return std::nullopt;
    for (const auto& pin : instances_[inst.id].pins) {
        if (pin.pin_name == pin_name) return pin.handle;
    }
    return std::nullopt;
}

std::optional<PinHandle> GateNetlistView::find_port_pin_handle(
    const std::string& name) const {
    for (const auto& port : ports_) {
        if (port.name == name) return port.pin;
    }
    return std::nullopt;
}

const GateInstance* GateNetlistView::find_instance(const std::string& name) const {
    auto it = inst_name_map_.find(name);
    if (it != inst_name_map_.end()) return &instances_[it->second.id];
    return nullptr;
}

const GateNet* GateNetlistView::find_net(const std::string& name) const {
    auto it = net_name_map_.find(name);
    if (it != net_name_map_.end()) return &nets_[it->second.id];
    return nullptr;
}

InstanceHandle GateNetlistView::find_instance_handle(const std::string& name) const {
    auto it = inst_name_map_.find(name);
    if (it != inst_name_map_.end()) return it->second;
    return NULL_INSTANCE;
}

NetHandle GateNetlistView::find_net_handle(const std::string& name) const {
    auto it = net_name_map_.find(name);
    if (it != net_name_map_.end()) return it->second;
    return NULL_NET;
}

void GateNetlistView::for_each_instance(std::function<void(const GateInstance&)> fn) const {
    for (const auto& inst : instances_) fn(inst);
}

void GateNetlistView::for_each_net(std::function<void(const GateNet&)> fn) const {
    for (const auto& net : nets_) fn(net);
}

std::string GateNetlistView::to_verilog(const std::string& module_name) const {
    std::ostringstream oss;

    // Determine ports: use explicit ports if set, otherwise infer from net topology
    std::vector<NetlistPort> effective_ports = ports_;
    if (effective_ports.empty()) {
        // Infer ports from net topology: undriven nets = inputs, no-load nets = outputs
        for (const auto& net : nets_) {
            if (net.driver_pin.empty() && !net.load_pins.empty()) {
                NetlistPort p;
                p.name = net.name;
                p.direction = PortDirection::Input;
                p.net = net.handle;
                effective_ports.push_back(p);
            } else if (!net.driver_pin.empty() && net.load_pins.empty()) {
                NetlistPort p;
                p.name = net.name;
                p.direction = PortDirection::Output;
                p.net = net.handle;
                effective_ports.push_back(p);
            }
        }
    }

    // Module declaration
    oss << "module " << module_name << " (\n";
    bool first = true;
    for (const auto& p : effective_ports) {
        if (!first) oss << ",\n";
        switch (p.direction) {
            case PortDirection::Input:  oss << "  input "; break;
            case PortDirection::Output: oss << "  output "; break;
            case PortDirection::Inout:  oss << "  inout "; break;
            default: oss << "  wire "; break;
        }
        if (p.bus_width > 1) {
            oss << "[" << (p.bus_width - 1) << ":0] ";
        }
        oss << p.name;
        first = false;
    }
    oss << "\n);\n\n";

    // Collect port net names for wire declaration filtering.  A port may be
    // bound to an internal net with a different name; in that case the net
    // still needs a wire declaration and an assign below.
    std::unordered_map<std::string, bool> port_nets;
    for (const auto& p : effective_ports) {
        if (valid(p.net)) {
            const auto& net_name = nets_[p.net.id].name;
            if (net_name == p.name) {
                port_nets[net_name] = true;
            }
        } else {
            port_nets[p.name] = true;
        }
    }

    // Declare internal wires (skip nets that are ports)
    for (const auto& net : nets_) {
        if (port_nets.count(net.name)) continue;
        oss << "  wire " << net.name << ";\n";
    }
    oss << "\n";

    // Connect top-level ports to internal net names when they differ.
    for (const auto& p : effective_ports) {
        if (!valid(p.net)) continue;
        const auto& net_name = nets_[p.net.id].name;
        if (net_name == p.name) continue;
        switch (p.direction) {
            case PortDirection::Input:
                oss << "  assign " << net_name << " = " << p.name << ";\n";
                break;
            case PortDirection::Output:
                oss << "  assign " << p.name << " = " << net_name << ";\n";
                break;
            default:
                break;
        }
    }
    if (!effective_ports.empty()) oss << "\n";

    for (const auto& net : nets_) {
        if ((net.constant_value == 0 || net.constant_value == 1) &&
            net.driver_pin.empty()) {
            oss << "  assign " << net.name << " = 1'b"
                << static_cast<int>(net.constant_value) << ";\n";
        }
    }
    if (!nets_.empty()) oss << "\n";

    // Instantiate cells with pin connections
    for (const auto& inst : instances_) {
        oss << "  " << inst.cell_name << " " << inst.inst_name << " (";
        if (!inst.pins.empty()) {
            oss << "\n";
            for (size_t i = 0; i < inst.pins.size(); ++i) {
                const auto& pc = inst.pins[i];
                // Find the net name for this pin
                std::string net_name;
                if (valid(pc.net)) {
                    net_name = nets_[pc.net.id].name;
                }
                oss << "    ." << pc.pin_name << "(" << net_name << ")";
                if (i + 1 < inst.pins.size()) oss << ",";
                oss << "\n";
            }
            oss << "  ";
        }
        oss << ");\n";
    }

    oss << "\nendmodule\n";
    return oss.str();
}

GateNetlistView::ValidationReport GateNetlistView::validate() const {
    ValidationReport report;

    std::vector<uint32_t> driver_counts(nets_.size(), 0);
    std::vector<bool> external_inouts(nets_.size(), false);
    for (const auto& port : ports_) {
        if (!valid(port.net) || port.net.id >= driver_counts.size()) continue;
        if (port.direction == PortDirection::Input) {
            driver_counts[port.net.id]++;
        } else if (port.direction == PortDirection::Inout) {
            // An inout marks an external resolved boundary, not another
            // unconditional internal driver. It supplies read-side data when
            // the local output is high impedance. Still count every actual
            // output pin so conflicting internal drivers remain invalid.
            external_inouts[port.net.id] = true;
        }
    }
    for (const auto& inst : instances_) {
        for (const auto& pc : inst.pins) {
            if (pc.is_output && valid(pc.net) && pc.net.id < driver_counts.size()) {
                driver_counts[pc.net.id]++;
            }
        }
    }

    for (const auto& net : nets_) {
        if (net.constant_value == 0 || net.constant_value == 1) continue;
        const uint32_t driver_count = driver_counts[net.handle.id];
        if (driver_count == 0 && !external_inouts[net.handle.id] &&
            !net.load_pins.empty()) {
            report.undriven_nets++;
        }
        if (driver_count > 1) {
            report.multi_driver_nets++;
            report.warnings.push_back("Net '" + net.name + "' has " +
                                      std::to_string(driver_count) + " drivers");
        }
    }

    return report;
}

void GateNetlistView::clear() {
    instances_.clear();
    nets_.clear();
    ports_.clear();
    inst_name_map_.clear();
    net_name_map_.clear();
    next_pin_id_ = 0;
}

} // namespace edacraft::core
