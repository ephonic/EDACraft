#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_TIMING_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 // A partially finished activation is cancelled and reused while old timers
 // remain in the heap/wheel. Its pending NBA values must still be delivered.
 Sim s;int q=s.signal(32,false),nba=s.signal(32,false),done=s.signal(32,false);
 s.set(q,V(0));s.set(nba,V(0));s.set(done,V(0));int group=-1,target=-1,parent=-1,first=-1,late=-1;
 parent=s.process([&,pc=0,round=0]() mutable {
  if(int transfer=s.take_process_transfer(parent);transfer>=0)pc=transfer;
  if(!pc){pc=1;s.start_fork(group);return;}
  assert(pc==2&&s.get(q).a==0);
  if(++round<3){pc=0;s.start_fork(group);return;}
  s.set(done,V(round,0,32));
 });
 first=s.process([&,pc=0]()mutable {
  if(int transfer=s.take_process_transfer(first);transfer>=0)pc=transfer;
  if(!pc){pc=1;s.assign_nba_after(nba,V(11,0,32),5);s.delay(first,2);return;}
  assert(s.disable_block(target,first)<0);
 });
 late=s.process([&,pc=0]()mutable {
  if(int transfer=s.take_process_transfer(late);transfer>=0)pc=transfer;
  if(!pc){pc=1;s.delay(late,20);return;}
  s.set(q,V(99,0,32));s.finish_fork(group,1);
 });
 group=s.add_fork_group(parent,{first,late});target=s.add_disable_target(parent,2,{group});
 s.enqueue(parent);s.run_until(1);auto pending=s.checkpoint();
 s.run();assert(s.now==9&&s.get(done).a==3&&s.get(q).a==0&&s.get(nba).a==11);
 s.restore(pending);assert(!s.predict_until(10,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&s.get(done).a==3&&s.get(q).a==0&&s.get(nba).a==11);
 // An old Active item must not clear the queued bit for a new activation.
 Sim a;int calls=0,ap=a.process([]{}),ac=a.process([&]{++calls;});
 int ag=a.add_fork_group(ap,{ac}),at=a.add_disable_target(ap,7,{ag});
 a.start_fork(ag);assert(a.disable_block(at,ap)==7);a.start_fork(ag);a.run();assert(calls==1);
 // Inactive and signal-wait wakes from cancelled branches are invalidated.
 Sim z;int zcalls=0,zp=z.process([]{}),zc=z.process([&]{++zcalls;});
 int zg=z.add_fork_group(zp,{zc}),zt=z.add_disable_target(zp,3,{zg});
 z.delay(zc,0);z.disable_block(zt,zp);z.run();assert(zcalls==0&&z.now==0);
#ifdef DSIM_COMPACT_GATES
 int clk=z.compact_net();
#else
 int clk=z.signal(1,false);
#endif
 z.set(clk,V(0));int site=z.add_wait_site(zc,{{clk,1}});z.arm_wait(site);
 z.disable_block(zt,zp);z.set(clk,V(1));z.run();assert(zcalls==0);
 // Pruning alternating cancelled process and inertial driver timers must not
 // advance time. An already issued real driver transition remains independent.
 Sim h;int hp=h.process([]{}),hc=h.process([]{});
 int hg=h.add_fork_group(hp,{hc}),ht=h.add_disable_target(hp,1,{hg});
#ifdef DSIM_COMPACT_GATES
 int net=h.compact_net();
#else
 int net=h.signal(1,true);
#endif
 auto ch=h.delayed_driver(net,0,Sim::DelayPolicy::ReplacePending);
 h.drive_after(ch,V(0),0);h.run();h.delay(hc,10);
 h.drive_after(ch,V(1),20);h.drive_after(ch,V(0),30);
 h.disable_block(ht,hp);h.run();assert(h.now==0&&h.get(net).same(V(0)));
 h.drive_after(ch,V(1),5);h.run();assert(h.now==5&&h.get(net).same(V(1)));
 std::cout<<"PASS named disable: stale Active/Inactive/timer/event, reuse, checkpoint/rollback and independent NBA/drivers\n";
}
