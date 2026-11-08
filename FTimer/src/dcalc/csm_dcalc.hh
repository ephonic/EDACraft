#pragma once

#include <vector>
#include <utility>

#include "edacraft/core/liberty_db.hpp"
#include "time_engine/types.hh"
#include "parasitics/timing_parasitics.hh"

namespace te {

// ────────────────────────────────────────────────────────────
// CSM (Current Source Model) delay calculator
// ────────────────────────────────────────────────────────────
//
// Replaces the fixed NLDM gate_delay with a current-source driver
// model.  The output_current table gives I(t) for a given input slew
// and load cap.  We numerically integrate the current into the actual
// load (lumped cap or Pi-model RC network) to obtain V(t), then
// extract delay (50 % Vdd crossing) and slew (20 %–80 % Vdd).
//
// Two integration modes:
//   1. Lumped capacitance: trapezoidal rule (2nd-order accurate).
//   2. Pi model (C2–Rpi–C1): implicit backward-Euler on the two-node
//      RC network driven by a time-varying current source.
// ────────────────────────────────────────────────────────────

class CsmDelayCalc {
public:
    struct Result {
        Delay delay;  // 50 % crossing time
        Slew slew;    // slew_lower–slew_upper transition time
        bool physical_slew = false; // NLDM fallbacks are already normalized
        float effective_capacitance = 0.0f;
    };

    // Pre-compute integrated t50 and slew at each corner waveform.
    // Call once after the table is loaded.  Subsequent calls are no-ops.
    void precompute_corner_delays(edacraft::core::CsmOutputCurrentTable& table,
                                  float slew_lower = 0.2f,
                                  float slew_upper = 0.8f,
                                  float vdd = 1.0f) const;

    // Compute delay/slew from CSM output current table.
    //   current_table : output_current_rise or output_current_fall
    //   input_slew    : transition time at the driver input
    //   load_cap      : total effective capacitance driven by this pin
    //   vdd           : supply voltage (from library nom_voltage or PVT)
    //   pi            : reduced Pi model from SPEF (rpi==0 → lumped cap)
    //   r_driver      : optional driver output resistance (0 = ideal current source)
    //   delay_nldm    : optional NLDM delay table for lumped-cap mode
    //   slew_nldm     : optional NLDM output slew table for lumped-cap mode
    //   slew_lower    : lower slew threshold as fraction of Vdd (default 0.2)
    //   slew_upper    : upper slew threshold as fraction of Vdd (default 0.8)
    Result gate_delay(const edacraft::core::CsmOutputCurrentTable& current_table,
                      float input_slew,
                      float load_cap,
                      float vdd,
                      const PiModel& pi,
                      float r_driver = 0.0f,
                      const edacraft::core::NldmTable* delay_nldm = nullptr,
                      const edacraft::core::NldmTable* slew_nldm = nullptr,
                      float slew_lower = 0.2f,
                      float slew_upper = 0.8f,
                      float miller_cap = 0.0f) const;

private:
    friend class RcWaveformCalc;
    // Find bracketing indices in (slew, cap) for bilinear interpolation.
    void find_bracketing(const edacraft::core::CsmOutputCurrentTable& table,
                         float input_slew,
                         float load_cap,
                         size_t& s0, size_t& s1, float& s_frac,
                         size_t& c0, size_t& c1, float& c_frac) const;

    // Select / bilinearly interpolate the current waveform for the
    // given (input_slew, load_cap) operating point.
    void select_waveform(const edacraft::core::CsmOutputCurrentTable& table,
                         float input_slew,
                         float load_cap,
                         std::vector<float>& out_time,
                         std::vector<float>& out_current,
                         float& out_reference_time, float vdd = 1.0f) const;

    // Trapezoidal integration of I(t) into a lumped capacitor.
    // voltage[0] is initialised to 0 (ground).  voltage[i] corresponds
    // to time[i].  The result is clamped to [0, vdd].
    void integrate_lumped_cap_trapezoidal(const std::vector<float>& time,
                                          const std::vector<float>& current,
                                          float cap,
                                          float vdd,
                                          float r_driver,
                                          float miller_cap,
                                          std::vector<float>& voltage) const;

    // Implicit backward-Euler integration of I(t) into a Pi-model
    // RC network (C2 at driver node, Rpi to far node, C1 + load_cap
    // at far node). Computes driver voltage for the cell arc;
    // the net arc accounts for propagation to each receiver separately.
    void integrate_pi_model(const std::vector<float>& time,
                            const std::vector<float>& current,
                            float load_cap,
                            float vdd,
                            const PiModel& pi,
                            float r_driver,
                            float miller_cap,
                            std::vector<float>& voltage) const;

    // Linear interpolation: find t where f(t) = target_value.
    // Assumes the waveform is monotonic (valid for a single transition).
    float interpolate_crossing(const std::vector<float>& time,
                               const std::vector<float>& voltage,
                               float target) const;
};

} // namespace te
