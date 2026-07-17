// measure.cpp — .measure 测量指令求值实现
//
// 详见 measure.hpp。支持 tran 分析的 max/min/pp/avg/rms/when/delay。
#include "measure.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>

namespace rfsim {

namespace {

// 把信号表达式 "v(out)" / "v(3)" / "i(v1)" 解析为波形列索引。
// time 是列 0；v(node) 是 1..numNodes；i(branch) 是 numNodes+1..
// 返回 {列索引, 信号名}；未找到返回 {SIZE_MAX, ""}。
struct SignalRef { size_t col; std::string name; };
SignalRef resolveSignal(const std::string& expr, const TimeDomainResult& wave,
                        const Circuit& circuit) {
    // expr 形如 "v(out)" / "v(3)" / "i(0)" / "all"
    // 去空格，小写化首字母
    std::string s = expr;
    // 去引号
    if (!s.empty() && s.front() == '\'') s.erase(0, 1);
    if (!s.empty() && s.back() == '\'') s.pop_back();
    // v(name) 或 v(id)
    if (s.size() > 2 && (s[0] == 'v' || s[0] == 'V') && s[1] == '(' && s.back() == ')') {
        std::string inner = s.substr(2, s.size() - 3);
        // 数字 → NodeId 直接
        bool isNum = !inner.empty();
        for (char c : inner) if (!std::isdigit(static_cast<unsigned char>(c))) { isNum = false; break; }
        if (isNum) {
            uint32_t nid = static_cast<uint32_t>(std::stoul(inner));
            // tp.x 索引：0..numNodes-1 = 节点电压（NodeId 1..numNodes），numNodes.. = 分支
            if (nid >= 1 && nid <= wave.numNodes) return {nid - 1, s};
        } else {
            NodeId nid = circuit.nodes.lookup(inner);
            if (nid != 0xFFFFFFFFu && nid >= 1 && nid <= wave.numNodes)
                return {nid - 1, s};
        }
    }
    // i(branch) — 分支电流
    if (s.size() > 2 && (s[0] == 'i' || s[0] == 'I') && s[1] == '(' && s.back() == ')') {
        std::string inner = s.substr(2, s.size() - 3);
        bool isNum = !inner.empty();
        for (char c : inner) if (!std::isdigit(static_cast<unsigned char>(c))) { isNum = false; break; }
        if (isNum) {
            uint32_t bid = static_cast<uint32_t>(std::stoul(inner));
            if (bid < wave.numBranches) return {wave.numNodes + bid, s};
        }
    }
    return {SIZE_MAX, ""};
}

// 取某信号在时间窗口 [t1,t2] 内的值序列（time + value 对）
std::vector<std::pair<double, double>> extractSeries(const TimeDomainResult& wave,
                                                      size_t col, double t1, double t2) {
    std::vector<std::pair<double, double>> s;
    for (const auto& tp : wave.points) {
        if (tp.time < t1 - 1e-15 || tp.time > t2 + 1e-15) continue;
        double v = (col < tp.x.size()) ? tp.x[col] : 0.0;
        s.emplace_back(tp.time, v);
    }
    return s;
}

// 线性插值求 v=target 的时刻（在 (t0,v0)-(t1,v1) 段内）
double interpCross(double t0, double v0, double t1, double v1, double target) {
    if (std::fabs(v1 - v0) < 1e-300) return t0;
    return t0 + (target - v0) / (v1 - v0) * (t1 - t0);
}

} // namespace

MeasureResult evaluateMeasureTran(const ControlCard& card,
                                  const TimeDomainResult& wave,
                                  const Circuit& circuit) {
    MeasureResult r;
    r.analysis = "tran";
    // .measure tran <name> <type> <signal-expr> [from= t1 to= t2] [val= / rise= / ...]
    // args: [0]=tran [1]=name [2]=type ...
    if (card.args.size() < 3) {
        r.message = "too few args (need: tran <name> <type> <signal>)";
        return r;
    }
    r.name = card.args[1];
    r.type = card.args[2];
    // signal expr 重构：parser 把 "v(out)" 拆成 args: ["v","(","out",")"]，
    // 且 "when v(out)=0.5" 的 "=0.5" 可能被 parseParamPairs 吞。
    // 从 args[3] 起拼接所有后续 token（去空格）。
    std::string sigExpr;
    for (size_t i = 3; i < card.args.size(); ++i) sigExpr += card.args[i];
    // 去空格
    std::string clean;
    for (char ch : sigExpr) if (ch != ' ') clean += ch;
    sigExpr = clean;
    // 对 when 类型：参数里可能有 val=0.5 等；signal expr 可能含 "=..."，去掉
    // （when 的 target 值在 params 的 val=/target= 里，或 args 里的 =val 被吞到 params）
    size_t eqPos = sigExpr.find('=');
    if (eqPos != std::string::npos) sigExpr = sigExpr.substr(0, eqPos);
    // 确保括号闭合（parser 可能丢了 ')'）
    int paren = 0;
    for (char ch : sigExpr) { if (ch == '(') ++paren; else if (ch == ')') --paren; }
    while (paren > 0) { sigExpr += ')'; --paren; }
    // 时间窗口
    double t1 = 0.0, t2 = 1e30;
    for (const auto& [pn, pv] : card.params) {
        bool ok;
        if (pn == "from" || pn == "t1") t1 = std::stod(pv.str.empty() ? std::to_string(pv.num) : pv.str);
        if (pn == "to" || pn == "t2") t2 = std::stod(pv.str.empty() ? std::to_string(pv.num) : pv.str);
        (void)ok;
    }

    // when/delay 需要信号；max/min/pp/avg/rms 也需要信号
    auto sref = resolveSignal(sigExpr, wave, circuit);
    if (sref.col == SIZE_MAX && r.type != "delay") {
        r.message = "cannot resolve signal '" + sigExpr + "'";
        return r;
    }
    auto series = (sref.col != SIZE_MAX) ? extractSeries(wave, sref.col, t1, t2)
                                         : std::vector<std::pair<double,double>>{};

    if (r.type == "max") {
        if (series.empty()) { r.message = "no data in window"; return r; }
        double m = series[0].second;
        for (auto& p : series) m = std::max(m, p.second);
        r.value = m; r.ok = true;
    } else if (r.type == "min") {
        if (series.empty()) { r.message = "no data in window"; return r; }
        double m = series[0].second;
        for (auto& p : series) m = std::min(m, p.second);
        r.value = m; r.ok = true;
    } else if (r.type == "pp" || r.type == "peak-to-peak") {
        if (series.empty()) { r.message = "no data in window"; return r; }
        double mx = series[0].second, mn = series[0].second;
        for (auto& p : series) { mx = std::max(mx, p.second); mn = std::min(mn, p.second); }
        r.value = mx - mn; r.ok = true;
    } else if (r.type == "avg" || r.type == "average") {
        if (series.empty()) { r.message = "no data in window"; return r; }
        // 梯形积分 / 时间跨度
        double sum = 0, tspan = 0;
        for (size_t i = 1; i < series.size(); ++i) {
            double dt = series[i].first - series[i-1].first;
            sum += 0.5 * (series[i].second + series[i-1].second) * dt;
            tspan += dt;
        }
        r.value = (tspan > 0) ? sum / tspan : 0.0; r.ok = true;
    } else if (r.type == "rms") {
        if (series.empty()) { r.message = "no data in window"; return r; }
        double sum = 0, tspan = 0;
        for (size_t i = 1; i < series.size(); ++i) {
            double dt = series[i].first - series[i-1].first;
            double v0 = series[i].second, v1 = series[i-1].second;
            sum += 0.5 * (v0*v0 + v1*v1) * dt;
            tspan += dt;
        }
        r.value = (tspan > 0) ? std::sqrt(sum / tspan) : 0.0; r.ok = true;
    } else if (r.type == "when") {
        // when v(sig)=val [rise|fall|cross]=N
        double target = 0;
        bool hasTarget = false;
        int crossN = 1;  // 默认第 1 次
        bool riseOnly = false, fallOnly = false;
        for (const auto& [pn, pv] : card.params) {
            if (pn == "val" || pn == "target") { target = pv.num; hasTarget = true; }
            if (pn == "rise") { riseOnly = true; crossN = static_cast<int>(pv.num); }
            if (pn == "fall") { fallOnly = true; crossN = static_cast<int>(pv.num); }
            if (pn == "cross") { crossN = static_cast<int>(pv.num); }
            // parser 把 "v(out)=0.5" 当 name=val → pn 可能是 "v(out" 或 "v(out)"
            // 若 pn 含信号名（如 "v(out)"）→ pv.num 是 target
            if (!hasTarget && pv.kind == ParamValue::Kind::Number &&
                pn.find("v(") == 0) { target = pv.num; hasTarget = true; }
            // 兜底：任何非关键字且非 from/to 的数值参数 → target
            if (!hasTarget && pv.kind == ParamValue::Kind::Number &&
                pn != "from" && pn != "to" && pn != "t1" && pn != "t2" &&
                pn != "rise" && pn != "fall" && pn != "cross" && pn != "td") {
                target = pv.num; hasTarget = true;
            }
        }
        if (!hasTarget) { r.message = "when needs val="; return r; }
        int found = 0;
        for (size_t i = 1; i < series.size(); ++i) {
            double v0 = series[i-1].second, v1 = series[i].second;
            bool crossedUp = (v0 <= target && v1 > target);
            bool crossedDn = (v0 >= target && v1 < target);
            if ((riseOnly && !crossedUp) || (fallOnly && !crossedDn)) continue;
            if (crossedUp || crossedDn) {
                ++found;
                if (found == crossN) {
                    r.value = interpCross(series[i-1].first, v0, series[i].first, v1, target);
                    r.ok = true;
                    return r;
                }
            }
        }
        r.message = "target crossing not found";
    } else if (r.type == "delay" || r.type == "trig" || r.type == "targ") {
        // delay: trig v(a)=va targ v(b)=vb [rise/fall on each]
        // 简化：单 trig+targ，各找首次穿越
        std::string trigSig, targSig;
        double trigVal = 0, targVal = 0;
        bool trigRise = false, trigFall = false, targRise = false, targFall = false;
        bool haveTrig = false, haveTarg = false;
        for (const auto& [pn, pv] : card.params) {
            if (pn == "trig") { trigSig = pv.str; haveTrig = true; }
            else if (pn == "targ") { targSig = pv.str; haveTarg = true; }
            else if (pn == "trigval") trigVal = pv.num;
            else if (pn == "targval") targVal = pv.num;
            else if (pn == "trigrise") trigRise = true;
            else if (pn == "trigfall") trigFall = true;
            else if (pn == "targrise") targRise = true;
            else if (pn == "targfall") targFall = true;
        }
        if (!haveTrig || !haveTarg) { r.message = "delay needs trig= and targ="; return r; }
        auto findCross = [&](const std::string& sigExpr, double target, bool riseOnly, bool fallOnly,
                             double& tOut) -> bool {
            auto sref2 = resolveSignal(sigExpr, wave, circuit);
            if (sref2.col == SIZE_MAX) return false;
            auto s2 = extractSeries(wave, sref2.col, t1, t2);
            for (size_t i = 1; i < s2.size(); ++i) {
                double v0 = s2[i-1].second, v1 = s2[i].second;
                bool up = (v0 <= target && v1 > target);
                bool dn = (v0 >= target && v1 < target);
                if ((riseOnly && !up) || (fallOnly && !dn)) continue;
                if (up || dn) { tOut = interpCross(s2[i-1].first, v0, s2[i].first, v1, target); return true; }
            }
            return false;
        };
        double tTrig = 0, tTarg = 0;
        if (!findCross(trigSig, trigVal, trigRise, trigFall, tTrig)) {
            r.message = "trig crossing not found"; return r;
        }
        if (!findCross(targSig, targVal, targRise, targFall, tTarg)) {
            r.message = "targ crossing not found"; return r;
        }
        r.value = tTarg - tTrig; r.ok = true;
    } else {
        r.message = "unsupported measure type '" + r.type + "'";
    }
    return r;
}

std::vector<MeasureResult> evaluateAllMeasures(
    const std::vector<ControlCard>& controls,
    const TimeDomainResult& wave,
    const Circuit& circuit,
    std::ostream& os) {
    std::vector<MeasureResult> results;
    for (const auto& cc : controls) {
        if (cc.command != "measure") continue;
        if (cc.args.empty() || cc.args[0] != "tran") {
            os << ".measure: only tran analysis supported (got '" 
               << (cc.args.empty() ? "" : cc.args[0]) << "')\n";
            continue;
        }
        MeasureResult r = evaluateMeasureTran(cc, wave, circuit);
        results.push_back(r);
        os << "  " << r.name << " (" << r.type << ") = ";
        if (r.ok) {
            os.setf(std::ios::scientific); os.precision(8);
            os << r.value;
            os.unsetf(std::ios::scientific);
        } else {
            os << "FAILED (" << r.message << ")";
        }
        os << "\n";
    }
    return results;
}

} // namespace rfsim
