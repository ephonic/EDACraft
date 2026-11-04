#include "gate_partition.hpp"
#include "gate_timing.hpp"
#include "../include/dsim/partition.hpp"
#include <sstream>
#include <unordered_map>

namespace dsim {
std::string gate_partition_report(const GateDesign& d,size_t count) {
    PartitionGraph graph;
    for(size_t n=0;n<d.constants.size();++n)graph.node(0);
    for(const auto& cell:d.instances) {
        const auto& model=d.models.at(cell.model);
        graph.node(std::max(size_t(1),model.wait_inputs.size())+(model.sequential_kind?4:0));
    }
    std::unordered_map<uint32_t,uint64_t> delays;
    if(d.timing)for(const auto& ic:d.timing->interconnects) {
        auto q=*std::min_element(ic.quanta.begin(),ic.quanta.end());
        if(ic.precision_fs&&q>UINT64_MAX/ic.precision_fs)throw std::runtime_error("partition INTERCONNECT delay overflow");
        if(!ic.precision_fs)throw std::runtime_error("partition INTERCONNECT precision is zero");
        if(!delays.emplace(ic.pin,q*ic.precision_fs).second)throw std::runtime_error("duplicate partition INTERCONNECT pin");
    }
    for(size_t i=0;i<d.instances.size();++i) {
        const auto& cell=d.instances[i];const auto& model=d.models.at(cell.model);
        auto vertex=d.constants.size()+i;
        for(size_t p=0;p<model.pins.size();++p) {
            auto flat=cell.first+p;auto net=d.pin_nets.at(flat);
            // Constants are immutable and may be replicated in every kernel.
            if(d.constants.at(net)>=0)continue;
            const auto& pin=model.pins[p];
            if(pin.output||pin.inout||pin.internal)graph.edge(vertex,size_t(net),0);
            else {auto delay=delays.find(uint32_t(flat));graph.edge(size_t(net),vertex,delay==delays.end()?0:delay->second);}
        }
    }
    auto plan=graph.plan(count);
    std::vector<size_t> cells(plan.loads.size(),0),nets(plan.loads.size(),0);
    for(size_t n=0;n<d.constants.size();++n)if(d.constants[n]<0)++nets[plan.owner[n]];
    for(size_t i=0;i<d.instances.size();++i)++cells[plan.owner[d.constants.size()+i]];
    std::ostringstream out;
    out<<"{\"schema\":\"dsim.gate-partition.v1\",\"scope\":\"gate-only\",\"execution\":\"serial\",\"requested_partitions\":"<<count
       <<",\"partitions\":"<<plan.loads.size()<<",\"zero_delay_domains\":"<<plan.domains<<",\"cut_edges\":"<<plan.cut_edges
       <<",\"lookahead_fs\":"<<plan.lookahead<<",\"constant_replication\":true,\"iopath_cuts\":false,\"loads\":[";
    for(size_t i=0;i<plan.loads.size();++i){if(i)out<<",";out<<plan.loads[i];}
    out<<"],\"instance_counts\":[";for(size_t i=0;i<cells.size();++i){if(i)out<<",";out<<cells[i];}
    out<<"],\"net_counts\":[";for(size_t i=0;i<nets.size();++i){if(i)out<<",";out<<nets[i];}
    out<<"],\"instance_partition\":[";
    for(size_t i=0;i<d.instances.size();++i){if(i)out<<",";out<<plan.owner[d.constants.size()+i];}
    out<<"]}";return out.str();
}
}
