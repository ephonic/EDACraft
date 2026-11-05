// Offline diagnostic only: the production event guard remains enabled.
// Frozen Gauss roots use actual accepted quad n/p/P from ordinary split NLS.
#include "device_simulator.h"
#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>
using namespace tcad;
using V=std::vector<real_t>;
constexpr real_t T=TCAD_CONST(0x1p-40),B=TCAD_CONST(0x1p-25),S=TCAD_CONST(0x1p66),PS=TCAD_CONST(0x1p-20);
void need(bool good,const char* why){if(!good)throw std::runtime_error(why);}
void number(real_t x){char b[160];quadmath_snprintf(b,sizeof b,"%.36Qg",x);std::cout<<'"'<<b<<'"';}
void values(const V& a){std::cout<<'[';for(size_t i=0;i<a.size();++i){if(i)std::cout<<',';number(a[i]);}std::cout<<']';}
void drive(const FerroelectricNlsDrive& d){values({d.raw_mean_field,d.mean_field,d.peak_field,d.mean_polarization,d.volume,d.zero_field_tolerance});}
real_t voltage(real_t t){return t<=2*T?TCAD_CONST(0x1p-10)*t/(2*T):TCAD_CONST(0x1p-10)-TCAD_CONST(0x1p-9)*(t-2*T)/(2*T);}
struct Fixture{
 Grid3D g;V eps,doping,n,p;std::map<size_t,real_t> bc,nbc,pbc;
 Fixture(int dim):g{3,3,dim==3?3u:1u,B,B,B}{
  g.xx={0,3*B,8*B};g.yx={0,5*B,11*B};if(dim==3)g.zx={0,2*B,7*B};
  const size_t N=g.npts();eps.resize(N);doping.resize(N);n.resize(N);p.resize(N);
  for(size_t k=0;k<g.nz;++k)for(size_t j=0;j<3;++j)for(size_t i=0;i<3;++i){size_t q=g.index(i,j,k);
   eps[q]=TCAD_CONST(0x1p-33)*(1+j*TCAD_CONST(.25)+k*TCAD_CONST(.5));doping[q]=S*(TCAD_CONST(.125)-i*TCAD_CONST(.03125));
   n[q]=S*(1+j*TCAD_CONST(.0625)+k*TCAD_CONST(.03125)+(i==1?TCAD_CONST(.5):0));p[q]=S*(1+j*TCAD_CONST(.03125)+k*TCAD_CONST(.0625)+(i==1?TCAD_CONST(.25):0));
   if(i!=1){bc[q]=0;nbc[q]=n[q];pbc[q]=p[q];}
  }
 }
 std::unique_ptr<DeviceSimulator> simulator(bool log,int depol)const{
  const size_t N=g.npts();auto s=std::make_unique<DeviceSimulator>(g.nx,g.ny,g.nz,g.dx,g.dy,g.dz);s->set_grid_x(g.xx);s->set_grid_y(g.yx);if(g.nz>1)s->set_grid_z(g.zx);
  s->set_permittivity(eps);s->set_doping(doping);s->set_mobility(V(N,TCAD_CONST(.125)),V(N,TCAD_CONST(.0625)));s->set_effective_dos(V(N,S),V(N,S));s->set_bandgap(V(N,0));s->set_recombination(V(N,TCAD_CONST(1e100)),V(N,TCAD_CONST(1e100)));
  s->set_thermal_voltage(TCAD_CONST(.03125));s->set_newton_use_log_space(log);s->set_dirichlet_potential(bc);s->set_electron_bc(nbc);s->set_hole_bc(pbc);s->set_initial_guess(V(N,0),n,p);s->set_gummel_max_iter(100);s->set_tolerance(TCAD_CONST(1e-11));
  s->set_transient_dt(T/2);s->set_transient_t_final(4*T);s->set_nonlinear_history_enabled(true);s->set_ferroelectric_enabled(true);s->set_ferroelectric_params(std::vector<char>(N,1),TCAD_CONST(1e8),TCAD_CONST(1e12));s->set_ferroelectric_model(2);s->set_ferroelectric_polar_axis(0);s->set_ferroelectric_preisach(PS,TCAD_CONST(1e5),0);s->set_ferroelectric_nls(TCAD_CONST(0x1p-36),TCAD_CONST(2048.0),TCAD_CONST(0x1p-50));s->set_ferroelectric_builtin_field(-TCAD_CONST(512.0));s->set_ferroelectric_depol(depol);s->set_ferroelectric_gamma(0);s->set_transient_lk_coupled(false);
  V times,volts;for(int i=0;i<=16;++i){times.push_back(i*T/4);volts.push_back(voltage(times.back()));}std::map<size_t,V> offsets;for(const auto& item:bc)if(item.first%3==2)offsets[item.first]=volts;s->set_transient_voltage_waveforms(times,offsets);return s;
 }
};
struct Root{real_t low,high,value;FerroelectricNlsDrive report;V phi;};
void row(const Fixture& f,int dim,bool log,int depol,size_t index,const SimulationResult& state){
 const size_t N=f.g.npts();PoissonSolver s(f.g);s.set_permittivity(f.eps);s.set_doping(f.doping);s.set_ferroelectric(std::vector<char>(N,1),TCAD_CONST(1e8),TCAD_CONST(1e12));s.set_ferroelectric_model(2);s.set_ferroelectric_polar_axis(0);s.set_ferroelectric_builtin_field(-TCAD_CONST(512.0));s.set_ferroelectric_depol(depol);s.set_fe_polarization(state.P);s.set_fe_play_state({TCAD_CONST(.125),-TCAD_CONST(.25)});
 const auto play=s.fe_play_state();
 auto probe=[&](real_t v,V& phi){auto bc=f.bc;for(auto& x:bc)if(x.first%3==2)x.second=v;s.set_dirichlet(bc);s.assemble(state.n,state.p);phi.assign(N,0);need(s.solve(phi),"frozen Gauss failed");auto entered=phi,rhs=s.rhs(),matrix=s.matrix().vals();auto d=s.ferroelectric_nls_drive(phi);auto repeated=s.ferroelectric_nls_drive(phi);need(d.active && d.raw_mean_field==repeated.raw_mean_field && d.mean_polarization==repeated.mean_polarization,"nonrepeatable drive");need(phi==entered && s.rhs()==rhs && s.matrix().vals()==matrix && s.fe_polarization()==state.P && s.fe_play_state()==play,"probe mutated frozen state");return d;};
 V low_phi,high_phi;const real_t lo=-TCAD_CONST(.0625),hi=TCAD_CONST(.0625);auto low=probe(lo,low_phi),high=probe(hi,high_phi);need(low.raw_mean_field>0 && high.raw_mean_field<0,"missing root bracket");
 auto locate=[&](){Root r{lo,hi,0,{},{}};for(int i=0;i<76;++i){real_t mid=(r.low+r.high)/2;V phi;auto d=probe(mid,phi);if(d.raw_mean_field>0)r.low=mid;else r.high=mid;}r.value=(r.low+r.high)/2;r.report=probe(r.value,r.phi);return r;};
 const auto root=locate();s.set_ferroelectric_depol(0);const auto zero=locate();s.set_ferroelectric_depol(depol);
 // The physical split update uses old accepted carriers/P at the next voltage.
 V end_phi,after;FerroelectricNlsDrive end_drive;real_t interval=0;
 if(index<16){interval=T/4;end_drive=probe(voltage(state.time+interval),end_phi);s.set_ferroelectric_preisach(PS,TCAD_CONST(1e5),0);s.set_ferroelectric_nls(TCAD_CONST(0x1p-36),TCAD_CONST(2048.0),TCAD_CONST(0x1p-50));s.update_ferroelectric_polarization_transient(end_phi,interval);after=s.fe_polarization();need(s.fe_play_state()==play,"offline update consumed play");}
 std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"index\":"<<index<<",\"time\":";number(state.time);std::cout<<",\"dt\":";number(interval);std::cout<<",\"shape\":[3,3,"<<f.g.nz<<"],\"axes\":[";values(f.g.xx);std::cout<<',';values(f.g.yx);std::cout<<',';values(f.g.nz==1?V{0}:f.g.zx);std::cout<<']';
#define FIELD(key,x) std::cout<<",\"" key "\":";values(x)
 FIELD("eps",f.eps);FIELD("doping",f.doping);FIELD("n",state.n);FIELD("p",state.p);FIELD("P",state.P);FIELD("accepted_phi",state.phi);FIELD("low_phi",low_phi);FIELD("high_phi",high_phi);FIELD("root_phi",root.phi);FIELD("end_phi",end_phi);FIELD("after",after);
#undef FIELD
 std::cout<<",\"low_drive\":";drive(low);std::cout<<",\"high_drive\":";drive(high);std::cout<<",\"root_drive\":";drive(root.report);std::cout<<",\"end_drive\":";drive(end_drive);
 std::cout<<",\"root_bracket\":";values({root.low,root.high,root.value});std::cout<<",\"zero_root_bracket\":";values({zero.low,zero.high,zero.value});std::cout<<",\"passed\":true}"<<std::endl;
}
void run(int dim,bool log,int depol){
 Fixture f(dim);auto s=f.simulator(log,depol);int rejected=0;
 auto reject=[&](){auto P=s->fe_polarization(),play=s->ferroelectric_play_history(),params=s->ferroelectric_ensemble_parameters();s->set_transient_nls_event_control(true,TCAD_CONST(0x1p-60));bool caught=false;try{s->solve_transient();}catch(const std::invalid_argument& e){caught=std::string(e.what()).find("NLS event control requires")!=std::string::npos;}need(caught && s->fe_polarization()==P && s->ferroelectric_play_history()==play && s->ferroelectric_ensemble_parameters()==params && s->transient_attempt_history().empty(),"depol scope guard mutated memory");s->set_transient_nls_event_control(false,TCAD_CONST(0x1p-60));++rejected;};
 if(depol){reject();}
 const auto before=s->fe_polarization(),play=s->ferroelectric_play_history();s->begin_reliability_transaction();const auto h=s->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged && !r.phi_frozen;}),"ordinary split trajectory failed");if(depol)reject();s->rollback_reliability_transaction();need(s->fe_polarization()==before && s->ferroelectric_play_history()==play,"transaction rollback failed");
 const auto recovered=s->solve_transient();need(recovered.size()==h.size(),"recovered timeline changed");for(size_t i=0;i<h.size();++i)need(h[i].time==recovered[i].time && h[i].phi==recovered[i].phi && h[i].n==recovered[i].n && h[i].p==recovered[i].p && h[i].P==recovered[i].P,"recovered trajectory changed");
 const auto held=s->fe_polarization(),held_play=s->ferroelectric_play_history();for(size_t i=0;i<h.size();++i)row(f,dim,log,depol,i,h[i]);need(s->fe_polarization()==held && s->ferroelectric_play_history()==held_play,"offline analysis mutated live device");
 std::cout<<"{\"summary\":true,\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"states\":"<<h.size()<<",\"guard_rejections\":"<<rejected<<",\"transaction_rollback\":true,\"recovery_identical\":true,\"observation_read_only\":true}"<<std::endl;
}
int main(){try{for(int d:{2,3})for(bool log:{false,true})for(int depol:{0,25,50})run(d,log,depol);return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
