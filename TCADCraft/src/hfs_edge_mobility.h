#include "hfs_reference.h"
#pragma once
#include "transport_contract.h"
#include <algorithm>

namespace tcad {
// Classical SG edge mobility and derivatives with respect to physical
// potential/density variables. The caller applies the log-density chain rule.
// This helper is used by the II source and its Jacobian; its value follows
// the existing continuity/current HFS law, including the small-ratio guard.
struct HfsEdgeMobility {
    real_t mobility = TCAD_CONST(0.0);
    real_t dphi_j = TCAD_CONST(0.0); // dmu/dphi_i = -dmu/dphi_j
    real_t dcarrier_i = TCAD_CONST(0.0);
    real_t dcarrier_j = TCAD_CONST(0.0);
};

inline HfsEdgeMobility classical_hfs_edge_mobility(
    real_t mu0, real_t phi_i, real_t phi_j, real_t carrier_i,
    real_t carrier_j, real_t dos_i, real_t dos_j, real_t VT,
    real_t spacing, real_t vsat, real_t beta, int driving,
    real_t cutoff, bool hole, real_t reference = TCAD_CONST(0.0)) {
    HfsEdgeMobility result{mu0};
    real_t difference = phi_j - phi_i;
    const real_t carrier_sign = hole ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
    if (driving == 0) {
        const real_t qi = phi_i + carrier_sign * VT *
            log_q(hfs_reference_carrier(carrier_i, reference) / std::max(dos_i, TCAD_CONST(1.0)));
        const real_t qj = phi_j + carrier_sign * VT *
            log_q(hfs_reference_carrier(carrier_j, reference) / std::max(dos_j, TCAD_CONST(1.0)));
        difference = qj - qi;
    }
    real_t force = hfs_active_driving_force(abs_q(difference) / spacing, cutoff);
    const real_t ratio = mu0 * force / vsat;
    if (ratio <= TCAD_CONST(1e-12)) return result;
    const real_t rb = pow_q(ratio, beta);
    result.mobility /= pow_q(TCAD_CONST(1.0) + rb, TCAD_CONST(1.0) / beta);
    const real_t dmu_dforce = -(mu0 * mu0 / vsat) * pow_q(ratio, beta - TCAD_CONST(1.0)) *
        pow_q(TCAD_CONST(1.0) + rb, -TCAD_CONST(1.0) / beta - TCAD_CONST(1.0));
    const real_t direction = difference > TCAD_CONST(0.0) ? TCAD_CONST(1.0) : -TCAD_CONST(1.0);
    result.dphi_j = dmu_dforce * direction / spacing;
    if (driving == 0) {
        // log(max(c,1)) is constant below its carrier clamp. No derivative
        // at c=1 or at the cutoff discontinuity is claimed.
        if (carrier_i+reference > TCAD_CONST(1.0))
            result.dcarrier_i = -result.dphi_j * carrier_sign * VT / (carrier_i+reference);
        if (carrier_j+reference > TCAD_CONST(1.0))
            result.dcarrier_j = result.dphi_j * carrier_sign * VT / (carrier_j+reference);
    }
    return result;
}
} // namespace tcad
