#include <dsim/parallel.hpp>
#include <cassert>
#include <sstream>
using namespace dsim;

static void planner() {
    PartitionGraph g;
    for(auto w:{9,3,7,5,0})g.node(w);
    g.edge(0,1,0);g.edge(1,2,3);g.edge(2,3,2);
    auto p=g.plan(4);
    assert(p.domains==4&&p.loads.size()==3&&p.owner[0]==p.owner[1]);
    assert((p.loads==std::vector<uint64_t>{12,7,5}));
    assert(p.cut_edges==2&&p.lookahead==2);
    for(size_t count=1;count<=8;++count) {
        auto plan=g.plan(count);assert(plan.owner==g.plan(count).owner);
        uint64_t sum=std::accumulate(plan.loads.begin(),plan.loads.end(),uint64_t(0));assert(sum==24);
        for(auto e:g.edges())assert(e.delay||plan.owner[e.from]==plan.owner[e.to]);
    }
    // A zero-delay feedback component cannot be split to fill more workers.
    g.edge(3,0,0);g.edge(2,3,0);assert(g.plan(100).loads.size()==1);
    bool failed=false;try{g.plan(0);}catch(const std::runtime_error&){failed=true;}assert(failed);
    failed=false;try{g.edge(99,0,1);}catch(const std::runtime_error&){failed=true;}assert(failed);
    PartitionGraph overflow;overflow.node(UINT64_MAX);overflow.node(1);overflow.edge(0,1,0);
    failed=false;try{overflow.plan(2);}catch(const std::runtime_error&){failed=true;}assert(failed);
    PartitionGraph large;
    for(size_t i=0;i<100000;++i){large.node(1);if(i)large.edge(i-1,i,i%100==0?1:0);}
    auto big=large.plan(4);assert(big.domains==1000&&big.loads.size()==4);
    assert((big.loads==std::vector<uint64_t>{25000,25000,25000,25000}));
}

static std::string circuit(size_t workers,uint64_t window) {
    PartitionGraph g;auto a=g.node(2),alias=g.node(1),b=g.node(3),c=g.node(2);
    auto wire=g.edge(a,alias,0),first=g.edge(alias,b,3),second=g.edge(b,c,4);
    AutoConservativeSim machine(g,workers,window);
    assert(&machine.kernel(a)==&machine.kernel(alias));
    assert(machine.plan().loads.size()==std::min(workers,size_t(3)));
    auto& left=machine.kernel(a);auto& middle=machine.kernel(b);auto& right=machine.kernel(c);
    int source=left.signal(1,true),copy=left.signal(1,true);
    int input=middle.signal(1,true),output=middle.signal(1,true),dest=right.signal(1,true);
    machine.connect(wire,source,copy);machine.connect(first,copy,input,100);machine.connect(second,output,dest,200);
    int generator=left.process([&,i=0]() mutable {
        static const int bits[]={0,1,2,3,1,0};
        left.drive(source,300,bits[i]<2?V(bits[i]):bits[i]==2?V::x(1):V::z(1));if(++i<6)left.delay(generator,5);
    });left.enqueue(generator);
    int relay=middle.process([&]{middle.drive(output,400,inv(middle.get(input)));middle.wait(relay,{{input,0}});});middle.enqueue(relay);
    int monitor=right.process([&]{right.print("%0t %b",{V(right.now,0,64),right.get(dest)});right.wait(monitor,{{dest,0}});});right.enqueue(monitor);
    std::ostringstream captured;auto* previous=std::cout.rdbuf(captured.rdbuf());
    try {machine.run_until(12);machine.run_until(40);}catch(...){std::cout.rdbuf(previous);throw;}
    std::cout.rdbuf(previous);
    assert(captured.str()=="0 z\n4 x\n7 1\n12 0\n17 x\n27 0\n32 1\n");
    assert(machine.stats().messages>0);
    bool failed=false;try{machine.connect(first,copy,input,100);}catch(const std::runtime_error&){failed=true;}assert(failed);
    return captured.str();
}

int main() {
    planner();auto reference=circuit(1,1);
    for(auto workers:{1,2,4})for(auto window:{1,2,3,7,1024})assert(circuit(size_t(workers),uint64_t(window))==reference);
    PartitionGraph g;g.node();g.node();g.edge(0,1,1);AutoConservativeSim incomplete(g,2);
    bool failed=false;try{incomplete.run_until(10);}catch(const std::runtime_error&){failed=true;}assert(failed);
    std::cout<<"PASS automatic partition planning, zero-delay aliases, 100000-node graph, independent four-state timeline and 1/2/4 workers\n";
}
