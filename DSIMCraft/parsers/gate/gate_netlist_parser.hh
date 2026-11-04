#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "network/network.hh"

namespace te {

// ============================================================================
// Streaming gate-level netlist parser
// ============================================================================
// Designed for Yosys-synthesized and hand-written gate-level Verilog.
// Does NOT build an AST — parses directly into Network.
//
// Supported subset:
//   module Name (port1, port2, ...);
//   input/output/inout [msb:lsb] name1, name2, ...;
//   wire [msb:lsb] name1, name2, ...;
//   assign lhs = rhs;
//   CELL_TYPE inst_name (.PORT(net), ...);
//   CELL_TYPE inst_name (net1, net2, ...);
//
// Features:
//   - Multi-line port lists & instantiations
//   - Escaped identifiers: \name <space>
//   - Bit-select & part-select: name[7], name[7:0]
//   - Constant literals as nets: 1'b0, 32'd9
//   - Automatic top-module detection
//   - Automatic black-box cell inference from instantiations
//   - Hierarchical module flattening (modules with internal logic are expanded)
// ============================================================================

class GateNetlistParser {
public:
    explicit GateNetlistParser(Network& network);

    // Parse a Verilog file and populate the network.
    // Returns the top module name.
    // Throws std::runtime_error on unrecoverable parse errors.
    std::string parse(std::string_view filepath,
                      std::string_view preferred_top_name = {});
    // Transfer already preprocessed text; still uses the independent streaming
    // structural grammar and network elaborator, with no RTL AST dependency.
    std::string parse_source(std::string source, std::string_view filename,
                             std::string_view preferred_top_name = {});

    struct PortInfo {
        std::string name; PortDirection direction; std::vector<std::string> bits;
    };
    std::vector<PortInfo> top_ports() const;
    // Simulation rejects timing-only approximations and unsupported syntax.
    void set_simulation_mode(bool enabled) { simulation_mode_ = enabled; strict_mode_ = enabled; }

    // Liberty scalar pins supply real directions, independent of timing guesses.
    using SimulationPorts = std::unordered_map<std::string, std::vector<std::pair<std::string, PortDirection>>>;
    void set_simulation_ports(SimulationPorts ports) { simulation_ports_ = std::move(ports); }
    struct TimingPort { std::string name; PortDirection direction; NetId net; };
    using LeafObserver = std::function<void(InstanceId, const std::vector<std::string>&)>;
    using ScopeObserver = std::function<void(const std::vector<std::string>&, const std::string&, const std::vector<TimingPort>&)>;
    // Optional hierarchy-preserving export. No per-instance metadata is kept
    // by the parser; observers consume it while Network names are still live.
    void set_timing_observers(LeafObserver leaf, ScopeObserver scope) {
        timing_leaf_ = std::move(leaf); timing_scope_ = std::move(scope);
    }

    // Configuration
    void set_strict_mode(bool strict) { strict_mode_ = strict; }
    bool strict_mode() const { return strict_mode_; }

private:
    // ------------------------------------------------------------------------
    // Tokenizer
    // ------------------------------------------------------------------------
    enum class TokenType : uint8_t {
        EOI,
        // Keywords
        Module, EndModule,
        Input, Output, Inout, Wire, Reg, Assign, Always,
        // Identifiers / literals
        Identifier, Number,
        // Punctuation
        LParen, RParen,       // ( )
        LBracket, RBracket,   // [ ]
        LBrace, RBrace,       // { }
        Comma, Semi, Dot, Eq, Colon,
    };

    struct Token {
        TokenType type;
        std::string text;   // raw text (for identifiers, numbers)
        uint32_t line{0};
        uint32_t col{0};
    };

    class Tokenizer {
    public:
        explicit Tokenizer(std::string_view source);
        Token next();
        const Token& peek() const { return current_; }
        void consume() { current_ = next(); }
        bool match(TokenType t) {
            if (current_.type == t) { consume(); return true; }
            return false;
        }
        bool expect(TokenType t, const char* context);
        uint32_t line() const { return current_.line; }
        uint32_t col() const { return current_.col; }
        const char* token_start() const { return token_start_; }
    private:
        const char* begin_;
        const char* end_;
        const char* pos_;
        const char* token_start_{nullptr};
        uint32_t line_{1};
        uint32_t col_{1};
        Token current_;

        void skip_whitespace_and_comments();
        void advance_char();
        Token make_token(TokenType t, const char* start, size_t len);
    };

    // ------------------------------------------------------------------------
    // Pass 1: metadata collection
    // ------------------------------------------------------------------------
    struct ModuleMeta {
        std::vector<std::pair<std::string, PortDirection>> ports;
        std::unordered_map<std::string, std::vector<std::string>> signal_bits;
        bool defined{false};      // true if module body is present in file
        bool has_logic{false};    // true if body contains instances or assigns
        std::string_view body;    // source text of module body
    };
    struct CellMeta {
        std::unordered_set<std::string> ports;
    };

    void collect_metadata(std::string_view filepath);
    void scan_module_ports(Tokenizer& tok, ModuleMeta& meta);

    // ------------------------------------------------------------------------
    // Pass 2: network building
    // ------------------------------------------------------------------------
    void build_network(std::string_view filepath, std::string_view top_name);
    void parse_module_body(Tokenizer& tok, const std::string& mod_name,
                           ModuleMeta* meta = nullptr);

    // Declarations
    void parse_port_decl(Tokenizer& tok, PortDirection dir);
    void parse_wire_decl(Tokenizer& tok);
    void parse_assign_stmt(Tokenizer& tok, uint32_t& assign_counter);

    // Instances
    void parse_instance(Tokenizer& tok, std::string_view cell_name,
                         std::string_view inst_name);

    // Hierarchical flattening
    static constexpr int kMaxFlattenDepth = 100;
    void flatten_module(const std::string& mod_name,
                        const std::string& inst_name,
                        const std::unordered_map<std::string, std::string>& port_map);
    void flatten_port_decl(Tokenizer& tok, PortDirection dir);
    void flatten_wire_decl(Tokenizer& tok);
    void flatten_assign_stmt(Tokenizer& tok, uint32_t& assign_counter);
    void flatten_instance(Tokenizer& tok, std::string_view cell_name,
                           std::string_view inst_name);
    std::string remap_net_name(std::string_view local_name);
    std::string resolve_net_reference(const std::string& net);

    // Helpers
    std::string parse_net_reference(Tokenizer& tok);
    // Consume the remainder of a net expression after its first reference.
    // The timing graph only needs the referenced net; operators and constant
    // operands are skipped while preserving the surrounding comma/semicolon/
    // parenthesis delimiter for the caller.
    void consume_net_expression_tail(Tokenizer& tok);
    std::vector<std::string> parse_identifier_list(Tokenizer& tok);
    PortDirection lookup_port_direction(std::string_view cell_name,
                                         std::string_view port_name) const;

    // Parse a Verilog range [msb:lsb] and return individual bit names.
    // Returns empty vector if range is not a simple integer range.
    std::vector<std::string> expand_range(Tokenizer& tok, const std::string& base_name);

    // Resolve or create a net by name. Constants get their own net.
    NetId resolve_net(std::string_view name);

    // Error reporting
    [[noreturn]] void error(Tokenizer& tok, const std::string& msg);
    void warn(Tokenizer& tok, const std::string& msg);

    // ------------------------------------------------------------------------
    // State
    // ------------------------------------------------------------------------
    Network& network_;
    bool strict_mode_{false};
    bool simulation_mode_{false};
    std::string selected_top_;
    void validate_simulation_source();
    struct SimulationReference {
        std::vector<std::string> bits; // MSB first; globally scoped during build
        char fill = 0; // context-sized '0/'1/'x/'z, otherwise unsigned extension
    };
    SimulationPorts simulation_ports_;
    LeafObserver timing_leaf_;
    ScopeObserver timing_scope_;
    std::vector<std::string> timing_path_;
    uint64_t simulation_generated_ = 0;
    std::string simulation_identifier(Tokenizer& tok);
    SimulationReference simulation_reference(Tokenizer& tok, bool target, unsigned depth = 0);
    void simulation_instance(Tokenizer& tok, const std::string& cell, const std::string& name);
    void simulation_assign(Tokenizer& tok);
    void simulation_copy(const std::vector<std::string>& target, const std::vector<std::string>& source);
    NetId simulation_net(const std::string& name);
    static std::vector<std::string> simulation_resize(const SimulationReference& ref, size_t width);

    InstanceId current_top_inst_{NULL_INSTANCE};

    // Pass 1 results
    std::string source_;
    std::unordered_map<std::string, ModuleMeta> modules_;
    std::unordered_map<std::string, CellMeta> inferred_cells_;
    std::unordered_set<std::string> instantiated_modules_;
    uint32_t dummy_net_counter_ = 0;

    // Flattening state
    std::string flatten_inst_prefix_;
    std::string current_module_;
    std::unordered_map<std::string, std::string> flatten_net_map_;
    bool flattening_ = false;
    int flatten_depth_ = 0;
};

} // namespace te
