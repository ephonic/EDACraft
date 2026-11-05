#pragma once
#include "math_types.h"
#include <algorithm>
#include <stdexcept>
#include <vector>
namespace tcad {
inline void validate_hfs_reference_density(real_t n0,real_t p0) {
    if (!isfinite_q(n0)||!isfinite_q(p0)||n0<0||p0<0)
        throw std::invalid_argument("HFS reference densities must be finite and nonnegative [m^-3]");
}
inline bool active_hfs_reference(bool enabled,int driving,real_t n0,real_t p0) {
    return enabled && driving==0 && (n0>0 || p0>0);
}
template<class Grid> inline void validate_hfs_reference_geometry(const Grid& g,bool unsupported) {
    if (int(g.nx>1)+int(g.ny>1)+int(g.nz>1)!=1 || unsupported)
        throw std::invalid_argument("nonzero HFS RefDens requires one-dimensional classical isothermal MB without FE/DG and with constant mobility");
}
inline void validate_hfs_reference_material(size_t N,const std::vector<real_t>& nc,
        const std::vector<real_t>& nv,const std::vector<real_t>& eg,
        const std::vector<real_t>& mn,const std::vector<real_t>& mp) {
    for (const auto* a : {&nc,&nv,&eg,&mn,&mp}) {
        if (a->empty()) continue; // direct solver's homogeneous defaults
        if (a->size()!=N) throw std::invalid_argument("HFS RefDens material size mismatch");
        for (real_t v:*a) if (!isfinite_q(v)||v!=(*a)[0]||(a==&eg?v<0:v<=0))
            throw std::invalid_argument("nonzero HFS RefDens requires homogeneous finite bandgap/DOS and positive constant mobility");
    }
}
// W-2024.09 equations 387-388: only the HFS quasi-Fermi potential uses
// n+n0 / p+p0. The existing carrier floor protects the logarithm; it is
// applied to the modified density. SG factors keep the actual densities.
inline real_t hfs_reference_carrier(real_t carrier,real_t reference) {
    return std::max(carrier+reference,TCAD_CONST(1.0));
}

inline real_t hfs_reference_chain(real_t correction,real_t carrier,real_t reference,bool logarithmic) {
    if (reference==TCAD_CONST(0.0))
        return logarithmic ? correction : (carrier>TCAD_CONST(1.0) ? correction/carrier : TCAD_CONST(0.0));
    if (carrier+reference<=TCAD_CONST(1.0)) return TCAD_CONST(0.0);
    return logarithmic ? correction*(carrier/(carrier+reference)) : correction/(carrier+reference);
}
} // namespace tcad
