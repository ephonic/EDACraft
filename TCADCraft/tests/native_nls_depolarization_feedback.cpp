// Isolated frozen-carrier feedback experiment, not an accepted device solve.
// Reuse the sealed484 public fixture; production depolarization guard stays.
#define main sealed484_fixture_main
#include "native_nls_depolarization_roots.cpp"
#undef main
namespace feedback485 {
struct Wave {
 V times,voltages;
 real_t at(real_t t)const{
  for(size_t i=1;i<times.size();++i)if(t<=times[i])return voltages[i-1]+(voltages[i]-voltages[i-1])*(t-times[i-1])/(times[i]-times[i-1]);
  return voltages.back();
 }
 real_t limit(real_t t)const{for(auto knot:times)if(knot>t)return knot;return times.back();}
};
struct Observation {V phi;FerroelectricNlsDrive d;};
class Frozen {
 const Fixture& f;const SimulationResult& source;PoissonSolver solver;
public:
 V P;
 Frozen(const Fixture& fixture,const SimulationResult& state,int depol):f(fixture),source(state),solver(f.g),P(state.P){
  solver.set_permittivity(f.eps);solver.set_doping(f.doping);solver.set_ferroelectric(std::vector<char>(f.g.npts(),1),TCAD_CONST(1e8),TCAD_CONST(1e12));solver.set_ferroelectric_model(2);solver.set_ferroelectric_polar_axis(0);solver.set_ferroelectric_builtin_field(-TCAD_CONST(512.0));solver.set_ferroelectric_depol(depol);solver.set_ferroelectric_preisach(PS,TCAD_CONST(1e5),0);solver.set_ferroelectric_nls(TCAD_CONST(0x1p-36),TCAD_CONST(2048.0),TCAD_CONST(0x1p-50));solver.set_fe_play_state({TCAD_CONST(.125),-TCAD_CONST(.25)});
 }
 Observation probe(real_t v){
  solver.set_fe_polarization(P);auto bc=f.bc;for(auto& x:bc)if(x.first%3==2)x.second=v;solver.set_dirichlet(bc);solver.assemble(source.n,source.p);Observation o;o.phi.assign(f.g.npts(),0);need(solver.solve(o.phi),"feedback Gauss failed");
  auto old=o.phi,rhs=solver.rhs(),matrix=solver.matrix().vals(),play=solver.fe_play_state();o.d=solver.ferroelectric_nls_drive(o.phi);auto again=solver.ferroelectric_nls_drive(o.phi);
  need(o.d.raw_mean_field==again.raw_mean_field && o.phi==old && solver.rhs()==rhs && solver.matrix().vals()==matrix && solver.fe_polarization()==P && solver.fe_play_state()==play,"feedback probe changed memory");return o;
 }
 real_t root_voltage(const Observation& low,const Observation& high)const{return -TCAD_CONST(.0625)+TCAD_CONST(.125)*low.d.raw_mean_field/(low.d.raw_mean_field-high.d.raw_mean_field);}
 V advance(const Observation& at,real_t dt){solver.set_fe_polarization(P);auto play=solver.fe_play_state();solver.update_ferroelectric_polarization_transient(at.phi,dt);need(solver.fe_play_state()==play,"feedback consumed play");P=solver.fe_polarization();return P;}
};
void observed(const Observation& o){std::cout<<"{\"phi\":";values(o.phi);std::cout<<",\"drive\":";drive(o.d);std::cout<<'}';}
void run_case(const Fixture& f,const SimulationResult& source,int dim,bool log,int depol,int source_index,int family,int protocol,int mode){
 const real_t width=family?TCAD_CONST(0x1p-66):TCAD_CONST(0x1p-60);Frozen s(f,source,depol);const auto seedlo=s.probe(-TCAD_CONST(.0625)),seedhi=s.probe(TCAD_CONST(.0625));const real_t vroot=s.root_voltage(seedlo,seedhi);
 const real_t root=source_index==0?2*T*vroot/TCAD_CONST(0x1p-10):2*T+(TCAD_CONST(0x1p-10)-vroot)*T/TCAD_CONST(0x1p-10);
 Wave wave{{source.time,source_index==0?2*T:4*T},{voltage(source.time),voltage(source_index==0?2*T:4*T)}};
 need(root>wave.times.front()+T/16 && root<wave.times.back()-T/16,"seed root not interior");
 if(protocol)wave={{source.time,root-T/16,root+T/16,wave.times.back()},{wave.voltages.front(),vroot,vroot,wave.voltages.back()}};
 real_t time=mode==0?source.time:mode==1?(protocol?root-T/16:root)-TCAD_CONST(.37)*width:mode==2?root:(protocol?root+T/16:root)+TCAD_CONST(.37)*width;
 const real_t entered=time;const int max_steps=24;int steps=0;bool progress=true;
 std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_index\":"<<source_index<<",\"family\":"<<family<<",\"protocol\":"<<protocol<<",\"start_mode\":"<<mode<<",\"source_time\":";number(source.time);std::cout<<",\"start\":";number(entered);std::cout<<",\"width\":";number(width);std::cout<<",\"initial_root_time\":";number(root);std::cout<<",\"initial_root_voltage\":";number(vroot);std::cout<<",\"wave_times\":";values(wave.times);std::cout<<",\"wave_voltages\":";values(wave.voltages);
 std::cout<<",\"n\":";values(source.n);std::cout<<",\"p\":";values(source.p);std::cout<<",\"source_P\":";values(source.P);std::cout<<",\"seed_low\":";observed(seedlo);std::cout<<",\"seed_high\":";observed(seedhi);std::cout<<",\"steps\":[";
 while(time<wave.times.back() && steps<max_steps){
  const auto low=s.probe(-TCAD_CONST(.0625)),high=s.probe(TCAD_CONST(.0625));const auto P=s.P;const real_t before_root=s.root_voltage(low,high),limit=wave.limit(time),proposed=std::min(limit,time+T/4);const auto first=s.probe(wave.at(time)),last=s.probe(wave.at(proposed));
  real_t selected=proposed,local_root=proposed;std::string role="ordinary";
  if(first.d.mean_field==0){
   if(last.d.mean_field==0)role="zero_band";
   else{const real_t outgoing=std::min(proposed,time+width);if(outgoing<proposed && s.probe(wave.at(outgoing)).d.mean_field==0)role="zero_band_exit";else{selected=outgoing;role="outgoing_zero";}}
  }else if((first.d.raw_mean_field>0 && last.d.raw_mean_field<0)||(first.d.raw_mean_field<0 && last.d.raw_mean_field>0)||last.d.mean_field==0){
   // Affine frozen Gauss root, independently audited. This substitutes only
   // the root solve in a diagnostic copy of481's endpoint selection rule.
   if(last.d.mean_field!=0)local_root=time+(proposed-time)*first.d.raw_mean_field/(first.d.raw_mean_field-last.d.raw_mean_field);
   const real_t incoming=local_root-width;selected=incoming>time+width/8?incoming:std::min(proposed,local_root+width);role=incoming>time+width/8?"incoming":"outgoing_cross";
  }
  if(!(selected>time && selected<=proposed)){progress=false;break;}
  const auto endpoint=s.probe(wave.at(selected));const auto after=s.advance(endpoint,selected-time);const auto after_low=s.probe(-TCAD_CONST(.0625)),after_high=s.probe(TCAD_CONST(.0625));const real_t after_root=s.root_voltage(after_low,after_high);
  if(steps)std::cout<<',';std::cout<<"{\"start\":";number(time);std::cout<<",\"limit\":";number(limit);std::cout<<",\"proposed\":";number(proposed);std::cout<<",\"end\":";number(selected);std::cout<<",\"dt\":";number(selected-time);std::cout<<",\"role\":\""<<role<<"\",\"local_root\":";number(local_root);std::cout<<",\"root_before_voltage\":";number(before_root);std::cout<<",\"root_after_voltage\":";number(after_root);
  std::cout<<",\"P\":";values(P);std::cout<<",\"after\":";values(after);std::cout<<",\"low\":";observed(low);std::cout<<",\"high\":";observed(high);std::cout<<",\"first\":";observed(first);std::cout<<",\"last\":";observed(last);std::cout<<",\"endpoint\":";observed(endpoint);std::cout<<",\"after_low\":";observed(after_low);std::cout<<",\"after_high\":";observed(after_high);std::cout<<'}';
  time=selected;++steps;
 }
 std::cout<<"],\"end\":";number(time);std::cout<<",\"status\":\""<<(!progress?"nonprogress":time==wave.times.back()?"finished":"iteration_cap")<<"\",\"max_steps\":"<<max_steps<<",\"carriers_frozen\":true,\"device_step_accepted\":false}"<<std::endl;
}
void matrix(){for(int dim:{2,3})for(bool log:{false,true})for(int depol:{0,25,50}){
 Fixture f(dim);auto live=f.simulator(log,depol);const auto h=live->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source trajectory failed");const auto P=live->fe_polarization(),play=live->ferroelectric_play_history();
 for(int source_index:{0,8})for(int family:{0,1})for(int protocol:{0,1})for(int mode:{0,1,2,3})run_case(f,h[source_index],dim,log,depol,source_index,family,protocol,mode);
 need(live->fe_polarization()==P && live->ferroelectric_play_history()==play,"isolated feedback mutated device");std::cout<<"{\"summary\":true,\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_states\":2,\"cases\":32,\"live_memory_unchanged\":true}"<<std::endl;
}}
}
int main(){try{feedback485::matrix();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
