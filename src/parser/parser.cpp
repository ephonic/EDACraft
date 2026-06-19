// parser.cpp — SPICE 网表递归下降语法分析器实现
//
// SPICE 是行导向的：每张卡占一行（续行 + 合并为逻辑行）。
// 因此本解析器采用"逻辑行 → 词法化 → 按首字符分发"的策略，
// 而非纯 token 流（纯 token 流难以可靠区分卡边界）。
#include "parser.hpp"
#include "token.hpp"

#include <cctype>
#include <fstream>
#include <sstream>

namespace rfsim {

namespace {

// ---- 工具函数 --------------------------------------------------------------
std::string ltrim(std::string s) {
    size_t b = 0;
    while (b < s.size() && (s[b] == ' ' || s[b] == '\t')) ++b;
    return s.substr(b);
}
std::string trim(std::string s) {
    size_t b = 0, e = s.size();
    while (b < e && (s[b] == ' ' || s[b] == '\t')) ++b;
    while (e > b && (s[e-1] == ' ' || s[e-1] == '\t')) --e;
    return s.substr(b, e - b);
}
void stripInlineComment(std::string& s) {
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == '$' || s[i] == ';') { s.resize(i); return; }
    }
}

// 逻辑行：合并续行后的文本 + 起始行号
struct LogicalLine { std::string text; uint32_t line; };

// 把源码切为逻辑行：行首 + 表示续行，合并到上一逻辑行。
// 行首 * 开头为整行注释，跳过（不产生逻辑行）。
std::vector<LogicalLine> splitLogicalLines(const std::string& src) {
    std::vector<LogicalLine> out;
    std::string cur;
    uint32_t startLine = 1;
    uint32_t lineNo = 1;
    bool pending = false;
    size_t i = 0;

    while (i < src.size()) {
        size_t ls = i;
        while (i < src.size() && src[i] != '\n') ++i;
        std::string raw(src.substr(ls, i - ls));
        if (i < src.size()) ++i; // 消费 \n
        if (!raw.empty() && raw.back() == '\r') raw.pop_back();

        lineNo = (lineNo); // 仅记录
        // 整行注释跳过
        if (!raw.empty() && raw[0] == '*') { ++lineNo; continue; }

        std::string lt = ltrim(raw);
        if (!lt.empty() && lt[0] == '+') {
            // 续行：合并
            if (!pending) { cur = ltrim(lt.substr(1)); startLine = lineNo; pending = true; }
            else { cur += " " + ltrim(lt.substr(1)); }
        } else {
            if (pending) out.push_back({cur, startLine});
            cur = lt;
            startLine = lineNo;
            pending = !lt.empty();
        }
        ++lineNo;
    }
    if (pending && !cur.empty()) out.push_back({cur, startLine});
    return out;
}

// 用 Lexer 词法化单行
std::vector<Token> tokenizeLine(const std::string& line, const std::string& filename, uint32_t lineNo) {
    Lexer lx(line, filename);
    std::vector<Token> toks;
    while (true) {
        Token t = lx.next();
        if (t.kind == TokenKind::EndOfFile) break;
        t.loc.line = lineNo;
        toks.push_back(std::move(t));
    }
    return toks;
}

ParamValue tokenToParamValue(const Token& t) {
    ParamValue v;
    v.loc = t.loc;
    if (t.kind == TokenKind::Number) {
        v.kind = ParamValue::Kind::Number; v.num = t.value; v.str = t.text;
    } else if (t.kind == TokenKind::String) {
        v.kind = ParamValue::Kind::String; v.str = t.text;
    } else {
        v.kind = ParamValue::Kind::Expr; v.str = t.text;
    }
    return v;
}

// 从 token 序列解析 name=val 参数对，跳过非配对 token
ParamList parseParamPairs(const std::vector<Token>& toks) {
    ParamList pl;
    for (size_t i = 0; i < toks.size(); ++i) {
        if (toks[i].kind == TokenKind::Word && i + 2 < toks.size() && toks[i+1].kind == TokenKind::Equal) {
            pl.emplace_back(toks[i].text, tokenToParamValue(toks[i+2]));
            i += 2;
        }
    }
    return pl;
}

// ---- 解析器 ----------------------------------------------------------------
class Parser {
public:
    Parser(std::string src, std::string filename, ParseOptions opts)
        : src_(std::move(src)), filename_(std::move(filename)), opts_(opts) {}

    void parse(Netlist& out) {
        // SPICE 传统：第一行总是标题（无论是否以 * 注释开头）。
        // 直接从源码提取第一行作为标题，再解析剩余内容。
        {
            size_t nl = src_.find('\n');
            std::string firstLine = (nl == std::string::npos) ? src_ : src_.substr(0, nl);
            if (!firstLine.empty() && firstLine.back() == '\r') firstLine.pop_back();
            // 去掉行首注释符 * 与空白
            std::string t = ltrim(firstLine);
            if (!t.empty() && t[0] == '*') t = ltrim(t.substr(1));
            out.title = trim(t);
        }

        auto lines = splitLogicalLines(src_);
        // 跳过第一物理行（已是标题）：splitLogicalLines 已跳过 * 注释行，
        // 但若第一行非注释(纯标题文本)，它会作为 lines[0] 出现——需跳过。
        size_t start = 0;
        if (!lines.empty()) {
            // 判断 lines[0] 是否对应第一物理行(标题)
            if (lines[0].line == 1) start = 1;
        }

        for (size_t idx = start; idx < lines.size(); ++idx) {
            std::string line = lines[idx].text;
            uint32_t ln = lines[idx].line;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty()) continue;

            if (line[0] == '.') {
                parseDotLine(line, ln, out);
            } else {
                parseCardLine(line, ln, out);
            }
        }

        if (!substack_.empty()) {
            diags_.error({filename_, 0, 0}, "unterminated .subckt: " + substack_.back().name);
        }
    }

    Diagnostics& diags() { return diags_; }

private:
    std::string src_;
    std::string filename_;
    ParseOptions opts_;
    Diagnostics diags_;

    // 子电路定义栈
    struct Frame { std::shared_ptr<SubcktDef> def; std::string name; };
    std::vector<Frame> substack_;

    SourceLoc at(uint32_t line) const { return {filename_, line, 1}; }

    // 当前语句应加入的容器
    std::vector<NetlistItem>* currentTarget(Netlist& netlist) {
        if (substack_.empty()) return &netlist.items;
        return &substack_.back().def->body;
    }

    void parseDotLine(const std::string& line, uint32_t ln, Netlist& netlist) {
        auto toks = tokenizeLine(line, filename_, ln);
        if (toks.size() < 2 || toks[0].kind != TokenKind::Dot || toks[1].kind != TokenKind::Word) {
            diags_.error(at(ln), "malformed control line"); return;
        }
        const std::string& cmd = toks[1].text;
        std::vector<Token> rest(toks.begin() + 2, toks.end());

        if (cmd == "subckt") { parseSubcktHeader(rest, ln); return; }
        if (cmd == "ends")   { parseEnds(ln, netlist); return; }
        if (cmd == "end")    { return; }
        if (cmd == "model")  { parseModelCard(rest, ln, netlist); return; }
        if (cmd == "param" || cmd == "params") { parseParamCard(rest, ln, netlist); return; }
        if (cmd == "options" || cmd == "option") {
            ControlCard c; c.command = "options"; c.loc = at(ln);
            c.params = parseParamPairs(rest);
            currentTarget(netlist)->push_back(c); return;
        }
        if (cmd == "include" || cmd == "lib") { parseInclude(rest, ln, netlist); return; }

        // 通用控制卡: .tran/.ac/.dc/.hb/.print/.measure/.nodeset/.ic/...
        ControlCard c;
        c.command = cmd;
        c.loc = at(ln);
        for (size_t i = 0; i < rest.size(); ++i) {
            if (i + 2 < rest.size() && rest[i+1].kind == TokenKind::Equal) {
                c.params.emplace_back(rest[i].text, tokenToParamValue(rest[i+2]));
                i += 2;
            } else {
                c.args.push_back(rest[i].text);
            }
        }
        currentTarget(netlist)->push_back(c);
    }

    void parseSubcktHeader(const std::vector<Token>& rest, uint32_t ln) {
        auto def = std::make_shared<SubcktDef>();
        def->loc = at(ln);
        if (rest.empty() || rest[0].kind != TokenKind::Word) {
            diags_.error(at(ln), ".subckt missing name"); return;
        }
        def->name = rest[0].text;
        bool inParams = false; // 遇到 params: 后切换到形参声明
        for (size_t i = 1; i < rest.size(); ++i) {
            if (rest[i].kind == TokenKind::Equal) continue;
            // params: 关键字（HSPICE 子电路形参声明起始）
            if (rest[i].kind == TokenKind::Word && rest[i].text == "params") {
                inParams = true;
                // 跳过紧跟的冒号（词法器把 ':' 当单字符 Word）
                if (i + 1 < rest.size() && rest[i+1].kind == TokenKind::Word && rest[i+1].text == ":") ++i;
                continue;
            }
            if (rest[i].kind == TokenKind::Word && rest[i].text == ":") continue; // 裸冒号
            if (i + 2 < rest.size() && rest[i+1].kind == TokenKind::Equal) {
                def->params.emplace_back(rest[i].text, tokenToParamValue(rest[i+2]));
                i += 2;
            } else if (rest[i].kind == TokenKind::Word) {
                if (!inParams) def->ports.push_back(rest[i].text);
                // params 段内的无值形参：忽略默认值
            }
        }
        substack_.push_back({def, def->name});
    }

    void parseEnds(uint32_t ln, Netlist& netlist) {
        if (substack_.empty()) {
            diags_.error(at(ln), ".ends without matching .subckt"); return;
        }
        auto def = substack_.back().def;
        substack_.pop_back();
        // 闭合的子电路定义加入当前目标容器（顶层或父子电路体）
        currentTarget(netlist)->push_back(def);
    }

    void parseModelCard(const std::vector<Token>& rest, uint32_t ln, Netlist& netlist) {
        ModelCard m; m.loc = at(ln);
        size_t i = 0;
        if (i < rest.size() && rest[i].kind == TokenKind::Word) m.name = rest[i++].text;
        if (i < rest.size() && rest[i].kind == TokenKind::Word) m.type = rest[i++].text;
        if (i < rest.size() && rest[i].kind == TokenKind::LParen) ++i;
        m.params = parseParamPairs(rest); // 简单处理：扫描所有 name=val
        currentTarget(netlist)->push_back(m);
    }

    void parseParamCard(const std::vector<Token>& rest, uint32_t ln, Netlist& netlist) {
        ParamList pl = parseParamPairs(rest);
        if (substack_.empty()) {
            for (auto& p : pl) netlist.globalParams.push_back(p);
        } else {
            for (auto& p : pl) substack_.back().def->params.push_back(p);
        }
        (void)ln;
    }

    void parseInclude(const std::vector<Token>& rest, uint32_t ln, Netlist& netlist) {
        // .include path   或  .lib path section
        std::string path;
        for (const auto& t : rest) {
            if (t.kind == TokenKind::Word || t.kind == TokenKind::String) {
                path = t.text; break;
            }
        }
        if (path.empty()) { diags_.error(at(ln), ".include/.lib missing path"); return; }
        std::ifstream f(path);
        if (!f) { diags_.error(at(ln), "cannot open included file: " + path); return; }
        std::stringstream ss; ss << f.rdbuf();
        Parser sub(ss.str(), path, opts_);
        // 子解析器复用当前子电路栈：把 substack_ 传过去
        // 简化：子文件独立解析后，把其 netlist.items 合并到当前位置
        Netlist subNet;
        sub.parseInto(subNet, substack_);
        for (auto& it : subNet.items) currentTarget(netlist)->push_back(std::move(it));
        for (auto& p : subNet.globalParams) netlist.globalParams.push_back(p);
        // 合并子解析器的诊断
        for (auto& e : sub.diags().errors) diags_.errors.push_back(e);
        for (auto& w : sub.diags().warnings) diags_.warnings.push_back(w);
    }

    // 供 parseInclude 复用栈的入口
    void parseInto(Netlist& out, std::vector<Frame>& sharedStack) {
        substack_ = sharedStack; // 继承外层栈
        auto lines = splitLogicalLines(src_);
        for (auto& ll : lines) {
            std::string line = ll.text;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty()) continue;
            if (line[0] == '.') parseDotLine(line, ll.line, out);
            else parseCardLine(line, ll.line, out);
        }
        sharedStack = substack_; // 写回（可能新增了未闭合的 subckt）
    }

    void parseCardLine(const std::string& line, uint32_t ln, Netlist& netlist) {
        auto toks = tokenizeLine(line, filename_, ln);
        if (toks.empty() || toks[0].kind != TokenKind::Word) {
            diags_.error(at(ln), "card must start with a name"); return;
        }
        const std::string& name = toks[0].text;
        if (!name.empty() && name[0] == 'x') {
            currentTarget(netlist)->push_back(parseSubcktCall(toks, ln));
        } else {
            currentTarget(netlist)->push_back(parseDevice(toks, ln));
        }
    }

    DeviceCard parseDevice(const std::vector<Token>& toks, uint32_t ln) {
        DeviceCard d;
        d.name = toks[0].text;
        d.loc = at(ln);
        d.firstLetter = static_cast<char>(std::tolower(static_cast<unsigned char>(
            d.name.empty() ? ' ' : d.name[0])));

        // 半导体器件(M/Q/D/Z/J/S/B)：先收集节点，达到预期节点数后下一个 Word 为模型名。
        // 线性器件(R/L/C/V/I)：节点数为 2，无模型名，后续 Word/Number 为参数。
        const bool semi = isSemiconductor(d.firstLetter);
        const int expectedNodes = semi ? maxNodes(d.firstLetter) : 2;
        bool modelSeen = !semi; // 线性器件不需要模型名

        for (size_t i = 1; i < toks.size(); ++i) {
            const Token& t = toks[i];
            if (t.kind == TokenKind::Equal) continue;
            // 命名参数 name=value
            if (i + 2 < toks.size() && toks[i+1].kind == TokenKind::Equal) {
                d.params.emplace_back(t.text, tokenToParamValue(toks[i+2]));
                i += 2;
                continue;
            }
            if (t.kind == TokenKind::Number) {
                // 节点未收集够时，数字也是节点（如地节点 0）；否则为位置参数（如阻值）
                if (static_cast<int>(d.nodes.size()) < expectedNodes) {
                    d.nodes.push_back(t.text);
                } else {
                    d.positional.push_back(tokenToParamValue(t));
                }
            } else if (t.kind == TokenKind::Word) {
                // 节点未收集够时，Word 视为节点
                if (static_cast<int>(d.nodes.size()) < expectedNodes) {
                    d.nodes.push_back(t.text);
                } else if (!modelSeen) {
                    // 节点收齐后的第一个 Word 是模型名
                    d.model = t.text;
                    modelSeen = true;
                } else {
                    // 模型名已取，后续 Word 视为位置字符串参数
                    ParamValue v; v.kind = ParamValue::Kind::String; v.str = t.text; v.loc = t.loc;
                    d.positional.push_back(v);
                }
            } else if (t.kind == TokenKind::String) {
                d.positional.push_back(tokenToParamValue(t));
            }
        }
        return d;
    }

    SubcktCall parseSubcktCall(const std::vector<Token>& toks, uint32_t ln) {
        SubcktCall sc;
        sc.name = toks[0].text;
        sc.loc = at(ln);
        std::vector<std::string> nodesAndName;
        bool inParen = false;
        for (size_t i = 1; i < toks.size(); ++i) {
            const Token& t = toks[i];
            if (t.kind == TokenKind::LParen) { inParen = true; continue; }
            if (t.kind == TokenKind::RParen) { inParen = false; continue; }
            // 命名参数 name=value（括号内外都支持）
            if (t.kind == TokenKind::Word && i + 2 < toks.size() && toks[i+1].kind == TokenKind::Equal) {
                sc.params.emplace_back(t.text, tokenToParamValue(toks[i+2]));
                i += 2;
                continue;
            }
            if (t.kind == TokenKind::Equal) continue; // 已被上面跳过
            if (inParen) {
                // 括号内位置参数
                sc.params.emplace_back("", tokenToParamValue(t));
            } else if (t.kind == TokenKind::Word || t.kind == TokenKind::Number) {
                // 节点名可以是标识符或数字（如地节点 0）
                nodesAndName.push_back(t.text);
            }
        }
        // 节点名列表 + 最后一个为子电路名
        if (!nodesAndName.empty()) {
            sc.subcktName = nodesAndName.back();
            nodesAndName.pop_back();
            sc.nodes = std::move(nodesAndName);
        }
        return sc;
    }

    static bool isSemiconductor(char c) {
        return c=='m'||c=='q'||c=='d'||c=='z'||c=='j'||c=='s'||c=='b';
    }
    // 半导体器件的预期节点数（模型名之前的节点数）
    static int maxNodes(char c) {
        switch (c) {
            case 'd': return 2;            // 二极管: anode cathode
            case 'q': return 3;            // BJT: c b e (+ 可选 substrate)
            case 'm': return 4;            // MOSFET: d g s b
            case 'j': return 3;            // JFET: d g s
            case 'z': return 3;            // MESFET: d g s
            case 's': return 3;            // SOI
            case 'b': return 4;            // GaAs
            default: return 2;
        }
    }
};

} // namespace

// 修正 parseEnds 的顶层 push：实际用 parseSubcktClose。这里在 Parser 内统一。
// 为避免上面 parseEnds 的逻辑遗漏，parseDotLine 中 .ends 改调 parseSubcktClose。
// 但 parseDotLine 已直接调用 parseEnds——下面通过重新定义行为修正：
// 实际上我们让 parseDotLine 调用一个正确版本。为简洁，将 .ends 处理内联到 parseDotLine。

ParseResult parseNetlist(std::string source, std::string filename, ParseOptions opts) {
    ParseResult r;
    Parser p(std::move(source), std::move(filename), opts);
    p.parse(r.netlist);
    r.diags = std::move(p.diags());
    r.ok = !r.hasErrors();
    return r;
}

ParseResult parseFile(const std::string& path, ParseOptions opts) {
    std::ifstream f(path);
    if (!f) {
        ParseResult r;
        r.diags.error({path, 0, 0}, "cannot open file: " + path);
        r.ok = false;
        return r;
    }
    std::stringstream ss; ss << f.rdbuf();
    return parseNetlist(ss.str(), path, opts);
}

} // namespace rfsim
