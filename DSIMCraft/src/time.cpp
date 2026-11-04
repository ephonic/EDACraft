#include "time.hpp"
#include "sdf.hpp"
#include <algorithm>
#include <cctype>
#include <limits>
#include <map>
#include <stdexcept>
namespace dsim {
uint64_t parse_time_unit(const std::string& text) {
    static const std::map<std::string,uint64_t> units={{"fs",1},{"ps",1000},{"ns",1000000},{"us",1000000000},{"ms",1000000000000},{"s",1000000000000000}};
    auto pos=text.find_first_not_of("0123456789");
    auto n=text.substr(0,pos);auto unit=pos==std::string::npos?std::string():text.substr(pos);
    auto found=units.find(unit);
    if((n!="1"&&n!="10"&&n!="100")||found==units.end())throw std::runtime_error("time unit must be 1/10/100 followed by s/ms/us/ns/ps/fs");
    return std::stoull(n)*found->second;
}
TimeScale parse_timescale(const std::string& text) {
    std::string s;for(unsigned char c:text)if(!std::isspace(c))s+=char(c);
    auto p=s.find('/');if(p==std::string::npos||s.find('/',p+1)!=std::string::npos)throw std::runtime_error("timescale requires unit/precision");
    TimeScale t{parse_time_unit(s.substr(0,p)),parse_time_unit(s.substr(p+1))};
    if(t.precision_fs>t.unit_fs)throw std::runtime_error("timescale precision must not be coarser than unit");
    return t;
}
std::string time_unit_name(uint64_t fs) {
    for(const auto& u:{std::pair<const char*,uint64_t>{"s",1000000000000000ULL},{"ms",1000000000000ULL},{"us",1000000000ULL},{"ns",1000000ULL},{"ps",1000ULL},{"fs",1ULL}})
        if(fs==u.second||fs==10*u.second||fs==100*u.second)return std::to_string(fs/u.second)+u.first;
    throw std::runtime_error("invalid physical time unit");
}
uint64_t TimingConfig::global_precision() const {
    auto value=modules.empty()?defaults.precision_fs:modules.front().scale.precision_fs;
    for(const auto& m:modules)value=std::min(value,m.scale.precision_fs);
    if(declared_precision_fs)value=std::min(value,declared_precision_fs);
    return value;
}
TimeScale TimingConfig::at(size_t line) const {
    auto it=std::upper_bound(modules.begin(),modules.end(),line,[](size_t n,const ModuleTimeScale& m){return n<m.line;});
    return it==modules.begin()?defaults:std::prev(it)->scale;
}
uint64_t delay_ticks(const std::string& decimal,TimeScale scope,uint64_t global_fs) {
    if(!global_fs||scope.precision_fs<global_fs||scope.precision_fs%global_fs)throw std::runtime_error("inconsistent simulation precision");
    auto local=sdf_ticks(decimal,scope.unit_fs,scope.precision_fs),factor=scope.precision_fs/global_fs;
    if(local>std::numeric_limits<uint64_t>::max()/factor)throw std::runtime_error("delay exceeds simulation time range");
    return local*factor;
}
}
