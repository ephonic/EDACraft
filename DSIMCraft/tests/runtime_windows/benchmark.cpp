// Component benchmark, separate from the original RTL/VCS performance suite.
#include <dsim/parallel.hpp>
#include <chrono>
#include <cstdlib>
using namespace dsim;
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    auto start=std::chrono::steady_clock::now();uint64_t checksum=0,windows=0,replays=0;
    if(std::string(argv[1])=="restore") {
        Sim s;for(int i=0;i<10000;++i)s.signal(32,false);
        int p=-1;p=s.process([&,pc=0]()mutable{s.set(pc%10000,V(pc,0,32));if(++pc<100)s.delay(p,1);});s.enqueue(p);
        auto checkpoint=s.checkpoint();
        for(int i=0;i<3000;++i){s.restore(checkpoint);s.run();checksum+=s.get(99).a;}
    } else {
        bool finish=std::string(argv[1])=="finish";
        ConservativeSim engine(4,1024);if(finish)engine.enable_global_finish();
        for(size_t i=0;i<4;++i) {
            auto id=engine.partition();auto& s=engine.kernel(id);
            for(int k=0;k<64;++k)s.signal(32,false);
            auto job=std::make_shared<int>(-1);
            *job=s.process([&s,job,i,finish,pc=uint64_t(0)]()mutable{
                s.set(0,V((pc*1664525+i*17)^1013904223,0,32));
                if(finish&&i==1&&pc==200000){s.finished=true;return;}
                if(++pc<250000)s.delay(*job,1);
            });
            s.enqueue(*job);
        }
        engine.run();windows=engine.stats.windows;replays=engine.stats.window_replays;
        for(size_t i=0;i<4;++i)checksum+=engine.kernel(i).get(0).a;
    }
    auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    std::cout<<"RESULT "<<argv[1]<<" "<<checksum<<" windows="<<windows<<" replays="<<replays<<" seconds="<<elapsed<<"\n";
}
