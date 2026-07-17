// parser.cpp — SPICE 网表递归下降语法分析器实现
//
// SPICE 是行导向的：每张卡占一行（续行 + 合并为逻辑行）。
// 因此本解析器采用"逻辑行 → 词法化 → 按首字符分发"的策略，
// 而非纯 token 流（纯 token 流难以可靠区分卡边界）。
#include "parser.hpp"
#include "token.hpp"

#include <cctype>
#include <fstream>
#include <map>
#include <set>
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

        std::vector<std::string> topLevelBlockStack;  // C1：顶层 .lib NAME 块栈
        for (size_t idx = start; idx < lines.size(); ++idx) {
            std::string line = lines[idx].text;
            uint32_t ln = lines[idx].line;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty()) continue;

            // C1：顶层也支持 .lib NAME...endl 块记录（与 parseBodyInto 一致）。
            // 块定义行不直接 parseDotLine（会误入 parseLibSelect）；块内行归档。
            std::string low = line;
            for (auto& c : low) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            bool isLibStart = (low.size() > 5 && low.substr(0, 5) == ".lib ");
            bool isEndl = (low.size() > 5 && low.substr(0, 5) == ".endl");
            if (isLibStart) {
                auto toks = tokenizeLine(line, filename_, ln);
                std::string firstArg; bool isPath = false;
                for (size_t ti = 2; ti < toks.size(); ++ti) {
                    if (toks[ti].kind == TokenKind::String) { firstArg = toks[ti].text; isPath = true; break; }
                    if (toks[ti].kind == TokenKind::Word) { firstArg = toks[ti].text; break; }
                }
                if (!isPath && !firstArg.empty() &&
                    (firstArg.find('.') != std::string::npos || firstArg.find('/') != std::string::npos ||
                     firstArg.find('\\') != std::string::npos)) isPath = true;
                if (isPath) {
                    parseDotLine(line, ln, out);  // 跨文件 .lib "path" CORNER
                } else if (!firstArg.empty()) {
                    std::string blkName = firstArg;
                    for (auto& c : blkName) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                    topLevelBlockStack.push_back(blkName);
                    libBlocks_[blkName];
                }
                continue;
            }
            if (isEndl) {
                if (!topLevelBlockStack.empty()) topLevelBlockStack.pop_back();
                continue;
            }
            if (!topLevelBlockStack.empty()) {
                libBlocks_[topLevelBlockStack.back()].emplace_back(line, ln);
                continue;
            }

            if (line[0] == '.') {
                parseDotLine(line, ln, out);
            } else {
                parseCardLine(line, ln, out);
            }
        }

        if (!substack_.empty()) {
            diags_.error({filename_, 0, 0}, "unterminated .subckt: " + substack_.back().name);
        }
        // 展开顶层被选择的本地块（顶层 .lib NAME 块若被注入 libSelectSet_）
        for (const auto& selName : libSelectSet_) {
            auto it = libBlocks_.find(selName);
            if (it == libBlocks_.end()) continue;
            for (auto& [text, lno] : it->second) {
                if (text[0] == '.') parseDotLine(text, lno, out);
                else parseCardLine(text, lno, out);
            }
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

    // C1：.lib NAME ... .endl NAME 命名块记录。
    // libBlocks_[name] = 块内的逻辑行序列（已 strip 注释/trim）。
    // activeLibBlock_：当前正在记录的块名（空表示不在记录态，正常处理）。
    // libSelectSet_：本 Parser 实例应激活的 corner 名集合（由 .lib "path" CORNER 注入）。
    // libLoadingFiles_：当前正在加载的 .lib 文件绝对路径集合（防递归 .lib 自引用）。
    std::map<std::string, std::vector<std::pair<std::string, uint32_t>>> libBlocks_;
    std::string activeLibBlock_;
    std::set<std::string> libSelectSet_;
    std::set<std::string> libLoadingFiles_;

    // C1：.lib 文件缓存。key = 规范化文件路径，value = 该文件解析后的
    // {outOfBlockLines（块外行）, blocks（块名→块内行）}。同文件只解析一次，
    // 后续 .lib 引用（含自引用）从缓存取块。这是 HSPICE PDK 自引用嵌套的关键。
    struct LibFileCache {
        std::vector<std::pair<std::string, uint32_t>> outOfBlockLines;
        std::map<std::string, std::vector<std::pair<std::string, uint32_t>>> blocks;
    };
    static std::map<std::string, LibFileCache>& libFileCache() {
        static std::map<std::string, LibFileCache> cache;
        return cache;
    }

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
        if (cmd == "include") { parseInclude(rest, ln, netlist); return; }
        if (cmd == "lib")     { parseLibSelect(rest, ln, netlist); return; }

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

    // C1：解析路径——优先相对于当前文件所在目录（HSPICE 语义），再相对 CWD。
    // 例如 toplevel.l 里的 `.lib './crn28.l' X`，'./crn28.l' 应相对 toplevel.l 的目录，
    // 而非进程 CWD。返回能打开的绝对/相对路径；都打不开返回原始 path（让后续报错）。
    std::string resolveLibPath(const std::string& path) const {
        // 已是绝对路径或能直接打开 → 原样
        std::ifstream testDirect(path);
        if (testDirect) return path;
        // 相对当前文件目录
        if (!filename_.empty()) {
            size_t slash = filename_.find_last_of("\\/");
            std::string dir = (slash != std::string::npos) ? filename_.substr(0, slash) : ".";
            std::string rel = dir + "/" + path;
            std::ifstream testRel(rel);
            if (testRel) return rel;
        }
        return path;  // 打不开，返回原样让 parseInclude/parseLibSelect 报错
    }

    void parseInclude(const std::vector<Token>& rest, uint32_t ln, Netlist& netlist) {
        std::string path;
        for (const auto& t : rest) {
            if (t.kind == TokenKind::String) { path = t.text; break; }  // 引号路径优先
            if (t.kind == TokenKind::Word) { path = t.text; break; }
        }
        // 若 path 不含 '.'（tokenizer 把 .inc 拆开了），拼接后续 token
        if (path.find('.') == std::string::npos) {
            for (const auto& t : rest) {
                if (t.kind == TokenKind::Dot) { path += "."; }
                else if (t.kind == TokenKind::Word && path != t.text) { path += t.text; }
            }
        }
        if (path.empty()) { diags_.error(at(ln), ".include/.lib missing path"); return; }
        path = resolveLibPath(path);  // C1：相对当前文件目录解析
        std::ifstream f(path);
        if (!f) { diags_.error(at(ln), "cannot open included file: " + path); return; }
        std::stringstream ss; ss << f.rdbuf();
        Parser sub(ss.str(), path, opts_);
        // 子解析器复用当前子电路栈：把 substack_ 传过去
        // 简化：子文件独立解析后，把其 netlist.items 合并到当前位置
        Netlist subNet;
        // .include 文件不应跳第一行当标题——直接从第一行开始解析
        sub.parseBodyInto(subNet, substack_);
        for (auto& it : subNet.items) currentTarget(netlist)->push_back(std::move(it));
        for (auto& p : subNet.globalParams) netlist.globalParams.push_back(p);
        // 合并子解析器的诊断
        for (auto& e : sub.diags().errors) diags_.errors.push_back(e);
        for (auto& w : sub.diags().warnings) diags_.warnings.push_back(w);
    }

    // 把一个 .lib 文件解析一次到缓存（块外行 + 各命名块）。同文件只解析一次。
    // 解析用临时 Parser，复用 splitLogicalLines 的块边界识别逻辑，但不做块展开
    // （只记录块定义）。返回缓存条目引用（若文件无法打开返回 nullptr）。
    const LibFileCache* loadLibFileToCache(const std::string& path) {
        std::string normPath = path;
        for (auto& c : normPath) if (c == '\\') c = '/';
        auto& cache = libFileCache();
        auto it = cache.find(normPath);
        if (it != cache.end()) return &it->second;
        std::ifstream f(path);
        if (!f) return nullptr;
        std::stringstream ss; ss << f.rdbuf();
        std::string src = ss.str();
        // 临时解析器：仅做块边界识别，填充 cache 条目
        LibFileCache entry;
        auto lines = splitLogicalLines(src);
        std::vector<std::string> blockStack;
        for (auto& ll : lines) {
            std::string line = ll.text;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty() || line[0] == '*') continue;
            std::string low = line;
            for (auto& c : low) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            bool isLibStart = (low.size() > 5 && low.substr(0, 5) == ".lib ");
            bool isEndl = (low.size() > 5 && low.substr(0, 5) == ".endl");
            if (isLibStart) {
                auto toks = tokenizeLine(line, path, ll.line);
                std::string firstArg; bool isPath = false;
                for (size_t ti = 2; ti < toks.size(); ++ti) {
                    if (toks[ti].kind == TokenKind::String) { firstArg = toks[ti].text; isPath = true; break; }
                    if (toks[ti].kind == TokenKind::Word) { firstArg = toks[ti].text; break; }
                }
                if (!isPath && !firstArg.empty() &&
                    (firstArg.find('.') != std::string::npos || firstArg.find('/') != std::string::npos ||
                     firstArg.find('\\') != std::string::npos)) isPath = true;
                if (isPath) {
                    // 跨文件 .lib：作为块外行记录（展开时由调用方处理）
                    if (blockStack.empty()) entry.outOfBlockLines.emplace_back(line, ll.line);
                    else entry.blocks[blockStack.back()].emplace_back(line, ll.line);
                } else if (!firstArg.empty()) {
                    std::string blk = firstArg;
                    for (auto& c : blk) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                    blockStack.push_back(blk);
                    entry.blocks[blk];
                }
                continue;
            }
            if (isEndl) {
                if (!blockStack.empty()) blockStack.pop_back();
                continue;
            }
            if (blockStack.empty()) entry.outOfBlockLines.emplace_back(line, ll.line);
            else entry.blocks[blockStack.back()].emplace_back(line, ll.line);
        }
        auto inserted = cache.emplace(normPath, std::move(entry));
        return &inserted.first->second;
    }

    // C1：.lib "path" CORNER —— 从文件缓存取 CORNER 块（或块外行）展开。
    // 文件只解析一次（缓存）；自引用 .lib 'samefile' BLOCK 从已缓存块取，不重载。
    void parseLibSelect(const std::vector<Token>& rest, uint32_t ln, Netlist& netlist) {
        std::string path;
        std::string corner;
        bool gotPath = false;
        for (const auto& t : rest) {
            if (!gotPath) {
                if (t.kind == TokenKind::String) { path = t.text; gotPath = true; continue; }
                if (t.kind == TokenKind::Word) { path = t.text; gotPath = true; continue; }
                if (t.kind == TokenKind::Dot) { path += "."; gotPath = true; continue; }
            } else {
                if (t.kind == TokenKind::Word) { corner = t.text; break; }
                if (t.kind == TokenKind::String) { corner = t.text; break; }
            }
        }
        if (path.find('.') == std::string::npos && !gotPath) {
            for (const auto& t : rest) {
                if (t.kind == TokenKind::Dot) { path += "."; gotPath = true; }
                else if (t.kind == TokenKind::Word && path != t.text) { path += t.text; gotPath = true; }
            }
        }
        if (path.empty()) { diags_.error(at(ln), ".lib missing path"); return; }
        path = resolveLibPath(path);
        const LibFileCache* cached = loadLibFileToCache(path);
        if (!cached) { diags_.error(at(ln), "cannot open .lib file: " + path); return; }
        // 选 corner（小写归一）；缺省则展开块外行
        std::string cl = corner;
        for (auto& c : cl) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        const std::vector<std::pair<std::string, uint32_t>>* linesToExpand = nullptr;
        if (!cl.empty()) {
            auto bit = cached->blocks.find(cl);
            if (bit != cached->blocks.end()) linesToExpand = &bit->second;
            else diags_.warn(at(ln), ".lib corner '" + corner + "' not found in " + path);
        } else {
            linesToExpand = &cached->outOfBlockLines;
        }
        if (!linesToExpand) return;
        // 展开选中行：用临时 Parser（filename=目标文件，便于其内部 .lib 路径解析）。
        // 子 Parser 继承 libLoadingFiles_（防无限递归）+ substack_（子电路作用域）。
        Parser sub("", path, opts_);
        sub.libLoadingFiles_ = libLoadingFiles_;
        sub.substack_ = substack_;
        Netlist subNet;
        // 把行直接喂给子 parser 的 dot/card 处理（不经 parseBodyInto 的块识别——
        // 这些行已是选中块内容，不需要再分块）。
        for (auto& [text, lno] : *linesToExpand) {
            if (text[0] == '.') sub.parseDotLine(text, lno, subNet);
            else sub.parseCardLine(text, lno, subNet);
        }
        for (auto& it : subNet.items) currentTarget(netlist)->push_back(std::move(it));
        for (auto& p : subNet.globalParams) netlist.globalParams.push_back(p);
        for (auto& e : sub.diags().errors) diags_.errors.push_back(e);
        for (auto& w : sub.diags().warnings) diags_.warnings.push_back(w);
    }

    // 供 parseInclude 复用栈的入口
    void parseInto(Netlist& out, std::vector<Frame>& sharedStack) {
        substack_ = sharedStack; // 继承外层栈
        auto lines = splitLogicalLines(src_);
        // 跳过第一行（标题）—— 仅顶层 netlist 需要
        for (size_t i = 1; i < lines.size(); ++i) {
            auto& ll = lines[i];
            std::string line = ll.text;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty()) continue;
            if (line[0] == '.') parseDotLine(line, ll.line, out);
            else parseCardLine(line, ll.line, out);
        }
        sharedStack = substack_; // 写回（可能新增了未闭合的 subckt）
    }

    // .include 用——不跳第一行，所有行都解析
    // C1：支持 .lib NAME ... .endl NAME 命名块（同文件定义）+ .lib "path" CORNER
    //     选择性包含另一文件的命名块。实现：单遍扫描，块定义存入 libBlocks_，
    //     .lib "path" CORNER 递归解析目标文件并展开其 CORNER 块。
    void parseBodyInto(Netlist& out, std::vector<Frame>& sharedStack) {
        substack_ = sharedStack;
        auto lines = splitLogicalLines(src_);
        // 第一遍：识别 .lib/.endl 块边界，把块内行归档，块外行标记为正常解析。
        // blockStack：嵌套的块名栈（.lib NAME 入栈，.endl NAME 出栈）。
        std::vector<std::string> blockStack;
        std::vector<std::pair<std::string, uint32_t>> inlineLines;  // 块外、需正常解析的行
        for (auto& ll : lines) {
            std::string line = ll.text;
            stripInlineComment(line);
            line = trim(line);
            if (line.empty()) continue;
            if (line[0] == '*') continue;
            // 判断是否 .lib/.endl 控制（不区分大小写）
            std::string low = line;
            for (auto& c : low) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            bool isLibStart = (low.size() > 5 && low.substr(0, 5) == ".lib ");
            bool isEndl = (low.size() > 5 && low.substr(0, 5) == ".endl");
            if (isLibStart) {
                // .lib 的两种语义：
                //   (a) .lib NAME  —— NAME 是标识符（非路径）→ 定义命名块开始
                //   (b) .lib "path" CORNER 或 .lib path CORNER —— 跨文件块选择
                // 区分：若第一个参数含 '.' 或 '/' 或被引号包裹 → 路径（语义 b）。
                auto toks = tokenizeLine(line, filename_, ll.line);
                // toks[0]='.', toks[1]='lib', 后续是参数
                std::string firstArg;
                bool isPath = false;
                for (size_t ti = 2; ti < toks.size(); ++ti) {
                    if (toks[ti].kind == TokenKind::String) { firstArg = toks[ti].text; isPath = true; break; }
                    if (toks[ti].kind == TokenKind::Word) { firstArg = toks[ti].text; break; }
                }
                if (!isPath && !firstArg.empty()) {
                    if (firstArg.find('.') != std::string::npos || firstArg.find('/') != std::string::npos ||
                        firstArg.find('\\') != std::string::npos) isPath = true;
                }
                if (isPath) {
                    // 语义 b：跨文件块选择——作为普通行交给 parseDotLine 处理（块外）
                    inlineLines.emplace_back(line, ll.line);
                } else if (!firstArg.empty()) {
                    // 语义 a：命名块开始（块名小写归一，与 libSelectSet_ 匹配）
                    std::string blkName = firstArg;
                    for (auto& c : blkName) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                    blockStack.push_back(blkName);
                    libBlocks_[blkName];  // 创建空条目
                }
                continue;
            }
            if (isEndl) {
                if (!blockStack.empty()) blockStack.pop_back();
                continue;
            }
            // 普通行：若在块内则归档到最内层块，否则标记正常解析
            if (!blockStack.empty()) {
                libBlocks_[blockStack.back()].emplace_back(line, ll.line);
            } else {
                inlineLines.emplace_back(line, ll.line);
            }
        }
        // 第二遍：解析块外行。.lib "path" CORNER 由 parseDotLine 触发块展开。
        for (auto& [text, lno] : inlineLines) {
            if (text[0] == '.') parseDotLine(text, lno, out);
            else parseCardLine(text, lno, out);
        }
        // 第三遍：展开本文件内被选择的本地块（libSelectSet_ 由 .lib "path" CORNER
        // 跨文件注入；本地 .lib NAME 块若在 libSelectSet_ 中也展开）。
        for (const auto& selName : libSelectSet_) {
            auto it = libBlocks_.find(selName);
            if (it == libBlocks_.end()) continue;
            for (auto& [text, lno] : it->second) {
                if (text[0] == '.') parseDotLine(text, lno, out);
                else parseCardLine(text, lno, out);
            }
        }
        sharedStack = substack_;
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
        // S 参数器件(K)：变长节点，收集到 file= 参数前都是节点
        const bool semi = isSemiconductor(d.firstLetter);
        const bool isSparam = (d.firstLetter == 'k');
        int expectedNodes = semi ? maxNodes(d.firstLetter) : 2;
        if (isSparam) expectedNodes = 999;  // 变长：收集到 file= 前都是节点
        bool modelSeen = !semi; // 线性器件不需要模型名

        for (size_t i = 1; i < toks.size(); ++i) {
            const Token& t = toks[i];
            if (t.kind == TokenKind::Equal) continue;
            // 命名参数 name=value
            if (i + 2 < toks.size() && toks[i+1].kind == TokenKind::Equal) {
                d.params.emplace_back(t.text, tokenToParamValue(toks[i+2]));
                i += 2;
                // S 参数器件遇到 file= 时停止收集节点
                if (isSparam && (t.text == "file" || t.text == "z0"))
                    expectedNodes = static_cast<int>(d.nodes.size());
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
