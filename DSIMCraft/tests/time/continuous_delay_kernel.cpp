#define DSIM_CONTINUOUS_VARIABLE_ENABLED 1
#define DSIM_TWO_STATE_ENABLED 1
#define DSIM_TIMING_ENABLED 1
#define DSIM_CONTINUOUS_DELAY_ENABLED 1
#define DSIM_DELAYED_NBA_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <iostream>
using namespace dsim;

static V bit(int code) {return code==2?V::x(1):code==3?V::z(1):V(code);}
static uint32_t channel(Sim& s,int id,int driver=1) {
    auto ch=s.continuous_driver({{id,0,s.get(id).w,0,driver}},s.get(id).w);
    return ch;
}
int main() {
    // Variable channels exercise scalar timing as well as vector/compact paths.
    for(int width:{1,8,130}) {
        Sim s;int q=s.signal(width,false);auto c=s.continuous_driver({{q,0,width,0,-1}},width);
        s.finish_connections();s.initialize_continuous(c);assert(s.get(q).same(V::x(width)));
        s.drive_continuous(c,V(1,0,width),2,2,2,width==1);s.run_until(1);
        auto checkpoint=s.checkpoint();s.run_until(2);assert(s.get(q).same(V(1,0,width)));
        s.drive_continuous(c,V(0,0,width),2,2,2,width==1);s.run_until(3);
        s.drive_continuous(c,V(1,0,width),2,2,2,width==1);s.run();assert(s.get(q).same(V(1,0,width)));
        s.restore(checkpoint);s.run();assert(s.get(q).same(V(1,0,width)));
    }
    {
        Sim s;int v=s.signal(8,false),n=s.signal(4,true),b=s.signal_two_state(4);
        auto c=s.continuous_driver({{v,4,4,8,-1},{n,0,4,4,10},{b,0,4,0,-1}},12);
        auto other=s.continuous_driver({{v,0,4,0,-1}},4); // legal disjoint variable channels
        s.finish_connections();s.initialize_continuous(c);
        s.drive_continuous(c,V(0xa31,0,12),2,2,2,false);
        s.drive_continuous(other,V(1,0,4),2,2,2,false);s.run();
        assert(s.get(v).same(V(0xa1,0,8))&&s.get(n).same(V(3,0,4))&&s.get(b).same(V(1,0,4)));
    }
    // All four-state transitions; explicit IEEE mode keeps vector selection.
    for(bool scalar:{false,true})for(int from=0;from<4;++from)for(int to=0;to<4;++to) {
        Sim s;int q=s.signal(1,true);auto ch=channel(s,q);
        s.finish_connections();s.initialize_continuous(ch);
        assert(s.get(q).bit(0)==2);
        s.drive_continuous(ch,bit(from),1,1,1,scalar);s.run_until(1);
        assert(s.get(q).bit(0)==from);
        s.drive_continuous(ch,bit(to),7,11,5,scalar);
        const uint64_t dt=to==0?11:to==3?5:to==2
#ifdef DSIM_CONTINUOUS_DELAY_IEEE_MODE
            &&scalar
#endif
            ?5:7;
        s.run_until(dt);assert(s.get(q).bit(0)==from);
        s.run_until(dt+1);assert(s.get(q).bit(0)==to);
    }
    {
        Sim s;int q=s.signal(1,true);auto ch=channel(s,q);
        s.finish_connections();s.initialize_continuous(ch);
        s.drive_continuous(ch,V(0),0,0,0,true);s.run_until(0);
        s.drive_continuous(ch,V(1),5,5,5,true);s.run_until(2);
        s.drive_continuous(ch,V(1),5,5,5,true);s.run_until(5);
        assert(s.get(q).bit(0)==1); // same RHS cannot postpone an event
        s.drive_continuous(ch,V(0),5,5,5,true);s.run_until(6);
        s.drive_continuous(ch,V(1),5,5,5,true);s.run();
        assert(s.get(q).bit(0)==1&&s.now==6); // canceled timers do not move time
    }
    {
        Sim s;int q=s.signal(8,true),alias=s.signal(8,true);
        for(int i=0;i<8;++i)s.connect_net(q,i,alias,i);
        auto ch=s.continuous_driver({{q,4,4,4,1},{q,0,4,0,2}},8);
        s.finish_connections();s.initialize_continuous(ch);
        s.drive_continuous(ch,V(0x12,0,8),3,3,3,false);s.run_until(3);
        auto cp=s.checkpoint();
        for(int i=0;i<100;++i) {
            s.drive_continuous(ch,V(0xa5,0,8),3,3,3,false);s.run_until(4);
            s.drive_continuous(ch,V(0x12,0,8),3,3,3,false);s.run();
            assert(s.get(q).same(V(0x12,0,8))&&s.get(alias).same(s.get(q)));
            s.restore(cp);
        }
        // Cancellation is independent of the resolved value of another driver.
        s.drive(q,99,V(0xff,0,8));
        s.drive_continuous(ch,V(0xff,0,8),3,3,3,false);s.run_until(4);
        s.drive_continuous(ch,V(0x12,0,8),3,3,3,false);s.run_until(8);
        s.drive(q,99,V::z(8));assert(s.get(q).same(V(0x12,0,8)));
    }
    {
        Sim s;int q=s.signal(257,true),q2=s.signal(1,true);
        auto ch=channel(s,q);auto direct=s.delayed_driver(q2,9,Sim::DelayPolicy::ReplacePending);
        s.finish_connections();s.initialize_continuous(ch);
        auto value=V::ones(257);s.drive_continuous(ch,value,4,7,2,false);
        s.drive_after(direct,V(1),3);
        auto cp=s.checkpoint();s.run_until(8);
        assert(s.get(q).same(value)&&s.get(q2).bit(0)==1);
        s.restore(cp);s.run_until(2);assert(s.get(q).same(V::x(257)));
        s.run_until(8);assert(s.get(q).same(value)&&s.get(q2).bit(0)==1);
    }
    {
        Sim s;int q=s.signal(1,true);auto ch=channel(s,q);
        s.finish_connections();s.initialize_continuous(ch);s.now=UINT64_MAX-5;
        s.drive_continuous(ch,V(0),3,3,3,true);s.run_until(UINT64_MAX-4);
        bool rejected=false;
        try {s.drive_continuous(ch,V(1),10,10,10,true);}catch(const std::runtime_error&){rejected=true;}
        assert(rejected);s.run();assert(s.get(q).bit(0)==0&&s.now==UINT64_MAX-2);
    }
#ifdef DSIM_COMPACT_GATES
    {
        Sim s;int q=s.compact_net();auto ch=channel(s,q);
        s.finish_connections();s.initialize_continuous(ch);
        s.drive_continuous(ch,V(1),3,5,2,true);s.run();assert(s.get(q).bit(0)==1);
    }
#endif
    std::cout<<"PASS continuous channels: 32 transitions, vector/scalar selection, pulse/dedup, parts/aliases/multidrivers, 257 bits, mixed timing, checkpoint reuse and overflow\n";
}
