#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_TIMING_ENABLED 1
#define DSIM_COMPACT_GATES 1
#define DSIM_SCALAR_TIMING_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/parallel.hpp>
#include <cassert>
#include <tuple>
using namespace dsim;
using Trace=std::vector<std::tuple<uint64_t,int,std::string>>;
template<class F> static void rejects(F fn) {
    bool caught=false;try{fn();}catch(const std::exception&){caught=true;}assert(caught);
}
static V wide() {return V::from_words({{7,0},{0,~uint64_t(0)},{23,0},{~uint64_t(0),0},{1,0}},257);}
static void regions() {
    Sim s;int q=s.signal(8,false),w=s.signal(257,false),pin=s.compact_net();
    s.set(q,V(0,0,8));s.set(w,V(0,0,257));
    auto channel=s.delayed_driver(pin,10,Sim::DelayPolicy::PreserveTransitions);
    s.drive_scalar_after(channel,0,0);s.run_until(0);
    Trace trace;s.observe_resolved([&](auto t,auto id,V value){trace.emplace_back(t,id,format(value,'h'));});
    s.assign_nba_after(q,V(1,0,8),5);s.assign_nba_after(w,wide(),5);s.assign_nba_after(q,V(2,0,8),5);
    s.drive_scalar_after(channel,1,5);
    int phase=0;
    int inactive=s.process([&]{assert(phase==1&&s.get(q).a==0);phase=2;s.assign_nba_after(q,V(4,0,8),0);});
    int active=s.process([&]{assert(phase==0&&s.get(q).a==0&&s.get(pin).a==1);phase=1;
        s.assign_nba(q,V(3,0,8));s.delay(inactive,0);});
    s.delay(active,5);s.run();assert(phase==2&&s.now==5);
    Trace expected={{5,pin,"1"},{5,q,"01"},{5,w,format(wide(),'h')},{5,q,"02"},{5,q,"03"},{5,q,"04"}};
    assert(trace==expected&&s.get(w).same(wide()));
    s.assign_parts_after({{q,4,4,0}},V(0xa,0,4),2);
    s.set(q,V(0x47,0,8));s.run();assert(s.get(q).a==0xa7);
}
static void checkpoint() {
    Sim s;int q=s.signal(8,false),w=s.signal(257,false);s.set(q,V(0,0,8));s.set(w,V(0,0,257));
    Trace trace;s.observe_resolved([&](auto t,auto id,V value){trace.emplace_back(t,id,format(value,'h'));});
    s.assign_nba_after(q,V(1,0,8),2);s.assign_nba_after(w,wide(),4);
    s.assign_nba_after(q,V(2,0,8),4);s.assign_parts_after({{q,0,4,0}},V::z(4),6);
    s.run_until(1);auto cp=s.checkpoint();
    bool accepted=s.predict_until(5,[&](Sim& p){p.assign_nba_after(q,V(99,0,8),1);
        p.assign_nba_after(w,V::z(257),2);p.assign_parts_after({{q,0,8,0}},V(44,0,8),4);
    },[](const Sim&){return false;},[](Sim&){});
    s.run();assert(!accepted&&s.prediction_stats.rollbacks==1);
    const Trace expected={{2,q,"01"},{4,w,format(wide(),'h')},{4,q,"02"},{6,q,"0z"}};
    assert(trace==expected&&s.get(w).same(wide()));
    for(int i=0;i<100;++i){s.restore(cp);trace.clear();s.run();assert(trace==expected);}
    // Reuse freed slots while snapshots retain their earlier pending values.
    s.assign_nba_after(q,V(7,0,8),1);s.assign_nba_after(w,V::x(257),2);s.run();
    s.restore(cp);trace.clear();s.run();assert(trace==expected);
    Sim overflow;int v=overflow.signal(1,false);overflow.now=UINT64_MAX-1;
    overflow.assign_nba_after(v,V(1),1);
    rejects([&]{overflow.assign_nba_after(v,V(0),2);});overflow.run();
    assert(overflow.now==UINT64_MAX&&overflow.get(v).same(V(1)));
    rejects([&]{overflow.assign_nba_after(123456,V(0),1);});
}
static void finish(size_t workers,uint64_t window) {
    ConservativeSim m(workers,window);m.enable_global_finish();
    auto p=m.partition(),q=m.partition();auto& a=m.kernel(p);auto& b=m.kernel(q);
    int v=a.signal(257,false);a.set(v,V(0,0,257));Trace trace;
    a.observe_resolved([&](auto t,auto id,V value){trace.emplace_back(t,id,format(value,'h'));});
    a.assign_nba_after(v,wide(),5);a.assign_nba_after(v,V::x(257),7);
    int stop=b.process([&]{b.finished=true;});b.delay(stop,5);
    m.run_until(20);assert(m.finished()&&m.finish_time()==5);
    assert(trace==Trace({{5,v,format(wide(),'h')}})&&a.get(v).same(wide()));
}
int main() {
    regions();checkpoint();
    for(auto workers:{1,2,4})for(uint64_t window:{1,2,7,1024})finish(size_t(workers),window);
    std::cout<<"PASS delayed NBA: Active/Inactive/NBA, stable timed order, scalar delay coexistence, partial/257-bit values, pool reuse, prediction/checkpoints and global finish\n";
}
