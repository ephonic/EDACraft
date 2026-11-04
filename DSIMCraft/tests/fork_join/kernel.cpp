#define DSIM_FORK_JOIN_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int q=s.signal(32,false),r=s.signal(32,false),done=s.signal(32,false);
 s.set(q,V(0));s.set(r,V(0));s.set(done,V(0));
 int group=-1,parent=-1,first=-1,last=-1;
 parent=s.process([&,pc=0,round=0]() mutable {
  if(!pc){pc=1;assert(s.start_fork(group));return;}
  assert(s.get(q).a==uint64_t(round+1)&&s.get(r).a==uint64_t(round+1));
  if(++round<3){assert(s.start_fork(group));return;}
  s.set(done,V(round,0,32));
 });
 first=s.process([&,pc=0]() mutable {
  if(!pc){pc=1;s.delay(first,1);return;}
  pc=0;s.set(q,V(s.get(q).a+1,0,32));s.finish_fork(group,0);
 });
 last=s.process([&,pc=0]() mutable {
  if(!pc){pc=1;s.delay(last,3);return;}
  pc=0;s.set(r,V(s.get(r).a+1,0,32));s.finish_fork(group,1);
 });
 group=s.add_fork_group(parent,{first,last});
 int empty=s.add_fork_group(parent,{});assert(!s.start_fork(empty));
 bool rejected=false;try{s.add_fork_group(parent,{first,first});}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 // Children stay dormant until the parent reaches its fork.
 s.run_until(0);assert(s.get(q).a==0&&s.get(r).a==0);
 s.enqueue(parent);s.run_until(1);
 assert(s.get(q).a==1&&s.get(r).a==0&&s.processes[parent].waiting);
 auto pending=s.checkpoint();
 s.run_until(10);assert(s.get(q).a==3&&s.get(r).a==3&&s.get(done).a==3&&!s.processes[parent].waiting);
 s.restore(pending);assert(s.get(q).a==1&&s.get(r).a==0&&s.processes[parent].waiting);
 assert(!s.predict_until(10,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&s.get(q).a==3&&s.get(r).a==3&&s.get(done).a==3);
 rejected=false;try{s.finish_fork(group,1);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 rejected=false;try{s.add_fork_group(parent,{});}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 // Zero-time children finish in Active; the parent resumes before their NBA.
 Sim z;int x=z.signal(32,false);z.set(x,V(0));int zg=-1;
 int zp=z.process([&,pc=0]()mutable{if(!pc){pc=1;z.start_fork(zg);return;}assert(z.get(x).a==0);});
 int za=z.process([&]{z.assign_nba(x,V(11,0,32));z.finish_fork(zg,0);});
 int zb=z.process([&]{z.finish_fork(zg,1);});
 zg=z.add_fork_group(zp,{za,zb});z.enqueue(zp);z.run();assert(z.get(x).a==11);
 // A signal-sensitive child must remain suspended until its actual edge.
 Sim e;
#ifdef DSIM_COMPACT_GATES
 int clk=e.compact_net();
#else
 int clk=e.signal(1,false);
#endif
 e.set(clk,V(0,0,1));int eg=-1,site=-1;bool joined=false;
 int ep=e.process([&,pc=0]()mutable{if(!pc){pc=1;e.start_fork(eg);return;}joined=true;});
 int ec=e.process([&,pc=0]()mutable{if(!pc){pc=1;e.arm_wait(site);return;}e.finish_fork(eg,0);});
 site=e.add_wait_site(ec,{{clk,1}});eg=e.add_fork_group(ep,{ec});e.enqueue(ep);e.run_until(1);assert(!joined);
 e.set(clk,V(1,0,1));e.run();assert(joined);
 std::cout<<"PASS fork join: dormant branches, reuse, pending checkpoint/rollback, NBA, edge wait and validation\n";
}
