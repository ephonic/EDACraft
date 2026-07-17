// mor_wrapper.h — MOR (Model Order Reduction) 集成接口
//
// 把 amor RC 互连线降阶集成到仿真器流程中：
//   仿真前（.options mor=on 时）→ amor 读网表 → 分区 → 降阶 → 输出简化网表 → 仿真器用简化网表。
//
// amor 的 run(input, output) 做完整流程：parse → partition → reduction → dump。
// 本 wrapper 封装为 rfsim 命名空间的调用入口。
#ifndef RFSIM_MOR_WRAPPER_H
#define RFSIM_MOR_WRAPPER_H

#include <string>

namespace rfsim {

// MOR 降阶选项
struct MorOptions {
    int maxBlockSize = 35;    // amor 最大分区端口数
    double relativeTol = 1e-4; // 分区相对容差
};

// 对输入网表做 MOR 降阶，输出简化网表到 reducedPath。
// 返回 true 若降阶成功（reducedPath 可用于后续仿真）。
// 失败返回 false（调用方用原网表）。
bool runMorReduction(const std::string& inputPath,
                     const std::string& reducedPath,
                     const MorOptions& opts = {});

} // namespace rfsim

#endif // RFSIM_MOR_WRAPPER_H
