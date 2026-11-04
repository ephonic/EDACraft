// File -> strict gate binding -> model-precision path table -> compiled buffer
// -> delayed driver. A numeric integration probe, not a general SDF simulator.
#define DSIM_TIMING_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include "sdf_binding.hpp"
#include "sdf_delay.hpp"
#include <cassert>
using namespace dsim;
struct Buffer {int input,site;uint32_t channel;std::array<uint64_t,12> delays;int previous=2;};
static void evaluate(Sim& s,void* raw,uint32_t) {
    auto& m=*static_cast<Buffer*>(raw);s.arm_fixed_wait(m.site);auto value=s.get(m.input);
    auto transition=SdfPathDelays::transition(m.previous,value.bit(0));m.previous=value.bit(0);
    s.drive_after(m.channel,value,transition<0?0:m.delays[size_t(transition)]);
}
int main(int argc,char** argv) {
    try {
        if(argc!=5)throw std::runtime_error("usage: probe fixture-dir sdf model-timescale initial-comma-list");
        std::string fixture=argv[1];auto design=parse_gate(fixture+"/buffer.v","B",{fixture+"/buffer.lib"},{false,true,false});
        std::vector<std::string> initial;std::istringstream list(argv[4]);std::string item;
        while(std::getline(list,item,','))initial.push_back(item);
        SdfPathDelays table(parse_timescale(argv[3]),initial);SdfBindOptions options;options.numeric_preview=false;
        size_t entries=0;
        // This local table is discarded on any parse/bind/apply failure. No
        // simulator or output is constructed before the whole file succeeds.
        bind_sdf_file(argv[2],design,options,[&](const SdfBoundEntry& bound) {
            const auto& e=*bound.syntax;
            if(e.kind!="IOPATH"||e.ports.size()!=2||e.ports[0].name!="A"||e.ports[1].name!="Z"||
               !e.condition.empty()||e.conditional_else||!e.retain.empty()||!e.label.empty())
                throw std::runtime_error("probe supports only unconditional A-to-Z IOPATH");
            for(const auto& port:e.ports)if(!port.edge.empty()||!port.condition.empty())throw std::runtime_error("probe does not implement edge/conditional paths");
            std::vector<std::optional<std::string>> selected;
            for(const auto& v:e.values) {
                if(v.reject||v.xlimit)throw std::runtime_error("probe does not implement pulse thresholds");
                selected.push_back(v.delay.corner.at(bound.corner));
            }
            table.apply(e.mode,selected,bound.unit_fs);++entries;
        });
        if(!entries)throw std::runtime_error("probe requires at least one path update");
        Sim s;s.set_time_precision(1000);int input=s.signal(1,false),output=s.signal(1,true);
        auto state=std::make_shared<Buffer>(Buffer{input,0,s.delayed_driver(output,11,Sim::DelayPolicy::ReplacePending),table.ticks(1000),2});
        auto context=s.compiled_context(state);auto handler=s.compiled_handler(context,evaluate);
        int process=s.compiled_process(handler,0);state->site=s.add_fixed_wait(process,{{input,0}});s.enqueue(process);
        s.attach_wave(&output,+[](void* raw,uint64_t time,int signal,V value) {
            if(signal==*static_cast<int*>(raw)&&time>=1000)std::cout<<"TRACE t="<<time<<" z="<<format(value,'b')<<'\n';
        },+[](void*,uint64_t){});
        int values[]={0,1,3,2,0,2,1,2,3,0,3,1,0};
        for(int i=0;i<13;++i) {
            int value=values[i];int p=s.process([&,value]{s.set(input,value==3?V::z(1):value==2?V::x(1):V(value));});
            s.delay(p,1000+uint64_t(i)*100);
        }
        s.run_until(2300);
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
