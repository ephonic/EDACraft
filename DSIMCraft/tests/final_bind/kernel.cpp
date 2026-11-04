#define DSIM_FINAL_ENABLED 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/parallel.hpp>
#include <cassert>
using namespace dsim;
static void parallel_final(bool early) {
    ConservativeSim engine(2,1024);engine.enable_global_finish();
    std::vector<int> values;
    for(int i=0;i<2;++i) {
        auto part=engine.partition();auto& s=engine.kernel(part);int value=s.signal(8,false);s.set(value,V(0,0,8));values.push_back(value);
        int p=int(s.processes.size());
        s.process([&,i,p,value,pc=0]() mutable {
            auto& local=engine.kernel(size_t(i));
            if(!pc++){local.set(value,V(i+1,0,8));local.delay(p,i?5:3);return;}
            local.set(value,V(i+11,0,8));if(early&&i==0)local.finished=true;
        });s.enqueue(p);
        auto final=s.process([&,i,value]{
            auto& local=engine.kernel(size_t(i));local.set(value,V(local.get(value).a+100,0,8));
            local.print("FINAL %0d %0d %0d",{V(i,0,32),V(local.now,0,64),local.get(value)});
        });s.add_final_process(final);
    }
    std::ostringstream text;auto* old=std::cout.rdbuf(text.rdbuf());
    try {if(early)engine.run_until(20);else engine.run();engine.run();engine.run_until(30);}
    catch(...){std::cout.rdbuf(old);throw;}
    std::cout.rdbuf(old);
    assert(text.str()==(early?"FINAL 0 3 111\nFINAL 1 3 102\n":"FINAL 0 5 111\nFINAL 1 5 112\n"));
    assert(engine.kernel(0).get(values[0]).a==111);
    assert(engine.kernel(1).get(values[1]).a==uint64_t(early?102:112));
    assert(!early||engine.stats.window_replays==1);
}
int main(){parallel_final(false);parallel_final(true);std::cout<<"PASS final coordinator natural/finish/fence/exactly-once output\n";}
