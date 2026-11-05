// Reuse the frozen475 public fixture; width controls match the477 waveform.
#define main restart_fixture_main
#include "native_restart_time_convergence.cpp"
#undef main
namespace {
constexpr real_t reversal_time=TCAD_CONST(1.93e-12);
real_t original_voltage(real_t t){
    return t<=TCAD_CONST(1e-12)?TCAD_CONST(.001)*t/TCAD_CONST(1e-12):
        TCAD_CONST(.001)-TCAD_CONST(.002)*(t-TCAD_CONST(1e-12))/TCAD_CONST(1.5e-12);
}
real_t half_width(int family,int level){
    if(family==0)return TCAD_CONST(1e-16);
    if(family==1)return TCAD_CONST(1e-18);
    if(family==2)return TCAD_CONST(1e-20);
    return TCAD_CONST(1e-4)*TCAD_CONST(.25e-12)/(1u<<level);
}
Values width_knots(int family,int level){
    Values times;
    for(int i=0;i<=10;++i)times.push_back(i*TCAD_CONST(.25e-12));
    const real_t width=half_width(family,level);
    times.push_back(reversal_time-width);times.push_back(reversal_time+width);
    std::sort(times.begin(),times.end());return times;
}
std::unique_ptr<DeviceSimulator> width_fixture(int dimension,bool log,int level,int family){
    auto s=fixed_fixture(dimension,log,2,level);Values voltages;
    const auto knots=width_knots(family,level);for(real_t t:knots)voltages.push_back(original_voltage(t));
    std::map<size_t,Values> waveforms;
    for(size_t k=0;k<(dimension==3?3u:1u);++k)for(size_t j=0;j<3;++j)waveforms[2+3*(j+3*k)]=voltages;
    s->set_transient_voltage_waveforms(knots,waveforms);return s;
}
bool width_alignment(int dimension,bool log,int level,int family){
    auto s=width_fixture(dimension,log,level,family);const Snapshot entry(*s);
    const auto full=s->solve_transient();const auto full_trace=s->transient_attempt_history();const Snapshot after(*s);
    if(!accepted(full))throw std::runtime_error("width full trajectory rejected");
    const real_t desired_cut=reversal_time-half_width(family,level);
    const auto found=std::find_if(full.begin(),full.end(),[&](const SimulationResult& r){return tcad::abs_q(r.time-desired_cut)<=TCAD_CONST(1e-30)*final_time;});
    if(found==full.end())throw std::runtime_error("width restart cut missing");
    const real_t cut=found->time;const size_t index=found-full.begin();auto tail_sim=width_fixture(dimension,log,level,family);
    seed(*tail_sim,*found,after.play,2,cut);const Snapshot tail_entry(*tail_sim);
    const auto tail=tail_sim->solve_transient();const auto tail_trace=tail_sim->transient_attempt_history();const Snapshot tail_after(*tail_sim);
    const bool good=accepted(tail) && index+tail.size()==full.size() && returned_timeline_matches(full,full_trace) && returned_timeline_matches(tail,tail_trace)
        && after.phi==entry.phi && after.n==entry.n && after.p==entry.p && after.contacts==entry.contacts
        && tail.front().P==found->P && tail_entry.P==found->P && tail_after.P==tail.back().P
        && tail_after.phi==tail_entry.phi && tail_after.n==tail_entry.n && tail_after.p==tail_entry.p && tail_after.contacts==entry.contacts;
    std::cout<<"{\"dimension\":"<<dimension<<",\"logarithmic\":"<<log<<",\"mode\":2,\"nls\":1,\"natural\":0,\"schedule\":3,\"level\":"<<level<<",\"family\":"<<family;
    std::cout<<",\"half_width\":";values({half_width(family,level)});
    std::cout<<",\"knots\":";values(width_knots(family,level));Values voltages;for(real_t t:width_knots(family,level))voltages.push_back(original_voltage(t));
    std::cout<<",\"voltages\":";values(voltages);std::cout<<",\"index\":"<<index<<",\"cut\":";values({cut});
    std::cout<<",\"full\":";history(full);std::cout<<",\"full_trace\":";trace(full_trace);
    std::cout<<",\"tail\":";history(tail);std::cout<<",\"tail_trace\":";trace(tail_trace);
    std::cout<<",\"entry\":";snapshot(tail_entry);std::cout<<",\"after\":";snapshot(tail_after);
    std::cout<<",\"passed\":"<<good<<"}"<<std::endl;return good;
}
}
int main(){
    bool passed=true;
    try{for(int d:{2,3})for(bool log:{false,true})for(int family:{0,1,2,3})for(int level:{0,1,2,3})passed=width_alignment(d,log,level,family)&&passed;}
    catch(const std::exception& e){std::cerr<<"fixture error: "<<e.what()<<'\n';return 2;}
    return passed?0:1;
}
