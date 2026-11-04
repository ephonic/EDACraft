#define DSIM_TIMING_ENABLED 1
#define DSIM_PATH_ENABLED 1
#define DSIM_CONDITIONAL_PATH_ENABLED 1
#include <dsim/runtime.hpp>
#include <dsim/path.hpp>
#include <cassert>
using namespace dsim;
static bool always(Sim&,const int*){return true;}
static bool enabled(Sim& s,const int* p){return s.get(p[1]).bit(0)!=0;}
static bool disabled(Sim& s,const int* p){return unary("!",s.get(p[1]),1).bit(0)!=0;}
static bool known_one(Sim& s,const int* p){return s.get(p[1]).bit(0)==1;}
static ConditionalModulePathArc arc(uint32_t input,uint32_t condition,uint64_t delay,bool fallback=false,int edge=0){
    ConditionalModulePathArc result{{input,uint8_t(edge),{}},0,condition,fallback};
    for(auto& d:result.path.delay)d=delay;
    return result;
}
int main(){
    for(bool compact:{false,true}){
        Sim s;auto net=[&](){
#ifdef DSIM_COMPACT_GATES
            if(compact)return s.compact_net();
#else
            (void)compact;
#endif
            return s.signal(1,true);
        };
        int p[]={net(),net(),net()};s.set(p[0],V(0));s.set(p[1],V(0));s.set(p[2],V(0));
        ModulePathCondition conditions[]={always,enabled,disabled,known_one};
        ConditionalModulePathArc paths[]={arc(0,1,7),arc(0,2,11),arc(0,0,19,true)};
        s.run_until(10);s.set(p[0],V(1));
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==11);
        // Selection is made when the output is to change, using current
        // conditions and the latest source timestamp, not captured input flags.
        s.run_until(12);s.set(p[1],V(1));
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==5);
        for(V value:{V::x(1),V::z(1)}){
            s.set(p[1],value);assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==5);
        }
        paths[1].condition=3;s.set(p[1],V::x(1));paths[0].condition=3;
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==17);
        assert(conditional_module_path_delay(s,p,paths,2,0,1,conditions)==0);
        // VCS uses ifnone when an enabled edge-qualified declaration does
        // not match this source transition.
        paths[0]=arc(0,1,7,false,2);s.set(p[1],V(1));
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==9); // second path is also enabled
        paths[1].condition=2;
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==17);
        // A different source's condition must not suppress this source's ifnone.
        paths[0]=arc(0,1,7);paths[1]=arc(2,2,3);s.set(p[1],V(0));
        s.set(p[2],V(1));assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==3);
        paths[1].condition=1;assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==17);
        auto cp=s.checkpoint();s.run_until(13);s.set(p[1],V(1));s.set(p[0],V(0));s.restore(cp);
        assert(s.now==12&&s.get(p[1]).bit(0)==0&&s.path_stamp(p[0]).time==10);
        assert(conditional_module_path_delay(s,p,paths,3,0,1,conditions)==17);
        bool accepted=s.predict_until(15,[&](Sim& q){q.set(p[1],V(1));q.set(p[0],V(0));},[](const Sim&){return false;},[](Sim&){});
        assert(!accepted&&s.get(p[1]).bit(0)==0&&s.path_stamp(p[0]).time==10);
        assert(conditional_module_path_delay(s,p,paths,3,1,1,conditions)==0);
        paths[2].path.delay[0]=UINT64_MAX;bool failed=false;
        try{(void)conditional_module_path_delay(s,p,paths,3,0,1,conditions);}catch(const std::runtime_error&){failed=true;}
        assert(failed);
    }
    std::cout<<"PASS conditional path current-state selection, X/Z, ifnone grouping, edges, timestamps and rollback\n";
}
