// expression.cpp — 递归下降表达式求值器
#include "expression.hpp"
#include "token.hpp"

#include <cmath>
#include <sstream>

namespace rfsim {

namespace {

// 基于字符串的简单 tokenizer（复用 Lexer 的数值后缀逻辑）
// 为避免与网表 Lexer 混淆，这里用一个轻量递归下降解析器直接操作字符串下标。
struct ExprParser {
    std::string_view s;
    size_t i = 0;
    const EvalContext& ctx;
    std::string err;

    explicit ExprParser(std::string_view src, const EvalContext& c) : s(src), ctx(c) {}

    void skipWs() {
        while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) ++i;
    }
    bool eof() const { return i >= s.size(); }

    // expr := term (('+'|'-') term)*
    double parseExpr() {
        double v = parseTerm();
        skipWs();
        while (!eof() && (s[i] == '+' || s[i] == '-')) {
            char op = s[i++];
            double r = parseTerm();
            if (op == '+') v += r; else v -= r;
            skipWs();
        }
        return v;
    }
    // term := factor (('*'|'/') factor)*
    double parseTerm() {
        double v = parseFactor();
        skipWs();
        while (!eof() && (s[i] == '*' || s[i] == '/')) {
            char op = s[i++];
            double r = parseFactor();
            if (op == '*') v *= r;
            else {
                if (r == 0.0) { err = "division by zero"; return 0; }
                v /= r;
            }
            skipWs();
        }
        return v;
    }
    // factor := ('-'|'+') factor | power
    double parseFactor() {
        skipWs();
        if (!eof() && (s[i] == '+' || s[i] == '-')) {
            char op = s[i++];
            double v = parseFactor();
            return op == '-' ? -v : v;
        }
        return parsePower();
    }
    // power := atom ('^' factor)?   (右结合)
    double parsePower() {
        double base = parseAtom();
        skipWs();
        if (!eof() && s[i] == '^') {
            ++i;
            double e = parseFactor(); // 右结合
            return std::pow(base, e);
        }
        return base;
    }
    // atom := number | name | name '(' expr ')' | '(' expr ')'
    double parseAtom() {
        skipWs();
        if (eof()) { err = "unexpected end of expression"; return 0; }
        if (s[i] == '(') {
            ++i;
            double v = parseExpr();
            skipWs();
            if (eof() || s[i] != ')') { err = "missing ')'"; return 0; }
            ++i;
            return v;
        }
        // 数值字面量
        if (std::isdigit(static_cast<unsigned char>(s[i])) ||
            (s[i] == '.' && i + 1 < s.size() && std::isdigit(static_cast<unsigned char>(s[i + 1])))) {
            double v = 0.0; size_t used = 0;
            if (!Lexer::parseNumberLiteral(s.substr(i), v, used)) { err = "invalid number"; return 0; }
            i += used;
            return v;
        }
        // 标识符（变量或函数调用）
        if (std::isalpha(static_cast<unsigned char>(s[i])) || s[i] == '_') {
            size_t start = i;
            while (i < s.size() && (std::isalnum(static_cast<unsigned char>(s[i])) || s[i] == '_')) ++i;
            std::string name(s.substr(start, i - start));
            for (auto& c : name) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            skipWs();
            if (!eof() && s[i] == '(') {
                // 函数调用（单参）
                ++i;
                double arg = parseExpr();
                skipWs();
                if (eof() || s[i] != ')') { err = "missing ')' in function call"; return 0; }
                ++i;
                auto it = ctx.funcs.find(name);
                if (it == ctx.funcs.end()) { err = "unknown function: " + name; return 0; }
                return it->second(arg);
            }
            // 变量
            auto it = ctx.vars.find(name);
            if (it == ctx.vars.end()) { err = "unknown variable: " + name; return 0; }
            return it->second;
        }
        err = "unexpected character in expression";
        return 0;
    }
};

} // namespace

bool evaluateExpression(std::string_view expr, const EvalContext& ctx,
                        double& outValue, std::string& errMessage) {
    ExprParser p(expr, ctx);
    double v = p.parseExpr();
    p.skipWs();
    if (!p.err.empty()) { errMessage = p.err; return false; }
    if (!p.eof()) { errMessage = "trailing characters in expression"; return false; }
    outValue = v;
    return true;
}

void registerBuiltinFunctions(EvalContext& ctx) {
    ctx.funcs["sin"]   = [](double x){ return std::sin(x); };
    ctx.funcs["cos"]   = [](double x){ return std::cos(x); };
    ctx.funcs["tan"]   = [](double x){ return std::tan(x); };
    ctx.funcs["asin"]  = [](double x){ return std::asin(x); };
    ctx.funcs["acos"]  = [](double x){ return std::acos(x); };
    ctx.funcs["atan"]  = [](double x){ return std::atan(x); };
    ctx.funcs["exp"]   = [](double x){ return std::exp(x); };
    ctx.funcs["ln"]    = [](double x){ return std::log(x); };
    ctx.funcs["log"]   = [](double x){ return std::log10(x); };
    ctx.funcs["sqrt"]  = [](double x){ return std::sqrt(x); };
    ctx.funcs["abs"]   = [](double x){ return std::fabs(x); };
    ctx.funcs["pow"]   = [](double x){ return std::pow(x, /*placeholder*/0) * 0 + x; }; // 单参占位，实际多参未支持
    // 注: pow 实际需双参，此处仅注册签名；表达式层单参语义下不常用，保留以防误用
    ctx.funcs["sgn"]   = [](double x){ return (x > 0) ? 1.0 : ((x < 0) ? -1.0 : 0.0); };
}

} // namespace rfsim
