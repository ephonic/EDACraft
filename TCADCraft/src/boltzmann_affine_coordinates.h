#pragma once
#include "boltzmann_particle_energy.h"

namespace tcad { namespace mb_affine_coordinate_detail {
// An affine anchor is a coordinate baseline, not a separate physical cell.
// Validate every stored component and structural scale here. Actual n and
// Tl/Tn/Tp must be checked on the complete affine point by the caller.
// The standalone particle-energy API retains its original temperature checks.
inline void validate_anchor(const std::vector<std::string>& frame,
    const std::vector<std::string>& en,const std::vector<std::string>& ep) {
    using mb_particle_detail::bounded;
    if(real_mantissa_bits()!=113 || frame.size()<10 || frame.size()>256 || en.empty() || ep.empty()
        || en.size()>4096 || ep.size()>4096)
        throw std::invalid_argument("MB affine coordinates require 113 bits and bounded expansion widths");
    const auto f=fermi_local_detail::decimals(frame);
    for(real_t x:f)bounded(x);
    for(const auto& raw:{en,ep})for(real_t x:fermi_local_detail::decimals(raw))bounded(x);
    for(size_t j:{0,1,3,4})if(f[j]<TCAD_CONST(1e-1000) || f[j]>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB affine positive coordinate scales outside supported range");
    for(size_t j:{5,6})if(abs_q(f[j])>TCAD_CONST(1e1000))
        throw std::invalid_argument("MB affine coordinate band energy range exceeded");
    if(!(f[2]>1 && f[2]<TCAD_CONST(1e5) && f[7]>1 && f[7]<f[8] && f[8]<TCAD_CONST(1e5)))
        throw std::invalid_argument("MB affine coordinate temperature domain invalid");
}
} } // namespace tcad::mb_affine_coordinate_detail
