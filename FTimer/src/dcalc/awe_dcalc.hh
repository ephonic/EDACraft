#pragma once

#include <cmath>
#include <cstdint>
#include <vector>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "time_engine/wire_delay.hh"
#include "parasitics/timing_parasitics.hh"

namespace te {

// ────────────────────────────────────────────────────────────
// AWE (Asymptotic Waveform Evaluation) Delay Calculator
// ────────────────────────────────────────────────────────────
//
// Reduces full RC networks to Pi models via moment matching,
// then computes Elmore delays.
//
// Steps:
// 1. Build nodal conductance (G) and capacitance (C) matrices
// 2. Compute moments: m0 = G^{-1} * b, m1 = -G^{-1} * C * m0, ...
// 3. Arnoldi/Lanczos reduction to 2nd-order model
// 4. Fit Pi model parameters (C2, Rpi, C1) from moments

class AweDelayCalc {
public:
    AweDelayCalc() = default;

    // Reduce full RC network to Pi model using Arnoldi/AWE.
    // order = 2 gives Pi model, order = 3 gives 3-pole model.
    PiModel reduce_to_pi(
        const FullRcNetwork& rc,
        uint32_t driver_node_id,
        const std::vector<uint32_t>& sink_node_ids,
        int order = 2
    ) const;

    // Compute Elmore delay from driver to each sink.
    std::vector<float> elmore_delays(
        const FullRcNetwork& rc,
        uint32_t driver_node_id,
        const std::vector<uint32_t>& sink_node_ids
    ) const;

    // Compute Pi model from moments (m0, m1, m2).
    PiModel fit_pi_from_moments(double m0, double m1, double m2, float c_total) const;

    // Find Pi model for a driver pin from TimingParasiticDB.
    // If already reduced, return it. If full RC exists, reduce it.
    PiModel get_pi_model(
        PinId driver_pin,
        const TimingParasiticDB& db,
        const std::vector<PinId>& load_pins,
        int mm_rf
    ) const;

    // ── 2-pole delay/slew for net edges ──
    // Compute wire delay and slew degradation through a Pi model
    // driven by a ramp voltage source with series resistance Rd.
    //   pi          : reduced Pi model (c1,c2 in fF, rpi in ohms)
    //   input_slew  : driver transition time (ps)
    //   rd          : driver output resistance (ohms), estimated from NLDM
    // Returns delay to 50% and degraded slew 20%-80% at the load.
    PiResponse compute_pi_response(const PiModel& pi, float input_slew, float rd,
                                   float lower = 0.2f, float upper = 0.8f) const;
    PiResponse compute_pi_response(float c1, float rpi, float c2, float cap_scale,
                                   float input_slew, float rd) const;

    // Estimate driver resistance from NLDM output slew table.
    // Rd = slew(Cmax) / Cmax  (units: time/capacitance → ohms for fF/ps)
    static float estimate_rd(const edacraft::core::NldmTable& slew_table);

private:
    // Build G (conductance) and C (capacitance) matrices from RC network.
    void build_matrices(
        const FullRcNetwork& rc,
        std::vector<double>& G,
        std::vector<double>& C,
        std::vector<double>& b,
        std::vector<size_t>& node_index
    ) const;

    // LU factorization with partial pivoting (factorize once, solve many).
    // Stores L (unit lower triangular) and U (upper triangular) in A.
    // pivot[i] = row permutation for row i.
    bool factorize_lu(
        std::vector<double>& A,
        std::vector<size_t>& pivot,
        size_t n
    ) const;

    // Solve using pre-factored LU: L*U*x = Pb.
    void solve_lu(
        const std::vector<double>& LU,
        const std::vector<size_t>& pivot,
        std::vector<double>& x,
        const std::vector<double>& b,
        size_t n
    ) const;

    // Solve G * x = b (Gaussian elimination for small systems).
    void solve_linear(
        const std::vector<double>& G,
        std::vector<double>& x,
        const std::vector<double>& b,
        size_t n
    ) const;

    // Matrix-vector multiply: y = A * x.
    void matvec(
        const std::vector<double>& A,
        std::vector<double>& y,
        const std::vector<double>& x,
        size_t n
    ) const;

    // ── 2-pole ramp-response helpers ──
    // Solve ramp response y(t) = target using Newton-Raphson.
    // Returns t in ps.  If no convergence, falls back to D2M estimate.
    float solve_ramp_target(
        float p1, float p2, float k1, float k2,
        float tr, float target, float t_hint
    ) const;

    // Single-pole ramp response (limit of 2-pole when one pole → -∞).
    float solve_single_pole_target(
        float p, float tr, float target, float t_hint
    ) const;

    // Direct 2-moment (D2M) step-delay estimate for initial guess.
    static float d2m_delay(float b1, float b2);
    static float d2m_slew(float b1, float b2);
};

// ────────────────────────────────────────────────────────────
// Inline implementations
// ────────────────────────────────────────────────────────────
inline void AweDelayCalc::matvec(
    const std::vector<double>& A,
    std::vector<double>& y,
    const std::vector<double>& x,
    size_t n
) const {
    for (size_t i = 0; i < n; ++i) {
        double sum = 0.0;
        for (size_t j = 0; j < n; ++j) {
            sum += A[i * n + j] * x[j];
        }
        y[i] = sum;
    }
}

inline void AweDelayCalc::solve_linear(
    const std::vector<double>& G,
    std::vector<double>& x,
    const std::vector<double>& b,
    size_t n
) const {
    // Gaussian elimination with partial pivoting
    std::vector<double> A = G;
    x = b;

    for (size_t k = 0; k < n; ++k) {
        // Partial pivoting
        size_t pivot = k;
        for (size_t i = k + 1; i < n; ++i) {
            if (std::abs(A[i * n + k]) > std::abs(A[pivot * n + k])) {
                pivot = i;
            }
        }
        if (pivot != k) {
            for (size_t j = 0; j < n; ++j) {
                std::swap(A[k * n + j], A[pivot * n + j]);
            }
            std::swap(x[k], x[pivot]);
        }

        double diag = A[k * n + k];
        if (std::abs(diag) < 1e-15) {
            // Singular matrix: return zeros to avoid garbage results
            x.assign(n, 0.0);
            return;
        }

        for (size_t i = k + 1; i < n; ++i) {
            double factor = A[i * n + k] / diag;
            for (size_t j = k; j < n; ++j) {
                A[i * n + j] -= factor * A[k * n + j];
            }
            x[i] -= factor * x[k];
        }
    }

    // Back substitution
    for (int i = static_cast<int>(n) - 1; i >= 0; --i) {
        for (size_t j = i + 1; j < n; ++j) {
            x[i] -= A[i * n + j] * x[j];
        }
        if (std::abs(A[i * n + i]) > 1e-15) {
            x[i] /= A[i * n + i];
        }
    }
}

} // namespace te
