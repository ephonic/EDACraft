#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "edacraft/core/object_table.hpp"
#include "edacraft/core/string_pool.hpp"
#include "time_engine/types.hh"

namespace te {

// ────────────────────────────────────────────────────────────
// Network data structures
// ────────────────────────────────────────────────────────────

struct NetData {
    uint32_t name; // StringId
    PinId driver = NULL_PIN;
    std::vector<PinId> loads;
    int8_t constant_value = -1; // -1 unknown, 0/1 static constant net
};

struct PinData {
    uint32_t name; // StringId
    InstanceId instance;
    PortDirection direction;
    NetId net;
    float load_cap = 0.0f;
    // Electrical reporting retains the late envelope; timing selects mm/rf.
    std::array<float, 2> load_cap_rf{{0.0f, 0.0f}};
    std::array<float, 2> load_cap_min_rf{{0.0f, 0.0f}};
    LibertyPinId liberty_pin = NULL_LIBERTY_PIN;
};

struct InstanceData {
    uint32_t name; // StringId
    CellId cell;
    InstanceId parent;
    std::vector<PinId> pins;
};

struct CellData {
    uint32_t name; // StringId
    std::vector<uint32_t> port_names; // StringId
    LibraryId liberty_library = NULL_LIBRARY;
    LibertyCellId liberty_cell = NULL_LIBERTY_CELL;
    bool is_combinational = true;
    bool is_sequential = false;
};

// ────────────────────────────────────────────────────────────
// Network: owns all network data
// ────────────────────────────────────────────────────────────
class Network {
public:
    Network() = default;
    explicit Network(const edacraft::core::StringPool& strings) : strings_(strings) {}
    explicit Network(edacraft::core::StringPool& strings) : external_strings_(&strings) {}

    // ── Construction ────────────────────────────────────────
    NetId create_net(std::string_view name);
    InstanceId create_instance(std::string_view name, CellId cell,
                               InstanceId parent = NULL_INSTANCE);
    PinId create_pin(std::string_view name, InstanceId inst,
                     PortDirection dir);
    void connect_pin_to_net(PinId pin, NetId net);
    void set_net_constant(NetId net, int value);
    CellId create_cell(std::string_view name);
    void set_liberty_cell(CellId cell, LibraryId lib, LibertyCellId lib_cell);
    void add_port(CellId cell, std::string_view port_name);
    void set_load_capacitance(PinId pin, float cap);
    void set_load_capacitance(PinId pin, Transition rf, float cap) {
        set_load_capacitance(pin, MinMax::Min, rf, cap);
        set_load_capacitance(pin, MinMax::Max, rf, cap);
    }
    float load_capacitance(PinId pin, MinMax mm, Transition rf) const {
        const auto& data = pins_[pin.id];
        return (mm == MinMax::Min ? data.load_cap_min_rf : data.load_cap_rf)[static_cast<unsigned>(rf)];
    }
    void set_load_capacitance(PinId pin, MinMax mm, Transition rf, float cap) {
        auto constrained = unconstrained_load_caps_.find(pin.id);
        if (constrained != unconstrained_load_caps_.end()) {
            constrained->second[mm_rf_index(mm, rf)] = cap;
            return;
        }
        auto& caps = mm == MinMax::Min ? pins_[pin.id].load_cap_min_rf : pins_[pin.id].load_cap_rf;
        caps[static_cast<unsigned>(rf)] = cap;
        pins_[pin.id].load_cap = std::max(pins_[pin.id].load_cap_rf[0],
                                         pins_[pin.id].load_cap_rf[1]);
    }
    void set_load_override(PinId pin, float cap) {
        if (!valid(pin) || pin.id >= pins_.size()) return;
        auto& data = pins_[pin.id];
        unconstrained_load_caps_.emplace(pin.id, std::array<float,4>{{
            data.load_cap_min_rf[0], data.load_cap_min_rf[1], data.load_cap_rf[0], data.load_cap_rf[1]}});
        data.load_cap = cap;
        data.load_cap_rf = {{cap, cap}};
        data.load_cap_min_rf = {{cap, cap}};
    }
    bool has_load_override(PinId pin) const {
        return unconstrained_load_caps_.find(pin.id) != unconstrained_load_caps_.end();
    }
    void clear_load_overrides() {
        for (const auto& entry : unconstrained_load_caps_) {
            auto& data = pins_[entry.first];
            data.load_cap_min_rf = {{entry.second[0], entry.second[1]}};
            data.load_cap_rf = {{entry.second[2], entry.second[3]}};
            data.load_cap = std::max(entry.second[2], entry.second[3]);
        }
        unconstrained_load_caps_.clear();
    }
    void set_liberty_pin(PinId pin, LibertyPinId lib_pin);
    void set_pin_direction(PinId pin, PortDirection dir);
    void set_parent(InstanceId inst, InstanceId parent);
    void add_pin(InstanceId inst, PinId pin);

    // ── Query ───────────────────────────────────────────────
    std::string_view net_name(NetId id) const;
    const NetData& net(NetId id) const;
    const PinData& pin(PinId id) const;
    const InstanceData& instance(InstanceId id) const;
    const CellData& cell(CellId id) const;
    std::string_view pin_name(PinId id) const;
    std::string_view instance_name(InstanceId id) const;
    std::string_view cell_name(CellId id) const;

    // ── Mutable access (for synthesis integration) ──────────
    InstanceData& instance(InstanceId id) { return instances_[id.id]; }
    CellData& cell(CellId id) { return cells_[id.id]; }
    void set_instance_cell(InstanceId inst, CellId cell) {
        instances_[inst.id].cell = cell;
    }

    // ── Lookup by name ─────────────────────────────────────
    std::optional<NetId> find_net(std::string_view name) const;
    std::optional<InstanceId> find_instance(std::string_view name) const;
    std::optional<PinId> find_pin(InstanceId inst, std::string_view port_name) const;
    std::optional<CellId> find_cell(std::string_view name) const;

    // ── Iteration ──────────────────────────────────────────
    size_t net_count() const { return nets_.size(); }
    size_t pin_count() const { return pins_.size(); }
    size_t instance_count() const { return instances_.size(); }
    size_t cell_count() const { return cells_.size(); }

    // Rebuild net driver/load relationships after pin directions change
    void rebuild_net_connections();

    // Collapse electrical wire aliases after parsing, before graph/parasitic
    // construction. Keep all names queryable and all real pins; no buffer
    // or duplicated physical net is introduced by a scalar wire assignment.
    void merge_wire_aliases(const std::vector<std::pair<NetId,NetId>>& aliases) {
        if(aliases.empty())return;
        std::vector<uint32_t> parent(nets_.size());
        for(uint32_t k=0;k<parent.size();++k)parent[k]=k;
        auto root=[&](uint32_t k) {
            while(parent[k]!=k) {parent[k]=parent[parent[k]];k=parent[k];}
            return k;
        };
        for(const auto& pair:aliases) {
            if(!valid(pair.first) || !valid(pair.second) ||
                pair.first.id>=parent.size() || pair.second.id>=parent.size())
                throw std::runtime_error("Invalid Verilog wire alias");
            const auto a=root(pair.first.id),b=root(pair.second.id);
            if(a!=b)parent[a]=b;
        }
        std::vector<PinId> drivers(nets_.size(),NULL_PIN);
        std::vector<int8_t> constants(nets_.size(),-1);
        // Validate before changing the network. A wire alias must not hide
        // conflicting physical drivers or contradictory constant values.
        for(uint32_t k=0;k<nets_.size();++k) {
            const auto r=root(k);const auto& n=nets_[k];
            if(valid(n.driver)) {
                if(valid(drivers[r]) && drivers[r]!=n.driver)
                    throw std::runtime_error("Verilog wire alias joins multiple drivers");
                drivers[r]=n.driver;
            }
            if(n.constant_value>=0) {
                if(constants[r]>=0 && constants[r]!=n.constant_value)
                    throw std::runtime_error("Verilog wire alias joins conflicting constants");
                constants[r]=n.constant_value;
            }
        }
        for(auto& entry:net_name_map_)entry.second=root(entry.second);
        for(uint32_t k=0;k<nets_.size();++k) {
            nets_[k].driver=NULL_PIN;nets_[k].loads.clear();
            nets_[k].constant_value=parent[k]==k?constants[k]:-1;
        }
        for(uint32_t k=0;k<pins_.size();++k) {
            auto& p=pins_[k];if(!valid(p.net))continue;
            p.net=NetId{root(p.net.id)};auto& n=nets_[p.net.id];
            if(p.direction==PortDirection::Output || p.direction==PortDirection::Inout)n.driver=PinId{k};
            else n.loads.push_back(PinId{k});
        }
    }

    // ── String pool ────────────────────────────────────────
    uint32_t intern_string(std::string_view s);
    std::string_view str(uint32_t id) const;
    edacraft::core::StringPool& string_pool() { return string_pool_ref(); }
    const edacraft::core::StringPool& string_pool() const { return string_pool_ref(); }

private:
    edacraft::core::StringPool& string_pool_ref() {
        return external_strings_ ? *external_strings_ : strings_;
    }
    const edacraft::core::StringPool& string_pool_ref() const {
        return external_strings_ ? *external_strings_ : strings_;
    }

    edacraft::core::StringPool* external_strings_ = nullptr;
    edacraft::core::StringPool strings_;
    edacraft::core::ObjectTable<NetData> nets_;
    edacraft::core::ObjectTable<PinData> pins_;
    // Only constrained pins need saved receiver caps. Liberty linking/refinement
    // updates these values so removing set_load restores the current cell model.
    std::unordered_map<uint32_t, std::array<float, 4>> unconstrained_load_caps_;
    edacraft::core::ObjectTable<InstanceData> instances_;
    edacraft::core::ObjectTable<CellData> cells_;

    // Name → ID maps (built incrementally)
    // Names already live in the shared StringPool. Index by StringId so the
    // timing network does not retain another copy of every generated name.
    std::unordered_map<uint32_t, uint32_t> net_name_map_;
    std::unordered_map<uint32_t, uint32_t> inst_name_map_;
    std::unordered_map<uint32_t, uint32_t> cell_name_map_;
};

// ────────────────────────────────────────────────────────────
// Inline implementations
// ────────────────────────────────────────────────────────────
inline NetId Network::create_net(std::string_view name) {
    uint32_t sid = intern_string(name);
    uint32_t id = nets_.emplace(sid);
    net_name_map_[sid] = id;
    return NetId{id};
}

inline CellId Network::create_cell(std::string_view name) {
    uint32_t sid = intern_string(name);
    uint32_t id = cells_.emplace(sid);
    cell_name_map_[sid] = id;
    return CellId{id};
}

inline void Network::set_liberty_cell(CellId cell, LibraryId lib, LibertyCellId lib_cell) {
    cells_[cell.id].liberty_library = lib;
    cells_[cell.id].liberty_cell = lib_cell;
}

inline void Network::add_port(CellId cell, std::string_view port_name) {
    cells_[cell.id].port_names.push_back(intern_string(port_name));
}

inline InstanceId Network::create_instance(std::string_view name, CellId cell,
                                           InstanceId parent) {
    uint32_t sid = intern_string(name);
    uint32_t id = instances_.emplace(sid, cell, parent);
    inst_name_map_[sid] = id;
    return InstanceId{id};
}

inline PinId Network::create_pin(std::string_view name, InstanceId inst,
                                 PortDirection dir) {
    uint32_t sid = intern_string(name);
    uint32_t id = pins_.emplace(sid, inst, dir, NULL_NET);
    return PinId{id};
}

inline void Network::connect_pin_to_net(PinId pin, NetId net) {
    auto& p = pins_[pin.id];
    // Disconnect from old net if already connected
    if (valid(p.net)) {
        auto& old_n = nets_[p.net.id];
        if (p.direction == PortDirection::Output || p.direction == PortDirection::Inout) {
            if (old_n.driver == pin) old_n.driver = NULL_PIN;
        } else {
            old_n.loads.erase(std::remove(old_n.loads.begin(), old_n.loads.end(), pin), old_n.loads.end());
        }
    }
    p.net = net;
    auto& n = nets_[net.id];
    if (p.direction == PortDirection::Output || p.direction == PortDirection::Inout) {
        n.driver = pin;
    } else {
        n.loads.push_back(pin);
    }
}

inline void Network::set_net_constant(NetId net, int value) {
    if (!valid(net) || net.id >= nets_.size()) return;
    nets_[net.id].constant_value = value ? 1 : 0;
}

inline void Network::set_load_capacitance(PinId pin, float cap) {
    set_load_capacitance(pin, Transition::Rise, cap);
    set_load_capacitance(pin, Transition::Fall, cap);
}

inline void Network::set_liberty_pin(PinId pin, LibertyPinId lib_pin) {
    pins_[pin.id].liberty_pin = lib_pin;
}

inline void Network::set_pin_direction(PinId pin, PortDirection dir) {
    pins_[pin.id].direction = dir;
}

inline void Network::set_parent(InstanceId inst, InstanceId parent) {
    instances_[inst.id].parent = parent;
}

inline void Network::add_pin(InstanceId inst, PinId pin) {
    instances_[inst.id].pins.push_back(pin);
}

inline std::string_view Network::net_name(NetId id) const {
    return string_pool_ref().view(nets_[id.id].name);
}

inline const NetData& Network::net(NetId id) const { return nets_[id.id]; }
inline const PinData& Network::pin(PinId id) const { return pins_[id.id]; }
inline const InstanceData& Network::instance(InstanceId id) const { return instances_[id.id]; }
inline const CellData& Network::cell(CellId id) const { return cells_[id.id]; }

inline std::string_view Network::pin_name(PinId id) const {
    return string_pool_ref().view(pins_[id.id].name);
}

inline std::string_view Network::instance_name(InstanceId id) const {
    return string_pool_ref().view(instances_[id.id].name);
}

inline std::string_view Network::cell_name(CellId id) const {
    return string_pool_ref().view(cells_[id.id].name);
}

inline std::optional<NetId> Network::find_net(std::string_view name) const {
    auto sid = string_pool_ref().find(name);
    if (!sid) return std::nullopt;
    auto it = net_name_map_.find(*sid);
    if (it == net_name_map_.end()) return std::nullopt;
    return NetId{it->second};
}

inline std::optional<InstanceId> Network::find_instance(std::string_view name) const {
    auto sid = string_pool_ref().find(name);
    if (!sid) return std::nullopt;
    auto it = inst_name_map_.find(*sid);
    if (it == inst_name_map_.end()) return std::nullopt;
    return InstanceId{it->second};
}

inline std::optional<PinId> Network::find_pin(InstanceId inst, std::string_view port_name) const {
    const auto& inst_data = instance(inst);
    for (auto pid : inst_data.pins) {
        if (pin_name(pid) == port_name) return PinId{pid.id};
    }
    return std::nullopt;
}

inline std::optional<CellId> Network::find_cell(std::string_view name) const {
    auto sid = string_pool_ref().find(name);
    if (!sid) return std::nullopt;
    auto it = cell_name_map_.find(*sid);
    if (it == cell_name_map_.end()) return std::nullopt;
    return CellId{it->second};
}

inline uint32_t Network::intern_string(std::string_view s) {
    return string_pool_ref().intern(s);
}

inline std::string_view Network::str(uint32_t id) const {
    return string_pool_ref().view(id);
}

inline void Network::rebuild_net_connections() {
    for (uint32_t nid = 0; nid < nets_.size(); ++nid) {
        nets_[nid].driver = NULL_PIN;
        nets_[nid].loads.clear();
    }
    for (uint32_t pid = 0; pid < pins_.size(); ++pid) {
        PinId pin{pid};
        const auto& p = pins_[pid];
        if (!valid(p.net)) continue;
        auto& n = nets_[p.net.id];

        if (p.direction == PortDirection::Output || p.direction == PortDirection::Inout) {
            // Detect multiple drivers (short circuit) — last one wins but warn
            if (valid(n.driver) && n.driver != pin) {
                // Multiple output/inout pins on same net — short circuit
                // Keep the first driver; subsequent drivers treated as loads
                n.loads.push_back(pin);
            } else {
                n.driver = pin;
            }
        } else {
            n.loads.push_back(pin);
        }
    }
}

} // namespace te
