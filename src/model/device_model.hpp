// device_model.hpp — 器件模型抽象基类与装配接口
//
// 对应 plan.md §4.3 / §5。
// FlatDevice 只是解析出的纯数据；DeviceModel 是带行为的模型 wrapper。
// 内置线性器件(R/L/C/V/I)直接实现本接口；半导体器件由 OsdiModel
// (plan.md §4.3.3) 包装 OpenVAF/OSDI 评估例程实现。
//
// 装配语义（DC/MNA 视角，HB 频域推广见 §4.4）：
//   - 线性导纳器件：向 G 矩阵 stamp 导纳，向 RHS stamp 源贡献
//   - 非线性器件：在给定工作点计算 I(V) 与 dI/dV，向 J、F 贡献
#ifndef RFSIM_MODEL_DEVICE_MODEL_HPP
#define RFSIM_MODEL_DEVICE_MODEL_HPP

#include "../rfsim.hpp"
#include "../circuit/circuit.hpp"
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

    // 在给定工作点评估贡献（残差 + 雅可比）。
    // 线性器件可忽略 op 中的值（导纳恒定）；非线性器件依赖 op。
    // 返回的 f/jac 维度对齐 nodes() 与 stamp_pattern。
    virtual void eval(const OperatingPoint& op, DeviceContribution& out) const = 0;

    // 瞬态评估：在 t_n 时刻 stamp companion model。
    // 默认实现退化为 DC eval（纯电阻/源器件）。
    // 动态器件（C/L/OSDI）需要重载以处理 v_prev / dt / method。
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

    // 实例名（带层级前缀），用于诊断与输出
    [[nodiscard]] virtual std::string name() const = 0;
};

} // namespace rfsim

#endif // RFSIM_MODEL_DEVICE_MODEL_HPP
