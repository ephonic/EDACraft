#define DSIM_TIMING_ENABLED 1
#define DSIM_SCALAR_TIMING_ENABLED 1
#define DSIM_SDF_JOBS_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <tuple>
using namespace dsim;
using Record=std::tuple<uint64_t,uint32_t,int>;
struct Model {
    bool jobs=false;
    int source=0,alias=0;
    uint32_t channels[2]{};
    int sites[2]{};
    unsigned calls[2]{};
    std::vector<Record> history;
};
static V bit(int code) {return code==2?V::x(1):code==3?V::z(1):V(code,0,1);}
static void changed(void* raw,uint64_t time,int signal,V value) {
    static_cast<Model*>(raw)->history.emplace_back(time,uint32_t(signal)^0x80000000u,value.bit(0));
}
static void tick(void*,uint64_t) {}
static int net(Sim& s,bool compact) {
#ifdef DSIM_COMPACT_GATES
    if(compact)return s.compact_net();
#else
    (void)compact;
#endif
    return s.signal(1,true);
}
template<class F> static void rejects(F fn) {
    bool rejected=false;try {fn();}catch(const std::exception&){rejected=true;}assert(rejected);
}
static auto install(Sim& s,bool jobs,bool compact,bool start=true) {
    auto state=std::make_shared<Model>();state->jobs=jobs;
    state->source=net(s,compact);state->alias=net(s,compact);
    s.connect_net(state->source,0,state->alias,0);
    for(int i=0;i<2;++i)state->channels[i]=s.delayed_driver(net(s,compact),100+i,Sim::DelayPolicy::ReplacePending);
    auto context=s.compiled_context(state);
    auto marker=s.compiled_handler(context,+[](Sim& q,void* raw,uint32_t tag){
        auto& m=*static_cast<Model*>(raw);
        m.history.emplace_back(q.now,tag,q.get_scalar(m.source));
        if(tag==100)q.drive(m.source,1,V(0,0,1));
    });
    auto handler=s.compiled_handler(context,+[](Sim& q,void* raw,uint32_t index){
        auto& m=*static_cast<Model*>(raw);
        if(!m.jobs)q.arm_fixed_wait(m.sites[index]);
        int value=q.get_scalar(index?m.alias:m.source);
        m.history.emplace_back(q.now,index+1,value);
        ++m.calls[index];
        q.drive_scalar_after(m.channels[index],uint8_t(value),index?0:5);
        // Rearming before the callback must preserve a self-triggered next job.
        if(!index&&m.calls[index]==1)q.drive(m.source,1,V(1,0,1));
    });
    s.compiled_process(marker,100);
    for(int i=0;i<2;++i) {
        int input=i?state->alias:state->source;
        if(jobs)s.compiled_sdf_job(handler,uint32_t(i),input);
        else {
            auto p=s.compiled_process(handler,uint32_t(i));
            state->sites[i]=s.add_fixed_wait(p,{{input,0}});
        }
        s.compiled_process(marker,uint32_t(200+100*i));
    }
    if(start) {
        s.attach_wave(state.get(),changed,tick);
        s.finish_connections();
        s.initialize_sdf_jobs_and_processes();
    }
    return state;
}
struct Result {std::vector<Record> history;uint64_t steps;};
static Result scenario(bool jobs,bool compact,int prediction) {
    Sim s;auto m=install(s,jobs,compact);
    assert(s.processes.size()==size_t(jobs?3:5));
    s.run_until(0);
    std::vector<uint32_t> tags;
    for(auto [time,tag,value]:m->history)if(tag<1000){(void)time;(void)value;tags.push_back(tag);}
    assert((tags==std::vector<uint32_t>{100,1,200,2,300,1}));
    // Sample several changes before the awakened work runs; both backends
    // coalesce to the latest value but retain their original FIFO position.
    s.drive(m->source,1,V(0,0,1));s.drive(m->source,1,V::x(1));s.drive(m->source,1,V::z(1));
    if(prediction) {
        const auto before=m->history;
        auto accepted=s.predict_until(3,[&](Sim& q){q.drive(m->source,1,V(1,0,1));},
            [prediction](const Sim&){return prediction==2;},[](Sim&){});
        assert(accepted==(prediction==2));
        if(prediction==1)assert(m->calls[0]==3&&m->calls[1]==2);
        assert(m->history.size()>before.size());
    } else s.run_until(3);
    s.run_until(10);
    for(int code:{0,1,2,3,0}) {
        s.drive(m->source,1,bit(code));s.run_until(s.now+1);
    }
    // A rejected speculative zero-time loop/exception must restore queued,
    // armed and context state. Wave effects from that attempt are discarded.
    auto before=m->history;
    rejects([&]{s.predict_until(s.now+2,[&](Sim& q){
        q.drive(m->source,1,V::x(1));throw std::runtime_error("abort prediction");
    },[](const Sim&){return true;},[](Sim&){});});
    assert(m->history==before);
    s.run();
    return {m->history,s.executed_steps()};
}
int main() {
    static_assert(sizeof(Ready)==8,"job tag must use Ready padding");
    for(bool compact:{false,true})for(int prediction:{0,1,2}) {
        auto baseline=scenario(false,compact,prediction),candidate=scenario(true,compact,prediction);
        assert(baseline.history==candidate.history&&baseline.steps==candidate.steps);
    }
    // Checkpoints include jobs awakened but not yet run, even when several
    // model scopes share a kernel and reuse the same handler payload indices.
    {
        Sim s;auto a=install(s,true,false,false);auto b=install(s,true,false,false);
        s.attach_wave(b.get(),changed,tick);s.finish_connections();s.initialize_sdf_jobs_and_processes();
        s.run_until(1);s.drive(a->source,1,V::x(1));s.drive(b->source,1,V::z(1));
        // Manual checkpoints cannot rewind a wave sink; use a transaction.
        bool accepted=s.predict_until(20,[&](Sim& q){q.drive(a->source,1,V(0,0,1));},
            [](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&a->calls[0]>=3&&b->calls[0]>=3);
    }
    {
        Sim s;auto m=install(s,true,false);s.run_until(0);
        s.attach_wave(nullptr,nullptr,nullptr);
        s.drive(m->source,1,V::z(1));auto checkpoint=s.checkpoint();
        s.run_until(20);const auto expected=m->history;
        for(int repeat=0;repeat<3;++repeat) {
            s.restore(checkpoint);s.run_until(20);assert(m->history==expected);
        }
    }
#ifdef DSIM_BATCH_ENABLED
    // A job between two same-handler gate processes is a FIFO boundary. It
    // must not be mistaken for a process ID by the batch prefix scanner.
    for(bool finish:{false,true})for(bool limited:{false,true}) {
        Sim s;auto order=std::make_shared<std::vector<uint32_t>>();
        auto context=s.compiled_context(order);
        auto batch=s.compiled_handler(context,+[](Sim& q,void* raw,uint32_t first){
            auto& order=*static_cast<std::vector<uint32_t>*>(raw);
            // The first installed handler is the batch handler in this kernel.
            q.compiled_batch(0,first,[&](uint32_t value){order.push_back(value);});
        });
        assert(batch==0);
        auto job=s.compiled_handler(context,finish?
            +[](Sim& q,void* raw,uint32_t value){static_cast<std::vector<uint32_t>*>(raw)->push_back(value);q.finished=true;}:
            +[](Sim&,void* raw,uint32_t value){static_cast<std::vector<uint32_t>*>(raw)->push_back(value);});
        int input=s.signal(1,false);
        s.compiled_process(batch,1);s.compiled_sdf_job(job,2,input);s.compiled_process(batch,3);
        s.initialize_sdf_jobs_and_processes();
        if(limited){s.limit=1;rejects([&]{s.run();});s.limit=100;}
        s.run();assert((*order==(finish?std::vector<uint32_t>{1,2}:std::vector<uint32_t>{1,2,3})));
        assert(s.executed_steps()==uint64_t((finish?2:3)+(limited?1:0)));
    }
#endif
    // Invalid registrations leave the valid model usable and do not consume
    // a job position or process record. Topology is immutable after execution.
    {
        Sim s;int n=s.signal(1,false);
        auto model=std::make_shared<unsigned>(0);auto context=s.compiled_context(model);
        auto handler=s.compiled_handler(context,+[](Sim&,void* raw,uint32_t){++*static_cast<unsigned*>(raw);});
        rejects([&]{s.compiled_sdf_job(UINT32_MAX,0,n);});
        rejects([&]{s.compiled_sdf_job(handler,0,12345);});
        int wide=s.signal(8,false);rejects([&]{s.compiled_sdf_job(handler,0,wide);});
        s.compiled_sdf_job(handler,0,n);s.initialize_sdf_jobs_and_processes();s.run_until(0);
        assert(*model==1&&s.processes.empty());
        s.set(n,V(1,0,1));s.set(n,V(0,0,1));s.run();assert(*model==2);
        s.freeze_topology();rejects([&]{s.compiled_sdf_job(handler,0,n);});
    }
    std::cout<<"PASS SDF jobs: initialization interleaving, self-wake, FIFO/coalescing, four states, aliases, pending deliveries, exact steps, prediction/exception rollback, owned scopes, guards\n";
}
