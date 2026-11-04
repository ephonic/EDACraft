#include <dsim/parallel.hpp>
#include <cassert>
#include <set>
using namespace dsim;
struct Relay {int input,output,site;bool print,fixed;};
static void relay(Sim& s,void* context,uint32_t) {
    auto& m=*static_cast<Relay*>(context);
    if(m.print)s.print("%0t %h",{V(s.now,0,64),s.get(m.input)});
    else s.set(m.output,inv(s.get(m.input)));
    if(m.fixed)s.arm_fixed_wait(m.site);else s.arm_wait(m.site);
}
static int compiled_relay(Sim& s,int input,int output,bool print,bool fixed) {
    auto state=std::make_shared<Relay>(Relay{input,output,0,print,fixed});
    auto context=s.compiled_context(state);auto handler=s.compiled_handler(context,relay);
    int process=s.compiled_process(handler,0);state->site=fixed?s.add_fixed_wait(process,{{input,0}}):s.add_wait_site(process,{{input,0}});return process;
}
static std::string circuit(size_t workers,uint64_t quantum,int compiled=0) {
    ConservativeSim machine(workers,quantum);
    auto p0=machine.partition(),p1=machine.partition(),p2=machine.partition();
    auto& a=machine.kernel(p0);auto& b=machine.kernel(p1);auto& c=machine.kernel(p2);
    int source=a.signal(8,false),input=b.signal(8,true),middle=b.signal(8,false),dest=c.signal(8,false);
    int source_process=a.process([&,pc=0]() mutable {a.set(source,V(uint64_t(pc*17),0,8));if(++pc<30)a.delay(0,5);});a.enqueue(source_process);
    int compute=compiled?compiled_relay(b,input,middle,false,compiled==2):b.process([&]{b.set(middle,inv(b.get(input)));b.wait(0,{{input,0}});});b.enqueue(compute);
    int observe=compiled?compiled_relay(c,dest,-1,true,compiled==2):c.process([&]{c.print("%0t %h",{V(c.now,0,64),c.get(dest)});c.wait(0,{{dest,0}});});c.enqueue(observe);
    machine.connect(p0,source,p1,input,3,123);
    machine.connect(p1,middle,p2,dest,4);
    std::ostringstream output;auto* old=std::cout.rdbuf(output.rdbuf());
    machine.run_until(50);machine.run_until(180);std::cout.rdbuf(old);
    std::ostringstream oracle;display("%0t %h",{V(0,0,64),V::x(8)},true,oracle);
    for(int i=0;i<30;++i)display("%0t %h",{V(uint64_t(i*5+7),0,64),inv(V(uint64_t(i*17),0,8))},true,oracle);
    assert(output.str()==oracle.str());assert(c.get(dest).same(inv(V(29*17,0,8))));
    assert(machine.stats.messages>60&&machine.stats.windows>0);
    return output.str();
}
int main() {
    Sim boundary;int input=boundary.signal(8,false);
    int reader=boundary.process([&]{assert(boundary.get(input).same(V(0x5a,0,8)));});
    boundary.enqueue(reader);boundary.deliver_at(0,input,-1,V(0x5a,0,8));boundary.run_until(0);
    std::vector<V> delivered;
    boundary.observe_resolved([&](uint64_t,int,V value){delivered.push_back(value);});
    bool accepted=boundary.predict_until(1,[&](Sim& s){s.set(input,V(0xff,0,8));},[](const Sim&){return false;},[](Sim&){});
    assert(!accepted&&delivered.empty()&&boundary.get(input).same(V(0x5a,0,8)));
    Sim committed;std::vector<uint64_t> output_times;
    committed.redirect_output([&](uint64_t time,const std::string&){output_times.push_back(time);});
    int printer=committed.process([&]{committed.print("accepted",{});});committed.delay(printer,2);committed.delay(printer,4);
    accepted=committed.predict_until(5,[](Sim&){},[](const Sim&){return true;},[](Sim&){});
    assert(accepted&&output_times==std::vector<uint64_t>({2,4}));
    // Unconnected partitions can batch known scalar loops. Outgoing channels
    // must disable batching even for a different local variable: it cannot
    // bypass the resolved-value notification path used for message delivery.
    ConservativeSim guarded(2);auto ga=guarded.partition(),gb=guarded.partition();
    auto& gsa=guarded.kernel(ga);auto& gsb=guarded.kernel(gb);
    int gac=gsa.signal(32,false),gau=gsa.signal(32,false),gbc=gsb.signal(32,false);
    gsa.set(gac,V(7,0,32));gsa.set(gau,V(9,0,32));gsb.set(gbc,V(0,0,32));
    assert(gsa.integral_loop_ready({gac,gau})&&gsb.integral_loop_ready({gbc}));
    gsa.set(gau,V::x(32));assert(!gsa.integral_loop_ready({gau}));gsa.set(gau,V(9,0,32));
    guarded.connect(ga,gac,gb,gbc,3);
    assert(!gsa.integral_loop_ready({gac})&&!gsa.integral_loop_ready({gau}));
    assert(gsb.integral_loop_ready({gbc}));
    int update=gsa.process([&]{gsa.set(gac,V(11,0,32));});gsa.delay(update,2);
    guarded.run();assert(gsb.get(gbc).same(V(11,0,32))&&guarded.stats.messages==2);
    auto reference=circuit(1,1);
    for(auto workers:{1,2,4})for(auto quantum:{1,2,3,7,1024})for(int compiled:{0,1,2})assert(circuit(size_t(workers),uint64_t(quantum),compiled)==reference);
    // Known initial boundary values make this delayed feedback alternate every
    // two ticks; this exercises a cycle that cannot be split at zero delay.
    ConservativeSim ring(2,10);auto a=ring.partition(),b=ring.partition();
    auto& x=ring.kernel(a);auto& y=ring.kernel(b);
    int xi=x.signal(1,false),xo=x.signal(1,false),yi=y.signal(1,false),yo=y.signal(1,false);
    x.set(xi,V(0));y.set(yi,V(0));x.set(xo,V(1));y.set(yo,V(0));
    int xp=x.process([&]{x.set(xo,inv(x.get(xi)));x.wait(0,{{xi,0}});});x.enqueue(xp);
    int yp=y.process([&]{y.set(yo,y.get(yi));y.wait(0,{{yi,0}});});y.enqueue(yp);
    ring.connect(a,xo,b,yi,1);ring.connect(b,yo,a,xi,1);ring.run_until(20);
    assert(x.get(xo).same(V(1))&&y.get(yo).same(V(0)));
    // Verify tasks really overlap on two OS threads, without timing assertions.
    ConservativeSim concurrent(2);std::mutex mutex;std::condition_variable ready;int entered=0;std::set<std::thread::id> ids;
    for(int i=0;i<2;++i) {
        auto id=concurrent.partition();auto& sim=concurrent.kernel(id);
        int p=sim.process([&]{std::unique_lock<std::mutex> hold(mutex);ids.insert(std::this_thread::get_id());++entered;ready.notify_all();ready.wait(hold,[&]{return entered==2;});});sim.enqueue(p);
    }
    concurrent.run_until(0);assert(ids.size()==2);
    ConservativeSim invalid(1);auto u=invalid.partition(),v=invalid.partition();int us=invalid.kernel(u).signal(1,false),vs=invalid.kernel(v).signal(1,false);
    bool failed=false;try{invalid.connect(u,us,v,vs,0);}catch(const std::runtime_error&){failed=true;}assert(failed);
    // A worker failure joins all workers and propagates, rather than deadlocking.
    ConservativeSim broken(2);auto part=broken.partition();auto& sim=broken.kernel(part);
    int p=sim.process([]{throw std::runtime_error("expected worker failure");});sim.enqueue(p);
    failed=false;try{broken.run_until(3);}catch(const std::runtime_error&){failed=true;}assert(failed);
    ConservativeSim units(2);auto ta=units.partition(),tb=units.partition();
    units.kernel(ta).set_time_precision(1000);units.kernel(tb).set_time_precision(1000000);
    failed=false;try{units.run_until(1);}catch(const std::runtime_error&){failed=true;}assert(failed);
    std::cout<<"PASS conservative parallel simulation: 1/2/4 workers, generic/compiled dynamic/fixed contexts, channels, windows, deterministic output, feedback, overlap, errors, physical time consistency\n";
}
