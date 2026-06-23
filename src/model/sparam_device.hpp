// sparam_device.hpp — N-port S 参数器件
//
// 从 Touchstone .sNp 文件加载 S 参数数据。
// AC 分析：按频率插值 S→Y，stamp N×N 复数 Y 矩阵。
// DC 分析：Y(ω→0) 实部 stamp。
// 瞬态分析：VF companion model（Phase 4 实现）。
#ifndef RFSIM_MODEL_SPARAM_DEVICE_HPP
#define RFSIM_MODEL_SPARAM_DEVICE_HPP

#include "device_model.hpp"
#include "../sparam/touchstone.hpp"
#include <string>
#include <vector>

namespace rfsim {

class SParamDevice : public DeviceModel {
public:
    SParamDevice(std::string name, std::vector<NodeId> nodes,
                 const std::string& touchstonePath, double z0 = 50.0);

    // 从已解析的 TouchstoneData 构造
    SParamDevice(std::string name, std::vector<NodeId> nodes, TouchstoneData data);

    // DeviceModel 接口
    [[nodiscard]] const std::vector<NodeId>& nodes() const override { return nodes_; }
    void stamp_pattern(StampPattern& out) const override;
    void eval(const OperatingPoint& op, DeviceContribution& out) const override;
    [[nodiscard]] bool is_linear() const override { return true; }
    [[nodiscard]] std::string name() const override { return name_; }

    // AC 接口：返回 N×N 复数 Y 矩阵（行优先）
    [[nodiscard]] std::vector<Complex> admittanceMatrix(double omega) const;

    [[nodiscard]] uint32_t numPorts() const { return numPorts_; }
    [[nodiscard]] const TouchstoneData& data() const { return sData_; }

private:
    std::string name_;
    std::vector<NodeId> nodes_;
    uint32_t numPorts_ = 0;
    TouchstoneData sData_;
};

} // namespace rfsim

#endif // RFSIM_MODEL_SPARAM_DEVICE_HPP
