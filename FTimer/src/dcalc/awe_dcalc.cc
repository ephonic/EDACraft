#include "awe_dcalc.hh"
#include "parasitics/elmore_calc.hh"

#include <algorithm>
#include <cmath>
#include <unordered_map>

namespace te {

namespace ec = edacraft::core;

// ────────────────────────────────────────────────────────────
// Build G and C matrices from RC network
// ────────────────────────────────────────────────────────────
void AweDelayCalc::build_matrices(
    const FullRcNetwork& rc,
    std::vector<double>& G,
    std::vector<double>& C,
    std::vector<double>& b,
    std::vector<size_t>& node_index
) const {
    // Map RC node IDs to matrix indices
    std::unordered_map<uint32_t, size_t> id_to_idx;
    size_t n = rc.nodes.size();
    node_index.clear();
    for (size_t i = 0; i < n; ++i) {
        id_to_idx[rc.nodes[i].id] = i;
        node_index.push_back(i);
    }

    G.assign(n * n, 0.0);
    C.assign(n * n, 0.0);
    b.assign(n, 0.0);

    // Conductance matrix from resistors
    for (const auto& res : rc.resistors) {
        auto it1 = id_to_idx.find(res.node1);
        auto it2 = id_to_idx.find(res.node2);
        if (it1 == id_to_idx.end() || it2 == id_to_idx.end()) continue;

        double g = 1.0 / res.resistance;
        G[it1->second * n + it1->second] += g;
        G[it2->second * n + it2->second] += g;
        G[it1->second * n + it2->second] -= g;
        G[it2->second * n + it1->second] -= g;
    }

    // Capacitance matrix from capacitors
    for (const auto& cap : rc.capacitors) {
        auto it1 = id_to_idx.find(cap.node1);
        if (it1 == id_to_idx.end()) continue;

        if (cap.node2 == UINT32_MAX) {
            // Ground capacitor
            C[it1->second * n + it1->second] += cap.capacitance;
        } else {
            // Coupling capacitor
            auto it2 = id_to_idx.find(cap.node2);
            if (it2 == id_to_idx.end()) continue;
            C[it1->second * n + it1->second] += cap.capacitance;
            C[it2->second * n + it2->second] += cap.capacitance;
            C[it1->second * n + it2->second] -= cap.capacitance;
            C[it2->second * n + it1->second] -= cap.capacitance;
        }
    }

    // Add pin capacitance to nodes
    for (const auto& node : rc.nodes) {
        if (valid(node.pin)) {
            // Node's gnd_cap already includes pin capacitance from SPEF
            auto it = id_to_idx.find(node.id);
            if (it != id_to_idx.end()) {
                C[it->second * n + it->second] += node.gnd_cap;
            }
        }
    }

    // Add tiny ground conductance to every node to prevent singular Laplacian.
    // This is a standard regularization trick for AWE moment matching.
    for (size_t i = 0; i < n; ++i) {
        G[i * n + i] += 1e-12;
    }

    // Input vector b: 1 at driver node, 0 elsewhere
    for (const auto& node : rc.nodes) {
        if (node.id == rc.driver_node_id) {
            auto it = id_to_idx.find(node.id);
            if (it != id_to_idx.end()) b[it->second] = 1.0;
        }
    }
}

// ────────────────────────────────────────────────────────────
// LU factorization with partial pivoting
// ────────────────────────────────────────────────────────────
bool AweDelayCalc::factorize_lu(
    std::vector<double>& A,
    std::vector<size_t>& pivot,
    size_t n
) const {
    pivot.resize(n);
    for (size_t i = 0; i < n; ++i) pivot[i] = i;

    for (size_t k = 0; k < n; ++k) {
        size_t pivot_row = k;
        double max_val = std::abs(A[k * n + k]);
        for (size_t i = k + 1; i < n; ++i) {
            double val = std::abs(A[i * n + k]);
            if (val > max_val) {
                max_val = val;
                pivot_row = i;
            }
        }
        if (max_val < 1e-18) return false;

        if (pivot_row != k) {
            for (size_t j = 0; j < n; ++j) {
                std::swap(A[k * n + j], A[pivot_row * n + j]);
            }
            std::swap(pivot[k], pivot[pivot_row]);
        }

        for (size_t i = k + 1; i < n; ++i) {
            A[i * n + k] /= A[k * n + k];
            for (size_t j = k + 1; j < n; ++j) {
                A[i * n + j] -= A[i * n + k] * A[k * n + j];
            }
        }
    }
    return true;
}

// ────────────────────────────────────────────────────────────
// Solve using pre-factored LU
// ────────────────────────────────────────────────────────────
void AweDelayCalc::solve_lu(
    const std::vector<double>& LU,
    const std::vector<size_t>& pivot,
    std::vector<double>& x,
    const std::vector<double>& b,
    size_t n
) const {
    x.resize(n);
    for (size_t i = 0; i < n; ++i) {
        x[i] = b[pivot[i]];
        for (size_t j = 0; j < i; ++j) {
            x[i] -= LU[i * n + j] * x[j];
        }
    }
    for (int i = static_cast<int>(n) - 1; i >= 0; --i) {
        for (size_t j = i + 1; j < n; ++j) {
            x[i] -= LU[i * n + j] * x[j];
        }
        x[i] /= LU[i * n + i];
    }
}

// ────────────────────────────────────────────────────────────
// Elmore delay computation (simplest AWE approximation)
// ────────────────────────────────────────────────────────────
// Elmore delay = R_pi * C_total (first moment of impulse response)
// For a tree: delay to sink = sum of R * C_downstream along path
std::vector<float> AweDelayCalc::elmore_delays(
    const FullRcNetwork& rc,
    uint32_t driver_node_id,
    const std::vector<uint32_t>& sink_node_ids
) const {
    std::vector<float> delays;
    delays.reserve(sink_node_ids.size());

    // Build adjacency list for the RC tree
    size_t n = rc.nodes.size();
    std::unordered_map<uint32_t, size_t> id_to_idx;
    for (size_t i = 0; i < n; ++i) {
        id_to_idx[rc.nodes[i].id] = i;
    }

    // For each sink, compute Elmore delay via DFS from driver
    // Elmore = sum(R_i * C_downstream_i) along path
    auto drv_it = id_to_idx.find(driver_node_id);
    if (drv_it == id_to_idx.end()) {
        for (size_t i = 0; i < sink_node_ids.size(); ++i) delays.push_back(0.0f);
        return delays;
    }

    // Simple approach: use moment matching
    std::vector<double> G, C_mat, b, x;
    std::vector<size_t> node_index;
    build_matrices(rc, G, C_mat, b, node_index);

    // Solve G * m0 = b  → m0 is DC response
    std::vector<double> m0;
    solve_linear(G, m0, b, n);

    // Compute m1 = -G^{-1} * C * m0
    std::vector<double> Cm0(n);
    matvec(C_mat, Cm0, m0, n);

    std::vector<double> m1;
    std::vector<double> neg_Cm0(n);
    for (size_t i = 0; i < n; ++i) neg_Cm0[i] = -Cm0[i];
    solve_linear(G, m1, neg_Cm0, n);

    // Elmore delay to each sink = -m1[sink_idx] / m0[sink_idx]
    for (auto sink_id : sink_node_ids) {
        auto sit = id_to_idx.find(sink_id);
        if (sit != id_to_idx.end() && std::abs(m0[sit->second]) > 1e-15) {
            delays.push_back(static_cast<float>(-m1[sit->second] / m0[sit->second]));
        } else {
            delays.push_back(0.0f);
        }
    }

    return delays;
}

// ────────────────────────────────────────────────────────────
// Pi model fitting from moments
// ────────────────────────────────────────────────────────────
// Given moments m0, m1, m2:
//   C_total = m0 (total downstream capacitance)
//   Rpi = m1 / m0 (effective resistance)
//   C1 = m0^2 / (m1^2 / m0 + m2) ... simplified Pi fitting
PiModel AweDelayCalc::fit_pi_from_moments(
    double m0, double m1, double m2, float c_total
) const {
    PiModel pi;
    pi.cap_scale = 1e-15f; // assume fF by default

    // Total capacitance from the caller-provided sum (m0 is regularized DC voltage, not capacitance)
    double c_tot = c_total;

    // Elmore delay (first moment normalized)
    double elmore = std::abs(m0) > 1e-15 ? m1 / m0 : 0.0;

    // Second moment for Pi fitting
    double sigma = 0.0;
    if (std::abs(m1) > 1e-15) {
        sigma = std::sqrt(std::abs(m2 / m1));
    }

    // Pi model parameters (2-pole AWE fit)
    // C2 = c_tot * (elmore^2) / (elmore^2 + sigma^2)
    // Rpi = elmore^2 / (elmore^2 + sigma^2) / (c_tot - C2)
    // C1 = c_tot - C2
    double elmore_sq = elmore * elmore;
    double sigma_sq = sigma * sigma;
    double denom = elmore_sq + sigma_sq;

    if (denom > 1e-30) {
        pi.c2 = static_cast<float>(c_tot * elmore_sq / denom);
        pi.c1 = static_cast<float>(c_tot - pi.c2);
        if (std::abs(pi.c1) > 1e-15) {
            pi.rpi = static_cast<float>(elmore_sq / (denom * pi.c1));
        } else {
            pi.rpi = static_cast<float>(elmore);
        }
    } else {
        // Degenerate case: use lumped capacitance
        pi.c2 = static_cast<float>(c_tot);
        pi.rpi = 0.0f;
        pi.c1 = 0.0f;
    }

    // Ensure non-negative values
    if (pi.c1 < 0) pi.c1 = 0;
    if (pi.c2 < 0) pi.c2 = 0;
    if (pi.rpi < 0) pi.rpi = 0;

    return pi;
}

// ────────────────────────────────────────────────────────────
// AWE reduction to Pi model
// ────────────────────────────────────────────────────────────
// Fallback: use direct Elmore delays to fit a simple Pi model.
// The AWE moment matching with regularisation is numerically unstable
// for floating RC trees, so we compute the total capacitance and
// the maximum Elmore delay directly and fit a 2-pole Pi model.
// ────────────────────────────────────────────────────────────
PiModel AweDelayCalc::reduce_to_pi(
    const FullRcNetwork& rc,
    uint32_t driver_node_id,
    const std::vector<uint32_t>& sink_node_ids,
    int order
) const {
    (void)order;
    (void)sink_node_ids;

    // Compute Elmore delays and driving-point admittance moments via
    // tree-based O(n) traversal (numerically stable, no dense LU needed).
    auto elmore = compute_elmore_delays(rc);
    float total_c = elmore.total_load_cap;  // in native SPEF cap units (fF)
    float max_delay = 0.0f;
    for (const auto& pd : elmore.pin_delay) {
        max_delay = std::max(max_delay, pd.second);
    }

    PiModel pi;
    pi.cap_scale = rc.cap_scale;
    if (total_c <= 0.0f) {
        pi.c1 = pi.c2 = pi.rpi = 0.0f;
        return pi;
    }

    // For nets with very small parasitics, use lumped capacitance.
    if (max_delay < 1e-6f) {
        pi.c1 = 0.0f;
        pi.c2 = total_c;
        pi.rpi = 0.0f;
        return pi;
    }

    // Proper AWE moment matching from tree-based second moments.
    // Driving-point admittance 2nd moment: y2 = -Σ R_edge·C_subtree².
    // For a Pi model: y2 = -Rpi·C1².
    // Effective resistance: R_eff = y2 / C_total² = Rpi·(C1/C_total)².
    // Max Elmore delay (to dominant sink): delay = Rpi·C1.
    // Solving: C1 = R_eff·C_total² / delay_native, Rpi = delay_native / C1.
    float rc_to_ps = elmore.rc_to_ps;
    float delay_native = max_delay / rc_to_ps; // raw units
    float sum_r_c2 = elmore.sum_r_c2;          // raw units
    float r_eff_native = sum_r_c2 / (total_c * total_c); // ohms (res_scale units)

    if (r_eff_native > 1e-12f && delay_native > 1e-12f) {
        float c1 = r_eff_native * total_c * total_c / delay_native;
        float rpi = delay_native / c1;  // in kohm for both fF/pF raw units
        float c2 = total_c - c1;

        // Sanity checks — fall back to symmetric Pi if moments give nonsense.
        if (c1 > 0.0f && c2 >= 0.0f && rpi > 0.0f &&
            c1 <= total_c * 1.5f && c2 <= total_c * 1.5f) {
            pi.c1 = c1;
            pi.c2 = std::max(0.0f, c2);
            pi.rpi = rpi * rc.res_scale; // native resistance to ohms
            return pi;
        }
    }

    // Fallback: symmetric Pi model.
    // Ensure rpi gives b1 = rpi * c1 * cap_to_ps = max_delay.
    float cap_to_ps = rc.cap_scale / 1e-12f;
    pi.c1 = total_c * 0.5f;
    pi.c2 = total_c * 0.5f;
    pi.rpi = max_delay / (pi.c1 * cap_to_ps);
    return pi;
}

// ────────────────────────────────────────────────────────────
// Get Pi model from database (with on-demand reduction)
// ────────────────────────────────────────────────────────────
PiModel AweDelayCalc::get_pi_model(
    PinId driver_pin,
    const TimingParasiticDB& db,
    const std::vector<PinId>& load_pins,
    int mm_rf
) const {
    // Check if already reduced
    if (auto pi = db.get_reduced(driver_pin, mm_rf)) {
        return *pi;
    }

    // Check for lumped capacitance
    if (auto lc = db.get_lumped(driver_pin)) {
        PiModel pi;
        pi.c1 = 0;
        pi.rpi = 0;
        pi.c2 = lc->capacitance;
        pi.cap_scale = 1e-15f; // assume fF
        return pi;
    }

    // Default: zero delay (no parasitics loaded)
    PiModel pi;
    pi.c1 = 0; pi.rpi = 0; pi.c2 = 0;
    pi.cap_scale = 1e-15f;
    return pi;
}

// ────────────────────────────────────────────────────────────
// 2-pole delay / slew solver for Pi model + ramp source
// ────────────────────────────────────────────────────────────

float AweDelayCalc::estimate_rd(const ec::NldmTable& slew_table) {
    if (slew_table.rows == 0 || slew_table.axis2.empty() ||
        slew_table.values.size() < slew_table.axis2.size()) {
        return 0.0f;
    }

    size_t n2 = slew_table.axis2.size();

    // Use minimum input transition to avoid input-slew contamination.
    size_t i = 0;  // min input transition

    if (n2 >= 2) {
        // Incremental resistance: Δslew / Δcap
        size_t j1 = 0;
        size_t j2 = n2 - 1;
        float slew1 = slew_table.values[i * n2 + j1];
        float slew2 = slew_table.values[i * n2 + j2];
        float cap1  = slew_table.axis2[j1];
        float cap2  = slew_table.axis2[j2];
        float dc    = cap2 - cap1;
        if (dc > 1e-15f && slew2 > slew1) {
            // Values are in lib time units (ns), caps in lib cap units (pF).
            // Rd = Δslew_ns / Δcap_pF * 1000  → ohms
            return (slew2 - slew1) / dc * 1000.0f;
        }
    }

    // Fallback: single-point estimate
    size_t j = n2 - 1;
    float slew = slew_table.values[i * n2 + j];
    float cap  = slew_table.axis2[j];
    if (cap > 1e-15f) {
        return slew / cap * 1000.0f;
    }
    return 0.0f;
}

// D2M (direct 2-moment) step-delay estimate.
// b1 = first moment (ps), b2 = second moment (ps²).
float AweDelayCalc::d2m_delay(float b1, float b2) {
    if (b1 <= 0.0f) return 0.0f;
    // For a single pole: t50 = b1 * ln(2).
    // For two poles, a slightly better estimate:
    // t50 ≈ b1 * ln(2) - 0.1 * b2 / b1
    float t = b1 * 0.693147f;
    if (b2 > 0.0f) {
        t -= 0.1f * b2 / b1;
        if (t < 0.0f) t = b1 * 0.5f;
    }
    return t;
}

float AweDelayCalc::d2m_slew(float b1, float b2) {
    if (b1 <= 0.0f) return 0.0f;
    // Step 20%-80% slew for single pole: 2.2 * τ where τ = b1.
    // For two poles, use a conservative estimate.
    float tau = b1;
    if (b2 > 0.0f) {
        // Reduce τ estimate when second moment is significant
        tau = b1 - 0.3f * b2 / b1;
        if (tau < 0.1f * b1) tau = 0.1f * b1;
    }
    return tau * 2.197f; // ln(5) ≈ 1.609 for 20→80, but 2.2 is the traditional factor
}

// Single-pole ramp-response solver (limit of 2-pole when Rd→0 or Rpi→0).
float AweDelayCalc::solve_single_pole_target(
    float p, float tr, float target, float t_hint
) const {
    if (tr <= 1e-6f || target <= 1e-6f || target >= 1.0f - 1e-6f) {
        // Step response
        if (target <= 1e-6f) return 0.0f;
        if (target >= 1.0f - 1e-6f) return 1e6f;
        float t = std::log(1.0f - target) / p;
        if (t < 0.0f) t = 0.0f;
        return t;
    }

    auto eval = [&](float t, float& y, float& dy) {
        float pt = p * t;
        float ept = std::exp(pt);
        if (t <= tr) {
            // y = (t - (exp(p*t)-1)/p) / tr
            y = (t - (ept - 1.0f) / p) / tr;
            dy = (1.0f - ept) / tr;
        } else {
            // y = 1 - (1-exp(-p*tr)) * exp(p*t) / (tr*p)
            float emtr = std::exp(-p * tr);
            float A = (1.0f - emtr) / (tr * p);
            y = 1.0f - A * ept;
            dy = -A * p * ept;
        }
    };

    float t = t_hint;
    if (t <= 0.0f) t = tr * target;

    for (int iter = 0; iter < 20; ++iter) {
        float y, dy;
        eval(t, y, dy);
        float f = y - target;
        if (std::abs(f) < 1e-6f) return t;
        if (std::abs(dy) < 1e-15f) break;
        float dt = -f / dy;
        // Damped Newton
        float alpha = 1.0f;
        for (int ls = 0; ls < 10; ++ls) {
            float t_new = t + alpha * dt;
            if (t_new < 0.0f) t_new = 0.0f;
            float y_new, dy_new;
            eval(t_new, y_new, dy_new);
            if (std::abs(y_new - target) < std::abs(f)) {
                t = t_new;
                break;
            }
            alpha *= 0.5f;
            if (alpha < 1e-4f) {
                t = t_new;
                break;
            }
        }
    }
    return t;
}

// Full 2-pole ramp-response solver.
float AweDelayCalc::solve_ramp_target(
    float p1, float p2, float k1, float k2,
    float tr, float target, float t_hint
) const {
    if (tr <= 1e-6f || target <= 1e-6f || target >= 1.0f - 1e-6f) {
        // Step response: 0.5 = k1*exp(p1*t) + k2*exp(p2*t)
        if (target <= 1e-6f) return 0.0f;
        if (target >= 1.0f - 1e-6f) return 1e6f;
        float t = t_hint;
        if (t <= 0.0f) t = 1.0f;
        for (int iter = 0; iter < 20; ++iter) {
            float e1 = std::exp(p1 * t);
            float e2 = std::exp(p2 * t);
            float f = k1 * e1 + k2 * e2 - target;
            float fp = k1 * p1 * e1 + k2 * p2 * e2;
            if (std::abs(f) < 1e-6f) return t;
            if (std::abs(fp) < 1e-15f) break;
            t -= f / fp;
            if (t < 0.0f) t = 0.0f;
        }
        return t;
    }

    auto eval = [&](float t, float& y, float& dy) {
        float e1 = std::exp(p1 * t);
        float e2 = std::exp(p2 * t);
        if (t <= tr) {
            // y = (t - k1*(exp(p1*t)-1)/p1 - k2*(exp(p2*t)-1)/p2) / tr
            y = (t - k1 * (e1 - 1.0f) / p1 - k2 * (e2 - 1.0f) / p2) / tr;
            dy = (1.0f - k1 * e1 - k2 * e2) / tr;
        } else {
            // y = 1 - A*exp(p1*t) - B*exp(p2*t)
            float A = k1 * (1.0f - std::exp(-p1 * tr)) / (tr * p1);
            float B = k2 * (1.0f - std::exp(-p2 * tr)) / (tr * p2);
            y = 1.0f - A * e1 - B * e2;
            dy = -(A * p1 * e1 + B * p2 * e2);
        }
    };

    float t = t_hint;
    if (t <= 0.0f) t = tr * target;

    for (int iter = 0; iter < 20; ++iter) {
        float y, dy;
        eval(t, y, dy);
        float f = y - target;
        if (std::abs(f) < 1e-6f) return t;
        if (std::abs(dy) < 1e-15f) break;
        float dt = -f / dy;
        float alpha = 1.0f;
        for (int ls = 0; ls < 10; ++ls) {
            float t_new = t + alpha * dt;
            if (t_new < 0.0f) t_new = 0.0f;
            float y_new, dy_new;
            eval(t_new, y_new, dy_new);
            if (std::abs(y_new - target) < std::abs(f)) {
                t = t_new;
                break;
            }
            alpha *= 0.5f;
            if (alpha < 1e-4f) {
                t = t_new;
                break;
            }
        }
    }
    return t;
}

PiResponse AweDelayCalc::compute_pi_response(
    const PiModel& pi, float input_slew, float rd, float lower, float upper) const {
    PiResponse resp;

    // Degenerate cases: no resistance or no capacitance
    if (pi.rpi <= 0.0f && rd <= 0.0f) {
        resp.delay = 0.0f;
        resp.slew = input_slew;
        return resp;
    }

    float c1 = pi.c1;
    float c2 = pi.c2;
    float rpi = pi.rpi;
    float ctot = c1 + c2;

    if (ctot <= 0.0f) {
        resp.delay = 0.0f;
        resp.slew = input_slew;
        return resp;
    }

    // Convert to ps-compatible units.
    // cap_scale converts native cap to farads.
    // rd[Ω] * ctot[farad] = seconds.  Multiply by 1e12 to get ps.
    // => b1[ps] = (rd * ctot + rpi * c1) * (cap_scale / 1e-12)
    float cap_to_ps = pi.cap_scale / 1e-12f;
    float b1 = (rd * ctot + rpi * c1) * cap_to_ps;
    float b2 = rd * rpi * c1 * c2 * cap_to_ps * cap_to_ps;

    if (b1 <= 1e-9f) {
        resp.delay = 0.0f;
        resp.slew = input_slew;
        return resp;
    }

    // Single-pole threshold: when b2 is negligible compared to b1²
    float b1_sq = b1 * b1;
    const float POLE_THRESH = 1e-6f;
    bool single_pole = (b2 <= POLE_THRESH * b1_sq) || (rd <= 1e-3f) || (rpi <= 1e-3f);

    // input_slew is in ns, but b1/b2 are in ps/ps².
    // Convert tr to ps so the solver uses consistent units.
    float tr = input_slew * 1000.0f; // ramp transition time [ps]

    // Initial delay guess: D2M step delay + tr/2 for ramp
    float t50_hint = d2m_delay(b1, b2) + tr * 0.5f;
    if (t50_hint < tr * 0.1f) t50_hint = tr * 0.1f;

    float t50 = 0.0f;
    float t20 = 0.0f;
    float t80 = 0.0f;

    if (single_pole) {
        float p = -1.0f / b1;
        t50 = solve_single_pole_target(p, tr, 0.5f, t50_hint);
        float t20_hint = std::max(tr * 0.05f, t50 * 0.3f);
        float t80_hint = std::max(tr * 0.9f, t50 * 1.5f);
        t20 = solve_single_pole_target(p, tr, lower, t20_hint);
        t80 = solve_single_pole_target(p, tr, upper, t80_hint);
    } else {
        // 2-pole system
        float disc = b1_sq - 4.0f * b2;
        if (disc < 0.0f) disc = 0.0f; // should not happen for RC, but guard
        float sqrt_d = std::sqrt(disc);

        // Poles: p1 is fast (more negative), p2 is slow
        float denom = 2.0f * b2;
        float p1 = (-b1 - sqrt_d) / denom;
        float p2 = (-b1 + sqrt_d) / denom;

        // Cap p1 to avoid underflow in exp()
        const float P_MAX = -1e4f; // 1/exp(10000) underflows anyway
        if (p1 < P_MAX) {
            // Effectively single-pole dominated by p2
            single_pole = true;
            float p = p2;
            t50 = solve_single_pole_target(p, tr, 0.5f, t50_hint);
            float t20_hint = std::max(tr * 0.05f, t50 * 0.3f);
            float t80_hint = std::max(tr * 0.9f, t50 * 1.5f);
            t20 = solve_single_pole_target(p, tr, lower, t20_hint);
            t80 = solve_single_pole_target(p, tr, upper, t80_hint);
        } else {
            // k1 + k2 = 1, k1 = p2/(p2-p1), k2 = p1/(p1-p2)
            float dp = p2 - p1;
            float k1 = (std::abs(dp) > 1e-12f) ? p2 / dp : 0.5f;
            float k2 = 1.0f - k1;

            t50 = solve_ramp_target(p1, p2, k1, k2, tr, 0.5f, t50_hint);
            float t20_hint = std::max(tr * 0.05f, t50 * 0.3f);
            float t80_hint = std::max(tr * 0.9f, t50 * 1.5f);
            t20 = solve_ramp_target(p1, p2, k1, k2, tr, lower, t20_hint);
            t80 = solve_ramp_target(p1, p2, k1, k2, tr, upper, t80_hint);
        }
    }

    // Convert results from ps back to ns.
    resp.delay = t50 / 1000.0f;
    resp.slew = (t80 - t20) / 1000.0f;
    if (resp.slew < tr * 0.0001f) resp.slew = tr / 1000.0f;
    return resp;
}

PiResponse AweDelayCalc::compute_pi_response(float c1, float rpi, float c2, float cap_scale,
                                             float input_slew, float rd) const {
    return te::compute_pi_response(c1, rpi, c2, cap_scale, input_slew, rd);
}

PiResponse compute_pi_response(float c1, float rpi, float c2, float cap_scale,
                               float input_slew, float rd) {
    AweDelayCalc calc;
    return calc.compute_pi_response(PiModel{c1, rpi, c2, cap_scale}, input_slew, rd);
}

} // namespace te
