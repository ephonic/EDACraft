#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1
#define DSIM_OBJECTS_ENABLED 1
#define DSIM_STRING_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_TWO_STATE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;const int map=s.signal_two_state(32),copy=s.signal_two_state(32),heap=s.signal_two_state(64);
 s.associative_set_unsigned(map);s.associative_set_unsigned(copy);
 auto owner=s.object_new(9,{V(0,0,32)},heap);auto field=s.object_associative(owner,9,0,32,heap,true);
 auto high=V::from_words({{1,0},{0,0},{1,0}},129);
 for(auto root:{s.associative_ref(map),field}) {
  auto sub=s.associative_subarray(root,high,false,false);
  assert(!s.associative_size(sub)&&!s.associative_exists(root,high));
  s.associative_delete(sub,V(0),true,32);assert(!s.associative_exists(root,high));
  s.associative_write(sub,V(~uint64_t(0),0,32),V(17,0,32),32,true);
  s.associative_write(sub,V(1,0,32),V(9,0,32),32,true);
  V key;assert(s.associative_cursor(sub,key,0)&&key.a==0xffffffff); // inner signed overrides outer unsigned
  assert(s.associative_exists(root,high)&&s.associative_size(root)==1);
  auto third=s.associative_subarray(sub,V(99,0,32),false,false);
  s.associative_write(third,V(7,0,32),V(23,0,32),32,true);
  assert(s.associative_read(third,V(7,0,32),32,true).a==23);
 }
 s.associative_replace(copy,map,32,true);auto snap=s.checkpoint();
 auto sub=s.associative_subarray(s.associative_ref(map),high);
 auto sibling=s.associative_subarray(s.associative_ref(copy),high);
 s.associative_delete(sub,V(0),true,32);
 assert(s.associative_size(sub)==0&&s.associative_exists(map,high));
 assert(s.associative_size(sibling)==3);
 s.restore(snap);assert(s.associative_size(sub)==3);
 // Copy before resolving a destination below the source, and before deleting
 // an ancestor of the source; both must own an independent tree.
 auto child=s.associative_subarray(sibling,V(99,0,32),false,false);
 s.associative_replace(sibling,child,32,true);
 assert(s.associative_size(sibling)==1&&s.associative_read(sibling,V(7,0,32),32,true).a==23);
 s.associative_delete(copy,high,false,32);assert(!s.associative_exists(copy,high)&&s.associative_size(sub)==3);
 bool rejected=false;try{s.associative_subarray(map,V::x(129));}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 std::cout<<"PASS nested associative storage, key axes, deletion, copies and rollback\n";
}
