#pragma once
#include "time.hpp"
#include <filesystem>
#include <map>
#include <string>
#include <vector>
namespace dsim {
struct SourceLocation { std::string file; size_t line=1; };
struct Preprocessed {
    std::string text;
    std::vector<SourceLocation> lines;
    std::vector<std::string> dependencies;
    TimingConfig timing;
    std::vector<std::pair<size_t,size_t>> compiler_directives; // byte ranges, blank for AST only
    std::string report() const;
};
struct PreprocessOptions {
    std::vector<std::filesystem::path> include_dirs;
    std::vector<std::pair<std::string,bool>> defines; // value or undefine, in order
    TimeScale default_timescale;
    bool timing_model_source=false; // accept cell-library classification directives only here
    bool gate_source=false; // structural source classification; never invokes the RTL parser
};
// Shared lexical preprocessing. Structural gate files retain their own parser.
Preprocessed preprocess(const std::vector<std::string>& files,const PreprocessOptions& options);
// Expand -f (cwd relative) / -F (filelist relative) before interpreting CLI options.
std::vector<std::string> expand_filelists(const std::vector<std::string>& args,std::vector<std::string>& dependencies);
}
