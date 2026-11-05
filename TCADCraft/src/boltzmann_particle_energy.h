#pragma once
#include "boltzmann_reference_rebase.h"

namespace tcad { namespace mb_particle_detail {
inline void bounded(real_t x) {
    if(!isfinite_q(x) || (x!=0 && (abs_q(x)<TCAD_CONST(1e-4000) || abs_q(x)>TCAD_CONST(1e4000))))
        throw std::invalid_argument("MB expansion arithmetic normal range exceeded");
}
inline std::vector<real_t> difference(real_t a,real_t b) {
    const real_t h=a-b,v=a-h,w=h+v,l=(a-w)+(v-b);
    bounded(h);bounded(l);return {h,l};
}
inline std::vector<real_t> product(real_t a,real_t b) {
    if(a==0 || b==0)return {};
    const real_t h=a*b;
    if(h==0)throw std::invalid_argument("MB expansion product underflow");
    bounded(h);
    const real_t l=boltzmann_rebase_detail::fused(a,b,-h);bounded(l);
    return {h,l};
}
inline std::vector<real_t> multiply(const std::vector<real_t>& a,real_t b) {
    std::vector<real_t> r;
    for(real_t x:a)for(real_t y:product(x,b))if(y!=0)r.push_back(y);
    return r;
}
inline std::vector<real_t> divide(const std::vector<real_t>& a,real_t b) {
    std::vector<real_t> r;
    for(real_t x:a)if(x!=0) {
        const real_t h=x/b;
        if(h==0)throw std::invalid_argument("MB expansion quotient underflow");
        bounded(h);
        const real_t residual=boltzmann_rebase_detail::fused(-h,b,x),l=residual/b;
        if(residual!=0 && l==0)throw std::invalid_argument("MB expansion quotient residual underflow");
        bounded(l);r.push_back(h);if(l!=0)r.push_back(l);
    }
    return r;
}
inline real_t view(const std::vector<real_t>& a) {
    // Grow an error-free expansion before rounding the view. In particular,
    // a density/band round trip can cancel finite terms around a tiny tail.
    std::vector<real_t> e;
    for(real_t x:a) {
        real_t q=x;std::vector<real_t> next;
        for(real_t y:e) {
            const real_t h=q+y,v=h-q,l=(q-(h-v))+(y-v);
            bounded(h);bounded(l);if(l!=0)next.push_back(l);q=h;
        }
        if(q!=0)next.push_back(q);e=std::move(next);
    }
    real_t r=0;for(real_t x:e)r+=x;
    bounded(r);return r;
}
inline void append(std::vector<real_t>& a,const std::vector<real_t>& b) {
    a.insert(a.end(),b.begin(),b.end());
    if(a.size()>4096)throw std::invalid_argument("MB carrier expansion component budget exceeded");
}
} // namespace mb_particle_detail

// Frame: n,p,Tref,Cv,V,En,Ep,Tmin,Tmax,lattice_base,L1,L2,...
// Each E includes the common offset of an equal-offset carrier valley set.
// Commands: new n,p,En,Ep,Qn,Qp. Q is TOTAL carrier energy delivered (J),
// including any prescribed band/particle work; it is never inferred here.
// Return: four frame replacements, two component counts, new n/p excess
// expansions, then old/new Tl,Tn,Tp views. No time advance or collision.
inline std::vector<std::string> native_boltzmann_particle_energy_raw(
    const std::vector<std::string>& frame,const std::vector<std::string>& dn,
    const std::vector<std::string>& dp,const std::vector<std::string>& commands) {
    using namespace mb_particle_detail;
    using boltzmann_detail::exported;
    if(real_mantissa_bits()!=113 || frame.size()<10 || frame.size()>256 || dn.empty() || dp.empty()
        || dn.size()>4096 || dp.size()>4096 || commands.size()!=6)
        throw std::invalid_argument("MB particle energy requires 113 bits and bounded expansion widths");
    const auto f=fermi_local_detail::decimals(frame),c=fermi_local_detail::decimals(commands);
    const std::vector<std::vector<real_t>> old={fermi_local_detail::decimals(dn),fermi_local_detail::decimals(dp)};
    for(real_t x:f)bounded(x);for(real_t x:c)bounded(x);for(const auto& a:old)for(real_t x:a)bounded(x);
    for(size_t j:{0,1,3,4})if(f[j]<TCAD_CONST(1e-1000) || f[j]>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB positive frame scales outside supported range");
    for(size_t j:{0,1})if(c[j]<TCAD_CONST(1e-1000) || c[j]>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB commanded densities outside supported range");
    for(real_t e:{f[5],f[6],c[2],c[3]})if(abs_q(e)>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB band energy range exceeded");
    if(!(f[2]>1 && f[2]<TCAD_CONST(1e5) && f[7]>1 && f[7]<f[8] && f[8]<TCAD_CONST(1e5)))
        throw std::invalid_argument("MB frame temperature domain invalid");
    const std::vector<real_t> lattice(f.begin()+9,f.end());
    const real_t Tl=f[2]+view(lattice)/f[3],alpha=TCAD_CONST(1.5)*KB;
    auto temperatures=[&](const std::vector<std::vector<real_t>>& d,real_t n,real_t p) {
        std::vector<real_t> t={Tl,Tl+view(d[0])/(alpha*n),Tl+view(d[1])/(alpha*p)};
        for(real_t x:t)if(!isfinite_q(x) || x<f[7] || x>f[8])
            throw std::invalid_argument("MB particle energy temperature view outside bounds");
        return t;
    };
    const auto oldviews=temperatures(old,f[0],f[1]);auto next=old;
    for(size_t k=0;k<2;++k) {
        // U = n*(E + alpha*Tl) + delta. Keep the existing delta
        // components byte-for-byte and append Q/V + old baseline - new.
        append(next[k],divide({c[4+k]},f[4]));
        const auto density=difference(f[k],c[k]);
        append(next[k],multiply(density,f[5+k]));
        append(next[k],multiply(difference(f[5+k],c[2+k]),c[k]));
        const auto heat=multiply(density,alpha);
        append(next[k],multiply(heat,f[2]));
        for(real_t ell:lattice)append(next[k],divide(multiply(heat,ell),f[3]));
    }
    const auto newviews=temperatures(next,c[0],c[1]);
    auto result=exported({c[0],c[1],c[2],c[3],real_t(next[0].size()),real_t(next[1].size())});
    // A native no-op must not alter the authoritative decimal frame merely
    // by reformatting a value originally serialized with fewer digits.
    for(size_t j=0;j<4;++j) {
        const size_t index=j<2?j:j+3;
        if(c[j]==f[index])result[j]=frame[index];
    }
    // Export only added components: old decimal strings remain authoritative.
    for(size_t k=0;k<2;++k) {
        const auto& raw=k==0?dn:dp;result.insert(result.end(),raw.begin(),raw.end());
        const auto added=exported(std::vector<real_t>(next[k].begin()+raw.size(),next[k].end()));
        result.insert(result.end(),added.begin(),added.end());
    }
    for(const auto& t:{oldviews,newviews}){const auto v=exported(t);result.insert(result.end(),v.begin(),v.end());}
    return result;
}
} // namespace tcad
