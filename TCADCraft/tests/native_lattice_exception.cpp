// Read-only private-state observation uses -fno-access-control on this test
// translation unit only. All fixture changes use the public native API.
#include "device_simulator.h"
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <new>
#include <stdexcept>
#include <string>
using tcad::DeviceSimulator;
using tcad::SimulationResult;
using tcad::real_t;
using Values=std::vector<real_t>;
namespace {
bool armed=false,fired=false,after_inner=false;
size_t allocations=0,fail_at=0;
const DeviceSimulator* watched=nullptr;
std::uintptr_t entered_data=0;
void* allocate(size_t size){
    if(armed){
        ++allocations;
        bool hit=after_inner ? reinterpret_cast<std::uintptr_t>(watched->init_phi_.data())!=entered_data : allocations==fail_at;
        if(hit){armed=false;fired=true;throw std::bad_alloc();}
    }
    if(void* p=std::malloc(size?size:1))return p;
    throw std::bad_alloc();
}
}
void* operator new(size_t n){return allocate(n);}
void* operator new[](size_t n){return allocate(n);}
void operator delete(void* p) noexcept{std::free(p);}
void operator delete[](void* p) noexcept{std::free(p);}
void operator delete(void* p,size_t) noexcept{std::free(p);}
void operator delete[](void* p,size_t) noexcept{std::free(p);}
namespace {
struct Snapshot{
    Values phi,n,p,mobility,previous,capacity,Qn,Qp,P,play;
    std::vector<char> bd;
    real_t dt;
    bool guess,fe_init,bd_init;
    explicit Snapshot(const DeviceSimulator& s):phi(s.init_phi_),n(s.init_n_),p(s.init_p_),
        mobility(s.mobility_temperature_),previous(s.lattice_previous_temperature_),capacity(s.lattice_heat_capacity_),
        Qn(s.dg_transport_Qn_),Qp(s.dg_transport_Qp_),P(s.fe_polarization()),play(s.ferroelectric_play_history()),
        bd(s.breakdown_state()),dt(s.lattice_dt_),guess(s.has_initial_guess_),fe_init(s.fe_polarization_init_),bd_init(s.bd_state_init_){}
    bool operator==(const Snapshot& b)const{
        return phi==b.phi && n==b.n && p==b.p && mobility==b.mobility && previous==b.previous &&
            capacity==b.capacity && dt==b.dt && guess==b.guess && Qn==b.Qn && Qp==b.Qp && P==b.P && play==b.play &&
            bd==b.bd && fe_init==b.fe_init && bd_init==b.bd_init;
    }
};
void values(const Values& v){
    std::cout<<'[';
    for(size_t i=0;i<v.size();++i){char b[160];
#ifdef TCAD_USE_FLOAT128
        quadmath_snprintf(b,sizeof b,"%.36Qg",v[i]);
#else
        snprintf(b,sizeof b,"%.36Lg",v[i]);
#endif
        if(i)std::cout<<',';
        std::cout<<'"'<<b<<'"';
    }
    std::cout<<']';
}
void snapshot(const Snapshot& s){
    std::cout<<"{\"guess\":"<<s.guess<<",\"fe_init\":"<<s.fe_init<<",\"bd_init\":"<<s.bd_init;
#define FIELD(name) std::cout<<",\"" #name "\":";values(s.name)
    FIELD(phi);FIELD(n);FIELD(p);FIELD(mobility);FIELD(previous);FIELD(capacity);FIELD(Qn);FIELD(Qp);FIELD(P);FIELD(play);
#undef FIELD
    std::cout<<",\"dt\":";values({s.dt});
    std::cout<<",\"bd\":[";for(size_t i=0;i<s.bd.size();++i){if(i)std::cout<<',';std::cout<<int(s.bd[i]);}std::cout<<"]}";
}
void result(const SimulationResult& r){
    std::cout<<"{\"converged\":"<<r.converged<<",\"iterations\":"<<r.iterations;
#define FIELD(name) std::cout<<",\"" #name "\":";values(r.name)
    FIELD(phi);FIELD(n);FIELD(p);FIELD(Qn);FIELD(Qp);FIELD(temperature);
    FIELD(Jn_x);FIELD(Jn_y);FIELD(Jn_z);FIELD(Jp_x);FIELD(Jp_y);FIELD(Jp_z);
#undef FIELD
    auto& t=r.thermal;
    std::cout<<",\"ledger_available\":"<<t.available<<",\"storage\":"<<t.transient_storage
        <<",\"feedback\":"<<t.mobility_feedback<<",\"feedback_iterations\":"<<t.feedback_iterations;
    std::cout<<",\"dt\":";values({t.dt});std::cout<<",\"storage_power\":";values({t.storage_power});
    std::cout<<",\"previous\":";values(t.previous_temperature);std::cout<<",\"capacity\":";values(t.heat_capacity);
    std::cout<<",\"mobility_temperature\":";values(t.mobility_temperature);std::cout<<'}';
}
bool same(const SimulationResult& a,const SimulationResult& b){
    return a.converged==b.converged && a.iterations==b.iterations && a.phi==b.phi && a.n==b.n && a.p==b.p &&
        a.Qn==b.Qn && a.Qp==b.Qp && a.temperature==b.temperature && a.Jn_x==b.Jn_x && a.Jn_y==b.Jn_y && a.Jn_z==b.Jn_z &&
        a.Jp_x==b.Jp_x && a.Jp_y==b.Jp_y && a.Jp_z==b.Jp_z && a.thermal.available==b.thermal.available &&
        a.thermal.transient_storage==b.thermal.transient_storage && a.thermal.mobility_feedback==b.thermal.mobility_feedback &&
        a.thermal.feedback_iterations==b.thermal.feedback_iterations && a.thermal.dt==b.thermal.dt &&
        a.thermal.storage_power==b.thermal.storage_power && a.thermal.previous_temperature==b.thermal.previous_temperature &&
        a.thermal.heat_capacity==b.thermal.heat_capacity && a.thermal.mobility_temperature==b.thermal.mobility_temperature;
}
SimulationResult invoke(DeviceSimulator& s,int mode){
    if(mode==0)return s.solve();
    const Values previous(5,TCAD_CONST(310.0)),capacity(5,TCAD_CONST(2e5));
    return s.solve_lattice_step(previous,capacity,TCAD_CONST(1e-7));
}
std::unique_ptr<DeviceSimulator> device(int axis,int mode,bool warm){
    const size_t N=5;const real_t d=TCAD_CONST(1e-7)/(N-1);
    auto owned=std::make_unique<DeviceSimulator>(axis==0?N:1,axis==1?N:1,axis==2?N:1,
        axis==0?d:TCAD_CONST(1e-7),axis==1?d:TCAD_CONST(8e-8),axis==2?d:TCAD_CONST(6e-8));
    auto& s=*owned;
    s.set_permittivity(Values(N,TCAD_CONST(1e-10)));s.set_mobility(Values(N,TCAD_CONST(.01)),Values(N,TCAD_CONST(.005)));
    s.set_doping(Values(N,0));s.set_effective_dos(Values(N,TCAD_CONST(1e21)),Values(N,TCAD_CONST(1e21)));s.set_bandgap(Values(N,0));
    s.set_temperature(300);s.set_mobility_model(1);
    s.set_electron_bc({{0,TCAD_CONST(1e21)},{N-1,TCAD_CONST(1e21)}});s.set_hole_bc({{0,TCAD_CONST(1e21)},{N-1,TCAD_CONST(1e21)}});
    s.set_gummel_max_iter(300);s.set_tolerance(TCAD_CONST(1e-11));s.set_use_newton(true);
    s.set_newton_use_log_space(true);s.set_newton_use_log_damping(true);
    s.set_thermal_coupling_enabled(true);s.set_thermal_conductivity(Values(N,TCAD_CONST(.001)));s.set_thermal_dirichlet({{0,300},{N-1,300}});
    s.set_lattice_mobility_feedback(mode!=2,120,TCAD_CONST(1e-7),TCAD_CONST(.5));
    if(warm){
        s.set_dirichlet_potential({{0,0},{N-1,TCAD_CONST(.04)}});
        if(!invoke(s,mode).converged)throw std::runtime_error("warm seed rejected");
    }
    s.set_dirichlet_potential({{0,0},{N-1,TCAD_CONST(.08)}});
    return owned;
}
bool scenario(int axis,int mode,bool warm){
    auto ref=device(axis,mode,warm);auto reference=invoke(*ref,mode);
    if(!reference.converged)throw std::runtime_error("reference rejected");
    const Snapshot expected(*ref);
    bool passed=true;
    for(int fault=0;fault<=14;++fault){
        if(mode==2 && fault>=13)continue;
        auto s=device(axis,mode,warm);const Snapshot before(*s);
        const bool reject=fault==14;
        if(reject)s->set_lattice_mobility_feedback(true,1,TCAD_CONST(1e-7),TCAD_CONST(.5));
        // Construct caller-side buffers BEFORE arming: only allocations made
        // by the actual native method, including step-input copies, may fail.
        SimulationResult returned;
        const Values previous(5,TCAD_CONST(310.0)),capacity(5,TCAD_CONST(2e5));
        allocations=0;fail_at=fault<=12?size_t(fault):0;fired=false;after_inner=fault==13;
        watched=s.get();entered_data=reinterpret_cast<std::uintptr_t>(s->init_phi_.data());
        armed=fault>0 && fault<14;
        bool caught=false;
        try{returned=mode==0?s->solve():s->solve_lattice_step(previous,capacity,TCAD_CONST(1e-7));}
        catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
        armed=false;watched=nullptr;
        const Snapshot after(*s);
        const bool accepted=!caught && returned.converged,restored=after==before;
        const bool atomic=accepted?after==expected:restored;
        if(reject)s->set_lattice_mobility_feedback(true,120,TCAD_CONST(1e-7),TCAD_CONST(.5));
        auto retry=accepted?std::move(returned):invoke(*s,mode);
        const Snapshot retried(*s);
        bool ok=atomic && retry.converged && same(retry,reference) && retried==expected &&
            (!(fault>0 && fault<14) || fired) && (!reject || !accepted);
        passed=ok && passed;
        std::cout<<"{\"axis\":"<<axis<<",\"mode\":"<<mode<<",\"warm\":"<<warm<<",\"fault\":"<<fault
            <<",\"caught\":"<<caught<<",\"fired\":"<<fired<<",\"accepted\":"<<accepted
            <<",\"restored\":"<<restored<<",\"atomic\":"<<atomic<<",\"passed\":"<<ok;
        std::cout<<",\"before\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);
        std::cout<<",\"retry_state\":";snapshot(retried);std::cout<<",\"reference_state\":";snapshot(expected);
        std::cout<<",\"retry\":";result(retry);std::cout<<",\"reference\":";result(reference);std::cout<<"}\n";
    }
    return passed;
}
}
int main(int argc,char** argv){
    std::cout<<std::boolalpha<<'\n';bool passed=true;
    try{for(int axis=0;axis<3;++axis)for(int mode=0;mode<3;++mode)for(bool warm:{false,true})passed=scenario(axis,mode,warm) && passed;}
    catch(const std::exception& e){armed=false;std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return (passed || (argc==2 && std::string(argv[1])=="--observe"))?0:1;
}
