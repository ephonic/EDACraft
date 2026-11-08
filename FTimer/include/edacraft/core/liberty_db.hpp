#ifndef EDACRAFT_CORE_LIBERTY_DB_HPP
#define EDACRAFT_CORE_LIBERTY_DB_HPP

#include "edacraft/core/ids.hpp"
#include "edacraft/core/object_table.hpp"
#include "edacraft/core/string_pool.hpp"

#include <algorithm>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace edacraft::core {

struct LibertyCellHandle { uint32_t id; };
struct LibertyPinHandle { uint32_t id; };
struct LibertyArcHandle { uint32_t id; };

constexpr LibertyCellHandle NULL_LIBERTY_CELL{UINT32_MAX};
constexpr LibertyPinHandle NULL_LIBERTY_PIN{UINT32_MAX};
constexpr LibertyArcHandle NULL_LIBERTY_ARC{UINT32_MAX};

inline bool valid(LibertyCellHandle h) { return h.id != UINT32_MAX; }
inline bool valid(LibertyPinHandle h) { return h.id != UINT32_MAX; }
inline bool valid(LibertyArcHandle h) { return h.id != UINT32_MAX; }

inline bool operator==(LibertyCellHandle a, LibertyCellHandle b) { return a.id == b.id; }
inline bool operator!=(LibertyCellHandle a, LibertyCellHandle b) { return a.id != b.id; }
inline bool operator==(LibertyPinHandle a, LibertyPinHandle b) { return a.id == b.id; }
inline bool operator!=(LibertyPinHandle a, LibertyPinHandle b) { return a.id != b.id; }
inline bool operator==(LibertyArcHandle a, LibertyArcHandle b) { return a.id == b.id; }
inline bool operator!=(LibertyArcHandle a, LibertyArcHandle b) { return a.id != b.id; }

struct PvtPoint {
    float process = 1.0f;
    float voltage = 0.0f;
    float temperature = 25.0f;
};

enum class LibertyTimingSense : uint8_t {
    PositiveUnate,
    NegativeUnate,
    NonUnate,
    None,
};

enum class LibertyTimingType : uint8_t {
    Combinational,
    RisingEdge,
    FallingEdge,
    LevelSensitive,
    Preset,
    Clear,
    SetupRising,
    HoldRising,
    SetupFalling,
    HoldFalling,
    RecoveryRising,
    RecoveryFalling,
    RemovalRising,
    RemovalFalling,
    Unknown,
};

inline bool liberty_timing_type_is_check(LibertyTimingType type) {
    return type == LibertyTimingType::SetupRising || type == LibertyTimingType::SetupFalling ||
           type == LibertyTimingType::HoldRising || type == LibertyTimingType::HoldFalling ||
           type == LibertyTimingType::RecoveryRising || type == LibertyTimingType::RecoveryFalling ||
           type == LibertyTimingType::RemovalRising || type == LibertyTimingType::RemovalFalling;
}

inline bool liberty_timing_type_is_async_check(LibertyTimingType type) {
    return type == LibertyTimingType::RecoveryRising || type == LibertyTimingType::RecoveryFalling ||
           type == LibertyTimingType::RemovalRising || type == LibertyTimingType::RemovalFalling;
}

inline bool liberty_timing_type_is_min_check(LibertyTimingType type) {
    return type == LibertyTimingType::HoldRising || type == LibertyTimingType::HoldFalling ||
           type == LibertyTimingType::RemovalRising || type == LibertyTimingType::RemovalFalling;
}

inline bool liberty_timing_type_is_falling_check(LibertyTimingType type) {
    return type == LibertyTimingType::SetupFalling || type == LibertyTimingType::HoldFalling ||
           type == LibertyTimingType::RecoveryFalling || type == LibertyTimingType::RemovalFalling;
}

struct NldmTable {
    std::vector<float> axis1;
    std::vector<float> axis2;
    std::vector<float> values;
    size_t rows = 0;
    size_t cols = 0;

    float lookup(float v1, float v2) const {
        if (rows == 0 || cols == 0) return 0.0f;

        size_t r0 = 0, r1 = 0, c0 = 0, c1 = 0;
        float fr = 0.0f, fc = 0.0f;
        find_axis(axis1, v1, r0, r1, fr);
        find_axis(axis2, v2, c0, c1, fc);

        float v00 = values[r0 * cols + c0];
        float v01 = values[r0 * cols + c1];
        float v10 = values[r1 * cols + c0];
        float v11 = values[r1 * cols + c1];
        float top = v00 * (1.0f - fc) + v01 * fc;
        float bot = v10 * (1.0f - fc) + v11 * fc;
        return top * (1.0f - fr) + bot * fr;
    }

private:
    static void find_axis(const std::vector<float>& axis, float value,
                          size_t& i0, size_t& i1, float& frac) {
        if (axis.empty() || axis.size() < 2) {
            i0 = i1 = 0;
            frac = 0.0f;
            return;
        }
        if (value <= axis.front()) {
            i0 = 0;
            i1 = 1;
            float a0 = axis[i0];
            float a1 = axis[i1];
            frac = (a1 == a0) ? 0.0f : (value - a0) / (a1 - a0);
            return;
        }
        if (value >= axis.back()) {
            i0 = axis.size() - 2;
            i1 = axis.size() - 1;
            float a0 = axis[i0];
            float a1 = axis[i1];
            frac = (a1 == a0) ? 0.0f : (value - a0) / (a1 - a0);
            return;
        }
        auto it = std::lower_bound(axis.begin(), axis.end(), value);
        i1 = static_cast<size_t>(it - axis.begin());
        i0 = i1 - 1;
        float a0 = axis[i0];
        float a1 = axis[i1];
        frac = (a1 == a0) ? 0.0f : (value - a0) / (a1 - a0);
    }
};

struct CsmWaveform {
    std::vector<float> time_points;
    std::vector<float> current;
    float reference_time = 0.0f;
};

struct CsmOutputCurrentTable {
    uint32_t nslew = 0;
    uint32_t ncap = 0;
    std::vector<float> input_slews;
    std::vector<float> load_caps;
    std::vector<CsmWaveform> waveforms;
    std::vector<float> corner_delays;
    std::vector<float> corner_slews;

    bool empty() const { return waveforms.empty(); }
};

// Structured CCS noise characterization in source-library units. Keep token
// spelling and quote information, all axes (including ragged time vectors),
// stage attributes and ordering. This is retained model data, not a claim that
// the timing/SI solver implements dynamic CCSN semantics.
struct LibertyCcsnNode {
    enum class Kind : uint8_t { Attribute, Call, Group };
    struct Atom {
        std::string text;
        bool quoted = false;
    };
    std::string name;
    Kind kind = Kind::Group;
    std::vector<Atom> arguments;
    std::vector<LibertyCcsnNode> children;
};

struct LibertyArcData {
    uint32_t from_pin = UINT32_MAX;
    uint32_t to_pin = UINT32_MAX;
    LibertyTimingSense sense = LibertyTimingSense::None;
    LibertyTimingType type = LibertyTimingType::Combinational;
    uint32_t when = UINT32_MAX;

    NldmTable rise_delay;
    NldmTable fall_delay;
    NldmTable rise_output_slew;
    NldmTable fall_output_slew;
    NldmTable rise_constraint;
    NldmTable fall_constraint;
    // Declared data/check-pin transitions, independent of the related-clock
    // edge in timing_type. Keep declarations even when a table is malformed.
    // Zero means unknown (legacy/programmatic model): require both edges.
    uint8_t constraint_transition_mask = 0; // rise=1, fall=2

    // Timing-arc-level CCS receiver model.  Unlike the pin-level fallback,
    // these tables are indexed by input transition and output load.
    NldmTable receiver_capacitance1_rise;
    NldmTable receiver_capacitance1_fall;
    NldmTable receiver_capacitance2_rise;
    NldmTable receiver_capacitance2_fall;

    // CCSN first-stage Miller terms belong to the input->output timing arc.
    // Keeping them per arc avoids losing distinct values when one input pin
    // drives multiple characterized outputs.
    float miller_cap_rise = 0.0f;
    float miller_cap_fall = 0.0f;

    CsmOutputCurrentTable csm_output_current_rise;
    CsmOutputCurrentTable csm_output_current_fall;

    uint32_t related_pin = UINT32_MAX;
    // Timing-owned stages inherit this arc's related_pin and when condition.
    std::vector<LibertyCcsnNode> ccsn_stages;
};

struct LibertyPinData {
    struct InternalPowerData {
        uint32_t related_pin = UINT32_MAX;
        uint32_t related_pg_pin = UINT32_MAX;
        uint32_t when = UINT32_MAX;
        NldmTable rise_power;
        NldmTable fall_power;
    };

    // CCS receiver capacitance can be characterized by multiple conditional
    // receiver_capacitance() groups.  Keep the groups intact for consumers
    // (notably power analysis); the flat tables below remain as a compatibility
    // view for timing code that has not yet selected a condition explicitly.
    struct ReceiverCapacitanceData {
        uint32_t when = UINT32_MAX;
        NldmTable receiver_capacitance1_rise;
        NldmTable receiver_capacitance1_fall;
        NldmTable receiver_capacitance2_rise;
        NldmTable receiver_capacitance2_fall;
    };

    uint32_t name = UINT32_MAX;
    float capacitance = 0.0f;
    // Negative means absent. Preserve explicit zero and min/max RF bounds.
    float rise_capacitance = -1.0f, fall_capacitance = -1.0f;
    float rise_capacitance_lower = -1.0f, rise_capacitance_upper = -1.0f;
    float fall_capacitance_lower = -1.0f, fall_capacitance_upper = -1.0f;
    // Negative means use the library default. Explicit zero is a real load.
    float fanout_load = -1.0f;
    bool is_clock = false;
    PortDirection direction = PortDirection::Input;
    std::vector<uint32_t> arc_ids;

    NldmTable receiver_capacitance1_rise;
    NldmTable receiver_capacitance1_fall;
    NldmTable receiver_capacitance2_rise;
    NldmTable receiver_capacitance2_fall;
    std::vector<ReceiverCapacitanceData> receiver_capacitance;

    float miller_cap_rise = 0.0f;
    float miller_cap_fall = 0.0f;
    // Only pin-owned stages; timing-owned stages remain on their arcs.
    std::vector<LibertyCcsnNode> ccsn_stages;

    uint32_t related_pg_pin = UINT32_MAX;
    uint32_t function = UINT32_MAX;
    uint32_t clear = UINT32_MAX;
    uint32_t preset = UINT32_MAX;
    uint32_t enable = UINT32_MAX;
    bool clock_gate_clock_pin = false;
    bool clock_gate_enable_pin = false;
    bool clock_gate_test_pin = false;
    bool clock_gate_out_pin = false;
    std::vector<InternalPowerData> internal_power;
    // Preserve per-pin limits; cell-wide aggregates cannot distinguish input
    // limits or outputs with different electrical requirements. Negative is
    // absent; an explicit zero is a real limit.
    float max_transition = -1.0f;
    float max_capacitance = -1.0f;
    float max_fanout = -1.0f;
};

struct LibertyCellData {
    struct LeakagePowerData {
        float value = 0.0f;
        uint32_t when = UINT32_MAX;
        uint32_t related_pg_pin = UINT32_MAX;
    };
    uint32_t name = UINT32_MAX;
    float area = 0.0f;
    uint32_t function = UINT32_MAX;
    uint32_t footprint = UINT32_MAX;
    float cell_leakage_power = 0.0f;
    bool dont_use = false;

    uint32_t ff_clocked_on = UINT32_MAX;
    uint32_t ff_next_state = UINT32_MAX;
    uint32_t ff_clear = UINT32_MAX;
    uint32_t ff_preset = UINT32_MAX;
    uint32_t ff_enable = UINT32_MAX;
    uint32_t ff_state = UINT32_MAX;
    uint32_t ff_state_neg = UINT32_MAX;
    uint32_t clock_gating_integrated_cell = UINT32_MAX;

    float max_capacitance = 0.0f;
    float max_transition = 0.0f;
    float max_fanout = 0.0f;

    std::vector<LibertyPinData> pins;
    std::vector<LibertyArcData> arcs;
    std::vector<PvtPoint> pvt_points;
    std::vector<LeakagePowerData> leakage_power;
};

class LibertyLibrary {
public:
    // Legacy binary schemas omitted conditional leakage and power-axis
    // semantics. Timing can consume them, but power requires regeneration.
    bool power_metadata_complete = true;
    // Pre-v15 caches discarded the complementary ff(...) state variable.
    bool sequential_metadata_complete = true;
    struct Units {
        float time = 1.0f;
        float capacitance = 1.0f;
        float resistance = 1.0f;
        float voltage = 1.0f;
        float current = 1.0f;
        float leakage_power = 1.0f;
        // Explicit SI scales used by power analysis.  The legacy fields above
        // retain their historical timing-engine meanings (notably `voltage`
        // is the nominal operating voltage in existing Liberty readers).
        float time_unit_seconds = 1.0e-9f;
        float capacitance_unit_farads = 1.0e-12f;
        float voltage_unit_volts = 1.0f;
        float leakage_power_unit_watts = 1.0e-9f;
        float slew_lower = 0.2f;
        float slew_upper = 0.8f;
        float input_threshold_rise = 0.5f;
        float input_threshold_fall = 0.5f;
        float output_threshold_rise = 0.5f;
        float output_threshold_fall = 0.5f;
        float slew_derate = 1.0f;
    };

    struct WireLoadModel {
        uint32_t name = UINT32_MAX;
        float resistance = 0.0f;
        float capacitance = 0.0f;
        float area = 0.0f;
        float slope = 0.0f;
        std::vector<std::pair<uint32_t, float>> fanout_lengths;

        float get_length(uint32_t fanout) const {
            if (fanout == 0) return 0.f;
            if (fanout_lengths.empty()) return slope * static_cast<float>(fanout);
            const auto& first = fanout_lengths.front();
            if (fanout <= first.first)
                return first.first ? first.second * float(fanout) / first.first : first.second;
            for (size_t i = 1; i < fanout_lengths.size(); ++i) {
                const auto& a = fanout_lengths[i-1];
                const auto& b = fanout_lengths[i];
                if (fanout <= b.first) return a.second + (b.second-a.second) *
                    float(fanout-a.first) / std::max(1u, b.first-a.first);
            }
            const auto& last = fanout_lengths.back();
            return last.second + slope * float(fanout-last.first);
        }
    };

    uint32_t name = UINT32_MAX;
    Units units;
    // Complete definitions referenced by CCSN stages, in source units.
    std::vector<LibertyCcsnNode> ccsn_templates;
    std::vector<WireLoadModel> wire_load_models;
    uint32_t default_wire_load = UINT32_MAX;
    uint32_t default_wire_load_selection = UINT32_MAX;
    float default_max_transition = 0.0f;
    float default_max_capacitance = 0.0f;
    float default_max_fanout = 0.0f;
    float default_fanout_load = 1.0f;
    bool electrical_metadata_complete = true;
    ObjectTable<LibertyCellData> cells;

    std::optional<uint32_t> find_cell(uint32_t name_id) const {
        for (uint32_t i = 0; i < cells.size(); ++i) {
            if (cells[i].name == name_id) return i;
        }
        return std::nullopt;
    }
};

class LibertyDB {
public:
    LibertyLibrary& create_library() {
        libs_.emplace_back();
        return libs_.back();
    }

    LibraryHandle add_library(uint32_t name_id = UINT32_MAX) {
        libs_.emplace_back();
        libs_.back().name = name_id;
        return LibraryHandle{static_cast<uint32_t>(libs_.size() - 1)};
    }

    LibertyCellHandle add_cell(uint32_t name_id) {
        auto& lib = libs_.back();
        return LibertyCellHandle{lib.cells.emplace(LibertyCellData{name_id})};
    }

    LibertyCellHandle add_cell(LibraryHandle lib, uint32_t name_id) {
        return LibertyCellHandle{library(lib.id).cells.emplace(LibertyCellData{name_id})};
    }

    LibertyLibrary& library(uint32_t id) { return libs_[id]; }
    const LibertyLibrary& library(uint32_t id) const { return libs_[id]; }
    LibertyLibrary& library(LibraryHandle id) { return libs_[id.id]; }
    const LibertyLibrary& library(LibraryHandle id) const { return libs_[id.id]; }

    LibertyCellData& cell(LibraryHandle lib, LibertyCellHandle id) {
        return libs_[lib.id].cells[id.id];
    }

    const LibertyCellData& cell(LibraryHandle lib, LibertyCellHandle id) const {
        return libs_[lib.id].cells[id.id];
    }

    LibertyArcData& arc(LibraryHandle lib, LibertyCellHandle cell_id, uint32_t arc_index) {
        return libs_[lib.id].cells[cell_id.id].arcs[arc_index];
    }

    const LibertyArcData& arc(LibraryHandle lib, LibertyCellHandle cell_id,
                              uint32_t arc_index) const {
        return libs_[lib.id].cells[cell_id.id].arcs[arc_index];
    }

    const LibertyPinData* get_pin(LibraryHandle lib, LibertyCellHandle cell_id,
                                  uint32_t pin_name_id) const {
        const auto& cell_data = cell(lib, cell_id);
        for (const auto& pin : cell_data.pins) {
            if (pin.name == pin_name_id) return &pin;
        }
        return nullptr;
    }

    const LibertyArcData* get_arc(LibraryHandle lib, LibertyCellHandle cell_id,
                                  uint32_t arc_index) const {
        const auto& cell_data = cell(lib, cell_id);
        if (arc_index >= cell_data.arcs.size()) return nullptr;
        return &cell_data.arcs[arc_index];
    }

    size_t library_count() const { return libs_.size(); }

    void clear() { libs_.clear(); }

    std::pair<int, LibertyCellHandle> find_cell_library(uint32_t cell_name_id) const {
        for (int i = 0; i < static_cast<int>(libs_.size()); ++i) {
            for (uint32_t j = 0; j < libs_[i].cells.size(); ++j) {
                if (libs_[i].cells[j].name == cell_name_id) {
                    return {i, LibertyCellHandle{j}};
                }
            }
        }
        return {-1, NULL_LIBERTY_CELL};
    }

private:
    std::vector<LibertyLibrary> libs_;
};

inline LibertyCellHandle liberty_find_or_add_cell(LibertyLibrary& lib, uint32_t name_id) {
    for (uint32_t i = 0; i < lib.cells.size(); ++i) {
        if (lib.cells[i].name == name_id) return LibertyCellHandle{i};
    }
    return LibertyCellHandle{lib.cells.emplace(LibertyCellData{name_id})};
}

inline std::string normalize_liberty_func(std::string_view f) {
    std::string result;
    result.reserve(f.size());
    for (size_t i = 0; i < f.size(); ++i) {
        char c = f[i];
        if (std::isspace(static_cast<unsigned char>(c))) {
            size_t j = i + 1;
            while (j < f.size() && std::isspace(static_cast<unsigned char>(f[j]))) ++j;
            if (j < f.size() && (f[j] == '|' || f[j] == '+' || f[j] == '&' ||
                                 f[j] == '*' || f[j] == '^')) {
                continue;
            }
            if (!result.empty()) {
                char p = result.back();
                if (p == '|' || p == '&' || p == '*' || p == '+' || p == '^' || p == '!') {
                    continue;
                }
            }
            if (result.empty() || result.back() != '&') result += '&';
            continue;
        }
        if (c == '(' || c == ')' || c == '"') continue;
        if (c == '*') c = '&';
        else if (c == '+') c = '|';
        result += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }

    std::string clean;
    clean.reserve(result.size());
    for (size_t i = 0; i < result.size(); ++i) {
        char c = result[i];
        if (c == '&') {
            while (i + 1 < result.size() && result[i + 1] == '&') ++i;
            // Flattened Liberty expressions may spell OR as "& | &".
            // The conjunction following the OR is redundant.
            if (!clean.empty() && clean.back() == '|') continue;
            clean += '&';
            continue;
        }
        if (!clean.empty()) {
            char p = clean.back();
            if (p == '&' && c == '|') {
                clean.back() = '|';
                continue;
            }
        }
        clean += c;
    }
    return clean;
}

inline std::vector<uint32_t> cells_by_function(const LibertyLibrary& lib,
                                               const StringPool& pool,
                                               std::string_view func) {
    std::string nf = normalize_liberty_func(func);
    std::vector<uint32_t> result;
    for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
        const auto& cell = lib.cells[ci];
        if (cell.function != UINT32_MAX) {
            std::string cf = normalize_liberty_func(pool.view(cell.function));
            if (cf == nf) {
                result.push_back(ci);
                continue;
            }
        }
        for (const auto& pin : cell.pins) {
            if (pin.direction == PortDirection::Output && pin.function != UINT32_MAX) {
                std::string pf = normalize_liberty_func(pool.view(pin.function));
                if (pf == nf) {
                    result.push_back(ci);
                    break;
                }
            }
        }
    }
    return result;
}

inline std::vector<std::pair<uint32_t, uint32_t>>
cells_by_function_across(const LibertyDB& db,
                         const StringPool& pool,
                         std::string_view func) {
    std::vector<std::pair<uint32_t, uint32_t>> result;
    for (uint32_t li = 0; li < db.library_count(); ++li) {
        auto indices = cells_by_function(db.library(li), pool, func);
        for (uint32_t ci : indices) {
            result.push_back({li, ci});
        }
    }
    return result;
}

} // namespace edacraft::core

#endif // EDACRAFT_CORE_LIBERTY_DB_HPP
