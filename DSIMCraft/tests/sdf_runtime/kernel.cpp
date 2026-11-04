#define DSIM_TIMING_ENABLED 1
#define DSIM_PATH_ENABLED 1
#include <dsim/runtime.hpp>
#include <dsim/path.hpp>
#include <cassert>
using namespace dsim;
static V value(int code){return code==2?V::x(1):code==3?V::z(1):V(code);}
template<class F>void fails(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}assert(failed);}
static int net(Sim& s,bool compact){
#ifdef DSIM_COMPACT_GATES
    if(compact)return s.compact_net();
#else
    (void)compact;
#endif
    return s.signal(1,true);
}
int main(){
    const int transitions[4][4]={{-1,0,6,2},{1,-1,8,4},{9,7,-1,10},{5,3,11,-1}};
    for(bool compact:{false,true})for(int a=0;a<4;++a)for(int b=0;b<4;++b){
        Sim s;int id=net(s,compact);s.set(id,value(a));s.run_until(3);s.set(id,value(b));
        const auto stamp=s.path_stamp(id);assert(s.get(id).bit(0)==b);assert(path_transition(a,b)==transitions[a][b]);
        if(a!=b){assert(stamp.time==3&&stamp.before==a&&stamp.after==b&&stamp.valid);}
        ModulePathArc arc{0,0,{}};for(int i=0;i<12;++i)arc.delay[i]=uint64_t(5+i);
        assert(module_path_delay(s,&id,&arc,1,a,b)==uint64_t(a==b?0:5+transitions[a][b]));
        for(int edge:{1,2}){
            arc.edge=uint8_t(edge);bool active=edge==1?((a==0&&b!=0)||(a>=2&&b==1)):((a==1&&b!=1)||(a>=2&&b==0));
            if(a!=b)assert(module_path_delay(s,&id,&arc,1,a,b)==uint64_t(active?5+transitions[a][b]:0));
        }
    }
    {
        Sim init;int pin=init.signal(1,true);init.set(pin,V(0));
        ModulePathArc arc{0,1,{7}};
        assert(module_path_delay(init,&pin,&arc,1,0,1)==7);
        init.run_until(1);assert(module_path_delay(init,&pin,&arc,1,0,1)==0);
    }
    Sim s;int pins[]={s.signal(1,true),net(s,true)};ModulePathArc arcs[]={{0,0,{7}},{1,0,{19}}};
    assert(module_path_delay(s,pins,arcs,2,0,1)==0);s.set(pins[0],V(0));s.set(pins[1],V(0));
    s.run_until(10);s.set(pins[0],V(1));s.set(pins[1],V(1));assert(module_path_delay(s,pins,arcs,2,0,1)==7);
    s.run_until(15);s.set(pins[1],V(0));assert(module_path_delay(s,pins,arcs,2,0,1)==19);
    auto cp=s.checkpoint();s.run_until(18);s.set(pins[0],V(0));s.restore(cp);
    assert(s.path_stamp(pins[0]).time==10&&s.path_stamp(pins[1]).time==15);s.run_until(25);assert(module_path_delay(s,pins,arcs,2,0,1)==9);
    s.restore(cp);bool accepted=s.predict_until(30,[&](Sim& q){q.set(pins[0],V(0));},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&s.path_stamp(pins[0]).time==10&&s.path_stamp(pins[1]).time==15);
    s.restore(cp);arcs[1].delay[0]=UINT64_MAX;fails([&]{module_path_delay(s,pins,arcs,2,0,1);});
    // Resolved aliases and fallback multi-driver storage stamp resolved changes.
    Sim q;int a=net(q,true),b=q.signal(1,true);q.connect_net(a,0,b,0);q.finish_connections();q.drive(a,1,V(0));q.run_until(8);q.drive(b,2,V(1));
    for(int id:{a,b}){auto stamp=q.path_stamp(id);assert(stamp.time==8&&stamp.before==0&&stamp.after==2);}
    auto old=q.path_stamp(a);q.drive(a,1,V(0));assert(q.path_stamp(a).time==old.time);
    std::cout<<"PASS path transition stamps, latest/min selection, edge masks, alias resolution, overflow and rollback\n";
}
