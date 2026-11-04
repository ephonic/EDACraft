#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int a=s.signal(32,false),b=s.signal(32,false),done=s.signal(1,false);
 s.set(a,V(0));s.set(b,V(0));s.set(done,V(0));int group=-1,parent=-1,first=-1,last=-1;
 parent=s.process([&,pc=0]()mutable {
  if(!pc){pc=1;assert(s.start_fork(group));return;}
  if(pc==1){assert(s.now==2&&s.get(a).a==1&&s.get(b).a==0);pc=2;assert(s.wait_fork(parent));return;}
  assert(s.now==5&&s.get(b).a==1);s.set(done,V(1));
 });
 first=s.process([&,pc=0]()mutable {if(!pc){pc=1;s.delay(first,2);return;}pc=0;s.set(a,V(1));s.finish_fork(group,0);});
 last=s.process([&,pc=0]()mutable {if(!pc){pc=1;s.delay(last,5);return;}pc=0;s.set(b,V(1));s.finish_fork(group,1);});
 group=s.add_fork_group(parent,{first,last},2);s.enqueue(parent);s.run_until(3);assert(s.processes[size_t(parent)].waiting);auto cp=s.checkpoint();
 s.run();assert(s.now==5&&s.get(done).a==1);s.restore(cp);
 assert(!s.predict_until(6,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&s.get(done).a==1);
 // join_none never resumes its parent, and children sample after it yields.
 Sim n;int nq=n.signal(32,false),nr=n.signal(32,false),np=-1,nc=-1,ng=-1,calls=0;
 n.set(nq,V(0));n.set(nr,V(0));np=n.process([&]{++calls;assert(!n.start_fork(ng));n.set(nq,V(7,0,32));});
 nc=n.process([&]{n.set(nr,n.get(nq));n.finish_fork(ng,0);});ng=n.add_fork_group(np,{nc},3);
 n.enqueue(np);n.run();assert(calls==1&&n.get(nr).a==7&&!n.wait_fork(np));
 // Direct-child wait excludes a live grandchild after its parent completes.
 // Descendant cancellation must still reach that orphan and prune its timer.
 Sim d;int dp=-1,dc=-1,gc=-1,dg=-1,gg=-1,count=d.signal(32,false);d.set(count,V(0));
 dp=d.process([&,pc=0]()mutable {if(!pc){pc=1;assert(!d.start_fork(dg));assert(d.wait_fork(dp));return;}
  assert(d.now==2);d.disable_fork(dp);assert(!d.wait_fork(dp));d.set(count,V(1));});
 dc=d.process([&,pc=0]()mutable {if(!pc){pc=1;d.delay(dc,2);return;}assert(!d.start_fork(gg));d.finish_fork(dg,0);});
 gc=d.process([&,pc=0]()mutable {if(!pc){pc=1;d.delay(gc,8);return;}d.set(count,V(99,0,32));d.finish_fork(gg,0);});
 dg=d.add_fork_group(dp,{dc},3);gg=d.add_fork_group(dc,{gc},3);d.enqueue(dp);d.run();assert(d.now==2&&d.get(count).a==1);
 // Reject static-slot reuse while either direct children or their descendants
 // remain live; after cancellation, the same site is reusable.
 Sim o;int op=o.process([]{}),oc=o.process([]{}),og=o.add_fork_group(op,{oc},3);
 assert(!o.start_fork(og));bool rejected=false;try{o.start_fork(og);}catch(const std::runtime_error& e){rejected=std::string(e.what()).find("overlapping fork activations")!=std::string::npos;}assert(rejected);
 o.disable_fork(op);assert(!o.start_fork(og));o.disable_fork(op);o.run();assert(o.now==0);
 bool invalid=false;try{o.add_fork_group(op,{},4);}catch(const std::runtime_error&){invalid=true;}assert(invalid);
 std::cout<<"PASS fork control: any/none, direct-child wait, descendant cancellation, overlap guards and actual rollback\n";
}
