#define DSIM_TIMING_ENABLED 1
#include <dsim/parallel.hpp>
#include <cassert>
using namespace dsim;
static std::string circuit(size_t workers,uint64_t quantum) {
    ConservativeSim machine(workers,quantum);auto p=machine.partition(),q=machine.partition();
    auto& a=machine.kernel(p);auto& b=machine.kernel(q);
    int output=a.signal(8,true),input=b.signal(8,true),dest=b.signal(8,true);
    auto first=a.delayed_driver(output,-9,Sim::DelayPolicy::PreserveTransitions);
    auto second=b.delayed_driver(dest,7,Sim::DelayPolicy::ReplacePending);
    int source=a.process([&,pc=0]() mutable {
        a.drive_after(first,V(uint64_t(pc*17),0,8),2);
        if(++pc<30)a.delay(0,5);
    });a.enqueue(source);
    int relay=b.process([&]{b.drive_after(second,inv(b.get(input)),2);b.wait(0,{{input,0}});});b.enqueue(relay);
    int monitor=b.process([&]{b.print("%0t %h",{V(b.now,0,64),b.get(dest)});b.wait(1,{{dest,0}});});b.enqueue(monitor);
    machine.connect(p,output,q,input,3,123);
    std::ostringstream output_text;auto* old=std::cout.rdbuf(output_text.rdbuf());
    machine.run_until(50);machine.run_until(180);std::cout.rdbuf(old);
    std::ostringstream oracle;display("%0t %h",{V(0,0,64),V::z(8)},true,oracle);
    display("%0t %h",{V(2,0,64),V::x(8)},true,oracle);
    for(int i=0;i<30;++i)display("%0t %h",{V(uint64_t(i*5+7),0,64),inv(V(uint64_t(i*17),0,8))},true,oracle);
    assert(output_text.str()==oracle.str());assert(b.get(dest).same(inv(V(29*17,0,8))));
    return output_text.str();
}
int main() {
    auto reference=circuit(1,1);
    for(auto workers:{1,2,4})for(auto quantum:{1,2,3,7,1024})assert(circuit(size_t(workers),uint64_t(quantum))==reference);
    std::cout<<"PASS delayed drivers in conservative partitions: independent queues, 1/2/4 workers, 5 quanta, input arrivals and deterministic output\n";
}
