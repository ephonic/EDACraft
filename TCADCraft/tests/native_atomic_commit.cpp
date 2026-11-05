// Link with real solver objects. Compile THIS translation unit only with
// -fno-access-control for read-only observation of accepted continuation state.
// Neither the solver headers/ABI nor its compilation flags are modified.
#include "device_simulator.h"
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
bool armed=false,fired=false;
size_t allocations=0,fail_at=0;
void* allocate(size_t size) {
    if(armed && ++allocations==fail_at) {
        armed=false;fired=true;throw std::bad_alloc();
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
struct Snapshot {
    Values phi,n,p,Qn,Qp,P,play;
    std::vector<char> bd;
    bool guess,fe_init,bd_init;
    explicit Snapshot(const DeviceSimulator& s):phi(s.init_phi_),n(s.init_n_),p(s.init_p_),
        Qn(s.dg_transport_Qn_),Qp(s.dg_transport_Qp_),P(s.fe_polarization()),
        play(s.ferroelectric_play_history()),bd(s.breakdown_state()),guess(s.has_initial_guess_),
        fe_init(s.fe_polarization_init_),bd_init(s.bd_state_init_){}
    bool operator==(const Snapshot& b)const {
        return phi==b.phi && n==b.n && p==b.p && Qn==b.Qn && Qp==b.Qp && P==b.P &&
            play==b.play && bd==b.bd && guess==b.guess && fe_init==b.fe_init && bd_init==b.bd_init;
    }
};
void values(const Values& v) {
    std::cout<<'[';
    for(size_t i=0;i<v.size();++i){char b[160];
#ifdef TCAD_USE_FLOAT128
        quadmath_snprintf(b,sizeof b,"%.36Qg",v[i]);
#else
        snprintf(b,sizeof b,"%.36Lg",v[i]);
#endif
        if(i)std::cout<<',';std::cout<<'"'<<b<<'"';
    }
    std::cout<<']';
}
void snapshot(const Snapshot& s){
    std::cout<<"{\"guess\":"<<s.guess<<",\"fe_init\":"<<s.fe_init<<",\"bd_init\":"<<s.bd_init;
#define FIELD(name) std::cout<<",\"" #name "\":";values(s.name)
    FIELD(phi);FIELD(n);FIELD(p);FIELD(Qn);FIELD(Qp);FIELD(P);FIELD(play);
#undef FIELD
    std::cout<<",\"bd\":[";for(size_t i=0;i<s.bd.size();++i){if(i)std::cout<<',';std::cout<<int(s.bd[i]);}
    std::cout<<"]}";
}
void result(const SimulationResult& r){
    std::cout<<"{\"converged\":"<<r.converged<<",\"iterations\":"<<r.iterations;
#define FIELD(name) std::cout<<",\"" #name "\":";values(r.name)
    FIELD(phi);FIELD(n);FIELD(p);FIELD(P);FIELD(Qn);FIELD(Qp);FIELD(temperature);
    FIELD(Jn_x);FIELD(Jn_y);FIELD(Jn_z);FIELD(Jp_x);FIELD(Jp_y);FIELD(Jp_z);
    FIELD(Jleak_x);FIELD(Jleak_y);FIELD(Jleak_z);
#undef FIELD
    std::cout<<'}';
}
bool same(const SimulationResult& a,const SimulationResult& b){
    return a.converged==b.converged && a.iterations==b.iterations && a.phi==b.phi &&
        a.n==b.n && a.p==b.p && a.P==b.P && a.Qn==b.Qn && a.Qp==b.Qp && a.temperature==b.temperature &&
        a.Jn_x==b.Jn_x && a.Jn_y==b.Jn_y && a.Jn_z==b.Jn_z &&
        a.Jp_x==b.Jp_x && a.Jp_y==b.Jp_y && a.Jp_z==b.Jp_z &&
        a.Jleak_x==b.Jleak_x && a.Jleak_y==b.Jleak_y && a.Jleak_z==b.Jleak_z;
}
std::unique_ptr<DeviceSimulator> device(int axis,bool quantum,bool newton,bool warm){
    size_t N=quantum?5:9;
    real_t length=quantum?TCAD_CONST(1e-7):TCAD_CONST(40e-9),d=length/(N-1);
    auto owned=std::make_unique<DeviceSimulator>(axis==0?N:1,axis==1?N:1,axis==2?N:1,
        axis==0?d:TCAD_CONST(1e-7),axis==1?d:TCAD_CONST(8e-8),axis==2?d:TCAD_CONST(6e-8));
    auto& s=*owned;
    s.set_use_newton(newton);s.set_gummel_max_iter(300);s.set_tolerance(TCAD_CONST(1e-11));
    s.set_thermal_voltage(TCAD_CONST(.02585));
    s.set_doping(Values(N,0));
    s.set_breakdown_enabled(true);
    s.set_breakdown_params(std::vector<char>(N,1),Values(N,quantum?TCAD_CONST(3e5):TCAD_CONST(2.5e8)),TCAD_CONST(.01));
    if(quantum){
        s.set_permittivity(Values(N,TCAD_CONST(1e-10)));
        s.set_mobility(Values(N,TCAD_CONST(.01)),Values(N,TCAD_CONST(.005)));
        s.set_effective_dos(Values(N,TCAD_CONST(1e21)),Values(N,TCAD_CONST(1e21)));
        s.set_bandgap(Values(N,0));
        s.set_doping({0,TCAD_CONST(1e19),TCAD_CONST(2e19),TCAD_CONST(1e19),0});
        s.set_electron_bc({{0,TCAD_CONST(1e21)},{N-1,TCAD_CONST(1e21)}});
        s.set_hole_bc({{0,TCAD_CONST(1e21)},{N-1,TCAD_CONST(1e21)}});
        s.set_quantum_enabled(true);s.set_density_gradient_potential_form(true);
        s.set_density_gradient_coefficients(TCAD_CONST(1e-18),TCAD_CONST(1e-18));
        s.set_thermal_coupling_enabled(true);s.set_thermal_conductivity(Values(N,TCAD_CONST(.001)));
        s.set_thermal_dirichlet({{0,300},{N-1,300}});
    }else{
        s.set_permittivity(Values(N,9*tcad::EPS0));s.set_mobility(Values(N,0),Values(N,0));
        s.set_effective_dos(Values(N,TCAD_CONST(2.8e25)),Values(N,TCAD_CONST(1.04e25)));
        s.set_bandgap(Values(N,6));s.set_electron_bc({{0,0},{N-1,0}});s.set_hole_bc({{0,0},{N-1,0}});
        s.set_ferroelectric_enabled(true);s.set_ferroelectric_polar_axis(axis);
        s.set_ferroelectric_params(std::vector<char>(N,1),TCAD_CONST(-5e8),TCAD_CONST(1.25e10));
        s.set_ferroelectric_model(2);s.set_ferroelectric_preisach(TCAD_CONST(.2),TCAD_CONST(1e8),TCAD_CONST(1e8));
        s.set_ferroelectric_nls(1,0,TCAD_CONST(.1));
    }
    if(warm){
        s.set_dirichlet_potential({{0,0},{N-1,quantum?TCAD_CONST(.02):TCAD_CONST(8.0)}});
        if(!s.solve().converged)throw std::runtime_error("warm seed rejected");
    }
    s.set_dirichlet_potential({{0,0},{N-1,quantum?TCAD_CONST(.04):TCAD_CONST(-12.0)}});
    return owned;
}
bool scenario(int axis,bool quantum,bool newton,bool warm){
    auto ref=device(axis,quantum,newton,warm);
    allocations=0;fail_at=0;armed=true;
    SimulationResult reference;
    try{reference=ref->solve();}catch(...){armed=false;throw;}
    armed=false;
    const size_t count=allocations;
    if(!reference.converged || count<8)throw std::runtime_error("reference rejected/too few allocations");
    const Snapshot expected(*ref);
    bool passed=true;
    for(int offset=0;offset<=8;++offset){
        auto s=device(axis,quantum,newton,warm);
        const Snapshot before(*s);
        allocations=0;fail_at=offset?count-offset+1:0;fired=false;armed=true;
        bool caught=false;
        SimulationResult returned;
        try{returned=s->solve();}catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
        armed=false;
        const Snapshot after(*s);
        const bool restored=after==before;
        // Optional row auditing can catch allocation errors itself and still
        // accept a fully solved physical point. An accepted return must commit
        // ALL fields; an exception/rejected return must preserve ALL old fields.
        const bool accepted=!caught && returned.converged;
        const bool atomic=accepted?after==expected:restored;
        auto retry=accepted?std::move(returned):s->solve();
        const Snapshot retried(*s);
        bool ok=(!offset || fired) && atomic && retry.converged && same(retry,reference) && retried==expected;
        passed=ok && passed;
        std::cout<<"{\"axis\":"<<axis<<",\"quantum\":"<<quantum<<",\"newton\":"<<newton<<",\"warm\":"<<warm
            <<",\"tail_offset\":"<<offset<<",\"total_allocations\":"<<count<<",\"failure_index\":"<<fail_at
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
    std::cout<<std::boolalpha<<'\n';
    bool passed=true;
    try{
        for(int axis=0;axis<3;++axis)
        for(bool quantum:{false,true})
        for(bool newton:{false,true}){
            if(quantum && newton)continue;
            for(bool warm:{false,true})passed=scenario(axis,quantum,newton,warm) && passed;
        }
    }catch(const std::exception& e){armed=false;std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return (passed || (argc==2 && std::string(argv[1])=="--observe"))?0:1;
}
