// test_parser.cpp - parser unit tests
#include "parser/parser.hpp"
#include <gtest/gtest.h>

using namespace rfsim;

TEST(Parser, SimpleDevice) {
    auto r = parseNetlist("title\nR1 n1 n2 1k\n", "<test>");
    ASSERT_TRUE(r.ok) << "errors: " << (r.diags.errors.empty()?"":r.diags.errors[0].message);
    ASSERT_EQ(r.netlist.items.size(), 1u);
    ASSERT_TRUE(std::holds_alternative<DeviceCard>(r.netlist.items[0]));
    const auto& d = std::get<DeviceCard>(r.netlist.items[0]);
    EXPECT_EQ(d.name, "r1");
    EXPECT_EQ(d.firstLetter, 'r');
    ASSERT_EQ(d.nodes.size(), 2u);
    EXPECT_EQ(d.nodes[0], "n1");
    EXPECT_EQ(d.nodes[1], "n2");
    ASSERT_EQ(d.positional.size(), 1u);
    EXPECT_DOUBLE_EQ(d.positional[0].num, 1000.0);
}

TEST(Parser, MosfetWithModel) {
    auto r = parseNetlist("title\nM1 d g s b nmos w=1u l=180n\n", "<test>");
    ASSERT_TRUE(r.ok);
    const auto& d = std::get<DeviceCard>(r.netlist.items[0]);
    EXPECT_EQ(d.firstLetter, 'm');
    EXPECT_EQ(d.model, "nmos");
    ASSERT_EQ(d.nodes.size(), 4u);
    EXPECT_EQ(d.nodes[0], "d");
    EXPECT_EQ(d.params.size(), 2u);
    EXPECT_EQ(d.params[0].first, "w");
    EXPECT_DOUBLE_EQ(d.params[0].second.num, 1e-6);
}

TEST(Parser, ModelCard) {
    auto r = parseNetlist("title\n.model nch nmos (vt0=0.5 kp=50u)\n", "<test>");
    ASSERT_TRUE(r.ok);
    const auto& m = std::get<ModelCard>(r.netlist.items[0]);
    EXPECT_EQ(m.name, "nch");
    EXPECT_EQ(m.type, "nmos");
    EXPECT_EQ(m.params.size(), 2u);
}

TEST(Parser, SubcktDefAndCall) {
    std::string src =
        "title\n"
        ".subckt inv in out vdd gnd\n"
        "Mn1 out in gnd gnd nmos w=1u l=180n\n"
        "Mp1 out in vdd vdd pmos w=2u l=180n\n"
        ".ends\n"
        "Xinv1 in out vdd 0 inv\n";
    auto r = parseNetlist(src, "<test>");
    ASSERT_TRUE(r.ok);
    // 椤跺眰搴旀湁 2 椤癸細subckt 瀹氫箟 + subckt 璋冪敤
    ASSERT_EQ(r.netlist.items.size(), 2u);
    ASSERT_TRUE(std::holds_alternative<std::shared_ptr<SubcktDef>>(r.netlist.items[0]));
    const auto& def = std::get<std::shared_ptr<SubcktDef>>(r.netlist.items[0]);
    EXPECT_EQ(def->name, "inv");
    ASSERT_EQ(def->ports.size(), 4u);
    ASSERT_EQ(def->body.size(), 2u); // 涓や釜鍣ㄤ欢
    ASSERT_TRUE(std::holds_alternative<SubcktCall>(r.netlist.items[1]));
    const auto& call = std::get<SubcktCall>(r.netlist.items[1]);
    EXPECT_EQ(call.subcktName, "inv");
    ASSERT_EQ(call.nodes.size(), 4u);
}

TEST(Parser, ControlCards) {
    std::string src =
        "title\n"
        ".hb freq=2.5G nh=5\n"
        ".print v(out)\n"
        ".options reltol=1e-6\n";
    auto r = parseNetlist(src, "<test>");
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.netlist.items.size(), 3u);
    const auto& hb = std::get<ControlCard>(r.netlist.items[0]);
    EXPECT_EQ(hb.command, "hb");
    ASSERT_EQ(hb.params.size(), 2u);
    EXPECT_EQ(hb.params[0].first, "freq");
    EXPECT_EQ(hb.params[1].first, "nh");
    const auto& pr = std::get<ControlCard>(r.netlist.items[1]);
    EXPECT_EQ(pr.command, "print");
}

TEST(Parser, ParamCard) {
    std::string src =
        "title\n"
        ".param wn=1u wp=2u rl=1k\n";
    auto r = parseNetlist(src, "<test>");
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.netlist.globalParams.size(), 3u);
    EXPECT_EQ(r.netlist.globalParams[0].first, "wn");
    EXPECT_DOUBLE_EQ(r.netlist.globalParams[0].second.num, 1e-6);
}

TEST(Parser, ContinuationAndComments) {
    std::string src =
        "* title\n"
        "R1 n1 n2\n+ 1k ; trailing comment\n"
        "C1 n2 0 1p\n";
    auto r = parseNetlist(src, "<test>");
    ASSERT_TRUE(r.ok);
    ASSERT_EQ(r.netlist.items.size(), 2u);
}

TEST(Parser, ExampleNetlist) {
    // 瑙ｆ瀽 tests/netlists/inverter.sp
    const char* dir = RFSIM_TEST_DATA_DIR;
    std::string path = std::string(dir) + "/inverter.sp";
    auto r = parseFile(path);
    EXPECT_TRUE(r.ok);
    if (!r.ok) {
        for (const auto& e : r.diags.errors) {
            std::cerr << "  " << e.loc.file << ":" << e.loc.line << ": " << e.message << "\n";
        }
    }
}


