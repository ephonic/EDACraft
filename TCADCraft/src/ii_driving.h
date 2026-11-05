#pragma once
#include "math_types.h"
#include <algorithm>
#include <stdexcept>
#include <vector>
namespace tcad {
inline void validate_ii_driving(int mode) {
    if(mode!=0 && mode!=1) throw std::invalid_argument("impact ionization driving must be 0 (ElectricField) or 1 (GradQuasiFermi)");
}
template<class Grid> inline void validate_ii_gqf_geometry(const Grid& g,bool unsupported) {
    if(int(g.nx>1)+int(g.ny>1)+int(g.nz>1)!=1 || unsupported)
        throw std::invalid_argument("II GradQuasiFermi requires one-dimensional classical isothermal Boltzmann transport without FE/DG and with constant mobility");
}
inline void validate_ii_gqf_material(size_t N,const std::vector<real_t>& nc,
        const std::vector<real_t>& nv,const std::vector<real_t>& eg,
        const std::vector<real_t>& mn,const std::vector<real_t>& mp) {
    for(const auto* a:{&nc,&nv,&eg,&mn,&mp}) {
        if(a->empty()) continue;
        if(a->size()!=N) throw std::invalid_argument("II GradQuasiFermi material size mismatch");
        for(real_t v:*a) if(!isfinite_q(v)||v!=(*a)[0]||(a==&eg?v<0:v<=0))
            throw std::invalid_argument("II GradQuasiFermi requires homogeneous finite bandgap/DOS and positive constant mobility");
    }
}
inline void validate_ii_reference_density(real_t n0,real_t p0) {
    if (!isfinite_q(n0)||!isfinite_q(p0)||n0<0||p0<0)
        throw std::invalid_argument("impact reference densities must be finite and nonnegative [m^-3]");
}
struct IIForce {real_t value,dphi,di,dj;};
inline IIForce ii_quasi_fermi_force(real_t dphi,real_t left,real_t right,
                                    real_t VT,real_t d,bool hole,real_t reference=TCAD_CONST(0.0)) {
    // Homogeneous MB material: F_n=|dphi-VT*dlog(n)|/d,
    // F_p=|dphi+VT*dlog(p)|/d. Uniform band/DOS offsets cancel.
    // W-2024.09 equations 387-388 and page 536: reference density enters
    // only the modified quasi-Fermi potential, not the SG carrier factors.
    // Preserve the exact legacy zero-reference arithmetic and log floor.
    const real_t floor=TCAD_CONST(1e-300);
    const real_t ml=reference>0?left+reference:left;
    const real_t mr=reference>0?right+reference:right;
    const real_t l=std::max(ml,floor),r=std::max(mr,floor);
    const real_t c=hole?VT:-VT;
    const real_t u=dphi+c*(log_q(r)-log_q(l));
    const real_t sign=u>0?TCAD_CONST(1.0):(u<0?-TCAD_CONST(1.0):TCAD_CONST(0.0));
    return {abs_q(u/d),sign/d,ml>floor?-sign*c/(d*ml):TCAD_CONST(0.0),mr>floor?sign*c/(d*mr):TCAD_CONST(0.0)};
}
}
