// Exercise the public double adapter independently of Cython. All fixture
// geometry, pulse times and voltages are dyadic; no private access is used.
#include "device_simulator_double.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
using tcad::DeviceSimulatorDouble;
using V=std::vector<double>;
constexpr double T=0x1p-40,B=0x1p-25,S=0x1p66,PS=0x1p-20;
double width(int f){return f?0x1p-66:0x1p-60;}
double voltage(double t,int protocol){
 if(protocol){if(t<=T)return 0x1p-13*t/T;if(t<=1.5*T)return 0x1p-13;if(t<=2*T)return 0x1p-13+(0x1p-10-0x1p-13)*(t-1.5*T)/(.5*T);}
 return t<=2*T?0x1p-10*t/(2*T):0x1p-10-0x1p-9*(t-2*T)/(2*T);
}
std::unique_ptr<DeviceSimulatorDouble> fixture(int dim,bool log,int family,int protocol,int level,bool manual){
 const size_t nz=dim==3?3:1,N=9*nz;
 auto s=std::make_unique<DeviceSimulatorDouble>(3,3,nz,B,B,B);
 s->set_x_positions({0,3*B,8*B});s->set_y_positions({0,5*B,11*B});if(dim==3)s->set_z_positions({0,2*B,7*B});
 V eps(N),doping(N),n(N),p(N);std::map<size_t,double> bc,nbc,pbc;
 for(size_t k=0;k<nz;++k)for(size_t j=0;j<3;++j)for(size_t i=0;i<3;++i){
  const size_t q=i+3*(j+3*k);bool contact=i!=1;
  eps[q]=0x1p-33*(1+j*.25+k*.5);doping[q]=S*(.125-i*.03125);
  n[q]=S*(1+j*.0625+k*.03125+(contact?0:.5));p[q]=S*(1+j*.03125+k*.0625+(contact?0:.25));
  if(contact){bc[q]=0;nbc[q]=n[q];pbc[q]=p[q];}
 }
 s->set_permittivity(eps);s->set_doping(doping);s->set_mobility(V(N,.125),V(N,.0625));s->set_effective_dos(V(N,S),V(N,S));s->set_bandgap(V(N,0));
 s->set_recombination(V(N,1e100),V(N,1e100));s->set_thermal_voltage(.03125);s->set_newton_use_log_space(log);
 s->set_dirichlet_potential(bc);s->set_electron_bc(nbc);s->set_hole_bc(pbc);s->set_initial_guess(V(N,0),n,p);
 s->set_gummel_max_iter(100);s->set_tolerance(1e-11);s->set_transient_dt(.5*T/(1<<level));s->set_transient_t_final(4*T);s->set_nonlinear_history_enabled(true);
 s->set_ferroelectric_enabled(true);s->set_ferroelectric_params(std::vector<signed char>(N,1),1e8,1e12);s->set_ferroelectric_model(2);s->set_ferroelectric_polar_axis(0);
 s->set_ferroelectric_preisach(PS,1e5,0);s->set_ferroelectric_nls(0x1p-36,2048,0x1p-50);s->set_ferroelectric_builtin_field(-512);s->set_ferroelectric_gamma(0);s->set_transient_lk_coupled(false);
 V times;for(int i=0;i<=16;++i)times.push_back(i*T/4);times.push_back(2.875*T);
 if(manual){V events=protocol?V{T-width(family),1.5*T+width(family),2.875*T-width(family),2.875*T+width(family)}:V{.25*T-width(family),.25*T+width(family),2.875*T-width(family),2.875*T+width(family)};times.insert(times.end(),events.begin(),events.end());}
 std::sort(times.begin(),times.end());times.erase(std::unique(times.begin(),times.end()),times.end());V volts;for(double t:times)volts.push_back(voltage(t,protocol));std::map<size_t,V> offsets;
 for(size_t k=0;k<nz;++k)for(size_t j=0;j<3;++j)offsets[2+3*(j+3*k)]=volts;
 s->set_transient_voltage_waveforms(times,offsets);s->set_transient_nls_event_control(!manual,width(family));return s;
}
void values(const V& a){std::cout<<'[';for(size_t i=0;i<a.size();++i){if(i)std::cout<<',';std::cout<<a[i];}std::cout<<']';}
void history(const std::vector<tcad::TransientResultDouble>& h){std::cout<<'[';for(size_t i=0;i<h.size();++i){if(i)std::cout<<',';const auto& r=h[i];
 std::cout<<"{\"time_s\":"<<r.time<<",\"attempted_time_s\":"<<r.attempted_time<<",\"dt_s\":"<<r.accepted_dt<<",\"valid\":"<<r.converged<<",\"initial_state\":"<<r.initial_state<<",\"iterations\":"<<r.iterations;
#define FIELD(name) std::cout<<",\"" #name "\":";values(r.name)
 FIELD(phi);FIELD(n);FIELD(p);FIELD(P);FIELD(Ex);FIELD(Ey);FIELD(Ez);FIELD(Jn_x);FIELD(Jn_y);FIELD(Jn_z);FIELD(Jp_x);FIELD(Jp_y);FIELD(Jp_z);
 if(r.electrostatic_flux_available){FIELD(D_x);FIELD(D_y);FIELD(D_z);}
 if(r.displacement_current_available){FIELD(Jdisp_x);FIELD(Jdisp_y);FIELD(Jdisp_z);FIELD(Jdielectric_x);FIELD(Jdielectric_y);FIELD(Jdielectric_z);FIELD(Jpolarization_x);FIELD(Jpolarization_y);FIELD(Jpolarization_z);}
#undef FIELD
#define NAMED(key,name) std::cout<<",\"" key "\":";values(r.name)
 if(r.charge_ledger_available){NAMED("terminal_currents_A",terminal_currents);std::cout<<",\"stored_charge_C\":"<<r.mobile_charge;}
 if(r.electrode_charge_available){NAMED("electrode_charges_C",electrode_charges);NAMED("electrode_voltages_V",electrode_voltages);}
 if(r.total_terminal_current_available){NAMED("electrode_total_currents_A",electrode_total_currents);NAMED("electrode_displacement_currents_A",electrode_displacement_currents);NAMED("electrode_conduction_currents_A",electrode_conduction_currents);NAMED("electrode_dielectric_currents_A",electrode_dielectric_currents);NAMED("electrode_polarization_currents_A",electrode_polarization_currents);NAMED("electrode_charge_increments_C",electrode_charge_increments);}
#undef NAMED
#define FLAG(name) std::cout<<",\"" #name "\":"<<r.name
 FLAG(charge_ledger_available);FLAG(electrostatic_flux_available);FLAG(displacement_current_available);FLAG(electrode_charge_available);FLAG(total_terminal_current_available);
#undef FLAG
 std::cout<<'}';}std::cout<<']';}
void trace(const std::vector<tcad::TransientAttemptHistoryDouble>& h){std::cout<<'[';for(size_t i=0;i<h.size();++i){if(i)std::cout<<',';const auto& g=h[i];std::cout<<'['<<g.start_time<<','<<g.end_time<<','<<g.step_dt<<','<<g.accepted<<','<<g.retry_index<<",[";for(size_t j=0;j<g.trials.size();++j){if(j)std::cout<<',';const auto& t=g.trials[j];std::cout<<"[\""<<t.role<<"\",\""<<t.solver<<"\","<<t.start_time<<','<<t.end_time<<','<<t.step_dt<<','<<t.converged<<','<<t.retained<<','<<t.exception<<']';}std::cout<<"]]";}std::cout<<']';}
int main(){try{std::cout<<std::setprecision(17);for(int d:{2,3})for(bool log:{false,true})for(int f:{0,1})for(int protocol:{0,1})for(int level:{0,1}){
 auto s=fixture(d,log,f,protocol,level,false);const auto full=s->solve_transient_results();const auto ft=s->transient_attempt_history();
 const double cut=(protocol?1.25:.25)*T;const auto found=std::find_if(full.begin(),full.end(),[&](const auto& r){return r.time==cut;});if(found==full.end())throw std::runtime_error("missing native checkpoint");
 auto tail_s=fixture(d,log,f,protocol,level,false);tail_s->set_initial_guess(found->phi,found->n,found->p);tail_s->set_ferroelectric_ensemble_history(found->P,{});tail_s->set_transient_start_time(found->time);const auto tail=tail_s->solve_transient_results();
 auto manual_s=fixture(d,log,f,protocol,level,true);const auto manual=manual_s->solve_transient_results();
 for(const auto* h:{&full,&tail,&manual})if(h->back().time!=4*T||!std::all_of(h->begin(),h->end(),[](const auto& r){return r.converged;}))throw std::runtime_error("native bridge solve failed");
 std::cout<<"{\"dimension\":"<<d<<",\"logarithmic\":"<<log<<",\"family\":"<<f<<",\"protocol\":"<<protocol<<",\"level\":"<<level<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(ft);std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tail_s->transient_attempt_history());std::cout<<",\"manual\":";history(manual);std::cout<<",\"manual_trace\":";trace(manual_s->transient_attempt_history());std::cout<<"}"<<std::endl;
 }return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
