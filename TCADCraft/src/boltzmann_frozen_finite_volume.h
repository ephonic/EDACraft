#pragma once
#include "boltzmann_expanded_flat_face.h"

namespace tcad {
// Integrate a saved outward moment without rounding it to a scalar first.
inline std::vector<std::string> native_mb_fv_integrate_raw(
    const std::vector<std::string>& values,const std::string& dt) {
    using namespace mb_particle_detail;
    if(real_mantissa_bits()!=113 || values.size()>4096)
        throw std::invalid_argument("MB FV requires bounded 113-bit moments");
    const real_t t=fermi_local_detail::decimals({dt})[0];bounded(t);
    if(!(t>0))throw std::invalid_argument("MB FV positive time step required");
    const auto v=fermi_local_detail::decimals(values);std::vector<real_t> result;
    for(real_t x:v){bounded(x);append(result,multiply({x},t));}
    return boltzmann_detail::exported(result);
}

// Convert independently shared, signed particle/energy transfers to cell
// density increments. The frame and old excess remain the immutable anchor.
// Return four counted increment vectors, followed by Tl,Te,Th views.
inline std::vector<std::string> native_mb_fv_cell_raw(
    const std::vector<std::string>& frame,const std::vector<std::string>& en,
    const std::vector<std::string>& ep,const std::vector<std::string>& nn,
    const std::vector<std::string>& np,const std::vector<std::string>& un,
    const std::vector<std::string>& up) {
    using namespace mb_particle_detail;
    native_boltzmann_particle_energy_raw(frame,en,ep,{frame.at(0),frame.at(1),frame.at(5),frame.at(6),"0","0"});
    const auto f=fermi_local_detail::decimals(frame);
    std::vector<std::vector<real_t>> change;
    for(const auto& raw:{nn,np,un,up}) {
        if(raw.size()>4096)throw std::invalid_argument("MB FV transfer budget exceeded");
        const auto v=fermi_local_detail::decimals(raw);
        for(real_t x:v)bounded(x);
        const auto q=divide(v,f[4]);
        if(q.size()>4096)throw std::invalid_argument("MB FV density component budget exceeded");
        change.push_back(q);
    }
    const real_t alpha=TCAD_CONST(1.5)*KB;
    const std::vector<real_t> lattice(f.begin()+9,f.end());
    const real_t Tl=f[2]+view(lattice)/f[3];std::vector<real_t> temperatures={Tl};
    for(size_t k=0;k<2;++k) {
        auto density=change[k];density.insert(density.begin(),f[k]);const real_t n=view(density);
        if(n<TCAD_CONST(1e-1000) || n>TCAD_CONST(1e1000))
            throw std::invalid_argument("MB FV updated density outside positive range");
        auto excess=fermi_local_detail::decimals(k==0?en:ep);
        excess.insert(excess.end(),change[2+k].begin(),change[2+k].end());
        for(real_t x:change[k]) {
            const auto band=multiply({-x},f[5+k]);excess.insert(excess.end(),band.begin(),band.end());
            auto heat=multiply({-x},alpha);const auto base=multiply(heat,f[2]);
            excess.insert(excess.end(),base.begin(),base.end());
            for(real_t ell:lattice) {
                const auto add=divide(multiply(heat,ell),f[3]);excess.insert(excess.end(),add.begin(),add.end());
            }
        }
        if(excess.size()>65536)throw std::invalid_argument("MB FV temperature work budget exceeded");
        const real_t t=Tl+view(excess)/(alpha*n);
        if(!isfinite_q(t) || t<f[7] || t>f[8])throw std::invalid_argument("MB FV updated temperature outside bounds");
        temperatures.push_back(t);
    }
    std::vector<std::string> result;
    for(const auto& v:change) {
        const auto count=boltzmann_detail::exported({real_t(v.size())});result.push_back(count[0]);
        const auto raw=boltzmann_detail::exported(v);result.insert(result.end(),raw.begin(),raw.end());
    }
    const auto raw=boltzmann_detail::exported(temperatures);result.insert(result.end(),raw.begin(),raw.end());
    return result;
}
} // namespace tcad
