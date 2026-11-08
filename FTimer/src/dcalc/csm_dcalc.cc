#include "csm_dcalc.hh"
#include "dmp_ceff.hh"

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <cstdlib>
#include <cmath>
#include <iostream>
#include <limits>
#include <string>

namespace te {

namespace ec = edacraft::core;

static bool env_flag_enabled(const char* name) {
    const char* value = std::getenv(name);
    if (!value) return false;
    std::string text(value);
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return text == "1" || text == "true" || text == "yes" || text == "on";
}

static float env_float_or_default(const char* name, float fallback) {
    const char* value = std::getenv(name);
    if (!value || !*value) return fallback;
    char* end = nullptr;
    float parsed = std::strtof(value, &end);
    if (end == value || !std::isfinite(parsed)) return fallback;
    return parsed;
}

static float interpolate_current_at_relative_time(const ec::CsmWaveform& wf,
                                                  float rel_time) {
    const size_t n = std::min(wf.time_points.size(), wf.current.size());
    if (n == 0) return 0.0f;

    auto rel_at = [&](size_t idx) {
        return wf.time_points[idx] - wf.reference_time;
    };

    const float first = rel_at(0);
    const float last = rel_at(n - 1);
    if (rel_time < first || rel_time > last) {
        return 0.0f;
    }
    if (rel_time == first) return wf.current[0];
    if (rel_time == last) return wf.current[n - 1];

    auto it = std::lower_bound(
        wf.time_points.begin(), wf.time_points.begin() + static_cast<std::ptrdiff_t>(n),
        rel_time + wf.reference_time);
    size_t hi = static_cast<size_t>(it - wf.time_points.begin());
    if (hi == 0) return wf.current[0];
    if (hi >= n) return wf.current[n - 1];
    size_t lo = hi - 1;
    const float t0 = rel_at(lo);
    const float t1 = rel_at(hi);
    if (t1 <= t0) return wf.current[lo];
    const float frac = (rel_time - t0) / (t1 - t0);
    return wf.current[lo] + frac * (wf.current[hi] - wf.current[lo]);
}

static void append_relative_time_grid(const ec::CsmWaveform* wf,
                                      std::vector<float>& grid) {
    if (!wf) return;
    const size_t n = std::min(wf->time_points.size(), wf->current.size());
    grid.reserve(grid.size() + n);
    for (size_t i = 0; i < n; ++i) {
        grid.push_back(wf->time_points[i] - wf->reference_time);
    }
}

// ────────────────────────────────────────────────────────────
// Corner delay / slew precomputation
// ────────────────────────────────────────────────────────────

// A linearly interpolated current has a quadratic voltage integral. Solve
// that integral before clipping the endpoint to the rails; interpolating
// clipped voltage samples shifts crossings of sparse or overshooting pulses.
static float lumped_current_crossing(const std::vector<float>& time,
                                    const std::vector<float>& current,
                                    double cap, double vdd, double target) {
    const size_t n=std::min(time.size(),current.size());
    if(n==0 || cap<=0.) return 0.f;
    double voltage=0.;
    for(size_t k=0;k<n;++k) if(std::fabs(current[k])>1e-12f) {
        if(current[k]<0.f) voltage=vdd;
        break;
    }
    for(size_t k=1;k<n;++k) {
        const double dt=double(time[k])-time[k-1];
        if(dt<=0.) continue;
        const double b=current[k-1];
        const double a=.5*(double(current[k])-b)/dt;
        const double c=cap*(voltage-target);
        double elapsed=std::numeric_limits<double>::infinity();
        auto accept=[&](double root) {
            if(root>=0. && root<=dt) elapsed=std::min(elapsed,root);
        };
        if(c==0.) accept(0.);
        if(a==0.) {
            if(b!=0.) accept(-c/b);
        } else {
            const double discriminant=b*b-4.*a*c;
            if(discriminant>=0.) {
                const double q=-.5*(b+std::copysign(std::sqrt(discriminant),b));
                accept(q/a);
                if(q!=0.) accept(c/q);
            }
        }
        if(std::isfinite(elapsed)) return float(time[k-1]+elapsed);
        voltage=std::clamp(voltage+(a*dt+b)*dt/cap,0.,vdd);
    }
    return time[n-1];
}

static float compute_corner_t50(const ec::CsmWaveform& wf, float cap, float vdd) {
    if(wf.time_points.empty() || wf.current.empty() || cap<=0.f) return 0.f;
    return lumped_current_crossing(wf.time_points,wf.current,cap,vdd,.5*vdd)-wf.reference_time;
}

static float compute_corner_slew(
    const ec::CsmWaveform& wf, float cap, float vdd,
    float slew_lower, float slew_upper)
{
    if(wf.time_points.empty() || wf.current.empty() || cap<=0.f) return 0.f;
    const float first=lumped_current_crossing(wf.time_points,wf.current,cap,vdd,double(vdd)*slew_lower);
    const float last=lumped_current_crossing(wf.time_points,wf.current,cap,vdd,double(vdd)*slew_upper);
    return std::fabs(last-first);
}

void CsmDelayCalc::precompute_corner_delays(ec::CsmOutputCurrentTable& table, float slew_lower, float slew_upper, float vdd) const {
    if (table.empty()) return;
    bool need_delay = table.corner_delays.empty();
    bool need_slew  = table.corner_slews.empty();
    if (!need_delay && !need_slew) return;

    if (need_delay) table.corner_delays.resize(table.nslew * table.ncap);
    if (need_slew)  table.corner_slews.resize(table.nslew * table.ncap);

    float vdd_eff = (vdd > 0.0f) ? vdd : 1.0f;
    for (uint32_t si = 0; si < table.nslew; ++si) {
        for (uint32_t ci = 0; ci < table.ncap; ++ci) {
            size_t idx = si * table.ncap + ci;
            const auto& wf = table.waveforms[idx];
            float cap = table.load_caps.empty() ? 1.0f : table.load_caps[ci];
            if (need_delay) table.corner_delays[idx] = compute_corner_t50(wf, cap, vdd_eff);
            if (need_slew)  table.corner_slews[idx]  = compute_corner_slew(wf, cap, vdd_eff, slew_lower, slew_upper);
        }
    }
}

// ────────────────────────────────────────────────────────────
// Public API
// ────────────────────────────────────────────────────────────

void CsmDelayCalc::find_bracketing(
    const ec::CsmOutputCurrentTable& table,
    float input_slew,
    float load_cap,
    size_t& s0, size_t& s1, float& s_frac,
    size_t& c0, size_t& c1, float& c_frac) const
{
    s0 = s1 = 0; s_frac = 0.0f;
    if (!table.input_slews.empty()) {
        if (input_slew <= table.input_slews.front()) { s0 = s1 = 0; }
        else if (input_slew >= table.input_slews.back()) { s0 = s1 = table.input_slews.size() - 1; }
        else {
            auto it = std::lower_bound(table.input_slews.begin(), table.input_slews.end(), input_slew);
            s1 = static_cast<size_t>(it - table.input_slews.begin());
            s0 = s1 - 1;
            float a0 = table.input_slews[s0], a1 = table.input_slews[s1];
            s_frac = (a1 == a0) ? 0.0f : (input_slew - a0) / (a1 - a0);
        }
    }

    c0 = c1 = 0; c_frac = 0.0f;
    if (!table.load_caps.empty()) {
        if (load_cap <= table.load_caps.front()) { c0 = c1 = 0; }
        else if (load_cap >= table.load_caps.back()) { c0 = c1 = table.load_caps.size() - 1; }
        else {
            auto it = std::lower_bound(table.load_caps.begin(), table.load_caps.end(), load_cap);
            c1 = static_cast<size_t>(it - table.load_caps.begin());
            c0 = c1 - 1;
            float a0 = table.load_caps[c0], a1 = table.load_caps[c1];
            c_frac = (a1 == a0) ? 0.0f : (load_cap - a0) / (a1 - a0);
        }
    }
}

static bool same_time_axis(const std::vector<ec::CsmWaveform>& wfs) {
    if (wfs.size() <= 1) return true;
    const auto& first = wfs.front().time_points;
    const double reference = wfs.front().reference_time;
    for (size_t i = 1; i < wfs.size(); ++i) {
        if (wfs[i].time_points.size() != first.size()) return false;
        for (size_t j = 0; j < first.size(); ++j) {
            // CCS grids are relative to each corner's input crossing.
            // Comparing absolute samples loses reference offsets, and can
            // select a different interpolation for an equivalent encoding.
            const double relative = double(wfs[i].time_points[j]) - wfs[i].reference_time;
            if (std::fabs(relative - (double(first[j]) - reference)) > 1e-12) return false;
        }
    }
    return true;
}

CsmDelayCalc::Result CsmDelayCalc::gate_delay(
    const ec::CsmOutputCurrentTable& current_table,
    float input_slew,
    float load_cap,
    float vdd,
    const PiModel& pi,
    float r_driver,
    const ec::NldmTable* delay_nldm,
    const ec::NldmTable* slew_nldm,
    float slew_lower,
    float slew_upper,
    float miller_cap) const
{
    Result result{Delay::ZERO(), Slew::ZERO()};
    result.effective_capacitance = load_cap;

    const bool has_nldm_delay = (delay_nldm && !delay_nldm->values.empty());
    const bool has_nldm_slew  = (slew_nldm  && !slew_nldm->values.empty());

    if (current_table.empty() || vdd <= 0.0f) {
        if (has_nldm_delay) result.delay = Delay{std::max(0.0f, delay_nldm->lookup(input_slew, load_cap))};
        if (has_nldm_slew)  result.slew  = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
        return result;
    }

    // DEBUG: force NLDM fallback to compare
    // if (has_nldm_delay) result.delay = Delay{std::max(0.0f, delay_nldm->lookup(input_slew, load_cap))};
    // if (has_nldm_slew)  result.slew  = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
    // return result;

    float alpha = r_driver;
    if (alpha < 0.0f) alpha = 0.0f;

    float clamped_load = load_cap;
    if (!current_table.load_caps.empty()) {
        clamped_load = std::max(clamped_load, current_table.load_caps.front());
    }

    // If the load is outside the CSM table's capacitance range, fall back to
    // NLDM.  Using a clamped CSM waveform for a load far beyond the table max
    // causes severe over-estimation because the waveform current is too small.
    if (!current_table.load_caps.empty() &&
        (clamped_load + miller_cap > current_table.load_caps.back() * 1.05f)) {
        // Falling back from CCS must retain the extracted RC load. A lumped
        // lookup includes all far-end capacitance even when resistance
        // shields it from the driver during the transition.
        if (pi.rpi > 0.0f && has_nldm_delay && has_nldm_slew) {
            PiModel loaded = pi;
            // Match integrate_pi_model: a separately supplied load is on
            // the far side of Rpi; Miller capacitance is at the driver.
            loaded.c1 += std::max(0.0f, load_cap - pi.c1 - pi.c2);
            loaded.c2 += miller_cap;
            const auto fallback = DmpCeffCalc().compute(loaded, input_slew,
                                                       *delay_nldm, *slew_nldm);
            result.delay = Delay{fallback.delay};
            result.slew = Slew{fallback.slew};
            result.effective_capacitance = fallback.ceff;
            return result;
        }
        if (has_nldm_delay) result.delay = Delay{std::max(0.0f, delay_nldm->lookup(input_slew, load_cap))};
        if (has_nldm_slew)  result.slew  = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
        return result;
    }

    float c_total = clamped_load;
    if (c_total + miller_cap <= 0.0f) {
        if (has_nldm_delay) result.delay = Delay{std::max(0.0f, delay_nldm->lookup(input_slew, load_cap))};
        if (has_nldm_slew)  result.slew  = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
        return result;
    }

    bool has_pi = (pi.rpi > 0.0f);
    // Iterate the driving capacitance from charge delivered by the selected
    // waveform up to the driver's 50% crossing.
    float ceff = c_total + miller_cap;
    if (has_pi) ceff = load_cap + miller_cap;
    const int max_iter = 12;
    const float ceff_tol = 1e-6f;

    std::vector<float> time, current, voltage;
    float t50 = 0.0f;
    bool converged = false;

    for (int iter = 0; iter < max_iter; ++iter) {
        float ceff_clamped = ceff;
        if (!current_table.load_caps.empty()) {
            ceff_clamped = std::max(ceff_clamped, current_table.load_caps.front());
        }

        float reference_time = 0.0f;
        select_waveform(current_table, input_slew, ceff_clamped, time, current, reference_time, vdd);
        if (time.empty() || current.empty()) break;

        for (float& t : time) t -= reference_time;

        voltage.clear();
        if (has_pi) {
            float additional_load = load_cap - pi.c1 - pi.c2;
            if (additional_load < 0.0f) additional_load = 0.0f;
            integrate_pi_model(time, current, additional_load, vdd, pi, alpha, miller_cap, voltage);
        } else {
            integrate_lumped_cap_trapezoidal(time, current, c_total, vdd, alpha, miller_cap, voltage);
        }
        if (voltage.empty()) break;

        t50 = !has_pi && alpha<=1e-6f ?
            lumped_current_crossing(time,current,double(c_total)+miller_cap,vdd,.5*vdd) :
            interpolate_crossing(time, voltage, vdd * 0.5f);

        // Compute charge delivered up to t50.
        float Q = 0.0f;
        for (size_t i = 1; i < time.size() && time[i - 1] < t50; ++i) {
            float dt = time[i] - time[i - 1];
            if (dt <= 0.0f) continue;
            float I0 = current[i - 1];
            float I1 = current[i];
            if (alpha > 1e-6f && vdd > 1e-6f) {
                float v0 = (i > 1) ? voltage[i - 1] : ((current[0] < 0.0f) ? vdd : 0.0f);
                float v1 = voltage[i];
                I0 *= std::max(0.0f, 1.0f - alpha * v0 / vdd);
                I1 *= std::max(0.0f, 1.0f - alpha * v1 / vdd);
            }
            const float elapsed=std::min(dt,t50-time[i-1]);
            const float endpoint=I0+(I1-I0)*(elapsed/dt);
            Q += .5f*(I0+endpoint)*elapsed;
        }

        float ceff_new = (vdd > 1e-9f) ? (2.0f * std::fabs(Q) / vdd) : ceff;
        if (ceff_new <= 0.0f) ceff_new = ceff;

        if (std::fabs(ceff_new - ceff) < ceff_tol * ceff) {
            ceff = ceff_new;
            converged = true;
            break;
        }
        ceff = ceff_new;
    }

    if (voltage.empty()) {
        if (has_nldm_delay) result.delay = Delay{std::max(0.0f, delay_nldm->lookup(input_slew, load_cap))};
        if (has_nldm_slew)  result.slew  = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
        return result;
    }

    // Extract delay and slew from final integrated waveform.
    const bool exact_lumped=!has_pi && alpha<=1e-6f;
    auto crossing=[&](float target) {
        return exact_lumped ?
            lumped_current_crossing(time,current,double(c_total)+miller_cap,vdd,target) :
            interpolate_crossing(time,voltage,target);
    };
    t50 = crossing(vdd*.5f);
    result.delay = Delay{t50};
    result.effective_capacitance = ceff;

    float t_lo = crossing(vdd*slew_lower);
    float t_hi = crossing(vdd*slew_upper);
    result.slew = Slew{std::max(0.0f, std::fabs(t_hi - t_lo))};
    result.physical_slew = true;

    // A prescribed CCS current pulse has no voltage feedback. Its driver
    // waveform may plateau on a highly shielded RC load. Use the characterized
    // transition at the converged driving capacitance for such cell arcs;
    // keep direct integration available for CCS-only libraries/experiments.
    if (has_pi && has_nldm_slew &&
        !env_flag_enabled("FSYN_TIMING_CSM_PHYSICAL_SLEW")) {
        result.slew = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, ceff))};
        result.physical_slew = false;
    }

    if (result.slew.value < 1e-9f && has_nldm_slew) {
        result.slew = Slew{std::max(0.0f, slew_nldm->lookup(input_slew, load_cap))};
        result.physical_slew = false;
    }

    return result;
}

// ────────────────────────────────────────────────────────────
// Waveform selection
// ────────────────────────────────────────────────────────────

void CsmDelayCalc::select_waveform(
    const ec::CsmOutputCurrentTable& table,
    float input_slew,
    float load_cap,
    std::vector<float>& out_time,
    std::vector<float>& out_current,
    float& out_reference_time, float vdd) const
{
    out_time.clear();
    out_current.clear();
    out_reference_time = 0.0f;
    if (table.empty()) return;

    size_t s0 = 0, s1 = 0;
    float s_frac = 0.0f;
    if (!table.input_slews.empty()) {
        if (input_slew <= table.input_slews.front()) { s0 = s1 = 0; }
        else if (input_slew >= table.input_slews.back()) { s0 = s1 = table.input_slews.size() - 1; }
        else {
            auto it = std::lower_bound(table.input_slews.begin(), table.input_slews.end(), input_slew);
            s1 = static_cast<size_t>(it - table.input_slews.begin());
            s0 = s1 - 1;
            float a0 = table.input_slews[s0], a1 = table.input_slews[s1];
            s_frac = (a1 == a0) ? 0.0f : (input_slew - a0) / (a1 - a0);
        }
    }

    size_t c0 = 0, c1 = 0;
    float c_frac = 0.0f;
    if (!table.load_caps.empty()) {
        if (load_cap <= table.load_caps.front()) { c0 = c1 = 0; }
        else if (load_cap >= table.load_caps.back()) { c0 = c1 = table.load_caps.size() - 1; }
        else {
            auto it = std::lower_bound(table.load_caps.begin(), table.load_caps.end(), load_cap);
            c1 = static_cast<size_t>(it - table.load_caps.begin());
            c0 = c1 - 1;
            float a0 = table.load_caps[c0], a1 = table.load_caps[c1];
            c_frac = (a1 == a0) ? 0.0f : (load_cap - a0) / (a1 - a0);
        }
    }

    auto get_wf = [&](size_t si, size_t ci) -> const ec::CsmWaveform* {
        size_t idx = si * table.ncap + ci;
        return (idx < table.waveforms.size()) ? &table.waveforms[idx] : nullptr;
    };

    // An exact native lookup must retain its measured signed pulse. The
    // charge-alignment interpolator is only needed between distinct corners;
    // resampling an existing corner can change charge at current reversals.
    const bool native_slew=s0==s1 || s_frac==0.f || s_frac==1.f;
    const bool native_cap=c0==c1 || c_frac==0.f || c_frac==1.f;
    const size_t native_si=s_frac==1.f?s1:s0,native_ci=c_frac==1.f?c1:c0;
    if(native_slew && native_cap && native_si<table.input_slews.size() &&
       native_ci<table.load_caps.size() && input_slew==table.input_slews[native_si] &&
       load_cap==table.load_caps[native_ci]) {
        const auto* wave=get_wf(native_si,native_ci);
        if(!wave) return;
        out_time.reserve(wave->time_points.size());
        for(float t:wave->time_points) out_time.push_back(t-wave->reference_time);
        out_current=wave->current;
        return;
    }

    // Corners have different time axes and load-dependent pulse positions.
    // Interpolating I at the same absolute time can create two separate
    // pulses. Align the complete measured charge support of each corner,
    // interpolate inverse-charge times, and reconstruct dQ/dt. A fixed
    // voltage grid drops finite tails and can miss a narrow turn-on layer
    // next to a zero-current corner, even at an infinitesimal weight.
    if (!same_time_axis(table.waveforms) &&
        !env_flag_enabled("FSYN_TIMING_CSM_INTERPOLATE_TIME")) {
        const size_t si[4]={s0,s1,s0,s1}, ci[4]={c0,c0,c1,c1};
        const double weight[4]={(1.-s_frac)*(1.-c_frac),s_frac*(1.-c_frac),
                                (1.-s_frac)*c_frac,double(s_frac)*c_frac};
        const ec::CsmWaveform* wave[4];
        std::vector<double> charge[4];
        double sign=1.,total_charge=0.,peak_current=0.;
        std::vector<double> grid{0.,1.};
        for(unsigned k=0;k<4;++k) {
            if(weight[k]<=0.) continue;
            wave[k]=get_wf(si[k],ci[k]);
            if(!wave[k] || table.load_caps[ci[k]]<=0.) return;
            const auto& w=*wave[k];
            if(w.current.size()<2 || w.current.size()!=w.time_points.size()) return;
            charge[k].assign(w.current.size(),0.);
            for(size_t j=1;j<w.current.size();++j) {
                const double dt=double(w.time_points[j])-w.time_points[j-1];
                if(dt<=0.) return;
                charge[k][j]=charge[k][j-1]+.5*(std::fabs(double(w.current[j-1]))+
                    std::fabs(double(w.current[j])))*dt;
            }
            if(charge[k].back()<=0.) return;
            total_charge+=weight[k]*charge[k].back()/table.load_caps[ci[k]]*load_cap;
            for(double q:charge[k]) grid.push_back(q/charge[k].back());
            for(float i:w.current) {
                peak_current=std::max(peak_current,std::fabs(double(i))*load_cap/table.load_caps[ci[k]]);
                if(std::fabs(i)>1e-12f) sign=i<0.f?-1.:1.;
            }
        }
        std::sort(grid.begin(),grid.end());
        grid.erase(std::unique(grid.begin(),grid.end()),grid.end());
        struct Sample { double q,t,i; };
        auto evaluate=[&](double q) {
            double t=0.,derivative=0.;
            for(unsigned k=0;k<4;++k) {
                if(weight[k]<=0.) continue;
                const auto& w=*wave[k];
                const double target=q*charge[k].back();
                auto it=std::upper_bound(charge[k].begin(),charge[k].end(),target);
                const size_t hi=std::clamp<size_t>(it-charge[k].begin(),1,charge[k].size()-1),lo=hi-1;
                const double dt=double(w.time_points[hi])-w.time_points[lo];
                const double i0=std::fabs(double(w.current[lo]));
                const double slope=(std::fabs(double(w.current[hi]))-i0)/dt;
                const double dq=std::max(0.,target-charge[k][lo]);
                const double root=std::sqrt(std::max(0.,i0*i0+2.*slope*dq));
                const double elapsed=std::clamp(2.*dq/std::max(i0+root,1e-300),0.,dt);
                const double current=std::max(0.,i0+slope*elapsed);
                t+=weight[k]*(double(w.time_points[lo])+elapsed-w.reference_time);
                derivative+=weight[k]*charge[k].back()/std::max(current,1e-300);
            }
            return Sample{q,t,total_charge/derivative};
        };
        auto append=[&](const Sample& p) {
            const float t=float(p.t),i=float(sign*p.i);
            if(!out_time.empty() && t<=out_time.back()) {
                if(t==out_time.back()) out_current.back()=i;
                return;
            }
            out_time.push_back(t);out_current.push_back(i);
        };
        // The output remains piecewise linear I(t). Bound its charge defect
        // and midpoint current error, retaining every measured charge knot.
        // The tolerances are relative to this pulse, independent of units.
        auto refine=[&](auto&& self,const Sample& a,const Sample& b,unsigned depth)->void {
            const auto m=evaluate(.5*(a.q+b.q));
            const double area=.5*(a.i+b.i)*(b.t-a.t);
            const double expected=total_charge*(b.q-a.q);
            const double linear=b.t>a.t?a.i+(b.i-a.i)*(m.t-a.t)/(b.t-a.t):m.i;
            if(depth<28 && float(m.t)>float(a.t) && float(m.t)<float(b.t) &&
               (std::fabs(area-expected)>1e-8*total_charge ||
                std::fabs(linear-m.i)>1e-4*peak_current)) {
                self(self,a,m,depth+1);self(self,m,b,depth+1);
            } else append(b);
        };
        auto previous=evaluate(grid.front());append(previous);
        for(size_t j=1;j<grid.size();++j) {
            const auto next=evaluate(grid[j]);
            refine(refine,previous,next,0);previous=next;
        }
        return;
    }

    if (same_time_axis(table.waveforms)) {
        const ec::CsmWaveform* wf00 = get_wf(s0, c0);
        if (!wf00) return;
        out_time.clear();
        out_time.reserve(wf00->time_points.size());
        for (float t : wf00->time_points) {
            out_time.push_back(t - wf00->reference_time);
        }
        out_current.resize(out_time.size(), 0.0f);
        const ec::CsmWaveform* wf10 = get_wf(s1, c0);
        const ec::CsmWaveform* wf01 = get_wf(s0, c1);
        const ec::CsmWaveform* wf11 = get_wf(s1, c1);
        for (size_t t = 0; t < out_time.size(); ++t) {
            float i00 = (wf00 && t < wf00->current.size()) ? wf00->current[t] : 0.0f;
            float i10 = (wf10 && t < wf10->current.size()) ? wf10->current[t] : 0.0f;
            float i01 = (wf01 && t < wf01->current.size()) ? wf01->current[t] : 0.0f;
            float i11 = (wf11 && t < wf11->current.size()) ? wf11->current[t] : 0.0f;
            float i0 = i00 + s_frac * (i10 - i00);
            float i1 = i01 + s_frac * (i11 - i01);
            out_current[t] = i0 + c_frac * (i1 - i0);
        }
        out_reference_time = 0.0f;
        return;
    }

    const float interpolate_min_cap =
        env_float_or_default("FSYN_TIMING_CSM_INTERPOLATE_MIN_CAP", 0.0f);
    if (env_flag_enabled("FSYN_TIMING_CSM_INTERPOLATE_WAVEFORM") ||
        interpolate_min_cap <= 0.0f || load_cap >= interpolate_min_cap) {
        const ec::CsmWaveform* wf00 = get_wf(s0, c0);
        const ec::CsmWaveform* wf10 = get_wf(s1, c0);
        const ec::CsmWaveform* wf01 = get_wf(s0, c1);
        const ec::CsmWaveform* wf11 = get_wf(s1, c1);
        if (!wf00 || !wf10 || !wf01 || !wf11) return;

        std::vector<float> grid;
        append_relative_time_grid(wf00, grid);
        append_relative_time_grid(wf10, grid);
        append_relative_time_grid(wf01, grid);
        append_relative_time_grid(wf11, grid);
        if (grid.empty()) return;
        std::sort(grid.begin(), grid.end());
        grid.erase(std::unique(grid.begin(), grid.end(),
                               [](float a, float b) {
                                   return std::fabs(a - b) <= 1.0e-7f;
                               }),
                   grid.end());

        out_time = std::move(grid);
        out_current.resize(out_time.size(), 0.0f);
        for (size_t t = 0; t < out_time.size(); ++t) {
            const float rel_time = out_time[t];
            const float i00 = interpolate_current_at_relative_time(*wf00, rel_time);
            const float i10 = interpolate_current_at_relative_time(*wf10, rel_time);
            const float i01 = interpolate_current_at_relative_time(*wf01, rel_time);
            const float i11 = interpolate_current_at_relative_time(*wf11, rel_time);
            const float i0 = i00 + s_frac * (i10 - i00);
            const float i1 = i01 + s_frac * (i11 - i01);
            out_current[t] = i0 + c_frac * (i1 - i0);
        }
        out_reference_time = 0.0f;
        return;
    }

    size_t si = (s_frac <= 0.5f) ? s0 : s1;
    size_t ci = (c_frac <= 0.5f) ? c0 : c1;
    const ec::CsmWaveform* wf = get_wf(si, ci);
    if (!wf) return;
    out_time.clear();
    out_time.reserve(wf->time_points.size());
    for (float t : wf->time_points) {
        out_time.push_back(t - wf->reference_time);
    }
    out_current = wf->current;
    out_reference_time = 0.0f;
}

// ────────────────────────────────────────────────────────────
// Lumped-capacitance integration (trapezoidal rule)
// ────────────────────────────────────────────────────────────

void CsmDelayCalc::integrate_lumped_cap_trapezoidal(
    const std::vector<float>& time,
    const std::vector<float>& current,
    float cap,
    float vdd,
    float alpha,
    float miller_cap,
    std::vector<float>& voltage) const
{
    voltage.clear();
    if (time.empty() || current.empty() || cap + miller_cap <= 0.0f) return;
    size_t n = std::min(time.size(), current.size());

    voltage.resize(n, 0.0f);

    float v0 = 0.0f;
    for (size_t k = 0; k < current.size(); ++k) {
        if (std::fabs(current[k]) > 1e-12f) {
            if (current[k] < 0.0f) v0 = vdd;
            break;
        }
    }
    voltage[0] = v0;

    for (size_t i = 1; i < n; ++i) {
        float dt = time[i] - time[i - 1];
        if (dt <= 0.0f) {
            voltage[i] = voltage[i - 1];
            continue;
        }

        float v_prev = voltage[i - 1];
        float I_n = current[i];
        float c_eff = cap + miller_cap;

        if (alpha > 1e-6f && vdd > 1e-6f) {
            float denom = 1.0f + dt * I_n * alpha / (c_eff * vdd);
            float v = (v_prev + dt * I_n / c_eff) / denom;
            if (v > vdd) v = vdd;
            if (v < 0.0f) v = 0.0f;
            voltage[i] = v;
        } else {
            float I_prev = (i > 0) ? current[i - 1] : 0.0f;
            float v = v_prev + 0.5f * (I_prev + I_n) * dt / c_eff;
            if (v > vdd) v = vdd;
            if (v < 0.0f) v = 0.0f;
            voltage[i] = v;
        }
    }
}

// ────────────────────────────────────────────────────────────
// Pi-model RC integration (implicit backward Euler)
// ────────────────────────────────────────────────────────────

void CsmDelayCalc::integrate_pi_model(
    const std::vector<float>& time,
    const std::vector<float>& current,
    float load_cap,
    float vdd,
    const PiModel& pi,
    float alpha,
    float miller_cap,
    std::vector<float>& voltage) const
{
    voltage.clear();
    if (time.empty() || current.empty() || pi.rpi <= 0.0f) return;
    size_t n = std::min(time.size(), current.size());

    float c_far = pi.c1 + load_cap;
    float c_drv = pi.c2 + miller_cap;
    if (c_far <= 0.0f && c_drv <= 0.0f) return;

    voltage.resize(n, 0.0f);

    float v0 = 0.0f;
    for (size_t k = 0; k < current.size(); ++k) {
        if (std::fabs(current[k]) > 1e-12f) {
            if (current[k] < 0.0f) v0 = vdd;
            break;
        }
    }

    float vd_prev = v0;
    float vf_prev = v0;

    for (size_t i = 0; i < n; ++i) {
        float dt = (i == 0) ? 0.0f : (time[i] - time[i - 1]);
        if (i == 0 || dt <= 0.0f) {
            voltage[i] = v0;
            continue;
        }

        float I_prev = (i > 0) ? current[i - 1] : 0.0f;
        float I_n = current[i];
        float I_avg = 0.5f * (I_prev + I_n);

        float beta = pi.rpi * c_far * 1e-3f / dt;
        float cdrv_dt = c_drv / dt;
        float cfar_dt = c_far / dt;

        float A = (1.0f + beta) * cdrv_dt + cfar_dt;
        float B = I_avg + cdrv_dt * (beta * vf_prev + vd_prev) + cfar_dt * vf_prev;

        if (alpha > 1e-6f && vdd > 1e-6f) {
            A += (1.0f + beta) * I_avg * alpha / vdd;
            B += I_avg * alpha * beta * vf_prev / vdd;
        }

        float vf = B / A;
        float vd = vf * (1.0f + beta) - beta * vf_prev;

        if (vd > vdd) vd = vdd;
        if (vd < 0.0f) vd = 0.0f;
        if (vf > vdd) vf = vdd;
        if (vf < 0.0f) vf = 0.0f;

        voltage[i] = vd;
        vd_prev = vd;
        vf_prev = vf;
    }
}

// ────────────────────────────────────────────────────────────
// Interpolate crossing time
// ────────────────────────────────────────────────────────────

float CsmDelayCalc::interpolate_crossing(
    const std::vector<float>& time,
    const std::vector<float>& voltage,
    float target) const
{
    if (time.empty() || voltage.empty()) return 0.0f;

    for (size_t i = 1; i < voltage.size(); ++i) {
        float v0 = voltage[i - 1];
        float v1 = voltage[i];
        if ((v0 <= target && target <= v1) || (v1 <= target && target <= v0)) {
            float t0 = time[i - 1];
            float t1 = time[i];
            float frac = (v1 == v0) ? 0.0f : (target - v0) / (v1 - v0);
            return t0 + frac * (t1 - t0);
        }
    }
    float vmin = *std::min_element(voltage.begin(), voltage.end());
    float vmax = *std::max_element(voltage.begin(), voltage.end());
    if (target <= vmin) {
        return (voltage.front() <= voltage.back()) ? time.front() : time.back();
    }
    if (target >= vmax) {
        return (voltage.front() <= voltage.back()) ? time.back() : time.front();
    }
    return time.back();
}

} // namespace te
