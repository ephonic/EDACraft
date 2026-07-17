// touchstone.cpp — Touchstone .sNp 文件解析实现
#include "touchstone.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace rfsim {

namespace {

// 解析频率单位 → 缩放因子
double freqScale(const std::string& unit) {
    if (unit == "hz" || unit == "Hz") return 1.0;
    if (unit == "khz" || unit == "kHz" || unit == "KHZ") return 1e3;
    if (unit == "mhz" || unit == "MHz" || unit == "MHZ") return 1e6;
    if (unit == "ghz" || unit == "GHz" || unit == "GHZ") return 1e9;
    return 1.0;
}

// 从数据格式转换到 Complex
Complex parseDataPoint(double a, double b, const std::string& fmt) {
    if (fmt == "RI") {
        return Complex(a, b);                    // Re, Im
    } else if (fmt == "MA") {
        return std::polar(a, b * M_PI / 180.0);   // 幅度, 角度(°)
    } else if (fmt == "DB") {
        return std::polar(std::pow(10.0, a / 20.0), b * M_PI / 180.0);  // dB, 角度(°)
    }
    return Complex(a, b);  // 默认 RI
}

// 从文件名推断端口数
uint32_t inferNumPorts(const std::string& path) {
    // 找 .sNp 后缀
    size_t pos = path.find_last_of('.');
    if (pos == std::string::npos) return 0;
    std::string ext = path.substr(pos + 1);
    // 转小写
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (ext.size() >= 3 && ext[0] == 's' && ext[ext.size()-1] == 'p') {
        std::string numStr = ext.substr(1, ext.size() - 2);
        try { return std::stoul(numStr); } catch (...) { return 0; }
    }
    return 0;
}

} // namespace

TouchstoneData parseTouchstone(const std::string& path) {
    TouchstoneData td;
    td.numPorts = inferNumPorts(path);
    if (td.numPorts == 0)
        throw std::runtime_error("cannot infer port count from file: " + path);

    std::ifstream f(path);
    if (!f)
        throw std::runtime_error("cannot open touchstone file: " + path);

    std::string line;
    std::string fmt = "RI";
    std::string funit = "GHz";
    double z0 = 50.0;

    // 解析 option line（# MHz S RI R 50）
    while (std::getline(f, line)) {
        // 跳过空行
        std::string trimmed = line;
        // 去首尾空格
        size_t start = trimmed.find_first_not_of(" \t");
        if (start == std::string::npos) continue;
        trimmed = trimmed.substr(start);

        // 注释行
        if (trimmed[0] == '!')
            continue;

        // Option line
        if (trimmed[0] == '#') {
            std::istringstream iss(trimmed.substr(1));
            std::string tok;
            while (iss >> tok) {
                // 转小写比较
                std::string tokLower = tok;
                std::transform(tokLower.begin(), tokLower.end(), tokLower.begin(), ::tolower);
                if (tokLower == "ghz" || tokLower == "mhz" || tokLower == "khz" || tokLower == "hz") {
                    funit = tokLower;
                } else if (tokLower == "ri" || tokLower == "ma" || tokLower == "db") {
                    fmt = tok;  // 保持原始大小写
                    std::transform(fmt.begin(), fmt.end(), fmt.begin(), ::toupper);
                } else if (tokLower == "r") {
                    // 下一个 token 是 Z0
                    iss >> z0;
                } else if (tokLower == "s") {
                    // S 参数类型标记
                }
                // 其他忽略（如 Y/Z/G/H 参数类型——当前只支持 S）
            }
            break;  // option line 之后开始数据
        }
        // 没有 option line——直接是数据
        break;
    }

    td.format = fmt;
    td.freqUnit = funit;
    td.refImpedance = z0;

    double fscale = freqScale(funit);
    uint32_t N = td.numPorts;
    uint32_t nS = N * N;

    // 重新打开文件，跳到 option line 之后
    f.clear();
    f.seekg(0);
    bool pastOption = false;

    while (std::getline(f, line)) {
        // 去首尾空格
        size_t start = line.find_first_not_of(" \t");
        if (start == std::string::npos) continue;
        std::string trimmed = line.substr(start);

        if (trimmed[0] == '!') continue;      // 注释
        if (trimmed[0] == '#') { pastOption = true; continue; }  // option line

        // 数据行：freq S11_re S11_im S21_re S21_im ...
        std::istringstream iss(trimmed);
        double freq;
        if (!(iss >> freq)) continue;

        std::vector<Complex> sRow(nS);
        bool ok = true;
        for (uint32_t i = 0; i < nS; ++i) {
            double a, b;
            if (!(iss >> a >> b)) { ok = false; break; }
            sRow[i] = parseDataPoint(a, b, fmt);
        }
        if (!ok) continue;

        // Touchstone 2 端口格式：S11 S21 S12 S22
        // 需要重新映射到矩阵存储（行优先）：S11 S12 S21 S22
        if (N == 2) {
            std::vector<Complex> reordered(4);
            reordered[0] = sRow[0];  // S11
            reordered[1] = sRow[2];  // S12
            reordered[2] = sRow[1];  // S21
            reordered[3] = sRow[3];  // S22
            sRow = reordered;
        }

        td.freqs.push_back(freq * fscale);  // 转换到 Hz
        td.S.push_back(std::move(sRow));
    }

    if (td.freqs.empty())
        throw std::runtime_error("no data points in touchstone file: " + path);

    return td;
}

std::vector<Complex> sToY(const std::vector<Complex>& S, uint32_t N, double Z0) {
    uint32_t n = N;
    // Y = (1/Z0) * (I - S)^{-1} * (I + S) * (1/Z0)
    // 即 (I - S) * Y * Z0 = (I + S) / Z0
    // 设 A = (I - S), B = (I + S) / Z0, 则 Y = A^{-1} * B

    // 构造 A = I - S
    std::vector<Complex> A(n * n), B(n * n);
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            A[i * n + j] = (i == j ? Complex(1, 0) : Complex(0, 0)) - S[i * n + j];
            B[i * n + j] = (i == j ? Complex(1, 0) : Complex(0, 0)) + S[i * n + j];
            B[i * n + j] /= Z0;
        }
    }

    // 解 A * Y = B（Gauss-Jordan 消元，复数）
    // 对 B 做 in-place 消元
    for (uint32_t col = 0; col < n; ++col) {
        // 找主元
        uint32_t piv = col;
        double maxAbs = std::abs(A[col * n + col]);
        for (uint32_t r = col + 1; r < n; ++r) {
            double a = std::abs(A[r * n + col]);
            if (a > maxAbs) { maxAbs = a; piv = r; }
        }
        if (maxAbs < 1e-15) {
            // 奇异矩阵——返回零
            return std::vector<Complex>(n * n, Complex(0, 0));
        }
        // 交换行
        if (piv != col) {
            for (uint32_t j = 0; j < n; ++j) {
                std::swap(A[col * n + j], A[piv * n + j]);
                std::swap(B[col * n + j], B[piv * n + j]);
            }
        }
        // 归一化主元行
        Complex pivot = A[col * n + col];
        for (uint32_t j = 0; j < n; ++j) {
            A[col * n + j] /= pivot;
            B[col * n + j] /= pivot;
        }
        // 消元其他行
        for (uint32_t r = 0; r < n; ++r) {
            if (r == col) continue;
            Complex factor = A[r * n + col];
            if (std::abs(factor) < 1e-15) continue;
            for (uint32_t j = 0; j < n; ++j) {
                A[r * n + j] -= factor * A[col * n + j];
                B[r * n + j] -= factor * B[col * n + j];
            }
        }
    }

    // B 此时是 Y（还需要除以 Z0，因为 Y = (1/Z0) * A^{-1} * (I+S) / Z0... 不对
    // 正确公式：Y = (I - S)^{-1} * (I + S) * (1/Z0)
    // 即 Y = A^{-1} * B，其中 B = (I+S)/Z0
    // Gauss-Jordan 后 B = A^{-1} * B = Y
    return B;
}

std::vector<Complex> interpolateS(const TouchstoneData& td, double freq) {
    uint32_t N = td.numPorts;
    uint32_t nS = N * N;
    std::vector<Complex> result(nS, Complex(0, 0));

    if (td.freqs.empty()) return result;

    // 频率在范围外——用端点值
    if (freq <= td.freqs.front()) {
        result = td.S.front();
        return result;
    }
    if (freq >= td.freqs.back()) {
        result = td.S.back();
        return result;
    }

    // 二分查找
    auto it = std::lower_bound(td.freqs.begin(), td.freqs.end(), freq);
    size_t hi = static_cast<size_t>(it - td.freqs.begin());
    size_t lo = hi - 1;

    double f0 = td.freqs[lo], f1 = td.freqs[hi];
    double t = (freq - f0) / (f1 - f0);  // 插值参数 [0,1]

    for (uint32_t i = 0; i < nS; ++i) {
        result[i] = td.S[lo][i] * (1.0 - t) + td.S[hi][i] * t;
    }
    return result;
}

} // namespace rfsim
