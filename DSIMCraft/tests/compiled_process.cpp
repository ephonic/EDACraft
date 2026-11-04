#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
struct Model {
    int output=0,seed=0,timer=0,commit=0,site=0,count=0;
    std::vector<std::string> trace;
};
static void evaluate(Sim& s,void* context,uint32_t payload) {
    auto& m=*static_cast<Model*>(context);
    auto record=[&](std::string text){m.trace.push_back(text+"@"+std::to_string(s.now));};
    if(payload==0) {
        record("sample");s.assign_nba(m.output,V(m.seed,0,8));s.enqueue_nba(m.commit);
        s.delay(m.timer,0);s.delay(m.timer,3);
    } else if(payload==1)record("commit"+std::to_string(s.get(m.output).a));
    else if(payload==2) {record("timer"+std::to_string(++m.count));s.set(m.output,V(10+m.count,0,8));}
    else {record("watch");s.arm_wait(m.site);}
}
int main() {
    Sim s;int trigger=s.signal(1,false);s.set(trigger,V(0));
    auto a=std::make_shared<Model>(),b=std::make_shared<Model>();
    a->output=s.signal(8,false);b->output=s.signal(8,false);a->seed=1;b->seed=7;
    int generic=-1;
    generic=s.process([&,a,pc=0]() mutable {
        a->trace.push_back("generic"+std::to_string(pc)+"@"+std::to_string(s.now));
        if(pc++==0)s.delay(generic,2);else s.set(trigger,V(1));
    });
    auto ca=s.compiled_context(a),cb=s.compiled_context(b);
    auto ha=s.compiled_handler(ca,evaluate),hb=s.compiled_handler(cb,evaluate);
    auto install=[&](std::shared_ptr<Model> m,uint32_t handler) {
        int sample=s.compiled_process(handler,0);m->commit=s.compiled_process(handler,1);
        m->timer=s.compiled_process(handler,2);int watch=s.compiled_process(handler,3);
        m->site=s.add_wait_site(watch,{{trigger,0}});s.arm_wait(m->site);return sample;
    };
    int sa=install(a,ha),sb=install(b,hb);
    auto fails=[](auto action){bool failed=false;try{action();}catch(const std::exception&){failed=true;}assert(failed);};
    fails([&]{s.compiled_context(std::shared_ptr<Model>{});});
    fails([&]{s.compiled_handler(UINT32_MAX,evaluate);});
    fails([&]{s.compiled_handler(ca,nullptr);});
    fails([&]{s.compiled_process(UINT32_MAX,0);});
    std::weak_ptr<Model> owned=b;b.reset();assert(!owned.expired());
    s.enqueue(generic);s.enqueue(sa);s.enqueue(sb);auto cp=s.checkpoint();
    const std::vector<std::string> expected_a={"generic0@0","sample@0","timer1@0","commit1@0","generic1@2","watch@2","timer2@3"};
    const std::vector<std::string> expected_b={"sample@0","timer1@0","commit7@0","watch@2","timer2@3"};
    auto check=[&]{assert(a->trace==expected_a&&owned.lock()->trace==expected_b);assert(a->count==2&&owned.lock()->count==2);assert(s.get(a->output).same(V(12,0,8))&&s.get(owned.lock()->output).same(V(12,0,8)));};
    s.run_until(4);check();
    for(int i=0;i<2;++i){s.restore(cp);assert(a->trace.empty()&&owned.lock()->trace.empty());s.run_until(4);check();}
    s.restore(cp);
    bool accepted=s.predict_until(4,[&](Sim& sim){sim.set(trigger,V(1));},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted);check();s.restore(cp);
    accepted=s.predict_until(4,[](Sim&){},[](const Sim&){return true;},[](Sim&){assert(false);});assert(accepted);check();
    fails([&]{s.compiled_context(std::make_shared<Model>());});
    fails([&]{s.compiled_handler(ca,evaluate);});fails([&]{s.compiled_process(ha,0);});
    std::weak_ptr<Model> lifetime;
    {Sim owner;auto state=std::make_shared<Model>();lifetime=state;owner.compiled_context(state);state.reset();assert(!lifetime.expired());}
    assert(lifetime.expired());
    // A dense instance population shares one model context and handler. Its
    // independently computed arithmetic checksum also checks all payload bits.
    struct Sum {uint64_t sum=0;};Sim dense;auto sum=std::make_shared<Sum>();
    auto context=dense.compiled_context(sum);
    auto handler=dense.compiled_handler(context,+[](Sim&,void* p,uint32_t value){static_cast<Sum*>(p)->sum+=value;});
    for(uint32_t i=0;i<100000;++i)dense.enqueue(dense.compiled_process(handler,i));
    dense.run();assert(sum->sum==uint64_t(99999)*100000/2);
    std::cout<<"PASS compiled/generic dispatch, owned contexts, multiple models, payloads, Active/Inactive/NBA/timers/watches, mutable PCs, reusable checkpoints, prediction replay; sizeof(Process)="<<sizeof(Process)<<'\n';
}
