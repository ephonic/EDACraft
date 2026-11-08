#ifndef EDACRAFT_CORE_GATE_NETLIST_VIEW_HPP
#define EDACRAFT_CORE_GATE_NETLIST_VIEW_HPP

#include "edacraft/core/ids.hpp"
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <optional>
#include <cstddef>

namespace edacraft::core {

// ─── Pin connection record ──────────────────────────────────────────
struct PinConnection {
    PinHandle handle = NULL_PIN;        // canonical pin handle in this view
    std::string pin_name;            // Liberty cell pin name (e.g. "A1", "ZN")
    NetHandle net = NULL_NET;        // net this pin connects to
    bool is_output = false;          // true if this pin is a cell output
};

// ─── Gate instance in the netlist ───────────────────────────────────
struct GateInstance {
    std::string inst_name;           // e.g. "U1", "gate_42"
    std::string cell_name;           // Liberty cell name (e.g. "BUF_X2")
    InstanceHandle handle = NULL_INSTANCE;
    std::vector<PinConnection> pins; // all pin connections
};

// ─── Net in the gate netlist ────────────────────────────────────────
struct GateNet {
    std::string name;
    NetHandle handle = NULL_NET;
    std::string driver_pin;          // "inst_name/pin_name" of the driver
    std::vector<std::string> load_pins; // "inst_name/pin_name" of loads
    int8_t constant_value = -1;      // -1 unknown, 0/1 static constant net
};

// ─── Port declaration for Verilog output ────────────────────────────
struct NetlistPort {
    PinHandle pin = NULL_PIN;           // canonical top-level port pin handle
    std::string name;
    PortDirection direction = PortDirection::Input;
    uint16_t bus_width = 1;          // 1 = scalar, >1 = bus
    NetHandle net = NULL_NET;        // net this port connects to
};

// ─── Gate-level netlist view ────────────────────────────────────────
// Provides a stable, queryable gate-level netlist representation
// that both fsyn (for writing Verilog) and ftimer (for building
// timing graph) can consume.
class GateNetlistView {
public:
    GateNetlistView();
    ~GateNetlistView();

    // ── Construction ─────────────────────────────────────────────
    void reserve(std::size_t instance_count,
                 std::size_t net_count,
                 std::size_t port_count = 0);
    InstanceHandle add_instance(const std::string& name,
                                const std::string& cell_name);
    NetHandle add_net(const std::string& name);
    InstanceHandle get_or_add_instance(const std::string& name,
                                       const std::string& cell_name);
    NetHandle get_or_add_net(const std::string& name);
    void set_net_constant(NetHandle net, int value);
    std::optional<int> net_constant(NetHandle net) const;

    // Connect a pin of an instance to a net.
    // is_output = true marks this pin as a cell output (drives the net).
    void connect_pin(InstanceHandle inst, const std::string& pin_name,
                     NetHandle net, bool is_output = false);

    // ── Ports ────────────────────────────────────────────────────
    void add_port(const std::string& name, PortDirection dir,
                  NetHandle net, uint16_t bus_width = 1);
    const std::vector<NetlistPort>& ports() const { return ports_; }

    // ── Query ────────────────────────────────────────────────────
    uint32_t instance_count() const { return static_cast<uint32_t>(instances_.size()); }
    uint32_t net_count() const { return static_cast<uint32_t>(nets_.size()); }

    const GateInstance& instance(InstanceHandle h) const;
    const GateNet& net(NetHandle h) const;
    std::optional<PinHandle> find_pin_handle(InstanceHandle inst,
                                             const std::string& pin_name) const;
    std::optional<PinHandle> find_port_pin_handle(const std::string& name) const;

    const GateInstance* find_instance(const std::string& name) const;
    const GateNet* find_net(const std::string& name) const;
    InstanceHandle find_instance_handle(const std::string& name) const;
    NetHandle find_net_handle(const std::string& name) const;

    const std::vector<GateInstance>& instances() const { return instances_; }
    const std::vector<GateNet>& nets() const { return nets_; }

    // ── Iteration ────────────────────────────────────────────────
    void for_each_instance(std::function<void(const GateInstance&)> fn) const;
    void for_each_net(std::function<void(const GateNet&)> fn) const;

    // ── Dump ─────────────────────────────────────────────────────
    // Write gate-level Verilog netlist. This is the golden dump
    // that PrimeTime and ftimer should read identically.
    std::string to_verilog(const std::string& module_name = "top") const;

    // ── Validation ───────────────────────────────────────────────
    struct ValidationReport {
        uint32_t undriven_nets = 0;
        uint32_t unconnected_pins = 0;
        uint32_t multi_driver_nets = 0;
        std::vector<std::string> warnings;
    };
    ValidationReport validate() const;

    void clear();

private:
    std::vector<GateInstance> instances_;
    std::vector<GateNet> nets_;
    std::vector<NetlistPort> ports_;
    uint32_t next_pin_id_ = 0;
    std::unordered_map<std::string, InstanceHandle> inst_name_map_;
    std::unordered_map<std::string, NetHandle> net_name_map_;

};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_GATE_NETLIST_VIEW_HPP
