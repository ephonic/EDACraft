#ifndef DSIM_REFERENCE_COMB_REGIONS
#define DSIM_COMB_REGION_ENABLED 1
#endif
#define DSIM_SCHEDULING_STATS 1
#include "dsim/runtime.hpp"
#include <array>
#include <cassert>
using namespace dsim;

int main() {
    uint64_t batched=0,expanded=0;unsigned checks=0;
    for(unsigned cut=0;cut<40;++cut) {
        Sim s;int input=s.signal(8,false);s.set(input,V(0));
        std::array<int,3> output{},process{};
        for(int& id:output)id=s.signal(8,true);
        const auto body=[&](int member){s.set(output[member],binary_op<Binary::Add>(s.get(input),V(member+1),8));};
        for(int member=0;member<3;++member)process[member]=s.process([&,member,pc=0]() mutable {
            for(;;){s.step();switch(pc){
            case 0:
#ifdef DSIM_COMB_REGION_ENABLED
                s.arm_comb_member(0,member,process[member],member);
#else
                s.arm_wait(member);
#endif
                pc=1;continue;
            case 1:body(member);pc=2;continue;
            case 2:pc=0;return;
            default:assert(false);
            }}
        });
        int monitor=-1;
        monitor=s.process([&]{
            s.print("OBS %h %h %h",{s.get(output[0]),s.get(output[1]),s.get(output[2])});
            s.wait(monitor,{{output[0],0},{output[1],0},{output[2],0}});
        });
        for(int member=0;member<3;++member) {
#ifdef DSIM_COMB_REGION_ENABLED
            s.add_wait_site(process[member],{});
#else
            s.add_wait_site(process[member],{{input,0}});
#endif
        }
#ifdef DSIM_COMB_REGION_ENABLED
        s.add_comb_region({process[0],process[1],process[2]},{input},[&]{
            for(int member=0;member<3;++member){s.arm_comb_member(0,member,process[member],member);body(member);}
        });
        s.enqueue_comb_region(0);
#else
        for(int id:process)s.enqueue(id);
#endif
        s.enqueue(monitor);
        const auto state=[&](const char* stage) {
            std::cout<<"STATE "<<cut<<" "<<stage<<" "<<s.executed_steps();
            for(const auto& signal:s.signals){std::cout<<" ";for(int bit=0;bit<signal.value.w;++bit)std::cout<<signal.value.bit(bit);}
            for(const auto& p:s.processes)std::cout<<" "<<p.queued<<p.waiting<<":"<<p.generation<<":"<<p.last_wait_site;
            std::cout<<"\n";++checks;
        };
        s.limit=cut;
        try{s.run_until(0);}catch(const std::runtime_error& e){assert(std::string(e.what()).find("execution budget exhausted")!=std::string::npos);}
        state("interrupted");
        auto cp=s.checkpoint();
        for(int mode=0;mode<3;++mode) {
            s.restore(cp);s.limit=10000;
            // Change an input with only part of a batch rearmed/queued.
            s.set(input,V(17));
            if(mode==0)s.run_until(0);
            else assert(s.predict_until(0,[](Sim&){},[mode](const Sim&){return mode==1;},[](Sim&){})==(mode==1));
            state("resumed");
            for(V value:{V::x(8),V::z(8),V(19)}){s.set(input,value);s.run_until(0);state("changed");}
            batched+=s.comb_region_runs;expanded+=s.comb_region_expansions;
        }
    }
#ifdef DSIM_COMB_REGION_ENABLED
    assert(batched>0&&expanded>0);
#else
    assert(batched==0&&expanded==0);
#endif
    std::cout<<"PASS "<<checks<<" interrupted checkpoint and prediction states\n";
}
