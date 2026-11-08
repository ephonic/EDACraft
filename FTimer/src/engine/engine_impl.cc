#include "engine_impl.hh"
#include "concurrent/parallel_for.hh"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <limits>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#if defined(__GLIBC__)
#include <malloc.h>
#endif

#include "edacraft/core/design_db.hpp"
#include "edacraft/core/liberty_db.hpp"
#include "edacraft/core/sdc_parser.hpp"
#include "edacraft/core/timing_db.hpp"
#include "sdc/core_sdc_applier.hh"
#include "sdc/netlist_collections.hh"
#include "network/gate_view_adapter.hh"
#include "network/network.hh"
#include "liberty/liberty_binary.hh"
#include "liberty/liberty_input_format.hh"
#include "liberty/core_liberty_utils.hh"
#include "parser/liberty_parser.hh"
#include "parser/verilog_parser_adapter.hh"
#include "parser/spef_parser.hh"
#include "graph/timing_graph.hh"
#include "parasitics/timing_parasitics.hh"
#include "sdc/resolved_constraints.hh"
#include "search/arrival_propagator.hh"
#include "search/required_propagator.hh"
#include "search/path_collector.hh"
#include "dcalc/nldm_dcalc.hh"
#include "dcalc/awe_dcalc.hh"
#include "storage/mmap_store.hh"

namespace te {

namespace ec = edacraft::core;

namespace {

// SDC collection selectors use Tcl glob semantics. Treating a selector such
// as `pad_cpu_rst_b*` as an exact name silently drops every bit of a bus and
// makes timing depend on elaboration names. Brackets remain literal because
// Verilog bit names contain them; C906 needs only `*` and `?` here.
bool sdc_glob_match(std::string_view pattern, std::string_view value) {
    size_t p = 0, v = 0, star = std::string_view::npos, retry = 0;
    while (v < value.size()) {
        if (p < pattern.size() && pattern[p] == '?') { ++p; ++v; continue; }
        if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            retry = v;
            continue;
        }
        if (p < pattern.size() && pattern[p] == value[v]) { ++p; ++v; continue; }
        if (star != std::string_view::npos) {
            p = star + 1;
            v = ++retry;
            continue;
        }
        return false;
    }
    while (p < pattern.size() && pattern[p] == '*') ++p;
    return p == pattern.size();
}

bool env_flag_enabled(const char* name) {
    const char* value = std::getenv(name);
    if (!value) return false;
    std::string text(value);
    for (char& ch : text) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    return text == "1" || text == "true" || text == "yes" || text == "on";
}

float receiver_cap_blend_factor() {
    if (env_flag_enabled("FSYN_TIMING_USE_RECEIVER_CAP_AS_LOAD")) {
        return 1.0f;
    }
    const char* value = std::getenv("FSYN_TIMING_RECEIVER_CAP_BLEND");
    if (!value || !*value) return 1.0f;
    char* end = nullptr;
    float blend = std::strtof(value, &end);
    if (end == value || !std::isfinite(blend)) return 1.0f;
    if (blend < 0.0f) return 0.0f;
    if (blend > 1.0f) return 1.0f;
    return blend;
}

edacraft::core::Transition to_core_transition(Transition rf) {
    return rf == Transition::Rise
        ? edacraft::core::Transition::Rise
        : edacraft::core::Transition::Fall;
}

edacraft::core::MinMax to_core_min_max(MinMax mm) {
    return mm == MinMax::Min
        ? edacraft::core::MinMax::Min
        : edacraft::core::MinMax::Max;
}

edacraft::core::TimingArcType to_core_arc_type(ec::LibertyTimingType type) {
    using CoreType = edacraft::core::TimingArcType;
    switch (type) {
        case ec::LibertyTimingType::Combinational:
        case ec::LibertyTimingType::LevelSensitive:
        case ec::LibertyTimingType::Preset:
        case ec::LibertyTimingType::Clear:
            return CoreType::Combinational;
        case ec::LibertyTimingType::RisingEdge:
            return CoreType::RisingEdge;
        case ec::LibertyTimingType::FallingEdge:
            return CoreType::FallingEdge;
        case ec::LibertyTimingType::SetupRising:
        case ec::LibertyTimingType::SetupFalling:
            return CoreType::Setup;
        case ec::LibertyTimingType::HoldRising:
        case ec::LibertyTimingType::HoldFalling:
            return CoreType::Hold;
        case ec::LibertyTimingType::RecoveryRising:
        case ec::LibertyTimingType::RecoveryFalling:
            return CoreType::Recovery;
        case ec::LibertyTimingType::RemovalRising:
        case ec::LibertyTimingType::RemovalFalling:
            return CoreType::Removal;
        case ec::LibertyTimingType::Unknown:
            return CoreType::Unknown;
    }
    return CoreType::Unknown;
}

edacraft::core::TimingSense to_core_sense(ec::LibertyTimingSense sense) {
    using CoreSense = edacraft::core::TimingSense;
    switch (sense) {
        case ec::LibertyTimingSense::PositiveUnate:
            return CoreSense::PositiveUnate;
        case ec::LibertyTimingSense::NegativeUnate:
            return CoreSense::NegativeUnate;
        case ec::LibertyTimingSense::NonUnate:
            return CoreSense::NonUnate;
        case ec::LibertyTimingSense::None:
            return CoreSense::None;
    }
    return CoreSense::None;
}

edacraft::core::TimingDelayModel to_core_delay_model(DelayModelSource source) {
    using CoreModel = edacraft::core::TimingDelayModel;
    switch (source) {
        case DelayModelSource::Nldm:
            return CoreModel::Nldm;
        case DelayModelSource::Csm:
            return CoreModel::Csm;
        case DelayModelSource::AwePi:
            return CoreModel::AwePi;
        case DelayModelSource::Lumped:
            return CoreModel::Lumped;
        case DelayModelSource::None:
            return CoreModel::None;
    }
    return CoreModel::None;
}

edacraft::core::PinHandle to_core_pin(
    PinId pin,
    const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr) {
    if (!valid(pin)) return edacraft::core::NULL_PIN;
    if (bindings) {
        auto it = bindings->find(pin.id);
        if (it != bindings->end()) return it->second;
    }
    return edacraft::core::PinHandle{pin.id};
}

uint32_t remap_string(uint32_t id,
                      const ec::StringPool& source,
                      edacraft::core::StringPool& target,
                      std::vector<uint32_t>& cache) {
    if (id == UINT32_MAX) return UINT32_MAX;
    if (id >= cache.size()) cache.resize(id + 1, UINT32_MAX);
    if (cache[id] != UINT32_MAX) return cache[id];
    cache[id] = target.intern(source.view(id));
    return cache[id];
}

ec::NldmTable remap_nldm_table(const ec::NldmTable& table) {
    return table;
}

ec::CsmOutputCurrentTable remap_csm_table(const ec::CsmOutputCurrentTable& table) {
    return table;
}

ec::LibertyPinData remap_liberty_pin(const ec::LibertyPinData& pin,
                                     const ec::StringPool& source,
                                     edacraft::core::StringPool& target,
                                     std::vector<uint32_t>& cache) {
    ec::LibertyPinData out = pin;
    out.name = remap_string(pin.name, source, target, cache);
    out.related_pg_pin = remap_string(pin.related_pg_pin, source, target, cache);
    out.function = remap_string(pin.function, source, target, cache);
    out.clear = remap_string(pin.clear, source, target, cache);
    out.preset = remap_string(pin.preset, source, target, cache);
    out.enable = remap_string(pin.enable, source, target, cache);
    out.receiver_capacitance1_rise = remap_nldm_table(pin.receiver_capacitance1_rise);
    out.receiver_capacitance1_fall = remap_nldm_table(pin.receiver_capacitance1_fall);
    out.receiver_capacitance2_rise = remap_nldm_table(pin.receiver_capacitance2_rise);
    out.receiver_capacitance2_fall = remap_nldm_table(pin.receiver_capacitance2_fall);
    for (auto& receiver : out.receiver_capacitance) {
        receiver.when = remap_string(receiver.when, source, target, cache);
    }
    for (auto& power : out.internal_power) {
        power.related_pin = remap_string(power.related_pin, source, target, cache);
        power.related_pg_pin = remap_string(power.related_pg_pin, source, target, cache);
        power.when = remap_string(power.when, source, target, cache);
    }
    return out;
}

ec::LibertyArcData remap_liberty_arc(const ec::LibertyArcData& arc,
                                     const ec::StringPool& source,
                                     edacraft::core::StringPool& target,
                                     std::vector<uint32_t>& cache) {
    ec::LibertyArcData out = arc;
    out.from_pin = remap_string(arc.from_pin, source, target, cache);
    out.to_pin = remap_string(arc.to_pin, source, target, cache);
    out.related_pin = remap_string(arc.related_pin, source, target, cache);
    out.when = remap_string(arc.when, source, target, cache);
    out.rise_delay = remap_nldm_table(arc.rise_delay);
    out.fall_delay = remap_nldm_table(arc.fall_delay);
    out.rise_output_slew = remap_nldm_table(arc.rise_output_slew);
    out.fall_output_slew = remap_nldm_table(arc.fall_output_slew);
    out.rise_constraint = remap_nldm_table(arc.rise_constraint);
    out.fall_constraint = remap_nldm_table(arc.fall_constraint);
    out.receiver_capacitance1_rise =
        remap_nldm_table(arc.receiver_capacitance1_rise);
    out.receiver_capacitance1_fall =
        remap_nldm_table(arc.receiver_capacitance1_fall);
    out.receiver_capacitance2_rise =
        remap_nldm_table(arc.receiver_capacitance2_rise);
    out.receiver_capacitance2_fall =
        remap_nldm_table(arc.receiver_capacitance2_fall);
    out.csm_output_current_rise = remap_csm_table(arc.csm_output_current_rise);
    out.csm_output_current_fall = remap_csm_table(arc.csm_output_current_fall);
    return out;
}

ec::LibertyCellData remap_liberty_cell(const ec::LibertyCellData& cell,
                                       const ec::StringPool& source,
                                       edacraft::core::StringPool& target,
                                       std::vector<uint32_t>& cache) {
    ec::LibertyCellData out = cell;
    out.name = remap_string(cell.name, source, target, cache);
    out.function = remap_string(cell.function, source, target, cache);
    out.footprint = remap_string(cell.footprint, source, target, cache);
    out.ff_clocked_on = remap_string(cell.ff_clocked_on, source, target, cache);
    out.ff_next_state = remap_string(cell.ff_next_state, source, target, cache);
    out.ff_clear = remap_string(cell.ff_clear, source, target, cache);
    out.ff_preset = remap_string(cell.ff_preset, source, target, cache);
    out.ff_enable = remap_string(cell.ff_enable, source, target, cache);
    out.ff_state = remap_string(cell.ff_state, source, target, cache);
    out.ff_state_neg = remap_string(cell.ff_state_neg, source, target, cache);
    out.clock_gating_integrated_cell = remap_string(cell.clock_gating_integrated_cell, source, target, cache);

    out.pins.clear();
    out.pins.reserve(cell.pins.size());
    for (const auto& pin : cell.pins) {
        out.pins.push_back(remap_liberty_pin(pin, source, target, cache));
    }

    out.arcs.clear();
    out.arcs.reserve(cell.arcs.size());
    for (const auto& arc : cell.arcs) {
        out.arcs.push_back(remap_liberty_arc(arc, source, target, cache));
    }
    for (auto& group : out.leakage_power) {
        group.when=remap_string(group.when,source,target,cache);
        group.related_pg_pin=remap_string(group.related_pg_pin,source,target,cache);
    }
    return out;
}

ec::LibertyDB remap_core_liberty_db(const ec::LibertyDB& source_db,
                                    const ec::StringPool& source_pool,
                                    edacraft::core::StringPool& target_pool) {
    ec::LibertyDB out;
    std::vector<uint32_t> string_cache(source_pool.size(), UINT32_MAX);
    for (uint32_t li = 0; li < source_db.library_count(); ++li) {
        const auto& src_lib = source_db.library(li);
        auto dst_lib_handle = out.add_library(remap_string(src_lib.name, source_pool, target_pool, string_cache));
        auto& dst_lib = out.library(dst_lib_handle);

        dst_lib.units = src_lib.units;
        // Retained CCSN nodes own textual atoms, not StringPool IDs. Preserve
        // library-level DC templates along with the cell-owned stage nodes.
        dst_lib.ccsn_templates = src_lib.ccsn_templates;
        dst_lib.power_metadata_complete=src_lib.power_metadata_complete;
        dst_lib.sequential_metadata_complete=src_lib.sequential_metadata_complete;
        dst_lib.electrical_metadata_complete=src_lib.electrical_metadata_complete;
        dst_lib.default_wire_load = remap_string(src_lib.default_wire_load, source_pool, target_pool, string_cache);
        dst_lib.default_wire_load_selection = remap_string(src_lib.default_wire_load_selection, source_pool, target_pool, string_cache);
        dst_lib.default_max_transition = src_lib.default_max_transition;
        dst_lib.default_max_capacitance = src_lib.default_max_capacitance;
        dst_lib.default_max_fanout = src_lib.default_max_fanout;
        dst_lib.default_fanout_load = src_lib.default_fanout_load;

        dst_lib.wire_load_models.reserve(src_lib.wire_load_models.size());
        for (const auto& src_wlm : src_lib.wire_load_models) {
            auto dst_wlm = src_wlm;
            dst_wlm.name = remap_string(src_wlm.name, source_pool, target_pool, string_cache);
            dst_lib.wire_load_models.push_back(std::move(dst_wlm));
        }

        for (uint32_t ci = 0; ci < src_lib.cells.size(); ++ci) {
            auto cell_handle = out.add_cell(dst_lib_handle,
                remap_string(src_lib.cells[ci].name, source_pool, target_pool, string_cache));
            out.cell(dst_lib_handle, cell_handle) =
                remap_liberty_cell(src_lib.cells[ci], source_pool, target_pool, string_cache);
        }
    }
    return out;
 }

// Append all libraries of a (remapped) LibertyDB into an existing target DB.
// Used by read_liberty so that multiple library files accumulate instead of
// overwriting each other (issue: loading >1 -lib lost all but the last).
void merge_liberty_db(edacraft::core::LibertyDB& dst,
                      edacraft::core::LibertyDB& src) {
    for (uint32_t li = 0; li < src.library_count(); ++li) {
        auto& sl = src.library(li);
        auto h = dst.add_library(sl.name);
        dst.library(h) = std::move(sl);
    }
}

Transition transition_from_name(const std::string& name) {
    return name == "fall" ? Transition::Fall : Transition::Rise;
}

std::optional<PinId> resolve_report_pin(const Network& network,
                                        const std::string& name) {
    size_t delim = name.find_last_of("/:");
    if (delim != std::string::npos) {
        std::string_view inst_name(name.data(), delim);
        std::string_view pin_name(name.data() + delim + 1, name.size() - delim - 1);
        auto inst = network.find_instance(inst_name);
        if (inst) {
            auto pin = network.find_pin(*inst, pin_name);
            if (pin) return pin;
        }
    }

    for (uint32_t pid = 0; pid < network.pin_count(); ++pid) {
        PinId pin{pid};
        if (network.pin_name(pin) == name) return pin;
        const auto& pin_data = network.pin(pin);
        if (valid(pin_data.instance)) {
            std::string full_name = std::string(network.instance_name(pin_data.instance)) +
                                    "/" + std::string(network.pin_name(pin));
            if (full_name == name) return pin;
        }
    }
    return std::nullopt;
}

float slack_from_values(float arrival, float required, MinMax mm) {
    return mm == MinMax::Min ? (arrival - required) : (required - arrival);
}

template <typename Fn>
void for_each_or_null_pin(const std::vector<PinId>& pins, Fn&& fn) {
    if (pins.empty()) {
        fn(NULL_PIN);
        return;
    }
    for (PinId pin : pins) fn(pin);
}

void export_resolved_exceptions(const ResolvedConstraintSet& sdc,
                                edacraft::core::TimingDB& timing_db,
                                const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr) {
    for (const auto& fp : sdc.false_paths()) {
        for_each_or_null_pin(fp.from_pins, [&](PinId from_pin) {
            for_each_or_null_pin(fp.through_pins, [&](PinId through_pin) {
                for_each_or_null_pin(fp.to_pins, [&](PinId to_pin) {
                    edacraft::core::ResolvedTimingException ex;
                    ex.type = edacraft::core::TimingExceptionType::FalsePath;
                    ex.from_pin = to_core_pin(from_pin, bindings);
                    ex.through_pin = to_core_pin(through_pin, bindings);
                    for (const auto& stage : fp.through_stages) {
                        std::vector<ec::PinHandle> converted;
                        for (auto pin : stage) converted.push_back(to_core_pin(pin, bindings));
                        ex.through_stages.push_back(std::move(converted));
                    }
                    ex.to_pin = to_core_pin(to_pin, bindings);
                    ex.source = "set_false_path";
                    ex.from_clocks = fp.from_clocks;
                    ex.to_clocks = fp.to_clocks;
                    if (fp.setup) {
                        ex.analysis = edacraft::core::MinMax::Max;
                        timing_db.add_exception(ex);
                    }
                    if (fp.hold) {
                        ex.analysis = edacraft::core::MinMax::Min;
                        timing_db.add_exception(std::move(ex));
                    }
                });
            });
        });
    }

    for (const auto& mcp : sdc.multicycle_paths()) {
        for_each_or_null_pin(mcp.from_pins, [&](PinId from_pin) {
            for_each_or_null_pin(mcp.to_pins, [&](PinId to_pin) {
                edacraft::core::ResolvedTimingException setup_ex;
                setup_ex.type = edacraft::core::TimingExceptionType::MulticyclePath;
                setup_ex.from_pin = to_core_pin(from_pin, bindings);
                setup_ex.to_pin = to_core_pin(to_pin, bindings);
                setup_ex.analysis = mcp.is_hold ? edacraft::core::MinMax::Min : edacraft::core::MinMax::Max;
                setup_ex.setup_cycles = mcp.setup_cycles;
                setup_ex.hold_cycles = (mcp.hold_cycles > 0)
                    ? mcp.hold_cycles
                    : (mcp.setup_cycles - 1);
                setup_ex.source = mcp.is_hold ? "set_multicycle_path -hold" : "set_multicycle_path -setup";
                setup_ex.from_clocks = mcp.from_clocks;
                setup_ex.to_clocks = mcp.to_clocks;
                setup_ex.is_hold = mcp.is_hold;
                setup_ex.use_start = mcp.use_start;
                timing_db.add_exception(setup_ex);

                if (!mcp.is_hold) {
                    edacraft::core::ResolvedTimingException hold_ex = setup_ex;
                    hold_ex.analysis = edacraft::core::MinMax::Min;
                    hold_ex.source = "set_multicycle_path -hold";
                    timing_db.add_exception(std::move(hold_ex));
                }
            });
        });
    }

    for (const auto& dt : sdc.disable_timings()) {
        edacraft::core::ResolvedTimingException ex;
        ex.type = edacraft::core::TimingExceptionType::DisableTiming;
        ex.from_pin = to_core_pin(dt.from_pin, bindings);
        ex.to_pin = to_core_pin(dt.to_pin, bindings);
        ex.analysis = edacraft::core::MinMax::Max;
        ex.source = "set_disable_timing";
        timing_db.add_exception(ex);

        ex.analysis = edacraft::core::MinMax::Min;
        timing_db.add_exception(std::move(ex));
    }

    for (const auto& ca : sdc.case_analyses()) {
        edacraft::core::ResolvedTimingException ex;
        ex.type = edacraft::core::TimingExceptionType::CaseAnalysis;
        ex.to_pin = to_core_pin(ca.pin, bindings);
        ex.analysis = edacraft::core::MinMax::Max;
        ex.case_value = static_cast<int>(ca.value);
        ex.source = "set_case_analysis";
        timing_db.add_exception(ex);

        ex.analysis = edacraft::core::MinMax::Min;
        timing_db.add_exception(std::move(ex));
    }
}

std::vector<ec::PinHandle> to_core_pins(
    const std::vector<PinId>& pins,
    const std::unordered_map<uint32_t, ec::PinHandle>* bindings) {
    std::vector<ec::PinHandle> out;
    out.reserve(pins.size());
    for (auto pin : pins) {
        auto core_pin = to_core_pin(pin, bindings);
        if (ec::valid(core_pin)) out.push_back(core_pin);
    }
    return out;
}

ec::ResolvedConstraintSet export_resolved_constraints(
    const ResolvedConstraintSet& sdc,
    const std::unordered_map<uint32_t, ec::PinHandle>* bindings) {
    ec::ResolvedConstraintSet out;
    const auto& design_rules = sdc.design_rules();
    out.set_design_rules(design_rules.max_fanout,
                         design_rules.max_capacitance,
                         design_rules.max_transition);

    for (uint32_t cid = 0; cid < sdc.clocks().size(); ++cid) {
        const auto& clk = sdc.clocks()[cid];
        uint32_t out_id = out.create_clock(clk.name, clk.period, clk.transition);
        if (clk.rise_time >= 0.0f || clk.fall_time >= 0.0f) {
            out.set_clock_waveform(out_id, clk.rise_time, clk.fall_time);
        }
        for (auto pin : clk.sources) {
            auto core_pin = to_core_pin(pin, bindings);
            if (ec::valid(core_pin)) out.add_clock_source(out_id, core_pin);
        }
    }

    for (uint32_t cid = 0; cid < sdc.clocks().size(); ++cid) {
        const auto& clk = sdc.clocks()[cid];
        if (!clk.generated) continue;
        const auto source = to_core_pin(clk.generated_source, bindings);
        if (!ec::valid(source)) throw std::runtime_error("Generated clock source has no core pin binding");
        out.set_generated_clock(cid, clk.master_clock, source);
    }

    for (const auto& d : sdc.input_delays()) {
        out.set_input_delay(d.clock, d.delay, d.is_max, to_core_transition(d.clock_edge),
                            to_core_pins(d.ports, bindings));
    }
    for (const auto& d : sdc.output_delays()) {
        out.set_output_delay(d.clock, d.delay, d.is_max, to_core_transition(d.clock_edge),
                             to_core_pins(d.ports, bindings));
    }
    for (const auto& sl : sdc.set_loads()) {
        out.set_load(sl.capacitance, to_core_pins(sl.pins, bindings));
    }
    for (const auto& it : sdc.input_transitions()) {
        out.set_input_transition(it.transition, to_core_pins(it.ports, bindings),
                                 it.rise, it.fall, it.min, it.max, it.order);
    }
    for (const auto& driver : sdc.driving_cells()) {
        out.set_driving_cell(driver.model, to_core_pins(driver.ports, bindings));
    }
    for (const auto& cl : sdc.clock_latencies()) {
        out.set_clock_latency(cl.latency, cl.clock, to_core_pins(cl.pins, bindings));
    }
    for (const auto& cu : sdc.clock_uncertainties()) {
        if (cu.setup_uncertainty != 0.0f) {
            out.set_clock_uncertainty(cu.setup_uncertainty, cu.clock, true);
        }
        if (cu.hold_uncertainty != 0.0f) {
            out.set_clock_uncertainty(cu.hold_uncertainty, cu.clock, false);
        }
    }
    for (const auto& md : sdc.max_delays()) {
        std::vector<std::vector<ec::PinHandle>> stages;
        for(const auto& stage:md.through_stages)stages.push_back(to_core_pins(stage,bindings));
        out.set_max_delay(md.delay, to_core_pins(md.from_pins, bindings),
                          to_core_pins(md.to_pins, bindings),to_core_pins(md.through_pins,bindings),std::move(stages),md.from_clocks,md.to_clocks,md.ignore_clock_latency);
    }
    for (const auto& md : sdc.min_delays()) {
        std::vector<std::vector<ec::PinHandle>> stages;
        for(const auto& stage:md.through_stages)stages.push_back(to_core_pins(stage,bindings));
        out.set_min_delay(md.delay, to_core_pins(md.from_pins, bindings),
                          to_core_pins(md.to_pins, bindings),to_core_pins(md.through_pins,bindings),std::move(stages),md.from_clocks,md.to_clocks,md.ignore_clock_latency);
    }
    for (const auto& check : sdc.data_checks()) {
        out.set_data_check(check.delay, check.is_setup,
                           to_core_pins(check.from_pins, bindings),
                           to_core_pins(check.to_pins, bindings),
                           check.from_transitions, check.to_transitions);
    }
    for (const auto& group : sdc.path_groups()) {
        ec::ResolvedConstraintSet::PathGroup resolved;
        resolved.name = group.name;
        resolved.weight = group.weight;
        resolved.from_clocks = group.from_clocks;
        resolved.to_clocks = group.to_clocks;
        resolved.from_transitions = group.from_transitions;
        resolved.to_transitions = group.to_transitions;
        resolved.through_transitions = group.through_transitions;
        resolved.through_stage_transitions = group.through_stage_transitions;
        auto convert = [&](const std::vector<PinId>& pins) {
            auto converted = to_core_pins(pins, bindings);
            if (!pins.empty() && converted.empty()) converted.push_back(ec::PinHandle{UINT32_MAX});
            return converted;
        };
        resolved.from_pins = convert(group.from_pins);
        resolved.to_pins = convert(group.to_pins);
        resolved.through_pins = convert(group.through_pins);
        for (const auto& stage : group.through_stages)
            resolved.through_stages.push_back(convert(stage));
        out.add_path_group(std::move(resolved));
    }
    for (const auto& mcp : sdc.multicycle_paths()) {
        out.set_multicycle_path(mcp.setup_cycles, mcp.hold_cycles,
                                to_core_pins(mcp.from_pins, bindings),
                                to_core_pins(mcp.to_pins, bindings),mcp.from_clocks,mcp.to_clocks,mcp.is_hold,mcp.use_start);
    }
    for (const auto& ca : sdc.case_analyses()) {
        auto pin = to_core_pin(ca.pin, bindings);
        if (ec::valid(pin)) {
            out.set_case_analysis(static_cast<ec::ResolvedCaseAnalysis::Value>(ca.value), pin);
        }
    }
    for (const auto& dt : sdc.disable_timings()) {
        out.set_disable_timing(to_core_pin(dt.from_pin, bindings),
                               to_core_pin(dt.to_pin, bindings));
    }
    for (const auto& fp : sdc.false_paths()) {
        std::vector<std::vector<ec::PinHandle>> through_stages;
        for (const auto& stage : fp.through_stages)
            through_stages.push_back(to_core_pins(stage, bindings));
        out.set_false_path(to_core_pins(fp.from_pins, bindings),
                           to_core_pins(fp.through_pins, bindings),
                           to_core_pins(fp.to_pins, bindings),
                           std::move(through_stages), fp.setup, fp.hold,fp.from_transitions,fp.to_transitions,
                           fp.through_transitions,fp.through_stage_transitions,fp.from_clocks,fp.to_clocks);
    }
    for (const auto& clock_group : sdc.clock_groups()) {
        out.set_clock_groups(clock_group.mode, clock_group.groups);
    }

    out.set_timing_derate(sdc.ocv_derate().early_data,
                          sdc.ocv_derate().late_data,
                          false);
    out.set_timing_derate(sdc.ocv_derate().early_clock,
                          sdc.ocv_derate().late_clock,
                          true);
    if (!sdc.aocv_table().empty()) {
        std::vector<ec::ResolvedAocvPoint> points;
        points.reserve(sdc.aocv_table().points.size());
        for (const auto& p : sdc.aocv_table().points) {
            points.push_back({p.depth, p.late_derate, p.early_derate});
        }
        out.set_aocv_derate(std::move(points));
    }

    return out;
}

void write_timing_point(const TimingGraph& graph,
                        PinId pin,
                        edacraft::core::TimingDB& timing_db,
                        const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr) {
    if (!valid(pin) || pin.id > UINT32_MAX / 2) return;
    for (int mm_i = 0; mm_i < 2; ++mm_i) {
        MinMax mm = static_cast<MinMax>(mm_i);
        auto core_mm = to_core_min_max(mm);
        for (int rf_i = 0; rf_i < 2; ++rf_i) {
            Transition rf = static_cast<Transition>(rf_i);
            uint32_t vid = pin.id * 2 + static_cast<uint32_t>(rf);
            if (vid >= graph.vertex_count()) continue;

            float arrival = graph.arrival(vid, mm, rf).value;
            float required = graph.required(vid, mm, rf).value;
            float slew = graph.slew(vid, mm, rf).value;
            // Export the same launch context as the public timing queries.
            // Scalar SOA requirements preserve worst slack, but can pair it
            // with a different reconvergent arrival.
            if (const auto* label = graph.worst_launch_label(vid, mm)) {
                arrival = label->arrival;
                required = label->required;
            }

            edacraft::core::TimingPoint point;
            point.key.pin = to_core_pin(pin, bindings);
            point.key.transition = to_core_transition(rf);
            point.key.analysis = core_mm;
            point.arrival_ns = arrival;
            point.required_ns = required;
            point.slew_ns = slew;
            point.slack_ns = slack_from_values(arrival, required, mm);
            point.has_arrival = std::isfinite(arrival);
            point.has_required = std::isfinite(required);
            point.has_slew = std::isfinite(slew);
            point.has_slack = std::isfinite(point.slack_ns);
            timing_db.set_point(std::move(point));
        }
    }
}

void write_timing_arc(const TimingGraph& graph,
                      const Network& network,
                      const ec::LibertyDB& liberty,
                      uint32_t eid,
                      edacraft::core::TimingDB& timing_db,
                      const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr,
                      std::unordered_set<ec::TimingArcKey, ec::TimingArcKeyHash>* written = nullptr) {
    uint32_t from_vid = graph.edge_from(eid);
    uint32_t to_vid = graph.edge_to(eid);
    if (from_vid >= graph.vertex_count() || to_vid >= graph.vertex_count()) return;

    PinId from_pin = graph.vertex_pin(from_vid);
    PinId to_pin = graph.vertex_pin(to_vid);
    if (!valid(from_pin) || !valid(to_pin)) return;

    Transition from_rf = graph.vertex_transition(from_vid);
    Transition to_rf = graph.vertex_transition(to_vid);
    edacraft::core::TimingArcType arc_type = edacraft::core::TimingArcType::Combinational;
    edacraft::core::TimingSense sense = edacraft::core::TimingSense::None;
    std::string source = "net";

    uint32_t arc_idx = graph.edge_arc(eid);
    if (arc_idx != UINT32_MAX) {
        const auto& to_pin_data = network.pin(to_pin);
        if (valid(to_pin_data.instance)) {
            const auto& inst = network.instance(to_pin_data.instance);
            const auto& cell = network.cell(inst.cell);
            if (valid(cell.liberty_library) && valid(cell.liberty_cell)) {
                const auto& lib_cell = liberty.cell(liberty::to_core(cell.liberty_library),
                                                    liberty::to_core(cell.liberty_cell));
                if (arc_idx < lib_cell.arcs.size()) {
                    const auto& lib_arc = lib_cell.arcs[arc_idx];
                    arc_type = to_core_arc_type(lib_arc.type);
                    sense = to_core_sense(lib_arc.sense);
                    source = std::string(network.cell_name(inst.cell)) +
                             "." + std::string(network.pin_name(from_pin)) +
                             "->" + std::string(network.pin_name(to_pin));
                }
            }
        }
    }

    for (auto mm : {MinMax::Max, MinMax::Min}) {
        const float delay = graph.edge_delay(eid, mm);
        const auto model = graph.edge_delay_source(eid, mm);
        const auto delay_model = to_core_delay_model(model);
        const float ceff = graph.edge_ceff(eid, mm);
        float output_slew = graph.edge_output_slew(eid, mm);
        if (model == DelayModelSource::None && output_slew <= 0.0f)
            output_slew = graph.slew(to_vid, mm, to_rf).value;
        edacraft::core::TimingArc arc;
        arc.from_pin = to_core_pin(from_pin, bindings);
        arc.to_pin = to_core_pin(to_pin, bindings);
        arc.from_transition = to_core_transition(from_rf);
        arc.to_transition = to_core_transition(to_rf);
        arc.analysis = to_core_min_max(mm);
        arc.type = arc_type;
        arc.sense = sense;
        arc.delay_model = delay_model;
        arc.delay_ns = delay;
        arc.output_slew_ns = output_slew;
        arc.effective_capacitance = ceff;
        arc.source = source;
        // TimingDB keys do not include Liberty's when condition. Export one
        // bounding delay per key, with the slew/Ceff of that same graph arc.
        // The first write in each export replaces any previous snapshot, so
        // incremental updates can lower a formerly worst conditional delay.
        const ec::TimingArcKey key{arc.from_pin, arc.to_pin, arc.from_transition,
            arc.to_transition, arc.analysis, arc.corner, arc.type};
        if (written && !written->insert(key).second) {
            const auto* previous = timing_db.find_arc(key);
            if (previous && std::isfinite(previous->delay_ns) &&
                (!std::isfinite(delay) ||
                 (mm == MinMax::Max ? previous->delay_ns >= delay
                                    : previous->delay_ns <= delay))) continue;
        }
        timing_db.set_arc(std::move(arc));
    }
}

void write_constraint_arcs_for_pin(const TimingGraph& graph,
                                   const Network& network,
                                   const ec::LibertyDB& liberty,
                                   PinId target_pin,
                                   edacraft::core::TimingDB& timing_db,
                                   const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr) {
    if (!valid(target_pin)) return;
    const auto& target_pin_data = network.pin(target_pin);
    if (!valid(target_pin_data.instance)) return;
    const auto& inst = network.instance(target_pin_data.instance);
    const auto& cell = network.cell(inst.cell);
    if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) return;

    const auto& lib_cell = liberty.cell(liberty::to_core(cell.liberty_library),
                                        liberty::to_core(cell.liberty_cell));

    std::vector<ec::TimingArc> constraints;
    for (const auto& lib_arc : lib_cell.arcs) {
        if (graph.check_arc_disabled(target_pin_data.instance.id,
            static_cast<uint32_t>(&lib_arc-lib_cell.arcs.data()))) continue;
        if (!ec::liberty_timing_type_is_check(lib_arc.type)) {
            continue;
        }
        if (lib_arc.to_pin != target_pin_data.name) continue;

        PinId clock_pin = NULL_PIN;
        for (auto pid : inst.pins) {
            const auto& pin = network.pin(pid);
            if (pin.name == lib_arc.from_pin) {
                clock_pin = pid;
                break;
            }
        }
        if (!valid(clock_pin)) continue;

        Transition clock_rf = ec::liberty_timing_type_is_falling_check(lib_arc.type)
            ? Transition::Fall
            : Transition::Rise;
        uint32_t clock_vid = clock_pin.id * 2 + static_cast<uint32_t>(clock_rf);
        if (clock_vid >= graph.vertex_count()) continue;
        MinMax clock_slew_mode = ec::liberty_timing_type_is_min_check(lib_arc.type)
            ? MinMax::Min
            : MinMax::Max;
        float clock_slew = graph.slew(clock_vid, clock_slew_mode, clock_rf).value;

        for (Transition data_rf : {Transition::Rise, Transition::Fall}) {
            uint32_t data_vid = target_pin.id * 2 + static_cast<uint32_t>(data_rf);
            if (data_vid >= graph.vertex_count()) continue;
            float data_slew = graph.slew(data_vid, clock_slew_mode, data_rf).value;
            const auto& table = (data_rf == Transition::Rise)
                ? lib_arc.rise_constraint
                : lib_arc.fall_constraint;
            // A declared constraint may retain template dimensions while its
            // data is missing. The timing-check ledger records MissingTable;
            // the snapshot must not interpolate an incomplete table.
            if (table.rows == 0 || table.cols == 0 ||
                table.values.size() != size_t(table.rows) * table.cols) continue;

            edacraft::core::TimingArc arc;
            arc.from_pin = to_core_pin(clock_pin, bindings);
            arc.to_pin = to_core_pin(target_pin, bindings);
            arc.from_transition = to_core_transition(clock_rf);
            arc.to_transition = to_core_transition(data_rf);
            arc.analysis = ec::liberty_timing_type_is_min_check(lib_arc.type)
                ? edacraft::core::MinMax::Min
                : edacraft::core::MinMax::Max;
            arc.type = to_core_arc_type(lib_arc.type);
            arc.sense = to_core_sense(lib_arc.sense);
            arc.constraint_ns = liberty::constraint_ns(table, clock_slew, data_slew,
                liberty::time_unit_ns(liberty.library(cell.liberty_library.id)));
            if (!std::isfinite(arc.constraint_ns)) continue;
            arc.has_constraint = true;
            arc.source = std::string(network.cell_name(inst.cell)) +
                         "." + std::string(network.pin_name(clock_pin)) +
                         "->" + std::string(network.pin_name(target_pin)) +
                         (arc.type == ec::TimingArcType::Hold ? ":hold" : arc.type == ec::TimingArcType::Recovery ? ":recovery" : arc.type == ec::TimingArcType::Removal ? ":removal" : ":setup");
            auto same = std::find_if(constraints.begin(), constraints.end(), [&](const auto& old) {
                return old.from_pin == arc.from_pin && old.type == arc.type &&
                    old.from_transition == arc.from_transition && old.to_transition == arc.to_transition;
            });
            if (same == constraints.end()) constraints.push_back(std::move(arc));
            else if (arc.constraint_ns > same->constraint_ns) *same = std::move(arc);
        }
    }
    for (auto& arc : constraints) timing_db.set_arc(std::move(arc));
}

std::vector<PathReport> all_check_reports(const TimingEngine& engine, MinMax mm) {
    auto reports = engine.report_worst_paths(mm, 32, TimingCheckKind::Data);
    auto async = engine.report_worst_paths(mm, 32,
        mm == MinMax::Max ? TimingCheckKind::Recovery : TimingCheckKind::Removal);
    for (auto& p : async) reports.push_back(std::move(p));
    return reports;
}

void write_timing_paths(const TimingEngine& engine,
                        const Network& network,
                        edacraft::core::TimingDB& timing_db,
                        const std::unordered_map<uint32_t, edacraft::core::PinHandle>* bindings = nullptr) {
    timing_db.clear_paths();
    auto write_paths = [&](MinMax mm) {
        auto reports = all_check_reports(engine, mm);
        auto core_mm = to_core_min_max(mm);
        for (const auto& report : reports) {
            edacraft::core::TimingPath path;
            path.analysis = core_mm;
            path.slack_ns = report.slack;
            if (report.check_kind == TimingCheckKind::Recovery) path.path_group = "recovery";
            else if (report.check_kind == TimingCheckKind::Removal) path.path_group = "removal";
            else if (!report.path_group.empty()) path.path_group = report.path_group;

            for (size_t i = 0; i < report.point_names.size(); ++i) {
                edacraft::core::TimingPathPoint point;
                point.pin_name = report.point_names[i];
                if (auto pin = resolve_report_pin(network, report.point_names[i])) {
                    point.pin = to_core_pin(*pin, bindings);
                    if (i == 0) path.startpoint = point.pin;
                    if (i + 1 == report.point_names.size()) path.endpoint = point.pin;
                }
                if (i < report.transitions.size()) {
                    point.transition = to_core_transition(transition_from_name(report.transitions[i]));
                }
                if (i < report.arrivals.size()) point.arrival_ns = report.arrivals[i];
                if (i < report.slews.size()) point.slew_ns = report.slews[i];
                if (i < report.delays.size()) point.arc_delay_ns = report.delays[i];
                point.slack_ns = report.slack;
                path.points.push_back(std::move(point));
            }
            if (!report.transitions.empty()) {
                path.endpoint_transition = to_core_transition(
                    transition_from_name(report.transitions.back()));
            }
            timing_db.add_path(std::move(path));
        }
    };

    write_paths(MinMax::Max);
    write_paths(MinMax::Min);
}

} // namespace

// ────────────────────────────────────────────────────────────
// TimingEngine public API
// ────────────────────────────────────────────────────────────

TimingEngine::TimingEngine() : impl_(std::make_unique<Impl>()) {}
TimingEngine::~TimingEngine() = default;

void TimingEngine::set_thread_count(int n) {
    impl_->thread_count = n;
    parallel_thread_count().store(n);
}

void TimingEngine::set_pvt(float voltage, float temperature) {
    impl_->voltage = voltage;
    impl_->power_voltage_explicit = true;
    impl_->temperature = temperature;
}

void TimingEngine::set_verbose(bool verbose) {
    impl_->verbose = verbose;
    if (impl_->graph) impl_->graph->set_verbose(verbose);
}

void TimingEngine::set_temperature(float temperature) { impl_->temperature=temperature; }

void TimingEngine::read_liberty(std::string_view filepath) {
    detail::reject_experimental_db_input(std::string(filepath));
    auto ext = std::filesystem::path(filepath).extension();
    std::string path_str(filepath);

    bool try_binary = (ext == ".ftlib" || ext == ".gz");
    if (!try_binary && ext.empty()) {
        // Check for .ftlib.gz by looking at the full filename
        if (path_str.find(".ftlib.gz") != std::string::npos) {
            try_binary = true;
        }
    }

    if (try_binary) {
        ec::LibertyDB loaded_liberty;
        ec::StringPool loaded_strings;
        if (load_liberty_binary(path_str, loaded_liberty, loaded_strings)) {
            impl_->use_owned_liberty();
            auto remapped = remap_core_liberty_db(loaded_liberty,
                                                   loaded_strings,
                                                   impl_->network->string_pool());
            merge_liberty_db(impl_->owned_liberty, remapped);
            return;
        }
        // An incompatible cache is binary, never a successful empty text library.
        if (ext == ".ftlib" || path_str.find(".ftlib.gz") != std::string::npos)
            throw std::runtime_error("Cannot load Liberty cache; regenerate from .lib: " + path_str);
        // If binary load fails, fall through to text parser
        // (the file might be a gzip'd text .lib)
    }

    std::ifstream file{path_str};
    if (!file) throw std::runtime_error(std::string("Cannot open liberty file: ") + path_str);

    std::ostringstream ss;
    ss << file.rdbuf();
    std::string content = ss.str();

    parser::LibertyParser lib_parser(content);
    ec::LibertyDB parsed_liberty;
    ec::StringPool parsed_strings;
    // Each file is parsed into a temporary DB before merging. Invalid slew
    // windows must inherit the session's main library, not this empty DB's
    // 20/80 defaults. The first loaded library still uses those defaults.
    const auto* main_units = impl_->liberty->library_count() ?
        &impl_->liberty->library(0).units : nullptr;
    lib_parser.parse(parsed_liberty, parsed_strings, main_units);
    impl_->use_owned_liberty();
    auto remapped = remap_core_liberty_db(parsed_liberty,
                                           parsed_strings,
                                           impl_->network->string_pool());
    merge_liberty_db(impl_->owned_liberty, remapped);
}

void TimingEngine::use_external_liberty(const edacraft::core::LibertyDB& liberty) {
    impl_->use_external_liberty(
        const_cast<edacraft::core::LibertyDB&>(liberty));
}

void TimingEngine::use_external_liberty(
    const edacraft::core::LibertyDB& liberty,
    const edacraft::core::StringPool& liberty_strings) {
    impl_->owned_liberty = remap_core_liberty_db(
        liberty, liberty_strings, impl_->network->string_pool());
    impl_->liberty = &impl_->owned_liberty;
}

void TimingEngine::set_top_design(std::string_view top_name) {
    impl_->preferred_top_name = std::string(top_name);
}

void TimingEngine::read_verilog(std::string_view filepath) {
    std::filesystem::path p{std::string(filepath)};
    std::string include_dir = p.parent_path().string();
    build_network_from_verilog(
        *impl_->network, filepath, include_dir, impl_->preferred_top_name);
}

void TimingEngine::read_spef(std::string_view filepath) {
    std::ifstream file{std::string(filepath)};
    if (!file) throw std::runtime_error(std::string("Cannot open SPEF file: ") + std::string(filepath));

    std::ostringstream ss;
    ss << file.rdbuf();
    std::string content = ss.str();

    SpefParser spef_parser(content);

    struct Resolver : public SpefNameResolver {
        Network& net;
        Resolver(Network& n) : net(n) {}
        mutable std::unordered_map<std::string, PinId> pin_cache_;
        mutable std::unordered_map<std::string, NetId> net_cache_;

        NetId resolve_net(std::string_view name) override {
            std::string key(name);
            auto it = net_cache_.find(key);
            if (it != net_cache_.end()) return it->second;
            auto id = net.find_net(name);
            NetId result = id.value_or(NULL_NET);
            net_cache_[std::move(key)] = result;
            return result;
        }
        NetId resolve_node_net(std::string_view name) override {
            const NetId direct = resolve_net(name);
            if (valid(direct)) return direct;
            const PinId pin = resolve_pin(name);
            if (valid(pin) && valid(net.pin(pin).net)) return net.pin(pin).net;
            return NULL_NET;
        }
        PinId resolve_pin(std::string_view name) override {
            std::string key(name);
            auto it = pin_cache_.find(key);
            if (it != pin_cache_.end()) return it->second;
            PinId result = NULL_PIN;
            // SPEF uses ':' between a hierarchical instance and pin, while
            // Verilog/netlist names use '/'. Convert only the final separator
            // after decoding escaped hierarchy names.
            std::string decoded;
            decoded.reserve(name.size());
            for (size_t i=0;i<name.size();++i) {
                if (name[i]=='\\' && i+1<name.size()) ++i;
                decoded.push_back(name[i]);
            }
            const std::string_view decoded_name = decoded;
            name = decoded_name;
            // Fast path: most SPEF pin names are instance/pin format (e.g., "u1:A")
            size_t delim = name.find_last_of("/:");
            if (delim != std::string_view::npos) {
                std::string_view inst_name = name.substr(0, delim);
                std::string_view pin_name = name.substr(delim + 1);
                auto inst = net.find_instance(inst_name);
                if (inst) {
                    auto pin = net.find_pin(*inst, pin_name);
                    if (pin) result = *pin;
                }
            } else {
                // Top-level port: linear scan (rare)
                for (uint32_t pid = 0; pid < net.pin_count(); ++pid) {
                    if (net.pin_name(PinId{pid}) == name) {
                        result = PinId{pid};
                        break;
                    }
                }
            }
            pin_cache_[std::move(key)] = result;
            return result;
        }
    };

    Resolver resolver(*impl_->network);
    if (!spef_parser.parse(*impl_->parasitics, resolver)) {
        throw std::runtime_error("Cannot parse SPEF: " + std::string(spef_parser.last_error()));
    }
    // A new extraction changes both driver loading and receiver waveforms.
    // Include all timing points in the next incremental bridge publication.
    if (impl_->graph) {
        for (uint32_t vid = 0; vid < impl_->graph->vertex_count(); ++vid)
            impl_->dirty_tracker.mark_vertex(vid);
    }
}

void TimingEngine::read_sdc(std::string_view filepath) {
    ec::ConstraintDB constraints;
    ec::SdcParser parser;
    std::ifstream input{std::string(filepath)};
    if (!input) throw std::runtime_error("Cannot read SDC: " + std::string(filepath));
    std::ostringstream content;
    content << input.rdbuf();
    std::string resolved_sdc;
    if (!parser.resolve_static_variables(content.str(), resolved_sdc) ||
        !parser.parse_string(expand_netlist_collections(resolved_sdc, *impl_->network), constraints)) {
        throw std::runtime_error(parser.last_error());
    }

    // Materialized collections contain many exact port names. Avoid a full
    // pin scan for each bus bit when resolving all_inputs/all_outputs.
    std::unordered_map<std::string, std::vector<PinId>> exact_pins;
    for (uint32_t pid = 0; pid < impl_->network->pin_count(); ++pid) {
        PinId pin{pid};
        exact_pins[std::string(impl_->network->pin_name(pin))].push_back(pin);
    }
    std::unordered_set<std::string> unresolved_sdc_globs;
    PinListResolver pin_resolver = [this, &exact_pins, &unresolved_sdc_globs](const std::string& name) -> std::vector<PinId> {
        std::vector<PinId> pins;
        if (!impl_->network) return pins;
        const auto& network = *impl_->network;
        auto exact = exact_pins.find(name);
        if (exact != exact_pins.end()) return exact->second;

        // Resolve SDC wildcard collections before scalar and bus-alias
        // fallbacks. The old resolver treated `pad_plic_int_vld*` as an exact
        // name, silently dropping every selected bit from the constraints.
        if (name.find('*') != std::string::npos ||
            name.find('?') != std::string::npos) {
            for (uint32_t pid = 0; pid < network.pin_count(); ++pid) {
                PinId pin{pid};
                if (sdc_glob_match(name, network.pin_name(pin))) pins.push_back(pin);
            }
            if (!pins.empty()) return pins;
            unresolved_sdc_globs.insert(name);
        }

        auto add_exact_top_level = [&]() {
            for (uint32_t pid = 0; pid < network.pin_count(); ++pid) {
                PinId pin{pid};
                std::string_view pin_name = network.pin_name(pin);
                if (pin_name == name) {
                    pins.push_back(pin);
                    continue;
                }
                if (pin_name.size() > name.size() &&
                    pin_name.substr(pin_name.size() - name.size()) == name &&
                    pin_name[pin_name.size() - name.size() - 1] == '/') {
                    pins.push_back(pin);
                }
            }
        };

        add_exact_top_level();
        if (!pins.empty()) return pins;

        const std::string prefix = name + "[";
        for (uint32_t pid = 0; pid < network.pin_count(); ++pid) {
            PinId pin{pid};
            std::string_view pin_name = network.pin_name(pin);
            if (pin_name.size() > prefix.size() &&
                pin_name.compare(0, prefix.size(), prefix) == 0) {
                pins.push_back(pin);
                continue;
            }
            const std::string suffix = "/" + prefix;
            auto pos = pin_name.find(suffix);
            if (pos != std::string_view::npos &&
                pos + suffix.size() < pin_name.size()) {
                pins.push_back(pin);
            }
        }
        if (!pins.empty()) return pins;

        size_t delim = name.find_last_of("/:");
        if (delim != std::string::npos) {
            std::string inst_name = name.substr(0, delim);
            std::string pin_name = name.substr(delim + 1);
            auto inst = network.find_instance(inst_name);
            if (inst) {
                auto pin = network.find_pin(*inst, pin_name);
                if (pin) pins.push_back(*pin);
            }
        }
        return pins;
    };
    StringInterner string_interner = [this](const std::string& name) -> uint32_t {
        return impl_->network->string_pool().intern(name);
    };
    apply_constraints(constraints, pin_resolver, string_interner, impl_->verbose);
    if (!unresolved_sdc_globs.empty()) {
        std::ostringstream message;
        message << "[SDC] Unresolved wildcard selector(s):";
        for (const auto& selector : unresolved_sdc_globs) message << " " << selector;
        if (env_flag_enabled("FTIMER_SDC_STRICT_COLLECTIONS")) {
            throw std::runtime_error(message.str());
        }
        if (impl_->verbose) std::cerr << message.str() << "\n";
    }
    if (impl_->verbose) {
        std::cerr << "[SDC] After parse: clocks=" << impl_->sdc->clocks().size()
                  << " input_delays=" << impl_->sdc->input_delays().size()
                  << " output_delays=" << impl_->sdc->output_delays().size() << "\n";
        for (const auto& warning : parser.warnings())
            std::cerr << "[SDC] Warning: " << warning << "\n";
        for (const auto& id : impl_->sdc->input_delays()) {
            std::cerr << "[SDC]   input_delay: delay=" << id.delay << " clock=" << id.clock << " ports=";
            for (auto p : id.ports) std::cerr << p.id << " ";
            std::cerr << "\n";
        }
    }
}

void TimingEngine::apply_constraints(
    const edacraft::core::ConstraintDB& constraints,
    const ConstraintPinResolver& pin_resolver,
    const ConstraintStringInterner& string_interner,
    bool verbose) {
    // ConstraintDB is the complete constraint state for an analysis.  Full
    // timing rebuilds may apply it repeatedly, so retaining resolved entries
    // would create duplicate clock domains and detach uncertainty from the
    // domain assigned to sequential endpoints.
    impl_->sdc->clear();
    apply_core_sdc(constraints, *impl_->sdc, pin_resolver, string_interner,
                   verbose || impl_->verbose);
    // Synthesis links the network before applying SDC. Refresh explicit loads
    // here as well as during link, and undo removed constraints on the same netlist.
    impl_->network->clear_load_overrides();
    for (const auto& load : impl_->sdc->set_loads()) {
        for (auto pin : load.pins)
            impl_->network->set_load_override(pin, load.capacitance * 1e-12f /
                liberty::pin_cap_unit(*impl_->network, *impl_->liberty, pin));
    }
    mark_all_dirty();
}

void TimingEngine::apply_design_constraints(edacraft::core::DesignDB& design,
                                            bool verbose) {
    auto pin_resolver = [&design, this](const std::string& name) -> std::vector<PinId> {
        std::vector<PinId> pins;
        for (uint32_t pin_id : design.runtime_pins_for_alias("ftimer", name)) {
            PinId pin{pin_id};
            if (valid(pin)) pins.push_back(pin);
        }
        if (!pins.empty()) return pins;
        auto pin = find_pin(name);
        if (pin) pins.push_back(*pin);
        return pins;
    };
    auto string_interner = [&design](const std::string& name) -> uint32_t {
        return design.strings().intern(name);
    };

    apply_constraints(design.constraints(), pin_resolver, string_interner, verbose);
    design.resolved_constraints() = export_resolved_constraints(*impl_->sdc,
                                                                &impl_->pin_bindings);
}

void TimingEngine::set_aocv_derate(const std::vector<AocvPoint>& points) {
    std::vector<te::AocvPoint> te_points;
    te_points.reserve(points.size());
    for (const auto& p : points) {
        te_points.push_back({p.depth, p.late_derate, p.early_derate});
    }
    impl_->sdc->set_aocv_derate(std::move(te_points));
}

void TimingEngine::link_design() {
    impl_->clock_pin_data_paths.clear();
    auto& network = *impl_->network;
    auto& liberty = *impl_->liberty;

    std::vector<std::vector<InstanceId>> instances_by_cell(network.cell_count());
    for (uint32_t iid = 0; iid < network.instance_count(); ++iid) {
        InstanceId inst_id{iid};
        const auto& inst = network.instance(inst_id);
        if (inst.cell.id < instances_by_cell.size()) {
            instances_by_cell[inst.cell.id].push_back(inst_id);
        }
    }

    struct LinkedPinInfo {
        PortDirection direction = PortDirection::Internal;
        LibertyPinId liberty_pin = NULL_LIBERTY_PIN;
        std::array<float, 4> load_cap{};
    };

    size_t linked = 0;
    // Link each network cell to its Liberty counterpart by name.
    // Both use the same string pool, so StringId comparison is valid.
    for (uint32_t cid = 0; cid < network.cell_count(); ++cid) {
        CellId cell_id{cid};
        const auto& cell_data = network.cell(cell_id);

        for (uint32_t lib_idx = 0; lib_idx < liberty.library_count(); ++lib_idx) {
            auto& lib = liberty.library(lib_idx);
            auto found = lib.find_cell(cell_data.name);
            if (found) {
                LibertyCellId lib_cell_id{*found};
                network.set_liberty_cell(cell_id, LibraryId{lib_idx}, lib_cell_id);
                ++linked;

                // Update pin directions and capacitance from Liberty model
                const auto& lib_cell = lib.cells[lib_cell_id.id];
                std::unordered_map<uint32_t, LinkedPinInfo> linked_pins;
                linked_pins.reserve(lib_cell.pins.size());
                for (uint32_t pi = 0; pi < lib_cell.pins.size(); ++pi) {
                    const auto& lib_pin = lib_cell.pins[pi];
                    LinkedPinInfo info;
                    info.direction = liberty::to_network_direction(lib_pin.direction);
                    info.liberty_pin = LibertyPinId{pi};
                    for (auto mm : {MinMax::Min, MinMax::Max})
                      for (unsigned rf = 0; rf < 2; ++rf) {
                        const float receiver = liberty::lumped_receiver_capacitance(
                            lib_cell, lib_pin, static_cast<Transition>(rf), mm);
                        const float blend = receiver_cap_blend_factor();
                        const float base = liberty::static_pin_capacitance(
                            lib_pin, static_cast<Transition>(rf), mm);
                        info.load_cap[mm_rf_index(mm, static_cast<Transition>(rf))] = receiver > 0.0f
                            ? base * (1.0f - blend) + receiver * blend : base;
                    }
                    linked_pins[lib_pin.name] = info;
                }

                for (InstanceId inst_id : instances_by_cell[cid]) {
                    // Omitted/open output connections still exist physically:
                    // their internal power and Liberty state conditions must
                    // be evaluated, even with zero external capacitance.
                    // Materialize them before graph construction; never create
                    // a missing input or connect an open output to user nets.
                    for (const auto& lib_pin : lib_cell.pins) {
                        if (liberty::to_network_direction(lib_pin.direction)!=PortDirection::Output) continue;
                        const std::string pin_name(network.str(lib_pin.name));
                        auto pin=network.find_pin(inst_id,pin_name);
                        if (!pin) {
                            pin=network.create_pin(pin_name,inst_id,PortDirection::Output);
                            network.add_pin(inst_id,*pin);
                        }
                        if (!valid(network.pin(*pin).net)) {
                            const std::string base="__ftimer_open__/"+std::string(network.instance_name(inst_id))+"/"+pin_name;
                            std::string name=base;
                            for (unsigned suffix=1;network.find_net(name);++suffix) name=base+"/"+std::to_string(suffix);
                            network.connect_pin_to_net(*pin,network.create_net(name));
                        }
                    }
                    const auto& inst = network.instance(inst_id);
                    for (auto pid : inst.pins) {
                        const auto& pin_data = network.pin(pid);
                        auto pin_it = linked_pins.find(pin_data.name);
                        if (pin_it == linked_pins.end()) continue;
                        network.set_pin_direction(pid, pin_it->second.direction);
                        network.set_liberty_pin(pid, pin_it->second.liberty_pin);
                        for (auto mm : {MinMax::Min, MinMax::Max})
                            for (auto rf : {Transition::Rise, Transition::Fall})
                                network.set_load_capacitance(pid, mm, rf,
                                    pin_it->second.load_cap[mm_rf_index(mm, rf)]);
                    }
                }
                break;
            }
        }
    }
    // Rebuild net drivers now that pin directions are correct
    network.rebuild_net_connections();

    std::vector<std::pair<uint32_t, const ec::LibertyLibrary::WireLoadModel*>> default_wire_loads;
    if (impl_->liberty) {
        default_wire_loads.reserve(impl_->liberty->library_count());
        for (uint32_t li = 0; li < impl_->liberty->library_count(); ++li) {
            const auto& lib = impl_->liberty->library(li);
            if (lib.wire_load_models.empty()) continue;
            uint32_t wlm_name = lib.default_wire_load;
            if (wlm_name == UINT32_MAX) continue;
            for (const auto& model : lib.wire_load_models) {
                if (model.name == wlm_name) {
                    default_wire_loads.push_back({li, &model});
                    break;
                }
            }
        }
    }

    // Pre-compute Pi models for all nets.
    // Priority: 1) SPEF parasitics > 2) Wire Load Model > 3) None (zero wire delay)
    for_each_driven_net([&](const DrivenNetInfo& driven) {
        NetId net = driven.net;
        const auto& net_data = impl_->network->net(net);
        if (!valid(net_data.driver) || driven.driver_cell_name.find("__assign__") == 0) return;

        // Try SPEF parasitics first
        auto rc = impl_->parasitics->get_network(net);
        if (rc && rc->driver_node_id != UINT32_MAX) {
            PiModel pi = impl_->wire_calc->reduce_to_pi(*rc, rc->driver_node_id, {});
            if (pi.c1 > 0.0f || pi.c2 > 0.0f || pi.rpi > 0.0f) {
                for (int mm_rf = 0; mm_rf < 4; ++mm_rf)
                    impl_->parasitics->set_reduced(net_data.driver, mm_rf, pi);
                return;
            }
        }

        // Fallback to Wire Load Model: compute Pi model from WLM tables.
        uint32_t preferred_wlm_library = UINT32_MAX;
        const auto& driver = impl_->network->pin(net_data.driver);
        if (valid(driver.instance)) {
            const auto& cell = impl_->network->cell(impl_->network->instance(driver.instance).cell);
            if (valid(cell.liberty_library))
                for (const auto& entry : default_wire_loads)
                    if (entry.first == cell.liberty_library.id) preferred_wlm_library = entry.first;
        }
        for (const auto& [wlm_library, wlm] : default_wire_loads) {
            if (!wlm) continue;
            if (preferred_wlm_library != UINT32_MAX && wlm_library != preferred_wlm_library) continue;

            const uint32_t fanout = driven.fanout;

            // Compute total wire length from WLM
            float length = wlm->get_length(fanout);
            if (length <= 0.0f) continue;

            // R_total = resistance * length (kOhm), C_total = capacitance * length (pF)
            const auto& units = impl_->liberty->library(wlm_library).units;
            float r_total = wlm->resistance * length * units.resistance; // kOhm
            float c_total = wlm->capacitance * length * units.capacitance_unit_farads / 1e-12f; // pF

            // Convert to Pi model: PiModel uses fF and Ohms
            // c1 = C_total/2 (pF -> fF: * 1e3), c2 = C_total/2, rpi = R_total (kOhm -> Ohm: * 1e3)
            PiModel pi;
            pi.c1 = (c_total / 2.0f) * 1000.0f;   // pF -> fF
            pi.c2 = (c_total / 2.0f) * 1000.0f;   // pF -> fF
            pi.rpi = r_total * 1000.0f;           // kOhm -> Ohm
            pi.cap_scale = 1e-15f;                // fF to farads

            if (pi.c1 > 0.0f || pi.c2 > 0.0f || pi.rpi > 0.0f) {
                for (int mm_rf = 0; mm_rf < 4; ++mm_rf)
                    impl_->parasitics->set_reduced(net_data.driver, mm_rf, pi);
            }
            break; // use first library with WLM
        }
    });

    // Apply SDC set_load constraints to output port pins
    if (impl_->sdc) {
        for (const auto& sl : impl_->sdc->set_loads()) {
            for (auto pin : sl.pins) {
                network.set_load_override(pin, sl.capacitance * 1e-12f /
                    liberty::pin_cap_unit(network, liberty, pin));
            }
        }
    }

    // Diagnostic: report unlinked cells and nets without drivers
    size_t unlinked_instances = 0;
    std::unordered_map<std::string, int> unlinked_cell_counts;
    for (uint32_t iid = 0; iid < network.instance_count(); ++iid) {
        const auto& inst = network.instance(InstanceId{iid});
        const auto& cell_data = network.cell(inst.cell);
        if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell)) {
            ++unlinked_instances;
            unlinked_cell_counts[std::string(network.cell_name(inst.cell))]++;
        }
    }
    if (impl_->verbose && unlinked_instances > 0) {
        std::cerr << "[DIAG] Unlinked instances: " << unlinked_instances << "\n";
        for (const auto& [cname, cnt] : unlinked_cell_counts) {
            std::cerr << "[DIAG]   Cell '" << cname << "': " << cnt << " instances\n";
        }
    }
    size_t no_driver_nets = 0;
    size_t no_load_nets = 0;
    for (uint32_t nid = 0; nid < network.net_count(); ++nid) {
        const auto& n = network.net(NetId{nid});
        if (!valid(n.driver)) ++no_driver_nets;
        if (n.loads.empty()) ++no_load_nets;
    }
    if (impl_->verbose && no_driver_nets > 0) {
        std::cerr << "[DIAG] Nets without driver: " << no_driver_nets << "\n";
    }
    if (impl_->verbose && no_load_nets > 0) {
        std::cerr << "[DIAG] Nets without loads: " << no_load_nets << "\n";
    }

    // Debug: print all undriven nets with load counts
    if (impl_->verbose) {
        int undriven_printed = 0;
        for (uint32_t nid = 0; nid < network.net_count(); ++nid) {
            NetId net{nid};
            const auto& n = network.net(net);
            if (!valid(n.driver) && n.loads.size() > 0) {
                std::cerr << "[DIAG] Undriven net " << network.net_name(net)
                          << " loads=" << n.loads.size() << "\n";
                if (++undriven_printed >= 20) break;
            }
        }
    }
}

void TimingEngine::update_timing() {
    if (!impl_->graph) return;
    impl_->last_dirty_vertices.clear();

    // Build timing graph
    impl_->graph->set_verbose(impl_->verbose);
    impl_->graph->build(*impl_->network, *impl_->liberty, impl_->sdc.get());

    // Propagate arrivals
    float vdd = impl_->voltage;
    if (impl_->liberty->library_count() > 0) {
        vdd = impl_->liberty->library(0).units.voltage;
    }
    ArrivalPropagator propagator(
        *impl_->graph,
        *impl_->network,
        *impl_->liberty,
        *impl_->parasitics,
        *impl_->gate_calc,
        *impl_->csm_calc,
        *impl_->wire_calc,
        impl_->sdc.get(),
        vdd
    );
    propagator.refine_receiver_caps(*impl_->network);
    propagator.propagate_all();


    // Back-propagate required times
    RequiredPropagator req_prop(*impl_->graph, *impl_->network, *impl_->liberty, impl_->sdc.get(), &propagator);
    req_prop.propagate_all();

    impl_->clock_pin_data_paths = propagator.clock_pin_data_paths();

    // Diagnostic: count pins with -inf arrival
    size_t neg_inf_pins = 0;
    std::unordered_map<std::string, int> neg_inf_by_cell;
    for (uint32_t pid = 0; pid < impl_->network->pin_count(); ++pid) {
        PinId pin{pid};
        uint32_t vid_r = pid * 2 + static_cast<uint32_t>(Transition::Rise);
        uint32_t vid_f = pid * 2 + static_cast<uint32_t>(Transition::Fall);
        float r_arr = impl_->graph->arrival(vid_r, MinMax::Max, Transition::Rise).value;
        float f_arr = impl_->graph->arrival(vid_f, MinMax::Max, Transition::Fall).value;
        if (r_arr <= std::numeric_limits<float>::lowest() / 2 ||
            f_arr <= std::numeric_limits<float>::lowest() / 2) {
            ++neg_inf_pins;
            const auto& pin_data = impl_->network->pin(pin);
            std::string cell_name = "(top_port)";
            if (valid(pin_data.instance)) {
                const auto& inst = impl_->network->instance(pin_data.instance);
                cell_name = std::string(impl_->network->cell_name(inst.cell));
            }
            neg_inf_by_cell[cell_name]++;
        }
    }
    if (impl_->verbose && neg_inf_pins > 0) {
        std::cerr << "[DIAG] Pins with -inf arrival: " << neg_inf_pins << "\n";
        for (const auto& [cname, cnt] : neg_inf_by_cell) {
            std::cerr << "[DIAG]   Cell '" << cname << "': " << cnt << " pins\n";
        }
    }

    impl_->graph->increment_generation();
}

void TimingEngine::update_incremental() {
    if (!impl_->graph) return;
    impl_->last_dirty_vertices = impl_->dirty_tracker.queued_vertices();
    if (impl_->last_dirty_vertices.empty()) {
        impl_->dirty_tracker.clear();
        impl_->graph->clear_dirty();
        return;
    }
    // Synthetic SDC data checks are evaluated after a complete required-time
    // pass. Rebuild once here so an incremental update cannot publish stale
    // data-check coverage/results.
    if (impl_->sdc && !impl_->sdc->data_checks().empty()) {
        impl_->dirty_tracker.clear();
        update_timing();
        return;
    }

    // Flush queued dirty marks to the graph
    impl_->dirty_tracker.flush();

    // Forward propagation of arrivals through dirty cone
    float vdd_incr = impl_->voltage;
    if (impl_->liberty->library_count() > 0) {
        vdd_incr = impl_->liberty->library(0).units.voltage;
    }
    ArrivalPropagator arr_prop(
        *impl_->graph,
        *impl_->network,
        *impl_->liberty,
        *impl_->parasitics,
        *impl_->gate_calc,
        *impl_->csm_calc,
        *impl_->wire_calc,
        impl_->sdc.get(),
        vdd_incr
    );
    arr_prop.set_clock_pin_data_paths(impl_->clock_pin_data_paths);
    arr_prop.propagate_dirty();
    const bool receiver_changed = arr_prop.refine_receiver_caps(*impl_->network);
    if (receiver_changed) arr_prop.propagate_all();
    const bool full_update = receiver_changed || arr_prop.used_full_propagation();
    if (full_update) {
        // A receiver output load can change the upstream driver's delay.
        // Publish every affected point/arc to incremental bridge consumers.
        impl_->last_dirty_vertices.resize(impl_->graph->vertex_count());
        for (uint32_t vid = 0; vid < impl_->graph->vertex_count(); ++vid)
            impl_->last_dirty_vertices[vid] = vid;
    }

    // Backward propagation of required times through dirty cone
    RequiredPropagator req_prop(*impl_->graph, *impl_->network, *impl_->liberty, impl_->sdc.get(), &arr_prop);
    if (full_update) req_prop.propagate_all();
    else req_prop.propagate_dirty();
    impl_->clock_pin_data_paths = arr_prop.clock_pin_data_paths();

    // Clear dirty flags once both forward and backward propagation are done
    impl_->graph->clear_dirty();
    impl_->graph->increment_generation();
}

std::optional<ClockPinTiming> TimingEngine::get_clock_pin_timing(PinId pin, Transition rf, MinMax mm) const {
    if (!impl_->graph || pin.id > UINT32_MAX / 2) return std::nullopt;
    const uint32_t vid = pin.id * 2 + static_cast<unsigned>(rf);
    if (vid >= impl_->graph->vertex_count()) return std::nullopt;
    const auto found = impl_->clock_pin_data_paths.find(pin.id);
    if (found == impl_->clock_pin_data_paths.end()) return std::nullopt;
    const auto slot = 2 * mm_rf_index(mm, rf);
    return ClockPinTiming{impl_->graph->arrival(vid, mm, rf).value,
        impl_->graph->slew(vid, mm, rf).value, found->second[slot], found->second[slot + 1]};
}

float TimingEngine::get_arrival(PinId pin, Transition rf, MinMax mm) const {
    if (!impl_->graph) return 0.0f;
    // Map pin ID to vertex ID
    if (pin.id > UINT32_MAX / 2) return 0.0f;
    uint32_t vid = pin.id * 2 + static_cast<int>(rf);
    if (vid >= impl_->graph->vertex_count()) return 0.0f;
    if (const auto* label = impl_->graph->worst_launch_label(vid, mm)) return label->arrival;
    float value = impl_->graph->arrival(vid, mm, rf).value;
    // Preserve unavailable timing for a valid pin.
    return value;
}

float TimingEngine::get_required(PinId pin, Transition rf, MinMax mm) const {
    const float unavailable = mm == MinMax::Max ? Delay::INF().value : Delay::NEG_INF().value;
    if (!impl_->graph) return unavailable;
    if (pin.id > UINT32_MAX / 2) return unavailable;
    uint32_t vid = pin.id * 2 + static_cast<int>(rf);
    if (vid >= impl_->graph->vertex_count()) return unavailable;
    if (const auto* label = impl_->graph->worst_launch_label(vid, mm)) return label->required;
    return impl_->graph->required(vid, mm, rf).value;
}

float TimingEngine::get_slew(PinId pin, Transition rf, MinMax mm) const {
    if (!impl_->graph) return 0.0f;
    if (pin.id > UINT32_MAX / 2) return 0.0f;
    uint32_t vid = pin.id * 2 + static_cast<int>(rf);
    if (vid >= impl_->graph->vertex_count()) return 0.0f;
    float value = impl_->graph->slew(vid, mm, rf).value;
    return std::isfinite(value) ? value : 0.0f;
}

float TimingEngine::get_slack(PinId pin, Transition rf, MinMax mm) const {
    const float unavailable = std::numeric_limits<float>::quiet_NaN();
    if (!impl_->graph) return unavailable;
    if (pin.id > UINT32_MAX / 2) return unavailable;
    uint32_t vid = pin.id * 2 + static_cast<int>(rf);
    if (vid >= impl_->graph->vertex_count()) return unavailable;
    if (const auto* label = impl_->graph->worst_launch_label(vid, mm))
        return slack_from_values(label->arrival, label->required, mm);
    float req = impl_->graph->required(vid, mm, rf).value;
    float arr = impl_->graph->arrival(vid, mm, rf).value;
    if (!std::isfinite(req) || !std::isfinite(arr)) return unavailable;
    return slack_from_values(arr, req, mm);
}

float TimingEngine::worst_slack(MinMax mm, TimingCheckKind kind) const {
    if (!impl_->graph) return 0.0f;
    float worst = std::numeric_limits<float>::infinity();
    for (uint32_t vid = 0; vid < impl_->graph->vertex_count(); ++vid) {
        if (!impl_->graph->is_endpoint(vid)) continue;
        if (!timing_check_matches(impl_->graph->endpoint_check_kind(vid, mm), kind)) continue;
        if (impl_->graph->has_launch_labels()) {
            if (const auto* label = impl_->graph->worst_launch_label(vid, mm))
                worst = std::min(worst, slack_from_values(label->arrival, label->required, mm));
            continue;
        }
        for (int rf = 0; rf < 2; ++rf) {
            auto transition = static_cast<Transition>(rf);
            float arrival = impl_->graph->arrival(vid, mm, transition).value;
            float required = impl_->graph->required(vid, mm, transition).value;
            if (!std::isfinite(arrival) || !std::isfinite(required)) continue;
            float slack = slack_from_values(arrival, required, mm);
            if (slack < worst) worst = slack;
        }
    }
    for (const auto& check : impl_->graph->check_results()) {
        if (check.coverage.analysis != mm ||
            check.coverage.state != CheckCoverageState::Evaluated ||
            !timing_check_matches(check.coverage.kind, kind) ||
            !std::isfinite(check.slack)) continue;
        worst = std::min(worst, check.slack);
    }
    return worst;
}

uint64_t TimingEngine::timing_generation() const {
    if (!impl_->graph) return 0;
    return impl_->graph->generation();
}

std::vector<PinId> TimingEngine::endpoint_pins() const {
    std::vector<PinId> endpoints;
    if (!impl_->network) return endpoints;

    const auto& network = *impl_->network;
    auto is_async_control_name = [](std::string_view name) {
        return name == "RD" || name == "RDN" || name == "CD" ||
               name == "CDN" || name == "SET" || name == "SDN" ||
               name == "PRE" || name == "PRESET" || name == "CLR" ||
               name == "CLEAR" || name == "RESET" || name == "RST";
    };

    for (uint32_t pid = 0; pid < network.pin_count(); ++pid) {
        PinId pin{pid};
        const auto& pd = network.pin(pin);
        if (!valid(pd.instance) || pd.direction != PortDirection::Input) continue;

        const auto& inst = network.instance(pd.instance);
        std::string_view cell_name = network.cell_name(inst.cell);
        if (cell_name == "__top__") {
            endpoints.push_back(pin);
            continue;
        }

        std::string_view pin_name = network.pin_name(pin);
        if (is_async_control_name(pin_name)) continue;

        const auto& cell_data = network.cell(inst.cell);
        if (!valid(cell_data.liberty_library) || !valid(cell_data.liberty_cell) ||
            !impl_->liberty) {
            continue;
        }
        const auto& lib_cell = impl_->liberty->cell(
            liberty::to_core(cell_data.liberty_library),
            liberty::to_core(cell_data.liberty_cell));
        for (const auto& arc : lib_cell.arcs) {
            if ((arc.type == ec::LibertyTimingType::SetupRising ||
                 arc.type == ec::LibertyTimingType::SetupFalling) &&
                arc.to_pin == pd.name) {
                endpoints.push_back(pin);
                break;
            }
        }
    }
    return endpoints;
}

std::vector<TimingCheckCoverage> TimingEngine::timing_check_coverage() const {
    return impl_->graph ? impl_->graph->check_coverage() : std::vector<TimingCheckCoverage>{};
}

std::vector<TimingCheckResult> TimingEngine::timing_check_results() const {
    return impl_->graph ? impl_->graph->check_results() : std::vector<TimingCheckResult>{};
}

std::vector<PathReport> TimingEngine::report_check_paths(MinMax mm, int count, TimingCheckKind kind, bool balance_groups, std::string_view path_group) const {
    if (!impl_->graph) return {};
    auto paths = PathCollector::collect_check_paths(*impl_->graph, *impl_->network,
        mm, count, impl_->sdc.get(), kind, balance_groups, path_group);
    std::vector<PathReport> result;
    result.reserve(paths.size());
    for (auto& path : paths) {
        PathReport report{path.slack, path.cppr, path.start_clock_domain,
            path.end_clock_domain, std::move(path.point_names), std::move(path.cell_names),
            std::move(path.delays), std::move(path.arrivals), std::move(path.slews),
            std::move(path.transitions), path.check_kind, std::move(path.check)};
        report.path_group = std::move(path.path_group);
        if (report.check) {
            auto full_name = [&](PinId pin) {
                const auto& pd = impl_->network->pin(pin);
                std::string name;
                if (valid(pd.instance)) {
                    const auto& inst = impl_->network->instance(pd.instance);
                    if (impl_->network->cell_name(inst.cell) != "__top__")
                        name = std::string(impl_->network->instance_name(pd.instance)) + "/";
                }
                return name + std::string(impl_->network->pin_name(pin));
            };
            if (valid(report.check->related))
                report.check_related_name = full_name(report.check->related);
            if (valid(report.check->coverage.pin))
                report.check_endpoint_name = full_name(report.check->coverage.pin);
        }
        result.push_back(std::move(report));
    }
    return result;
}

std::vector<PathReport> TimingEngine::report_pba_paths(MinMax mm, int count,
    std::string_view group, size_t limit, TimingCheckKind kind) const {
    if (!impl_->graph || count <= 0) return {};
    // Work on a private graph. Reporting must never replace the GBA snapshot
    // consumed by incremental optimization or the fsyn bridge.
    TimingGraph graph = *impl_->graph;
    float vdd = impl_->liberty->library_count() ? impl_->liberty->library(0).units.voltage : impl_->voltage;
    ArrivalPropagator arrival(graph, *impl_->network, *impl_->liberty, *impl_->parasitics,
        *impl_->gate_calc, *impl_->csm_calc, *impl_->wire_calc, impl_->sdc.get(), vdd);
    arrival.propagate_all();
    RequiredPropagator required(graph, *impl_->network, *impl_->liberty, impl_->sdc.get(), &arrival, true, limit);
    required.propagate_all();
    auto paths = PathCollector::collect_check_paths(graph, *impl_->network, mm,
        count, impl_->sdc.get(), kind, false, group);
    std::vector<PathReport> result;
    for (auto& p : paths) {
        PathReport report{p.slack, p.cppr, p.start_clock_domain, p.end_clock_domain,
            std::move(p.point_names), std::move(p.cell_names), std::move(p.delays),
            std::move(p.arrivals), std::move(p.slews), std::move(p.transitions), p.check_kind, std::move(p.check)};
        report.path_group = std::move(p.path_group); report.path_based = true;
        auto name = [&](PinId pin) {
            const auto& data = impl_->network->pin(pin);
            std::string prefix;
            if (valid(data.instance) && impl_->network->cell_name(impl_->network->instance(data.instance).cell) != "__top__")
                prefix = std::string(impl_->network->instance_name(data.instance)) + "/";
            return prefix + std::string(impl_->network->pin_name(pin));
        };
        if (report.check && valid(report.check->related)) report.check_related_name = name(report.check->related);
        if (report.check) report.check_endpoint_name = name(report.check->coverage.pin);
        result.push_back(std::move(report));
    }
    return result;
}

std::vector<PinId> TimingEngine::timing_check_endpoints(TimingCheckKind kind) const {
    std::vector<PinId> result;
    if (!impl_->graph) return result;
    for (uint32_t pid = 0; pid < impl_->network->pin_count(); ++pid) {
        bool include = false;
        for (auto mm : {MinMax::Min, MinMax::Max}) for (uint32_t rf = 0; rf < 2; ++rf) {
            const auto vid = pid * 2 + rf;
            if (!impl_->graph->is_endpoint(vid)) continue;
            const auto k = impl_->graph->endpoint_check_kind(vid, mm);
            include |= k != TimingCheckKind::None && timing_check_matches(k, kind);
        }
        if (include) result.push_back(PinId{pid});
    }
    for (const auto& check : impl_->graph->check_results()) {
        if (check.coverage.state == CheckCoverageState::Evaluated &&
            timing_check_matches(check.coverage.kind, kind) &&
            std::find(result.begin(), result.end(), check.coverage.pin) == result.end()) {
            result.push_back(check.coverage.pin);
        }
    }
    return result;
}

std::vector<PathReport> TimingEngine::report_worst_paths(MinMax mm, int count, TimingCheckKind kind, std::string_view path_group) const {
    if (!impl_->graph) return {};
    auto raw = PathCollector::collect_worst_paths(*impl_->graph, *impl_->network, mm, count, impl_->sdc.get(), false, kind, path_group);
    std::vector<PathReport> result;
    for (auto& r : raw) {
        result.push_back({r.slack, r.cppr, r.start_clock_domain,
                          r.end_clock_domain, std::move(r.point_names),
                          std::move(r.cell_names),
                          std::move(r.delays), std::move(r.arrivals),
                          std::move(r.slews), std::move(r.transitions), r.check_kind});
        result.back().path_group = std::move(r.path_group);
    }
    return result;
}

std::vector<PathReport> TimingEngine::report_longest_paths(
    MinMax mm, int count) const {
    if (!impl_->graph) return {};
    auto raw = PathCollector::collect_worst_paths(
        *impl_->graph, *impl_->network, mm, count, impl_->sdc.get(), true);
    std::vector<PathReport> result;
    result.reserve(raw.size());
    for (auto& r : raw) {
        result.push_back({r.slack, r.cppr, r.start_clock_domain,
                          r.end_clock_domain, std::move(r.point_names),
                          std::move(r.cell_names), std::move(r.delays),
                          std::move(r.arrivals), std::move(r.slews),
                          std::move(r.transitions), r.check_kind});
        result.back().path_group = std::move(r.path_group);
    }
    return result;
}

void TimingEngine::mark_net_dirty(NetId net) {
    if (!impl_->graph || !valid(net)) return;
    impl_->dirty_tracker.mark_net(net, *impl_->network);
}

void TimingEngine::mark_pin_dirty(PinId pin) {
    if (!impl_->graph) return;
    impl_->dirty_tracker.mark_pin(pin);
}

void TimingEngine::mark_all_dirty() {
    if (!impl_->graph) return;
    for (uint32_t vid = 0; vid < impl_->graph->vertex_count(); ++vid) {
        impl_->dirty_tracker.mark_vertex(vid);
    }
}

std::optional<NetId> TimingEngine::find_net(std::string_view name) const {
    if (!impl_->network) return std::nullopt;
    return impl_->network->find_net(name);
}

std::optional<int> TimingEngine::literal_constant_value(
    PinId pin, std::string_view expected_net_name) const {
    if (!impl_->network || !valid(pin) || pin.id >= impl_->network->pin_count())
        return std::nullopt;
    const auto& network = *impl_->network;
    const auto net_id = network.pin(pin).net;
    if (!valid(net_id) || net_id.id >= network.net_count() ||
        network.net_name(net_id) != expected_net_name) return std::nullopt;
    const auto& net = network.net(net_id);
    if (valid(net.driver) || (net.constant_value != 0 && net.constant_value != 1))
        return std::nullopt;
    return net.constant_value;
}

std::optional<PinId> TimingEngine::find_pin(std::string_view name) const {
    if (!impl_->network) return std::nullopt;
    const size_t delimiter = name.find_last_of("/:");
    if (delimiter != std::string_view::npos && delimiter > 0 &&
        delimiter + 1 < name.size()) {
        const std::string_view instance_name = name.substr(0, delimiter);
        const std::string_view port_name = name.substr(delimiter + 1);
        auto instance = impl_->network->find_instance(instance_name);
        if (instance) {
            auto pin = impl_->network->find_pin(*instance, port_name);
            if (pin) return pin;
        }
    }
    for (uint32_t pid = 0; pid < impl_->network->pin_count(); ++pid) {
        PinId pin{pid};
        if (impl_->network->pin_name(pin) == name) return pin;
    }
    return std::nullopt;
}

std::optional<PinId> TimingEngine::find_instance_pin(
    std::string_view instance_name,
    std::string_view port_name) const {
    if (!impl_->network) return std::nullopt;
    auto instance = impl_->network->find_instance(instance_name);
    if (!instance) return std::nullopt;
    return impl_->network->find_pin(*instance, port_name);
}

void TimingEngine::for_each_driven_net(const DrivenNetVisitor& visitor) const {
    if (!impl_->network || !visitor) return;
    const auto& network = *impl_->network;
    // Continuous assignments are electrical connectivity. Build their net
    // components once per scan, then count real receiver pins once per
    // component. Counting the assign inputs misses downstream branching and
    // counts dead aliases as receivers. A component scan also avoids walking
    // every suffix separately on long alias chains.
    std::vector<uint32_t> parent(network.net_count());
    std::vector<uint8_t> rank(network.net_count(), 0);
    std::vector<uint8_t> assign_cells(network.cell_count(), 0);
    for (uint32_t nid = 0; nid < network.net_count(); ++nid) parent[nid] = nid;
    for (uint32_t cid = 0; cid < network.cell_count(); ++cid)
        assign_cells[cid] = network.cell_name(CellId{cid}).find("__assign__") == 0;
    auto root = [&](uint32_t nid) {
        while (parent[nid] != nid) {
            parent[nid] = parent[parent[nid]];
            nid = parent[nid];
        }
        return nid;
    };
    auto is_assign = [&](PinId pin) {
        const auto& pd = network.pin(pin);
        return valid(pd.instance) && assign_cells[network.instance(pd.instance).cell.id];
    };
    for (uint32_t nid = 0; nid < network.net_count(); ++nid) {
        for (auto pin : network.net(NetId{nid}).loads) {
            if (!is_assign(pin)) continue;
            for (auto output : network.instance(network.pin(pin).instance).pins) {
                const auto& pd = network.pin(output);
                if (pd.direction != PortDirection::Output || !valid(pd.net)) continue;
                auto left = root(nid), right = root(pd.net.id);
                if (left == right) continue;
                if (rank[left] < rank[right]) std::swap(left, right);
                parent[right] = left;
                if (rank[left] == rank[right]) ++rank[left];
            }
        }
    }
    std::vector<uint32_t> receivers(network.net_count(), 0);
    std::vector<float> fanout_loads(network.net_count(), 0.f);
    auto pin_fanout_load = [&](PinId pin) {
        const auto& pd = network.pin(pin);
        if (!valid(pd.instance)) return 1.f;
        const auto& cell = network.cell(network.instance(pd.instance).cell);
        if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) return 1.f;
        const auto& lib = impl_->liberty->library(cell.liberty_library.id);
        const auto& pins = lib.cells[cell.liberty_cell.id].pins;
        const float load = valid(pd.liberty_pin) && pd.liberty_pin.id < pins.size()
            ? pins[pd.liberty_pin.id].fanout_load : -1.f;
        return load >= 0.f ? load : lib.default_fanout_load;
    };
    for (uint32_t nid = 0; nid < network.net_count(); ++nid) {
        for (auto pin : network.net(NetId{nid}).loads) {
            if (is_assign(pin)) continue;
            ++receivers[root(nid)];
            fanout_loads[root(nid)] += pin_fanout_load(pin);
        }
    }
    for (uint32_t nid = 0; nid < network.net_count(); ++nid) {
        NetId net{nid};
        const auto& nd = network.net(net);
        if (!valid(nd.driver) || nd.loads.empty()) continue;

        DrivenNetInfo info;
        info.net = net;
        info.name = std::string(network.net_name(net));
        info.fanout = receivers[root(nid)];
        info.fanout_load = fanout_loads[root(nid)];
        info.driver_pin = nd.driver;
        const auto& driver = network.pin(nd.driver);
        if (valid(driver.instance)) {
            const auto& inst = network.instance(driver.instance);
            info.driver_instance_name = std::string(network.instance_name(driver.instance));
            info.driver_cell_name = std::string(network.cell_name(inst.cell));
        }
        for (auto pin : nd.loads) {
            info.total_load_cap += network.pin(pin).load_cap;
        }
        // A top-level output port can be represented as the net driver.  In
        // that form an SDC set_load is attached to the driver pin rather than
        // to nd.loads; retain that constrained load in the runtime estimate.
        if (driver.load_cap > 0.0f && std::isfinite(driver.load_cap)) {
            info.total_load_cap += driver.load_cap;
        }
        visitor(info);
    }
}

uint32_t TimingEngine::pin_count() const {
    if (!impl_->network) return 0;
    return impl_->network->pin_count();
}

std::string_view TimingEngine::pin_name(PinId pin) const {
    if (!impl_->network) return "";
    return impl_->network->pin_name(pin);
}

std::string_view TimingEngine::pin_instance_name(PinId pin) const {
    if (!impl_->network) return "";
    const auto& pin_data = impl_->network->pin(pin);
    if (!valid(pin_data.instance)) return "";
    return impl_->network->instance_name(pin_data.instance);
}

float TimingEngine::get_net_cap(NetId net) const {
    if (!impl_->parasitics) return 0.0f;
    auto rc = impl_->parasitics->get_network(net);
    if (!rc) return 0.0f;

    float total = 0.0f;
    for (const auto& cap : rc->capacitors) {
        if (cap.node2 == UINT32_MAX) total += cap.capacitance;
    }
    return total;
}

float TimingEngine::get_net_terminal_load_cap(NetId net) const {
    if (!impl_->network || !valid(net) || net.id >= impl_->network->net_count()) return 0.f;
    const auto& network = *impl_->network;
    float driver_cap_unit = 1e-12f;
    const auto driver = network.net(net).driver;
    if (valid(driver) && valid(network.pin(driver).instance)) {
        const auto& cell = network.cell(network.instance(network.pin(driver).instance).cell);
        if (valid(cell.liberty_library))
            driver_cap_unit = impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
    }
    std::array<double, 2> total{{0., 0.}};
    std::vector<NetId> pending{net};
    std::unordered_set<uint32_t> visited, counted_pins;
    while (!pending.empty()) {
        const auto current = pending.back(); pending.pop_back();
        if (!visited.insert(current.id).second) continue;
        const auto& data = network.net(current);
        auto add = [&](PinId pin, bool is_driver) {
            if (!valid(pin) || !counted_pins.insert(pin.id).second) return;
            const auto& pd = network.pin(pin);
            // A real cell driver can carry a set_load resolved through a port
            // alias. Its load is external; a receiver's model load is not.
            // Top-level ports also belong to a runtime design instance; a
            // valid instance alone does not make a pin a Liberty receiver.
            if (valid(pd.liberty_pin) && !(is_driver && network.has_load_override(pin))) return;
            float unit = 1e-12f;
            if (valid(pd.instance)) {
                const auto& cell = network.cell(network.instance(pd.instance).cell);
                if (valid(cell.liberty_library))
                    unit = impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
            }
            for (unsigned rf = 0; rf < 2; ++rf)
                total[rf] += std::max(0.f, pd.load_cap_rf[rf]) * double(unit);
        };
        add(data.driver, true);
        for (auto pin : data.loads) {
            add(pin, false);
            const auto& pd = network.pin(pin);
            if (!valid(pd.instance)) continue;
            const auto& instance = network.instance(pd.instance);
            if (network.cell_name(instance.cell).find("__assign__") != 0) continue;
            for (auto output : instance.pins) {
                const auto& op = network.pin(output);
                if (op.direction == PortDirection::Output && valid(op.net)) pending.push_back(op.net);
            }
        }
    }
    return static_cast<float>(std::max(total[0], total[1]) / driver_cap_unit);
}

float TimingEngine::get_net_load_cap(NetId net) const {
    if (!impl_->network || !valid(net) || net.id >= impl_->network->net_count()) return 0.f;
    const auto& network = *impl_->network;
    const auto& nd = network.net(net);
    float driver_cap_unit = 1e-12f;
    if (valid(nd.driver)) {
        const auto& driver = network.pin(nd.driver);
        if (valid(driver.instance)) {
            const auto& cell = network.cell(network.instance(driver.instance).cell);
            if (valid(cell.liberty_library))
                driver_cap_unit = impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
        }
    }
    // Assign instances represent connectivity, not electrical isolation. Walk
    // their output nets, stopping at real cells. Count each physical net once
    // even when aliases revisit it; use an iterative walk for long chains.
    std::array<double, 2> total{{0., 0.}};
    std::vector<NetId> pending{net};
    std::unordered_set<uint32_t> visited;
    while (!pending.empty()) {
        const NetId current = pending.back(); pending.pop_back();
        if (!visited.insert(current.id).second) continue;
        const auto& current_net = network.net(current);
        double extracted = 0.;
        bool includes_pin_caps = false;
        if (impl_->parasitics) {
            if (const auto* rc = impl_->parasitics->get_network(current)) {
                includes_pin_caps = impl_->parasitics->includes_pin_caps(current);
                for (const auto& node : rc->nodes) {
                    double cap = double(node.gnd_cap) * rc->cap_scale;
                    if (includes_pin_caps && valid(node.pin) && network.has_load_override(node.pin))
                        cap = std::max(0., cap - double(liberty::extracted_pin_cap(network, *impl_->liberty, node.pin)) *
                            liberty::pin_cap_unit(network, *impl_->liberty, node.pin));
                    extracted += cap;
                }
            } else if (valid(current_net.driver)) {
                // With no full extraction, the reduced model contains wire only.
                if (const auto pi = impl_->parasitics->get_reduced(current_net.driver, mm_rf_index(MinMax::Max, Transition::Rise)))
                    extracted += double(pi->c1 + pi->c2) * pi->cap_scale;
            }
            extracted += double(impl_->parasitics->total_coupling_cap(current)) * 1e-12;
        }
        for (double& cap : total) cap += extracted;
        auto add_pin = [&](PinId pin, bool driver) {
            const auto& pd = network.pin(pin);
            const bool explicit_load = network.has_load_override(pin);
            if (driver && !explicit_load) return;
            if (includes_pin_caps && !explicit_load) return;
            float unit = 1e-12f;
            if (valid(pd.instance)) {
                const auto& cell = network.cell(network.instance(pd.instance).cell);
                if (valid(cell.liberty_library))
                    unit = impl_->liberty->library(cell.liberty_library.id).units.capacitance_unit_farads;
            }
            for (unsigned rf = 0; rf < 2; ++rf) total[rf] += double(pd.load_cap_rf[rf]) * unit;
        };
        for (auto pin : current_net.loads) {
            add_pin(pin, false);
            const auto& pd = network.pin(pin);
            if (!valid(pd.instance)) continue;
            const auto& instance = network.instance(pd.instance);
            if (network.cell_name(instance.cell).find("__assign__") != 0) continue;
            for (auto output : instance.pins) {
                const auto& output_pin = network.pin(output);
                if (output_pin.direction == PortDirection::Output && valid(output_pin.net))
                    pending.push_back(output_pin.net);
            }
        }
        if (valid(current_net.driver)) add_pin(current_net.driver, true);
    }
    return static_cast<float>(std::max(total[0], total[1]) / driver_cap_unit);
}

void TimingEngine::set_wire_pi_model(NetId net, float c1, float rpi, float c2,
                                     float cap_scale) {
    if (!impl_->parasitics || !impl_->network) return;
    const auto& nd = impl_->network->net(net);
    if (!valid(nd.driver)) return;
    PiModel model{c1, rpi, c2, cap_scale};
    for (int mm = 0; mm < 2; ++mm)
        for (int rf = 0; rf < 2; ++rf)
            impl_->parasitics->set_reduced(nd.driver, mm * 2 + rf, model);
}

float TimingEngine::get_cell_area(std::string_view cell_name) const {
    if (!impl_->liberty || !impl_->network) return 0.0f;
    uint32_t name_id = impl_->network->intern_string(cell_name);
    auto [lib_idx, cell_id] = impl_->liberty->find_cell_library(name_id);
    if (lib_idx < 0) return 0.0f;
    const auto& cell_data = impl_->liberty->cell(ec::LibraryHandle{static_cast<uint32_t>(lib_idx)}, cell_id);
    return cell_data.area;
}

float TimingEngine::get_cell_delay(std::string_view cell_name,
                                    std::string_view from_pin,
                                    std::string_view to_pin,
                                    float input_slew,
                                    float load_cap) const {
    if (!impl_->liberty || !impl_->network) return 0.0f;
    uint32_t cell_name_id = impl_->network->intern_string(cell_name);
    auto [lib_idx, cell_id] = impl_->liberty->find_cell_library(cell_name_id);
    if (lib_idx < 0) return 0.0f;

    uint32_t from_pin_id = impl_->network->intern_string(from_pin);
    uint32_t to_pin_id = impl_->network->intern_string(to_pin);

    const float unit_ns = liberty::time_unit_ns(impl_->liberty->library(lib_idx));
    const float library_input_slew = input_slew / unit_ns;
    const auto& cell_data = impl_->liberty->cell(ec::LibraryHandle{static_cast<uint32_t>(lib_idx)}, cell_id);
    for (const auto& arc : cell_data.arcs) {
        if (arc.from_pin == from_pin_id && arc.to_pin == to_pin_id) {
            if (ec::liberty_timing_type_is_check(arc.type) ||
                arc.type == ec::LibertyTimingType::Unknown) {
                // Clock-to-Q edge arcs propagate data; setup/hold are checks.
                continue;
            }
            float rise = arc.rise_delay.lookup(library_input_slew, load_cap);
            float fall = arc.fall_delay.lookup(library_input_slew, load_cap);
            return std::max(rise, fall) * unit_ns;
        }
    }
    return 0.0f;
}

float TimingEngine::get_cell_output_slew(std::string_view cell_name,
                                          std::string_view from_pin,
                                          std::string_view to_pin,
                                          float input_slew,
                                          float load_cap) const {
    if (!impl_->liberty || !impl_->network) return 0.0f;
    uint32_t cell_name_id = impl_->network->intern_string(cell_name);
    auto [lib_idx, cell_id] = impl_->liberty->find_cell_library(cell_name_id);
    if (lib_idx < 0) return 0.0f;

    uint32_t from_pin_id = impl_->network->intern_string(from_pin);
    uint32_t to_pin_id = impl_->network->intern_string(to_pin);

    const float unit_ns = liberty::time_unit_ns(impl_->liberty->library(lib_idx));
    const float library_input_slew = input_slew / unit_ns;
    const auto& cell_data = impl_->liberty->cell(ec::LibraryHandle{static_cast<uint32_t>(lib_idx)}, cell_id);
    for (const auto& arc : cell_data.arcs) {
        if (arc.from_pin == from_pin_id && arc.to_pin == to_pin_id) {
            if (ec::liberty_timing_type_is_check(arc.type) ||
                arc.type == ec::LibertyTimingType::Unknown) {
                continue;
            }
            float rise_slew = arc.rise_output_slew.lookup(library_input_slew, load_cap);
            float fall_slew = arc.fall_output_slew.lookup(library_input_slew, load_cap);
            if (rise_slew > 0.0f || fall_slew > 0.0f) {
                return std::max(rise_slew, fall_slew) * unit_ns;
            }
            // No slew table: fall back to input slew
            return input_slew;
        }
    }
    return input_slew;
}

TimingEngine::SiSummary TimingEngine::analyze_si() const {
    SiSummary result;
    if (!impl_->network || !impl_->parasitics) return result;
    for (uint32_t nid = 0; nid < impl_->network->net_count(); ++nid) {
        // Coupling entries are normalized to pF by the SPEF parser and by
        // add_coupling_capacitance(), independent of each net's RC C_UNIT.
        // Do not apply the local ground-cap scale a second time here.
        float coupling = impl_->parasitics->total_coupling_cap(NetId{nid});
        if (!(coupling > 0.0f) || !std::isfinite(coupling)) continue;
        ++result.victim_nets;
        result.total_coupling_cap += coupling;
        result.max_victim_coupling_cap = std::max(result.max_victim_coupling_cap, coupling);
    }
    return result;
}

std::vector<TimingEngine::SiCoupling> TimingEngine::analyze_si_detail() const {
    std::vector<SiCoupling> result;
    if (!impl_->network || !impl_->parasitics) return result;
    for (const auto& record : impl_->parasitics->coupling_records()) {
        if (!(record.capacitance > 0.0f) || !std::isfinite(record.capacitance)) continue;
        const float victim_total = impl_->parasitics->total_coupling_cap(record.net1);
        const float ratio = victim_total > 0.0f ? record.capacitance / victim_total : 0.0f;
        result.push_back({std::string(impl_->network->net_name(record.net1)),
                          std::string(impl_->network->net_name(record.net2)),
                          record.capacitance, victim_total, ratio});
    }
    std::sort(result.begin(), result.end(), [](const auto& lhs, const auto& rhs) {
        if (lhs.coupling_cap != rhs.coupling_cap)
            return lhs.coupling_cap > rhs.coupling_cap;
        if (lhs.victim_net != rhs.victim_net) return lhs.victim_net < rhs.victim_net;
        return lhs.aggressor_net < rhs.aggressor_net;
    });
    return result;
}

TimingEngine::DesignRuleLimits TimingEngine::design_rule_limits() const {
    if (!impl_->sdc) return {};
    const auto& rules = impl_->sdc->design_rules();
    return {rules.max_fanout, rules.max_capacitance, rules.max_transition};
}

std::vector<TimingEngine::DesignRuleViolation> TimingEngine::design_rule_violations() const {
    std::vector<DesignRuleViolation> result;
    if (!impl_->network || !impl_->graph) return result;
    const auto limits = design_rule_limits();
    for (uint32_t li=0;li<impl_->liberty->library_count();++li)
        if (!impl_->liberty->library(li).electrical_metadata_complete)
            throw std::runtime_error("Electrical rule reporting needs regenerated .ftlib v13 or Liberty text; legacy pin limits are incomplete");
    auto pin_limits = [&](PinId pin) {
        auto effective=limits;
        const auto& pd=impl_->network->pin(pin);
        if (!valid(pd.instance) || !valid(pd.liberty_pin)) return effective;
        const auto& cell=impl_->network->cell(impl_->network->instance(pd.instance).cell);
        if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) return effective;
        const auto& lib=impl_->liberty->library(cell.liberty_library.id);
        const auto& lp=lib.cells[cell.liberty_cell.id].pins.at(pd.liberty_pin.id);
        auto tighten=[](float& limit,float pin_limit,float fallback,float unit) {
            const float library_limit=pin_limit>=0 ? pin_limit : (fallback>0 ? fallback : -1.f);
            if (library_limit<0) return;
            const float value=library_limit*unit;
            limit=limit>=0 ? std::min(limit,value) : value;
        };
        tighten(effective.max_fanout,lp.max_fanout,lib.default_max_fanout,1.f);
        tighten(effective.max_capacitance,lp.max_capacitance,lib.default_max_capacitance,
                lib.units.capacitance_unit_farads*1e12f);
        tighten(effective.max_transition,lp.max_transition,lib.default_max_transition,
                lib.units.time_unit_seconds*1e9f);
        return effective;
    };
    auto append = [&](const char* rule, std::string object, float limit, float value) {
        if (limit >= 0.0f && std::isfinite(value) && value > limit)
            result.push_back({rule, std::move(object), limit, value});
    };
    for_each_driven_net([&](const DrivenNetInfo& net) {
        const auto effective=pin_limits(net.driver_pin);
        append("max_fanout", net.name, effective.max_fanout,
               net.fanout_load);
        // get_net_load_cap includes extracted wire and coupling capacitance,
        // receiver caps and SDC overrides without counting PIN_CAP twice.
        // Its result is in the driver's library units; SDC limits are pF.
        if (effective.max_capacitance >= 0.0f)
            append("max_capacitance", net.name, effective.max_capacitance,
                   get_net_load_cap(net.net) *
                   liberty::pin_cap_unit(*impl_->network, *impl_->liberty,
                                          net.driver_pin) * 1e12f);
    });
    // Distributed RC may make the receiving pin slower than its driver.
    // Scan each physical pin in both analyses rather than only max drivers.
    {
        for (uint32_t id = 0; id < pin_count(); ++id) {
            const PinId pin{id};
            const auto effective=pin_limits(pin);
            if (effective.max_transition<0.f) continue;
            const auto& pd = impl_->network->pin(pin);
            if (valid(pd.instance)) {
                const auto& inst = impl_->network->instance(pd.instance);
                if (impl_->network->cell_name(inst.cell).find("__assign__") == 0)
                    continue;
            }
            float slew = 0.0f;
            for (auto mm : {MinMax::Min, MinMax::Max})
                for (auto rf : {Transition::Rise, Transition::Fall})
                    slew = std::max(slew, get_slew(pin, rf, mm));
            std::string name;
            if (valid(pd.instance) && impl_->network->cell_name(
                    impl_->network->instance(pd.instance).cell) != "__top__")
                name = std::string(pin_instance_name(pin));
            if (!name.empty()) name += "/";
            name += std::string(pin_name(pin));
            append("max_transition", std::move(name), effective.max_transition, slew);
        }
    }
    std::sort(result.begin(), result.end(), [](const auto& a, const auto& b) {
        return std::tie(a.rule, a.object) < std::tie(b.rule, b.object);
    });
    return result;
}

void TimingEngine::add_coupling_capacitance(NetId net1, NetId net2, float capacitance) {
    if (!impl_->parasitics) return;
    impl_->parasitics->add_coupling_cap(net1, net2, capacitance);
}

void TimingEngine::save_state(std::string_view filepath) {
    if (!impl_->graph) return;
    MmapStore::save(*impl_->graph, std::string(filepath));
}

void TimingEngine::load_state(std::string_view filepath) {
    if (!impl_->graph) return;
    MmapStore::load(*impl_->graph, std::string(filepath));
    // The mmap snapshot contains the timing graph, not physical observations.
    impl_->clock_pin_data_paths.clear();
}

// ────────────────────────────────────────────────────────────
// Synthesis integration
// ────────────────────────────────────────────────────────────

GateViewAttachResult TimingEngine::attach_gate_view(
    const edacraft::core::GateNetlistView& view,
    const std::unordered_map<std::string, std::vector<std::string>>& port_aliases,
    edacraft::core::StringPool* shared_string_pool) {
    // Full attach replaces the complete logical network and timing graph.
    // Drop the previous generation before materializing the next network;
    // otherwise both multi-million-pin representations coexist while
    // network_from_gate_view() is running.
    impl_->dirty_tracker.clear();
    impl_->network.reset();
    impl_->clock_pin_data_paths.clear();
    impl_->graph = std::make_unique<TimingGraph>();
    impl_->graph->set_verbose(impl_->verbose);
    impl_->dirty_tracker.attach(*impl_->graph);
    impl_->last_dirty_vertices.clear();
#if defined(__GLIBC__)
    (void)malloc_trim(0);
#endif

    auto build = network_from_gate_view(view, port_aliases, shared_string_pool);

    GateViewAttachResult result;
    result.pins_by_full_name = std::move(build.pins_by_full_name);
    result.pin_to_core_pin = std::move(build.pin_to_core_pin);
    result.core_pin_to_pin = std::move(build.core_pin_to_pin);
    result.port_aliases = std::move(build.port_aliases);

    impl_->network = std::move(build.network);
    impl_->pin_bindings.clear();
    impl_->reverse_pin_bindings.clear();
    for (const auto& [pin_id, core_pin] : result.pin_to_core_pin) {
        PinId pin{pin_id};
        if (!valid(pin) || !edacraft::core::valid(core_pin)) continue;
        impl_->pin_bindings[pin.id] = core_pin;
        impl_->reverse_pin_bindings[core_pin.id] = pin;
    }

    return result;
}

GateViewAttachResult TimingEngine::attach_design_db(
    edacraft::core::DesignDB& design,
    const std::unordered_map<std::string, std::vector<std::string>>& port_aliases) {
    auto* view = design.gate_netlist();
    if (!view) return {};

    auto result = attach_gate_view(*view, port_aliases, &design.strings());
    design.clear_runtime_pin_bindings("ftimer");
    for (const auto& [runtime_pin_id, core_pin] : result.pin_to_core_pin) {
        design.bind_runtime_pin("ftimer", runtime_pin_id, core_pin);
    }
    design.clear_runtime_pin_aliases("ftimer");
    for (const auto& [alias, pins] : result.port_aliases) {
        std::vector<uint32_t> runtime_pin_ids;
        runtime_pin_ids.reserve(pins.size());
        for (auto pin : pins) {
            if (valid(pin)) runtime_pin_ids.push_back(pin.id);
        }
        design.bind_runtime_pin_alias("ftimer", alias, runtime_pin_ids);
    }
    if (design.liberty().library_count() > 0) {
        impl_->use_external_liberty(design.liberty());
    }
    return result;
}

bool TimingEngine::replace_instance_cell(std::string_view instance_name,
                                         std::string_view cell_name,
                                         const std::vector<std::string>& input_pins,
                                         std::string_view output_pin) {
    std::vector<std::string> output_pins;
    if (!output_pin.empty()) {
        output_pins.emplace_back(output_pin);
    }
    return replace_instance_cell(instance_name, cell_name, input_pins, output_pins);
}

bool TimingEngine::replace_instance_cell(std::string_view instance_name,
                                         std::string_view cell_name,
                                         const std::vector<std::string>& input_pins,
                                         const std::vector<std::string>& output_pins) {
    if (!impl_->network) return false;

    auto inst = impl_->network->find_instance(instance_name);
    if (!inst) return false;

    CellId new_cell = impl_->network->create_cell(cell_name);
    for (const auto& pin_name : input_pins) {
        impl_->network->add_port(new_cell, pin_name);
    }
    for (const auto& pin_name : output_pins) {
        if (!pin_name.empty()) {
            impl_->network->add_port(new_cell, pin_name);
        }
    }

    impl_->network->set_instance_cell(*inst, new_cell);
    impl_->network->rebuild_net_connections();
    return true;
}

std::optional<edacraft::core::PinHandle> TimingEngine::core_pin_for_pin(PinId pin) const {
    if (!valid(pin)) return std::nullopt;
    auto it = impl_->pin_bindings.find(pin.id);
    if (it == impl_->pin_bindings.end()) {
        return edacraft::core::PinHandle{pin.id};
    }
    return it->second;
}

std::optional<PinId> TimingEngine::pin_for_core_pin(edacraft::core::PinHandle core_pin) const {
    if (!edacraft::core::valid(core_pin)) return std::nullopt;
    auto it = impl_->reverse_pin_bindings.find(core_pin.id);
    if (it == impl_->reverse_pin_bindings.end()) {
        return PinId{core_pin.id};
    }
    return it->second;
}

void TimingEngine::update_timing_incremental(
    const std::vector<NetId>& changed_nets,
    const std::vector<PinId>& changed_pins
) {
    for (auto net : changed_nets) {
        mark_net_dirty(net);
    }
    for (auto pin : changed_pins) {
        mark_pin_dirty(pin);
    }
    update_incremental();
}

TimingView TimingEngine::get_timing_view() const {
    if (!impl_->graph) return {};
    TimingView view;
    view.vertex_count = impl_->graph->vertex_count();
    view.arrival = impl_->graph->arrival_data();
    view.slew = impl_->graph->slew_data();
    view.required = impl_->graph->required_data();
    view.pred_max = impl_->graph->pred_max_data();
    view.pred_min = impl_->graph->pred_min_data();
    return view;
}

template <typename ImplT>
void update_timing_db_snapshot(const ImplT& impl,
                               edacraft::core::TimingDB& timing_db,
                               const TimingEngine& engine) {
    timing_db.clear();
    if (!impl.graph || !impl.network || !impl.liberty) return;
    const auto* bindings = &impl.pin_bindings;

    for (uint32_t pid = 0; pid < impl.network->pin_count(); ++pid) {
        PinId pin{pid};
        if (pid > UINT32_MAX / 2) continue;
        for (int mm_i = 0; mm_i < 2; ++mm_i) {
            MinMax mm = static_cast<MinMax>(mm_i);
            auto core_mm = to_core_min_max(mm);
            for (int rf_i = 0; rf_i < 2; ++rf_i) {
                Transition rf = static_cast<Transition>(rf_i);
                uint32_t vid = pid * 2 + static_cast<uint32_t>(rf);
                if (vid >= impl.graph->vertex_count()) continue;

            float arrival = impl.graph->arrival(vid, mm, rf).value;
            float required = impl.graph->required(vid, mm, rf).value;
            float slew = impl.graph->slew(vid, mm, rf).value;
            if (const auto* label = impl.graph->worst_launch_label(vid, mm)) {
                arrival = label->arrival;
                required = label->required;
            }

            edacraft::core::TimingPoint point;
            point.key.pin = to_core_pin(pin, bindings);
            point.key.transition = to_core_transition(rf);
            point.key.analysis = core_mm;
            point.arrival_ns = arrival;
            point.required_ns = required;
            point.slew_ns = slew;
            point.slack_ns = slack_from_values(arrival, required, mm);
            point.has_arrival = std::isfinite(arrival);
            point.has_required = std::isfinite(required);
            point.has_slew = std::isfinite(slew);
            point.has_slack = std::isfinite(point.slack_ns);
            timing_db.set_point(std::move(point));
        }
    }
    }

    std::unordered_set<ec::TimingArcKey, ec::TimingArcKeyHash> written_arcs;
    for (uint32_t eid = 0; eid < impl.graph->edge_count(); ++eid) {
        write_timing_arc(*impl.graph, *impl.network, *impl.liberty, eid,
                         timing_db, bindings, &written_arcs);
    }

    for (uint32_t pid = 0; pid < impl.network->pin_count(); ++pid) {
        write_constraint_arcs_for_pin(*impl.graph, *impl.network, *impl.liberty,
                                     PinId{pid}, timing_db, bindings);
    }

    export_resolved_exceptions(*impl.sdc, timing_db, bindings);

    auto write_paths = [&](MinMax mm) {
        auto reports = all_check_reports(engine, mm);
        auto core_mm = to_core_min_max(mm);
        for (const auto& report : reports) {
            edacraft::core::TimingPath path;
            path.analysis = core_mm;
            path.slack_ns = report.slack;
            if (report.check_kind == TimingCheckKind::Recovery) path.path_group = "recovery";
            else if (report.check_kind == TimingCheckKind::Removal) path.path_group = "removal";
            else if (!report.path_group.empty()) path.path_group = report.path_group;

            for (size_t i = 0; i < report.point_names.size(); ++i) {
                edacraft::core::TimingPathPoint point;
                point.pin_name = report.point_names[i];
                if (auto pin = resolve_report_pin(*impl.network, report.point_names[i])) {
                    point.pin = to_core_pin(*pin, bindings);
                    if (i == 0) path.startpoint = point.pin;
                    if (i + 1 == report.point_names.size()) path.endpoint = point.pin;
                }
                if (i < report.transitions.size()) {
                    point.transition = to_core_transition(transition_from_name(report.transitions[i]));
                }
                if (i < report.arrivals.size()) point.arrival_ns = report.arrivals[i];
                if (i < report.slews.size()) point.slew_ns = report.slews[i];
                if (i < report.delays.size()) point.arc_delay_ns = report.delays[i];
                point.slack_ns = report.slack;
                path.points.push_back(std::move(point));
            }
            if (!report.transitions.empty()) {
                path.endpoint_transition = to_core_transition(
                    transition_from_name(report.transitions.back()));
            }
            timing_db.add_path(std::move(path));
        }
    };

    write_paths(MinMax::Max);
    write_paths(MinMax::Min);
}

template <typename ImplT>
void update_timing_db_points_snapshot(const ImplT& impl,
                                      edacraft::core::TimingDB& timing_db) {
    timing_db.clear();
    if (!impl.graph || !impl.network) return;
    const auto* bindings = &impl.pin_bindings;

    for (uint32_t pid = 0; pid < impl.network->pin_count(); ++pid) {
        PinId pin{pid};
        if (pid > UINT32_MAX / 2) continue;
        for (int mm_i = 0; mm_i < 2; ++mm_i) {
            MinMax mm = static_cast<MinMax>(mm_i);
            auto core_mm = to_core_min_max(mm);
            for (int rf_i = 0; rf_i < 2; ++rf_i) {
                Transition rf = static_cast<Transition>(rf_i);
                uint32_t vid = pid * 2 + static_cast<uint32_t>(rf);
                if (vid >= impl.graph->vertex_count()) continue;

                float arrival = impl.graph->arrival(vid, mm, rf).value;
                float required = impl.graph->required(vid, mm, rf).value;
                float slew = impl.graph->slew(vid, mm, rf).value;
                if (const auto* label = impl.graph->worst_launch_label(vid, mm)) {
                    arrival = label->arrival;
                    required = label->required;
                }

                edacraft::core::TimingPoint point;
                point.key.pin = to_core_pin(pin, bindings);
                point.key.transition = to_core_transition(rf);
                point.key.analysis = core_mm;
                point.arrival_ns = arrival;
                point.required_ns = required;
                point.slew_ns = slew;
                point.slack_ns = slack_from_values(arrival, required, mm);
                point.has_arrival = std::isfinite(arrival);
                point.has_required = std::isfinite(required);
                point.has_slew = std::isfinite(slew);
                point.has_slack = std::isfinite(point.slack_ns);
                timing_db.set_point(std::move(point));
            }
        }
    }
}

template <typename ImplT>
void update_timing_db_incremental_snapshot(const ImplT& impl,
                                           edacraft::core::TimingDB& timing_db,
                                           const TimingEngine& engine) {
    // A full timing update clears the incremental dirty list too. An empty
    // list therefore cannot prove that an existing consumer snapshot is up
    // to date (for example after replacing SPEF and calling update_timing).
    // Rebuild in this ambiguous case, including points and arcs. This also
    // safely handles a no-op incremental update following a full update.
    if (timing_db.empty() || impl.last_dirty_vertices.empty()) {
        update_timing_db_snapshot(impl, timing_db, engine);
        return;
    }
    if (!impl.graph || !impl.network || !impl.liberty) return;
    const auto* bindings = &impl.pin_bindings;

    const auto& graph = *impl.graph;
    const auto& network = *impl.network;
    const auto& liberty = *impl.liberty;
    std::vector<uint8_t> affected(graph.vertex_count(), 0);
    std::vector<uint32_t> queue;

    auto enqueue = [&](uint32_t vid) {
        if (vid >= graph.vertex_count() || affected[vid]) return;
        affected[vid] = 1;
        queue.push_back(vid);
    };

    for (uint32_t vid : impl.last_dirty_vertices) {
        enqueue(vid);
    }

    for (size_t head = 0; head < queue.size(); ++head) {
        uint32_t vid = queue[head];
        for (uint32_t eid : graph.forward_edges(vid)) {
            enqueue(graph.edge_to(eid));
        }
    }

    for (size_t head = 0; head < queue.size(); ++head) {
        uint32_t vid = queue[head];
        for (uint32_t eid : graph.reverse_edges(vid)) {
            enqueue(graph.edge_from(eid));
        }
    }

    std::unordered_set<uint32_t> affected_pins;
    std::unordered_set<uint32_t> affected_edges;
    for (uint32_t vid : queue) {
        PinId pin = graph.vertex_pin(vid);
        if (valid(pin)) affected_pins.insert(pin.id);
        for (uint32_t eid : graph.forward_edges(vid)) affected_edges.insert(eid);
        for (uint32_t eid : graph.reverse_edges(vid)) affected_edges.insert(eid);
    }

    std::unordered_set<uint32_t> affected_constraint_targets = affected_pins;
    for (uint32_t pin_id : affected_pins) {
        PinId pin{pin_id};
        if (pin_id >= network.pin_count()) continue;
        const auto& pin_data = network.pin(pin);
        if (!valid(pin_data.instance)) continue;
        const auto& inst = network.instance(pin_data.instance);
        const auto& cell = network.cell(inst.cell);
        if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) continue;
        const auto& lib_cell = liberty.cell(liberty::to_core(cell.liberty_library),
                                            liberty::to_core(cell.liberty_cell));
        for (const auto& lib_arc : lib_cell.arcs) {
            if (!ec::liberty_timing_type_is_check(lib_arc.type)) {
                continue;
            }
            if (lib_arc.from_pin != pin_data.name) continue;
            for (PinId inst_pin : inst.pins) {
                if (network.pin(inst_pin).name == lib_arc.to_pin) {
                    affected_constraint_targets.insert(inst_pin.id);
                    break;
                }
            }
        }
    }

    // Required times are recomputed globally, including endpoints depending
    // on a changed related clock without a forward data edge.
    for (uint32_t pin_id = 0; pin_id < network.pin_count(); ++pin_id) {
        PinId pin{pin_id};
        write_timing_point(graph, pin, timing_db, bindings);
    }
    for (uint32_t pin_id : affected_constraint_targets) {
        write_constraint_arcs_for_pin(graph, network, liberty, PinId{pin_id}, timing_db, bindings);
    }

    // All parallel conditional edges touch the affected vertices. Rebuild
    // their shared keys together, in the same order as a complete export.
    std::vector<uint32_t> ordered_edges(affected_edges.begin(), affected_edges.end());
    std::sort(ordered_edges.begin(), ordered_edges.end());
    std::unordered_set<ec::TimingArcKey, ec::TimingArcKeyHash> written_arcs;
    for (uint32_t eid : ordered_edges) {
        if (eid < graph.edge_count()) {
            write_timing_arc(graph, network, liberty, eid, timing_db, bindings, &written_arcs);
        }
    }

    write_timing_paths(engine, network, timing_db, bindings);
}

void TimingEngine::update_design_db(edacraft::core::DesignDB& design) const {
    update_timing_db_snapshot(*impl_, design.timing(), *this);
}

void TimingEngine::update_design_db_points(edacraft::core::DesignDB& design) const {
    update_timing_db_points_snapshot(*impl_, design.timing());
}

void TimingEngine::update_design_db_incremental(edacraft::core::DesignDB& design) const {
    update_timing_db_incremental_snapshot(*impl_, design.timing(), *this);
}

} // namespace te
