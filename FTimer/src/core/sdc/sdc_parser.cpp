#include "edacraft/core/sdc_parser.hpp"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <optional>
#include <unordered_map>
#include <unordered_set>

namespace edacraft::core {

static bool starts_with(const std::string& s, const std::string& prefix) {
    return s.size() >= prefix.size() && s.compare(0, prefix.size(), prefix) == 0;
}

static bool negative_number_token(const std::string& token) {
    return token.size() > 1 && token.front() == '-' &&
        (std::isdigit(static_cast<unsigned char>(token[1])) || token[1] == '.');
}

static bool parse_delay_number(const std::string& token, float& value) {
    try {
        size_t consumed = 0;
        value = std::stof(token, &consumed);
        return consumed == token.size() && std::isfinite(value);
    } catch (...) { return false; }
}

bool SdcParser::parse_time_number(const std::string& token, float& value) const {
    if (!parse_delay_number(token, value)) return false;
    value *= time_scale_ns_;
    return std::isfinite(value);
}

bool SdcParser::parse_capacitance_number(const std::string& token, float& value) const {
    if (!parse_delay_number(token, value)) return false;
    value *= capacitance_scale_pf_;
    return std::isfinite(value);
}

std::string SdcParser::Tokens::peek() const {
    return pos < words.size() ? words[pos] : "";
}

std::string SdcParser::Tokens::next() {
    return pos < words.size() ? words[pos++] : "";
}

bool SdcParser::Tokens::has_more() const {
    return pos < words.size();
}

SdcParser::Tokens SdcParser::tokenize(const std::string& line) {
    Tokens result;
    std::string current;
    int bracket_depth = 0;
    bool in_brace = false;
    bool in_quote = false;
    int i = 0;
    while (i < (int)line.size()) {
        char c = line[i];
        if (c == '"') {
            in_quote = !in_quote;
            current += c;
        } else if (c == '[' && !in_brace && !in_quote) {
            ++bracket_depth;
            current += c;
        } else if (c == ']' && !in_brace && !in_quote) {
            --bracket_depth;
            current += c;
            if (!current.empty() && !in_quote && !in_brace && bracket_depth == 0) {
                result.words.push_back(current);
                current.clear();
            }
        } else if (c == '{') {
            in_brace = true;
            current += c;
        } else if (c == '}') {
            in_brace = false;
            current += c;
            if (!current.empty() && !in_quote && bracket_depth == 0) {
                result.words.push_back(current);
                current.clear();
            }
        } else if (std::isspace(static_cast<unsigned char>(c)) && bracket_depth == 0 && !in_brace && !in_quote) {
            if (!current.empty()) {
                result.words.push_back(current);
                current.clear();
            }
        } else {
            current += c;
        }
        i++;
    }
    if (!current.empty()) {
        result.words.push_back(current);
    }
    return result;
}

std::string SdcParser::expand_bracket_expr(const std::string& s) {
    size_t start = s.find('[');
    if (start == std::string::npos) return s;
    if (start != 0) return s;

    int depth = 0;
    bool in_brace = false;
    bool in_quote = false;
    size_t end = std::string::npos;
    for (size_t i = start; i < s.size(); ++i) {
        char c = s[i];
        if (c == '"') {
            in_quote = !in_quote;
        } else if (c == '{' && !in_quote) {
            in_brace = true;
        } else if (c == '}' && !in_quote) {
            in_brace = false;
        } else if (c == '[' && !in_brace && !in_quote) {
            ++depth;
        } else if (c == ']' && !in_brace && !in_quote) {
            --depth;
            if (depth == 0) { end = i; break; }
        }
    }
    if (end == std::string::npos) return s;

    std::string inner = s.substr(start + 1, end - start - 1);
    // DC emits exception selectors as [list [get_ports a] ...]. Keep the
    // complete nested expression as one word, then flatten its static name
    // lists. Splitting at the first inner ']' drops the remaining selectors.
    auto list = tokenize(inner);
    if (list.next() == "list") {
        std::string names;
        while (list.has_more()) {
            std::string value = expand_bracket_expr(list.next());
            if (value.size() >= 2 && value.front() == '{' && value.back() == '}')
                value = value.substr(1, value.size()-2);
            if (!names.empty()) names += " ";
            names += value;
        }
        return "{" + names + "}";
    }
    inner = expand_bracket_expr(inner);
    // "get_ports foo" or "get_pins foo" -> return the argument(s)
    std::istringstream iss(inner);
    std::string cmd;
    iss >> cmd;
    std::string result;
    std::string token;
    bool first_argument = true;
    while (iss >> token) {
        if (first_argument && starts_with(cmd, "get_") && token == "-quiet") {
            first_argument = false; continue;
        }
        first_argument = false;
        if (!result.empty()) result += " ";
        result += token;
    }
    return result.empty() ? inner : result;
}

// Extract port name(s) from a token that may contain [get_ports ...]
static std::vector<std::string> extract_ports(const std::string& token,
                                               const std::string& expanded) {
    std::vector<std::string> result;
    auto trim_token = [](std::string s) {
        while (!s.empty() && std::isspace(static_cast<unsigned char>(s.front()))) {
            s.erase(s.begin());
        }
        while (!s.empty() && std::isspace(static_cast<unsigned char>(s.back()))) {
            s.pop_back();
        }
        if (s.size() >= 2 && ((s.front() == '{' && s.back() == '}') ||
                              (s.front() == '"' && s.back() == '"'))) {
            s = s.substr(1, s.size() - 2);
        }
        return s;
    };
    std::string text = trim_token(expanded);
    // If the expanded string contains spaces, split into multiple ports
    if (text.find(' ') != std::string::npos) {
        std::istringstream iss(text);
        std::string t;
        while (iss >> t) {
            result.push_back(trim_token(t));
        }
    } else {
        result.push_back(text);
    }
    return result;
}

void SdcParser::parse_path_selector(const std::string& token,
    std::vector<std::string>& pins, std::vector<std::string>& clocks) {
    if (token.size() >= 2 && token.front() == '[' && token.back() == ']') {
        auto words = tokenize(token.substr(1, token.size()-2));
        const auto command = words.next();
        if (command == "list") {
            while (words.has_more()) parse_path_selector(words.next(), pins, clocks);
            return;
        }
        if (command == "get_clocks") {
            auto names = extract_ports(token, expand_bracket_expr(token));
            for (const auto& name : names) if (!name.empty()) clocks.push_back(name);
            return;
        }
    }
    for (const auto& name : extract_ports(token, expand_bracket_expr(token)))
        if (!name.empty()) pins.push_back(name);
}

static bool sdc_command_is_balanced(const std::string& command) {
    int bracket_depth = 0;
    int brace_depth = 0;
    bool in_quote = false;
    bool escaped = false;
    for (char c : command) {
        if (escaped) {
            escaped = false;
            continue;
        }
        if (c == '\\') {
            escaped = true;
            continue;
        }
        if (c == '"' && brace_depth == 0) {
            in_quote = !in_quote;
            continue;
        }
        if (in_quote) continue;
        if (c == '{') {
            ++brace_depth;
        } else if (c == '}') {
            --brace_depth;
        } else if (c == '[' && brace_depth == 0) {
            ++bracket_depth;
        } else if (c == ']' && brace_depth == 0) {
            --bracket_depth;
        }
        if (bracket_depth < 0 || brace_depth < 0) return false;
    }
    return bracket_depth == 0 && brace_depth == 0 && !in_quote;
}

bool SdcParser::parse_file(const std::string& filepath, ConstraintDB& constraints) {
    std::ifstream ifs(filepath);
    if (!ifs.is_open()) {
        last_error_ = "Cannot open file: " + filepath;
        return false;
    }
    std::string content((std::istreambuf_iterator<char>(ifs)),
                        std::istreambuf_iterator<char>());
    return parse_string(content, constraints);
}

namespace {
constexpr size_t static_sdc_budget = 8 * 1024 * 1024;
struct StaticSdcWord {
    enum Kind { Literal, Brace, Query } kind = Literal;
    std::string value;
};

bool static_sdc_name(const std::string& name) {
    auto first = [](char c) {
        return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_';
    };
    if (name.empty() || !first(name.front())) return false;
    return std::all_of(name.begin(), name.end(), [&](char c) {
        return first(c) || (c >= '0' && c <= '9');
    });
}

// Keep word boundaries and distinguish object handles from literal name lists.
// No command execution, recursive substitutions, or string concatenation.
bool static_sdc_words(const std::string& text, bool queries,
                      std::vector<StaticSdcWord>& words, std::string& error) {
    size_t pos = 0;
    auto fail = [&]() { error = "Unsupported dynamic or malformed static SDC word"; return false; };
    while (pos < text.size()) {
        if (std::isspace(static_cast<unsigned char>(text[pos]))) { ++pos; continue; }
        StaticSdcWord word;
        char closing = 0;
        if (text[pos] == '{') { word.kind = StaticSdcWord::Brace; closing = '}'; ++pos; }
        else if (text[pos] == '[' && queries) { word.kind = StaticSdcWord::Query; closing = ']'; ++pos; }
        const size_t start = pos;
        if (closing) {
            bool braced = false;
            while (pos < text.size()) {
                const char c = text[pos];
                if (word.kind == StaticSdcWord::Query && c == '{' && !braced) braced = true;
                else if (word.kind == StaticSdcWord::Query && c == '}' && braced) braced = false;
                else if (c == closing && !braced) break;
                else if (c == '\\' || c == '"' || c == ';' || c == '\n' || c == '\r' ||
                         (c == '$' && (word.kind != StaticSdcWord::Query || braced)) ||
                         (c == '[' && word.kind == StaticSdcWord::Query && !braced) ||
                         ((c == '{' || c == '}') && word.kind == StaticSdcWord::Query) ||
                         ((c == '{' || c == '}') && word.kind == StaticSdcWord::Brace)) return fail();
                ++pos;
            }
            if (pos == text.size()) return fail();
            word.value = text.substr(start, pos - start);
            ++pos;
            if (pos < text.size() && !std::isspace(static_cast<unsigned char>(text[pos]))) return fail();
        } else {
            while (pos < text.size() && !std::isspace(static_cast<unsigned char>(text[pos]))) {
                if (std::string("{}[]\\\";").find(text[pos]) != std::string::npos) return fail();
                ++pos;
            }
            word.value = text.substr(start, pos - start);
        }
        if (word.value.empty()) return fail();
        words.push_back(std::move(word));
        if (words.size() > 4096) { error = "Static SDC word budget exceeded"; return false; }
    }
    return true;
}

std::string static_sdc_render(const StaticSdcWord& word) {
    if (word.kind == StaticSdcWord::Brace) return "{" + word.value + "}";
    if (word.kind == StaticSdcWord::Query) return "[" + word.value + "]";
    return word.value;
}

bool static_sdc_append(std::string& out, const std::string& part, std::string& error) {
    if (part.size() > static_sdc_budget - out.size()) {
        error = "Expanded static SDC byte budget exceeded"; return false;
    }
    out += part;
    return true;
}
} // namespace

bool SdcParser::resolve_static_variables(const std::string& content, std::string& resolved) {
    last_error_.clear();
    // Keep the existing syntax path byte-for-byte when variables are absent.
    bool needed = content.find('$') != std::string::npos;
    if (!needed) {
        std::istringstream scan(content);
        std::string line;
        while (std::getline(scan, line)) {
            const auto start = line.find_first_not_of(" \t\r");
            if (start != std::string::npos && line.compare(start, 3, "set") == 0 &&
                (start + 3 == line.size() || std::isspace(static_cast<unsigned char>(line[start + 3])))) {
                // DC's write_sdc header declares the SDC format version. It
                // does not require variable substitution. Preserve the native
                // command/diagnostic path for otherwise variable-free files.
                std::istringstream declaration(line.substr(start));
                std::string command, name, version, extra;
                declaration >> command >> name >> version;
                float number = 0.f;
                if (name == "sdc_version" && parse_delay_number(version, number) &&
                    number > 0.f && !(declaration >> extra)) continue;
                needed = true; break;
            }
        }
    }
    if (!needed) { resolved = content; return true; }
    if (content.size() > static_sdc_budget) {
        last_error_ = "Static SDC input budget exceeded"; return false;
    }
    std::unordered_map<std::string, StaticSdcWord> values;
    size_t value_bytes = 0;
    auto fail = [&](const std::string& message) { last_error_ = message; return false; };
    auto canonical = [](StaticSdcWord& word) {
        if (word.kind == StaticSdcWord::Brace &&
            word.value.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:*?+%-") == std::string::npos)
            word.kind = StaticSdcWord::Literal;
    };
    auto resolve_literal = [&](StaticSdcWord& word, bool in_query) {
        if (word.kind == StaticSdcWord::Literal && word.value.find('$') != std::string::npos) {
            const auto name = word.value.substr(1);
            if (word.value.front() != '$' || !static_sdc_name(name))
                return fail("SDC variables require a complete word and a simple name");
            const auto found = values.find(name);
            if (found == values.end()) return fail("Unbound static SDC variable: " + name);
            if (in_query && found->second.kind == StaticSdcWord::Query)
                return fail("SDC collection object used as a name list");
            word = found->second;
        }
        canonical(word);
        return true;
    };
    auto resolve = [&](StaticSdcWord& word) {
        if (word.kind != StaticSdcWord::Query) return resolve_literal(word, false);
        std::vector<StaticSdcWord> args;
        if (!static_sdc_words(word.value, false, args, last_error_)) return false;
        if (args.empty() || args[0].kind != StaticSdcWord::Literal || args[0].value.find('$') != std::string::npos)
            return fail("Dynamic SDC collection command");
        const auto& cmd = args[0].value;
        const bool quiet = args.size() > 1 && args[1].value == "-quiet";
        if (cmd == "all_inputs" || cmd == "all_outputs" || cmd == "all_clocks" || cmd == "current_design") {
            if (args.size() != 1) return fail("Unsupported SDC all-collection options");
        } else if (cmd == "get_ports" || cmd == "get_pins" || cmd == "get_nets" ||
                   cmd == "get_cells" || cmd == "get_clocks") {
            const size_t name_index = quiet ? 2 : 1;
            if (args.size() != name_index + 1) return fail("SDC collection requires one static name list");
            if (!resolve_literal(args[name_index], true)) return false;
            if (args[name_index].kind == StaticSdcWord::Literal && args[name_index].value.front() == '-')
                return fail("Unsupported static SDC collection option");
        } else return fail("Unsupported static SDC collection: " + cmd);
        std::string query;
        for (size_t i = 0; i < args.size(); ++i) {
            // The native name extractor has no query option interpreter.
            // -quiet only controls query diagnostics, not the selected names.
            if (i == 1 && quiet) continue;
            if (!query.empty() && !static_sdc_append(query, " ", last_error_)) return false;
            if (!static_sdc_append(query, static_sdc_render(args[i]), last_error_)) return false;
        }
        word.value = std::move(query);
        return true;
    };
    std::string output, pending, line;
    std::istringstream input(content);
    size_t commands = 0, line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        auto end = line.find_last_not_of(" \t\r");
        const bool continued = end != std::string::npos && line[end] == '\\';
        if (continued) line.erase(end);
        if (!pending.empty() && !static_sdc_append(pending, " ", last_error_)) return false;
        if (!static_sdc_append(pending, line, last_error_)) return false;
        if (continued) continue;
        const auto start = pending.find_first_not_of(" \t\r");
        if (start != std::string::npos && pending[start] != '#') {
            if (++commands > 50000) return fail("Static SDC command budget exceeded");
            std::vector<StaticSdcWord> words;
            if (!static_sdc_words(pending, true, words, last_error_)) {
                last_error_ += " at line " + std::to_string(line_number); return false;
            }
            if (words.empty() || words[0].kind != StaticSdcWord::Literal || words[0].value.find('$') != std::string::npos)
                return fail("Dynamic SDC command name");
            const auto& cmd = words[0].value;
            if (cmd == "set") {
                if (words.size() != 3 || words[1].kind != StaticSdcWord::Literal || !static_sdc_name(words[1].value))
                    return fail("Static SDC set requires a simple name and one value");
                if (!resolve(words[2])) return false;
                auto& value = words[2];
                if (value.kind == StaticSdcWord::Query) {
                    const auto command = value.value.substr(0, value.value.find(' '));
                    if (command == "get_clocks" || command == "all_clocks")
                        return fail("Stored SDC clock collections require execution-time semantics");
                }
                const auto& name = words[1].value;
                const auto found = values.find(name);
                const size_t bytes = value.value.size() + (value.kind == StaticSdcWord::Literal ? 0 : 2);
                if (bytes > 256 * 1024 || (found == values.end() && values.size() >= 1024))
                    return fail("Static SDC variable budget exceeded");
                size_t previous_bytes = 0;
                if (found != values.end()) previous_bytes = found->second.value.size() +
                    (found->second.kind == StaticSdcWord::Literal ? 0 : 2);
                if (bytes > static_sdc_budget - (value_bytes - previous_bytes))
                    return fail("Static SDC environment budget exceeded");
                value_bytes = value_bytes - previous_bytes + bytes;
                values[name] = std::move(value);
            } else {
                // Unknown Tcl can mutate variables or stop execution (incr,
                // return, catch, etc.). Never silently skip it in this mode.
                static const std::unordered_set<std::string> supported_commands = {
                    "create_clock", "create_generated_clock", "set_clock_groups", "set_input_delay", "set_output_delay",
                    "set_max_delay", "set_min_delay", "set_load", "set_input_transition", "set_driving_cell",
                    "set_clock_latency", "set_clock_waveform", "set_clock_uncertainty",
                    "set_clock_transition", "set_data_check", "group_path",
                    "set_multicycle_path", "set_false_path", "set_disable_timing",
                    "set_case_analysis", "set_timing_derate", "set_max_fanout",
                    "set_max_capacitance", "set_max_transition", "set_units",
                    "set_propagated_clock"
                };
                if (!supported_commands.count(cmd))
                    return fail("Unsupported command in static SDC variable mode: " + cmd);
                for (size_t i = 0; i < words.size(); ++i) {
                    if (i && !resolve(words[i])) return false;
                    if (i && !static_sdc_append(output, " ", last_error_)) return false;
                    if (!static_sdc_append(output, static_sdc_render(words[i]), last_error_)) return false;
                }
            }
        }
        if (!static_sdc_append(output, "\n", last_error_)) return false;
        pending.clear();
    }
    if (!pending.empty()) return fail("Unterminated static SDC continuation");
    resolved = std::move(output);
    return true;
}

static std::string strip_sdc_comments(const std::string& input) {
    std::string output;
    output.reserve(input.size());
    bool block_comment = false;
    bool line_comment = false;
    bool in_quote = false;
    int brace_depth = 0;
    for (size_t i = 0; i < input.size(); ++i) {
        const char c = input[i];
        const char next = i + 1 < input.size() ? input[i + 1] : '\0';
        if (block_comment) {
            if (c == '*' && next == '/') { block_comment = false; ++i; }
            else if (c == '\n') output.push_back('\n');
            continue;
        }
        if (line_comment) {
            if (c == '\n') { line_comment = false; output.push_back('\n'); }
            continue;
        }
        if (!in_quote && brace_depth == 0 && c == '/' && next == '*') {
            block_comment = true;
            ++i;
            continue;
        }
        if (!in_quote && brace_depth == 0 && c == '/' && next == '/') {
            line_comment = true;
            ++i;
            continue;
        }
        if (c == '"' && brace_depth == 0) in_quote = !in_quote;
        if (!in_quote) {
            if (c == '{') ++brace_depth;
            else if (c == '}' && brace_depth > 0) --brace_depth;
        }
        output.push_back(c);
    }
    return output;
}

bool SdcParser::parse_string(const std::string& content, ConstraintDB& constraints) {
    last_error_.clear();
    warnings_.clear();
    time_scale_ns_ = 1.0f;
    capacitance_scale_pf_ = 1.0f;
    std::string resolved;
    // Strip comments before the static-variable pass as DC headers precede
    // Tcl `set`/`if` constructs and otherwise break its static tokenizer.
    if (!resolve_static_variables(strip_sdc_comments(content), resolved)) return false;
    std::istringstream stream(resolved);
    std::string line;
    std::string accumulated;
    while (std::getline(stream, line)) {
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) {
            continue;
        }
        line = line.substr(start);
        if (line[0] == '#') continue;
        if (line.empty()) continue;

        size_t last = line.find_last_not_of(" \t\r\n");
        const bool explicit_continuation =
            last != std::string::npos && line[last] == '\\';
        if (explicit_continuation) {
            line.erase(last);
        }

        if (!accumulated.empty()) accumulated += ' ';
        accumulated += line;
        if (!explicit_continuation && sdc_command_is_balanced(accumulated)) {
            if (!parse_line(accumulated, constraints)) return false;
            accumulated.clear();
        }
    }
    if (!accumulated.empty()) {
        if (!sdc_command_is_balanced(accumulated)) {
            last_error_ = "Unterminated bracket, brace, or quote in SDC command: " +
                          accumulated;
            return false;
        }
        if (!parse_line(accumulated, constraints)) return false;
    }
    return constraints.resolve_generated_clocks(last_error_);
}

bool SdcParser::parse_line(const std::string& line, ConstraintDB& constraints) {
    auto tokens = tokenize(line);
    if (!tokens.has_more()) return true;

    std::string cmd = tokens.next();

    if (cmd == "create_clock") {
        ClockDef clock;
        clock.name = "clk_auto";

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-name") {
                clock.name = tokens.next();
                if (clock.name.size() >= 2 && clock.name.front() == '{' && clock.name.back() == '}')
                    clock.name = clock.name.substr(1, clock.name.size() - 2);
            } else if (t == "-period") {
                if (!parse_time_number(tokens.next(), clock.period_ns)) {
                    last_error_ = "Invalid period value"; return false;
                }
            } else if (t == "-waveform") {
                std::string wf = expand_bracket_expr(tokens.next());
                // Parse "{rise fall}" or "rise fall"
                wf.erase(std::remove(wf.begin(), wf.end(), '{'), wf.end());
                wf.erase(std::remove(wf.begin(), wf.end(), '}'), wf.end());
                std::istringstream wss(wf);
                std::string rise, fall;
                wss >> rise >> fall;
                if (!parse_time_number(rise, clock.rise_edge_ns) ||
                    !parse_time_number(fall, clock.fall_edge_ns)) {
                    last_error_ = "Invalid clock waveform value"; return false;
                }
                clock.waveform_explicit = true;
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                clock.source_port = expand_bracket_expr(t);
                clock.source_is_pin = tokenize(t.substr(1, t.size() - 2)).next() == "get_pins";
                if (clock.source_port.size() >= 2 && clock.source_port.front() == '{' && clock.source_port.back() == '}')
                    clock.source_port = clock.source_port.substr(1, clock.source_port.size() - 2);
            } else if (t[0] != '-' && !t.empty() && std::isalpha(t[0])) {
                clock.source_port = t;
            }
        }

        if (clock.name == "clk_auto" && !clock.source_port.empty()) {
            clock.name = clock.source_port;
        }
        if (!clock.waveform_explicit && clock.period_ns > 0) {
            clock.rise_edge_ns = 0.0f;
            clock.fall_edge_ns = clock.period_ns / 2.0f;
        }
        constraints.add_clock(std::move(clock));
    }
    else if (cmd == "create_generated_clock") {
        ClockDef clock;
        clock.generated.emplace();
        auto& def = *clock.generated;
        auto fail = [&](const std::string& reason) { last_error_ = "create_generated_clock: " + reason; return false; };
        auto unquote = [](std::string text) {
            if (text.size() >= 2 && ((text.front() == '{' && text.back() == '}') ||
                                      (text.front() == '"' && text.back() == '"')))
                text = text.substr(1, text.size() - 2);
            return text;
        };
        auto exact_name = [&](std::string text, std::string& name) {
            text = unquote(text);
            std::istringstream list(text);
            std::string extra;
            if (!(list >> name) || (list >> extra)) return false;
            if (name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:[]-") != std::string::npos)
                return false;
            // Braced bus bits are literal names, never glob selectors.
            for (size_t pos = 0; pos < name.size(); ++pos) {
                if (name[pos] == ']') return false;
                if (name[pos] != '[') continue;
                ++pos;
                if (pos < name.size() && name[pos] == '-') ++pos;
                const size_t start = pos;
                while (pos < name.size() && std::isdigit(static_cast<unsigned char>(name[pos]))) ++pos;
                if (pos == start || pos == name.size() || name[pos] != ']') return false;
            }
            return true;
        };
        auto object = [&](const std::string& text, std::string& name, bool& pin, bool clock_object = false) {
            if (text.empty()) return false;
            if (text.front() != '[') {
                if (!exact_name(text, name)) return false;
                pin = name.find('/') != std::string::npos;
                return true;
            }
            if (text.back() != ']') return false;
            auto args = tokenize(text.substr(1, text.size() - 2));
            const auto query = args.next();
            if (clock_object ? query != "get_clocks" : (query != "get_ports" && query != "get_pins")) return false;
            pin = query == "get_pins";
            auto selector = args.next();
            if (selector == "-quiet") selector = args.next();
            if (args.has_more() || !exact_name(selector, name)) return false;
            return clock_object || (pin == (name.find('/') != std::string::npos));
        };
        auto integer = [&](const std::string& text, uint32_t& number) {
            if (text.empty() || !std::all_of(text.begin(), text.end(), [](char c) { return c >= '0' && c <= '9'; })) return false;
            try {
                const auto value = std::stoull(text);
                if (!value || value > 2147483647) return false;
                number = static_cast<uint32_t>(value); return true;
            } catch (...) { return false; }
        };
        std::unordered_set<std::string> seen;
        while (tokens.has_more()) {
            const auto option = tokens.next();
            if (!option.empty() && option.front() == '-') {
                if (!seen.insert(option).second) return fail("duplicate option " + option);
                if (option == "-invert") def.invert = true;
                else if (option == "-combinational") def.combinational = true;
                else if (option == "-name") {
                    if (!exact_name(tokens.next(), clock.name)) return fail("needs one literal clock name");
                } else if (option == "-source") {
                    if (!object(tokens.next(), def.source, def.source_is_pin)) return fail("source needs one exact port or pin");
                } else if (option == "-master_clock") {
                    bool ignored = false;
                    if (!object(tokens.next(), def.master_clock, ignored, true)) return fail("needs one exact master clock");
                } else if (option == "-divide_by" || option == "-multiply_by") {
                    if (!integer(tokens.next(), option == "-divide_by" ? def.divide_by : def.multiply_by))
                        return fail("ratio must be a positive 32-bit integer");
                } else if (option == "-duty_cycle") {
                    if (!parse_delay_number(tokens.next(), def.duty_cycle) || def.duty_cycle <= 0 || def.duty_cycle >= 100)
                        return fail("duty cycle must be strictly between 0 and 100");
                } else if (option == "-edges" || option == "-edge_shift") {
                    std::istringstream list(unquote(tokens.next()));
                    std::string value;
                    while (list >> value) {
                        if (option == "-edges") {
                            uint32_t index;
                            if (!integer(value, index) || def.edges.size() == 3) return fail("needs three positive edge indices");
                            def.edges.push_back(index);
                        } else {
                            float shift;
                            if (!parse_time_number(value, shift) || def.edge_shifts_ns.size() == 3) return fail("needs three finite edge shifts");
                            def.edge_shifts_ns.push_back(shift);
                        }
                    }
                    if ((option == "-edges" ? def.edges.size() : def.edge_shifts_ns.size()) != 3)
                        return fail("edge lists need exactly three values");
                } else return fail("unsupported option " + option);
            } else {
                if (!clock.source_port.empty() || !object(option, clock.source_port, clock.source_is_pin))
                    return fail("target needs one exact port or pin");
            }
        }
        if (def.source.empty() || clock.source_port.empty()) return fail("source and target are required");
        if (clock.name.empty()) clock.name = clock.source_port;
        if (def.combinational && !def.divide_by) def.divide_by = 1;
        for (const auto& existing : constraints.clocks()) {
            if (existing.name != clock.name && existing.source_port == clock.source_port && existing.source_is_pin == clock.source_is_pin)
                return fail("multiple clocks on a generated target are unsupported");
        }
        auto updated = constraints;
        updated.add_clock(std::move(clock));
        if (!updated.resolve_generated_clocks(last_error_)) return false;
        constraints = std::move(updated);
    }
    else if (cmd == "set_propagated_clock") {
        bool applied = false;
        while (tokens.has_more()) {
            const std::string token = tokens.next();
            if (token == "-quiet") continue;
            const auto names = extract_ports(token, expand_bracket_expr(token));
            for (const auto& name : names) {
                if (!name.empty()) {
                    constraints.set_clock_propagated(name, true);
                    applied = true;
                }
            }
        }
        if (!applied) {
            last_error_ = "set_propagated_clock requires one or more clocks";
            return false;
        }
    }
    else if (cmd == "set_clock_groups") {
        ClockGroupDef group_def;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-asynchronous") {
                group_def.mode = ClockGroupDef::Mode::Asynchronous;
            } else if (t == "-logically_exclusive") {
                group_def.mode = ClockGroupDef::Mode::LogicallyExclusive;
            } else if (t == "-physically_exclusive") {
                group_def.mode = ClockGroupDef::Mode::PhysicallyExclusive;
            } else if (t == "-group") {
                if (!tokens.has_more()) break;
                std::string group_tok = tokens.next();
                std::string expanded = expand_bracket_expr(group_tok);
                auto clocks = extract_ports(group_tok, expanded);
                clocks.erase(
                    std::remove_if(clocks.begin(), clocks.end(),
                                   [](const std::string& name) { return name.empty(); }),
                    clocks.end());
                if (!clocks.empty()) {
                    group_def.groups.push_back(std::move(clocks));
                }
            } else if (t == "-name" || t == "-comment") {
                if (tokens.has_more()) tokens.next();
            } else if (t[0] == '-') {
                // Skip unknown flags.
            }
        }

        constraints.add_clock_group(std::move(group_def));
    }
    else if (cmd == "set_input_delay" || cmd == "set_output_delay") {
        IoDelay delay;
        delay.is_input = (cmd == "set_input_delay");
        std::string clock_name;
        bool delay_assigned = false;
        bool min_max_explicit = false;
        bool transition_explicit = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-clock") {
                const auto selector = tokens.next();
                const auto clocks = extract_ports(selector, expand_bracket_expr(selector));
                if (clocks.size() != 1 || clocks.front().empty()) {
                    last_error_ = "I/O delay requires one reference clock"; return false;
                }
                clock_name = clocks.front();
            } else if (t == "-max") {
                delay.is_max = true;
                min_max_explicit = true;
            } else if (t == "-min") {
                delay.is_max = false;
                min_max_explicit = true;
            } else if (t == "-add_delay" || t == "-network_latency_included"
                       || t == "-source_latency_included") {
                // Skip optional flags
            } else if (t == "-rise" || t == "-fall") {
                delay.clock_edge = (t == "-rise") ? Transition::Rise : Transition::Fall;
                transition_explicit = true;
            } else if (t[0] == '-' && !negative_number_token(t)) {
                // Unknown flag, skip
            } else if (!delay_assigned) {
                if (!parse_time_number(t, delay.delay_ns)) {
                    last_error_ = "Invalid delay value in " + cmd; return false;
                }
                delay_assigned = true;
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                std::string expanded = expand_bracket_expr(t);
                delay.port_names = extract_ports(t, expanded);
            } else {
                delay.port_names.push_back(t);
            }
        }
        if (!delay_assigned) { last_error_ = "Missing delay value in " + cmd; return false; }
        delay.clock_name = clock_name;
        std::vector<IoDelay> analysis_delays;
        if (min_max_explicit) {
            analysis_delays.push_back(delay);
        } else {
            IoDelay max_delay = delay;
            max_delay.is_max = true;
            IoDelay min_delay = delay;
            min_delay.is_max = false;
            analysis_delays.push_back(std::move(max_delay));
            analysis_delays.push_back(std::move(min_delay));
        }
        for (const auto& analysis_delay : analysis_delays) {
            if (transition_explicit) {
                constraints.add_io_delay(analysis_delay);
                continue;
            }
            IoDelay rise_delay = analysis_delay;
            rise_delay.clock_edge = Transition::Rise;
            IoDelay fall_delay = analysis_delay;
            fall_delay.clock_edge = Transition::Fall;
            constraints.add_io_delay(std::move(rise_delay));
            constraints.add_io_delay(std::move(fall_delay));
        }
    }
    else if (cmd == "set_max_delay" || cmd == "set_min_delay") {
        PathDelay pd;
        pd.is_max = (cmd == "set_max_delay");
        bool delay_assigned = false;
        bool seen_from = false, seen_to = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-from") {
                seen_from = true;
                std::string from_tok = tokens.next();
                parse_path_selector(from_tok, pd.from_pins, pd.from_clocks);
            } else if (t == "-to") {
                seen_to = true;
                std::string to_tok = tokens.next();
                parse_path_selector(to_tok, pd.to_pins, pd.to_clocks);
            } else if (t == "-through") {
                std::string th_tok = tokens.next();
                std::string expanded = expand_bracket_expr(th_tok);
                auto ports = extract_ports(th_tok, expanded);
                if (ports.empty()) { last_error_ = "Empty -through selector in " + cmd; return false; }
                if (pd.through_pins.empty()) pd.through_pins = std::move(ports);
                else pd.through_stages.push_back(std::move(ports));
            } else if (t == "-datapath_only") {
                // Skip
            } else if (t == "-ignore_clock_latency") {
                pd.ignore_clock_latency = true;
            } else if (t[0] == '-' && !negative_number_token(t)) {
                // Unknown flag
            } else if (!delay_assigned) {
                if (!parse_time_number(t, pd.delay_ns)) {
                    last_error_ = "Invalid delay value in " + cmd; return false;
                }
                delay_assigned = true;
            }
        }
        if (!delay_assigned) { last_error_ = "Missing delay value in " + cmd; return false; }
        if ((seen_from && pd.from_pins.empty() && pd.from_clocks.empty()) ||
            (seen_to && pd.to_pins.empty() && pd.to_clocks.empty()) ||
            (!pd.from_pins.empty() && !pd.from_clocks.empty()) ||
            (!pd.to_pins.empty() && !pd.to_clocks.empty())) {
            last_error_ = "Empty or mixed pin/clock selector in " + cmd; return false;
        }
        constraints.add_path_delay(std::move(pd));
    }
    else if (cmd == "set_load") {
        SetLoadDef sl;
        bool cap_assigned = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t[0] == '[' || starts_with(t, "[get_")) {
                std::string expanded = expand_bracket_expr(t);
                sl.pin_names = extract_ports(t, expanded);
            } else if (t[0] == '-') {
                // Skip flags like -pin_load
            } else if (!cap_assigned) {
                if (!parse_capacitance_number(t, sl.capacitance_pf)) {
                    last_error_ = "Invalid capacitance value"; return false;
                }
                cap_assigned = true;
            } else {
                sl.pin_names.push_back(t);
            }
        }
        constraints.add_set_load(std::move(sl));
    }
    else if (cmd == "set_input_transition") {
        InputTransitionDef it;
        bool trans_assigned = false;
        bool transition_selected = false;
        bool analysis_selected = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t[0] == '[' || starts_with(t, "[get_")) {
                std::string expanded = expand_bracket_expr(t);
                it.port_names = extract_ports(t, expanded);
            } else if (t == "-rise" || t == "-fall") {
                if (!transition_selected) it.rise = it.fall = false;
                transition_selected = true;
                if (t == "-rise") it.rise = true; else it.fall = true;
            } else if (t == "-min" || t == "-max") {
                if (!analysis_selected) it.min = it.max = false;
                analysis_selected = true;
                if (t == "-min") it.min = true; else it.max = true;
            } else if (t[0] == '-') {
                // Skip flags
            } else if (!trans_assigned) {
                if (!parse_time_number(t, it.transition_ns)) {
                    last_error_ = "Invalid transition value"; return false;
                }
                trans_assigned = true;
            } else {
                it.port_names.push_back(t);
            }
        }
        constraints.add_input_transition(std::move(it));
    }
    else if (cmd == "set_driving_cell") {
        DrivingCellDef driver;
        bool rf_selected = false, mm_selected = false;
        while (tokens.has_more()) {
            const std::string t = tokens.next();
            if (t == "-lib_cell" || t == "-library" || t == "-pin" || t == "-from_pin" ||
                t == "-input_transition_rise" || t == "-input_transition_fall") {
                if (!tokens.has_more()) { last_error_ = "Missing set_driving_cell option value: " + t; return false; }
                const auto value = tokens.next();
                if (t == "-lib_cell") driver.cell = value;
                else if (t == "-library") driver.library = value;
                else if (t == "-pin") driver.pin = value;
                else if (t == "-from_pin") driver.from_pin = value;
                else {
                    float ns = 0.f;
                    if (!parse_time_number(value, ns) || ns < 0.f) {
                        last_error_ = "Invalid set_driving_cell input transition"; return false;
                    }
                    if (t == "-input_transition_rise") driver.input_transition_rise_ns = ns;
                    else driver.input_transition_fall_ns = ns;
                }
            } else if (t == "-rise" || t == "-fall") {
                if (!rf_selected) driver.rise = driver.fall = false;
                rf_selected = true;
                if (t == "-rise") driver.rise = true; else driver.fall = true;
            } else if (t == "-min" || t == "-max") {
                if (!mm_selected) driver.min = driver.max = false;
                mm_selected = true;
                if (t == "-min") driver.min = true; else driver.max = true;
            } else if (t == "-no_design_rule") driver.no_design_rule = true;
            else if (t == "-dont_scale") driver.dont_scale = true;
            else if (t[0] == '-') {
                last_error_ = "Unsupported set_driving_cell option: " + t; return false;
            } else {
                auto ports = extract_ports(t, expand_bracket_expr(t));
                driver.port_names.insert(driver.port_names.end(), ports.begin(), ports.end());
            }
        }
        if (driver.cell.empty() || driver.port_names.empty()) {
            last_error_ = "set_driving_cell requires -lib_cell and input ports"; return false;
        }
        constraints.add_driving_cell(std::move(driver));
    }
    else if (cmd == "set_clock_latency") {
        ClockLatencyDef cl;
        bool lat_assigned = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-source" || t == "-early" || t == "-late") {
                // Skip optional flags
            } else if (t[0] == '-') {
                // Skip unknown flags
            } else if (!lat_assigned) {
                if (!parse_time_number(t, cl.latency_ns)) {
                    last_error_ = "Invalid latency value"; return false;
                }
                lat_assigned = true;
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                std::string expanded = expand_bracket_expr(t);
                cl.pin_names = extract_ports(t, expanded);
            } else {
                // Could be clock name or pin name
                if (cl.clock_name.empty()) {
                    cl.clock_name = t;
                } else {
                    cl.pin_names.push_back(t);
                }
            }
        }
        constraints.add_clock_latency(std::move(cl));
    }
    else if (cmd == "set_clock_waveform") {
        // set_clock_waveform -name <clock> -edges {rise fall}
        // or set_clock_waveform <clock> {rise fall}
        std::string clock_name;
        float rise = 0, fall = 0;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-name") {
                clock_name = tokens.next();
            } else if (t == "-edges" || t == "-waveform") {
                std::string wf = expand_bracket_expr(tokens.next());
                wf.erase(std::remove(wf.begin(), wf.end(), '{'), wf.end());
                wf.erase(std::remove(wf.begin(), wf.end(), '}'), wf.end());
                std::istringstream wss(wf);
                std::string rise_token, fall_token;
                wss >> rise_token >> fall_token;
                if (!parse_time_number(rise_token, rise) ||
                    !parse_time_number(fall_token, fall)) {
                    last_error_ = "Invalid clock waveform value"; return false;
                }
            } else if (t[0] == '-') {
                // Skip
            } else if (clock_name.empty()) {
                clock_name = t;
            }
        }
        if (!clock_name.empty()) {
            constraints.set_clock_waveform(clock_name, rise, fall);
        }
    }
    else if (cmd == "set_clock_transition") {
        float transition = 0.0f;
        bool assigned = false;
        std::vector<std::string> clock_names;
        while (tokens.has_more()) {
            const std::string t = tokens.next();
            if (t == "-rise" || t == "-fall" || t == "-min" || t == "-max") {
                // The resolved clock model has one source slew.  Keep the
                // command edge/analysis qualifiers accepted while applying
                // the value to the clock object selected by the command.
                continue;
            }
            if (t[0] == '[' || starts_with(t, "[get_")) {
                const auto names = extract_ports(t, expand_bracket_expr(t));
                clock_names.insert(clock_names.end(), names.begin(), names.end());
            } else if (!assigned) {
                if (!parse_time_number(t, transition) || transition < 0.0f) {
                    last_error_ = "Invalid clock transition value";
                    return false;
                }
                assigned = true;
            } else {
                clock_names.push_back(t);
            }
        }
        if (!assigned || clock_names.empty()) {
            last_error_ = "set_clock_transition requires a value and clock selector";
            return false;
        }
        bool applied = false;
        for (const auto& name : clock_names) {
            applied = constraints.set_clock_transition(name, transition) || applied;
        }
        if (!applied) {
            last_error_ = "set_clock_transition references an unknown clock";
            return false;
        }
    }
    else if (cmd == "set_data_check") {
        DataCheckDef check;
        bool assigned = false;
        while (tokens.has_more()) {
            const std::string t = tokens.next();
            if (t == "-from" || t == "-rise_from" || t == "-fall_from") {
                check.from_transitions = t == "-rise_from" ? 1 : t == "-fall_from" ? 2 : 3;
                if (!tokens.has_more()) { last_error_ = "Missing -from value in set_data_check"; return false; }
                const auto selector = tokens.next();
                check.from_pins = extract_ports(selector, expand_bracket_expr(selector));
            } else if (t == "-to" || t == "-rise_to" || t == "-fall_to") {
                check.to_transitions = t == "-rise_to" ? 1 : t == "-fall_to" ? 2 : 3;
                if (!tokens.has_more()) { last_error_ = "Missing -to value in set_data_check"; return false; }
                const auto selector = tokens.next();
                check.to_pins = extract_ports(selector, expand_bracket_expr(selector));
            } else if (t == "-setup") {
                check.is_setup = true;
            } else if (t == "-hold") {
                check.is_setup = false;
            } else if (t == "-clock") {
                if (tokens.has_more()) tokens.next();
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                check.to_pins = extract_ports(t, expand_bracket_expr(t));
            } else if (!assigned && t[0] != '-') {
                if (!parse_time_number(t, check.delay_ns)) {
                    last_error_ = "Invalid data check value";
                    return false;
                }
                assigned = true;
            } else if (t[0] != '-') {
                check.to_pins.push_back(t);
            }
        }
        if (!assigned) {
            last_error_ = "set_data_check requires a delay value";
            return false;
        }
        constraints.add_data_check(std::move(check));
    }
    else if (cmd == "group_path") {
        PathGroupDef group;
        while (tokens.has_more()) {
            const std::string t = tokens.next();
            if (t == "-name") {
                if (!tokens.has_more()) { last_error_ = "Missing name in group_path"; return false; }
                group.name = tokens.next();
                if (group.name.size() >= 2 &&
                    ((group.name.front() == '{' && group.name.back() == '}') ||
                     (group.name.front() == '"' && group.name.back() == '"')))
                    group.name = group.name.substr(1, group.name.size() - 2);
            } else if (t == "-weight") {
                if (!tokens.has_more()) { last_error_ = "Missing group_path weight"; return false; }
                const auto value = tokens.next();
                size_t used = 0;
                try { group.weight = std::stof(value, &used); }
                catch (...) { last_error_ = "Invalid group_path weight"; return false; }
                if (used != value.size() || !std::isfinite(group.weight) || group.weight < 0 || group.weight > 100) {
                    last_error_ = "group_path weight must be in [0,100]"; return false;
                }
                group.weight_explicit = true;
            } else if (t == "-from" || t == "-through" || t == "-to" ||
                       t == "-rise_from" || t == "-fall_from" || t == "-rise_to" ||
                       t == "-fall_to" || t == "-rise_through" || t == "-fall_through") {
                if (!tokens.has_more()) { last_error_ = "Missing selector in group_path"; return false; }
                const auto selector = tokens.next();
                const bool clocks = selector.rfind("[get_clocks", 0) == 0;
                const auto pins = extract_ports(selector, expand_bracket_expr(selector));
                if (pins.empty() || std::all_of(pins.begin(), pins.end(),
                        [](const auto& name) { return name.empty(); })) {
                    last_error_ = "Empty selector in group_path"; return false;
                }
                const uint8_t mask = t.rfind("-rise_", 0) == 0 ? 1 : t.rfind("-fall_", 0) == 0 ? 2 : 3;
                if (t == "-from" || t.find("_from") != std::string::npos) {
                    (clocks ? group.from_clocks : group.from_pins) = pins;
                    group.from_transitions = mask;
                } else if (t == "-through" || t.find("_through") != std::string::npos) {
                    if (clocks) { last_error_ = "group_path -through requires pins/ports"; return false; }
                    if (group.through_pins.empty()) { group.through_pins = pins; group.through_transitions = mask; }
                    else { group.through_stages.push_back(pins); group.through_stage_transitions.push_back(mask); }
                } else {
                    (clocks ? group.to_clocks : group.to_pins) = pins;
                    group.to_transitions = mask;
                }
            } else if (!t.empty() && t[0] != '-') {
                if (group.name.empty()) group.name = t;
                else { last_error_ = "Unexpected argument in group_path: " + t; return false; }
            } else {
                last_error_ = "Unsupported group_path option: " + t;
                return false;
            }
        }
        if (group.name.empty()) {
            last_error_ = "group_path requires a name";
            return false;
        }
        constraints.add_path_group(std::move(group));
    }
    else if (cmd == "set_clock_uncertainty") {
        ClockUncertaintyDef cu;
        enum class UncertaintyMode { Both, Setup, Hold };
        UncertaintyMode mode = UncertaintyMode::Both;
        bool val_assigned = false;
        float uncertainty = 0.0f;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-setup") {
                mode = UncertaintyMode::Setup;
            } else if (t == "-hold") {
                mode = UncertaintyMode::Hold;
            } else if (t == "-from" || t == "-to") {
                cu.clock_name = expand_bracket_expr(tokens.next());
            } else if (t[0] == '-') {
                // Skip
            } else if (!val_assigned) {
                if (!parse_time_number(t, uncertainty)) {
                    last_error_ = "Invalid uncertainty value"; return false;
                }
                val_assigned = true;
            } else if (cu.clock_name.empty()) {
                cu.clock_name = expand_bracket_expr(t);
            }
        }
        if (!cu.clock_name.empty()) {
            const auto clocks = extract_ports(cu.clock_name, cu.clock_name);
            if (clocks.size() != 1 || clocks.front().empty()) {
                last_error_ = "Clock uncertainty requires one reference clock"; return false;
            }
            cu.clock_name = clocks.front();
        }
        if (mode != UncertaintyMode::Hold) {
            cu.setup_uncertainty_ns = uncertainty;
        }
        if (mode != UncertaintyMode::Setup) {
            cu.hold_uncertainty_ns = uncertainty;
        }
        constraints.set_clock_uncertainty(std::move(cu));
    }
    else if (cmd == "set_multicycle_path") {
        MulticyclePathDef mcp;
        bool cycles_assigned = false;
        bool is_setup = true;
        int cycles = 1;
        bool end_explicit = false;
        bool seen_from = false, seen_to = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-setup") {
                is_setup = true;
            } else if (t == "-hold") {
                is_setup = false;
            } else if (t == "-start" || t == "-end") {
                mcp.use_start = t == "-start";
                end_explicit = true;
            } else if (t == "-from") {
                seen_from = true;
                std::string from_tok = tokens.next();
                parse_path_selector(from_tok, mcp.from_pins, mcp.from_clocks);
            } else if (t == "-to") {
                seen_to = true;
                std::string to_tok = tokens.next();
                parse_path_selector(to_tok, mcp.to_pins, mcp.to_clocks);
            } else if (t[0] == '-') {
                // Skip
            } else if (!cycles_assigned) {
                try {
                    size_t used = 0;
                    cycles = std::stoi(t, &used);
                    if (used != t.size() || cycles < 0) throw std::invalid_argument("cycles");
                    cycles_assigned = true;
                }
                catch (...) { last_error_ = "Invalid cycle count"; return false; }
            }
        }
        if (!cycles_assigned || (is_setup && cycles == 0)) {
            last_error_ = "Missing or invalid multicycle count"; return false;
        }
        mcp.is_hold = !is_setup;
        if (!end_explicit) mcp.use_start = !is_setup;
        if (is_setup) mcp.setup_cycles = cycles;
        else mcp.hold_cycles = cycles;
        if ((seen_from && mcp.from_pins.empty() && mcp.from_clocks.empty()) ||
            (seen_to && mcp.to_pins.empty() && mcp.to_clocks.empty()) ||
            (!mcp.from_pins.empty() && !mcp.from_clocks.empty()) ||
            (!mcp.to_pins.empty() && !mcp.to_clocks.empty())) {
            last_error_ = "Empty or mixed pin/clock selector in set_multicycle_path"; return false;
        }
        constraints.add_multicycle_path(std::move(mcp));
    }
    else if (cmd == "set_false_path") {
        FalsePathDef fp;
        bool seen_from = false, seen_to = false, seen_through = false;
        bool seen_analysis = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-from" || t == "-rise_from" || t == "-fall_from") {
                if (seen_from) { last_error_ = "Repeated -from in set_false_path"; return false; }
                seen_from = true;
                fp.from_transitions = t == "-rise_from" ? 1 : t == "-fall_from" ? 2 : 3;
                std::string from_tok = tokens.next();
                if (from_tok.empty() || from_tok[0] == '-') { last_error_ = "Missing -from value in set_false_path"; return false; }
                parse_path_selector(from_tok, fp.from_pins, fp.from_clocks);
            } else if (t == "-to" || t == "-rise_to" || t == "-fall_to") {
                if (seen_to) { last_error_ = "Repeated -to in set_false_path"; return false; }
                seen_to = true;
                fp.to_transitions &= t == "-rise_to" ? 1 : t == "-fall_to" ? 2 : 3;
                std::string to_tok = tokens.next();
                if (to_tok.empty() || to_tok[0] == '-') { last_error_ = "Missing -to value in set_false_path"; return false; }
                parse_path_selector(to_tok, fp.to_pins, fp.to_clocks);
            } else if (t == "-through" || t == "-rise_through" || t == "-fall_through") {
                std::string th_tok = tokens.next();
                if (th_tok.empty() || th_tok[0] == '-') { last_error_ = "Missing -through value in set_false_path"; return false; }
                std::string expanded = expand_bracket_expr(th_tok);
                auto pins = extract_ports(th_tok, expanded);
                const uint8_t mask = t == "-rise_through" ? 1 : t == "-fall_through" ? 2 : 3;
                if (seen_through) {
                    fp.through_stages.push_back(std::move(pins));
                    fp.through_stage_transitions.push_back(mask);
                } else { fp.through_pins = std::move(pins); fp.through_transitions = mask; }
                seen_through = true;
            } else if (t == "-rise" || t == "-fall") {
                fp.to_transitions &= t == "-rise" ? 1 : 2;
            } else if (t == "-setup" || t == "-hold") {
                if (!seen_analysis) { fp.setup = false; fp.hold = false; seen_analysis = true; }
                if (t == "-setup") fp.setup = true;
                else fp.hold = true;
            } else {
                last_error_ = "Unsupported option in set_false_path: " + t; return false;
            }
        }
        const auto empty_selector = [](const auto& pins) {
            return pins.empty() || std::any_of(pins.begin(), pins.end(), [](const auto& pin) { return pin.empty(); });
        };
        if (fp.to_transitions == 0 || (!seen_from && !seen_to && !seen_through) ||
            (!fp.from_pins.empty() && !fp.from_clocks.empty()) ||
            (!fp.to_pins.empty() && !fp.to_clocks.empty()) ||
            (seen_from && empty_selector(fp.from_pins) && fp.from_clocks.empty()) ||
            (seen_to && empty_selector(fp.to_pins) && fp.to_clocks.empty()) ||
            (seen_through && empty_selector(fp.through_pins)) ||
            std::any_of(fp.through_stages.begin(), fp.through_stages.end(), empty_selector)) {
            last_error_ = "Empty path selector in set_false_path"; return false;
        }
        constraints.add_false_path(std::move(fp));
    }
    else if (cmd == "set_disable_timing") {
        DisableTimingDef dt;
        std::vector<std::string> cells;
        bool pin_options = false;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-from") {
                pin_options = true;
                dt.from_pin = expand_bracket_expr(tokens.next());
            } else if (t == "-to") {
                pin_options = true;
                dt.to_pin = expand_bracket_expr(tokens.next());
            } else if (starts_with(t, "[get_cells")) {
                cells = extract_ports(t, expand_bracket_expr(t));
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                dt.from_pin = expand_bracket_expr(t);
            } else if (t[0] != '-') {
                if (pin_options) cells.push_back(t);
                else if (dt.from_pin.empty()) dt.from_pin = t;
                else dt.to_pin = t;
            }
        }
        if (!cells.empty() && pin_options) {
            for (const auto& cell : cells) {
                DisableTimingDef resolved;
                if (!dt.from_pin.empty()) resolved.from_pin = cell + "/" + dt.from_pin;
                if (!dt.to_pin.empty()) resolved.to_pin = cell + "/" + dt.to_pin;
                constraints.add_disable_timing(std::move(resolved));
            }
        } else {
            if (!cells.empty()) dt.from_pin = cells.front();
            constraints.add_disable_timing(std::move(dt));
        }
    }
    else if (cmd == "set_case_analysis") {
        CaseAnalysisDef ca;

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "0" || t == "zero") {
                ca.value = CaseAnalysisDef::Zero;
            } else if (t == "1" || t == "one") {
                ca.value = CaseAnalysisDef::One;
            } else if (t == "rising" || t == "rise") {
                ca.value = CaseAnalysisDef::Rise;
            } else if (t == "falling" || t == "fall") {
                ca.value = CaseAnalysisDef::Fall;
            } else if (t[0] == '[' || starts_with(t, "[get_")) {
                ca.pin_name = expand_bracket_expr(t);
            } else if (t[0] != '-') {
                ca.pin_name = t;
            }
        }
        constraints.add_case_analysis(std::move(ca));
    }
    else if (cmd == "set_timing_derate") {
        // set_timing_derate -early <val> -late <val> [-clock|-data]
        OcvDerateDef derate = constraints.ocv_derate();
        float early_value = 1.0f, late_value = 1.0f;
        bool set_early = false, set_late = false, got_value = false;
        bool early_literal = false, late_literal = false;
        std::optional<float> positional_value;
        bool is_clock = false;
        auto read_derate = [&](const std::string& token, float& value) {
            size_t consumed = 0;
            try { value = std::stof(token, &consumed); }
            catch (...) { return false; }
            return consumed == token.size() && std::isfinite(value) && value >= 0;
        };

        while (tokens.has_more()) {
            std::string t = tokens.next();
            if (t == "-early") {
                set_early = true;
                if (tokens.has_more() && tokens.peek()[0] != '-') {
                    if (!read_derate(tokens.next(), early_value)) { last_error_ = "Invalid derate value"; return false; }
                    early_literal = got_value = true;
                }
            } else if (t == "-late") {
                set_late = true;
                if (tokens.has_more() && tokens.peek()[0] != '-') {
                    if (!read_derate(tokens.next(), late_value)) { last_error_ = "Invalid derate value"; return false; }
                    late_literal = got_value = true;
                }
            } else if (t == "-clock" || t == "-clock_delay") {
                is_clock = true;
            } else if (t == "-data" || t == "-data_delay") {
                is_clock = false;
            } else if (t[0] == '-') {
                last_error_ = "Unsupported timing derate qualifier: " + t; return false;
            } else {
                float value;
                if (positional_value || !read_derate(t, value)) { last_error_ = "Invalid derate value"; return false; }
                positional_value = value; got_value = true;
            }
        }
        if (!set_early && !set_late) set_early = set_late = true;
        if (positional_value) {
            if (set_early && !early_literal) early_value = *positional_value;
            if (set_late && !late_literal) late_value = *positional_value;
        }
        // A single canonical value applies to both selected analyses, even
        // when it follows -early/-late directly. Keep the historical two-value
        // spelling while making the canonical command option-order independent.
        if (set_early && set_late && !positional_value) {
            if (early_literal && !late_literal) late_value = early_value;
            if (late_literal && !early_literal) early_value = late_value;
        }
        if (!got_value || !std::isfinite(early_value) || !std::isfinite(late_value) || early_value < 0 || late_value < 0) {
            last_error_ = "Invalid or missing timing derate value"; return false;
        }
        if (is_clock) {
            if (set_early) derate.early_clock = early_value;
            if (set_late) derate.late_clock = late_value;
        } else {
            if (set_early) derate.early_data = early_value;
            if (set_late) derate.late_data = late_value;
        }
        constraints.set_ocv_derate(derate);
    }
    else if (cmd == "set_max_fanout") {
        if (tokens.has_more()) {
            try { constraints.set_max_fanout(std::stof(tokens.next())); }
            catch (...) { last_error_ = "Invalid fanout value"; return false; }
        }
        if (tokens.has_more()) tokens.next(); // skip port
    }
    else if (cmd == "set_max_capacitance") {
        if (tokens.has_more()) {
            float value = 0.0f;
            if (!parse_capacitance_number(tokens.next(), value)) {
                last_error_ = "Invalid capacitance value"; return false;
            }
            constraints.set_max_capacitance(value);
        }
        if (tokens.has_more()) tokens.next();
    }
    else if (cmd == "set_max_transition") {
        if (tokens.has_more()) {
            float value = 0.0f;
            if (!parse_time_number(tokens.next(), value)) {
                last_error_ = "Invalid transition value"; return false;
            }
            constraints.set_max_transition(value);
        }
        if (tokens.has_more()) tokens.next();
    }
    else if (cmd == "set_units") {
        auto time_scale = [](const std::string& unit) -> float {
            if (unit == "s") return 1.0e9f;
            if (unit == "ms") return 1.0e6f;
            if (unit == "us") return 1.0e3f;
            if (unit == "ns") return 1.0f;
            if (unit == "ps") return 1.0e-3f;
            if (unit == "fs") return 1.0e-6f;
            return -1.0f;
        };
        auto capacitance_scale = [](const std::string& unit) -> float {
            if (unit == "F") return 1.0e12f;
            if (unit == "mF") return 1.0e9f;
            if (unit == "uF") return 1.0e6f;
            if (unit == "nF") return 1.0e3f;
            if (unit == "pF") return 1.0f;
            if (unit == "fF") return 1.0e-3f;
            return -1.0f;
        };
        while (tokens.has_more()) {
            const std::string kind = tokens.next();
            if (!tokens.has_more()) {
                last_error_ = "set_units requires a unit after " + kind;
                return false;
            }
            const std::string unit = tokens.next();
            if (kind == "-time") {
                time_scale_ns_ = time_scale(unit);
                if (time_scale_ns_ < 0.0f) {
                    last_error_ = "Unsupported SDC time unit: " + unit;
                    return false;
                }
            } else if (kind == "-capacitance") {
                capacitance_scale_pf_ = capacitance_scale(unit);
                if (capacitance_scale_pf_ < 0.0f) {
                    last_error_ = "Unsupported SDC capacitance unit: " + unit;
                    return false;
                }
            } else if ((kind == "-resistance" && (unit == "Ohm" || unit == "kOhm" || unit == "MOhm")) ||
                       (kind == "-voltage" && (unit == "V" || unit == "mV")) ||
                       (kind == "-current" && (unit == "A" || unit == "mA" || unit == "uA")) ||
                       (kind == "-power" && (unit == "W" || unit == "mW" || unit == "uW"))) {
                // These declarations do not scale any supported ConstraintDB
                // value. SPEF and Liberty carry their own independent units.
            } else {
                last_error_ = "Unsupported set_units option: " + kind;
                return false;
            }
        }
    }
    // Keep parsing compatible with Tcl flows, but expose unsupported commands
    // to callers.  Silently dropping a timing command is unsafe for signoff.
    else if (!cmd.empty()) {
        warnings_.push_back("Unsupported SDC command: " + cmd);
    }

    return true;
}

} // namespace edacraft::core
