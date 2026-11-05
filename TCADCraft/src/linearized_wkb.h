#pragma once
#include "math_types.h"
#include "poisson_solver.h"
#include "structured_field.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace tcad {

// Existing x-directed, locally linearized finite-window barrier model.
// This is not an arbitrary band-profile nonlocal tunneling model.
struct LinearizedWKBParameters {
    real_t A, D, mass, path_fraction;
    size_t segments;
};
struct LinearizedWKBResult {
    real_t generation = TCAD_CONST(0.0);
    real_t d_generation_d_field = TCAD_CONST(0.0); // derivative w.r.t. |Ex|
};
// Bound a single source evaluation before entering any quadrature loop.
// The work bound counts all grid nodes conservatively, including skipped
// boundary/insulator nodes; it is not a time or device-memory guarantee.
inline size_t validated_linearized_wkb_segments(size_t segments) {
    if (segments < 2)
        throw std::invalid_argument("BTBT wkb_npts must be >= 2");
    constexpr size_t max_segments = size_t(1) << 20;
    if (segments > max_segments)
        throw std::invalid_argument("WKB segment count exceeds resource limit");
    return segments >= 4 && segments % 2 ? segments + 1 : segments;
}
inline void validate_linearized_wkb_work(size_t nodes, size_t segments) {
    const size_t rounded = validated_linearized_wkb_segments(segments);
    const size_t samples = rounded >= 4 ? rounded + 1 : 1;
    constexpr size_t max_samples = size_t(1) << 26;
    // Divide instead of multiplying untrusted dimensions/counts.
    if (nodes > max_samples / samples)
        throw std::invalid_argument("WKB grid quadrature exceeds resource limit");
}
// Preserve the historical double path when every multiplication is in its
// normal range. Otherwise combine the factors in log space before applying
// the positive source cap. In particular, a large prefactor times a small
// transmission/weight need not be a large source, and zero times an
// overflowing field power must still be exactly zero.
inline real_t wkb_generation_product(real_t A, double field, real_t power,
                              double exponent, real_t weight,
                              bool* positive_capped=nullptr) {
    if(positive_capped)*positive_capped=false;
    if (!isfinite_q(A) || !isfinite_q(power) || !isfinite_q(weight))
        throw std::invalid_argument("WKB source parameters must be finite");
    if (A == TCAD_CONST(0.0) || weight == TCAD_CONST(0.0))
        return TCAD_CONST(0.0);
    const double prefactor = (double)A * 1.0e6;
    const double field_power = std::pow(field, (double)power);
    const double unattenuated = prefactor * field_power;
    const double attenuated = unattenuated * std::exp(exponent);
    const double generation = attenuated * (double)weight;
    const real_t cap = (real_t)1e50;
    if (std::isnormal(prefactor) && std::isnormal(field_power) &&
        std::isnormal(unattenuated) && std::isnormal(attenuated) &&
        std::isnormal(generation)) {
        // A double result can round to the cap from either side. Recover
        // the product before selecting the active branch; equality of the
        // returned value with the cap is not a saturation flag.
        if(generation>0.0 && std::fabs(generation-1e50)<=1e50/256.0) {
            const real_t native_product=A*TCAD_CONST(1e6)*
                pow_q((real_t)field,power)*exp_q((real_t)exponent)*weight;
            if(native_product>=cap) {
                if(positive_capped)*positive_capped=true;
                return cap;
            }
            return native_product;
        }
        if(generation>1e50) {
            if(positive_capped)*positive_capped=true;
            return cap;
        }
        return (real_t)generation;
    }

    const bool positive = (A > TCAD_CONST(0.0)) == (weight > TCAD_CONST(0.0));
    const real_t magnitude_log = log_q(abs_q(A)) + log_q(TCAD_CONST(1e6)) +
        power * log_q((real_t)field) + (real_t)exponent + log_q(abs_q(weight));
    // Use the same cap representation as the double path, including rounding.
    if (positive && magnitude_log >= log_q(cap)) {
        if(positive_capped)*positive_capped=true;
        return cap;
    }
    const real_t magnitude = exp_q(magnitude_log);
    if (!isfinite_q(magnitude))
        throw std::overflow_error("signed WKB source exceeds native numeric range");
    return positive ? magnitude : -magnitude;
}


template<class Potential>
inline double linearized_wkb_x_field(const Grid3D& g, const Potential& phi, size_t idx) {
    const size_t i=idx%g.nx;
    if (!g.xx.empty())
        return (double)structured_node_field(phi,idx,i,1,g.nx,g.xx,g.dx);
    const double dx=(double)g.dx;
    if(i>0 && i+1<g.nx)return -((double)phi[idx+1]-(double)phi[idx-1])/(2.0*dx);
    if(i+1<g.nx)return -((double)phi[idx+1]-(double)phi[idx])/dx;
    if(i>0)return -((double)phi[idx]-(double)phi[idx-1])/dx;
    return 0.0;
}

template<class Potential>
inline LinearizedWKBResult evaluate_linearized_wkb(const Grid3D& g,
        const Potential& phi, size_t idx, real_t gap_eV,
        const LinearizedWKBParameters& p, real_t weight, bool derivatives=false) {
    LinearizedWKBResult result;
    const double hbar=1.054571817e-34, m0=9.1093837015e-31, qe=1.602176634e-19;
    const double mt_eff=(double)p.mass*m0;
    const size_t n_wkb=validated_linearized_wkb_segments(p.segments);
    const size_t i=idx%g.nx;
    const double E_field=std::fabs(linearized_wkb_x_field(g,phi,idx));
    const double Eg_J=(double)gap_eV*qe;
    if(E_field<=1.0)return result;
    const double d_min=Eg_J/(qe*E_field);
    const double dx_m=(double)g.dx;
    const double avail_lo=g.xx.empty()?(double)i*dx_m:(double)(g.xx[i]-g.xx.front());
    const double avail_hi=g.xx.empty()?(double)(g.nx-1-i)*dx_m:(double)(g.xx.back()-g.xx[i]);
    const double avail=std::min(avail_lo,avail_hi);
    double path_L=std::min(2.0*d_min,avail);
    bool field_limited=2.0*d_min<=avail;
    double geometric_cap=avail;
    const double fraction=(double)p.path_fraction;
    if(fraction>0.0) {
        const double domain_L=g.xx.empty()?(double)(g.nx-1)*dx_m:(double)(g.xx.back()-g.xx.front());
        const double fraction_cap=fraction*domain_L;
        geometric_cap=std::min(geometric_cap,fraction_cap);
        if(fraction_cap<path_L)field_limited=false;
        path_L=std::min(path_L,fraction_cap);
    }
    // Near the path switch, converting Eg to joules and dividing by qE
    // can move equality to either side by one double ulp. Compare the
    // equivalent voltage drops in native precision before selecting the
    // active derivative. This is cancellation recovery, not a tolerance
    // that snaps a small positive barrier to zero. At exact equality the
    // field-limited branch is the increasing-|E| branch.
    if(std::fabs(2.0*d_min-geometric_cap)<=std::fabs(geometric_cap)/256.0) {
        const real_t twice_gap=TCAD_CONST(2.0)*gap_eV;
        field_limited=twice_gap<=(real_t)E_field*(real_t)geometric_cap;
        path_L=field_limited?(double)(twice_gap/(real_t)E_field):geometric_cap;
    }
    const double effective_L=path_L;
    if(effective_L<1e-12)return result;
    double wkb_integral=0.0;
    real_t derivative_sum=TCAD_CONST(0.0);
    if(n_wkb>=4) {
        const double h=effective_L/(double)n_wkb;
        for(size_t s=0;s<=n_wkb;++s) {
            const double x=(double)s*h;
            // With L=2*Eg/(qE), the sample barrier is exactly
            // Eg*(n-2*s)/n. At s=n/2 it must be zero: subtracting
            // separately rounded energies can instead leave O(epsilon)*Eg,
            // whose square root adds O(sqrt(epsilon)) action noise. Form
            // the integer numerator first so this field-limited sample is
            // exact and the quadrature shape stays independent of E.
            double barrier=field_limited
                ? (s>=n_wkb/2 ? 0.0 : Eg_J*(double)(n_wkb-2*s)/(double)n_wkb)
                : std::max(Eg_J-qe*E_field*x,0.0);
            real_t resolved_barrier=(real_t)barrier;
            real_t sample_x=(real_t)x, sample_charge=(real_t)qe;
            // Recover cancelled bits only near a fixed-window turning sample.
            // This detects loss of >=8 bits; it does not snap small barriers
            // to zero. Resolve the intended rational Simpson node in native
            // precision, including its sign, before taking a square root.
            if(!field_limited && std::fabs(Eg_J-qe*E_field*x)<=std::fabs(Eg_J)/256.0) {
                sample_charge=TCAD_CONST(1.602176634e-19);
                sample_x=(real_t)effective_L*(real_t)s/(real_t)n_wkb;
                resolved_barrier=(gap_eV*(real_t)n_wkb-
                    (real_t)E_field*(real_t)effective_L*(real_t)s)/
                    (real_t)n_wkb*sample_charge;
                barrier=(double)std::max(resolved_barrier,TCAD_CONST(0.0));
            }
            if(barrier<=0.0)continue;
            const double integrand=std::sqrt(2.0*mt_eff*barrier)/hbar;
            if(std::isinf(integrand)){wkb_integral=1e10;break;}
            const double w=(s==0||s==n_wkb)?1.0:(s%2?4.0:2.0);
            wkb_integral+=w*integrand;
            // When L is proportional to 1/E, E*x_s is constant. Differentiate
            // only the quadrature measure, avoiding cancellation at a turning
            // point. With a fixed geometric cap, differentiate each barrier.
            if(derivatives && !field_limited)
                derivative_sum+=(real_t)(w*integrand)*TCAD_CONST(0.5)*
                    (-sample_charge*sample_x)/resolved_barrier;
        }
        wkb_integral*=h/3.0;
        derivative_sum*=(real_t)h/TCAD_CONST(3.0);
    } else {
        wkb_integral=std::sqrt(2.0*mt_eff*Eg_J)/hbar*effective_L;
    }
    const double exponent=-2.0*wkb_integral;
    if(exponent < -700.0)return result;
    bool positive_capped=false;
    result.generation=wkb_generation_product(p.A,E_field,p.D,exponent,weight,&positive_capped);
    if(!derivatives || result.generation==TCAD_CONST(0.0))return result;
    // The positive source cap is constant on its active branch. Threshold,
    // path-switch and quadrature turning-point corners use active branches.
    if(positive_capped)return result;
    const real_t d_action=field_limited?-(real_t)wkb_integral/(real_t)E_field:derivative_sum;
    result.d_generation_d_field=result.generation*(p.D/(real_t)E_field-TCAD_CONST(2.0)*d_action);
    return result;
}
} // namespace tcad
