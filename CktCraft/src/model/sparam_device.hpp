// sparam_device.hpp — N-port S 参数器件
//
// 从 Touchstone .sNp 文件加载 S 参数数据。
// AC 分析：按频率插值 S→Y，stamp N×N 复数 Y 矩阵。
// DC 分析：Y(ω→0) 实部 stamp。
// 瞬态分析：Vector Fitting companion model（Backward-Euler）。
#ifndef RFSIM_MODEL_SPARAM_DEVICE_HPP
#define RFSIM_MODEL_SPARAM_DEVICE_HPP

#include "device_model.hpp"
#include "../sparam/touchstone.hpp"
#include "../sparam/vector_fit.hpp"
#include <string>
#include <vector>

namespace rfsim {

class SParamDevice : public DeviceModel {
public:
    SParamDevice(std::string name, std::vector<NodeId> nodes,
                 const std::string& touchstonePath, double z0 = 50.0);

    // 从已解析的 TouchstoneData 构造（测试 / 内存电路用）
    SParamDevice(std::string name, std::vector<NodeId> nodes, TouchstoneData data);

    // DeviceModel 接口
    [[nodiscard]] const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    [[nodiscard]] bool is_linear() const override { return true; }
    [[nodiscard]] std::string name() const override { return name_; }

    // AC 接口：返回 N×N 复数 Y 矩阵（行优先）
    [[nodiscard]] std::vector<Complex> admittanceMatrix(double omega) const;

    // DC 接口：返回 Y(ω→0) 的实部矩阵（用于 DC stamp）
    [[nodiscard]] std::vector<Complex> dcAdmittanceMatrix() const;

    // Transient 接口: Vector Fitting companion model
    void evalTransient(const TransientOpPoint& op, DeviceContribution& out) const override;
    bool hasTransientState() const override { return true; }
    size_t transientStateSize() const override;
    void initializeTransientState(const std::vector<double>& nodeV) override;
    [[nodiscard]] std::vector<double> getTransientState() const override;
    void setTransientState(const std::vector<double>& state) override;
    void updateTransientState(const TransientOpPoint& op) override;

    [[nodiscard]] uint32_t numPorts() const { return numPorts_; }
    [[nodiscard]] const TouchstoneData& data() const { return sData_; }
    [[nodiscard]] bool vfFitted() const { return vfFitted_; }

private:
    std::string name_;
    std::vector<NodeId> nodes_;
    uint32_t numPorts_ = 0;
    TouchstoneData sData_;

    // Vector Fitting companion model 状态
    // vfPoles_: 公共极点集（所有 Y_ij 共享，保证 companion model 一致）
    // vfResidues_[k]: 第 k 个极点的 N×N 留数矩阵（行优先展平，size = numPorts_^2）
    // vfConstant_: N×N 常数矩阵 D（行优先展平）
    std::vector<std::complex<double>> vfPoles_;
    std::vector<std::vector<std::complex<double>>> vfResidues_;
    std::vector<std::complex<double>> vfConstant_;
    bool vfFitted_ = false;

    // companion model 状态变量（实数存储）。
    // 布局: [pole_idx * numPorts_ + port_idx]，大小 = vfPoles_.size() * numPorts_。
    // 对复数极点对，与其共轭对的状态在 eval/update 中合并取实部。
    std::vector<double> state_;

    void initVectorFitting();
};

} // namespace rfsim

#endif // RFSIM_MODEL_SPARAM_DEVICE_HPP
