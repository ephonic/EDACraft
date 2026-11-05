// Read-only private-state observation uses -fno-access-control on this test
// translation unit only. All fixture changes use the public native API.
#include "device_simulator.h"
#include <algorithm>
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
bool armed=false,fired=false,persistent=false;
int trigger=0;size_t allocations=0,fail_at=0;
const DeviceSimulator* watched=nullptr;
const Values* entered_P=nullptr;const Values* entered_play=nullptr;
void* allocate(size_t size){
    if(watched)++allocations;
    if(armed){
        const bool changed=trigger==5 ? allocations==fail_at :
            trigger==2 ? watched->ferroelectric_play_history()!=*entered_play :
            trigger==4 ? watched->transient_attempt_history().size()>1 && watched->transient_attempt_history().front().accepted :
            watched->fe_polarization()!=*entered_P;
        if((persistent && fired) || changed){
            fired=true;if(!persistent)armed=false;throw std::bad_alloc();
        }
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
    std::map<size_t,real_t> contacts;
    std::vector<char> bd;
    real_t dt;
    bool guess,fe_init,bd_init;
    explicit Snapshot(const DeviceSimulator& s):phi(s.init_phi_),n(s.init_n_),p(s.init_p_),
        mobility(s.mobility_temperature_),previous(s.lattice_previous_temperature_),capacity(s.lattice_heat_capacity_),
        Qn(s.dg_transport_Qn_),Qp(s.dg_transport_Qp_),P(s.fe_polarization()),play(s.ferroelectric_play_history()),
        contacts(s.phi_bc_),bd(s.breakdown_state()),dt(s.lattice_dt_),guess(s.has_initial_guess_),fe_init(s.fe_polarization_init_),bd_init(s.bd_state_init_){}
    bool operator==(const Snapshot& b)const{
        return contacts==b.contacts && phi==b.phi && n==b.n && p==b.p && mobility==b.mobility && previous==b.previous &&
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
    Values bc;for(const auto& x:s.contacts){bc.push_back(x.first);bc.push_back(x.second);}
    std::cout<<",\"contacts\":";values(bc);
    std::cout<<",\"bd\":[";for(size_t i=0;i<s.bd.size();++i){if(i)std::cout<<',';std::cout<<int(s.bd[i]);}std::cout<<"]}";
}
void result(const SimulationResult& r){
    std::cout<<"{\"converged\":"<<r.converged<<",\"iterations\":"<<r.iterations
        <<",\"initial\":"<<r.initial_state<<",\"displacement_available\":"<<r.displacement_current_available;
#define FIELD(name) std::cout<<",\"" #name "\":";values(r.name)
    FIELD(phi);FIELD(n);FIELD(p);FIELD(P);FIELD(Ex);FIELD(Ey);FIELD(Ez);FIELD(Qn);FIELD(Qp);FIELD(temperature);
    FIELD(Jn_x);FIELD(Jn_y);FIELD(Jn_z);FIELD(Jp_x);FIELD(Jp_y);FIELD(Jp_z);
    FIELD(D_x);FIELD(D_y);FIELD(D_z);FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);
    FIELD(electrode_voltages);FIELD(electrode_charges);FIELD(electrode_total_currents);
    FIELD(electrode_dielectric_currents);FIELD(electrode_polarization_currents);FIELD(electrode_charge_increments);
#undef FIELD
    std::cout<<",\"clock\":";values({r.time,r.attempted_time,r.accepted_dt});std::cout<<'}';
}
void history(const std::vector<SimulationResult>& h){
    std::cout<<'[';for(size_t i=0;i<h.size();++i){if(i)std::cout<<',';result(h[i]);}std::cout<<']';
}
bool same(const std::vector<SimulationResult>& a,const std::vector<SimulationResult>& b){
    if(a.size()!=b.size())return false;
    for(size_t i=0;i<a.size();++i){const auto& x=a[i];const auto& y=b[i];
        if(x.converged!=y.converged || x.iterations!=y.iterations || x.initial_state!=y.initial_state ||
           x.time!=y.time || x.attempted_time!=y.attempted_time || x.accepted_dt!=y.accepted_dt)return false;
#define FIELD(n) if(x.n!=y.n)return false
        FIELD(phi);FIELD(n);FIELD(p);FIELD(P);FIELD(Ex);FIELD(Ey);FIELD(Ez);FIELD(Qn);FIELD(Qp);FIELD(temperature);
        FIELD(Jn_x);FIELD(Jn_y);FIELD(Jn_z);FIELD(Jp_x);FIELD(Jp_y);FIELD(Jp_z);
        FIELD(D_x);FIELD(D_y);FIELD(D_z);FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);
        FIELD(electrode_voltages);FIELD(electrode_charges);FIELD(electrode_total_currents);
        FIELD(electrode_dielectric_currents);FIELD(electrode_polarization_currents);FIELD(electrode_charge_increments);
#undef FIELD
    }return true;
}
bool accepted(const std::vector<SimulationResult>& h){return h.size()==4 && h.back().time==TCAD_CONST(2.5e-10) &&
    std::all_of(h.begin(),h.end(),[](const SimulationResult& r){return r.converged;});}
void protocol(DeviceSimulator& s,bool reversal){
    s.set_transient_voltage_waveforms({0,TCAD_CONST(1e-10),TCAD_CONST(2.5e-10)},
        {{8,{0,reversal?TCAD_CONST(-.02):TCAD_CONST(.005),reversal?TCAD_CONST(.015):TCAD_CONST(-.015)}}});
}
std::unique_ptr<DeviceSimulator> device(int axis,int model,bool warm,bool diagnostics){
    const size_t N=9;const real_t d=TCAD_CONST(1e-8);
    auto owned=std::make_unique<DeviceSimulator>(axis==0?N:1,axis==1?N:1,axis==2?N:1,
        axis==0?d:TCAD_CONST(2e-7),axis==1?d:TCAD_CONST(3e-7),axis==2?d:TCAD_CONST(4e-7));
    auto& s=*owned;
    s.set_permittivity(Values(N,20*tcad::EPS0));s.set_mobility(Values(N,0),Values(N,0));
    s.set_doping(Values(N,0));s.set_effective_dos(Values(N,TCAD_CONST(1e16)),Values(N,TCAD_CONST(1e16)));s.set_bandgap(Values(N,6));
    s.set_initial_guess(Values(N,0),Values(N,0),Values(N,0));
    s.set_recombination(Values(N,TCAD_CONST(1e100)),Values(N,TCAD_CONST(1e100)));
    s.set_dirichlet_potential({{0,0},{N-1,TCAD_CONST(-.01)}});
    s.set_ferroelectric_enabled(true);s.set_ferroelectric_params(std::vector<char>(N,1),TCAD_CONST(-1e8),TCAD_CONST(1e12));
    s.set_ferroelectric_model(model);s.set_ferroelectric_preisach(TCAD_CONST(1e-6),TCAD_CONST(1e5),0);
    s.set_ferroelectric_nls(TCAD_CONST(1e-9),0,TCAD_CONST(1e-15));s.set_ferroelectric_gamma(model==0?TCAD_CONST(.1):0);
    s.set_ferroelectric_polar_axis(axis);s.set_transient_lk_coupled(false);
    s.set_gummel_max_iter(80);s.set_tolerance(TCAD_CONST(1e-11));
    s.set_transient_dt(TCAD_CONST(1e-10));s.set_transient_t_final(TCAD_CONST(2.5e-10));
    s.set_nonlinear_history_enabled(diagnostics);
    if(warm && !accepted(s.solve_transient()))throw std::runtime_error("warm seed rejected");
    protocol(s,false);return owned;
}
bool scenario(int axis,int model,bool warm,bool diagnostics,int fault){
    auto s=device(axis,model,warm,diagnostics),ref=device(axis,model,warm,diagnostics);
    const Snapshot before(*s);std::vector<SimulationResult> returned;
    fired=false;trigger=fault;persistent=fault==3;watched=s.get();entered_P=&before.P;entered_play=&before.play;
    armed=fault!=0;bool caught=false;
    try{returned=s->solve_transient();}catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
    armed=false;watched=nullptr;
    const Snapshot after(*s);const bool restored=after==before;
    auto reference=ref->solve_transient();auto retry=fault?s->solve_transient():std::move(returned);
    const Snapshot retry_state(*s),reference_state(*ref);
    const bool equal=accepted(retry) && accepted(reference) && same(retry,reference) && retry_state==reference_state;
    protocol(*s,true);protocol(*ref,true);auto reversal=s->solve_transient(),reference_reversal=ref->solve_transient();
    const Snapshot future_state(*s),future_reference_state(*ref);
    const bool future=accepted(reversal) && same(reversal,reference_reversal) && future_state==future_reference_state;
    const bool pass=equal && future && (!fault || (caught && fired && restored));
    std::cout<<"{\"axis\":"<<axis<<",\"model\":"<<model<<",\"warm\":"<<warm<<",\"diagnostics\":"<<diagnostics
        <<",\"fault\":"<<fault<<",\"caught\":"<<caught<<",\"fired\":"<<fired<<",\"restored\":"<<restored
        <<",\"same_retry\":"<<equal<<",\"same_reversal\":"<<future<<",\"passed\":"<<pass;
    std::cout<<",\"before\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);
    std::cout<<",\"retry_state\":";snapshot(retry_state);std::cout<<",\"reference_state\":";snapshot(reference_state);
    std::cout<<",\"future_state\":";snapshot(future_state);std::cout<<",\"future_reference_state\":";snapshot(future_reference_state);
    std::cout<<",\"retry\":";history(retry);std::cout<<",\"reference\":";history(reference);
    std::cout<<",\"reversal\":";history(reversal);std::cout<<",\"reference_reversal\":";history(reference_reversal);std::cout<<"}\n";
    return pass;
}
bool disabled_scenario(int axis,bool diagnostics){
    auto make=[&](){auto s=device(axis,3,true,diagnostics);s->set_ferroelectric_enabled(false);return s;};
    auto ref=make();const Snapshot before_ref(*ref);
    allocations=0;watched=ref.get();auto reference=ref->solve_transient();watched=nullptr;
    const size_t count=allocations;const Snapshot expected(*ref);
    if(!accepted(reference) || !(expected==before_ref) || count<4)throw std::runtime_error("disabled FE control rejected");
    bool passed=true;
    for(int fault=0;fault<=4;++fault){
        auto s=make();const Snapshot before(*s);std::vector<SimulationResult> returned;
        allocations=0;trigger=5;fail_at=count+1-fault;persistent=false;fired=false;watched=s.get();armed=fault!=0;
        bool caught=false;try{returned=s->solve_transient();}catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
        armed=false;watched=nullptr;const Snapshot after(*s);
        auto retry=fault?s->solve_transient():std::move(returned);const Snapshot retry_state(*s);
        // Re-enable FE to observe the retained branch memory via the solver.
        auto future=make();s->set_ferroelectric_enabled(true);future->set_ferroelectric_enabled(true);
        protocol(*s,true);protocol(*future,true);auto reversal=s->solve_transient(),reference_reversal=future->solve_transient();
        const Snapshot future_state(*s),future_reference_state(*future);
        const bool equal=accepted(retry) && same(retry,reference) && retry_state==expected;
        const bool same_future=accepted(reversal) && same(reversal,reference_reversal) && future_state==future_reference_state;
        const bool restored=after==before,pass=restored && equal && same_future && (!fault || (fired && caught));passed=pass && passed;
        std::cout<<"{\"axis\":"<<axis<<",\"model\":-1,\"warm\":true,\"diagnostics\":"<<diagnostics
            <<",\"fault\":"<<fault<<",\"allocation\":"<<fail_at<<",\"caught\":"<<caught<<",\"fired\":"<<fired
            <<",\"restored\":"<<restored<<",\"same_retry\":"<<equal<<",\"same_reversal\":"<<same_future<<",\"passed\":"<<pass;
        std::cout<<",\"before\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);
        std::cout<<",\"retry_state\":";snapshot(retry_state);std::cout<<",\"reference_state\":";snapshot(expected);
        std::cout<<",\"future_state\":";snapshot(future_state);std::cout<<",\"future_reference_state\":";snapshot(future_reference_state);
        std::cout<<",\"retry\":";history(retry);std::cout<<",\"reference\":";history(reference);
        std::cout<<",\"reversal\":";history(reversal);std::cout<<",\"reference_reversal\":";history(reference_reversal);std::cout<<"}\n";
    }return passed;
}
}
int main(int argc,char** argv){
    std::cout<<std::boolalpha<<'\n';bool passed=true;
    try{for(int axis=0;axis<3;++axis)for(int model=0;model<4;++model)for(bool warm:{false,true})for(bool diagnostic:{false,true})
        for(int fault:{0,1,2,3,4}){
            if(fault==2 && model!=1 && model!=3)continue;
            if(fault==4 && !diagnostic)continue;
            passed=scenario(axis,model,warm,diagnostic,fault) && passed;
        }
        for(int axis=0;axis<3;++axis)for(bool diagnostic:{false,true})passed=disabled_scenario(axis,diagnostic) && passed;
    }
    catch(const std::exception& e){armed=false;std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return (passed || (argc==2 && std::string(argv[1])=="--observe"))?0:1;
}
