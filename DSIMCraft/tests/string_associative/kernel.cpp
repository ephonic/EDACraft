#define DSIM_OBJECTS_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_STRING_ENABLED 1
#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int heap=s.signal_two_state(64),top=s.signal(129,false);
 auto one=s.object_new(1,{V(0)},heap),two=s.object_new(1,{V(0)},heap);
 auto a=s.object_associative(one,1,0,129,heap),b=s.object_associative(two,1,0,129,heap);
 s.associative_write(a,V::text(""),V::ones(129),129,false);
 s.associative_write(top,V::text("\200"),V::x(129),129,false);
 auto before=s.checkpoint();
 s.associative_replace(b,a,129);s.associative_write(a,V::text(""),V(13,0,129),129,false);
 s.associative_write(a,V::text("late"),V(7,0,129),129,false);
 auto full=s.checkpoint();
 s.associative_delete(a,V(0),true,129);s.associative_delete(top,V(0),true,129);
 assert(s.associative_size(a)==0);
 s.restore(before);
 assert(s.associative_size(a)==1&&s.associative_size(b)==0);
 assert(s.associative_read(a,V::text(""),129,false).same(V::ones(129)));
 assert(s.associative_read(top,V::text("\200"),129,false).same(V::x(129)));
 V key=V::text("unchanged");assert(s.associative_cursor(a,key,0)&&key.text_value().empty());
 assert(!s.associative_cursor(a,key,2)&&key.text_value().empty());
 s.restore(full);
 assert(s.associative_size(a)==2&&s.associative_size(b)==1);
 assert(s.associative_read(a,V::text(""),129,false).a==13);
 assert(s.associative_read(b,V::text(""),129,false).same(V::ones(129)));
 s.associative_write_slice(a,V::text(""),Part{0,65,3,0},V(1,4,3),false);
 assert(s.associative_read(b,V::text(""),129,false).same(V::ones(129)));
 assert(s.associative_read(a,V::text(""),129,false).bit(67)>=2);
 assert(s.associative_size(a)==2&&!s.associative_exists(a,V::text("absent")));
 s.associative_replace(b,top,129,true);
 assert(s.associative_read(b,V::text("\200"),129,true).same(V(0,0,129)));
 bool rejected=false;try{s.object_associative(V(0,0,64),1,0,129,heap);}catch(const std::runtime_error&){rejected=true;}
 assert(rejected);
 std::cout<<"PASS string associative heap and checkpoint isolation\n";
}
