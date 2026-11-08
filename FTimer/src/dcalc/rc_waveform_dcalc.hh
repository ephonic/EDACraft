#pragma once

#include "csm_dcalc.hh"
#include "delay_result.hh"
#include <array>
#include <limits>
#include <optional>
#include <unordered_map>
#include <vector>

namespace te {

// Raw measured-current integration and PT's compressed runtime source have
// different time origins for a sub-0.5% peak. Keep the choice explicit so
// physical RC calculations retain their independent charge oracle.
enum class CcsSourceRepresentation { Measured, PrimeTimeCompressed };

struct RcReceiverCapacitance {
    uint32_t node;
    // Capacitances use the extraction's cap_scale, as do node ground caps.
    float first, second, threshold;
    // RF-averaged lumped receiver used to build the fixed MOR basis. Zero
    // means the caller did not supply a separate reference capacitance.
    float nominal = 0.f;
    // Transition-specific means of the characterized C1/C2 grids. These
    // choose the initial solve; they do not replace the MOR reference above.
    float nominal_first = 0.f, nominal_second = 0.f;
    // Analysis-specific RF-averaged load selects the retained CCS columns.
    // It must not replace the fixed Max reference used by the voltage basis.
    float source_nominal = 0.f;
    // Analysis-specific nominal RF pin caps, in the extracted RC units.
    // These are lumped Liberty values, not regional receiver-grid averages.
    float nominal_rise = 0.f, nominal_fall = 0.f;
    // Opposite RF regional-cap envelope (RC units) and joint input slew (ns).
    float admission_cap = 0.f, admission_slew_ns = 0.f;
    // A short initialization rejected after the receiver update stays
    // distributed and retains the short source's bracketing load columns.
    bool force_distributed = false;
    // Ground before this regional pin load was added; optional for callers.
    float extracted_ground = std::numeric_limits<float>::quiet_NaN();
    // Fixed CCS basis reference, converted without another unit-rounding step.
    double precise_nominal = std::numeric_limits<double>::quiet_NaN();
};

// Optional delay measurement overrides by RC node. Values are transition
// progress (1-input_threshold_pct_fall for a falling transition).
using RcDelayThresholds = std::unordered_map<uint32_t, float>;

// Receiver measurement windows in the driver's normalized voltage. A falling
// transition uses progress 1-V/Vdriver; derate belongs to the receiver library.
struct RcSlewWindow { float lower, upper, derate; };
using RcSlewThresholds = std::unordered_map<uint32_t, RcSlewWindow>;
inline RcSlewWindow rc_slew_window(uint32_t node, float lower, float upper,
                                  float derate, const RcSlewThresholds* windows) {
    if(windows) {
        const auto it=windows->find(node);
        if(it!=windows->end()) return it->second;
    }
    return {lower,upper,derate};
}
// Delay-threshold overrides must not move the split used by a receiver's
// two slew segments. A supplied voltage window has its own physical center.
inline float rc_slew_middle(uint32_t node, float fallback, const RcSlewThresholds* windows) {
    if(windows) {
        const auto it=windows->find(node);
        if(it!=windows->end()) return .5f*(it->second.lower+it->second.upper);
    }
    return fallback;
}

struct RcWaveformResult {
    DelayResult driver;
    // Net delays are measured relative to the driver threshold crossing.
    std::unordered_map<uint32_t, DelayResult> loads;
    std::unordered_map<uint32_t, std::array<float, 2>> receiver_slews;
    bool time_voltage_surface = false;
    // A native CCS load column integrated in the equipotential RC limit.
    // Empirical interpolation/extrapolation fits must not shift these crossings.
    bool native_lumped_waveform = false;
    // Coverage of the actual loaded network, including receiver capacitance.
    // A Pi estimate at the call site can differ after receiver refinement.
    bool load_within_table = false;
    // The adaptive source/ROM integrator measures crossings directly. Legacy
    // residual fits describe the older solver and must not alter these results.
    bool adaptive_integration = false;
    // The short-network CCS runtime consumes the initial regional caps.
    // Its result must not enter the distributed receiver-refinement pass.
    bool lumped_ccs_runtime = false;
    // The initial nominal solve was short, but its loaded solve is distributed.
    // Receiver refinement must start from that distributed waveform.
    bool initial_short_ccs_runtime = false;
};

// Solve a passive RC network driven by the CCS current source. Trees use
// linear-time elimination; meshes retain all resistor branches.
class RcWaveformCalc {
public:
    // Preliminary equipotential CCS waveform used to update C1/C2 before
    // distributed integration. This estimate is not a propagated net delay.
    std::optional<RcWaveformResult> estimate_receiver_slews(
        const edacraft::core::CsmOutputCurrentTable&, const FullRcNetwork&,
        float input_slew, float vdd, float lower, float upper, float slew_derate,
        float cap_unit_farads, float load_threshold,
        const std::vector<RcReceiverCapacitance>&,
        const RcSlewThresholds* load_slew_thresholds = nullptr) const;
    std::optional<RcWaveformResult> calculate(
        const CsmDelayCalc& csm, const edacraft::core::CsmOutputCurrentTable& table,
        const FullRcNetwork& rc, float input_slew, float vdd,
        const edacraft::core::NldmTable* delay_table,
        float lower, float upper, float slew_derate,
        float cap_unit_farads = 1e-12f, float time_unit_seconds = 1e-9f,
        float driver_threshold = .5f, float load_threshold = .5f,
        const std::vector<RcReceiverCapacitance>* receivers = nullptr,
        CcsSourceRepresentation source_representation = CcsSourceRepresentation::Measured,
        const RcDelayThresholds* load_thresholds = nullptr,
        const RcSlewThresholds* load_slew_thresholds = nullptr) const;
private:
    std::optional<RcWaveformResult> calculate_surface(
        const CsmDelayCalc&, const edacraft::core::CsmOutputCurrentTable&,
        const FullRcNetwork&, float, float, const edacraft::core::NldmTable*,
        float, float, float, float, float, float, float,
        const std::vector<RcReceiverCapacitance>*, CcsSourceRepresentation,
        const RcDelayThresholds*, const RcSlewThresholds*) const;
};

} // namespace te
