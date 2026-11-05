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
        <<",\"lk_coupled\":"<<r.lk_coupled<<",\"lk_material_field\":"<<r.lk_material_field
        <<",\"nls_error_control\":"<<r.nls_error_control<<",\"lk_error_control\":"<<r.lk_error_control<<",\"lk_substepping\":"<<r.lk_substepping
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
    if(states.empty() || !states.front().initial_state || states.front().time<0)return false;
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
    return index==states.size() && tcad::abs_q(retained-(states.back().time-states.front().time))<=TCAD_CONST(1e-30)*final_time;
}
std::unique_ptr<DeviceSimulator> material_mobile_device(int dimension,bool logarithmic,bool warm,bool natural){
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
        doping[q]=contact?0:TCAD_CONST(.15)*scale*(1-TCAD_CONST(.4)*i);
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
    s->set_ferroelectric_model(0);s->set_ferroelectric_polar_axis(0);
    s->set_ferroelectric_preisach(TCAD_CONST(1e-6),TCAD_CONST(1e5),0);
    s->set_ferroelectric_builtin_field(TCAD_CONST(1000.0));
    s->set_ferroelectric_gamma(TCAD_CONST(.1));
    s->set_transient_lk_coupled(true);s->set_transient_lk_material_field(true);
    if(natural)s->set_transient_lk_zero_d_faces(dimension==3?"yYzZ":"yY");
    s->set_transient_lk_substepping(true,TCAD_CONST(.8));
    if(warm){
        auto h=s->solve_transient();if(!accepted(h))throw std::runtime_error("mobile warm seed rejected");
        s->set_initial_guess(h.back().phi,h.back().n,h.back().p);
    }
    mobile_protocol(*s,nx,ny,nz,false);
    s->set_transient_lk_error_control(true,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-17),20);
    s->set_transient_lk_electrical_error_control(true,TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8));
    return s;
}

std::unique_ptr<DeviceSimulator> fixture(int dimension,bool logarithmic,int mode){
    if(mode==1 || mode==3)return material_mobile_device(dimension,logarithmic,false,mode==3);
    return mobile_fe_device(dimension,logarithmic,false,mode==2);
}
void seed(DeviceSimulator& s,const SimulationResult& r,const Values& play,int mode,real_t start){
    s.set_initial_guess(r.phi,r.n,r.p);
    if(mode==2)s.set_ferroelectric_ensemble_history(r.P,play);
    else s.set_ferroelectric_history(r.P);
    s.set_transient_start_time(start);
}

std::unique_ptr<DeviceSimulator> fixed_fixture(int dimension,bool log,int mode,int level){
    auto s=fixture(dimension,log,mode);
    s->set_transient_lk_electrical_error_control(false,TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8));
    s->set_transient_lk_error_control(false,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-17),20);
    s->set_transient_nls_error_control(false,TCAD_CONST(.01),TCAD_CONST(1e-8),TCAD_CONST(1e-5),TCAD_CONST(.01),TCAD_CONST(1e8),TCAD_CONST(1e-17),20);
    s->set_transient_lk_substepping(false,TCAD_CONST(.8));
    s->set_transient_dt(TCAD_CONST(1e-12)/(4*(1u<<level)));
    return s;
}
bool convergence(int dimension,bool log,int mode,int level){
    auto s=fixed_fixture(dimension,log,mode,level);
    const Snapshot before(*s);const auto full=s->solve_transient();const auto full_trace=s->transient_attempt_history();const Snapshot after(*s);
    if(!accepted(full) || full.size()!=10*(1u<<level)+1)throw std::runtime_error("fixed full grid incomplete");
    bool passed=returned_timeline_matches(full,full_trace) && after.phi==before.phi && after.n==before.n && after.p==before.p;
    std::cout<<"{\"dimension\":"<<dimension<<",\"logarithmic\":"<<log<<",\"mode\":"<<mode<<",\"nls\":"<<(mode==2)<<",\"natural\":"<<(mode==3)<<",\"level\":"<<level;
    std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(full_trace);
    std::cout<<",\"segments\":[";
    for(int cut_index:{0,1}){
        const size_t index=(cut_index?3:4)*(1u<<level);const real_t cut=full[index].time;
        auto prefix_sim=fixed_fixture(dimension,log,mode,level),tail_sim=fixed_fixture(dimension,log,mode,level);
        prefix_sim->set_transient_t_final(cut);
        const auto prefix=prefix_sim->solve_transient();const auto prefix_trace=prefix_sim->transient_attempt_history();const Snapshot prefix_state(*prefix_sim);
        if(prefix.size()!=index+1 || !prefix.back().converged || prefix.back().time!=cut)throw std::runtime_error("fixed prefix incomplete");
        seed(*tail_sim,prefix.back(),prefix_state.play,mode,cut);const Snapshot entry(*tail_sim);
        const auto tail=tail_sim->solve_transient();const auto tail_trace=tail_sim->transient_attempt_history();const Snapshot final_state(*tail_sim);
        bool good=accepted(tail) && tail.size()+index==full.size() && returned_timeline_matches(prefix,prefix_trace) && returned_timeline_matches(tail,tail_trace) &&
            tail.front().P==prefix.back().P && entry.P==prefix.back().P && final_state.P==tail.back().P && final_state.phi==entry.phi && final_state.n==entry.n && final_state.p==entry.p &&
            entry.contacts==before.contacts && final_state.contacts==before.contacts && tail.back().n!=tail.front().n && tail.back().p!=tail.front().p && tail.back().P!=tail.front().P;
        passed=passed && good;
        if(cut_index)std::cout<<',';
        std::cout<<"{\"cut_index\":"<<cut_index<<",\"index\":"<<index<<",\"passed\":"<<good;
        std::cout<<",\"prefix\":";history(prefix);std::cout<<",\"prefix_trace\":";trace(prefix_trace);
        std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tail_trace);
        std::cout<<",\"entry\":";snapshot(entry);std::cout<<",\"after\":";snapshot(final_state);std::cout<<'}';
    }
    std::cout<<"],\"passed\":"<<passed<<"}"<<std::endl;return passed;
}
}
int main(){
    bool passed=true;
    try{for(int d:{2,3})for(bool log:{false,true})for(int mode:{0,1,2,3})for(int level:{0,1,2})passed=convergence(d,log,mode,level)&&passed;}
    catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return passed?0:1;
}
