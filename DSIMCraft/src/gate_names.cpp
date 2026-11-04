#include "gate_compiler.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>
namespace dsim {
namespace {
void append32(std::string& s,uint32_t n){for(int i=0;i<4;++i)s+=char(n>>(8*i));}
uint32_t read32(const char* p){uint32_t n=0;for(int i=0;i<4;++i)n|=uint32_t(static_cast<unsigned char>(p[i]))<<(8*i);return n;}
}
std::string GateTimingNames::encode(const std::vector<std::string>& path) {
    std::string key;
    for(const auto& part:path) {
        if(part.empty()||part.size()>UINT32_MAX)throw std::runtime_error("invalid timing path component");
        append32(key,uint32_t(part.size()));key+=part;
    }
    return key;
}
uint32_t GateTimingNames::append(const std::vector<std::string>& path) {
    auto encoded=encode(path);
    if(encoded.size()>UINT32_MAX-4 || bytes.size()>UINT32_MAX-4-encoded.size())throw std::runtime_error("timing name pool exceeds 4 GiB");
    auto offset=uint32_t(bytes.size());std::string size;append32(size,uint32_t(encoded.size()));
    bytes.insert(bytes.end(),size.begin(),size.end());bytes.insert(bytes.end(),encoded.begin(),encoded.end());return offset;
}
std::string_view GateTimingNames::key(uint32_t offset) const {
    if(offset>bytes.size()||bytes.size()-offset<4)throw std::runtime_error("invalid timing name offset");
    auto size=read32(bytes.data()+offset);
    if(size>bytes.size()-offset-4)throw std::runtime_error("invalid timing name length");
    return {bytes.data()+offset+4,size};
}
void GateTimingNames::finalize() {
    sorted_instances.clear();
    for(size_t i=0;i<instance_names.size();++i)if(instance_names[i]!=UINT32_MAX)sorted_instances.push_back(uint32_t(i));
    std::sort(sorted_instances.begin(),sorted_instances.end(),[&](uint32_t a,uint32_t b){return key(instance_names[a])<key(instance_names[b]);});
    for(size_t i=1;i<sorted_instances.size();++i)if(key(instance_names[sorted_instances[i-1]])==key(instance_names[sorted_instances[i]]))throw std::runtime_error("duplicate timing instance path");
}
int GateTimingNames::find_instance(const std::vector<std::string>& path) const {
    auto encoded=encode(path);
    auto it=std::lower_bound(sorted_instances.begin(),sorted_instances.end(),std::string_view(encoded),[&](uint32_t id,std::string_view target){return key(instance_names[id])<target;});
    return it!=sorted_instances.end()&&key(instance_names[*it])==encoded?int(*it):-1;
}
}
