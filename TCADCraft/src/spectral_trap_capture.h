#pragma once
// Standalone local source operator. It does not advance a device or Poisson.
// Single nondegenerate electron trap; supplied constant capture coefficients.
#include "fermi_local.h"

namespace tcad {
namespace trap_capture_detail {
inline real_t log_occupation(real_t x) {
    return x>=0 ? -log_q(1+exp_q(-x)) : x-log_q(1+exp_q(x));
}
inline real_t difference(real_t a,real_t b) {
    // Difference of positive rates from their logarithms, including near balance.
    return a>=b ? -exp_q(a)*expm1_q(b-a) : exp_q(b)*expm1_q(a-b);
}
struct Moments {
    real_t capture=0,emission=0,capture_energy=0,emission_energy=0;
    real_t net=0,net_energy=0,entropy=0,density=0;
};
inline Moments integrate(real_t T,real_t Tl,real_t mu,real_t band,
    real_t level,real_t Nt,real_t coefficient,real_t filled,
    const std::vector<real_t>& valleys,bool holes) {
    Moments m;
    const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    const real_t scale=KB*std::min(T,Tl);
    // Electron capture needs an empty trap; hole capture needs a filled trap.
    const real_t cprob=holes?filled:1-filled,eprob=holes?1-filled:filled;
    for(size_t v=0;v<valleys.size();v+=4) {
        const real_t edge=band+valleys[v+3];
        const real_t gap=holes?edge+level:edge-level;
        if(gap<0) throw std::invalid_argument("trap level must lie within every valley gap");
        const real_t upper=std::max({80*KB*T,80*KB*Tl,mu-edge+80*KB*T})/scale;
        std::vector<real_t> breaks={0,upper};
        for(real_t temperature:{T,Tl}) for(int k:{1,4,16,64,80})
            breaks.push_back(std::min(upper,k*KB*temperature/scale));
        for(int k:{-64,-16,0,16,64})
            breaks.push_back(std::min(upper,std::max(TCAD_CONST(0.0),(mu-edge+k*KB*T)/scale)));
        std::sort(breaks.begin(),breaks.end());breaks.erase(std::unique(breaks.begin(),breaks.end()),breaks.end());
        const real_t base=2*PI*valleys[v+1]*m0/(h*h);
        const real_t D0=2*valleys[v+2]*spectral_detail::three_halves(base)/(sqrt_q(PI)/2);
        for(size_t segment=1;segment<breaks.size();++segment) {
            const real_t a=sqrt_q(breaks[segment-1]),b=sqrt_q(breaks[segment]);
            for(const auto& node:spectral_detail::quadrature()) {
                const real_t t=a+(b-a)*(node.first+1)/2,kinetic=scale*t*t;
                const real_t energy=edge+kinetic,heat=gap+kinetic;
                const real_t weight=D0*sqrt_q(kinetic)*scale*(b-a)*t*node.second;
                const real_t x=(mu-energy)/(KB*T);
                const real_t logF=log_occupation(x),logVacancy=log_occupation(-x);
                m.density+=weight*exp_q(logF);
                if(coefficient==0 || Nt==0) continue;
                const real_t logC=log_q(cprob)+logF;
                const real_t logE=log_q(eprob)+logVacancy-heat/(KB*Tl);
                const real_t factor=weight*Nt*coefficient;
                const real_t capture=factor*exp_q(logC),emission=factor*exp_q(logE);
                const real_t net=factor*difference(logC,logE);
                m.capture+=capture;m.emission+=emission;
                m.capture_energy+=capture*energy;m.emission_energy+=emission*energy;
                m.net+=net;m.net_energy+=net*energy;
                m.entropy+=KB*net*(logC-logE);
            }
        }
    }
    return m;
}
} // namespace trap_capture_detail

// States: Tn,Tp,Tl,mu_n,mu_p,Ec,Eh,Nt,Et,c_n,c_p,f.
// Valleys: normal mass, DOS mass, valley degeneracy, offset (all decimals).
// No density inversion: mu_n/mu_p are explicit material quasi-Fermi energies.
inline std::vector<real_t> spectral_trap_capture_values(
    const std::vector<real_t>& s,const std::vector<real_t>& n,const std::vector<real_t>& p) {
    using namespace fermi_local_detail;
    if(s.size()!=12 || n.empty() || p.empty() || n.size()%4 || p.size()%4)
        throw std::invalid_argument("native trap capture dimensions invalid");
    for(const auto& values:{s,n,p}) for(real_t v:values)
        if(!isfinite_q(v)) throw std::invalid_argument("finite native trap inputs required");
    if(s[0]<=0 || s[1]<=0 || s[2]<=0 || s[7]<0 || s[9]<0 || s[10]<0 || s[11]<=0 || s[11]>=1)
        throw std::invalid_argument("positive temperatures, open occupancy, nonnegative trap density and coefficients required");
    real_t en=s[5]+n[3],ep=s[6]+p[3];
    for(const auto& valleys:{n,p}) for(size_t v=0;v<valleys.size();v+=4)
        if(valleys[v]<=0 || valleys[v+1]<=0 || valleys[v+2]<=0)
            throw std::invalid_argument("positive trap DOS masses and degeneracy required");
    for(size_t v=0;v<n.size();v+=4) en=std::min(en,s[5]+n[v+3]);
    for(size_t v=0;v<p.size();v+=4) ep=std::min(ep,s[6]+p[v+3]);
    if(en+ep<=0 || s[8]>en || s[8]<-ep)
        throw std::invalid_argument("positive material gap and in-gap trap level required");
    const auto a=trap_capture_detail::integrate(s[0],s[2],s[3],s[5],s[8],s[7],s[9],s[11],n,false);
    const auto b=trap_capture_detail::integrate(s[1],s[2],s[4],s[6],s[8],s[7],s[10],s[11],p,true);
    const real_t trapped=a.net-b.net;
    const real_t trap_energy=s[8]*trapped;
    const real_t heat=a.net_energy+b.net_energy-trap_energy;
    // Do not subtract independently rounded exported gross rates for net fluxes.
    return {a.capture,a.emission,b.capture,b.emission,
        a.capture_energy,a.emission_energy,b.capture_energy,b.emission_energy,
        a.net,b.net,-a.net,-b.net,s[7]>0?trapped/s[7]:TCAD_CONST(0.0),
        -a.net_energy,-b.net_energy,trap_energy,heat,-si_transport::elementary_charge*trapped,
        si_transport::elementary_charge*a.net-si_transport::elementary_charge*b.net-si_transport::elementary_charge*trapped,
        -a.net_energy-b.net_energy+trap_energy+heat,a.entropy+b.entropy,a.density,b.density};
}
inline std::vector<double> native_spectral_trap_capture_raw(
    const std::vector<std::string>& state,const std::vector<std::string>& vn,
    const std::vector<std::string>& vp) {
    using namespace fermi_local_detail;
    return exported(spectral_trap_capture_values(decimals(state),decimals(vn),decimals(vp)));
}
} // namespace tcad
