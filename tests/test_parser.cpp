// test_parser.cpp - parser unit tests
#include "parser/parser.hpp"
#include <gtest/gtest.h>
#include <cstdio>
#include <fstream>

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

// ===== C1（Phase C）.lib/.endl corner 块选择测试 =====

TEST(Parser, C1LibEndlSameFileBlockIgnoredIfNotSelected) {
    // .lib NAME ... .endl NAME 块定义：未在 .lib "path" CORNER 选择时，块内容不应出现。
    // 顶层非块行正常解析。
    std::string src =
        "title\n"
        "R1 n1 n2 1k\n"           // 块外：正常
        ".lib TT\n"               // 块 TT 开始
        "R2 n3 n4 2k\n"           // 块内
        ".endl TT\n"
        "R3 n5 n6 3k\n";          // 块外：正常
    auto r = parseNetlist(src, "<test>");
    ASSERT_TRUE(r.ok);
    // 块外 2 个器件（R1, R3），块内 R2 不应出现（未被选择）
    EXPECT_EQ(r.netlist.items.size(), 2u);
    const auto& d0 = std::get<DeviceCard>(r.netlist.items[0]);
    EXPECT_EQ(d0.name, "r1");
    const auto& d1 = std::get<DeviceCard>(r.netlist.items[1]);
    EXPECT_EQ(d1.name, "r3");
}

TEST(Parser, C1LibEndlCrossFileCornerSelect) {
    // 跨文件 .lib "path" CORNER：创建一个 PDK 风格的临时文件，含多个 corner 块，
    // 主网表用 .lib 选择其中一个，验证只有该块的器件被包含。
    const char* dir = RFSIM_TEST_DATA_DIR;
    std::string libPath = std::string(dir) + "/_test_pdk_corner.l";
    {
        std::ofstream f(libPath);
        f <<
            "* test PDK lib\n"
            ".lib TT\n"
            "Rtt a b 1k\n"
            ".endl TT\n"
            ".lib SS\n"
            "Rss a b 2k\n"
            ".endl SS\n"
            ".lib FF\n"
            "Rff a b 3k\n"
            ".endl FF\n";
    }
    std::string src =
        "title\n"
        ".lib \"" + libPath + "\" TT\n";
    auto r = parseNetlist(src, "<test>");
    // 清理临时文件
    std::remove(libPath.c_str());
    ASSERT_TRUE(r.ok);
    // 只有 TT corner 的 Rtt 应出现（1 个器件）
    EXPECT_EQ(r.netlist.items.size(), 1u);
    const auto& d = std::get<DeviceCard>(r.netlist.items[0]);
    EXPECT_EQ(d.name, "rtt");
    EXPECT_DOUBLE_EQ(d.positional[0].num, 1000.0);
}

TEST(Parser, C1LibEndlSelectDifferentCorner) {
    // 选择 SS corner 验证 corner 路由正确（不是固定 TT）
    const char* dir = RFSIM_TEST_DATA_DIR;
    std::string libPath = std::string(dir) + "/_test_pdk_corner2.l";
    {
        std::ofstream f(libPath);
        f <<
            "* test PDK lib\n"
            ".lib TT\n"
            "Rtt a b 1k\n"
            ".endl TT\n"
            ".lib SS\n"
            "Rss a b 2k\n"
            ".endl SS\n";
    }
    std::string src =
        "title\n"
        ".lib \"" + libPath + "\" SS\n";
    auto r = parseNetlist(src, "<test>");
    std::remove(libPath.c_str());
    ASSERT_TRUE(r.ok);
    EXPECT_EQ(r.netlist.items.size(), 1u);
    const auto& d = std::get<DeviceCard>(r.netlist.items[0]);
    EXPECT_EQ(d.name, "rss");
    EXPECT_DOUBLE_EQ(d.positional[0].num, 2000.0);
}


