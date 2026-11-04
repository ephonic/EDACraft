#define DSIM_OBJECTS_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#ifndef DSIM_TEST_NARROW
#define DSIM_WIDE_VALUES 1
#define DSIM_STRING_ENABLED 1
#endif
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int heap=s.signal_two_state(64);
 auto a=s.object_new(7,{V(4,0,32),V::x(64)},heap),alias=a;
 assert(s.get(heap).a==1);
 auto before=s.checkpoint();
 s.object_set(alias,7,0,V(8,0,32),heap);
 auto b=s.object_new(8,{V(11,0,32)},heap);
 auto full=s.checkpoint();
 s.object_set(a,7,0,V(99,0,32),heap);
 s.restore(before);
 assert(s.object_get(alias,7,0).a==4&&s.get(heap).a==1);
 bool rejected=false;try{s.object_get(b,8,0);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 s.restore(full);assert(s.object_get(a,7,0).a==8&&s.object_get(b,8,0).a==11);
 auto generation=s.get(heap);s.object_set(alias,7,0,V(8,0,32),heap);assert(s.get(heap).same(generation));
 for(auto handle:{V(0,0,64),V(100,0,64),V(1,1,64),V(1,0,32)}) {
  rejected=false;try{s.object_get(handle,7,0);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 }
 rejected=false;try{s.object_get(a,8,0);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 auto derived=s.object_new(12,{V(5,0,32),V(9,0,32),V(11,0,32)},heap,{7,10});
 assert(s.object_type(derived)==12&&s.object_get(derived,7,0).a==5&&s.object_get(derived,10,1).a==9);
 s.object_set(derived,7,0,V(13,0,32),heap);assert(s.object_get(derived,12,0).a==13);
 auto inherited=s.checkpoint();auto old_heap=s.get(heap);
 auto allocated=s.object_new(13,{V(17,0,32)},heap,{7});s.object_set(derived,7,0,V(99,0,32),heap);
 s.restore(inherited);assert(s.object_type(derived)==12&&s.object_get(derived,7,0).a==13&&s.get(heap).same(old_heap));
 rejected=false;try{s.object_type(allocated);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 rejected=false;try{s.object_get(derived,11,0);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
#ifndef DSIM_TEST_NARROW
 auto wide=s.object_new(9,{V::ones(129),V::text("before")},heap);
 auto cp=s.checkpoint();s.object_set(wide,9,0,V::x(129),heap);s.object_set(wide,9,1,V::text("after"),heap);
 s.restore(cp);assert(s.object_get(wide,9,0).same(V::ones(129))&&s.object_get(wide,9,1).text_value()=="before");
#endif
 std::cout<<"PASS class heap alias/type/checkpoint isolation\n";
}
