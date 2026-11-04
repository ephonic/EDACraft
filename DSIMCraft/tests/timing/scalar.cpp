#define DSIM_TIMING_ENABLED 1
#define DSIM_COMPACT_GATES 1
#define DSIM_WIDE_VALUES 1
#define DSIM_WAVE_ENABLED 1
#define DSIM_PATH_ENABLED 1
#include <dsim/parallel.hpp>
#include <dsim/path.hpp>
#include <cassert>
#include <tuple>
using namespace dsim;
using Trace=std::vector<std::tuple<uint64_t,int,std::string>>;
static V bit(uint8_t code){return code<2?V(code,0,1):code==2?V::x(1):V::z(1);}
static void issue(Sim& s,uint32_t ch,uint8_t code,uint64_t dt) {
#ifdef DSIM_SCALAR_TIMING_ENABLED
    s.drive_scalar_after(ch,code,dt);
#else
    s.drive_after(ch,bit(code),dt);
#endif
}
static void changed(void* raw,uint64_t t,int id,V v) {
    static_cast<Trace*>(raw)->emplace_back(t,id,format(v,'b'));
}
static void tick(void*,uint64_t){}
template<class F> static void rejects(F fn) {
    bool caught=false;try{fn();}catch(const std::exception&){caught=true;}assert(caught);
}
static V wide(uint64_t seed) {
    return V::from_words({{seed,0},{0,~uint64_t(0)},{seed<<1,0},{~seed,0},{1,0}},257);
}
static void mixed() {
    Sim s;int a=s.compact_net(),b=s.signal(1,true),w=s.signal(257,true);
    s.set(a,V::z(1));
    auto ca=s.delayed_driver(a,1,Sim::DelayPolicy::PreserveTransitions);
    auto cb=s.delayed_driver(b,2,Sim::DelayPolicy::PreserveTransitions);
    auto cw=s.delayed_driver(w,3,Sim::DelayPolicy::PreserveTransitions);
    Trace trace;s.attach_wave(&trace,changed,tick);
    issue(s,ca,0,0);s.drive_after(cw,V::z(257),0);issue(s,cb,3,0);s.run_until(0);
    const auto one=wide(7),two=wide(31);
    issue(s,ca,2,2);s.drive_after(cw,one,2);issue(s,cb,1,2);
    s.drive_after(cw,two,3);issue(s,cb,2,3);issue(s,ca,1,4);s.run_until(1);
#ifdef DSIM_SCALAR_TIMING_ENABLED
    rejects([&]{s.get_scalar(w);});rejects([&]{s.drive_scalar_after(cw,1,0);});
    rejects([&]{s.drive_scalar_after(ca,4,0);});
    assert(s.get_scalar(a)==0&&s.get_scalar(b)==3);
#endif
    auto accepted=s.predict_until(5,[&](Sim& q){
        q.cancel_delayed(cw);q.drive_after(cw,wide(99),0);
        issue(q,ca,3,0);issue(q,cb,0,2);
    },[](const Sim&){return false;},[](Sim&){});
    const Trace expected={{0,a,"0"},{2,a,"x"},{2,w,format(one,'b')},{2,b,"1"},
                          {3,w,format(two,'b')},{3,b,"x"},{4,a,"1"}};
    assert(!accepted&&trace==expected&&s.get(w).same(two));
    assert(s.path_stamp(a).time==4&&s.path_stamp(a).after==1);
    s.attach_wave(nullptr,nullptr,nullptr);
    auto cp=s.checkpoint();
    for(int i=0;i<100;++i) {
        s.restore(cp);s.drive_after(cw,wide(uint64_t(i)),7);s.cancel_delayed(cw);
        issue(s,ca,3,1);s.drive_after(cw,wide(123),2);issue(s,cb,0,2);
        s.run();assert(s.now==7&&s.get(a).same(V::z(1))&&s.get(b).same(V(0))&&s.get(w).same(wide(123)));
    }
    s.restore(cp);s.drive_after(cw,wide(51),2);
    rejects([&]{s.drive_after(cw,wide(71),UINT64_MAX);});
    s.run();assert(s.now==7&&s.get(w).same(wide(51)));
}
static void finish(size_t workers,uint64_t window) {
    ConservativeSim machine(workers,window);machine.enable_global_finish();
    auto p=machine.partition(),q=machine.partition();auto& a=machine.kernel(p);auto& b=machine.kernel(q);
    int x=a.compact_net(),w=a.signal(257,true);a.set(x,V::z(1));
    auto scalar=a.delayed_driver(x,1,Sim::DelayPolicy::ReplacePending);
    auto vector=a.delayed_driver(w,2,Sim::DelayPolicy::PreserveTransitions);
    // One live scalar transition, one rejected pulse, wide pending values and
    // a future exception all lie in the private execution of a large window.
    int first=a.process([&]{issue(a,scalar,0,0);a.drive_after(vector,wide(11),2);});a.enqueue(first);
    int pulse=a.process([&]{issue(a,scalar,1,4);issue(a,scalar,0,5);});a.delay(pulse,1);
    int later=a.process([&]{issue(a,scalar,1,1);a.drive_after(vector,wide(23),1);});a.delay(later,3);
    int stop=b.process([&]{b.finished=true;});b.delay(stop,5);
    int fail=a.process([]{throw std::runtime_error("beyond finish");});a.delay(fail,9);
    Trace trace;a.attach_wave(&trace,changed,tick);
    machine.run_until(20);assert(machine.finished()&&machine.finish_time()==5);
    const Trace expected={{0,x,"0"},{2,w,format(wide(11),'b')},{4,x,"1"},{4,w,format(wide(23),'b')}};
    assert(trace==expected&&a.get(x).same(V(1))&&a.get(w).same(wide(23)));
}
int main() {
    mixed();for(auto workers:{1,2,4})for(uint64_t window:{1,2,7,1024})finish(size_t(workers),window);
    std::cout<<"PASS mixed scalar/vector timing: explicit FIFO timeline, X/Z, 257 bits, pool reuse, invalid requests, path stamps, prediction and global finish\n";
}
