// sparam_device.cpp — N-port S 参数器件实现
#include "sparam_device.hpp"
#include <stdexcept>

namespace rfsim {

SParamDevice::SParamDevice(std::string name, std::vector<NodeId> nodes,
                           const std::string& touchstonePath, double z0)
    : name_(std::move(name)), nodes_(std::move(nodes)) {
    sData_ = parseTouchstone(touchstonePath);
    if (z0 > 0) sData_.refImpedance = z0;
    numPorts_ = sData_.numPorts;
    if (nodes_.size() < numPorts_) {
        throw std::runtime_error("SParamDevice '" + name_ +
            "': netlist has " + std::to_string(nodes_.size()) +
            " nodes but touchstone has " + std::to_string(numPorts_) + " ports");
    }
    // 若节点数 > 端口数，截断（多余的可能是 file= 等参数被误当节点）
    nodes_.resize(numPorts_);
}

SParamDevice::SParamDevice(std::string name, std::vector<NodeId> nodes,
                           TouchstoneData data)
    : name_(std::move(name)), nodes_(std::move(nodes)), sData_(std::move(data)) {
    numPorts_ = sData_.numPorts;
    if (nodes_.size() > numPorts_) nodes_.resize(numPorts_);
}

void SParamDevice::stamp_pattern(StampPattern& out) const {
    // N×N 全密 Y 矩阵——所有 (i,j) 对都有非零
    for (uint32_t i = 0; i < numPorts_; ++i) {
        NodeId ni = nodes_[i];
        if (ni == 0) continue;  // 地节点跳过
        for (uint32_t j = 0; j < numPorts_; ++j) {
            NodeId nj = nodes_[j];
            if (nj == 0) continue;
            out.entries.emplace_back(ni, nj);
        }
    }
}

void SParamDevice::eval(const OperatingPoint& op, DeviceContribution& out) const {
    // DC: Y(ω→0) 的实部
    // 用最低频率点的 Y 矩阵实部近似
    (void)op;  // DC 分析不使用工作点
    if (sData_.freqs.empty()) {
        out.f.assign(numPorts_, 0.0);
        out.jac.assign(numPorts_ * numPorts_, 0.0);
        return;
    }

    // 外推到 ω=0：用最低两个频率点线性外推
    std::vector<Complex> S0;
    if (sData_.freqs.size() >= 2) {
        // 线性外推 S(0) = S[0] - (S[1]-S[0]) * f0/(f1-f0)
        double f0 = sData_.freqs[0], f1 = sData_.freqs[1];
        double t = f0 / (f1 - f0);
        S0.resize(sData_.numSParams());
        for (size_t i = 0; i < S0.size(); ++i)
            S0[i] = sData_.S[0][i] - (sData_.S[1][i] - sData_.S[0][i]) * t;
    } else {
        S0 = sData_.S[0];
    }

    auto Y = sToY(S0, numPorts_, sData_.refImpedance);

    // DC stamp：实部作为电导
    out.f.assign(numPorts_, 0.0);
    out.jac.assign(numPorts_ * numPorts_, 0.0);
    for (uint32_t i = 0; i < numPorts_; ++i)
        out.jac[i * numPorts_ + i] = 0.0;  // 先清零
    for (uint32_t i = 0; i < numPorts_; ++i) {
        for (uint32_t j = 0; j < numPorts_; ++j) {
            out.jac[i * numPorts_ + j] = Y[i * numPorts_ + j].real();
        }
    }
    // 加 gmin 对角正则化（防止奇异）
    const double gmin = 1e-12;
    for (uint32_t i = 0; i < numPorts_; ++i)
        out.jac[i * numPorts_ + i] += gmin;
}

std::vector<Complex> SParamDevice::admittanceMatrix(double omega) const {
    // omega = 2πf
    double freq = omega / (2.0 * 3.14159265358979323846);
    // 插值 S 参数
    auto S = interpolateS(sData_, freq);
    // S → Y 转换
    return sToY(S, numPorts_, sData_.refImpedance);
}

} // namespace rfsim
