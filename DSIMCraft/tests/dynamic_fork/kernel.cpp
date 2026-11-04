#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DYNAMIC_FORK_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int q=s.signal(32,false);s.set(q,V(0,0,32));int parent=-1,child=-1,group=-1;
 parent=s.process([&,pc=0]()mutable {
  if(!pc){pc=1;s.delay(parent,1);return;}
  if(pc==1){pc=2;for(int i=0;i<3;++i)assert(!s.start_fork(group));assert(s.wait_fork(parent));return;}
  assert(s.now==3&&s.get(q).a==3);
 });
 child=s.process([&,pc=0]()mutable {
  if(!pc){pc=1;s.delay(s.fork_process_id(child),2);return;}
  pc=0;s.set(q,V(s.get(q).a+1,0,32));s.finish_fork(s.fork_group_id(group),0);
 });
 group=s.add_fork_group(parent,{child},3);s.enable_dynamic_forks();s.enqueue(parent);
 s.run_until(0);auto before_spawn=s.checkpoint();assert(s.processes.size()==2);
 s.run();assert(s.get(q).a==3&&s.processes.size()==4);
 s.restore(before_spawn);assert(s.processes.size()==2&&s.get(q).a==0);
 assert(!s.predict_until(2,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&s.processes.size()==4&&s.get(q).a==0);
 auto waiting=s.checkpoint();s.run();assert(s.get(q).a==3);
 s.restore(waiting);s.run();assert(s.get(q).a==3&&s.processes.size()==4);
 // Source-level named disable and event subscriptions are checked by the RTL
 // models; this verifies allocation itself restores after a failed prediction.
 std::cout<<"PASS dynamic fork allocation, independent PCs and rollback before/after spawning\n";
}
