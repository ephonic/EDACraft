#pragma once
#include "sdf_annotation.hpp"
#include <stdexcept>
namespace dsim {
struct GateTimedArc {
    uint32_t input=0,output=0;
    uint8_t edge=0;
    uint64_t precision_fs=0;
    std::array<uint64_t,12> quanta{};
    uint32_t first=0,condition=0;
    bool ifnone=false;
    std::array<uint64_t,12> ticks(uint64_t global) const {
        if(!global||!precision_fs||precision_fs%global)throw std::runtime_error("invalid module path global precision");
        auto result=quanta;auto scale=precision_fs/global;
        for(auto& q:result){if(q>UINT64_MAX/scale)throw std::runtime_error("module path tick overflow");q*=scale;}
        return result;
    }
};
struct GateTimingData {
    struct Condition {uint32_t model;std::string expression;};
    std::vector<Condition> conditions{{0,""}}; // zero is unconditional
    bool conditional_paths=false;
    struct Check {uint32_t instance,first;TimingCheckSpec spec;uint64_t precision_fs;};
    uint64_t precision_fs=0,annotated_updates=0,disabled_checks=0;
    std::vector<GateTimedArc> arcs;
    std::vector<Check> checks;
    uint64_t check_updates=0;
    uint64_t negative_check_limits_clamped=0;
    std::vector<AnnotatedInterconnect> interconnects;
    uint64_t interconnect_updates=0;
    uint64_t port_updates=0,device_updates=0,port_pins=0;
};
// Actual runtime subset is checked across the entire model library before any
// simulation source is written. Deferred non-check entries are never ignored.
std::shared_ptr<GateTimingData> build_gate_timing(const GateDesign&,const TimingLibrary&,
                                               const SdfPathAnnotation&,bool disable_checks);
}
