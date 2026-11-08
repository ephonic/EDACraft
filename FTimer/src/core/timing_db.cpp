#include "edacraft/core/timing_db.hpp"

#include <algorithm>
#include <cmath>

namespace edacraft::core {

namespace {

TimingPointKey make_key(PinHandle pin, Transition transition, MinMax analysis,
                        uint32_t corner) {
    TimingPointKey key;
    key.pin = pin;
    key.transition = transition;
    key.analysis = analysis;
    key.corner = corner;
    return key;
}

} // namespace

size_t TimingPointKeyHash::operator()(const TimingPointKey& key) const {
    size_t h = std::hash<uint32_t>{}(key.pin.id);
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.transition)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.analysis)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint32_t>{}(key.corner) + 0x9e3779b9u + (h << 6) + (h >> 2));
    return h;
}

size_t TimingArcKeyHash::operator()(const TimingArcKey& key) const {
    size_t h = std::hash<uint32_t>{}(key.from_pin.id);
    h ^= (std::hash<uint32_t>{}(key.to_pin.id) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.from_transition)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.to_transition)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.analysis)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint32_t>{}(key.corner) + 0x9e3779b9u + (h << 6) + (h >> 2));
    h ^= (std::hash<uint8_t>{}(static_cast<uint8_t>(key.type)) + 0x9e3779b9u + (h << 6) + (h >> 2));
    return h;
}

void TimingDB::set_point(TimingPoint point) {
    if (point.has_arrival && !std::isfinite(point.arrival_ns)) {
        point.has_arrival = false;
        point.arrival_ns = 0.0f;
    }
    if (point.has_required && !std::isfinite(point.required_ns)) {
        point.has_required = false;
        point.required_ns = 0.0f;
    }
    if (point.has_slack && !std::isfinite(point.slack_ns)) {
        point.has_slack = false;
        point.slack_ns = 0.0f;
    }
    if (point.has_slew && !std::isfinite(point.slew_ns)) {
        point.has_slew = false;
        point.slew_ns = 0.0f;
    }
    auto it = point_index_.find(point.key);
    if (it != point_index_.end()) {
        points_[it->second] = std::move(point);
        return;
    }
    uint32_t id = static_cast<uint32_t>(points_.size());
    point_index_[point.key] = id;
    points_.push_back(std::move(point));
}

void TimingDB::set_arrival(PinHandle pin, Transition transition, MinMax analysis,
                           float value_ns, uint32_t corner) {
    auto& point = get_or_create_point(make_key(pin, transition, analysis, corner));
    point.arrival_ns = std::isfinite(value_ns) ? value_ns : 0.0f;
    point.has_arrival = std::isfinite(value_ns);
}

void TimingDB::set_required(PinHandle pin, Transition transition, MinMax analysis,
                            float value_ns, uint32_t corner) {
    auto& point = get_or_create_point(make_key(pin, transition, analysis, corner));
    point.required_ns = std::isfinite(value_ns) ? value_ns : 0.0f;
    point.has_required = std::isfinite(value_ns);
}

void TimingDB::set_slack(PinHandle pin, Transition transition, MinMax analysis,
                         float value_ns, uint32_t corner) {
    auto& point = get_or_create_point(make_key(pin, transition, analysis, corner));
    point.slack_ns = std::isfinite(value_ns) ? value_ns : 0.0f;
    point.has_slack = std::isfinite(value_ns);
}

void TimingDB::set_slew(PinHandle pin, Transition transition, MinMax analysis,
                        float value_ns, uint32_t corner) {
    auto& point = get_or_create_point(make_key(pin, transition, analysis, corner));
    point.slew_ns = std::isfinite(value_ns) ? value_ns : 0.0f;
    point.has_slew = std::isfinite(value_ns);
}

const TimingPoint* TimingDB::find_point(const TimingPointKey& key) const {
    auto it = point_index_.find(key);
    if (it == point_index_.end()) return nullptr;
    return &points_[it->second];
}

std::optional<float> TimingDB::arrival(PinHandle pin, Transition transition,
                                       MinMax analysis, uint32_t corner) const {
    return point_value(make_key(pin, transition, analysis, corner), 'a');
}

std::optional<float> TimingDB::required(PinHandle pin, Transition transition,
                                        MinMax analysis, uint32_t corner) const {
    return point_value(make_key(pin, transition, analysis, corner), 'r');
}

std::optional<float> TimingDB::slack(PinHandle pin, Transition transition,
                                     MinMax analysis, uint32_t corner) const {
    return point_value(make_key(pin, transition, analysis, corner), 's');
}

std::optional<float> TimingDB::slew(PinHandle pin, Transition transition,
                                    MinMax analysis, uint32_t corner) const {
    return point_value(make_key(pin, transition, analysis, corner), 'w');
}

TimingArcHandle TimingDB::add_arc(TimingArc arc) {
    uint32_t id = static_cast<uint32_t>(arcs_.size());
    arc_index_[make_arc_key(arc)] = id;
    arcs_.push_back(std::move(arc));
    return TimingArcHandle{id};
}

TimingArcHandle TimingDB::set_arc(TimingArc arc) {
    auto key = make_arc_key(arc);
    auto it = arc_index_.find(key);
    if (it != arc_index_.end()) {
        arcs_[it->second] = std::move(arc);
        return TimingArcHandle{it->second};
    }
    uint32_t id = static_cast<uint32_t>(arcs_.size());
    arc_index_[key] = id;
    arcs_.push_back(std::move(arc));
    return TimingArcHandle{id};
}

const TimingArc* TimingDB::arc(TimingArcHandle handle) const {
    if (!valid(handle) || handle.id >= arcs_.size()) return nullptr;
    return &arcs_[handle.id];
}

const TimingArc* TimingDB::find_arc(const TimingArcKey& key) const {
    auto it = arc_index_.find(key);
    if (it == arc_index_.end()) return nullptr;
    return &arcs_[it->second];
}

std::optional<float> TimingDB::arc_delay(PinHandle from_pin, PinHandle to_pin,
                                         Transition from_transition,
                                         Transition to_transition,
                                         MinMax analysis,
                                         uint32_t corner) const {
    const TimingArc* found = find_delay_arc(from_pin, to_pin, from_transition,
                                            to_transition, analysis, corner);
    if (!found) return std::nullopt;
    return found->delay_ns;
}

std::optional<float> TimingDB::arc_output_slew(PinHandle from_pin, PinHandle to_pin,
                                               Transition from_transition,
                                               Transition to_transition,
                                               MinMax analysis,
                                               uint32_t corner) const {
    const TimingArc* found = find_delay_arc(from_pin, to_pin, from_transition,
                                            to_transition, analysis, corner);
    if (!found) return std::nullopt;
    return found->output_slew_ns;
}

std::optional<float> TimingDB::arc_effective_capacitance(PinHandle from_pin, PinHandle to_pin,
                                                         Transition from_transition,
                                                         Transition to_transition,
                                                         MinMax analysis,
                                                         uint32_t corner) const {
    const TimingArc* found = find_delay_arc(from_pin, to_pin, from_transition,
                                            to_transition, analysis, corner);
    if (!found) return std::nullopt;
    return found->effective_capacitance;
}

std::optional<TimingDelayModel> TimingDB::arc_delay_model(PinHandle from_pin, PinHandle to_pin,
                                                          Transition from_transition,
                                                          Transition to_transition,
                                                          MinMax analysis,
                                                          uint32_t corner) const {
    const TimingArc* found = find_delay_arc(from_pin, to_pin, from_transition,
                                            to_transition, analysis, corner);
    if (!found) return std::nullopt;
    return found->delay_model;
}

std::optional<float> TimingDB::arc_constraint(PinHandle from_pin, PinHandle to_pin,
                                              Transition from_transition,
                                              Transition to_transition,
                                              MinMax analysis,
                                              uint32_t corner) const {
    TimingArcKey key;
    key.from_pin = from_pin;
    key.to_pin = to_pin;
    key.from_transition = from_transition;
    key.to_transition = to_transition;
    key.analysis = analysis;
    key.corner = corner;
    key.type = (analysis == MinMax::Min) ? TimingArcType::Hold : TimingArcType::Setup;
    const TimingArc* found = find_arc(key);
    if (!found || !found->has_constraint) return std::nullopt;
    return found->constraint_ns;
}

TimingPathHandle TimingDB::add_path(TimingPath path) {
    uint32_t id = static_cast<uint32_t>(paths_.size());
    paths_.push_back(std::move(path));
    return TimingPathHandle{id};
}

void TimingDB::clear_paths() {
    paths_.clear();
}

const TimingPath* TimingDB::path(TimingPathHandle handle) const {
    if (!valid(handle) || handle.id >= paths_.size()) return nullptr;
    return &paths_[handle.id];
}

std::vector<const TimingPath*> TimingDB::critical_paths(size_t max_paths,
                                                        MinMax analysis,
                                                        uint32_t corner) const {
    std::vector<const TimingPath*> result;
    for (const auto& path : paths_) {
        if (path.analysis == analysis && path.corner == corner) {
            result.push_back(&path);
        }
    }
    std::sort(result.begin(), result.end(),
              [](const TimingPath* lhs, const TimingPath* rhs) {
                  return lhs->slack_ns < rhs->slack_ns;
              });
    if (result.size() > max_paths) result.resize(max_paths);
    return result;
}

TimingExceptionHandle TimingDB::add_exception(ResolvedTimingException exception) {
    uint32_t id = static_cast<uint32_t>(exceptions_.size());
    exceptions_.push_back(std::move(exception));
    return TimingExceptionHandle{id};
}

const ResolvedTimingException* TimingDB::exception(TimingExceptionHandle handle) const {
    if (!valid(handle) || handle.id >= exceptions_.size()) return nullptr;
    return &exceptions_[handle.id];
}

std::optional<float> TimingDB::worst_slack(MinMax analysis, uint32_t corner) const {
    std::optional<float> worst;
    for (const auto& point : points_) {
        if (point.key.analysis != analysis || point.key.corner != corner || !point.has_slack) {
            continue;
        }
        if (!worst || point.slack_ns < *worst) worst = point.slack_ns;
    }
    if (worst) return worst;

    for (const auto& path : paths_) {
        if (path.analysis != analysis || path.corner != corner) continue;
        if (!worst || path.slack_ns < *worst) worst = path.slack_ns;
    }
    return worst;
}

bool TimingDB::empty() const {
    return points_.empty() && arcs_.empty() && paths_.empty() && exceptions_.empty();
}

void TimingDB::clear() {
    points_.clear();
    point_index_.clear();
    arcs_.clear();
    arc_index_.clear();
    paths_.clear();
    exceptions_.clear();
}

TimingPoint& TimingDB::get_or_create_point(const TimingPointKey& key) {
    auto it = point_index_.find(key);
    if (it != point_index_.end()) return points_[it->second];

    uint32_t id = static_cast<uint32_t>(points_.size());
    TimingPoint point;
    point.key = key;
    points_.push_back(point);
    point_index_[key] = id;
    return points_.back();
}

std::optional<float> TimingDB::point_value(const TimingPointKey& key,
                                           char value_kind) const {
    const TimingPoint* point = find_point(key);
    if (!point) return std::nullopt;

    switch (value_kind) {
        case 'a':
            if (point->has_arrival && std::isfinite(point->arrival_ns)) {
                return point->arrival_ns;
            }
            break;
        case 'r':
            if (point->has_required && std::isfinite(point->required_ns)) {
                return point->required_ns;
            }
            break;
        case 's':
            if (point->has_slack && std::isfinite(point->slack_ns)) {
                return point->slack_ns;
            }
            break;
        case 'w':
            if (point->has_slew && std::isfinite(point->slew_ns)) {
                return point->slew_ns;
            }
            break;
        default:
            break;
    }
    return std::nullopt;
}

const TimingArc* TimingDB::find_delay_arc(PinHandle from_pin, PinHandle to_pin,
                                          Transition from_transition,
                                          Transition to_transition,
                                          MinMax analysis,
                                          uint32_t corner) const {
    TimingArcKey key;
    key.from_pin = from_pin;
    key.to_pin = to_pin;
    key.from_transition = from_transition;
    key.to_transition = to_transition;
    key.analysis = analysis;
    key.corner = corner;
    for (TimingArcType type : {TimingArcType::Combinational,
                               TimingArcType::RisingEdge,
                               TimingArcType::FallingEdge}) {
        key.type = type;
        const TimingArc* found = find_arc(key);
        if (found && !found->has_constraint) return found;
    }
    return nullptr;
}

TimingArcKey TimingDB::make_arc_key(const TimingArc& arc) {
    TimingArcKey key;
    key.from_pin = arc.from_pin;
    key.to_pin = arc.to_pin;
    key.from_transition = arc.from_transition;
    key.to_transition = arc.to_transition;
    key.analysis = arc.analysis;
    key.corner = arc.corner;
    key.type = arc.type;
    return key;
}

} // namespace edacraft::core
