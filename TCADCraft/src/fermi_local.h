#pragma once

// FD thermodynamics and local conservation rows for the matched-valley,
// shared-temperature model. Poisson and the nonlinear driver are external.
#include "fermi_spectral.h"
#include <cstdlib>
#include <cerrno>
#include <string>

namespace tcad {
namespace fermi_local_detail {
inline real_t decimal(const std::string& s) {
    if (s.empty()) throw std::invalid_argument("empty native decimal");
    char* end=nullptr;
    errno=0;
#ifdef TCAD_USE_FLOAT128
    const real_t x=strtoflt128(s.c_str(),&end);
#else
    const real_t x=strtold(s.c_str(),&end);
#endif
    const int parse_errno=errno;
    if (end!=s.data()+s.size() || !isfinite_q(x))
        throw std::invalid_argument("finite complete native decimal required");
    // ERANGE also marks representable subnormals: only a nonzero input
    // rounded all the way to zero loses its authoritative coordinate.
    if (x==0 && parse_errno==ERANGE)
        throw std::invalid_argument("nonzero native decimal underflows to zero");
    return x;
}
inline std::vector<real_t> decimals(const std::vector<std::string>& values) {
    std::vector<real_t> result;result.reserve(values.size());
    for (const auto& s:values) result.push_back(decimal(s));
    return result;
}
inline std::vector<double> exported(const std::vector<real_t>& values) {
    std::vector<double> result;result.reserve(values.size());
    for (real_t x:values) {
        if (!isfinite_q(x) || !std::isfinite((double)x))
            throw std::invalid_argument("native local output range exceeded");
        result.push_back((double)x);
    }
    return result;
}
struct Integral { real_t density=0,energy=0,derivative=0; };
// Normalized F_1/2, F_3/2 and dF_1/2/deta, independently of SciPy.
inline Integral integral(real_t eta) {
    const real_t upper=std::max(TCAD_CONST(64.0),eta+64);
    std::vector<real_t> breaks={0,upper,std::min(upper,std::max(TCAD_CONST(0.0),eta-16)),
        std::min(upper,std::max(TCAD_CONST(0.0),eta+16))};
    std::sort(breaks.begin(),breaks.end());breaks.erase(std::unique(breaks.begin(),breaks.end()),breaks.end());
    Integral r;
    for (size_t k=1;k<breaks.size();++k) {
        const real_t a=sqrt_q(breaks[k-1]),b=sqrt_q(breaks[k]);
        for (const auto& node:spectral_detail::quadrature()) {
            const real_t t=a+(b-a)*(node.first+1)/2,f=spectral_detail::occupation(eta-t*t);
            const real_t measure=(b-a)*node.second*t*t;
            r.density+=measure*f;r.energy+=measure*t*t*f;r.derivative+=measure*f*(1-f);
        }
    }
    const real_t gamma=sqrt_q(PI)/2;
    r.density/=gamma;r.derivative/=gamma;r.energy/=(TCAD_CONST(1.5)*gamma);
    return r;
}
} // namespace fermi_local_detail

// Repeated [density_m3, temperature_K, band_J] as decimal strings preserves
// the caller's longdouble density at the Cython boundary. Valleys use the
// spectral raw layout. Per-state output: mu, energy density, total n, n_v...
inline std::vector<double> native_fermi_reservoir_raw(const std::vector<std::string>& states,
                                                     const std::vector<double>& valleys) {
    using namespace fermi_local_detail;
    if (states.empty() || states.size()%3 || valleys.empty() || valleys.size()%4)
        throw std::invalid_argument("native FD reservoir dimensions invalid");
    const auto input=decimals(states);
    for (size_t v=0;v<valleys.size();v+=4) {
        for (size_t k=0;k<4;++k) if (!std::isfinite(valleys[v+k]))
            throw std::invalid_argument("nonfinite native valley");
        if (valleys[v]<=0 || valleys[v+1]<=0 || valleys[v+2]<=0)
            throw std::invalid_argument("positive valley masses and degeneracy required");
    }
    std::vector<real_t> result;
    const real_t m0=TCAD_CONST(9.1093837015e-31),h=TCAD_CONST(6.62607015e-34);
    for (size_t s=0;s<input.size();s+=3) {
        const real_t density=input[s],T=input[s+1],band=input[s+2];
        if (density<=0 || T<=0) throw std::invalid_argument("positive FD density and temperature required");
        const size_t nv=valleys.size()/4;
        std::vector<real_t> edges(nv),pref(nv),population(nv);
        real_t origin=band+valleys[3];
        for (size_t v=0;v<nv;++v) {
            edges[v]=band+valleys[4*v+3];origin=std::min(origin,edges[v]);
            pref[v]=2*valleys[4*v+2]*spectral_detail::three_halves(2*PI*valleys[4*v+1]*m0*KB*T/(h*h));
        }
        real_t log_pref_max=log_q(pref[0])-(edges[0]-origin)/(KB*T),pref_sum=0;
        for (size_t v=0;v<nv;++v) log_pref_max=std::max(log_pref_max,log_q(pref[v])-(edges[v]-origin)/(KB*T));
        for (size_t v=0;v<nv;++v) pref_sum+=exp_q(log_q(pref[v])-(edges[v]-origin)/(KB*T)-log_pref_max);
        const real_t eta_mb=log_q(density)-log_pref_max-log_q(pref_sum);
        real_t lo=eta_mb-2,hi=std::max(eta_mb+2,TCAD_CONST(2.0)),eta=eta_mb;
        real_t n=0,u=0,derivative=0;
        auto evaluate=[&](real_t e) {
            n=0;u=0;derivative=0;
            for (size_t v=0;v<nv;++v) {
                auto f=integral(e-(edges[v]-origin)/(KB*T));
                population[v]=pref[v]*f.density;n+=population[v];derivative+=pref[v]*f.derivative;
                u+=edges[v]*population[v]+TCAD_CONST(1.5)*KB*T*pref[v]*f.energy;
            }
            if (!isfinite_q(n) || !isfinite_q(u) || !isfinite_q(derivative))
                throw std::invalid_argument("native FD reservoir range exceeded");
        };
        for (int k=0;;++k) {
            evaluate(hi);
            if (n>=density) break;
            if (k==63) throw std::invalid_argument("native FD reservoir could not bracket density");
            hi*=2;
        }
        bool converged=false;
        for (int k=0;k<128;++k) {
            evaluate(eta);
            if (abs_q(n/density-1)<std::max(TCAD_CONST(1e-25),128*epsilon_q())) { converged=true;break; }
            if (n>density) hi=eta;else lo=eta;
            const real_t trial=derivative>0 ? eta-(n-density)/derivative : (lo+hi)/2;
            eta=(isfinite_q(trial) && trial>lo && trial<hi) ? trial : (lo+hi)/2;
        }
        if (!converged) throw std::invalid_argument("native FD density inversion did not converge");
        result.push_back(origin+KB*T*eta);result.push_back(u);result.push_back(n);
        result.insert(result.end(),population.begin(),population.end());
    }
    return exported(result);
}

// Cells (13 each): n0,p0,T0,n,p,T,u0,u,V,capacity,phi0,phi,kappa.
// Faces (12 each): owner,neighbor,Fn,Fp,energy,phi0,phi,area,do,dn,bathT,bathMode.
// dt is separate. All state differences, integrated work, Fourier flux and
// local conservation sums are evaluated in real_t before exporting float64.
// Output blocks: rn,rp,delta_u,delta_T,work,energy (nc each), heat_flux (nf).
inline std::vector<double> native_fermi_local_raw(const std::vector<std::string>& cells,
    const std::vector<std::string>& faces, double dt_s) {
    using namespace fermi_local_detail;
    if (cells.empty() || cells.size()%13 || faces.empty() || faces.size()%12 ||
        !std::isfinite(dt_s) || dt_s<=0)
        throw std::invalid_argument("native local dimensions or timestep invalid");
    const auto c=decimals(cells),f=decimals(faces);
    const size_t nc=c.size()/13,nf=f.size()/12;
    const real_t dt=dt_s;
    std::vector<real_t> r(6*nc+nf,0);
    for (size_t i=0;i<nc;++i) {
        const size_t b=13*i;
        for (size_t k:{0,1,2,3,4,5,8,9,12}) if (c[b+k]<=0)
            throw std::invalid_argument("positive native state, volume and thermal coefficients required");
        r[i]=c[b+8]*(c[b+3]-c[b]);r[nc+i]=c[b+8]*(c[b+4]-c[b+1]);
        r[2*nc+i]=c[b+8]*(c[b+7]-c[b+6]);
        r[3*nc+i]=c[b+8]*c[b+9]*(c[b+5]-c[b+2]);
        r[5*nc+i]=r[2*nc+i]+r[3*nc+i];
    }
    for (size_t k=0;k<nf;++k) {
        const size_t b=12*k;
        if (f[b]<0 || f[b]>=nc || f[b+1]<-1 || f[b+1]>=nc ||
            f[b]!=(real_t)(size_t)f[b] || (f[b+1]!=-1 && f[b+1]!=(real_t)(size_t)f[b+1]) ||
            f[b]==f[b+1] || f[b+7]<=0 || f[b+8]<=0 ||
            (f[b+1]>=0 ? f[b+9]<=0 : f[b+9]!=0) ||
            (f[b+11]!=0 && f[b+11]!=1) || (f[b+11]==1 && (f[b+1]>=0 || f[b+10]<=0)))
            throw std::invalid_argument("native local face geometry, index or bath invalid");
        const size_t i=(size_t)f[b];const long j=(long)f[b+1];
        real_t heat=0;
        if (j>=0) {
            const real_t ki=c[13*i+12],kj=c[13*j+12];
            heat=2*ki*kj/(ki+kj)*f[b+7]/(f[b+8]+f[b+9])*(c[13*i+5]-c[13*j+5]);
        } else if (f[b+11]==1) heat=c[13*i+12]*f[b+7]/f[b+8]*(c[13*i+5]-f[b+10]);
        r[6*nc+k]=heat;
        const real_t charge=si_transport::elementary_charge*(f[b+3]-f[b+2]),facephi=(f[b+5]+f[b+6])/2;
        auto deposit=[&](size_t node,real_t sign) {
            const real_t phi=(c[13*node+10]+c[13*node+11])/2;
            const real_t work=dt*sign*charge*(phi-facephi);
            r[node]+=dt*sign*f[b+2];r[nc+node]+=dt*sign*f[b+3];
            r[4*nc+node]+=work;r[5*nc+node]+=dt*sign*(f[b+4]+heat)-work;
        };
        deposit(i,1);if (j>=0) deposit((size_t)j,-1);
    }
    return exported(r);
}
} // namespace tcad
