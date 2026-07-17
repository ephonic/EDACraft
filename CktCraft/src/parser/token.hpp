// token.hpp — SPICE 词法单元定义
#ifndef RFSIM_PARSER_TOKEN_HPP
#define RFSIM_PARSER_TOKEN_HPP

#include "../rfsim.hpp"
#include <string>
#include <variant>

namespace rfsim {

// SPICE 词法单元种类
enum class TokenKind {
    EndOfFile,      // 文件结束
    Word,           // 标识符/关键字/器件名/值名（HSPICE 不区分大小写，归一化为小写）
    Number,         // 数值字面量（已剥离单位后缀，存为 double）
    String,         // 带引号字符串 "..."
    LParen,         // (
    RParen,         // )
    LBracket,       // [
    RBracket,       // ]
    LBrace,         // {   （参数表达式包裹）
    RBrace,         // }
    Equal,          // =   （参数赋值）
    Comma,          // ,
    Dot,            // .   （控制卡开头，独立保留以便区分）
    Plus,           // +   （续行符，词法层已合并，不会作为 token 产出）
    // 运算符（用于 .param 表达式）
    PlusOp,         // +
    Minus,          // -
    Star,           // *
    Slash,          // /
    Caret,          // ^
};

// 词法单元
struct Token {
    TokenKind   kind = TokenKind::EndOfFile;
    std::string text;            // 原始文本（Word/Number 的规范化文本）
    double      value = 0.0;     // Number 时的数值
    SourceLoc   loc;
};

    // 词法器：将源文本切分为 token 流，处理：
    //   - 续行（行首 + 合并到上一行）
    //   - 注释（行首 * 整行注释；行内 $ 或 ;）
    //   - 大小写归一（HSPICE 不区分大小写，但保留字符串字面量原文）
    //   - 数值字面量的单位后缀剥离（meg/u/p/f/k/g/...）
    class Lexer {
    public:
        explicit Lexer(std::string source, std::string filename = "<string>");

        // 逐个产出 token，直到 EndOfFile
        [[nodiscard]] Token next();

        // 只看下一个但不消费（ lookahead = 1）
        [[nodiscard]] Token peek();

        // 解析数值字面量 + 单位后缀；供表达式求值器复用。
        // 成功时 outValue 存数值，consumed 存消费的字符数（含后缀）
        static bool parseNumberLiteral(std::string_view s, double& outValue, size_t& consumed);

    private:
    std::string source_;
    std::string filename_;
    size_t      pos_  = 0;   // 字节偏移
    uint32_t    line_ = 1;   // 当前行号
    uint32_t    col_  = 1;   // 当前列号

    // 预读缓存（peek 用）
    bool        peeked_ = false;
    Token       peek_;

    [[nodiscard]] SourceLoc here() const;
    char ch() const noexcept { return pos_ < source_.size() ? source_[pos_] : '\0'; }
    char ch(size_t off) const noexcept { return pos_ + off < source_.size() ? source_[pos_ + off] : '\0'; }
    void advance(size_t n = 1);

    Token lexOne();
    Token lexNumber();
    Token lexWord();
    Token lexString();
    Token lexBraceExpr();

    // 处理续行与行首注释：返回是否应跳过当前行首的空白/注释/续行
    void skipWhitespaceAndComments();
};

} // namespace rfsim

#endif // RFSIM_PARSER_TOKEN_HPP
