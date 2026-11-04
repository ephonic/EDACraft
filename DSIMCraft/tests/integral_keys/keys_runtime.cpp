#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1
#define DSIM_OBJECTS_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_TWO_STATE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int map=s.signal_two_state(32),copy=s.signal_two_state(32),heap=s.signal_two_state(64),signed_map=s.signal_two_state(32);
 s.associative_set_unsigned(map);s.associative_set_unsigned(copy);
 auto owner=s.object_new(9,{V(0,0,32)},heap);
 auto field=s.object_associative(owner,9,0,32,heap,true);
 const auto low=V(1,0,129),high=V::from_words({{1,0},{0,0},{1,0}},129);
 const auto middle=V::from_words({{0,0},{1,0},{0,0}},129);
 auto module=field;module.object=-1;module.signal=module.dependency=map;
 for(auto ref:{module,field}) {
  s.associative_write(ref,high,V(33,0,32),32,true);
  s.associative_write(ref,low,V(11,0,32),32,true);
  s.associative_write(ref,middle,V(22,0,32),32,true);
  assert(s.associative_size(ref)==3);
  V key;assert(s.associative_cursor(ref,key,0)&&key.same(low));
  assert(s.associative_cursor(ref,key,2)&&key.same(middle));
  assert(s.associative_cursor(ref,key,2)&&key.same(high));
  assert(!s.associative_cursor(ref,key,2)&&key.same(high));
  assert(s.associative_cursor(ref,key,3)&&key.same(middle));
  auto unknown=V::from_words({{0,0},{0,0},{1,1}},129);
  assert(!s.associative_exists(ref,unknown));bool rejected=false;
  try{s.associative_read(ref,unknown,32,true);}catch(const std::runtime_error&){rejected=true;}assert(rejected);rejected=false;
  try{s.associative_write(ref,unknown,V(1,0,32),32,true);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 }
 s.associative_replace(copy,map,32,true);auto checkpoint=s.checkpoint();
 s.associative_delete(map,high,false,32);s.associative_write(field,high,V(99,0,32),32,true);
 assert(s.associative_read(copy,high,32,true).a==33);s.restore(checkpoint);
 assert(s.associative_read(map,high,32,true).a==33&&s.associative_read(field,high,32,true).a==33);
 const auto minus=V::from_words({{~uint64_t(1),0},{1,0}},65),zero=V(0,0,65),positive=V(~uint64_t(0),0,65);
 for(auto key:{zero,positive,minus})s.associative_write(signed_map,key,V(1,0,32),32,true);
 V key;assert(s.associative_cursor(signed_map,key,0)&&key.same(minus));
 assert(s.associative_cursor(signed_map,key,2)&&key.same(zero));
 assert(s.associative_cursor(signed_map,key,2)&&key.same(positive));
 std::cout<<"PASS typed integral key limbs, sign order, X/Z rejection and checkpoint\n";
}
