#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <iosfwd>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace dsim {
// A decimal stays decimal until annotation. No binary floating point rounding
// is introduced by parsing; missing corners are distinct from zero.
struct SdfTriple {
    std::array<std::optional<std::string>,3> corner;
    bool scalar=false;
};
struct SdfPort {
    std::string name,edge,condition,label;
};
struct SdfDelayValue {
    SdfTriple delay;
    std::optional<SdfTriple> reject,xlimit;
};
struct SdfEntry {
    enum class Mode { Absolute, Increment, TimingCheck } mode=Mode::Absolute;
    std::string kind,condition,label;
    bool conditional_else=false;
    std::vector<SdfPort> ports;
    std::vector<SdfDelayValue> values;
    std::vector<std::vector<SdfDelayValue>> retain;
    size_t line=0;
};
struct SdfCell { std::string type,instance; size_t line=0; };
struct SdfHeader {
    std::map<std::string,std::string> fields;
    char divider='.';
    std::optional<uint64_t> timescale_fs;
};
struct SdfStats {
    uint64_t cells=0,entries=0,conditional=0,incremental=0,retains=0;
    std::map<std::string,uint64_t> kinds;
    SdfHeader header;
    std::string report() const;
};
struct SdfCallbacks {
    std::function<void(const SdfHeader&)> header;
    std::function<void(const SdfCell&)> cell;
    std::function<void(const SdfCell&,const SdfEntry&)> entry;
};
// Sequential input; retains only the current entry, not a whole file or CELL.
// Syntax outside this supported subset is rejected, never silently skipped.
SdfStats parse_sdf(std::istream&,const std::string& filename,const SdfCallbacks& = {});
SdfStats read_sdf(const std::string& filename,const SdfCallbacks& = {});
// Exact decimal -> integral tick conversion, round half up. Negative values
// are rejected here; INCREMENT/timing-check consumers must handle signed data.
uint64_t sdf_ticks(const std::string& decimal,uint64_t scale_fs,uint64_t tick_fs);
}
