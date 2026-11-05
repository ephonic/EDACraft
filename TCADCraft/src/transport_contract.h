#pragma once
#include "math_types.h"
#include <stdexcept>

namespace tcad {
inline void validate_ii_coefficients(real_t An, real_t Bn, real_t Ap, real_t Bp) {
    if (!isfinite_q(An) || !isfinite_q(Bn) || !isfinite_q(Ap) || !isfinite_q(Bp) ||
        An < 0 || Bn < 0 || Ap < 0 || Bp < 0)
        throw std::invalid_argument("impact ionization coefficients must be finite and nonnegative");
}

inline void validate_ii_floor(real_t floor) {
    if (!isfinite_q(floor) || floor <= 0)
        throw std::invalid_argument("impact ionization E_floor must be finite and positive");
}

inline void validate_auger_coefficients(real_t Cn, real_t Cp) {
    if (!isfinite_q(Cn) || !isfinite_q(Cp) || Cn < 0 || Cp < 0)
        throw std::invalid_argument("Auger coefficients must be finite and nonnegative");
}

// Explicit numerical cutoff, shared by assembly and returned current.
// Equality remains active. The discontinuity itself has no Jacobian.
inline void validate_hfs_low_field_cutoff(real_t cutoff) {
    if (!isfinite_q(cutoff) || cutoff < TCAD_CONST(0.0))
        throw std::invalid_argument("HFS low-field cutoff must be finite and nonnegative [V/m]");
}
inline real_t hfs_active_driving_force(real_t force, real_t cutoff) {
    return force < cutoff ? TCAD_CONST(0.0) : force;
}

// Contact policy is carrier-specific: a potential boundary alone does not
// prescribe either carrier. Selecting ElectricField also removes GQF density
// derivatives on that edge. The default keeps the existing driving selector.
inline int hfs_edge_driving(int configured, bool quasi_fermi_at_contacts, bool carrier_contact) {
    return !quasi_fermi_at_contacts && carrier_contact ? 1 : configured;
}

inline void validate_hfs_parameters(real_t vn, real_t vp, real_t bn, real_t bp, int driving) {
    if (!isfinite_q(vn) || !isfinite_q(vp) || !isfinite_q(bn) || !isfinite_q(bp) ||
        vn <= 0 || vp <= 0 || bn <= 0 || bp <= 0)
        throw std::invalid_argument("high-field saturation parameters must be finite and > 0");
    if (driving != 0 && driving != 1)
        throw std::invalid_argument("high-field driving must be 0 (GradQuasiFermi) or 1 (ElectricField)");
}
} // namespace tcad
