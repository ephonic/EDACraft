#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;auto count=std::make_shared<int>(0);s.register_state(count);
#ifdef DSIM_COMPACT_GATES
 int clk=s.compact_net();
#else
 int clk=s.signal(1,false);
#endif
 int guard=s.signal(4,false);s.set(clk,V(0,0,1));s.set(guard,V(0,0,4));
 int site=-1;int waiter=s.process([&]{++*count;s.arm_wait(site);});
 site=s.add_expression_wait_site(waiter,{},{{[=](Sim& sim){return sim.get(clk);},{clk},1,true,[=](Sim& sim){return sim.get(guard);}}});
 s.arm_wait(site);s.set(guard,V(1,0,4));s.run_until(1);assert(*count==0);
 s.set(clk,V(1,0,1));auto pending=s.checkpoint();s.set(guard,V(0,0,4));s.run_until(2);assert(*count==0);
 s.restore(pending);s.run_until(2);assert(*count==1);
 s.set(clk,V(0,0,1));s.run_until(3);s.set(guard,V(0,8,4));s.set(clk,V(1,0,1));s.run_until(4);assert(*count==1);
 s.set(guard,V(1,0,4));s.run_until(5);assert(*count==1);
 s.set(clk,V(0,0,1));s.run_until(6);s.set(guard,V(1,8,4));s.set(clk,V(1,0,1));
 assert(!s.predict_until(7,[](Sim&){},[](const Sim&){return false;},[](Sim&){}));
 assert(s.prediction_stats.rollbacks==1&&*count==2);
 std::cout<<"PASS conditional event kernel: guard-only changes, Active sampling, four-state truth, queued checkpoint and rollback\n";
}
