#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#define DSIM_NAMED_EVENTS_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;auto count=std::make_shared<int>(0);s.register_state(count);
 int event=s.named_event(),guard=s.signal(4,false);
#ifdef DSIM_COMPACT_GATES
 int clock=s.compact_net();
#else
 int clock=s.signal(1,false);
#endif
 s.set(clock,V(0,0,1));
 s.set(guard,V(0,0,4));
 int site=-1;int waiter=s.process([&]{++*count;s.arm_wait(site);});
 site=s.add_expression_wait_site(waiter,{{clock,1}},{{[=](Sim& sim){return sim.get(event);},{event},3,false,[=](Sim& sim){return sim.get(guard);}}});
 // Late subscribers cannot consume an occurrence already queued for this site.
 s.trigger_event(event);s.arm_wait(site);s.run_until(1);assert(*count==0);
 s.trigger_event(event);s.set(guard,V(1,0,4));s.run_until(2);assert(*count==1);
 s.trigger_event(event);s.set(guard,V(0,0,4));s.run_until(3);assert(*count==1);
 s.set(guard,V(1,0,4));s.trigger_event(event);s.trigger_event(event);s.run_until(4);assert(*count==2);
 s.set(guard,V(0,8,4));s.trigger_event(event);s.run_until(5);assert(*count==2);
 s.set(guard,V(1,8,4));s.run_until(6);assert(*count==2);
 // An old pending job cannot wake a new generation; a new occurrence can.
 s.trigger_event(event);s.arm_wait(site);s.run_until(7);assert(*count==2);
 s.trigger_event(event);s.arm_wait(site);s.trigger_event(event);s.run_until(8);assert(*count==3);
 // A queued occurrence and the guard survive a reusable checkpoint.
 s.trigger_event(event);auto pending=s.checkpoint();s.set(guard,V(0,0,4));s.run_until(9);assert(*count==3);
 s.restore(pending);s.run_until(9);assert(*count==4);
 s.trigger_event_after(event,1);
 assert(!s.predict_until(12,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&*count==5);
 // The ordinary branch wins once. Its following occurrence cannot be replayed
 // into the next arm, including through compact-signal notification.
 s.set(clock,V(1,0,1));s.trigger_event(event);s.run_until(13);assert(*count==6);
 s.trigger_event(event);s.run_until(14);assert(*count==7);
 // Occurrence mode is only valid for one declared named event dependency.
 for(int variant=0;variant<2;++variant) {
  Sim bad;int signal=bad.signal(1,false),e=bad.named_event(),p=bad.process([]{});bool rejected=false;
  try {bad.add_expression_wait_site(p,{},{{[=](Sim& sim){return sim.get(e);},variant?std::vector<int>{e,signal}:std::vector<int>{signal},3,false,{}}});}
  catch(const std::runtime_error&){rejected=true;}
  assert(rejected);
 }
 std::cout<<"PASS qualified named events: Active sampling, even occurrences, arm generations, checkpoint and delayed rollback\n";
}
