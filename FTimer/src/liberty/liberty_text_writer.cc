// Adapted from /home/yangfan/c906/t12/db_api.cc, writer snapshot 2026-10-25.
// This writer serializes the ftimer model, not unretained source Liberty syntax.
#include "time_engine/db_api.h"
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <set>
#include <sstream>
#include <stdexcept>
namespace edacraft::core::dbio {
namespace ec = edacraft::core;
namespace {
namespace writer {

std::string fn(float v, int prec = std::numeric_limits<float>::max_digits10) {
    if (!std::isfinite(v)) throw std::runtime_error("nonfinite Liberty value");
    std::ostringstream out; out.imbue(std::locale::classic());
    out << std::setprecision(prec) << v; return out.str();
}

std::string sv(const StringPool& pool, uint32_t id) {
    if (id == UINT32_MAX) return "";
    if (id >= pool.size()) throw std::runtime_error("invalid Liberty string ID");
    std::string out;
    for (char c : pool.view(id)) {
        if (c == '\\' || c == '"') out += '\\';
        if (c == '\n') out += "\\n";
        else if (c == '\t') out += "\\t";
        else if (static_cast<unsigned char>(c) < 32) throw std::runtime_error("control character in Liberty string");
        else out += c;
    }
    return out;
}

const char* sense_str(ec::LibertyTimingSense s) {
    switch (s) {
        case ec::LibertyTimingSense::PositiveUnate: return "positive_unate";
        case ec::LibertyTimingSense::NegativeUnate: return "negative_unate";
        case ec::LibertyTimingSense::NonUnate: return "non_unate";
        case ec::LibertyTimingSense::None: return "";
        default: throw std::runtime_error("unsupported timing sense");
    }
}

const char* type_str(ec::LibertyTimingType t) {
    switch (t) {
        case ec::LibertyTimingType::Combinational: return "combinational";
        case ec::LibertyTimingType::RisingEdge: return "rising_edge";
        case ec::LibertyTimingType::FallingEdge: return "falling_edge";
        case ec::LibertyTimingType::Preset: return "preset";
        case ec::LibertyTimingType::Clear: return "clear";
        case ec::LibertyTimingType::SetupRising: return "setup_rising";
        case ec::LibertyTimingType::SetupFalling: return "setup_falling";
        case ec::LibertyTimingType::HoldRising: return "hold_rising";
        case ec::LibertyTimingType::HoldFalling: return "hold_falling";
        case ec::LibertyTimingType::RecoveryRising: return "recovery_rising";
        case ec::LibertyTimingType::RecoveryFalling: return "recovery_falling";
        case ec::LibertyTimingType::RemovalRising: return "removal_rising";
        case ec::LibertyTimingType::RemovalFalling: return "removal_falling";
        default: throw std::runtime_error("unsupported timing type");
    }
}

const char* dir_str(ec::PortDirection d) {
    switch (d) {
        case ec::PortDirection::Input: return "input";
        case ec::PortDirection::Output: return "output";
        case ec::PortDirection::Inout: return "inout";
        default: return "internal";
    }
}

void attr(std::ostream& out, const StringPool& pool, const char* name, uint32_t id) {
    if (id != UINT32_MAX) out << "      " << name << " : \"" << sv(pool,id) << "\";\n";
}

template<class T> void receiver(std::ostream& out, const T& data, const char* indent);

// Write an NLDM 2-D table in Liberty syntax
void write_table(std::ostream& o, const char* name,
                 const ec::NldmTable& t, const char* indent) {
    if (!t.rows && !t.cols && t.values.empty() && t.axis1.empty() && t.axis2.empty()) return;
    if (!t.rows || !t.cols || t.axis1.size()!=t.rows || t.axis2.size()!=t.cols ||
        t.rows > t.values.size()/t.cols || t.rows*t.cols!=t.values.size())
        throw std::runtime_error("inconsistent Liberty table shape");
    bool is_constraint = std::strstr(name, "constraint") != nullptr;
    o << indent << name << " ("
      << (is_constraint ? "constraint_template" : (std::strstr(name,"power") ? "power_template" : "delay_template"))
      << ") {\n";
    o << indent << "    index_1 (\"";
    for (size_t i = 0; i < t.axis1.size(); ++i)
        o << (i ? ", " : "") << fn(t.axis1[i]);
    o << "\");\n";
    o << indent << "    index_2 (\"";
    for (size_t i = 0; i < t.axis2.size(); ++i)
        o << (i ? ", " : "") << fn(t.axis2[i]);
    o << "\");\n";
    o << indent << "    values ( \\\n";
    for (size_t r = 0; r < t.rows; ++r) {
        o << indent << "        \"";
        for (size_t c = 0; c < t.cols; ++c)
            o << (c ? ", " : "") << fn(t.values[r * t.cols + c]);
        o << (r + 1 < t.rows ? "\", \\\n" : "\" \\\n");
    }
    o << indent << "    );\n";
    o << indent << "}\n";
}

// Write a CCS output_current table
void write_ccs(std::ostream& o, const char* name,
               const ec::CsmOutputCurrentTable& t, const char* indent) {
    if (t.empty() && !t.nslew && !t.ncap) return;
    if (!t.nslew || !t.ncap || t.input_slews.size()!=t.nslew || t.load_caps.size()!=t.ncap ||
        size_t(t.nslew)*t.ncap!=t.waveforms.size()) throw std::runtime_error("inconsistent CCS shape");
    if (!t.corner_delays.empty() || !t.corner_slews.empty())
        throw std::runtime_error("derived CCS corners have no Liberty text representation");
    o << indent << name << " (ccs_template) {\n";
    // unique slews and caps
    std::set<float> slews(t.input_slews.begin(), t.input_slews.end());
    std::set<float> caps(t.load_caps.begin(), t.load_caps.end());
    if (slews.size()!=t.nslew || caps.size()!=t.ncap)
        throw std::runtime_error("duplicate CCS axis entries");
    for (uint32_t si=0; si<t.nslew; ++si) {
        for (uint32_t ci=0; ci<t.ncap; ++ci) {
            const float slew=t.input_slews[si], cap=t.load_caps[ci];
            const auto* w = &t.waveforms[static_cast<size_t>(si)*t.ncap+ci];
            if (!w || w->time_points.empty() || w->time_points.size()!=w->current.size())
                throw std::runtime_error("incomplete CCS waveform");
            o << indent << "    vector (ccs_template) {\n";
            o << indent << "        reference_time : " << fn(w->reference_time)
              << ";\n";
            o << indent << "        index_1 (\"" << fn(slew) << "\");\n";
            o << indent << "        index_2 (\"" << fn(cap) << "\");\n";
            o << indent << "        index_3 (\"";
            for (size_t i = 0; i < w->time_points.size(); ++i)
                o << (i ? ", " : "") << fn(w->time_points[i]);
            o << "\");\n";
            o << indent << "        values ( \\\n";
            o << indent << "            \"";
            for (size_t i = 0; i < w->current.size(); ++i)
                o << (i ? ", " : "") << fn(w->current[i]);
            o << char(34) << " " << char(92) << "\n";
            o << indent << "        );\n";
            o << indent << "    }\n";
        }
    }
    o << indent << "}\n";
}

template<class T> void receiver(std::ostream& out, const T& data, const char* indent) {
    write_table(out,"receiver_capacitance1_rise",data.receiver_capacitance1_rise,indent);
    write_table(out,"receiver_capacitance1_fall",data.receiver_capacitance1_fall,indent);
    write_table(out,"receiver_capacitance2_rise",data.receiver_capacitance2_rise,indent);
    write_table(out,"receiver_capacitance2_fall",data.receiver_capacitance2_fall,indent);
}

void miller(std::ostream& out, float rise, float fall) {
    if (rise!=0 || fall!=0)
        throw std::runtime_error("CCSN stage ownership is not retained for text export");
}

} // namespace writer
} // namespace

static bool write_impl(const LibertyDB& db, const StringPool& pool,
                        std::ostream& out, std::string* error) {
    if (db.library_count() == 0) {
        if (error) *error = "empty LibertyDB";
        return false;
    }

    for (uint32_t li = 0; li < db.library_count(); ++li) {
        const auto& lib = db.library(li);
        std::string lname = writer::sv(pool, lib.name);
        if (lname.empty()) lname = "library";

        // header
        if (!lib.power_metadata_complete || !lib.electrical_metadata_complete || !lib.sequential_metadata_complete)
            throw std::runtime_error("incomplete Liberty metadata cannot be exported faithfully");
        out << "library (\"" << lname << "\") {\n";
        const auto& u = lib.units;
        if (!(u.time_unit_seconds>0 && u.capacitance_unit_farads>0 &&
              u.voltage_unit_volts>0 && u.leakage_power_unit_watts>0 && u.current>0 && u.resistance>0))
            throw std::runtime_error("invalid Liberty unit scale");
        if (u.time!=1 || u.capacitance!=1 || u.leakage_power!=1)
            throw std::runtime_error("noncanonical legacy Liberty unit scale");
        out << "  delay_model : table_lookup;\n";
        out << "  time_unit : \"" << writer::fn(u.time_unit_seconds/1e-9f) << "ns\";\n";
        out << "  capacitive_load_unit (" << writer::fn(u.capacitance_unit_farads/1e-12f) << ", pf);\n";
        out << "  voltage_unit : \"" << writer::fn(u.voltage_unit_volts) << "V\";\n";
        out << "  current_unit : \"" << writer::fn(u.current) << "mA\";\n";
        out << "  leakage_power_unit : \"" << writer::fn(u.leakage_power_unit_watts/1e-9f) << "nW\";\n";
        out << "  pulling_resistance_unit : \"" << writer::fn(u.resistance) << "kohm\";\n";
        out << "  nom_process : " << writer::fn(1.0) << ";\n";
        out << "  nom_temperature : " << writer::fn(25.0) << ";\n";
        out << "  nom_voltage : " << writer::fn(u.voltage) << ";\n";
        out << "  default_max_transition : " << writer::fn(lib.default_max_transition)
            << ";\n";
        out << "  default_fanout_load : " << writer::fn(lib.default_fanout_load)
            << ";\n";
        out << "  default_max_capacitance : " << writer::fn(lib.default_max_capacitance) << ";\n";
        out << "  default_max_fanout : " << writer::fn(lib.default_max_fanout) << ";\n";
        writer::attr(out,pool,"default_wire_load",lib.default_wire_load);
        if (lib.default_wire_load_selection!=UINT32_MAX)
            throw std::runtime_error("wire_load_selection groups are not retained for export");
        for (const auto& w : lib.wire_load_models) {
            out << "  wire_load (\"" << writer::sv(pool,w.name) << "\") {\n";
            out << "    resistance : " << writer::fn(w.resistance) << ";\n";
            out << "    capacitance : " << writer::fn(w.capacitance) << ";\n";
            out << "    area : " << writer::fn(w.area) << ";\n";
            out << "    slope : " << writer::fn(w.slope) << ";\n";
            for (const auto& f : w.fanout_lengths)
                out << "    fanout_length (" << f.first << ", " << writer::fn(f.second) << ");\n";
            out << "  }\n";
        }
        out << "  slew_lower_threshold_pct_rise : "
            << writer::fn(u.slew_lower * 100) << ";\n";
        out << "  slew_lower_threshold_pct_fall : "
            << writer::fn(u.slew_lower * 100) << ";\n";
        out << "  slew_upper_threshold_pct_rise : "
            << writer::fn(u.slew_upper * 100) << ";\n";
        out << "  slew_upper_threshold_pct_fall : "
            << writer::fn(u.slew_upper * 100) << ";\n";
        out << "  input_threshold_pct_rise : "
            << writer::fn(u.input_threshold_rise * 100) << ";\n";
        out << "  input_threshold_pct_fall : "
            << writer::fn(u.input_threshold_fall * 100) << ";\n";
        out << "  output_threshold_pct_rise : "
            << writer::fn(u.output_threshold_rise * 100) << ";\n";
        out << "  output_threshold_pct_fall : "
            << writer::fn(u.output_threshold_fall * 100) << ";\n";
        out << "  slew_derate_from_library : " << writer::fn(u.slew_derate)
            << ";\n";
        out << "\n";
        // delay/power templates (generic — inline axes override)
        out << "  lu_table_template (delay_template) {\n";
        out << "    variable_1 : input_net_transition;\n";
        out << "    variable_2 : total_output_net_capacitance;\n";
        out << "    index_1 (\"0.001, 0.1\");\n";
        out << "    index_2 (\"0.001, 0.1\");\n";
        out << "  }\n";
        out << "  power_lut_template (power_template) {\n";
        out << "    variable_1 : input_transition_time;\n";
        out << "    variable_2 : total_output_net_capacitance;\n";
        out << "    index_1 (\"0.001\"); index_2 (\"0.001\");\n  }\n";
        out << "  lu_table_template (constraint_template) {\n";
        out << "    variable_1 : related_pin_transition;\n";
        out << "    variable_2 : constrained_pin_transition;\n";
        out << "    index_1 (\"0.001, 0.1\");\n";
        out << "    index_2 (\"0.001, 0.1\");\n";
        out << "  }\n";
        out << "  output_current_template (ccs_template) {\n";
        out << "    variable_1 : input_net_transition;\n";
        out << "    variable_2 : total_output_net_capacitance;\n";
        out << "    variable_3 : time;\n";
        out << "  }\n\n";

        // cells
        for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
            const auto& cell = lib.cells[ci];
            std::string cn = writer::sv(pool, cell.name);
            out << "  cell (\"" << cn << "\") {\n";
            out << "    area : " << writer::fn(cell.area) << ";\n";
            if (!cell.pvt_points.empty()) throw std::runtime_error("per-cell PVT export is unsupported");
            writer::attr(out,pool,"function",cell.function);
            writer::attr(out,pool,"clock_gating_integrated_cell",cell.clock_gating_integrated_cell);
            // These fields are aggregates of the output pins in the parser.
            // Cell-level defaults must not override the retained per-pin limits.
            auto aggregate=[&](auto member,float stored) {
                float value=0;
                for (const auto& p : cell.pins) if (p.direction==ec::PortDirection::Output && p.*member>0)
                    value=value>0 ? std::min(value,p.*member) : p.*member;
                if (value!=stored) throw std::runtime_error("cell electrical aggregate has no matching pin limits");
            };
            aggregate(&ec::LibertyPinData::max_capacitance,cell.max_capacitance);
            aggregate(&ec::LibertyPinData::max_transition,cell.max_transition);
            aggregate(&ec::LibertyPinData::max_fanout,cell.max_fanout);
            for (const auto& leak : cell.leakage_power) {
                out << "    leakage_power () {\n";
                writer::attr(out,pool,"when",leak.when);
                writer::attr(out,pool,"related_pg_pin",leak.related_pg_pin);
                out << "      value : " << writer::fn(leak.value) << ";\n    }\n";
            }
            if (cell.footprint != UINT32_MAX) {
                std::string fp = writer::sv(pool, cell.footprint);
                if (!fp.empty())
                    out << "    cell_footprint : \"" << fp << "\";\n";
            }
            if (cell.dont_use) out << "    dont_use : true;\n";
            if (cell.cell_leakage_power != 0.0f)
                out << "    cell_leakage_power : "
                    << writer::fn(cell.cell_leakage_power) << ";\n";

            // sequential state (only if state names are valid)
            std::string fs = writer::sv(pool, cell.ff_state);
            std::string fn2 = writer::sv(pool, cell.ff_next_state);
            if ((cell.ff_clocked_on!=UINT32_MAX || cell.ff_next_state!=UINT32_MAX ||
                 cell.ff_state!=UINT32_MAX || cell.ff_clear!=UINT32_MAX || cell.ff_preset!=UINT32_MAX ||
                 cell.ff_enable!=UINT32_MAX) &&
                (cell.ff_clocked_on==UINT32_MAX || fs.empty() || fn2.empty()))
                throw std::runtime_error("incomplete sequential state cannot be exported");
            if (cell.ff_clocked_on != UINT32_MAX && !fs.empty() && !fn2.empty()) {
                out << "    ff (\"" << fs << "\"";
                if (cell.ff_state_neg!=UINT32_MAX)
                    out << ", \"" << writer::sv(pool,cell.ff_state_neg) << "\"";
                out << ") {\n";
                out << "      next_state : \"" << fn2 << "\";\n";
                out << "      clocked_on : \""
                    << writer::sv(pool, cell.ff_clocked_on) << "\";\n";
                writer::attr(out,pool,"enable",cell.ff_enable);
                if (cell.ff_clear != UINT32_MAX)
                    out << "      clear : \""
                        << writer::sv(pool, cell.ff_clear) << "\";\n";
                if (cell.ff_preset != UINT32_MAX)
                    out << "      preset : \""
                        << writer::sv(pool, cell.ff_preset) << "\";\n";
                out << "    }\n";
            }

            // pins
            for (const auto& pin : cell.pins) {
                std::string pn = writer::sv(pool, pin.name);
                out << "    pin (\"" << pn << "\") {\n";
                out << "      direction : "
                    << writer::dir_str(pin.direction) << ";\n";
                if (pin.capacitance != 0.0f)
                    out << "      capacitance : "
                        << writer::fn(pin.capacitance) << ";\n";
                if (pin.is_clock) out << "      clock : true;\n";
                if (pin.rise_capacitance>=0) out << "      rise_capacitance : " << writer::fn(pin.rise_capacitance) << ";\n";
                if (pin.fall_capacitance>=0) out << "      fall_capacitance : " << writer::fn(pin.fall_capacitance) << ";\n";
                if (pin.rise_capacitance_lower>=0 && pin.rise_capacitance_upper>=0)
                    out << "      rise_capacitance_range (" << writer::fn(pin.rise_capacitance_lower) << ", " << writer::fn(pin.rise_capacitance_upper) << ");\n";
                if (pin.fall_capacitance_lower>=0 && pin.fall_capacitance_upper>=0)
                    out << "      fall_capacitance_range (" << writer::fn(pin.fall_capacitance_lower) << ", " << writer::fn(pin.fall_capacitance_upper) << ");\n";
                writer::attr(out,pool,"related_pg_pin",pin.related_pg_pin);
                writer::attr(out,pool,"clear",pin.clear);
                writer::attr(out,pool,"preset",pin.preset);
                writer::attr(out,pool,"enable",pin.enable);
                if (pin.fanout_load>=0) out << "      fanout_load : " << writer::fn(pin.fanout_load) << ";\n";
                if (pin.max_fanout>=0) out << "      max_fanout : " << writer::fn(pin.max_fanout) << ";\n";
#define GATE_FLAG(f) if(pin.f) out << "      " #f " : true;\n"
                GATE_FLAG(clock_gate_clock_pin); GATE_FLAG(clock_gate_enable_pin);
                GATE_FLAG(clock_gate_test_pin); GATE_FLAG(clock_gate_out_pin);
#undef GATE_FLAG
                if (!pin.ccsn_stages.empty())
                    throw std::runtime_error("CCSN stage text export is not implemented");
                writer::miller(out,pin.miller_cap_rise,pin.miller_cap_fall);
                if (pin.receiver_capacitance.empty()) writer::receiver(out,pin,"      ");
                else for (const auto& r : pin.receiver_capacitance) {
                    out << "      receiver_capacitance () {\n";
                    writer::attr(out,pool,"when",r.when); writer::receiver(out,r,"        ");
                    out << "      }\n";
                }
                for (const auto& power : pin.internal_power) {
                    out << "      internal_power () {\n";
                    writer::attr(out,pool,"related_pin",power.related_pin);
                    writer::attr(out,pool,"related_pg_pin",power.related_pg_pin);
                    writer::attr(out,pool,"when",power.when);
                    writer::write_table(out,"rise_power",power.rise_power,"        ");
                    writer::write_table(out,"fall_power",power.fall_power,"        ");
                    out << "      }\n";
                }
                if (pin.max_capacitance >= 0)
                    out << "      max_capacitance : "
                        << writer::fn(pin.max_capacitance) << ";\n";
                if (pin.max_transition >= 0)
                    out << "      max_transition : "
                        << writer::fn(pin.max_transition) << ";\n";
                if (pin.function != UINT32_MAX) {
                    std::string pf = writer::sv(pool, pin.function);
                    if (!pf.empty())
                        out << "      function : \"" << pf << "\";\n";
                }

                // timing arcs
                for (const auto& arc : cell.arcs) {
                    if (arc.to_pin != pin.name) continue;
                    bool source_found=false;
                    for (const auto& source : cell.pins) if(source.name==arc.from_pin) source_found=true;
                    if (!source_found) throw std::runtime_error("timing source pin is missing");
                    if (!arc.ccsn_stages.empty())
                        throw std::runtime_error("CCSN stage text export is not implemented");
                    writer::miller(out,arc.miller_cap_rise,arc.miller_cap_fall);
                    out << "      timing () {\n";
                    out << "        related_pin : \""
                        << writer::sv(pool, arc.from_pin) << "\";\n";
                    const char* ss = writer::sense_str(arc.sense);
                    if (*ss) out << "        timing_sense : " << ss << ";\n";
                    const char* ts = writer::type_str(arc.type);
                    if (*ts) out << "        timing_type : " << ts << ";\n";
                    if (arc.when != UINT32_MAX) {
                        std::string w = writer::sv(pool, arc.when);
                        if (!w.empty())
                            out << "        when : \"" << w << "\";\n";
                    }

                    // NLDM tables
                    writer::write_table(out, "cell_rise", arc.rise_delay, "        ");
                    writer::write_table(out, "cell_fall", arc.fall_delay, "        ");
                    writer::write_table(out, "rise_transition",
                                       arc.rise_output_slew, "        ");
                    writer::write_table(out, "fall_transition",
                                       arc.fall_output_slew, "        ");
                    writer::receiver(out,arc,"        ");
                    writer::write_table(out, "rise_constraint",
                                           arc.rise_constraint, "        ");
                    writer::write_table(out, "fall_constraint",
                                           arc.fall_constraint, "        ");

                    // CCS
                    writer::write_ccs(out, "output_current_rise",
                                      arc.csm_output_current_rise, "        ");
                    writer::write_ccs(out, "output_current_fall",
                                      arc.csm_output_current_fall, "        ");

                    out << "      }\n";
                }
                out << "    }\n";
            }
            for (const auto& arc : cell.arcs) {
                size_t found=0;
                for (const auto& pin : cell.pins) if(pin.name==arc.to_pin) ++found;
                if (found!=1) throw std::runtime_error("timing destination pin is missing or duplicated");
            }
            out << "  }\n";
        }
        out << "}\n";
    }
    return static_cast<bool>(out);
}


bool write_liberty_text(const LibertyDB& db, const StringPool& pool,
                        std::ostream& out, std::string* error) {
    if (error) error->clear();
    try {
        // Validate the complete model before writing any bytes to the caller.
        std::ostringstream buffer; buffer.imbue(std::locale::classic());
        std::string detail;
        if (!write_impl(db, pool, buffer, &detail)) throw std::runtime_error(detail);
        out << buffer.str();
        if (!out) throw std::runtime_error("Liberty output stream write failed");
        return true;
    } catch (const std::exception& e) { if (error) *error=e.what(); return false; }
}
bool write_liberty_file(const LibertyDB& db, const StringPool& pool,
                        const std::string& path, std::string* error) {
    std::ostringstream buffer;
    if (!write_liberty_text(db, pool, buffer, error)) return false;
    try {
        std::ofstream out(path, std::ios::binary | std::ios::trunc);
        if (!out) throw std::runtime_error("cannot write " + path);
        out << buffer.str(); out.close();
        if (!out) throw std::runtime_error("Liberty file write/close failed: " + path);
        return true;
    } catch (const std::exception& e) { if (error) *error=e.what(); return false; }
}
} // namespace edacraft::core::dbio
