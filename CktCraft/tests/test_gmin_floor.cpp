// test_gmin_floor.cpp -- plan0620_v2 §B4 gmin homotopy floor path coverage
//
// Goal: build a circuit whose DC OP MUST go through the gmin homotopy
//       "floor accept" branches, and assert:
//
//   (1) r.converged == true
//   (2) r.floorAcceptsInner > 0  OR  r.floorAcceptOuter == true
//
// Design: 1-ref + 1-mirror BSIM4 NMOS current mirror.
//
//   vdd (n1) --[Rref 10k]-- nGate(n2) [diode-connected M_ref]
//   vdd (n1) --[Rload 10k]-- nOut(n3)
//
//   M_ref   : d=2 g=2 s=0 b=0    (gate tied to its own drain)
//   M_mirror: d=3 g=2 s=0 b=0
//
// Per dc_op.cpp:255 doc note --
//   "for gate-strongly-coupled current_mirror topology, gminStart must
//    be smaller (1e-5) to land Newton in the physical region directly,
//    avoiding V(gate) crossing Vth during homotopy ramp which causes
//    ID-avalanche / V(gate)-collapse two-valued switching."
//
// We DELIBERATELY pick gminStart=1e-3 (the hostile choice) so the Vth
// crossing happens during the homotopy sweep, forcing line-search
// backtracking. The residual-floor branch in newtonSolve catches each
// stagnant step and accepts it as the gmin-step OP -> floorAcceptsInner
// counts up. Eventually a deeper gmin step diverges -> floorAcceptOuter.
#include "model/builtin_devices.hpp"
#include "model/osdi_model.hpp"
#include "model/osdi/osdi_library.hpp"
#include "solver/dc_op.hpp"

#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

namespace rfsim {
namespace {

std::string projectRootFromTestData() {
    std::string s = RFSIM_TEST_DATA_DIR;
    auto pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    pos = s.find_last_of("/\\");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}

std::string bsim4LibPath() {
    if (const char* p = std::getenv("RFSIM_BSIM4_LIB")) return p;
#ifdef _WIN32
    return projectRootFromTestData() + "/models/bsim4.dll";
#else
    return projectRootFromTestData() + "/models/bsim4.so";
#endif
}

ParamList bsim4Model() {
    ParamList p;
    auto add = [&](const char* n, double v) {
        p.push_back({n, ParamValue{ParamValue::Kind::Number, v, "", SourceLoc{}}});
    };
    add("toxe", 3e-9); add("toxp", 3e-9); add("vth0", 0.5);
    add("k1", 0.5); add("k2", 0.0); add("k3", 0.0);
    add("dvt0", 1.0); add("dvt1", 2.0); add("dvt2", -0.032);
    add("u0", 0.045); add("ua", -1e-10); add("ub", 0.0);
    add("vsat", 1.5e5); add("rdsw", 160); add("nfactor", 1.2);
    add("cgso", 0.1e-9); add("cgdo", 0.1e-9); add("cgbo", 0.0);
    add("cjs", 1e-3); add("cjd", 1e-3);
    add("cjsws", 1e-10); add("cjswd", 1e-10);
    add("mjs", 0.5); add("mjd", 0.5);
    add("mjsws", 0.33); add("mjswd", 0.33);
    add("pbs", 0.88); add("pbd", 0.88);
    add("pbsws", 0.88); add("pbswd", 0.88);
    return p;
}

ParamList instWL(double w = 1e-6, double l = 130e-9) {
    ParamList p;
    p.push_back({"w", ParamValue{ParamValue::Kind::Number, w, "", SourceLoc{}}});
    p.push_back({"l", ParamValue{ParamValue::Kind::Number, l, "", SourceLoc{}}});
    return p;
}

NodeId computeMaxNode(const std::vector<std::unique_ptr<DeviceModel>>& devs) {
    NodeId mx = 0;
    for (const auto& dv : devs)
        for (NodeId n : dv->nodes()) if (n > mx) mx = n;
    return mx;
}

bool allFinite(const std::vector<double>& v) {
    for (double x : v) if (!std::isfinite(x)) return false;
    return true;
}

} // namespace

TEST(GminFloor, CurrentMirrorHostileHomotopy) {
    OsdiLibrary tmpLib;
    std::string why;
    if (!tmpLib.load(bsim4LibPath(), why))
        GTEST_SKIP() << "bsim4 lib not loadable: " << why;
    auto lib = std::make_shared<OsdiLibrary>(std::move(tmpLib));
    if (lib->numDescriptors() < 1)
        GTEST_SKIP() << "no descriptors in bsim4";
    const OsdiDescriptor* desc = lib->descriptors();

    // Nodes: 1=vdd, 2=nGate(=nDrainRef), 3=nOut
    std::vector<std::unique_ptr<DeviceModel>> devs;
    devs.push_back(std::make_unique<VoltageSource>("vdd", 1, 0, 2.5));
    devs.push_back(std::make_unique<Resistor>("rref",  1, 2, 10e3));
    devs.push_back(std::make_unique<Resistor>("rload", 1, 3, 10e3));

    Diagnostics diags; NodeId base = 4;
    auto mref = std::make_unique<OsdiModel>(
        "mref", std::vector<NodeId>{2, 2, 0, 0},  // d, g(=d, diode), s, b
        lib, desc, instWL(), bsim4Model());
    ASSERT_TRUE(mref->initialize(diags, base)) << "mref BSIM4 init failed";
    devs.push_back(std::move(mref));

    auto mmir = std::make_unique<OsdiModel>(
        "mmir", std::vector<NodeId>{3, 2, 0, 0},  // d=nOut, g=nGate, s, b
        lib, desc, instWL(), bsim4Model());
    ASSERT_TRUE(mmir->initialize(diags, base)) << "mmir BSIM4 init failed";
    devs.push_back(std::move(mmir));

    NodeId nN = computeMaxNode(devs);

    DcOpOptions opts;
    // Hostile gmin schedule: gminStart=1e-3 lands Newton on the wrong side
    // of M_ref's Vth at the first step; subsequent log-spaced steps to
    // gmin=1e-9 cross the threshold and force backtracking.
    opts.gmin.gmin       = 1e-9;
    opts.gmin.gminStart  = 1e-3;
    opts.gmin.gminSteps  = 15;
    opts.maxIterations   = 200;
    opts.dvmax           = 0.2;

    auto r = solveDcOp(nN, devs, opts);

    ASSERT_TRUE(allFinite(r.nodeVoltages))
        << "current-mirror DC produced NaN/Inf";
    EXPECT_TRUE(r.converged) << "current-mirror DC failed to converge";

    // Physical sanity: V[gate] in (0, vdd), V[out] in (0, vdd).
    if (r.converged) {
        double vg = r.nodeVoltages.size() > 2 ? r.nodeVoltages[2] : 0.0;
        double vo = r.nodeVoltages.size() > 3 ? r.nodeVoltages[3] : 0.0;
        EXPECT_GT(vg, 0.0);
        EXPECT_LT(vg, 2.5001);
        EXPECT_GT(vo, 0.0);
        EXPECT_LT(vo, 2.5001);
    }

    // Core assertion: at least one floor branch must have fired.
    bool floorTouched =
        (r.floorAcceptsInner > 0) || r.floorAcceptOuter;
    EXPECT_TRUE(floorTouched)
        << "expected gmin homotopy floor path to be exercised, but "
        << "floorAcceptsInner=" << r.floorAcceptsInner
        << " floorAcceptOuter=" << (r.floorAcceptOuter ? 1 : 0);

    std::fprintf(stderr,
        "[GminFloor.CurrentMirrorHostileHomotopy] conv=%d iters=%u "
        "floorInner=%u floorOuter=%d V[g]=%.4f V[o]=%.4f\n",
        r.converged, r.iterations, r.floorAcceptsInner,
        r.floorAcceptOuter ? 1 : 0,
        r.nodeVoltages.size() > 2 ? r.nodeVoltages[2] : 0.0,
        r.nodeVoltages.size() > 3 ? r.nodeVoltages[3] : 0.0);
}

} // namespace rfsim
