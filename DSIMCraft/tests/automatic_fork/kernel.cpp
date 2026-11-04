#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DYNAMIC_FORK_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
static void exercise(bool snapshots) {
 Sim s;int q=s.signal(32,false),local=s.signal(32,false),scratch=s.signal(32,false);s.set(q,V(0,0,32));
 int parent=-1,child=-1,group=-1;
 parent=s.process([&,pc=0,round=0]()mutable {
  if(!pc){pc=1;s.delay(parent,1);return;}
  if(pc==1){
   for(int i=1;i<=3;++i){s.push_activation({local});s.set(local,V(i,0,32));assert(!s.start_fork(group));s.set(local,V(i+10,0,32));s.activation_depth(0);}
   pc=2;assert(s.wait_fork(parent));return;
  }
  assert(s.get(q).a==uint64_t((round+1)*72));
  if(++round<20){pc=1;s.delay(parent,1);return;}
 });
 child=s.process([&,pc=0]()mutable {
  if(!pc){s.push_activation({scratch});s.set(scratch,V(0,0,32));s.assign_parts({{scratch,0,8,0}},V(s.get(local).a*2,0,8),false);pc=1;s.delay(s.fork_process_id(child),2);return;}
  s.set(q,V(s.get(q).a+s.get(scratch).a,0,32));s.activation_depth(0);pc=0;s.finish_fork(s.fork_group_id(group),0);
 });
 group=s.add_fork_group(parent,{child},3);s.enable_dynamic_forks();
 // Mixed gate installation may register more signals after fork templates.
 int late=s.signal(1,false),wave_changes=0;
 if(!snapshots)s.attach_wave(&wave_changes,[](void* context,uint64_t,int id,V){assert(id==0||id==3);++*static_cast<int*>(context);},nullptr);
 s.set(late,V(1,0,1));s.enqueue(parent);
 if(snapshots) {
  s.run_until(0);auto before=s.checkpoint();s.run_until(2);assert(s.signals.size()==10&&s.get(q).a==0);
  s.restore(before);assert(s.signals.size()==4);
  assert(!s.predict_until(2,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
  assert(s.prediction_stats.rollbacks==1&&s.signals.size()==10);
  auto waiting=s.checkpoint();s.run();assert(s.get(q).a==1440);
  s.restore(waiting);s.run();assert(s.get(q).a==1440);
 } else {s.run();assert(s.get(q).a==1440&&s.signals.size()==10&&wave_changes==61);}
 assert(s.processes.size()==4);
}
int main(){exercise(false);exercise(true);std::cout<<"PASS automatic frame sharing, escape, partial writes, pool and rollback\n";}
