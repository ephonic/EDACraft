// =====================================================================
// mom/sweep/frequency_sweep.cpp
// =====================================================================
#include "mom/sweep/frequency_sweep.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>

namespace mom {

std::vector<Real> FrequencySweep::frequencies() const {
    validate();
    std::vector<Real> f;
    f.reserve(count);

    if (count == 1) {
        f.push_back(start);
        return f;
    }

    // count>=2：在 [start, stop] 上等间距（含两端点）。
    const Real denom = static_cast<Real>(count - 1);
    switch (scale) {
        case SweepScale::Linear: {
            for (Size i = 0; i < count; ++i) {
                const Real t = static_cast<Real>(i) / denom;
                f.push_back(start + t * (stop - start));
            }
            break;
        }
        case SweepScale::Log: {
            // 对数刻度：f_i = start * (stop/start)^(i/(count-1))
            const Real lr_start = std::log(start);
            const Real lr_stop  = std::log(stop);
            for (Size i = 0; i < count; ++i) {
                const Real t = static_cast<Real>(i) / denom;
                f.push_back(std::exp(lr_start + t * (lr_stop - lr_start)));
            }
            break;
        }
    }

    // 数值护栏：首尾严格等于 start/stop，避免浮点累积误差。
    f.front() = start;
    f.back()  = stop;
    return f;
}

SweepScale parse_scale(const std::string& s) {
    std::string lower(s.size(), '\0');
    std::transform(s.begin(), s.end(), lower.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (lower == "log" || lower == "logarithmic")
        return SweepScale::Log;
    if (lower == "lin" || lower == "linear" || lower.empty())
        return SweepScale::Linear;
    throw std::invalid_argument("parse_scale: 未知刻度 '" + s + "'，应为 'lin' 或 'log'");
}

} // namespace mom
