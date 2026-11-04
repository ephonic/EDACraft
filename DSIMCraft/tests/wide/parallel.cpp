#define DSIM_WIDE_VALUES 1
#include "dsim/parallel.hpp"
#include <cassert>
#include <tuple>
using namespace dsim;
using Trace=std::vector<std::pair<uint64_t,V>>;
int main(){
    const int width=257;
    std::vector<V> values={V::from_words({{1,0},{0,0},{0,0},{0,0},{1,0}},width),V::from_words({{1,0},{0,~uint64_t(0)},{0,0},{0,0},{0,1}},width),V::ones(width)};
    Sim serial;int source=serial.signal(width,false),target=serial.signal(width,false);serial.set(source,V(0,0,width));
    Trace reference;serial.observe_resolved([&](uint64_t t,int id,V value){if(id==target)reference.push_back({t,value});});
    auto step=std::make_shared<size_t>(0);int producer=-1;producer=serial.process([&,step]{serial.set(source,values.at((*step)++));if(*step<values.size())serial.delay(producer,5);});
    // External deliveries use the same positive-delay transport semantics as channels.
    serial.deliver_at(3,target,-1,V(0,0,width));
    for(size_t i=0;i<values.size();++i)serial.deliver_at(3+5*i,target,-1,values[i]);
    serial.enqueue(producer);serial.run_until(25);
    for(size_t workers:{size_t(1),size_t(2),size_t(4)}){
        ConservativeSim parallel(workers,2);auto left=parallel.partition(),right=parallel.partition();auto& a=parallel.kernel(left);auto& b=parallel.kernel(right);
        int input=a.signal(width,false),output=b.signal(width,false);a.set(input,V(0,0,width));
        parallel.connect(left,input,right,output,3);
        Trace observed;b.observe_resolved([&](uint64_t t,int id,V value){if(id==output)observed.push_back({t,value});});
        auto index=std::make_shared<size_t>(0);int process=-1;process=a.process([&,index,input]{a.set(input,values.at((*index)++));if(*index<values.size())a.delay(process,5);});a.enqueue(process);
        parallel.run_until(7);parallel.run_until(25);
        assert(observed.size()==reference.size());
        for(size_t i=0;i<reference.size();++i)assert(observed[i].first==reference[i].first&&observed[i].second.same(reference[i].second));
        assert(b.get(output).same(V::ones(width)));
    }
    std::cout<<"PASS multiword 257-bit conservative transport with 1/2/4 workers and X/Z high limbs\n";
}
