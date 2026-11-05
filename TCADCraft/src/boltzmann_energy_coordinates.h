#pragma once
#include "boltzmann_spectral.h"

namespace tcad { namespace boltzmann_energy_detail {
struct Thermal {
    real_t mean=0,capacity=0,energy=0;
    std::vector<real_t> delta,probability;
};
// Fixed-density classical valley redistribution: common T^(3/2) cancels.
// Use offset differences before adding the common band, so an arbitrary
// energy origin cannot erase valley splitting or contaminate heat capacity.
inline Thermal thermal(real_t T,const std::vector<real_t>& v) {
    if(!(T>=1 && T<=TCAD_CONST(1e5)))throw std::invalid_argument("MB energy temperature outside closed evaluation bounds");
    Thermal r;const size_t nv=v.size()/4;
    real_t minimum=v[3];for(size_t j=0;j<nv;++j)minimum=std::min(minimum,v[4*j+3]);
    std::vector<real_t> logs(nv);real_t maximum=0;
    for(size_t j=0;j<nv;++j) {
        const real_t d=v[4*j+3]-minimum;r.delta.push_back(d);
        logs[j]=log_q(v[4*j+2])+TCAD_CONST(1.5)*log_q(v[4*j+1])-d/(KB*T);
        if(!isfinite_q(logs[j]))throw std::invalid_argument("MB energy valley range exceeded");
        if(j==0 || logs[j]>maximum)maximum=logs[j];
    }
    real_t sum=0;for(real_t x:logs)sum+=exp_q(x-maximum);
    for(size_t j=0;j<nv;++j) {
        const real_t p=exp_q(logs[j]-maximum)/sum;r.probability.push_back(p);r.mean+=p*r.delta[j];
    }
    real_t variance=0;
    for(size_t j=0;j<nv;++j) {
        const real_t centered=(r.delta[j]-r.mean)/(KB*T);
        variance+=r.probability[j]*centered*centered;
    }
    r.capacity=KB*(TCAD_CONST(1.5)+variance);
    r.energy=TCAD_CONST(1.5)*KB*T+r.mean;
    if(!(r.capacity>0) || !isfinite_q(r.capacity) || !isfinite_q(r.energy))
        throw std::invalid_argument("MB energy/capacity range exceeded");
    return r;
}
inline real_t difference(real_t T,real_t ref,const Thermal& base,const Thermal& current) {
    const real_t dt=T-ref;
    if(dt==0)return 0;
    real_t shift=current.mean-base.mean;
    if(abs_q(dt)<=TCAD_CONST(1e-4)*ref) {
        // Normalize reweighting before expm1; the centered covariance gives
        // exactly zero for dt=0 and avoids subtracting two finite DOS energies.
        std::vector<real_t> logs(base.delta.size());real_t largest=0;
        for(size_t j=0;j<logs.size();++j) {
            logs[j]=base.delta[j]/(KB*ref)*(dt/T);largest=std::max(largest,logs[j]);
        }
        real_t denominator=0,numerator=0;
        for(size_t j=0;j<logs.size();++j) {
            const real_t x=logs[j]-largest;
            denominator+=base.probability[j]*exp_q(x);
            numerator+=base.probability[j]*(base.delta[j]-base.mean)*expm1_q(x);
        }
        if(!(denominator>0))throw std::invalid_argument("MB energy reweighting range exceeded");
        shift=numerator/denominator;
    }
    const real_t result=TCAD_CONST(1.5)*KB*dt+shift;
    if(!isfinite_q(result))throw std::invalid_argument("MB energy difference range exceeded");
    return result;
}
struct Coordinate {real_t T,error,budget;int iterations;};
inline Coordinate invert(real_t n,real_t ref,real_t target,const std::vector<real_t>& v,const Thermal& base,int maximum) {
    real_t lo=1,hi=TCAD_CONST(1e5);
    const real_t low=n*difference(lo,ref,base,thermal(lo,v)),high=n*difference(hi,ref,base,thermal(hi,v));
    if(!isfinite_q(low) || !isfinite_q(high))throw std::invalid_argument("MB energy bracket range exceeded");
    if(!(target>low && target<high))throw std::invalid_argument("MB excess outside open temperature bounds");
    const real_t budget=64*epsilon_q()*std::max({abs_q(target),n*KB*ref,n*KB});
    const real_t capacity=n*base.capacity;
    if(!(capacity>0 && budget>0) || !isfinite_q(capacity) || !isfinite_q(budget))
        throw std::invalid_argument("MB energy inversion scale range exceeded");
    real_t T=ref+target/capacity;
    if(!(T>lo && T<hi))T=(lo+hi)/2;
    for(int k=0;k<maximum;++k) {
        const auto r=thermal(T,v);const real_t error=n*difference(T,ref,base,r)-target;
        if(abs_q(error)<=budget)return {T,error,budget,k+1};
        if(error>0)hi=T;else lo=T;
        real_t next=T-error/(n*r.capacity);
        if(!(next>lo && next<hi))next=lo+(hi-lo)/2;
        if(next==T)throw std::invalid_argument("MB excess inversion stagnated outside residual budget");
        T=next;
    }
    throw std::invalid_argument("MB excess inversion evaluation budget exhausted");
}
} // namespace boltzmann_energy_detail

// Repeated state [n,Tref,Tcarrier (initialize) or signed excess_J_m3,band].
// Per-state decimal output: native T,reference thermal energy,authoritative
// excess,EOS residual,residual budget,capacity,mu,total energy,origin,iterations.
// The excess remains authoritative even below native temperature resolution.
inline std::vector<std::string> native_boltzmann_energy_coordinates_raw(
    const std::vector<std::string>& states,const std::vector<std::string>& raw_valleys,
    bool initialize=false,int max_iterations=128) {
    if(states.empty() || states.size()%4 || max_iterations<1 || max_iterations>512)
        throw std::invalid_argument("MB energy state width or evaluation budget invalid");
    const auto s=fermi_local_detail::decimals(states),v=boltzmann_detail::valleys(raw_valleys);
    std::vector<real_t> out;
    for(size_t i=0;i<s.size();i+=4) {
        const real_t n=s[i],ref=s[i+1],band=s[i+3];
        if(!(n>0 && ref>1 && ref<TCAD_CONST(1e5)))throw std::invalid_argument("positive MB density and open reference temperature bounds required");
        const auto base=boltzmann_energy_detail::thermal(ref,v);
        real_t excess=s[i+2];
        if(initialize) {
            if(!(excess>1 && excess<TCAD_CONST(1e5)))throw std::invalid_argument("initial MB temperature outside open bounds");
            const real_t difference=boltzmann_energy_detail::difference(excess,ref,base,boltzmann_energy_detail::thermal(excess,v));
            excess=n*difference;
            if(difference!=0 && excess==0)throw std::invalid_argument("nonzero initial MB excess underflows");
        }
        if(!isfinite_q(excess))throw std::invalid_argument("MB energy coordinate range exceeded");
        const auto decoded=boltzmann_energy_detail::invert(n,ref,excess,v,base,max_iterations);
        const auto cell=boltzmann_energy_detail::thermal(decoded.T,v);
        const auto reservoir=boltzmann_detail::reservoir(n,decoded.T,band,v);
        real_t offset=v[3];for(size_t j=0;j<v.size();j+=4)offset=std::min(offset,v[j+3]);
        const real_t origin=band+offset,capacity=n*cell.capacity,equilibrium=n*base.energy;
        const real_t error=decoded.error,budget=decoded.budget;
        if(!(capacity>0 && equilibrium>0 && budget>0) || !isfinite_q(error) || !isfinite_q(capacity))
            throw std::invalid_argument("representable positive MB energy scales required");
        // Form total energy from authoritative excess, not the rounded T.
        const real_t total=n*origin+equilibrium+excess;
        out.insert(out.end(),{decoded.T,equilibrium,excess,error,budget,capacity,reservoir.mu,total,origin,real_t(decoded.iterations)});
    }
    return boltzmann_detail::exported(out);
}
} // namespace tcad
