#define DSIM_TIME_WHEEL_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <iostream>
#include <queue>
#include <random>
#include <tuple>

struct Event {uint64_t time,order;int process;bool nba=false;};
struct Later {
    bool operator()(const Event& a,const Event& b) const {
        return std::tie(a.time,a.order)>std::tie(b.time,b.order);
    }
};
using Queue=dsim::NearTimerQueue<Event>;
using Reference=std::priority_queue<Event,std::vector<Event>,Later>;
static void equal(const Event& a,const Event& b) {
    assert(std::tie(a.time,a.order,a.process,a.nba)==std::tie(b.time,b.order,b.process,b.nba));
}
static void check(Queue& q,Reference& ref) {
    assert(q.size()==ref.size()&&q.empty()==ref.empty());
    if(!q.empty())equal(q.front(),ref.top());
}
static void drain(Queue q,Reference ref) {
    while(!ref.empty()){check(q,ref);equal(q.pop(),ref.top());ref.pop();}
    check(q,ref);
}
int main() {
    Queue q;Reference ref;uint64_t order=0,now=0;
    auto push=[&](uint64_t time,int process=0,bool nba=false) {
        Event e{time,order++,process,nba};q.push(e,now);ref.push(e);check(q,ref);
    };
    // Older far events must precede subsequently inserted near events at the
    // same timestamp, including wrap, the 255/256 boundary and huge idle gaps.
    for(uint64_t base:{uint64_t(0),uint64_t(1023),uint64_t(2048),uint64_t(65536),uint64_t(1)<<48}) {
        assert(q.empty());now=base;q.advance(now);
        for(uint64_t dt:{uint64_t(1),uint64_t(255),uint64_t(256),uint64_t(500),uint64_t(512)})push(now+dt);
        while(!ref.empty()) {
            now=ref.top().time;q.advance(now);
            if(now==base+255)push(base+500,-12,true);
            equal(q.pop(),ref.top());ref.pop();check(q,ref);
        }
    }
    // Removing a cancelled future timer must not advance the queue clock.
    now+=1000;q.advance(now);push(now+5000);equal(q.pop(),ref.top());ref.pop();
    push(now+2);drain(q,ref);equal(q.pop(),ref.top());ref.pop();
    // Full owned-state copies allow divergent execution and restoration.
    for(unsigned i=0;i<4096;++i)push(now+i%1024,int(i),i%2);
    Queue saved=q;Reference saved_ref=ref;uint64_t saved_now=now,saved_order=order;
    while(!ref.empty()){now=ref.top().time;q.advance(now);equal(q.pop(),ref.top());ref.pop();}
    q=saved;ref=saved_ref;now=saved_now;order=saved_order;
    push(now+3,999,true);drain(q,ref);
    // Randomly interleave timers, actual time advances, and cancelled-front
    // removal without advancing. Compare every visible minimum to std heap.
    q=Queue{};ref=Reference{};now=0;order=0;std::mt19937_64 rng(1018);
    for(unsigned i=0;i<1000000;++i) {
        if(ref.empty()||rng()%100<63) {
            uint64_t dt;
            switch(rng()%6){case 0:dt=0;break;case 1:dt=255;break;case 2:dt=256;break;
                case 3:dt=rng()%256;break;case 4:dt=rng()%65536;break;default:dt=rng()%(uint64_t(1)<<40);}
            push(now+dt,int(rng()%3000)-1500,rng()%2);
        } else {
            if(rng()%4){now=ref.top().time;q.advance(now);}
            equal(q.pop(),ref.top());ref.pop();check(q,ref);
        }
        if(i%100003==0)drain(q,ref);
    }
    drain(q,ref);
    // Arithmetic must work at the final uint64 timestamp, without base+width.
    q=Queue{};ref=Reference{};now=UINT64_MAX-1024;order=0;
    q.advance(now);push(UINT64_MAX);push(now+255);push(now+256);push(UINT64_MAX-1);
    while(!ref.empty()){now=ref.top().time;q.advance(now);equal(q.pop(),ref.top());ref.pop();check(q,ref);}
    bool rejected=false;try{q.push({now-1,order++,0,false},now);}catch(const std::runtime_error&){rejected=true;}
    assert(rejected);
    std::cout<<"PASS stable near/far ordering, promotion, cancellation, copies, 1000000 mixed operations, uint64 boundary\n";
}
