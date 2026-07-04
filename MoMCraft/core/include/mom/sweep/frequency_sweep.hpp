// =====================================================================
// mom/sweep/frequency_sweep.hpp —— 扫频配置与频点生成
//
// 设计原则（plan0627.md §3）：扫频按用户指定频点【逐点】精确求解，
// 不做任何插值/降阶重构（AWE 等留作后续工具链）。
// 支持：线性分布、对数分布；C++ 与 Python 共用同一实现。
// =====================================================================
#pragma once

#include "mom/common/types.hpp"
#include <vector>
#include <stdexcept>
#include <string>

namespace mom {

enum class SweepScale {
    Linear,   // scale="lin"
    Log,      // scale="log"
};

// 描述一次扫频：[start, stop] 上 count 个频点（单位 Hz）。
// count==1 时返回 {start}。
struct FrequencySweep {
    Real   start = 1.0e6;      // Hz
    Real   stop  = 1.0e9;      // Hz
    Size   count = 201;
    SweepScale scale = SweepScale::Linear;

    FrequencySweep() = default;
    FrequencySweep(Real start_Hz, Real stop_Hz, Size count_, SweepScale sc)
        : start(start_Hz), stop(stop_Hz), count(count_), scale(sc) {
        validate();
    }

    // 健壮性检查（对数扫频要求 start>0）
    void validate() const {
        if (!(stop >= start) || count == 0)
            throw std::invalid_argument(
                "FrequencySweep: stop>=start 且 count>0 必须满足");
        if (scale == SweepScale::Log && !(start > 0.0))
            throw std::invalid_argument(
                "FrequencySweep: 对数扫频要求 start>0");
    }

    // 生成本次扫频的全部频点（Hz）。
    std::vector<Real> frequencies() const;
};

// 将字符串（"lin"/"log"，大小写不敏感）转为 SweepScale。
SweepScale parse_scale(const std::string& s);

} // namespace mom
