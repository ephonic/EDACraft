#include "dsim/runtime.hpp"
#include <array>
#include <cassert>
using namespace dsim;

static V bit(int v) {return v==2?V::x(1):v==3?V::z(1):V(v);}
struct Observers {
    bool fixed=true,rearm=true;
    std::array<int,4> sites{},calls{};
};
static void observe(Sim& s,void* raw,uint32_t index) {
    auto& state=*static_cast<Observers*>(raw);
    ++state.calls[index];
    if(state.rearm) {
        if(state.fixed)s.arm_fixed_wait(state.sites[index]);
        else s.arm_wait(state.sites[index]);
    }
}
static auto install(Sim& s,int input,bool fixed) {
    auto state=std::make_shared<Observers>();state->fixed=fixed;
    auto context=s.compiled_context(state),handler=s.compiled_handler(context,observe);
    const std::array<std::vector<std::pair<int,int>>,4> events={{{{input,0},{input,0}},{{input,1}},{{input,2}},{{input,1},{input,2}}}};
    for(int i=0;i<4;++i) {
        int p=s.compiled_process(handler,uint32_t(i));
        state->sites[i]=fixed?s.add_fixed_wait(p,events[i]):s.add_wait_site(p,events[i]);
        if(fixed)s.arm_fixed_wait(state->sites[i]);else s.arm_wait(state->sites[i]);
    }
    return state;
}
template<class F> static void rejects(F action) {
    bool rejected=false;try{action();}catch(const std::exception&){rejected=true;}assert(rejected);
}
int main() {
    static_assert(sizeof(Process)==24,"fixed sensitivity must fit process padding");
    static_assert(sizeof(Watch)==16,"watch layout must remain compact");
    // Independent Verilog edge table. X and Z may change without either edge.
    const bool pos[4][4]={{0,1,1,1},{0,0,0,0},{0,1,0,0},{0,1,0,0}};
    const bool neg[4][4]={{0,0,0,0},{1,0,1,1},{1,0,0,0},{1,0,0,0}};
    for(bool fixed:{false,true})for(int from=0;from<4;++from)for(int to=0;to<4;++to) {
        Sim s;int n=s.signal(1,false);s.set(n,bit(from));auto state=install(s,n,fixed);
        s.set(n,bit(to));s.run();
        assert((state->calls==std::array<int,4>{from!=to,pos[from][to],neg[from][to],pos[from][to]||neg[from][to]}));
    }
    // Two independently owned contexts observe one aliased net. Repeated
    // restoration must recover waiting/queued state and each context's counts.
    Sim s;int input=s.signal(1,true),alias=s.signal(1,true);
    s.connect_net(input,0,alias,0);s.drive(input,1,V(0));
    auto a=install(s,input,true),b=install(s,alias,true);
    int generic=-1,site=-1;auto generic_calls=std::make_shared<int>(0);s.register_state(generic_calls);
    generic=s.process([&]{++*generic_calls;s.arm_wait(site);});site=s.add_wait_site(generic,{{alias,0}});s.arm_wait(site);
    auto cp=s.checkpoint();
    auto check=[&] {
        assert((a->calls==std::array<int,4>{1,1,0,1})&&a->calls==b->calls);
        assert(*generic_calls==1&&s.get(alias).same(V(1)));
    };
    for(int i=0;i<3;++i) {if(i)s.restore(cp);s.drive(input,1,V(1));s.run_until(5);check();}
    s.restore(cp);
    bool accepted=s.predict_until(5,[&](Sim& probe){probe.drive(input,1,V::x(1));},
        [](const Sim&){return false;},[&](Sim& replay){replay.drive(input,1,V(1));});
    assert(!accepted&&s.prediction_stats.rollbacks==1);check();
    s.restore(cp);
    accepted=s.predict_until(5,[&](Sim& probe){probe.drive(input,1,V(1));},
        [](const Sim&){return true;},[](Sim&){assert(false);});assert(accepted);check();
    // A callback which does not rearm stays disarmed even with permanent slots.
    a->rearm=false;s.drive(input,1,V(0));s.run();auto counts=a->calls;
    s.drive(input,1,V(1));s.run();assert(a->calls[0]==counts[0]&&b->calls[0]>counts[0]);
    // Guards prevent permanent generation-zero watches from surviving a switch
    // to another list or to a timer; failures leave the fixed observer usable.
    Sim guard;int n=guard.signal(1,false);guard.set(n,V(0));auto model=install(guard,n,true);
    int p=model->sites[0];
    rejects([&]{guard.wait(p,{{n,0}});});rejects([&]{guard.add_wait_site(p,{{n,0}});});
    rejects([&]{guard.add_fixed_wait(p,{{n,0}});});rejects([&]{guard.delay(p,0);});rejects([&]{guard.delay(p,1);});
    auto context=guard.compiled_context(std::make_shared<Observers>());
    auto handler=guard.compiled_handler(context,observe);
    auto fresh=[&]{return guard.compiled_process(handler,0);};
    int q=fresh();guard.add_wait_site(q,{});rejects([&]{guard.add_fixed_wait(q,{});});rejects([&]{guard.arm_fixed_wait(q);});
    q=fresh();guard.wait(q,{});rejects([&]{guard.add_fixed_wait(q,{});});
    q=fresh();guard.delay(q,1);rejects([&]{guard.add_fixed_wait(q,{});});
    q=guard.process([]{});rejects([&]{guard.add_fixed_wait(q,{});});
    q=fresh();rejects([&]{guard.add_fixed_wait(q,{{-1,0}});});guard.add_fixed_wait(q,{});guard.arm_fixed_wait(q);
    // Do not run the guard's deliberately unscheduled model payloads. Drain
    // only the fixed observers awakened by this input change.
    guard.set(n,V(1));guard.run_until(0);assert(model->calls[0]==1);
    guard.freeze_topology();rejects([&]{guard.add_fixed_wait(q,{});});
    std::cout<<"PASS fixed/dynamic four-state edges, duplicate masks, alias contexts, disarm, reusable checkpoints, prediction commit/rollback, mode guards; Process=24 Watch=16\n";
}
