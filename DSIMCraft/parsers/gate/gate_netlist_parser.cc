#include "gate_netlist_parser.hh"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>

namespace te {

static std::vector<std::string> parse_concatenation(const std::string& concat);

// Network pin directions are relative to the owning instance.  The synthetic
// __top__ instance therefore sees an RTL input as an output pin (it drives the
// internal design) and an RTL output as an input pin (the design drives it).
// Leaf-cell directions keep their ordinary Liberty meaning.
static PortDirection top_instance_port_direction(PortDirection rtl_direction) {
    if (rtl_direction == PortDirection::Input) return PortDirection::Output;
    if (rtl_direction == PortDirection::Output) return PortDirection::Input;
    return rtl_direction;
}

// ============================================================================
// Helpers
// ============================================================================

static std::string read_file(std::string_view path) {
    std::ifstream f(std::string{path}, std::ios::binary);
    if (!f) throw std::runtime_error("Cannot open file: " + std::string{path});
    std::string content((std::istreambuf_iterator<char>(f)),
                         std::istreambuf_iterator<char>());
    return content;
}

static bool is_verilog_id_start(char c) {
    return std::isalpha(static_cast<unsigned char>(c)) || c == '_' || c == '\\';
}

static bool is_verilog_id_body(char c) {
    return std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '$';
}

static std::optional<int> scalar_constant_literal_value(std::string_view text) {
    if (text == "0") return 0;
    if (text == "1") return 1;

    size_t quote = text.find('\'');
    if (quote == std::string_view::npos) return std::nullopt;
    if (quote == 0) return std::nullopt;

    uint64_t width = 0;
    for (size_t i = 0; i < quote; ++i) {
        char ch = text[i];
        if (!std::isdigit(static_cast<unsigned char>(ch))) return std::nullopt;
        width = width * 10 + static_cast<uint64_t>(ch - '0');
        if (width > 1) return std::nullopt;
    }
    if (width != 1) return std::nullopt;

    size_t base_pos = quote + 1;
    if (base_pos < text.size() &&
        (text[base_pos] == 's' || text[base_pos] == 'S')) {
        ++base_pos;
    }
    if (base_pos >= text.size()) return std::nullopt;
    char base = static_cast<char>(
        std::tolower(static_cast<unsigned char>(text[base_pos])));
    if (base != 'b' && base != 'o' && base != 'd' && base != 'h') {
        return std::nullopt;
    }

    std::string digits;
    digits.reserve(text.size() - base_pos - 1);
    for (size_t i = base_pos + 1; i < text.size(); ++i) {
        if (text[i] == '_') continue;
        digits.push_back(static_cast<char>(
            std::tolower(static_cast<unsigned char>(text[i]))));
    }
    if (digits.size() != 1) return std::nullopt;
    if (digits[0] == '0') return 0;
    if (digits[0] == '1') return 1;
    return std::nullopt;
}

static bool is_sized_cast_width(std::string_view text) {
    // The lexer intentionally keeps the quote in a token such as `32'` so it
    // can distinguish a sized cast from an ordinary decimal number.  Based
    // literals (for example `32'd9`) have characters after the quote and are
    // therefore excluded here.
    if (text.size() < 2 || text.back() != '\'') return false;
    for (size_t i = 0; i + 1 < text.size(); ++i) {
        if (!std::isdigit(static_cast<unsigned char>(text[i]))) return false;
    }
    return true;
}

// ============================================================================
// Tokenizer
// ============================================================================

GateNetlistParser::Tokenizer::Tokenizer(std::string_view source)
    : begin_(source.data()), end_(source.data() + source.size()),
      pos_(begin_), line_(1), col_(1) {
    current_ = next();
}

bool GateNetlistParser::Tokenizer::expect(TokenType t, const char* context) {
    if (current_.type == t) {
        consume();
        return true;
    }
    std::string msg = "Expected ";
    msg += context;
    msg += " but got '";
    msg += current_.text;
    msg += "'";
    throw std::runtime_error(msg + " at line " + std::to_string(current_.line));
}

void GateNetlistParser::Tokenizer::advance_char() {
    if (pos_ >= end_) return;
    if (*pos_ == '\n') {
        ++line_;
        col_ = 1;
    } else {
        ++col_;
    }
    ++pos_;
}

GateNetlistParser::Token
GateNetlistParser::Tokenizer::make_token(TokenType t,
                                          const char* start, size_t len) {
    return Token{t, std::string(start, len), line_, col_};
}

void GateNetlistParser::Tokenizer::skip_whitespace_and_comments() {
    while (pos_ < end_) {
        char c = *pos_;
        if (std::isspace(static_cast<unsigned char>(c))) {
            advance_char();
        } else if (c == '/' && pos_ + 1 < end_) {
            if (pos_[1] == '/') {
                // line comment
                while (pos_ < end_ && *pos_ != '\n') advance_char();
            } else if (pos_[1] == '*') {
                // block comment
                advance_char(); // /
                advance_char(); // *
                while (pos_ + 1 < end_) {
                    if (*pos_ == '*' && pos_[1] == '/') {
                        advance_char();
                        advance_char();
                        break;
                    }
                    advance_char();
                }
            } else {
                break;
            }
        } else {
            break;
        }
    }
}

GateNetlistParser::Token GateNetlistParser::Tokenizer::next() {
    skip_whitespace_and_comments();
    if (pos_ >= end_) {
        token_start_ = pos_;
        return Token{TokenType::EOI, "", line_, col_};
    }

    token_start_ = pos_;
    const char* start = pos_;
    uint32_t tk_line = line_;
    uint32_t tk_col = col_;
    char c = *pos_;

    // Single-char tokens
    switch (c) {
        case '(': advance_char(); return Token{TokenType::LParen, "(", tk_line, tk_col};
        case ')': advance_char(); return Token{TokenType::RParen, ")", tk_line, tk_col};
        case '[': advance_char(); return Token{TokenType::LBracket, "[", tk_line, tk_col};
        case ']': advance_char(); return Token{TokenType::RBracket, "]", tk_line, tk_col};
        case '{': advance_char(); return Token{TokenType::LBrace, "{", tk_line, tk_col};
        case '}': advance_char(); return Token{TokenType::RBrace, "}", tk_line, tk_col};
        case ',': advance_char(); return Token{TokenType::Comma, ",", tk_line, tk_col};
        case ';': advance_char(); return Token{TokenType::Semi, ";", tk_line, tk_col};
        case '.': advance_char(); return Token{TokenType::Dot, ".", tk_line, tk_col};
        case '=': advance_char(); return Token{TokenType::Eq, "=", tk_line, tk_col};
        case ':': advance_char(); return Token{TokenType::Colon, ":", tk_line, tk_col};
        default: break;
    }

    // Escaped identifier: \name<space_or_tab>
    if (c == '\\') {
        advance_char(); // backslash
        const char* id_start = pos_;
        while (pos_ < end_ && !std::isspace(static_cast<unsigned char>(*pos_))) {
            advance_char();
        }
        std::string text(id_start, pos_);
        // consume the terminating whitespace (usually space or tab)
        if (pos_ < end_ && std::isspace(static_cast<unsigned char>(*pos_))) {
            advance_char();
        }
        return Token{TokenType::Identifier, text, tk_line, tk_col};
    }

    // Number (including based numbers like 1'b0, 32'd9, 8'hFF)
    if (std::isdigit(static_cast<unsigned char>(c)) || (c == '\'' && pos_ + 1 < end_ && std::string("01xXzZbBoOdDhHsS").find(pos_[1]) != std::string::npos)) {
        const char* num_start = pos_;
        while (pos_ < end_ && (std::isdigit(static_cast<unsigned char>(*pos_)) || *pos_ == '_')) {
            advance_char();
        }
        // Based literals, signed modifiers and unbased context-fill literals.
        if (pos_ < end_ && *pos_ == '\'') {
            advance_char();
            if (pos_ < end_ && (*pos_ == '0' || *pos_ == '1' || *pos_ == 'x' || *pos_ == 'X' || *pos_ == 'z' || *pos_ == 'Z') && num_start == start && c == '\'') {
                advance_char();
            } else {
                if (pos_ < end_ && (*pos_ == 's' || *pos_ == 'S')) advance_char();
                if (pos_ < end_ && std::string("bBoOdDhH").find(*pos_) != std::string::npos) advance_char();
                while (pos_ < end_ && (std::isalnum(static_cast<unsigned char>(*pos_)) || *pos_ == '_' || *pos_ == '?')) advance_char();
            }
        }
        return Token{TokenType::Number, std::string(num_start, pos_), tk_line, tk_col};
    }

    // Identifier or keyword
    if (is_verilog_id_start(c)) {
        const char* id_start = pos_;
        advance_char();
        while (pos_ < end_ && is_verilog_id_body(*pos_)) {
            advance_char();
        }
        std::string text(id_start, pos_);

        if (text == "module")      return Token{TokenType::Module, text, tk_line, tk_col};
        if (text == "endmodule")   return Token{TokenType::EndModule, text, tk_line, tk_col};
        if (text == "input")       return Token{TokenType::Input, text, tk_line, tk_col};
        if (text == "output")      return Token{TokenType::Output, text, tk_line, tk_col};
        if (text == "inout")       return Token{TokenType::Inout, text, tk_line, tk_col};
        if (text == "wire" || text == "tri") return Token{TokenType::Wire, text, tk_line, tk_col};
        if (text == "reg")         return Token{TokenType::Reg, text, tk_line, tk_col};
        if (text == "assign")      return Token{TokenType::Assign, text, tk_line, tk_col};
        if (text == "always")      return Token{TokenType::Always, text, tk_line, tk_col};

        return Token{TokenType::Identifier, text, tk_line, tk_col};
    }

    // Unknown character — skip and treat as identifier for robustness
    advance_char();
    return Token{TokenType::Identifier, std::string(start, pos_),
                 tk_line, tk_col};
}

// ============================================================================
// Parser public API
// ============================================================================

GateNetlistParser::GateNetlistParser(Network& network)
    : network_(network) {}

std::vector<GateNetlistParser::PortInfo> GateNetlistParser::top_ports() const {
    const auto& meta = modules_.at(selected_top_);
    std::vector<PortInfo> result;
    for (const auto& port : meta.ports) {
        auto bits = meta.signal_bits.find(port.first);
        result.push_back({port.first, port.second,
            bits == meta.signal_bits.end() ? std::vector<std::string>{port.first} : bits->second});
    }
    return result;
}

std::string GateNetlistParser::simulation_identifier(Tokenizer& tok) {
    using T = TokenType;
        if (tok.peek().type != T::Identifier) error(tok, "expected identifier");
        auto text = tok.peek().text;
        bool escaped = *tok.token_start() == '\\';
        if (text.empty()) error(tok, "empty escaped gate identifier");
        static const std::unordered_set<std::string> reserved = {
            "begin","end","initial","generate","endgenerate","for","while","repeat","forever",
            "if","else","case","casez","casex","endcase","default","parameter","localparam",
            "specify","endspecify","tri","tri0","tri1","supply0","supply1","wand","wor",
            "triand","trior","trireg","logic","integer","int","signed","unsigned","event",
            "task","function","endtask","endfunction","real","realtime","time","genvar",
            "automatic","deassign","force","release","fork","join","disable","defparam",
            "buf","not","and","nand","or","nor","xor","xnor","bufif0","bufif1","tran",
            "rtran","tranif0","tranif1","rtranif0","rtranif1","pullup","pulldown"
        };
        if (!escaped && reserved.count(text)) error(tok, "expected identifier, found reserved keyword " + text);
        if (!escaped && (text.empty() || !is_verilog_id_start(text.front()))) error(tok, "expected identifier");
        if (escaped && (text.find_first_of("[]'") != std::string::npos || text == "0" || text == "1"))
            error(tok, "escaped scalar names containing brackets/quotes or literal names require a distinct-name representation");
        if (text.rfind("__dsim_", 0) == 0) error(tok, "reserved generated gate identifier");
        tok.consume(); return text;
}

// Simulation connections are transient bit vectors, not expression AST nodes.
// Their width is independent of the RTL runtime's packed word size.
GateNetlistParser::SimulationReference GateNetlistParser::simulation_reference(
    Tokenizer& tok, bool target, unsigned depth) {
    using T = TokenType;
    if (depth > 128) error(tok, "structural concatenation nesting exceeds 128");
    SimulationReference result;
    auto require = [&](T type, const char* message) { if (!tok.match(type)) error(tok, message); };
    auto append = [&](const SimulationReference& part) {
        if (part.bits.size() > 1000000 - result.bits.size()) error(tok, "structural connection width exceeds 1000000");
        result.bits.insert(result.bits.end(), part.bits.begin(), part.bits.end());
    };
    auto decimal = [&]() {
        const auto text = tok.peek().text;
        if (tok.peek().type != T::Number || text.empty() || text.find_first_not_of("0123456789") != std::string::npos)
            error(tok, "structural selects require nonnegative decimal indices");
        if (text.size() > 7 || std::stoul(text) > 1000000) error(tok, "gate packed index exceeds 1000000");
        tok.consume(); return int(std::stoul(text));
    };
    if (tok.match(T::LBrace)) {
        if (tok.peek().type == T::RBrace) error(tok, "empty structural concatenation");
        // A replication count must be a nonnegative decimal constant.
        Tokenizer look = tok;
        bool replication = false;
        if (look.peek().type == T::Number) { look.consume(); replication = look.peek().type == T::LBrace; }
        if (replication) {
            if (target) error(tok, "replication is not a structural output lvalue");
            int count = decimal();
            auto part = simulation_reference(tok, false, depth + 1);
            require(T::RBrace, "expected '}' after structural replication");
            if (!count || part.bits.empty()) error(tok, "zero-width structural replication");
            if (part.bits.size() > size_t(1000000 / count)) error(tok, "structural connection width exceeds 1000000");
            result.bits.reserve(part.bits.size() * size_t(count));
            while (count--) append(part);
        } else {
            do { append(simulation_reference(tok, target, depth + 1)); } while (tok.match(T::Comma));
            require(T::RBrace, "expected '}' after structural concatenation");
        }
        return result;
    }
    if (tok.peek().type == T::Number) {
        if (target) error(tok, "gate output cannot drive a constant");
        std::string text;
        for (unsigned char c : tok.peek().text) if (c != '_') text += char(std::tolower(c));
        tok.consume();
        size_t quote = text.find('\'');
        bool unbased = quote == 0 && text.size() == 2 && std::string("01xz").find(text[1]) != std::string::npos;
        bool unsized = quote == std::string::npos || quote == 0;
        if (depth && unsized && !unbased) error(tok, "unsized constant in structural concatenation");
        bool is_signed = quote == std::string::npos;
        std::string value;
        size_t width = 32;
        if (unbased) {
            result.fill = text[1]; value = text.substr(1); width = 1;
        } else {
            char base = 'd';
            std::string digits = text;
            if (quote != std::string::npos) {
                if (quote) {
                    auto size = text.substr(0, quote);
                    if (size.size() > 7 || size.find_first_not_of("0123456789") != std::string::npos)
                        error(tok, "invalid structural literal width");
                    width = std::stoul(size);
                }
                size_t at = quote + 1;
                if (at < text.size() && text[at] == 's') { is_signed = true; ++at; }
                if (at >= text.size()) error(tok, "invalid structural constant (casts are unsupported)");
                base = text[at]; digits = text.substr(at + 1);
            }
            if (!width || width > 1000000 || digits.empty() || digits.size() > 250000)
                error(tok, "invalid structural literal width/digits");
            if (base == 'b' || base == 'o' || base == 'h') {
                int shift = base == 'b' ? 1 : base == 'o' ? 3 : 4;
                for (char c : digits) {
                    if (c == 'x' || c == 'z' || c == '?') value.append(size_t(shift), c == '?' ? 'z' : c);
                    else {
                        int digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
                        if (digit < 0 || digit >= (1 << shift)) error(tok, "invalid structural based digit");
                        for (int i = shift - 1; i >= 0; --i) value += (digit >> i) & 1 ? '1' : '0';
                    }
                }
                if (unsized) width = std::max(width, value.size());
            } else if (base == 'd') {
                if (digits == "x" || digits == "z" || digits == "?") value.assign(width, digits.front() == '?' ? 'z' : digits.front());
                else {
                    if (digits.find_first_not_of("0123456789") != std::string::npos) error(tok, "invalid structural decimal constant");
                    // VCS plain decimal integers are signed 32-bit; based literals
                    // may carry a larger self-determined width.
                    size_t capacity = unsized && quote != std::string::npos ? std::max(width, digits.size() * 4) : width;
                    std::vector<unsigned char> binary(capacity, 0);
                    for (char c : digits) {
                        unsigned carry = unsigned(c - '0');
                        for (auto& bit : binary) { carry += unsigned(bit) * 10; bit = carry & 1; carry >>= 1; }
                    }
                    auto first = binary.size();
                    while (first > 1 && binary[first - 1] == 0) --first;
                    while (first) value += char('0' + binary[--first]);
                    if (unsized && quote != std::string::npos) width = std::max(width, value.size());
                }
            } else error(tok, "invalid structural constant base (casts are unsupported)");
            if (width > 1000000) error(tok, "structural literal width exceeds 1000000");
            if (value.size() < width) value.insert(0, width - value.size(), value.front() == 'x' || value.front() == 'z' ? value.front() : '0');
            if (value.size() > width) value.erase(0, value.size() - width);
            // Sized unsigned X/Z extends with zero; signed and unsized based
            // X/Z literals carry their leading state into the context width.
            if (is_signed || (unsized && (value.front() == 'x' || value.front() == 'z'))) result.fill = value.front();
        }
        result.bits.reserve(width);
        for (char c : value) result.bits.push_back(std::string("1'b") + c);
        return result;
    }
    auto name = simulation_identifier(tok);
    auto mod = modules_.find(current_module_);
    auto declared = mod->second.signal_bits.find(name);
    if (tok.match(T::LBracket)) {
        int first = decimal(), last = first;
        if (tok.match(T::Colon)) last = decimal();
        require(T::RBracket, "expected ']' after structural select");
        if (declared == mod->second.signal_bits.end() || declared->second.empty() || declared->second.front() == name)
            error(tok, "undeclared or out-of-range bit " + name);
        const auto& bits = declared->second;
        auto index = [&](const std::string& bit) { return std::stoi(bit.substr(name.size() + 1)); };
        int high = index(bits.front()), low = index(bits.back());
        if (first < std::min(high, low) || first > std::max(high, low) || last < std::min(high, low) || last > std::max(high, low))
            error(tok, "undeclared or out-of-range bit " + name);
        if (first != last && ((first > last) != (high > low))) error(tok, "part-select direction disagrees with declaration");
        for (int i = first;; i += first <= last ? 1 : -1) {
            result.bits.push_back(name + "[" + std::to_string(i) + "]");
            if (i == last) break;
        }
    } else if (declared != mod->second.signal_bits.end()) result.bits = declared->second;
    else result.bits.push_back(name); // Verilog's implicit scalar wire.
    if (tok.peek().type == T::LBracket) error(tok, "multidimensional structural selects are not supported");
    if (flattening_) for (auto& bit : result.bits) bit = remap_net_name(bit);
    return result;
}

std::vector<std::string> GateNetlistParser::simulation_resize(const SimulationReference& ref, size_t width) {
    auto bits = ref.bits;
    if (bits.size() > width) bits.erase(bits.begin(), bits.end() - width);
    else if (bits.size() < width) bits.insert(bits.begin(), width - bits.size(), std::string("1'b") + (ref.fill ? ref.fill : '0'));
    return bits;
}

NetId GateNetlistParser::simulation_net(const std::string& name) {
    auto found = network_.find_net(name);
    NetId id = found ? *found : network_.create_net(name);
    if (auto value = scalar_constant_literal_value(name)) network_.set_net_constant(id, *value);
    return id;
}

void GateNetlistParser::simulation_copy(const std::vector<std::string>& target, const std::vector<std::string>& source) {
    if (target.size() != source.size() || target.empty()) throw std::runtime_error("invalid structural copy width");
    const bool scalar = target.size() == 1;
    const auto cell_name = scalar ? "__assign__" : "__dsim_copy_" + std::to_string(target.size());
    auto found = network_.find_cell(cell_name);
    auto cell = found ? *found : network_.create_cell(cell_name);
    std::string generated;
    do { generated = "__dsim_generated_" + std::to_string(simulation_generated_++); } while (network_.find_instance(generated));
    auto inst = network_.create_instance(generated, cell);
    for (size_t i = 0; i < target.size(); ++i) {
        for (int output = 0; output < 2; ++output) {
            const auto pin_name = scalar ? (output ? "X" : "A") : (output ? "X" : "A") + std::to_string(i);
            auto pin = network_.create_pin(pin_name, inst, output ? PortDirection::Output : PortDirection::Input);
            network_.add_pin(inst, pin);
            network_.connect_pin_to_net(pin, simulation_net(output ? target[i] : source[i]));
        }
    }
}

void GateNetlistParser::simulation_assign(Tokenizer& tok) {
    auto target = simulation_reference(tok, true);
    tok.expect(TokenType::Eq, "=");
    auto source = simulation_reference(tok, false);
    if (!tok.match(TokenType::Semi)) error(tok, "gate simulation does not approximate expressions; use a cell model");
    simulation_copy(target.bits, simulation_resize(source, target.bits.size()));
}

void GateNetlistParser::simulation_instance(Tokenizer& tok, const std::string& cell_name, const std::string& name) {
    using T = TokenType;
    tok.expect(T::LParen, "(");
    struct Connection { std::string port; SimulationReference actual; };
    std::vector<Connection> connections;
    const auto definition = modules_.find(cell_name);
    const auto library = simulation_ports_.find(cell_name);
    const bool hierarchical = definition != modules_.end() && (definition->second.has_logic || library == simulation_ports_.end());
    const auto* formals = hierarchical ? &definition->second.ports : library != simulation_ports_.end() ? &library->second : nullptr;
    auto direction = [&](const std::string& port) {
        if (formals) for (const auto& p : *formals) if (p.first == port) return p.second;
        return PortDirection::Input; // unbound cells are diagnosed by the binder.
    };
    bool named = tok.peek().type == T::Dot;
    size_t position = 0;
    if (!tok.match(T::RParen)) for (;;) {
        std::string port;
        SimulationReference actual;
        if (named) {
            tok.expect(T::Dot, "."); port = simulation_identifier(tok); tok.expect(T::LParen, "(");
            if (tok.peek().type != T::RParen) actual = simulation_reference(tok, direction(port) != PortDirection::Input);
            tok.expect(T::RParen, ")");
        } else {
            if (definition == modules_.end() || position >= definition->second.ports.size()) error(tok, "positional leaf connections require a Verilog port declaration");
            port = definition->second.ports[position++].first;
            if (tok.peek().type != T::Comma && tok.peek().type != T::RParen) actual = simulation_reference(tok, direction(port) != PortDirection::Input);
        }
        connections.push_back({port, std::move(actual)});
        if (tok.match(T::RParen)) break;
        tok.expect(T::Comma, ",");
    }
    tok.expect(T::Semi, ";");
    const auto prefix = flatten_inst_prefix_.empty() ? name : flatten_inst_prefix_ + "/" + name;
    if (hierarchical) {
        std::unordered_map<std::string, std::string> mapping;
        for (const auto& port : definition->second.ports) {
            const auto declared = definition->second.signal_bits.find(port.first);
            const auto local = declared == definition->second.signal_bits.end() ? std::vector<std::string>{port.first} : declared->second;
            auto conn = std::find_if(connections.begin(), connections.end(), [&](const auto& c) { return c.port == port.first; });
            const bool connected = conn != connections.end() && !conn->actual.bits.empty();
            if (connected && port.second == PortDirection::Inout && conn->actual.bits.size() != local.size()) error(tok, "inout gate port width mismatch");
            std::vector<std::string> inner, copy_to, copy_from;
            const auto padded = connected && port.second == PortDirection::Input ? simulation_resize(conn->actual, local.size()) : std::vector<std::string>{};
            for (size_t i = 0; i < local.size(); ++i) {
                const auto offset = int64_t(i) + (connected ? int64_t(conn->actual.bits.size()) : 0) - int64_t(local.size());
                const bool matched = connected && offset >= 0 && size_t(offset) < conn->actual.bits.size();
                const auto source = matched ? conn->actual.bits[size_t(offset)] : std::string{};
                const bool constant = source.rfind("1'b", 0) == 0;
                const bool shared = matched && !constant;
                auto bit = shared ? source : prefix + "/" + local[i];
                mapping[local[i]] = bit; inner.push_back(bit);
                simulation_net(bit);
                // Literal/padded inputs have local drivers: writing the input
                // must never drive a globally shared literal net backwards.
                if (connected && port.second == PortDirection::Input && !shared) {
                    copy_to.push_back(bit); copy_from.push_back(padded[i]);
                }
            }
            if (!copy_to.empty()) simulation_copy(copy_to, copy_from);
            if (connected && port.second == PortDirection::Output && conn->actual.bits.size() > local.size()) {
                // Output widening aliases the common low bits and drives
                // only the additional high bits with unsigned zero padding.
                std::vector<std::string> high(conn->actual.bits.begin(), conn->actual.bits.end() - local.size());
                simulation_copy(high, std::vector<std::string>(high.size(), "1'b0"));
            }
        }
        flatten_module(cell_name, name, mapping);
        return;
    }
    auto found = network_.find_cell(cell_name);
    auto cell = found ? *found : network_.create_cell(cell_name);
    auto inst = network_.create_instance(prefix, cell);
    if (timing_leaf_) {
        timing_path_.push_back(name); timing_leaf_(inst, timing_path_); timing_path_.pop_back();
    }
    for (auto& conn : connections) {
        auto dir = direction(conn.port);
        auto pin = network_.create_pin(conn.port, inst, dir);
        network_.add_pin(inst, pin);
        if (conn.actual.bits.empty()) continue;
        std::string bit;
        if (dir == PortDirection::Input) bit = simulation_resize(conn.actual, 1).front();
        else if (conn.actual.bits.size() == 1) bit = conn.actual.bits.front();
        else {
            bit = conn.actual.bits.back();
            std::vector<std::string> high(conn.actual.bits.begin(), conn.actual.bits.end() - 1);
            simulation_copy(high, std::vector<std::string>(high.size(), "1'b0"));
        }
        network_.connect_pin_to_net(pin, simulation_net(bit));
    }
}

// A streaming grammar check, separate from the timing parser's deliberately
// permissive expression approximation. It creates no expression/statement AST.
void GateNetlistParser::validate_simulation_source() {
    Tokenizer tok(source_);
    using T = TokenType;
    auto require = [&](T type, const char* message) {
        if (!tok.match(type)) error(tok, message);
    };
    auto identifier = [&]() { return simulation_identifier(tok); };
    auto decimal = [&]() {
        auto text = tok.peek().text;
        if (tok.peek().type != T::Number || text.empty() ||
            text.find_first_not_of("0123456789") != std::string::npos)
            error(tok, "simulation requires nonnegative decimal indices");
        auto value = std::stoull(text);
        if (value > 1000000) error(tok, "gate packed index exceeds 1000000");
        tok.consume(); return value;
    };
    auto range = [&]() {
        if (tok.match(T::LBracket)) {
            auto high = decimal(); require(T::Colon, "expected ':' in packed range");
            auto low = decimal(); require(T::RBracket, "expected ']' in packed range");
            (void)high; (void)low;
        }
    };
    std::unordered_set<std::string> module_names;
    while (tok.peek().type != T::EOI) {
        require(T::Module, "gate simulation expects a structural module");
        auto module = identifier();
        if (!module_names.insert(module).second) error(tok, "duplicate module " + module);
        if (module == "__assign__" || module == "__top__") error(tok, "reserved gate module name");
        const auto& meta = modules_.at(module);
        current_module_ = module;
        auto reference = [&](bool target) { return simulation_reference(tok, target); };
        if (tok.match(T::LParen)) {
            std::unordered_set<std::string> ports;
            if (!tok.match(T::RParen)) for (;;) {
                if (tok.peek().type == T::Input || tok.peek().type == T::Output || tok.peek().type == T::Inout) {
                    tok.consume(); tok.match(T::Wire); range();
                }
                auto name = identifier();
                if (!ports.insert(name).second) error(tok, "duplicate module port " + name);
                if (tok.match(T::RParen)) break;
                require(T::Comma, "expected ',' in gate port list");
            }
        }
        require(T::Semi, "expected ';' after gate module header");
        std::unordered_set<std::string> instances;
        while (!tok.match(T::EndModule)) {
            auto kind = tok.peek().type;
            if (kind == T::Input || kind == T::Output || kind == T::Inout || kind == T::Wire) {
                tok.consume(); if (kind != T::Wire) tok.match(T::Wire); range();
                identifier(); while (tok.match(T::Comma)) identifier();
                require(T::Semi, "unsupported gate declaration (only wires and packed ports)");
            } else if (tok.match(T::Assign)) {
                reference(true); require(T::Eq, "expected '=' in structural assign");
                reference(false); require(T::Semi, "gate simulation does not approximate expressions; use a cell model");
            } else if (kind == T::Identifier) {
                auto cell = identifier();
                if (cell == "__assign__" || cell == "__top__") error(tok, "reserved gate cell name");
                auto instance = identifier();
                if (!instances.insert(instance).second) error(tok, "duplicate gate instance " + instance);
                require(T::LParen, "expected '(' after gate instance name");
                bool named = tok.peek().type == T::Dot;
                if (!named && modules_.find(cell) == modules_.end())
                    error(tok, "positional leaf connections require a Verilog port declaration");
                auto definition = modules_.find(cell);
                auto target_port = [&](const std::string& port) {
                    auto lib = simulation_ports_.find(cell);
                    if (lib != simulation_ports_.end()) {
                        for (const auto& pin : lib->second) if (pin.first == port)
                            return pin.second != PortDirection::Input;
                        error(tok, "unknown pin " + cell + "." + port);
                    }
                    if (definition == modules_.end()) return false;
                    for (const auto& formal : definition->second.ports) if (formal.first == port)
                        return formal.second != PortDirection::Input;
                    error(tok, "unknown hierarchical gate port " + cell + "." + port);
                    return false;
                };
                size_t position = 0;
                std::unordered_set<std::string> pins;
                if (!tok.match(T::RParen)) for (;;) {
                    if (named) {
                        require(T::Dot, "cannot mix named and positional gate connections");
                        auto pin = identifier();
                        if (!pins.insert(pin).second) error(tok, "duplicate gate pin " + pin);
                        require(T::LParen, "expected '(' after gate pin");
                        bool target = target_port(pin);
                        if (tok.peek().type != T::RParen) reference(target);
                        require(T::RParen, "gate pin requires a structural net reference");
                    } else {
                        if (position >= definition->second.ports.size()) error(tok, "too many positional gate ports");
                        bool target = target_port(definition->second.ports[position++].first);
                        if (tok.peek().type != T::Comma && tok.peek().type != T::RParen) reference(target);
                    }
                    if (tok.match(T::RParen)) break;
                    require(T::Comma, "expected ',' between gate connections");
                }
                require(T::Semi, "expected ';' after gate instance");
            } else error(tok, "unsupported gate simulation construct: " + tok.peek().text);
        }
    }
}

std::string GateNetlistParser::parse(std::string_view filepath,
                                     std::string_view preferred_top_name) {
    return parse_source(read_file(filepath), filepath, preferred_top_name);
}

std::string GateNetlistParser::parse_source(std::string source, std::string_view filepath,
                                            std::string_view preferred_top_name) {
    // Clear state from any previous parse
    source_.clear();
    modules_.clear();
    inferred_cells_.clear();
    instantiated_modules_.clear();
    dummy_net_counter_ = 0;
    simulation_generated_ = 0;
    flatten_inst_prefix_.clear();
    timing_path_.clear();
    if ((timing_leaf_ || timing_scope_) && !simulation_mode_)
        throw std::runtime_error("timing observers require simulation mode");
    flatten_net_map_.clear();
    flattening_ = false;
    flatten_depth_ = 0;

    // Pass 1: collect metadata (module definitions & cell types)
    source_ = std::move(source);
    collect_metadata(filepath);
    if (simulation_mode_) validate_simulation_source();

    std::string top_name;
    if (!preferred_top_name.empty()) {
        auto preferred = modules_.find(std::string(preferred_top_name));
        if (preferred == modules_.end() || !preferred->second.defined) {
            throw std::runtime_error(
                "Requested top module not found in file: " +
                std::string(preferred_top_name));
        }
        top_name = preferred->first;
    } else {
        // Determine top module: the one never instantiated by others.
        // Explicit selection should be used when several roots exist because
        // unordered-map iteration order is intentionally unspecified.
        for (auto& [name, meta] : modules_) {
            if (instantiated_modules_.find(name) == instantiated_modules_.end()) {
                top_name = name;
                break;
            }
        }
    }
    if (top_name.empty() && !modules_.empty()) {
        top_name = modules_.begin()->first;
    }
    if (top_name.empty()) {
        throw std::runtime_error("No module found in file: " + std::string{filepath});
    }

    // Pass 2: build network from top module
    selected_top_ = top_name;
    build_network(filepath, top_name);
    return top_name;
}

// ============================================================================
// Pass 1: metadata collection
// ============================================================================

void GateNetlistParser::collect_metadata(std::string_view filepath) {
    (void)filepath;
    Tokenizer tok(source_);

    while (tok.peek().type != TokenType::EOI) {
        if (tok.match(TokenType::Module)) {
            if (tok.peek().type != TokenType::Identifier) {
                error(tok, "Expected module name after 'module'");
            }
            std::string mod_name = tok.peek().text;
            tok.consume();

            ModuleMeta& meta = modules_[mod_name];
            meta.defined = true;

            // Parse port list in header: module name (port1, port2, ...);
            if (tok.match(TokenType::LParen)) {
                scan_module_ports(tok, meta);
            }
            if (!tok.match(TokenType::Semi)) {
                error(tok, "Expected ';' after module header");
            }

            // Capture body start position
            const char* body_start = tok.token_start();

            // Scan body until endmodule
            while (tok.peek().type != TokenType::EOI) {
                if (tok.peek().type == TokenType::EndModule) {
                    meta.body = std::string_view(body_start,
                                                 tok.token_start() - body_start);
                    tok.consume(); // consume endmodule
                    break;
                }

                TokenType t = tok.peek().type;
                if (t == TokenType::Input || t == TokenType::Output ||
                    t == TokenType::Inout) {
                    PortDirection dir = PortDirection::Input;
                    if (t == TokenType::Output) dir = PortDirection::Output;
                    else if (t == TokenType::Inout) dir = PortDirection::Inout;
                    tok.consume();

                    tok.match(TokenType::Wire);
                    const auto suffixes = expand_range(tok, "");

                    // Collect identifiers until semicolon
                    while (tok.peek().type != TokenType::Semi &&
                           tok.peek().type != TokenType::EOI) {
                        if (tok.peek().type == TokenType::Identifier) {
                            auto& bits = meta.signal_bits[tok.peek().text];
                            bits.clear();
                            for (const auto& suffix : suffixes)
                                bits.push_back(tok.peek().text + suffix);
                            bool found = false;
                            for (auto& [pname, pdir] : meta.ports) {
                                if (pname == tok.peek().text) {
                                    pdir = dir;
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                meta.ports.push_back({tok.peek().text, dir});
                            }
                        }
                        tok.consume();
                    }
                    tok.expect(TokenType::Semi, ";");
                }
                else if (t == TokenType::Wire || t == TokenType::Reg) {
                    tok.consume();
                    const auto suffixes = expand_range(tok, "");
                    while (tok.peek().type != TokenType::Semi &&
                           tok.peek().type != TokenType::EOI) {
                        if (tok.peek().type == TokenType::Identifier) {
                            auto& bits = meta.signal_bits[tok.peek().text];
                            bits.clear();
                            for (const auto& suffix : suffixes)
                                bits.push_back(tok.peek().text + suffix);
                        }
                        tok.consume();
                    }
                    if (tok.peek().type == TokenType::Semi) tok.consume();
                }
                else if (t == TokenType::Assign) {
                    meta.has_logic = true;
                    tok.consume();
                    while (tok.peek().type != TokenType::Semi &&
                           tok.peek().type != TokenType::EOI) {
                        tok.consume();
                    }
                    if (tok.peek().type == TokenType::Semi) tok.consume();
                }
                else if (t == TokenType::Identifier) {
                    // Possible cell instantiation: CELL_TYPE inst_name ( ... );
                    std::string cell_name = tok.peek().text;
                    tok.consume();

                    if (tok.peek().type == TokenType::Identifier) {
                        std::string inst_name = tok.peek().text;
                        (void)inst_name;
                        tok.consume();
                        instantiated_modules_.insert(cell_name);
                        CellMeta& cm = inferred_cells_[cell_name];
                        meta.has_logic = true;

                        if (tok.match(TokenType::LParen)) {
                            while (tok.peek().type != TokenType::RParen &&
                                   tok.peek().type != TokenType::EOI) {
                                if (tok.match(TokenType::Dot)) {
                                    if (tok.peek().type == TokenType::Identifier) {
                                        cm.ports.insert(tok.peek().text);
                                    }
                                    tok.consume(); // port name
                                    if (tok.match(TokenType::LParen)) {
                                        while (tok.peek().type != TokenType::RParen &&
                                               tok.peek().type != TokenType::EOI) {
                                            tok.consume();
                                        }
                                        tok.expect(TokenType::RParen, ")");
                                    }
                                } else {
                                    tok.consume();
                                }
                            }
                            tok.expect(TokenType::RParen, ")");
                        }
                        if (!tok.match(TokenType::Semi)) {
                            if (strict_mode_) {
                                error(tok, "Expected ';' after instantiation");
                            }
                        }
                    } else {
                        // Not an instantiation — skip until semicolon
                        while (tok.peek().type != TokenType::Semi &&
                               tok.peek().type != TokenType::EOI) {
                            tok.consume();
                        }
                        if (tok.peek().type == TokenType::Semi) tok.consume();
                    }
                }
                else if (t == TokenType::Always) {
                    // Procedural blocks are outside the gate-level timing
                    // subset.  Skip the complete statement/block during the
                    // metadata pass so its event expression is not mistaken
                    // for a cell instantiation.
                    meta.has_logic = true;
                    tok.consume();
                    int begin_depth = 0;
                    while (tok.peek().type != TokenType::EOI) {
                        if (tok.peek().type == TokenType::Identifier &&
                            tok.peek().text == "begin") {
                            ++begin_depth;
                        } else if (tok.peek().type == TokenType::Identifier &&
                                   tok.peek().text == "end" && begin_depth > 0) {
                            --begin_depth;
                        }
                        const bool done = tok.peek().type == TokenType::Semi &&
                                          begin_depth == 0;
                        tok.consume();
                        if (done) break;
                    }
                }
                else {
                    tok.consume();
                }
            }
        } else {
            tok.consume();
        }
    }
}

void GateNetlistParser::scan_module_ports(Tokenizer& tok, ModuleMeta& meta) {
    PortDirection dir = PortDirection::Inout;
    std::vector<std::string> suffixes{ "" };
    while (tok.peek().type != TokenType::RParen &&
           tok.peek().type != TokenType::EOI) {
        if (tok.peek().type == TokenType::Input) {
            dir = PortDirection::Input;
            suffixes = { "" };
        } else if (tok.peek().type == TokenType::Output) {
            dir = PortDirection::Output;
            suffixes = { "" };
        } else if (tok.peek().type == TokenType::Inout) {
            dir = PortDirection::Inout;
            suffixes = { "" };
        } else if (tok.peek().type == TokenType::LBracket) {
            suffixes = expand_range(tok, "");
            continue;
        } else if (tok.peek().type == TokenType::Identifier) {
            meta.ports.push_back({tok.peek().text, dir});
            auto& bits = meta.signal_bits[tok.peek().text];
            for (const auto& suffix : suffixes)
                bits.push_back(tok.peek().text + suffix);
        }
        tok.consume();
    }
    tok.expect(TokenType::RParen, ")");
}

// ============================================================================
// Pass 2: network building
// ============================================================================

void GateNetlistParser::build_network(std::string_view filepath,
                                       std::string_view top_name) {
    (void)filepath;
    Tokenizer tok(source_);

    // Pre-create all cells (defined modules + inferred black-boxes)
    for (auto& [name, meta] : modules_) {
        CellId cid = network_.create_cell(name);
        for (auto& [pname, dir] : meta.ports) {
            network_.add_port(cid, pname);
        }
    }
    for (auto& [name, cm] : inferred_cells_) {
        if (network_.find_cell(name)) continue;
        CellId cid = network_.create_cell(name);
        for (auto& pname : cm.ports) {
            network_.add_port(cid, pname);
        }
    }
    // Ensure assign buffer cell exists
    if (!network_.find_cell("__assign__")) {
        CellId cid = network_.create_cell("__assign__");
        network_.add_port(cid, "A");
        network_.add_port(cid, "X");
    }

    // Find top module in token stream
    while (tok.peek().type != TokenType::EOI) {
        if (tok.match(TokenType::Module)) {
            if (tok.peek().type != TokenType::Identifier) {
                error(tok, "Expected module name");
            }
            std::string mod_name = tok.peek().text;
            tok.consume();

            // Skip header
            if (tok.match(TokenType::LParen)) {
                while (tok.peek().type != TokenType::RParen &&
                       tok.peek().type != TokenType::EOI) {
                    tok.consume();
                }
                tok.expect(TokenType::RParen, ")");
            }
            tok.expect(TokenType::Semi, ";");

            if (mod_name == top_name) {
                auto meta_it = modules_.find(mod_name);
                if (meta_it != modules_.end()) {
                    parse_module_body(tok, mod_name, &meta_it->second);
                } else {
                    parse_module_body(tok, mod_name);
                }
                return;
            } else {
                // Skip this module's body
                int depth = 1;
                while (tok.peek().type != TokenType::EOI && depth > 0) {
                    if (tok.peek().type == TokenType::Module) ++depth;
                    else if (tok.peek().type == TokenType::EndModule) --depth;
                    tok.consume();
                }
            }
        } else {
            tok.consume();
        }
    }
}

void GateNetlistParser::parse_module_body(Tokenizer& tok,
                                           const std::string& mod_name,
                                           ModuleMeta* meta) {
    current_module_ = mod_name;
    // Create top-level cell & instance
    CellId top_cell;
    auto existing_top = network_.find_cell("__top__");
    if (existing_top) {
        top_cell = *existing_top;
    } else {
        top_cell = network_.create_cell("__top__");
    }
    current_top_inst_ = network_.create_instance(mod_name, top_cell);

    uint32_t assign_counter = 0;

    while (tok.peek().type != TokenType::EOI) {
        if (tok.match(TokenType::EndModule)) break;

        TokenType t = tok.peek().type;
        if (t == TokenType::Input) {
            tok.consume();
            parse_port_decl(tok, PortDirection::Input);
        }
        else if (t == TokenType::Output) {
            tok.consume();
            parse_port_decl(tok, PortDirection::Output);
        }
        else if (t == TokenType::Inout) {
            tok.consume();
            parse_port_decl(tok, PortDirection::Inout);
        }
        else if (t == TokenType::Wire || t == TokenType::Reg) {
            tok.consume();
            parse_wire_decl(tok);
        }
        else if (t == TokenType::Assign) {
            tok.consume();
            parse_assign_stmt(tok, assign_counter);
        }
        else if (t == TokenType::Always) {
            // Ignore sequential/procedural RTL here; the gate-level timing
            // graph is built from continuous assigns and cell instances.
            tok.consume();
            int begin_depth = 0;
            while (tok.peek().type != TokenType::EOI) {
                if (tok.peek().type == TokenType::Identifier &&
                    tok.peek().text == "begin") {
                    ++begin_depth;
                } else if (tok.peek().type == TokenType::Identifier &&
                           tok.peek().text == "end" && begin_depth > 0) {
                    --begin_depth;
                }
                const bool done = tok.peek().type == TokenType::Semi &&
                                  begin_depth == 0;
                tok.consume();
                if (done) break;
            }
        }
        else if (t == TokenType::Identifier) {
            std::string cell_name = tok.peek().text;
            tok.consume();

            if (tok.peek().type == TokenType::Identifier) {
                std::string inst_name = tok.peek().text;
                tok.consume();
                parse_instance(tok, cell_name, inst_name);
            } else {
                // Unknown construct — skip to semicolon
                while (tok.peek().type != TokenType::Semi &&
                       tok.peek().type != TokenType::EOI) {
                    tok.consume();
                }
                if (tok.peek().type == TokenType::Semi) tok.consume();
            }
        }
        else {
            tok.consume();
        }
    }

    // For ANSI-style port declarations (ports declared in module header),
    // create any top-level pins that were not declared in the body.
    if (meta) {
        for (const auto& [pname, dir] : meta->ports) {
            bool has_pin = false;
            std::string bus_prefix = std::string(pname) + "[";
            for (auto pid : network_.instance(current_top_inst_).pins) {
                std::string pin_name = std::string(network_.pin_name(pid));
                if (pin_name == pname || pin_name.find(bus_prefix) == 0) {
                    has_pin = true;
                    break;
                }
            }
            if (has_pin) continue;
            const auto bits = meta->signal_bits.find(pname);
            const auto names = bits == meta->signal_bits.end()
                ? std::vector<std::string>{pname} : bits->second;
            for (const auto& name : names) {
                NetId net = network_.find_net(name).value_or(NULL_NET);
                if (net == NULL_NET) net = network_.create_net(name);
                PinId pin = network_.create_pin(
                    name, current_top_inst_, top_instance_port_direction(dir));
                network_.add_pin(current_top_inst_, pin);
                network_.connect_pin_to_net(pin, net);
            }
        }
    }

    network_.rebuild_net_connections();
}

// ------------------------------------------------------------------------
// Declarations
// ------------------------------------------------------------------------

void GateNetlistParser::parse_port_decl(Tokenizer& tok, PortDirection dir) {
    tok.match(TokenType::Wire);
    // Optional range [msb:lsb] — must be parsed before identifiers
    int msb = 0, lsb = 0;
    bool have_int_range = false;
    if (tok.peek().type == TokenType::LBracket) {
        tok.consume(); // [
        if (tok.peek().type == TokenType::Number) {
            try {
                msb = std::stoi(tok.peek().text);
                tok.consume();
                if (tok.match(TokenType::Colon)) {
                    if (tok.peek().type == TokenType::Number) {
                        lsb = std::stoi(tok.peek().text);
                        tok.consume();
                        have_int_range = true;
                    }
                }
            } catch (...) {}
        }
        while (tok.peek().type != TokenType::RBracket && tok.peek().type != TokenType::EOI) {
            tok.consume();
        }
        tok.expect(TokenType::RBracket, "]");
    }

    auto ids = parse_identifier_list(tok);
    for (auto& id : ids) {
        std::vector<std::string> names;
        if (have_int_range && simulation_mode_ && (msb < 0 || msb > 1000000 || lsb > 1000000 || lsb < 0))
            error(tok, "unsupported gate simulation packed range");
        if (have_int_range) {
            if (msb >= lsb) {
                for (int i = msb; i >= lsb; --i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            } else {
                for (int i = msb; i <= lsb; ++i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            }
        } else {
            names.push_back(id);
        }
        for (auto& full_name : names) {
            NetId net;
            auto existing = network_.find_net(full_name);
            if (existing) {
                net = *existing;
            } else {
                net = network_.create_net(full_name);
            }
            // Create top-level pin and connect
            // The top instance is always the first one we created in this module
            PinId pin = network_.create_pin(
                full_name, current_top_inst_,
                top_instance_port_direction(dir));
            network_.add_pin(current_top_inst_, pin);
            network_.connect_pin_to_net(pin, net);
        }
    }
    tok.expect(TokenType::Semi, ";");
}

void GateNetlistParser::parse_wire_decl(Tokenizer& tok) {
    // Optional range [msb:lsb] — must be parsed before identifiers
    int msb = 0, lsb = 0;
    bool have_int_range = false;
    if (tok.peek().type == TokenType::LBracket) {
        tok.consume(); // [
        if (tok.peek().type == TokenType::Number) {
            try {
                msb = std::stoi(tok.peek().text);
                tok.consume();
                if (tok.match(TokenType::Colon)) {
                    if (tok.peek().type == TokenType::Number) {
                        lsb = std::stoi(tok.peek().text);
                        tok.consume();
                        have_int_range = true;
                    }
                }
            } catch (...) {}
        }
        while (tok.peek().type != TokenType::RBracket && tok.peek().type != TokenType::EOI) {
            tok.consume();
        }
        tok.expect(TokenType::RBracket, "]");
    }

    auto ids = parse_identifier_list(tok);
    for (auto& id : ids) {
        std::vector<std::string> names;
        if (have_int_range && simulation_mode_ && (msb < 0 || msb > 1000000 || lsb > 1000000 || lsb < 0))
            error(tok, "unsupported gate simulation packed range");
        if (have_int_range) {
            if (msb >= lsb) {
                for (int i = msb; i >= lsb; --i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            } else {
                for (int i = msb; i <= lsb; ++i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            }
        } else {
            names.push_back(id);
        }
        for (auto& full_name : names) {
            if (!network_.find_net(full_name)) {
                network_.create_net(full_name);
            }
        }
    }
    tok.expect(TokenType::Semi, ";");
}

void GateNetlistParser::parse_assign_stmt(Tokenizer& tok,
                                           uint32_t& assign_counter) {
    if (simulation_mode_) { simulation_assign(tok); return; }
    // assign lhs = rhs;
    std::string lhs = parse_net_reference(tok);
    tok.expect(TokenType::Eq, "=");
    std::string rhs = parse_net_reference(tok);
    tok.expect(TokenType::Semi, ";");

    // Model assign as a buffer instance so the timing graph has an arc.
    std::string inst_name = "_assign_" + std::to_string(assign_counter++);

    CellId cell = *network_.find_cell("__assign__");
    InstanceId inst = network_.create_instance(inst_name, cell);

    PinId pin_a = network_.create_pin("A", inst, PortDirection::Input);
    network_.add_pin(inst, pin_a);
    NetId net_rhs = resolve_net(rhs);
    network_.connect_pin_to_net(pin_a, net_rhs);

    PinId pin_x = network_.create_pin("X", inst, PortDirection::Output);
    network_.add_pin(inst, pin_x);
    NetId net_lhs = resolve_net(lhs);
    network_.connect_pin_to_net(pin_x, net_lhs);
}

// ------------------------------------------------------------------------
// Instances
// ------------------------------------------------------------------------

void GateNetlistParser::parse_instance(Tokenizer& tok,
                                        std::string_view cell_name,
                                        std::string_view inst_name) {
    if (simulation_mode_) { simulation_instance(tok, std::string(cell_name), std::string(inst_name)); return; }
    std::string cell_str{cell_name};
    std::string inst_str{inst_name};
    std::string prefixed_inst = flatten_inst_prefix_.empty()
        ? inst_str
        : flatten_inst_prefix_ + "/" + inst_str;

    if (!tok.match(TokenType::LParen)) {
        error(tok, "Expected '(' after instance name");
    }

    // Collect all port connections first
    struct Conn { std::string port; std::string net; };
    std::vector<Conn> conns;
    bool named = (tok.peek().type == TokenType::Dot);

    if (named) {
        while (tok.peek().type != TokenType::RParen &&
               tok.peek().type != TokenType::EOI) {
            if (!tok.match(TokenType::Dot)) {
                error(tok, "Expected '.' for named port connection");
            }
            if (tok.peek().type != TokenType::Identifier &&
                tok.peek().type != TokenType::Number) {
                error(tok, "Expected port name after '.'");
            }
            std::string port_name = tok.peek().text;
            tok.consume();

            if (!tok.match(TokenType::LParen)) {
                error(tok, "Expected '(' after port name");
            }
            std::string net_name = parse_net_reference(tok);
            if (!tok.match(TokenType::RParen)) {
                error(tok, "Expected ')' after net reference");
            }
            conns.push_back({port_name, net_name});
            if (tok.peek().type == TokenType::Comma) {
                tok.consume();
            }
        }
    } else {
        // Positional: match by order with cell's port list
        size_t port_idx = 0;
        auto mod_it = modules_.find(cell_str);
        std::vector<std::string> ordered_ports;
        if (mod_it != modules_.end()) {
            for (auto& [pname, pdir] : mod_it->second.ports) {
                ordered_ports.push_back(pname);
            }
        } else {
            auto cell_opt = network_.find_cell(cell_str);
            if (cell_opt) {
                auto& cdata = network_.cell(*cell_opt);
                for (auto psid : cdata.port_names) {
                    ordered_ports.push_back(std::string(network_.str(psid)));
                }
            }
        }
        while (tok.peek().type != TokenType::RParen &&
               tok.peek().type != TokenType::EOI) {
            std::string net_name = parse_net_reference(tok);
            std::string port_name = (port_idx < ordered_ports.size())
                ? ordered_ports[port_idx]
                : ("p" + std::to_string(port_idx));
            conns.push_back({port_name, net_name});
            ++port_idx;
            if (tok.peek().type == TokenType::Comma) {
                tok.consume();
            }
        }
    }

    tok.expect(TokenType::RParen, ")");
    if (!tok.match(TokenType::Semi)) {
        if (strict_mode_) {
            error(tok, "Expected ';' after instantiation");
        }
    }

    // Check if this is a submodule with internal logic that should be flattened
    auto mod_it = modules_.find(cell_str);
    if (mod_it != modules_.end() && mod_it->second.defined &&
        mod_it->second.has_logic && !mod_it->second.body.empty()) {
        std::unordered_map<std::string, std::string> port_map;
        for (auto& c : conns) {
            // When already flattening, resolve parent-local net names to
            // their globally-scoped names so nested flatten_module() does
            // not double-prefix them.
            if (!simulation_mode_ || !c.net.empty()) port_map[c.port] = resolve_net_reference(c.net);
        }
        flatten_module(cell_str, inst_str, port_map);
        return;
    }

    // Create black-box leaf instance
    CellId cell;
    auto cell_opt = network_.find_cell(cell_str);
    if (cell_opt) {
        cell = *cell_opt;
    } else {
        cell = network_.create_cell(cell_str);
    }

    InstanceId inst = network_.create_instance(prefixed_inst, cell);

    for (auto& c : conns) {
        const auto concat_parts = parse_concatenation(c.net);
        // A named Liberty bus port is written in gate netlists as one
        // concatenation, for example .QA({q[7],q[6],...,q[0]}).  Materialize
        // one network pin per bit so SPEF names such as instance:QA[7] bind
        // to the same pins that timing linking sees in the Liberty bus.
        if (concat_parts.size() > 1) {
            const PortDirection dir = lookup_port_direction(cell_str, c.port);
            for (size_t i = 0; i < concat_parts.size(); ++i) {
                const std::string bit_name = c.port + "[" +
                    std::to_string(concat_parts.size() - 1 - i) + "]";
                const uint32_t bit_sid = network_.intern_string(bit_name);
                bool has_bit_port = false;
                for (auto psid : network_.cell(cell).port_names) {
                    if (psid == bit_sid) { has_bit_port = true; break; }
                }
                if (!has_bit_port) network_.add_port(cell, bit_name);
                PinId pin = network_.create_pin(bit_name, inst, dir);
                network_.add_pin(inst, pin);
                if (!concat_parts[i].empty()) {
                    network_.connect_pin_to_net(pin, resolve_net(concat_parts[i]));
                }
            }
            continue;
        }
        auto& cdata = network_.cell(cell);
        bool has_port = false;
        uint32_t port_sid = network_.intern_string(c.port);
        for (auto psid : cdata.port_names) {
            if (psid == port_sid) { has_port = true; break; }
        }
        if (!has_port) {
            network_.add_port(cell, c.port);
        }

        PortDirection dir = lookup_port_direction(cell_str, c.port);
        PinId pin = network_.create_pin(c.port, inst, dir);
        network_.add_pin(inst, pin);
        if (!c.net.empty()) {
            NetId net = resolve_net(c.net);
            network_.connect_pin_to_net(pin, net);
        }
    }
}

// ------------------------------------------------------------------------
// Hierarchical flattening
// ------------------------------------------------------------------------

std::string GateNetlistParser::remap_net_name(std::string_view local_name) {
    std::string local_str(local_name);

    // Exact match
    auto it = flatten_net_map_.find(local_str);
    if (it != flatten_net_map_.end()) return it->second;

    // Check for bit-select or part-select on a mapped name:
    // "op_in[0]" where "op_in" is mapped to "parent_net"
    for (auto& [key, val] : flatten_net_map_) {
        if (local_str.size() > key.size() &&
            local_str[key.size()] == '[' &&
            local_str.compare(0, key.size(), key) == 0) {
            return val + local_str.substr(key.size());
        }
    }

    // Not mapped — prefix with instance path
    if (flatten_inst_prefix_.empty()) return local_str;
    return flatten_inst_prefix_ + "/" + local_str;
}

void GateNetlistParser::flatten_module(
    const std::string& mod_name,
    const std::string& inst_name,
    const std::unordered_map<std::string, std::string>& port_map) {

    auto mod_it = modules_.find(mod_name);
    if (mod_it == modules_.end() || (!simulation_mode_ && mod_it->second.body.empty())) {
        throw std::runtime_error("Cannot flatten undefined module: " + mod_name);
    }

    if (++flatten_depth_ > kMaxFlattenDepth) {
        throw std::runtime_error("Exceeded maximum hierarchy flatten depth for module: " + mod_name);
    }

    // Save current state
    std::string old_prefix = flatten_inst_prefix_;
    std::string old_module = current_module_;
    std::unordered_map<std::string, std::string> old_net_map = flatten_net_map_;
    bool old_flattening = flattening_;

    // Set new state
    flattening_ = true;
    current_module_ = mod_name;
    flatten_inst_prefix_ = old_prefix.empty() ? inst_name : old_prefix + "/" + inst_name;
    flatten_net_map_ = port_map;
    if (timing_leaf_ || timing_scope_) timing_path_.push_back(inst_name);
    if (timing_scope_) {
        std::vector<TimingPort> ports;
        for (const auto& port : mod_it->second.ports) {
            const auto bits = mod_it->second.signal_bits.find(port.first);
            const auto local = bits == mod_it->second.signal_bits.end() ? std::vector<std::string>{port.first} : bits->second;
            for (const auto& bit : local) ports.push_back({bit, port.second, simulation_net(remap_net_name(bit))});
        }
        timing_scope_(timing_path_, mod_name, ports);
    }
    // ANSI declarations live outside body. Establish bit mappings here too,
    // so both ANSI and body declarations use the same vector connection.
    if (!simulation_mode_) for (const auto& port : mod_it->second.ports) {
        const auto declared = mod_it->second.signal_bits.find(port.first);
        const auto mapped = port_map.find(port.first);
        if (declared == mod_it->second.signal_bits.end() || mapped == port_map.end() ||
            declared->second.size() <= 1 || mapped->second.empty() || mapped->second.front() != '{') continue;
        const auto bits = parse_concatenation(mapped->second);
        if (bits.size() != declared->second.size()) {
            throw std::runtime_error("Port width mismatch while flattening " + mod_name + "." + port.first);
        }
        for (size_t i = 0; i < bits.size(); ++i) flatten_net_map_[declared->second[i]] = bits[i];
    }

    // Create tokenizer for module body
    Tokenizer tok(mod_it->second.body);
    uint32_t assign_counter = 0;

    while (tok.peek().type != TokenType::EOI) {
        if (tok.match(TokenType::EndModule)) break;

        TokenType t = tok.peek().type;
        if (t == TokenType::Input) {
            tok.consume();
            flatten_port_decl(tok, PortDirection::Input);
        }
        else if (t == TokenType::Output) {
            tok.consume();
            flatten_port_decl(tok, PortDirection::Output);
        }
        else if (t == TokenType::Inout) {
            tok.consume();
            flatten_port_decl(tok, PortDirection::Inout);
        }
        else if (t == TokenType::Wire || t == TokenType::Reg) {
            tok.consume();
            flatten_wire_decl(tok);
        }
        else if (t == TokenType::Assign) {
            tok.consume();
            flatten_assign_stmt(tok, assign_counter);
        }
        else if (t == TokenType::Identifier) {
            std::string cell_name = tok.peek().text;
            tok.consume();
            if (tok.peek().type == TokenType::Identifier) {
                std::string inst_name_local = tok.peek().text;
                tok.consume();
                flatten_instance(tok, cell_name, inst_name_local);
            } else {
                while (tok.peek().type != TokenType::Semi &&
                       tok.peek().type != TokenType::EOI) {
                    tok.consume();
                }
                if (tok.peek().type == TokenType::Semi) tok.consume();
            }
        }
        else {
            tok.consume();
        }
    }

    // Restore state
    if (timing_leaf_ || timing_scope_) timing_path_.pop_back();
    flatten_inst_prefix_ = std::move(old_prefix);
    current_module_ = std::move(old_module);
    flatten_net_map_ = std::move(old_net_map);
    flattening_ = old_flattening;
    --flatten_depth_;
}

// Parse a concatenation string "{a,b[0],c}" into individual net names.
static std::vector<std::string> parse_concatenation(const std::string& concat) {
    std::vector<std::string> result;
    if (concat.size() < 2 || concat.front() != '{' || concat.back() != '}') {
        return result;
    }
    size_t i = 1;
    size_t end = concat.size() - 1;
    while (i < end) {
        size_t start = i;
        int depth = 0;
        while (i < end && (depth > 0 || concat[i] != ',')) {
            if (concat[i] == '{') ++depth;
            else if (concat[i] == '}') --depth;
            ++i;
        }
        std::string net = concat.substr(start, i - start);
        size_t first = net.find_first_not_of(" \t");
        if (first != std::string::npos) {
            size_t last = net.find_last_not_of(" \t");
            result.push_back(net.substr(first, last - first + 1));
        }
        if (i < end && concat[i] == ',') ++i;
    }
    return result;
}

void GateNetlistParser::flatten_port_decl(Tokenizer& tok, PortDirection /*dir*/) {
    tok.match(TokenType::Wire);
    // Optional range [msb:lsb] — must be parsed before identifiers
    int msb = 0, lsb = 0;
    bool have_int_range = false;
    if (tok.peek().type == TokenType::LBracket) {
        tok.consume(); // [
        if (tok.peek().type == TokenType::Number) {
            try {
                msb = std::stoi(tok.peek().text);
                tok.consume();
                if (tok.match(TokenType::Colon)) {
                    if (tok.peek().type == TokenType::Number) {
                        lsb = std::stoi(tok.peek().text);
                        tok.consume();
                        have_int_range = true;
                    }
                }
            } catch (...) {}
        }
        while (tok.peek().type != TokenType::RBracket && tok.peek().type != TokenType::EOI) {
            tok.consume();
        }
        tok.expect(TokenType::RBracket, "]");
    }

    auto ids = parse_identifier_list(tok);
    for (auto& id : ids) {
        std::vector<std::string> names;
        if (have_int_range && simulation_mode_ && (msb < 0 || msb > 1000000 || lsb > 1000000 || lsb < 0))
            error(tok, "unsupported gate simulation packed range");
        if (have_int_range) {
            if (msb >= lsb) {
                for (int i = msb; i >= lsb; --i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            } else {
                for (int i = msb; i <= lsb; ++i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            }
        } else {
            names.push_back(id);
        }
        for (size_t name_idx = 0; name_idx < names.size(); ++name_idx) {
            auto& full_name = names[name_idx];
            // If this port isn't already mapped (e.g. unconnected), create a
            // prefixed local net so that internal references still resolve.
            if (flatten_net_map_.find(full_name) == flatten_net_map_.end()) {
                // Check if the base bus name is mapped (e.g. port "a" mapped to
                // "al_s1", so bit "a[15]" should map to "al_s1[15]").
                size_t bracket_pos = full_name.find('[');
                if (bracket_pos != std::string::npos) {
                    std::string base_name = full_name.substr(0, bracket_pos);
                    auto base_it = flatten_net_map_.find(base_name);
                    if (base_it != flatten_net_map_.end()) {
                        const std::string& mapped = base_it->second;
                        // If the port is connected to a concatenation, map each
                        // bit to the corresponding element (MSB-first).
                        if (!mapped.empty() && mapped.front() == '{') {
                            auto concat_nets = parse_concatenation(mapped);
                            if (name_idx < concat_nets.size()) {
                                flatten_net_map_[full_name] = concat_nets[name_idx];
                                continue;
                            }
                        }
                        flatten_net_map_[full_name] = mapped + full_name.substr(bracket_pos);
                        continue;
                    }
                }
                flatten_net_map_[full_name] = flatten_inst_prefix_.empty()
                    ? full_name
                    : flatten_inst_prefix_ + "/" + full_name;
            }
        }
    }
    tok.expect(TokenType::Semi, ";");
}

void GateNetlistParser::flatten_wire_decl(Tokenizer& tok) {
    // Optional range [msb:lsb] — must be parsed before identifiers
    int msb = 0, lsb = 0;
    bool have_int_range = false;
    if (tok.peek().type == TokenType::LBracket) {
        tok.consume(); // [
        if (tok.peek().type == TokenType::Number) {
            try {
                msb = std::stoi(tok.peek().text);
                tok.consume();
                if (tok.match(TokenType::Colon)) {
                    if (tok.peek().type == TokenType::Number) {
                        lsb = std::stoi(tok.peek().text);
                        tok.consume();
                        have_int_range = true;
                    }
                }
            } catch (...) {}
        }
        while (tok.peek().type != TokenType::RBracket && tok.peek().type != TokenType::EOI) {
            tok.consume();
        }
        tok.expect(TokenType::RBracket, "]");
    }

    auto ids = parse_identifier_list(tok);
    for (auto& id : ids) {
        std::vector<std::string> names;
        if (have_int_range && simulation_mode_ && (msb < 0 || msb > 1000000 || lsb > 1000000 || lsb < 0))
            error(tok, "unsupported gate simulation packed range");
        if (have_int_range) {
            if (msb >= lsb) {
                for (int i = msb; i >= lsb; --i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            } else {
                for (int i = msb; i <= lsb; ++i)
                    names.push_back(id + "[" + std::to_string(i) + "]");
            }
        } else {
            names.push_back(id);
        }
        for (auto& local_name : names) {
            // Don't overwrite a port mapping
            if (flatten_net_map_.find(local_name) != flatten_net_map_.end())
                continue;

            std::string global_name = flatten_inst_prefix_.empty()
                ? local_name
                : flatten_inst_prefix_ + "/" + local_name;
            flatten_net_map_[local_name] = global_name;
            if (!network_.find_net(global_name)) {
                network_.create_net(global_name);
            }
        }
    }
    tok.expect(TokenType::Semi, ";");
}

void GateNetlistParser::flatten_assign_stmt(Tokenizer& tok,
                                             uint32_t& assign_counter) {
    if (simulation_mode_) { simulation_assign(tok); return; }
    std::string lhs = parse_net_reference(tok);
    tok.expect(TokenType::Eq, "=");
    std::string rhs = parse_net_reference(tok);
    tok.expect(TokenType::Semi, ";");

    std::string inst_name = "_assign_" + std::to_string(assign_counter++);
    if (!flatten_inst_prefix_.empty()) {
        inst_name = flatten_inst_prefix_ + "/" + inst_name;
    }

    CellId cell = *network_.find_cell("__assign__");
    InstanceId inst = network_.create_instance(inst_name, cell);

    PinId pin_a = network_.create_pin("A", inst, PortDirection::Input);
    network_.add_pin(inst, pin_a);
    NetId net_rhs = resolve_net(rhs);
    network_.connect_pin_to_net(pin_a, net_rhs);

    PinId pin_x = network_.create_pin("X", inst, PortDirection::Output);
    network_.add_pin(inst, pin_x);
    NetId net_lhs = resolve_net(lhs);
    network_.connect_pin_to_net(pin_x, net_lhs);
}

void GateNetlistParser::flatten_instance(Tokenizer& tok,
                                          std::string_view cell_name,
                                          std::string_view inst_name) {
    if (simulation_mode_) { simulation_instance(tok, std::string(cell_name), std::string(inst_name)); return; }
    std::string cell_str{cell_name};
    std::string inst_str{inst_name};
    std::string prefixed_inst = flatten_inst_prefix_.empty()
        ? inst_str
        : flatten_inst_prefix_ + "/" + inst_str;

    if (!tok.match(TokenType::LParen)) {
        error(tok, "Expected '(' after instance name");
    }

    // Collect all port connections first
    struct Conn { std::string port; std::string net; };
    std::vector<Conn> conns;
    bool named = (tok.peek().type == TokenType::Dot);

    if (named) {
        while (tok.peek().type != TokenType::RParen &&
               tok.peek().type != TokenType::EOI) {
            if (!tok.match(TokenType::Dot)) {
                error(tok, "Expected '.' for named port connection");
            }
            if (tok.peek().type != TokenType::Identifier &&
                tok.peek().type != TokenType::Number) {
                error(tok, "Expected port name after '.'");
            }
            std::string port_name = tok.peek().text;
            tok.consume();

            if (!tok.match(TokenType::LParen)) {
                error(tok, "Expected '(' after port name");
            }
            std::string net_name = parse_net_reference(tok);
            if (!tok.match(TokenType::RParen)) {
                error(tok, "Expected ')' after net reference");
            }
            conns.push_back({port_name, net_name});
            if (tok.peek().type == TokenType::Comma) {
                tok.consume();
            }
        }
    } else {
        size_t port_idx = 0;
        auto mod_it = modules_.find(cell_str);
        std::vector<std::string> ordered_ports;
        if (mod_it != modules_.end()) {
            for (auto& [pname, pdir] : mod_it->second.ports) {
                ordered_ports.push_back(pname);
            }
        } else {
            auto cell_opt = network_.find_cell(cell_str);
            if (cell_opt) {
                auto& cdata = network_.cell(*cell_opt);
                for (auto psid : cdata.port_names) {
                    ordered_ports.push_back(std::string(network_.str(psid)));
                }
            }
        }
        while (tok.peek().type != TokenType::RParen &&
               tok.peek().type != TokenType::EOI) {
            std::string net_name = parse_net_reference(tok);
            std::string port_name = (port_idx < ordered_ports.size())
                ? ordered_ports[port_idx]
                : ("p" + std::to_string(port_idx));
            conns.push_back({port_name, net_name});
            ++port_idx;
            if (tok.peek().type == TokenType::Comma) {
                tok.consume();
            }
        }
    }

    tok.expect(TokenType::RParen, ")");
    if (!tok.match(TokenType::Semi)) {
        if (strict_mode_) {
            error(tok, "Expected ';' after instantiation");
        }
    }

    // Check if this is a submodule with internal logic that should be flattened
    auto mod_it = modules_.find(cell_str);
    if (mod_it != modules_.end() && mod_it->second.defined &&
        mod_it->second.has_logic && !mod_it->second.body.empty()) {
        std::unordered_map<std::string, std::string> port_map;
        for (auto& c : conns) {
            // When already flattening, resolve parent-local net names to
            // their globally-scoped names so nested flatten_module() does
            // not double-prefix them.
            if (!simulation_mode_ || !c.net.empty()) port_map[c.port] = resolve_net_reference(c.net);
        }
        flatten_module(cell_str, inst_str, port_map);
        return;
    }

    // Create black-box leaf instance
    CellId cell;
    auto cell_opt = network_.find_cell(cell_str);
    if (cell_opt) {
        cell = *cell_opt;
    } else {
        cell = network_.create_cell(cell_str);
    }

    InstanceId inst = network_.create_instance(prefixed_inst, cell);

    for (auto& c : conns) {
        auto& cdata = network_.cell(cell);
        bool has_port = false;
        uint32_t port_sid = network_.intern_string(c.port);
        for (auto psid : cdata.port_names) {
            if (psid == port_sid) { has_port = true; break; }
        }
        if (!has_port) {
            network_.add_port(cell, c.port);
        }

        PortDirection dir = lookup_port_direction(cell_str, c.port);
        PinId pin = network_.create_pin(c.port, inst, dir);
        network_.add_pin(inst, pin);
        if (!c.net.empty()) {
            NetId net = resolve_net(c.net);
            network_.connect_pin_to_net(pin, net);
        }
    }
}

// ------------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------------

std::vector<std::string> GateNetlistParser::parse_identifier_list(
    Tokenizer& tok) {
    std::vector<std::string> ids;
    while (true) {
        if (tok.peek().type == TokenType::Identifier ||
            tok.peek().type == TokenType::Number) {
            ids.push_back(tok.peek().text);
            tok.consume();
        } else {
            break;
        }
        if (tok.peek().type == TokenType::Comma) {
            tok.consume();
        } else {
            break;
        }
    }
    return ids;
}

std::string GateNetlistParser::parse_net_reference(Tokenizer& tok) {
    // net_reference := identifier [ [expr] ] [ [expr:expr] ]
    //                 | number
    //                 | concatenation { expr, expr, ... }
    // For simplicity in gate-level netlists, we support:
    //   identifier [ bit_select ]
    //   identifier [ part_select ]
    //   number
    //   { ... }  (concatenation — return as string)

    if (tok.peek().type == TokenType::Number) {
        std::string text = tok.peek().text;
        if (is_sized_cast_width(text)) {
            // SystemVerilog sized cast, e.g. 32'(a), 71'(a * 7'b1000000).
            // Width conversion does not create a separate timing source, so
            // retain the first referenced net while consuming the complete
            // expression.  This also prevents the cast's closing ')' from
            // being mistaken for the enclosing port/statement delimiter.
            tok.consume();
            if (tok.match(TokenType::LParen)) {
                std::string inner = parse_net_reference(tok);
                tok.expect(TokenType::RParen, ")");
                return inner;
            }
            return text;
        }
        tok.consume();
        consume_net_expression_tail(tok);
        return text;
    }

    if (tok.peek().type == TokenType::LBrace) {
        // Parse a concatenation component by component.  Parsing each part is
        // important for casts inside concatenations: `{32'(a), b}` must map
        // to `{a,b}`, rather than creating a literal net named `32'(a)`.
        std::string concat = "{";
        tok.consume();
        while (tok.peek().type != TokenType::RBrace &&
               tok.peek().type != TokenType::EOI) {
            if (tok.peek().type == TokenType::Comma) {
                concat += ',';
                tok.consume();
                continue;
            }
            std::string part = parse_net_reference(tok);
            if (part.empty()) {
                // Keep the parser forward-progressing on an unsupported
                // expression component while retaining its original token.
                concat += tok.peek().text;
                tok.consume();
            } else {
                concat += part;
            }
        }
        tok.expect(TokenType::RBrace, "}");
        concat += "}";
        // A concatenation may itself be an operand of an expression, for
        // example `{a,b} >> 5'b1`; consume that tail just like an identifier
        // reference so the enclosing assign/connection sees its delimiter.
        consume_net_expression_tail(tok);
        return concat;
    }

    if (tok.peek().type != TokenType::Identifier) {
        // Return empty for robustness (e.g., unconnected port)
        return "";
    }

    std::string name = tok.peek().text;
    tok.consume();

    // Parameterized and typed casts use an identifier before the apostrophe,
    // for example WIDTH'(a), logic'(a), or signed'(a).  The tokenizer emits
    // the apostrophe as a one-character robustness token, so recognize that
    // pair here before treating the identifier as an ordinary net.
    if (tok.peek().type == TokenType::Identifier && tok.peek().text == "'") {
        tok.consume();
        if (tok.match(TokenType::LParen)) {
            std::string inner = parse_net_reference(tok);
            tok.expect(TokenType::RParen, ")");
            return inner;
        }
    }

    // Optional bit-select or part-select
    while (tok.peek().type == TokenType::LBracket) {
        name += "[";
        tok.consume();
        while (tok.peek().type != TokenType::RBracket &&
               tok.peek().type != TokenType::EOI) {
            name += tok.peek().text;
            tok.consume();
        }
        if (tok.peek().type == TokenType::RBracket) {
            tok.consume();
            name += "]";
        }
    }

    // A reference can be followed by an arithmetic/logical expression.  The
    // network model represents assigns and pin connections as net references,
    // so consume the expression tail while retaining the first dynamic
    // operand.  This is what allows casts such as
    // `71'(state_in[63:0] * 7'b1000000)` to bind state_in correctly.
    consume_net_expression_tail(tok);
    return name;
}

void GateNetlistParser::consume_net_expression_tail(Tokenizer& tok) {
    int paren_depth = 0;
    int bracket_depth = 0;
    int brace_depth = 0;
    while (tok.peek().type != TokenType::EOI) {
        switch (tok.peek().type) {
        case TokenType::LParen:
            ++paren_depth;
            tok.consume();
            break;
        case TokenType::RParen:
            if (paren_depth == 0) return;
            --paren_depth;
            tok.consume();
            break;
        case TokenType::LBracket:
            ++bracket_depth;
            tok.consume();
            break;
        case TokenType::RBracket:
            if (bracket_depth == 0) return;
            --bracket_depth;
            tok.consume();
            break;
        case TokenType::LBrace:
            ++brace_depth;
            tok.consume();
            break;
        case TokenType::RBrace:
            if (brace_depth == 0) return;
            --brace_depth;
            tok.consume();
            break;
        case TokenType::Comma:
        case TokenType::Semi:
            if (paren_depth == 0 && bracket_depth == 0 && brace_depth == 0)
                return;
            tok.consume();
            break;
        case TokenType::Eq:
            if (paren_depth == 0 && bracket_depth == 0 && brace_depth == 0)
                return;
            tok.consume();
            break;
        default:
            tok.consume();
            break;
        }
    }
}

// Resolve a net reference (single net or concatenation) through the current
// flatten_net_map_ when flattening is active.
std::string GateNetlistParser::resolve_net_reference(const std::string& net) {
    std::vector<std::string> bits;
    auto append = [&](const std::string& ref, auto&& self) -> void {
        if (!ref.empty() && ref.front() == '{') {
            for (const auto& part : parse_concatenation(ref)) self(part, self);
            return;
        }
        // A whole bus inside a concatenation contributes every declared bit,
        // in Verilog's MSB-to-LSB order, rather than one opaque net name.
        auto mod = modules_.find(current_module_);
        if (mod != modules_.end()) {
            auto bus = mod->second.signal_bits.find(ref);
            if (bus != mod->second.signal_bits.end() && bus->second.size() > 1) {
                for (const auto& bit : bus->second) self(bit, self);
                return;
            }
        }
        const auto bracket = ref.find('[');
        const auto colon = ref.find(':', bracket);
        if (bracket != std::string::npos && colon != std::string::npos && ref.back() == ']') {
            const int msb = std::stoi(ref.substr(bracket + 1, colon - bracket - 1));
            const int lsb = std::stoi(ref.substr(colon + 1, ref.size() - colon - 2));
            const int step = msb <= lsb ? 1 : -1;
            for (int i = msb;; i += step) {
                self(ref.substr(0, bracket) + "[" + std::to_string(i) + "]", self);
                if (i == lsb) break;
            }
            return;
        }
        const bool four_state_constant = ref == "1'bx" || ref == "1'bX" || ref == "1'bz" || ref == "1'bZ";
        bits.push_back(flattening_ && !scalar_constant_literal_value(ref).has_value() && !(simulation_mode_ && four_state_constant)
                           ? remap_net_name(ref) : ref);
    };
    append(net, append);
    if (bits.size() == 1) return bits.front();
    if (bits.empty()) return net;
    std::string resolved = "{";
    for (const auto& bit : bits) {
        if (resolved.size() > 1) resolved += ",";
        resolved += bit;
    }
    return resolved + "}";
}

PortDirection GateNetlistParser::lookup_port_direction(
    std::string_view cell_name, std::string_view port_name) const {
    auto it = modules_.find(std::string(cell_name));
    if (it != modules_.end()) {
        for (auto& [pname, pdir] : it->second.ports) {
            if (pname == port_name) return pdir;
        }
    }
    // Black-box cell: default to Input (conservative for timing graph)
    return PortDirection::Input;
}

NetId GateNetlistParser::resolve_net(std::string_view name) {
    if (name.empty()) {
        // Unconnected port — create a dummy net to keep graph valid.
        std::string dummy = "_unconnected_" + std::to_string(dummy_net_counter_++);
        return network_.create_net(dummy);
    }

    std::string resolved(name);
    std::optional<int> literal_value = scalar_constant_literal_value(resolved);
    const bool four_state_constant = name == "1'bx" || name == "1'bX" || name == "1'bz" || name == "1'bZ";
    if (flattening_ && !literal_value.has_value() && !(simulation_mode_ && four_state_constant)) {
        resolved = remap_net_name(name);
    }

    auto opt = network_.find_net(resolved);
    if (opt) {
        if (literal_value) {
            network_.set_net_constant(*opt, *literal_value);
        }
        return *opt;
    }

    // Constant literal — create a net named after the constant
    NetId net = network_.create_net(resolved);
    if (literal_value) {
        network_.set_net_constant(net, *literal_value);
    }
    return net;
}

// ------------------------------------------------------------------------
// Error / warning
// ------------------------------------------------------------------------

void GateNetlistParser::error(Tokenizer& tok, const std::string& msg) {
    std::string full = "[GateNetlistParser] Error at line " +
                       std::to_string(tok.line()) + ": " + msg;
    throw std::runtime_error(full);
}

void GateNetlistParser::warn(Tokenizer& tok, const std::string& msg) {
    std::cerr << "[GateNetlistParser] Warning at line " << tok.line()
              << ": " << msg << std::endl;
}

// ------------------------------------------------------------------------
// Bus range expansion
// ------------------------------------------------------------------------
// Parse [msb:lsb] from the tokenizer (assumes '[' has NOT been consumed)
// and return individual bit names: base[msb], base[msb-1], ..., base[lsb].
// If the range cannot be parsed as simple integers, returns {base}.
// ------------------------------------------------------------------------
std::vector<std::string> GateNetlistParser::expand_range(Tokenizer& tok,
                                                          const std::string& base_name) {
    std::vector<std::string> result;
    if (!tok.match(TokenType::LBracket)) {
        result.push_back(base_name);
        return result;
    }

    // Try to parse msb as integer
    int msb = 0, lsb = 0;
    bool have_range = false;
    if (tok.peek().type == TokenType::Number) {
        try {
            msb = std::stoi(tok.peek().text);
            tok.consume();
            if (tok.match(TokenType::Colon)) {
                if (tok.peek().type == TokenType::Number) {
                    lsb = std::stoi(tok.peek().text);
                    tok.consume();
                    have_range = true;
                }
            }
        } catch (...) {
            // Not a simple integer range
        }
    }

    // Skip everything until ]
    while (tok.peek().type != TokenType::RBracket && tok.peek().type != TokenType::EOI) {
        tok.consume();
    }
    tok.expect(TokenType::RBracket, "]");

    if (have_range && simulation_mode_ && (msb < 0 || msb > 1000000 || lsb > 1000000 || lsb < 0))
        error(tok, "unsupported gate simulation packed range");
    if (have_range) {
        if (msb >= lsb) {
            for (int i = msb; i >= lsb; --i) {
                result.push_back(base_name + "[" + std::to_string(i) + "]");
            }
        } else {
            for (int i = msb; i <= lsb; ++i) {
                result.push_back(base_name + "[" + std::to_string(i) + "]");
            }
        }
    } else {
        result.push_back(base_name);
    }
    return result;
}

} // namespace te
