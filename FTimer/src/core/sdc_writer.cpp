#include "edacraft/core/sdc_writer.hpp"
#include <fstream>
#include <sstream>
#include <iomanip>
#include <limits>
#include <functional>
#include <stdexcept>
#include <unordered_map>
#include <algorithm>

namespace edacraft::core {

static std::string clock_word(const std::string& name) {
    return name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./:-") == std::string::npos
        ? name : "{" + name + "}";
}

static void write_ports(std::ostringstream& oss, const std::vector<std::string>& ports) {
    if (ports.size() == 1) {
        oss << "[get_ports " << clock_word(ports[0]) << "]";
    } else if (ports.size() > 1) {
        oss << "[get_ports {";
        for (size_t i = 0; i < ports.size(); ++i) {
            if (i > 0) oss << " ";
            oss << ports[i];
        }
        oss << "}]";
    }
}

static void write_pins(std::ostringstream& oss, const std::string& flag,
                        const std::vector<std::string>& pins) {
    if (pins.empty()) return;
    oss << " " << flag << " ";
    if (pins.size() == 1) {
        oss << "[get_pins " << pins[0] << "]";
    } else {
        oss << "[get_pins {";
        for (size_t i = 0; i < pins.size(); ++i) {
            if (i > 0) oss << " ";
            oss << pins[i];
        }
        oss << "}]";
    }
}

static void write_clocks(std::ostringstream& oss, const std::vector<std::string>& clocks) {
    if (clocks.size() == 1) {
        oss << "[get_clocks " << clocks[0] << "]";
    } else if (clocks.size() > 1) {
        oss << "[get_clocks {";
        for (size_t i = 0; i < clocks.size(); ++i) {
            if (i > 0) oss << " ";
            oss << clocks[i];
        }
        oss << "}]";
    }
}

static void write_path_selector(std::ostringstream& oss, const std::string& flag,
    const std::vector<std::string>& pins, const std::vector<std::string>& clocks) {
    if (clocks.empty()) { write_pins(oss,flag,pins); return; }
    if (!pins.empty()) throw std::runtime_error("Mixed pin/clock exception selector is unsupported");
    oss << " " << flag << " "; write_clocks(oss,clocks);
}

std::string write_sdc(const ConstraintDB& constraints) {
    std::ostringstream oss;
    oss << std::setprecision(std::numeric_limits<float>::max_digits10);

    // Emit masters before descendants even for a DB populated through C++.
    auto prepared = constraints;
    std::string error;
    if (!prepared.resolve_generated_clocks(error)) throw std::runtime_error(error);
    std::unordered_map<std::string, size_t> clock_index;
    for (size_t i = 0; i < prepared.clocks().size(); ++i) clock_index[prepared.clocks()[i].name] = i;
    std::vector<size_t> order;
    std::vector<bool> emitted(prepared.clocks().size(), false);
    std::function<void(size_t)> emit = [&](size_t index) {
        if (emitted[index]) return;
        const auto& clk = prepared.clocks()[index];
        if (clk.generated) emit(clock_index.at(clk.generated->resolved_master_clock));
        emitted[index] = true; order.push_back(index);
    };
    for (size_t i = 0; i < prepared.clocks().size(); ++i) emit(i);
    for (const auto index : order) {
        const auto& clk = prepared.clocks()[index];
        if (clk.generated) {
            const auto& def = *clk.generated;
            oss << "create_generated_clock -name " << clock_word(clk.name)
                << " -source [" << (def.source_is_pin ? "get_pins" : "get_ports") << " {" << def.source << "}]";
            if (!def.master_clock.empty()) oss << " -master_clock " << clock_word(def.master_clock);
            if (def.divide_by && !def.combinational) oss << " -divide_by " << def.divide_by;
            if (def.multiply_by) oss << " -multiply_by " << def.multiply_by;
            if (def.combinational) oss << " -combinational";
            if (def.duty_cycle != 0) oss << " -duty_cycle " << def.duty_cycle;
            if (def.invert) oss << " -invert";
            if (!def.edges.empty()) {
                oss << " -edges {";
                for (size_t i = 0; i < def.edges.size(); ++i) oss << (i ? " " : "") << def.edges[i];
                oss << "}";
            }
            if (!def.edge_shifts_ns.empty()) {
                oss << " -edge_shift {";
                for (size_t i = 0; i < def.edge_shifts_ns.size(); ++i) oss << (i ? " " : "") << def.edge_shifts_ns[i];
                oss << "}";
            }
            oss << " [" << (clk.source_is_pin ? "get_pins" : "get_ports") << " {" << clk.source_port << "}]\n";
            continue;
        }
        oss << "create_clock -name " << clock_word(clk.name)
            << " -period " << clk.period_ns;
        if (clk.waveform_explicit) {
            oss << " -waveform {" << clk.rise_edge_ns << " " << clk.fall_edge_ns << "}";
        }
        if (!clk.source_port.empty()) {
            oss << " [" << (clk.source_is_pin ? "get_pins" : "get_ports") << " {" << clk.source_port << "}]";
        }
        oss << "\n";
    }

    std::vector<std::string> propagated_clocks;
    for (const auto& clk : prepared.clocks()) {
        if (clk.propagated) propagated_clocks.push_back(clk.name);
    }
    if (!propagated_clocks.empty()) {
        oss << "set_propagated_clock ";
        write_clocks(oss, propagated_clocks);
        oss << "\n";
    }

    // Clock waveform (if set separately)
    // (already handled in create_clock)
    for (const auto& clk : prepared.clocks()) {
        if (clk.transition_ns >= 0.0f) {
            oss << "set_clock_transition " << clk.transition_ns
                << " " << clock_word(clk.name) << "\n";
        }
    }

    // Clock groups
    for (const auto& group_def : constraints.clock_groups()) {
        oss << "set_clock_groups";
        switch (group_def.mode) {
            case ClockGroupDef::Mode::Asynchronous:
                oss << " -asynchronous";
                break;
            case ClockGroupDef::Mode::LogicallyExclusive:
                oss << " -logically_exclusive";
                break;
            case ClockGroupDef::Mode::PhysicallyExclusive:
                oss << " -physically_exclusive";
                break;
        }
        for (const auto& group : group_def.groups) {
            if (group.empty()) continue;
            oss << " -group ";
            write_clocks(oss, group);
        }
        oss << "\n";
    }

    // Clock latency
    for (const auto& cl : constraints.clock_latencies()) {
        oss << "set_clock_latency " << cl.latency_ns;
        if (!cl.clock_name.empty()) oss << " " << cl.clock_name;
        if (!cl.pin_names.empty()) {
            oss << " ";
            write_ports(oss, cl.pin_names);
        }
        oss << "\n";
    }

    // Clock uncertainty
    for (const auto& cu : constraints.clock_uncertainties()) {
        if (cu.setup_uncertainty_ns != 0.0f) {
            oss << "set_clock_uncertainty -setup " << cu.setup_uncertainty_ns;
            if (!cu.clock_name.empty()) oss << " -from " << cu.clock_name;
            oss << "\n";
        }
        if (cu.hold_uncertainty_ns != 0.0f) {
            oss << "set_clock_uncertainty -hold " << cu.hold_uncertainty_ns;
            if (!cu.clock_name.empty()) oss << " -from " << cu.clock_name;
            oss << "\n";
        }
    }

    // I/O delays
    for (const auto& d : constraints.io_delays()) {
        oss << (d.is_input ? "set_input_delay" : "set_output_delay");
        if (!d.clock_name.empty()) oss << " -clock " << d.clock_name;
        oss << (d.is_max ? " -max" : " -min");
        oss << (d.clock_edge == Transition::Fall ? " -fall" : " -rise");
        oss << " " << d.delay_ns;
        oss << " ";
        write_ports(oss, d.port_names);
        oss << "\n";
    }

    // Path delays
    for (const auto& pd : constraints.path_delays()) {
        oss << (pd.is_max ? "set_max_delay" : "set_min_delay");
        oss << " " << pd.delay_ns;
        if (pd.ignore_clock_latency) oss << " -ignore_clock_latency";
        write_path_selector(oss, "-from", pd.from_pins, pd.from_clocks);
        write_pins(oss, "-through", pd.through_pins);
        for (const auto& stage : pd.through_stages) write_pins(oss, "-through", stage);
        write_path_selector(oss, "-to", pd.to_pins, pd.to_clocks);
        oss << "\n";
    }

    for (const auto& check : constraints.data_checks()) {
        oss << "set_data_check " << check.delay_ns
            << (check.is_setup ? " -setup" : " -hold");
        const auto selector = [](uint8_t mask, const char* any,
                                 const char* rise, const char* fall) {
            return mask == 1 ? rise : mask == 2 ? fall : any;
        };
        write_pins(oss, selector(check.from_transitions, "-from", "-rise_from", "-fall_from"), check.from_pins);
        write_pins(oss, selector(check.to_transitions, "-to", "-rise_to", "-fall_to"), check.to_pins);
        oss << "\n";
    }

    for (const auto& group : constraints.path_groups()) {
        oss << "group_path -name " << clock_word(group.name);
        oss << " -weight " << group.weight;
        auto option = [](const char* base, uint8_t mask) {
            return std::string("-") + (mask == 1 ? "rise_" : mask == 2 ? "fall_" : "") + base;
        };
        write_pins(oss, option("from", group.from_transitions), group.from_pins);
        if (!group.from_clocks.empty()) { oss << " " << option("from", group.from_transitions) << " "; write_clocks(oss, group.from_clocks); }
        write_pins(oss, option("through", group.through_transitions), group.through_pins);
        for (size_t i = 0; i < group.through_stages.size(); ++i)
            write_pins(oss, option("through", i < group.through_stage_transitions.size() ? group.through_stage_transitions[i] : 3), group.through_stages[i]);
        write_pins(oss, option("to", group.to_transitions), group.to_pins);
        if (!group.to_clocks.empty()) { oss << " " << option("to", group.to_transitions) << " "; write_clocks(oss, group.to_clocks); }
        oss << "\n";
    }

    // Set load
    for (const auto& sl : constraints.set_loads()) {
        oss << "set_load " << sl.capacitance_pf;
        oss << " ";
        write_ports(oss, sl.pin_names);
        oss << "\n";
    }

    // Preserve last-command precedence between explicit slew and cell drive.
    std::vector<std::pair<uint64_t, std::string>> input_drivers;
    for (const auto& it : constraints.input_transitions()) {
        std::ostringstream line;
        line << std::setprecision(std::numeric_limits<float>::max_digits10);
        line << "set_input_transition";
        if (it.rise && !it.fall) line << " -rise";
        if (it.fall && !it.rise) line << " -fall";
        if (it.min && !it.max) line << " -min";
        if (it.max && !it.min) line << " -max";
        line << " " << it.transition_ns << " ";
        write_ports(line, it.port_names);
        input_drivers.emplace_back(it.order, line.str());
    }
    for (const auto& driver : constraints.driving_cells()) {
        std::ostringstream line;
        line << std::setprecision(std::numeric_limits<float>::max_digits10);
        line << "set_driving_cell -lib_cell " << clock_word(driver.cell);
        if (!driver.library.empty()) line << " -library " << clock_word(driver.library);
        if (!driver.pin.empty()) line << " -pin " << clock_word(driver.pin);
        if (!driver.from_pin.empty()) line << " -from_pin " << clock_word(driver.from_pin);
        if (driver.rise && !driver.fall) line << " -rise";
        if (driver.fall && !driver.rise) line << " -fall";
        if (driver.min && !driver.max) line << " -min";
        if (driver.max && !driver.min) line << " -max";
        if (driver.no_design_rule) line << " -no_design_rule";
        if (driver.dont_scale) line << " -dont_scale";
        line << " -input_transition_rise " << driver.input_transition_rise_ns;
        line << " -input_transition_fall " << driver.input_transition_fall_ns << " ";
        write_ports(line, driver.port_names);
        input_drivers.emplace_back(driver.order, line.str());
    }
    std::stable_sort(input_drivers.begin(), input_drivers.end(),
        [](const auto& a, const auto& b) { return a.first < b.first; });
    for (const auto& driver : input_drivers) oss << driver.second << "\n";

    // Multicycle paths
    for (const auto& mcp : constraints.multicycle_paths()) {
        oss << "set_multicycle_path " << (mcp.is_hold ? "-hold " : "-setup ")
            << (mcp.is_hold ? mcp.hold_cycles : mcp.setup_cycles)
            << (mcp.use_start ? " -start" : " -end");
        write_path_selector(oss, "-from", mcp.from_pins, mcp.from_clocks);
        write_path_selector(oss, "-to", mcp.to_pins, mcp.to_clocks);
        oss << "\n";
        if (!mcp.is_hold && mcp.hold_cycles > 0) {
            oss << "set_multicycle_path -hold " << mcp.hold_cycles;
            write_path_selector(oss, "-from", mcp.from_pins, mcp.from_clocks);
            write_path_selector(oss, "-to", mcp.to_pins, mcp.to_clocks);
            oss << "\n";
        }
    }

    // False paths
    for (const auto& fp : constraints.false_paths()) {
        // A programmatic exception disabled for both analyses is a no-op.
        if (!fp.setup && !fp.hold) continue;
        oss << "set_false_path";
        if (fp.setup && !fp.hold) oss << " -setup";
        if (fp.hold && !fp.setup) oss << " -hold";
        auto selector = [](const char* any, const char* rise, const char* fall, uint8_t mask) {
            return mask == 1 ? rise : mask == 2 ? fall : any;
        };
        write_path_selector(oss, selector("-from", "-rise_from", "-fall_from", fp.from_transitions), fp.from_pins, fp.from_clocks);
        write_pins(oss, selector("-through", "-rise_through", "-fall_through", fp.through_transitions), fp.through_pins);
        for (size_t i = 0; i < fp.through_stages.size(); ++i)
            write_pins(oss, selector("-through", "-rise_through", "-fall_through",
                i < fp.through_stage_transitions.size() ? fp.through_stage_transitions[i] : 3), fp.through_stages[i]);
        write_path_selector(oss, selector("-to", "-rise_to", "-fall_to", fp.to_transitions), fp.to_pins, fp.to_clocks);
        if (fp.to_pins.empty() && fp.to_clocks.empty() && fp.to_transitions != 3)
            oss << (fp.to_transitions == 1 ? " -rise" : " -fall");
        oss << "\n";
    }

    // Disable timing
    for (const auto& dt : constraints.disable_timings()) {
        oss << "set_disable_timing";
        if (!dt.from_pin.empty()) oss << " -from " << dt.from_pin;
        if (!dt.to_pin.empty()) oss << " -to " << dt.to_pin;
        oss << "\n";
    }

    // Case analysis
    for (const auto& ca : constraints.case_analyses()) {
        oss << "set_case_analysis ";
        switch (ca.value) {
            case CaseAnalysisDef::Zero: oss << "0"; break;
            case CaseAnalysisDef::One:  oss << "1"; break;
            case CaseAnalysisDef::Rise: oss << "rising"; break;
            case CaseAnalysisDef::Fall: oss << "falling"; break;
        }
        oss << " " << ca.pin_name << "\n";
    }

    // OCV derate
    const auto& ocv = constraints.ocv_derate();
    if (ocv.early_data != 1.0f || ocv.late_data != 1.0f) {
        oss << "set_timing_derate -early " << ocv.early_data
            << " -late " << ocv.late_data << " -data\n";
    }
    if (ocv.early_clock != 1.0f || ocv.late_clock != 1.0f) {
        oss << "set_timing_derate -early " << ocv.early_clock
            << " -late " << ocv.late_clock << " -clock\n";
    }

    // Design rules
    const auto& dr = constraints.design_rules();
    if (dr.max_fanout >= 0.0f) {
        oss << "set_max_fanout " << dr.max_fanout << "\n";
    }
    if (dr.max_capacitance >= 0.0f) {
        oss << "set_max_capacitance " << dr.max_capacitance << "\n";
    }
    if (dr.max_transition >= 0.0f) {
        oss << "set_max_transition " << dr.max_transition << "\n";
    }

    return oss.str();
}

bool write_sdc_file(const std::string& filepath, const ConstraintDB& constraints) {
    std::ofstream ofs(filepath);
    if (!ofs.is_open()) return false;
    ofs << write_sdc(constraints);
    return true;
}

} // namespace edacraft::core
