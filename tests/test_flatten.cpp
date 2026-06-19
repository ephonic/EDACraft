// test_flatten
#include "circuit/flatten.hpp"
#include "parser/parser.hpp"
#include <gtest/gtest.h>

using namespace rfsim;

TEST(Flatten, SimpleDevicesNodes) {
    auto pr = parseNetlist("title\nR1 a b 1k\nC1 b 0 1p\n", "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist);
    ASSERT_TRUE(fr.ok);
    // 鑺傜偣 a, b锛? 涓哄湴锛?    EXPECT_EQ(fr.circuit.nodes.size(), 2u);
    EXPECT_EQ(fr.circuit.devices.size(), 2u);
}

TEST(Flatten, GroundAliases) {
    auto pr = parseNetlist("title\nR1 gnd a 1k\nR2 a 0 1k\n", "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist);
    ASSERT_TRUE(fr.ok);
    // gnd 涓?0 閮芥槧灏勫埌鑺傜偣 0
    ASSERT_EQ(fr.circuit.devices.size(), 2u);
    EXPECT_EQ(fr.circuit.devices[0].nodes[0], 0u); // gnd -> 0
    EXPECT_EQ(fr.circuit.devices[1].nodes[1], 0u); // 0 -> 0
    // 鑺傜偣 a 搴斿彧鏈?1 涓?    EXPECT_EQ(fr.circuit.nodes.size(), 1u);
}

TEST(Flatten, SubcktExpansion) {
    std::string src =
        "title\n"
        ".subckt inv in out vdd gnd\n"
        "Mn1 out in gnd gnd nmos w=1u\n"
        "Mp1 out in vdd vdd pmos w=2u\n"
        ".ends\n"
        "Xinv1 in out vdd 0 inv\n";
    auto pr = parseNetlist(src, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist);
    ASSERT_TRUE(fr.ok);
    // 灞曞紑鍚庡簲鏈?2 涓櫒浠讹紙Mn1/Mp1锛夛紝甯﹀墠缂€ xinv1.
    EXPECT_EQ(fr.circuit.devices.size(), 2u);
    EXPECT_EQ(fr.circuit.devices[0].name, "xinv1.mn1");
    EXPECT_EQ(fr.circuit.devices[1].name, "xinv1.mp1");
    // 瀛愮數璺唴 gnd 绔彛搴旀槧灏勫埌澶栭儴鐨?0
    EXPECT_EQ(fr.circuit.devices[0].nodes[2], 0u); // Mn1 鐨?source=gnd->0
    EXPECT_EQ(fr.circuit.devices[0].nodes[3], 0u); // Mn1 鐨?body=gnd->0
    EXPECT_EQ(fr.circuit.devices[1].nodes[2], fr.circuit.nodes.lookup("vdd"));
}

TEST(Flatten, NestedSubckt) {
    std::string src =
        "title\n"
        ".subckt nand2 a b out vdd gnd\n"
        "Mn1 out a gnd gnd nmos w=1u\n"
        "Mn2 out b gnd gnd nmos w=1u\n"
        "Mp1 out a vdd vdd pmos w=2u\n"
        "Mp2 out b net vdd pmos w=2u\n"
        ".ends\n"
        ".subckt inv in out vdd gnd\n"
        "Mn out in gnd gnd nmos w=1u\n"
        "Mp out in vdd vdd pmos w=2u\n"
        ".ends\n"
        "Xnand1 a b n vdd 0 nand2\n"
        "Xinv1 n out vdd 0 inv\n";
    auto pr = parseNetlist(src, "<test>");
    ASSERT_TRUE(pr.ok);
    auto fr = flatten(pr.netlist);
    ASSERT_TRUE(fr.ok);
    EXPECT_EQ(fr.circuit.devices.size(), 6u); // nand2(4) + inv(2)
    EXPECT_EQ(fr.circuit.devices[0].name, "xnand1.mn1");
    EXPECT_EQ(fr.circuit.devices[4].name, "xinv1.mn");
}


