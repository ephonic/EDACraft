#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_EVENT_NBA_ENABLED 1
#define DSIM_EXPRESSION_EVENTS_ENABLED 1
#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DYNAMIC_FORK_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_INDEXED_SELECT_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
static void allocations() {
 Sim s;int a=s.signal(96,false),b=s.signal_two_state(8);
 s.dynamic_new(a,V(1),96,false);s.dynamic_write(a,V(0),V(0,0,96),96,false);
 auto first=s.dynamic_part(a,V(0),96);
 s.assign_parts({first},V(1,0,96),true);s.assign_parts({first},V(2,0,96),true);
 assert(s.dynamic_read(a,V(0),96,false).a==0);s.run();assert(s.dynamic_read(a,V(0),96,false).a==2);
 // Same-length self initialization retains a pending element address.
 s.assign_parts_after({s.dynamic_part(a,V(0),96)},V::ones(96),2);
 s.dynamic_new(a,V(1),96,false,s.dynamic_values(a),a);s.run();
 assert(s.dynamic_read(a,V(0),96,false).same(V::ones(96)));
 // Ordinary assignment, even self assignment, replaces the allocation.
 s.assign_parts_after({s.dynamic_part(a,V(0),96)},V(3,0,96),2);
 s.dynamic_replace(a,s.dynamic_values(a),96,false);s.run();assert(s.dynamic_read(a,V(0),96,false).same(V::ones(96)));
 s.assign_parts_after({s.dynamic_part(a,V(0),96)},V(4,0,96),2);
 s.dynamic_new(a,V(2,0,32),96,false,s.dynamic_values(a),a);s.run();assert(s.dynamic_read(a,V(0),96,false).same(V::ones(96)));
 // Queued generations and values restore independently of speculative allocation.
 s.assign_parts_after({s.dynamic_part(a,V(0),96)},V(9,0,96),2);auto cp=s.checkpoint();
 assert(!s.predict_until(s.now+4,[&](Sim& x){x.dynamic_new(a,V(1),96,false);},[](const Sim&){return false;},[](Sim&){}));
 s.run();assert(s.dynamic_read(a,V(0),96,false).a==9);s.restore(cp);s.run();assert(s.dynamic_read(a,V(0),96,false).a==9);
 s.dynamic_new(b,V(1),8,true);s.assign_parts({s.dynamic_part(b,V(0),8)},V::x(8),true);s.run();assert(s.dynamic_read(b,V(0),8,true).same(V(0,0,8)));
 for(V index:{V::x(32),V(uint64_t(-1),0,64),V(2,0,32)}) {
  bool rejected=false;try{s.dynamic_part(a,index,96);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 }
}
static void events() {
 Sim s;int a=s.signal(32,false),clk=s.signal(1,false);s.set(clk,V(0));
 int site=s.add_event_nba_site({{clk,1}});
 s.assign_event_nba(site,{s.dynamic_part(a,V(0),32,true)},V(7,0,32));
 s.dynamic_new(a,V(1),32,false);s.set(clk,V(1));s.run();assert(s.dynamic_read(a,V(0),32,false).a==7);
 s.set(clk,V(0));s.run();
 s.assign_event_nba(site,{s.dynamic_part(a,V(0),32,true)},V(9,0,32));
 s.dynamic_new(a,V(2,0,32),32,false);s.set(clk,V(1));s.run();assert(s.dynamic_read(a,V(0),32,false).a==9);
}
static void reuse() {
 Sim s;int local=s.signal(32,false),clk=s.signal(1,false),p=-1,calls=0;
 s.set(clk,V(0));int site=s.add_event_nba_site({{clk,1}});
 p=s.process([&,pc=0]()mutable {
  if(!pc){s.push_activation({local});s.dynamic_new(local,V(1),32,false);s.dynamic_write(local,V(0),V(0,0,32),32,false);
   ++calls;
   if(calls<=24) {
    s.assign_parts_after({s.dynamic_part(local,V(0),32)},V(uint64_t(calls),0,32),4);
    s.assign_event_nba(site,{s.dynamic_part(local,V(0),32,true)},V(uint64_t(calls),0,32));
   }
   pc=1;s.delay(p,1);return;}
  assert(s.dynamic_read(local,V(0),32,false).a==0);s.activation_depth(0);pc=0;
 });
 s.enable_dynamic_forks();
 for(int i=1;i<=24;++i){s.enqueue(p);s.run_until(uint64_t(i));}
 s.enqueue(p);s.run_until(24);s.set(clk,V(1));s.run_until(25);
 s.run();assert(calls==25&&s.signals.size()==3);
}
static void selected_updates() {
 Sim s;int a=s.signal(96,false),b=s.signal_two_state(16),clk=s.signal(1,false);
 int site=s.add_event_nba_site({{clk,1}});
 s.dynamic_new(a,V(1),96,false);s.dynamic_write(a,V(0),V(0,0,96),96,false);
 s.dynamic_new(b,V(1),16,true);s.set(clk,V(0));
 auto part=[&](int lo,int width,bool event=false){auto p=s.dynamic_part(a,V(0),96,event);p.lo=lo;p.width=width;return p;};
 // Merge independent delayed updates with the element's value at commit time.
 s.assign_parts_after({part(4,4)},V(10,0,4),2);
 s.assign_parts_after({part(68,12)},V(0xdef,0,12),2);
 s.dynamic_write_slice(a,V(0),Part{0,0,4,0},V(7,0,4),false);
 auto cp=s.checkpoint();
 assert(!s.predict_until(3,[&](Sim& x){x.dynamic_write_slice(a,V(0),Part{0,0,4,0},V(8,0,4),false);},[](const Sim&){return false;},[](Sim&){}));
 s.run();auto wanted=replace(replace(V(7,0,96),4,4,V(10,0,4)),68,12,V(0xdef,0,12));
 assert(s.dynamic_read(a,V(0),96,false).same(wanted));s.restore(cp);s.run();assert(s.dynamic_read(a,V(0),96,false).same(wanted));
 // Unknown selects are no-ops; partly overlapping selects retain RHS alignment.
 s.dynamic_write_slice(a,V(0),indexed_part(0,96,V::x(32),0,4,false,0),V(15,0,4),false);
 s.dynamic_write_slice(a,V(0),indexed_part(0,96,V(1,0,32),0,4,true,0),V(10,0,4),false);
 wanted=replace(wanted,0,2,V(2,0,2));assert(s.dynamic_read(a,V(0),96,false).same(wanted));
 auto bp=s.dynamic_part(b,V(0),16);bp.lo=4;bp.width=4;
 s.assign_parts({bp},V::x(4),true);s.run();assert(s.dynamic_read(b,V(0),16,true).a==0);
 s.assign_event_nba(site,{part(4,4,true)},V(12,0,4));
 s.dynamic_new(a,V(2,0,32),96,false);s.dynamic_write(a,V(0),V(0x1234,0,96),96,false);
 s.set(clk,V(1));s.run();assert(s.dynamic_read(a,V(0),96,false).same(V(0x12c4,0,96)));
 // A replaced allocation cannot receive an earlier partial delayed update.
 s.assign_parts_after({part(0,4)},V(9,0,4),1);s.dynamic_new(a,V(1),96,false);
 s.run();assert(s.dynamic_read(a,V(0),96,false).same(V::x(96)));
}
static void concatenation() {
 Sim s;int a=s.signal(16,false),tail=s.signal(8,false),clk=s.signal(1,false);
 int site=s.add_event_nba_site({{clk,1}});s.set(clk,V(0));s.set(tail,V(0,0,8));
 s.dynamic_new(a,V(1),16,false);s.dynamic_write(a,V(0),V(0,0,16),16,false);
 auto left=s.dynamic_part(a,V(0),16);left.lo=4;left.width=8;left.rhs_lo=8;
 auto right=s.dynamic_part(a,V(0),16);right.width=8;
 s.assign_parts({right,left},V(0x1234,0,16),false);
 assert(s.dynamic_read(a,V(0),16,false).a==0x134);
 auto whole=s.dynamic_part(a,V(0),16);whole.rhs_lo=8;
 s.assign_parts_after({Part{tail,0,8,0},whole},V(0x56789a,0,24),2);
 auto cp=s.checkpoint();assert(!s.predict_until(3,[&](Sim& x){x.dynamic_new(a,V(2,0,32),16,false);},[](const Sim&){return false;},[](Sim&){}));
 s.run();assert(s.dynamic_read(a,V(0),16,false).a==0x5678&&s.get(tail).a==0x9a);
 s.restore(cp);s.dynamic_new(a,V(2,0,32),16,false);s.run();
 assert(s.dynamic_read(a,V(0),16,false).same(V::x(16))&&s.get(tail).a==0x9a);
 auto event=s.dynamic_part(a,V(0),16,true);event.rhs_lo=8;
 s.assign_event_nba(site,{Part{tail,0,8,0},event},V(0x765432,0,24));
 s.dynamic_new(a,V(1),16,false);s.set(clk,V(1));s.run();
 assert(s.dynamic_read(a,V(0),16,false).a==0x7654&&s.get(tail).a==0x32);
 auto invalid=s.dynamic_part(a,V::x(32),16,false,true);assert(invalid.width==0);
 s.assign_parts({Part{tail,0,8,0},invalid},V(0xffff71,0,24),false);assert(s.get(tail).a==0x71);
}
int main(){allocations();events();reuse();selected_updates();concatenation();std::cout<<"PASS dynamic NBA slices, mixed concatenations, allocation capture, rollback and automatic slot reuse\n";}
