#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#define DSIM_BATCH_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
struct Counts {int changes=0,edges=0,mixed=0;};
int main() {
 Sim s;auto counts=std::make_shared<Counts>();s.register_state(counts);
 int a=s.signal(8,false),b=s.signal(8,false),flag=s.signal(1,false);
 s.set(a,V(0,0,8));s.set(b,V(0,0,8));s.set(flag,V(0,0,1));
 int change_site=-1,edge_site=-1,mixed_site=-1;
 int changes=s.process([&]{++counts->changes;s.arm_wait(change_site);});
 int edges=s.process([&]{++counts->edges;s.arm_wait(edge_site);});
 int mixed=s.process([&]{++counts->mixed;s.arm_wait(mixed_site);});
 auto sum=[=](Sim& sim){return binary_op<Binary::Add>(sim.get(a),sim.get(b),8);};
 change_site=s.add_expression_wait_site(changes,{},{{sum,{a,b},0}});
 edge_site=s.add_expression_wait_site(edges,{},{{[=](Sim& sim){return sim.get(a);},{a},1}});
 mixed_site=s.add_expression_wait_site(mixed,{{flag,0}},{{sum,{a,b},0}});
 for(int site:{change_site,edge_site,mixed_site})s.arm_wait(site);
 s.set(a,V(1,0,8));s.set(b,V(1,0,8));
 auto pending=s.checkpoint();
 assert(!s.predict_until(1,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&counts->changes==1&&counts->edges==1&&counts->mixed==1);
 s.restore(pending);assert(counts->changes==0&&s.now==0);s.run_until(1);
 assert(counts->changes==1&&counts->edges==1&&counts->mixed==1);
 s.set(a,V(2,0,8));s.set(b,V(0,0,8));s.run_until(2);
 assert(counts->changes==1&&counts->edges==1);
 s.set(a,V(3,0,8));s.set(flag,V(1,0,1));s.run_until(3);
 assert(counts->changes==2&&counts->edges==2&&counts->mixed==2);
 s.set(a,V(4,0,8));s.run_until(4);assert(counts->changes==3);
 // Expression job zero must not be mistaken for compiled gate process zero.
 struct BatchState {uint32_t handler=0;int calls=0,wakes=0,site=-1;};
 Sim batch_sim;auto batch=std::make_shared<BatchState>();
 auto context=batch_sim.compiled_context(batch);
 batch->handler=batch_sim.compiled_handler(context,[](Sim& sim,void* raw,uint32_t payload){
   auto& state=*static_cast<BatchState*>(raw);
   sim.compiled_batch(state.handler,payload,[&](uint32_t){++state.calls;});
 });
 int gate=batch_sim.compiled_process(batch->handler,0),source=batch_sim.signal(1,false);
 batch_sim.set(source,V(0,0,1));
 int waiter=batch_sim.process([&]{++batch->wakes;batch_sim.arm_wait(batch->site);});
 batch->site=batch_sim.add_expression_wait_site(waiter,{},{{[=](Sim& sim){return sim.get(source);},{source},0}});
 batch_sim.arm_wait(batch->site);batch_sim.enqueue(gate);batch_sim.set(source,V(1,0,1));batch_sim.run();
 assert(batch->calls==1&&batch->wakes==1);
#ifdef DSIM_COMPACT_GATES
 Sim compact_sim;int compact_count=0;
 int compact=compact_sim.compact_net();compact_sim.set(compact,V(0,0,1));int compact_site=-1;
 int compact_waiter=compact_sim.process([&]{++compact_count;compact_sim.arm_wait(compact_site);});
 compact_site=compact_sim.add_expression_wait_site(compact_waiter,{},{{[=](Sim& sim){return unary("!",sim.get(compact),1);},{compact},0}});
 compact_sim.arm_wait(compact_site);compact_sim.set(compact,V(1,0,1));compact_sim.run_until(1);assert(compact_count==1);
#endif
 std::cout<<"PASS expression event kernel: coalescing, cached values, bit-zero edges, mixed waits, queued checkpoint and rollback\n";
}
