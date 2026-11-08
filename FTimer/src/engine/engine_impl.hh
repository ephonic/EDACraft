#pragma once

#include <memory>
#include <array>
#include <string>
#include <string_view>
#include <vector>

#include "time_engine/engine.hh"
#include "time_engine/types.hh"
#include "edacraft/core/ids.hpp"
#include "edacraft/core/liberty_db.hpp"

#include "dcalc/csm_dcalc.hh"
#include "incremental/dirty_tracker.hh"
#include "parasitics/timing_parasitics.hh"
#include "sdc/resolved_constraints.hh"

namespace te {

class Network;
class TimingGraph;
class NldmDelayCalc;
class AweDelayCalc;

struct TimingEngine::Impl {
    std::unique_ptr<Network> network;
    edacraft::core::LibertyDB owned_liberty;
    edacraft::core::LibertyDB* liberty = &owned_liberty;
    std::unique_ptr<TimingGraph> graph;
    std::unique_ptr<TimingParasiticDB> parasitics;
    std::unique_ptr<ResolvedConstraintSet> sdc;

    std::unique_ptr<NldmDelayCalc> gate_calc;
    std::unique_ptr<CsmDelayCalc> csm_calc;
    std::unique_ptr<AweDelayCalc> wire_calc;
    DirtyTracker dirty_tracker;

    int thread_count = 1;
    float voltage = 1.0f;
    bool power_voltage_explicit = false;
    bool power_clocked_propagation = true;
    float temperature = 25.0f;
    bool verbose = false;
    struct PowerActivity { double rate=0, probability=.5; };
    std::unordered_map<uint32_t,PowerActivity> power_activity;
    struct InternalPowerActivity { double rate=0, rise_ratio=.5; };
    std::unordered_map<uint64_t,InternalPowerActivity> power_internal_activity;
    std::string preferred_top_name;
    std::vector<uint32_t> last_dirty_vertices;
    std::unordered_map<uint32_t, edacraft::core::PinHandle> pin_bindings;
    std::unordered_map<uint32_t, PinId> reverse_pin_bindings;
    std::unordered_map<uint32_t, std::array<float, 8>> clock_pin_data_paths;

    edacraft::core::LibertyDB& use_owned_liberty() {
        liberty = &owned_liberty;
        return owned_liberty;
    }

    void use_external_liberty(edacraft::core::LibertyDB& external) {
        liberty = &external;
    }

    Impl()
        : network(std::make_unique<Network>()),
          graph(std::make_unique<TimingGraph>()),
          parasitics(std::make_unique<TimingParasiticDB>()),
          sdc(std::make_unique<ResolvedConstraintSet>()),
          gate_calc(std::make_unique<NldmDelayCalc>()),
          csm_calc(std::make_unique<CsmDelayCalc>()),
          wire_calc(std::make_unique<AweDelayCalc>()),
          dirty_tracker(*graph) {}
};

} // namespace te
