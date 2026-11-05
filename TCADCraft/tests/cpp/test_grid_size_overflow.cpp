#include <device_simulator.h>
#include <device_simulator_double.h>
#include <algorithm>
#include <array>
#include <iostream>
#include <limits>
#include <set>
#include <string>
using namespace tcad;
using Dims=std::array<size_t,3>;
namespace {
size_t cases=0,failed=0;
const size_t limit=std::numeric_limits<size_t>::max();
bool overflow(const Dims& d) {
    if(!d[0]||!d[1]||!d[2])return false;
    const __uint128_t plane=(__uint128_t)d[0]*d[1];
    return plane>limit || plane*d[2]>limit;
}
void emit(const char* kind,const Dims& d,bool rejected,size_t count,bool passed,int route=-1) {
    ++cases;if(!passed)++failed;
    std::cout<<"{\"case\":"<<cases<<",\"kind\":\""<<kind<<"\",\"dims\":["<<d[0]<<','<<d[1]<<','<<d[2]<<"],\"route\":"<<route<<",\"rejected\":"<<(rejected?"true":"false")<<",\"count\":"<<count<<",\"passed\":"<<(passed?"true":"false")<<"}\n";
}
void count_case(const Dims& d) {
    Grid3D g{d[0],d[1],d[2],1,1,1};size_t count=0;bool rejected=false;
    try {count=g.npts();}catch(const std::overflow_error& e) {rejected=std::string(e.what())=="grid node count overflows size_t";}
    const bool expected=overflow(d);
    const size_t product=d[0]*d[1]*d[2];
    emit("count",d,rejected,count,rejected==expected&&(expected||count==product));
}
void constructor_case(const Dims& d,int route) {
    Grid3D g{d[0],d[1],d[2],1,1,1};bool rejected=false;size_t count=0;
    try {
        // Observe construction itself: a later checked npts() getter must
        // not turn successful construction into an apparent rejection.
        if(route==0){PoissonSolver s(g);}
        else if(route==1){GummelSolver s(g,GummelOptions{});}
        else if(route==2){NewtonSolver s(g,NewtonOptions{});}
        else if(route==3){DeviceSimulator s(d[0],d[1],d[2],1,1,1);}
        else {DeviceSimulatorDouble s(d[0],d[1],d[2],1,1,1);}
        count=d[0]*d[1]*d[2];
    }catch(const std::overflow_error& e){rejected=std::string(e.what())=="grid node count overflows size_t";}
    const bool expected=overflow(d);
    emit("constructor",d,rejected,count,rejected==expected&&(expected||count==d[0]*d[1]*d[2]),route);
}
}
int main(int argc,char** argv) {try {
    const bool observe=argc>1&&std::string(argv[1])=="--observe";
    const size_t bits=sizeof(size_t)*8,high=size_t(1)<<(bits-1),quarter=size_t(1)<<(bits-2);
    std::set<Dims> counts,constructors;
    for(size_t x:{size_t(0),size_t(1),size_t(2),size_t(3),size_t(7),high,high+1,quarter,limit/3,limit})
    for(size_t y:{size_t(0),size_t(1),size_t(2),size_t(3),size_t(7),high,high+1,quarter,limit/3,limit})
    for(size_t z:{size_t(0),size_t(1),size_t(2),size_t(3),size_t(7),high,high+1,quarter,limit/3,limit})counts.insert({x,y,z});
    for(size_t divisor:{size_t(3),size_t(5),size_t(7),size_t(17),size_t(257),size_t(65537)})for(int offset:{-1,0,1}) {
        Dims d{limit/divisor+(size_t)offset,divisor,1};std::sort(d.begin(),d.end());
        do {counts.insert(d);}while(std::next_permutation(d.begin(),d.end()));
    }
    for(Dims d:{Dims{high,2,1},Dims{high+1,2,1},Dims{limit,limit,1},Dims{quarter,4,1},Dims{size_t(1)<<(bits/2),size_t(1)<<(bits/4),size_t(1)<<(bits-bits/2-bits/4)}}) {
        std::sort(d.begin(),d.end());do {constructors.insert(d);}while(std::next_permutation(d.begin(),d.end()));
    }
    for(Dims d:{Dims{0,1,1},Dims{1,0,1},Dims{1,1,0},Dims{1,1,1},Dims{2,1,1},Dims{1,3,2},Dims{3,3,3}})constructors.insert(d);
    for(const auto& d:counts)count_case(d);
    for(const auto& d:constructors) {
        if(overflow(d)&&d[0]*d[1]*d[2]>8)throw std::runtime_error("unsafe baseline fixture");
        for(int route=0;route<5;++route)constructor_case(d,route);
    }
    std::cout<<"{\"summary\":true,\"profile\":\""<<compiled_constants_profile_name()<<"\",\"mantissa_bits\":"<<real_mantissa_bits()<<",\"size_bits\":"<<bits<<",\"count_cases\":"<<counts.size()<<",\"constructor_cases\":"<<constructors.size()*5<<",\"cases\":"<<cases<<",\"failed\":"<<failed<<"}\n";
    return !observe&&failed?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
