#define DSIM_TIMING_ENABLED 1
#define DSIM_WIDE_VALUES 1
#include <dsim/parallel_waveform.hpp>
#include <cassert>
using namespace dsim;

static V bit(int code) {return code==2?V::x(1):code==3?V::z(1):V(code,0,1);}
struct Pins {int data,flag;};
static Pins install(Sim& s,size_t id,const std::string& scenario) {
    int data=s.signal(257,false);
#ifdef DSIM_COMPACT_GATES
    int flag=s.compact_net(),alias=s.compact_net();
#else
    int flag=s.signal(1,true),alias=s.signal(1,true);
#endif
    s.connect_net(flag,0,alias,0);
    int job=int(s.processes.size());
    s.process([&s,id,data,flag,job,scenario,pc=0]() mutable {
        V first=pc%4==0?V::x(257):pc%4==1?V::z(257):
            V::from_words({{uint64_t(pc)+(pc%4==2?id:0),0},
                {0,pc%4==3?~uint64_t(0):0},{0,0},{0,0},{1,0}},257);
        s.set(data,first);
        s.drive(flag,10,bit((pc+int(id))%4));
        s.drive(flag,11,pc%3?V::z(1):V(1,0,1));
        s.assign_nba(data,V(uint64_t(pc)+16*id,0,257));
        if((scenario=="finish"&&id==1&&pc==3)||(scenario=="finish0"&&id==1&&pc==0))s.finished=true;
        else if((scenario=="finish"&&id==3&&pc==9)||(scenario=="failure"&&id==2&&pc==1))
            throw std::runtime_error("test worker failure");
        else if(++pc<12)s.delay(job,id%3+1);
    });s.enqueue(job);return {data,flag};
}
template<class F> static void rejects(F fn) {
    bool rejected=false;try{fn();}catch(const std::runtime_error&){rejected=true;}assert(rejected);
}
static void lifecycle() {
    ConservativeSim engine(1);
    auto token=engine.observe_committed_windows([](uint64_t){throw std::runtime_error("expired observer invoked");});
    token.reset();engine.partition();engine.run_until(0);
    rejects([&]{engine.observe_committed_windows([](uint64_t){});});
}
static void failed_attachment(const std::string& path) {
    ConservativeSim engine(1);engine.partition();engine.partition();
    auto& a=engine.kernel(0);auto& b=engine.kernel(1);
    int x=a.signal(1,false),y=b.signal(1,false);
    auto cp=b.begin_transaction();
    std::vector<std::string> options={"test","--waveform",path,"--wave-format","vcd"};
    std::vector<char*> args;for(auto& option:options)args.push_back(option.data());
    {
        ParallelWaveCapture wave(engine,int(args.size()),args.data());
        wave.declare(0,x,{"top"},"a",0,0,false,false);
        wave.declare(1,y,{"top"},"b",0,0,false,false);
        // a attaches successfully; b rejects attachment during its transaction.
        rejects([&]{wave.start();});
    }
    b.rollback_transaction(cp);
    a.set(x,V(1,0,1)); // Must never call a freed Source after partial attachment.
}

int main(int argc,char** argv) {
    try {
        if(argc<7)throw std::runtime_error("expected scenario workers window path ordered|settled vcd|raw|zstd [scope]");
        const std::string scenario=argv[1],mode=argv[5],codec=argv[6];
        if(scenario=="attachment") {failed_attachment(argv[4]);std::cout<<"PASS attachment cleanup\n";return 0;}
        size_t workers=std::stoul(argv[2]);uint64_t window=std::stoull(argv[3]);
        std::vector<std::string> options={"test","--waveform",argv[4],"--wave-mode",mode,
            "--wave-format",codec=="vcd"?"vcd":"dwf","--wave-codec",codec=="vcd"?"raw":codec,
            "--wave-block-events","3","--wave-timescale","1ps"};
        if(argc>7) {options.push_back("--wave-scope");options.push_back(argv[7]);}
        if(argc>8) {options.push_back("--wave-compression-jobs");options.push_back(argv[8]);}
        std::vector<char*> args;for(auto& option:options)args.push_back(option.data());
        if(scenario=="channels") {
            PartitionGraph graph;auto a=graph.node(2),alias=graph.node(1),b=graph.node(3),c=graph.node(2);
            auto wire=graph.edge(a,alias,0),first=graph.edge(alias,b,3),second=graph.edge(b,c,4);
            AutoConservativeSim machine(graph,workers,window);machine.enable_global_finish();
            for(size_t i=0;i<machine.partition_count();++i)machine.partition_kernel(i).time_precision_fs=1000;
            auto& left=machine.kernel(a);auto& middle=machine.kernel(b);auto& right=machine.kernel(c);
            int source=left.signal(1,true),copy=left.signal(1,true);
            int input=middle.signal(1,true),output=middle.signal(1,true),dest=right.signal(1,true);
            machine.connect(wire,source,copy);machine.connect(first,copy,input,100);machine.connect(second,output,dest,200);
            int generator=int(left.processes.size());
            left.process([&left,source,generator,pc=0]() mutable {
                static const int bits[]={0,1,2,3,1,0};left.drive(source,300,bit(bits[pc]));
                if(++pc<6)left.delay(generator,5);
            });left.enqueue(generator);
            int relay=int(middle.processes.size());
            middle.process([&middle,input,output,relay]{middle.drive(output,400,inv(middle.get(input)));middle.wait(relay,{{input,0}});});middle.enqueue(relay);
            ParallelWaveCapture wave(machine,int(args.size()),args.data(),"1ps");
            for(auto item:std::vector<std::tuple<size_t,int,std::string>>{{a,source,"source"},{alias,copy,"copy"},{b,input,"input"},{b,output,"output"},{c,dest,"dest"}})
                wave.declare(machine.plan().owner[std::get<0>(item)],std::get<1>(item),{"top"},std::get<2>(item),0,0,true,false);
            wave.start();machine.run_until(12);machine.run_until(40);wave.close();
            assert(machine.stats().messages>0);std::cout<<"PASS channels\n";
        } else {
            ConservativeSim machine(workers,window);
            // Test both worker-direct buffering and transactional finish/replay.
            if(scenario!="direct")machine.enable_global_finish();
            std::vector<Pins> pins;
            for(size_t i=0;i<4;++i) {auto p=machine.partition();machine.kernel(p).time_precision_fs=1000;pins.push_back(install(machine.kernel(p),i,scenario));}
            ParallelWaveCapture wave(machine,int(args.size()),args.data(),"1ps");
            for(size_t i=0;i<4;++i) {
                auto scope=std::vector<std::string>{"top","p"+std::to_string(i)};
                wave.declare(i,pins[i].data,scope,"data",256,0,false,true);
                wave.declare(i,pins[i].flag,scope,"flag",0,0,true,false);
                wave.declare(i,pins[i].flag,scope,"escaped.alias[0]",0,0,true,true);
            }
            wave.start();rejects([&]{wave.start();});
            rejects([&]{wave.declare(0,pins[0].data,{"top"},"late",256,0,false,true);});
            if(scenario=="failure") {
                rejects([&]{machine.run_until(20);});rejects([&]{machine.run_until(20);});
            } else {
                machine.run_until(2);machine.run_until(20);
                if(scenario=="finish"||scenario=="finish0")
                    assert(machine.finished()&&machine.finish_time()==(scenario=="finish"?6:0)&&machine.finish_partition()==1);
            }
            wave.close();wave.close();
            if(scenario!="failure")machine.run_until(25); // Detached weak hook is inert.
            std::cout<<"PASS "<<scenario<<" replays="<<machine.stats.window_replays<<'\n';
        }
        lifecycle();return 0;
    }catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
