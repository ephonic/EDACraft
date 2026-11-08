#include "rc_waveform_dcalc.hh"
#include "rc_linear_system.hh"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <string>
#include <vector>

namespace te {
namespace {
double crossing(const std::vector<float>& x, const std::vector<float>& y, double target) {
    for (size_t i = 1; i < y.size(); ++i) {
        if (y[i-1] <= target && target <= y[i] && y[i] > y[i-1])
            return x[i-1] + (x[i]-x[i-1]) * (target-y[i-1]) / (y[i]-y[i-1]);
    }
    return std::numeric_limits<double>::quiet_NaN();
}
} // namespace

std::optional<RcWaveformResult> RcWaveformCalc::calculate(
    const CsmDelayCalc& csm, const edacraft::core::CsmOutputCurrentTable& table,
    const FullRcNetwork& rc, float input_slew, float vdd,
    const edacraft::core::NldmTable* delay_table,
    float lower, float upper, float slew_derate, float cap_unit, float time_unit,
    float driver_threshold, float load_threshold,
    const std::vector<RcReceiverCapacitance>* receivers,
    CcsSourceRepresentation source_representation,
    const RcDelayThresholds* load_thresholds,
    const RcSlewThresholds* load_slew_thresholds) const {
    if(load_thresholds) for(const auto& [node,threshold]:*load_thresholds)
        if(node>=rc.nodes.size() || !std::isfinite(threshold) || threshold<=0.f || threshold>=1.f)
            return std::nullopt;
    if(load_slew_thresholds) for(const auto& [node,w]:*load_slew_thresholds)
        if(node>=rc.nodes.size() || !std::isfinite(w.lower) || !std::isfinite(w.upper) ||
           !std::isfinite(w.derate) || w.lower<=0.f || w.upper>=1.f ||
           w.lower>=w.upper || w.derate<=0.f) return std::nullopt;
    const char* disable_surface=std::getenv("FSYN_TIMING_DISABLE_RC_SURFACE");
    if(!disable_surface || std::string(disable_surface)!="1") {
        auto surface=calculate_surface(csm,table,rc,input_slew,vdd,delay_table,
            lower,upper,slew_derate,cap_unit,time_unit,driver_threshold,load_threshold,receivers,
            source_representation,load_thresholds,load_slew_thresholds);
        if(surface) return surface;
    }
    const size_t n = rc.nodes.size();
    const uint32_t driver = rc.driver_node_id;
    if (n < 2 || driver >= n || vdd <= 0 || cap_unit <= 0 || time_unit <= 0 ||
        table.empty() || table.load_caps.empty() || lower >= upper ||
        driver_threshold <= 0 || driver_threshold >= 1 ||
        load_threshold <= 0 || load_threshold >= 1) return std::nullopt;

    std::vector<double> caps(n);
    std::vector<RcLinearSystem::Edge> edges;
    double total_cap = 0.0;
    std::vector<uint32_t> loads;
    for (size_t i = 0; i < n; ++i) {
        if (rc.nodes[i].id != i) return std::nullopt;
        caps[i] = rc.nodes[i].gnd_cap * double(rc.cap_scale) / cap_unit;
        if (caps[i] < 0 || !std::isfinite(caps[i])) return std::nullopt;
        total_cap += caps[i];
        if (i != driver && valid(rc.nodes[i].pin)) loads.push_back(static_cast<uint32_t>(i));
    }
    if (loads.empty() || total_cap <= 0 || total_cap > table.load_caps.back()*1.05)
        return std::nullopt;
    auto threshold_at=[&](uint32_t node) {
        if(node==driver) return driver_threshold;
        if(load_thresholds) {
            const auto it=load_thresholds->find(node);
            if(it!=load_thresholds->end()) return it->second;
        }
        return load_threshold;
    };
    for (const auto& r : rc.resistors) {
        const double resistance = r.resistance * double(rc.res_scale) * cap_unit / time_unit;
        if (r.node1 >= n || r.node2 >= n || resistance <= 0 || !std::isfinite(resistance))
            return std::nullopt;
        edges.push_back({r.node1,r.node2,1.0/resistance});
    }
    RcLinearSystem system;
    if (!system.initialize(n,driver,edges)) return std::nullopt;

    double ceff = total_cap;
    std::vector<double> voltage(n), next(n), rhs(n), cd(n);
    std::vector<std::array<double, 3>> times(n);
    std::vector<float> time, current, progress;
    double driver_crossing = 0.0, characterized_crossing = 0.0;
    const double nan = std::numeric_limits<double>::quiet_NaN();
    bool ceff_converged = false;
    for (unsigned iteration = 0; iteration < 32; ++iteration) {
        const double selected_cap = std::max(ceff, double(table.load_caps.front()));
        float reference = 0.0f;
        csm.select_waveform(table, input_slew, float(selected_cap), time, current, reference, vdd);
        if (time.size() < 2 || current.size() != time.size()) return std::nullopt;
        progress.assign(time.size(), 0.0f);
        for (size_t j = 1; j < time.size(); ++j) {
            const double dt = time[j]-time[j-1];
            if (dt <= 0) return std::nullopt;
            progress[j] = float(progress[j-1] + .5*(std::fabs(current[j])+std::fabs(current[j-1]))
                                *dt/(selected_cap*vdd));
        }
        characterized_crossing = crossing(time, progress, driver_threshold)-reference;
        const double width = crossing(time, progress, upper)-crossing(time, progress, lower);
        if (!std::isfinite(characterized_crossing) || !std::isfinite(width) || width <= 0)
            return std::nullopt;
        const double step = std::max(width/240.0, 1e-15/double(time_unit));
        // Fixed-step backward Euler is stable even for tiny near-end caps.
        // Factor the tree once, then solve its RHS for each waveform sample.
        for (size_t i = 0; i < n; ++i) {
            cd[i] = caps[i]/step;
            voltage[i] = 0.0;
            times[i] = {nan, nan, nan};
        }
        if (!system.factor(cd)) return std::nullopt;
        double measured_cap = nan;
        bool complete = false;
        for (unsigned tick = 1; tick <= 100000; ++tick) {
            for (size_t i = 0; i < n; ++i) rhs[i] = cd[i]*voltage[i];
            if (!system.reduce(rhs)) return std::nullopt;
            // CCS supplies I(V). For each linear segment the driver equation
            // has an exact scalar solution. Choose the first root reached as
            // the transition advances, avoiding unstable Newton steps.
            double vd = 1.0;
            size_t first = std::upper_bound(progress.begin(), progress.end(), float(voltage[driver]))
                           - progress.begin();
            if (first) --first;
            for (size_t j = first; j+1 < progress.size(); ++j) {
                const double span = progress[j+1]-progress[j];
                if (span <= 0) continue;
                const double i0 = std::fabs(current[j])/vdd;
                const double slope = (std::fabs(current[j+1])/vdd-i0)/span;
                const double denominator = system.driver_diagonal-slope;
                if (std::fabs(denominator) < 1e-20) continue;
                const double value = (system.driver_rhs+i0-slope*progress[j])/denominator;
                if (value >= std::max(voltage[driver], double(progress[j]))-1e-10 &&
                    value <= progress[j+1]+1e-10) {
                    vd = std::clamp(value, voltage[driver], 1.0);
                    break;
                }
            }
            system.back_substitute(vd,next);
            for (size_t i = 0; i < n; ++i) {
                const double middle = threshold_at(uint32_t(i));
                const auto w=rc_slew_window(uint32_t(i),lower,upper,slew_derate,load_slew_thresholds);
                const double target[3] = {w.lower, middle, w.upper};
                for (unsigned j = 0; j < 3; ++j) {
                    if (!std::isfinite(times[i][j]) && voltage[i] < target[j] && next[i] >= target[j])
                        times[i][j] = step*(tick-1 + (target[j]-voltage[i])/(next[i]-voltage[i]));
                }
            }
            if (!std::isfinite(measured_cap) && std::isfinite(times[driver][1])) {
                const double fraction = (driver_threshold-voltage[driver])/(next[driver]-voltage[driver]);
                measured_cap = 0.0;
                for (size_t i = 0; i < n; ++i)
                    measured_cap += caps[i]*(voltage[i]+fraction*(next[i]-voltage[i]))/driver_threshold;
            }
            voltage.swap(next);
            complete = std::isfinite(times[driver][0]) && std::isfinite(times[driver][1]) &&
                       std::isfinite(times[driver][2]);
            for (uint32_t u : loads) complete = complete && std::isfinite(times[u][0]) &&
                std::isfinite(times[u][1]) && std::isfinite(times[u][2]);
            if (complete) break;
        }
        if (!complete || !std::isfinite(measured_cap) || measured_cap <= 0) return std::nullopt;
        driver_crossing = times[driver][1];
        if (std::fabs(measured_cap-ceff) <= 1e-4*ceff) {
            ceff = measured_cap;
            ceff_converged = true;
            break;
        }
        // Long resistive wires can make the fixed-point updates alternate
        // between a strong driver/small Ceff and a weak driver/large Ceff.
        // Relax the update to converge without discarding the sink response.
        ceff = .5*(ceff + measured_cap);
    }
    if (!ceff_converged) return std::nullopt;

    RcWaveformResult result;
    result.load_within_table=total_cap<=double(table.load_caps.back())*
        (1.+8.*std::numeric_limits<float>::epsilon());
    // NLDM supplies the characterized absolute cell delay at Ceff. Its table
    // already includes input-reference and voltage-threshold normalization.
    // CCS-only libraries use the selected lumped waveform's threshold time.
    result.driver.delay = Delay{delay_table && !delay_table->values.empty()
        ? delay_table->lookup(input_slew, float(ceff)) : float(characterized_crossing)};
    const float normalization = slew_derate > 0 ? slew_derate : 1.0f;
    result.driver.output_slew = Slew{float((times[driver][2]-times[driver][0])/normalization)};
    result.driver.ceff = float(ceff);
    result.driver.source = DelayModelSource::Csm;
    for (uint32_t u : loads) {
        const auto w=rc_slew_window(u,lower,upper,normalization,load_slew_thresholds);
        DelayResult load;
        load.delay = Delay{float(times[u][1]-driver_crossing)};
        load.output_slew = Slew{float((times[u][2]-times[u][0])/w.derate)};
        load.ceff = float(total_cap);
        load.source = DelayModelSource::Csm;
        result.loads[rc.nodes[u].pin.id] = load;
    }
    return result;
}
} // namespace te
