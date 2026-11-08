#include "time_engine/engine.hh"

#include <stdexcept>

namespace te {

void ScenarioManager::add_scenario(ScenarioSpec spec) {
    if (spec.name.empty())
        throw std::invalid_argument("MCMM scenario name must not be empty");
    specs_.push_back(std::move(spec));
}

void ScenarioManager::clear() {
    specs_.clear();
}

std::vector<ScenarioResult> ScenarioManager::analyze() const {
    std::vector<ScenarioResult> results;
    results.reserve(specs_.size());
    for (const auto& spec : specs_) {
        try {
            TimingEngine engine;
            engine.set_pvt(spec.voltage, spec.temperature);
            for (const auto& liberty : spec.liberty_files)
                if (!liberty.empty()) engine.read_liberty(liberty);
            if (spec.verilog_file.empty())
                throw std::invalid_argument("missing Verilog file");
            engine.read_verilog(spec.verilog_file);
            if (!spec.spef_file.empty()) engine.read_spef(spec.spef_file);
            if (!spec.sdc_file.empty()) engine.read_sdc(spec.sdc_file);
            engine.link_design();
            engine.update_timing();
            results.push_back({spec.name, spec.voltage, spec.temperature,
                engine.worst_slack(MinMax::Max, TimingCheckKind::Data),
                engine.worst_slack(MinMax::Min, TimingCheckKind::Data),
                engine.timing_generation()});
        } catch (const std::exception& e) {
            throw std::runtime_error("MCMM scenario '" + spec.name + "': " + e.what());
        }
    }
    return results;
}

} // namespace te
