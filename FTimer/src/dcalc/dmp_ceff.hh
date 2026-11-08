#pragma once

#include <cmath>
#include "edacraft/core/liberty_db.hpp"
#include "parasitics/timing_parasitics.hh"

namespace te {

// ────────────────────────────────────────────────────────────
// DMP (Dartu/Menezes/Pileggi) Effective-Capacitance Calculator
// ────────────────────────────────────────────────────────────
// Phase 1 (current): analytical tanh approximation with one
//   iteration of slew feedback.
// Phase 2 (future): full Newton-Raphson for t0/dt/Ceff with
//   pole/residue waveform matching.
// ────────────────────────────────────────────────────────────
struct DmpCeffResult {
    float ceff = 0.0f;      // effective capacitance seen by driver
    float delay = 0.0f;     // gate delay
    float slew = 0.0f;      // output transition time
    float rd = 0.0f;        // normalized driver resistance (Ohms for ns/pF)
};

class DmpCeffCalc {
public:
    // Compute Ceff / delay / slew for a gate driving a Pi-model load.
    // If the Pi model is pure capacitive (rpi==0), returns lumped cap.
    DmpCeffResult compute(
        const PiModel& pi,
        float input_slew,
        const edacraft::core::NldmTable& delay_table,
        const edacraft::core::NldmTable& slew_table
    ) const;

private:
    // Estimate output driver resistance from NLDM slew table.
    // Uses the largest-capacitance point: Rd ≈ slew / cap.
    static float estimate_rd(const edacraft::core::NldmTable& slew_table);

    // Phase-1 analytical approximation (Keutzer / O'Brien).
    static float ceff_approx(float c1, float rpi, float c2,
                             float input_slew,
                             const edacraft::core::NldmTable& slew_table);

};

} // namespace te
