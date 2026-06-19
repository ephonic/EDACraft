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

// 时变源波形（简化支持 SIN / PULSE / DC）
struct Waveform {
    enum Type { DC, SIN, PULSE } type = DC;
    // SIN:  v(t) = vo + va * sin(2*pi*freq*(t - td))
    // PULSE: v(t) = (t 在 [td, td+pw] 模 period 内) ? v1 : v2
    double vo = 0.0;      // DC offset / SIN offset / PULSE v1
    double va = 0.0;      // SIN amplitude / PULSE v2-v1
    double freq = 0.0;    // SIN frequency
    double td = 0.0;      // delay
    double period = 0.0;  // PULSE period
    double pw = 0.0;      // PULSE pulse width
    double tr = 0.0;      // PULSE rise time (暂不用)
    double tf = 0.0;      // PULSE fall time (暂不用)

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

} // namespace rfsim

#endif // RFSIM_MODEL_BUILTIN_DEVICES_HPP
