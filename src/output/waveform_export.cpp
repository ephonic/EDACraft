// waveform_export.cpp — 波形多格式导出实现
//
// Phase D。详见 waveform_export.hpp。
#include "waveform_export.hpp"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>

namespace rfsim {

WaveFormat parseWaveFormat(const std::string& name) {
    std::string n = name;
    for (auto& c : n) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    if (n == "raw" || n == "rawfile") return WaveFormat::Rawfile;
    if (n == "json") return WaveFormat::Json;
    if (n == "all") return WaveFormat::All;
    return WaveFormat::Csv;  // csv / 未知 → Csv
}

const char* waveFormatName(WaveFormat f) {
    switch (f) {
        case WaveFormat::Csv:     return "csv";
        case WaveFormat::Rawfile: return "raw";
        case WaveFormat::Json:    return "json";
        case WaveFormat::All:     return "all";
    }
    return "csv";
}

std::vector<std::string> waveformSignalNames(const TimeDomainResult& w,
                                             const Circuit* c) {
    std::vector<std::string> names;
    names.reserve(w.numNodes + w.numBranches + 1);
    // 第一列：time
    names.emplace_back("time");
    // 节点电压
    for (uint32_t n = 1; n <= w.numNodes; ++n) {
        if (c && n <= c->nodes.size()) {
            names.push_back("v(" + c->nodes.nameOf(n) + ")");
        } else {
            names.push_back("v" + std::to_string(n));
        }
    }
    // 分支电流
    for (uint32_t b = 0; b < w.numBranches; ++b) {
        names.push_back("i" + std::to_string(b));
    }
    return names;
}

void writeWaveformCsv(std::ostream& os, const TimeDomainResult& w,
                      const std::vector<std::string>& signalNames,
                      const std::string& title) {
    (void)title;
    // 表头
    for (size_t k = 0; k < signalNames.size(); ++k) {
        if (k) os << ",";
        os << signalNames[k];
    }
    os << "\n";
    // 数据行：time + 每个 TimePoint.x（节点电压 + 分支电流）
    os.setf(std::ios::scientific);
    os.precision(10);
    for (const auto& tp : w.points) {
        os << tp.time;
        for (double xi : tp.x) os << "," << xi;
        os << "\n";
    }
    os.unsetf(std::ios::scientific);
}

void writeWaveformRawfile(std::ostream& os, const TimeDomainResult& w,
                          const std::vector<std::string>& signalNames,
                          const std::string& title,
                          const std::string& plotname) {
    // ngspice ASCII raw 格式：
    //   Title: ...
    //   Date: ...
    //   Plotname: ...
    //   Flags: real
    //   No. Variables: N
    //   No. Points: P
    //   Variables:
    //     0 time time
    //     1 v(n1) voltage
    //     ...
    //   Values:
    //     0  t0  x0_0 x0_1 ...
    //     ...
    const size_t numVars = signalNames.size();
    const size_t numPoints = w.points.size();
    os << "Title: " << (title.empty() ? "rfsim waveform" : title) << "\n";
    os << "Date: rfsim export\n";
    os << "Plotname: " << plotname << "\n";
    os << "Flags: real\n";
    os << "No. Variables: " << numVars << "\n";
    os << "No. Points: " << numPoints << "\n";
    os << "Variables:\n";
    for (size_t k = 0; k < numVars; ++k) {
        // 变量声明：序号 名称 类型
        const std::string& nm = signalNames[k];
        std::string type;
        if (k == 0) type = "time";
        else if (!nm.empty() && nm[0] == 'v') type = "voltage";
        else type = "current";
        os << "  " << k << " " << nm << " " << type << "\n";
    }
    os << "Values:\n";
    os.setf(std::ios::scientific);
    os.precision(12);
    for (size_t p = 0; p < numPoints; ++p) {
        const auto& tp = w.points[p];
        os << "  " << p << "  " << tp.time << "\n";
        // 后续每个变量的值（每行一个，缩进）；ngspice 实际允许同行，但分列更兼容
        for (size_t k = 1; k < numVars; ++k) {
            double xi = (k - 1 < tp.x.size()) ? tp.x[k - 1] : 0.0;
            os << "      " << xi << "\n";
        }
    }
    os.unsetf(std::ios::scientific);
}

void writeWaveformJson(std::ostream& os, const TimeDomainResult& w,
                       const std::vector<std::string>& signalNames,
                       const std::string& title) {
    // 紧凑 JSON：{ "title":..., "signals":[...], "points":[ {"t":..., "v":[...]}, ... ] }
    os << "{\n";
    os << "  \"title\": \"" << (title.empty() ? "rfsim waveform" : title) << "\",\n";
    os << "  \"signals\": [";
    for (size_t k = 0; k < signalNames.size(); ++k) {
        if (k) os << ", ";
        os << "\"" << signalNames[k] << "\"";
    }
    os << "],\n";
    os << "  \"points\": [\n";
    os.setf(std::ios::scientific);
    os.precision(10);
    for (size_t p = 0; p < w.points.size(); ++p) {
        const auto& tp = w.points[p];
        os << "    {\"t\": " << tp.time << ", \"v\": [";
        for (size_t k = 0; k < tp.x.size(); ++k) {
            if (k) os << ", ";
            os << tp.x[k];
        }
        os << "]}";
        if (p + 1 < w.points.size()) os << ",";
        os << "\n";
    }
    os.unsetf(std::ios::scientific);
    os << "  ]\n}\n";
}

std::vector<std::string> writeWaveformFile(const std::string& basePath,
                                           const std::string& suffix,
                                           WaveFormat format,
                                           const TimeDomainResult& w,
                                           const Circuit* c,
                                           const std::string& title,
                                           const std::string& plotname) {
    std::vector<std::string> written;
    const auto names = waveformSignalNames(w, c);
    auto writeOne = [&](WaveFormat f) {
        std::string ext;
        switch (f) {
            case WaveFormat::Csv:     ext = ".csv"; break;
            case WaveFormat::Rawfile: ext = ".raw"; break;
            case WaveFormat::Json:    ext = ".json"; break;
            default: return;
        }
        std::string path = basePath + suffix + ext;
        std::ofstream fOut(path);
        if (!fOut) return;
        switch (f) {
            case WaveFormat::Csv:     writeWaveformCsv(fOut, w, names, title); break;
            case WaveFormat::Rawfile: writeWaveformRawfile(fOut, w, names, title, plotname); break;
            case WaveFormat::Json:    writeWaveformJson(fOut, w, names, title); break;
            default: break;
        }
        written.push_back(path);
    };
    if (format == WaveFormat::All) {
        writeOne(WaveFormat::Csv);
        writeOne(WaveFormat::Rawfile);
        writeOne(WaveFormat::Json);
    } else {
        writeOne(format);
    }
    return written;
}

} // namespace rfsim
