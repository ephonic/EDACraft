// cli/main.cpp 鈥?rfsim 鍛戒护琛屽叆鍙?//
// M1 闃舵锛氳В鏋愮綉琛紝鎵佸钩鍖栵紝鎵撳嵃缁撴瀯鍖栫數璺弿杩帮紙鑺傜偣/鍣ㄤ欢/妯″瀷/鎺у埗鍗★級銆?// 鐢ㄦ硶: rfsim <netlist.sp>
#include "../parser/parser.hpp"
#include "../parser/ast.hpp"
#include "../parser/expression.hpp"
#include "../parser/token.hpp"
#include "../circuit/flatten.hpp"
#include "../model/device_factory.hpp"
#include "../solver/dc_op.hpp"
#include "../solver/dc_sweep.hpp"
#include "../solver/ac_analysis.hpp"
#include "../solver/hb_solver.hpp"
#include "../output/hspice_out.hpp"
#include "rfsim/rfsim_config.h"

#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
namespace {

// 解析数值参数（支持 SPICE 单位后缀如 100k, 1meg, 1u）
double parseSpiceNumber(const std::string& s, bool& ok) {
    double v = 0; size_t used = 0;
    ok = rfsim::Lexer::parseNumberLiteral(s, v, used);
    if (!ok || used == 0) { ok = false; return 0; }
    return v;
}

void printParamValue(const rfsim::ParamValue& v) {
    using K = rfsim::ParamValue::Kind;
    switch (v.kind) {
        case K::Number: std::cout << v.num; break;
        case K::String: std::cout << '"' << v.str << '"'; break;
        case K::Expr:   std::cout << v.str; break;
    }
}

int run(const std::string& path) {
    std::ifstream f(path);
    if (!f) {
        std::cerr << "error: cannot open file: " << path << "\n";
        return 1;
    }
    std::stringstream ss; ss << f.rdbuf();

    auto pr = rfsim::parseNetlist(ss.str(), path);
    if (pr.hasErrors()) {
        std::cerr << "parse errors (" << pr.diags.errors.size() << "):\n";
        for (const auto& e : pr.diags.errors) {
            std::cerr << "  " << e.loc.file << ":" << e.loc.line << ": " << e.message << "\n";
        }
        // 缁х画鎵撳嵃宸茶В鏋愬唴瀹逛互渚胯皟璇
    }

    std::cout << "rfsim v" << RFSIM_VERSION_STRING << "\n";
    std::cout << "netlist title: " << (pr.netlist.title.empty() ? "(none)" : pr.netlist.title) << "\n";
    std::cout << "parsed items (AST): " << pr.netlist.items.size() << "\n";

    auto fr = rfsim::flatten(pr.netlist);
    if (!fr.ok) {
        std::cerr << "flatten errors (" << fr.diags.errors.size() << "):\n";
        for (const auto& e : fr.diags.errors) {
            std::cerr << "  " << e.loc.file << ":" << e.loc.line << ": " << e.message << "\n";
        }
    }

    const auto& c = fr.circuit;
    std::cout << "\n=== Flattened Circuit ===\n";
    std::cout << "nodes (excl. gnd): " << c.nodes.size() << "\n";
    std::cout << "devices: " << c.devices.size() << "\n";
    std::cout << "models:  " << c.models.size() << "\n";
    std::cout << "control cards: " << c.controls.size() << "\n";

    std::cout << "\n--- Nodes ---\n";
    for (rfsim::NodeId i = 1; i <= c.nodes.size(); ++i) {
        std::cout << "  [" << i << "] " << c.nodes.nameOf(i) << "\n";
    }

    std::cout << "\n--- Devices ---\n";
    for (const auto& d : c.devices) {
        std::cout << "  " << d.name << " (" << d.firstLetter << ")";
        std::cout << " nodes=[";
        for (size_t i = 0; i < d.nodes.size(); ++i) {
            if (i) std::cout << ",";
            std::cout << d.nodes[i];
        }
        std::cout << "]";
        if (!d.model.empty()) std::cout << " model=" << d.model;
        for (const auto& [pn, pv] : d.params) {
            std::cout << " " << pn << "="; printParamValue(pv);
        }
        for (const auto& pv : d.positional) {
            std::cout << " "; printParamValue(pv);
        }
        std::cout << "\n";
    }

    std::cout << "\n--- Models ---\n";
    for (const auto& m : c.models) {
        std::cout << "  " << m.name << " (" << m.type << ")";
        for (const auto& [pn, pv] : m.params) {
            std::cout << " " << pn << "="; printParamValue(pv);
        }
        std::cout << "\n";
    }

    std::cout << "\n--- Control Cards ---\n";
    for (const auto& cc : c.controls) {
        std::cout << "  ." << cc.command;
        for (const auto& a : cc.args) std::cout << " " << a;
        for (const auto& [pn, pv] : cc.params) {
            std::cout << " " << pn << "="; printParamValue(pv);
        }
        std::cout << "\n";
    }

    // 妫€娴嬪垎鏋愭帶鍒跺崱
    bool hasOp = false;
    const rfsim::ControlCard* dcCard = nullptr;
    const rfsim::ControlCard* acCard = nullptr;
    const rfsim::ControlCard* hbCard = nullptr;
    for (const auto& cc : c.controls) {
        if (cc.command == "op") hasOp = true;
        else if (cc.command == "dc") dcCard = &cc;
        else if (cc.command == "ac") acCard = &cc;
        else if (cc.command == "hb") hbCard = &cc;
    }

    // 鑻ユ湁浠讳綍鍒嗘瀽锛屾瀯閫犲櫒浠?wrapper锛堝悇鍒嗘瀽鎸夐渶澶嶅埗鍓湰锛
    if (hasOp || dcCard || acCard || hbCard) {
        rfsim::ParamEnv env;
        auto fac = rfsim::buildDeviceModels(c, env);
        for (const auto& e : fac.diags.errors) {
            std::cerr << "  " << e.loc.file << ":" << e.loc.line << ": " << e.message << "\n";
        }
        for (const auto& w : fac.diags.warnings) {
            std::cerr << "  warn " << w.loc.file << ":" << w.loc.line << ": " << w.message << "\n";
        }

        // ---- .op: DC 宸ヤ綔鐐?----
        if (hasOp) {
            std::cout << "\n=== DC Operating Point ===\n";
            auto dc = rfsim::solveDcOp(fac.totalNodes, fac.devices);
            if (!dc.converged) {
                std::cerr << "DC did not converge after " << dc.iterations << " iterations\n";
                for (const auto& e : dc.diags.errors) std::cerr << "  " << e.message << "\n";
                for (const auto& w : dc.diags.warnings) std::cerr << "  warn: " << w.message << "\n";
            } else {
                std::cout << "converged in " << dc.iterations << " iteration(s)\n\n--- Node Voltages ---\n";
                std::cout.setf(std::ios::fixed); std::cout.precision(6);
                for (rfsim::NodeId i = 1; i <= c.nodes.size(); ++i) {
                    std::cout << "  v(" << c.nodes.nameOf(i) << ") = " << dc.nodeVoltages[i] << " V\n";
                }
                uint32_t vsIdx = 0;
                for (const auto& d : fac.devices) {
                    if (!d->name().empty() && d->name()[0] == 'v' && vsIdx < dc.branchCurrents.size()) {
                        std::cout << "  i(" << d->name() << ") = " << dc.branchCurrents[vsIdx] << " A\n";
                        ++vsIdx;
                    }
                }
            }
        }

        // ---- .dc: 鎵弿 ----
        if (dcCard) {
            // .dc <src> <start> <stop> <step>
            if (dcCard->args.size() >= 4) {
                rfsim::DcSweepSpec spec;
                bool ok1, ok2, ok3;
                spec.sourceName = dcCard->args[0];
                spec.start = parseSpiceNumber(dcCard->args[1], ok1);
                spec.stop  = parseSpiceNumber(dcCard->args[2], ok2);
                spec.step  = parseSpiceNumber(dcCard->args[3], ok3);
                if (!(ok1 && ok2 && ok3)) {
                    std::cerr << ".dc: bad numeric args\n";
                } else {
                    std::cout << "\n=== DC Sweep (" << spec.sourceName << " "
                              << spec.start << "->" << spec.stop << " step " << spec.step << ") ===\n";
                    auto sw = rfsim::solveDcSweep(fac.totalNodes, fac.devices, spec);
                    if (sw.ok) {
                        std::cout << "points: " << sw.points.size() << "\n";
                        std::cout.setf(std::ios::fixed); std::cout.precision(6);
                        for (const auto& p : sw.points) {
                            std::cout << "  " << spec.sourceName << "=" << p.sweepValue;
                            for (rfsim::NodeId i = 1; i <= c.nodes.size(); ++i) {
                                std::cout << "  v(" << c.nodes.nameOf(i) << ")=" << p.nodeVoltages[i];
                            }
                            std::cout << "\n";
                        }
                    } else {
                        std::cerr << "DC sweep failed\n";
                    }
                }
            } else {
                std::cerr << ".dc needs <src> <start> <stop> <step>\n";
            }
        }

        // ---- .ac: 灏忎俊鍙烽鍝?----
        if (acCard) {
            // .ac <DEC|LIN> <pts> <fstart> <fstop>
            if (acCard->args.size() >= 4) {
                rfsim::AcSpec spec;
                std::string mode = acCard->args[0];
                bool okPts, okF1, okF2;
                int pts = static_cast<int>(parseSpiceNumber(acCard->args[1], okPts));
                double f1 = parseSpiceNumber(acCard->args[2], okF1);
                double f2 = parseSpiceNumber(acCard->args[3], okF2);
                if (!(okPts && okF1 && okF2)) {
                    std::cerr << ".ac: bad numeric args\n";
                } else {
                    spec.startFreq = f1; spec.stopFreq = f2;
                    if (mode == "dec" || mode == "DEC") {
                        spec.sweep = rfsim::AcSpec::Sweep::Dec;
                        spec.pointsPerDecade = pts;
                    } else {
                        spec.sweep = rfsim::AcSpec::Sweep::Lin;
                        spec.pointsPerDecade = pts;
                    }
                    std::cout << "\n=== AC Analysis (" << mode << " " << pts
                              << " " << f1 << " " << f2 << " Hz) ===\n";
                    auto ac = rfsim::solveAc(fac.totalNodes, fac.devices, spec);
                    if (ac.ok) {
                        std::cout << "freq(Hz)";
                        for (rfsim::NodeId i = 1; i <= c.nodes.size(); ++i)
                            std::cout << "  |v(" << c.nodes.nameOf(i) << ")|  phase(deg)";
                        std::cout << "\n";
                        std::cout.setf(std::ios::fixed); std::cout.precision(4);
                        for (const auto& p : ac.points) {
                            std::cout << p.freq;
                            for (rfsim::NodeId i = 1; i <= c.nodes.size(); ++i) {
                                double mag = std::abs(p.nodeVoltages[i]);
                                double ph = std::arg(p.nodeVoltages[i]) * 180.0 / 3.14159265358979323846;
                                std::cout << "  " << mag << "  " << ph;
                            }
                            std::cout << "\n";
                        }
                    } else {
                        std::cerr << "AC analysis failed\n";
                    }
                }
            } else {
                std::cerr << ".ac needs <DEC|LIN> <pts> <fstart> <fstop>\n";
            }
        }

        // ---- .hb: 璋愭尝骞宠　 ----
        if (hbCard) {
            // .hb freq=<val> nh=<num>
            rfsim::HbConfig hbcfg;
            hbcfg.fundamental = 1e9;
            hbcfg.numHarmonics = 5;
            for (const auto& [pn, pv] : hbCard->params) {
                bool ok;
                if (pn == "freq" || pn == "f0" || pn == "f") {
                    hbcfg.fundamental = parseSpiceNumber(pv.str, ok);
                    if (pv.kind == rfsim::ParamValue::Kind::Number) hbcfg.fundamental = pv.num;
                } else if (pn == "nh" || pn == "n") {
                    int n = 5;
                    if (pv.kind == rfsim::ParamValue::Kind::Number) n = static_cast<int>(pv.num);
                    else { double v = parseSpiceNumber(pv.str, ok); if (ok) n = static_cast<int>(v); }
                    hbcfg.numHarmonics = static_cast<uint32_t>(n);
                }
            }
            std::cout << "\n=== Harmonic Balance (f0=" << hbcfg.fundamental
                      << " Hz, NH=" << hbcfg.numHarmonics << ") ===\n";
            auto hb = rfsim::solveHbLinear(fac.totalNodes, fac.devices, hbcfg);
            if (hb.ok) {
                rfsim::writeHb(std::cout, c, hb, true);
            } else {
                std::cerr << "HB analysis failed\n";
            }
        }

        // ---- 鍐?.lis 鍒楄〃鏂囦欢 ----
        {
            // 鐢ㄧ綉琛ㄨ矾寰勬淳鐢?.lis 鏂囦欢鍚
            std::string basePath = path;
            size_t dot = basePath.find_last_of('.');
            if (dot != std::string::npos) basePath = basePath.substr(0, dot);
            std::string lisPath = basePath + ".lis";
            std::ofstream lisf(lisPath);
            if (lisf) {
                // 璇诲洖婧愮爜锛堢畝鍖栵細鏍囬 + 鎻愮ず锛
                rfsim::writeBanner(lisf);
                lisf << "$ netlist: " << c.title << "\n$ source: " << path << "\n\n";
                rfsim::writeNodeTable(lisf, c);
                std::cout << "\nlisting written to: " << lisPath << "\n";
            }
        }
    }


    return (pr.hasErrors() || !fr.ok) ? 2 : 0;
}

} // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: rfsim <netlist.sp>\n";
        return 1;
    }
    return run(argv[1]);
}

