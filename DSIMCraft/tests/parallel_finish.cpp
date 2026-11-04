#define DSIM_TIMING_ENABLED 1
#define DSIM_PATH_ENABLED 1
#define DSIM_WIDE_VALUES 1
#define DSIM_WAVE_ENABLED 1
#include <dsim/parallel.hpp>
#include <dsim/path.hpp>
#include <cassert>
#include <tuple>
using namespace dsim;

using Changes=std::vector<std::tuple<uint64_t,int,V>>;
struct Capture {
    Changes changes;
    std::vector<uint64_t> ticks;
    static void change(void* raw,uint64_t t,int id,V value) {
        static_cast<Capture*>(raw)->changes.emplace_back(t,id,value);
    }
    static void tick(void* raw,uint64_t t) {static_cast<Capture*>(raw)->ticks.push_back(t);}
};
template<class F> static void rejects(F fn) {
    bool rejected=false;try{fn();}catch(const std::runtime_error&){rejected=true;}assert(rejected);
}
static void transactions() {
    Sim s,other;int value=s.signal(257,false);s.set(value,V(0,0,257));
    auto state=std::make_shared<int>(0);s.register_state(state);
    Capture wave;s.attach_wave(&wave,Capture::change,Capture::tick);
    std::vector<std::pair<uint64_t,V>> notifications;
    s.observe_resolved([&](uint64_t t,int id,V v){if(id==value)notifications.emplace_back(t,v);});
    std::string printed;s.redirect_output([&](uint64_t,const std::string& t){printed+=t;});
    auto four=V::from_words({{1,0},{0,~uint64_t(0)},{1,0},{0,0},{1,0}},257);
    int job=-1;job=s.process([&,pc=0]() mutable {
        ++*state;++pc;s.set(value,pc==1?four:V::z(257));s.print("%0t",{V(s.now,0,64)});
        if(pc<2)s.delay(job,2);
    });s.enqueue(job);
    auto cp=s.begin_transaction();
    rejects([&]{s.begin_transaction();});rejects([&]{other.commit_transaction(cp);});
    s.run_until(3);assert(*state==2&&printed.empty()&&wave.changes.empty()&&notifications.empty());
    s.rollback_transaction(cp);assert(s.now==0&&*state==0&&s.get(value).same(V(0,0,257)));
    auto second=s.begin_transaction();
    rejects([&]{s.commit_transaction(cp);});rejects([&]{s.rollback_transaction(cp);});
    s.run_until(1);s.commit_transaction(second);
    assert(*state==1&&s.get(value).same(four)&&printed=="0\n");
    assert(notifications.size()==1&&notifications[0].first==0&&notifications[0].second.same(four));
    assert(wave.changes.size()==1&&std::get<2>(wave.changes[0]).same(four));
    rejects([&]{s.commit_transaction(second);});rejects([&]{s.rollback_transaction(second);});
    auto third=s.begin_transaction();s.run_until(3);s.commit_transaction(third);
    assert(*state==2&&s.get(value).same(V::z(257))&&printed=="0\n2\n");

    // A partly committed external sink is terminal, never silently replayed.
    Sim bad;int calls=0;bad.redirect_output([&](uint64_t,const std::string&){++calls;throw std::runtime_error("sink");});
    int p=bad.process([&]{bad.print("first",{});bad.print("second",{});});bad.enqueue(p);
    auto token=bad.begin_transaction();bad.run_until(0);rejects([&]{bad.commit_transaction(token);});
    assert(calls==1&&!bad.transaction_pending(token));rejects([&]{bad.rollback_transaction(token);});
}

static std::string circuit(size_t workers,uint64_t window,size_t winner,uint64_t finish,bool split,bool channel) {
    ConservativeSim machine(workers,window);machine.enable_global_finish();
    std::vector<int> values;std::vector<std::shared_ptr<int>> states;
    std::vector<Capture> waves(4);
    for(size_t i=0;i<4;++i) {
        auto id=machine.partition();assert(id==i);auto& s=machine.kernel(id);
        int value=s.signal(8,false);s.set(value,V(0xff,0,8));values.push_back(value);
        auto state=std::make_shared<int>(0);s.register_state(state);states.push_back(state);
        s.attach_wave(&waves[i],Capture::change,Capture::tick);
        int job=int(s.processes.size());
        int created=s.process([&,i,value,state,job,pc=0]() mutable {
            auto& local=machine.kernel(i);++*state;local.set(value,V(uint64_t(pc),0,8));
            local.print("P%0d %0t",{V(i,0,32),V(local.now,0,64)});
            if(i==3&&local.now==9)throw std::runtime_error("failure beyond global finish");
            // A second partition requests finish at the same tick; ID wins ties.
            if((i==winner||i==winner+1)&&local.now==finish)local.finished=true;
            else if(++pc<16)local.delay(job,1);
        });assert(job==created);s.enqueue(job);
    }
    int input=-1;
    if(channel) {
        input=machine.kernel(2).signal(8,true);
        machine.connect(0,values[0],2,input,2,123);
    }
    std::ostringstream output;auto* previous=std::cout.rdbuf(output.rdbuf());
    try {
        if(split&&finish>3)machine.run_until(3);
        machine.run_until(12);
    }catch(...){std::cout.rdbuf(previous);throw;}
    std::cout.rdbuf(previous);
    assert(machine.finished()&&machine.finish_time()==finish&&machine.finish_partition()==winner);
    assert(machine.stats.window_replays==1);
    auto windows=machine.stats.windows;machine.run_until(30);assert(machine.stats.windows==windows);
    rejects([&]{machine.enable_global_finish();});
    std::ostringstream expected;
    for(uint64_t t=0;t<=finish;++t)for(size_t i=0;i<4;++i)
        if(t<finish||i<=winner)expected<<"P"<<i<<" "<<t<<"\n";
    assert(output.str()==expected.str());
    for(size_t i=0;i<4;++i) {
        auto count=int(finish+uint64_t(i<=winner));assert(*states[i]==count);
        auto& s=machine.kernel(i);assert(s.now==(i<=winner?finish:finish?finish-1:0));
        assert(s.get(values[i]).same(count?V(uint64_t(count-1),0,8):V(0xff,0,8)));
        assert(size_t(std::count_if(waves[i].changes.begin(),waves[i].changes.end(),
            [&](const auto& event){return std::get<1>(event)==values[i];}))==size_t(count));
        for(const auto& event:waves[i].changes)assert(std::get<0>(event)<finish||(i<=winner&&std::get<0>(event)==finish));
        for(auto tick:waves[i].ticks)assert(tick<finish||(i<=winner&&tick==finish));
    }
    if(channel&&finish>=4&&winner<2)assert(machine.kernel(2).get(input).same(V(finish-3,0,8)));
    return output.str();
}

static void failures() {
    ConservativeSim legacy(1);auto id=legacy.partition();auto& s=legacy.kernel(id);
    int job=s.process([&]{s.finished=true;});s.enqueue(job);rejects([&]{legacy.run_until(1);});
    ConservativeSim machine(2);machine.enable_global_finish();
    std::vector<int> values;
    for(int i=0;i<3;++i) {
        auto p=machine.partition();auto& local=machine.kernel(p);int v=local.signal(8,false);values.push_back(v);
        local.set(v,V(0,0,8));int process=local.process([&,p,v] {
            auto& k=machine.kernel(p);k.set(v,V(0xff,0,8));k.print("must stay private",{});
            if(p==1)throw std::runtime_error("worker failure");
        });local.enqueue(process);
    }
    std::ostringstream output;auto* previous=std::cout.rdbuf(output.rdbuf());
    rejects([&]{machine.run_until(10);});std::cout.rdbuf(previous);assert(output.str().empty());
    for(size_t i=0;i<values.size();++i)assert(machine.kernel(i).get(values[i]).same(V(0,0,8)));
    rejects([&]{machine.run_until(10);});

    PartitionGraph graph;auto first=graph.node(1),second=graph.node(1);
    AutoConservativeSim automatic(graph,2);automatic.enable_global_finish();
    auto& left=automatic.kernel(first);auto& right=automatic.kernel(second);
    int stop=left.process([&]{left.finished=true;});left.delay(stop,3);
    int later=right.process([&]{right.print("late",{});});right.delay(later,4);
    automatic.run_until(10);assert(automatic.finished()&&automatic.finish_time()==3);

    // Exception ordering uses the same (tick, partition) fence as output.
    for(auto failure_time:{3,5,7})for(auto failure_partition:{0,2}) {
        ConservativeSim ordered(2,32);ordered.enable_global_finish();
        for(int i=0;i<3;++i) {
            auto p=ordered.partition();auto& k=ordered.kernel(p);
            if(i==1) {int f=k.process([&k]{k.finished=true;});k.delay(f,5);}
            else if(i==failure_partition) {int f=k.process([]{throw std::runtime_error("ordered failure");});k.delay(f,uint64_t(failure_time));}
        }
        if(failure_time<5||(failure_time==5&&failure_partition==0))rejects([&]{ordered.run_until(20);});
        else {ordered.run_until(20);assert(ordered.finished()&&ordered.finish_time()==5);}
    }
}

int main() {
    transactions();
    for(auto workers:{1,2,4})for(auto window:{1,2,3,7,1024})
        for(size_t winner:{size_t(0),size_t(1),size_t(2)})for(uint64_t t:{uint64_t(0),uint64_t(5)})
            for(bool split:{false,true})for(bool channel:{false,true})
                circuit(size_t(workers),uint64_t(window),winner,t,split,channel);
    failures();
    std::cout<<"PASS transactional parallel finish: independent timeline, tied/zero-time finish, 1/2/4 workers, windows, channels, registered state, wide values, waveform/output isolation and failures\n";
}
