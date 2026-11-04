#include <cassert>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>

#include "edacraft/core/liberty_db.hpp"
#include "liberty/liberty_binary.hh"
#include "liberty/liberty_parser.hh"

using namespace te;
namespace ec = edacraft::core;

static bool near(float a, float b) {
    if (std::isnan(a) && std::isnan(b)) return true;
    return std::abs(a - b) < 1e-5f;
}

static void check_nldm(const ec::NldmTable& t1, const ec::NldmTable& t2) {
    assert(t1.rows == t2.rows);
    assert(t1.cols == t2.cols);
    assert(t1.axis1.size() == t2.axis1.size());
    assert(t1.axis2.size() == t2.axis2.size());
    assert(t1.values.size() == t2.values.size());
    for (size_t i = 0; i < t1.axis1.size(); ++i) assert(near(t1.axis1[i], t2.axis1[i]));
    for (size_t i = 0; i < t1.axis2.size(); ++i) assert(near(t1.axis2[i], t2.axis2[i]));
    for (size_t i = 0; i < t1.values.size(); ++i) assert(near(t1.values[i], t2.values[i]));
}

static void check_csm(const ec::CsmOutputCurrentTable& t1, const ec::CsmOutputCurrentTable& t2) {
    assert(t1.nslew == t2.nslew);
    assert(t1.ncap == t2.ncap);
    assert(t1.input_slews.size() == t2.input_slews.size());
    assert(t1.load_caps.size() == t2.load_caps.size());
    assert(t1.waveforms.size() == t2.waveforms.size());
    assert(t1.corner_delays.size() == t2.corner_delays.size());
    assert(t1.corner_slews.size() == t2.corner_slews.size());
    for (size_t i = 0; i < t1.input_slews.size(); ++i) assert(near(t1.input_slews[i], t2.input_slews[i]));
    for (size_t i = 0; i < t1.load_caps.size(); ++i) assert(near(t1.load_caps[i], t2.load_caps[i]));
    for (size_t i = 0; i < t1.waveforms.size(); ++i) {
        assert(t1.waveforms[i].time_points.size() == t2.waveforms[i].time_points.size());
        assert(near(t1.waveforms[i].reference_time, t2.waveforms[i].reference_time));
        for (size_t j = 0; j < t1.waveforms[i].time_points.size(); ++j) {
            assert(near(t1.waveforms[i].time_points[j], t2.waveforms[i].time_points[j]));
            assert(near(t1.waveforms[i].current[j], t2.waveforms[i].current[j]));
        }
    }
    for (size_t i = 0; i < t1.corner_delays.size(); ++i) assert(near(t1.corner_delays[i], t2.corner_delays[i]));
    for (size_t i = 0; i < t1.corner_slews.size(); ++i) assert(near(t1.corner_slews[i], t2.corner_slews[i]));
}

static void test_nldm_extrapolation() {
    ec::NldmTable table;
    table.axis1 = {0.0f, 1.0f};
    table.axis2 = {0.0f, 1.0f};
    table.values = {
        0.0f, 10.0f,
        1.0f, 11.0f,
    };
    table.rows = 2;
    table.cols = 2;

    assert(near(table.lookup(0.5f, 0.5f), 5.5f));
    assert(near(table.lookup(2.0f, 0.5f), 7.0f));
    assert(near(table.lookup(-1.0f, 0.5f), 4.0f));
    assert(near(table.lookup(0.5f, 2.0f), 20.5f));
}

static void test_wire_load_group_preserves_following_cells() {
    const char* content = R"lib(
library(test) {
  wire_load(wl0) {
    resistance : 0.000000;
    capacitance : 0.000171;
    area : 0.00;
    slope : 1;
    fanout_length(1, 1);
  }
  lu_table_template(tmg_ntin_oload_2x2) {
    variable_1 : input_net_transition;
    variable_2 : total_output_net_capacitance;
    index_1("1, 2");
    index_2("1, 2");
  }
  cell(BUF_X1) {
    area : 1.0;
    dont_use : true;
    pin(A) {
      direction : input;
      capacitance : 0.01;
    }
    pin(Y) {
      direction : output;
      function : "A";
      timing() {
        related_pin : "A";
        timing_sense : positive_unate;
        timing_type : combinational;
        cell_rise(tmg_ntin_oload_2x2) {
          index_1("0.1, 0.2");
          index_2("0.01, 0.02");
          values("1.0, 2.0", "3.0, 4.0");
        }
        cell_fall(tmg_ntin_oload_2x2) {
          index_1("0.1, 0.2");
          index_2("0.01, 0.02");
          values("1.5, 2.5", "3.5, 4.5");
        }
        rise_transition(tmg_ntin_oload_2x2) {
          index_1("0.1, 0.2");
          index_2("0.01, 0.02");
          values("0.1, 0.2", "0.3, 0.4");
        }
        fall_transition(tmg_ntin_oload_2x2) {
          index_1("0.1, 0.2");
          index_2("0.01, 0.02");
          values("0.1, 0.2", "0.3, 0.4");
        }
      }
    }
  }
}
)lib";

    ec::LibertyDB db;
    ec::StringPool pool;
    parser::LibertyParser parser(content);
    parser.parse(db, pool);

    assert(db.library_count() == 1);
    const auto& lib = db.library(0);
    assert(lib.wire_load_models.size() == 1);
    assert(lib.wire_load_models[0].fanout_lengths.size() == 1);
    assert(lib.cells.size() == 1);
    const auto& cell = lib.cells[0];
    assert(pool.view(cell.name) == "BUF_X1");
    assert(cell.dont_use);
    assert(cell.pins.size() == 2);
    assert(cell.arcs.size() == 1);
    const auto& arc = cell.arcs[0];
    assert(pool.view(arc.from_pin) == "A");
    assert(pool.view(arc.to_pin) == "Y");
    assert(arc.type == ec::LibertyTimingType::Combinational);
    assert(arc.rise_delay.rows == 2);
    assert(arc.rise_delay.cols == 2);
    assert(near(arc.rise_delay.lookup(0.1f, 0.01f), 1.0f));
}

static void test_output_pin_design_rules_are_preserved() {
    const char* content = R"lib(
library(test) {
  default_fanout_load : 1.0;
  default_max_transition : 0.5;
  cell(BUF_X1) {
    area : 1.0;
    pin(A) {
      direction : input;
      capacitance : 0.01;
    }
    pin(Y) {
      direction : output;
      function : "A";
      max_capacitance : 0.125;
      max_transition : 0.40;
      max_fanout : 12.0;
    }
  }
}
)lib";

    ec::LibertyDB db;
    ec::StringPool pool;
    parser::LibertyParser parser(content);
    parser.parse(db, pool);

    assert(db.library_count() == 1);
    const auto& lib = db.library(0);
    assert(lib.cells.size() == 1);
    assert(near(lib.default_max_transition, 0.5f));
    assert(near(lib.default_max_fanout, 0.0f));
    const auto& cell = lib.cells[0];
    assert(near(cell.max_capacitance, 0.125f));
    assert(near(cell.max_transition, 0.40f));
    assert(near(cell.max_fanout, 12.0f));
}

static void test_optional_foundry_nldm_smoke() {
    const std::filesystem::path libpath =
        "../liberty/nldm/HL28HKCSTC7TP140G40HPA01_BASE_TT0P9V85C.lib";
    if (!std::filesystem::exists(libpath)) return;

    std::ifstream infile(libpath);
    std::ostringstream ss;
    ss << infile.rdbuf();
    std::string content = ss.str();

    ec::LibertyDB db;
    ec::StringPool pool;
    parser::LibertyParser parser(content);
    parser.parse(db, pool);

    assert(db.library_count() == 1);
    const auto& lib = db.library(0);
    assert(lib.cells.size() > 0);

    size_t comb_arcs = 0;
    bool saw_dont_use = false;
    for (uint32_t ci = 0; ci < lib.cells.size(); ++ci) {
        const auto& cell = lib.cells[ci];
        saw_dont_use = saw_dont_use || cell.dont_use;
        for (const auto& arc : cell.arcs) {
            if (arc.type == ec::LibertyTimingType::Combinational &&
                arc.rise_delay.rows > 0 &&
                arc.fall_delay.rows > 0) {
                ++comb_arcs;
            }
        }
    }
    assert(saw_dont_use);
    assert(comb_arcs > 0);
}

static void compare_db(const ec::LibertyDB& db1, const ec::StringPool& p1,
                       const ec::LibertyDB& db2, const ec::StringPool& p2) {
    assert(db1.library_count() == db2.library_count());
    for (uint32_t li = 0; li < db1.library_count(); ++li) {
        const auto& l1 = db1.library(li);
        const auto& l2 = db2.library(li);
        assert(l1.cells.size() == l2.cells.size());

        for (uint32_t ci = 0; ci < l1.cells.size(); ++ci) {
            const auto& c1 = l1.cells[ci];
            const auto& c2 = l2.cells[ci];
            assert(p1.view(c1.name) == p2.view(c2.name));
            assert(near(c1.area, c2.area));
            assert(near(c1.max_capacitance, c2.max_capacitance));
            assert(near(c1.max_transition, c2.max_transition));
            assert(near(c1.max_fanout, c2.max_fanout));
            assert(c1.pins.size() == c2.pins.size());
            assert(c1.arcs.size() == c2.arcs.size());
            assert(c1.pvt_points.size() == c2.pvt_points.size());

            for (uint32_t pi = 0; pi < c1.pins.size(); ++pi) {
                assert(p1.view(c1.pins[pi].name) == p2.view(c2.pins[pi].name));
                assert(near(c1.pins[pi].capacitance, c2.pins[pi].capacitance));
                assert(c1.pins[pi].is_clock == c2.pins[pi].is_clock);
                assert(c1.pins[pi].direction == c2.pins[pi].direction);
                assert(c1.pins[pi].arc_ids.size() == c2.pins[pi].arc_ids.size());
                assert(near(c1.pins[pi].miller_cap_rise, c2.pins[pi].miller_cap_rise));
                assert(near(c1.pins[pi].miller_cap_fall, c2.pins[pi].miller_cap_fall));
                check_nldm(c1.pins[pi].receiver_capacitance1_rise, c2.pins[pi].receiver_capacitance1_rise);
                check_nldm(c1.pins[pi].receiver_capacitance1_fall, c2.pins[pi].receiver_capacitance1_fall);
                check_nldm(c1.pins[pi].receiver_capacitance2_rise, c2.pins[pi].receiver_capacitance2_rise);
                check_nldm(c1.pins[pi].receiver_capacitance2_fall, c2.pins[pi].receiver_capacitance2_fall);
                assert(c1.pins[pi].receiver_capacitance.size() ==
                       c2.pins[pi].receiver_capacitance.size());
                for (size_t ri = 0;
                     ri < c1.pins[pi].receiver_capacitance.size(); ++ri) {
                    const auto& r1 = c1.pins[pi].receiver_capacitance[ri];
                    const auto& r2 = c2.pins[pi].receiver_capacitance[ri];
                    assert((r1.when == UINT32_MAX && r2.when == UINT32_MAX) ||
                           p1.view(r1.when) == p2.view(r2.when));
                    check_nldm(r1.receiver_capacitance1_rise,
                               r2.receiver_capacitance1_rise);
                    check_nldm(r1.receiver_capacitance1_fall,
                               r2.receiver_capacitance1_fall);
                    check_nldm(r1.receiver_capacitance2_rise,
                               r2.receiver_capacitance2_rise);
                    check_nldm(r1.receiver_capacitance2_fall,
                               r2.receiver_capacitance2_fall);
                }
            }

            for (uint32_t ai = 0; ai < c1.arcs.size(); ++ai) {
                assert(p1.view(c1.arcs[ai].from_pin) == p2.view(c2.arcs[ai].from_pin));
                assert(p1.view(c1.arcs[ai].to_pin) == p2.view(c2.arcs[ai].to_pin));
                assert(c1.arcs[ai].sense == c2.arcs[ai].sense);
                assert(c1.arcs[ai].type == c2.arcs[ai].type);
                assert(near(c1.arcs[ai].miller_cap_rise,
                            c2.arcs[ai].miller_cap_rise));
                assert(near(c1.arcs[ai].miller_cap_fall,
                            c2.arcs[ai].miller_cap_fall));
                check_nldm(c1.arcs[ai].rise_delay, c2.arcs[ai].rise_delay);
                check_nldm(c1.arcs[ai].fall_delay, c2.arcs[ai].fall_delay);
                check_nldm(c1.arcs[ai].rise_output_slew, c2.arcs[ai].rise_output_slew);
                check_nldm(c1.arcs[ai].fall_output_slew, c2.arcs[ai].fall_output_slew);
                check_nldm(c1.arcs[ai].rise_constraint, c2.arcs[ai].rise_constraint);
                check_nldm(c1.arcs[ai].fall_constraint, c2.arcs[ai].fall_constraint);
                check_nldm(c1.arcs[ai].receiver_capacitance1_rise,
                           c2.arcs[ai].receiver_capacitance1_rise);
                check_nldm(c1.arcs[ai].receiver_capacitance1_fall,
                           c2.arcs[ai].receiver_capacitance1_fall);
                check_nldm(c1.arcs[ai].receiver_capacitance2_rise,
                           c2.arcs[ai].receiver_capacitance2_rise);
                check_nldm(c1.arcs[ai].receiver_capacitance2_fall,
                           c2.arcs[ai].receiver_capacitance2_fall);
                check_csm(c1.arcs[ai].csm_output_current_rise, c2.arcs[ai].csm_output_current_rise);
                check_csm(c1.arcs[ai].csm_output_current_fall, c2.arcs[ai].csm_output_current_fall);
            }
        }
    }
}

static void test_lib(const std::string& libpath) {
    std::ifstream infile(libpath);
    std::ostringstream ss;
    ss << infile.rdbuf();
    std::string content = ss.str();

    ec::LibertyDB db_text;
    ec::StringPool pool_text;
    parser::LibertyParser parser(content);
    parser.parse(db_text, pool_text);

    std::string binpath = libpath + ".ftlib";
    std::string gzpath = libpath + ".ftlib.gz";

    // Uncompressed round-trip
    {
        std::ofstream out(binpath, std::ios::binary);
        assert(save_liberty_binary(db_text, pool_text, out, false));
        out.close();

        ec::LibertyDB db_bin;
        ec::StringPool pool_bin;
        assert(load_liberty_binary(binpath, db_bin, pool_bin));
        compare_db(db_text, pool_text, db_bin, pool_bin);
    }

    // Gzip compressed round-trip
    {
        std::ofstream out(gzpath, std::ios::binary);
        assert(save_liberty_binary(db_text, pool_text, out, true));
        out.close();

        ec::LibertyDB db_gz;
        ec::StringPool pool_gz;
        assert(load_liberty_binary(gzpath, db_gz, pool_gz));
        compare_db(db_text, pool_text, db_gz, pool_gz);
    }

    // Cleanup
    std::filesystem::remove(binpath);
    std::filesystem::remove(gzpath);
}

int main() {
    test_nldm_extrapolation();
    test_wire_load_group_preserves_following_cells();
    test_output_pin_design_rules_are_preserved();
    test_optional_foundry_nldm_smoke();

    std::cout << "Testing seq_cell.lib...\n";
    test_lib("test/compare/seq_cell.lib");
    std::cout << "  PASS\n";

    std::cout << "Testing csm_cell.lib...\n";
    test_lib("test/compare/csm_cell.lib");
    std::cout << "  PASS\n";

    std::cout << "Testing industrial_ccs.lib...\n";
    test_lib("test/compare/industrial_ccs.lib");
    std::cout << "  PASS\n";

    std::cout << "All liberty_binary tests passed!\n";
    return 0;
}
