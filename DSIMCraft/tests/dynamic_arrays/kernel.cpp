#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_FORK_JOIN_ENABLED 1
#define DSIM_PROCESS_CONTROL_ENABLED 1
#define DSIM_DYNAMIC_FORK_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int object=s.signal(96,false),local=s.signal(32,false);
 // Fork activations own separate descriptors. Reused physical slots start empty.
 int p=-1,iterations=0;
 p=s.process([&,pc=0]() mutable {
  if(!pc) {
   s.push_activation({local});assert(s.dynamic_size(local)==0);
   s.dynamic_new(local,V(3,0,32),32,true);s.dynamic_write(local,V(0),V(5,0,32),32,true);
   pc=1;s.delay(p,2);return;
  }
  assert(s.dynamic_read(local,V(0),32,true).a==5);
  s.activation_depth(0);pc=0;++iterations;
 });
 s.enable_dynamic_forks();
 assert(s.dynamic_size(object)==0);
 auto empty=s.checkpoint();
 s.dynamic_new(object,V(2,0,32),96,false);
 assert(s.dynamic_read(object,V(0),96,false).same(V::x(96)));
 s.dynamic_write(object,V(1,0,32),V::ones(96),96,false);
 auto full=s.checkpoint();auto source=s.dynamic_values(object);
 s.dynamic_new(object,V(4,0,32),96,false,source);
 s.dynamic_write(object,V(1,0,32),V(7,0,96),96,false);
 assert(source[1].same(V::ones(96)));
 s.restore(full);assert(s.dynamic_size(object)==2&&s.dynamic_read(object,V(1,0,32),96,false).same(V::ones(96)));
 s.restore(empty);assert(s.dynamic_size(object)==0);
 s.enqueue(p);s.run_until(1);auto suspended=s.checkpoint();
 s.run();assert(iterations==1);s.restore(suspended);s.run();assert(iterations==2);
 suspended=Sim::Checkpoint{};s.enqueue(p);s.run();assert(iterations==3&&s.signals.size()==3);
 s.dynamic_new(object,V(1),96,true);s.dynamic_write(object,V(0),V::x(96),96,true);
 assert(s.dynamic_read(object,V(0),96,true).same(V(0,0,96)));
 assert(s.dynamic_read(object,V::x(32),96,true).same(V(0,0,96)));
 bool rejected=false;try{s.dynamic_new(object,V(uint64_t(-1),0,64),96,true);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 std::cout<<"PASS dynamic array checkpoint isolation, suspended frames, slot reuse and wide states\n";
}
