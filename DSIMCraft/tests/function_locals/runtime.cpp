#define DSIM_FORCE_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_MIXED_STATE_ENABLED 1
#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
int main() {
    Sim s;
    int a=s.signal(32,false), b=s.signal(8,false), net=s.signal(1,true);
    assert(s.function_locals_ready({a,b})); // X/Z are valid cached values.
    assert(!s.integral_loop_ready({a,b}));
    s.set(a,V(12,0,32));s.set(b,V(3,0,8));
    assert(s.integral_loop_ready({a,b}));
    assert(!s.function_locals_ready({net}));
    assert(!s.function_locals_ready({-1}));
    assert(!s.function_locals_ready({1000}));
    s.force_value(a,7,V(99,0,32));
    assert(!s.function_locals_ready({a}));s.release_value(a);
    assert(s.function_locals_ready({a}));
    s.signals[size_t(a)].aliased=true;
    assert(!s.function_locals_ready({a}));s.signals[size_t(a)].aliased=false;
    s.set_state_mask(b,V(0xff,0,8));assert(!s.function_locals_ready({b}));
    int p=s.process([]{});s.wait(p,{{a,4}});
    assert(!s.function_locals_ready({a}));
    auto checkpoint=s.checkpoint();s.set(a,V(56,0,32));s.restore(checkpoint);
    assert(s.get(a).a==99&&!s.function_locals_ready({a}));
    std::cout<<"PASS scalar function storage guards and restore\n";
}
