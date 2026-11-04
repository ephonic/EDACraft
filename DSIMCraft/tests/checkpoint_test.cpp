#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <random>
using namespace dsim;
int main() {
    Sim s;int a=s.signal(8,true),alias=s.signal(8,true),b=s.signal(8,false);
    for(int i=0;i<8;++i)s.connect_net(a,i,alias,i);
    // Owned mutable captures (PC/local count) are restored by copying closures.
    int timed=s.process([&,pc=0]() mutable {
        s.print("T%0d=%h\n",{V(s.now,0,64),s.get(alias)},false);
        s.assign_nba(b,s.get(alias));
        if(++pc<4)s.delay(0,2);
    });
    int watcher=s.process([&]{s.assign_nba(b,s.get(alias));});
    s.wait(watcher,{{alias,0}});s.delay(timed,2);s.drive(a,11,V(0x55,0,8));
    auto state=std::make_shared<std::vector<GateState>>(1);s.register_state(state);
    auto rng=std::make_shared<std::mt19937>(123);s.register_state(rng);
    state->at(0).capture(false,V(0),V(1),V(0),V(0),'X','X');
    auto cp=s.checkpoint();
    std::ostringstream out;auto* old=std::cout.rdbuf(out.rdbuf());
    s.run_until(3);auto text1=out.str();auto v1=s.get(b);auto random1=(*rng)();
    state->at(0).capture(false,V(1),V(1),V(0),V(0),'X','X');state->at(0).apply();
    s.drive(a,22,V(0xaa,0,8));s.run();assert(s.now==8);
    s.restore(cp);assert(!state->at(0).initialized||state->at(0).clock==0);assert(state->at(0).q==2);
    out.str("");out.clear();s.run_until(3);
    assert(out.str()==text1&&s.get(b).same(v1)&&(*rng)()==random1);
    s.run();auto expected=out.str();auto final=s.get(b);
    // Same checkpoint is reusable, including timer order and wait generations.
    s.restore(cp);out.str("");out.clear();s.run();assert(out.str()==expected&&s.get(b).same(final));
    s.restore(cp);out.str("");out.clear();
    bool accepted=s.predict_until(8,[&](Sim& sim){sim.drive(a,11,V(0xa3,0,8));},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&out.str()==expected&&s.get(b).same(final));
    assert(s.prediction_stats.attempts==1&&s.prediction_stats.rollbacks==1&&s.prediction_stats.commits==0);
    assert(s.prediction_stats.speculative_steps>0&&s.prediction_stats.replayed_steps>0);
    s.restore(cp);out.str("");out.clear();
    accepted=s.predict_until(8,[](Sim&){},[](const Sim&){return true;},[](Sim&){assert(false);});
    assert(accepted&&out.str()==expected&&s.get(b).same(final));
    s.restore(cp);out.str("");out.clear();bool failed=false;
    try{s.predict_until(8,[&](Sim& sim){sim.drive(a,22,V(0));(*rng)();throw std::runtime_error("prediction failure");},[](const Sim&){return true;},[](Sim&){});}
    catch(const std::runtime_error&){failed=true;}
    assert(failed&&out.str().empty()&&s.now==0&&s.get(alias).same(V(0x55,0,8)));
    Sim foreign;failed=false;try{foreign.restore(cp);}catch(const std::runtime_error&){failed=true;}assert(failed);
    failed=false;try{s.signal(1,false);}catch(const std::runtime_error&){failed=true;}assert(failed);
    // #0 and NBA queues must survive, not just signals / future timers.
    Sim q;int x=q.signal(8,false);auto count=std::make_shared<int>(0);q.register_state(count);
    int p=q.process([&]{++*count;q.assign_nba(x,V(0x9a,0,8));});q.delay(p,0);
    auto qc=q.checkpoint();q.run();assert(*count==1&&q.get(x).a==0x9a);q.restore(qc);q.run();assert(*count==1&&q.get(x).a==0x9a);
    // Deferred waveform callbacks see no rejected events or ticks.
    Sim w;int v=w.signal(1,false);std::vector<std::string> events;
    auto change=[](void* ctx,uint64_t t,int,V value){static_cast<std::vector<std::string>*>(ctx)->push_back(std::to_string(t)+":"+format(value,'b'));};
    auto tick=[](void* ctx,uint64_t t){static_cast<std::vector<std::string>*>(ctx)->push_back(std::to_string(t)+":tick");};
    w.attach_wave(&events,change,tick);
    int wp=w.process([&,pc=0]() mutable {w.set(v,V(pc++&1));if(pc<3)w.delay(0,2);});w.enqueue(wp);
    failed=false;try{w.checkpoint();}catch(const std::runtime_error&){failed=true;}assert(failed);
    accepted=w.predict_until(5,[&](Sim& sim){sim.set(v,V(1));},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&events==std::vector<std::string>({"0:0","0:tick","2:1","2:tick","4:0","4:tick","5:tick"}));
    std::cout.rdbuf(old);
    std::cout<<"PASS checkpoint PCs/locals, drivers/aliases, watches, queues, ff state, RNG, reject/replay, commit, output isolation\n";
}
