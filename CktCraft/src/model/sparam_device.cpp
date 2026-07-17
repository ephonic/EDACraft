// sparam_device.cpp — N-port S 参数器件实现
//
// AC 分析：按频率插值 S→Y，stamp N×N 复数 Y 矩阵。
// DC 分析：Y(ω→0) 实部 stamp。
// 瞬态分析：Vector Fitting companion model（Backward-Euler）。
//
// VF 模型: Y(s) = Σ_k (R_k / (s − p_k)) + D
//   R_k 是 N×N 留数矩阵，D 是 N×N 常数矩阵，所有 Y_ij 共享同一组极点 p_k。
//   每极点对应一个 N 维状态向量 x_k，端口电流 I = Σ_k x_k + D·V。
#include "sparam_device.hpp"
#include "../sparam/touchstone.hpp"
#include <stdexcept>
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

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

    // 初始化 Vector Fitting（所有 Y_ij 共享极点）
    initVectorFitting();
}

SParamDevice::SParamDevice(std::string name, std::vector<NodeId> nodes,
                           TouchstoneData data)
    : name_(std::move(name)), nodes_(std::move(nodes)), sData_(std::move(data)) {
    numPorts_ = sData_.numPorts;
    if (nodes_.size() > numPorts_) nodes_.resize(numPorts_);
    initVectorFitting();
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

// ---- DC: Y(ω→0) 实部 stamp ----
namespace {
// 外推 S(0): 用最低两个频率点线性外推
std::vector<Complex> extrapolateS0(const TouchstoneData& td) {
    if (td.freqs.empty()) return {};
    if (td.freqs.size() >= 2) {
        double f0 = td.freqs[0], f1 = td.freqs[1];
        double t = f0 / (f1 - f0);
        std::vector<Complex> S0(td.numSParams());
        for (size_t i = 0; i < S0.size(); ++i)
            S0[i] = td.S[0][i] - (td.S[1][i] - td.S[0][i]) * t;
        return S0;
    }
    return td.S[0];
}
} // anonymous namespace

void SParamDevice::eval(const OperatingPoint& op, DeviceContribution& out) const {
    (void)op;  // DC 分析不使用工作点（线性器件）
    out.f.assign(numPorts_, 0.0);
    out.jac.assign(numPorts_ * numPorts_, 0.0);

    if (sData_.freqs.empty()) return;

    auto S0 = extrapolateS0(sData_);
    auto Y = sToY(S0, numPorts_, sData_.refImpedance);

    // DC stamp：实部作为电导
    for (uint32_t i = 0; i < numPorts_; ++i) {
        for (uint32_t j = 0; j < numPorts_; ++j) {
            out.jac[i * numPorts_ + j] = Y[i * numPorts_ + j].real();
        }
    }
    // gmin 对角正则化（防止奇异矩阵）
    const double gmin = 1e-12;
    for (uint32_t i = 0; i < numPorts_; ++i)
        out.jac[i * numPorts_ + i] += gmin;
}

std::vector<Complex> SParamDevice::admittanceMatrix(double omega) const {
    double freq = omega / (2.0 * M_PI);
    auto S = interpolateS(sData_, freq);
    return sToY(S, numPorts_, sData_.refImpedance);
}

std::vector<Complex> SParamDevice::dcAdmittanceMatrix() const {
    if (sData_.freqs.empty())
        return std::vector<Complex>(numPorts_ * numPorts_, Complex(0, 0));

    auto S0 = extrapolateS0(sData_);
    auto Y = sToY(S0, numPorts_, sData_.refImpedance);

    // 返回 Y 矩阵（实部作为电导，虚部置零）
    std::vector<Complex> Ydc(numPorts_ * numPorts_);
    for (uint32_t i = 0; i < numPorts_; ++i) {
        for (uint32_t j = 0; j < numPorts_; ++j) {
            Ydc[i * numPorts_ + j] = Complex(Y[i * numPorts_ + j].real(), 0);
        }
    }
    return Ydc;
}

// ---- Vector Fitting 初始化 ----
void SParamDevice::initVectorFitting() {
    vfFitted_ = false;
    if (sData_.freqs.empty() || numPorts_ == 0) return;

    // 极点数取 min(10, freqs/2)，避免过拟合（数据点过少时极点冗余）
    const int numPoles = std::min(10, std::max(2, static_cast<int>(sData_.freqs.size()) / 2));
    const uint32_t N = numPorts_;
    const auto& freqs = sData_.freqs;

    // 预计算所有频率点的 Y 矩阵
    // Ydata[freq_idx] = N×N Y 矩阵（行优先）
    std::vector<std::vector<std::complex<double>>> Ydata(freqs.size());
    for (size_t f = 0; f < freqs.size(); ++f) {
        Ydata[f] = sToY(sData_.S[f], N, sData_.refImpedance);
    }

    // 1) 对 Y_00 做 VF 拟合得到公共极点
    std::vector<std::complex<double>> Y00(freqs.size());
    for (size_t f = 0; f < freqs.size(); ++f)
        Y00[f] = Ydata[f][0];  // Y[0][0]

    VFResult vf0 = vectorFit(freqs, Y00, numPoles);
    vfPoles_ = vf0.poles;

    // 2) 用固定极点对所有 Y_ij 解留数（保证 companion model 极点一致）
    vfResidues_.assign(vfPoles_.size(),
                       std::vector<std::complex<double>>(N * N, std::complex<double>(0, 0)));
    vfConstant_.assign(N * N, std::complex<double>(0, 0));

    for (uint32_t i = 0; i < N; ++i) {
        for (uint32_t j = 0; j < N; ++j) {
            std::vector<std::complex<double>> Yij(freqs.size());
            for (size_t f = 0; f < freqs.size(); ++f)
                Yij[f] = Ydata[f][i * N + j];

            VFResult vfij = vectorFitFixedPoles(freqs, Yij, vfPoles_);
            // 存该 (i,j) 的留数到每个极点的 N×N 矩阵
            for (size_t k = 0; k < vfPoles_.size(); ++k)
                vfResidues_[k][i * N + j] = vfij.residues[k];
            vfConstant_[i * N + j] = vfij.constant;
        }
    }

    // 3) 初始化 companion model 状态（每极点×端口一个实数状态变量）
    // 对复数极点对 (p, p̄)，状态合并为实数存储：每对用一个实数状态/端口。
    // 为简化：直接按极点数×端口数分配实数状态，updateTransientState 中
    // 对复数极点取实部合并。
    state_.assign(vfPoles_.size() * N, 0.0);
    vfFitted_ = true;
}

// ---- 瞬态 companion model (Backward-Euler) ----
//
// Y(s) = Σ_k R_k/(s-p_k) + D，状态方程 s·x_k = p_k·x_k + R_k·V
// BE: x_k[n] = (x_k[n-1] + dt·R_k·V[n]) / (1 - dt·p_k)
//    I = Σ_k x_k + D·V
//    G_eq (雅可比) = Σ_k R_k/(1-dt·p_k) + D
//    I_hist (常数) = Σ_k x_k[n-1]/(1-dt·p_k)
//    f = G_eq·V + I_hist  （I_hist 已含 -x_prev 项的等价合并）
void SParamDevice::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    const uint32_t N = numPorts_;
    out.f.assign(N, 0.0);
    out.jac.assign(N * N, 0.0);

    if (!vfFitted_ || vfPoles_.empty()) {
        // 无 VF 拟合：退化为 DC 电导
        auto Ydc = dcAdmittanceMatrix();
        for (uint32_t i = 0; i < N; ++i)
            for (uint32_t j = 0; j < N; ++j)
                out.jac[i * N + j] = Ydc[i * N + j].real();
        // f = G·V
        for (uint32_t i = 0; i < N; ++i) {
            for (uint32_t j = 0; j < N; ++j) {
                NodeId nj = nodes_[j];
                double Vj = (nj < op.v.size()) ? op.v[nj] : 0.0;
                out.f[i] += out.jac[i * N + j] * Vj;
            }
        }
        return;
    }

    const double dt = op.dt;
    const int K = static_cast<int>(vfPoles_.size());

    // 端口电压
    std::vector<double> V(N, 0.0);
    for (uint32_t i = 0; i < N; ++i) {
        NodeId ni = nodes_[i];
        V[i] = (ni < op.v.size()) ? op.v[ni] : 0.0;
    }

    // G_eq = Σ_k R_k/(1-dt·p_k) + D  (N×N 复数 → 取实部)
    std::vector<std::complex<double>> Geq(N * N, std::complex<double>(0, 0));
    std::vector<std::complex<double>> Ihist(N, std::complex<double>(0, 0));

    for (int k = 0; k < K; ++k) {
        std::complex<double> pk = vfPoles_[k];
        std::complex<double> denom(1.0, 0.0);
        denom = (1.0 - dt * pk);
        if (std::abs(denom) < 1e-15) denom = std::complex<double>(1e-15, 0.0);
        std::complex<double> invDenom = std::complex<double>(1.0, 0.0) / denom;

        // R_k/(1-dt·p_k) 累加到 G_eq
        for (uint32_t e = 0; e < N * N; ++e)
            Geq[e] += vfResidues_[k][e] * invDenom;

        // 历史电流: x_k[n-1]/(1-dt·p_k)
        // 状态布局: state_[k*N + port]，对复数极点对合并取实部
        for (uint32_t j = 0; j < N; ++j) {
            double xPrev = state_[k * N + j];
            Ihist[j] += std::complex<double>(xPrev, 0.0) * invDenom;
        }
    }
    // 加常数项 D
    for (uint32_t e = 0; e < N * N; ++e)
        Geq[e] += vfConstant_[e];

    // 输出雅可比（取实部）
    for (uint32_t i = 0; i < N; ++i)
        for (uint32_t j = 0; j < N; ++j)
            out.jac[i * N + j] = Geq[i * N + j].real();

    // f = G_eq·V + I_hist
    for (uint32_t i = 0; i < N; ++i) {
        double Ii = Ihist[i].real();
        for (uint32_t j = 0; j < N; ++j)
            Ii += Geq[i * N + j].real() * V[j];
        out.f[i] = Ii;
    }
}

void SParamDevice::updateTransientState(const TransientOpPoint& op) {
    if (!vfFitted_ || vfPoles_.empty()) return;

    const uint32_t N = numPorts_;
    const double dt = op.dt;
    const int K = static_cast<int>(vfPoles_.size());

    // 端口电压
    std::vector<double> V(N, 0.0);
    for (uint32_t i = 0; i < N; ++i) {
        NodeId ni = nodes_[i];
        V[i] = (ni < op.v.size()) ? op.v[ni] : 0.0;
    }

    // BE 状态更新: x_k[n] = (x_k[n-1] + dt·R_k·V) / (1 - dt·p_k)
    // 对复数极点对 (p, p̄)，其状态 x_p 与 x_p̄ 共轭，实数状态取 Re(x_p)。
    // 这里直接按极点逐个更新实数状态，复数极点的虚部贡献在
    // evalTransient 的 G_eq/I_hist 中已通过 R_k/(1-dt·p_k) 的实部隐含。
    std::vector<double> newState(K * N, 0.0);
    for (int k = 0; k < K; ++k) {
        std::complex<double> pk = vfPoles_[k];
        std::complex<double> denom = (1.0 - dt * pk);
        if (std::abs(denom) < 1e-15) denom = std::complex<double>(1e-15, 0.0);
        std::complex<double> invDenom = std::complex<double>(1.0, 0.0) / denom;

        for (uint32_t j = 0; j < N; ++j) {
            double xPrev = state_[k * N + j];
            // dt · (R_k·V)_j = dt · Σ_m R_k[j,m]·V[m]
            std::complex<double> rkVj(0, 0);
            for (uint32_t m = 0; m < N; ++m)
                rkVj += vfResidues_[k][j * N + m] * V[m];
            std::complex<double> xNew =
                (std::complex<double>(xPrev, 0.0) + dt * rkVj) * invDenom;
            // 取实部存储（复数极点对的虚部在配对极点处相互抵消）
            newState[k * N + j] = xNew.real();
        }
    }
    state_ = std::move(newState);
}

size_t SParamDevice::transientStateSize() const {
    if (!vfFitted_) return 0;
    return vfPoles_.size() * numPorts_;
}

void SParamDevice::initializeTransientState(const std::vector<double>& nodeV) {
    (void)nodeV;
    if (vfFitted_) std::fill(state_.begin(), state_.end(), 0.0);
}

std::vector<double> SParamDevice::getTransientState() const {
    return state_;
}

void SParamDevice::setTransientState(const std::vector<double>& state) {
    state_ = state;
}

} // namespace rfsim
