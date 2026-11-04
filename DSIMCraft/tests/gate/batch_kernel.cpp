#define DSIM_BATCH_ENABLED 1
#define DSIM_BATCH_PROFILE 1
#define DSIM_TIMING_ENABLED 1
#define DSIM_PARALLEL_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
struct Model {uint32_t handler;bool batch;std::vector<int> pins,sites;};
static void evaluate(Sim& s,Model& m,uint32_t i) {
    s.arm_fixed_wait(m.sites[i]);
    s.print("E %0t %d %b",{V(s.now,0,64),V(i),s.get(m.pins[i])});
    s.drive(m.pins[i+1],int(i),inv(s.get(m.pins[i])));
}
static void handler(Sim& s,void* raw,uint32_t first) {
    auto& m=*static_cast<Model*>(raw);
    if(m.batch)s.compiled_batch(m.handler,first,[&](uint32_t i){evaluate(s,m,i);});
    else evaluate(s,m,first);
}
static std::string circuit(bool batch,bool replay,uint64_t limit=100000) {
    Sim s;s.limit=limit;std::string output;
    s.redirect_output([&](uint64_t,const std::string& text){output+=text;});
    auto m=std::make_shared<Model>();m->batch=batch;
    for(int i=0;i<6;++i)m->pins.push_back(s.signal(1,true));
    auto ctx=s.compiled_context(m);m->handler=s.compiled_handler(ctx,handler);
    // Alternate other handler identities with a long same-handler prefix.
    int monitor=s.process([&]{s.print("M %0t %b",{V(s.now,0,64),s.get(m->pins.back())});s.wait(0,{{m->pins.back(),0}});});
    assert(monitor==0);
    for(uint32_t i=0;i<5;++i){auto p=s.compiled_process(m->handler,i);m->sites.push_back(s.add_fixed_wait(p,{{m->pins[i],0}}));s.enqueue(p);}
    auto channel=s.delayed_driver(m->pins.front(),100,Sim::DelayPolicy::ReplacePending);
    int source=s.process([&,pc=0]() mutable {
        s.drive_after(channel,V(pc&1),2);s.drive_after(channel,V((pc+1)&1),1);
        if(++pc<8)s.delay(6,3);
    });assert(source==6);s.enqueue(source);s.enqueue(monitor);
    // A zero-delay wake and NBA callback must retain their FIFO positions.
    int special=s.process([&,pc=0]() mutable {
        if(pc++==0){s.delay(7,0);return;}
        s.print("I %0t",{V(s.now,0,64)});s.assign_nba(m->pins.front(),V::x(1));
    });assert(special==7);s.enqueue(special);
    s.deliver_at(4,m->pins.front(),100,V::z(1));
    if(replay) {
        s.run_until(3);
        auto before=s.batch_stats;
        bool accepted=s.predict_until(10,[&](Sim& x){x.drive(m->pins.front(),100,V::x(1));},[](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&s.prediction_stats.rollbacks==1);
        assert(s.batch_stats.events>=before.events);
    }
    try{s.run_until(40);}catch(const std::runtime_error& e){output+=e.what();}
    if(batch&&limit==100000)assert(s.batch_stats.events>s.batch_stats.entries);
    return output;
}
int main() {
    auto reference=circuit(false,false);
    assert(circuit(true,false)==reference);
    assert(circuit(true,true)==circuit(false,true));
    // Compare each budget boundary, including failures inside a batch.
    for(uint64_t limit=1;limit<90;++limit)assert(circuit(true,false,limit)==circuit(false,false,limit));
    Sim outside;bool failed=false;try{outside.compiled_batch(0,0,[](uint32_t){});}catch(const std::runtime_error&){failed=true;}assert(failed);
    std::cout<<"PASS FIFO batches: four-state changes, mixed actions, fixed rearm, Active wake/Inactive/NBA, delayed cancellation, arrivals, rollback and 89 instruction boundaries\n";
}
