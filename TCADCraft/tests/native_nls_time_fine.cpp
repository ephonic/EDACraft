#include "device_simulator.h"
#include <cstdlib>
#include <fstream>
#include <new>
#include <sstream>
#include <tuple>
namespace fault490 {
const tcad::DeviceSimulator* watched=nullptr;
const std::vector<tcad::real_t>* entered=nullptr;
bool armed=false,fired=false,persistent=false,in_linear=false;
int phase=0;size_t failures=0,observed_groups=0;
bool observed_called=false,observed_converged=false,observed_prefix=false,observed_P_changed=false,observed_linear=false;
tcad::real_t observed_start=0,observed_end=0;
void* allocate(size_t bytes){
 if(armed){
  bool hit=fired && persistent;
  if(!hit){
   const auto& groups=watched->transient_attempt_history();
   if(!groups.empty() && !groups.back().trials.empty()){
    const auto& g=groups.back();const auto& t=g.trials.back();bool prefix=false;for(const auto& prior:groups)prefix=prefix || prior.accepted;
    const bool changed=watched->fe_polarization()!=*entered;
    hit=(phase==0 && !t.solver_called && !changed) || (phase==1 && !t.solver_called && changed) || (phase==2 && t.solver_called && t.converged) || (phase==3 && in_linear && prefix && t.solver_called && !t.converged);
    if(hit){observed_groups=groups.size();observed_called=t.solver_called;observed_converged=t.converged;observed_prefix=prefix;observed_P_changed=changed;observed_linear=in_linear;observed_start=g.start_time;observed_end=g.end_time;}
   }
  }
  if(hit){fired=true;++failures;if(!persistent)armed=false;throw std::bad_alloc();}
 }
 if(void* p=std::malloc(bytes?bytes:1))return p;throw std::bad_alloc();
}
}
void* operator new(size_t n){return fault490::allocate(n);}
void* operator new[](size_t n){return fault490::allocate(n);}
void operator delete(void* p) noexcept{std::free(p);}
void operator delete[](void* p) noexcept{std::free(p);}
void operator delete(void* p,size_t) noexcept{std::free(p);}
void operator delete[](void* p,size_t) noexcept{std::free(p);}
extern "C" size_t real_linear490(tcad::LinearSolver*,const tcad::SparseMatrix&,const tcad::Vector&,tcad::Vector&)
 asm("__real__ZN4tcad12LinearSolver5solveERKNS_12SparseMatrixERKSt6vectorIgSaIgEERS6_");
extern "C" size_t wrap_linear490(tcad::LinearSolver*,const tcad::SparseMatrix&,const tcad::Vector&,tcad::Vector&)
 asm("__wrap__ZN4tcad12LinearSolver5solveERKNS_12SparseMatrixERKSt6vectorIgSaIgEERS6_");
extern "C" size_t wrap_linear490(tcad::LinearSolver* self,const tcad::SparseMatrix& a,const tcad::Vector& b,tcad::Vector& x){
 struct Guard {bool previous=fault490::in_linear;Guard(){fault490::in_linear=true;}~Guard(){fault490::in_linear=previous;}} guard;
 return real_linear490(self,a,b,x);
}
// Isolated acceptance-loop diagnostic; sealed485 helpers, production unchanged.
// Reuse the sealed484 public fixture; production depolarization guard stays.
#define main sealed484_fixture_main
#include "native_nls_depolarization_roots.cpp"
#undef main
namespace continuous490 {
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
struct Candidate {real_t time;Observation before,after;V P;};
bool same(const Observation& a,const Observation& b){return a.phi==b.phi && a.d.raw_mean_field==b.d.raw_mean_field && a.d.mean_field==b.d.mean_field && a.d.peak_field==b.d.peak_field && a.d.mean_polarization==b.d.mean_polarization && a.d.volume==b.d.volume && a.d.zero_field_tolerance==b.d.zero_field_tolerance;}
Candidate trial(const Fixture& f,const SimulationResult& source,int depol,const V& base,const Wave& wave,real_t start,real_t end,int fail=0){
 need(end>=start,"candidate negative dwell");Frozen disposable(f,source,depol);disposable.P=base;Candidate r;r.time=end;r.before=disposable.probe(wave.at(end));
 if(fail==1)throw std::runtime_error("synthetic before-update failure");
 if(end>start)disposable.advance(r.before,end-start);r.P=disposable.P;
 if(fail==2)throw std::runtime_error("synthetic after-update failure");
 r.after=disposable.probe(wave.at(end));return r;
}
void emit(const Candidate& c,const std::string& label){std::cout<<"{\"label\":\""<<label<<"\",\"time\":";number(c.time);std::cout<<",\"before\":";observed(c.before);std::cout<<",\"P\":";values(c.P);std::cout<<",\"after\":";observed(c.after);std::cout<<'}';}
struct Sample {real_t time,pre,post,guard;};
std::string bracket(const std::vector<Sample>& a,real_t width,size_t& at){
 if(!(width>0))return "invalid_width";
 if(a.size()<2)return "no_crossing";
 if(!(a.front().time+width>a.front().time))return "unrepresentable";
 int changes=0;bool increasing=false;
 for(size_t i=0;i<a.size();++i){
  if(!(a[i].pre>0))return "wrong_branch";
  if(i){if(!(a[i].time>a[i-1].time))return "invalid_clock";
   if(a[i-1].post>0 && a[i].post<=0){++changes;at=i;}
   if(a[i].post>a[i-1].post+std::max(a[i].guard,a[i-1].guard))increasing=true;
  }
 }
 if(changes==0)return "no_crossing";if(changes>1)return "multiple_crossings";if(increasing)return "nonmonotone";return "ok";
}
bool bounds(real_t start,real_t proposed,real_t frozen_root,real_t middle,real_t width){return middle-width>start && middle+width< frozen_root && middle+width<=proposed;}
int guard_tests(){
 size_t at=0;const real_t z=TCAD_CONST(1e-24);std::vector<Sample> good={{0,1,1,z},{1,1,TCAD_CONST(.5),z},{2,1,-1,z}};
 need(bracket(good,TCAD_CONST(.1),at)=="ok" && at==2,"valid bracket rejected");
 auto a=good;a.back().post=TCAD_CONST(.2);need(bracket(a,TCAD_CONST(.1),at)=="no_crossing","no-cross guard");
 a={{0,1,1,z},{1,1,-1,z},{2,1,1,z},{3,1,-1,z}};need(bracket(a,TCAD_CONST(.1),at)=="multiple_crossings","multiple guard");
 a={{0,1,1,z},{1,1,TCAD_CONST(.5),z},{2,1,TCAD_CONST(.8),z},{3,1,-1,z}};need(bracket(a,TCAD_CONST(.1),at)=="nonmonotone","nonmonotone guard");
 a=good;a[1].pre=0;need(bracket(a,TCAD_CONST(.1),at)=="wrong_branch","branch guard");
 a=good;a[1].time=0;need(bracket(a,TCAD_CONST(.1),at)=="invalid_clock","clock guard");
 need(bracket(good,0,at)=="invalid_width","width guard");
 a=good;a[0].time=TCAD_CONST(1e40);need(bracket(a,TCAD_CONST(1e-30),at)=="unrepresentable","representability guard");
 need(!bounds(0,1,1,TCAD_CONST(.01),TCAD_CONST(.1)),"incoming bounds guard");
 need(!bounds(0,TCAD_CONST(.5),1,TCAD_CONST(.6),TCAD_CONST(.1)),"node bounds guard");return 10;
}
struct Step {
 real_t start=0,limit=0,proposed=0,original_end=0,root=0,low=0,high=0;
 V P;Observation first,last;Candidate initial,chosen,certificate;std::vector<Candidate> scan,bisected;
 std::string role,reason="ok";bool corrected=false,committed=false;
};
struct Result {std::vector<Step> steps;real_t end;V P;std::string status;int exceptions=0;};
Result advance_loop(const Fixture& f,const SimulationResult& source,int depol,const Wave& wave,real_t start,const V& base,real_t width,int budget,bool inject){
 Frozen state(f,source,depol);state.P=base;Result result;real_t time=start;std::string status="iteration_cap";
 for(int count=0;count<budget && time<wave.times.back();++count){
  Step step;step.P=state.P;step.start=time;step.limit=wave.limit(time);step.proposed=std::min(step.limit,time+T/4);step.first=state.probe(wave.at(time));step.last=state.probe(wave.at(step.proposed));step.original_end=step.proposed;step.root=step.proposed;step.role="ordinary";
  if(step.first.d.mean_field==0){
   if(step.last.d.mean_field==0)step.role="zero_band";
   else{const real_t out=std::min(step.proposed,time+width);if(out<step.proposed && state.probe(wave.at(out)).d.mean_field==0)step.role="zero_band_exit";else{step.original_end=out;step.role="outgoing_zero";}}
  }else if((step.first.d.raw_mean_field>0 && step.last.d.raw_mean_field<0)||(step.first.d.raw_mean_field<0 && step.last.d.raw_mean_field>0)||step.last.d.mean_field==0){
   if(step.last.d.mean_field!=0)step.root=time+(step.proposed-time)*step.first.d.raw_mean_field/(step.first.d.raw_mean_field-step.last.d.raw_mean_field);
   const real_t incoming=step.root-width;if(incoming>time+width/8){step.original_end=incoming;step.role="incoming";}else{step.original_end=std::min(step.proposed,step.root+width);step.role="outgoing_cross";}
  }
  if(!(step.original_end>time && step.original_end<=step.proposed)){status="nonprogress";break;}
  auto evaluate=[&](real_t t,int fail=0){return trial(f,source,depol,step.P,wave,time,t,fail);};
  step.initial=evaluate(step.original_end);step.chosen=step.initial;step.certificate=step.initial;
  const real_t first_sign=step.first.d.mean_field>0?1:step.first.d.mean_field<0?-1:0;
  if(step.initial.before.d.mean_field*step.initial.after.d.mean_field<0){
   if(first_sign!=0 && first_sign*step.initial.before.d.mean_field>0 && (step.role=="incoming" || step.role=="ordinary")){
    std::vector<Sample> samples;for(int i=0;i<=16;++i){auto c=evaluate(time+(step.original_end-time)*i/16);samples.push_back({c.time,first_sign*c.before.d.mean_field,first_sign*c.after.d.mean_field,std::max(c.before.d.zero_field_tolerance,c.after.d.zero_field_tolerance)});step.scan.push_back(std::move(c));}
    size_t at=0;step.reason=bracket(samples,width,at);
    if(step.reason=="ok"){
     step.low=step.scan[at-1].time;step.high=step.scan[at].time;
     for(int j=0;j<80 && step.high-step.low>width/64;++j){const real_t mid=(step.low+step.high)/2;auto c=evaluate(mid);if(!(first_sign*c.before.d.mean_field>0)){step.reason="wrong_branch";break;}if(first_sign*c.after.d.mean_field>0)step.low=mid;else step.high=mid;step.bisected.push_back(std::move(c));}
     if(step.reason=="ok" && step.high-step.low>width/64)step.reason="bisection_cap";
     const real_t middle=(step.low+step.high)/2;
     if(step.reason=="ok" && !bounds(time,step.proposed,step.root,middle,width))step.reason="clock_bounds";
     if(step.reason=="ok"){
      step.chosen=evaluate(middle-width);step.certificate=evaluate(middle+width);
      if(!(first_sign*step.chosen.before.d.mean_field>0 && first_sign*step.certificate.before.d.mean_field>0 && first_sign*step.chosen.after.d.mean_field>0 && first_sign*step.certificate.after.d.mean_field<0))step.reason="post_update_sides";else step.corrected=true;
     }
    }
    if(step.reason!="ok")status="selector_rejected";
   }else{step.reason="outgoing_sign_flip";status="outgoing_rejected";}
  }
  if(inject && count==0){
   for(int fail:{1,2}){try{evaluate(step.chosen.time,fail);}catch(const std::runtime_error& e){need(std::string(e.what()).find("synthetic ")==0,"unexpected injected failure");++result.exceptions;}}
   const auto repeated=evaluate(step.chosen.time);need(repeated.P==step.chosen.P && same(repeated.before,step.chosen.before) && same(repeated.after,step.chosen.after),"retry accumulated dwell");
  }
  need(state.P==step.P && same(step.first,state.probe(wave.at(time))),"candidate retry mutated accepted state");
  if(step.reason!="ok"){result.steps.push_back(std::move(step));break;}
  need(step.chosen.time>time && step.chosen.time<=step.proposed,"accepted clock bounds");step.committed=true;state.P=step.chosen.P;time=step.chosen.time;result.steps.push_back(std::move(step));
 }
 if(time==wave.times.back())status="finished";result.end=time;result.P=state.P;result.status=status;return result;
}
bool same_step(const Step& a,const Step& b){return a.start==b.start && a.limit==b.limit && a.proposed==b.proposed && a.original_end==b.original_end && a.root==b.root && a.P==b.P && a.role==b.role && a.corrected==b.corrected && a.committed==b.committed && a.reason==b.reason && a.chosen.time==b.chosen.time && a.chosen.P==b.chosen.P && same(a.chosen.before,b.chosen.before) && same(a.chosen.after,b.chosen.after);}
void emit_step(const Step& s){
 std::cout<<"{\"start\":";number(s.start);std::cout<<",\"limit\":";number(s.limit);std::cout<<",\"proposed\":";number(s.proposed);std::cout<<",\"original_end\":";number(s.original_end);std::cout<<",\"local_root\":";number(s.root);std::cout<<",\"P\":";values(s.P);std::cout<<",\"first\":";observed(s.first);std::cout<<",\"last\":";observed(s.last);std::cout<<",\"initial\":";emit(s.initial,"initial");std::cout<<",\"chosen\":";emit(s.chosen,"chosen");std::cout<<",\"certificate\":";emit(s.certificate,"certificate");
 std::cout<<",\"scan\":[";for(size_t i=0;i<s.scan.size();++i){if(i)std::cout<<',';emit(s.scan[i],"scan_"+std::to_string(i));}std::cout<<"],\"bisection\":[";for(size_t i=0;i<s.bisected.size();++i){if(i)std::cout<<',';emit(s.bisected[i],"bisect_"+std::to_string(i));}
 std::cout<<"],\"bracket_low\":";number(s.low);std::cout<<",\"bracket_high\":";number(s.high);std::cout<<",\"role\":\""<<s.role<<"\",\"reason\":\""<<s.reason<<"\",\"corrected\":"<<(s.corrected?"true":"false")<<",\"committed\":"<<(s.committed?"true":"false")<<'}';
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
void configure(DeviceSimulator& s,const Fixture& f,const SimulationResult& state,const Wave& wave,real_t end){
 s.set_tolerance(TCAD_CONST(1e-16));
 s.set_initial_guess(state.phi,state.n,state.p);s.set_ferroelectric_ensemble_history(state.P,{});s.set_transient_start_time(state.time);s.set_transient_t_final(end);s.set_transient_dt(end-state.time);
 V times=wave.times,volts=wave.voltages;if(times.front()>0){times.insert(times.begin(),0);volts.insert(volts.begin(),volts.front());}
 std::map<size_t,V> offsets;for(const auto& entry:f.bc)if(entry.first%3==2)offsets[entry.first]=volts;s.set_transient_voltage_waveforms(times,offsets);
}
bool same_states(const std::vector<SimulationResult>& a,const std::vector<SimulationResult>& b){
 if(a.size()!=b.size())return false;for(size_t i=0;i<a.size();++i){const auto& x=a[i];const auto& y=b[i];if(x.time!=y.time || x.attempted_time!=y.attempted_time || x.accepted_dt!=y.accepted_dt || x.converged!=y.converged)return false;
#define CHECK(name) if(x.name!=y.name)return false
 CHECK(phi);CHECK(n);CHECK(p);CHECK(P);CHECK(Jn_x);CHECK(Jn_y);CHECK(Jn_z);CHECK(Jp_x);CHECK(Jp_y);CHECK(Jp_z);CHECK(D_x);CHECK(D_y);CHECK(D_z);CHECK(Jdisp_x);CHECK(Jdisp_y);CHECK(Jdisp_z);CHECK(Jdielectric_x);CHECK(Jdielectric_y);CHECK(Jdielectric_z);CHECK(Jpolarization_x);CHECK(Jpolarization_y);CHECK(Jpolarization_z);CHECK(electrode_charges);CHECK(electrode_charge_increments);CHECK(electrode_total_currents);CHECK(terminal_currents);
#undef CHECK
 }return true;
}
struct Coupled {std::vector<SimulationResult> states;std::vector<TransientAttemptHistory> attempts;};
Coupled solve_candidate(const Fixture& f,const SimulationResult& state,const Wave& wave,bool log,int depol,real_t end,bool transaction=false){
 auto disposable=f.simulator(log,depol);configure(*disposable,f,state,wave,end);const auto P=disposable->fe_polarization(),play=disposable->ferroelectric_play_history(),params=disposable->ferroelectric_ensemble_parameters();
 if(transaction)disposable->begin_reliability_transaction();Coupled out;out.states=disposable->solve_transient();out.attempts=disposable->transient_attempt_history();
 if(transaction){disposable->rollback_reliability_transaction();need(disposable->fe_polarization()==P && disposable->ferroelectric_play_history()==play && disposable->ferroelectric_ensemble_parameters()==params,"material transaction rollback changed memory");const auto again=disposable->solve_transient();need(same_states(out.states,again),"material rollback replay differs");}
 return out;
}
void failure_controls(const Fixture& f,const SimulationResult& state,const Wave& wave,bool log,int depol,real_t end,const Coupled& good){
 {auto disposable=f.simulator(log,depol);configure(*disposable,f,state,wave,end);disposable->set_gummel_max_iter(0);const auto h=disposable->solve_transient();need(h.size()==2 && h.front().converged && !h.back().converged && h.back().time==state.time && h.back().attempted_time==end && h.back().accepted_dt==0,"ordinary candidate failure clock");need(h.back().phi==h.front().phi && h.back().n==h.front().n && h.back().p==h.front().p && h.back().P==h.front().P && disposable->fe_polarization()==state.P,"ordinary failure left trial state");const auto& trace=disposable->transient_attempt_history();need(trace.size()==1 && !trace[0].accepted && trace[0].status=="solver_failure" && trace[0].trials.size()==1 && !trace[0].trials[0].retained,"ordinary failure retained dwell");}
 bool caught=false;try{auto disposable=solve_candidate(f,state,wave,log,depol,end);need(same_states(disposable.states,good.states),"throw candidate differs");throw std::runtime_error("synthetic discarded coupled candidate");}catch(const std::runtime_error& e){caught=std::string(e.what())=="synthetic discarded coupled candidate";}need(caught,"discard exception missing");const auto retry=solve_candidate(f,state,wave,log,depol,end);need(same_states(good.states,retry.states),"failure/discard replay changed candidate");
}
FerroelectricNlsDrive final_drive(const Fixture& f,const SimulationResult& state,int depol){PoissonSolver observer(f.g);observer.set_ferroelectric(std::vector<char>(f.g.npts(),1),TCAD_CONST(1e8),TCAD_CONST(1e12));observer.set_ferroelectric_model(2);observer.set_ferroelectric_polar_axis(0);observer.set_ferroelectric_builtin_field(-TCAD_CONST(512.0));observer.set_ferroelectric_depol(depol);observer.set_fe_polarization(state.P);return observer.ferroelectric_nls_drive(state.phi);}
struct Entry {Step selection;Coupled actual;FerroelectricNlsDrive actual_drive;real_t P_defect=0;};
struct Snapshot {
 V phi,n,p,P,play,params,charge,Qn,Qp,mobility,previous,capacity,wave_times,configuration;
 std::vector<char> breakdown;std::map<size_t,real_t> phi_bc,n_bc,p_bc;std::map<size_t,V> offsets;
 bool guess,fe_init,bd_init,history_updates;
 explicit Snapshot(const DeviceSimulator& s):phi(s.init_phi_),n(s.init_n_),p(s.init_p_),P(s.fe_polarization()),play(s.ferroelectric_play_history()),params(s.ferroelectric_ensemble_parameters()),charge(s.Q_ot_),Qn(s.dg_transport_Qn_),Qp(s.dg_transport_Qp_),mobility(s.mobility_temperature_),previous(s.lattice_previous_temperature_),capacity(s.lattice_heat_capacity_),wave_times(s.transient_waveform_times_),configuration({s.tol_,s.transient_dt_,s.transient_start_time_,s.transient_t_final_,s.lattice_dt_,s.fe_gamma_,s.fe_alpha_,s.fe_beta_,s.transient_nls_event_half_width_,real_t(s.max_iter_),real_t(s.transient_nls_event_control_),real_t(s.transient_nls_error_control_),real_t(s.transient_electrical_error_control_),real_t(s.transient_lk_error_control_)}),breakdown(s.breakdown_state()),phi_bc(s.phi_bc_),n_bc(s.n_bc_),p_bc(s.p_bc_),offsets(s.transient_voltage_offsets_),guess(s.has_initial_guess_),fe_init(s.fe_polarization_init_),bd_init(s.bd_state_init_),history_updates(s.history_updates_enabled_){}
 bool operator==(const Snapshot& b)const{
#define SAME(n) if(n!=b.n)return false
 SAME(phi);SAME(n);SAME(p);SAME(P);SAME(play);SAME(params);SAME(charge);SAME(Qn);SAME(Qp);SAME(mobility);SAME(previous);SAME(capacity);SAME(wave_times);SAME(configuration);SAME(breakdown);SAME(phi_bc);SAME(n_bc);SAME(p_bc);SAME(offsets);SAME(guess);SAME(fe_init);SAME(bd_init);SAME(history_updates);
#undef SAME
 return true;
 }
};
void snapshot(const Snapshot& s){
 std::cout<<"{\"guess\":"<<s.guess<<",\"fe_init\":"<<s.fe_init<<",\"bd_init\":"<<s.bd_init<<",\"history_updates\":"<<s.history_updates;
#define FIELD(n) std::cout<<",\"" #n "\":";values(s.n)
 FIELD(phi);FIELD(n);FIELD(p);FIELD(P);FIELD(play);FIELD(params);FIELD(charge);FIELD(Qn);FIELD(Qp);FIELD(mobility);FIELD(previous);FIELD(capacity);FIELD(wave_times);FIELD(configuration);
#undef FIELD
 auto boundary=[](const std::map<size_t,real_t>& m){V flat;for(const auto& x:m){flat.push_back(x.first);flat.push_back(x.second);}values(flat);};
 std::cout<<",\"phi_bc\":";boundary(s.phi_bc);std::cout<<",\"n_bc\":";boundary(s.n_bc);std::cout<<",\"p_bc\":";boundary(s.p_bc);std::cout<<",\"offsets\":[";bool first=true;for(const auto& x:s.offsets){if(!first)std::cout<<',';first=false;std::cout<<"{\"node\":"<<x.first<<",\"values\":";values(x.second);std::cout<<'}';}std::cout<<"],\"breakdown\":[";for(size_t i=0;i<s.breakdown.size();++i){if(i)std::cout<<',';std::cout<<int(s.breakdown[i]);}std::cout<<"]}";
}
template<class F>std::string serialized(F write){std::ostringstream out;struct Redirect{std::streambuf* old;Redirect(std::streambuf* b):old(std::cout.rdbuf(b)){}~Redirect(){std::cout.rdbuf(old);}} redirect(out.rdbuf());write();return out.str();}
bool identical(const std::vector<SimulationResult>& a,const std::vector<SimulationResult>& b){return serialized([&]{history(a);})==serialized([&]{history(b);});}
bool identical(const std::vector<TransientAttemptHistory>& a,const std::vector<TransientAttemptHistory>& b){return serialized([&]{trace(a);})==serialized([&]{trace(b);});}
bool accepted(const std::vector<SimulationResult>& h,real_t end,size_t steps){return h.size()==steps+1 && h.back().time==end && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged && !r.phi_frozen && !r.transient_majority_frozen && r.transient_charge_ledger_available;});}
real_t read_number(std::istream& input){std::string s;need(bool(input>>s),"missing numeric input");char* end=nullptr;real_t v=strtoflt128(s.c_str(),&end);need(end && *end==0 && isfinite_q(v),"bad numeric input");return v;}
void key(int dim,bool log,int depol,int index,int family,int protocol){std::cout<<"\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_index\":"<<index<<",\"family\":"<<family<<",\"protocol\":"<<protocol;}
std::unique_ptr<DeviceSimulator> make(const Fixture& f,const SimulationResult& source,const Wave& scheduled,bool log,int depol){auto s=f.simulator(log,depol);configure(*s,f,source,scheduled,scheduled.times.back());s->set_transient_dt(T/4);return s;}
void failure_case(const Fixture& f,const SimulationResult& source,const Wave& scheduled,bool log,int depol,int dim,int index,int family,int protocol,int phase,bool persistent,const Coupled& baseline){
 auto s=make(f,source,scheduled,log,depol);const Snapshot before(*s);std::vector<SimulationResult> returned;bool caught=false;
 fault490::watched=s.get();fault490::entered=&before.P;fault490::phase=phase;fault490::persistent=persistent;fault490::fired=false;fault490::failures=0;fault490::observed_groups=0;fault490::armed=true;
 try{returned=s->solve_transient();}catch(const std::bad_alloc&){caught=true;}catch(...){fault490::armed=false;throw;}
 fault490::armed=false;fault490::watched=nullptr;fault490::entered=nullptr;
 need(fault490::fired && fault490::failures>0,"internal fault not reached");const Snapshot after(*s);const auto diagnostic=s->transient_attempt_history();need(!diagnostic.empty(),"fault trace missing");
 if(caught){need(returned.empty() && after==before && diagnostic.back().status=="exception","exception did not restore call entry");for(const auto& g:diagnostic){need(!g.accepted,"exception kept accepted group");for(const auto& t:g.trials)need(!t.retained,"exception retained dwell");}}
 else{
  need(phase==3 && !persistent && returned.size()>=3 && !returned.back().converged && returned.back().accepted_dt==0,"unexpected normal fault outcome");Snapshot expected=before;expected.P=returned.back().P;expected.fe_init=true;need(after==expected,"normal failure changed persistent configuration");need(diagnostic.back().status=="solver_failure" && !diagnostic.back().accepted,"normal failure trace");const auto& prior=returned[returned.size()-2];const auto& failed=returned.back();need(prior.converged && failed.time==prior.time && failed.phi==prior.phi && failed.n==prior.n && failed.p==prior.p && failed.P==prior.P,"normal failure lost accepted prefix");
  std::vector<SimulationResult> prefix(returned.begin(),returned.end()-1),control(baseline.states.begin(),baseline.states.begin()+prefix.size());need(identical(prefix,control),"accepted prefix differs from control");for(const auto& t:diagnostic.back().trials)need(!t.retained,"failed normal trial retained dwell");
  // Normal return intentionally retained the prefix. Explicitly rewind its
  // public material memory before retrying the whole original call.
  s->set_ferroelectric_ensemble_history(before.P,before.play);need(Snapshot(*s)==before,"explicit whole-call rewind incomplete");
 }
 const auto retry=s->solve_transient();const auto retry_trace=s->transient_attempt_history();need(identical(retry,baseline.states) && identical(retry_trace,baseline.attempts),"fault retry changed full history/trace");Snapshot expected_final=before;expected_final.P=retry.back().P;expected_final.fe_init=true;need(Snapshot(*s)==expected_final,"retry configuration drift");
 std::cout<<"{\"fault_case\":true,";key(dim,log,depol,index,family,protocol);std::cout<<",\"phase\":"<<phase<<",\"persistent\":"<<persistent<<",\"caught\":"<<caught<<",\"fired\":true,\"failure_count\":"<<fault490::failures<<",\"observed_groups\":"<<fault490::observed_groups<<",\"observed_called\":"<<fault490::observed_called<<",\"observed_converged\":"<<fault490::observed_converged<<",\"observed_prefix\":"<<fault490::observed_prefix<<",\"observed_P_changed\":"<<fault490::observed_P_changed<<",\"observed_linear\":"<<fault490::observed_linear<<",\"observed_clock\":";values({fault490::observed_start,fault490::observed_end});std::cout<<",\"entry\":";snapshot(before);std::cout<<",\"after\":";snapshot(after);std::cout<<",\"returned\":";history(returned);std::cout<<",\"fault_trace\":";trace(diagnostic);std::cout<<",\"retry\":";history(retry);std::cout<<",\"retry_trace\":";trace(retry_trace);std::cout<<",\"same_retry\":true,\"same_retry_trace\":true,\"explicit_normal_rewind\":"<<(!caught)<<"}"<<std::endl;
}
void matrix(std::istream& input){
 int count;need(bool(input>>count) && count==96,"wrong input matrix size");std::map<std::tuple<int,bool,int>,std::vector<SimulationResult>> sources;
 for(int c=0;c<count;++c){
  int dim,log_int,depol,index,family,protocol,nwave,nsteps;need(bool(input>>dim>>log_int>>depol>>index>>family>>protocol>>nwave>>nsteps),"truncated input matrix");bool log=log_int;Fixture f(dim);const auto id=std::make_tuple(dim,log,depol);
  if(!sources.count(id)){auto live=f.simulator(log,depol);auto h=live->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source failed");sources.emplace(id,std::move(h));}
  const auto& source=sources.at(id).at(index);Wave original;for(int i=0;i<nwave;++i){original.times.push_back(read_number(input));original.voltages.push_back(read_number(input));}Wave scheduled{{source.time},{original.at(source.time)}};for(int i=0;i<nsteps;++i){const auto t=read_number(input);need(t>scheduled.times.back(),"input clock did not advance");scheduled.times.push_back(t);scheduled.voltages.push_back(original.at(t));}
  need(scheduled.times.back()==original.times.back(),"input endpoint missing");auto s=make(f,source,scheduled,log,depol);const Snapshot entry(*s);Coupled baseline;baseline.states=s->solve_transient();baseline.attempts=s->transient_attempt_history();need(accepted(baseline.states,scheduled.times.back(),nsteps) && baseline.attempts.size()==size_t(nsteps),"uninterrupted solve hidden/missing interval");Snapshot expected=entry;expected.P=baseline.states.back().P;expected.fe_init=true;need(Snapshot(*s)==expected,"uninterrupted configuration drift");
  for(size_t i=1;i<baseline.states.size();++i)need(baseline.states[i].time==scheduled.times[i] && baseline.states[i].displacement_current_available && baseline.states[i].total_terminal_current_available,"uninterrupted ledger/clock missing");
  std::vector<Candidate> predictors;for(size_t i=1;i<baseline.states.size();++i){const auto& old=baseline.states[i-1];predictors.push_back(trial(f,old,depol,old.P,scheduled,old.time,baseline.states[i].time));for(size_t j=0;j<old.P.size();++j)need(abs_q(predictors.back().P[j]-baseline.states[i].P[j])/PS<TCAD_CONST(1e-24),"continuous split phase mismatch");}
  std::cout<<"{\"continuous_case\":true,";key(dim,log,depol,index,family,protocol);std::cout<<",\"wave_times\":";values(scheduled.times);std::cout<<",\"wave_voltages\":";values(scheduled.voltages);std::cout<<",\"source\":";result(source);std::cout<<",\"full\":";history(baseline.states);std::cout<<",\"predictors\":[";for(size_t i=0;i<predictors.size();++i){if(i)std::cout<<',';emit(predictors[i],"uninterrupted_predictor");}std::cout<<"],\"trace\":";trace(baseline.attempts);std::cout<<",\"entry\":";snapshot(entry);std::cout<<",\"after\":";snapshot(Snapshot(*s));std::cout<<",\"runtime_event_controller\":false,\"nonlinear_tolerance\":";number(TCAD_CONST(1e-16));std::cout<<"}"<<std::endl;
  if(index==8 && family==1 && protocol==1)for(int phase=0;phase<4;++phase)for(bool persistent:{false,true})failure_case(f,source,scheduled,log,depol,dim,index,family,protocol,phase,persistent,baseline);
 }
}
}
namespace fine493 {
using namespace continuous490;
void run(std::istream& input){
 int count;need(bool(input>>count) && count==24,"wrong refinement matrix");std::map<std::tuple<int,bool,int>,std::vector<SimulationResult>> sources;
 for(int c=0;c<count;++c){
  int dim,li,depol,index,family,protocol,nwave;need(bool(input>>dim>>li>>depol>>index>>family>>protocol>>nwave),"truncated waves");bool log=li;Fixture f(dim);auto id=std::make_tuple(dim,log,depol);
  if(!sources.count(id)){auto s=f.simulator(log,depol);auto h=s->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source failed");sources.emplace(id,std::move(h));}
  const auto& source=sources.at(id).at(index);Wave original;for(int i=0;i<nwave;++i){original.times.push_back(read_number(input));original.voltages.push_back(read_number(input));}
  V common=original.times;for(int i=0;i<=8;++i)common.push_back(source.time+i*T/4);std::sort(common.begin(),common.end());common.erase(std::unique(common.begin(),common.end()),common.end());Wave wave;wave.times=common;for(auto t:common)wave.voltages.push_back(original.at(t));
  need(wave.times.front()==source.time && wave.times.back()==source.time+2*T,"physical wave bounds");
  std::vector<std::string> levels;
  for(int factor:{32,64}){
   auto s=make(f,source,wave,log,depol);const real_t cap=T/(4*factor);s->set_transient_dt(cap);const Snapshot entry(*s);auto h=s->solve_transient();auto groups=s->transient_attempt_history();need(h.size()>1 && accepted(h,wave.times.back(),h.size()-1) && groups.size()==h.size()-1,"refinement failed");
   std::vector<size_t> indices;for(auto t:common){auto at=std::find_if(h.begin(),h.end(),[&](const auto& r){return r.time==t;});need(at!=h.end(),"common observation missing");indices.push_back(at-h.begin());}
   for(size_t i=1;i<h.size();++i)need(h[i].accepted_dt>0 && h[i].accepted_dt<=cap && h[i].time>h[i-1].time && h[i].displacement_current_available && h[i].total_terminal_current_available,"invalid refined clock/ledger");
   Snapshot expected=entry;expected.P=h.back().P;expected.fe_init=true;need(Snapshot(*s)==expected,"refinement configuration drift");
   levels.push_back(serialized([&]{std::cout<<"{\"factor\":"<<factor<<",\"dt_cap\":";number(cap);std::cout<<",\"history\":";history(h);std::cout<<",\"trace\":";trace(groups);std::cout<<",\"entry\":";snapshot(entry);std::cout<<",\"after\":";snapshot(Snapshot(*s));std::cout<<",\"common_indices\":[";for(size_t i=0;i<indices.size();++i){if(i)std::cout<<',';std::cout<<indices[i];}std::cout<<"]}";}));
  }
  std::cout<<"{\"refinement_case\":true,";key(dim,log,depol,index,family,protocol);std::cout<<",\"source\":";result(source);std::cout<<",\"original_times\":";values(original.times);std::cout<<",\"original_voltages\":";values(original.voltages);std::cout<<",\"wave_times\":";values(wave.times);std::cout<<",\"wave_voltages\":";values(wave.voltages);std::cout<<",\"levels\":[";for(size_t i=0;i<levels.size();++i){if(i)std::cout<<',';std::cout<<levels[i];}std::cout<<"],\"runtime_event_controller\":false}"<<std::endl;
 }
}
}
int main(int argc,char** argv){try{need(argc==2,"expected input file");std::ifstream input(argv[1]);need(bool(input),"input open failed");fine493::run(input);return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
