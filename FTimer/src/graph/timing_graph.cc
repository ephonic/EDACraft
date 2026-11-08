#include "timing_graph.hh"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <optional>
#include <queue>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <stdexcept>

#include "edacraft/core/liberty_db.hpp"
#include "network/network.hh"
#include "liberty/core_liberty_utils.hh"
#include "sdc/resolved_constraints.hh"

namespace te {

namespace ec = edacraft::core;

namespace {

enum class TriValue : uint8_t {
    False,
    True,
    Unknown,
};

TriValue tri_not(TriValue value) {
    if (value == TriValue::Unknown) return TriValue::Unknown;
    return value == TriValue::True ? TriValue::False : TriValue::True;
}

TriValue tri_and(TriValue lhs, TriValue rhs) {
    if (lhs == TriValue::False || rhs == TriValue::False) return TriValue::False;
    if (lhs == TriValue::True && rhs == TriValue::True) return TriValue::True;
    return TriValue::Unknown;
}

TriValue tri_or(TriValue lhs, TriValue rhs) {
    if (lhs == TriValue::True || rhs == TriValue::True) return TriValue::True;
    if (lhs == TriValue::False && rhs == TriValue::False) return TriValue::False;
    return TriValue::Unknown;
}

TriValue tri_xor(TriValue lhs, TriValue rhs) {
    if (lhs == TriValue::Unknown || rhs == TriValue::Unknown) return TriValue::Unknown;
    return lhs == rhs ? TriValue::False : TriValue::True;
}

bool is_when_ident_start(char ch) {
    return std::isalpha(static_cast<unsigned char>(ch)) || ch == '_' ||
           ch == '$' || ch == '\\';
}

bool is_when_ident_char(char ch) {
    return std::isalnum(static_cast<unsigned char>(ch)) || ch == '_' ||
           ch == '$' || ch == '[' || ch == ']' || ch == '.' || ch == '/' ||
           ch == '\\';
}

class LibertyWhenParser {
public:
    using Lookup = std::function<std::optional<int>(std::string_view)>;

    LibertyWhenParser(std::string_view expr, Lookup lookup)
        : expr_(expr), lookup_(std::move(lookup)) {}

    std::optional<bool> parse() {
        auto parsed = parse_tri();
        if (!parsed || *parsed == TriValue::Unknown) return std::nullopt;
        return *parsed == TriValue::True;
    }

    std::optional<TriValue> parse_tri() {
        TriValue value = parse_or();
        skip_ws();
        if (pos_ != expr_.size() || parse_error_) return std::nullopt;
        return value;
    }

private:
    TriValue parse_or() {
        TriValue value = parse_xor();
        while (!parse_error_) {
            skip_ws();
            if (!match('|') && !match('+')) break;
            value = tri_or(value, parse_xor());
        }
        return value;
    }

    TriValue parse_xor() {
        TriValue value = parse_and();
        while (!parse_error_) {
            skip_ws();
            if (!match('^')) break;
            value = tri_xor(value, parse_and());
        }
        return value;
    }

    TriValue parse_and() {
        TriValue value = parse_unary();
        while (!parse_error_) {
            skip_ws();
            if (match('&') || match('*')) {
                value = tri_and(value, parse_unary());
                continue;
            }
            if (!can_start_unary()) break;
            value = tri_and(value, parse_unary());
        }
        return value;
    }

    TriValue parse_unary() {
        skip_ws();
        if (match('!') || match('~')) {
            return tri_not(parse_unary());
        }
        return parse_postfix();
    }

    TriValue parse_postfix() {
        TriValue value = parse_primary();
        while (!parse_error_) {
            skip_ws();
            if (!match('\'')) break;
            value = tri_not(value);
        }
        return value;
    }

    TriValue parse_primary() {
        skip_ws();
        if (match('(')) {
            TriValue value = parse_or();
            skip_ws();
            if (!match(')')) parse_error_ = true;
            return value;
        }

        if (pos_ >= expr_.size()) {
            parse_error_ = true;
            return TriValue::Unknown;
        }

        if ((expr_[pos_] == '0' || expr_[pos_] == '1') &&
            pos_ + 3 < expr_.size() &&
            expr_[pos_ + 1] == '\'' &&
            (expr_[pos_ + 2] == 'b' || expr_[pos_ + 2] == 'B') &&
            (expr_[pos_ + 3] == '0' || expr_[pos_ + 3] == '1')) {
            int value = expr_[pos_ + 3] == '1' ? 1 : 0;
            pos_ += 4;
            return value ? TriValue::True : TriValue::False;
        }

        if (expr_[pos_] == '0' || expr_[pos_] == '1') {
            int value = expr_[pos_++] == '1' ? 1 : 0;
            return value ? TriValue::True : TriValue::False;
        }

        if (expr_[pos_] == '\'' &&
            pos_ + 1 < expr_.size() &&
            (expr_[pos_ + 1] == '0' || expr_[pos_ + 1] == '1')) {
            int value = expr_[pos_ + 1] == '1' ? 1 : 0;
            pos_ += 2;
            return value ? TriValue::True : TriValue::False;
        }

        if (!is_when_ident_start(expr_[pos_])) {
            parse_error_ = true;
            return TriValue::Unknown;
        }

        size_t start = pos_;
        while (pos_ < expr_.size() && is_when_ident_char(expr_[pos_])) {
            ++pos_;
        }
        std::string_view ident = expr_.substr(start, pos_ - start);
        if (!ident.empty() && ident.front() == '\\') {
            ident.remove_prefix(1);
        }
        auto value = lookup_(ident);
        if (!value) return TriValue::Unknown;
        return *value ? TriValue::True : TriValue::False;
    }

    void skip_ws() {
        while (pos_ < expr_.size() &&
               std::isspace(static_cast<unsigned char>(expr_[pos_]))) {
            ++pos_;
        }
    }

    bool match(char ch) {
        if (pos_ < expr_.size() && expr_[pos_] == ch) {
            ++pos_;
            return true;
        }
        return false;
    }

    bool can_start_unary() {
        if (pos_ >= expr_.size()) return false;
        char ch = expr_[pos_];
        return ch == '(' || ch == '!' || ch == '~' ||
               ch == '0' || ch == '1' || ch == '\'' ||
               is_when_ident_start(ch);
    }

    std::string_view expr_;
    Lookup lookup_;
    size_t pos_ = 0;
    bool parse_error_ = false;
};

std::optional<bool> evaluate_liberty_when(
    std::string_view expr,
    const LibertyWhenParser::Lookup& lookup) {
    LibertyWhenParser parser(expr, lookup);
    return parser.parse();
}

std::optional<TriValue> evaluate_liberty_logic(
    std::string_view expr,
    const LibertyWhenParser::Lookup& lookup) {
    LibertyWhenParser parser(expr, lookup);
    return parser.parse_tri();
}

bool merge_constant(std::vector<int8_t>& constants,
                    std::vector<uint8_t>& conflicts,
                    uint32_t net_id,
                    int value) {
    if (net_id >= constants.size() || conflicts[net_id]) return false;
    value = value ? 1 : 0;
    if (constants[net_id] < 0) {
        constants[net_id] = static_cast<int8_t>(value);
        return true;
    }
    if (constants[net_id] == value) return false;
    constants[net_id] = -1;
    conflicts[net_id] = 1;
    return true;
}

std::vector<int8_t> infer_static_net_constants(const Network& net,
                                               const ec::LibertyDB& lib,
                                               const ResolvedConstraintSet* sdc) {
    std::vector<int8_t> constants(net.net_count(), -1);
    std::vector<uint8_t> conflicts(net.net_count(), 0);

    for (uint32_t nid = 0; nid < net.net_count(); ++nid) {
        const auto& n = net.net(NetId{nid});
        if (n.constant_value == 0 || n.constant_value == 1) {
            constants[nid] = n.constant_value;
        }
    }

    auto pin_net_constant = [&](PinId pin) -> std::optional<int> {
        if (!valid(pin) || pin.id >= net.pin_count()) return std::nullopt;
        const auto& p = net.pin(pin);
        if (!valid(p.net) || p.net.id >= constants.size()) return std::nullopt;
        int8_t value = constants[p.net.id];
        if (value != 0 && value != 1) return std::nullopt;
        return static_cast<int>(value);
    };

    auto set_pin_net_constant = [&](PinId pin, int value) -> bool {
        if (!valid(pin) || pin.id >= net.pin_count()) return false;
        const auto& p = net.pin(pin);
        if (!valid(p.net)) return false;
        return merge_constant(constants, conflicts, p.net.id, value);
    };

    if (sdc) {
        for (const auto& ca : sdc->case_analyses()) {
            int value = -1;
            switch (ca.value) {
                case CaseAnalysis::Zero:
                case CaseAnalysis::Fall:
                    value = 0;
                    break;
                case CaseAnalysis::One:
                case CaseAnalysis::Rise:
                    value = 1;
                    break;
            }
            if (value >= 0) {
                set_pin_net_constant(ca.pin, value);
            }
        }
    }

    size_t max_iters = std::max<size_t>(1, net.instance_count() + 1);
    for (size_t iter = 0; iter < max_iters; ++iter) {
        bool changed = false;
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            InstanceId inst_id{iid};
            const auto& inst = net.instance(inst_id);
            std::string_view cell_name = net.cell_name(inst.cell);

            std::unordered_map<std::string, PinId> port_name_to_pin;
            port_name_to_pin.reserve(inst.pins.size());
            for (auto pid : inst.pins) {
                port_name_to_pin.emplace(std::string(net.pin_name(pid)), pid);
            }

            if (cell_name == "__assign__") {
                auto a_it = port_name_to_pin.find("A");
                auto x_it = port_name_to_pin.find("X");
                if (a_it != port_name_to_pin.end() && x_it != port_name_to_pin.end()) {
                    if (auto value = pin_net_constant(a_it->second)) {
                        changed |= set_pin_net_constant(x_it->second, *value);
                    }
                }
                continue;
            }

            const auto& cell_data = net.cell(inst.cell);
            if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) {
                continue;
            }
            const auto& lib_cell = lib.cell(liberty::to_core(cell_data.liberty_library),
                                            liberty::to_core(cell_data.liberty_cell));

            auto lookup = [&](std::string_view pin_name) -> std::optional<int> {
                auto it = port_name_to_pin.find(std::string(pin_name));
                if (it == port_name_to_pin.end()) return std::nullopt;
                return pin_net_constant(it->second);
            };

            for (const auto& lib_pin : lib_cell.pins) {
                if (lib_pin.direction != ec::PortDirection::Output ||
                    lib_pin.function == UINT32_MAX) {
                    continue;
                }
                auto out_it = port_name_to_pin.find(std::string(net.str(lib_pin.name)));
                if (out_it == port_name_to_pin.end()) continue;
                const auto expression = net.str(lib_pin.function);
                auto value = evaluate_liberty_when(expression, lookup);
                if (!value) {
                    // Tri-valued evaluation loses correlations such as
                    // (1 & S) | (1 & !S). Arc observability can nevertheless
                    // remove every input edge of that constant output. Prove
                    // the constant here before publishing the timing graph.
                    std::vector<std::string> unknown;
                    bool supported = true, has_constant = false;
                    evaluate_liberty_when(expression, [&](std::string_view name) -> std::optional<int> {
                        const auto pin = port_name_to_pin.find(std::string(name));
                        if (pin == port_name_to_pin.end() ||
                            net.pin(pin->second).direction != PortDirection::Input) {
                            supported = false; return std::nullopt;
                        }
                        if (const auto known = lookup(name)) { has_constant = true; return known; }
                        if (std::find(unknown.begin(), unknown.end(), name) == unknown.end())
                            unknown.emplace_back(name);
                        return std::nullopt;
                    });
                    // Unknown state symbols, malformed expressions and large
                    // supports remain unknown. No sampled assignment proves
                    // a constant: every assignment must agree.
                    if (supported && has_constant && !unknown.empty() && unknown.size() <= 8) {
                        for (size_t bits = 0; bits < (size_t{1} << unknown.size()); ++bits) {
                            const auto result = evaluate_liberty_when(expression,
                                [&](std::string_view name) -> std::optional<int> {
                                    if (const auto known = lookup(name)) return known;
                                    const auto i = std::find(unknown.begin(), unknown.end(), name);
                                    if (i == unknown.end()) return std::nullopt;
                                    return int((bits >> size_t(i-unknown.begin())) & 1);
                                });
                            if (!result || (value && *value != *result)) { value.reset(); break; }
                            value = result;
                        }
                    }
                }
                if (!value) continue;
                changed |= set_pin_net_constant(out_it->second, *value ? 1 : 0);
            }
        }
        if (!changed) break;
    }

    return constants;
}

} // namespace

std::optional<bool> evaluate_liberty_boolean(std::string_view expression,
    const std::function<std::optional<int>(std::string_view)>& lookup) {
    return evaluate_liberty_when(expression, lookup);
}

// ────────────────────────────────────────────────────────────
// TimingGraph build
// ────────────────────────────────────────────────────────────
//
// For each network pin, create two vertices (rise, fall).
// For each Liberty timing arc, create edges between vertices.
// Bidirectional pins: handled separately (input port → rise/fall vertices).
//
// Vertex mapping: vid = pin_id * 2 + (rf == Rise ? 0 : 1)

int TimingGraph::build(const Network& net, const ec::LibertyDB& lib, const ResolvedConstraintSet* sdc) {
    // Map: pin_id → base vertex id (pin_id * 2)
    uint32_t pin_count = net.pin_count();
    if (pin_count > UINT32_MAX / 2) {
        // Pin count overflow: design too large for 32-bit vertex IDs
        return -1;
    }
    vertices_ = pin_count * 2;

    // Reset all build-owned state. resize(value) preserves existing elements
    // on same-size rebuilds, so use assign/clear for deterministic results.
    pin_.assign(vertices_, PinId{UINT32_MAX});
    transition_.assign(vertices_, Transition::Rise);
    level_.assign(vertices_, 0);
    startpoints_.assign(vertices_, 0);
    endpoints_.assign(vertices_, 0);
    dirty_.assign(vertices_, 0);
    arrivals_.assign(vertices_ * 4, Delay::NEG_INF());
    slews_.assign(vertices_ * 4, Delay::ZERO());
    requireds_.assign(vertices_ * 4, Delay::INF());
    check_kinds_.assign(vertices_ * 2, TimingCheckKind::None);
    check_coverage_.clear();
    disabled_checks_.clear();
    pred_max_.assign(vertices_ * 4, UINT32_MAX);
    pred_min_.assign(vertices_ * 4, UINT32_MAX);
    edge_from_.clear();
    edge_to_.clear();
    edge_arc_.clear();
    edge_conditions_.clear();
    edge_delay_.clear();
    edge_propagated_delay_.clear();
    edge_output_slew_.clear();
    edge_ceff_.clear();
    edge_delay_source_.clear();
    fwd_offset_.clear();
    fwd_edge_.clear();
    rev_offset_.clear();
    rev_edge_.clear();
    level_sorted_.clear();
    level_offsets_.clear();
    clock_domain_.assign(vertices_, UINT32_MAX);
    instance_clk_pin_.assign(net.instance_count(), UINT32_MAX);
    max_level_ = 0;

    // Initialize vertex properties
    for (uint32_t pid = 0; pid < pin_count; ++pid) {
        for (int rf = 0; rf < 2; ++rf) {
            uint32_t vid = pid * 2 + rf;
            pin_[vid] = PinId{pid};
            transition_[vid] = static_cast<Transition>(rf);
        }
    }

    // Build case-analysis disabled transition map
    std::vector<uint8_t> disabled_rise(pin_count, 0);
    std::vector<uint8_t> disabled_fall(pin_count, 0);
    if (sdc) {
        for (const auto& ca : sdc->case_analyses()) {
            if (ca.pin.id < pin_count) {
                switch (ca.value) {
                    case CaseAnalysis::Zero:
                    case CaseAnalysis::Fall:
                        disabled_rise[ca.pin.id] = 1;
                        break;
                    case CaseAnalysis::One:
                    case CaseAnalysis::Rise:
                        disabled_fall[ca.pin.id] = 1;
                        break;
                }
            }
        }
    }

    std::vector<int8_t> static_net_constants =
        infer_static_net_constants(net, lib, sdc);
    static_pin_constants_.assign(pin_count, -1);
    size_t static_constant_nets = 0;
    for (int8_t value : static_net_constants) {
        if (value == 0 || value == 1) static_constant_nets++;
    }
    size_t static_constant_pins = 0;
    for (uint32_t pid = 0; pid < pin_count; ++pid) {
        const auto& p = net.pin(PinId{pid});
        if (!valid(p.net) || p.net.id >= static_net_constants.size()) continue;
        int8_t value = static_net_constants[p.net.id];
        if (value != 0 && value != 1) continue;
        static_pin_constants_[pid] = value;
        disabled_rise[pid] = 1;
        disabled_fall[pid] = 1;
        static_constant_pins++;
    }

    // Collect edges as triples plus optional simple Liberty `when` conditions.
    struct TempEdge {
        uint32_t from;
        uint32_t to;
        uint32_t arc;
        std::vector<EdgeConditionLiteral> conditions;
    };
    std::vector<TempEdge> temp_edges;

    // For each instance, look up its Liberty cell and create edges
    size_t skipped_no_liberty = 0;
    size_t skipped_no_arcs = 0;
    size_t total_arcs = 0;
    size_t when_pruned_arcs = 0;
    size_t function_pruned_arcs = 0;
    size_t an2_arcs = 0;
    size_t cknd_arcs = 0;
    size_t seq_out_pins = 0;
    for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
        InstanceId inst_id{iid};
        const auto& inst = net.instance(inst_id);
        const auto& cell_data = net.cell(inst.cell);

        // Handle assign statements (__assign__ pseudo-cell): create direct
        // zero-delay edges from input pin A to output pin X.
        std::string_view cell_name = net.cell_name(inst.cell);
        if (cell_name == "__assign__") {
            uint32_t a_pid = UINT32_MAX, x_pid = UINT32_MAX;
            for (auto pid : inst.pins) {
                std::string_view pname = net.pin_name(pid);
                if (pname == "A") a_pid = pid.id;
                else if (pname == "X") x_pid = pid.id;
            }
            if (a_pid != UINT32_MAX && x_pid != UINT32_MAX) {
                for (int rf = 0; rf < 2; ++rf) {
                    uint32_t from_vid = a_pid * 2 + rf;
                    uint32_t to_vid   = x_pid * 2 + rf;
                    temp_edges.push_back({from_vid, to_vid, UINT32_MAX, {}});
                }
            }
            continue;
        }

        if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) {
            skipped_no_liberty++;
            continue;
        }

        const auto& lib_cell = lib.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));

        // Build pin name → pin_id map for this instance
        std::unordered_map<uint32_t, uint32_t> port_to_pid; // StringId → pin_id
        std::unordered_map<std::string, uint32_t> port_name_to_pid;
        for (auto pid : inst.pins) {
            const auto& p = net.pin(pid);
            port_to_pid[p.name] = pid.id;
            port_name_to_pid.emplace(std::string(net.pin_name(pid)), pid.id);
        }

        auto pin_constant_value = [&](uint32_t pid) -> std::optional<int> {
            if (pid >= pin_count) return std::nullopt;
            const auto& p = net.pin(PinId{pid});
            if (!valid(p.net)) return std::nullopt;
            if (p.net.id >= static_net_constants.size()) return std::nullopt;
            int8_t value = static_net_constants[p.net.id];
            if (value != 0 && value != 1) return std::nullopt;
            return static_cast<int>(value);
        };

        auto when_condition_is_false =
            [&](const ec::LibertyArcData& arc) -> bool {
                if (arc.when == UINT32_MAX) return false;
                std::string_view expr = net.str(arc.when);
                if (expr.empty()) return false;
                auto lookup = [&](std::string_view pin_name) -> std::optional<int> {
                    auto it = port_name_to_pid.find(std::string(pin_name));
                    if (it == port_name_to_pid.end()) return std::nullopt;
                    return pin_constant_value(it->second);
                };
                auto value = evaluate_liberty_when(expr, lookup);
                return value.has_value() && !*value;
            };

        std::unordered_map<std::string, int> static_port_constants;
        for (const auto& [port_name, pid] : port_name_to_pid) {
            if (auto value = pin_constant_value(pid)) {
                static_port_constants.emplace(port_name, *value);
            }
        }

        auto liberty_output_pin_by_name =
            [&](uint32_t pin_name_id) -> const ec::LibertyPinData* {
                for (const auto& pin : lib_cell.pins) {
                    if (pin.name == pin_name_id) return &pin;
                }
                return nullptr;
            };

        auto output_function_input_unobservable =
            [&](const ec::LibertyArcData& arc) -> bool {
                if (arc.type != ec::LibertyTimingType::Combinational &&
                    arc.type != ec::LibertyTimingType::Clear &&
                    arc.type != ec::LibertyTimingType::Preset) {
                    return false;
                }
                if (static_port_constants.empty()) return false;
                const auto* out_pin = liberty_output_pin_by_name(arc.to_pin);
                if (!out_pin ||
                    out_pin->direction != ec::PortDirection::Output ||
                    out_pin->function == UINT32_MAX) {
                    return false;
                }

                const std::string from_name(net.str(arc.from_pin));
                bool has_context_constant = false;
                for (const auto& [port_name, _] : static_port_constants) {
                    if (port_name != from_name) {
                        has_context_constant = true;
                        break;
                    }
                }
                if (!has_context_constant) return false;

                std::string_view expr = net.str(out_pin->function);
                auto eval_with_forced_input = [&](int forced_value) {
                    auto lookup = [&](std::string_view pin_name) -> std::optional<int> {
                        if (pin_name == from_name) return forced_value;
                        auto it = static_port_constants.find(std::string(pin_name));
                        if (it == static_port_constants.end()) return std::nullopt;
                        return it->second;
                    };
                    return evaluate_liberty_logic(expr, lookup);
                };

                auto value0 = eval_with_forced_input(0);
                auto value1 = eval_with_forced_input(1);
                if (!value0 || !value1) return false;
                if (*value0 == TriValue::Unknown || *value1 == TriValue::Unknown) {
                    return false;
                }
                return *value0 == *value1;
            };

        auto parse_simple_when_assignments =
            [&](std::string_view expr)
                -> std::optional<std::unordered_map<std::string, int>> {
                std::string text(expr);
                for (char& ch : text) {
                    if (ch == '&') ch = ' ';
                }
                if (text.find('|') != std::string::npos ||
                    text.find('+') != std::string::npos ||
                    text.find('^') != std::string::npos) {
                    return std::nullopt;
                }

                std::unordered_map<std::string, int> assignments;
                size_t pos = 0;
                while (pos < text.size()) {
                    while (pos < text.size() &&
                           (std::isspace(static_cast<unsigned char>(text[pos])) ||
                            text[pos] == '(' || text[pos] == ')')) {
                        ++pos;
                    }
                    if (pos >= text.size()) break;

                    int value = 1;
                    if (text[pos] == '!') {
                        value = 0;
                        ++pos;
                    }
                    while (pos < text.size() &&
                           std::isspace(static_cast<unsigned char>(text[pos]))) {
                        ++pos;
                    }

                    size_t start = pos;
                    while (pos < text.size() && is_when_ident_char(text[pos])) {
                        ++pos;
                    }
                    if (start == pos) return std::nullopt;
                    std::string pin = text.substr(start, pos - start);
                    while (!pin.empty() && pin.back() == ')') pin.pop_back();
                    if (pin.empty()) return std::nullopt;

                    auto [it, inserted] = assignments.emplace(std::move(pin), value);
                    if (!inserted && it->second != value) return std::nullopt;
                }
                if (assignments.empty()) return std::nullopt;
                return assignments;
            };

        auto effective_timing_sense =
            [&](const ec::LibertyArcData& arc) -> ec::LibertyTimingSense {
                if (arc.sense != ec::LibertyTimingSense::NonUnate ||
                    arc.when == UINT32_MAX) {
                    return arc.sense;
                }
                const auto* out_pin = liberty_output_pin_by_name(arc.to_pin);
                if (!out_pin || out_pin->function == UINT32_MAX) {
                    return arc.sense;
                }
                auto assignments =
                    parse_simple_when_assignments(net.str(arc.when));
                if (!assignments) return arc.sense;

                const std::string from_name(net.str(arc.from_pin));
                auto eval_with_forced_input = [&](int forced_value) {
                    auto lookup = [&](std::string_view pin_name)
                        -> std::optional<int> {
                        if (pin_name == from_name) return forced_value;
                        auto it = assignments->find(std::string(pin_name));
                        if (it == assignments->end()) return std::nullopt;
                        return it->second;
                    };
                    return evaluate_liberty_logic(net.str(out_pin->function),
                                                  lookup);
                };

                auto value0 = eval_with_forced_input(0);
                auto value1 = eval_with_forced_input(1);
                if (!value0 || !value1 ||
                    *value0 == TriValue::Unknown ||
                    *value1 == TriValue::Unknown) {
                    return arc.sense;
                }
                if (*value0 == TriValue::False && *value1 == TriValue::True) {
                    return ec::LibertyTimingSense::PositiveUnate;
                }
                if (*value0 == TriValue::True && *value1 == TriValue::False) {
                    return ec::LibertyTimingSense::NegativeUnate;
                }
                return ec::LibertyTimingSense::None;
            };

        auto edge_when_conditions =
            [&](const ec::LibertyArcData& arc,
                uint32_t from_pid) -> std::vector<EdgeConditionLiteral> {
                std::vector<EdgeConditionLiteral> conditions;

                const auto& from_pin = net.pin(PinId{from_pid});
                uint32_t from_net = valid(from_pin.net) ? from_pin.net.id : UINT32_MAX;
                auto add_condition = [&](uint32_t cond_pid, int value) -> bool {
                    if (cond_pid >= pin_count) return true;
                    const auto& cond_pin = net.pin(PinId{cond_pid});
                    if (!valid(cond_pin.net)) return true;
                    uint32_t cond_net = cond_pin.net.id;

                    // A condition on the toggling input itself does not define
                    // a stable side value for this timing edge.
                    if (cond_pid == from_pid || cond_net == from_net) return true;

                    if (auto constant = pin_constant_value(cond_pid)) {
                        return *constant == value;
                    }

                    for (auto& literal : conditions) {
                        if (literal.net != cond_net) continue;
                        return literal.value == value;
                    }
                    conditions.push_back(
                        EdgeConditionLiteral{cond_net,
                                             static_cast<int8_t>(value)});
                    return true;
                };

                if (arc.when != UINT32_MAX) {
                    auto assignments =
                        parse_simple_when_assignments(net.str(arc.when));
                    if (assignments) {
                        for (const auto& [port_name, value] : *assignments) {
                            auto it = port_name_to_pid.find(port_name);
                            if (it == port_name_to_pid.end()) continue;
                            if (!add_condition(it->second, value)) {
                                conditions.clear();
                                return conditions;
                            }
                        }
                    }
                }

                if (arc.type != ec::LibertyTimingType::Combinational &&
                    arc.type != ec::LibertyTimingType::Clear &&
                    arc.type != ec::LibertyTimingType::Preset) {
                    return conditions;
                }
                const auto* out_pin = liberty_output_pin_by_name(arc.to_pin);
                if (!out_pin || out_pin->function == UINT32_MAX) {
                    return conditions;
                }

                const std::string from_name(net.str(arc.from_pin));
                for (const auto& [port_name, cond_pid] : port_name_to_pid) {
                    if (port_name == from_name) continue;
                    auto it = port_name_to_pid.find(port_name);
                    if (it == port_name_to_pid.end()) continue;
                    auto blocks_observability = [&](int side_value) -> bool {
                        auto eval_with_forced_input = [&](int forced_value) {
                            auto lookup = [&](std::string_view pin_name)
                                -> std::optional<int> {
                                if (pin_name == from_name) return forced_value;
                                if (pin_name == port_name) return side_value;
                                auto pit = port_name_to_pid.find(std::string(pin_name));
                                if (pit != port_name_to_pid.end()) {
                                    return pin_constant_value(pit->second);
                                }
                                return std::nullopt;
                            };
                            return evaluate_liberty_logic(
                                net.str(out_pin->function), lookup);
                        };

                        auto value0 = eval_with_forced_input(0);
                        auto value1 = eval_with_forced_input(1);
                        return value0 && value1 &&
                               *value0 != TriValue::Unknown &&
                               *value1 != TriValue::Unknown &&
                               *value0 == *value1;
                    };

                    bool block0 = blocks_observability(0);
                    bool block1 = blocks_observability(1);
                    if (block0 == block1) continue;
                    int required = block0 ? 1 : 0;
                    if (!add_condition(cond_pid, required)) {
                        conditions.clear();
                        return conditions;
                    }
                }
                return conditions;
            };

        // Determine if this is a sequential cell (has clk-q arcs)
        bool has_seq_arc = false;
        uint32_t clk_pin_name = UINT32_MAX;
        for (const auto& arc : lib_cell.arcs) {
            if (arc.type == ec::LibertyTimingType::RisingEdge || arc.type == ec::LibertyTimingType::FallingEdge) {
                has_seq_arc = true;
                clk_pin_name = arc.from_pin;
                break;
            }
        }

        // Store CLK pin for this instance (used by CPPR)
        if (has_seq_arc && clk_pin_name != UINT32_MAX) {
            auto clk_it = port_to_pid.find(clk_pin_name);
            if (clk_it != port_to_pid.end()) {
                instance_clk_pin_[iid] = clk_it->second;
            }
        }

        // Helper: check if a pin name is an async control pin (RD, CD, SET, etc.)
        auto is_async_pin_name = [&](uint32_t pin_id) -> bool {
            std::string_view name = net.pin_name(PinId{pin_id});
            // Common async control pin names in standard cell libraries
            static const std::string_view async_names[] = {
                "RD", "RDN", "CD", "CDN", "SET", "SDN",
                "PRE", "PRESET", "CLR", "CLEAR", "RESET"
            };
            for (auto n : async_names) {
                if (name == n) return true;
            }
            return false;
        };

        // Identify async control pins: pins with setup/hold arcs that also drive outputs
        // (e.g. RD, SET, RESET). These should not create combinational edges to Q/QN
        // in the setup/hold graph — they are recovery/removal endpoints, not data endpoints.
        // Also detect by pin name for cells like DRQHDV2 where RD has setup arcs but
        // no explicit combinational arcs to Q (the reset is implied by the ff group).
        std::unordered_set<uint32_t> async_pins;
        for (const auto& arc : lib_cell.arcs) {
            if (ec::liberty_timing_type_is_async_check(arc.type)) {
                auto it = port_to_pid.find(arc.to_pin);
                if (it != port_to_pid.end()) async_pins.insert(it->second);
            }
            if (arc.type == ec::LibertyTimingType::SetupRising || arc.type == ec::LibertyTimingType::SetupFalling) {
                auto setup_to_it = port_to_pid.find(arc.to_pin);
                if (setup_to_it == port_to_pid.end()) continue;
                uint32_t ctrl_pid = setup_to_it->second;
                const auto& pin_data = net.pin(PinId{ctrl_pid});
                // Detect by pin name heuristic
                if (is_async_pin_name(ctrl_pid)) {
                    async_pins.insert(ctrl_pid);
                    continue;
                }
                // A latch D pin has a setup check and a transparent D-Q arc.
                // Their combination does not make it an asynchronous reset.
                if(lib_cell.ff_clocked_on==UINT32_MAX && lib_cell.ff_enable!=UINT32_MAX)
                    continue;
                // Detect by combinational arc to output
                for (const auto& a2 : lib_cell.arcs) {
                    if (a2.from_pin != arc.to_pin) continue;
                    if (a2.type != ec::LibertyTimingType::Combinational &&
                        a2.type != ec::LibertyTimingType::Clear &&
                        a2.type != ec::LibertyTimingType::Preset) continue;
                    auto out_it = port_to_pid.find(a2.to_pin);
                    if (out_it == port_to_pid.end()) continue;
                    if (net.pin(PinId{out_it->second}).direction == PortDirection::Output) {
                        async_pins.insert(ctrl_pid);
                        break;
                    }
                }
            }
        }

        // For each Liberty timing arc, create graph edges
        for (uint32_t arc_idx = 0; arc_idx < lib_cell.arcs.size(); ++arc_idx) {
            const auto& arc = lib_cell.arcs[arc_idx];

            auto from_it = port_to_pid.find(arc.from_pin);
            auto to_it = port_to_pid.find(arc.to_pin);
            if (from_it == port_to_pid.end() || to_it == port_to_pid.end()) continue;

            uint32_t from_pid = from_it->second;
            uint32_t to_pid = to_it->second;
            const auto& from_pin_data = net.pin(PinId{from_pid});
            const auto& to_pin_data = net.pin(PinId{to_pid});

            // Checks and unsupported timing types never become propagation edges.
            if (ec::liberty_timing_type_is_check(arc.type) ||
                arc.type == ec::LibertyTimingType::Unknown) {
                continue;
            }

            // Skip async reset/set edges from async control pins to outputs
            // (Clear, Preset, and Combinational arcs from RD/SET to Q/QN belong to
            // recovery/removal analysis, not setup/hold)
            if ((arc.type == ec::LibertyTimingType::Combinational ||
                 arc.type == ec::LibertyTimingType::Clear ||
                 arc.type == ec::LibertyTimingType::Preset) &&
                async_pins.count(from_pid) &&
                to_pin_data.direction == PortDirection::Output) {
                continue;
            }

            // Skip arcs where both are inputs (no timing path)
            if (from_pin_data.direction == PortDirection::Input &&
                to_pin_data.direction == PortDirection::Input) continue;

            // Check set_disable_timing
            bool arc_disabled = false;
            if (sdc) {
                for (const auto& dt : sdc->disable_timings()) {
                    if (!valid(dt.to_pin) && !valid(dt.from_pin)) {
                        // Both unspecified — shouldn't happen, but skip
                    } else if (!valid(dt.to_pin)) {
                        // Only -from: disable arcs originating from this pin
                        if (from_pid == dt.from_pin.id) {
                            arc_disabled = true;
                            break;
                        }
                    } else if (!valid(dt.from_pin)) {
                        // Only -to: disable arcs arriving at this pin
                        if (to_pid == dt.to_pin.id) {
                            arc_disabled = true;
                            break;
                        }
                    } else {
                        // Both -from and -to: disable specific arc
                        if (from_pid == dt.from_pin.id && to_pid == dt.to_pin.id) {
                            arc_disabled = true;
                            break;
                        }
                    }
                }
            }
            if (arc_disabled) continue;

            if (when_condition_is_false(arc)) {
                when_pruned_arcs++;
                continue;
            }

            if (output_function_input_unobservable(arc)) {
                function_pruned_arcs++;
                continue;
            }

            total_arcs++;
            if (cell_name == "AN2D0BWP30P140") an2_arcs++;
            if (cell_name == "CKND0BWP30P140") cknd_arcs++;

            // Determine which input transitions create edges
            // A clock edge may launch either Q transition, regardless of the
            // clock-to-Q arc's unateness. Both characterized output tables
            // belong to the same triggering clock edge.
            const auto edge_sense = (arc.type == ec::LibertyTimingType::RisingEdge ||
                                     arc.type == ec::LibertyTimingType::FallingEdge)
                ? ec::LibertyTimingSense::NonUnate : effective_timing_sense(arc);
            if (edge_sense == ec::LibertyTimingSense::None) continue;
            const auto arc_conditions = edge_when_conditions(arc, from_pid);
            int rf_start = 0, rf_end = 2;
            if (arc.type == ec::LibertyTimingType::RisingEdge) {
                rf_start = 0; rf_end = 1; // only rise triggers
            } else if (arc.type == ec::LibertyTimingType::FallingEdge) {
                rf_start = 1; rf_end = 2; // only fall triggers
            }

            // Create edges for triggering transitions
            // Positive unate: rise→rise, fall→fall
            // Negative unate: rise→fall, fall→rise
            // Non-unate: all four
            for (int in_rf = rf_start; in_rf < rf_end; ++in_rf) {
                // Skip if this input transition is disabled by case analysis
                if (in_rf == 0 && disabled_rise[from_pid]) continue;
                if (in_rf == 1 && disabled_fall[from_pid]) continue;

                uint32_t from_vid = from_pid * 2 + in_rf;
                int out_rf = (edge_sense == ec::LibertyTimingSense::NegativeUnate)
                    ? (1 - in_rf) : in_rf;
                uint32_t to_vid = to_pid * 2 + out_rf;
                temp_edges.push_back({from_vid, to_vid, arc_idx, arc_conditions});
                if (edge_sense == ec::LibertyTimingSense::NonUnate) {
                    out_rf = 1 - in_rf;
                    uint32_t to_vid2 = to_pid * 2 + out_rf;
                    temp_edges.push_back({from_vid, to_vid2, arc_idx, arc_conditions});
                }
            }

            // Mark sequential outputs (Q) as startpoints
            if (has_seq_arc && (arc.type == ec::LibertyTimingType::RisingEdge || arc.type == ec::LibertyTimingType::FallingEdge)) {
                if (to_pin_data.direction == PortDirection::Output) {
                    startpoints_[to_pid * 2] = 1;
                    startpoints_[to_pid * 2 + 1] = 1;
                    seq_out_pins++;
                }
            }
        }
        if (lib_cell.arcs.empty()) {
            skipped_no_arcs++;
        }

        for (uint32_t a = 0; a < lib_cell.arcs.size(); ++a) {
            const auto& arc = lib_cell.arcs[a];
            if (!ec::liberty_timing_type_is_check(arc.type)) continue;
            bool disabled = when_condition_is_false(arc);
            const auto from = port_to_pid.find(arc.from_pin), to = port_to_pid.find(arc.to_pin);
            if (sdc && from != port_to_pid.end() && to != port_to_pid.end())
                for (const auto& dt : sdc->disable_timings())
                    if ((valid(dt.from_pin) || valid(dt.to_pin)) &&
                        (!valid(dt.from_pin) || dt.from_pin.id == from->second) &&
                        (!valid(dt.to_pin) || dt.to_pin.id == to->second)) disabled = true;
            if (disabled) disabled_checks_[(uint64_t(iid) << 32) | a] = true;
        }

        // Explicit asynchronous checks are endpoints too. Legacy libraries
        // encoding reset checks as setup retain their previous exclusion.
        for (const auto& arc : lib_cell.arcs) {
            if (ec::liberty_timing_type_is_check(arc.type)) {
                // Keep excluded check pins visible to the coverage ledger.
                auto to_it = port_to_pid.find(arc.to_pin);
                if (to_it != port_to_pid.end()) {
                    uint32_t to_pid = to_it->second;
                    // Enable setup/hold checks are data checks too. Discover
                    // endpoints from Liberty arcs, never from a pin-name list.
                    // Conditions and SDC exceptions are handled per check.
                    if (ec::liberty_timing_type_is_async_check(arc.type) ||
                        !async_pins.count(to_pid)) {
                        endpoints_[to_pid * 2] = 1;
                        endpoints_[to_pid * 2 + 1] = 1;
                    }
                }
            }
        }
    }

    // Mark startpoints and endpoints
    size_t top_input_pins = 0;
    size_t top_output_pins = 0;
    for (uint32_t pid = 0; pid < pin_count; ++pid) {
        const auto& p = net.pin(PinId{pid});
        const auto& inst = net.instance(p.instance);
        std::string_view cell_name = net.cell_name(inst.cell);
        if (cell_name != "__top__") continue;

        // Top-level input ports drive internal nets (direction=Output in our model)
        if (p.direction == PortDirection::Output) {
            top_input_pins++;
            startpoints_[pid * 2] = 1;
            startpoints_[pid * 2 + 1] = 1;
        }
        // Top-level output ports are driven by internal nets (direction=Input in our model)
        if (p.direction == PortDirection::Input) {
            top_output_pins++;
            endpoints_[pid * 2] = 1;
            endpoints_[pid * 2 + 1] = 1;
        }
    }

    // Tie cells (TIEH/TIEL) have no timing arcs; their outputs are static
    // startpoints.  Because their value never toggles, disable both transitions
    // so no timing paths propagate through constant-driven pins.
    for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
        InstanceId inst_id{iid};
        const auto& inst = net.instance(inst_id);
        std::string_view cell_name = net.cell_name(inst.cell);
        if (cell_name.find("TIEH") == std::string_view::npos &&
            cell_name.find("TIEL") == std::string_view::npos) {
            continue;
        }
        for (auto pid : inst.pins) {
            const auto& p = net.pin(pid);
            if (p.direction == PortDirection::Output) {
                startpoints_[pid.id * 2] = 1;
                startpoints_[pid.id * 2 + 1] = 1;
                disabled_rise[pid.id] = 1;
                disabled_fall[pid.id] = 1;
            }
        }
    }
    if (verbose_) {
        std::cerr << "[TimingGraph::build] top_input_pins=" << top_input_pins
                  << " top_output_pins=" << top_output_pins << "\n";
    }

    // Add net edges: driver output → load inputs
    size_t net_edges = 0;
    size_t net_edges_skipped = 0;
    // Parser directions are provisional until Liberty linking. Reclassify
    // connected pins from the linked Liberty pin before building net edges;
    // otherwise a sequential D pin can be left out of Net::loads entirely.
    std::vector<std::vector<uint32_t>> pins_by_net(net.net_count());
    for (uint32_t pid = 0; pid < pin_count; ++pid) {
        const auto& p = net.pin(PinId{pid});
        if (valid(p.net) && p.net.id < pins_by_net.size())
            pins_by_net[p.net.id].push_back(pid);
    }
    auto linked_pin_direction = [&](uint32_t pid) {
        const auto& p = net.pin(PinId{pid});
        PortDirection direction = p.direction;
        if (!valid(p.instance)) return direction;
        const auto& inst = net.instance(p.instance);
        const auto& cell_data = net.cell(inst.cell);
        if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell))
            return direction;
        const auto& lib_cell = lib.cell(liberty::to_core(cell_data.liberty_library),
                                        liberty::to_core(cell_data.liberty_cell));
        for (const auto& lib_pin : lib_cell.pins) {
            if (lib_pin.name != p.name) continue;
            return liberty::to_network_direction(lib_pin.direction);
        }
        return direction;
    };
    for (uint32_t nid = 0; nid < net.net_count(); ++nid) {
        const auto& n = net.net(NetId{nid});
        std::vector<uint32_t> drivers;
        std::vector<uint32_t> loads;
        drivers.reserve(2);
        loads.reserve(pins_by_net[nid].size());
        for (uint32_t pid : pins_by_net[nid]) {
            const auto direction = linked_pin_direction(pid);
            if (direction == PortDirection::Output || direction == PortDirection::Inout)
                drivers.push_back(pid);
            if (direction != PortDirection::Output)
                loads.push_back(pid);
        }
        uint32_t driver_pid = UINT32_MAX;
        if (valid(n.driver)) {
            const auto direction = linked_pin_direction(n.driver.id);
            if (direction == PortDirection::Output || direction == PortDirection::Inout)
                driver_pid = n.driver.id;
        }
        if (driver_pid == UINT32_MAX && !drivers.empty()) driver_pid = drivers.front();
        if (driver_pid == UINT32_MAX) {
            net_edges_skipped += loads.size();
            continue;
        }
        for (uint32_t load_pid : loads) {
            if (load_pid == driver_pid) continue;
            for (int rf = 0; rf < 2; ++rf) {
                // Skip if driver transition is disabled by case analysis
                if (rf == 0 && disabled_rise[driver_pid]) continue;
                if (rf == 1 && disabled_fall[driver_pid]) continue;
                uint32_t from_vid = driver_pid * 2 + rf;
                uint32_t to_vid = load_pid * 2 + rf;
                temp_edges.push_back({from_vid, to_vid, UINT32_MAX, {}});
                net_edges++;
            }
        }
    }
    if (verbose_) {
        std::cerr << "[TimingGraph::build] net_edges=" << net_edges
                  << " skipped_loads=" << net_edges_skipped << "\n";
    }

    // Build CSR adjacency
    edge_from_.assign(temp_edges.size(), 0);
    edge_to_.assign(temp_edges.size(), 0);
    edge_arc_.assign(temp_edges.size(), UINT32_MAX);
    edge_conditions_.assign(temp_edges.size(), {});
    edge_delay_.assign(temp_edges.size(), {});
    edge_propagated_delay_.assign(temp_edges.size(), {});
    edge_output_slew_.assign(temp_edges.size(), {});
    edge_ceff_.assign(temp_edges.size(), {});
    edge_delay_source_.assign(temp_edges.size(), {});

    for (size_t i = 0; i < temp_edges.size(); ++i) {
        edge_from_[i] = temp_edges[i].from;
        edge_to_[i] = temp_edges[i].to;
        edge_arc_[i] = temp_edges[i].arc;
        edge_conditions_[i] = std::move(temp_edges[i].conditions);
    }

    // Forward CSR
    std::vector<uint32_t> fwd_deg(vertices_, 0);
    for (auto& e : temp_edges) fwd_deg[e.from]++;
    fwd_offset_.resize(vertices_ + 1);
    fwd_offset_[0] = 0;
    for (uint32_t i = 0; i < vertices_; ++i)
        fwd_offset_[i + 1] = fwd_offset_[i] + fwd_deg[i];
    fwd_edge_.resize(temp_edges.size());
    {
        std::vector<uint32_t> cur = fwd_offset_;
        for (uint32_t eid = 0; eid < temp_edges.size(); ++eid) {
            uint32_t slot = cur[temp_edges[eid].from]++;
            fwd_edge_[slot] = eid;
        }
    }

    // Reverse CSR
    std::vector<uint32_t> rev_deg(vertices_, 0);
    for (auto& e : temp_edges) rev_deg[e.to]++;
    rev_offset_.resize(vertices_ + 1);
    rev_offset_[0] = 0;
    for (uint32_t i = 0; i < vertices_; ++i)
        rev_offset_[i + 1] = rev_offset_[i] + rev_deg[i];
    rev_edge_.resize(temp_edges.size());
    {
        std::vector<uint32_t> cur = rev_offset_;
        for (uint32_t eid = 0; eid < temp_edges.size(); ++eid) {
            uint32_t slot = cur[temp_edges[eid].to]++;
            rev_edge_[slot] = eid;
        }
    }

    // Assign clock domains to startpoints and endpoints
    std::fill(clock_domain_.begin(), clock_domain_.end(), UINT32_MAX);
    if (sdc) {
        const bool has_generated_clocks = std::any_of(sdc->clocks().begin(), sdc->clocks().end(),
            [](const auto& clock) { return clock.generated; });
        // Map clock source pin -> clock index
        std::unordered_map<uint32_t, uint32_t> pin_to_clock;
        for (uint32_t cid = 0; cid < sdc->clocks().size(); ++cid) {
            for (PinId src : sdc->clocks()[cid].sources) {
                if (!valid(src) || src.id >= net.pin_count()) throw std::runtime_error("Clock source pin is outside the network");
                pin_to_clock[src.id] = cid;
            }
        }

        // Assign clock domain to clock source pins
        for (const auto& [pid, cid] : pin_to_clock) {
            clock_domain_[pid * 2] = cid;
            clock_domain_[pid * 2 + 1] = cid;
        }

        // Flattened preserved clock wrappers are represented only by
        // synthetic __assign__ cells. Resolve this zero-delay alias chain
        // when finding a sequential clock source; never traverse arbitrary
        // combinational logic, which can turn reset/data cones into clocks.
        std::unordered_map<uint32_t, uint32_t> assign_driver_by_output;
        std::unordered_map<uint32_t, uint32_t> clock_output_by_input;
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            InstanceId assign_id{iid};
            const auto& assign_inst = net.instance(assign_id);
            if (net.cell_name(assign_inst.cell) != "__assign__") continue;
            PinId input_pin;
            PinId output_pin;
            for (auto pid : assign_inst.pins) {
                if (net.pin_name(pid) == "A") input_pin = pid;
                else if (net.pin_name(pid) == "X") output_pin = pid;
            }
            if (!valid(input_pin) || !valid(output_pin) ||
                input_pin.id >= net.pin_count() || output_pin.id >= net.pin_count()) {
                continue;
            }
            const auto& input_data = net.pin(input_pin);
            if (!valid(input_data.net) || input_data.net.id >= net.net_count()) continue;
            const auto& input_net = net.net(input_data.net);
            if (valid(input_net.driver)) {
                assign_driver_by_output[output_pin.id] = pin_to_clock.count(input_pin.id) ? input_pin.id : input_net.driver.id;
                clock_output_by_input[input_pin.id] = output_pin.id;
            }
        }

        // Liberty-declared integrated clock gates preserve the source clock
        // domain.  Follow only the pins carrying explicit clock-gate roles;
        // arbitrary combinational clock logic remains unconstrained unless
        // the SDC defines a generated clock for it.
        std::unordered_map<uint32_t, uint32_t> icg_clock_driver_by_output;
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            InstanceId instance_id{iid};
            const auto& instance = net.instance(instance_id);
            const auto& cell_data = net.cell(instance.cell);
            if (!valid(cell_data.liberty_library) ||
                !valid(cell_data.liberty_cell)) {
                continue;
            }
            const auto& liberty_cell = lib.cell(
                liberty::to_core(cell_data.liberty_library),
                liberty::to_core(cell_data.liberty_cell));
            if (liberty_cell.clock_gating_integrated_cell == UINT32_MAX) {
                continue;
            }

            uint32_t clock_name = UINT32_MAX;
            uint32_t output_name = UINT32_MAX;
            bool ambiguous = false;
            for (const auto& liberty_pin : liberty_cell.pins) {
                if (liberty_pin.clock_gate_clock_pin) {
                    if (clock_name != UINT32_MAX) ambiguous = true;
                    clock_name = liberty_pin.name;
                }
                if (liberty_pin.clock_gate_out_pin) {
                    if (output_name != UINT32_MAX) ambiguous = true;
                    output_name = liberty_pin.name;
                }
            }
            if (ambiguous || clock_name == UINT32_MAX ||
                output_name == UINT32_MAX) {
                continue;
            }

            PinId clock_pin = NULL_PIN;
            PinId output_pin = NULL_PIN;
            for (PinId pin : instance.pins) {
                const auto& pin_data = net.pin(pin);
                if (pin_data.name == clock_name) clock_pin = pin;
                if (pin_data.name == output_name) output_pin = pin;
            }
            if (!valid(clock_pin) || !valid(output_pin)) continue;
            const auto& clock_pin_data = net.pin(clock_pin);
            if (!valid(clock_pin_data.net)) continue;
            const auto& clock_net = net.net(clock_pin_data.net);
            if (!valid(clock_net.driver)) continue;
            icg_clock_driver_by_output[output_pin.id] = pin_to_clock.count(clock_pin.id) ? clock_pin.id : clock_net.driver.id;
            clock_output_by_input[clock_pin.id] = output_pin.id;
        }

        // CTS buffers preserve the clock waveform and source domain. Identify
        // them by their single input/output and positive-unate combinational
        // arcs, rather than by technology-specific cell names. Do not cross
        // multi-input logic, sequential cells, or disabled timing arcs.
        std::unordered_map<uint32_t, uint32_t> buffer_clock_driver_by_output;
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            const auto& instance = net.instance(InstanceId{iid});
            const auto& cell = net.cell(instance.cell);
            if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
            const auto& lc = lib.cell(liberty::to_core(cell.liberty_library),
                                      liberty::to_core(cell.liberty_cell));
            uint32_t input_name = UINT32_MAX, output_name = UINT32_MAX;
            bool ambiguous = false;
            for (const auto& pin : lc.pins) {
                if (pin.direction == ec::PortDirection::Input) {
                    if (input_name != UINT32_MAX) ambiguous = true;
                    input_name = pin.name;
                } else if (pin.direction == ec::PortDirection::Output) {
                    if (output_name != UINT32_MAX) ambiguous = true;
                    output_name = pin.name;
                } else {
                    ambiguous = true;
                }
            }
            if (ambiguous || input_name == UINT32_MAX || output_name == UINT32_MAX ||
                lc.arcs.empty()) continue;
            for (const auto& arc : lc.arcs) {
                if (arc.from_pin != input_name || arc.to_pin != output_name ||
                    arc.type != ec::LibertyTimingType::Combinational ||
                    arc.sense != ec::LibertyTimingSense::PositiveUnate) {
                    ambiguous = true;
                    break;
                }
            }
            if (ambiguous) continue;
            PinId input = NULL_PIN, output = NULL_PIN;
            for (auto pin : instance.pins) {
                if (net.pin(pin).name == input_name) input = pin;
                if (net.pin(pin).name == output_name) output = pin;
            }
            if (!valid(input) || !valid(output) || !valid(net.pin(input).net)) continue;
            bool active_arc = false;
            for (auto eid : reverse_edges(output.id * 2)) {
                if (edge_arc(eid) != UINT32_MAX &&
                    vertex_pin(edge_from(eid)) == input) active_arc = true;
            }
            if (!active_arc) continue;
            auto driver = net.net(net.pin(input).net).driver;
            if (valid(driver)) {
                buffer_clock_driver_by_output[output.id] = pin_to_clock.count(input.id) ? input.id : driver.id;
                clock_output_by_input[input.id] = output.id;
            }
        }

        // A defined clock propagates through active combinational timing arcs,
        // including discrete clock gates whose enable is not itself a clock.
        // Requiring every input to be a clock loses latch+gate implementations
        // (C906 apb_clk_buf) and turns their ideal clock slew into a data slew.
        // Never traverse sequential launch arcs or overwrite explicit sources.
        // Keep all reached domains until the walk finishes: two clock sources
        // at a mux must not silently select whichever source was visited first.
        std::vector<std::pair<uint32_t,uint32_t>> clock_queue;
        std::unordered_map<uint32_t,std::vector<uint32_t>> clock_domains;
        auto enqueue_clock = [&](uint32_t vertex, uint32_t domain) {
            auto& domains = clock_domains[vertex];
            if (std::find(domains.begin(),domains.end(),domain) == domains.end()) {
                domains.push_back(domain);
                clock_queue.emplace_back(vertex,domain);
            }
        };
        for (const auto& source : pin_to_clock) {
            enqueue_clock(source.first*2,source.second);
            enqueue_clock(source.first*2+1,source.second);
        }
        for (size_t head=0;head<clock_queue.size();++head) {
            const auto [from,domain]=clock_queue[head];
            for (const auto edge : forward_edges(from)) {
                const auto to=edge_to(edge);
                if (is_startpoint(to) || pin_to_clock.count(vertex_pin(to).id)) continue;
                enqueue_clock(to,domain);
            }
        }
        for (const auto& [vertex,domains] : clock_domains)
            clock_domain_[vertex] = domains.size()==1 ? domains.front() : UINT32_MAX;
        std::unordered_map<uint32_t, uint32_t> resolved_clock_by_driver;
        auto resolve_alias_clock_domain = [&](PinId driver,
                                              std::vector<PinId>* alias_pins = nullptr)
            -> std::optional<uint32_t> {
            std::unordered_set<uint32_t> seen;
            PinId current = driver;
            std::optional<uint32_t> resolved;
            while (valid(current)) {
                auto clock_it = pin_to_clock.find(current.id);
                if (clock_it != pin_to_clock.end()) {
                    resolved = clock_it->second;
                    break;
                }
                // Q/D also store their launch/capture domain. That tag is not
                // proof that a clock waveform reaches the pin: crossing Q
                // would invent a divided/generated clock absent from the SDC.
                if (clock_domains.count(current.id*2) && clock_domains.count(current.id*2+1) &&
                    clock_domain_[current.id*2]!=UINT32_MAX &&
                    clock_domain_[current.id*2]==clock_domain_[current.id*2+1]) {
                    resolved=clock_domain_[current.id*2];
                    break;
                }
                auto cached = resolved_clock_by_driver.find(current.id);
                if (cached != resolved_clock_by_driver.end()) {
                    if (cached->second != UINT32_MAX) resolved = cached->second;
                    break;
                }
                if (!seen.insert(current.id).second) break;
                if (alias_pins) alias_pins->push_back(current);
                auto alias_it = assign_driver_by_output.find(current.id);
                if (alias_it != assign_driver_by_output.end()) {
                    current = PinId{alias_it->second};
                    continue;
                }
                auto icg_it = icg_clock_driver_by_output.find(current.id);
                if (icg_it != icg_clock_driver_by_output.end()) {
                    current = PinId{icg_it->second};
                    continue;
                }
                auto buffer_it = buffer_clock_driver_by_output.find(current.id);
                if (buffer_it != buffer_clock_driver_by_output.end()) {
                    current = PinId{buffer_it->second};
                    continue;
                }
                break;
            }
            // Cache both successful and unavailable chains. Deep CTS trees
            // must not hit an arbitrary depth limit or be retraced once for
            // every register; cycles are bounded by the visited-pin set.
            for (auto pid : seen) resolved_clock_by_driver[pid] = resolved.value_or(UINT32_MAX);
            return resolved;
        };

        // A generated waveform is an ideal clock seed. A single per-vertex
        // domain cannot also retain its pre-generation data launch history.
        // Accept only clock sinks and the clock-preserving paths above.
        if (has_generated_clocks) {
        std::unordered_set<uint32_t> clock_sinks;
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            const auto& instance = net.instance(InstanceId{iid});
            const auto& cell = net.cell(instance.cell);
            if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
            const auto& lc = lib.cell(liberty::to_core(cell.liberty_library), liberty::to_core(cell.liberty_cell));
            for (const auto& arc : lc.arcs) {
                if (arc.type != ec::LibertyTimingType::RisingEdge && arc.type != ec::LibertyTimingType::FallingEdge &&
                    !ec::liberty_timing_type_is_check(arc.type)) continue;
                for (auto pin : instance.pins) if (net.pin(pin).name == arc.from_pin) clock_sinks.insert(pin.id);
            }
        }
        for (uint32_t cid = 0; cid < sdc->clocks().size(); ++cid) {
            const auto& clock = sdc->clocks()[cid];
            if (!clock.generated) continue;
            if (clock.sources.size() != 1) throw std::runtime_error("Generated clock requires exactly one target");
            auto source = clock.generated_source;
            if (!valid(source) || source.id >= net.pin_count()) throw std::runtime_error("Generated clock source is outside the network");
            auto master = resolve_alias_clock_domain(source);
            if (!master && valid(source) && valid(net.pin(source).net))
                master = resolve_alias_clock_domain(net.net(net.pin(source).net).driver);
            if (!master || *master != clock.master_clock)
                throw std::runtime_error("Generated clock source is not bound to its declared master clock tree");
            for (auto target : clock.sources) {
                std::unordered_map<uint32_t, uint8_t> state;
                std::vector<std::pair<PinId, bool>> pending{{target, false}};
                while (!pending.empty()) {
                    const auto [driver, leaving] = pending.back(); pending.pop_back();
                    if (leaving) { state[driver.id] = 2; continue; }
                    if (state[driver.id] == 2) continue;
                    if (state[driver.id] == 1) throw std::runtime_error("Cycle in generated clock fanout");
                    state[driver.id] = 1; pending.push_back({driver, true});
                    const auto output = clock_output_by_input.find(driver.id);
                    if (output != clock_output_by_input.end()) {
                        pending.push_back({PinId{output->second}, false}); continue;
                    }
                    if (clock_sinks.count(driver.id)) continue;
                    const auto& pd = net.pin(driver);
                    if (!valid(pd.net) || net.net(pd.net).driver != driver)
                        throw std::runtime_error("Generated clock target must drive a clock net or be a clock input");
                    for (auto load : net.net(pd.net).loads) {
                        if (load == driver) continue;
                        const auto next = clock_output_by_input.find(load.id);
                        if (next == clock_output_by_input.end() && !clock_sinks.count(load.id))
                            throw std::runtime_error("Generated clock has unsupported data, output-port or uncharacterized fanout");
                        if (next != clock_output_by_input.end()) pending.push_back({PinId{next->second}, false});
                    }
                }
                startpoints_[target.id * 2] = startpoints_[target.id * 2 + 1] = 1;
            }
        }
        }

        // PI/PO domains from input/output delays
        for (uint32_t pid = 0; pid < pin_count; ++pid) {
            if (pin_to_clock.count(pid)) continue;
            const auto& p = net.pin(PinId{pid});
            const auto& inst = net.instance(p.instance);
            std::string_view cell_name = net.cell_name(inst.cell);
            if (cell_name == "__top__") {
                if (p.direction == PortDirection::Output) {
                    for (const auto& id : sdc->input_delays()) {
                        for (auto port : id.ports) {
                            if (port.id == pid) {
                                uint32_t domain = id.clock < sdc->clocks().size() ? id.clock : 0;
                                clock_domain_[pid * 2] = domain;
                                clock_domain_[pid * 2 + 1] = domain;
                                break;
                            }
                        }
                    }
                }
                if (p.direction == PortDirection::Input) {
                    for (const auto& od : sdc->output_delays()) {
                        for (auto port : od.ports) {
                            if (port.id == pid) {
                                uint32_t domain = od.clock < sdc->clocks().size() ? od.clock : 0;
                                clock_domain_[pid * 2] = domain;
                                clock_domain_[pid * 2 + 1] = domain;
                                break;
                            }
                        }
                    }
                }
            }
        }

        // Register domains by tracing CLK net driver back to clock source
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            InstanceId inst_id{iid};
            const auto& inst = net.instance(inst_id);
            const auto& cell_data = net.cell(inst.cell);
            if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) continue;
            const auto& lib_cell = lib.cell(liberty::to_core(cell_data.liberty_library),
                                            liberty::to_core(cell_data.liberty_cell));

            bool has_seq = false;
            uint32_t clk_pin_name = UINT32_MAX;
            for (const auto& arc : lib_cell.arcs) {
                if (arc.type == ec::LibertyTimingType::RisingEdge || arc.type == ec::LibertyTimingType::FallingEdge) {
                    has_seq = true;
                    clk_pin_name = arc.from_pin;
                    break;
                }
            }
            if (!has_seq) continue;

            PinId clk_pin;
            for (auto pid : inst.pins) {
                const auto& p = net.pin(pid);
                if (p.name == clk_pin_name) {
                    clk_pin = pid;
                    break;
                }
            }
            if (!valid(clk_pin)) continue;

            const auto& clk_pin_data = net.pin(clk_pin);
            if (!valid(clk_pin_data.net)) continue;
            const auto& clk_net = net.net(clk_pin_data.net);
            if (!valid(clk_net.driver)) continue;

            std::vector<PinId> alias_pins;
            auto domain = pin_to_clock.count(clk_pin.id) ? std::optional<uint32_t>{pin_to_clock.at(clk_pin.id)}
                : resolve_alias_clock_domain(clk_net.driver, &alias_pins);
            if (!domain) continue;
            for (PinId alias_pin : alias_pins) {
                clock_domain_[alias_pin.id * 2] = *domain;
                clock_domain_[alias_pin.id * 2 + 1] = *domain;
            }
            clock_domain_[clk_pin.id * 2] = *domain;
            clock_domain_[clk_pin.id * 2 + 1] = *domain;

            // Build local port->pid map
            std::unordered_map<uint32_t, uint32_t> port_to_pid;
            for (auto pid : inst.pins) {
                const auto& p = net.pin(pid);
                port_to_pid[p.name] = pid.id;
            }

            for (const auto& arc : lib_cell.arcs) {
                if (arc.type == ec::LibertyTimingType::RisingEdge || arc.type == ec::LibertyTimingType::FallingEdge) {
                    auto q_it = port_to_pid.find(arc.to_pin);
                    if (q_it != port_to_pid.end()) {
                        uint32_t q_pid = q_it->second;
                        if (pin_to_clock.count(q_pid)) continue;
                        clock_domain_[q_pid * 2] = *domain;
                        clock_domain_[q_pid * 2 + 1] = *domain;
                    }
                }
                if (arc.type == ec::LibertyTimingType::SetupRising || arc.type == ec::LibertyTimingType::SetupFalling) {
                    auto d_it = port_to_pid.find(arc.to_pin);
                    if (d_it != port_to_pid.end()) {
                        uint32_t d_pid = d_it->second;
                        clock_domain_[d_pid * 2] = *domain;
                        clock_domain_[d_pid * 2 + 1] = *domain;
                    }
                }
            }
        }
    // Resolve each timing check's actual related pin independently of CP->Q.
    // This also covers cells with checks but no characterized sequential output.
        for (uint32_t iid = 0; iid < net.instance_count(); ++iid) {
            const auto& inst = net.instance(InstanceId{iid});
            const auto& cell = net.cell(inst.cell);
            if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
            const auto& lc = lib.cell(liberty::to_core(cell.liberty_library),
                                      liberty::to_core(cell.liberty_cell));
            for (const auto& arc : lc.arcs) {
                if (!ec::liberty_timing_type_is_check(arc.type)) continue;
                PinId clock = NULL_PIN, target = NULL_PIN;
                for (auto pin : inst.pins) {
                    if (net.pin(pin).name == arc.from_pin) clock = pin;
                    if (net.pin(pin).name == arc.to_pin) target = pin;
                }
                if (!valid(clock) || !valid(target) || !valid(net.pin(clock).net)) continue;
                auto driver = net.net(net.pin(clock).net).driver;
                if (!valid(driver)) continue;
                std::vector<PinId> aliases;
                auto domain = pin_to_clock.count(clock.id) ? std::optional<uint32_t>{pin_to_clock.at(clock.id)}
                    : resolve_alias_clock_domain(driver, &aliases);
                if (!domain) continue;
                aliases.push_back(clock);
                aliases.push_back(target);
                for (auto pin : aliases) {
                    if (pin_to_clock.count(pin.id)) continue;
                    clock_domain_[pin.id * 2] = *domain;
                    clock_domain_[pin.id * 2 + 1] = *domain;
                }
            }
        }
    }

    path_only_endpoints_.assign(vertices_,0);
    path_origin_pin_ids_.clear();
    if(sdc) {
        // Runtime PinIds change when a buffer/ECO rebuilds the adapter. Use
        // ordinals of logical names for the check identity across candidates.
        std::map<std::string,std::vector<uint32_t>> origins;
        auto collect_origins=[&](const auto& delays) { for(const auto& d:delays)for(auto pin:d.from_pins) {
            const auto& pd=net.pin(pin);
            const auto name=(valid(pd.instance)?std::string(net.instance_name(pd.instance))+"/":std::string{})+
                std::string(net.pin_name(pin));
            origins[name].push_back(pin.id);
        }};
        collect_origins(sdc->max_delays());collect_origins(sdc->min_delays());
        uint32_t origin_id=0;
        for(const auto& [name,pins]:origins) { ++origin_id;for(auto pin:pins)path_origin_pin_ids_[pin]=origin_id; }
        auto mark=[&](const auto& delays) { for(const auto& d:delays)for(auto pin:d.to_pins)
            for(unsigned rf=0;rf<2;++rf) {
                const auto vid=pin.id*2+rf;
                if(vid>=vertices_)continue;
                if(!endpoints_[vid])path_only_endpoints_[vid]=1;
                endpoints_[vid]=1;
            }
        };
        mark(sdc->max_delays());mark(sdc->min_delays());mark(sdc->data_checks());
    }

    // Count startpoints and endpoints
    size_t sp_count = 0, ep_count = 0;
    for (uint32_t v = 0; v < vertices_; ++v) {
        if (startpoints_[v]) sp_count++;
        if (endpoints_[v]) ep_count++;
    }
    if (verbose_) {
        std::cerr << "[TimingGraph::build] seq_out_pins_marked=" << seq_out_pins << "\n";
    }

    // Count vertices with 0 incoming edges
    std::vector<uint32_t> indeg(vertices_, 0);
    for (auto& e : temp_edges) indeg[e.to]++;
    size_t zero_indegree = 0;
    size_t zero_indegree_output = 0;
    size_t zero_indegree_input = 0;
    size_t zero_indegree_other = 0;
    for (uint32_t v = 0; v < vertices_; ++v) {
        if (indeg[v] == 0) {
            zero_indegree++;
            PinId pin = pin_[v];
            const auto& p = net.pin(pin);
            if (p.direction == PortDirection::Output) {
                zero_indegree_output++;
            } else if (p.direction == PortDirection::Input) {
                zero_indegree_input++;
            } else {
                zero_indegree_other++;
            }
        }
    }
    if (verbose_) {
        std::cerr << "[TimingGraph::build] vertices_with_0_incoming=" << zero_indegree
                  << " output=" << zero_indegree_output
                  << " input=" << zero_indegree_input
                  << " other=" << zero_indegree_other << "\n";
        // Debug: list the "other" zero-indegree vertices
        int dbg_other = 0;
        for (uint32_t v = 0; v < vertices_ && dbg_other < 20; ++v) {
            if (indeg[v] == 0) {
                PinId pin = pin_[v];
                const auto& p = net.pin(pin);
                if (p.direction != PortDirection::Output && p.direction != PortDirection::Input) {
                    std::string_view cell_name = "(none)";
                    std::string_view pin_name = net.pin_name(pin);
                    if (valid(p.instance)) {
                        const auto& inst = net.instance(p.instance);
                        cell_name = net.cell_name(inst.cell);
                    }
                    std::cerr << "[TimingGraph::build]   zero_indeg_other vid=" << v << " pin="
                              << pin_name << " cell=" << cell_name << " dir="
                              << static_cast<int>(p.direction) << "\n";
                    dbg_other++;
                }
            }
        }
    }

    // Levelize
    if (verbose_) {
        std::cerr << "[TimingGraph::build] instances=" << net.instance_count()
              << " skipped_no_liberty=" << skipped_no_liberty
              << " skipped_no_arcs=" << skipped_no_arcs
              << " total_arcs=" << total_arcs
              << " when_pruned_arcs=" << when_pruned_arcs
              << " function_pruned_arcs=" << function_pruned_arcs
              << " static_constant_nets=" << static_constant_nets
              << " static_constant_pins=" << static_constant_pins
              << " an2_arcs=" << an2_arcs
              << " cknd_arcs=" << cknd_arcs
              << " edges=" << temp_edges.size()
              << " startpoints=" << sp_count
              << " endpoints=" << ep_count
              << "\n";
    }
    int levels = levelize();
    // Clock reachability was computed through active combinational arcs before
    // binding launch/capture domains; sequential outputs are traversal stops.
    return levels;
}

// ────────────────────────────────────────────────────────────
// Levelize: topological sort (Kahn's algorithm)
// ────────────────────────────────────────────────────────────
int TimingGraph::levelize() {
    std::vector<int> in_degree(vertices_, 0);
    for (uint32_t eid = 0; eid < edge_from_.size(); ++eid) {
        in_degree[edge_to_[eid]]++;
    }

    std::queue<uint32_t> q;
    for (uint32_t vid = 0; vid < vertices_; ++vid) {
        if (in_degree[vid] == 0) {
            level_[vid] = 0;
            q.push(vid);
        }
    }
    if (verbose_) {
        std::cerr << "[levelize] zero-indegree vertices: " << q.size() << "\n";
    }

    int max_level = 0;
    std::vector<uint32_t> sorted;
    sorted.reserve(vertices_);

    while (!q.empty()) {
        uint32_t vid = q.front(); q.pop();
        sorted.push_back(vid);
        max_level = std::max(max_level, level_[vid]);

        for (uint32_t eid : forward_edges(vid)) {
            uint32_t to = edge_to_[eid];
            in_degree[to]--;
            if (in_degree[to] == 0) {
                level_[to] = level_[vid] + 1;
                q.push(to);
            }
        }
    }

    // Handle cycles: unvisited vertices get level = max_level + 1
    int cycle_level = max_level + 1;
    for (uint32_t vid = 0; vid < vertices_; ++vid) {
        if (in_degree[vid] > 0) {
            level_[vid] = cycle_level;
            sorted.push_back(vid);
        }
    }

    max_level_ = max_level;
    level_sorted_ = std::move(sorted);

    // Build level offsets: level_offsets_[L] = first index in level_sorted_
    level_offsets_.assign(cycle_level + 2, -1); // -1 = not yet set
    for (size_t i = 0; i < level_sorted_.size(); ++i) {
        int lvl = level_[level_sorted_[i]];
        if (level_offsets_[lvl] < 0) level_offsets_[lvl] = static_cast<int>(i);
        level_offsets_[lvl + 1] = static_cast<int>(i + 1);
    }

    return max_level_;
}

void TimingGraph::propagate_clock_domains() {
    if (clock_domain_.empty() || level_sorted_.empty()) return;

    size_t inferred = 0;
    // A preserved hierarchical clock tree may cross several module ports and
    // generated assign/gating nodes whose levels are not strictly ordered
    // with the data graph. Iterate to a fixed point so a domain can travel
    // through all such nodes instead of stopping after the first pass.
    bool changed = true;
    while (changed) {
        changed = false;
        for (uint32_t vid : level_sorted_) {
            if (vid >= clock_domain_.size()) continue;
            if (clock_domain_[vid] != UINT32_MAX) continue;

            uint32_t inferred_domain = UINT32_MAX;
            bool conflict = false;
            for (uint32_t eid : reverse_edges(vid)) {
                uint32_t from_vid = edge_from_[eid];
                if (from_vid >= clock_domain_.size()) continue;
                uint32_t from_domain = clock_domain_[from_vid];
                if (from_domain == UINT32_MAX) continue;
                if (inferred_domain == UINT32_MAX) {
                    inferred_domain = from_domain;
                    continue;
                }
                if (inferred_domain != from_domain) {
                    conflict = true;
                    break;
                }
            }

            if (!conflict && inferred_domain != UINT32_MAX) {
                clock_domain_[vid] = inferred_domain;
                ++inferred;
                changed = true;
            }
        }
    }

    if (verbose_) {
        std::cerr << "[TimingGraph::build] inferred_clock_domain_vertices="
                  << inferred << "\n";
    }
}

} // namespace te
