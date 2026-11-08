#include "edacraft/core/constraint_db.hpp"
#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <unordered_set>

namespace edacraft::core {

void ConstraintDB::add_clock(ClockDef clock) {
    // Replace existing clock with same name
    for (auto& existing : clocks_) {
        if (existing.name == clock.name) {
            existing = std::move(clock);
            return;
        }
    }
    clocks_.push_back(std::move(clock));
}

void ConstraintDB::set_clock_propagated(const std::string& name, bool propagated) {
    for (auto& clock : clocks_) {
        if (name == "*" || clock.name == name) clock.propagated = propagated;
    }
}

bool ConstraintDB::resolve_generated_clocks(std::string& error) {
    error.clear();
    auto updated = clocks_;
    std::unordered_map<std::string, size_t> names;
    for (size_t i = 0; i < updated.size(); ++i) names[updated[i].name] = i;
    std::vector<uint8_t> state(updated.size(), 0);
    std::function<bool(size_t, size_t)> visit = [&](size_t index, size_t depth) {
        if (depth > 128) { error = "Generated clock dependency depth exceeded"; return false; }
        if (state[index] == 2) return true;
        if (state[index] == 1) { error = "Generated clock dependency cycle"; return false; }
        state[index] = 1;
        auto& clock = updated[index];
        if (!clock.generated) { state[index] = 2; return true; }
        auto& def = *clock.generated;
        size_t master = updated.size();
        if (!def.master_clock.empty()) {
            const auto found = names.find(def.master_clock);
            if (found != names.end()) master = found->second;
        } else {
            for (size_t i = 0; i < updated.size(); ++i) {
                if (i == index || updated[i].source_port != def.source ||
                    updated[i].source_is_pin != def.source_is_pin) continue;
                if (master != updated.size()) {
                    error = "Ambiguous generated clock master for " + clock.name; return false;
                }
                master = i;
            }
        }
        if (master == updated.size()) {
            error = "Generated clock " + clock.name + " needs an existing master; use -master_clock for a source inside its tree";
            return false;
        }
        if (!visit(master, depth + 1)) return false;
        const auto& parent = updated[master];
        // The current latency model does not retain source/network or
        // early/late qualifiers. Do not invent inheritance for generated
        // clocks by adding these different quantities together.
        if (parent.latency_ns != 0 || clock.latency_ns != 0) {
            error = "Generated clocks currently require zero source/network latency"; return false;
        }
        for (const auto& latency : clock_latencies_) {
            if (latency.latency_ns != 0 && (latency.clock_name.empty() ||
                latency.clock_name == parent.name || latency.clock_name == clock.name || !latency.pin_names.empty())) {
                error = "Generated clocks with qualified or pin latency require the extended latency model"; return false;
            }
        }
        for (const auto& delay : io_delays_) {
            const auto reference = names.find(delay.clock_name);
            if (reference == names.end()) {
                error = "Generated-clock designs require exact primary clock references for I/O delays"; return false;
            }
            if (updated[reference->second].generated) {
                error = "I/O delays referenced to generated clocks require the extended I/O edge model"; return false;
            }
        }
        for (const auto& uncertainty : clock_uncertainties_) {
            if (!names.count(uncertainty.clock_name)) {
                error = "Generated-clock designs require exact per-clock uncertainty references"; return false;
            }
        }
        const double period = parent.period_ns;
        const double rise = parent.waveform_explicit ? parent.rise_edge_ns : 0.0;
        const double fall = parent.waveform_explicit ? parent.fall_edge_ns : period * .5;
        if (!std::isfinite(period) || period <= 0 || !std::isfinite(rise) || !std::isfinite(fall) ||
            rise < 0 || fall <= rise || fall >= rise + period) {
            error = "Unsupported master waveform for generated clock " + clock.name; return false;
        }
        double p = period, r = rise, f = fall;
        if (def.combinational && !def.divide_by && !def.multiply_by && def.edges.empty()) def.divide_by = 1;
        const unsigned modes = unsigned(def.divide_by != 0) + unsigned(def.multiply_by != 0) + unsigned(!def.edges.empty());
        if (modes != 1 || (def.combinational && (def.divide_by != 1 || !def.edges.empty())) ||
            (def.duty_cycle != 0 && (!def.multiply_by || !std::isfinite(def.duty_cycle) || def.duty_cycle <= 0 || def.duty_cycle >= 100)) ||
            (!def.edge_shifts_ns.empty() && def.edge_shifts_ns.size() != 3) ||
            (!def.edge_shifts_ns.empty() && def.edges.empty()) || (!def.edges.empty() && def.invert)) {
            error = "Invalid generated clock transform for " + clock.name; return false;
        }
        if (def.divide_by > 1) {
            const double ratio = def.divide_by;
            p *= ratio;
            if ((def.divide_by & (def.divide_by - 1)) == 0) f = r + p * .5;
            else { r *= ratio; f *= ratio; }
        } else if (def.multiply_by) {
            p /= def.multiply_by; r /= def.multiply_by; f /= def.multiply_by;
            if (def.duty_cycle != 0) f = r + p * def.duty_cycle / 100.0;
        } else if (!def.edges.empty()) {
            if (def.edges.size() != 3 || !def.edges[0] || def.edges[0] >= def.edges[1] || def.edges[1] >= def.edges[2]) {
                error = "Generated clock needs three increasing positive edge indices"; return false;
            }
            double times[3];
            for (size_t i = 0; i < 3; ++i) {
                const auto edge = def.edges[i] - 1;
                times[i] = (edge % 2 ? fall : rise) + (edge / 2) * period;
                if (!def.edge_shifts_ns.empty()) times[i] += def.edge_shifts_ns[i];
            }
            r = times[0]; f = times[1]; p = times[2] - r;
        }
        if (def.invert) { const double old_r = r; r = f; f = old_r + p; }
        // Preserve edge order and phase; never force an inverted falling edge
        // into [0, period), where it could precede the rising edge.
        if (p > 0 && std::isfinite(p) && std::isfinite(r)) {
            const double offset = std::floor(r / p) * p;
            r -= offset; f -= offset;
        }
        const double bound = std::numeric_limits<float>::max();
        if (!std::isfinite(p) || !std::isfinite(r) || !std::isfinite(f) ||
            p <= 0 || p > bound || r < 0 || f <= r || f >= r + p || f > bound) {
            error = "Invalid or overflowing generated waveform for " + clock.name; return false;
        }
        const float fp = static_cast<float>(p), fr = static_cast<float>(r), ff = static_cast<float>(f);
        if (!(fp > 0 && ff > fr && double(ff) < double(fr) + fp)) {
            error = "Generated clock waveform loses precision for " + clock.name; return false;
        }
        clock.period_ns = fp; clock.rise_edge_ns = fr; clock.fall_edge_ns = ff;
        clock.waveform_explicit = true;
        def.resolved_master_clock = parent.name;
        state[index] = 2;
        return true;
    };
    for (size_t i = 0; i < updated.size(); ++i) if (!visit(i, 0)) return false;
    clocks_ = std::move(updated);
    return true;
}

const ClockDef* ConstraintDB::find_clock(const std::string& name) const {
    for (const auto& c : clocks_) {
        if (c.name == name) return &c;
    }
    return nullptr;
}

const ClockDef* ConstraintDB::clock_for_port(const std::string& port) const {
    for (const auto& c : clocks_) {
        if (c.source_port == port) return &c;
    }
    return nullptr;
}

void ConstraintDB::add_clock_group(ClockGroupDef group) {
    if (group.groups.size() >= 2) {
        clock_groups_.push_back(std::move(group));
    }
}

void ConstraintDB::add_io_delay(IoDelay delay) {
    io_delays_.push_back(std::move(delay));
}

std::vector<IoDelay> ConstraintDB::input_delays() const {
    std::vector<IoDelay> result;
    for (const auto& d : io_delays_) {
        if (d.is_input) result.push_back(d);
    }
    return result;
}

std::vector<IoDelay> ConstraintDB::output_delays() const {
    std::vector<IoDelay> result;
    for (const auto& d : io_delays_) {
        if (!d.is_input) result.push_back(d);
    }
    return result;
}

void ConstraintDB::add_path_delay(PathDelay pd) {
    path_delays_.push_back(std::move(pd));
}

void ConstraintDB::add_data_check(DataCheckDef check) {
    data_checks_.push_back(std::move(check));
}

void ConstraintDB::add_path_group(PathGroupDef group) {
    for (auto& old : path_groups_) if (old.name == group.name) {
        if (group.weight_explicit) old.weight = group.weight;
        else group.weight = old.weight;
    }
    path_groups_.push_back(std::move(group));
}

void ConstraintDB::add_clock_latency(ClockLatencyDef cl) {
    clock_latencies_.push_back(std::move(cl));
}

void ConstraintDB::set_clock_uncertainty(ClockUncertaintyDef cu) {
    // Merge with existing entry for same clock (preserve setup/hold independently)
    for (auto& existing : clock_uncertainties_) {
        if (existing.clock_name == cu.clock_name) {
            if (cu.setup_uncertainty_ns != 0.0f)
                existing.setup_uncertainty_ns = cu.setup_uncertainty_ns;
            if (cu.hold_uncertainty_ns != 0.0f)
                existing.hold_uncertainty_ns = cu.hold_uncertainty_ns;
            return;
        }
    }
    clock_uncertainties_.push_back(std::move(cu));
}

void ConstraintDB::set_clock_waveform(const std::string& clock_name,
                                       float rise_ns, float fall_ns) {
    for (auto& c : clocks_) {
        if (c.name == clock_name) {
            c.rise_edge_ns = rise_ns;
            c.fall_edge_ns = fall_ns;
            c.waveform_explicit = true;
            return;
        }
    }
}

bool ConstraintDB::set_clock_transition(const std::string& clock_name,
                                        float transition_ns) {
    bool changed = false;
    for (auto& c : clocks_) {
        if (c.name == clock_name) {
            c.transition_ns = transition_ns;
            changed = true;
        }
    }
    return changed;
}

void ConstraintDB::add_multicycle_path(MulticyclePathDef mcp) {
    multicycle_paths_.push_back(std::move(mcp));
}

void ConstraintDB::add_false_path(FalsePathDef fp) {
    false_paths_.push_back(std::move(fp));
}

void ConstraintDB::add_disable_timing(DisableTimingDef dt) {
    disable_timings_.push_back(std::move(dt));
}

void ConstraintDB::add_case_analysis(CaseAnalysisDef ca) {
    case_analyses_.push_back(std::move(ca));
}

void ConstraintDB::add_set_load(SetLoadDef sl) {
    set_loads_.push_back(std::move(sl));
}

void ConstraintDB::add_input_transition(InputTransitionDef it) {
    it.order = ++input_driver_order_;
    input_transitions_.push_back(std::move(it));
}

void ConstraintDB::add_driving_cell(DrivingCellDef driver) {
    driver.order = ++input_driver_order_;
    driving_cells_.push_back(std::move(driver));
}

void ConstraintDB::set_ocv_derate(OcvDerateDef derate) {
    ocv_derate_ = derate;
}

void ConstraintDB::add_aocv_point(AocvPointDef point) {
    aocv_points_.push_back(point);
    // Keep sorted by depth
    std::sort(aocv_points_.begin(), aocv_points_.end(),
              [](const AocvPointDef& a, const AocvPointDef& b) {
                  return a.depth < b.depth;
              });
}

void ConstraintDB::set_max_fanout(float value) {
    design_rules_.max_fanout = value;
}

void ConstraintDB::set_max_capacitance(float value) {
    design_rules_.max_capacitance = value;
}

void ConstraintDB::set_max_transition(float value) {
    design_rules_.max_transition = value;
}

bool ConstraintDB::has_constraints() const {
    return !clocks_.empty()
        || !clock_groups_.empty()
        || !io_delays_.empty()
        || !path_delays_.empty()
        || !data_checks_.empty()
        || !path_groups_.empty()
        || !clock_latencies_.empty()
        || !clock_uncertainties_.empty()
        || !multicycle_paths_.empty()
        || !false_paths_.empty()
        || !disable_timings_.empty()
        || !case_analyses_.empty()
        || !set_loads_.empty()
        || !input_transitions_.empty()
        || !driving_cells_.empty()
        || ocv_derate_.early_data != 1.0f
        || ocv_derate_.late_data != 1.0f
        || ocv_derate_.early_clock != 1.0f
        || ocv_derate_.late_clock != 1.0f
        || !aocv_points_.empty()
        || design_rules_.max_fanout >= 0.0f
        || design_rules_.max_capacitance >= 0.0f
        || design_rules_.max_transition >= 0.0f;
}

void ConstraintDB::clear() {
    clocks_.clear();
    clock_groups_.clear();
    io_delays_.clear();
    path_delays_.clear();
    data_checks_.clear();
    path_groups_.clear();
    clock_latencies_.clear();
    clock_uncertainties_.clear();
    multicycle_paths_.clear();
    false_paths_.clear();
    disable_timings_.clear();
    case_analyses_.clear();
    set_loads_.clear();
    input_transitions_.clear();
    driving_cells_.clear();
    input_driver_order_ = 0;
    ocv_derate_ = {};
    aocv_points_.clear();
    design_rules_ = {};
}

void ConstraintDB::register_bus_port(const std::string& base_name, uint16_t width) {
    bus_port_widths_[base_name] = width;
}

std::vector<std::string> ConstraintDB::expand_port_name(const std::string& name) const {
    auto it = bus_port_widths_.find(name);
    if (it == bus_port_widths_.end()) return {name};
    std::vector<std::string> bits;
    bits.reserve(it->second);
    for (uint16_t b = 0; b < it->second; ++b) {
        bits.push_back(name + "[" + std::to_string(b) + "]");
    }
    return bits;
}

void ConstraintDB::materialize_port_collections(const std::vector<std::string>& ports) {
    const std::unordered_set<std::string> exact(ports.begin(),ports.end());
    auto matches=[](const std::string& pattern,const std::string& value) {
        size_t p=0,v=0,star=std::string::npos,retry=0;
        while (v<value.size()) {
            if (p<pattern.size() && (pattern[p]=='?' || pattern[p]==value[v])) {++p;++v;}
            else if (p<pattern.size() && pattern[p]=='*') {star=p++;retry=v;}
            else if (star!=std::string::npos) {p=star+1;v=++retry;}
            else return false;
        }
        while (p<pattern.size() && pattern[p]=='*') ++p;
        return p==pattern.size();
    };
    auto expand=[&](std::vector<std::string>& selectors) {
        std::vector<std::string> result;std::unordered_set<std::string> seen;
        for (const auto& selector:selectors) {
            bool found=false;
            if (!exact.count(selector) && selector.find_first_of("*?")!=std::string::npos)
                for (const auto& port:ports) if (matches(selector,port)) {
                    found=true;if (seen.insert(port).second) result.push_back(port);
                }
            // Never turn an unmatched nonempty selector into an empty list:
            // several SDC commands interpret an empty scope as all objects.
            if (!found && seen.insert(selector).second) result.push_back(selector);
        }
        selectors=std::move(result);
    };
    for (auto& delay:io_delays_) expand(delay.port_names);
    for (auto& transition:input_transitions_) expand(transition.port_names);
    for (auto& driver:driving_cells_) expand(driver.port_names);
}

} // namespace edacraft::core
