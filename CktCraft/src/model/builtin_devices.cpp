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
        // HSPICE PULSE(v1 v2 td tr tf pw per)
        // vo=v1, va=v2-v1
        double v1 = vo, v2 = vo + va;
        if (period <= 0.0) {
            // 单脉冲：td -> tr -> v2 -> pw -> tf -> v1
            if (tp < tr) return v1 + (v2 - v1) * (tr > 0 ? tp / tr : 1.0);
            if (tp < tr + pw) return v2;
            if (tp < tr + pw + tf) return v2 - (v2 - v1) * (tf > 0 ? (tp - tr - pw) / tf : 1.0);
            return v1;
        }
        double r = std::fmod(tp, period);
        double t_rise = tr;
        double t_high = tr + pw;
        double t_fall = tr + pw + tf;
        if (r < t_rise)       return v1 + (v2 - v1) * (tr > 0 ? r / tr : 1.0);
        else if (r < t_high)  return v2;
        else if (r < t_fall)  return v2 - (v2 - v1) * (tf > 0 ? (r - t_high) / tf : 1.0);
        else                  return v1;
    }
    case EXP: {
        // EXP(v1 v2 td1 tau1 td2 tau2)
        // vo=v1, va=v2-v1, td=td1, freq=tau1, pw=td2, period=tau2
        double v1 = vo, v2 = vo + va;
        double td1 = td, tau1 = freq;
        double td2 = pw, tau2 = period;
        if (tp < td1) return v1;
        if (tp < td2) return v1 + (v2 - v1) * (1.0 - std::exp(-(tp - td1) / (tau1 > 0 ? tau1 : 1e-12)));
        return v2 - (v2 - v1) * (1.0 - std::exp(-(tp - td2) / (tau2 > 0 ? tau2 : 1e-12)));
    }
    case PWL: {
        // 分段线性：pwlPoints 按 t 排序，线性插值
        if (pwlPoints.empty()) return vo;
        if (pwlPoints.size() == 1) return pwlPoints[0].second;
        if (tp <= pwlPoints[0].first) return pwlPoints[0].second;
        if (tp >= pwlPoints.back().first) return pwlPoints.back().second;
        for (size_t i = 1; i < pwlPoints.size(); ++i) {
            if (tp <= pwlPoints[i].first) {
                double t0 = pwlPoints[i-1].first, v0 = pwlPoints[i-1].second;
                double t1 = pwlPoints[i].first, v1 = pwlPoints[i].second;
                if (t1 <= t0) return v1;
                return v0 + (v1 - v0) * (tp - t0) / (t1 - t0);
            }
        }
        return pwlPoints.back().second;
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

// ==================== VCVS (E) ====================
VCVS::VCVS(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2, double gain)
    : name_(std::move(name)), nodes_{n1, n2, c1, c2}, gain_(gain) {}

void VCVS::stamp_pattern(StampPattern& out) const {
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void VCVS::eval(const OperatingPoint& op, DeviceContribution& out) const {
    out.f.assign(4, 0.0);
    out.jac.assign(4, 0.0);
    // VCVS: V(n1) - V(n2) = gain * (V(c1) - V(c2))
    // KCL at n1: I_branch flows out
    // KCL at n2: -I_branch
    // Branch equation: V(n1) - V(n2) - gain*(V(c1)-V(c2)) = 0
    // This requires a branch current variable in MNA.
    // Simplified: use large conductance approximation (like voltage source)
    double vc = 0.0;
    if (nodes_[2] < op.v.size()) vc += op.v[nodes_[2]];
    if (nodes_[3] < op.v.size()) vc -= op.v[nodes_[3]];
    double vout = gain_ * vc;
    // Stamp as voltage source with value vout between n1 and n2
    // The assembly layer handles branch current for VS-type devices
    out.f[0] = vout;  // report voltage value; assembly handles MNA stamp
    out.jac[0] = 0;   // linear, constant
}

// ==================== VCCS (G) ====================
VCCS::VCCS(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2, double gain)
    : name_(std::move(name)), nodes_{n1, n2, c1, c2}, gain_(gain) {}

void VCCS::stamp_pattern(StampPattern& out) const {
    out.entries.emplace_back(nodes_[0], nodes_[0]); out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[0], nodes_[2]); out.entries.emplace_back(nodes_[0], nodes_[3]);
    out.entries.emplace_back(nodes_[1], nodes_[0]); out.entries.emplace_back(nodes_[1], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[2]); out.entries.emplace_back(nodes_[1], nodes_[3]);
}

void VCCS::eval(const OperatingPoint& op, DeviceContribution& out) const {
    out.f.assign(4, 0.0);  // 4 nodes: n1, n2, c1, c2
    out.jac.assign(8, 0.0);
    double vc = 0.0;
    if (nodes_[2] < op.v.size()) vc += op.v[nodes_[2]];
    if (nodes_[3] < op.v.size()) vc -= op.v[nodes_[3]];
    double i = gain_ * vc;  // current from n2 to n1 (into n1)
    // Convention: f = current LEAVING the node (same as Resistor)
    out.f[0] = -i;   // current leaving n1 = -i (current enters n1)
    out.f[1] = i;    // current leaving n2 = +i (current leaves n2)
    // c1 and c2 have no residual (only Jacobian contributions)
    out.f[2] = 0; out.f[3] = 0;
    // Jacobian: dI_leaving_n1/dV(c1) = -gain, dI_leaving_n1/dV(c2) = +gain
    out.jac[0] = 0;    out.jac[1] = 0;    out.jac[2] = -gain_;  out.jac[3] = gain_;
    out.jac[4] = 0;    out.jac[5] = 0;    out.jac[6] = gain_;   out.jac[7] = -gain_;
}

// ==================== CCCS (F) ====================
CCCS::CCCS(std::string name, NodeId n1, NodeId n2, NodeId vsIdx, double gain)
    : name_(std::move(name)), nodes_{n1, n2}, vsIdx_(vsIdx), gain_(gain) {}

CCCS::CCCS(std::string name, NodeId n1, NodeId n2, const std::string& vsName, double gain)
    : name_(std::move(name)), nodes_{n1, n2}, vsIdx_(0), vsName_(vsName), gain_(gain) {}

void CCCS::stamp_pattern(StampPattern& out) const {
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void CCCS::eval(const OperatingPoint& op, DeviceContribution& out) const {
    out.f.assign(2, 0.0);
    out.jac.assign(2, 0.0);
    // I_out = gain * I_vs
    // branchCurrents_ points to fullSol: [V0, V1..Vn, Ibr0, Ibr1, ...]
    // vsIdx_ = numNodes + k (0-based matrix index)
    // Branch current k is at fullSol[numNodes + 1 + k] = fullSol[vsIdx_ + 1]
    double i_vs = 0.0;
    if (branchCurrents_ && vsIdx_ + 1 < branchCurrents_->size())
        i_vs = (*branchCurrents_)[vsIdx_ + 1];
    double i_out = gain_ * i_vs;
    out.f[0] = i_out;
    out.f[1] = -i_out;
}

void CCCS::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    OperatingPoint dcOp{op.v};
    eval(dcOp, out);
}

// ==================== CCVS (H) ====================
CCVS::CCVS(std::string name, NodeId n1, NodeId n2, NodeId vsIdx, double gain)
    : name_(std::move(name)), nodes_{n1, n2}, vsIdx_(vsIdx), gain_(gain) {}

CCVS::CCVS(std::string name, NodeId n1, NodeId n2, const std::string& vsName, double gain)
    : name_(std::move(name)), nodes_{n1, n2}, vsIdx_(0), vsName_(vsName), gain_(gain) {}

void CCVS::stamp_pattern(StampPattern& out) const {
    out.entries.emplace_back(nodes_[0], nodes_[0]);
    out.entries.emplace_back(nodes_[1], nodes_[1]);
}

void CCVS::eval(const OperatingPoint& op, DeviceContribution& out) const {
    out.f.assign(2, 0.0);
    out.jac.assign(2, 0.0);
    double i_vs = 0.0;
    if (branchCurrents_ && vsIdx_ < branchCurrents_->size())
        i_vs = (*branchCurrents_)[vsIdx_];
    double v_out = gain_ * i_vs;
    out.f[0] = v_out;
    out.jac[0] = 0;
}

// ==================== MutualInductance (K) ====================
MutualInductance::MutualInductance(std::string name, NodeId l1a, NodeId l1b,
                                   NodeId l2a, NodeId l2b, double L1, double L2, double k)
    : name_(std::move(name)), nodes_{l1a, l1b, l2a, l2b},
      L1_(L1), L2_(L2), k_(k), M_(k * std::sqrt(L1 * L2)) {}

void MutualInductance::stamp_pattern(StampPattern& out) const {
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            out.entries.emplace_back(nodes_[i], nodes_[j]);
}

void MutualInductance::eval(const OperatingPoint& op, DeviceContribution& out) const {
    // DC: inductors are shorts, mutual coupling has no DC effect
    out.f.assign(4, 0.0);
    out.jac.assign(16, 0.0);
}

void MutualInductance::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    out.f.assign(4, 0.0);
    out.jac.assign(16, 0.0);
    // Transient companion model for coupled inductors:
    // V1 = L1 * dI1/dt + M * dI2/dt
    // V2 = M * dI1/dt + L2 * dI2/dt
    // Backward Euler: dI/dt = (I - I_prev)/dt
    // V1 = (L1/dt) * I1 + (M/dt) * I2 - (L1/dt)*I1_prev - (M/dt)*I2_prev
    double g11 = L1_ / op.dt;
    double g22 = L2_ / op.dt;
    double gm = M_ / op.dt;
    // I1 = g11*V1 + gm*V2 - g11*i1Prev - gm*i2Prev (companion model current)
    // Stamp as conductance matrix [[g11, gm], [gm, g22]] between nodes
    double i1 = g11 * i1Prev_ + gm * i2Prev_;
    double i2 = gm * i1Prev_ + g22 * i2Prev_;
    // KCL at l1a: +I1, at l1b: -I1
    // KCL at l2a: +I2, at l2b: -I2
    // out.f contains: current source part (-companion model)
    // out.jac contains: conductance matrix
    double v1 = 0, v2 = 0;
    if (nodes_[0] < op.v.size() && nodes_[1] < op.v.size())
        v1 = op.v[nodes_[0]] - op.v[nodes_[1]];
    if (nodes_[2] < op.v.size() && nodes_[3] < op.v.size())
        v2 = op.v[nodes_[2]] - op.v[nodes_[3]];
    double I1 = g11 * v1 + gm * v2 - i1;
    double I2 = gm * v1 + g22 * v2 - i2;
    out.f[0] = I1;
    out.f[1] = -I1;
    out.f[2] = I2;
    out.f[3] = -I2;
    // Jacobian (4x4: rows=l1a,l1b,l2a,l2b; cols=l1a,l1b,l2a,l2b)
    double J[4][4] = {
        {g11, -g11, gm, -gm},
        {-g11, g11, -gm, gm},
        {gm, -gm, g22, -g22},
        {-gm, gm, -g22, g22}
    };
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            out.jac[i*4+j] = J[i][j];
}

void MutualInductance::initializeTransientState(const std::vector<double>&) {
    i1Prev_ = 0.0;
    i2Prev_ = 0.0;
}

std::vector<double> MutualInductance::getTransientState() const {
    return {i1Prev_, i2Prev_};
}

void MutualInductance::setTransientState(const std::vector<double>& s) {
    if (s.size() >= 2) { i1Prev_ = s[0]; i2Prev_ = s[1]; }
}

void MutualInductance::updateTransientState(const TransientOpPoint& op) {
    double g11 = L1_ / op.dt;
    double g22 = L2_ / op.dt;
    double gm = M_ / op.dt;
    double v1 = 0, v2 = 0;
    if (nodes_[0] < op.v.size() && nodes_[1] < op.v.size())
        v1 = op.v[nodes_[0]] - op.v[nodes_[1]];
    if (nodes_[2] < op.v.size() && nodes_[3] < op.v.size())
        v2 = op.v[nodes_[2]] - op.v[nodes_[3]];
    i1Prev_ = g11 * v1 + gm * v2 - (g11 * i1Prev_ + gm * i2Prev_);
    i2Prev_ = gm * v1 + g22 * v2 - (gm * i1Prev_ + g22 * i2Prev_);
}

// ==================== VCSwitch (S) ====================
VCSwitch::VCSwitch(std::string name, NodeId n1, NodeId n2, NodeId c1, NodeId c2,
                   double ron, double roff, double vt, double vh)
    : name_(std::move(name)), nodes_{n1, n2, c1, c2},
      ron_(ron), roff_(roff), vt_(vt), vh_(vh) {}

double VCSwitch::conductance(double vctrl) const {
    // Smooth transition using tanh
    // G = (1/Ron + 1/Roff)/2 + (1/Ron - 1/Roff)/2 * tanh((vctrl - vt) / vh)
    if (vh_ <= 0.0) {
        // Hard switch
        return (vctrl > vt_) ? (1.0 / ron_) : (1.0 / roff_);
    }
    double g_on = 1.0 / ron_;
    double g_off = 1.0 / roff_;
    double t = std::tanh((vctrl - vt_) / vh_);
    return 0.5 * (g_on + g_off) + 0.5 * (g_on - g_off) * t;
}

void VCSwitch::stamp_pattern(StampPattern& out) const {
    out.entries.emplace_back(nodes_[0], nodes_[0]); out.entries.emplace_back(nodes_[0], nodes_[1]);
    out.entries.emplace_back(nodes_[0], nodes_[2]); out.entries.emplace_back(nodes_[0], nodes_[3]);
    out.entries.emplace_back(nodes_[1], nodes_[0]); out.entries.emplace_back(nodes_[1], nodes_[1]);
    out.entries.emplace_back(nodes_[1], nodes_[2]); out.entries.emplace_back(nodes_[1], nodes_[3]);
}

void VCSwitch::eval(const OperatingPoint& op, DeviceContribution& out) const {
    out.f.assign(2, 0.0);
    out.jac.assign(8, 0.0);
    double vc = 0.0;
    if (nodes_[2] < op.v.size()) vc += op.v[nodes_[2]];
    if (nodes_[3] < op.v.size()) vc -= op.v[nodes_[3]];
    double g = conductance(vc);
    double v = 0.0;
    if (nodes_[0] < op.v.size()) v += op.v[nodes_[0]];
    if (nodes_[1] < op.v.size()) v -= op.v[nodes_[1]];
    double i = g * v;
    out.f[0] = i;
    out.f[1] = -i;
    out.jac[0] = g;    out.jac[1] = -g;   // dI/dV(n1), dI/dV(n2)
    out.jac[4] = -g;   out.jac[5] = g;
    // dG/dVctrl contribution (nonlinear Jacobian to ctrl nodes)
    if (vh_ > 0.0) {
        double g_on = 1.0 / ron_;
        double g_off = 1.0 / roff_;
        double sech2 = 1.0 - std::tanh((vc - vt_) / vh_) * std::tanh((vc - vt_) / vh_);
        double dgdv = 0.5 * (g_on - g_off) * sech2 / vh_;
        out.jac[2] = dgdv * v;   out.jac[3] = -dgdv * v;
        out.jac[6] = -dgdv * v;  out.jac[7] = dgdv * v;
    }
}

void VCSwitch::evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
    OperatingPoint dcOp{op.v};
    eval(dcOp, out);
}

} // namespace rfsim
