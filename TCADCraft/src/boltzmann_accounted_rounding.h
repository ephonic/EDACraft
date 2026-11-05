#pragma once
#include "boltzmann_scaled_transport.h"
#include "boltzmann_capacity_arithmetic.h"
namespace tcad { namespace mb_accounted_rounding_detail {
namespace transport=mb_scaled_transport_detail;
namespace ar=mb_capacity_arithmetic_detail;
using I=ar::Integer;
// RN113 directly from guard/sticky bits. No wide ratio or widened workspace.
inline I rounded(I a) {
    a=ar::normalized(a);const size_t width=ar::bits(a.words);
    if(width<=113)return a;
    const size_t low=width-113;I q;q.sign=a.sign;q.exponent=a.exponent+int(low);q.words.assign(8,0);
    for(size_t j=0;j<113;++j)q.words[j/16]|=mb_scaled_detail::bit(a.words,low+j)<<(j%16);
    bool sticky=false;for(size_t j=0;j+1<low;++j)sticky=sticky || mb_scaled_detail::bit(a.words,j);
    if(mb_scaled_detail::bit(a.words,low-1) && (sticky || (q.words[0]&1)))q.words=ar::add(q.words,{1});
    return ar::normalized(q);
}
inline std::vector<std::string> endpoint(const std::vector<std::string>& raw) {
    if(real_mantissa_bits()!=113)throw std::invalid_argument("accounted rounding requires binary113");
    auto p=transport::decode(raw);transport::valid(p);std::vector<I> tails;
    for(auto& x:p.v){const auto old=x;x=rounded(x);tails.push_back(ar::plus(old,x,-1));}
    transport::valid(p);const auto state=transport::emit(p);size_t evidence=0;
    for(const auto& x:p.v)evidence+=ar::count(ar::write(x)[2],4096);
    for(const auto& x:tails)evidence+=ar::count(ar::write(x)[2],4096);
    if(evidence>4096)throw std::invalid_argument("accounted rounding combined saved component budget exceeded");
    std::vector<std::string> out={"mb_accounted_rounding_v1","113",std::to_string(evidence)};
    transport::packet(out,state);for(const auto& x:tails)transport::packet(out,ar::write(x));return out;
}
} }
