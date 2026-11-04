#pragma once

#include <string>
#include <string_view>
#include <vector>
#include <unordered_map>

#include "edacraft/core/liberty_db.hpp"

namespace te {

namespace parser {

enum class TokenType {
    Ident,
    String,
    Number,
    LBrace,
    RBrace,
    Colon,
    Semi,
    LParen,
    RParen,
    Comma,
    Eof,
};

struct Token {
    TokenType type;
    std::string text;
    int line;
};

// Hand-written tokenizer for Liberty format.
class LibertyTokenizer {
public:
    explicit LibertyTokenizer(std::string_view input);
    Token next();
    int current_line() const { return line_; }

private:
    std::string_view input_;
    size_t pos_ = 0;
    int line_ = 1;

    void skip_whitespace();
    void skip_comment();
    char peek() const;
    char advance();
    bool eof() const;
};

// Full Liberty parser: handles all NLDM constructs including
// template references, inline index values, pg_pin, leakage_power,
// and both group/statement table forms.
class LibertyParser {
public:
    explicit LibertyParser(std::string_view input);

    // Parse entire file into the Liberty database.
    void parse(edacraft::core::LibertyDB& liberty,
               edacraft::core::StringPool& strings);

private:
    Token& peek();
    Token consume();
    Token expect(TokenType type);
    bool match(TokenType type);

    void parse_top_level(edacraft::core::LibertyDB& liberty,
                         edacraft::core::StringPool& strings);
    void parse_library(edacraft::core::LibertyDB& liberty,
                       edacraft::core::StringPool& strings);
    void parse_library_attrs(edacraft::core::LibertyLibrary& lib,
                             edacraft::core::StringPool& strings);
    void parse_cell(edacraft::core::LibertyLibrary& lib,
                    edacraft::core::StringPool& strings);
    void parse_pin(edacraft::core::LibertyLibrary& lib,
                   edacraft::core::LibertyCellData& cell,
                   edacraft::core::StringPool& strings);
    void parse_timing(edacraft::core::LibertyLibrary& lib,
                      edacraft::core::LibertyCellData& cell,
                      edacraft::core::LibertyPinData& pin,
                      edacraft::core::StringPool& strings);
    void parse_internal_power(edacraft::core::LibertyPinData& pin,
                              edacraft::core::StringPool& strings);

    // Table templates at library level: store by name for later reference
    void parse_table_template(edacraft::core::StringPool& strings);

    // Group-based table: { index_1(...); index_2(...); values(...); }
    void parse_table_group(edacraft::core::LibertyCellData& cell,
                           const std::string& table_type,
                           edacraft::core::LibertyPinData& pin);

    // Parse table body into a local NldmTable, resolving axes from inline or template.
    void parse_table_body(edacraft::core::NldmTable* table,
                          const std::string& template_ref,
                          edacraft::core::StringPool& strings);

    // Parse CSM output_current 3D table (input_slew × load_cap × time).
    void parse_csm_table_body(edacraft::core::CsmOutputCurrentTable* table,
                              const std::string& template_ref,
                              edacraft::core::StringPool& strings);

    void skip_group();
    void skip_statement();

    float parse_number();
    std::string parse_statement_text_until_semi();
    std::vector<float> parse_index_values(std::string_view raw);
    std::string parse_paren_or_plain();

    LibertyTokenizer tokenizer_;
    Token current_;
    bool have_current_ = false;

    // Cached templates: name -> (axis1, axis2, var1, var2)
    struct TemplateDef {
        std::vector<float> axis1;
        std::vector<float> axis2;
        std::string var1;
        std::string var2;
    };
    std::unordered_map<std::string, TemplateDef> templates_;

    // Normalize NLDM table axes based on Liberty variable semantics.
    // For delay/slew tables: ensures axis1 = input_transition, axis2 = output_load.
    // For constraint tables: ensures axis1 = related_pin_transition, axis2 = constrained_pin_transition.
    void normalize_nldm_axes(edacraft::core::NldmTable* table,
                             const std::string& template_ref,
                             bool is_constraint = false);
};

} // namespace parser
} // namespace te
