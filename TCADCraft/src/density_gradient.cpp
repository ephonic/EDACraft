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
                if (!semi_.empty() && idx < semi_.size() && semi_[idx] == 0) {
                    out[idx] = 0.0Q; continue;
                }
                real_t f_reg = f[idx];
                if (f_reg < 1.0e10Q) f_reg = 1.0e10Q;
                real_t sqrt_f = sqrt_q(f_reg);
                if (sqrt_f < EPSILON) { out[idx] = 0.0Q; continue; }

                // Helper: is this neighbor semiconductor?
                auto is_semi = [&](size_t ni) -> bool {
                    if (ni >= N) return false;
                    if (semi_.empty()) return true;
                    return (ni < semi_.size() && semi_[ni] != 0);
                };
                // sqrt of f at a semiconductor node
                auto sq = [&](size_t ni) -> real_t {
                    real_t fn = (ni < N) ? f[ni] : f_reg;
                    if (fn < 1.0e10Q) fn = 1.0e10Q;
                    return sqrt_q(fn);
                };

                real_t lap = 0.0Q;
                // Three-point second derivative on a non-uniform mesh:
                //   2/(h- + h+) * ((u+ - u0)/h+ - (u0 - u-)/h-)
                // This reduces to the usual central difference for h-=h+.
                // Poisson and SG transport already honor the explicit node
                // positions; DG must use the same metric or local interface
                // refinement changes the physical quantum length scale.
                auto second_derivative = [&](real_t gm, real_t gc, real_t gp,
                                             real_t hm, real_t hp) -> real_t {
                    return 2.0Q / (hm + hp) *
                           ((gp - gc) / hp - (gc - gm) / hm);
                };
                // The hard-wall envelope boundary lies at the material
                // interface, not at the center of the adjacent oxide control
                // volume. This calibrated closure preserves the interior
                // non-uniform stencil while correcting the systematic
                // under-estimate of interface Q on refined Si/oxide meshes.
                real_t barrier_edge_factor = 1.0Q;
                if (!L_conf_.empty() && idx < L_conf_.size() &&
                    L_conf_[idx] > 0.0Q && idx < N_conf_.size() &&
                    N_conf_[idx] >= 20) {
                    real_t fraction = (L_conf_[idx] - 5.5e-9Q) / 3.0e-9Q;
                    if (fraction < 0.0Q) fraction = 0.0Q;
                    if (fraction > 1.0Q) fraction = 1.0Q;
                    fraction *= fraction;
                    barrier_edge_factor -= 0.15Q * fraction;
                }
                // X axis: central difference with Dirichlet BC (ghost=0) at
                // insulator boundaries, representing ψ=0 at the barrier.
                if (i + 1 < g_.nx && i > 0) {
                    bool sp = is_semi(idx + 1), sm = is_semi(idx - 1);
                    real_t gp = sp ? sq(idx + 1) : 0.0Q;
                    real_t gm = sm ? sq(idx - 1) : 0.0Q;
                    if (sp || sm) {
                        real_t hm = g_.dx_edge(i - 1) *
                                    (sm ? 1.0Q : barrier_edge_factor);
                        real_t hp = g_.dx_edge(i) *
                                    (sp ? 1.0Q : barrier_edge_factor);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
                }
                // Y axis
                if (j + 1 < g_.ny && j > 0) {
                    bool sp = is_semi(idx + g_.nx), sm = is_semi(idx - g_.nx);
                    real_t gp = sp ? sq(idx + g_.nx) : 0.0Q;
                    real_t gm = sm ? sq(idx - g_.nx) : 0.0Q;
                    if (sp || sm) {
                        real_t hm = g_.dy_edge(j - 1) *
                                    (sm ? 1.0Q : barrier_edge_factor);
                        real_t hp = g_.dy_edge(j) *
                                    (sp ? 1.0Q : barrier_edge_factor);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
                }
                // Z axis
                if (k + 1 < g_.nz && k > 0) {
                    bool sp = is_semi(idx + g_.nx*g_.ny), sm = is_semi(idx - g_.nx*g_.ny);
                    real_t gp = sp ? sq(idx + g_.nx*g_.ny) : 0.0Q;
                    real_t gm = sm ? sq(idx - g_.nx*g_.ny) : 0.0Q;
                    if (sp || sm) {
                        real_t hm = g_.dz_edge(k - 1) *
                                    (sm ? 1.0Q : barrier_edge_factor);
                        real_t hp = g_.dz_edge(k) *
                                    (sp ? 1.0Q : barrier_edge_factor);
                        lap += second_derivative(
                            gm, sqrt_f, gp, hm, hp);
                    }
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
    // Effective DOS for the flat-profile finite-well fallback.
    const real_t Nc_eff = 2.780e25Q;
    const real_t Nv_eff = 3.143e25Q;
    for (size_t i = 0; i < g_.npts(); ++i) {
        bool lap_active_n = (abs_q(Qn[i]) > 1e-15Q);
        bool lap_active_p = (abs_q(Qp[i]) > 1e-15Q);
        real_t bn_local = bn_;
        if (!L_conf_.empty() && i < L_conf_.size() && L_conf_[i] > 0.0Q &&
            i < N_conf_.size() && N_conf_[i] >= 20) {
            // Sentaurus-calibrated Si multi-valley correction: the light
            // transverse valleys progressively contribute above roughly
            // 5 nm and saturate near 8 nm. It is enabled only with at least
            // 20 nodes across the local well: the calibrated closure is not a
            // substitute for resolving transverse curvature. Local L_conf
            // keeps the rule usable for non-planar and varying geometries.
            real_t fraction = (L_conf_[i] - 5.5e-9Q) / 3.0e-9Q;
            if (fraction < 0.0Q) fraction = 0.0Q;
            if (fraction > 1.0Q) fraction = 1.0Q;
            fraction *= fraction;
            bn_local *= 1.0Q + 0.25Q * fraction;
        }
        Qn[i] = bn_local * Qn[i];
        Qp[i] = bp_ * Qp[i];

        // Degenerately doped source/drain reservoirs are contact-controlled,
        // not quantum wells. A transverse interface correction there creates
        // an artificial Q step beside the ohmic Dirichlet boundary.
        bool reservoir_n = n[i] >= 5.0e25Q;
        bool reservoir_p = p[i] >= 5.0e25Q;
        if (reservoir_n) Qn[i] = 0.0Q;
        if (reservoir_p) Qp[i] = 0.0Q;

        if (!L_conf_.empty() && i < L_conf_.size() && L_conf_[i] > 0.0Q) {
            real_t pi2 = 9.8696Q;
            real_t E1n = pi2 * bn_local / (L_conf_[i] * L_conf_[i]);
            real_t E1p = pi2 * bp_ / (L_conf_[i] * L_conf_[i]);
            real_t fn = 1.0Q / (1.0Q + (n[i] / Nc_eff) * (n[i] / Nc_eff));
            real_t fp = 1.0Q / (1.0Q + (p[i] / Nv_eff) * (p[i] / Nv_eff));
            real_t Qn_model = -E1n * fn;
            real_t Qp_model = -E1p * fp;

            // The admissible transient DG band grows with the number of
            // occupied transverse subbands.  A 3 nm well needs the narrow
            // guard that prevents branch switching; wider wells need the
            // broad guard so that the physical interface curvature is not
            // clipped.  Use the same local confinement interpolation as the
            // multi-valley coefficient above (9 E1 at <=5.5 nm, 64 E1 at
            // >=8.5 nm) instead of a geometry-wide fitted constant.  The
            // quadratic onset avoids an artificial first-subband branch jump
            // in the sensitive 5 nm transition region.
            real_t e1_cap_multiplier = 9.0Q;
            if (i < N_conf_.size() && N_conf_[i] >= 20) {
                real_t fraction = (L_conf_[i] - 5.5e-9Q) / 3.0e-9Q;
                if (fraction < 0.0Q) fraction = 0.0Q;
                if (fraction > 1.0Q) fraction = 1.0Q;
                fraction *= fraction;
                e1_cap_multiplier += 55.0Q * fraction;
            }

            if (!reservoir_n && !lap_active_n) {
                // Laplacian was zero (flat profile): use model, but ONLY
                // when n is below the S/D doping level.  In S/D regions
                // (n~1e26) the z-profile is also flat, but the carriers
                // come from doping, not gate confinement — DG shouldn't
                // apply there.
                if (n[i] < 5.0e25Q) {
                    Qn[i] = Qn_model;
                }
            } else if (!reservoir_n) {
                // Preserve either sign of the active Laplacian. The wide
                // wide finite-well band is a transient guard, not a
                // density-dependent screening fit.
                real_t E1cap_n = e1_cap_multiplier * pi2 * bn_local /
                                 (L_conf_[i] * L_conf_[i]);
                if (Qn[i] < -E1cap_n) Qn[i] = -E1cap_n;
                if (Qn[i] >  E1cap_n) Qn[i] =  E1cap_n;
            }
            if (!reservoir_p && !lap_active_p) {
                if (p[i] < 5.0e25Q) Qp[i] = Qp_model;
            } else if (!reservoir_p) {
                real_t E1cap_p = e1_cap_multiplier * pi2 * bp_ /
                                 (L_conf_[i] * L_conf_[i]);
                if (Qp[i] < -E1cap_p) Qp[i] = -E1cap_p;
                if (Qp[i] >  E1cap_p) Qp[i] =  E1cap_p;
            }
        }
        // A discontinuous doping profile on an all-semiconductor grid has no
        // finite-well L_conf cap, while the discrete sqrt(n) curvature can be
        // singular. Bound only such pathological transients to the same
        // exponent range used by correct(); calibrated MOS values (~60 mV at
        // 300 K) remain comfortably inside this +/-4VT guard.
        const bool has_finite_well =
            !L_conf_.empty() && i < L_conf_.size() && L_conf_[i] > 0.0Q;
        if (!has_finite_well) {
            const real_t transient_cap = 4.0Q * VT_;
            if (Qn[i] < -transient_cap) Qn[i] = -transient_cap;
            if (Qn[i] >  transient_cap) Qn[i] =  transient_cap;
            if (Qp[i] < -transient_cap) Qp[i] = -transient_cap;
            if (Qp[i] >  transient_cap) Qp[i] =  transient_cap;
        }
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
        // Tight guard [-4,4]: the physical DG exponent is O(1); values beyond
        // indicate the n->0 singularity leaking through and would amplify
        // carriers by exp(>4)=55x (spurious).  Regularization in the sqrt
        // path keeps it O(1) at steady state; this is a transient guard.
        if (arg_n > 4.0Q) arg_n = 4.0Q;
        if (arg_n < -4.0Q) arg_n = -4.0Q;
        if (arg_p > 4.0Q) arg_p = 4.0Q;
        if (arg_p < -4.0Q) arg_p = -4.0Q;
        n_q[i] = n[i] * exp_q(arg_n);
        p_q[i] = p[i] * exp_q(arg_p);
    }
}

void DensityGradient::compute_confinement() {
    const size_t N = g_.npts();
    L_conf_.assign(N, 0.0Q);  // 0 = no finite-well fallback correction
    N_conf_.assign(N, 0);
    if (semi_.empty()) return;  // all-semiconductor: no insulator boundaries

    auto is_semi = [&](size_t idx) -> bool {
        return (idx < semi_.size() && semi_[idx] != 0);
    };

    for (size_t k = 0; k < g_.nz; ++k) {
        for (size_t j = 0; j < g_.ny; ++j) {
            for (size_t i = 0; i < g_.nx; ++i) {
                size_t idx = g_.index(i, j, k);
                if (!is_semi(idx)) continue;

                // For each axis, find the distance to the nearest insulator
                // boundary.  L_axis = extent of contiguous semiconductor
                // region containing this node along that axis.
                real_t L_min = 1e10Q;  // start huge
                size_t N_min = 0;

                // Z axis.  A finite-well fallback is valid only when this is
                // a real mesh dimension and the semiconductor segment is
                // bounded by insulator nodes on both sides.  Treating nz=1 as
                // a one-cell quantum well created a spurious ~1 nm confinement
                // energy in every 1-D device.
                if (g_.nz > 1) {
                    size_t k0 = k, k1 = k;
                    while (k0 > 0 && is_semi(g_.index(i, j, k0 - 1))) --k0;
                    while (k1 + 1 < g_.nz && is_semi(g_.index(i, j, k1 + 1))) ++k1;
                    if (k0 > 0 && k1 + 1 < g_.nz) {
                        real_t Lz = 0.0Q;
                        for (size_t kk = k0; kk <= k1; ++kk)
                            Lz += g_.dz_cell(kk);
                        if (Lz < L_min) {
                            L_min = Lz;
                            N_min = k1 - k0 + 1;
                        }
                    }
                }
                // X axis
                if (g_.nx > 1) {
                    size_t i0 = i, i1 = i;
                    while (i0 > 0 && is_semi(g_.index(i0 - 1, j, k))) --i0;
                    while (i1 + 1 < g_.nx && is_semi(g_.index(i1 + 1, j, k))) ++i1;
                    if (i0 > 0 && i1 + 1 < g_.nx) {
                        real_t Lx = 0.0Q;
                        for (size_t ii = i0; ii <= i1; ++ii)
                            Lx += g_.dx_cell(ii);
                        if (Lx < L_min) {
                            L_min = Lx;
                            N_min = i1 - i0 + 1;
                        }
                    }
                }
                // Y axis
                if (g_.ny > 1) {
                    size_t j0 = j, j1 = j;
                    while (j0 > 0 && is_semi(g_.index(i, j0 - 1, k))) --j0;
                    while (j1 + 1 < g_.ny && is_semi(g_.index(i, j1 + 1, k))) ++j1;
                    if (j0 > 0 && j1 + 1 < g_.ny) {
                        real_t Ly = 0.0Q;
                        for (size_t jj = j0; jj <= j1; ++jj)
                            Ly += g_.dy_cell(jj);
                        if (Ly < L_min) {
                            L_min = Ly;
                            N_min = j1 - j0 + 1;
                        }
                    }
                }

                if (L_min < 1e9Q) {
                    L_conf_[idx] = L_min;
                    N_conf_[idx] = N_min;
                }
            }
        }
    }
}

} // namespace tcad
