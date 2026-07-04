// =====================================================================
// mom/port/port.hpp —— 端口激励、S 参数提取、去嵌
//
// 阶段 3 实现：
//   - delta-gap / 磁流环激励，在参考面定义端口
//   - 逐端口激励 → 解 A-EFIE → 端口电压/电流 → Z_port
//   - S = (Z_port - Z0 I)(Z_port + Z0 I)^{-1}
//   - 去嵌：参考面移动 / renormalization
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <string>

namespace mom::port {

struct Port {
    std::string name;
    Real  z0 = 50.0;     // 参考阻抗 (ohm)
    // TODO 阶段3：位置、所在层、参考面
};

} // namespace mom::port
