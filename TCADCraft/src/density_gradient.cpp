#include "density_gradient.h"
#include <algorithm>
#include <cmath>

namespace tcad {

DensityGradient::DensityGradient(const Grid3D& grid) : g_(grid) {}

void DensityGradient::set_coefficients(real_t bn, real_t bp) {
    bn_ = bn;
    bp_ = bp;
}

void DensityGradient::set_thermal_voltage(real_t VT) {
    VT_ = VT;
}

void DensityGradient::laplace_sqrt_over_sqrt(const std::vector<real_t>& f,
                                             std::vector<real_t>& out) const {
    const size_t N = g_.npts();
    out.assign(N, 0.0Q);

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                real_t sqrt_f = sqrt_q(f[idx]);
                if (sqrt_f < EPSILON) {
                    out[idx] = 0.0Q;
                    continue;
                }

                real_t lap = 0.0Q;
                // Central difference Laplacian
                if (i > 0 && i + 1 < g_.nx) {
                    lap += (sqrt_q(f[idx + 1]) - 2.0Q * sqrt_f + sqrt_q(f[idx - 1])) / (g_.dx * g_.dx);
                }
                if (j > 0 && j + 1 < g_.ny) {
                    lap += (sqrt_q(f[idx + g_.nx]) - 2.0Q * sqrt_f + sqrt_q(f[idx - g_.nx])) / (g_.dy * g_.dy);
                }
                if (k > 0 && k + 1 < g_.nz) {
                    lap += (sqrt_q(f[idx + g_.nx * g_.ny]) - 2.0Q * sqrt_f + sqrt_q(f[idx - g_.nx * g_.ny])) / (g_.dz * g_.dz);
                }
                out[idx] = lap / sqrt_f;
            }
        }
    }
}

void DensityGradient::quantum_potential(const std::vector<real_t>& n,
                                        const std::vector<real_t>& p,
                                        std::vector<real_t>& Qn,
                                        std::vector<real_t>& Qp) const {
    laplace_sqrt_over_sqrt(n, Qn);
    laplace_sqrt_over_sqrt(p, Qp);
    for (size_t i = 0; i < g_.npts(); ++i) {
        Qn[i] = bn_ * Qn[i];
        Qp[i] = bp_ * Qp[i];
    }
}

void DensityGradient::correct(const std::vector<real_t>& n,
                              const std::vector<real_t>& p,
                              std::vector<real_t>& n_q,
                              std::vector<real_t>& p_q) const {
    std::vector<real_t> Qn, Qp;
    quantum_potential(n, p, Qn, Qp);
    const size_t N = g_.npts();
    n_q.resize(N);
    p_q.resize(N);
    for (size_t i = 0; i < N; ++i) {
        // Phase 3.6 sign fix (audit §16.3): the Ancona-Stafford DG quantum
        // potential is V_q = -(b/2)·∇²√n/√n, applied as n_q = n·exp(-V_q/VT),
        // i.e. n_q = n·exp(+(b/2)·∇²√n/√n/VT).  At a density peak ∇²√n<0,
        // so the exponent is negative and exp<1 -> DG DEPLETES the interface
        // peak (the physical quantum-confinement effect).
        //
        // Qn here is b·∇²√n/√n (without the 1/2 factor and without the
        // leading minus).  So the correct exponential is exp(+Qn/VT).
        // The previous code used exp(-Qn/VT), which amplified the peak —
        // the opposite of the intended physics.  Flipped here.
        real_t arg_n = Qn[i] / VT_;
        real_t arg_p = Qp[i] / VT_;
        // Phase 3.5 (audit §16): with the physical b_n (V·m²), the exponent
        // is O(1) and no clamp is needed for correctness.  We keep a wide
        // guard [-100, 100] purely to absorb transients from pathological
        // grids (NaN/Inf protection) during iteration; at steady state on a
        // sane grid the exponent never approaches this band.
        if (arg_n > 100.0Q) arg_n = 100.0Q;
        if (arg_n < -100.0Q) arg_n = -100.0Q;
        if (arg_p > 100.0Q) arg_p = 100.0Q;
        if (arg_p < -100.0Q) arg_p = -100.0Q;
        n_q[i] = n[i] * exp_q(arg_n);
        p_q[i] = p[i] * exp_q(arg_p);
    }
}

} // namespace tcad
