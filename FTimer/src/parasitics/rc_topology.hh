#pragma once

#include "timing_parasitics.hh"
#include <algorithm>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace te {

// Merge parallel edges and transparent series chains before selecting a CCS
// policy. Neither subdivision changes the passive network's electrical load.
// The original network, including every observation pin, stays in the solve.
struct RcResistanceSummary {
    double maximum=0.;
    double sum=0.;
};

inline RcResistanceSummary summarize_rc_resistance_ohms(const FullRcNetwork& rc) {
    const size_t n=rc.nodes.size();
    struct Segment { size_t node1,node2; double resistance; };
    auto merge_parallel=[](const std::vector<Segment>& input) {
        std::vector<Segment> output;
        std::vector<double> conductance;
        std::unordered_map<uint64_t,size_t> index;
        for(const auto& r:input) {
            if(r.node1==r.node2) continue;
            const auto a=std::min(r.node1,r.node2), b=std::max(r.node1,r.node2);
            const uint64_t key=(uint64_t(a)<<32)|uint64_t(b);
            const auto inserted=index.emplace(key,output.size());
            if(inserted.second) {
                output.push_back(r);
                conductance.push_back(r.resistance>0.?1./r.resistance:0.);
            } else {
                const size_t k=inserted.first->second;
                if(output[k].resistance==0. || r.resistance==0.) output[k].resistance=0.;
                else {
                    conductance[k]+=1./r.resistance;
                    output[k].resistance=1./conductance[k];
                }
            }
        }
        return output;
    };
    std::vector<std::vector<size_t>> adjacent(n);
    std::vector<bool> stored_charge(n,false);
    RcResistanceSummary fallback;
    std::vector<Segment> raw;
    for(const auto& r:rc.resistors) {
        fallback.maximum=std::max(fallback.maximum,double(r.resistance)*rc.res_scale);
        fallback.sum+=double(r.resistance)*rc.res_scale;
        if(r.node1>=n || r.node2>=n) return fallback;
        raw.push_back({r.node1,r.node2,double(r.resistance)*rc.res_scale});
    }
    const auto resistors=merge_parallel(raw);
    for(size_t k=0;k<resistors.size();++k) {
        const auto& r=resistors[k];
        adjacent[r.node1].push_back(k);adjacent[r.node2].push_back(k);
    }
    for(const auto& c:rc.capacitors) if(c.capacitance!=0.f) {
        if(c.node1<n) stored_charge[c.node1]=true;
        if(c.node2<n) stored_charge[c.node2]=true;
    }
    auto transparent=[&](size_t node) {
        return node!=rc.driver_node_id && !valid(rc.nodes[node].pin) &&
            rc.nodes[node].gnd_cap==0.f && !stored_charge[node] && adjacent[node].size()==2;
    };
    std::vector<bool> visited(resistors.size(),false);
    std::vector<Segment> chains;
    for(size_t start=0;start<n;++start) if(!transparent(start)) {
        for(size_t edge:adjacent[start]) {
            if(visited[edge]) continue;
            size_t node=start;double resistance=0.;
            do {
                visited[edge]=true;
                const auto& r=resistors[edge];
                resistance+=r.resistance;
                node=r.node1==node?r.node2:r.node1;
                if(!transparent(node)) break;
                edge=adjacent[node][0]==edge?adjacent[node][1]:adjacent[node][0];
            } while(!visited[edge]);
            // A passive loop returning to its only landmark has no load.
            if(node!=start) chains.push_back({start,node,resistance});
        }
    }
    RcResistanceSummary result;
    for(const auto& r:merge_parallel(chains)) {
        result.maximum=std::max(result.maximum,r.resistance);
        result.sum+=r.resistance;
    }
    return result;
}

inline double max_series_resistance_ohms(const FullRcNetwork& rc) {
    return summarize_rc_resistance_ohms(rc).maximum;
}

} // namespace te
