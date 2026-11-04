#ifndef DSIM_RUNTIME_HEADER
#define DSIM_RUNTIME_HEADER "dsim/runtime.hpp"
#endif
#include DSIM_RUNTIME_HEADER
#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <new>

static bool count_allocations=false;
static size_t allocation_calls=0;
void* operator new(std::size_t size) {
    if(void* p=std::malloc(size?size:1)) {
        if(count_allocations) ++allocation_calls;
        return p;
    }
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p,std::size_t) noexcept { std::free(p); }
void operator delete[](void* p,std::size_t) noexcept { std::free(p); }

int main(int argc,char**) {
    using namespace dsim;
    Sim s;
    int clk=s.signal(1,false),q=s.signal(64,false);
    s.set(clk,V(0)); s.set(q,V(0,0,64));
    uint64_t ticks=0,target=64,wakes=0;
    bool initialized=false,bit=false;
    int observer=-1,clock=-1,site=-1;
    observer=s.process([&] {
        if(initialized) { ++wakes; s.assign_nba(q,V(wakes,0,64)); }
        initialized=true;
#ifdef DSIM_SCHEDULER_BASELINE
        s.wait(observer,{{clk,1}});
#else
        s.arm_wait(site);
#endif
    });
    clock=s.process([&] {
        bit=!bit; s.set(clk,V(bit)); ++ticks;
        if(ticks<target) s.delay(clock,1);
    });
#ifndef DSIM_SCHEDULER_BASELINE
    site=s.add_wait_site(observer,{{clk,1}});
#else
    (void)site;
#endif
    s.enqueue(observer); s.enqueue(clock); s.run();
    assert(wakes==32 && s.get(q).a==32);
    target+=20000;
    count_allocations=true;
    s.enqueue(clock); s.run();
    count_allocations=false;
    assert(wakes==10032 && s.get(q).a==10032 && ticks==target);
    std::printf("PASS 10000 warmed clock/edge/NBA cycles; C++ allocation calls=%zu\n",allocation_calls);
    // An explicit report-only invocation permits measuring the old runtime.
    if(argc==1) assert(allocation_calls==0);
}
