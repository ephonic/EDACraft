#include "time_engine/api_c.h"

#include <cstring>
#include <string.h>
#include <new>
#include <algorithm>
#include <limits>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>

#include "time_engine/engine.hh"

using namespace te;

// ────────────────────────────────────────────────────────────
// Helper: unwrap opaque pointer
// ────────────────────────────────────────────────────────────
static inline TimingEngine* unwrap(te_engine* e) {
    return reinterpret_cast<TimingEngine*>(e);
}

static char* duplicate_c_string(const std::string& value) {
    auto* copy = static_cast<char*>(std::malloc(value.size() + 1));
    if (!copy) return nullptr;
    std::memcpy(copy, value.c_str(), value.size() + 1);
    return copy;
}

void te_free_si_waveform(struct te_si_waveform* result) {
    if (!result) return;
    if (result->nodes) for (uint32_t i=0; i<result->num_nodes; ++i) {
        std::free(const_cast<char*>(result->nodes[i].pin));
        std::free(result->nodes[i].baseline_voltage);
        std::free(result->nodes[i].voltage);
    }
    std::free(const_cast<char*>(result->victim_net));
    std::free(const_cast<char*>(result->model));
    std::free(result->time_ns); std::free(result->nodes); std::free(result);
}

int te_solve_si_waveforms(te_engine* eng, const char* victim,
    const struct te_si_aggressor* aggressors, uint32_t count,
    const struct te_si_waveform_options* options, struct te_si_waveform** result,
    char* error, uint32_t error_capacity) {
    if (result) *result = nullptr;
    if (error && error_capacity) error[0] = 0;
    te_si_waveform* copy = nullptr;
    try {
        if (!eng || !victim || !result || (count && !aggressors))
            throw std::runtime_error("Invalid SI arguments");
        TimingEngine::SiWaveformOptions opt;
        if (options) {
            opt.victim_rise = options->victim_rise != 0;
            opt.quiet_victim = options->quiet_victim != 0;
            opt.respect_timing_windows = options->respect_timing_windows != 0;
            opt.victim_resistance_ohm = options->victim_resistance_ohm;
            opt.step_ns = options->step_ns; opt.max_steps = options->max_steps;
        }
        std::vector<TimingEngine::SiAggressor> selected;
        for (uint32_t i=0; i<count; ++i) {
            if (!aggressors[i].net) throw std::runtime_error("Missing SI aggressor name");
            selected.push_back({aggressors[i].net, aggressors[i].rise != 0,
                aggressors[i].offset_ns, aggressors[i].driver_resistance_ohm});
        }
        const auto wave = unwrap(eng)->solve_si_waveforms(victim, selected, opt);
        auto allocate = [](size_t size, size_t element) {
            auto* data = std::calloc(size,element);
            if (!data && size) throw std::bad_alloc();
            return data;
        };
        auto string = [](const std::string& value) {
            auto* data = duplicate_c_string(value);
            if (!data) throw std::bad_alloc();
            return data;
        };
        auto samples = [&](const std::vector<float>& values) {
            auto* data = static_cast<float*>(allocate(values.size(),sizeof(float)));
            std::copy(values.begin(),values.end(),data); return data;
        };
        copy = static_cast<te_si_waveform*>(allocate(1,sizeof(te_si_waveform)));
        copy->victim_net = string(wave.victim_net); copy->model = string(wave.model);
        copy->active_aggressors = wave.active_aggressors;
        copy->num_samples = uint32_t(wave.time_ns.size()); copy->num_nodes = uint32_t(wave.nodes.size());
        copy->time_ns = samples(wave.time_ns);
        copy->nodes = static_cast<te_si_node_waveform*>(allocate(copy->num_nodes,sizeof(te_si_node_waveform)));
        for (uint32_t i=0; i<copy->num_nodes; ++i) {
            auto& out = copy->nodes[i]; const auto& in = wave.nodes[i];
            out.node = in.node; out.pin = string(in.pin);
            out.delay_delta_ns = in.delay_delta_ns; out.slew_delta_ns = in.slew_delta_ns;
            out.noise_peak_v = in.noise_peak_v; out.noise_width_ns = in.noise_width_ns;
            out.baseline_voltage = samples(in.baseline_voltage); out.voltage = samples(in.voltage);
        }
        *result = copy; return 0;
    } catch (const std::exception& e) {
        te_free_si_waveform(copy);
        if (error && error_capacity) {
            std::strncpy(error,e.what(),error_capacity-1); error[error_capacity-1]=0;
        }
        return -1;
    } catch (...) {
        te_free_si_waveform(copy); return -1;
    }
}

// ────────────────────────────────────────────────────────────
// Lifecycle
// ────────────────────────────────────────────────────────────

te_engine* te_engine_create(void) {
    try {
        return reinterpret_cast<te_engine*>(new TimingEngine());
    } catch (...) {
        return nullptr;
    }
}

void te_engine_destroy(te_engine* eng) {
    delete unwrap(eng);
}

// ────────────────────────────────────────────────────────────
// Configuration
// ────────────────────────────────────────────────────────────

void te_set_thread_count(te_engine* eng, int n) {
    if (!eng) return;
    unwrap(eng)->set_thread_count(n);
}

void te_set_pvt(te_engine* eng, float voltage, float temperature) {
    if (!eng) return;
    unwrap(eng)->set_pvt(voltage, temperature);
}

// ────────────────────────────────────────────────────────────
// Loading
// ────────────────────────────────────────────────────────────

void te_read_liberty(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->read_liberty(filepath);
    } catch (...) {
        // C API: swallow exceptions
    }
}

void te_read_verilog(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->read_verilog(filepath);
    } catch (...) {
    }
}

void te_read_spef(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->read_spef(filepath);
    } catch (...) {
    }
}

void te_read_sdc(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->read_sdc(filepath);
    } catch (...) {
    }
}

// ────────────────────────────────────────────────────────────
// AOCV derate
// ────────────────────────────────────────────────────────────

void te_set_aocv_derate(te_engine* eng, const struct te_aocv_point* points, int count) {
    if (!eng || !points || count <= 0) return;
    std::vector<te::TimingEngine::AocvPoint> cpp_points;
    cpp_points.reserve(count);
    for (int i = 0; i < count; ++i) {
        cpp_points.push_back({points[i].depth, points[i].late_derate, points[i].early_derate});
    }
    try {
        unwrap(eng)->set_aocv_derate(cpp_points);
    } catch (...) {
    }
}

// ────────────────────────────────────────────────────────────
// Linking & analysis
// ────────────────────────────────────────────────────────────

void te_link_design(te_engine* eng) {
    if (!eng) return;
    try {
        unwrap(eng)->link_design();
    } catch (...) {
    }
}

void te_update_timing(te_engine* eng) {
    if (!eng) return;
    try {
        unwrap(eng)->update_timing();
    } catch (...) {
    }
}

void te_update_incremental(te_engine* eng) {
    if (!eng) return;
    try {
        unwrap(eng)->update_incremental();
    } catch (...) {
    }
}

// ────────────────────────────────────────────────────────────
// Results
// ────────────────────────────────────────────────────────────

float te_get_arrival(te_engine* eng, te_pin_id pin, int rf, int mm) {
    if (!eng) return 0.0f;
    return unwrap(eng)->get_arrival(
        PinId{pin},
        static_cast<Transition>(rf),
        static_cast<MinMax>(mm));
}

float te_get_required(te_engine* eng, te_pin_id pin, int rf, int mm) {
    if (!eng) return 0.0f;
    return unwrap(eng)->get_required(
        PinId{pin},
        static_cast<Transition>(rf),
        static_cast<MinMax>(mm));
}

float te_get_slew(te_engine* eng, te_pin_id pin, int rf, int mm) {
    if (!eng) return 0.0f;
    return unwrap(eng)->get_slew(
        PinId{pin},
        static_cast<Transition>(rf),
        static_cast<MinMax>(mm));
}

float te_get_slack(te_engine* eng, te_pin_id pin, int rf, int mm) {
    if (!eng) return 0.0f;
    return unwrap(eng)->get_slack(
        PinId{pin},
        static_cast<Transition>(rf),
        static_cast<MinMax>(mm));
}

float te_worst_slack(te_engine* eng, int mm) {
    if (!eng) return 0.0f;
    return unwrap(eng)->worst_slack(static_cast<MinMax>(mm));
}

// ────────────────────────────────────────────────────────────
struct te_power_summary te_estimate_power(te_engine* eng, float frequency_hz, float activity) {
    struct te_power_summary result{};
    if (!eng) return result;
    try {
    const auto power = unwrap(eng)->estimate_power(frequency_hz, activity);
    result.leakage_w = power.leakage_w;
    result.internal_w = power.internal_w;
    result.switching_w = power.switching_w;
    result.total_w = power.total_w;
    result.frequency_hz = power.frequency_hz;
    result.activity = power.activity;
    } catch (...) {
        result.leakage_w=result.internal_w=result.switching_w=result.total_w=std::numeric_limits<float>::quiet_NaN();
    }
    return result;
}

int te_set_power_activity(te_engine* eng, const char* object, double rate, double probability,
    char* error, uint32_t capacity) {
    if (error && capacity) error[0]=0;
    try {
        if (!eng || !object) throw std::invalid_argument("Invalid power activity arguments");
        unwrap(eng)->set_power_activity(object,rate,probability); return 0;
    } catch (const std::exception& ex) {
        if (error && capacity) { std::strncpy(error,ex.what(),capacity-1); error[capacity-1]=0; }
        return -1;
    }
}
void te_clear_power_activity(te_engine* eng) { if (eng) unwrap(eng)->clear_power_activity(); }

int te_set_power_propagation_mode(te_engine* eng, const char* mode, char* error, uint32_t capacity) {
    if (error && capacity) error[0]=0;
    try {
        if (!eng || !mode) throw std::invalid_argument("Invalid power propagation arguments");
        unwrap(eng)->set_power_propagation_mode(mode);return 0;
    } catch (const std::exception& ex) {
        if (error && capacity) {std::strncpy(error,ex.what(),capacity-1);error[capacity-1]=0;}
        return -1;
    }
}

int te_set_power_internal_activity(te_engine* eng, const char* pin, const char* when,
    const char* related_pin, double rate, double ratio, char* error, uint32_t capacity) {
    if (error && capacity) error[0]=0;
    try {
        if (!eng || !pin || !when || !related_pin) throw std::invalid_argument("Invalid internal power activity arguments");
        unwrap(eng)->set_power_internal_activity(pin,when,related_pin,rate,ratio); return 0;
    } catch (const std::exception& ex) {
        if (error && capacity) { std::strncpy(error,ex.what(),capacity-1); error[capacity-1]=0; }
        return -1;
    }
}

struct te_si_summary te_analyze_si(te_engine* eng) {
    struct te_si_summary result{};
    if (!eng) return result;
    const auto si = unwrap(eng)->analyze_si();
    result.victim_nets = si.victim_nets;
    result.total_coupling_cap = si.total_coupling_cap;
    result.max_victim_coupling_cap = si.max_victim_coupling_cap;
    result.crosstalk_waveform_solver = si.crosstalk_waveform_solver ? 1 : 0;
    result.si_timing_applied = si.si_timing_applied ? 1 : 0;
    return result;
}

int te_get_timing_check_coverage(
    te_engine* eng, struct te_timing_check_coverage* records, int capacity) {
    if (!eng) return 0;
    const auto coverage = unwrap(eng)->timing_check_coverage();
    const int total = static_cast<int>(coverage.size());
    if (!records || capacity <= 0) return total;
    const int count = std::min(total, capacity);
    for (int i = 0; i < count; ++i) {
        const auto& src = coverage[static_cast<size_t>(i)];
        records[i].pin = src.pin.id;
        records[i].arc = src.arc;
        records[i].transition = static_cast<int>(src.transition);
        records[i].analysis = static_cast<int>(src.analysis);
        records[i].kind = static_cast<int>(src.kind);
        records[i].state = static_cast<int>(src.state);
    }
    return total;
}

// Path reporting
// ────────────────────────────────────────────────────────────

static int copy_path_reports(const std::vector<PathReport>& cpp_reports,
                             struct te_path_report** reports) {
    if (!reports) return 0;
    *reports = nullptr;
    te_path_report* reps = nullptr;
    int n = 0;
    try {
        if (cpp_reports.empty()) return 0;

        n = static_cast<int>(cpp_reports.size());
        reps = static_cast<te_path_report*>(std::malloc(sizeof(te_path_report) * n));
        if (!reps) return 0;
        std::memset(reps, 0, sizeof(te_path_report) * n);

        for (int i = 0; i < n; ++i) {
            const auto& src = cpp_reports[i];
            reps[i].slack = src.slack;
            reps[i].cppr = src.cppr;
            reps[i].path_based = src.path_based;
            reps[i].check_kind = static_cast<int>(src.check_kind);
            reps[i].path_group = src.path_group.empty() ? nullptr : duplicate_c_string(src.path_group);
            if (!src.path_group.empty() && !reps[i].path_group) {
                te_free_path_reports(reps, i + 1); return 0;
            }
            reps[i].check_related_name = src.check_related_name.empty()
                ? nullptr : duplicate_c_string(src.check_related_name);
            if (!src.check_related_name.empty() && !reps[i].check_related_name) {
                te_free_path_reports(reps, i + 1); return 0;
            }
            reps[i].check_endpoint_name = src.check_endpoint_name.empty()
                ? nullptr : duplicate_c_string(src.check_endpoint_name);
            if (!src.check_endpoint_name.empty() && !reps[i].check_endpoint_name) {
                te_free_path_reports(reps, i + 1); return 0;
            }
            reps[i].num_points = static_cast<int>(src.point_names.size());

            if (reps[i].num_points > 0) {
                reps[i].points = static_cast<te_path_point*>(
                    std::calloc(reps[i].num_points, sizeof(te_path_point)));
                if (!reps[i].points) {
                    te_free_path_reports(reps, i + 1);
                    return 0;
                }
                for (int j = 0; j < reps[i].num_points; ++j) {
                    reps[i].points[j].name = duplicate_c_string(src.point_names[j]);
                    if (!reps[i].points[j].name) { te_free_path_reports(reps, i + 1); return 0; }
                    reps[i].points[j].cell_name = src.cell_names[j].empty()
                        ? nullptr
                        : duplicate_c_string(src.cell_names[j]);
                    if (src.cell_names[j].empty() == false && !reps[i].points[j].cell_name) {
                        te_free_path_reports(reps, i + 1); return 0;
                    }
                    reps[i].points[j].delay = src.delays[j];
                    reps[i].points[j].arrival = src.arrivals[j];
                    reps[i].points[j].slew = src.slews[j];
                    reps[i].points[j].transition = duplicate_c_string(src.transitions[j]);
                    if (!reps[i].points[j].transition) { te_free_path_reports(reps, i + 1); return 0; }
                }
            }
        }
        *reports = reps;
        return n;
    } catch (...) {
        if (reps) te_free_path_reports(reps, n);
        return 0;
    }
}

int te_report_worst_paths(te_engine* eng, int mm, int count,
                          struct te_path_report** reports) {
    if (!eng || !reports) return 0;
    try {
        return copy_path_reports(
            unwrap(eng)->report_worst_paths(static_cast<MinMax>(mm), count), reports);
    } catch (...) {
        if (reports) *reports = nullptr;
        return 0;
    }
}

int te_report_check_paths(te_engine* eng, int mm, int count, int kind,
                          int balance_groups, struct te_path_report** reports) {
    if (!eng || !reports) return 0;
    try {
        return copy_path_reports(
            unwrap(eng)->report_check_paths(static_cast<MinMax>(mm), count,
                                            static_cast<TimingCheckKind>(kind),
                                            balance_groups != 0),
            reports);
    } catch (...) {
        if (reports) *reports = nullptr;
        return 0;
    }
}

void te_free_path_reports(struct te_path_report* reports, int count) {
    if (!reports) return;
    for (int i = 0; i < count; ++i) {
        std::free(const_cast<char*>(reports[i].path_group));
        std::free(const_cast<char*>(reports[i].check_related_name));
        std::free(const_cast<char*>(reports[i].check_endpoint_name));
        if (reports[i].points) {
            for (int j = 0; j < reports[i].num_points; ++j) {
                std::free(const_cast<char*>(reports[i].points[j].name));
                if (reports[i].points[j].cell_name)
                    std::free(const_cast<char*>(reports[i].points[j].cell_name));
                std::free(const_cast<char*>(reports[i].points[j].transition));
            }
            std::free(reports[i].points);
        }
    }
    std::free(reports);
}

int te_report_group_paths(te_engine* eng, int mm, int count, const char* group,
                          struct te_path_report** reports) {
    if (!reports) return 0;
    *reports = nullptr;
    if (!eng || !group) return 0;
    try {
        return copy_path_reports(unwrap(eng)->report_worst_paths(
            static_cast<MinMax>(mm), count, TimingCheckKind::Data, group), reports);
    } catch (...) { return 0; }
}

int te_report_pba_paths(te_engine* eng, int mm, int count, const char* group,
                       uint32_t limit, struct te_path_report** reports) {
    if (!reports) return 0;
    *reports = nullptr;
    if (!eng) return 0;
    try { return copy_path_reports(unwrap(eng)->report_pba_paths(
        static_cast<MinMax>(mm), count, group ? group : "", limit), reports); }
    catch (...) { return -1; }
}

int te_get_design_rule_limits(te_engine* eng, struct te_design_rule_limits* limits) {
    if (!eng || !limits) return 0;
    try {
        const auto rules = unwrap(eng)->design_rule_limits();
        limits->max_fanout = rules.max_fanout;
        limits->max_capacitance = rules.max_capacitance;
        limits->max_transition = rules.max_transition;
        return 1;
    } catch (...) {
        return 0;
    }
}

int te_report_design_rule_violations(te_engine* eng,
                                   struct te_design_rule_violation** violations) {
    if (!violations) return 0;
    *violations = nullptr;
    if (!eng) return 0;
    try {
        const auto records = unwrap(eng)->design_rule_violations();
        const int count = static_cast<int>(records.size());
        if (!count) return 0;
        auto* out = static_cast<te_design_rule_violation*>(
            std::calloc(count, sizeof(te_design_rule_violation)));
        if (!out) return 0;
        for (int i = 0; i < count; ++i) {
            out[i].rule = duplicate_c_string(records[i].rule);
            out[i].object = duplicate_c_string(records[i].object);
            out[i].limit = records[i].limit;
            out[i].value = records[i].value;
            if (!out[i].rule || !out[i].object) {
                te_free_design_rule_violations(out, count);
                return 0;
            }
        }
        *violations = out;
        return count;
    } catch (...) { return -1; }
}

void te_free_design_rule_violations(struct te_design_rule_violation* violations,
                                    int count) {
    if (!violations) return;
    for (int i = 0; i < count; ++i) {
        std::free(const_cast<char*>(violations[i].rule));
        std::free(const_cast<char*>(violations[i].object));
    }
    std::free(violations);
}

// ────────────────────────────────────────────────────────────
// Dirty tracking
// ────────────────────────────────────────────────────────────

void te_mark_net_dirty(te_engine* eng, te_net_id net) {
    if (!eng) return;
    unwrap(eng)->mark_net_dirty(NetId{net});
}

void te_mark_pin_dirty(te_engine* eng, te_pin_id pin) {
    if (!eng) return;
    unwrap(eng)->mark_pin_dirty(PinId{pin});
}

void te_mark_all_dirty(te_engine* eng) {
    if (!eng) return;
    unwrap(eng)->mark_all_dirty();
}

// ────────────────────────────────────────────────────────────
// Lookup
// ────────────────────────────────────────────────────────────

te_net_id te_find_net(te_engine* eng, const char* name) {
    if (!eng || !name) return UINT32_MAX;
    auto opt = unwrap(eng)->find_net(name);
    return opt ? opt->id : UINT32_MAX;
}

te_pin_id te_find_pin(te_engine* eng, const char* name) {
    if (!eng || !name) return UINT32_MAX;
    auto opt = unwrap(eng)->find_pin(name);
    return opt ? opt->id : UINT32_MAX;
}

// ────────────────────────────────────────────────────────────
// Parasitics
// ────────────────────────────────────────────────────────────

float te_get_net_cap(te_engine* eng, te_net_id net) {
    if (!eng) return 0.0f;
    return unwrap(eng)->get_net_cap(NetId{net});
}

// ────────────────────────────────────────────────────────────
// Save / load
// ────────────────────────────────────────────────────────────

void te_save_state(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->save_state(filepath);
    } catch (...) {
    }
}

void te_load_state(te_engine* eng, const char* filepath) {
    if (!eng || !filepath) return;
    try {
        unwrap(eng)->load_state(filepath);
    } catch (...) {
    }
}

// ────────────────────────────────────────────────────────────
// Synthesis integration
// ────────────────────────────────────────────────────────────

void te_update_timing_incremental(
    te_engine* eng,
    const te_net_id* changed_nets, int net_count,
    const te_pin_id* changed_pins, int pin_count
) {
    if (!eng) return;
    try {
        std::vector<NetId> nets;
        nets.reserve(net_count);
        for (int i = 0; i < net_count; ++i) nets.push_back(NetId{changed_nets[i]});
        std::vector<PinId> pins;
        pins.reserve(pin_count);
        for (int i = 0; i < pin_count; ++i) pins.push_back(PinId{changed_pins[i]});
        unwrap(eng)->update_timing_incremental(nets, pins);
    } catch (...) {
    }
}

struct te_timing_view te_get_timing_view(te_engine* eng) {
    struct te_timing_view view{};
    if (!eng) return view;
    try {
        auto cpp_view = unwrap(eng)->get_timing_view();
        view.vertex_count = cpp_view.vertex_count;
        view.arrival = cpp_view.arrival;
        view.slew = cpp_view.slew;
        view.required = cpp_view.required;
        view.pred_max = cpp_view.pred_max;
        view.pred_min = cpp_view.pred_min;
    } catch (...) {
    }
    return view;
}
