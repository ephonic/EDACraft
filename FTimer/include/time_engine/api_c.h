#ifndef TIME_ENGINE_API_C_H
#define TIME_ENGINE_API_C_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct te_engine te_engine;
typedef uint32_t te_net_id;
typedef uint32_t te_pin_id;
typedef uint32_t te_instance_id;
typedef uint32_t te_cell_id;

/* Path report point (C-struct mirror of PathReport::point_names[i]) */
struct te_path_point {
    const char* name;       /* pin name (owned by caller; must free via te_free_path_reports) */
    const char* cell_name;  /* cell name (may be NULL for top-level ports) */
    float delay;            /* delay to this point from previous */
    float arrival;          /* cumulative arrival time */
    float slew;             /* slew at this point */
    const char* transition; /* "rise" or "fall" */
};

/* Path report (C-struct mirror of PathReport) */
struct te_path_report {
    float slack;
    float cppr;
    int check_kind;          /* te::TimingCheckKind numeric value */
    struct te_path_point* points;
    int num_points;
    const char* check_related_name; /* source/related pin, or NULL */
    const char* check_endpoint_name; /* checked endpoint pin, or NULL */
    const char* path_group; /* explicit SDC group, or NULL */
    int path_based;
};

/* AOCV derate point */
struct te_aocv_point {
    int depth;
    float late_derate;
    float early_derate;
};

struct te_power_summary {
    float leakage_w;
    float internal_w;
    float switching_w;
    float total_w;
    float frequency_hz;
    float activity;
};

struct te_design_rule_limits {
    float max_fanout;
    float max_capacitance;
    float max_transition;
};

struct te_design_rule_violation {
    const char* rule;
    const char* object;
    float limit;
    float value;
};

struct te_si_summary {
    uint32_t victim_nets;
    float total_coupling_cap;
    float max_victim_coupling_cap;
    int crosstalk_waveform_solver;
    int si_timing_applied;
};

/* Standalone linear Thevenin SI analysis (ns, ohm, volt).
 * This result does not replace the GBA/bridge timing snapshot. */
struct te_si_aggressor {
    const char* net;
    int rise;
    float offset_ns;
    float driver_resistance_ohm; /* >0: explicit R; <=0: fixed SDC port waveform,
                                  otherwise estimate resistance from slew/load */
};
struct te_si_waveform_options {
    int victim_rise;
    int quiet_victim;
    int respect_timing_windows;
    float victim_resistance_ohm;
    float step_ns;
    uint32_t max_steps;
};
struct te_si_node_waveform {
    uint32_t node;
    const char* pin;
    float delay_delta_ns, slew_delta_ns, noise_peak_v, noise_width_ns;
    float* baseline_voltage; /* num_samples entries */
    float* voltage;
};
struct te_si_waveform {
    const char* victim_net;
    const char* model;
    uint32_t active_aggressors, num_samples, num_nodes;
    float* time_ns;
    struct te_si_node_waveform* nodes;
};

struct te_timing_check_coverage {
    uint32_t pin;
    uint32_t arc;
    int transition; /* 0 rise, 1 fall */
    int analysis;   /* 0 min, 1 max */
    int kind;       /* te::TimingCheckKind numeric value */
    int state;      /* te::CheckCoverageState numeric value */
};

/* Lifecycle */
te_engine* te_engine_create(void);
void te_engine_destroy(te_engine* eng);

/* Configuration */
void te_set_thread_count(te_engine* eng, int n);
void te_set_pvt(te_engine* eng, float voltage, float temperature);

/* Loading */
void te_read_liberty(te_engine* eng, const char* filepath);
void te_read_verilog(te_engine* eng, const char* filepath);
void te_read_spef(te_engine* eng, const char* filepath);
void te_read_sdc(te_engine* eng, const char* filepath);

/* AOCV derate */
void te_set_aocv_derate(te_engine* eng, const struct te_aocv_point* points, int count);

/* Linking & analysis */
void te_link_design(te_engine* eng);
void te_update_timing(te_engine* eng);
void te_update_incremental(te_engine* eng);

/* Results */
float te_get_arrival(te_engine* eng, te_pin_id pin, int rf, int mm);
float te_get_required(te_engine* eng, te_pin_id pin, int rf, int mm);
float te_get_slew(te_engine* eng, te_pin_id pin, int rf, int mm);
float te_get_slack(te_engine* eng, te_pin_id pin, int rf, int mm);
float te_worst_slack(te_engine* eng, int mm);
struct te_power_summary te_estimate_power(te_engine* eng, float frequency_hz, float activity);
/* Activity is both-edge transitions/second; probability is P(1). 0=success. */
int te_set_power_activity(te_engine* eng, const char* object, double toggle_rate_hz,
    double static_probability, char* error, uint32_t error_capacity);
void te_clear_power_activity(te_engine* eng);
/* mode: "clocked" (default) or "independent". 0=success, -1=invalid. */
int te_set_power_propagation_mode(te_engine* eng, const char* mode,
    char* error, uint32_t error_capacity);
int te_set_power_internal_activity(te_engine* eng, const char* pin, const char* when,
    const char* related_pin, double toggle_rate_hz, double rise_ratio,
    char* error, uint32_t error_capacity);
struct te_si_summary te_analyze_si(te_engine* eng);
/* Returns 0 on success, -1 on failure; optional error buffer is NUL terminated.
 * NULL options selects C++ defaults. Free the result with te_free_si_waveform. */
int te_solve_si_waveforms(te_engine* eng, const char* victim,
    const struct te_si_aggressor* aggressors, uint32_t count,
    const struct te_si_waveform_options* options, struct te_si_waveform** result,
    char* error, uint32_t error_capacity);
void te_free_si_waveform(struct te_si_waveform* result);
/* Returns the total record count; fills at most capacity entries. */
int te_get_timing_check_coverage(
    te_engine* eng, struct te_timing_check_coverage* records, int capacity);

/* Path reporting (caller must free *reports via te_free_path_reports) */
int te_report_worst_paths(te_engine* eng, int mm, int count,
                          struct te_path_report** reports);
/* Report evaluated timing-check paths.  kind uses te::TimingCheckKind values
 * (Any is 0).  When balance_groups is nonzero, setup/hold/check groups
 * are interleaved similarly to the text report. */
int te_report_check_paths(te_engine* eng, int mm, int count, int kind,
                          int balance_groups, struct te_path_report** reports);
void te_free_path_reports(struct te_path_report* reports, int count);
int te_report_group_paths(te_engine* eng, int mm, int count, const char* group,
                          struct te_path_report** reports);
int te_report_pba_paths(te_engine* eng, int mm, int count, const char* group,
                       uint32_t path_label_limit, struct te_path_report** reports);
int te_get_design_rule_limits(te_engine* eng, struct te_design_rule_limits* limits);
/* Returned strings/array are owned by ftimer; release with the matching free. */
/* Returns count, or -1 on analysis failure, including incomplete legacy
 * .ftlib electrical metadata. The output is null on failure. */
int te_report_design_rule_violations(te_engine* eng,
                                   struct te_design_rule_violation** violations);
void te_free_design_rule_violations(struct te_design_rule_violation* violations,
                                    int count);

/* Dirty tracking */
void te_mark_net_dirty(te_engine* eng, te_net_id net);
void te_mark_pin_dirty(te_engine* eng, te_pin_id pin);
void te_mark_all_dirty(te_engine* eng);

/* Net / pin lookup by name (returns UINT32_MAX if not found) */
te_net_id te_find_net(te_engine* eng, const char* name);
te_pin_id te_find_pin(te_engine* eng, const char* name);

/* Parasitics access */
float te_get_net_cap(te_engine* eng, te_net_id net);

/* Save / load timing state */
void te_save_state(te_engine* eng, const char* filepath);
void te_load_state(te_engine* eng, const char* filepath);

/* ── Synthesis integration ──────────────────────────────── */

/* TimingView: zero-copy read-only access to timing results */
struct te_timing_view {
    uint32_t vertex_count;
    const float* arrival;      /* [vertex_count * 4] flat */
    const float* slew;         /* [vertex_count * 4] flat */
    const float* required;     /* [vertex_count * 4] flat */
    const uint32_t* pred_max;  /* [vertex_count * 4] per mm_rf */
    const uint32_t* pred_min;  /* [vertex_count * 4] per mm_rf */
};

/* Batch incremental analysis */
void te_update_timing_incremental(
    te_engine* eng,
    const te_net_id* changed_nets, int net_count,
    const te_pin_id* changed_pins, int pin_count
);

/* Get zero-copy timing view (valid until next update) */
struct te_timing_view te_get_timing_view(te_engine* eng);

/* Vertex index helper: vid = pin_id * 2 + (rf ? 1 : 0) */
static inline uint32_t te_vid(te_pin_id pin, int rf) {
    return pin * 2 + (rf ? 1 : 0);
}

#ifdef __cplusplus
}
#endif

#endif
