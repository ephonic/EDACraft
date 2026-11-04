#pragma once

#include <cstdint>
#include <limits>
#include <string>

namespace te {

// ────────────────────────────────────────────────────────────
// Transition direction: rise or fall
// ────────────────────────────────────────────────────────────
enum class Transition : uint8_t { Rise = 0, Fall = 1 };
inline constexpr int TRANSITION_COUNT = 2;

// ────────────────────────────────────────────────────────────
// Min/Max analysis corner
// ────────────────────────────────────────────────────────────
enum class MinMax : uint8_t { Min = 0, Max = 1 };
enum class TimingCheckKind : uint8_t { Any, Data, Setup, Hold, Recovery, Removal, OutputDelay, None };
inline bool timing_check_matches(TimingCheckKind actual, TimingCheckKind filter) {
    return filter == TimingCheckKind::Any || actual == filter ||
        (filter == TimingCheckKind::Data && (actual == TimingCheckKind::Setup ||
         actual == TimingCheckKind::Hold || actual == TimingCheckKind::OutputDelay));
}
inline constexpr int MIN_MAX_COUNT = 2;

// ────────────────────────────────────────────────────────────
// Combined index: 4-element array indexed by (min_max, transition)
//   index = mm * 2 + rf
// ────────────────────────────────────────────────────────────
inline constexpr int mm_rf_index(MinMax mm, Transition rf) {
    return static_cast<int>(mm) * TRANSITION_COUNT + static_cast<int>(rf);
}

inline MinMax index_min_max(int index) {
    return static_cast<MinMax>(index / TRANSITION_COUNT);
}

inline Transition index_transition(int index) {
    return static_cast<Transition>(index % TRANSITION_COUNT);
}

// ────────────────────────────────────────────────────────────
// Strongly-typed 32-bit identifiers (index into ObjectTable)
// ────────────────────────────────────────────────────────────
struct NetId       { uint32_t id; };
struct PinId       { uint32_t id; };
struct InstanceId  { uint32_t id; };
struct CellId      { uint32_t id; };
struct VertexId    { uint32_t id; };
struct EdgeId      { uint32_t id; };
struct LibraryId   { uint32_t id; };
struct LibertyCellId { uint32_t id; };
struct LibertyPinId  { uint32_t id; };
struct LibertyArcId  { uint32_t id; };
struct StringId    { uint32_t id; };
struct ClockId     { uint32_t id; };

constexpr NetId        NULL_NET{UINT32_MAX};
constexpr PinId        NULL_PIN{UINT32_MAX};
enum class CheckCoverageState : uint8_t {
    Evaluated, ExcludedDisabled, ExcludedFalsePath, MissingTable,
    MissingRelatedPin, MissingCaptureClock, MissingLaunchClock,
    MissingArrival, InvalidCheck, ExcludedClockGroup, UnsupportedMixedClockPaths
};
struct TimingCheckCoverage {
    PinId pin;
    uint32_t arc;
    Transition transition;
    MinMax analysis;
    TimingCheckKind kind;
    CheckCoverageState state;
};
struct TimingCheckResult {
    TimingCheckCoverage coverage{PinId{UINT32_MAX}, UINT32_MAX, Transition::Rise,
        MinMax::Max, TimingCheckKind::None, CheckCoverageState::InvalidCheck};
    // Logical arc signature (type/related pin/when/duplicate ordinal), stable
    // across library cell sizing and independent of the physical arc index.
    std::string identity;
    PinId related{UINT32_MAX};
    Transition capture_transition = Transition::Rise;
    uint32_t capture_domain = UINT32_MAX;
    uint64_t launch_key = UINT64_MAX; // Untagged scalar analysis.
    std::string launch_identity; // Stable exception history; empty without history.
    float arrival = std::numeric_limits<float>::quiet_NaN();
    float required = std::numeric_limits<float>::quiet_NaN();
    float slack = std::numeric_limits<float>::quiet_NaN();
    float cppr = 0.0f;
    float path_time_shift = 0.0f; // report-only launch-cycle alignment
};
inline const char* check_coverage_name(CheckCoverageState state) {
    switch (state) {
    case CheckCoverageState::Evaluated: return "evaluated";
    case CheckCoverageState::ExcludedDisabled: return "excluded_disabled";
    case CheckCoverageState::ExcludedFalsePath: return "excluded_false_path";
    case CheckCoverageState::MissingTable: return "missing_table";
    case CheckCoverageState::MissingRelatedPin: return "missing_related_pin";
    case CheckCoverageState::MissingCaptureClock: return "missing_capture_clock";
    case CheckCoverageState::MissingLaunchClock: return "missing_launch_clock";
    case CheckCoverageState::MissingArrival: return "missing_arrival";
    case CheckCoverageState::InvalidCheck: return "invalid_check";
    case CheckCoverageState::ExcludedClockGroup: return "excluded_clock_group";
    case CheckCoverageState::UnsupportedMixedClockPaths: return "unsupported_mixed_clock_paths";
    }
    return "invalid_check";
}
inline bool check_coverage_valid(CheckCoverageState state) {
    return state == CheckCoverageState::Evaluated ||
        state == CheckCoverageState::ExcludedDisabled || state == CheckCoverageState::ExcludedFalsePath ||
        state == CheckCoverageState::ExcludedClockGroup;
}
constexpr InstanceId   NULL_INSTANCE{UINT32_MAX};
constexpr CellId       NULL_CELL{UINT32_MAX};
constexpr VertexId     NULL_VERTEX{UINT32_MAX};
constexpr EdgeId       NULL_EDGE{UINT32_MAX};
constexpr LibraryId    NULL_LIBRARY{UINT32_MAX};
constexpr LibertyCellId NULL_LIBERTY_CELL{UINT32_MAX};
constexpr LibertyPinId  NULL_LIBERTY_PIN{UINT32_MAX};
constexpr LibertyArcId  NULL_LIBERTY_ARC{UINT32_MAX};
constexpr StringId     NULL_STRING{UINT32_MAX};
constexpr ClockId      NULL_CLOCK{UINT32_MAX};

inline bool valid(NetId id)        { return id.id != UINT32_MAX; }
inline bool valid(PinId id)        { return id.id != UINT32_MAX; }
inline bool valid(InstanceId id)   { return id.id != UINT32_MAX; }
inline bool valid(CellId id)       { return id.id != UINT32_MAX; }
inline bool valid(VertexId id)     { return id.id != UINT32_MAX; }
inline bool valid(EdgeId id)       { return id.id != UINT32_MAX; }
inline bool valid(LibraryId id)    { return id.id != UINT32_MAX; }
inline bool valid(LibertyCellId id) { return id.id != UINT32_MAX; }
inline bool valid(LibertyPinId id)  { return id.id != UINT32_MAX; }
inline bool valid(LibertyArcId id)  { return id.id != UINT32_MAX; }
inline bool valid(StringId id)     { return id.id != UINT32_MAX; }
inline bool valid(ClockId id)      { return id.id != UINT32_MAX; }

inline bool operator==(NetId a, NetId b)        { return a.id == b.id; }
inline bool operator!=(NetId a, NetId b)        { return a.id != b.id; }
inline bool operator==(PinId a, PinId b)        { return a.id == b.id; }
inline bool operator!=(PinId a, PinId b)        { return a.id != b.id; }
inline bool operator==(InstanceId a, InstanceId b) { return a.id == b.id; }
inline bool operator!=(InstanceId a, InstanceId b) { return a.id != b.id; }
inline bool operator==(CellId a, CellId b)      { return a.id == b.id; }
inline bool operator!=(CellId a, CellId b)      { return a.id != b.id; }
inline bool operator==(VertexId a, VertexId b)  { return a.id == b.id; }
inline bool operator!=(VertexId a, VertexId b)  { return a.id != b.id; }
inline bool operator==(EdgeId a, EdgeId b)      { return a.id == b.id; }
inline bool operator!=(EdgeId a, EdgeId b)      { return a.id != b.id; }
inline bool operator==(LibertyCellId a, LibertyCellId b) { return a.id == b.id; }
inline bool operator!=(LibertyCellId a, LibertyCellId b) { return a.id != b.id; }
inline bool operator==(LibertyPinId a, LibertyPinId b)  { return a.id == b.id; }
inline bool operator!=(LibertyPinId a, LibertyPinId b)  { return a.id != b.id; }

// ────────────────────────────────────────────────────────────
// Timing quantities (in library units)
// ────────────────────────────────────────────────────────────
struct Delay {
    float value;
    static constexpr Delay ZERO() { return {0.0f}; }
    static constexpr Delay INF() { return {std::numeric_limits<float>::infinity()}; }
    static constexpr Delay NEG_INF() { return {-std::numeric_limits<float>::infinity()}; }

    constexpr Delay operator+(const Delay& o) const { return {value + o.value}; }
    constexpr Delay operator-(const Delay& o) const { return {value - o.value}; }
    constexpr bool  operator<(const Delay& o) const { return value < o.value; }
    constexpr bool  operator>(const Delay& o) const { return value > o.value; }
    constexpr bool  operator<=(const Delay& o) const { return value <= o.value; }
    constexpr bool  operator>=(const Delay& o) const { return value >= o.value; }
    // Note: exact float comparison is intentional.
    // Timing values are often sentinel-checked (INF, NEG_INF, 0),
    // and epsilon-based comparison would break those checks.
    constexpr bool  operator==(const Delay& o) const { return value == o.value; }
    constexpr bool  operator!=(const Delay& o) const { return value != o.value; }
};

using Slew     = Delay;
using Arrival  = Delay;
using Required = Delay;
using Slack    = Delay;

// ────────────────────────────────────────────────────────────
// PVT operating condition point
// ────────────────────────────────────────────────────────────
struct Pvt {
    float process;      // relative (1.0 = nominal)
    float voltage;      // library voltage units
    float temperature;  // Celsius
};

// ────────────────────────────────────────────────────────────
// Timing sense for arc propagation
// ────────────────────────────────────────────────────────────
enum class TimingSense : uint8_t {
    PositiveUnate,
    NegativeUnate,
    NonUnate,
    None,
};
inline constexpr int TIMING_SENSE_COUNT = 4;

// ────────────────────────────────────────────────────────────
// Timing arc type
// ────────────────────────────────────────────────────────────
enum class TimingType : uint8_t {
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
};

// ────────────────────────────────────────────────────────────
// Port direction
// ────────────────────────────────────────────────────────────
enum class PortDirection : uint8_t {
    Input,
    Output,
    Inout,
    Internal,
};

// ────────────────────────────────────────────────────────────
// Early / Late for statistical timing (placeholder)
// ────────────────────────────────────────────────────────────
enum class EarlyLate : uint8_t { Early = 0, Late = 1 };
inline constexpr int EARLY_LATE_COUNT = 2;

} // namespace te
