#pragma once
// Explicit classical parabolic-DOS primitives. No FD state/occupation conversion,
// Python callback, precomputed chemical potential or change to an existing ABI.
#include "fermi_local.h"
#include <cstdio>

namespace tcad {
namespace boltzmann_detail {
inline std::string text(real_t x) {
    if(!isfinite_q(x)) throw std::invalid_argument("nonfinite native MB result");
    char b[128];
#ifdef TCAD_USE_FLOAT128
    const int n=quadmath_snprintf(b,sizeof(b),"%.36Qe",x);
#else
    const int n=std::snprintf(b,sizeof(b),"%.36Le",x);
#endif
    if(n<0 || size_t(n)>=sizeof(b)) throw std::runtime_error("native MB decimal formatting failed");
    return std::string(b,size_t(n));
}
inline std::vector<std::string> exported(const std::vector<real_t>& values) {
    std::vector<std::string> out;for(real_t x:values)out.push_back(text(x));return out;
}
inline std::vector<real_t> valleys(const std::vector<std::string>& raw) {
    if(raw.empty() || raw.size()%4) throw std::invalid_argument("native MB valley width invalid");
    auto v=fermi_local_detail::decimals(raw);
    for(size_t i=0;i<v.size();i+=4)
        if(v[i]<=0 || v[i+1]<=0 || v[i+2]<=0)
            throw std::invalid_argument("positive native MB valley masses and degeneracy required");
    return v;
}
struct Reservoir {
    real_t n,T,band,mu,u;
    std::vector<real_t> populations;
};
inline Reservoir reservoir(real_t n,real_t T,real_t band,const std::vector<real_t>& v) {
    if(n<=0 || T<=1 || T>=TCAD_CONST(1e5))
        throw std::invalid_argument("positive native MB density and 1<T<100000 required");
    const size_t nv=v.size()/4;
    const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    real_t origin=band+v[3];
    for(size_t j=0;j<nv;++j)origin=std::min(origin,band+v[4*j+3]);
    std::vector<real_t> logs(nv);real_t maximum=0;
    for(size_t j=0;j<nv;++j) {
        const real_t base=2*PI*v[4*j+1]*m0*KB*T/(h*h);
        if(base<=0 || !isfinite_q(base))throw std::invalid_argument("native MB DOS range exceeded");
        logs[j]=log_q(2*v[4*j+2])+TCAD_CONST(1.5)*log_q(base)-(band+v[4*j+3]-origin)/(KB*T);
        if(j==0 || logs[j]>maximum)maximum=logs[j];
    }
    real_t sum=0;for(real_t x:logs)sum+=exp_q(x-maximum);
    const real_t logZ=maximum+log_q(sum);
    Reservoir r{n,T,band,origin+KB*T*(log_q(n)-logZ),0,{}};
    for(size_t j=0;j<nv;++j) {
        const real_t population=n*exp_q(logs[j]-logZ);
        r.populations.push_back(population);
        r.u+=population*(band+v[4*j+3]+TCAD_CONST(1.5)*KB*T);
    }
    if(!isfinite_q(r.mu) || !isfinite_q(r.u))throw std::invalid_argument("native MB reservoir range exceeded");
    return r;
}
} // namespace boltzmann_detail

// Decimal states: repeated [n_m3,T_K,band_J]. Valleys: repeated
// [normal_mass/m0,DOS_mass/m0,degeneracy,same_offset_J] as decimals.
// Output per state: mu,u,n,followed by one population per valley.
inline std::vector<std::string> native_boltzmann_reservoir_raw(
    const std::vector<std::string>& states,const std::vector<std::string>& raw_valleys) {
    if(states.empty() || states.size()%3)throw std::invalid_argument("native MB state width invalid");
    auto s=fermi_local_detail::decimals(states);auto v=boltzmann_detail::valleys(raw_valleys);
    std::vector<real_t> out;
    for(size_t i=0;i<s.size();i+=3) {
        auto r=boltzmann_detail::reservoir(s[i],s[i+1],s[i+2],v);
        out.insert(out.end(),{r.mu,r.u,r.n});out.insert(out.end(),r.populations.begin(),r.populations.end());
    }
    return boltzmann_detail::exported(out);
}

// State: owner and neighbor physical [n,T,band] triples. No precomputed mu.
// Geometry: phi_o,phi_n,phi_f,z,mobility_o,mobility_n,area,do,dn,path.
// path: 0 endpoint barrier, 2 linear-series bulk; no thermionic mode.
// Output: number,total,material,entropy,sampled_min_f,sampled_max_f, then
//         particle,total energy per valley. All outputs remain native decimals.
inline std::vector<std::string> native_boltzmann_bulk_face_raw(
    const std::vector<std::string>& state,const std::vector<std::string>& geometry,
    const std::vector<std::string>& raw_valleys) {
    if(state.size()!=6 || geometry.size()!=10)throw std::invalid_argument("native MB face width invalid");
    const auto s=fermi_local_detail::decimals(state),g=fermi_local_detail::decimals(geometry);
    const auto v=boltzmann_detail::valleys(raw_valleys);
    if((g[3]!=-1 && g[3]!=1) || g[4]<=0 || g[5]<=0 || g[6]<=0 || g[7]<=0 || g[8]<0 || (g[9]!=0 && g[9]!=2))
        throw std::invalid_argument("native MB face geometry, mobility or bulk mode invalid");
    const auto a=boltzmann_detail::reservoir(s[0],s[1],s[2],v),b=boltzmann_detail::reservoir(s[3],s[4],s[5],v);
    const real_t qo=g[3]*si_transport::elementary_charge,scale=KB*std::max(a.T,b.T);
    const real_t muo=a.mu+qo*g[0],mun=b.mu+qo*g[1];
    const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    std::vector<real_t> out(6+v.size()/2,0);real_t number=0,total=0,entropy=0,minimum=0,maximum=0;bool first=true;
    for(size_t j=0;j<v.size();j+=4) {
        const real_t uo=a.band+v[j+3]+qo*g[0],un=b.band+v[j+3]+qo*g[1],high=std::max(uo,un);
        const real_t ao0=(muo-high)/(KB*a.T),an0=(mun-high)/(KB*b.T);
        const real_t pop=exp_q(std::max(ao0,an0));
        if(!isfinite_q(pop) || pop<=0)throw std::invalid_argument("native MB spectral population outside representable range");
        const real_t ref=KB*300,base=2*PI*v[j+1]*m0*ref/(h*h);
        const real_t dos=2*v[j+2]*spectral_detail::three_halves(base);
        const real_t D0=dos/(spectral_detail::three_halves(ref)*sqrt_q(PI)/2);
        std::vector<real_t> breaks={0,80};
        if(g[9]==2)breaks.push_back(std::min(TCAD_CONST(80.),abs_q(un-uo)/scale));
        std::sort(breaks.begin(),breaks.end());breaks.erase(std::unique(breaks.begin(),breaks.end()),breaks.end());
        real_t rate=0,energy=0,sigma=0;
        for(size_t k=1;k<breaks.size();++k) {
            const real_t lo=sqrt_q(breaks[k-1]),hi=sqrt_q(breaks[k]);
            for(const auto& node:spectral_detail::quadrature()) {
                const real_t t=lo+(hi-lo)*(node.first+1)/2,e=high+scale*t*t;
                const real_t ao=ao0-scale/(KB*a.T)*t*t,an=an0-scale/(KB*b.T)*t*t;
                const real_t lf=exp_q(ao),rf=exp_q(an);
                if(first){minimum=std::min(lf,rf);maximum=std::max(lf,rf);first=false;}
                else{minimum=std::min({minimum,lf,rf});maximum=std::max({maximum,lf,rf});}
                const real_t diff=ao>=an ? exp_q(ao)*(-expm1_q(an-ao)) : exp_q(an)*expm1_q(ao-an);
                real_t conductance=0;
                if(g[9]==0)conductance=g[6]/(g[7]/g[4]+g[8]/g[5])*2/(3*si_transport::elementary_charge)*D0*spectral_detail::three_halves(e-high);
                else {
                    const real_t middle=uo+(un-uo)*g[7]/(g[7]+g[8]);
                    auto mean=[](real_t x,real_t y){const real_t a=sqrt_q(x),b=sqrt_q(y);return a*b*(a+b)/2;};
                    const real_t resistance=g[7]/g[4]/mean(e-uo,e-middle)+(g[8]>0 ? g[8]/g[5]/mean(e-middle,e-un) : real_t(0));
                    conductance=g[6]*2/(3*si_transport::elementary_charge)*D0/resistance;
                }
                const real_t flow=scale*(hi-lo)*t*node.second*conductance*diff;
                rate+=flow;energy+=flow*e;sigma+=KB*flow*(ao-an);
            }
        }
        out[6+j/2]=rate;out[7+j/2]=energy;number+=rate;total+=energy;entropy+=sigma;
    }
    out[0]=number;out[1]=total;out[2]=total-qo*g[2]*number;out[3]=entropy;out[4]=minimum;out[5]=maximum;
    return boltzmann_detail::exported(out);
}
} // namespace tcad
