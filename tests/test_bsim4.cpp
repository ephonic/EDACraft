// test_bsim4.cpp - MOSFET OSDI model tests (BSIM4 / EKV / optional BSIM4SOI / BSIMCMG)
#include "model/osdi/osdi_library.hpp"
#include "model/osdi_model.hpp"
#include <gtest/gtest.h>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
using namespace rfsim;

namespace {

#ifndef RFSIM_TEST_DATA_DIR
#define RFSIM_TEST_DATA_DIR "."
#endif

std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;
    // RFSIM_TEST_DATA_DIR = <project>/tests/netlists
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);      // <project>/tests
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);      // <project>
    return s;
}

std::string defaultModelPath(const char* envVar, const char* fallback) {
    if (const char* p = std::getenv(envVar)) return p;
    std::string root = projectRootFromTestData();
    return root + "/" + fallback;
}

struct MosModelInfo {
    const char* name;
    const char* envVar;
    const char* fallback;
    uint32_t minTerminals;
};

const std::vector<MosModelInfo> kMosModels = {
    {"bsim4", "RFSIM_BSIM4_LIB", "models/bsim4.dll", 4},
    {"ekv",   "RFSIM_EKV_LIB",   "models/ekv.dll",   4},
    {"bsim4soi", "RFSIM_BSIM4SOI_LIB", "models/bsim4soi.dll", 4},
    {"bsimcmg",  "RFSIM_BSIMCMG_LIB",  "models/bsimcmg.dll",  4},
};

} // namespace

class MosfetModelTest : public ::testing::TestWithParam<MosModelInfo> {};

TEST_P(MosfetModelTest, Descriptor) {
    const auto& info = GetParam();
    std::string path = defaultModelPath(info.envVar, info.fallback);
    OsdiLibrary lib;
    std::string err;
    if (!lib.load(path, err)) {
        GTEST_SKIP() << "cannot load " << info.name << " from " << path
                     << ": " << err;
    }
    ASSERT_GE(lib.numDescriptors(), 1u);
    const OsdiDescriptor* d = &lib.descriptors()[0];
    std::cout << "[Mosfet] " << info.name << " name=" << (d->name ? d->name : "?")
              << " nodes=" << d->num_nodes
              << " terminals=" << d->num_terminals
              << " jac=" << d->num_jacobian_entries << "\n";
    EXPECT_GE(d->num_nodes, d->num_terminals);
    EXPECT_GE(d->num_terminals, info.minTerminals);
    EXPECT_NE(d->eval, nullptr);
    EXPECT_NE(d->setup_instance, nullptr);
}

TEST_P(MosfetModelTest, SetupInstance) {
    const auto& info = GetParam();
    std::string path = defaultModelPath(info.envVar, info.fallback);
    OsdiLibrary lib;
    std::string err;
    if (!lib.load(path, err)) {
        GTEST_SKIP() << "cannot load " << info.name << " from " << path
                     << ": " << err;
    }
    auto libShared = std::make_shared<OsdiLibrary>(std::move(lib));
    const OsdiDescriptor* d = libShared->descriptors();

    // 按 descriptor 的端子数构造外部节点连接（多余的端子接地）
    std::vector<NodeId> nodes(d->num_terminals, 0);
    if (d->num_terminals > 0) nodes[0] = 1; // drain
    if (d->num_terminals > 1) nodes[1] = 2; // gate
    // source/bulk/substrate/others default to ground

    // 设置典型实例参数 W/L
    ParamList instParams;
    instParams.push_back({"w", ParamValue{ParamValue::Kind::Number, 1e-6, "", SourceLoc{}}});
    instParams.push_back({"l", ParamValue{ParamValue::Kind::Number, 130e-9, "", SourceLoc{}}});

    ParamList modelParams;
    if (std::string(info.name) == "bsim4") {
        // Minimal BSIM4.8 NMOS model card matching the parameter names exposed
        // by the OpenVAF-compiled bsim4va model (models/bsim4.va).
        auto add = [&](const char* n, double v) {
            modelParams.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
        };
        add("toxe", 3e-9);
        add("toxp", 3e-9);
        add("vth0", 0.5);
        add("k1", 0.5);
        add("k2", 0.0);
        add("k3", 0.0);
        add("dvt0", 1.0);
        add("dvt1", 2.0);
        add("dvt2", -0.032);
        add("u0", 0.045);
        add("ua", -1e-10);
        add("ub", 0.0);
        add("vsat", 1.5e5);
        add("rdsw", 160);
        add("nfactor", 1.2);
        add("cgso", 0.1e-9);
        add("cgdo", 0.1e-9);
        add("cgbo", 0.0);
        add("cjs", 1e-3);
        add("cjd", 1e-3);
        add("cjsws", 1e-10);
        add("cjswd", 1e-10);
        add("mjs", 0.5);
        add("mjd", 0.5);
        add("mjsws", 0.33);
        add("mjswd", 0.33);
        add("pbs", 0.88);
        add("pbd", 0.88);
        add("pbsws", 0.88);
        add("pbswd", 0.88);
    }

    auto mos = std::make_unique<OsdiModel>("m1",
        nodes, libShared, d, instParams, modelParams);
    Diagnostics diags;
    bool ok = mos->initialize(diags);
    std::cout << "[Mosfet] " << info.name << " setup: " << (ok ? "OK" : "FAILED")
              << " total nodes=" << mos->nodes().size() << "\n";
    for (auto& e : diags.errors)
        std::cout << "[Mosfet] " << info.name << " err: " << e.message << "\n";
    EXPECT_TRUE(ok);
    EXPECT_GE(mos->nodes().size(), d->num_nodes);
}

INSTANTIATE_TEST_SUITE_P(Mosfet, MosfetModelTest,
                         ::testing::ValuesIn(kMosModels),
                         [](const ::testing::TestParamInfo<MosModelInfo>& p) {
                             return p.param.name;
                         });
