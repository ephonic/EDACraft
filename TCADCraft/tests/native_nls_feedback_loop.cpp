// Isolated acceptance-loop diagnostic; sealed485 helpers, production unchanged.
// Reuse the sealed484 public fixture; production depolarization guard stays.
#define main sealed484_fixture_main
#include "native_nls_depolarization_roots.cpp"
#undef main
namespace loop487 {
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
void run_case(const Fixture& f,const SimulationResult& source,int dim,bool log,int depol,int source_index,int family,int protocol,int mode){
 const real_t width=family?TCAD_CONST(0x1p-66):TCAD_CONST(0x1p-60);Frozen seed(f,source,depol);const auto lo=seed.probe(-TCAD_CONST(.0625)),hi=seed.probe(TCAD_CONST(.0625));const real_t vroot=seed.root_voltage(lo,hi),root=source_index==0?2*T*vroot/TCAD_CONST(0x1p-10):2*T+(TCAD_CONST(0x1p-10)-vroot)*T/TCAD_CONST(0x1p-10);
 Wave wave{{source.time,source_index==0?2*T:4*T},{voltage(source.time),voltage(source_index==0?2*T:4*T)}};if(protocol)wave={{source.time,root-T/16,root+T/16,wave.times.back()},{wave.voltages.front(),vroot,vroot,wave.voltages.back()}};
 const real_t start=mode==0?source.time:mode==1?(protocol?root-T/16:root)-TCAD_CONST(.37)*width:mode==2?root:(protocol?root+T/16:root)+TCAD_CONST(.37)*width;
 const auto result=advance_loop(f,source,depol,wave,start,source.P,width,24,true);need(!result.steps.empty() && result.exceptions==2,"empty loop or injection missing");
 bool restarted=false;size_t restart_count=0;
 if(result.steps.front().committed){const auto& checkpoint=result.steps.front().chosen;const auto resumed=advance_loop(f,source,depol,wave,checkpoint.time,checkpoint.P,width,23,false);need(resumed.status==result.status && resumed.end==result.end && resumed.P==result.P && resumed.steps.size()+1==result.steps.size(),"local restart endpoint mismatch");for(size_t i=0;i<resumed.steps.size();++i)need(same_step(resumed.steps[i],result.steps[i+1]),"local restart trace mismatch");restarted=true;restart_count=resumed.steps.size();}
 std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_index\":"<<source_index<<",\"family\":"<<family<<",\"protocol\":"<<protocol<<",\"start_mode\":"<<mode<<",\"source_time\":";number(source.time);std::cout<<",\"start\":";number(start);std::cout<<",\"width\":";number(width);std::cout<<",\"wave_times\":";values(wave.times);std::cout<<",\"wave_voltages\":";values(wave.voltages);std::cout<<",\"n\":";values(source.n);std::cout<<",\"p\":";values(source.p);std::cout<<",\"source_P\":";values(source.P);std::cout<<",\"steps\":[";
 for(size_t i=0;i<result.steps.size();++i){if(i)std::cout<<',';emit_step(result.steps[i]);}std::cout<<"],\"end\":";number(result.end);std::cout<<",\"final_P\":";values(result.P);std::cout<<",\"status\":\""<<result.status<<"\",\"max_steps\":24,\"synthetic_exception_checks\":"<<result.exceptions<<",\"accepted_state_preserved_on_retry\":true,\"local_restart_identical\":"<<(restarted?"true":"false")<<",\"local_restart_steps\":"<<restart_count<<",\"carriers_frozen\":true,\"device_step_accepted\":false}"<<std::endl;
}
void matrix(){for(int dim:{2,3})for(bool log:{false,true})for(int depol:{0,25,50}){
 Fixture f(dim);auto live=f.simulator(log,depol);const auto h=live->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source trajectory failed");const auto P=live->fe_polarization(),play=live->ferroelectric_play_history();const int guards=guard_tests();
 for(int source_index:{0,8})for(int family:{0,1})for(int protocol:{0,1})for(int mode:{0,1,2,3})run_case(f,h[source_index],dim,log,depol,source_index,family,protocol,mode);
 need(live->fe_polarization()==P && live->ferroelectric_play_history()==play,"loop mutated source device");std::cout<<"{\"summary\":true,\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_states\":2,\"cases\":32,\"selector_guard_checks\":"<<guards<<",\"live_memory_unchanged\":true}"<<std::endl;
}}
}
int main(){try{loop487::matrix();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
