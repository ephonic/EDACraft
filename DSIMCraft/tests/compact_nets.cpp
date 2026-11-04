#define DSIM_COMPACT_GATES 1
#define DSIM_WAVE_ENABLED 1
#define DSIM_TIMING_ENABLED 1
#include "dsim/parallel.hpp"
#include <array>
#include <cassert>
using namespace dsim;
static V value(int b,int w=1){return b==2?V::x(w):b==3?V::z(w):V(b?mask(w):0,0,w);}
static int merge(int a,int b){return a==3?b:b==3?a:a==b?a:2;}
static int net(Sim& s,bool compact){return compact?s.compact_net():s.signal(1,true);}
template<class F> static void rejects(F f){bool caught=false;try{f();}catch(const std::exception&){caught=true;}assert(caught);}
struct Event {uint64_t time;int id,bit;bool operator==(const Event& b)const{return time==b.time&&id==b.id&&bit==b.bit;}};
struct Capture {std::vector<Event> events;std::map<int,int> tags;};
static void hook(void* raw,uint64_t t,int id,V v){auto& c=*static_cast<Capture*>(raw);c.events.push_back({t,c.tags.at(id),v.bit(0)});}
static void resolution() {
    for(bool compact:{false,true})for(int a=0;a<4;++a)for(int b=0;b<4;++b)for(int c=0;c<4;++c) {
        Sim s;int n=net(s,compact);assert(s.get(n).same(V::z(1)));
        s.drive(n,-17,value(a));auto cp=s.checkpoint();
        // Direct set changes resolved state only. The same driver repairs it.
        s.set(n,value((a+1)%4,7));s.drive(n,-17,value(a,64));assert(s.get(n).bit(0)==a);
        s.drive(n,27,value(b));assert(s.get(n).bit(0)==merge(a,b));
        auto overflow=s.checkpoint();s.drive(n,INT32_MIN,value(c));assert(s.get(n).bit(0)==merge(merge(a,b),c));
        s.drive(n,27,value(c));s.restore(overflow);assert(s.get(n).bit(0)==merge(a,b));
        s.drive(n,27,value(c));assert(s.get(n).bit(0)==merge(a,c));
        s.restore(cp);s.drive(n,27,value(c));assert(s.get(n).bit(0)==merge(a,c));
        s.restore(cp);s.drive(n,-17,value(c));assert(s.get(n).bit(0)==c);
        rejects([&]{s.compact_net();});rejects([&]{s.get(INT32_MIN);});
    }
}
struct EdgeState {std::array<int,3> p{},site{},count{};};
static void late_slots() {
    Sim s;int first=s.signal(1,true);s.drive(first,9,V(1));
    int late=s.compact_net();assert(s.get(late).same(V::z(1))&&s.is_net(late));
    s.drive(late,-1,V::z(1));s.drive(late,1,V(0));assert(s.get(late).same(V(0)));
    // The first explicit Z identity survives overflow and restoration.
    auto cp=s.checkpoint();s.drive(late,-1,V(1));assert(s.get(late).same(V::x(1)));
    s.restore(cp);s.drive(late,1,V::z(1));assert(s.get(late).same(V::z(1)));
    rejects([&]{s.get(-2);});rejects([&]{s.set(-2,V(0));});rejects([&]{s.drive(-2,0,V(0));});
    rejects([&]{s.get(1);});
}
static void edges() {
    const bool pos[4][4]={{0,1,1,1},{0,0,0,0},{0,1,0,0},{0,1,0,0}};
    const bool neg[4][4]={{0,0,0,0},{1,0,1,1},{1,0,0,0},{1,0,0,0}};
    for(bool compact:{false,true})for(bool fixed:{false,true})for(int a=0;a<4;++a)for(int b=0;b<4;++b){
        Sim s;int n=net(s,compact);s.set(n,value(a));auto state=std::make_shared<EdgeState>();
        auto ctx=s.compiled_context(state);auto h=s.compiled_handler(ctx,+[](Sim&,void* raw,uint32_t i){auto& st=*static_cast<EdgeState*>(raw);++st.count[i];});
        for(int i=0;i<3;++i){int p=s.compiled_process(h,uint32_t(i));state->p[i]=p;
            if(fixed){s.add_fixed_wait(p,{{n,i},{n,i}});s.arm_fixed_wait(p);}
            else {state->site[i]=s.add_wait_site(p,{{n,i},{n,i}});s.arm_wait(state->site[i]);}}
        s.set(n,value(b));s.run();assert((state->count==std::array<int,3>{a!=b,pos[a][b],neg[a][b]}));
        // Re-arm a permanent or dynamic site and prove its copied watch state.
        for(int i=0;i<3;++i)if(fixed)s.arm_fixed_wait(state->p[i]);else s.arm_wait(state->site[i]);
        auto cp=s.checkpoint();s.set(n,value(a));s.run();auto expected=state->count;
        s.restore(cp);s.set(n,value(a));s.run();assert(state->count==expected);
    }
}
static void atomic_order() {
    Sim s;std::array<int,4> ids={s.signal(1,true),s.compact_net(),s.signal(1,true),s.compact_net()};
    int src=s.signal(1,false);s.set(src,V(1));std::array<int,4> from={src,src,src,src};
    std::array<int,4> reverse={ids[3],ids[2],ids[1],ids[0]},process{};std::vector<int> woke;int expected=1;
    for(int i=3;i>=0;--i){process[i]=s.process([&,i]{for(int id:ids)assert(s.get(id).bit(0)==expected);woke.push_back(i);s.wait(process[i],{{ids[i],0}});});s.wait(process[i],{{ids[i],0}});}
    Capture cap;for(int i=0;i<4;++i)cap.tags[ids[i]]=i;s.attach_wave(&cap,hook,nullptr);
    s.drive_copies(reverse.data(),from.data(),100,4);s.run();assert((woke==std::vector<int>{0,1,2,3}));
    assert((cap.events==std::vector<Event>{{0,0,1},{0,1,1},{0,2,1},{0,3,1}}));
    woke.clear();cap.events.clear();expected=0;
    std::vector<Part> parts;for(int i=3;i>=0;--i)parts.push_back({ids[i],0,1,0,-1});
    s.assign_parts(parts,V(0),false);s.run();assert((woke==std::vector<int>{0,1,2,3}));
    assert((cap.events==std::vector<Event>{{0,0,0},{0,1,0},{0,2,0},{0,3,0}}));
    // This must repair direct assignments even though own drivers remain 1.
    woke.clear();cap.events.clear();expected=1;s.drive_copies(reverse.data(),from.data(),100,4);s.run();
    assert((woke==std::vector<int>{0,1,2,3}));
    // Alternate driver storage path also publishes in logical creation order.
    woke.clear();cap.events.clear();expected=2;parts.clear();
    for(int i=3;i>=0;--i)parts.push_back({ids[i],0,1,0,300+i});
    s.drive_parts(parts,V(0));s.run();assert((woke==std::vector<int>{0,1,2,3}));
    assert((cap.events==std::vector<Event>{{0,0,2},{0,1,2},{0,2,2},{0,3,2}}));
}
static std::vector<Event> aliases(bool compact) {
    Sim s;int a=net(s,compact),wide=s.signal(64,true),b=net(s,compact);
    Capture cap;cap.tags={{a,0},{wide,1},{b,2}};s.attach_wave(&cap,hook,nullptr);
    // Watches exist before promotion and must remain attached to their slot.
    int calls=0,p=-1;p=s.process([&]{++calls;s.wait(p,{{a,0},{b,0}});});s.wait(p,{{a,0},{b,0}});
    s.connect_net(a,0,wide,63);s.connect_net(b,0,wide,0);
    s.drive(wide,2,V(0,0,64));s.run();assert(calls==1);
    s.drive(a,-5,V(1));s.run();assert(s.get(a).bit(0)==2&&s.get(wide).bit(63)==2&&s.get(wide).bit(0)==0);
    s.attach_wave(nullptr,nullptr,nullptr);auto cp=s.checkpoint();
    s.drive(b,9,V(1));assert(s.get(b).bit(0)==2);s.restore(cp);assert(s.get(b).bit(0)==0);
    s.attach_wave(&cap,hook,nullptr);s.drive(a,-5,V::z(1));s.run();assert(s.get(a).bit(0)==0);
    return cap.events;
}
static void transaction() {
    Sim s;int n=s.compact_net();s.drive(n,1,V(0));Capture c;c.tags[n]=0;s.attach_wave(&c,hook,nullptr);
    bool accepted=s.predict_until(5,[&](Sim& p){p.drive(n,2,V(1));},[](const Sim&){return false;},[&](Sim& p){p.drive(n,1,V(1));});
    assert(!accepted&&s.get(n).bit(0)==1&&c.events==std::vector<Event>({{0,0,1}}));
    c.events.clear();accepted=s.predict_until(10,[&](Sim& p){p.drive(n,1,V(0));},[](const Sim&){return true;},[](Sim&){assert(false);});
    assert(accepted&&c.events==std::vector<Event>({{5,0,0}}));
}
static std::vector<Event> delayed(bool compact) {
    Sim s;int a=net(s,compact),b=net(s,compact);Capture cap;cap.tags={{a,0},{b,1}};s.attach_wave(&cap,hook,nullptr);
    auto replace=s.delayed_driver(a,-7,Sim::DelayPolicy::ReplacePending),preserve=s.delayed_driver(b,3,Sim::DelayPolicy::PreserveTransitions);
    s.drive_after(replace,V(0),1);s.drive_after(preserve,V(0),1);s.run_until(2);
    bool accepted=s.predict_until(20,[&](Sim& p){p.drive_after(replace,V(1),2);p.drive_after(preserve,V(1),3);},[](const Sim&){return false;},[&](Sim& p){
        p.drive_after(replace,V(1),8);p.drive_after(replace,V::x(1),3);
        p.drive_after(preserve,V(1),8);p.drive_after(preserve,V::z(1),3);
    });assert(!accepted);return cap.events;
}
static std::string parallel(bool compact,size_t workers,uint64_t quantum) {
    ConservativeSim machine(workers,quantum);auto left=machine.partition(),right=machine.partition();auto& a=machine.kernel(left);auto& b=machine.kernel(right);
    int source=net(a,compact),input=net(b,compact),output=net(b,compact);
    auto channel=b.delayed_driver(output,5,Sim::DelayPolicy::PreserveTransitions);
    int p=-1;p=a.process([&,pc=0]()mutable{a.drive(source,7,value(pc%4));if(++pc<20)a.delay(p,5);});a.enqueue(p);
    int relay=-1;relay=b.process([&]{b.drive_after(channel,inv(b.get(input)),2);b.wait(relay,{{input,0}});});b.enqueue(relay);
    int monitor=-1;monitor=b.process([&]{b.print("%0t %b",{V(b.now,0,64),b.get(output)});b.wait(monitor,{{output,0}});});b.enqueue(monitor);
    machine.connect(left,source,right,input,3,99);std::ostringstream text;auto* old=std::cout.rdbuf(text.rdbuf());
    machine.run_until(37);machine.run_until(110);std::cout.rdbuf(old);return text.str();
}
int main(){
    static_assert(sizeof(CompactSignal)<sizeof(Signal));resolution();late_slots();edges();atomic_order();assert(aliases(false)==aliases(true));transaction();assert(delayed(false)==delayed(true));
    auto expected=parallel(false,1,1);for(size_t workers:{1,2,4})for(uint64_t q:{1,2,3,7,1024})assert(parallel(true,workers,q)==expected);
    std::cout<<"PASS compact net four-state resolution, signed/extra drivers, direct-set repair, edge masks, atomic creation order, aliases, deep checkpoints, waveform transactions, delayed/parallel endpoints; CompactSignal="<<sizeof(CompactSignal)<<" Signal="<<sizeof(Signal)<<'\n';
}
