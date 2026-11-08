#pragma once
#include "holding_resistance_probe.hh"

namespace te {
// Caller-selected quiet-stage policy. The threshold and uncertainty band are
// explicit parameters, never vendor-specific runtime defaults.
class QuietNoiseProbe {
public:
    using Rc=CoupledRcSolver;
    enum class Selection { resistance, physical, indeterminate };
    struct Metric { double peak_v=0., area_vns=0., width_ns=0.; };
    struct Result {
        HoldingResistanceProbe::Result resistance;
        Rc::Result physical, baseline;
        Metric resistance_noise, physical_noise;
        Selection selection=Selection::indeterminate;
        const Rc::Result& selected_waveform() const {
            if(selection==Selection::indeterminate)
                throw std::runtime_error("Quiet noise selection lies within uncertainty band");
            return selection==Selection::resistance?resistance.waveform:physical;
        }
    };
    static Selection select(double peak,double threshold,double uncertainty) {
        if(!std::isfinite(peak) || peak<0 || !std::isfinite(threshold) ||
            !std::isfinite(uncertainty) || uncertainty<0 || !(threshold>uncertainty))
            throw std::runtime_error("Invalid explicit quiet noise selection policy");
        // Subtraction followed by abs can round an endpoint outside its own
        // inclusive band. Compare directly against representable endpoints.
        if(peak>=threshold-uncertainty && peak<=threshold+uncertainty)
            return Selection::indeterminate;
        return peak<threshold?Selection::resistance:Selection::physical;
    }
    static Metric measure(const Rc::Result& wave,const Rc::Result* baseline,
        size_t observation,double reference,double direction) {
        if(wave.time.size()<2 || wave.voltage.size()!=wave.time.size() ||
            (direction!=1. && direction!=-1.) || !std::isfinite(reference) ||
            (baseline && (baseline->time!=wave.time || baseline->voltage.size()!=wave.time.size())))
            throw std::runtime_error("Invalid quiet noise measurement grid");
        Metric m;double previous=0.;
        for(size_t k=0;k<wave.time.size();++k) {
            if(observation>=wave.voltage[k].size() ||
                (baseline && observation>=baseline->voltage[k].size()))
                throw std::runtime_error("Invalid quiet noise observation node");
            const double value=direction*(wave.voltage[k][observation]-
                (baseline?baseline->voltage[k][observation]:reference));
            if(!std::isfinite(value) || !std::isfinite(wave.time[k]) ||
                (k && !(wave.time[k]>wave.time[k-1])))
                throw std::runtime_error("Invalid quiet noise measurement sample");
            m.peak_v=std::max(m.peak_v,value);
            if(k) {
                const double dt=wave.time[k]-wave.time[k-1];
                if(previous>=0 && value>=0)m.area_vns+=.5*dt*(previous+value);
                else if(previous*value<0) {
                    const double positive=std::max(previous,value);
                    m.area_vns+=.5*dt*positive*positive/std::abs(value-previous);
                }
            }
            previous=value;
        }
        if(m.peak_v>0)m.width_ns=2*m.area_vns/m.peak_v;
        return m;
    }
    static Result solve(size_t n,const std::vector<Rc::Resistor>& resistors,
        const std::vector<Rc::Capacitor>& capacitors,const std::vector<Rc::Driver>& drivers,
        const Rc::DynamicStage& stage,const std::vector<double>& initial,size_t observation,
        double direction,double first_sample_v,size_t evaluations,
        double threshold_v,double uncertainty_v,double begin,double end,double max_dt,
        size_t max_steps=100000) {
        select(0.,threshold_v,uncertainty_v);
        if(stage.node>=n || observation>=n || initial.size()!=n ||
            stage.time.size()<2 || stage.time.size()!=stage.input_v.size() || stage.lag_output_feedback)
            throw std::runtime_error("Quiet noise probe requires an explicit fixed-input stage");
        for(double v:stage.input_v)if(v!=stage.input_v.front())
            throw std::runtime_error("Quiet noise probe does not select dynamic-input models");
        Rc::StaticDriver iv{stage.node,stage.output_voltage,
            Rc::stage_slice(stage,stage.input_v.front()),{}};
        Result result;
        result.resistance=HoldingResistanceProbe::solve(n,resistors,capacitors,drivers,
            iv,initial,observation,direction,first_sample_v,evaluations,begin,end,max_dt,max_steps);
        result.resistance_noise=measure(result.resistance.waveform,&result.resistance.baseline,
            observation,initial[observation],direction);
        result.selection=select(result.resistance_noise.peak_v,threshold_v,uncertainty_v);
        auto quiet=HoldingResistanceProbe::hold_sources_at(drivers,begin);
        result.baseline=Rc::solve(n,resistors,capacitors,quiet,initial,begin,end,max_dt,max_steps,nullptr,{},&stage);
        result.physical=Rc::solve(n,resistors,capacitors,drivers,initial,begin,end,max_dt,max_steps,nullptr,{},&stage);
        result.physical_noise=measure(result.physical,&result.baseline,observation,initial[observation],direction);
        return result;
    }
};
} // namespace te
