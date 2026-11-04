#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>
#include <numeric>
#include <queue>
#include <stdexcept>
#include <vector>

namespace dsim {
// Nodes own state. A zero-delay dependency forces both endpoints into the
// same sequential domain; positive delays may cross worker boundaries.
class PartitionGraph {
public:
    struct Edge {size_t from,to;uint64_t delay;};
    struct Plan {
        std::vector<size_t> owner;
        std::vector<uint64_t> loads;
        size_t domains=0,cut_edges=0;
        uint64_t lookahead=0; // 0 means no cross-partition channels
    };
private:
    std::vector<uint64_t> weights;
    std::vector<Edge> links;
public:
    size_t node(uint64_t weight=1) {weights.push_back(weight);return weights.size()-1;}
    size_t edge(size_t from,size_t to,uint64_t delay) {
        if(from>=weights.size()||to>=weights.size())throw std::runtime_error("partition edge endpoint out of range");
        links.push_back({from,to,delay});return links.size()-1;
    }
    size_t size() const {return weights.size();}
    const std::vector<Edge>& edges() const {return links;}
    Plan plan(size_t count) const {
        if(!count)throw std::runtime_error("partition count must be positive");
        Plan result;result.owner.resize(size());
        if(weights.empty())return result;
        std::vector<size_t> parent(size()),rank(size(),0);
        std::iota(parent.begin(),parent.end(),size_t(0));
        auto root=[&](size_t n){while(parent[n]!=n){parent[n]=parent[parent[n]];n=parent[n];}return n;};
        for(const auto& e:links)if(!e.delay) {
            auto a=root(e.from),b=root(e.to);if(a==b)continue;
            if(rank[a]<rank[b])std::swap(a,b);
            parent[b]=a;if(rank[a]==rank[b])++rank[a];
        }
        std::vector<uint64_t> load(size(),0);
        for(size_t n=0;n<size();++n) {
            auto r=root(n);parent[n]=r;
            if(weights[n]>UINT64_MAX-load[r])throw std::runtime_error("partition load overflow");
            load[r]+=weights[n];
        }
        std::vector<size_t> domains;
        for(size_t n=0;n<size();++n)if(parent[n]==n){++result.domains;if(load[n])domains.push_back(n);}
        // Deterministic largest-domain-first scheduling; zero-weight topology
        // vertices do not allocate otherwise idle workers.
        std::sort(domains.begin(),domains.end(),[&](size_t a,size_t b){return load[a]!=load[b]?load[a]>load[b]:a<b;});
        count=std::min(count,std::max(size_t(1),domains.size()));
        result.loads.resize(count,0);
        using Bin=std::pair<uint64_t,size_t>;
        std::priority_queue<Bin,std::vector<Bin>,std::greater<Bin>> bins;
        for(size_t i=0;i<count;++i)bins.push({0,i});
        std::vector<size_t> assignment(size(),0);
        for(auto domain:domains) {
            auto bin=bins.top();bins.pop();
            if(load[domain]>UINT64_MAX-bin.first)throw std::runtime_error("partition load overflow");
            assignment[domain]=bin.second;bin.first+=load[domain];result.loads[bin.second]=bin.first;bins.push(bin);
        }
        for(size_t n=0;n<size();++n)result.owner[n]=assignment[parent[n]];
        for(const auto& e:links)if(result.owner[e.from]!=result.owner[e.to]) {
            if(!e.delay)throw std::logic_error("zero-delay partition cut");
            ++result.cut_edges;result.lookahead=result.lookahead?std::min(result.lookahead,e.delay):e.delay;
        }
        return result;
    }
};
}
