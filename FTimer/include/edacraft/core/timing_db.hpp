#ifndef EDACRAFT_CORE_TIMING_DB_HPP
#define EDACRAFT_CORE_TIMING_DB_HPP

#include "edacraft/core/ids.hpp"

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace edacraft::core {

struct TimingArcHandle { uint32_t id; };
struct TimingPathHandle { uint32_t id; };
struct TimingExceptionHandle { uint32_t id; };

constexpr TimingArcHandle NULL_TIMING_ARC{UINT32_MAX};
constexpr TimingPathHandle NULL_TIMING_PATH{UINT32_MAX};
constexpr TimingExceptionHandle NULL_TIMING_EXCEPTION{UINT32_MAX};

inline bool valid(TimingArcHandle h) { return h.id != UINT32_MAX; }
inline bool valid(TimingPathHandle h) { return h.id != UINT32_MAX; }
inline bool valid(TimingExceptionHandle h) { return h.id != UINT32_MAX; }

inline bool operator==(TimingArcHandle a, TimingArcHandle b) { return a.id == b.id; }
inline bool operator!=(TimingArcHandle a, TimingArcHandle b) { return a.id != b.id; }
inline bool operator==(TimingPathHandle a, TimingPathHandle b) { return a.id == b.id; }
inline bool operator!=(TimingPathHandle a, TimingPathHandle b) { return a.id != b.id; }
inline bool operator==(TimingExceptionHandle a, TimingExceptionHandle b) { return a.id == b.id; }
inline bool operator!=(TimingExceptionHandle a, TimingExceptionHandle b) { return a.id != b.id; }

enum class TimingArcType : uint8_t {
    Combinational,
    RisingEdge,
    FallingEdge,
    Setup,
    Hold,
    Recovery,
    Removal,
    MinPulseWidth,
    Unknown,
};

enum class TimingSense : uint8_t {
    PositiveUnate,
    NegativeUnate,
    NonUnate,
    None,
};

enum class TimingExceptionType : uint8_t {
    FalsePath,
    MulticyclePath,
    DisableTiming,
    CaseAnalysis,
};

enum class TimingDelayModel : uint8_t {
    None,
    Nldm,
    Csm,
    AwePi,
    Lumped,
};

// A timing point is keyed by physical/logical pin, transition, min/max
// analysis mode, and corner. Corner 0 is the default single-corner view.
struct TimingPointKey {
    PinHandle pin = NULL_PIN;
    Transition transition = Transition::Rise;
    MinMax analysis = MinMax::Max;
    uint32_t corner = 0;

    bool operator==(const TimingPointKey& other) const {
        return pin == other.pin &&
               transition == other.transition &&
               analysis == other.analysis &&
               corner == other.corner;
    }
};

struct TimingPointKeyHash {
    size_t operator()(const TimingPointKey& key) const;
};

struct TimingArcKey {
    PinHandle from_pin = NULL_PIN;
    PinHandle to_pin = NULL_PIN;
    Transition from_transition = Transition::Rise;
    Transition to_transition = Transition::Rise;
    MinMax analysis = MinMax::Max;
    uint32_t corner = 0;
    TimingArcType type = TimingArcType::Combinational;

    bool operator==(const TimingArcKey& other) const {
        return from_pin == other.from_pin &&
               to_pin == other.to_pin &&
               from_transition == other.from_transition &&
               to_transition == other.to_transition &&
               analysis == other.analysis &&
               corner == other.corner &&
               type == other.type;
    }
};

struct TimingArcKeyHash {
    size_t operator()(const TimingArcKey& key) const;
};

struct TimingPoint {
    TimingPointKey key;
    float arrival_ns = 0.0f;
    float required_ns = 0.0f;
    float slack_ns = 0.0f;
    float slew_ns = 0.0f;
    bool has_arrival = false;
    bool has_required = false;
    bool has_slack = false;
    bool has_slew = false;
};

struct TimingArc {
    PinHandle from_pin = NULL_PIN;
    PinHandle to_pin = NULL_PIN;
    Transition from_transition = Transition::Rise;
    Transition to_transition = Transition::Rise;
    MinMax analysis = MinMax::Max;
    uint32_t corner = 0;
    TimingArcType type = TimingArcType::Combinational;
    TimingSense sense = TimingSense::None;
    TimingDelayModel delay_model = TimingDelayModel::None;
    float delay_ns = 0.0f;
    float output_slew_ns = 0.0f;
    float effective_capacitance = 0.0f;
    float constraint_ns = 0.0f;
    bool has_constraint = false;
    bool disabled = false;
    std::string source;
};

struct TimingPathPoint {
    PinHandle pin = NULL_PIN;
    std::string pin_name;
    Transition transition = Transition::Rise;
    float arrival_ns = 0.0f;
    float required_ns = 0.0f;
    float slack_ns = 0.0f;
    float slew_ns = 0.0f;
    float arc_delay_ns = 0.0f;
};

struct TimingPath {
    PinHandle startpoint = NULL_PIN;
    PinHandle endpoint = NULL_PIN;
    Transition endpoint_transition = Transition::Rise;
    MinMax analysis = MinMax::Max;
    uint32_t corner = 0;
    std::string path_group;
    float slack_ns = 0.0f;
    std::vector<TimingPathPoint> points;
};

struct ResolvedTimingException {
    TimingExceptionType type = TimingExceptionType::FalsePath;
    PinHandle from_pin = NULL_PIN;
    PinHandle through_pin = NULL_PIN;
    std::vector<std::vector<PinHandle>> through_stages;
    PinHandle to_pin = NULL_PIN;
    MinMax analysis = MinMax::Max;
    uint32_t corner = 0;
    int setup_cycles = 1;
    int hold_cycles = 0;
    int case_value = -1;
    std::string source;
    std::vector<uint32_t> from_clocks, to_clocks;
    bool is_hold = false;
    bool use_start = false;
};

class TimingDB {
public:
    TimingDB() = default;

    // Point values.
    void set_point(TimingPoint point);
    void set_arrival(PinHandle pin, Transition transition, MinMax analysis,
                     float value_ns, uint32_t corner = 0);
    void set_required(PinHandle pin, Transition transition, MinMax analysis,
                      float value_ns, uint32_t corner = 0);
    void set_slack(PinHandle pin, Transition transition, MinMax analysis,
                   float value_ns, uint32_t corner = 0);
    void set_slew(PinHandle pin, Transition transition, MinMax analysis,
                  float value_ns, uint32_t corner = 0);

    const TimingPoint* find_point(const TimingPointKey& key) const;
    std::optional<float> arrival(PinHandle pin, Transition transition,
                                 MinMax analysis, uint32_t corner = 0) const;
    std::optional<float> required(PinHandle pin, Transition transition,
                                  MinMax analysis, uint32_t corner = 0) const;
    std::optional<float> slack(PinHandle pin, Transition transition,
                               MinMax analysis, uint32_t corner = 0) const;
    std::optional<float> slew(PinHandle pin, Transition transition,
                              MinMax analysis, uint32_t corner = 0) const;
    const std::vector<TimingPoint>& points() const { return points_; }

    // Arcs.
    TimingArcHandle add_arc(TimingArc arc);
    TimingArcHandle set_arc(TimingArc arc);
    const TimingArc* arc(TimingArcHandle handle) const;
    const TimingArc* find_arc(const TimingArcKey& key) const;
    std::optional<float> arc_delay(PinHandle from_pin, PinHandle to_pin,
                                   Transition from_transition,
                                   Transition to_transition,
                                   MinMax analysis = MinMax::Max,
                                   uint32_t corner = 0) const;
    std::optional<float> arc_output_slew(PinHandle from_pin, PinHandle to_pin,
                                         Transition from_transition,
                                         Transition to_transition,
                                         MinMax analysis = MinMax::Max,
                                         uint32_t corner = 0) const;
    std::optional<float> arc_effective_capacitance(PinHandle from_pin, PinHandle to_pin,
                                                   Transition from_transition,
                                                   Transition to_transition,
                                                   MinMax analysis = MinMax::Max,
                                                   uint32_t corner = 0) const;
    std::optional<TimingDelayModel> arc_delay_model(PinHandle from_pin, PinHandle to_pin,
                                                    Transition from_transition,
                                                    Transition to_transition,
                                                    MinMax analysis = MinMax::Max,
                                                    uint32_t corner = 0) const;
    std::optional<float> arc_constraint(PinHandle from_pin, PinHandle to_pin,
                                        Transition from_transition,
                                        Transition to_transition,
                                        MinMax analysis,
                                        uint32_t corner = 0) const;
    const std::vector<TimingArc>& arcs() const { return arcs_; }

    // Paths.
    TimingPathHandle add_path(TimingPath path);
    const TimingPath* path(TimingPathHandle handle) const;
    const std::vector<TimingPath>& paths() const { return paths_; }
    void clear_paths();
    std::vector<const TimingPath*> critical_paths(size_t max_paths,
                                                  MinMax analysis = MinMax::Max,
                                                  uint32_t corner = 0) const;

    // Resolved exceptions.
    TimingExceptionHandle add_exception(ResolvedTimingException exception);
    const ResolvedTimingException* exception(TimingExceptionHandle handle) const;
    const std::vector<ResolvedTimingException>& exceptions() const { return exceptions_; }

    // Summary.
    std::optional<float> worst_slack(MinMax analysis = MinMax::Max,
                                     uint32_t corner = 0) const;
    bool empty() const;
    void clear();

private:
    TimingPoint& get_or_create_point(const TimingPointKey& key);
    std::optional<float> point_value(const TimingPointKey& key,
                                     char value_kind) const;
    const TimingArc* find_delay_arc(PinHandle from_pin, PinHandle to_pin,
                                    Transition from_transition,
                                    Transition to_transition,
                                    MinMax analysis,
                                    uint32_t corner) const;
    static TimingArcKey make_arc_key(const TimingArc& arc);

    std::vector<TimingPoint> points_;
    std::unordered_map<TimingPointKey, uint32_t, TimingPointKeyHash> point_index_;
    std::vector<TimingArc> arcs_;
    std::unordered_map<TimingArcKey, uint32_t, TimingArcKeyHash> arc_index_;
    std::vector<TimingPath> paths_;
    std::vector<ResolvedTimingException> exceptions_;
};

} // namespace edacraft::core

#endif // EDACRAFT_CORE_TIMING_DB_HPP
