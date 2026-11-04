#include "dsim/parallel.hpp"
#include <cassert>
#include <sstream>
using namespace dsim;

static std::string clocked(size_t workers,uint64_t window,bool finish,bool channel) {
    ConservativeSim engine(workers,window);
    if(finish)engine.enable_global_finish();
    auto a=engine.partition(),b=engine.partition();
    auto& left=engine.kernel(a);auto& right=engine.kernel(b);
    int x=left.signal(8,false),y=right.signal(8,false);
    int first=-1,second=-1;
    first=left.process([&,count=0]() mutable {
        if(finish&&left.now==40)throw std::runtime_error("past finish in another partition");
        left.set(x,V(count,0,8));
        left.print("L %0t %0d",{V(left.now,0,64),V(count,0,32)});
        if(++count<41)left.delay(first,2);
    });
    second=right.process([&,count=0]() mutable {
        right.print("R %0t %0d",{V(right.now,0,64),channel?right.get(y):V(count,0,32)});
        if(finish&&right.now==27){right.finished=true;return;}
        // A late exception must remain private to a discarded window.
        if(finish&&right.now>27)throw std::runtime_error("past finish");
        if(++count<20)right.delay(second,3);
    });
    left.enqueue(first);right.enqueue(second);
    if(channel)engine.connect(a,x,b,y,5);
    std::ostringstream output;auto* saved=std::cout.rdbuf(output.rdbuf());
    try{engine.run();}catch(...){std::cout.rdbuf(saved);throw;}
    std::cout.rdbuf(saved);
    if(finish)assert(engine.finished()&&engine.finish_time()==27);
    else {
        auto end=channel?85:80;
        assert(left.now==uint64_t(end)&&right.now==uint64_t(end));
        auto windows=engine.stats.windows;engine.run();assert(windows==engine.stats.windows);
        engine.run_until(uint64_t(end+1));assert(left.now==uint64_t(end+1));
    }
    if(!channel&&window==1024)assert(engine.stats.windows<=4);
    return output.str();
}

int main() {
    {
        ConservativeSim engine(2);
        auto a=engine.partition(),b=engine.partition();
        auto& left=engine.kernel(a);auto& right=engine.kernel(b);
        int x=left.signal(1,false),y=right.signal(1,false);
        auto p=left.process([&,pc=0]() mutable {
            if(pc++==0){left.set(x,V(0));left.delay(0,uint64_t(1)<<50);return;}
            left.set(x,V(1));
        });
        assert(p==0);left.enqueue(p);engine.connect(a,x,b,y,3);
        engine.run();
        assert(left.get(x).a==1&&right.get(y).a==1);
        assert(left.now==(uint64_t(1)<<50)+3&&right.now==left.now);
        assert(engine.stats.windows==4); // 0,3,large,large+3; both initial messages arrive at3.
    }
    {
        ConservativeSim engine(2);engine.enable_global_finish();
        auto a=engine.partition(),b=engine.partition();auto& left=engine.kernel(a);auto& right=engine.kernel(b);
        auto p=left.process([&,pc=0]() mutable {
            if(!pc++){left.delay(0,7);return;}left.finished=true;
        });
        auto q=right.process([&,pc=0]() mutable {
            if(!pc++){right.delay(0,20);return;}throw std::runtime_error("after finish");
        });
        left.enqueue(p);right.enqueue(q);engine.run();
        assert(engine.finished()&&engine.finish_time()==7&&engine.finish_partition()==a);
        assert(engine.stats.window_replays==1);
        engine.run();
    }
    {
        ConservativeSim engine(1);auto a=engine.partition();engine.run();
        assert(engine.kernel(a).now==0&&engine.stats.windows==1);
        bool frozen=false;try{engine.partition();}catch(const std::exception&){frozen=true;}assert(frozen);
    }
    {
        PartitionGraph graph;auto a=graph.node(),b=graph.node();auto e=graph.edge(a,b,5);
        AutoConservativeSim engine(graph,2);auto& left=engine.kernel(a);auto& right=engine.kernel(b);
        int x=left.signal(1,false),y=right.signal(1,false);left.set(x,V(1));engine.connect(e,x,y);
        engine.run();assert(right.get(y).a==1&&right.now==5);
    }
    for(bool finish:{false,true})for(bool channel:{false,true}) {
        auto reference=clocked(1,1,finish,channel);
        for(size_t workers:{1,2,4})for(uint64_t window:{2,5,17,1024})
            assert(clocked(workers,window,finish,channel)==reference);
    }

}
