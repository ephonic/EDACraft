#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DYNAMIC_FORK_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int x=s.signal(32,false),formal=s.signal(32,false),nested=s.signal(32,false),local=s.signal(32,false);
 s.set(x,V(1,0,32));int p=-1;
 p=s.process([&,pc=0]()mutable {
  if(!pc) {
   s.push_activation({local},{{formal,s.reference_signal(x)}});
   s.set(local,V(17,0,32));
   // Two reference levels resolve to the same physical variable. A thrown
   // function body must restore the suspended task's frame and depth.
   try {
    auto guard=s.reference_activation({},{{nested,s.reference_signal(formal)}});
    s.set(nested,V(s.get(nested).a+4,0,32));
    assert(s.get(formal).a==5&&s.get(local).a==17);
    throw std::runtime_error("function exit");
   } catch(const std::runtime_error&) {}
   assert(s.reference_signal(nested)==nested&&s.reference_signal(formal)==x);
   assert(s.get(local).a==17);
   pc=1;s.delay(p,2);return;
  }
  assert(s.get(formal).a==5&&s.get(local).a==17);
  s.set(formal,V(s.get(formal).a+s.get(local).a,0,32));s.activation_depth(0);pc=0;
 });
 s.enable_dynamic_forks();s.enqueue(p);auto before=s.checkpoint();
 s.run_until(1);assert(s.get(x).a==5);auto waiting=s.checkpoint();
 assert(!s.predict_until(3,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.get(x).a==22&&s.prediction_stats.rollbacks==1);
 s.run();assert(s.get(x).a==22);
 s.restore(waiting);s.run();assert(s.get(x).a==22);
 s.restore(before);s.run();assert(s.get(x).a==22&&s.signals.size()==5);
 std::cout<<"PASS reference frame nesting, exception exit and suspended rollback\n";
}
