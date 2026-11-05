// Candidate transactions only; all helpers copied from sealed485. No runtime change.
// Reuse the sealed484 public fixture; production depolarization guard stays.
#define main sealed484_fixture_main
#include "native_nls_depolarization_roots.cpp"
#undef main
namespace transactions486 {
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
void candidate_case(const Fixture& f,const SimulationResult& source,Frozen& reference,const Wave& wave,int dim,bool log,int depol,int source_index,int family,int protocol,real_t width,real_t start,real_t limit,real_t proposed,real_t original,real_t root){
 const V base=reference.P;const auto control=reference.probe(wave.at(start));const real_t sign=control.d.mean_field>0?1:-1;need(control.d.mean_field!=0,"incoming zero start");
 auto evaluate=[&](real_t t,int fail=0){return trial(f,source,depol,base,wave,start,t,fail);};
 const auto A=evaluate(original),B=evaluate(start+(original-start)/2),again=evaluate(original);
 need(A.P==again.P && same(A.before,again.before) && same(A.after,again.after),"candidate dwell accumulated");
 int failures=0;for(int fail:{1,2}){try{evaluate(original,fail);}catch(const std::runtime_error& e){need(std::string(e.what()).find("synthetic ")==0,"unexpected candidate exception");++failures;}}
 const auto recovered=evaluate(original);need(failures==2 && recovered.P==A.P && same(recovered.before,A.before) && same(recovered.after,A.after),"discard recovery changed candidate");
 std::vector<Candidate> scan;for(int i=0;i<=16;++i)scan.push_back(evaluate(start+(original-start)*i/16));
 std::vector<Candidate> branch;for(int i:{-1,0,1})branch.push_back(evaluate(root+i*width));
 std::vector<Candidate> bisected;real_t low=start,high=original;int crossings=0;
 for(size_t i=1;i<scan.size();++i)if(sign*scan[i-1].after.d.mean_field>0 && sign*scan[i].after.d.mean_field<0){++crossings;low=scan[i-1].time;high=scan[i].time;}
 const bool corrected=sign*A.after.d.mean_field<0;Candidate incoming=A,outgoing=A;
 if(corrected){
  need(depol>0 && crossings==1,"candidate branch scan ambiguous");
  for(int i=0;i<80 && high-low>width/64;++i){const real_t mid=(low+high)/2;auto c=evaluate(mid);need(c.before.d.mean_field*sign>0,"candidate bisection left original branch");if(c.after.d.mean_field*sign>0)low=mid;else high=mid;bisected.push_back(std::move(c));}
  need(high-low<=width/64,"candidate bisection cap");const real_t middle=(low+high)/2;
  need(middle-width>start && middle+width<root && middle+width<=proposed && original<=proposed && proposed<=limit,"candidate corrected clock bounds");
  incoming=evaluate(middle-width);outgoing=evaluate(middle+width);
  need(sign*incoming.before.d.mean_field>0 && sign*outgoing.before.d.mean_field>0 && sign*incoming.after.d.mean_field>0 && sign*outgoing.after.d.mean_field<0,"candidate post-update bracket failed");
 }else need(depol==0 && crossings==0 && sign*A.after.d.mean_field>0,"unexpected unchanged candidate");
 need(reference.P==base && same(control,reference.probe(wave.at(start))),"discard changed reference state");
 std::cout<<"{\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_index\":"<<source_index<<",\"family\":"<<family<<",\"protocol\":"<<protocol<<",\"start\":";number(start);std::cout<<",\"limit\":";number(limit);std::cout<<",\"proposed\":";number(proposed);std::cout<<",\"original_end\":";number(original);std::cout<<",\"frozen_root\":";number(root);std::cout<<",\"width\":";number(width);std::cout<<",\"wave_times\":";values(wave.times);std::cout<<",\"wave_voltages\":";values(wave.voltages);std::cout<<",\"n\":";values(source.n);std::cout<<",\"p\":";values(source.p);std::cout<<",\"base_P\":";values(base);
 std::cout<<",\"control\":";observed(control);std::cout<<",\"original\":";emit(A,"original");std::cout<<",\"interleaved\":";emit(B,"interleaved");std::cout<<",\"repeat\":";emit(again,"repeat");std::cout<<",\"recovered\":";emit(recovered,"recovered");
 std::cout<<",\"scan\":[";for(size_t i=0;i<scan.size();++i){if(i)std::cout<<',';emit(scan[i],"scan_"+std::to_string(i));}
 std::cout<<"],\"branch\":[";for(size_t i=0;i<branch.size();++i){if(i)std::cout<<',';emit(branch[i],"branch_"+std::to_string(i));}
 std::cout<<"],\"bisection\":[";for(size_t i=0;i<bisected.size();++i){if(i)std::cout<<',';emit(bisected[i],"bisect_"+std::to_string(i));}
 std::cout<<"],\"bracket_low\":";number(low);std::cout<<",\"bracket_high\":";number(high);std::cout<<",\"incoming\":";emit(incoming,"incoming");std::cout<<",\"outgoing\":";emit(outgoing,"outgoing");
 std::cout<<",\"sampled_crossings\":"<<crossings<<",\"synthetic_exception_checks\":"<<failures<<",\"reference_unchanged\":true,\"repeat_identical\":true,\"carriers_frozen\":true,\"device_step_accepted\":false,\"status\":\""<<(corrected?"candidate_verified":"unchanged_control")<<"\"}"<<std::endl;
}
void replay(const Fixture& f,const SimulationResult& source,int dim,bool log,int depol,int source_index,int family,int protocol){
 const real_t width=family?TCAD_CONST(0x1p-66):TCAD_CONST(0x1p-60);Frozen s(f,source,depol);const auto lo=s.probe(-TCAD_CONST(.0625)),hi=s.probe(TCAD_CONST(.0625));const real_t vroot=s.root_voltage(lo,hi),root0=source_index==0?2*T*vroot/TCAD_CONST(0x1p-10):2*T+(TCAD_CONST(0x1p-10)-vroot)*T/TCAD_CONST(0x1p-10);
 Wave wave{{source.time,source_index==0?2*T:4*T},{voltage(source.time),voltage(source_index==0?2*T:4*T)}};
 if(protocol)wave={{source.time,root0-T/16,root0+T/16,wave.times.back()},{wave.voltages.front(),vroot,vroot,wave.voltages.back()}};
 real_t time=source.time;
 for(int count=0;count<24 && time<wave.times.back();++count){
  const auto first=s.probe(wave.at(time)),last=s.probe(wave.at(std::min(wave.limit(time),time+T/4)));const real_t limit=wave.limit(time),proposed=std::min(limit,time+T/4);real_t selected=proposed,local_root=proposed;bool incoming=false;
  if(first.d.mean_field==0){if(last.d.mean_field!=0){const real_t out=std::min(proposed,time+width);if(!(out<proposed && s.probe(wave.at(out)).d.mean_field==0))selected=out;}}
  else if((first.d.raw_mean_field>0 && last.d.raw_mean_field<0)||(first.d.raw_mean_field<0 && last.d.raw_mean_field>0)||last.d.mean_field==0){
   if(last.d.mean_field!=0)local_root=time+(proposed-time)*first.d.raw_mean_field/(first.d.raw_mean_field-last.d.raw_mean_field);
   incoming=local_root-width>time+width/8;selected=incoming?local_root-width:std::min(proposed,local_root+width);
  }
  need(selected>time && selected<=proposed,"replay did not advance");
  if(incoming){candidate_case(f,source,s,wave,dim,log,depol,source_index,family,protocol,width,time,limit,proposed,selected,local_root);return;}
  s.advance(s.probe(wave.at(selected)),selected-time);time=selected;
 }
 throw std::runtime_error("replay missing first incoming");
}
void matrix(){for(int dim:{2,3})for(bool log:{false,true})for(int depol:{0,25,50}){
 Fixture f(dim);auto live=f.simulator(log,depol);const auto h=live->solve_transient();need(h.size()==17 && std::all_of(h.begin(),h.end(),[](const auto& r){return r.converged;}),"source trajectory failed");const auto P=live->fe_polarization(),play=live->ferroelectric_play_history();
 for(int source_index:{0,8})for(int family:{0,1})for(int protocol:{0,1})replay(f,h[source_index],dim,log,depol,source_index,family,protocol);
 need(live->fe_polarization()==P && live->ferroelectric_play_history()==play,"transactions mutated source device");std::cout<<"{\"summary\":true,\"dimension\":"<<dim<<",\"logarithmic\":"<<log<<",\"depol\":"<<depol<<",\"source_states\":2,\"cases\":8,\"live_memory_unchanged\":true}"<<std::endl;
}}
}
int main(){try{transactions486::matrix();return 0;}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}}
