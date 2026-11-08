#include "gate_netlist_parser.hh"

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
    if (std::isdigit(static_cast<unsigned char>(c))) {
        const char* num_start = pos_;
        while (pos_ < end_ && std::isdigit(static_cast<unsigned char>(*pos_))) {
            advance_char();
        }
        // Based number: digits ' base hex_digits
        if (pos_ < end_ && *pos_ == '\'') {
            advance_char(); // '
            if (pos_ < end_ && (std::isalpha(static_cast<unsigned char>(*pos_)) ||
                                *pos_ == 'b' || *pos_ == 'B' || *pos_ == 'o' ||
                                *pos_ == 'O' || *pos_ == 'd' || *pos_ == 'D' ||
                                *pos_ == 'h' || *pos_ == 'H')) {
                advance_char(); // base specifier
            }
            while (pos_ < end_ && (std::isxdigit(static_cast<unsigned char>(*pos_)) ||
                                   *pos_ == '_' || *pos_ == 'x' || *pos_ == 'X' ||
                                   *pos_ == 'z' || *pos_ == 'Z')) {
                advance_char();
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
        if (text == "wire")        return Token{TokenType::Wire, text, tk_line, tk_col};
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

std::string GateNetlistParser::parse(std::string_view filepath,
                                     std::string_view preferred_top_name) {
    // Clear state from any previous parse
    source_.clear();
    modules_.clear();
    inferred_cells_.clear();
    instantiated_modules_.clear();
    dummy_net_counter_ = 0;
    wire_aliases_.clear();
    flatten_inst_prefix_.clear();
    flatten_net_map_.clear();
    flattening_ = false;
    flatten_depth_ = 0;

    // Pass 1: collect metadata (module definitions & cell types)
    collect_metadata(filepath);

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
    build_network(filepath, top_name);
    network_.merge_wire_aliases(wire_aliases_);
    return top_name;
}

// ============================================================================
// Pass 1: metadata collection
// ============================================================================

void GateNetlistParser::collect_metadata(std::string_view filepath) {
    source_ = read_file(filepath);
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
    std::string source = read_file(filepath);
    Tokenizer tok(source);

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
    // assign lhs = rhs;
    const char* lhs_begin=tok.token_start();
    std::string lhs = parse_net_reference(tok);
    const auto lhs_text=std::string_view(lhs_begin,tok.token_start()-lhs_begin);
    tok.expect(TokenType::Eq, "=");
    const char* rhs_begin=tok.token_start();
    std::string rhs = parse_net_reference(tok);
    const auto rhs_text=std::string_view(rhs_begin,tok.token_start()-rhs_begin);
    tok.expect(TokenType::Semi, ";");

    std::string inst_name = "_assign_" + std::to_string(assign_counter++);
    const NetId net_rhs=resolve_net(rhs),net_lhs=resolve_net(lhs);
    if(is_scalar_wire_reference(lhs_text) && is_scalar_wire_reference(rhs_text)) {
        wire_aliases_.emplace_back(net_lhs,net_rhs);
        return;
    }
    // Constants, whole buses and expressions retain the existing synthetic
    // assign representation. They are not scalar electrical wire aliases.

    CellId cell = *network_.find_cell("__assign__");
    InstanceId inst = network_.create_instance(inst_name, cell);

    PinId pin_a = network_.create_pin("A", inst, PortDirection::Input);
    network_.add_pin(inst, pin_a);
    network_.connect_pin_to_net(pin_a, net_rhs);

    PinId pin_x = network_.create_pin("X", inst, PortDirection::Output);
    network_.add_pin(inst, pin_x);
    network_.connect_pin_to_net(pin_x, net_lhs);
}

bool GateNetlistParser::is_scalar_wire_reference(std::string_view text) const {
    Tokenizer tok(text);
    if(tok.peek().type!=TokenType::Identifier)return false;
    const auto name=tok.peek().text;tok.consume();
    if(tok.match(TokenType::LBracket)) {
        if(tok.peek().type!=TokenType::Number)return false;
        const auto index=tok.peek().text;
        if(index.empty() || !std::all_of(index.begin(),index.end(),
            [](unsigned char c){return std::isdigit(c);}))return false;
        tok.consume();if(!tok.match(TokenType::RBracket))return false;
    } else {
        const auto module=modules_.find(current_module_);
        if(module!=modules_.end()) {
            const auto bits=module->second.signal_bits.find(name);
            if(bits!=module->second.signal_bits.end() && bits->second.size()!=1)return false;
        }
    }
    return tok.peek().type==TokenType::EOI;
}

// ------------------------------------------------------------------------
// Instances
// ------------------------------------------------------------------------

void GateNetlistParser::parse_instance(Tokenizer& tok,
                                        std::string_view cell_name,
                                        std::string_view inst_name) {
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
            port_map[c.port] = resolve_net_reference(c.net);
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
    if (mod_it == modules_.end() || mod_it->second.body.empty()) {
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
    // ANSI declarations live outside body. Establish bit mappings here too,
    // so both ANSI and body declarations use the same vector connection.
    for (const auto& port : mod_it->second.ports) {
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
    const char* lhs_begin=tok.token_start();
    std::string lhs = parse_net_reference(tok);
    const auto lhs_text=std::string_view(lhs_begin,tok.token_start()-lhs_begin);
    tok.expect(TokenType::Eq, "=");
    const char* rhs_begin=tok.token_start();
    std::string rhs = parse_net_reference(tok);
    const auto rhs_text=std::string_view(rhs_begin,tok.token_start()-rhs_begin);
    tok.expect(TokenType::Semi, ";");

    std::string inst_name = "_assign_" + std::to_string(assign_counter++);
    if (!flatten_inst_prefix_.empty()) {
        inst_name = flatten_inst_prefix_ + "/" + inst_name;
    }
    const NetId net_rhs=resolve_net(rhs),net_lhs=resolve_net(lhs);
    if(is_scalar_wire_reference(lhs_text) && is_scalar_wire_reference(rhs_text)) {
        wire_aliases_.emplace_back(net_lhs,net_rhs);
        return;
    }

    CellId cell = *network_.find_cell("__assign__");
    InstanceId inst = network_.create_instance(inst_name, cell);

    PinId pin_a = network_.create_pin("A", inst, PortDirection::Input);
    network_.add_pin(inst, pin_a);
    network_.connect_pin_to_net(pin_a, net_rhs);

    PinId pin_x = network_.create_pin("X", inst, PortDirection::Output);
    network_.add_pin(inst, pin_x);
    network_.connect_pin_to_net(pin_x, net_lhs);
}

void GateNetlistParser::flatten_instance(Tokenizer& tok,
                                          std::string_view cell_name,
                                          std::string_view inst_name) {
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
            port_map[c.port] = resolve_net_reference(c.net);
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
        bits.push_back(flattening_ && !scalar_constant_literal_value(ref).has_value()
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
    if (flattening_ && !literal_value.has_value()) {
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
