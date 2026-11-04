#pragma once
#include "preprocessor.hpp"
#include "sdf_delay.hpp"
#include <map>

namespace dsim {
// Specify metadata is separate from structural netlist parsing and functional
// Liberty lowering. Functional Verilog bodies are NOT compiled by this reader.
struct TimingPath {
    std::vector<std::string> inputs,outputs;
    std::string edge,polarity,output_polarity,data,condition;
    bool full=false,ifnone=false;
    std::vector<std::string> delays; // unevaluated constant expressions, declaration order
    SourceLocation source;
};
struct TimingCheckDeclaration {
    std::string kind;
    std::vector<std::string> arguments; // event conditions/notifier included
    SourceLocation source;
};
struct TimingEvent {
    std::string pin,condition;
    uint16_t transitions=1023;
};
struct TimingCheckSpec {
    // Canonical event order: data/asynchronous control, reference clock.
    enum Kind : uint8_t { Setup,Hold,Recovery,Removal,SetupHold,RecRem,Width,Period,Skew };
    Kind kind=Setup;
    std::array<TimingEvent,2> events;
    std::array<uint64_t,2> limits{};
    uint64_t threshold=0;
    uint32_t declaration=0;
    uint32_t negative_limits_clamped=0;
};
struct TimingModel {
    std::string name;
    TimeScale time;
    std::map<std::string,std::string> ports; // scalar pin -> input/output/inout
    std::map<std::string,std::string> constants;
    std::map<std::string,std::string> aliases; // simple continuous assignments; resolved only when a condition uses them
    std::vector<TimingPath> paths;
    std::vector<TimingCheckDeclaration> checks;
    std::vector<std::string> pulse_declarations;
    SourceLocation source;
    // Byte ranges in the preprocessed source, for explicit model preparation.
    // Functional bodies remain opaque and are copied without token rewriting.
    size_t module_end=0;
    std::vector<std::pair<size_t,size_t>> specify_ranges;
    // Exact token identity after preprocessing, excluding only the module
    // name, comments and whitespace; includes the time unit/precision.
    // This does not assert Boolean or general elaboration equivalence.
    std::string definition_key;
    // Resolves decimal literals, unary signs, parentheses, corner triples and
    // specparam references. Unsupported arithmetic fails rather than rounding
    // intermediate terms or inventing a default delay.
    std::vector<std::string> initial(const TimingPath&,int corner) const;
    std::vector<TimingCheckSpec> executable_checks(int corner) const;
    std::string resolve_condition(const std::string&) const;
};
struct TimingLibrary {
    std::vector<TimingModel> models;
    std::vector<std::string> dependencies;
    const TimingModel& model(const std::string&) const;
    std::string report() const;
};
TimingLibrary parse_timing_models(const Preprocessed&);
TimingLibrary read_timing_models(const std::vector<std::string>&,const PreprocessOptions& = {});
// Lexical canonicalization only. No Boolean simplification (especially X/Z).
std::string timing_expression_key(const std::string&);
TimingEvent timing_event(const std::string&);
uint16_t timing_edge_mask(const std::string&);
std::string timing_condition_code(const std::string&,const std::function<std::string(const std::string&)>&);
}
