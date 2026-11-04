#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#define DSIM_EVENT_NBA_ENABLED 1
#define DSIM_NAMED_EVENTS_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_BATCH_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int q=s.signal(32,false),r=s.signal(32,false),guard=s.signal(4,false),e=s.named_event();
#ifdef DSIM_COMPACT_GATES
 int clk=s.compact_net();
#else
 int clk=s.signal(1,false);
#endif
 s.set(q,V(0));s.set(r,V(0));s.set(clk,V(0,0,1));s.set(guard,V(1,0,4));
 int direct=s.add_event_nba_site({{clk,1}});
 int named=s.add_event_nba_site({},{{[=](Sim& sim){return sim.get(e);},{e},3,false,[=](Sim& sim){return sim.get(guard);}}});
 auto issue=[&](int site,int dest,int v,uint64_t n=1){s.assign_event_nba(site,{{dest,0,32,0}},V(v,0,32),n);};
 issue(direct,q,11,2);issue(direct,q,22);s.set(clk,V(1,0,1));
 // Late issue cannot consume the existing queued edge.
 issue(direct,r,33);auto pending=s.checkpoint();
 s.run_until(1);assert(s.get(q).a==22&&s.get(r).a==0);
 s.set(clk,V(0,0,1));s.set(clk,V(1,0,1));s.run_until(2);assert(s.get(q).a==11&&s.get(r).a==33);
 s.restore(pending);s.run_until(1);assert(s.get(q).a==22&&s.get(r).a==0);
 s.set(clk,V(0,0,1));s.set(clk,V(1,0,1));
 assert(!s.predict_until(2,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&s.get(q).a==11&&s.get(r).a==33);
 issue(named,q,44,2);s.trigger_event(e);s.trigger_event(e);s.set(guard,V(0,0,4));s.run_until(3);assert(s.get(q).a==11);
 s.trigger_event(e);s.trigger_event(e);s.set(guard,V(1,0,4));s.run_until(4);assert(s.get(q).a==11);
 s.trigger_event(e);s.run_until(5);assert(s.get(q).a==44);
 issue(named,q,55,0);assert(s.get(q).a==44);s.run_until(6);assert(s.get(q).a==55);
 // Reuse a site with many simultaneous issues and then release all payloads.
 for(int i=0;i<1000;++i)issue(direct,q,100+i);
 s.set(clk,V(0,0,1));s.set(clk,V(1,0,1));s.run_until(7);assert(s.get(q).a==1099);
 // Batch lookahead must stop before event jobs even when their numeric IDs
 // alias compiled-process IDs.
 Sim b;int clock=b.signal(1,false),out=b.signal(32,false);b.set(clock,V(0,0,1));b.set(out,V(0));
 struct Batch {uint32_t handler=0;int calls=0;};auto state=std::make_shared<Batch>();
 auto context=b.compiled_context(state);
 state->handler=b.compiled_handler(context,[](Sim& sim,void* raw,uint32_t payload){
  auto& batch=*static_cast<Batch*>(raw);
  sim.compiled_batch(batch.handler,payload,[&](uint32_t){++batch.calls;});
 });
 int site=b.add_event_nba_site({{clock,1}}),gate=b.compiled_process(state->handler,0);
 b.assign_event_nba(site,{{out,0,32,0}},V(7,0,32));b.enqueue(gate);b.set(clock,V(1,0,1));b.run();
 assert(state->calls==1&&b.get(out).a==7);
 // Compound caches remain live while no update is pending; each issue has
 // its own baseline and only consumes notifications after its issue point.
 Sim x;int a=x.signal(8,false),c=x.signal(8,false),dest=x.signal(32,false),event=x.named_event();
 x.set(a,V(0,0,8));x.set(c,V(0,0,8));x.set(dest,V(0,0,32));
 auto sum=[=](Sim& sim){return binary_op<Binary::Add>(sim.get(a),sim.get(c),8);};
 int compound=x.add_event_nba_site({},{{sum,{a,c},0}}),query=x.add_event_nba_site({{event,3}});
 x.set(a,V(1,0,8));x.assign_event_nba(compound,{{dest,0,32,0}},V(66,0,32));x.run_until(1);assert(x.get(dest).a==0);
 x.set(c,V(1,0,8));x.run_until(2);assert(x.get(dest).a==66);
 x.assign_event_nba(compound,{{dest,0,32,0}},V(77,0,32),2);
 x.set(a,V(2,0,8));x.set(c,V(0,0,8));x.run_until(3);assert(x.get(dest).a==66);
 x.set(a,V(3,0,8));x.run_until(4);assert(x.get(dest).a==66);
 x.set(c,V(1,0,8));x.run_until(5);assert(x.get(dest).a==77);
 x.assign_event_nba(query,{{dest,0,32,0}},V(88,0,32));x.trigger_event(event);x.run_until(6);assert(x.get(dest).a==88);
 x.assign_event_nba(query,{{dest,0,32,0}},V(99,0,32));x.trigger_event(event);x.run_until(7);assert(x.get(dest).a==99);
 std::cout<<"PASS event NBA: independent issues, queued checkpoint, rollback, burst/iff, release and batching\n";
}
