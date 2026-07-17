// expression.cpp — 递归下降表达式求值器
//
// C2（Phase C）增强：
//   - 多参函数：name(arg1, arg2, ...) —— 优先查 multiFuncs，回退单参 funcs
//   - 条件表达式：cond ? a : b（右结合，最低优先级）
//   - 逻辑或 ||、逻辑与 &&、比较 == != < > <= >=、逻辑非 !
//   - 结果布尔值用 1.0（真）/0.0（假）
//
// 优先级（从低到高）：
//   ?:  →  ||  →  &&  →  == !=  →  < > <= >=  →  + -  →  * /  →  unary +-!  →  ^  →  atom
#include "expression.hpp"
#include "token.hpp"

#include <cmath>
#include <sstream>

namespace rfsim {

namespace {

// 基于字符串的简单 tokenizer（复用 Lexer 的数值后缀逻辑）
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

    // ternary := logicOr ('?' ternary ':' ternary)?
    double parseTernary() {
        double cond = parseLogicOr();
        skipWs();
        if (!eof() && s[i] == '?') {
            ++i;
            double a = parseTernary();
            skipWs();
            if (eof() || s[i] != ':') { err = "missing ':' in ternary"; return 0; }
            ++i;
            double b = parseTernary();
            return (cond != 0.0) ? a : b;
        }
        return cond;
    }

    // logicOr := logicAnd ('||' logicAnd)*
    double parseLogicOr() {
        double v = parseLogicAnd();
        skipWs();
        while (!eof() && s[i] == '|' && i + 1 < s.size() && s[i + 1] == '|') {
            i += 2;
            double r = parseLogicAnd();
            v = (v != 0.0 || r != 0.0) ? 1.0 : 0.0;
            skipWs();
        }
        return v;
    }

    // logicAnd := equality ('&&' equality)*
    double parseLogicAnd() {
        double v = parseEquality();
        skipWs();
        while (!eof() && s[i] == '&' && i + 1 < s.size() && s[i + 1] == '&') {
            i += 2;
            double r = parseEquality();
            v = (v != 0.0 && r != 0.0) ? 1.0 : 0.0;
            skipWs();
        }
        return v;
    }

    // equality := relational (('==' | '!=') relational)*
    double parseEquality() {
        double v = parseRelational();
        skipWs();
        while (!eof() && s[i] == '=' && i + 1 < s.size() && s[i + 1] == '=') {
            i += 2; double r = parseRelational(); v = (v == r) ? 1.0 : 0.0; skipWs();
        }
        while (!eof() && s[i] == '!' && i + 1 < s.size() && s[i + 1] == '=') {
            i += 2; double r = parseRelational(); v = (v != r) ? 1.0 : 0.0; skipWs();
        }
        return v;
    }

    // relational := additive (('<'|'>'|'<='|'>=') additive)*
    double parseRelational() {
        double v = parseAdditive();
        skipWs();
        while (!eof()) {
            if (s[i] == '<' && i + 1 < s.size() && s[i + 1] == '=') {
                i += 2; double r = parseAdditive(); v = (v <= r) ? 1.0 : 0.0;
            } else if (s[i] == '>' && i + 1 < s.size() && s[i + 1] == '=') {
                i += 2; double r = parseAdditive(); v = (v >= r) ? 1.0 : 0.0;
            } else if (s[i] == '<') {
                ++i; double r = parseAdditive(); v = (v < r) ? 1.0 : 0.0;
            } else if (s[i] == '>') {
                ++i; double r = parseAdditive(); v = (v > r) ? 1.0 : 0.0;
            } else break;
            skipWs();
        }
        return v;
    }

    // additive := term (('+'|'-') term)*   （原 parseExpr，降级一层）
    double parseAdditive() {
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
    // factor := ('-'|'+'|'!') factor | power
    double parseFactor() {
        skipWs();
        if (!eof() && (s[i] == '+' || s[i] == '-')) {
            char op = s[i++];
            double v = parseFactor();
            return op == '-' ? -v : v;
        }
        if (!eof() && s[i] == '!') {
            ++i;
            double v = parseFactor();
            return (v == 0.0) ? 1.0 : 0.0;
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
    // atom := number | name | name '(' args ')' | '(' ternary ')'
    double parseAtom() {
        skipWs();
        if (eof()) { err = "unexpected end of expression"; return 0; }
        if (s[i] == '(') {
            ++i;
            double v = parseTernary();
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
                // 函数调用：解析逗号分隔的参数列表
                ++i;
                std::vector<double> args;
                skipWs();
                if (!eof() && s[i] == ')') {
                    ++i;  // 无参函数
                } else {
                    args.push_back(parseTernary());
                    skipWs();
                    while (!eof() && s[i] == ',') {
                        ++i;
                        args.push_back(parseTernary());
                        skipWs();
                    }
                    if (eof() || s[i] != ')') { err = "missing ')' in function call"; return 0; }
                    ++i;
                }
                // C2：优先查多参函数表（含 agauss/pow/min/max/atan2/if/用户 .func）
                auto mit = ctx.multiFuncs.find(name);
                if (mit != ctx.multiFuncs.end()) {
                    return mit->second(args);
                }
                // 回退单参函数（向后兼容）
                auto it = ctx.funcs.find(name);
                if (it != ctx.funcs.end()) {
                    if (args.size() != 1) {
                        err = "function '" + name + "' expects 1 arg, got " + std::to_string(args.size());
                        return 0;
                    }
                    return it->second(args[0]);
                }
                err = "unknown function: " + name;
                return 0;
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
    double v = p.parseTernary();  // C2：顶层入口改为 ternary（含 ?:）
    p.skipWs();
    if (!p.err.empty()) { errMessage = p.err; return false; }
    if (!p.eof()) { errMessage = "trailing characters in expression"; return false; }
    outValue = v;
    return true;
}

void registerBuiltinFunctions(EvalContext& ctx) {
    // 单参函数（向后兼容）
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
    ctx.funcs["sgn"]   = [](double x){ return (x > 0) ? 1.0 : ((x < 0) ? -1.0 : 0.0); };

    // C2：多参函数（HSPICE/Verilog-A 常用）。
    // agauss(nom, abs, nsgma) = nom + abs·tan()... 实际 HSPICE 语义为高斯分布，
    // 用于 monte-carlo；确定性求值时取名义值 nom（abs/sgma 项均值为 0）。
    // unif(nom, abs) 同理取 nom。
    ctx.multiFuncs["agauss"] = [](const std::vector<double>& a) -> double {
        // 确定性求值：取均值（nom）。a = {nom, abs, nsgma}
        return a.empty() ? 0.0 : a[0];
    };
    ctx.multiFuncs["unif"] = [](const std::vector<double>& a) -> double {
        return a.empty() ? 0.0 : a[0];
    };
    ctx.multiFuncs["gauss"] = [](const std::vector<double>& a) -> double {
        return a.empty() ? 0.0 : a[0];
    };
    ctx.multiFuncs["pow"] = [](const std::vector<double>& a) -> double {
        if (a.size() < 2) return 0.0;
        return std::pow(a[0], a[1]);
    };
    ctx.multiFuncs["min"] = [](const std::vector<double>& a) -> double {
        if (a.empty()) return 0.0;
        double m = a[0]; for (size_t k = 1; k < a.size(); ++k) m = std::min(m, a[k]);
        return m;
    };
    ctx.multiFuncs["max"] = [](const std::vector<double>& a) -> double {
        if (a.empty()) return 0.0;
        double m = a[0]; for (size_t k = 1; k < a.size(); ++k) m = std::max(m, a[k]);
        return m;
    };
    ctx.multiFuncs["atan2"] = [](const std::vector<double>& a) -> double {
        if (a.size() < 2) return 0.0;
        return std::atan2(a[0], a[1]);
    };
    // if(cond, a, b)：cond!=0 返回 a 否则 b
    ctx.multiFuncs["if"] = [](const std::vector<double>& a) -> double {
        if (a.size() < 3) return a.empty() ? 0.0 : a[0];
        return (a[0] != 0.0) ? a[1] : a[2];
    };
}

} // namespace rfsim
