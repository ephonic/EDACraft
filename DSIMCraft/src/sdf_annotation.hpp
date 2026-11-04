#pragma once
#include "sdf_binding.hpp"
#include "timing_model.hpp"

namespace dsim {
struct AnnotatedPath {
    uint32_t instance=0,model=0,path=0;
    uint32_t input=0,output=0; // terminal indices within a full path declaration
    SdfPathDelays delays;
    // Origin matters for subsequent ABSOLUTE readback. Repeated updates of
    // one family replace; a path touched by both families uses MAXIMUM.
    bool iopath_updated=false,device_updated=false;
    AnnotatedPath(uint32_t i,uint32_t m,uint32_t p,uint32_t a,uint32_t z,SdfPathDelays d):instance(i),model(m),path(p),input(a),output(z),delays(std::move(d)) {}
};
struct AnnotatedInterconnect {
    uint32_t instance=0,pin=0; // pin is the flattened functional pin index
    uint64_t precision_fs=0;
    std::array<uint64_t,3> quanta{}; // receiver rise, fall, turnoff
    bool interconnect=false,port=false;
};
struct SdfPathAnnotation {
    SdfBindStats binding;
    int model_corner=1;
    std::vector<AnnotatedPath> paths;
    std::vector<AnnotatedInterconnect> interconnects;
    uint64_t interconnect_updates=0;
    uint64_t port_updates=0,device_updates=0;
    // Input delays share one physical MIPD per receiving pin, including PORT.
    uint64_t port_pins=0;
    uint64_t path_updates=0,clamped_transition_slots=0;
    std::map<uint32_t,std::vector<TimingCheckSpec>> checks;
    uint64_t check_updates=0;
    uint64_t negative_check_limits_clamped=0;
    // These entries are endpoint-bound only. They are never called annotated
    // or silently converted into zero delay paths or path timing checks.
    std::map<std::string,uint64_t> deferred_entries;
    std::string report(const TimingLibrary&,uint64_t global_tick_fs) const;
};
// Builds model IOPATH tables and optional receiving-pin/check tables.
// Entire result is staged: parse, endpoint,
// identity and numeric failures return no partially annotated database.
// Conditional/edge identity is preserved, not evaluated by this layer.
SdfPathAnnotation annotate_sdf_paths(const std::string& file,const GateDesign&,
                                   const TimingLibrary&,SdfBindOptions,int model_corner=1,
                                   bool annotate_interconnect=false,bool annotate_checks=false);
}
