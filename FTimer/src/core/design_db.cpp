#include "edacraft/core/design_db.hpp"
#include "edacraft/core/gate_netlist_view.hpp"

#include <algorithm>

namespace edacraft::core {

DesignDB::DesignDB() = default;
DesignDB::~DesignDB() = default;

void DesignDB::set_design_name(const std::string& name) {
    info_.design_name = name;
}

PinHandle DesignDB::add_port(const std::string& name, PortDirection dir, uint16_t width) {
    PortDef port;
    port.name = name;
    port.direction = dir;
    port.bus_width = width;
    uint32_t id = static_cast<uint32_t>(ports_.size());
    port.pin = PinHandle{id};
    ports_.push_back(std::move(port));

    // Register bus width in constraints for port name expansion
    if (width > 1) {
        constraints_.register_bus_port(name, width);
    }

    return PinHandle{id};
}

const PortDef* DesignDB::find_port(const std::string& name) const {
    for (const auto& p : ports_) {
        if (p.name == name) return &p;
    }
    // Also check bus-expanded names like "p[0]"
    size_t bracket = name.find('[');
    if (bracket != std::string::npos) {
        std::string base = name.substr(0, bracket);
        for (const auto& p : ports_) {
            if (p.name == base) return &p;
        }
    }
    return nullptr;
}

std::vector<const PortDef*> DesignDB::input_ports() const {
    std::vector<const PortDef*> result;
    for (const auto& p : ports_) {
        if (p.direction == PortDirection::Input) result.push_back(&p);
    }
    return result;
}

std::vector<const PortDef*> DesignDB::output_ports() const {
    std::vector<const PortDef*> result;
    for (const auto& p : ports_) {
        if (p.direction == PortDirection::Output) result.push_back(&p);
    }
    return result;
}

uint32_t DesignDB::intern_string(const std::string& s) {
    return strings_.intern(s);
}

std::string_view DesignDB::lookup_string(uint32_t id) const {
    return strings_.view(id);
}

void DesignDB::set_gate_netlist(std::shared_ptr<GateNetlistView> view) {
    gate_netlist_ = std::move(view);
}

LogicView& DesignDB::logic_view(std::string_view domain) {
    return logic_views_[std::string(domain)];
}

const LogicView* DesignDB::logic_view(std::string_view domain) const {
    auto it = logic_views_.find(std::string(domain));
    if (it == logic_views_.end()) return nullptr;
    return &it->second;
}

void DesignDB::clear_logic_view(std::string_view domain) {
    logic_views_.erase(std::string(domain));
}

std::vector<std::string> DesignDB::logic_view_domains() const {
    std::vector<std::string> domains;
    domains.reserve(logic_views_.size());
    for (const auto& [domain, view] : logic_views_) {
        (void)view;
        domains.push_back(domain);
    }
    return domains;
}

void DesignDB::clear_runtime_pin_bindings(std::string_view domain) {
    runtime_pin_bindings_.erase(std::string(domain));
}

void DesignDB::bind_runtime_pin(std::string_view domain,
                                uint32_t runtime_pin_id,
                                PinHandle pin) {
    if (!valid(pin)) return;
    auto& table = runtime_pin_bindings_[std::string(domain)];
    if (auto old_core = table.runtime_to_core.find(runtime_pin_id);
        old_core != table.runtime_to_core.end()) {
        table.core_to_runtime.erase(old_core->second.id);
    }
    if (auto old_runtime = table.core_to_runtime.find(pin.id);
        old_runtime != table.core_to_runtime.end()) {
        table.runtime_to_core.erase(old_runtime->second);
    }
    table.runtime_to_core[runtime_pin_id] = pin;
    table.core_to_runtime[pin.id] = runtime_pin_id;
}

std::optional<PinHandle> DesignDB::core_pin_for_runtime_pin(std::string_view domain,
                                                            uint32_t runtime_pin_id) const {
    auto domain_it = runtime_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_pin_bindings_.end()) return std::nullopt;
    auto pin_it = domain_it->second.runtime_to_core.find(runtime_pin_id);
    if (pin_it == domain_it->second.runtime_to_core.end()) return std::nullopt;
    return pin_it->second;
}

std::optional<uint32_t> DesignDB::runtime_pin_for_core_pin(std::string_view domain,
                                                           PinHandle pin) const {
    if (!valid(pin)) return std::nullopt;
    auto domain_it = runtime_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_pin_bindings_.end()) return std::nullopt;
    auto pin_it = domain_it->second.core_to_runtime.find(pin.id);
    if (pin_it == domain_it->second.core_to_runtime.end()) return std::nullopt;
    return pin_it->second;
}

size_t DesignDB::runtime_pin_binding_count(std::string_view domain) const {
    auto domain_it = runtime_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_pin_bindings_.end()) return 0;
    return domain_it->second.runtime_to_core.size();
}

std::vector<RuntimePinBinding> DesignDB::runtime_pin_bindings(
    std::string_view domain) const {
    std::vector<RuntimePinBinding> result;
    auto domain_it = runtime_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_pin_bindings_.end()) return result;
    result.reserve(domain_it->second.runtime_to_core.size());
    for (const auto& [runtime_pin_id, pin] :
         domain_it->second.runtime_to_core) {
        result.push_back({runtime_pin_id, pin});
    }
    return result;
}

void DesignDB::clear_runtime_pin_aliases(std::string_view domain) {
    runtime_pin_aliases_.erase(std::string(domain));
}

void DesignDB::bind_runtime_pin_alias(std::string_view domain,
                                      std::string_view alias,
                                      const std::vector<uint32_t>& runtime_pin_ids) {
    if (alias.empty()) return;
    runtime_pin_aliases_[std::string(domain)][std::string(alias)] = runtime_pin_ids;
}

std::vector<uint32_t> DesignDB::runtime_pins_for_alias(std::string_view domain,
                                                       std::string_view alias) const {
    auto domain_it = runtime_pin_aliases_.find(std::string(domain));
    if (domain_it == runtime_pin_aliases_.end()) return {};
    auto alias_it = domain_it->second.find(std::string(alias));
    if (alias_it == domain_it->second.end()) return {};
    return alias_it->second;
}

size_t DesignDB::runtime_pin_alias_count(std::string_view domain) const {
    auto domain_it = runtime_pin_aliases_.find(std::string(domain));
    if (domain_it == runtime_pin_aliases_.end()) return 0;
    return domain_it->second.size();
}

std::vector<RuntimePinAlias> DesignDB::runtime_pin_aliases(
    std::string_view domain) const {
    std::vector<RuntimePinAlias> result;
    auto domain_it = runtime_pin_aliases_.find(std::string(domain));
    if (domain_it == runtime_pin_aliases_.end()) return result;
    result.reserve(domain_it->second.size());
    for (const auto& [alias, pins] : domain_it->second) {
        result.push_back({alias, pins});
    }
    return result;
}

void DesignDB::clear_runtime_node_bindings(std::string_view domain) {
    runtime_node_bindings_.erase(std::string(domain));
}

void DesignDB::bind_runtime_node(std::string_view domain,
                                 uint64_t runtime_node_id,
                                 uint64_t canonical_node_id) {
    if (runtime_node_id == 0 || canonical_node_id == 0) return;
    auto& table = runtime_node_bindings_[std::string(domain)];
    if (auto old_canonical = table.runtime_to_canonical.find(runtime_node_id);
        old_canonical != table.runtime_to_canonical.end()) {
        table.canonical_to_runtime.erase(old_canonical->second);
    }
    if (auto old_runtime = table.canonical_to_runtime.find(canonical_node_id);
        old_runtime != table.canonical_to_runtime.end()) {
        table.runtime_to_canonical.erase(old_runtime->second);
    }
    table.runtime_to_canonical[runtime_node_id] = canonical_node_id;
    table.canonical_to_runtime[canonical_node_id] = runtime_node_id;
}

std::optional<uint64_t> DesignDB::canonical_node_for_runtime_node(
    std::string_view domain,
    uint64_t runtime_node_id) const {
    auto domain_it = runtime_node_bindings_.find(std::string(domain));
    if (domain_it == runtime_node_bindings_.end()) return std::nullopt;
    auto node_it = domain_it->second.runtime_to_canonical.find(runtime_node_id);
    if (node_it == domain_it->second.runtime_to_canonical.end()) return std::nullopt;
    return node_it->second;
}

std::optional<uint64_t> DesignDB::runtime_node_for_canonical_node(
    std::string_view domain,
    uint64_t canonical_node_id) const {
    auto domain_it = runtime_node_bindings_.find(std::string(domain));
    if (domain_it == runtime_node_bindings_.end()) return std::nullopt;
    auto node_it = domain_it->second.canonical_to_runtime.find(canonical_node_id);
    if (node_it == domain_it->second.canonical_to_runtime.end()) return std::nullopt;
    return node_it->second;
}

size_t DesignDB::runtime_node_binding_count(std::string_view domain) const {
    auto domain_it = runtime_node_bindings_.find(std::string(domain));
    if (domain_it == runtime_node_bindings_.end()) return 0;
    return domain_it->second.runtime_to_canonical.size();
}

std::vector<RuntimeNodeBinding> DesignDB::runtime_node_bindings(
    std::string_view domain) const {
    std::vector<RuntimeNodeBinding> result;
    auto domain_it = runtime_node_bindings_.find(std::string(domain));
    if (domain_it == runtime_node_bindings_.end()) return result;
    result.reserve(domain_it->second.runtime_to_canonical.size());
    for (const auto& [runtime_node_id, canonical_node_id] :
         domain_it->second.runtime_to_canonical) {
        result.push_back({runtime_node_id, canonical_node_id});
    }
    return result;
}

void DesignDB::clear_runtime_logic_pin_bindings(std::string_view domain) {
    runtime_logic_pin_bindings_.erase(std::string(domain));
}

void DesignDB::bind_runtime_logic_pin(std::string_view domain,
                                      uint64_t logic_node_id,
                                      std::string_view role,
                                      PinHandle pin) {
    if (logic_node_id == 0 || !valid(pin)) return;
    auto& table = runtime_logic_pin_bindings_[std::string(domain)];
    const std::string role_key(role);
    auto node_it = table.node_to_entries.find(logic_node_id);
    if (node_it != table.node_to_entries.end()) {
        for (size_t idx : node_it->second) {
            if (idx >= table.entries.size()) continue;
            const auto& entry = table.entries[idx];
            if (entry.role == role_key && entry.pin == pin) {
                return;
            }
        }
    }
    size_t idx = table.entries.size();
    table.entries.push_back({logic_node_id, role_key, pin});
    table.node_to_entries[logic_node_id].push_back(idx);
    table.pin_to_entries[pin.id].push_back(idx);
}

std::vector<PinHandle> DesignDB::core_pins_for_runtime_logic_node(
    std::string_view domain,
    uint64_t logic_node_id,
    std::string_view role) const {
    std::vector<PinHandle> result;
    auto domain_it = runtime_logic_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_logic_pin_bindings_.end()) return result;
    auto node_it = domain_it->second.node_to_entries.find(logic_node_id);
    if (node_it == domain_it->second.node_to_entries.end()) return result;
    const std::string role_key(role);
    for (size_t idx : node_it->second) {
        if (idx >= domain_it->second.entries.size()) continue;
        const auto& entry = domain_it->second.entries[idx];
        if (!role_key.empty() && entry.role != role_key) continue;
        result.push_back(entry.pin);
    }
    return result;
}

std::vector<uint64_t> DesignDB::runtime_logic_nodes_for_core_pin(
    std::string_view domain,
    PinHandle pin,
    std::string_view role) const {
    std::vector<uint64_t> result;
    if (!valid(pin)) return result;
    auto domain_it = runtime_logic_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_logic_pin_bindings_.end()) return result;
    auto pin_it = domain_it->second.pin_to_entries.find(pin.id);
    if (pin_it == domain_it->second.pin_to_entries.end()) return result;
    const std::string role_key(role);
    for (size_t idx : pin_it->second) {
        if (idx >= domain_it->second.entries.size()) continue;
        const auto& entry = domain_it->second.entries[idx];
        if (!role_key.empty() && entry.role != role_key) continue;
        result.push_back(entry.logic_node_id);
    }
    return result;
}

size_t DesignDB::runtime_logic_pin_binding_count(std::string_view domain) const {
    auto domain_it = runtime_logic_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_logic_pin_bindings_.end()) return 0;
    return domain_it->second.entries.size();
}

std::vector<RuntimeLogicPinBinding> DesignDB::runtime_logic_pin_bindings(
    std::string_view domain) const {
    auto domain_it = runtime_logic_pin_bindings_.find(std::string(domain));
    if (domain_it == runtime_logic_pin_bindings_.end()) return {};
    return domain_it->second.entries;
}

void DesignDB::clear_runtime_gate_mappings(std::string_view domain) {
    runtime_gate_mappings_.erase(std::string(domain));
}

void DesignDB::bind_runtime_gate_mapping(std::string_view domain,
                                         RuntimeGateMapping mapping) {
    if (mapping.logic_node_id == 0 || mapping.instance_name.empty()) return;

    auto& table = runtime_gate_mappings_[std::string(domain)];
    auto existing = table.node_to_entry.find(mapping.logic_node_id);
    if (existing != table.node_to_entry.end()) {
        size_t idx = existing->second;
        if (idx < table.entries.size()) {
            const std::string old_instance = table.entries[idx].instance_name;
            if (old_instance != mapping.instance_name) {
                auto inst_it = table.instance_to_entries.find(old_instance);
                if (inst_it != table.instance_to_entries.end()) {
                    auto& indices = inst_it->second;
                    indices.erase(std::remove(indices.begin(), indices.end(), idx), indices.end());
                    if (indices.empty()) table.instance_to_entries.erase(inst_it);
                }
                table.instance_to_entries[mapping.instance_name].push_back(idx);
            }
            table.entries[idx] = std::move(mapping);
            return;
        }
    }

    size_t idx = table.entries.size();
    uint64_t logic_node_id = mapping.logic_node_id;
    std::string instance_name = mapping.instance_name;
    table.entries.push_back(std::move(mapping));
    table.node_to_entry[logic_node_id] = idx;
    table.instance_to_entries[std::move(instance_name)].push_back(idx);
}

std::optional<RuntimeGateMapping> DesignDB::runtime_gate_mapping_for_logic_node(
    std::string_view domain,
    uint64_t logic_node_id) const {
    auto domain_it = runtime_gate_mappings_.find(std::string(domain));
    if (domain_it == runtime_gate_mappings_.end()) return std::nullopt;
    auto node_it = domain_it->second.node_to_entry.find(logic_node_id);
    if (node_it == domain_it->second.node_to_entry.end()) return std::nullopt;
    if (node_it->second >= domain_it->second.entries.size()) return std::nullopt;
    return domain_it->second.entries[node_it->second];
}

std::vector<RuntimeGateMapping> DesignDB::runtime_gate_mappings_for_instance(
    std::string_view domain,
    std::string_view instance_name) const {
    std::vector<RuntimeGateMapping> result;
    auto domain_it = runtime_gate_mappings_.find(std::string(domain));
    if (domain_it == runtime_gate_mappings_.end()) return result;
    auto inst_it = domain_it->second.instance_to_entries.find(std::string(instance_name));
    if (inst_it == domain_it->second.instance_to_entries.end()) return result;
    result.reserve(inst_it->second.size());
    for (size_t idx : inst_it->second) {
        if (idx >= domain_it->second.entries.size()) continue;
        result.push_back(domain_it->second.entries[idx]);
    }
    return result;
}

size_t DesignDB::runtime_gate_mapping_count(std::string_view domain) const {
    auto domain_it = runtime_gate_mappings_.find(std::string(domain));
    if (domain_it == runtime_gate_mappings_.end()) return 0;
    return domain_it->second.entries.size();
}

std::vector<RuntimeGateMapping> DesignDB::runtime_gate_mappings(
    std::string_view domain) const {
    auto domain_it = runtime_gate_mappings_.find(std::string(domain));
    if (domain_it == runtime_gate_mappings_.end()) return {};
    return domain_it->second.entries;
}

void DesignDB::clear() {
    info_ = {};
    ports_.clear();
    constraints_.clear();
    resolved_constraints_.clear();
    liberty_.clear();
    timing_.clear();
    parasitics_.clear();
    strings_.clear();
    gate_netlist_.reset();
    logic_views_.clear();
    runtime_pin_bindings_.clear();
    runtime_pin_aliases_.clear();
    runtime_node_bindings_.clear();
    runtime_logic_pin_bindings_.clear();
    runtime_gate_mappings_.clear();
}

} // namespace edacraft::core
