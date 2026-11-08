#pragma once
#include "dcalc/coupled_rc_solver.hh"
#include "liberty/logic_expression.hh"
#include "edacraft/core/liberty_db.hpp"
#include <cstdlib>
#include <cctype>
#include <string>

namespace te {
// Typed consumption of retained CCSN AST. Selection is for a fixed Boolean
// state; it does not assume that an unknown condition is an unconditional case.
class CcsnStageBuilder {
public:
    using Node=edacraft::core::LibertyCcsnNode;
    using Lookup=std::function<std::optional<int>(std::string_view)>;
    struct Selection { const Node* stage=nullptr;std::vector<size_t> equivalent_indices;bool disabled=false; };
    struct Waveform {
        std::string kind;
        double input_transition_ns=0., noise_height_v=0., noise_width_ns=0., load_pf=0.;
        std::vector<double> time_ns, output_v;
    };
    struct Model {
        CoupledRcSolver::DynamicStage table;
        std::string stage_type;
        bool inverting=false;
        std::vector<Waveform> waveforms; // characterization observations, not reconstructed current laws
    };
    static const Node* child(const Node& n,std::string_view name) {
        const Node* out=nullptr;
        for(const auto& c:n.children)if(c.name==name) {
            if(out)throw std::runtime_error("Duplicate CCSN field");out=&c;
        }
        return out;
    }
    static std::string text(const Node& n,std::string_view name,std::string fallback="") {
        const auto* c=child(n,name);if(!c)return fallback;
        if(c->arguments.size()!=1)throw std::runtime_error("Invalid CCSN scalar field");
        return c->arguments.front().text;
    }
    static bool boolean(const Node& n,std::string_view name,bool fallback) {
        const auto s=text(n,name,fallback?"true":"false");
        if(s!="true" && s!="false")throw std::runtime_error("Invalid CCSN Boolean attribute");
        return s=="true";
    }
    static bool same(const Node& a,const Node& b,bool ignore_condition=false) {
        if(a.name!=b.name || a.kind!=b.kind || a.arguments.size()!=b.arguments.size())return false;
        for(size_t i=0;i<a.arguments.size();++i)
            if(a.arguments[i].text!=b.arguments[i].text || a.arguments[i].quoted!=b.arguments[i].quoted)return false;
        std::vector<const Node*> x,y;
        for(const auto& c:a.children)if(!ignore_condition || c.name!="when")x.push_back(&c);
        for(const auto& c:b.children)if(!ignore_condition || c.name!="when")y.push_back(&c);
        if(x.size()!=y.size())return false;
        for(size_t i=0;i<x.size();++i)if(!same(*x[i],*y[i]))return false;
        return true;
    }
    static Selection select(const std::vector<Node>& nodes,std::string_view stage_name,
        std::string_view owner_when,const Lookup& lookup) {
        auto enabled=[&](std::string_view condition) {
            if(condition.empty())return true;
            const auto z=evaluate_liberty_boolean(condition,lookup);
            if(!z)throw std::runtime_error("CCSN condition is invalid or needs an explicit input state");
            return *z;
        };
        if(!enabled(owner_when))return {};
        std::vector<size_t> conditional,fallback;
        for(size_t i=0;i<nodes.size();++i)if(nodes[i].name==stage_name) {
            const auto condition=text(nodes[i],"when");
            if(condition.empty())fallback.push_back(i);
            else if(enabled(condition))conditional.push_back(i);
        }
        const auto& matches=conditional.empty()?fallback:conditional;
        Selection out;
        for(size_t i:matches) {
            if(out.stage && !same(*out.stage,nodes[i],true))
                throw std::runtime_error("Ambiguous active CCSN stages with different models");
            if(!out.stage)out.stage=&nodes[i];out.equivalent_indices.push_back(i);
        }
        out.disabled=out.stage && !boolean(*out.stage,"is_needed",true);
        return out;
    }
    static std::vector<double> numbers(const Node& n) {
        std::vector<double> out;
        for(const auto& a:n.arguments) {
            const char* p=a.text.c_str();
            while(*p) {
                while(*p && (std::isspace(static_cast<unsigned char>(*p)) || *p==','))++p;
                if(!*p)break;
                char* end=nullptr;const double x=std::strtod(p,&end);
                if(end==p || !std::isfinite(x) || (*end && *end!=',' && !std::isspace(static_cast<unsigned char>(*end))))
                    throw std::runtime_error("Invalid CCSN numeric vector");
                out.push_back(x);p=end;
                if(out.size()>8000000)throw std::runtime_error("CCSN numeric vector budget exceeded");
            }
        }
        return out;
    }
    static Model build(const Node& stage,const std::vector<Node>& templates,
        const edacraft::core::LibertyLibrary::Units& units,bool output_rise) {
        if(!boolean(stage,"is_needed",true))throw std::runtime_error("Disabled CCSN stage has no active circuit");
        if(!child(stage,"is_inverting"))throw std::runtime_error("Active CCSN stage requires is_inverting");
        if(boolean(stage,"is_pass_gate",false))throw std::runtime_error("CCSN pass-gate circuit reconstruction is unsupported");
        for(const char* field:{"mode","input_signal_level","output_signal_level"})
            if(child(stage,field))throw std::runtime_error("Unresolved CCSN mode or voltage-domain reference");
        const auto* dc=child(stage,"dc_current");
        if(!dc || dc->arguments.size()!=1)throw std::runtime_error("CCSN stage lacks a DC table/template");
        const Node* model_template=nullptr;
        for(const auto& t:templates)if(t.arguments.size()==1 && t.arguments[0].text==dc->arguments[0].text) {
            if(model_template)throw std::runtime_error("Ambiguous CCSN DC template");model_template=&t;
        }
        if(!model_template)throw std::runtime_error("CCSN DC template missing");
        const auto first=text(*model_template,"variable_1"),second=text(*model_template,"variable_2");
        const bool transpose=first=="output_voltage" && second=="input_voltage";
        if(!transpose && !(first=="input_voltage" && second=="output_voltage"))
            throw std::runtime_error("Unsupported CCSN DC template axes");
        auto axis=[&](const char* name) {
            const auto* n=child(*dc,name);if(!n)n=child(*model_template,name);
            if(!n)throw std::runtime_error("CCSN DC voltage axis missing");
            auto out=numbers(*n);if(out.size()<2)throw std::runtime_error("CCSN DC axis too small");
            for(size_t k=0;k<out.size();++k) {
                out[k]*=units.voltage_unit_volts;
                if(!std::isfinite(out[k]) || (k && !(out[k]>out[k-1])))
                    throw std::runtime_error("CCSN DC axis must be ordered");
            }
            return out;
        };
        auto a=axis("index_1"),b=axis("index_2");
        const auto* values=child(*dc,"values");if(!values)throw std::runtime_error("CCSN DC values missing");
        auto data=numbers(*values);
        if(a.size()>8000000/b.size() || data.size()!=a.size()*b.size() ||
            !std::isfinite(units.current) || !(units.current>0) ||
            !std::isfinite(units.capacitance_unit_farads) || !(units.capacitance_unit_farads>0) ||
            !std::isfinite(units.voltage_unit_volts) || !(units.voltage_unit_volts>0))
            throw std::runtime_error("Invalid CCSN DC dimensions/units");
        Model out;out.table.node=0;out.stage_type=text(stage,"stage_type");out.inverting=boolean(stage,"is_inverting",false);
        // Liberty stage_type describes pull direction, NOT first/last CCB topology.
        if(out.stage_type!="both" && out.stage_type!="pull_up" && out.stage_type!="pull_down")
            throw std::runtime_error("CCSN stage_type must be pull_up, pull_down or both");
        out.table.input_voltage=transpose?b:a;out.table.output_voltage=transpose?a:b;
        for(size_t i=0;i<out.table.input_voltage.size();++i)
            for(size_t j=0;j<out.table.output_voltage.size();++j) {
                const double value=data[transpose?j*b.size()+i:i*b.size()+j]*units.current;
                if(!std::isfinite(value))throw std::runtime_error("CCSN current unit overflow");
                out.table.current_ma.push_back(value);
            }
        const auto* miller=child(stage,output_rise?"miller_cap_rise":"miller_cap_fall");
        if(!miller)throw std::runtime_error("CCSN selected-polarity Miller capacitance missing");
        auto caps=numbers(*miller);
        if(caps.size()!=1 || caps[0]<0)throw std::runtime_error("Invalid CCSN Miller capacitance");
        out.table.miller_pf=caps[0]*units.capacitance_unit_farads/1e-12;
        if(!std::isfinite(out.table.miller_pf))throw std::runtime_error("CCSN capacitance unit overflow");
        const double ns=units.time_unit_seconds/1e-9,pf=units.capacitance_unit_farads/1e-12;
        if(!std::isfinite(ns) || !(ns>0))throw std::runtime_error("Invalid CCSN time unit");
        size_t samples=0;
        for(const char* kind:{"output_voltage_rise","output_voltage_fall","propagated_noise_high","propagated_noise_low"}) {
            const auto* group=child(stage,kind);if(!group)continue;
            const bool noise=std::string_view(kind).substr(0,10)=="propagated";
            const size_t dimensions=noise?4:3;
            for(const auto& vector:group->children) {
                if(vector.name!="vector" || vector.arguments.size()!=1)
                    throw std::runtime_error("Invalid CCSN characterization vector");
                const Node* layout=nullptr;
                for(const auto& t:templates)if(t.arguments.size()==1 && t.arguments[0].text==vector.arguments[0].text) {
                    if(layout)throw std::runtime_error("Ambiguous CCSN waveform template");layout=&t;
                }
                if(!layout)throw std::runtime_error("CCSN waveform template missing");
                Waveform w;w.kind=kind;bool time=false,load=false,transition=false,height=false,width=false;
                for(size_t k=1;k<=dimensions;++k) {
                    const auto variable="variable_"+std::to_string(k),index="index_"+std::to_string(k);
                    const auto axis_name=text(*layout,variable);const auto* axis=child(vector,index);
                    if(!axis)axis=child(*layout,index);
                    if(!axis)throw std::runtime_error("CCSN waveform axis missing");
                    auto values=numbers(*axis);
                    if(axis_name=="time" && !time) {
                        time=true;w.time_ns=std::move(values);
                        for(double& v:w.time_ns)v*=ns;
                    } else {
                        if(values.size()!=1 || values[0]<0)throw std::runtime_error("Invalid CCSN waveform scalar coordinate");
                        if(axis_name=="total_output_net_capacitance" && !load) {load=true;w.load_pf=values[0]*pf;}
                        else if(!noise && axis_name=="input_net_transition" && !transition) {transition=true;w.input_transition_ns=values[0]*ns;}
                        else if(noise && axis_name=="input_noise_height" && !height) {height=true;w.noise_height_v=values[0]*units.voltage_unit_volts;}
                        else if(noise && axis_name=="input_noise_width" && !width) {width=true;w.noise_width_ns=values[0]*ns;}
                        else throw std::runtime_error("Unexpected/duplicate CCSN waveform template axis");
                    }
                }
                if(child(*layout,"variable_"+std::to_string(dimensions+1)))
                    throw std::runtime_error("Extra CCSN waveform template axis");
                const auto* v=child(vector,"values");if(!v)throw std::runtime_error("CCSN waveform samples missing");
                w.output_v=numbers(*v);for(double& x:w.output_v)x*=units.voltage_unit_volts;
                if(!time || !load || (noise?!(height && width):!transition) || w.time_ns.size()<2 ||
                    w.time_ns.size()!=w.output_v.size() || w.time_ns.size()>8000000-samples ||
                    !std::isfinite(w.load_pf) || !std::isfinite(w.input_transition_ns) ||
                    !std::isfinite(w.noise_height_v) || !std::isfinite(w.noise_width_ns))
                    throw std::runtime_error("Invalid CCSN waveform dimensions/units");
                for(size_t k=0;k<w.time_ns.size();++k)
                    if(!std::isfinite(w.time_ns[k]) || !std::isfinite(w.output_v[k]) ||
                        (k && !(w.time_ns[k]>w.time_ns[k-1])))throw std::runtime_error("Invalid CCSN waveform time/voltage");
                samples+=w.time_ns.size();out.waveforms.push_back(std::move(w));
            }
        }
        return out;
    }
};
} // namespace te
