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
int trigger=0;size_t observed_groups=0;std::string observed_role;bool observed_converged=false;
const DeviceSimulator* watched=nullptr;
void* allocate(size_t size){
    if(armed){
        bool hit=persistent && fired;
        const auto& groups=watched->transient_attempt_history();
        if(!hit && !groups.empty()){
            const auto& g=groups.back();
            if(trigger==7 || trigger==14){for(const auto& prior:groups)hit=hit || prior.accepted;hit=hit && groups.size()>1;}
            else if(!g.trials.empty()){
                const auto& t=g.trials.back();
                const int role=(trigger<=6?(trigger-1)%3:(trigger-8)%3);
                const char* target=role==0?"coarse":role==1?"fine_first":"fine_second";
                hit=t.role==target && (trigger<=6 || t.converged);
            }
            if(hit && !fired){
                observed_groups=groups.size();
                // No allocation in the observer. Role strings fit the caller's
                // reserved buffer, including under persistent exhaustion.
                if(!g.trials.empty()){observed_role=g.trials.back().role;observed_converged=g.trials.back().converged;}
            }
        }
        if(hit){fired=true;if(!persistent)armed=false;throw std::bad_alloc();}
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
    FIELD(lk_coarse_P);FIELD(lk_error_delta_P);FIELD(lk_coarse_phi);FIELD(lk_coarse_n);FIELD(lk_coarse_p);FIELD(lk_delta_phi);FIELD(lk_delta_n);FIELD(lk_delta_p);
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
        FIELD(lk_coarse_P);FIELD(lk_error_delta_P);FIELD(lk_coarse_phi);FIELD(lk_coarse_n);FIELD(lk_coarse_p);FIELD(lk_delta_phi);FIELD(lk_delta_n);FIELD(lk_delta_p);
    FIELD(D_x);FIELD(D_y);FIELD(D_z);FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);
        FIELD(electrode_voltages);FIELD(electrode_charges);FIELD(electrode_total_currents);
        FIELD(electrode_dielectric_currents);FIELD(electrode_polarization_currents);FIELD(electrode_charge_increments);
#undef FIELD
    }return true;
}
bool accepted(const std::vector<SimulationResult>& h){return h.size()>=3 && h.back().time==TCAD_CONST(2.5e-10) &&
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
void configure(DeviceSimulator& s,int controller){
    if(controller==0){
        s.set_ferroelectric_enabled(false);s.set_ferroelectric_gamma(0);
        s.set_transient_electrical_error_control(true,TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8),TCAD_CONST(1e-15),20);
    }else if(controller==1){
        s.set_transient_nls_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-5),TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8),TCAD_CONST(1e-15),20);
    }else{
        s.set_transient_lk_coupled(true);s.set_transient_lk_material_field(controller==3);
        s.set_transient_lk_substepping(true,TCAD_CONST(.8));
        s.set_transient_lk_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-5),TCAD_CONST(1e-15),20);
        s.set_transient_lk_electrical_error_control(true,TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8));
    }
}
void trace(const std::vector<tcad::TransientAttemptHistory>& groups){
    std::cout<<'[';
    for(size_t i=0;i<groups.size();++i){if(i)std::cout<<',';const auto& g=groups[i];
        std::cout<<"{\"status\":\""<<g.status<<"\",\"reason\":\""<<g.stopping_reason<<"\",\"accepted\":"<<g.accepted
            <<",\"retry\":"<<g.retry_index<<",\"estimate\":"<<g.error_estimate_available<<",\"clock\":";
        values({g.start_time,g.end_time,g.step_dt});
        std::cout<<",\"ratios\":";values({g.polarization_error_ratio,g.electrical_error_ratio,g.exported_polarization_error_ratio,g.exported_electrical_error_ratio});
        std::cout<<",\"trials\":[";
        for(size_t j=0;j<g.trials.size();++j){if(j)std::cout<<',';const auto& t=g.trials[j];
            std::cout<<"{\"role\":\""<<t.role<<"\",\"solver\":\""<<t.solver<<"\",\"called\":"<<t.solver_called
                <<",\"converged\":"<<t.converged<<",\"retained\":"<<t.retained<<",\"exception\":"<<t.exception<<",\"clock\":";
            values({t.start_time,t.end_time,t.step_dt});std::cout<<",\"samples\":[";
            for(size_t k=0;k<t.samples.size();++k){if(k)std::cout<<',';values(t.samples[k]);}std::cout<<"]}";
        }std::cout<<"]}";
    }std::cout<<']';
}
bool scenario(int axis,int controller,bool warm,int fault){
    const int model=controller==1?2:0;
    auto s=device(axis,model,warm,true),ref=device(axis,model,warm,true);
    configure(*s,controller);configure(*ref,controller);
    const Snapshot before(*s);std::vector<SimulationResult> returned;
    if(fault==-1)s->set_gummel_max_iter(0);
    observed_role.clear();observed_role.reserve(32);observed_converged=false;observed_groups=0;
    fired=false;trigger=fault;persistent=(fault>=4 && fault<=6) || fault>=11;watched=s.get();armed=fault>0;
    bool caught=false;try{returned=s->solve_transient();}catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
    armed=false;watched=nullptr;const Snapshot after(*s);const auto diagnostic=s->transient_attempt_history();
    const bool restored=after==before;
    bool consistent=true;size_t retained=0,accepted_groups=0;
    for(const auto& g:diagnostic){accepted_groups+=g.accepted;for(const auto& t:g.trials)retained+=t.retained;}
    if(caught){
        consistent=!diagnostic.empty() && !accepted_groups && !retained && diagnostic.back().status=="exception" && diagnostic.back().stopping_reason=="exception";
        if(fault!=7 && fault!=14)consistent=consistent && !diagnostic.back().trials.empty() && diagnostic.back().trials.back().exception;
    }
    const bool rejected=fault==-1 && !returned.empty() && !returned.back().converged;
    const bool prefix_matches=!rejected || controller==0 || after.P==returned.back().P;
    if(fault==-1)s->set_gummel_max_iter(80);
    auto reference=ref->solve_transient();const auto reference_trace=ref->transient_attempt_history();
    auto retry=fault?s->solve_transient():std::move(returned);const auto retry_trace=s->transient_attempt_history();
    const Snapshot retry_state(*s),reference_state(*ref);
    const bool equal=accepted(retry) && accepted(reference) && same(retry,reference) && retry_state==reference_state;
    protocol(*s,true);protocol(*ref,true);auto reversal=s->solve_transient(),reference_reversal=ref->solve_transient();
    const Snapshot future_state(*s),future_reference_state(*ref);
    const bool future=accepted(reversal) && same(reversal,reference_reversal) && future_state==future_reference_state;
    const bool pass=equal && future && prefix_matches && (fault<0?rejected:!fault || (fired && caught && restored && consistent));
    std::cout<<"{\"axis\":"<<axis<<",\"controller\":"<<controller<<",\"warm\":"<<warm<<",\"fault\":"<<fault
        <<",\"caught\":"<<caught<<",\"fired\":"<<fired<<",\"restored\":"<<restored<<",\"trace_consistent\":"<<consistent
        <<",\"same_retry\":"<<equal<<",\"same_reversal\":"<<future<<",\"rejected\":"<<rejected<<",\"prefix_matches\":"<<prefix_matches
        <<",\"observed_groups\":"<<observed_groups<<",\"observed_role\":\""<<observed_role<<"\",\"observed_converged\":"<<observed_converged<<",\"passed\":"<<pass;
    std::cout<<",\"before\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);std::cout<<",\"diagnostic\":";trace(diagnostic);
    std::cout<<",\"retry_trace\":";trace(retry_trace);std::cout<<",\"reference_trace\":";trace(reference_trace);
    std::cout<<",\"retry_state\":";snapshot(retry_state);std::cout<<",\"reference_state\":";snapshot(reference_state);
    std::cout<<",\"future_state\":";snapshot(future_state);std::cout<<",\"future_reference_state\":";snapshot(future_reference_state);
    std::cout<<",\"retry\":";history(retry);std::cout<<",\"reference\":";history(reference);
    std::cout<<",\"reversal\":";history(reversal);std::cout<<",\"reference_reversal\":";history(reference_reversal);std::cout<<"}\n";
    return pass;
}
}
int main(int argc,char** argv){
    std::cout<<std::boolalpha<<'\n';bool passed=true;
    try{for(int axis=0;axis<3;++axis)for(int controller=0;controller<4;++controller)for(bool warm:{false,true})for(int fault=-1;fault<=14;++fault)
        passed=scenario(axis,controller,warm,fault) && passed;}
    catch(const std::exception& e){armed=false;std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return (passed || (argc==2 && std::string(argv[1])=="--observe"))?0:1;
}
