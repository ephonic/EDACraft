#define DSIM_TIMING_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/parallel.hpp>
#include <dsim/waveform.hpp>
#include <cassert>
#include <filesystem>
#include <tuple>
using namespace dsim;
namespace fs=std::filesystem;
using Output=std::tuple<uint64_t,size_t,std::string>;

static std::unique_ptr<WaveCapture> install(Sim& s,size_t id,const fs::path& directory,
        const std::string& mode,const std::string& codec) {
    int value=s.signal(257,false);
    std::string path=(directory/('p'+std::to_string(id)+(codec=="vcd"?".vcd":".dwf"))).string();
    std::vector<std::string> args={"test","--waveform",path,"--wave-mode",mode,
        "--wave-format",codec=="vcd"?"vcd":"dwf","--wave-codec",codec=="vcd"?"raw":codec,
        "--wave-block-events","3"};
    std::vector<char*> argv;for(auto& a:args)argv.push_back(a.data());
    auto wave=std::make_unique<WaveCapture>(s,int(argv.size()),argv.data());
    wave->declare(value,{"top","p"+std::to_string(id)},"data",256,0,false,true);
    wave->start();
    int job=int(s.processes.size());
    s.process([&,id,value,job,pc=0]() mutable {
        auto first=pc%4==0?V::x(257):pc%4==1?V::z(257):
            V::from_words({{uint64_t(pc),0},{0,~uint64_t(0)},{0,0},{0,0},{1,0}},257);
        s.set(value,first);s.assign_nba(value,V(uint64_t(pc),0,257));
        s.print("TRACE p=%0d t=%0t value=%h",{V(id,0,32),V(s.now,0,64),s.get(value)});
        if(id==1&&pc==5)s.finished=true;
        else {
            if(id==3&&pc==9)throw std::runtime_error("discarded late branch");
            if(++pc<12)s.delay(job,1);
        }
    });s.enqueue(job);return wave;
}

int main(int argc,char** argv) {
    try {
        if(argc!=5)throw std::runtime_error("expected reference|workers directory mode codec");
        fs::path directory=fs::absolute(argv[2]);fs::create_directories(directory);
        std::vector<std::unique_ptr<WaveCapture>> waves;
        if(std::string(argv[1])=="reference") {
            std::vector<Output> output;
            std::vector<std::unique_ptr<Sim>> sims;
            for(size_t i=0;i<4;++i) {
                sims.push_back(std::make_unique<Sim>());auto& s=*sims.back();
                s.redirect_output([&,i](uint64_t t,const std::string& text){output.emplace_back(t,i,text);});
                waves.push_back(install(s,i,directory,argv[3],argv[4]));
                // Independent serial oracle for the documented (tick, ID) fence.
                s.run_until(i<=1?5:4);waves.back()->close();
            }
            std::stable_sort(output.begin(),output.end(),[](const auto& a,const auto& b){
                return std::get<0>(a)!=std::get<0>(b)?std::get<0>(a)<std::get<0>(b):std::get<1>(a)<std::get<1>(b);
            });
            for(const auto& e:output)std::cout<<std::get<2>(e);
        } else {
            ConservativeSim machine(size_t(std::stoul(argv[1])),32);machine.enable_global_finish();
            for(size_t i=0;i<4;++i) {
                auto p=machine.partition();waves.push_back(install(machine.kernel(p),i,directory,argv[3],argv[4]));
            }
            machine.run_until(20);
            assert(machine.finished()&&machine.finish_time()==5&&machine.finish_partition()==1);
            for(auto& w:waves)w->close();
        }
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
