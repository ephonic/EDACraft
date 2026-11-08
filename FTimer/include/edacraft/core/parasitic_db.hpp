#ifndef EDACRAFT_CORE_PARASITIC_DB_HPP
#define EDACRAFT_CORE_PARASITIC_DB_HPP

#include "edacraft/core/ids.hpp"

#include <cstdint>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <utility>
#include <vector>

namespace edacraft::core {

// Reduced C2-Rpi-C1 wire model. Capacitance values are stored in the native
// extraction units; cap_scale converts raw capacitance to farads.
struct PiModel {
    float c1 = 0.0f;
    float rpi = 0.0f;
    float c2 = 0.0f;
    float cap_scale = 1e-15f;
};

struct LumpedCap {
    float capacitance = 0.0f;
};

template <typename PinHandleT>
struct BasicParasiticNode {
    uint32_t id = 0;
    PinHandleT pin{UINT32_MAX};
    float gnd_cap = 0.0f;
};

struct ParasiticResistor {
    uint32_t id = 0;
    uint32_t node1 = UINT32_MAX;
    uint32_t node2 = UINT32_MAX;
    float resistance = 0.0f;
};

struct ParasiticCapacitor {
    uint32_t id = 0;
    uint32_t node1 = UINT32_MAX;
    uint32_t node2 = UINT32_MAX; // UINT32_MAX = ground
    float capacitance = 0.0f;
};

template <typename NetHandleT, typename PinHandleT>
struct BasicFullRcNetwork {
    NetHandleT net{UINT32_MAX};
    uint32_t driver_node_id = UINT32_MAX;
    std::vector<BasicParasiticNode<PinHandleT>> nodes;
    std::vector<ParasiticResistor> resistors;
    std::vector<ParasiticCapacitor> capacitors;
    float time_scale = 1.0f;
    float res_scale = 1.0f;
    float cap_scale = 1.0f;
};

template <typename NetHandleT, typename PinHandleT>
class BasicParasiticDB {
public:
    using NetHandleType = NetHandleT;
    using PinHandleType = PinHandleT;
    using Node = BasicParasiticNode<PinHandleT>;
    using FullRcNetwork = BasicFullRcNetwork<NetHandleT, PinHandleT>;

    void set_network(NetHandleT net, FullRcNetwork rc);
    const FullRcNetwork* get_network(NetHandleT net) const;
    bool has_network(NetHandleT net) const;
    void clear_net(NetHandleT net);

    void set_reduced(PinHandleT driver_pin, int mm_rf, PiModel model);
    std::optional<PiModel> get_reduced(PinHandleT driver_pin, int mm_rf) const;

    void set_lumped(PinHandleT pin, LumpedCap cap);
    std::optional<LumpedCap> get_lumped(PinHandleT pin) const;

    float total_load_cap(PinHandleT driver_pin,
                         const std::vector<PinHandleT>& load_pins) const;
    float elmore_delay(PinHandleT driver_pin, PinHandleT load_pin, int mm_rf) const;

    std::optional<std::unordered_map<uint32_t, float>> get_elmore_pin_delays(NetHandleT net) const;
    void cache_elmore(NetHandleT net, const std::unordered_map<uint32_t, float>& pin_delays);

    std::optional<std::unordered_map<uint32_t, float>> get_elmore_pin_impulses(NetHandleT net) const;
    void cache_elmore_impulse(NetHandleT net,
                              const std::unordered_map<uint32_t, float>& pin_impulses);

    void add_coupling_cap(NetHandleT net1, NetHandleT net2, float cap);
    float get_coupling_cap(NetHandleT net1, NetHandleT net2) const;
    float total_coupling_cap(NetHandleT victim) const;
    struct CouplingRecord {
        NetHandleT net1;
        NetHandleT net2;
        float capacitance = 0.0f;
    };
    std::vector<CouplingRecord> coupling_records() const;

    void clear();

private:
    static uint64_t reduced_key(PinHandleT pin, int mm_rf) {
        return (static_cast<uint64_t>(pin.id) << 2) | static_cast<uint64_t>(mm_rf);
    }

    static uint64_t coupling_key(NetHandleT a, NetHandleT b) {
        return (a.id < b.id)
            ? ((static_cast<uint64_t>(a.id) << 32) | b.id)
            : ((static_cast<uint64_t>(b.id) << 32) | a.id);
    }

    std::unordered_map<uint32_t, FullRcNetwork> networks_;
    std::unordered_map<uint64_t, PiModel> reduced_;
    std::unordered_map<uint32_t, LumpedCap> lumped_;
    mutable std::unordered_map<uint32_t, std::unordered_map<uint32_t, float>> elmore_cache_;
    mutable std::unordered_map<uint32_t, std::unordered_map<uint32_t, float>> elmore_impulse_cache_;
    mutable std::mutex elmore_mutex_;
    std::unordered_map<uint64_t, float> coupling_caps_;
};

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::set_network(
    NetHandleT net, FullRcNetwork rc) {
    rc.net = net;
    networks_[net.id] = std::move(rc);
}

template <typename NetHandleT, typename PinHandleT>
inline const typename BasicParasiticDB<NetHandleT, PinHandleT>::FullRcNetwork*
BasicParasiticDB<NetHandleT, PinHandleT>::get_network(NetHandleT net) const {
    auto it = networks_.find(net.id);
    return it != networks_.end() ? &it->second : nullptr;
}

template <typename NetHandleT, typename PinHandleT>
inline bool BasicParasiticDB<NetHandleT, PinHandleT>::has_network(NetHandleT net) const {
    return networks_.count(net.id) > 0;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::clear_net(NetHandleT net) {
    networks_.erase(net.id);
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::set_reduced(
    PinHandleT driver_pin, int mm_rf, PiModel model) {
    reduced_[reduced_key(driver_pin, mm_rf)] = model;
}

template <typename NetHandleT, typename PinHandleT>
inline std::optional<PiModel> BasicParasiticDB<NetHandleT, PinHandleT>::get_reduced(
    PinHandleT driver_pin, int mm_rf) const {
    auto it = reduced_.find(reduced_key(driver_pin, mm_rf));
    if (it != reduced_.end()) return it->second;
    return std::nullopt;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::set_lumped(
    PinHandleT pin, LumpedCap cap) {
    lumped_[pin.id] = cap;
}

template <typename NetHandleT, typename PinHandleT>
inline std::optional<LumpedCap> BasicParasiticDB<NetHandleT, PinHandleT>::get_lumped(
    PinHandleT pin) const {
    auto it = lumped_.find(pin.id);
    if (it != lumped_.end()) return it->second;
    return std::nullopt;
}

template <typename NetHandleT, typename PinHandleT>
inline float BasicParasiticDB<NetHandleT, PinHandleT>::total_load_cap(
    PinHandleT driver_pin, const std::vector<PinHandleT>& load_pins) const {
    (void)driver_pin;
    float total = 0.0f;
    for (auto pin : load_pins) {
        if (auto cap = get_lumped(pin)) {
            total += cap->capacitance;
        }
    }
    return total;
}

template <typename NetHandleT, typename PinHandleT>
inline float BasicParasiticDB<NetHandleT, PinHandleT>::elmore_delay(
    PinHandleT driver_pin, PinHandleT load_pin, int mm_rf) const {
    (void)load_pin;
    if (auto pi = get_reduced(driver_pin, mm_rf)) {
        return pi->rpi * pi->c1;
    }
    if (get_lumped(driver_pin)) {
        return 0.0f;
    }
    return 0.0f;
}

template <typename NetHandleT, typename PinHandleT>
inline std::optional<std::unordered_map<uint32_t, float>>
BasicParasiticDB<NetHandleT, PinHandleT>::get_elmore_pin_delays(NetHandleT net) const {
    std::lock_guard<std::mutex> lock(elmore_mutex_);
    auto it = elmore_cache_.find(net.id);
    if (it != elmore_cache_.end()) return it->second;
    return std::nullopt;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::cache_elmore(
    NetHandleT net, const std::unordered_map<uint32_t, float>& pin_delays) {
    std::lock_guard<std::mutex> lock(elmore_mutex_);
    elmore_cache_[net.id] = pin_delays;
}

template <typename NetHandleT, typename PinHandleT>
inline std::optional<std::unordered_map<uint32_t, float>>
BasicParasiticDB<NetHandleT, PinHandleT>::get_elmore_pin_impulses(NetHandleT net) const {
    std::lock_guard<std::mutex> lock(elmore_mutex_);
    auto it = elmore_impulse_cache_.find(net.id);
    if (it != elmore_impulse_cache_.end()) return it->second;
    return std::nullopt;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::cache_elmore_impulse(
    NetHandleT net, const std::unordered_map<uint32_t, float>& pin_impulses) {
    std::lock_guard<std::mutex> lock(elmore_mutex_);
    elmore_impulse_cache_[net.id] = pin_impulses;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::add_coupling_cap(
    NetHandleT net1, NetHandleT net2, float cap) {
    coupling_caps_[coupling_key(net1, net2)] = cap;
}

template <typename NetHandleT, typename PinHandleT>
inline float BasicParasiticDB<NetHandleT, PinHandleT>::get_coupling_cap(
    NetHandleT net1, NetHandleT net2) const {
    auto it = coupling_caps_.find(coupling_key(net1, net2));
    return it != coupling_caps_.end() ? it->second : 0.0f;
}

template <typename NetHandleT, typename PinHandleT>
inline float BasicParasiticDB<NetHandleT, PinHandleT>::total_coupling_cap(
    NetHandleT victim) const {
    float total = 0.0f;
    for (const auto& [key, cap] : coupling_caps_) {
        uint32_t a = static_cast<uint32_t>(key >> 32);
        uint32_t b = static_cast<uint32_t>(key);
        if (a == victim.id || b == victim.id) {
            total += cap;
        }
    }
    return total;
}

template <typename NetHandleT, typename PinHandleT>
inline std::vector<typename BasicParasiticDB<NetHandleT, PinHandleT>::CouplingRecord>
BasicParasiticDB<NetHandleT, PinHandleT>::coupling_records() const {
    std::vector<CouplingRecord> records;
    records.reserve(coupling_caps_.size());
    for (const auto& [key, cap] : coupling_caps_) {
        records.push_back({NetHandleT{static_cast<uint32_t>(key >> 32)},
                           NetHandleT{static_cast<uint32_t>(key)}, cap});
    }
    return records;
}

template <typename NetHandleT, typename PinHandleT>
inline void BasicParasiticDB<NetHandleT, PinHandleT>::clear() {
    std::lock_guard<std::mutex> lock(elmore_mutex_);
    networks_.clear();
    reduced_.clear();
    lumped_.clear();
    elmore_cache_.clear();
    elmore_impulse_cache_.clear();
    coupling_caps_.clear();
}

using ParasiticNode = BasicParasiticNode<PinHandle>;
using FullRcNetwork = BasicFullRcNetwork<NetHandle, PinHandle>;
using ParasiticDB = BasicParasiticDB<NetHandle, PinHandle>;

} // namespace edacraft::core

#endif // EDACRAFT_CORE_PARASITIC_DB_HPP
