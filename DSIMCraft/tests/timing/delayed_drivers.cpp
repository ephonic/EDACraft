#define DSIM_TIMING_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <tuple>
using namespace dsim;
using Policy=Sim::DelayPolicy;
using Trace=std::vector<std::pair<uint64_t,std::string>>;
static void changed(void* context,uint64_t time,int,V value) {
    static_cast<Trace*>(context)->push_back({time,format(value,'b')});
}
static void tick(void*,uint64_t) {}
template<class F> static void fails(F fn) {bool caught=false;try{fn();}catch(const std::exception&){caught=true;}assert(caught);}
static V bit(int state,int width=1) {return state==3?V::z(width):state==2?V::x(width):V(state?mask(width):0,0,width);}
static int net(Sim& s,int width=1) {
#ifdef DSIM_COMPACT_GATES
    if(width==1){int id=s.compact_net();s.set(id,V::z(1));return id;}
#endif
    return s.signal(width,true);
}
int main() {
    // Every four-state/vector transition; equal requests do not postpone a
    // live event. Requests are sized to their net, including 64-bit values.
    for(int width:{1,64})for(auto policy:{Policy::ReplacePending,Policy::PreserveTransitions})
    for(int from=0;from<4;++from)for(int to=0;to<4;++to) {
        Sim s;int n=net(s,width);auto ch=s.delayed_driver(n,-31,policy);
        s.drive_after(ch,bit(from,width),0);s.run_until(0);
        assert(s.get(n).same(bit(from,width)));
        s.drive_after(ch,bit(to,width),5);s.run_until(2);
        s.drive_after(ch,bit(to,width),50);s.run_until(4);
        assert(s.get(n).same(bit(from,width)));s.run_until(5);
        assert(s.get(n).same(bit(to,width)));
    }
    // Positive and zero delay are asynchronous Active events. A zero delay
    // arrives after already-enqueued Active work and before that work's NBA.
    {
        Sim s;int n=net(s),v=s.signal(1,false);Trace trace;
        s.attach_wave(&trace,changed,tick);auto ch=s.delayed_driver(n,7,Policy::PreserveTransitions);
        int p=s.process([&]{assert(s.get(n).same(V::z(1)));s.assign_nba(v,V(1));});
        s.enqueue(p);s.drive_after(ch,V(0),0);assert(s.get(n).same(V::z(1)));
        s.run();assert((trace==Trace{{0,"0"},{0,"1"}}));
    }
    // Lazy cancellation of the final timer must not spuriously advance time.
    // Returning to the committed driver value rejects a short pending pulse.
    {
        Sim s;int n=net(s);auto ch=s.delayed_driver(n,0,Policy::ReplacePending);
        s.drive_after(ch,V(0),0);s.run_until(0);
        s.drive_after(ch,V(1),100);s.drive_after(ch,V(0),200);s.run();
        assert(s.now==0&&s.get(n).same(V(0)));
        s.drive_after(ch,V(1),0);s.cancel_delayed(ch);s.run();assert(s.get(n).same(V(0)));
        s.drive_after(ch,V(1),4);s.run();assert(s.now==4&&s.get(n).same(V(1)));
    }
    // Preserved transitions keep both edges, even when both arrive together.
    // A process timer shares the same timestamp; its body observes deliveries
    // already in Active before its timer wake has enqueued the process body.
    {
        Sim s;int n=net(s);Trace trace;s.attach_wave(&trace,changed,tick);
        auto ch=s.delayed_driver(n,0,Policy::PreserveTransitions);
        int p=s.process([&]{assert(s.get(n).same(V(0)));});s.delay(p,3);
        s.drive_after(ch,V(1),3);s.drive_after(ch,V(0),3);s.run();
        assert((trace==Trace{{3,"1"},{3,"0"}}));
    }
    // The two policies intentionally differ on a narrow pulse. Repeat many
    // times to exercise delivery-slot reuse rather than unbounded append.
    for(auto policy:{Policy::ReplacePending,Policy::PreserveTransitions}) {
        Sim s;int n=net(s);auto ch=s.delayed_driver(n,0,policy);
        s.drive_after(ch,V(0),0);s.run_until(0);
        for(uint64_t t=0;t<10000;t+=10) {
            s.drive_after(ch,V(1),2);s.run_until(t+1);s.drive_after(ch,V(0),2);
            s.run_until(t+2);assert(s.get(n).same(V(policy==Policy::PreserveTransitions?1:0)));
            s.run_until(t+10);assert(s.get(n).same(V(0)));
        }
    }
    // A fixed compiled process can continue sampling while its drive is
    // delayed; it never switches to the process delay/wait protocol.
    {
        Sim s;int input=s.signal(1,false),output=net(s);
        auto ch=s.delayed_driver(output,0,Policy::ReplacePending);
        struct State {int input,site;uint32_t channel;};
        auto state=std::make_shared<State>(State{input,0,ch});
        auto context=s.compiled_context(state);
        auto handler=s.compiled_handler(context,+[](Sim& q,void* raw,uint32_t){
            auto& m=*static_cast<State*>(raw);q.arm_fixed_wait(m.site);q.drive_after(m.channel,q.get(m.input),5);
        });
        int p=s.compiled_process(handler,0);state->site=s.add_fixed_wait(p,{{input,0}});
        s.set(input,V(0));s.enqueue(p);s.run_until(5);assert(s.get(output).same(V(0)));
        for(uint64_t t=6;t<=10;++t) {s.run_until(t);s.set(input,V(t%2==0?1:0));s.run_until(t);}
        assert(s.get(output).same(V(0)));s.run_until(15);assert(s.get(output).same(V(1)));
        assert(s.processes[p].generation==0&&s.processes[p].waiting);
    }
    // Resolution is per driver, never per resolved signal. Aliases and a
    // competing driver can obscure the channel's committed output.
    {
        Sim s;int n=net(s),alias=net(s);s.connect_net(n,0,alias,0);
        auto a=s.delayed_driver(n,-1,Policy::ReplacePending),b=s.delayed_driver(alias,7,Policy::PreserveTransitions);
        s.drive_after(a,V(0),0);s.drive_after(b,V(1),0);s.run_until(0);assert(s.get(n).same(V::x(1)));
        s.drive_after(a,V(1),8);s.drive_after(a,V(0),9);s.run();assert(s.now==0&&s.get(n).same(V::x(1)));
        s.drive_after(b,V::z(1),2);s.run();assert(s.get(alias).same(V(0))&&s.now==2);
    }
    // Both live and canceled events, an Active zero-delay event, the free-slot
    // list, per-driver values, input deduplication and generations are copied.
    for(int width:{1,8})for(auto policy:{Policy::ReplacePending,Policy::PreserveTransitions}) {
        Sim s;int n=net(s,width);auto a=s.delayed_driver(n,1,policy),b=s.delayed_driver(n,2,policy);
        s.drive_after(a,V(0x55,0,width),1);s.drive_after(b,V::z(width),1);s.run_until(1);
        s.drive_after(a,V(0xaa,0,width),2);s.cancel_delayed(a);
        s.drive_after(a,V(0x33,0,width),0);s.drive_after(b,V(0x77,0,width),5);
        auto cp=s.checkpoint();s.run_until(7);auto expected=s.get(n);
        s.cancel_delayed(a);s.cancel_delayed(b);s.drive_after(a,V(0,0,width),0);s.run();
        for(int i=0;i<3;++i) {s.restore(cp);s.run_until(7);assert(s.get(n).same(expected));}
        s.restore(cp);
        bool accepted=s.predict_until(7,[&](Sim& q){q.cancel_delayed(b);q.drive_after(a,V(0,0,width),1);},
            [](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&s.get(n).same(expected));
        s.restore(cp);accepted=s.predict_until(7,[](Sim&){},[](const Sim&){return true;},[](Sim&){assert(false);});
        assert(accepted&&s.get(n).same(expected));
        s.restore(cp);fails([&]{s.predict_until(7,[&](Sim& q){q.cancel_delayed(a);throw std::runtime_error("stop");},
            [](const Sim&){return true;},[](Sim&){});});
        assert(s.now==1);s.run_until(7);assert(s.get(n).same(expected));
    }
    // Rejected speculative deliveries must produce no waveform changes.
    {
        Sim s;int n=net(s);auto ch=s.delayed_driver(n,0,Policy::PreserveTransitions);Trace trace;
        s.attach_wave(&trace,changed,tick);s.drive_after(ch,V(0),2);s.drive_after(ch,V(1),4);
        bool accepted=s.predict_until(6,[&](Sim& q){q.cancel_delayed(ch);q.drive_after(ch,V::x(1),1);},
            [](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&(trace==Trace{{2,"0"},{4,"1"}}));
    }
    // Invalid requests cannot cancel a previously valid pending drive.
    {
        Sim s;int n=net(s),reg=s.signal(1,false);
        fails([&]{s.delayed_driver(reg,0,Policy::ReplacePending);});
        fails([&]{s.delayed_driver(n,0,static_cast<Policy>(99));});
        auto ch=s.delayed_driver(n,0,Policy::ReplacePending);
        fails([&]{s.delayed_driver(n,0,Policy::PreserveTransitions);});
        fails([&]{s.drive_after(99,V(1),0);});fails([&]{s.cancel_delayed(99);});
        s.run_until(1);s.drive_after(ch,V(1),3);
        fails([&]{s.drive_after(ch,V(0),UINT64_MAX);});s.run();assert(s.now==4&&s.get(n).same(V(1)));
        s.freeze_topology();
        fails([&]{s.delayed_driver(n,1,Policy::ReplacePending);});
    }
    std::cout<<"PASS delayed drivers: four states, vectors, asynchronous zero delay, Active/NBA/FIFO, pulses, cancellation, aliases/resolution, reusable checkpoints, prediction/wave isolation, errors\n";
}
