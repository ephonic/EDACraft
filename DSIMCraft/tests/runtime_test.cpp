#include "dsim/runtime.hpp"
#include <cassert>
using namespace dsim;
int main() {
    // Exhaustive scalar truth tables, including Z passthrough and driver conflicts.
    auto val=[](int n) {return n==2?V::x(1):n==3?V::z(1):V(n);};
    for(int a=0;a<4;++a) for(int b=0;b<4;++b) {
        for(int c=0;c<4;++c)
            assert(mux(val(c),val(a),val(b),1).bit(0)==(c<2?(c?a:b):a==b&&a<2?a:2));
        assert(bitop('&',val(a),val(b),1).bit(0)==(a==0||b==0?0:a==1&&b==1?1:2));
        assert(bitop('|',val(a),val(b),1).bit(0)==(a==1||b==1?1:a==0&&b==0?0:2));
        assert(resolve(val(a),val(b)).bit(0)==(a==3?b:b==3?a:a==b?a:2));
        assert(case_match(val(a),val(b),0)==(a==b));
        assert(case_match(val(a),val(b),1)==(a==b||a==3||b==3));
        assert(case_match(val(a),val(b),2)==(a==b||a>=2||b>=2));
    }
    assert(case_match(V(1),V(1,0,64),0));
    assert(!case_match(V(1),V((uint64_t(1)<<63)|1,0,64),0));
    assert(case_match(V(1),V(1,uint64_t(1)<<63,64),1));
    assert(!case_match(V(1),V((uint64_t(1)<<63)|1,uint64_t(1)<<63,64),1));
    assert(binary("==",V(0,2,2),V(1,0,2),1).bit(0)==0);
    assert(binary("+",V(~uint64_t(0),0,64),V(1,0,64),64).a==0);
    assert(binary(">>",V::x(8),V(64,0,8),8).a==0);
    assert(mux(V::x(1),V(5,0,4),V(7,0,4),4).same(V(7,2,4)));
    for(int disable=0;disable<4;++disable) for(int data=0;data<4;++data) {
        auto scalar=[](int bit) { return bit==0?V(0):bit==1?V(1):bit==2?V::x(1):V::z(1); };
        assert(tristate(scalar(disable),scalar(data),1).bit(0)==(disable==0?data:disable==1?3:2));
    }
    assert(slice(V(1,0,64),63,1).a==0);
    assert(format(V(3,2,4),'d')=="X");
    assert(format(V::x(4),'d')=="x");
    assert(format(V::z(4),'d')=="z");
    assert(format(V(0,2,4),'h')=="Z");
    Sim s; int a=s.signal(1,false),b=s.signal(1,false); int observations=0;
    int p=s.process([&] { ++observations; assert(s.get(a).a==1); assert(s.get(b).a==1); });
    s.wait(p,{{a,0},{b,0}});
    s.assign_nba(a,V(1)); s.assign_nba(b,V(1)); s.run(); assert(observations==1);
    Sim z; int phase=0;
    int q=z.process([&] {assert(phase==1); phase=2;}); z.delay(q,0);
    int r=z.process([&] {assert(phase==0);phase=1;}); z.enqueue(r); z.run(); assert(phase==2);
    // NBA callbacks run after Inactive and after the whole assignment batch.
    Sim deferred; int dv=deferred.signal(1,false); deferred.set(dv,V(0));
    std::vector<int> order;
    int wake=deferred.process([&]{ assert(deferred.get(dv).same(V(1))); order.push_back(3); });
    int ia=deferred.process([&]{ order.push_back(2); });
    int ac=deferred.process([&]{ order.push_back(1); });
    deferred.enqueue_nba(wake); deferred.assign_nba(dv,V(1));
    deferred.delay(ia,0); deferred.enqueue(ac); deferred.run();
    assert(order==std::vector<int>({1,2,3}));
    // Liberty's L/H/N/T/X conflict truth table, including initially unknown
    // state and independent complementary/noncomplementary state variables.
    const char* actions="LHNTX";
    const int truth[3][5]={{0,1,0,1,2},{0,1,1,0,2},{0,1,2,2,2}};
    for(int seed=0;seed<3;++seed) for(int x=0;x<5;++x) for(int y=0;y<5;++y) {
        GateState state;
        if(seed<2) { state.capture(false,V(0),V(0),V(seed==0),V(seed==1),'X','X'); state.apply(); }
        state.capture(false,V(0),V(0),V(1),V(1),actions[x],actions[y]); state.apply();
        assert(state.value().bit(0)==truth[seed][x]);
        assert(state.value(true).bit(0)==truth[seed<2?1-seed:2][y]);
    }
    // Four-state preservation outside every legal slice of a small vector.
    for(int lo=0;lo<4;++lo) for(int width=1;width<=4-lo;++width) for(int bit=0;bit<4;++bit) {
        V source=bit==2?V::x(width):bit==3?V::z(width):V(bit?mask(width):0,0,width);
        V result=replace(V::x(4),lo,width,source);
        for(int i=0;i<4;++i) assert(result.bit(i)==(i>=lo && i<lo+width?bit:2));
    }
    assert(replace(V::z(64),0,64,V(~uint64_t(0),0,64)).same(V(mask(64),0,64)));
    assert(replace(V(0,0,64),63,1,V(1)).a==(uint64_t(1)<<63));
    Sim partial; int word=partial.signal(8,false);
    partial.set(word,V(0,0,8));
    partial.assign_parts({{word,4,4,0}},V(10,0,4),true);
    partial.assign_parts({{word,0,4,0}},V(5,0,4),true);
    partial.run(); assert(partial.get(word).same(V(0xa5,0,8)));
    partial.assign_parts({{word,4,4,0}},V(3,0,4),true);
    partial.set(word,V(0xa1,0,8)); partial.run();
    assert(partial.get(word).same(V(0x31,0,8)));
    partial.assign_parts({{word,0,1,0},{word,0,1,1}},V(2,0,2),false);
    assert(partial.get(word).bit(0)==0); // VCS: rightmost concatenation occurrence.
    partial.assign_parts({{word,0,1,0},{word,0,1,1}},V(1,0,2),true);
    partial.run(); assert(partial.get(word).bit(0)==1);
    Sim joined; int ja=joined.signal(4,true),jb=joined.signal(4,true),jc=joined.signal(1,true);
    joined.connect_net(ja,3,jb,1); joined.connect_net(jb,1,jc,0); joined.connect_net(jc,0,ja,3);
    joined.finish_connections();
    joined.drive(ja,0,V(8,7,4));
    assert(joined.get(ja).same(V(8,7,4)) && joined.get(jb).same(V(2,13,4)) && joined.get(jc).same(V(1)));
    joined.drive(jc,1,V(0)); assert(joined.get(ja).bit(3)==2 && joined.get(jb).bit(1)==2);
    joined.drive(ja,0,V::z(4)); assert(joined.get(ja).bit(3)==0 && joined.get(jb).bit(1)==0);
    joined.drive(jc,1,V::z(1)); assert(joined.get(ja).same(V::z(4)) && joined.get(jb).same(V::z(4)));
    Sim atomic; int bus=atomic.signal(1,true),mirror=atomic.signal(1,true),changes=0;
    atomic.connect_net(bus,0,mirror,0); atomic.finish_connections();
    std::vector<Part> drivers={{bus,0,1,0,0},{bus,0,1,1,1}};
    atomic.drive_parts(drivers,V(2,0,2)); assert(atomic.get(bus).same(V::x(1)));
    int watcher=atomic.process([&]{++changes;}); atomic.wait(watcher,{{mirror,0}});
    atomic.drive_parts(drivers,V(1,0,2)); atomic.run();
    assert(changes==0 && atomic.get(mirror).same(V::x(1)));
    // An entire structural copy reads the old RHS before resolving any output.
    Sim copy; int ca=copy.signal(1,true),cb=copy.signal(1,true);
    copy.drive(ca,10,V(0)); copy.drive(cb,11,V(1));
    int dest[]={ca,cb},src[]={cb,ca}; copy.drive_copies(dest,src,10,2);
    assert(copy.get(ca).same(V(1)) && copy.get(cb).same(V(0)));
    Sim copy_alias; int cl=copy_alias.signal(1,false),cr=copy_alias.signal(1,false),cn=copy_alias.signal(1,true),cm=copy_alias.signal(1,true);
    copy_alias.connect_net(cn,0,cm,0); copy_alias.finish_connections();
    copy_alias.set(cl,V(0)); copy_alias.set(cr,V(1));
    int repeated[]={cn,cn},rhs[]={cl,cr}; copy_alias.drive_copies(repeated,rhs,20,2);
    int copy_changes=0,cp=copy_alias.process([&]{++copy_changes;}); copy_alias.wait(cp,{{cm,0}});
    copy_alias.set(cl,V(1)); copy_alias.set(cr,V(0)); copy_alias.drive_copies(repeated,rhs,20,2); copy_alias.run();
    assert(copy_alias.get(cn).same(V::x(1)) && copy_changes==0);
    // Inactive generations must not wake a process after it switches wait sites.
    Sim sites; int sa=sites.signal(1,false),sb=sites.signal(1,false),calls=0;
    sites.set(sa,V(0)); sites.set(sb,V(1));
    int sp=sites.process([&]{++calls;});
    int ap=sites.add_wait_site(sp,{{sa,1}}),bn=sites.add_wait_site(sp,{{sb,2}});
    sites.arm_wait(ap); sites.set(sa,V(1)); sites.run(); assert(calls==1);
    sites.arm_wait(bn); sites.set(sa,V(0)); sites.set(sa,V(1)); sites.run(); assert(calls==1);
    sites.set(sb,V(0)); sites.run(); assert(calls==2);
    sites.wait(sp,{{sa,1},{sa,2}}); sites.set(sa,V(0)); sites.run(); assert(calls==3);
    sites.arm_wait(ap); sites.set(sa,V(1)); sites.run(); assert(calls==4);
    // Edge-only controls inspect bit zero; a whole-vector change also sees upper bits.
    Sim edges; int vector=edges.signal(4,false),edge_calls=0;
    edges.set(vector,V(0,0,4)); int ep=edges.process([&]{++edge_calls;});
    edges.wait(ep,{{vector,1},{vector,2}}); edges.set(vector,V(8,0,4)); edges.run(); assert(edge_calls==0);
    edges.set(vector,V(9,0,4)); edges.run(); assert(edge_calls==1);
    edges.wait(ep,{{vector,1},{vector,0}}); edges.set(vector,V(1,0,4)); edges.run(); assert(edge_calls==2);
    for(int from=0;from<4;++from) for(int to=0;to<4;++to) {
        Sim e; int v=e.signal(1,false); e.set(v,val(from)); int any=0,pos=0,neg=0;
        int pa=e.process([&]{++any;}),pp=e.process([&]{++pos;}),pn=e.process([&]{++neg;});
        e.arm_wait(e.add_wait_site(pa,{{v,0}}));
        e.arm_wait(e.add_wait_site(pp,{{v,1}}));
        e.arm_wait(e.add_wait_site(pn,{{v,2}}));
        e.set(v,val(to)); e.run();
        assert(any==(from!=to));
        assert(pos==((from==0 && to!=0)||(from>=2 && to==1)));
        assert(neg==((from==1 && to!=1)||(from>=2 && to==0)));
    }
    // Re-enqueueing a nonempty FIFO exercises both growth and repeated ring wrap.
    Sim fifo; std::vector<int> observed; std::vector<int> rounds(120,0),ids;
    for(int i=0;i<120;++i) ids.push_back(fifo.process([&,i]{
        observed.push_back(i); if(++rounds[i]<4) fifo.enqueue(ids[i]);
    }));
    for(int p:ids) fifo.enqueue(p);
    fifo.run(); assert(observed.size()==480);
    for(size_t i=0;i<observed.size();++i) assert(observed[i]==int(i%120));
    Sim timers; std::vector<std::pair<uint64_t,int>> expected,actual;
    std::vector<int> timer_ids;
    for(int i=0;i<256;++i) timer_ids.push_back(timers.process([&,i]{actual.push_back({timers.now,i});}));
    for(int i=255;i>=0;--i) {
        uint64_t time=1+i%7; timers.delay(timer_ids[i],time); expected.push_back({time,i});
    }
    std::stable_sort(expected.begin(),expected.end(),[](auto a,auto b){return a.first<b.first;});
    timers.run(); assert(actual==expected);
    // Timer wakes deduplicate an already queued process, as immediate events do.
    Sim duplicates; int duplicate_calls=0;
    int dp=duplicates.process([&]{++duplicate_calls;});
    duplicates.delay(dp,1); duplicates.delay(dp,1); duplicates.delay(dp,2);
    duplicates.run(); assert(duplicate_calls==2);
    duplicates.now=std::numeric_limits<uint64_t>::max(); bool overflow=false;
    try {duplicates.delay(dp,1);} catch(const std::runtime_error&) {overflow=true;}
    assert(overflow);
    std::cout<<"PASS runtime truth tables, NBA, partial writes, net bits, wait generations, FIFO, stable timers and region ordering\n";
}
