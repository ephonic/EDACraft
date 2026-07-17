// hspice_out.cpp — HSPICE 兼容输出实现
#include "hspice_out.hpp"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace rfsim {

namespace {

const double PI = 3.14159265358979323846;

void hdr(std::ostream& os, const std::string& title) {
    os << "$rfsim ============================================================\n";
    os << "$  " << title << "\n";
    os << "$rfsim ============================================================\n\n";
}

} // namespace

void writeBanner(std::ostream& os) {
    os << "****** rfsim RF simulator ******\n";
    os << "****** harmonic balance + osdi ******\n";
    os << "****** version 0.2 ******\n\n";
}

void writeNetlistEcho(std::ostream& os, const std::string& title, const std::string& source) {
    hdr(os, "netlist: " + title);
    os << source << "\n\n";
}

void writeNodeTable(std::ostream& os, const Circuit& c) {
    hdr(os, "node table");
    os << "  nodes (excl. gnd): " << c.nodes.size() << "\n";
    for (NodeId i = 1; i <= c.nodes.size(); ++i) {
        os << "  [" << i << "] " << c.nodes.nameOf(i) << "\n";
    }
    os << "\n";
}

void writeDcOp(std::ostream& os, const Circuit& c, const DcOpResult& r) {
    hdr(os, "operating point (dc)");
    if (!r.converged) {
        os << "  ** NOT CONVERGED **\n\n";
        return;
    }
    os << "  converged in " << r.iterations << " iteration(s)\n\n";
    os << "  node         voltage\n";
    os << "  ----         -------\n";
    os.setf(std::ios::fixed);
    for (NodeId i = 1; i <= c.nodes.size(); ++i) {
        os << "  " << std::left << std::setw(12) << c.nodes.nameOf(i)
           << std::right << std::setw(12) << std::setprecision(6) << r.nodeVoltages[i] << "\n";
    }
    if (!r.branchCurrents.empty()) {
        os << "\n  voltage source currents\n";
        os << "  source       current\n";
        uint32_t k = 0;
        for (const auto& d : c.devices) {
            if (!d.name.empty() && d.name[0] == 'v' && k < r.branchCurrents.size()) {
                os << "  " << std::left << std::setw(12) << d.name
                   << std::right << std::setw(12) << std::setprecision(6)
                   << r.branchCurrents[k] << "\n";
                ++k;
            }
        }
    }
    os << "\n";
}

void writeDcSweep(std::ostream& os, const Circuit& c, const DcSweepResult& r) {
    hdr(os, "dc sweep: " + r.sweepSourceName);
    if (!r.ok) { os << "  ** FAILED **\n\n"; return; }
    // .print 风格表头
    os << "  " << std::left << std::setw(14) << r.sweepSourceName;
    for (NodeId i = 1; i <= c.nodes.size(); ++i) {
        os << std::setw(16) << ("v(" + c.nodes.nameOf(i) + ")");
    }
    os << "\n";
    os.setf(std::ios::scientific);
    for (const auto& p : r.points) {
        os << "  " << std::setw(14) << std::setprecision(6) << p.sweepValue;
        for (NodeId i = 1; i <= c.nodes.size(); ++i) {
            os << std::setw(16) << std::setprecision(6) << p.nodeVoltages[i];
        }
        os << "\n";
    }
    os.unsetf(std::ios::scientific);
    os << "\n";
}

void writeAc(std::ostream& os, const Circuit& c, const AcResult& r) {
    hdr(os, "ac analysis");
    if (!r.ok) { os << "  ** FAILED **\n\n"; return; }
    os << "  " << std::left << std::setw(14) << "freq";
    for (NodeId i = 1; i <= c.nodes.size(); ++i) {
        std::string n = "v(" + c.nodes.nameOf(i) + ")";
        os << std::setw(14) << n;
        os << std::setw(12) << (n + ".ph");
    }
    os << "\n";
    os.setf(std::ios::scientific);
    for (const auto& p : r.points) {
        os << "  " << std::setw(14) << std::setprecision(6) << p.freq;
        for (NodeId i = 1; i <= c.nodes.size(); ++i) {
            Complex v = p.nodeVoltages[i];
            double mag = std::abs(v);
            double phase = std::arg(v) * 180.0 / PI;
            os << std::setw(14) << std::setprecision(6) << mag;
            os << std::setw(12) << std::setprecision(4) << phase;
        }
        os << "\n";
    }
    os.unsetf(std::ios::scientific);
    os << "\n";
}

void writeHb(std::ostream& os, const Circuit& c, const HbResult& r, bool includeWaveform) {
    hdr(os, "harmonic balance");
    if (!r.ok) { os << "  ** FAILED **\n\n"; return; }
    os << "  fundamental: " << r.config.fundamental << " Hz\n";
    os << "  harmonics: 0.." << r.config.numHarmonics << "\n\n";

    // 谐波幅度/相位表
    os << "  harmonic   ";
    for (NodeId i = 1; i <= c.nodes.size(); ++i) {
        os << std::setw(14) << ("|v(" + c.nodes.nameOf(i) + ")|");
        os << std::setw(12) << ("ph(deg)");
    }
    os << "\n";
    os.setf(std::ios::scientific);
    for (uint32_t k = 0; k <= r.config.numHarmonics; ++k) {
        double freq = k * r.config.fundamental;
        os << "  " << std::left << std::setw(4) << k
           << std::right << std::setw(10) << std::setprecision(3) << freq;
        for (NodeId i = 1; i <= c.nodes.size(); ++i) {
            Complex v = (i < r.nodeVoltages.size() && k < r.nodeVoltages[i].v.size())
                        ? r.nodeVoltages[i].v[k] : Complex(0,0);
            os << std::setw(14) << std::setprecision(6) << std::abs(v);
            os << std::setw(12) << std::setprecision(4) << (std::arg(v) * 180.0 / PI);
        }
        os << "\n";
    }
    os.unsetf(std::ios::scientific);

    // 时域波形（每节点一个周期）
    if (includeWaveform) {
        os << "\n  time-domain waveform (one period):\n";
        uint32_t N = 2 * (r.config.numHarmonics + 1);
        double T = 1.0 / r.config.fundamental;
        os << "  " << std::left << std::setw(12) << "time";
        for (NodeId i = 1; i <= c.nodes.size(); ++i) {
            os << std::setw(14) << ("v(" + c.nodes.nameOf(i) + ")");
        }
        os << "\n";
        for (uint32_t t = 0; t < N; ++t) {
            double tm = T * t / N;
            os << "  " << std::setw(12) << std::setprecision(6) << tm;
            for (NodeId i = 1; i <= c.nodes.size(); ++i) {
                if (i < r.nodeVoltages.size()) {
                    auto wave = nodeHarmonicsToWaveform(r.nodeVoltages[i], r.config.numHarmonics);
                    os << std::setw(14) << std::setprecision(6) << (t < wave.size() ? wave[t] : 0.0);
                } else {
                    os << std::setw(14) << 0.0;
                }
            }
            os << "\n";
        }
    }
    os << "\n";
}

void writeListing(const std::string& path, const Circuit& c, const std::string& source) {
    std::ofstream f(path);
    if (!f) return;
    writeBanner(f);
    writeNetlistEcho(f, c.title, source);
    writeNodeTable(f, c);
}

} // namespace rfsim
