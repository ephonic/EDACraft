#pragma once
#include "isolated_relaxation.h"
#include "fermi_newton.h"

namespace tcad { namespace fermi_energy_detail {
using isolated_relaxation_detail::text;
struct Reservoir { real_t mu=0,u=0,capacity=0; };
// This new EOS retains native real_t energies; the established float64-export
// reservoir and its quadrature/inversion path are deliberately unchanged.
inline Reservoir reservoir(real_t density,real_t T,real_t band,const std::vector<double>& valleys) {
    if(density<=0 || T<=0 || valleys.empty() || valleys.size()%4)
        throw std::invalid_argument("positive energy-coordinate FD state and complete valleys required");
    const size_t nv=valleys.size()/4;const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    std::vector<real_t> edge(nv),pref(nv),population(nv),offset(nv);
    real_t origin=band+valleys[3];
    for(size_t v=0;v<nv;++v) {
        for(size_t k=0;k<4;++k)if(!std::isfinite(valleys[4*v+k]))throw std::invalid_argument("finite FD valleys required");
        for(size_t k=0;k<3;++k)if(valleys[4*v+k]<=0)throw std::invalid_argument("positive FD valley masses and degeneracy required");
        edge[v]=band+real_t(valleys[4*v+3]);origin=std::min(origin,edge[v]);
        pref[v]=2*real_t(valleys[4*v+2])*spectral_detail::three_halves(2*PI*real_t(valleys[4*v+1])*m0*KB*T/(h*h));
    }
    real_t logmax=-TCAD_CONST(1e4900),sum=0;
    for(size_t v=0;v<nv;++v) {offset[v]=(edge[v]-origin)/(KB*T);logmax=std::max(logmax,log_q(pref[v])-offset[v]);}
    for(size_t v=0;v<nv;++v)sum+=exp_q(log_q(pref[v])-offset[v]-logmax);
    const real_t mb=log_q(density)-logmax-log_q(sum);
    real_t lo=mb-2,hi=std::max(mb+2,real_t(2)),eta=mb,n=0,u=0,dn=0;
    auto evaluate=[&](real_t e) {
        n=0;u=0;dn=0;
        for(size_t v=0;v<nv;++v) {
            const auto f=fermi_local_detail::integral(e-offset[v]);population[v]=pref[v]*f.density;
            n+=population[v];dn+=pref[v]*f.derivative;
            u+=(edge[v]-origin)*population[v]+TCAD_CONST(1.5)*KB*T*pref[v]*f.energy;
        }
        if(!isfinite_q(n) || !isfinite_q(u) || !isfinite_q(dn))throw FermiStateDomainError("FD energy-coordinate range exceeded");
    };
    for(int k=0;;++k) {evaluate(hi);if(n>=density)break;if(k==63)throw FermiStateDomainError("FD energy-coordinate density bracket exhausted");hi*=2;}
    bool converged=false;
    for(int k=0;k<128;++k) {
        evaluate(eta);
        if(abs_q(n/density-1)<std::max(TCAD_CONST(1e-28),128*epsilon_q())){converged=true;break;}
        if(n>density)hi=eta;else lo=eta;
        const real_t next=dn>0?eta-(n-density)/dn:(lo+hi)/2;
        eta=isfinite_q(next) && next>lo && next<hi?next:(lo+hi)/2;
    }
    if(!converged)throw FermiStateDomainError("FD energy-coordinate density inversion exhausted");
    // Fixed-density derivative from occupation moments. The common band shift
    // is excluded before differentiating; it cannot contaminate heat capacity.
    real_t nt=0,ut=0,ue=0;
    for(size_t v=0;v<nv;++v) {
        const auto f=fermi_local_detail::integral(eta-offset[v]);
        const real_t upper=std::max(real_t(64),eta-offset[v]+64);
        std::vector<real_t> cuts={0,upper,std::min(upper,std::max(real_t(0),eta-offset[v]-16)),
            std::min(upper,std::max(real_t(0),eta-offset[v]+16))};
        std::sort(cuts.begin(),cuts.end());cuts.erase(std::unique(cuts.begin(),cuts.end()),cuts.end());
        real_t de=0;
        for(size_t k=1;k<cuts.size();++k) {
            const real_t a=sqrt_q(cuts[k-1]),b=sqrt_q(cuts[k]);
            for(const auto& node:spectral_detail::quadrature()) {
                const real_t t=a+(b-a)*(node.first+1)/2,o=spectral_detail::occupation(eta-offset[v]-t*t);
                de+=(b-a)*node.second*t*t*t*t*o*(1-o);
            }
        }
        de/=(TCAD_CONST(1.5)*sqrt_q(PI)/2);
        const real_t a=pref[v]/T*(TCAD_CONST(1.5)*f.density+offset[v]*f.derivative);
        nt+=a;ut+=(edge[v]-origin)*a+TCAD_CONST(1.5)*KB*pref[v]*(TCAD_CONST(2.5)*f.energy+offset[v]*de);
        ue+=(edge[v]-origin)*pref[v]*f.derivative+TCAD_CONST(1.5)*KB*T*pref[v]*de;
    }
    const real_t capacity=ut-ue*nt/dn;
    if(!(capacity>0) || !isfinite_q(capacity))throw FermiStateDomainError("positive FD fixed-density heat capacity required");
    return {origin+KB*T*eta,origin*density+u,capacity};
}

struct Temperature {double T=0;real_t eq=0,error=0,lower=0,upper=0;int iterations=0;};
inline Temperature temperature(real_t density,double Tl,real_t excess,real_t band,const std::vector<double>& valleys) {
    if(!(Tl>1 && Tl<1e5) || !std::isfinite(Tl))throw FermiStateDomainError("FD lattice temperature outside open bounds");
    const auto eq=reservoir(density,real_t(Tl),band,valleys);
    auto cell=[&](double T,const Reservoir& r,Temperature& out) {
        const double left=std::nextafter(T,-std::numeric_limits<double>::infinity());
        const double right=std::nextafter(T,std::numeric_limits<double>::infinity());
        const real_t low=reservoir(density,(real_t(left)+real_t(T))/2,band,valleys).u-eq.u;
        const real_t high=reservoir(density,(real_t(right)+real_t(T))/2,band,valleys).u-eq.u;
        if(excess<low || excess>high)return false;
        out.T=T;out.eq=eq.u;out.error=(r.u-eq.u)-excess;out.lower=low;out.upper=high;return true;
    };
    Temperature out;
    const real_t ulp=real_t(std::nextafter(Tl,std::numeric_limits<double>::infinity()))-real_t(Tl);
    if(abs_q(excess)<=eq.capacity*ulp && cell(Tl,eq,out))return out;
    real_t lo=1,hi=1e5;
    if(excess<=reservoir(density,lo,band,valleys).u-eq.u || excess>=reservoir(density,hi,band,valleys).u-eq.u)
        throw FermiStateDomainError("FD excess energy outside temperature bounds");
    double T=double(std::max(lo+1,std::min(hi-1,real_t(Tl)+excess/eq.capacity)));
    for(int k=0;k<128;++k) {
        ++out.iterations;const auto r=reservoir(density,real_t(T),band,valleys);
        const real_t error=(r.u-eq.u)-excess;
        const real_t spacing=real_t(std::nextafter(T,std::numeric_limits<double>::infinity()))-real_t(T);
        if(abs_q(error)<=2*r.capacity*spacing && cell(T,r,out))return out;
        if(error>0)hi=real_t(T);else lo=real_t(T);
        real_t trial=real_t(T)-error/r.capacity;
        if(!(trial>lo && trial<hi))trial=(lo+hi)/2;
        const double next=double(trial);
        if(next==T) {
            const double neighbor=std::nextafter(T,error>0?-std::numeric_limits<double>::infinity():std::numeric_limits<double>::infinity());
            if(neighbor>1 && neighbor<1e5 && cell(neighbor,reservoir(density,real_t(neighbor),band,valleys),out))return out;
            throw FermiStateDomainError("FD excess temperature rounding cell exhausted");
        }
        T=next;
    }
    throw FermiStateDomainError("FD excess temperature inversion exhausted");
}
} // namespace fermi_energy_detail

// State tuples: n,Tl,Tc (initialize) or excess,band. Result tuples:
// rounded Tc,quad Ueq,excess,EOS error,lower/upper excess of the rounding cell.
inline std::vector<std::string> native_fermi_energy_coordinates_raw(const std::vector<std::string>& states,
        const std::vector<double>& valleys,bool initialize) {
    const auto s=fermi_local_detail::decimals(states);
    if(s.empty() || s.size()%4)throw std::invalid_argument("FD energy-coordinate tuple coverage invalid");
    std::vector<std::string> output;
    for(size_t i=0;i<s.size();i+=4) {
        const double Tl=double(s[i+1]);real_t e=s[i+2];
        if(initialize) {
            const double Tc=double(e);if(!(Tc>1 && Tc<1e5))throw std::invalid_argument("initial FD carrier temperature bounds invalid");
            e=fermi_energy_detail::reservoir(s[i],real_t(Tc),s[i+3],valleys).u-
                fermi_energy_detail::reservoir(s[i],real_t(Tl),s[i+3],valleys).u;
        }
        const auto t=fermi_energy_detail::temperature(s[i],Tl,e,s[i+3],valleys);
        for(real_t value:{real_t(t.T),t.eq,e,t.error,t.lower,t.upper})output.push_back(fermi_energy_detail::text(value));
    }
    return output;
}
} // namespace tcad
