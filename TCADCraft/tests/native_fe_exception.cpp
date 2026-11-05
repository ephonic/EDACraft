// Standalone regression linked to the real native solver objects, without
// Cython/Python. Allocation injection belongs to this executable only.
#include "device_simulator.h"
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>

using tcad::DeviceSimulator;
using tcad::SimulationResult;
using tcad::real_t;
using Values = std::vector<real_t>;
namespace {
const DeviceSimulator* watched = nullptr;
const Values* entered_p = nullptr;
const Values* entered_h = nullptr;
bool armed = false, fired = false;
int trigger = 0;
void* allocate(std::size_t n) {
    if (armed && watched &&
        (trigger == 1 ? watched->fe_polarization() != *entered_p
                      : watched->ferroelectric_play_history() != *entered_h)) {
        // Single shot: rollback, unwinding and subsequent retries allocate
        // normally. Observers return references and comparisons never allocate.
        armed = false;
        fired = true;
        throw std::bad_alloc();
    }
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
}
void* operator new(std::size_t n) { return allocate(n); }
void* operator new[](std::size_t n) { return allocate(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }

namespace {
std::unique_ptr<DeviceSimulator> make_device(int axis, int model, bool newton) {
    const size_t N = 9;
    const real_t d = TCAD_CONST(40e-9) / (N - 1);
    auto owned = std::make_unique<DeviceSimulator>(axis==0?N:1, axis==1?N:1, axis==2?N:1,
                      axis==0?d:1, axis==1?d:1, axis==2?d:1);
    auto& s = *owned;
    s.set_permittivity(Values(N, 9*tcad::EPS0));
    s.set_mobility(Values(N,0), Values(N,0));
    s.set_doping(Values(N,0));
    s.set_effective_dos(Values(N,TCAD_CONST(2.8e25)),Values(N,TCAD_CONST(1.04e25)));
    s.set_bandgap(Values(N,6));
    s.set_thermal_voltage(TCAD_CONST(.02585));
    s.set_electron_bc({{0,0},{N-1,0}});
    s.set_hole_bc({{0,0},{N-1,0}});
    s.set_dirichlet_potential({{0,0},{N-1,0}});
    s.set_ferroelectric_enabled(true);
    s.set_ferroelectric_params(std::vector<char>(N,1),TCAD_CONST(-5e8),TCAD_CONST(1.25e10));
    s.set_ferroelectric_model(model);
    s.set_ferroelectric_polar_axis(axis);
    s.set_ferroelectric_preisach(TCAD_CONST(.2),TCAD_CONST(1e8),TCAD_CONST(1e8));
    s.set_ferroelectric_nls(1,0,TCAD_CONST(.1));
    s.set_use_newton(newton);
    s.set_gummel_max_iter(300);
    s.set_tolerance(TCAD_CONST(1e-8));
    return owned;
}
void values(const Values& v) {
    std::cout << '[';
    for (size_t i=0; i<v.size(); ++i) {
        char b[160];
#ifdef TCAD_USE_FLOAT128
        quadmath_snprintf(b,sizeof b,"%.36Qg",v[i]);
#else
        snprintf(b,sizeof b,"%.36Lg",v[i]);
#endif
        if (i) std::cout << ',';
        std::cout << '"' << b << '"';
    }
    std::cout << ']';
}
void result(const SimulationResult& r) {
    std::cout << "{\"converged\":" << r.converged << ",\"iterations\":" << r.iterations;
#define FIELD(name) std::cout << ",\"" #name "\":"; values(r.name)
    FIELD(phi); FIELD(n); FIELD(p); FIELD(P);
    FIELD(Ex); FIELD(Ey); FIELD(Ez); FIELD(Qn); FIELD(Qp); FIELD(temperature);
    FIELD(Jn_x); FIELD(Jn_y); FIELD(Jn_z); FIELD(Jp_x); FIELD(Jp_y); FIELD(Jp_z);
#undef FIELD
    std::cout << '}';
}
bool equal(const SimulationResult& a, const SimulationResult& b) {
    return a.converged==b.converged && a.iterations==b.iterations &&
        a.phi==b.phi && a.n==b.n && a.p==b.p && a.P==b.P &&
        a.Ex==b.Ex && a.Ey==b.Ey && a.Ez==b.Ez && a.Qn==b.Qn && a.Qp==b.Qp &&
        a.temperature==b.temperature && a.Jn_x==b.Jn_x && a.Jn_y==b.Jn_y &&
        a.Jn_z==b.Jn_z && a.Jp_x==b.Jp_x && a.Jp_y==b.Jp_y && a.Jp_z==b.Jp_z;
}
bool row(int axis,int model,bool newton,bool warm,int mode) {
    auto owned=make_device(axis,model,newton), reference_owned=make_device(axis,model,newton);
    auto& s=*owned;
    auto& ref=*reference_owned;
    if (warm) {
        for (auto* q : {&s,&ref}) {
            if (!q->solve().converged) throw std::runtime_error("zero-bias seed rejected");
            q->set_dirichlet_potential({{0,0},{8,8}});
            if (!q->solve().converged) throw std::runtime_error("programmed seed rejected");
        }
    }
    const Values p=s.fe_polarization(), h=s.ferroelectric_play_history();
    s.set_dirichlet_potential({{0,0},{8,-8}});
    ref.set_dirichlet_potential({{0,0},{8,-8}});
    bool caught=false;
    fired=false;
    if (mode) {
        watched=&s; entered_p=&p; entered_h=&h; trigger=mode; armed=true;
        try { s.solve(); }
        catch (const std::bad_alloc&) { caught=true; }
        catch (...) { armed=false; watched=nullptr; throw; }
        armed=false; watched=nullptr;
    }
    const Values after_p=s.fe_polarization(), after_h=s.ferroelectric_play_history();
    const bool restored=after_p==p && after_h==h;
    auto retried=s.solve(), reference=ref.solve();
    const bool same=equal(retried,reference) &&
        s.ferroelectric_play_history()==ref.ferroelectric_play_history();
    // A later reversal also checks that hidden branch/initialization memory
    // matches an independent solver, rather than checking public P alone.
    s.set_dirichlet_potential({{0,0},{8,12}});
    ref.set_dirichlet_potential({{0,0},{8,12}});
    auto reversed=s.solve(), ref_reversed=ref.solve();
    const bool future=equal(reversed,ref_reversed) &&
        s.ferroelectric_play_history()==ref.ferroelectric_play_history();
    const bool pass=(!mode || (caught && fired && restored)) && same && future &&
        retried.converged && reference.converged && reversed.converged && ref_reversed.converged;
    std::cout << "{\"axis\":" << axis << ",\"model\":" << model
        << ",\"newton\":" << newton << ",\"warm\":" << warm << ",\"trigger\":" << mode
        << ",\"caught\":" << caught << ",\"fired\":" << fired << ",\"restored\":" << restored
        << ",\"same_retry\":" << same << ",\"same_reversal\":" << future << ",\"passed\":" << pass;
    std::cout << ",\"entered_P\":"; values(p);
    std::cout << ",\"entered_play\":"; values(h);
    std::cout << ",\"after_P\":"; values(after_p);
    std::cout << ",\"after_play\":"; values(after_h);
    std::cout << ",\"retry\":"; result(retried);
    std::cout << ",\"reference\":"; result(reference);
    std::cout << ",\"reversal\":"; result(reversed);
    std::cout << ",\"reference_reversal\":"; result(ref_reversed);
    std::cout << "}\n";
    return pass;
}
}
int main(int argc,char** argv) {
    std::cout << std::boolalpha;
    bool pass=true;
    try {
        for (int axis=0;axis<3;++axis)
        for (int model=0;model<4;++model)
        for (bool newton : {false,true})
        for (bool warm : {false,true}) {
            pass=row(axis,model,newton,warm,0) && pass;
            pass=row(axis,model,newton,warm,1) && pass;
            if (model==1 || model==3) pass=row(axis,model,newton,warm,2) && pass;
        }
    } catch (const std::exception& e) {
        armed=false;
        std::cerr << "fixture error: " << e.what() << '\n';
        return 2;
    }
    return (pass || (argc==2 && std::string(argv[1])=="--observe")) ? 0 : 1;
}
