// test_waveform_export.cpp — Phase D: 波形多格式导出单元测试
//
// 覆盖 CSV / rawfile / JSON 三种格式的正确性：
//   - parseWaveFormat / waveFormatName 往返
//   - waveformSignalNames（含/不含 Circuit）
//   - 各格式输出含正确的表头/变量声明/数据点
#include "../src/output/waveform_export.hpp"
#include "../src/solver/time_stepper.hpp"
#include "../src/circuit/node_table.hpp"
#include <gtest/gtest.h>
#include <sstream>
#include <string>

using namespace rfsim;

namespace {
// 构造一个 2 节点 + 1 分支的 3 点波形：t=[0,1,2], v=[0,1,4], i=[0.1,0.2,0.3]
TimeDomainResult makeSampleWave() {
    TimeDomainResult w;
    w.numNodes = 2;
    w.numBranches = 1;
    w.points = {
        {0.0, {0.0, 1.0, 0.1}},
        {1.0, {1.0, 2.0, 0.2}},
        {2.0, {4.0, 3.0, 0.3}},
    };
    return w;
}
} // namespace

TEST(WaveformExport, FormatParseRoundTrip) {
    EXPECT_EQ(parseWaveFormat("csv"), WaveFormat::Csv);
    EXPECT_EQ(parseWaveFormat("raw"), WaveFormat::Rawfile);
    EXPECT_EQ(parseWaveFormat("rawfile"), WaveFormat::Rawfile);
    EXPECT_EQ(parseWaveFormat("json"), WaveFormat::Json);
    EXPECT_EQ(parseWaveFormat("all"), WaveFormat::All);
    EXPECT_EQ(parseWaveFormat("bogus"), WaveFormat::Csv);  // 未知 → csv
    EXPECT_EQ(parseWaveFormat(""), WaveFormat::Csv);
    EXPECT_STREQ(waveFormatName(WaveFormat::Csv), "csv");
    EXPECT_STREQ(waveFormatName(WaveFormat::Rawfile), "raw");
    EXPECT_STREQ(waveFormatName(WaveFormat::Json), "json");
}

TEST(WaveformExport, SignalNamesWithoutCircuit) {
    auto w = makeSampleWave();
    auto names = waveformSignalNames(w);
    // time + v1 + v2 + i0
    ASSERT_EQ(names.size(), 4u);
    EXPECT_EQ(names[0], "time");
    EXPECT_EQ(names[1], "v1");
    EXPECT_EQ(names[2], "v2");
    EXPECT_EQ(names[3], "i0");
}

TEST(WaveformExport, SignalNamesWithCircuit) {
    auto w = makeSampleWave();
    Circuit c;
    c.nodes.intern("in");   // NodeId 1
    c.nodes.intern("out");  // NodeId 2
    auto names = waveformSignalNames(w, &c);
    ASSERT_EQ(names.size(), 4u);
    EXPECT_EQ(names[0], "time");
    EXPECT_EQ(names[1], "v(in)");
    EXPECT_EQ(names[2], "v(out)");
    EXPECT_EQ(names[3], "i0");
}

TEST(WaveformExport, CsvFormat) {
    auto w = makeSampleWave();
    auto names = waveformSignalNames(w);
    std::ostringstream os;
    writeWaveformCsv(os, w, names);
    std::string s = os.str();
    // 表头
    EXPECT_NE(s.find("time,v1,v2,i0"), std::string::npos);
    // 数据点（scientific 格式，含 0、1、4 等值）
    EXPECT_NE(s.find("0.0000000000e+00,1.0000000000e+00"), std::string::npos);  // 第一行 v1=1
}

TEST(WaveformExport, RawfileFormat) {
    auto w = makeSampleWave();
    auto names = waveformSignalNames(w);
    std::ostringstream os;
    writeWaveformRawfile(os, w, names, "test title", "transient");
    std::string s = os.str();
    // ngspice raw 必需字段
    EXPECT_NE(s.find("Title: test title"), std::string::npos);
    EXPECT_NE(s.find("Plotname: transient"), std::string::npos);
    EXPECT_NE(s.find("Flags: real"), std::string::npos);
    EXPECT_NE(s.find("No. Variables: 4"), std::string::npos);
    EXPECT_NE(s.find("No. Points: 3"), std::string::npos);
    EXPECT_NE(s.find("Variables:"), std::string::npos);
    EXPECT_NE(s.find("0 time time"), std::string::npos);
    EXPECT_NE(s.find("1 v1 voltage"), std::string::npos);
    EXPECT_NE(s.find("Values:"), std::string::npos);
}

TEST(WaveformExport, JsonFormat) {
    auto w = makeSampleWave();
    auto names = waveformSignalNames(w);
    std::ostringstream os;
    writeWaveformJson(os, w, names);
    std::string s = os.str();
    EXPECT_NE(s.find("\"title\""), std::string::npos);
    EXPECT_NE(s.find("\"signals\""), std::string::npos);
    EXPECT_NE(s.find("\"time\""), std::string::npos);
    EXPECT_NE(s.find("\"v1\""), std::string::npos);
    EXPECT_NE(s.find("\"points\""), std::string::npos);
    EXPECT_NE(s.find("\"t\":"), std::string::npos);
    EXPECT_NE(s.find("\"v\":"), std::string::npos);
    // 3 个 point 对象
    size_t pos = 0, count = 0;
    while ((pos = s.find("\"t\":", pos)) != std::string::npos) { ++count; ++pos; }
    EXPECT_EQ(count, 3u);
}
