// Isolated acceptance-loop diagnostic; sealed485 helpers, production unchanged.
// Reuse the sealed484 public fixture; production depolarization guard stays.
#define main sealed484_fixture_main
#include "native_nls_depolarization_roots.cpp"
#undef main
namespace coupled488 {
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
void run_coupled(const Fixture& f,const SimulationResult& source,int dim,bool log,int depol,int source_index,int family,int protocol){
 const real_t width=family?TCAD_CONST(0x1p-66):TCAD_CONST(0x1p-60);Frozen seed(f,source,depol);const auto lo=seed.probe(-TCAD_CONST(.0625)),hi=seed.probe(TCAD_CONST(.0625));const real_t vroot=seed.root_voltage(lo,hi),root=source_index==0?2*T*vroot/TCAD_CONST(0x1p-10):2*T+(TCAD_CONST(0x1p-10)-vroot)*T/TCAD_CONST(0x1p-10);
 Wave wave{{source.time,source_index==0?2*T:4*T},{voltage(source.time),voltage(source_index==0?2*T:4*T)}};if(protocol)wave={{source.time,root-T/16,root+T/16,wave.times.back()},{wave.voltages.front(),vroot,vroot,wave.voltages.back()}};
 SimulationResult accepted=source;std::vector<Entry> entries;std::string status="iteration_cap";int transactions=0,failures=0,exceptions=0;
 for(int count=0;count<24 && accepted.time<wave.times.back();++count){
  auto selected=advance_loop(f,accepted,depol,wave,accepted.time,accepted.P,width,1,false);if(selected.steps.empty() || !selected.steps[0].committed){status=selected.status;break;}
  Entry entry;entry.selection=std::move(selected.steps[0]);entry.actual=solve_candidate(f,accepted,wave,log,depol,entry.selection.chosen.time,count==0);if(count==0){++transactions;failure_controls(f,accepted,wave,log,depol,entry.selection.chosen.time,entry.actual);++failures;++exceptions;}
  need(entry.actual.states.size()==2 && entry.actual.attempts.size()==1,"candidate interval contains hidden steps");const auto& end=entry.actual.states.back();
  if(!end.converged){status="electrical_failure";entries.push_back(std::move(entry));break;}
  need(!end.phi_frozen && !end.transient_majority_frozen && end.accepted_dt>0 && end.time==entry.selection.chosen.time && end.transient_charge_ledger_available && end.displacement_current_available && end.total_terminal_current_available,"coupled candidate missing equations/ledger");
  for(size_t i=0;i<end.P.size();++i)entry.P_defect=std::max(entry.P_defect,abs_q(end.P[i]-entry.selection.chosen.P[i])/PS);need(entry.P_defect<TCAD_CONST(1e-24),"real split NLS phase differs from frozen candidate");entry.actual_drive=final_drive(f,end,depol);accepted=end;entries.push_back(std::move(entry));
 }
 if(accepted.time==wave.times.back())status="finished";
 std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_index\":"<<source_index<<",\"family\":"<<family<<",\"protocol\":"<<protocol<<",\"width\":";number(width);std::cout<<",\"wave_times\":";values(wave.times);std::cout<<",\"wave_voltages\":";values(wave.voltages);std::cout<<",\"source\":";result(source);std::cout<<",\"steps\":[";
 for(size_t i=0;i<entries.size();++i){if(i)std::cout<<',';const auto& e=entries[i];std::cout<<"{\"selection\":";emit_step(e.selection);std::cout<<",\"actual\":";history(e.actual.states);std::cout<<",\"trace\":";trace(e.actual.attempts);std::cout<<",\"actual_drive\":";drive(e.actual_drive);std::cout<<",\"P_normalized_defect\":";number(e.P_defect);std::cout<<'}';}
 std::cout<<"],\"end\":";number(accepted.time);std::cout<<",\"status\":\""<<status<<"\",\"max_steps\":24,\"material_rollback_replays\":"<<transactions<<",\"ordinary_failure_checks\":"<<failures<<",\"discard_exception_checks\":"<<exceptions<<",\"carriers_frozen\":false,\"device_steps_executed\":true,\"runtime_event_controller\":false}"<<std::endl;
}
void matrix(){for(int dim:{2,3})for(bool log:{false,true})for(int depol:{0,25,50}){
 Fixture f(dim);auto live=f.simulator(log,depol);const auto h=live->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source trajectory failed");const auto P=live->fe_polarization(),play=live->ferroelectric_play_history();
 for(int source_index:{0,8})for(int family:{0,1})for(int protocol:{0,1})run_coupled(f,h[source_index],dim,log,depol,source_index,family,protocol);
 need(live->fe_polarization()==P && live->ferroelectric_play_history()==play,"coupled candidates mutated source device");std::cout<<"{\"summary\":true,\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_states\":2,\"cases\":8,\"live_memory_unchanged\":true}"<<std::endl;
}}
}
int main(){try{coupled488::matrix();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
