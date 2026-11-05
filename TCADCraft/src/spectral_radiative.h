#pragma once
// Instantaneous matched direct-gap transitions and a maintained Planck bath.
// The caller supplies a phenomenological per-pair-state spontaneous rate.
#include "fermi_local.h"

namespace tcad {
namespace radiative_detail {
inline bool integer(real_t x) {
#ifdef TCAD_USE_FLOAT128
    return floorq(x)==x;
#else
    return floorl(x)==x;
#endif
}
inline real_t log_f(real_t x) {
    return x>=0 ? -log_q(1+exp_q(-x)) : x-log_q(1+exp_q(x));
}
inline real_t difference(real_t a,real_t b) {
    return a>=b ? -exp_q(a)*expm1_q(b-a) : exp_q(b)*expm1_q(a-b);
}
} // namespace radiative_detail

// Tn,Tp,Tphoton,mu_n,mu_p,Ec,Eh,mn/m0,mp/m0,pair_degeneracy,gamma/s.
// Spin-conserving matched transitions: two spins are counted ONCE in pair DOS.
inline std::vector<real_t> spectral_radiative_values(const std::vector<real_t>& s) {
    if(s.size()!=11) throw std::invalid_argument("native radiative state requires 11 scalars");
    for(real_t v:s) if(!isfinite_q(v)) throw std::invalid_argument("finite radiative inputs required");
    if(s[0]<=0 || s[1]<=0 || s[2]<=0 || s[7]<=0 || s[8]<=0 || s[9]<=0 ||
       !radiative_detail::integer(s[9]) || s[10]<0 || s[5]+s[6]<=0)
        throw std::invalid_argument("positive temperatures, masses, integer pair degeneracy and gap; nonnegative rate required");
    const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    const real_t an=s[8]/(s[7]+s[8]),ap=1-an;
    const real_t reduced=s[7]*s[8]/(s[7]+s[8]),gap=s[5]+s[6];
    const real_t tn=KB*s[0]/an,tp=KB*s[1]/ap,tg=KB*s[2];
    const real_t scale=std::min({tn,tp,tg});
    const real_t upper=std::max({80*tn,80*tp,80*tg,
        (s[3]-s[5])/an+80*tn,(s[4]-s[6])/ap+80*tp});
    std::vector<real_t> breaks={0,upper};
    for(real_t thermal:{tn,tp,tg}) for(int k:{1,4,16,64,80})
        breaks.push_back(std::min(upper,k*thermal));
    for(int k:{-64,-16,0,16,64}) {
        breaks.push_back(std::min(upper,std::max(TCAD_CONST(0.0),(s[3]-s[5])/an+k*tn)));
        breaks.push_back(std::min(upper,std::max(TCAD_CONST(0.0),(s[4]-s[6])/ap+k*tp)));
    }
    std::sort(breaks.begin(),breaks.end());breaks.erase(std::unique(breaks.begin(),breaks.end()),breaks.end());
    const real_t base=2*PI*reduced*m0/(h*h);
    const real_t D0=2*s[9]*spectral_detail::three_halves(base)/(sqrt_q(PI)/2);
    real_t spontaneous=0,stimulated=0,absorption=0,uen=0,uep=0,uan=0,uap=0,net=0,jn=0,jp=0,entropy=0;
    if(s[10]>0) for(size_t segment=1;segment<breaks.size();++segment) {
        const real_t a=sqrt_q(breaks[segment-1]/scale),b=sqrt_q(breaks[segment]/scale);
        for(const auto& node:spectral_detail::quadrature()) {
            const real_t t=a+(b-a)*(node.first+1)/2,x=scale*t*t;
            const real_t en=s[5]+an*x,ep=s[6]+ap*x;
            const real_t z=(s[3]-en)/(KB*s[0]),w=(s[4]-ep)/(KB*s[1]);
            const real_t y=(gap+x)/tg;
            // Stable even for tiny photon occupancy and gaps well below kT.
            const real_t log1N=-log_q(-expm1_q(-y)),logN=-y+log1N;
            const real_t logsp=radiative_detail::log_f(z)+radiative_detail::log_f(w);
            const real_t la=logsp+log1N;
            const real_t lb=radiative_detail::log_f(-z)+radiative_detail::log_f(-w)+logN;
            const real_t weight=s[10]*D0*sqrt_q(x)*scale*(b-a)*t*node.second;
            const real_t sp=weight*exp_q(logsp),st=weight*exp_q(logsp+logN);
            const real_t ab=weight*exp_q(lb),d=weight*radiative_detail::difference(la,lb);
            spontaneous+=sp;stimulated+=st;absorption+=ab;
            uen+=(sp+st)*en;uep+=(sp+st)*ep;uan+=ab*en;uap+=ab*ep;
            net+=d;jn+=d*en;jp+=d*ep;entropy+=KB*d*(la-lb);
        }
    }
    return {spontaneous,stimulated,absorption,spontaneous+stimulated,net,
        uen,uep,uan,uap,-net,-net,net,-jn,-jp,jn+jp,
        0,0,-jn-jp+(jn+jp),entropy};
}
inline std::vector<double> native_spectral_radiative_raw(const std::vector<std::string>& state) {
    using namespace fermi_local_detail;
    return exported(spectral_radiative_values(decimals(state)));
}
} // namespace tcad
