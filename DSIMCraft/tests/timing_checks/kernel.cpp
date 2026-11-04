#define DSIM_TIMING_ENABLED 1
#define DSIM_CHECKS_ENABLED 1
#define DSIM_PATH_ENABLED 1
#define DSIM_COMPACT_GATES 1
#include <dsim/runtime.hpp>
#include <dsim/path.hpp>
#include <array>
#include <cassert>
using namespace dsim;
struct Context { TimingCheckState window;std::vector<std::array<int,3>> changes; };
static const RuntimeTimingCheck descriptor{0,0,1,0,0,1023,205,4,5,5,0,"cell=test"};
static void change(Sim& s,void* raw,uint32_t role,int before,int after) {
    auto& context=*static_cast<Context*>(raw);context.changes.push_back({int(role),before,after});
    context.window.change(s,descriptor,int(role),before,after,true);
}
int main() {
    std::ostringstream text;auto old=std::cout.rdbuf(text.rdbuf());
    for(bool compact:{false,true}) {
        Sim s;int data=compact?s.compact_net():s.signal(1,true),clock=s.signal(1,true);
        s.set(data,V(0));s.set(clock,V(0));auto context=std::make_shared<Context>();auto id=s.compiled_context(context);
        s.timing_watch(data,id,change,0);s.timing_watch(clock,id,change,1);
        s.run_until(100);s.set(data,V(1));s.run_until(102);s.set(clock,V(1));
        assert(context->window.reference_time==102);auto before=text.str();assert(before.find("kind=SETUP time=102")!=std::string::npos);
        auto changes=context->changes;
        bool accepted=s.predict_until(104,[&](Sim& probe){probe.set(data,V(0));probe.set(data,V(1));probe.set(data,V::x(1));probe.set(data,V::z(1));},[](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&context->changes==changes&&context->window.data_time==100&&text.str()==before);
        s.run_until(105);s.set(data,V(0));s.set(data,V(1));s.set(data,V::x(1));s.set(data,V::z(1));
        assert(context->changes.size()==changes.size()+4);assert(context->changes.back()==(std::array<int,3>{0,2,3}));
        assert(context->window.data_time==105);
        auto state=context->window;auto count=context->changes.size();before=text.str();
        accepted=s.predict_until(110,[&](Sim& probe){probe.set(data,V(0));},[](const Sim&){return true;},[](Sim&){});
        assert(accepted&&context->changes.size()==count+1&&text.str()!=before&&state.reference_time==context->window.reference_time);
    }
    // Sparse observers on interleaved ordinary and compact IDs: gaps must not
    // alias a group, and duplicate observers retain registration order.
    {
        Sim s;std::vector<int> normal,compact;
        for(int i=0;i<4096;++i){normal.push_back(s.signal(1,false));compact.push_back(s.compact_net());}
        auto state=std::make_shared<Context>();auto id=s.compiled_context(state);
        auto collect=[](Sim&,void* raw,uint32_t role,int a,int b){
            static_cast<Context*>(raw)->changes.push_back({int(role),a,b});
        };
        for(int index:{4090,2,2048,0}) {
            s.timing_watch(normal[index],id,collect,uint32_t(index));
            s.timing_watch(compact[index],id,collect,uint32_t(index+10000));
            s.timing_watch(normal[index],id,collect,uint32_t(index+20000));
        }
        std::vector<std::array<int,3>> expected;
        for(int i=0;i<4096;++i){
            s.set(normal[i],V(1));s.set(compact[i],V(0));
            if(i==4090||i==2||i==2048||i==0){
                expected.push_back({i,2,1});expected.push_back({i+20000,2,1});expected.push_back({i+10000,3,0});
            }
        }
        assert(state->changes==expected);
        auto cp=s.checkpoint();s.set(normal[2],V(0));s.restore(cp);
        assert(state->changes==expected);s.set(compact[2],V(1));
        expected.push_back({10002,0,1});assert(state->changes==expected);
    }
    std::cout.rdbuf(old);std::cout<<"PASS per-change compact/generic X/Z checks, checkpoint history, rejected diagnostic transaction and accepted commit\n";
}
