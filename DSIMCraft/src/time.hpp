#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace dsim {
struct TimeScale {
    uint64_t unit_fs=1000000000000000ULL,precision_fs=1000000000000000ULL;
};
struct ModuleTimeScale {size_t line=0;TimeScale scale;bool directive=false;};
struct TimingConfig {
    TimeScale defaults;
    std::vector<ModuleTimeScale> modules;
    uint64_t declared_precision_fs=0;
    uint64_t global_precision() const;
    TimeScale at(size_t module_line) const;
};
uint64_t parse_time_unit(const std::string&);
TimeScale parse_timescale(const std::string&);
std::string time_unit_name(uint64_t fs);
uint64_t delay_ticks(const std::string& decimal,TimeScale,uint64_t global_fs);
}
