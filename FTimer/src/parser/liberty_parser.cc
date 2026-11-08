#include "liberty_parser.hh"

#include <cctype>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <algorithm>
#include <sstream>
#include <map>
#include <set>
#include <iostream>

#include "edacraft/core/liberty_db.hpp"

namespace te::parser {
namespace ec = edacraft::core;

static bool env_flag_enabled(const char* name) {
    const char* value = std::getenv(name);
    if (!value) return false;
    std::string text(value);
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char ch) {
                       return static_cast<char>(std::tolower(ch));
                   });
    return text == "1" || text == "true" || text == "yes" || text == "on";
}

static float liberty_si_quantity(std::string text, float fallback) {
    text.erase(std::remove_if(text.begin(), text.end(),
                              [](unsigned char ch) { return std::isspace(ch); }),
               text.end());
    if (text.empty()) return fallback;
    char* end = nullptr;
    const float magnitude = std::strtof(text.c_str(), &end);
    if (end == text.c_str() || !std::isfinite(magnitude)) return fallback;
    const std::string suffix(end);
    static const std::map<std::string, float> scales = {
        {"s", 1.0f}, {"ms", 1.0e-3f}, {"us", 1.0e-6f},
        {"ns", 1.0e-9f}, {"ps", 1.0e-12f}, {"fs", 1.0e-15f},
        {"V", 1.0f}, {"mV", 1.0e-3f},
        {"A", 1.0f}, {"mA", 1.0e-3f}, {"uA", 1.0e-6f},
        {"nA", 1.0e-9f}, {"pA", 1.0e-12f},
        {"F", 1.0f}, {"pf", 1.0e-12f}, {"ff", 1.0e-15f},
        {"ohm", 1.0f}, {"kohm", 1.0e3f}, {"Ohm", 1.0f}, {"kOhm", 1.0e3f},
        {"W", 1.0f}, {"mW", 1.0e-3f}, {"uW", 1.0e-6f},
        {"nW", 1.0e-9f}, {"pW", 1.0e-12f}
    };
    const auto it = scales.find(suffix);
    return it == scales.end() ? fallback : magnitude * it->second;
}

// ────────────────────────────────────────────────────────────
// Tokenizer
// ────────────────────────────────────────────────────────────

LibertyTokenizer::LibertyTokenizer(std::string_view input)
    : input_(input) {}

char LibertyTokenizer::peek() const {
    return eof() ? '\0' : input_[pos_];
}

char LibertyTokenizer::advance() {
    return eof() ? '\0' : input_[pos_++];
}

bool LibertyTokenizer::eof() const {
    return pos_ >= input_.size();
}

void LibertyTokenizer::skip_whitespace() {
    while (!eof()) {
        char c = peek();
        if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
            if (c == '\n') ++line_;
            advance();
        } else if (c == '\\' && pos_ + 1 < input_.size() && input_[pos_ + 1] == '\n') {
            // Liberty line continuation: backslash followed by newline
            advance(); advance(); // skip both
            ++line_;
        } else {
            break;
        }
    }
}

void LibertyTokenizer::skip_comment() {
    if (peek() == '/' && pos_ + 1 < input_.size() && input_[pos_ + 1] == '/') {
        while (!eof() && peek() != '\n') advance();
        return;
    }
    if (peek() == '/' && pos_ + 1 < input_.size() && input_[pos_ + 1] == '*') {
        pos_ += 2;
        while (!eof()) {
            if (peek() == '\n') ++line_;
            if (peek() == '*' && pos_ + 1 < input_.size() && input_[pos_ + 1] == '/') {
                pos_ += 2;
                break;
            }
            advance();
        }
    }
}

Token LibertyTokenizer::next() {
    while (true) {
        skip_whitespace();
        if (eof()) return {TokenType::Eof, "", line_};
        if (peek() == '/') {
            skip_comment();
            continue;
        }
        break;
    }

    int line = line_;

    switch (peek()) {
        case '{': advance(); return {TokenType::LBrace, "{", line};
        case '}': advance(); return {TokenType::RBrace, "}", line};
        case ':': advance(); return {TokenType::Colon, ":", line};
        case ';': advance(); return {TokenType::Semi, ";", line};
        case '(': advance(); return {TokenType::LParen, "(", line};
        case ')': advance(); return {TokenType::RParen, ")", line};
        case ',': advance(); return {TokenType::Comma, ",", line};

        case '&':
        case '|':
        case '+':
        case '*':
        case '^':
        case '~':
        case '\'':
            return {TokenType::Ident, std::string(1, advance()), line};

        case '"': {
            advance();
            std::string s;
            while (!eof() && peek() != '"') {
                if (peek() == '\\' && pos_ + 1 < input_.size()) {
                    advance();
                    char escaped = advance();
                    switch (escaped) {
                        case 'n':  s += '\n'; break;
                        case 't':  s += '\t'; break;
                        case '\\': s += '\\'; break;
                        case '"':  s += '"';  break;
                        default:   s += escaped; break;
                    }
                } else {
                    s += advance();
                }
            }
            if (peek() == '"') advance();
            return {TokenType::String, std::move(s), line};
        }

        default: {
            // Number: possibly negative, possibly scientific notation
            if (std::isdigit(static_cast<unsigned char>(peek())) || peek() == '.' ||
                (peek() == '-' && pos_ + 1 < input_.size() &&
                 (std::isdigit(static_cast<unsigned char>(input_[pos_ + 1])) || input_[pos_ + 1] == '.'))) {
                std::string num;
                if (peek() == '-') num += advance();
                while (!eof() && (std::isdigit(static_cast<unsigned char>(peek())) || peek() == '.')) {
                    num += advance();
                }
                if (!eof() && (peek() == 'e' || peek() == 'E')) {
                    num += advance();
                    if (!eof() && (peek() == '+' || peek() == '-')) {
                        num += advance();
                    }
                    while (!eof() && std::isdigit(static_cast<unsigned char>(peek()))) {
                        num += advance();
                    }
                }
                // Absorb common Liberty unit suffixes (e.g., 1ns, 1pf, 1mA)
                static const char* units[] = {
                    "ns", "us", "ps", "fs",
                    "mV", "V",
                    "mA", "uA", "nA", "pA", "fA",
                    "pf", "ff",
                    "kohm", "ohm",
                    "pW", "nW", "uW", "mW", "W",
                    nullptr
                };
                for (const char** u = units; *u; ++u) {
                    size_t len = strlen(*u);
                    if (pos_ + len <= input_.size() &&
                        input_.compare(pos_, len, *u) == 0) {
                        num += input_.substr(pos_, len);
                        pos_ += len;
                        break;
                    }
                }
                return {TokenType::Number, std::move(num), line};
            }

            if (std::isalpha(static_cast<unsigned char>(peek())) || peek() == '_' || peek() == '-' || peek() == '!') {
                std::string id;
                int bracket_depth = 0;
                while (!eof()) {
                    const char c = peek();
                    const bool ordinary = std::isalnum(static_cast<unsigned char>(c)) ||
                        c == '_' || c == '-' || c == '!';
                    const bool bracketed = c == '[' || c == ']' ||
                        (c == ':' && bracket_depth > 0);
                    if (!ordinary && !bracketed) break;
                    if (c == '[') ++bracket_depth;
                    else if (c == ']' && bracket_depth > 0) --bracket_depth;
                    id += advance();
                }
                return {TokenType::Ident, std::move(id), line};
            }

            advance();
            return next();
        }
    }
}

// ────────────────────────────────────────────────────────────
// Parser
// ────────────────────────────────────────────────────────────

LibertyParser::LibertyParser(std::string_view input)
    : tokenizer_(input) {}

Token& LibertyParser::peek() {
    if (!have_current_) {
        current_ = tokenizer_.next();
        have_current_ = true;
    }
    return current_;
}

Token LibertyParser::consume() {
    Token t = peek();
    have_current_ = false;
    return t;
}

Token LibertyParser::expect(TokenType type) {
    Token t = consume();
    if (t.type != type) {
        throw std::runtime_error(
            "Expected token type " + std::to_string(static_cast<int>(type)) +
            " but got " + std::to_string(static_cast<int>(t.type)) +
            " (" + t.text + ") at line " + std::to_string(t.line));
    }
    return t;
}

bool LibertyParser::match(TokenType type) {
    if (peek().type == type) {
        consume();
        return true;
    }
    return false;
}

float LibertyParser::parse_number() {
    Token t = expect(TokenType::Number);
    try {
        return std::stof(t.text);
    } catch (const std::exception&) {
        return 0.0f;
    }
}

ec::LibertyCcsnNode LibertyParser::parse_ccsn_node(unsigned depth) {
    if (depth > 64) throw std::runtime_error("Liberty CCSN nesting exceeds 64");
    ec::LibertyCcsnNode node;
    node.name = expect(TokenType::Ident).text;
    auto append = [&]() {
        const auto token = consume();
        if (token.type == TokenType::Eof || token.type == TokenType::RBrace)
            throw std::runtime_error("truncated Liberty CCSN statement");
        node.arguments.push_back({token.text, token.type == TokenType::String});
    };
    if (match(TokenType::Colon)) {
        node.kind = ec::LibertyCcsnNode::Kind::Attribute;
        while (peek().type != TokenType::Semi) append();
        expect(TokenType::Semi);
        return node;
    }
    expect(TokenType::LParen);
    unsigned parens = 1;
    while (parens) {
        if (peek().type == TokenType::LParen) ++parens;
        else if (peek().type == TokenType::RParen && --parens == 0) {
            consume(); break;
        }
        append();
    }
    if (match(TokenType::Semi)) {
        node.kind = ec::LibertyCcsnNode::Kind::Call;
    } else {
        node.kind = ec::LibertyCcsnNode::Kind::Group;
        expect(TokenType::LBrace);
        while (peek().type != TokenType::RBrace)
            node.children.push_back(parse_ccsn_node(depth + 1));
        expect(TokenType::RBrace);
    }
    return node;
}

// Preserve the historical Miller compatibility view without flattening stage
// ownership or interpreting the remaining CCSN characterization as ordinary CCS.
static void ccsn_miller_view(const ec::LibertyCcsnNode& stage,
                             ec::LibertyPinData& pin, float* rise = nullptr,
                             float* fall = nullptr) {
    for (const auto& attr : stage.children) {
        if (attr.kind != ec::LibertyCcsnNode::Kind::Attribute || attr.arguments.empty()) continue;
        if (attr.name == "miller_cap_rise") {
            pin.miller_cap_rise = std::stof(attr.arguments.front().text);
            if (rise) *rise = std::max(*rise, pin.miller_cap_rise);
        } else if (attr.name == "miller_cap_fall") {
            pin.miller_cap_fall = std::stof(attr.arguments.front().text);
            if (fall) *fall = std::max(*fall, pin.miller_cap_fall);
        }
    }
}

void LibertyParser::skip_group() {
    expect(TokenType::LBrace);
    int depth = 1;
    while (depth > 0 && peek().type != TokenType::Eof) {
        if (peek().type == TokenType::LBrace) { consume(); ++depth; }
        else if (peek().type == TokenType::RBrace) { consume(); --depth; }
        else consume();
    }
}

void LibertyParser::skip_statement() {
    // No debug here — too verbose. Just handle the statement.
    if (peek().type == TokenType::LBrace) {
        skip_group();
        return;
    }
    if (peek().type == TokenType::LParen) {
        consume();
        int depth = 1;
        while (depth > 0 && peek().type != TokenType::Eof) {
            if (peek().type == TokenType::LParen) { consume(); ++depth; }
            else if (peek().type == TokenType::RParen) { consume(); --depth; }
            else consume();
        }
    }
    // After optional paren, may be group or simple statement
    if (peek().type == TokenType::LBrace) {
        skip_group();
    } else {
        while (peek().type != TokenType::Semi && peek().type != TokenType::Eof) {
            consume();
        }
        if (peek().type == TokenType::Semi) consume();
    }
}

std::vector<float> LibertyParser::parse_index_values(std::string_view raw) {
    std::vector<float> result;
    std::string cleaned;
    for (char c : raw) {
        if (c == '"' || c == '\\') continue;
        if (c == '\n' || c == '\r' || c == '\t') c = ' ';
        cleaned += c;
    }
    // Split by both whitespace and commas, then parse each fragment.
    std::istringstream iss(cleaned);
    std::string token;
    while (iss >> token) {
        size_t start = 0;
        while (start < token.size()) {
            size_t comma = token.find(',', start);
            std::string frag = token.substr(start, comma - start);
            if (!frag.empty()) {
                try { result.push_back(std::stof(frag)); } catch (...) {}
            }
            if (comma == std::string::npos) break;
            start = comma + 1;
        }
    }
    return result;
}

std::string LibertyParser::parse_statement_text_until_semi() {
    std::string result;
    while (peek().type != TokenType::Semi && peek().type != TokenType::Eof) {
        Token t = consume();
        result += t.text;
    }
    if (peek().type == TokenType::Semi) consume();
    return result;
}

void LibertyParser::parse(ec::LibertyDB& liberty, ec::StringPool& strings,
                          const ec::LibertyLibrary::Units* main_units) {
    parse_top_level(liberty, strings, main_units);
}

void LibertyParser::parse_top_level(ec::LibertyDB& liberty, ec::StringPool& strings,
                                    const ec::LibertyLibrary::Units* main_units) {
    while (peek().type != TokenType::Eof) {
        if (peek().type == TokenType::Ident) {
            std::string name = peek().text;
            if (name == "library") {
                parse_library(liberty, strings, main_units);
            } else {
                skip_statement();
            }
        } else {
            consume();
        }
    }
}

// ────────────────────────────────────────────────────────────
// Library-level parsing
// ────────────────────────────────────────────────────────────

std::string LibertyParser::parse_paren_or_plain() {
    if (match(TokenType::LParen)) {
        std::string val;
        if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
            val = consume().text;
        }
        expect(TokenType::RParen);
        return val;
    }
    if (peek().type == TokenType::String || peek().type == TokenType::Ident) {
        return consume().text;
    }
    return "";
}

void LibertyParser::parse_library(ec::LibertyDB& liberty, ec::StringPool& strings,
                                  const ec::LibertyLibrary::Units* main_units) {
    consume(); // "library"

    std::string lib_name = parse_paren_or_plain();
    if (lib_name.empty()) lib_name = "unnamed";

    expect(TokenType::LBrace);

    auto& lib = liberty.create_library();
    lib.name = strings.intern(lib_name);
    bus_types_.clear();
    templates_.clear();
    source_templates_.clear();

    parse_library_attrs(lib, strings);
    // Resolve after the whole library: declarations may follow cells. Retain
    // only templates actually referenced by a CCSN node, in deterministic order.
    std::set<std::string> references;
    auto visit = [&](const auto& self, const ec::LibertyCcsnNode& node) -> void {
        if (node.kind == ec::LibertyCcsnNode::Kind::Group && !node.arguments.empty()) {
            const auto& ref = node.arguments.front().text;
            if (source_templates_.count(ref)) references.insert(ref);
        }
        for (const auto& child : node.children) self(self, child);
    };
    for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
        const auto& cell = lib.cells[ci];
        for (const auto& pin : cell.pins)
            for (const auto& stage : pin.ccsn_stages) visit(visit, stage);
        for (const auto& arc : cell.arcs)
            for (const auto& stage : arc.ccsn_stages) visit(visit, stage);
    }
    for (const auto& ref : references) lib.ccsn_templates.push_back(source_templates_.at(ref));


    // PT accepts fractional threshold spellings as well as percentages.
    // In particular 1 means 100%, so the diagnostic 1/99 window is invalid.
    // An invalid window inherits the main library's window (or the default
    // 20/80 window when this is the first library), retaining its own derate.
    if (!(lib.units.slew_lower >= 0.f && lib.units.slew_lower < lib.units.slew_upper &&
          lib.units.slew_upper <= 1.f)) {
        float lower=.2f, upper=.8f;
        const auto* main_context = main_units ? main_units :
            (liberty.library_count()>1 ? &liberty.library(0).units : nullptr);
        if (main_context) {
            const auto& main=*main_context;
            if (main.slew_lower>=0.f && main.slew_lower<main.slew_upper && main.slew_upper<=1.f) {
                lower=main.slew_lower; upper=main.slew_upper;
            }
        }
        lib.units.slew_lower=lower; lib.units.slew_upper=upper;
    }

    if (peek().type == TokenType::RBrace) consume();
}

void LibertyParser::parse_library_attrs(ec::LibertyLibrary& lib, ec::StringPool& strings) {
    (void)strings;
    int loop_cnt = 0;
    while (peek().type != TokenType::Eof) {
        if (peek().type == TokenType::RBrace) {
            // Some reduced/malformed libraries have stray closing braces
            // before cell definitions (e.g. deleted cell's closing brace).
            // If the next token is "cell", skip the stray brace and continue.
            Token saved = peek();
            consume();
            if (peek().type == TokenType::Ident && peek().text == "cell") {
                continue;
            }
            // Otherwise this is likely the library closing brace.
            // We have consumed it; parse_library will not see it, but
            // parse_top_level handles any stray tokens gracefully.
            break;
        }
        if (peek().type != TokenType::Ident) {
            consume(); continue;
        }

        std::string name = peek().text;

        // Simple attributes: name [:(] value ;
        auto skip_attr = [&]() {
            consume(); // skip name
            if (peek().type == TokenType::Colon) consume();
            if (peek().type == TokenType::LParen) {
                consume();
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            // Skip value tokens
            if (peek().type == TokenType::LBrace) {
                skip_group();
            } else {
                consume(); // value
                match(TokenType::Semi);
            }
        };

        if (name == "type") {
            consume();
            const auto type_name = parse_paren_or_plain();
            expect(TokenType::LBrace);
            int from = 0, to = 0, width = 1;
            bool has_from = false, has_to = false;
            while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
                const auto attr = consume().text;
                if (attr == "bit_from" || attr == "bit_to" || attr == "bit_width") {
                    match(TokenType::Colon);
                    const int value = static_cast<int>(parse_number());
                    if (attr == "bit_from") { from = value; has_from = true; }
                    else if (attr == "bit_to") { to = value; has_to = true; }
                    else width = value;
                    match(TokenType::Semi);
                } else skip_statement();
            }
            match(TokenType::RBrace);
            if (!has_from) from = has_to ? to + width - 1 : width - 1;
            if (!has_to) to = from - width + 1;
            bus_types_[type_name] = {from, to};
        } else if (name == "delay_model") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            consume(); match(TokenType::Semi);
        } else if (name == "slew_derate_from_library") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            float val = parse_number();
            match(TokenType::Semi);
            lib.units.slew_derate =
                env_flag_enabled("FSYN_TIMING_IGNORE_SLEW_DERATE") ? 1.0f : val;
        } else if (name == "time_unit") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            lib.units.time_unit_seconds =
                liberty_si_quantity(consume().text, lib.units.time_unit_seconds);
            match(TokenType::Semi);
        } else if (name == "voltage_unit" || name == "current_unit" ||
                   name == "leakage_power_unit" || name == "pulling_resistance_unit" ||
                   name == "capacitive_load_unit") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            std::string quantity;
            if (peek().type == TokenType::LParen) {
                consume();
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) {
                    if (peek().type != TokenType::Comma) quantity += consume().text;
                    else consume();
                }
            } else {
                quantity = consume().text;
            }
            match(TokenType::Semi);
            if (name == "voltage_unit") {
                lib.units.voltage_unit_volts = liberty_si_quantity(
                    quantity, lib.units.voltage_unit_volts);
            } else if (name == "leakage_power_unit") {
                lib.units.leakage_power_unit_watts = liberty_si_quantity(
                    quantity, lib.units.leakage_power_unit_watts);
            } else if (name == "current_unit") {
                // Legacy/current binary field expresses one unit in mA.
                lib.units.current = liberty_si_quantity(quantity, 1e-3f) / 1e-3f;
            } else if (name == "capacitive_load_unit") {
                lib.units.capacitance_unit_farads = liberty_si_quantity(
                    quantity, lib.units.capacitance_unit_farads);
            } else if (name == "pulling_resistance_unit") {
                // The legacy resistance field expresses one library unit in kOhm.
                lib.units.resistance = liberty_si_quantity(quantity, 1e3f) / 1e3f;
            }
        } else if (name == "nom_process" || name == "nom_temperature") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            float val = parse_number();
            match(TokenType::Semi);
            (void)val;
        } else if (name == "nom_voltage") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            float val = parse_number();
            match(TokenType::Semi);
            lib.units.voltage = val;
        } else if (name == "input_threshold_pct_rise" || name == "input_threshold_pct_fall" ||
                   name == "output_threshold_pct_rise" || name == "output_threshold_pct_fall" ||
                   name == "slew_lower_threshold_pct_rise" || name == "slew_lower_threshold_pct_fall" ||
                   name == "slew_upper_threshold_pct_rise" || name == "slew_upper_threshold_pct_fall") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            float val = parse_number();
            match(TokenType::Semi);
            float frac = val > 1.f ? val / 100.0f : val;
            if (name.find("slew_lower") != std::string::npos) {
                lib.units.slew_lower = frac;
            } else if (name.find("slew_upper") != std::string::npos) {
                lib.units.slew_upper = frac;
            } else if (name == "input_threshold_pct_rise") {
                lib.units.input_threshold_rise = frac;
            } else if (name == "input_threshold_pct_fall") {
                lib.units.input_threshold_fall = frac;
            } else if (name == "output_threshold_pct_rise") {
                lib.units.output_threshold_rise = frac;
            } else if (name == "output_threshold_pct_fall") {
                lib.units.output_threshold_fall = frac;
            }
        } else if (name == "default_operating_conditions") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            consume(); match(TokenType::Semi);
        } else if (name == "operating_conditions") {
            consume();
            if (peek().type == TokenType::LParen) {
                consume();
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
                if (peek().type == TokenType::Semi) consume();
            }
            if (peek().type == TokenType::LBrace) skip_group();
            else if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                consume(); match(TokenType::Semi);
            }
        } else if (name == "default_max_transition" || name == "default_max_capacitance" ||
                   name == "default_max_fanout") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            const float value = parse_number();
            if (name == "default_max_transition") lib.default_max_transition = value;
            else if (name == "default_max_capacitance") lib.default_max_capacitance = value;
            else lib.default_max_fanout = value;
            match(TokenType::Semi);
        } else if (name == "default_fanout_load") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            // Liberty default_fanout_load is the load-unit assigned to input
            // pins without an explicit fanout_load.  It is not a maximum
            // legal fanout constraint.
            lib.default_fanout_load = parse_number();
            match(TokenType::Semi);
        } else if (name == "voltage_map" || name == "default_cell_leakage_power" ||
                   name == "default_input_pin_cap" || name == "default_inout_pin_cap" ||
                   name == "default_output_pin_cap" || name == "in_place_swap_mode" ||
                   name == "library_features" || name == "simulation") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            if (peek().type == TokenType::LParen) {
                consume();
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
                match(TokenType::Semi);
            } else {
                consume(); match(TokenType::Semi);
            }
        } else if (name == "lu_table_template" || name == "power_lut_template" ||
                   name == "output_current_template") {
            parse_table_template(strings);
        } else if (name == "type") {
            consume();
            if (match(TokenType::LParen)) {
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            skip_group();
        } else if (name == "cell") {
            parse_cell(lib, strings);
        } else if (name == "wire_load") {
            consume();
            ec::LibertyLibrary::WireLoadModel wlm;
            if (match(TokenType::LParen)) {
                wlm.name = strings.intern(peek().text);
                consume();
                match(TokenType::RParen);
            }
            if (match(TokenType::LBrace)) {
                while (!match(TokenType::RBrace) && peek().type != TokenType::Eof) {
                    if (peek().type != TokenType::Ident) {
                        consume();
                        continue;
                    }
                    std::string attr = peek().text;
                    consume();
                    if (attr == "resistance") {
                        match(TokenType::Colon);
                        wlm.resistance = parse_number();
                        match(TokenType::Semi);
                    } else if (attr == "capacitance") {
                        match(TokenType::Colon);
                        wlm.capacitance = parse_number();
                        match(TokenType::Semi);
                    } else if (attr == "area") {
                        match(TokenType::Colon);
                        wlm.area = parse_number();
                        match(TokenType::Semi);
                    } else if (attr == "slope") {
                        match(TokenType::Colon);
                        wlm.slope = parse_number();
                        match(TokenType::Semi);
                    } else if (attr == "fanout_length") {
                        match(TokenType::LParen);
                        uint32_t fanout = static_cast<uint32_t>(parse_number());
                        match(TokenType::Comma);
                        float length = parse_number();
                        match(TokenType::RParen);
                        wlm.fanout_lengths.push_back({fanout, length});
                        match(TokenType::Semi);
                    } else {
                        skip_statement();
                    }
                }
            }
            lib.wire_load_models.push_back(std::move(wlm));
        } else if (name == "default_wire_load") {
            consume(); match(TokenType::Colon);
            if (peek().type != TokenType::Eof && peek().type != TokenType::Semi) {
                lib.default_wire_load = strings.intern(peek().text);
                consume();
            }
            match(TokenType::Semi);
        } else if (name == "default_wire_load_selection") {
            consume(); match(TokenType::Colon);
            if (peek().type != TokenType::Eof && peek().type != TokenType::Semi) {
                lib.default_wire_load_selection = strings.intern(peek().text);
                consume();
            }
            match(TokenType::Semi);
        } else if (name == "normalization_property" ||
                   name == "power_domain" || name == "input_voltage" ||
                   name == "output_voltage" || name == "normalized_driver_waveform") {
            consume();
            skip_statement();
        } else {
            // Unknown attribute — robust skip
            consume();
            skip_statement();
        }
    }
}

// Parse library-level table template definition.
// Forms: lu_table_template(name) { variable_1 : ...; index_1("..."); index_2("..."); }
void LibertyParser::parse_table_template(ec::StringPool& strings) {
    (void)strings;
    auto node = parse_ccsn_node();
    if (node.arguments.empty()) throw std::runtime_error("unnamed Liberty table template");
    const auto name = node.arguments.front().text;
    TemplateDef def;
    for (const auto& child : node.children) {
        std::string value;
        for (const auto& atom : child.arguments) value += atom.text + " ";
        if (child.name == "index_1") def.axis1 = parse_index_values(value);
        else if (child.name == "index_2") def.axis2 = parse_index_values(value);
        else if (child.name == "variable_1" || child.name == "variable_2") {
            // Variables normally use a colon. Support the legacy call form too.
            std::string variable;
            for (const auto& atom : child.arguments) variable += atom.text;
            if (child.name == "variable_1") def.var1 = variable;
            else def.var2 = variable;
            if (child.kind == ec::LibertyCcsnNode::Kind::Call) {
                if (child.name == "variable_1") def.axis1 = parse_index_values(value);
                else def.axis2 = parse_index_values(value);
            }
        }
    }
    templates_[name] = std::move(def);
    source_templates_[name] = std::move(node);
}

// ────────────────────────────────────────────────────────────
// Cell parsing
// ────────────────────────────────────────────────────────────

void LibertyParser::parse_cell(ec::LibertyLibrary& lib, ec::StringPool& strings) {
    consume(); // "cell"

    std::string cell_name = parse_paren_or_plain();
    if (cell_name.empty()) { skip_statement(); return; }

    uint32_t cell_name_id = strings.intern(cell_name);
    ec::LibertyCellHandle cell_id = ec::liberty_find_or_add_cell(lib, cell_name_id);
    auto& cell = lib.cells[cell_id.id];
    float unconditional_leakage_sum = 0.0f;
    bool has_unconditional_leakage = false;

    expect(TokenType::LBrace);

    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
        if (peek().type != TokenType::Ident) { consume(); continue; }

        std::string name = peek().text;

        if (name == "area") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            cell.area = parse_number();
            if (peek().type == TokenType::Semi) consume();
        } else if (name == "clock_gating_integrated_cell") {
            consume();
            expect(TokenType::Colon);
            cell.clock_gating_integrated_cell = strings.intern(consume().text);
            expect(TokenType::Semi);
        } else if (name == "pin") {
            parse_pin(lib, cell, strings);
        } else if (name == "pg_pin") {
            consume();
            parse_paren_or_plain();
            if (peek().type == TokenType::LBrace) skip_group();
            else { consume(); expect(TokenType::Semi); }
        } else if (name == "leakage_power") {
            consume();
            if (match(TokenType::LParen)) {
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            if (match(TokenType::LBrace)) {
                float value = 0.0f;
                bool has_value = false;
                bool conditional = false;
                ec::LibertyCellData::LeakagePowerData leakage;
                while (peek().type != TokenType::RBrace &&
                       peek().type != TokenType::Eof) {
                    if (peek().type != TokenType::Ident) { consume(); continue; }
                    const std::string attr = consume().text;
                    if (peek().type == TokenType::Colon) consume();
                    if (attr == "value" && peek().type == TokenType::Number) {
                        value = parse_number();
                        has_value = true;
                        match(TokenType::Semi);
                    } else if (attr == "when") {
                        conditional = true;
                        leakage.when = strings.intern(consume().text);
                        match(TokenType::Semi);
                    } else if (attr == "related_pg_pin") {
                        leakage.related_pg_pin = strings.intern(consume().text);
                        match(TokenType::Semi);
                    } else {
                        skip_statement();
                    }
                }
                if (peek().type == TokenType::RBrace) consume();
                if (has_value) {
                    leakage.value = value;
                    cell.leakage_power.push_back(leakage);
                }
                if (has_value && !conditional) {
                    unconditional_leakage_sum += value;
                    has_unconditional_leakage = true;
                }
            } else {
                skip_statement();
            }
        } else if (name == "dont_use" || name == "don_t_use") {
            consume();
            skip_statement();
            cell.dont_use = true;
        } else if (name == "ff" || name == "latch") {
            consume();
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    cell.ff_state = strings.intern(consume().text);
                    if (match(TokenType::Comma) &&
                        (peek().type == TokenType::Ident || peek().type == TokenType::String))
                        cell.ff_state_neg = strings.intern(consume().text);
                }
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            if (peek().type == TokenType::LBrace) {
                expect(TokenType::LBrace);
                while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
                    if (peek().type != TokenType::Ident) { consume(); continue; }
                    std::string ff_attr = peek().text;
                    consume();
                    if (peek().type == TokenType::Colon) consume();
                    std::string val;
                    if (peek().type == TokenType::String || peek().type == TokenType::Ident) {
                        val = consume().text;
                    }
                    expect(TokenType::Semi);
                    uint32_t sid = strings.intern(val);
                    if (ff_attr == "clocked_on") cell.ff_clocked_on = sid;
                    else if (ff_attr == "next_state" || ff_attr == "data_in") cell.ff_next_state = sid;
                    else if (ff_attr == "clear") cell.ff_clear = sid;
                    else if (ff_attr == "preset") cell.ff_preset = sid;
                    else if (ff_attr == "enable") cell.ff_enable = sid;
                }
                if (peek().type == TokenType::RBrace) consume();
            } else {
                skip_statement();
            }
        } else if (name == "bus") {
            parse_bus(lib, cell, strings);
        } else if (name == "internal_power" || name == "three_state") {
            consume();
            skip_statement();
        } else if (name == "cell_leakage_power") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            cell.cell_leakage_power = parse_number();
            if (peek().type == TokenType::Semi) consume();
        } else if (name == "footprint" || name == "cell_footprint") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            cell.footprint = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "function") {
            // Cell-level function (e.g. for combinatorial cells)
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            cell.function = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "power_down_function" ||
                   name == "related_ground_pin" || name == "related_power_pin" ||
                   name == "output_voltage" || name == "clamp_condition" ||
                   name == "enable_condition" || name == "bus_function" ||
                   name == "hold_function" || name == "nextstate_type" ||
                   name == "state_function" || name == "clear" || name == "preset" ||
                   name == "data" || name == "clock" || name == "data_pin" ||
                   name == "clock_pin" || name == "clear_pin" || name == "preset_pin") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            if (name == "clear") cell.ff_clear = strings.intern(val.text);
            else if (name == "preset") cell.ff_preset = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "max_transition") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            cell.max_transition = parse_number();
            expect(TokenType::Semi);
        } else if (name == "max_capacitance") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            cell.max_capacitance = parse_number();
            expect(TokenType::Semi);
        } else if (name == "max_fanout") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            cell.max_fanout = parse_number();
            expect(TokenType::Semi);
        } else if (name == "driver_waveform" ||
                   name == "min_power_density" || name == "is_memory_cell") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            consume(); expect(TokenType::Semi);
        } else {
            consume();
            skip_statement();
        }
    }

    if (cell.cell_leakage_power == 0.0f && has_unconditional_leakage) {
        cell.cell_leakage_power = unconditional_leakage_sum;
    }
    if (peek().type == TokenType::RBrace) consume();
}

// ────────────────────────────────────────────────────────────
// Pin parsing
// ────────────────────────────────────────────────────────────

void LibertyParser::parse_bus(ec::LibertyLibrary& lib, ec::LibertyCellData& cell,
                              ec::StringPool& strings) {
    // Parse the common attributes/timing with the ordinary pin parser. Revisit
    // the body for members after all defaults are known, so inheritance does
    // not depend on whether a bus attribute precedes or follows pin().
    const auto saved_tokenizer = tokenizer_;
    const auto saved_current = current_;
    const auto saved_have_current = have_current_;
    ec::LibertyCellData common;
    parse_pin(lib, common, strings);
    if (common.pins.empty()) return;
    tokenizer_ = saved_tokenizer;
    current_ = saved_current;
    have_current_ = saved_have_current;
    consume();
    const auto declaration = parse_paren_or_plain();
    expect(TokenType::LBrace);
    std::string bus_type;
    ec::LibertyCellData members;
    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
        if (peek().type != TokenType::Ident) { consume(); continue; }
        if (peek().text == "pin") {
            parse_pin(lib, members, strings, &common.pins.front());
        } else {
            const auto attr = consume().text;
            if (attr == "bus_type") {
                match(TokenType::Colon);
                bus_type = consume().text;
                match(TokenType::Semi);
            } else skip_statement();
        }
    }
    match(TokenType::RBrace);
    auto expand = [](const std::string& name) {
        std::vector<std::string> bits;
        const auto open = name.find('['), colon = name.find(':', open);
        if (open == std::string::npos || colon == std::string::npos) return std::vector<std::string>{name};
        const int from = std::stoi(name.substr(open+1, colon-open-1));
        const int to = std::stoi(name.substr(colon+1));
        for (int bit = std::min(from,to); bit <= std::max(from,to); ++bit)
            bits.push_back(name.substr(0,open)+"["+std::to_string(bit)+"]");
        return bits;
    };
    std::map<std::string, size_t> member_by_bit;
    for (size_t i=0; i<members.pins.size(); ++i)
        for (const auto& bit : expand(std::string(strings.view(members.pins[i].name))))
            member_by_bit[bit] = i;
    std::set<std::string> bits;
    const auto type = bus_types_.find(bus_type);
    if (type != bus_types_.end()) {
        const auto base = declaration.substr(0,declaration.find('['));
        const auto [from,to] = type->second;
        for (int i=std::min(from,to); i<=std::max(from,to); ++i)
            bits.insert(base+"["+std::to_string(i)+"]");
    } else if (declaration.find(':') != std::string::npos) {
        const auto expanded = expand(declaration);
        bits.insert(expanded.begin(),expanded.end());
    }
    for (const auto& member : member_by_bit) bits.insert(member.first);
    if (bits.empty()) bits.insert(declaration);
    for (const auto& bit : bits) {
        const auto member = member_by_bit.find(bit);
        const auto* specific = member == member_by_bit.end() ? nullptr : &members.pins[member->second];
        auto pin = specific ? *specific : common.pins.front();
        pin.name = strings.intern(bit);
        cell.pins.push_back(pin);
        for (const auto& arc : common.arcs) {
            // A member's timing group overrides the matching inherited group.
            const bool overridden = specific && std::any_of(members.arcs.begin(), members.arcs.end(), [&](const auto& a) {
                return a.to_pin == specific->name && a.from_pin == arc.from_pin && a.type == arc.type && a.when == arc.when;
            });
            if (!overridden) { auto copy = arc; copy.to_pin = pin.name; cell.arcs.push_back(std::move(copy)); }
        }
        if (specific) for (const auto& arc : members.arcs) if (arc.to_pin == specific->name) {
            auto copy = arc; copy.to_pin = pin.name; cell.arcs.push_back(std::move(copy));
        }
    }
    for (auto limits : {&common, &members}) {
        auto merge = [](float& aggregate, float value) {
            if (value > 0.f) aggregate = aggregate > 0.f ? std::min(aggregate,value) : value;
        };
        merge(cell.max_capacitance,limits->max_capacitance);
        merge(cell.max_transition,limits->max_transition);
        merge(cell.max_fanout,limits->max_fanout);
    }
}

void LibertyParser::parse_pin(ec::LibertyLibrary& lib, ec::LibertyCellData& cell, ec::StringPool& strings,
                              const ec::LibertyPinData* inherited) {
    (void)lib;
    consume(); // "pin"

    std::string pin_name = parse_paren_or_plain();
    if (pin_name.empty()) { skip_statement(); return; }

    uint32_t pin_name_id = strings.intern(pin_name);

    ec::LibertyPinData pin = inherited ? *inherited : ec::LibertyPinData{};
    pin.name = pin_name_id;
    float pin_max_capacitance = 0.0f;
    float pin_max_transition = 0.0f;
    float pin_max_fanout = 0.0f;

    expect(TokenType::LBrace);

    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
        if (peek().type != TokenType::Ident) { consume(); continue; }

        std::string name = peek().text;

        if (name == "direction") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            if (val.text == "input") pin.direction = ec::PortDirection::Input;
            else if (val.text == "output") pin.direction = ec::PortDirection::Output;
            else if (val.text == "inout") pin.direction = ec::PortDirection::Inout;
            else if (val.text == "internal") pin.direction = ec::PortDirection::Internal;
            else if (val.text == "clock") pin.is_clock = true;
            expect(TokenType::Semi);
        } else if (name == "capacitance") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            pin.capacitance = parse_number();
            expect(TokenType::Semi);
        } else if (name == "rise_capacitance" || name == "fall_capacitance") {
            consume();
            expect(TokenType::Colon);
            const float value = parse_number();
            if (name == "rise_capacitance") pin.rise_capacitance = value;
            else pin.fall_capacitance = value;
            expect(TokenType::Semi);
        } else if (name == "rise_capacitance_range" || name == "fall_capacitance_range") {
            consume();
            expect(TokenType::LParen);
            const float lower = parse_number();
            expect(TokenType::Comma);
            const float upper = parse_number();
            expect(TokenType::RParen);
            expect(TokenType::Semi);
            if (name == "rise_capacitance_range") {
                pin.rise_capacitance_lower = lower; pin.rise_capacitance_upper = upper;
            } else {
                pin.fall_capacitance_lower = lower; pin.fall_capacitance_upper = upper;
            }
        } else if (name == "fanout_load") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            pin.fanout_load = parse_number();
            expect(TokenType::Semi);
        } else if (name == "max_transition" || name == "min_transition" ||
                   name == "max_capacitance" || name == "min_capacitance" ||
                   name == "max_fanout") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            float value = parse_number();
            if (name == "max_transition") pin_max_transition = value;
            else if (name == "max_capacitance") pin_max_capacitance = value;
            else if (name == "max_fanout") pin_max_fanout = value;
            if (name == "max_transition") pin.max_transition = value;
            else if (name == "max_capacitance") pin.max_capacitance = value;
            else if (name == "max_fanout") pin.max_fanout = value;
            expect(TokenType::Semi);
        } else if (name == "clock_gate_clock_pin" || name == "clock_gate_enable_pin" ||
                   name == "clock_gate_test_pin" || name == "clock_gate_out_pin") {
            consume();
            expect(TokenType::Colon);
            const bool enabled = consume().text == "true";
            if (name == "clock_gate_clock_pin") pin.clock_gate_clock_pin = enabled;
            else if (name == "clock_gate_enable_pin") pin.clock_gate_enable_pin = enabled;
            else if (name == "clock_gate_test_pin") pin.clock_gate_test_pin = enabled;
            else pin.clock_gate_out_pin = enabled;
            expect(TokenType::Semi);
        } else if (name == "clock") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            consume(); expect(TokenType::Semi);
            pin.is_clock = true;
        } else if (name == "function") {
            // Pin-level function (e.g. output pin boolean function)
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            pin.function = strings.intern(val.text);
            if (pin.direction == ec::PortDirection::Input) {
                pin.direction = ec::PortDirection::Output;
            }
            expect(TokenType::Semi);
        } else if (name == "power_down_function" ||
                   name == "related_ground_pin" || name == "related_power_pin" ||
                   name == "output_voltage" || name == "driver_resistance") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            consume(); expect(TokenType::Semi);
        } else if (name == "clear") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            pin.clear = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "preset") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            pin.preset = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "enable") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            pin.enable = strings.intern(val.text);
            expect(TokenType::Semi);
        } else if (name == "receiver_capacitance1_rise" || name == "receiver_capacitance1_fall") {
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            if (name == "receiver_capacitance1_rise") {
                parse_table_body(&pin.receiver_capacitance1_rise, template_ref, strings);
            } else {
                parse_table_body(&pin.receiver_capacitance1_fall, template_ref, strings);
            }
        } else if (name == "receiver_capacitance2_rise" || name == "receiver_capacitance2_fall") {
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            if (name == "receiver_capacitance2_rise") {
                parse_table_body(&pin.receiver_capacitance2_rise, template_ref, strings);
            } else {
                parse_table_body(&pin.receiver_capacitance2_fall, template_ref, strings);
            }
        } else if (name == "related_pg_pin") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                pin.related_pg_pin = strings.intern(consume().text);
            }
            expect(TokenType::Semi);
        } else if (name == "timing") {
            consume();
            if (match(TokenType::LParen)) {
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            parse_timing(lib, cell, pin, strings);
        } else if (name == "receiver_capacitance") {
            consume();
            if (match(TokenType::LParen)) {
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            expect(TokenType::LBrace);
            ec::LibertyPinData::ReceiverCapacitanceData receiver;
            while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
                if (peek().type != TokenType::Ident) { consume(); continue; }
                std::string rc_name = peek().text;
                if (rc_name == "char_when" || rc_name == "when") {
                    consume();
                    if (peek().type == TokenType::Colon) consume();
                    if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                        receiver.when = strings.intern(consume().text);
                    }
                    match(TokenType::Semi);
                } else if (rc_name == "receiver_capacitance1_rise" || rc_name == "receiver_capacitance1_fall") {
                    consume();
                    std::string template_ref;
                    if (match(TokenType::LParen)) {
                        if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                            template_ref = consume().text;
                        }
                        expect(TokenType::RParen);
                    }
                    if (rc_name == "receiver_capacitance1_rise") {
                        parse_table_body(&receiver.receiver_capacitance1_rise, template_ref, strings);
                    } else {
                        parse_table_body(&receiver.receiver_capacitance1_fall, template_ref, strings);
                    }
                } else if (rc_name == "receiver_capacitance2_rise" || rc_name == "receiver_capacitance2_fall") {
                    consume();
                    std::string template_ref;
                    if (match(TokenType::LParen)) {
                        if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                            template_ref = consume().text;
                        }
                        expect(TokenType::RParen);
                    }
                    if (rc_name == "receiver_capacitance2_rise") {
                        parse_table_body(&receiver.receiver_capacitance2_rise, template_ref, strings);
                    } else {
                        parse_table_body(&receiver.receiver_capacitance2_fall, template_ref, strings);
                    }
                } else {
                    consume();
                    skip_statement();
                }
            }
            if (peek().type == TokenType::RBrace) consume();
            const auto table_present = [](const ec::NldmTable& table) {
                return table.rows != 0 || table.cols != 0 || !table.values.empty();
            };
            if (table_present(receiver.receiver_capacitance1_rise) ||
                table_present(receiver.receiver_capacitance1_fall) ||
                table_present(receiver.receiver_capacitance2_rise) ||
                table_present(receiver.receiver_capacitance2_fall)) {
                // Preserve the pre-v7 compatibility view: the last nested group
                // wins.  Timing therefore remains unchanged by retaining groups.
                pin.receiver_capacitance1_rise = receiver.receiver_capacitance1_rise;
                pin.receiver_capacitance1_fall = receiver.receiver_capacitance1_fall;
                pin.receiver_capacitance2_rise = receiver.receiver_capacitance2_rise;
                pin.receiver_capacitance2_fall = receiver.receiver_capacitance2_fall;
                pin.receiver_capacitance.push_back(std::move(receiver));
            }
        } else if (name == "ccsn_first_stage" || name == "ccsn_last_stage") {
            auto stage = parse_ccsn_node();
            ccsn_miller_view(stage, pin);
            pin.ccsn_stages.push_back(std::move(stage));
        } else if (name == "internal_power") {
            parse_internal_power(pin, strings);
        } else if (name == "three_state" || name == "rec") {
            consume();
            skip_statement();
        } else {
            consume();
            skip_statement();
        }
    }

    if (pin.direction == ec::PortDirection::Output) {
        auto merge_positive_limit = [](float& aggregate, float pin_limit) {
            if (!(pin_limit > 0.0f)) return;
            aggregate = aggregate > 0.0f
                ? std::min(aggregate, pin_limit)
                : pin_limit;
        };
        merge_positive_limit(cell.max_capacitance, pin_max_capacitance);
        merge_positive_limit(cell.max_transition, pin_max_transition);
        merge_positive_limit(cell.max_fanout, pin_max_fanout);
    }

    cell.pins.push_back(pin);

    if (peek().type == TokenType::RBrace) consume();
}

void LibertyParser::parse_internal_power(ec::LibertyPinData& pin,
                                         ec::StringPool& strings) {
    consume(); // internal_power
    if (match(TokenType::LParen)) {
        while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
    }
    if (!match(TokenType::LBrace)) {
        skip_statement();
        return;
    }

    ec::LibertyPinData::InternalPowerData power;
    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
        if (peek().type != TokenType::Ident) { consume(); continue; }
        const std::string attr = consume().text;
        if (attr == "related_pin" || attr == "related_pg_pin" || attr == "when") {
            if (peek().type == TokenType::Colon) consume();
            if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                const uint32_t id = strings.intern(consume().text);
                if (attr == "related_pin") power.related_pin = id;
                else if (attr == "related_pg_pin") power.related_pg_pin = id;
                else power.when = id;
            }
            match(TokenType::Semi);
        } else if (attr == "rise_power" || attr == "fall_power") {
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            parse_table_body(attr == "rise_power" ? &power.rise_power
                                                   : &power.fall_power,
                             template_ref, strings);
            normalize_nldm_axes(attr == "rise_power" ? &power.rise_power : &power.fall_power,
                                template_ref, false);
        } else {
            skip_statement();
        }
    }
    if (peek().type == TokenType::RBrace) consume();
    if (power.rise_power.rows != 0 || power.fall_power.rows != 0) {
        pin.internal_power.push_back(std::move(power));
    }
}

// ────────────────────────────────────────────────────────────
// Timing group parsing
// ────────────────────────────────────────────────────────────

void LibertyParser::parse_timing(ec::LibertyLibrary& lib, ec::LibertyCellData& cell, ec::LibertyPinData& pin, ec::StringPool& strings) {
    (void)lib;
    //std::cerr << "[LIB_DBG_TIMING] enter timing for pin=" << pin.name << " cell=" << cell.name << "\n";
    expect(TokenType::LBrace);

    std::string related_pin;
    std::string when_condition;
    ec::LibertyTimingSense sense = ec::LibertyTimingSense::None;
    ec::LibertyTimingType type = ec::LibertyTimingType::Combinational;

    // Accumulate tables locally, create arc at end.
    ec::NldmTable rise_table, fall_table, rise_slew_table, fall_slew_table;
    ec::NldmTable retain_rise, retain_fall, retain_rise_slew, retain_fall_slew;
    ec::NldmTable rise_constraint_table, fall_constraint_table;
    uint8_t constraint_transition_mask = 0;
    ec::NldmTable receiver1_rise, receiver1_fall;
    ec::NldmTable receiver2_rise, receiver2_fall;
    ec::CsmOutputCurrentTable csm_rise, csm_fall;
    ec::CsmOutputCurrentTable csm_retain_rise, csm_retain_fall;
    std::vector<ec::LibertyCcsnNode> ccsn_stages;
    float arc_miller_cap_rise = 0.0f;
    float arc_miller_cap_fall = 0.0f;

    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
        if (peek().type != TokenType::Ident) { consume(); continue; }

        std::string name = peek().text;

        if (name == "related_pin") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            related_pin = val.text;
            expect(TokenType::Semi);
        } else if (name == "timing_sense") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            expect(TokenType::Semi);
            if (val.text == "positive_unate") sense = ec::LibertyTimingSense::PositiveUnate;
            else if (val.text == "negative_unate") sense = ec::LibertyTimingSense::NegativeUnate;
            else if (val.text == "non_unate") sense = ec::LibertyTimingSense::NonUnate;
            else if (val.text == "positive") sense = ec::LibertyTimingSense::PositiveUnate;
            else if (val.text == "negative") sense = ec::LibertyTimingSense::NegativeUnate;
        } else if (name == "timing_type") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            Token val = consume();
            expect(TokenType::Semi);
            if (val.text == "rising_edge") type = ec::LibertyTimingType::RisingEdge;
            else if (val.text == "falling_edge") type = ec::LibertyTimingType::FallingEdge;
            else if (val.text == "preset") type = ec::LibertyTimingType::Preset;
            else if (val.text == "clear") type = ec::LibertyTimingType::Clear;
            else if (val.text == "combinational" || val.text == "combinational_rise" ||
                     val.text == "combinational_fall") type = ec::LibertyTimingType::Combinational;
            else if (val.text == "setup_rising") type = ec::LibertyTimingType::SetupRising;
            else if (val.text == "setup_falling") type = ec::LibertyTimingType::SetupFalling;
            else if (val.text == "hold_rising") type = ec::LibertyTimingType::HoldRising;
            else if (val.text == "hold_falling") type = ec::LibertyTimingType::HoldFalling;
            else if (val.text == "recovery_rising") type = ec::LibertyTimingType::RecoveryRising;
            else if (val.text == "recovery_falling") type = ec::LibertyTimingType::RecoveryFalling;
            else if (val.text == "removal_rising") type = ec::LibertyTimingType::RemovalRising;
            else if (val.text == "removal_falling") type = ec::LibertyTimingType::RemovalFalling;
            else type = ec::LibertyTimingType::Unknown;
        } else if (name == "when") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            when_condition = parse_statement_text_until_semi();
        } else if (name == "related_output_pin" || name == "sdf_cond" ||
                   name == "cell_fall_cond" || name == "cell_rise_cond" ||
                   name == "fall_cond" || name == "rise_cond") {
            consume();
            if (peek().type == TokenType::Colon) consume();
            if (peek().type == TokenType::LParen) {
                consume();
                while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
            }
            consume(); expect(TokenType::Semi);
        } else if (name == "cell_rise" || name == "cell_fall" ||
                   name == "rise_transition" || name == "fall_transition" ||
                   name == "retaining_rise" || name == "retaining_fall" ||
                   name == "retain_rise_slew" || name == "retain_fall_slew") {
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }

            ec::NldmTable* target = nullptr;
            if (name == "cell_rise") target = &rise_table;
            else if (name == "cell_fall") target = &fall_table;
            else if (name == "rise_transition") target = &rise_slew_table;
            else if (name == "fall_transition") target = &fall_slew_table;
            else if (name == "retaining_rise") target = &retain_rise;
            else if (name == "retaining_fall") target = &retain_fall;
            else if (name == "retain_rise_slew") target = &retain_rise_slew;
            else if (name == "retain_fall_slew") target = &retain_fall_slew;

            parse_table_body(target, template_ref, strings);
            normalize_nldm_axes(target, template_ref, false);
        } else if (name == "output_current_rise" || name == "output_current_fall" ||
                   name == "ccs_retain_rise" || name == "ccs_retain_fall") {
            // std::cerr << "[LIB_DBG] Found " << name << "\n";
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            ec::CsmOutputCurrentTable* target = nullptr;
            if (name == "output_current_rise") target = &csm_rise;
            else if (name == "output_current_fall") target = &csm_fall;
            else if (name == "ccs_retain_rise") target = &csm_retain_rise;
            else target = &csm_retain_fall;
            parse_csm_table_body(target, template_ref, strings);
        } else if (name == "receiver_capacitance1_rise" ||
                   name == "receiver_capacitance1_fall" ||
                   name == "receiver_capacitance2_rise" ||
                   name == "receiver_capacitance2_fall") {
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident ||
                    peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            ec::NldmTable* target = nullptr;
            if (name == "receiver_capacitance1_rise") target = &receiver1_rise;
            else if (name == "receiver_capacitance1_fall") target = &receiver1_fall;
            else if (name == "receiver_capacitance2_rise") target = &receiver2_rise;
            else target = &receiver2_fall;
            parse_table_body(target, template_ref, strings);
            normalize_nldm_axes(target, template_ref, false);
        } else if (name == "rise_constraint") {
            constraint_transition_mask |= 1;
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            parse_table_body(&rise_constraint_table, template_ref, strings);
            normalize_nldm_axes(&rise_constraint_table, template_ref, true);
        } else if (name == "fall_constraint") {
            constraint_transition_mask |= 2;
            consume();
            std::string template_ref;
            if (match(TokenType::LParen)) {
                if (peek().type == TokenType::Ident || peek().type == TokenType::String) {
                    template_ref = consume().text;
                }
                expect(TokenType::RParen);
            }
            parse_table_body(&fall_constraint_table, template_ref, strings);
            normalize_nldm_axes(&fall_constraint_table, template_ref, true);
        } else if (name == "ccsn_first_stage" || name == "ccsn_last_stage") {
            const bool first = name == "ccsn_first_stage";
            auto stage = parse_ccsn_node();
            ccsn_miller_view(stage, pin, first ? &arc_miller_cap_rise : nullptr,
                             first ? &arc_miller_cap_fall : nullptr);
            ccsn_stages.push_back(std::move(stage));
        } else {
            consume(); // consume name before skip_statement
            skip_statement();
        }
    }

    // For sequential arcs (rising_edge / falling_edge), if no timing_sense
    // is specified, default to NonUnate because the output transition depends
    // on the data value (Q can rise or fall on the same clock edge).
    if (sense == ec::LibertyTimingSense::None &&
        (type == ec::LibertyTimingType::RisingEdge || type == ec::LibertyTimingType::FallingEdge)) {
        sense = ec::LibertyTimingSense::NonUnate;
    }

    // Build single timing arc with all tables.
    ec::LibertyArcData arc;
    arc.from_pin = strings.intern(related_pin);
    arc.to_pin = pin.name;
    arc.sense = sense;
    arc.type = type;
    if (!when_condition.empty()) {
        arc.when = strings.intern(when_condition);
    }
    arc.rise_delay = std::move(rise_table);
    arc.fall_delay = std::move(fall_table);
    arc.rise_output_slew = std::move(rise_slew_table);
    arc.fall_output_slew = std::move(fall_slew_table);
    arc.rise_constraint = std::move(rise_constraint_table);
    arc.fall_constraint = std::move(fall_constraint_table);
    arc.constraint_transition_mask = constraint_transition_mask;
    arc.receiver_capacitance1_rise = std::move(receiver1_rise);
    arc.receiver_capacitance1_fall = std::move(receiver1_fall);
    arc.receiver_capacitance2_rise = std::move(receiver2_rise);
    arc.receiver_capacitance2_fall = std::move(receiver2_fall);
    arc.ccsn_stages = std::move(ccsn_stages);
    arc.miller_cap_rise = arc_miller_cap_rise;
    arc.miller_cap_fall = arc_miller_cap_fall;
    arc.csm_output_current_rise = std::move(csm_rise);
    arc.csm_output_current_fall = std::move(csm_fall);

    cell.arcs.push_back(std::move(arc));

    // Retaining tables describe a separate characterized response to the
    // same event and condition. Its RC fit can have a larger transition even
    // when its lumped slew is smaller. Preserve both responses so delay and
    // slew are bounded independently by the normal propagation machinery.
    // The existing arc representation and binary format already preserve
    // parallel conditional arcs; no table may replace the ordinary response.
    if ((!retain_rise.values.empty() && !retain_rise_slew.values.empty()) ||
        (!retain_fall.values.empty() && !retain_fall_slew.values.empty()) ||
        !csm_retain_rise.waveforms.empty() || !csm_retain_fall.waveforms.empty()) {
        ec::LibertyArcData retained;
        retained.from_pin = strings.intern(related_pin);
        retained.to_pin = pin.name;
        retained.sense = sense;
        retained.type = type;
        if (!when_condition.empty()) retained.when = strings.intern(when_condition);
        retained.rise_delay = std::move(retain_rise);
        retained.fall_delay = std::move(retain_fall);
        retained.rise_output_slew = std::move(retain_rise_slew);
        retained.fall_output_slew = std::move(retain_fall_slew);
        // CCS retaining currents characterize this response independently of
        // the ordinary output-current waveform, just like retaining NLDM.
        retained.csm_output_current_rise = std::move(csm_retain_rise);
        retained.csm_output_current_fall = std::move(csm_retain_fall);
        cell.arcs.push_back(std::move(retained));
    }

    if (peek().type == TokenType::RBrace) consume();
}

// Parse the body of a CSM output_current group.
// Supports both flat format (index_1/2/3 + values at group level)
// and nested vector(ccs_template) groups (industrial CCS libraries).
void LibertyParser::parse_csm_table_body(ec::CsmOutputCurrentTable* table,
                                           const std::string& template_ref,
                                           ec::StringPool& strings) {
    (void)strings;
    if (!table) return;

    struct TempVec {
        float slew = 0.0f;
        float cap = 0.0f;
        float reference_time = 0.0f;
        std::vector<float> time;
        std::vector<float> current;
    };
    std::vector<TempVec> vectors;

    // Flat-format fallback state
    std::vector<float> flat_axis1, flat_axis2, flat_axis3, flat_current;

    if (match(TokenType::LBrace)) {
        while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
            if (peek().type != TokenType::Ident) { consume(); continue; }
            std::string attr = peek().text;
            consume();
            if (peek().type == TokenType::Colon) consume();

            if (attr == "vector") {
                // Nested vector group: vector(template) { reference_time; index_1; index_2; index_3; values; }
                if (match(TokenType::LParen)) {
                    while (!match(TokenType::RParen) && peek().type != TokenType::Eof) consume();
                }
                if (match(TokenType::LBrace)) {
                    TempVec vec;
                    while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
                        if (peek().type != TokenType::Ident) { consume(); continue; }
                        std::string vattr = peek().text;
                        consume();
                        if (peek().type == TokenType::Colon) consume();

                        if (peek().type == TokenType::LParen) {
                            consume();
                            std::string val;
                            while (!match(TokenType::RParen)) {
                                if (peek().type == TokenType::String) {
                                    val += consume().text + " ";
                                } else if (peek().type == TokenType::Comma) {
                                    consume();
                                } else {
                                    val += consume().text + " ";
                                }
                            }
                            std::vector<float> nums = parse_index_values(val);
                            if (vattr == "index_1" || vattr == "variable_1") {
                                if (nums.size() == 1) vec.slew = nums[0];
                            } else if (vattr == "index_2" || vattr == "variable_2") {
                                if (nums.size() == 1) vec.cap = nums[0];
                            } else if (vattr == "index_3" || vattr == "variable_3") {
                                vec.time = std::move(nums);
                            } else if (vattr == "values") {
                                vec.current = std::move(nums);
                            }
                        } else {
                            if (vattr == "reference_time" && peek().type == TokenType::Number) {
                                vec.reference_time = std::stof(consume().text);
                            } else {
                                consume();
                            }
                            expect(TokenType::Semi);
                        }
                    }
                    if (peek().type == TokenType::RBrace) consume();
                    if (!vec.time.empty() && !vec.current.empty()) {
                        vectors.push_back(std::move(vec));
                    }
                }
            } else if (peek().type == TokenType::LParen) {
                // Flat format attributes at output_current level
                consume();
                std::string val;
                while (!match(TokenType::RParen)) {
                    if (peek().type == TokenType::String) {
                        val += consume().text + " ";
                    } else if (peek().type == TokenType::Comma) {
                        consume();
                    } else {
                        val += consume().text + " ";
                    }
                }
                std::vector<float> nums = parse_index_values(val);
                if (attr == "index_1" || attr == "variable_1") flat_axis1 = std::move(nums);
                else if (attr == "index_2" || attr == "variable_2") flat_axis2 = std::move(nums);
                else if (attr == "index_3" || attr == "variable_3") flat_axis3 = std::move(nums);
                else if (attr == "values") flat_current = std::move(nums);
            } else {
                consume();
                expect(TokenType::Semi);
            }
        }
        if (peek().type == TokenType::RBrace) consume();
    } else {
        expect(TokenType::Semi);
        return;
    }

    // ── Build table from nested vectors (industrial format) ──
    if (!vectors.empty()) {
        std::set<float> slew_set, cap_set;
        for (const auto& v : vectors) {
            slew_set.insert(v.slew);
            cap_set.insert(v.cap);
        }
        table->input_slews.assign(slew_set.begin(), slew_set.end());
        table->load_caps.assign(cap_set.begin(), cap_set.end());
        table->nslew = static_cast<uint32_t>(table->input_slews.size());
        table->ncap  = static_cast<uint32_t>(table->load_caps.size());

        std::map<std::pair<float, float>, size_t> idx_map;
        for (size_t i = 0; i < vectors.size(); ++i) {
            idx_map[{vectors[i].slew, vectors[i].cap}] = i;
        }

        table->waveforms.resize(table->nslew * table->ncap);
        for (size_t si = 0; si < table->nslew; ++si) {
            for (size_t ci = 0; ci < table->ncap; ++ci) {
                auto it = idx_map.find({table->input_slews[si], table->load_caps[ci]});
                if (it != idx_map.end()) {
                    const auto& src = vectors[it->second];
                    ec::CsmWaveform& dst = table->waveforms[si * table->ncap + ci];
                    dst.time_points = src.time;
                    dst.current = src.current;
                    dst.reference_time = src.reference_time;
                }
            }
        }
        return;
    }

    // ── Build table from flat format (simple test libraries) ──
    if (!flat_axis1.empty()) {
        table->input_slews = flat_axis1;
        table->nslew = static_cast<uint32_t>(flat_axis1.size());
    } else if (!templates_[template_ref].axis1.empty()) {
        table->input_slews = templates_[template_ref].axis1;
        table->nslew = static_cast<uint32_t>(table->input_slews.size());
    }
    if (!flat_axis2.empty()) {
        table->load_caps = flat_axis2;
        table->ncap = static_cast<uint32_t>(flat_axis2.size());
    } else if (!templates_[template_ref].axis2.empty()) {
        table->load_caps = templates_[template_ref].axis2;
        table->ncap = static_cast<uint32_t>(table->load_caps.size());
    }

    uint32_t ntime = 0;
    if (!flat_axis3.empty()) {
        ntime = static_cast<uint32_t>(flat_axis3.size());
    }
    if (ntime == 0 && table->nslew > 0 && table->ncap > 0) {
        size_t total = flat_current.size();
        if (total > 0 && table->nslew * table->ncap > 0) {
            ntime = static_cast<uint32_t>(total / (table->nslew * table->ncap));
        }
    }
    if (table->nslew == 0 || table->ncap == 0 || ntime == 0) {
        size_t n = flat_current.size();
        if (n > 0 && ntime > 0 && table->ncap > 0) {
            table->nslew = static_cast<uint32_t>(n / (table->ncap * ntime));
        } else if (n > 0 && ntime > 0) {
            table->ncap = 1;
            table->nslew = static_cast<uint32_t>(n / ntime);
        } else if (n > 0) {
            table->ncap = 1;
            table->nslew = 1;
            ntime = static_cast<uint32_t>(n);
        }
    }

    if (table->nslew > 0 && table->ncap > 0 && ntime > 0) {
        table->waveforms.resize(table->nslew * table->ncap);
        for (size_t si = 0; si < table->nslew; ++si) {
            for (size_t ci = 0; ci < table->ncap; ++ci) {
                ec::CsmWaveform& wf = table->waveforms[si * table->ncap + ci];
                wf.time_points = flat_axis3;
                wf.current.resize(ntime);
                for (uint32_t ti = 0; ti < ntime; ++ti) {
                    size_t idx = ((si * table->ncap) + ci) * ntime + ti;
                    if (idx < flat_current.size()) {
                        wf.current[ti] = flat_current[idx];
                    }
                }
            }
        }
    }
}

void LibertyParser::parse_table_body(ec::NldmTable* table,
                                     const std::string& template_ref,
                                     ec::StringPool& strings) {
    (void)strings;
    if (!table) return;

    std::vector<float> axis1, axis2;
    std::string inline_var1, inline_var2;

    if (match(TokenType::LBrace)) {
        while (peek().type != TokenType::RBrace && peek().type != TokenType::Eof) {
            if (peek().type != TokenType::Ident) { consume(); continue; }
            std::string attr = peek().text;
            consume();
            if (peek().type == TokenType::Colon) consume();

            if (peek().type == TokenType::LParen) {
                consume();
                std::string val;
                while (!match(TokenType::RParen)) {
                    if (peek().type == TokenType::String) {
                        val += consume().text + " ";
                    } else if (peek().type == TokenType::Comma) {
                        consume();
                    } else {
                        val += consume().text + " ";
                    }
                }
                std::vector<float> nums = parse_index_values(val);
                if (attr == "index_1") axis1 = std::move(nums);
                else if (attr == "index_2") axis2 = std::move(nums);
                else if (attr == "variable_1") {
                    inline_var1 = val;
                    axis1 = std::move(nums);
                }
                else if (attr == "variable_2") {
                    inline_var2 = val;
                    axis2 = std::move(nums);
                }
                else if (attr == "values") {
                    table->values = std::move(nums);
                }
            } else {
                // Number or ident followed by semicolon
                std::string val;
                if (peek().type == TokenType::Number || peek().type == TokenType::Ident) {
                    val = peek().text;
                    consume();
                }
                if (attr == "variable_1") inline_var1 = val;
                else if (attr == "variable_2") inline_var2 = val;
                expect(TokenType::Semi);
            }
        }
        if (peek().type == TokenType::RBrace) consume();
    } else {
        expect(TokenType::Semi);
        return;
    }

    // Apply axis values: inline first, then template fallback, then sqrt inference.
    if (!axis1.empty()) {
        table->axis1 = axis1;
        table->rows = axis1.size();
    } else if (!templates_[template_ref].axis1.empty()) {
        table->axis1 = templates_[template_ref].axis1;
        table->rows = table->axis1.size();
    }
    if (!axis2.empty()) {
        table->axis2 = axis2;
        table->cols = axis2.size();
    } else if (!templates_[template_ref].axis2.empty()) {
        table->axis2 = templates_[template_ref].axis2;
        table->cols = table->axis2.size();
    }
    // A one-dimensional template has no second axis. Preserve its declared
    // extent rather than guessing a square from the number of values.
    if (table->rows > 0 && table->axis2.empty()) {
        table->cols = 1;
    }
    if (table->rows == 0 || table->cols == 0) {
        size_t n = table->values.size();
        size_t dim = static_cast<size_t>(std::sqrt(n));
        if (dim > 0 && dim * dim == n) {
            table->rows = dim;
            table->cols = dim;
        } else if (n > 0) {
            table->rows = n;
            table->cols = 1;
        }
    }
}

void LibertyParser::normalize_nldm_axes(ec::NldmTable* table, const std::string& template_ref,
                                         bool is_constraint) {
    if (!table || table->rows == 0 || table->cols == 0) return;

    // Determine the semantic meaning of axis1/axis2 from template or inline vars.
    std::string var1, var2;
    auto it = templates_.find(template_ref);
    if (it != templates_.end()) {
        var1 = it->second.var1;
        var2 = it->second.var2;
    }

    bool need_swap = false;
    if (is_constraint) {
        // Constraints: callers pass (related_pin_slew, constrained_pin_slew) and
        // expect axis1 = related_pin_transition, axis2 = constrained_pin_transition.
        // If the template declares variable_1 = constrained_pin_transition, we must
        // swap so that axis1 becomes related_pin (from index_2) and axis2 becomes
        // constrained_pin (from index_1).
        if (var1 == "constrained_pin_transition") {
            need_swap = true;
        }
    }
    // Gate callers pass (input_transition, output_capacitance). Honor the
    // Liberty template, including load-only tables (which become 1 x N).
    if (!is_constraint && var1 == "total_output_net_capacitance") {
        need_swap = true;
    }
    if (need_swap) {
        // Transpose values array so row-major layout matches swapped axes.
        size_t old_rows = table->rows;
        size_t old_cols = table->cols;
        std::vector<float> transposed(old_rows * old_cols);
        for (size_t r = 0; r < old_rows; ++r) {
            for (size_t c = 0; c < old_cols; ++c) {
                transposed[c * old_rows + r] = table->values[r * old_cols + c];
            }
        }
        table->values = std::move(transposed);
        std::swap(table->axis1, table->axis2);
        std::swap(table->rows, table->cols);
    }
}

} // namespace te::parser
