#include "dmp_ceff.hh"

#include <algorithm>
#include <cmath>

namespace te {

namespace ec = edacraft::core;

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────
DmpCeffResult DmpCeffCalc::compute(
    const PiModel& pi,
    float input_slew,
    const ec::NldmTable& delay_table,
    const ec::NldmTable& slew_table) const
{
    DmpCeffResult result;

    // Estimate driver resistance first (needed for degeneracy checks)
    result.rd = estimate_rd(slew_table);

    // Pure capacitive load — degenerate cases that OpenSTA also shortcuts:
    // 1. Rd is negligible (constant-delay cell)
    // 2. Rpi is tiny compared to Rd (load looks capacitive)
    // 3. C1 is negligible or Rpi is zero
    if (result.rd < 1e-2f
        || pi.rpi < result.rd * 1e-3f
        || (pi.c1 == 0.0f || pi.c1 < pi.c2 * 1e-3f || pi.rpi == 0.0f)) {
        float load = pi.c1 + pi.c2;
        result.ceff  = load;
        result.delay = delay_table.lookup(input_slew, load);
        result.slew  = std::max(0.0f, slew_table.lookup(input_slew, load));
        return result;
    }

    // Phase 1: analytical approximation
    result.ceff = ceff_approx(pi.c1, pi.rpi, pi.c2, input_slew, slew_table);

    // Lookup final delay / slew with Ceff
    result.delay = delay_table.lookup(input_slew, result.ceff);
    result.slew  = std::max(0.0f, slew_table.lookup(input_slew, result.ceff));

    // Optional: second iteration for better convergence
    // (typically < 0.1% change, disabled for speed)
    // result.ceff = ceff_approx(pi.c1, pi.rpi, pi.c2, input_slew, slew_table);
    // result.delay = delay_table.lookup(input_slew, result.ceff);
    // result.slew  = slew_table.lookup(input_slew, result.ceff);

    return result;
}

// ────────────────────────────────────────────────────────────
// Driver resistance estimate
// ────────────────────────────────────────────────────────────
// OpenSTA heuristic: use the point with largest Cload.
// Rpi uses the Ohm*pF -> ns convention below, so Rd must use the
// same scale: ns/pF is kiloohms, requiring a factor of 1000.
// ────────────────────────────────────────────────────────────
float DmpCeffCalc::estimate_rd(const ec::NldmTable& slew_table)
{
    if (slew_table.cols == 0 || slew_table.rows == 0 ||
        slew_table.axis2.empty() || slew_table.values.empty()) return 0.0f;

    float cap  = slew_table.axis2.back();                     // largest cap
    // Load-only SRAM tables have one row and no input-transition axis.
    // NldmTable::lookup already handles that representation.
    float input = slew_table.axis1.empty() ? 0.0f : slew_table.axis1.front();
    float slew = slew_table.lookup(input, cap);
    if (cap > 1e-18f)
        return slew / cap * 1000.0f;
    return 0.0f;
}

// ────────────────────────────────────────────────────────────
// Phase-1 analytical Ceff
// ────────────────────────────────────────────────────────────
// One-pass Keutzer approximation:
//   Ceff = C2 + C1 * (1 - tanh(τ / slew))
// where τ = Rpi * C1.
// ────────────────────────────────────────────────────────────
float DmpCeffCalc::ceff_approx(float c1, float rpi, float c2,
                               float input_slew,
                               const ec::NldmTable& slew_table)
{
    // Initial guess: lumped cap
    float ceff = c1 + c2;

    // First-pass slew
    float output_slew = slew_table.lookup(input_slew, ceff);
    if (output_slew <= 1e-15f) return ceff;

    float tau = rpi * c1 * 1e-3f;  // Ohm * pF → ns (1 Ohm·pF = 1e-3 ns)
    float ratio = std::tanh(tau / output_slew);
    ceff = c2 + c1 * (1.0f - ratio);

    ceff = std::max(ceff, c2);
    ceff = std::min(ceff, c1 + c2);
    return ceff;
}

} // namespace te
