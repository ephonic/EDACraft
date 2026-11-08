#pragma once

#include "awe_dcalc.hh"
#include "csm_dcalc.hh"
#include "delay_result.hh"
#include "edacraft/core/liberty_db.hpp"

#include <algorithm>
#include <cmath>

namespace te {

// ────────────────────────────────────────────────────────────
// Unified delay calculator: 2-pole AWE for net edges
// ────────────────────────────────────────────────────────────
// Thin wrapper around AweDelayCalc::compute_pi_response() that
// computes wire delay and slew degradation for a net edge.
//
// Given a reduced Pi model, a gate output slew, and an estimated
// driver resistance, returns the 50% delay and 20%-80% slew at
// the load node using an analytical 2-pole ramp response.

class UnifiedDelayCalc {
public:
    UnifiedDelayCalc() = default;

    // Compute wire delay and load slew for a net edge.
    PiResponse net_edge(
        const PiModel& pi,
        float gate_output_slew,
        float rd
    ) const {
        return awe_.compute_pi_response(pi, gate_output_slew, rd);
    }

    DelayResult calculate_net_edge(
        const PiModel& pi,
        float gate_output_slew,
        float rd
    ) const {
        DelayResult result;
        result.output_slew = Slew{gate_output_slew};
        result.ceff = pi.c1 + pi.c2;

        if (pi.rpi <= 0.0f && pi.c1 <= 0.0f && pi.c2 <= 0.0f) {
            result.source = DelayModelSource::Lumped;
            return result;
        }

        auto response = awe_.compute_pi_response(pi, gate_output_slew, rd);
        result.converged = std::isfinite(response.delay) &&
                           std::isfinite(response.slew);
        if (!result.converged) {
            return result;
        }

        result.delay = Delay{std::max(0.0f, response.delay)};
        result.output_slew = Slew{std::max(0.0f, response.slew)};
        result.source = DelayModelSource::AwePi;
        return result;
    }

    DelayResult calculate_nldm_gate_arc(
        const edacraft::core::NldmTable& delay_table,
        const edacraft::core::NldmTable& slew_table,
        float input_slew,
        float load_cap
    ) const {
        DelayResult result;
        result.ceff = load_cap;
        result.source = DelayModelSource::Nldm;

        if (delay_table.rows == 0 || delay_table.cols == 0 ||
            slew_table.rows == 0 || slew_table.cols == 0) {
            result.converged = false;
            return result;
        }

        float delay = delay_table.lookup(input_slew, load_cap);
        float slew = slew_table.lookup(input_slew, load_cap);
        result.converged = std::isfinite(delay) && std::isfinite(slew);
        if (!result.converged) {
            return result;
        }

        // A characterized cell delay may be negative: input/output voltage
        // thresholds need not cross in temporal order. Only slew is unsigned.
        result.delay = Delay{delay};
        result.output_slew = Slew{std::max(0.0f, slew)};
        return result;
    }

    // First-moment RC-tree response from an already timed driver waveform.
    // Driver impedance belongs to the cell calculation; adding it here would
    // count the same load delay twice. Each sink has its own Elmore moment.
    DelayResult calculate_rc_tree_edge(float elmore_ns, float slew,
                                      float lower, float upper, float derate) const {
        DelayResult result;
        result.source = DelayModelSource::AwePi;
        result.output_slew = Slew{slew};
        if (elmore_ns <= 0.0f) return result;
        const float scale = derate > 0.0f ? derate : 1.0f;
        const float span = std::max(upper - lower, 1e-6f);
        const float ramp = slew * scale / span;
        PiModel equivalent{1.0f, elmore_ns * 1000.0f, 0.0f, 1e-12f};
        const auto response = awe_.compute_pi_response(equivalent, ramp, 0.0f, lower, upper);
        result.delay = Delay{std::max(0.0f, response.delay - ramp * 0.5f)};
        result.output_slew = Slew{response.slew / scale};
        result.converged = std::isfinite(result.delay.value) && std::isfinite(result.output_slew.value);
        return result;
    }

    DelayResult calculate_csm_gate_arc(
        const CsmDelayCalc& csm_calc,
        const edacraft::core::CsmOutputCurrentTable& current_table,
        float input_slew,
        float load_cap,
        float vdd,
        const PiModel& pi,
        float r_driver = 0.0f,
        const edacraft::core::NldmTable* delay_nldm = nullptr,
        const edacraft::core::NldmTable* slew_nldm = nullptr,
        float slew_lower = 0.2f,
        float slew_upper = 0.8f,
        float miller_cap = 0.0f,
        float slew_derate = 1.0f
    ) const {
        DelayResult result;
        result.ceff = load_cap;
        result.source = DelayModelSource::Csm;

        if (current_table.empty()) {
            result.converged = false;
            return result;
        }

        auto csm_result = csm_calc.gate_delay(current_table, input_slew,
                                              load_cap, vdd, pi, r_driver,
                                              delay_nldm, slew_nldm,
                                              slew_lower, slew_upper,
                                              miller_cap);
        result.converged = std::isfinite(csm_result.delay.value) &&
                           std::isfinite(csm_result.slew.value);
        if (!result.converged) {
            return result;
        }

        result.delay = csm_result.delay;
        result.ceff = csm_result.effective_capacitance;
        const float normalization = csm_result.physical_slew && slew_derate > 0.0f
            ? slew_derate : 1.0f;
        result.output_slew = Slew{std::max(0.0f, csm_result.slew.value / normalization)};
        return result;
    }

    // Estimate driver resistance from NLDM output-slew table.
    static float estimate_rd(const edacraft::core::NldmTable& slew_table) {
        return AweDelayCalc::estimate_rd(slew_table);
    }

private:
    AweDelayCalc awe_;
};

} // namespace te
