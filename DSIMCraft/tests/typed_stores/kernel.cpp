#ifndef DSIM_REFERENCE_TYPED_STORES
#define DSIM_TYPED_STORES_ENABLED 1
#endif
#define DSIM_PARALLEL_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;

template<int Width> void store(Sim& s,int signal,V value) {
#ifdef DSIM_TYPED_STORES_ENABLED
    s.set_sized<Width>(signal,value);
#else
    s.set(signal,value);
#endif
}
template<int Width> unsigned transitions() {
    unsigned cases=0;
    const auto logic=[](int state){return state==2?V::x(Width):state==3?V::z(Width):V(state,0,Width);};
    for(int from=0;from<4;++from)for(int to=0;to<4;++to)for(bool high:{false,true}) {
        Sim s;int signal=s.signal(Width,true);store<Width>(s,signal,logic(from));
        int wakes[3]={};
        for(int edge=0;edge<3;++edge){int p=s.process([&,edge]{++wakes[edge];});s.wait(p,{{signal,edge}});}
        unsigned publications=0;
        s.observe_resolved([&](uint64_t,int id,V value){assert(id==signal);assert(value.w==Width);++publications;});
        V next=logic(to);if(high&&Width>1)next.a^=UINT64_C(1)<<(Width-1);
        // Inputs deliberately carry bits beyond the destination width.
        const V wide(next.a|~mask(Width),next.b|~mask(Width),64);
        const auto before=s.get(signal);store<Width>(s,signal,wide);
        assert(s.get(signal).same(next));s.run_until(0);
        assert(publications==unsigned(!before.same(next)));
        assert(wakes[0]==int(!before.same(next)));
        assert(wakes[1]==int((from==0&&to!=0)||(from>=2&&to==1)));
        assert(wakes[2]==int((from==1&&to!=1)||(from>=2&&to==0)));
        store<Width>(s,signal,wide);assert(publications==unsigned(!before.same(next)));
        ++cases;
    }
    return cases;
}
int main() {
    const auto cases=transitions<1>()+transitions<5>()+transitions<8>()+transitions<32>()+transitions<64>();
    Sim s;const int signal=s.signal(5,true),other=s.signal(5,true);store<5>(s,signal,V(0));
    int runs=0;
    const int p=s.process([&]{++runs;});s.wait(p,{{signal,0}});
    store<5>(s,signal,V(1));
    const auto pending=s.checkpoint();
    s.run_until(0);assert(runs==1);
    s.restore(pending);s.run_until(0);assert(runs==2);
    // A stale sensitivity on this signal must not wake a process now waiting elsewhere.
    s.wait(p,{{other,0}});store<5>(s,signal,V(2));s.run_until(0);assert(runs==2);
    s.assign_nba(signal,V(3));s.assign_nba(signal,V::x(5));s.assign_nba(signal,V::z(5));
    s.run_until(0);assert(s.get(signal).same(V::z(5)));
    std::cout<<"PASS "<<cases<<" width/edge transitions and pending/stale/NBA states\n";
}
