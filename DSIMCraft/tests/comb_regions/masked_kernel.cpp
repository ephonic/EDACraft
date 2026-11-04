#ifndef DSIM_REFERENCE_COMB_REGIONS
#define DSIM_COMB_REGION_ENABLED 1
#define DSIM_MASKED_COMB_REGION_ENABLED 1
#endif
#define DSIM_SCHEDULING_STATS 1
#include "dsim/runtime.hpp"
#include <array>
#include <cassert>
using namespace dsim;
#ifdef DSIM_MASKED_COMB_REGION_ENABLED
// Budget continuation adds a resume flag after the packed mask fields.
static_assert(sizeof(Ready)==12,"masked work and budget continuation must fit three words");
#endif

int main() {
    uint64_t batched=0,expanded=0;unsigned checks=0;
    for(unsigned cut=0;cut<64;++cut) {
        Sim s;int input=s.signal(8,false),other=s.signal(8,false);s.set(input,V(0));s.set(other,V(3));
        std::array<int,3> output{},process{};
        for(int& id:output)id=s.signal(8,true);
        const auto body=[&](int member){s.set(output[member],binary_op<Binary::Add>(member==0?s.get(input):member==1?s.get(other):binary_op<Binary::BitXor>(s.get(input),s.get(other),8),V(member+1),8));};
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
            if(member==0)s.add_wait_site(process[member],{{input,0}});
            else if(member==1)s.add_wait_site(process[member],{{other,0}});
            else s.add_wait_site(process[member],{{input,0},{other,0}});
#endif
        }
#ifdef DSIM_COMB_REGION_ENABLED
        s.add_masked_comb_region({process[0],process[1],process[2]},{{input,5},{other,6}},[&](uint64_t mask){
            for(int member=0;member<3;++member)if(mask&(UINT64_C(1)<<member)){s.arm_comb_member(0,member,process[member],member);body(member);}
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
            s.set(input,V(17));s.set(other,V(23));
            if(mode==0)s.run_until(0);
            else assert(s.predict_until(0,[](Sim&){},[mode](const Sim&){return mode==1;},[](Sim&){})==(mode==1));
            state("resumed");
            for(V value:{V::x(8),V::z(8),V(19)}){s.set(input,value);s.run_until(0);state("changed");s.set(other,value);s.run_until(0);state("other");}
            s.set(other,V(3));s.set(input,V(7));s.set(other,V(9));
            auto pending=s.checkpoint();s.run_until(0);state("overlap");
            s.restore(pending);
            assert(!s.predict_until(0,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
            state("pending-rollback");s.run_until(0);state("pending-replayed");
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
