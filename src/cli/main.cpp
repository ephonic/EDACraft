// cli/main.cpp 鈥?rfsim 鍛戒护琛屽叆鍙?//
// M1 闃舵锛氳В鏋愮綉琛紝鎵佸钩鍖栵紝鎵撳嵃缁撴瀯鍖栫數璺弿杩帮紙鑺傜偣/鍣ㄤ欢/妯″瀷/鎺у埗鍗★級銆?// 鐢ㄦ硶: rfsim <netlist.sp>
#include "../parser/parser.hpp"
#include "../parser/ast.hpp"
#include "../parser/expression.hpp"
#include "../parser/token.hpp"
#include "../circuit/flatten.hpp"
#include "../model/device_factory.hpp"
#include "../model/osdi_model.hpp"
#include "../model/builtin_devices.hpp"
#include "../solver/dc_op.hpp"
#include "../solver/dc_sweep.hpp"
#include "../solver/ac_analysis.hpp"
#include "../solver/hb_solver.hpp"
#include "../solver/hb_nonlinear.hpp"
#include "../solver/shooting.hpp"
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

int run(const std::string& path, const std::string& libSearchDir) {
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
    const rfsim::ControlCard* pssCard = nullptr;
    for (const auto& cc : c.controls) {
        if (cc.command == "op") hasOp = true;
        else if (cc.command == "dc") dcCard = &cc;
        else if (cc.command == "ac") acCard = &cc;
        else if (cc.command == "hb") hbCard = &cc;
        else if (cc.command == "pss") pssCard = &cc;
    }

    // 鑻ユ湁浠讳綍鍒嗘瀽锛屾瀯閫犲櫒浠?wrapper锛堝悇鍒嗘瀽鎸夐渶澶嶅埗鍓湰锛
    if (hasOp || dcCard || acCard || hbCard || pssCard) {
        rfsim::ParamEnv env;
        env.libSearchDir = libSearchDir;
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
            // 检测是否含非线性 OSDI 器件，决定是否走非线性 HB
            bool hasNonlinear = false;
            for (const auto& dev : fac.devices) {
                auto* om = dynamic_cast<rfsim::OsdiModel*>(dev.get());
                if (om && om->ready() && !om->is_linear()) { hasNonlinear = true; break; }
            }
            std::cout << "\n=== Harmonic Balance (f0=" << hbcfg.fundamental
                      << " Hz, NH=" << hbcfg.numHarmonics
                      << (hasNonlinear ? ", nonlinear" : ", linear") << ") ===\n";

            rfsim::HbResult hb;
            if (hasNonlinear) {
                // 1) 先尝试非线性 HB（弱非线性快路径）
                rfsim::HbNlOptions nlOpts;
                nlOpts.sourceSteps = 5;
                nlOpts.gmin.gmin = 1e-9;
                nlOpts.dvmax = 0.5;
                nlOpts.maxIter = 60;
                auto dcInit = rfsim::solveDcOp(fac.totalNodes, fac.devices);
                const std::vector<double>* dcPtr = dcInit.converged ? &dcInit.nodeVoltages : nullptr;
                auto hbnl = rfsim::solveHbNonlinear(fac.totalNodes, fac.devices, hbcfg, dcPtr, nlOpts);
                if (hbnl.converged) {
                    hb.config = hbcfg;
                    hb.nodeVoltages = hbnl.nodeVoltages;
                    hb.diags = hbnl.diags;
                    hb.ok = true;
                    std::cout << "  nonlinear HB converged in " << hbnl.iterations
                              << " iter, " << hbnl.continuationSteps << " continuation steps\n";
                } else {
                    // 2) 非线性 HB 不收敛 → 自动回退到 Shooting-PSS → FFT
                    std::cout << "  nonlinear HB did not converge; falling back to Shooting-PSS\n";
                    rfsim::ShootingConfig pssCfg;
                    pssCfg.fundamental = hbcfg.fundamental;
                    pssCfg.numTimePoints = std::max<uint32_t>(64u, 4u * (hbcfg.numHarmonics + 1));
                    pssCfg.method = rfsim::IntegrationMethod::BackwardEuler;
                    rfsim::ShootingOptions pssOpts;
                    pssOpts.maxIter = 15;
                    auto pss = rfsim::solveShooting(fac.totalNodes, fac.devices, pssCfg,
                                                    dcPtr, pssOpts);
                    if (pss.converged) {
                        hb = rfsim::shootingToHarmonics(pss, fac.totalNodes,
                                                       hbcfg.numHarmonics, hbcfg.fundamental);
                        std::cout << "  shooting-PSS converged in " << pss.iterations << " iter\n";
                    } else {
                        std::cerr << "  shooting-PSS also failed to converge\n";
                    }
                }
            } else {
                hb = rfsim::solveHbLinear(fac.totalNodes, fac.devices, hbcfg);
            }
            if (hb.ok) {
                rfsim::writeHb(std::cout, c, hb, true);
            } else {
                std::cerr << "HB analysis failed\n";
            }
        }

        // ---- .pss: 鍛ㄦ湡绋虫€佸垎鏋愶紙Shooting-Newton锛?----
        if (pssCard) {
            // .pss freq=<val> nh=<num> pts=<num>
            double f0 = 1e9;
            uint32_t nh = 5;
            uint32_t pts = 64;
            for (const auto& [pn, pv] : pssCard->params) {
                bool ok;
                if (pn == "freq" || pn == "f0" || pn == "f") {
                    if (pv.kind == rfsim::ParamValue::Kind::Number) f0 = pv.num;
                    else f0 = parseSpiceNumber(pv.str, ok);
                } else if (pn == "nh" || pn == "n") {
                    if (pv.kind == rfsim::ParamValue::Kind::Number) nh = static_cast<uint32_t>(pv.num);
                    else { double v = parseSpiceNumber(pv.str, ok); if (ok) nh = static_cast<uint32_t>(v); }
                } else if (pn == "pts" || pn == "tpts") {
                    if (pv.kind == rfsim::ParamValue::Kind::Number) pts = static_cast<uint32_t>(pv.num);
                    else { double v = parseSpiceNumber(pv.str, ok); if (ok) pts = static_cast<uint32_t>(v); }
                }
            }
            if (pts < 2u * (nh + 1)) pts = 2u * (nh + 1);
            std::cout << "\n=== Periodic Steady State (Shooting, f0=" << f0
                      << " Hz, NH=" << nh << ", pts=" << pts << ") ===\n";
            rfsim::ShootingConfig pssCfg;
            pssCfg.fundamental = f0;
            pssCfg.numTimePoints = pts;
            pssCfg.method = rfsim::IntegrationMethod::BackwardEuler;
            rfsim::ShootingOptions pssOpts;
            pssOpts.maxIter = 20;
            pssOpts.localNewtonDvMax = 0.3;
            auto dcInit = rfsim::solveDcOp(fac.totalNodes, fac.devices);
            std::vector<double> initFallback;
            const std::vector<double>* dcPtr = nullptr;
            if (dcInit.converged && dcInit.nodeVoltages.size() > fac.totalNodes) {
                dcPtr = &dcInit.nodeVoltages;
            } else {
                // DC 不收敛时，用电压源的 DC 直接给被强制节点赋值，其他节点取
                // 与之相连的电压源最接近值（简单启发：从所有 VS 取最大值作通用偏置）。
                initFallback.assign(fac.totalNodes + 1, 0.0);
                double maxVdd = 0.0;
                for (const auto& d : fac.devices) {
                    if (auto* vs = dynamic_cast<rfsim::VoltageSource*>(d.get())) {
                        if (vs->voltage() > maxVdd) maxVdd = vs->voltage();
                        rfsim::NodeId n1 = vs->nodes()[0];
                        rfsim::NodeId n2 = vs->nodes()[1];
                        // VS 连到地的节点直接强制
                        if (n1 != 0 && n2 == 0 && n1 <= fac.totalNodes) initFallback[n1] = vs->voltage();
                        if (n2 != 0 && n1 == 0 && n2 <= fac.totalNodes) initFallback[n2] = -vs->voltage();
                    }
                }
                // 其他节点（如 drain）默认取电源最高电压，更接近偏置而非 0
                for (size_t i = 1; i <= fac.totalNodes; ++i) {
                    if (initFallback[i] == 0.0) initFallback[i] = maxVdd;
                }
                dcPtr = &initFallback;
                std::cerr << "  warn: DC did not converge; using voltage-source-derived init"
                          << " (Vmax=" << maxVdd << ") for shooting\n";
            }
            auto pss = rfsim::solveShooting(fac.totalNodes, fac.devices, pssCfg, dcPtr, pssOpts);
            if (!pss.converged) {
                std::cerr << "PSS shooting did not converge after " << pss.iterations << " iter\n";
            } else {
                std::cout << "  shooting converged in " << pss.iterations << " iter\n";
            }
            // 即使未收敛也尽力 FFT 输出（只要波形有限），与单元测试语义保持一致：
            // 真实非线性网表常常需要后续手动检查或加倍 numTimePoints。
            bool finite = !pss.waveform.points.empty();
            for (const auto& tp : pss.waveform.points) {
                for (double xi : tp.x) {
                    if (!std::isfinite(xi)) { finite = false; break; }
                }
                if (!finite) break;
            }
            if (finite) {
                auto hb = rfsim::shootingToHarmonics(pss, fac.totalNodes, nh, f0);
                if (hb.ok) {
                    rfsim::writeHb(std::cout, c, hb, true);
                } else {
                    for (const auto& e : hb.diags.errors) std::cerr << "  " << e.message << "\n";
                }
            } else {
                std::cerr << "PSS waveform contains non-finite values; FFT skipped\n";
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
    std::string netlist;
    std::string libDir;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "-L" && i + 1 < argc) { libDir = argv[++i]; }
        else if (a.rfind("-L", 0) == 0 && a.size() > 2) { libDir = a.substr(2); }
        else if (a == "-h" || a == "--help") {
            std::cerr << "usage: rfsim [-L <osdi_lib_dir>] <netlist.sp>\n";
            return 0;
        }
        else if (netlist.empty()) { netlist = a; }
        else { std::cerr << "warn: extra arg ignored: " << a << "\n"; }
    }
    if (netlist.empty()) {
        std::cerr << "usage: rfsim [-L <osdi_lib_dir>] <netlist.sp>\n";
        return 1;
    }
    return run(netlist, libDir);
}

