#define DSIM_WAVE_ENABLED 1
#define DSIM_TIMING_ENABLED 1
#define DSIM_PARALLEL_ENABLED 1
#include <dsim/runtime.hpp>
#include <cassert>
#include <random>
using namespace dsim;
static V bit(int state,int width) {return state==3?V::z(width):state==2?V::x(width):V(state?mask(width):0,0,width);}
static int merge(int a,int b) {return a==3?b:b==3?a:a==b?a:2;}
static V resolved(const std::map<int,V>& drivers,int width) {
    uint64_t a=0,b=0;
    for(int i=0;i<width;++i) {
        int value=3;for(const auto& driver:drivers)value=merge(value,driver.second.bit(i));
        if(value==1||value==2)a|=uint64_t(1)<<i;
        if(value>=2)b|=uint64_t(1)<<i;
    }
    return V(a,b,width);
}
int main() {
    for(int width:{1,7,64})for(int a=0;a<4;++a)for(int b=0;b<4;++b) {
        Sim s;int n=s.signal(width,true);s.drive(n,-7,bit(a,width));
        auto cp=s.checkpoint();
        for(int i=0;i<8;++i)s.drive(n,-7,bit(a,width));
        assert(s.get(n).same(bit(a,width)));
        // set() writes the resolved value without updating stored drivers.
        // The next repeated drive must repair it, not return on driver identity.
        s.set(n,bit(b,width));s.drive(n,-7,bit(a,width));assert(s.get(n).same(bit(a,width)));
        // A new driver with an identical value still has to be registered.
        s.drive(n,29,bit(a,width));s.drive(n,-7,V::z(width));assert(s.get(n).same(bit(a,width)));
        s.drive(n,-7,bit(b,width));s.restore(cp);s.drive(n,-7,bit(a,width));assert(s.get(n).same(bit(a,width)));
        // Width normalization precedes equality testing.
        s.drive(n,-7,V(1));assert(s.get(n).same(V(1,0,width)));
        s.drive(n,-7,V(1,0,width));assert(s.get(n).same(V(1,0,width)));
    }
    // A resolved X must not mask a change to one of its individual drivers.
    for(bool alias:{false,true}) {
        Sim s;int left=s.signal(1,true),right=alias?s.signal(1,true):left;
        if(alias)s.connect_net(left,0,right,0);
        s.drive(left,0,V(0));s.drive(right,1,V(1));assert(s.get(left).same(V::x(1)));
        s.drive(left,0,V::x(1));s.drive(right,1,V::z(1));assert(s.get(left).same(V::x(1)));
        s.drive(left,0,V(0));s.drive(right,1,V(0));s.drive(left,0,V::z(1));assert(s.get(left).same(V(0)));
    }
    // Pending connections have not yet populated the alias membership cache.
    {
        Sim s;int a=s.signal(1,true),b=s.signal(1,true);s.set(b,V(1));s.connect_net(a,0,b,0);
        s.drive(a,0,V::z(1));assert(s.get(a).same(V::z(1))&&s.get(b).same(V::z(1)));
    }
    // Compare mixed writes with a bit-by-bit independent strong-driver model.
    // Both resolved callbacks must contain every change, with no extra event.
    for(int width:{1,7,64}) {
        Sim s;int n=s.signal(width,true);std::vector<V> wave,observer,expected;
        s.attach_wave(&wave,+[](void* raw,uint64_t,int,V value){static_cast<std::vector<V>*>(raw)->push_back(value);},+[](void*,uint64_t){});
        s.observe_resolved([&](uint64_t,int,V value){observer.push_back(value);});
        std::map<int,V> drivers;V current=V::z(width);std::mt19937 rng(271828);
        auto change=[&](V v){if(!current.same(v))expected.push_back(v);current=v;};
        for(int i=0;i<2000;++i) {
            int id=i<500?-11:int(rng()%5)-2;
            V value=bit(int(rng()%4),width);
            if(i%7==0) {s.set(n,value);change(value);}
            else {
                if(i%3==0&&drivers.count(id))value=drivers[id];
                s.drive(n,id,value);drivers[id]=value;change(resolved(drivers,width));
            }
            assert(s.get(n).same(current));
        }
        assert(wave.size()==expected.size()&&observer.size()==expected.size());
        for(size_t i=0;i<expected.size();++i)assert(wave[i].same(expected[i])&&observer[i].same(expected[i]));
    }
    // No-op drives cannot wake an armed process; an NBA/direct set overwrite
    // can, and an identical driver request must restore the committed value.
    {
        Sim s;int n=s.signal(1,true);auto count=std::make_shared<int>(0);s.register_state(count);
        int p=s.process([&]{++*count;s.wait(0,{{n,0}});});s.wait(p,{{n,0}});
        s.drive(n,0,V(1));s.run_until(0);assert(*count==1);
        s.drive(n,0,V(1));s.run_until(0);assert(*count==1);
        s.assign_nba(n,V(0));s.drive(n,0,V(1));s.run_until(0);assert(*count==2&&s.get(n).same(V(0)));
        s.drive(n,0,V(1));s.run_until(0);assert(*count==3&&s.get(n).same(V(1)));
        auto cp=s.checkpoint();s.drive(n,1,V(0));s.run_until(0);s.restore(cp);
        s.drive(n,0,V(1));s.run_until(0);assert(*count==3);
    }
    // Delayed-driver completion uses drive(): checkpoint restoration and
    // rejected/accepted speculation must preserve both stored and resolved V.
    {
        Sim s;int n=s.signal(1,true);auto ch=s.delayed_driver(n,-1,Sim::DelayPolicy::PreserveTransitions);
        s.drive_after(ch,V(1),0);s.run_until(0);auto cp=s.checkpoint();
        s.set(n,V(0));s.cancel_delayed(ch);s.drive_after(ch,V(1),2);s.run_until(2);assert(s.get(n).same(V(1)));
        s.restore(cp);std::vector<V> changes;
        s.attach_wave(&changes,+[](void* raw,uint64_t,int,V v){static_cast<std::vector<V>*>(raw)->push_back(v);},+[](void*,uint64_t){});
        bool accepted=s.predict_until(3,[&](Sim& q){q.drive(n,3,V(0));},[](const Sim&){return false;},[&](Sim& q){q.drive(n,-1,V(1));});
        assert(!accepted&&changes.empty()&&s.get(n).same(V(1)));
        accepted=s.predict_until(4,[&](Sim& q){q.set(n,V(0));q.cancel_delayed(ch);q.drive_after(ch,V(1),1);},[](const Sim&){return true;},[](Sim&){assert(false);});
        assert(accepted&&changes.size()==2&&changes[0].same(V(0))&&changes[1].same(V(1)));
    }
    std::cout<<"PASS repeated drivers: four states/widths, direct set/NBA repair, driver identity, aliases, independent resolved model and callbacks, wakes, checkpoints and delayed prediction\n";
}
