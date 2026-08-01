// builtin_devices.hpp — 内置线性器件 wrapper（不经过 OpenVAF/OSDI）
//
// DC/MNA 装配语义：
//   Resistor(n1,n2,R):  G[n1,n1]+=g  G[n2,n2]+=g  G[n1,n2]-=g  G[n2,n1]-=g,  g=1/R
//   CurrentSource(n1,n2,I):  F[n1]+=I  F[n2]-=I  (电流从 n2 流向 n1 时 I>0)
//   VoltageSource(n1,n2,V):  需额外分支电流未知数，由装配层处理；此处提供源值
//
// 注：电压源在 MNA 中引入额外行（分支电流），其 stamp 涉及矩阵扩维。
//     本 wrapper 只描述器件自身贡献，扩维与边界约束由装配层(assembly/)统一处理。
//     M2 阶段先实现 R/I/V 的 DC 行为，L/C 在 HB 频域装配时再补。
#ifndef RFSIM_MODEL_BUILTIN_DEVICES_HPP
#define RFSIM_MODEL_BUILTIN_DEVICES_HPP

#include "device_model.hpp"
#include "../rfsim.hpp"
#include <string>
#include <vector>

namespace rfsim {

// 时变源波形（支持 DC / SIN / PULSE / EXP / PWL）
struct Waveform {
    enum Type { DC, SIN, PULSE, EXP, PWL } type = DC;
    // SIN:  v(t) = vo + va * sin(2*pi*freq*(t - td))
    // PULSE: v(t) = (t 在 [td, td+pw] 模 period 内) ? v1 : v2
    double vo = 0.0;      // DC offset / SIN offset / PULSE v1
    double va = 0.0;      // SIN amplitude / PULSE v2-v1
    double freq = 0.0;    // SIN frequency
    double td = 0.0;      // delay
    double period = 0.0;  // PULSE period
    double pw = 0.0;      // PULSE pulse width
    double tr = 0.0;      // PULSE rise time
    double tf = 0.0;      // PULSE fall time
    // PWL: 分段线性 (t_i, v_i) 对
    std::vector<std::pair<double,double>> pwlPoints;

    [[nodiscard]] double valueAt(double t) const;
};

// 电阻 R
class Resistor : public DeviceModel {
public:
    Resistor(std::string name, NodeId n1, NodeId n2, double resistance);

    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }

    [[nodiscard]] double resistance() const noexcept { return r_; }
    [[nodiscard]] double conductance() const noexcept { return g_; }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1, n2}
    double r_ = 0;
    double g_ = 0;  // 1/R
};

// 电流源 I（从 n2 流向 n1，即电流注入 n1）
class CurrentSource : public DeviceModel {
public:
    CurrentSource(std::string name, NodeId n1, NodeId n2, double current);

    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }

    [[nodiscard]] double current() const noexcept { return i_; }
    void setCurrent(double i) noexcept { i_ = i; }
    [[nodiscard]] const Waveform& waveform() const noexcept { return wf_; }
    void setWaveform(const Waveform& w) { wf_ = w; }
private:
    std::string name_;
    std::vector<NodeId> nodes_;
    double i_ = 0;
    Waveform wf_;
};

// 电压源 V（n1 - n2 = V）
// MNA 中需引入分支电流未知数 I_branch；stamp 涉及矩阵扩维。
// 此 wrapper 暴露源值与节点，扩维由装配层处理。
class VoltageSource : public DeviceModel {
public:
    VoltageSource(std::string name, NodeId n1, NodeId n2, double voltage);

    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }

    [[nodiscard]] double voltage() const noexcept { return v_; }
    void setVoltage(double v) noexcept { v_ = v; }
    // AC 小信号幅度（复激励；imag=相位，默认0）
    [[nodiscard]] Complex acMag() const noexcept { return acMag_; }
    void setAcMag(Complex c) { acMag_ = c; }
    [[nodiscard]] bool needs_branch_current() const noexcept { return true; }
    [[nodiscard]] const Waveform& waveform() const noexcept { return wf_; }
    void setWaveform(const Waveform& w) { wf_ = w; }
    [[nodiscard]] double valueAt(double t) const noexcept;
private:
    std::string name_;
    std::vector<NodeId> nodes_;
    double v_ = 0;
    Complex acMag_ = {0.0, 0.0};
    Waveform wf_;
};

// 电容 C —— DC 开路，AC 频域导纳 Y = jωC
// DC 阶段导纳为 0（不 stamp G 矩阵），AC 阶段 stamp Y_C。
class Capacitor : public DeviceModel {
public:
    Capacitor(std::string name, NodeId n1, NodeId n2, double capacitance);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }
    [[nodiscard]] double capacitance() const noexcept { return c_; }
    // 频域导纳
    [[nodiscard]] Complex admittance(double omega) const noexcept {
        return Complex(0.0, omega * c_);
    }
    // 瞬态状态：上一时刻电容电压 vC_prev
    [[nodiscard]] bool hasTransientState() const override { return true; }
    [[nodiscard]] size_t transientStateSize() const override { return 1; }
    void initializeTransientState(const std::vector<double>& nodeV) override;
    [[nodiscard]] std::vector<double> getTransientState() const override;
    void setTransientState(const std::vector<double>& s) override;
    void updateTransientState(const TransientOpPoint& op) override;
private:
    std::string name_;
    std::vector<NodeId> nodes_;
    double c_ = 0;
    mutable double vPrev_ = 0.0;  // 上一时刻 v1 - v2
};

// 电感 L —— DC 短路，AC 频域导纳 Y = 1/(jωL)
class Inductor : public DeviceModel {
public:
    Inductor(std::string name, NodeId n1, NodeId n2, double inductance);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }
    [[nodiscard]] double inductance() const noexcept { return l_; }
    [[nodiscard]] Complex admittance(double omega) const noexcept {
        // H6: omega=0 时返回大电导（短路），避免除零
        if (omega == 0.0) return Complex(1e6, 0.0);
        // 1/(jωL) = -j/(ωL)
        return Complex(0.0, -1.0 / (omega * l_));
    }
    // 瞬态状态：上一时刻电感电流 iL_prev（从 n1 流向 n2）
    [[nodiscard]] bool hasTransientState() const override { return true; }
    [[nodiscard]] size_t transientStateSize() const override { return 1; }
    void initializeTransientState(const std::vector<double>& nodeV) override;
    [[nodiscard]] std::vector<double> getTransientState() const override;
    void setTransientState(const std::vector<double>& s) override;
    void updateTransientState(const TransientOpPoint& op) override;
private:
    std::string name_;
    std::vector<NodeId> nodes_;
    double l_ = 0;
    mutable double iPrev_ = 0.0;  // 上一时刻从 n1 流向 n2 的电流
};

// ---- 行为源 E/F/G/H ----
// E: VCVS (电压控电压源)  V(out+) - V(out-) = gain * (V(in+) - V(in-))
// G: VCCS (电压控电流源) I(out+ -> out-) = gain * (V(in+) - V(in-))
// F: CCVS (电流控电压源) V(out+) - V(out-) = gain * I(Vsrc)   [需 VS 分支电流]
// H: CCCS (电流控电流源) I(out+ -> out-) = gain * I(Vsrc)      [需 VS 分支电流]
// 简化实现：E/G 支持任意节点对控制；F/H 需要 VS 分支电流（通过 branchCurrents 访问）

// E: VCVS 线性电压控电压源
class VCVS : public DeviceModel {
public:
    VCVS(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2, double gain);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }
    [[nodiscard]] bool needs_branch_current() const { return true; }
    [[nodiscard]] double gain() const noexcept { return gain_; }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1(out+), n2(out-), c1(in+), c2(in-)}
    double gain_;
};

// G: VCCS 线性电压控电流源（跨导）
class VCCS : public DeviceModel {
public:
    VCCS(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2, double gain);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }
    [[nodiscard]] double gain() const noexcept { return gain_; }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1(out+), n2(out-), c1(in+), c2(in-)}
    double gain_;
};

// F: CCCS 线性电流控电流源（电流增益，控制源为 VS 分支电流）
class CCCS : public DeviceModel {
public:
    CCCS(std::string name, NodeId n1, NodeId n2, NodeId vsIdx, double gain);
    CCCS(std::string name, NodeId n1, NodeId n2, const std::string& vsName, double gain);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }
    [[nodiscard]] double gain() const noexcept { return gain_; }
    [[nodiscard]] NodeId vsIndex() const noexcept { return vsIdx_; }
    void setVsIndex(NodeId idx) { vsIdx_ = idx; }
    [[nodiscard]] const std::string& vsName() const noexcept { return vsName_; }
    void setBranchCurrents(const std::vector<double>* bc) const { branchCurrents_ = bc; }
    [[nodiscard]] double readBranchCurrent() const {
        if (branchCurrents_ && vsIdx_ + 1 < branchCurrents_->size())
            return (*branchCurrents_)[vsIdx_ + 1];
        return 0.0;
    }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1(out+), n2(out-)}
    NodeId vsIdx_;  // 控制电压源分支索引（在 MNA 扩展矩阵中的列号）
    std::string vsName_;  // 控制电压源实例名（用于装配阶段解析）
    double gain_;
    mutable const std::vector<double>* branchCurrents_ = nullptr;
};

// H: CCVS 线性电流控电压源（跨阻，控制源为 VS 分支电流）
class CCVS : public DeviceModel {
public:
    CCVS(std::string name, NodeId n1, NodeId n2, NodeId vsIdx, double gain);
    CCVS(std::string name, NodeId n1, NodeId n2, const std::string& vsName, double gain);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }
    [[nodiscard]] bool needs_branch_current() const { return true; }
    [[nodiscard]] double gain() const noexcept { return gain_; }
    [[nodiscard]] NodeId vsIndex() const noexcept { return vsIdx_; }
    void setVsIndex(NodeId idx) { vsIdx_ = idx; }
    [[nodiscard]] const std::string& vsName() const noexcept { return vsName_; }
    void setBranchCurrents(const std::vector<double>* bc) const { branchCurrents_ = bc; }
    [[nodiscard]] double readBranchCurrent() const {
        if (branchCurrents_ && vsIdx_ + 1 < branchCurrents_->size())
            return (*branchCurrents_)[vsIdx_ + 1];
        return 0.0;
    }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1(out+), n2(out-)}
    NodeId vsIdx_;
    std::string vsName_;
    double gain_;
    mutable const std::vector<double>* branchCurrents_ = nullptr;
};

// K: 互感（耦合电感）
// 两个电感 L1(n1a,n1b) 和 L2(n2a,n2b) 通过耦合系数 k 耦合
// M = k * sqrt(L1 * L2)
class MutualInductance : public DeviceModel {
public:
    MutualInductance(std::string name, NodeId l1a, NodeId l1b,
                     NodeId l2a, NodeId l2b, double L1, double L2, double k);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return true; }
    std::string name() const override { return name_; }
    [[nodiscard]] bool hasTransientState() const override { return true; }
    [[nodiscard]] size_t transientStateSize() const override { return 2; }
    void initializeTransientState(const std::vector<double>& nodeV) override;
    [[nodiscard]] std::vector<double> getTransientState() const override;
    void setTransientState(const std::vector<double>& s) override;
    void updateTransientState(const TransientOpPoint& op) override;
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {l1a, l1b, l2a, l2b}
    double L1_, L2_, k_, M_;  // M = k * sqrt(L1*L2)
    mutable double i1Prev_ = 0.0, i2Prev_ = 0.0;
};

// S: 压控开关
// 当 V(ctrl+) - V(ctrl-) > vt 时导通（Ron），否则断开（Roff）
class VCSwitch : public DeviceModel {
public:
    VCSwitch(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2,
             double ron, double roff, double vt, double vh);
    const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool is_linear() const override { return false; }
    std::string name() const override { return name_; }
private:
    std::string name_;
    std::vector<NodeId> nodes_;  // {n1, n2, c1, c2}
    double ron_, roff_, vt_, vh_;
    // 平滑过渡参数：在 [vt-vh, vt+vh] 之间用 tanh 平滑
    [[nodiscard]] double conductance(double vctrl) const;
};

} // namespace rfsim

#endif // RFSIM_MODEL_BUILTIN_DEVICES_HPP
