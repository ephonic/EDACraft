#define DSIM_TIMING_ENABLED 1
#define DSIM_PATH_ENABLED 1
#define DSIM_CONDITIONAL_PATH_ENABLED 1
#include <dsim/runtime.hpp>
#include <dsim/path.hpp>
#include <dsim/path_dictionary.hpp>
#include <cassert>
#include <random>
using namespace dsim;
static bool yes(Sim&,const int*){return true;}
static bool enabled(Sim& s,const int* p){return s.get(p[0]).bit(0)!=0;}
static bool known(Sim& s,const int* p){return s.get(p[1]).bit(0)==1;}
static V logic(int n){return n==2?V::x(1):n==3?V::z(1):V(n);}
template<class F>static std::pair<bool,uint64_t> outcome(F fn){
    try{return {false,fn()};}catch(const std::runtime_error&){return {true,0};}
}
int main(){
    static_assert(sizeof(ModulePathArc)==104,"baseline arc ABI changed");
    static_assert(sizeof(DictionaryModulePathArc)==12,"packed arc ABI changed");
    uint64_t comparisons=0;
    std::mt19937 random(101817);
    ModulePathCondition conditions[]={yes,enabled,known};
    for(bool compact:{false,true}) {
        Sim s;int pins[8];
        for(auto& pin:pins){
#ifdef DSIM_COMPACT_GATES
            if(compact)pin=s.compact_net();else
#else
            (void)compact;
#endif
            pin=s.signal(1,true);
        }
        uint64_t tables[17][12];
        for(auto& row:tables)for(auto& value:row)value=random()%100;
        ModulePathArc baseline[32];DictionaryModulePathArc packed[32];
        ConditionalModulePathArc conditional[32];DictionaryConditionalModulePathArc conditional_packed[32];
        for(int step=0;step<400;++step){
            for(auto& pin:pins)if(random()%4==0)s.set(pin,logic(int(random()%4)));
            for(size_t i=0;i<32;++i){
                uint32_t input=random()%8,table=random()%17;uint8_t edge=uint8_t(random()%4);
                baseline[i]={input,edge,{}};std::copy(tables[table],tables[table]+12,baseline[i].delay);
                packed[i]={input,table,edge};
                uint32_t first=random()%6,condition=random()%3;bool fallback=random()%4==0;
                conditional[i]={baseline[i],first,condition,fallback};
                conditional_packed[i]={packed[i],first,condition,fallback};
            }
            for(size_t count:{size_t(0),size_t(1),size_t(7),size_t(32)})for(int from=0;from<4;++from)for(int to=0;to<4;++to){
                assert(outcome([&]{return module_path_delay(s,pins,baseline,count,from,to);})==
                       outcome([&]{return dictionary_module_path_delay(s,pins,packed,count,from,to,tables);}));
                assert(outcome([&]{return conditional_module_path_delay(s,pins,conditional,count,from,to,conditions);})==
                       outcome([&]{return dictionary_conditional_module_path_delay(s,pins,conditional_packed,count,from,to,conditions,tables);}));
                comparisons+=2;
            }
            if(step%10==0){
                auto old=s.checkpoint();s.run_until(s.now+3);for(auto pin:pins)s.set(pin,logic(int(random()%4)));s.restore(old);
            }
            s.run_until(s.now+uint64_t(random()%5));
        }
    }
    // Independent hand values: latest timestamp, tied minimum, remaining delay,
    // initialization edge exemption and the precise overflow boundary.
    Sim s;int pins[]={s.signal(1,true),s.signal(1,true)};
    uint64_t tables[2][12]{};for(auto& d:tables[0])d=7;for(auto& d:tables[1])d=19;
    DictionaryModulePathArc arcs[]={{0,0,0},{1,1,0}};
    assert(dictionary_module_path_delay(s,pins,arcs,2,0,1,tables)==0);
    s.set(pins[0],V(0));arcs[0].edge=1;
    assert(dictionary_module_path_delay(s,pins,arcs,1,0,1,tables)==7);
    arcs[0].edge=0;s.set(pins[1],V(0));s.run_until(10);s.set(pins[0],V(1));s.set(pins[1],V(1));
    assert(dictionary_module_path_delay(s,pins,arcs,2,0,1,tables)==7);
    s.run_until(15);s.set(pins[1],V(0));
    assert(dictionary_module_path_delay(s,pins,arcs,2,0,1,tables)==19);
    auto checkpoint=s.checkpoint();s.run_until(25);
    assert(dictionary_module_path_delay(s,pins,arcs,2,0,1,tables)==9);s.restore(checkpoint);
    tables[1][0]=UINT64_MAX-15;
    assert(dictionary_module_path_delay(s,pins,arcs,2,0,1,tables)==UINT64_MAX-15);
    ++tables[1][0];assert(outcome([&]{return dictionary_module_path_delay(s,pins,arcs,2,0,1,tables);}).first);
    std::cout<<"PASS path dictionary comparisons="<<comparisons<<" metadata=12 baseline=104\n";
}
