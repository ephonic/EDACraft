#pragma once
#include "preprocessor.hpp"
#include <map>
namespace dsim {
struct GateModuleTime {std::string name; size_t line; TimeScale scale;};
// Owns preprocessed structural text until the independent network parser takes
// it. Ordinary directive-only netlists need no per-token or per-line storage.
struct GateSource {
    std::string file,text;
    size_t bytes=0;
    bool fast_path=false;
    double seconds=0;
    std::vector<std::string> dependencies;
    std::vector<SourceLocation> lines; // populated only for macro/include expansion
    std::vector<GateModuleTime> modules;
    std::map<std::string,TimeScale> module_times;
    SourceLocation location(size_t line) const;
    TimeScale time(const std::string& module) const;
    std::string report() const;
};
GateSource prepare_gate_source(const std::string& file,const PreprocessOptions& options={});
}
