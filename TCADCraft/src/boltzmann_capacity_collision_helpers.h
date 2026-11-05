#pragma once
#include "boltzmann_capacity_arithmetic.h"
#include "boltzmann_affine_transport.h"
namespace tcad { namespace mb_capacity_collision_detail {
namespace ar=mb_capacity_arithmetic_detail;using I=ar::Integer;struct Stop {};
inline I imported(const std::vector<std::string>& raw) {return ar::normalized(ar::sum(raw));}
inline I scalar(real_t x) {return imported(boltzmann_detail::exported({x}));}
inline I multiply(I a,I b) {
    if(ar::count(ar::write(a)[2],4096)*ar::count(ar::write(b)[2],4096)>65536)
        throw std::invalid_argument("original trace product pair budget exceeded");
    return ar::times(a,b);
}
inline I divide_atoms(const std::vector<I>& atoms,I b,I& remainder) {
    I q;remainder={};
    for(const auto& a:atoms) {
        const auto h=ar::rounded_ratio(a,b);
        const auto l=ar::rounded_ratio(ar::plus(a,multiply(b,h),-1),b);
        const auto part=ar::plus(h,l);
        q=ar::plus(q,part);
        remainder=ar::plus(remainder,ar::plus(a,multiply(b,part),-1));
    }
    return q;
}
inline std::vector<I> atoms(I a) {
    const auto wire=ar::write(a);std::vector<I> result;
    for(size_t j=3;j<wire.size();j+=2)
        result.push_back(ar::coefficient(wire[j],ar::bounded_decimal_integer(wire[j+1])));
    return result;
}
} }
