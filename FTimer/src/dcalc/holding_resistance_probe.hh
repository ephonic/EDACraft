#pragma once
#include "coupled_rc_solver.hh"

namespace te {
// Explicit diagnostic approximation. Each pass uses a constant secant output
// resistance and the complete reciprocal RC network. This is neither a DC
// transient solution nor an automatic replacement for a dynamic CCSN stage.
// The initial sample and number of evaluations must be supplied by the caller.
class HoldingResistanceProbe {
public:
    using Rc=CoupledRcSolver;
    // An explicitly selected diagnostic hypothesis, not a vendor CCSN rule.
    enum class RecoveryMode { constant_resistance, first_secant_after_peak };
    struct Evaluation { double sample_displacement_v, conductance_ma_per_v, peak_v; };
    struct Result {
        Rc::Result waveform;
        std::vector<Evaluation> evaluations;
        Rc::Result baseline; // same conductance, sources held at their begin voltages
        bool recovery_applied=false;
        double recovery_time_ns=std::numeric_limits<double>::quiet_NaN();
    };
    // Keep the original source event grid, but freeze its *forcing voltage*
    // at the observation window's start. Driver::initial is the pre-ramp
    // voltage; it need not be the source value at begin (or the node voltage
    // behind a finite source resistance).
    static std::vector<Rc::Driver> hold_sources_at(
        const std::vector<Rc::Driver>& drivers,double begin) {
        if(!std::isfinite(begin))throw std::runtime_error("Invalid quiet source reference time");
        auto quiet=drivers;
        for(auto& d:quiet) {
            if(!std::isfinite(d.initial) || !std::isfinite(d.final) ||
                !std::isfinite(d.center) || !std::isfinite(d.ramp) || d.ramp<0)
                throw std::runtime_error("Invalid quiet source waveform");
            const double f=d.ramp>0?std::clamp((begin-d.center)/d.ramp+.5,0.,1.):(begin>d.center?1.:0.);
            const double value=d.initial+(d.final-d.initial)*f;
            d.initial=d.final=value;
        }
        return quiet;
    }
    static Result solve(size_t n,const std::vector<Rc::Resistor>& resistors,
        const std::vector<Rc::Capacitor>& capacitors,const std::vector<Rc::Driver>& drivers,
        const Rc::StaticDriver& iv,const std::vector<double>& initial,size_t observation,
        double direction,double first_sample_v,size_t evaluations,
        double begin,double end,double max_dt,size_t max_steps=100000,
        RecoveryMode recovery=RecoveryMode::constant_resistance) {
        if(iv.node>=n || observation>=n || initial.size()!=n ||
            (direction!=1. && direction!=-1.) || !std::isfinite(first_sample_v) ||
            !(first_sample_v>0) || !evaluations || evaluations>16 ||
            iv.voltage.size()<2 || iv.voltage.size()!=iv.current_ma.size() ||
            !iv.output_charge_pc.empty() ||
            (recovery!=RecoveryMode::constant_resistance &&
             recovery!=RecoveryMode::first_secant_after_peak))
            throw std::runtime_error("Invalid explicit holding resistance probe");
        for(size_t k=0;k<iv.voltage.size();++k)
            if(!std::isfinite(iv.voltage[k]) || !std::isfinite(iv.current_ma[k]) ||
                (k && (!(iv.voltage[k]>iv.voltage[k-1]) || iv.current_ma[k]>iv.current_ma[k-1])))
                throw std::runtime_error("Holding resistance probe requires passive ordered I-V");
        for(const auto& d:drivers)if(d.node==iv.node)
            throw std::runtime_error("Holding resistance probe overlaps an explicit driver");
        auto current=[&](double v) {
            if(!std::isfinite(v) || v<iv.voltage.front() || v>iv.voltage.back())
                throw std::runtime_error("Holding resistance sample outside characterized domain");
            size_t k=std::upper_bound(iv.voltage.begin(),iv.voltage.end(),v)-iv.voltage.begin();
            k=std::min(std::max(k,size_t(1)),iv.voltage.size()-1)-1;
            return iv.current_ma[k]+(iv.current_ma[k+1]-iv.current_ma[k])*
                (v-iv.voltage[k])/(iv.voltage[k+1]-iv.voltage[k]);
        };
        const double reference=initial[iv.node],baseline=current(reference);
        double sample=first_sample_v;Result result;
        for(size_t pass=0;pass<evaluations;++pass) {
            const double g=-(current(reference+direction*sample)-baseline)/(direction*sample);
            if(!std::isfinite(g) || !(g>0))
                throw std::runtime_error("Holding resistance probe requires positive restoring conductance");
            auto boundary=drivers;
            boundary.push_back({iv.node,1000./g,reference,reference,begin,0.});
            auto wave=Rc::solve(n,resistors,capacitors,boundary,initial,begin,end,max_dt,max_steps);
            auto quiet=hold_sources_at(boundary,begin);
            auto baseline_wave=Rc::solve(n,resistors,capacitors,quiet,initial,begin,end,max_dt,max_steps);
            if(wave.time!=baseline_wave.time)
                throw std::runtime_error("Holding resistance quiet/active grids differ");
            double peak=0.;
            for(size_t k=0;k<wave.time.size();++k)
                peak=std::max(peak,direction*(wave.voltage[k][observation]-baseline_wave.voltage[k][observation]));
            if(!std::isfinite(peak) || !(peak>0))
                throw std::runtime_error("Holding resistance probe has no positive noise response");
            result.evaluations.push_back({sample,g,peak});
            result.waveform=std::move(wave);result.baseline=std::move(baseline_wave);sample=peak;
        }
        if(recovery==RecoveryMode::first_secant_after_peak) {
            const double first_g=result.evaluations.front().conductance_ma_per_v;
            const double last_g=result.evaluations.back().conductance_ma_per_v;
            // Preserve a linear table's response, including its original grid.
            if(std::abs(first_g-last_g)>32*std::numeric_limits<double>::epsilon()*std::max(first_g,last_g)) {
                size_t peak_index=0;double peak=0.;
                for(size_t k=0;k<result.waveform.time.size();++k) {
                    const double v=direction*(result.waveform.voltage[k][observation]-result.baseline.voltage[k][observation]);
                    if(v>peak) {peak=v;peak_index=k;}
                }
                const double time=result.waveform.time[peak_index];
                if(time>begin && time<end) {
                    auto boundary=drivers;
                    boundary.push_back({iv.node,1000./first_g,reference,reference,begin,0.});
                    // Carry every RC state on each side of the paired experiment.
                    auto tail=Rc::solve(n,resistors,capacitors,boundary,result.waveform.voltage[peak_index],time,end,max_dt,max_steps);
                    // The quiet forcing is frozen at the ORIGINAL window start,
                    // even when the switch occurs during another source's ramp.
                    auto quiet=hold_sources_at(boundary,begin);
                    auto quiet_tail=Rc::solve(n,resistors,capacitors,quiet,result.baseline.voltage[peak_index],time,end,max_dt,max_steps);
                    if(tail.time!=quiet_tail.time)
                        throw std::runtime_error("Holding recovery quiet/active grids differ");
                    auto append=[&](Rc::Result& wave,const Rc::Result& rest) {
                        wave.time.resize(peak_index);wave.voltage.resize(peak_index);
                        wave.time.insert(wave.time.end(),rest.time.begin(),rest.time.end());
                        wave.voltage.insert(wave.voltage.end(),rest.voltage.begin(),rest.voltage.end());
                    };
                    append(result.waveform,tail);append(result.baseline,quiet_tail);
                    result.recovery_applied=true;result.recovery_time_ns=time;
                }
            }
        }
        return result;
    }
};
} // namespace te
