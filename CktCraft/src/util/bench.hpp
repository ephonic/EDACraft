// bench.hpp — V2-γ C3 性能计数器
//
// 由 RFSIM_BENCH_JSON=1 启用。每个 solver (DC OP / HB-NL / Shooting) 在其 Result
// 内嵌一个 BenchCounters 字段，并在求解过程中填充：
//   wall_ms         整个 solve() 的墙钟时间（毫秒）
//   newton_iter     Newton 外层迭代总数
//   klu_factor_ms   KLU factorize 累计墙钟（毫秒）
//   klu_solve_ms    KLU solve 累计墙钟（毫秒）
//   peak_rss_mb     求解结束时的进程 RSS（MB，Windows GetProcessMemoryInfo）
//
// GoogleTest fixture 在 TearDown 读 RFSIM_BENCH_JSON；若开启，把当前 case 名 +
// BenchCounters 写一行 JSON 到 build/bench_<timestamp>.json。
//
// 计时器走 std::chrono::steady_clock；RSS 走 Windows API（其它平台 fallback 0）。
#ifndef RFSIM_UTIL_BENCH_HPP
#define RFSIM_UTIL_BENCH_HPP

#include <chrono>
#include <cstdint>

namespace rfsim {

struct BenchCounters {
    double wall_ms       = 0.0;
    uint32_t newton_iter = 0;
    double klu_factor_ms = 0.0;
    double klu_solve_ms  = 0.0;
    double peak_rss_mb   = 0.0;
};

// 是否启用 bench 输出（RFSIM_BENCH_JSON=1）。一次性查询，避免每次 getenv。
inline bool benchJsonEnabled() {
#ifdef _MSC_VER
    static bool v = [] {
        const char* s = std::getenv("RFSIM_BENCH_JSON");
        return s && (s[0]=='1' || s[0]=='t' || s[0]=='T');
    }();
    return v;
#else
    static bool v = [] {
        const char* s = std::getenv("RFSIM_BENCH_JSON");
        return s && (s[0]=='1' || s[0]=='t' || s[0]=='T');
    }();
    return v;
#endif
}

// 便捷：steady_clock 计时器
struct SteadyTimer {
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
    double elapsedMs() const {
        auto t1 = std::chrono::steady_clock::now();
        return std::chrono::duration<double, std::milli>(t1 - t0).count();
    }
    void reset() { t0 = std::chrono::steady_clock::now(); }
};

// Windows RSS 采样（非 Windows 返回 0）
double currentRssMb();

} // namespace rfsim

#endif // RFSIM_UTIL_BENCH_HPP
