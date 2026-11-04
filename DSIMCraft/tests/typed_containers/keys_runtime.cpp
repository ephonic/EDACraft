#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1
#define DSIM_OBJECTS_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int map=s.signal_two_state(32),copy=s.signal_two_state(32),heap=s.signal_two_state(64);
 s.associative_set_class(map);s.associative_set_class(copy);
 const V low(1,0,64),high(0x100000001ULL,0,64),last(UINT64_MAX,0,64),zero(0,0,64);
 auto owner=s.object_new(9,{V(0,0,32)},heap);
 auto field=s.object_associative(owner,9,0,32,heap,false,true);
 auto module=field;module.object=-1;module.signal=module.dependency=map;
 for(auto ref:{module,field}) {
  s.associative_write(ref,low,V(11,0,32),32,true);
  s.associative_write(ref,high,V(22,0,32),32,true);
  s.associative_write(ref,last,V(33,0,32),32,true);
  s.associative_write(ref,zero,V(44,0,32),32,true);
  assert(s.associative_size(ref)==4);
  V key;assert(s.associative_cursor(ref,key,0)&&key.w==64&&key.a==0);
  assert(s.associative_cursor(ref,key,2)&&key.a==1);
  assert(s.associative_cursor(ref,key,2)&&key.a==high.a);
  assert(s.associative_cursor(ref,key,2)&&key.a==UINT64_MAX);
  assert(!s.associative_cursor(ref,key,2)&&key.a==UINT64_MAX);
  assert(s.associative_cursor(ref,key,3)&&key.a==high.a);
 }
 s.associative_replace(copy,map,32,true);auto checkpoint=s.checkpoint();
 s.associative_delete(map,high,false,32);s.associative_write(field,high,V(99,0,32),32,true);
 assert(s.associative_read(copy,high,32,true).a==22);
 s.restore(checkpoint);
 assert(s.associative_read(map,high,32,true).a==22&&s.associative_read(field,high,32,true).a==22);
 assert(s.associative_size(map)==4&&s.associative_size(field)==4);
 std::cout<<"PASS full-width object keys, unsigned traversal, copy and checkpoint\n";
}
