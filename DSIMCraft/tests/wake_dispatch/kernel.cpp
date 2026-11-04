#define DSIM_SCHEDULING_STATS 1
#define DSIM_DELAYED_NBA_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
struct State { std::vector<std::string> trace; int count=0; };
int main() {
    uint64_t fused=0;unsigned checks=0;
    for(unsigned cut=0;cut<128;++cut) {
        Sim s;int q=s.signal(8,false);s.set(q,V(0,0,8));
        auto state=std::make_shared<State>();s.register_state(state);
        int first=-1,second=-1,watch=-1,inactive=-1;
        auto record=[&](const char* label){state->trace.push_back(std::string(label)+"@"+std::to_string(s.now)+":"+std::to_string(s.get(q).a));};
        inactive=s.process([&]{record("inactive");s.assign_nba(q,V(27,0,8));});
        watch=s.process([&]{record("watch");s.wait(watch,{{q,0}});});
        first=s.process([&,pc=0]() mutable {
            record("first");++state->count;
            s.set(q,V(++pc,0,8));
            if(pc<4)s.delay(first,pc==2?0:3);
            if(pc==3){s.enqueue(first);s.delay(inactive,0);}
        });
        second=s.process([&]{record("second");s.assign_nba(q,V(21,0,8));s.delay(inactive,0);});
        s.wait(watch,{{q,0}});
        // Duplicate timed wakes must deduplicate before either process runs.
        s.delay(first,2);s.delay(second,2);s.delay(first,2);
        s.delay(first,11);s.assign_nba_after(q,V(31,0,8),13);
        s.delay(second,0);s.enqueue(second); // already queued on the #0 wake
        auto emit=[&](const char* stage) {
            std::cout<<"STATE "<<cut<<" "<<stage<<" "<<s.now<<" "<<s.executed_steps()<<" "<<s.get(q).a<<" "<<s.get(q).b<<" "<<state->count;
            for(const auto& p:s.processes)std::cout<<" "<<p.queued<<p.waiting<<":"<<p.generation<<":"<<p.last_wait_site;
            for(const auto& event:state->trace)std::cout<<" "<<event;
            std::cout<<"\n";++checks;
        };
        s.limit=cut;
        try{s.run_until(6);}catch(const std::runtime_error& e){assert(std::string(e.what()).find("execution budget exhausted")!=std::string::npos);}
        emit("interrupted");auto cp=s.checkpoint();
        for(int mode=0;mode<3;++mode) {
            s.restore(cp);s.limit=10000;
            if(mode==0)s.run_until(14);
            else assert(s.predict_until(14,[](Sim&){},[mode](const Sim&){return mode==1;},[](Sim&){})==(mode==1));
            assert(s.get(q).same(V(31,0,8)));emit("resumed");fused+=s.wake_dispatch_runs;
        }
    }
#ifndef DSIM_REFERENCE_WAKE_DISPATCH
    assert(fused>0);
#else
    assert(fused==0);
#endif
    std::cerr<<"FUSED "<<fused<<"\n";
    std::cout<<"PASS "<<checks<<" wake, budget, checkpoint and prediction states\n";
}
