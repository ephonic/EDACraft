// Explicit-delay kernel adapter for the existing VCS SDF micro-oracles.
// This deliberately does not parse or annotate SDF.
#define DSIM_TIMING_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
using namespace dsim;
struct Buffer {int input,site;uint32_t channel;bool twelve;int previous=2;};
static void evaluate(Sim& s,void* raw,uint32_t) {
    auto& m=*static_cast<Buffer*>(raw);s.arm_fixed_wait(m.site);V value=s.get(m.input);
    static const uint64_t delays[4][4]={{0,1000,7000,3000},{2000,0,9000,5000},{10000,8000,0,11000},{6000,4000,12000,0}};
    uint64_t dt=m.twelve?delays[m.previous][value.bit(0)]:2000;
    m.previous=value.bit(0);s.drive_after(m.channel,value,dt);
}
int main(int argc,char** argv) {
    assert(argc==2);std::string mode=argv[1];assert(mode=="replace"||mode=="preserve"||mode=="twelve");
    Sim s;s.set_time_precision(1000);int input=s.signal(1,false),output=s.signal(1,true);
    auto state=std::make_shared<Buffer>(Buffer{input,0,s.delayed_driver(output,11,
        mode=="preserve"?Sim::DelayPolicy::PreserveTransitions:Sim::DelayPolicy::ReplacePending),mode=="twelve",2});
    auto context=s.compiled_context(state);auto handler=s.compiled_handler(context,evaluate);
    int p=s.compiled_process(handler,0);state->site=s.add_fixed_wait(p,{{input,0}});s.enqueue(p);
    s.attach_wave(&output,+[](void* raw,uint64_t time,int signal,V value){
        if(signal==*static_cast<int*>(raw)&&time>=10000)std::cout<<"TRACE t="<<time<<" z="<<format(value,'b')<<'\n';
    },+[](void*,uint64_t){});
    auto event=[&](uint64_t t,int value){
        int p=s.process([&,value]{s.set(input,value==3?V::z(1):value==2?V::x(1):V(value));});s.delay(p,t);
    };
    if(mode=="twelve") {
        int values[]={0,1,3,2,0,2,1,2,3,0,3,1,0};
        for(int i=0;i<13;++i)event(10000+uint64_t(i)*50000,values[i]);
        s.run_until(630000);
    } else {event(10000,0);event(20000,1);event(21000,0);event(40000,1);event(45000,0);s.run_until(55000);}
}
