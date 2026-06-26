// bench.cpp — V2-γ C3 性能计数器实现
#include "bench.hpp"

#if defined(_WIN32)
#  define WIN32_LEAN_AND_MEAN
#  include <windows.h>
#  include <psapi.h>
#else
#  include <cstdlib>
#  include <cstdio>
#endif

namespace rfsim {

double currentRssMb() {
#if defined(_WIN32)
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        return static_cast<double>(pmc.PeakWorkingSetSize) / (1024.0 * 1024.0);
    }
    return 0.0;
#else
    // Linux/MSYS: 读 /proc/self/status VmHWM（fallback 0）
    FILE* f = std::fopen("/proc/self/status", "r");
    if (!f) return 0.0;
    char line[256];
    double rss = 0.0;
    while (std::fgets(line, sizeof(line), f)) {
        if (std::sscanf(line, "VmHWM: %lf kB", &rss) == 1) { rss /= 1024.0; break; }
        if (std::sscanf(line, "VmRSS: %lf kB", &rss) == 1) { rss /= 1024.0; /* keep scanning for HWM */ }
    }
    std::fclose(f);
    return rss;
#endif
}

} // namespace rfsim
