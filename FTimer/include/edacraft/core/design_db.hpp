#ifndef EDACRAFT_CORE_DESIGN_DB_HPP
#define EDACRAFT_CORE_DESIGN_DB_HPP

#include "edacraft/core/constraint_db.hpp"
#include "edacraft/core/ids.hpp"
#include "edacraft/core/liberty_db.hpp"
#include "edacraft/core/logic_view.hpp"
#include "edacraft/core/parasitic_db.hpp"
#include "edacraft/core/resolved_constraint_set.hpp"
#include "edacraft/core/string_pool.hpp"
#include "edacraft/core/timing_db.hpp"
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace edacraft::core {

// Forward declarations for views
class GateNetlistView;

// ─── Design metadata ────────────────────────────────────────────────
struct DesignInfo {
    std::string design_name;
    std::string technology;          // e.g. "tsmc28", "sky130"
    float time_unit_ns = 1.0f;       // library time unit in ns
    float cap_unit_pf = 1.0f;        // library cap unit in pF
    float res_unit_ohm = 1.0f;       // library resistance unit in ohm
};

// ─── Port definition ────────────────────────────────────────────────
struct PortDef {
    std::string name;
    PortDirection direction = PortDirection::Input;
    uint16_t bus_width = 1;          // 1 = scalar, >1 = bus
    PinHandle pin = NULL_PIN;
    NetHandle net = NULL_NET;
};

struct RuntimeNodeBinding {
    uint64_t runtime_node_id = 0;
    uint64_t canonical_node_id = 0;
};

struct RuntimePinBinding {
    uint32_t runtime_pin_id = 0;
    PinHandle pin = NULL_PIN;
};

struct RuntimePinAlias {
    std::string alias;
    std::vector<uint32_t> runtime_pin_ids;
};

struct RuntimeLogicPinBinding {
    uint64_t logic_node_id = 0;
    std::string role;
    PinHandle pin = NULL_PIN;
};

struct RuntimeGatePinNet {
    std::string pin_name;
    std::string net_name;
    bool inverted = false;
};

struct RuntimeGateInputSource {
    std::string pin_name;
    uint64_t logic_node_id = 0;
    uint16_t bit_offset = 0;
    bool inverted = false;
    // Realize the inversion after the producer cell's physical output.  This
    // prevents output-phase compensation from cancelling a required real NOT.
    bool force_materialized_inversion = false;
};

struct RuntimeGateExtraOutput {
    uint64_t logic_node_id = 0;
    std::string pin_name;
    std::string net_name;
};

struct RuntimeGateMapping {
    uint64_t logic_node_id = 0;
    std::string instance_name;
    std::string cell_name;
    std::string output_pin;
    std::string output_net;
    bool output_inverted = false;
    std::vector<RuntimeGatePinNet> input_nets;
    std::vector<RuntimeGateInputSource> input_sources;
    std::vector<RuntimeGateExtraOutput> extra_outputs;
    std::vector<uint64_t> internal_logic_node_ids;
};

// ─── Top-level design database ──────────────────────────────────────
// Owns all shared data: constraints, ports, design metadata.
// Views (GateNetlistView, LogicView, etc.) operate on this database.
class DesignDB {
public:
    DesignDB();
    ~DesignDB();

    // ── Design info ──────────────────────────────────────────────
    void set_design_name(const std::string& name);
    const std::string& design_name() const { return info_.design_name; }
    const DesignInfo& info() const { return info_; }
    DesignInfo& mutable_info() { return info_; }

    // ── Ports ────────────────────────────────────────────────────
    PinHandle add_port(const std::string& name, PortDirection dir, uint16_t width = 1);
    const PortDef* find_port(const std::string& name) const;
    const std::vector<PortDef>& ports() const { return ports_; }
    std::vector<const PortDef*> input_ports() const;
    std::vector<const PortDef*> output_ports() const;

    // ── Constraints ──────────────────────────────────────────────
    ConstraintDB& constraints() { return constraints_; }
    const ConstraintDB& constraints() const { return constraints_; }

    // ── Resolved constraints ─────────────────────────────────────
    ResolvedConstraintSet& resolved_constraints() { return resolved_constraints_; }
    const ResolvedConstraintSet& resolved_constraints() const { return resolved_constraints_; }

    // ── Liberty/timing results ───────────────────────────────────
    LibertyDB& liberty() { return liberty_; }
    const LibertyDB& liberty() const { return liberty_; }
    TimingDB& timing() { return timing_; }
    const TimingDB& timing() const { return timing_; }

    // ── Parasitics ───────────────────────────────────────────────
    ParasiticDB& parasitics() { return parasitics_; }
    const ParasiticDB& parasitics() const { return parasitics_; }

    // ── String pool (shared name storage) ────────────────────────
    StringPool& strings() { return strings_; }
    const StringPool& strings() const { return strings_; }
    uint32_t intern_string(const std::string& s);
    std::string_view lookup_string(uint32_t id) const;

    // ── View access (non-owning) ─────────────────────────────────
    void set_gate_netlist(std::shared_ptr<GateNetlistView> view);
    GateNetlistView* gate_netlist() const { return gate_netlist_.get(); }
    // Shared-ownership access for state snapshots that must keep a view alive
    // across a transaction rollback.
    std::shared_ptr<GateNetlistView> gate_netlist_shared() const {
        return gate_netlist_;
    }
    LogicView& logic_view(std::string_view domain);
    const LogicView* logic_view(std::string_view domain) const;
    void clear_logic_view(std::string_view domain);
    std::vector<std::string> logic_view_domains() const;

    // ── Runtime tool bindings ────────────────────────────────────
    void clear_runtime_pin_bindings(std::string_view domain);
    void bind_runtime_pin(std::string_view domain, uint32_t runtime_pin_id, PinHandle pin);
    std::optional<PinHandle> core_pin_for_runtime_pin(std::string_view domain,
                                                      uint32_t runtime_pin_id) const;
    std::optional<uint32_t> runtime_pin_for_core_pin(std::string_view domain,
                                                     PinHandle pin) const;
    size_t runtime_pin_binding_count(std::string_view domain) const;
    std::vector<RuntimePinBinding> runtime_pin_bindings(
        std::string_view domain) const;

    void clear_runtime_pin_aliases(std::string_view domain);
    void bind_runtime_pin_alias(std::string_view domain, std::string_view alias,
                                const std::vector<uint32_t>& runtime_pin_ids);
    std::vector<uint32_t> runtime_pins_for_alias(std::string_view domain,
                                                 std::string_view alias) const;
    size_t runtime_pin_alias_count(std::string_view domain) const;
    std::vector<RuntimePinAlias> runtime_pin_aliases(std::string_view domain) const;

    void clear_runtime_node_bindings(std::string_view domain);
    void bind_runtime_node(std::string_view domain, uint64_t runtime_node_id,
                           uint64_t canonical_node_id);
    std::optional<uint64_t> canonical_node_for_runtime_node(std::string_view domain,
                                                            uint64_t runtime_node_id) const;
    std::optional<uint64_t> runtime_node_for_canonical_node(std::string_view domain,
                                                            uint64_t canonical_node_id) const;
    size_t runtime_node_binding_count(std::string_view domain) const;
    std::vector<RuntimeNodeBinding> runtime_node_bindings(std::string_view domain) const;

    void clear_runtime_logic_pin_bindings(std::string_view domain);
    void bind_runtime_logic_pin(std::string_view domain, uint64_t logic_node_id,
                                std::string_view role, PinHandle pin);
    std::vector<PinHandle> core_pins_for_runtime_logic_node(
        std::string_view domain, uint64_t logic_node_id,
        std::string_view role = {}) const;
    std::vector<uint64_t> runtime_logic_nodes_for_core_pin(
        std::string_view domain, PinHandle pin,
        std::string_view role = {}) const;
    size_t runtime_logic_pin_binding_count(std::string_view domain) const;
    std::vector<RuntimeLogicPinBinding> runtime_logic_pin_bindings(
        std::string_view domain) const;

    void clear_runtime_gate_mappings(std::string_view domain);
    void bind_runtime_gate_mapping(std::string_view domain,
                                   RuntimeGateMapping mapping);
    std::optional<RuntimeGateMapping> runtime_gate_mapping_for_logic_node(
        std::string_view domain, uint64_t logic_node_id) const;
    std::vector<RuntimeGateMapping> runtime_gate_mappings_for_instance(
        std::string_view domain, std::string_view instance_name) const;
    size_t runtime_gate_mapping_count(std::string_view domain) const;
    std::vector<RuntimeGateMapping> runtime_gate_mappings(
        std::string_view domain) const;

    // ── Utility ──────────────────────────────────────────────────
    void clear();

private:
    struct RuntimePinBindingTable {
        std::unordered_map<uint32_t, PinHandle> runtime_to_core;
        std::unordered_map<uint32_t, uint32_t> core_to_runtime;
    };
    struct RuntimeNodeBindingTable {
        std::unordered_map<uint64_t, uint64_t> runtime_to_canonical;
        std::unordered_map<uint64_t, uint64_t> canonical_to_runtime;
    };
    struct RuntimeLogicPinBindingTable {
        std::vector<RuntimeLogicPinBinding> entries;
        std::unordered_map<uint64_t, std::vector<size_t>> node_to_entries;
        std::unordered_map<uint32_t, std::vector<size_t>> pin_to_entries;
    };
    struct RuntimeGateMappingTable {
        std::vector<RuntimeGateMapping> entries;
        std::unordered_map<uint64_t, size_t> node_to_entry;
        std::unordered_map<std::string, std::vector<size_t>> instance_to_entries;
    };

    DesignInfo info_;
    std::vector<PortDef> ports_;
    ConstraintDB constraints_;
    ResolvedConstraintSet resolved_constraints_;
    LibertyDB liberty_;
    TimingDB timing_;
    ParasiticDB parasitics_;
    StringPool strings_;

    // Views
    std::shared_ptr<GateNetlistView> gate_netlist_;
    std::unordered_map<std::string, LogicView> logic_views_;

    std::unordered_map<std::string, RuntimePinBindingTable> runtime_pin_bindings_;
    std::unordered_map<std::string, std::unordered_map<std::string, std::vector<uint32_t>>>
        runtime_pin_aliases_;
    std::unordered_map<std::string, RuntimeNodeBindingTable> runtime_node_bindings_;
    std::unordered_map<std::string, RuntimeLogicPinBindingTable> runtime_logic_pin_bindings_;
    std::unordered_map<std::string, RuntimeGateMappingTable> runtime_gate_mappings_;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_DESIGN_DB_HPP
