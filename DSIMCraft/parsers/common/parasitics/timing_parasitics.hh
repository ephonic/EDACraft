#pragma once

#include "edacraft/core/parasitic_db.hpp"
#include "time_engine/types.hh"
#include <map>
#include <string>

namespace te {

using PiModel = edacraft::core::PiModel;
using LumpedCap = edacraft::core::LumpedCap;
using ParasiticNode = edacraft::core::BasicParasiticNode<PinId>;
using ParasiticResistor = edacraft::core::ParasiticResistor;
using ParasiticCapacitor = edacraft::core::ParasiticCapacitor;
using FullRcNetwork = edacraft::core::BasicFullRcNetwork<NetId, PinId>;
class TimingParasiticDB : public edacraft::core::BasicParasiticDB<NetId, PinId> {
public:
    struct NodeCoupling {
        NetId net1, net2;
        uint32_t node1, node2;
        float cap_pf;
    };
    void register_node(const std::string& name, NetId net, uint32_t node) {
        node_locations_[name] = {net, node};
    }
    // Preserve physical endpoints. Several capacitors between the same two
    // nets add; reciprocal SPEF listings of one capacitor count once.
    void add_node_coupling(std::string a, std::string b, NetId owner, NetId other,
                           uint32_t id, float cap_pf) {
        NetId first = owner, second = other;
        if (b < a) { std::swap(a,b); std::swap(first,second); }
        auto& pair = physical_couplings_[{a,b}];
        const float previous = pair.cap_pf;
        pair.first = first; pair.second = second;
        pair.entries[{owner.id,id}] = cap_pf;
        float side1 = 0, side2 = 0;
        for (const auto& entry : pair.entries)
            (entry.first.first == first.id ? side1 : side2) += entry.second;
        pair.cap_pf = std::max(side1, side2);
        add_coupling_cap(first,second,get_coupling_cap(first,second)+pair.cap_pf-previous);
    }
    std::vector<NodeCoupling> node_couplings() const {
        std::vector<NodeCoupling> result;
        for (const auto& item : physical_couplings_) {
            const auto a = node_locations_.find(item.first.first), b = node_locations_.find(item.first.second);
            result.push_back({item.second.first,item.second.second,
                a == node_locations_.end() ? UINT32_MAX : a->second.second,
                b == node_locations_.end() ? UINT32_MAX : b->second.second,item.second.cap_pf});
        }
        return result;
    }
    void set_includes_pin_caps(NetId net, bool value) { pin_caps_[net.id] = value; }
    bool includes_pin_caps(NetId net) const {
        auto it = pin_caps_.find(net.id);
        return it != pin_caps_.end() && it->second;
    }
    void clear() { edacraft::core::BasicParasiticDB<NetId, PinId>::clear(); pin_caps_.clear();
        physical_couplings_.clear(); node_locations_.clear(); }
private:
    struct PhysicalPair {
        NetId first, second;
        float cap_pf = 0;
        std::map<std::pair<uint32_t,uint32_t>,float> entries;
    };
    std::map<std::pair<std::string,std::string>,PhysicalPair> physical_couplings_;
    std::map<std::string,std::pair<NetId,uint32_t>> node_locations_;
    std::unordered_map<uint32_t, bool> pin_caps_;
};

} // namespace te
