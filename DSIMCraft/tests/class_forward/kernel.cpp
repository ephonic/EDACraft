#define DSIM_DYNAMIC_FORK_ENABLED 1
#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int local=s.signal_two_state(32),actual=s.signal_two_state(32);
 s.set(local,V(7,0,32));s.set(actual,V(11,0,32));
 assert(s.processes.empty());
 try {
  auto outer=s.reference_activation({local},{});
  s.set(local,V(19,0,32));
  {
   const int target=s.reference_signal(local);
   auto inner=s.reference_activation({},{{actual,target}});
   s.set(actual,V(23,0,32));assert(s.get(local).a==23);
  }
  assert(s.get(actual).a==11&&s.get(local).a==23);
  throw std::runtime_error("unwind");
 } catch(const std::runtime_error&) {}
 assert(s.get(local).a==7&&s.get(actual).a==11);
 assert(s.reference_signal(local)==local&&s.reference_signal(actual)==actual);
 s.activation_depth(0);bool rejected=false;
 try{s.activation_depth(1);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 s.process([&]{auto frame=s.reference_activation({local},{});s.set(local,V(31,0,32));assert(s.get(local).a==31);});
 s.enqueue(0);s.run();assert(s.get(local).a==7);
 auto cp=s.checkpoint();s.set(actual,V(99,0,32));s.restore(cp);assert(s.get(actual).a==11);
 std::cout<<"PASS startup automatic frame nesting, ref aliases, unwind and subsequent process isolation\n";
}
