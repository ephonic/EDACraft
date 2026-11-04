#define DSIM_COMB_LEAF_ENABLED 1
#ifndef DSIM_REFERENCE_LEAF_BATCH
#define DSIM_COMB_LEAF_BATCH_ENABLED 1
#endif
#define DSIM_SCHEDULING_STATS 1
#include "dsim/runtime.hpp"
#include <array>
#include <cassert>
using namespace dsim;

int main() {
    uint64_t entries=0,events=0;unsigned states=0;
    for(unsigned cut=0;cut<96;++cut) {
        Sim s;int input=s.signal(8,false);s.set(input,V(0));
        std::array<int,3> output{},process{};
        for(int& id:output)id=s.signal(8,true);
        auto body=[&](int member){s.arm_wait(member);s.set(output[member],binary_op<Binary::Add>(s.get(input),V(member+1),8));};
        for(int member=0;member<3;++member)process[member]=s.process([&,member,pc=0]() mutable {
            if(pc==0&&s.begin_comb_leaf()){body(member);return;}
            for(;;){s.step();switch(pc){
            case 0:s.arm_wait(member);pc=1;continue;
            case 1:s.set(output[member],binary_op<Binary::Add>(s.get(input),V(member+1),8));pc=2;continue;
            case 2:pc=0;return;
            default:assert(false);
            }}
        });
        int monitor=-1;
        monitor=s.process([&]{
            s.print("OBS %h %h %h",{s.get(output[0]),s.get(output[1]),s.get(output[2])});
            s.wait(monitor,{{output[0],0},{output[1],0},{output[2],0}});
        });
        // An unrelated compiled handler must also split the FIFO prefix.
        auto foreign_state=std::make_shared<unsigned>(0);auto foreign=s.compiled_context(foreign_state);
        auto foreign_handler=s.compiled_handler(foreign,[](Sim& sim,void* value,uint32_t payload){
            assert(payload==81);++*static_cast<unsigned*>(value);sim.print("FOREIGN",{});
        });
        int boundary=s.compiled_process(foreign_handler,81);
#ifdef DSIM_COMB_LEAF_BATCH_ENABLED
        auto handler=std::make_shared<uint32_t>();auto context=s.compiled_context(handler);
        *handler=s.compiled_handler(context,[](Sim& sim,void* value,uint32_t payload){
            sim.compiled_leaf_batch(*static_cast<uint32_t*>(value),payload,[&](uint32_t member){
                sim.arm_wait(int(member));
                // This model registers input 0 and outputs 1..3.
                sim.set(int(member)+1,binary_op<Binary::Add>(sim.get(0),V(member+1),8));
            });
        });
        for(int p:process)s.bind_comb_leaf(p,*handler);
#endif
        for(int member=0;member<3;++member)s.add_wait_site(process[member],{{input,0}});
        s.enqueue(process[0]);s.enqueue(process[1]);s.enqueue(monitor);s.enqueue(boundary);s.enqueue(process[2]);
        const auto state=[&](const char* stage) {
            std::cout<<"STATE "<<cut<<" "<<stage<<" "<<s.executed_steps();
            for(const auto& signal:s.signals){std::cout<<" ";for(int bit=0;bit<signal.value.w;++bit)std::cout<<signal.value.bit(bit);}
            for(const auto& p:s.processes)std::cout<<" "<<p.queued<<p.waiting<<":"<<p.generation<<":"<<p.last_wait_site;
            std::cout<<" FOREIGN_COUNT "<<*foreign_state<<"\n";++states;
        };
        s.limit=cut;
        try{s.run_until(0);}catch(const std::runtime_error& e){assert(std::string(e.what()).find("execution budget exhausted")!=std::string::npos);}
        state("interrupted");auto cp=s.checkpoint();
        for(int mode=0;mode<3;++mode) {
            s.restore(cp);s.limit=10000;s.set(input,V(17));
            if(mode==0)s.run_until(0);
            else assert(s.predict_until(0,[](Sim&){},[mode](const Sim&){return mode==1;},[](Sim&){})==(mode==1));
            state("resumed");
            for(V value:{V::x(8),V::z(8),V(19)}){s.set(input,value);s.run_until(0);state("changed");}
#ifdef DSIM_COMB_LEAF_BATCH_ENABLED
            entries+=s.comb_leaf_batch_entries;events+=s.comb_leaf_batch_events;
#endif
        }
    }
#ifdef DSIM_COMB_LEAF_BATCH_ENABLED
    assert(entries>0&&events>entries);
#endif
    std::cout<<"PASS "<<states<<" FIFO, budget, checkpoint and prediction states\n";
}
