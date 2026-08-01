// device_model.hpp — 器件模型抽象基类与装配接口
//
// 对应 plan.md §4.3 / §5。
// FlatDevice 只是解析出的纯数据；DeviceModel 是带行为的模型 wrapper。
// 内置线性器件(R/L/C/V/I)直接实现本接口；半导体器件由 Verilog-A
// 生成模型（model/generated/*_gen.cpp，rfsim_codegen 产出）实现。
// （历史 OsdiModel/OpenVAF 路径已移除，生成模型为唯一半导体器件路径。）
//
// 装配语义（DC/MNA 视角，HB 频域推广见 §4.4）：
//   - 线性导纳器件：向 G 矩阵 stamp 导纳，向 RHS stamp 源贡献
//   - 非线性器件：在给定工作点计算 I(V) 与 dI/dV，向 J、F 贡献
#ifndef RFSIM_MODEL_DEVICE_MODEL_HPP
#define RFSIM_MODEL_DEVICE_MODEL_HPP

#include "../rfsim.hpp"
#include "../circuit/circuit.hpp"
#include "../assembly/matrix.hpp"
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

namespace rfsim {

// 瞬态积分方法
enum class IntegrationMethod {
    BackwardEuler,
    Trapezoidal
};

// 矩阵 stamp 模式：描述该器件对全局矩阵的非零位置 (row, col)。
// 装配前用于预分配稀疏矩阵存储，避免动态插入。
struct StampPattern {
    // (行, 列) 对，均用 NodeId（0=地）；电压源等额外行由装配层扩展
    std::vector<std::pair<NodeId, NodeId>> entries;
};

// 工作点：各节点的电压（索引对齐 DeviceModel 实例的 nodes()）。
// 非线性迭代时由求解层填入当前猜测值。
struct OperatingPoint {
    std::vector<double> v;   // 节点电压，v[i] 对应 nodes()[i]
};

// 瞬态工作点：当前步电压 + 上一时刻电压 + 时间信息
struct TransientOpPoint {
    std::vector<double> v;       // 当前时刻节点电压
    std::vector<double> v_prev;  // 上一时刻节点电压（与 v 同维度）
    double time = 0.0;           // 当前时刻 t_n
    double dt = 0.0;             // 步长
    IntegrationMethod method = IntegrationMethod::BackwardEuler;
};

// 装配贡献：器件对全局残差 F 与雅可比 J 的贡献。
// DC/MNA 下：F = -I(注入节点的电流)，J = dI/dV（导纳矩阵）。
// 求解层把 contribution 累加到全局矩阵/向量对应位置。
struct DeviceContribution {
    // 残差贡献：对每个节点 k，电流注入 f[k]（A，流入节点为正约定）
    std::vector<double> f;
    // 雅可比贡献：df[i]/dv[j]，对齐 stamp 模式的 entries 顺序
    std::vector<double> jac;
};

// 器件模型 wrapper 抽象基类
class DeviceModel {
public:
    virtual ~DeviceModel() = default;

    // 该实例连接的节点列表（对齐 OperatingPoint/DeviceContribution 的索引）
    [[nodiscard]] virtual const std::vector<NodeId>& nodes() const = 0;

    // 矩阵非零模式，供装配预分配
    virtual void stamp_pattern(StampPattern& out) const = 0;

    // V3-L0: pattern 固化后，器件从 SparseMatrix 取出自己每个 jacobian entry
    // 对应的 values_ 指针，存入 stampPtrs_。后续 stampValues() 直接写指针 O(1)。
    // numExternalNodes: 外部可见节点数上限（内部节点 NodeId > numExternalNodes
    // 的 entry 指针为 nullptr，不进外部 MNA）。
    // 默认实现：空（线性器件在 assembler 内联 stamp，不走此路径）。
    virtual void bindStampPtrs(SparseMatrix& G, uint32_t numExternalNodes) {
        (void)G; (void)numExternalNodes;
    }

    // V3-L0: 用预存的指针直接 stamp 雅可比值到 SparseMatrix。
    // stampPtrs_ 绑定到特定 G 对象；若当前 G 不同（如 time_stepper 的局部 sys），
    // stampPtrsBound() 返回 false，回退到 add() 路径。
    [[nodiscard]] bool stampPtrsBound(const SparseMatrix& G) const {
        return !stampPtrs_.empty() && boundG_ == &G;
    }
    void stampValuesViaPtrs(const std::vector<double>& jac) {
        for (size_t e = 0; e < stampPtrs_.size() && e < jac.size(); ++e) {
            if (stampPtrs_[e]) *stampPtrs_[e] += jac[e];
        }
    }
    void clearStampPtrs() { stampPtrs_.clear(); boundG_ = nullptr; }

    // 在给定工作点评估贡献（残差 + 雅可比）。
    // 线性器件可忽略 op 中的值（导纳恒定）；非线性器件依赖 op。
    // 返回的 f/jac 维度对齐 nodes() 与 stamp_pattern。
    virtual void eval(const OperatingPoint& op, DeviceContribution& out) const = 0;

    // ---- Bypass 机制 ----
    // 当端电压在多次 Newton 迭代间变化小于 bypassTol 时，跳过 eval，
    // 复用上一次的残差和雅可比。对非线性器件可大幅加速收敛后段。
    // 默认开启，bypassTol=1e-9。设 RFSIM_BYPASS_TOL=0 禁用。
    [[nodiscard]] bool bypassEnabled() const {
        static const double tol = []() {
            const char* s = std::getenv("RFSIM_BYPASS_TOL");
            if (s) { double v = std::atof(s); if (v >= 0) return v; }
            return 1e-9;
        }();
        return tol > 0.0;
    }
    [[nodiscard]] double bypassTol() const {
        static const double tol = []() {
            const char* s = std::getenv("RFSIM_BYPASS_TOL");
            if (s) { double v = std::atof(s); if (v >= 0) return v; }
            return 1e-9;
        }();
        return tol;
    }
    // 检查端电压是否在 bypass 容差内。返回 true 则可 bypass。
    bool checkBypass(const OperatingPoint& op) const {
        if (!bypassEnabled() || !bypassCached_) return false;
        const auto& nds = nodes();
        if (lastTermV_.size() != nds.size()) return false;
        for (size_t k = 0; k < nds.size(); ++k) {
            double vk = (nds[k] < op.v.size()) ? op.v[nds[k]] : 0.0;
            double scale = std::max(std::fabs(lastTermV_[k]), 1.0);
            if (std::fabs(vk - lastTermV_[k]) > bypassTol() * scale) return false;
        }
        return true;
    }
    // 缓存 eval 结果（在 eval 完成后调用）
    void cacheEvalResult(const OperatingPoint& op, const DeviceContribution& out) const {
        const auto& nds = nodes();
        lastTermV_.resize(nds.size());
        for (size_t k = 0; k < nds.size(); ++k)
            lastTermV_[k] = (nds[k] < op.v.size()) ? op.v[nds[k]] : 0.0;
        lastF_ = out.f;
        lastJac_ = out.jac;
        bypassCached_ = true;
    }
    // 返回缓存的 eval 结果（bypass 命中时调用）
    void loadCachedResult(DeviceContribution& out) const {
        out.f = lastF_;
        out.jac = lastJac_;
    }
    // 清除 bypass 缓存（gmin 变化等需要强制重新 eval 时调用）
    void invalidateBypassCache() { bypassCached_ = false; }
    [[nodiscard]] bool evalBypassed() const { return bypassCached_ && lastTermV_.empty() == false; }

    // 瞬态评估：在 t_n 时刻 stamp companion model。
    // 默认实现退化为 DC eval（纯电阻/源器件）。
    // 动态器件（C/L/生成模型）需要重载以处理 v_prev / dt / method。
    virtual void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const {
        OperatingPoint dcOp{op.v};
        eval(dcOp, out);
    }

    // 瞬态状态管理。动态器件在积分前初始化状态，每步后更新状态。
    [[nodiscard]] virtual bool hasTransientState() const { return false; }
    [[nodiscard]] virtual size_t transientStateSize() const { return 0; }
    virtual void initializeTransientState(const std::vector<double>& nodeV) { (void)nodeV; }
    [[nodiscard]] virtual std::vector<double> getTransientState() const { return {}; }
    virtual void setTransientState(const std::vector<double>& s) { (void)s; }
    virtual void updateTransientState(const TransientOpPoint& op) { (void)op; }

    // 是否线性（导纳不随工作点变化）。线性器件在 Newton 迭代中只需评估一次。
    [[nodiscard]] virtual bool is_linear() const = 0;

    // ---- HB 时域采样评估接口（谐波平衡非线性装配用）----
    // HB 时域电压 clamp（±V）：防止 Newton 探索阶段极端电压使模型 eval
    // 溢出，同时保持 FFT 输入周期性（不产生方波 artifact）。
    static constexpr double kHbVoltClamp = 20.0;

    // 一次遍历完成 HB 时域采样评估（每采样点一次 eval，同时取电流与雅可比，
    // 避免 f/jac 分离接口造成的双倍 eval 开销——BSIM4 eval 是 HB 装配主开销）。
    // timeV[globalNode][sample]：一个周期内 N 个等距采样点的节点电压波形
    // （含地节点行，timeV[0] 恒为 0）。
    // outCurrents[s][localNode]：第 s 个采样点注入各本地节点的阻性电流 I
    // （符号约定与 eval() 的 out.f 一致，装配侧按 F += -(I + jωQ) 累加）。
    // outCharges[s][localNode]：第 s 个采样点各本地节点的电荷 Q（无电荷模型返回零）。
    // outJac[s][e] / outJacReact[s][e]：dI/dV 与 dQ/dV，e 严格对齐
    // stamp_pattern() 的 entries 顺序（包括触地 entry，装配侧自行跳过）。
    // 默认实现：逐采样点调用 eval()（纯阻性；电荷与电抗雅可比为空）。
    virtual void evalHb(const std::vector<std::vector<double>>& timeV,
                        std::vector<std::vector<double>>& outCurrents,
                        std::vector<std::vector<double>>& outCharges,
                        std::vector<std::vector<double>>& outJac,
                        std::vector<std::vector<double>>& outJacReact) const {
        const size_t N = timeV.empty() ? 0 : timeV[0].size();
        const auto& nds = nodes();
        const size_t nL = nds.size();
        StampPattern pat;
        stamp_pattern(pat);
        const size_t nE = pat.entries.size();
        outCurrents.assign(N, std::vector<double>(nL, 0.0));
        outCharges.assign(N, std::vector<double>(nL, 0.0));
        outJac.assign(N, std::vector<double>(nE, 0.0));
        outJacReact.clear();  // 默认无电荷模型
        OperatingPoint op;
        op.v.assign(timeV.size(), 0.0);
        DeviceContribution contrib;
        for (size_t s = 0; s < N; ++s) {
            // 只填器件涉及节点的电压（eval 只读 nodes() 对应位置），
            // 避免大电路下每采样点复制整条全局电压向量
            bool bad = false;
            for (NodeId g : nds) {
                if (g >= timeV.size()) continue;
                double vv = timeV[g][s];
                if (std::isnan(vv) || std::isinf(vv)) { bad = true; break; }
                op.v[g] = (vv > kHbVoltClamp) ? kHbVoltClamp
                        : (vv < -kHbVoltClamp ? -kHbVoltClamp : vv);
            }
            if (bad) continue;  // 该采样点保持零贡献
            eval(op, contrib);
            for (size_t i = 0; i < nL && i < contrib.f.size(); ++i)
                outCurrents[s][i] = contrib.f[i];
            for (size_t e = 0; e < nE && e < contrib.jac.size(); ++e)
                outJac[s][e] = contrib.jac[e];
        }
    }

    // 设置器件温度（K）。供 $temperature/$vt 类模型使用；
    // 不依赖温度的模型忽略。生成模型即时生效。
    // 调用方：device_factory（env.temperature）。
    virtual void setTemperature(double tempK) { (void)tempK; }

    // 分配内部节点（Verilog-A 生成模型等带内部网络的器件）。
    // factory 在构造后调用；internalNodeBase 递增（in/out）。
    // 默认无内部节点。注意：生成模型在调用前内部节点全为 0（地），
    // 模型处于退化状态——直接使用的测试代码必须手动调用。
    virtual void allocateInternalNodes(NodeId& internalNodeBase) {
        (void)internalNodeBase;
    }

    // 返回该器件需要的内部节点数（基于当前参数设置）。
    // factory 在分配前调用此方法做节点数扫描，然后调用 allocateInternalNodes。
    // 默认 0（无内部节点）。
    [[nodiscard]] virtual uint32_t numInternalNodes() const { return 0; }

    // 实例名（带层级前缀），用于诊断与输出
    [[nodiscard]] virtual std::string name() const = 0;

    // ---- 器件级控制接口（原 OSDI 专属，现提升为通用虚方法）----

    // 重置模型内部 limiting 状态（跨 Newton 迭代前调用）。默认空操作。
    virtual void resetLimiting() {}

    // 使能/禁用 eval bypass cache。默认空操作。
    virtual void setMrAutoTune(bool enable) { (void)enable; }

    // 清除 eval 缓存（gmin 步间、状态恢复时调用）。默认空操作。
    virtual void invalidateEvalCache() {}

    // Newton 步开始时重置 resid-only 标记。默认空操作。
    virtual void beginNewtonStep() {}

    // Multi-rate 速率比设置。默认空操作（不支持 multi-rate）。
    virtual void setRateRatio(uint32_t K) { (void)K; }
    virtual void setMrRelTol(double tol) { (void)tol; }

protected:
    // V3-L0: 预存的 CSR values_ 指针，对齐 stamp_pattern 的 entries 顺序。
    // bindStampPtrs 时由器件子类填入。stampValuesViaPtrs 直接写 *ptr += val。
    // boundG_ 记录绑定的 G 对象——若 assembleTransient 用不同 G（如 time_stepper
    // 的局部 sys），stampPtrsBound() 返回 false，回退到 add() 路径。
    std::vector<double*> stampPtrs_;
    const SparseMatrix* boundG_ = nullptr;
    // Bypass cache state (mutable: eval is const but modifies cache)
    mutable bool bypassCached_ = false;
    mutable std::vector<double> lastTermV_;
    mutable std::vector<double> lastF_;
    mutable std::vector<double> lastJac_;
};

} // namespace rfsim

#endif // RFSIM_MODEL_DEVICE_MODEL_HPP
