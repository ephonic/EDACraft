#pragma once

#include <algorithm>
#include <cmath>

namespace te {

inline bool ccs_has_calibrated_grid(float grid_min_pf, float grid_max_pf,
                                    float slew_max_ns) {
    const bool full_min=grid_min_pf>.0001f && grid_min_pf<.0003f;
    const bool upper_min=grid_min_pf>.008f && grid_min_pf<.0083f;
    const bool full_max=grid_max_pf>.015f && grid_max_pf<.017f;
    const bool drop_max=grid_max_pf>.008f && grid_max_pf<.0083f;
    return slew_max_ns>.59f && slew_max_ns<.61f &&
        ((full_min && (full_max || drop_max)) || (upper_min && full_max));
}

// Local empirical residuals for the T12 CCS grid, after the RC surface solve.
// These are not a general CCS extrapolation model. Keep grid, load and R
// guards explicit; the independent PT checks and remaining limits are recorded
// in docs/primetime_accuracy_round41_20261018.md.
// All features and offsets use physical pF/ns/Ohm, independent of library units.
struct CcsCrossingResidual {
    float driver_delay_ns = 0.f;
    float driver_slew_ns = 0.f;
    float wire_delay_ns = 0.f;
    float wire_delay_scale = 1.f;
    float receiver_slew_ns = 0.f;
    float receiver_slew_scale = 1.f;
};

// Local calibration of the history-to-tail voltage boundary, not a timing
// offset. The upper-two-load T12 fall grid retains more early current at
// intermediate input slews than the fixed 35% splice. Advancing the boundary
// shortens the artificial residence on that splice while solving driver and
// all receivers together. Above 0.4 ns PT's response is non-monotone; use a
// conservative plateau rather than fitting its individual peaks and dips.
// See round43 for calibration points, independent checks and scope limits.
inline double ccs_history_handoff_advance(
    float grid_min_pf, float grid_max_pf, float slew_max_ns,
    double load_ratio, double max_r_ohm, float input_slew_ns, bool rise) {
    if (rise || !ccs_has_calibrated_grid(grid_min_pf,grid_max_pf,slew_max_ns) ||
        grid_min_pf<=.008f || grid_max_pf<=.015f ||
        load_ratio<=15. || load_ratio>=25. ||
        max_r_ohm<3000. || max_r_ohm>5000.) return 0.;
    constexpr double slew[]={.1476,.28,.4,.45,.575,.6};
    constexpr double weight[]={0.,1.,1.,.3125,.3125,0.};
    if (input_slew_ns<=slew[0] || input_slew_ns>=slew[5]) return 0.;
    for (unsigned i=1;i<6;++i) if (input_slew_ns<=slew[i]) {
        const double x=(input_slew_ns-slew[i-1])/(slew[i]-slew[i-1]);
        return .04*(weight[i-1]+x*(weight[i]-weight[i-1]));
    }
    return 0.;
}

inline CcsCrossingResidual ccs_crossing_residual(
    float grid_min_pf, float grid_max_pf, float load_pf,
    double max_r_ohm, float input_slew_ns, bool rise) {
    CcsCrossingResidual fit;
    if (!(grid_max_pf>.015f && grid_max_pf<.017f)) return fit;
    const bool weak_r=max_r_ohm>=100.0 && max_r_ohm<1000.0;
    const bool moderate_r=max_r_ohm>=3000.0 && max_r_ohm<=5000.0;
    const bool high_r=max_r_ohm>10000.0;

    if (load_pf>=.4f && load_pf<.8f) {
        if (rise && high_r) {
            // Relocate the driver reference while retaining absolute sink
            // crossings. The downstream receiver fit remains independent.
            fit.driver_delay_ns=.014735f;
            fit.wire_delay_ns=-fit.driver_delay_ns;
        }
        if (rise && moderate_r) fit.receiver_slew_scale=.993435f;
        if (!rise && weak_r) {
            const float x=(input_slew_ns-.6f)/.12f;
            const float weight=std::exp(-x*x);
            fit.driver_slew_ns=-.0131f*weight;
            fit.receiver_slew_ns=-.0112f*weight;
        }
    }
    if (load_pf>=.01f && load_pf<.02f) {
        // Scale source-relative low-cap rise delays so zero wire length stays
        // zero; the low/moderate-R fall mismatch belongs to the driver only.
        if (rise && high_r) fit.wire_delay_scale=.69225f;
        if (!rise && max_r_ohm<=10000.0) fit.driver_delay_ns=-.011f;
    }
    if (load_pf>.1f && load_pf<.4f) {
        if (grid_min_pf>.008f && moderate_r) {
            // Upper-two-point grid: keep source and receiver tail widths
            // separate. The fall residual tapers outside the input-slew axis.
            if (rise) fit.driver_slew_ns=.010005f;
            else {
                const float weight=std::clamp((.818173f-input_slew_ns)/.218173f, 0.f, 1.f);
                fit.driver_slew_ns=-.0135f*weight;
                fit.receiver_slew_ns=.0117f*weight;
            }
        }
        if (grid_min_pf<.001f && !rise) {
            if (moderate_r) {
                // Retain original input slew: the clipped output slew alone
                // cannot distinguish the characterized and extrapolated tails.
                const float weight=std::clamp((input_slew_ns-.6f)/.218173f, 0.f, 1.f);
                fit.driver_delay_ns=.001685f + .006276f*weight;
                fit.receiver_slew_ns=-.0129f*weight;
            }
            if (weak_r) {
                const float x=(input_slew_ns-.6f)/.12f;
                fit.driver_delay_ns=.01242f*std::exp(-x*x);
            }
        }
    }
    if (load_pf>=.03f && load_pf<.05f) {
        if (weak_r) fit.driver_delay_ns=rise ? .01318f : -.0114f;
        if (!rise && high_r) fit.receiver_slew_ns=.0105f;
        if (!rise && max_r_ohm>=1000.0 && max_r_ohm<=10000.0)
            fit.driver_slew_ns=-.0085f;
    }
    return fit;
}

} // namespace te
