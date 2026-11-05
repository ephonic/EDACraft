#pragma once
#include "boltzmann_relaxation.h"

namespace tcad { namespace boltzmann_rebase_detail {
inline real_t fused(real_t a,real_t b,real_t c) {
#ifdef TCAD_USE_FLOAT128
    return fmaq(a,b,c);
#else
    return std::fma(a,b,c);
#endif
}
inline std::vector<real_t> shift(real_t capacity,real_t oldref,real_t newref) {
    // Error-free TwoDiff and FMA TwoProd on the supported normal range.
    const real_t hi=oldref-newref,bvirt=oldref-hi,avirt=hi+bvirt;
    const real_t lo=(oldref-avirt)+(bvirt-newref);
    const real_t ph=capacity*hi,pl=capacity*lo;
    return {ph,fused(capacity,hi,-ph),pl,fused(capacity,lo,-pl)};
}
}
inline std::vector<std::string> native_boltzmann_reference_rebase_raw(
    const std::vector<std::string>& state,const std::vector<std::string>& parameters,
    const std::vector<std::string>& vn,const std::vector<std::string>& vp,const std::string& reference) {
    if(real_mantissa_bits()!=113 || state.size()<6 || state.size()>4092 || parameters.size()!=14)
        throw std::invalid_argument("MB reference rebase requires 113 bits, bounded state and 14 parameters");
    boltzmann_relaxation_detail::equal_offsets(vn);boltzmann_relaxation_detail::equal_offsets(vp);
    const auto s=fermi_local_detail::decimals(state),p=fermi_local_detail::decimals(parameters);
    const real_t ref=fermi_local_detail::decimals({reference})[0];
    for(size_t j:{0,1,2,3,4,5,8,9})if(!(p[j]>0))throw std::invalid_argument("positive MB configuration scales required");
    if(!(s[0]>0 && s[1]>0 && s[2]>1 && s[2]<TCAD_CONST(1e5) && ref>1 && ref<TCAD_CONST(1e5)
        && p[12]>1 && p[13]<TCAD_CONST(1e5) && p[12]<p[13]
        && p[0]>=TCAD_CONST(1e-1000) && p[0]<=TCAD_CONST(1e1000)))
        throw std::invalid_argument("MB reference/capacity normal range exceeded");
    const real_t C[]={TCAD_CONST(1.5)*KB*s[0],TCAD_CONST(1.5)*KB*s[1]};
    for(real_t c:C)if(!(c>0) || !isfinite_q(c))throw std::invalid_argument("MB capacity range exceeded");
    auto views=[&](real_t r,const std::vector<real_t>& extra) {
        real_t ell=s[3];for(size_t j=6;j<s.size();++j)ell+=s[j];for(real_t x:extra)ell+=x;
        const real_t Tl=r+ell/p[0];
        std::vector<real_t> v={Tl,Tl+s[4]/C[0],Tl+s[5]/C[1]};
        for(real_t T:v)if(!isfinite_q(T) || T<p[12] || T>p[13])
            throw std::invalid_argument("MB rebased temperature view outside bounds");
        return v;
    };
    const auto oldview=views(s[2],{}),terms=boltzmann_rebase_detail::shift(p[0],s[2],ref),newview=views(ref,terms);
    auto result=state;result[2]=boltzmann_detail::exported({ref})[0];
    const auto raw_terms=boltzmann_detail::exported(terms);result.insert(result.end(),raw_terms.begin(),raw_terms.end());
    const auto ov=boltzmann_detail::exported(oldview),nv=boltzmann_detail::exported(newview);
    result.insert(result.end(),ov.begin(),ov.end());result.insert(result.end(),nv.begin(),nv.end());return result;
}
} // namespace tcad
