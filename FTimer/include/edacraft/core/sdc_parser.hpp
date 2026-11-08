#ifndef EDACRAFT_CORE_SDC_PARSER_HPP
#define EDACRAFT_CORE_SDC_PARSER_HPP

#include "edacraft/core/constraint_db.hpp"
#include <string>
#include <vector>

namespace edacraft::core {

// Unified SDC parser that populates ConstraintDB directly.
// Covers: create_clock, set_input_delay, set_output_delay, set_max_delay,
//         set_min_delay, set_load, set_input_transition, set_clock_groups,
//         set_clock_latency, set_driving_cell,
//         set_clock_waveform, set_clock_uncertainty, set_multicycle_path,
//         set_false_path, set_disable_timing, set_case_analysis,
//         set_timing_derate, set_max_fanout, set_max_capacitance,
//         set_max_transition, set_clock_transition, set_data_check,
//         group_path, set_units.
class SdcParser {
public:
    SdcParser() = default;

    bool parse_file(const std::string& filepath, ConstraintDB& constraints);
    bool parse_string(const std::string& content, ConstraintDB& constraints);

    // Resolve bounded whole-word $variables and immutable topology aliases.
    // This is a static subset of Tcl; definitions are consumed in source order.
    // Call before network collection materialization, then parse the result.
    bool resolve_static_variables(const std::string& content, std::string& resolved);

    const std::string& last_error() const { return last_error_; }
    // Non-fatal diagnostics for commands accepted by the Tcl front-end but
    // not represented in ConstraintDB.  Keeping these separate from
    // last_error() lets a flow run while still exposing incomplete coverage.
    const std::vector<std::string>& warnings() const { return warnings_; }

private:
    std::string last_error_;
    std::vector<std::string> warnings_;
    // ConstraintDB stores time in ns and capacitance in pF, independent of
    // the units declared by the SDC source.
    float time_scale_ns_ = 1.0f;
    float capacitance_scale_pf_ = 1.0f;

    bool parse_time_number(const std::string& token, float& value) const;
    bool parse_capacitance_number(const std::string& token, float& value) const;

    struct Tokens {
        std::vector<std::string> words;
        size_t pos = 0;

        std::string peek() const;
        std::string next();
        bool has_more() const;
    };

    Tokens tokenize(const std::string& line);
    std::string expand_bracket_expr(const std::string& s);
    void parse_path_selector(const std::string& token, std::vector<std::string>& pins,
                             std::vector<std::string>& clocks);
    bool parse_line(const std::string& line, ConstraintDB& constraints);
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_SDC_PARSER_HPP
