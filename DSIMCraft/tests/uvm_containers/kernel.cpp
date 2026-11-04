#define DSIM_DYNAMIC_ARRAYS_ENABLED 1
#define DSIM_QUEUES_ENABLED 1
#define DSIM_ASSOCIATIVE_ARRAYS_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
int main() {
 Sim s;int q=s.signal(96,false),a=s.signal(96,false);
 s.queue_method(q,0,V(0),V::ones(96),96,false,-1);
 s.associative_write(a,V(uint32_t(-7),0,32),V::x(96),96,false);
 auto before=s.checkpoint();
 s.queue_method(q,1,V(0),V(13,0,96),96,false,-1);
 s.associative_write(a,V(uint32_t(-7),0,32),V(9,0,96),96,false);
 auto full=s.checkpoint();
 s.queue_method(q,6,V(0),V(0),96,false,-1);s.associative_delete(a,V(0),true,96);
 assert(s.dynamic_size(q)==0&&s.associative_size(a)==0);
 s.restore(before);assert(s.dynamic_size(q)==1&&s.dynamic_read(q,V(0),96,false).same(V::ones(96)));
 assert(s.associative_read(a,V(uint32_t(-7),0,32),96,false).same(V::x(96)));
 s.restore(full);assert(s.dynamic_size(q)==2&&s.dynamic_read(q,V(0),96,false).a==13);
 assert(s.associative_read(a,V(uint32_t(-7),0,32),96,false).a==9);
 V key(123,0,32);assert(s.associative_cursor(a,key,0)&&int32_t(key.a)==-7);
 assert(!s.associative_cursor(a,key,3)&&int32_t(key.a)==-7);
 assert(!s.associative_exists(a,V::x(32)));
 bool failed=false;try{s.associative_write(a,V::x(32),V(1),96,false);}catch(const std::runtime_error&){failed=true;}assert(failed);
 std::cout<<"PASS queue and associative value/checkpoint isolation\n";
}
