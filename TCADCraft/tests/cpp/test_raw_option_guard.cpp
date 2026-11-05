#include "gummel_solver.h"
#include "newton_solver.h"
#include "device_simulator.h"
#include "device_simulator_double.h"
#include <array>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace tcad;
namespace {
size_t checks = 0, failures = 0, wide_checks = 0;
template<class Call> void expect(Call call, bool rejection) {
    bool caught = false;
    try { call(); }
    catch (const std::invalid_argument&) { caught = true; }
    ++checks;
    if (caught != rejection) ++failures;
}
struct GummelAccess {
    using Options = GummelOptions;
    using Solver = GummelSolver;
    static auto hfs(Options& o) { return std::array<real_t*,4>{&o.hfs.vsat_n,&o.hfs.vsat_p,&o.hfs.beta_n,&o.hfs.beta_p}; }
    static auto ii(Options& o) { return std::array<real_t*,4>{&o.ii.A_n,&o.ii.B_n,&o.ii.A_p,&o.ii.B_p}; }
    static auto auger(Options& o) { return std::array<real_t*,2>{&o.auger.Cn,&o.auger.Cp}; }
    static bool& hfs_on(Options& o) { return o.hfs.enabled; }
    static bool& ii_on(Options& o) { return o.ii.enabled; }
    static bool& auger_on(Options& o) { return o.auger.enabled; }
    static int& driving(Options& o) { return o.hfs.driving; }
    static real_t& floor(Options& o) { return o.ii.E_floor; }
};
struct NewtonAccess {
    using Options = NewtonOptions;
    using Solver = NewtonSolver;
    static auto hfs(Options& o) { return std::array<real_t*,4>{&o.hfs_vsat_n,&o.hfs_vsat_p,&o.hfs_beta_n,&o.hfs_beta_p}; }
    static auto ii(Options& o) { return std::array<real_t*,4>{&o.ii_A_n,&o.ii_B_n,&o.ii_A_p,&o.ii_B_p}; }
    static auto auger(Options& o) { return std::array<real_t*,2>{&o.auger_Cn,&o.auger_Cp}; }
    static bool& hfs_on(Options& o) { return o.hfs_enabled; }
    static bool& ii_on(Options& o) { return o.enable_ii; }
    static bool& auger_on(Options& o) { return o.enable_auger; }
    static int& driving(Options& o) { return o.hfs_driving; }
    static real_t& floor(Options& o) { return o.ii_E_floor; }
};
template<class Access> void raw_options() {
    using O = typename Access::Options;
    const Grid3D grid{2,1,1,TCAD_CONST(1e-6),1,1};
    const real_t inf = static_cast<real_t>(std::numeric_limits<double>::infinity());
    const real_t nan = static_cast<real_t>(std::numeric_limits<double>::quiet_NaN());
    auto build = [&](const O& o, bool rejection) {
        expect([&] { typename Access::Solver solver(grid,o); },rejection);
    };
    for (bool on : {false,true}) {
        for (size_t slot=0;slot<4;++slot) {
            for (real_t bad : {real_t(-1),real_t(0),inf,-inf,nan}) {
                O o; Access::hfs_on(o)=on; *Access::hfs(o)[slot]=bad;
                build(o,on);
            }
            for (real_t bad : {real_t(-1),inf,-inf,nan}) {
                O o; Access::ii_on(o)=on; *Access::ii(o)[slot]=bad;
                build(o,on);
            }
        }
        for (int driving : {-1,2,7}) {
            O o; Access::hfs_on(o)=on; Access::driving(o)=driving;
            build(o,on);
        }
        for (real_t bad : {real_t(-1),real_t(0),inf,-inf,nan}) {
            O o; Access::ii_on(o)=on; Access::floor(o)=bad;
            build(o,on);
        }
        for (size_t slot=0;slot<2;++slot)
            for (real_t bad : {real_t(-1),inf,-inf,nan}) {
                O o; Access::auger_on(o)=on; *Access::auger(o)[slot]=bad;
                build(o,on);
            }
    }
    build(O{},false);
    for (int driving : {0,1}) {
        O o; Access::hfs_on(o)=Access::ii_on(o)=Access::auger_on(o)=true;
        Access::driving(o)=driving;
        for (auto p : Access::ii(o)) *p=0;
        for (auto p : Access::auger(o)) *p=0;
        build(o,false);
    }
    if (real_max_decimal_exponent()>std::numeric_limits<double>::max_exponent10) {
        const real_t wide=static_cast<real_t>(std::numeric_limits<double>::max())*2;
        for (size_t slot=0;slot<4;++slot) {
            O h; Access::hfs_on(h)=true; *Access::hfs(h)[slot]=wide; build(h,false); ++wide_checks;
            O i; Access::ii_on(i)=true; *Access::ii(i)[slot]=wide; build(i,false); ++wide_checks;
        }
        for (size_t slot=0;slot<2;++slot) {
            O o; Access::auger_on(o)=true; *Access::auger(o)[slot]=wide; build(o,false); ++wide_checks;
        }
        O o; Access::ii_on(o)=true; Access::floor(o)=wide; build(o,false); ++wide_checks;
    }
}
template<class Sim,class Scalar> void auger_setter(Sim& sim) {
    const Scalar inf=static_cast<Scalar>(std::numeric_limits<double>::infinity());
    const Scalar nan=static_cast<Scalar>(std::numeric_limits<double>::quiet_NaN());
    for (size_t slot=0;slot<2;++slot)
        for (Scalar bad : {Scalar(-1),inf,-inf,nan}) {
            std::array<Scalar,2> p={Scalar(2.8e-43),Scalar(9.9e-44)};
            p[slot]=bad;
            expect([&] { sim.set_auger_params(p[0],p[1]); },true);
        }
    expect([&] { sim.set_auger_params(0,0); },false);
}
}
int main() {
    try {
        raw_options<GummelAccess>(); raw_options<NewtonAccess>();
        DeviceSimulator native(2,1,1,TCAD_CONST(1e-6),1,1);
        DeviceSimulatorDouble facade(2,1,1,1e-6,1,1);
        auger_setter<DeviceSimulator,real_t>(native);
        auger_setter<DeviceSimulatorDouble,double>(facade);
        if (real_max_decimal_exponent()>std::numeric_limits<double>::max_exponent10) {
            const real_t wide=static_cast<real_t>(std::numeric_limits<double>::max())*2;
            expect([&] { native.set_auger_params(wide,0); },false);
            expect([&] { native.set_auger_params(0,wide); },false);
            wide_checks+=2;
        }
        std::cout << "{\"checks\":" << checks << ",\"failures\":" << failures
                  << ",\"wide_checks\":" << wide_checks << ",\"profile\":\""
                  << compiled_constants_profile_name() << "\"}\n";
        return failures ? 1 : 0;
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 2; }
}
