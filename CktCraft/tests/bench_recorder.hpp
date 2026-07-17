// bench_recorder.hpp — V2-γ C3 bench JSON 落库
//
// 与 plan0620_v2.md §C3 对齐：每个用例在 solver 调用后把 BenchCounters 写一行 JSON
// 到 build/bench_<timestamp>.json。timestamp 在第一次调用时确定（进程级）。
//
// 用法（在测试体里 solve 完成后）：
//   auto dc = solveDcOp(...);
//   rfsim::test::recordBench("MultiDevice", "EightFingerBalanced", "DC", dc.bench);
//
// 若 RFSIM_BENCH_JSON 未设置，recordBench 为 no-op。
#ifndef RFSIM_TEST_BENCH_RECORDER_HPP
#define RFSIM_TEST_BENCH_RECORDER_HPP

#include "../src/util/bench.hpp"
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <mutex>
#include <string>

namespace rfsim {
namespace test {

namespace bench_detail {
struct BenchState {
    std::mutex m;
    bool firstCall = true;   // 还没写过任何记录
    std::string path;
    bool initialized = false;
};
inline BenchState& state() {
    static BenchState s;
    return s;
}
}

inline const std::string& benchFilePath() {
    auto& s = bench_detail::state();
    if (!s.initialized) {
        const char* dir = std::getenv("RFSIM_BENCH_DIR");
        std::string d = dir ? dir : "build";
        std::time_t now = std::time(nullptr);
        std::tm tm{};
#ifdef _WIN32
        localtime_s(&tm, &now);
#else
        localtime_r(&now, &tm);
#endif
        char ts[32];
        std::strftime(ts, sizeof(ts), "%Y%m%d-%H%M%S", &tm);
        s.path = d + "/bench_" + ts + ".json";
        s.initialized = true;
    }
    return s.path;
}

// 追加一条 case 记录。线程安全。
inline void recordBench(const char* suite, const char* caseName,
                        const char* phase, // "DC" / "HB" / "Shooting"
                        const BenchCounters& c) {
    if (!benchJsonEnabled()) return;
    auto& s = bench_detail::state();
    std::lock_guard<std::mutex> lk(s.m);
    const std::string& path = benchFilePath();
    FILE* f = std::fopen(path.c_str(), s.firstCall ? "w" : "a");
    if (!f) return;
    if (s.firstCall) {
        std::fprintf(f, "[\n");
        s.firstCall = false;
    } else {
        std::fprintf(f, ",\n");
    }
    std::fprintf(f,
        "  {\"suite\":\"%s\",\"case\":\"%s\",\"phase\":\"%s\","
        "\"wall_ms\":%.3f,\"newton_iter\":%u,"
        "\"klu_factor_ms\":%.3f,\"klu_solve_ms\":%.3f,"
        "\"peak_rss_mb\":%.3f}",
        suite, caseName, phase,
        c.wall_ms, c.newton_iter,
        c.klu_factor_ms, c.klu_solve_ms,
        c.peak_rss_mb);
    std::fclose(f);
}

// 进程退出时调用收尾 JSON 数组。若没有任何记录，不创建文件。
inline void finalizeBenchFile() {
    if (!benchJsonEnabled()) return;
    auto& s = bench_detail::state();
    std::lock_guard<std::mutex> lk(s.m);
    if (s.firstCall) return;  // 没写过任何记录
    FILE* f = std::fopen(s.path.c_str(), "a");
    if (!f) return;
    std::fprintf(f, "\n]\n");
    std::fclose(f);
    // 标记已 finalize，避免重复
    s.firstCall = true;
}

// 进程启动时注册 atexit 收尾（inline 变量，C++17 允许多 TU 共享同一实例）
namespace bench_detail {
inline const int _atexitReg = []() {
    if (benchJsonEnabled()) std::atexit(finalizeBenchFile);
    return 0;
}();
}

} // namespace test
} // namespace rfsim

#endif // RFSIM_TEST_BENCH_RECORDER_HPP
