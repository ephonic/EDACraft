#include <algorithm>
#include <iomanip>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <chrono>

#include "time_engine/engine.hh"

using hires_clock = std::chrono::high_resolution_clock;
static double elapsed_ms(hires_clock::time_point t0) {
    return std::chrono::duration<double, std::milli>(hires_clock::now() - t0).count();
}

using namespace te;

static void print_usage(const char* prog) {
    std::cout << "TimeEngine v0.1.1 - Timing Analysis Engine\n"
              << "Usage: " << prog << " [options]\n"
              << "Options:\n"
              << "  -lib <file>       Liberty library file (.lib)\n"
              << "  -verilog <file>   Gate-level netlist (.v)\n"
              << "  -top <name>       Explicit top module for multi-root netlists\n"
              << "  -spef <file>      Parasitics file (.spef)\n"
              << "  -sdc <file>       SDC constraints (.sdc)\n"
              << "  -threads <n>      Thread count (default: 1)\n"
              << "  -voltage <V>      Operating voltage\n"
              << "  -temperature <T>  Operating temperature (C)\n"
              << "  -report <n>       Report top N worst setup (max) paths\n"
              << "  -report_reg2reg <n>  Report top N register-start setup paths\n"
              << "  -report_min <n>   Report top N worst hold (min) paths\n"
              << "  -report_check <n> Report top N max timing-check paths\n"
              << "  -report_check_min <n> Report top N min timing-check paths\n"
              << "  -group <name>     Restrict path reports to an explicit SDC group\n"
              << "  -pba_mode <mode>  none | exhaustive (route-specific recalculation)\n"
              << "  -pba_limit <n>    Exhaustive path-label budget (default 1000000)\n"
              << "  -check_coverage   Report timing-check coverage records\n"
              << "  -query_pin <name> Print timing values for a full pin name\n"
              << "  -power <Hz>       Estimate leakage/internal/switching power\n"
              << "  -activity <a>     Both-edge toggles/cycle for -power (default 0.1)\n"
              << "  -power_activity <net|pin> <Hz> <P1> (repeatable)\n"
              << "  -power_activity_file <tsv>  net/pin, Hz, P1 (three tab-separated fields)\n"
              << "  -power_internal_activity <pin> <when> <related_pin> <Hz> <rise_ratio>\n"
              << "  -power_internal_activity_file <tsv>  same five tab-separated fields\n"
              << "  -power_detail     Per-cell/net power and annotation coverage\n"
              << "  -power_propagation <clocked|independent> (default clocked)\n"
              << "  -si               Report SPEF coupling inventory\n"
              << "  -si_detail        Report normalized victim/aggressor coupling pairs\n"
              << "  -si_victim <net>  Solve extracted coupled RC waveforms\n"
              << "  -si_aggressor <net> <rise|fall> <offset_ns> <R_ohm> (repeatable)\n"
              << "  -si_quiet -si_fall -si_no_windows -si_step <ns> -si_victim_r <ohm>\n"
              << "  -si_waveform_file <csv>  Export baseline and coupled voltages\n"
              << "  -design_rules     Report resolved SDC design-rule limits\n"
              << "  -design_rule_violations  Report actual design-rule violations\n"
              << "  -report_format <fmt>  Report format: default | opensta\n"
              << "  -verbose          Print parser/link diagnostics\n"
              << "  -dump_pins        Dump all pin arrivals/slews\n"
              << "  -dump_pins_min    Dump all min-analysis pin arrivals/slews\n"
              << "  -dump_clock_pins  Dump clock events and physical data paths at clock inputs\n"
              << "  -help             Print this help\n";
}

static const char* timing_check_kind_name(TimingCheckKind kind) {
    switch (kind) {
    case TimingCheckKind::Data: return "data";
    case TimingCheckKind::Setup: return "setup";
    case TimingCheckKind::Hold: return "hold";
    case TimingCheckKind::Recovery: return "recovery";
    case TimingCheckKind::Removal: return "removal";
    case TimingCheckKind::OutputDelay: return "output_delay";
    case TimingCheckKind::Any: return "any";
    case TimingCheckKind::None: return "none";
    }
    return "none";
}

static const char* transition_name(Transition rf) {
    return rf == Transition::Rise ? "rise" : "fall";
}

static const char* minmax_name(MinMax mm) {
    return mm == MinMax::Min ? "min" : "max";
}

static void print_path_default(const PathReport& path, int path_idx) {
    std::cout << "  Path " << path_idx + 1 << ": slack = " << path.slack << "\n";
    if (!path.path_group.empty()) std::cout << "    Path Group: " << path.path_group << "\n";
    std::cout << "    " << std::setw(10) << "Arrival"
              << std::setw(10) << "Delay"
              << "  Point" << "\n";
    for (size_t j = 0; j < path.point_names.size(); ++j) {
        float arrival = path.arrivals[j];
        float delay = path.delays[j];
        std::cout << "    " << std::fixed << std::setprecision(4)
                  << std::setw(10) << arrival
                  << std::setw(10) << delay
                  << "  " << path.point_names[j];
        if (j == 0) std::cout << " (startpoint)";
        if (j == path.point_names.size() - 1) std::cout << " (endpoint)";
        std::cout << "\n";
    }
    if (path.check) {
        if (!path.check_related_name.empty())
            std::cout << "    DataCheckFrom: " << path.check_related_name << "\n";
        if (!path.check_endpoint_name.empty())
            std::cout << "    DataCheckTo: " << path.check_endpoint_name << "\n";
    }
}

static void print_path_opensta(const PathReport& path, int path_idx, const char* path_type) {
    (void)path_idx;
    std::string startpoint = path.point_names.empty() ? "" : path.point_names.front();
    std::string endpoint = path.point_names.empty() ? "" : path.point_names.back();
    std::string startpoint_type = "input port";
    std::string endpoint_type = "output port";

    // Infer point types from cell names
    if (!path.cell_names.empty() && !path.cell_names.front().empty()) {
        startpoint_type = path.cell_names.front();
    }
    if (!path.cell_names.empty() && path.cell_names.back().empty() && endpoint.find("/") == std::string::npos) {
        endpoint_type = "output port";
    } else if (!path.cell_names.empty() && !path.cell_names.back().empty()) {
        endpoint_type = path.cell_names.back();
    }

    std::cout << "Startpoint: " << startpoint << " (" << startpoint_type << ")\n";
    std::cout << "Endpoint: " << endpoint << " (" << endpoint_type << ")\n";
    const char* path_group = !path.path_group.empty() ? path.path_group.c_str() :
        path.check ? timing_check_kind_name(path.check_kind) : "(none)";
    std::cout << "Path Group: " << path_group << "\n";
    std::cout << "Path Analysis: " << (path.path_based ? "pba_exhaustive" : "gba") << "\n";
    std::cout << "Clock Pessimism Removal: " << path.cppr << "\n";
    std::cout << "Path Type: " << path_type << "\n\n";

    std::cout << "      Delay        Time        Slew   Description\n";
    std::cout << "-----------------------------------------------------------------\n";

    for (size_t j = 0; j < path.point_names.size(); ++j) {
        float delay = path.delays[j];
        float arrival = path.arrivals[j];
        float slew = (j < path.slews.size()) ? path.slews[j] : 0.0f;
        const std::string& point = path.point_names[j];
        const std::string& cell = (j < path.cell_names.size()) ? path.cell_names[j] : "";

        std::string desc = point;
        if (!cell.empty()) {
            desc += " (" + cell + ")";
        } else if (j == 0) {
            desc += " (input port)";
        } else if (j == path.point_names.size() - 1) {
            desc += " (output port)";
        }

        // Show incremental delay, cumulative arrival, and slew
        std::cout << "   " << std::fixed << std::setprecision(4)
                  << std::setw(8) << delay
                  << std::setw(12) << arrival
                  << std::setw(12) << slew
                  << "   " << desc << "\n";
    }

    // Summary section
    // Setup: slack = required - arrival  →  required = arrival + slack
    // Hold:   slack = arrival - required  →  required = arrival - slack
    bool is_hold = (path_type == std::string_view("min"));
    float required = is_hold
        ? (path.arrivals.back() - path.slack)
        : (path.arrivals.back() + path.slack);
    std::cout << "-----------------------------------------------------------------\n";
    std::cout << "              " << std::fixed << std::setprecision(4)
              << std::setw(12) << required
              << "   data required time\n";
    float arr = path.arrivals.back();
    std::cout << "             " << std::fixed << std::setprecision(4)
              << std::setw(11) << -arr
              << "   data arrival time\n";
    std::cout << "-----------------------------------------------------------------\n";
    std::cout << "              " << std::fixed << std::setprecision(4)
              << std::setw(12) << path.slack
              << "   slack (" << (path.slack >= 0.0f ? "MET" : "VIOLATED") << ")\n";
    if (path.check) {
        if (!path.check_related_name.empty())
            std::cout << "DataCheckFrom: " << path.check_related_name << "\n";
        if (!path.check_endpoint_name.empty())
            std::cout << "DataCheckTo: " << path.check_endpoint_name << "\n";
    }
}

int main(int argc, char* argv[]) {
    std::vector<std::string> lib_files, verilog_files, spef_files, sdc_files;
    int threads = 1;
    float voltage = 1.0f, temperature = 25.0f;
    int report_count = 0;
    int report_reg2reg_count = 0;
    int report_min_count = 0;
    int report_check_count = 0;
    int report_check_min_count = 0;
    std::vector<std::string> query_pins;
    std::string report_format = "default";
    std::string report_group;
    std::string pba_mode = "none";
    size_t pba_limit = 1000000;
    std::string top_design;
    bool dump_pins = false;
    bool dump_pins_min = false;
    bool dump_clock_pins = false;
    bool verbose = false;
    float power_frequency = 0.0f;
    float power_activity = 0.1f;
    bool power_report = false;
    bool power_detail = false;
    std::string power_propagation="clocked";
    bool voltage_explicit = false;
    struct PowerAnnotation { std::string object; double rate, probability; };
    std::vector<PowerAnnotation> power_annotations;
    struct InternalPowerAnnotation { std::string pin, when, related; double rate, ratio; };
    std::vector<InternalPowerAnnotation> internal_power_annotations;
    bool si_report = false;
    bool si_detail_report = false;
    std::string si_victim, si_waveform_file;
    TimingEngine::SiWaveformOptions si_options;
    std::vector<TimingEngine::SiAggressor> si_aggressors;
    bool check_coverage = false;
    bool design_rule_report = false;
    bool design_rule_violation_report = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto next = [&]() -> std::string {
            if (i + 1 < argc) return argv[++i];
            throw std::runtime_error("Missing argument for " + arg);
        };

        if (arg == "-help" || arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "-lib") {
            lib_files.push_back(next());
        } else if (arg == "-verilog") {
            verilog_files.push_back(next());
        } else if (arg == "-top") {
            top_design = next();
        } else if (arg == "-spef") {
            spef_files.push_back(next());
        } else if (arg == "-sdc") {
            sdc_files.push_back(next());
        } else if (arg == "-threads") {
            threads = std::stoi(next());
        } else if (arg == "-voltage") {
            voltage = std::stof(next());
            voltage_explicit = true;
        } else if (arg == "-temperature") {
            temperature = std::stof(next());
        } else if (arg == "-report") {
            report_count = std::stoi(next());
        } else if (arg == "-report_reg2reg") {
            report_reg2reg_count = std::stoi(next());
        } else if (arg == "-report_min") {
            report_min_count = std::stoi(next());
        } else if (arg == "-report_check") {
            report_check_count = std::stoi(next());
        } else if (arg == "-report_check_min") {
            report_check_min_count = std::stoi(next());
        } else if (arg == "-group") {
            report_group = next();
        } else if (arg == "-pba_mode") {
            pba_mode = next();
            if (pba_mode != "none" && pba_mode != "exhaustive")
                throw std::runtime_error("-pba_mode must be none or exhaustive");
        } else if (arg == "-pba_limit") {
            pba_limit = std::stoull(next());
        } else if (arg == "-si_victim") {
            si_victim = next();
        } else if (arg == "-si_aggressor") {
            TimingEngine::SiAggressor aggr;
            aggr.net = next();
            const auto direction = next();
            if (direction != "rise" && direction != "fall") throw std::runtime_error("Invalid SI aggressor direction");
            aggr.rise = direction == "rise"; aggr.offset_ns = std::stof(next());
            aggr.driver_resistance_ohm = std::stof(next()); si_aggressors.push_back(aggr);
        } else if (arg == "-si_quiet") {
            si_options.quiet_victim = true;
        } else if (arg == "-si_fall") {
            si_options.victim_rise = false;
        } else if (arg == "-si_no_windows") {
            si_options.respect_timing_windows = false;
        } else if (arg == "-si_step") {
            si_options.step_ns = std::stof(next());
        } else if (arg == "-si_victim_r") {
            si_options.victim_resistance_ohm = std::stof(next());
        } else if (arg == "-si_waveform_file") {
            si_waveform_file = next();
        } else if (arg == "-query_pin") {
            query_pins.push_back(next());
        } else if (arg == "-power") {
            power_frequency = std::stof(next());
            power_report = true;
        } else if (arg == "-activity") {
            power_activity = std::stof(next());
        } else if (arg == "-power_detail") {
            power_detail = true; power_report = true;
        } else if (arg == "-power_propagation") {
            power_propagation=next();
        } else if (arg == "-power_activity") {
            PowerAnnotation item;
            item.object=next(); item.rate=std::stod(next()); item.probability=std::stod(next());
            power_annotations.push_back(std::move(item));
        } else if (arg == "-power_activity_file") {
            const auto filename=next(); std::ifstream file(filename);
            if (!file) throw std::runtime_error("Cannot read power activity file: "+filename);
            std::string line;
            while (std::getline(file,line)) {
                if (line.empty()) continue;
                std::istringstream row(line); std::string object;
                std::getline(row,object,'\t'); PowerAnnotation item; item.object=object;
                if (!(row>>item.rate>>item.probability)) throw std::runtime_error("Malformed power activity row");
                row>>std::ws;
                if (!row.eof()) throw std::runtime_error("Extra fields in power activity row");
                power_annotations.push_back(std::move(item));
            }
        } else if (arg == "-power_internal_activity") {
            InternalPowerAnnotation item;
            item.pin=next(); item.when=next(); item.related=next();
            item.rate=std::stod(next()); item.ratio=std::stod(next());
            internal_power_annotations.push_back(std::move(item));
        } else if (arg == "-power_internal_activity_file") {
            const auto filename=next(); std::ifstream file(filename);
            if (!file) throw std::runtime_error("Cannot read internal power activity file: "+filename);
            std::string line;
            while (std::getline(file,line)) {
                if (line.empty()) continue;
                InternalPowerAnnotation item; std::istringstream row(line);
                if (!std::getline(row,item.pin,'\t') || !std::getline(row,item.when,'\t') ||
                    !std::getline(row,item.related,'\t') || !(row>>item.rate>>item.ratio))
                    throw std::runtime_error("Malformed internal power activity row");
                row>>std::ws;
                if (!row.eof()) throw std::runtime_error("Extra fields in internal power activity row");
                internal_power_annotations.push_back(std::move(item));
            }
        } else if (arg == "-si") {
            si_report = true;
        } else if (arg == "-si_detail") {
            si_report = true;
            si_detail_report = true;
        } else if (arg == "-check_coverage") {
            check_coverage = true;
        } else if (arg == "-design_rules") {
            design_rule_report = true;
        } else if (arg == "-design_rule_violations") {
            design_rule_violation_report = true;
        } else if (arg == "-report_format") {
            report_format = next();
        } else if (arg == "-verbose") {
            verbose = true;
        } else if (arg == "-dump_pins") {
            dump_pins = true;
        } else if (arg == "-dump_pins_min") {
            dump_pins_min = true;
        } else if (arg == "-dump_clock_pins") {
            dump_clock_pins = true;
        } else {
            std::cerr << "Unknown option: " << arg << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    if (lib_files.empty() && verilog_files.empty()) {
        std::cerr << "Error: at least one -lib or -verilog file required\n";
        print_usage(argv[0]);
        return 1;
    }

    try {
        TimingEngine engine;
        engine.set_verbose(verbose);
        engine.set_thread_count(threads);
        if (voltage_explicit) engine.set_pvt(voltage, temperature);
        else engine.set_temperature(temperature);
        engine.set_top_design(top_design);

        auto t0 = hires_clock::now();
        for (auto& f : lib_files) {
            auto t = hires_clock::now();
            engine.read_liberty(f);
            std::cout << "[TIME] Liberty " << f << ": " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        for (auto& f : verilog_files) {
            auto t = hires_clock::now();
            engine.read_verilog(f);
            std::cout << "[TIME] Verilog " << f << ": " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        for (auto& f : spef_files) {
            auto t = hires_clock::now();
            engine.read_spef(f);
            std::cout << "[TIME] SPEF " << f << ": " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        for (auto& f : sdc_files) {
            auto t = hires_clock::now();
            engine.read_sdc(f);
            std::cout << "[TIME] SDC " << f << ": " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        {
            auto t = hires_clock::now();
            engine.link_design();
            std::cout << "[TIME] Link: " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        {
            auto t = hires_clock::now();
            engine.update_timing();
            std::cout << "[TIME] Update timing: " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        if (report_count > 0 || report_reg2reg_count > 0 ||
            report_min_count > 0 || report_check_count > 0 ||
            report_check_min_count > 0) {
            auto t = hires_clock::now();
            if (report_count > 0)
                engine.report_worst_paths(MinMax::Max, report_count, TimingCheckKind::Data, report_group);
            if (report_reg2reg_count > 0) {
                const int scan_count = std::max(4096, report_reg2reg_count * 128);
                engine.report_worst_paths(MinMax::Max, scan_count, TimingCheckKind::Data, report_group);
            }
            if (report_min_count > 0)
                engine.report_worst_paths(MinMax::Min, report_min_count, TimingCheckKind::Data, report_group);
            if (report_check_count > 0)
                engine.report_check_paths(MinMax::Max, report_check_count,
                                          TimingCheckKind::Any, true, report_group);
            if (report_check_min_count > 0)
                engine.report_check_paths(MinMax::Min, report_check_min_count,
                                          TimingCheckKind::Any, true, report_group);
            std::cout << "[TIME] Report paths: " << elapsed_ms(t) << " ms\n" << std::flush;
        }

        std::cout << "[TIME] Total: " << elapsed_ms(t0) << " ms\n";
        std::cout << "Timing analysis complete.\n";
        std::cout.flush();

        if (power_report) {
            engine.set_power_propagation_mode(power_propagation);
            for (const auto& item : power_annotations)
                engine.set_power_activity(item.object,item.rate,item.probability);
            for (const auto& item : internal_power_annotations)
                engine.set_power_internal_activity(item.pin,item.when,item.related,item.rate,item.ratio);
            const auto detail = engine.estimate_power_detail(power_frequency, power_activity);
            const auto& power = detail.summary;
            std::cout << std::setprecision(9)
                      << "POWER_SUMMARY frequency_hz=" << power.frequency_hz
                      << " activity=" << power.activity
                      << " leakage_w=" << power.leakage_w
                      << " internal_w=" << power.internal_w
                      << " switching_w=" << power.switching_w
                      << " total_w=" << power.total_w << "\n";
            if (power_detail) {
                std::cout << "POWER_COVERAGE annotated=" << detail.annotated_nets
                    << " propagated=" << detail.propagated_nets << " default=" << detail.default_nets
                    << " constant=" << detail.constant_nets << " unsupported=" << detail.unsupported_expressions
                    << " internal_annotated=" << detail.internal_annotated_groups << "\n";
                std::cout << "POWER_MODEL activity=both_edge_toggles independence="
                    << (detail.activity_samples ? "root_nets" : "per_net") << " clock_nets="
                    << detail.clock_nets << " glitch=0 sample_hz=" << detail.activity_sample_hz
                    << " propagation=" << (detail.activity_sample_hz>0 ? "clocked" : "boolean_derivative")
                    << " activity_samples=" << detail.activity_samples << "\n";
                for (const auto& cell : detail.cells)
                    std::cout << "POWER_CELL name=" << cell.name << " leakage_w=" << cell.leakage_w
                        << " internal_w=" << cell.internal_w << " switching_w=" << cell.switching_w
                        << " total_w=" << cell.total_w << "\n";
                for (const auto& net : detail.nets)
                    std::cout << "POWER_NET name=" << net.name << " source=" << net.source
                        << " toggle_rate_hz=" << net.toggle_rate_hz << " probability=" << net.static_probability
                        << " capacitance_f=" << net.capacitance_f << " switching_w=" << net.switching_w
                        << " included_in_total=" << net.included_in_total << "\n";
            }
        }
        if (si_report) {
            const auto si = engine.analyze_si();
            if (si_detail_report) {
                for (const auto& item : engine.analyze_si_detail()) {
                    std::cout << std::setprecision(9)
                              << "SI_COUPLING victim=" << item.victim_net
                              << " aggressor=" << item.aggressor_net
                              << " cap=" << item.coupling_cap
                              << " victim_total=" << item.victim_total_coupling_cap
                              << " ratio=" << item.coupling_ratio << "\n";
                }
            }
            std::cout << std::setprecision(9)
                      << "SI_SUMMARY victim_nets=" << si.victim_nets
                      << " total_coupling_cap=" << si.total_coupling_cap
                      << " max_victim_coupling_cap=" << si.max_victim_coupling_cap
                      << " crosstalk_waveform_solver="
                      << (si.crosstalk_waveform_solver ? 1 : 0)
                      << " si_timing_applied=" << (si.si_timing_applied ? 1 : 0) << "\n";
        }
        if (check_coverage) {
            const auto coverage = engine.timing_check_coverage();
            size_t evaluated = 0;
            size_t excluded = 0;
            size_t invalid = 0;
            for (const auto& item : coverage) {
                const bool coverage_valid = check_coverage_valid(item.state);
                if (item.state == CheckCoverageState::Evaluated) ++evaluated;
                else if (coverage_valid) ++excluded;
                else ++invalid;
                std::cout << "TIMING_CHECK_COVERAGE pin=";
                if (valid(item.pin)) std::cout << engine.pin_name(item.pin);
                else std::cout << "<unknown>";
                std::cout << " arc=" << item.arc
                          << " transition=" << transition_name(item.transition)
                          << " analysis=" << minmax_name(item.analysis)
                          << " kind=" << timing_check_kind_name(item.kind)
                          << " state=" << check_coverage_name(item.state) << "\n";
            }
            std::cout << "TIMING_CHECK_SUMMARY total=" << coverage.size()
                      << " evaluated=" << evaluated
                      << " excluded=" << excluded
                      << " invalid=" << invalid << "\n";
        }
        if (design_rule_report) {
            const auto rules = engine.design_rule_limits();
            std::cout << std::setprecision(9)
                      << "DESIGN_RULES max_fanout=" << rules.max_fanout
                      << " max_capacitance=" << rules.max_capacitance
                      << " max_transition=" << rules.max_transition << "\n";
        }
        if (design_rule_violation_report) {
            for (const auto& item : engine.design_rule_violations()) {
                std::cout << std::setprecision(9)
                          << "DESIGN_RULE_VIOLATION rule=" << item.rule
                          << " object=" << item.object
                          << " limit=" << item.limit
                          << " value=" << item.value << "\n";
            }
        }

        auto dump_pin_values = [&](MinMax analysis) {
            std::cout << std::setprecision(9);
            auto tv = engine.get_timing_view();
            std::cout << (analysis == MinMax::Max ? "\n=== PIN DUMP ===\n" : "\n=== PIN DUMP MIN ===\n");
            std::cout << "pin_name,rise_arrival,fall_arrival,rise_slew,fall_slew\n";
            for (uint32_t pid = 0; pid < engine.pin_count(); ++pid) {
                PinId pin{pid};
                std::string name;
                auto inst_name = engine.pin_instance_name(pin);
                auto local_name = engine.pin_name(pin);
                if (!inst_name.empty()) {
                    name = std::string(inst_name) + "/" + std::string(local_name);
                } else {
                    name = std::string(local_name);
                }
                uint32_t vid_r = pid * 2 + static_cast<uint32_t>(Transition::Rise);
                uint32_t vid_f = pid * 2 + static_cast<uint32_t>(Transition::Fall);
                float r_arr = tv.get_arrival(vid_r, analysis, Transition::Rise);
                float f_arr = tv.get_arrival(vid_f, analysis, Transition::Fall);
                float r_slew = tv.get_slew(vid_r, analysis, Transition::Rise);
                float f_slew = tv.get_slew(vid_f, analysis, Transition::Fall);
                std::cout << name << "," << r_arr << "," << f_arr << "," << r_slew << "," << f_slew << "\n";
            }
        };
        if (dump_pins) dump_pin_values(MinMax::Max);
        if (dump_pins_min) dump_pin_values(MinMax::Min);

        if (dump_clock_pins) {
            std::cout << std::setprecision(9)
                      << "\n=== CLOCK PIN DUMP (ns; data arrival includes launch phase) ===\n"
                      << "pin_name,analysis,transition,clock_arrival,clock_slew,data_path_arrival,data_path_slew\n";
            for (uint32_t pid = 0; pid < engine.pin_count(); ++pid) {
                const PinId pin{pid};
                for (auto mm : {MinMax::Min, MinMax::Max}) {
                    for (auto rf : {Transition::Rise, Transition::Fall}) {
                        const auto timing = engine.get_clock_pin_timing(pin, rf, mm);
                        if (!timing) continue;
                        const auto instance = engine.pin_instance_name(pin);
                        if (!instance.empty()) std::cout << instance << '/';
                        std::cout << engine.pin_name(pin) << ','
                                  << (mm == MinMax::Max ? "max" : "min") << ','
                                  << (rf == Transition::Rise ? "rise" : "fall") << ','
                                  << timing->clock_arrival << ',' << timing->clock_slew << ','
                                  << timing->data_path_arrival << ',' << timing->data_path_slew << '\n';
                    }
                }
            }
        }

        for (const auto& name : query_pins) {
            std::cout << std::setprecision(9);
            auto pin = engine.find_pin(name);
            if (!pin) {
                std::cout << "QUERY_PIN name=" << name << " found=0\n";
                continue;
            }
            std::cout << "QUERY_PIN name=" << name << " found=1";
            for (auto mm : {MinMax::Min, MinMax::Max}) {
                for (auto rf : {Transition::Rise, Transition::Fall}) {
                    const char* mm_name = mm == MinMax::Max ? "max" : "min";
                    const char* rf_name = rf == Transition::Rise ? "rise" : "fall";
                    std::cout << ' ' << mm_name << '_' << rf_name
                              << "_arrival=" << engine.get_arrival(*pin, rf, mm)
                              << ' ' << mm_name << '_' << rf_name
                              << "_required=" << engine.get_required(*pin, rf, mm)
                              << ' ' << mm_name << '_' << rf_name
                              << "_slack=" << engine.get_slack(*pin, rf, mm);
                    std::cout << ' ' << mm_name << '_' << rf_name
                              << "_slew=" << engine.get_slew(*pin, rf, mm);
                    if (const auto timing = engine.get_clock_pin_timing(*pin, rf, mm)) {
                        std::cout << ' ' << mm_name << '_' << rf_name
                                  << "_clock_arrival=" << timing->clock_arrival
                                  << ' ' << mm_name << '_' << rf_name
                                  << "_data_path_arrival=" << timing->data_path_arrival
                                  << ' ' << mm_name << '_' << rf_name
                                  << "_data_path_slew=" << timing->data_path_slew;
                    }
                }
            }
            std::cout << "\n";
        }

        if (!si_victim.empty()) {
            const auto solved = engine.solve_si_waveforms(si_victim, si_aggressors, si_options);
            std::cout << std::setprecision(9) << "SI_WAVEFORM victim=" << solved.victim_net
                      << " model=" << solved.model << " active_aggressors=" << solved.active_aggressors
                      << " samples=" << solved.time_ns.size() << "\n";
            for (const auto& node : solved.nodes)
                std::cout << "SI_NODE node=" << node.node << " pin=" << (node.pin.empty() ? "-" : node.pin)
                          << " delay_delta_ns=" << node.delay_delta_ns << " slew_delta_ns=" << node.slew_delta_ns
                          << " noise_peak_v=" << node.noise_peak_v << " noise_width_ns=" << node.noise_width_ns << "\n";
            if (!si_waveform_file.empty()) {
                std::ofstream file(si_waveform_file);
                if (!file) throw std::runtime_error("Cannot open SI waveform CSV");
                file << "time_ns";
                for (const auto& node : solved.nodes) file << ",node" << node.node << "_baseline_v,node" << node.node << "_coupled_v";
                file << "\n" << std::setprecision(9);
                for (size_t k=0;k<solved.time_ns.size();++k) {
                    file << solved.time_ns[k];
                    for (const auto& node : solved.nodes) file << ',' << node.baseline_voltage[k] << ',' << node.voltage[k];
                    file << "\n";
                }
                if (!file) throw std::runtime_error("Cannot write SI waveform CSV");
            }
        }

        if (report_count > 0) {
            auto paths = pba_mode == "exhaustive" ? engine.report_pba_paths(MinMax::Max, report_count, report_group, pba_limit) :
                engine.report_worst_paths(MinMax::Max, report_count, TimingCheckKind::Data, report_group);
            if (report_format == "opensta") {
                for (size_t i = 0; i < paths.size(); ++i) {
                    if (i > 0) std::cout << "\n";
                    print_path_opensta(paths[i], static_cast<int>(i), "max");
                }
            } else {
                std::cout << "\nWorst " << report_count << " paths (max):\n";
                for (size_t i = 0; i < paths.size(); ++i) {
                    print_path_default(paths[i], static_cast<int>(i));
                }
            }
        }
        if (report_reg2reg_count > 0) {
            const int scan_count = std::max(4096, report_reg2reg_count * 128);
            auto paths = pba_mode == "exhaustive" ? engine.report_pba_paths(MinMax::Max, scan_count, report_group, pba_limit) :
                engine.report_worst_paths(MinMax::Max, scan_count, TimingCheckKind::Data, report_group);
            std::cout << "\nWorst " << report_reg2reg_count
                      << " register-start paths (max):\n";
            int emitted = 0;
            for (const auto& path : paths) {
                if (path.cell_names.empty() || path.cell_names.front().empty()) {
                    continue;
                }
                if (report_format == "opensta") {
                    if (emitted > 0) std::cout << "\n";
                    print_path_opensta(path, emitted, "max");
                } else {
                    print_path_default(path, emitted);
                }
                if (++emitted >= report_reg2reg_count) break;
            }
        }
        if (report_min_count > 0) {
            auto paths = pba_mode == "exhaustive" ? engine.report_pba_paths(MinMax::Min, report_min_count, report_group, pba_limit) :
                engine.report_worst_paths(MinMax::Min, report_min_count, TimingCheckKind::Data, report_group);
            if (report_format == "opensta") {
                for (size_t i = 0; i < paths.size(); ++i) {
                    if (i > 0) std::cout << "\n";
                    print_path_opensta(paths[i], static_cast<int>(i), "min");
                }
            } else {
                std::cout << "\nWorst " << report_min_count << " paths (min):\n";
                for (size_t i = 0; i < paths.size(); ++i) {
                    print_path_default(paths[i], static_cast<int>(i));
                }
            }
        }

        auto print_check_reports = [&](MinMax mm, int count) {
            if (count <= 0) return;
            const auto paths = pba_mode == "exhaustive" ? engine.report_pba_paths(mm, count, report_group, pba_limit, TimingCheckKind::Any) :
                engine.report_check_paths(mm, count, TimingCheckKind::Any, true, report_group);
            std::cout << "\nTiming-check paths (" << minmax_name(mm) << "):\n";
            int emitted = 0;
            for (const auto& path : paths) {
                if (report_format == "opensta")
                    print_path_opensta(path, emitted, minmax_name(mm));
                else
                    print_path_default(path, emitted);
                std::cout << "TimingCheck: " << timing_check_kind_name(path.check_kind) << "\n";
                if (++emitted >= count) break;
            }
        };
        print_check_reports(MinMax::Max, report_check_count);
        print_check_reports(MinMax::Min, report_check_min_count);

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
