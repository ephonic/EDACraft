// builtin_devices.cpp — 内置线性器件 wrapper 实现
#include "builtin_devices.hpp"

#include <cmath>
#include <stdexcept>

namespace rfsim {

// ---- Waveform --------------------------------------------------------------
double Waveform::valueAt(double t) const {
    if (t < td) return vo;
    double tp = t - td;
    switch (type) {
    case SIN:
        return vo + va * std::sin(2.0 * 3.14159265358979323846 * freq * tp);
    case PULSE: {
        if (period <= 0.0) return vo + va;  // 单脉冲
        double r = std::fmod(tp, period);
        return (r <= pw) ? (vo + va) : vo;
    }
    case DC:
    default:
        return vo;
    }
}

// ---- Resistor --------------------------------------------------------------
Resistor::Resistor(std::string name, NodeId n1, NodeId n2, double resistance)
    : name_(std::move(name)), nodes_{n1, n2}, r_(resistance) {
    if (resistance <= 0.0) {
        // 0 阻值在 SPICE 中合法(需作为 V=0 处理)，此处保守抛错；后续可细化
        if (resistance == 0.0) {
            g_ = std::numeric_limits<double>::infinity();
        } else {
            throw std::invalid_argument("Resistor: negative resistance");
        }
    } else {
        g_ = 1.0 / resistance;
    }
}

void Resistor::stamp_pattern(StampPattern& out) const {
    // 2x2 块: (n1,n1) (n1,n2) (n2,n1) (n2,n2)
    out.entries.reserve(out.entries.size() + 4);
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void Resistor::eval(const OperatingPoint& op, DeviceContribution& out) const {
    // 线性电阻只提供雅可比（导纳矩阵），残差由装配层用当前工作点计算
    out.f.assign(2, 0.0);
    out.jac.assign(4, 0.0);
    out.jac[0] =  g_;  // (n1,n1)
    out.jac[1] = -g_;  // (n1,n2)
    out.jac[2] = -g_;  // (n2,n1)
    out.jac[3] =  g_;  // (n2,n2)
    (void)op;
}

// ---- CurrentSource ---------------------------------------------------------
CurrentSource::CurrentSource(std::string name, NodeId n1, NodeId n2, double current)
    : name_(std::move(name)), nodes_{n1, n2}, i_(current) {}

void CurrentSource::stamp_pattern(StampPattern& out) const {
    (void)out;
}

void CurrentSource::eval(const OperatingPoint& op, DeviceContribution& out) const {
    // 电流从 n2 流向 n1：注入 n1 为 +i，注入 n2 为 -i
    out.f = { i_, -i_ };
    out.jac.clear();
    (void)op;
}

// ---- VoltageSource ---------------------------------------------------------
VoltageSource::VoltageSource(std::string name, NodeId n1, NodeId n2, double voltage)
    : name_(std::move(name)), nodes_{n1, n2}, v_(voltage) {}

void VoltageSource::stamp_pattern(StampPattern& out) const {
    // 电压源的 MNA stamp 涉及额外分支电流行，由装配层扩展。
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void VoltageSource::eval(const OperatingPoint& op, DeviceContribution& out) const {
    // 电压源约束: v1 - v2 = V。装配层把此约束加入扩展行。
    out.f = { v_, -v_ };
    out.jac.clear();
    (void)op;
}

double VoltageSource::valueAt(double t) const noexcept {
    if (wf_.type == Waveform::DC) return v_;
    return wf_.valueAt(t);
}

// ---- Capacitor -------------------------------------------------------------
Capacitor::Capacitor(std::string name, NodeId n1, NodeId n2, double capacitance)
    : name_(std::move(name)), nodes_{n1, n2}, c_(capacitance) {
    if (capacitance < 0.0) throw std::invalid_argument("Capacitor: negative capacitance");
}

void Capacitor::stamp_pattern(StampPattern& out) const {
    out.entries.reserve(out.entries.size() + 4);
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void Capacitor::eval(const OperatingPoint& /*op*/, DeviceContribution& out) const {
    // DC: 电容开路
    out.f.assign(2, 0.0);
    out.jac.assign(4, 0.0);
}

void Capacitor::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    out.f.assign(2, 0.0);
    out.jac.assign(4, 0.0);
    if (op.dt <= 0.0 || c_ <= 0.0) return;

    NodeId n1 = nodes_[0];
    NodeId n2 = nodes_[1];
    double v1 = (n1 < op.v.size()) ? op.v[n1] : 0.0;
    double v2 = (n2 < op.v.size()) ? op.v[n2] : 0.0;
    double v1p = (n1 < op.v_prev.size()) ? op.v_prev[n1] : 0.0;
    double v2p = (n2 < op.v_prev.size()) ? op.v_prev[n2] : 0.0;
    double vC = v1 - v2;
    double vCp = v1p - v2p;

    // 目前仅实现 Backward Euler（L-stable，对 stiff 问题更稳妥）
    double gEq = c_ / op.dt;
    double iC = gEq * (vC - vCp);  // 从 n1 流向 n2 的电容电流（Newton 残差）

    // companion model：I_n = gEq * vC - iEq，其中 iEq = gEq * vCp
    // 对节点 n1：流出电流 = +iC
    // 对节点 n2：流出电流 = -iC
    out.jac[0] =  gEq;
    out.jac[1] = -gEq;
    out.jac[2] = -gEq;
    out.jac[3] =  gEq;
    out.f[0] =  iC;
    out.f[1] = -iC;
}

void Capacitor::initializeTransientState(const std::vector<double>& nodeV) {
    NodeId n1 = nodes_[0];
    NodeId n2 = nodes_[1];
    double v1 = (n1 < nodeV.size()) ? nodeV[n1] : 0.0;
    double v2 = (n2 < nodeV.size()) ? nodeV[n2] : 0.0;
    vPrev_ = v1 - v2;
}

std::vector<double> Capacitor::getTransientState() const {
    return { vPrev_ };
}

void Capacitor::setTransientState(const std::vector<double>& s) {
    if (!s.empty()) vPrev_ = s[0];
}

void Capacitor::updateTransientState(const TransientOpPoint& op) {
    NodeId n1 = nodes_[0];
    NodeId n2 = nodes_[1];
    double v1 = (n1 < op.v.size()) ? op.v[n1] : 0.0;
    double v2 = (n2 < op.v.size()) ? op.v[n2] : 0.0;
    vPrev_ = v1 - v2;
}

// ---- Inductor --------------------------------------------------------------
Inductor::Inductor(std::string name, NodeId n1, NodeId n2, double inductance)
    : name_(std::move(name)), nodes_{n1, n2}, l_(inductance) {
    if (inductance <= 0.0) throw std::invalid_argument("Inductor: non-positive inductance");
}

void Inductor::stamp_pattern(StampPattern& out) const {
    out.entries.reserve(out.entries.size() + 4);
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void Inductor::eval(const OperatingPoint& /*op*/, DeviceContribution& out) const {
    // DC: 电感短路，由装配层用小电阻近似
    out.f.assign(2, 0.0);
    out.jac.assign(4, 0.0);
}

void Inductor::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    out.f.assign(2, 0.0);
    out.jac.assign(4, 0.0);
    if (op.dt <= 0.0 || l_ <= 0.0) return;

    NodeId n1 = nodes_[0];
    NodeId n2 = nodes_[1];
    double vC = 0.0;
    if (n1 < op.v.size() && n2 < op.v.size()) vC = op.v[n1] - op.v[n2];

    // 目前仅实现 Backward Euler
    double gEq = op.dt / l_;
    double iL = gEq * vC + iPrev_;  // 从 n1 流向 n2 的电感电流（Newton 残差）

    // I_n = gEq * vC + iPrev_
    out.jac[0] =  gEq;
    out.jac[1] = -gEq;
    out.jac[2] = -gEq;
    out.jac[3] =  gEq;
    out.f[0] =  iL;
    out.f[1] = -iL;
}

void Inductor::initializeTransientState(const std::vector<double>& nodeV) {
    // 没有额外信息时假设初始电流为 0
    (void)nodeV;
    iPrev_ = 0.0;
}

std::vector<double> Inductor::getTransientState() const {
    return { iPrev_ };
}

void Inductor::setTransientState(const std::vector<double>& s) {
    if (!s.empty()) iPrev_ = s[0];
}

void Inductor::updateTransientState(const TransientOpPoint& op) {
    NodeId n1 = nodes_[0];
    NodeId n2 = nodes_[1];
    double vC = 0.0;
    if (n1 < op.v.size() && n2 < op.v.size()) vC = op.v[n1] - op.v[n2];
    double gEq = op.dt / l_;
    iPrev_ = gEq * vC + iPrev_;
}

} // namespace rfsim
