#pragma once
#include "sdf.hpp"
#include "gate_compiler.hpp"
#include <istream>
#include <map>
namespace dsim {
struct SdfSignedTicks {bool negative=false;uint64_t magnitude=0;};
struct SdfSelectedValue {
    std::optional<SdfSignedTicks> delay,reject,xlimit;
};
struct SdfBoundCell {bool scope=false;uint32_t id=0;};
struct SdfBoundPin {
    SdfBoundCell owner;
    uint32_t pin=0;
    int net=-1;
    std::string direction;
};
struct SdfBoundEntry {
    // Borrowed syntax survives only for this callback, preserving conditions,
    // edges, mode, labels and the original corner lists without duplication.
    const SdfEntry* syntax=nullptr;
    SdfBoundCell cell;
    std::vector<SdfBoundPin> ports;
    std::vector<SdfSelectedValue> values;
    std::vector<std::vector<SdfSelectedValue>> retain;
    // Units and corner for borrowed raw syntax, including raw numeric mode.
    uint64_t unit_fs=0;
    int corner=1;
    // False means values/retain are deliberately unconverted and empty;
    // it does not mean the syntax contains no values or missing corners.
    bool numeric_preview=true;
};
struct SdfBindOptions {
    int corner=1; // 0 min, 1 typ, 2 max
    uint64_t tick_fs=0; // required only for numeric preview
    std::optional<uint64_t> default_unit_fs;
    // Annotation consumers need the target model's precision for each update;
    // a global-tick preview cannot supply model-specific rounding semantics.
    // Raw mode performs endpoint binding without tick conversion/overflow.
    bool numeric_preview=true;
    // Optional leaf module identities proved by the annotation consumer.
    // Standalone topology binding leaves this empty and remains type-strict.
    // Only INSTANCE * expands aliases; explicit instance checks stay strict.
    std::map<std::string,std::vector<std::string>> wildcard_model_aliases;
};
struct SdfBindStats {
    SdfStats parsed;
    uint64_t target_cells=0,bound_entries=0,interconnects=0,missing_values=0,negative_values=0;
    uint64_t unit_fs=0,tick_fs=0;
    uint64_t topology_instances=0,named_instances=0,hierarchical_scopes=0,name_pool_bytes=0,name_index_bytes=0;
    uint64_t wildcard_alias_targets=0;
    int corner=1;
    bool numeric_preview=true;
    std::string report() const;
};
std::vector<std::string> sdf_path_parts(const std::string&,char divider);
// Streaming endpoint/connectivity binding, not delay annotation. On failure no
// result is returned. Callback consumers must stage effects until success.
SdfBindStats bind_sdf(std::istream&,const std::string& filename,const GateDesign&,const SdfBindOptions&,
                     const std::function<void(const SdfBoundEntry&)>& callback={});
SdfBindStats bind_sdf_file(const std::string& filename,const GateDesign&,const SdfBindOptions&,
                          const std::function<void(const SdfBoundEntry&)>& callback={});
}
