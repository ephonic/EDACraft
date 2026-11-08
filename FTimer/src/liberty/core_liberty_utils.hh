#pragma once

#include <algorithm>
#include <cmath>
#include <limits>

#include "edacraft/core/liberty_db.hpp"
#include "edacraft/core/timing_db.hpp"
#include "time_engine/types.hh"
#include "network/network.hh"

namespace te::liberty {

namespace ec = edacraft::core;

// Timing graph, SDC and TimingDB use ns. Characterization tables retain
// each library's native units, including when several libraries are linked.
inline float time_unit_ns(const ec::LibertyLibrary& library) {
    return library.units.time_unit_seconds / 1e-9f;
}

inline float pin_time_unit_ns(const Network& network, const ec::LibertyDB& db, PinId pin) {
    const auto& pd = network.pin(pin);
    if (valid(pd.instance)) {
        const auto& cell = network.cell(network.instance(pd.instance).cell);
        if (valid(cell.liberty_library)) return time_unit_ns(db.library(cell.liberty_library.id));
    }
    return 1.f;
}

inline float constraint_ns(const ec::NldmTable& table, float clock_slew_ns,
                           float data_slew_ns, float unit_ns) {
    return table.lookup(clock_slew_ns / unit_ns, data_slew_ns / unit_ns) * unit_ns;
}

inline float pin_cap_unit(const Network& network, const ec::LibertyDB& db, PinId pin) {
    const auto& pd = network.pin(pin);
    if (valid(pd.instance)) {
        const auto& cell = network.cell(network.instance(pd.instance).cell);
        if (valid(cell.liberty_library))
            return db.library(cell.liberty_library.id).units.capacitance_unit_farads;
    }
    return 1e-12f;
}

// SPEF PIN_CAP INCLUDED embeds the static Liberty input pin capacitance.
// Dynamic receiver envelopes and SDC overrides are separate from that value.
inline float extracted_pin_cap(const Network& network, const ec::LibertyDB& db, PinId pin) {
    const auto& pd = network.pin(pin);
    if (!valid(pd.instance)) return 0.f;
    const auto& cell = network.cell(network.instance(pd.instance).cell);
    if (!valid(cell.liberty_library) || !valid(cell.liberty_cell)) return 0.f;
    const auto& pins = db.library(cell.liberty_library.id).cells[cell.liberty_cell.id].pins;
    return valid(pd.liberty_pin) && pd.liberty_pin.id < pins.size() ? pins[pd.liberty_pin.id].capacitance : 0.f;
}

// For lumped loads, collapse each CCS receiver region over its characterized
// slew/load grid. PrimeTime's pre-layout pin capacitance is the mean of the
// two regions, with an early/late envelope across conditional timing arcs.
inline float receiver_region_mean(const ec::NldmTable& table) {
    if (table.values.empty()) return 0.0f;
    double sum = 0.0;
    for (float v : table.values) sum += v;
    return static_cast<float>(sum / table.values.size());
}

inline float static_pin_capacitance(const ec::LibertyPinData& pin,
                                    Transition rf, MinMax mm = MinMax::Max) {
    const bool rise = rf == Transition::Rise;
    const float bound = mm == MinMax::Max
        ? (rise ? pin.rise_capacitance_upper : pin.fall_capacitance_upper)
        : (rise ? pin.rise_capacitance_lower : pin.fall_capacitance_lower);
    if (bound >= 0.f) return bound;
    const float edge = rise ? pin.rise_capacitance : pin.fall_capacitance;
    return edge >= 0.f ? edge : pin.capacitance;
}

inline float lumped_receiver_capacitance(const ec::LibertyCellData& cell,
                                         const ec::LibertyPinData& pin,
                                         Transition rf, MinMax mm = MinMax::Max) {
    float cap = mm == MinMax::Max ? 0.0f : std::numeric_limits<float>::infinity();
    auto consider = [&](const auto& receiver) {
        const auto& c1 = rf == Transition::Rise ? receiver.receiver_capacitance1_rise
                                               : receiver.receiver_capacitance1_fall;
        const auto& c2 = rf == Transition::Rise ? receiver.receiver_capacitance2_rise
                                               : receiver.receiver_capacitance2_fall;
        const unsigned regions = unsigned(!c1.values.empty()) + unsigned(!c2.values.empty());
        if (regions) {
            const float mean1 = receiver_region_mean(c1);
            const float mean2 = receiver_region_mean(c2);
            float selected = (mean1 + mean2) / regions;
            cap = mm == MinMax::Max ? std::max(cap, selected) : std::min(cap, selected);
        }
    };
    consider(pin);
    for (const auto& receiver : pin.receiver_capacitance) consider(receiver);
    for (const auto& arc : cell.arcs)
        if (arc.from_pin == pin.name) consider(arc);
    return std::isfinite(cap) ? cap : 0.0f;
}

// PT legacy bounds receiver slew lookup coordinates, while the solved
// transition retains its physical value. Keep this policy local to CCS
// receivers; generic NLDM and constraint tables have independent semantics.
inline float receiver_table_value(const ec::NldmTable& table, float slew, float load) {
    if (table.axis1.size()>1)
        slew=std::clamp(slew,.2f*table.axis1.front(),1.1f*table.axis1.back());
    // An unloaded receiver output selects the first characterized load.
    // A positive load is bounded to 20% of the first index through 110% of
    // the last (native controlled-load boundary campaign507/510/513).
    if (load==0.f && !table.axis2.empty()) load=table.axis2.front();
    // Receiver-capacitance tables have the same 10% upper extrapolation
    // limit as their slew coordinate. This is independent of the much wider
    // effective-capacitance bounds used by the CCS current-source solver.
    if (table.axis2.size()>1)
        load=std::clamp(load,.2f*table.axis2.front(),1.1f*table.axis2.back());
    return table.lookup(slew,load);
}

// Evaluate the characterized CCS receiver regions at the transition/load of
// the net being solved. This dynamic counterpart is used only for distributed
// SPEF waveforms; lumped paths retain the static receiver envelope above.
inline float receiver_capacitance_at(const ec::LibertyCellData& cell,
                                     const ec::LibertyPinData& pin,
                                     Transition rf, float input_slew,
                                     float load_cap) {
    if (!(input_slew > 0.0f) || !(load_cap > 0.0f)) return 0.0f;
    float cap = 0.0f;
    auto consider = [&](const auto& receiver) {
        const auto& c1 = rf == Transition::Rise ? receiver.receiver_capacitance1_rise
                                               : receiver.receiver_capacitance1_fall;
        const auto& c2 = rf == Transition::Rise ? receiver.receiver_capacitance2_rise
                                               : receiver.receiver_capacitance2_fall;
        const unsigned regions = unsigned(!c1.values.empty()) + unsigned(!c2.values.empty());
        if (!regions) return;
        float selected = 0.0f;
        if (!c1.values.empty()) selected += receiver_table_value(c1, input_slew, load_cap);
        if (!c2.values.empty()) selected += receiver_table_value(c2, input_slew, load_cap);
        cap = std::max(cap, selected / regions);
    };
    consider(pin);
    for (const auto& receiver : pin.receiver_capacitance) consider(receiver);
    for (const auto& arc : cell.arcs)
        if (arc.from_pin == pin.name) consider(arc);
    return cap;
}

struct ReceiverCapacitance { float first = 0.0f, second = 0.0f; };

// Initial receiver-table coordinate in the compressed CCS runtime. The early
// estimator contracts the nominal transition; it does not use the late
// full-swing estimate. The 0.133 coefficient is the native runtime's default
// early-estimate weight, independent of cell, slew, load and time units.
inline float receiver_initial_slew(float nldm_slew, float lower, float upper, bool late) {
    const float width = upper - lower;
    if (!(width > 0.f)) return nldm_slew;
    if (late) return nldm_slew / width;
    const float full_swing_scale = 1.f / width;
    return static_cast<float>(nldm_slew * (1. - (full_swing_scale - 1.) * .133));
}

// Nominal regional loads used to choose the initial CCS receiver solve.
// Keep C1/C2 and transition polarity separate: their maximum is not the
// RF-averaged capacitance used by the distributed network's MOR basis.
template <typename Enabled>
inline ReceiverCapacitance nominal_receiver_regions(const ec::LibertyCellData& cell,
                                                     const ec::LibertyPinData& pin,
                                                     Transition rf, Enabled enabled, bool late = true) {
    ReceiverCapacitance cap;
    auto consider = [&](const auto& receiver) {
        const auto& c1 = rf == Transition::Rise ? receiver.receiver_capacitance1_rise
                                               : receiver.receiver_capacitance1_fall;
        const auto& c2 = rf == Transition::Rise ? receiver.receiver_capacitance2_rise
                                               : receiver.receiver_capacitance2_fall;
        const float first = receiver_region_mean(c1), second = receiver_region_mean(c2);
        if (first > 0.f && std::isfinite(first))
            cap.first = cap.first == 0.f ? first : late ? std::max(cap.first, first) : std::min(cap.first, first);
        if (second > 0.f && std::isfinite(second))
            cap.second = cap.second == 0.f ? second : late ? std::max(cap.second, second) : std::min(cap.second, second);
    };
    if (pin.receiver_capacitance.empty()) consider(pin);
    for (const auto& receiver : pin.receiver_capacitance)
        if (enabled(receiver.when)) consider(receiver);
    for (const auto& arc : cell.arcs)
        if (arc.from_pin == pin.name && enabled(arc.when)) consider(arc);
    return cap;
}

// Arc-level receiver tables use the load of that arc's output, not the load
// being driven at its input. Keep the two voltage regions distinct.
template <typename OutputLoad, typename Enabled>
inline ReceiverCapacitance receiver_regions_at(const ec::LibertyCellData& cell,
                                               const ec::LibertyPinData& pin,
                                               Transition rf, float slew1, float slew2,
                                               OutputLoad output_load, Enabled enabled, bool late = true) {
    ReceiverCapacitance cap;
    struct Envelope {
        const ec::NldmTable* table;
        float load;
        ec::NldmTable merged;
    };
    std::vector<Envelope> first_tables, second_tables;
    auto collect = [late](auto& tables, const ec::NldmTable& table, float load) {
        if (table.values.empty()) return;
        for (auto& group : tables) {
            const auto& base = *group.table;
            if (base.rows != table.rows || base.axis1 != table.axis1 ||
                base.axis1.size() != base.rows || table.axis1.size() != table.rows) continue;
            if (group.merged.values.empty()) {
                group.merged.rows = base.rows;group.merged.cols = 1;
                group.merged.axis1 = base.axis1;group.merged.axis2 = {0.f};
                for (float slew : base.axis1)
                    group.merged.values.push_back(receiver_table_value(base, slew, group.load));
            }
            for (size_t j = 0; j < table.rows; ++j) {
                const float candidate = receiver_table_value(table, table.axis1[j], load);
                group.merged.values[j] = late ? std::max(group.merged.values[j], candidate)
                                              : std::min(group.merged.values[j], candidate);
            }
            return;
        }
        tables.push_back({&table, load, {}});
    };
    auto consider = [&](const auto& receiver, float load) {
        const auto& c1 = rf == Transition::Rise ? receiver.receiver_capacitance1_rise
                                               : receiver.receiver_capacitance1_fall;
        const auto& c2 = rf == Transition::Rise ? receiver.receiver_capacitance2_rise
                                               : receiver.receiver_capacitance2_fall;
        collect(first_tables, c1, load);
        collect(second_tables, c2, load);
    };
    // Flat tables are the compatibility copy of the last nested group.
    // Including that copy would reintroduce a statically disabled group.
    if (pin.receiver_capacitance.empty()) consider(pin, 0.0f);
    for (const auto& receiver : pin.receiver_capacitance)
        if (enabled(receiver.when)) consider(receiver, 0.0f);
    for (const auto& arc : cell.arcs)
        if (arc.from_pin == pin.name && enabled(arc.when)) consider(arc, output_load(arc));
    // Evaluate each enabled table at its output load first. Envelope the
    // resulting curves on their common slew grid, then interpolate/extrapolate
    // the regional input slew. Select the maximum for late analysis and the
    // minimum for early analysis. Selection after slew extrapolation, or before
    // output-load evaluation, changes the result when weights are negative.
    auto evaluate = [&](const auto& tables, float slew) {
        float value = 0.f;
        for (const auto& group : tables) {
            const auto& table = group.merged.values.empty() ? *group.table : group.merged;
            const float candidate = receiver_table_value(table, slew,
                group.merged.values.empty() ? group.load : 0.f);
            if (candidate > 0.f && std::isfinite(candidate))
                value = value == 0.f ? candidate : late ? std::max(value, candidate) : std::min(value, candidate);
        }
        return value;
    };
    cap.first = evaluate(first_tables, slew1);
    cap.second = evaluate(second_tables, slew2);
    if (!(cap.first > 0.0f)) cap.first = cap.second;
    if (!(cap.second > 0.0f)) cap.second = cap.first;
    return cap;
}

template <typename OutputLoad>
inline ReceiverCapacitance receiver_regions_at(const ec::LibertyCellData& cell,
                                               const ec::LibertyPinData& pin,
                                               Transition rf, float slew1, float slew2,
                                               OutputLoad output_load) {
    return receiver_regions_at(cell, pin, rf, slew1, slew2, output_load,
                               [](uint32_t) { return true; });
}

inline ec::LibraryHandle to_core(LibraryId id) {
    return ec::LibraryHandle{id.id};
}

inline ec::LibertyCellHandle to_core(LibertyCellId id) {
    return ec::LibertyCellHandle{id.id};
}

inline LibertyCellId to_te(ec::LibertyCellHandle id) {
    return LibertyCellId{id.id};
}

inline PortDirection to_network_direction(ec::PortDirection dir) {
    switch (dir) {
        case ec::PortDirection::Input:
            return PortDirection::Input;
        case ec::PortDirection::Output:
            return PortDirection::Output;
        case ec::PortDirection::Inout:
            return PortDirection::Inout;
        case ec::PortDirection::Internal:
            return PortDirection::Internal;
    }
    return PortDirection::Internal;
}

inline bool is_edge_trigger(ec::LibertyTimingType type) {
    return type == ec::LibertyTimingType::RisingEdge ||
           type == ec::LibertyTimingType::FallingEdge;
}

inline bool is_setup(ec::LibertyTimingType type) {
    return type == ec::LibertyTimingType::SetupRising ||
           type == ec::LibertyTimingType::SetupFalling;
}

inline bool is_hold(ec::LibertyTimingType type) {
    return type == ec::LibertyTimingType::HoldRising ||
           type == ec::LibertyTimingType::HoldFalling;
}

inline bool is_setup_or_hold(ec::LibertyTimingType type) {
    return is_setup(type) || is_hold(type);
}

inline bool is_data_arc(ec::LibertyTimingType type) {
    return type == ec::LibertyTimingType::Combinational ||
           type == ec::LibertyTimingType::Clear ||
           type == ec::LibertyTimingType::Preset;
}

inline ec::TimingArcType to_timing_db_arc_type(ec::LibertyTimingType type) {
    using CoreType = ec::TimingArcType;
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
    }
    return CoreType::Unknown;
}

inline ec::TimingSense to_timing_db_sense(ec::LibertyTimingSense sense) {
    using CoreSense = ec::TimingSense;
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

} // namespace te::liberty
