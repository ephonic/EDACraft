#define DSIM_NAMED_EVENTS_ENABLED 1
#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#define DSIM_OBJECTS_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
struct State {V a,b,selected;int pc=0,hits=0,bindings=0,round=0;};
int main() {
 Sim s;auto state=std::make_shared<State>();s.register_state(state);
 int heap=s.signal(64,false);s.set(heap,V(0,0,64));
 auto allocate=[=](Sim& sim){return sim.object_new(1,{V(uint64_t(sim.named_event(heap))+1,0,64)},heap);};
 auto identity=[=](Sim& sim,V object){return sim.event_id(sim.object_get(object,1,0));};
 int site=-1,driver=-1;
 int waiter=s.process([&]{++state->hits;if(state->hits<32)s.arm_wait(site);});
 EventExpression expression;expression.edge=3;expression.sample_on_arm=true;expression.defer_until_armed=true;
 expression.named_source=[=](Sim& sim){++state->bindings;return identity(sim,state->selected);};
 site=s.add_expression_wait_site(waiter,{}, {expression});
 driver=s.process([&]{
  if(state->pc==0) {
   state->a=allocate(s);state->b=allocate(s);state->selected=state->a;
   s.arm_wait(site);state->pc=1;s.delay(driver,1);return;
  }
  if(state->pc==1) {
   state->selected=state->b;s.trigger_event(identity(s,state->b));
   assert(state->hits==0);state->pc=2;s.delay(driver,1);return;
  }
  if(state->pc==2) {
   assert(state->hits==0&&state->bindings==1);s.trigger_event(identity(s,state->a));
   state->pc=3;s.delay(driver,1);return;
  }
  if(state->round<31) {
   // The stale A subscription must not deliver to a newer B wait.
   s.trigger_event(identity(s,state->a));s.trigger_event(identity(s,state->b));++state->round;
   s.delay(driver,1);
  }
 });
 s.enqueue(driver);s.run_until(1);assert(state->hits==0);
 const auto signals=s.signals.size();auto checkpoint=s.checkpoint();
 V ghost=allocate(s);int ghost_event=identity(s,ghost);s.trigger_event(ghost_event);
 s.restore(checkpoint);assert(s.signals.size()==signals);
 bool absent=false;try{(void)s.event_triggered(ghost_event);}catch(const std::out_of_range&){absent=true;}assert(absent);
 s.run();assert(state->hits==32&&state->bindings==32);
 const int a=identity(s,state->a),b=identity(s,state->b);
 assert(a!=b&&s.signals[a].watches.size()==1&&s.signals[b].watches.size()==1);
 s.restore(checkpoint);s.run();assert(state->hits==32&&state->bindings==32);
 assert(s.signals[a].watches.size()==1&&s.signals[b].watches.size()==1);
}
