#pragma once
#include "boltzmann_scaled_arithmetic.h"

namespace tcad {
// Each numerator atom is one signed binary113 dyadic (or zero). Keep this
// partition: merging atoms before rounding changes the legacy expansion law.
// All quotient terms and exact residuals are returned; no state is committed.
inline std::vector<std::string> native_mb_scaled_component_division_raw(
    const std::vector<std::vector<std::string>>& atoms,
    const std::vector<std::string>& divisor) {
    using namespace mb_scaled_arithmetic_detail;
    if(real_mantissa_bits()!=113 || atoms.size()>4096)
        throw std::invalid_argument("binary113 bounded component division required");
    const auto b=read(divisor);
    if(!b.sign)throw std::invalid_argument("scaled component division by zero");
    size_t evidence=count(divisor[2],4096);
    std::vector<std::string> records;
    Integer quotient,remainder;
    const auto save=[&](Integer x,std::vector<std::string>& target) {
        const auto wire=write(x);
        evidence+=count(wire[2],4096);
        if(evidence>4096)throw std::invalid_argument("original cumulative component evidence budget exceeded");
        target.push_back(std::to_string(wire.size()));
        target.insert(target.end(),wire.begin(),wire.end());
    };
    for(const auto& atom:atoms) {
        const auto a=read(atom);
        if(count(atom[2],4096)>1)
            throw std::invalid_argument("one binary113 numerator atom required");
        evidence+=count(atom[2],4096);
        if(evidence>4096)throw std::invalid_argument("original cumulative component evidence budget exceeded");
        const auto first=rounded_ratio(a,b);
        const auto second=rounded_ratio(plus(a,times(b,first),-1),b);
        const auto q=plus(first,second);
        const auto r=plus(a,times(b,q),-1);
        quotient=plus(quotient,q);remainder=plus(remainder,r);
        save(first,records);save(second,records);save(r,records);
    }
    std::vector<std::string> out={"mb_scaled_component_division_v1","113",std::to_string(atoms.size())};
    save(quotient,out);save(remainder,out);
    out.insert(out.end(),records.begin(),records.end());
    return out;
}
} // namespace tcad
