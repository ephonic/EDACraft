// token.cpp — 词法单元实现
#include "token.hpp"

#include <cctype>
#include <cmath>
#include <cstring>

namespace rfsim {

Lexer::Lexer(std::string source, std::string filename)
    : source_(std::move(source)), filename_(std::move(filename)) {}

SourceLoc Lexer::here() const {
    return {filename_, line_, col_};
}

void Lexer::advance(size_t n) {
    for (size_t i = 0; i < n && pos_ < source_.size(); ++i) {
        if (source_[pos_] == '\n') { ++line_; col_ = 1; }
        else { ++col_; }
        ++pos_;
    }
}

void Lexer::skipWhitespaceAndComments() {
    while (pos_ < source_.size()) {
        char c = source_[pos_];
        // 空白
        if (c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\f' || c == '\v') {
            advance();
            continue;
        }
        // 行首整行注释：* 出现在行首（前一字符为 \n 或文件开头）
        if (c == '*' && (pos_ == 0 || source_[pos_ - 1] == '\n')) {
            while (pos_ < source_.size() && source_[pos_] != '\n') advance();
            continue;
        }
        // 续行符 +：出现在行首（仅空白之后），与下一行合并
        // SPICE 约定 + 在行首表示续行。这里消费 + 与其后到行尾的空白。
        if (c == '+') {
            // 判断是否在行首：回看本行到 pos_ 是否只有空白
            bool at_line_start = true;
            for (size_t k = pos_; k > 0; --k) {
                char p = source_[k - 1];
                if (p == '\n') break;
                if (p != ' ' && p != '\t' && p != '\r') { at_line_start = false; break; }
            }
            if (at_line_start) {
                advance(); // 消费 +
                while (pos_ < source_.size() && (source_[pos_] == ' ' || source_[pos_] == '\t')) advance();
                continue;
            }
            // 否则 + 是运算符，交给 lexOne
            break;
        }
        // 行内注释 $ 或 ;
        if (c == '$' || c == ';') {
            while (pos_ < source_.size() && source_[pos_] != '\n') advance();
            continue;
        }
        break;
    }
}

// SPICE 数值后缀表（大小写不敏感，但 mil/meg 等需精确匹配）
// 注意：m 既是 milli(1e-3) 在 HSPICE 中也可表 mega(1e6) 的简写冲突——
// HSPICE 约定 m=1e-3, meg=1e6, g=1e9, t=1e12, k=1e3。
// 单字母后缀取常用工程解释。
struct Suffix { const char* s; double scale; };
static const Suffix kSuffixes[] = {
    {"meg", 1e6},  {"g", 1e9}, {"t", 1e12},
    {"k", 1e3},
    {"m", 1e-3}, {"u", 1e-6}, {"n", 1e-9}, {"p", 1e-12}, {"f", 1e-15}, {"a", 1e-18},
    // 比例后缀（HSPICE）
    {"x", 1e6},    // x = meg
    {"mil", 25.4e-6}, // mil = 25.4 微米
};

bool Lexer::parseNumberLiteral(std::string_view s, double& outValue, size_t& consumed) {
    // 解析 [+-]?digits(.digits)?([eE][+-]?digits)?
    size_t i = 0;
    const size_t n = s.size();
    std::string num;
    num.reserve(16);
    if (i < n && (s[i] == '+' || s[i] == '-')) { num.push_back(s[i++]); }
    bool hasDigit = false, hasDot = false;
    while (i < n) {
        if (std::isdigit(static_cast<unsigned char>(s[i]))) { num.push_back(s[i++]); hasDigit = true; }
        else if (s[i] == '.' && !hasDot) { num.push_back(s[i++]); hasDot = true; }
        else break;
    }
    if (!hasDigit) return false;
    if (i < n && (s[i] == 'e' || s[i] == 'E')) {
        size_t save = i;
        num.push_back(s[i++]);
        if (i < n && (s[i] == '+' || s[i] == '-')) num.push_back(s[i++]);
        bool expDigit = false;
        while (i < n && std::isdigit(static_cast<unsigned char>(s[i]))) { num.push_back(s[i++]); expDigit = true; }
        if (!expDigit) { i = save; num.resize(num.size() - 1); } // 回退，e 不作为指数
    }

    double value = 0.0;
    try { value = std::stod(num); } catch (...) { return false; }

    // 剥离单位后缀：仅识别字母后缀，遇到非字母停止
    // 后缀可包含单位名如 farad/hertz/volts，但工程值由第一个匹配的后缀决定。
    // 策略：取连续字母，先尝试最长后缀匹配（meg/mil），再单字母。
    // 剥离单位后缀：连续字母中，先匹配工程比例后缀（meg/mil/单字母），
    // 剩余字母视为单位名（farad/hz/volts/ohm...）忽略。
    // 例: 1kohm -> k(1e3) + "ohm"(忽略) = 1000
    //     1meg  -> meg(1e6) = 1e6
    //     1uf   -> u(1e-6) + "f"(忽略, 不再二次乘) = 1e-6
    size_t sufStart = i;
    while (i < n && std::isalpha(static_cast<unsigned char>(s[i]))) ++i;
    if (i > sufStart) {
        std::string low(s.substr(sufStart, i - sufStart));
        for (auto& c : low) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        double scale = 1.0;
        bool matched = false;
        // 先尝试最长多字母后缀的前缀匹配（meg/mil）
        for (const auto& e : kSuffixes) {
            size_t elen = std::strlen(e.s);
            if (elen >= 2 && low.size() >= elen && low.compare(0, elen, e.s) == 0) {
                scale = e.scale; matched = true; break;
            }
        }
        // 再单字母前缀匹配（m/u/p/k/g/t/f/a/x）
        if (!matched) {
            for (const auto& e : kSuffixes) {
                size_t elen = std::strlen(e.s);
                if (elen == 1 && !low.empty() && low[0] == e.s[0]) {
                    scale = e.scale; matched = true; break;
                }
            }
        }
        // 未匹配（纯单位名如 ohm/volts）则 scale=1
        (void)matched;
        value *= scale;
    }
    outValue = value;
    consumed = i;
    return true;
}

Token Lexer::lexNumber() {
    SourceLoc start = here();
    double value = 0.0;
    size_t consumed = 0;
    parseNumberLiteral(std::string_view(source_).substr(pos_), value, consumed);
    Token t;
    t.kind = TokenKind::Number;
    t.value = value;
    t.text = source_.substr(pos_, consumed);
    t.loc = start;
    advance(consumed);
    return t;
}

Token Lexer::lexWord() {
    SourceLoc start = here();
    size_t begin = pos_;
    // 标识符：字母/数字/_/$/#/?/.(在名字中间)/! 等
    // SPICE 名字相当宽松，只要不以数字开头
    while (pos_ < source_.size()) {
        char c = source_[pos_];
        if (std::isalnum(static_cast<unsigned char>(c)) || c == '_' || c == '$' ||
            c == '#' || c == '?' || c == '!') { advance(); }
        else break;
    }
    std::string word = source_.substr(begin, pos_ - begin);
    // 大小写归一（HSPICE 不区分大小写）
    for (auto& c : word) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    Token t;
    t.kind = TokenKind::Word;
    t.text = std::move(word);
    t.loc = start;
    return t;
}

Token Lexer::lexString() {
    SourceLoc start = here();
    char quote = source_[pos_];  // 开引号（" 或 '）
    advance(); // 跳过开引号
    size_t begin = pos_;
    while (pos_ < source_.size() && source_[pos_] != quote) {
        if (source_[pos_] == '\\' && pos_ + 1 < source_.size()) advance();
        advance();
    }
    std::string s = source_.substr(begin, pos_ - begin);
    if (pos_ < source_.size()) advance(); // 闭引号
    Token t;
    t.kind = TokenKind::String;
    t.text = std::move(s);
    t.loc = start;
    return t;
}

Token Lexer::lexBraceExpr() {
    // 读取 { 到匹配 } 的内容，支持嵌套花括号。返回 Word token，text 为内部表达式原文。
    SourceLoc start = here();
    advance(); // 跳过开 {
    size_t begin = pos_;
    int depth = 1;
    while (pos_ < source_.size() && depth > 0) {
        char c = source_[pos_];
        if (c == '{') ++depth;
        else if (c == '}') { --depth; if (depth == 0) break; }
        advance();
    }
    std::string expr = source_.substr(begin, pos_ - begin);
    if (pos_ < source_.size()) advance(); // 跳过闭 }
    Token t;
    t.kind = TokenKind::Word;  // 作为 Word，但标记为表达式（内部含运算符）
    t.text = std::move(expr);
    t.loc = start;
    return t;
}

Token Lexer::lexOne() {
    skipWhitespaceAndComments();
    if (pos_ >= source_.size()) {
        Token t; t.kind = TokenKind::EndOfFile; t.loc = here(); return t;
    }
    char c = source_[pos_];
    SourceLoc start = here();

    // 数值字面量：以数字开头，或以 . 后接数字开头
    if (std::isdigit(static_cast<unsigned char>(c)) ||
        (c == '.' && pos_ + 1 < source_.size() && std::isdigit(static_cast<unsigned char>(source_[pos_ + 1])))) {
        return lexNumber();
    }
    // 带 [+-] 的数值：仅当后接数字或 .数字
    if ((c == '+' || c == '-') && pos_ + 1 < source_.size() &&
        (std::isdigit(static_cast<unsigned char>(source_[pos_ + 1])) ||
         (source_[pos_ + 1] == '.' && pos_ + 2 < source_.size() && std::isdigit(static_cast<unsigned char>(source_[pos_ + 2]))))) {
        return lexNumber();
    }

    // 字符串（双引号或单引号——HSPICE .lib 路径常用单引号）
    if (c == '"' || c == '\'') return lexString();

    // 花括号参数表达式 {expr}：作为整体 Expr token 返回（保留内部文本，去掉外层花括号）
    if (c == '{') return lexBraceExpr();

    // 标点与运算符
    switch (c) {
        case '(': advance(); return {TokenKind::LParen, "(", 0.0, start};
        case ')': advance(); return {TokenKind::RParen, ")", 0.0, start};
        case '[': advance(); return {TokenKind::LBracket, "[", 0.0, start};
        case ']': advance(); return {TokenKind::RBracket, "]", 0.0, start};
        case '}': advance(); return {TokenKind::RBrace, "}", 0.0, start}; // 多余的 } 兜底
        case '=': advance(); return {TokenKind::Equal, "=", 0.0, start};
        case ',': advance(); return {TokenKind::Comma, ",", 0.0, start};
        case '-': advance(); return {TokenKind::Minus, "-", 0.0, start};
        case '*': advance(); return {TokenKind::Star, "*", 0.0, start};
        case '/': advance(); return {TokenKind::Slash, "/", 0.0, start};
        case '^': advance(); return {TokenKind::Caret, "^", 0.0, start};
        case '+':
            // 到这里说明 + 不是续行（skipWhitespaceAndComments 已处理行首 +），作为运算符
            advance(); return {TokenKind::PlusOp, "+", 0.0, start};
        case '.':
            // 单独的 dot token（控制卡以 . 开头）
            advance(); return {TokenKind::Dot, ".", 0.0, start};
        default:
            break;
    }

    // 标识符
    if (std::isalpha(static_cast<unsigned char>(c)) || c == '_' || c == '$' || c == '#' || c == '!') {
        return lexWord();
    }

    // 未知字符：作为单字符 Word 返回并告警由上层处理
    advance();
    Token t;
    t.kind = TokenKind::Word;
    t.text = std::string(1, c);
    t.loc = start;
    return t;
}

Token Lexer::next() {
    if (peeked_) { peeked_ = false; return std::move(peek_); }
    return lexOne();
}

Token Lexer::peek() {
    if (!peeked_) { peek_ = lexOne(); peeked_ = true; }
    return peek_;
}

} // namespace rfsim
