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
int trigger=0;size_t skip_allocations=0,matching_allocations=0;size_t observed_groups=0;std::string observed_role;bool observed_converged=false;
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
                const int role=trigger>=15?(trigger-15)%3:(trigger<=6?(trigger-1)%3:(trigger-8)%3);
                const char* target=role==0?"coarse":role==1?"fine_first":"fine_second";
                hit=t.role==target && (trigger<=6 || trigger>=15 || t.converged);
                if(hit && trigger>=15)hit=matching_allocations++>=skip_allocations;
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
    FIELD(lk_drive_field);FIELD(lk_polarization_increment);FIELD(lk_node_volumes);FIELD(lk_parameters);FIELD(lk_coarse_P);FIELD(lk_error_delta_P);FIELD(lk_coarse_phi);FIELD(lk_coarse_n);FIELD(lk_coarse_p);FIELD(lk_delta_phi);FIELD(lk_delta_n);FIELD(lk_delta_p);
    FIELD(D_x);FIELD(D_y);FIELD(D_z);FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);
    FIELD(electrode_voltages);FIELD(electrode_charges);FIELD(electrode_total_currents);
    FIELD(terminal_currents);FIELD(electrode_conduction_currents);FIELD(electrode_displacement_currents);
    FIELD(Jdielectric_x);FIELD(Jdielectric_y);FIELD(Jdielectric_z);FIELD(Jpolarization_x);FIELD(Jpolarization_y);FIELD(Jpolarization_z);
    FIELD(electrode_dielectric_currents);FIELD(electrode_polarization_currents);FIELD(electrode_charge_increments);
#undef FIELD
    std::cout<<",\"ledger\":";values({r.mobile_charge,r.poisson_residual});
    std::cout<<",\"fe_energy\":";values({r.lk_free_energy,r.lk_free_energy_increment,r.lk_dissipation,r.lk_field_work,r.lk_be_correction});
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
        FIELD(lk_drive_field);FIELD(lk_polarization_increment);FIELD(lk_node_volumes);FIELD(lk_parameters);FIELD(lk_coarse_P);FIELD(lk_error_delta_P);FIELD(lk_coarse_phi);FIELD(lk_coarse_n);FIELD(lk_coarse_p);FIELD(lk_delta_phi);FIELD(lk_delta_n);FIELD(lk_delta_p);
    FIELD(D_x);FIELD(D_y);FIELD(D_z);FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);
        FIELD(electrode_voltages);FIELD(electrode_charges);FIELD(electrode_total_currents);
    FIELD(terminal_currents);FIELD(electrode_conduction_currents);FIELD(electrode_displacement_currents);
    FIELD(Jdielectric_x);FIELD(Jdielectric_y);FIELD(Jdielectric_z);FIELD(Jpolarization_x);FIELD(Jpolarization_y);FIELD(Jpolarization_z);
        FIELD(electrode_dielectric_currents);FIELD(electrode_polarization_currents);FIELD(electrode_charge_increments);
#undef FIELD
    }return true;
}

constexpr real_t final_time=TCAD_CONST(2.5e-12);
bool accepted(const std::vector<SimulationResult>& h){return h.size()>=3 && h.back().time==final_time &&
    std::all_of(h.begin(),h.end(),[](const SimulationResult& r){return r.converged && !r.phi_frozen && !r.transient_majority_frozen && r.transient_charge_ledger_available;});}
void mobile_protocol(DeviceSimulator& s,size_t nx,size_t ny,size_t nz,bool reversal){
    std::map<size_t,Values> offsets;
    for(size_t k=0;k<nz;++k)for(size_t j=0;j<ny;++j){
        size_t i=nx-1+nx*(j+ny*k);
        offsets[i]={0,reversal?TCAD_CONST(-.002):TCAD_CONST(.001),reversal?TCAD_CONST(.0015):TCAD_CONST(-.001)};
    }
    s.set_transient_voltage_waveforms({0,TCAD_CONST(1e-12),final_time},offsets);
}
std::unique_ptr<DeviceSimulator> mobile_fe_device(int dimension,bool logarithmic,bool warm,bool nls){
    const size_t nx=dimension==1?5:3,ny=dimension>=2?3:1,nz=dimension==3?3:1,N=nx*ny*nz;
    const real_t scale=TCAD_CONST(1e20);
    auto s=std::make_unique<DeviceSimulator>(nx,ny,nz,TCAD_CONST(1e-7),TCAD_CONST(1.3e-7),TCAD_CONST(.8e-7));
    Values x(nx),y(ny),z(nz),eps(N),doping(N),n(N),p(N);
    for(size_t i=0;i<nx;++i)x[i]=i*TCAD_CONST(1e-7)*(1+TCAD_CONST(.1)*i);
    for(size_t i=0;i<ny;++i)y[i]=i*TCAD_CONST(1.3e-7)*(1+TCAD_CONST(.1)*i);
    for(size_t i=0;i<nz;++i)z[i]=i*TCAD_CONST(.8e-7)*(1+TCAD_CONST(.1)*i);
    s->set_grid_x(x);s->set_grid_y(y);s->set_grid_z(z);
    std::map<size_t,real_t> phi_bc,nbc,pbc;
    for(size_t k=0;k<nz;++k)for(size_t j=0;j<ny;++j)for(size_t i=0;i<nx;++i){
        size_t q=i+nx*(j+ny*k);
        bool contact=i==0 || i==nx-1;
        eps[q]=TCAD_CONST(11.7)*tcad::EPS0*(1+TCAD_CONST(.2)*j+TCAD_CONST(.3)*k);
        doping[q]=TCAD_CONST(.15)*scale*(1-TCAD_CONST(.4)*i);
        n[q]=scale*(1+TCAD_CONST(.08)*j*j+TCAD_CONST(.06)*k+(contact?0:TCAD_CONST(.5)));
        p[q]=scale*(1+TCAD_CONST(.04)*j+TCAD_CONST(.05)*k*k+(contact?0:TCAD_CONST(.2)));
        if(contact){phi_bc[q]=0;nbc[q]=n[q];pbc[q]=p[q];}
    }
    s->set_permittivity(eps);s->set_doping(doping);s->set_mobility(Values(N,TCAD_CONST(.1)),Values(N,TCAD_CONST(.05)));
    s->set_effective_dos(Values(N,scale),Values(N,scale));s->set_bandgap(Values(N,0));
    s->set_recombination(Values(N,TCAD_CONST(1e100)),Values(N,TCAD_CONST(1e100)));
    s->set_thermal_voltage(TCAD_CONST(.025852));s->set_newton_use_log_space(logarithmic);
    s->set_dirichlet_potential(phi_bc);s->set_electron_bc(nbc);s->set_hole_bc(pbc);s->set_initial_guess(Values(N,0),n,p);
    s->set_gummel_max_iter(100);s->set_tolerance(TCAD_CONST(1e-11));
    s->set_transient_dt(TCAD_CONST(1e-12));s->set_transient_t_final(final_time);s->set_nonlinear_history_enabled(true);
    s->set_ferroelectric_enabled(true);
    s->set_ferroelectric_params(std::vector<char>(N,1),TCAD_CONST(1e8),TCAD_CONST(1e12));
    s->set_ferroelectric_model(nls?2:0);s->set_ferroelectric_polar_axis(0);
    s->set_ferroelectric_preisach(TCAD_CONST(1e-6),TCAD_CONST(1e5),0);
    s->set_ferroelectric_nls(TCAD_CONST(1e-11),TCAD_CONST(2000.0),TCAD_CONST(1e-15));
    s->set_ferroelectric_builtin_field(TCAD_CONST(1000.0));
    s->set_ferroelectric_gamma(nls?0:TCAD_CONST(.1));
    s->set_transient_lk_coupled(!nls);s->set_transient_lk_material_field(false);
    if(!nls)s->set_transient_lk_substepping(true,TCAD_CONST(.8));
    if(warm){
        auto h=s->solve_transient();if(!accepted(h))throw std::runtime_error("mobile warm seed rejected");
        s->set_initial_guess(h.back().phi,h.back().n,h.back().p);
    }
    mobile_protocol(*s,nx,ny,nz,false);
    if(nls)s->set_transient_nls_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8),TCAD_CONST(1e-17),20);
    else {
        s->set_transient_lk_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-17),20);
        s->set_transient_lk_electrical_error_control(true,TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8));
    }
    return s;
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
bool returned_timeline_matches(const std::vector<SimulationResult>& states,
        const std::vector<tcad::TransientAttemptHistory>& groups){
    if(states.empty() || !states.front().initial_state || states.front().time!=0)return false;
    size_t index=1;real_t retained=0;
    for(const auto& g:groups)for(const auto& t:g.trials){
        if(t.retained!=(g.accepted && t.converged && t.role!="coarse"))return false;
        if(!t.retained)continue;
        if(index>=states.size())return false;
        const auto& r=states[index++];
        if(!r.converged || r.time!=t.end_time || r.accepted_dt!=t.step_dt ||
           t.start_time+t.step_dt!=t.end_time || t.samples.size()!=r.iterations)return false;
        retained+=t.step_dt;
    }
    if(index<states.size()){
        if(index+1!=states.size() || states.back().converged || states.back().accepted_dt!=0)return false;
        if(states.back().time!=states[index-1].time)return false;
        ++index;
    }
    return index==states.size() && retained==states.back().time;
}
bool mobile_fe_scenario(int dimension,bool logarithmic,bool warm,bool nls,int fault){
    auto s=mobile_fe_device(dimension,logarithmic,warm,nls),ref=mobile_fe_device(dimension,logarithmic,warm,nls);
    const Snapshot before(*s);std::vector<SimulationResult> returned;
    if(fault==-1)s->set_gummel_max_iter(0);
    observed_role.clear();observed_role.reserve(32);observed_converged=false;observed_groups=0;
    matching_allocations=0;skip_allocations=fault>=18?128:32;
    fired=false;trigger=fault;persistent=(fault>=4 && fault<=6) || (fault>=11 && fault<=14) || fault>=18;
    watched=s.get();armed=fault>0;
    bool caught=false;try{returned=s->solve_transient();}catch(const std::bad_alloc&){caught=true;}catch(...){armed=false;throw;}
    armed=false;watched=nullptr;const Snapshot after(*s);const auto diagnostic=s->transient_attempt_history();
    const auto returned_log=returned;
    const bool returned_timeline=!caught && returned_timeline_matches(returned,diagnostic);
    bool consistent=true;size_t retained=0,accepted_groups=0;
    for(const auto& g:diagnostic){accepted_groups+=g.accepted;for(const auto& t:g.trials)retained+=t.retained;}
    if(caught){
        consistent=!diagnostic.empty() && !accepted_groups && !retained && diagnostic.back().status=="exception" && diagnostic.back().stopping_reason=="exception";
        if(fault<=14 && fault!=7 && fault!=14)consistent=consistent && !diagnostic.back().trials.empty() && diagnostic.back().trials.back().exception;
    }
    bool rejected=fault==-1 && !returned.empty() && !returned.back().converged;
    if(fault==-1)s->set_gummel_max_iter(100);
    auto reference=ref->solve_transient();auto retry=fault?s->solve_transient():std::move(returned);
    const auto retry_trace=s->transient_attempt_history(),reference_trace=ref->transient_attempt_history();
    const Snapshot retry_state(*s),reference_state(*ref);
    bool equal=accepted(retry) && accepted(reference) && same(retry,reference) && retry_state==reference_state;
    bool dynamic=accepted(reference) && reference.front().n!=reference.back().n && reference.front().p!=reference.back().p &&
        std::any_of(reference.back().phi.begin(),reference.back().phi.end(),[](real_t v){return v!=0;});
    for(int a=0;a<dimension;++a){
        const auto& current=a==0?reference.back().Jn_x:a==1?reference.back().Jn_y:reference.back().Jn_z;
        dynamic=dynamic && std::any_of(current.begin(),current.end(),[](real_t v){return v!=0;});
    }
    size_t nx=dimension==1?5:3,ny=dimension>=2?3:1,nz=dimension==3?3:1;
    mobile_protocol(*s,nx,ny,nz,true);mobile_protocol(*ref,nx,ny,nz,true);
    auto reversal=s->solve_transient(),reference_reversal=ref->solve_transient();
    const Snapshot future_state(*s),future_reference_state(*ref);
    bool future=accepted(reversal) && same(reversal,reference_reversal) && future_state==future_reference_state;
    bool handled=fault>0 && fired && !caught && returned_timeline;
    dynamic=dynamic && reference.front().P!=reference.back().P;
    bool pass=equal && future && dynamic && (fault<0?(rejected && returned_timeline):!fault?returned_timeline:(fired && after==before && consistent && (caught || handled)));
    std::cout<<"{\"dimension\":"<<dimension<<",\"logarithmic\":"<<logarithmic<<",\"warm\":"<<warm<<",\"nls\":"<<nls<<",\"fault\":"<<fault
        <<",\"caught\":"<<caught<<",\"fired\":"<<fired<<",\"restored\":"<<(after==before)<<",\"trace_consistent\":"<<consistent
        <<",\"same_retry\":"<<equal<<",\"same_reversal\":"<<future<<",\"dynamic\":"<<dynamic<<",\"rejected\":"<<rejected
        <<",\"handled\":"<<handled<<",\"returned_timeline\":"<<returned_timeline<<",\"observed_groups\":"<<observed_groups<<",\"matching_allocations\":"<<matching_allocations<<",\"observed_role\":\""<<observed_role<<"\",\"observed_converged\":"<<observed_converged<<",\"passed\":"<<pass;
    std::cout<<",\"returned\":";history(returned_log);std::cout<<",\"before\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);std::cout<<",\"diagnostic\":";trace(diagnostic);
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
    bool smoke=argc==2 && std::string(argv[1])=="--smoke";
    try{for(int dimension=2;dimension<=3;++dimension)for(bool logarithmic:{false,true})for(bool warm:{false,true})for(bool nls:{false,true})
        for(int fault=smoke?0:-1;fault<=(smoke?0:14);++fault)
            passed=mobile_fe_scenario(dimension,logarithmic,warm,nls,fault) && passed;}
    catch(const std::exception& e){armed=false;std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return (passed || (argc==2 && std::string(argv[1])=="--observe"))?0:1;
}
