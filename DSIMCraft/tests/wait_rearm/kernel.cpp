#include "dsim/runtime.hpp"
#include <cassert>
#include <iostream>
using namespace dsim;

int main() {
    static_assert(sizeof(Process)==24,"wait cache must fit process padding");
    static_assert(sizeof(Watch)==16,"watch layout must remain compact");
    Sim s;int a=s.signal(1,false),b=s.signal(1,false),out=s.signal(1,false);
    s.set(a,V(0));s.set(b,V(0));s.set(out,V(0));
    auto calls=std::make_shared<int>(0);s.register_state(calls);
    int p=s.process([&]{++*calls;s.assign_nba(out,V(*calls&1));});
    int wa=s.add_wait_site(p,{{a,0},{a,1},{a,0}}),wb=s.add_wait_site(p,{{b,0}});
    auto check=[&](int want){s.run();assert(*calls==want&&s.get(out).same(V(want&1)));};
    s.arm_wait(wa);s.set(b,V(1));check(0);s.set(a,V(1));check(1);
    // Repeated same-site rearm keeps every duplicate mask valid, but wake
    // coalescing still dispatches exactly once. Unarmed changes never wake.
    for(int i=0;i<20;++i){s.arm_wait(wa);s.set(a,V(i&1));check(i+2);s.set(b,V(i&1));check(i+2);}
    s.set(a,V(1));check(21);
    // Switching lists must retire the old list even when the old signal changes
    // in the same delta as the new one. A disarmed site's slots cannot reactivate.
    s.arm_wait(wb);s.set(a,V(0));check(21);s.set(b,V(0));s.set(b,V(1));check(22);
    s.arm_wait(wa);s.set(b,V(0));check(22);s.set(a,V(1));check(23);
    // Dynamic watches use separate slots and must be invalidated when returning
    // to the cached static list, including an empty dynamic wait.
    s.wait(p,{{b,0},{b,1}});s.set(a,V(0));check(23);s.set(b,V(1));check(24);
    s.arm_wait(wa);s.set(b,V(0));check(24);s.set(a,V(1));check(25);
    s.wait(p,{});s.set(a,V(0));check(25);s.arm_wait(wa);s.set(a,V(1));check(26);
    // Timers and inactive-region resumes are separate wake sources. Switching
    // to another static/dynamic list afterwards must not reuse stale generations.
    for(uint64_t dt:{uint64_t(0),uint64_t(3)}){
        int n=*calls;s.delay(p,dt);check(n+1);s.arm_wait(wb);
        s.set(a,V(0));check(n+1);s.set(b,V(1));check(n+2);
        s.arm_wait(wa);s.set(b,V(0));check(n+2);s.set(a,V(1));check(n+3);
    }
    // Checkpoints own both cache and subscription generations. Restore snapshots
    // from two different wait sites repeatedly, then exercise prediction replay.
    int n=*calls;s.arm_wait(wa);auto ca=s.checkpoint();s.arm_wait(wb);auto cb=s.checkpoint();
    for(int i=0;i<3;++i){
        s.restore(ca);s.arm_wait(wa);s.set(b,V(1));check(n);s.set(a,V(0));check(n+1);
        s.restore(cb);s.arm_wait(wb);s.set(a,V(0));check(n);s.set(b,V(1));check(n+1);
    }
    s.restore(ca);bool accept=s.predict_until(s.now+10,[](Sim&){},[](const Sim&){return false;},[&](Sim& replay){replay.set(a,V(0));});
    assert(!accept&&s.prediction_stats.rollbacks==1);check(n+1);
    s.restore(cb);accept=s.predict_until(s.now+10,[&](Sim& probe){probe.set(b,V(1));},[](const Sim&){return true;},[](Sim&){assert(false);});
    assert(accept&&s.prediction_stats.commits==1);check(n+1);
#ifdef DSIM_FORK_JOIN_ENABLED
    // A static join and wait fork each change the parent's generation. Returning
    // to the pre-fork sensitivity list must refresh its cached subscriptions.
    for(int kind:{1,3}) {
        Sim f;int signal=f.signal(1,false);f.set(signal,V(0));
        int parent=-1,child=-1,site=-1,group=-1,calls=0;
        parent=f.process([&]{
            ++calls;
            if(calls==1) {
                bool suspended=f.start_fork(group);assert(suspended==(kind==1));
                if(kind==3)assert(f.wait_fork(parent));
            } else f.arm_wait(site);
        });
        child=f.process([&]{f.finish_fork(group,0);});
        site=f.add_wait_site(parent,{{signal,0}});group=f.add_fork_group(parent,{child},kind);
        f.arm_wait(site);f.set(signal,V(1));f.run();assert(calls==2);
        f.set(signal,V(0));f.run();assert(calls==3);
    }
#endif
    std::cout<<"PASS wait rearm: same/switching/duplicate/empty lists, dynamic waits, inactive/timers, NBA, repeated checkpoints, prediction commit/rollback; Process=24 Watch=16\n";
}
