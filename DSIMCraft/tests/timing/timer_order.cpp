#include <dsim/runtime.hpp>
#include <cassert>
#include <map>
#include <random>
#include <tuple>
using namespace dsim;
using Event=std::tuple<uint64_t,int,int>;
int main() {
    // Independent ordered-map oracle: equal-time FIFO, new timers inserted while
    // draining, sparse far-future events, and reuse of a live checkpoint.
    constexpr int count=4096;
    std::mt19937 rng(1017);std::vector<uint64_t> times;
    std::map<std::pair<uint64_t,uint64_t>,std::pair<int,int>> pending;
    uint64_t sequence=0;
    Sim sim;std::vector<Event> actual,expected;
    for(int i=0;i<count;++i) {
        const uint64_t t=i%17?1+rng()%127:(uint64_t(1)<<48)+rng()%7;
        times.push_back(t);pending[{t,sequence++}]={i,0};
        const int p=sim.process([&,i,generation=0]() mutable {
            actual.emplace_back(sim.now,i,generation);
            if(++generation<3&&i%3==0)sim.delay(i,1+i%11);
        });
        assert(p==i);sim.delay(p,t);
    }
    while(!pending.empty()) {
        const auto e=*pending.begin();pending.erase(pending.begin());
        auto [id,generation]=e.second;const auto t=e.first.first;
        expected.emplace_back(t,id,generation);
        if(++generation<3&&id%3==0)pending[{t+1+id%11,sequence++}]={id,generation};
    }
    sim.run_until(35);const auto prefix=actual;auto cp=sim.checkpoint();
    sim.run();assert(actual==expected);
    for(int i=0;i<4;++i){sim.restore(cp);actual=prefix;sim.run();assert(actual==expected);}
    // The largest representable timestamp must retain insertion order too.
    Sim end;std::vector<int> order;
    for(int i=0;i<100;++i){int p=end.process([&,i]{order.push_back(i);});end.delay(p,UINT64_MAX);}
    end.run();for(int i=0;i<100;++i)assert(order.at(i)==i);
    std::cout<<"PASS stable timer order: "<<expected.size()<<" events, repeated live restore and UINT64_MAX ties\n";
}
