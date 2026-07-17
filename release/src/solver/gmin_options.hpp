#pragma once
#include <cstdint>

namespace rfsim {

// Gmin 旁路与 log-spaced 同伦的统一配置（P1-8）。
//
// 各求解器（DcOp / HbNl / Shooting / TimeStepper）历史上各自维护
// gmin/gminStart/gminSteps 三个字段，语义虽相同但散落多处，容易出现：
//   1. 不同模块对 "gminSteps==0" 的解读分叉（DcOp 默认开同伦，
//      其余默认关）；
//   2. 后续若引入更多调度参数（如对数底、加速因子）需在四个
//      结构里重复添加；
//   3. 调用方在不同 *Options 之间复制粘贴时遗漏字段。
//
// 引入此共享子结构后，调用方写 `opts.gmin.gmin / opts.gmin.gminStart /
// opts.gmin.gminSteps`，并在每个 *Options 通过聚合初始化覆写默认值
// 以保留各模块的历史默认行为（见对应头文件的注释）。
struct GminOptions {
    // 目标 gmin（最小值）。所有求解器最终回到此值。
    double gmin = 1e-12;

    // log-spaced 同伦起点（仅当 gminSteps>0 时使用）。
    double gminStart = 1e-2;

    // 同伦级数。
    //   0 = 不启用同伦，单点 schedule={gmin}（零开销，与未启用前完全一致）；
    //   N>0 = log-spaced 从 gminStart 衰减到 gmin，共 N+1 个 gmin 取值。
    // 注意：调度必须只依赖此结构（不依赖 trial 状态/时间步），
    // 否则会破坏 FD 雅可比一致性（参见 shooting.cpp 的设计注释）。
    std::uint32_t gminSteps = 0;
};

} // namespace rfsim
